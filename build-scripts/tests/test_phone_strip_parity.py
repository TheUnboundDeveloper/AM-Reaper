#!/usr/bin/env python3
"""On a phone the dashboard's rail strip is the same strip every other page shows (2026-10-31).

WHY. At <= 680 px the rail turns into a horizontal icon strip under the header. reaper_shell.asp (every page but
the dashboard) hid the rail's language row and group headings there; Main_ReaperDash.asp, which draws its own copy
of the rail, did not. The dashboard strip therefore showed a "LANGUAGE:" row whose select was squashed to nothing
(the label took the whole 85 px row, the select has min-width 0), a GENERAL heading, a two-line ADVANCED SETTINGS
heading and the full About tile, so the strip was 81 px high on the dashboard and 63 px everywhere else. The
dashboard's phone logo (36 px high, uncapped) also pushed a 320 px phone 13 px wide. Measured in the mock with
WebKit and Chromium at 402 / 375 / 320 px (scratchpad hdr/strip.js, wide.js).

WHAT IT CHECKS. Both 680 px blocks hide the language row and the headings and keep only the About mark; the
dashboard's hide carries a `.rail` prefix because its base `.raillang` rule comes after the block (same
specificity, later wins: a bare `.raillang{display:none}` there did nothing). The strip padding, clock, item
height, active-item bar and logo use the same numbers on both pages, and the logo is capped at its row.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "reaper_shell.asp")):
    print("SKIP: no router source tree with www/reaper_shell.asp (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

def block(html):
    i = html.find("@media (max-width:680px){")
    j = html.find("\n}", i)
    return (i, html[i:j + 2]) if i >= 0 and j > i else (-1, "")

d, sh = rd("www", "Main_ReaperDash.asp"), rd("www", "reaper_shell.asp")
di, db = block(d)
si, sb = block(sh)
check("both pages have a 680 px phone block", db != "" and sb != "")

check("shell phone: language row and group headings hidden", ".raillang,.grp{display:none}" in sb, sb)
base = d.find(".raillang{display:flex")
hide = re.search(r"\n  (\.rail )?\.raillang,\.grp\{display:none\}", db)
check("dashboard phone: language row and group headings hidden, by a rule that wins over the base .raillang rule",
      hide is not None and (hide.group(1) is not None or 0 <= base < di), (base, di, hide and hide.group(0)))

for name, rule in [
    ("About tile keeps only its mark", ".railabout>span:last-child{display:none}"),
    ("About tile sits in the row", ".railabout{margin-top:0;padding:0 0 0 6px;border-top:0;position:static;flex:0 0 auto;background:transparent}"),
]:
    check("both phone strips: " + name, rule in db and rule in sb)

def nums(b, item):
    def g(p):
        m = re.search(p, b)
        return m.group(1) if m else None
    return {
        "rail padding": g(r"\.rail\{[^}]*?padding:([^;]+);"),
        "clock padding": g(r"\.railclock\{padding:([^;]+);"),
        "clock size": g(r"\.railclock \.rc-time\{font-size:([^}]+)\}"),
        "item height": g(re.escape(item) + r"\{[^}]*height:([0-9]+px)"),
        "active bar": g(re.escape(item) + r"\.on::before\{([^}]+)\}"),
        "logo": g(r"\.brand img\{([^}]+)\}"),
    }
dn, sn = nums(db, ".nav a"), nums(sb, "a.item")
for k in ["rail padding", "clock padding", "clock size", "item height", "active bar", "logo"]:
    check("same %s on both phone strips (%s)" % (k, dn[k]), dn[k] is not None and dn[k] == sn[k], (dn[k], sn[k]))
check("phone logo is capped at its row on both pages",
      "max-width:100%" in (dn["logo"] or "") and ".brand{min-width:0}" in db and "min-width:0" in sb[sb.find(".top .brand{"):][:80])
check("edited files stay ASCII", all(ord(c) < 128 for c in d + sh))
print("%d failure(s)" % len(fails))
for x in fails: print("  " + x)
sys.exit(1 if fails else 0)
