#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hardware QoS shapes the physical WAN port, never the PPP device (field, 2026-10-09).

WHY THIS EXISTS. A GT-BE98 tester on PPPoE with Hardware QoS (classful, 450 Mbps upload)
found the hardware shaper on eth0 at zero: both hardware engines took their interface from
stock get_wan_ifname(), which returns ppp0 on a PPP line, and every tmctl call on ppp0
failed (rc=108) - the Runner traffic manager has queues only on physical ports. So nothing
was shaped; classification marked packets and nothing acted on the marks.

WHAT IT DOES. Extracts hwqos_tm_ifname() (and, since 2026-10-10, the hwqos_lan_port() it
calls) from rc/qos.c (brace-matched, never copied), compiles them on the host with stubs for
nvram and the WAN helpers, and checks the port it picks for DHCP, PPPoE, PPTP, L2TP, a PPP line
with no port recorded, and an 802.1Q VLAN under the session (resolved through a
/proc/net/vlan/config fixture). Then pins that both start_hwqos() and start_hwqos_classful()
use it. The LAN-trunk refusal has its own suite, test_hwqos_lan_trunk.py.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
QOS = os.path.join(SRC, "rc", "qos.c")
if not SRC or not os.path.isfile(QOS):
    skip("no router source tree with rc/qos.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

src = open(QOS, encoding="latin-1").read()

def extract(sig):
    i = src.find(sig)
    if i < 0: return None
    j = src.find("{", i); d = 0
    for k in range(j, len(src)):
        if src[k] == "{": d += 1
        elif src[k] == "}":
            d -= 1
            if d == 0: return src[i:k + 1]
    return None

fn = extract("static const char *hwqos_tm_ifname(int unit)")
check("rc/qos.c defines hwqos_tm_ifname()", fn is not None)
if fn is None:
    print("FAILED"); sys.exit(1)
lan = extract("static int hwqos_lan_port(const char *ifname)") or ""

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <net/if.h>
#include <sys/stat.h>
#define foreach(word, wordlist, next) \
	for (next = &wordlist[strspn(wordlist, " ")], \
	     strncpy(word, next, sizeof(word)), \
	     word[strcspn(word, " ")] = '\0', \
	     word[sizeof(word) - 1] = '\0', \
	     next = strchr(next, ' '); \
	     strlen(word); \
	     next = next ? &next[strspn(next, " ")] : "", \
	     strncpy(word, next, sizeof(word)), \
	     word[strcspn(word, " ")] = '\0', \
	     word[sizeof(word) - 1] = '\0', \
	     next = strchr(next, ' '))
enum { WAN_DISABLED, WAN_DHCP, WAN_STATIC, WAN_PPPOE, WAN_PPTP, WAN_L2TP };
static int g_proto; static const char *g_pppif, *g_physif;
static const char *get_wan_ifname(int unit) { (void)unit; return g_proto >= WAN_PPPOE ? g_pppif : g_physif; }
static int get_wan_proto(char *prefix) { (void)prefix; return g_proto; }
static char *nvram_safe_get(const char *k)
{
	if (!strcmp(k, "lan_ifnames")) return (char *)"";	/* no LAN signal in this suite */
	return (char *)(strstr(k, "wan") && strstr(k, "ifname") ? g_physif : "");
}
static char *strlcat_r(const char *a, const char *b, char *buf, size_t n) { snprintf(buf, n, "%s%s", a, b); return buf; }
static int d_exists(const char *p) { struct stat st; return stat(p, &st) == 0 && S_ISDIR(st.st_mode); }
static void logmessage(const char *t, const char *fmt, ...) { (void)t; (void)fmt; }
@@LAN@@
@@FN@@
int main(int argc, char **argv)
{
	(void)argc;
	g_proto = atoi(argv[1]); g_pppif = argv[2]; g_physif = argv[3];
	printf("%s\n", hwqos_tm_ifname(0));
	return 0;
}
'''
td = tempfile.mkdtemp(prefix="hwqos.")
try:
    vlan = os.path.join(td, "vlan_config")
    with open(vlan, "w") as f:
        f.write("VLAN Dev name    | VLAN ID\nName-Type: VLAN_NAME_TYPE_RAW_PLUS_VID_NO_PAD\nvlan101        | 101  | eth0\n")
    sysnet = os.path.join(td, "sysnet"); os.makedirs(sysnet)
    c = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    with open(c, "w") as f: f.write(HARNESS.replace("@@LAN@@", lan).replace("@@FN@@", fn))
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", '-DHWQOS_VLAN_CFG="%s"' % vlan,
                        '-DHWQOS_SYSNET="%s"' % sysnet, "-o", exe, c],
                       capture_output=True, text=True)
    check("the helper compiles warning-free on the host", p.returncode == 0, p.stderr[-500:])
    if p.returncode == 0:
        def pick(proto, ppp, phys):
            return subprocess.run([exe, str(proto), ppp, phys], capture_output=True, text=True).stdout.strip()
        check("DHCP WAN: shapes eth0", pick(1, "ppp0", "eth0") == "eth0")
        check("PPPoE WAN: shapes eth0, not ppp0 (the field report)", pick(3, "ppp0", "eth0") == "eth0")
        check("PPTP WAN: shapes the port under it", pick(4, "ppp0", "eth0") == "eth0")
        check("L2TP WAN: shapes the port under it", pick(5, "ppp0", "eth0") == "eth0")
        check("PPP line with no port recorded: falls back to what stock gives (no worse than before)", pick(3, "ppp0", "") == "ppp0")
        check("PPPoE over an 802.1Q VLAN: the VLAN's parent port is shaped", pick(3, "ppp0", "vlan101") == "eth0")
        check("a VLAN name that is not in the table is left as it is", pick(1, "ppp0", "eth0.v0") == "eth0.v0")
finally:
    shutil.rmtree(td, ignore_errors=True)

def body(name):
    b = extract("int %s(void)" % name)
    return b or ""
for eng in ("start_hwqos", "start_hwqos_classful"):
    b = body(eng)
    check("%s() takes its port from hwqos_tm_ifname()" % eng,
          "= hwqos_tm_ifname(wan_primary_ifunit())" in b and "get_wan_ifname(" not in b)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: both hardware QoS engines program the physical WAN port, on PPP lines too")
