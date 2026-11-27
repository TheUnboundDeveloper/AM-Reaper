#!/usr/bin/env python3
"""Native-UI cutover, stage 2 (2026-11-25): AiMesh on the kit.

  Reaper_AiMesh.asp   replaces AiMesh.asp + aimesh/aimesh_topology.html + aimesh/aimesh_system_settings.html (and the
                      backhaul / fronthaul fragments). The owner's rule: the stock behaviour and function, in a Reaper
                      design and implementation. Same backends: the appGet hooks get_cfg_clientlist / get_clientlist /
                      get_clientlist_from_json_database / get_onboardingstatus, POST /applyapp.cgi (JSON, with the page
                      token) for every write, get_port_status.cgi and the get_diag_*_traffic.cgi readings. No stock
                      script is loaded: no jQuery, state.js, httpApi.js, client_function.js or jstree.
  owner decisions     a click on a connected device opens Reaper's Devices page; the LED schedule keeps the stock
                      scheduler (aimesh/aimesh_led_sched.html hosts it in a hidden frame)
  stage 4a            (2026-11-26) Add node runs in a dialog of the page with the stock wizard's requests, order and
                      timing; the page no longer names the wizard
  REAPER-CUT3         the menu tab and reaper_native[]. The stock page still ships and still opens by its own address
                      (no reaper_pagemap[] row yet): it stays as the reference until the owner has checked the kit
                      page against a real node
The page's behaviour is exercised in a DOM by the maintainer's scenario harness (49 scenarios against a scripted
router shaped like a captured two-member mesh); this suite pins the source facts those rest on, and the stock tables
the page copies (location presets, capability bits), so a firmware merge that changes one fails here.
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "reaper_inject.c")):
    print("SKIP: no router source tree with httpd/reaper_inject.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))
def rd(*p): return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()
def has(*p): return os.path.isfile(os.path.join(SRC, *p))

inj = rd("httpd", "reaper_inject.c"); web = rd("httpd", "web.c"); menu = rd("www", "reaper", "menu.js"); mk = rd("www", "Makefile")
pg = rd("www", "Reaper_AiMesh.asp")
m = re.search(r"reaper_pagemap\[\]\s*=\s*\{(.*?)\n\};", inj, re.S); tab = m.group(1) if m else ""
m = re.search(r"reaper_native\[\]\s*=\s*\{(.*?)\n\};", inj, re.S); native = m.group(1) if m else ""
EN = {}
for l in open(os.path.join(SRC, "www", "EN.dict"), encoding="utf-8", errors="replace"):
    if "=" in l: k, v = l.rstrip("\n").split("=", 1); EN[k] = v
head, js = pg.split("<script>\n(function(){", 1)

# ---------------------------------------------------------------- the page is a kit page
check("a Reaper-native kit page (meta, rp.css, rp.js, reaper_util.js; no other script file)",
      '<meta name="reaper-native" content="1">' in pg and 'href="/reaper/rp.css"' in pg
      and sorted(re.findall(r'<script src="([^"]+)"', pg)) == ["/reaper/rp.js", "/reaper_util.js"], re.findall(r'<script src="([^"]+)"', pg))
check("plain ASCII, LF line ends", all(ord(c) < 128 for c in pg) and "\r" not in pg)
check("one script, one strict closure", pg.count("<script>") - pg.count("<script>/*REAPER-CBMODE*/") == 1 and "'use strict';" in js[:40] and js.rstrip().endswith("</html>"))
toks = sorted(set(re.findall(r"<#([A-Za-z0-9_-]+)#>", pg)))
check("every dictionary token exists (%d tokens)" % len(toks), all(t in EN for t in toks), [t for t in toks if t not in EN])
out = [l.strip()[:90] for l in js.split("\n") if "<#" in re.sub(r"`[^`]*`", "", l)]
check("script: a dictionary token only inside a template literal (an apostrophe in a translation cannot end a string)", not out, out[:3])
check("script: no ${ in a template literal, no token text with a backtick", "${" not in js and not [t for t in toks if "`" in EN[t] or "${" in EN[t]])
check("names and router text go in as text: innerHTML only inside plain(), no eval, no document.write, no inline handler",
      js.count("innerHTML") == 1 and "d.innerHTML = String(s)" in js and "eval(" not in pg and "document.write" not in pg and not re.search(r'\son[a-z]+="', head))
ids = re.findall(r'id="([A-Za-z0-9_]+)"', head)
used = set(re.findall(r"\bq\('([A-Za-z0-9_]+)'\)", js)) | set(re.findall(r"\b(?:show|on)\('([A-Za-z0-9_]+)'", js))
check("markup ids are unique and every id the script asks for is there", len(ids) == len(set(ids)) and not (used - set(ids) - {"ledhost"}), sorted(used - set(ids)))
check("dialogs carry the class the shell anchors to the visible part of the frame", "el('div', 'ovl adlg')" in js)

# ---------------------------------------------------------------- reads
check("one joined request for members, clients and the values a write changes (hooks joined with %3B)",
      "'get_cfg_clientlist()', 'get_clientlist()', 'get_clientlist_from_json_database()', 'nvram_char_to_ascii(sta_binding_list,sta_binding_list)'" in js
      and "list.join('%3B')" in js)
for hook in ("get_cfg_clientlist", "get_clientlist", "get_clientlist_from_json_database", "get_onboardingstatus", "get_wan_unit"):
    check("httpd still has the hook %s" % hook, '{ "%s"' % hook in web)
for cgi in ("get_port_status.cgi", "get_diag_wifi_traffic.cgi", "get_diag_eth_traffic.cgi", "get_diag_sta_traffic.cgi", "reaper_dev.cgi", "applyapp.cgi"):
    check("httpd still serves %s, and the page asks for it" % cgi, '"%s' % cgi in web and "/" + cgi in js)
check("requests complete exactly once (load, error, timeout and abort share one guard)",
      "function end(ok){ if (fired) return; fired = true;" in js and "x.onerror = x.ontimeout = x.onabort = function(){ end(false); };" in js)
check("the refresh is single-flight, every 10 s, and waits while an optimisation runs or the page is hidden",
      "if (busy){ again = true;" in js and "timer = setInterval(tick, 10000);" in js and "if (document.hidden || reconFlag !== '') return;" in js)
check("no 25-minute self-reload (the stock page reloaded itself, closing dialogs and half-typed text)", "location.reload" not in js)

# ---------------------------------------------------------------- writes
check("every write goes through one function: POST /applyapp.cgi, the object as JSON, with the page token",
      js.count("'/applyapp.cgi'") == 1 and "b.http_id = HTTPID;" in js and "encodeURIComponent(JSON.stringify(b))" in js
      and 'var HTTPID = <% nvram_get_js("http_id"); %>;' in js)
check("a node setting is a config_changed event for that member", "apply({config: JSON.stringify(data), re_mac: mac, action_mode: 'config_changed'}, done);" in js)
for mode in ("config_changed", "force_roaming", "reset_default", "device_reboot", "re_reconnect", "prefer_node_apply", "onboarding", "firmware_check"):
    check("action %s: sent by the page, handled by httpd" % mode, "action_mode: '%s'" % mode in js and '"%s"' % mode in web)
WRITES = [
 ("router location", "apply({cfg_alias: text, action_mode: 'apply'}, done);"),
 ("node location", "cfgSet(mac, {cfg_alias: text}, done);"),
 ("device reconnect", "apply({device_list: n.mac.toUpperCase(), client_mac: c.mac.toUpperCase(), action_mode: 'force_roaming'});"),
 ("bind: move the device first, 20 s block", "target_ap: target.mac.toUpperCase(), block_time: 20, action_mode: 'force_roaming'});"),
 ("bind rules", "apply({sta_binding_list: bindString(D.bind), rc_service: 'update_sta_binding', action_mode: 'apply'}, done);"),
 ("remove node", "apply({slave_mac: n.mac, action_mode: 'reset_default'}"),
 ("connection priority", "cfgSet(n.mac, {amas_ethernet: want}"),
 ("preferred AP (node applies it)", "apply({target_bssid: mac, re_mac: n.mac.toUpperCase(), action_mode: 'prefer_node_apply'}, done);"),
 ("preferred AP (older nodes)", "amas_wlc0_target_bssid: up('ap2g'), amas_wlc1_target_bssid: up('ap5g'), amas_wlc2_target_bssid: up('ap5g1')}"),
 ("link aggregation", "cfgSet(n.mac, {lacp_enabled: sel.value}"),
 ("LED brightness", "cfgSet(n.mac, {bc_ledLv: parseInt(r.value, 10) - 1}"),
 ("LED (lp55xx nodes)", "{lp55xx_lp5523_user_enable: 1, lp55xx_lp5523_user_col: 101, lp55xx_lp5523_user_beh: 300}"),
 ("LED (router alone)", "apply({led_val: v, rc_service: 'ctrl_led', action_mode: 'apply'}, done);"),
 ("radio on / off", "data['wl' + r.idx + '_radio'] = on2 ? 1 : 0; cfgSet(n.mac, data"),
 ("reboot node", "apply({device_list: n.mac.toUpperCase(), action_mode: 'device_reboot'}"),
 ("Ethernet-only backhaul", "apply({amas_eap_bhmode: v, action_mode: 'apply', rc_service: 'restart_wireless'}"),
 ("system LED", "var o = {rc_service: 'no_service', action_mode: 'apply'}; o[key] = v;"),
 ("system reset", "apply({action_mode: 'reset_default'}, null, true);"),
 ("system reboot", "apply({action_mode: 'device_reboot'}, null, true);"),
]
for name, frag in WRITES:
    check("write: %s" % name, frag in js)
check("bind rule text: <NODE>ENABLE>CLIENT,15 joined with a bar; nodes with no device are left out",
      "if (list.length) s += '<' + node + '>' + b[node].enable + '>' + list.map(function(m){ return m + ',15'; }).join('|');" in js)
check("rc still runs update_sta_binding and ctrl_led", '"update_sta_binding"' in rd("rc", "services.c") and '"ctrl_led"' in rd("rc", "services.c"))
check("follow-up refreshes are timed from the reply (stock timed them from the send)", "function done(j){ if (j !== null) later(1000); }" in js)

# ---------------------------------------------------------------- stock tables the page copies
st = rd("www", "state.js")
m = re.search(r"var aimesh_location_arr = \[(.*?)\];", st, re.S)
stock_loc = re.findall(r'\{value:"([^"]+)",text:"<#(AiMesh_NodeLocation\d+)#>"\}', m.group(1)) if m else []
page_loc = re.findall(r"\['([^']+)', `<#(AiMesh_NodeLocation\d+)#>`\]", js)
check("location presets: the stock list, value for value and text for text (%d)" % len(stock_loc), len(stock_loc) == 28 and page_loc == stock_loc,
      [x for x in stock_loc if x not in page_loc] + [x for x in page_loc if x not in stock_loc])
api = rd("www", "js", "httpApi.js")
blk = api[api.index('"aimesh_get_node_capability"'):api.index("var node_capability_status")]
stock_caps = {}
for mm in re.finditer(r'"value"\s*:\s*(\d+),\s*"def"\s*:\s*\{(.*?)\}\s*\}', blk, re.S):
    for nm, bit in re.findall(r'"(\w+)"\s*:\s*\{"bit"\s*:\s*(\d+)', mm.group(2)): stock_caps[(mm.group(1), int(bit))] = nm
m = re.search(r"var CAPDEF = \{(.*?)\n\};", js, re.S)
page_caps = {}
for idx, body in re.findall(r"'(\d+)': (\[[^\]]*\]|\{[^}]*\})", m.group(1) if m else ""):
    if body[0] == "[":
        for bit, nm in enumerate(re.findall(r"'(\w+)'", body)): page_caps[(idx, bit)] = nm
    else:
        for bit, nm in re.findall(r"(\d+): '(\w+)'", body): page_caps[(idx, int(bit))] = nm
bad = [(k, v, stock_caps.get(k)) for k, v in sorted(page_caps.items()) if stock_caps.get(k) != v]
check("capability bits: every bit the page names is the stock helper's bit (%d)" % len(page_caps), len(page_caps) >= 30 and not bad, bad)
check("a member that reports no capability 15 counts as WAN-capable (old firmware), as stock", "(idx === '15' ? 1 : 0)" in js)
check("httpd reshapes capability 21 into numbered port objects (Def, Type, SubType, index, amas_ethernet); the page reads both shapes",
      'json_object_object_add(portObj, "amas_ethernet"' in web and "if (Array.isArray(p)) return p.filter(" in js and "for (k in p) if (has(p, k) && p[k] && typeof p[k] === 'object') out.push(p[k]);" in js)

# ---------------------------------------------------------------- behaviour rules pinned at the source
check("quality: 5 / 6 GHz graded at -70 and -80 dBm, 2.4 GHz always weak, an MLO uplink never below OK",
      "if (v > -70){ r.quality = 3; r.text = QT.great; }" in js and "else if (v >= -80){ r.quality = 2; r.text = QT.ok; }" in js
      and "r.quality = 2; r.text = QT.ok;" in js and "if (!isNaN(v) && v > -70){ r.quality = 3; r.text = QT.great; }" in js
      and "r.quality = 1; r.text = QT.weak; r.rssi.push({title: '2.4 GHz', rssi: parseInt(n.rssi2g, 10)});" in js)
check("tree: a wired node hangs under the LAST member that lists it; an unknown parent means the router",
      "m.wired_mac.indexOf(n.mac) !== -1) hit = m;" in js and "else if (hit) break;" in js and "return hit && hit.mac ? hit.mac : CAP;" in js)
check("the state reads without colour: the uplink kind and the quality word are in each row", "pathWord(n) + ' / ' + quality(n).text" in js)
check("location text: trimmed, not blank, no double quote, 32 bytes in UTF-8",
      "if (v.indexOf('\"') >= 0) return '\" ' + `<#JS_invalid_chars#>`;" in js and "if (utf8len(v) > 32)" in js)
check("a refresh leaves the location controls alone while the user is in them", "if (!force && (locBusy || a === sel || a === txt)) return;" in js)
check("Access Point / repeater / media bridge: Reaper's device store places the clients, asked with the token, at most every 30 s",
      "var AP = {on: !ROUTING, t: 0, busy: false, dev: null};" in js and "'/reaper_dev.cgi?action=status&http_id=' + encodeURIComponent(HTTPID)" in js
      and "Date.now() - AP.t < 30000" in js and "if (!d || !d.online || d.mlo_link || d.node || !d.mac || !d.via) continue;" in js)
check("the setup notice: shown until this router is the mesh controller, with the link to the Wi-Fi setup box",
      "show('setupnote', (NV.sw_mode === '1' || (NV.sw_mode === '3' && NV.wlc_psta !== '1')) && NV.re_mode !== '1' && NV.x_Setting !== '1' && NV.cfg_master !== '1');" in js
      and '<#RAMS_10#> <a href="/reaper_shell.asp#Reaper_WiFiSetup.asp" target="_top"><#RWFS_1#></a>' in head)
check("owner decision: a connected device opens Reaper's Devices page", "location.href = '/reaper_shell.asp#Reaper_Devices.asp';" in js)
check("links to pages that no longer ship go to their Reaper pages (firmware, roaming block list, MLO, Wi-Fi settings)",
      all(("'/reaper_shell.asp#%s'" % p) in js for p in ("Reaper_Firmware.asp", "Reaper_RoamBlock.asp", "Reaper_MLO.asp", "Reaper_WiFiSettings.asp"))
      and all(has("www", p) for p in ("Reaper_Firmware.asp", "Reaper_RoamBlock.asp", "Reaper_MLO.asp", "Reaper_WiFiSettings.asp", "Reaper_Devices.asp")))
check("Ethernet-only backhaul: drawn on MLO builds only (the stock form that renames the networks on older models is not carried)",
      "if (sup('amas_eap') && sup('mlo')){" in js)
cfgp = os.path.join(SRC, ".config")
if os.path.isfile(cfgp):
    check("...and this tree is an MLO build", re.search(r"^RTCONFIG_MLO=y", open(cfgp, encoding="utf-8", errors="replace").read(), re.M) is not None)
check("ASUS's FAQ pages are plain links, opened in a new tab, only on a click (no request is made for them)",
      js.count("nw-dlcdnet.asus.com") == 1 and "a.target = '_blank'; a.rel = 'noopener noreferrer';" in js)

# ---------------------------------------------------------------- add node: the wizard's steps, in the page (stage 4a)
check("Add node runs in the page: the stock wizard, its window and its hand-back are not named",
      "QIS_wizard" not in pg and "child_window_callback" not in pg and "window.open('', '_blank'" not in js)
check("node limit and not-ready are refused before the dialog", "if (s.cfg_ready !== '1'){ info(" in js and "if (cnt >= max){" in js)
check("search: the selection is cleared, then onboarding is made available when it is off; the list and the status are read together",
      "apply({action_mode: 'ob_selection'}, function(){" in js and "if (s2 && s2.cfg_obstatus === '1') apply({action_mode: 'onboarding'}, null, true);" in js
      and "hooks(['get_onboardinglist()', 'get_onboardingstatus()']," in js)
check("choose and pair: the selection names the node and its link; the pairing request names the uplink member",
      "apply({action_mode: 'ob_selection', new_re_mac: c.mac, ob_path: c.source}, null, true);" in js
      and "apply({action_mode: 'ob_selection', new_re_mac: mac, ob_path: source}, null, true);" in js
      and "apply({action_mode: 'onboarding', re_mac: pap, new_re_mac: mac}, null, true);" in js)
check("httpd still takes both events and serves both readings",
      'else if (!strcmp(action_mode, "onboarding")) {' in web and 'else if (!strcmp(action_mode, "ob_selection")) {' in web
      and '{ "get_onboardinglist", ej_get_onboardinglist}' in web and '{ "wl_nband_info", ej_wl_nband_info}' in web)
check("a Wi-Fi mode the node cannot join is changed with a wireless restart, never on 6 GHz, never with MLO on",
      "b.action_mode = 'apply'; b.rc_service = 'restart_wireless';" in js and "if (String(v) === '4') return;" in js
      and "if (sup('mlo') && d.mld_enable === '1') P = {};" in js)
check("the dialog is modal and every timer is tied to the open step",
      "modal: true, onCancel: function(){ anEnd(a); }" in js and "if (e.target === ov && !o.modal) cancel();" in js
      and "function anOk(a, g){ return AN === a && dlgNow === a.d && a.gen === g; }" in js)
check("a candidate's name reaches the result text as text", ".split('#DEV#').join(who)" in js)
hj = os.path.join(SRC, "www", "sysdep", "FUNCTION", "QIS_V3", "mobile", "js", "handler.js")
if os.path.isfile(hj):
    hs = open(hj, encoding="utf-8", errors="replace").read()
    check("the timings are the stock wizard's: 120 s search, 3 s before the pairing request, 10 s after a wireless restart, 180 s to come online",
          "var searchTimeout = 120;" in hs and "Date.now() > t0 + 120000" in js
          and "cfg_obtimeout = 180;" in hs and "tmo = 180;" in js
          and "setTimeout(onboardingSearch, 10000)" in hs and "anLater(a, g, 10000, findAgain);" in js
          and '"new_re_mac": re_Mac\n\t\t\t\t});\n\t\t\t}, 3000);' in hs and "anLater(a, g, 3000, function(){ apply({action_mode: 'onboarding', re_mac: pap" in js)

# ---------------------------------------------------------------- the stock LED scheduler's host
host = rd("www", "aimesh", "aimesh_led_sched.html") if has("www", "aimesh", "aimesh_led_sched.html") else ""
check("owner decision: the LED schedule is the stock scheduler, hosted in a hidden frame", "var LED_HOST = '/aimesh/aimesh_led_sched.html';" in js and "new popupLedScheduler({" in host)
check("the host loads the stock scripts the scheduler needs, so the Reaper page loads none",
      re.findall(r'src="([^"]+)"', host) == ["/js/jquery.js", "/state.js", "/js/httpApi.js", "/js/ledScheduler.js"], re.findall(r'src="([^"]+)"', host))
check("the host adds the page token to the scheduler's saves and reports the close to the top window",
      "o.http_id = TOKEN;" in host and "new CustomEvent('ledSchedulerClosed')" in host and "top2.addEventListener('ledSchedulerClosed'" in js)
check("the host is plain ASCII", all(ord(c) < 128 for c in host))
check("Makefile: the host goes when the scheduler is not built",
      "\trm -rf $(INSTALLDIR)/www/js/ledScheduler.js\n\trm -f $(INSTALLDIR)/www/aimesh/aimesh_led_sched.html\n" in mk)

# ---------------------------------------------------------------- wiring
check("menu: AiMesh is the kit page, under the stock condition", "{index: 'menu_AiMesh', label: 'AiMesh', when: aimeshRouterUI, tabs: [T('Reaper_AiMesh.asp', 'AiMesh')]}," in menu
      and "T('AiMesh.asp'" not in menu)
check("httpd: the page is in reaper_native[] (the shell frames it; no stock stylesheet is injected)", '\t"Reaper_AiMesh.asp",' in native)
check("REAPER-CUT8 (stage 5): the stock page no longer ships (removed at install, the source stays) and its address goes to the kit page",
      has("www", "AiMesh.asp") and "\trm -f $(INSTALLDIR)/www/AiMesh.asp\n" in mk[mk.find("REAPER-CUT8-STOCK"):]
      and "\trm -f $(INSTALLDIR)/www/aimesh/aimesh_topology.html\n" in mk[mk.find("REAPER-CUT8-STOCK"):]
      and '{ "aimesh.asp", "Reaper_AiMesh.asp", 0 }' in tab and '"AiMesh.asp"' not in inj)
check("Makefile: the kit page goes with AiMesh on a build without it (two places, as the stock page)",
      mk.count("\trm -f $(INSTALLDIR)/www/Reaper_AiMesh.asp\n") == 2)
pages = sorted(set(re.findall(r"T\('([A-Za-z0-9_]+\.(?:asp|htm|html))'", menu)))
left = [p for p in pages if not p.startswith(("Reaper_", "Main_ReaperDash"))]
check("menu: no stock page is listed any more (stage 3 moved the Network page to the kit)", left == [], left)

if fails:
    print("\n%d FAILED" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
