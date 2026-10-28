#!/usr/bin/env python3
"""System Log: Find / Exclude lists and the saved exclusions (2026-10-26).

WHY. A user asked for three things the stock page never had: several search words at once, an exclude box, and
their own version of logFilter.json (the stock file sits in the read-only image, so nobody could add to it). Find
and Exclude now take comma-separated lists, and the saved exclusions live in /jffs/reaper/logfilter, read and
written through reaper_logf.cgi behind the http_id gate. Only the page view changes; the log file, Save and a
remote syslog server still get every line.

WHAT IT DOES. Lifts rlogf_ok() out of httpd/web.c and runs its edge cases under the host gcc (skipped without one);
checks the CGI is registered behind do_auth with the gate first, that an empty list removes the file, that the
list rides the Reaper settings file (export + validated import), that the page splits both boxes on commas, sends
the token, keeps the saved list for the System log only, and that all 25 language packs carry RLOG_89-101.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
web, page = rd("httpd/web.c"), rd("www/Reaper_Log.asp")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

# ---- httpd
check("reaper_logf.cgi is registered behind do_auth",
      re.search(r'\{ "reaper_logf\.cgi\*", "application/json", no_cache(?:_IE7)?, do_html_post_and_get, do_reaper_logf_cgi, do_auth \}', web))
m = re.search(r'\ndo_reaper_logf_cgi\(char \*url, FILE \*stream\)\n\{(.*?)\n\}\n', web, re.S)
body = m.group(1) if m else ""
check("the handler refuses anything without the token before reading an action", body.find("reaper_gate()") >= 0 and
      body.find("reaper_gate_deny") < body.find('"get"'), body[:200])
check("save validates the whole list first, then writes through rjf_set or removes the file when empty",
      body.find("rlogf_ok(v)") < body.find("rjf_set(RLOGF_FILE") and "unlink(RLOGF_FILE)" in body)
check("the list is read without following a link (rview_slurp, bounded)", "rview_slurp(RLOGF_FILE, RLOGF_BYTES)" in body)
check("the file is /jffs/reaper/logfilter, 64 entries of 128", '#define RLOGF_FILE\t"/jffs/reaper/logfilter"' in web and
      re.search(r'#define RLOGF_MAX\t64\b', web) and re.search(r'#define RLOGF_LINE\t128\b', web))
check("the settings file carries it: table row, export, validated import",
      # 2026-10-27: export / import go through rcfg_get / rcfg_put
      '{ "log",    "rlog_filter",     RLOGF_BYTES }' in web and "rview_slurp(RLOGF_FILE, RLOGF_BYTES)" in web and
      'if (!strcmp(nv, "rlog_filter"))\t/* 2026-10-26: multi-line, its own gate */' in web and
      'return (rlogf_ok(v) != 0 || (*v ? rjf_set(RLOGF_FILE, v, "log") != 0 : (unlink(RLOGF_FILE), 0))) ? -1 : 0;' in web)

v = re.search(r'\nstatic int rlogf_ok\(const char \*v\)\n\{.*?\n\}\n', web, re.S)
check("rlogf_ok() found", v)
CC = shutil.which("gcc") or shutil.which("cc")
if v and CC:
    work = tempfile.mkdtemp(prefix="rlogf_")
    try:
        c = os.path.join(work, "t.c")
        open(c, "w").write(r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define RLOGF_MAX 64
#define RLOGF_LINE 128
#define RLOGF_BYTES (RLOGF_MAX * (RLOGF_LINE + 1))
''' + v.group(0) + r'''
static char *rep(char ch, int n){ char *s = malloc(n + 1); memset(s, ch, n); s[n] = 0; return s; }
int main(void){
	static char big[RLOGF_BYTES + 16]; int i;
	#define T(x) printf("%d\n", rlogf_ok(x))
	T(""); T("dnsmasq"); T("dnsmasq\nwlceventd\n"); T("a, b, c"); T("x\n\n\ny");
	T("tab\there"); T("cr\r\n"); T("\x7f"); T("caf\xc3\xa9");
	T(rep('a', 128)); T(rep('a', 129));
	for (i = 0; i < 64; i++) strcat(big, "ab\n");
	T(big); strcat(big, "c"); T(big);
	return 0;
}
''')
        exe = os.path.join(work, "t")
        r = subprocess.run([CC, "-Wall", "-o", exe, c], capture_output=True, text=True)
        check("the validator compiles on its own", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            got = subprocess.run([exe], capture_output=True, text=True).stdout.split()
            want = ["0", "0", "0", "0", "0", "-1", "-1", "-1", "-1", "0", "-1", "0", "-1"]
            names = ["empty", "one word", "two lines", "commas inside an entry", "blank lines", "tab", "CR", "DEL",
                     "UTF-8", "128 bytes", "129 bytes", "64 entries", "65 entries"]
            for n, g, w in zip(names, got, want):
                check("validator: %s -> %s" % (n, "accepted" if w == "0" else "refused"), g == w, g)
            check("validator: every case ran", len(got) == len(want), got)
    finally:
        shutil.rmtree(work, ignore_errors=True)
else:
    print("skip the validator run (no C compiler)")

# ---- page
check("Find and Exclude are both on the bar", 'id="find" placeholder="<#RLOG_89#>"' in page and 'id="excl" placeholder="<#RLOG_90#>"' in page)
check("both boxes split on commas, blanks dropped, case ignored",
      "function words(id){ return q(id).value.split(',').map(function(w){ return w.trim().toLowerCase(); }).filter(Boolean); }" in page)
check("a line shows with ANY Find word; any Exclude or saved word hides it",
      "if (hasAny(low, saved) || hasAny(low, drop)){ hidden++; continue; }" in page and "if (want.length && !hasAny(low, want)) continue;" in page)
check("the saved list and the built-in list apply to the System log only, and only while ticked",
      "var keep = view === 'sys' && q('c_lfon').checked" in page)
check("the page sends the token with every request to reaper_logf.cgi",
      "f.append('http_id', HID);" in page and "'/reaper_logf.cgi'" in page and "var HID = <% nvram_get_js(\"http_id\"); %>;" in page)
check("the page checks the limits before sending", "list.length > LFMAX" in page and "s.length > LFLEN" in page)
check("the page stays ASCII", all(ord(ch) < 128 for ch in page))

# ---- language packs
www = os.path.join(SRC, "www")
packs = [f for f in os.listdir(www) if f.endswith(".dict")]
keys = ["RLOG_%d" % n for n in range(89, 102)]
short = []
for f in packs:
    t = open(os.path.join(www, f), encoding="utf-8", errors="replace").read()
    if "\nRLOG_01=" not in t:
        continue                                   # not a language pack
    miss = [k for k in keys if "\n%s=" % k not in t]
    if miss: short.append((f, miss[:3]))
check("every language pack carries RLOG_89-101", not short, short)
check("RLOG_97 keeps its %1 count in English", re.search(r'\nRLOG_97=[^\n]*%1', open(os.path.join(www, "EN.dict"), encoding="utf-8").read()))

print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
