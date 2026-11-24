#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unused request handlers, batch C (v3.8.4, owner 2026-11-21, after the batch-B report).

WHY THIS EXISTS. Batch B (test_unused_handlers_v384b.py) left 41 request addresses and 80 page hooks that nothing
shipped calls, with a reason each. Reading the ones that change state (the private keep-review) showed what they did
on a bare request: reset_sdn_rule.cgi deleted every network the admin had created, auto_guestnetwork.cgi switched on a
guest network with an empty name on every radio, mld_enable.cgi?do_rc=1 rebooted, clean_ddns.cgi wiped the DDNS setup
and the Let's Encrypt archive, wl_apply.cgi wrote any wireless setting unchecked, splash_page.cgi wrote files to a
path taken from the upload, and the hook backup_nvram printed any setting without the protected-name refusal. The
owner approved removing them, and the three iperf3 addresses that only the (unsupported) phone app used, with their
entries in the AiMesh node list.
  addresses (14)  set_iperf3_svr.cgi, set_iperf3_cli.cgi, get_iperf3_state.cgi; splash_page.cgi, splash_page_del.cgi;
                  create_sdn_profile.cgi, create_sdn_mwl.cgi, create_sdn_legacy.cgi, reset_sdn_rule.cgi,
                  auto_guestnetwork.cgi, wl_apply.cgi, set_wl_band.cgi, mld_enable.cgi; clean_ddns.cgi
  hooks (2)       get_iperf3_state, backup_nvram
  with them       the code only they reached: the three create_sdn_* workers and their helpers, the Alexa / IFTTT
                  guest-network chain, reaper_apg_rg_clear() (its three callers were those create paths),
                  bandwidth_to_band_id(), APXx_NVRAM_LIST[], four splash-page macros.
What must stay: the guest portal's own upload (splash_page_SDN.cgi, do_splash_page_post_SDN with its digits-only
id check, do_splash_page_cgi), the generic save path the Network page uses (apply_cgi, validate_apply,
response_nvram_config, reaper_sdn_tok), and a well-formed AiMesh node list.

WHAT IT DOES. Reads httpd/web.c, httpd.c, httpd.h: every removed row, hook and node-list entry is out of its table
and marked REAPER-UNUSED-V384C; none of the 31 removed functions (4 macros, 1 array) is defined or referenced in
httpd/; AiMesh_whitelists[] still ends in its terminator and nothing sizes it; what must stay is there; no prebuilt
httpd object of the tree imports a removed function (nm -u); the older tags are untouched; and no shipped web file
(the model of test_handler_callers.py) names a removed address or calls a removed hook.
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
TAG = "REAPER-UNUSED-V384C"

def rd(*rel):
    with open(os.path.join(SRC, *rel), encoding="utf-8", errors="replace") as f:
        return f.read()

ROWS = ["set_iperf3_svr.cgi", "set_iperf3_cli.cgi", "get_iperf3_state.cgi", "splash_page.cgi*", "splash_page_del.cgi*",
        "create_sdn_profile.cgi*", "create_sdn_mwl.cgi*", "create_sdn_legacy.cgi*", "reset_sdn_rule.cgi*",
        "auto_guestnetwork.cgi", "wl_apply.cgi*", "set_wl_band.cgi*", "mld_enable.cgi*", "clean_ddns.cgi*"]
NODE = ["set_iperf3_svr.cgi", "set_iperf3_cli.cgi", "get_iperf3_state.cgi"]
HOOKS = ["get_iperf3_state", "backup_nvram"]
HANDLERS = """do_set_iperf3_svr_cgi do_set_iperf3_cli_cgi do_get_iperf3_state_cgi do_splash_page_post do_splash_page_del
do_create_sdn_profile_cgi do_create_sdn_mwl_cgi do_create_sdn_legacy_cgi do_reset_sdn_rule_cgi do_auto_guestnetwork_cgi
do_wl_apply_cgi do_set_wl_band_cgi do_mld_enable_cgi do_clean_ddns_cgi ej_get_iperf3_state ej_backup_nvram""".split()
HELPERS = """create_sdn_profile create_sdn_mwl_profile create_sdn_guest_profile web_get_availabel_sdn_profile
convert_sdn_band convert_security_radius get_sdn_trigger_from bandwidth_to_band_id check_alexa_ifttt_guestnetwork
create_alexa_ifttt_guestnetwork update_alexa_ifttt_guestnetwork create_alexa_ifttt_sdn_profile update_apgx_profile
response_app_nvram_config reaper_apg_rg_clear""".split()
FUNCS = HANDLERS + HELPERS
MACROS = ["INCLUDE_JQUERY", "INCLUDE_UAM", "TAG_START", "TAG_END"]
OBJECTS = ["APXx_NVRAM_LIST"]

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
wl = table(web, r"struct AiMesh_whitelist AiMesh_whitelists\[\] =")
rown, hookn, wln = names(mime), names(ej), names(wl)
check("web.c: mime_handlers[], ej_handlers[] and AiMesh_whitelists[] are found", len(rown) > 200 and len(hookn) > 200 and len(wln) > 15,
      (len(rown), len(hookn), len(wln)))
check("the batch is counted right: 14 addresses, 3 node-list entries, 2 hooks, 16 + 15 functions",
      (len(ROWS), len(NODE), len(HOOKS), len(HANDLERS), len(HELPERS)) == (14, 3, 2, 16, 15))

left = [r for r in ROWS if r in rown]
check("the 14 rows are out of mime_handlers[]", not left, left)
left = [h for h in HOOKS if h in hookn]
check("the 2 hooks are out of ej_handlers[]", not left, left)
left = [n for n in NODE if n in wln]
check("the 3 iperf3 entries are out of AiMesh_whitelists[] (a node no longer answers them)", not left, left)
nomark = ([r for r in ROWS if '%s: "%s"' % (TAG, r) not in mime] + [h for h in HOOKS if '%s: "%s"' % (TAG, h) not in ej]
          + [n for n in NODE if '%s: "%s"' % (TAG, n) not in wl])
check("each removed row, hook and node-list entry left its tagged marker in its table (REAPER-UNUSED-V384C)", not nomark, nomark[:8])
nomark = [f for f in FUNCS if "%s: %s()" % (TAG, f) not in web] + [o for o in OBJECTS if "%s: %s[]" % (TAG, o) not in web]
check("each removed function (and the array) left its marker", not nomark, nomark[:8])
check("the earlier tags are untouched: REAPER-UNUSED-V384 x3 exactly, REAPER-UNUSED-V384B still there, REAPER-INITIAL-ACCOUNT",
      len(re.findall(r"REAPER-UNUSED-V384(?![A-Z])", web)) == 3 and web.count("REAPER-UNUSED-V384B") > 100 and "REAPER-INITIAL-ACCOUNT" in web)

# ---------------------------------------------------------------- the node list is still a well-formed table
rows_code = [l.strip() for l in nocomment_c(wl).split("\n") if l.strip() and not l.strip().startswith("#")]
check("AiMesh_whitelists[]: every line is one { \"pattern\", NULL } entry and the last is the { NULL, NULL } terminator",
      bool(rows_code) and rows_code[-1] == "{ NULL, NULL }" and all(re.fullmatch(r'\{\s*"[^"]+"\s*,\s*NULL\s*\},', l) for l in rows_code[:-1]),
      [l for l in rows_code if not re.fullmatch(r'\{\s*"[^"]+"\s*,\s*NULL\s*\},', l)][:4])
check("AiMesh_whitelists[]: the entries a node needs are still there (firmware upgrade, sign-in, appGet, scripts)",
      all(x in wln for x in ("AiMesh_Node_FirmwareUpgrade.asp", "upgrade.cgi", "Main_Login.asp", "appGet.cgi", "*.js")))
allsrc = ""
for p in sorted(glob.glob(os.path.join(SRC, "httpd", "*.[ch]")) + glob.glob(os.path.join(SRC, "httpd", "sysdeps", "*.[ch]"))):
    try:
        allsrc += open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        pass
check("AiMesh_whitelists[]: nothing in httpd sizes or counts the array (it is walked to its terminator by closed code)",
      "sizeof(AiMesh_whitelists" not in allsrc.replace(" ", "") and "ARRAY_SIZE(AiMesh_whitelists" not in allsrc.replace(" ", "")
      and "extern struct AiMesh_whitelist AiMesh_whitelists[];" in hh and "check_AiMesh_whitelist(file)" in hc)

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
for f in FUNCS + MACROS + OBJECTS:
    rx = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(f) + r"(?![A-Za-z0-9_])")
    for rel, t in srcs.items():
        if rx.search(t):
            alive.append("%s in %s" % (f, rel))
check("none of the 31 removed functions, 4 macros and the array is defined, declared or referenced anywhere in httpd/", not alive, alive[:10])
wcode = srcs.get(os.path.join("httpd", "web.c"), "")
check("the state-changing calls only those handlers made are gone (start_clean_ddns, the iperf3 client fields, the reboot on mld_enable)",
      '"start_clean_ddns"' not in web and 'nvram_set("iperf3_cli_host"' not in web and 'nvram_set_int("iperf3_svr_port"' not in web
      and '"/jffs/customized_splash/%s.json", value);' in web and web.count('"/jffs/customized_splash/%s.json", value);') == 1)

# ---------------------------------------------------------------- what must stay
sp = web[web.find("do_splash_page_post_SDN(char *url, FILE *stream, int len, char *boundary)"):]
sp = sp[:sp.find("\n}\n")] if sp else ""
check("kept: the guest portal's upload splash_page_SDN.cgi, its handler with the digits-only id check, and do_splash_page_cgi",
      "splash_page_SDN.cgi*" in rown and "isValid_digit_string(value) && strlen(value) < 14" in sp
      and re.search(r"(?m)^do_splash_page_cgi\(char \*url, FILE \*stream\)", web) is not None
      and '#define JFFS_CUSTOMIZED_SPLASH "/jffs/customized_splash/"' in web)
check("kept: the generic save path of the Network page (apply_cgi, validate_apply, response_nvram_config, reaper_sdn_tok)",
      all(re.search(r"(?<![A-Za-z0-9_])" + f + r"\s*\(", wcode) for f in ("apply_cgi", "validate_apply", "response_nvram_config", "reaper_sdn_tok"))
      and "apply.cgi*" in rown and "applyapp.cgi*" in rown)
check("kept by decision: set_TM_EULA.cgi, cert.tar, bwm/*.gz, the closed config-sync rows, the icon rows, the IPsec read-only rows",
      all(x in rown for x in ("set_TM_EULA.cgi*", "cert.tar", "bwm/*.gz", "save_all_profile.cgi*", "start_config_sync.cgi*",
                              "upload_config_sync.cgi*", "upload_blacklist_config.cgi*", "uploadIconFile.tar",
                              "get_ipsec_profile.cgi*", "ipsec_s2s.conf", "server_ipsec.cert")),
      [x for x in ("set_TM_EULA.cgi*", "cert.tar", "bwm/*.gz", "save_all_profile.cgi*", "uploadIconFile.tar") if x not in rown])
check("kept: the hooks the Network page and the MLO page read (get_sdn_all_list is not one of the removed; nvram_get, nvram_char_to_ascii, reaper_sdn_defer)",
      all(h in hookn for h in ("nvram_get", "nvram_char_to_ascii")) and ("reaper_sdn_defer" in hookn or "reaper_sdn_defer" not in web))

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
        for f in FUNCS + OBJECTS:
            if f in und:
                need.append("%s needs %s" % (os.path.relpath(o, SRC), f))
    check("no prebuilt httpd object of the tree imports a removed function or the array (nm -u over %d objects)" % read,
          read > 0 and not need, need[:8] or "no object readable")
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
row_rx = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(r.rstrip("*")) for r in ROWS) + r")(?![A-Za-z0-9_])")
hook_rx = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(h) for h in HOOKS) + r")(?![A-Za-z0-9_])")
BIN = (".png", ".gif", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".gz", ".svg", ".webp", ".dict")
hits, groups = [], {"wizard": 0, "network / MLO pages": 0, "portal pages": 0}
for dst, reals in model:
    if dst.lower().endswith(BIN):
        continue
    if re.match(r"QIS_wizard\.htm|mobile/", dst): groups["wizard"] += 1
    if re.match(r"SDN/|SDN\.asp|reaper/reaper_sdn", dst) or "mlo" in dst.lower(): groups["network / MLO pages"] += 1
    if re.search(r"(?i)captive|FreeWiFi|portal", dst): groups["portal pages"] += 1
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
        for m in hook_rx.finditer(t):          # any use of the word at all, stricter than "a hook call"
            hits.append("%s has the word %s" % (dst, m.group(1)))
check("no shipped web file names a removed address or even contains a removed hook's name", not hits, sorted(set(hits))[:10])
check("the files the owner asked about were among those read (setup wizard, Network / MLO pages, portal pages)",
      all(v > 0 for v in groups.values()), groups)

if FAILS:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
print("all passed")
