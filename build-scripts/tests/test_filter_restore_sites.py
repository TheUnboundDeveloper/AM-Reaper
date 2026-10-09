#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Only the firewall builder may restore the main IPv4 filter file.

WHY THIS EXISTS. /tmp/filter_rules is what filter_setting() wrote the LAST time the firewall was built.
Restoring it again later replaces the whole IPv4 filter table with that snapshot: every chain added
after the snapshot - the SDN per-network rows (handle_sdn_feature), Gatekeeper, Warden, the rules
engine - is deleted, and a stray restore has no SDN re-add and no Reaper tail to put them back.
Stock did exactly that in stop_ddns() (rc/services.c) to remove ONE rule it had inserted for the
tunnelbroker.net DDNS provider; traced live on the owner's RT-BE96U 2026-10-08 12:27:48, one second
after start_firewall()'s tail, inside wan_up(). The router ran for 20 minutes with no SDN isolation,
no Warden and no rules engine while the log showed nothing.

WHAT IT DOES. Scans rc/*.c for any restore of /tmp/filter_rules (iptables-restore or
reaper_restore_rules) and allows it only inside the builder's own functions in rc/firewall.c:
filter_setting / filter_setting2 (the build), repeater_filter_setting (the repeater-mode table).
Anywhere else is a fail, with the function named. Exit 0 pass, 1 fail, 77 skipped (no router
source tree - pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import glob, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
rc_dir = os.path.join(src_root, "rc") if src_root else ""
if not rc_dir or not os.path.isfile(os.path.join(rc_dir, "firewall.c")):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")

ALLOWED = {("firewall.c", "filter_setting"), ("firewall.c", "filter_setting2"), ("firewall.c", "repeater_filter_setting")}
FUNC_RE = re.compile(r'^(?:static\s+)?(?:int|void|char\s*\*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(|^([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^;]*$')
HIT_RE = re.compile(r'(iptables-restore|reaper_restore_rules)[^;\n]*"/tmp/filter_rules"')

fails = []
hits = 0
for path in sorted(glob.glob(os.path.join(rc_dir, "*.c"))):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    fn = "?"
    for i, line in enumerate(lines):
        m = FUNC_RE.match(line)
        if m and not line.lstrip().startswith(("if", "else", "for", "while", "switch", "return")):
            fn = m.group(1) or m.group(2)
        if HIT_RE.search(line) and not line.lstrip().startswith(("*", "//", "/*")):
            hits += 1
            where = (os.path.basename(path), fn)
            ok = where in ALLOWED
            print(("ok   " if ok else "FAIL ") + "%s:%d in %s(): %s" % (where[0], i + 1, fn, line.strip()[:90]))
            if not ok:
                fails.append("%s:%d %s()" % (where[0], i + 1, fn))

print("%d restore site(s) of /tmp/filter_rules found" % hits)
if hits == 0:
    print("FAIL: no restore site found at all - the pattern no longer matches the builder; fix the test"); sys.exit(1)
if fails:
    print("\n%d restore(s) of /tmp/filter_rules outside the firewall builder:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall filter-restore sites are inside the builder")
sys.exit(0)
