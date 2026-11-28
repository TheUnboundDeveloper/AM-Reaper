#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Removed <% %> hooks that break a script when they print nothing (REAPER-HOOK-PLACEHOLDER, owner 2026-11-27).

WHY THIS EXISTS. httpd's page parser (httpd/ej.c call()) prints nothing for a <% name(); %> hook that has no handler.
The native-UI cutover removed many hooks with the stock pages that used them. A third-party add-on page written for
stock Merlin that still uses one as a bare JavaScript value (`var a = <% apps_info("asus"); %>;`) then gets
`var a = ;` - a syntax error that stops the whole script block. ej.c now prints an empty value of the right shape for
the hooks the stock pages used that way, only when no handler matched, and writes one system log line per hook per
httpd run naming the page. This test checks the source and compiles call() on the host (stub headers) to run it.
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
EJ = os.path.join(SRC, "httpd", "ej.c") if SRC else ""
if not EJ or not os.path.isfile(EJ):
    print("SKIP: no router source tree"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(EJ, encoding="utf-8", errors="replace").read()
WANT = [("apps_info", "[]"), ("bwdpi_appStat", "[]"), ("bwdpi_wanStat", "[]"), ("dns_appStat", "[]"), ("dns_wanStat", "[]"),
        ("dns_status", "[]"), ("usb_is_exist", "0"), ("get_label_mac", '""'), ("cpu_core_num", "0")]
tb = src[src.find("ej_removed_hooks[] = {"):]
tb = tb[:tb.find("};")]
rows = [(a, b.replace('\\"', '"')) for a, b in re.findall(r'\{ "([A-Za-z0-9_]+)", "((?:[^"\\]|\\.)*)" \}', tb)]
check("REAPER-HOOK-PLACEHOLDER: the table holds exactly the owner's nine hooks and values", rows == WANT, rows)
check("the table ends with a NULL row", "{ NULL, NULL }" in tb)
cf = src[src.find("\ncall(char *func, FILE *stream)"):]
cf = cf[:cf.find("\n}\n")]
check("call(): a matched flag set by every handler call, the placeholder only when nothing matched",
      "int argc, matched = 0;" in cf and "handler->output(0, stream, argc, argv);\n\t\t\tmatched = 1;" in cf
      and "if (!matched)\n\t\tej_removed_hook(func, stream);" in cf, cf[-400:])
fn = src[src.find("\nej_removed_hook(const char *func, FILE *stream)"):]
fn = fn[:fn.find("\n}\n")]
check("the log line: one bit per row, a static bitmap, once per httpd run, table rows only",
      "static unsigned int logged;" in fn and "!(logged & (1u << i))" in fn and "logged |= 1u << i;" in fn
      and fn.find("continue;") < fn.find("logmessage(") and len(WANT) < 32)
check("do_ej() names the page for the log line and clears it", "ej_cur_page = path;" in src and "ej_cur_page = NULL;" in src)

# none of the nine is a live handler: the placeholder must never stand in for a hook that is built
live = set()
for root, _, fs in os.walk(os.path.join(SRC, "httpd")):
    for f in fs:
        if f.endswith(".c"):
            try: t = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
            except OSError: continue
            t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
            i = t.find("struct ej_handler ej_handlers[] = {")
            if i >= 0:
                live |= set(re.findall(r'\{\s*"([A-Za-z0-9_.-]+)"\s*,', t[i:t.find("\n};", i)]))
check("ej_handlers[] found", len(live) > 100, len(live))
both = sorted(n for n, _ in WANT if n in live)
check("no table hook is still a live handler (it would answer instead; a stale row is dead weight)", not both, both)

CC = shutil.which("gcc") or shutil.which("cc")
if not CC or not sys.platform.startswith("linux"):
    print("SKIP (run part): needs a host compiler on Linux")
else:
    work = tempfile.mkdtemp(prefix="ej_")
    try:
        inc = os.path.join(work, "inc"); os.makedirs(inc)
        open(os.path.join(inc, "httpd.h"), "w").write(
            "#include <stdio.h>\ntypedef FILE *webs_t;\ntypedef char char_t;\n"
            "struct ej_handler { char *pattern; int (*output)(int eid, webs_t wp, int argc, char_t **argv); };\n"
            "extern struct ej_handler ej_handlers[];\n")
        for h in ("bcmnvram.h", "shutils.h", "webapi.h"):
            open(os.path.join(inc, h), "w").write("\n")
        open(os.path.join(inc, "shared.h"), "w").write("void logmessage(const char *ident, const char *fmt, ...);\n")
        harness = r'''
#include <stdarg.h>
#include "%s"
void logmessage(const char *ident, const char *fmt, ...)
{ va_list ap; printf("[LOG %%s: ", ident); va_start(ap, fmt); vprintf(fmt, ap); va_end(ap); printf("]"); }
static int h_get(int eid, webs_t wp, int argc, char_t **argv) { (void)eid; fprintf(wp, "V(%%s)", argc ? argv[0] : ""); return 0; }
static int h_usb(int eid, webs_t wp, int argc, char_t **argv) { (void)eid; (void)argc; (void)argv; fputs("LIVE", wp); return 0; }
struct ej_handler ej_handlers[] = { { "nvram_get", h_get }, { "usb_is_exist", h_usb }, { NULL, NULL } };
int main(int argc, char **argv)
{
	int i;
	for (i = 1; i + 1 < argc; i += 2) {
		char buf[256];
		ej_cur_page = argv[i][0] ? argv[i] : NULL;
		snprintf(buf, sizeof(buf), "%%s", argv[i + 1]);
		call(buf, stdout);
		printf("|\n");
	}
	(void)ejArgs;
	return 0;
}
''' % EJ.replace("\\", "/")
        hp = os.path.join(work, "h.c"); open(hp, "w").write(harness)
        exe = os.path.join(work, "h")
        b = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-Wno-sign-compare",
                            "-Wno-unused-function", "-I", inc, "-o", exe, hp], capture_output=True, text=True)
        check("ej.c call() compiles on the host (-Wall -Wextra -Werror) against stub headers", b.returncode == 0, b.stderr[-800:])
        if b.returncode == 0:
            args = ["/www/user3.asp", 'apps_info("asus")', "/www/user3.asp", 'apps_info("asus")',
                    "/www/user5.asp", "cpu_core_num()", "/www/user5.asp", "get_label_mac()",
                    "/www/x.asp", "dns_status(\"traffic\", \"\", \"realtime\", \"\")", "/www/x.asp", "bwdpi_wanStat(\"\")",
                    "/www/x.asp", "some_unknown_hook()", "/www/x.asp", 'nvram_get("productid")', "/www/x.asp", "usb_is_exist()",
                    "/www/a b\n<i>.asp", "dns_appStat(\"\")", "", "dns_wanStat(\"\")", "/www/x.asp", "bwdpi_appStat(\"\")"]
            out = subprocess.run([exe] + args, capture_output=True, text=True).stdout.split("|\n")
            o = lambda k: out[k] if k < len(out) else "<missing>"
            check("bare-value hook apps_info prints [] and logs the page once", o(0) ==
                  "[][LOG httpd: reaper: page user3.asp uses removed hook apps_info (an empty value was written; logged once)]", o(0))
            check("the same hook again: [] and no second log line", o(1) == "[]", o(1))
            check("cpu_core_num prints 0 (logged)", o(2).startswith("0[LOG httpd: reaper: page user5.asp uses removed hook cpu_core_num"), o(2))
            check('get_label_mac prints "" (logged)', o(3).startswith('""[LOG ') and "get_label_mac" in o(3), o(3))
            check("dns_status / bwdpi_wanStat print []", o(4).startswith("[][LOG ") and o(5).startswith("[][LOG "), (o(4), o(5)))
            check("a hook outside the table still prints nothing and logs nothing", o(6) == "", o(6))
            check("a live handler answers as before", o(7) == "V(productid)", o(7))
            check("a table hook that IS a live handler on this build answers itself, no placeholder, no log", o(8) == "LIVE", o(8))
            check("the logged page name keeps plain file-name characters only", "page abi.asp uses removed hook dns_appStat" in o(9), o(9))
            check("no page known: (unknown)", "page (unknown) uses removed hook dns_wanStat" in o(10), o(10))
            check("each row logs once, independently", o(11).startswith("[][LOG ") and "bwdpi_appStat" in o(11), o(11))
    finally:
        shutil.rmtree(work, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
