#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A fetched list (ASN / country) goes when its last rule goes (2026-11-22, found on metal with test image _r5).

WHY. The router builds a fetched list's sets, saved copy and daily job in rfw_gen_lists (rc/reaper_fw.c), which
runs on a Policy Routing APPLY. While a change can still be reverted, reaper_pbr_uses_object() counts the staged
rule list AND the confirmed one, so a revert finds its set. On metal: the operator removed the only rule that
named an ASN list, applied, pressed Keep - and the sets, the saved copy, the 05:17 job and the updater stayed,
and "Update now" kept fetching a list no rule used. Keep never looked again: at apply time the old confirmed list
still named the object.

WHAT IT CHECKS (source): reaper_pbr_confirm() calls reaper_fw_lists_sync() after it has written the confirmed
list and promoted the objects; reaper_pbr_rollback() calls it after the revert script ran; rc.h declares it, and
reaper_fw_lists_sync() itself rebuilds the lists from the current config. Exit 0 pass, 1 fail, 77 skipped (no
router source tree, or a tree without fetched lists).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
PBR = os.path.join(SRC, "rc", "reaper_pbr.c")
if not SRC or not os.path.isfile(PBR):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
pbr, fw, rch = rd("rc/reaper_pbr.c"), rd("rc/reaper_fw.c"), rd("rc/rc.h")
if "void reaper_fw_lists_sync(void)" not in fw:
    skip("this tree has no fetched lists")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def body(src, sig):
    i = src.find(sig)
    if i < 0: return ""
    j = src.find("\n}\n", i)
    return src[i:j + 3] if j > 0 else ""

conf = body(pbr, "void reaper_pbr_confirm(void)\n")
roll = body(pbr, "void reaper_pbr_rollback(void)\n")
sync = body(fw, "void reaper_fw_lists_sync(void)\n")
check("reaper_pbr_confirm() is found", bool(conf))
i_lg, i_pr, i_sy = conf.find("ppbr_write_lastgood(rl)"), conf.find("reaper_fw_promote_objects();"), conf.find("reaper_fw_lists_sync();")
check("Keep runs the list check again", i_sy > 0, conf[:200])
check("...after the confirmed rule list is written and the objects are promoted", 0 < i_lg < i_sy and 0 < i_pr < i_sy, (i_lg, i_pr, i_sy))
check("...exactly once", conf.count("reaper_fw_lists_sync();") == 1)
check("...not behind the enable test (switching routing off at Keep also drops the lists)",
      i_sy < conf.find('if (nvram_match("reaper_pbr_enable", "1"))'), conf[i_sy - 80:i_sy + 80])
check("...after the arm token is taken (a stray confirm returns before it)",
      conf.find("rmdir(PPBR_ARMED) != 0") < conf.find("return;") < i_sy)
i_sc = roll.find('system("sh " PPBR_ROLLBACK')
check("the page's Revert runs the list check after the revert script", 0 < i_sc < roll.find("reaper_fw_lists_sync();"), roll)
check("...and not when there is no revert script (it returns first)",
      roll.find("return;") < roll.find("reaper_fw_lists_sync();"))
check("rc.h declares reaper_fw_lists_sync()", re.search(r"extern void reaper_fw_lists_sync\(void\);", rch) is not None)
check("reaper_fw_lists_sync() rebuilds the lists from the current config", "rfw_cfg_load(&c," in sync and "rfw_gen_lists(&c);" in sync, sync)
check("rfw_gen_lists() still drops the job and the script when no list is in use",
      'eval("cru", "d", "reaper_fw_lists");' in fw and "unlink(RFW_LISTS);" in fw)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
