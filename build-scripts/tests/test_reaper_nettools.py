#!/usr/bin/env python3
"""Network Tools group on the Reaper kit (Reaper-native UI, 2026-10-23): Reaper_Analysis, Reaper_Netstat, Reaper_WOL,
Reaper_SmartConnect, the reaper_net.cgi runner, and the hardening of the two stock command paths.

WHY. The stock Network Tools pages hand the router a CALLER-BUILT command line that runs as root (apply.cgi SystemCmd,
netool.cgi into the rc netool daemon through /bin/sh) behind a charset filter that blocks shell syntax but not extra
options. The Reaper pages send a tool + target to reaper_net.cgi, which validates the target and builds the argv
itself (execvp, no shell, bounded, one job, always ends). The stock paths stay for the stock pages and the ASUS app
(owner) but accept only the stock command shapes. This pins all of that, and runs the validators for real.

WHAT IT DOES. Source checks on the four pages, menu.js, rp.js, reaper_inject.c and web.c; `node --check` on each page
script; with gcc, compiles rnet_host_ok / rnet_mac_ok / reaper_syscmd_shape_ok out of web.c and runs an accept/reject
table (stock forms accepted, option injection refused).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")
www = os.path.join(SRC, "www")
PAGES = ["Reaper_Analysis.asp", "Reaper_Netstat.asp", "Reaper_WOL.asp", "Reaper_SmartConnect.asp"]
if not all(os.path.exists(os.path.join(www, p)) for p in PAGES):
    print("SKIP: Network Tools pages not found"); sys.exit(0)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

en = rd(os.path.join(www, "EN.dict"))
T = {p: rd(os.path.join(www, p)) for p in PAGES}
for p, t in T.items():
    check(p + ": ASCII only", not any(ord(c) > 127 for c in t))
    check(p + ": on the kit (plain rp.css link, rp.js, reaper-native meta) inside the crimson frame",
          '<link rel="stylesheet" href="/reaper/rp.css">' in t and '<script src="/reaper/rp.js"></script>' in t
          and '<meta name="reaper-native" content="1">' in t and '<div class="rframe">' in t)
    js = t[t.rfind("<script>"):]
    check(p + ": one closure, strict, no inline handlers", js.startswith("<script>\n(function(){\n'use strict';") and js.count("<script>") == 1 and "onclick=" not in t)
    toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
    miss = [k for k in toks if ("\n%s=" % k) not in en]
    check(p + ": every dict token exists (%d)" % len(toks), not miss, miss)
    check(p + ": tokens in the script only inside backticks (rule 29)", "<#" not in re.sub(r"`[^`]*`", "", js))
    code = re.sub(r"<!--.*?-->", "", t, flags=re.S)   # the header comments name what the page replaces
    check(p + ": never uses the stock command paths (SystemCmd / netool.cgi / syscmd.sh)",
          "SystemCmd" not in code and "netool.cgi" not in code and "syscmd" not in code)

A, N, W, S = (T[p] for p in PAGES)
for p in ("Reaper_Analysis.asp", "Reaper_Netstat.asp", "Reaper_WOL.asp"):
    # review 2026-10-24 (Q-C2-11): the reaper_net.cgi client is the kit's rp.net; the page passes its own token
    check(p + ": calls reaper_net.cgi with the http_id token", "rp.net(HTTPID, params, cb)" in T[p]
          and "var HTTPID = '<% nvram_get(\"http_id\"); %>';" in T[p])
check("kit: rp.net POSTs to reaper_net.cgi with the page's http_id first in the body",
      "rp.net = function(httpId, params, cb){" in rd(os.path.join(www, "reaper", "rp.js"))
      and "'http_id=' + encodeURIComponent(httpId) + '&' + params" in rd(os.path.join(www, "reaper", "rp.js"))
      and "x.open('POST', '/reaper_net.cgi', true)" in rd(os.path.join(www, "reaper", "rp.js")))
check("Analysis: sends a tool + target, never a command; presets from the kit", "'action=start&target=' + encodeURIComponent(target)" in A and "rp.pingPresets(q('presets'))" in A)
check("Netstat: option bitmask only; NAT view is the Connections page", "'action=start&tool=netstat&opts=' + opts" in N and "Reaper_Conn.asp" in N)
check("WOL: wollist read decoded (char_to_ascii), names stripped of < > and control chars, 1 KB cap, saved with saveNvram",
      "nvram_char_to_ascii(\"\",\"wollist\")" in W and "replace(/[<>\\x00-\\x1f\\x7f]/g, '')" in W and "var MAXB = 1000;" in W
      and "rp.post(document.form, {wollist: serialize()}, 'saveNvram', 1, false)" in W)
check("SmartConnect: capability write clears every capability bit first; load balance bit 6 cleared when off",
      "for (i = 0; i < 4; i++) v &= ~(1 << c[i]);" in S and "sv &= ~(1 << 6);" in S and "CAPBITS = {steer: [11, 10, 3, 2], sta: [15, 14, 3, 2], qual: [11, 10, 2, 1]}" in S)
check("SmartConnect: Restore never touches wlN_txchain; only changed keys posted via applyapp.cgi + restart_wireless; slot-indexed selif mask",
      "_txchain" not in S.replace("never wlN_txchain", "").replace("reset wlN_txchain", "").replace("also reset\n     wlN_txchain", "")
      and "'/applyapp.cgi'" in S and "ch.rc_service = 'restart_wireless'" in S and "m |= 1 << b.bit" in S)

# wiring
menu = rd(os.path.join(www, "reaper", "menu.js")); inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c"))
check("menu: Network Tools tabs point at the Reaper pages",
      all(("T('%s'" % p) in menu for p in PAGES) and not any(s in menu for s in ("Main_Analysis_Content", "Main_Netstat_Content", "Main_WOL_Content", "Advanced_Smart_Connect")))
sup = {"main_analysis_content": "Reaper_Analysis", "main_netstat_content": "Reaper_Netstat", "main_wol_content": "Reaper_WOL", "advanced_smart_connect": "Reaper_SmartConnect"}
check("httpd: SUP redirects the four stock URLs; the pages are native",
      all(('{ "%s.asp", "%s.asp", ' % kv) in inj for kv in sup.items())
      and all(inj.index('\t"%s",' % p) > inj.index("static const char *reaper_native[]") for p in PAGES))
rpjs = rd(os.path.join(www, "reaper", "rp.js"))
check("kit: rp.pingPresets (one preset loader) and rp.cmp", "rp.pingPresets = function(dl){" in rpjs and "rp.cmp = function(type){" in rpjs)

# C: the runner
web = rd(os.path.join(SRC, "httpd", "web.c"))
i0 = web.index("#define RNET_DIR"); i1 = web.index("reaper v2.6.10: Reaper-wide settings export", i0); R = web[i0:i1]
check("reaper_net.cgi registered with do_auth and gated by reaper_gate", '{ "reaper_net.cgi*", "application/json", no_cache_IE7, do_html_post_and_get, do_reaper_net_cgi, do_auth },' in web
      and "why = reaper_gate();" in R)
check("runner: execvp, no shell (no system / popen / sh -c in the runner)", "execvp(j->argv[0], j->argv);" in R and not re.search(r"\b(system|popen|vpopen)\s*\(", R) and "sh -c" not in R)
check("runner: one job (lock), runtime cap kills the tool, output capped, state always ends in DONE",
      "E_BUSY" in R and "kill(c, killed ? SIGKILL : SIGTERM);" in R and "RNET_OUTMAX" in R and 'rnet_state("DONE", code, killed ? 1 : 0, j);' in R)
check("runner: validation before the busy check; nslookup takes a name only", R.index("rnet_build(&rnet_job)") < R.index('"{\\"ok\\":0,\\"error\\":\\"E_BUSY\\"}"')
      and 'rnet_arg(j, "nslookup");\n\t\trnet_arg(j, target);' in R)
check("diag collector and runner share reaper_detach (the diag handler no longer carries its own double fork)",
      "reaper_detach(rdiag_worker, NULL);" in web and "reaper_detach(rnet_worker, &rnet_job);" in web
      and "rdiag_worker();\n\t\t\t\t_exit(0);" not in web)
# C: stock paths hardened
check("apply.cgi SystemCmd: NULL guard (B2), shape check, atoi(NULL) fix (B1), WOL per-port wakes use the validated MAC (B6)",
      "/* reaper 2026-10-23 (B2)" in web and "if (!reaper_syscmd_shape_ok(current_url, system_cmd, wolmac, sizeof(wolmac))) {" in web
      and "wan = u ? get_wan_ifname(atoi(u)) : NULL;" in web and "strlcpy(dstmac, wolmac, sizeof(dstmac));" in web)
check("netool.cgi: targets validated, result reads limited, IPv4-only hosts, no interface override, counts/timeouts capped",
      "else if (rt != REQ_NETSTAT_MODE && rt != REQ_NETSTAT_NAT_MODE && !rnet_host_ok(target, 0)) {" in web and 'interface = "";' in web
      and web.count("if (req_t.response > 10) req_t.response = 10;") == 2 and web.count("if (req_t.hops > 30) req_t.hops = 30;") == 2)
# review 2026-10-24 (Q-B-9): ONE declaration, placed just ahead of the RTCONFIG_NETOOL block (was one inside + one outside)
_decl = "static int rnet_host_ok(const char *s, int fam);\nstatic int rnet_mac_ok(const char *s);\n\n#ifdef RTCONFIG_NETOOL"
check("the validators are declared outside the RTCONFIG_NETOOL block (models without netool still compile)",
      web.count("static int rnet_host_ok(const char *s, int fam);") == 1 and _decl in web)

gcc = shutil.which("gcc")
if gcc:
    def fn(start, end):
        a = web.index(start); return web[a:web.index(end, a)]
    # rnet_mac_ok delegates to the Gatekeeper's gk_valid_mac (review 2026-10-24, Q-B-9): lift that one too
    _g = web.index("static int\ngk_valid_mac(const char *m)")
    code = web[_g:web.index("\n}\n", _g) + 3] + fn("static int reaper_syscmd_shape_ok(", "static int\napply_cgi(") + fn("/* host name (RFC 1123 labels", "/* bounded decimal;")
    harness = r'''#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <arpa/inet.h>
static size_t strlcpy(char *d, const char *s, size_t n){ size_t l = strlen(s); if (n){ size_t k = l >= n ? n - 1 : l; memcpy(d, s, k); d[k] = 0; } return l; }
static int isValid_digit_string(const char *s){ if (!*s) return 0; for (; *s; s++) if (!isdigit((unsigned char)*s)) return 0; return 1; }
static int rnet_host_ok(const char *s, int fam);
static int rnet_mac_ok(const char *s);
''' + code + r'''
static int bad = 0;
static void S(const char *pg, const char *c, int want){ char m[18] = ""; if (reaper_syscmd_shape_ok(pg, c, m, sizeof(m)) != want){ printf("SHAPE %s [%s] != %d\n", pg, c, want); bad++; } }
static void H(const char *h, int fam, int want){ if (rnet_host_ok(h, fam) != want){ printf("HOST [%s]/%d != %d\n", h, fam, want); bad++; } }
static void M(const char *m, int want){ if (rnet_mac_ok(m) != want){ printf("MAC [%s] != %d\n", m, want); bad++; } }
int main(void){
  const char *N = "Main_Netstat_Content.asp", *A = "Main_Analysis_Content.asp", *W = "Main_WOL_Content.asp", *C = "Main_ConnStatus_Content.asp";
  S(N, "netstat -pa", 1); S(N, "netstat -r -n", 1); S(N, "netstat-nat -s 192.168.50.10  -n", 1); S(C, "netstat-nat -L -n", 1);
  S(A, "ping -c 5 www.google.com", 1); S(A, "traceroute 1.1.1.1", 1); S(A, "nslookup example.com", 1); S(W, "ether-wake -i br0 -b AA:BB:CC:DD:EE:FF", 1);
  S(A, "ping -c 5 host -s 65000", 0); S(A, "ping -w 99999 -c 5 host", 0); S(A, "traceroute -i eth0 -m 255 host", 0); S(A, "nslookup name 8.8.8.8", 0);
  S(N, "netstat -pa -e", 0); S(N, "netstat-nat -L -r src -p tcp", 0); S(W, "ether-wake -i br0 -p secret AA:BB:CC:DD:EE:FF", 0); S(W, "ether-wake -i eth0 -b AA:BB:CC:DD:EE:FF", 0);
  S(A, "netstat -pa", 0); S("Other.asp", "ping -c 1 host", 0);
  H("example.com", 0, 1); H("1.1.1.1", 4, 1); H("2001:db8::1", 6, 1); H("2001:db8::1", 4, 0); H("-c", 0, 0); H("a b", 0, 0); H("a;b", 0, 0);
  H("a..b", 0, 0); H("-host.example", 0, 0); H("host-.example", 0, 0); H("", 0, 0);
  M("AA:BB:CC:DD:EE:FF", 1); M("aa:bb:cc:dd:ee:ff", 1); M("AA:BB:CC:DD:EE", 0); M("AA-BB-CC-DD-EE-FF", 0); M("GG:BB:CC:DD:EE:FF", 0);
  printf("%d bad\n", bad); return bad != 0;
}
'''
    d = tempfile.mkdtemp()
    open(os.path.join(d, "t.c"), "w").write(harness)
    r = subprocess.run([gcc, "-std=gnu99", "-Wall", "-Werror", "-o", os.path.join(d, "t"), os.path.join(d, "t.c")], capture_output=True, text=True)
    check("validators + SystemCmd shape check compile cleanly (-Wall -Werror)", r.returncode == 0, r.stderr[-400:])
    if r.returncode == 0:
        r = subprocess.run([os.path.join(d, "t")], capture_output=True, text=True)
        check("accept/reject table: stock forms accepted, option injection refused (%s)" % r.stdout.strip().splitlines()[-1], r.returncode == 0, r.stdout[-500:])
    shutil.rmtree(d, ignore_errors=True)
else:
    print("note: gcc not found - validator run skipped")

node = shutil.which("node")
if node:
    for p, t in T.items():
        s = re.findall(r"<script>(.*?)</script>", t, re.S)[-1]
        s = re.sub(r"<%.*?%>", "0", s); s = re.sub(r"<#[A-Za-z0-9_-]+#>", "X", s)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(s); jp = f.name
        r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
        check(p + ": script parses (node --check)", r.returncode == 0, r.stderr[-300:])
else:
    print("note: node not found - syntax checks skipped")

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + x) for x in fails]; sys.exit(1)
print("\nall checks passed")
