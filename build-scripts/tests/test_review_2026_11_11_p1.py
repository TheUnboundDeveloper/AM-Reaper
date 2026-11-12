#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-11, remediation phase 1: the small fixes, and the Wireless stability switches.

WHY THIS EXISTS. The 2026-11-11 code review listed about sixty items. Phase 1 fixes the small ones in open code:
restart requests rc sent to itself and then dropped (firewall rules engine, firewall log path), the channel picker's
client called with no time limit, a shell string built from the DDNS account name (3006.102.8 line), 0777 folders
made by rc, a settings import that replaced the Gatekeeper device list, a reused connection slot in rednsd, and a
set of one-line bugs. It also adds three switches on the Tweaks page (Wireless stability), all OFF by default:
the Wi-Fi driver's wait for a radio (reaper_dhd_ioto), the roaming assistant's disconnect on a node's report
(disable_exap) and ASUS's background-DFS rule (reaper_bgdfs_stock; its #ifdef was misspelled and never compiled).

WHAT IT DOES. Pins each fix in the source, and where a fix is logic, cuts the real function out of the tree,
compiles it on the host with small stand-ins and runs it: the Gatekeeper merge, the DFS switch (on, off, restore),
the timeout switch (range, radios, teardown, watchdog), the JSON skipper, the portal secret. Checks the page, the
defaults, the backup rows and that every language pack carries the ten new texts on the same line.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "reaper_fw.c")):
    skip("no router source tree with rc/reaper_fw.c (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))

def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

def fn(text, head):
    """the body of the function whose definition line starts with `head` (to the first line that is just '}')"""
    i = text.find(head)
    if i < 0:
        return ""
    j = text.find("\n}\n", i)
    return text[i:j + 3] if j > 0 else ""

CC = shutil.which("gcc") or shutil.which("cc")
def run_c(name, src, args=(), timeout=10):
    """compile + run; returns stdout, or None when it did not compile / timed out (reported as a failure)"""
    with tempfile.TemporaryDirectory() as td:
        c, x = os.path.join(td, "t.c"), os.path.join(td, "t")
        open(c, "w").write(src)
        r = subprocess.run([CC, "-Wall", "-Wno-unused-function", "-o", x, c], capture_output=True, text=True)
        if r.returncode != 0:
            check(name + ": compiles on the host", False, r.stderr); return None
        try:
            return subprocess.run([x] + list(args), capture_output=True, text=True, timeout=timeout).stdout
        except subprocess.TimeoutExpired:
            check(name + ": returns", False, "timeout"); return None

FOREACH = r'''
#define foreach(word, wordlist, next) \
	for (next = &wordlist[strspn(wordlist, " ")], strncpy(word, next, sizeof(word)), word[strcspn(word, " ")] = '\0', \
	     word[sizeof(word) - 1] = '\0', next = strchr(next, ' '); strlen(word); \
	     next = next ? &next[strspn(next, " ")] : "", strncpy(word, next, sizeof(word)), word[strcspn(word, " ")] = '\0', \
	     word[sizeof(word) - 1] = '\0', next = strchr(next, ' '))
'''
STRL = r'''
static size_t strlcat(char *d, const char *s, size_t n){ size_t l = strlen(d), m = strlen(s); if (l < n) { size_t c = (m < n - l - 1) ? m : n - l - 1; memcpy(d + l, s, c); d[l + c] = 0; } return l + m; }
static size_t strlcpy(char *d, const char *s, size_t n){ size_t m = strlen(s); if (n) { size_t c = m < n - 1 ? m : n - 1; memcpy(d, s, c); d[c] = 0; } return m; }
'''

# ---------------------------------------------------------------- C-1, C-2: rc does not send itself a restart
fw = rd("rc", "reaper_fw.c")
b = fn(fw, "static void rfw_sync_dnsmasq(")
check("C-1: in rc, the rules engine restarts dnsmasq directly", "getpid() == 1" in b and "stop_dnsmasq(" in b and "start_dnsmasq(" in b)
check("C-1: the restart request is kept for other processes only",
      re.search(r"\}\s*else\s*\n\s*notify_rc\(\"restart_dnsmasq\"\);", b) is not None, b[-300:])
fl = rd("rc", "reaper_fwlog.c")
b = fn(fl, "static void rfl_set_path(")
check("C-2: in rc, a log-path change rebuilds the firewall directly",
      "getpid() == 1" in b and "start_default_filter(0);" in b and "start_firewall(wan_primary_ifunit(), 0);" in b)
check("C-2: the restart request is kept for other processes only",
      re.search(r"\}\s*else\s*\n\s*notify_rc\(\"restart_firewall\"\);", b) is not None)
w = fn(fl, "void reaper_fwlog_watch(")
rest = fl.replace(w, "").replace(b, "")
check("C-2: no other restart request in the collector's rc code (the watchdog's own two are in its function)",
      "notify_rc(" not in rest and w.count('notify_rc("restart_rflog")') == 2, rest.count("notify_rc("))

# ---------------------------------------------------------------- D-7: the picker's client has a time limit
bf = rd("rc", "reaper_bwfloor.c")
check("D-7: reaper_bwfloor no longer waits on acs_cli2 for ever", 'eval("acs_cli2"' not in bf and bf.count("_eval(av, NULL, 10, NULL);") == 2)
rcc = rd("rc", "rc.c")
i = rcc.find('snprintf(cmd, sizeof(cmd), "acs_cli2 -i %s acs_restart", word);')
seg = rcc[i:i + 600] if i > 0 else ""
check("D-7: rc's own acs_cli2 call is bounded and runs no shell",
      "_eval(reaper_av, NULL, 10, NULL);" in seg and "safe_do_system(" not in seg and "system(cmd)" not in seg, seg[:300])

# ---------------------------------------------------------------- D-8, B-P1..3: the 102.8 carries (true on both lines)
dd = rd("inadyn", "src", "ddns.c")
b = fn(dd, "static int shell_transaction(")
check("D-8: inadyn runs the command alone - no account name in the shell string",
      "INADYN_USER" not in b and 'snprintf(ctx->request_buf, ctx->request_buflen, "%s", cmd);' in b)
wa = rd("libwebapi", "webapi.c")
m = re.search(r"static const char \*const reaper_one_line\[\] = \{(.*?)\};", wa, re.S)
check("D-8: the DDNS account name and password are one-line settings in the gate",
      m is not None and '"ddns_username_x"' in m.group(1) and '"ddns_passwd_x"' in m.group(1))
for f in ("upload_server_ovpn_cert_cgi", "upload_server_ipsec_cert_cgi"):
    b = wa[wa.find("int %s()" % f):]
    b = b[:b.find("\nint ", 10)] if b.find("\nint ", 10) > 0 else b
    check("B-P1: %s stages the archive, lists it and refuses links and traversal" % f,
          "mkstemp" in b and "symlink/hardlink" in b and "grep -qE '(^| )/|" in b, len(b))
check("B-P2: the VPN status text is never the format string", "websWrite(wp, result)" not in rd("httpd", "sysinfo.c"))
hc = rd("httpd", "httpd.c")
check("B-P3: the file checks use the request path without its query string",
      "reaper_gone_page(file)" not in hc and "!check_if_file_exist(file)" not in hc)

# ---------------------------------------------------------------- C-3: no world-writable folders from rc
sv = rd("rc", "services.c")
# the shared helper is NOT changed: 45 callers, USB share folders among them (decision of 2026-11-06,
# test_review_wwt_2026_11_06.py). The folders a root daemon reads from are fixed where they are made.
check("C-3: mkdir_if_none keeps its mode; the fix is per folder", "mkdir -m 0777 -p '%s'" in sv and "mkdir -m 0755 -p" not in sv)
tm = rd("rc", "timemachine.c")
check("C-3: Time Machine's folders are root's own, and afp.conf is never written through a link",
      "reaper_secure_dir(AFP_LOCK_PATH, 0755);" in tm and "reaper_secure_dir(AFP_CONFIG_PATH, 0755);" in tm
      and "mkdir_if_none(AFP_CONFIG_PATH)" not in tm and "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0644" in tm)

# ---------------------------------------------------------------- D-2 and the rednsd one-liners
rn = rd("rednsd", "rednsd.c")
check("D-2: each poll entry remembers the connection it was taken for",
      "unsigned pgen[MAX_LISTEN + 2 + MAX_CONN + MAX_TCPRE];" in rn and "pgen[np] = c->gen; map[np++] = i;" in rn)
check("D-2: a slot that changed hands in this pass is skipped",
      re.search(r"struct conn \*c = &conns\[map\[i\]\];\s*\n\s*if \(c->gen != pgen\[i\]\)\s*\n\s*continue;", rn) is not None)
check("rednsd: STATUS_MAX is defined once", len(re.findall(r"^#define STATUS_MAX\b", rn, re.M)) == 1)
check("rednsd: the write buffer holds the longest answer with its length prefix",
      re.search(r"#define WBUF_MAX\s+\(64 \* 1024 \+ 2\)", rn) is not None and re.search(r"#define RMAX\s+65535", rn) is not None)
ed = rd("rc", "encdns.c")
check("rednsd.conf is written beside the file and renamed over it",
      'fopen(RED_CONF ".new", "w")' in ed and 'rename(RED_CONF ".new", RED_CONF) == 0' in ed)
sh = rd("rednsd", "encdns.sh")
check("encdns.sh: a missing cached list counts as 0, with no error text",
      '${cnt:-0}' in sh and '|| echo 0)" > "$D/doh.state"' not in sh)
for shell in ("sh", "dash", "busybox"):
    if shutil.which(shell):
        cmd = [shell, "ash", "-n"] if shell == "busybox" else [shell, "-n"]
        r = subprocess.run(cmd + [os.path.join(SRC, "rednsd", "encdns.sh")], capture_output=True, text=True)
        check("encdns.sh parses (%s -n)" % " ".join(cmd[:-1]), r.returncode == 0, r.stderr)

# ---------------------------------------------------------------- B-6: the Gatekeeper list merge, run for real
wc = rd("httpd", "web.c")
check("B-6: the settings import merges", "gk_rl_merge(v) >= 0" in wc and "gk_rl_set(v) == 0) { nlists++; touch_gk" not in wc)
m_valid = re.search(r"^static int\s*\n?gk_valid_mac\(const char \*m\)\n\{.*?^\}\n", wc, re.S | re.M) or re.search(r"^static int gk_valid_mac\(const char \*m\)\s*\{.*?^\}\n", wc, re.S | re.M)
m_find = re.search(r"^static int\ngk_rl_find\(.*?^\}\n", wc, re.S | re.M)
m_merge = re.search(r"^static int\ngk_rl_merge\(const char \*in\)\n\{.*?^\}\n", wc, re.S | re.M)
check("B-6: the merge and its two helpers can be cut out", bool(m_valid and m_find and m_merge))
if CC and m_valid and m_find and m_merge:
    prog = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/file.h>
''' + STRL + r'''
static char store[8192]; static int set_fail;
static char *gk_rl_get(void){ return store; }
static int gk_rl_set(const char *v){ if (set_fail) return -1; snprintf(store, sizeof(store), "%s", v); return 0; }
static void logmessage(const char *a, const char *f, ...){ (void)a; (void)f; }
''' + m_valid.group(0) + m_find.group(0) + m_merge.group(0) + r'''
int main(int argc, char **argv){
  int n;
  snprintf(store, sizeof(store), "%s", argv[1]);
  set_fail = argc > 3;
  n = gk_rl_merge(argv[2]);
  printf("%d|%s", n, store);
  return 0; }
'''
    A, Bm, Cm, Dm = "AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02", "AA:BB:CC:DD:EE:03", "AA:BB:CC:DD:EE:04"
    have = "<%s>1>0<%s>2>0" % (A, Bm)
    out = run_c("B-6", prog, [have, "<%s>0>0<%s>3>1900000000" % (Bm, Cm)])
    check("B-6: a device on the box that the file does not name keeps its row; a named one takes the file's row; a new one is added",
          out == "2|<%s>1>0<%s>0>0<%s>3>1900000000" % (A, Bm, Cm), out)
    out = run_c("B-6", prog, [have, "<%s>9>0<ZZ:BB:CC:DD:EE:03>1>0<%s>1>-5<%s>1>0<%s>2>0<%s>" % (Bm, Cm, Dm, Dm, A)])
    check("B-6: a bad state, a bad address, a negative expiry and a row with no state are not taken (the box's rows stay); a device named twice keeps its first row",
          out == "1|<%s>1>0<%s>2>0<%s>1>0" % (A, Bm, Dm), out)
    out = run_c("B-6", prog, ["", "<%s>1>0" % A])
    check("B-6: an import into an empty list", out == "1|<%s>1>0" % A, out)
    out = run_c("B-6", prog, [have, "<%s>1>0" % Cm, "fail"])
    check("B-6: a failed write is reported and the list is left as it was", out == "-1|" + have, out)

# ---------------------------------------------------------------- small pins
check("login lock: a source lock's time left is counted from MAX_LOGIN_BLOCK_TIME",
      "MAX_LOGIN_BLOCK_TIME - reaper_ll_rem" in wc and "login_dt = MAX_LOGIN_BLOCK_TIME - rem;" in hc)
check("AiMesh node lookups never read past the shared table",
      wc.count("i < tbl->count && i < CFG_CLIENT_NUM; i++)") >= 3 and "for (i = 1; i < tbl->count; i++)" not in wc)
check("a bookmark of the unshipped Wi-Fi Pro page bounces",
      '{ "reaper_wifipro.asp", "Reaper_WiFiSettings.asp", 0 }' in rd("httpd", "reaper_inject.c"))
wg = rd("wallguard", "wallguardc.c")
check("Wallguard Advanced: the regex ends at the last \"/$\" when text follows the last slash",
      'strstr(q, "/$")' in wg and wg.find('strstr(q, "/$")') < wg.find('ADV_SKIP("text after a regex")'))
check("the dead Samba guard in rc/usb.c is spelled as the build spells it",
      "#ifdef RTCONFIG_SAMBA_SRV" not in rd("rc", "usb.c"))

# ---------------------------------------------------------------- js_skip: "[}" returns, run for real
mc = rd("rc", "reaper_meshchan.c")
i, j = mc.find("struct jp"), mc.find("static int js_skip(")
k = mc.find("\n}\n", j)
if CC and 0 <= i < j < k:
    out = run_c("js_skip", "#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n#include <ctype.h>\n" + mc[i:k + 3] + r'''
int main(int argc, char **argv){ int i; for (i = 1; i < argc; i++) { struct jp j; memset(&j, 0, sizeof(j)); j.p = argv[i]; printf("%d", js_skip(&j, 0) < 0 ? 0 : 1); } return 0; }
''', ["[}", "{]", '[1,"a",{"b":[2,3]}]', '{"a":1}', "[1,2"], timeout=5)
    check("AiMesh channel fit: the JSON skipper refuses a wrong closing bracket and still reads good input (it used to spin on \"[}\")",
          out == "00110", out)
else:
    check("AiMesh channel fit: the JSON reader can be cut out", not CC, (i, j, k))

# ---------------------------------------------------------------- the portal secret is never NULL, run for real
nc = rd("lighttpd-1.4.39", "src", "nvram_control.c")
b = fn(nc, "char *nvram_get_uamsecret(")
if CC and b:
    out = run_c("uamsecret", r'''
#include <stdio.h>
#include <string.h>
static const char *v_net, *v_chilli, *v_cp;
static char *nvram_get(const char *k){ return (char *)(!strcmp(k, "chilli_net") ? v_net : !strcmp(k, "chilli_uamsecret") ? v_chilli : !strcmp(k, "cp_uamsecret") ? v_cp : NULL); }
''' + b + r'''
int main(void){
  printf("[%s]", nvram_get_uamsecret("192.0.2.0/24"));                       /* nothing set */
  v_cp = "cpsec"; printf("[%s]", nvram_get_uamsecret("192.0.2.0/24"));
  v_net = "192.0.2.0/24"; printf("[%s]", nvram_get_uamsecret("192.0.2.0/24")); /* chilli net, its secret unset */
  v_chilli = "chsec"; printf("[%s]", nvram_get_uamsecret("192.0.2.0/24"));
  printf("[%s]", nvram_get_uamsecret(NULL));
  return 0; }
''')
    check("captive portal: a missing secret reads as an empty string, never NULL", out == "[][cpsec][][chsec][cpsec]", out)
else:
    check("captive portal: nvram_get_uamsecret can be cut out", not CC)

# ---------------------------------------------------------------- C-5: ASUS's background-DFS rule behind a switch
ib = rd("rc", "sysdeps", "init-broadcom.c")
check("C-5: the misspelled guard is gone", re.search(r"^#\s*if\w*\s+.*RTCONIFG", ib, re.M) is None)
m = re.search(r"#ifdef RTCONFIG_HND_ROUTER_AX\n\t\t/\* review 2026-11-11 \(C-5\).*?\n(\t\t\{\n.*?\n\t\t\}\n)#endif\n", ib, re.S)
check("C-5: ASUS's rule sits under the correctly spelled guard, behind reaper_bgdfs_stock", m is not None and "reaper_bgdfs_stock" in m.group(1))
if CC and m:
    prog = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static struct { char k[64], v[64]; int set; } nv[32];
static int slot(const char *k, int mk){ int i; for (i = 0; i < 32; i++) if (nv[i].set && !strcmp(nv[i].k, k)) return i; if (!mk) return -1; for (i = 0; i < 32; i++) if (!nv[i].set) { nv[i].set = 1; snprintf(nv[i].k, 64, "%s", k); nv[i].v[0] = 0; return i; } return -1; }
static char *nvram_get(const char *k){ int i = slot(k, 0); return i < 0 ? NULL : nv[i].v; }
static char *nvram_safe_get(const char *k){ char *v = nvram_get(k); return v ? v : ""; }
static void nvram_set(const char *k, const char *v){ snprintf(nv[slot(k, 1)].v, 64, "%s", v); }
static void nvram_set_int(const char *k, int v){ char b[16]; snprintf(b, sizeof(b), "%d", v); nvram_set(k, b); }
static void nvram_unset(const char *k){ int i = slot(k, 0); if (i >= 0) nv[i].set = 0; }
static int nvram_match(const char *k, const char *v){ return !strcmp(nvram_safe_get(k), v); }
static void rule(const char *prefix)
''' + m.group(1) + r'''
static void show(const char *t){ char *e = nvram_get("wl1_acs_bgdfs_enab"), *a = nvram_get("wl1_acs_bgdfs_ahead"), *x = nvram_get("wl1_acs_ignore_txfail"), *s = nvram_get("wl1_reaper_bgdfs_sv");
  printf("%s:%s,%s,%s,%s;", t, e ? e : "-", a ? a : "-", x ? x : "-", s ? s : "-"); }
int main(void){
  nvram_set("wl1_acs_bgdfs_enab", "1"); nvram_set("wl1_acs_bgdfs_ahead", "1");      /* ignore_txfail not set */
  rule("wl1_"); show("off");
  nvram_set("reaper_bgdfs_stock", "1"); rule("wl1_"); show("on");
  nvram_set("wl1_acs_bgdfs_enab", "1"); rule("wl1_"); show("on2");                 /* something set it back: applied again, the kept values stay */
  nvram_set("acsd_ctrl", "1"); rule("wl1_"); show("ctrl");                         /* ASUS's own exception: the radio gets its values back */
  nvram_unset("acsd_ctrl"); rule("wl1_"); show("on3");
  nvram_set("reaper_bgdfs_stock", "0"); rule("wl1_"); show("off2");
  rule("wl1_"); show("off3");
  return 0; }
'''
    out = run_c("C-5", prog)
    check("C-5: switch off = the radio is left alone; on = ASUS's values, what the radio had kept once; off again (or acsd_ctrl=1) = put back, an unset key unset again",
          out == "off:1,1,-,-;on:0,0,1,1 1 -1;on2:0,0,1,1 1 -1;ctrl:1,1,-,-;on3:0,0,1,1 1 -1;off2:1,1,-,-;off3:1,1,-,-;", out)

# ---------------------------------------------------------------- A-C1 gate: the radio call timeout switch, run for real
i, j = sv.find("#define REAPER_DHD_IOTO_STOCK"), sv.find("reaper_dhd_ioto_watch(void)\n{")
k = sv.find("\n}\n", j)
check("timeout switch: the rc code can be cut out", 0 < i < j < k)
if CC and 0 < i < j < k:
    prog = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
''' + STRL + FOREACH + r'''
static int nv_ioto, mark; static char calls[512];
static int nvram_get_int(const char *k){ (void)k; return nv_ioto; }
static char *nvram_safe_get(const char *k){ (void)k; return "wl0 wl1 wl2"; }
static int dhd_probe(char *n){ return strcmp(n, "wl1") ? 0 : 1; }               /* wl1 runs on the other driver */
static int dhd_iovar_setint(char *n, char *v, int ms){ char b[64]; snprintf(b, sizeof(b), "%s.%s=%d ", n, v, ms); strcat(calls, b); return 0; }
static int f_exists(const char *p){ (void)p; return mark; }
static int f_write_string(const char *p, const char *s, unsigned f, unsigned m){ (void)p; (void)s; (void)f; (void)m; mark = 1; return 0; }
static void logmessage(const char *a, const char *f, ...){ (void)a; (void)f; }
#define unlink(p) (mark = 0)
''' + sv[i:k + 3] + r'''
static void show(const char *t){ printf("%s:%s|%d;", t, calls, mark); calls[0] = 0; }
int main(void){
  int i;
  reaper_dhd_ioto_apply(); show("off");
  nv_ioto = 1999; reaper_dhd_ioto_apply(); show("low");
  nv_ioto = 5001; reaper_dhd_ioto_apply(); show("high");
  nv_ioto = 5000; reaper_dhd_ioto_apply(); show("stock");
  nv_ioto = 3000; reaper_dhd_ioto_apply(); show("on");
  reaper_dhd_ioto_stock(); show("teardown");
  reaper_dhd_ioto_stock(); show("teardown2");
  for (i = 0; i < 300; i++) reaper_dhd_ioto_watch(); show("watch-down");
  reaper_dhd_ioto_apply(); show("up");
  for (i = 0; i < 299; i++) reaper_dhd_ioto_watch(); show("watch-299");
  reaper_dhd_ioto_watch(); show("watch-300");
  nv_ioto = 0; reaper_dhd_ioto_apply(); show("switched-off");
  reaper_dhd_ioto_apply(); show("off-again");
  return 0; }
'''
    out = run_c("timeout switch", prog)
    S3, S5 = "wl0.ioctl_timeout=3000 wl2.ioctl_timeout=3000 ", "wl0.ioctl_timeout=5000 wl2.ioctl_timeout=5000 "
    check("timeout switch: off, out of range (below 2000, above 5000) and 5000 itself never touch a radio",
          out is not None and out.startswith("off:|0;low:|0;high:|0;stock:|0;"), out)
    check("timeout switch: on = the value in every radio the dhd driver runs, and only those",
          out is not None and "on:%s|1;" % S3 in out, out)
    check("timeout switch: a wireless teardown runs at the driver's own 5000, once; the watchdog stays out until the radios are up",
          out is not None and "teardown:%s|0;teardown2:|0;watch-down:|0;up:%s|1;" % (S5, S3) in out, out)
    check("timeout switch: the watchdog sets the value again every 300 s, not sooner",
          out is not None and "watch-299:|1;watch-300:%s|1;" % S3 in out, out)
    check("timeout switch: switched off = the driver's own 5000 back in the radios, once",
          out is not None and out.endswith("switched-off:%s|0;off-again:|0;" % S5), out)
b = fn(sv, "reaper_wl_readers_stop(void)\n{")
check("timeout switch: the driver's own wait is restored first thing in the wireless teardown",
      0 < b.find("reaper_dhd_ioto_stock();") < b.find("stop_rpunctd();"))
b = fn(sv, "reaper_wl_readers_start(void)\n{")
check("timeout switch: set again when the radios are up, at boot, on the page's Apply, and by the watchdog",
      "reaper_dhd_ioto_apply();" in b and 'reaper_dhd_ioto_apply();	/* review 2026-11-11 (A-C1) the "Radio call timeout" switch' in sv
      and re.search(r'strcmp\(script, "reaper_wltune"\) == 0\).*?\n\s*\{\n\s*if\(action & RC_SERVICE_START\) reaper_dhd_ioto_apply\(\);', sv) is not None
      and "reaper_dhd_ioto_watch();" in rd("rc", "watchdog.c"))

# ---------------------------------------------------------------- defaults, backup rows, the page, the language packs
df = rd("shared", "defaults.c")
for key in ("reaper_bgdfs_stock", "reaper_dhd_ioto"):
    check("defaults: %s is OFF (0)" % key, re.search(r'\{ "%s", "0", ' % key, df) is not None)
check("defaults: disable_exap has a row (httpd saves only settings that have one) with no value of its own = the stock behaviour",
      re.search(r'\{ "disable_exap", "", ', df) is not None)
m = re.search(r"rcfg_flags\[\] = \{(.*?)\n\};", wc, re.S)
check("a settings backup carries the three switches",
      m is not None and all('"%s"' % x in m.group(1) for x in ("reaper_bgdfs_stock", "reaper_dhd_ioto", "disable_exap")))
pg = rd("www", "Reaper_Tweaks.asp")
check("Tweaks: the Wireless stability panel has the three switches and the timeout field",
      all(x in pg for x in ('id="p_wlstab"', 'id="t_dhd_ioto"', 'id="i_dhd_ioto"', 'id="t_disable_exap"', 'id="t_bgdfs_stock"')))
check("Tweaks: the page reads the three settings and treats an empty value as off",
      all('%s: <% nvram_get_js("%s"); %>'.replace("%s", x) in pg for x in ("reaper_dhd_ioto", "disable_exap", "reaper_bgdfs_stock"))
      and "reaper_dhd_ioto: '0', disable_exap: '0', reaper_bgdfs_stock: '0'" in pg)
check("Tweaks: switch off posts 0; the field is prefilled with the recommended 3000 and checked 2000-5000",
      "var IOTO_REC = '3000';" in pg and "chk('t_dhd_ioto') === '1' ? q('i_dhd_ioto').value.trim() : '0'" in pg
      and "rp.v.int(c.reaper_dhd_ioto, 2000, 5000)" in pg)
check("Tweaks: each switch takes the lightest action (timeout live, node reports saved only, DFS rule restarts Wi-Fi)",
      "if (has('reaper_dhd_ioto')) S.push('restart_reaper_wltune');" in pg and "if (has('reaper_bgdfs_stock')) S.push('restart_wireless');" in pg
      and "has('disable_exap')" not in pg)
check("Tweaks: the page is plain ASCII", all(ord(c) < 128 for c in pg), [c for c in pg if ord(c) >= 128][:5])
toks = ["RTWK_%d" % n for n in range(32, 42)]
check("Tweaks: every new text is used on the page", all("<#%s#>" % t in pg for t in toks), [t for t in toks if "<#%s#>" % t not in pg])
wdir = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(wdir) if re.fullmatch(r"[A-Z]{2}\.dict", f))
pos, missing, same_as_en = set(), [], []
en = {}
for f in ["EN.dict"] + [p for p in packs if p != "EN.dict"]:
    lines = open(os.path.join(wdir, f), encoding="utf-8", errors="surrogateescape").read().split("\n")
    d = {}
    for n, l in enumerate(lines):
        mm = re.match(r"(RTWK_(?:3[2-9]|4[01]))=(.*)$", l)
        if mm:
            d[mm.group(1)] = (n, mm.group(2))
    if f == "EN.dict":
        en = d
    if sorted(d) != sorted(toks) or any(not v[1].strip() or "`" in v[1] or "${" in v[1] for v in d.values()):
        missing.append(f); continue
    pos.add(tuple(d[t][0] for t in toks))
    if f != "EN.dict" and sum(1 for t in toks if d[t][1] == en.get(t, (0, ""))[1]) > 2:
        same_as_en.append(f)
check("language packs: all %d carry the ten new texts, usable in a script string" % len(packs), len(packs) == 25 and not missing, missing)
check("language packs: the ten texts sit on the same lines in every pack (lockstep)", len(pos) == 1, len(pos))
check("language packs: the texts are translated, not English copies", not same_as_en, same_as_en)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nall checks passed")
