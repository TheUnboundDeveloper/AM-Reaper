#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every model ships the one reference networkmap prebuilt (2026-10-10).

WHY THIS EXISTS. networkmap is a closed daemon whose shared-memory client table httpd reads
through networkmap.h. ASUS's 3006.102.8 build of it is byte-identical across RT-BE96U/86U/88U,
GT-BE98/Pro and BQ16/Pro; the GT-BE19000's platform archive carried the GPL 39274 build instead,
whose table predates mlo_links/is_re - httpd reads a garbage entry count and every client list
is empty (the GT-BE98 v1.5.9 defect, fixed there by swapping the binary). The clean room now
copies canon's reference binary over the model's prebuild dir and asserts it by hash
(ci/container_build.sh, phase networkmap-prebuilt).

WHAT IT DOES. Source-free: the phase exists, pins NMP_REF_SHA, copies to the model's dir and
proves it with cmp, and sits AFTER the platform archive is unpacked. With a router source tree
(argv[1] or REAPER_ROUTER_SRC): the reference binary's sha256 equals the pin, and every roster
model's networkmap/prebuild/<MODEL>/networkmap present in that tree equals it too.

Exit 0 pass, 1 fail, 77 skipped.
"""
import hashlib, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

here = os.path.dirname(os.path.abspath(__file__))
cb = os.path.join(here, "..", "ci", "container_build.sh")
if not os.path.isfile(cb):
    skip("no build-scripts/ci/container_build.sh next to this test")
s = open(cb, encoding="utf-8").read()
m = re.search(r"^NMP_REF_SHA=([0-9a-f]{64})$", s, re.M)
check("container_build.sh pins NMP_REF_SHA (64 hex)", m is not None)
pin = m.group(1) if m else ""
check("the phase is declared", "_ph networkmap-prebuilt" in s)
check("the reference is canon's RT-BE96U prebuilt and the target is the model's own dir",
      'NMP_REF="release/src/router/networkmap/prebuild/RT-BE96U/networkmap"' in s
      and 'NMP_DST="release/src/router/networkmap/prebuild/${MODEL}/networkmap"' in s)
check("the reference hash is verified before use, and a mismatch is an error, not a skip",
      'sha256sum "$NMP_REF"' in s and 'not the pinned $NMP_REF_SHA' in s)
check("the copy is proved with cmp and a missing model dir is an error",
      'cmp -s "$NMP_REF" "$NMP_DST"' in s and 'platform tree missing?' in s)
i_plat = s.find('tar -xzf "$PLAT"'); i_phase = s.find("_ph networkmap-prebuilt"); i_fw = s.find("# --- radio firmware identity")
check("the phase runs after the platform archive is unpacked and before the radio-firmware gate",
      0 < i_plat < i_phase < i_fw)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
ref = os.path.join(SRC, "networkmap", "prebuild", "RT-BE96U", "networkmap") if SRC else ""
if SRC and os.path.isfile(ref):
    got = hashlib.sha256(open(ref, "rb").read()).hexdigest()
    check("canon's reference networkmap matches the pin", got == pin, got)
    roster = ["RT-BE96U", "RT-BE86U", "RT-BE88U", "GT-BE98", "GT-BE98_PRO", "GT-BE19000", "BQ16", "BQ16_PRO"]
    for mdl in roster:
        p = os.path.join(SRC, "networkmap", "prebuild", mdl, "networkmap")
        if not os.path.isfile(p):
            print("     (no %s dir in this tree - supplied by its platform archive in CI)" % mdl); continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        check("%s prebuild dir carries the reference build" % mdl, h == pin, h[:16])
else:
    print("     (no router source tree - hash checks skipped)")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: the clean room ships one networkmap layout on every model")
