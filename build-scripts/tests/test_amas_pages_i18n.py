#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every string the AiMesh pages show exists in every language pack (2026-10-12).

WHY THIS EXISTS. The AiMesh add-node and node-mode flows run inside the kept QIS wizard
(sysdep/FUNCTION/QIS_V3/mobile/pages/amas*_page.html) and the AiMesh page itself (aimesh/*.html).
Their text is dictionary tokens, so a page is only as translated as the packs behind it: a token that
is missing from one pack renders as its raw name in that language, and a token that exists only in
EN.dict silently breaks the lockstep the build depends on. The owner asked (2026-10-12) that the AiMesh
information and pages support every language the router ships. This pins it.

WHAT IT PINS. For every `<#KEY#>` in those pages: the key exists in all 25 packs (same key set,
non-empty value in each); the nine RAMS_* keys of the search page are among them; the packs stay in
lockstep (equal line counts); and no value contains a double quote (it would break the HTML
attribute the subtitle tooltip uses). Also: the search fragment carries the tooltip attribute on the
subtitle and the prerequisites box, and the theme sheet clips the subtitle and the buttons with an
ellipsis (the overflow rule, reaper-ui 26/41) instead of letting a long language stretch the page.

Exit 0 pass, 1 fail, 77 skipped (no tree: pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import glob, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WWW = os.path.join(SRC, "www") if SRC else ""
QIS = os.path.join(WWW, "sysdep", "FUNCTION", "QIS_V3", "mobile", "pages")
if not WWW or not os.path.isdir(QIS) or not os.path.isfile(os.path.join(WWW, "EN.dict")):
    skip("no router tree with www/EN.dict and the QIS_V3 pages (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

pages = sorted(glob.glob(os.path.join(QIS, "amas*_page.html")) + glob.glob(os.path.join(WWW, "aimesh", "*.html")))
check("AiMesh pages found (9 wizard fragments + the aimesh/ pages)", len(pages) >= 9, len(pages))
tokens = {}
for p in pages:
    s = open(p, encoding="utf-8", errors="replace").read()
    for k in re.findall(r"<#([A-Za-z0-9_]+)#>", s):
        tokens.setdefault(k, set()).add(os.path.basename(p))
check("the pages use dictionary tokens", len(tokens) > 20, len(tokens))
for k in ["RAMS_%d" % i for i in range(1, 10)]:
    check("search page uses %s" % k, "amassearch_page.html" in tokens.get(k, set()))

packs = sorted(p for p in glob.glob(os.path.join(WWW, "*.dict")) if os.path.basename(p) != "temp.dict")
check("25 language packs", len(packs) == 25, len(packs))
counts = {}
values = {}
for p in packs:
    lang = os.path.basename(p)[:-5]
    raw = open(p, "rb").read().decode("utf-8", errors="replace")
    lines = raw.split("\n")
    counts[lang] = len(lines)
    d = {}
    for ln in lines:
        if "=" in ln and not ln.startswith("#"):
            k, _, v = ln.partition("=")
            d[k] = v
    values[lang] = d
check("packs in lockstep (equal line counts)", len(set(counts.values())) == 1, counts)

missing = []
empty = []
quoted = []
for k in sorted(tokens):
    for lang in values:
        if k not in values[lang]:
            missing.append("%s:%s" % (lang, k))
        elif values[lang][k].strip() == "":
            empty.append("%s:%s" % (lang, k))
        elif '"' in values[lang][k] and k.startswith("RAMS_"):
            quoted.append("%s:%s" % (lang, k))
check("every AiMesh-page key exists in every pack", not missing, ", ".join(missing[:12]))
check("no AiMesh-page key is empty in any pack", not empty, ", ".join(empty[:12]))
check("no RAMS_ value carries a double quote (tooltip attribute safety)", not quoted, ", ".join(quoted[:12]))
check("RAMS_1 differs per language (really translated, not English copied)",
      len(set(values[l].get("RAMS_1", "") for l in values)) >= 20)

frag = open(os.path.join(QIS, "amassearch_page.html"), encoding="utf-8", errors="replace").read()
check("subtitle carries a tooltip with the full text", 'class="titleSub" title="<#RAMS_1#>"' in frag)
check("prerequisites box present", 'class="rqs_box"' in frag and 'class="rqs_list"' in frag)
sheet_p = os.path.join(WWW, "reaper_qis.css")
sheet = open(sheet_p, encoding="utf-8", errors="replace").read() if os.path.isfile(sheet_p) else ""
check("theme sheet clips the subtitle (ellipsis, not a stretched column)",
      re.search(r"\.titleSub\{[^}]*text-overflow:ellipsis", sheet) is not None)
check("theme sheet clips the desktop buttons",
      re.search(r"\.desktop_applyBtn[^{]*\{[^}]*text-overflow:ellipsis", sheet) is not None)
check("theme sheet clips the mobile buttons",
      re.search(r"\.mobile_applyBtn[^{]*\{[^}]*text-overflow:ellipsis", sheet) is not None)

print("%d failed" % len(fails))
if fails:
    print("FAILED:"); [print("  " + f) for f in fails]
    sys.exit(1)
sys.exit(0)
