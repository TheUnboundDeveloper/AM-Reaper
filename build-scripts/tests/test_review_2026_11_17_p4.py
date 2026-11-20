#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-17, remediation phase 4 (one copy of what was copied): pins for each fold as it lands.

WHY THIS EXISTS. The review found readers of the same data that had drifted apart. The first fold is the one
with a field report behind it: the Devices page read the main network's lease file only, and showed a lease's
address for as long as the lease lived even after the device had been given another address by hand. The shared
neighbour reader now serves IPv4 too and says which entries are FRESH (the kernel has heard from the address
lately - /proc/net/arp cannot tell that: its "complete" flag is set for a stale entry as well).

WHAT IT DOES. Compiles shared/reaper_nd.c on the host; runs the "which address is this MAC using now" rule over a
table; where a network namespace is available, makes real neighbour entries in each state and reads them back
through both loaders (the IPv6 one was rewritten onto the shared dump routine); reads rdev_collect in httpd/web.c.
Exit 0 pass, 1 fail, 77 skipped (no router source tree or no C compiler)."""
import os, re, shutil, subprocess, sys, tempfile


def skip(msg):
    print("SKIP: " + msg); sys.exit(77)


SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "reaper_nd.c")):
    skip("no router source tree with shared/reaper_nd.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no C compiler on the host")
fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))


rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
ndc, ndh = rd(os.path.join(SRC, "shared", "reaper_nd.c")), rd(os.path.join(SRC, "shared", "reaper_nd.h"))

# ---------------------------------------------------------------- one dump routine, two families
check("neighbour reader: ONE netlink dump routine serves the IPv6 and the IPv4 loader",
      ndc.count("req.nh.nlmsg_type  = RTM_GETNEIGH;") == 1 and ndc.count("socket(AF_NETLINK") == 1
      and "nd_dump(AF_INET6, nd_fill6, &f);" in ndc and "nd_dump(AF_INET, nd_fill4, &f);" in ndc)
check("neighbour reader: fresh = REACHABLE, DELAY or PROBE - never STALE, never PERMANENT",
      "t[f->n].fresh = (state & (NUD_REACHABLE | NUD_DELAY | NUD_PROBE)) ? 1 : 0;" in ndc)
check("neighbour reader: the header declares the IPv4 table and both new functions",
      "struct reaper_nd4 {" in ndh and "int reaper_nd4_load(struct reaper_nd4 *tbl, int max);" in ndh
      and "int reaper_nd4_fresh_of(const struct reaper_nd4 *tbl, int n, const char *mac, const char *held," in ndh)

home = os.path.expanduser("~")
tmp = tempfile.mkdtemp(prefix=".rev1117p4_", dir=home if os.access(home, os.W_OK) and not home.startswith("/tmp") else os.getcwd())
try:
    src = os.path.join(tmp, "t.c")
    open(src, "w", newline="\n").write(r"""
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>
#include "reaper_nd.h"
static struct reaper_nd4 T[8]; static int N;
static void add(const char *ip, const char *mac, int fresh)
{ inet_pton(AF_INET, ip, T[N].ip); snprintf(T[N].mac, sizeof(T[N].mac), "%s", mac); snprintf(T[N].br, sizeof(T[N].br), "br0"); T[N].fresh = fresh; N++; }
static int want(const char *what, const char *mac, const char *held, int rc, const char *out)
{
	char o[INET_ADDRSTRLEN] = "";
	int r = reaper_nd4_fresh_of(T, N, mac, held, o, sizeof(o));
	if (r != rc || (rc && strcmp(o, out))) { printf("%s: got %d '%s', wanted %d '%s'\n", what, r, o, rc, out); return 1; }
	return 0;
}
int main(int argc, char **argv)
{
	int bad = 0;
	if (argc > 1 && !strcmp(argv[1], "dump")) {
		static struct reaper_nd4 t4[32]; static struct reaper_nd t6[32];
		int i, n4 = reaper_nd4_load(t4, 32), n6 = reaper_nd_load(t6, 32);
		for (i = 0; i < n4; i++) { char a[INET_ADDRSTRLEN]; inet_ntop(AF_INET, t4[i].ip, a, sizeof(a)); printf("4 %s %s %s %d\n", a, t4[i].mac, t4[i].br, t4[i].fresh); }
		for (i = 0; i < n6; i++) { char a[INET6_ADDRSTRLEN]; inet_ntop(AF_INET6, t6[i].ip, a, sizeof(a)); printf("6 %s %s %s\n", a, t6[i].mac, t6[i].br); }
		return 0;
	}
	add("192.168.50.20", "aa:bb:cc:00:00:01", 0);		/* the lease's address: stale */
	add("192.168.50.77", "aa:bb:cc:00:00:01", 1);		/* the address typed in on the device: fresh */
	add("192.168.50.30", "aa:bb:cc:00:00:02", 1);		/* a device on its lease address */
	add("192.168.50.40", "aa:bb:cc:00:00:03", 0);		/* an absent device: only a stale entry */
	add("192.168.50.41", "aa:bb:cc:00:00:03", 0);
	add("192.168.50.50", "aa:bb:cc:00:00:04", 1);		/* two fresh addresses, one of them the lease's */
	add("192.168.50.51", "aa:bb:cc:00:00:04", 1);
	bad |= want("moved by hand", "AA:BB:CC:00:00:01", "192.168.50.20", 1, "192.168.50.77");
	bad |= want("on its lease address", "aa:bb:cc:00:00:02", "192.168.50.30", 0, "");
	bad |= want("absent: stale entries only", "aa:bb:cc:00:00:03", "192.168.50.40", 0, "");
	bad |= want("two fresh, the held one among them", "aa:bb:cc:00:00:04", "192.168.50.51", 0, "");
	bad |= want("nothing held yet", "aa:bb:cc:00:00:02", "", 1, "192.168.50.30");
	bad |= want("held is not an address", "aa:bb:cc:00:00:02", "junk", 1, "192.168.50.30");
	bad |= want("unknown MAC", "aa:bb:cc:00:00:99", "192.168.50.20", 0, "");
	{ char small[8]; if (reaper_nd4_fresh_of(T, N, "aa:bb:cc:00:00:01", "", small, sizeof(small)) != 0) { puts("a buffer too small for an address was written"); bad = 1; } }
	return bad;
}
""")
    exe = os.path.join(tmp, "t")
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(SRC, "shared"), "-o", exe, src,
                        os.path.join(SRC, "shared", "reaper_nd.c")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=120)
    check("neighbour reader: compiles on the host with -Wall -Wextra -Werror", r.returncode == 0, r.stdout)
    if r.returncode == 0:
        r = subprocess.run([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
        check("rule: a MAC whose held address is not fresh while another of its addresses is -> that address; held address "
              "in use, nothing fresh, or an unknown MAC -> no change", r.returncode == 0, r.stdout)
        UNS, IP = shutil.which("unshare"), shutil.which("ip")
        if UNS and IP:
            ns = os.path.join(tmp, "ns.sh")
            open(ns, "w", newline="\n").write(
                "ip link add br0 type bridge 2>/dev/null || ip link add br0 type dummy || exit 9\n"
                "ip link add eth9 type dummy 2>/dev/null\nip link set br0 up; ip link set eth9 up 2>/dev/null\n"
                "ip addr add 10.9.0.1/24 dev br0; ip -6 addr add fd00:9::1/64 dev br0 nodad\n"
                "ip addr add 10.8.0.1/24 dev eth9 2>/dev/null\n"
                "ip neigh add 10.9.0.11 lladdr 02:00:00:00:00:11 dev br0 nud reachable || exit 9\n"
                "ip neigh add 10.9.0.12 lladdr 02:00:00:00:00:12 dev br0 nud stale\n"
                "ip neigh add 10.9.0.13 lladdr 02:00:00:00:00:13 dev br0 nud permanent\n"
                "ip neigh add 10.9.0.14 lladdr 02:00:00:00:00:14 dev br0 nud delay\n"
                "ip neigh add 10.8.0.15 lladdr 02:00:00:00:00:15 dev eth9 nud reachable 2>/dev/null\n"
                "ip -6 neigh add fd00:9::21 lladdr 02:00:00:00:00:21 dev br0 nud reachable\n"
                "ip -6 neigh add fd00:9::22 lladdr 02:00:00:00:00:22 dev br0 nud stale\n"
                + exe + " dump\n")
            r = subprocess.run([UNS, "-Urn", "sh", ns], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
            rows = [l.split() for l in r.stdout.strip().split("\n") if l[:2] in ("4 ", "6 ")]
            if r.returncode == 9 or not rows:
                print("note: no usable network namespace here - the read-back of real neighbour entries is skipped (%s)" % r.stdout.strip()[:140])
            else:
                v4 = {x[1]: (x[2], x[3], x[4]) for x in rows if x[0] == "4"}
                v6 = {x[1]: (x[2], x[3]) for x in rows if x[0] == "6"}
                check("kernel read-back, IPv4: reachable and delay are fresh, stale and permanent are not, MAC and bridge are right",
                      v4.get("10.9.0.11") == ("02:00:00:00:00:11", "br0", "1") and v4.get("10.9.0.12") == ("02:00:00:00:00:12", "br0", "0")
                      and v4.get("10.9.0.13") == ("02:00:00:00:00:13", "br0", "0") and v4.get("10.9.0.14", ("", "", ""))[2] == "1", r.stdout)
                check("kernel read-back: a neighbour that is not on a bridge is not listed (the LAN side only)", "10.8.0.15" not in v4, r.stdout)
                check("kernel read-back, IPv6: the rewritten loader still returns the same entries (reachable and stale)",
                      v6.get("fd00:9::21") == ("02:00:00:00:00:21", "br0") and v6.get("fd00:9::22") == ("02:00:00:00:00:22", "br0"), r.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- the Devices collector
web = rd(os.path.join(SRC, "httpd", "web.c"))
a = web.find("static void rdev_collect(void)")
rc_ = web[a:web.find("\n}\n", a)] if a > 0 else ""
i1, i2, i2a, i2b = (rc_.find(x) for x in ("REAPER-DEV-LEASEFILES", "/* 2. ARP: devices with an IPv4 neighbour entry", "REAPER-DEV-FRESH4", "/* 2b. IPv6 A3"))
check("devices: every network's lease file is read (one rule for what a lease file is), not the main one only",
      0 < i1 < i2 and 'if (!reaper_leases_name_ok(le->d_name) || strncmp(le->d_name, "dnsmasq", 7) != 0)' in rc_
      and 'fopen("/var/lib/misc/dnsmasq.leases", "r")' not in rc_ and "closedir(ld);" in rc_)
check("devices: the fresh-address step runs after the lease and ARP steps and before presence is worked out",
      0 < i2 < i2a < i2b and "if (reaper_nd4_fresh_of(n4t, n4n, dev[i].mac, dev[i].ip, now4, sizeof(now4)))" in rc_)
check("devices: the lease and ARP steps still fill a blank only (the correction is the one place an address is replaced)",
      rc_.count('if (!dev[idx].ip[0]) snprintf(dev[idx].ip, sizeof(dev[0].ip), "%s", ip);') == 2
      and rc_.count("snprintf(dev[i].ip, sizeof(dev[0].ip)") == 1)

print()
if fails:
    print("%d check(s) FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
