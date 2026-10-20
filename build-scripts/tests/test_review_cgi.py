#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Security Review CGI helpers: per-item accept, rules validation, the accept log - compiled on the host.

WHY THIS EXISTS. Reviewer feedback 2026-10-20: the review flagged the same churning /jffs files on
every run, and an acceptance was not traceable. The fix added operator rules (rwatch, tested by
test_rwatch_review.py), a per-row Accept that folds ONE item into the baseline, a rules editor, and a
log of every acceptance and rules change - all in httpd/web.c, which cannot be compiled whole on a
host. The helpers are self-contained, so this test lifts them out of web.c and runs them.

WHAT IT DOES. Extracts rview_slurp .. rview_rules_ok from web.c, compiles them with stubs (rjf_set
writes the file, websWrite prints), and asserts:
  - rview_same_item: a file is one item whatever its mode letter (S/A/K/E); C/N match on type+key;
    a key that is only a prefix does not match;
  - rview_fold_one: the item's baseline line is replaced by its live line, a gone item leaves the
    baseline, other lines untouched and in order, an unknown item reports no hit, a missing final
    newline is repaired;
  - rview_rules_ok: the four modes, the three pattern kinds, comments and blanks; a quote,
    backslash, backtick, control byte, unknown mode, bare mode, relative path, an over-long line and
    more than 100 rules are refused;
  - rview_alog: tab-separated time / client / action / detail, a newline or tab in the detail is
    flattened, the log keeps the newest 200 entries;
  - rview_fold_summary: counts by status from a diff, keys listed;
and statically: the CGI wires ack (with the summary), ack_one, rules, rules_set and log behind the
same gate, and Accept-all no longer audits a bare "accepted".
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WEB = os.path.join(SRC, "httpd", "web.c")
if not SRC or not os.path.isfile(WEB):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

web = open(WEB, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

a = web.find("static char *rview_slurp(const char *path, size_t max)")
b = web.find("static int rview_rules_ok(const char *s)")
if a < 0 or b < 0:
    print("FAIL helpers not found in web.c"); sys.exit(1)
b = web.find("\n}\n", b) + 3
helpers = web[a:b]

# ---- static wiring
cgi = web[web.find("do_reaper_watch_cgi(char *url, FILE *stream)"):]
cgi = cgi[:cgi.find("\n}\n")]
for act in ("ack", "ack_one", "rules", "rules_set", "log"):
    check("the review CGI handles action=%s" % act, ('!strcmp(action, "%s")' % act) in cgi)
check("every action sits behind reaper_gate()", cgi.find("reaper_gate()") < cgi.find('!strcmp(action, "status")'))
check("Accept-all audits and logs WHAT it folded in",
      'reaper_audit("review", "baseline", sum);' in cgi and 'rview_alog("accept-all", sum);' in cgi
      and 'reaper_audit("review", "baseline", "accepted");' not in cgi)
check("per-row accept and a rules save are audited and logged",
      'rview_alog("accept-one", d);' in cgi and 'rview_alog("rules", d);' in cgi)
check("the rules and the accept log live on /jffs (they survive a firmware update)",
      '#define RVIEW_RULES   "/jffs/reaper/review/rules"' in web and '#define RVIEW_ALOG    "/jffs/reaper/review/accept.log"' in web)
check("httpd's rules path is rwatch's", '"RV_RULES=/jffs/reaper/review/rules\\n"' in open(os.path.join(SRC, "rc", "rwatch.c"), encoding="utf-8", errors="replace").read())
check("the fold never strcat's over the baseline (quadratic on 200 KB)", "strcat(" not in helpers)
check("JSON strings go through gk_json_esc (buffered) - never a websWrite per character",
      cgi.count("gk_json_esc(stream,") >= 4 and "rview_json_str" not in web)
check("the settings export/import carries the rules: exported from the /jffs file, imported through rview_rules_ok, logged",
      '{ "watch",  "rwatch_rules",    RVIEW_RULES_BYTES + 1 },' in web
      and 'char *rv = rview_slurp(RVIEW_RULES, RVIEW_RULES_BYTES);' in web
      and 'if (!v || rview_rules_ok(v) != 0) { rejected++; continue; }' in web
      and 'rview_alog("rules", "imported from a settings file");' in web)

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
static char reaper_client_ip[128] = "192.168.50.20";
static char RVIEW_DIFF[512], RVIEW_ALOG[512];
#define RVIEW_RULES_MAX   100
#define RVIEW_RULES_BYTES 8192
#define RVIEW_ALOG_LINES  200
static int rjf_set(const char *path, const char *v, const char *tag)
{ FILE *f = fopen(path, "w"); (void)tag; if (!f) return -1; fputs(v, f); fclose(f); return 0; }
#define websWrite fprintf
''' + helpers + r'''
static void show_fold(const char *tag, const char *b0, const char *i0, char t, const char *k)
{
	char *b = strdup(b0), *i = strdup(i0), *o; int hit;
	o = rview_fold_one(b, i, t, k, &hit);
	printf("%s hit=%d [", tag, hit);
	for (char *p = o; *p; p++) putchar(*p == '\n' ? '|' : *p == '\t' ? '>' : *p);
	printf("] restored=%d\n", !strcmp(b, b0) && !strcmp(i, i0));
	free(b); free(i); free(o);
}
int main(int argc, char **argv)
{
	char sum[640], big[9000], longl[400]; int i;
	memcpy(longl, "ignore /jffs/", 13); memset(longl + 13, 'a', 300); strcpy(longl + 313, "\n");	/* a 313-byte rule line */
	snprintf(RVIEW_DIFF, sizeof(RVIEW_DIFF), "%s/diff", argv[1]);
	snprintf(RVIEW_ALOG, sizeof(RVIEW_ALOG), "%s/accept.log", argv[1]);
	(void)argc;
	printf("same S~E=%d A~K=%d S~C=%d C~C=%d N~N=%d prefix=%d\n",
		rview_same_item("S\t/jffs/scripts/x\tmd5 -rw", 'E', "/jffs/scripts/x"),
		rview_same_item("A\t/jffs/addons/a\t1 Oct 1 10:00", 'K', "/jffs/addons/a"),
		rview_same_item("S\t/jffs/scripts/x\tm", 'C', "/jffs/scripts/x"),
		rview_same_item("C\t0 3 * * * x #b#\t-", 'C', "0 3 * * * x #b#"),
		rview_same_item("N\tsshd_port\t22", 'N', "sshd_port"),
		rview_same_item("S\t/jffs/scripts/xy\tm", 'S', "/jffs/scripts/x"));
	show_fold("replace", "A\t/a\t1\nS\t/s\tOLD\nN\tk\tv\n", "A\t/a\t1\nE\t/s\t-\nN\tk\tv\n", 'S', "/s");
	show_fold("gone", "A\t/a\t1\nS\t/s\tOLD\nN\tk\tv\n", "A\t/a\t1\nN\tk\tv\n", 'S', "/s");
	show_fold("added", "A\t/a\t1\n", "A\t/a\t1\nC\tnew line\t-\n", 'C', "new line");
	show_fold("none", "A\t/a\t1\n", "A\t/a\t1\n", 'S', "/zz");
	show_fold("nonl", "A\t/a\t1\nS\t/s\tOLD", "S\t/s\tNEW", 'S', "/s");
	printf("rules ok=%d\n", rview_rules_ok("# comment\n\nhash /jffs/scripts/*\nmeta /jffs/addons/x/*\nexist /jffs/a b/c\nignore cron:*#backup#\nignore nvram:sshd_port\r\n"));
	printf("rules quote=%d bslash=%d tick=%d ctrl=%d mode=%d bare=%d rel=%d long=%d\n",
		rview_rules_ok("ignore /jffs/\"x\n"), rview_rules_ok("ignore /jffs/a\\b\n"), rview_rules_ok("ignore /jffs/`id`\n"),
		rview_rules_ok("ignore /jffs/a\tb\n"), rview_rules_ok("drop /jffs/a\n"), rview_rules_ok("ignore\n"),
		rview_rules_ok("ignore jffs/a\n"), rview_rules_ok(longl));
	big[0] = 0;
	for (i = 0; i < 101; i++) strcat(big, "ignore /jffs/x\n");
	printf("rules 100=%d", rview_rules_ok(big + strlen("ignore /jffs/x\n")));
	printf(" 101=%d\n", rview_rules_ok(big));
	{ FILE *f = fopen(RVIEW_DIFF, "w");
	  fputs("baseline\tS\t/jffs/scripts/a\tm\nadded\tS\t/jffs/scripts/new\tm\nchanged\tN\tsshd_port\t22\nremoved\tA\t/jffs/addons/x\t1\nrule\tE\t/jffs/scripts/b\t-\nnew\tC\tx\t-\n", f); fclose(f); }
	rview_fold_summary(sum, sizeof(sum));
	printf("summary [%s]\n", sum);
	for (i = 0; i < 205; i++) { char d[32]; snprintf(d, sizeof(d), "n%d", i); rview_alog("rules", d); }
	rview_alog("accept-one", "S /jffs/scripts/a\tb\nc");
	return 0;
}
'''

with tempfile.TemporaryDirectory() as td:
    c = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    open(c, "w").write(harness)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
    check("the review CGI helpers compile cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n".join(fails)); sys.exit(1)
    p = subprocess.run([exe, td], capture_output=True, text=True)
    out = p.stdout
    alog = open(os.path.join(td, "accept.log")).read().split("\n")
print(out, end="")
def has(s): return s in out
check("same item: a file whatever its mode letter; C/N by type+key; a prefix is not a match",
      has("same S~E=1 A~K=1 S~C=0 C~C=1 N~N=1 prefix=0"))
check("fold: the item's baseline line is replaced by its live line, the rest kept in order, inputs restored",
      has("replace hit=1 [A>/a>1|N>k>v|E>/s>-|] restored=1"))
check("fold: an item gone from the inventory leaves the baseline", has("gone hit=1 [A>/a>1|N>k>v|] restored=1"))
check("fold: an added item joins the baseline", has("added hit=1 [A>/a>1|C>new line>-|] restored=1"))
check("fold: an unknown item is no hit", has("none hit=0 [A>/a>1|] restored=1"))
check("fold: a baseline without a final newline is repaired", has("nonl hit=1 [A>/a>1|S>/s>NEW|] restored=1"))
check("rules: modes, kinds, comments, blanks and CRLF accepted", has("rules ok=0"))
check("rules: quote, backslash, backtick, control byte, unknown/bare mode, relative path, long line refused",
      has("rules quote=-1 bslash=-1 tick=-1 ctrl=-1 mode=-1 bare=-1 rel=-1 long=-1"))
check("rules: 100 accepted, 101 refused", has("rules 100=0 101=-1"))
check("summary: counts by status and the item keys (baseline and new rows not folded)",
      has("summary [1 added, 1 changed, 1 removed, 1 by rule: /jffs/scripts/new, sshd_port, /jffs/addons/x, /jffs/scripts/b]"))
ents = [l for l in alog if l]
last = ents[-1].split("\t") if ents else []
check("accept log keeps the newest 200 entries", len(ents) == 200 and ents[0].split("\t")[3] == "n6", (len(ents), ents[:1]))
check("accept log: time, client, action, detail - a tab or newline in the detail is flattened",
      len(last) == 4 and last[0].isdigit() and last[1] == "192.168.50.20" and last[2] == "accept-one" and last[3] == "S /jffs/scripts/a b c", last)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
