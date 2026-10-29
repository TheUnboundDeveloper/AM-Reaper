#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Roaming Assistant can be switched off from Wireless > Settings (www/Reaper_WiFiSettings.asp).

WHY THIS EXISTS. Field report 2026-10-21 (GT-BE98, v3.4.8): Roaming Assistant could not be disabled -
"the Apply button is inactive", while other changes applied. The band's Enabled/Disabled select has
no nvram name of its own: on Disabled it writes 0 into the wlN_user_rssi number input and HIDES that
input's wrapper (.rssiNum). The change counter counted it and lit Apply, but the apply loop skipped
every control inside [hidden], so nothing was posted and Apply returned silently. Broken since the
page was built (v3.2.2).

WHAT IT DOES. Pins the coupling on the page source: the Disabled handler writes 0 and hides .rssiNum;
the apply loop exempts exactly a hidden .rssiNum (and still skips other hidden controls, and a
.rssiNum inside another hidden element); the range check lets 0 through for user_rssi; the apply
restarts wireless (stock restart_wireless stops and starts roamast, which reads wlN_user_rssi).
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "www", "Reaper_WiFiSettings.asp")
if not SRC or not os.path.isfile(P):
    print("SKIP: no router source tree with www/Reaper_WiFiSettings.asp"); sys.exit(77)
page = open(P, encoding="utf-8", errors="replace").read()
svc = open(os.path.join(SRC, "rc", "services.c"), encoding="utf-8", errors="replace").read()

fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

check("the Disabled choice writes 0 into the band's user_rssi input and hides its wrapper",
      'if(el.value==="0"){ inp.value="0"; wrap.hidden=true; }' in page)
m = re.search(r'btn\.addEventListener\("click",function\(\)\{(.*?)\n  \}\);', page, re.S)
apply = m.group(1) if m else ""
check("the apply handler is found", bool(apply))
loop = apply[apply.find('var reboot=false, postedG={};'):]
loop = loop[:loop.find("add(nm,v);")]
check("the apply loop exempts a hidden .rssiNum - the 0 that means off is posted",
      'var hid=el.closest("[hidden]");' in loop
      and 'if(hid && !(hid.classList.contains("rssiNum") && !hid.parentElement.closest("[hidden]"))) return;' in loop)
check("...and no longer skips every hidden control outright", 'if(el.closest("[hidden]")) return;' not in loop)
check("the range check lets 0 through for user_rssi (min is -90)",
      'if(v===0 && el.getAttribute("data-name").slice(-10)==="_user_rssi") return;' in apply)
check("a wireless apply restarts wireless", 'f.action_script.value="restart_wireless"' in apply)
check("restart_wireless restarts roamast (stock), which reads wlN_user_rssi at start",
      svc.count("stop_roamast();") >= 2 and svc.count("start_roamast();") >= 2)

# the once-over that followed (2026-10-21): the counter and Apply must agree elsewhere too
rc = re.search(r'function recount\(\)\{(.*?)\n  \}\n', page, re.S)
rc = rc.group(1) if rc else ""
check("recount() counts a Time Scheduling grid edit itself (a later edit can no longer drop it and grey Apply)",
      'RADIOS.forEach(function(r){ var t=q(r.unit,"timesched"); if(t&&schedDirty(r.unit)&&getVal(t)===t._base) n++; });' in rc
      # review 2026-10-24 (Q-C2-13): the one-line recountSched() wrapper went; the grid's Done calls recount() itself
      and 'document.getElementById("schedModal").classList.remove("show"); recount();' in page and "recountSched" not in page)
check("Apply posts a grid edit (schedDirty -> wlN_sched_v2)", 'if(schedDirty(u)) add(r.ifn+"_sched_v2",SCHED[u]);' in apply)
check("one key shown in two columns (amas_chanfit) counts as one change, as Apply posts it once",
      'if(d){ var gg=el.getAttribute("data-g"); if(!gg||!cntG[gg]){ n++; if(gg) cntG[gg]=1; } }' in rc
      and 'if(g){ if(postedG[g]) return;' in apply)
check("render() runs after SCHED exists (recount reads it on first paint)",
      page.find("var SCHED={}") != -1 and page.rfind("\n  render();") > page.find("var SCHED={}"))

if fails:
    print("\n%d FAILED" % len(fails)); sys.exit(1)
print("\nall checks passed")
