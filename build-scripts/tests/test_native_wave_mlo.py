#!/usr/bin/env python3
"""Native wave (owner, 2026-11-01): Wireless > MLO rebuilt as a Reaper kit page (Reaper_MLO.asp).

WHY. Stock MLO.asp is the SDN single-page app in an iframe (sdn.js, mlo.js, rwd_component.js). The owner approved a
native page with the master switch, the MLO profile list and the backhaul editor, with "Add a Network" handing off to
the Network page's own MLO wizard. The stock page keeps shipping until the owner has reviewed the new one.

WHAT IT CHECKS. On the kit and wired (reaper_native[], reaper_langcheck OUR[], the Wireless menu slot, stock page still
shipping). The requests are stock's: url-encoded JSON to /applyapp.cgi (httpd maps the band keys), the switch ON body
(mld_enable=1 plus 11be / crypto aes+gcmp256 / radio on / schedule off for every band present, rc_service "reboot;"),
the switch OFF body (mld_enable=0; an enabled MLO fronthaul goes off with it - apm<N>_mlo=0 + its band list without MLO
for a main network, apg<N>_enable=0 + its sdn_rl row disabled otherwise), the backhaul body (apg<N>_ssid / hide_ssid,
"restart_wireless;restart_sdn <idx>;", SSID 1-32 bytes). The list keeps stock's filter (type MLO, apg mlo 1 or 2, the
backhaul first). The backhaul password is masked until Show. SDN.asp opens the MLO wizard once for the one-shot flag.
The two new strings exist in all 25 packs. Behaviour measured in the mock (scratchpad hdr/mlo.js, 20 checks).
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_MLO.asp")):
    print("SKIP: no router source tree with www/Reaper_MLO.asp (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

t = rd("www", "Reaper_MLO.asp")
inj = rd("httpd", "reaper_inject.c")
nat = inj[inj.index("static const char *reaper_native[]"):]; nat = nat[:nat.index("};")]
pm = inj[inj.index("reaper_pagemap[] = {"):]; pm = pm[:pm.index("};")]
menu = rd("www", "reaper", "menu.js")
lc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reaper_langcheck.py")
lc = open(lc_path, encoding="utf-8").read() if os.path.isfile(lc_path) else ""

check("on the kit, one strict closure, no jQuery/httpApi/state.js, ASCII",
      '<meta name="reaper-native" content="1">' in t and 'href="/reaper/rp.css"' in t and 'src="/reaper/rp.js"' in t
      and t.count("'use strict';") == 1 and not re.search(r'src="/(js/jquery|js/httpApi|state)\.js"', t)
      and all(ord(c) < 128 for c in t))
check("in reaper_native[] (no stock skin injected)", '"Reaper_MLO.asp"' in nat)
check("in reaper_langcheck OUR[]", not lc or "'Reaper_MLO.asp'" in lc)
check("Wireless menu slot points here with stock's gate, not at MLO.asp",
      "T('Reaper_MLO.asp', 'MLO', sup('mtlancfg') && sup('mlo'))" in menu and "T('MLO.asp'" not in menu)
# 2026-11-01: the owner reviewed the kit page - stock MLO.asp stopped shipping (test_native_wave_unship.py)
check("stock MLO.asp unshipped after the owner's review: pagemap row shipped = 0 -> this page",
      '{ "mlo.asp", "Reaper_MLO.asp", 0 },' in pm)

check("posts as httpApi.nvramSet does: url-encoded JSON to /applyapp.cgi",
      "x.open('POST', '/applyapp.cgi', true);" in t and "x.send(encodeURIComponent(JSON.stringify(obj)));" in t)
check("switch ON: mld_enable=1, reboot;, and 11be / aes+gcmp256 / radio on / schedule off per band present",
      "var o = {action_mode: 'apply', rc_service: 'reboot;', mld_enable: '1'};" in t
      and "o[s.key + '_11be'] = '1'; o[s.key + '_crypto'] = 'aes+gcmp256'; o[s.key + '_radio'] = '1'; o[s.key + '_timesched'] = '0';" in t
      and "['2g1', '5g1', '5g2', '6g1', '6g2']" in t and "WLNB.indexOf(s.toUpperCase())" in t)
check("switch ON asks first, listing radios it turns on and schedules it turns off",
      "lines.push(`<#RNW_7#>`);" in t and "`<#Wireless_Radio#>`" in t and "`<#Time_Scheduling#>`" in t
      and "if (!confirm(lines.join('\\n'))) return false;" in t)
check("switch OFF: mld_enable=0, reboot;, enabled MLO fronthaul networks go off with it",
      "var o = {action_mode: 'apply', rc_service: 'reboot;', mld_enable: '0'}" in t
      and "return x.on && a && a.mlo === '2';" in t
      and "o['apm' + x.apg + '_mlo'] = '0';" in t and "o['apm' + x.apg + '_dut_list'] = mainDutNoMlo(firstBands(a.dut_list) & BAND_BITS);" in t
      and "o['apg' + x.apg + '_enable'] = '0';" in t and "f[2] = '0';" in t and "o.sdn_rl = rp.list.ser(" in t)
check("switch OFF warns when MLO networks go off (stock WiFi_mlo_disable_Hint) and names the reboot",
      "(fh.length ? `<#WiFi_mlo_disable_Hint#>` + '\\n' : '') + `<#AiMesh_System_Reboot_Hint#>`" in t)
# stock get_mainfh_dut_list(bits, false), line for line
for rule in ["if ((bits & 4) && !(bits & 2)) band += 2;", "if ((bits & 64) && !(bits & 16)) band += 16;",
             "if ((bits & 2) && !(band & 4)) band += 4;", "if ((bits & 16) && !(band & 64)) band += 64;",
             "if ((bits & 8) && bits > 8 && !(band & 2)) band += 2;", "if ((bits & 32) && bits > 32 && !(band & 16)) band += 16;",
             "return '<*>' + band + '>';"]:
    check("main band list without MLO keeps stock's rule: " + rule, rule in t)
check("a cancelled switch goes back", "if (!ok) this.checked = !this.checked;" in t)
check("a reboot waits the router's reboot time, then for httpd", "get_default_reboot_time" in t and "/httpd_check.xml?_=" in t)

check("list: stock's filter - type MLO, apg mlo 1 (backhaul, first) or 2 (fronthaul)",
      "if (x.name !== 'MLO') return;" in t and "if (a.mlo === '1') bh.push(x); else if (a.mlo === '2') fh.push(x);" in t
      and "return bh.concat(fh);" in t)
check("list: names go in escaped", "hx(a.ssid)" in t and not re.search(r"innerHTML\s*=[^;]*\ba\.ssid\b", t.replace("hx(a.ssid)", "")))
check("backhaul: apg<N>_ssid + apg<N>_hide_ssid, restart_wireless;restart_sdn <idx>;",
      "rc_service: 'restart_wireless;restart_sdn ' + selBh.idx + ';'" in t
      and "o['apg' + selBh.apg + '_ssid'] = s; o['apg' + selBh.apg + '_hide_ssid']" in t)
check("backhaul: SSID 1-32 bytes, no control characters", "bytes > 32" in t and "unescape(encodeURIComponent(s)).length" in t and "/[\\x00-\\x1f\\x7f]/" in t)
check("backhaul: the password is masked until Show (stock printed it in clear)",
      'id="v_pwd">&bull;' in t and "v.textContent = v.dataset.pwd" in t)
check("Add a Network: one-shot flag, then the SDN page",
      "sessionStorage.setItem('reaper_sdn_wizard', 'MLO')" in t and "top.location.href = '/reaper_shell.asp#SDN.asp';" in t)

sdn = rd("www", "sysdep", "FUNCTION", "SDN", "SDN.asp")
check("SDN.asp: reads and clears the flag, opens only the MLO wizard, on the app frame's load",
      'sessionStorage.removeItem("reaper_sdn_wizard")' in sdn and 'if(t!=="MLO") return;' in sdn
      and 'w.show_popup_Wizard_Setting("MLO")' in sdn and "reaperGrowFrame(_sifr); reaperOpenWizard(_sifr);" in sdn)
blk = sdn[sdn.find("/* reaper 2026-11-01"):sdn.find("/* reaper v3.3.1")]
check("SDN.asp: the hand-off block is ASCII (the stock file keeps its own BOM)", blk != "" and all(ord(c) < 128 for c in blk))

langs = [f for f in os.listdir(os.path.join(SRC, "www")) if f.endswith(".dict") and f != "temp.dict"]
miss = [(f, k) for f in langs for k in ("RNW_7", "RNW_8") if not re.search(r"^%s=." % k, rd("www", f), re.M)]
check("RNW_7 / RNW_8 in all %d packs" % len(langs), len(langs) == 25 and not miss, miss[:6])
check("RNW_8 carries its %1 (the page name) in every pack", all("%1" in re.search(r"^RNW_8=(.*)$", rd("www", f), re.M).group(1) for f in langs))
print("%d failure(s)" % len(fails))
for x in fails: print("  " + x)
sys.exit(1 if fails else 0)
