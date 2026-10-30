#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The speed test runs ASUS's 102_40585 Ookla setup on both lines (2026-10-29).

WHY THIS EXISTS. ASUS retired the old Ookla embed key on 2026-10-01 (FAQ 1057454). The 102.10 line
took the new setup with the 40585 merge (Asuswrt-Merlin 0c5d53820c7); the 102.8 line kept the
retired key hard-coded in web.c until it was ported the same day. The new setup picks the key by
platform (shared/ookla_utils.c ookla_get_cmd_profile: an HND router outside the Wi-Fi 8 SDK gets
the AXHND_A7 key), runs the quota (100 free tests, then 3 per 24 h, after QIS/FRS on BE_4916;
counted by the ookla_quota_mon applet) and shows the page's quota notice; 40585 pairs it with
engine 3.8.0 (build 235) (OOKLA-38000). A later merge or port that brings back any of the old pieces
puts the box on a key ASUS no longer serves.

WHAT IT DOES. Reads the router source (argv[1] or REAPER_ROUTER_SRC) and checks every piece, plus
that Reaper's own launch path (ookla_run, the kept stderr) survived.
Exit 0 pass, 1 fail, 77 skipped."""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)
def rd(rel):
    p = os.path.join(SRC, rel)
    return open(p, encoding="utf-8", errors="surrogateescape").read() if os.path.isfile(p) else ""

web, utils, hdr = rd("httpd/web.c"), rd("shared/ookla_utils.c"), rd("shared/ookla_common.h")
check("web.c no longer hard-codes the retired key", "4tiouex6gsnzq55o" not in web)
check("web.c takes the key from ookla_get_cmd_profile()", "profile = ookla_get_cmd_profile();" in web
      and "config = profile.config;" in web)
check("web.c defines no Ookla constants of its own (ookla_common.h is the one source)",
      "#define OOKLA_FOLDER" not in web and "#define OOKLA_RESULT" not in web)
check("the quota is checked before a test and reported to the page",
      "ookla_check_quota(void)" in web and "ej_ookla_speedtest_get_quota(int eid" in web
      and '{ "ookla_speedtest_get_quota", ej_ookla_speedtest_get_quota},' in web)
check("Reaper's launch path is kept: every run goes through ookla_run with its stderr file",
      'cmd[cmd_idx++] = "ookla_run";' in web and "OOKLA_LIST_STDERR : OOKLA_STDERR" in web)
check("shared.h includes ookla_common.h", '#include "ookla_common.h"' in rd("shared/shared.h"))
m = re.search(r'#define OOKLA_CONFIG_AXHND_A7\s+"([^"]+)"', hdr)
check("ookla_common.h carries the AXHND_A7 key", m is not None and "0ptd555qj7mb2ccz" in m.group(1))
check("the retired key is the end-of-service default profile only",
      "OOKLA_CMD_PROFILE_TUPLE(OOKLA_CONFIG_DEFAULT, 0, 1)" in utils)
hnd = utils[utils.find("defined(HND_ROUTER)"):]
check("an HND router outside the Wi-Fi 8 SDK gets the AXHND_A7 profile",
      "return s_ookla_cmd_tuple[OOKLA_PROFILE_AXHND_A7];" in hnd.split("#elif")[0])
check("ookla_utils.o is built", "OBJS += ookla_utils.o" in rd("shared/Makefile"))
check("the ookla_quota default exists", '{ "ookla_quota", "0<0<0", CKN_STR20' in rd("shared/defaults.c"))
rcmk, rcc, rch = rd("rc/Makefile"), rd("rc/rc.c"), rd("rc/rc.h")
check("ookla_quota_mon is built, linked and registered",
      os.path.isfile(os.path.join(SRC, "rc", "ookla_quota_mon.c")) and "OBJS += ookla_quota_mon.o" in rcmk
      and "ln -sf rc ookla_quota_mon" in rcmk and '"ookla_quota_mon",' in rcc
      and "extern int ookla_quota_mon_main(int argc, char *argv[]);" in rch)
omk = rd("ookla_speedtest/Makefile")
check("the engine is 3.8.0 (build 235) (OOKLA-38000 ookla-AXHND-A7) as 40585 selects",
      re.search(r"^OOKLA_VER = 38000\b", omk, re.M) is not None and "$(OOKLA_PATH)/ookla-AXHND-A7" in omk
      and os.path.isfile(os.path.join(SRC, "ookla_speedtest", "OOKLA-38000", "ookla-AXHND-A7")))
page = rd("www/internet_speed.html")
check("the page shows the quota notice and stops a run when the quota is used up",
      'id="speedTest_quota_overlay"' in page and 'httpApi.hookGet("ookla_speedtest_get_quota", true)' in page
      and "if(is_quota_exceeded())" in page)
check("the page keeps Reaper's per-run resets", "speedTest_retry_done = false;" in page
      and "level_err_last_len = 0;" in page)

if fails:
    print("\n%d FAILED" % len(fails)); sys.exit(1)
print("\nall checks passed: the speed test is on the 40585 Ookla setup")
