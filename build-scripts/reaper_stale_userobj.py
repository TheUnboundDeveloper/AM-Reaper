#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reaper_stale_userobj.py - stale userspace objects on a warm build tree (2026-11-17).

WHY. Many packages under release/src/router have no compiler dependency tracking: make recompiles a .c file when
that file changed, and nothing when a header it includes changed. On a tree that is built again and again (a local
build tree) a header change therefore leaves objects compiled against the OLD header beside objects compiled
against the new one. The first case found: a field added to a configuration struct in avahi's core.h recompiled
2 of the library's 34 source files; the other 32 kept the old layout, so the daemon read a socket number and a
pointer from the wrong offsets - no multicast join, a crash when a service file was loaded, an abort at every
stop. A clean tree (CI) compiles everything and never has this; the script is a no-op there.

WHAT IT DOES. For every UNTRACKED .o / .lo under release/src/router that has its source file beside it (or one
directory up, libtool's .libs), it reads the source's #include lines, follows them through the TRACKED headers it
can name with certainty (beside the source, by path inside the package, or a top-level header of shared/ for a
package whose Makefile uses shared), and reports each object that is OLDER than a header it includes.

    reaper_stale_userobj.py <tree>                     report; exit 0
    reaper_stale_userobj.py <tree> --fix               set the stale objects aside (moved, never deleted) so the
                                                       next make compiles them again; writes the list file
    reaper_stale_userobj.py <tree> --verify            after the build: every object set aside must exist again;
                                                       exit 1 and a [WARN] line for each one that does not (a
                                                       package this build does not make, or one a stamp blocks)

Options: --quarantine DIR (default <tree>/../stale_objects/<tree name>-<time>), --list FILE (default
/tmp/reaper_stale_userobj_<tree name>.list). An object tracked by git is never touched."""
import os, re, shutil, subprocess, sys, time

INC = re.compile(r'^[ \t]*#[ \t]*include[ \t]*[<"]([^>"]+)[>"]', re.M)
SRC_EXT = (".c", ".cc", ".cpp")


def scan(tree):
    R = os.path.join(tree, "release", "src", "router")
    if not os.path.isdir(R):
        return R, None
    out = subprocess.run(["git", "-C", R, "ls-files", "-z"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    tracked = set(out.decode("utf-8", "surrogateescape").split("\0"))
    mt, by_base = {}, {}
    for f in tracked:
        if f.endswith((".h", ".hh", ".hpp")):
            p = os.path.join(R, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            mt[f] = os.lstat(p).st_mtime
            by_base.setdefault(os.path.basename(f), []).append(f)
    # 2026-11-18: Broadcom's platform include directory ($(SRCBASE)/include = impl103/main/src/include) is reached by
    # bare <name.h> includes from every package. It sits outside release/src/router, so a change there (bcmnvram.h's
    # nvram_safe_get, batch p11) went unseen and r11 shipped old objects next to the new header. Its tracked headers are
    # indexed too, under paths relative to R, and a bare name not found in the package or shared resolves there.
    plat = {}
    PI = os.path.join(tree, "release", "src-rt-5.04behnd.4916", "bcmdrivers", "broadcom", "net", "wl", "impl103",
                      "main", "src", "include")
    if os.path.isdir(PI):
        out = subprocess.run(["git", "-C", PI, "ls-files", "-z", "--", "."], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL).stdout
        for f in out.decode("utf-8", "surrogateescape").split("\0"):
            if not f.endswith(".h") or "/" in f:
                continue
            p = os.path.join(PI, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            rel = os.path.relpath(p, R)
            mt[rel] = os.lstat(p).st_mtime
            plat[f] = rel
    inc_cache, uses_shared = {}, {}

    def includes(path):
        if path not in inc_cache:
            try:
                inc_cache[path] = INC.findall(open(path, encoding="utf-8", errors="replace").read())
            except OSError:
                inc_cache[path] = []
        return inc_cache[path]

    def pkg_uses_shared(pkg):
        if pkg not in uses_shared:
            hit = pkg in ("shared", "rc", "httpd")
            for mk in ("Makefile", "Makefile.am", "GNUmakefile"):
                p = os.path.join(R, pkg, mk)
                if not hit and os.path.isfile(p):
                    try:
                        hit = "/shared" in open(p, encoding="utf-8", errors="replace").read()
                    except OSError:
                        pass
            uses_shared[pkg] = hit
        return uses_shared[pkg]

    def resolve(name, from_dir, pkg):
        cand = os.path.normpath(os.path.join(from_dir, name))
        if cand in mt:
            return cand
        base = os.path.basename(name)
        inpkg = [f for f in by_base.get(base, ()) if f.split("/", 1)[0] == pkg and ("/" + f).endswith("/" + name)]
        if len(inpkg) == 1:
            return inpkg[0]
        if inpkg:
            return None                 # several headers of that name in the package: not certain, leave it
        if "/" not in name and pkg_uses_shared(pkg) and ("shared/" + name) in mt:
            return "shared/" + name
        if "/" not in name and name in plat:
            return plat[name]
        return None

    stale = {}                          # object (relative to R) -> (header, header mtime)
    for dp, dn, fn in os.walk(R):
        for n in fn:
            if not n.endswith((".o", ".lo")):
                continue
            rel = os.path.relpath(os.path.join(dp, n), R)
            if rel in tracked or os.sep not in rel:
                continue
            pkg = rel.split(os.sep, 1)[0]
            stem = n.rsplit(".", 1)[0]
            d = os.path.dirname(dp) if os.path.basename(dp) == ".libs" else dp
            src = None
            for s in (stem, stem.split("-", 1)[1] if "-" in stem else None):
                for e in SRC_EXT:
                    if s and os.path.isfile(os.path.join(d, s + e)):
                        src = os.path.join(d, s + e)
                        break
                if src:
                    break
            if not src:
                continue
            try:
                om = os.lstat(os.path.join(dp, n)).st_mtime
            except OSError:
                continue
            seen, todo = set(), [src]
            while todo:
                p = todo.pop()
                for inc in includes(p):
                    h = resolve(inc, os.path.relpath(os.path.dirname(p), R), pkg)
                    if not h or h in seen:
                        continue
                    seen.add(h)
                    if mt[h] > om + 2 and (rel not in stale or mt[h] > stale[rel][1]):
                        stale[rel] = (h, mt[h])
                    todo.append(os.path.join(R, h))
    return R, stale


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        print(__doc__)
        return 2
    tree = os.path.abspath(a[0])
    opt = lambda k, d: a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d
    lst = opt("--list", "/tmp/reaper_stale_userobj_%s.list" % os.path.basename(tree.rstrip("/")))
    R = os.path.join(tree, "release", "src", "router")

    if "--verify" in a:
        if not os.path.isfile(lst):
            print("stale-object guard: nothing was set aside before this build")
            return 0
        rows = [l.rstrip("\n").split("\t") for l in open(lst, encoding="utf-8", errors="surrogateescape")
                if "\t" in l and not l.startswith("#")]
        missing = [r[0] for r in rows if not os.path.isfile(os.path.join(R, r[0]))]
        for m in missing:
            print("[WARN] stale-object guard: set aside before the build and NOT compiled again: " + m)
        print("stale-object guard: %d object(s) were set aside, %d compiled again, %d missing"
              % (len(rows), len(rows) - len(missing), len(missing)))
        if missing:
            print("[WARN] stale-object guard: a package this build does not make is harmless here; for one it does "
                  "make, the image may carry a binary linked before the header change - run that package's clean "
                  "target. The objects are kept in the quarantine named in " + lst + ".done")
            os.replace(lst, lst + ".done")
            return 1
        os.remove(lst)
        return 0

    R, stale = scan(tree)
    if stale is None:
        print("stale-object guard: no release/src/router under " + tree)
        return 0
    if not stale:
        print("stale-object guard: no object is older than a header it includes")
        return 0            # a list left by an earlier --fix stays: its objects still await --verify
    per = {}
    for o, (h, m) in stale.items():
        per.setdefault((o.split(os.sep, 1)[0], h, m), []).append(o)
    for (pkg, h, m), objs in sorted(per.items()):
        print("  %-24s %4d object(s) older than %s (%s)" % (pkg, len(objs), h, time.strftime("%Y-%m-%d %H:%M", time.localtime(m))))
    if "--fix" not in a:
        print("stale-object guard: %d stale object(s) in %d package(s) - run with --fix before building"
              % (len(stale), len(set(k[0] for k in per))))
        return 0
    q = opt("--quarantine", os.path.join(os.path.dirname(tree.rstrip("/")), "stale_objects",
                                         os.path.basename(tree.rstrip("/")) + "-" + time.strftime("%Y%m%d-%H%M%S")))
    with open(lst, "a", encoding="utf-8", errors="surrogateescape") as f:      # "a": an earlier, unverified list is kept
        f.write("# quarantine\t%s\n" % q)
        for o in sorted(stale):
            dst = os.path.join(q, o)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(os.path.join(R, o), dst)
            f.write("%s\t%s\n" % (o, stale[o][0]))
    print("stale-object guard: %d stale object(s) set aside in %s - this build compiles them again" % (len(stale), q))
    return 0


if __name__ == "__main__":
    sys.exit(main())
