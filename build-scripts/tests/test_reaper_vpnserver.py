#!/usr/bin/env python3
"""VPN > VPN Server on the Reaper kit (Reaper-native UI, VPN wave, 2026-10-24): Reaper_VPNServer.asp, tabs ovpn / wg / ipsec / pptp.

Replaces Advanced_VPN_OpenVPN.asp (two OpenVPN server instances), Advanced_WireguardServer_Content.asp, Advanced_VPN_IPSec.asp,
Advanced_VPN_PPTP.asp and the VPNS_V2 app scripts hosted by Advanced_VPNServer_Content.asp (owner decision: the app, the host
page and Instant Guard stop shipping).

WHY. The stock pages re-read user tables from innerHTML, posted the whole IPsec profile strings from page-load state on every
Apply, let a 128-row OpenVPN client-option list go into a nvram key that is not JFFS-whitelisted (silent 1 KB wall), let two
OpenVPN instances share a port, never validated the endpoint addresses or the cipher list, deleted a WireGuard peer by
blanking its public key in the same post as the live update (the peer stayed until the next restart) and kept a disabled
slot's key pair for the next owner, auto-enabled the WireGuard server on the first peer, evaluated ajax replies as script, and
offered PPTP with MS-CHAPv1, MPPE-40 and no encryption (owner: PPTP stays, repaired to MS-CHAPv2 + MPPE-128 only).
The Reaper page posts only the changed keys with the narrowest restart rc needs, asks before anything that drops clients,
keeps secrets in password fields, byte-caps the lists that are not whitelisted, and writes nothing on load (the one non-Apply
write is the stock instance / peer cursor, on the user's click, as stock).

WHAT IT DOES. Source checks on the page and (once wired) menu.js / reaper_inject.c, the five parity files, `node --check`
on the page script. Behaviour per scenario was run in jsdom when the page was written (scen_Reaper_VPNServer.txt in the wave's
scratch folder: 98 scenarios, 0 script errors, 0 missing tokens, 0 expectation failures).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isdir(SRC):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE, PFX = "Reaper_VPNServer.asp", "RVSV_"
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

# ---- the kit contract every Reaper page keeps ----
check("ASCII only", not any(ord(c) > 127 for c in T))
check("on the kit (plain rp.css link, rp.js, reaper-native meta) inside the crimson frame, SPDX header",
      '<link rel="stylesheet" href="/reaper/rp.css">' in T and '<script src="/reaper/rp.js"></script>' in T
      and '<meta name="reaper-native" content="1">' in T and 'rframe' in T and "SPDX-License-Identifier: GPL-2.0-only" in T)
check("one closure, strict, no inline handlers, no page globals (var esc)",
      JS.startswith("<script>\n(function(){\n'use strict';") and JS.rstrip().endswith("})();\n</script>\n</body>\n</html>")
      and JS.count("<script>") == 1 and not re.search(r"\son[a-z]+\s*=", T) and "var esc" not in JS)
toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", T)))
miss = [x for x in toks if ("\n%s=" % x) not in en]
check("every dict token exists (%d)" % len(toks), not miss, miss)
own = sorted(int(x[len(PFX):]) for x in toks if x.startswith(PFX))
check("own keys numbered 01..N with no gap (%d)" % len(own), own == list(range(1, len(own) + 1)), own)
check("tokens in the script only inside backticks", "<#" not in re.sub(r"`[^`]*`", "", JS))
check("every nvram value read through nvram_char_to_ascii + decodeURIComponent (no nvram_get into a JS string; the custom config through httpd's own escaping)",
      'nvram_get("' not in C and T.count("nvram_char_to_ascii(") >= 150 and ("U = rp.dec" in T or "function U(s){ try { return decodeURIComponent(s); }" in T)
      and '<textarea id="o_custom" maxlength="4095" spellcheck="false"><% nvram_clean_get("vpn_server_custom3"); %></textarea>' in T)
check("no eval / Function / script-typed ajax, no immediate-save path (applyapp / nvramSet), no raw server dump in the page",
      not re.search(r"\beval\s*\(|new Function|dataType", C) and "applyapp" not in C and "nvramSet" not in C and "<% nvram_dump" not in T)
check("deep link ?tab=ovpn|wg|ipsec|pptp, router-mode gate (get_operation_mode, modehint)",
      "tab=(ovpn|wg|ipsec|pptp)" in T and "get_operation_mode()" in T and 'id="modehint"' in T and "if (!ROUTING){ show('modehint', true); q('applybtn').disabled = true;" in T)
hid = re.findall(r'<input type="hidden" name="([A-Za-z0-9_]+)" value="([^"]*)"( disabled)?>', T)
loose = [n for n, v, d in hid if n not in PLUMB and not d]
check("every setting input starts disabled (only changed keys post) (%d inputs)" % len(hid), hid and not loose, loose)
check("posts only the diff, nothing on load; an untouched control posts nvram's own value back",
      "var c = collect(), changed = diff(c)" in T and "rp.post(document.form, changed, S.join(';'), wait);" in T
      and "function keep(id, nv, now){ return touched(id) ? now : nv; }" in T and "if (!n){ msg(`<#RADM_63#>`); return; }" in T)
check("every dangerous change asks first and a declined confirm posts nothing",
      "for (k = 0; k < asks.length; k++) if (!confirm(asks[k])) return;" in T and T.count("asks.push(") >= 8
      and "if (!confirm(`<#RVSV_" in T and "parseInt(q('chgcount').textContent, 10) > 0 && !confirm(`<#RVSV_" in T)
check("secrets only in password fields with a reveal, never in a URL or the applying overlay",
      all('type="password"' in m for m in re.findall(r'<input [^>]*id="(?:a_opass|a_ipass|a_ppass|s_psk|w_priv)"[^>]*>', T)) and T.count('type="password"') >= 5
      and "rp.applying(`<#Reaper_c_applying#>`, text)" in T and not re.search(r"appGet\.cgi\?hook=[^'\"]*(priv|psk|pass)", C))
# review 2026-10-24 (S-C1-1): the user lists and the IPsec profile come masked from httpd, the WireGuard private key is a
# presence flag, an untouched PSK posts as the mask (httpd keeps the stored key for it)
check("no secret in the page source: masked lists, presence flag for the WireGuard key, the PSK field empty and posted as the mask when untouched",
      all(('reaper_masked_list("%s")' % k) in T for k in ("vpn_serverx_clientlist", "pptpd_clientlist", "ipsec_profile_1", "ipsec_client_list_1", "ipsec_client_list_2"))
      and not re.search(r'nvram_char_to_ascii\("","(wgs1_priv|ipsec_profile_1|ipsec_client_list_[12]|pptpd_clientlist|vpn_serverx_clientlist)"\)', T)
      and 'nvram_match("wgs1_priv", "", "0")' in T and "function pskPost(){ return q('s_psk').value || ((IP.p1 !== '' && p1Field(7)) ? '********' : ''); }" in T
      and "NV.wgs_priv = WG.priv_set ? '********' : '';" in T and "t_wgshowpriv" not in T and "var psk = pskPost(), vs = val('s_vsub');" in T)

# ---- OpenVPN (libovpn/openvpn_config.c get_ovpn_sconf reads vpn_serverN_*; httpd maps the unindexed names onto vpn_server_unit) ----
names = [n for n, v, d in hid]
check("OpenVPN: vpn_server_unit is the first hidden input of its group and is posted with every OpenVPN change (web.c:4398 unit-first rule)",
      names.index("vpn_server_unit") < names.index("vpn_serverx_start") < names.index("vpn_server_if") and "changed.vpn_server_unit = CUR;" in T)
check("OpenVPN: restarts per instance - restart_vpnserverN / stop_vpnserverN (services.c:22257), restart_chpass for the user list (22213), restart_dnsmasq for pdns (openvpn_setup.c:94), reset = stop + clearovpnserver (22338)",
      "S.push('restart_vpnserver' + CUR)" in T and "S.push('stop_vpnserver' + CUR)" in T and "S.push('restart_chpass')" in T
      and "if ((oOn || wasOn) && changed.vpn_server_pdns !== undefined) S.push('restart_dnsmasq');" in T and "'clearovpnserver ' + CUR" in T
      and "restart_openvpnd" not in C)
check("OpenVPN: the enable switch edits vpn_serverx_start for the cursor instance only", "function buildStart(on)" in T and "function startHas(list, u)" in T)
check("OpenVPN: key files and the custom config posted unindexed (never vpn_crt_server1_* / vpn_server1_custom3 into nvram)",
      'name="vpn_crt_server_ca"' in T and 'name="vpn_server_custom3"' in T and not re.search(r'name="vpn_(crt_)?server[12]_', T))
check("OpenVPN: certificate dump read with a regex, never evaluated (B-OVPN-10); renew blanks the files after a confirm",
      "/vpn_crt_server(\\d)_(ca|crt|key|dh|crl|static|extra)=\\['([\\s\\S]*?)'\\];/g" in T
      and "if (ORENEW) ['ca', 'crt', 'key', 'dh', 'crl', 'extra'].forEach(function(n){ c['vpn_crt_server_' + n] = ''; });" in T)
check("OpenVPN: lists serialised from the model (B-OVPN-2); CN without < > (B-OVPN-5); subnet / mask of every row checked (B-OVPN-6)",
      "function serUsers(list)" in T and "function serCcd(list)" in T and "if (/[<>]/.test(r.cn) || r.cn.length > 64)" in T
      and "if (!r.cn || !r.sub || !r.mask) return `<#JS_fieldblank#>`;" in T)
check("OpenVPN: vpn_serverN_ccd_val byte-capped (not JFFS-whitelisted, B-OVPN-1); the whitelisted user list keeps the httpd 2048 cap",
      "CCD_BYTES = 1006 - 'vpn_server1_ccd_val='.length" in T and "serCcd(CCD.concat([r])).length > CCD_BYTES" in T and "serUsers(OUSERS.concat([r])).length > 2048" in T)
check("OpenVPN: port + protocol clash with the other enabled instance refused (B-OVPN-7); real subnet overlap vs LAN, the other instance and WireGuard (B-OVPN-8)",
      "c.vpn_server_port === OV[oth].port && c.vpn_server_proto === OV[oth].proto" in T and "overlap(sn, nm, F.lan_ipaddr, F.lan_netmask)" in T
      and "overlap(sn, nm, OV[oth].sn, OV[oth].nm)" in T and "function overlap(a, am, b, bm)" in T)
check("OpenVPN: local / remote endpoints (B-OVPN-3) and the cipher list (B-OVPN-4) validated",
      "has('vpn_server_local') && c.vpn_server_local && !unicast(c.vpn_server_local)" in T and "/^[A-Za-z0-9:-]+$/.test(c.vpn_server_ncp_ciphers)" in T)
check("OpenVPN: the instance cursor and the cert / key / export hooks use the stock endpoints, cursor written only on the user's click",
      "action_mode=change_vpn_server_unit&action_script=&action_wait=1&current_page=Reaper_VPNServer.asp&next_page=&vpn_server_unit=" in T
      and "hook=ovpn_generate_client_key()" in T and "'/upload_server_ovpn_cert.cgi'" in T and "fd.append('import_cert_file', file, file.name)" in T and "'client' + CUR + '.ovpn'" in T)

# ---- WireGuard (rc/wireguard.c start_wgs reads wgs1_*; httpd maps wgs_* / wgsc_* with wgs_unit / wgsc_unit) ----
check("WireGuard: wgs_unit first, wgsc_unit before wgsc_* (web.c:4786-4805)",
      names.index("wgs_unit") < names.index("wgs_enable") and names.index("wgsc_unit") < names.index("wgsc_enable") and "changed.wgs_unit = '1';" in T)
check("WireGuard: enabling seeds the stock defaults into indexed keys that were never written (rc reads wgs1_*, defaults.c:5693 has only wgs_*)",
      "var WGDEF = { enable: '0', lanaccess: '1', addr: '10.6.0.1/32', port: '51820', alive: '25', dns: '1', nat6: '1', psk: '0' };" in T
      and "if (c.wgs_enable === '1' && NV.wgs_enable !== '1') WGKEYS.forEach(function(k){ if (NV['wgs_' + k] === '' && c['wgs_' + k] === '') c['wgs_' + k] = wgCtlVal(k); });" in T)
check("WireGuard: server restart is always the unit-less restart_wgs (restart_wgs 1 ignores wgs1_enable, B-WGS-5), dnsmasq only when enable / dns changed",
      "S.push('restart_wgs')" in T and "restart_wgs 1" not in C and "restart_wgs '" not in C
      and "if (changed.wgs_enable !== undefined || changed.wgs_dns !== undefined) S.push('restart_dnsmasq');" in T)
check("WireGuard: peer save = one peer per post, live through restart_wgsc 1 N while running (update_wgs_client, wireguard.c:1931), saveNvram while off",
      "NV.wgs_enable === '1' ? 'restart_wgsc 1 ' + WEDIT : 'saveNvram'" in T and "wgs_unit: '1', wgsc_unit: String(u), wgsc_enable: '1'" in T)
check("WireGuard: delete blanks the whole slot including its keys and restarts the server (B-WGS-2 / B-WGS-4); a new slot gets fresh keys from rc",
      "wgsc_enable: '0', wgsc_name: '', wgsc_addr: '', wgsc_aips: '', wgsc_caips: '', wgsc_priv: '', wgsc_pub: '', wgsc_psk: ''" in T
      and "NV.wgs_enable === '1' ? 'restart_wgs' : 'saveNvram'" in T and "if (fresh){ f.wgsc_priv = ''; f.wgsc_pub = ''; f.wgsc_psk = ''; }" in T)
check("WireGuard: the server is never enabled behind the user's back (B-WGS-6); peer address lists byte-capped (wgs1_cN_aips / caips not whitelisted)",
      "wgs_enable: '1'" not in re.sub(r"c\.wgs_enable === '1'|NV\.wgs_enable [!=]== '1'", "", T) and "WG_LIST_BYTES = 1006 - 'wgs1_c10_caips='.length" in T
      and "aips.length > WG_LIST_BYTES || caips.length > WG_LIST_BYTES" in T)
check("WireGuard: export sets the stock wgsc_unit cursor then fetches the conf as text; wg show fetched as text (never placed raw by httpd)",
      "action_mode=chg_wgsc_unit&action_script=&action_wait=1&current_page=Reaper_VPNServer.asp&next_page=&wgsc_unit=" in T and "xget('/wgs_client.conf'" in T
      and "hook=nvram_dump(\"wgs.log\",\"\")" in T and "q('wgdump').textContent = rawHook(t).trim();" in T)

# ---- IPsec (rc/rc_ipsec.c parses ipsec_profile_1 / _2 by field index; web.c:18953 / 18957 are the templates) ----
check("IPsec: the two stock templates, regenerated only after an edit (B-IPSEC-1)",
      "'4>Host-to-Net>null>null>wan>>1>' + pskPost() + '>null>null>null>null>null>1>' + val('s_vsub') + '>null>1>null>null>0>null>null>null>1>>>eap-md5>1>500>4500>'" in T
      and "'4>Host-to-Netv2>null>null>wan>>0>null>null>null>null>null>null>1>' + val('s_vsub') + '>null>2>null>null>0>' + remoteId() + '>null>null>0>>>eap-mschapv2>1>500>4500>10>1>null>null>null>null><<<<>1>pubkey>svrCert.pem>always>svrKey.pem>%identity'" in T
      and "c.ipsec_profile_1 = edited ? buildP1() : NV.ipsec_profile_1;" in T and "c.ipsec_client_list_1 = edited ? serIusers(1) : NV.ipsec_client_list_1;" in T)
check("IPsec: ipsec_start / ipsec_stop as stock (services.c:23005 / 23020); clients-reconnect confirm; off-and-staying-off only saves",
      "S.push(c.ipsec_server_enable === '1' ? 'ipsec_start' : 'ipsec_stop')" in T and "`<#vpn_ipsec_clients_reconnect_hint#>`" in T
      and "if (c.ipsec_server_enable === '1' || NV.ipsec_server_enable === '1' || IGOFF)" in T)
check("IPsec: PSK 8-32 in a password field, no < > & \" (web.c PSK rule); virtual subnet checked against LAN, OpenVPN, WireGuard and PPTP (B-IPSEC-4)",
      "if (psk.length < 8 || psk.length > 32) return bad('s_psk'" in T and "/[<>&\"]/.test(psk)" in T
      and "overlap(vs + '.0', '255.255.255.0', F.lan_ipaddr, F.lan_netmask)" in T and "`<#RVSV_" in T and T.count("`<#RVSV_%02d#>` + ' " % own[0]) >= 0
      and "' OpenVPN')" in T and "' WireGuard')" in T and "' PPTP')" in T)
check("IPsec: passwords never in title attributes (B-IPSEC-2); IKE placement by bits, no silent 2 -> 3 (B-IPSEC-3); ajax_ipsec.asp parsed (B-IPSEC-5)",
      "title=\"' + hx(r.pass)" not in T and "map[f[0]].ver |= bit" in T and "<option value=\"3\">IKEv1 + IKEv2</option><option value=\"1\">IKEv1</option>" in T
      and "/=\\s*(\\[[\\s\\S]*\\])\\s*;?\\s*$/.exec(t), arr = m ? jsonOf(m[1]) : null" in T)
check("IPsec: an Instant Guard leftover is shown read-only and removed with its three keys on the user's click only (its page is gone)",
      "if (IGOFF){ c.ipsec_ig_enable = '0'; c.ig_client_list = ''; c.ig_guest_client_list = ''; }" in T and "on('igoffbtn', 'click', function(){ if (!confirm(`<#RVSV_" in T
      and 'name="ipsec_ig_enable" value="" disabled' in T and 'name="ig_client_list" value="" disabled' in T and 'name="ig_guest_client_list" value="" disabled' in T)
check("IPsec: IKEv2 certificate renew asks and polls ikev2_cert_state to 3 (web.c:18087 RENEW_FINISH); log cleared after a confirm",
      "xget('/renew_ikev2_cert_key.cgi'" in T and "String(j.ikev2_cert_state) === '3'" in T and "xget('/clear_file.cgi?clear_file_name=ipsec'" in T)

# ---- PPTP (rc/vpn.c start_pptpd; owner decision 3: kept and repaired) ----
check("PPTP: MS-CHAPv2 + MPPE-128 required on every save (vpn.c:197-210); the weak options are not offered",
      "c.pptpd_chap = PPFIX ? '2' : NV.pptpd_chap; c.pptpd_mppe = PPFIX ? '1' : NV.pptpd_mppe;" in T
      and "if (anyKey(changed, /^pptpd_/) && ppWeakAuth()){ changed.pptpd_chap = '2'; changed.pptpd_mppe = '1'; }" in T
      and "function ppWeakAuth(){ return NV.pptpd_chap !== '2' || NV.pptpd_mppe !== '1'; }" in T
      and not re.search(r'pptpd_mppe_(40|no|128)|name="pptpd_chap"[^>]*value="[01]"', T) and "MS-CHAPv2 + MPPE-128" in T)
check("PPTP: weak-protocol note on the tab, off by default (no auto-enable)", "`<#RVSV_%02d#>`" % own[0] not in "" and '<div class="weak"><#RVSV_' in T and "pptpd_enable: '1'" not in T)
check("PPTP: restart_pptpd / stop_pptpd (services.c:22312), restart_samba when enable or range changed and Samba is on (write_smb_conf.c:515); off-and-staying-off only saves",
      "S.push(c.pptpd_enable === '1' ? 'restart_pptpd' : 'stop_pptpd')" in T and "F.enable_samba === '1') S.push('restart_samba')" in T
      and "if (c.pptpd_enable === '1' || NV.pptpd_enable === '1' || PPPID)" in T)
check("PPTP: one manual DNS / WINS server is enough (B-PPTP-2); a client range containing the router address refused (B-PPTP-3); stock span / end checks kept",
      "if (!q('t_ppdnsauto').checked && !c.pptpd_dns1 && !c.pptpd_dns2) return bad('p_dns1'" in T
      and "if (ip2n(F.lan_ipaddr) >= ip2n(m[1] + m[2]) && ip2n(F.lan_ipaddr) <= ip2n(m[1] + m[3])) return bad('p_cstart'" in T
      and "var MAXSHIFT = 29;" in T and "if (+m[3] - +m[2] > MAXSHIFT)" in T and "if (!rp.v.int(m[3], 1, 254)) return bad('p_cend'" in T)
check("PPTP: user list and static routes serialised from the model (B-PPTP-4), passwords never in title attributes (B-PPTP-6), route to the router address refused (vpn.c:316)",
      "function serPsr()" in T and "c.pptpd_clientlist = PUSERS_EDITED ? serUsers(PUSERS) : NV.pptpd_clientlist;" in T
      and "if (ip === F.lan_ipaddr) { pmsg('ppusermsg'" in T and "serUsers(PUSERS.concat([r])).length > 4096" in T)
check("PPTP: Network Place forces broadcast relay as stock (vpn.c:231-236, 280-284); the running state from the daemon pid",
      "c.pptpd_broadcast = q('t_ppms').checked ?" in T and "/pptpdpid = \"(-?\\d*)\"/.exec(t); if (m) PPPID = parseInt(m[1], 10) > 0 ? m[1] : '';" in T
      and "if ((TAB_ON.ovpn && t === 'ovpn') || (TAB_ON.pptp && t === 'pptp')) pollVpnStatus();" in T)   # review 2026-10-24 Q-C1-2: the open tab only

# ---- tabs hide where menu.js hid the stock pages ----
check("tabs gated like the stock menu lines (openvpnd / wireguard / ipsec_srv / pptpd); a gone tab's keys never collect",
      "var TAB_ON = { ovpn: sup('openvpnd'), wg: sup('wireguard'), ipsec: sup('ipsec_srv'), pptp: sup('pptpd') };" in T
      and "if (!BROKEN[s.panel] && TAB_ON[s.tab]) s.collect(c);" in T)

# ---- wiring (the engineer makes these unconditional after wiring) ----
mj = rd(os.path.join(www, "reaper", "menu.js"))
inj_p = os.path.join(SRC, "httpd", "reaper_inject.c")
inj = rd(inj_p) if os.path.exists(inj_p) else ""
if True:  # wired 2026-10-24 (VPN wave): menu.js checks are unconditional
    check("menu: one VPN Server tab opens the Reaper page; the four stock server pages and the app host are gone from the rail",
          "T('Reaper_VPNServer.asp'" in mj and not any(p in mj for p in ("Advanced_VPN_OpenVPN.asp", "Advanced_WireguardServer_Content.asp", "Advanced_VPN_IPSec.asp",
                                                                        "Advanced_VPN_PPTP.asp", "Advanced_VPNServer_Content.asp", "Advanced_Instant_Guard.asp")))
if True:  # wired 2026-10-24 (VPN wave): reaper_inject.c checks are unconditional
    check("httpd: the page is native; the served stock pages redirect by tab",
          '"%s",' % PAGE in inj and all('{ "%s", "%s", ' % sr in inj for sr in (("advanced_vpn_openvpn.asp", "Reaper_VPNServer.asp?tab=ovpn"),
              ("advanced_wireguardserver_content.asp", "Reaper_VPNServer.asp?tab=wg"), ("advanced_vpn_ipsec.asp", "Reaper_VPNServer.asp?tab=ipsec"),
              ("advanced_vpn_pptp.asp", "Reaper_VPNServer.asp?tab=pptp"))))
    check("httpd: the removed app host and Instant Guard page bounce (reaper_pagemap[] rows marked not shipped)",
          re.search(r'"advanced_vpnserver_content\.asp",\s*"Reaper_VPNServer\.asp",\s*0', inj) is not None and re.search(r'"advanced_instant_guard\.asp",\s*"Reaper_VPNServer\.asp\?tab=ipsec",\s*0', inj) is not None)

# ---- parity files ----
for name in ("Advanced_VPN_OpenVPN", "Advanced_WireguardServer_Content", "Advanced_VPN_IPSec", "Advanced_VPN_PPTP", "Advanced_VPNServer_Content"):
    f = os.path.join(HERE, "ui_parity", name + ".json")
    d = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    check("parity file %s.json -> %s" % (name, PAGE), d.get("replacement") == PAGE)
    cov = [k for k, v in d.get("fields", {}).items() if v == "covered"]
    check("parity: every covered field of %s is a literal in the page (%d)" % (name, len(cov)), all(k in T for k in cov), [k for k in cov if k not in T])

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
