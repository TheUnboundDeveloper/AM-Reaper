#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The 40585 hndnvram.sh reaches every 102.8 platform tree (2026-10-29).

WHY THIS EXISTS. The four 102.8-line models take router-sysdep.<model> from
overlays/<MODEL>-platform.tar.gz, whose hndnvram.sh predates Asuswrt-Merlin d7c6a53e440 (ASUS
GPL 102_40585): it mounts the defaults volume on every invocation and stacks a second mount on
the one mount-data.inc made. container_build.sh swaps in overlays/hndnvram-40585.sh right after
the archive unpacks, but only over the known older copy.

WHAT IT DOES. Runs that block of container_build.sh (cut out of the script, not copied) in a
scratch tree for every platform archive: the old copy is replaced with the pinned one and keeps
its mode, an already-fixed copy is left alone, and any other copy fails the build. Also checks
the sidecar hash and that the shipped script parses (sh -n).
Exit 0 pass, 1 fail, 77 skipped."""
import glob, hashlib, os, re, shutil, stat, subprocess, sys, tarfile, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

HERE = os.path.dirname(os.path.abspath(__file__))
LEAN = os.path.dirname(os.path.dirname(HERE))
OV = os.path.join(LEAN, "overlays")
CB = os.path.join(LEAN, "build-scripts", "ci", "container_build.sh")
HNV = os.path.join(OV, "hndnvram-40585.sh")
if not os.path.isdir(OV):
    skip("no overlays/ directory next to build-scripts/")
archives = sorted(glob.glob(os.path.join(OV, "*-platform.tar.gz")))
if not archives:
    skip("no overlays/*-platform.tar.gz (sparse checkout)")
if shutil.which("bash") is None or shutil.which("sh") is None:
    skip("no bash / sh")

fails = []
def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

check(os.path.isfile(HNV), "overlays/hndnvram-40585.sh exists")
side = open(HNV[:-3] + ".sha256").read().split()[0] if os.path.isfile(HNV[:-3] + ".sha256") else ""
NEW = sha(HNV) if os.path.isfile(HNV) else ""
check(side == NEW and NEW != "", "sidecar sha256 matches the shipped script")
check(subprocess.run(["sh", "-n", HNV]).returncode == 0, "shipped script parses (sh -n)")
check(b"\r" not in open(HNV, "rb").read(), "shipped script is LF only")

src = open(CB, encoding="utf-8").read()
m = re.search(r"\n(    HNV=\"\$REPO_DIR/overlays/hndnvram-40585\.sh\"\n.*?\n    esac\n)", src, re.S)
check(m is not None, "container_build.sh carries the hndnvram block")
if m is None:
    sys.exit(1)
block = m.group(1)
OLD = re.search(r"HNV_OLD=([0-9a-f]{64})", block).group(1)
pos_tar = src.find('tar -xzf "$PLAT"'); pos_blk = src.find(block); pos_ov = src.find('git apply --binary --whitespace=nowarn "$OV"')
check(0 <= pos_tar < pos_blk < pos_ov, "block runs after the platform unpack and before the overlay apply")

def run(model, dst_content, mode=0o755):
    """Run the block in a scratch tree; return (rc, output, dst sha, dst mode)."""
    with tempfile.TemporaryDirectory() as d:
        dst = os.path.join(d, "release/src-rt-5.04behnd.4916/router-sysdep.%s/wlan/scripts/hndnvram.sh" % model.lower())
        os.makedirs(os.path.dirname(dst))
        if dst_content is not None:
            with open(dst, "wb") as f:
                f.write(dst_content)
            os.chmod(dst, mode)
        script = "set -euo pipefail\nREPO_DIR=%s\nMODEL=%s\n%s" % (LEAN, model, block)
        p = subprocess.run(["bash", "-c", script], cwd=d, capture_output=True, text=True)
        after = (sha(dst), stat.S_IMODE(os.stat(dst).st_mode)) if os.path.isfile(dst) else ("", 0)
        return p.returncode, (p.stdout + p.stderr).strip(), after[0], after[1]

for a in archives:
    model = os.path.basename(a)[:-len("-platform.tar.gz")]
    want = "release/src-rt-5.04behnd.4916/router-sysdep.%s/wlan/scripts/hndnvram.sh" % model.lower()
    with tarfile.open(a, "r:gz") as t:
        names = {n.lstrip("./"): n for n in t.getnames()}
        member = names.get(want)
        check(member is not None, "%s: archive carries %s" % (model, want))
        if member is None:
            continue
        data = t.extractfile(member).read()
    h = hashlib.sha256(data).hexdigest()
    check(h in (OLD, NEW), "%s: archive's hndnvram.sh is the known older (or fixed) script" % model)
    rc, out, after, mode = run(model, data)
    check(rc == 0 and after == NEW, "%s: block leaves the pinned 40585 script (rc=%d)" % (model, rc))
    check(mode == 0o755, "%s: mode kept 0755 (got %o)" % (model, mode))

rc, out, after, _ = run("GT-BE98", open(HNV, "rb").read())
check(rc == 0 and after == NEW and "already carries" in out, "already-fixed copy is left as it is")
rc, out, after, _ = run("GT-BE98", b"#!/bin/sh\necho somebody else's script\n")
check(rc != 0 and "neither the known older" in out, "an unknown copy fails the build")
rc, out, after, _ = run("GT-BE98", None)
check(rc != 0 and "not in the platform tree" in out, "a missing copy fails the build")

if fails:
    print("\n%d check(s) failed" % len(fails)); sys.exit(1)
print("\nall checks passed")
