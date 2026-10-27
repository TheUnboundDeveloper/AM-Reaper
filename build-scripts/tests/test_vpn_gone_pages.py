#!/usr/bin/env python3
"""Pages that stop shipping bounce to their Reaper replacement (VPN wave, 2026-10-23).

WHY. The Reaper bounce is a script injected into a SERVED stock page, so a page that is removed from the
image cannot redirect: do_ej() returns silently when the file is missing and the browser got an empty 200.
The VPN wave removes the ASUS VPN app, its host page, Instant Guard and the Fusion client list, so httpd
gained reaper_gone[] (reaper_inject.c): a missing page whose name is in the table answers with a tiny page
that bounces to the replacement, query string kept.

WHAT IT DOES. Pins the table, that every target is a page that ships, that the stub runs before the inject
decision and only for a missing file, and that www/Makefile removes every listed page.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "httpd")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c"))
mk = rd(os.path.join(SRC, "www", "Makefile"))
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

# review 2026-10-24 (Q-B-5): one table, reaper_pagemap[] { name, target, shipped }; the gone pages are the shipped = 0 rows
m = re.search(r"reaper_pagemap\[\] = \{(.*?)\n\};", inj, re.S)
check("the page table (reaper_pagemap[]) is present", bool(m))
rows = re.findall(r'\{\s*"([a-z0-9_.]+)",\s*"([^"]+)",\s*0\s*\}', m.group(1)) if m else []
check("table has at least the four VPN-wave pages", len(rows) >= 4 and {r[0] for r in rows} >= {
      "advanced_instant_guard.asp", "advanced_vpnserver_content.asp", "advanced_vpnclient_content.asp",
      "advanced_vpnclientfusion_content.asp"}, rows)
check("the AiMesh wizard's feedback link (failed node join) bounces to the diagnostics page (2026-10-25)",
      ("advanced_feedback.asp", "Reaper_Diag.asp") in rows)
check("every gone name is lower-case and a .asp", all(r[0] == r[0].lower() and r[0].endswith(".asp") for r in rows))
def _ships(page):   # www/ itself, or the SDN overlay that www/Makefile copies in at install (SDN.asp, MLO.asp)
    return os.path.exists(os.path.join(SRC, "www", page)) or os.path.exists(os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", page))
missing = [r[1] for r in rows if not _ships(r[1].split("?")[0])]
check("every target page exists in www (the fragment before any ?tab=)", not missing, missing)
check("targets carry no characters that could break the stub", all(re.fullmatch(r"[A-Za-z0-9_.?=&]+", r[1]) for r in rows))
check("reaper_gone_target() compares the basename case-insensitively",
      "base = strrchr(file, '/');" in inj and "!reaper_pagemap[i].shipped && strcasecmp(base, reaper_pagemap[i].name) == 0" in inj)
out = inj[inj.find("void reaper_output("):]
check("stub runs only for a missing .asp file (review 2026-10-24 Q-B-6: no access() for other fetches), before the inject decision, and keeps the query",
      0 < out.find('if (ext && !strcasecmp(ext, ".asp") && access(file, R_OK) != 0) {') < out.find("mode = reaper_should_inject(handler, file);")
      and 'top.location.replace(\\"/reaper_shell.asp#%s\\"+(q?\\"%s\\"+q:\\"\\"));' in out   # 2026-10-24: & after a ?tab= target
      and "strchr(to, '?') ? \"&\" : \"?\"" in out
      and '<noscript><meta http-equiv=\\"refresh\\"' in out and "#include <unistd.h>" in inj)
# review 2026-10-24 (Q-B-2): handle_request() answered "file not found" before reaper_output() could run the stub
hc = open(os.path.join(SRC, "httpd", "httpd.c"), encoding="utf-8", errors="replace").read()
# 40585 base (merge stop 63): the gate matches on upstream's query-stripped file_path; the stub still gets `file`
# (query kept for the bounce)
g = hc.find("reaper_gone_page(file_path) && !check_if_file_exist(file_path)")
qs = hc.rfind("copy_request_path_without_query(file, file_path, sizeof(file_path));", 0, g)
check("httpd asks reaper_gone_page() and serves the bounce BEFORE its own 404 for a missing page",
      0 < qs < g < hc.find('send_error( 404, "Not Found", (char*) 0, "File not found." );', g) and "int reaper_gone_page(const char *file)" in inj
      and g - qs < 800 and "reaper_output(handler, file, conn_fp);" in hc[g:g + 600])
for name, _ in rows:
    stock = re.sub(r"\.asp$", "", name)
    real = [f for f in os.listdir(os.path.join(SRC, "www")) if f.lower() == name]
    cased = real[0] if real else None
    if cased:
        check("www/Makefile removes %s at install" % cased, re.search(r"rm -r?f[^\n]*\b" + re.escape(cased), mk) is not None)
check("www/Makefile removes the VPN app and its images",
      re.search(r"rm -rf \$\(INSTALLDIR\)/www/VPN \$\(INSTALLDIR\)/www/images/New_ui/VPN", mk) is not None)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall ok")
