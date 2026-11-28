#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Native-UI cutover stage 5 (REAPER-CUT8, owner, 2026-11-26): the stock ASUS UI is gone.

WHY THIS EXISTS. Stage 5 removed the stock skin and the nvram switch reaper_inject (=0 served the stock UI), made the
dashboard the only index page, and stopped shipping the stock files nothing loads any more - while the owner kept
three things on purpose: the setup wizard (QIS_wizard.htm + mobile/, the Repeater / Express Way / AiMesh-node mode
flows), the stock Printer Server / Time Machine pages (an AiMesh node serves them), and the pages the closed
libwebapi.so names (SDN/sdn.html, internet_speed.html), plus the small scripts add-on pages may load. A later edit
that deletes one of those, or brings the switch or index.asp back, breaks a real flow; this test pins all of it.
The module's own serving behaviour is pinned by test_inject_pieces.py.
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "reaper_inject.c")):
    print("SKIP: no router source tree"); sys.exit(77)
HERE = os.path.dirname(os.path.abspath(__file__))
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))
def rd(*p):
    try: return open(os.path.join(*p), encoding="utf-8", errors="replace").read()
    except OSError: return ""
def code(t):      # what the compiler sees
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", t, flags=re.S))

www = os.path.join(SRC, "www")
mk = rd(www, "Makefile")
a = mk.find("REAPER-CUT8-STOCK"); b = mk.find("# End REAPER-CUT8-STOCK")
blk = mk[a:b] if 0 <= a < b else ""
rm = lambda f: "\trm -f $(INSTALLDIR)/www/%s\n" % f
# the dictionary prune (REAPER-CUT8-DICT, test_dict_prune.py) is the only step allowed after the block
tail = mk[b + len("# End REAPER-CUT8-STOCK"):] if b >= 0 else ""
check("www/Makefile: the stage 5 removal block is there once, at the end of the install recipe",
      mk.count("# End REAPER-CUT8-STOCK") == 1 and blk.count("rm -f") >= 380
      and (not tail.strip() or (tail.lstrip().startswith("# ---- REAPER-CUT8-DICT") and tail.rstrip().endswith("# End REAPER-CUT8-DICT"))),
      blk.count("rm -f"))
check("...its conditionals are balanced", blk.count("ifneq (") == blk.count("endif") == 3)
for f in ("index.asp", "AiMesh.asp", "SDN.asp", "AdaptiveQoS_InternetSpeed.asp", "Advanced_OperationMode_Content.asp",
          "aimesh/aimesh_topology.html", "device-map/amesh.asp", "Nologin.asp", "offline.htm", "gotoHomePage.htm",
          "reaper/reaper_content.css", "reaper/reaper_content_aimesh.css", "reaper/reaper_content_network.css"):
    check("removed at install: %s" % f, rm(f) in blk)
# REAPER-ADDON-SKIN (owner 2026-11-27): the add-on page sheet ships (third-party pages installed at run time load it)
check("REAPER-ADDON-SKIN: reaper/reaper_addon.css is in the source and nothing removes it at install",
      os.path.isfile(os.path.join(www, "reaper", "reaper_addon.css")) and "reaper_addon.css" not in mk.replace(
          "# REAPER-ADDON-SKIN (2026-11-27): reaper/reaper_addon.css", "") and "REAPER-ADDON-SKIN" in blk)
gate = {"get_release_note_revertfw.asp": "ifneq ($(RTCONFIG_REVERTFW),y)\n\trm -f $(INSTALLDIR)/www/get_release_note_revertfw.asp\n",
        "release_note_amas.asp": "ifneq ($(RTCONFIG_ROLLBACKFW),y)\n\trm -f $(INSTALLDIR)/www/release_note_amas.asp\nendif\nendif\n",
        "get_release_note_amas.asp": "ifneq ($(RTCONFIG_ROLLBACKFW),y)\n\trm -f $(INSTALLDIR)/www/get_release_note_amas.asp\n\trm -f $(INSTALLDIR)/www/ajax_onboarding.asp\nendif\n"}
check("the AiMesh node firmware helpers go only where their feature is not built (web.c AiMesh_whitelists)",
      all(v in blk for v in gate.values()) and blk.count("release_note_amas.asp") == 2)
KEEP = ["QIS_wizard.htm", "PrinterServer.asp", "Advanced_TimeMachine.asp", "AiMesh_Node_FirmwareUpgrade.asp", "message.htm",
        "start_apply.htm", "start_apply2.htm", "SDN/sdn.html", "SDN/sdn.js", "SDN/mlo.html", "SDN/mlo.js", "SDN/mlo.css",
        "internet_speed.html", "require/modules/menuTree.js", "aimesh/aimesh_led_sched.html", "device-map/safely_remove_disk.asp",
        "device-map/device-map.css", "js/confirm_block.js", "SDN/Captive_Portal/FreeWiFi_template.json",
        "SDN/Captive_Portal/MessageBoard_template.json", "ajax/freewifi_tos.json", "ajax/DNS_List.json",
        "state.js", "general.js", "popup.js", "help.js", "js/httpApi.js",
        # the scripts third-party add-on pages may load (owner, stage 5: kept)
        "detect.js", "detectWAN.asp", "detect_timezone.js", "base64.js", "ajax.js", "alttxt.js", "replaceisp.js", "js/trafmon.js",
        "chart.js", "js/Chart.js", "js/chart.min.js", "js/chartjs-plugin-zoom.min.js", "js/hammer.min.js", "menu_style.css",
        "datepicker.css", "js/weekSchedule/jquery-ui.css"]
gone = [k for k in KEEP if rm(k) in blk]
check("nothing the owner kept is removed (wizard, node pages, libwebapi-named pages, add-on scripts, Network data files)", not gone, gone)
check("the wizard's mobile/ tree is untouched by the block", "/www/mobile" not in blk)

inj = code(rd(SRC, "httpd", "reaper_inject.c"))
web = rd(SRC, "httpd", "web.c")
misc = rd(SRC, "shared", "misc.c")
rmcp = rd(SRC, "rmcpd", "rmcpd.c")
check("no program reads the nvram switch reaper_inject (httpd module, web.c, libshared, the Advisor whitelist)",
      '"reaper_inject"' not in inj and '"reaper_inject"' not in code(web) and '"reaper_inject"' not in code(misc)
      and '"reaper_inject"' not in code(rmcp))
gi = misc[misc.find("int get_index_page(char *page, int size)"):]
gi = gi[:gi.find("\n}\n") + 3]
check("get_index_page(): the dashboard, no index.asp fallback", 'strlcpy(page, "Main_ReaperDash.asp", size);' in gi and '"index.asp"' not in gi, gi[:300])
url = web[web.find("useful_redirect_lists[]"):]
url = url[:url.find("};")]
check("post-login redirect list: no row for a page that no longer ships (index.asp, SDN.asp, Feedback_Info.asp, GameBoost.asp)",
      bool(url) and not any('{"%s", NULL}' % p in url for p in ("index.asp", "SDN.asp", "Feedback_Info.asp", "GameBoost.asp")))
ok_fn = web[web.find("static int reaper_apply_token_ok("):]
ok_fn = ok_fn[:ok_fn.find("\n}\n")]
check("the apply-token gate exempts AiMesh nodes only", 'if (nvram_match("re_mode", "1") || nvram_match("disable_ui", "1"))' in ok_fn)

shell = rd(www, "reaper_shell.asp")
check("shell: a malformed page name falls back to the dashboard; no run-time copy of the stock skin",
      "var DEFAULT_PAGE = 'Main_ReaperDash.asp';" in shell and "reaper_content.css'" not in shell and "link[href*=\"reaper_content\"]" not in shell)
# REAPER-ADDON-SKIN: the frame-load backstop adds the add-on sheet to a framed add-on page that lacks it (never to a Reaper page)
check("shell: a framed add-on page without reaper_addon.css gets it at load, veiled until it lands; Reaper pages never",
      "l.href='/reaper/reaper_addon.css';" in shell and "l.onload=unveil; l.onerror=unveil;" in shell
      and "!d.querySelector('meta[name=\"reaper-native\"]') && !d.querySelector('link[href*=\"reaper_addon.css\"]')" in shell
      and "/(^|\\/)user\\d+\\.asp$/i.test(p) || d.getElementById('TopBanner') || d.getElementById('mainMenu') || d.getElementById('tabMenu')" in shell)
wfs = rd(www, "Reaper_WiFiSetup.asp")
check("the first-boot Wi-Fi box carries its own copy of the skin rules it used",
      "REAPER-CUT8" in wfs and ".button{background:linear-gradient(180deg,#1a1a1f,#101014)!important" in wfs
      and "input[type=\"radio\"],input[type=\"checkbox\"]{accent-color:var(--cb-acc,#E10600)!important}" in wfs)

# httpd writes its pieces before the FIRST closing head tag - it must be the real one on every Reaper page
REWR = ["Main_ReaperDash.asp", "reaper_shell.asp", "Main_Login.asp", "Main_Password.asp", "Logout.asp", "error_page.htm",
        "blocking.asp", "message.htm"]
pages = sorted(f for f in os.listdir(www) if f.startswith("Reaper_") and f.endswith(".asp")) + REWR
badh = []
for f in pages:
    t = rd(www, f); i = t.lower().find("</head>")
    if i < 0: continue
    pre = t[:i]
    if pre.count("<!--") > pre.count("-->") or 0 <= t.lower().find("<body") < i or pre.lower().count("</head>"):
        badh.append(f)
check("every Reaper page's first closing head tag closes the real head (not inside a comment, before <body>)", not badh, badh)

ver = rd(HERE, "..", "reaper_verify.sh")
check("reaper_verify: index.asp is no longer a critical image file", bool(ver) and 'critical="reaper_shell.asp Main_ReaperDash.asp' in ver
      and "critical=\"index.asp" not in ver)
allow = rd(HERE, "handler_callers.allow")
check("handler_callers.allow: the stage 5 section is gone - its rows and hooks were removed (REAPER-UNUSED-CUT8, "
      "test_unused_handlers_cut8.py) and **.zip is filed as a FILE-ROW line",
      "REAPER-CUT8 (native-UI cutover stage 5" not in allow and "\n**.zip\tFILE-ROW (" in allow)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
