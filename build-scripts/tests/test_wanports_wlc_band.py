#!/usr/bin/env python3
"""WAN Ports (Dual WAN) tab in router mode whatever wlc_band holds (field report, RT-BE88U v3.6.1, 2026-10-29).

WHY. wlc_band names the uplink band of a wireless client (repeater, media bridge, WISP), but a router can hold one
too: the field box, set up from scratch in router mode (sw_mode 1, dualwan in rc_support), read wlc_band=-1. Both
menu rules - state.js dualWAN_support (read by menuTree.js) and reaper/menu.js - hid the tab whenever it was set.
The page itself still opened by URL. In router mode only the dualwan support flag decides now; every other mode
keeps the stock rule.

WHAT IT DOES. Finds the dualWAN_support line in state.js and evaluates it under node for every mode x wlc_band x
dualwan combination against the expected table; checks menu.js carries the same rule (its runtime cases are in
test_reaper_menu.py).
"""
import json, os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "state.js")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

st = rd("www", "state.js")
lines = re.findall(r"(?m)^var dualWAN_support = .*;$", st)
check("state.js has exactly one dualWAN_support line", len(lines) == 1, lines)
check("state.js: wlc_band is ignored in router mode", lines == ['var dualWAN_support = (wlc_band != "" && !isSwMode("rt")) ? false : isSupport("dualwan");'], lines)
mn = rd("www", "reaper", "menu.js")
check("menu.js: the same rule", "var dualWAN = (is('rt') || (F.wlc_band || '') === '') && sup('dualwan');" in mn)
# require/menuTrees/menuTree.js is the copy www/Makefile installs as require/modules/menuTree.js
check("menuTree.js still hides the tab from dualWAN_support", 'if(!dualWAN_support){\nretArray.push("Reaper_WANPorts.asp");' in
      re.sub(r"\n\s+", "\n", rd("www", "require", "menuTrees", "menuTree.js")))

node = shutil.which("node")
if lines and node:
    # '-1' is the field value (RT-BE88U router, 2026-10-29)
    js = ("var out = {};\n['rt', 'wisp', 'rp', 'mb', 'ap'].forEach(function(m){ ['', '1', '-1'].forEach(function(b){ [0, 1].forEach(function(d){\n"
          "  var wlc_band = b, isSwMode = function(x){ return x == m; }, isSupport = function(x){ return x == 'dualwan' && d == 1; };\n"
          "  " + lines[0] + "\n  out[m + '/' + (b || '-') + '/' + d] = dualWAN_support ? 1 : 0; }); }); });\n"
          "console.log(JSON.stringify(out));\n")
    r = subprocess.run([node, "-e", js], capture_output=True, text=True)
    check("the state.js rule runs under node", r.returncode == 0, r.stderr[-300:])
    if r.returncode == 0:
        o = json.loads(r.stdout.strip().splitlines()[-1])
        want = {}
        for m in ("rt", "wisp", "rp", "mb", "ap"):
            for b in ("-", "1", "-1"):
                for d in (0, 1):
                    want["%s/%s/%d" % (m, b, d)] = 1 if d and (m == "rt" or b == "-") else 0
        check("router: dualwan flag alone decides; other modes: hidden while wlc_band is set (stock)", o == want,
              {k: (o.get(k), v) for k, v in want.items() if o.get(k) != v})
elif not node:
    print("note: node not found - the runtime check is skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
