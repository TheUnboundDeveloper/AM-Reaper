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
  1. every menu in the shipped tree (www/require/menuTrees/menuTree.js - every roster model
     builds ROG_UI=n, so www/Makefile installs this one) has an ICONS key, menu_QIS and
     menu_Split excepted;
  2. no ICONS key draws the _default glyph;
  3. two menus share a glyph only when both are Traffic Manager (menu_QoS, menu_BandwidthMonitor);
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
m = re.search(r"var ICONS\s*=\s*\{(.*?)\n\};", shell, re.S)
check("reaper_shell.asp declares var ICONS = {...};", m is not None)
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

# 1. every shipped menu has its own key
missing = [i for i in indices if i not in ("menu_QIS", "menu_Split") and i not in ICONS]
check("every menu in the shipped menuTree.js has an ICONS key (none falls to _default)", not missing, missing)

# 2. no key draws the fallback
dflt = [k for k, v in ICONS.items() if k != "_default" and v == DEFAULT]
check("no ICONS key draws the _default circle-dot", not dflt, dflt)

# 3. uniqueness, Traffic Manager's two indices excepted
SAME = {"menu_QoS", "menu_BandwidthMonitor"}
by_glyph = {}
for k, v in ICONS.items():
    if k != "_default": by_glyph.setdefault(v, []).append(k)
dups = [ks for ks in by_glyph.values() if len(ks) > 1 and set(ks) != SAME]
check("each menu draws a distinct glyph (only Traffic Manager's two indices share one)", not dups, dups)
check("Traffic Manager draws the same glyph under menu_QoS and menu_BandwidthMonitor",
      ICONS.get("menu_QoS") and ICONS.get("menu_QoS") == ICONS.get("menu_BandwidthMonitor"))
check("Traffic Manager and Traffic Analyzer draw different glyphs",
      ICONS.get("menu_BandwidthMonitor") != ICONS.get("menu_TrafficAnalyzer"))

# 4. dashboard rail parity
dash = rd(dash_p)
links = re.findall(r'<a href="/(?:reaper_shell\.asp#)?([A-Za-z0-9_]+\.asp)"[^>]*>\s*<span class="ni">(<svg.*?</svg>)</span>', dash, re.S)
check("Main_ReaperDash.asp rail parsed (at least 15 links)", len(links) >= 15, len(links))
for page, svg in links:
    owner = page_owner.get(page)
    if not owner:
        check("dashboard link %s belongs to a menu in menuTree.js" % page, False); continue
    check("dashboard %-30s == shell %s" % (page, owner), ICONS.get(owner) == norm(svg),
          "shell has %s" % ("no key" if owner not in ICONS else "a different glyph"))

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: one glyph per menu, the same on the dashboard and in the shell")
