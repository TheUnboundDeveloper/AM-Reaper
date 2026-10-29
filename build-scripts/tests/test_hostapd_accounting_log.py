#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hostapd logs "RADIUS: starting accounting session" only when RADIUS accounting exists (2026-10-15).

WHY THIS EXISTS. Every client connection put
    hostapd: wl0.1: STA <mac> RADIUS: starting accounting session <id>
in syslog (490 lines across two logs on the owner's RT-BE96U), though no RADIUS server is
configured anywhere: stock accounting_sta_start() (src/ap/accounting.c, open hostapd in impl103
router_tools) logs at INFO BEFORE its `if (!hapd->conf->radius->acct_server) return;`. Without a
server nothing is sent - the function only records the start time and zeroes the per-client
counters. Metal (lab): no auth_server / acct_server in any /tmp/wl*_hapd.conf, no RADIUS socket.

THE FIX. With an accounting server the INFO line is unchanged; without one the line is
HOSTAPD_LEVEL_DEBUG and says what happened ("local session ... started (no accounting server)").
The default syslog level is INFO (ap_config.c), so the debug line stays out of syslog. The work
after the log - start time, counters, driver stats clear, the acct_server return - is untouched.

WHAT IT DOES. Checks the function body: the INFO log sits under the acct_server test, the else
branch is DEBUG, the bookkeeping and the early return are still there in order, and the default
logger_syslog_level is HOSTAPD_LEVEL_INFO above HOSTAPD_LEVEL_DEBUG. A negative self-test puts the
stock log back and expects the check to fail.

Exit 0 pass, 1 fail, 77 skipped (no tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
H = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "bcmdrivers", "broadcom", "net",
                                  "wl", "impl103", "main", "components", "opensource", "router_tools",
                                  "hostapd", "src")) if SRC else ""
ACC = os.path.join(H, "ap", "accounting.c")
if not H or not os.path.isfile(ACC):
    skip("no hostapd tree (argv[1] = release/src/router, or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

acc = open(ACC, encoding="utf-8", errors="replace").read()
m = re.search(r"\nvoid accounting_sta_start\(struct hostapd_data \*hapd, struct sta_info \*sta\)\n\{\n.*?\n\}\n", acc, re.S)
body = m.group(0) if m else ""
check("accounting_sta_start() found", bool(body))

def gated(b):
    """the INFO start line is only reachable with an accounting server; otherwise DEBUG"""
    code = re.sub(r"/\*.*?\*/", "", b, flags=re.S)
    return re.search(r"if \(hapd->conf->radius->acct_server\)\s*hostapd_logger\([^;]*HOSTAPD_LEVEL_INFO,\s*"
                     r"\"starting accounting session %016llX\"[^;]*;\s*else\s*hostapd_logger\([^;]*"
                     r"HOSTAPD_LEVEL_DEBUG,[^;]*;", code) is not None

check("the INFO 'starting accounting session' line is behind the acct_server test, DEBUG otherwise", gated(body))
code = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
order = [code.find(s) for s in ("os_get_reltime(&sta->acct_session_start);",
                                "hostapd_drv_sta_clear_stats(hapd, sta->addr);",
                                "if (!hapd->conf->radius->acct_server)",
                                "radius_client_send(hapd->radius, msg, RADIUS_ACCT, sta->addr)")]
check("the bookkeeping and the no-server return are unchanged and in order", all(o >= 0 for o in order)
      and order == sorted(order), order)
check("the debug line names what it is", "(no accounting server)" in body)

cfg = open(os.path.join(H, "ap", "ap_config.c"), encoding="utf-8", errors="replace").read()
dbg = open(os.path.join(H, "utils", "wpa_debug.h"), encoding="utf-8", errors="replace").read()
lv = dict(re.findall(r"HOSTAPD_LEVEL_(DEBUG|INFO) = (\d+)", dbg))
check("premise: the default syslog level is INFO, above DEBUG (the debug line stays out of syslog)",
      "bss->logger_syslog_level = HOSTAPD_LEVEL_INFO;" in cfg and lv and int(lv["DEBUG"]) < int(lv["INFO"]), lv)

stock = re.sub(r"\t/\* reaper 2026-10-15:.*?\n\tos_get_reltime",
               "\thostapd_logger(hapd, sta->addr, HOSTAPD_MODULE_RADIUS,\n\t\t       HOSTAPD_LEVEL_INFO,\n"
               "\t\t       \"starting accounting session %016llX\",\n"
               "\t\t       (unsigned long long) sta->acct_session_id);\n\n\tos_get_reltime", body, flags=re.S)
check("self-test: the stock function fails the gate check", stock != body and not gated(stock))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
