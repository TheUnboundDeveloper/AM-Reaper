#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every stock page that no Reaper image installs has a row in httpd's page table.

WHY THIS EXISTS. A stock page that is not shipped answers an EMPTY page when an old link, a bookmark or a stock
script asks for it, unless httpd/reaper_inject.c reaper_pagemap[] carries a row that sends the request to a Reaper
page. The per-model review of 2026-11-20 compared 12 release images with the stock firmware and found 24 such pages
without a row; 21 get one - the bounce stub answers only for a missing .asp, so the two .html
files (adguard_dns.html, phone_as_modem_instructions.html) stay a plain 404, and cloud_status.asp (an AiCloud data page) gets none
because its name contains the removed page hook "cloud_status", whose absence from httpd the image check proves (v3.8.4, tag REAPER-GONE-V384).

WHAT IT DOES. Pins the 21 rows (not shipped, a target that exists), the build conditions of the four captive-portal
ones (a row is also fed to the bounce script of every served stock page, so a page that CAN ship on some build must
sit behind the same condition as its removal in www/Makefile), and that none of them is a page the source would
install unconditionally. Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
INJ = os.path.join(SRC, "httpd", "reaper_inject.c")
WWW = os.path.join(SRC, "www")
if not SRC or not os.path.isfile(INJ) or not os.path.isdir(WWW):
    print("SKIP: no router source tree with httpd/reaper_inject.c and www/"); sys.exit(77)
inj = open(INJ, encoding="utf-8", errors="replace").read()
mk = open(os.path.join(WWW, "Makefile"), encoding="utf-8", errors="replace").read()

fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

WANT = {
    "adaptiveqos_rog.asp": "Reaper_QoS.asp",
    "advanced_applist_content.asp": "Reaper_USBApps.asp", "advanced_aidisk_webdav.asp": "Reaper_USBApps.asp",
    "apps_test.asp": "Reaper_USBApps.asp", "getsharelink.asp": "Reaper_USBApps.asp",
    "advanced_notification_content.asp": "Main_ReaperDash.asp", "advanced_privacy.asp": "Main_ReaperDash.asp",
    "advanced_web_account_binding.asp": "Main_ReaperDash.asp", "aiprotection_group.asp": "Main_ReaperDash.asp",
    "aiprotection_homeprotection.asp": "Main_ReaperDash.asp", "gameboost_rog.asp": "Main_ReaperDash.asp",
    "gamedashboard.asp": "Main_ReaperDash.asp", "gearaccelerator.asp": "Main_ReaperDash.asp",
    "uuaccelerator.asp": "Main_ReaperDash.asp", "wifi_insight.asp": "Main_ReaperDash.asp",
    "adguard_dns.asp": "Reaper_DNS.asp", "ajax_wanlink.asp": "Reaper_Internet.asp",
    "captive_portal_preview.asp": "Reaper_Network.asp", "captive_portal_advanced_preview.asp": "Reaper_Network.asp",
    "ajax_captive_portal.asp": "Reaper_Network.asp", "ajax_captive_portal_log.asp": "Reaper_Network.asp",
}
CP = ("captive_portal_preview.asp", "captive_portal_advanced_preview.asp", "ajax_captive_portal.asp", "ajax_captive_portal_log.asp")

m = re.search(r"reaper_pagemap\[\] = \{(.*?)\n\};", inj, re.S)
tab = m.group(1) if m else ""
check("the page table (reaper_pagemap[]) is present", bool(tab))
rows = re.findall(r'\{ "([a-z0-9_.-]+)",\s*"([^"]+)",\s*([01]) \}', tab)
names = [r[0] for r in rows]
check("no page has two rows", len(names) == len(set(names)))
d = {r[0]: (r[1], r[2]) for r in rows}
miss = [n for n in WANT if n not in d]
check("the 21 pages have a row" + (" - missing " + ", ".join(miss) if miss else ""), not miss)
wrong = [n for n in WANT if n in d and d[n] != (WANT[n], "0")]
check("each is marked not shipped and goes to its Reaper page" + (" - " + ", ".join(wrong) if wrong else ""), not wrong)
check("the tag REAPER-GONE-V384 marks the block", tab.count("REAPER-GONE-V384") >= 3)
check("no row re-introduces the name of a removed page hook into httpd (cloud_status)", "cloud_status" not in tab)
check("21 pages, every name a lower-case .asp (the stub does not run for other files)", len(WANT) == 21 and all(n == n.lower() and n.endswith(".asp") for n in WANT))

# targets exist (SDN.asp lives in the Network-page overlay)
def exists(t):
    t = t.split("?")[0]
    return os.path.isfile(os.path.join(WWW, t)) or os.path.isfile(os.path.join(WWW, "sysdep", "FUNCTION", "SDN", t))
bad = sorted({t for t, _ in d.values() if not exists(t)})
check("every target in the table is a page in the source" + (" - " + ", ".join(bad) if bad else ""), not bad)

# the build conditions of the captive-portal rows
def cond_stack(text, needle):
    st = []
    for l in text.split("\n"):
        s = l.strip()
        if needle in l: return list(st)
        if re.match(r"#\s*(ifdef|ifndef|if)\b", s): st.append(s)
        elif re.match(r"#\s*endif\b", s) and st: st.pop()
    return None
cs = {n: cond_stack(tab, '"%s"' % n) for n in CP}
check("the editor's preview page sits behind RTCONFIG_MULTILAN_CFG only, as the editor does",
      cs[CP[0]] == ["#ifdef RTCONFIG_MULTILAN_CFG"] and cond_stack(tab, '"captive_portal.asp"') == ["#ifdef RTCONFIG_MULTILAN_CFG"])
check("the Advanced preview and the two portal data pages sit behind MULTILAN_CFG and not CP_ADVANCED, as their removal does",
      all(cs[n] == ["#ifdef RTCONFIG_MULTILAN_CFG", "#ifndef RTCONFIG_CP_ADVANCED"] for n in CP[1:]))
blk = mk[mk.find("ifeq ($(RTCONFIG_MULTILAN_CFG), y)\n\trm -f $(INSTALLDIR)/www/Captive_Portal.asp"):]
blk = blk[:blk.find("\nendif\nendif") if "\nendif\nendif" in blk else 1200]
check("www/Makefile removes the four under the same conditions",
      "Captive_Portal_Preview.asp" in blk.split("ifneq ($(RTCONFIG_CP_ADVANCED), y)")[0]
      and all(x in blk.split("ifneq ($(RTCONFIG_CP_ADVANCED), y)")[-1] for x in
              ("Captive_Portal_Advanced_Preview.asp", "ajax_captive_portal.asp", "ajax_captive_portal_log.asp")))

# none of the other 20 is a page the source installs unconditionally
top = {f.lower(): f for f in os.listdir(WWW)}
live = []
for n in WANT:
    if n in CP or n not in top: continue
    f = top[n]
    if not re.search(r"rm -r?f [^\n]*\$\(INSTALLDIR\)/www/%s\b" % re.escape(f), mk): live.append(f)
check("each of the other pages is either absent from the source or removed by www/Makefile" + (" - " + ", ".join(live) if live else ""), not live)

# REAPER-GONE-JFFSUP (owner 2026-11-24): UploadingJFFS.asp only reloaded the page after a /jffs restore upload, and
# that upload (jffsupload.cgi) left in v3.8.4 - the page goes with it, on every build, and its old address bounces.
check("UploadingJFFS.asp: a row to the Backup page, marked not shipped", d.get("uploadingjffs.asp") == ("Reaper_Backup.asp", "0"))
check("UploadingJFFS.asp: its row sits outside any build condition", cond_stack(tab, '"uploadingjffs.asp"') == [])
mpos = mk.find("\trm -f $(INSTALLDIR)/www/UploadingJFFS.asp\n")
depth = 0
for ln in mk[:max(mpos, 0)].split("\n"):
    if re.match(r"(ifeq|ifneq|ifdef|ifndef)\b", ln): depth += 1
    elif re.match(r"endif\b", ln) and depth: depth -= 1
check("UploadingJFFS.asp: www/Makefile removes it, outside any build condition", mpos >= 0 and depth == 0)
web = open(os.path.join(SRC, "httpd", "web.c"), encoding="utf-8", errors="replace").read()
check("the upload it landed from is gone from httpd (no \"jffsupload.cgi\" handler entry)", '"jffsupload.cgi"' not in web)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
