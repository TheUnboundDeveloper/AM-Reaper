#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Network page: the live main network cannot be deleted by accident (2026-11-23, REAPER-MAINFH-GUARD).

WHY. The stock Network page script (www/sysdep/FUNCTION/SDN/SDN/sdn.js) had two weaknesses next to the backlog item
"Delete does nothing on a main-network card":
  1. Delete on a main network (MAINFH) was refused only when ONE MAINFH row existed. A Smart Connect change leaves empty
     MAINFH rows behind (apmN_enable 0, no SSID, no dut_list - two of them after a Smart Connect change on 2026-09-06),
     so with such rows present the LIVE main network could be deleted and the router left without its main Wi-Fi.
  2. The Smart Connect clean-up in apply_profile (another main network on the ticked bands is removed) ran on EVERY
     network's Apply and counted ticked band boxes over the whole document, so an Apply on a guest network could put
     the live main network on the delete list (sdn_rl_x).
  3. The Delete confirm opens 4% from the top of a page the shell frame grows to its full height: pressed on a card
     further down, it opened out of sight - the likely "Delete does nothing".

WHAT IT CHECKS. Source pins for the three changes and that the old forms are gone; then, with node, the guard's own
condition (lifted from the page) against row sets shaped like the router's: one live row plus empty rows (deleting
the live one is refused, an empty one may go), two live rows (either may go), a single row (refused), a live row plus
a row the firmware set aside (apmN_disabled 1: refused). Exit 0 pass, 1 fail, 77 skipped (no router source tree, or a
tree without the Network page).
"""
import json, os, re, shutil, subprocess, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js")
if not SRC or not os.path.isfile(P):
    skip("no router source tree with the Network page (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
js = open(P, encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

M = "REAPER-MAINFH-GUARD"
check("the three changes and the helpers carry the marker (5)", js.count(M) == 5, js.count(M))
check("the old guard (any single MAINFH row) is gone",
      'if(sdn_all_rl_json.filter(item => item.sdn_rl.sdn_name === "MAINFH").length == 1){' not in js)
g = js.find("const mfh_rows = sdn_all_rl_json.filter(")
gb = js[g:js.find("$(\".container\").addClass(\"blur_effect\");", g)] if g > 0 else ""
check("the guard counts live rows and keeps the stock notice", "reaper_mainfh_live(mfh_me)" in gb
      and "show_customize_alert(`<#SDN_MainFH_keep_Hint#>`);" in gb and "return;" in gb, gb[:300])
check("the notice is brought into view", 'reaper_popup_into_view(".popup_container.popup_customize_alert");' in gb)
check("the Delete confirm is brought into view",
      'setTimeout(function(){ reaper_popup_into_view(".popup_container.popup_element_second"); }, 0);' in js)
check("the Smart Connect clean-up runs on a main network's Apply only", 'if(isSupport("sdn_mwl") && is_sdn_mainfh){' in js)
check("...and counts this panel's band boxes, not the whole page's",
      'const smart_connect_enable = $(_obj).find("#checkbox_wifi_band [data-component=checkbox_val].clicked").length > 1' in js
      and 'const smart_connect_enable = $("[data-component=checkbox_val].clicked").length > 1' not in js)
check("the helpers are defined once", js.count("function reaper_mainfh_live(_item){") == 1 and js.count("function reaper_popup_into_view(_sel){") == 1)

node = shutil.which("node")
if not node:
    print("node not found - the guard's condition is not run (source pins only)")
elif "function reaper_mainfh_live(_item){" not in js or "if(mfh_rows.length <= 1 ||" not in gb:
    check("the guard's condition is there to run", False)
else:
    i = js.find("function reaper_mainfh_live(_item){")
    live_fn = js[i:js.index("\n}\n", i) + 3]
    c = gb.find("if(mfh_rows.length <= 1 ||")
    cond = gb[c + 3:gb.index("){\n", c)] if c >= 0 else "true"
    row = lambda idx, en, ssid, dut, dis="0": {"sdn_rl": {"idx": idx, "sdn_name": "MAINFH"},
                                              "apg_rl": {"enable": en, "ssid": ssid, "dut_list": dut, "disabled": dis}}
    live3, e4, e5 = row("3", "1", "VieNet", "<*>87>"), row("4", "0", "", ""), row("5", "0", "", "")
    live6, aside = row("6", "1", "Second", "<*>40>"), row("7", "1", "Old", "<*>40>", "1")
    cases = [("one live row + two empty rows: deleting the live one is refused", [live3, e4, e5], live3, True),
             ("...an empty row may go", [live3, e4, e5], e4, False),
             ("two live rows: either may go", [live3, live6, e4], live3, False),
             ("a single main-network row is refused", [live3], live3, True),
             ("a single EMPTY row is refused too (stock rule kept)", [e4], e4, True),
             ("a live row + a row the firmware set aside: deleting the live one is refused", [live3, aside], live3, True)]
    prog = (live_fn + "\nconst cases = " + json.dumps([[n, rows, me] for n, rows, me, _ in cases]) + ";\n"
            "const out = cases.map(([n, sdn_all_rl_json, _profile_data]) => {\n"
            "  const mfh_rows = sdn_all_rl_json.filter(item => item.sdn_rl.sdn_name === \"MAINFH\");\n"
            "  const mfh_me = mfh_rows.find(item => item.sdn_rl.idx == _profile_data.sdn_rl.idx) || _profile_data;\n"
            "  return !!(" + cond + ");\n});\nconsole.log(JSON.stringify(out));\n")
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True, timeout=60)
    got = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip().startswith("[") else None
    check("node ran the guard's condition", got is not None, r.stderr[-300:])
    for k, (n, _, _, want) in enumerate(cases):
        check(n, got is not None and got[k] == want, got)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
