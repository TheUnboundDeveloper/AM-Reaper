#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal create / delete always applied on the router; portal processes follow the settings (2026-11-12).

WHY THIS EXISTS. Field report: a Guest Portal network switched on did nothing until a reboot, and switched off
stayed on. Reproduced on the owner's router: on an AiMesh router httpd hands the Network page's service list to
the closed cfg_server (/tmp/cfg.json action_script); a create ("restart_wireless;restart_sdn 4;restart_chilli;
restart_uam_srv;") reached it as "...restart_sdn+4..." and nothing reached rc - settings saved, no Wi-Fi restart,
no bridge, no portal. A delete (no argument) ran.

WHAT IT DOES. Compiles on the host, against stubs, and runs: the settle decisions and pending-file reader
(rc/sdn.c RSDN-PURE block), httpd's guest-network request recognition / merge / settle start
(httpd/web.c reaper_sdn_pending), rc's chilli finder against a real dummy "chilli" process, and the portal
reconcile (rc/services.c). Then pins every call site: the hand-off, the handler stamps, the stop fallbacks, the
applet entry and its /sbin symlink. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router tree - argv[1] or
REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, signal, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "sdn.c")):
    skip("no router tree with rc/sdn.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

sdn, svc, web = read("rc/sdn.c"), read("rc/services.c"), read("httpd/web.c")
rcc, rch, mk = read("rc/rc.c"), read("rc/rc.h"), read("rc/Makefile")
TMP = tempfile.mkdtemp()

def build(name, code):
    c = os.path.join(TMP, name + ".c"); exe = os.path.join(TMP, name)
    open(c, "w").write(code)
    r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
    return exe if r.returncode == 0 else None, r.stderr

COMMON = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <ctype.h>
#include <dirent.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/types.h>
static size_t strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l < n - 1 ? l : n - 1; memcpy(d, s, c); d[c] = 0; } return l; }
'''

# ---------------------------------------------------------------- 1. settle decisions + pending reader
m = re.search(r"/\* RSDN-PURE-BEGIN.*?\*/(.*?)/\* RSDN-PURE-END \*/", sdn, re.S)
check("rc/sdn.c carries the RSDN-PURE block", m is not None)
consts = re.findall(r"#define RSDN_SETTLE_(?:S|MAX)\s+\d+", sdn)
check("settle window constants present (15 s, never over 45 s)", "#define RSDN_SETTLE_S\t15" in sdn and "#define RSDN_SETTLE_MAX\t45" in sdn, consts)
if m:
    code = COMMON + "\n".join(consts) + r'''
static int fake_root = 1;
static int t_fstat(int fd, struct stat *st) { int r = fstat(fd, st); if (r == 0 && fake_root) st->st_uid = 0; return r; }
#define fstat(a, b) t_fstat(a, b)
''' + m.group(1) + r'''
#undef fstat
int main(int argc, char **argv)
{
	char list[256]; long t = 0;
	if (argv[1][0] == 's') {	/* s second t0 have t applied busy */
		printf("%d\n", rsdn_settle_step(atoi(argv[2]), atol(argv[3]), atoi(argv[4]), atol(argv[5]), atol(argv[6]), atoi(argv[7])));
	} else if (argv[1][0] == 'p') {	/* p path [notroot] */
		fake_root = argc < 4;
		int ok = rsdn_read_pending(argv[2], &t, list, sizeof(list));
		printf("%d %ld %s\n", ok, ok ? t : 0, ok ? list : "-");
	} else if (argv[1][0] == 'l') {
		printf("%ld\n", rsdn_read_long(argv[2]));
	}
	return 0;
}
'''
    exe, err = build("settle", code)
    check("RSDN-PURE compiles with -Wall -Werror", exe is not None, err)
    if exe:
        def step(*a): return subprocess.run([exe, "s"] + [str(x) for x in a], capture_output=True, text=True).stdout.strip()
        check("applied after the request -> done, nothing run", step(3, 100, 1, 100, 101, 0) == "1" and step(3, 100, 1, 100, 100, 0) == "1")
        check("request gone, or replaced by a newer one -> done (the newer settle owns it)", step(3, 100, 0, 0, -1, 0) == "1" and step(3, 100, 1, 105, -1, 0) == "1")
        check("not applied, inside the 15 s window -> keep waiting", step(14, 100, 1, 100, 99, 0) == "0")
        check("not applied, window over and rc idle -> apply now", step(15, 100, 1, 100, 99, 0) == "2" and step(15, 100, 1, 100, -1, 0) == "2")
        check("not applied, window over but rc busy -> wait, but never past 45 s", step(30, 100, 1, 100, 99, 1) == "0" and step(45, 100, 1, 100, 99, 1) == "2")
        def pend(content, notroot=False):
            p = os.path.join(TMP, "pend")
            if content is None:
                if os.path.exists(p): os.unlink(p)
            else:
                open(p, "w").write(content)
            return subprocess.run([exe, "p", p] + (["x"] if notroot else []), capture_output=True, text=True).stdout.strip()
        check("pending file read: time and the whole list (spaces kept)", pend("1234 restart_wireless;restart_sdn 4;restart_chilli;\n") == "1 1234 restart_wireless;restart_sdn 4;restart_chilli;")
        check("pending file absent / malformed / empty list -> 0", pend(None) == "0 0 -" and pend("abc def\n") == "0 0 -" and pend("1234\n") == "0 0 -" and pend("1234 \n") == "0 0 -")
        check("pending file not root's -> refused", pend("1234 restart_sdn;\n", notroot=True) == "0 0 -")
        lp = os.path.join(TMP, "applied"); open(lp, "w").write("777\n")
        check("applied stamp read; absent -> -1",
              subprocess.run([exe, "l", lp], capture_output=True, text=True).stdout.strip() == "777"
              and subprocess.run([exe, "l", lp + "x"], capture_output=True, text=True).stdout.strip() == "-1")

# ---------------------------------------------------------------- 2. httpd: recognise, merge, record, start settle
hm = re.search(r"(/\* is t\[0\.\.n\) a guest-network service.*?\nstatic void reaper_sdn_pending\(const char \*act\)\n\{.*?\n\}\n)", web, re.S)
check("httpd/web.c carries reaper_sdn_tok / reaper_sdn_list_has / reaper_sdn_pending", hm is not None)
if hm:
    pdir = os.path.join(TMP, "reaper")
    body = (hm.group(1).replace('"/tmp/reaper"', '"%s"' % pdir).replace("REAPER_TMPDIR", '"%s"' % pdir)
            .replace("RSDN_PENDING", '"%s/sdn_pending"' % pdir))
    code = COMMON + r'''
static int reaper_secure_dir(const char *p, mode_t m) { return mkdir(p, m); }
static long now_s = 1000;
static long uptime(void) { return now_s; }
static int _eval(char *const argv[], const char *path, int timeout, pid_t *ppid) { printf("eval %s %s\n", argv[0], argv[1]); return 0; }
/* the build host is not root: report the test's own file as root's, as it is on the router */
static int t_fstat(int fd, struct stat *st) { int r = fstat(fd, st); if (r == 0) st->st_uid = 0; return r; }
#define fstat(a, b) t_fstat(a, b)
''' + body + r'''
#undef fstat
int main(int argc, char **argv)
{
	int i;
	for (i = 1; i < argc; i++) {
		if (argv[i][0] == '@') now_s = atol(argv[i] + 1);
		else { reaper_sdn_pending(argv[i]); printf("|\n"); }
	}
	return 0;
}
'''
    exe, err = build("pending", code)
    check("httpd helpers compile with -Wall -Werror", exe is not None, err)
    if exe:
        pf = os.path.join(pdir, "sdn_pending")
        def run(*a):
            if os.path.exists(pf): os.unlink(pf)
            o = subprocess.run([exe] + list(a), capture_output=True, text=True).stdout
            return [x.strip() for x in o.split("|")][:-1], (open(pf).read() if os.path.exists(pf) else None)
        o, f = run("restart_wireless;restart_qos;")
        check("a request with no guest-network service: nothing recorded, no settle", o == [""] and f is None, (o, f))
        o, f = run("restart_wireless;restart_sdn 4;restart_chilli;restart_uam_srv;")
        check("a portal create: recorded verbatim with its time, settle started with that time",
              f == "1000 restart_wireless;restart_sdn 4;restart_chilli;restart_uam_srv;\n" and o == ["eval /sbin/reaper_sdn_settle 1000"], (o, f))
        check("the record is root-only (0600)", f is not None and (os.stat(pf).st_mode & 0o777) == 0o600)
        o, f = run("start_sdn_del;restart_wireless;restart_qos;restart_firewall;")
        check("a delete is recognised too", f == "1000 start_sdn_del;restart_wireless;restart_qos;restart_firewall;\n", f)
        o, f = run("restart_wireless;restart_sdn 4;", "@1010", "restart_wireless;restart_sdn 5;restart_chilli;")
        check("a second change within 60 s keeps the first one's services and adds the new ones (no duplicates)",
              f == "1010 restart_wireless;restart_sdn 4;restart_sdn 5;restart_chilli;\n", f)
        o, f = run("restart_wireless;restart_sdn 4;", "@1100", "restart_wireless;restart_sdn 5;")
        check("a pending request older than 60 s is not merged", f == "1100 restart_wireless;restart_sdn 5;\n", f)
        check("restart_sdnx / restart_chilli2 are not guest-network services (whole names only)",
              run("restart_sdnx;restart_chilli2;")[1] is None)

# ---------------------------------------------------------------- 3. rc: chilli finder against a real process
cm = re.search(r"(int reaper_chilli_count\(const char \*conf, int sig\)\n\{.*?\n\}\n)", svc, re.S)
check("rc/services.c carries reaper_chilli_count", cm is not None)
if cm:
    dummy, err = build("chilli", "#include <unistd.h>\nint main(void){ sleep(30); return 0; }\n")
    finder, err2 = build("finder", COMMON + cm.group(1) + r'''
int main(int argc, char **argv) { printf("%d\n", reaper_chilli_count(argv[1], argc > 2 ? atoi(argv[2]) : 0)); return 0; }
''')
    check("finder + dummy chilli compile", dummy is not None and finder is not None, (err or "") + (err2 or ""))
    if dummy and finder:
        procs = [subprocess.Popen([dummy, "-c", "/tmp/chilli.conf"]),
                 subprocess.Popen([dummy, "-c", "/tmp/chilli-cp.conf", "--pidfile=/var/run/chilli-cp.pid"])]
        time.sleep(0.3)
        def cnt(conf, sig=0): return subprocess.run([finder, conf, str(int(sig))], capture_output=True, text=True).stdout.strip()
        check("finds the Free Wi-Fi chilli by its config, and only that one", cnt("/tmp/chilli.conf") == "1" and cnt("/tmp/chilli-cp.conf") == "1")
        check("a config nobody runs -> 0", cnt("/tmp/none.conf") == "0")
        cnt("/tmp/chilli.conf", signal.SIGTERM); time.sleep(0.3)
        check("SIGTERM stops the matching chilli and leaves the other instance alone",
              procs[0].poll() is not None and procs[1].poll() is None)
        for p in procs:
            if p.poll() is None: p.kill()

# ---------------------------------------------------------------- 4. portal reconcile
rm_ = re.search(r"(/\* which portals an enabled network asks for.*?\nstatic void reaper_portal_reconcile\(const char \*rest\)\n\{.*?\n\}\n)", svc, re.S)
check("rc/services.c carries reaper_portals_wanted / reaper_portal_reconcile", rm_ is not None)
if rm_:
    code = COMMON + r'''
typedef struct { int cp_idx; } SDN_T_;
typedef struct { int enable; SDN_T_ sdn_t; } MTLAN_T;
typedef struct { int cp_idx; int cp_type; } CP_TYPE_RL;
static int nnet = 0, en[4], cpidx[4], cptype[8], run_fw = 0, run_cp = 0;
static void *INIT_MTLAN(unsigned int sz) { return calloc(8, sz); }
static void FREE_MTLAN(void *p) { free(p); }
static MTLAN_T *get_mtlan(MTLAN_T *l, size_t *sz) { int i; for (i = 0; i < nnet; i++) { l[i].enable = en[i]; l[i].sdn_t.cp_idx = cpidx[i]; } *sz = nnet; return l; }
static CP_TYPE_RL *get_cp_type_byidx(int idx, CP_TYPE_RL *c) { if (idx < 1 || idx > 7 || !cptype[idx]) return NULL; c->cp_idx = idx; c->cp_type = cptype[idx]; return c; }
static int reaper_chilli_count(const char *conf, int sig) { return strstr(conf, "-cp") ? run_cp : run_fw; }
static void logmessage(const char *h, const char *f, ...) { }
static void start_chilli(void) { printf("start_chilli\n"); }
static void stop_chilli(void) { printf("stop_chilli\n"); }
static void start_CP(void) { printf("start_CP\n"); }
static void stop_CP(void) { printf("stop_CP\n"); }
static void setup_passwd(void) { }
''' + rm_.group(1) + r'''
int main(int argc, char **argv)
{	/* argv: rest fw_running cp_running [enable:cpidx ...]; cp_type_rl fixed: 1>1 2>2 3>3 4>4 */
	int i;
	cptype[1] = 1; cptype[2] = 2; cptype[3] = 3; cptype[4] = 4;
	run_fw = atoi(argv[2]); run_cp = atoi(argv[3]);
	for (i = 4; i < argc; i++) { en[nnet] = atoi(argv[i]); cpidx[nnet] = atoi(strchr(argv[i], ':') + 1); nnet++; }
	reaper_portal_reconcile(strcmp(argv[1], "-") ? argv[1] : NULL);
	return 0;
}
'''
    exe, err = build("reconcile", code)
    check("reconcile compiles with -Wall -Werror", exe is not None, err)
    if exe:
        def rec(*a): return subprocess.run([exe] + list(a), capture_output=True, text=True).stdout.split()
        check("enabled Free Wi-Fi portal, nothing running -> start_chilli", rec("-", "0", "0", "1:2") == ["start_chilli"])
        check("message-board portal (type 4) counts as Free Wi-Fi", rec("-", "0", "0", "1:4") == ["start_chilli"])
        check("portal network switched off, chilli still running -> stop_chilli", rec("-", "1", "0", "0:2") == ["stop_chilli"])
        check("portal network deleted (no network asks), chilli running -> stop_chilli", rec("-", "1", "0") == ["stop_chilli"])
        check("already in the right state -> nothing", rec("-", "1", "0", "1:2") == [] and rec("-", "0", "0", "1:0") == [])
        check("restart_chilli still to come in this list -> leave chilli to it (no double start)",
              rec("restart_chilli;restart_uam_srv;", "0", "0", "1:2") == [])
        check("account portal (type 1) handled the same way through start_CP / stop_CP",
              rec("-", "0", "0", "1:1") == ["start_CP"] and rec("-", "0", "1") == ["stop_CP"] and rec("restart_CP;", "0", "0", "1:1") == [])

# ---------------------------------------------------------------- 4b. '+' in the service list (_r1, owner's router)
# The list reached httpd as "...restart_sdn+4..." and none of it ran, whether by way of cfg_server
# or of the settle step. httpd turns '+' back into a space on its own copy; the settle step does too.
pm = re.search(r"(\t\tif \(action_para && strchr\(action_para, '\+'\)\) \{\n.*?\n\t\t\}\n)", web, re.S)
check("httpd: rc_service '+' turned back into spaces, right after it is read and before any hand-off",
      pm is not None and web.find('action_para = get_cgi_json("rc_service",root);\n\t\t/* reaper 2026-11-12 (Guest Portal')
      < web.find("static char reaper_rcsvc[1024];") < web.find("reaper_sdn_pending(action_para);"))
if pm:
    exe, err = build("plus", COMMON + r'''
int main(int argc, char **argv)
{
	char *action_para = argv[1];
''' + pm.group(1) + r'''
	puts(action_para);
	return 0;
}
''')
    check("httpd conversion block compiles", exe is not None, err)
    if exe:
        o = subprocess.run([exe, "restart_wireless;restart_sdn+4;restart_chilli;restart_uam_srv;"], capture_output=True, text=True).stdout.strip()
        check("the router's exact list comes out runnable", o == "restart_wireless;restart_sdn 4;restart_chilli;restart_uam_srv;", o)
        o = subprocess.run([exe, "start_sdn_del;restart_wireless;"], capture_output=True, text=True).stdout.strip()
        check("a list without '+' is handed on unchanged", o == "start_sdn_del;restart_wireless;", o)
check("settle: '+' turned into spaces before the list is resubmitted",
      "\tfor (i = 0; list[i]; i++)	/* 2026-11-12: no service name holds a '+' (see httpd apply_cgi) */\n\t\tif (list[i] == '+')\n\t\t\tlist[i] = ' ';\n\tlogmessage(\"sdn\"" in sdn)

# ---------------------------------------------------------------- 5. call sites
check("httpd: the guest-network request is recorded right before cfg_server is signalled (apply_cgi only)",
      web.count("reaper_sdn_pending(action_para);") == 1
      and re.search(r"reaper_sdn_pending\(action_para\);[^\n]*\n\n\t+/\* trigger cfg_server to send notification \*/\n\t+kill_pidfile_s\(CFG_SERVER_PID, SIGUSR2\);", web) is not None)
check("httpd: helper under RTCONFIG_CFGSYNC, settle started by its /sbin path, /tmp/reaper made the hardened way",
      "#ifdef RTCONFIG_CFGSYNC\n/* reaper 2026-11-12 (Guest Portal field report" in web and '"/sbin/reaper_sdn_settle"' in web
      and "\treaper_secure_dir(REAPER_TMPDIR, 0700);	/* tmp hardening: root's own directory */\n\tif ((fd = mkstemp(tmp)) < 0)" in web
      and "\treaper_secure_dir(RSDN_DIR, 0700);	/* tmp hardening: root's own directory */" in sdn)
check("rc: the sdn handler stamps and reconciles (start only); sdn_del stamps and reconciles",
      "reaper_sdn_applied_stamp();	/* reaper 2026-11-12: reaper_sdn_settle (rc/sdn.c) sees it ran */\n#ifdef RTCONFIG_COOVACHILLI\n\t\tif (action & RC_SERVICE_START)\n\t\t\treaper_portal_reconcile(nvptr);" in svc
      and "remove_sdn();\n\t\tgk_refresh();	/* reaper v2.6.5 */\n\t\treaper_sdn_applied_stamp();	/* reaper 2026-11-12 */\n#ifdef RTCONFIG_COOVACHILLI\n\t\treaper_portal_reconcile(nvptr);" in svc)
check("rc: stop_chilli / stop_CP no longer skip a running chilli, and stop one the pid file missed",
      'if(nvram_match("chilli_enable", "0") && reaper_chilli_count("/tmp/chilli.conf", 0) <= 0){' in svc
      and 'if(nvram_match("cp_enable", "0") && reaper_chilli_count("/tmp/chilli-cp.conf", 0) <= 0){' in svc
      and svc.count('reaper_chilli_count("/tmp/chilli.conf", SIGKILL);') == 1 and svc.count('reaper_chilli_count("/tmp/chilli-cp.conf", SIGKILL);') == 1)
check("rc: stop_uam_srv falls back to the process name when no pid file was written",
      '\t\tif (pids("uamsrv"))	/* reaper 2026-11-12: no pid file was written - stop it by its own name */\n\t\t\tkillall_tk("uamsrv");' in svc)
check("rc: applet registered under MULTILAN_CFG, extern declared, and /sbin symlink installed (basename dispatch)",
      '\t{ "reaper_sdn_settle",		reaper_sdn_settle_main			},' in rcc
      and "extern int reaper_sdn_settle_main(int argc, char *argv[]);" in rch
      and "\t@cd $(INSTALLDIR)/sbin && ln -sf rc reaper_sdn_settle" in mk)
check("rc: the settle applies with notify_rc_and_wait_2min and logs one line",
      'logmessage("sdn", "a network change was saved but not applied - applying it now (%s)", list);\n\tnotify_rc_and_wait_2min(list);' in sdn)

shutil.rmtree(TMP, ignore_errors=True)
if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
