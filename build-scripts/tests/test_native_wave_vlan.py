#!/usr/bin/env python3
"""Native wave (owner, 2026-11-01): LAN > VLAN rebuilt as one Reaper kit page (Reaper_VLAN.asp, Switch + Profiles tabs).

WHY. The two stock VLAN pages (Advanced_VLAN_Switch_Content.asp, Advanced_VLAN_Profile_Content.asp with sdn.js) are the
last stock LAN tabs. The owner's router uses them live (VLAN 52 on router LAN 5, an RT-AX92U node - read on the lab,
2026-10-31), so the kit page must read that layout back exactly and write stock's requests. The stock pages keep
shipping until the owner has reviewed the new one.

WHAT IT CHECKS. On the kit and wired (reaper_native[], reaper_langcheck OUR[], one LAN menu tab with stock's gate in
place of both stock tabs, stock pages still shipping). Switch: nodes from get_cfg_clientlist capability 27 (smart-home
master excluded), ports from /get_port_status.cgi (W/L keys only), stock's port locks (dual-WAN LAN port, WAN
aggregation, LACP bonding table, IPTV, external switch, live WAN), Apply = every VLAN network's apg<N>_dut_list
(lanport cleared, Access ports appended, missing nodes added back as <MAC>>) + vlan_trunklist, rc_service
restart_net_and_phy, the lock-out warning when every router LAN port is on VLAN, a multi-VID trunk kept. Profiles: VID
3-4093 and unique, Add = stock's VLAN-only network (sdn row type Customized, br<idx+51> subnet with DHCP off from the
factory LAN defaults, open apg VLAN_<vid> with <MAC>0> for every node, restart_wireless;restart_net_and_phy;), Edit =
vlan_rl + trunk VID swap, Delete = rows out + *_x lists + apg<N>_enable=0 + VID out of the trunk list (+ QoS restart).
RNW_9 in all 25 packs. Behaviour measured in the mock (scratchpad hdr/vlan.js, 30 checks, Chromium 1366 + WebKit 402).
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_VLAN.asp")):
    print("SKIP: no router source tree with www/Reaper_VLAN.asp (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

t = rd("www", "Reaper_VLAN.asp")
inj = rd("httpd", "reaper_inject.c")
nat = inj[inj.index("static const char *reaper_native[]"):]; nat = nat[:nat.index("};")]
pm = inj[inj.index("reaper_pagemap[] = {"):]; pm = pm[:pm.index("};")]
menu = rd("www", "reaper", "menu.js")
lc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reaper_langcheck.py")
lc = open(lc_path, encoding="utf-8").read() if os.path.isfile(lc_path) else ""
GATE = "sup('mtlancfg') && !sup('SMART_HOME_MASTER_UI') && !is('rp', 'mb')"

check("on the kit, one strict closure, no jQuery/httpApi/state.js/sdn.js, ASCII",
      '<meta name="reaper-native" content="1">' in t and 'href="/reaper/rp.css"' in t and 'src="/reaper/rp.js"' in t
      and t.count("'use strict';") == 1 and not re.search(r'src="/(js/jquery|js/httpApi|state|SDN/sdn)\.js"', t)
      and all(ord(c) < 128 for c in t))
check("in reaper_native[] (no stock skin injected)", '"Reaper_VLAN.asp"' in nat)
check("in reaper_langcheck OUR[]", not lc or "'Reaper_VLAN.asp'" in lc)
check("one LAN menu tab with stock's gate, neither stock VLAN tab",
      "T('Reaper_VLAN.asp', 'VLAN', %s)" % GATE in menu
      and "T('Advanced_VLAN_Switch_Content.asp'" not in menu and "T('Advanced_VLAN_Profile_Content.asp'" not in menu)
# 2026-11-01: the owner reviewed the kit page - both stock VLAN pages stopped shipping (test_native_wave_unship.py)
check("both stock VLAN pages unshipped after the owner's review: pagemap rows shipped = 0 -> this page",
      '{ "advanced_vlan_switch_content.asp", "Reaper_VLAN.asp", 0 },' in pm
      and '{ "advanced_vlan_profile_content.asp", "Reaper_VLAN.asp?tab=pf", 0 },' in pm)
check("posts as httpApi.nvramSet does: url-encoded JSON to /applyapp.cgi",
      "x.open('POST', '/applyapp.cgi', true);" in t and "x.send(encodeURIComponent(JSON.stringify(obj)));" in t)

# Switch
check("Switch: nodes from get_cfg_clientlist with LAN ports (cap 27), smart-home master (cap 4 bit 22) left out",
      "get_cfg_clientlist()" in t and "(c['27'] || {}).lan_port" in t and "& 4194304" in t)
# _r5 on metal: lan_port is a JSON object keyed by port (rc.c check_lan_port_cap), so lp.length was undefined and no node showed
check("Switch: cap 27 lan_port counted as an object (Object.keys), not as an array",
      "typeof lp === 'object' && Object.keys(lp).length > 0" in t and "lp && lp.length" not in t)
check("Switch: live port state from /get_port_status.cgi (MAC sent as stock sends it), W/L ports only",
      "'/get_port_status.cgi?node_mac=' + n.mac + '&_='" in t and r"/^[WL]\d+$/.test(key)" in t)
for name, needle in [
        ("dual-WAN LAN port", "NV.wans_dualwan.indexOf('lan') >= 0 && NV.wans_lanport === idx"),
        ("WAN aggregation (LAN 4)", "p.label === 'L4' && NV.bond_wan === '1'"),
        ("LACP bonding table", "bondingPorts(node.product_id).indexOf(idx) >= 0"),
        ("IPTV ports", "NV.iptv_stb_port.indexOf(idx) > 0"),
        ("external switch port", "cap(d, 'LAN') && cap(d, 'WANLAN') && String(d.ext_port_id) !== '-1'"),
        ("live WAN port", "d.is_on === '1' && (cap(d, 'DUALWAN_SECONDARY_WAN') || cap(d, 'DUALWAN_PRIMARY_WAN'))")]:
    check("Switch: stock lock kept - " + name, needle in t)
check("Switch: every port gets its lock", "p.lock = lockOf(nd, p, i === 0);" in t)
check("Switch: Apply clears every lanport, appends Access ports per node, rebuilds the trunk list",
      "DUT[apg].forEach(function(r){ r.lanport = ''; });" in t
      and "r.lanport = r.lanport ? r.lanport + ',' + p.label : p.label;" in t
      and "t += '>' + p.label + '#' + (v.value || 'all');" in t and "if (t) trunk += '<' + n.mac + t;" in t)
check("Switch: nodes missing from a dut_list come back as <MAC>> (stock add_back_missing_apg_dut_list)",
      "rows.push({mac: n.mac, wifiband: '', lanport: ''});" in t)
check("Switch: body = apg<N>_dut_list + vlan_trunklist, rc_service restart_net_and_phy (no ;)",
      "o['apg' + apg + '_dut_list'] = '<' + DUT[apg].map(" in t and "o.vlan_trunklist = trunk; o.action_mode = 'apply'; o.rc_service = 'restart_net_and_phy';" in t)
check("Switch: every router LAN port on VLAN asks first (VLAN_eachport_assign)", "!confirm(`<#VLAN_eachport_assign#>`)" in t)
check("Switch: a multi-VID trunk this page did not write is kept", "if (mode === 'Trunk' && cur && cur !== 'all' && !have)" in t)

# Profiles
check("Profiles: VID 3-4093, unique", "rp.v.int(v, 3, 4093)" in t and "`<#JS_duplicate#>`" in t)
check("Profiles: stock's network limit (MaxRule_SDN - 1, default 6)", "UI.MaxRule_SDN === '0') ? 6 : (parseInt(UI.MaxRule_SDN, 10) - 1)" in t
      and "`<#AiMesh_Binding_Rule_Maxi#>`" in t)
check("Add: sdn row type Customized, 23 fields, created by WEB",
      "L.row([idx, 'Customized', '1', vidx, sub, apg, '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', 'WEB', '0', '0', '0'])" in t)
check("Add: subnet br<idx+51>, DHCP off, from the factory LAN defaults (21 fields + trailing >)",
      "'br' + (+idx + 51)" in t and "DEF.lan_netmask, '0', net + '.2', net + '.254'" in t and "nvram_default_get(\"lan_ipaddr\")" in t)
check("Add: open apg VLAN_<vid>, no Wi-Fi (<MAC>0> per node), restart_wireless;restart_net_and_phy;",
      "o[p + 'ssid'] = 'VLAN_' + vid;" in t and "o[p + 'security'] = '';" in t and "return '<' + n.mac + '>0>';" in t
      and "rc_service: 'restart_wireless;restart_net_and_phy;'" in t)
check("Edit: vlan_rl + the VID swapped in the trunk list, restart_net_and_phy;",
      "var o = {action_mode: 'apply', rc_service: 'restart_net_and_phy;', vlan_rl: L.ser(rows)};" in t and "x === old ? nv : x" in t)
check("Delete: rows out and into sdn_rl_x / vlan_rl_x / subnet_rl_x / radius_list_x, apg<N>_enable=0",
      "o.sdn_rl_x = sr.x; o.vlan_rl_x = vr.x; o.subnet_rl_x = nr.x; o.radius_list_x = rr.x;" in t and "o['apg' + s.f[5] + '_enable'] = '0';" in t)
check("Delete: VID out of the trunk list, emptied with the last VLAN row; QoS restart when QoS is on",
      "o.vlan_trunklist = vr.list === '' ? '' : trunkMap(" in t and "if (NV.qos_enable === '1') o.rc_service += 'restart_qos;restart_firewall;';" in t)
check("Delete asks first", "if (!confirm(`<#VPN_Fusion_Delete_Alert#>`)) return;" in t)
check("names go in escaped", "names.map(hx)" in t and "hx(n.model)" in t and "hx(portName(p))" in t)
check("the lock note fills its %@ (rp.fmt does not)", "`<#VLAN_port_binding_note#>`.replace('%@', " in t and "rp.fmt(`<#VLAN_port_binding_note#>`" not in t)

langs = [f for f in os.listdir(os.path.join(SRC, "www")) if f.endswith(".dict") and f != "temp.dict"]
miss = [f for f in langs if not re.search(r"^RNW_9=.", rd("www", f), re.M)]
check("RNW_9 in all %d packs" % len(langs), len(langs) == 25 and not miss, miss[:6])
check("VLAN_port_binding_note carries %@ in every pack", all("%@" in (re.search(r"^VLAN_port_binding_note=(.*)$", rd("www", f), re.M) or [None, ""])[1] for f in langs))
print("%d failure(s)" % len(fails))
for x in fails: print("  " + x)
sys.exit(1 if fails else 0)
