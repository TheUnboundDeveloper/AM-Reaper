#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every help link a page carries into the guide lands on a real heading (forum report, 2026-11-02).

WHY THIS EXISTS. Warden's ? button linked REAPER-GUIDE.md#43-warden after section 4.3 had been renamed
"Bastion", so the link opened the top of the guide and nothing failed. This checks every
`docs/<FILE>.md#<anchor>` link in the router's www tree against the headings of that file in this repo,
using GitHub's anchor rules (lower case, punctuation dropped, spaces to dashes, -1/-2 for repeats), plus any
explicit <a id="..."> / <a name="..."> anchors (kept for links in already-shipped firmware).

Exit 0 pass, 1 fail, 77 skipped (no router source tree or no docs/).
"""
import collections, os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WWW = os.path.join(SRC, "www") if SRC else ""
DOCS = os.environ.get("REAPER_DOCS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs"))
if not WWW or not os.path.isdir(WWW):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
if not os.path.isdir(DOCS):
    print("SKIP: no docs/ directory"); sys.exit(77)

def slug(h):
    s = re.sub(r"[^\w\- ]", "", h.strip().lower())
    return s.replace(" ", "-")

def anchors(path):
    known, seen, code = set(), collections.Counter(), False
    text = open(path, encoding="utf-8").read()
    for line in text.splitlines():
        if line.startswith("```"):
            code = not code
            continue
        if code:
            continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            b = slug(m.group(2))
            known.add(b if not seen[b] else "%s-%d" % (b, seen[b]))
            seen[b] += 1
    known.update(re.findall(r'<a\s+(?:id|name)="([^"]+)"', text))
    return known

uses = collections.defaultdict(set)
for root, _, files in os.walk(WWW):
    for f in files:
        p = os.path.join(root, f)
        if not f.endswith((".asp", ".js", ".html", ".htm")) or not os.path.isfile(p):
            continue	# a dangling sysdep link (seen on the 3006.102.8 tree) is not a page
        t = open(p, encoding="utf-8", errors="replace").read()
        for doc, a in re.findall(r"docs/([A-Za-z0-9_\-]+\.md)#([A-Za-z0-9_\-]+)", t):
            uses[(doc, a)].add(f)

fails, cache = [], {}
for (doc, a), pages in sorted(uses.items()):
    p = os.path.join(DOCS, doc)
    if doc not in cache:
        cache[doc] = anchors(p) if os.path.isfile(p) else None
    ok = cache[doc] is not None and a in cache[doc]
    print(("ok   " if ok else "FAIL ") + "%s#%s  (%s)" % (doc, a, ", ".join(sorted(pages))))
    if not ok:
        fails.append("%s#%s from %s" % (doc, a, ", ".join(sorted(pages))))
print("\n%d link(s), %d unresolved" % (len(uses), len(fails)))
if not uses:
    print("FAIL: no help links found - the pattern no longer matches the pages"); sys.exit(1)
if fails:
    print("\n".join(fails)); sys.exit(1)
