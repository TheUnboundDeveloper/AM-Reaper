#!/usr/bin/env python3
"""WAN 802.1Q only where the firmware can tag the WAN (field report, GT-BE98 v3.5.0, 2026-10-26).

WHY. The Internet Connection page showed the 802.1Q switch on every model. The WAN VLAN keys (wan_dot1q / wan_vid /
wan_dot1p) are in router_defaults only with RTCONFIG_MULTISERVICE_WAN, and httpd saves only names it has a default
for; rc tags the WAN only in that build too. GT-BE98, GT-BE19000, BQ16 and BQ16 Pro build without it: turning the
switch on dropped the keys, still ran the auto-WAN-port reboot, and the switch came back off with no connection.
Stock hides the row on those models; their ISP VLAN goes on LAN > IPTV (Manual Setting, Internet VID / PRIO).

WHAT IT DOES. Source checks: the page gates the switch on rc_support mswan (which rc adds only under
RTCONFIG_MULTISERVICE_WAN) and shows RINT_92 with an IPTV link instead; RINT_92 is in all 25 packs right after
RINT_91; the defaults and rc facts the gate relies on still hold.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_Internet.asp")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

t = rd("www", "Reaper_Internet.asp")
check("the 802.1Q switch needs rc_support mswan", "R.vlanp = !s46; R.vlan = R.vlanp && sup('mswan');" in t)
check("without mswan the panel shows RINT_92 and links LAN > IPTV instead of the switch",
      '<div class="sub" id="vlanalt"><#RINT_92#> <a class="link" href="/reaper_shell.asp#Reaper_IPTV.asp" target="_top">IPTV</a></div>' in t
      and "show('p_vlan', R.vlanp); show('vlansub', R.vlan); show('r_dot1q', R.vlan); show('vlanalt', R.vlanp && !R.vlan);" in t)
check("the 802.1Q keys are collected only when the switch is offered",
      "if (R.vlan){ put(c, 'wan_dot1q', 't_dot1q', chk('t_dot1q'));" in t)

www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(www) if f.endswith(".dict") and f != "temp.dict")
bad = []
for f in packs:
    lines = open(os.path.join(www, f), encoding="utf-8", errors="replace").read().split("\n")
    i = [n for n, l in enumerate(lines) if l.startswith("RINT_91=")]
    if len(i) != 1 or not lines[i[0] + 1].startswith("RINT_92=") or "LAN > IPTV" not in lines[i[0] + 1]:
        bad.append(f)
check("all 25 packs carry RINT_92 (naming LAN > IPTV) right after RINT_91", len(packs) == 25 and not bad, bad)

d = rd("shared", "defaults.c")
blocks = [m.group(1) for m in re.finditer(r'#if defined\(RTCONFIG_MULTISERVICE_WAN\)\n((?:\t\{[^\n]*\n)+)#endif', d)]
check("defaults: wan_dot1q / wan_vid / wan_dot1p exist under RTCONFIG_MULTISERVICE_WAN (the reason for the gate)",
      any(all('{ "wan_%s",' % k in b for k in ("dot1q", "vid", "dot1p")) for b in blocks), len(blocks))
i = rd("rc", "init.c")
check("rc: mswan is added to rc_support only under RTCONFIG_MULTISERVICE_WAN",
      '#ifdef RTCONFIG_MULTISERVICE_WAN\n\tadd_rc_support("mswan");\n#endif' in i)
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
