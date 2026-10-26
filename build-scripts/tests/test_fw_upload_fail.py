#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A refused firmware upload says so (httpd/web.c do_upgrade_cgi, www/Reaper_Firmware.asp, 2026-10-21).

WHY THIS EXISTS. Test images _r8.._r10 carried 31 editor backup copies swept in from www/ and grew the
rootfs (73.3 MB) past the RT-BE96U flash slot (69.5 MB). The flasher refused them, httpd answered the
stock UpdateError_reboot.asp and rebooted anyway, the Reaper Firmware page read that reboot as success
and sent the owner to the login page of the OLD firmware - twice, with no message anywhere.

WHAT IT DOES. Pins the three surfaces: httpd logs the refusal (the /jffs syslog persists) and keeps an
nvram note that the next successful upgrade clears; the page reads httpd's answer for the error page
before it trusts liveness, and shows the last refusal on every visit; the four strings exist in all 25
packs in lockstep. Exit 0 pass, 1 fail, 77 skipped.
"""
import os, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    print("SKIP: no router source tree"); sys.exit(77)
def read(rel): return open(os.path.join(SRC, rel), encoding="utf-8", errors="replace").read()
web, page, defaults = read("httpd/web.c"), read("www/Reaper_Firmware.asp"), read("shared/defaults.c")

fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

check("httpd: the flasher's refusal is logged with its code where the console line was lost",
      'logmessage("httpd", "firmware upgrade: the flasher refused the image (code %d) - it was not written' in web)
cgi = web[web.index("static void\ndo_upgrade_cgi(") if "static void\ndo_upgrade_cgi(" in web else web.index("do_upgrade_cgi("):]
cgi = cgi[:cgi.index("\n}\n") + 3]
check("httpd: a refused image logs FAILED with the reason and whether the router restarts",
      'logmessage("httpd", "firmware upgrade FAILED - %s; the router %s its current firmware"' in cgi
      and '"the image was not written (too large for the flash slot, or a damaged file)"' in cgi)
check("httpd: the refusal is kept in nvram (committed) so it outlives the reboot",
      'nvram_set("reaper_upg_fail", note);\n\t\t\tnvram_commit();' in cgi and 'snprintf(note, sizeof(note), "%ld %d", (long)time(NULL), upgrade_err == 2 ? 2 : 1);' in cgi)
check("httpd: a successful write retires the note before Updating.asp",
      cgi.index('nvram_set("reaper_upg_fail", "");') < cgi.index('websApply(stream, "Updating.asp");'))
check("defaults: reaper_upg_fail exists, empty", '{ "reaper_upg_fail", "", CKN_STR32' in defaults)
check("page: httpd's answer is read for the error page before liveness decides",
      "if(String(x.responseText || '').indexOf('UpdateError') >= 0){ upRefused(); return; }" in page
      and page.index("x.onload = function(){") < page.index("x.onerror = x.ontimeout = handed;"))
check("page: a refusal shows the failure and frees the page (no 'rebooting' veil)",
      "var upRefused = once(function(){" in page and "veilFail(esc(`<#RFWU_58#>`), '');" in page)
check("page: the last refusal is shown on every visit from the nvram note",
      "nvGet('reaper_upg_fail', function(v){" in page and "showLastRefusal();" in page
      and "`<#RFWU_59#>`.replace('%1', when).replace('%2', why)" in page)
check("page: pure ASCII", all(ord(c) < 128 for c in page))
LANGS = "BR CN CZ DA DE EN ES FI FR HU IT JP KR MS NL NO PL RO RU SL SV TH TR TW UK".split()
NEW = ["RFWU_58", "RFWU_59", "RFWU_60", "RFWU_61"]
orders = set(); okk = True
for lg in LANGS:
    keys = [l.split("=", 1)[0] for l in read("www/%s.dict" % lg).splitlines() if "=" in l]
    if [k for k in keys if k in NEW] != NEW: okk = False
    orders.add(tuple(keys))
check("dicts: RFWU_58..61 in all 25 packs, same order, lockstep", okk and len(orders) == 1)

if fails:
    print("\n%d FAILED" % len(fails)); sys.exit(1)
print("\nall checks passed")
