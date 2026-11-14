#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wanduck re-kicks native IPv6 once the internet comes back after an outage (2026-11-12).

WHY THIS EXISTS. Field report: after an ISP outage IPv4 came back but native IPv6 never did, until
the WAN was toggled or the cable replugged. odhcp6c is started only from wan6_up() on a fresh DHCPv4
bound; with the WAN link up through the outage IPv4 merely renews, so nothing touched IPv6 again:
odhcp6c sat in its Solicit back-off (the server's SOL_MAX_RT persists in the process) or held a bind
without a prefix, and rdisc6 had long exited. wanduck's D2C path only redid NAT and resolv.conf.

WHAT IT DOES. Takes reaper_v6_mark_down()/reaper_v6_kick() out of rc/wanduck.c, compiles them on the
host against stubs and runs the decisions: boot (no prior outage) does nothing; one outage = one
kick; SIGUSR1 normally, SIGUSR2 when DHCP-PD is on and no prefix is held, start_dhcp6c when odhcp6c
is not running; always start_rdisc6; not for the non-IPv6 unit, not outside router mode, not for
6in4/6rd/static/disabled; at most once a minute. Then pins the two call sites: the mark inside the
C2D branch's braces (C2D only), the kick at the top of the D2C/CONNED branch, both under
RTCONFIG_IPV6. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router tree - argv[1] or
REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WD = os.path.join(SRC, "rc", "wanduck.c") if SRC else ""
if not WD or not os.path.isfile(WD):
    skip("no router tree with rc/wanduck.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(WD, encoding="utf-8", errors="surrogateescape").read()
m = re.search(r"static int reaper_v6_down\[WAN_UNIT_MAX\];.*?\nstatic void reaper_v6_kick\(int wan_unit\)\n\{.*?\n\}\n", src, re.S)
check("wanduck.c carries reaper_v6_mark_down() and reaper_v6_kick()", m is not None)
if not m:
    print("\n1 check failed"); sys.exit(1)

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#define RTCONFIG_IPV6 1
#define RTCONFIG_6RELAYD 1
#define WAN_UNIT_MAX 3
#define SW_MODE_ROUTER 1
#define SW_MODE_AP 3
enum { IPV6_DISABLED, IPV6_NATIVE_DHCP, IPV6_6TO4, IPV6_6IN4, IPV6_6RD, IPV6_MANUAL, IPV6_PASSTHROUGH };
static int sw_mode = SW_MODE_ROUTER, v6unit = 0, service = IPV6_NATIVE_DHCP, running = 1, pd = 1;
static const char *prefix = "2001:db8:1::";
static long now_s = 1000;
static long uptime(void) { return now_s; }
static int wan_primary_ifunit_ipv6(void) { return v6unit; }
static int get_ipv6_service(void) { return service; }
static int pidof(const char *n) { return (running && !strcmp(n, "odhcp6c")) ? 123 : -1; }
static int killall(const char *n, int sig) { printf("kill %s %s\n", n, sig == SIGUSR2 ? "USR2" : sig == SIGUSR1 ? "USR1" : "OTHER"); return 0; }
static int notify_rc(const char *e) { printf("rc %s\n", e); return 0; }
static void logmessage(const char *h, const char *f, ...) { (void)h; (void)f; }
static const char *ipv6_nvname(const char *n) { return n; }
static int nvram_get_int(const char *n) { return !strcmp(n, "ipv6_dhcp_pd") ? pd : 0; }
static const char *nvram_safe_get(const char *n) { return !strcmp(n, "ipv6_prefix") ? prefix : ""; }
@@KICK@@
int main(int argc, char **argv)
{
	int a;
	for (a = 1; a < argc; a++) {
		char *s = argv[a];
		switch (s[0]) {
		case 'D': reaper_v6_mark_down(atoi(s + 1)); break;	/* C2D on unit */
		case 'U': reaper_v6_kick(atoi(s + 1)); break;		/* D2C/CONNED tick on unit */
		case 't': now_s += atol(s + 1); break;
		case 'm': sw_mode = atoi(s + 1); break;
		case 'v': v6unit = atoi(s + 1); break;
		case 's': service = atoi(s + 1); break;
		case 'r': running = atoi(s + 1); break;
		case 'p': pd = atoi(s + 1); break;
		case 'x': prefix = ""; break;
		}
		printf("|\n");
	}
	return 0;
}
'''
tmp = tempfile.mkdtemp()
try:
    c = os.path.join(tmp, "k.c"); exe = os.path.join(tmp, "k")
    open(c, "w").write(HARNESS.replace("@@KICK@@", m.group(0)))
    r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
    check("the extracted functions compile cleanly with -Wall -Werror", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n%d check(s) failed" % len(fails)); sys.exit(1)

    def run(*args):
        out = subprocess.run([exe] + list(args), capture_output=True, text=True).stdout
        return [x.strip().split("\n") if x.strip() else [] for x in out.split("|")][:-1]

    def acts(*args):
        """all actions of the run, flattened"""
        return [y for x in run(*args) for y in x]

    check("boot: a first connection with no outage before it does nothing", acts("U0", "U0", "U0") == [])
    check("one outage = one kick: SIGUSR1 to odhcp6c + start_rdisc6, then quiet on later ticks",
          run("D0", "U0", "U0", "U0") == [[], ["kill odhcp6c USR1", "rc start_rdisc6"], [], []])
    check("DHCP-PD on and no prefix held: SIGUSR2 (a full new transaction) instead",
          acts("x", "D0", "U0") == ["kill odhcp6c USR2", "rc start_rdisc6"])
    check("DHCP-PD off and no prefix: still only SIGUSR1 (nothing to re-request)",
          acts("p0", "x", "D0", "U0") == ["kill odhcp6c USR1", "rc start_rdisc6"])
    check("odhcp6c not running: start_dhcp6c (+ start_rdisc6), no signal",
          acts("r0", "D0", "U0") == ["rc start_dhcp6c", "rc start_rdisc6"])
    check("Passthrough: SIGUSR1 even without a prefix (SIGUSR2 is for native DHCP-PD only)",
          acts("s6", "x", "D0", "U0") == ["kill odhcp6c USR1", "rc start_rdisc6"])
    check("not the IPv6 unit (dual WAN, IPv6 on unit 0, outage on unit 1): nothing",
          acts("D1", "U1") == [])
    check("an outage on another unit does not arm this one", acts("D1", "U0") == [])
    check("AP mode: nothing", acts("m3", "D0", "U0") == [])
    for sv, nm in ((0, "disabled"), (3, "6in4"), (4, "6rd"), (5, "static")):
        check("IPv6 %s: nothing" % nm, acts("s%d" % sv, "D0", "U0") == [])
    check("rate limit: a second outage within 60 s is consumed without a kick; after 60 s it kicks again",
          run("D0", "U0", "t30", "D0", "U0", "t61", "D0", "U0") ==
          [[], ["kill odhcp6c USR1", "rc start_rdisc6"], [], [], [], [], [], ["kill odhcp6c USR1", "rc start_rdisc6"]])
    check("an out-of-range unit is ignored", acts("D7", "U7", "D-1", "U-1") == [])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- call sites
c2d = "\t\telse if(conn_changed_state[current_wan_unit] == C2D || (conn_changed_state[current_wan_unit] == CONNED && isFirstUse)){\n"
d2c = "\t\telse if(conn_changed_state[current_wan_unit] == D2C || conn_changed_state[current_wan_unit] == CONNED){\n"
check("the mark sits first inside the C2D branch's braces, C2D only, under RTCONFIG_IPV6",
      src.count(c2d + "#ifdef RTCONFIG_IPV6\n\t\t\tif(conn_changed_state[current_wan_unit] == C2D)\n"
                "\t\t\t\treaper_v6_mark_down(current_wan_unit);") == 1)
check("the kick sits first inside the D2C/CONNED branch's braces, under RTCONFIG_IPV6",
      src.count(d2c + "#ifdef RTCONFIG_IPV6\n\t\t\treaper_v6_kick(current_wan_unit);") == 1)
check("exactly one call site each", src.count("reaper_v6_mark_down(current_wan_unit);") == 1
      and src.count("reaper_v6_kick(current_wan_unit);") == 1)
check("the definitions are under RTCONFIG_IPV6 and above set_link_internet()",
      src.find("#ifdef RTCONFIG_IPV6\n/* reaper 2026-11-12 (field report: native IPv6") < src.find("static void reaper_v6_kick(int wan_unit)")
      < src.find("void set_link_internet(int wan_unit, int link_internet){"))
check("the kick never blocks wanduck (notify_rc, not the _and_wait variants, inside reaper_v6_kick)",
      "notify_rc_and_wait" not in m.group(0) and "start_dhcp6c();" not in m.group(0) and "start_rdisc6();" not in m.group(0))

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
