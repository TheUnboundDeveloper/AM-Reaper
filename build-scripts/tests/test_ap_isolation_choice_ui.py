#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AP Isolation as a choice: the page side (owner decision 2026-11-19).

WHY THIS EXISTS. AP Isolation used to be one switch per network. The owner made it a choice on every network that has
it: Off / "Wi-Fi only" (the default: Wi-Fi clients cannot reach each other, wired devices stay reachable) / "Wi-Fi and
LAN ports" (the LAN ports are kept apart too, from each other and from Wi-Fi; devices behind one external switch still
reach each other; AiMesh backhaul ports never are). The switch keeps its stock keys (apmN_ap_isolate for the main
network, apgN_ap_isolate for the others); the choice is reaper_ap_isolate_lan for the main network and every network
riding its subnet (they share its bridge), apgN_ap_isolate_lan for a network with its own subnet ("1" = Wi-Fi and LAN
ports, anything else = Wi-Fi only; rc/lan.c REAPER-BRPORT-WIRED reads them, test_main_brport_wired_open.py). The only
page that shows the switch is the stock Network page (www/sysdep/FUNCTION/SDN/SDN/sdn.js): the stock Wireless >
Professional page does not ship (Reaper_WiFiSettings.asp replaces it and carries no AP isolation control). The pins
below hold where the choice row is built (its own wrapper under the switch: the outer one in the wifi_settings group,
the inner one following the switch alone), how it is filled, saved and cleared, the LAN page's VLAN tab seeding the
key, and the language tokens (the label back to "AP Isolation"; the new row's tokens in 25 packs, quote-safe).

WHAT IT RUNS. The pure helpers (reaper_apiso_lan_global / _shown / _next) are cut out of sdn.js and run under node,
with reaper_gc_only_cross (a changed choice must keep the stock restart, never the light restart_reaper_guest).

Exit 0 pass, 1 fail, 77 skipped (no router source tree; without node the pins still run and a pass exits 77)."""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
SJ = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js") if SRC else ""
VL = os.path.join(SRC, "www", "Reaper_VLAN.asp") if SRC else ""
if not SJ or not os.path.isfile(SJ) or not os.path.isfile(VL):
    skip("no router source tree with www/sysdep/FUNCTION/SDN/SDN/sdn.js (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def read(p):
    return open(p, encoding="utf-8", errors="surrogateescape").read().replace("\r\n", "\n")

def between(s, a, b):
    i = s.find(a)
    if i < 0:
        return ""
    j = s.find(b, i + len(a))
    return s[i:j] if j > 0 else ""

sj = read(SJ)
vl = read(VL)
www = os.path.join(SRC, "www")

# ---------------------------------------------------------------- where the option lives
mk = read(os.path.join(www, "Makefile")) if os.path.isfile(os.path.join(www, "Makefile")) else ""
check("the stock Wireless > Professional page does not ship (the Network page is the one place with the switch)",
      "rm -f $(INSTALLDIR)/www/Advanced_Wireless_Content.asp $(INSTALLDIR)/www/Advanced_WAdvanced_Content.asp" in mk)
wfs = os.path.join(www, "Reaper_WiFiSettings.asp")
check("Wireless > Settings carries no AP isolation control",
      os.path.isfile(wfs) and "ap_isolate" not in read(wfs) and "IsolateAP" not in read(wfs))

# ---------------------------------------------------------------- markers
for mrk in ("/* REAPER-APISO-LAN-ROW (2026-11-19", "/* REAPER-APISO-LAN-ROW-END */", "//REAPER-APISO-LAN-FILL",
            "//REAPER-APISO-LAN-COLLECT", "//REAPER-APISO-LAN-DEL", "/* REAPER-APISO-LAN-BEGIN ", "/* REAPER-APISO-LAN-END */"):
    check("sdn.js marker %s once" % mrk, sj.count(mrk) == 1, sj.count(mrk))
for mrk in ("/* REAPER-APISO-LAN-VLAN (2026-11-19)", "/* REAPER-APISO-LAN-VLAN-DEL (2026-11-19) */",
            "/* REAPER-RG-VLAN (2026-11-19)", "/* REAPER-RG-VLAN-DEL (2026-11-19) */"):
    check("Reaper_VLAN.asp marker %s once" % mrk, vl.count(mrk) == 1, vl.count(mrk))

# ---------------------------------------------------------------- storage: apg_rl and the nvram keys
attr = between(sj, "var apg_rl_attr = function(){", "\n};")
check("apg_rl_attr carries ap_isolate_lan, empty by default", '\tthis.ap_isolate_lan = "";' in attr)
check("get_apg_rl_list fetches apgN_ap_isolate_lan beside apgN_ap_isolate and decodes it",
      sj.count('prefix + _idx + "_expiretime",prefix + _idx + "_ap_isolate", prefix + _idx + "_ap_isolate_lan",\n') == 1
      and sj.count('apg_profile.ap_isolate_lan = decodeURIComponent(apg_info[prefix + _idx + "_ap_isolate_lan"] || "");') == 1)
newapg = between(sj, "function get_new_apg_rl(_ap_prefix){", "return (JSON.parse(JSON.stringify(apg_profile)));")
check("get_new_apg_rl: a new network starts at Wi-Fi only", 'apg_profile.ap_isolate_lan = "0";' in newapg)
parse = between(sj, "function parse_apg_rl_to_apgX_rl(_apg_rl, _prefix){", "\n}\n")
check("parse_apg_rl_to_apgX_rl writes apgN_ap_isolate_lan, never apmN_ap_isolate_lan (the main network's is global)",
      'result[prefix + apg_idx + "_" + nvram_key] = _apg_rl[key];' in parse
      and '&& !(prefix == "apm" && nvram_key == "ap_isolate_lan")' in parse)
dl = sj.find('\t\t\t\tnvramSet_obj[ap_prefix + del_sdn_rl[0].apg_rl.apg_idx + "_disabled"] = "0";\n')
dblk = between(sj[dl:], 'if(ap_prefix == "apg"){', "\n\t\t\t\t}\n") if dl > 0 else ""
check("delete clears apgN_ap_isolate_lan of the deleted apg index (inside the apg-only clearing)",
      'nvramSet_obj["apg" + del_sdn_rl[0].apg_rl.apg_idx + "_ap_isolate_lan"] = "";//REAPER-APISO-LAN-DEL' in dblk, dblk)

# ---------------------------------------------------------------- the row: under the switch, own wrappers
sw = ('\t\t\tvar ap_iso_parm = {"title":"<#WLANConfig11b_x_IsolateAP_itemname#>", "type":"switch", "id":"ap_isolate", "openHint":"3_5"};\n'
      '\t\t\tGet_Component_Switch(ap_iso_parm).attr({"data-group":"wifi_settings"}).appendTo($net_mode_container);\n')
rows = between(sj, "/* REAPER-APISO-LAN-ROW (2026-11-19", "/* REAPER-APISO-LAN-ROW-END */")
check("the row is built right below the AP Isolation switch, before the IPv6 rows",
      sj.count(sw) == 1 and sj.find(sw) + len(sw) == sj.find("\t\t\t/* REAPER-APISO-LAN-ROW (2026-11-19")
      and 0 < sj.find("/* REAPER-APISO-LAN-ROW-END */") < sj.find('if(isSupport("ipv6")){', sj.find(sw)))
check("outer wrapper in the wifi_settings group (hidden with the switch on a wired-only network)",
      '$("<div>").attr({"id":"ap_iso_lan_wrap", "data-group":"wifi_settings"}).appendTo($net_mode_container);' in rows)
check("inner wrapper hidden at build, holding the select and the note (showing the group never shows it)",
      '$("<div>").attr({"id":"ap_iso_lan_inner"}).hide().appendTo($ap_iso_lan_wrap);' in rows
      and "Get_Component_Custom_Select(ap_iso_lan_parm).appendTo($ap_iso_lan_inner);" in rows
      and ".html(`<#RSDN_34#>`).appendTo($ap_iso_lan_inner);" in rows)
check("the select: title RSDN_31, id ap_isolate_lan, Wi-Fi only = 0 (default), Wi-Fi and LAN ports = 1",
      'const ap_iso_lan_parm = {"title":`<#RSDN_31#>`, "id":"ap_isolate_lan", "options":[{"text":`<#RSDN_32#>`, "value":"0"}, '
      '{"text":`<#RSDN_33#>`, "value":"1"}], "set_value":"0"};' in rows)
check("the row is not a portal-type block and has no need_check field (nothing to validate while hidden)",
      "data-portal-type" not in rows and "need_check" not in rows)
check("the row and the helper block are ASCII",
      all(ord(c) < 128 for c in rows + between(sj, "/* REAPER-APISO-LAN-BEGIN ", "/* REAPER-APISO-LAN-END */")))

# ---------------------------------------------------------------- fill / gate / collect
fillset = ('\t$(_obj).find("#ap_isolate").removeClass("off on").addClass((function(){\n'
           '\t\treturn ((_profile_data.apg_rl.ap_isolate == "1") ? "on" : "off");\n\t})());\n'
           '\treaper_apiso_lan_fill(_obj, _profile_data);//REAPER-APISO-LAN-FILL')
check("the fill runs right after the switch is set from apg_rl.ap_isolate", sj.count(fillset) == 1)
blk = between(sj, "/* REAPER-APISO-LAN-BEGIN ", "/* REAPER-APISO-LAN-END */")
fill = between(blk, "function reaper_apiso_lan_fill(_obj, _profile_data){", "\n}\n")
check("fill: no switch, no apg_rl or the AiMesh backhaul network -> the row is removed",
      '$ps.find("#ap_isolate").length == 0 || $.isEmptyObject(_profile_data.apg_rl) || sdn_rl.sdn_name == "MAINBH"' in fill
      and "$wrap.remove();" in fill)
check("fill: the main network (and its subnet) reads reaper_ap_isolate_lan, another network its apg_rl value",
      'const n = httpApi.nvramGet(["reaper_ap_isolate_lan"], true);' in fill and "reaper_apiso_lan_global(sdn_rl)" in fill
      and 'cur = (apg_rl.ap_isolate_lan == undefined) ? "" : String(apg_rl.ap_isolate_lan);' in fill)
check("fill: the stored value is kept on the wrapper, shown, and the switch re-gates the row (namespaced handler)",
      '$wrap.attr({"data-apiso-cur":cur});' in fill and "reaper_apiso_lan_set($wrap, cur);" in fill
      and '$ps.find("#ap_isolate").unbind("click.apiso").bind("click.apiso", function(){ reaper_apiso_lan_gate($ps); });' in fill
      and fill.rstrip().endswith("reaper_apiso_lan_gate($ps);"))
gate = between(blk, "function reaper_apiso_lan_gate($ps){", "\n}\n")
check("gate: the inner wrapper follows the switch alone",
      '$ps.find("#ap_iso_lan_inner").toggle($ps.find("#ap_isolate").hasClass("on"));' in gate)
coll = ('\t\t\t\t\t\tsdn_profile.apg_rl.ap_isolate = $(_obj).find("#ap_isolate").hasClass("on") ? "1" : "0";\n'
        '\t\t\t\t\t\treaper_apiso_lan_collect($(_obj), sdn_profile, nvramSet_obj);//REAPER-APISO-LAN-COLLECT')
check("the save collects the choice right after the stock switch value", sj.count(coll) == 1)
col = between(blk, "function reaper_apiso_lan_collect($ps, _sdn_profile, _nvramSet_obj){", "\n}\n")
check("collect: switch off keeps the stored choice; main network -> reaper_ap_isolate_lan only when it changes; "
      "else apg_rl.ap_isolate_lan",
      'if(!$ps.find("#ap_isolate").hasClass("on"))\n\t\treturn;' in col
      and 'reaper_apiso_lan_next(cur, $wrap.find("#select_ap_isolate_lan").children(".selected").attr("value"))' in col
      and "if(next !== cur)\n\t\t\t_nvramSet_obj.reaper_ap_isolate_lan = next;" in col
      and "_sdn_profile.apg_rl.ap_isolate_lan = next;" in col)
check("the light restart stays for the two guest-path keys only (a changed choice keeps restart_wireless;restart_sdn N;)",
      'const cross = ["apg" + _apg_idx + "_rg_devs", "apg" + _apg_idx + "_rg_mdns"];' in sj
      and "_nvramSet_obj.rc_service = \"restart_reaper_guest;\";" in sj and "restart_reaper_guest" not in blk.replace(
          "the light\n   restart_reaper_guest does not", ""))

# ---------------------------------------------------------------- the LAN page's VLAN tab
add = between(vl, "q('b_add').addEventListener('click', function(){", "\n});\n")
dele = between(vl, "function del(vidx){", "\n}\n")
check("VLAN tab: a network it creates gets apgN_ap_isolate_lan 0 (an index may be a deleted network's)",
      vl.count("  o[p + 'maclist'] = ''; o[p + 'iot_max_cmpt'] = ''; o[p + '11be'] = '0';\n  o[p + 'ap_isolate_lan'] = '0';") == 1
      and "o[p + 'ap_isolate_lan'] = '0';" in add)
check("VLAN tab: a network it creates starts with no guest paths (apgN_rg_devs / apgN_rg_mdns empty)",
      vl.count("  o[p + 'rg_devs'] = ''; o[p + 'rg_mdns'] = '';") == 1 and "o[p + 'rg_devs'] = ''; o[p + 'rg_mdns'] = '';" in add
      and add.find("o[p + 'rg_devs']") < add.find("nvSet(o);"))
check("VLAN tab: deleting a network clears its apgN_ap_isolate_lan, apgN_rg_devs and apgN_rg_mdns (never apg0)",
      vl.count("  if (s) o['apg' + s.f[5] + '_enable'] = '0';\n  if (s && +s.f[5] > 0) o['apg' + s.f[5] + '_ap_isolate_lan'] = '';") == 1
      and "  if (s && +s.f[5] > 0){ o['apg' + s.f[5] + '_rg_devs'] = ''; o['apg' + s.f[5] + '_rg_mdns'] = ''; }" in dele
      and dele.find("_rg_mdns'] = ''") < dele.find("nvSet(o"))

# ---------------------------------------------------------------- tokens
KEYS = ["RSDN_31", "RSDN_32", "RSDN_33", "RSDN_34"]
packs = sorted(f for f in os.listdir(www) if re.match(r"^[A-Z]{2}\.dict$", f))
bad, lens, vals = [], set(), {}
for f in packs:
    t = read(os.path.join(www, f))
    lens.add(t.count("\n"))
    vals[f] = {}
    for k in KEYS + ["WLANConfig11b_x_IsolateAP_itemname", "RSDN_25", "RTWK_48"]:
        m = re.findall(r"^" + k + r"=(.*)$", t, re.M)
        vals[f][k] = m[0] if len(m) == 1 else None
        if len(m) != 1 or m[0].strip() == "" or any(x in m[0] for x in ('"', "'", "`", "\\", "${", "</")):
            bad.append(f + ":" + k)
check("RSDN_31..34 (and the three renamed keys) once in all %d packs, non-empty, quote-safe; packs in lockstep" % len(packs),
      len(packs) == 25 and not bad and len(lens) == 1, (bad[:10], lens))
sj_bad = [k for k in KEYS if sj.count("<#%s#>" % k) != 1 or sj.count("`<#%s#>`" % k) != 1]
check("each new token is used once in sdn.js, alone in a backtick template", not sj_bad, sj_bad)
en = vals.get("EN.dict", {})
check("English: the label is AP Isolation again; the row reads Isolate: Wi-Fi only / Wi-Fi and LAN ports",
      en.get("WLANConfig11b_x_IsolateAP_itemname") == "AP Isolation" and en.get("RSDN_31") == "Isolate"
      and en.get("RSDN_32") == "Wi-Fi only" and en.get("RSDN_33") == "Wi-Fi and LAN ports")
check("English: the note names both choices, the external switch and AiMesh backhaul; plain ASCII",
      (en.get("RSDN_34") or "").startswith("Wi-Fi only: wireless devices cannot reach each other; wired devices stay reachable. "
                                           "Wi-Fi and LAN ports: ")
      and "external switch" in (en.get("RSDN_34") or "") and "AiMesh backhaul ports are never isolated" in (en.get("RSDN_34") or "")
      and all(ord(c) < 128 for k in KEYS for c in (en.get(k) or "x")))
check("English: the discovery note and the Tweaks text say AP Isolation",
      en.get("RSDN_25") == "Not available while AP Isolation is on for this network."
      and "Networks with AP Isolation on, networks without intranet access" in (en.get("RTWK_48") or ""))
paren = []
for f, v in vals.items():
    lab = v.get("WLANConfig11b_x_IsolateAP_itemname") or ""
    if not lab or re.search(r"[()（）]", lab):
        paren.append(f + ":label")
    for k in ("RSDN_25", "RTWK_48"):
        if re.search(r"[(（][^()（）]*(WiFi|WLAN|Wi-Fi)[^()（）]*[)）]", v.get(k) or ""):
            paren.append(f + ":" + k)
check("every pack: the label has no (WiFi only) part, nor do RSDN_25 / RTWK_48", not paren, paren)

# ---------------------------------------------------------------- the pure helpers under node
NAMES = ["reaper_apiso_lan_global", "reaper_apiso_lan_shown", "reaper_apiso_lan_next", "reaper_gc_only_cross"]
cut = []
for n in NAMES:
    m = re.search(r"^function " + n + r"\(.*?^\}\n", sj, re.S | re.M)
    check("helper %s is a block the test can cut out" % n, m is not None)
    if m:
        cut.append(m.group(0))
for n, body in zip(NAMES, cut):
    check("helper %s takes no page state (no $, httpApi, document)" % n,
          not re.search(r"\$\(|\$\.|httpApi|document\.|window\.", body), n)

ran = False
if len(cut) != len(NAMES):
    pass
elif not shutil.which("node"):
    print("note: no node on the host - the helper runs are skipped")
else:
    HARNESS = r"""
FNS
const g = reaper_apiso_lan_global, sh = reaper_apiso_lan_shown, nx = reaper_apiso_lan_next;
const o = {};
o.global = [g({"sdn_name":"MAINFH", "subnet_idx":"0"}), g({"sdn_name":"MAINFH", "subnet_idx":""}), g({"sdn_name":"IoT", "subnet_idx":"0"}),
  g({"sdn_name":"Guest", "subnet_idx":"2"}), g({"sdn_name":"MAINBH", "subnet_idx":"0"}), g({"sdn_name":"Customized", "subnet_idx":0}),
  g(undefined), g(null), g({})];
o.shown = [sh("1"), sh("0"), sh(""), sh(undefined), sh("yes"), sh(1)];
o.next = [nx("", "0"), nx(undefined, "0"), nx("0", "0"), nx("1", "0"), nx("junk", "0"), nx("", "1"), nx("0", "1"), nx("1", "1"),
  nx("", undefined), nx("1", undefined)];
const set = {"action_mode":"apply", "rc_service":"restart_wireless;restart_sdn 3;", "apg3_ap_isolate":"1", "apg3_ap_isolate_lan":"1",
  "apg3_rg_devs":"", "apg3_rg_mdns":""};
const cur = {"apg3_ap_isolate":"1", "apg3_ap_isolate_lan":"", "apg3_rg_devs":"", "apg3_rg_mdns":""};
o.choice_only = reaper_gc_only_cross(set, cur, "3");
o.choice_and_rg = reaper_gc_only_cross(Object.assign({}, set, {"apg3_rg_mdns":"print"}), cur, "3");
o.untouched = reaper_gc_only_cross(Object.assign({}, set, {"apg3_ap_isolate_lan":"", "apg3_rg_mdns":"print"}), cur, "3");
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
        ran = True
        check("global key for the main network and every network on its subnet; never MAINBH or a network with its own subnet",
              o["global"] == [True, True, True, False, False, True, False, False, False], o["global"])
        check("shown choice: only \"1\" is Wi-Fi and LAN ports", o["shown"] == ["1", "0", "0", "0", "0", "1"], o["shown"])
        check("stored value: Wi-Fi only keeps unset unset, else 0; Wi-Fi and LAN ports is 1",
              o["next"] == ["", "", "0", "0", "0", "1", "1", "1", "", "0"], o["next"])
        check("a changed choice is never a light (restart_reaper_guest) save; an untouched one lets the guest-path save stay light",
              o["choice_only"] is False and o["choice_and_rg"] is False and o["untouched"] is True,
              (o["choice_only"], o["choice_and_rg"], o["untouched"]))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  " + f)
if fails:
    sys.exit(1)
if not ran:
    skip("no node on the host (the pins passed; the helper runs did not happen)")
sys.exit(0)
