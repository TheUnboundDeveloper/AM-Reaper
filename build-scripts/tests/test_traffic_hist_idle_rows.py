#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Traffic Analyzer: a history timeframe lists only devices with traffic in it (2026-11-13).

WHY THIS EXISTS. Field report (BQ16; the code is the same on every model): choosing a timeframe listed every device the
collector had stored, including ones that moved nothing in that window, as 0 B / 0 B rows. The Live view already
leaves idle devices out.

WHAT IT DOES. Runs the page's own Top Devices block from renderHist() under node with stubbed helpers: a device with
traffic in the window is listed (an IP-keyed and a MAC-keyed row of one device still merge first), a device whose
window is all zero is not, and a window with no traffic at all shows the empty line. Then pins the filter.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC). Without node only the pin runs."""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
PAGE = os.path.join(SRC, "www", "Reaper_Traffic.asp") if SRC else ""
if not SRC or not os.path.isfile(PAGE):
    print("SKIP: no router tree with www/Reaper_Traffic.asp (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
page = open(PAGE, encoding="latin-1").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

check("the window's rows are filtered to devices with traffic before ranking",
      "rows=rows.filter(function(r){ return r.tot>0; });\n  rows.sort(function(a,b){return b.tot-a.tot;});" in page)
m = re.search(r"(  var cli=d\.clients\|\|\{\}, rows=\[\], agg=\{\};\n.*?  fillTop\('cli', tb, `<#RTRF_69#>`\);\n)", page, re.S)
check("Top Devices block found in renderHist", bool(m))
NODE = shutil.which("node") or shutil.which("nodejs")
if m and NODE:
    body = m.group(1).replace("`<#RTRF_69#>`", "'EMPTY'")
    js = ("var out={};var TOPN_MAX=50;var ReaperNames={macForIp:function(ip){return ip=='192.168.50.9'?'aa:bb:cc:00:00:09':'';}};\n"
          "function devCell(ip,n){return '['+n+']';} function shareBar(){return '';} function fmtBytes(b){return b+'B';}\n"
          "function fillTop(w,rows,empty){out[w]=rows.length?rows.join('|'):empty;}\n"
          "function render(d){\n" + body + "}\n"
          "var r={};\n"
          "render({clients:{'aa:bb:cc:00:00:01':{ip:'192.168.50.1',d:[[0,0],[100,20]]},"
          "'aa:bb:cc:00:00:02':{ip:'192.168.50.2',d:[[0,0],[0,0]]},"
          "'192.168.50.9':{d:[[5,0]]},'aa:bb:cc:00:00:09':{ip:'192.168.50.9',d:[[0,1]]}}}); r.mixed=out.cli;\n"
          "render({clients:{'aa:bb:cc:00:00:02':{d:[[0,0]]}}}); r.idle=out.cli;\n"
          "render({clients:{}}); r.none=out.cli;\n"
          "console.log(JSON.stringify(r));\n")
    tmp = tempfile.mkdtemp()
    try:
        h = os.path.join(tmp, "t.js"); open(h, "w", encoding="ascii").write(js)
        res = subprocess.run([NODE, h], capture_output=True, text=True, timeout=60)
        o = {}
        try:
            o = json.loads(res.stdout)
        except Exception:
            pass
        check("block ran under node", bool(o), (res.stdout + res.stderr)[-400:])
        if o:
            check("a device with traffic in the window is listed, busiest first",
                  o["mixed"].startswith("<tr><td>[aa:bb:cc:00:00:01]") and "120B" not in o["mixed"] and "100B" in o["mixed"], o["mixed"])
            check("an IP-keyed and a MAC-keyed row of one device still merge (5 B + 1 B under the MAC name)",
                  "[aa:bb:cc:00:00:09]</td><td class=\"num\">5B</td><td class=\"num\">1B</td>" in o["mixed"]
                  and o["mixed"].count("<tr>") == 2, o["mixed"])
            check("a device with nothing in the window is not listed", "00:00:02" not in o["mixed"], o["mixed"])
            check("a window where nobody moved traffic shows the empty line", o["idle"] == "EMPTY" and o["none"] == "EMPTY", o)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
elif m:
    print("SKIP (part): no node")

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
