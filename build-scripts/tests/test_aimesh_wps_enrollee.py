#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The AiMesh join of a factory box gets WPS on its onboarding band (2026-10-16).

WHY THIS EXISTS. Reaper ships WPS off (wps_enable / wps_enable_x "0", v2.0.4);
stock ships it on. generate_wl_para() (rc/sysdeps/init-broadcom.c) computes each
radio's wps_mode with every arm nested inside wps_enable == "1" - including the
arm stock uses while an unconfigured router-mode box enrolls into an AiMesh
system (amesh_wps_enr, set by the rc "wps_enr" service, unset at every boot in
rc/init.c). A factory Reaper box asked to join a mesh therefore had WPS disabled
on its onboarding band. Field: a ZenWiFi BQ16 on Reaper would not join a GT-BE98
main router with MLO on, while the same unit on stock firmware joined.

THE FIX. reaper_amesh_wps_enrollee() ORs that one arm back in, on its own: an
unconfigured (x_Setting 0) router-mode box that is not a node, while
amesh_wps_enr is set, on the band the stock arm names. It never writes
wps_enable / wps_enable_x, so the user's setting is untouched and the window
closes with the reboot that ends the join.

WHAT IT DOES.
  A. Extracts the real helper from init-broadcom.c, compiles it on the host
     against stub nvram / is_router_mode / logmessage, and runs a truth table.
  B. Static checks: the helper is ORed into the wps_mode rule under the same
     guards, the stock expression is otherwise intact, the helper writes no
     nvram, the factory default stays WPS off, amesh_wps_enr is still unset at
     boot, and the marker string is present.

Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC,
or no host C compiler).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "rc")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        die("missing %s" % rel)
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

ib = read("rc/sysdeps/init-broadcom.c")
MARK = "WPS on for the AiMesh join of this factory box (the WPS setting itself stays off)"

# ---- B. static ----------------------------------------------------------------
m = re.search(r'#if defined\(RTCONFIG_AMAS\) && defined\(RTCONFIG_PROXYSTA\)\n(/\*.*?\*/\n)?'
              r'static int reaper_amesh_wps_enrollee\(int unit\)\n\{\n(.*?)\n\}\n#endif\n', ib, re.S)
if not m:
    die("reaper_amesh_wps_enrollee() not found under #if RTCONFIG_AMAS && RTCONFIG_PROXYSTA")
body = m.group(2)
ok("helper present under the stock arm's guards")
if re.search(r'nvram_(set|unset|commit)', body):
    die("the helper writes nvram - it must only read")
ok("helper only reads nvram (the user's WPS setting is never written)")
if MARK not in body:
    die("marker log line missing from the helper")
ok("marker log line present")

w = ib.find('nvram_set(strcat_r(p, "wps_mode", tmp), ((nvram_match("wps_enable", "1") && (is_ap(unit)')
if w < 0:
    die("wps_mode rule head not found (outer paren for the OR)")
seg = ib[w:w + 1600]
tail = seg.find('? "enabled" : "disabled");')
if tail < 0:
    die("wps_mode rule tail not found")
seg = seg[:tail]
if "|| reaper_amesh_wps_enrollee(unit)" not in seg:
    die("helper not ORed into the wps_mode rule")
if not re.search(r'\)\)\n#if defined\(RTCONFIG_AMAS\) && defined\(RTCONFIG_PROXYSTA\)\n.*\n\t*\|\| reaper_amesh_wps_enrollee\(unit\)\n#endif\n\t*\) $', seg, re.S):
    die("the OR is not the last term of the rule, inside its own #if")
for stock in ('|| (is_router_mode() && nvram_get_int("amesh_wps_enr"))',
              '((unit == WL_2G_BAND) || unit == nvram_get_int("wps_band_x"))',
              '|| is_dpsta(unit)'):
    if stock not in seg:
        die("stock wps_mode arm changed: " + stock)
ok("stock wps_mode arms intact; the helper is one extra OR term")
if seg.count("(") != seg.count(")") + 1:   # +1: nvram_set( is closed after the ternary
    die("parenthesis balance of the wps_mode rule looks wrong")
ok("wps_mode rule parentheses balance")

dflt = read("shared/defaults.c")
for k in ("wps_enable", "wps_enable_x"):
    vals = re.findall(r'\{\s*"%s"\s*,\s*"([^"]*)"' % k, dflt)
    if not vals or any(v != "0" for v in vals):
        die("factory default %s is not \"0\" everywhere: %s" % (k, vals))
ok("factory default WPS stays off (wps_enable / wps_enable_x \"0\")")
if 'nvram_unset("amesh_wps_enr");' not in read("rc/init.c"):
    die("rc/init.c no longer unsets amesh_wps_enr at boot - the join window would outlive a reboot")
ok("amesh_wps_enr still unset at every boot (the window cannot outlive a reboot)")
if 'nvram_set_int("amesh_wps_enr", 1);' not in read("rc/services.c"):
    die("rc/services.c wps_enr service no longer sets amesh_wps_enr")
ok("the wps_enr service still opens the window")

# ---- A. compile the real helper and run a truth table -----------------------------
cc = shutil.which("gcc") or shutil.which("cc")
if not cc:
    skip("no host C compiler for the truth table (static checks passed)")

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define RTCONFIG_AMAS 1
#define RTCONFIG_PROXYSTA 1
#define WL_2G_BAND 0
#define WL_5G_BAND 1
static const char *nv_key[16]; static const char *nv_val[16]; static int nv_n;
static void nv(const char *k, const char *v) { nv_key[nv_n] = k; nv_val[nv_n++] = v; }
static const char *nvram_safe_get(const char *k) { for (int i = 0; i < nv_n; i++) if (!strcmp(nv_key[i], k)) return nv_val[i]; return ""; }
static int nvram_match(const char *k, const char *v) { return !strcmp(nvram_safe_get(k), v); }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static char *strcat_r(const char *a, const char *b, char *buf) { strcpy(buf, a); strcat(buf, b); return buf; }
static int g_router = 1, g_logs = 0;
static int is_router_mode(void) { return g_router; }
static void logmessage(const char *t, const char *fmt, ...) { (void)t; (void)fmt; g_logs++; }
@HELPER@
struct row { const char *name; int router, unit; const char *wps, *xs, *re, *enr, *band; int want; };
int main(void) {
	struct row t[] = {
		{"factory join, 2.4 GHz",            1, 0, "0", "0", "0", "1", "0", 1},
		{"factory join, wps_band_x unit",    1, 3, "0", "0", "0", "1", "3", 1},
		{"factory join, other band",         1, 1, "0", "0", "0", "1", "0", 0},
		{"factory, no join running",         1, 0, "0", "0", "0", "",  "0", 0},
		{"configured box (x_Setting 1)",     1, 0, "0", "1", "0", "1", "0", 0},
		{"already a node (re_mode 1)",       1, 0, "0", "0", "1", "1", "0", 0},
		{"not router mode (AP/repeater)",    0, 0, "0", "0", "0", "1", "0", 0},
		{"user WPS on: stock rule covers it",1, 0, "1", "0", "0", "1", "0", 0},
	};
	int fail = 0;
	for (unsigned i = 0; i < sizeof(t) / sizeof(t[0]); i++) {
		nv_n = 0; g_router = t[i].router; g_logs = 0;
		nv("wps_enable", t[i].wps); nv("x_Setting", t[i].xs); nv("re_mode", t[i].re);
		nv("amesh_wps_enr", t[i].enr); nv("wps_band_x", t[i].band);
		int got = reaper_amesh_wps_enrollee(t[i].unit);
		int bad = got != t[i].want || (got && g_logs != 1) || (!got && g_logs);
		printf("%s %-36s got %d want %d logs %d\n", bad ? "BAD " : "ok  ", t[i].name, got, t[i].want, g_logs);
		fail |= bad;
	}
	return fail;
}
'''
helper_src = "static int reaper_amesh_wps_enrollee(int unit)\n{\n" + body + "\n}\n"
tmp = tempfile.mkdtemp(prefix="wpsenr_")
try:
    c = os.path.join(tmp, "t.c")
    with open(c, "w") as f:
        f.write(harness.replace("@HELPER@", helper_src))
    exe = os.path.join(tmp, "t")
    r = subprocess.run([cc, "-std=gnu99", "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, c],
                       capture_output=True, text=True)
    if r.returncode:
        die("harness did not compile:\n" + r.stderr)
    r = subprocess.run([exe], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode:
        die("truth table")
    ok("truth table: on only for a factory router-mode box joining, on the onboarding band")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("PASS")
