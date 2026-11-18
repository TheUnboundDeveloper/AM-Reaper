#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reaper_stale_userobj.py: objects older than a header they include are found, set aside and checked after the build.

WHY THIS EXISTS. Packages without compiler dependency tracking recompile a source file only when that file
changed. On a tree that is built repeatedly, a header change left 32 of avahi's 34 library objects on the old
struct layout (2026-11-14 to 2026-11-17 local images): no multicast join, a crash on a service reload, an abort at
every stop. The guard runs before every local build; this test pins what it may and may not touch.

WHAT IT DOES. Builds a small git tree shaped like release/src/router, sets file times, and runs the script in its
three modes. Exit 0 pass, 1 fail, 77 skipped (no git)."""
import os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "reaper_stale_userobj.py")
if not shutil.which("git"):
    print("SKIP: no git"); sys.exit(77)
fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))


tmp = tempfile.mkdtemp(prefix="staleobj_")
tree = os.path.join(tmp, "tree")
R = os.path.join(tree, "release", "src", "router")
T0 = time.time() - 100000          # "built" time of the old objects
T1 = T0 + 5000                     # a header changed after that
T2 = T1 + 5000                     # objects built after the change


def put(rel, text="", t=None):
    p = os.path.join(R, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", newline="\n").write(text)
    if t:
        os.utime(p, (t, t))


def run(*args):
    r = subprocess.run([sys.executable, "-I", TOOL, tree] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=120)
    return r.returncode, r.stdout


# shared/: one header changed late, one not
put("shared/shared.h", '#include "inner.h"\n', T0 - 10)
put("shared/inner.h", "/* changed */\n", T1)
put("shared/common.h", "/* a name other packages also use */\n", T1)
put("shared/Makefile", "all:\n")
# pkga: uses shared (Makefile says so), includes <shared.h> -> inner.h changed -> a.o stale; b.o includes nothing changed
put("pkga/Makefile", "CFLAGS += -I$(TOP)/shared\n")
put("pkga/a.c", "#include <shared.h>\n", T0 - 10)
put("pkga/b.c", '#include "b.h"\n', T0 - 10)
put("pkga/b.h", "", T0 - 10)
put("pkga/a.o", "old", T0)
put("pkga/b.o", "old", T0)
# pkgb: libtool layout, own header changed -> the .lo, the plain .o and the .libs object are all stale
put("pkgb/Makefile", "all:\n")
put("pkgb/core/core.h", "/* field added */\n", T1)
put("pkgb/core/server.c", '#include "core.h"\n', T0 - 10)
put("pkgb/core/entry.c", '#include "core.h"\n', T0 - 10)
put("pkgb/core/libx_la-server.lo", "new", T2)
put("pkgb/core/.libs/libx_la-server.o", "new", T2)
put("pkgb/core/libx_la-entry.lo", "old", T0)
put("pkgb/core/libx_la-entry.o", "old", T0)
put("pkgb/core/.libs/libx_la-entry.o", "old", T0)
# pkgc: a tracked (prebuilt) object older than its header - never touched
put("pkgc/Makefile", "CFLAGS += -I$(TOP)/shared\n")
put("pkgc/c.h", "", T1)
put("pkgc/c.c", '#include "c.h"\n', T0 - 10)
put("pkgc/c.o", "prebuilt", T0)
# pkgd: includes "common.h", has none, and its Makefile does not use shared -> shared/common.h must NOT be taken
put("pkgd/Makefile", "all:\n")
put("pkgd/d.c", '#include "common.h"\n#include <stdio.h>\n', T0 - 10)
put("pkgd/d.o", "old", T0)
# pkge: two headers of the same name in the package -> not certain -> left alone
put("pkge/Makefile", "all:\n")
put("pkge/x/config.h", "", T1)
put("pkge/y/config.h", "", T1)
put("pkge/z/e.c", "#include <config.h>\n", T0 - 10)
put("pkge/z/e.o", "old", T0)
# an object with no source beside it
put("pkga/orphan.o", "old", T0)
# pkgf: a bare <bcmnvram.h> from Broadcom's platform include directory (outside release/src/router), changed late ->
# f.o stale (2026-11-18: the guard did not see that directory and r11 kept old objects beside the new header)
PLATINC = "../../src-rt-5.04behnd.4916/bcmdrivers/broadcom/net/wl/impl103/main/src/include/bcmnvram.h"
put(PLATINC, "/* nvram_safe_get changed */\n", T1)
put("pkgf/Makefile", "all:\n")
put("pkgf/f.c", "#include <bcmnvram.h>\n", T0 - 10)
put("pkgf/f.o", "old", T0)

g = lambda *a: subprocess.run(["git", "-C", tree] + list(a), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
g("init", "-q")
g("add", "-A", ":!*.o", ":!*.lo")
g("add", "-f", "release/src/router/pkgc/c.o")
g("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "tree")
# git does not change file times; set them again for safety (the index refresh may not, an editor could)
for rel, t in (("shared/inner.h", T1), ("shared/common.h", T1), ("pkgb/core/core.h", T1), ("pkgc/c.h", T1),
               ("pkge/x/config.h", T1), ("pkge/y/config.h", T1), ("shared/shared.h", T0 - 10), (PLATINC, T1)):
    os.utime(os.path.join(R, rel), (t, t))

WANT = sorted(["pkga/a.o", "pkgb/core/libx_la-entry.lo", "pkgb/core/libx_la-entry.o", "pkgb/core/.libs/libx_la-entry.o",
               "pkgf/f.o"])
exists = lambda rel: os.path.isfile(os.path.join(R, rel))
lst, q = os.path.join(tmp, "list"), os.path.join(tmp, "quarantine")

rc, out = run("--list", lst)
check("report: exit 0, nothing moved, 5 stale objects in 3 packages named",
      rc == 0 and all(exists(o) for o in WANT) and "5 stale object(s) in 3 package(s)" in out, out)
check("report: the header behind each is named (through one include level for shared.h -> inner.h)",
      "older than shared/inner.h" in out and "older than pkgb/core/core.h" in out, out)
check("report: a bare <bcmnvram.h> resolves into Broadcom's platform include directory", "include/bcmnvram.h" in out, out)
rc, out = run("--fix", "--list", lst, "--quarantine", q)
check("fix: the five stale objects are set aside in the quarantine (moved, same relative path)",
      rc == 0 and not any(exists(o) for o in WANT) and all(os.path.isfile(os.path.join(q, o)) for o in WANT), out)
check("fix: fresh objects, an object whose includes did not change, an orphan and a tracked object are untouched",
      all(exists(o) for o in ("pkga/b.o", "pkga/orphan.o", "pkgb/core/libx_la-server.lo", "pkgb/core/.libs/libx_la-server.o", "pkgc/c.o")))
check("fix: a header of the same name in shared/ is not taken for a package that does not use shared; "
      "two candidates in one package are not guessed", exists("pkgd/d.o") and exists("pkge/z/e.o"))
put(WANT[0], "rebuilt")
rc, out = run("--verify", "--list", lst)
check("verify: objects that were not compiled again are named in [WARN] lines, exit 1, the list is kept as .done",
      rc == 1 and out.count("NOT compiled again") == 4 and "[WARN]" in out and "1 compiled again, 4 missing" in out
      and not os.path.isfile(lst) and os.path.isfile(lst + ".done"), out)
os.replace(lst + ".done", lst)
for o in WANT:
    put(o, "rebuilt")
rc, out = run("--verify", "--list", lst)
check("verify: all compiled again -> pass, and the list is cleared",
      rc == 0 and "5 compiled again, 0 missing" in out and not os.path.isfile(lst), out)
rc, out = run("--fix", "--list", lst, "--quarantine", q + "2")
check("a second run on the rebuilt tree finds nothing", rc == 0 and "no object is older" in out and not os.path.isdir(q + "2"), out)
rc, out = run("--verify", "--list", lst)
check("verify with nothing set aside passes", rc == 0, out)
shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("%d check(s) FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
