#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3.8.4 fixes the owner chose on 2026-11-20 after the review agents reported.

WHY THIS EXISTS.
  - initial_account: an unused page hook. A signed-in request to appGet.cgi?hook=initial_account() emptied the USB
    share accounts, committed nvram and deleted the .__* files on every mounted disk; no shipped page calls it. Its
    ej_handlers row is gone (the function body stays linked but unreachable - its own error string keeps the name
    in the binary, so an image absence marker cannot be used; this source pin replaces it).
  - ceventd: rc starts /bin/ceventd but cevent_app installs /usr/sbin/ceventd, so the daemon never ran (stock ships
    it in /bin). The install target now adds the link bin/ceventd -> ../usr/sbin/ceventd.
  - GT-BE98 Pro pressure sensor: stock 3006.102.39442 builds ICP201XX for it (the GT-BE98PRO_ICP board); its
    target.mak block lacked PRESSURE_SENSOR=y. Only trees that build the GT-BE98 Pro carry the line.

WHAT IT DOES. Static pins in httpd/web.c, the router Makefile and target.mak.
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

FAILS = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond or not detail else ": " + str(detail)[:600]))
    if not cond:
        FAILS.append(name)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "httpd")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def rd(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()

web = rd("httpd/web.c")
check("initial_account: the ej_handlers row is gone", '{ "initial_account", ej_initial_account}' not in web)
check("initial_account: the removal is explained where the row was", "initial_account hook row removed" in web)

mk = rd("Makefile")
blk = mk[mk.find("cevent_app-install: cevent_app\n"):]
blk = blk[:blk.find("\ncevent_app-clean:")]
check("ceventd: the install target adds bin/ceventd -> ../usr/sbin/ceventd (rc starts /bin/ceventd)",
      "\tinstall -d $(INSTALLDIR)/cevent_app/bin\n" in blk and "\tln -sf ../usr/sbin/ceventd $(INSTALLDIR)/cevent_app/bin/ceventd\n" in blk
      and "REAPER-CEVENTD-BIN" in blk)
svc = rd("rc/services.c")
check("ceventd: rc still starts it as /bin/ceventd (the link's reason)", '"/bin/ceventd"' in svc)

tm = os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "target.mak")
if os.path.isfile(tm):
    t = open(tm, encoding="utf-8", errors="replace").read()
    if 'export GT-BE98_PRO += BUILD_NAME="GT-BE98_PRO"' in t and "REAPER-GTBE98PRO-PRESSURE" in t:
        check("pressure: exactly one PRESSURE_SENSOR=y line for the GT-BE98 Pro", t.count("export GT-BE98_PRO += PRESSURE_SENSOR=y") == 1)
        check("pressure: it follows the GT-BE98 Pro block (after its last continued line)",
              t.find('export GT-BE98_PRO += BUILD_NAME="GT-BE98_PRO"') < t.find("export GT-BE98_PRO += PRESSURE_SENSOR=y"))
    elif 'export GT-BE98_PRO += BUILD_NAME="GT-BE98_PRO"' in t and "/wt-102.8/" not in os.path.realpath(tm):
        check("pressure: the GT-BE98 Pro block carries PRESSURE_SENSOR=y", False, "REAPER-GTBE98PRO-PRESSURE line missing")
    else:
        print("note: this tree does not build the GT-BE98 Pro with the pressure line (3006.102.8 line) - pressure checks skipped")
else:
    print("note: target.mak not found next to the router tree - pressure checks skipped")

if FAILS:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
print("all ok")
