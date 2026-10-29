#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""httpd's injected head blocks - written in pieces from one page table (review 2026-10-24, Q-B-4 / Q-B-5).

WHY THIS EXISTS. reaper_inject.c used to hold four whole `static const char[]` blocks built from the same macros
(~13 KB of duplicate rodata in httpd's RAM) and the page->replacement map twice: a JS literal (SUP) inside the
bounce script and the C table reaper_gone[] - two hand-kept lists of 60+ rows that had already drifted (six gone
pages without a SUP row, one row with a different target). Now: one copy of each piece, written per mode, and
one table, reaper_pagemap[], from which both the gone-page stub and the SUP literal come. The serve path is C
that only the image build compiles, so this test compiles reaper_inject.c on the host against stub headers and
serves a page through reaper_output() in every mode.

WHAT IT DOES. (1) Builds a harness around reaper_inject.c with a fake mime handler and a fake nvram. (2) For each
mode (stock page, reaper-native, first-run gate, banner-only, skipped) it serves a page and checks the head: the
right pieces in the right order, the block exactly once before </head>, the body untouched. (3) Parses the SUP
literal out of the served stock page and checks it equals reaper_pagemap[] exactly (every row, shipped or not);
(4) the gone-page stub answers for an unshipped name only, never for a shipped one; (5) a page with no </head>
is served verbatim; a body holding '<' everywhere still finds the one </head> (the memchr search).
Exit 0 pass, 1 fail, 77 skipped.
"""
import json, os, re, shutil, subprocess, sys, tempfile

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
rows = re.findall(r'\{ "([a-z0-9_.]+)",\s*"([^"]+)",\s*([01]) \}', src[src.index("reaper_pagemap[] = {"):])
check("reaper_pagemap[] parses (one table, ~69 rows)", len(rows) >= 60, len(rows))
check("no second copy of the map: no SUP literal and no reaper_gone[] table left in the source",
      '\\"advanced_' not in src and "reaper_gone[] = {" not in src and "static const char REAPER_BLOCK[]" not in src)
names = [r[0] for r in rows]
check("every name appears once", len(names) == len(set(names)))
check("the SNMP row exists only on a build with snmpd (Reaper_SNMP.asp ships only then; review 1.2)",
      re.search(r'#ifdef RTCONFIG_SNMPD[^\n]*\n\t\{ "advanced_snmp_content\.asp", "Reaper_SNMP\.asp", 0 \},\n#endif', src) is not None)

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
char *nvram_get(const char *n) { (void)n; return "1"; }
int nvram_match(const char *n, const char *v) { (void)n; (void)v; return 0; }
static const char *BODY;
static void out(char *file, FILE *f) { (void)file; fputs(BODY, f); }
int main(int argc, char **argv)
{
	struct mime_handler h = { "*.asp", "text/html", NULL, NULL, out, NULL };
	if (argc < 3) return 2;
	BODY = argv[2];
	reaper_output(&h, argv[1], stdout);
	return 0;
}
'''
    hp = os.path.join(work, "h.c"); open(hp, "w").write(harness)
    exe = os.path.join(work, "h")
    b = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-Wno-unused-parameter",
                        "-I", inc, "-o", exe, hp, INJ], capture_output=True, text=True)
    check("reaper_inject.c compiles on the host (-Wall -Wextra -Werror) against stub headers", b.returncode == 0, b.stderr[-800:])
    if b.returncode:
        raise SystemExit
    os.chdir(work)                       # a served file "exists" when it is in the cwd (access())
    def serve(name, body):
        return subprocess.run([exe, name, body], capture_output=True, text=True).stdout
    PAGE = "<html><head><title>x</title></head><body>B</body></html>"
    for n in ("Advanced_Stock_Page.asp", "Reaper_LAN.asp", "Main_ReaperDash.asp", "reaper_shell.asp", "Main_Login.asp",
              "Advanced_Wireless_Content.asp", "Main_Password.asp"):
        open(n, "w").write("x")
    stock = serve("Advanced_Stock_Page.asp", PAGE)
    head = stock[:stock.index("</head>")]
    check("stock page: theme link, reaper_content.css, the bounce with the SUP map, before </head>, body untouched",
          stock.startswith("<html><head><title>x</title><style>") and 'href="/reaper/reaper_content.css"' in head
          and "var SUP={" in head and "if(self===top){location.replace" in head and stock.endswith("</head><body>B</body></html>")
          and stock.count("</head>") == 1 and "Reaper_SecBanner.asp" not in stock)
    m = re.search(r"var SUP=(\{.*?\});", stock)
    sup = json.loads(m.group(1)) if m else {}
    check("the SUP map served equals reaper_pagemap[] exactly (shipped and gone rows)", sup == {r[0]: r[1] for r in rows},
          set(sup.items()) ^ set((r[0], r[1]) for r in rows))
    check("the one row the two lists disagreed on now has one target", sup.get("main_security_change_notification.asp") == "Reaper_Log.asp?view=login")
    check("the gone pages that had no SUP row bounce from a served copy too",
          all(k in sup for k in ("advanced_instant_guard.asp", "advanced_multisubnet_content.asp",
                                 "advanced_vpnclientfusion_content.asp", "advanced_vpnserver_content.asp")))
    # 2026-10-26 (owner): the VLAN Switch / Profile pair is a live stock page again (stock shows it WITH mtlancfg) -
    # no row may bounce it to SDN.asp
    check("LAN > VLAN is not bounced: no SUP row for the VLAN Switch / Profile pages",
          "advanced_vlan_switch_content.asp" not in sup and "advanced_vlan_profile_content.asp" not in sup)
    nat = serve("Reaper_LAN.asp", PAGE)
    check("reaper-native page: the link floor and the small self-top bounce only (no SUP, no reaper_content.css, no banner)",
          "if(self===top){var rp=" in nat and "var SUP=" not in nat and "reaper_content.css" not in nat and "Reaper_SecBanner.asp" not in nat)
    for n in ("Main_ReaperDash.asp", "reaper_shell.asp"):
        bo = serve(n, PAGE)
        check("banner-only surface %s: the banner loader, no bounce, no stylesheet" % n,
              "Reaper_SecBanner.asp" in bo and "var SUP=" not in bo and "reaper_content.css" not in bo)
    lg = serve("Main_Login.asp", PAGE)
    check("a skipped page (login) is served pristine", lg == PAGE, lg[:200])
    gone = [r for r in rows if r[2] == "0"]; kept = [r for r in rows if r[2] == "1"]
    g = gone[0]
    st = serve(g[0].replace("advanced", "Advanced"), PAGE)
    check("an unshipped page answers with the bounce stub to its target", "/reaper_shell.asp#%s" % g[1] in st and "B</body>" not in st, st[:200])
    k = kept[0]
    ks = serve(k[0] + ".missing.asp", PAGE)
    check("a name not in the table is not a gone page", "reaper_shell.asp#" not in ks.split("<script>")[0])
    check("a shipped row is never answered with the stub, even when the file is absent",
          all("<noscript><meta http-equiv" not in serve(r[0], PAGE) for r in kept))
    check("no </head>: the body goes out verbatim", serve("Advanced_Stock_Page.asp", "<p>a<b>c</p>") == "<p>a<b>c</p>")
    many = "<" * 5000 + "<head></head>" + "<" * 50
    out = serve("Advanced_Stock_Page.asp", many)
    check("a body full of '<' still finds the one </head> (memchr search)", out.count("var SUP={") == 1 and out.endswith("</head>" + "<" * 50))
except SystemExit:
    pass
finally:
    os.chdir("/")
    shutil.rmtree(work, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
