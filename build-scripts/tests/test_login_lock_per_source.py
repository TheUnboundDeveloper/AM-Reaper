#!/usr/bin/env python3
"""Web login lock per source, not per side (review 2026-11-03 A-8; owner go-ahead 2026-11-08), and the backstop held
in open code (review 2026-11-11 B-1; owner go-ahead 2026-11-24).

WHY. login_cgi() counted failed logins per LAN/WAN side (nvram HTTPD_LOGIN_FAIL_LAN/_WAN), and at
DEFAULT_LOGIN_MAX_NUM the whole side was locked out for MAX_LOGIN_BLOCK_TIME. So one host's five wrong passwords
locked every admin on that side out, including admins already logged in, and could repeat that for ever. And
check_current_ip_is_lan_or_wan() called every IPv6 client LAN, so with remote access on, internet clients reaching the
IPv6 remote-access listener counted against the LAN side.
B-1: the per-source key of an IPv6 address was its /64, so every IPv6 device on the LAN shared one lock; and the
backstop against a guesser who rotates addresses set the STOCK side counter, whose closed check turns away every
request from that side - twenty failed logins from one LAN host still bounced every logged-in admin.

WHAT IT DOES.
- Compiles httpd.c's per-source block (between the reaper-ll markers) on the build host (-Wall -Werror) and runs it:
  - a source locks at DEFAULT_LOGIN_MAX_NUM failures, for MAX_LOGIN_BLOCK_TIME, alone;
  - refused tries do not extend the lock; failures lapse; a good login clears the count;
  - on the LAN side an IPv6 source is its address, on the WAN side its /64; a v4-mapped address is its IPv4 address;
  - the table survives more sources than slots without dropping a live lock;
  - the side-wide backstop trips at REAPER_LL_SIDE_BAR failures inside the window and not before;
  - B-1: once tripped it refuses a login on that side for MAX_LOGIN_BLOCK_TIME, on that side only, and is not
    extended by anything but a new trip; a source that logged in correctly and has not failed since may still log
    in; one failure ends that; a good login lapses after REAPER_LL_GOOD_TTL; the oldest good login makes room.
- Compiles the listener test and the login-page hook the same way.
- Pins the wiring in login_cgi, handle_request and the classifier, and the rc start lines the listener test relies on;
  B-1: login_cgi never writes the stock side counter.
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
def bdef(name):
    mm = re.search(r"#define %s\s+(\d+)" % name, block)
    return int(mm.group(1)) if mm else 0
BAR, SLOTS, GOOD, TTL = bdef("REAPER_LL_SIDE_BAR"), bdef("REAPER_LL_SLOTS"), bdef("REAPER_LL_GOOD"), bdef("REAPER_LL_GOOD_TTL")
check("backstop bar is above the per-source limit (%d > %d), table has slots (%d)" % (BAR, MAXN or 0, SLOTS),
      BAR > (MAXN or 0) and SLOTS >= 16)
check("B-1: good logins are remembered (%d sources, %d s - longer than a lock, at least a day)" % (GOOD, TTL),
      GOOD >= 8 and TTL >= 86400 and TTL > (BLOCK or 0))
check("httpd.h declares the five entry points for web.c",
      all(x in hh for x in ("extern long reaper_login_src_locked(const uaddr *u, int side);", "extern int reaper_login_src_fail(const uaddr *u, int side);",
                            "extern void reaper_login_src_ok(const uaddr *u, int side);", "extern int reaper_login_side_fail(int side);",
                            "extern long reaper_login_side_locked(const uaddr *u, int side);")))
hr = hc[hc.index("\t\tlock_status = check_lock_status(&login_dt);"):]
hr = hr[:hr.index("http_login_timeout(&login_uip_tmp, cookies, fromapp);")]
check("handle_request: the login-page hook runs after the stock lock bounce, before the session checks",
      hr.find("send_login_page(fromapp, lock_status, url, NULL, 0, NOLOGINTRY);") < hr.find("reaper_login_page_status(file, lock_status);") > 0)
check("B-1: handle_request never asks the backstop - only a login is refused, a request with a session is not",
      "reaper_login_side_locked" not in func(hc, "handle_request(void)\n{") if "handle_request(void)\n{" in hc else hc.count("reaper_login_side_locked(") == 2,
      hc.count("reaper_login_side_locked("))
check("B-1: httpd.c never writes the stock side counter for the backstop",
      "nvram_set_int(HTTPD_LOGIN_FAIL_LAN, DEFAULT_LOGIN_MAX_NUM)" not in hc and "nvram_set_int(HTTPD_LOGIN_FAIL_WAN, DEFAULT_LOGIN_MAX_NUM)" not in hc)
cc = func(hc, "int check_current_ip_is_lan_or_wan()\n{")
check("classifier: the remote-access listener is WAN, asked before any address test",
      0 < cc.find("if (reaper_wan_listener())\t") < cc.find("switch (login_uip_tmp.family)") and "\t\treturn 1;\n" in cc)
check("rc starts the LAN listeners with -i lan_ifname", svc.count('_argv[https_index++] = nvram_safe_get("lan_ifname");') >= 1
      and 'httpd_argv[httpd_index++] = nvram_safe_get("lan_ifname");' in svc)
check("rc starts the IPv6 remote-access listener with -i <wan6face>",
      "https_ipv6_argv[https_ipv6_index++] = (char *) get_wan6face();" in svc or "https_ipv6_argv[https_ipv6_index++] = pif;" in svc)

# ---------------------------------------------------------------- wiring: web.c login_cgi
SIDE = "cur_login_ip_type ? 1 : 0"
lc = web[web.index("static int\nlogin_cgi(webs_t wp, char_t *url, int auth_version)\n{"):]
lc = lc[:lc.index("\nFINISH:\n")]
pre = lc.find("else if((reaper_ll_rem = reaper_login_src_locked(&login_uip_tmp, %s)) > 0){" % SIDE)
check("login_cgi: source pre-check after the stock lock replies, before the captcha and password checks",
      0 < lc.find("send_login_page(fromapp_flag, lock_status, NULL, NULL, dt, LOGINTRY);") < pre < lc.find('safe_get_cgi_json("login_captcha", root);'))
pre2 = lc.find("else if((reaper_ll_rem = reaper_login_side_locked(&login_uip_tmp, %s)) > 0){" % SIDE)
check("B-1 login_cgi: the backstop pre-check follows it, still before the captcha and password checks",
      0 < pre < pre2 < lc.find('safe_get_cgi_json("login_captcha", root);'))
check("login_cgi: a locked source and a held backstop both get the stock LOGINLOCK reply, NOLOGINTRY (nothing is counted)",
      # review 2026-11-11: counted from MAX_LOGIN_BLOCK_TIME, the length a lock really has
      lc.count("send_login_page(fromapp_flag, LOGINLOCK, NULL, NULL, MAX_LOGIN_BLOCK_TIME - reaper_ll_rem, NOLOGINTRY);") == 2)
ok_b = lc[lc.index('HTTPD_DBG("authpass!\\n");'):lc.index("\t}else{\n#ifdef RTCONFIG_CAPTCHA\n\t\tif(nvram_get_int(\"captcha_enable\")){")]
check("login_cgi: a good login clears the source (and is remembered)", "reaper_login_src_ok(&login_uip_tmp, %s);" % SIDE in ok_b)
fb = lc[lc.index("\t}else{\n#ifdef RTCONFIG_CAPTCHA\n\t\tif(nvram_get_int(\"captcha_enable\")){"):]
check("login_cgi: a failure counts the source and the backstop",
      "reaper_src_lock = reaper_login_src_fail(&login_uip_tmp, %s);" % SIDE in fb and "reaper_side_lock = reaper_login_side_fail(%s);" % SIDE in fb)
check("B-1 login_cgi: a failure never writes the stock side counter, and never sets the stock lock flag",
      "nvram_set_int(HTTPD_LOGIN_FAIL_LAN" not in fb and "nvram_set_int(HTTPD_LOGIN_FAIL_WAN" not in fb
      and "++httpd_login_fail_lan_t" not in fb and "++httpd_login_fail_wan_t" not in fb and "lock_flag |=" not in fb)
check("login_cgi: the side timestamps still move on every failure (the closed check clears the captcha count by them)",
      "nvram_set_int(HTTPD_LAST_LOGIN_FAIL_TS, login_timestamp_tmp);" in fb and "nvram_set_int(HTTPD_LAST_LOGIN_FAIL_TS_W, login_timestamp_tmp_wan);" in fb)
check("login_cgi: the backstop first, then the source lock, then a plain failure",
      0 < fb.find("\t\tif(reaper_side_lock){\n") < fb.find("}else if(reaper_src_lock){") < fb.find("login_error_status = ACCOUNTFAIL;"))
bs = fb[fb.find("\t\tif(reaper_side_lock){\n"):fb.find("}else if(reaper_src_lock){")]
check("B-1 login_cgi: the backstop logs the side and the newest address, says who is not affected, and replies LOGINLOCK",
      'logmessage("httpd login lock", "Many failed logins on the %s side within %d seconds, the newest from %s: for %d seconds a login is taken only from an address that logged in before. Devices already logged in are not affected.", cur_login_ip_type ? "WAN" : "LAN", MAX_LOGIN_BLOCK_TIME, temp_ip_str, MAX_LOGIN_BLOCK_TIME);' in bs
      and "login_error_status = LOGINLOCK;" in bs)
check("...and the SG_mode rule (a second trip is a forced lock) is still inside that branch",
      'if(nvram_get_int("SG_mode") == 1){' in bs and 'nvram_set_int("httpd_force_lock", 1);' in bs and "max_lock_time = MAX_LOGIN_BLOCK_TIME;" in bs)
sl = fb[fb.find("}else if(reaper_src_lock){"):fb.find("login_error_status = ACCOUNTFAIL;")]
check("login_cgi: the source lock logs the address and replies LOGINLOCK",
      'logmessage("httpd login lock", "%d failed logins from %s: that address is locked out for %d seconds, other addresses can still log in.", DEFAULT_LOGIN_MAX_NUM, temp_ip_str, MAX_LOGIN_BLOCK_TIME);' in sl
      and "login_error_status = LOGINLOCK;" in sl and "lock_flag" not in sl and "max_lock_time =" not in sl)
check("B-1: no open code sets the stock side counter to the lock value any more",
      "nvram_set_int(HTTPD_LOGIN_FAIL_LAN, DEFAULT_LOGIN_MAX_NUM)" not in web and "nvram_set_int(HTTPD_LOGIN_FAIL_WAN, DEFAULT_LOGIN_MAX_NUM)" not in web)

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
int cur_login_ip_type = 0;	/* the side of the request: 0 = LAN, 1 = WAN */
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
		if (!strcmp(op, "sd")) { scanf("%%ld", &n); cur_login_ip_type = (int)n; continue; }	/* the side the next sources are on */
		if (!strcmp(op, "side")) { scanf("%%ld", &n); printf("%%d\n", reaper_login_side_fail((int)n)); continue; }
		if (!strcmp(op, "lan")) { scanf("%%63s", a); LAN = strcmp(a, "-") ? strdup(a) : ""; continue; }
		if (!strcmp(op, "if")) { scanf("%%63s", a); http_ifname = strcmp(a, "-") ? strdup(a) : NULL; printf("%%d\n", reaper_wan_listener()); continue; }
		if (!strcmp(op, "es")) { scanf("%%ld", &n); login_error_status = (int)n; continue; }
		scanf("%%63s", a);
		u = A(a);
		if (!strcmp(op, "f")) printf("%%d\n", reaper_login_src_fail(&u, cur_login_ip_type));
		else if (!strcmp(op, "l")) printf("%%ld\n", reaper_login_src_locked(&u, cur_login_ip_type));
		else if (!strcmp(op, "ok")) reaper_login_src_ok(&u, cur_login_ip_type);
		else if (!strcmp(op, "sl")) printf("%%ld\n", reaper_login_side_locked(&u, cur_login_ip_type));
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
            # B-1: the LAN's devices share one /64 - each is its own source there
            o = run(P, "t 1000\nsd 0\n" + "f 2001:db8:1:2::10\n" * MAXN + "l 2001:db8:1:2::10\nl 2001:db8:1:2:aaaa::1\nl 2001:db8:1:2::11\n")
            check("B-1 LAN side: an IPv6 address is one source; its neighbours in the same /64 are not locked with it",
                  o[MAXN - 1] == "1" and o[MAXN:] == [str(BLOCK), "0", "0"], o)
            o = run(P, "t 1000\nsd 0\n" + "f 2001:db8:1:2::10\n" * (MAXN - 1) + "f 2001:db8:1:2::11\n" * (MAXN - 1) + "l 2001:db8:1:2::10\n")
            check("B-1 LAN side: failures from two addresses in one /64 are not added up", o == ["0"] * (2 * MAXN - 2) + ["0"], o)
            o = run(P, "t 1000\nsd 1\n" + "f 2001:db8:1:2::10\n" * 2 + "f 2001:db8:1:2:aaaa::1\n" * (MAXN - 2) + "l 2001:db8:1:2:ffff::9\nl 2001:db8:1:3::10\n")
            check("WAN side: an IPv6 /64 is one source; the next /64 is not", o[MAXN - 1] == "1" and o[MAXN:] == [str(BLOCK), "0"], o)
            o = run(P, "t 1000\nsd 1\n" + "f 2001:db8:1:2::10\n" * MAXN + "sd 0\nl 2001:db8:1:2::10\nsd 1\nl 2001:db8:1:2::10\n")
            check("a lock belongs to the side it was earned on", o[MAXN:] == ["0", str(BLOCK)], o[MAXN:])
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
            # ---- B-1: the backstop held in open code
            TRIP0 = "".join("side 0\n" for _ in range(BAR))		# all at one instant; the last one trips (prints BAR lines)
            o = run(P, "t 1000\nsd 0\nsl %s\n" % X + TRIP0 + "sl %s\n+ 100\nsl %s\n+ %d\nsl %s\n+ 1\nsl %s\n" % (X, X, BLOCK - 101, X, X))
            check("B-1 backstop: nothing is refused before it trips", o[0] == "0", o[:1])
            check("B-1 backstop: once tripped it refuses a login for MAX_LOGIN_BLOCK_TIME (%d s) and ends on time" % BLOCK,
                  o[BAR] == "1" and o[BAR + 1:] == [str(BLOCK), str(BLOCK - 100), "1", "0"], o[BAR:])
            o = run(P, "t 1000\nsd 0\n" + TRIP0 + "sl %s\nsd 1\nsl 203.0.113.9\n" % X)
            check("B-1 backstop: the other side is not refused", o[BAR:] == [str(BLOCK), "0"], o[BAR:])
            o = run(P, "t 1000\nsd 0\n" + TRIP0 + "+ 50\n" + "".join("side 0\n" for _ in range(BAR - 1)) + "sl %s\n" % X)
            check("B-1 backstop: failures short of a new trip do not extend it", o[-1] == str(BLOCK - 50), o[-1:])
            o = run(P, "t 1000\nsd 0\n" + TRIP0 + "+ 50\n" + TRIP0 + "sl %s\n" % X)
            check("B-1 backstop: a new trip holds it for another MAX_LOGIN_BLOCK_TIME", o[-1] == str(BLOCK), o[-1:])
            o = run(P, "t 1000\nsd 0\nok %s\n+ 10\n" % Y + TRIP0 + "sl %s\nsl %s\n" % (Y, X))
            check("B-1: a source that logged in correctly may still log in while the backstop holds; another may not",
                  o[BAR:] == ["0", str(BLOCK)], o[BAR:])
            o = run(P, "t 1000\nsd 0\nok %s\n+ 10\n" % Y + TRIP0 + "f %s\nsl %s\n" % (Y, Y))
            check("B-1: one failed login ends that - the source is refused like any other", o[BAR:] == ["0", str(BLOCK)], o[BAR:])
            o = run(P, "t 1000\nsd 0\nok %s\nf %s\nok %s\n+ 10\n" % (Y, Y, Y) + TRIP0 + "sl %s\n" % Y)
            check("B-1: a later good login earns it back", o[-1] == "0", o[-3:])
            o = run(P, "t 1000\nsd 1\nok 203.0.113.9\nsd 0\n" + TRIP0 + "sl 203.0.113.9\n")
            check("B-1: a good login counts on the side it was made on only", o[-1] == str(BLOCK), o[-1:])
            o = run(P, "t 1000\nsd 0\nok %s\n+ %d\n" % (Y, TTL + 1) + TRIP0 + "sl %s\n" % Y)
            check("B-1: a good login older than REAPER_LL_GOOD_TTL (%d s) is forgotten" % TTL, o[-1] == str(BLOCK), o[-1:])
            o = run(P, "t 1000\nsd 0\nok %s\n+ %d\n" % (Y, TTL - 10) + TRIP0 + "sl %s\n" % Y)
            check("...and one just inside it still counts", o[-1] == "0", o[-1:])
            goods = "".join("+ 1\nok 10.9.0.%d\n" % i for i in range(GOOD + 1))
            o = run(P, "t 1000\nsd 0\n" + goods + TRIP0 + "sl 10.9.0.0\nsl 10.9.0.1\nsl 10.9.0.%d\n" % GOOD)
            check("B-1: more good logins than the list holds (%d): the oldest makes room, the rest stay" % (GOOD + 1),
                  o[BAR:] == [str(BLOCK), "0", "0"], o[BAR:])
            o = run(P, "t 1000\nsd 0\nok 2001:db8:1:2::10\n" + TRIP0 + "sl 2001:db8:1:2::10\nsl 2001:db8:1:2::11\n")
            check("B-1 LAN side: a good login belongs to that IPv6 address, not to its /64", o[BAR:] == ["0", str(BLOCK)], o[BAR:])
            o = run(P, "t 1000\nsd 0\n" + "f %s\n" % X * MAXN + TRIP0 + "+ %d\nl %s\nsl %s\n" % (BLOCK, X, X))
            check("B-1: a source lock and the backstop each end on their own time", o[-2:] == ["0", "0"], o[-2:])
            o = run(P, "if -\nif br0\nif lo\nif eth0\nif ppp0\nlan -\nif eth0\n")
            check("listener: no -i, the LAN bridge and lo are not WAN; any other interface is; no lan_ifname -> never WAN",
                  o == ["0", "0", "0", "1", "1", "0"], o)
            o = run(P, "t 1000\n" + "f %s\n" % X * MAXN + "+ 10\nes 0\npage %s\nes %d\npage %s\nes 3\npage %s\n" % (X, LOCK_C, Y, Y))
            check("login page: the locked source sees its lock and time left; another source does not inherit it",
                  o[MAXN:] == ["%d %d" % (LOCK_C, 10), "0 10", "3 10"], o[MAXN:])
            o = run(P, "t 1000\nsd 0\nok %s\n" % Y + TRIP0 + "+ 30\nes 0\npage %s\nes 0\npage %s\n" % (X, Y))
            check("B-1 login page: while the backstop holds, a source with no good login sees the lock and its time left; one with a good login sees the plain page",
                  o[BAR:] == ["%d %d" % (LOCK_C, 30), "0 30"], o[BAR:])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
