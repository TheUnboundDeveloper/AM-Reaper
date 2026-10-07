#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A known WAN port is never bridged into the LAN again (stock auto-WAN-port pin).

WHY THIS EXISTS. Stock auto-WAN-port detection (RTCONFIG_AUTO_WANPORT, autowan_enable on by
default) finds the WAN by bridging every candidate port into br0 and running a DHCP client on
br0 itself; the closed restore_auto_wanport() re-does that at EVERY boot and EVERY WAN link
loss, so the ISP-facing port was a forwarding LAN-bridge member for ~35-45 s each time (owner's
RT-BE96U, 2026-10-06: link drops after boots, a new ISP subnet each time). v3.3.6 pins the port
once it is known (rc/reaper_wanpin.c): the restore calls are skipped and shared _eval() refuses
`brctl addif <bridge> <pinned port>`. The property is easy to lose silently: one new or merged
restore_auto_wanport() call without the gate brings the leak back with a green build.

WHAT IT DOES.
  - every restore_auto_wanport() call in rc/*.c outside reaper_wanpin.c sits behind
    reaper_wanpin_hold() in the same condition;
  - the boot (lan.c start_lan) and init (reconfig_manual_wan_ifnames) paths seed the pin
    before the bridge and the port lists are built; udhcpc pins right after detection;
    wanduck learns the pin and stops re-launching the prober once pinned;
  - the _eval guard exists, needs router mode + auto-detection on + Dual WAN off, and
    pretends success;
  - reaper_wanpin.c compiled on the host with stubbed nvram and a stubbed stock gate:
    nothing pins before detection; detection pins the port; a pinned port is held at boot
    and on link loss and stays "detected"; Dual WAN / AP mode (stock gate 0) never holds;
    auto-detection off clears the pin; a stale name that is no longer a candidate is
    ignored; Detect again clears the pin and runs the stock restore once;
  - the rc Makefile builds the object, the service handler exists, the marker is pinned.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import glob, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
PIN = os.path.join(SRC, "rc", "reaper_wanpin.c")
if not SRC or not os.path.isfile(PIN):
    skip("no router source tree with rc/reaper_wanpin.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

HERE = os.path.dirname(os.path.abspath(__file__))
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

# ------------------------------------------------------------------ every restore is gated
calls = []
for path in sorted(glob.glob(os.path.join(SRC, "rc", "*.c"))):
    if os.path.basename(path) == "reaper_wanpin.c":
        continue
    lines = open(path, encoding="utf-8", errors="surrogateescape").read().split("\n")
    for i, l in enumerate(lines):
        if re.search(r"\brestore_auto_wanport\s*\(\s*\)\s*;", l):
            ctx = "\n".join(lines[max(0, i - 4):i + 1])
            calls.append((os.path.basename(path), i + 1, "reaper_wanpin_hold(" in ctx))
check("found the stock restore call sites (lan.c boot + wanduck link loss x3)", len(calls) >= 4, calls)
for f, n, gated in calls:
    check("%s:%d restore_auto_wanport() is gated by reaper_wanpin_hold()" % (f, n), gated)

lan = read("rc/lan.c"); wd = read("rc/wanduck.c"); ud = read("rc/udhcpc.c"); ini = read("rc/init.c")
svc = read("rc/services.c"); mk = read("rc/Makefile"); rch = read("rc/rc.h"); sh = read("shared/shutils.c")
i_seed = lan.find("reaper_wanpin_seed();"); i_br = lan.find('eval("brctl", "addif", lan_ifname, ifname);')
check("start_lan seeds the pin before the bridge is built", 0 < i_seed < i_br, (i_seed, i_br))
check("init seeds the pin before the port lists are built",
      re.search(r"reaper_wanpin_seed\(\);[^\n]*\n\s*if\(is_auto_wanport_enabled\(\) == 2\)\n\s*snprintf\(wan_ifname", ini) is not None)
check("udhcpc pins right after DHCP detection", re.search(r"set_auto_wanport\(wan_ifname, 1\);\s*\n\s*reaper_wanpin_learn\(\);", ud) is not None)
check("wanduck learns the pin and leaves the prober alone once pinned",
      re.search(r"reaper_wanpin_learn\(\);\s*\n\s*if\(\*reaper_wanpin_get\(\)\)\s*\n\s*;\s*\n\s*else if\(current_state", wd) is not None)
check("Detect again service", '"reaper_wanredetect"' in svc and "reaper_wanpin_redetect();" in svc)
check("rc Makefile builds reaper_wanpin.o", "OBJS += reaper_wanpin.o" in mk)
check("rc.h declares the pin API", all(s in rch for s in ("reaper_wanpin_get(void)", "reaper_wanpin_hold(const char *why)", "reaper_wanpin_redetect(void)")))
g = sh[sh.find("int _eval(char *const argv[]"):]
g = g[:g.find("pid = fork();")]
check("_eval guard: brctl addif of the pinned port", '!strcmp(argv[0], "brctl") && !strcmp(argv[1], "addif")' in g and 'nvram_match("reaper_wanport", argv[3])' in g)
check("_eval guard: router mode + auto-detection on only", 'nvram_match("sw_mode", "1")' in g and 'nvram_match("autowan_enable", "1")' in g)
check("_eval guard: Dual WAN off only (wan none / wan usb)", 'nvram_match("wans_dualwan", "wan none")' in g and 'nvram_match("wans_dualwan", "wan usb")' in g)
check("_eval guard pretends success", re.search(r'refused to bridge the pinned WAN port[^;]*;\s*\n\s*return 0;', g) is not None)
mkr = open(os.path.join(HERE, "..", "verify_markers.txt"), encoding="utf-8").read()
check("build marker for the pin", "sbin/rc|pinned: it stays out of the LAN bridge|1" in mkr)

# ------------------------------------------------------------------ the state machine, on the host
body = read("rc/reaper_wanpin.c").replace('#include "rc.h"', "")
harness = r'''
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#define RTCONFIG_AUTO_WANPORT 1
#define NV 16
static char nk[NV][40], nv[NV][64]; static int nn, commits, restores, logs;
static int stock_gate = 1;	/* is_auto_wanport_enabled(): 0 = Dual WAN/AP/IPTV..., 1 = searching */
static long up = 1000;
static char *nvram_safe_get(const char *k){ for(int i=0;i<nn;i++) if(!strcmp(nk[i],k)) return nv[i]; return ""; }
static void nvram_set(const char *k,const char *v){ for(int i=0;i<nn;i++) if(!strcmp(nk[i],k)){ snprintf(nv[i],64,"%s",v); return;} snprintf(nk[nn],40,"%s",k); snprintf(nv[nn++],64,"%s",v); }
static void nvram_unset(const char *k){ nvram_set(k,""); }
static int nvram_match(const char *k,const char *v){ return !strcmp(nvram_safe_get(k),v); }
static void nvram_commit(void){ commits++; }
static int is_auto_wanport_enabled(void){ if(!stock_gate) return 0; return *nvram_safe_get("autowan_detected_ifname") ? 2 : 1; }
static void restore_auto_wanport(void){ restores++; nvram_unset("autowan_detected_ifname"); }
static long uptime(void){ return up; }
static void logmessage(const char *h,const char *f,...){ (void)h;(void)f; logs++; }
static size_t strlcpy(char *d,const char *s,size_t n){ size_t l=strlen(s); if(n){ size_t c=l<n-1?l:n-1; memcpy(d,s,c); d[c]=0;} return l; }
#define foreach(word, wordlist, next) \
	for (next = &wordlist[strspn(wordlist, " ")], strncpy(word, next, sizeof(word)), word[strcspn(word, " ")] = '\0', \
	     word[sizeof(word) - 1] = '\0', next = strchr(next, ' '); strlen(word); \
	     next = next ? &next[strspn(next, " ")] : "", strncpy(word, next, sizeof(word)), word[strcspn(word, " ")] = '\0', \
	     word[sizeof(word) - 1] = '\0', next = strchr(next, ' '))
''' + body + r'''
int main(void)
{
	nvram_set("sw_mode","1"); nvram_set("autowan_enable","1"); nvram_set("autowan_ifnames","eth0 eth1");
	printf("fresh_get [%s] hold %d\n", reaper_wanpin_get(), reaper_wanpin_hold("Boot"));
	nvram_set("autowan_detected_ifname","eth0");		/* stock detection settled */
	reaper_wanpin_learn();
	printf("learned pin [%s] commits %d\n", nvram_safe_get("reaper_wanport"), commits);
	reaper_wanpin_learn();
	printf("relearn commits %d\n", commits);
	nvram_unset("autowan_detected_ifname");			/* e.g. a reboot where detection was not saved */
	reaper_wanpin_seed();
	printf("seeded detected [%s]\n", nvram_safe_get("autowan_detected_ifname"));
	printf("hold link %d detected [%s] restores %d\n", reaper_wanpin_hold("WAN link lost"), nvram_safe_get("autowan_detected_ifname"), restores);
	int l0 = logs; reaper_wanpin_hold("WAN link lost"); reaper_wanpin_hold("WAN link lost");
	printf("hold repeat logs +%d\n", logs - l0);
	stock_gate = 0;						/* Dual WAN / AP mode / IPTV ... */
	printf("dualwan get [%s] hold %d\n", reaper_wanpin_get(), reaper_wanpin_hold("WAN link lost"));
	stock_gate = 1;
	nvram_set("reaper_wanport","eth9");			/* stale: no longer a candidate */
	printf("stale get [%s]\n", reaper_wanpin_get());
	nvram_set("reaper_wanport","eth0");
	nvram_set("autowan_enable","0");			/* user chose a fixed WAN port */
	reaper_wanpin_learn();
	printf("fixed pin [%s] get [%s]\n", nvram_safe_get("reaper_wanport"), reaper_wanpin_get());
	nvram_set("autowan_enable","1"); nvram_set("reaper_wanport","eth0"); nvram_set("autowan_detected_ifname","eth0");
	reaper_wanpin_redetect();
	printf("redetect pin [%s] restores %d detected [%s]\n", nvram_safe_get("reaper_wanport"), restores, nvram_safe_get("autowan_detected_ifname"));
	nvram_set("sw_mode","3"); nvram_set("reaper_wanport","eth0");
	printf("apmode get [%s]\n", reaper_wanpin_get());
	return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    c = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    open(c, "w").write(harness)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Wno-unused-function", "-Werror", "-o", exe, c], capture_output=True, text=True)
    check("reaper_wanpin.c compiles on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
    out = subprocess.run([exe], capture_output=True, text=True).stdout if r.returncode == 0 else ""
print(out, end="")
check("nothing is pinned or held before detection", "fresh_get [] hold 0" in out)
check("detection pins the port and commits once", "learned pin [eth0] commits 1" in out and "relearn commits 1" in out)
check("a pinned port is 'detected' from boot", "seeded detected [eth0]" in out)
check("link loss on a pinned port: held, still detected, no stock restore", "hold link 1 detected [eth0] restores 0" in out)
check("the hold log line does not repeat every scan", "hold repeat logs +0" in out)
check("Dual WAN / stock gate off: no pin, no hold", "dualwan get [] hold 0" in out)
check("a stale port name is ignored", "stale get []" in out)
check("choosing a fixed WAN port clears the pin", "fixed pin [] get []" in out)
check("Detect again clears the pin and runs the stock restore once", "redetect pin [] restores 1 detected []" in out)
check("AP mode: no pin", "apmode get []" in out)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
