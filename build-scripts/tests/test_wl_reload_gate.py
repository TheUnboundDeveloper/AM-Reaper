#!/usr/bin/env python3
"""Host test for the Wi-Fi driver reload gate in restart_wireless()
(release/src/router/rc/lan.c, reaper_ed_reload_gate(); field report 2026-10-28,
RT-BE86U: a Guest Network Pro save reloaded wl.ko + dhd.ko live and the 5 GHz
dongle stayed "wl driver adapter not found" until a power cycle).

ASUS's closed reload_wl_check() reloads the Wi-Fi drivers when init_nvram()
has set ed_thresh_reload. The gate runs right before it and keeps the drivers
loaded unless the energy-detect MODE (no_dy_ed_thresh_ctrl) changed in this init_nvram() call.

The gate is compiled from the real lan.c text against a stub nvram. Checked:
  - flag clear: nothing written, nothing logged;
  - flag set, mode unchanged (normal 0 -> 0, debug -1 -> -1): flag cleared, logged;
  - flag set, mode changed (0 -> -1, -1 -> 0): flag kept (stock reload), logged;
  - restart_wireless(): the mode is read before init_nvram() and the gate is the
    statement right before reload_wl_check(), under the same model list as the
    gate's own #if;
  - the closed object still keys on ed_thresh_reload (else the gate is stale);
  - two mutants (gate never clears; gate ignores the mode) must fail.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile


def skip(msg):
    print("SKIP: " + msg); sys.exit(77)


def die(msg):
    print("FAIL: " + msg); sys.exit(1)


src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
lan = os.path.join(src_root, "rc", "lan.c") if src_root else ""
if not lan or not os.path.isfile(lan):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no C compiler")
L = open(lan, encoding="utf-8").read()

# ---- the gate's own block: #if <list> / #define REAPER_ED_RELOAD_GATE ... #endif
m = re.search(r"#if ([^\n]+)\n#define REAPER_ED_RELOAD_GATE\n(.*?)\n#endif\n", L, re.S)
if not m:
    die("lan.c has no REAPER_ED_RELOAD_GATE block - the driver reload gate is missing")
gate_list, gate_body = m.group(1).strip(), m.group(2)
if "static void reaper_ed_reload_gate(int mode_old)" not in gate_body:
    die("REAPER_ED_RELOAD_GATE block does not define reaper_ed_reload_gate(int mode_old)")

# ---- restart_wireless(): snapshot before init_nvram(), gate right before reload_wl_check()
f = L.find("\nvoid restart_wireless(void)\n{")
if f < 0:
    die("lan.c: restart_wireless() not found")
end = L.find("\n}\n", f)
fn = L[f:end]
snap = fn.find('int ed_mode_old = nvram_get_int("no_dy_ed_thresh_ctrl");')
initn = fn.find("init_nvram();")
if snap < 0:
    die("restart_wireless(): the ED mode is not read before the teardown (ed_mode_old)")
if initn < 0 or snap > initn:
    die("restart_wireless(): ed_mode_old must be read BEFORE init_nvram() recomputes the mode")
cs = re.search(r"#if ([^\n]+)\n\treaper_ed_reload_gate\(ed_mode_old\);[^\n]*\n\treload_wl_check\(\);\n#endif", fn)
if not cs:
    die("restart_wireless(): reaper_ed_reload_gate(ed_mode_old) must be the statement right before reload_wl_check()")
if cs.group(1).strip() != gate_list:
    die("the gate's model list differs from reload_wl_check()'s call-site list:\n  gate: %s\n  call: %s"
        % (gate_list, cs.group(1).strip()))
if fn.count("reload_wl_check();") != 1:
    die("restart_wireless(): expected exactly one reload_wl_check() call")

# ---- the closed side still keys on the same flag
po = os.path.join(src_root, "rc", "prebuild", "RT-BE86U", "private.o")
if os.path.isfile(po):
    b = open(po, "rb").read()
    if b"reload_wl_check" not in b or b"ed_thresh_reload" not in b:
        die("RT-BE86U private.o: reload_wl_check / ed_thresh_reload not found - the gate may be stale")

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
static char k1[64][64], v1[64][64]; static int nk;
static char logbuf[4096];
static int find(const char *k){ for (int i = 0; i < nk; i++) if (!strcmp(k1[i], k)) return i; return -1; }
int nvram_get_int(const char *k){ int i = find(k); return i < 0 ? 0 : atoi(v1[i]); }
int nvram_set_int(const char *k, int v){ int i = find(k); if (i < 0) { i = nk++; strcpy(k1[i], k); } sprintf(v1[i], "%d", v); return 0; }
void logmessage(const char *tag, const char *fmt, ...){ va_list a; va_start(a, fmt); char t[512]; vsnprintf(t, sizeof t, fmt, a); va_end(a);
	strcat(logbuf, tag); strcat(logbuf, ": "); strcat(logbuf, t); strcat(logbuf, "\n"); }
GATE_BODY
int main(int argc, char **argv){
	/* argv: <flag> <mode_old> <mode_new> */
	nvram_set_int("ed_thresh_reload", atoi(argv[1]));
	nvram_set_int("no_dy_ed_thresh_ctrl", atoi(argv[3]));
	reaper_ed_reload_gate(atoi(argv[2]));
	printf("FLAG=%d\n%s", nvram_get_int("ed_thresh_reload"), logbuf);
	return 0;
}
'''


def build(body, tmp, name):
    c = os.path.join(tmp, name + ".c"); x = os.path.join(tmp, name)
    open(c, "w").write(HARNESS.replace("GATE_BODY", body))
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Werror", "-o", x, c], capture_output=True, text=True)
    if r.returncode:
        die("compile %s:\n%s" % (name, r.stderr))
    return x


def run(x, flag, old, new):
    return subprocess.run([x, str(flag), str(old), str(new)], capture_output=True, text=True).stdout


def check(x):
    errs = []
    o = run(x, 0, 0, 0)
    if "FLAG=0" not in o or "reaper" in o: errs.append("flag clear must stay clear and log nothing: %r" % o)
    for old, new in ((0, 0), (-1, -1)):
        o = run(x, 1, old, new)
        if "FLAG=0" not in o or "kept loaded" not in o:
            errs.append("mode %d -> %d unchanged: the reload must be dropped and logged: %r" % (old, new, o))
    for old, new in ((0, -1), (-1, 0)):
        o = run(x, 1, old, new)
        if "FLAG=1" not in o or "mode changed" not in o:
            errs.append("mode %d -> %d changed: the stock reload must stand and be logged: %r" % (old, new, o))
    return errs


tmp = tempfile.mkdtemp(prefix="wlgate")
try:
    errs = check(build(gate_body, tmp, "real"))
    if errs:
        die("; ".join(errs))
    mutants = {
        "never clears": gate_body.replace('nvram_set_int("ed_thresh_reload", 0);', ""),
        "ignores the mode": gate_body.replace("if (mode_old != nvram_get_int(\"no_dy_ed_thresh_ctrl\")) {", "if (0) {"),
    }
    for name, body in mutants.items():
        if body == gate_body:
            die("mutant '%s' did not apply - the test no longer matches the gate's text" % name)
        if not check(build(body, tmp, "mut")):
            die("mutant '%s' passed - the checks are too weak" % name)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("PASS: driver reload gate (4 cases, call order, model lists, closed-object pin, 2 mutants)")
