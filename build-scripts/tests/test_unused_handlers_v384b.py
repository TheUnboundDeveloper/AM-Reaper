#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unused request handlers, batch B (v3.8.4, owner 2026-11-21; review 2026-11-17 B-28 / B-29).

WHY THIS EXISTS. After the small batch of 2026-11-20 (test_unused_handlers_v384.py), 74 request addresses and about
a hundred page hooks that nothing shipped calls were still registered in httpd - behind sign-in, but parsers of
admin input that no page test exercises. The owner approved two batches; the ASUS Router phone app is not a
supported way to manage a Reaper router, so "the app might call it" keeps nothing.
  batch 1  AiProtection / DNS filter (no Trend Micro engine is built): blocking.cgi, get_nt_db.cgi,
           update_InfectedEventJson_security.cgi, get_ccevent_data.cgi, get_dns_block_stats / _list /
           _list_insert_or_update.cgi; IPsec uploads: set_ipsec_profile.cgi, ipsecupload.cgi, ipsec_s2s_upload.cgi,
           upload_server_ipsec_cert.cgi, caupload.cgi; exec_force_cable_diag.cgi, networkmap.tar, and the rows of
           two closed handlers (feedback_mail.cgi, dfb_log.cgi); AiCloud / USB: set_app_mnt.cgi, get_app_mnt.cgi,
           ftpServerTree.cgi, set_usb_bk.cgi; hooks: the AiCloud status group, the nvram_*_x family, and every
           unused hook that changed state on a GET (set_variables on the GT models among them).
  batch 2  family / app control (set_family_group, block_device_internet, internet_ctrl, del_client_data,
           set_pc_reward, get_pc_reward, enable_remote_control, get_custom_clientlist) and the notification centre
           (nc_*.cgi, get_nc_conf.cgi).
What must NOT go with them: delete_client_in_group_list() (closed web_hook.o links to it) and the declarations of the
two closed handlers.

WHAT IT DOES. Reads httpd/web.c, httpd.c and httpd.h of the tree: every removed row and hook is out of its table and
marked REAPER-UNUSED-V384B; none of the 81 removed functions is defined or referenced anywhere in httpd/ (comments
and strings aside); the pieces closed code needs are still there; no prebuilt httpd object in the tree imports a
removed function (nm -u - the firmware would not link); the rows kept for a reason are still there together with
that reason (the run-time-built set_TM_EULA address, the sign-in bounce to page_default.cgi, the AiMesh node list's
iperf3 rows); and no shipped web file (the model of test_handler_callers.py) names a removed address or calls a
removed hook. Exit 0 pass, 1 fail, 77 skipped (no router source tree).
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

def rd(*rel):
    with open(os.path.join(SRC, *rel), encoding="utf-8", errors="replace") as f:
        return f.read()

ROWS_1 = ["blocking.cgi", "get_nt_db.cgi*", "update_InfectedEventJson_security.cgi*", "get_ccevent_data.cgi*",
          "get_dns_block_stats.cgi", "get_dns_block_list.cgi", "get_dns_block_list_insert_or_update.cgi",
          "set_ipsec_profile.cgi*", "ipsecupload.cgi*", "ipsec_s2s_upload.cgi*", "upload_server_ipsec_cert.cgi*",
          "caupload.cgi*", "exec_force_cable_diag.cgi", "feedback_mail.cgi*", "dfb_log.cgi", "networkmap.tar",
          "set_app_mnt.cgi*", "get_app_mnt.cgi*", "ftpServerTree.cgi*", "set_usb_bk.cgi*"]
ROWS_2 = ["set_family_group.cgi", "block_device_internet.cgi", "internet_ctrl.cgi*", "del_client_data.cgi*",
          "set_pc_reward.cgi*", "get_pc_reward.cgi*", "enable_remote_control.cgi", "get_custom_clientlist.cgi",
          "nc_exist_wifi_notice.cgi", "nc_new_wifi_notice.cgi", "nc_exist_wifi_notice_app.cgi",
          "nc_new_wifi_notice_app.cgi", "nc_notice.cgi", "get_nc_conf.cgi*"]
HOOKS = ["cloud_status", "UI_cloud_status", "UI_cloud_dropbox_status", "UI_cloud_ftpclient_status",
         "UI_cloud_sambaclient_status", "UI_cloud_usbclient_status", "UI_rs_status", "getWebdavInfo",
         "initial_folder_var_file", "check_ftp_samba_anonymous",
         "nvram_get_x", "nvram_get_f", "nvram_get_list_x", "nvram_get_buf_x", "nvram_double_match_x",
         "nvram_match_both_x", "nvram_match_list_x", "find_word", "nvram_show_chinese_char",
         "start_wlcscan", "start_autodet", "gen_oauth_salt", "get_MS_WAN_list_Pri", "get_MS_WAN_list_Sec",
         "get_wgs_parameter", "get_wgsc_parameter", "get_wgc_parameter", "wl_get_parameter", "lan_get_parameter",
         "vpn_server_get_parameter", "vpn_client_get_parameter", "nvram_get_ddns", "qrate", "set_variables"]
FUNCS = """asp_ctcount config_MULTIFILTER_setting convert_cloudsync_status delete_client_in_list
delete_client_in_sta_binding_list do_block_device_internet_cgi do_blocking_cgi do_caupload_post do_del_client_data_cgi
do_dns_block_list do_dns_block_list_insert_or_update do_dns_block_stats do_enable_remote_control_cgi
do_exec_force_cable_diag_cgi do_ftpServerTree_cgi do_get_app_mnt_cgi do_get_ccevent_data_cgi
do_get_custom_clientlist_cgi do_get_nc_conf_cgi do_get_nt_db_cgi do_get_pc_reward_cgi do_internet_ctrl_cgi
do_ipsec_s2s_upload_cgi do_ipsec_s2s_upload_post do_ipsecupload_cgi do_ipsecupload_post
do_nc_exist_wifi_notice_app_cgi do_nc_exist_wifi_notice_cgi do_nc_new_wifi_notice_app_cgi do_nc_new_wifi_notice_cgi
do_nc_notice_cgi do_networkmap_file do_set_app_mnt_cgi do_set_family_group_cgi do_set_ipsec_profile_cgi
do_set_pc_reward_cgi do_set_usb_bk_cgi do_update_InfectedEventJson_security_cgi do_upload_server_ipsec_cert_cgi
do_upload_server_ipsec_cert_post ej_UI_cloud_dropbox_status ej_UI_cloud_ftpclient_status
ej_UI_cloud_sambaclient_status ej_UI_cloud_status ej_UI_cloud_usbclient_status ej_UI_rs_status
ej_check_ftp_samba_anonymous ej_cloud_status ej_find_word ej_gen_oauth_salt ej_get_MS_WAN_list_Pri
ej_get_MS_WAN_list_Sec ej_get_wgc_parameter ej_get_wgs_parameter ej_get_wgsc_parameter ej_initial_folder_var_file
ej_lan_get_parameter ej_nvram_double_match_x ej_nvram_get_buf_x ej_nvram_get_ddns ej_nvram_get_f ej_nvram_get_list_x
ej_nvram_get_x ej_nvram_match_both_x ej_nvram_match_list_x ej_nvram_show_chinese_char ej_qos_packet ej_set_variables
ej_vpn_client_get_parameter ej_vpn_server_get_parameter ej_webdavInfo ej_wl_get_parameter enable_nc_notice
ftpServerTree_cgi isIP isValidtimestamp is_valid_cert_filename search_device_name_in_clientlist send_action
start_autodet start_wlcscan""".split()
MACROS = ["IPSEC_S2S_UPLOAD_FILE", "WEBDEVINFO_VER", "ApiMaxNumRegister", "ApiMaxNumPortforward", "ApiMaxNumQos"]

web, hc, hh = rd("httpd", "web.c"), rd("httpd", "httpd.c"), rd("httpd", "httpd.h")

def table(text, head_re):
    m = re.search(head_re + r"\s*\{(.*?)\n\};", text, re.S)
    return m.group(1) if m else ""
def nocomment_c(text):
    """C comments out, string literals untouched (an address pattern such as "js/*" is not a comment start)"""
    return re.sub(r'"(?:\\.|[^"\\\n])*"|/\*.*?\*/|//[^\n]*',
                  lambda m: m.group(0) if m.group(0).startswith('"') else " ", text, flags=re.S)

def names(tbl):
    return re.findall(r'^\s*\{\s*"([^"]+)"\s*,', nocomment_c(tbl), re.M)
mime = table(web, r"struct mime_handler mime_handlers\[\] =")
ej = table(web, r"struct ej_handler ej_handlers\[\] =")
rown, hookn = names(mime), names(ej)
check("web.c: mime_handlers[] and ej_handlers[] are found", len(rown) > 200 and len(hookn) > 200, (len(rown), len(hookn)))
check("the stage is counted right: 20 + 14 addresses, 34 hooks, 81 functions", (len(ROWS_1), len(ROWS_2), len(HOOKS), len(FUNCS)) == (20, 14, 34, 81))

left = [r for r in ROWS_1 if r in rown]
check("batch 1: the 20 rows are out of mime_handlers[]", not left, left)
left = [r for r in ROWS_2 if r in rown]
check("batch 2: the 14 family / app-control and notification-centre rows are out of mime_handlers[]", not left, left)
left = [h for h in HOOKS if h in hookn]
check("the 34 hooks are out of ej_handlers[]", not left, left)
nomark = [r for r in ROWS_1 + ROWS_2 if 'REAPER-UNUSED-V384B: "%s"' % r not in mime] + [h for h in HOOKS if 'REAPER-UNUSED-V384B: "%s"' % h not in ej]
check("each removed row and hook left its tagged marker in the table (REAPER-UNUSED-V384B)", not nomark, nomark[:8])
check("each removed function left its marker", not [f for f in FUNCS if "REAPER-UNUSED-V384B: %s()" % f not in web],
      [f for f in FUNCS if "REAPER-UNUSED-V384B: %s()" % f not in web][:8])
check("the 2026-11-20 tags are untouched (REAPER-UNUSED-V384 x3, REAPER-INITIAL-ACCOUNT)",
      len(re.findall(r"REAPER-UNUSED-V384(?![A-Z])", web)) == 3 and "REAPER-INITIAL-ACCOUNT" in web)

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
for f in FUNCS + MACROS:
    rx = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(f) + r"(?![A-Za-z0-9_])")
    for rel, t in srcs.items():
        if rx.search(t):
            alive.append("%s in %s" % (f, rel))
check("none of the 81 removed functions (and 5 macros) is defined, declared or referenced anywhere in httpd/", not alive, alive[:10])
check("not removed: delete_client_in_group_list() - no caller is left in web.c, closed web_hook.o links to it",
      re.search(r"(?m)^delete_client_in_group_list\(char \*del_maclist", web) is not None and "delete_client_in_group_list" in hh)
check("not removed: the declarations of the closed handlers whose rows went (do_feedback_mail_cgi, do_dfb_log_file)",
      "extern void do_feedback_mail_cgi(char *url, FILE *stream);" in hh and "do_dfb_log_file" in hh)
check("httpd.c: the file-need-not-exist exemption of networkmap.tar went with its row; its neighbours stay",
      "networkmap.tar" not in hc and '"uploadIconFile.tar"' in hc and '"cert.tar"' in hc)

# ---------------------------------------------------------------- the link: closed objects must not need what went
NM = shutil.which("nm")
objs = sorted(glob.glob(os.path.join(SRC, "httpd", "prebuild", "*.o")) + glob.glob(os.path.join(SRC, "httpd", "prebuild", "*", "*.o")))
if NM and objs:
    need, read = [], 0
    for o in objs:
        r = subprocess.run([NM, "-u", o], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if r.returncode != 0:
            continue
        read += 1
        und = set(l.split()[-1] for l in r.stdout.decode("latin1").split("\n") if l.strip())
        for f in FUNCS:
            if f in und:
                need.append("%s needs %s" % (os.path.relpath(o, SRC), f))
    check("no prebuilt httpd object of the tree imports a removed function (nm -u over %d objects)" % read, read > 0 and not need, need[:8] or "no object readable")
    r = subprocess.run([NM, "-u"] + objs, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    check("... and a closed object does import delete_client_in_group_list (why it stays)",
          "delete_client_in_group_list" in r.stdout.decode("latin1"))
else:
    print("     (no nm or no prebuilt objects in this tree: the import check is skipped)")

# ---------------------------------------------------------------- rows kept for a reason: the reason is still true
check("kept: set_TM_EULA.cgi - a shipped script builds its address at run time (httpApi.enableEula)",
      "set_TM_EULA.cgi*" in rown and "'/set_' + eulaType + '_EULA.cgi?'" in rd("www", "js", "httpApi.js"))
check("kept: page_default.cgi - httpd's sign-in path sends the browser there",
      "page_default.cgi" in rown and "top.location.href='/page_default.cgi?url=%s'" in hc)
wl = table(web, r"struct AiMesh_whitelist AiMesh_whitelists\[\] =")
ip = ["set_iperf3_svr.cgi", "set_iperf3_cli.cgi", "get_iperf3_state.cgi"]
check("the three iperf3 rows and their AiMesh node-list entries go together (both gone since batch C, test_unused_handlers_v384c.py)",
      all(x in rown for x in ip) == all('{"%s", NULL}' % x in wl for x in ip))
check("kept: cert.tar and the closed config-sync rows",
      "cert.tar" in rown and all(x in rown for x in ("save_all_profile.cgi*", "start_config_sync.cgi*", "upload_config_sync.cgi*", "upload_blacklist_config.cgi*")))

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
row_rx = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(r.rstrip("*")) for r in ROWS_1 + ROWS_2) + r")(?![A-Za-z0-9_])")
hook_rx = re.compile(r"(?:<%\s*|hook=[^\"'\n]*?[=;(]?|[\"'`])(?<![A-Za-z0-9_])(" + "|".join(re.escape(h) for h in HOOKS) + r")\s*[\"'`(\-]")
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
ha = rd("www", "js", "httpApi.js")
eula = sorted(set(re.findall(r"enableEula\(\s*[\"']([A-Za-z_]+)[\"']", "".join(open(r, encoding="utf-8", errors="replace").read() for d, rs in model if d.endswith((".js", ".asp", ".html", ".htm")) for r in rs))))
check("the one run-time-built address (set_<type>_EULA.cgi) is only ever built for a type that has a row", bool(eula) and all(("set_%s_EULA.cgi*" % e.upper()) in rown for e in eula), eula)

if FAILS:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
print("all passed")
