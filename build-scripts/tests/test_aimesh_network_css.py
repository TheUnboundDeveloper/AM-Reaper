#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AiMesh and Network pages: their Reaper look is a stylesheet of their own, linked by the page (owner, 2026-11-01).

WHY THIS EXISTS. The two stock pages Reaper keeps - AiMesh (AiMesh.asp) and Network (SDN.asp, the network app
/SDN/sdn.html it frames, /SDN/mlo.html) - were themed by the shared stock-page skin reaper/reaper_content.css that
httpd injects into stock pages. Owner: no stock UI and no injected theme. They now carry their own files,
reaper/reaper_content_aimesh.css and reaper/reaper_content_network.css (built from that skin, computed styles
compared old vs new in a browser: identical), linked by each page as the LAST stylesheet in its <head> - the slot
httpd's injection used, so the cascade is unchanged. httpd injects no stylesheet into them (reaper_own_theme[],
the reaper-native treatment: link floor + shell bounce), and the stock alternate themes (WHITE/ROG/TUF) never load
and do not ship.

WHAT IT CHECKS. (1) the files: present, ASCII/LF, balanced, the page-defining rules; (2) each of the four
documents links its own file exactly once, as the last stylesheet before </head>, and never reaper_content.css;
the stock theme switch is forced off; (3) httpd: reaper_inject.c compiles on the host; the four paths (query or
not, any case) are served the bounce with NO stylesheet and no SUP map; dashboard/pages/sdn.html, XSDN.asp and a
stock page still get the shared skin; the interim stylesheet table is gone; (4) the www Makefile drops the eight
alternate-theme files; (5) the shell's runtime re-injector keys on the "reaper_content" prefix the files carry.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
INJ = os.path.join(SRC, "httpd", "reaper_inject.c") if SRC else ""
if not INJ or not os.path.isfile(INJ):
    print("SKIP: no router source tree"); sys.exit(77)
WWW = os.path.join(SRC, "www")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))
def read(rel):
    p = os.path.join(WWW, rel)
    return open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""

AIM, NET, SKIN = "/reaper/reaper_content_aimesh.css", "/reaper/reaper_content_network.css", "/reaper/reaper_content.css"

# ---------- (1) the files ----------
files = {}
for n in ("reaper_content_aimesh.css", "reaper_content_network.css"):
    p = os.path.join(WWW, "reaper", n)
    b = open(p, "rb").read() if os.path.isfile(p) else b""
    check("www/reaper/%s exists" % n, bool(b))
    files[n] = b.decode("ascii", "replace")
    check("%s is pure ASCII and LF (the minifier strips non-ASCII)" % n, b and max(b) < 128 and b"\r" not in b)
    body = re.sub(r"/\*.*?\*/", "", files[n], flags=re.S)
    check("%s: braces balance" % n, body.count("{") == body.count("}") and body.count("{") > 100, (body.count("{"), body.count("}")))
    check("%s: its header says the page links it and httpd injects none" % n,
          "reaper_own_theme[]" in files[n] and "last stylesheet in its <head>" in files[n])
aim, net = files["reaper_content_aimesh.css"], files["reaper_content_network.css"]
check("AiMesh: the node-card backdrop (RLogo) and its height knob", ".primary_info_bg::before" in aim and "RLogo.png" in aim and "234px" in aim)
check("AiMesh: top tabs keep the maroon underline, not the red fill", ".aimesh_tab > span.clicked" in aim)
check("AiMesh: the stock chrome strip (banner/menu/footer hidden)", "#TopBanner,#mainMenu,#subMenu,#footer" in aim)
check("Network: the SPA palette override and the main-network section labels", "rwd_component" in net and ".sdn_section_title" in net)
check("Network: toggles stay neutral grey, never crimson (standing rule 11)",
      re.search(r"\.sdn_switch\.on[^{]*\{\s*background-color:#6b6b72", net) is not None)
check("Network: the stock chrome strip", "#TopBanner,#mainMenu,#subMenu,#footer" in net)
check("the files are not copies of the shared skin (rules for other pages left out)",
      "#internetSpeed_iframe" not in aim and "#internetSpeed_iframe" not in net and ".aimesh_tab" not in net)

# ---------- (2) the pages link their own file; no stock theme switch ----------
for rel, want in (("AiMesh.asp", AIM), ("sysdep/FUNCTION/SDN/SDN.asp", NET),
                  ("sysdep/FUNCTION/SDN/SDN/sdn.html", NET), ("sysdep/FUNCTION/SDN/SDN/mlo.html", NET)):
    t = read(rel)
    head = t[:t.find("</head>")] if "</head>" in t else ""
    links = re.findall(r'<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"|<link[^>]*rel=\'stylesheet\'[^>]*href=\'([^\']+)\'', head)
    hrefs = [a or b for a, b in links]
    check("%s: links %s once, as the LAST stylesheet before </head>" % (rel, want),
          head.count(want) == 1 and hrefs and hrefs[-1] == want, hrefs[-3:])
    check("%s: never links the shared skin" % rel, SKIN not in t)
for rel in ("AiMesh.asp", "sysdep/FUNCTION/SDN/SDN/sdn.html", "sysdep/FUNCTION/SDN/SDN/mlo.html"):
    t = read(rel)
    check("%s: the stock theme switch is forced off (no WHITE/ROG/TUF variant can load)" % rel,
          'var theme = "";' in t and not re.search(r'var theme = getSafeTheme\("current_theme"', t))

# ---------- (4) the alternate themes do not ship ----------
mk = read("Makefile")
for f in ("SDN/sdn_WHITE.css", "SDN/sdn_ROG.css", "SDN/sdn_TUF.css", "SDN/mlo_WHITE.css", "SDN/mlo_ROG.css",
          "SDN/mlo_TUF.css", "aimesh/aimesh_topology_WHITE.css", "aimesh/aimesh_system_settings_WHITE.css"):
    check("www/Makefile removes %s" % f, re.search(r"\n\trm -f [^\n]*\$\(INSTALLDIR\)/www/" + re.escape(f) + r"\b", mk) is not None)

# ---------- (5) the shell's re-injector ----------
shell = read("reaper_shell.asp")
check("reaper_shell.asp re-injects the skin only where no link[href*=\"reaper_content\"] exists",
      "link[href*=\"reaper_content\"]" in shell)

# ---------- (3) httpd ----------
src = open(INJ, encoding="utf-8").read()
m = re.search(r"static const char \*reaper_own_theme\[\] = \{([^}]*)\};", src)
names = re.findall(r'"([^"]+)"', m.group(1)) if m else []
check("reaper_own_theme[]: exactly AiMesh.asp, SDN.asp, SDN/sdn.html, SDN/mlo.html",
      sorted(names) == sorted(["AiMesh.asp", "SDN.asp", "SDN/sdn.html", "SDN/mlo.html"]), names)
code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)	# comments may name the files; code must not emit them
check("the interim stylesheet table is gone (httpd links no page stylesheet)",
      "reaper_page_css" not in code and "reaper_put_css" not in code and "reaper_content_aimesh" not in code
      and "reaper_content_network" not in code)

CC = shutil.which("gcc") or shutil.which("cc")
if CC and sys.platform.startswith("linux"):
    work = tempfile.mkdtemp(prefix="pcss_")
    try:
        inc = os.path.join(work, "inc"); os.makedirs(inc)
        open(os.path.join(inc, "bcmnvram.h"), "w").write(
            "char *nvram_get(const char *n);\nint nvram_match(const char *n, const char *v);\n")
        open(os.path.join(inc, "httpd.h"), "w").write(
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
        check("reaper_inject.c compiles on the host (-Wall -Wextra -Werror)", b.returncode == 0, b.stderr[-800:])
        if b.returncode == 0:
            os.chdir(work)
            for d in ("SDN", "dashboard/pages"): os.makedirs(d, exist_ok=True)
            for n in ("AiMesh.asp", "SDN.asp", "SDN/sdn.html", "SDN/mlo.html", "dashboard/pages/sdn.html", "XSDN.asp",
                      "Advanced_Stock_Page.asp", "aimesh.asp"):
                open(n, "w").write("x")
            PAGE = "<html><head><title>x</title></head><body>B</body></html>"
            def head(name):
                o = subprocess.run([exe, name, PAGE], capture_output=True, text=True).stdout
                return o[:o.index("</head>")] if "</head>" in o else o
            for name in ("AiMesh.asp", "SDN.asp", "SDN/sdn.html", "SDN/mlo.html", "SDN/sdn.html?current_theme=ROG", "aimesh.asp"):
                h = head(name)
                check("%s: the shell bounce only - no stylesheet injected, no SUP map" % name,
                      "<link" not in h and "if(self===top){var rp=" in h and "var SUP=" not in h, h[:300])
            for name in ("dashboard/pages/sdn.html", "XSDN.asp", "Advanced_Stock_Page.asp"):
                h = head(name)
                check("%s: still the shared skin + SUP (match is on whole path components)" % name,
                      ('href="%s"' % SKIN) in h and "var SUP={" in h, h[:300])
        os.chdir("/")
    finally:
        shutil.rmtree(work, ignore_errors=True)
else:
    print("note: no host compiler on Linux - serve checks skipped (source checks ran)")

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
