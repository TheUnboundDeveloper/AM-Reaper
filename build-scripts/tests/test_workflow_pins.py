#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every GitHub Action a workflow uses is pinned to a full commit SHA.

WHY THIS EXISTS. Security review 2026-10-20 (F-5): the workflows pulled
`actions/checkout@v7`, `actions/cache@v6` and `actions/upload-artifact@v7` by
their MAJOR tags. A major tag is a moving pointer the action's maintainers (or
anyone who takes over their account) can repoint at any commit, and the build
job runs that code with the repository checked out - the published firmware is
whatever that job produces. GitHub's own hardening guidance is to pin to a
full-length commit SHA and let dependabot propose the bumps as pull requests
(.github/dependabot.yml). A tag can come back by accident (a copied snippet, a
dependabot PR edited by hand); this test is the gate.

WHAT IT DOES. For every `uses:` in .github/workflows/*.yml that names a remote
action (owner/repo[/path]@ref), the ref must be 40 hex characters and the line
must carry a `# v...` comment naming the version it stands for. Local reusable
workflows (`./...`) and docker:// references are not actions from a tag and are
exempt. Exit 0 pass, 1 fail, 77 skipped (no workflows directory)."""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.join(HERE, "..", "..", ".github", "workflows")
files = sorted(glob.glob(os.path.join(WF, "*.yml")) + glob.glob(os.path.join(WF, "*.yaml")))
if not files:
    print("SKIP: no .github/workflows directory next to build-scripts/")
    sys.exit(77)

USES = re.compile(r'^\s*(?:-\s*)?uses:\s*(\S+)(.*)$')
REMOTE = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@(\S+)$')
bad, seen = [], 0
for f in files:
    for n, line in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
        m = USES.match(line)
        if not m:
            continue
        ref, rest = m.group(1).strip('"\''), m.group(2)
        if ref.startswith("./") or ref.startswith("docker://"):
            continue
        seen += 1
        r = REMOTE.match(ref)
        where = "%s:%d" % (os.path.basename(f), n)
        if not r:
            bad.append("%s: unrecognised uses: %s" % (where, ref)); continue
        sha = r.group(1)
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            bad.append("%s: %s is not pinned to a 40-hex commit SHA" % (where, ref)); continue
        if not re.search(r"#\s*v\d", rest):
            bad.append("%s: %s lacks the '# vN.N.N' comment that says what the SHA stands for" % (where, ref))

if bad:
    print("FAIL: %d action reference(s) not pinned:" % len(bad))
    for b in bad:
        print("  - " + b)
    sys.exit(1)
print("ok   %d remote action reference(s) in %d workflow(s), every one a 40-hex commit SHA with its version comment" % (seen, len(files)))
print("PASS test_workflow_pins")
