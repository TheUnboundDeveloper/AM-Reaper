#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The navigation rail draws one glyph per menu, the same on every page (2026-10-10).

WHY THIS EXISTS. The rail exists twice: Main_ReaperDash.asp writes it as static markup, and
reaper_shell.asp builds it from menuTree.js, picking the glyph by the menu's `index` from its
ICONS map and falling back to ICONS._default (a circle with a dot). The map was never completed
for the menus Reaper adds (menu_ReaperGK, menu_ReaperWarden, menu_ReaperAdvisor, menu_Sysinfo)
or for menu_IPv6, so those showed the circle-dot inside the shell and their real glyph on the
dashboard; Traffic Manager (menu_BandwidthMonitor on Reaper's tree) drew Traffic Analyzer's line
chart. Field (owner screenshot): "some pages use a circle with a dot instead of the original
unique symbol".

WHAT IT DOES. With a router source tree (argv[1] or REAPER_ROUTER_SRC):
  1. every menu the Reaper menu model (www/reaper/menu.js) emits has an ICONS key, menu_Split
     excepted, and every model menu is in the shipped tree (www/require/menuTrees/menuTree.js);
     2026-11-05 (review 2026-10-24 Q-C2-8, owner): the map holds ONLY the model's menus - the ten
     stock indexes the model never emits lost their glyphs; an add-on naming one draws _default;
  2. no ICONS key draws the _default glyph;
  3. every menu draws a distinct glyph;
  4. every dashboard rail link draws exactly the glyph the shell draws for the menu that
     owns the linked page.

Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
www = os.path.join(SRC, "www") if SRC else ""
shell_p = os.path.join(www, "reaper_shell.asp")
dash_p = os.path.join(www, "Main_ReaperDash.asp")
tree_p = os.path.join(www, "require", "menuTrees", "menuTree.js")
if not SRC or not all(os.path.isfile(p) for p in (shell_p, dash_p, tree_p)):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC) with www/reaper_shell.asp")

def rd(p): return open(p, encoding="utf-8", errors="replace").read()
norm = lambda s: re.sub(r"\s+", "", s)

shell = rd(shell_p)
# 2026-10-22: the map moved to www/reaper/menu.js (the menu model), shared by the shell and dashboard rails
menu_p = os.path.join(www, "reaper", "menu.js")
menu_js = open(menu_p, encoding="utf-8", errors="surrogateescape").read() if os.path.exists(menu_p) else ""
m = re.search(r"var ICONS\s*=\s*\{(.*?)\n\s*\};", menu_js, re.S)
check("www/reaper/menu.js declares var ICONS = {...} and the shell takes it from there",
      m is not None and "var ICONS = ReaperMenu.ICONS;" in shell)
if not m: print("\n1 FAILED"); sys.exit(1)
ICONS = {k: norm(v) for k, v in re.findall(r"^\s*(\w+)\s*:\s*'(<svg.*?</svg>)'\s*,?\s*$", m.group(1), re.M)}
DEFAULT = ICONS.get("_default", "")
check("ICONS has a _default glyph", bool(DEFAULT))

# menuTree.js: blocks from one `index:` to the next; a page belongs to the first menu naming it
tree = rd(tree_p)
idx_pos = [(mm.start(), mm.group(1)) for mm in re.finditer(r'index:\s*"(menu_\w+)"', tree)]
indices, page_owner = [], {}
for n, (pos, idx) in enumerate(idx_pos):
    end = idx_pos[n + 1][0] if n + 1 < len(idx_pos) else len(tree)
    if idx not in indices: indices.append(idx)
    for page in re.findall(r'"([A-Za-z0-9_]+\.(?:asp|htm|html))"', tree[pos:end]):
        page_owner.setdefault(page, idx)
check("menuTree.js carries the Reaper menus", all(i in indices for i in
      ("menu_ReaperGK", "menu_ReaperWarden", "menu_ReaperDevices", "menu_Sysinfo")), indices)

# 1. every model menu has its own key; the map holds nothing else (Q-C2-8, 2026-11-05)
model = sorted(set(re.findall(r"index: '(menu_\w+)'", menu_js)) - {"menu_Split"})
missing = [i for i in model if i not in ICONS]
check("every menu the model emits has an ICONS key (none falls to _default)", model and not missing, missing)
check("every model menu is in the shipped menuTree.js", not [i for i in model if i not in indices], [i for i in model if i not in indices])
extra = [k for k in ICONS if k not in model and k not in ("_default", "menu_Addons")]
check("ICONS holds only the model's menus + menu_Addons + _default (the ten stock-only glyphs are gone)", not extra, extra)
GONE = ["menu_AiCloud", "menu_AiProtection", "menu_Alexa_IFTTT", "menu_GameBoost", "menu_NewDashboard", "menu_OpenNAT",
        "menu_QoS", "menu_SMS", "menu_TencentAcceleration", "menu_UU"]
check("none of the ten stock-only indexes is named in menu.js outside the comment", not [g for g in GONE if (g + ":") in menu_js], [g for g in GONE if (g + ":") in menu_js])

# 2. no key draws the fallback
dflt = [k for k, v in ICONS.items() if k != "_default" and v == DEFAULT]
check("no ICONS key draws the _default circle-dot", not dflt, dflt)

# 3. uniqueness (menu_QoS, the stock twin of menu_BandwidthMonitor, is gone since 2026-11-05)
SAME = set()
by_glyph = {}
for k, v in ICONS.items():
    if k != "_default": by_glyph.setdefault(v, []).append(k)
dups = [ks for ks in by_glyph.values() if len(ks) > 1 and set(ks) != SAME]
check("each menu draws a distinct glyph", not dups, dups)
check("Traffic Manager (menu_BandwidthMonitor) draws the bars",
      ICONS.get("menu_BandwidthMonitor") == norm('<svg viewBox="0 0 24 24"><path d="M4 18v-5M9 18V7M14 18v-8M19 18v-12"/></svg>'))
check("Traffic Manager and Traffic Analyzer draw different glyphs",
      ICONS.get("menu_BandwidthMonitor") != ICONS.get("menu_TrafficAnalyzer"))

# 4. dashboard rail parity
# 2026-10-22: the dashboard no longer carries a hand-kept copy of the rail - it draws ReaperMenu.rail(),
# whose icons are this same map, so parity is structural: the generated markup uses r.icon and no
# static rail anchor (a literal <span class="ni"><svg) survives in the page.
dash = rd(dash_p)
check("Main_ReaperDash.asp draws its rail from the menu model (ReaperMenu.rail(), r.icon)",
      "ReaperMenu.rail()" in dash and "r.icon" in dash and '<script src="/reaper/menu.js"></script>' in dash)
check("no static rail anchors remain in Main_ReaperDash.asp (only the add-on section's glyph template)",
      dash.count('<span class="ni"><svg') == 1 and "var ICON = '<span class=\"ni\"><svg" in dash)
check("menu.js's rail() picks ICONS[index] with the _default fallback", "icon: ICONS[m.index] || ICONS._default" in menu_js)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: one glyph per menu, the same on the dashboard and in the shell")
