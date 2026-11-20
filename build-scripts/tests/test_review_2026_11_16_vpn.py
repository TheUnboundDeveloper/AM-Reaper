#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VPN pages: what a switched-off client does, pushed-routes-only OpenVPN targets, WireGuard server peer defaults
and listen-port clashes (2026-11-16).

WHY THIS EXISTS.
1. A VPN client that is switched off never blocks: its Killswitch counts only while the client is on, so the traffic
   of its VPN Director and Policy Routing rules uses the WAN. Several texts said such devices were blocked. The one
   case that does block is a guest network bound to the client with the network's own Kill Switch on.
2. VPN Director: a rule to an OpenVPN client that is on but not in VPN Director mode is never installed. The page
   showed it as a normal rule. Its Apply question also listed a client once per rule.
3. Policy Routing: an OpenVPN client with Redirect Internet traffic = No only carries the networks its server pushes,
   and a TAP client carries nothing for these rules. The Status column said Active for both.
4. WireGuard server: a new peer was only offered an IPv4 address, and ::/0 joined its client-side Allowed IPs only
   when the FIRST server address was IPv6. The listen-port check compared WireGuard with the selected OpenVPN instance
   only, and OpenVPN with the other instance only when its port was edited.
5. rc logged "Starting server." even when the WireGuard interface could not be brought up.

WHAT IT DOES. Cuts the functions out of the real pages and runs them in node (ifaceOff, the Apply list, tgtStatus,
renderTargets, pbrTargetChange, peerDefaults and its helpers, peerDupAddr, listeners, portClash); checks the page
wiring; checks the reworded and new strings in all 25 language packs; compiles _wg_tunnel_create out of rc/wireguard.c
with stubs and checks it returns the result of the bring-up.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1], REAPER_ROUTER_SRC or REAPER_SRC)."""
import glob, json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
www = os.path.join(SRC, "www") if SRC else ""
PAGES = ("Reaper_VPNDirector.asp", "Reaper_VPNRouting.asp", "Reaper_VPNServer.asp", "Reaper_VPNClient.asp")
if not www or not all(os.path.isfile(os.path.join(www, p)) for p in PAGES):
    skip("no router source tree with the VPN pages (argv[1] / REAPER_ROUTER_SRC / REAPER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))
def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

def cut(text, name):
    """one function, cut out of a page by matching its braces (strings and comments are stepped over)"""
    m = re.search(r"^[ \t]*function %s\(" % re.escape(name), text, re.M)
    if not m:
        return None
    i, depth, n = text.index("{", m.end()), 0, len(text)
    while i < n:
        c = text[i]
        if c in "'\"`":
            j = i + 1
            while text[j] != c:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if text.startswith("/*", i):
            i = text.index("*/", i) + 2
            continue
        if text.startswith("//", i):
            i = text.index("\n", i)
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():i + 1] + "\n"
        i += 1
    return None

NODE = shutil.which("node")
def run_node(label, parts, tail):
    """parts: [(name, source or None)]; returns the parsed JSON the script prints, or None"""
    missing = [n for n, s in parts if s is None]
    check(label + ": the functions can be cut out of the page", not missing, missing)
    if missing or not NODE:
        return None
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "t.js")
        open(p, "w", encoding="utf-8").write("'use strict';\n" + "".join(s for n, s in parts) + tail)
        r = subprocess.run([NODE, p], capture_output=True, text=True)
    if r.returncode != 0:
        check(label + ": runs in node", False, r.stderr[-400:])
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        check(label + ": prints JSON", False, r.stdout[-300:])
        return None
if not NODE:
    print("note no node on the host - the functions are not run")

# =====================================================================================================================
# VPN Director: why a rule does nothing right now
# =====================================================================================================================
D = rd("www", "Reaper_VPNDirector.asp")
check("Director: ASCII only", not any(ord(c) > 127 for c in D))
check("Director: the Killswitch-blocks branch is gone from ifaceOff", ".ks === '1' ? `<#RVDR_15#>`" not in D)
offs = re.search(r"^  var offs = \[\], offSeen = \[\];\n  RULES\.forEach\(function\(r\)\{.*\n", D, re.M)
check("Director: the Apply question keeps the clients already listed in their own list",
      offs is not None and "offs.indexOf(ifaceName(f[4]))" not in D and "if (offs.length && !confirm(`<#RVDR_32#>` + '\\n- ' + offs.join('\\n- '))) return;" in D)
# the harness: clients 1..5 with their Redirect mode, Killswitch and state; the rules for the Apply list
DIR_HEAD = """
var OV = [null, {desc: 'a', rgw: '2', ks: '1'}, {desc: '', rgw: '0', ks: '1'}, {desc: '', rgw: '1', ks: '0'}, {desc: '', rgw: '2', ks: '1'}, {desc: '', rgw: '3', ks: '0'}];
var WG = [null, {desc: '', en: '0', ks: '1'}, {desc: '', en: '1', ks: '1'}, {desc: '', en: '0', ks: '0'}, {desc: '', en: '1', ks: '0'}, {desc: '', en: '1', ks: '0'}];
var EAS = ['2', '3', '4', '5'];
var RULES = [{f: ['1', 'x', '192.0.2.10', '', 'OVPN1']}, {f: ['1', 'y', '192.0.2.11', '', 'OVPN1']}, {f: ['1', 'z', '192.0.2.12', '', 'OVPN1']},
  {f: ['1', '', '192.0.2.13', '', 'OVPN2']}, {f: ['1', '', '192.0.2.14', '', 'OVPN2']}, {f: ['0', '', '192.0.2.15', '', 'WGC1']},
  {f: ['1', '', '192.0.2.16', '', 'WGC3']}, {f: ['1', '', '192.0.2.17', '', 'OVPN4']}, {f: ['1', '', '192.0.2.18', '', 'WAN']}, {f: ['1', 'broken']}];
"""
DIR_TAIL = """
var R = {};
['OVPN1', 'OVPN2', 'OVPN3', 'OVPN4', 'OVPN5', 'WGC1', 'WGC2', 'WGC3', 'WAN', 'XYZ'].forEach(function(t){ R[t] = ifaceOff(t); });
console.log(JSON.stringify({off: R, offs: offs}));
"""
j = run_node("Director", [("head", DIR_HEAD), ("ovEnabled", cut(D, "ovEnabled")), ("ifaceName", cut(D, "ifaceName")), ("ifaceOff", cut(D, "ifaceOff")),
                          ("the Apply list", offs.group(0) if offs else None)], DIR_TAIL)
if j:
    o = j["off"]
    check("ifaceOff: an OpenVPN client that is off uses the WAN, with its Killswitch on or off", o["OVPN1"] == "<#RVDR_16#>", o)
    check("ifaceOff: an OpenVPN client that is on but not in VPN Director mode (Redirect No, Redirect all) has its own reason",
          o["OVPN2"] == "<#RVDR_15#>" and o["OVPN3"] == "<#RVDR_15#>", o)
    check("ifaceOff: an OpenVPN client that is on and in VPN Director mode is in use", o["OVPN4"] == "" and o["OVPN5"] == "", o)
    check("ifaceOff: a WireGuard client that is off uses the WAN, with its Killswitch on or off; one that is on is in use",
          o["WGC1"] == "<#RVDR_16#>" and o["WGC3"] == "<#RVDR_16#>" and o["WGC2"] == "", o)
    check("ifaceOff: WAN and an unknown target have no reason", o["WAN"] == "" and o["XYZ"] == "", o)
    check("Apply question: one line per client, for both reasons; disabled rules, working clients and broken records are left out",
          j["offs"] == ["OpenVPN 1: a (<#RVDR_16#>)", "OpenVPN 2 (<#RVDR_15#>)", "WireGuard 3 (<#RVDR_16#>)"], j["offs"])
check("Director: the group row shows the reason", "(ifaceOff(g) ? ' <span class=\"tag warn\">' + hx(ifaceOff(g)) + '</span>' : '')" in D)

# =====================================================================================================================
# Policy Routing: Status of an OpenVPN target that does not carry the default route
# =====================================================================================================================
P = rd("www", "Reaper_VPNRouting.asp")
check("Policy Routing: ASCII only", not any(ord(c) > 127 for c in P))
check("Policy Routing: the note sits after the Killswitch note, the hint beside the WireGuard hint",
      re.search(r'<li id="ksnote"><#RVR_64#></li>\n(\s*<!--[^\n]*-->\n)?\s*<li><#RVR_76#></li>\n', P) is not None
      and '<div class="hint" id="wghint" style="display:none"><#RVR_54#></div>\n  <div class="hint" id="ovhint" style="display:none"><#RVR_76#></div>\n' in P)
check("Policy Routing: every status reply refreshes the targets (and with them the hint)", P.count("cfgArrays(j); renderTargets();") == 3)
PR_HEAD = """
function esc(s){ return String(s); }
var WGON = [0, 0, 0, 0, 0], OVON = [0, 0, 0, 0, 0], WKS = [0, 0, 0, 0, 0], OKS = [0, 0, 0, 0, 0], OMODE = [0, 0, 0, 0, 0];
var EL = {};
function mk(id){ return EL[id] || (EL[id] = {id: id, style: {display: 'unset'}, value: '', options: []}); }
var document = {getElementById: mk};
['OVPN1', 'OVPN2', 'OVPN3', 'OVPN4', 'OVPN5', 'WGC1', 'WGC2', 'WGC3', 'WGC4', 'WGC5', 'WAN', 'BLOCK'].forEach(function(v){ mk('e_target').options.push({value: v, hidden: false, disabled: false}); });
"""
PR_TAIL = """
/* OpenVPN 1: default route + Killswitch. 2: pushed routes only. 3: TAP. 4: switched off (stored mode 1). 5: default route, no Killswitch.
   The second reply carries a stale Killswitch for the pushed-routes client: the page must still not show it. */
cfgArrays({wg: [1, 0, 0, 0, 0], ov: [1, 1, 1, 0, 1], wks: [1, 1, 0, 0, 0], oks: [1, 0, 0, 0, 0], omode: [0, 1, 2, 1, 0]});
var S = {};
['OVPN1', 'OVPN2', 'OVPN3', 'OVPN4', 'OVPN5', 'WGC1', 'WGC2', 'WAN', 'BLOCK'].forEach(function(t){ S[t] = tgtStatus({target: t}); });
mk('e_target').value = 'OVPN1';
renderTargets();
var shown = {}; mk('e_target').options.forEach(function(o){ shown[o.value] = !o.hidden && !o.disabled; });
var hint = {};
['OVPN1', 'OVPN2', 'OVPN3', 'OVPN5', 'WGC1', 'WAN', 'BLOCK'].forEach(function(t){ mk('e_target').value = t; pbrTargetChange(); hint[t] = [mk('ovhint').style.display, mk('wghint').style.display, mk('wanhint').style.display]; });
cfgArrays({oks: [1, 1, 0, 0, 0], omode: [0, 1, 2, 1, 0]});
var stale = tgtStatus({target: 'OVPN2'});
cfgArrays({wg: [1, 0, 0, 0, 0]});
console.log(JSON.stringify({S: S, shown: shown, hint: hint, stale: stale, kept: OMODE}));
"""
j = run_node("Policy Routing", [("head", PR_HEAD), ("cfgArrays", cut(P, "cfgArrays")), ("tgtStatus", cut(P, "tgtStatus")),
                                ("renderTargets", cut(P, "renderTargets")), ("pbrTargetChange", cut(P, "pbrTargetChange"))], PR_TAIL)
if j:
    S = j["S"]
    def has(s, *t): return all(x in s for x in t)
    def lacks(s, *t): return not any(x in s for x in t)
    check("tgtStatus mode 0: Active, with the Killswitch text when the switch is on and without it when it is off",
          has(S["OVPN1"], "<#RVR_72#>", "<#RVR_74#>", 'class="dot ks"') and lacks(S["OVPN1"], "<#RVR_75#>", "TAP", "<#RVR_73#>")
          and has(S["OVPN5"], "<#RVR_72#>") and lacks(S["OVPN5"], "<#RVR_74#>", "<#RVR_75#>", "TAP"), (S["OVPN1"], S["OVPN5"]))
    check("tgtStatus mode 1: Active + the separator + pushed routes only, no Killswitch text",
          S["OVPN2"] == '<span class="st"><span class="dot"></span><#RVR_72#> <span class="dash">&middot;</span> <#RVR_75#></span>', S["OVPN2"])
    check("tgtStatus mode 1: no Killswitch text even if the reply still carried the switch", j["stale"] == S["OVPN2"], j["stale"])
    check("tgtStatus mode 2: the Inactive / WAN status + the separator + TAP",
          S["OVPN3"] == '<span class="st off"><span class="dot off"></span><#RVR_73#> <span class="dash">&middot;</span> <span class="via">WAN</span> <span class="dash">&middot;</span> TAP</span>', S["OVPN3"])
    check("tgtStatus: a switched-off client is Inactive / WAN whatever its mode",
          S["OVPN4"] == '<span class="st off"><span class="dot off"></span><#RVR_73#> <span class="dash">&middot;</span> <span class="via">WAN</span></span>', S["OVPN4"])
    check("tgtStatus: WireGuard, WAN and Block are as before",
          has(S["WGC1"], "<#RVR_72#>", "<#RVR_74#>") and S["WGC2"] == S["OVPN4"] and has(S["WAN"], "<#RVR_72#>") and lacks(S["WAN"], "<#RVR_74#>") and "&mdash;" in S["BLOCK"], S)
    sh = j["shown"]
    check("renderTargets: a TAP client is not offered for a new rule; a pushed-routes client and a default-route client are",
          sh["OVPN3"] is False and sh["OVPN2"] is True and sh["OVPN1"] is True and sh["OVPN5"] is True, sh)
    check("renderTargets: a switched-off client is still not offered; WAN, Block and an enabled WireGuard client are",
          sh["OVPN4"] is False and sh["WGC2"] is False and sh["WGC1"] is True and sh["WAN"] is True and sh["BLOCK"] is True, sh)
    h = j["hint"]
    check("editor hint: shown for a pushed-routes target and for a TAP target, hidden for a default-route target",
          h["OVPN2"][0] == "" and h["OVPN3"][0] == "" and h["OVPN1"][0] == "none" and h["OVPN5"][0] == "none", h)
    check("editor hint: hidden for WireGuard, WAN and Block; their own hints are as before",
          h["WGC1"] == ["none", "", "none"] and h["WAN"] == ["none", "none", ""] and h["BLOCK"] == ["none", "none", "none"], h)
    check("cfgArrays: a reply without omode keeps the last one", j["kept"] == [0, 1, 2, 1, 0], j["kept"])
check("Policy Routing: editing a rule refreshes the target hints", "document.getElementById('e_target').value=r.target||'OVPN1';\n  pbrTargetChange();" in P)

# =====================================================================================================================
# WireGuard server: defaults of a new peer
# =====================================================================================================================
V = rd("www", "Reaper_VPNServer.asp")
check("VPN Server: ASCII only", not any(ord(c) > 127 for c in V))
check("peerOpen: a new peer takes peerDefaults, an existing peer keeps its stored values",
      "var d = p ? null : peerDefaults(wgEff('addr'), WP);" in V
      and "q('e_waddr').value = p ? p.addr : d.addr; q('e_waips').value = p ? p.aips : d.addr; q('e_wcaips').value = p ? p.caips : d.caips;" in V
      and "hostAddr(wgEff('addr')).indexOf(':')" not in V and "nextPeerAddr" not in V)
PD_HEAD = """
var SRV = '10.6.0.1/32,fd00::1/64', WP = [];
function wgEff(k){ return k === 'addr' ? SRV : ''; }
"""
PD_TAIL = """
function P(u, addr, en){ return {u: u, enable: en === undefined ? '1' : en, addr: addr}; }
var R = {};
R.v4first = peerDefaults('10.6.0.1/32,fd00::1/64', []);
R.v6first = peerDefaults('fd00::1/64,10.6.0.1/32', []);
R.v4only = peerDefaults('10.6.0.1/32', []);
R.v6only = peerDefaults('2001:db8:0:1::1/64', []);
R.usedV4 = peerDefaults('10.6.0.1/32,fd00::1/64', [P(1, '10.6.0.2/32')]);
R.usedV6 = peerDefaults('10.6.0.1/32,fd00::1/64', [P(1, '10.6.0.9/32,fd00::2/128')]);
R.usedOff = peerDefaults('10.6.0.1/32,fd00::1/64', [P(1, '10.6.0.2/32', '0')]);
R.expanded = peerDefaults('10.6.0.1/32,fd00::1/64', [P(1, 'FD00:0000:0000:0000:0000:0000:0000:0002/128')]);
R.srvExpanded = peerDefaults('10.6.0.1/32,fd00:0:0:0:0:0:0:2/64', []);
var nine = []; for (var i = 2; i <= 9; i++) nine.push(P(i, '10.6.0.' + i + '/32'));
R.ten = peerDefaults('10.6.0.1/32,fd00::1/64', nine);
R.linklocal = peerDefaults('fe80::1/64,10.6.0.1/32', []);
R.secondV6 = peerDefaults('fe80::1/64,2001:db8::1/64', []);
R.longPrefix = peerDefaults('192.0.2.1/24,2001:db8:1:2:3:4:5:1/64', []);
R.none = peerDefaults('', []);
R.junk = peerDefaults('not-an-address', []);
var full = []; for (i = 2; i <= 254; i++) full.push(P(i, '10.6.0.' + i + '/32'));
R.full = peerDefaults('10.6.0.1/32', full);
R.exp = [exp6('2001:db8::1'), exp6('::'), exp6('1::2::3'), exp6('1:2:3:4:5:6:7'), exp6('1:2:3:4:5:6:7:8:9'), exp6('fd00::g'), exp6('')];
R.fmt = [fmt6([0x2001, 0xdb8, 0, 0, 1, 0, 0, 1]), fmt6([0, 0, 0, 0, 0, 0, 0, 0]), fmt6([0x2001, 0xdb8, 0, 1, 1, 1, 1, 1]), fmt6([0, 0, 0, 0, 0, 0, 0, 1]), fmt6([0xfd00, 0, 0, 0, 0, 0, 0, 0])];
R.canon = [canonAddr('2001:0DB8:0000:0000:0000:0000:0000:0001/64'), canonAddr('10.6.0.3/32'), canonAddr(' FD00::3 ')];
R.srv = [srv4('fd00::1/64,10.6.0.1/32'), srv4('fd00::1/64'), srv4('300.1.1.1/32,192.0.2.1/24'), srv6('10.6.0.1/32')];
/* duplicate check: the server is fd00::1, peer 2 holds fd00::5 written the compressed way */
WP = [P(2, '10.6.0.5/32,fd00::5/128'), P(3, '10.6.0.6/32', '0')];
R.dup = [peerDupAddr('10.6.0.7/32,fd00:0:0:0:0:0:0:5/128', 4), peerDupAddr('10.6.0.7/32,FD00:0000::0005/128', 2), peerDupAddr('10.6.0.7/32,fd00:0:0:0:0:0:0:1/128', 4),
  peerDupAddr('10.6.0.5/32', 4), peerDupAddr('10.6.0.6/32,fd00::6/128', 4)];
console.log(JSON.stringify(R));
"""
j = run_node("peer defaults", [("head", PD_HEAD)] + [(n, cut(V, n)) for n in ("hostAddr", "peerUsed", "exp6", "fmt6", "canonAddr", "srv4", "srv6", "peerDefaults", "peerDupAddr")], PD_TAIL)
if j:
    both = {"addr": "10.6.0.2/32,fd00::2/128", "caips": "0.0.0.0/0,::/0"}
    three = {"addr": "10.6.0.3/32,fd00::3/128", "caips": "0.0.0.0/0,::/0"}
    check("peerDefaults: dual-stack server written IPv4 first - both families, ::/0 offered", j["v4first"] == both, j["v4first"])
    check("peerDefaults: dual-stack server written IPv6 first - the same result", j["v6first"] == both, j["v6first"])
    check("peerDefaults: IPv4-only server - an IPv4 /32 and 0.0.0.0/0 alone", j["v4only"] == {"addr": "10.6.0.2/32", "caips": "0.0.0.0/0"}, j["v4only"])
    check("peerDefaults: IPv6-only server - an IPv6 /128, ::/0 offered", j["v6only"] == {"addr": "2001:db8:0:1::2/128", "caips": "0.0.0.0/0,::/0"}, j["v6only"])
    check("peerDefaults: a host number used in either family is skipped in both", j["usedV4"] == three and j["usedV6"] == three, (j["usedV4"], j["usedV6"]))
    check("peerDefaults: a slot that is not in use does not hold its number", j["usedOff"] == both, j["usedOff"])
    check("peerDefaults: an address stored the expanded way is the same address as its compressed spelling",
          j["expanded"] == three and j["srvExpanded"] == three, (j["expanded"], j["srvExpanded"]))
    check("peerDefaults: the IPv6 host is written with the same digits as the IPv4 host", j["ten"] == {"addr": "10.6.0.10/32,fd00::10/128", "caips": "0.0.0.0/0,::/0"}, j["ten"])
    check("peerDefaults: a link-local server address is not used (no ::/0 without an IPv6 address); the next IPv6 entry is",
          j["linklocal"] == {"addr": "10.6.0.2/32", "caips": "0.0.0.0/0"} and j["secondV6"] == {"addr": "2001:db8::2/128", "caips": "0.0.0.0/0,::/0"}, (j["linklocal"], j["secondV6"]))
    check("peerDefaults: the first seven groups of the server address are kept", j["longPrefix"] == {"addr": "192.0.2.2/32,2001:db8:1:2:3:4:5:2/128", "caips": "0.0.0.0/0,::/0"}, j["longPrefix"])
    check("peerDefaults: no usable server address or no free number - an empty address, 0.0.0.0/0",
          j["none"] == {"addr": "", "caips": "0.0.0.0/0"} and j["junk"] == j["none"] and j["full"] == j["none"], (j["none"], j["junk"], j["full"]))
    check("exp6: :: aware, refuses a second ::, a wrong group count and a bad group",
          j["exp"] == [[0x2001, 0xdb8, 0, 0, 0, 0, 0, 1], [0] * 8, None, None, None, None, None], j["exp"])
    check("fmt6: lower case, the first longest run of zero groups as ::, a single zero group kept",
          j["fmt"] == ["2001:db8::1:0:0:1", "::", "2001:db8:0:1:1:1:1:1", "::1", "fd00::"], j["fmt"])
    check("canonAddr: one spelling per address, prefix length dropped", j["canon"] == ["2001:db8::1", "10.6.0.3", "fd00::3"], j["canon"])
    check("srv4 / srv6: the first entry of the family wherever it sits, '' / null when there is none", j["srv"] == ["10.6.0.1", "", "192.0.2.1", None], j["srv"])
    d = j["dup"]
    check("peerDupAddr: the expanded spelling of another peer's or the server's IPv6 address is a duplicate",
          d[0] == "fd00::5" and d[2] == "fd00::1" and d[3] == "10.6.0.5", d)
    check("peerDupAddr: the peer being edited and an unused slot are not duplicates", d[1] == "" and d[4] == "", d)

# =====================================================================================================================
# VPN server listen ports
# =====================================================================================================================
check("validate: one check for every VPN server, the message names what the port runs into",
      "var pc = portClash(listeners(c)); if (pc) return bad(pc.id, `<#RVSV_145#>` + ' (' + pc.who + ')');" in V
      and "c.vpn_server_port === OV[oth].port && c.vpn_server_proto === OV[oth].proto" not in V
      and "c.wgs_port === c.vpn_server_port" not in V)
PC_HEAD = """
var CUR, NV, OV, IP, TAB_ON;
var WGDEF = { port: '51820' };
/* a scenario: what is stored (o), what this save changes (ch); returns portClash(listeners(collected)) */
function run(o, ch){
  var k, c = {};
  CUR = o.cur || '1';
  TAB_ON = o.tabs || {ovpn: true, wg: true, ipsec: true, pptp: true};
  OV = {'1': {proto: o.p1 || 'udp', port: o.port1 || '1194'}, '2': {proto: o.p2 || 'udp', port: o.port2 || '1195'}};
  IP = {isakmp: o.isakmp === undefined ? '500' : o.isakmp, natt: o.natt === undefined ? '4500' : o.natt};
  NV = {vpn_serverx_start: o.start === undefined ? '' : o.start, vpn_server_port: OV[CUR].port, vpn_server_proto: OV[CUR].proto,
    wgs_enable: o.wg || '0', wgs_port: o.wgport === undefined ? '51820' : o.wgport, ipsec_server_enable: o.ipsec || '0'};
  for (k in NV) c[k] = NV[k];
  for (k in (ch || {})) c[k] = ch[k];
  return {clash: portClash(listeners(c)), n: listeners(c).length};
}
"""
PC_TAIL = """
var R = {};
/* 1. WireGuard port set to the port of the OpenVPN instance that is NOT selected */
R.wgVsOther = run({cur: '1', start: '1,2,', port2: '51900', wg: '1'}, {wgs_port: '51900'});
/* 2. the selected OpenVPN instance changed to the WireGuard port */
R.ovToWg = run({start: '1,', wg: '1'}, {vpn_server_port: '51820'});
R.ovProtoToUdp = run({start: '1,', p1: 'tcp-server', port1: '51820', wg: '1'}, {vpn_server_proto: 'udp'});
/* 3. switching on an instance whose STORED port clashes */
R.enableOv = run({start: '', port1: '51820', wg: '1'}, {vpn_serverx_start: '1,'});
R.enableOvNeverSavedWg = run({start: '', port1: '51820', wg: '1', wgport: ''}, {vpn_serverx_start: '1,'});
R.enableWg = run({start: '2,', port2: '51820', wg: '0'}, {wgs_enable: '1'});
R.enableWgNeverSaved = run({start: '1,', port1: '51820', wg: '0', wgport: ''}, {wgs_enable: '1', wgs_port: '51820'});
R.enableOvVsOv = run({cur: '2', start: '1,', port1: '1194', port2: '1194'}, {vpn_serverx_start: '1,2,'});
R.ovPortVsOv = run({start: '1,2,'}, {vpn_server_port: '1195'});
/* 4. OpenVPN on TCP may share the number with WireGuard */
R.tcp = run({start: '1,', p1: 'tcp-server', wg: '1'}, {vpn_server_port: '51820'});
R.tcpOther = run({start: '1,2,', p2: 'tcp-server', port2: '51900', wg: '1'}, {wgs_port: '51900'});
R.ovTcpVsOvUdp = run({start: '1,2,', p2: 'tcp-server'}, {vpn_server_port: '1195'});
/* 5. a server that is off does not hold its port */
R.ovOff = run({start: '', wg: '1'}, {vpn_server_port: '51820'});
R.wgOff = run({start: '1,', wg: '0'}, {wgs_port: '1194'});
R.otherOff = run({start: '1,', port2: '51900', wg: '1'}, {wgs_port: '51900'});
R.ipsecOff = run({wg: '1'}, {wgs_port: '4500'});
/* 6. IPsec holds UDP 500 and 4500 */
R.wg4500 = run({wg: '1', ipsec: '1'}, {wgs_port: '4500'});
R.wg500 = run({wg: '1', ipsec: '1'}, {wgs_port: '500'});
R.enableIpsec = run({wg: '1', wgport: '4500'}, {ipsec_server_enable: '1'});
R.ovTcp500 = run({start: '1,', p1: 'tcp-server', ipsec: '1'}, {vpn_server_port: '500'});
/* 7. a save that touches neither side is never blocked by a clash that is already stored */
R.untouched = run({start: '1,', port1: '51820', wg: '1'}, {});
R.untouchedOther = run({start: '1,2,', port1: '1194', port2: '1194'}, {});
R.untouchedIpsec = run({wg: '1', wgport: '4500', ipsec: '1'}, {});
/* 8. ports are compared as numbers; a port that is not a number is left to the range check */
R.leadingZero = run({start: '1,', wg: '1'}, {vpn_server_port: '051820'});
R.notANumber = run({start: '1,', wg: '1'}, {vpn_server_port: '51820x'});
/* 9. a model without a server type does not count it */
R.noWgTab = run({start: '1,', wg: '1', tabs: {ovpn: true, wg: false, ipsec: true}}, {vpn_server_port: '51820'});
R.noOvTab = run({start: '1,', port1: '51820', wg: '0', tabs: {ovpn: false, wg: true, ipsec: true}}, {wgs_enable: '1'});
/* 10. nothing clashes on the defaults */
R.defaults = run({start: '1,2,', wg: '1', ipsec: '1'}, {vpn_server_port: '1196'});
console.log(JSON.stringify(R));
"""
j = run_node("listen ports", [("head", PC_HEAD), ("startHas", cut(V, "startHas")), ("listeners", cut(V, "listeners")), ("portClash", cut(V, "portClash"))], PC_TAIL)
if j:
    def hit(k, fid, who): return j[k]["clash"] == {"id": fid, "who": who}
    def free(*ks): return all(j[k]["clash"] is None for k in ks)
    check("port clash: WireGuard set to the port of the OpenVPN instance that is not selected - refused", hit("wgVsOther", "w_port", "OpenVPN 2"), j["wgVsOther"])
    check("port clash: OpenVPN changed to the WireGuard port, or switched to UDP on it - refused",
          hit("ovToWg", "o_port", "WireGuard") and hit("ovProtoToUdp", "o_port", "WireGuard"), (j["ovToWg"], j["ovProtoToUdp"]))
    check("port clash: switching on an OpenVPN instance whose stored port is the WireGuard port - refused (also with a never-saved WireGuard port)",
          hit("enableOv", "o_port", "WireGuard") and hit("enableOvNeverSavedWg", "o_port", "WireGuard"), (j["enableOv"], j["enableOvNeverSavedWg"]))
    check("port clash: switching on WireGuard on a port an OpenVPN instance holds - refused",
          hit("enableWg", "w_port", "OpenVPN 2") and hit("enableWgNeverSaved", "w_port", "OpenVPN 1"), (j["enableWg"], j["enableWgNeverSaved"]))
    check("port clash: the two OpenVPN instances - a port edit and switching one on with the stored port both refused",
          hit("ovPortVsOv", "o_port", "OpenVPN 2") and hit("enableOvVsOv", "o_port", "OpenVPN 1"), (j["ovPortVsOv"], j["enableOvVsOv"]))
    check("port clash: OpenVPN on TCP may use the WireGuard number, and the number of a UDP instance", free("tcp", "tcpOther", "ovTcpVsOvUdp", "ovTcp500"),
          [j[k] for k in ("tcp", "tcpOther", "ovTcpVsOvUdp", "ovTcp500")])
    check("port clash: a server that is off does not hold its port", free("ovOff", "wgOff", "otherOff", "ipsecOff"), [j[k] for k in ("ovOff", "wgOff", "otherOff", "ipsecOff")])
    check("port clash: WireGuard on 4500 or 500 with IPsec on - refused; switching IPsec on over a WireGuard port - refused",
          hit("wg4500", "w_port", "IPsec") and hit("wg500", "w_port", "IPsec") and hit("enableIpsec", "t_ipen", "WireGuard"), (j["wg4500"], j["wg500"], j["enableIpsec"]))
    check("port clash: a save that touches neither side is not blocked", free("untouched", "untouchedOther", "untouchedIpsec"),
          [j[k] for k in ("untouched", "untouchedOther", "untouchedIpsec")])
    check("port clash: ports compared as numbers; a value that is not a number is left to the range check",
          hit("leadingZero", "o_port", "WireGuard") and free("notANumber"), (j["leadingZero"], j["notANumber"]))
    check("port clash: a server type the model does not have is not counted", free("noWgTab", "noOvTab"), (j["noWgTab"], j["noOvTab"]))
    check("port clash: the defaults do not clash (OpenVPN 1 + 2, WireGuard, IPsec 500 + 4500 listed)", free("defaults") and j["defaults"]["n"] == 5, j["defaults"])

# =====================================================================================================================
# language packs
# =====================================================================================================================
def val(text, key):
    m = re.search(r"^%s=(.*)$" % re.escape(key), text, re.M)
    return m.group(1).rstrip("\r") if m else None
packs = sorted(p for p in glob.glob(os.path.join(www, "*.dict")) if os.path.basename(p) != "temp.dict")
texts = {os.path.basename(p)[:-5]: open(p, encoding="utf-8", errors="replace").read() for p in packs}
en = texts.get("EN", "")
check("25 language packs", len(texts) == 25, sorted(texts))
counts = {l: t.count("\n") for l, t in texts.items()}
check("every pack has the same number of lines", len(set(counts.values())) == 1, counts)
EN = {
 "RVDR_15": "not in VPN Director mode, rule not used",
 "RVDR_32": "These rules have no effect right now. A switched-off client blocks nothing, even with its Killswitch on. Apply anyway?",
 "RVCL_146": "The OpenVPN tunnel stops. Devices routed through it use the WAN until it is switched on again; its Killswitch does not block them while it is off. A guest network bound to this client with its own Kill Switch on loses Internet access.",
 "RVCL_150": "The WireGuard tunnel stops. Devices routed through it use the WAN until it is switched on again; its Killswitch does not block them while it is off. A guest network bound to this client with its own Kill Switch on loses Internet access.",
 "RVR_38": "A device rule here does what a VPN Director source rule does, plus: it can target Block, a MAC rule follows the device across IP changes, and it overrides VPN Director. When the tunnel is down, the traffic is blocked only if the Killswitch of that client is on; otherwise it uses the WAN. If you only need plain source routing, VPN Director is enough.",
 "RVR_54": "WireGuard targets need a hardware-acceleration bypass (the same one VPN Director uses). A source rule bypasses only that address; a destination or MAC rule bypasses the LAN, so LAN traffic loses hardware acceleration while such a rule exists. If the WireGuard client is on but its tunnel is down, its Killswitch decides whether the selected traffic is blocked or uses the WAN. Traffic of a switched-off client uses the WAN.",
 "RVCL_34": "On: while this client is switched on and its tunnel is down, devices routed through it lose Internet access instead of using the WAN. A switched-off client blocks nothing.",
 "RVCL_148": "With the Killswitch on, routed devices have no Internet access while the client is switched on and its tunnel is down.",
 "RVR_75": "pushed routes only",
 "RVR_76": "Pushed routes only: that OpenVPN client has Redirect Internet traffic set to No, so only the networks its server pushes use the tunnel and everything else uses the WAN. Set Redirect to VPN Director rules on the client page to send all of this traffic through the tunnel. A rule to a TAP client has no effect.",
}
got = {k: val(en, k) for k in EN}
check("EN: the reworded and the new texts", got == EN, {k: v for k, v in got.items() if v != EN[k]})
old = [s for s in ("Killswitch blocks", "lose Internet access while its killswitch", "fail-closed (tunnel down = blocked", "blocked when that client's Killswitch is on") if s in en]
check("EN: the texts that promised a block from a switched-off client are gone", not old, old)
bad = {}
for l, t in texts.items():
    for k in EN:
        v = val(t, k)
        if not v:
            bad[l + " " + k] = "missing"
        elif l != "EN" and v == EN[k]:
            bad[l + " " + k] = "still English"
        elif any(x in v for x in ('"', "'", "`", "${")) or (l == "EN" and any(ord(c) > 127 for c in v)):
            bad[l + " " + k] = "a character the pages cannot carry"
        elif t.count("\n%s=" % k) + (1 if t.startswith(k + "=") else 0) != 1:
            bad[l + " " + k] = "not exactly once"
check("25 packs carry the ten texts once each, translated, without quote characters", not bad, bad)
short = {l: val(t, "RVR_75") for l, t in texts.items() if len(val(t, "RVR_75") or "") > 30}
check("the Status cell text stays short in every pack (30 characters)", not short, short)
kw = {l: [k for k in ("RVDR_32", "RVCL_146", "RVCL_150", "RVR_38", "RVR_54", "RVCL_148") if "Killswitch" not in (val(t, k) or "")] for l, t in texts.items()}
check("every pack keeps the name Killswitch in the texts that speak of it", not any(kw.values()), {l: v for l, v in kw.items() if v})
ks = {l: [k for k in ("RVCL_146", "RVCL_150") if "Kill Switch" not in (val(t, k) or "")] for l, t in texts.items()}
check("the switch-off question names the guest network's own Kill Switch as the Network page spells it", not any(ks.values()), {l: v for l, v in ks.items() if v})
# (HU: the article follows the name - "Az OpenVPN", "A WireGuard")
same = {l: 1 for l, t in texts.items() if (val(t, "RVCL_146") or "").replace("Az OpenVPN", "A WireGuard").replace("OpenVPN", "WireGuard") != (val(t, "RVCL_150") or "")}
check("the OpenVPN and the WireGuard switch-off question say the same thing", not same, sorted(same))
for page, T in (("Reaper_VPNDirector.asp", D), ("Reaper_VPNRouting.asp", P), ("Reaper_VPNServer.asp", V), ("Reaper_VPNClient.asp", rd("www", "Reaper_VPNClient.asp"))):
    miss = [x for x in sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", T))) if ("\n%s=" % x) not in en]
    check("%s: every dict token exists" % page, not miss, miss)
    js = T[T.rfind("<script>"):]
    check("%s: tokens in the script only inside backticks" % page, "<#" not in re.sub(r"`[^`]*`", "", js))
    if NODE:
        # the page script with every server tag read as 0 and every dictionary text as an empty string
        body = re.sub(r"`[^`]*`", "''", re.sub(r"<%.*?%>", "0", js[len("<script>"):js.rfind("</script>")]))
        with tempfile.TemporaryDirectory() as td:
            jp = os.path.join(td, "p.js")
            open(jp, "w", encoding="utf-8", errors="surrogateescape").write(body)
            r = subprocess.run([NODE, "--check", jp], capture_output=True, text=True)
        check("%s: the page script parses (node --check)" % page, r.returncode == 0, r.stderr[-300:])
check("the reused key is still used by the VPN Director page, the new keys by the Policy Routing page",
      "`<#RVDR_15#>`" in D and "`<#RVR_75#>`" in P and P.count("<#RVR_76#>") == 2)

# =====================================================================================================================
# rc/wireguard.c: the server start says when the interface did not come up
# =====================================================================================================================
WGC = os.path.join(SRC, "rc", "wireguard.c")
if os.path.isfile(WGC):
    w = open(WGC, encoding="utf-8", errors="surrogateescape").read()
    mf = re.search(r"^static int _wg_tunnel_create\(char\* prefix, char\* ifname, char\* conf_path\)\n\{\n.*?^\}\n", w, re.S | re.M)
    check("wireguard.c: _wg_tunnel_create returns the result of bringing the interface up",
          mf is not None and 'return eval("ip", "link", "set", "up", "dev", ifname);' in mf.group(0) and "static void _wg_tunnel_create(" not in w)
    ms = re.search(r"^void start_wgs\(int unit\)\n\{\n.*?^\}\n", w, re.S | re.M)
    body = ms.group(0) if ms else ""
    check("wireguard.c: start_wgs keeps that result and logs the failure instead of Starting server.",
          "up_rc = _wg_tunnel_create(prefix, ifname, path);" in body
          and 'if (up_rc)\n\t\tlogmessage("WireGuard", "WireGuard server did not start: the interface could not be brought up (is UDP port %s in use?)", nvram_pf_safe_get(prefix, "port"));\n\telse\n\t\tlogmessage("WireGuard", "Starting server.");\n}\n' in body)
    cc = shutil.which("gcc") or shutil.which("cc")
    if mf and cc:
        stub = r"""
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
static int UP_RC, CALLS;
static int fake_eval(const char *cmd, ...)
{
	va_list ap; const char *a; int up = 0;
	va_start(ap, cmd);
	while ((a = va_arg(ap, const char *)) != NULL) if (!strcmp(a, "up")) up = 1;
	va_end(ap);
	CALLS++;
	return up ? UP_RC : 0;
}
#define eval(cmd, args...) fake_eval(cmd, ## args, NULL)
#define foreach_44(word, wordlist, next) for (next = NULL, strcpy(word, wordlist); next == NULL; next = word)
static char *nvram_pf_safe_get(char *prefix, char *name) { (void)prefix; (void)name; return "10.6.0.1/32"; }
static int nvram_pf_get_int(char *prefix, char *name) { (void)prefix; (void)name; return 0; }
"""
        with tempfile.TemporaryDirectory() as td:
            c = os.path.join(td, "w.c"); x = os.path.join(td, "w")
            open(c, "w").write(stub + mf.group(0) + r"""
int main(void)
{
	int a, b;
	UP_RC = 0; a = _wg_tunnel_create("wgs1_", "wgs1", "/tmp/x.conf");
	UP_RC = 2; b = _wg_tunnel_create("wgs1_", "wgs1", "/tmp/x.conf");
	printf("%d %d %d", a, b, CALLS);
	return 0;
}
""")
            r = subprocess.run([cc, "-Wall", "-Werror", "-o", x, c], capture_output=True, text=True)
            out = subprocess.run([x], capture_output=True, text=True).stdout if r.returncode == 0 else r.stderr[-400:]
            check("wireguard.c: compiled with stubs, 0 when the interface came up and the error when it did not (4 commands each run)", out == "0 2 8", out)
    elif mf:
        print("note no C compiler on the host - _wg_tunnel_create is not compiled")
else:
    print("note no rc/wireguard.c in this tree")

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
