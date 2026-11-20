#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reaper_docs.py --fix: two marked claims on one line are both rewritten in place.

WHY THIS EXISTS. The positions of every claim on a line are measured once, before any of them is rewritten. When
the first claim changed length - the patch count going from three digits to four at v3.8.1 (997 -> 1009) - the
second one was written one character to the left and swallowed the space before it: "through v3.8.0" became
"throughv3.8.1" in three documents. The fixer now rewrites the rightmost claim first.

WHAT IT DOES. Builds a throwaway docs folder with lines that carry two claims each (count then version, in both
length directions, with and without code ticks), runs the real process() in fix mode with stand-in facts, and
compares every line with the text a careful hand edit would give. A second pass must change nothing.

Exit 0 pass, 1 fail. Needs no router source tree.
"""
import io, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import reaper_docs  # noqa: E402


class StandIn(object):
    treever, pubver, pubdate = "v3.8.1", "v3.1.0", "2026-09-08"
    patchcount, modelcount, fleetjobs = 1009, 4, 8
    models = ["RT-BE96U"]


CASES = [
    # (before, after)
    ("recipe (the series is now at 997 <!--@patchcount--> patches, through v3.8.0 <!--@treever-->,\n",
     "recipe (the series is now at 1009 <!--@patchcount--> patches, through v3.8.1 <!--@treever-->,\n"),
    ("series (**997 <!--@patchcount--> patches, v1.0 → v3.8.0 <!--@treever-->**), as files\n",
     "series (**1009 <!--@patchcount--> patches, v1.0 → v3.8.1 <!--@treever-->**), as files\n"),
    ("to `997` <!--@patchcount--> (v3.8.0 <!--@treever-->, RT-BE96U-only), while\n",
     "to `1009` <!--@patchcount--> (v3.8.1 <!--@treever-->, RT-BE96U-only), while\n"),
    # the version first and the count second, each in code ticks
    ("built `Reaper_v3.8.0` <!--@treever--> (patch series `0001`–`997` <!--@patchcount-->) and on\n",
     "built `Reaper_v3.8.1` <!--@treever--> (patch series `0001`–`1009` <!--@patchcount-->) and on\n"),
    ("applies all 1009 <!--@patchcount--> patches (through v3.8.1 <!--@treever-->).\n",
     "applies all 1009 <!--@patchcount--> patches (through v3.8.1 <!--@treever-->).\n"),
]

fails = []
root = tempfile.mkdtemp(prefix="rdocs_")
try:
    os.makedirs(os.path.join(root, "docs"))
    p = os.path.join(root, "docs", "T.md")
    head = "# T\n\n> **Doc status:** current as of **v3.8.1** · 2026-11-16 <!--@stamp-->\n\n"
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(head + "".join(b for b, _ in CASES))
    reaper_docs.process(root, "fix", StandIn())
    got = io.open(p, encoding="utf-8", newline="").read()
    lines = got[len(head):].splitlines(True)
    for (before, want), have in zip(CASES, lines):
        ok = have == want
        print(("ok   " if ok else "FAIL ") + want.strip()[:90].encode("ascii", "backslashreplace").decode("ascii"))
        if not ok:
            fails.append("got %r" % have)
    if len(lines) != len(CASES):
        fails.append("line count changed: %d" % len(lines))
    reaper_docs.process(root, "fix", StandIn())
    again = io.open(p, encoding="utf-8", newline="").read()
    ok = again == got
    print(("ok   " if ok else "FAIL ") + "a second pass changes nothing")
    if not ok:
        fails.append("second pass rewrote the file")
finally:
    shutil.rmtree(root, ignore_errors=True)

if fails:
    print("FAIL test_reaper_docs_same_line (%d)" % len(fails))
    for x in fails:
        print("  - " + x[:300].encode("ascii", "backslashreplace").decode("ascii"))
    sys.exit(1)
print("PASS test_reaper_docs_same_line")
