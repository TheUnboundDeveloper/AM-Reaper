#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The shell header's Internet status tooltip, run for real under node (2026-10-11).

WHY THIS EXISTS. The amber LAN-names state and its tooltip (2026-10-10) lived on the dashboard only;
every other page is framed in reaper_shell.asp, whose header had the WAN pill but not the tooltip, so
the header read differently depending on the page. The shell now carries the dashboard's box, readings
and colours. test_landns_check.py pins the wiring and compares the shared functions verbatim; this
suite runs the shell's header code itself, because a static check cannot see a ReferenceError from a
declaration that sits below its first use inside the shell's IIFE, nor what the box says per state.

WHAT IT DOES. Takes the topbar IIFE out of reaper_shell.asp, resolves its SSI hooks and dictionary
tokens with scenario values (tokens become [NAME]), runs it under node against a stubbed document, then
hovers the pill and reads the box. Five states: failing LAN names (amber, the silent server named),
working (jade, no amber), WAN down (danger, "no address" line), AP mode (mode name in steel, no
tooltip, plain pill), IPv6-only (Connected, "(IPv6)"). Also: focus leaving for the framed page
closes the box; a click pins it. Exit 0 pass, 1 fail, 77 skipped (no node, or no router source tree -
argv[1] or REAPER_ROUTER_SRC)."""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
SHELL = os.path.join(SRC, "www", "reaper_shell.asp") if SRC else ""
if not SHELL or not os.path.isfile(SHELL):
    skip("no router source tree with www/reaper_shell.asp (argv[1] or REAPER_ROUTER_SRC)")
# node on PATH, or REAPER_NODE=<path to a node binary> (the build host's WSL has none; the Windows
# side and the CI runner do)
NODE = shutil.which("node") or shutil.which("nodejs") or os.environ.get("REAPER_NODE", "")
if not NODE or not os.path.isfile(NODE):
    skip("no node on this host (PATH or REAPER_NODE)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(SHELL, encoding="utf-8", errors="replace").read()
blocks = re.findall(r"<script[^>]*>([\s\S]*?)</script>", src)
last = blocks[-1] if blocks else ""
i = last.find("/* topbar status pills")
iife = last[i:] if i >= 0 else ""
check("the topbar IIFE is the last thing in the shell's final script block", bool(iife) and iife.rstrip().endswith("})();"))

PRELUDE = r"""
'use strict';
function El(id){ this.id=id; this.style={}; this.textContent=''; this.hidden=false; this.children=[]; this.handlers={};
  this.attrs={tabindex:'0',role:'button','aria-describedby':'ntip'}; var cls=new Set(['pill','tipa']); this.className='';
  this.classList={remove:function(c){cls.delete(c);},add:function(c){cls.add(c);},contains:function(c){return cls.has(c);}};
  this.offsetWidth=200; this.offsetHeight=80; }
El.prototype.addEventListener=function(t,f){ (this.handlers[t]=this.handlers[t]||[]).push(f); };
El.prototype.fire=function(t,e){ var self=this; e=e||{}; e.target=e.target||self; e.preventDefault=e.preventDefault||function(){}; e.stopPropagation=e.stopPropagation||function(){};
  (this.handlers[t]||[]).forEach(function(f){ f.call(self,e); }); };
El.prototype.click=function(){ this.fire('click',{}); };
El.prototype.removeAttribute=function(a){ delete this.attrs[a]; };
El.prototype.getBoundingClientRect=function(){ return {left:100,top:10,bottom:40,right:200}; };
El.prototype.appendChild=function(c){ this.children.push(c); return c; };
El.prototype.removeChild=function(c){ this.children=this.children.filter(function(x){return x!==c;}); };
El.prototype.contains=function(x){ return x===this; };
Object.defineProperty(El.prototype,'firstChild',{get:function(){ return this.children[0]||null; }});
var IDS=['p_wan','p_wan_dot','p_wan_pill','ntip','i_opmode','p_uptime','p_fw','p_fwbeta','p_clients','p_mesh'];
var DOM={}; IDS.forEach(function(k){ DOM[k]=new El(k); }); DOM.ntip.hidden=true;
var docHandlers={};
var document={ getElementById:function(id){ return DOM[id]||null; },
  createElement:function(tag){ var e=new El(''); e.tag=tag; return e; },
  createTextNode:function(t){ return {nodeValue:String(t)}; },
  addEventListener:function(t,f){ (docHandlers[t]=docHandlers[t]||[]).push(f); } };
var winHandlers={};
var window=globalThis; window.innerWidth=1200; window.innerHeight=800; window.wanSetEnable=null;
window.addEventListener=function(t,f){ (winHandlers[t]=winHandlers[t]||[]).push(f); };
function winFire(t,e){ (winHandlers[t]||[]).forEach(function(f){ f(e||{}); }); }
function XMLHttpRequest(){ this.readyState=0; this.status=0; this.responseText=''; }
XMLHttpRequest.prototype.open=function(){}; XMLHttpRequest.prototype.send=function(){}; XMLHttpRequest.prototype.setRequestHeader=function(){};
var setTimeout=function(){ return 1; }, setInterval=function(){ return 1; }, clearTimeout=function(){}, clearInterval=function(){};
function $id(id){ return document.getElementById(id); }
function txt(n){ if(n.nodeValue!==undefined) return n.nodeValue; return n.children.length ? n.children.map(txt).join('') : String(n.textContent||''); }
"""

EPILOGUE = r"""
var out={ p_wan:DOM.p_wan.textContent, p_wan_color:DOM.p_wan.style.color||'', dot_bg:DOM.p_wan_dot.style.background||'',
  dot_shadow:DOM.p_wan_dot.style.boxShadow||'', pill_attrs:Object.keys(DOM.p_wan_pill.attrs).sort(), tipa:DOM.p_wan_pill.classList.contains('tipa'),
  i_opmode:DOM.i_opmode.textContent, hidden_before:DOM.ntip.hidden };
DOM.p_wan_pill.fire('pointerenter',{pointerType:'mouse'});
out.hidden_on_hover=DOM.ntip.hidden;
out.rows=DOM.ntip.children.map(function(r){ return {cls:r.className, text:txt(r)}; });
out.left=DOM.ntip.style.left; out.top=DOM.ntip.style.top;
DOM.p_wan_pill.fire('pointerleave',{pointerType:'mouse'});
out.hidden_after_leave=DOM.ntip.hidden;
DOM.p_wan_pill.fire('pointerenter',{pointerType:'mouse'}); DOM.p_wan_pill.click();
DOM.p_wan_pill.fire('pointerleave',{pointerType:'mouse'});
out.pinned_stays=!DOM.ntip.hidden;
winFire('blur');
out.hidden_after_blur=DOM.ntip.hidden;
console.log(JSON.stringify(out));
"""

def run(ssi):
    js = iife
    def ssi_sub(m):
        h = m.group(1).strip()
        return ssi.get(h, "")
    js = re.sub(r"<%\s*([^%]+?);\s*%>", ssi_sub, js)
    js = re.sub(r"<#([^#]+)#>", r"[\1]", js)
    fd, p = tempfile.mkstemp(suffix=".js"); os.close(fd)
    open(p, "w", encoding="utf-8").write(PRELUDE + "\n" + js + "\n" + EPILOGUE)
    try:
        r = subprocess.run([NODE, p], capture_output=True, text=True, timeout=30)
    finally:
        os.unlink(p)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-600:]
    try:
        return json.loads(r.stdout.strip().splitlines()[-1]), ""
    except Exception as e:
        return None, "bad output: %r %s" % (r.stdout[-300:], e)

BASE = {
    'nvram_get("firmver")': "3.0.0.6", 'nvram_get("buildno")': "102", 'nvram_get("extendno")': "Reaper_v3.4.0_BETA",
    'nvram_get("wans_mode")': "fo", 'get_operation_mode()': '"rt"', 'get_wan_unit()': "0",
    'nvram_get("wan0_state_t")': "2", 'nvram_get("wan0_ipaddr")': "203.0.113.5",
    'nvram_get("wan1_state_t")': "0", 'nvram_get("wan1_ipaddr")': "",
    "wan_ipv6_network()": '{"status":"1","Connection_Type":"native","IPv6_Address":"2001:db8::1/64","IPv6_Gateway":"fe80::1","DNS_Servers":""}',
    'nvram_get("reaper_landns_state")': "fail 125 10.20.0.98",
    "sysuptime()": "1 days 02:03:04 since boot",
}
def scenario(**over):
    d = dict(BASE); d.update(over); return d

def rows_text(o):
    return [r["text"] for r in o.get("rows", [])]

# 1. failing LAN names, WAN up: amber word + dot, five rows, the silent server named
o, err = run(scenario())
check("state 'fail': the IIFE runs clean under node (no ReferenceError from declaration order)", o is not None, err)
if o:
    check("state 'fail': the word stays Connected and turns amber; the dot turns amber", o["p_wan"] == "[Connected]" and o["p_wan_color"] == "var(--amber)" and o["dot_bg"] == "var(--amber)", o)
    check("state 'fail': hover opens the box and places it under the pill", o["hidden_before"] is True and o["hidden_on_hover"] is False and o["left"] == "100px" and o["top"] == "48px", o)
    check("state 'fail': readings = Internet Connected (ip) / LAN names failing (2 min) / why / silent server / every minute",
          rows_text(o) == ["[Internet]: [Connected] (203.0.113.5)", "[RDSH_91]: [RDSH_93] (2 min)", "[RDSH_98]", "[RDSH_99] 10.20.0.98", "[RDSH_101]"], rows_text(o))
    check("state 'fail': row colours ok / warn", [r["cls"] for r in o["rows"]][:2] == ["r ok", "r warn"], o["rows"])
    check("mouse leave closes; a click pins it open through a leave; focus leaving for the framed page closes it",
          o["hidden_after_leave"] is True and o["pinned_stays"] is True and o["hidden_after_blur"] is True, o)

# 2. working: no amber, jade handed back to the CSS
o, err = run(scenario(**{'nvram_get("reaper_landns_state")': "ok 3600 -"}))
check("state 'ok': runs clean", o is not None, err)
if o:
    check("state 'ok': no inline amber (word and dot colours handed back to the CSS)", o["p_wan"] == "[Connected]" and o["p_wan_color"] == "" and o["dot_bg"] == "", o)
    check("state 'ok': readings = Connected (ip) / LAN names working / every minute", rows_text(o) == ["[Internet]: [Connected] (203.0.113.5)", "[RDSH_91]: [RDSH_92]", "[RDSH_101]"], rows_text(o))
    check("state 'ok': the LAN names row is jade", len(o["rows"]) > 1 and o["rows"][1]["cls"] == "r ok", o["rows"])

# 3. WAN down (v4 and v6): danger dot, Disconnected, the no-address line and nothing else
o, err = run(scenario(**{'nvram_get("wan0_state_t")': "0", 'nvram_get("wan0_ipaddr")': "", "wan_ipv6_network()": '{"status":"0"}', 'nvram_get("reaper_landns_state")': "wan 10 -"}))
check("state 'down': runs clean", o is not None, err)
if o:
    check("state 'down': Disconnected in the dashboard's danger colour, no amber", o["p_wan"] == "[Disconnected]" and o["dot_bg"] == "var(--danger)" and o["dot_shadow"] == "none" and o["p_wan_color"] == "", o)
    check("state 'down': readings = Internet Disconnected / no address", rows_text(o) == ["[Internet]: [Disconnected]", "[RDSH_102]"] and o["rows"][0]["cls"] == "r bad", rows_text(o))

# 4. AP mode: the mode name in steel, no tooltip, the pill is plain text again
o, err = run(scenario(**{'get_operation_mode()': '"ap"', 'nvram_get("wan0_state_t")': "0", 'nvram_get("wan0_ipaddr")': ""}))
check("AP mode: runs clean", o is not None, err)
if o:
    check("AP mode: the pill names the mode in steel instead of a structural Disconnected", o["p_wan"] == "[Device_type_03_AP]" and o["dot_bg"] == "var(--steel)" and o["i_opmode"] == "[Device_type_03_AP]", o)
    check("AP mode: no tooltip - affordance attributes removed, hover opens nothing", o["pill_attrs"] == [] and o["tipa"] is False and o["hidden_on_hover"] is True, o)

# 5. IPv6-only WAN: Connected with the (IPv6) marker
o, err = run(scenario(**{'nvram_get("wan0_state_t")': "0", 'nvram_get("wan0_ipaddr")': "", 'nvram_get("reaper_landns_state")': "ok 60 -"}))
check("IPv6-only: runs clean", o is not None, err)
if o:
    check("IPv6-only: Connected, and the Internet line says (IPv6)", o["p_wan"] == "[Connected]" and rows_text(o)[0] == "[Internet]: [Connected] (IPv6)", rows_text(o))

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails:
    print(" - " + f)
sys.exit(1 if fails else 0)
