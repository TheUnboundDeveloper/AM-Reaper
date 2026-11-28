#!/usr/bin/env python3
"""A dialog taller than the screen is reachable with the page scrollbar (owner 2026-11-28, REAPER-DLG-TALL).

WHY. The shell grows the page frame to the framed page's full height, so inside a page "vh" and position:fixed mean the
whole document. The shell re-anchors a page's dialog backdrop to the slice of the frame that is on screen and keeps it
there while the user scrolls - so a dialog TALLER than that slice (the Devices picture + type dialog at 1080p, the
Network new-network wizard) hung out of it top and bottom and its buttons could never be reached; the "max-height:NNvh"
scroll areas inside those dialogs limited nothing.

WHAT IT CHECKS.
- The shell's watcher, run under node against a small layout model: a dialog that fits is left alone; a taller one is
  pinned (data-rv-tall + --rv-pin = the slice top at that moment) and the frame is re-fitted; scrolling never moves or
  releases a pinned dialog; a dialog that fits again is released; a removed dialog re-fits the frame; a scroll that
  shortens the slice pins a dialog that no longer fits; a pinned box left wholly out of view by a change is pinned again.
- The sheet the shell gives a framed page: the pinned rule (border-box, min-height 100%, padding from --rv-pin) and no
  scrolling inside a framed backdrop.
- The frame fit counts a pinned dialog by its box and exports reaperFrameFit().
- The Devices, Network and AiMesh dialogs carry no viewport-unit cap and no scroll area of their own; opened without the
  shell their backdrop scrolls.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www/reaper_shell.asp")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda *p: open(os.path.join(SRC, *p), encoding="latin-1").read()
sh = rd("www", "reaper_shell.asp")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

# ---- the sheet
check("shell: the framed backdrops include the Speed page's (.dlg)", "+ '.veil,.ovl,#ovl,.applying,.overlay,.fbov,.scrim,.dlg{'" in sh)
check("shell: a framed dialog backdrop never scrolls", "+ '.ovl,#ovl,.overlay,.fbov,.dlg{overflow:visible!important}'" in sh)
check("shell: the pinned rule (whole page, border-box, box at --rv-pin + 16px)",
      "[data-rv-tall][data-rv-tall],#ovl[data-rv-tall]{top:0!important;height:auto!important;min-height:100%!important;" in sh
      and "box-sizing:border-box!important;align-items:flex-start!important;" in sh
      and "padding-top:calc(var(--rv-pin,0px) + 16px)!important;padding-bottom:16px!important}" in sh
      and "[data-rv-tall]>*{margin-top:0!important;margin-bottom:0!important;flex-shrink:0!important}" in sh)
# ---- the frame fit
check("shell: the frame fit counts a pinned dialog by its box, not its backdrop",
      "t=d.querySelectorAll('[data-rv-tall]');" in sh and "m=Math.max(m, c[j].getBoundingClientRect().bottom+16);" in sh
      and "if(k[i].hasAttribute('data-rv-tall')) continue;" in sh)
check("shell: reaperFrameFit() re-fits both ways", "window.reaperFrameFit=function(){ lastEst=-1; fit(); };" in sh)
check("shell: the watcher starts on reaper-native pages only, with the load",
      "dlgWatch(d, nat);" in sh and "nat=!!(d && d.querySelector('meta[name=\"reaper-native\"]'))" in sh)
check("shell: content, class and style changes are watched; a window resize too",
      "dlgMo.observe(d.body, {childList:true, subtree:true, attributes:true, attributeFilter:['class','style','hidden']});" in sh
      and "window.addEventListener('resize', dlgSoon);" in sh)

START, END = "(function(){\n  var f=$id('page_frame');\n  if(!f) return;\n  var HDR=64;", "  window.addEventListener('resize', dlgSoon);\n})();\n"
a = sh.find(START); b = sh.find(END, a)
block = sh[a:b + len(END)] if a >= 0 and b > a else ""
check("shell: the anchor + watcher block is there", bool(block))
check("ASCII only (www rule)", all(ord(c) < 128 for c in block))

JS = r'''
const vm = require('vm');
const BLOCK = %s;
function world(){
  const M = { top0: 64, frameH: 3000, innerH: 1080, y: 0, fits: 0, ovs: [] };
  const q = [], H = {}, obs = [];
  const html = { style: { p: {}, setProperty(k, v){ this.p[k] = v; } } };
  const sl = () => ({ top: parseInt(html.style.p['--rv-top'], 10), h: parseInt(html.style.p['--rv-h'], 10) });
  function dialog(h){
    const ov = { a: {}, display: 'flex', style: { p: {}, setProperty(k, v){ this.p[k] = v; }, removeProperty(k){ delete this.p[k]; } },
      hasAttribute(k){ return k in this.a; }, setAttribute(k, v){ this.a[k] = v; }, removeAttribute(k){ delete this.a[k]; } };
    const box = { h: h, get offsetHeight(){ return this.h; },
      getBoundingClientRect(){ const s = sl(), t = ('data-rv-tall' in ov.a) ? parseInt(ov.style.p['--rv-pin'], 10) + 16 : s.top + (s.h - this.h) / 2; return { top: t, bottom: t + this.h }; } };
    ov.children = [box]; ov.box = box; M.ovs.push(ov); return ov;
  }
  const win = { getComputedStyle(e){ return e.box ? { display: e.display } : { display: 'block', position: 'static' }; } };
  const doc = { documentElement: html, body: {}, head: { appendChild(){} }, defaultView: win, getElementById(){ return null; }, createElement(){ return {}; },
    querySelector(){ return {}; }, querySelectorAll(){ return M.ovs.slice(); } };
  const f = { contentDocument: doc, handlers: {}, addEventListener(t, fn){ this.handlers[t] = fn; },
    getBoundingClientRect(){ return { top: M.top0 - M.y, height: M.frameH }; } };
  const ctx = { $id: id => id === 'page_frame' ? f : null, RV_CSS: '', RV_CSS_NATIVE: '' };
  ctx.window = ctx;
  ctx.addEventListener = (t, fn) => { (H[t] = H[t] || []).push(fn); };
  ctx.requestAnimationFrame = fn => { q.push(fn); return q.length; };
  ctx.setTimeout = () => 0;
  ctx.MutationObserver = function(cb){ this.cb = cb; obs.push(this); this.observe = () => {}; this.disconnect = () => {}; };
  ctx.ResizeObserver = function(cb){ this.cb = cb; this.observe = () => {}; this.disconnect = () => {}; };
  Object.defineProperty(ctx, 'innerHeight', { get(){ return M.innerH; } });
  ctx.reaperFrameFit = () => { M.fits++; };
  vm.createContext(ctx); vm.runInContext(BLOCK, ctx);
  const flush = () => { while (q.length) q.shift()(); };
  const fire = t => { (H[t] || []).forEach(fn => fn()); flush(); };
  f.handlers.load(); flush();
  const change = () => { obs[0].cb(); flush(); };                     /* the page changed something (a dialog opened, its content changed) */
  const scroll = y => { M.y = y; fire('scroll'); };
  const st = ov => ({ tall: 'data-rv-tall' in ov.a, pin: ov.style.p['--rv-pin'] || null, fits: M.fits, top: sl().top, h: sl().h });
  return { M, dialog, change, scroll, fire, st };
}
const R = {};
{ /* a dialog that fits: left alone, also after scrolling */
  const w = world(); w.scroll(400); const d = w.dialog(600); w.change(); R.fit = [w.st(d)]; w.scroll(900); R.fit.push(w.st(d)); }
{ /* a taller one: pinned where the user is; scrolling does not move or release it; shrinking releases it; removal re-fits */
  const w = world(); w.scroll(400); const d = w.dialog(1300); w.change(); R.tall = [w.st(d)];
  w.scroll(700); R.tall.push(w.st(d)); w.scroll(0); R.tall.push(w.st(d));
  w.scroll(700); d.box.h = 1500; w.change(); R.tall.push(w.st(d));
  d.box.h = 500; w.change(); R.tall.push(w.st(d));
  d.box.h = 1300; w.change(); R.tall.push(w.st(d));
  w.M.ovs.length = 0; w.change(); R.tall.push({ fits: w.M.fits }); w.change(); R.tall.push({ fits: w.M.fits }); }
{ /* the slice is shorter at the very top of the page: a scroll there pins a dialog that no longer fits, and it stays pinned */
  const w = world(); w.M.top0 = 120; w.scroll(400); const d = w.dialog(950); w.change(); R.edge = [w.st(d)];
  w.scroll(0); R.edge.push(w.st(d)); w.scroll(400); R.edge.push(w.st(d)); }
{ /* window resize: a shorter window pins, a taller one releases */
  const w = world(); w.scroll(300); const d = w.dialog(800); w.change(); R.resize = [w.st(d)];
  w.M.innerH = 700; w.fire('resize'); R.resize.push(w.st(d)); w.M.innerH = 1440; w.fire('resize'); R.resize.push(w.st(d)); }
{ /* pinned, scrolled far past it, then the dialog changes: pinned again where the user is */
  const w = world(); const d = w.dialog(1300); w.change(); R.lost = [w.st(d)]; w.scroll(2000); R.lost.push(w.st(d)); d.box.h = 1320; w.change(); R.lost.push(w.st(d)); }
{ /* a backdrop that is not shown, or holds no single box, is never pinned */
  const w = world(); const d = w.dialog(1300); d.display = 'none'; w.change(); const e = w.dialog(1300); e.children = [e.box, e.box]; w.change(); R.skip = [w.st(d), w.st(e)]; }
console.log(JSON.stringify(R));
'''
node = shutil.which("node")
if block and not node:
    check("node for the behaviour checks", False, "no node on PATH")
elif block:
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "h.js"); open(p, "w").write(JS % json.dumps(block))
        r = subprocess.run([node, p], capture_output=True, text=True, timeout=60)
        try: R = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception: R = None
        check("the watcher runs under the layout model", R is not None, (r.returncode, r.stderr[-400:]))
        if R:
            F = R["fit"]
            check("a dialog that fits is left alone (not pinned, frame not re-fitted), also after a scroll",
                  not F[0]["tall"] and not F[1]["tall"] and F[1]["fits"] == 0 and F[0]["h"] == 1016, F)
            T = R["tall"]
            check("a taller dialog is pinned at the slice top of that moment and the frame is re-fitted",
                  T[0]["tall"] and T[0]["pin"] == "400px" and T[0]["fits"] == 1, T[0])
            check("scrolling never moves or releases a pinned dialog, nor re-fits the frame",
                  all(x["tall"] and x["pin"] == "400px" and x["fits"] == 1 for x in T[1:3]), T[1:3])
            check("a pinned dialog that changes height stays where it is and the frame is re-fitted",
                  T[3]["tall"] and T[3]["pin"] == "400px" and T[3]["fits"] == 2, T[3])
            check("a dialog that fits again is released; one that grows again is pinned where the user is now",
                  not T[4]["tall"] and T[4]["pin"] is None and T[4]["fits"] == 3 and T[5]["tall"] and T[5]["pin"] == "700px" and T[5]["fits"] == 4, T[4:6])
            check("a pinned dialog that is removed re-fits the frame, once", T[6]["fits"] == 5 and T[7]["fits"] == 5, T[6:])
            E = R["edge"]
            check("a scroll that shortens the slice pins a dialog that no longer fits; it stays pinned",
                  not E[0]["tall"] and E[1]["tall"] and E[1]["pin"] == "0px" and E[1]["h"] == 960 and E[2]["tall"] and E[2]["pin"] == "0px", E)
            Z = R["resize"]
            check("window resize: a shorter window pins, a taller one releases",
                  not Z[0]["tall"] and Z[1]["tall"] and Z[1]["pin"] == "300px" and not Z[2]["tall"], Z)
            L = R["lost"]
            check("a pinned box left wholly out of view is pinned again where the user is, on the next change only",
                  L[1]["pin"] == "0px" and L[2]["tall"] and L[2]["pin"] == "2000px", L)
            K = R["skip"]
            check("a hidden backdrop, or one without a single box, is never pinned", not K[0]["tall"] and not K[1]["tall"], K)

# ---- the pages: no viewport-unit cap, no scroll area of their own inside a dialog
def style_of(page):
    m = re.search(r"<style>(.*?)</style>", page, re.S); return m.group(1) if m else ""
def rule(css, sel):
    m = re.search(r"(?m)^" + re.escape(sel) + r"\{([^}]*)\}", css); return m.group(1) if m else None
dev = rd("www", "Reaper_Devices.asp"); dcss = style_of(dev)
check("Devices: no viewport-height unit anywhere in the page sheet", re.search(r"\d(?:vh|dvh|svh|lvh)\b", dcss) is None)
check("Devices: the type list is not a scroll area", rule(dcss, ".tscroll") == "margin-bottom:10px" and "keepScroll" not in dev)
check("Devices: opened on its own the backdrop scrolls and a tall box keeps its top (auto margins)",
      (rule(dcss, ".ovl") or "").endswith("overflow-y:auto") and (rule(dcss, ".modal") or "").endswith("margin:auto"))
check("Devices: the picture dialog uses the width there is; the short type groups share a row",
      rule(dcss, ".modal.wide") == "max-width:1320px;width:94%" and "minmax(136px,1fr)" in (rule(dcss, ".tgrid") or "")
      and rule(dcss, ".tcats") == "display:flex;flex-wrap:wrap;column-gap:20px" and "calc(var(--n,99) * 142px - 6px)" in (rule(dcss, ".tsec") or "")
      and "'<div class=\"tsec\" style=\"--n:' + cat[1].length + '\">" in dev)
for name in ("Reaper_Network.asp", "Reaper_AiMesh.asp"):
    if not os.path.isfile(os.path.join(SRC, "www", name)): continue
    css = style_of(rd("www", name)); bd, bx = rule(css, ".adlg") or "", rule(css, ".abox2") or ""
    check("%s: the dialog box has no height cap and no scroll area" % name, bx != "" and "max-height" not in bx and "overflow-y" not in bx and "vh" not in bx, bx)
    check("%s: opened on its own the backdrop scrolls and a tall box keeps its top" % name, "overflow-y:auto" in bd and "margin:auto" in bx, (bd, bx))
    check("%s: the backdrop keeps the class the shell anchors" % name, "el('div', 'ovl adlg')" in rd("www", name))
net = style_of(rd("www", "Reaper_Network.asp")) if os.path.isfile(os.path.join(SRC, "www", "Reaper_Network.asp")) else ""
if net:
    check("Network: the one data list that keeps a cap has a fixed one", rule(net, ".maclist") == "max-height:420px;overflow-y:auto")
    check("Network: no viewport-height unit anywhere in the page sheet", re.search(r"\d(?:vh|dvh|svh|lvh)\b", net) is None)

print("%d checks failed" % len(fails) if fails else "all checks passed")
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
