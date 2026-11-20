#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Radio firmware per model (review 2026-11-17 phase 7; batch p10, 2026-11-18) - 6717a0 only where a BCM6717 exists.

WHY. Each image carries dongle firmware per radio chip: rom/etc/wlan/dhd/6717a0 (BCM6717, about 4 MB) and 6726b0
(BCM6726). The router loads /rom/etc/wlan/nvram/<boardid>.nvm, and that board file lists every radio with its device
id (N:devid=); Broadcom's bcmdevs.h maps 0x6025-27 to BCM6717 and 0x602c-e to BCM6726. Every board file of the
GT-BE98, GT-BE98 Pro, GT-BE19000, BQ16 and BQ16 Pro names BCM6726 radios only, so their 6717a0 was dead weight that
ASUS ships in most vendor images anyway. The RT-BE96U is the opposite case: its early units carry three BCM6717
(RT-BE96U.nvm), so its 6717a0 must ALWAYS ship (a review once called it unused from a B0 unit's reading).
WHAT IT CHECKS.
  1. The evidence, from the tree's board files (targets/nvram/6813): every GT-BE98* / GT-BE19000* / BQ16* board file
     names only BCM6726 radios, with the radio count the model has (4, or 3 for the GT-BE19000); RT-BE96U.nvm names
     three BCM6717 radios. If a new board file for one of the five names a BCM6717, this fails - take the model off
     REAPER_NO_6717A0 before shipping.
  2. release/src-rt/Makefile: REAPER_NO_6717A0 lists exactly the five, never the RT-BE96U / RT-BE86U / RT-BE88U, and
     gates the 6717a0 copy. The real wl_sysdep dongle block is extracted and RUN by make on a scratch tree: a listed
     model gets 6726b0 only and loses a stale dongle/bin/6717a0; the RT-BE96U gets both.
  3. build-scripts/reaper_verify.sh 8c, extracted and run against scratch images: a listed model passes with 6726b0
     alone and FAILS with 6717a0 staged; the RT-BE96U fails without 6717a0.
Exit 0 pass, 1 fail, 77 skipped (no router source tree, or no make / bash).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
REL = os.path.dirname(os.path.dirname(os.path.abspath(SRC))) if SRC else ""
NVM = os.path.join(REL, "src-rt-5.04behnd.4916", "targets", "nvram", "6813")
MK = os.path.join(REL, "src-rt", "Makefile")
if not SRC or not os.path.isdir(NVM) or not os.path.isfile(MK):
    print("SKIP: no router source tree"); sys.exit(77)
if not shutil.which("make") or not shutil.which("bash"):
    print("SKIP: no make / bash"); sys.exit(77)
LEAN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RV = os.path.join(LEAN, "build-scripts", "reaper_verify.sh")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:900] if detail else ""))

FIVE = ["GT-BE98", "GT-BE98_PRO", "GT-BE19000", "BQ16", "BQ16_PRO"]
BCM6717 = {"0x6025", "0x6026", "0x6027"}
BCM6726 = {"0x602c", "0x602d", "0x602e"}

def radios(path):
    b = open(path, "rb").read().replace(b"\0", b"\n")
    return {int(n): v.decode().lower() for n, v in re.findall(rb"(?:^|[^0-9a-z])([0-9]+):devid=(0x[0-9a-fA-F]+)", b)}

# ---- 1. the evidence: board files
files = sorted(f for f in os.listdir(NVM) if f.endswith(".nvm"))
five_files = [f for f in files if re.match(r"(GT-BE98|GT-BE19000|BQ16)", f)]
check("board files of the five models are present (%d)" % len(five_files), len(five_files) >= 9, files)
for f in five_files:
    p = os.path.join(NVM, f)
    if os.path.islink(p): continue
    r = radios(p); want = 3 if f.startswith("GT-BE19000") else 4
    check("%s: %d radios, every one a BCM6726 (%s)" % (f, want, " ".join("%d:%s" % kv for kv in sorted(r.items()))),
          len(r) == want and set(r.values()) <= BCM6726 and not (set(r.values()) & BCM6717), r)
r96 = radios(os.path.join(NVM, "RT-BE96U.nvm")); r96b = radios(os.path.join(NVM, "RT-BE96U_B0.nvm"))
check("RT-BE96U.nvm (early units): three BCM6717 radios - its 6717a0 must always ship", len(r96) == 3 and set(r96.values()) == BCM6717, r96)
check("RT-BE96U_B0.nvm (B0 units): three BCM6726 radios", len(r96b) == 3 and set(r96b.values()) == BCM6726, r96b)

# ---- 2. the build rule
mk = open(MK, encoding="utf-8", errors="surrogateescape").read()
m = re.findall(r"^REAPER_NO_6717A0 := (.*)$", mk, re.M)
check("src-rt/Makefile: REAPER_NO_6717A0 defined once", len(m) == 1, m)
lst = m[0].split() if m else []
check("REAPER_NO_6717A0 = exactly the five models whose board files name no BCM6717", sorted(lst) == sorted(FIVE), lst)
check("REAPER_NO_6717A0 never lists the RT-BE96U, RT-BE86U or RT-BE88U", not ({"RT-BE96U", "RT-BE86U", "RT-BE88U"} & set(lst)), lst)
check("the list sits above wl_sysdep", m and mk.index("REAPER_NO_6717A0 :=") < mk.index("\nwl_sysdep:\n"))
gate = '\t\tif [ -n "$(filter $(BUILD_NAME),$(REAPER_NO_6717A0))" ]; then \\\n'
check("the 6717a0 copy is gated by the list (once)", mk.count(gate) == 1)
lines = mk.splitlines(keepends=True)
try:
    s = next(i for i, l in enumerate(lines) if "dongle/sysdeps/$(BUILD_NAME) ]; then" in l and l.startswith("\tif [ -d "))
    e = next(i for i in range(s + 1, len(lines)) if lines[i] == "\telse \\\n")
    block = "".join(lines[s:e]) + "\tfi;\n"
except StopIteration:
    block = ""
check("wl_sysdep's dongle block found", bool(block))

td = tempfile.mkdtemp(prefix="p10dongle_")
def run_rule(model):
    root = os.path.join(td, model); shutil.rmtree(root, ignore_errors=True)
    sb = os.path.join(root, "a", "b", "c"); os.makedirs(sb)
    dng = os.path.join(root, "bcm9X", "dhd", "src", "dongle")
    for c in ("6717a0", "6726b0"):
        os.makedirs(os.path.join(dng, "sysdeps", model, c)); open(os.path.join(dng, "sysdeps", model, c, "rtecdc.bin"), "w").write(c)
    os.makedirs(os.path.join(dng, "bin", "6717a0", "release")); open(os.path.join(dng, "bin", "6717a0", "release", "rtecdc.bin"), "w").write("stale")
    mf = os.path.join(root, "t.mk")
    open(mf, "w").write("REAPER_NO_6717A0 := %s\nt:\n%s" % (" ".join(lst), block))
    p = subprocess.run(["make", "-s", "-f", mf, "t", "SRCBASE=" + sb, "BRCM_CHIP=X", "DHD_DIR=dhd", "BUILD_NAME=" + model, "BCM_MFG="],
                       capture_output=True, text=True)
    have = sorted(c for c in ("6717a0", "6726b0") if os.path.isfile(os.path.join(dng, "bin", c, "release", "rtecdc.bin")))
    return p.returncode, have, p.stderr
if block:
    for model in ("GT-BE98", "BQ16_PRO", "GT-BE19000"):
        rc, have, err = run_rule(model)
        check("rule RUN for %s: 6726b0 installed, 6717a0 not, the stale dongle/bin/6717a0 removed" % model, rc == 0 and have == ["6726b0"], (rc, have, err))
    rc, have, err = run_rule("RT-BE96U")
    check("rule RUN for RT-BE96U: both 6717a0 and 6726b0 installed", rc == 0 and have == ["6717a0", "6726b0"], (rc, have, err))

# ---- 3. reaper_verify 8c
rv = open(RV, encoding="utf-8").read() if os.path.isfile(RV) else ""
try:
    sec = rv[rv.index("# ---- 8c."):rv.index("# ---- 8d.")]
except ValueError:
    sec = ""
check("reaper_verify.sh 8c found", bool(sec))
def run_8c(model, chips):
    fs = os.path.join(td, "fs_" + model + "_" + "_".join(chips)); shutil.rmtree(fs, ignore_errors=True)
    for c in chips:
        os.makedirs(os.path.join(fs, "rom/etc/wlan/dhd", c, "release")); open(os.path.join(fs, "rom/etc/wlan/dhd", c, "release", "rtecdc.bin"), "w").write("x")
    script = ('pass(){ echo "PASS $1"; }; fail(){ echo "FAIL $1"; }; warn(){ echo "WARN $1"; }\n'
              'MODEL="%s"; FS="%s"\n%s' % (model, fs, sec))
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return p.stdout
if sec:
    out = run_8c("GT-BE98", ["6726b0"])
    check("8c: GT-BE98 with 6726b0 only passes both checks", "FAIL" not in out and "PASS dongle-fw\n" in out and "PASS dongle-fw-unused" in out, out)
    out = run_8c("BQ16", ["6717a0", "6726b0"])
    check("8c: BQ16 with 6717a0 staged FAILS dongle-fw-unused", "FAIL dongle-fw-unused" in out, out)
    out = run_8c("RT-BE96U", ["6726b0"])
    check("8c: RT-BE96U without 6717a0 FAILS dongle-fw (early units would lose all three radios)", "FAIL dongle-fw\n" in out, out)
    out = run_8c("RT-BE96U", ["6717a0", "6726b0"])
    check("8c: RT-BE96U with both passes, and is never judged for an unused 6717a0", "FAIL" not in out and "dongle-fw-unused" not in out, out)
shutil.rmtree(td, ignore_errors=True)

if fails:
    print("\n%d check(s) failed" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
