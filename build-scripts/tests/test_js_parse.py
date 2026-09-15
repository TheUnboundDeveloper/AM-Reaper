#!/usr/bin/env python3
"""Every Reaper page's inline JavaScript must PARSE.

WHY. The www gates check i18n quoting (reaper_langcheck) and CSRF token callers
(reaper_csrfcheck), but nothing checked that the JavaScript on a page is
syntactically valid. A hand edit that drops a brace passes every existing gate,
ships in the image, and kills the page in the browser - the card, the tab or the
whole dashboard simply never renders, with nothing in any log on the router to
say why. This closes that hole.

It needs a JS engine, which the build container may not have, so it skips with 77
rather than failing when node is absent - the same contract the other suites use.

Usage: test_js_parse.py [<release/src/router>]   (or REAPER_ROUTER_SRC)
Exit:  0 pass, 1 a page does not parse, 77 skipped.
"""
import glob
import os
import subprocess
import sys

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not src_root or not os.path.isdir(os.path.join(src_root, "www")):
    print("skip: no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
    sys.exit(77)

here = os.path.dirname(os.path.abspath(__file__))
checker = os.path.join(here, os.pardir, "jscheck.py")
if not os.path.isfile(checker):
    print("skip: build-scripts/jscheck.py not found next to the suites")
    sys.exit(77)

www = os.path.join(src_root, "www")
# dedupe by real name: the glob is case-insensitive on NTFS/DrvFs, so
# "Reaper_*.asp" already matches reaper_shell.asp there and not on ext4
pages, seen = [], set()
for p in sorted(glob.glob(os.path.join(www, "Reaper_*.asp"))) + \
         [os.path.join(www, e) for e in ("Main_ReaperDash.asp", "reaper_shell.asp")]:
    k = os.path.normcase(os.path.abspath(p))
    if k in seen or not os.path.isfile(p):
        continue
    seen.add(k)
    pages.append(p)
if not pages:
    print("skip: no Reaper pages found under %s" % www)
    sys.exit(77)

p = subprocess.run([sys.executable, checker] + pages, capture_output=True, text=True)
sys.stdout.write(p.stdout)
sys.stderr.write(p.stderr)
if p.returncode == 77:
    sys.exit(77)               # jscheck could not find a JS engine
if p.returncode != 0:
    print("\nat least one Reaper page does not parse - see above")
    sys.exit(1)
print("all %d Reaper page(s) parse" % len(pages))
sys.exit(0)
