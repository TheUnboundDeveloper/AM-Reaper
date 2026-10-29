#!/usr/bin/env python3
"""WAN > Internet Connection and LAN > IPTV on the Reaper kit (Reaper-native UI, LAN/WAN wave, 2026-10-23):
Reaper_Internet.asp replaces the MULTISERVICE_WAN overlay Advanced_WAN_Content.asp (the page that ships) and
Advanced_Modem_Content.asp (the USB unit's view); Reaper_IPTV.asp replaces Advanced_IPTV_Content.asp.

WHY. These are the riskiest pages in the UI: a wrong post takes the household offline. Stock wrote nvram on page load
(wan_get_parameter copied wan<N>_* into wan_*, the IPTV page's get_MS_WAN_list_Pri set wan_unit=0), saved WAN DNS and
Multi-Service WAN profiles without Apply, sent IPTV conflict fixes before the reboot was confirmed, threw on the WAN
aggregation save (validForm wrote wans_dualwan / wans_mode inputs the form lacked), never validated the IPTV service
connections' manual DNS (if(!x == "1")), and embedded the PPPoE passwords in the page. The Reaper pages post only what
changed, confirm every WAN restart or reboot first (saying what drops and for how long), and never hold a password.

WHAT IT DOES. Source checks on both pages (kit, closure, tokens, nvram reads, posting pattern, restarts, confirms, the
fixed stock bugs), the parity files' covered names against the hidden inputs, `node --check` on each page script, and -
once the engineer has wired them - menu.js / reaper_inject.c. The per-type visibility and the POST of every restart and
conflict path were checked in jsdom when the pages were written (scen_Reaper_Internet.txt, scen_Reaper_IPTV.txt).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isdir(SRC):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
HERE = os.path.dirname(os.path.abspath(__file__))
PI, PT = os.path.join(www, "Reaper_Internet.asp"), os.path.join(www, "Reaper_IPTV.asp")
if not os.path.exists(PI) and not os.path.exists(PT):
    print("SKIP: Reaper_Internet.asp / Reaper_IPTV.asp not found"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
en = rd(os.path.join(www, "EN.dict"))
# the code without comments (the pages' comments name the stock calls they no longer make)
code = lambda t: re.sub(r"/\*.*?\*/|<!--.*?-->", "", t, flags=re.S)

def common(tag, t):
    js = t[t.rfind("<script>"):]
    check(tag + ": ASCII only", not any(ord(c) > 127 for c in t))
    check(tag + ": on the kit (plain rp.css link, rp.js, reaper-native meta), crimson frame",
          '<link rel="stylesheet" href="/reaper/rp.css">' in t and '<script src="/reaper/rp.js"></script>' in t
          and '<meta name="reaper-native" content="1">' in t and 'rframe' in t and "SPDX-License-Identifier: GPL-2.0-only" in t)
    check(tag + ": one closure, strict, no inline handlers, no jQuery/httpApi/state.js",
          js.startswith("<script>\n(function(){\n'use strict';") and js.count("<script>") == 1 and js.rstrip().endswith("})();\n</script>\n</body>\n</html>")
          and not re.search(r'\son[a-z]+=', t) and not re.search(r'src="/(js/jquery|js/httpApi|state|general)\.js"', t))
    toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
    miss = [k for k in toks if ("\n%s=" % k) not in en]
    check(tag + ": every dict token exists (%d)" % len(toks), not miss, miss)
    check(tag + ": tokens in the script only inside backticks", "<#" not in re.sub(r"`[^`]*`", "", js))
    check(tag + ": no nvram_get, every value through nvram_char_to_ascii + decodeURIComponent",
          "nvram_get(" not in t and ("U = rp.dec" in t or "function U(s){ try { return decodeURIComponent(s); }" in t))
    pw = re.findall(r'nvram_char_to_ascii\("",\s*"([^"]*(?:passwd|modem_pass|modem_pincode))"\)', t)
    check(tag + ": no password is read into the page (only an is-it-saved nvram_match)", not pw, pw)
    nm = re.findall(r'nvram_match\("([^"]+)"', t)
    check(tag + ": nvram_match only for the password-saved flags", nm and all(re.search(r'(passwd|modem_pass|modem_pincode)$', n) for n in nm), nm)
    check(tag + ": no write on load (no wan_get_parameter, get_MS_WAN_list*, change_wan_unit)",
          not re.search(r'wan_get_parameter|get_MS_WAN_list|change_wan_unit', code(t)))
    check(tag + ": untouched Apply posts nothing (diff first, then validate)",
          "if (!count(changed)){ msg(T.nothing); return; }" in t)
    check(tag + ": only changed settings reach rp.post", re.search(r"rp\.post\(f, changed, ", t) is not None)
    node = shutil.which("node")
    if node:
        body = js[len("<script>"):js.rfind("</script>")]
        body = re.sub(r"<%.*?%>", "", body, flags=re.S); body = re.sub(r"`[^`]*`", "''", body)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(body); jp = f.name
        r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
        check(tag + ": page script parses (node --check)", r.returncode == 0, r.stderr[-300:])
    else:
        print("note: node not found - syntax check skipped")

def covered_inputs(tag, t, parity):
    p = os.path.join(HERE, "ui_parity", parity)
    if not os.path.exists(p): check(tag + ": parity file " + parity, False); return
    d = json.load(open(p, encoding="utf-8"))
    cov = [k for k, v in d["fields"].items() if v == "covered"]
    miss = [k for k in cov if '<input type="hidden" name="%s" value="" disabled>' % k not in t]
    check(tag + ": every covered %s setting is a disabled hidden input (%d)" % (parity, len(cov)), not miss, miss)
    check(tag + ": stock action_script %r kept for its path" % d["action_script"], d["action_script"] in t)

if os.path.exists(PI):
    t = rd(PI); common("Internet", t)
    covered_inputs("Internet", t, "Advanced_WAN_Content.json"); covered_inputs("Internet", t, "Advanced_Modem_Content.json")
    check("Internet: every connection type of the overlay (+ JP S46 types behind s46, Bridge for profiles)",
          all(("%s:" % v) in t or ("'%s'" % v) in t for v in ("dhcp", "static", "pppoe", "pptp", "l2tp", "bridge", "v6plus", "ocnvc", "dslite", "v6opt"))
          and "if (!isProf(u) && sup('s46'))" in t)
    check("Internet: units switch in the browser and post wan_unit with the change (httpd maps wan_* to wan<N>_*)",
          "f.wan_unit.disabled = false; f.wan_unit.value = UNIT;" in t and '<input type="hidden" name="wan_unit" value="" disabled>' in t)
    check("Internet: WAN changes run restart_wan_if (httpd appends the unit), confirmed with what drops and for how long",
          "script = 'restart_wan_if'; wait = 5;" in t and "lines.push(fmt(T.cDrop, baseName(baseOf(UNIT))));" in t
          and "if (lines.length){ lines.push(T.cGo); if (!confirm(lines.join('\\n\\n'))) return; }" in t)
    check("Internet: UPnP-only -> restart_firewall;restart_upnp, TTL-only -> restart_firewall, no WAN restart",
          "if (ttl || upnp) S.push('restart_firewall');" in t and "if (upnp) S.push('restart_upnp');" in t)
    check("Internet: reboots (aggregation, auto-WAN pin, IPTV cleared, dual-WAN keys, USB modem) are confirmed with the reboot time",
          "script = 'reboot'; wait = REBOOT_WAIT;" in t and "lines.push(fmt(T.cReboot, REBOOT_WAIT));" in t
          and "if (usb && unitChanges(changed)) reboot = true;" in t)
    check("Internet: B-WAN-1 fixed - aggregation with dual WAN posts real wans_dualwan / wans_mode inputs",
          "extra.wans_dualwan = 'wan none'; extra.wans_mode = 'fo';" in t and '<input type="hidden" name="wans_dualwan" value="" disabled>' in t
          and '<input type="hidden" name="wans_mode" value="" disabled>' in t)
    check("Internet: 802.1Q / IPTV conflict asked only when 802.1Q is turned on", "if (changed.wan_dot1q === '1' && !prof && iptvOn){" in t)
    check("Internet: WAN DNS lives on the DNS page (link, no DNS-server fields for a base WAN; DoT client not carried)",
          'href="/reaper_shell.asp#Reaper_DNS.asp"' in t and "R.dnsman = prof && " in t and "dnspriv" not in t)
    check("Internet: a base WAN switched to Static needs its DNS servers set first",
          "if (!isProf(UNIT) && v === 'static' && n.proto !== 'static' && !(n.dnsenable_x === '0' && (n.dns1_x || n.dns2_x))) return bad('s_proto', T.dnsStatic);" in t)
    check("Internet: Multi-Service WAN profiles saved by Apply (read with appGet, no applyapp), delete posts only wan_enable=0",
          "applyapp" not in code(t) and "'/appGet.cgi?hook=' + hook" in t and "put(c, 'wan_enable', 't_enable', chk('t_enable'));" in t)
    check("Internet: stock checks kept - static IP/mask/gateway, PPPoE MTU/MRU 128-1500 + RFC 4638 pairing, Host-Uniq hex, MTU 1280-1500, UPnP ports, MAC unicast",
          "if (c.wan_gateway_x === c.wan_ipaddr_x) return bad('i_gw', T.eGwIp);" in t and "num(val('i_pmtu'), 128, 1500)" in t
          and "if (+pm > 1492 && +pr <= 1492) pr = pm;" in t and "/^[0-9A-Fa-f]*$/" in t and "num(c.wan_mtu, 1280, 1500)" in t
          and "if (+val('i_intmax') < +val('i_intmin'))" in t and "/^.[02468aceACE]/" in t)
    check("Internet: checks the inventory flagged - VLAN ID 2-4094 with 802.1Q, 802.1P 0-7, VPN server <= 64 chars (CKN_STR64)",
          "num(c.wan_vid, 2, 4094)" in t and "num(c.wan_dot1p, 0, 7)" in t and 'id="i_hb" maxlength="64"' in t and "c.wan_heartbeat_x.length > 64" in t)
    check("Internet: switching into v6plus / OCN / IPv6 Option resets the MAP rule first (s46reset.cgi), as stock",
          "xr.open('GET', '/s46reset.cgi', true);" in t)

if os.path.exists(PT):
    t = rd(PT); common("IPTV", t)
    covered_inputs("IPTV", t, "Advanced_IPTV_Content.json")
    check("IPTV: profiles / STB ports / port names from the stock httpd calls",
          "[<% get_iptvSettings(); %>][0]" in t and "[<% get_stbPortMappings(); %>][0]" in t)
    check("IPTV: profile / STB / VLAN change reboots (confirmed), the rest restart_net as stock",
          "var reboot = assign;" in t and "rp.post(f, changed, 'reboot', REBOOT_WAIT, false);" in t and "rp.post(f, changed, 'restart_net', 10);" in t
          and "if (!confirm(lines.join('\\n\\n'))) return;" in t)
    i_conf, i_app = t.find("if (!confirm(lines.join('\\n\\n'))) return;"), t.find("xr.open('POST', '/applyapp.cgi', true);")
    check("IPTV: B-IPTV-3 fixed - the Multi-Service WAN fix is sent only after the final confirm, 802.1Q rides in the same post",
          0 < i_conf < i_app and "extra.wan_unit = '0'; extra.wan_dot1q = '0';" in t)
    check("IPTV: B-IPTV-1 fixed - manual service DNS validated",
          "if (c[u + 'dns1_x'] !== '' && !ip4u(c[u + 'dns1_x'])) return bad(p + '_dns1', T.eIp);" in t and "!x == " not in code(t))
    check("IPTV: stock checks kept - VID 2-4094, PRIO 0-7, service PPPoE MTU/MRU 576-1492, idle 0-4294967295, port conflicts refused",
          "num(val('i_vid' + i), 2, 4094)" in t and "num(val('i_prio' + i), 0, 7)" in t
          and "num(c[u + 'pppoe_mtu'], 576, 1492)" in t and "0, 4294967295" in t and "var pc = portConflict(R); if (pc){ msg(pc); return; }" in t)
    check("IPTV: multicast / IGMP / udpxy are Reaper_LAN's (field split): not posted here, linked",
          not re.search(r'name="(mr_enable_x|mr_igmp_ver|mr_qleave_x|emf_enable|udpxy_enable_x)"', t) and 'href="/reaper_shell.asp#Reaper_LAN.asp"' in t)
    check("IPTV: manual STB value derived from the filled VLAN IDs (0/3/4/6) as stock validForm",
          "return !a && !b ? '0' : (!a && b ? '3' : (a && !b ? '4' : '6'));" in t)

menu = rd(os.path.join(www, "reaper", "menu.js")) if os.path.exists(os.path.join(www, "reaper", "menu.js")) else ""
injp = os.path.join(SRC, "httpd", "reaper_inject.c"); inj = rd(injp) if os.path.exists(injp) else ""
if True:  # wired 2026-10-23
    check("menu: WAN > Internet Connection and LAN > IPTV open the Reaper pages; no stock WAN/IPTV/Modem tab left",
          "T('Reaper_Internet.asp'" in menu and "T('Reaper_IPTV.asp'" in menu
          and "Advanced_WAN_Content.asp" not in menu and "Advanced_IPTV_Content.asp" not in menu)
    check("httpd: both pages on reaper_native[] and the three stock pages redirect",
          '"Reaper_Internet.asp",' in inj and '"Reaper_IPTV.asp",' in inj
          and '{ "advanced_wan_content.asp", "Reaper_Internet.asp", ' in inj and '{ "advanced_modem_content.asp", "Reaper_Internet.asp", ' in inj
          and '{ "advanced_iptv_content.asp", "Reaper_IPTV.asp", ' in inj)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
