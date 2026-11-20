#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Buttons that start background work show it (2026-11-13; owner request 2026-11-07).

WHY THIS EXISTS. Owner: "buttons that don't visually show when they have been clicked" (e.g. Encrypted DNS > Update
lists - only a timestamp changing later told it had worked). Shape approved 2026-11-13: the button greys out and says
it is working until the status refresh, then shows the result. One shared helper, ReaperBusy (www/reaper_util.js),
one shared word trio RBSY_1-3 in every pack.

WHAT IT DOES. Runs the real REAPER-BUSY block under node against a small DOM stub on a fake clock: start() greys the
button out (disabled, busy class, aria-busy) and writes "Working..." beside it; a second press while busy does
nothing; finish(true) restores the button and shows "Done hh:mm:ss", finish(false, msg) the error, finish(null)
just restores; the note fades; a page that never calls finish gets its button back after maxMs; a button that was
already disabled stays disabled; words() sets the page's own words. Then checks the words are in every pack and
every page wired to the helper loads reaper_util.js and sets the words (WIRED below).
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC). Without node only the pins run."""
import glob, json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WWW = os.path.join(SRC, "www") if SRC else ""
UTIL = os.path.join(WWW, "reaper_util.js") if SRC else ""
if not SRC or not os.path.isfile(UTIL):
    print("SKIP: no router tree with www/reaper_util.js (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
util = open(UTIL, encoding="latin-1").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

# page -> button handlers wired to the helper (each pin is a substring of the page). Survey 2026-11-13: Tier A (no
# sign at all) and Tier B (nothing until the reply) buttons; refresh-only buttons and Firmware's override left as is.
WIRED = {
 "Reaper_EncryptedDNS.asp": ['<script src="/reaper_util.js"></script>\n<script src="/reaper/rp.js"></script>',
                             "var x = new XMLHttpRequest(), fin = ReaperBusy.startLast();", "setTimeout(function(){ encGet(); fin(ok); }, 5000);"],
 "Reaper_Wallguard.asp": ["function shAct(a){ var fin = ReaperBusy.startLast();", "function shResume(){ var fin = ReaperBusy.startLast();",
                          "function shAllow(name, dur){ var fin = ReaperBusy.startLast();", "shConfig(function(){ shStatus(function(){ fin(true); }); });"],
 "Reaper_Dreadwatch.asp": ["dwGet('action=dns_reset', function(){ dwStats(); fin(true); });"],
 "Reaper_Devices.asp": ["function unpin(i){\n  var fin = ReaperBusy.startLast();", "function unpin6(i){\n  var fin = ReaperBusy.startLast();",
                        "    fin(null); pinClose();\n", "if(++done === macs.length){ fin(true); loadAll(); }"],
 "Reaper_GK.asp": ["  var fin = ReaperBusy.startLast();\t/* a click only (not the settings selects) */",
                   "GK.busy = false; gkRefresh(); fin(true);"],
 "Reaper_Firewall.asp": ["function rvpost(q,cb,btn){", "},$('rv_ack'));", "},$('rv_reset'));", "var bf=ReaperBusy.startLast();\n    fwcgi('action=export'"],
 "Reaper_VPNRouting.asp": ["var bf=ReaperBusy.startLast(); pbrcgi('action=confirm'", "var bf=ReaperBusy.startLast(); pbrcgi('action=rollback'"],
 "Reaper_Wireless.asp": ["fetchStatus();bf(null);},600);", "ReaperBusy.startLast({maxMs:60000});\n  submitApply(unit,\"0\",\"0\");"],
 "Reaper_Survey.asp": ["var x=new XMLHttpRequest(),bf=ReaperBusy.startLast();\n  x.open(\"GET\",\"/reaper_wifi.cgi?action=svystop"],
 "Reaper_WOL.asp": ["  var bf = ReaperBusy.startLast();\n  call('action=start&tool=wake"],
 "Reaper_Advisor.asp": ["function disarm(){ var bf=ReaperBusy.startLast(); post('disarm')"],
 "Reaper_Analysis.asp": ["call('action=cancel', function(){ bf(null); poll(); })"],
 "Reaper_Netstat.asp": ["call('action=start&tool=netstat&opts=' + opts, function(d){\n    bf(null);"],
 "Reaper_Analytics.asp": ['<script src="/reaper_util.js"></script>', "var bf = ReaperBusy.start(self);"],
 "Reaper_VPNServer.asp": ["hook=ovpn_generate_client_key()', function(t){\n    bf(null);"],
 "Reaper_Conn.asp": ["bf=ReaperBusy.start(nb);"],
}
# pages whose actions run after a password dialog / confirm, so they write the shared word into their own status line
TOKEN_ONLY = {
 "Reaper_Backup.asp": ["  setStat(statId, `<#RBSY_1#>`, '');", "    setStat('st_cfg', `<#RBSY_1#>`, '');\n    var g = new XMLHttpRequest();",
                       "function cfgImportJson(j){\n  setStat('st_cfg', `<#RBSY_1#>`, '');"],
 "Reaper_USB.asp": ["dkSetStat(port, esc(`<#RBSY_1#>`), '');"],
}

blk = re.search(r"/\* REAPER-BUSY-BEGIN.*?\*/(.*?)/\* REAPER-BUSY-END \*/", util, re.S)
check("exactly one REAPER-BUSY block in reaper_util.js", util.count("/* REAPER-BUSY-BEGIN") == 1 and bool(blk))
check("reaper_util.js stays plain ASCII", all(ord(c) < 128 for c in util))
NODE = shutil.which("node") or shutil.which("nodejs")
if blk and NODE:
    js = r"""
var T = 0, timers = [];
function setTimeout(f, ms){ timers.push({at: T + ms, f: f, id: timers.length + 1}); return timers.length; }
function clearTimeout(id){ timers.forEach(function(t){ if(t.id === id) t.dead = true; }); }
function advance(ms){ T += ms; timers.slice().forEach(function(t){ if(!t.dead && t.at <= T){ t.dead = true; t.f(); } }); }
function El(tag){ this.tagName = tag; this.nodeType = 1; this.className = ''; this.textContent = ''; this.attrs = {}; this.children = []; this.parentNode = null; this.disabled = false; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = v; };
El.prototype.removeAttribute = function(k){ delete this.attrs[k]; };
El.prototype.appendChild = function(c){ c.parentNode = this; this.children.push(c); return c; };
El.prototype.insertBefore = function(c, ref){ c.parentNode = this; var i = ref ? this.children.indexOf(ref) : -1; if(i < 0) this.children.push(c); else this.children.splice(i, 0, c); return c; };
El.prototype.removeChild = function(c){ var i = this.children.indexOf(c); if(i >= 0) this.children.splice(i, 1); c.parentNode = null; };
Object.defineProperty(El.prototype, 'nextSibling', { get: function(){ if(!this.parentNode) return null; var s = this.parentNode.children; return s[s.indexOf(this) + 1] || null; } });
var head = new El('head'), document = { head: head, createElement: function(t){ return new El(t); } };
var window = {};
var Date = function(){ return { getHours: function(){ return 9; }, getMinutes: function(){ return 5; }, getSeconds: function(){ return 7; } }; };
""" + blk.group(1) + r"""
var R = window.ReaperBusy, row = new El('div'), b = row.appendChild(new El('button')), out = {};
b.className = 'btn';
var fin = R.start(b);
var note = b.nextSibling;
out.busy = { disabled: b.disabled, cls: b.className, aria: b.attrs['aria-busy'], note: note && note.textContent, styled: head.children.length };
out.second = (R.start(b), row.children.length);
fin(true);
out.done = { disabled: b.disabled, cls: b.className, aria: b.attrs['aria-busy'] || '', note: note.textContent, ncls: note.className };
advance(8000); out.faded = row.children.length;
fin = R.start(b); fin(false, 'list host unreachable'); out.err = { note: b.nextSibling.textContent, ncls: b.nextSibling.className };
advance(9000);
fin = R.start(b); fin(null); out.plain = row.children.length;
fin = R.start(b); advance(30000); out.guard = { disabled: b.disabled, cls: b.className, kids: row.children.length };
var d = row.appendChild(new El('button')); d.disabled = true; fin = R.start(d); fin(true); out.keptDisabled = d.disabled;
R.words('Arbeite...', 'Fertig', 'Fehler'); var e = row.appendChild(new El('button')); fin = R.start(e); out.w1 = e.nextSibling.textContent; fin(false); out.w2 = e.nextSibling.textContent;
fin = R.start(e); fin(true); out.w3 = e.nextSibling.textContent;
out.nullbtn = typeof R.start(null);
console.log(JSON.stringify(out));
"""
    tmp = tempfile.mkdtemp()
    try:
        h = os.path.join(tmp, "b.js"); open(h, "w", encoding="ascii").write(js)
        r = subprocess.run([NODE, h], capture_output=True, text=True, timeout=60)
        o = {}
        try:
            o = json.loads(r.stdout)
        except Exception:
            pass
        check("helper ran under node", bool(o), (r.stdout + r.stderr)[-500:])
        if o:
            check("pressed: greyed out (disabled, busy class, aria-busy) and 'Working...' beside it, style added once",
                  o["busy"] == {"disabled": True, "cls": "btn rbusy", "aria": "true", "note": "Working...", "styled": 1}, o["busy"])
            check("a second press while busy adds nothing", o["second"] == 2, o["second"])
            check("finished: button back as it was, 'Done hh:mm:ss' in green",
                  o["done"] == {"disabled": False, "cls": "btn", "aria": "", "note": "Done 09:05:07", "ncls": "rbusy-note ok"}, o["done"])
            check("the note fades after a few seconds", o["faded"] == 1, o["faded"])
            check("an error is shown as given, in amber", o["err"] == {"note": "list host unreachable", "ncls": "rbusy-note err"}, o["err"])
            check("finish(null) just restores, no note", o["plain"] == 1, o["plain"])
            check("never finished: the button comes back after maxMs (no dead button)",
                  o["guard"]["disabled"] is False and o["guard"]["cls"] == "btn" and o["guard"]["kids"] == 1, o["guard"])
            check("a button that was disabled before stays disabled", o["keptDisabled"] is True)
            check("the page's own words are used", (o["w1"], o["w2"], o["w3"]) == ("Arbeite...", "Fehler", "Fertig 09:05:07"), o)
            check("no button: a harmless no-op", o["nullbtn"] == "function")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
elif blk:
    print("SKIP (part): no node")

packs = [p for p in glob.glob(os.path.join(WWW, "*.dict")) if not p.endswith("temp.dict")]
miss = [os.path.basename(p) for p in packs if not all(re.search(r"^RBSY_%d=\S" % i, open(p, encoding="utf-8").read(), re.M) for i in (1, 2, 3))]
check("RBSY_1-3 in all %d packs" % len(packs), packs and not miss, miss)
for page, pins in sorted(WIRED.items()):
    t = open(os.path.join(WWW, page), encoding="latin-1").read()
    check("%s loads reaper_util.js and sets the shared words" % page,
          "reaper_util.js" in t and "ReaperBusy.words(`<#RBSY_1#>`, `<#RBSY_2#>`, `<#RBSY_3#>`)" in t)
    for p in pins:
        check("%s: %s" % (page, p[:70]), p in t, p)
for page, pins in sorted(TOKEN_ONLY.items()):
    t = open(os.path.join(WWW, page), encoding="latin-1").read()
    for p in pins:
        check("%s: %s" % (page, p[:70]), p in t, p)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
