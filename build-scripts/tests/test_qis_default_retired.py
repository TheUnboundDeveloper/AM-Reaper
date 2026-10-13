#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QIS_default.cgi lands on "/", never in the stock setup wizard (2026-10-12).

WHY THIS EXISTS. Stock's do_qis_default() turned any ?flag= into QIS_wizard.htm?flag=<x> and no
flag into ?flag=welcome - the whole ASUS first-boot wizard. Two paths still reached it on a shipped
Reaper box: wanduck's first-use captive redirect (every HTTP request on a factory box, x_Setting==0)
and the LAN-subnet-change landing on the no-internet page. Reaper keeps the wizard for one flow,
AiMesh add-node, which aimesh_topology.html opens directly, so the CGI now redirects to "/".

WHAT IT PINS (source): do_qis_default() redirects to "/" and never names the wizard; its handler
row stays (the wizard's own keep-alive POST to /QIS_default.cgi while x_Setting==0 needs a 200
path and ignores the reply); that keep-alive is still the only place the wizard calls the CGI.

Exit 0 pass, 1 fail, 77 skipped (no tree: pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
FILES = {
    "web": "httpd/web.c",
    "wiz": "www/sysdep/FUNCTION/QIS_V3/QIS_wizard.htm",
}
if not SRC or not all(os.path.isfile(os.path.join(SRC, p)) for p in FILES.values()):
    skip("no router tree (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def rd(k): return open(os.path.join(SRC, FILES[k]), encoding="utf-8", errors="replace").read()

web = rd("web")
m = re.search(r"\ndo_qis_default\(char \*url, FILE \*stream\)\n\{(.*?)\n\}\n", web, re.S)
check("web.c: do_qis_default() is defined", m is not None)
body_raw = m.group(1) if m else ""
check("do_qis_default() explains itself in a reaper comment", "reaper 2026-10-12" in body_raw)
# the comment quotes the stock behaviour; judge the code only
body = re.sub(r"/\*.*?\*/", "", body_raw, flags=re.S)
check("do_qis_default() redirects to /", 'websRedirect(stream, "/");' in body)
check("do_qis_default() never names the wizard", "QIS_wizard.htm" not in body)
check("do_qis_default() no longer reads ?flag=", "websGetVar" not in body)
check("do_qis_default() carries the marker string the staged image is checked for",
      "QIS_default.cgi retired" in body)
check("the QIS_default.cgi handler row stays (the wizard's keep-alive POST needs a 200 path)",
      re.search(r'\{\s*"QIS_default\.cgi",\s*"text/html",[^}]*do_qis_default,\s*do_auth\s*\}', web) is not None)

wiz = rd("wiz")
posts = re.findall(r'open\(\s*"POST"\s*,\s*"/QIS_default\.cgi"', wiz)
check("the wizard POSTs to QIS_default.cgi exactly once (its x_Setting==0 keep-alive)", len(posts) == 1, len(posts))
i = wiz.find('"/QIS_default.cgi"')
ctx = wiz[max(0, i - 400):i] if i >= 0 else ""
check("that POST is gated on x_Setting == '0' (never on a configured box)", "x_Setting == '0'" in ctx)

print("%d check(s), %d failed" % (len(fails) + sum(1 for _ in []), len(fails)))
if fails:
    print("FAILED:"); [print("  " + f) for f in fails]
    sys.exit(1)
sys.exit(0)
