#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rtrafd's conntrack pass is paced by its own cost, and the health probe rides that pass.

WHY THIS EXISTS. Field report 2026-10-06 (RT-BE88U, v3.3.4): a DHT crawler on the LAN held
~10,700 conntrack entries (9,000 of them unanswered SYNs) and rtrafd used a whole core, mostly
in the kernel. The collector re-read the entire /proc/net/nf_conntrack every 2 s - the kernel
formats every line - and the health probe read it a second time each cycle. v3.3.5 paces the
pass by its measured cost (ct_pace: CT_BUDGET_PCT of one core, 2 s floor, 30 s ceiling) and
counts the probe's TCP connections inside the same pass. Every figure that used to assume the
fixed 2 s (live rates, top-talker rate, flow staleness, the Connections grace) now uses the
measured interval. A wrong conversion there is silent: a too-short staleness reclaims a live
flow's slot and credits its whole cumulative byte counter as one sample.

WHAT IT DOES. Extracts ct_pace(), flow_stale() and connseen_miss_max() with their #defines
from rtrafd.c, compiles them on the host behind a small main with stubbed syslog/mono_secs,
and asserts:
  - ct_pace: a cheap pass keeps the 2 s floor; a one-off slow read (lost the CPU) neither
    moves the interval nor logs; a 460 ms pass settles at ~15 s; a huge pass is held at 30 s;
    one log line on entering the slow state, one on leaving it, none sooner than 10 min apart;
  - flow_stale: 8 passes at 2 s (unchanged from v3.3.4), never fewer than 2 passes however
    slow the pass;
  - connseen_miss_max: 30 passes at 2 s (60 s), at least 1;
and statically: one fopen of nf_conntrack in the file (the probe no longer opens its own),
no rate divides by the fixed FCACHE_SECS, the probe's count sits in poll_conntrack before
the bytes= requirement, the main loop schedules the pass on a clock, and the build marker
for the pacing log line is present.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
RTRAFD = os.path.join(SRC, "rtrafd", "rtrafd.c")
if not SRC or not os.path.isfile(RTRAFD):
    skip("no router source tree with rtrafd (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

src = open(RTRAFD, encoding="utf-8", errors="surrogateescape").read()
HERE = os.path.dirname(os.path.abspath(__file__))
MARKERS = os.path.join(HERE, "..", "verify_markers.txt")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def define(name):
    m = re.search(r"^#define\s+" + name + r"\b.*$", src, re.M)
    if not m:
        fails.append("missing #define " + name); return ""
    return re.sub(r"\s*/\*.*$", "", m.group(0))	# a trailing comment may run onto the next lines

def function(sig):
    i = src.find(sig)
    if i < 0:
        fails.append("missing function " + sig); return ""
    j = src.find("\n}\n", i)
    return src[i:j + 3]

# ------------------------------------------------------------------ static wiring
check("one fopen of /proc/net/nf_conntrack (the probe shares the pass)",
      src.count('fopen("/proc/net/nf_conntrack"') == 1, src.count('fopen("/proc/net/nf_conntrack"'))
check("no rate divides by the fixed FCACHE_SECS", "/ FCACHE_SECS" not in src)
check("the old sliced probe reader is gone",
      not re.search(r"health_conn_(begin|step)|hp_ctf|HCONN_PER_TICK", src))
pc = function("static void poll_conntrack(void)\n{")
i_count = pc.find("hp_count_conn(src, line)")
i_bytes = pc.find('strstr(line, "bytes=")')
check("poll_conntrack counts for the probe", i_count > 0)
check("...before the bytes= requirement (the probe never needed accounting)",
      0 < i_count < i_bytes, (i_count, i_bytes))
check("...and publishes at the end of the pass",
      re.search(r"fclose\(f\);\s*if \(hcount\) \{ hp_count_publish\(\);", pc) is not None)
check("main loop schedules the pass on a clock", "ct_due_ms = nms + ct_pace(" in src)
check("main loop measures the interval the deltas span", "ct_iv_ms = ct_last_ms ? nms - ct_last_ms" in src)
check("HP_SCAN waits for the shared pass", "if (hp_ct_ready) { hp_ct_ready = 0; h_phase = HP_SEND; }" in src)
check("live rates use the measured interval", src.count("CT_BPS(") >= 10, src.count("CT_BPS("))
mk = open(MARKERS, encoding="utf-8").read() if os.path.isfile(MARKERS) else ""
check("build marker for the pacing log line", "bin/rtrafd|to stay near|1" in mk)

# ------------------------------------------------------------------ compiled behaviour
defs = "\n".join(define(n) for n in ("TICK_MS", "TPS", "HEAVY_EVERY", "FCACHE_SECS", "CT_MIN_MS",
                                       "CT_MAX_MS", "CT_BUDGET_PCT", "FLOW_STALE_SECS",
                                       "CONNSEEN_GRACE_SECS"))
body = "\n".join(function(s) for s in ("static long ct_pace(long cost_ms)",
                                        "static int flow_stale(uint32_t g)",
                                        "static int connseen_miss_max(void)"))
if fails:
    for f in fails: print("FAIL " + f)
    sys.exit(1)

harness = r'''
#include <stdio.h>
#include <stdint.h>
#include <stdarg.h>
#include <time.h>
#define LOG_NOTICE 5
static long ct_iv_ms;
static int ct_lines = 10672;
static uint32_t flowgen;
static time_t fake_now = 1000;
static int nlog = 0;
static char lastlog[512];
static time_t mono_secs(void) { return fake_now; }
static void syslog(int pri, const char *fmt, ...)
{
	va_list ap; (void)pri;
	va_start(ap, fmt); vsnprintf(lastlog, sizeof(lastlog), fmt, ap); va_end(ap);
	nlog++;
}
''' + defs + "\n" + body + r'''
int main(void)
{
	long iv = 0; int i;
	/* cheap passes: the floor */
	for (i = 0; i < 10; i++) iv = ct_pace(12);
	printf("cheap %ld logs %d\n", iv, nlog);
	/* a one-off slow read (the pass lost the CPU) is not a big table */
	iv = ct_pace(2000);
	printf("spike %ld logs %d\n", iv, nlog);
	iv = ct_pace(12);
	printf("after %ld logs %d\n", iv, nlog);
	/* the field case: ~460 ms per pass, steady */
	for (i = 0; i < 40; i++) { fake_now += 1; iv = ct_pace(460); }
	printf("field %ld logs %d last [%s]\n", iv, nlog, lastlog);
	/* a huge table: the ceiling */
	for (i = 0; i < 40; i++) iv = ct_pace(5000);
	printf("huge %ld logs %d\n", iv, nlog);
	/* table shrinks right away: back to the floor, but the log waits out 10 min */
	for (i = 0; i < 40; i++) iv = ct_pace(12);
	printf("back %ld logs %d\n", iv, nlog);
	fake_now += 600;
	iv = ct_pace(12);
	printf("later %ld logs %d last [%s]\n", iv, nlog, lastlog);
	/* staleness and grace at several intervals */
	flowgen = 100;
	{
		long ivs[] = { 2000, 5000, 15000, 30000 };
		for (i = 0; i < 4; i++) {
			uint32_t g; int need = 0;
			ct_iv_ms = ivs[i];
			for (g = 0; g <= 100; g++) if (flow_stale(100 - g)) { need = (int)g; break; }
			printf("iv %ld stale_after %d grace %d\n", ivs[i], need, connseen_miss_max());
		}
	}
	return 0;
}
'''

with tempfile.TemporaryDirectory() as td:
    c = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    open(c, "w").write(harness)
    r = subprocess.run([CC, "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
    check("pacing functions compile cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        for f in fails: print("FAIL " + f)
        sys.exit(1)
    out = subprocess.run([exe], capture_output=True, text=True).stdout
print(out, end="")

def val(key, field=1):
    m = re.search(r"^" + key + r" (\d+)", out, re.M)
    return int(m.group(1)) if m else -1

check("cheap pass keeps the 2 s floor, no log", "cheap 2000 logs 0" in out)
check("a one-off 2 s read keeps the floor and logs nothing", "spike 2000 logs 0" in out and "after 2000 logs 0" in out)
field = val("field")
check("a 460 ms pass settles at ~15 s (3% of one core)", 14000 <= field <= 16000, field)
check("entering the slow state logs once, with the entry count and the interval",
      "field 15333 logs 1 last [rtrafd: connection table holds 10672 entries and one read takes 460 ms - sampling every 15 s to stay near 3% of one core]" in out)
check("a huge pass is held at the 30 s ceiling", "huge 30000 logs 1" in out)
check("back to the floor at once, but no second log inside 10 min", "back 2000 logs 1" in out)
check("the recovery is logged once the 10 min have passed",
      "later 2000 logs 2 last [rtrafd: connection table down to 10672 entries - sampling every 2 s again]" in out)
check("staleness at 2 s = 8 passes (unchanged from v3.3.4), grace 30 passes", "iv 2000 stale_after 8 grace 30" in out)
check("staleness at 5 s = 3 passes, grace 12", "iv 5000 stale_after 3 grace 12" in out)
check("staleness never below 2 passes (15 s and 30 s), grace at least 1",
      "iv 15000 stale_after 2 grace 4" in out and "iv 30000 stale_after 2 grace 2" in out)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
