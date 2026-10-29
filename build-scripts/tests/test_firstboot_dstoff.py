#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""First boot writes the DST rule (time_zone_dstoff), not only the zone and the DST switch.

WHY THIS EXISTS. rc builds TZ as time_zone + "," + time_zone_dstoff whenever time_zone_dst=1
(rc/common.c time_zone_x_mapping). The stock default rule is M3.2.0/2,M10.2.0/2, which matches
no zone in www/ajax/tz_db.json. Stock replaced it from that table in the QIS wizard
(QIS_V3/mobile/js/plugins.js getTimeZoneOffset) and on the System page's Apply. Reaper retired
QIS in v3.1.2, so first boot runs Main_Password.asp, which set time_zone + time_zone_dst only:
every box first set up on Reaper in a DST zone kept the default rule (field 2026-10-11, US
Eastern: the clock fell back an hour on the second Sunday of October). v3.4.1 has the page take
the rule from tz_db.json, the same table and lookup the wizard used.

WHAT IT PINS (source, comments stripped): for a DST zone the first-boot block fetches
tz_db.json and writes time_zone_dstoff with the wizard's lookup (the zone's rule, else the US
rule), enabling the field only inside that callback; the hidden field exists and starts disabled
(an unread table changes nothing); every DST zone the browser-zone module can pick is a tz_db.json
key; the default rule is in no zone (why the write is needed); the System page still writes the
rule on Apply.

Exit 0 pass, 1 fail, 77 skipped (no tree: pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import json, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
FILES = {
    "pw": "www/Main_Password.asp",
    "tzdb": "www/ajax/tz_db.json",
    "tzmod": "www/require/modules/timeZone.js",
    "sys": "www/Advanced_System_Content.asp",
    "defaults": "shared/defaults.c",
}
if not SRC or not all(os.path.isfile(os.path.join(SRC, p)) for p in FILES.values()):
    skip("no router tree (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def nocomment(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return "\n".join(l for l in s.splitlines() if not l.lstrip().startswith("//"))

def norm(s): return re.sub(r"\s+", " ", s)
def rd(k): return open(os.path.join(SRC, FILES[k]), encoding="utf-8", errors="replace").read()

pw = norm(nocomment(rd("pw")))
i = pw.find("if(defaultPass){ require(['/require/modules/timeZone.js']")
check("Main_Password.asp: the first-boot time zone block is found", i >= 0)
blk = pw[i:i + 2200] if i >= 0 else ""
check("first boot fetches the bundled tz_db.json (no CDN)", '$.getJSON("/ajax/tz_db.json", function(tz_db){' in blk)
check("the fetch runs only for a DST zone", re.search(r'if\(timeZoneObj\.hasDst\)\{ .*?dstBtn\.prop\("disabled", true\); \$\.getJSON\("/ajax/tz_db\.json"', blk, re.S) is not None)
check("the rule is looked up by the zone the page writes", "var rule = tz_db[timeZoneObj.time_zone];" in blk)
check("a zone without a rule gets the wizard's fallback (the US rule), as QIS and the System page do",
      'document.form.time_zone_dstoff.value = rule ? rule : "M3.2.0/2,M11.1.0/2";' in blk)
check("time_zone_dstoff is enabled only inside the table callback (an unread table changes nothing)",
      re.search(r'function\(tz_db\)\{ var rule = [^}]*document\.form\.time_zone_dstoff\.disabled = false; \}\)\.always\(', blk) is not None)
check("Apply is held until the table answers, the fetch fails, or 8 s pass (2026-10-13: a submit that beat the fetch sent no rule)",
      'var dstBtn = $("#btn_modify input"), dstT = setTimeout(function(){ dstBtn.prop("disabled", false); }, 8000);' in blk
      and 'dstBtn.prop("disabled", true); $.getJSON(' in blk
      and '}).always(function(){ clearTimeout(dstT); dstBtn.prop("disabled", false); });' in blk)
check("the zone and DST switch are still written as before",
      "document.form.time_zone.value = timeZoneObj.time_zone;" in blk and
      "document.form.time_zone_dst.value = (timeZoneObj.hasDst) ? 1 : 0;" in blk)
check("the hidden time_zone_dstoff field exists once and starts disabled",
      pw.count('name="time_zone_dstoff"') == 1 and '<input type="hidden" name="time_zone_dstoff" value="" disabled>' in pw)
check("the field sits in the form that is submitted (after time_zone_dst)",
      0 <= pw.find('name="time_zone_dst" value="" disabled>') < pw.find('name="time_zone_dstoff"'))

tzdb = json.loads(rd("tzdb"))
check("tz_db.json loads as a zone -> rule map", isinstance(tzdb, dict) and len(tzdb) > 50, len(tzdb) if isinstance(tzdb, dict) else type(tzdb))
check("US Eastern (EST5DST) carries the US rule", tzdb.get("EST5DST") == "M3.2.0/2,M11.1.0/2", tzdb.get("EST5DST"))

mod = nocomment(rd("tzmod"))
zones = set(re.findall(r'"-?\d+(?:\.\d+)?"\s*:\s*"([A-Za-z0-9_.+-]+)"', mod))
dst_zones = sorted(z for z in zones if "DST" in z or "TDT" in z)
check("timeZone.js offers DST zones to first boot", len(dst_zones) > 5, dst_zones)
missing = [z for z in dst_zones if z not in tzdb]
check("every DST zone timeZone.js can pick is a tz_db.json key", not missing, missing)
empty = [z for z in dst_zones if z in tzdb and not tzdb[z]]
if empty:
    print("note: DST-named zones with no rule in tz_db.json (fallback applies if the browser reports DST): " + ", ".join(empty))

d = re.search(r'\{\s*"time_zone_dstoff",\s*"([^"]*)"', rd("defaults"))
default_rule = d.group(1) if d else None
check("defaults.c: time_zone_dstoff default found", default_rule is not None)
check("the default rule is in no zone (why first boot must write one)",
      default_rule is not None and default_rule not in set(tzdb.values()), default_rule)

sysp = norm(nocomment(rd("sys")))
check("System page Apply still writes time_zone_dstoff for a DST zone",
      'document.form.time_zone_dstoff.value=time_zone_s_tmp+","+time_zone_e_tmp;' in sysp)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: first boot writes the DST rule from tz_db.json")
