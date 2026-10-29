#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rwatch's incident dump and outage timer must survive the pre-NTP clock of a no-WAN boot.

WHY THIS EXISTS. A router booted without internet runs on a placeholder clock (2023-12-31 19:00)
until its first NTP sync, then steps years forward. On the owner's RT-BE96U (v3.4.2_BETA_r6,
2026-10-13, ONT dead overnight) rwatch got both of its time figures wrong:
  - `FAILURE detected: ... filter-skeleton - diagnostics dumped to <store>` followed by
    `incident dump suppressed (-1460995 min since the last one)`: the throttle compared the
    pre-NTP now with a real-clock `.last` on the durable store, the difference was negative, and
    the boot that most needed a bundle got none while the log said it had been written;
  - `recovered (1463770 min outage)` for an outage of about 730 minutes: T0 was stamped on the
    pre-NTP clock and the recovery on the real one.
The fix times the outage on /proc/uptime (the state file is per boot), lets a `.last` that is
ahead of the clock throttle nothing, and logs the FAILURE line after the dump with what the dump
actually did.

WHAT IT DOES. Extracts the generated shell between `rw_dump() {` and the outage state machine
from rc/rwatch.c, runs it under /bin/sh with stubbed logger/date/system tools, and replays the
metal sequence plus the throttle that must keep working. Exit 0 pass, 1 fail, 77 skipped (no
router source tree - pass release/src/router as argv[1] or REAPER_ROUTER_SRC - or no /bin/sh).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
rwatch = os.path.join(src_root, "rc", "rwatch.c") if src_root else ""
if not rwatch or not os.path.isfile(rwatch):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
SH = shutil.which("sh")
if not SH or os.name == "nt":
    skip("no POSIX sh on this host")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

with open(rwatch, encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# --- the generated shell: every C string literal line from rw_dump() to the end of the state machine
start = next((i for i, l in enumerate(lines) if l.strip() == '"rw_dump() {\\n"'), None)
end = next((i for i, l in enumerate(lines) if start is not None and i > start and l.strip() == '"  echo OK > $STATE\\n"'), None)
if start is None or end is None:
    print("FAIL: rw_dump()/state-machine block not found in rc/rwatch.c"); sys.exit(1)
lit = re.compile(r'"((?:[^"\\]|\\.)*)"')
unesc = lambda s: re.sub(r'\\(.)', lambda m: "\n" if m.group(1) == "n" else m.group(1), s)
body = []
for l in lines[start:end + 3]:
    if l.lstrip().startswith('"'):
        body.extend(unesc(x) for x in lit.findall(l))
script = "".join(body)
check("the extracted block ends with the state machine's fi", script.rstrip().endswith("fi"), script[-120:])

STUBS = r'''
logger() { shift 2; echo "$*" >> "$LOG"; }
date() { if [ "$1" = "+%s" ]; then echo "$FAKE_NOW"; else echo "Sun Dec 31 19:10:01 EST 2023"; fi; }
uptime() { echo " up"; }
dmesg() { :; }; iptables() { :; }; ip6tables() { :; }; ipset() { :; }; ip() { :; }
fcctl() { :; }; bpmctl() { :; }; tmctl() { :; }; _nv() { :; }; reaper_lockrun() { :; }
GDX=0; HEALGRACE=0; CRIT=""
'''

def run(tmp, fake_now, up, fail, state=None, last=None):
    droot = os.path.join(tmp, "rwatch"); os.makedirs(droot, exist_ok=True)
    st = os.path.join(tmp, "rwatch.state"); log = os.path.join(tmp, "log")
    if state is not None:
        open(st, "w").write(state + "\n")
    if last is not None:
        open(os.path.join(droot, ".last"), "w").write("%d\n" % last)
    if os.path.exists(log): os.remove(log)
    env = dict(os.environ, LOG=log, FAKE_NOW=str(fake_now))
    pre = STUBS + 'DUMPROOT="%s"\nSTATE="%s"\nUP=%d\nFAIL="%s"\n' % (droot, st, up, fail)
    r = subprocess.run([SH, "-c", pre + script], env=env, capture_output=True, text=True, timeout=30)
    out = open(log).read() if os.path.exists(log) else ""
    dirs = sorted(d for d in os.listdir(droot) if d.startswith("inc-"))
    stv = open(st).read().strip() if os.path.exists(st) else ""
    return r, out, dirs, stv

PRE_NTP = 1704067800          # 2023-12-31 19:10 EST, the placeholder clock at uptime ~10 min
REAL_LAST = 1791727521        # the owner's .last from a real-clock dump on 2026-10-11

# 1) no-WAN boot: first failure on the pre-NTP clock after a real-clock dump -> a bundle IS written
with tempfile.TemporaryDirectory() as t:
    r, out, dirs, stv = run(t, PRE_NTP, 600, " wan6-gw filter-skeleton", last=REAL_LAST)
    check("pre-NTP failure: the script runs clean", r.returncode == 0 and not r.stderr.strip(), r.stderr)
    check("pre-NTP failure: a bundle is written despite a .last ahead of the clock", dirs == ["inc-%d" % PRE_NTP], dirs)
    check("pre-NTP failure: nothing is reported as suppressed", "suppressed" not in out, out)
    check("pre-NTP failure: the FAILURE line names the bundle it wrote",
          "FAILURE detected: wan6-gw filter-skeleton - diagnostics dumped to " in out and out.rstrip().endswith("inc-%d" % PRE_NTP), out)
    check("pre-NTP failure: the outage is stamped on uptime", stv == "FAIL 600 1", stv)

    # 2) the NTP step, then recovery 730 min later: the duration is uptime-based
    r, out, dirs, stv = run(t, 1791860402, 600 + 730 * 60, "")
    check("recovery after the NTP step reports the real outage", out.strip() == "recovered (730 min outage)", out)
    check("recovery resets the state", stv == "OK", stv)

# 3) a genuine flap inside 30 min on a real clock is still throttled, and the log says so
with tempfile.TemporaryDirectory() as t:
    r, out, dirs, stv = run(t, 1791860400, 5000, " wan-gw", state="OK", last=1791860000)
    check("flap within RWDUMP_MIN_S: no new bundle", dirs == [], dirs)
    check("flap within RWDUMP_MIN_S: the FAILURE line carries the suppression, not a dump claim",
          out.strip() == "FAILURE detected: wan-gw - incident dump suppressed (6 min since the last one)", out)

# 4) still failing: every third tick logs a non-negative uptime duration; a stale wall-clock T0
#    (state written by an older script in the same boot) clamps instead of going negative
with tempfile.TemporaryDirectory() as t:
    r, out, dirs, stv = run(t, 1791860400, 4200, " wan6-gw", state="FAIL 600 2")
    check("still failing: duration from uptime", out.strip() == "still failing: wan6-gw (60 min)", out)
    r, out, dirs, stv = run(t, 1791860400, 4200, " wan6-gw", state="FAIL %d 2" % REAL_LAST)
    check("still failing: a wall-clock T0 above uptime never prints a negative", out.strip() == "still failing: wan6-gw (0 min)", out)
    r, out, dirs, stv = run(t, 1791860400, 4200, "", state="FAIL %d 5" % REAL_LAST)
    check("recovery: a wall-clock T0 above uptime never prints a negative", out.strip() == "recovered (0 min outage)", out)

# 5) static: the 'FAILURE detected:' prefix the diag 19b counter and REAPER-GUIDE rely on is kept
check("the 'rwatch: FAILURE detected:' prefix is unchanged", 'logger -t rwatch "FAILURE detected:$FAIL$CRIT - $RWD"' in script, "")

if fails:
    print("\n%d FAIL:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
