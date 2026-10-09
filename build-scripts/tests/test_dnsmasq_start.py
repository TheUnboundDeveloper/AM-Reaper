#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The shipped dnsmasq must START with every directive Reaper emits (2026-10-08, r26 outage).

WHY THIS EXISTS. r26 emitted `hostsdir=` for IPv6 device names. This firmware builds dnsmasq with
-DNO_INOTIFY, so dnsmasq refused to start ("hostsdir are not supported on this platform") and the
router served no DNS, no DHCP and no IPv6 router advertisements until the owner rolled back.
`dnsmasq --test` PASSED that config - the option is refused at startup, not at parse time - so a
syntax check cannot catch this class. Only starting the real binary does.

WHAT IT DOES. Runs the STAGED router dnsmasq (ARM) under qemu-arm-static on a loopback port with a
config holding one line of every directive kind Reaper's writers emit (rc/services.c start_dnsmasq,
rc/sdn.c: rev-server with and without a server, addn-hosts, servers-file, ipset-style local=), checks
it starts and answers an IPv6 PTR from the addn-hosts file and an address-less reverse zone with
NXDOMAIN; then proves the check bites by starting it with hostsdir= and expecting the refusal.
Exit 0 pass, 1 fail, 77 skipped (no staged fs, no qemu-arm-static, or no dig)."""
import os, shutil, subprocess, sys, tempfile, time, getpass

def skip(m): print("SKIP: " + m); sys.exit(77)
def die(m): print("FAIL: " + m); sys.exit(1)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
FS = os.environ.get("REAPER_STAGED_FS") or (os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "targets", "96813GW", "fs")) if SRC else "")
DM = os.path.join(FS, "usr", "sbin", "dnsmasq") if FS else ""
Q = shutil.which("qemu-arm-static")
DIG = shutil.which("dig")
if not DM or not os.path.isfile(DM): skip("no staged dnsmasq (build first, or set REAPER_STAGED_FS)")
if not Q: skip("no qemu-arm-static")
if not DIG: skip("no dig")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def run(conf_lines, port, queries):
    td = tempfile.mkdtemp(prefix="dmstart-")
    try:
        hosts = os.path.join(td, "hosts"); open(hosts, "w").write("2001:db8::10 DESKTOP-TEST\n")
        srv = os.path.join(td, "servers"); open(srv, "w").write("server=127.0.0.2#1\n")
        conf = os.path.join(td, "d.conf")
        base = ["port=%d" % port, "listen-address=127.0.0.1", "bind-interfaces", "no-resolv", "no-hosts",
                "user=%s" % getpass.getuser(), "pid-file=%s" % os.path.join(td, "pid")]
        open(conf, "w").write("\n".join(base + [l.replace("@HOSTS@", hosts).replace("@SRV@", srv).replace("@DIR@", td) for l in conf_lines]) + "\n")
        p = subprocess.Popen([Q, "-L", FS, DM, "-k", "-C", conf, "--log-facility=-"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(2.0)
        answers = []
        if p.poll() is None:
            for q in queries:
                r = subprocess.run([DIG, "@127.0.0.1", "-p", str(port)] + q + ["+time=1", "+tries=1"], capture_output=True, text=True)
                answers.append(r.stdout)
            p.terminate()
        try: out = p.communicate(timeout=5)[0]
        except subprocess.TimeoutExpired: p.kill(); out = p.communicate()[0]
        return out, answers
    finally:
        shutil.rmtree(td, ignore_errors=True)

# every directive kind the Reaper writers emit (rc/services.c, rc/sdn.c)
GOOD = ["addn-hosts=@HOSTS@", "servers-file=@SRV@", "rev-server=2001:db8::/64", "rev-server=10.20.0.0/24,127.0.0.2",
        "rev-server=2001:db8:1::/64,127.0.0.2", "local=/use-application-dns.net/", "strict-order", "edns-packet-max=1232",
        "bogus-priv", "domain-needed", "no-negcache"]
out, ans = run(GOOD, 53531, [["-x", "2001:db8::10", "+short"], ["-x", "2001:db8::99"]])
check("the shipped dnsmasq starts with every directive kind Reaper emits", "started, version" in out and "FAILED" not in out, out[-400:])
check("it answers an IPv6 PTR from the addn-hosts file (the IPv6 device names path)", bool(ans) and "DESKTOP-TEST." in ans[0], ans[:1])
check("an unknown address in an address-less rev-server zone is answered NXDOMAIN at home",
      len(ans) > 1 and "NXDOMAIN" in ans[1], ans[1:2])
out2, _ = run(["hostsdir=@DIR@"], 53532, [])
check("the check bites: hostsdir= (r26) is refused at startup by this -DNO_INOTIFY build",
      "not supported on this platform" in out2 or "FAILED to start up" in out2, out2[-300:])

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("all checks passed: the shipped dnsmasq starts with Reaper's directives and refuses what it cannot run")
