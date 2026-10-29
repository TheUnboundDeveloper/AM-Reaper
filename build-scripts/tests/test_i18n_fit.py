#!/usr/bin/env python3
"""Translated labels that do not fit: one line, "...", the whole text on hover (owner, 2026-10-26).

WHY. Longer translations (FR, FI, PL, SL, BR ...) wrapped buttons, tabs, form labels and table headers onto two
lines, spilled text out of tiles, pushed row buttons out of a table's frame (Devices) and cut the header chip
strip's last chip mid-word on every page. Measured over every menu page in all 25 languages with the private
Playwright audit (scratchpad kit/i18n_fit: a mock that switches dictionaries, real Chromium layout).

WHAT IT DOES. Source checks: www/reaper/fit.js is static (no <% %> or <# #> - cached and revalidated like any
script), ASCII, touches only what misbehaves (wraps / spills / pushes past its container), restores only the
properties it set, never cuts prose (> 60 characters) or the value side of a key/value grid, sets a tooltip only on
a cut element and removes it once it fits, leaves an author's title alone, shares a container's overflow per table
column, and leaves a scrolling container that cannot fit as it is. The shell loads it for itself and every framed
page; the dashboard for itself; the shell's chip strip lets labels give way and never cuts a data value.
`node --check` on fit.js when node is there.
"""
import os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "reaper", "fit.js")):
    print("SKIP: no router source tree with www/reaper/fit.js (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

f = rd("www", "reaper", "fit.js")
check("fit.js is static (no ej or dictionary tags) and ASCII", "<%" not in f and "<#" not in f and all(ord(c) < 128 for c in f))
check("only what misbehaves is touched: wraps, spills, or past its container", "if (ln > 1 || over) todo.push(" in f and "fitContainers(doc, win, cand, todo);" in f)
check("prose (over 60 characters) is never cut", "var MAXLEN = 60" in f and "if (textOf(el).length > MAXLEN) return false;" in f)
cls = re.search(r"var CTRL_CLS = /(.*)/;", f)
check("label-like classes only - not the value side of a key/value grid", cls and "|v|" not in cls.group(1) and "|d|" not in cls.group(1) and "|k|" in cls.group(1), cls and cls.group(1))
check("a pass restores only the properties it set (a page's own show/hide survives)",
      "var PROPS = ['whiteSpace', 'overflow', 'textOverflow', 'minWidth', 'maxWidth', 'width', 'display'];" in f
      and "if (prev) for (k in prev) el.style[k] = prev[k];" in f and "removeAttribute('style')" not in f)
check("a tooltip only on a cut element, removed once it fits; an author's title is kept",
      "if (!el.title || mine) { el.title = textOf(el); el.setAttribute('data-rfit-title', '1'); }" in f
      and "} else if (mine) { el.removeAttribute('title'); el.removeAttribute('data-rfit-title'); }" in f)
check("table cells: content wrapped in a block (cells ignore max-width), the cell carries the tooltip",
      "function cellWrap(doc, el, px)" in f and "cell.title = textOf(sp);" in f)
check("container overflow shared per table column, down to the column's widest data cell",
      "fl[col] = Math.max(fl[col], cellNeed(doc, c));" in f and "key = 'c' + col + '|'" in f)
check("a scrolling container that cannot fit is left alone; a clipping one gives all it can",
      "if (total < ov && /auto|scroll/.test(win.getComputedStyle(a).overflowX)) break;" in f)
check("passes: on load, resize and 250 ms after content changes; own wrap spans are not a page change",
      "mo.observe(doc.documentElement, { childList: true, subtree: true, characterData: true });" in f and "mo.takeRecords();" in f)

sh = rd("www", "reaper_shell.asp")
check("shell: loads fit.js and watches itself and every framed page",
      '<script type="text/javascript" src="/reaper/fit.js"></script>' in sh and "RFIT.watch(document);" in sh
      and "RFIT.watch(f.contentDocument);" in sh)
check("shell chip strip: chips shrink, labels first, data values never cut",
      ".pill{" in sh and "flex:0 1 auto;min-width:0}" in sh and ".pill .k{" in sh and "flex:0 4 auto;min-width:3em;overflow:hidden;text-overflow:ellipsis}" in sh
      and ".pill .v.mono{flex:0 0 auto}" in sh)
d = rd("www", "Main_ReaperDash.asp")
check("dashboard: loads fit.js and watches itself", '<script src="/reaper/fit.js"></script>' in d and "RFIT.watch(document);" in d)
check("dashboard chip strip: as the shell's (labels first, data values never cut)",
      "flex:0 4 auto;min-width:3em;overflow:hidden;text-overflow:ellipsis}" in d and ".pill .v.mono{flex:0 0 auto}" in d)
check("an item its page pins (flex-shrink 0 in a flex row) is never shrunk",
      "win.getComputedStyle(el).flexShrink === '0') continue;" in f)
check("passes are throttled (a page that changes every second still gets them), one a second at most",
      "if (busy || t) return;" in f and "Math.max(ms, last + 1000 - Date.now())" in f)
node = shutil.which("node")
if node:
    r = subprocess.run([node, "--check", os.path.join(SRC, "www", "reaper", "fit.js")], capture_output=True, text=True)
    check("fit.js parses (node --check)", r.returncode == 0, r.stderr[-300:])
print("%d failure(s)" % len(fails))
for x in fails: print("  " + x)
sys.exit(1 if fails else 0)
