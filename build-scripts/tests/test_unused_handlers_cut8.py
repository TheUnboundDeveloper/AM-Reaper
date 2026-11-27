#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unused request handlers after the native-UI cutover, stage 5 follow-up (REAPER-UNUSED-CUT8, owner 2026-11-27).

WHY THIS EXISTS. Stage 5 (REAPER-CUT8) stopped shipping the stock pages; 78 rows and hooks of httpd lost their last
caller and were parked in handler_callers.allow. The review (cutover/stage5/handlers/REPORT.md) found none of them
still called - no shipped page (literal or a name built at run time), no open code, no closed object, no AiMesh node
use - and the owner approved removing 77 of them with the code only they reached; **.zip stays as a generic archive
type. Several of them acted on a bare request: update.cgi ran ANY hook named in ?output= with up to 16 request
arguments (a second hook path beside appGet.cgi), apps_action started USB application installs and removals,
wan_action connected / disconnected the WAN, set_AiDisk_status and set_account_all_folder_permission changed the USB
shares, act_chksta set enable_diag, rog_first_qos.cgi rewrote and committed the QoS rule lists.
  rows (29)    the stock-page files (Nologin.asp, offline.htm, manifest.asp, manifest.appcache, gotoHomePage.htm,
               ureip.asp, update_applist.asp, update_appstate.asp, wlc_status.json, wcdma_list.js, remote.js,
               js/oauth.js, js/table/tableValidator.js, require/modules/amesh.js, eight style sheets,
               images/New_ui/asustitle.png), **.appcache, **.part.*, fb_data.tgz.gz(.part.*), TCC.log.*,
               update.cgi*, rog_first_qos.cgi*  (the 3006.102.8 line lacks 12 of them)
  hooks (48)   see HOOKS
  node list    update_applist.asp, update_appstate.asp out of AiMesh_whitelists[]
  with them    38 handler functions, the helpers convert_to_kbps(), delete_qos_rulelist(), delete_rog_clientlist(),
               isNumber(), SambaVersion[], the LACP_PORT1/2 and PPACMD_* macros, the traffic_wanlan() prototype, the
               prototypes of the ten closed web-broadcom.o hooks (their rows only could go), the offline.htm HTTPS
               skip, the TCC.log / asustitle.png file tests and three etag entries in httpd.c.
What must stay: ej_dns_status (the bwdpi_status rows), ej_wl_status_array (ej_wl_status_json, the Wireless Log),
the kept hooks next to the removed ones (get_wl_status_json, get_wl_channel_list_5g, chanspecs_5g / _5g_2,
IP_dhcpLeaseInfo, dns_wanStat_detail), **.zip, httpd.c's acting[] GET-refusal list, a well-formed node list.

WHAT IT DOES. Reads httpd/web.c, data_arrays.c, data_arrays.h, httpd.c: every removed row, hook and node-list entry
is out of its table and marked REAPER-UNUSED-CUT8; none of the removed functions, macros and globals is defined,
declared or referenced in httpd/; what must stay is there; no prebuilt httpd object imports a removed function
(nm -u); no shipped web file (the model of test_handler_callers.py) names a removed address or calls a removed hook.
These are also the source pins of the names that cannot carry an image absence marker (update.cgi, dhcpLeaseInfo,
dns_wanStat, get_wl_status, plc_status, wan_action, update_appstate.asp and the nine names no Reaper model compiles).
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import glob, os, re, shutil, subprocess, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

FAILS = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond or not detail else ": " + str(detail)[:700]))
    if not cond:
        FAILS.append(name)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
HERE = os.path.dirname(os.path.abspath(__file__))
TAG = "REAPER-UNUSED-CUT8"

def rd(*rel):
    with open(os.path.join(SRC, *rel), encoding="utf-8", errors="replace") as f:
        return f.read()

ROWS = """Nologin.asp gotoHomePage.htm ureip.asp wlc_status.json manifest.appcache offline.htm wcdma_list.js manifest.asp
update_applist.asp update_appstate.asp aimesh_system_settings.css aimesh_topology.css amesh.css gameprofile.css
networkMap.css NM_style.css **.appcache TCC.log.* fb_data.tgz.gz fb_data.tgz.gz.part.* **.part.* aimesh/aimesh_topology.css
images/New_ui/asustitle.png js/oauth.js js/table/tableValidator.js remote.js require/modules/amesh.js update.cgi*
rog_first_qos.cgi*""".split()
HOOKS = """act_chksta apps_action apps_info apps_state_info bwdpi_appStat bwdpi_conntrack bwdpi_wanStat channel_list_6g
channel_list_6g_2 chanspecs_2g chanspecs_6g chanspecs_6g_2 cpu_core_num dhcpLeaseInfo dns_appStat dns_status dns_wanStat
get_connlist_array get_diag_db get_disk_format_log get_ipv6clients_array get_label_mac get_opt_status get_SambaInfo
get_tcclass_array get_usb_phy_port get_wl_channel_list_2g get_wl_channel_list_5g_2 get_wl_channel_list_6g
get_wl_channel_list_6g_2 get_wl_status netdev plc_status set_account_all_folder_permission set_AiDisk_status
set_group_all_folder_permission set_group_permission usb_is_exist wan_action wan_get_parameter wl_cap_2g wl_cap_5g
wl_cap_5g_2 wl_cap_6g wl_cap_6g_2 wl_edmg_channel yadns_clients yadns_servers""".split()
NODE = ["update_applist.asp", "update_appstate.asp"]
HANDLERS = """do_diag_log_file do_rog_first_qos_cgi do_update_cgi ej_apps_action ej_apps_info ej_apps_state_info
ej_bwdpi_appStat ej_bwdpi_conntrack ej_bwdpi_wanStat ej_chksta ej_connlist_array ej_cpu_core_num ej_dhcpLeaseInfo
ej_dns_appStat ej_dns_wanStat ej_get_SambaInfo ej_get_diag_db ej_get_disk_format_log ej_get_label_mac ej_get_opt_status
ej_get_usb_phy_port ej_get_wl_channel_list_2g ej_get_wl_channel_list_5g_2 ej_get_wl_channel_list_6g
ej_get_wl_channel_list_6g_2 ej_lan_ipv6_clients_array ej_netdev ej_plc_status ej_set_AiDisk_status
ej_set_account_all_folder_permission ej_set_group_all_folder_permission ej_set_group_permission ej_tcclass_dump_array
ej_usb_is_exist ej_wan_get_parameter wan_action_hook yadns_clients_hook yadns_servers_hook""".split()
HELPERS = ["convert_to_kbps", "delete_qos_rulelist", "delete_rog_clientlist", "isNumber"]
CLOSED = """ej_wl_cap_2g ej_wl_cap_5g ej_wl_cap_5g_2 ej_wl_cap_6g ej_wl_cap_6g_2 ej_wl_chanspecs_2g ej_wl_chanspecs_6g
ej_wl_chanspecs_6g_2 ej_wl_channel_list_6g ej_wl_channel_list_6g_2 ej_wl_edmg_channel""".split()
OTHERS = ["SambaVersion", "LACP_PORT1", "LACP_PORT2", "PPACMD_WAN_PATH", "PPACMD_LAN_PATH", "PPACMD_TRAFFIC_PATH", "traffic_wanlan"]
FUNCS = HANDLERS + HELPERS

web, hc = rd("httpd", "web.c"), rd("httpd", "httpd.c")
da = rd("httpd", "data_arrays.c") if os.path.isfile(os.path.join(SRC, "httpd", "data_arrays.c")) else ""

def table(text, head_re):
    m = re.search(head_re + r"\s*\{(.*?)\n\};", text, re.S)
    return m.group(1) if m else ""
def nocomment_c(text):
    """C comments out, string literals untouched (an address pattern such as "js/*" is not a comment start)"""
    return re.sub(r'"(?:\\.|[^"\\\n])*"|/\*.*?\*/|//[^\n]*',
                  lambda m: m.group(0) if m.group(0).startswith('"') else " ", text, flags=re.S)
def names(tbl):
    return re.findall(r'^\s*\{\s*"([^"]+)"\s*,', nocomment_c(tbl), re.M)
def tags(tbl, word):
    return re.findall(r'/\* %s: "([^"]+)" %s removed - ' % (TAG, word), tbl)

mime = table(web, r"struct mime_handler mime_handlers\[\] =")
ej = table(web, r"struct ej_handler ej_handlers\[\] =")
wl = table(web, r"struct AiMesh_whitelist AiMesh_whitelists\[\] =")
rown, hookn, wln = names(mime), names(ej), names(wl)
check("web.c: mime_handlers[], ej_handlers[] and AiMesh_whitelists[] are found", len(rown) > 200 and len(hookn) > 200 and len(wln) > 15,
      (len(rown), len(hookn), len(wln)))
check("the change is counted right: 29 rows, 48 hooks, 2 node-list entries, 38 handlers + 4 helpers, 11 closed prototypes",
      (len(ROWS), len(HOOKS), len(NODE), len(HANDLERS), len(HELPERS), len(CLOSED)) == (29, 48, 2, 38, 4, 11))

left = [r for r in ROWS if r in rown]
check("the 29 rows are out of mime_handlers[]", not left, left)
left = [h for h in HOOKS if h in hookn]
check("the 48 hooks are out of ej_handlers[]", not left, left)
left = [n for n in NODE if n in wln]
check("update_applist.asp / update_appstate.asp are out of AiMesh_whitelists[]", not left, left)
mt, ht, nt = tags(mime, "row"), tags(ej, "hook"), tags(wl, "node-list entry")
check("each removed hook left its tagged marker in ej_handlers[] (52 lines: bwdpi_appStat / bwdpi_wanStat had three rows each)",
      sorted(set(ht)) == sorted(HOOKS) and len(ht) == 52, (len(ht), sorted(set(HOOKS) - set(ht))[:6]))
LINE_1028_ABSENT = {"aimesh_system_settings.css", "aimesh_topology.css", "amesh.css", "gameprofile.css", "networkMap.css",
                    "NM_style.css", "js/oauth.js", "js/table/tableValidator.js", "remote.js", "require/modules/amesh.js",
                    "fb_data.tgz.gz", "fb_data.tgz.gz.part.*"}
need = set(ROWS) - LINE_1028_ABSENT
check("each removed row left its tagged marker in mime_handlers[] (all 29 on the 102.10 lines, 17 on 3006.102.8)",
      need <= set(mt) and set(mt) <= set(ROWS) and len(mt) in (17, 30) and (len(mt) == 17 or set(mt) == set(ROWS)),
      (len(mt), sorted(need - set(mt))[:6]))
check("each removed node-list entry left its marker", sorted(nt) == sorted(NODE), nt)
nomark = [f for f in FUNCS if "%s: %s() removed" % (TAG, f) not in web + da]
check("each removed function left its marker (web.c / data_arrays.c)", not nomark, nomark[:8])
check("the earlier tags are untouched (REAPER-UNUSED-V384B / V384C still there)",
      web.count("REAPER-UNUSED-V384B") > 100 and web.count("REAPER-UNUSED-V384C") > 10)

# ---------------------------------------------------------------- nothing of the removed code is left, nothing refers to it
def code_only(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"(?m)//[^\n]*$", " ", t)
    return re.sub(r'"(\\.|[^"\\\n])*"', '""', t)
srcs = {}
for p in sorted(glob.glob(os.path.join(SRC, "httpd", "*.[ch]")) + glob.glob(os.path.join(SRC, "httpd", "sysdeps", "*.[ch]"))):
    try:
        srcs[os.path.relpath(p, SRC)] = code_only(open(p, encoding="utf-8", errors="replace").read())
    except OSError:
        pass
alive = []
for f in FUNCS + CLOSED + OTHERS:
    rx = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(f) + r"(?![A-Za-z0-9_])")
    for rel, t in srcs.items():
        if rx.search(t):
            alive.append("%s in %s" % (f, rel))
check("none of the removed functions, prototypes, macros and globals is defined, declared or referenced anywhere in httpd/",
      not alive, alive[:10])
hcode = nocomment_c(hc)
check("httpd.c: the offline.htm HTTPS skip, the TCC.log / asustitle.png file tests and the three etag entries are gone",
      'strcmp(url, "offline.htm")' not in hc and '"TCC.log"' not in hc and '"asustitle.png"' not in hc
      and not re.search(r'\{"(oauth|remote|tableValidator)\.js",0\}', hcode))
check("the generic hook reader update.cgi is gone: no handler walks ej_handlers[] by a request's output= name",
      'get_cgi("output")' not in web and '"arg%d"' not in web)

# ---------------------------------------------------------------- what must stay
wcode = srcs.get(os.path.join("httpd", "web.c"), "")
check("kept: ej_dns_status() behind the bwdpi_status rows; ej_wl_status_array() called by ej_wl_status_json() (the Wireless Log)",
      re.search(r'\{\s*"bwdpi_status"\s*,\s*ej_dns_status\s*\}', nocomment_c(ej)) is not None
      and "ej_wl_status_array(eid, m, argc, argv);" in web
      and re.search(r'\{\s*"get_wl_status_json"\s*,\s*ej_wl_status_json\s*\}', nocomment_c(ej)) is not None)
check("kept: the hooks next to the removed ones (get_wl_channel_list_5g, chanspecs_5g / _5g_2, IP_dhcpLeaseInfo, dns_wanStat_detail)",
      all(h in hookn for h in ("get_wl_channel_list_5g", "chanspecs_5g", "chanspecs_5g_2", "IP_dhcpLeaseInfo", "dns_wanStat_detail")),
      [h for h in ("get_wl_channel_list_5g", "chanspecs_5g", "chanspecs_5g_2", "IP_dhcpLeaseInfo", "dns_wanStat_detail") if h not in hookn])
check("kept: **.zip (a generic archive type, like **.gz / **.tgz / **.ipk) and the other archive rows",
      all(r in rown for r in ("**.zip", "**.gz", "**.tgz", "**.ipk")))
check("kept: httpd.c's acting[] GET-refusal list still names the acting pages (defence in depth)",
      '"switch_AiDisk_app.asp", "wan_action.asp", "safely_remove_disk.asp", "update_appstate.asp", NULL };' in hc)
rows_code = [l.strip() for l in nocomment_c(wl).split("\n") if l.strip() and not l.strip().startswith("#")]
check("AiMesh_whitelists[]: every line is one { \"pattern\", NULL } entry, the last is the terminator, the node's entries are there",
      bool(rows_code) and rows_code[-1] == "{ NULL, NULL }" and all(re.fullmatch(r'\{\s*"[^"]+"\s*,\s*NULL\s*\},', l) for l in rows_code[:-1])
      and all(x in wln for x in ("AiMesh_Node_FirmwareUpgrade.asp", "upgrade.cgi", "Main_Login.asp", "appGet.cgi", "*.js")))

# ---------------------------------------------------------------- the link: closed objects must not need what went
NM = shutil.which("nm")
objs = sorted(glob.glob(os.path.join(SRC, "httpd", "prebuild", "*.o")) + glob.glob(os.path.join(SRC, "httpd", "prebuild", "*", "*.o")))
if NM and objs:
    needs, read = [], 0
    for o in objs:
        r = subprocess.run([NM, "-u", o], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if r.returncode != 0:
            continue
        read += 1
        und = set(l.split()[-1] for l in r.stdout.decode("latin1").split("\n") if l.strip())
        for f in FUNCS + ["SambaVersion"]:
            if f in und:
                needs.append("%s needs %s" % (os.path.relpath(o, SRC), f))
    check("no prebuilt httpd object of the tree imports a removed function or global (nm -u over %d objects)" % read,
          read > 0 and not needs, needs[:8] or "no object readable")
else:
    print("     (no nm or no prebuilt objects in this tree: the import check is skipped)")

# ---------------------------------------------------------------- shipped www: nothing names what went
tc = os.path.join(HERE, "test_handler_callers.py")
model = []
if os.path.isfile(tc):
    r = subprocess.run([sys.executable, tc, SRC, "--model"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                       env=dict(os.environ, REAPER_ROUTER_SRC=SRC))
    for ln in r.stdout.decode("utf-8", errors="replace").split("\n"):
        p = ln.split("\t")
        if len(p) == 3 and p[0] == "MODEL":
            model.append((p[1], p[2].split("|")))
check("the shipped-file model of test_handler_callers.py is available", len(model) > 300, len(model))
plain = [r.rstrip("*") for r in ROWS if "**" not in r]
row_rx = re.compile(r"(?<![A-Za-z0-9_\-])(" + "|".join(re.escape(r) for r in sorted(plain, key=len, reverse=True)) + r")(?![A-Za-z0-9_])")
# a hook CALL: <% name( ... %>, inside an appGet hook= string, or a quoted hook name ("name" / "name(" / 'name')
hk = "|".join(re.escape(h) for h in sorted(HOOKS, key=len, reverse=True))
hook_rx = re.compile(r"(?:<%\s*|hook=[^'\"\s&]*?|[\"'`])(" + hk + r")(?:\s*\(|%28|[\"'`])")
BIN = (".png", ".gif", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".gz", ".svg", ".webp", ".dict")
hits = []
for dst, reals in model:
    if dst.lower().endswith(BIN):
        continue
    for real in reals:
        try:
            raw = open(real, "rb").read()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue
        t = raw.decode("utf-8", errors="replace")
        for m in row_rx.finditer(t):
            hits.append("%s names %s" % (dst, m.group(1)))
        for m in hook_rx.finditer(t):
            hits.append("%s calls %s" % (dst, m.group(1)))
check("no shipped web file names a removed address or calls a removed hook", not hits, sorted(set(hits))[:10])

if FAILS:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
print("all passed")
