#!/usr/bin/env python3
"""Native wave (owner, 2026-10-30/31): five stock Wireless tabs rebuilt as Reaper kit pages.

WHY. The owner asked for WPS, WDS, Wireless MAC Filter, RADIUS Setting and Roaming Block List as Reaper-native pages
with every stock function kept; the stock pages keep shipping until the owner has reviewed each new page (so no
reaper_pagemap[] row and no www/Makefile removal yet - that is the follow-up change).

WHAT IT CHECKS, per page: on the kit (rp.css + rp.js, reaper-native meta, one 'use strict' closure, no jQuery /
httpApi / state.js, ASCII), listed in httpd reaper_native[] and in reaper_langcheck OUR[], the Wireless menu tab
points at it (and no longer at the stock page), it writes exactly the stock nvram keys through the stock apply path,
device names / SSIDs go in as text, and the owner-proven or stock rules it keeps (MAC Filter owns wlN_ keys - proven
on the router 2026-10-31; Accept with an empty list refused; WDS posts no Wireless Settings keys back; WPS takes only
an 8-digit PIN with a valid checksum and asks before a Reset; RADIUS shows whether each band's server is in use).
The six new strings RNW_1..6 exist in all 25 packs.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_WPS.asp")):
    print("SKIP: no router source tree with www/Reaper_WPS.asp (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

PAGES = {   # page -> (stock page it replaces, keys it must write)
    "Reaper_RoamBlock.asp": ("Advanced_Roaming_Block_Content.asp", ["rast_static_cli_enable", "_rast_static_client"]),
    "Reaper_MACFilter.asp": ("Advanced_ACL_Content.asp", ["_macmode", "_maclist_x"]),
    "Reaper_RADIUS.asp": ("Advanced_WSecurity_Content.asp", ["_radius_"]),
    "Reaper_WDS.asp": ("Advanced_WMode_Content.asp", ["_mode_x", "_wdsapply_x", "_wdslist"]),
    "Reaper_WPS.asp": ("Advanced_WWPS_Content.asp", ["wps_enable", "wps_band", "wps_sta_pin"]),
}
inj = rd("httpd", "reaper_inject.c")
nat = inj[inj.index("static const char *reaper_native[]"):]
nat = nat[:nat.index("};")]
pm = inj[inj.index("reaper_pagemap[] = {"):]
pm = pm[:pm.index("};")]
menu = rd("www", "reaper", "menu.js")
lc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reaper_langcheck.py")
lc = open(lc_path, encoding="utf-8").read() if os.path.isfile(lc_path) else ""

for page, (stock, keys) in PAGES.items():
    t = rd("www", page)
    check(page + ": on the kit, one strict closure, no jQuery/httpApi/state.js, ASCII",
          '<meta name="reaper-native" content="1">' in t and 'href="/reaper/rp.css"' in t and 'src="/reaper/rp.js"' in t
          and t.count("'use strict';") == 1 and not re.search(r'src="/(js/jquery|js/httpApi|state)\.js"', t)
          and all(ord(c) < 128 for c in t))
    check(page + ": in reaper_native[] (no stock skin injected)", '"%s"' % page in nat)
    check(page + ": in reaper_langcheck OUR[]", not lc or "'%s'" % page in lc)
    check(page + ": Wireless menu tab points here, not at " + stock, "T('%s'" % page in menu and "T('%s'" % stock not in menu)
    # 2026-11-01: the owner reviewed the five pages - the stock pages stopped shipping (test_native_wave_unship.py)
    check(page + ": stock page unshipped after the owner's review: pagemap row shipped = 0 -> this page",
          '{ "%s", "%s", 0 },' % (stock.lower(), page) in pm)
    check(page + ": writes the stock keys " + ", ".join(keys), all(k in t for k in keys))
    check(page + ": no device name or SSID through innerHTML", not re.search(r"innerHTML\s*=\s*[^;]*\b(nm|name|ssid|label)\b", t))

rb = rd("www", "Reaper_RoamBlock.asp")
check("RoamBlock: the list goes to wl0/1/2 together, restart_wireless, only when the list changed",
      "var UNITS = [0, 1, 2];" in rb and "if (listChanged()){ var s = ser(); UNITS.forEach(function(u){ ch['wl' + u + '_rast_static_client'] = s; }); }" in rb
      and "ch.rc_service = 'restart_wireless';" in rb)
check("RoamBlock: reads the union of the three radios (stock read wl0 only)", "UNITS.forEach(function(u){ macs(NV['wl' + u + '_rast_static_client'])" in rb)

acl = rd("www", "Reaper_MACFilter.asp")
check("MACFilter: Accept with an empty list is refused", "curMode(i) === 'allow' && !b.list.length" in acl and "`<#RNW_1#>`" in acl)
check("MACFilter: changing Accept/Reject keeps the list (stock emptied it)", "/* the list stays (stock emptied it) */" in acl)
check("MACFilter: the router-proven store is wlN_ (comment records the lab proof)", "PROVEN on the owner's RT-BE96U (2026-10-31, lab)" in acl)

rad = rd("www", "Reaper_RADIUS.asp")
check("RADIUS: each band says whether its server is in use (Enterprise modes)",
      "var ENT = {wpa: 1, wpa2: 1, wpawpa2: 1, wpa3: 1, wpa2wpa3: 1, 'suite-b': 1, radius: 1};" in rad and "`<#RNW_4#>` : `<#RNW_3#>`" in rad)
check("RADIUS: stock validators (IPv4 / IPv6 in router mode, port, secret without edge quotes)",
      "rp.v.ipv4(ip) && !(V6 && rp.v.ipv6(ip))" in rad and "rp.v.int(pt, 1, 65535)" in rad and "ky.charAt(0) === '\"'" in rad)

wds = rd("www", "Reaper_WDS.asp")
check("WDS: no Wireless Settings keys posted back (bw/channel/chanspec/nmode_x)",
      not re.search(r"ch\[[^\]]*_(bw|chanspec|channel|nmode_x)'", wds) and "wl_bw" not in wds)
check("WDS: survey through reaper_wifi.cgi with the http_id", "/reaper_wifi.cgi?action=svystart&unit=' + b.u + '&http_id='" in wds)
check("WDS: at most 4 peers (stock)", "var MAX = 4;" in wds)

wps = rd("www", "Reaper_WPS.asp")
check("WPS: 8-digit PIN with checksum only (httpd drops anything else)", "if (!/^\\d{8}$/.test(s)) return '';" in wps and "(i % 2 ? 1 : 3)" in wps)
check("WPS: Reset asks first", "if (!confirm(`<#WLANConfig11b_x_ResetWPS_desc#>`)) return;" in wps and "action_mode: 'wps_reset'" in wps)
check("WPS: 6 GHz left out of the WPS radios", "u < 3" in wps and "NB[u] === '2'" in wps and "NB[u] === '1'" in wps and "'4'" not in wps)
check("WPS: band changes only while WPS is off", "if (ON){ rp.pick(this, NV.wps_band_x);" in wps)
# owner, _r3: a dimmed panel let the crimson frame through (opacity on the panel), and Start sat apart from the method
check("WPS: a dimmed panel keeps its solid background (contents dimmed, not the panel)",
      ".off>*{opacity:.45}" in wps and "opacity:.45;pointer-events:none" not in wps)
check("WPS: method, PIN and Start share one row",
      re.search(r'<div class="fc radios">(?:(?!</div>).)*id="b_start"', wps, re.S) is not None)

langs = [f for f in os.listdir(os.path.join(SRC, "www")) if f.endswith(".dict") and f != "temp.dict"]
miss = [(f, k) for f in langs for k in ("RNW_1", "RNW_2", "RNW_3", "RNW_4", "RNW_5", "RNW_6")
        if not re.search(r"^%s=" % k, rd("www", f), re.M)]
check("RNW_1..6 in all %d packs" % len(langs), len(langs) == 25 and not miss, miss[:6])
counts = {f: rd("www", f).count("\n") for f in langs}
check("packs still in lockstep (same line count)", len(set(counts.values())) == 1, counts)

print("%d failure(s)" % len(fails))
for x in fails: print("  " + x)
sys.exit(1 if fails else 0)
