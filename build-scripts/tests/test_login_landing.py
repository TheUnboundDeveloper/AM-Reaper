#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The page login returns to is a page the browser navigated to (2026-11-03, owner metal report).

WHY THIS EXISTS. httpd's send_login_page() records the URL of whatever request failed auth as login_url, and
Main_Login.asp sends the browser there after a good login (it only checks the name holds .asp or .htm). A page's
background requests fail auth too: the security banner's loader GETs /Reaper_SecBanner.asp on every top-level
page, and pages poll ajax_*.asp. When one of those was the last refused request, login opened the FRAGMENT as the
top page - hidden spans only, a white screen (v3.7.0 on the owner's BE96U; reproduced with two curl requests).

WHAT IT DOES. (1) Static: httpd.c parses Sec-Fetch-Dest into reaper_sfd, clears it per request before the header
loop, and send_login_page() records url only when reaper_login_landing(url) says so (else the index page, file
NULL). (2) Compiles reaper_login_landing() out of httpd.c on the host and runs it: navigations (document, iframe,
frame, or no header) land; empty/cors-style destinations, the banner fragment and ajax_ polls never do.
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
H = os.path.join(SRC, "httpd", "httpd.c") if SRC else ""
if not H or not os.path.isfile(H):
    print("SKIP: no router source tree"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

src = open(H, encoding="utf-8", errors="replace").read()
m = re.search(r"static int reaper_login_landing\(const char \*u\)\n\{.*?\n\}\n", src, re.S)
check("reaper_login_landing() exists", m is not None)
slp = src[src.find("\nsend_login_page(int fromapp_flag"):]
slp = slp[:slp.find("\n}\n")]
check("send_login_page records url only through reaper_login_landing (else indexpage, file NULL)",
      re.search(r"if\(url == NULL \|\| !reaper_login_landing\(url\)\) \{[^}]*strncpy\(login_url, indexpage[^}]*file = NULL;\s*\} else\s*strncpy\(login_url, url",
                slp) is not None)
hr = src[src.find("\nhandle_request(void)"):]
i_reset = hr.find("reaper_sfd[0] = '\\0';")
i_parse = hr.find('strncasecmp( cur, "Sec-Fetch-Dest:", 15 )')
check("handle_request clears reaper_sfd before the header loop and parses Sec-Fetch-Dest",
      0 <= i_reset < i_parse, (i_reset, i_parse))
check("the parse copies into reaper_sfd with a bound and trims at whitespace",
      "strlcpy(reaper_sfd, cp, sizeof(reaper_sfd));" in hr and
      "reaper_sfd[strcspn(reaper_sfd, \"\\r\\n \\t\")] = '\\0';" in hr)

CC = shutil.which("gcc") or shutil.which("cc")
if m and CC and sys.platform.startswith("linux"):
    d = tempfile.mkdtemp()
    cf = os.path.join(d, "t.c")
    open(cf, "w").write("#include <stdio.h>\n#include <string.h>\n#include <strings.h>\n"
                        "static char reaper_sfd[16];\n" + m.group(0) +
                        "int main(int c, char **v){ strncpy(reaper_sfd, v[1], sizeof(reaper_sfd)-1);"
                        " printf(\"%d\\n\", reaper_login_landing(v[2])); return 0; }\n")
    exe = os.path.join(d, "t")
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Werror", "-o", exe, cf], capture_output=True, text=True)
    check("the helper compiles", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        def land(dest, url):
            return subprocess.run([exe, dest, url], capture_output=True, text=True).stdout.strip() == "1"
        cases = [("document", "Advanced_LAN_Content.asp", True), ("iframe", "Advanced_LAN_Content.asp", True),
                 ("frame", "Reaper_Samba.asp", True), ("", "Main_ReaperDash.asp", True),
                 ("DOCUMENT", "reaper_shell.asp", True),
                 ("empty", "Reaper_SecBanner.asp", False), ("empty", "Advanced_LAN_Content.asp", False),
                 ("script", "state.js", False), ("", "Reaper_SecBanner.asp", False),
                 ("", "/Reaper_SecBanner.asp", False), ("", "Reaper_SecBanner.asp?x=1", False),
                 ("document", "Reaper_SecBanner.asp", False), ("", "ajax_coretmp.asp", False),
                 ("", "ajax_dms_status.asp", False)]
        bad = [(a, b, e) for a, b, e in cases if land(a, b) != e]
        check("navigations land; background requests, the fragment and ajax_ polls never do", not bad, bad)
    shutil.rmtree(d, ignore_errors=True)
else:
    print("skip the compiled cases (no host compiler on Linux)")

if fails:
    print("\n".join("FAILED: " + f for f in fails)); sys.exit(1)
print("all checks passed")
