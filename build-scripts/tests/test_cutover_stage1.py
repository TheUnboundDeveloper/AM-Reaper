#!/usr/bin/env python3
"""Native-UI cutover, stage 1 (2026-11-25): two more kit pages, dead menu tabs out, proven-dead stock files out.

  Reaper_Printer.asp       replaces PrinterServer.asp: usb_printer, restart_lpd;restart_u2ec;
  Reaper_TimeMachine.asp   replaces Advanced_TimeMachine.asp: timemachine_enable, tm_device_name, tm_vol_size
                           (GB typed, MB stored), restart_timemachine, tm_ui_setting=1 with every save
  REAPER-CUT1              the menu model no longer lists tabs that needed a feature flag no program can set
                           (proof: no supported image carries the flag's name), or a build without the Network page
  REAPER-CUT1-DEAD         stock web files nothing names stop shipping; every removed PAGE has a reaper_pagemap[] row
                           (a missing .asp bounces, it does not answer an empty page); the TrendMicro and NFS files
                           only where that option is off, with the SAME condition in www/Makefile and httpd
Kept on purpose, and checked here: the stock scripts third-party add-on pages may load, and the eleven data files
whose removal would orphan an httpd page hook (they go with their hooks at the final cutover).
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

mk = rd("www", "Makefile"); inj = rd("httpd", "reaper_inject.c"); menu = rd("www", "reaper", "menu.js")
hub = rd("www", "Reaper_USBApps.asp"); pr = rd("www", "Reaper_Printer.asp"); tm = rd("www", "Reaper_TimeMachine.asp")
m = re.search(r"reaper_pagemap\[\]\s*=\s*\{(.*?)\n\};", inj, re.S); tab = m.group(1) if m else ""
m = re.search(r"reaper_native\[\]\s*=\s*\{(.*?)\n\};", inj, re.S); native = m.group(1) if m else ""
check("httpd: reaper_pagemap[] and reaper_native[] are found", bool(tab) and bool(native))

# ---------------------------------------------------------------- the two kit pages
for name, page in (("Reaper_Printer.asp", pr), ("Reaper_TimeMachine.asp", tm)):
    check("%s: a Reaper-native kit page (meta, rp.css, rp.js, no stock script)" % name,
          '<meta name="reaper-native" content="1">' in page and 'href="/reaper/rp.css"' in page and 'src="/reaper/rp.js"' in page
          and not re.search(r'src="/(state|general|popup|help|validator)\.js"|jquery|httpApi', page))
    check("%s: plain ASCII, LF line ends" % name, all(ord(c) < 128 for c in page) and "\r" not in page)
    check("%s: dict tokens only inside backticks or markup, never in a quoted script string (rule 29)" % name,
          not re.search(r"""['"][^'"\n<>]*<#[A-Za-z0-9_]+#>[^'"\n<>]*['"]\s*[;,)+]""", "\n".join(re.findall(r"<script>(.*?)</script>", page, re.S))))
    check("%s: one closure, strict mode (no page globals)" % name, "(function(){\n'use strict';" in page)
    check("%s: httpd lists it as Reaper-native" % name, '"%s",' % name in native)
    check("%s: posts its own name as current_page / next_page" % name, page.count('value="%s"' % name) == 2)
check("Printer: one setting, the stock services", "usb_printer: chk('t_usb_printer')" in pr and "'restart_lpd;restart_u2ec;', 5" in pr)
check("Printer: nothing posted when nothing changed", "if (!n){ msg(" in pr)
check("Printer: no ASUS forwarding link is carried", "asus.com" not in pr and "asus.com" not in tm)
check("Time Machine: the three settings and the stock service",
      all(x in tm for x in ("timemachine_enable: chk('t_enable')", "tm_device_name: q('s_part').value", "tm_vol_size: sizeMb()", "'restart_timemachine', 5")))
check("Time Machine: tm_ui_setting=1 rides with every save (rc/timemachine.c takes the page's partition only then)",
      "changed.tm_ui_setting = '1';" in tm and tm.find("changed.tm_ui_setting = '1';") < tm.find("rp.post(document.form, changed"))
check("...and rc still reads tm_ui_setting that way", 'nvram_match("tm_ui_setting", "1")' in rd("rc", "timemachine.c"))
check("Time Machine: GB typed, MB stored; an untouched box keeps the stored value", "* 1024)" in tm and "if (v === SIZE0) return NV.tm_vol_size;" in tm)
check("Time Machine: the size may not exceed the partition's free space; a partition is required when on",
      "/ 1024 > max" in tm and "c.timemachine_enable === '1' && c.tm_device_name === ''" in tm)
check("Time Machine: 1 GB free or less cannot be chosen; another partition clears the size (stock rules)",
      "if (!(p.free > 1) && p.name !== saved) o.disabled = true;" in tm and "q('i_size').value = ''; sizeHint();" in tm)
check("Time Machine: disk data comes from the router's emitters inside a function (no page globals), never get_AiDisk_status",
      "rp.usbData = (function(){" in tm and "<% disk_pool_mapping_info(); %>" in tm and "get_AiDisk_status" not in tm)
check("Time Machine: every stored value is read through an encoder (a stored quote cannot end the script string)",
      "nvram_char_to_ascii(\"\",\"tm_device_name\")" in tm and not re.search(r"'<% nvram_get\(", tm))
check("Time Machine: option text is set with textContent (a partition name is never parsed as markup)", "o.textContent = '/mnt/' + p.name" in tm and "innerHTML" not in tm)

# ---------------------------------------------------------------- wiring
check("menu: the two pages are reached from the hub (INH tabs), the stock names are gone",
      "T('Reaper_Printer.asp', INH), T('Reaper_TimeMachine.asp', INH)," in menu and "PrinterServer.asp" not in menu and "Advanced_TimeMachine.asp" not in menu)
check("hub: both cards open the kit pages; the printer card shows its state",
      "{page: 'Reaper_Printer.asp'" in hub and "on: ON.prn === '1'" in hub and "{page: 'Reaper_TimeMachine.asp'" in hub
      and "PrinterServer.asp" not in hub and "Advanced_TimeMachine.asp" not in hub)
for old, new in (("printerserver.asp", "Reaper_Printer.asp"), ("advanced_timemachine.asp", "Reaper_TimeMachine.asp")):
    check("httpd: %s bounces to %s while the stock file still ships (shipped = 1)" % (old, new),
          tab.count('\t{ "%s", "%s", 1 },\n' % (old, new)) == 1 and tab.count('"%s"' % old) == 1)
check("...and www/Makefile does not remove the two stock pages yet (owner router check first)",
      "\trm -f $(INSTALLDIR)/www/PrinterServer.asp\n" not in mk and "\trm -f $(INSTALLDIR)/www/Advanced_TimeMachine.asp\n" not in mk)
# (the stock Makefile's own "rm -rf" lines for builds without USB / Time Machine are a different thing and stay)

# ---------------------------------------------------------------- dead menu tabs
DEAD_TABS = ["Guest_network.asp", "Captive_Portal.asp", "Captive_Portal_Advanced.asp", "Guest_network_fbwifi.asp",
             "AiProtection_WebProtector.asp", "AiProtection_ContentFilter.asp", "Ark_WebHistory_Content.asp", "Advanced_AiDisk_NFS.asp",
             "fileflex.asp", "Advanced_MultiSubnet_Content.asp", "Advanced_PerformanceTuning_Content.asp", "Feedback_Info.asp"]
left = [p for p in DEAD_TABS if p in menu]
check("menu: none of the 12 tabs that could never show is listed", not left, left)
check("menu: the guest menu's tab is the Network page (the kit page since stage 3)", "T('Reaper_Network.asp', sup('sdn_mwl') ? `<#Network#>` : `<#Guest_Network#>`)]}," in menu)
check("menu: Parental keeps Time Scheduling", "T('Reaper_Parental.asp', `<#Time_Scheduling#>`, sup('PARENTAL2'))]}," in menu)
for flag in ("webs_filter", "ark_iam", "nfsd", "fileflex", "tagged_based_vlan", "fanctrl", "frs_feedback", "cp_advanced", "fbwifi"):
    check("menu: no condition reads the unsettable flag %s any more" % flag, "sup('%s')" % flag not in menu)
check("rc: mtlancfg is added on every MULTILAN_CFG build, unconditionally (why the Network page is always there)",
      re.search(r'#ifdef RTCONFIG_MULTILAN_CFG\n\tadd_rc_support\("mtlancfg"\);\n#endif', rd("rc", "init.c")) is not None)
pages = sorted(set(re.findall(r"T\('([A-Za-z0-9_]+\.(?:asp|htm|html))'", menu)))
stock_left = [p for p in pages if not p.startswith(("Reaper_", "Main_ReaperDash"))]
# stage 1c (lean test_cutover_stage1c.py) converted Internet Speed and Operation Mode; stage 2 (test_cutover_stage2.py) AiMesh;
# stage 3 (test_cutover_stage3.py) the Network page
check("menu: no stock page is listed any more (every tab is a Reaper page)",
      stock_left == [], stock_left)

# ---------------------------------------------------------------- dead files
BWDPI_PAGES = {"AiProtection_HomeSecurity.asp": "Reaper_Warden.asp", "AiProtection_InfectedDevicePreventBlock.asp": "Reaper_Warden.asp",
               "AiProtection_IntrusionPreventionSystem.asp": "Reaper_Warden.asp", "AiProtection_MaliciousSitesBlocking.asp": "Reaper_Warden.asp",
               "AiProtection_WebProtector.asp": "Reaper_Parental.asp", "AdaptiveQoS_WebHistory.asp": "Reaper_Traffic.asp"}
BWDPI_DATA = ["getAiProtectionEvent.asp", "getIPSChart.asp", "getIPSDetailEvent.asp", "getIPSEvent.asp", "getNonIPSChart.asp",
              "getWebHistory.asp", "getDBList.asp"]
NFS_PAGES = {"Advanced_AiDisk_NFS.asp": "Reaper_Samba.asp"}
PLAIN_PAGES = {"Main_GameServer_Content.asp": "Reaper_NAT.asp"}
PLAIN = ["getTraffic.asp", "ajax_wl_channel.asp", "ajax_wl_ready.asp", "ajax/ajax_wl_ready.asp", "ajax_wlc_pre_auth_state.asp",
         "ajax_wlc_state.asp", "get_release_note0.asp", "getsl.asp", "ajax_openvpn_client_status.xml", "ParentalControl.css",
         "css/effect.css", "css/adaptive_mobile_WHITE.css", "RWD_UI/rwd_component_ROG.css", "RWD_UI/rwd_component_TUF.css",
         "fonts/ROG_Fonts-Regular.otf", "fonts/ROG_Fonts-Regular.woff", "aimesh/aimesh_topology_v4.css",
         "js/weekSchedule/schedule_ui_ROG.css", "calendar/fullcalendar.css"] + \
        ["images/New_ui/amesh/white_theme/" + x for x in ("cards_usage.svg", "client_control.svg", "managment_icon.svg", "port_status.svg",
         "topology_connect_quality.svg", "topology_connect_quality_mlo.svg", "topology_connect_quality_mlo_1.svg", "topology_connect_quality_moca.svg")]
KEPT = ["detect.js", "detectWAN.asp", "detect_timezone.js", "alttxt.js", "base64.js", "ajax.js", "replaceisp.js", "js/trafmon.js",
        "js/chartjs-plugin-zoom.min.js", "js/hammer.min.js", "menu_style.css",
        "js/weekSchedule/jquery-ui.css", "datepicker.css"]     # add-on pages may load them (owner, stage 5: they stay)
# the eleven hook-bound data files stage 1 kept "until the final cutover": REAPER-CUT8 (stage 5) removes them
HOOKDATA = ["getAppTraffic.asp", "getAppTraffic_Dns.asp", "getTraffic_Dns.asp", "getWanTraffic.asp", "getWanTraffic_Dns.asp",
            "ajax_gettcdata.asp", "getdhcpLeaseInfo.xml", "ajax_conntrack.asp", "ajax_conn_diag.asp", "ajax_wificlients.asp",
            "ajax_wl_edmg_channel.asp"]
rm = lambda f: "\trm -f $(INSTALLDIR)/www/%s\n" % f
a = mk.find("REAPER-CUT1-DEAD"); b = mk.find("\n# reaper", a + 1)
blk = mk[a:b + 1] if a >= 0 and b > a else ""
check("www/Makefile: the removal block is there, once", mk.count("REAPER-CUT1-DEAD") == 1 and bool(blk))
bw = "ifneq ($(RTCONFIG_BWDPI),y)\n" + "".join(rm(p) for p in BWDPI_PAGES) + "".join(rm(p) for p in BWDPI_DATA) + "endif\n"
check("www/Makefile: the TrendMicro pages and data files go only where RTCONFIG_BWDPI is off", bw in blk)
check("www/Makefile: the NFS page goes only where RTCONFIG_NFS is off", "ifneq ($(RTCONFIG_NFS),y)\n" + rm("Advanced_AiDisk_NFS.asp") + "endif\n" in blk)
check("...and the conditional lines are balanced", blk.count("ifneq (") == 2 and blk.count("endif") == 2)
tail = blk[blk.rfind("endif\n") + 6:]
miss = [p for p in list(PLAIN_PAGES) + PLAIN if rm(p) not in tail]
check("www/Makefile: the %d plain files go on every build" % (len(PLAIN_PAGES) + len(PLAIN)), not miss, miss)
check("www/Makefile: the block removes nothing else", blk.count("rm -f") == len(BWDPI_PAGES) + len(BWDPI_DATA) + 1 + len(PLAIN_PAGES) + len(PLAIN),
      blk.count("rm -f"))
gone = [k for k in KEPT if rm(k) in mk]
check("www/Makefile: the add-on scripts are NOT removed (owner, stage 5)", not gone, gone)
c8 = mk[mk.find("REAPER-CUT8-STOCK"):mk.find("# End REAPER-CUT8-STOCK")]
check("www/Makefile: the hook-bound data files go in stage 5 (REAPER-CUT8-STOCK), not in the stage 1 block",
      all(rm(k) in c8 and rm(k) not in blk for k in HOOKDATA), [k for k in HOOKDATA if rm(k) not in c8])

def rows_in(cond):
    mm = re.search(r"#ifndef %s\n((?:\t\{ [^\n]*\n)+)#endif\n" % cond, tab[tab.find("REAPER-CUT1-DEAD"):])
    return mm.group(1) if mm else ""
for cond, group in (("RTCONFIG_BWDPI", BWDPI_PAGES), ("RTCONFIG_NFS", NFS_PAGES)):
    sec = rows_in(cond)
    for p, tgt in group.items():
        check("httpd: %s bounces to %s, only where %s is off" % (p, tgt, cond),
              '\t{ "%s", "%s", 0 },\n' % (p.lower(), tgt) in sec and tab.count('"%s"' % p.lower()) == 1)
for p, tgt in PLAIN_PAGES.items():
    check("httpd: %s bounces to %s" % (p, tgt), tab.count('\t{ "%s", "%s", 0 },\n' % (p.lower(), tgt)) == 1 and tab.count('"%s"' % p.lower()) == 1)
for tgt in sorted(set(list(BWDPI_PAGES.values()) + list(NFS_PAGES.values()) + list(PLAIN_PAGES.values()))):
    check("...and %s ships in www" % tgt, os.path.isfile(os.path.join(SRC, "www", tgt)))
# nothing that still ships names a removed file (the proof, kept as a guard): Reaper pages, the kit, the pages left to convert
WWW = os.path.join(SRC, "www")
live = [f for f in os.listdir(WWW) if f.startswith(("Reaper_", "reaper_")) or f in ("Main_ReaperDash.asp", "Main_Login.asp", "AiMesh.asp",
        "Advanced_OperationMode_Content.asp", "AdaptiveQoS_InternetSpeed.asp", "internet_speed.html", "QIS_wizard.htm", "start_apply.htm")]
live = [os.path.join(WWW, f) for f in live] + [os.path.join(WWW, "reaper", f) for f in os.listdir(os.path.join(WWW, "reaper"))]
live += [os.path.join(dp, f) for sub in ("aimesh", os.path.join("sysdep", "FUNCTION", "SDN"), "mobile") for dp, _, fn in os.walk(os.path.join(WWW, sub)) for f in fn
         if f.endswith((".asp", ".html", ".htm", ".js"))]
names = [os.path.basename(p) for p in list(BWDPI_PAGES) + BWDPI_DATA + list(NFS_PAGES) + list(PLAIN_PAGES) + PLAIN if not p.startswith("images/")]
# run-time name builders in the live pages: the theme is fixed to "" on Reaper (lean test_aimesh_network_css.py), so
# "..._" + theme + ".css" reaches no themed file; the two ROG / TUF component sheets and schedule_ui_ROG.css are named
# only that way
for f in ("AiMesh.asp", os.path.join("sysdep", "FUNCTION", "SDN", "SDN", "sdn.html"), os.path.join("sysdep", "FUNCTION", "SDN", "SDN", "mlo.html")):
    check("%s: the theme is the empty string (no themed sheet can be asked for)" % f.replace(os.sep, "/"), 'var theme = "";' in rd("www", f))
hit = []
for p in live:
    if os.path.basename(p) in names: continue
    try: t = open(p, encoding="utf-8", errors="replace").read()
    except Exception: continue
    for n in names:
        if re.search(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9_])", t): hit.append("%s names %s" % (os.path.relpath(p, WWW), n))
check("no live page or script names a removed file (%d files read)" % len(live), not hit, hit[:8])

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
