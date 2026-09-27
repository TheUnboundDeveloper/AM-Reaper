#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The dynamic puncturing core must only change a bitmap when the problem is sustained, the
candidate is legal, the gain is meaningful and the change interval has expired.

WHY THIS EXISTS. Dynamic preamble puncturing (rpunctd) drives the static applier from radio
telemetry. A wrong decision there is a radio switching part of its channel off on a family's
network, so the decision layer (release/src/router/rpunctd/punct_core.c) has no I/O of its
own and is pinned here on a build host, with synthetic telemetry, before any radio sees it.

WHAT IT DOES. Compiles punct_core.c + punct_host.c with the host compiler and drives
scenario files through it: the legal-bitmap tables per width against the rules measured on
the RT-BE96U on 2026-09-25; the scorer on the two textbook cases (a 79 % busy secondary 80
is worth switching off, a 40 % one is not); the hysteresis traces (a 20 s burst never
punctures, a sustained one does at Conservative after its hold; a punctured slice is only
restored after the long clean hold and a meaningful gain; the change interval blocks a flip;
a refused bitmap is blacklisted; two disruptive applies fall back); a slice reported lost
(fell off the radio) is forgotten at once and re-applied only after the change interval,
a refusal never leaves anything to restore; the scan tiers (an unresolved far-160 candidate
asks for a scan, Passive only holds); and the reset on a channel change.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass release/src/router
as argv[1] or REAPER_ROUTER_SRC).
"""
import os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
core = os.path.join(src_root, "rpunctd", "punct_core.c") if src_root else ""
host = os.path.join(src_root, "rpunctd", "punct_host.c") if src_root else ""
if not core or not os.path.isfile(core):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
if not os.path.isfile(host):
    die("punct_host.c missing next to the core")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

tmp = tempfile.mkdtemp(prefix="punct_")
exe = os.path.join(tmp, "punct_host")
r = subprocess.run([CC, "-O1", "-Wall", "-Wextra", "-Werror", "-std=gnu99", "-o", exe, core, host],
                   capture_output=True, text=True)
if r.returncode != 0:
    die("host compile failed:\n" + r.stderr)

def run(scenario):
    p = os.path.join(tmp, "s.txt")
    with open(p, "w") as f:
        f.write(scenario)
    out = subprocess.run([exe, p], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        die("punct_host exited %d:\n%s" % (out.returncode, out.stderr))
    return out.stdout.splitlines()

def acts(lines):
    return [l for l in lines if l.split(" ")[1:2] and l.split(" ")[1] in ("APPLY", "CLEAR", "SCAN")]

passed = 0
def ok(cond, what):
    global passed
    if not cond:
        die(what)
    passed += 1

# ---- 1. legal bitmaps: exactly one slice, never the primary 80 (or the primary 20 at 80 MHz)
lines = run("legal 320 1\nlegal 320 9\nlegal 80 0\nlegal 80 2\nlegal 160 5\n")
tbl = {l.split(":")[0]: l.split(":")[1].split() for l in lines if l.startswith("legal")}
ok(tbl["legal 320 1"] == ["0x30", "0xc0", "0x300", "0xc00", "0x3000", "0xc000", "0xf0", "0xf00", "0xf000"],
   "320 MHz primary 1: expected the 40s and 80s outside 0x000f, got %s" % tbl["legal 320 1"])
ok(all(m not in tbl["legal 320 9"] for m in ("0x300", "0xc00", "0xf00")) and all(m in tbl["legal 320 9"] for m in ("0xf", "0xf0", "0xf000")),
   "320 MHz primary 9: the primary 80 (bits 8-11) must be excluded and the rest offered, got %s" % tbl["legal 320 9"])
ok(tbl["legal 80 0"] == ["0x2", "0x4", "0x8"], "80 MHz primary 0: got %s" % tbl["legal 80 0"])
ok(tbl["legal 80 2"] == ["0x1", "0x2", "0x8"], "80 MHz primary 2: got %s" % tbl["legal 80 2"])
ok(tbl["legal 160 5"] == ["0x1", "0x2", "0x4", "0x8", "0x3", "0xc"],
   "160 MHz primary 5: 20s and 40s outside the primary 80 (bits 4-7), got %s" % tbl["legal 160 5"])

# ---- 2. scorer: 320 MHz, primary 1 (6g69/320-1). sec80 = 0xf0.
def window(t, pri, s20, s40, s80, total, own=20):
    return "t %d %d %d %d %d %d %d\n" % (t, pri, s20, s40, s80, total, own)

base = "init c p\ngeom 320 1 0\n"
# 79 % busy on sec80, ~15 % elsewhere: switching the 80 off must score much higher
s = base + window(10, 150, 0, 0, 790, 940) + "score 0x0\nscore 0xf0\nscore 0x30\n"
sc = {l.split()[1]: int(l.split()[2]) for l in run(s) if l.startswith("score")}
ok(sc["0xf0"] > sc["0x0"] * 2, "79 %% sec80: 240 MHz (%d) must beat 320 MHz (%d) clearly" % (sc["0xf0"], sc["0x0"]))
ok(sc["0x30"] < sc["0xf0"], "a 40 inside a busy 80 leaves the other half busy: %d vs %d" % (sc["0x30"], sc["0xf0"]))
# 25 % busy on sec80 (just above the ~23 % break-even for an 80 of 320): a cleaner 240 is NOT
# automatically better than a slightly noisy 320 - the gain must stay marginal
s = base + window(10, 150, 0, 0, 250, 400) + "score 0x0\nscore 0xf0\n"
sc = {l.split()[1]: int(l.split()[2]) for l in run(s) if l.startswith("score")}
gain = (sc["0xf0"] - sc["0x0"]) * 1000 // sc["0x0"]
ok(0 <= gain < 100, "25 %% sec80: gain %d permille must stay marginal" % gain)
# 15 % busy: switching off loses capacity outright
s = base + window(10, 150, 0, 0, 150, 300) + "score 0x0\nscore 0xf0\n"
sc = {l.split()[1]: int(l.split()[2]) for l in run(s) if l.startswith("score")}
ok(sc["0xf0"] < sc["0x0"], "15 %% sec80: 240 MHz (%d) must lose to 320 MHz (%d)" % (sc["0xf0"], sc["0x0"]))

# ---- 3. hysteresis at Conservative (trigger 80 %, hold 60 s, min interval 300 s, eval 60 s)
def ticks(t0, n, *w, step=10):
    return "".join(window(t0 + i * step, *w) for i in range(n))

# a 20 s burst never punctures
s = base + ticks(10, 6, 100, 0, 0, 50, 150) + ticks(70, 2, 100, 0, 0, 900, 950) + ticks(90, 30, 100, 0, 0, 50, 150)
ok(acts(run(s)) == [], "a 20 s burst must not puncture")
# sustained 85 % on sec80 punctures after the hold, once
s = base + ticks(10, 6, 100, 0, 0, 50, 150) + ticks(70, 40, 100, 0, 0, 850, 950)
a = acts(run(s))
ok(len(a) == 1 and a[0].split()[1] == "APPLY" and a[0].split()[2] == "0xf0", "sustained sec80 must APPLY 0xf0 once, got %s" % a)
t_apply = int(a[0].split()[0])
ok(t_apply >= 70 + 60, "APPLY at %d is before the 60 s hold" % t_apply)
ok("persistent sec80" in a[0] and "APPLY" in a[0], "the decision line must say why: %s" % a[0])

# after the apply: restore only after the 240 s clean hold, and a meaningful gain
s2 = s + "apply ok %d\n" % t_apply + ticks(t_apply + 10, 70, 100, 0, 0, 0, 100)
a = acts(run(s2))
ok(len(a) == 2 and a[1].split()[1] == "CLEAR", "clean slice must be RESTOREd, got %s" % a)
t_clear = int(a[1].split()[0])
ok(t_clear - t_apply >= 300 and t_clear - t_apply >= 240, "restore at +%d s: needs the change interval and the clean hold" % (t_clear - t_apply))
# still busy while punctured: never restored
s3 = s + "apply ok %d\n" % t_apply + ticks(t_apply + 10, 70, 100, 0, 0, 850, 950)
ok(len(acts(run(s3))) == 1, "a slice that stays busy must stay switched off")

# the change interval blocks a flip: a second problem right after the apply waits
s4 = s + "apply ok %d\n" % t_apply + ticks(t_apply + 10, 8, 100, 0, 0, 0, 900)
out = run(s4 + "\n")
ok(len(acts(out)) == 1, "no second change inside the min interval, got %s" % acts(out))

# refused bitmap is blacklisted and not retried
s5 = s + "apply refused %d\n" % t_apply + ticks(t_apply + 10, 40, 100, 0, 0, 850, 950)
ok(len(acts(run(s5))) == 1, "a refused bitmap must not be retried")

# two disruptive applies fall back and clear
s6 = s + "apply disruptive %d\n" % t_apply
out = run(s6)
ok(any("fallback" in l or "holding" in l for l in out), "a disruptive apply must slow down or fall back")

# ---- 4. tiers: a busy FAR 160 at 320 MHz is unresolved by the counters
far = base.replace("init c p", "init c p") + ticks(10, 6, 100, 0, 0, 0, 150) + ticks(70, 30, 100, 0, 0, 0, 950)
ok(acts(run(far)) == [], "Passive only must hold on an unresolved far-160 candidate")
out = run(far.replace("init c p", "init c a"))
a = acts(out)
ok(len(a) >= 1 and a[0].split()[1] == "SCAN" and a[0].split()[2] == "0xff00", "Active tier must SCAN the far 160, got %s" % a)
t_scan = int(a[0].split()[0])
# the scan says the upper 80 (bits 12-15) is the busy one: apply 0xf000
sc_line = "scan %d %s\n" % (t_scan + 2, " ".join(["50"] * 12 + ["900"] * 4))
out = run(far.replace("init c p", "init c a") + sc_line + ticks(t_scan + 10, 8, 100, 0, 0, 0, 950))
a = acts(out)
ok(len(a) == 2 and a[1].split()[1] == "APPLY" and a[1].split()[2] == "0xf000", "after the scan the busy far 80 must be applied, got %s" % a)
# idle tier waits while own airtime is high
busy_own = base.replace("init c p", "init c i") + ticks(10, 6, 100, 0, 0, 0, 150, 400) + ticks(70, 30, 100, 0, 0, 0, 950, 400)
ok(acts(run(busy_own)) == [], "Idle tier must not scan while own airtime is high")

# ---- 4b. a slice that left the radio (crawl 2026-09-26 F1): the daemon reports it lost,
# the core forgets it and monitors afresh - and a re-apply still waits out the change interval
s9 = s + "apply ok %d\n" % t_apply + "lost %d\n" % (t_apply + 20)
out = run(s9)
ok(any(l.endswith("STATE monitoring") and int(l.split()[0]) == t_apply + 20 for l in out),
   "a lost slice must put the core back to monitoring at once, got %s" % [l for l in out if "STATE" in l])
# the problem is still there: the same slice is applied again, but not inside the interval
s10 = s9 + ticks(t_apply + 30, 40, 100, 0, 0, 850, 950)
a = acts(run(s10))
ok(len(a) == 2 and a[1].split()[1] == "APPLY" and a[1].split()[2] == "0xf0", "after a loss a sustained problem must APPLY again, got %s" % a)
ok(int(a[1].split()[0]) - t_apply >= 300, "the re-apply at +%d s must respect the 300 s change interval" % (int(a[1].split()[0]) - t_apply))
# nothing on the radio: a lost report is a no-op (no state line, no change)
out = run(base + ticks(10, 3, 100, 0, 0, 0, 150) + "lost 40\n" + ticks(50, 3, 100, 0, 0, 0, 150))
ok(not any("STATE" in l and int(l.split()[0]) == 40 for l in out), "lost with no slice on the radio must change nothing")
# a refused apply leaves the core believing nothing is on the radio: no CLEAR is ever issued for it
s11 = s + "apply refused %d\n" % t_apply + ticks(t_apply + 10, 70, 100, 0, 0, 0, 100)
ok(not any(l.split()[1] == "CLEAR" for l in acts(run(s11))), "after a refusal there is nothing to restore")

# ---- 5. a channel change resets everything; 80 MHz sec20 is a resolved candidate
s7 = base + ticks(10, 30, 100, 0, 0, 850, 950) + "geom 80 0 320\n" + ticks(330, 6, 100, 0, 0, 0, 150)
ok(len(acts(run(s7))) == 1, "state after a channel change must not carry the old candidate")
s8 = "init c p\ngeom 80 0 0\n" + ticks(10, 6, 100, 0, 0, 0, 150) + ticks(70, 40, 100, 900, 0, 0, 950)
a = acts(run(s8))
ok(len(a) == 1 and a[0].split()[2] == "0x2", "80 MHz: a busy sec20 must APPLY 0x2, got %s" % a)

print("PASS: %d checks" % passed)
shutil.rmtree(tmp, ignore_errors=True)
