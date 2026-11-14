#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Traffic page: a bar is the row's share of its list's total, not a fraction of the busiest row (2026-11-12).

WHY THIS EXISTS. Field report: on the Traffic page the top device and DEFAULT (br0) had their bars "hard pegged
at 100% all the time". Each bar in By network, Top devices (live) and Top devices (history windows) was scaled to
the busiest row of its list, so that row was full whatever it did - the bar repeated the list order and said
nothing else.

WHAT IT DOES. Runs shareOf()/shareBar() from www/Reaper_Traffic.asp under node on sample rows (an even split, one
dominant device, a tiny share, nothing at all) and checks widths and hover text; then pins the three call sites to
the list totals and checks the busiest-row scale is gone. Exit 0 pass, 1 fail, 77 skipped (no node, or no router
tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
PAGE = os.path.join(SRC, "www", "Reaper_Traffic.asp") if SRC else ""
if not PAGE or not os.path.isfile(PAGE):
    skip("no router tree with www/Reaper_Traffic.asp (argv[1] or REAPER_ROUTER_SRC)")
NODE = shutil.which("node") or shutil.which("nodejs") or os.environ.get("REAPER_NODE", "")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(PAGE, encoding="utf-8", errors="replace").read()
m = re.search(r"(function shareOf\(v, tot\)\{.*?\n\}\nfunction shareBar\(v, tot, style, color\)\{.*?\n\})", src, re.S)
check("the page carries shareOf() and shareBar()", m is not None)

if m and NODE:
    js = m.group(1) + r'''
var out = {
  even: [shareOf(50, 100), shareOf(50, 100)],
  dominant: shareOf(109, 154),
  tiny: shareOf(1, 1000),
  none: shareOf(0, 0),
  zero_row: shareOf(0, 500),
  full: shareOf(80, 80),
  bar_dev: shareBar(30, 120),
  bar_net: shareBar(30, 120, 'flex:1;margin:0', '#4FB286')
};
console.log(JSON.stringify(out));
'''
    fd, p = tempfile.mkstemp(suffix=".js"); os.close(fd)
    open(p, "w", encoding="utf-8").write(js)
    try:
        r = subprocess.run([NODE, p], capture_output=True, text=True, timeout=30)
    finally:
        os.unlink(p)
    check("runs clean under node", r.returncode == 0, r.stderr[-400:])
    if r.returncode == 0:
        o = json.loads(r.stdout.strip().splitlines()[-1])
        check("two equal devices read 50% each (before: both 100%)", o["even"][0] == {"w": "50.0", "t": "50%"} == o["even"][1], o["even"])
        check("a device with 109 of 154 reads 71%", o["dominant"] == {"w": "70.8", "t": "71%"}, o["dominant"])
        check("a tiny share keeps its real width and says <1%", o["tiny"] == {"w": "0.1", "t": "&lt;1%"}, o["tiny"])
        check("no traffic at all, or a silent row -> 0%", o["none"] == {"w": "0", "t": "0%"} and o["zero_row"] == {"w": "0", "t": "0%"}, (o["none"], o["zero_row"]))
        check("only the list's sole active row is 100%", o["full"] == {"w": "100.0", "t": "100%"}, o["full"])
        check("bar markup: hover text on the bar, width on the fill",
              o["bar_dev"] == '<div class="bar" title="25%"><span style="width:25.0%"></span></div>', o["bar_dev"])
        check("network bar keeps its layout style and its colour",
              o["bar_net"] == '<div class="bar" style="flex:1;margin:0" title="25%"><span style="width:25.0%;background:#4FB286"></span></div>', o["bar_net"])
elif m:
    print("note: no node - the share arithmetic was not run (set REAPER_NODE)")

check("By network: total of the networks shown (the router-self bucket stays out), bar = share",
      "nrows=[], ntot=0;" in src and "nrows.push([nm,v,nrx,ntx]); ntot+=v;" in src
      and "'+shareBar(nrows[n2][1], ntot, 'flex:1;margin:0', col)+'" in src)
check("Top devices (live): total over EVERY device, not only the rows shown",
      "devs.forEach(function(r){ dtot+=r.dn+r.up; });" in src and "+shareBar(tot, dtot)+'</td>" in src)
check("Top devices (history windows): total over every device in the window",
      "rows.forEach(function(r){ htot+=r.tot; });" in src and "+shareBar(r.tot, htot)+'</td>" in src)
check("the busiest-row scale is gone", "/nmax*100" not in src and "/dmax*100" not in src and "/maxTot*100" not in src)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
