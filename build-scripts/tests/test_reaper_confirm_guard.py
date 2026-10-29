#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every reaperConfirm() callback checks the answer before acting.

WHY THIS EXISTS. reaperConfirm(msg, opts, cb) (www/reaper_util.js) calls cb(true) on OK and cb(false)
on Cancel, Escape or a click outside the box. Firewall > Status > Security review's "Accept current
state as baseline" passed a callback that ignored the argument, so Cancel accepted the baseline
anyway (owner, metal, 2026-10-23). This suite fails on any inline callback that does not take the
answer and test it before doing anything else.

WHAT IT CHECKS. Every `reaperConfirm(` call in www (Reaper pages, kit scripts, stock pages): the third
argument is an inline `function(<name>){`, and the callback's first statement tests <name> - an early
`if(!<name>...) return`, or an `if(<name>)` that wraps the action. A callback passed by name is
reported for a manual look (none exist today). Exit 0 pass, 1 fail, 77 skipped (no router tree).
"""
import glob, os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
W = os.path.join(SRC, "www")
if not SRC or not os.path.isfile(os.path.join(W, "reaper_util.js")):
    print("SKIP: no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)"); sys.exit(77)
extra = [p for p in sys.argv[2:] if os.path.isfile(p)]   # pages not installed yet (a wave in progress)

files = sorted(set(glob.glob(os.path.join(W, "*.asp")) + glob.glob(os.path.join(W, "*.js")) +
                   glob.glob(os.path.join(W, "reaper", "*.js")) + glob.glob(os.path.join(W, "*.htm")) + extra))
bad, named, total = [], [], 0
for f in files:
    t = open(f, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"\breaperConfirm\s*\(", t):
        if t[max(0, m.start() - 7):m.start()] == "window.":
            continue                                   # the definition
        line = t.count("\n", 0, m.start()) + 1
        seg = t[m.end():m.end() + 2500]
        # walk to the third top-level argument
        depth, args, start, i, q = 0, [], 0, 0, None
        while i < len(seg):
            c = seg[i]
            if q:
                if c == "\\": i += 2; continue
                if c == q: q = None
            elif c in "'\"`": q = c
            elif c in "([{": depth += 1
            elif c in ")]}":
                if depth == 0: args.append(seg[start:i]); break
                depth -= 1
            elif c == "," and depth == 0: args.append(seg[start:i]); start = i + 1
            i += 1
        total += 1
        cb = args[2].strip() if len(args) >= 3 else ""
        fm = re.match(r"function\s*\w*\s*\(\s*(\w*)\s*\)\s*\{(.*)", cb, re.S)
        where = "%s:%d" % (os.path.relpath(f, W) if f.startswith(W) else f, line)
        if not fm:
            named.append(where); continue
        a, body = fm.group(1), fm.group(2).lstrip()
        ok = bool(a) and (re.match(r"if\s*\(\s*!\s*%s\b[^)]*\)\s*(\{\s*)?return\b" % a, body) or
                          re.match(r"if\s*\(\s*%s\s*\)" % a, body))
        if not ok:
            bad.append("%s  callback(%s): %s" % (where, a, body[:70].replace("\n", " ")))

print("reaperConfirm calls checked: %d" % total)
for n in named:
    print("note: callback passed by name, check by hand: " + n)
if bad:
    print("FAIL: a reaperConfirm callback acts without testing the answer (Cancel would act):")
    for b in bad:
        print("  " + b)
    sys.exit(1)
print("PASS test_reaper_confirm_guard")
