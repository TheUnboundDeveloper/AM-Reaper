#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hardware QoS never shapes a port that also carries the LAN (field, GT-BE98 family, 2026-10-10).

WHY THIS EXISTS. v3.3.7 made hwqos_tm_ifname() resolve an 802.1Q WAN device to its parent so a
PPPoE line is shaped on its physical port. On the boards with the external 2.5G switch (GT-BE98,
GT-BE98 Pro, GT-BE96, GT-BE19000) the "2.5G WAN/LAN-1" jack is vlan4094 on eth1, and eth1 is also
LAN-2..4 and a wired AiMesh backhaul. With hardware QoS on, the whole classful program (queues
deleted and recreated, PI2, the shapers, the port shaper at the upload rate, the policer) landed on
the LAN trunk: wired LAN and backhaul throttled to the upload rate, the main router looked dead,
a wired node could not rejoin; v3.3.6 - which pointed tmctl at vlan4094 itself, refused with
rc=108 - "worked" because it was inert. Reported on three GT-BE98 Pro units on v3.3.8.

WHAT IT DOES. Extracts hwqos_lan_port() and hwqos_tm_ifname() from rc/qos.c (brace-matched),
compiles them on the host with stubs for nvram, d_exists and the WAN helpers, and checks that a
WAN VLAN whose parent is a bridge member (a brport entry under a sysfs fixture) or is listed in
lan_ifnames yields NO port, while the plain 10G WAN, a PPPoE VLAN on a dedicated port, and a VLAN
whose parent shows no LAN signal still resolve as before. Then pins the wiring: both engines
refuse to arm on an empty port, the QoS page carries the note and reads wan0_ifname, RQOS_125 is
in all 25 packs, and the markers pin the staged rc and page.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import glob, os, shutil, subprocess, sys, tempfile

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

lan = extract("static int hwqos_lan_port(const char *ifname)")
fn = extract("static const char *hwqos_tm_ifname(int unit)")
check("rc/qos.c defines hwqos_lan_port()", lan is not None)
check("rc/qos.c defines hwqos_tm_ifname()", fn is not None)
if lan is None or fn is None:
    print("FAILED"); sys.exit(1)
check("hwqos_tm_ifname() asks hwqos_lan_port() about the resolved parent and drops it",
      "hwqos_lan_port(buf)" in fn and "buf[0] = '\\0';" in fn)

# The foreach() of shared/shutils.h, verbatim semantics: split a space list into word.
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
static int g_proto; static const char *g_pppif, *g_physif, *g_lan;
static const char *get_wan_ifname(int unit) { (void)unit; return g_proto >= WAN_PPPOE ? g_pppif : g_physif; }
static int get_wan_proto(char *prefix) { (void)prefix; return g_proto; }
static char *nvram_safe_get(const char *k)
{
	if (!strcmp(k, "lan_ifnames")) return (char *)g_lan;
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
	g_proto = atoi(argv[1]); g_pppif = argv[2]; g_physif = argv[3]; g_lan = argv[4];
	printf("%s\n", hwqos_tm_ifname(0));
	return 0;
}
'''
td = tempfile.mkdtemp(prefix="hwqos-trunk.")
try:
    vlan = os.path.join(td, "vlan_config")
    with open(vlan, "w") as f:
        f.write("VLAN Dev name    | VLAN ID\nName-Type: VLAN_NAME_TYPE_RAW_PLUS_VID_NO_PAD\n"
                "vlan4094       | 4094  | eth1\nvlan101        | 101  | eth0\nvlan7          | 7  | eth9\n")
    sysnet = os.path.join(td, "sysnet")
    os.makedirs(os.path.join(sysnet, "eth9", "brport"))      # eth9: a bridge member in the kernel's view
    os.makedirs(os.path.join(sysnet, "eth1"))                # eth1: NOT a brport here - lan_ifnames decides
    os.makedirs(os.path.join(sysnet, "eth0"))
    c = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    with open(c, "w") as f:
        f.write(HARNESS.replace("@@LAN@@", lan).replace("@@FN@@", fn))
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror",
                        '-DHWQOS_VLAN_CFG="%s"' % vlan, '-DHWQOS_SYSNET="%s"' % sysnet, "-o", exe, c],
                       capture_output=True, text=True)
    check("the helpers compile warning-free on the host", p.returncode == 0, p.stderr[-600:])
    if p.returncode == 0:
        def pick(proto, ppp, phys, lan_list):
            return subprocess.run([exe, str(proto), ppp, phys, lan_list], capture_output=True, text=True).stdout.strip()
        LAN98 = "eth1 eth2 eth3 wl0 wl1 wl2 wl3"
        check("GT-BE98 family, WAN on the 2.5G WAN/LAN-1 jack (vlan4094 on eth1, eth1 in lan_ifnames): NO port",
              pick(1, "ppp0", "vlan4094", LAN98) == "")
        check("same jack on PPPoE: NO port", pick(3, "ppp0", "vlan4094", LAN98) == "")
        check("a parent that is a bridge member right now (brport) is refused even with an empty lan_ifnames",
              pick(1, "ppp0", "vlan7", "") == "")
        check("GT-BE98 family, WAN on the 10G port: eth0 is shaped as before",
              pick(1, "ppp0", "eth0", LAN98) == "eth0")
        check("PPPoE over an ISP VLAN on a dedicated WAN port: the parent is shaped (v3.3.7 behaviour kept)",
              pick(3, "ppp0", "vlan101", LAN98) == "eth0")
        check("a VLAN parent with no LAN signal at all still resolves (the refusal is signal-driven, not name-driven)",
              pick(1, "ppp0", "vlan4094", "eth2 eth3") == "eth1")
        check("a plain port never in the table is left as it is", pick(1, "ppp0", "eth0.v0", LAN98) == "eth0.v0")
finally:
    shutil.rmtree(td, ignore_errors=True)

# ---------------------------------------------------------------- wiring
def body(name):
    return extract("int %s(void)" % name) or ""
for eng in ("start_hwqos", "start_hwqos_classful"):
    b = body(eng)
    check("%s() refuses to arm with no port and says so" % eng,
          "if (!*wan_ifname) {" in b and "hardware QoS not started: no port to shape" in b
          and b.find("if (!*wan_ifname) {") < b.find('fopen(qosfn, "w")'))
page = open(os.path.join(SRC, "www", "Reaper_QoS.asp"), encoding="utf-8", errors="replace").read()
check("QoS page: the note sits by the engine choice, hidden until wan0_ifname is a vlanNNNN device",
      'id="rqos_trunknote"' in page and "<#RQOS_125#>" in page
      and "wanif:   '<% nvram_get(\"wan0_ifname\"); %>'" in page
      and "/^vlan[0-9]+$/.test(NV.wanif)" in page
      and page.find('id="modes"') < page.find('id="rqos_trunknote"'))
packs = [x for x in glob.glob(os.path.join(SRC, "www", "*.dict")) if not x.endswith("temp.dict")]
miss = [os.path.basename(x) for x in packs if "RQOS_125=" not in open(x, encoding="utf-8", errors="replace").read()]
check("RQOS_125 exists in all 25 language packs", len(packs) == 25 and not miss, miss)
counts = set(open(x, "rb").read().count(b"\n") for x in packs)
check("the 25 packs stay in lockstep", len(counts) == 1, counts)
here = os.path.dirname(os.path.abspath(__file__))
mp = os.path.join(here, "..", "verify_markers.txt")
if os.path.isfile(mp):
    m = open(mp, encoding="utf-8").read()
    check("verify_markers pins the refusal in the staged rc and the note in the staged page",
          "sbin/rc|also carries the LAN ports|1" in m and "www/Reaper_QoS.asp|rqos_trunknote|1" in m)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: a WAN VLAN on a LAN trunk is never shaped; dedicated ports shape as before")
