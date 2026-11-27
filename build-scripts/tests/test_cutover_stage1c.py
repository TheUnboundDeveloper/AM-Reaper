#!/usr/bin/env python3
"""Native-UI cutover, stage 1c (2026-11-25): Internet Speed and Operation Mode on the kit.

  Reaper_Speed.asp    replaces AdaptiveQoS_InternetSpeed.asp + internet_speed.html (the Ookla speed test): the same
                      five backends, the stock rules (120 s per run, 50 results kept, pages of 10, six speed levels,
                      link-rate panel on a 5G+ WAN without a 10G test, quota / end-of-service notices) and Reaper's
                      fixes carried over (polling that never blocks or stacks, one silent retry, errors counted per
                      new engine line, the failure named, the QoS cap note)
  Reaper_OpMode.asp   replaces Advanced_OperationMode_Content.asp: the mode chooser. It saves nothing itself (as
                      stock: saveMode() returns before applyRule()); each choice opens the step that does the work
  REAPER-CUT2         menu tabs, reaper_native[], reaper_pagemap[] rows with shipped = 1 (the stock pages still ship
                      until the owner has checked the kit pages on a router)
The pages' behaviour is exercised under node by the maintainer's scenario harnesses (15 speed-test scenarios, 13
mode scenarios); this suite pins the source facts those rest on.
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "reaper_inject.c")):
    print("SKIP: no router source tree with httpd/reaper_inject.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))
def rd(*p): return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

inj = rd("httpd", "reaper_inject.c"); web = rd("httpd", "web.c"); menu = rd("www", "reaper", "menu.js")
sp = rd("www", "Reaper_Speed.asp"); om = rd("www", "Reaper_OpMode.asp"); ms = rd("www", "Reaper_ModeSetup.asp")
m = re.search(r"reaper_pagemap\[\]\s*=\s*\{(.*?)\n\};", inj, re.S); tab = m.group(1) if m else ""
m = re.search(r"reaper_native\[\]\s*=\s*\{(.*?)\n\};", inj, re.S); native = m.group(1) if m else ""
EN = {}
for l in open(os.path.join(SRC, "www", "EN.dict"), encoding="utf-8", errors="replace"):
    if "=" in l: k, v = l.rstrip("\n").split("=", 1); EN[k] = v

for name, page in (("Reaper_Speed.asp", sp), ("Reaper_OpMode.asp", om)):
    js = "\n".join(re.findall(r"<script>(.*?)</script>", page, re.S))
    check("%s: a Reaper-native kit page (meta, rp.css, rp.js; no stock script, no jQuery)" % name,
          '<meta name="reaper-native" content="1">' in page and 'href="/reaper/rp.css"' in page and 'src="/reaper/rp.js"' in page
          and not re.search(r'src="/(state|general|popup|help|validator|client_function)\.js"|jquery|httpApi\.js', page))
    check("%s: plain ASCII, LF line ends" % name, all(ord(c) < 128 for c in page) and "\r" not in page)
    check("%s: one strict closure" % name, "(function(){\n'use strict';" in page)
    check("%s: dict tokens in script only inside backticks (rule 29)" % name, "<#" not in re.sub(r"`[^`]*`", "", js))
    miss = sorted(set(k for k in re.findall(r"<#([A-Za-z0-9_]+)#>", page) if k not in EN))
    check("%s: every dict token exists in EN.dict" % name, not miss, miss)
    check("%s: httpd lists it as Reaper-native" % name, '"%s",' % name in native)
    check("%s: no synchronous request" % name, not re.search(r"\.open\([^)]*,\s*false\s*\)", page))

# ---------------------------------------------------------------- Internet Speed
for cgi in ("ookla_speedtest_exe.cgi", "set_ookla_speedtest_state.cgi", "set_ookla_speedtest_start_time.cgi", "ookla_speedtest_write_history.cgi"):
    # the 102.8 line spells the cache argument no_cache_IE7
    check("Speed: posts /%s, and httpd still serves it" % cgi, ("'/%s'" % cgi) in sp
          and re.search(r'\{ "%s", "text/html", no_cache(?:_IE7)?, do_html_post_and_get,' % re.escape(cgi), web) is not None)
for hook in ("ookla_speedtest_get_result", "ookla_speedtest_get_servers", "ookla_speedtest_get_history", "ookla_speedtest_get_quota"):
    check("Speed: reads the %s hook, and httpd still has it" % hook, ("hook('%s'" % hook) in sp and ('{ "%s", ej_%s}' % (hook, hook)) in web)
check("Speed: the request names httpd reads are the ones posted (type, id, iface; ookla_state; ookla_start_time; speedTest_history)",
      all(('get_cgi_json("%s", root)' % k) in web for k in ("type", "id", "iface", "ookla_state", "ookla_start_time", "speedTest_history"))
      and "{type: type || '', id: id || '', iface: q('iface').value}" in sp and "{ookla_state: s}" in sp and "{ookla_start_time: startTime}" in sp
      and "{speedTest_history: s}" in sp)
check("Speed: the stock limits (120 s, 50 engine errors, 10 a page, 50 kept)", "TEST_TIMEOUT = 120000, LEVEL_ERR_MAX = 50, PAGE = 10, KEEP = 50" in sp)
check("Speed: the six level limits (5 / 50 / 100 / 250 / 900 Mbps)", re.search(r"\[5, `<#InternetSpeed_Normal#>`.*?\[50, .*?\[100, .*?\[250, .*?\[900, .*?\[Infinity, `<#InternetSpeed_Ultra#>`", sp, re.S) is not None)
check("Speed: every request completes exactly once (load, error, timeout and abort share one guard)",
      "if (fired) return; fired = true;" in sp and "x.onerror = x.ontimeout = x.onabort = function(){ end(false); };" in sp)
check("Speed: one result poll in flight (pollBusy), re-armed per run", "if (pollBusy) return;\n  pollBusy = true;" in sp and "retryDone = false; pollBusy = false; levelErr = 0; levelErrLen = 0;" in sp)
check("Speed: one silent retry per run, never for a WAN that is down", "if (!retryDone && status !== ST.ERR_DISCON){" in sp)
check("Speed: engine errors counted per NEW line, reset by progress", "if (result.length > levelErrLen){" in sp and "} else levelErr = 0;" in sp)
check("Speed: the engine's own words are escaped before they reach the dialog", "`<#RSPD_3#>`.replace('%1', rp.esc(lastEngineError()))" in sp)
check("Speed: one WAN status chain (the timer is cleared before it is set)", sp.count("clearTimeout(wanTimer); wanTimer = setTimeout(wanCheck, 2000);") == 1)
check("Speed: a result id is saved once; the 51st result drops the oldest", "if (!dupe(r)){" in sp and "if (hist.length === KEEP + 1) hist.splice(KEEP - 1, 1);" in sp)
check("Speed: history rows are built with textContent (a server name is never parsed as markup)", "td.textContent = text" in sp and "h_rows').innerHTML" not in sp)
check("Speed: link-rate panel only for a 5G+ active WAN port without a 10G test (or by ISP profile)",
      "if (!EOS && rate >= 5000 && (!sup('10g_speedTest') || isp)) initRate(rate); else initTest();" in sp)
check("Speed: the page never names its own history list 'history' (the window's)", not re.search(r"(?<![A-Za-z0-9_.])history(?![A-Za-z0-9_])", "\n".join(re.findall(r"<script>(.*?)</script>", sp, re.S))))
check("Speed: stored values are read through an encoder", "'<% nvram_get(" not in sp)

# ---------------------------------------------------------------- Operation Mode
check("OpMode: the page posts nothing (no form, no request)", "<form" not in om and "XMLHttpRequest" not in om and "rp.post" not in om)
for target in ("/Reaper_ModeSetup.asp?mode=mb", "/QIS_wizard.htm?flag=sitesurvey_rep", "/QIS_wizard.htm?flag=sitesurvey_exp2",
               "/QIS_wizard.htm?flag=sitesurvey_exp5", "/QIS_wizard.htm?flag=amasnode_page"):
    check("OpMode: opens %s" % target, ("'%s'" % target) in om)
check("OpMode: Router / Access Point open the step page", "go('/Reaper_ModeSetup.asp?mode=' + (m.mode === '3' ? 'ap' : 'rt'));" in om)
check("OpMode: the step page takes exactly these modes", all(("mode=%s" % x) in ms or ("'%s'" % x) in ms for x in ("ap", "mb", "rt")))
check("OpMode: the step page's Cancel returns to this page", "top.location.href = '/reaper_shell.asp#Reaper_OpMode.asp';" in ms)
check("OpMode: modes offered by the stock flags (noRouter, noAP, repeater, rp_express_2g / _5g, psta, amas + amasNode)",
      all(x in om for x in ("when: !sup('noRouter')", "when: !sup('noAP')", "when: sup('repeater')", "when: sup('rp_express_2g')", "when: sup('rp_express_5g')",
                            "when: sup('psta')", "when: sup('amas') && sup('amasNode')")))
check("OpMode: already in this mode is refused; for Repeater the Express Way choice counts", "function isNow(m){ return m.mode === NOW && (m.mode !== '2' || m.x === NOWX); }" in om
      and "if (isNow(m)){ msg(NAME + ' ' + `<#op_already_configured#>`); return; }" in om)
check("OpMode: the AiMesh question before Repeater or Media Bridge on an AiMesh router", "if (MESH && (m.mode === '2' || m.mode === '4')){" in om
      and "`<#AiMesh_confirm_msg2#>` : `<#AiMesh_confirm_msg4#>`" in om)
check("OpMode: the Network-page warning only between Router and Access Point", "if (sup('mtlancfg') && NOW === from){" in om)
check("OpMode: questions go through the Reaper dialog (text only), descriptions through textContent", "window.reaperConfirm(text," in om and "p.textContent = plain(t)" in om)
stock = rd("www", "Advanced_OperationMode_Content.asp")
check("stock page (still shipped): its saveMode() targets are the ones this page uses",
      all(x in stock for x in ("'/Reaper_ModeSetup.asp?mode=ap'", "'/Reaper_ModeSetup.asp?mode=mb'", "'/Reaper_ModeSetup.asp?mode=rt'",
                               "'/QIS_wizard.htm?flag=sitesurvey_rep'", "'/QIS_wizard.htm?flag=amasnode_page'")))

# ---------------------------------------------------------------- wiring
check("menu: Internet Speed is the kit page, behind the ookla flag", "T('Reaper_Speed.asp', `<#InternetSpeed#>`, sup('ookla'))" in menu and "AdaptiveQoS_InternetSpeed" not in menu)
check("menu: Operation Mode is the kit page, with the stock condition", "T('Reaper_OpMode.asp', `<#menu5_6_1#>`, !sup('swmode_switch') && !sup('lyra_hide'))" in menu
      and "Advanced_OperationMode_Content" not in menu)
for old, new in (("adaptiveqos_internetspeed.asp", "Reaper_Speed.asp"), ("advanced_operationmode_content.asp", "Reaper_OpMode.asp")):
    check("httpd: %s goes to %s; the stock file no longer ships (REAPER-CUT8, shipped = 0)" % (old, new),
          tab.count('\t{ "%s", "%s", 0 },\n' % (old, new)) == 1 and tab.count('"%s"' % old) == 1)
pages = sorted(set(re.findall(r"T\('([A-Za-z0-9_]+\.(?:asp|htm|html))'", menu)))
left = [p for p in pages if not p.startswith(("Reaper_", "Main_ReaperDash"))]
check("menu: no stock page is listed any more (stage 2 moved AiMesh to the kit, stage 3 the Network page)", left == [], left)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
