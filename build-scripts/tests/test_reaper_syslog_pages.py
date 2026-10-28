#!/usr/bin/env python3
"""System Log group on the Reaper kit (Reaper-native UI, 2026-10-23): Reaper_Log (General Log + the login log that
was "Security Update Notification"), Reaper_WLog, Reaper_Leases, Reaper_IPv6, Reaper_Routes, Reaper_PortFwd.

WHY. Pins what the parity harness cannot see: every page is ASCII, on the kit, runs in one closure, uses only
existing dict tokens and only inside backticks in JS, is native in httpd (no stock skin) with the stock URL
redirected; the emitters escape client-influenced text for inline arrays and always close them; the wireless
emitter keeps its column count; the routes action dumps every table; the kit carries one shared sort comparator.

WHAT IT DOES. Source checks on the six pages, www/ajax_reaper_wlstatus.asp, www/reaper/menu.js, www/reaper/rp.js,
www/reaper_shell.asp, httpd/reaper_inject.c, httpd/web.c, httpd/data_arrays.c, httpd/sysdeps/web-broadcom-am.c and
the 25 dicts; `node --check` on each page script; a node run of rp.cmp.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")
www = os.path.join(SRC, "www")
PAGES = ["Reaper_Log.asp", "Reaper_WLog.asp", "Reaper_Leases.asp", "Reaper_IPv6.asp", "Reaper_Routes.asp", "Reaper_PortFwd.asp"]
if not all(os.path.exists(os.path.join(www, p)) for p in PAGES):
    print("SKIP: System Log pages not found"); sys.exit(0)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

en = rd(os.path.join(www, "EN.dict"))
T = {p: rd(os.path.join(www, p)) for p in PAGES}
for p, t in T.items():
    check(p + ": ASCII only", not any(ord(c) > 127 for c in t))
    check(p + ": on the kit (rp.css, rp.js, reaper-native meta, no jQuery/httpApi/state.js) and inside the crimson frame",
          '<link rel="stylesheet" href="/reaper/rp.css">' in t and '<script src="/reaper/rp.js"></script>' in t
          and '<meta name="reaper-native" content="1">' in t and '<div class="rframe">' in t and not re.search(r'src="/(js/jquery|js/httpApi|state)\.js"', t))
    js = t[t.rfind("<script>"):]
    check(p + ": one closure, strict, no inline handlers", js.startswith("<script>\n(function(){\n'use strict';") and js.rstrip().endswith("})();\n</script>\n</body>\n</html>")
          and js.count("<script>") == 1 and "onclick=" not in t)
    toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
    miss = [k for k in toks if ("\n%s=" % k) not in en]
    check(p + ": every dict token exists (%d)" % len(toks), not miss, miss)
    js_wo = re.sub(r"`[^`]*`", "", js)
    check(p + ": tokens in the script only inside backticks (rule 29)", "<#" not in js_wo, [m.group(0) for m in re.finditer(r".{0,40}<#[A-Za-z0-9_]+#>", js_wo)][:3])

# behaviour pins
L, W, LS, I6, RT, PF = (T[p] for p in PAGES)
check("Log: appGet text cut between the first '\":' and the last \"\\n}\" (no fixed offsets), polling only while visible + auto refresh",
      "var a = t.indexOf('\":'), b = t.lastIndexOf('\\n}');" in L and "if (!document.hidden) load(false);" in L and "if (q('c_auto').checked) timer = setInterval" in L)
check("Log: system + login views, Clear = apply.cgi \" Clear \", Save = syslog.txt, settings post changed-only with restart_logger",
      "nvram_dump(\"security_recored.log\",\"\")" in L and 'name="action_mode" value=" Clear "' in L and "location.href = '/syslog.txt'" in L
      and "rp.post(document.form, ch, 'restart_logger', 5, false)" in L)
check("Log: the view is written as text (textContent), never as HTML", "box.textContent = out.join('\\n');" in L and "innerHTML" not in L.split("function render()")[1].split("function load(")[0])
check("WLog: band by wlN_nband, endpoint evaluated in a function scope, driver dump only on demand",
      "b === '2' ? '2.4 GHz' : b === '1' ? '5 GHz' : b === '4' ? '6 GHz'" in W and "return (new Function(src))();" in W and "'/ajax_reaper_wlstatus.asp?_='" in W
      and W.count("/wl_log.asp") == 1)
check("Leases/IPv6/PortFwd: emitter arrays declared before the ej call (strict mode), no pop()+length>1 off-by-one",
      "var leasearray = [];\n<% get_leases_array(); %>" in LS and "var ipv6cfgarray = [[]], ipv6clientarray = [[]], pinholesarray = [[]];" in I6
      and ".pop()" not in I6 and "<% get_vserver_array(); %>" in PF and "<% get_upnp_array(); %>" in PF)
check("PortFwd: Reaper's own DNAT chain is named, not passed off as a user port forward", "REAPER_GKN: `<#RLOG_" in PF)
check("Routes: every table + rules from reaper_pbr.cgi?action=routes, local table folded by default",
      "'/reaper_pbr.cgi?action=routes&http_id=' + encodeURIComponent(HTTPID)" in RT and "var HTTPID = <% nvram_get_js(\"http_id\"); %>;" in RT
      and "if (t === 'local' && !showLocal) return;" in RT)
check("sortable lists use the kit comparator", "rp.cmp(" in LS and "rp.cmp(" in I6 and "rp.cmp(" in W)

# wiring
menu = rd(os.path.join(www, "reaper", "menu.js")); inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c")); shell = rd(os.path.join(www, "reaper_shell.asp"))
stock = ["Main_LogStatus_Content", "Main_WStatus_Content", "Main_DHCPStatus_Content", "Main_IPV6Status_Content", "Main_RouteStatus_Content", "Main_IPTStatus_Content", "Main_Security_Change_Notification"]
check("menu: the System Log group points at the Reaper pages; the login-log tab folded into General Log",
      all(("T('%s'" % p) in menu for p in PAGES) and not any(s in menu for s in stock) and "Main_LogStatus_Content" not in shell)
# review 2026-10-24 (Q-B-4): the login-notification row had two targets in the old two lists; it now opens the
# General Log's login view
sup = {"main_logstatus_content": "Reaper_Log.asp", "main_security_change_notification": "Reaper_Log.asp?view=login", "main_wstatus_content": "Reaper_WLog.asp",
       "main_dhcpstatus_content": "Reaper_Leases.asp", "main_ipv6status_content": "Reaper_IPv6.asp", "main_routestatus_content": "Reaper_Routes.asp", "main_iptstatus_content": "Reaper_PortFwd.asp"}
check("httpd: SUP redirects all seven stock URLs; the six pages are native (no stock skin)",
      all(('{ "%s.asp", "%s", ' % kv) in inj for kv in sup.items())
      and all(inj.index('\t"%s",' % p) > inj.index("static const char *reaper_native[]") for p in PAGES))
aj = rd(os.path.join(www, "ajax_reaper_wlstatus.asp"))
check("ajax_reaper_wlstatus.asp runs get_wl_status only (stock's ajax also ran the closed driver dump every refresh)",
      aj.strip() == "<% get_wl_status(); %>")

# _r25 field: a ?query on a static file 404'd on the old base (do_file looked the path up with the query); kept so
# the kit does not grow a cache-busting query the build stamp already covers
allw = "".join(rd(os.path.join(www, f)) for f in os.listdir(www) if f.endswith(".asp"))
check("no page links rp.css with a query string (httpd answers 404)", "rp.css?" not in allw)

# C side
web = rd(os.path.join(SRC, "httpd", "web.c")); da = rd(os.path.join(SRC, "httpd", "data_arrays.c"))
wb = rd(os.path.join(SRC, "httpd", "sysdeps", "web-broadcom-am.c"))
check("reaper_pbr.cgi routes action: ip rule + every table (v4/v6) + rt_tables, fixed commands, capped",
      'if (strcmp(action, "routes") == 0) {' in web and 'fw_emit_cmd(stream, "ip -4 route show table all 2>/dev/null", 262144);' in web
      and 'fw_emit_cmd(stream, "ip -6 rule show 2>/dev/null", 32768);' in web)
check("data_arrays.c: UPnP + pinhole descriptions and IPv6 hostnames go through lease_js_escape (no str_escape_quotes left for them)",
      da.count("lease_js_escape(desc2, sizeof(desc2), desc);") == 2 and da.count("lease_js_escape(host_esc, sizeof(host_esc), hostname);") == 2
      and "str_escape_quotes(desc2" not in da)
# 40585 base (merge stops 63/64): upstream serves every .css no_cache and do_file strips the query; the cache bust
# answers .css with Cache-Control: no-cache plus a build-stamped ETag, so the old 60 s rp.css row is gone (moot)
_hc = rd(os.path.join(SRC, "httpd", "httpd.c"))
_css = web.find('{ "**.css", "text/css", no_cache, NULL, do_file, NULL },')
check("httpd serves reaper/rp.css fresh: **.css is no_cache with no cached row ahead of it, .css revalidates on a build-stamped ETag",
      _css >= 0 and not re.search(r'\{ "reaper/[^"]*", "text/css", cache_object', web[:_css])
      and '(!strcasecmp(ext, ".css") || (!strcasecmp(ext, ".js") && etag_header_flag == 1));' in _hc
      and "if (revalidate)\n\t\textra_header = no_cache;" in _hc
      and "reaper_append_buildinfo_to_etag(etag_value, sizeof(etag_value));" in _hc)
check("data_arrays.c: a missing IPv6 client list still closes the array", "close the array - returning here left it open" in da)
check("web-broadcom-am.c: no-SCBSTATS stations keep the column count; one failed interface no longer drops the rest",
      'ret += websWrite(wp, "\\"\\",\\"\\",\\"\\",\\"\\",\\"\\",\\"\\",\\"");' in wb and "if (wl_ioctl(name_vif, WLC_GET_VAR, auth, mac_list_size))\n\t\t\t\tcontinue;" in wb)

# dicts
PACKS = "EN DE FR ES BR IT NL DA NO SV FI PL CZ SL HU RO RU UK TR MS TH JP KR CN TW".split()
n = len(re.findall(r"^RLOG_\d+=", en, re.M))
def pos(t): return {l.split("=", 1)[0]: i for i, l in enumerate(t.split("\n")) if "=" in l}
ep = pos(en); keys = ["RLOG_%02d" % i for i in range(1, n + 1)]
bad = [pk for pk in PACKS if any(pos(rd(os.path.join(www, pk + ".dict"))).get(k) != ep.get(k) for k in keys)]
check("RLOG_01-%02d in all 25 packs at the same line (lockstep)" % n, n >= 80 and not bad, bad)

node = shutil.which("node")
if node:
    for p, t in T.items():
        s = re.findall(r"<script>(.*?)</script>", t, re.S)[-1]
        s = re.sub(r"<%.*?%>", "0", re.sub(r"<%\s*nvram_get_js\([^%]*%>", '""', s)); s = re.sub(r"<#[A-Za-z0-9_-]+#>", "X", s)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(s); jp = f.name
        r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
        check(p + ": script parses (node --check)", r.returncode == 0, r.stderr[-300:])
    rpjs = rd(os.path.join(www, "reaper", "rp.js"))
    h = ("var window = {}; var document = {readyState: 'complete', addEventListener: function(){}, querySelectorAll: function(){ return []; },"
         " getElementById: function(){ return null; }, body: {appendChild: function(){}} }; window.addEventListener = function(){};\n" + re.sub(r"<%.*?%>", "", re.sub(r"<%\s*nvram_get_js\([^%]*%>", '""', rpjs))
         + "\nconsole.log(['10.0.0.20','192.168.50.3','','10.0.0.3','fe80::1'].sort(window.rp.cmp('ip')).join(','));\n")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(h); jp = f.name
    r = subprocess.run([node, jp], capture_output=True, text=True); os.unlink(jp)
    check("rp.cmp('ip') sorts IPv4 by octet, other text after, empties last", r.stdout.strip() == "10.0.0.3,10.0.0.20,192.168.50.3,fe80::1,", r.stdout + r.stderr[-200:])
else:
    print("note: node not found - syntax and comparator checks skipped")

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + x) for x in fails]; sys.exit(1)
print("\nall checks passed")
