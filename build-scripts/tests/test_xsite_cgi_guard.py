#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every authenticated CGI refuses a cross-site request from a browser.

WHY THIS EXISTS. ASUS bulletin 2026-10-23, CVE-2026-75779: a logged-in admin who opens a
hostile page gets a root command run on the router (CSRF into an OS command injection). The
closed httpd Referer whitelist (mime_referers[] in web_hook.o) covers only 38 CGIs; the other
authenticated CGIs - over a hundred, netool, set_iperf3_cli, wl_apply, set_fw_path, the
create_sdn family among them - ran on the session cookie alone. SameSite=Lax keeps the cookie
off cross-site POSTs but not off a top-level cross-site GET, and do_html_post_and_get reads a
GET query string. httpd.c now refuses, for every authenticated .cgi and every non-app client,
a request the browser marks cross-site (Sec-Fetch-Site) or whose Referer names another host,
unless that host is the router under another of its own names. One stock cross-device flow is
kept: the AiMesh node wizard's GET to the CAP's cfg_onboarding.cgi (no re_mac in the query).

Review 2026-10-24 (S-B-1, S-B-2): over plain HTTP a browser sends NEITHER header to a private
address, so "no header passes" left the HTTP listener (the shipped default serves both) open;
the guard now treats a header-less request from a browser (Mozilla/ User-Agent) on the plain-HTTP
listener as cross-site, curl and HTTPS unchanged. And the onboarding exemption read the raw query
text, so a percent-encoded key (%72e_mac) slipped past it while init_cgi() decoded it; it now
decides on the query decoded the same way.

WHAT IT DOES. Compiles the helpers out of httpd/httpd.c on the host with stubbed nvram (plus
cgi.c's unescape, the decoder the exemption must mirror), drives them through browser scenarios
(same-origin, cross-site with and without a Referer, curl, old browsers, plain HTTP vs HTTPS,
the router's own names, ports, IPv6 literals, the AiMesh exemption and its encoded bypasses, log
rate limit and sanitising), and checks statically that the guard sits in the authenticated
branch before auth_check(), skips fromapp, answers 403 after draining a POST body, is handed the
User-Agent and the listener, and that Sec-Fetch-Site is parsed.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
HC = os.path.join(SRC, "httpd", "httpd.c")
if not SRC or not os.path.isfile(HC):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

hc = open(HC, encoding="utf-8", errors="surrogateescape").read()
cg = open(os.path.join(SRC, "httpd", "cgi.c"), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

a = hc.find("static void reaper_hostpart(const char *s, char *out, size_t outsz)")
b = hc.find("static void\nhandle_request(void)")
if a < 0 or b < 0 or b < a:
    print("FAIL guard helpers not found in httpd.c"); sys.exit(1)
helpers = hc[a:b]

# ---- static wiring
hr = hc[b:]
hr = hr[:hr.find("\n}\n")]
g = hr.find("reaper_xsite_cgi_refused(url, file, method, sec_fetch_site, useragent, do_ssl)")
check("handle_request calls the guard with the User-Agent and the listener (review S-B-1)", g >= 0)
ua = cg.find("void\nunescape(char *s, size_t len)")
ub = cg.find("\n}\n", ua)
check("cgi.c's unescape() found (the exemption must decode as init_cgi does)", ua >= 0 and ub > ua)
unescape_src = cg[ua:ub + 3] if ua >= 0 and ub > ua else "void unescape(char *s, size_t len) { (void)s; (void)len; }\n"
check("the exemption decides on the decoded query, never the raw text (review S-B-2)",
      "unescape(q, sizeof(q));" in helpers and 'reaper_query_has(file, "re_mac")' in helpers and 'strstr(file, "re_mac")' not in helpers)
check("the guard skips the ASUS app (fromapp)", "if (!fromapp && reaper_xsite_cgi_refused(" in hr)
auth = hr.find("auth_result = auth_check(url, file, cookies, fromapp, &add_try);")
ref = hr.find("referer_result = referer_check(referer, fromapp);")
check("the guard runs in the authenticated branch, before the stock referer_check() and auth_check()",
      0 <= g < ref < auth and hr.rfind("if (handler->auth) {", 0, g) >= 0)
blk = hr[g:hr.find("return;", g) + 7]
check("a refusal drains a POST body and answers a bare 403",
      "fgetc(conn_fp)" in blk and 'send_error( 403, "Forbidden", (char*) 0, "Cross-site request refused." );' in blk)
check("Sec-Fetch-Site is parsed into a request-local buffer, reset per request",
      'char sec_fetch_site[16] = {0};' in hr and 'strncasecmp( cur, "Sec-Fetch-Site:", 15 ) == 0' in hr
      and "strlcpy(sec_fetch_site, cp, sizeof(sec_fetch_site));" in hr)
check("referer_url is still reset per request (the guard reads it)", "referer_url[0] = '\\0';" in hr)
hj = os.path.join(SRC, "www", "sysdep", "FUNCTION", "QIS_V3", "mobile", "js", "handler.js")
if os.path.isfile(hj):
    check("the AiMesh node wizard's cross-device navigation is still the GET the exemption is cut for",
          '"http://<#Web_DOMAIN_NAME#>/cfg_onboarding.cgi?flag=AMesh&id=" +' in open(hj, encoding="utf-8", errors="replace").read())

harness = r'''
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#define DUT_DOMAIN_NAME "www.asusrouter.com"
#define OLD_DUT_DOMAIN_NAME "router.asus.com"
static char referer_url[128], host_name[64];
static const char *nv_ip = "192.168.50.1", *nv_hn = "RT-BE96U-1234", *nv_dom = "lan";
static const char *nvram_safe_get(const char *k)
{
	if (!strcmp(k, "lan_ipaddr")) return nv_ip;
	if (!strcmp(k, "lan_hostname")) return nv_hn;
	if (!strcmp(k, "lan_domain")) return nv_dom;
	return "";
}
static long now_t = 1000;
static long uptime(void) { return now_t; }
static int nlog;
static char lastlog[256];
static void logmessage(const char *tag, const char *fmt, ...)
{
	va_list ap;
	(void)tag;
	va_start(ap, fmt); vsnprintf(lastlog, sizeof(lastlog), fmt, ap); va_end(ap);
	nlog++;
}
''' + unescape_src + helpers + r'''
#define MOZ "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0"
static int run(const char *url, const char *file, const char *method, const char *sfs, const char *host, const char *ref, const char *ua, int tls)
{
	snprintf(host_name, sizeof(host_name), "%s", host);
	snprintf(referer_url, sizeof(referer_url), "%s", ref);
	now_t += 100;	/* keep every case outside the log window */
	return reaper_xsite_cgi_refused(url, file, method, sfs, ua, tls);
}
/* C = a browser on the HTTPS listener (the rules of 2026-10-23); CX names the User-Agent and the listener */
#define C(tag, u, f, m, s, h, r) printf("%s %d\n", tag, run(u, f, m, s, h, r, MOZ, 1))
#define CX(tag, ...) printf("%s %d\n", tag, run(__VA_ARGS__))
int main(void)
{
	const char *L = "192.168.50.1";
	char longq[700];
	memset(longq, 'a', sizeof(longq) - 1); longq[sizeof(longq) - 1] = 0;
	memcpy(longq, "cfg_onboarding.cgi?flag=AMesh&id=", 33);
	C("same_origin_xhr",      "netool.cgi", "netool.cgi", "post", "same-origin", L, "http://192.168.50.1/Reaper_NetTools.asp\r\n");
	C("xsite_foreign_ref",    "netool.cgi", "netool.cgi?x=1", "get", "cross-site", L, "https://evil.example/a.html\r\n");
	C("xsite_no_ref",         "set_iperf3_cli.cgi", "set_iperf3_cli.cgi?x=1", "get", "cross-site", L, "");
	CX("curl_no_headers",     "netool.cgi", "netool.cgi", "post", "", L, "", "curl/8.4.0", 0);
	C("typed_url_none",       "netool.cgi", "netool.cgi", "get", "none", L, "");
	/* review 2026-10-24 S-B-1: the plain-HTTP listener */
	CX("http_browser_no_headers",      "netool.cgi", "netool.cgi?x=1", "get", "", L, "", MOZ, 0);
	CX("http_browser_no_headers_post", "wl_apply.cgi", "wl_apply.cgi", "post", "", L, "", MOZ, 0);
	CX("https_browser_no_headers",     "netool.cgi", "netool.cgi?x=1", "get", "", L, "", MOZ, 1);
	CX("http_browser_same_ref",        "netool.cgi", "netool.cgi", "post", "", L, "http://192.168.50.1/Reaper_Analysis.asp\r\n", MOZ, 0);
	CX("http_browser_self_ref",        "netool.cgi", "netool.cgi", "get", "", L, "http://www.asusrouter.com/x.asp\r\n", MOZ, 0);
	CX("http_browser_sfs_same_origin", "netool.cgi", "netool.cgi", "get", "same-origin", L, "", MOZ, 0);
	CX("http_no_ua_no_headers",        "netool.cgi", "netool.cgi", "get", "", L, "", NULL, 0);
	CX("http_script_no_headers",       "netool.cgi", "netool.cgi", "get", "", L, "", "python-requests/2.32", 0);
	CX("http_browser_page_not_cgi",    "Reaper_System.asp", "Reaper_System.asp", "get", "", L, "", MOZ, 0);
	/* review 2026-10-24 S-B-2: the exemption reads the query decoded */
	C("aimesh_lock_encoded_key",       "cfg_onboarding.cgi", "cfg_onboarding.cgi?id=x&%72e_mac=AABBCCDDEEFF&new_%72e_mac=AABBCCDDEEF0", "get", "cross-site", "www.asusrouter.com", "");
	C("aimesh_lock_encoded_underscore","cfg_onboarding.cgi", "cfg_onboarding.cgi?flag=AMesh&id=x&re%5Fmac=AABBCCDDEEFF", "get", "cross-site", "www.asusrouter.com", "");
	C("aimesh_lock_encoded_all",       "cfg_onboarding.cgi", "cfg_onboarding.cgi?%72%65%5f%6d%61%63=AABBCCDDEEFF", "get", "cross-site", "www.asusrouter.com", "");
	C("aimesh_other_case_not_lock",    "cfg_onboarding.cgi", "cfg_onboarding.cgi?flag=AMesh&id=x&%52e_mac=AA", "get", "cross-site", "www.asusrouter.com", "");
	CX("aimesh_conncap_http_browser",  "cfg_onboarding.cgi", "cfg_onboarding.cgi?flag=AMesh&id=AABBCCDDEEFF", "get", "", "www.asusrouter.com", "", MOZ, 0);
	C("aimesh_long_query_refused",     "cfg_onboarding.cgi", longq, "get", "cross-site", "www.asusrouter.com", "");
	C("old_browser_foreign",  "wl_apply.cgi", "wl_apply.cgi?x=1", "get", "", L, "http://evil.example/\r\n");
	C("old_browser_same",     "wl_apply.cgi", "wl_apply.cgi", "post", "", L, "http://192.168.50.1/Advanced_Wireless_Content.asp\r\n");
	C("page_not_cgi",         "Main_Analysis_Content.asp", "Main_Analysis_Content.asp", "get", "cross-site", L, "https://evil.example/\r\n");
	C("same_site_foreign",    "netool.cgi", "netool.cgi", "get", "same-site", "router.example.lan", "http://evil.example.lan/\r\n");
	C("self_ip_to_domain",    "netool.cgi", "netool.cgi", "get", "cross-site", "www.asusrouter.com", "http://192.168.50.1/x.asp\r\n");
	C("self_old_domain",      "netool.cgi", "netool.cgi", "get", "cross-site", L, "http://router.asus.com/x.asp\r\n");
	C("self_hostname",        "netool.cgi", "netool.cgi", "get", "cross-site", L, "http://rt-be96u-1234/x.asp\r\n");
	C("self_hostname_fq",     "netool.cgi", "netool.cgi", "get", "cross-site", L, "http://RT-BE96U-1234.lan/x.asp\r\n");
	C("port_both",            "netool.cgi", "netool.cgi", "post", "same-origin", "192.168.50.1:8443", "https://192.168.50.1:8443/x.asp\r\n");
	C("cross_scheme_same_host","netool.cgi", "netool.cgi", "get", "cross-site", "192.168.50.1:8443", "http://192.168.50.1/x.asp\r\n");
	C("ref_no_path_crlf",     "netool.cgi", "netool.cgi", "get", "same-origin", L, "http://192.168.50.1\r\n");
	C("ref_host_prefix",      "netool.cgi", "netool.cgi", "get", "cross-site", L, "http://192.168.50.1.evil.example/\r\n");
	C("ref_host_in_query",    "netool.cgi", "netool.cgi", "get", "cross-site", L, "http://evil.example/?http://192.168.50.1/\r\n");
	C("ref_userinfo",         "netool.cgi", "netool.cgi", "get", "cross-site", L, "http://192.168.50.1@evil.example/\r\n");
	C("ipv6_same",            "netool.cgi", "netool.cgi", "get", "same-origin", "[fd00::1]:80", "http://[fd00::1]/x.asp\r\n");
	C("ipv6_other",           "netool.cgi", "netool.cgi", "get", "cross-site", "[fd00::1]:80", "http://[fd00::2]/x.asp\r\n");
	C("host_case",            "netool.cgi", "netool.cgi", "get", "same-origin", "WWW.ASUSROUTER.COM", "http://www.asusrouter.com/x.asp\r\n");
	C("sfs_case",             "netool.cgi", "netool.cgi", "get", "Cross-Site", L, "");
	C("aimesh_conncap",       "cfg_onboarding.cgi", "cfg_onboarding.cgi?flag=AMesh&id=AABBCCDDEEFF", "get", "cross-site", "www.asusrouter.com", "http://192.168.50.77/QIS_wizard.htm?flag=amasnode_page\r\n");
	C("aimesh_conncap_noref", "cfg_onboarding.cgi", "cfg_onboarding.cgi?flag=AMesh&id=AABBCCDDEEFF", "get", "cross-site", "www.asusrouter.com", "");
	C("aimesh_lock_refused",  "cfg_onboarding.cgi", "cfg_onboarding.cgi?re_mac=AA&new_re_mac=BB", "get", "cross-site", "www.asusrouter.com", "http://192.168.50.77/\r\n");
	C("aimesh_post_refused",  "cfg_onboarding.cgi", "cfg_onboarding.cgi", "post", "cross-site", "www.asusrouter.com", "http://192.168.50.77/\r\n");
	/* log: one line per 10 s window, the CGI name stripped to [A-Za-z0-9._/-] */
	nlog = 0; now_t = 50000;
	snprintf(host_name, sizeof(host_name), "%s", L); referer_url[0] = 0;
	reaper_xsite_cgi_refused("ne\x1b[2Jtool.cgi", "x", "get", "cross-site", MOZ, 1);
	printf("log_text %s\n", lastlog);
	now_t += 3; reaper_xsite_cgi_refused("netool.cgi", "x", "get", "cross-site", MOZ, 1);
	printf("log_window %d\n", nlog);
	now_t += 10; reaper_xsite_cgi_refused("netool.cgi", "x", "get", "cross-site", MOZ, 1);
	printf("log_after %d\n", nlog);
	now_t += 10; reaper_xsite_cgi_refused("netool.cgi", "x", "get", "", MOZ, 0);
	printf("log_http %s\n", lastlog);
	return 0;
}
'''

EXPECT = {
    "same_origin_xhr": 0, "xsite_foreign_ref": 1, "xsite_no_ref": 1, "curl_no_headers": 0,
    "typed_url_none": 0, "old_browser_foreign": 1, "old_browser_same": 0, "page_not_cgi": 0,
    "same_site_foreign": 1, "self_ip_to_domain": 0, "self_old_domain": 0, "self_hostname": 0,
    "self_hostname_fq": 0, "port_both": 0, "cross_scheme_same_host": 0, "ref_no_path_crlf": 0,
    "ref_host_prefix": 1, "ref_host_in_query": 1, "ref_userinfo": 1, "ipv6_same": 0,
    "ipv6_other": 1, "host_case": 0, "sfs_case": 1, "aimesh_conncap": 0, "aimesh_conncap_noref": 0,
    "aimesh_lock_refused": 1, "aimesh_post_refused": 1,
    # review 2026-10-24 S-B-1: plain HTTP, a browser with neither header is cross-site; scripts and HTTPS as before
    "http_browser_no_headers": 1, "http_browser_no_headers_post": 1, "https_browser_no_headers": 0,
    "http_browser_same_ref": 0, "http_browser_self_ref": 0, "http_browser_sfs_same_origin": 0,
    "http_no_ua_no_headers": 0, "http_script_no_headers": 0, "http_browser_page_not_cgi": 0,
    # review 2026-10-24 S-B-2: the exemption sees what init_cgi() sees
    "aimesh_lock_encoded_key": 1, "aimesh_lock_encoded_underscore": 1, "aimesh_lock_encoded_all": 1,
    "aimesh_other_case_not_lock": 0, "aimesh_conncap_http_browser": 0, "aimesh_long_query_refused": 1,
}

with tempfile.TemporaryDirectory() as td:
    c = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    open(c, "w").write(harness)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-Wno-unused-parameter", "-o", exe, c],
                       capture_output=True, text=True)
    check("the guard helpers compile cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n".join(fails)); sys.exit(1)
    out = subprocess.run([exe], capture_output=True, text=True).stdout
got = dict(l.split(" ", 1) for l in out.strip().split("\n"))
for k, want in EXPECT.items():
    check("%s -> %s" % (k, "refused" if want else "allowed"), got.get(k) == str(want), got.get(k))
check("the log names the CGI with control characters stripped",
      got.get("log_text") == "reaper: cross-site request refused (ne2Jtool.cgi, referer host absent, Sec-Fetch-Site cross-site)",
      got.get("log_text"))
check("a burst inside 10 s logs once", got.get("log_window") == "1", got.get("log_window"))
check("the next refusal after the window logs again", got.get("log_after") == "2", got.get("log_after"))
check("a plain-HTTP refusal says why (no header, browser)",
      got.get("log_http") == "reaper: cross-site request refused (netool.cgi, referer host absent, plain HTTP browser)", got.get("log_http"))
# review 2026-10-24 S-C2-1: the request method reaches web.c for the apply paths
check("handle_request records the method for web.c (reaper_req_post) before the handler runs",
      0 <= hr.find('reaper_req_post = strcasecmp(method, "post") == 0;') < hr.find("handler->input(file, conn_fp, cl, boundary);")
      and "int reaper_req_post = 0;" in hc)

if fails:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
print("PASS test_xsite_cgi_guard")
