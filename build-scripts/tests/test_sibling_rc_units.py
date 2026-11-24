#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sibling-supplied rc sources stay in rc/Makefile (2026-10-09).

WHY THIS EXISTS. rc/reaper_chanlist_shim.c exists only on GT-BE98 (overlay) and GT-BE19000,
BQ16 and BQ16 Pro (platform archives): it stubs wl_scb, backup_eth_ob_log and
is_wan_port_ext_switch, which their closed rc objects lack. From canon (RT-BE96U) the wildcard
line that compiles it looks dead, so the 2026-10-07 audit listed it (B4) and the v3.3.7 rung
removed it - and all eight jobs of those four models failed to link rc in CI. A canon-only view
cannot see this class; this suite looks at what the siblings actually carry.

SINCE THE UNIFICATION (2026-11-04) those stubs live in canon instead:
rc/reaper_legacy_blobs_shim.c and httpd/reaper_legacy_blobs_httpd.c, compiled only under
RTCONFIG_REAPER_LEGACY_BLOBS (set by the four models' target.mak blocks), and no overlay or
archive carries reaper_chanlist_shim.c any more. The generic rule below still holds: an rc
source that a sibling ships must be compiled, so a stale archive that still carries the old
shim fails here (its file would be named by nothing).

WHAT IT DOES. Lists every release/src/router/rc/*.c that an overlays/*.patch touches or an
overlays/*-platform.tar.gz carries, then requires canon's rc/Makefile (comment lines stripped)
to name each one's .o; and requires canon's compatibility layer to be wired: both shim sources
present and each named by its Makefile inside an RTCONFIG_REAPER_LEGACY_BLOBS block.
Needs the router source (argv[1] or REAPER_ROUTER_SRC). Exit 0 pass, 1 fail, 77 skipped."""
import glob, os, re, sys, tarfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

HERE = os.path.dirname(os.path.abspath(__file__))
LEAN = os.path.dirname(os.path.dirname(HERE))
OV = os.path.join(LEAN, "overlays")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
MK = os.path.join(SRC, "rc", "Makefile") if SRC else ""
if not MK or not os.path.isfile(MK):
    skip("no router source tree with rc/Makefile (argv[1] or REAPER_ROUTER_SRC)")
if not os.path.isdir(OV):
    skip("no overlays/ directory next to build-scripts/")

RC_C = re.compile(r"release/src/router/rc/([^/\s]+)\.c$")
need = {}  # stem -> [sources]
for p in sorted(glob.glob(os.path.join(OV, "*.patch"))):
    with open(p, encoding="utf-8", errors="surrogateescape") as f:
        for line in f:
            if line.startswith("diff --git a/"):
                m = RC_C.search(line.split()[2])
                if m:
                    need.setdefault(m.group(1), []).append(os.path.basename(p))
for a in sorted(glob.glob(os.path.join(OV, "*-platform.tar.gz"))):
    with tarfile.open(a, "r:gz") as t:
        for name in t.getnames():
            m = RC_C.search(name.lstrip("./"))
            if m:
                need.setdefault(m.group(1), []).append(os.path.basename(a))

mk = "\n".join(l for l in open(MK, encoding="utf-8", errors="surrogateescape").read().split("\n")
               if not l.lstrip().startswith("#"))
fails = []
print("sibling-supplied rc sources: %d" % len(need))
for stem in sorted(need):
    ok = re.search(r"(^|[\s,(])%s\.o\b" % re.escape(stem), mk, re.M) is not None
    print(("ok   " if ok else "FAIL ") + "%s.o compiled by rc/Makefile  (from %s)" % (stem, ", ".join(sorted(set(need[stem])))))
    if not ok:
        fails.append(stem)
for sub, src, obj in (("rc", "reaper_legacy_blobs_shim.c", "reaper_legacy_blobs_shim.o"),
                      ("httpd", "reaper_legacy_blobs_httpd.c", "reaper_legacy_blobs_httpd.o")):
    path = os.path.join(SRC, sub, src)
    text = "\n".join(l for l in open(os.path.join(SRC, sub, "Makefile"), encoding="utf-8",
                                     errors="surrogateescape").read().split("\n")
                     if not l.lstrip().startswith("#"))
    wired = re.search(r"ifeq \(\$\(RTCONFIG_REAPER_LEGACY_BLOBS\),y\)\s*\nOBJS \+= %s\s*\nendif" % re.escape(obj),
                      text) is not None
    ok = os.path.isfile(path) and wired
    print(("ok   " if ok else "FAIL ") + "%s/%s present and compiled under RTCONFIG_REAPER_LEGACY_BLOBS" % (sub, src))
    if not ok:
        fails.append(src)
if fails:
    print("\n%d sibling rc source(s) not linked: %s - a sibling that ships the file will fail to link rc"
          % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks passed: every rc source a sibling carries is compiled by canon's rc/Makefile")
