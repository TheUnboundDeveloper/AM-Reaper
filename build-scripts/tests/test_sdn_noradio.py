#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Network page: an edit of Access Intranet / VPN / DNS / DHCP only restarts no radio (v3.8.4, plan item 1, stage 3).

WHY THIS EXISTS. Router evidence 2026-11-16: ticking Access Intranet on the stock Network page
(www/sysdep/FUNCTION/SDN/SDN/sdn.js) sent "restart_wireless;restart_sdn 4;..." and every Wi-Fi client on every band
was dropped, although only firewall rules changed. restart_sdn N rebuilds the network's DHCP / DNS server, encrypted
DNS, routing, VPN binding and every network's Access Intranet rules (rc/sdn.c handle_sdn_feature); restart_wireless
rebuilds radios and bridges only. So an edit whose changed keys are all of that class keeps stock's list without
restart_wireless. Anything else (SSID, security, bands, schedule, isolation, limiter, VLAN, address, portal) and any
list that is not the plain shape keeps stock's list.

WHAT IT RUNS. The pure helpers (reaper_nr_*) are cut out of sdn.js and run under node: the row-list field compare,
the list rewrite (accepted and refused shapes) and the changed-key classifier. Then pins the call site: after the
guest-path light save, on existing networks only, before the save is sent.

Exit 0 pass, 1 fail, 77 skipped (no router tree; without node the pins still run and a pass exits 77)."""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
SJ = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js") if SRC else ""
if not SJ or not os.path.isfile(SJ):
    skip("no router source tree with www/sysdep/FUNCTION/SDN/SDN/sdn.js (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

sj = open(SJ, encoding="utf-8", errors="surrogateescape").read().replace("\r\n", "\n")

def between(s, a, b):
    i = s.find(a)
    if i < 0:
        return ""
    j = s.find(b, i + len(a))
    return s[i:j] if j > 0 else ""

blk = between(sj, "/* REAPER-SDN-NORADIO-BEGIN", "/* REAPER-SDN-NORADIO-END */")
check("sdn.js carries the REAPER-SDN-NORADIO block once", sj.count("/* REAPER-SDN-NORADIO-BEGIN") == 1 and blk != "")
pure = between(blk, "/* \"<a>b<c>d\"", "/* page side:")
check("the pure helpers sit before the page-side function", pure != "" and "httpApi" not in pure and "$(" not in pure)

# ---------------------------------------------------------------- the call site
ap = between(sj, "\t\t\tfunction apply_profile(){\n", "\n\t\t\t\t\thttpApi.nvramSet(nvramSet_obj, function(){")
site = ("if(reaper_guest_cross_save(nvramSet_obj, sdn_profile.apg_rl.apg_idx)){\n\t\t\t\t\t\tshowLoading_status = get_showLoading_status(nvramSet_obj.rc_service);\n\t\t\t\t\t}\n"
        "\t\t\t\t\t/* REAPER-SDN-NORADIO (2026-11-20): Access Intranet / VPN / DNS / DHCP only -> no radio restart */\n"
        "\t\t\t\t\telse if(!isNewProfile && reaper_sdn_noradio_save(nvramSet_obj, sdn_profile)){\n"
        "\t\t\t\t\t\tshowLoading_status = get_showLoading_status(nvramSet_obj.rc_service);\n\t\t\t\t\t}")
isv = ap.find(site)
check("called once, in the edit panel's apply_profile, right after the guest-path light save (else-if), existing networks only",
      sj.count("reaper_sdn_noradio_save(nvramSet_obj, sdn_profile)") == 1 and isv > 0)
check("runs on the complete save (after apgX / cpX), before the wait is shown and the save is sent",
      0 < ap.find("$.extend(nvramSet_obj, cpX_rl);") < isv < ap.find("if(!httpApi.app_dataHandler){"))
page = between(blk, "function reaper_sdn_noradio_save(", "\n}\n")
check("page side: reads every written key from nvram in one call, any missing answer or error keeps stock's list",
      "httpApi.nvramCharToAscii(keys, true)" in page and "if(got == undefined || got.isError)" in page
      and "if(got[keys[i]] == undefined)" in page and "catch(e){\n\t\treturn false;" in page
      and page.find("reaper_nr_list(") < page.find("httpApi.nvramCharToAscii") < page.find("reaper_nr_only("))
check("the block is ASCII", all(ord(c) < 128 for c in blk))

NODE = shutil.which("node")
if not NODE:
    print("SKIP: node not found - the helper runs are skipped")
elif pure:
    cases = r'''
const R = [];
function t(name, got, want){ R.push([name, JSON.stringify(got), JSON.stringify(want)]); }
// list rewrite
t("plain edit list -> radio restart dropped", reaper_nr_list("restart_wireless;restart_sdn 4;", "4"), "restart_sdn 4;");
t("qos / firewall / stubby / vpn tails kept in order", reaper_nr_list("restart_wireless;restart_sdn 4;restart_qos;restart_firewall;restart_stubby;start_vpnclient2;", "4"),
  "restart_sdn 4;restart_qos;restart_firewall;restart_stubby;start_vpnclient2;");
t("ledg first and other networks' restart_sdn kept", reaper_nr_list("restart_ledg;restart_wireless;restart_sdn 4;restart_sdn 6;", "4"), "restart_ledg;restart_sdn 4;restart_sdn 6;");
t("portal list refused", reaper_nr_list("restart_wireless;restart_sdn 4;restart_chilli;restart_uam_srv;", "4"), "");
t("delete refused", reaper_nr_list("start_sdn_del;restart_wireless;restart_sdn;", "4"), "");
t("LAN-port list refused", reaper_nr_list("restart_net_and_phy;", "4"), "");
t("reboot refused", reaper_nr_list("restart_wireless;restart_sdn 4;reboot;", "4"), "");
t("no own restart_sdn refused", reaper_nr_list("restart_wireless;restart_sdn 5;", "4"), "");
t("no radio restart refused (nothing to drop)", reaper_nr_list("restart_sdn 4;", "4"), "");
t("plain restart_sdn refused", reaper_nr_list("restart_wireless;restart_sdn;", "4"), "");
t("unterminated list refused", reaper_nr_list("restart_wireless;restart_sdn 4", "4"), "");
t("unknown service refused", reaper_nr_list("restart_wireless;restart_sdn 4;restart_dnsmasq;", "4"), "");
t("bad index refused", reaper_nr_list("restart_wireless;restart_sdn 4;", "x"), "");
// row compare
const SDN0 = "<0>DEFAULT>1>0>0>0>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0<4>Guest>1>2>3>4>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0";
const SDN_VPN = SDN0.replace("<4>Guest>1>2>3>4>0>0", "<4>Guest>1>2>3>4>6>0");
const SDN_KS = SDN_VPN.replace(/(<4>Guest>1>2>3>4>6>0>0>0>0>0>0>0)>0/, "$1>1");
t("VPN client field of the edited row changed -> ok", reaper_nr_rl_ok(SDN_VPN, SDN0, "4", [6, 7, 14]), true);
t("VPN client + kill switch -> ok", reaper_nr_rl_ok(SDN_KS, SDN0, "4", [6, 7, 14]), true);
t("same field of another row -> refused", reaper_nr_rl_ok(SDN_VPN, SDN0, "5", [6, 7, 14]), false);
t("enable field changed -> refused", reaper_nr_rl_ok(SDN0.replace("<4>Guest>1", "<4>Guest>0"), SDN0, "4", [6, 7, 14]), false);
t("VLAN field changed -> refused", reaper_nr_rl_ok(SDN0.replace("<4>Guest>1>2", "<4>Guest>1>9"), SDN0, "4", [6, 7, 14]), false);
t("row added -> refused", reaper_nr_rl_ok(SDN0 + "<5>IoT>1>3>4>5>0", SDN0, "4", [6, 7, 14]), false);
t("repeated row index -> refused", reaper_nr_rl_ok(SDN0 + "<4>Guest>1", SDN0 + "<4>Guest>1", "4", [6, 7, 14]), false);
t("missing trailing fields count as empty", reaper_nr_rl_ok("<4>a>b>", "<4>a>b", "4", []), true);
t("same rows in another order -> ok", reaper_nr_rl_ok("<5>x<4>y", "<4>y<5>x", "4", []), true);
// classifier
const SUB0 = "<3>br54>192.168.54.1>255.255.255.0>1>192.168.54.2>192.168.54.254>86400>>>>>>0>0>>>>>0>";
const I = {"idx": "4", "subnet_idx": "3"};
const base = {"action_mode": "apply", "rc_service": "x", "sdn_rl": SDN0, "subnet_rl": SUB0, "apg4_ssid": "Guest", "apg4_security": "<3>psk2>aes>k>0"};
const cur = {"sdn_rl": SDN0, "subnet_rl": SUB0, "apg4_ssid": "Guest", "apg4_security": "<3>psk2>aes>k>0"};
function w(o){ return Object.assign({}, base, o); }
t("nothing changed -> stock (no swap)", reaper_nr_only(base, cur, I), false);
t("Access Intranet pairs changed -> no radio", reaper_nr_only(w({"sdn_access_rl": "<0>4"}), Object.assign({"sdn_access_rl": ""}, cur), I), true);
t("VPN binding changed -> no radio", reaper_nr_only(w({"sdn_rl": SDN_VPN}), cur, I), true);
t("VPN binding + WireGuard client switched on -> no radio", reaper_nr_only(w({"sdn_rl": SDN_VPN, "wgc1_enable": "1"}), Object.assign({"wgc1_enable": "0"}, cur), I), true);
t("DNS servers changed -> no radio", reaper_nr_only(w({"subnet_rl": SUB0.replace("86400>>", "86400>>9.9.9.9")}), cur, I), true);
t("DHCP range changed -> no radio", reaper_nr_only(w({"subnet_rl": SUB0.replace("192.168.54.254", "192.168.54.200")}), cur, I), true);
t("encrypted DNS list of its own subnet -> no radio", reaper_nr_only(w({"dot3_rl": "<1.1.1.1>853>one>"}), Object.assign({"dot3_rl": ""}, cur), I), true);
t("encrypted DNS list of another subnet -> stock", reaper_nr_only(w({"dot5_rl": "<1.1.1.1>853>one>"}), Object.assign({"dot5_rl": ""}, cur), I), false);
t("reservations list -> no radio", reaper_nr_only(w({"dhcpres3_rl": "<AA:BB:CC:DD:EE:FF>192.168.54.9"}), Object.assign({"dhcpres3_rl": ""}, cur), I), true);
t("router address changed -> stock", reaper_nr_only(w({"subnet_rl": SUB0.replace(">192.168.54.1>", ">192.168.55.1>")}), cur, I), false);
t("bridge name changed -> stock", reaper_nr_only(w({"subnet_rl": SUB0.replace("br54", "br55")}), cur, I), false);
t("IPv6 switched on -> stock", reaper_nr_only(w({"subnet_rl": SUB0.replace(">>>>>0>0>", ">>>>>1>0>")}), cur, I), false);
t("subnet_rl change on a network riding the main subnet -> stock", reaper_nr_only(w({"subnet_rl": SUB0.replace("86400>>", "86400>>9.9.9.9")}), cur, {"idx": "4", "subnet_idx": "0"}), false);
t("SSID changed with Access Intranet -> stock", reaper_nr_only(w({"sdn_access_rl": "<0>4", "apg4_ssid": "Guest2"}), Object.assign({"sdn_access_rl": ""}, cur), I), false);
t("password changed -> stock", reaper_nr_only(w({"apg4_security": "<3>psk2>aes>k2>0"}), cur, I), false);
t("limiter changed -> stock", reaper_nr_only(w({"apg4_bw_limit": "<1>1024>1024"}), Object.assign({"apg4_bw_limit": "<0>>"}, cur), I), false);
t("unknown key -> stock", reaper_nr_only(w({"game_vts_rulelist": "x"}), cur, I), false);
t("no info -> stock", reaper_nr_only(w({"sdn_access_rl": "<0>4"}), cur, undefined), false);
console.log(JSON.stringify(R));
'''
    tmp = tempfile.mkdtemp()
    f = os.path.join(tmp, "nr.js")
    open(f, "w").write(pure + "\n" + cases)
    r = subprocess.run([NODE, f], capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        check("helpers run under node", False, r.stderr)
    else:
        for name, got, want in json.loads(r.stdout.strip().splitlines()[-1]):
            check(name, got == want, "got %s want %s" % (got, want))

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
if not NODE:
    sys.exit(77)
print("\nall checks passed")
