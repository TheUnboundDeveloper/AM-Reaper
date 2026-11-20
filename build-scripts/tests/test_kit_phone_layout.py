#!/usr/bin/env python3
"""Native (kit) pages fit a phone screen (2026-10-31).

WHY. Under 680 px the shell gives a framed page the full screen width, and grows the frame when the page is wider
(so a wide stock table pans on the stage). The kit settings row was a grid of minmax(200px,320px) and
minmax(160px,1fr) with a 22 px gap - 382 px before the body and panel padding - so on a 402 px phone 21 of the 32
kit pages came out 424-592 px wide and the whole page panned sideways. Multi-column data tables (NAT, QoS, Routes,
the VPN pages, LAN) and NAT's preset picker (as wide as its longest option) did the same. Measured in the mock
with WebKit at 402 / 320 px and Chromium at 375 px (scratchpad hdr/phonescan2.js, minscan.js, tablefill2.js):
afterwards every kit page is exactly the screen's width.

WHAT IT CHECKS. rp.css ends with a 680 px block (last, so it wins over the base rules) that stacks a settings row
into one column, pans only table.classes in its own box (a table shown as a block shrinks to its content, so a
short list would stop filling its panel) with one-line headers and a left-aligned "no rows" line, and caps the
add-row fields at the panel. fit.js never squeezes the headers of a table shown that way. No kit page sets its
own .frow columns (a page's style comes after rp.css, so it would undo the phone rule).
"""
import os, re, sys, glob

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "reaper", "rp.css")):
    print("SKIP: no router source tree with www/reaper/rp.css (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

css, fit = rd("www", "reaper", "rp.css"), rd("www", "reaper", "fit.js")
i = css.rfind("@media (max-width:680px){")
blk = css[i:] if i >= 0 else ""
check("rp.css has a 680 px phone block", i >= 0)
check("the phone block is the last rule in rp.css (it wins over the base rules above it)",
      blk.rstrip().endswith("}") and blk.count("{") == blk.count("}") and css[i:].rstrip() == blk.rstrip(), blk[-80:])
check("phone: a settings row is one column", ".frow{grid-template-columns:minmax(0,1fr)" in blk, blk[:200])
check("phone: table.classes pans in its own box",
      re.search(r"table\.classes\{display:block;[^}]*overflow-x:auto", blk) is not None)
check("phone: only table.classes pans (no other table is turned into a block)",
      not re.search(r"(^|[\s,}])table(:not\([^)]*\))?\s*\{", blk) and blk.count("display:block") == 1)
check("phone: a panning table keeps its headers on one line", "table.classes th{white-space:nowrap}" in blk)
check("phone: the 'no rows' line of a panning table starts at the left", "table.classes td.empty{text-align:left}" in blk)
check("phone: add-row fields never run wider than the panel", ".bwl-add .f,.bwl-add input,.bwl-add select{max-width:100%}" in blk)

fc = fit[fit.find("function fitContainers"):]
ca = fc.find("a = clipAncestor(win, el);")
ex = fc.find("if (a.tagName === 'TABLE' && win.getComputedStyle(a).display === 'block') continue;")
check("fit.js: a table shown as a panning block never has its headers squeezed (right after the clip-box lookup)",
      0 <= ca < ex < ca + 400, (ca, ex))

own = []
for p in sorted(glob.glob(os.path.join(SRC, "www", "*.asp"))):
    s = open(p, encoding="utf-8", errors="replace").read()
    if "reaper/rp.css" not in s: continue
    s = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^}]*\})*[^{}]*\}", "", s)   # a page's own phone/tablet rules are its business
    if re.search(r"\.frow\s*\{[^}]*grid-template-columns", s): own.append(os.path.basename(p))
check("no kit page sets its own .frow columns (it would undo the phone rule)", not own, own)
check("edited files stay ASCII", all(ord(c) < 128 for c in css + fit))
print("%d failure(s)" % len(fails))
for x in fails: print("  " + x)
sys.exit(1 if fails else 0)
