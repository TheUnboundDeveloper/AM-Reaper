#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wallguard: the State and verdict colours reach their table cells (2026-11-13).

WHY THIS EXISTS. Owner: "ok" in the State column should be green. The page always had .st-ok (jade), .st-failed /
.st-missing (amber) and the live table's .v-b / .v-a / .v-p verdict colours, but `.tbl td{color:var(--bone)}`
(class + element, specificity 0,1,1) outranks a bare class (0,1,0), so every such table cell drew in bone. The fix
adds the `.tbl td.<class>` forms.

WHAT IT DOES. Parses the page's style block, computes the specificity of every rule that sets `color` on a cell with
each state / verdict class, and checks the winning colour is the intended one - so a later `.tbl td` rule or a
removed form fails here. Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC)."""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
PAGE = os.path.join(SRC, "www", "Reaper_Wallguard.asp") if SRC else ""
if not SRC or not os.path.isfile(PAGE):
    print("SKIP: no router tree with www/Reaper_Wallguard.asp (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

page = open(PAGE, encoding="latin-1").read()
css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", page, re.S))
css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def spec(sel):
    sel = sel.strip()
    ids = sel.count("#")
    cls = len(re.findall(r"\.[\w-]+", sel)) + len(re.findall(r"\[[^\]]*\]", sel)) + len(re.findall(r":(?!:)[\w-]+", sel))
    els = len([t for t in re.split(r"[\s>+~]+", sel) if re.match(r"^[a-zA-Z]", t)])
    return (ids, cls, els)

def matches(sel, cls):
    """does selector `sel` apply to <td class=cls> inside a .tbl table (no other state)?"""
    sel = sel.strip()
    parts = re.split(r"\s+", sel)
    last = parts[-1]
    m = re.match(r"^(td)?((?:\.[\w-]+)*)$", last)
    if not m:
        return False
    need = re.findall(r"\.([\w-]+)", m.group(2))
    if any(n != cls for n in need):
        return False
    if not m.group(1) and not need:
        return False
    return all(p in (".tbl", "table", "tbody", "tr") for p in parts[:-1])

rules = []
for i, (sels, body) in enumerate(re.findall(r"([^{}]+)\{([^}]*)\}", css)):
    cm = re.search(r"(?:^|;)\s*color\s*:\s*([^;]+)", body)
    if cm:
        for s in sels.split(","):
            rules.append((s.strip(), cm.group(1).strip(), i))

WANT = {"st-ok": "var(--jade)", "st-failed": "var(--amber)", "st-missing": "var(--amber)", "st-new": "var(--steel)",
        "v-b": "var(--crimson)", "v-a": "var(--jade)", "v-p": "var(--amber)", "v--": "var(--steel)"}
check("the generic cell colour this has to beat is still there", any(s == ".tbl td" and c == "var(--bone)" for s, c, _ in rules))
for cls, want in WANT.items():
    cand = [(spec(s), i, c, s) for s, c, i in rules if matches(s, cls)]
    win = max(cand)[2] if cand else None
    check("a table cell with class %s draws in %s" % (cls, want), win == want, sorted(cand)[-3:])
check("the State cell carries the st- class and the live verdict cell the v- class",
      "stc.className = f ? 'st-' + f.st : '';" in page and "c.className = 'v-' + r.v;" in page)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
