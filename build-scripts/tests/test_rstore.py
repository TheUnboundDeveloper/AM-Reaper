#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rstore - the long-term store's no-follow writer (shared/reaper_store_io.h, wallguard/rstore.c, 2026-10-21).

WHY THIS EXISTS. A USB long-term store is a volume other people can write: in guest share mode the
firmware's smb.conf sets "guest account = admin" (uid 0), so anyone on the LAN can plant a symlink
inside <volume>/.reaper. The first cut of the Wallguard / Dreadwatch / Encrypted DNS storage rows wrote
there from shell by path (`>>`, `cp`, `rm`), and root followed whatever was planted - an arbitrary
file write, truncate or delete on the router (/jffs/scripts included). The review moved every such
write to rstore, which opens the base from its trusted parent and every level below with
openat(O_NOFOLLOW|O_DIRECTORY), files O_NOFOLLOW and regular-only, and replaces by rename.

WHAT IT DOES. Builds rstore for the host with test trust roots and attacks each operation: a link
planted at the file, at a sub-folder, at .reaper itself, at the temp name of a put, at a stamp; a
FIFO; an oversized file; a base outside the two allowed places; a three-level sub-path; a prune
whose folder holds a link to a precious file. Every case must leave the target outside the store
untouched. Plus the normal paths: append + rotation, put/get round trip, prune keeps the kept,
stamp creates once.
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "wallguard", "rstore.c")):
    print("SKIP: no router source tree with wallguard/rstore.c"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC or not sys.platform.startswith("linux"):
    print("SKIP: needs a host compiler on Linux"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

work = tempfile.mkdtemp(prefix="rstore_")
try:
    mnt, jffs = os.path.join(work, "mnt"), os.path.join(work, "jffs")
    vol = os.path.join(mnt, "VOL"); base = os.path.join(vol, ".reaper")
    os.makedirs(base); os.makedirs(jffs)
    exe = os.path.join(work, "rstore")
    b = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(SRC, "shared"),
                        '-DRSTORE_TRUST_MNT="%s"' % mnt, '-DRSTORE_TRUST_JFFS="%s"' % jffs, "-DRSTORE_NEED_MOUNT=0",
                        "-o", exe, os.path.join(SRC, "wallguard", "rstore.c")], capture_output=True, text=True)
    check("rstore builds on the host (-Wall -Wextra -Werror)", b.returncode == 0, b.stderr[-500:])
    if b.returncode != 0:
        raise SystemExit
    def rs(*a, data=None):
        return subprocess.run([exe] + list(a), input=data, capture_output=True, text=True).returncode
    precious = os.path.join(work, "precious"); open(precious, "w").write("KEEP\n")
    def intact(): return open(precious).read() == "KEEP\n"

    # append + rotation
    r1 = rs("append", base, "wallguard", "blocked.log", "20", data="0123456789\n")
    r2 = rs("append", base, "wallguard", "blocked.log", "20", data="abcdefghij\n")
    r3 = rs("append", base, "wallguard", "blocked.log", "20", data="third\n")
    sh = os.path.join(base, "wallguard")
    check("append creates the sub-folder 0700 and the file 0600, and appends",
          r1 == r2 == r3 == 0 and oct(os.stat(sh).st_mode & 0o777) == "0o700"
          and oct(os.stat(os.path.join(sh, "blocked.log.1")).st_mode & 0o777) == "0o600")
    check("past the cap the log rolls to .1 before the append",
          open(os.path.join(sh, "blocked.log.1")).read() == "0123456789\nabcdefghij\n" and open(os.path.join(sh, "blocked.log")).read() == "third\n")
    # a link planted at the file
    os.remove(os.path.join(sh, "blocked.log")); os.symlink(precious, os.path.join(sh, "blocked.log"))
    r = rs("append", base, "wallguard", "blocked.log", "0", data="EVIL\n")
    check("append: a link planted at the file is removed, never written through",
          intact() and not os.path.islink(os.path.join(sh, "blocked.log")) and open(os.path.join(sh, "blocked.log")).read() == "EVIL\n", r)
    # a link planted at the sub-folder
    outside = os.path.join(work, "outside"); os.makedirs(outside)
    os.symlink(outside, os.path.join(base, "dreadwatch"))
    r = rs("append", base, "dreadwatch", "blocked.log", "0", data="EVIL\n")
    check("append: a sub-folder that is a link is refused (nothing written outside the store)", r != 0 and os.listdir(outside) == [])
    # .reaper itself a link
    vol2 = os.path.join(mnt, "VOL2"); os.makedirs(vol2); os.symlink(outside, os.path.join(vol2, ".reaper"))
    r = rs("append", os.path.join(vol2, ".reaper"), "-", "x.log", "0", data="EVIL\n")
    check("a .reaper that is a link is refused", r != 0 and os.listdir(outside) == [])
    # bases outside the two allowed places, and path tricks
    check("a base outside /jffs/reaper and <mnt>/<vol>/.reaper is refused",
          rs("append", outside, "-", "x.log", "0", data="x") != 0 and rs("append", base + "/..", "-", "x.log", "0", data="x") != 0
          and rs("append", os.path.join(mnt, "VOL", "sub", ".reaper"), "-", "x.log", "0", data="x") != 0)
    check("names with a slash, a leading dot or '..' are refused; three sub levels are refused",
          rs("append", base, "-", "../x", "0", data="x") != 0 and rs("append", base, "-", ".hidden", "0", data="x") != 0
          and rs("append", base, "../..", "x", "0", data="x") != 0 and rs("append", base, "a/b/c", "x", "0", data="x") != 0)
    # put / get
    src = os.path.join(work, "src.txt"); open(src, "w").write("0.0.0.0 ads.example\n")
    os.makedirs(os.path.join(sh, "lists"), exist_ok=True)
    os.symlink(precious, os.path.join(sh, "lists", "one"))
    os.symlink(precious, os.path.join(sh, "lists", "one.%d.tmp" % 999999))
    r = rs("put", base, "wallguard/lists", "one", src)
    one = os.path.join(sh, "lists", "one")
    check("put: a link planted at the name is replaced by the new file, never followed",
          r == 0 and intact() and not os.path.islink(one) and open(one).read() == "0.0.0.0 ads.example\n")
    dst = os.path.join(work, "ram", "one"); os.makedirs(os.path.dirname(dst))
    check("get: the regular file comes back", rs("get", base, "wallguard/lists", "one", dst, "1000") == 0 and open(dst).read() == open(src).read())
    os.remove(one); os.symlink(precious, one)
    check("get: a link at the name is refused (no root read through it)", rs("get", base, "wallguard/lists", "one", dst, "1000") != 0 and not os.path.exists(dst))
    os.remove(one); os.mkfifo(one)
    check("get: a FIFO is refused without blocking", rs("get", base, "wallguard/lists", "one", dst, "1000") != 0)
    os.remove(one); open(one, "w").write("x" * 5000)
    check("get: a file over the size cap is refused and leaves no partial copy",
          rs("get", base, "wallguard/lists", "one", dst, "1000") != 0 and not os.path.exists(dst))
    # prune
    lists = os.path.join(sh, "lists")
    for n in ("keepme", "gone"):
        open(os.path.join(lists, n), "w").write(n)
    os.symlink(precious, os.path.join(lists, "linky"))
    open(os.path.join(lists, "Odd.Name"), "w").write("x")
    r = rs("prune", base, "wallguard/lists", "keepme")
    left = sorted(os.listdir(lists))
    check("prune: unkept [a-z0-9_] names go (a link is removed itself), kept names and other names stay",
          r == 0 and intact() and "keepme" in left and "gone" not in left and "linky" not in left and "Odd.Name" in left, left)
    # stamp
    st = os.path.join(base, "shl.since")
    check("stamp: created once, never rewritten",
          rs("stamp", base, "shl.since", "100") == 0 and rs("stamp", base, "shl.since", "200") == 0 and open(st).read() == "100")
    os.symlink(precious, os.path.join(base, "dw.since"))
    check("stamp: a link at the name is not written through", rs("stamp", base, "dw.since", "300") == 0 and intact())
    # ring (device / channel-quality history): keep the last N lines
    for i in range(7):
        rs("ring", base, "-", "devhist.log", "5", data="line%d\n" % i)
    dh = os.path.join(base, "devhist.log")
    check("ring: only the last N lines are kept", open(dh).read() == "".join("line%d\n" % i for i in range(2, 7)), open(dh).read())
    os.remove(dh); os.symlink(precious, dh)
    r = rs("ring", base, "-", "devhist.log", "5", data="x\n")
    check("ring: a link planted at the name is removed, never written or trimmed through", intact() and not os.path.islink(dh))
    # review 2026-10-24 (Q-A-5): a ring runs a tenth over N before it is trimmed - one rewrite per N/10 appends, not one per append
    sl = os.path.join(base, "slack.log")
    for i in range(22):
        rs("ring", base, "-", "slack.log", "20", data="s%d\n" % i)
    check("ring: up to N + N/10 lines stay untrimmed (no rewrite per append)", open(sl).read() == "".join("s%d\n" % i for i in range(22)), open(sl).read())
    rs("ring", base, "-", "slack.log", "20", data="s22\n")
    check("ring: the append past the slack trims back to the last N", open(sl).read() == "".join("s%d\n" % i for i in range(3, 23)), open(sl).read())
    # rmtree (an incident-dump folder)
    inc = os.path.join(base, "rwatch", "inc-100"); os.makedirs(inc)
    open(os.path.join(inc, "summary.txt"), "w").write("s")
    os.symlink(precious, os.path.join(inc, "planted"))
    r = rs("rmtree", base, "rwatch", "inc-100")
    check("rmtree: the folder and its files go; a link inside is removed itself", r == 0 and not os.path.exists(inc) and intact())
    pdir = os.path.join(work, "pdir"); os.makedirs(pdir); open(os.path.join(pdir, "keep"), "w").write("k")
    os.symlink(pdir, os.path.join(base, "rwatch", "inc-200"))
    r = rs("rmtree", base, "rwatch", "inc-200")
    check("rmtree: a dump name that is a link to a folder is removed itself - the folder it points to is untouched",
          not os.path.lexists(os.path.join(base, "rwatch", "inc-200")) and os.path.exists(os.path.join(pdir, "keep")))
    # the JFFS base
    check("the JFFS base works the same way", rs("append", jffs, "dreadwatch", "blocked.log", "0", data="j\n") == 0
          and open(os.path.join(jffs, "dreadwatch", "blocked.log")).read() == "j\n")
finally:
    shutil.rmtree(work, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
