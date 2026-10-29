#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The radio readers are stopped before every rc path that tears the radios down.

WHY THIS EXISTS. rpunctd arms a 4 s chanim_stats window on every Dynamic radio each tick,
reaper_bwfloor reads isup / chanspec / dfs_status every 15 s, rchqd reads chanim_stats
every 10 s. restart_wireless() has stopped the first two since v3.2.8 (GT-BE98, 2026-09-28:
a dongle trap one second into a restart_wireless). The net / allnet / net_and_phy / wps_enr
branches of handle_notifications tear the radios down WITHOUT that, and they never drop
wlready, so rpunctd's own guard was blind. Owner RT-BE96U, 2026-10-13 and 2026-10-14: a GUI
IPv6 change ran restart_net, seven seconds into the teardown both Dynamic radios' firmware
trapped (TRAP type 0x4 @ 0x80f084 on wl1 and wl2 alike) and they answered "wl driver
adapter not found" until a power cycle, with every client silently on 2.4 GHz; wl0, which no
reader touched, survived both times.

THE FIX. services.c: reaper_wl_readers_stop() (the three stops, then a wait of
REAPER_WL_WINDOW_MS + 600 ms when rpunctd was running, so an armed window closes before the
teardown) and reaper_wl_readers_start(); called right before stop_acsd() and right after
start_acsd() in every teardown branch, acsd being the stock daemon of the same class that
stock already sequences. restart_wireless() uses the same pair. shared/reaper_wlquiet.c:
reaper_wl_tearing_down() (rc_service names a radio-stopping service, whole tokens) and
reaper_wl_quiet() (that, or wlready != 1) - the readers' own check, used by rpunctd's
radio_quiet(), reaper_bwfloor's tick and rchqd's tick.

WHAT IT PINS (source, comments stripped): the two helpers and their order; every
stop_acsd()/start_acsd() inside handle_notifications paired with the helpers except in the
"acsd" branch (restart_acsd alone never touches a radio); restart_wireless() on the pair with
no bare stop_rpunctd()/start_rpunctd() left; REAPER_WL_WINDOW_MS >= rpunctd's RP_WINDOW_MS;
the predicate's service list and its whole-token match, COMPILED WITH THE HOST GCC against a
stub nvram and RUN over the cases that matter (restart_nasapps is not restart_nas,
restart_networkmap is not restart_net, a joined "start_x;restart_wireless" counts, wlready 0
counts); each reader's guard; the object in shared/Makefile.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: pass release/src/router as argv[1]
or REAPER_ROUTER_SRC). The compiled run is skipped, not failed, without a host gcc.
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
FILES = {
    "services": "rc/services.c", "lan": "rc/lan.c", "rch": "rc/rc.h", "bwfloor": "rc/reaper_bwfloor.c",
    "rpunctd": "rpunctd/rpunctd.c", "rchqd": "rchqd/rchqd.c",
    "quiet_c": "shared/reaper_wlquiet.c", "quiet_h": "shared/reaper_wlquiet.h", "shmk": "shared/Makefile",
}
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "services.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def rd(k):
    p = os.path.join(SRC, FILES[k])
    return open(p, encoding="latin-1").read() if os.path.isfile(p) else ""

def nocomment(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return "\n".join(l for l in s.splitlines() if not l.lstrip().startswith("//"))

def extract(src, sig):
    i = src.find(sig)
    if i < 0: return None
    j = src.find("{", i); d = 0
    for k in range(j, len(src)):
        if src[k] == "{": d += 1
        elif src[k] == "}":
            d -= 1
            if d == 0: return src[i:k + 1]
    return None

def norm(s): return re.sub(r"\s+", " ", s)

S = {k: nocomment(rd(k)) for k in FILES}
for k in ("quiet_c", "quiet_h"):
    check("%s exists" % FILES[k], bool(S[k]))

# ---- the helpers
fn = extract(S["services"], "reaper_wl_readers_stop(void)")
check("services.c: reaper_wl_readers_stop() found", fn is not None)
if fn:
    n = norm(fn)
    check("stop: remembers whether rpunctd was running, then stops all three readers",
          re.search(r"int armed = pids\(\"rpunctd\"\); stop_rpunctd\(\); stop_reaper_bwfloor\(\); stop_rchqd\(\);", n) is not None)
    check("stop: waits out an armed window only when rpunctd was running",
          "if (armed) {" in n and "usleep((REAPER_WL_WINDOW_MS + 600) * 1000);" in n)
    check("stop: logs either way (the diag's 19b lead)", n.count("radio readers stopped for a wireless teardown") == 2)
fn = extract(S["services"], "reaper_wl_readers_start(void)")
check("services.c: reaper_wl_readers_start() starts all three", fn is not None
      and re.search(r"start_rpunctd\(\); start_reaper_bwfloor\(\); start_rchqd\(\);", norm(fn)) is not None)
m = re.search(r"#define REAPER_WL_WINDOW_MS\s+(\d+)", S["rch"]); w_rc = int(m.group(1)) if m else -1
m = re.search(r"#define RP_WINDOW_MS\s+(\d+)", S["rpunctd"]); w_rp = int(m.group(1)) if m else -1
check("rc.h: REAPER_WL_WINDOW_MS covers rpunctd's RP_WINDOW_MS (%d >= %d)" % (w_rc, w_rp), w_rc >= w_rp > 0)
check("rc.h: the helpers are declared", "extern void reaper_wl_readers_stop(void);" in S["rch"] and "extern void reaper_wl_readers_start(void);" in S["rch"])

# ---- every teardown branch of handle_notifications
# Walked by LINES from the function's first line to its column-0 "}": services.c holds a
# brace inside a string literal before the wps_enr branch, which defeats a brace matcher,
# and a "/*" inside a string ("rm -f /var/cache/inadyn/*.cache") that a block-comment
# stripper would chase to the next "*/". Only same-line comments are stripped here.
raw = rd("services.c" if False else "services").splitlines()
hn = None
for i, l in enumerate(raw):
    if l.startswith("void handle_notifications(void)"):
        for j in range(i + 1, len(raw)):
            if raw[j] == "}":
                hn = "\n".join(raw[i:j + 1]); break
        break
check("services.c: handle_notifications() found (line-bounded)", hn is not None and 'strcmp(script, "wps_enr")' in hn and 'strcmp(script, "acsd")' in hn)
if hn:
    lines = [re.sub(r"/\*[^\n]*?\*/", "", l).strip() for l in hn.splitlines()]
    code = [l for l in lines if l and not l.startswith("#") and not l.startswith("//")]
    branch = "?"; stops = {}; starts = {}
    for i, l in enumerate(code):
        mb = re.search(r'strcmp\(script, "([a-z0-9_]+)"\)', l)
        if mb: branch = mb.group(1)
        if l == "stop_acsd();":
            stops.setdefault(branch, []).append(code[i - 1] == "reaper_wl_readers_stop();")
        if l == "start_acsd();":
            starts.setdefault(branch, []).append(code[i + 1] == "reaper_wl_readers_start();")
    for b in ("allnet", "net", "net_and_phy", "wps_enr"):
        check("branch %s: stop_acsd() is preceded by reaper_wl_readers_stop()" % b, b in stops and all(stops[b]), stops.get(b))
    for b in ("allnet", "net", "net_and_phy", "nas"):
        check("branch %s: start_acsd() is followed by reaper_wl_readers_start()" % b, b in starts and all(starts[b]), starts.get(b))
    check("branch acsd: restart_acsd alone leaves the readers alone",
          "acsd" in stops and not any(stops["acsd"]) and "acsd" in starts and not any(starts["acsd"]))
    wps = extract(hn, 'strcmp(script, "wps_enr")')
    check("branch wps_enr: the readers are started after start_wps() (this branch never restarts acsd)",
          wps is not None and re.search(r"start_nas\(\); start_wps\(\); reaper_wl_readers_start\(\);", norm(wps)) is not None)
    check("no stop_acsd() in a teardown branch is left unpaired",
          all(all(v) for b, v in stops.items() if b != "acsd"), {b: v for b, v in stops.items() if not all(v)})

# ---- restart_wireless
fn = extract(S["lan"], "void restart_wireless(void)")
check("lan.c: restart_wireless() found", fn is not None)
if fn:
    n = norm(fn)
    check("restart_wireless: wlready 0, the readers stopped, then stop_acsd()",
          re.search(r"nvram_set_int\(\"wlready\", 0\);.*reaper_wl_readers_stop\(\);.*stop_acsd\(\);", n) is not None)
    check("restart_wireless: wlready 1, then the readers started",
          re.search(r"nvram_set_int\(\"wlready\", 1\);.*reaper_wl_readers_start\(\);", n) is not None)
    check("restart_wireless: no bare stop_rpunctd()/start_rpunctd()/bwfloor calls left",
          not re.search(r"\b(stop|start)_(rpunctd|reaper_bwfloor)\(\)", n))

# ---- the readers' own guard
fn = extract(S["rpunctd"], "static int radio_quiet(void)")
check("rpunctd: radio_quiet() keys on reaper_wl_quiet()", fn is not None and "if (reaper_wl_quiet()) return 2;" in norm(fn)
      and "#include <reaper_wlquiet.h>" in S["rpunctd"])
fn = extract(S["bwfloor"], "int reaper_bwfloor_main(int argc, char *argv[])")
check("reaper_bwfloor: the tick skips while rc tears the radios down",
      fn is not None and re.search(r"while \(!g_stop\) \{.*?if \(reaper_wl_quiet\(\)\) \{ sleep\(2\); continue; \} esc_load\(e\);", norm(fn)) is not None
      and "#include <reaper_wlquiet.h>" in S["bwfloor"])
fn = extract(S["rchqd"], "int main(int argc, char **argv)")
check("rchqd: the tick skips while rc tears the radios down",
      fn is not None and re.search(r"if \(reaper_wl_quiet\(\)\) \{ for \(s = 0; s < 2 && running; s\+\+\) sleep\(1\); continue; \}", norm(fn)) is not None
      and "#include <reaper_wlquiet.h>" in S["rchqd"])

# ---- the predicate: source, then compiled and run
q = norm(S["quiet_c"])
SVC = ["restart_net", "restart_allnet", "restart_net_and_phy", "restart_wireless", "restart_dsl_wireless",
       "restart_wps_enr", "restart_nas", "restart_wlcconnect", "restart_modemscan"]
check("reaper_wlquiet.c: the service list names every radio-stopping rc service",
      all('"%s"' % s in q for s in SVC) and q.count('"restart_') == len(SVC), q.count('"restart_'))
check("reaper_wlquiet.c: whole-token match on ';' and ' '",
      "p[-1] == ';' || p[-1] == ' '" in q and "p[n] == 0 || p[n] == ';' || p[n] == ' '" in q)
check("reaper_wlquiet.c: reaper_wl_quiet() = wlready != 1 or a teardown",
      'return !nvram_match("wlready", "1") || reaper_wl_tearing_down();' in q)
check("shared/Makefile: reaper_wlquiet.o is built into libshared", re.search(r"\breaper_wlquiet\.o\b", S["shmk"]) is not None)
check("reaper_wlquiet.h: both prototypes", "int reaper_wl_tearing_down(void);" in S["quiet_h"] and "int reaper_wl_quiet(void);" in S["quiet_h"])

gcc = shutil.which("gcc") or shutil.which("cc")
if gcc and S["quiet_c"]:
    STUB_H = """#include <string.h>
extern const char *stub_get(const char *k);
#define nvram_safe_get(k) stub_get(k)
#define nvram_match(k, v) (strcmp(stub_get(k), (v)) == 0)
"""
    HARNESS = r"""#include <stdio.h>
#include <string.h>
#include "reaper_wlquiet.h"
static const char *g_rc = "", *g_wl = "1";
const char *stub_get(const char *k) { return !strcmp(k, "rc_service") ? g_rc : !strcmp(k, "wlready") ? g_wl : ""; }
struct c { const char *rc, *wl; int td, quiet; } C[] = {
 {"", "1", 0, 0}, {"restart_net", "1", 1, 1}, {"restart_nasapps", "1", 0, 0}, {"restart_networkmap", "1", 0, 0},
 {"start_x;restart_wireless", "1", 1, 1}, {"restart_wireless;restart_sdn", "1", 1, 1}, {"restart_allnet", "1", 1, 1},
 {"restart_net_and_phy", "1", 1, 1}, {"restart_wps_enr", "1", 1, 1}, {"restart_nas", "1", 1, 1}, {"restart_ddns", "1", 0, 0},
 {"restart_vpnserver", "1", 0, 0}, {"", "0", 0, 1}, {"restart_ddns", "0", 0, 1}, {"xrestart_net", "1", 0, 0}, {"restart_netx", "1", 0, 0},
};
int main(void) { int i, bad = 0; for (i = 0; i < (int)(sizeof C / sizeof *C); i++) { g_rc = C[i].rc; g_wl = C[i].wl;
 int td = reaper_wl_tearing_down(), qu = reaper_wl_quiet();
 if (td != C[i].td || qu != C[i].quiet) { printf("case %d rc='%s' wlready=%s: tearing_down=%d (want %d) quiet=%d (want %d)\n", i, C[i].rc, C[i].wl, td, C[i].td, qu, C[i].quiet); bad++; } }
 printf("%d cases, %d wrong\n", i, bad); return bad != 0; }
"""
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "bcmnvram.h"), "w").write(STUB_H)
        open(os.path.join(td, "reaper_wlquiet.h"), "w").write(rd("quiet_h"))
        open(os.path.join(td, "reaper_wlquiet.c"), "w").write(rd("quiet_c"))
        open(os.path.join(td, "h.c"), "w").write(HARNESS)
        r = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", "-I", td, "-o", os.path.join(td, "t"),
                            os.path.join(td, "reaper_wlquiet.c"), os.path.join(td, "h.c")], capture_output=True, text=True)
        check("host gcc: reaper_wlquiet.c compiles clean with -Wall -Wextra -Werror", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            r = subprocess.run([os.path.join(td, "t")], capture_output=True, text=True)
            check("host run: the predicate answers every case (nasapps/networkmap no, joined tokens yes, wlready 0 quiet)",
                  r.returncode == 0 and "0 wrong" in r.stdout, r.stdout)
else:
    print("note: no host gcc - the compiled predicate run is skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: the radio readers are quiesced before every rc teardown")
