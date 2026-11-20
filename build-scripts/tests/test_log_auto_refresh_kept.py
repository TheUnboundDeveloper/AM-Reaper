#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""System Log: the Auto refresh box remembers the admin's choice.

WHY THIS EXISTS. The box was `checked` in the markup and nothing stored its state, so every visit started with
Auto refresh on, whatever the admin chose last time - the opposite of the Firewall page, whose two Auto refresh
switches are kept per browser. The choice is now kept the same way (localStorage `reaper_log_auto`; no nvram key,
nothing in a backup); with nothing stored, or storage refused, the box is on as before.

WHAT IT DOES. Checks the page source for the pieces, then runs the page's own restore line and change handler under
node against a stand-in box and store: nothing stored = on; switched off = stored and stays off on the next visit;
switched on again = on; a store that throws = on, and no error.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
PAGE = os.path.join(SRC, "www", "Reaper_Log.asp") if SRC else ""
if not SRC or not os.path.isfile(PAGE):
    print("SKIP: no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)"); sys.exit(77)

fails = []
def check(label, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        fails.append(label + ((": " + str(detail)) if detail else ""))

s = open(PAGE, encoding="utf-8", errors="replace").read()
restore = re.search(r"^\s*(try \{ if \(localStorage\.getItem\('reaper_log_auto'\) === '0'\) q\('c_auto'\)\.checked = false; \} catch \(e\) \{\})\s*$", s, re.M)
handler = re.search(r"^\s*on\('c_auto', 'change', (function\(\)\{.*?schedule\(\); \})\);\s*$", s, re.M)
check("the box is on in the markup (the state with nothing stored)", '<input type="checkbox" id="c_auto" checked>' in s)
check("the stored choice is read", restore is not None)
check("a change stores the choice, then reschedules", handler is not None and "localStorage.setItem('reaper_log_auto'" in handler.group(1))
check("the bare handler is gone", "on('c_auto', 'change', schedule);" not in s)
if restore:
    first_sched = s.find("  schedule(); dirty();")
    check("the choice is restored before the first schedule()", 0 < restore.start() < first_sched, (restore.start(), first_sched))
check("the poll still runs only while the box is on", "if (q('c_auto').checked) timer = setInterval(" in s)

node = shutil.which("node")
if not node:
    print("note: node not found - the page was checked statically only")
elif restore and handler:
    js = r'''
var R = process.argv[2], H = process.argv[3];
function run(store, actions){
  var box = { checked: true }, scheduled = 0, err = null;
  var q = function(){ return box; }, schedule = function(){ scheduled++; };
  var localStorage = store;
  try { eval(R); } catch (e) { err = String(e); }
  var onchange = null;
  try { eval('onchange = ' + H + ';'); } catch (e) { err = String(e); }
  var out = [box.checked];
  (actions || []).forEach(function(v){ box.checked = v; try { onchange(); } catch (e) { err = String(e); } out.push(box.checked); });
  return { states: out, scheduled: scheduled, err: err };
}
function mem(init){ var d = init || {}; return { getItem: function(k){ return k in d ? d[k] : null; }, setItem: function(k, v){ d[k] = String(v); }, _d: d }; }
var a = mem();                       /* first visit */
var r1 = run(a, [false]);            /* admin switches it off */
var s1 = a._d.reaper_log_auto;       /* what is stored at that moment */
var r2 = run(a, []);                 /* next visit */
var r3 = run(a, [true]);             /* switches it on again */
var r4 = run(a, []);                 /* next visit */
var bad = { getItem: function(){ throw new Error('refused'); }, setItem: function(){ throw new Error('refused'); } };
var r5 = run(bad, [false]);
console.log(JSON.stringify({ r1: r1, stored1: s1, r2: r2, r3: r3, r4: r4, stored4: a._d.reaper_log_auto, r5: r5 }));
'''
    w = tempfile.mkdtemp(prefix="rlogauto_")
    try:
        p = os.path.join(w, "t.js"); open(p, "w").write(js)
        r = subprocess.run([node, p, restore.group(1), handler.group(1)], capture_output=True, text=True, timeout=30)
        check("node: the page's restore line and handler run", r.returncode == 0 and r.stdout.strip().startswith("{"), (r.stderr or r.stdout)[-600:])
        if r.returncode == 0 and r.stdout.strip().startswith("{"):
            o = json.loads(r.stdout.strip().splitlines()[-1])
            check("nothing stored: the box starts on", o["r1"]["states"][0] is True)
            check("switched off: stored, rescheduled", o["stored1"] == "0" and o["r1"]["states"][1] is False and o["r1"]["scheduled"] == 1, o["r1"])
            check("next visit: still off", o["r2"]["states"] == [False], o["r2"])
            check("switched on again and kept on", o["r3"]["states"] == [False, True] and o["r4"]["states"] == [True] and o["stored4"] == "1", (o["r3"], o["r4"]))
            check("a store that refuses: on, the handler still reschedules, no error",
                  o["r5"]["states"][0] is True and o["r5"]["scheduled"] == 1 and o["r5"]["err"] is None, o["r5"])
    finally:
        shutil.rmtree(w, ignore_errors=True)

if fails:
    print("FAIL test_log_auto_refresh_kept (%d)" % len(fails))
    for f in fails:
        print("  - " + f[:600])
    sys.exit(1)
print("PASS test_log_auto_refresh_kept")
