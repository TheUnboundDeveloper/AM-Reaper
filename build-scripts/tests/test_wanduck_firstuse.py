#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wanduck no longer runs a first-use captive portal for the stock setup wizard (2026-10-12).

WHY THIS EXISTS. wanduck sets isFirstUse = !x_Setting. Reaper keeps x_Setting at 0 on a factory
box so it is discoverable as an AiMesh node (obd gates on it), which also re-armed three stock
first-use behaviours written for the ASUS wizard: every HTTP request answered with a redirect to
/QIS_default.cgi?flag=welcome (the whole wizard, after login), the "direct rule" (all HTTP to the
router) held on a CONNECTED box, and the same hold in the load-balance branch. Reaper has no setup
wizard: the box is usable at once and the dashboard banner reports its state.

WHAT IT PINS (source): the captive branch is dead (`if(0 && isFirstUse)`) and its two redirect
strings still sit inside it (the branch is kept, not deleted, so the GPL merge diff stays small);
the CONNED first-use direct-rule arm is gone; the load-balance hold reads DISCONN only; the init
site logs the marker string the staged rc binary is checked for; the flag itself still exists (it
gates the harmless first-use DNS probe and autodet).

Exit 0 pass, 1 fail, 77 skipped (no tree: pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WD = os.path.join(SRC, "rc", "wanduck.c") if SRC else ""
if not WD or not os.path.isfile(WD):
    skip("no router tree with rc/wanduck.c (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def nocomment(s):
    # the reaper comments at the closed sites QUOTE the removed stock code
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return "\n".join(l for l in s.splitlines() if not l.lstrip().startswith("//"))

raw = open(WD, encoding="utf-8", errors="replace").read()
check("the closed sites are explained in reaper comments", raw.count("reaper 2026-10-12") >= 3, raw.count("reaper 2026-10-12"))
wd = nocomment(raw)

# -- the flag still exists and is set from x_Setting (unchanged stock) --------------------------
check("isFirstUse is still derived from x_Setting", re.search(r'if\(nvram_match\("x_Setting", "1"\)\)\s*\n\s*isFirstUse = 0;', wd) is not None)
check("the init site logs the marker string", "reaper: no first-use captive" in wd)

# -- the captive redirect branch is dead, with both redirect strings inside it ------------------
start = wd.find("if(0 && isFirstUse){")
check("the captive redirect branch is dead (if(0 && isFirstUse))", start >= 0)
if start >= 0:
    end = wd.find("else if(conn_changed_state[wan_unit] == C2D", start)
    blk = wd[start:end] if end > start else ""
    check("the dead branch still holds the welcome redirect (kept, not deleted)", "/QIS_default.cgi?flag=welcome" in blk)
    check("the dead branch still holds the repeater sitesurvey redirect", "/QIS_default.cgi?flag=sitesurvey" in blk)
    check("no live redirect to QIS_default.cgi remains outside the dead branch",
          wd.count("/QIS_default.cgi") == blk.count("/QIS_default.cgi"), wd.count("/QIS_default.cgi"))
check("no live if(isFirstUse) captive branch remains", re.search(r"\n\tif\(isFirstUse\)\{\s*\n#ifdef RTCONFIG_WIRELESSREPEATER", wd) is None)

# -- the CONNED first-use direct-rule arm is gone --------------------------------------------------
check("the CONNED && isFirstUse direct-rule arm is gone",
      re.search(r"else if\(cross_state == CONNED && isFirstUse\)\s*\{", wd) is None)
check("the DISCONN direct-rule arm is still there", re.search(r"if\(cross_state == DISCONN\)\{\s*\n\s*_dprintf\(\"\\n# Enable direct rule\\n\"\);", wd) is not None)

# -- the load-balance hold reads DISCONN only -------------------------------------------------------
check("the LB branch no longer holds the direct rule on first use", "cross_state == DISCONN || isFirstUse" not in wd)
check("the LB branch keeps its DISCONN hold", re.search(r"if\(cross_state == DISCONN\)\{\s*\n\s*if\(!rule_setup\)\{", wd) is not None)

print("%d failed" % len(fails))
if fails:
    print("FAILED:"); [print("  " + f) for f in fails]
    sys.exit(1)
sys.exit(0)
