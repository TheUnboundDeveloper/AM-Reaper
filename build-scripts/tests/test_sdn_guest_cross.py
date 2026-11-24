#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Network page: the two guest-path switches and the Firewall page zone switch (image 2, 2026-11-19).

WHY THIS EXISTS. Guest isolation (rc/reaper_guest.c) closes guest / IoT / VLAN networks to the main network. The
owner-approved opt-ins live on the stock Network page (www/sysdep/FUNCTION/SDN/SDN/sdn.js), in the edit panel below
Access Intranet: "Reach these main-network devices" (apgN_rg_devs, reserved devices only, at most 16) and "Device
discovery with the main network" (apgN_rg_mdns, presets + service types, at most 16 types). A save that changes only
those two keys sends the light rc service restart_reaper_guest instead of the radio / network restart. The Firewall
page's zones tab has one global switch, reaper_fw_zpol_guest. The stock page is large and changes with every GPL
drop, so the pins below hold where the rows are built (own wrappers, outside the wifi_settings group and every
portal-type block), when they are shown (router mode, own subnet, not LEGACY / MAINFH / MAINBH, not a portal, not
while paired with Main), how they are saved and cleared, and the tokens (25 packs, quote-safe, in backtick templates).

WHAT IT RUNS. The pure helpers (reaper_gc_*) are cut out of sdn.js and run under node: the service-picker serialiser
and validator, the stored-value parser, the device list builder from a dhcp_staticlist string (reservations on / off,
router address, AiMesh nodes, duplicates), the label rule, and the "only these keys changed -> restart_reaper_guest"
decision.

Exit 0 pass, 1 fail, 77 skipped (no router source tree; without node the pins still run and a pass exits 77)."""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
SJ = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js") if SRC else ""
FWP = os.path.join(SRC, "www", "Reaper_Firewall.asp") if SRC else ""
if not SJ or not os.path.isfile(SJ) or not os.path.isfile(FWP):
    skip("no router source tree with www/sysdep/FUNCTION/SDN/SDN/sdn.js (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def read(p):
    return open(p, encoding="utf-8", errors="surrogateescape").read().replace("\r\n", "\n")

sj = read(SJ)
fw = read(FWP)

def between(s, a, b):
    i = s.find(a)
    if i < 0:
        return ""
    j = s.find(b, i + len(a))
    return s[i:j] if j > 0 else ""

# ---------------------------------------------------------------- storage: the apg_rl object and the nvram keys
attr = between(sj, "var apg_rl_attr = function(){", "\n};")
check("apg_rl_attr carries rg_devs and rg_mdns, both empty by default",
      'this.rg_devs = "";' in attr and 'this.rg_mdns = "";' in attr)
check("get_apg_rl_list fetches apgN_rg_devs / apgN_rg_mdns with the other keys and decodes them",
      sj.count('prefix + _idx + "_11be", prefix + _idx + "_disabled", prefix + _idx + "_rg_devs", prefix + _idx + "_rg_mdns"], true);') == 1
      and 'apg_profile.rg_devs = decodeURIComponent(apg_info[prefix + _idx + "_rg_devs"] || "");' in sj
      and 'apg_profile.rg_mdns = decodeURIComponent(apg_info[prefix + _idx + "_rg_mdns"] || "");' in sj)
newapg = between(sj, "function get_new_apg_rl(_ap_prefix){", "return (JSON.parse(JSON.stringify(apg_profile)));")
check("get_new_apg_rl: a new network starts with no guest paths",
      'apg_profile.rg_devs = "";' in newapg and 'apg_profile.rg_mdns = "";' in newapg)
parse = between(sj, "function parse_apg_rl_to_apgX_rl(_apg_rl, _prefix){", "\n}\n")
check("parse_apg_rl_to_apgX_rl writes every apg_rl key as apgN_<key> (so apgN_rg_devs / apgN_rg_mdns), never for apm",
      'result[prefix + apg_idx + "_" + nvram_key] = _apg_rl[key];' in parse
      and '!(prefix == "apm" && (nvram_key == "rg_devs" || nvram_key == "rg_mdns"))' in parse)
dl = sj.find('\t\t\t\tnvramSet_obj[ap_prefix + del_sdn_rl[0].apg_rl.apg_idx + "_disabled"] = "0";\n')
dblk = sj[dl:dl + 700] if dl > 0 else ""
check("delete clears both keys of the deleted apg index (the index is reused lowest-first)",
      sj.count("/* REAPER-GUEST-CROSS-DEL ") == 1 and dblk.find("/* REAPER-GUEST-CROSS-DEL ") > 0
      and 'nvramSet_obj["apg" + del_sdn_rl[0].apg_rl.apg_idx + "_rg_devs"] = "";' in dblk
      and 'nvramSet_obj["apg" + del_sdn_rl[0].apg_rl.apg_idx + "_rg_mdns"] = "";' in dblk
      and 'if(ap_prefix == "apg"){' in dblk)

# ---------------------------------------------------------------- the rows: built once, own wrappers, below Access Intranet
gen = between(sj, "\tfunction Get_Net_General_Container(){", "\tfunction Get_Net_Adv_Container(){")
rows = between(gen, "/* REAPER-GUEST-CROSS-ROWS (2026-11-19)", "/* REAPER-GUEST-CROSS-ROWS-END */")
ai = gen.find('$("<div>").attr({"data-slide_target": "access_intranet_cntr", "data-container": "access_intranet_cntr"}).hide().appendTo($net_mode_container);')
check("rows built once, in the edit panel's Network > General container, right below Access Intranet",
      sj.count("/* REAPER-GUEST-CROSS-ROWS (2026-11-19)") == 1 and rows != "" and 0 < ai < gen.find("/* REAPER-GUEST-CROSS-ROWS (2026-11-19)")
      and gen.find("/* REAPER-GUEST-CROSS-ROWS-END */") < gen.find("if(support_gaming){"))
check("each row has its own hidden wrapper on $net_mode_container (the portal-type .show() trap)",
      '$("<div>").attr({"id":"rg_devs_wrap"}).hide().appendTo($net_mode_container);' in rows
      and '$("<div>").attr({"id":"rg_mdns_wrap"}).hide().appendTo($net_mode_container);' in rows
      and "appendTo($rg_devs_wrap)" in rows and "appendTo($rg_mdns_wrap)" in rows)
check("the rows are not in the wifi_settings group (hidden for wired-only networks) nor in a portal-type block",
      "data-group" not in rows and "data-portal-type" not in rows)
check("the wizards do not get the rows (only the edit panel builds them)",
      sj.count('"id":"rg_devs_wrap"') == 1 and sj.count('"id":"rg_mdns_wrap"') == 1)
check("discovery: a switch revealing five presets, a free-entry field and the note; a note for Set AP Isolated",
      '"type":"switch", "id":"rg_mdns_enabled", "set_value":"off"' in rows and "$.each(reaper_gc_svc_ui()" in rows
      and '"id":"rg_mdns_extra"' in rows and ".html(`<#RSDN_24#>`)" in rows and ".html(`<#RSDN_25#>`).hide()" in rows
      and 'if($(this).attr("temp_disable") == "disabled")' in rows)
ui = between(sj, "function reaper_gc_svc_ui(){", "\n}\n")
check("preset labels: Printing translated, the brand names as they are",
      all(x in ui for x in ('{"k":"print", "t":`<#RSDN_26#>`}', '{"k":"airplay", "t":`AirPlay`}', '{"k":"cast", "t":`Google Cast`}',
                            '{"k":"homekit", "t":`HomeKit / Matter`}', '{"k":"audio", "t":`Spotify / Sonos`}')))

# ---------------------------------------------------------------- fill + gating
fl = sj.find("""	reaper_apiso_lan_fill(_obj, _profile_data);//REAPER-APISO-LAN-FILL (2026-11-19): after the switch, whose state it follows
	reaper_guest_cross_fill(_obj, _profile_data);//REAPER-GUEST-CROSS-FILL""")
_ai = sj.find("""		$(_obj).find("#access_intranet, [data-container='access_intranet_cntr']").remove();""")
_iso = sj.find("""	$(_obj).find("#ap_isolate").removeClass("off on").addClass((function(){""")
# 2026-11-22 field report: filled before the AP Isolation switch was set, the gate read the switch's built-in "on"
# and held discovery (with its AP Isolation note) on every network
check("filled once, after Access Intranet (whose Main Network tick it reads) and after the AP Isolation switch is set",
      fl > 0 and 0 < _ai < fl and 0 < _iso < fl and sj.count("reaper_guest_cross_fill(_obj, _profile_data);") == 1
      and sj.rfind("\nfunction ", 0, fl) + 1 == sj.rfind("function Update_Setting_Profile(_obj, _profile_data){", 0, fl))
fill = between(sj, "function reaper_guest_cross_fill(_obj, _profile_data){", "\nfunction reaper_guest_cross_gate(")
check("shown only in router mode, for a network with its own subnet, not LEGACY / MAINFH / MAINBH, not a portal",
      '(isSwMode("RT") || isSwMode("WISP"))' in fill and "!$.isEmptyObject(_profile_data.subnet_rl)" in fill
      and '["LEGACY", "MAINFH", "MAINBH"].indexOf(sdn_rl.sdn_name) == -1' in fill
      and 'String((sdn_rl.cp_idx == undefined || sdn_rl.cp_idx === "") ? "0" : sdn_rl.cp_idx) == "0"' in fill
      and "if(!supported){\n\t\t$devs_wrap.remove();\n\t\t$mdns_wrap.remove();\n\t\treturn;\n\t}" in fill)
check("the device list: dhcp_staticlist + dhcp_static_x + lan_ipaddr, AiMesh nodes from cfg_clientlist, 16-tick limit",
      'httpApi.nvramCharToAscii(["dhcp_staticlist"], true)' in fill and 'httpApi.nvramGet(["dhcp_static_x", "lan_ipaddr"], true)' in fill
      and "reaper_gc_node_macs((typeof cfg_clientlist == \"object\") ? cfg_clientlist : [])" in fill
      and '.find(".icon_checkbox.clicked").length >= 16' in fill and "show_customize_alert(`<#RSDN_29#>`)" in fill)
check("labels: the router's Name / Hostname hook (reaper_devnames) through reaper_gc_label; empty state and note",
      '"data":"reaper_devnames"' in fill and "reaper_gc_label(" in fill and ".html(`<#RSDN_22#>`)" in fill
      and ".html(`<#RSDN_21#>`)" in fill and "`<#RSDN_30#>`" in fill and "htmlEnDeCode.htmlEncode(_label)" in fill)
check("re-evaluated when the Portal tab's type changes (a portal hides both rows; review 2026-11-19)",
      '$ps.find("#select_portal_type").children("div").unbind("click.rgc").bind("click.rgc", function(){ reaper_guest_cross_gate($ps); });' in fill)
check("re-evaluated when Set AP Isolated or the Main Network tick changes (namespaced, after stock's handlers)",
      '$ps.find("#ap_isolate").unbind("click.rgc").bind("click.rgc"' in fill
      and "$ps.find(\"[data-container='access_intranet_cntr'] [sdn_idx='0'] > .cb_item_content_container\").unbind(\"click.rgc\").bind(\"click.rgc\"" in fill
      and fill.rstrip().endswith("\treaper_guest_cross_gate($ps);\n}"))
gate = between(sj, "function reaper_guest_cross_gate($ps){", "\nfunction reaper_guest_cross_mdns_switched(")
check("hidden while Access Intranet pairs the network with Main; discovery held (with its note) while Set AP Isolated is on",
      "const paired = $ps.find(\"[data-container='access_intranet_cntr'] [sdn_idx='0'] .icon_checkbox\").hasClass(\"clicked\");" in gate
      and 'const shown = reaper_gc_rows_shown(paired, $ps.find("#select_portal_type").children(".selected").attr("value"));' in gate
      and "$devs_wrap.toggle(shown);" in gate and "$mdns_wrap.toggle(shown);" in gate
      and 'const iso = $ps.find("#ap_isolate").hasClass("on");' in gate and '$sw.attr({"temp_disable":"disabled"})' in gate
      and '$mdns_wrap.find("#rg_mdns_iso_note").toggle(iso);' in gate and "resize_iframe_height();" in gate)
sw = between(sj, "function reaper_guest_cross_mdns_switched($ps, _on){", "\n}\n")
check("switching discovery on starts with Printing, AirPlay and Google Cast; resize + apply-button status after a click",
      '$.each(["print", "airplay", "cast"]' in sw and "resize_iframe_height();" in sw and "set_apply_btn_status($ps);" in sw)

# ---------------------------------------------------------------- save
ap = between(sj, "\t\t\tfunction apply_profile(){\n", "\n\t\t\t\t\thttpApi.nvramSet(nvramSet_obj, function(){")
check("apply_profile validates the picker before anything is saved",
      ap.startswith('\t\t\tfunction apply_profile(){\n\t\t\t\tif(validate_format_Wizard_Item($(_obj), "ALL") && reaper_guest_cross_valid($(_obj))){'))
ic, iv = ap.find("reaper_guest_cross_collect($(_obj), sdn_profile);"), ap.find('\t\t\t\t\tsdn_profile.sdn_rl.vpnc_idx = "0";')
check("the keys are read into apg_rl after Access Intranet is saved, before parse_apg_rl_to_apgX_rl",
      0 < ap.find("sdn_profile.sdn_access_rl.push(") < ic < iv < ap.find("var apgX_rl = parse_apg_rl_to_apgX_rl(sdn_profile.apg_rl, ap_prefix);"))
isv = ap.find("if(reaper_guest_cross_save(nvramSet_obj, sdn_profile.apg_rl.apg_idx)){\n\t\t\t\t\t\tshowLoading_status = get_showLoading_status(nvramSet_obj.rc_service);\n\t\t\t\t\t}")
check("the light-restart decision runs on the complete nvramSet_obj (after apgX / cpX), before the save; the wait follows it",
      0 < ap.find("$.extend(nvramSet_obj, cpX_rl);") < isv < ap.find("if(!httpApi.app_dataHandler){"))
save = between(sj, "function reaper_guest_cross_save(_nvramSet_obj, _apg_idx){", "\n}\n")
check("reaper_guest_cross_save: compares every written key with nvram and only then sends restart_reaper_guest",
      "httpApi.nvramCharToAscii(keys, true)" in save and 0 < save.find("const now = httpApi.nvramCharToAscii(cross, true);") < save.find("httpApi.nvramCharToAscii(keys, true)") and"reaper_gc_only_cross(_nvramSet_obj, cur, _apg_idx)" in save
      and '_nvramSet_obj.rc_service = "restart_reaper_guest;";' in save and "if(got == undefined || got.isError)" in save)
col = between(sj, "function reaper_guest_cross_collect($ps, _sdn_profile){", "\n}\n")
check("a network saved as a portal keeps the stored values (nothing collected)",
      'if(!reaper_gc_rows_shown(false, $ps.find("#select_portal_type").children(".selected").attr("value")))\n\t\treturn;' in col
      and col.find("reaper_gc_rows_shown(") < col.find("const $devs_wrap"))
check("a hidden row (paired, unsupported) or a failed reservation read keeps the stored value",
      '$devs_wrap.css("display") != "none" && $devs_wrap.attr("data-rg-failed") != "1"' in col
      and "if(reaper_guest_cross_mdns_live($ps)){" in col and "_sdn_profile.apg_rl.rg_devs = reaper_gc_devs_serialise(macs);" in col)
check("the whole stock file stays ASCII", all(ord(ch) < 128 for ch in sj))

# ---------------------------------------------------------------- Firewall page: the zones-tab switch
zones = between(fw, '<div class="tab" id="tab_zones">', '<div class="tab" id="tab_egress">')
check("Firewall page: one switch bound to reaper_fw_zpol_guest, in the zones tab, with its hint and Apply",
      fw.count('data-nv="reaper_fw_zpol_guest"') == 1
      and '<span class="tg" data-nv="reaper_fw_zpol_guest" id="zg_en" role="switch" aria-label="<#RFW_420#>"></span>' in zones
      and '<p class="note"><#RFW_421#></p>' in zones and '<button class="btn ghost sm" id="zg_apply"><#RFW_62#></button>' in zones)
check("Firewall page: the stored value seeds the switch (NV) and Apply saves it through fwApply (restart_firewall)",
      fw.count('  reaper_fw_zpol_guest:<% nvram_get_js("reaper_fw_zpol_guest"); %>,\n') == 1
      and fw.count("$('zg_apply').onclick=function(){fwApply({reaper_fw_zpol_guest:tgGet($('zg_en'))});};") == 1
      and '<input type="hidden" name="action_script" value="restart_firewall">' in fw)
check("Firewall page additions are ASCII",
      all(ord(ch) < 128 for ch in between(fw, "<!-- REAPER-ZPOL-GUEST (2026-11-19)", "<#RFW_62#></button></div>")))

# ---------------------------------------------------------------- tokens
KEYS = ["RSDN_%d" % i for i in range(20, 31)] + ["RFW_420", "RFW_421"]
_www = os.path.join(SRC, "www")
_packs = sorted(f for f in os.listdir(_www) if re.match(r"^[A-Z]{2}\.dict$", f))
_bad, _lens = [], set()
for _f in _packs:
    _t = read(os.path.join(_www, _f))
    _lens.add(_t.count("\n"))
    for k in KEYS:
        _m = re.findall(r"^" + k + r"=(.*)$", _t, re.M)
        if len(_m) != 1 or _m[0].strip() == "" or any(x in _m[0] for x in ('"', "'", "`", "\\", "${", "</")):
            _bad.append(_f + ":" + k)
check("%d new tokens once in all %d packs, non-empty, quote-safe; packs in lockstep" % (len(KEYS), len(_packs)),
      len(_packs) == 25 and not _bad and len(_lens) == 1, (_bad[:10], _lens))
_sj_bad = [k for k in KEYS if k.startswith("RSDN_") and (sj.count("<#%s#>" % k) == 0 or sj.count("<#%s#>" % k) != sj.count("`<#%s#>`" % k))]
check("every RSDN token is used in sdn.js, each time alone in a backtick template", not _sj_bad, _sj_bad)
check("RSDN_3..19 stay free (reserved for the deferred-restart design)",
      not any(("<#RSDN_%d#>" % i) in sj for i in range(3, 20)))
check("RFW_420 / RFW_421 are used on the Firewall page", "<#RFW_420#>" in fw and "<#RFW_421#>" in fw)
_en = read(os.path.join(_www, "EN.dict"))
def en(k):
    m = re.search(r"^" + k + r"=(.*)$", _en, re.M)
    return m.group(1) if m else ""
check("English: the device-list note says guests start connections to the ticked devices only, never the router",
      en("RSDN_21").startswith("Guests on this network may start connections to the ticked devices only, never to the router")
      and "The ticked devices cannot start connections to guests." in en("RSDN_21"))
check("English: discovery only shows devices; the switch text names the main network and isolated guest networks",
      "Discovery only shows devices" in en("RSDN_24") and en("RSDN_23") == "Device discovery with the main network"
      and en("RFW_420") == "Zone policies may open one-way paths from the main network into isolated guest networks"
      and "guest networks stay closed to each other" in en("RFW_421"))

# ---------------------------------------------------------------- the pure helpers under node
NAMES = ["reaper_gc_svc_types", "reaper_gc_mdns_parse", "reaper_gc_mdns_serialise", "reaper_gc_devs_parse",
         "reaper_gc_devs_serialise", "reaper_gc_label", "reaper_gc_reserved", "reaper_gc_node_macs", "reaper_gc_only_cross",
         "reaper_gc_rows_shown"]
cut = []
for n in NAMES:
    m = re.search(r"^function " + n + r"\(.*?^\}\n", sj, re.S | re.M)
    check("helper %s is a block the test can cut out" % n, m is not None)
    if m:
        cut.append(m.group(0))
for n, body in zip(NAMES, cut):
    check("helper %s takes no page state (no $, httpApi, document)" % n,
          not re.search(r"\$\(|\$\.|httpApi|document\.|window\.", body), n)

if len(cut) != len(NAMES):
    pass
elif not shutil.which("node"):
    print("note: no node on the host - the helper runs are skipped")
else:
    HARNESS = r"""
FNS
const ALL = ["print","airplay","cast","homekit","audio"];
const ser = reaper_gc_mdns_serialise, par = reaper_gc_mdns_parse;
const o = {};
o.sizes = reaper_gc_svc_types().map(p => [p[0], p[1]]);
o.def = ser(["print","airplay","cast"], "");
o.order = ser(["cast","print"], "");
o.free = ser([], "_Foo-1._TCP, _bar._udp");
o.covered = ser(["print"], "_ipp._tcp _x._tcp,_x._tcp");
o.empty = ser([], " , ");
o.nounder = ser([], "ipp._tcp");
o.sctp = ser([], "_a._sctp");
o.max16 = ser(ALL, "_a._tcp,_b._tcp");
o.over16 = ser(ALL, "_a._tcp,_b._tcp,_c._tcp");
o.name32 = ser([], "_" + "a".repeat(32) + "._tcp");
o.name33 = ser([], "_" + "a".repeat(33) + "._tcp");
let longs = []; for(let i = 0; i < 7; i++) longs.push("_" + String.fromCharCode(97 + i).repeat(32) + "._udp");
o.len255 = ser([], longs.join(","));
o.parse = par("print,airplay,_x._tcp,bogus,PRINT, _y._udp ,_y._udp");
o.parse_empty = par("");
const v = "print,cast,_x._udp"; const pv = par(v);
o.round = ser(pv.presets, pv.extra.join(", "));
o.dser = reaper_gc_devs_serialise(["aa:bb:cc:dd:ee:01", "AA:BB:CC:DD:EE:01", "bad", "11:22:33:44:55:66"]);
o.dparse = reaper_gc_devs_parse("<AA:BB:CC:DD:EE:01><11:22:33:44:55:66>,aa:bb:cc:dd:ee:01");
let many = []; for(let i = 0; i < 20; i++) many.push("02:00:00:00:00:" + (16 + i).toString(16));
o.dcap = reaper_gc_devs_parse(reaper_gc_devs_serialise(many)).length;
o.dempty = reaper_gc_devs_serialise([]);
const set = {"action_mode":"apply", "rc_service":"restart_wireless;restart_sdn 3;", "apg3_ssid":"Guest", "apg3_rg_devs":"<AA:BB:CC:DD:EE:01",
  "apg3_rg_mdns":"print", "sdn_rl":"<3>Guest>1", "apg3_bw_limit":5};
const cur = {"apg3_ssid":"Guest", "apg3_rg_devs":"", "apg3_rg_mdns":"print", "sdn_rl":"<3>Guest>1", "apg3_bw_limit":"5"};
o.only = reaper_gc_only_cross(set, cur, "3");
o.other = reaper_gc_only_cross(set, Object.assign({}, cur, {"apg3_ssid":"Old"}), "3");
o.same = reaper_gc_only_cross(set, Object.assign({}, cur, {"apg3_rg_devs":"<AA:BB:CC:DD:EE:01"}), "3");
o.badidx = reaper_gc_only_cross(set, cur, "x");
o.noidx = reaper_gc_only_cross(set, cur, "");
o.wrongnet = reaper_gc_only_cross(set, cur, "4");
o.newkey = reaper_gc_only_cross(Object.assign({}, set, {"apg3_rg_devs":"", "apg3_rg_mdns":"cast"}), cur, "3");
const stl = "<AA:BB:CC:DD:EE:01>192.168.50.10>>printer<aa:bb:cc:dd:ee:02>192.168.50.11>8.8.8.8>tv" +
  "<AA:BB:CC:DD:EE:03>192.168.50.1>>router<AA:BB:CC:DD:EE:04>192.168.50.12>>node<zz>1.2.3.4>>bad" +
  "<AA:BB:CC:DD:EE:01>192.168.50.13>>dup<AA:BB:CC:DD:EE:05>notip>>x<AA:BB:CC:DD:EE:07>192.168.50.20";
const names = {"AA:BB:CC:DD:EE:01":{"n":"Office Printer","h":"HP123"}, "aa:bb:cc:dd:ee:02":{"n":"","h":"LivingRoom-TV"}};
o.off = reaper_gc_reserved(stl, "0", [], names, "192.168.50.1");
o.on = reaper_gc_reserved(stl, "1", ["aa:bb:cc:dd:ee:04"], names, "192.168.50.1").map(d => [d.mac, d.ip, d.label]);
o.nonames = reaper_gc_reserved(stl, "1", [], {}, "192.168.50.1").map(d => [d.mac, d.label]);
o.nolist = reaper_gc_reserved(undefined, "1", [], {}, "192.168.50.1");
o.nodes = reaper_gc_node_macs([{"mac":"aa:bb:cc:dd:ee:04", "ap2g":"AA:BB:CC:DD:EE:05", "wired_mac":["aa:bb:cc:dd:ee:06", "x"],
  "alias":"Node", "ip":"192.168.50.2", "online":"1"}, null, "junk"]);
o.nodes_bad = reaper_gc_node_macs("x");
o.shown = [reaper_gc_rows_shown(false, "0"), reaper_gc_rows_shown(false, undefined), reaper_gc_rows_shown(false, ""),
  reaper_gc_rows_shown(true, "0"), reaper_gc_rows_shown(false, "2"), reaper_gc_rows_shown(false, "4"), reaper_gc_rows_shown(true, "2")];
console.log(JSON.stringify(o));
"""
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "h.js"); open(f, "w", encoding="utf-8").write(HARNESS.replace("FNS", "\n".join(cut)))
        r = subprocess.run(["node", f], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    try:
        o = json.loads(r.stdout.strip().split("\n")[-1])
    except Exception:
        o = None
    check("the helpers run under node", o is not None, r.stdout + r.stderr)
    if o is not None:
        check("presets expand as the rc contract says (print 5, airplay 2, cast 1, homekit 4, audio 2)",
              o["sizes"] == [["print", ["_ipp._tcp", "_ipps._tcp", "_printer._tcp", "_pdl-datastream._tcp", "_uscan._tcp"]],
                             ["airplay", ["_airplay._tcp", "_raop._tcp"]], ["cast", ["_googlecast._tcp"]],
                             ["homekit", ["_hap._tcp", "_hap._udp", "_matter._tcp", "_matterc._udp"]],
                             ["audio", ["_spotify-connect._tcp", "_sonos._tcp"]]], o["sizes"])
        check("the switch-on default is print,airplay,cast (8 types)", o["def"] == {"ok": True, "value": "print,airplay,cast", "types": 8}, o["def"])
        check("presets are stored in a fixed order", o["order"]["value"] == "print,cast", o["order"])
        check("free entries: lower-cased, comma or space separated", o["free"] == {"ok": True, "value": "_foo-1._tcp,_bar._udp", "types": 2}, o["free"])
        check("an entry a chosen preset covers, and a repeat, are dropped", o["covered"] == {"ok": True, "value": "print,_x._tcp", "types": 6}, o["covered"])
        check("nothing chosen is refused", o["empty"]["ok"] is False, o["empty"])
        check("a malformed entry is refused and named", o["nounder"] == {"ok": False, "bad": "ipp._tcp"} and o["sctp"]["ok"] is False, (o["nounder"], o["sctp"]))
        check("16 types after expansion pass, 17 are refused", o["max16"]["ok"] is True and o["max16"]["types"] == 16 and o["over16"]["ok"] is False, (o["max16"], o["over16"]))
        check("a name of 32 characters passes, 33 are refused", o["name32"]["ok"] is True and o["name33"]["ok"] is False)
        check("a value over 255 characters (CKN_STR256) is refused", o["len255"]["ok"] is False, o["len255"])
        check("stored value -> picker: presets and valid types kept, junk and repeats dropped",
              o["parse"] == {"presets": ["print", "airplay"], "extra": ["_x._tcp", "_y._udp"]} and o["parse_empty"] == {"presets": [], "extra": []}, o["parse"])
        check("parse then serialise gives the stored value back", o["round"]["value"] == "print,cast,_x._udp", o["round"])
        check("devices are stored <MAC<MAC (upper case, no duplicates, no junk) - the form rc/reaper_guest.c splits on '<'",
              o["dser"] == "<AA:BB:CC:DD:EE:01<11:22:33:44:55:66" and o["dempty"] == "", o["dser"])
        check("the device parser takes either separator and keeps at most 16",
              o["dparse"] == ["AA:BB:CC:DD:EE:01", "11:22:33:44:55:66"] and o["dcap"] == 16, (o["dparse"], o["dcap"]))
        check("only the guest-path keys changed -> restart_reaper_guest", o["only"] is True and o["newkey"] is True)
        check("any other change, no change, or a bad index -> keep stock's restart",
              o["other"] is False and o["same"] is False and o["badidx"] is False and o["noidx"] is False and o["wrongnet"] is False,
              (o["other"], o["same"], o["badidx"], o["noidx"], o["wrongnet"]))
        check("reservations off (dhcp_static_x 0) -> no device offered", o["off"] == [] and o["nolist"] == [], o["off"])
        check("reservations on: the router address, an AiMesh node, malformed rows and a repeated MAC are left out; Name, then Hostname",
              o["on"] == [["AA:BB:CC:DD:EE:01", "192.168.50.10", "Office Printer"], ["AA:BB:CC:DD:EE:02", "192.168.50.11", "LivingRoom-TV"],
                          ["AA:BB:CC:DD:EE:07", "192.168.50.20", "AA:BB:CC:DD:EE:07"]], o["on"])
        check("without the router's names: the reservation name, else the MAC",
              o["nonames"] == [["AA:BB:CC:DD:EE:01", "printer"], ["AA:BB:CC:DD:EE:02", "tv"], ["AA:BB:CC:DD:EE:04", "node"],
                               ["AA:BB:CC:DD:EE:07", "AA:BB:CC:DD:EE:07"]], o["nonames"])
        check("AiMesh node MACs: every MAC-shaped field of a node entry, upper case",
              o["nodes"] == ["AA:BB:CC:DD:EE:04", "AA:BB:CC:DD:EE:05", "AA:BB:CC:DD:EE:06"] and o["nodes_bad"] == [], o["nodes"])
        check("rows shown: not paired and portal type 0 / none; hidden when paired with Main or a portal type (2 Free WiFi, 4 Message Board) is chosen",
              o["shown"] == [True, True, True, False, False, False, False], o["shown"])

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  " + f)
if fails:
    sys.exit(1)
if not shutil.which("node"):
    skip("no node on the host (the pins passed; the helper runs did not happen)")
sys.exit(0)
