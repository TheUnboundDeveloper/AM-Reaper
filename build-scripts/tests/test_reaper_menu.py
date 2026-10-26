#!/usr/bin/env python3
"""The Reaper menu model (www/reaper/menu.js), 2026-10-22.

WHY. Three places drew the menu (shell rail, shell tab strip, dashboard rail) and the dashboard's was a hand
copy that ignored every mode/support condition. menu.js is now the one list; this runs it under node with
crafted facts and checks the conditions carried over from menuTree.js, that every token it uses exists in
EN.dict, and that every page it names ships.

WHAT IT DOES. Stubs the httpd tags, loads menu.js in node, calls ReaperMenu.build/tree/rail for router, AP,
repeater and media-bridge facts and prints the visible menus/pages as JSON for the assertions below.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")
WWW = os.path.join(SRC, "www")
P = os.path.join(WWW, "reaper", "menu.js")
if not os.path.exists(P):
    print("SKIP: menu.js not found"); sys.exit(0)
t = open(P, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

check("ASCII only", not any(ord(c) > 127 for c in t))
check("the icon map was filled in (no __ICONS__ placeholder)", "__ICONS__" not in t and "menu_Firewall:" in t)
tokens = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
en = open(os.path.join(WWW, "EN.dict"), encoding="utf-8", errors="replace").read()
missing = [k for k in tokens if ("\n%s=" % k) not in en]
check("every dict token in menu.js exists in EN.dict (%d tokens)" % len(tokens), not missing, missing)
check("tokens only inside backticks (rule 29)", "<#" not in re.sub(r"`[^`]*`", "", t))
pages = sorted(set(re.findall(r"T\('([A-Za-z0-9_]+\.(?:asp|htm|html))'", t)))
overlay = {"SDN.asp", "MLO.asp", "Advanced_WAN_Content.asp", "Advanced_Modem_Content.asp"}   # supplied by sysdep overlays (SDN, MULTISERVICE_WAN) at install
absent = [p for p in pages if not os.path.exists(os.path.join(WWW, p)) and p not in overlay
          and not os.path.exists(os.path.join(WWW, "sysdep", "FUNCTION", "SDN", p))]
# pages that only exist on other models' feature sets are allowed when a flag gates them
gated_only = {"Guest_network_fbwifi.asp", "AiProtection_ContentFilter.asp", "Ark_WebHistory_Content.asp", "fileflex.asp",
              "Advanced_MobileBroadband_Content.asp", "Advanced_PerformanceTuning_Content.asp", "Advanced_MultiSubnet_Content.asp"}
check("every page the model names ships in www (or is gated behind a flag) (%d pages)" % len(pages),
      not [p for p in absent if p not in gated_only], [p for p in absent if p not in gated_only])

node = shutil.which("node")
if not node:
    print("note: node not found - the runtime checks are skipped"); sys.exit(1 if fails else 0)

js = t.replace("[<% get_ui_support(); %>][0]", "{}").replace("[<% get_operation_mode(); %>][0]", "'rt'")
js = re.sub(r"<%.*?%>", "", js); js = re.sub(r"<#([A-Za-z0-9_]+)#>", r"\1", js)
ALL = {k: 1 for k in ("amas", "amasRouter", "mssid", "sdn_mwl", "mtlancfg", "PARENTAL2", "webs_filter", "ookla", "dns_dpi", "reaper_mcp",
                      "usbX", "media", "dualwan", "ipv6", "openvpnd", "pptpd", "ipsec_srv", "vpnc", "tor", "wireguard", "snmp", "nwtool",
                      "smart_connect_v2", "dnsfilter", "switchctrl", "mlo", "sdn_mainfh", "nt_center", "nt_center_ui", "fanctrl")}
harness = js + r'''
var out = {};
function vis(F){ var tr = window.ReaperMenu.tree(F).list, o = {}; tr.forEach(function(m){ if (m.index !== 'menu_Split') o[m.index] = m.tab.filter(function(x){ return x.url !== 'NULL'; }).map(function(x){ return x.url + (x.tabName === '__INHERIT__' ? '*' : x.tabName === '__HIDE__' ? '~' : ''); }); }); return o; }
var base = {ui: ALL, mode: 'rt', wans_dualwan: 'wan none', wlc_band: '', mlo_rp: '', mlo_mb: ''};
out.rt = vis(base);
out.ap = vis(Object.assign({}, base, {mode: 'ap'}));
out.rp = vis(Object.assign({}, base, {mode: 'rp'}));
out.mb = vis(Object.assign({}, base, {mode: 'mb'}));
out.wisp = vis(Object.assign({}, base, {mode: 'wisp'}));
out.nodual = vis(Object.assign({}, base, {ui: Object.assign({}, ALL, {dualwan: 0})}));
out.nomcp = vis(Object.assign({}, base, {ui: Object.assign({}, ALL, {reaper_mcp: 0})}));
out.usbwan = vis(Object.assign({}, base, {wans_dualwan: 'usb none'}));
out.novpn = vis(Object.assign({}, base, {ui: Object.assign({}, ALL, {openvpnd: 0, wireguard: 0, ipsec_srv: 0, pptpd: 0, vpnc: 0, tor: 0})}));   /* 2026-10-24 VPN wave */   /* USB primary, dual WAN not enabled (menuTree.js:743) */
/* AiMesh (menuTree.js:536-545): [amasRouter, amasNode, mode] - the RT-BE96U reports BOTH router and node */
out.amas = {};
[[1, 1, 'rt'], [1, 1, 'ap'], [1, 1, 'wisp'], [1, 1, 'rp'], [1, 0, 'rt'], [0, 1, 'rt'], [0, 0, 'rt'], [0, 0, 'rp']].forEach(function(c){
  var v = vis(Object.assign({}, base, {mode: c[2], ui: Object.assign({}, ALL, {amasRouter: c[0], amasNode: c[1]})}));
  out.amas[c.join('/')] = ('menu_AiMesh' in v ? 'M' : '-') + ((v.menu_Wireless || []).indexOf('Advanced_Roaming_Block_Content.asp') !== -1 ? 'R' : '-');
});
out.amas['noamas'] = 'menu_AiMesh' in vis(Object.assign({}, base, {ui: Object.assign({}, ALL, {amas: 0})})) ? 'M' : '-';
out.rail = window.ReaperMenu.rail(base).filter(function(r){ return !r.section; }).map(function(r){ return r.index + ':' + r.page + ':' + (r.icon ? 1 : 0); });
console.log(JSON.stringify(out));
'''
harness = "var window = {}; var ALL = " + json.dumps(ALL) + ";\n" + harness
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(harness); jp = f.name
r = subprocess.run([node, jp], capture_output=True, text=True)
os.unlink(jp)
check("menu.js runs under node", r.returncode == 0, r.stderr[-400:])
if r.returncode == 0:
    o = json.loads(r.stdout.strip().splitlines()[-1])
    rt, ap, rp, mb = o["rt"], o["ap"], o["rp"], o["mb"]
    check("router: WAN, VPN, Firewall, QoS, Traffic, Parental, IPv6 present", all(k in rt for k in ("menu_WAN", "menu_VPN", "menu_Firewall", "menu_BandwidthMonitor", "menu_TrafficAnalyzer", "menu_ParentalControl", "menu_IPv6")), sorted(rt))
    check("AP mode drops WAN, VPN, Firewall, QoS, Traffic, Parental, IPv6; keeps LAN and Wireless",
          not any(k in ap for k in ("menu_WAN", "menu_VPN", "menu_Firewall", "menu_BandwidthMonitor", "menu_TrafficAnalyzer", "menu_ParentalControl", "menu_IPv6"))
          and "menu_LAN" in ap and "menu_Wireless" in ap, sorted(ap))
    check("AP mode: DHCP tab only with dhcp_override; DNS Director, routes, IPTV hidden",
          "Advanced_DHCP_Content.asp" not in ap["menu_LAN"] and "DNSDirector.asp" not in ap["menu_LAN"] and "Advanced_GWStaticRoute_Content.asp" not in ap["menu_LAN"], ap["menu_LAN"])
    check("repeater and media bridge also drop Wireless and Network", "menu_Wireless" not in rp and "menu_GuestNetwork" not in rp and "menu_Wireless" not in mb and "menu_GuestNetwork" not in mb)
    check("media bridge no longer shows DNS Director (the DNSFilter.asp typo)", "menu_LAN" in mb and "DNSDirector.asp" not in mb["menu_LAN"], mb.get("menu_LAN"))
    # 2026-10-22 (owner): Reaper's own menus hide where rc no-ops the feature (gatekeeper.c:836, rwarden.c:2375,
    # wallguard.c:67, rdnshc.c:991 all guard on is_routing_enabled()); Devices/Sysinfo/Settings stay in every mode
    check("AP, repeater and media bridge hide Gatekeeper and Warden (Dreadwatch, Wallguard, Encrypted DNS ride its menu)",
          all(k not in m for m in (ap, rp, mb) for k in ("menu_ReaperGK", "menu_ReaperWarden")), [sorted(m) for m in (ap, rp, mb)])
    check("router and WISP keep Gatekeeper and Warden with all four Warden tabs",
          all(k in m for m in (rt, o["wisp"]) for k in ("menu_ReaperGK", "menu_ReaperWarden"))
          and all(x in rt["menu_ReaperWarden"] for x in ("Reaper_Warden.asp", "Reaper_Dreadwatch.asp", "Reaper_Wallguard.asp", "Reaper_EncryptedDNS.asp")), rt.get("menu_ReaperWarden"))
    check("Reaper_Failover (DNS health check) only in routing modes; Devices, Sysinfo and Settings in every mode",
          "Reaper_Failover.asp" in rt["menu_Setting"] and "Reaper_Failover.asp" in o["wisp"]["menu_Setting"]
          and all("Reaper_Failover.asp" not in m["menu_Setting"] for m in (ap, rp, mb))
          and all(k in m for m in (ap, rp, mb) for k in ("menu_ReaperDevices", "menu_Sysinfo", "menu_Setting")), [m.get("menu_Setting") for m in (ap, rp, mb)])
    check("WAN Ports only with dual-WAN support", "Reaper_WANPorts.asp" in rt["menu_WAN"] and "Reaper_WANPorts.asp" not in o["nodual"]["menu_WAN"])
    check("Advisor only on MCP builds", "menu_ReaperAdvisor" in rt and "menu_ReaperAdvisor" not in o["nomcp"])
    # 2026-10-23 LAN/WAN wave: the USB modem view lives inside Reaper_Internet - no stock WAN or modem page is named
    # (this node half never ran before 2026-10-24: no node in WSL, no tree on the CI runner - the old expectation was stale)
    check("USB as the only WAN: Reaper_Internet (with the modem view) stays, no stock WAN or modem page",
          "Advanced_WAN_Content.asp" not in o["usbwan"]["menu_WAN"] and "Advanced_Modem_Content.asp*" not in o["usbwan"]["menu_WAN"]
          and "Reaper_Internet.asp" in o["usbwan"]["menu_WAN"], o["usbwan"]["menu_WAN"])
    # 2026-10-24 VPN wave (wave 7): the menu is Reaper-native; the ASUS VPN app, Instant Guard and the Fusion page no longer ship
    check("VPN menu: Status, Director, Policy Routing, Server, Client, Tor - in that order",
          rt["menu_VPN"] == ["Reaper_VPNStatus.asp", "Reaper_VPNDirector.asp", "Reaper_VPNRouting.asp", "Reaper_VPNServer.asp", "Reaper_VPNClient.asp", "Reaper_Tor.asp"], rt["menu_VPN"])
    check("without any VPN feature flag only Status and Policy Routing remain",
          o["novpn"]["menu_VPN"] == ["Reaper_VPNStatus.asp", "Reaper_VPNRouting.asp"], o["novpn"]["menu_VPN"])
    # 2026-10-23: _r27 lost the AiMesh menu on the RT-BE96U - menu.js hid it whenever amasNode was set, but
    # menuTree.js checks amasRouter first (router-and-node models show it in router/WISP/AP mode)
    want = {"1/1/rt": "MR", "1/1/ap": "MR", "1/1/wisp": "MR", "1/1/rp": "--", "1/0/rt": "MR", "0/1/rt": "--", "0/0/rt": "MR",
            "0/0/rp": "M-", "noamas": "-"}   # 0/0/rp: menuTree has no mode test without amasRouter (Wireless is gone in rp, so no R)
    check("AiMesh menu (M) and Roaming Block tab (R) follow menuTree.js, router-and-node models included",
          o["amas"] == want, {k: (o["amas"].get(k), v) for k, v in want.items() if o["amas"].get(k) != v})
    check("Firewall carries its badge flag in the tree", any("menu_Firewall" == m for m in rt))
    check("rail: every visible menu has a first page and an icon; the dashboard is a top-level page",
          all(x.split(":")[2] == "1" and x.split(":")[1] for x in o["rail"]) and "menu_Index:Main_ReaperDash.asp:1" in o["rail"], o["rail"][:6])
    check("rail opens a real page, never an inherit-only one (the old __HIDE__-first problem)",
          "menu_APP:APP_Installation.asp:1" in o["rail"] and "menu_Setting:Advanced_OperationMode_Content.asp:1" in o["rail"], [x for x in o["rail"] if x.startswith("menu_APP") or x.startswith("menu_Setting")])
    # 2026-10-24 (owner): USB Application first, USB Disks last
    check("USB Applications: USB Application is the first tab and USB Disks the last",
          rt["menu_APP"][0] == "APP_Installation.asp" and rt["menu_APP"][-1] == "Reaper_USB.asp", rt["menu_APP"])

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
