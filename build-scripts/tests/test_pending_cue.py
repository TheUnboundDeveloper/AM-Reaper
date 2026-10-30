#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unsaved-changes cue, DNS Director's device picker, Dreadwatch's own wording (2026-10-30).

WHY THIS EXISTS. On Reaper QoS a rule's x edited only the page and nothing said Apply was still owed,
so the owner's first delete was never written (metal, 2026-10-22). Five Reaper pages keep list edits on
the page until their own Apply / Save without the kit's chgpill: QoS, Policy Routing, WAN Ports,
Wallguard and Dreadwatch. www/reaper/reaper_pending.js gives them the same "Unsaved changes: N" pill and
Discard, comparing a snapshot of what the Apply / Save writes with the one taken when the page loaded.
Same day: DNS Director's add row gained a picker of connected devices (the native page had dropped
stock's client list), and Dreadwatch's apply overlay and how-it-works card stopped saying Warden.

WHAT IT DOES. Runs reaper_pending.js under node against a small DOM stub (count, re-check after an
edit, Discard state, re-arm, hold, a snapshot that throws), then checks each page's wiring, the
picker's rules and the two new keys in all 25 packs (lockstep, Dreadwatch in every value).
Needs the router source (argv[1] or REAPER_ROUTER_SRC). Exit 0 pass, 1 fail, 77 skipped."""
import glob, json, os, re, shutil, subprocess, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WWW = os.path.join(SRC, "www") if SRC else ""
HELPER = os.path.join(WWW, "reaper", "reaper_pending.js")
if not SRC or not os.path.isfile(os.path.join(WWW, "Reaper_QoS.asp")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
def rd(rel):
    p = os.path.join(WWW, rel)
    return open(p, encoding="utf-8", errors="surrogateescape").read() if os.path.isfile(p) else ""

# ---- the helper, run under node against a DOM stub
helper = rd("reaper/reaper_pending.js")
check("www/reaper/reaper_pending.js exists and is ASCII", helper != "" and all(ord(c) < 128 for c in helper))
STUB = r"""
var listeners = {}, byId = {};
function El(tag){ this.tagName = tag; this.children = []; this.parentNode = null; this.textContent = ''; this.disabled = false;
  this.id = ''; this.className = ''; var self = this;
  this.classList = { toggle: function(c, on){ var s = self.className.split(' ').filter(Boolean), i = s.indexOf(c);
      if (on === undefined) on = i < 0; if (on && i < 0) s.push(c); if (!on && i >= 0) s.splice(i, 1); self.className = s.join(' '); },
    remove: function(c){ this.toggle(c, false); }, contains: function(c){ return self.className.split(' ').indexOf(c) >= 0; } };
  this.attrs = {}; }
El.prototype.appendChild = function(c){ c.parentNode = this; this.children.push(c); if (c.id) byId[c.id] = c; return c; };
El.prototype.insertBefore = function(c, ref){ c.parentNode = this; this.children.splice(this.children.indexOf(ref), 0, c); return c; };
El.prototype.setAttribute = function(k, v){ this.attrs[k] = v; };
El.prototype.addEventListener = function(ev, fn){ (this.l = this.l || {})[ev] = fn; };
var head = new El('head');
global.document = { head: head, documentElement: head,
  createElement: function(t){ return new El(t); },
  getElementById: function(id){ var f = null; (function walk(n){ if (n.id === id) f = n; n.children.forEach(walk); })(head); (function walk(n){ if (!f && n.id === id) f = n; n.children.forEach(walk); })(bar); return f; },
  addEventListener: function(ev, fn){ (listeners[ev] = listeners[ev] || []).push(fn); } };
global.window = global; global.location = { reloads: 0, reload: function(){ this.reloads++; } };
var bar = new El('div'), apply = new El('button'); bar.appendChild(apply);
""" + helper + r"""
var S = {a: '1', list: '<x<y'}, out = [], boom = false;
function fire(){ (listeners.click || []).forEach(function(f){ f(); }); }
function pillN(){ var p = bar.children[0]; return p.classList.contains('show') ? Number(p.children[1].children[0].textContent) : 0; }
ReaperPending.watch({at: apply, label: 'Unsaved changes', discard: 'Discard', snap: function(){ if (boom) throw new Error('x'); return {a: S.a, list: S.list}; }});
out.push(['placed', bar.children.length === 3 && bar.children[0].className.indexOf('rpend') === 0 && bar.children[1].tagName === 'button' && bar.children[2] === apply]);
ReaperPending.arm();
out.push(['nothing at load', pillN() === 0 && bar.children[1].disabled === true]);
S.list = '<x'; fire();
setTimeout(function(){
  out.push(['a list edit counts one', pillN() === 1 && bar.children[1].disabled === false]);
  out.push(['the label', bar.children[0].children[1].textContent.indexOf('Unsaved changes: ') === 0]);
  S.a = '0'; fire();
  setTimeout(function(){
    out.push(['two keys count two', pillN() === 2]);
    S.a = '1'; S.list = '<x<y'; fire();
    setTimeout(function(){
      out.push(['undoing both clears it', pillN() === 0 && bar.children[1].disabled === true]);
      S.a = '9'; fire();
      setTimeout(function(){
        ReaperPending.arm(); out.push(['re-arm makes the current state the baseline', pillN() === 0]);
        S.a = '8'; ReaperPending.hold(); fire();
        setTimeout(function(){
          out.push(['hold keeps it hidden', pillN() === 0]);
          ReaperPending.arm(); boom = true; S.a = '7'; fire();
          setTimeout(function(){
            out.push(['a snapshot that throws changes nothing (no error, no pill)', pillN() === 0]);
            bar.children[1].l.click(); out.push(['Discard reloads the page', location.reloads === 1]);
            ReaperPending.watch({at: apply, snap: function(){ return {}; }});
            out.push(['a second watch() is ignored', bar.children.length === 3]);
            console.log(JSON.stringify(out));
          }, 5);
        }, 5);
      }, 5);
    }, 5);
  }, 5);
}, 5);
"""
node = shutil.which("node")
if node and helper:
    r = subprocess.run([node, "-e", STUB], capture_output=True, text=True)
    try:
        for name, good in json.loads(r.stdout.strip().splitlines()[-1]):
            check("helper: " + name, good)
    except Exception:
        check("helper runs under node", False, r.stderr[-400:])
else:
    print("note: no node - the helper's behaviour is not run here (the page checks still are)")

# ---- the five pages
LBL = "label: `<#RADM_77#>`, discard: `<#Discard#>`"
PAGES = {
    "Reaper_QoS.asp": ("document.getElementById('qos_apply')", "function qosSnap(){"),
    "Reaper_VPNRouting.asp": ("document.getElementById('applybtn')", "rules: serialize()"),
    "Reaper_WANPorts.asp": ("$id('apply')", "!/Opts$/.test(k)"),
    "Reaper_Wallguard.asp": ("document.querySelector('[data-act=\"save\"]')", "function shSnap(){"),
    "Reaper_Dreadwatch.asp": ("document.querySelector('button[onclick=\"dwSave(false)\"]')", "function dwSnap(){"),
}
for page, (anchor, snap) in PAGES.items():
    t = rd(page)
    tag = t.find('<script src="/reaper/reaper_pending.js"></script>')
    first_inline = re.search(r"<script>\s", t)
    check("%s loads reaper_pending.js before its own script" % page, tag >= 0 and first_inline is not None and tag < first_inline.start())
    check("%s puts the pill before its Apply / Save and labels it from the packs" % page,
          ("ReaperPending.watch({at: " + anchor) in t and LBL in t and snap in t and "ReaperPending.arm();" in t)
qos = rd("Reaper_QoS.asp")
check("QoS: the Apply button has its id and the snapshot covers both lists",
      'id="qos_apply" onclick="applyQoS()"' in qos and "limits: JSON.stringify(BWL), rules: serializeRules()" in qos)
pbr = rd("Reaper_VPNRouting.asp")
check("Policy Routing: re-baselined when the router's list loads and when an apply is written",
      "parseRules(); render(); armUI(); ReaperPending.arm(); }" in pbr and "NV.enable=masterOn?'1':'0';\n    ReaperPending.arm();" in pbr)
wg = rd("Reaper_Wallguard.asp")
check("Wallguard: Save sends shPayload() (one builder for the save and the snapshot)",
      "function shPayload(){" in wg and "var p = shPayload();" in wg and "shPost(p, function(j){" in wg
      and "shParseConfig(j); shPaint(); ReaperPending.arm();" in wg)
check("Wallguard: the snapshot reduces a typed key to 'set'", "(cfg.keyUpd[s] === '-' ? ' -' : ' set')" in wg)

# ---- DNS Director's picker
dns = rd("Reaper_DNS.asp")
check("DNS Director: a device picker before the MAC box",
      '<select id="s_ddpick"><option value=""><#Select_menu_default#></option></select>' in dns
      and dns.find('id="s_ddpick"') < dns.find('id="a_ddmac"'))
check("DNS Director: offline devices and devices with a rule are left out; names go in as text",
      "String(c.isOnline) === '0'" in dns and "if (have[d.mac]) return;" in dns and "o.textContent = d.label;" in dns)
check("DNS Director: picking fills the box, typing still works, the list redraws with the rules",
      "q('a_ddmac').value = this.value;" in dns and "on('a_ddmac', 'input'" in dns and "  ddPickDraw();\n}" in dns)
check("DNS Director: the kit page keeps its own pill (no reaper_pending.js)", "reaper_pending.js" not in dns)

# ---- Dreadwatch names itself
dw = rd("Reaper_Dreadwatch.asp")
check("Dreadwatch: the overlay and the how-it-works card no longer use Warden's strings",
      "<#RWDN_30#>" not in dw and "<#RWDN_38#>" not in dw and "<p><#RDWT_66#></p>" in dw and "<h2><#RDWT_67#></h2>" in dw)
packs = sorted(p for p in glob.glob(os.path.join(WWW, "*.dict")) if not p.endswith("temp.dict"))
bad = []
for p in packs:
    t = open(p, encoding="utf-8", errors="replace").read()
    for k in ("RDWT_66", "RDWT_67"):
        m = re.search(r"^%s=(.*)$" % k, t, re.M)
        if not m or "Dreadwatch" not in m.group(1) or "Warden" in m.group(1): bad.append(os.path.basename(p) + ":" + k)
check("RDWT_66 / RDWT_67 in all 25 packs, each naming Dreadwatch", len(packs) == 25 and not bad, bad)
counts = set(open(p, "rb").read().count(b"\n") for p in packs)
check("the 25 packs stay in lockstep", len(counts) == 1, counts)
en = open(os.path.join(WWW, "EN.dict"), encoding="utf-8").read()
check("Warden's own strings are unchanged (the Warden page still uses them)",
      re.search(r"^RWDN_30=Applying Warden rules", en, re.M) is not None and re.search(r"^RWDN_38=How Warden works$", en, re.M) is not None)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
