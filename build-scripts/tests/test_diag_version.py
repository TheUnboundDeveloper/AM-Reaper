#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Diagnostics page and the diag script must state the same version.

WHY THIS EXISTS. `www/Reaper_Diag.asp` shows the diag version as a plain literal
and `others/reaper_diag` defines the real one in VER. Two copies, one re-pinned
by hand, so they drift: v1.0.1 against a v1.3.16 script (found 2026-09-13), then
v1.3.18 against v1.3.19 (found 2026-09-15, already in a shipped image). The user
then sees the page and the report it just produced disagree on the same screen.

reaper_verify carries the same check against the STAGED fs; this one runs on the
SOURCE tree so a bump is caught at commit time rather than after a build is spent.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router
as argv[1] or REAPER_ROUTER_SRC).
"""
import io
import os
import re
import sys

PAT = re.compile(r"REAPER-DIAG v[0-9]+\.[0-9]+\.[0-9]+")


def read(p):
    return io.open(p, encoding="utf-8", errors="surrogateescape").read()


def main():
    src = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", ""))
    if not src or not os.path.isdir(src):
        print("SKIP: no router source tree given")
        return 77
    script = os.path.join(src, "others", "reaper_diag")
    page = os.path.join(src, "www", "Reaper_Diag.asp")
    for p in (script, page):
        if not os.path.isfile(p):
            print("SKIP: %s not present" % p)
            return 77

    sv = PAT.search(read(script))
    pv = PAT.search(read(page))
    if not sv:
        print("FAIL: others/reaper_diag carries no 'REAPER-DIAG vX.Y.Z' version")
        return 1
    if not pv:
        print("FAIL: www/Reaper_Diag.asp carries no 'REAPER-DIAG vX.Y.Z' literal")
        return 1
    if sv.group(0) != pv.group(0):
        print("FAIL: the Diagnostics page says %r but the script it runs is %r."
              % (pv.group(0), sv.group(0)))
        print("      Re-pin the literal in www/Reaper_Diag.asp to match others/reaper_diag's VER.")
        return 1

    # a second literal would defeat the re-pin silently
    n = len(PAT.findall(read(page)))
    if n != 1:
        print("FAIL: www/Reaper_Diag.asp carries %d version literals, expected exactly 1" % n)
        return 1

    print("all checks passed: page and script agree on %s (one literal)" % sv.group(0))
    return 0


sys.exit(main())
