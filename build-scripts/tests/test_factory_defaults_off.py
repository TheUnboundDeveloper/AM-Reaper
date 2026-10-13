#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Factory defaults that must stay off or fixed (owner, 2026-10-12).

WHY THIS EXISTS. Two owner rulings on 2026-10-12. (1) A new or factory-reset router never joins the
WAN port to the LAN: stock auto-WAN-port (autowan_enable=1) was the factory default and can only find
the WAN by bridging every candidate port into br0 (rc/reaper_wanpin.c), so the factory default is now
a fixed WAN port - autowan_enable=0 with wan_ifname_x = the port labelled WAN, eth0 on every model in
the fleet. Auto stays a choice on the WAN Ports page. (2) Every switch on the DNS Failover page's
DNSMASQ row starts off at factory. Both are defaults.c-only changes: an upgraded router keeps its
stored values (the no-overwrite rule), so this suite also proves that no boot or page-serving code
writes these keys. The property is easy to lose: a merge from upstream brings "1" back for
autowan_enable with a green build, and a factory-fresh router then bridges its ISP port again.

WHAT IT DOES.
  - pins the seven defaults in shared/defaults.c (comments stripped first, so a commented-out entry
    cannot satisfy a check) and that autowan_enable sits under the stock RTCONFIG_AUTO_WANPORT gate;
  - pins wan_ifname_x=eth0 on the model list that names RTBE96U and checks every fleet model is on it;
  - no rc/httpd code sets or unsets any of the seven keys;
  - the lldpd bind list skips a WAN interface in router mode outside an Auto search (the code path a
    factory-fresh router now lands in; stock bound lldpd to the ISP-facing port there);
  - the pin module's header states the new default; the build marker for the lldpd skip is pinned.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as argv[1] or
REAPER_ROUTER_SRC).
"""
import glob, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "defaults.c")):
    skip("no router source tree with shared/defaults.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

HERE = os.path.dirname(os.path.abspath(__file__))
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

# ------------------------------------------------------------------ the seven defaults
df = read("shared/defaults.c")
code = re.sub(r"/\*.*?\*/", "", df, flags=re.S)
code = re.sub(r"//[^\n]*", "", code)

def defaults_of(key):
    return re.findall(r'\{\s*"%s"\s*,\s*"([^"]*)"' % re.escape(key), code)

OFF = ["autowan_enable", "reaper_landns_enable", "reaper_dns_strict", "reaper_dns_nocache",
       "reaper_dns_revshare", "reaper_dns_v6names", "reaper_dot_strict"]
for k in OFF:
    vals = defaults_of(k)
    check("%s defaults to 0, one entry" % k, vals == ["0"], vals)

i = code.find('{ "autowan_enable", "0"')
check("autowan_enable entry sits under #ifdef RTCONFIG_AUTO_WANPORT",
      i > 0 and code.rfind("#ifdef RTCONFIG_AUTO_WANPORT", 0, i) > code.rfind("#endif", 0, i))

m = re.search(r'#if[^\n]*defined\(RTBE96U\)[^\n]*\n\s*\{\s*"wan_ifname_x"\s*,\s*"([^"]*)"', code)
check("wan_ifname_x defaults to eth0 on the model list that names RTBE96U",
      m is not None and m.group(1) == "eth0", m.group(1) if m else "entry not found")
for model in ("GTBE98", "GTBE98_PRO", "RTBE88U", "RTBE86U", "GTBE19000", "BQ16", "BQ16_PRO"):
    check("that wan_ifname_x entry covers %s" % model, m is not None and ("defined(%s)" % model) in m.group(0))

# ------------------------------------------------------------------ an upgrade keeps the user's value
writers = []
for path in sorted(glob.glob(os.path.join(SRC, "rc", "*.c")) + glob.glob(os.path.join(SRC, "httpd", "*.c"))):
    s = open(path, encoding="utf-8", errors="surrogateescape").read()
    for k in OFF:
        if re.search(r'nvram_(set|set_int|unset)\s*\(\s*"%s"' % re.escape(k), s):
            writers.append((os.path.relpath(path, SRC), k))
check("no rc/httpd code writes any of the seven keys (defaults.c only)", not writers, writers)

# ------------------------------------------------------------------ lldpd on the fixed-port path
svc = read("rc/services.c")
j = svc.find('foreach (word, nvram_safe_get("autowan_ifnames"), next) {')
blk = svc[j:j + 1500] if j > 0 else ""
check("lldpd bind list skips a WAN interface in router mode outside an Auto search",
      "is_router_mode() && is_auto_wanport_enabled() != 1" in blk
      and 'find_in_list(nvram_safe_get("wan_ifnames"), word)' in blk
      and "skip binding the fixed WAN %s for lldpd" in blk)
check("the stock skip of the Auto-detected port is kept",
      'is_auto_wanport_enabled() == 2 && !strcmp(autowan_detected_if, word)' in blk)

pin = read("rc/reaper_wanpin.c")
check("reaper_wanpin.c header states the fixed-port factory default", "factory default is a fixed WAN port" in pin)

mkr = open(os.path.join(HERE, "..", "verify_markers.txt"), encoding="utf-8").read()
check("build marker for the lldpd skip", "sbin/rc|skip binding the fixed WAN|1" in mkr)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
