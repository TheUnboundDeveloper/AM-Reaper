#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-11, remediation phase 2: checks placed in open code around code that ships without source.

WHY THIS EXISTS. Some of the review's findings sit in vendor objects that cannot be changed. Each one is contained
from open code instead:
  - three netlink families are served by prebuilt kernel modules (22, 23, 29 on a running router): the kernel's
    netlink send path now asks for CAP_SYS_ADMIN on those three families;
  - prebuilt objects in the web server call rand(): every rand() in the program now reads the kernel's generator;
  - a second admin password for the phone-app login (http_passwd_app) was never cleared: it is emptied at start and
    before each login check, and the settings gate refuses to store one;
  - the captive-portal page answer echoed its query as a web page: that answer is now sent as plain text;
  - the health watchdog reports a process that takes the radio crash helper's name and restarts a missing helper;
    the roaming assistant's local socket is kept root-only;
  - lan_gateway must be an IPv4 address;
  - a restart request sent from inside rc's own handler is not carried out: no such call may come back;
  - the diagnostics report gains section 12d (radio call stalls).

WHAT IT DOES. Cuts the real functions out of the tree, compiles them on the host and runs them (the netlink verdict,
the rand() replacement, the address check), runs the watchdog's new shell lines against stand-in commands, and pins
the call sites.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwatch.c")):
    skip("no router source tree with rc/rwatch.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
SH = shutil.which("sh")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))

def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

def nocomment(s):
    return re.sub(r"/\*.*?\*/", " ", s, flags=re.S)

def build_run(tmp, name, code, extra=(), run=True):
    """compile `code` (+ extra args) with every warning an error; returns (ok, output)"""
    src = os.path.join(tmp, name + ".c"); exe = os.path.join(tmp, name)
    open(src, "w", encoding="utf-8", errors="surrogateescape").write(code)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, src] + list(extra),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    if r.returncode != 0:
        return False, r.stdout
    if not run:
        return True, ""
    r = subprocess.run([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
    return r.returncode == 0, r.stdout

tmp = tempfile.mkdtemp(prefix="rev1111p2_")
try:
    # ------------------------------------------------------------ netlink families of the vendor modules
    kf = os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "kernel", "linux-4.19", "net", "netlink", "af_netlink.c")
    if not os.path.isfile(kf):
        print("note the kernel tree is not beside this router tree - the netlink checks are skipped")
    else:
        k = open(kf, encoding="utf-8", errors="surrogateescape").read()
        a, b = k.find("#define REAPER_NL_BRCM_A"), k.find("/* reaper-nl-gate: end */")
        check("kernel: the verdict function is present", 0 < a < b)
        send = k[k.find("static int netlink_sendmsg("):]
        send = send[:send.find("\n}\n")]
        g = send.find("if (reaper_nl_closed_family(sk->sk_protocol)) {")
        check("kernel: netlink_sendmsg asks the verdict after the message is copied in and before it is delivered",
              0 < send.find("memcpy_from_msg(skb_put(skb, len), msg, len)") < g < send.find("netlink_broadcast(sk, skb, dst_portid")
              and g < send.find("err = netlink_unicast(sk, skb, dst_portid")
              and "reaper_nl_closed_verdict(sk->sk_protocol, sk_capable(sk, CAP_SYS_ADMIN));" in send
              and "kfree_skb(skb);\n\t\t\tgoto out;" in send[g:g + 400])
        if CC and 0 < a < b:
            ok, out = build_run(tmp, "nl", '''#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <errno.h>
typedef unsigned int u32;
''' + k[a:b] + '''
int main(void) {
	int bad = 0, i;
	int closed[] = { 22, 23, 29 }, open_[] = { 0, 4, 12, 15, 16, 18, 17, 31 };
	for (i = 0; i < 8; i++)   /* every other family is untouched, with or without the capability */
		if (reaper_nl_closed_verdict(open_[i], false) || reaper_nl_closed_verdict(open_[i], true)) { printf("family %d touched\\n", open_[i]); bad++; }
	for (i = 0; i < 3; i++) {
		if (reaper_nl_closed_verdict(closed[i], false) != -EPERM) { printf("family %d open to all\\n", closed[i]); bad++; }
		if (reaper_nl_closed_verdict(closed[i], true) != 0) { printf("family %d refused with the capability\\n", closed[i]); bad++; }
	}
	return bad;
}
''')
            check("kernel: the verdict - other families untouched, 22/23/29 need CAP_SYS_ADMIN and pass with it", ok, out)
        check("kernel: the rule is the capability alone - no per-command filter",
              "REAPER_NL_IGS_CMD_OFF" not in k and "EOPNOTSUPP" not in k[a:b] and "skb->data, skb->len)" not in send[g:g + 200])

    # ------------------------------------------------------------ rand() in the web server
    mk = rd("httpd", "Makefile")
    check("httpd: reaper_rand.o is linked and rand/srand are wrapped",
          "OBJS += reaper_rand.o" in mk and "-Wl,--wrap=rand -Wl,--wrap=srand" in mk
          and os.path.isfile(os.path.join(SRC, "httpd", "reaper_rand.c")))
    if CC and os.path.isfile(os.path.join(SRC, "httpd", "reaper_rand.c")):
        rc_ = rd("httpd", "reaper_rand.c")
        check("httpd: the replacement never waits for the kernel generator and keeps rand()'s range",
              "GRND_NONBLOCK" in rc_ and "v & 0x7fffffffU" in rc_ and '"/dev/urandom"' in rc_ and "__real_rand()" in rc_)
        ok, out = build_run(tmp, "rnd", '''#include <stdio.h>
#include <stdlib.h>
int main(void) {
	int i, a[64], b[64], neg = 0, same = 0, bits = 0;
	srand(1); for (i = 0; i < 64; i++) { a[i] = rand(); if (a[i] < 0) neg++; bits |= a[i]; }
	srand(1); for (i = 0; i < 64; i++) { b[i] = rand(); if (b[i] < 0) neg++; if (a[i] == b[i]) same++; }
	/* rand()'s range is 0..RAND_MAX: a caller may index a table with it; a seed must not bring a sequence back */
	if (neg || same > 1 || (bits & 0x7fff0000) == 0) { printf("neg=%d same=%d bits=%x\\n", neg, same, bits); return 1; }
	return 0;
}
''', extra=[os.path.join(SRC, "httpd", "reaper_rand.c"), "-Wl,--wrap=rand", "-Wl,--wrap=srand"])
        check("httpd: rand() is never negative and srand() cannot replay a sequence", ok, out)

    # ------------------------------------------------------------ the second admin password
    web = rd("httpd", "web.c"); hc = rd("httpd", "httpd.c")
    check("web.c: reaper_app_pw_clear empties http_passwd_app, saves and logs - only when one is stored",
          'void reaper_app_pw_clear(void)\n{\n\tif (*nvram_safe_get("http_passwd_app")) {\n\t\tnvram_set("http_passwd_app", "");\n\t\tnvram_commit();' in web)
    code = nocomment(web)
    check("web.c: the first login form no longer tries the second password", "app_auth(authinfo, authpass)" not in code
          and 'nvram_match("http_username", authinfo) && compare_passwd_in_shadow(authinfo, authpass))' in code)
    i = web.find("auth_pass = validate_httpd_auth_v2(authorization_t, id, cnonce);")
    j = web.find("ret = do_chpass(cur_username, cur_passwd, new_username, new_passwd,")
    check("web.c: the setting is emptied right before the closed login check and the closed password-change check",
          i > 0 and j > 0 and "reaper_app_pw_clear();" in web[i - 160:i] and "reaper_app_pw_clear();" in web[j - 180:j])
    m = hc.find("int main(int argc, char **argv)")
    check("httpd.c: the setting is emptied when the web server starts", m > 0 and "reaper_app_pw_clear();" in hc[m:m + 6000])
    api = rd("libwebapi", "webapi.c")
    check("settings gate: a non-empty http_passwd_app is refused, lan_gateway must be an IPv4 address",
          'if (*value && strcmp(name, "http_passwd_app") == 0)\n\t\t\treturn 0;' in api
          and 'if (*value && strcmp(name, "lan_gateway") == 0 && !reaper_dotted_v4(value))' in api)
    a = api.find("static int reaper_dotted_v4(const char *s)")
    if CC and a > 0:
        body = api[a:api.find("\n}\n", a) + 3]
        ok, out = build_run(tmp, "v4", "#include <stdio.h>\n#include <string.h>\n" + body + '''
int main(void) {
	const char *good[] = { "192.168.50.1", "0.0.0.0", "255.255.255.255", "10.0.0.254" };
	const char *bad[] = { "", "1.2.3", "1.2.3.4.5", "256.1.1.1", "1.2.3.4 ", " 1.2.3.4", "1..2.3", "1.2.3.", ".1.2.3", "a.b.c.d",
	                      "1.2.3.4;reboot", "0001.2.3.4", "192.168.050.0011", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "1.2.3.4\\n" };
	unsigned i; int n = 0;
	for (i = 0; i < sizeof(good) / sizeof(*good); i++) if (!reaper_dotted_v4(good[i])) { printf("refused %s\\n", good[i]); n++; }
	for (i = 0; i < sizeof(bad) / sizeof(*bad); i++) if (reaper_dotted_v4(bad[i])) { printf("accepted [%s]\\n", bad[i]); n++; }
	if (reaper_dotted_v4(NULL)) n++;
	return n;
}
''')
        check("settings gate: the address check takes four numbers 0-255 and nothing longer than 15 characters", ok, out)
    else:
        check("settings gate: reaper_dotted_v4 is present", a > 0)
    svc = rd("rc", "services.c")
    i = svc.find("int start_networkmap(int bootwait)")
    blk = svc[i:i + 2500]
    check("rc: a lan_gateway that is not an IPv4 address is removed before networkmap starts (and only then)",
          i > 0 and 'if (*reaper_gw && (strlen(reaper_gw) > 15 || inet_pton(AF_INET, reaper_gw, &reaper_a) != 1)) {' in blk
          and 'nvram_unset("lan_gateway");' in blk and blk.find("stop_networkmap();") < blk.find("reaper_gw") < blk.find('networkmap_argv[1] = "--bootwait";'))

    # ------------------------------------------------------------ the captive portal's answer
    rs = rd("lighttpd-1.4.39", "src", "response.c")
    i = rs.find('strstr(con->uri.query->ptr, "login=")')
    check("lighttpd: a /Uam or /FreeUam answer to a login= query goes out as plain text, nosniff, with a closed policy",
          i > 0 and i < rs.find("/* add all headers */")
          and 'strncasecmp(con->uri.path->ptr, "/Uam", 4)' in rs and 'strncasecmp(con->uri.path->ptr, "/FreeUam", 8)' in rs
          and 'CONST_STR_LEN("Content-Type"), CONST_STR_LEN("text/plain; charset=utf-8")' in rs
          and 'CONST_STR_LEN("X-Content-Type-Options"), CONST_STR_LEN("nosniff")' in rs
          and "CONST_STR_LEN(\"Content-Security-Policy\"), CONST_STR_LEN(\"default-src 'none'; sandbox\")" in rs)
    uam = os.path.join(SRC, "lighttpd-1.4.39", "external_file", "css", "uam.js")
    if os.path.isfile(uam):
        u = open(uam, encoding="utf-8", errors="replace").read()
        check("the portal page still reads that answer as text (so plain text changes nothing for it)",
              "dataType: 'text'" in u and "window.location = data;" in u and 'param.login = "login";' in u)

    # ------------------------------------------------------------ the watchdog: crash helper and the roaming socket
    rw = rd("rc", "rwatch.c")
    a = rw.find("/* review 2026-11-11. The radio driver's crash helper (debug_monitor)"); b = rw.find("/* reaper v2.6.9 (field): after a reboot", a)
    check("rwatch: the block sits before the policy-routing heal", 0 < a < b)
    check("rc: the reaper_dbgmon verb starts the helper only when none runs",
          'else if (strcmp(script, "reaper_dbgmon") == 0)' in svc
          and 'if((action & RC_SERVICE_START) && !pids("debug_monitor")) start_dhd_monitor();' in svc)
    if SH and 0 < a < b:
        lines = "".join(m.group(1).encode("latin-1", "backslashreplace").decode("unicode_escape")
                        for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', rw[rw.find("*/", a) + 2:b]))
        check("rwatch: no stat applet (the router's BusyBox has none)", "stat " not in lines)
        d = os.path.join(tmp, "rw"); os.makedirs(os.path.join(d, "bin")); os.makedirs(os.path.join(d, "reaper"))
        helper = os.path.join(d, "debug_monitor"); open(helper, "w").write("#!/bin/sh\n"); os.chmod(helper, 0o755)
        body = lines.replace("/tmp/reaper/", d + "/reaper/").replace("/usr/sbin/debug_monitor", helper).replace("/var/run/rast_ipc_socket", d + "/sock")
        def stub(name, text):
            p = os.path.join(d, "bin", name); open(p, "w").write("#!/bin/sh\n" + text + "\n"); os.chmod(p, 0o755)
        stub("pidof", 'cat "%s/pids" 2>/dev/null' % d)
        stub("readlink", 'cat "%s/exe" 2>/dev/null' % d)
        stub("logger", 'shift 2; echo "$*" >> "%s/log"' % d)
        stub("service", 'echo "$*" >> "%s/svc"' % d)
        def tick(pids="", exe="", wl="1", up="999"):
            open(os.path.join(d, "pids"), "w").write(pids); open(os.path.join(d, "exe"), "w").write(exe)
            script = "_nv() { echo %s; }\nUP=%s\nHEALGRACE=300\n" % (wl, up) + body
            r = subprocess.run([SH, "-c", script], env={"PATH": os.path.join(d, "bin") + ":/usr/bin:/bin"},
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=30)
            return r.returncode, r.stdout
        def got(name):
            p = os.path.join(d, name); return open(p).read() if os.path.isfile(p) else ""
        r1 = tick(); miss1 = os.path.isfile(os.path.join(d, "reaper", "dbgmon.miss")); svc1 = got("svc")
        r2 = tick(); svc2 = got("svc")
        check("rwatch: a missing helper is started on the second tick in a row, not the first",
              r1[0] == 0 and r2[0] == 0 and miss1 and svc1 == "" and svc2.strip() == "start_reaper_dbgmon" and "started again (1 of 3)" in got("log"), r1[1] + r2[1])
        for _ in range(12): tick()
        check("rwatch: at most three restarts a boot", got("svc").count("start_reaper_dbgmon") == 3, got("svc"))
        os.remove(os.path.join(d, "svc")); os.remove(os.path.join(d, "reaper", "dbgmon.n")); open(os.path.join(d, "log"), "w").close()
        tick(pids="41", exe=helper); tick(pids="41", exe=helper)
        check("rwatch: the real helper running = nothing done, nothing logged", got("svc") == "" and got("log") == "")
        tick(wl="0"); tick(wl="0"); tick(up="100"); tick(up="100")
        check("rwatch: no restart while the radios are down or during the boot grace", got("svc") == "")
        tick(pids="77", exe="/tmp/evil/debug_monitor")
        check("rwatch: a process of that name running another file is reported", "is not the radio driver helper - it runs /tmp/evil/debug_monitor" in got("log"), got("log"))
        import socket as _s
        sk = _s.socket(_s.AF_UNIX); sp = os.path.join(d, "sock"); sk.bind(sp); os.chmod(sp, 0o777); open(os.path.join(d, "log"), "w").close()
        tick(pids="41", exe=helper); mode = os.stat(sp).st_mode & 0o777
        check("rwatch: a roaming-assistant socket writable by others is closed to them and logged", mode == 0o755 and "socket was writable by other accounts" in got("log"), oct(mode))
        open(os.path.join(d, "log"), "w").close(); tick(pids="41", exe=helper)
        check("rwatch: a root-only socket is left alone", os.stat(sp).st_mode & 0o777 == 0o755 and got("log") == "")
        sk.close()

    # ------------------------------------------------------------ no restart request from inside rc's own handler
    allowed = {("reaper_fwlog.c", "restart_rflog")}   # sent from the watchdog process, never from PID 1
    bare = []
    for f in ("reaper_fw.c", "reaper_fwlog.c", "rwarden.c", "wallguard.c", "encdns.c", "reaper_meshchan.c", "reaper_aimesh.c"):
        p = os.path.join(SRC, "rc", f)
        if not os.path.isfile(p):
            continue
        c = nocomment(open(p, encoding="utf-8", errors="surrogateescape").read())
        for m in re.finditer(r'notify_rc(?:_and_wait)?\("([a-z_0-9]+)', c):
            if (f, m.group(1)) in allowed:
                continue
            if "getpid() == 1" not in c[max(0, m.start() - 900):m.start()] and "getpid() != 1" not in c[max(0, m.start() - 300):m.start()]:
                bare.append("%s:%s" % (f, m.group(1)))
    check("rc: every restart request in the Reaper engines is guarded against running inside rc itself (it would wait 15 s and be dropped)", not bare, bare)

    # ------------------------------------------------------------ diagnostics
    dg = rd("others", "reaper_diag")
    i = dg.find('sec "12d. RADIO CALL STALLS'); j = dg.find('sec "13. ADDONS / JFFS"')
    sec = dg[i:j]
    check("diag: v1.3.59 on the page and in the script", 'VER="REAPER-DIAG v1.3.59"' in dg and "REAPER-DIAG v1.3.59</span>" in rd("www", "Reaper_Diag.asp"))
    check("diag: section 12d reads the switches, the per-radio timeout (not while a task is blocked) and the driver's lines",
          0 < i < j and "nvram get reaper_dhd_ioto" in sec and "nvram get disable_exap" in sec and "nvram get reaper_bgdfs_stock" in sec
          and 'dhd -i "$_w" ioctl_timeout' in sec and sec.find('if [ "${DST:-0}" -gt 0 ]; then') < sec.find('dhd -i "$_w" ioctl_timeout')
          and "GET STA INFO failed" in sec and "resumed on timeout" in sec)
    check("diag: blocked-task stacks are asked from the kernel only while a task is blocked, and read after a marker line",
          'if [ "${DST:-0}" -gt 0 ] && [ -w /proc/sysrq-trigger ]; then' in sec and "echo w > /proc/sysrq-trigger" in sec
          and 'echo "$_sm" > /dev/kmsg' in sec and "index($0, m) { p = 1; next } p" in sec and "tail -200" in sec)
    check("diag: the new section uses no stat applet and no apostrophe inside its awk program", "stat -c" not in sec and "'index($0, m) { p = 1; next } p'" in sec)
    if SH:
        r = subprocess.run([SH, "-n", os.path.join(SRC, "others", "reaper_diag")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        check("diag: the script parses (sh -n)", r.returncode == 0, r.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed: the vendor code's open doors are closed from open code (netlink families, tokens, second "
      "password, portal answer, crash helper, gateway setting) and the diagnostics report carries section 12d")
