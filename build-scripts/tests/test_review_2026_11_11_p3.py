#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-11, remediation phase 3: the medium fixes in open code.

WHY THIS EXISTS. Phase 3 of the 2026-11-11 review fixes the items that needed more than a line:
  - DHCP option 162 (the address of the router's encrypted DNS) could stay published on guest networks after the
    main network withdrew it, and a certificate that ran out was never noticed without a restart;
  - "DNS-over-HTTPS for devices" on port 443 dropped IPv6 web access from WAN when that used 443 as well;
  - the AiMesh channel fit took the mesh controller's file lock with no time limit, inside rc itself;
  - AiMesh sync files written by an older firmware stayed readable by every account, and the node-side sync daemon
    still started without the private file mode.

WHAT IT DOES. Cuts the real functions out of the tree, compiles them on the host with small stand-ins and runs
them: the option-162 watch (asks for one restart when the published state is stale, never more), the bounded lock
(given at once when free, refused after about two seconds when another process holds it), the file-mode sweep
(regular files closed to others, links not followed). Pins the call sites.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "encdns.c")):
    skip("no router source tree with rc/encdns.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))

def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

def fn(text, head):
    """the function whose definition starts with `head`, to the first line that is just '}'"""
    i = text.find(head)
    if i < 0:
        return ""
    j = text.find("\n}\n", i)
    return text[i:j + 3] if j > 0 else ""

def build(tmp, name, code, extra=()):
    src = os.path.join(tmp, name + ".c"); exe = os.path.join(tmp, name)
    open(src, "w", encoding="utf-8", errors="surrogateescape").write(code)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-o", exe, src] + list(extra),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    return (exe if r.returncode == 0 else None), r.stdout

def run(exe, *args, **kw):
    r = subprocess.run([exe] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60, **kw)
    return r.returncode, r.stdout

tmp = tempfile.mkdtemp(prefix="rev1111p3_")
try:
    enc = rd("rc", "encdns.c"); svc = rd("rc", "services.c"); wd = rd("rc", "watchdog.c"); web = rd("httpd", "web.c")
    mc = rd("rc", "reaper_meshchan.c")

    # ------------------------------------------------------------ C-6: port 443 and IPv6 web access from WAN
    six = 'if (nvram_get_int("misc_http_x") != 0 && nvram_get_int("misc_httpsport_x") == 443 && ipv6_enabled())\n\t\treturn "https";'
    check("C-6: rc and the web server both count IPv6 web access from WAN on 443 as 'port in use'",
          six in fn(enc, "static const char *red_doh_busy(void)") and six in fn(web, "static const char *renc_doh_busy(void)"))

    # ------------------------------------------------------------ C-4: DHCP option 162
    check("C-4: only a dnsmasq start that wrote every network's config records what is published",
          "#ifdef RTCONFIG_MULTILAN_CFG\n\tif (sdn_idx == ALL_SDN)" in svc
          and re.search(r"if \(sdn_idx == ALL_SDN\)[^\n]*\n#endif\n\trednsd_dnr_mark\(\);", svc) is not None
          and svc.count("rednsd_dnr_mark();") == 1)
    check("C-4: the watchdog calls the option-162 watch; it is declared in rc.h",
          "\trednsd_dnr_watch();" in wd and "extern void rednsd_dnr_watch(void);" in rd("rc", "rc.h"))
    w = fn(enc, "void rednsd_dnr_watch(void)")
    check("C-4: the watch asks rc for the restart (it runs in the watchdog process) and never restarts by itself",
          'if (getpid() != 1)\n\t\tnotify_rc("restart_dnsmasq");' in w and "start_dnsmasq(" not in w and "++tick % 300" in w)
    if CC and w:
        exe, out = build(tmp, "dnr", r'''#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
static const char *WANT = "", *MARK;
static int DNSMASQ = 1, ASKED;
#define RED_DNR MARK
static void red_dnr_state(char *b, size_t n) { snprintf(b, n, "%s", WANT); }
static int f_exists(const char *p) { struct stat sb; return stat(p, &sb) == 0; }
static int f_read_string(const char *p, char *b, int max) { FILE *f = fopen(p, "r"); size_t n; if (!f) return -1; n = fread(b, 1, max - 1, f); b[n] = 0; fclose(f); return (int)n; }
static int pids(const char *n) { (void)n; return DNSMASQ; }
static int notify_rc(const char *s) { if (!strcmp(s, "restart_dnsmasq")) ASKED++; return 0; }
#define logmessage(tag, ...) ((void)0)
''' + w + r'''
static void mark(const char *s) { FILE *f = fopen(MARK, "w"); fputs(s, f); fclose(f); }
int main(int argc, char **argv) {
	int i, bad = 0;
	(void)argc; MARK = argv[1];
	/* nothing was ever published: the file is absent, nothing happens */
	WANT = "router.example 1 1"; for (i = 0; i < 900; i++) rednsd_dnr_watch(); if (ASKED) { printf("asked with no mark\n"); bad++; }
	/* published and still right: quiet */
	mark("router.example 1 1\n"); for (i = 0; i < 900; i++) rednsd_dnr_watch(); if (ASKED) { printf("asked while in step\n"); bad++; }
	/* the certificate ran out: the wanted state is empty now. One request per five minutes, none in between */
	WANT = ""; ASKED = 0; for (i = 0; i < 299; i++) rednsd_dnr_watch(); if (ASKED > 1) { printf("asked %d times in 299 s\n", ASKED); bad++; }
	ASKED = 0; for (i = 0; i < 300; i++) rednsd_dnr_watch(); if (ASKED != 1) { printf("asked %d times in 300 s\n", ASKED); bad++; }
	/* the restart wrote the mark: quiet again */
	mark(""); ASKED = 0; for (i = 0; i < 900; i++) rednsd_dnr_watch(); if (ASKED) { printf("asked after the mark was rewritten\n"); bad++; }
	/* dnsmasq not running: nothing to restart */
	mark("old 1 0\n"); DNSMASQ = 0; ASKED = 0; for (i = 0; i < 900; i++) rednsd_dnr_watch(); if (ASKED) { printf("asked with no dnsmasq\n"); bad++; }
	return bad;
}
''')
        rc_, o = run(exe, os.path.join(tmp, "dnr.mark")) if exe else (1, out)
        check("C-4: the watch - quiet when nothing is published or all is in step, one restart request when stale", rc_ == 0, o)

    # ------------------------------------------------------------ C-7: the controller's lock, bounded
    ml = fn(mc, "static int mc_lock_try(void)")
    load = mc[mc.find("lock = mc_lock_try();"):][:600]
    check("C-7: the plan loader no longer waits on file_lock(); without the lock it reads nothing and uses the kept plan",
          'file_lock("chanspec")' not in re.sub(r"/\*.*?\*/", "", mc, flags=re.S) and "F_SETLK, &fl" in ml and "F_SETLKW" not in ml
          and "if (lock >= 0) {" in load and "close(lock);" in load and "n = 0;" in load and "file_unlock(lock)" not in load)
    if CC and ml:
        lockf = os.path.join(tmp, "chanspec.lock")
        exe, out = build(tmp, "lk", r'''#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
''' + ml.replace('"/var/lock/chanspec.lock"', '"%s"' % lockf.replace("\\", "/")) + r'''
int main(void) {
	struct timespec a, b; int fd; long ms;
	clock_gettime(CLOCK_MONOTONIC, &a); fd = mc_lock_try(); clock_gettime(CLOCK_MONOTONIC, &b);
	ms = (b.tv_sec - a.tv_sec) * 1000 + (b.tv_nsec - a.tv_nsec) / 1000000;
	printf("%s %ld\n", fd >= 0 ? "got" : "refused", ms);
	return 0;
}
''')
        if exe:
            _, o1 = run(exe)
            import fcntl
            hold = open(lockf, "r+"); fcntl.lockf(hold, fcntl.LOCK_EX)   # this process plays the stuck controller
            t0 = time.time(); _, o2 = run(exe); dt = time.time() - t0
            fcntl.lockf(hold, fcntl.LOCK_UN); hold.close()
            _, o3 = run(exe)
            check("C-7: a free lock is given at once", o1.startswith("got ") and int(o1.split()[1]) < 500, o1)
            check("C-7: a lock another process holds is refused after about two seconds, not waited on for ever",
                  o2.startswith("refused ") and 1500 <= int(o2.split()[1]) <= 4000 and dt < 6, o2)
            check("C-7: once released it is given again", o3.startswith("got "), o3)
        else:
            check("C-7: mc_lock_try compiles on the host", False, out)

    # ------------------------------------------------------------ D-9: AiMesh sync files
    sweep = fn(svc, "static void reaper_cfgmnt_private(void)")
    sync = svc[svc.find("int start_cfgsync(void)"):]
    sync = sync[:sync.find("\n}\n")]
    check("D-9: the sweep runs when the sync daemons start, and the node-side daemon starts under umask 077",
          "\treaper_cfgmnt_private();" in sync
          and re.search(r"mode_t um = umask\(077\);\s+ret = _eval\(cfg_client_argv, NULL, 0, &pid\);\s+umask\(um\);", sync) is not None)
    if CC and sweep:
        d = os.path.join(tmp, "cfg_mnt"); os.makedirs(d)
        exe, out = build(tmp, "sw", r'''#include <stdio.h>
#include <string.h>
#include <dirent.h>
#include <unistd.h>
#include <sys/stat.h>
''' + sweep.replace('"/jffs/.sys/cfg_mnt"', '"%s"' % d.replace("\\", "/")) + "\nint main(void) { reaper_cfgmnt_private(); return 0; }\n")
        if exe:
            def mk(name, mode):
                p = os.path.join(d, name); open(p, "w").write("{}"); os.chmod(p, mode); return p
            a = mk("a.json", 0o644); b = mk("b.json", 0o600); c = mk("c.json", 0o666); x = mk("run.sh", 0o755)
            outside = os.path.join(tmp, "outside"); open(outside, "w").write("x"); os.chmod(outside, 0o644)
            os.symlink(outside, os.path.join(d, "link.json"))
            os.makedirs(os.path.join(d, "sub")); os.chmod(os.path.join(d, "sub"), 0o755)
            run(exe)
            m = lambda p: os.stat(p).st_mode & 0o777
            check("D-9: files others could read are closed to them; the owner's own bits are kept",
                  m(a) == 0o600 and m(b) == 0o600 and m(c) == 0o600 and m(x) == 0o700, [oct(m(p)) for p in (a, b, c, x)])
            check("D-9: a link is not followed and a folder is left alone",
                  m(outside) == 0o644 and m(os.path.join(d, "sub")) == 0o755, [oct(m(outside))])
        else:
            check("D-9: the sweep compiles on the host", False, out)

    # ------------------------------------------------------------ B-2, B-4: the cross-site guard (run in test_xsite_cgi_guard.py)
    hc = rd("httpd", "httpd.c")
    g = fn(hc, "static int reaper_xsite_cgi_refused(")
    check("B-2: the guard covers the acting pages by file name - aidisk/, the Samba/FTP switch, WAN action, safe removal, app state",
          'strstr(url, "aidisk/") != NULL' in g and all(('"%s"' % p) in g for p in
              ("switch_AiDisk_app.asp", "wan_action.asp", "safely_remove_disk.asp", "update_appstate.asp", "apscan.asp"))
          and "const char *base = strrchr(url, '/');" in g and 'strcmp(url, "apscan.asp")' not in g)
    check("B-4: a Referer on the same host but another port is cross-site; a Host without a port takes the Referer scheme's port",
          "reaper_origin_port(referer_url, rdef) != reaper_origin_port(host_name, rdef)" in g
          and 'int rdef = !strncasecmp(referer_url, "https://", 8) ? 443 : 80;' in g)
    check("B-4: Sec-Fetch-Site same-site counts as cross-site, with or without a Referer",
          'xsite = strcasecmp(sfs, "cross-site") == 0 || strcasecmp(sfs, "same-site") == 0;' in g
          and '!strcasecmp(rh, hh) && (!strcasecmp(sfs, "cross-site") || !strcasecmp(sfs, "same-site"))' in g)

    # ------------------------------------------------------------ B-5: the request in flight
    hr = hc[hc.find("static void\nhandle_request(void)"):]
    check("B-5: handle_request writes no nvram for the request in flight; the note is a private file, removed at the end",
          'nvram_set("httpd_handle_request"' not in hc and 'nvram_unset("httpd_handle_request"' not in hc
          and "reaper_req_note(url, fromapp);" in hr and "unlink(REAPER_REQ_NOTE);" in hr)
    wblk = wd[wd.find('logmessage("watchdog", "start httpd");'):][:1800]
    check("B-5: the watchdog keeps a reduced copy from that file, never the nvram value",
          'nvram_safe_get("httpd_handle_request")' not in wd and 'f_read_string("/tmp/reaper/httpd.req"' in wblk
          and 'nvram_set("last_httpd_handle_request", reaper_u);' in wblk and "strchr(\"._-/\", c)" in wblk)
    note = fn(hc, "static void reaper_req_note(const char *u, int app)")
    if CC and note:
        np_ = os.path.join(tmp, "httpd.req")
        exe, out = build(tmp, "rq", r'''#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <fcntl.h>
#include <unistd.h>
#define REAPER_REQ_NOTE "%s"
''' % np_.replace("\\", "/") + note + r'''
int main(int argc, char **argv) { reaper_req_note(argv[1], argc > 2); return 0; }
''')
        if exe:
            run(exe, "aidisk/x.asp?a=1&b=<script>\x1b[2J $(reboot)", "app")
            got = open(np_).read() if os.path.isfile(np_) else ""
            check("B-5: the note holds only letters, digits and . _ - / (and the app flag), mode 0600",
                  got == "1 aidisk/x.asp_a_1_b__script___2J___reboot_\n" and (os.stat(np_).st_mode & 0o777) == 0o600, repr(got))
            run(exe, "A" * 400)
            got = open(np_).read()
            check("B-5: a long request is cut, the note never grows", len(got) <= 112 and got.startswith("0 AAAA") and got.endswith("\n"), len(got))
            os.remove(np_); target = os.path.join(tmp, "victim"); open(target, "w").write("keep"); os.symlink(target, np_)
            run(exe, "x.cgi")
            check("B-5: a link left at the note's path is not written through", open(target).read() == "keep")
            os.remove(np_)
        else:
            check("B-5: reaper_req_note compiles on the host", False, out)

    # ------------------------------------------------------------ A-1, A-2: the kernel's nvram netlink family
    kn = os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "bcmdrivers", "opensource", "char", "bcm_knvram", "impl1", "src", "wlcsm_netlink.c")
    if not os.path.isfile(kn):
        print("note the platform tree is not beside this router tree - the kernel nvram checks are skipped")
    else:
        k = open(kn, encoding="utf-8", errors="surrogateescape").read()
        bind = fn(k, "static int wlcsm_nl_bind(struct net *net, int group)")
        check("A-1: joining a group of the nvram netlink family needs CAP_SYS_ADMIN (the broadcast carries values)",
              "return capable(CAP_SYS_ADMIN) ? 0 : -EPERM;" in bind
              and re.search(r"\.input\s*=\s*wlcsm_nl_rcv_skb,\s*\n\s*\.bind\s*=\s*wlcsm_nl_bind,", k) is not None
              and k.find("static int wlcsm_nl_bind(") < k.find("int wlcsm_module_init(void)"))
        check("A-2: the two character-set helpers stay inside their 1024-byte buffer",
              "utf16s_to_utf8s(unibuf, i, UTF16_HOST_ENDIAN, buf, 1023);" in k and "buf, 1024);" not in k
              and "unibuf[i] && len + NLS_MAX_CHARSET_SIZE < 1024; i++)" in k)

    # ------------------------------------------------------------ rflogd: no forward of a line about its own forward packet
    rf = rd("rflogd", "rflogd.c")
    fw = fn(rf, "static void rfl_forward(const char *body, long long sec)")
    op = fn(rf, "static void rfl_fwd_open(void)")
    check("rflogd: a line that names the remote log server as destination (address and port) is not forwarded",
          "if (fwd_dst[0] && strstr(body, fwd_dst) && strstr(body, fwd_dpt))\n\t\treturn;" in fw
          and fw.find("strstr(body, fwd_dst)") < fw.find("sendto(fwd_fd"))
    check("rflogd: the match text is rebuilt with every (re)open of the forward socket, from the parsed address",
          "fwd_dst[0] = fwd_dpt[0] = 0;" in op and 'snprintf(fwd_dst, sizeof(fwd_dst), "DST=%s ", a);' in op
          and 'snprintf(fwd_dpt, sizeof(fwd_dpt), "DPT=%u ", (unsigned)C.fwd_port);' in op and "inet_ntop(AF_INET6, &s6->sin6_addr, a, sizeof(a));" in op)

    # ------------------------------------------------------------ C-8: a collector that runs but does nothing
    check("C-8: rflogd rewrites stats.json at least every RFL_BEAT seconds",
          "#define RFL_BEAT\t30" in rf and "if ((stats_dirty && m - stats_at >= 2) || m - stats_at >= RFL_BEAT)\n\t\t\trfl_stats(now);" in rf)
    fl = rd("rc", "reaper_fwlog.c")
    a = fl.find("static int rfl_pid;"); b = fl.find("static long rfl_num(")
    watch = fn(fl, "void reaper_fwlog_watch(void)")
    check("C-8: the watchdog reads the collector's pid and stamp and compares the stamp by CHANGE, on uptime",
          0 < a < b and "#define RFL_HUNG\t150" in fl[a:b] and "rfl_upd != seen_upd" in watch and "long up = uptime();" in watch
          and "kill(rfl_pid, SIGKILL);" in watch and watch.find("kill(rfl_pid, SIGKILL);") < watch.find("if (rfl_nflog()) {"))
    if CC and 0 < a < b and watch:
        exe, out = build(tmp, "hung", r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <time.h>
#define RFL_STATS "stats"
static char STATS[256]; static int KILLED, ASKED; static long UP = 5000;
static int rfl_slurp(const char *p, char *b, size_t n) {
	if (strstr(p, "/comm")) { snprintf(b, n, "rflogd\n"); return 0; }
	if (!STATS[0]) return -1;
	snprintf(b, n, "%s", STATS); return 0; }
static int t_kill(int pid, int sig) { (void)pid; if (sig == SIGKILL) { KILLED++; STATS[0] = 0; } return 0; }
#define kill(p, s) t_kill(p, s)
static long uptime(void) { return UP; }
static int is_routing_enabled(void) { return 1; }
static int rfl_nflog(void) { return 1; }
static int notify_rc(const char *s) { if (!strcmp(s, "restart_rflog")) ASKED++; return 0; }
#define logmessage(tag, ...) ((void)0)
''' + fl[a:b] + watch + r'''
static void st(int pid, long upd) { snprintf(STATS, sizeof(STATS), "{\"updated\":%ld,\"since\":1,\"pid\":%d,\"mode\":\"full\"}", upd, pid); }
static void secs(int n, int beat, long *upd) { int i; for (i = 0; i < n; i++) { UP++; if (beat && STATS[0] && UP % beat == 0) st(4242, ++*upd); reaper_fwlog_watch(); } }
int main(void) {
	long upd = 1700000000; int bad = 0;
	st(4242, upd); secs(900, 30, &upd);                 /* healthy: a new stamp every 30 s */
	if (KILLED || ASKED) { printf("healthy collector touched: killed=%d asked=%d\n", KILLED, ASKED); bad++; }
	upd += 99999999; st(4242, upd); secs(600, 30, &upd); /* the clock jumped (NTP): still healthy */
	if (KILLED) { printf("clock jump killed it\n"); bad++; }
	st(4242, ++upd); secs(2, 0, &upd);                   /* one last report, seen by the watch ... */
	secs(140, 0, &upd);                                  /* ... then stuck for 140 s: not yet */
	if (KILLED) { printf("killed after 140 s\n"); bad++; }
	secs(20, 0, &upd);                                   /* past 150 s: killed once, and a restart is asked for */
	if (KILLED != 1 || ASKED < 1) { printf("stuck collector: killed=%d asked=%d\n", KILLED, ASKED); bad++; }
	st(5151, ++upd); KILLED = 0; secs(600, 30, &upd);    /* the new one reports: left alone */
	if (KILLED) { printf("the replacement was killed\n"); bad++; }
	return bad;
}
''')
        rc_, o = run(exe) if exe else (1, out)
        check("C-8: a reporting collector is never touched (also across a clock jump); a silent one is killed after 150 s and restarted", rc_ == 0, o)
    cert = fn(enc, "static int red_public_name(char *out, size_t outsz)")
    check("C-8: a certificate chain that did not verify is tried again, once a minute at most (run in test_doh_server.py)",
          "(c_bad && uptime() - c_bad >= 60)" in cert and "c_bad = trusted ? 0 : (uptime() > 0 ? uptime() : 1);" in cert)

    # ------------------------------------------------------------ C-3 (the rest, per caller): folders a root daemon serves from
    tm = rd("rc", "timemachine.c")
    check("C-3: the captive portal's web folders and the avahi config folders are made 0755 by reaper_secure_dir, never 0777",
          'mkdir_if_none("/tmp/uamsrv' not in svc and svc.count('reaper_secure_dir("/tmp/uamsrv", 0755);') == 3
          and svc.count('reaper_secure_dir("/tmp/uamsrv/www", 0755);') == 3 and 'reaper_secure_dir("/tmp/uamsrv/www/USB", 0755);' in svc
          and "mkdir_if_none(AVAHI_" not in tm and "reaper_secure_dir(AVAHI_CONFIG_PATH, 0755);" in tm
          and "reaper_secure_dir(AVAHI_SERVICES_PATH, 0755);" in tm)
    order = [svc.find('reaper_secure_dir("/tmp/uamsrv", 0755);'), svc.find('reaper_secure_dir("/tmp/uamsrv/www", 0755);'),
             svc.find('reaper_secure_dir("/tmp/uamsrv/www/USB", 0755);')]
    check("C-3: parent before child (the helper does not make missing parents)", 0 < order[0] < order[1] < order[2], order)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed: option 162 follows the certificate and every network, port 443 is shared correctly, the mesh "
      "lock is bounded, AiMesh sync files are private")
