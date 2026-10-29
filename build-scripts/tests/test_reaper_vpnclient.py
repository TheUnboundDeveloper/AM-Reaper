#!/usr/bin/env python3
"""VPN > VPN Client on the Reaper kit (Reaper-native UI, VPN wave, 2026-10-24): Reaper_VPNClient.asp.

Replaces Advanced_OpenVPNClient_Content.asp (tab ovpn, OpenVPN clients 1-5), Advanced_WireguardClient_Content.asp (tab wg,
WireGuard clients 1-5) and Advanced_VPNClient_Content.asp (tab pptp, the PPTP / L2TP client and its saved servers).

WHY. The stock OpenVPN client page EVALUATED ajax_openvpn_server.asp as script (values pass ' and \\), carried two dead rows
nothing writes to the OpenVPN config, accepted an empty server address, and posted ";;restart_dnsmasq". The stock WireGuard
page's Apply ran restart_wgc with no unit, which restarts all five clients, let a disabled client be saved with garbage that
WAN-up would start, truncated a dual-stack address pair (maxlength 39), routed DNS host names (never routed), and had no cap
on wgcN_aips, which is not JFFS-whitelisted (silent 1 KB nvram wall). The Fusion-era PPTP/L2TP page offered "No encryption",
MPPE-40 and Auto, showed every profile password in a text field, blanked the connection to deactivate it, could mis-align
vpnc_pptp_options_x_list, and re-serialised rows in a shape rc/format.c rewrites at every boot. The Reaper page reads every
value through nvram_char_to_ascii, parses every reply, posts only the changed keys of the selected instance with the
narrowest rc restart, asks before anything that drops a tunnel, masks every secret, and writes nothing on load.

WHAT IT DOES. Source checks on the page and (once wired) menu.js / reaper_inject.c; the three parity files; `node --check`
on the page script. Behaviour per scenario was run in jsdom when the page was written (scen_Reaper_VPNClient.txt in the
wave's scratch folder: 74 scenarios, 0 script errors, 0 missing tokens, 0 expectation failures).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isdir(SRC):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE, PFX = "Reaper_VPNClient.asp", "RVCL_"
if not os.path.exists(os.path.join(www, PAGE)):
    print("SKIP: %s not found" % PAGE); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
def code_of(t):
    """the page without its HTML and JS comments (the comments cite the stock names they replace)"""
    return re.sub(r"/\*.*?\*/", "", re.sub(r"<!--.*?-->", "", t, flags=re.S), flags=re.S)

en = rd(os.path.join(www, "EN.dict"))
T = rd(os.path.join(www, PAGE)); JS = T[T.rfind("<script>"):]; C = code_of(T)
PLUMB = {"current_page", "next_page", "action_mode", "action_script", "action_wait"}

# ---- kit, strings, read path ----
check("ASCII only", not any(ord(c) > 127 for c in T))
check("on the kit (plain rp.css link, rp.js, reaper-native meta) inside the crimson frame, SPDX header",
      '<link rel="stylesheet" href="/reaper/rp.css">' in T and '<script src="/reaper/rp.js"></script>' in T
      and '<meta name="reaper-native" content="1">' in T and 'rframe' in T and "SPDX-License-Identifier: GPL-2.0-only" in T)
check("one closure, strict, no inline handlers (no page globals)",
      JS.startswith("<script>\n(function(){\n'use strict';") and JS.rstrip().endswith("})();\n</script>\n</body>\n</html>")
      and JS.count("<script>") == 1 and not re.search(r"\son[a-z]+\s*=", T) and "var esc" not in JS)
toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", T)))
miss = [x for x in toks if ("\n%s=" % x) not in en]
check("every dict token exists (%d)" % len(toks), not miss, miss)
own = sorted(int(x[len(PFX):]) for x in toks if x.startswith(PFX))
check("own keys numbered 01..N with no gap", own == list(range(1, len(own) + 1)) and len(own) >= 100, own[-3:])
check("tokens in the script only inside backticks", "<#" not in re.sub(r"`[^`]*`", "", JS))
check("every nvram value read through nvram_char_to_ascii (no nvram_get into a JS string); custom config via nvram_clean_get into the textarea",
      "nvram_get(" not in C and T.count("nvram_char_to_ascii(") >= 200 and ("U = rp.dec" in T or "function U(s){ try { return decodeURIComponent(s); }" in T)
      and '<textarea id="ta_ov_custom" rows="6" maxlength="4095" spellcheck="false"><% nvram_clean_get("vpn_client_custom3"); %></textarea>' in T)
check("no eval / Function / script-typed ajax, no immediate-save path (applyapp / nvramSet)",
      not re.search(r"\beval\s*\(|new Function|dataType", C) and "applyapp" not in C and "nvramSet" not in C)
# review 2026-10-24 (Q-C1-5 / Q-C1-8): the tab strip's storage and its .win.gone rule are the kit's (rp.js / rp.css)
RPCSS = open(os.path.join(SRC, "www", "reaper", "rp.css"), encoding="utf-8").read()
check("?tab= deep link (ovpn | wg | pptp), remembered per session", "tab=(ovpn|wg|pptp)" in T and "rp.tabShow(TABS, t, 'rvcl_tab')" in T)
check("tabs gated by the three stock menu flags; a tab whose flag is off is hidden, a note when none is built",
      "var TAB_ON = { ovpn: sup('openvpnd'), wg: sup('wireguard'), pptp: sup('vpnc') };" in T and ".win.gone{display:none}" in RPCSS and "note('notabs'" in T)

# ---- forms: only changed keys post, unit first ----
mf = T[T.find('<form method="post" name="form"'):]; mf = mf[:mf.find("</form>")]
hid = re.findall(r'<input type="hidden" name="([A-Za-z0-9_]+)" value="([^"]*)"( disabled)?>', mf)
loose = [n for n, v, d in hid if n not in PLUMB and not d]
check("every setting input starts disabled (only changed keys post)", hid and not loose, loose)
order = [n for n, v, d in hid]
ovk = [i for i, n in enumerate(order) if (n.startswith("vpn_client_") and n != "vpn_client_unit") or n.startswith("vpn_crt_client_")]
wgk = [i for i, n in enumerate(order) if n.startswith("wgc_") and n != "wgc_unit"]
check("vpn_client_unit precedes the vpn_client_* / vpn_crt_client_* inputs and wgc_unit the wgc_* inputs (httpd web.c:4396 reads the unit ahead of the fields)",
      order.index("vpn_client_unit") < min(ovk) and order.index("wgc_unit") < min(wgk) and max(ovk) < order.index("wgc_unit"))
check("posts only the diff, nothing on load; untouched Apply says nothing changed",
      "var c = collect(), changed = diff(c)" in T and "if (!n){ msg(`<#RADM_63#>`); return; }" in T
      and "function keep(id, nv, now){ return snap(id) === INIT[id] ? nv : now; }" in T
      and "rp.post(document.form, changed, S.join(';'), wait);" in T)   # the kit reloads after wait + 5 s (Q-C1-12)
check("the selected instance's unit is added to the post (httpd maps the unindexed names: web.c:4675, :4729, :4810)",
      "changed.vpn_client_unit = String(OU);" in T and "changed.wgc_unit = String(WU);" in T)
check("OpenVPN instance switch = the stock apply.cgi change_vpn_client_unit round trip; WireGuard switch page-side",
      '<input type="hidden" name="action_mode" value="change_vpn_client_unit">' in T and "document.chgform.submit();" in T and "function wgSwitch(u){" in T and "wgLoad(u); syncAll();" in T)

# ---- restarts (rc citations in the page) ----
check("OpenVPN: restart/stop_vpnclientN + start_vpnroutingN + restart_dnsmasq for adns (rc/services.c:22251-22310), one separator",
      "S.push('restart_vpnclient' + OU)" in T and "S.push('stop_vpnclient' + OU)" in T and "S.push('start_vpnrouting' + OU)" in T
      and "if (has('vpn_client_adns') && onNow) S.push('restart_dnsmasq');" in T and ";;" not in C)
check("WireGuard: restart_wgc N / stop_wgc N for the edited client only (never the unit-less restart_wgc = all five), start_vpnrouting0 for enable / killswitch",
      "S.push('restart_wgc ' + WU)" in T and "S.push('stop_wgc ' + WU)" in T and "if (has('wgc_enable', 'wgc_enforce')) S.push('start_vpnrouting0');" in T
      and "'restart_wgc'" not in C and "'restart_wgc;" not in C)
check("PPTP / L2TP: restart_vpncall (the only dispatch that reaches legacy_start_vpnc); the saved-servers lists alone save with saveNvram",
      "S.push('restart_vpncall')" in T and "if (!S.length) S.push('saveNvram');" in T)
check("Reset = the stock Default buttons (stop + clearovpnclient / clearwgclient) after a confirm",
      "rp.post(document.form, {}, 'stop_vpnclient' + OU + ';clearovpnclient ' + OU, 15);" in T and "rp.post(document.form, {}, 'stop_wgc ' + WU + ';clearwgclient ' + WU, 15);" in T)

# ---- dangerous changes ask first (rule 14) ----
check("a tunnel restart / stop, redirect-all and killswitch ask first; cancel posts nothing",
      "if (ask.length && !confirm(ask.join('\\n') + '\\n\\n' + `<#RVCL_" in T and T.count("ask.push(") == 9 and T.count("ask.push(`<#RVCL_") == 8
      and "if (changed.vpn_client_rgw === '1') ask.push(" in T and "if (changed.vpn_client_enforce === '1') ask.push(" in T and "if (changed.wgc_enforce === '1') ask.push(" in T)
check("imports, resets and an instance switch with unsaved changes ask first", T.count("if (!confirm(`<#RVCL_") >= 4 and T.count("tabDirty(") >= 2)

# ---- secrets (rule 12) ----
for i in ("i_ov_pass", "i_pp_pass", "i_wg_priv", "i_wg_psk", "a_pl_pass"):
    check("secret field %s is type=password with a reveal control" % i, re.search(r'<input type="password"[^>]*id="%s"' % i, T) and ('data-for="%s"' % i) in T)
check("OpenVPN private keys masked until shown; keys come from ajax_openvpn_server.asp parsed line by line (not evaluated)",
      '<textarea id="k_static" class="masked"' in T and '<textarea id="k_key" class="masked"' in T and "function crtParse(text)" in T
      and "x.open('GET', '/ajax_openvpn_server.asp?_=' + Date.now(), true)" in T and "/^vpn_crt_client([1-5])_(static|ca|crt|key|crl|extra)=\\['(.*)'\\];\\s*$/" in T)
check("no secret in a URL: the appGet polls name state keys only", not re.search(r"appGet\.cgi[^\n]*(passw|_password|priv|psk)", C))
# review 2026-10-24 (S-C1-1): no secret in the page source - presence flags, empty fields, masked profiles
check("no password, private key or PSK is read into the page: presence flags for the OpenVPN passwords, the WireGuard keys and PSKs and the PPTP password; the saved profiles come masked",
      not re.search(r'nvram_char_to_ascii\("","(vpn_client[1-5]_password|wgc[1-5]_(priv|psk)|vpnc_pppoe_passwd|vpnc_clientlist)"\)', T)
      and all(('nvram_match("vpn_client%d_password", "", "0")' % u) in T and ('nvram_match("wgc%d_priv", "", "0")' % u) in T and ('nvram_match("wgc%d_psk", "", "0")' % u) in T for u in range(1, 6))
      and 'nvram_match("vpnc_pppoe_passwd", "", "0")' in T and 'reaper_masked_list("vpnc_clientlist")' in T
      and "q('i_ov_pass').placeholder = o.pw_set ? '********' : ''" in T and "if (!c.vpn_client_password && !OV[OU].pw_set)" in T
      and "q('i_wg_priv').placeholder = w.priv_set ? '********' : ''" in T and "if (pon && !c.vpnc_pppoe_passwd && !G.vpnc_pppoe_passwd_set)" in T)

# ---- validation the stock pages had, or lacked ----
check("OpenVPN: server required when enabled (B-OVPNC-4), port / verb / reneg / retry ranges, cipher list, x509 name safe (libovpn/openvpn_setup.c:180)",
      "if ((on || c.vpn_client_addr) && !isHost(c.vpn_client_addr)) return bad('i_ov_addr'" in T and "if (!rp.v.port(c.vpn_client_port)) return bad('i_ov_port'" in T
      and "rp.v.int(c.vpn_client_verb, 0, 6)" in T and "rp.v.int(c.vpn_client_reneg, -1, 32767)" in T and "rp.v.int(c.vpn_client_connretry, 0, 999)" in T
      and "/^[A-Za-z0-9:_-]+$/.test(c.vpn_client_ncp_ciphers)" in T and "/^[A-Za-z0-9 ._,=:@*\\/+-]+$/.test(c.vpn_client_cn)" in T and "function pemOk(s)" in T)
check("OpenVPN: the dead Local/remote endpoint and Tunnel address rows are gone (B-OVPNC-2); TAP cannot use policy mode (stock update_rgw_options)",
      not re.search(r'name="vpn_client_(local|remote|nm)"', T) and "if (tap && rgw === '2') rgw = '1';" in T)
check("WireGuard: 44-char keys, address / allowed-IP prefixes, DNS addresses only (B-WGC-3), MTU 576-1500, port, keepalive; a disabled client still validated (B-WGC-4)",
      "function isWgKey(s){ return /^[A-Za-z0-9+\\/]{43}=$/.test(s); }" in T and "function isCidr(s)" in T
      and "if (!rp.v.ipv4(dl[i]) && !rp.v.ipv6(dl[i])) return bad('i_wg_dns'" in T and "rp.v.int(c.wgc_mtu, 576, 1500)" in T
      and "if ((won || c.wgc_ep_port) && !rp.v.port(c.wgc_ep_port))" in T and "if (c.wgc_priv ? !isWgKey(c.wgc_priv) : (won && !WG[WU].priv_set))" in T)
check("WireGuard: nvram sizes on the inputs (B-WGC-2) and the 1 KB wall on wgc_aips, shown and enforced (B-WGC-5)",
      'id="i_wg_addr" maxlength="63"' in T and 'id="i_wg_dns" maxlength="127"' in T and "var WG_AIPS_MAX = 1006 - 'wgc1_aips='.length;" in T
      and "if (c.wgc_aips.length > WG_AIPS_MAX) return bad('ta_wg_aips'" in T and 'id="ta_wg_aips" rows="3" maxlength="996"' in T and 'id="wg_aipsbudget"' in T)

# ---- PPTP / L2TP repair ----
enc = re.search(r'<select id="s_pp_enc">(.*?)</select>', T, re.S)
check("PPTP: the encryption select offers MPPE 128-bit only; no -mppc / +mppe-40 / +mppe-56 / auto option in the markup (B-VPNC-2)",
      enc and enc.group(1).count("<option") == 1 and 'value="+mppe-128"' in enc.group(1) and not re.search(r'value="(-mppc|\+mppe-40|\+mppe-56|auto)"', T))
check("PPTP: any new save of a PPTP connection writes +mppe-128; a saved weaker value is shown locked and marked until re-saved",
      "if (proto === 'pptp' && on && edited && enc !== '+mppe-128') enc = '+mppe-128';" in T and "note('pp_encnote', (pptp && q('s_pp_enc').value !== '+mppe-128')" in T
      and "s.insertAdjacentHTML('beforeend', '<option value=\"' + hx(cur) + '\">'" in T)
check("PPTP: saved rows get +mppe-128 (PPTP) / auto (L2TP), one option token per row with the leading < (shared/vpn_utils.c:210, B-VPNC-5)",
      "PL_OPTS.push(r.f[1] === 'PPTP' ? '+mppe-128' : 'auto')" in T and "PL_OPTS[PL_EDIT] = r.f[1] === 'PPTP' ? '+mppe-128' : 'auto';" in T
      and "return o.length ? '<' + o.join('<') : '';" in T and "while (PL_OPTS.length < PL.length) PL_OPTS.push('auto');" in T)
check("PPTP: untouched rows written back byte for byte, new rows 7 fields with the stock index allocator (shared/vpn_utils.c:240), 10 rows (B-VPNC-6)",
      "function plSer(){ return PL.map(function(r){ return r.raw !== undefined ? r.raw : r.f.join('>'); }).join('<'); }" in T
      and "r.f[5] = '0'; r.f[6] = plNextIdx(); PL.push(r);" in T and "for (var i = 5; i < 21; i++) if (!used[String(i)]) return String(i);" in T and "PL_MAX = 10" in T)
check("PPTP: the lists are re-serialised only once edited (no phantom change)",
      "c.vpnc_clientlist = PL_EDITED ? plSer() : NV.vpnc_clientlist;" in T and "c.vpnc_pptp_options_x_list = PL_EDITED ? plOptsSer() : NV.vpnc_pptp_options_x_list;" in T)
check("PPTP: stock row checks kept (description characters, host, no angle brackets, duplicate, blank)",
      "if (/[*+|:?<>,.\\/;\\[\\]\\\\=\"]/.test(r.f[0])) return" in T and "if (!isHost(r.f[2])) return" in T and "return `<#JS_duplicate#>`;" in T and "function noAngle(s)" in T)
check("PPTP: turning the client off keeps its settings (vpnc_proto=disable only, B-VPNC-4); enabling sets vpnc_auto_conn=1 (rc/wan.c:4538)",
      "c.vpnc_proto = keep('t_pp_on', NV.vpnc_proto, on ? proto : 'disable');" in T
      and "if (on && NV.vpnc_auto_conn !== '1' && c.vpnc_proto !== NV.vpnc_proto) c.vpnc_auto_conn = '1'; else c.vpnc_auto_conn = NV.vpnc_auto_conn;" in T)
check("PPTP: state from the legacy engine's unprefixed vpnc_state_t / vpnc_sbstate_t (rc/vpnc_legacy.c:338-345), never vpnc<idx>_state_t",
      'nvram_char_to_ascii("","vpnc_state_t")' in T and 'nvram_char_to_ascii("","vpnc_sbstate_t")' in T and "'vpnc' + " not in T)
check("PPTP: the weak-protocol note is on the tab", "<#RVCL_" in T[T.find('<div class="hint warn"'):T.find('<div class="hint warn"') + 60])

# ---- removed machinery stays removed ----
check("no Fusion / Instant Guard / provider / dev-policy machinery (owner decision 2; vpnc_dev_policy_list has no reader on this build)",
      not re.search(r"vpnc_dev_policy_list|Instant_Guard|ipsec_profile_client|/VPN/vpnc_|Advanced_VPNClient_Content|nordvpn|hmavpn|vpnc_type", C))
check("Director rows read-only (agent C's key never posted); links to Director, Policy Routing, Status and the static-route editor",
      "function dirRows(body, mine)" in T and 'name="vpndirector_rulelist"' not in T and "#Reaper_VPNDirector.asp" in T
      and "#Reaper_VPNRouting.asp" in T and "#Reaper_VPNStatus.asp" in T and "#Reaper_Routes.asp?tab=edit" in T)
check("live state parsed, never evaluated: ajax_vpn_status.asp lines + appGet JSON, first poll at load then 10 s (review 2026-10-24 Q-C1-1), none while hidden",
      "function liveParse(text)" in T and "JSON.parse(x.responseText)" in T and T.count("POLL_T = setTimeout(poll, 10000);") == 2 and "\n  poll();" in T
      and "if (document.hidden){ POLL_T = setTimeout(poll, 10000); return; }" in T and "setTimeout(poll, 5000)" not in T)

# ---- wiring (the engineer makes these unconditional after wiring) ----
mj = rd(os.path.join(www, "reaper", "menu.js"))
inj_p = os.path.join(SRC, "httpd", "reaper_inject.c")
inj = rd(inj_p) if os.path.exists(inj_p) else ""
if True:  # wired 2026-10-24 (VPN wave): menu.js checks are unconditional
    check("menu: one VPN Client tab opens the Reaper page; the three stock client pages are gone from the rail",
          "T('Reaper_VPNClient.asp'" in mj and not any(p in mj for p in ("Advanced_OpenVPNClient_Content.asp", "Advanced_WireguardClient_Content.asp", "Advanced_VPNClient_Content.asp")))
if True:  # wired 2026-10-24 (VPN wave): reaper_inject.c checks are unconditional
    check("httpd: the page native; the three stock pages redirect to their tab",
          ('"%s",' % PAGE) in inj and all('{ "%s", "%s", ' % sr in inj for sr in (("advanced_openvpnclient_content.asp", "Reaper_VPNClient.asp?tab=ovpn"),
              ("advanced_wireguardclient_content.asp", "Reaper_VPNClient.asp?tab=wg"), ("advanced_vpnclient_content.asp", "Reaper_VPNClient.asp?tab=pptp"))))

# ---- parity files ----
for name in ("Advanced_OpenVPNClient_Content", "Advanced_WireguardClient_Content", "Advanced_VPNClient_Content"):
    f = os.path.join(HERE, "ui_parity", name + ".json")
    d = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    check("parity file %s.json -> %s" % (name, PAGE), d.get("replacement") == PAGE and d.get("action_script", "") in T)
    cov = [k for k, v in d.get("fields", {}).items() if v == "covered"]
    check("parity: every covered %s key is literal in the page (%d)" % (name, len(cov)), cov and all(k in T for k in cov), [k for k in cov if k not in T])

node = shutil.which("node")
if node:
    body = JS[len("<script>"):JS.rfind("</script>")]
    body = re.sub(r"<%.*?%>", "", body); body = re.sub(r"`[^`]*`", "''", body)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(body); jp = f.name
    r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
    check("page script parses (node --check)", r.returncode == 0, r.stderr[-300:])
else:
    print("note: node not found - syntax check skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
