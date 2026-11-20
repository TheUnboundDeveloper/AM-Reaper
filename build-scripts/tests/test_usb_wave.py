#!/usr/bin/env python3
"""USB wave (owner, 2026-11-03): four USB Application tabs rebuilt as Reaper kit pages.

WHY. The owner asked for USB Application, Media Server, Network Place (Samba) Share and FTP Share as Reaper-native
pages. After the owner's check on the router (2026-11-03) the stock pages no longer ship: www/Makefile removes each,
and a reaper_pagemap[] row (shipped 0) bounces its old URL to the kit page.

WHAT IT CHECKS: each page is on the kit (rp.css + rp.js, reaper-native meta, a 'use strict' closure, ASCII, no
jQuery / httpApi / state.js), listed in httpd reaper_native[] and in reaper_langcheck OUR[], the USB Application menu
points at it (no tab names the stock page any more), it writes the stock keys through the stock handlers (Samba:
restart_ftpsamba;restart_dnsmasq and switch_share_mode.asp; FTP: restart_firewall when the on/off or WAN switch
changed, TLS off before anonymous on; Media: restart_media, the 128-character list limit), the shared manager
(rp.share.js) posts the stock /aidisk/ handlers, asks for DELETE before a folder delete and never runs the raw-name
emitter get_AiDisk_status (a folder named with a quote broke the stock page), the stock pages are gone, and the
33 new strings RUSB_1..33 exist in all 25 packs.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_Samba.asp")):
    print("SKIP: no router source tree with www/Reaper_Samba.asp (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

PAGES = {   # page -> (stock page it replaces, what it must carry)
    "Reaper_USBApps.asp": ("APP_Installation.asp", ["Reaper_Samba.asp", "Reaper_FTP.asp", "Reaper_MediaServer.asp", "PrinterServer.asp",
                                                   "Advanced_TimeMachine.asp", "sup('printer') && !sup('noprinter')", "sup('timemachine')"]),
    "Reaper_MediaServer.asp": ("mediaserver.asp", ["dms_dir_x", "dms_dir_type_x", "dms_dir_manual", "daapd_enable", "rc_service = 'restart_media'",
                                                  "MAXLEN = 128", "/ajax_dms_status.asp"]),
    "Reaper_Samba.asp": ("Advanced_AiDisk_samba.asp", ["computer_name", "st_samba_workgroup", "smbd_protocol", "smbd_simpler_naming", "smbd_master",
                                                      "smbd_wins", "st_max_user", "'restart_ftpsamba;restart_dnsmasq'", "switch_share_mode.asp"]),
    "Reaper_FTP.asp": ("Advanced_AiDisk_ftp.asp", ["enable_ftp", "ftp_wanac", "ftp_tls", "ftp_lang", "st_max_user", "';restart_firewall'",
                                                  "switch_share_mode.asp", "usb_tls_conflict"]),
}
inj = rd("httpd", "reaper_inject.c")
nat = inj[inj.index("static const char *reaper_native[]"):]
nat = nat[:nat.index("};")]
pm = inj[inj.index("reaper_pagemap[] = {"):]
pm = pm[:pm.index("};")]
menu = rd("www", "reaper", "menu.js")
app = menu[menu.index("index: 'menu_APP'"):]
app = app[:app.index("]},")]
lc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reaper_langcheck.py")
lc = open(lc_path, encoding="utf-8").read() if os.path.isfile(lc_path) else ""
mk = rd("www", "Makefile") if os.path.isfile(os.path.join(SRC, "www", "Makefile")) else ""

for page, (stock, must) in PAGES.items():
    t = rd("www", page)
    check(page + ": on the kit", '<meta name="reaper-native" content="1">' in t and "/reaper/rp.css" in t and "/reaper/rp.js" in t and "'use strict'" in t)
    check(page + ": loads no stock script stack", not re.search(r"<script[^>]+src=\"[^\"]*(jquery|httpApi|state\.js|general\.js|disk_functions\.js|validator\.js)", t, re.I))
    check(page + ": ASCII only", all(ord(c) < 128 for c in t))
    check(page + ": in reaper_native[]", '"%s"' % page in nat)
    check(page + ": in reaper_langcheck OUR[]", "'%s'" % page in lc, lc_path)
    check(page + ": the menu tab points at it", "T('%s'," % page in app)
    check(page + ": no menu tab names the stock page", "T('%s'" % stock not in app)
    check(page + ": the stock page no longer ships (www/Makefile removes it)", "rm -f $(INSTALLDIR)/www/%s\n" % stock in mk, stock)
    check(page + ": its old URL bounces here (reaper_pagemap[] row, shipped 0)", '{ "%s", "%s", 0 }' % (stock.lower(), page) in pm, stock)
    missing = [m for m in must if m not in t]
    check(page + ": writes / gates as stock", not missing, missing)
    check(page + ": never runs get_AiDisk_status (raw folder names in script)", "get_AiDisk_status" not in t)
    check(page + ": nvram reads in script use nvram_get_js", not re.search(r"'<% nvram_get\(", t))

sh = rd("www", "reaper", "rp.share.js")
check("rp_share: one 'use strict' closure under rp.share", "'use strict'" in sh and "rp.share = {}" in sh)
check("rp_share: posts the stock /aidisk/ handlers", all(("'%s'" % h) in sh for h in ("create_account.asp", "modify_account.asp", "delete_account.asp",
      "create_sharedfolder.asp", "modify_sharedfolder.asp", "delete_sharedfolder.asp", "set_account_permission.asp")))
check("rp_share: a folder delete asks for DELETE typed (it removes the files too)", "typed: 'DELETE'" in sh)
check("rp_share: rights for the escaped account name, the raw (html-decoded) folder name", "account: a.esc" in sh and "S.unhtml(x[0])" in sh)
check("rp_share: the first account (router login) cannot be modified or deleted", "a && !a.admin" in sh)
check("rp_share: ASCII only", all(ord(c) < 128 for c in sh))
check("Samba / FTP / Media load rp.share.js and disk_msg.js",
      all("/reaper/rp.share.js" in rd("www", p) and "/disk_msg.js" in rd("www", p) for p in ("Reaper_Samba.asp", "Reaper_FTP.asp", "Reaper_MediaServer.asp")))

LANGS = "BR CN CZ DA DE EN ES FI FR HU IT JP KR MS NL NO PL RO RU SL SV TH TR TW UK".split()
want = ["RUSB_%d" % i for i in range(1, 34)]
miss = {}
for L in LANGS:
    d = rd("www", L + ".dict")
    m = [k for k in want if not re.search(r"^%s=" % k, d, re.M)]
    if m: miss[L] = m
check("RUSB_1..33 in all 25 packs", not miss, miss)
en = rd("www", "EN.dict")
check("the folder-delete warning names the word to type", re.search(r"^RUSB_25=.*\bDELETE\b", en, re.M) is not None)
used = set()
for p in list(PAGES) + ["reaper/rp.share.js"]:
    used |= set(re.findall(r"<#([A-Za-z0-9_]+)#>", rd("www", *p.split("/"))))
nodef = sorted(k for k in used if not re.search(r"^%s=" % re.escape(k), en, re.M))
check("every token the wave uses exists in EN.dict", not nodef, nodef)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed: four USB kit pages, stock handlers, stock pages unshipped and bounced, 25 packs")
