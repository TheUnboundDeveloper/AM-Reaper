#!/usr/bin/env python3
"""The stock pages the native-wave kit pages replace no longer ship (owner review, 2026-11-01).

WHY. The owner reviewed the seven kit pages (WPS, WDS, MAC Filter, RADIUS, Roaming Block, MLO, VLAN) on a test
image and asked for the stock versions to go, to free flash space. A page that stops shipping must also get a
reaper_pagemap[] row with shipped = 0, or its old URL (stock links, sdn.js "/MLO.asp", bookmarks) answers an
empty page instead of bouncing to the Reaper page.

WHAT IT DOES. Pins the eight shipped = 0 rows and their targets, the unconditional www/Makefile rm lines (the
older removals of these pages sit under REMOVE_AP_UI / SMART_HOME_MASTER_UI / AMAS conditions that are unset on
these builds), that MLO.asp is no longer copied in from the SDN overlay, and that the dashboard rows open the
Reaper pages.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "httpd")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
inj = rd("httpd/reaper_inject.c")
mk = rd("www/Makefile")
dash = rd("www/Main_ReaperDash.asp")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

PAGES = [  # stock file, reaper_pagemap target
    ("Advanced_WWPS_Content.asp", "Reaper_WPS.asp"),
    ("Advanced_WMode_Content.asp", "Reaper_WDS.asp"),
    ("Advanced_ACL_Content.asp", "Reaper_MACFilter.asp"),
    ("Advanced_WSecurity_Content.asp", "Reaper_RADIUS.asp"),
    ("Advanced_Roaming_Block_Content.asp", "Reaper_RoamBlock.asp"),
    ("MLO.asp", "Reaper_MLO.asp"),
    ("Advanced_VLAN_Switch_Content.asp", "Reaper_VLAN.asp"),
    ("Advanced_VLAN_Profile_Content.asp", "Reaper_VLAN.asp?tab=pf"),
]
m = re.search(r"reaper_pagemap\[\] = \{(.*?)\n\};", inj, re.S)
table = m.group(1) if m else ""
check("the page table (reaper_pagemap[]) is present", bool(m))
# the unconditional removal lines: the 2026-11-01 block, outside any ifeq/ifneq
blk = mk[mk.find("# reaper 2026-11-01 (owner review, native wave)"):]
blk = blk[:blk.find("\n\n") + 1] if "\n\n" in blk else blk
check("www/Makefile has the 2026-11-01 removal block, with no conditional inside it",
      blk.startswith("# reaper 2026-11-01") and not re.search(r"^\s*(ifeq|ifneq|ifdef|ifndef|else|endif)\b", blk, re.M))
for stock, to in PAGES:
    row = '{ "%s", "%s", 0 },' % (stock.lower(), to)
    check("%s no longer ships: pagemap row shipped = 0 -> %s" % (stock, to), row in table)
    check("%s: removed at install, unconditionally" % stock, "\trm -f $(INSTALLDIR)/www/%s\n" % stock in blk)
    check("%s: target page exists" % stock, os.path.exists(os.path.join(SRC, "www", to.split("?")[0])))
check("MLO.asp is not copied in from the SDN overlay any more",
      "cp $(TOP)/www/sysdep/FUNCTION/SDN/MLO.asp $(INSTALLDIR)/www/MLO.asp" not in mk
      and "# reaper 2026-11-01: MLO.asp is not copied any more" in mk)
check("the MLO SPA's own files still ship (the Network page's app layout opens SDN/mlo.html)",
      "ifeq ($(RTCONFIG_MLO), y)" in mk and "rm -rf $(INSTALLDIR)/www/SDN/mlo*" in mk
      and mk.find("rm -rf $(INSTALLDIR)/www/SDN/mlo*") > mk.find("ifeq ($(RTCONFIG_MLO), y)"))
check("dashboard WPS row opens Reaper_WPS.asp", 'data-go="Reaper_WPS.asp"' in dash and 'data-go="Advanced_WWPS_Content.asp"' not in dash)
check("dashboard MLO row opens Reaper_MLO.asp", 'data-go="Reaper_MLO.asp"' in dash and 'data-go="MLO.asp"' not in dash)

if fails:
    print("\n%d failure(s)" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\n0 failure(s)")
