#!/usr/bin/env python3
"""The shell's page frame shrinks when the framed page does (owner 2026-11-07: Wallguard's empty scroll below the last card).

WHY. reaper_shell.asp sizes #page_frame to the framed page's scrollHeight. A document's scrollHeight is never less than
its own viewport (the frame), so a frame measured only at its grown height could only ever grow: open a long panel
(Wallguard's live view, the Advanced-rules report, the Unbreak table), close it, and the frame kept the tall height -
measured in the mock: +3000 px of content, removed, left the frame at 6364 px over 3330 px of content.

WHAT IT DOES.
- Runs the shell's frame-fit block under node (vm) against a small layout model (scrollHeight = max(content,
  document minimum, frame), a fallback frame height for an empty style) and checks:
  - load, grow, shrink back: the frame follows the content both ways;
  - at rest nothing is cleared (each clear is a resize event inside the framed page);
  - a short page whose document is taller than its content is cleared once, not on every fit, and still shrinks
    back after a grow; a page shorter than the fallback stays on the fallback;
  - the window scroll position is put back if the clear moved it.
- Pins the wiring: frameContentBottom() feeds the gate, the load handler resets lastEst, the width logic is unchanged.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www/reaper_shell.asp")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
sh = open(os.path.join(SRC, "www/reaper_shell.asp"), encoding="utf-8").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

START, END = "(function(){\n  var f=$id('page_frame');\n", "  window.addEventListener('resize', fit);\n})();\n"
a = sh.find(START); b = sh.find(END, a)
block = sh[a:b + len(END)] if a >= 0 and b > a else ""
check("reaper_shell.asp holds the frame-fit block", bool(block))
check("ASCII only (www rule)", all(ord(c) < 128 for c in block))
check("the gate reads frameContentBottom() and remembers lastEst",
      "var est=frameContentBottom(d), h;" in block and "if(f.style.height && est<f.offsetHeight-4 && est!==lastEst){" in block)
check("the load handler resets lastEst with the size", "f.style.height=''; f.style.width='';   /* reset before measuring the new page */\n    lastEst=-1;" in block)
check("the clear puts the window scroll back", "if(window.pageYOffset!==y) window.scrollTo(window.pageXOffset, y);" in block)
check("width logic unchanged (measured from the cleared state)", "if(f.style.width) f.style.width='';" in block and "if(cw>0 && w>cw+4) f.style.width=w+'px';" in block)

JS = r'''
const vm = require('vm');
const BLOCK = %s;
function run(steps){
  const M = { content: 0, docMin: 0, fallback: 836, padB: 16, marB: 18, clears: 0, y: 0, clampTo: null };
  const style = { _h: '', width: '', setProperty(){},
    get height(){ return this._h; },
    set height(v){ if (v === '' && this._h !== '') { M.clears++; if (M.clampTo !== null) M.y = Math.min(M.y, M.clampTo); } this._h = v; } };
  const html = {}, child = {};
  const est = () => M.content + M.marB + M.padB;
  const f = { style, parentElement: { clientWidth: 1000 }, handlers: {},
    get offsetHeight(){ return style._h ? parseInt(style._h, 10) : M.fallback; },
    addEventListener(t, fn){ this.handlers[t] = fn; } };
  const body = { children: [child], get scrollHeight(){ return Math.max(est(), M.docMin, f.offsetHeight); }, scrollWidth: 900 };
  child.getBoundingClientRect = () => ({ bottom: M.content, height: M.content, width: 900 });
  Object.defineProperty(html, 'scrollHeight', { get(){ return body.scrollHeight; } }); html.scrollWidth = 900;
  const win = { pageXOffset: 0,
    getComputedStyle(el){ return el === body ? { paddingBottom: M.padB + 'px', borderBottomWidth: '0px', marginBottom: '0px' }
      : el === html ? { paddingBottom: '0px', borderBottomWidth: '0px' } : { display: 'block', position: 'static', marginBottom: M.marB + 'px' }; } };
  Object.defineProperty(win, 'pageYOffset', { get(){ return 0; } });
  const doc = { documentElement: html, body, defaultView: win, getElementById(){ return null; } };
  f.contentDocument = doc;
  const ctx = { $id: id => id === 'page_frame' ? f : null, handlers: {} };
  ctx.window = ctx;
  ctx.addEventListener = (t, fn) => { ctx.handlers[t] = fn; };
  Object.defineProperty(ctx, 'pageYOffset', { get(){ return M.y; } });
  ctx.pageXOffset = 0;
  ctx.scrollTo = (x, y) => { M.y = y; };
  ctx.shellChromeLock = () => {};
  vm.createContext(ctx); vm.runInContext(BLOCK, ctx);
  const out = [];
  for (const s of steps) {
    if (s.content !== undefined) M.content = s.content;
    if (s.docMin !== undefined) M.docMin = s.docMin;
    if (s.y !== undefined) M.y = s.y;
    if (s.clampTo !== undefined) M.clampTo = s.clampTo;
    if (s.load) f.handlers.load(); else ctx.handlers.resize();
    out.push({ h: f.offsetHeight, style: style._h, clears: M.clears, y: M.y });
  }
  return out;
}
const R = {};
/* full page: load, idle, grow, shrink, idle */
R.full = run([{content: 3330, load: 1}, {}, {}, {content: 6330}, {content: 3330}, {}, {}]);
/* short page with a document taller than its content (min-height), then a grow and a shrink */
R.shortdoc = run([{content: 503, docMin: 975, load: 1}, {}, {}, {}, {content: 3000}, {content: 503}, {}, {}]);
/* a page shorter than the fallback: stays on the fallback, never cleared */
R.tiny = run([{content: 200, load: 1}, {}, {}, {content: 2000}, {content: 200}, {}]);
/* scrolled down; the clear clamps the window scroll to 500, the fit puts it back */
R.scroll = run([{content: 3330, load: 1}, {content: 6330}, {y: 2000, clampTo: 500, content: 3330}]);
console.log(JSON.stringify(R));
'''

node = shutil.which("node")
if not block:
    pass
elif not node:
    check("node for the behaviour checks", False, "no node on PATH")
else:
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "h.js"); open(p, "w").write(JS % json.dumps(block))
        r = subprocess.run([node, p], capture_output=True, text=True, timeout=60)
        try:
            R = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            R = None
        check("the frame-fit block runs under the layout model", R is not None, (r.returncode, r.stderr[-400:]))
        if R:
            F = R["full"]
            check("full page: load sizes the frame to the content (3364)", F[0]["h"] == 3364, F[0])
            check("full page: grows with the content (6364)", F[3]["h"] == 6364, F[3])
            check("full page: shrinks back when the content does (3364)", F[4]["h"] == 3364, F[4])
            check("full page: nothing cleared at rest; one clear for the shrink",
                  [x["clears"] for x in F] == [0, 0, 0, 0, 1, 1, 1], [x["clears"] for x in F])
            S = R["shortdoc"]
            check("short page: the frame is the document's height (975), cleared once, not on every fit",
                  all(x["h"] == 975 for x in S[:4]) and S[3]["clears"] == 1, S[:4])
            check("short page: grows (3034) and shrinks back (975) after a grow",
                  S[4]["h"] == 3034 and S[5]["h"] == 975 and S[7]["clears"] == S[5]["clears"], S[4:])
            T = R["tiny"]
            check("page shorter than the fallback: stays on the fallback style, never cleared at rest",
                  T[0]["style"] == "" and T[2]["clears"] == 0 and T[3]["h"] == 2034 and T[4]["style"] == "" and T[5]["clears"] == T[4]["clears"], T)
            C = R["scroll"]
            check("scroll position put back after the clear (2000)", C[2]["y"] == 2000 and C[2]["h"] == 3364, C)

print("%d checks failed" % len(fails) if fails else "all checks passed")
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
