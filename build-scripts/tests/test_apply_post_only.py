#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""An apply is a POST, and the Reaper shell frames only .asp pages (review 2026-10-24, S-C2-1).

WHY THIS EXISTS. httpd's do_html_post_and_get() merges a GET's query string into the same table the
forms post, and start_apply.htm (with start_apply2.htm, wlconn_apply.htm, diskmon_test.asp) runs
update_variables() from that table - so start_apply.htm?action_mode=apply&sshd_enable=1&... applied
nvram and ran services from a plain navigation. The shell's hash router framed any *.htm with any
query same-origin, which made such a request first-party (Referer, Sec-Fetch-Site and cookie all
pass): one link clicked by a logged-in admin = a full configuration write. Two halves close it:
httpd refuses action_mode=apply unless the request is a POST (update_variables for the pages,
apply.cgi for browsers - firmware_check/firmware_upgrade are legitimate GETs and stay), and the
shell frames only .asp page names, a query only for Reaper_*.asp from a small character set.

WHAT IT DOES. Pins the wiring in httpd.c / httpd.h / web.c (the method flag set before the handler
runs, the check ahead of validate_apply in both places), checks that nothing shipped links an apply
page with a query, and - with node on the host - runs the shell's frameUrl() against the deep links
the menu, the SUP map and reaper_gone[] produce and against the hostile shapes.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape") as f:
        return f.read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

hc, hh, wc, sh = read("httpd/httpd.c"), read("httpd/httpd.h"), read("httpd/web.c"), read("www/reaper_shell.asp")

# ---- the method flag
hr = hc[hc.find("static void\nhandle_request(void)"):]
check("httpd.c defines the flag and httpd.h exports it", "int reaper_req_post = 0;" in hc and "extern int reaper_req_post;" in hh)
s = hr.find('reaper_req_post = strcasecmp(method, "post") == 0;')
check("handle_request sets it from the request line before any handler runs",
      0 <= s < hr.find("handler->input(file, conn_fp, cl, boundary);"))

# ---- update_variables (the apply pages)
check("web.c has one reaper_apply_needs_post() helper that refuses when the request is not a POST",
      wc.count("static int reaper_apply_needs_post(const char *where)") == 1 and "if (reaper_req_post)\n\t\treturn 0;" in wc)
u = wc.find("static int ej_update_variables(")
ue = wc.find("\n}\n", u)
uv = wc[u:ue]
g = uv.find('reaper_apply_needs_post("update_variables")')
check("update_variables refuses action_mode apply / apply_new on a GET before validate_apply() can run",
      0 <= g < uv.find("validate_apply(wp, NULL)")
      and 'if ((!strcmp(action_mode, "apply") || !strcmp(action_mode, "apply_new")) && reaper_apply_needs_post("update_variables"))' in uv
      and "no_changes_and_no_committing();" in uv[g:g + 300] and "return 0;" in uv[g:g + 300])

# ---- apply.cgi
a = wc.find("apply_cgi(webs_t wp, char_t *urlPrefix")
ae = wc.find("\nAPPLY_FINISH:", a)
ac = wc[a:ae]
g = ac.find('reaper_apply_needs_post("apply.cgi")')
check("apply.cgi refuses a browser's action_mode=apply on a GET before validate_apply(), other modes untouched",
      0 <= g < ac.find("validate_apply(wp,root)")
      and 'if (!strcmp(action_mode, "apply") && check_user_agent(user_agent) == FROM_BROWSER && reaper_apply_needs_post("apply.cgi"))' in ac
      and "goto APPLY_FINISH;" in ac[g:g + 200]
      and ac.find('"firmware_check"') > g)
check("the two legitimate GETs of apply.cgi (firmware check / upgrade) are the only ones shipped, and neither is an apply",
      "action_mode=firmware_upgrade" in read("www/Reaper_Firmware.asp"))

# ---- nothing shipped reaches an apply page with a query (every form posts)
www = os.path.join(SRC, "www")
offenders = []
for root, dirs, files in os.walk(www):
    if os.sep + "sysdep" in root or root.endswith("sysdep"):
        dirs[:] = []; continue
    for fn in files:
        if not fn.endswith((".asp", ".js", ".htm", ".html")):
            continue
        try:
            t = open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in re.finditer(r"(start_apply2?\.htm|wlconn_apply\.htm|diskmon_test\.asp)\?", t):
            offenders.append("%s: %s" % (fn, t[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")))
check("no shipped page links an apply page with a query string (every apply is a form POST)", not offenders, offenders[:5])
hooks = []
for root, dirs, files in os.walk(www):
    if os.sep + "sysdep" in root or root.endswith("sysdep"):
        dirs[:] = []; continue
    for fn in files:
        if fn.endswith((".asp", ".htm", ".html")) and "update_variables();" in open(os.path.join(root, fn), encoding="utf-8", errors="replace").read():
            hooks.append(fn)
check("update_variables() is called from the four known apply pages only", set(hooks) <= {"start_apply.htm", "start_apply2.htm", "wlconn_apply.htm", "diskmon_test.asp"}, hooks)

# ---- the shell's frame allow-list
fu = sh[sh.find("function frameUrl(page){"):]
fu = fu[:fu.find("\n}\n") + 3]
check("frameUrl() admits .asp names only - no .htm / .html - and a query only for Reaper pages",
      "/^([A-Za-z0-9_-]+\\.asp)(\\?[A-Za-z0-9_=&.%:-]*)?$/.exec(page)" in fu and "m[1].indexOf('Reaper_')!==0" in fu
      and not re.search(r"html?\)", fu))

CASES = {
    # the deep links the menu model, the SUP map and reaper_gone[] produce (httpd/reaper_inject.c)
    "Reaper_LAN.asp?tab=dhcp": "/Reaper_LAN.asp?tab=dhcp",
    "Reaper_Log.asp?view=login": "/Reaper_Log.asp?view=login",
    "Reaper_Firewall.asp?t=rules": "/Reaper_Firewall.asp?t=rules",
    "Reaper_ModeSetup.asp?mode=ap": "/Reaper_ModeSetup.asp?mode=ap",
    "Reaper_System.asp?af=sshd_enable": "/Reaper_System.asp?af=sshd_enable",
    "Reaper_GK.asp?mac=aa:bb:cc:dd:ee:ff": "/Reaper_GK.asp?mac=aa:bb:cc:dd:ee:ff",
    "Reaper_VPNServer.asp?tab=ovpn": "/Reaper_VPNServer.asp?tab=ovpn",
    "Reaper_Devices.asp": "/Reaper_Devices.asp",
    "AiMesh.asp": "/AiMesh.asp", "SDN.asp": "/SDN.asp", "MLO.asp": "/MLO.asp", "APP_Installation.asp": "/APP_Installation.asp",
    "Advanced_WWPS_Content.asp": "/Advanced_WWPS_Content.asp", "Main_ReaperDash.asp": "/Main_ReaperDash.asp",
    "user1.asp": "/user1.asp", "Captive_Portal.asp": "/Captive_Portal.asp", "Logout.asp": "/Logout.asp",
    # the attack and its kin
    "start_apply.htm?action_mode=apply&sshd_enable=1&sshd_authkeys=ssh-ed25519+AAAA": "/Main_ReaperDash.asp",
    "start_apply.htm": "/Main_ReaperDash.asp", "start_apply2.htm?action_mode=apply": "/Main_ReaperDash.asp",
    "wlconn_apply.htm?action_mode=apply": "/Main_ReaperDash.asp", "diskmon_test.asp?action_mode=apply": "/Main_ReaperDash.asp",
    "Advanced_System_Content.asp?action_mode=apply": "/Main_ReaperDash.asp",
    "Advanced_Wireless_Content.asp?firstboot=1": "/Main_ReaperDash.asp",
    "x.html": "/Main_ReaperDash.asp", "message.htm": "/Main_ReaperDash.asp",
    "Reaper_System.asp?af=<script>": "/Main_ReaperDash.asp", "Reaper_System.asp?a=1;b=2": "/Main_ReaperDash.asp",
    "Reaper_System.asp?x=a/b": "/Main_ReaperDash.asp", "Reaper_System.asp?x=a+b": "/Main_ReaperDash.asp",
    "//evil.example/x.asp": "/Main_ReaperDash.asp", "javascript:alert(1)": "/Main_ReaperDash.asp",
    "/Reaper_System.asp": "/Main_ReaperDash.asp", "..\\x.asp": "/Main_ReaperDash.asp", "a/b.asp": "/Main_ReaperDash.asp",
    "Reaper_System.asp#x": "/Main_ReaperDash.asp", "reaper_shell.asp": "/reaper_shell.asp", "": "/Main_ReaperDash.asp",
}
node = shutil.which("node")
if not node:
    print("note: node not found - frameUrl() is pinned statically only")
else:
    js = "var DEFAULT_PAGE='Main_ReaperDash.asp';\n" + fu + "\nvar c=" + json.dumps(list(CASES.keys())) + ";var o={};c.forEach(function(p){o[p]=frameUrl(p);});console.log(JSON.stringify(o));\n"
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f.js"); open(p, "w").write(js)
        r = subprocess.run([node, p], capture_output=True, text=True, timeout=30)
    try:
        got = json.loads(r.stdout)
    except Exception as e:
        got = {}; check("frameUrl() runs under node", False, "%s %s %s" % (e, r.stdout[:200], r.stderr[:300]))
    bad = {k: (got.get(k), v) for k, v in CASES.items() if got.get(k) != v}
    check("frameUrl(): %d deep links kept, every .htm / foreign / malformed target falls to the dashboard" % sum(1 for v in CASES.values() if v != "/Main_ReaperDash.asp"),
          not bad, bad)

if fails:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
print("PASS test_apply_post_only")
