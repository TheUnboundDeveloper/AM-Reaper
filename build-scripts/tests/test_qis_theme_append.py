#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Reaper palette reaches the AiMesh wizard by an appended stylesheet (2026-10-12).

WHY THIS EXISTS. The stock QIS wizard is kept for one flow, AiMesh add-node, and the theme
injector refuses every QIS_* page on purpose (a bounce there would loop a factory box). So the
wizard rendered in ASUS's own theme: ASUS blue on every button, link and loading bar. Reaper now
ships www/reaper_qis.css and the www Makefile appends it to mobile/css/qis.css at install, after
the stock rules, so it wins by order with no change to the stock sheet or the injector.

WHAT IT PINS. Source: the sheet exists, is ASCII only (the www packaging strips non-ASCII), names
no ASUS blue, carries the marker comment, and every selector it styles exists in the stock
qis.css (a GPL merge that renames one would silently leave that element blue); the Makefile appends
the sheet once for every model and removes the loose copy; the stock sheet is untouched by this
change (no Reaper colour in it). Staged (optional, argv[2] or REAPER_STAGED_WWW): the staged
qis.css ends with the sheet, the loose copy is gone, and the ASUS dashboard bundle is gone.

Exit 0 pass, 1 fail, 77 skipped (no tree: pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
STAGED = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("REAPER_STAGED_WWW", "")
FILES = {
    "sheet": "www/reaper_qis.css",
    "stock": "www/sysdep/FUNCTION/QIS_V3/mobile/css/qis.css",
    "mk": "www/Makefile",
}
if not SRC or not all(os.path.isfile(os.path.join(SRC, p)) for p in FILES.values()):
    skip("no router tree (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def rdb(k): return open(os.path.join(SRC, FILES[k]), "rb").read()
def rd(k): return rdb(k).decode("utf-8", errors="replace")

sheet_b = rdb("sheet"); sheet = sheet_b.decode("utf-8", errors="replace")
stock = rd("stock"); mk = rd("mk")

# -- the sheet itself ---------------------------------------------------------------------------
check("reaper_qis.css is ASCII only", all(b < 0x80 for b in sheet_b),
      "first non-ASCII byte at offset %d" % next((i for i, b in enumerate(sheet_b) if b >= 0x80), -1))
check("reaper_qis.css names no ASUS blue (#007AFF)", "007aff" not in sheet.lower())
check("reaper_qis.css carries its marker comment", "reaper_qis" in sheet)
check("reaper_qis.css uses the Reaper accent", "#E10600" in sheet)
check("reaper_qis.css does not restyle toggles (rule 11)", not re.search(r"\.(switch|toggle|iphoneSwitch|ui-slider)", sheet))

# every selector token must exist in the stock sheet
body = re.sub(r"/\*.*?\*/", "", sheet, flags=re.S)
missing = []
for m in re.finditer(r"([^{}]+)\{", body):
    for sel in m.group(1).split(","):
        sel = sel.strip()
        if not sel: continue
        tok = re.match(r"(#[A-Za-z0-9_-]+|\.[A-Za-z0-9_-]+|[a-z][a-z0-9]*)", sel)
        if not tok: continue
        t = tok.group(1)
        if t.startswith(".rqs_"):
            continue  # reaper-owned classes (the prerequisites box in amassearch_page.html), not stock
        if not re.search(re.escape(t) + r"(?=[\s,{:.>\[#])", stock):
            missing.append(t)
check("every selector in reaper_qis.css exists in the stock qis.css", not missing, ", ".join(sorted(set(missing))))

# -- the stock sheet is untouched ---------------------------------------------------------------
check("the stock qis.css carries no Reaper colour (the theme lives only in the appended sheet)",
      "#E10600" not in stock and "#08080a" not in stock.lower())

# -- the Makefile hook ----------------------------------------------------------------------------
app = re.findall(r'echo "" \| cat - \$\(TOP\)/www/reaper_qis\.css >> \$\(INSTALLDIR\)/www/mobile/css/qis\.css', mk)
check("the www Makefile appends reaper_qis.css to the staged qis.css exactly once", len(app) == 1, len(app))
check("the append is not inside the RTCONFIG_WISP conditional",
      re.search(r"ifeq \(\$\(RTCONFIG_WISP\), y\)(?:(?!endif).)*reaper_qis", mk, re.S) is None)
check("the loose staged copy is removed", "rm -f $(INSTALLDIR)/www/reaper_qis.css" in mk)
check("the ASUS dashboard bundle is stripped at install", "rm -rf $(INSTALLDIR)/www/dashboard" in mk)

# -- staged image (optional) ----------------------------------------------------------------------
if STAGED and os.path.isdir(STAGED):
    sq = os.path.join(STAGED, "mobile", "css", "qis.css")
    if os.path.isfile(sq):
        s = open(sq, "rb").read().decode("utf-8", errors="replace")
        check("staged qis.css ends with the Reaper sheet", s.rstrip().endswith(sheet.rstrip()))
        check("staged qis.css has the stock rules before the sheet", s.find("#007AFF") >= 0 and s.find("#007AFF") < s.find("reaper_qis"))
    else:
        check("staged mobile/css/qis.css exists", False, sq)
    check("staged loose reaper_qis.css is gone", not os.path.exists(os.path.join(STAGED, "reaper_qis.css")))
    check("staged www/dashboard is gone", not os.path.isdir(os.path.join(STAGED, "dashboard")))
else:
    print("note: no staged www given - staged checks skipped")

print("%d failed" % len(fails))
if fails:
    print("FAILED:"); [print("  " + f) for f in fails]
    sys.exit(1)
sys.exit(0)
