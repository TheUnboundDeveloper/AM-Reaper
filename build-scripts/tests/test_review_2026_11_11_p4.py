#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-11, remediation phase 4: the larger changes.

WHY THIS EXISTS. Wallguard's Advanced rules take regular expressions (AdGuard syntax, /.../). The compiler accepted
anything the C library could compile. One construct, a back-reference (\\1 .. \\9), is matched by back-tracking: on a
long name that does not match it takes seconds, and dnsmasq answers every query from one thread - so a pasted rule
let any device on the network stall DNS for the whole router with one long name.

WHAT IT DOES. Cuts the back-reference test out of the compiler (wallguard/wallguardc.c) and out of the DNS engine
(dnsmasq/src/wallguard_adv.h), compiles both on the host and runs them on a table of patterns - a back-reference is
found, a backslash inside a bracket expression is not mistaken for one. Then builds the real compiler, feeds it a
list with sound and unsound regexes, and checks which were kept, which were left out and why.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import json, os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "wallguard", "wallguardc.c")):
    skip("no router source tree with wallguard/wallguardc.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))

def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

def fn(text, head):
    i = text.find(head)
    if i < 0:
        return ""
    j = text.find("\n}\n", i)
    return text[i:j + 3] if j > 0 else ""

wgc = rd("wallguard", "wallguardc.c"); eng = rd("dnsmasq", "src", "wallguard_adv.h")
TABLE = r'''
static const struct { const char *rx; int want; } T[] = {
	{ "^ads[0-9]+\\.", 0 }, { "(a|b)+c$", 0 }, { "^(.*)(.*)\\2\\1x$", 1 }, { "(a)\\1", 1 }, { "x\\9", 1 },
	{ "a\\\\1", 0 },            /* an escaped backslash, then the digit 1 */
	{ "\\.example\\.com$", 0 }, { "\\0", 0 }, { "[\\1]x", 0 }, { "[^\\1-9]+", 0 }, { "[]\\1]", 0 }, { "[^]\\1]z", 0 },
	{ "[[:alpha:]\\1]", 0 }, { "[[:digit:]]\\3", 1 }, { "[a-z]+\\1", 1 }, { "[ab", 0 }, { "\\", 0 }, { "", 0 },
	{ "((a{1,60}){1,60}){1,30}", 0 },
};
int main(void) {
	unsigned i; int bad = 0;
	for (i = 0; i < sizeof(T) / sizeof(*T); i++)
		if (F(T[i].rx) != T[i].want) { printf("[%s] want %d\n", T[i].rx, T[i].want); bad++; }
	return bad;
}
'''
tmp = tempfile.mkdtemp(prefix="rev1111p4_")
try:
    for label, text, head, name in (("compiler", wgc, "static int adv_rx_backref(const char *s)", "adv_rx_backref"),
                                    ("DNS engine", eng, "static inline int wga_rx_backref(const char *s)", "wga_rx_backref")):
        body = fn(text, head)
        check("D-1: the %s has the back-reference test" % label, bool(body))
        if not body:
            continue
        c = os.path.join(tmp, name + ".c"); x = os.path.join(tmp, name)
        open(c, "w").write("#include <stdio.h>\n" + body + "#define F %s\n" % name + TABLE)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", x, c], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        ok = r.returncode == 0
        out = r.stdout
        if ok:
            r = subprocess.run([x], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=30)
            ok, out = r.returncode == 0, r.stdout
        check("D-1: %s - a back-reference is found; a backslash in a bracket expression, an escaped backslash and \\0 are not one" % label, ok, out)

    check("D-1: the compiler refuses the rule before compiling it, and times every regex on three long names",
          wgc.find("if (adv_rx_backref(rx))") > 0 and wgc.find("if (adv_rx_backref(rx))") < wgc.find('ADV_SKIP("regex does not compile (POSIX extended syntax)");')
          and "CLOCK_PROCESS_CPUTIME_ID" in wgc and "static char probe[3][254];" in wgc and 'ADV_SKIP("regex too slow on a long name' in wgc)
    check("D-1: the engine drops such a rule if a file still holds one (it never reaches regexec)",
          "if (wga_rx_backref(pat) || regcomp(r.re, pat, REG_EXTENDED | REG_ICASE | REG_NOSUB)) {" in eng)

    exe = os.path.join(tmp, "wallguardc")
    r = subprocess.run([CC, "-std=gnu99", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(SRC, "wallguard"), "-o", exe,
                        os.path.join(SRC, "wallguard", "wallguardc.c")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    check("wallguardc builds on the host with -Werror", r.returncode == 0, r.stdout[-500:])
    if r.returncode == 0:
        rules = ["/^ads[0-9]+\\./", "/^(.*)(.*)(.*)(.*)(.*)\\5\\4\\3\\2\\1x$/", "/^track(er)?[0-9]*\\.example\\.net$/",
                 "/(a)\\1b/", "/[\\1]tele/", "||plain.example^"]
        fx, cl, sf, out, st = (os.path.join(tmp, n) for n in ("rules.txt", "clients", "safe", "adv", "adv.json"))
        open(fx, "w").write("\n".join(rules) + "\n"); open(cl, "w").write(""); open(sf, "w").write("")
        r = subprocess.run([exe, "adv", "--in", fx, "--out", out, "--stats", st, "--clients", cl, "--safe", sf],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
        check("wallguardc adv runs on the list", r.returncode == 0, r.stdout[-400:])
        j = json.load(open(st)) if os.path.isfile(st) else {}
        why = {l.get("line"): l.get("why", "") for l in j.get("lines", [])}
        check("D-1: the two rules with a back-reference are left out and the report says why",
              "back-reference" in why.get(2, "") and "back-reference" in why.get(4, ""), why)
        check("D-1: sound regexes are kept - also one with a backslash-digit inside brackets", j.get("regex") == 3 and 1 not in why and 3 not in why and 5 not in why, (j.get("regex"), why))
        kept = open(out, encoding="utf-8", errors="replace").read() if os.path.isfile(out) else ""
        check("D-1: nothing of a refused rule reaches the compiled file", "\\5\\4" not in kept and "(a)\\1b" not in kept and "plain.example" in kept)

    # ------------------------------------------------------------ D-4: rednsd takes a bounded number of connections per pass
    rn = rd("rednsd", "rednsd.c")
    acc = fn(rn, "static void accept_on(struct listener *l)")
    check("D-4: one pass of rednsd's main loop accepts at most 16 connections per listener (the rest wait for the next pass)",
          "#define ACCEPT_PASS\t16" in rn and "for (budget = ACCEPT_PASS; budget > 0; budget--) {" in acc and "for (;;) {" not in acc.split("accept4(")[0])
    check("D-4: the listener is polled level-triggered, so a backlog left behind is picked up at once", "epoll" not in rn and "poll(pfd, np, timeout)" in rn)

    # ------------------------------------------------------------ D-3 / D-4: who gives way when rednsd is full; one lookup per address
    pol = fn(rn, "int policy_allows(const struct cfg *c, const sockaddr_u *a)")
    check("D-4: policy and per-device cap share one neighbour lookup (kept two seconds for the last address)",
          "have_mac = mac_of(a, mac);" in pol and "has_mac = mac_of(&a, mac) == 0;" in acc
          and "now_ms() - kat < 2000" in fn(rn, "static int mac_of(const sockaddr_u *a, unsigned char *mac)"))
    check("D-3: one IPv6 /64 holds at most half of the slots, decided before anything is evicted",
          0 < acc.find("if (n64 >= MAX_CONN / 2) {") < acc.find("if (!c) {") and "!memcmp(b1, nb, 8)" in acc)
    check("D-3: when every slot is busy the device with the most connections gives one up, after the two older rules",
          acc.find("conn_close(h);") < acc.find("struct conn *b = conn_busiest(same);") < acc.find("if (!c || same >= PER_PEER) {"))
    a1 = rn.find("static int conn_same_dev("); b1 = rn.find("/* reaper-rednsd-busiest: end */")
    u1 = rn.find("typedef union {\n\tstruct sockaddr sa;"); sb = fn(rn, "static const unsigned char *sa_bytes(const sockaddr_u *a, int *family)")
    if 0 < a1 < b1 and u1 > 0 and sb:
        c = os.path.join(tmp, "busy.c"); x = os.path.join(tmp, "busy")
        open(c, "w").write(r'''#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#define MAX_CONN 128
enum { C_FREE, C_HANDSHAKE, C_OPEN };
''' + rn[u1:rn.find("} sockaddr_u;", u1) + 13] + r'''
struct conn { int state; sockaddr_u peer; unsigned char mac[6]; int has_mac; long long last; };
static struct conn conns[MAX_CONN];
''' + sb + rn[a1:b1] + r'''
static void put(int i, const char *ip, const char *mac, long long last) {
	memset(&conns[i], 0, sizeof(conns[i])); conns[i].state = C_OPEN; conns[i].last = last;
	if (strchr(ip, ':')) { conns[i].peer.in6.sin6_family = AF_INET6; inet_pton(AF_INET6, ip, &conns[i].peer.in6.sin6_addr); }
	else { conns[i].peer.in.sin_family = AF_INET; inet_pton(AF_INET, ip, &conns[i].peer.in.sin_addr); }
	if (mac) { conns[i].has_mac = 1; memcpy(conns[i].mac, mac, 6); }
}
int main(void) {
	int i, bad = 0; struct conn *b; char ip[40];
	/* everybody holds one connection: nobody is chosen */
	for (i = 0; i < MAX_CONN; i++) { snprintf(ip, sizeof(ip), "10.0.%d.%d", i / 200, i % 200 + 1); put(i, ip, NULL, 1000 + i); }
	if (conn_busiest(0)) { printf("a single-connection device was chosen\n"); bad++; }
	/* one device (by address) holds 8, the rest one each: its longest-quiet connection is chosen */
	for (i = 0; i < 8; i++) put(i, "10.9.9.9", NULL, 500 - i);
	b = conn_busiest(0);
	if (b != &conns[7]) { printf("wrong pick by address: %d\n", b ? (int)(b - conns) : -1); bad++; }
	/* a newcomer that already holds as many gets nothing */
	if (conn_busiest(8)) { printf("a device with 8 took from a device with 8\n"); bad++; }
	if (!conn_busiest(7)) { printf("a device with 7 got nothing from a device with 8\n"); bad++; }
	/* the same MAC behind 6 different IPv6 addresses is ONE device (6 > the others) */
	for (i = 0; i < MAX_CONN; i++) { snprintf(ip, sizeof(ip), "10.0.%d.%d", i / 200, i % 200 + 1); put(i, ip, NULL, 1000 + i); }
	for (i = 20; i < 26; i++) { snprintf(ip, sizeof(ip), "fd00::%x", i); put(i, ip, "\x02\x11\x22\x33\x44\x55", 2000 - i); }
	b = conn_busiest(1);
	if (b != &conns[25]) { printf("wrong pick by MAC: %d\n", b ? (int)(b - conns) : -1); bad++; }
	/* a v4-mapped IPv6 address is the same device as its IPv4 address */
	put(0, "::ffff:10.7.7.7", NULL, 10); put(1, "10.7.7.7", NULL, 20);
	if (!conn_same_dev(&conns[0], &conns[1])) { printf("v4-mapped not matched\n"); bad++; }
	put(2, "10.7.7.8", NULL, 20);
	if (conn_same_dev(&conns[1], &conns[2])) { printf("different addresses matched\n"); bad++; }
	/* free slots are not counted */
	for (i = 0; i < MAX_CONN; i++) conns[i].state = C_FREE;
	if (conn_busiest(0)) { printf("picked from an empty table\n"); bad++; }
	return bad;
}
''')
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", x, c], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        ok, out = r.returncode == 0, r.stdout
        if ok:
            r = subprocess.run([x], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=30)
            ok, out = r.returncode == 0, r.stdout
        check("D-3: the choice - the busiest device's longest-quiet connection; never a single-connection device; a MAC is one device across addresses", ok, out)
    else:
        check("D-3: conn_same_dev / conn_busiest found in rednsd.c", False)

    # ------------------------------------------------------------ B-3 + B-C1: a deadline per web connection
    hc = rd("httpd", "httpd.c")
    a = hc.find("#define REAPER_CONN_PREAUTH\t15"); b = hc.find("/* reaper-conn-deadline: end */")
    check("B-3: the deadline helpers are present", 0 < a < b)
    code = __import__("re").sub(r"/\*.*?\*/", " ", hc, flags=16)
    main_loop = hc[hc.find("/* Process request if any */"):]
    main_loop = main_loop[:main_loop.find("free(item);")]
    check("B-3: the timer is started before the TLS handshake and stopped on every way out of the connection",
          0 < main_loop.find("reaper_conn_deadline_on(item->fd, REAPER_CONN_PREAUTH);") < main_loop.find("ssl_server_fopen(item->fd)")
          and main_loop.rfind("reaper_conn_deadline_off();") > main_loop.find("fclose(conn_fp);")
          and main_loop.rfind("reaper_conn_deadline_off();") > main_loop.find("reset:"))
    check("B-3: it is stopped as soon as the login check passes, and on a router that is not set up yet",
          "reaper_req_authed = 1;\n\t\t\t\t\treaper_conn_deadline_off();" in hc
          and "if (!x_Setting)" in hc and hc.find("if (!x_Setting)") < hc.find("reaper_conn_deadline_off();", hc.find("if (!x_Setting)")) < hc.find("if (!x_Setting)") + 250)
    # libshared exports its own timer_create()/timer_settime() (shared/linux_timer_ax.c), which take the place of the C
    # library's in httpd; that timer_create() calls exit(1) for CLOCK_MONOTONIC. Through those names httpd quit on its
    # first connection (test image _r14), so the deadline must reach the kernel by number.
    check("B-3: the timer is the kernel's, called by number - never through the names libshared shadows",
          "syscall(SYS_timer_create, CLOCK_MONOTONIC, &ev, &reaper_conn_timer)" in hc
          and "syscall(SYS_timer_settime, reaper_conn_timer, 0, &its, NULL);" in hc
          and not __import__("re").search(r"(?<!SYS_)\btimer_(create|settime|delete|gettime)\s*\(", code)
          and "-lrt" not in rd("httpd", "Makefile"))
    check("B-C1: the vendor's slow-request ban list is no longer called (four calls gone)",
          all(n + "(" not in code for n in ("filter_ban_ip", "slowloris_check", "slow_post_read_check", "clean_ban_ip_timeout")))
    if 0 < a < b:
        c = os.path.join(tmp, "dl.c"); x = os.path.join(tmp, "dl")
        open(c, "w").write(r'''#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
#include <sys/socket.h>
/* What libshared puts in place of the C library's timers on the router (shared/linux_timer_ax.c exits on any clock
   but CLOCK_REALTIME). A deadline that goes through these names fails here as it did on the router. */
int timer_create(clockid_t c, struct sigevent *e, timer_t *t) { (void)c; (void)e; (void)t; printf("timer_create() by name\n"); _exit(41); }
int timer_settime(timer_t t, int f, const struct itimerspec *n, struct itimerspec *o) { (void)t; (void)f; (void)n; (void)o; printf("timer_settime() by name\n"); _exit(42); }
''' + hc[a:b] + r'''
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec / 1e9; }
int main(void) {
	int sv[2], bad = 0; char ch; double t0; ssize_t n;
	/* 1: a peer that sends one byte and then nothing - the blocked read must end when the time is up */
	socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
	if (write(sv[1], "G", 1) != 1) return 9;
	reaper_conn_deadline_on(sv[0], 1);
	t0 = now(); n = read(sv[0], &ch, 1); n = read(sv[0], &ch, 1);
	if (n != 0 || now() - t0 < 0.8 || now() - t0 > 3) { printf("stalled read: n=%d after %.2f s\n", (int)n, now() - t0); bad++; }
	reaper_conn_deadline_off(); close(sv[0]); close(sv[1]);
	/* 2: logged in before the time is up - nothing is shut afterwards */
	socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
	reaper_conn_deadline_on(sv[0], 1);
	reaper_conn_deadline_off();
	sleep(2);
	if (write(sv[1], "x", 1) != 1 || read(sv[0], &ch, 1) != 1) { printf("an authenticated connection was shut\n"); bad++; }
	/* 3: the next connection gets its own full time (the timer is re-armed, not left from the last one) */
	reaper_conn_deadline_on(sv[0], 2);
	sleep(1);
	if (write(sv[1], "y", 1) != 1 || read(sv[0], &ch, 1) != 1) { printf("cut early\n"); bad++; }
	t0 = now(); n = read(sv[0], &ch, 1);
	if (n != 0 || now() - t0 > 2.5) { printf("second deadline: n=%d after %.2f s\n", (int)n, now() - t0); bad++; }
	reaper_conn_deadline_off();
	/* 4: a late timer signal after the connection is over touches nothing */
	raise(SIGRTMIN + 3);
	return bad;
}
''')
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", x, c], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        ok, out = r.returncode == 0, r.stdout
        if ok:
            r = subprocess.run([x], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
            ok, out = r.returncode == 0, r.stdout
        check("B-3: a stalled connection is shut when its time is up; one that logged in is never cut; each connection gets its own time", ok, out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed: a regex that can stall DNS is refused by the compiler and ignored by the engine")
