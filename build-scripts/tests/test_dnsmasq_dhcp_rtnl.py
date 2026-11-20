#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dnsmasq: a DHCP packet no longer asks the kernel under the network configuration lock (review 2026-11-11, D-6).

WHY THIS EXISTS. For every DHCP packet dnsmasq dumped the kernel's IPv4 address list (a netlink request), asked for
the interface's own address (ioctl SIOCGIFADDR) and, to answer a client that has no address yet, wrote the client
into the ARP table (ioctl SIOCSARP). All three wait for the kernel's network configuration lock. A Wi-Fi driver call
that holds that lock for seconds therefore stopped DHCP, and DNS with it (one thread). Now the address list is kept
between packets and read again only after an address event, the interface address comes from that list, and rc
writes dnsmasq's own dhcp-broadcast option so the ARP write is gone.

WHAT IT DOES. Builds the tree's dnsmasq on the host and runs it for real inside a private network namespace (no
root needed): a veth pair, dnsmasq serving DHCP on one end, busybox udhcpc as the client on the other, with every
ioctl and netlink send of dnsmasq traced by strace.
  - several full DHCP exchanges get leases;
  - while they run, dnsmasq makes NO SIOCGIFADDR, NO SIOCSARP and no further address-list request;
  - the interface's address is then changed: the very next client is served from the NEW subnet (the kept list was
    dropped on the kernel's event) with exactly one more address-list request.
Pins the source and the four places rc writes the option.

Exit 0 pass, 1 fail, 77 skipped (no router source tree, or the host lacks unshare / strace / busybox udhcpc)."""
import os, re, shutil, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "dnsmasq", "src", "netlink.c")):
    skip("no router source tree with dnsmasq/src/netlink.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:900] if detail else ""))

def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

# ---------------------------------------------------------------- source pins
nl = rd("dnsmasq", "src", "netlink.c"); dh = rd("dnsmasq", "src", "dhcp.c")
check("netlink.c: the kernel dump is behind a wrapper that keeps the IPv4 list",
      "static int iface_enumerate_kernel(int family, void *parm, callback_t callback)" in nl
      and "if (family != AF_INET || !reaper_nl_events || daemon->pipe_to_parent != -1)\n    return iface_enumerate_kernel(family, parm, callback);" in nl)
check("netlink.c: the list is kept only when the socket hears address events, and dropped on every address event and failed read",
      "reaper_nl_events = (addr.nl_groups & RTMGRP_IPV4_IFADDR) != 0;" in nl
      # IPv4 events only: every IPv6 router advertisement refreshes lifetimes and would drop the list for nothing
      and "((struct ifaddrmsg *)NLMSG_DATA(h))->ifa_family == AF_INET)\n    reaper_ifa4_valid = 0;" in nl
      and "h->nlmsg_type == RTM_NEWADDR || h->nlmsg_type == RTM_DELADDR" in nl
      and "if (rc == -1 && errno != EAGAIN && errno != EWOULDBLOCK)\n    reaper_ifa4_valid = 0;" in nl)
check("netlink.c: 'valid' is set before the dump, so an event read during the dump forces one more read",
      nl.find("reaper_ifa4_valid = 1;") < nl.find("rc = iface_enumerate_kernel(AF_INET, NULL, (callback_t){.af_inet=reaper_ifa4_collect});"))
i = dh.find("reaper_ifa4_primary(iface_index, ifr.ifr_name, &iface_addr)")
check("dhcp.c: the interface address comes from the kept list first, the ioctl only as the fall-back",
      0 < i < dh.find("ioctl(daemon->dhcpfd, SIOCGIFADDR, &ifr) != -1", i) < i + 200)
svc = rd("rc", "services.c"); sdn = rd("rc", "sdn.c")
check("rc: every dnsmasq config that serves DHCP carries dhcp-broadcast (three in services.c, one in sdn.c)",
      svc.count('dhcp-broadcast\\n"') == 3 and sdn.count('dhcp-broadcast\\n"') == 1
      and 'fprintf(fp, "dhcp-broadcast\\n");' in svc
      and svc.find('fprintf(fp, "dhcp-broadcast\\n");') < svc.find('if (nvram_get_int("dhcpd_auth") >= 0)\n\t\t\tfprintf(fp, "dhcp-authoritative\\n");'))

# ---------------------------------------------------------------- the real thing
need = [t for t in ("unshare", "strace", "busybox", "ip", "make") if not shutil.which(t)]
if need or not CC:
    print("note the run needs %s on the host - the source pins above were checked, the DHCP run is skipped" % ", ".join(need or ["a C compiler"]))
elif subprocess.run(["unshare", "-Urn", "true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
    print("note unprivileged network namespaces are not available here - the DHCP run is skipped")
elif b"udhcpc" not in subprocess.run(["busybox", "--list"], stdout=subprocess.PIPE).stdout:
    print("note this busybox has no udhcpc - the DHCP run is skipped")
else:
    tmp = tempfile.mkdtemp(prefix="dnsmasq_rtnl_")
    try:
        db = os.path.join(tmp, "dnsmasq")
        shutil.copytree(os.path.join(SRC, "dnsmasq"), db, symlinks=True,
                        ignore=shutil.ignore_patterns("*.o", "dnsmasq", ".git", "po", "contrib"))
        b = subprocess.run(["make", "-C", db, "COPTS=-DNO_DBUS -DNO_INOTIFY -DHAVE_BROKEN_RTC", "CC=" + CC, "-j4"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=900)
        exe = os.path.join(db, "src", "dnsmasq")
        check("dnsmasq builds on the host", b.returncode == 0 and os.path.isfile(exe), b.stdout[-600:])
        if os.path.isfile(exe):
            conf = os.path.join(tmp, "d.conf")
            # user and group root: inside the namespace only uid/gid 0 exist, dnsmasq must not try to drop to another
            open(conf, "w").write("port=0\nuser=root\ngroup=root\ninterface=v0\nbind-interfaces\nno-ping\n"
                                  "dhcp-range=10.99.0.50,10.99.0.60,255.255.255.0,1h\n"
                                  "dhcp-range=10.77.0.50,10.77.0.60,255.255.255.0,1h\n"
                                  "dhcp-authoritative\ndhcp-broadcast\nlog-dhcp\n"
                                  "dhcp-leasefile=%s/leases\npid-file=%s/pid\nlog-facility=%s/log\n" % (tmp, tmp, tmp))
            hook = os.path.join(tmp, "hook.sh")
            open(hook, "w").write('#!/bin/sh\n[ "$1" = bound ] && echo "$ip" >> %s/got\nexit 0\n' % tmp)
            os.chmod(hook, 0o755)
            run = os.path.join(tmp, "run.sh")
            open(run, "w").write('''#!/bin/sh
T=%(tmp)s
ip link set lo up
ip link add v0 type veth peer name v1 || exit 3
ip addr add 10.99.0.1/24 dev v0
ip link set v0 up; ip link set v1 up
# -d: no fork and, above all, no change of user or group (not possible inside the namespace)
strace -f -o $T/trace -e trace=ioctl,sendto,sendmsg %(exe)s -d --conf-file=$T/d.conf >/dev/null 2>&1 &
SP=$!
i=0; while ! grep -q 'DHCP, IP range' $T/log 2>/dev/null && [ $i -lt 50 ]; do sleep 0.1; i=$((i+1)); done
sleep 0.5
wc -l < $T/trace > $T/mark1
client() { busybox udhcpc -i v1 -f -n -q -t 5 -T 1 -x hostname:c$1 -s $T/hook.sh >/dev/null 2>&1; echo "run$1 rc=$?" >> $T/runs; }
client 1; client 2; client 3; client 4
wc -l < $T/trace > $T/mark2
ip addr del 10.99.0.1/24 dev v0
ip addr add 10.77.0.1/24 dev v0
sleep 0.3
client 5
wc -l < $T/trace > $T/mark3
client 6; client 7; client 8
wc -l < $T/trace > $T/mark4
for p in $(pgrep -P $SP); do kill $p 2>/dev/null; done; sleep 0.3; kill $SP 2>/dev/null
exit 0
''' % {"tmp": tmp, "exe": exe})
            os.chmod(run, 0o755)
            r = subprocess.run(["unshare", "-Urn", "sh", run], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=180)
            def g(n):
                p = os.path.join(tmp, n); return open(p, errors="replace").read() if os.path.isfile(p) else ""
            got = g("got").split(); runs = g("runs"); log = g("log")
            check("four clients in a row get a lease from the interface's subnet",
                  len(got) >= 4 and all(a.startswith("10.99.0.") for a in got[:4]) and runs.count("rc=0") >= 4, (got, runs, r.stdout[-300:], log[-600:]))
            check("after the interface's address changes, the next four clients are served from the NEW subnet",
                  len(got) == 8 and all(a.startswith("10.77.0.") for a in got[4:]), (got, runs, log[-600:]))
            tr = g("trace").splitlines()
            try:
                m1, m2, m3, m4 = (int(g(n).strip() or 0) for n in ("mark1", "mark2", "mark3", "mark4"))
            except ValueError:
                m1 = m2 = m3 = m4 = 0
            check("the trace was taken", len(tr) > 10 and 0 < m1 <= m2 <= m3 <= m4, (len(tr), m1, m2, m3, m4))
            def count(lines, pat):
                return sum(1 for l in lines if re.search(pat, l))
            GETADDR = r"sendto\(.*RTM_GETADDR.*AF_INET[,}]"
            p1, p2, p3 = tr[m1:m2], tr[m2:m3], tr[m3:m4]
            replies = count(tr[m1:m4], r"sendmsg\(.*sin_port=htons\(68\)")
            check("dnsmasq answered at least 16 DHCP packets in the run (8 clients, offer and ack each)", replies >= 16, replies)
            check("no SIOCGIFADDR and no SIOCSARP for any DHCP packet",
                  count(tr[m1:m4], r"SIOCGIFADDR") == 0 and count(tr[m1:m4], r"SIOCSARP") == 0,
                  (count(tr[m1:m4], r"SIOCGIFADDR"), count(tr[m1:m4], r"SIOCSARP")))
            check("replies to clients without an address go to the broadcast address", count(tr[m1:m4], r"sendmsg\(.*255\.255\.255\.255") >= 16)
            check("four exchanges with no address change: at most one address-list request (the first packet's)",
                  count(p1, GETADDR) <= 1, [l[:160] for l in p1 if re.search(GETADDR, l)][:4])
            check("after the address change the list is read again - because of the kernel's events (a removal and an addition), a few times at most",
                  1 <= count(p2, GETADDR) <= 4, count(p2, GETADDR))
            check("...and then not at all for the next three exchanges on the new address", count(p3, GETADDR) == 0, count(p3, GETADDR))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed: a DHCP packet is answered without a call that waits for the kernel's network lock")
