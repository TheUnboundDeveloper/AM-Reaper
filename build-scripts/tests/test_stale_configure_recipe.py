#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reaper_stale_configure.sh: a change inside a package's configure recipe makes it stale, whatever the line says.

WHY THIS EXISTS. The guard decided "the rules changed" by searching router/Makefile diffs for the package's NAME. The
v3.8.1 SNMP change removed `ucd-snmp/dlmod,` from net-snmp's --with-mib-modules list - a line that does not name
net-snmp - so a warm tree configured on 2026-11-04 was not re-configured, and the local alpha image still carried
the agent's module loader. A clean CI tree configures fresh and was correct. The guard now also looks at the
package's recipe block (from its `<pkg>/stamp-h1:` / `<pkg>/Makefile:` target to the next blank line or target).

WHAT IT DOES. Builds a throwaway git tree with a router/Makefile holding two recipe blocks and two configured
packages, then:
  1. a commit after the configure date removes a line in net-snmp's block that does not name it -> net-snmp STALE,
     the other package not; --fix clears net-snmp's Makefile / config.status / stamp-h1 and nothing of the other;
  2. a commit that changes only the OTHER package's block -> net-snmp not flagged;
  3. a commit made BEFORE the configure date -> nothing flagged;
  4. control: the same tree with the new section cut out of the script -> net-snmp NOT flagged (the old blind spot).
Exit 0 pass, 1 fail, 77 skip (no bash or git).
"""
import os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "reaper_stale_configure.sh")
BASH, GIT = shutil.which("bash"), shutil.which("git")
if not BASH or not GIT:
    print("SKIP: needs bash and git"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ((" :: " + str(detail)[:500]) if (detail and not cond) else ""))
    if not cond:
        fails.append(name)

MAKEFILE = """obj-y += net-snmp-5.9.4 zlib-1.0

net-snmp-5.9.4/stamp-h1:
\tcd $(TOP)/net-snmp-5.9.4 && $(CONFIGURE) --prefix=/usr \\
\t\t--with-mib-modules="\\
\t\tmibII/vacm_vars,\\
\t\tucd-snmp/disk_hw,\\
\t\tucd-snmp/dlmod,\\
\t\tucd-snmp/memory"
\t@touch net-snmp-5.9.4/stamp-h1

net-snmp-5.9.4: net-snmp-5.9.4/stamp-h1
\t@$(MAKE) -C net-snmp-5.9.4

zlib-1.0/stamp-h1:
\tcd $(TOP)/zlib-1.0 && $(CONFIGURE) --prefix=/usr --static
\t@touch zlib-1.0/stamp-h1
"""


def run(cmd, cwd, env=None, check_rc=True):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True)
    if check_rc and r.returncode not in (0, 1):
        raise SystemExit("%s failed: %s" % (cmd[:3], r.stderr[-400:]))
    return r


def tree(script_text):
    d = tempfile.mkdtemp(prefix="rstale_")
    R = os.path.join(d, "release", "src", "router")
    for p in ("net-snmp-5.9.4", "zlib-1.0"):
        os.makedirs(os.path.join(R, p))
        open(os.path.join(R, p, "configure"), "w").write("#!/bin/sh\n")
        open(os.path.join(R, p, "src.c"), "w").write("int x;\n")
    open(os.path.join(R, "Makefile"), "w", newline="\n").write(MAKEFILE)
    open(os.path.join(d, ".gitignore"), "w").write("config.status\nMakefile.gen\nstamp-h1\n")
    open(os.path.join(d, "stale.sh"), "w", newline="\n").write(script_text)
    run([GIT, "init", "-q"], d)
    run([GIT, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "add", "-A"], d)
    t_base = int(time.time()) - 10 * 86400
    env = {"GIT_AUTHOR_DATE": "@%d +0000" % t_base, "GIT_COMMITTER_DATE": "@%d +0000" % t_base}
    run([GIT, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q", "-m", "base"], d, env)
    # configure both packages "5 days ago"
    t_cfg = int(time.time()) - 5 * 86400
    for p in ("net-snmp-5.9.4", "zlib-1.0"):
        for f in ("config.status", "stamp-h1"):
            fp = os.path.join(R, p, f); open(fp, "w").write("configured\n"); os.utime(fp, (t_cfg, t_cfg))
        fp = os.path.join(R, p, "Makefile"); open(fp, "w").write("generated\n"); os.utime(fp, (t_cfg, t_cfg))
    return d, R, t_cfg


def commit(d, R, old, new, when, msg):
    p = os.path.join(R, "Makefile")
    s = open(p).read(); assert s.count(old) == 1, old; open(p, "w", newline="\n").write(s.replace(old, new))
    env = {"GIT_AUTHOR_DATE": "@%d +0000" % when, "GIT_COMMITTER_DATE": "@%d +0000" % when}
    run([GIT, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q", "-am", msg], d, env)


def guard(d, mode="--check"):
    r = run([BASH, os.path.join(d, "stale.sh"), mode, d], d, check_rc=False)
    return r.returncode, r.stdout + r.stderr


src = open(SCRIPT, encoding="utf-8").read().replace("\r\n", "\n")
check("the guard carries the recipe-block section", "configure RECIPE block" in src and "-L \"$_blk:release/src/router/Makefile\"" in src)
m = re.search(r"\n  # 2026-11-16: and any change inside the package's configure RECIPE block.*?\n  fi\n", src, re.S)
check("the section can be cut out for the control run", m is not None)
old_src = src.replace(m.group(0), "\n") if m else src

now = int(time.time())
# 1. a line inside net-snmp's block that does not name it, changed after the configure date
d, R, t_cfg = tree(src)
try:
    commit(d, R, "\t\tucd-snmp/dlmod,\\\n", "", now - 86400, "SNMP: drop the module loader")
    rc, out = guard(d)
    check("1. net-snmp is STALE after a recipe line that does not name it changed", "[STALE] net-snmp-5.9.4" in out and rc == 1, out)
    check("1. the message names the recipe", "(its configure recipe)" in out, out)
    check("1. the other package is not flagged", "[STALE] zlib-1.0" not in out, out)
    rc, out = guard(d, "--fix")
    gone = [f for f in ("Makefile", "config.status", "stamp-h1") if not os.path.exists(os.path.join(R, "net-snmp-5.9.4", f))]
    kept = [f for f in ("Makefile", "config.status", "stamp-h1") if os.path.exists(os.path.join(R, "zlib-1.0", f))]
    check("1. --fix clears net-snmp's Makefile, config.status and stamp-h1", len(gone) == 3, (gone, out))
    check("1. --fix leaves the other package configured", len(kept) == 3, kept)
    check("1. the package's sources are untouched", os.path.exists(os.path.join(R, "net-snmp-5.9.4", "src.c")) and os.path.exists(os.path.join(R, "net-snmp-5.9.4", "configure")))
finally:
    shutil.rmtree(d, ignore_errors=True)

# 2. only the other package's block changed
d, R, t_cfg = tree(src)
try:
    commit(d, R, "--prefix=/usr --static", "--prefix=/usr --static --shared", now - 86400, "zlib: also shared")
    rc, out = guard(d)
    check("2. a change in another package's block does not flag net-snmp", "[STALE] net-snmp-5.9.4" not in out, out)
    check("2. ... and flags that package", "[STALE] zlib-1.0" in out, out)
finally:
    shutil.rmtree(d, ignore_errors=True)

# 3. the change happened before the package was configured
d, R, t_cfg = tree(src)
try:
    commit(d, R, "\t\tucd-snmp/dlmod,\\\n", "", t_cfg - 86400, "SNMP: drop the module loader (before configure)")
    rc, out = guard(d)
    check("3. a recipe change made before the configure date flags nothing", "[STALE]" not in out and rc == 0, out)
finally:
    shutil.rmtree(d, ignore_errors=True)

# 4. control: the guard without the new section misses case 1
d, R, t_cfg = tree(old_src)
try:
    commit(d, R, "\t\tucd-snmp/dlmod,\\\n", "", now - 86400, "SNMP: drop the module loader")
    rc, out = guard(d)
    check("4. control: without the section, net-snmp is NOT flagged (the blind spot this closes)", "[STALE] net-snmp-5.9.4" not in out, out)
finally:
    shutil.rmtree(d, ignore_errors=True)

if fails:
    print("FAIL test_stale_configure_recipe (%d)" % len(fails)); sys.exit(1)
print("PASS test_stale_configure_recipe")
