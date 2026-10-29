#!/usr/bin/env python3
"""VPN > Status, VPN Director and Tor on the Reaper kit (Reaper-native UI, VPN wave, 2026-10-23).

Reaper_VPNStatus.asp replaces Advanced_VPNStatus.asp (read-only, live), Reaper_VPNDirector.asp replaces
Advanced_VPNDirector.asp (vpndirector_rulelist), Reaper_Tor.asp replaces Advanced_TOR_Content.asp (Tor_* keys).

WHY. The stock status page EVALUATED two ajax replies as script (jQuery dataType:'script'), rendered status-file common
names and peer names as HTML, hid every stopped server and disabled client, read the WireGuard server state from the
page's editing buffer (wgs_enable) and wrote nvram from its Refresh button (reset_vpn_ip). The stock Director saved a
client's enable key at once from a rules page (httpApi.nvramSet + rc_service), never checked for duplicate rules, and let
httpd store a list longer than the 7999 bytes it can read back. The stock Tor page saved an EMPTY device list when the
user chose "only specified MACs" with none added - which rc reads as every LAN device - accepted port 0 / empty /
duplicate ports, and had no cap on a list that is not JFFS-whitelisted (silent 1 KB nvram wall).
The Reaper pages parse every reply, escape every value, post only the changed keys on Apply with the stock restart,
ask before anything that drops connections, and write nothing on load (the status page writes nothing at all).

WHAT IT DOES. Source checks on the three pages and (once wired) menu.js / reaper_inject.c; `node --check` on each page
script. Behaviour per scenario was run in jsdom when the pages were written (scen_Reaper_*.txt in the wave's scratch folder).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isdir(SRC):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = {"st": ("Reaper_VPNStatus.asp", "RVST_"), "dr": ("Reaper_VPNDirector.asp", "RVDR_"), "tor": ("Reaper_Tor.asp", "RTOR_")}
if not all(os.path.exists(os.path.join(www, p)) for p, _ in PAGES.values()):
    print("SKIP: Reaper_VPNStatus.asp / Reaper_VPNDirector.asp / Reaper_Tor.asp not found"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
def code_of(t):
    """the page without its HTML and JS comments (the comments cite the stock names they replace)"""
    return re.sub(r"/\*.*?\*/", "", re.sub(r"<!--.*?-->", "", t, flags=re.S), flags=re.S)

en = rd(os.path.join(www, "EN.dict"))
T = {k: rd(os.path.join(www, p)) for k, (p, _) in PAGES.items()}
JS = {k: t[t.rfind("<script>"):] for k, t in T.items()}
PLUMB = {"current_page", "next_page", "action_mode", "action_script", "action_wait"}
for k, (p, pfx) in PAGES.items():
    t, js, code = T[k], JS[k], code_of(T[k])
    check(p + ": ASCII only", not any(ord(c) > 127 for c in t))
    check(p + ": on the kit (plain rp.css link, rp.js, reaper-native meta) inside the crimson frame, SPDX header",
          '<link rel="stylesheet" href="/reaper/rp.css">' in t and '<script src="/reaper/rp.js"></script>' in t
          and '<meta name="reaper-native" content="1">' in t and 'rframe' in t and "SPDX-License-Identifier: GPL-2.0-only" in t)
    check(p + ": one closure, strict, no inline handlers (no page globals)",
          js.startswith("<script>\n(function(){\n'use strict';") and js.rstrip().endswith("})();\n</script>\n</body>\n</html>")
          and js.count("<script>") == 1 and not re.search(r"\son[a-z]+\s*=", t) and "var esc" not in js)
    toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
    miss = [x for x in toks if ("\n%s=" % x) not in en]
    check(p + ": every dict token exists (%d)" % len(toks), not miss, miss)
    own = sorted(int(x[len(pfx):]) for x in toks if x.startswith(pfx))
    check(p + ": own keys numbered 01..N with no gap", own == list(range(1, len(own) + 1)), own)
    check(p + ": tokens in the script only inside backticks", "<#" not in re.sub(r"`[^`]*`", "", js))
    check(p + ": every nvram value read through nvram_char_to_ascii (no nvram_get into a JS string)",
          "nvram_get(" not in code and t.count("nvram_char_to_ascii(") >= 5 and ("U = rp.dec" in t or "function U(s){ try { return decodeURIComponent(s); }" in t))
    check(p + ": no eval / Function / script-typed ajax, no immediate-save path (applyapp / nvramSet)",
          not re.search(r"\beval\s*\(|new Function|dataType", code) and "applyapp" not in code and "nvramSet" not in code)
    check(p + ": the ?tab= / mode gate reads get_operation_mode, router-mode hint present",
          "get_operation_mode()" in t and 'id="modehint"' in t)
    hid = re.findall(r'<input type="hidden" name="([A-Za-z0-9_]+)" value="([^"]*)"( disabled)?>', t)
    loose = [n for n, v, d in hid if n not in PLUMB and not d]
    check(p + ": every setting input starts disabled (only changed keys post)", not loose, loose)

S, D, R = T["st"], T["dr"], T["tor"]
# ---- Reaper_VPNStatus: read-only, live ----
check("Status: writes nothing - no form, no apply, no rp.post, no reset_vpn_ip", "<form" not in S and "rp.post(" not in S and "reset_vpn_ip" not in code_of(S) and 'action_mode' not in code_of(S))
check("Status: the stock endpoints are fetched and parsed, never evaluated",
      all(x in S for x in ("get('/ajax_vpn_status.asp'", "get('/ajax_ipsec.asp'", "get('/ajax_vpnserver_client_status.xml'",
                           "nvram_dump(\"wgs.log\",\"wgs.sh\")", "hook=get_wgsc_status()", "nvram_dump(\"wgc.log\",\"' + unit + '\")"))
      and "function parseKV(text)" in S and "function parseOvpn(text)" in S and "function parseWg(text)" in S and "function parseIpsec(text)" in S
      and "JSON.parse(s.slice(i + 1, j + 1))" in S and "ajax_openvpn_server" not in code_of(S))
check("Status: state keys polled through appGet nvram_char_to_ascii (JSON-safe), 10 s, paused while hidden",
      "'nvram_char_to_ascii(' + k + ',' + k + ')'" in S and "POLL_MS = 10000" in S and "document.hidden" in S and "visibilitychange" in S)
check("Status: WireGuard server state from wgs1_enable, not the editing buffer; PPTP/L2TP state from the legacy client's vpnc_state_t (vpnc<idx>_state_t is never written on this build)",
      'nvram_char_to_ascii("","wgs1_enable")' in S and 'nvram_char_to_ascii("","wgs_enable")' not in S
      and 'nvram_char_to_ascii("","vpnc_state_t")' in S and "c.idx + '_state_t'" not in S)
check("Status: the profile password never reaches the DOM; wg key lines skipped", "f[3] || '', active: f[5]" in S and "f[4]" not in S[S.find("var VPNC = []"):S.find("var LIVE")]
      and "if (/key/i.test(k)) return;" in S)
check("Status: every rendered value escaped (hx) and the tables built from hx cells", "function table(heads, rows)" in S and "'<td class=\"mono\">' + hx(c) + '</td>'" in S
      and "hx(desc)" in S and "hx(c.proto)" in S)
check("Status: every instance shown (2 servers, 5 + 5 clients) with a state pill; tabs servers / clients with ?tab= deep link",
      "OVPNS = 2, OVPNC = 5, WGC = 5" in S and "tab=(servers|clients)" in S and "function ovpnState(state, errno, pid)" in S)
check("Status: links to the server / client pages by tab", all(x in S for x in ("link('Reaper_VPNServer.asp', 'ovpn')", "link('Reaper_VPNServer.asp', 'wg')",
      "link('Reaper_VPNServer.asp', 'ipsec')", "link('Reaper_VPNServer.asp', 'pptp')", "link('Reaper_VPNClient.asp', 'ovpn')", "link('Reaper_VPNClient.asp', 'wg')", "link('Reaper_VPNClient.asp', 'pptp')")))

# ---- Reaper_VPNDirector ----
check("Director: posts vpndirector_rulelist only when edited, restart_vpnrouting0 wait 5 (stock script)",
      'name="vpndirector_rulelist" value="" disabled' in D and "if (EDITED) c.vpndirector_rulelist = ser(RULES);" in D
      and "rp.post(document.form, changed, 'restart_vpnrouting0', 5);" in D and "rp.post(" not in D[D.find("function boot()"):])
check("Director: stock record format kept, unedited rows written back byte for byte",
      "var f = [q('r_en').checked ? '1' : '0', val('r_desc'), val('r_local'), val('r_remote'), q('r_iface').value]" in D
      # review 2026-10-24 (Q-C1-7): the raw-preserving serialiser is the kit's one copy, bound by the page
      and "ser = rp.list.ser" in D
      and "ser: function(rows){ return rows.map(function(r){ return '<' + r.raw; }).join(''); }" in open(os.path.join(SRC, "www", "reaper", "rp.js"), encoding="utf-8").read())
check("Director: stock checks kept - description chars, IPv4 or CIDR, 199 rules, 7999 characters; duplicate refused (B-VPND-3)",
      "MAX_RULES = 199, MAX_BYTES = 7999" in D and "function descOk(s){ return !/[^\\x20-\\x7e]/.test(s) && !/[<>'%\"\\\\]/.test(s); }" in D
      and "function addrOk(s){ return s === '' || rp.v.ipv4(s) || rp.v.cidr4(s); }" in D and "if (dup(f, editIdx)) return edmsg(`<#JS_duplicate#>`" in D
      and "if (ser(list).length > MAX_BYTES) return edmsg(" in D and "RULES.length >= MAX_RULES" in D)
check("Director: a no-address rule asks (B-VPND-4); a rule to an off client asks at Apply (rule 14)",
      "(f[2] === '' || f[2] === '0.0.0.0') && (f[3] === '' || f[3] === '0.0.0.0') && f[0] === '1' && !confirm(" in D
      and "if (offs.length && !confirm(`<#RVDR_" in D and "function ifaceOff(t)" in D)
check("Director: client enable / edit not here (B's keys): read-only summary + link; untouched Apply says nothing changed",
      not re.search(r'name="(vpn_clientx_eas|wgc_enable|wgc_unit|vpn_client_unit)"', D) and "#Reaper_VPNClient.asp?tab=ovpn" in D
      and "if (!count(changed)){ msg(`<#RADM_63#>`); return; }" in D)
check("Director: Policy Routing linked as a different feature, stored order kept (display grouped only)",
      "#Reaper_VPNRouting.asp" in D and "`<#RVR_00#>`" in D or "<#RVR_00#>" in D)
check("Director: stored order kept; the table only groups by interface", "order.sort(function(a, b){ var d = groupKey(" in D and "RULES.sort" not in D)
check("Director: malformed records (not five fields) shown dimmed, deletable, never re-written", "ok = f.length === 5" in D and "`<#RVDR_" in D and "' class=\"dim\"'" in D)

# ---- Reaper_Tor ----
check("Tor: posts only the changed Tor_* keys, restart_tor wait 5",
      all('name="%s" value="" disabled' % k in R for k in ("Tor_enable", "Tor_socksport", "Tor_transport", "Tor_dnsport", "Tor_redir_list"))
      and "rp.post(document.form, changed, 'restart_tor', 5);" in R and "rp.post(" not in R[R.find("function boot()"):]
      and "function keep(id, nv, now){ return snap(id) === INIT[id] ? nv : now; }" in R)
check("Tor: ports 1-65535, distinct (B-TOR-3); device scope with an empty list refused (B-TOR-2)",
      "if (!rp.v.port(v)) return bad(ports[i][1]" in R and "if (seen[v]) return bad(ports[i][1]" in R
      and "if (q('s_scope').value === 'list' && !LIST.length) return bad('s_scope'" in R)
check("Tor: the 1 KB nvram wall enforced on Tor_redir_list (not JFFS-whitelisted, B-TOR-4)",
      "var MAXBYTES = 1006 - 'Tor_redir_list='.length;" in R and "if (ser(list).length > MAXBYTES) return edmsg(" in R
      and "c.Tor_redir_list.length > MAXBYTES" in R)
check("Tor: whole-LAN scope = empty list, as rc reads it; the list re-serialised only once edited",
      "if (q('s_scope').value === 'lan') c.Tor_redir_list = '';" in R and "LIST_EDITED ? ser(LIST) : NV.Tor_redir_list" in R)
check("Tor: turning on / widening to the whole LAN asks first (rule 14)",
      "var turningOn = NV.Tor_enable !== '1', widening = changed.Tor_redir_list === '' && NV.Tor_redir_list !== '';" in R and "if (!confirm(who + ' ' + `<#RTOR_" in R)
check("Tor: MAC entries validated (unicast, duplicate), device names from the client list, daemon state parsed from appGet raw text",
      "macOk = rp.v.macUnicast" in R and "return edmsg(`<#JS_duplicate#>`" in R and "ReaperNames.refresh(CUSTOM_CL" in R and "hook=sysinfo(\"pid.Tor\")" in R)

# ---- wiring (the engineer makes these unconditional after wiring) ----
mj = rd(os.path.join(www, "reaper", "menu.js"))
inj_p = os.path.join(SRC, "httpd", "reaper_inject.c")
inj = rd(inj_p) if os.path.exists(inj_p) else ""
if True:  # wired 2026-10-24 (VPN wave): menu.js checks are unconditional
    check("menu: Status / Director / Tor tabs open the Reaper pages; the three stock pages are gone from the rail",
          "T('Reaper_VPNStatus.asp'" in mj and "T('Reaper_VPNDirector.asp'" in mj and "T('Reaper_Tor.asp'" in mj
          and not any(p in mj for p in ("Advanced_VPNStatus.asp", "Advanced_VPNDirector.asp", "Advanced_TOR_Content.asp")))
if True:  # wired 2026-10-24 (VPN wave): reaper_inject.c checks are unconditional
    check("httpd: the three pages native; the stock pages redirect",
          all('"%s",' % p in inj for p in ("Reaper_VPNStatus.asp", "Reaper_VPNDirector.asp", "Reaper_Tor.asp"))
          and all('{ "%s", "%s", ' % sr in inj for sr in (("advanced_vpnstatus.asp", "Reaper_VPNStatus.asp"),
              ("advanced_vpndirector.asp", "Reaper_VPNDirector.asp"), ("advanced_tor_content.asp", "Reaper_Tor.asp"))))

# ---- parity files ----
for name, rep in (("Advanced_VPNStatus", "Reaper_VPNStatus.asp"), ("Advanced_VPNDirector", "Reaper_VPNDirector.asp"), ("Advanced_TOR_Content", "Reaper_Tor.asp")):
    f = os.path.join(HERE, "ui_parity", name + ".json")
    ok = os.path.exists(f) and json.load(open(f, encoding="utf-8")).get("replacement") == rep
    check("parity file %s.json -> %s" % (name, rep), ok)
pf = os.path.join(HERE, "ui_parity", "Advanced_TOR_Content.json")
if os.path.exists(pf):
    cov = [k for k, v in json.load(open(pf, encoding="utf-8"))["fields"].items() if v == "covered"]
    check("parity: every covered Tor key is a hidden input of Reaper_Tor.asp", cov and all('name="%s"' % k in R for k in cov), cov)

node = shutil.which("node")
if node:
    for k, (p, _) in PAGES.items():
        js = JS[k]; body = js[len("<script>"):js.rfind("</script>")]
        body = re.sub(r"<%.*?%>", "", body); body = re.sub(r"`[^`]*`", "''", body)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(body); jp = f.name
        r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
        check(p + ": page script parses (node --check)", r.returncode == 0, r.stderr[-300:])
else:
    print("note: node not found - syntax check skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
