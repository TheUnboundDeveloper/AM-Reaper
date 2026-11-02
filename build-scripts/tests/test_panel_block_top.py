#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stock pop-up panels open in the part of the page the user can SEE inside reaper_shell.asp (owner, 2026-11-01).

WHY THIS EXISTS. form.js adjust_panel_block_top() places a panel (the AiMesh client card, VPN/port-forward
editors, notification and schedule panels) at "this page's scrollTop + offset". Inside reaper_shell.asp the
framed page never scrolls - the shell grows its frame to the content and the browser window scrolls - so
scrollTop was always 0 and the AiMesh client card opened near the top of the page, out of sight once the user
had scrolled (measured in the shell: 410 px above the screen at scroll 500). The fix centres the panel in the
visible slice the shell publishes (--rv-top / --rv-h), refreshed synchronously through the shell's
reaperAnchorNow(), measured against the panel's containing block.

WHAT IT CHECKS, by running the real function from www/form.js in node with a stubbed page:
  (1) in the shell: centred in the slice; a panel taller than the slice starts at the slice top + the offset;
      a positioned containing block is subtracted; the shell's sync refresh runs BEFORE the slice is read;
  (2) outside the shell (no --rv-top): the stock scrollTop + offset, untouched;
  (3) the shell exports reaperAnchorNow next to reaperAnchorOverlays.
Exit 0 pass, 1 fail, 77 skipped (no router source tree / no node).
"""
import json, os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
FORM = os.path.join(SRC, "www", "form.js") if SRC else ""
if not FORM or not os.path.isfile(FORM):
    print("SKIP: no router source tree"); sys.exit(77)
NODE = shutil.which("node")
if not NODE:
    print("SKIP: no node"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(FORM, encoding="utf-8").read()
m = re.search(r"function adjust_panel_block_top\(_objID, _offsetHeight\) \{.*?\n\}\n", src, re.S)
check("adjust_panel_block_top() found in form.js", m is not None)
fn = m.group(0) if m else ""
check("the shell branch reads --rv-top / --rv-h", "--rv-top" in fn and "--rv-h" in fn)
shell = open(os.path.join(SRC, "www", "reaper_shell.asp"), encoding="utf-8", errors="replace").read()
check("reaper_shell.asp exports the synchronous anchor (reaperAnchorNow = anchorNow)", "window.reaperAnchorNow=anchorNow;" in shell)

HARNESS = r"""
const FN = %s;
function run(c) {
  const log = [];
  const docStyle = { v: {}, getPropertyValue(k) { return this.v[k] || ""; } };
  const el = { offsetHeight: c.h, style: { setProperty(k, v, p) { el.top = v; el.prio = p; } },
               offsetParent: c.cb ? { pos: c.cb.pos, getBoundingClientRect() { return { top: c.cb.top }; } } : null };
  const shellWin = { reaperAnchorNow() { log.push("anchorNow"); if (c.shell) { docStyle.v["--rv-top"] = c.rvTop + "px"; docStyle.v["--rv-h"] = c.rvH + "px"; } } };
  const g = {
    document: { getElementById() { return el; }, documentElement: { style: docStyle, scrollTop: 0 }, body: { scrollTop: 0 } },
    window: { pageYOffset: c.scroll || 0 }, getComputedStyle(x) { return { position: x.pos }; },
    isSupport() { return false; }, top: {}, parent: c.framed ? shellWin : undefined,
  };
  g.window.parent = c.framed ? shellWin : g.window;
  if (!c.framed) g.parent = g.window;
  const f = new Function("document", "window", "parent", "getComputedStyle", "isSupport", "top",
                         FN + "\nreturn adjust_panel_block_top;")(g.document, g.window, g.parent, g.getComputedStyle, g.isSupport, g.top);
  f("edit_client_block", c.offset);
  return { top: el.top, prio: el.prio, log };
}
const cases = %s;
console.log(JSON.stringify(cases.map(run)));
"""
cases = [
    {"framed": True, "shell": True, "rvTop": 501, "rvH": 710, "h": 400, "offset": 10, "cb": {"pos": "static", "top": 0}},
    {"framed": True, "shell": True, "rvTop": 501, "rvH": 370, "h": 400, "offset": 10, "cb": {"pos": "static", "top": 0}},
    {"framed": True, "shell": True, "rvTop": 501, "rvH": 710, "h": 400, "offset": 10, "cb": {"pos": "relative", "top": 300}},
    {"framed": False, "shell": False, "h": 400, "offset": 10, "scroll": 120, "cb": None},
    {"framed": True, "shell": False, "h": 400, "offset": 10, "scroll": 0, "cb": None},
]
if fn:
    r = subprocess.run([NODE, "-e", HARNESS % (json.dumps(fn), json.dumps(cases))], capture_output=True, text=True)
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        out = None
    check("the function runs in node", out is not None, r.stderr[-600:])
    if out:
        check("shell: centred in the visible slice (501 + (710-400)/2 = 656)", out[0]["top"] == "656px" and out[0]["prio"] == "important", out[0])
        check("shell: refreshes the slice synchronously before reading it", out[0]["log"] == ["anchorNow"], out[0])
        check("shell: a panel taller than the slice starts at its top + the offset (511)", out[1]["top"] == "511px", out[1])
        check("shell: a positioned containing block is subtracted (656 - 300 = 356)", out[2]["top"] == "356px", out[2])
        check("outside the shell: stock scrollTop + offset (130)", out[3]["top"] == "130px", out[3])
        check("framed by something that is not the shell: stock path (no slice published)", out[4]["top"] == "10px", out[4])

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
