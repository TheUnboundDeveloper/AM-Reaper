#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Network page: the nested frame holds the setup panels (2026-11-10).

WHY THIS EXISTS. SDN.asp frames the stock network app (/SDN/sdn.html) in #sdn_iframe; the app cannot scroll,
so the frame must be as tall as what it shows. A setup panel (.popup_container) is absolutely positioned: it
never changes the document's own size, and stock sizes the frame once, as the panel opens - but the panel opens
with a slide. Measured in headless Edge through the mock: 681 px at stock's call, 1047 px 400 ms later, so the
bottom 340 px of every network type's setup (the Apply button with it) was cut off. reaperGrowFrame() now counts
each shown panel's bottom + 30 px, observes the panels, and fits again after a click.

WHAT IT DOES. Cuts reaperGrowFrame() out of SDN.asp and MLO.asp and runs it under node against a small fake
document: a shown panel grows the frame, a hidden one does not, the frame never shrinks, the panels are observed,
and a click schedules a fit that picks up a panel that grew afterwards.

Exit 0 pass, 1 fail, 77 skipped (no router source tree, or no node on the host)."""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
D = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN") if SRC else ""
if not D or not os.path.isfile(os.path.join(D, "SDN.asp")):
    skip("no router source tree with www/sysdep/FUNCTION/SDN/SDN.asp (argv[1] or REAPER_ROUTER_SRC)")
if not shutil.which("node"):
    skip("no node on the host")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

HARNESS = r"""
const timers = []; global.setTimeout = (f, ms) => { timers.push([f, ms]); return timers.length; };
const observed = []; let roCb = null;
class RO { constructor(cb){ roCb = cb; } observe(e){ observed.push(e.name); } disconnect(){} }
global.ResizeObserver = RO; global.window = { ResizeObserver: RO };
const P = [ { name: 'p1', display: 'flex', b: 665, h: 635 }, { name: 'p2', display: 'none', b: 5000, h: 4000 }, { name: 'p3', display: 'none', b: 0, h: 0 } ];
P.forEach(p => { p.getBoundingClientRect = () => ({ bottom: p.b, height: p.h }); });
const listeners = [];
const body = { name: 'body', scrollHeight: 731 }, html = { name: 'html', scrollHeight: 731 };
const d = { documentElement: html, body, defaultView: { pageYOffset: 0, getComputedStyle: (p) => ({ display: p.display }) },
  querySelectorAll: (s) => (s === '.popup_container' ? P : []), addEventListener: (t, f, c) => listeners.push([t, f, c]) };
const ifr = { contentDocument: d, style: {}, _h: 731, get offsetHeight(){ return this.style.height ? parseFloat(this.style.height) : this._h; } };
const out = {};
FN
reaperGrowFrame(ifr);
out.afterLoad = ifr.offsetHeight;                       // one short panel shown, a tall hidden one: nothing to grow
out.observed = observed.slice();
out.listeners = listeners.map(l => [l[0], l[2]]);
out.loadTimers = timers.map(t => t[1]);
P[1].display = 'flex'; P[1].b = 1077; P[1].h = 1047;      // the second panel is shown and has finished its slide
roCb();
out.afterPanel = ifr.offsetHeight;
P[1].b = 400; P[1].h = 370; roCb();                      // it gets shorter: stock owns shrinks
out.afterShorter = ifr.offsetHeight;
P[1].b = 1500; P[1].h = 1470;                            // it grows again with no observation delivered...
timers.length = 0; listeners.filter(l => l[0] === 'click').forEach(l => l[1]());
out.clickTimers = timers.map(t => t[1]);
out.beforeClickTimers = ifr.offsetHeight;
timers.slice().forEach(t => t[0]());                     // ...and the timers a click set pick it up
out.afterClickTimers = ifr.offsetHeight;
body.scrollHeight = 2000; html.scrollHeight = 2000; roCb();
out.afterDocGrew = ifr.offsetHeight;                     // the document's own height still counts
console.log(JSON.stringify(out));
"""
for page in ("SDN.asp", "MLO.asp"):
    src = open(os.path.join(D, page), encoding="utf-8", errors="surrogateescape").read().replace("\r\n", "\n")
    m = re.search(r"^function reaperGrowFrame\(ifr\)\{\n.*?^\}\n", src, re.S | re.M)
    check(page + ": reaperGrowFrame() is a block the test can cut out", m is not None)
    if not m:
        continue
    fn = m.group(0)
    check(page + ": it counts the shown panels and observes them",
          'd.querySelectorAll(".popup_container")' in fn and "ro.observe(pc[k])" in fn and 'display=="none"' in fn)
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "h.js"); open(f, "w", encoding="utf-8").write(HARNESS.replace("FN", fn))
        r = subprocess.run(["node", f], capture_output=True, text=True)
    try:
        o = json.loads(r.stdout.strip().split("\n")[-1])
    except Exception:
        check(page + ": the function runs under node", False, r.stdout + r.stderr); continue
    check(page + ": a short shown panel and a tall HIDDEN one leave the frame alone", o["afterLoad"] == 731, o)
    check(page + ": the body, the root and all three panels are observed",
          sorted(o["observed"]) == ["body", "html", "p1", "p2", "p3"], o["observed"])
    check(page + ": a shown panel ending at 1077 makes the frame 1107 (its bottom + 30)", o["afterPanel"] == 1107, o)
    check(page + ": a panel that gets shorter does not shrink the frame", o["afterShorter"] == 1107, o)
    check(page + ": one capturing click listener, two fits after it", o["listeners"] == [["click", True]] and len(o["clickTimers"]) == 2
          and min(o["clickTimers"]) >= 400, (o["listeners"], o["clickTimers"]))
    check(page + ": those fits pick up a panel that grew with no observation", o["beforeClickTimers"] == 1107 and o["afterClickTimers"] == 1530, o)
    check(page + ": the document's own height still grows the frame", o["afterDocGrew"] == 2000, o)
    check(page + ": the load-time fits are kept", o["loadTimers"] == [400, 1200], o["loadTimers"])

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  " + f)
sys.exit(1 if fails else 0)
