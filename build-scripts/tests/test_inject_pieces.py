#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""httpd's serve-time pieces after the stock UI left (native-UI cutover stage 5, REAPER-CUT8, 2026-11-26).

WHY THIS EXISTS. reaper_inject.c used to skin every stock ASUS page (reaper_content.css + a superseded-page bounce,
"mode 1") and had an nvram switch, reaper_inject=0, that served the stock UI instead. The owner removed both in stage
5. What is left is load-bearing and only the image build compiles it, so this test compiles reaper_inject.c on the
host against stub headers and serves pages through reaper_output():
  - the http_id token hook on every authenticated page (web.c refuses a browser apply without the token; rp.post and
    httpApi.nvramSet do not add it - the hook is how ~80 apply sites get it), never on an unauthenticated one;
  - the gone-page stub for a page that no longer ships (reaper_pagemap[], shipped = 0);
  - shipped = 1 rows (stock pages kept only for an AiMesh node): a router answers them with the stub to the kit page,
    a node serves them untouched (owner, stage 5 question 3);
  - mode 2 (Reaper page by its own address -> the shell) with the link floor; mode 5 (banner loader) with the link
    floor on the dashboard, the shell, Main_Password and the first-boot Wi-Fi box; everything else token-only;
  - the colour-blind block on an authenticated answer while reaper_cbmode = 1;
  - nothing at all on an AiMesh node (re_mode = 1 / disable_ui = 1);
  - no stock skin, no SUP map, no reaper_inject switch left in the source.
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
INJ = os.path.join(SRC, "httpd", "reaper_inject.c") if SRC else ""
if not INJ or not os.path.isfile(INJ):
    print("SKIP: no router source tree"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC or not sys.platform.startswith("linux"):
    print("SKIP: needs a host compiler on Linux"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(INJ, encoding="utf-8").read()
code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)          # what the compiler sees (comments may tell the history)
rows = re.findall(r'\{ "([a-z0-9_.-]+)",\s*"([^"]+)",\s*([01]) \}', src[src.index("reaper_pagemap[] = {"):])
R = {r[0]: (r[1], r[2]) for r in rows}
check("reaper_pagemap[] parses (one table)", len(rows) >= 100, len(rows))
names = [r[0] for r in rows]
check("every name appears once", len(names) == len(set(names)))
check("the SNMP row exists only on a build with snmpd (Reaper_SNMP.asp ships only then; review 1.2)",
      re.search(r'#ifdef RTCONFIG_SNMPD[^\n]*\n\t\{ "advanced_snmp_content\.asp", "Reaper_SNMP\.asp", 0 \},\n#endif', src) is not None)
check("the stock skin is gone from the code: no reaper_content.css, no SUP map, no skin-only tables",
      "reaper_content" not in code and "SUP" not in code and "reaper_css_only" not in code
      and "reaper_own_theme" not in code and "REAPER_BOUNCE" not in code and "REAPER_CSS_LINK" not in code)
check("the nvram switch back to the stock UI is gone (no read of reaper_inject)", '"reaper_inject"' not in code)
check("the node guard is still there (re_mode / disable_ui)", 'nvram_match("re_mode", "1")' in code and 'nvram_match("disable_ui", "1")' in code)
check("stage 5 rows: index.asp -> dashboard, AiMesh / Network / Game* / Feedback addresses -> their Reaper pages",
      R.get("index.asp") == ("Main_ReaperDash.asp", "0") and R.get("aimesh.asp") == ("Reaper_AiMesh.asp", "0")
      and R.get("sdn.asp") == ("Reaper_Network.asp", "0") and R.get("gameboost.asp") == ("Main_ReaperDash.asp", "0")
      and R.get("gameprofile.asp") == ("Main_ReaperDash.asp", "0") and R.get("feedback_info.asp") == ("Reaper_Diag.asp", "0"),
      {k: R.get(k) for k in ("index.asp", "aimesh.asp", "sdn.asp", "gameboost.asp", "gameprofile.asp", "feedback_info.asp")})
check("the stock Speed / Operation Mode pages no longer ship (rows shipped = 0)",
      R.get("adaptiveqos_internetspeed.asp") == ("Reaper_Speed.asp", "0")
      and R.get("advanced_operationmode_content.asp") == ("Reaper_OpMode.asp", "0"))
kept = sorted(k for k, v in R.items() if v[1] == "1")
check("the only shipped = 1 rows are the two node pages (PrinterServer, Time Machine)",
      kept == ["advanced_timemachine.asp", "printerserver.asp"], kept)
check("sdn.asp sits with the other Network rows (RTCONFIG_MULTILAN_CFG)",
      src.find('"sdn.asp"') > src.find("#ifdef RTCONFIG_MULTILAN_CFG") >= 0)
check("the first-boot Wi-Fi box is a banner-only page now (it carries its own copy of the skin rules it used)",
      re.search(r'reaper_banner_only\[\] = \{[^}]*"Reaper_WiFiSetup\.asp"', code, re.S) is not None)

work = tempfile.mkdtemp(prefix="inj_")
try:
    inc = os.path.join(work, "inc"); os.makedirs(inc)
    open(os.path.join(inc, "bcmnvram.h"), "w").write(
        "char *nvram_get(const char *n);\nint nvram_match(const char *n, const char *v);\n")
    open(os.path.join(inc, "httpd.h"), "w").write(      # the real httpd.h pulls in rtconfig.h; RT-BE96U has snmpd
        "#include <stdio.h>\n#define RTCONFIG_SNMPD 1\nstruct mime_handler { char *pattern; char *mime_type; char *extra_header;\n"
        "  void (*input)(char *, FILE *, int, char *); void (*output)(char *, FILE *); void (*auth)(char *, char *, char *); };\n")
    shutil.copy(os.path.join(SRC, "httpd", "reaper_inject.h"), inc)
    harness = r'''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "httpd.h"
#include "reaper_inject.h"
static int env1(const char *e) { const char *v = getenv(e); return v && !strcmp(v, "1"); }
char *nvram_get(const char *n) { if (!strcmp(n, "http_id")) return env1("AUTH") ? "Tok3n" : ""; return ""; }
int nvram_match(const char *n, const char *v)
{
	if (!strcmp(n, "re_mode")) return env1("NODE") && !strcmp(v, "1");
	if (!strcmp(n, "disable_ui")) return env1("NOUI") && !strcmp(v, "1");
	if (!strcmp(n, "reaper_cbmode")) return env1("CB") && !strcmp(v, "1");
	return 0;
}
int reaper_req_authed = 0;
static const char *BODY;
static void out(char *file, FILE *f) { (void)file; fputs(BODY, f); }
int main(int argc, char **argv)
{
	struct mime_handler h = { "*.asp", "text/html", NULL, NULL, out, NULL };
	if (argc < 3) return 2;
	BODY = argv[2];
	reaper_req_authed = env1("AUTH");
	reaper_output(&h, argv[1], stdout);
	return 0;
}
'''
    hp = os.path.join(work, "h.c"); open(hp, "w").write(harness)
    exe = os.path.join(work, "h")
    b = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-Wno-unused-parameter",
                        "-DRTCONFIG_MULTILAN_CFG", "-I", inc, "-o", exe, hp, INJ], capture_output=True, text=True)
    check("reaper_inject.c compiles on the host (-Wall -Wextra -Werror) against stub headers", b.returncode == 0, b.stderr[-800:])
    if b.returncode:
        raise SystemExit
    os.chdir(work)                       # a served file "exists" when it is in the cwd (access())
    def serve(name, body, **env):
        e = dict(os.environ); e.update({k: str(v) for k, v in env.items()})
        return subprocess.run([exe, name, body], capture_output=True, text=True, env=e).stdout
    PAGE = "<html><head><title>x</title></head><body>B</body></html>"
    HEAD0 = "<html><head><title>x</title>"
    present = ["Advanced_Stock_Page.asp", "QIS_wizard.htm", "Reaper_LAN.asp", "Main_ReaperDash.asp", "reaper_shell.asp",
               "Main_Login.asp", "Main_Password.asp", "Reaper_WiFiSetup.asp", "PrinterServer.asp", "Advanced_TimeMachine.asp",
               "index.asp"]
    for n in present:
        open(n, "w").write("x")
    def pieces(s):
        return s[len(HEAD0):s.index("</head>")] if s.startswith(HEAD0) and "</head>" in s else None

    # unauthenticated: nothing but the visual pieces of modes 2 / 5
    st = serve("Advanced_Stock_Page.asp", PAGE)
    check("a kept stock page (unlisted) is served untouched: no skin, no bounce, no banner (unauthenticated)", st == PAGE, st[:300])
    check("the setup wizard (QIS_*) is served untouched (unauthenticated)", serve("QIS_wizard.htm", PAGE) == PAGE)
    nat = pieces(serve("Reaper_LAN.asp", PAGE))
    check("reaper-native page: the link floor then the self-top bounce, nothing else",
          nat is not None and nat.startswith("<style>:where(a:not([class]))") and "if(self===top){var rp=" in nat
          and '||"Main_ReaperDash.asp"' in nat and "Reaper_SecBanner.asp" not in nat and "reaper_content" not in nat, nat)
    for n in ("Main_ReaperDash.asp", "reaper_shell.asp", "Main_Password.asp", "Reaper_WiFiSetup.asp"):
        bo = pieces(serve(n, PAGE))
        check("banner-only page %s: the link floor and the banner loader, no bounce, no stylesheet link" % n,
              bo is not None and bo.startswith("<style>:where(") and "Reaper_SecBanner.asp" in bo
              and "location.replace" not in bo and "<link" not in bo, bo)
    check("a skipped page (login) is served untouched", serve("Main_Login.asp", PAGE) == PAGE)

    # authenticated: the token hook on every page, once, after the mode's pieces; the colour-blind block when on
    for n in ("Advanced_Stock_Page.asp", "QIS_wizard.htm", "Reaper_LAN.asp", "Main_ReaperDash.asp", "Main_Login.asp"):
        s = serve(n, PAGE, AUTH=1)
        check("authenticated %s: the token hook exactly once before </head>, body untouched" % n,
              s.count("var t='Tok3n'") == 1 and s.index("var t='Tok3n'") < s.index("</head>")
              and s.endswith("</head><body>B</body></html>") and "/reaper/reaper_cb.css" not in s, s[:200])
    s = serve("QIS_wizard.htm", PAGE, AUTH=1, CB=1)
    check("authenticated + colour-blind mode: the wizard gets the palette sheet and the class",
          '<link rel="stylesheet" href="/reaper/reaper_cb.css">' in s and 'classList.add("cb")' in s)
    s = serve("QIS_wizard.htm", PAGE, CB=1)
    check("colour-blind block only on an authenticated answer", "reaper_cb.css" not in s)

    # gone-page stub
    gone = [r for r in rows if r[2] == "0" and r[0] != "index.asp"]
    g = gone[0]
    st = serve(g[0].replace("advanced", "Advanced"), PAGE)
    check("an unshipped page answers with the bounce stub to its target", "/reaper_shell.asp#%s" % g[1] in st and "B</body>" not in st, st[:200])
    st = serve("AiMesh.asp", PAGE)
    check("the stock AiMesh address goes to the kit page", "/reaper_shell.asp#Reaper_AiMesh.asp" in st and "B</body>" not in st)
    st = serve("index.asp.missing", PAGE)
    check("a name not in the table is not a gone page", "reaper_shell.asp#" not in st)
    st = serve("index.asp", PAGE)
    check("a shipped = 0 row whose file is still present (an add-on, a port) is served, not stubbed", st == PAGE, st[:200])
    # shipped = 1: node pages
    for n, to in (("PrinterServer.asp", "Reaper_Printer.asp"), ("Advanced_TimeMachine.asp", "Reaper_TimeMachine.asp")):
        st = serve(n, PAGE)
        check("router: %s (kept for AiMesh nodes) answers with the stub to %s" % (n, to),
              "/reaper_shell.asp#%s" % to in st and "B</body>" not in st, st[:200])
        st = serve(n, PAGE, NODE=1)
        check("AiMesh node: %s is served untouched" % n, st == PAGE, st[:200])
        st = serve(n, PAGE, NOUI=1)
        check("web UI disabled: %s is served untouched" % n, st == PAGE, st[:200])
    os.remove("PrinterServer.asp")
    st = serve("PrinterServer.asp", PAGE)
    check("a shipped = 1 row is not stubbed when its file is absent (it is not a gone page)", "reaper_shell.asp#" not in st, st[:200])

    # the node guard covers every mode
    for n in ("Reaper_LAN.asp", "Main_ReaperDash.asp", "QIS_wizard.htm"):
        check("AiMesh node: %s gets nothing, even authenticated" % n, serve(n, PAGE, NODE=1, AUTH=1) == PAGE)
    check("no </head>: the body goes out verbatim", serve("Reaper_LAN.asp", "<p>a<b>c</p>") == "<p>a<b>c</p>")
    many = "<" * 5000 + "<head></head>" + "<" * 50
    out = serve("Reaper_LAN.asp", many)
    check("a body full of '<' still finds the one </head> (memchr search)",
          out.count("if(self===top){var rp=") == 1 and out.endswith("</head>" + "<" * 50))
except SystemExit:
    pass
finally:
    os.chdir("/")
    shutil.rmtree(work, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
