#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every self-heal rwatch hands to `reaper_lockrun` must be on reaper_lockrun's allowlist.

WHY THIS EXISTS. reaper_lockrun (rc/rwatch.c, reaper_lockrun_main) runs a heal script under the
firewall fcntl lock and refuses anything not on its static allowlist - return 1, nothing run.
rwatch invokes it with stdout and stderr discarded, so a refused heal is indistinguishable from a
successful one on the box: the tick logs "re-applying" and re-applies nothing. That shipped in
v3.3.4: section 3f (rules-chain-drift) called `reaper_lockrun /tmp/reaper_fw/apply.sh` and the
path was never added to the list, so the rules engine's v4 chains stayed gone for 20 minutes on
the owner's router on 2026-10-08 while the log claimed two re-applies. Same class as the v3.0.1
`rc reaper_lockrun` dispatch bug (see verify_markers.txt): a heal that cannot fail loudly.

WHAT IT DOES. Reads rc/rwatch.c and rc/rdnshc.c (the two callers), collects every script path
handed to reaper_lockrun - literal, or through a shell variable assigned within the preceding
lines - and checks each against the allowlist parsed out of reaper_lockrun_main. Also pins the
heals that must stay listed. Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
rwatch = os.path.join(src_root, "rc", "rwatch.c") if src_root else ""
if not rwatch or not os.path.isfile(rwatch):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

with open(rwatch, encoding="utf-8", errors="replace") as f:
    src = f.read()

# --- the allowlist: the string literals between `ok[] = {` and the terminating NULL
m = re.search(r"reaper_lockrun_main\s*\(int argc[^{]*\{.*?ok\[\]\s*=\s*\{(.*?)\bNULL\b", src, re.S)
if not m:
    die("reaper_lockrun_main's ok[] allowlist not found in rc/rwatch.c")
allow = set(re.findall(r'"(/[^"]+)"', m.group(1)))
check("allowlist parsed (at least the four original heals)", len(allow) >= 4, sorted(allow))

# --- every reaper_lockrun invocation in the generated shell of the callers
callers = [rwatch]
rdnshc = os.path.join(src_root, "rc", "rdnshc.c")
if os.path.isfile(rdnshc):
    callers.append(rdnshc)

used = {}   # path -> "file:line"
unresolved = []
for path in callers:
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        # a C comment that merely talks about the wrapper is not a call
        if "reaper_lockrun" not in line or line.lstrip().startswith(("*", "/*", "//")):
            continue
        for call in re.finditer(r'reaper_lockrun\s+(\\?"?)(\$[A-Za-z_][A-Za-z0-9_]*|/[A-Za-z0-9_./-]+)', line):
            tok = call.group(2)
            where = "%s:%d" % (os.path.basename(path), i + 1)
            if tok.startswith("/"):
                used[tok] = where
                continue
            # a variable: find its most recent assignment in the preceding lines (the PBR
            # heals set _sh/_shr 13-22 lines ahead of the call, candidate-or-apply on one line)
            var = tok[1:]
            resolved = []
            for back in range(i, max(-1, i - 40), -1):
                for a in re.finditer(r'\b' + re.escape(var) + r'=\\?"?(/[A-Za-z0-9_./-]+)', lines[back]):
                    resolved.append(a.group(1))
                if resolved:
                    break
            if resolved:
                for r in resolved:
                    used[r] = where + " via $" + var
            else:
                unresolved.append((where, tok))

check("every reaper_lockrun call hands over a path this test can read", not unresolved, unresolved)
check("at least the heals this suite knows about are invoked (3c/3d/3f, PBR, hcgate)", len(used) >= 5, sorted(used))
for p in sorted(used):
    check("invoked heal is allowlisted: %s (%s)" % (p, used[p]), p in allow, "allowlist: %s" % sorted(allow))

# --- the heals that must stay listed, by name: the regression of 2026-10-08 and the
# heals the earlier passes depended on
for must in ("/tmp/reaper_fw/apply.sh", "/tmp/rwarden/apply.sh", "/tmp/reaper/hook.sh", "/tmp/reaper_pbr/apply.sh"):
    check("allowlist pins %s" % must, must in allow)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall %s checks passed" % "lockrun-allowlist")
sys.exit(0)
