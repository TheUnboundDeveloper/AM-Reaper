#!/usr/bin/env python3
"""The ASUS Router app exemption is an opt-in, off at factory, home network only (REAPER-APP-OPTIN, 2026-11-28).

WHY. Since REAPER-NOAPP (2026-11-24) a request that names the ASUS Router phone app in its User-Agent is checked like
a browser's; the app sends no Referer and no page token, so it stopped working. A field user asked for a choice: off
by default, on for those who depend on the app and accept the risk, and never from outside the home network.

WHAT IS CHECKED.
  - the setting reaper_app_allow: one defaults row, value 0; no code writes it (only the admin's Apply does); it is
    not in the settings-file table (a security opt-in is switched on per router - test_backup_coverage.py names it
    full-backup-only); the Security review watches it.
  - ONE decision function, reaper_app_exempt(), called once per request right after the User-Agent is classified;
    its result (reaper_req_app) is what the five places read: the cross-site refusal, the Referer rule, the two
    Referer checks, the page token, the POST-only rule of apply.cgi. Nothing else assigns it.
  - the decision itself, compiled on the host from the tree's own text with stand-ins for nvram, the clock and the
    log: switch off = never; only the app's own User-Agent kind; peer inside the main network (IPv4 in the LAN
    subnet and not the router, IPv6 only on the listener bound to the LAN bridge); never on the remote-access or
    loopback listener, never a guest subnet, a VPN client or an internet address; one "in use" log line per boot,
    the "from outside" line at most once per 10 s.
  - the page: the switch on Administration > System, its texts by dict key, the question asked when switching ON.
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "httpd.c")):
    print("SKIP: no router source tree with httpd/httpd.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))

def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

def nocomment(s):
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)

hc, hh, wc = rd("httpd", "httpd.c"), rd("httpd", "httpd.h"), rd("httpd", "web.c")
defaults, rw, page = rd("shared", "defaults.c"), rd("rc", "rwatch.c"), rd("www", "Reaper_System.asp")
KEY = "reaper_app_allow"

# ---------------------------------------------------------------- the setting
rows = re.findall(r'\{\s*"%s",\s*"([^"]*)",' % KEY, defaults)
check("defaults.c: one row for %s, value 0 (off at factory)" % KEY, rows == ["0"], rows)
writers = []
for d in ("httpd", "rc", "shared"):
    for root, _, files in os.walk(os.path.join(SRC, d)):
        for f in files:
            if not f.endswith((".c", ".h")):
                continue
            try:
                s = open(os.path.join(root, f), encoding="utf-8", errors="surrogateescape").read()
            except OSError:
                continue
            if KEY in s and re.search(r'nvram_(?:set|set_int|unset|pf_set)\s*\([^;]*%s' % KEY, s):
                writers.append(os.path.join(d, f))
check("no code writes the setting (a firmware update or a boot never switches it)", not writers, writers)
m = re.search(r"rcfg_flags\[\] = \{(.*?)\n\};", wc, re.S)
check("the settings-file table does not carry it (switched on per router only)", m is not None and KEY not in m.group(1))
m = re.search(r"\"RV_NV_S='([^']*)'", rw)
check("the Security review watches it (switching it on shows as a change to accept)", m is not None and KEY in m.group(1).split())

# ---------------------------------------------------------------- one decision, five places
hcn, wcn = nocomment(hc), nocomment(wc)
check("httpd.c: one decision function", hc.count("\nstatic int reaper_app_exempt(int fromapp)\n{") == 1)
check("...called once per request, right after the User-Agent is classified",
      hcn.count("reaper_app_exempt(") == 2
      and re.search(r"\tfromapp = check_user_agent\(useragent\);\n\treaper_req_app = reaper_app_exempt\(fromapp\);", hc) is not None)
check("...and nothing else sets the result", len(re.findall(r"\breaper_req_app\s*=[^=]", hcn + wcn)) == 2
      and "\nint reaper_req_app = 0;" in hc and "extern int reaper_req_app;" in hh)
uses_h = len(re.findall(r"\breaper_req_app\b", hcn))
uses_w = len(re.findall(r"\breaper_req_app\b", wcn))
check("the result is read at the five places and nowhere else (httpd.c: definition, assignment, 4 reads; web.c: 2 reads)",
      uses_h == 6 and uses_w == 2, (uses_h, uses_w))
check("place 1: the cross-site refusal",
      hc.count("if (!reaper_req_app && reaper_xsite_cgi_refused(url, file, method, sec_fetch_site, useragent, do_ssl)) {") == 1)
check("place 2: the Referer rule of the page",
      hc.count("\tif (reaper_req_app)\t/* REAPER-APP-OPTIN: the app sends no Referer */\n\t\tdo_referer = 0;\n") == 1)
check("place 3: the two Referer checks",
      hc.count("referer_check(referer, reaper_req_app ? fromapp : 0);") == 1
      and hc.count("check_noauth_referrer(referer, reaper_req_app ? fromapp : 0);") == 1)
m = re.search(r"\nstatic int reaper_apply_token_ok\(const char \*hid, const char \*where\)\n\{(.*?)\n\}\n", wc, re.S)
tok = m.group(1) if m else ""
check("place 4: the page token (first thing the check does; the comparison itself is unchanged)",
      tok.lstrip("\n").startswith("\tstatic long last;\n\tconst char *want;\n\n\tif (reaper_req_app)\t/* REAPER-APP-OPTIN */\n\t\treturn 1;\n")
      and 'want = nvram_safe_get("http_id");' in tok and "strcmp(hid, want) == 0" in tok, tok[:300])
check("place 5: apply.cgi's POST-only rule",
      wc.count('if (!strcmp(action_mode, "apply") && !reaper_req_app && reaper_apply_needs_post("apply.cgi")) {') == 1)
check("signing in is untouched: auth_check() runs for the request whatever the decision",
      "auth_result = auth_check(url, file, cookies, fromapp, &add_try);" in hc and "reaper_req_app" not in
      hc[hc.find("auth_result = auth_check("):hc.find("reaper_req_authed = 1;")])
check("the start_apply path keeps its POST-only rule for everybody",
      'if ((!strcmp(action_mode, "apply") || !strcmp(action_mode, "apply_new")) && reaper_apply_needs_post("update_variables"))' in wc)

# ---------------------------------------------------------------- the decision, on the host
a = hc.find("static int reaper_wan_listener(void)\n")
b = hc.find("\nstatic int reaper_app_exempt(int fromapp)\n{")
e = hc.find("\n}\n", b) if b > 0 else -1
block = hc[a:e + 3] if 0 <= a < b < e else ""
check("the decision block is found (reaper_wan_listener .. reaper_app_exempt)", bool(block))
fn = block[block.find("static int reaper_app_exempt"):] if block else ""
check("the decision needs the switch, the app's own User-Agent kind and a main-network peer - all three",
      'fromapp != FROM_DUTUtil || !nvram_match("%s", "1")' % KEY in fn and "if (!reaper_peer_main_lan()) {" in fn
      and fn.count("return 1;") == 1)
enum = re.search(r"enum \{\n\tFROM_BROWSER,.*?\};", rd("shared", "shared.h"), re.S)
check("shared.h: the User-Agent kinds are found", enum is not None)

HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#define RTCONFIG_IPV6 1
@ENUM@
typedef struct { int family; union { struct in_addr in; struct in6_addr in6; }; } uaddr;
static uaddr login_uip_tmp;
static char *http_ifname;
static const char *nv_sw = "0", *nv_ip = "192.168.50.1", *nv_mask = "255.255.255.0", *nv_if = "br0";
static long now = 1000;
static int n_out, n_use, n_other;
static char *nvram_safe_get(const char *k)
{
	if (!strcmp(k, "reaper_app_allow")) return (char *)nv_sw;
	if (!strcmp(k, "lan_ipaddr")) return (char *)nv_ip;
	if (!strcmp(k, "lan_netmask")) return (char *)nv_mask;
	if (!strcmp(k, "lan_ifname")) return (char *)nv_if;
	return (char *)"";
}
static int nvram_match(const char *k, const char *v) { return !strcmp(nvram_safe_get(k), v); }
static long uptime(void) { return now; }
static void logmessage(const char *tag, const char *fmt, ...)
{
	(void)tag;
	if (strstr(fmt, "from outside the home network")) n_out++;
	else if (strstr(fmt, "exemption is in use")) n_use++;
	else n_other++;
}
static int uaddr_is_unspecified(uaddr *u)
{
	if (u->family == AF_INET) return u->in.s_addr == 0;
	if (u->family == AF_INET6) return IN6_IS_ADDR_UNSPECIFIED(&u->in6);
	return 1;
}
static int uaddr_is_localhost(uaddr *u)
{
	if (u->family == AF_INET) return (ntohl(u->in.s_addr) >> 24) == 127;
	if (u->family == AF_INET6) return IN6_IS_ADDR_LOOPBACK(&u->in6);
	return 0;
}
static char *safe_uaddr_ntop(const uaddr *u, char *dst, size_t cnt)
{
	if (!inet_ntop(u->family, u->family == AF_INET ? (const void *)&u->in : (const void *)&u->in6, dst, cnt))
		snprintf(dst, cnt, "?");
	return dst;
}
@BLOCK@
static int run(const char *sw, int kind, const char *ifn, const char *peer)
{
	nv_sw = sw; http_ifname = (char *)ifn;
	memset(&login_uip_tmp, 0, sizeof(login_uip_tmp));
	if (inet_pton(AF_INET, peer, &login_uip_tmp.in) == 1) login_uip_tmp.family = AF_INET;
	else if (inet_pton(AF_INET6, peer, &login_uip_tmp.in6) == 1) login_uip_tmp.family = AF_INET6;
	return reaper_app_exempt(kind);
}
#define T(name, got, want) printf("T\t%s\t%d\t%d\n", name, (int)(got), (int)(want))
int main(int argc, char **argv)
{
	static const int others[] = { FROM_BROWSER, FROM_ASUSROUTER, FROM_ASSIA, FROM_IFTTT, FROM_ALEXA, FROM_WebView, FROM_ATE,
		FROM_MyASUS, FROM_BLE, FROM_AWSIOT, FROM_UNKNOWN };
	const char *LANP = "192.168.50.20";
	unsigned i;
	int second = argc > 1 && !strcmp(argv[1], "second");

	if (second) {	/* another web server process of the same boot: the marker file is already there */
		T("second process: still exempt", run("1", FROM_DUTUtil, "br0", LANP), 1);
		T("second process: no second 'in use' line in this boot", n_use, 0);
		return 0;
	}
	T("switch 0: the app on the LAN earns nothing", run("0", FROM_DUTUtil, "br0", LANP), 0);
	T("switch unset: nothing", run("", FROM_DUTUtil, "br0", LANP), 0);
	T("switch 2 (not a value the page writes): nothing", run("2", FROM_DUTUtil, "br0", LANP), 0);
	T("switch 0: an app User-Agent from outside is not even logged", run("0", FROM_DUTUtil, "br0", "203.0.113.9"), 0);
	for (i = 0; i < sizeof(others) / sizeof(others[0]); i++)
		if (run("1", others[i], "br0", LANP)) { T("switch 1: another User-Agent kind earns nothing", others[i], -1); }
	T("switch 1: every other User-Agent kind earns nothing, silently", n_out + n_use + n_other, 0);

	T("internet address (web access from WAN forwards to the LAN listener)", run("1", FROM_DUTUtil, "br0", "203.0.113.9"), 0);
	T("...logged", n_out, 1);
	T("a second outside claim right away", run("1", FROM_DUTUtil, "br0", "198.51.100.7"), 0);
	T("...not logged again within 10 s", n_out, 1);
	now += 10;
	T("VPN-server client", run("1", FROM_DUTUtil, "br0", "10.8.0.2"), 0);
	T("...logged after 10 s", n_out, 2);
	now += 10; T("guest / other network with its own subnet", run("1", FROM_DUTUtil, "br0", "192.168.52.10"), 0);
	now += 10; T("loopback address", run("1", FROM_DUTUtil, "br0", "127.0.0.1"), 0);
	now += 10; T("the router's own LAN address", run("1", FROM_DUTUtil, "br0", "192.168.50.1"), 0);
	now += 10; T("LAN IPv4 address on the remote-access listener", run("1", FROM_DUTUtil, "eth0", LANP), 0);
	now += 10; T("IPv6 on the remote-access listener", run("1", FROM_DUTUtil, "eth0", "2001:db8::5"), 0);
	now += 10; T("LAN IPv4 address on the loopback listener", run("1", FROM_DUTUtil, "lo", LANP), 0);
	now += 10; T("IPv6 with no bound interface", run("1", FROM_DUTUtil, NULL, "2001:db8::5"), 0);
	now += 10; T("IPv6 loopback on the LAN listener", run("1", FROM_DUTUtil, "br0", "::1"), 0);
	now += 10; T("no peer address", run("1", FROM_DUTUtil, "br0", "0.0.0.0"), 0);
	nv_mask = "0.0.0.0"; now += 10; T("an empty netmask matches nobody", run("1", FROM_DUTUtil, "br0", "203.0.113.9"), 0);
	nv_mask = "junk"; now += 10; T("an unreadable netmask matches nobody", run("1", FROM_DUTUtil, "br0", LANP), 0);
	nv_mask = "255.255.255.0";
	T("nothing above counted as a use", n_use, 0);

	T("switch 1, the app, IPv4 on the main network", run("1", FROM_DUTUtil, "br0", LANP), 1);
	T("...'in use' logged", n_use, 1);
	T("again", run("1", FROM_DUTUtil, "br0", "192.168.50.77"), 1);
	T("IPv6 link-local on the listener bound to the LAN bridge", run("1", FROM_DUTUtil, "br0", "fe80::1234"), 1);
	T("IPv6 global on the listener bound to the LAN bridge", run("1", FROM_DUTUtil, "br0", "2001:db8::5"), 1);
	T("IPv4 on the main network, no bound interface (access-point mode)", run("1", FROM_DUTUtil, NULL, LANP), 1);
	T("...'in use' logged once only", n_use, 1);
	T("no other log line", n_other, 0);
	T("back to 0: off again at once", run("0", FROM_DUTUtil, "br0", LANP), 0);
	return 0;
}
'''

cc = shutil.which("gcc") or shutil.which("cc")
if not cc:
    print("note: no host C compiler - the decision was not run")
elif block and enum:
    tmp = tempfile.mkdtemp(prefix="app_optin_")
    try:
        marker = os.path.join(tmp, "used")
        blk = block.replace('"/tmp/reaper/.app_optin_used"', '"%s"' % marker)
        check("the once-per-boot marker path is in the block", blk != block)
        src = HARNESS.replace("@ENUM@", enum.group(0)).replace("@BLOCK@", blk)
        open(os.path.join(tmp, "h.c"), "w").write(src)
        r = subprocess.run([cc, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-O1", "-o", os.path.join(tmp, "h"), os.path.join(tmp, "h.c")],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        check("the decision block compiles cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stdout[-1500:])
        if r.returncode == 0:
            n = 0
            for arg in ([], ["second"]):
                o = subprocess.run([os.path.join(tmp, "h")] + arg, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
                check("harness run%s exits 0" % (" (second process)" if arg else ""), o.returncode == 0, o.stdout[-600:])
                for line in o.stdout.splitlines():
                    p = line.split("\t")
                    if len(p) == 4 and p[0] == "T":
                        n += 1
                        check("decision: " + p[1], p[2] == p[3], "got %s, want %s" % (p[2], p[3]))
            check("all decision cases ran (34)", n == 34, n)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- the page
check("page: the switch is on the Login and access tab, in its own panel",
      page.count('<div class="panel" id="p_app">') == 1 and page.count('<input type="checkbox" id="t_reaper_app_allow">') == 1
      and page.find('id="tab_access"') < page.find('id="p_app"') < page.find('<!-- ================= SSH'))
check("page: it shows the router's value and posts it only when changed (the page's diff)",
      'reaper_app_allow: <% nvram_get_js("reaper_app_allow"); %>' in page
      and "section('p_app', 'access', function(){ setChk('t_reaper_app_allow', isOn(NV.reaper_app_allow)); },\n  function(c){ c.reaper_app_allow = chk('t_reaper_app_allow'); });" in page
      and "reaper_app_allow: 't_reaper_app_allow'" in page)
check("page: switching it ON asks first; cancelling posts nothing",
      "if (c.reaper_app_allow === '1' && !isOn(NV.reaper_app_allow) && !confirm(`<#RAPP_8#>`)) return NOPOST;" in page)
p0 = page.find('<div class="panel" id="p_app">')
panel = page[p0:page.find('<div class="panel" id="p_acl">')] if p0 > 0 else ""
bare = re.sub(r"<#\w+#>", "", re.sub(r"<!--.*?-->", "", panel, flags=re.S))	# the panel without comments and dict tokens
keys = sorted(set(re.findall(r"<#(RAPP_\d+)#>", page)), key=lambda k: int(k[5:]))
check("page: every text is a dict key (RAPP_1..RAPP_8), none written into the page",
      bool(panel) and keys == ["RAPP_%d" % i for i in range(1, 9)] and not re.search(r"[A-Za-z]", re.sub(r"<[^>]*>", "", bare)),
      (keys, re.sub(r"<[^>]*>", "", bare).strip()[:200]))
check("page: no new colour (the kit's .hint / .hint.warn carry the notes)", bool(panel) and "#" not in bare and "style=" not in panel)
en = os.path.join(SRC, "www", "EN.dict")
if os.path.isfile(en):
    ent = open(en, encoding="utf-8", errors="surrogateescape").read()
    if re.search(r"^RAPP_1=", ent, re.M):
        packs = sorted(f for f in os.listdir(os.path.join(SRC, "www")) if re.fullmatch(r"[A-Z]{2}\.dict", f))
        miss = []
        for f in packs:
            s = open(os.path.join(SRC, "www", f), encoding="utf-8", errors="surrogateescape").read()
            miss += ["%s:RAPP_%d" % (f, i) for i in range(1, 9) if len(re.findall(r"^RAPP_%d=.+$" % i, s, re.M)) != 1]
        check("language packs: RAPP_1..RAPP_8 once in each of the %d packs" % len(packs), not miss and len(packs) == 25, miss[:8])
        check("EN: the switch names the home network, says sign-in is still required and that the app is not supported",
              all(re.search(p, ent, re.M) for p in (r"^RAPP_3=.*home network", r"^RAPP_5=.*sign", r"^RAPP_[267]=.*not (tested or )?supported")))
    else:
        print("note: RAPP_1..RAPP_8 are not in EN.dict yet (staged for the language-pack merge)")

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed: the ASUS Router app exemption is an opt-in, off at factory, main network only")
