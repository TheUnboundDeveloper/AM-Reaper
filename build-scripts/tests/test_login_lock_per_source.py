#!/usr/bin/env python3
"""Web login lock per source, not per side (review 2026-11-03 A-8; owner go-ahead 2026-11-08).

WHY. login_cgi() counted failed logins per LAN/WAN side (nvram HTTPD_LOGIN_FAIL_LAN/_WAN), and at
DEFAULT_LOGIN_MAX_NUM the whole side was locked out for MAX_LOGIN_BLOCK_TIME. So one host's five wrong passwords
locked every admin on that side out, including admins already logged in, and could repeat that for ever. And
check_current_ip_is_lan_or_wan() called every IPv6 client LAN, so with remote access on, internet clients reaching the
IPv6 remote-access listener counted against the LAN side.

WHAT IT DOES.
- Compiles httpd.c's per-source block (between the reaper-ll markers) on the build host (-Wall -Werror) and runs it:
  - a source locks at DEFAULT_LOGIN_MAX_NUM failures, for MAX_LOGIN_BLOCK_TIME, alone;
  - refused tries do not extend the lock; failures lapse; a good login clears the count;
  - an IPv6 /64 counts as one source, and a v4-mapped address counts as its IPv4 address;
  - the table survives more sources than slots without dropping a live lock;
  - the side-wide backstop trips at REAPER_LL_SIDE_BAR failures inside the window and not before.
- Compiles the listener test and the login-page hook the same way.
- Pins the wiring in login_cgi, handle_request and the classifier, and the rc start lines the listener test relies on.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "httpd")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def func(src, sig):
    a = src.index(sig); return src[a:src.index("\n}\n", a) + 3]

hc, hh, web, svc = rd("httpd/httpd.c"), rd("httpd/httpd.h"), rd("httpd/web.c"), rd("rc/services.c")
def define(name):
    m = re.search(r"^#define\s+%s\s+(\d+)" % name, hh, re.M)
    return int(m.group(1)) if m else None
MAXN, BLOCK = define("DEFAULT_LOGIN_MAX_NUM"), define("MAX_LOGIN_BLOCK_TIME")
LOCK_C, FORCE_C = define("LOGINLOCK"), define("FORCELOCK")
check("httpd.h: DEFAULT_LOGIN_MAX_NUM / MAX_LOGIN_BLOCK_TIME / LOGINLOCK / FORCELOCK", None not in (MAXN, BLOCK, LOCK_C, FORCE_C),
      (MAXN, BLOCK, LOCK_C, FORCE_C))

# ---------------------------------------------------------------- wiring: httpd.c / httpd.h
m = re.search(r"/\* reaper-ll: begin \*/\n(.*?)/\* reaper-ll: end \*/\n", hc, re.S)
block = m.group(1) if m else ""
check("httpd.c holds the per-source block between the reaper-ll markers", bool(block))
bar = re.search(r"#define REAPER_LL_SIDE_BAR\s+(\d+)", block)
BAR = int(bar.group(1)) if bar else 0
slots = re.search(r"#define REAPER_LL_SLOTS\s+(\d+)", block)
SLOTS = int(slots.group(1)) if slots else 0
check("backstop bar is above the per-source limit (%d > %d), table has slots (%d)" % (BAR, MAXN or 0, SLOTS),
      BAR > (MAXN or 0) and SLOTS >= 16)
check("httpd.h declares the four entry points for web.c",
      all(x in hh for x in ("extern long reaper_login_src_locked(const uaddr *u);", "extern int reaper_login_src_fail(const uaddr *u);",
                            "extern void reaper_login_src_ok(const uaddr *u);", "extern int reaper_login_side_fail(int side);")))
hr = hc[hc.index("\t\tlock_status = check_lock_status(&login_dt);"):]
hr = hr[:hr.index("http_login_timeout(&login_uip_tmp, cookies, fromapp);")]
check("handle_request: the login-page hook runs after the side-lock bounce, before the session checks",
      hr.find("send_login_page(fromapp, lock_status, url, NULL, 0, NOLOGINTRY);") < hr.find("reaper_login_page_status(file, lock_status);") > 0)
cc = func(hc, "int check_current_ip_is_lan_or_wan()\n{")
check("classifier: the remote-access listener is WAN, asked before any address test",
      0 < cc.find("if (reaper_wan_listener())\t") < cc.find("switch (login_uip_tmp.family)") and "\t\treturn 1;\n" in cc)
check("rc starts the LAN listeners with -i lan_ifname", svc.count('_argv[https_index++] = nvram_safe_get("lan_ifname");') >= 1
      and 'httpd_argv[httpd_index++] = nvram_safe_get("lan_ifname");' in svc)
check("rc starts the IPv6 remote-access listener with -i <wan6face>",
      "https_ipv6_argv[https_ipv6_index++] = (char *) get_wan6face();" in svc or "https_ipv6_argv[https_ipv6_index++] = pif;" in svc)

# ---------------------------------------------------------------- wiring: web.c login_cgi
lc = web[web.index("static int\nlogin_cgi(webs_t wp, char_t *url, int auth_version)\n{"):]
lc = lc[:lc.index("\nFINISH:\n")]
pre = lc.find("else if((reaper_ll_rem = reaper_login_src_locked(&login_uip_tmp)) > 0){")
check("login_cgi: source pre-check after the stock side-lock replies, before the captcha and password checks",
      0 < lc.find("send_login_page(fromapp_flag, lock_status, NULL, NULL, dt, LOGINTRY);") < pre < lc.find('safe_get_cgi_json("login_captcha", root);'))
check("login_cgi: a locked source gets the stock LOGINLOCK reply, NOLOGINTRY (it never feeds the side counter)",
      # review 2026-11-11: counted from MAX_LOGIN_BLOCK_TIME, the length a source lock really has
      "send_login_page(fromapp_flag, LOGINLOCK, NULL, NULL, MAX_LOGIN_BLOCK_TIME - reaper_ll_rem, NOLOGINTRY);" in lc)
ok_b = lc[lc.index('HTTPD_DBG("authpass!\\n");'):lc.index("\t}else{\n#ifdef RTCONFIG_CAPTCHA\n\t\tif(nvram_get_int(\"captcha_enable\")){")]
check("login_cgi: a good login clears the source", "reaper_login_src_ok(&login_uip_tmp);" in ok_b)
fb = lc[lc.index("\t}else{\n#ifdef RTCONFIG_CAPTCHA\n\t\tif(nvram_get_int(\"captcha_enable\")){"):]
check("login_cgi: a failure counts the source and the backstop",
      "reaper_src_lock = reaper_login_src_fail(&login_uip_tmp);" in fb and "reaper_side_lock = reaper_login_side_fail(cur_login_ip_type ? 1 : 0);" in fb)
check("login_cgi: the side counter is no longer bumped per failure",
      "++httpd_login_fail_lan_t" not in fb and "++httpd_login_fail_wan_t" not in fb
      and "if(reaper_side_lock && nvram_get_int(HTTPD_LOGIN_FAIL_LAN) < DEFAULT_LOGIN_MAX_NUM)" in fb
      and "if(reaper_side_lock && nvram_get_int(HTTPD_LOGIN_FAIL_WAN) < DEFAULT_LOGIN_MAX_NUM)" in fb)
check("login_cgi: the side timestamps still move on every failure (captcha and stock unlock timing)",
      "nvram_set_int(HTTPD_LAST_LOGIN_FAIL_TS, login_timestamp_tmp);" in fb and "nvram_set_int(HTTPD_LAST_LOGIN_FAIL_TS_W, login_timestamp_tmp_wan);" in fb)
check("login_cgi: side lock first, then the source lock, then a plain failure",
      0 < fb.find(">= DEFAULT_LOGIN_MAX_NUM){\n\t\t\tlock_flag |=") < fb.find("}else if(reaper_src_lock){") < fb.find("login_error_status = ACCOUNTFAIL;"))
sl = fb[fb.find("}else if(reaper_src_lock){"):fb.find("login_error_status = ACCOUNTFAIL;")]
check("login_cgi: the source lock logs the address and replies LOGINLOCK",
      'logmessage("httpd login lock", "%d failed logins from %s: that address is locked out for %d seconds, other addresses can still log in.", DEFAULT_LOGIN_MAX_NUM, temp_ip_str, MAX_LOGIN_BLOCK_TIME);' in sl
      and "login_error_status = LOGINLOCK;" in sl and "lock_flag" not in sl and "max_lock_time =" not in sl)

# ---------------------------------------------------------------- run the block
HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#define RTCONFIG_IPV6
#define DEFAULT_LOGIN_MAX_NUM %(MAXN)d
#define MAX_LOGIN_BLOCK_TIME %(BLOCK)d
#define LOGINLOCK %(LOCK)d
#define FORCELOCK %(FORCE)d
typedef struct uaddr { int family; union { struct in_addr in; struct in6_addr in6; }; } uaddr;
static long NOW = 1000;
long uptime(void) { return NOW; }
char *http_ifname = NULL;
static const char *LAN = "br0";
char *nvram_safe_get(const char *k) { return (char *)(strcmp(k, "lan_ifname") ? "" : LAN); }
uaddr login_uip_tmp;
int login_error_status = 0, max_lock_time = MAX_LOGIN_BLOCK_TIME;
long login_dt = 0;
%(BLOCK_C)s
%(PAGE)s
%(LISTENER)s
static uaddr A(const char *s)
{
	uaddr u;
	memset(&u, 0, sizeof(u));
	if (inet_pton(AF_INET, s, &u.in) == 1) u.family = AF_INET;
	else if (inet_pton(AF_INET6, s, &u.in6) == 1) u.family = AF_INET6;
	return u;
}
int main(void)
{
	char op[16], a[64];
	long n;
	uaddr u;
	while (scanf("%%15s", op) == 1) {
		if (!strcmp(op, "t")) { scanf("%%ld", &n); NOW = n; continue; }
		if (!strcmp(op, "+")) { scanf("%%ld", &n); NOW += n; continue; }
		if (!strcmp(op, "side")) { scanf("%%ld", &n); printf("%%d\n", reaper_login_side_fail((int)n)); continue; }
		if (!strcmp(op, "lan")) { scanf("%%63s", a); LAN = strcmp(a, "-") ? strdup(a) : ""; continue; }
		if (!strcmp(op, "if")) { scanf("%%63s", a); http_ifname = strcmp(a, "-") ? strdup(a) : NULL; printf("%%d\n", reaper_wan_listener()); continue; }
		if (!strcmp(op, "es")) { scanf("%%ld", &n); login_error_status = (int)n; continue; }
		scanf("%%63s", a);
		u = A(a);
		if (!strcmp(op, "f")) printf("%%d\n", reaper_login_src_fail(&u));
		else if (!strcmp(op, "l")) printf("%%ld\n", reaper_login_src_locked(&u));
		else if (!strcmp(op, "ok")) reaper_login_src_ok(&u);
		else if (!strcmp(op, "page")) { login_uip_tmp = u; reaper_login_page_status("Main_Login.asp", 0); printf("%%d %%ld\n", login_error_status, login_dt); }
	}
	return 0;
}
'''

def run(prog, script):
    r = subprocess.run([prog], input=script, capture_output=True, text=True)
    out = r.stdout.split("\n")[:-1]
    if r.returncode:	# the harness died (a memory fault in the block): pad so every check below fails, not the test
        out += ["<harness exit %d>" % r.returncode] * 256
    return out

d = tempfile.mkdtemp(prefix="ll_")
try:
    if not shutil.which("gcc"):
        check("gcc available to compile the per-source block", False)
    elif block:
        c = HARNESS % dict(MAXN=MAXN, BLOCK=BLOCK, LOCK=LOCK_C, FORCE=FORCE_C, BLOCK_C=block,
                           PAGE=func(hc, "static void reaper_login_page_status(const char *file, int lock_status)\n{"),
                           LISTENER=func(hc, "static int reaper_wan_listener(void)\n{"))
        open(d + "/ll.c", "w").write(c)
        r = subprocess.run(["gcc", "-Wall", "-Werror", "-o", d + "/ll", d + "/ll.c"], capture_output=True, text=True)
        check("the per-source block, page hook and listener test compile on the build host (-Wall -Werror)", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            P = d + "/ll"
            X, Y = "192.168.50.66", "192.168.50.10"
            o = run(P, "t 1000\n" + "".join("+ 2\nf %s\n" % X for _ in range(MAXN)) + "l %s\nl %s\n" % (X, Y))
            check("a source locks on failure %d, not before" % MAXN, o[:MAXN] == ["0"] * (MAXN - 1) + ["1"], o)
            check("locked for MAX_LOGIN_BLOCK_TIME (%d s); another source on the same LAN is not" % BLOCK, o[MAXN:] == [str(BLOCK), "0"], o[MAXN:])
            o = run(P, "t 1000\n" + "f %s\n" % X * MAXN + "+ 100\nf %s\nl %s\n+ %d\nl %s\n+ 1\nl %s\n" % (X, X, BLOCK - 101, X, X))
            check("a try while locked is refused uncounted and does not extend the lock; it ends on time",
                  o[MAXN:] == ["0", str(BLOCK - 100), "1", "0"], o[MAXN:])
            o = run(P, "t 1000\n" + "f %s\n" % X * MAXN + "+ %d\n" % BLOCK + "f %s\n" % X * MAXN)
            check("after the lock a source starts again from zero", o[MAXN:] == ["0"] * (MAXN - 1) + ["1"], o[MAXN:])
            o = run(P, "t 1000\n" + "".join("+ %d\nf %s\n" % (BLOCK + 1, X) for _ in range(MAXN * 2)))
            check("failures further apart than the window never lock", o == ["0"] * (MAXN * 2), o)
            o = run(P, "t 1000\n" + "f %s\n" % X * (MAXN - 1) + "ok %s\n" % X + "f %s\n" % X * (MAXN - 1))
            check("a good login clears the count", o == ["0"] * (2 * MAXN - 2), o)
            o = run(P, "t 1000\n" + "f 2001:db8:1:2::10\n" * 2 + "f 2001:db8:1:2:aaaa::1\n" * (MAXN - 2) + "l 2001:db8:1:2:ffff::9\nl 2001:db8:1:3::10\n")
            check("an IPv6 /64 is one source; the next /64 is not", o[MAXN - 1] == "1" and o[MAXN:] == [str(BLOCK), "0"], o)
            o = run(P, "t 1000\n" + "f ::ffff:192.168.50.66\n" * (MAXN - 1) + "f 192.168.50.66\n")
            check("a v4-mapped address is its IPv4 address", o[-1] == "1", o)
            many = "".join("+ 1\nf 10.0.%d.%d\n" % (i // 200, i % 200) for i in range(SLOTS + 20))
            o = run(P, "t 1000\n" + "f %s\n" % X * MAXN + many + "l %s\n" % X)
            check("more sources than slots (%d): a live lock is kept, unlocked entries go first" % (SLOTS + 20), o[-1] not in ("", "0"), o[-1:])
            o = run(P, "t 1000\n" + "".join("+ 1\nside 0\n" for _ in range(BAR - 1)) + "+ 1\nside 0\n" + "".join("+ 1\nside 0\n" for _ in range(BAR - 1)))
            check("backstop: %d failures in the window trip it, %d do not; then it starts over" % (BAR, BAR - 1),
                  o[:BAR] == ["0"] * (BAR - 1) + ["1"] and o[BAR:] == ["0"] * (BAR - 1), o)
            step = BLOCK // (BAR - 1) + 1
            o = run(P, "t 1000\n" + "".join("+ %d\nside 0\n" % step for _ in range(BAR * 3)))
            check("backstop: failures spread wider than the window never trip it", o == ["0"] * (BAR * 3), o[-3:])
            o = run(P, "t 1000\n" + "".join("+ 1\nside 0\n" for _ in range(BAR - 1)) + "".join("+ 1\nside 1\n" for _ in range(BAR - 1)))
            check("backstop: LAN and WAN count apart", o == ["0"] * (2 * BAR - 2), o)
            o = run(P, "if -\nif br0\nif lo\nif eth0\nif ppp0\nlan -\nif eth0\n")
            check("listener: no -i, the LAN bridge and lo are not WAN; any other interface is; no lan_ifname -> never WAN",
                  o == ["0", "0", "0", "1", "1", "0"], o)
            o = run(P, "t 1000\n" + "f %s\n" % X * MAXN + "+ 10\nes 0\npage %s\nes %d\npage %s\nes 3\npage %s\n" % (X, LOCK_C, Y, Y))
            check("login page: the locked source sees its lock and time left; another source does not inherit it",
                  o[MAXN:] == ["%d %d" % (LOCK_C, 10), "0 10", "3 10"], o[MAXN:])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
