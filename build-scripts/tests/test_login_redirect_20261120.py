#!/usr/bin/env python3
"""Login redirect to an address the admin types (item 9, 2026-11-20).

WHY. The Tweaks switch "Redirect the login page to the router domain name" could only send the browser to the stock
name (www.asusrouter.com). The owner asked to type the name he uses for his router (his own domain, https, port
8443). The parts are stored apart - reaper_dut_redir_proto / _host / _port (empty host = stock behaviour) - so each
is checked on its own and the name can be masked in a diagnostics report. A value lands in the login page's script
and is compared with Host headers, so its shape is checked in the page AND in httpd, by the same rules.

WHAT IT DOES.
  - shared/reaper_dut_redir.h compiled on the host (-Wall -Wextra -Werror): a table of names (labels 1-63, 57 in all,
    no '-' at a label's end, no IP literal, no empty label) and header / script injection tries (CR, LF, quotes, '@',
    '/', ':', space, '%', '<', NUL-free tails), ports (1-65535, no sign, no leading zero), protocols (http / https).
  - The page copies (Reaper_Tweaks.asp redirHostOk / redirPortOk, Main_Login.asp's inline check) run under node on
    the same table and must agree with the C rules.
  - httpd: the save check in nvram_check, the settings-file check in rcfg_put, the three keys in rcfg_flags, the
    defaults; reaper_host_is_self lifted out of httpd.c and run with stub nvram (the typed name, any case, is this
    router; a bad stored name never is; the stock names still are).
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
HDR = os.path.join(SRC, "shared", "reaper_dut_redir.h") if SRC else ""
if not SRC or not os.path.isfile(HDR):
    print("SKIP: no router tree with shared/reaper_dut_redir.h (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
web, httpd, dfl, tw, lp = rd("httpd/web.c"), rd("httpd/httpd.c"), rd("shared/defaults.c"), rd("www/Reaper_Tweaks.asp"), rd("www/Main_Login.asp")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:900] if detail != "" else ""))

L63 = "a" * 63
HOST_GOOD = ["router", "router.example.com", "Router.Example.COM", "my-router.home.arpa", "a.b", "x1.example", "1router.example",
             "rt-be96u.lan", "a" * 57, "a" * 28 + "." + "b" * 28, "xn--bcher-kva.example", "a1"]
HOST_BAD = ["", "-router.example", "router-.example", "router..example", ".router.example", "router.example.", "a" * 58,
            "192.168.50.1", "10.0.0.1", "1.2.3.4.5", "example.123", "123", "::1", "[fe80::1]", "fe80::1",
            "router.example:8443", "router.example/", "router.example/x", "user@router.example", "router example",
            "router.example\r\nX-Injected: 1", "router.example\n", "router.example\r", 'router".example', "router'.example",
            "router`x.example", "router%0d.example", "<script>.example", "router_x.example", "r\\x.example", "router.example;reboot",
            "router.ex\x7fample", "ro\tuter.example", "r\xc3\xa9seau.example", L63 + ".example"]
PORT_GOOD = ["", "1", "80", "443", "8443", "65535", "8080"]
PORT_BAD = ["0", "00", "080", "65536", "99999", "123456", "-1", "+80", " 80", "80 ", "8a", "8443\r\n", "0x50", "1e3"]
PROTO_GOOD = ["http", "https"]
PROTO_BAD = ["", "HTTP", "Https", "ftp", "https ", "javascript", "https:", "file"]

# ============================================================ pins
check("defaults: proto https, host and port empty (empty host = stock behaviour)",
      '{ "reaper_dut_redir_proto", "https", CKN_STR8,' in dfl and '{ "reaper_dut_redir_host", "", CKN_STR64,' in dfl and '{ "reaper_dut_redir_port", "", CKN_STR8,' in dfl)
check("backups: the three keys travel in the settings file (rcfg_flags, misc) and pass rdr_field_ok on import",
      '{ "misc",   "reaper_dut_redir_proto", 6 }, { "misc",   "reaper_dut_redir_host", 64 },' in web and '{ "misc",   "reaper_dut_redir_port", 6 },' in web
      and 'if (!strncmp(nv, "reaper_dut_redir_", 17) && !rdr_field_ok(nv, v))\n\t\treturn -1;' in web)
ncm = re.search(r"\nint nvram_check\(char \*name, char \*value, struct nvram_tuple \*t, char \*output\)\n\{.*?\n\}\n", web, re.S)
check("httpd: the Tweaks save is checked in nvram_check (a bad value is refused, logged, not stored)",
      ncm is not None and 'if (ret == 0 && !strncmp(name, "reaper_dut_redir_", 17) && !rdr_field_ok(name, value)) {\n\t\tret = 1;' in ncm.group(0)
      and ncm.group(0).find("rdr_field_ok") < ncm.group(0).find("if(ret == 1)\n\t\tgoto FINISH;"))
check("httpd: both files include the shared rules", '#include "reaper_dut_redir.h"' in web and '#include "reaper_dut_redir.h"' in httpd)
check("httpd: the Host copy is 64 bytes and the name is capped at 57 (name + \":65535\" fits)",
      "char host_name[64];" in httpd and "#define RDR_HOST_MAX\t57" in rd("shared/reaper_dut_redir.h"))

# ============================================================ C rules
CC = shutil.which("gcc") or shutil.which("cc")
C_RES = None
if CC:
    w = tempfile.mkdtemp(prefix="rdr_")
    try:
        c = os.path.join(w, "t.c")
        open(c, "w").write(r'''#include <stdio.h>
#include <stdlib.h>
#include "reaper_dut_redir.h"
static char *unhex(const char *h) { size_t n = strlen(h) / 2, i; char *o = malloc(n + 1); for (i = 0; i < n; i++) { unsigned v; sscanf(h + 2 * i, "%2x", &v); o[i] = (char)v; } o[n] = 0; return o; }
int main(int argc, char **argv) { int i; for (i = 2; i < argc; i++) { char *v = unhex(argv[i]);
  printf("%d", !strcmp(argv[1], "host") ? rdr_host_ok(v) : !strcmp(argv[1], "port") ? rdr_port_ok(v) : !strcmp(argv[1], "proto") ? rdr_proto_ok(v)
               : rdr_field_ok(argv[1], v)); free(v); } printf("\n"); return 0; }
''')
        exe = os.path.join(w, "t")
        r = subprocess.run([CC, "-Wall", "-Wextra", "-Werror", "-I", os.path.join(SRC, "shared"), "-o", exe, c], capture_output=True, text=True)
        check("C: shared/reaper_dut_redir.h compiles with -Wall -Wextra -Werror", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            def run(kind, vals):
                hx = [v.encode("latin-1").hex() or "" for v in vals]
                return subprocess.run([exe, kind] + hx, capture_output=True, text=True).stdout.strip()
            C_RES = {}
            for kind, good, bad in (("host", HOST_GOOD, HOST_BAD), ("port", PORT_GOOD, PORT_BAD), ("proto", PROTO_GOOD, PROTO_BAD)):
                g, b = run(kind, good), run(kind, bad)
                C_RES[kind] = (g, b)
                check("C: %s - every good value passes, every bad one (injection tries included) is refused" % kind,
                      g == "1" * len(good) and b == "0" * len(bad),
                      ([v for v, x in zip(good, g) if x != "1"], [v for v, x in zip(bad, b) if x != "0"]))
            f = run("reaper_dut_redir_host", ["", "router.example.com", "10.0.0.1"]) + run("reaper_dut_redir_port", ["", "8443", "0"]) \
                + run("reaper_dut_redir_proto", ["https", ""]) + run("reaper_dut_redir_other", ["x"])
            check("C: rdr_field_ok - an empty host / port allowed, an empty protocol and any other name refused", f == "110110" + "10" + "0", f)
    finally:
        shutil.rmtree(w, ignore_errors=True)

    # reaper_host_is_self with stub nvram
    m = re.search(r"\nstatic int reaper_host_is_self\(const char \*h\)\n\{.*?\n\}\n", httpd, re.S)
    check("httpd: reaper_host_is_self lifts", m is not None)
    if m:
        w = tempfile.mkdtemp(prefix="rdrself_")
        try:
            c = os.path.join(w, "s.c")
            open(c, "w").write(r'''#include <stdio.h>
#include <string.h>
#include <strings.h>
#include "reaper_dut_redir.h"
#define DUT_DOMAIN_NAME "www.asusrouter.com"
#define OLD_DUT_DOMAIN_NAME "router.asus.com"
static const char *NVH = "";
static char *nvram_safe_get(const char *k) {
  if (!strcmp(k, "lan_ipaddr")) return "192.168.50.1"; if (!strcmp(k, "lan_hostname")) return "RT-BE96U";
  if (!strcmp(k, "lan_domain")) return "lan"; if (!strcmp(k, "reaper_dut_redir_host")) return (char *)NVH; return ""; }
''' + m.group(0) + r'''
int main(int argc, char **argv) { int i; NVH = argv[1]; for (i = 2; i < argc; i++) printf("%d", reaper_host_is_self(argv[i])); printf("\n"); return 0; }
''')
            exe = os.path.join(w, "s")
            r = subprocess.run([CC, "-Wall", "-I", os.path.join(SRC, "shared"), "-o", exe, c], capture_output=True, text=True)
            check("httpd: reaper_host_is_self compiles with the shared rules", r.returncode == 0, r.stderr[-800:])
            if r.returncode == 0:
                q = ["router.example.com", "ROUTER.example.COM", "router.example.com.evil.example", "evil.example", "192.168.50.1",
                     "www.asusrouter.com", "rt-be96u.lan", "router.example.co", ""]
                a = subprocess.run([exe, "router.example.com"] + q, capture_output=True, text=True).stdout.strip()
                check("httpd: the typed name (any case) is this router; a longer or other name is not; the stock names still are",
                      a == "110011100", a)
                b = subprocess.run([exe, "bad name\r\n"] + ["bad name\r\n", "evil.example"], capture_output=True, text=True).stdout.strip()
                e = subprocess.run([exe, ""] + ["", "evil.example", "192.168.50.1"], capture_output=True, text=True).stdout.strip()
                check("httpd: a stored name that fails the rules (set by hand) is never this router; an empty one adds nothing", b == "00" and e == "001", (b, e))
        finally:
            shutil.rmtree(w, ignore_errors=True)

# ============================================================ the page copies agree with C
def jsfun(src, name):
    i = src.find("function %s(" % name)
    if i < 0: return ""
    j = src.find("{", i); d = 0
    for k in range(j, len(src)):
        if src[k] == "{": d += 1
        elif src[k] == "}":
            d -= 1
            if d == 0: return src[i:k + 1]
    return ""
th, tp = jsfun(tw, "redirHostOk"), jsfun(tw, "redirPortOk")
lb = lp[lp.find("REAPER-DUT-REDIR"):lp.find("var chdom = function()")]
lm = re.search(r"\tok = (h\.length <= 57 &&.*?);\n", lb)
check("pages: the Tweaks checks and the login page's check are there", th and tp and lm, (bool(th), bool(tp), bool(lm)))
NODE = shutil.which("node")
if NODE and th and tp and lm and C_RES:
    prog = th + "\n" + tp + "\nfunction loginOk(h){ h = String(h).toLowerCase(); return !!h && (" + lm.group(1) + "); }\n" + r'''
var T = JSON.parse(process.argv[1]), o = {};
o.th = [T.hg.map(redirHostOk), T.hb.map(redirHostOk)];
o.lh = [T.hg.map(loginOk), T.hb.map(loginOk)];
o.tp = [T.pg.map(redirPortOk), T.pb.map(redirPortOk)];
console.log(JSON.stringify(o));
'''
    r = subprocess.run([NODE, "-e", prog, json.dumps({"hg": HOST_GOOD, "hb": HOST_BAD, "pg": PORT_GOOD[1:], "pb": PORT_BAD})], capture_output=True, text=True)
    try:
        o = json.loads(r.stdout)
    except Exception:
        o = {}
    if o:
        bits = lambda a: "".join("1" if x else "0" for x in a)
        check("node: Tweaks redirHostOk agrees with httpd on every name", bits(o["th"][0]) == C_RES["host"][0] and bits(o["th"][1]) == C_RES["host"][1],
              ([v for v, x in zip(HOST_BAD, o["th"][1]) if x], [v for v, x in zip(HOST_GOOD, o["th"][0]) if not x]))
        check("node: the login page's check agrees with httpd on every name (it lowers the case first)",
              bits(o["lh"][0]) == C_RES["host"][0] and bits(o["lh"][1]) == C_RES["host"][1],
              ([v for v, x in zip(HOST_BAD, o["lh"][1]) if x], [v for v, x in zip(HOST_GOOD, o["lh"][0]) if not x]))
        check("node: Tweaks redirPortOk agrees with httpd on every port", bits(o["tp"][0]) == C_RES["port"][0][1:] and bits(o["tp"][1]) == C_RES["port"][1], o["tp"])
    else:
        check("node: the page checks run", False, r.stderr[-600:])
elif not NODE:
    print("SKIP (node part): no node")

print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
