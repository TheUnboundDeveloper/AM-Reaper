#!/usr/bin/env python3
"""Network page > Guest Portal > Print: the quick-connect sheet stays open until it is printed (owner, 2026-11-14).

WHY. The sheet (QR code, network name, passcode) opened and closed itself in under a second. The page wrote the sheet
into a new window with document.write and never closed that document, then 50 ms later called print() and close() one
after the other. On a window that is still loading, print() comes straight back in current browsers, so the next line
closed the window before the print dialog was up.

WHAT CHANGED. The document is closed after the write; print() runs once, when the window has loaded (with a fallback
timer in case no load event comes); the window is closed only from its afterprint event - after the dialog is done,
whether the user printed or cancelled. The print style also names the standard print-color-adjust (the QR code is a
background image; only the -webkit- name was there).

WHAT IT DOES. Cuts the block out of sdn.js and runs it under node with a recording window and hand-driven timers: load
first, the fallback timer first, a window the user closed, both paths firing. Exit 0 pass, 1 fail, 77 skipped (no
router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router - or no node)."""
import json, os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
SJ = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js") if SRC else ""
if not SJ or not os.path.isfile(SJ):
    skip("no router tree with the Network page (argv[1] or REAPER_ROUTER_SRC)")
NODE = shutil.which("node")
if not NODE:
    skip("no node on the host")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))

sj = open(SJ, encoding="utf-8", errors="surrogateescape").read().replace("\r\n", "\n")
a = sj.find("printWin.document.write($html_cntr[0].outerHTML);")
z = sj.find("setTimeout(reaper_print_go, 1200);", a)
blk = sj[a:z + len("setTimeout(reaper_print_go, 1200);")] if 0 < a < z else ""
check("sdn.js: the print block is there", bool(blk))
check("the old back-to-back print() + close() is gone", "printWin.print();\n\t\t\t\t\t\t\tprintWin.close();" not in sj
      and sj.count("printWin.close();") == 1 and sj.count("printWin.print();") == 1)
html = open(os.path.join(os.path.dirname(SJ), "sdn.html"), encoding="utf-8", errors="surrogateescape").read()
check("print style: backgrounds (the QR code) are printed under both property names",
      "-webkit-print-color-adjust: exact;" in html and "\tprint-color-adjust: exact;" in html)

JS = r'''
function run(order, closedByUser){
  var log = [], timers = [];
  var setTimeout = function(f, ms){ timers.push({f: f, ms: ms}); };
  var $html_cntr = [{outerHTML: "<html></html>"}];
  var printWin = { closed: false, onload: null, onafterprint: null,
    document: { write: function(){ log.push("write"); }, close: function(){ log.push("doc.close"); } },
    focus: function(){ log.push("focus"); }, print: function(){ log.push("print"); },
    close: function(){ log.push("win.close"); printWin.closed = true; } };
  @@BLK@@
  var fire = function(ms){ var t = timers.filter(function(x){ return x.ms == ms; }); timers = timers.filter(function(x){ return x.ms != ms; }); t.forEach(function(x){ x.f(); }); };
  if(closedByUser) printWin.closed = true;
  order.forEach(function(step){
    if(step == "load"){ if(printWin.onload) printWin.onload(); fire(200); }
    else if(step == "fallback") fire(1200);
    else if(step == "afterprint"){ if(printWin.onafterprint) printWin.onafterprint(); }
    log.push("|" + step);
  });
  return log;
}
console.log(JSON.stringify({
  load:      run(["load", "fallback", "afterprint"]),
  fallback:  run(["fallback", "load", "afterprint"]),
  noafter:   run(["load", "fallback"]),
  userclose: run(["load", "fallback"], true)
}));
'''
if blk:
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "p.js"); open(f, "w").write(JS.replace("@@BLK@@", blk))
        r = subprocess.run([NODE, f], capture_output=True, text=True)
        try:
            o = json.loads(r.stdout)
        except Exception:
            o = None
        check("the block runs under node", o is not None, r.stderr or r.stdout)
        if o:
            check("the written document is closed before anything else",
                  all(v[:2] == ["write", "doc.close"] for v in o.values()), o)
            check("window loaded: one print, and the window is closed only after the print dialog is done",
                  o["load"] == ["write", "doc.close", "focus", "print", "|load", "|fallback", "win.close", "|afterprint"], o["load"])
            check("no load event: the fallback timer prints once; a late load does not print again",
                  o["fallback"] == ["write", "doc.close", "focus", "print", "|fallback", "|load", "win.close", "|afterprint"], o["fallback"])
            check("THE BUG: without afterprint the window is NOT closed (it used to close 50 ms after opening)",
                  "win.close" not in o["noafter"] and o["noafter"].count("print") == 1, o["noafter"])
            check("a window the user already closed is left alone (no print on a dead window)",
                  "print" not in o["userclose"] and "win.close" not in o["userclose"], o["userclose"])

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
