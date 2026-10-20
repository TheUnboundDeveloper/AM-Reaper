#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rtrafd's live latency/loss come from a window of probe results, and the page keys its tiles on the target.

WHY THIS EXISTS. Owner report 2026-10-17: the Traffic Analyzer's Latency and Loss tiles were missing at
login and came back only after re-applying the probe IP (which restarts rtrafd). The page drew both tiles
only while the live RTT was non-zero, and rtrafd's live RTT was the running average of the open 5-min
bucket, falling back to `r_prb->b5[i5cur]` - a slot hist_tick had just zeroed. Any bucket with no reply
yet (the first seconds after every boundary; the whole stretch of an outage) read 0, so 100 % loss showed
no tile at all. A ping that could not be started returned uncounted and unlogged.

WHAT IT DOES. Extracts host_ok(), prbw_push(), prbw_stats() and poll_probe() with PRB_WIN from rtrafd.c,
compiles them on the host behind a main with stubbed nvram / rt_exec_bounded / syslog / mono_secs, and
asserts:
  - no target (or an invalid one): set 0, window emptied;
  - replies average over the window; a DUP! line does not double the RTT;
  - every attempt lost: ok 0, loss 100 (the figure the old page hid);
  - the window keeps the last 12 results (60 s) and rolls;
  - a ping that cannot start counts in err only, empties the window, logs once per streak and not
    more than once per 10 min; the next started ping clears err;
and statically: the live JSON carries set/n/ok/err and no longer reads the bucket accumulators or the
current history slot; the page keys the tiles on probe.set and the figures on ok / n; the build marker
for the launch-failure log line is present.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
RTRAFD = os.path.join(SRC, "rtrafd", "rtrafd.c")
PAGE = os.path.join(SRC, "www", "Reaper_Traffic.asp")
if not SRC or not os.path.isfile(RTRAFD):
    skip("no router source tree with rtrafd (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
NODE = shutil.which("node") or shutil.which("node.exe")
if not CC and not NODE:
    skip("no host C compiler and no node")

src = open(RTRAFD, encoding="utf-8", errors="surrogateescape").read()
page = open(PAGE, encoding="utf-8", errors="surrogateescape").read() if os.path.isfile(PAGE) else ""
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
    return re.sub(r"\s*/\*.*$", "", m.group(0))

def function(sig):
    i = src.find(sig)
    if i < 0:
        fails.append("missing function " + sig); return ""
    j = src.find("\n}\n", i)
    return src[i:j + 3]

# ------------------------------------------------------------------ static wiring
m = re.search(r'fprintf\(o, ",\\"probe\\":\{.*?\);', src, re.S)
blk = src[src.rfind("{", 0, m.start()):m.end()] if m else ""
check("live JSON carries set, n, ok, rtt_us, loss, err, seq, last_us",
      m is not None and all(('\\"%s\\":' % k) in m.group(0) for k in ("set", "n", "ok", "rtt_us", "loss", "err", "seq", "last_us")),
      m.group(0) if m else "no probe fprintf")
check("live figures come from the window (prbw_stats)", "prbw_stats(&pn, &pok, &prtt, &ploss);" in blk)
check("...not from the bucket accumulators or the just-zeroed history slot",
      blk != "" and "prb_n" not in blk and "r_prb" not in blk, blk)
check("the 5-min history bucket still accumulates (probe_close_bucket unchanged in role)",
      "prb_rtt_sum = 0; prb_n = prb_lost = 0;" in src)
check("page keys both tiles on probe.set", "if(pr.set){" in page)
check("page shows the RTT only with a reply, the loss only with an attempt",
      "pr.ok>0?(pr.rtt_us/1000)" in page and "pr.n>0?pr.loss" in page)
check("page no longer hides the tiles on a zero RTT", "d.probe&&d.probe.rtt_us" not in page)
mk = open(MARKERS, encoding="utf-8").read() if os.path.isfile(MARKERS) else ""
check("build marker for the launch-failure log line", "bin/rtrafd|latency probe could not start ping|1" in mk)

if not CC:
    print("note: no host C compiler - the compiled probe checks are skipped")
else:
    # ------------------------------------------------------------------ compiled behaviour
    defs = define("PRB_WIN")
    body = "\n".join(function(s) for s in ("static int host_ok(const char *s)",
                                            "static void prbw_push(int32_t rtt_us)",
                                            "static void prbw_stats(int *n, int *ok, uint64_t *rtt_us, uint64_t *loss)",
                                            "static void poll_probe(void)"))
    if fails:
        for f in fails: print("FAIL " + f)
        sys.exit(1)

    harness = r'''
    #include <stdio.h>
    #include <stdint.h>
    #include <stdlib.h>
    #include <string.h>
    #include <stdarg.h>
    #include <errno.h>
    #include <time.h>
    #include <sys/types.h>
    #define LOG_WARNING 4
    static uint64_t prb_rtt_sum = 0;
    static uint32_t prb_n = 0, prb_lost = 0;
    ''' + defs + r'''
    static int32_t prbw[PRB_WIN];
    static int prbw_len = 0, prbw_pos = 0;
    static int prb_set = 0;
    static uint32_t prb_err = 0;
    static uint32_t prb_seq = 0;
    static int32_t prb_last = -1;
    static time_t fake_now = 1000;
    static int nlog = 0;
    static char lastlog[256];
    static const char *nv_probe = "";
    static const char *ping_out = "";
    static int ping_fail = 0;
    static time_t mono_secs(void) { return fake_now; }
    static void syslog(int pri, const char *fmt, ...)
    {
    	va_list ap; (void)pri;
    	va_start(ap, fmt); vsnprintf(lastlog, sizeof(lastlog), fmt, ap); va_end(ap);
    	nlog++;
    }
    static const char *nvram_safe_get(const char *k) { (void)k; return nv_probe; }
    static size_t strlcpy(char *d, const char *s, size_t n)
    {
    	size_t l = strlen(s);
    	if (n) { size_t c = l < n - 1 ? l : n - 1; memcpy(d, s, c); d[c] = 0; }
    	return l;
    }
    static ssize_t rt_exec_bounded(char *const argv[], char *out, size_t outsz, int secs)
    {
    	(void)argv; (void)secs;
    	if (ping_fail) { errno = EMFILE; return -1; }
    	strlcpy(out, ping_out, outsz);
    	return (ssize_t)strlen(out);
    }
    ''' + body + r'''
    static void show(const char *tag)
    {
    	int n, ok; uint64_t rtt, loss;
    	prbw_stats(&n, &ok, &rtt, &loss);
    	printf("%s set=%d n=%d ok=%d rtt=%llu loss=%llu err=%u logs=%d seq=%u last=%d\n", tag, prb_set, n, ok,
    	       (unsigned long long)rtt, (unsigned long long)loss, (unsigned)prb_err, nlog, (unsigned)prb_seq, (int)prb_last);
    }
    #define REPLY(ms) "PING 1.1.1.1 (1.1.1.1): 56 data bytes\n64 bytes from 1.1.1.1: seq=0 ttl=57 time=" ms " ms\n"
    #define LOST "PING 1.1.1.1 (1.1.1.1): 56 data bytes\n\n--- 1.1.1.1 ping statistics ---\n1 packets transmitted, 0 packets received, 100% packet loss\n"
    int main(void)
    {
    	int i;
    	poll_probe(); show("empty");
    	nv_probe = "-f"; poll_probe(); show("badtgt");
    	nv_probe = "1.1.1.1";
    	ping_out = REPLY("10.000"); poll_probe();
    	ping_out = REPLY("20.000"); poll_probe();
    	ping_out = REPLY("30.000"); poll_probe(); show("three");
    	ping_out = REPLY("10.000") "64 bytes from 1.1.1.1: seq=0 ttl=57 time=10.000 ms (DUP!)\n";
    	poll_probe(); show("dup");
    	ping_out = LOST; for (i = 0; i < 12; i++) poll_probe();
    	show("alllost");
    	ping_out = REPLY("8.000"); for (i = 0; i < 6; i++) poll_probe();
    	show("half");
    	for (i = 0; i < 6; i++) poll_probe();
    	show("recovered");
    	ping_fail = 1; poll_probe(); show("fail1");
    	poll_probe(); show("fail2");
    	ping_fail = 0; poll_probe(); show("ok");
    	fake_now += 60; ping_fail = 1; poll_probe(); show("fail_soon");
    	ping_fail = 0; poll_probe();
    	fake_now += 600; ping_fail = 1; poll_probe(); show("fail_later");
    	printf("last [%s]\n", lastlog);
    	ping_fail = 0; nv_probe = ""; poll_probe(); show("cleared");
    	return 0;
    }
    '''

    with tempfile.TemporaryDirectory() as td:
        c = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
        open(c, "w").write(harness)
        r = subprocess.run([CC, "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
        check("probe functions compile cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
        if r.returncode != 0:
            for f in fails: print("FAIL " + f)
            sys.exit(1)
        out = subprocess.run([exe], capture_output=True, text=True).stdout
    print(out, end="")

    def has(s): return s in out
    check("no target: set 0, empty window", has("empty set=0 n=0 ok=0 rtt=0 loss=0 err=0 logs=0"))
    check("a target host_ok refuses (-f) counts as no target", has("badtgt set=0 n=0"))
    check("three replies average to 20 ms, 0 % loss", has("three set=1 n=3 ok=3 rtt=20000 loss=0 err=0"))
    check("a DUP! line does not double the RTT", has("dup set=1 n=4 ok=4 rtt=17500 loss=0"))
    check("every attempt lost: ok 0, loss 100 (still set - the page shows the tiles)",
          has("alllost set=1 n=12 ok=0 rtt=0 loss=100 err=0"))
    check("the window rolls: 6 replies after 12 losses = 50 % over the last 12",
          has("half set=1 n=12 ok=6 rtt=8000 loss=50"))
    check("12 replies push the losses out", has("recovered set=1 n=12 ok=12 rtt=8000 loss=0"))
    check("a ping that cannot start: err 1, window emptied, one log line",
          has("fail1 set=1 n=0 ok=0 rtt=0 loss=0 err=1 logs=1"))
    check("...the same streak does not log again", has("fail2 set=1 n=0 ok=0 rtt=0 loss=0 err=2 logs=1"))
    check("the next started ping clears err and refills", has("ok set=1 n=1 ok=1 rtt=8000 loss=0 err=0 logs=1"))
    check("a new streak inside 10 min is not logged", has("fail_soon set=1 n=0 ok=0 rtt=0 loss=0 err=1 logs=1"))
    check("a new streak after 10 min is logged", has("fail_later set=1 n=0 ok=0 rtt=0 loss=0 err=1 logs=2"))
    check("the log line names the cause", has("last [rtrafd: latency probe could not start ping ("))
    check("clearing the target empties the window", has("cleared set=0 n=0 ok=0 rtt=0 loss=0 err=0"))
    # 2026-10-20 (reviewer: no latency on the live chart): every pushed result advances seq and sets last;
    # a ping that could not start is not a result (seq unchanged); seq survives the window and bucket resets
    check("seq counts results and last carries the newest RTT", has("three set=1 n=3 ok=3 rtt=20000 loss=0 err=0 logs=0 seq=3 last=30000"))
    check("a lost reply is a result with last -1", has("alllost set=1 n=12 ok=0 rtt=0 loss=100 err=0 logs=0 seq=16 last=-1"))
    check("a ping that cannot start does not advance seq", has("fail1 set=1 n=0 ok=0 rtt=0 loss=0 err=1 logs=1 seq=28 last=8000")
          and has("fail2 set=1 n=0 ok=0 rtt=0 loss=0 err=2 logs=1 seq=28"))

# ------------------------------------------------------------------ the page: the latency & loss chart
# 2026-10-20 (owner): one probe every 5 s drew a fragmented, popping latency line on the WAN chart;
# latency and loss now have their own chart under it, sampled on every poll like the WAN ring
check("the WAN chart is throughput only again (two traces, no latency, no right axis)",
      "new LiveChart('wanchart',[],['var(--jade)','var(--crimson)'])" in page and "wanC.raxis(" not in page
      and "lineChart('wanchart', series, maxv, fmtBps);" in page and "v/lmax*maxv" not in page)
check("the latency & loss chart: its own card under WAN throughput, latency left (ms), loss right (%)",
      page.index('id="wanchart"') < page.index('id="latchart"') < page.index('id="clschart"')
      and "new LiveChart('latchart',[],['var(--amber)','var(--loss)'])" in page
      and "latC.raxis(pmx, fmtPct);" in page and "latC.axis(lmx, fmtMs);" in page)
check("live: one latency & loss sample per poll - the last reply held, loss the rolling 60 s figure",
      "pushSamp(latSamp,[st, latHold===null?-1:latHold, pr.n>0?(pr.loss||0):0]);" in page
      and "if(pr.last_us>=0) latHold=pr.last_us/1000;" in page and "pushLat(" not in page and "latSeq" not in page)
check("live: loss never scales below 10 % (a single lost probe reads small)", "lossScale.step(Math.max(praw, 9), t1, dt)" in page)
check("history: latency and loss from the per-slot probe data, a slot without a probe breaks both lines",
      "lineChart('latchart', [{data:lat, color:'var(--amber)'}], niceMax(lmax*1.08), fmtMs," in page
      and "{data:loss, color:'var(--loss)', fmt:fmtPct, floor:9.3}" in page)
check("no probe target: the card shows the probe-off note instead of an empty chart",
      'id="latoff"' in page and "latShow(!!pr.set);" in page)

if NODE and page:
    # run the real helpers (W, RGUT, fmtMs, niceMax, axis, lineChart) against a stub svg
    def js_fn(name):
        i = page.find("function " + name + "(")
        if i < 0: return ""
        depth = 0; j = page.index("{", i)
        for k in range(j, len(page)):
            if page[k] == "{": depth += 1
            elif page[k] == "}":
                depth -= 1
                if depth == 0: return page[i:k + 1]
        return ""
    js = "var W=1000, RGUT=44;\n" + "\n".join(js_fn(n) for n in ("fmtMs", "fmtPct", "niceMax", "axis", "lineChart")) + r'''
var svg={ innerHTML:'', getAttribute:function(){ return '0 0 1000 170'; } };
var document={ getElementById:function(){ return svg; } };
function bps(v){ return Math.round(v)+' b'; }
/* the history latency & loss chart: latency left (null = no probe), loss right with a 10 % floor */
lineChart('latchart', [{data:[10, null, 30],color:'var(--amber)'}], 50, fmtMs, {data:[0, null, 2], color:'var(--loss)', fmt:fmtPct, floor:9.3});
var withR=svg.innerHTML;
lineChart('wanchart', [{data:[1,2,3],color:'a'}], 3, bps);
var noR=svg.innerHTML;
console.log(JSON.stringify({pct:(withR.match(/ %</g)||[]).length, top:(withR.match(/>10 %</g)||[]).length, x2r:withR.indexOf('x2="956"')>=0,
  x2n:noR.indexOf('x2="1000"')>=0, nopct:(noR.match(/ %</g)||[]).length,
  lat:(withR.match(/d="([^"]*)" fill="none" stroke="var\(--amber\)"/)||['',''])[1],
  loss:(withR.match(/d="([^"]*)" fill="none" stroke="var\(--loss\)"/)||['',''])[1]}));
'''
    with tempfile.TemporaryDirectory() as td:
        jp = os.path.join(td, "c.js"); open(jp, "w").write(js)
        r = subprocess.run([NODE, jp], capture_output=True, text=True)
    import json as _json
    try: res = _json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: res = {}
    check("node: the latency & loss chart has five right-hand % labels topping at the 10 % floor, plot ending at 956",
          res.get("pct") == 5 and res.get("top") == 1 and res.get("x2r") is True, (r.stdout, r.stderr))
    check("node: a chart without a right series has no % labels and spans to 1000",
          res.get("nopct") == 0 and res.get("x2n") is True, res)
    check("node: a slot with no probe breaks both lines (two moves each, no join across it); a 0 % loss is drawn",
          res.get("lat", "").count("M") == 2 and "L" not in res.get("lat", "")
          and res.get("loss", "").count("M") == 2 and "L" not in res.get("loss", ""), res)
else:
    print("note: no node on this host - the executed chart checks are skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
