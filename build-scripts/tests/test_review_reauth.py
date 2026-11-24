#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Security Review: httpd's side of the seal, and the exports' re-auth (httpd/web.c reaper_watch.cgi, 2026-11-21).

WHY THIS EXISTS. The Security Review's request path writes the seal (nvram rwatch_review_seal) that rc/rwatch.c checks
at every run: Accept, Accept one / selected, a rules save and Reset each rewrite it, and a write the seal refuses must
leave nothing behind. web.c cannot be compiled whole on a host, so the REAL handler is lifted out and run.
From 2026-11-21 those actions also asked for the admin password again; the owner removed that on 2026-11-23
(REAPER-REVIEW-NOPW) - this test now also holds that no review action asks for one, while the backup exports keep
their own re-auth (reaper_reauth / rbk_reauth) exactly as before.

WHAT IT DOES. Lifts do_reaper_watch_cgi(), its helpers, the seal functions and the exports' re-auth
(reaper_priv_secret_ok, reaper_reauth, rbk_reauth) out of web.c, plus httpd's own unescape() from cgi.c, and compiles
them with stub nvram / CGI variables / files in a scratch directory. Checks:
  - no review action asks for a password (handler and page);
  - the seal: Accept stores "<fingerprint> <epoch> <who>" and the fingerprint is byte for byte the reference recipe
    (the one rc/rwatch.c hashes with sha256sum - test_rwatch_review.py holds the shell to the same reference); a
    rules save re-seals only while the seal held; a partial Accept is refused while it does not (RFW_430); reset
    clears it, also when only the seal is left; the no-report status answer names the state; a rules file that is a
    link cannot be sealed;
  - [unchanged] the exports' own behaviour: same answers, same log lines, the lock, the 16-character rule of an
    unconfigured box;
  - reaperConfirm's password box (kept in the kit for other callers), run under node.

Exit 0 pass, 1 fail, 77 skipped (no router source tree, no host compiler, or no OpenSSL headers).
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, urllib.parse

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")
if subprocess.run([CC, "-x", "c", "-", "-fsyntax-only"], input="#include <openssl/evp.h>\nint main(void){return 0;}\n",
                  capture_output=True, text=True).returncode != 0:
    skip("no OpenSSL headers on this host")

def rd(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape") as f:
        return f.read()

web, cgic = rd("httpd/web.c"), rd("httpd/cgi.c")
fw, util, dash = rd("www/Reaper_Firewall.asp"), rd("www/reaper_util.js"), rd("www/Main_ReaperDash.asp")
fails, passed = [], 0
def check(name, cond, detail=""):
    global passed
    if cond:
        passed += 1; print("ok   " + name)
    else:
        print("FAIL " + name + ((" - " + str(detail)[:700]) if detail else "")); fails.append(name)

def done():
    if fails:
        print("\n%d FAILED, %d passed:" % (len(fails), passed))
        for f in fails: print("  - " + f)
        sys.exit(1)
    print("\nPASS: %d checks" % passed); sys.exit(0)

def cfun(text, name):
    """one function definition, storage class to closing brace ('' when it is not there)"""
    m = re.search(r"\n((?:static )?[A-Za-z_][A-Za-z_ \*]*?\n?\*?%s\([^;{}]*?\)\n\{.*?\n\}\n" % re.escape(name) + ")", text, re.S)
    return m.group(1) if m else ""

def fingerprint(base_bytes, rules_bytes):
    # the reference recipe (rc/rwatch.c _rv_fp, httpd rview_seal_hash)
    return hashlib.sha256(b"reaper-review-seal-1\nbaseline %d\n" % len(base_bytes) + base_bytes
                          + b"\nrules %d\n" % len(rules_bytes) + rules_bytes + b"\n").hexdigest()

# ------------------------------------------------------------------ 1. lift
OLD = ["rview_slurp", "rview_alog", "rview_fold_summary", "rview_same_item", "rview_fold_one", "rview_rules_ok"]
SEAL = ["rview_seal_hash", "rview_seal_rules", "rview_seal_calc", "rview_seal_holds", "rview_seal_state",
        "rview_seal_store", "rview_seal_clear"]
AUTH = ["reaper_priv_secret_ok", "reaper_reauth"]
NAMES = OLD + SEAL + ["do_reaper_watch_cgi"] + AUTH + ["rbk_reauth"]
FN = {n: cfun(web, n) for n in NAMES}
missing = [n for n in NAMES if not FN[n]]
unesc = cfun(cgic, "unescape")
m_def = re.search(r"#define RVIEW_SEAL_NV\b.*?static const char \*const rview_seal_word\[\][^\n]*\n", web, re.S)
m_lock = re.search(r"#define RBK_PW_LOCK_AFTER\t\d+\n#define RBK_PW_LOCK_SECS\t\d+\n", web)
m_cnt = re.search(r"static int rbk_pwfail = 0;\nstatic time_t rbk_pwlock = 0;\n", web)
HAVE = not missing and bool(m_def)
check("web.c: the handler, the seal functions, the seal's defines and the shared re-auth are all there", HAVE, missing)
if not (unesc and m_lock and m_cnt and FN["do_reaper_watch_cgi"] and FN["rbk_reauth"] and all(FN[n] for n in OLD)):
    check("the review handler and the export re-auth lift at all", False, [n for n in OLD + ["do_reaper_watch_cgi", "rbk_reauth"] if not FN[n]])
    done()

cgi = FN["do_reaper_watch_cgi"]
def act(a):
    i = cgi.find('\tif (!strcmp(action, "%s")) {' % a)
    j = cgi.find("\n\t}\n", i)
    return cgi[i:j] if i >= 0 and j > i else ""

# ------------------------------------------------------------------ 2. static wiring
# REAPER-REVIEW-NOPW (2026-11-23, owner): no review action asks for a password any more
check("no review action asks for a password: no rview_reauth / rview_body_pw, no admpw in the handler",
      "rview_reauth" not in web and "rview_body_pw" not in web and "admpw" not in cgi, [a for a in ("rview_reauth", "rview_body_pw") if a in web])
check("WHICH secret is checked is decided in one function: reaper_priv_secret_ok() is the only caller of the password compare outside the login code",
      FN["reaper_priv_secret_ok"].count("compare_passwd_in_shadow(") == 2 and "compare_passwd_in_shadow(" not in FN["reaper_reauth"]
      and FN["reaper_reauth"].count("reaper_priv_secret_ok(pw)") == 1
      and web.count("compare_passwd_in_shadow(") == 4, web.count("compare_passwd_in_shadow("))
check("the exports call the same check through rbk_reauth() with their own tag and wording - three callers, their lines untouched",
      FN["rbk_reauth"].strip().endswith('{\n\treturn reaper_reauth(pw, what, "reaper_cfg", "exports");\n}')
      and 'int r = rbk_reauth(get_cgi("admpw"), "export pre-check");' in web and 'int r = rbk_reauth(get_cgi("admpw"), "settings export");' in web
      and '(r = rbk_reauth(get_cgi("admpw"), "full backup download")) != 0' in web and web.count("rbk_reauth(get_cgi(") == 3)
logcalls = re.findall(r"logmessage\(([^;]*)\);", FN["reaper_reauth"])
check("no log line of the re-auth is handed the password", len(logcalls) == 2 and not any(re.search(r"[,(]\s*pw\s*[,)]", a + ")") for a in logcalls), logcalls)

# ------------------------------------------------------------------ 3. the harness
PW = "S3cret&;+ %pw=x"          # every character the form encoding has to carry
HEAD = r'''#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>
#include <errno.h>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <openssl/evp.h>
static size_t fx_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
#define strlcpy fx_strlcpy
static time_t NOW = 1800000000;
static time_t fx_time(time_t *t) { if (t) *t = NOW; return NOW; }
#define time fx_time
/* the router's / is the working directory */
#define RVIEW_SH      "./tmp/reaper/rwatch.sh"
#define RVIEW_JSON    "./tmp/reaper/review.json"
#define RVIEW_INV     "./tmp/reaper/review.inv"
#define RVIEW_LAST    "./tmp/reaper/review.last"
#define RVIEW_AUTH    "./tmp/reaper/review.auth"
#define RVIEW_DIFF    "./tmp/reaper/review.diff"
#define RVIEW_BASE    "./jffs/reaper/review/baseline"
#define RVIEW_RULES   "./jffs/reaper/review/rules"
#define RVIEW_ALOG    "./jffs/reaper/review/accept.log"
#define RVIEW_INV_MAX (200 * 1024)
#define RVIEW_RULES_MAX   100
#define RVIEW_RULES_BYTES 8192
#define RVIEW_ALOG_LINES  200
#define RVIEW_MANY_MAX    100
#define RVIEW_MANY_BYTES  16384
#define RGATE_OK 0
static char reaper_client_ip[128] = "192.168.50.20";
static char post_json_buf[65535];
static char FIXPW[200] = "";
/* nvram */
static char NK[64][64], NV[64][600]; static int nn;
static char *nvram_safe_get(const char *k) { int i; for (i = 0; i < nn; i++) if (!strcmp(NK[i], k)) return NV[i]; return ""; }
static int nvram_set(const char *k, const char *v) { int i; for (i = 0; i < nn; i++) if (!strcmp(NK[i], k)) break;
  if (i == nn) { if (nn == 64) return -1; snprintf(NK[nn++], 64, "%s", k); } snprintf(NV[i], 600, "%s", v); return 0; }
static int nvram_unset(const char *k) { int i; for (i = 0; i < nn; i++) if (!strcmp(NK[i], k)) { NV[i][0] = 0; } return 0; }
static int nvram_match(const char *k, const char *v) { return !strcmp(nvram_safe_get(k), v); }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int nvram_commit(void) { printf("COMMIT\n"); return 0; }
/* CGI variables: the first assignment of a name wins, as hsearch ENTER keeps it */
static char *CK[64], *CV[64]; static int cn;
static char *get_cgi(char *n) { int i; for (i = 0; i < cn; i++) if (!strcmp(CK[i], n)) return CV[i]; return NULL; }
static int reaper_gate(void) { return RGATE_OK; }
static void reaper_gate_deny(FILE *s, int why, const char *ns) { fprintf(s, "{\"ok\":0,\"gate\":%d,\"ns\":\"%s\"}", why, ns); }
/* logmessage as httpd.h declares it (char *, char *): a const tag handed to it must be cast, or the real build warns */
static int websWrite(FILE *s, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
static int websWrite(FILE *s, const char *fmt, ...) { va_list ap; int r; va_start(ap, fmt); r = vfprintf(s, fmt, ap); va_end(ap); return r; }
static void logmessage(char *tag, char *fmt, ...) __attribute__((format(printf, 2, 3)));
static void logmessage(char *tag, char *fmt, ...) { va_list ap; printf("LOG %s: ", tag); va_start(ap, fmt); vprintf(fmt, ap); va_end(ap); printf("\n"); }
static void reaper_audit(const char *f, const char *a, const char *d) { printf("LOG reaper-audit: %s %s%s%s\n", f, a, (d && *d) ? " " : "", d ? d : ""); }
static int rjf_set(const char *path, const char *v, const char *tag)
{ FILE *f = fopen(path, "w"); (void)tag; if (!f) return -1; fputs(v, f); fclose(f); return 0; }
static int reaper_script_ok(const char *p) { (void)p; return 1; }
static void rview_kick(void) { printf("KICK\n"); }
static void gk_json_esc(FILE *s, const char *t) { fputc('"', s); for (; *t; t++) { if (*t == '"' || *t == '\\') fputc('\\', s); if (*t == '\n') fputs("\\n", s); else fputc(*t, s); } fputc('"', s); }
static int compare_passwd_in_shadow(const char *user, const char *pw) { return !strcmp(user, "admin") && FIXPW[0] && !strcmp(pw, FIXPW); }
static const char *rbk_peer(void) { return reaper_client_ip; }
'''
FWD = "static int reaper_reauth(const char *pw, const char *what, const char *tag, const char *scope);\n#define HAVE_SEAL 1\n"
MAIN = r'''
static char *unhex(const char *h) { size_t n = strlen(h) / 2, i; char *o = malloc(n + 1); for (i = 0; i < n; i++) { unsigned v = 0; sscanf(h + 2 * i, "%2x", &v); o[i] = (char)v; } o[n] = 0; return o; }
static void request(const char *body, const char *query)
{
	size_t bl = strlen(body), ql = strlen(query), len;
	char *merged = malloc(bl + ql + 2), *q, *out = NULL, url[] = "reaper_watch.cgi";
	size_t ol = 0; FILE *o; int i;

	snprintf(post_json_buf, sizeof(post_json_buf), "%s", body);
	sprintf(merged, "%s%s%s", body, (bl && ql) ? "&" : "", query);	/* do_html_post_and_get: body first, then the query */
	for (i = 0; i < cn; i++) { free(CK[i]); free(CV[i]); }
	cn = 0;
	len = strlen(merged);
	for (q = merged; *q; q++) if (*q == '&' || *q == ';') *q = 0;	/* init_cgi: assignments end at & and ; */
	for (q = merged; q < merged + len; ) {
		char *value, *name; size_t l = strlen(q);
		unescape(q, l + 1);
		value = q; name = strsep(&value, "=");
		if (value && cn < 64 && !get_cgi(name)) { CK[cn] = strdup(name); CV[cn] = strdup(value); cn++; }
		q += l; while (q < merged + len && !*q) q++;
	}
	free(merged);
	o = open_memstream(&out, &ol);
	do_reaper_watch_cgi(url, o);
	fclose(o);
	printf("OUT %s\n", out ? out : "");
	free(out);
}
int main(void)
{
	char *line = NULL; size_t cap = 0; ssize_t n;

	setvbuf(stdout, NULL, _IOLBF, 0);
	while ((n = getline(&line, &cap, stdin)) > 0) {
		char *f[4] = { line, "", "", "" }; int i;
		if (line[n - 1] == '\n') line[n - 1] = 0;
		for (i = 1; i < 4; i++) { char *t = strchr(f[i - 1], '\t'); if (!t) break; *t = 0; f[i] = t + 1; }
		if (!strcmp(f[0], "mark")) printf("== %s\n", f[1]);
		else if (!strcmp(f[0], "nv")) nvram_set(f[1], f[2]);
		else if (!strcmp(f[0], "unnv")) nvram_unset(f[1]);
		else if (!strcmp(f[0], "get")) printf("NV %s=[%s]\n", f[1], nvram_safe_get(f[1]));
		else if (!strcmp(f[0], "pw")) snprintf(FIXPW, sizeof(FIXPW), "%s", unhex(f[1]));
		else if (!strcmp(f[0], "time")) NOW += atol(f[1]);
		else if (!strcmp(f[0], "put")) { FILE *w = fopen(f[1], "w"); char *b = unhex(f[2]); if (w) { fputs(b, w); fclose(w); } free(b); }
		else if (!strcmp(f[0], "rm")) unlink(f[1]);
		else if (!strcmp(f[0], "ln")) { unlink(f[2]); if (symlink(f[1], f[2]) != 0) printf("ERR symlink\n"); }
		else if (!strcmp(f[0], "show")) { FILE *r = fopen(f[1], "r"); int c; printf("FILE %s ", f[1]); if (!r) printf("-"); else { printf("+"); while ((c = fgetc(r)) != EOF) printf("%02x", c); fclose(r); } printf("\n"); }
		else if (!strcmp(f[0], "req")) request(f[1], f[2]);
		else if (!strcmp(f[0], "export")) { char *b = unhex(f[1]); printf("EXP %d\n", rbk_reauth(b, f[2][0] ? f[2] : "export pre-check")); free(b); }
#ifdef HAVE_SEAL
		else if (!strcmp(f[0], "state")) printf("STATE %s\n", rview_seal_word[rview_seal_state()]);
		else if (!strcmp(f[0], "fp")) { char hex[65] = ""; int r = rview_seal_calc(NULL, NULL, hex); printf("FP %d %s\n", r, hex); }
#else
		else if (!strcmp(f[0], "state") || !strcmp(f[0], "fp")) printf("NOSEAL this tree has no seal\n");
#endif
		else printf("ERR unknown command %s\n", f[0]);
	}
	return 0;
}
'''
if HAVE:
    csrc = (HEAD + FWD + unesc + m_def.group(0) + m_lock.group(0) + "".join(FN[n] for n in OLD + SEAL + ["do_reaper_watch_cgi", "reaper_priv_secret_ok"])
            + m_cnt.group(0) + FN["reaper_reauth"] + FN["rbk_reauth"] + MAIN)
else:   # a tree without the feature: the old handler and the old export re-auth, as they are
    csrc = HEAD + unesc + m_lock.group(0) + "".join(FN[n] for n in OLD + ["do_reaper_watch_cgi"]) + m_cnt.group(0) + FN["rbk_reauth"] + MAIN

work = tempfile.mkdtemp(prefix="rvauth_")
try:
    cpath, exe = os.path.join(work, "t.c"), os.path.join(work, "t")
    open(cpath, "w", encoding="utf-8", errors="surrogateescape").write(csrc)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-Wno-unused-parameter",
                        "-o", exe, cpath, "-lcrypto"], capture_output=True, text=True)
    check("the lifted handler, with the seal and the re-auth, compiles cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0 and HAVE, r.stderr[-1500:])
    if r.returncode != 0:
        done()

    INV0 = "A\t/jffs/addons/x/run.sh\t7 Nov 1 10:00\nC\t0 3 * * * /jffs/scripts/b.sh #b#\t-\nN\tsshd_enable\t0\nN\tsshd_port\t22\nS\t/jffs/scripts/firewall-start\t0123456789abcdef0123456789abcdef -rwxr-xr-x\n"
    INV1 = INV0.replace("N\tsshd_port\t22\n", "N\tsshd_port\t2222\n").replace("N\tsshd_enable\t0\n", "N\tsshd_enable\t1\n")
    RULES = "ignore /jffs/addons/x/logs/*\n# kept\nexist /jffs/scripts/firewall-start"
    hx = lambda s: (s if isinstance(s, bytes) else s.encode()).hex()
    q = lambda s: urllib.parse.quote(s, safe="")
    def body(action, pw=None, **kw):
        b = "action=" + action + "".join("&%s=%s" % (k, q(v)) for k, v in kw.items()) + "&http_id=TOKEN"
        return b + ("&admpw=" + q(pw) if pw is not None else "")
    BASE, RULESF, ALOG = "./jffs/reaper/review/baseline", "./jffs/reaper/review/rules", "./jffs/reaper/review/accept.log"
    INVF = "./tmp/reaper/review.inv"

    def play(cmds):
        """run one harness process over a command script; -> {mark: [lines]} and the whole output"""
        root = tempfile.mkdtemp(prefix="root_", dir=work)
        for d in ("jffs/reaper/review", "tmp/reaper"): os.makedirs(os.path.join(root, d))
        script = "".join("\t".join(c) + "\n" for c in cmds)
        p = subprocess.run([exe], input=script, capture_output=True, text=True, cwd=root, timeout=60)
        if p.returncode != 0:
            check("the harness ran", False, p.stderr[-600:]); done()
        sect, cur = {}, None
        for l in p.stdout.splitlines():
            if l.startswith("== "): cur = l[3:]; sect[cur] = []
            elif cur is not None: sect[cur].append(l)
        return sect, p.stdout
    SETUP = [("pw", hx(PW)), ("nv", "http_username", "admin"), ("nv", "p_Setting", "1"), ("nv", "rwatch_review", "1"),
             ("nv", "rwatch_enable", "1"), ("put", INVF, hx(INV0)), ("put", "./tmp/reaper/review.diff", hx("added\tN\tsshd_port\t22\n"))]
    SNAP = [("show", BASE), ("show", RULESF), ("get", "rwatch_review_seal"), ("get", "rwatch_review")]
    ST = [("state",)]
    STATUS = [("req", "", "action=status&http_id=TOKEN")]
    def step(name, *reqs):                # one marked step: the requests, then the files / nvram / state after them
        return [("mark", name)] + [("req", b, "") for b in reqs] + SNAP + ST
    def look(name):                       # the state as httpd sees it, its fingerprint of the files, and the status answer
        return [("mark", name), ("state",), ("fp",)] + STATUS
    def outs(lines): return [l[4:] for l in lines if l.startswith("OUT ")]
    def logs(lines): return [l[4:] for l in lines if l.startswith("LOG ")]
    def snap(lines): return [l for l in lines if l.startswith(("FILE ", "NV "))]
    def fpl(lines): return [l[3:] for l in lines if l.startswith("FP ")]
    def filehex(lines, path):
        for l in lines:
            if l.startswith("FILE %s " % path): return l.split(" ", 2)[2]
        return None
    def nvv(lines, k):
        for l in lines:
            if l.startswith("NV %s=[" % k): return l[len("NV %s=[" % k):-1]
        return None
    def sealfp(lines): return (nvv(lines, "rwatch_review_seal") or "").split(" ")[0]

    # ---------------------------------------------------------- A. Accept, with no password (owner 2026-11-23)
    cmds = SETUP + [("mark", "first"), ("req", body("ack", None), "")] + SNAP
    cmds += [("mark", "off"), ("req", body("set", None, enable="0"), "")] + SNAP
    cmds += [("mark", "on"), ("req", body("set", None, enable="1"), "")] + SNAP
    S, allout = play(cmds)
    f0 = S.get("first", [])
    seal0 = (nvv(f0, "rwatch_review_seal") or "").split(" ")
    check("Accept with no password: baseline written, audited with what it folded in, re-check started - and sealed: "
          "'<fingerprint> <epoch> <who>' committed, the fingerprint being the reference recipe over the accepted bytes",
          outs(f0) == ['{"ok":1,"running":1}'] and filehex(f0, BASE) == "+" + hx(INV0) and "KICK" in f0
          and any(l.startswith("reaper-audit: review baseline 1 added") for l in logs(f0))
          and len(seal0) == 3 and seal0[0] == fingerprint(INV0.encode(), b"") and seal0[1] == "1800000000" and seal0[2] == "192.168.50.20" and "COMMIT" in f0, f0[:8])
    of, on = S.get("off", []), S.get("on", [])
    check("switching the review OFF and ON on its own page needs no password; both are audited",
          outs(of) == ['{"ok":1,"enabled":0}'] and nvv(of, "rwatch_review") == "0" and any(l == "reaper-audit: review off" for l in logs(of))
          and outs(on) == ['{"ok":1,"enabled":1}'] and nvv(on, "rwatch_review") == "1" and not any("REFUSED" in l for l in allout.splitlines()), (of, on))

    # ---------------------------------------------------------- B. accepted (no password since 2026-11-23); the seal follows
    cmds = SETUP + [("req", body("ack", None), ""), ("put", INVF, hx(INV1))]
    cmds += step("rules", body("rules_set", None, rules=RULES))
    cmds += step("one", body("ack_one", None, t="N", k="sshd_port"))
    cmds += step("many", body("ack_many", None, items="N\tsshd_enable\nS\t/jffs/scripts/firewall-start"))
    cmds += step("rules-clear", body("rules_set", None, rules=""))
    cmds += step("off", body("set", None, enable="0")) + [("mark", "prep"), ("nv", "rwatch_review", "1")]
    cmds += step("reset", body("reset", None)) + [("show", ALOG)]
    cmds += step("reset-none", body("reset", None))
    S, allout = play(cmds)
    r_ = S.get("rules", [])
    check("a rules save: the file is written and, the seal having held, re-sealed over baseline + new rules",
          outs(r_) == ['{"ok":1}'] and filehex(r_, RULESF) == "+" + hx(RULES) and sealfp(r_) == fingerprint(INV0.encode(), RULES.encode())
          and "STATE ok" in r_ and "COMMIT" in r_, r_)
    o_ = S.get("one", [])
    B1 = "A\t/jffs/addons/x/run.sh\t7 Nov 1 10:00\nC\t0 3 * * * /jffs/scripts/b.sh #b#\t-\nN\tsshd_enable\t0\nS\t/jffs/scripts/firewall-start\t0123456789abcdef0123456789abcdef -rwxr-xr-x\nN\tsshd_port\t2222\n"
    check("Accept of one row: folded in, and the seal follows the new baseline",
          outs(o_) == ['{"ok":1,"running":1}'] and filehex(o_, BASE) == "+" + hx(B1) and sealfp(o_) == fingerprint(B1.encode(), RULES.encode()) and "STATE ok" in o_, o_)
    m_ = S.get("many", [])
    B2 = "A\t/jffs/addons/x/run.sh\t7 Nov 1 10:00\nC\t0 3 * * * /jffs/scripts/b.sh #b#\t-\nN\tsshd_port\t2222\nN\tsshd_enable\t1\nS\t/jffs/scripts/firewall-start\t0123456789abcdef0123456789abcdef -rwxr-xr-x\n"
    check("Accept of selected rows: one write, and the seal follows",
          outs(m_) == ['{"ok":1,"running":1,"n":2}'] and filehex(m_, BASE) == "+" + hx(B2) and sealfp(m_) == fingerprint(B2.encode(), RULES.encode()) and "STATE ok" in m_, m_)
    c_ = S.get("rules-clear", [])
    check("saving an empty rules text removes the file and re-seals over 'no rules'",
          outs(c_) == ['{"ok":1}'] and filehex(c_, RULESF) == "-" and sealfp(c_) == fingerprint(B2.encode(), b"") and "STATE ok" in c_, c_)
    f_ = S.get("off", [])
    check("switching the review OFF works, is audited, and leaves baseline and seal alone",
          outs(f_) == ['{"ok":1,"enabled":0}'] and nvv(f_, "rwatch_review") == "0" and filehex(f_, BASE) == "+" + hx(B2)
          and sealfp(f_) == fingerprint(B2.encode(), b"") and any(l == "reaper-audit: review off" for l in logs(f_)), f_)
    s_ = S.get("reset", [])
    n_ = S.get("reset-none", [])
    check("Reset: the baseline is removed and the seal cleared with it (committed), state none; with nothing left it answers 'none' as before",
          outs(s_) == ['{"ok":1,"running":1}'] and filehex(s_, BASE) == "-" and nvv(s_, "rwatch_review_seal") == "" and "COMMIT" in s_ and "STATE none" in s_
          and any(l == "reaper-audit: review baseline-reset" for l in logs(s_)) and outs(n_) == ['{"ok":1,"none":1}'] and "COMMIT" not in n_, s_ + n_)
    alog = bytes.fromhex((filehex(s_, ALOG) or "+")[1:]).decode()
    check("the accept log has one line per accepted action, never the password; nor has any reply, log line or audit record of these sealed writes",
          [l.split("\t")[2] for l in alog.splitlines()] == ["accept-all", "rules", "accept-one", "accept-many", "rules", "reset"] and PW not in alog
          and PW not in allout and q(PW) not in allout and allout.count("COMMIT") == 7, (alog, allout.count("COMMIT")))

    # ---------------------------------------------------------- C. the seal's states on the request path
    TAMPER = INV0.replace("N\tsshd_enable\t0\n", "N\tsshd_enable\t1\n")
    cmds = SETUP + look("none")
    cmds += [("mark", "prep"), ("req", body("ack", None), "")] + look("ok")
    cmds += [("mark", "prep"), ("put", RULESF, hx(RULES))] + look("rules-behind") + [("mark", "prep"), ("rm", RULESF)]
    cmds += [("put", BASE, hx(TAMPER)), ("put", INVF, hx(INV1))] + look("changed")
    cmds += step("changed:one", body("ack_one", None, t="N", k="sshd_port"))
    cmds += step("changed:many", body("ack_many", None, items="N\tsshd_port"))
    cmds += step("changed:rules", body("rules_set", None, rules=RULES))
    cmds += step("changed:accept", body("ack", None))
    cmds += [("mark", "prep"), ("unnv", "rwatch_review_seal")] + look("unsealed")
    cmds += step("unsealed:many", body("ack_many", None, items="N\tsshd_port"))
    cmds += step("unsealed:accept", body("ack", None))
    cmds += [("mark", "prep"), ("rm", BASE)] + look("removed")
    cmds += step("removed:reset", body("reset", None))
    cmds += [("mark", "prep"), ("rm", RULESF)] + step("norules:rules", body("rules_set", None, rules=RULES))
    cmds += [("mark", "prep"), ("rm", RULESF), ("put", "./elsewhere", hx("ignore /jffs/scripts/*\n")), ("ln", "../../../elsewhere", RULESF)]
    cmds += step("link:accept", body("ack", None))
    cmds += [("mark", "prep"), ("rm", RULESF), ("req", body("ack", None), ""), ("ln", "../../../elsewhere", RULESF)] + look("link:state")
    cmds += [("mark", "prep"), ("rm", RULESF), ("nv", "rwatch_review", "0")] + look("disabled")
    S, allout = play(cmds)
    check("state none: no baseline, no seal - and the no-report status answer says so",
          "STATE none" in S.get("none", []) and any('"seal":"none","rwatch":1,"armed":0,"error":"no report yet"' in o for o in outs(S.get("none", []))), S.get("none"))
    ok_ = S.get("ok", [])
    check("state ok after an Accept; the C fingerprint of the files on disk is the reference recipe; status says ok and armed",
          "STATE ok" in ok_ and fpl(ok_) == ["0 " + fingerprint(INV0.encode(), b"")] and any('"seal":"ok","rwatch":1,"armed":1' in o for o in outs(ok_)), ok_)
    rb = S.get("rules-behind", [])
    check("a rules file written behind the page: state changed; the C fingerprint with rules is the reference recipe too",
          "STATE changed" in rb and fpl(rb) == ["0 " + fingerprint(INV0.encode(), RULES.encode())], rb)
    ch = S.get("changed", [])
    check("a baseline edited behind the page: state changed, named in the no-report status answer",
          "STATE changed" in ch and any('"seal":"changed"' in o for o in outs(ch)), ch)
    for nm in ("changed:one", "changed:many"):
        x = S.get(nm, [])
        check("%s: a partial Accept is refused while the seal does not hold (RFW_430) - nothing written, the seal untouched" % nm,
              outs(x) == ['{"ok":0,"ek":"RFW_430"}'] and filehex(x, BASE) == "+" + hx(TAMPER) and sealfp(x) == fingerprint(INV0.encode(), b"") and "COMMIT" not in x, x)
    cr = S.get("changed:rules", [])
    check("a rules save while the seal does not hold: the rules are saved, but the edited baseline is NOT re-sealed",
          outs(cr) == ['{"ok":1}'] and filehex(cr, RULESF) == "+" + hx(RULES) and sealfp(cr) == fingerprint(INV0.encode(), b"")
          and "STATE changed" in cr and "COMMIT" not in cr, cr)
    ca = S.get("changed:accept", [])
    check("a full Accept with the password records the current state and seals it: ok again",
          outs(ca) == ['{"ok":1,"running":1}'] and filehex(ca, BASE) == "+" + hx(INV1) and sealfp(ca) == fingerprint(INV1.encode(), RULES.encode()) and "STATE ok" in ca, ca)
    un = S.get("unsealed", [])
    check("a baseline with no seal: state unsealed, named in the no-report status answer (the baseline file still counts as armed there)",
          "STATE unsealed" in un and any('"seal":"unsealed","rwatch":1,"armed":1' in o for o in outs(un)), un)
    um = S.get("unsealed:many", [])
    check("unsealed: a partial Accept is refused too (RFW_430), and no seal is written by it",
          outs(um) == ['{"ok":0,"ek":"RFW_430"}'] and nvv(um, "rwatch_review_seal") == "", um)
    check("unsealed: one full Accept seals it", "STATE ok" in S.get("unsealed:accept", []), S.get("unsealed:accept"))
    rm_ = S.get("removed", [])
    check("the baseline deleted with its seal still set: state removed, named in the status answer",
          "STATE removed" in rm_ and any('"seal":"removed","rwatch":1,"armed":0' in o for o in outs(rm_)), rm_)
    rr = S.get("removed:reset", [])
    check("removed: Reset with the password clears the seal that was left (without the seal it answered 'none' and did nothing)",
          outs(rr) == ['{"ok":1,"running":1}'] and nvv(rr, "rwatch_review_seal") == "" and "STATE none" in rr and "COMMIT" in rr, rr)
    nr = S.get("norules:rules", [])
    check("a rules save with no baseline accepted writes the rules and no seal (there is nothing to seal yet)",
          outs(nr) == ['{"ok":1}'] and filehex(nr, RULESF) == "+" + hx(RULES) and nvv(nr, "rwatch_review_seal") == "" and "STATE none" in nr, nr)
    la = S.get("link:accept", [])
    check("a rules file that is a link cannot be sealed: Accept is refused before anything is written, and the log says why",
          outs(la) == ['{"ok":0,"ek":"RFW_357"}'] and filehex(la, BASE) == "-" and nvv(la, "rwatch_review_seal") == ""
          and any("the watch rules file is not a plain file" in l for l in logs(la)), la)
    check("a link put in place of the rules after an Accept is state changed (httpd never reads the rules through a link)",
          "STATE changed" in S.get("link:state", []), S.get("link:state"))
    check("with the review off the status answer carries no seal state",
          any('"enabled":0' in o and '"seal":"none"' in o for o in outs(S.get("disabled", []))), S.get("disabled"))

    # ---------------------------------------------------------- E. [unchanged] the exports' own behaviour, as it was
    P16 = "ABCDEFGHIJKLMNOP"
    cmds = [("pw", hx(PW)), ("nv", "http_username", "admin"), ("nv", "p_Setting", "1"),
            ("mark", "right"), ("export", hx(PW), ""),
            ("mark", "wrong"), ("export", hx("nope"), ""), ("export", hx(""), "settings export"), ("export", hx("x" * 65), "full backup download"),
            ("mark", "resets"), ("export", hx(PW), ""), ("export", hx("a"), ""), ("export", hx("b"), ""), ("export", hx("c"), ""), ("export", hx("d"), ""), ("export", hx(PW), ""),
            ("mark", "five"), ("export", hx("a"), ""), ("export", hx("b"), ""), ("export", hx("c"), ""), ("export", hx("d"), ""), ("export", hx("e"), ""),
            ("export", hx(PW), ""), ("time", "59"), ("export", hx(PW), ""), ("time", "1"), ("export", hx(PW), ""),
            ("mark", "p16"), ("pw", hx(P16)), ("export", hx(P16 + "QRST"), ""), ("nv", "p_Setting", "0"), ("export", hx(P16 + "QRST"), ""), ("export", hx("ABCDEFGH"), ""),
            ("mark", "user"), ("nv", "http_username", "someoneelse"), ("export", hx(P16), "")]
    S, allout = play(cmds)
    ex = lambda n: [l for l in S.get(n, []) if l.startswith("EXP ")]
    check("[unchanged] export: the right password is accepted (0) and logs nothing", ex("right") == ["EXP 0"] and logs(S.get("right", [])) == [])
    check("[unchanged] export: a wrong, an empty and an over-long password are each refused (1) with the line the exports always logged",
          ex("wrong") == ["EXP 1", "EXP 1", "EXP 1"] and logs(S.get("wrong", [])) == [
              "reaper_cfg: export pre-check REFUSED from 192.168.50.20: wrong admin password",
              "reaper_cfg: settings export REFUSED from 192.168.50.20: wrong admin password",
              "reaper_cfg: full backup download REFUSED from 192.168.50.20: wrong admin password"], S.get("wrong"))
    check("[unchanged] export: a right answer resets the count (four wrong after it do not lock)", ex("resets") == ["EXP 0", "EXP 1", "EXP 1", "EXP 1", "EXP 1", "EXP 0"], ex("resets"))
    check("[unchanged] export: five wrong answers lock for 60 s - the right password answers 2 until then, with the remaining seconds in the log",
          ex("five") == ["EXP 1"] * 5 + ["EXP 2", "EXP 2", "EXP 0"]
          and [l for l in logs(S.get("five", [])) if "locked" in l] == [
              "reaper_cfg: export pre-check REFUSED from 192.168.50.20: exports locked after 5 wrong admin passwords (60 s left)",
              "reaper_cfg: export pre-check REFUSED from 192.168.50.20: exports locked after 5 wrong admin passwords (1 s left)"], S.get("five"))
    check("[unchanged] export: an unconfigured box (p_Setting 0) compares the first 16 characters of a longer answer, a configured one does not",
          ex("p16") == ["EXP 1", "EXP 0", "EXP 1"], ex("p16"))
    check("[unchanged] export: the account checked is http_username", ex("user") == ["EXP 1"], ex("user"))
finally:
    shutil.rmtree(work, ignore_errors=True)

# ------------------------------------------------------------------ 4. the pages: no password anywhere (owner 2026-11-23)
callers = sorted(f for f in os.listdir(os.path.join(SRC, "www")) if f.endswith((".asp", ".js", ".htm"))
                 and "reaper_watch.cgi" in open(os.path.join(SRC, "www", f), encoding="utf-8", errors="replace").read())
posts = re.findall(r"rvpost\(([^\n]*?),function\(j\)", fw)
check("only the Firewall page posts to the review CGI (the dashboard reads the status); none of its requests carries a password",
      callers == ["Main_ReaperDash.asp", "Reaper_Firewall.asp"] and dash.count("reaper_watch.cgi") == 1 and "/reaper_watch.cgi?action=status&http_id=" in dash
      and len(posts) == 5 and not any("admpw" in p_ for p_ in posts) and "admpw" not in fw and "RV_PWL" not in fw and "password:" not in fw
      and "x.open('POST','/reaper_watch.cgi?http_id='+encodeURIComponent(REAPER_HTTPID)+'&_='+Date.now(),true);" in fw and "x.send(q);" in fw, (callers, posts))
en = rd("www/EN.dict")
check("the password texts RFW_426..429 are gone from the page and EN.dict; the seal's texts stay (RFW_422..425, RFW_430); the pages stay plain ASCII",
      not any(("\n%s=" % t) in en or ("<#%s#>" % t) in fw for t in ("RFW_426", "RFW_427", "RFW_428", "RFW_429"))
      and all(("\n%s=" % t) in en for t in ("RFW_422", "RFW_423", "RFW_424", "RFW_425", "RFW_430"))
      and "RFW_430:`<#RFW_430#>`};" in fw
      and all(ord(c) < 128 for c in fw) and all(ord(c) < 128 for c in util) and all(ord(c) < 128 for c in dash))

# ------------------------------------------------------------------ 5. reaperConfirm's password box, run under node
node = shutil.which("node")
m = re.search(r"window\.reaperConfirm = function\(msg, opts, cb\)\{.*?\n\};\n", util, re.S)
check("reaper_util.js: reaperConfirm has the password option", bool(m) and "if(opts.password){" in (m.group(0) if m else ""))
if not node:
    print("skip the node run (no node on this host)")
elif m:
    JS = r'''
var listeners = {};
function El(tag){ this.tag = tag; this.children = []; this.style = {}; this.value = ''; this.disabled = false; this.parentNode = null; }
El.prototype.appendChild = function(c){ c.parentNode = this; this.children.push(c); return c; };
El.prototype.removeChild = function(c){ this.children = this.children.filter(function(x){ return x !== c; }); c.parentNode = null; return c; };
El.prototype.focus = function(){ FOCUS = this; };
var FOCUS = null;
var document = { body: new El('body'),
  createElement: function(t){ return new El(t); },
  getElementById: function(id){ return null; },
  addEventListener: function(t, f){ listeners[t] = f; },
  removeEventListener: function(t, f){ if(listeners[t] === f) delete listeners[t]; } };
var window = {};
''' + m.group(0) + r'''
function find(el, pred){ if(pred(el)) return el; for(var i = 0; i < el.children.length; i++){ var r = find(el.children[i], pred); if(r) return r; } return null; }
function open(opts){ var got = []; window.reaperConfirm('msg', opts, function(a){ got.push(a); });
  var ov = document.body.children[document.body.children.length - 1];
  var btns = []; (function walk(e){ if(e.tag === 'button') btns.push(e); e.children.forEach(walk); })(ov);
  return { got: got, ov: ov, cancel: btns[0], ok: btns[1], pw: find(ov, function(e){ return e.tag === 'input' && e.type === 'password'; }),
           label: find(ov, function(e){ return e.tag === 'label'; }) }; }
function type(d, v){ if(!d.pw) return; d.pw.value = v; if(d.pw.oninput) d.pw.oninput(); }
function key(k){ if(listeners.keydown) listeners.keydown({ key: k, stopPropagation: function(){} }); }
var out = {};
try {
var d = open({ okLabel: 'OK', cancelLabel: 'Cancel', password: 'Admin password' });
out.box = !!d.pw && !!d.label && d.label.textContent === 'Admin password' && d.pw.maxLength === 128 && d.pw.autocomplete === 'current-password' && FOCUS === d.pw;
out.disabledEmpty = d.ok.disabled === true; d.ok.onclick(); key('Enter'); out.noAnswerWhileEmpty = d.got.length === 0;
type(d, 's3 cret&;'); out.enabledTyped = d.ok.disabled === false; d.ok.onclick();
out.answerIsPassword = d.got.length === 1 && d.got[0] === 's3 cret&;'; out.cleared = !!d.pw && d.pw.value === '' && document.body.children.indexOf(d.ov) < 0 && !listeners.keydown;
d = open({ password: 'P' }); type(d, 'x'); d.cancel.onclick(); out.cancelFalse = d.got.length === 1 && d.got[0] === false && !!d.pw && d.pw.value === '';
d = open({ password: 'P' }); type(d, 'x'); key('Escape'); out.escapeFalse = !!d.pw && d.got.length === 1 && d.got[0] === false;
d = open({ password: 'P' }); type(d, 'x'); d.ov.onclick({ target: d.ov }); out.outsideFalse = !!d.pw && d.got.length === 1 && d.got[0] === false;
d = open({ password: 'P' }); type(d, 'pw1'); key('Enter'); out.enterConfirms = d.got.length === 1 && d.got[0] === 'pw1';
d = open({ password: 'P', danger: true }); type(d, 'pw2'); key('Enter'); out.dangerNoEnter = !!d.pw && d.got.length === 0; d.ok.onclick(); out.dangerClick = d.got[0] === 'pw2';
d = open({ password: 'P' }); type(d, 'x'); type(d, ''); out.disabledAgain = d.ok.disabled === true; d.cancel.onclick();
d = open({}); out.plainNoBox = !d.pw; d.ok.onclick(); out.plainTrue = d.got.length === 1 && d.got[0] === true;
d = open({}); d.cancel.onclick(); out.plainFalse = d.got[0] === false;
d = open({ typed: 'DELETE' }); out.typedStillGates = d.ok.disabled === true; var ti = find(d.ov, function(e){ return e.tag === 'input' && e.type === 'text'; });
ti.value = 'DELETE'; ti.oninput(); out.typedOpens = d.ok.disabled === false; d.ok.onclick(); out.typedTrue = d.got[0] === true;
} catch(e) { out.error = String(e); }
console.log(JSON.stringify(out));
'''
    jd = tempfile.mkdtemp(prefix="rvjs_")
    try:
        jf = os.path.join(jd, "t.js"); open(jf, "w").write(JS)
        r = subprocess.run([node, jf], capture_output=True, text=True, timeout=60)
        try: o = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception: o = {}
        check("password box: labelled by the caller's text, takes the focus, the button waits while it is empty",
              r.returncode == 0 and o.get("box") and o.get("disabledEmpty") and o.get("noAnswerWhileEmpty") and o.get("enabledTyped") and o.get("disabledAgain"), (o, r.stderr[-300:]))
        check("password box: confirm answers with the password; Cancel, Escape and a click outside answer false",
              o.get("answerIsPassword") and o.get("cancelFalse") and o.get("escapeFalse") and o.get("outsideFalse"), o)
        check("password box: nothing is kept - the field is emptied and the dialog and its key handler are gone", o.get("cleared"), o)
        check("password box: Enter confirms a normal dialog and never a danger one; dialogs without the box answer true / false as before and the typed-word gate still works",
              o.get("enterConfirms") and o.get("dangerNoEnter") and o.get("dangerClick")
              and o.get("plainNoBox") and o.get("plainTrue") and o.get("plainFalse") and o.get("typedStillGates") and o.get("typedOpens") and o.get("typedTrue"), o)
    finally:
        shutil.rmtree(jd, ignore_errors=True)
done()
