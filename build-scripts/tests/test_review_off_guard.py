#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Security Review is switched off in one place only: its own switch on the Firewall page.

WHY THIS EXISTS. Two paths besides the page could switch the review off: the generic settings handler (rwatch_review
and rwatch_enable are ordinary settings to it) and a settings-file import. Owner decision 2026-11-21: both refuse to
switch either OFF; switching on stays free. The page's own switch asked for the admin password from 2026-11-21; the
owner removed that password on 2026-11-23 (REAPER-REVIEW-NOPW) - the switch posts at once, the guard stays.

WHAT IT DOES. Lifts reaper_review_off_refused() out of httpd/web.c, compiles it with stub settings and plays every
case; pins its two call sites; pins that the page's switch and its rules save send no password and the handler asks
for none. Exit 0 pass, 1 fail, 77 skipped (no router source tree; without gcc that part is skipped, pins still run).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WEB = os.path.join(SRC, "httpd", "web.c")
PAGE = os.path.join(SRC, "www", "Reaper_Firewall.asp")
if not SRC or not os.path.isfile(WEB) or not os.path.isfile(PAGE):
    print("SKIP: no router source tree with httpd/web.c and www/Reaper_Firewall.asp"); sys.exit(77)
web = open(WEB, encoding="utf-8", errors="replace").read()
page = open(PAGE, encoding="utf-8", errors="replace").read()

fails, skipped = [], []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

# ---------------------------------------------------------------- the helper, compiled
m = re.search(r"static int reaper_review_off_refused\(const char \*name, const char \*val, const char \*via\)\n\{.*?\n\}\n", web, re.S)
fn = m.group(0) if m else ""
check("reaper_review_off_refused() is in httpd/web.c", bool(fn))
i_fn, i_va = web.find("static int reaper_review_off_refused("), web.find("\nint validate_apply(webs_t wp")
check("it is defined before the generic settings handler that calls it", 0 < i_fn < i_va)

HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
static const char *NV[][2] = { {"rwatch_review", ""}, {"rwatch_enable", ""}, {"gk_enable", "1"} };
static int nvram_match(char *n, char *v) { unsigned i; for (i = 0; i < 3; i++) if (!strcmp(NV[i][0], n)) return !strcmp(NV[i][1], v); return 0; }
static int LOGS; static char LAST[512];
static void logmessage(char *h, char *fmt, ...) { va_list a; (void)h; va_start(a, fmt); vsnprintf(LAST, sizeof(LAST), fmt, a); va_end(a); LOGS++; }
static const char *rbk_peer(void) { return "192.168.50.9"; }
%s
static void set(const char *r, const char *e) { NV[0][1] = r; NV[1][1] = e; }
int main(void)
{
	struct { const char *r, *e, *name, *val; int want; } c[] = {
		{"1","1","rwatch_review","0",1}, {"1","1","rwatch_review","",1}, {"1","1","rwatch_review",NULL,1},
		{"1","1","rwatch_review","2",1}, {"1","1","rwatch_review","1",0}, {"0","1","rwatch_review","0",0},
		{"","1","rwatch_review","0",0},  {"0","1","rwatch_review","1",0},
		{"1","1","rwatch_enable","0",1}, {"1","0","rwatch_enable","0",0}, {"1","1","rwatch_enable","1",0},
		{"1","1","gk_enable","0",0},     {"1","1","rwatch_review_seal","",0}, {"1","1","rwatch_iv","0",0},
		{"1","1",NULL,"0",0},
	};
	unsigned i; int bad = 0, before;
	for (i = 0; i < sizeof(c) / sizeof(c[0]); i++) {
		set(c[i].r, c[i].e); before = LOGS; LAST[0] = 0;
		int got = reaper_review_off_refused(c[i].name, c[i].val, "the settings handler");
		int logged = LOGS - before;
		if (got != c[i].want || logged != c[i].want) { printf("case %%u: got %%d logged %%d want %%d\n", i, got, logged, c[i].want); bad++; }
		if (got && (!strstr(LAST, "REFUSED from 192.168.50.9") || !strstr(LAST, "the settings handler"))) { printf("case %%u: log line %%s\n", i, LAST); bad++; }
		if (got && c[i].val && *c[i].val && strstr(LAST, "=")) { printf("case %%u: the log line carries a value\n", i); bad++; }
	}
	printf("cases %%u bad %%d\n", (unsigned)(sizeof(c) / sizeof(c[0])), bad);
	return bad ? 1 : 0;
}
'''
gcc = shutil.which("gcc") or shutil.which("cc")
if fn and gcc:
    d = tempfile.mkdtemp(prefix="rvoff.")
    try:
        open(os.path.join(d, "t.c"), "w").write(HARNESS % fn)
        b = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", "-o", os.path.join(d, "t"), os.path.join(d, "t.c")], capture_output=True, text=True)
        check("the helper compiles clean (-Wall -Wextra -Werror)" + ("" if b.returncode == 0 else ": " + b.stderr[:300]), b.returncode == 0)
        if b.returncode == 0:
            r = subprocess.run([os.path.join(d, "t")], capture_output=True, text=True)
            check("15 cases: OFF refused and logged once while on (review and watchdog); ON, already-off and other settings pass"
                  + ("" if r.returncode == 0 else ": " + r.stdout[-300:]), r.returncode == 0 and "cases 15 bad 0" in r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)
elif fn:
    skipped.append("gcc")

# ---------------------------------------------------------------- the two call sites
va = web[i_va:i_va + 9000] if i_va > 0 else ""
a = va.find("value = reaper_rsec_unmask(wp, name, value, rsec_buf, sizeof(rsec_buf));")
b = va.find('if (reaper_review_off_refused(name, value, "the settings handler"))')
c = va.find("nvram_check(name, value, t, dec_passwd)")
check("the generic settings handler asks it for every posted setting, before the value is checked or stored",
      0 < a < b < c and va[b:b + 200].split("\n")[1].strip() == "continue;")
imp = web[web.find("static int rcfg_import_json("):]
imp = imp[:imp.find("\n}\n")]
f2 = imp.find('if (!strcmp(s, "fw") && fw_armed) { rejected++; continue; }')
g = imp.find('if (reaper_review_off_refused(n, json_object_get_string(val), "a settings file")) { rejected++; continue; }')
p = imp.find("if (rcfg_put(i, json_object_get_string(val)) != 0)")
check("the settings-file import asks it before a value is put, and counts a refusal as rejected", 0 < f2 < g < p)
check("exactly three uses in web.c (the definition and the two callers)", web.count("reaper_review_off_refused(") == 3)
# REAPER-REVIEW-NOPW (2026-11-23, owner): the page's own switch and its rules save carry no password, and the handler
# asks for none - the guard above is what keeps the switch in one place
check("the page's own switch writes the setting with no password asked (reaper_watch.cgi action=set)",
      "rview_reauth" not in web and "rview_body_pw" not in web and 'nvram_set("rwatch_review", on ? "1" : "0");' in web)
check("no factory-default row makes the seal writable through the generic handler",
      not re.search(r'\{\s*"rwatch_review_seal"', open(os.path.join(SRC, "shared", "defaults.c"), encoding="utf-8", errors="replace").read())
      if os.path.isfile(os.path.join(SRC, "shared", "defaults.c")) else True)
check("the page sends no password: no admpw, no password box, the switch and the rules save post directly",
      "admpw" not in page and "password:" not in page and "RV_PWL" not in page
      and "rvpost('action=set&enable='+(on?'1':'0'),function(j){" in page
      and "rvpost('action=rules_set&rules='+encodeURIComponent(text),function(j){" in page)

if skipped: print("note: skipped parts (not on this host): " + ", ".join(skipped))
print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
sys.exit(1 if fails else (77 if skipped and len(skipped) == 2 else 0))
