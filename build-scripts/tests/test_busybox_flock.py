#!/usr/bin/env python3
"""No router script asks busybox for an option it does not have (2026-10-26).

WHY. The router's busybox 1.25.1 `flock` knows only -s -x -u -n. Wallguard's table build took its lock with
`flock -w 300`, which failed at once on the router, so every build was "skipped" and Wallguard never blocked
anything after its first metal rungs; the host tests used util-linux flock, which has -w, and passed. Warden's
counter scripts used `flock -w` the same way and silently ran without their lock.

WHAT IT DOES. (1) No shell script under the router tree and no script rc emits from C carries `flock -w` (or any
flock option outside -s -x -u -n). (2) wallguard.sh's lock_wait, run under a fake flock that behaves like busybox
1.25 (refuses -w, honours -n), takes a free lock at once, waits for a held one and gives up after its limit.
"""
import os, re, shutil, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "rc")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

# (1) static: every flock invocation in Reaper's scripts and in the scripts rc / httpd emit
bad = []
roots = ["rc", "httpd", "wallguard", "rednsd", "others", "dreadwatch", "rtrafd", "shared"]
for r in roots:
    for dp, dn, fn in os.walk(os.path.join(SRC, r)):
        for f in fn:
            if not f.endswith((".c", ".h", ".sh")) and f not in ("reaper_diag",): continue
            p = os.path.join(dp, f)
            try: t = open(p, encoding="utf-8", errors="replace").read()
            except Exception: continue
            for m in re.finditer(r"\bflock((?:\s+-[A-Za-z]+(?:\s+\d+)?)+)", t):
                opts = re.findall(r"-([A-Za-z]+)", m.group(1))
                if any(c not in "sxun" for o in opts for c in o):
                    bad.append("%s:%d %s" % (os.path.relpath(p, SRC), t[:m.start()].count("\n") + 1, m.group(0).strip()))
check("no flock option the router's busybox 1.25 lacks (only -s -x -u -n)", not bad, bad)

# (2) lock_wait under a busybox-faithful flock
sh = open(os.path.join(SRC, "wallguard", "wallguard.sh"), encoding="utf-8").read()
m = re.search(r"\nlock_wait\(\) \{.*?\n\}\n", sh, re.S)
check("wallguard.sh defines lock_wait and uses it for the build and fold locks",
      m and "lock_wait 8 300 ||" in sh and "lock_wait 6 10 ||" in sh, bool(m))
real = shutil.which("flock")
if m and real:
    work = tempfile.mkdtemp(prefix="bbflock_")
    try:
        fake = os.path.join(work, "flock")
        open(fake, "w").write('#!/bin/sh\nfor a; do case "$a" in -w|-w*|--wait|--timeout) echo "flock: invalid option" >&2; exit 1;; esac; done\nexec %s "$@"\n' % real)
        os.chmod(fake, 0o755)
        us = os.path.join(work, "usleep")	# the router has busybox usleep; the host may not
        open(us, "w").write('#!/bin/sh\nexec sleep 0.2\n'); os.chmod(us, 0o755)
        lock = os.path.join(work, "l")
        env = dict(os.environ, PATH=work + os.pathsep + os.environ["PATH"])
        body = m.group(0)
        def run(script, timeout=30):
            return subprocess.run(["sh", "-c", body + script], capture_output=True, text=True, env=env, timeout=timeout)
        r = run('exec 9>"%s"; flock -w 1 9; echo "w=$?"' % lock)
        check("the fake refuses -w like busybox 1.25 (the old code's failure)", "w=1" in r.stdout, r.stdout + r.stderr)
        t0 = time.time(); r = run('exec 9>"%s"; lock_wait 9 5 && echo got' % lock)
        check("a free lock is taken at once", "got" in r.stdout and time.time() - t0 < 2, (r.stdout, r.stderr, time.time() - t0))
        holder = subprocess.Popen(["sh", "-c", 'exec 9>"%s"; flock -n 9; sleep 2' % lock])
        time.sleep(0.3)
        t0 = time.time(); r = run('exec 8>"%s"; lock_wait 8 10 && echo got' % lock)
        dt = time.time() - t0
        check("a held lock is waited for and taken when it is released", "got" in r.stdout and 1.0 < dt < 8, (r.stdout, r.stderr, dt))
        holder.wait()
        holder = subprocess.Popen(["sh", "-c", 'exec 9>"%s"; flock -n 9; sleep 6' % lock])
        time.sleep(0.3)
        t0 = time.time(); r = run('exec 8>"%s"; lock_wait 8 1 && echo got || echo gaveup' % lock)
        dt = time.time() - t0
        check("a lock held past the limit is given up after about the limit", "gaveup" in r.stdout and dt < 5.5, (r.stdout, dt))
        holder.wait()
    finally:
        shutil.rmtree(work, ignore_errors=True)
else:
    print("note: no host flock - the run half is skipped")

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
