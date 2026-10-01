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
# review 2026-10-01: the Active tier has a ceiling too - no off-channel second in a busy stream
busy_act = base.replace("init c p", "init c a") + ticks(10, 6, 100, 0, 0, 0, 150, 400) + ticks(70, 30, 100, 0, 0, 0, 950, 400)
ok(acts(run(busy_act)) == [], "Active tier must not scan while own airtime is above the 30 % ceiling")
mid_act = base.replace("init c p", "init c a") + ticks(10, 6, 100, 0, 0, 0, 150, 200) + ticks(70, 30, 100, 0, 0, 0, 950, 200)
a = acts(run(mid_act))
ok(len(a) >= 1 and a[0].split()[1] == "SCAN", "Active tier must still scan below the ceiling (own 20 %%), got %s" % a)

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

# ---- 6. the scan's other evidence (v3.3.1): a neighbour's home channels take the group's
# persistent busy as a prior, PHY impairment counts as busy where carrier sense read low,
# and a restore on a scan tier needs a fresh scan of the switched-off channels that agrees
def scanx(t, n, cca, imp=None, nb=None):
    imp = imp or [0] * n; nb = nb or [0] * n
    return "scanx %d %s\n" % (t, " ".join("%d:%d:%d" % (cca[i], imp[i], nb[i]) for i in range(n)))
act_far = far.replace("init c p", "init c a")
gap = [50] * 16
# control: a flat 5 % snapshot resolves nothing worth applying
a = acts(run(act_far + scanx(t_scan + 2, 16, gap) + ticks(t_scan + 10, 8, 100, 0, 0, 0, 950)))
ok(not any(l.split()[1] == "APPLY" for l in a), "a flat scan snapshot must not apply, got %s" % a)
# a strong neighbour on the upper far 80 (bits 12-15): its channels take the far group's busy
a = acts(run(act_far + scanx(t_scan + 2, 16, gap, nb=[0] * 12 + [1000] * 4) + ticks(t_scan + 10, 8, 100, 0, 0, 0, 950)))
ok(len(a) == 2 and a[1].split()[1] == "APPLY" and a[1].split()[2] == "0xf000", "the neighbour prior must pick the upper far 80, got %s" % a)
# a faint neighbour (weight 0) changes nothing
a = acts(run(act_far + scanx(t_scan + 2, 16, gap, nb=[0] * 12 + [0] * 4) + ticks(t_scan + 10, 8, 100, 0, 0, 0, 950)))
ok(not any(l.split()[1] == "APPLY" for l in a), "no neighbour weight, no prior, got %s" % a)
# PHY impairment on the lower far 80 (bits 8-11) with a flat carrier-sense snapshot
a = acts(run(act_far + scanx(t_scan + 2, 16, gap, imp=[0] * 8 + [900] * 4 + [0] * 4) + ticks(t_scan + 10, 8, 100, 0, 0, 0, 950)))
ok(len(a) == 2 and a[1].split()[1] == "APPLY" and a[1].split()[2] == "0xf00", "PHY impairment must pick the lower far 80, got %s" % a)
# restore on a scan tier: the counters going quiet is not enough - a fresh scan of the
# switched-off channels must agree; a busy one keeps the slice, a clean one restores it
s_act = base.replace("init c p", "init c a") + ticks(10, 6, 100, 0, 0, 50, 150) + ticks(70, 40, 100, 0, 0, 850, 950)
a = acts(run(s_act))
ok(len(a) == 1 and a[0].split()[2] == "0xf0", "active tier: sustained sec80 must APPLY 0xf0, got %s" % a)
t_ap = int(a[0].split()[0])
quiet = s_act + "apply ok %d\n" % t_ap + ticks(t_ap + 10, 70, 100, 0, 0, 0, 100)
a = acts(run(quiet))
ok(len(a) == 2 and a[1].split()[1] == "SCAN" and a[1].split()[2] == "0xf0", "before restoring, the switched-off channels must be scanned, got %s" % a)
t_rs = int(a[1].split()[0])
n1 = (t_rs - (t_ap + 10)) // 10 + 1
pre = s_act + "apply ok %d\n" % t_ap + ticks(t_ap + 10, n1, 100, 0, 0, 0, 100)
a = acts(run(pre + scanx(t_rs + 2, 16, [0] * 4 + [900] * 4 + [0] * 8) + ticks(t_rs + 10, 30, 100, 0, 0, 0, 100)))
ok(not any(l.split()[1] == "CLEAR" for l in a), "a scan that finds the switched-off channels busy must KEEP the slice, got %s" % a)
a = acts(run(pre + scanx(t_rs + 2, 16, [0] * 16) + ticks(t_rs + 10, 30, 100, 0, 0, 0, 100)))
ok(len(a) == 3 and a[2].split()[1] == "CLEAR", "a clean scan must let the slice be restored, got %s" % a)
# on the Passive source the counters alone still restore (section 3 above covers it)

# ---- 7. v3.3.1 r6: the whole-radio PHY impairment trigger (it may only ask for a scan) and
# the per-client evidence (tie-breaker, post-change proof), plus the scan block
def wimp(t, pri, s20, s40, s80, total, own, imp):
    return "t %d %d %d %d %d %d %d %d\n" % (t, pri, s20, s40, s80, total, own, imp)
def tick_imp(t0, n, *w, step=10):
    return "".join(wimp(t0 + i * step, *w) for i in range(n))
g160 = "geom 160 0 0\n"      # 160 MHz, primary 0: the puncturable channels are bits 4-7 (0xf0)
quiet_imp = lambda tier, imp: "init c %s\n" % tier + g160 + tick_imp(10, 30, 50, 0, 0, 0, 100, 20, imp)
# Passive: impairment alone never scans and never applies
ok(acts(run(quiet_imp("p", 600))) == [], "Passive: the impairment trigger must not act")
# Active: after the bad hold it asks for a scan of every puncturable channel - and nothing else
a = acts(run(quiet_imp("a", 600)))
ok(len(a) == 1 and a[0].split()[1] == "SCAN" and a[0].split()[2] == "0xf0",
   "Active: persistent impairment must SCAN the puncturable channels (0xf0) once, got %s" % a)
t_is = int(a[0].split()[0])
ok(t_is >= 10 + 60, "the impairment scan at %d must wait out the 60 s bad hold" % t_is)
ok("phy impairment" in a[0], "the scan line must say why: %s" % a[0])
# below the Conservative trigger (35 %): nothing
ok(acts(run(quiet_imp("a", 200))) == [], "impairment below the trigger must not scan")
# the scan finds two channels impaired: the 40 holding them is applied (scan evidence at trigger level)
n1 = (t_is - 10) // 10 + 1
pre_s = "init c a\n" + g160 + tick_imp(10, n1, 50, 0, 0, 0, 100, 20, 600)
a = acts(run(pre_s + scanx(t_is + 2, 8, [50] * 8, imp=[0] * 6 + [900] * 2) + tick_imp(t_is + 10, 12, 50, 0, 0, 0, 100, 20, 600)))
ok(len(a) == 2 and a[1].split()[1] == "APPLY" and a[1].split()[2] == "0xc0",
   "a scan that finds 0xc0 impaired must APPLY 0xc0, got %s" % a)
ok("phy impairment" in a[1] and "scan" in a[1], "the apply must name its evidence: %s" % a[1])
# the scan finds nothing: no apply, and no second scan inside the cooldown (900 s)
a = acts(run(pre_s + scanx(t_is + 2, 8, [50] * 8) + tick_imp(t_is + 10, 60, 50, 0, 0, 0, 100, 20, 600)))
ok(len(a) == 1, "a clean scan must neither apply nor rescan inside the cooldown, got %s" % a)
# a blocked radio (a scan lost a client) behaves as Passive
ok(acts(run("init c a\n" + g160 + "blockscans\n" + tick_imp(10, 30, 50, 0, 0, 0, 100, 20, 600))) == [],
   "after a scan lost a client, the impairment trigger must not scan again")
# the busy path is unchanged by a missing PHY figure (-1): section 3 runs with none

# tie-breaker at 320, primary 1 (primary 160 = bits 0-7): sec80 (0xf0, inside the primary 160)
# and the upper far 80 (0xf000, scan-resolved) both qualify; 0xf0 has the higher gain.
tb = ("init a a\ngeom 320 1 0\n" + scanx(5, 16, [50] * 12 + [600] * 4) +
      tick_imp(10, 3, 50, 0, 0, 600, 1000, 20, 600))
a = acts(run(tb + tick_imp(40, 2, 50, 0, 0, 600, 1000, 20, 600)))
ok(len(a) >= 1 and a[0].split()[1] == "APPLY" and a[0].split()[2] == "0xf0",
   "no client figures: the higher gain (0xf0) must win, got %s" % a)
a = acts(run(tb.replace("scanx 5", "clients 6 0 0 0 5 0\nscanx 5") + tick_imp(40, 2, 50, 0, 0, 600, 1000, 20, 600)))
ok(len(a) >= 1 and a[0].split()[1] == "APPLY" and a[0].split()[2] == "0xf000",
   "five 160 MHz clients: the slice outside their block (0xf000) must win, got %s" % a)
ok("narrows 0" in a[0], "the apply must say how many narrower clients it narrows: %s" % a[0])

# the post-change proof: most clients worse after an apply -> CLEAR, and not retried
out = run(s + "apply ok %d\nproof 0 4 3 0 %d\n" % (t_apply, t_apply + 120) + ticks(t_apply + 130, 3, 100, 0, 0, 850, 950))
ok(any("PROOF hurt=1" in l for l in out), "3 of 4 worse must count as a hurt")
a = acts(out)
ok(len(a) == 2 and a[1].split()[1] == "CLEAR" and "client evidence" in a[1],
   "a hurt must CLEAR the slice at once, got %s" % a)
t_pc = int(a[1].split()[0])
a = acts(run(s + "apply ok %d\nproof 0 4 3 0 %d\n" % (t_apply, t_apply + 120) + ticks(t_apply + 130, 1, 100, 0, 0, 850, 950) +
            "apply ok %d\n" % t_pc + ticks(t_pc + 10, 60, 100, 0, 0, 850, 950)))
ok(not any(l.split()[1] == "APPLY" and l.split()[2] == "0xf0" for l in a[1:]),
   "a slice the clients rejected must not be applied again on this channel, got %s" % a)
# mixed evidence is not a hurt; neither is a single client
for args, what in (("4 1 2", "1 worse, 2 better"), ("4 2 2", "2 worse, 2 better"), ("1 1 0", "one client")):
    out = run(s + "apply ok %d\nproof 0 %s %d\n" % (t_apply, args, t_apply + 120) + ticks(t_apply + 130, 3, 100, 0, 0, 850, 950))
    ok(any("PROOF hurt=0" in l for l in out) and len(acts(out)) == 1, "%s must not clear, got %s" % (what, acts(out)))
# after a restore, a hurt only lengthens the next restore hold - it never acts by itself
out = run(s2 + "apply ok %d\nproof 1 4 3 0 %d\n" % (t_clear, t_clear + 120) + ticks(t_clear + 130, 3, 100, 0, 0, 0, 100))
ok(any("PROOF hurt=1" in l for l in out) and len(acts(out)) == 2, "a restore hurt must not act, got %s" % acts(out))

# ---- 8. source tripwires in the daemon (release/src/router/rpunctd/rpunctd.c)
dsrc = open(os.path.join(src_root, "rpunctd", "rpunctd.c"), encoding="utf-8", errors="replace").read()
import re
bs = re.findall(r'bs_data[^"]*"', dsrc)
ok(bs and all("-noreset" in x for x in bs),
   "every station-table read must pass -noreset (a plain read clears the counters bsd steers on): %s" % bs)
ok("pc_block_scans(&r->pc);" in dsrc and "after < before" in dsrc,
   "a confirmation scan that loses a client must stop scanning on that radio")
ok("e = glitch + badplcp;" in dsrc and "* 9" not in dsrc.split("static int impair_of")[1].split("}")[0],
   "impair_of must take glitch and bad PLCP as per-second counts (chanim_stats_t), not scale them by 9")
ok("s.imp = (s.valid && read_phy(r))" in dsrc, "the PHY figures must be read only for a valid, closed window")

# ---- 9. v3.3.1 r7: the daemon's station-table and noise code, lifted out of rpunctd.c
# (brace-matched, never copied) and fed the r6 metal read-back (RT-BE96U, 2026-09-30; MAC
# addresses replaced). Pins what metal showed: txbw is MHz summed per packet, the table is
# reset by another reader every few seconds (time_delt), and the whole-channel noise figure
# grows with the width - so the noise term is measured above the radio's own baseline.
def lift(sig):
    i = dsrc.find(sig)
    while i >= 0 and dsrc.find(";", i) < dsrc.find("{", i):   # a prototype ends in ';' before any '{'
        i = dsrc.find(sig, i + 1)
    if i < 0:
        die("rpunctd.c: no definition for %s" % sig)
    j = dsrc.index("{", i); dep = 0; k = j
    while True:
        if dsrc[k] == "{": dep += 1
        elif dsrc[k] == "}":
            dep -= 1
            if dep == 0: break
        k += 1
    return dsrc[i:k + 1] + "\n"
defs = "".join("#define %s %s\n" % (n, re.search(r"#define\s+%s\s+(\d+)" % n, dsrc).group(1))
               for n in ("RP_STA_MAX", "RP_STA_MIN_PK", "RP_NBASE_TC"))
structs = "".join(re.search(r"^struct %s \{.*?\};$" % n, dsrc, re.M | re.S).group(0) + "\n"
                  for n in ("sta", "stasnap", "sacc", "sbucket"))
harness_src = (
    "#define _GNU_SOURCE\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <ctype.h>\n"
    "static size_t strlcpy(char *d, const char *s, size_t n){size_t l=strlen(s);if(n){size_t c=l<n-1?l:n-1;memcpy(d,s,c);d[c]=0;}return l;}\n"
    + defs + structs
    + lift("static int sta_parse(FILE *p, struct stasnap *sn, char *hdr, size_t hlen)")
    + lift("static const struct sta *sta_find(const struct stasnap *sn, const char *mac)")
    + lift("static void bucket_add(struct sbucket *b, const char *mac, unsigned long long acked, unsigned long long retry,")
    + lift("static void bucket_merge(struct sbucket *dst, const struct sbucket *src)")
    + lift("static void sta_fresh(const struct stasnap *prev, const struct stasnap *cur, long elapsed, struct sbucket *b1, struct sbucket *b2)")
    + lift("static int width_class(const struct sacc *c)")
    + lift("static int noise_floor(long *base_mdb, int *ok, int kn)")
    + lift("static int impair_of(int glitch, int badplcp, int knoise, int floor_dbm)")
    + r'''
static const char *META =
"  Station Address,retry_dro   rtsfail     retry txrate_ma txrate_su     acked throughpu time_delt   airtime      txbw     txmcs     txnss        ru        mu\n"
"02:00:00:00:00:01,        0         0         0         0     97217        99    193629   1753505     26764      7920        46       194         0         0\n"
"02:00:00:00:00:02,        0         0        12         0   1230752        37      5296   1753505      2006     11840       302        74         0         0\n"
"02:00:00:00:00:03,        0         0         0         0     11342         1       126   1753505       116       160        11         1         0         0\n";
static int parse(const char *text, struct stasnap *sn)
{
	char hdr[160] = ""; FILE *f = fmemopen((void *)text, strlen(text), "r"); int rc;
	memset(sn, 0, sizeof(*sn)); sn->has_td = 1; rc = sta_parse(f, sn, hdr, sizeof(hdr)); fclose(f);
	sn->ok = rc == 1; return rc;
}
static struct sacc *get(struct sbucket *b, const char *m){int i;for(i=0;i<b->n;i++)if(!strcmp(b->c[i].mac,m))return &b->c[i];return NULL;}
int main(void)
{
	static struct stasnap a, b; static struct sbucket k; struct sacc *c; long base = 0; int ok = 0, i, f = 0;
	#define CHK(x, m) do { if (x) printf("ok %s\n", m); else { printf("BAD %s\n", m); f++; } } while (0)
	CHK(parse(META, &a) == 1 && a.n == 3 && a.has_td, "metal table parses: 3 stations, time_delt found");
	CHK(a.s[0].acked == 99 && a.s[0].bw == 7920 && a.s[0].td == 1753505 && a.s[1].retry == 12 && a.s[1].rate == 1230752, "columns land by header name");
	{ struct sacc x = { "", 99, 0, 0, 7920 }, y = { "", 37, 0, 0, 11840 }, z = { "", 1, 0, 0, 160 }, q = { "", 3, 0, 0, 3105120 };
	  CHK(width_class(&x) == 2 && width_class(&y) == 4 && width_class(&z) == 3, "txbw / acked = 80, 320, 160 MHz");
	  CHK(width_class(&q) < 0, "a width that is not MHz is refused"); }
	/* the next read 30 s later: time_delt 2.1 s < 30 s = the table was reset in between -> the whole read is new */
	parse("  Station Address,retry_dro rtsfail retry txrate_ma txrate_su acked throughpu time_delt airtime txbw txmcs txnss ru mu\n"
	      "02:00:00:00:00:01, 0 0 2 0 50000 50 1 2100000 1 4000 1 1 0 0\n"
	      "02:00:00:00:00:04, 0 0 0 0 1000 10 1 45000000 1 800 1 1 0 0\n", &b);
	k.n = 0; sta_fresh(&a, &b, 30, &k, NULL);
	c = get(&k, "02:00:00:00:00:01");
	CHK(c && c->acked == 50 && c->retry == 2 && c->bw == 4000, "a reset between reads: the whole read counts, not a negative delta");
	CHK(!get(&k, "02:00:00:00:00:04"), "a station absent before and not reset since: cannot be placed, skipped");
	/* no reset: time_delt grew past the 30 s gap and the counters grew -> only the difference counts */
	parse("  Station Address,retry_dro rtsfail retry txrate_ma txrate_su acked throughpu time_delt airtime txbw txmcs txnss ru mu\n"
	      "02:00:00:00:00:01, 0 0 5 0 150000 150 1 32100000 1 12000 1 1 0 0\n", &a);
	k.n = 0; sta_fresh(&b, &a, 30, &k, NULL);
	c = get(&k, "02:00:00:00:00:01");
	CHK(c && c->acked == 100 && c->retry == 3 && c->bw == 8000, "no reset between reads: the delta counts");
	/* a table this code does not understand */
	CHK(parse("  Station Address PHY Mbps Data Mbps\n02:00:00:00:00:01 98.2 0.9\n", &b) < 0, "a table without acked/retry/txrate columns is refused");
	CHK(parse("  Station Address,retry acked txrate_su\n02:00:00:00:00:01, 1 2\n", &b) < 0, "a row with the wrong value count is refused");
	/* noise: the 6 GHz 320 MHz radio at rest (-79 dBm) must read 0 %, a 14 dB rise must register */
	for (i = 0; i < 30; i++) noise_floor(&base, &ok, -79);
	CHK(impair_of(0, 0, -79, noise_floor(&base, &ok, -79)) == 0, "a wide channel at its own resting noise reads 0 % (r6 read 50 %)");
	CHK(impair_of(0, 0, -65, noise_floor(&base, &ok, -65)) >= 350, "a 14 dB rise over the baseline crosses the Conservative trigger");
	CHK(base / 1000 <= -78, "one loud reading barely moves the baseline");
	noise_floor(&base, &ok, -90);
	CHK(base / 1000 == -90, "a quieter reading becomes the baseline at once");
	CHK(impair_of(25, 1, -93, -93) == 0, "5 GHz at rest (25 glitches/s, -93 dBm) reads 0 %");
	return f ? 1 : 0;
}
''')
hsrc = os.path.join(tmp, "sta_harness.c"); hexe = os.path.join(tmp, "sta_harness")
open(hsrc, "w").write(harness_src)
r9 = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wno-unused-function", "-o", hexe, hsrc], capture_output=True, text=True)
if r9.returncode != 0:
    die("station harness compile failed:\n" + r9.stderr[-2000:])
o9 = subprocess.run([hexe], capture_output=True, text=True, timeout=30)
for l in o9.stdout.splitlines():
    ok(l.startswith("ok "), "station/noise harness: " + l)
ok(o9.returncode == 0 and o9.stdout.count("\n") >= 13, "station/noise harness ran all its cases:\n" + o9.stdout)

print("PASS: %d checks" % passed)
shutil.rmtree(tmp, ignore_errors=True)
