#!/usr/bin/env python3
"""test_amaspark_vif.py - AiMesh backhaul parking holds the carriers up while a client network is down (2026-10-25).

WHY. Field (RT-BE88U tester): the Wireless Scheduler turned the networks back on at the end of their off window, the
log said so, yet no SSID was broadcast until a reboot. The scheduler raises a client network with the driver's bss
iovar (`wl bss -C <n> up` on wlN.M). Backhaul parking (rc/amaspark.c, opt-in) keeps the radio's PRIMARY BSS down, and
its safety proof only covered client networks that were already up when the primary went down - never bringing one up
under a parked primary. Now a client network that is enabled in the settings but down on the air keeps every carrier
up until it is back, so its bring-up happens as on stock firmware; parking resumes a minute after every client network
is up again (the proven case).

WHAT IT DOES. Lifts vif_down() out of rc/amaspark.c and runs it against a stub nvram and stub interface states; pins
how the daemon's loop uses it (hold, release reason, one log line each way, the settle delay) and that the bss-state
cache is wide enough for the client networks. Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "rc", "amaspark.c") if SRC else ""
if not P or not os.path.isfile(P):
    print("SKIP: no router source tree with rc/amaspark.c"); sys.exit(77)
t = open(P, encoding="utf-8", errors="replace").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond or not detail else "  " + str(detail)[:400]))
    if not cond: fails.append(name)

check("the bss-state cache holds the primaries AND their client networks (24 interfaces, not 4)",
      "#define AP_MAXIF\t24" in t and "seen[AP_MAXIF];" in t and "if (i == AP_MAXIF)" in t)
check("loop: a down client network holds the carriers up and releases any parked one, naming it (one log line)",
      "if (want || vheld) {" in t and 'logmessage(AP_TAG, "holding the backhaul carriers up: %s", vbuf);' in t
      and "want = 0;\n\t\t\t\twhy_rel = vbuf;" in t)
check("loop: once every client network is up, parking resumes after a settle (one log line)",
      "settle_until = now + AP_VIF_SETTLE;" in t and '"every client network is up again - parking resumes in %d s"' in t
      and "#define AP_VIF_SETTLE\t60" in t)
check("the check sits before the parking pass (a parked carrier is never kept parked under a down client network)",
      t.find("if (want || vheld) {") < t.find("if (want) {\n\t\t\tint acted = 0;"))

m = re.search(r"static int vif_down\(int u, char \*out, size_t n\)\n\{.*?\n\}\n", t, re.S)
check("vif_down() is found", bool(m))
gcc = shutil.which("gcc")
if m and gcc:
    drv = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define IFNAMSIZ 16
static size_t strlcpy(char *d, const char *s, size_t n){ size_t l = strlen(s); if (n){ size_t k = l >= n ? n - 1 : l; memcpy(d, s, k); d[k] = 0; } return l; }
static const char *NV[][2] = { {"wl0_vifs", "wl0.1 wl0.2 wl0.3"}, {"wl0.1_bss_enabled", "1"}, {"wl0.2_bss_enabled", "0"}, {"wl0.3_bss_enabled", "1"},
	{"wl1_vifs", "wl1.1 averyveryverylongifname"}, {"wl1.1_bss_enabled", "1"}, {"averyveryverylongifname_bss_enabled", "1"},
	{"wl2_vifs", ""}, {0, 0} };
static char *nvram_safe_get(const char *k){ int i; for (i = 0; NV[i][0]; i++) if (!strcmp(NV[i][0], k)) return (char *)NV[i][1]; return ""; }
static int nvram_match(const char *k, const char *v){ return !strcmp(nvram_safe_get(k), v); }
static const char *DOWN;	/* space-separated interfaces that are down */
static int bss_state(const char *ifn){ char b[64]; snprintf(b, sizeof(b), " %s ", ifn); return strstr(DOWN, b) ? 0 : 1; }
''' + m.group(0) + r'''
int main(void){
	char o[IFNAMSIZ];
	const char *cases[] = { " ", " wl0.2 ", " wl0.3 ", " wl0.1 wl0.3 ", " wl1.1 ", " averyveryverylongifname ", 0 };
	int i, u;
	for (i = 0; cases[i]; i++) {
		DOWN = cases[i];
		printf("[%s]", cases[i]);
		for (u = 0; u < 3; u++) { o[0] = 0; printf(" %d:%d:%s", u, vif_down(u, o, sizeof(o)), o); }
		printf("\n");
	}
	return 0;
}
'''
    td = tempfile.mkdtemp(prefix="apvif_")
    try:
        open(os.path.join(td, "v.c"), "w").write(drv)
        b = subprocess.run([gcc, "-Wall", "-Werror", "-Wno-unused-function", "-o", os.path.join(td, "v"), os.path.join(td, "v.c")], capture_output=True, text=True)
        check("vif_down(): compiles cleanly on the host", b.returncode == 0, b.stderr[-300:])
        if b.returncode == 0:
            o = subprocess.run([os.path.join(td, "v")], capture_output=True, text=True).stdout.splitlines()
            print("\n".join("     " + x for x in o))
            check("nothing down: no radio holds", o[0] == "[ ] 0:0: 1:0: 2:0:", o[0])
            check("a DISABLED client network that is down does not hold (wl0.2_bss_enabled=0)", o[1] == "[ wl0.2 ] 0:0: 1:0: 2:0:", o[1])
            check("an enabled client network that is down holds its radio and is named", o[2] == "[ wl0.3 ] 0:1:wl0.3 1:0: 2:0:", o[2])
            check("several down: the first listed is named", o[3] == "[ wl0.1 wl0.3 ] 0:1:wl0.1 1:0: 2:0:", o[3])
            check("another radio's client network is checked on its own radio only", o[4] == "[ wl1.1 ] 0:0: 1:1:wl1.1 2:0:", o[4])
            check("a name too long for an interface is ignored, never copied", o[5] == "[ averyveryverylongifname ] 0:0: 1:0: 2:0:", o[5])
    finally:
        shutil.rmtree(td, ignore_errors=True)
elif not gcc:
    print("note: no gcc - the vif_down() run is skipped")

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
