#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The diag's Warden log checks follow the firewall log (report v1.3.56, 2026-11-10).

WHY THIS EXISTS. Since v3.7.5 every firewall log rule is NFLOG and its lines go to the firewall log
(rflogd's RAM ring in /tmp/reaper/fwlog), not to the system log. The diag still looked for a "-j LOG"
rule in RW_ODROP and counted Warden's lines in /tmp/syslog.log only, so every router with Warden
logging on got "RW_ODROP carries no LOG rule - outbound blocks are dropped silently" while its
outbound drops WERE logged, and section 14 read 0 hits (owner's RT-BE96U report, 2026-11-10).

WHAT IT DOES. Cuts the finding line and the counting loop out of others/reaper_diag and runs them
under sh (and busybox ash when the host has it) with stub nvram / iptables / finding functions:
an NFLOG rule and a LOG rule are both "logged", a chain with only DROP still warns; the loop counts
each prefix in the firewall log (prev.log + current.log) and in the system log, and a missing file
counts as 0.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or
REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
DIAG = os.path.join(SRC, "others", "reaper_diag") if SRC else ""
if not DIAG or not os.path.isfile(DIAG):
    skip("no router source tree with others/reaper_diag (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(DIAG, encoding="utf-8", errors="surrogateescape").read()
mf = re.search(r'^\[ "\$\(nvram get rwarden_enable 2>/dev/null\)" = 1 \] && \[ "\$\(nvram get rwarden_log 2>/dev/null\)" = 1 \] && iptables -nL RW_ODROP .*$', src, re.M)
check("the RW_ODROP log finding is one line the test can cut out", mf is not None)
ml = re.search(r'^for P in "REAPER-WARDEN " "REAPER-WARDEN-FWD " "REAPER-WARDEN-OUT " "REAPER-WARDEN-SELF "; do\n.*?^done\n', src, re.S | re.M)
check("the Warden counting loop is a block the test can cut out", ml is not None)
check("the finding accepts either log target", mf is not None and "grep -c -E 'j (LOG|NFLOG)'" in mf.group(0) and "grep -c 'j LOG'" not in src)
check("the loop reads the firewall log's two files and the system log",
      ml is not None and "/tmp/reaper/fwlog/prev.log /tmp/reaper/fwlog/current.log" in ml.group(0) and "/tmp/syslog.log" in ml.group(0))

shells = [["sh"]]
if shutil.which("busybox") and subprocess.run(["busybox", "ash", "-c", "true"]).returncode == 0:
    shells.append(["busybox", "ash"])
STUB = 'nvram() { echo 1; }\niptables() { case "$1" in -nL) return 0;; -S) cat "$RULES";; esac; }\nfinding() { echo "FINDING $1 $2"; }\n'
CASES = [
    ("an NFLOG rule", '-N RW_ODROP\n-A RW_ODROP -m limit --limit 10000/sec --limit-burst 10000 -j NFLOG --nflog-prefix  "REAPER-WARDEN-OUT " --nflog-group 41\n-A RW_ODROP -j DROP\n', False),
    ("a LOG rule", '-N RW_ODROP\n-A RW_ODROP -m limit --limit 10/sec --limit-burst 50 -j LOG --log-prefix "REAPER-WARDEN-OUT " --log-level 5\n-A RW_ODROP -j DROP\n', False),
    ("only a DROP rule", '-N RW_ODROP\n-A RW_ODROP -j DROP\n', True),
]
for sh in shells if (mf and ml) else []:
    tag = "[%s] " % " ".join(sh)
    with tempfile.TemporaryDirectory() as td:
        for name, rules, warn in CASES:
            rf = os.path.join(td, "rules"); open(rf, "w").write(rules)
            sf = os.path.join(td, "f.sh"); open(sf, "w").write(STUB + mf.group(0) + "\ntrue\n")
            r = subprocess.run(sh + [sf], capture_output=True, text=True, env=dict(os.environ, RULES=rf))
            got = "FINDING WARN" in r.stdout
            check(tag + "%s: %s" % (name, "the finding fires" if warn else "no finding"), r.returncode == 0 and got == warn, r.stdout + r.stderr)
            if warn:
                check(tag + "the finding names both targets", "carries no log rule (LOG or NFLOG)" in r.stdout, r.stdout)
        fw = os.path.join(td, "fwlog"); os.mkdir(fw)
        open(os.path.join(fw, "prev.log"), "w").write("2026-11-10T11:38:16.700-05:00 REAPER-WARDEN IN=eth0 OUT= SRC=203.0.113.5\n")
        open(os.path.join(fw, "current.log"), "w").write(
            "2026-11-10T11:39:00.000-05:00 REAPER-WARDEN IN=eth0 OUT= SRC=203.0.113.6\n"
            "2026-11-10T11:39:01.000-05:00 REAPER-WARDEN-OUT IN=br0 OUT=eth0 SRC=192.168.50.9\n"
            "2026-11-10T11:39:02.000-05:00 ACCEPT IN=br0 OUT=eth0\n")
        sl = os.path.join(td, "syslog.log"); open(sl, "w").write("Nov 10 11:00:00 kernel: REAPER-WARDEN-SELF IN= OUT=eth0\nNov 10 11:00:01 kernel: REAPER-WARDEN IN=eth0\n")
        loop = ml.group(0).replace("/tmp/reaper/fwlog/", fw + "/").replace("/tmp/syslog.log", sl)
        sf = os.path.join(td, "l.sh"); open(sf, "w").write(loop)
        r = subprocess.run(sh + [sf], capture_output=True, text=True)
        L = [x.strip() for x in r.stdout.split("\n") if x.strip()]
        check(tag + "the loop prints one line for each of the four prefixes", r.returncode == 0 and len(L) == 4, r.stdout + r.stderr)
        if len(L) == 4:
            check(tag + "inbound drops: 2 in the firewall log (both files), 1 in the system log", L[0] == "'REAPER-WARDEN ' hits: firewall log 2, system log 1", L[0])
            check(tag + "a prefix with no line reads 0 and 0", L[1] == "'REAPER-WARDEN-FWD ' hits: firewall log 0, system log 0", L[1])
            check(tag + "outbound: 1 in the firewall log", L[2] == "'REAPER-WARDEN-OUT ' hits: firewall log 1, system log 0", L[2])
            check(tag + "the router's own: 1 in the system log", L[3] == "'REAPER-WARDEN-SELF ' hits: firewall log 0, system log 1", L[3])
        loop2 = ml.group(0).replace("/tmp/reaper/fwlog/", os.path.join(td, "absent") + "/").replace("/tmp/syslog.log", os.path.join(td, "absent.log"))
        open(sf, "w").write(loop2)
        r = subprocess.run(sh + [sf], capture_output=True, text=True)
        L = [x.strip() for x in r.stdout.split("\n") if x.strip()]
        check(tag + "missing files count as 0, one figure each", len(L) == 4 and all(x.endswith("hits: firewall log 0, system log 0") for x in L), r.stdout + r.stderr)

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  " + f)
sys.exit(1 if fails else 0)
