#!/usr/bin/env python3
"""Refuse a commit whose SHAPE says a warm build tree was swept into it.

The v3.1.2 cut hit this: `95a1ee8ac3` was meant to be a thirty-file DNS change
and added 10,110 build-output files across some fifty vendored packages -
objects, `.deps` and `.libs`, autom4te caches, and the CONFIGURED `Makefile`,
`libtool` and `config.h`.  Three separate gates then fired downstream: the
OpenSSL overlay tarball went past GitHub's 100 MB hard limit, the exported
patch would have been 217 MB, and the hidden-character scan refused the control
bytes autotools embeds by construction.  Every one of those caught a SYMPTOM.
Nothing looked at the commit itself.

Shipping it would have been worse than noise: a configured `Makefile` and
`libtool` carry the build host's absolute paths, and dropping those into the CI
clean room is the stale-configure trap that has cost this project a fleet
before.

WHY A PATTERN ALONE CANNOT WORK.  The vendored tree legitimately TRACKS build
artefacts from the pinned upstream base - measured against a7ebfa133a: 5,930
`*.o`, 16,747 `Makefile`, 802 `*.so`.  So "added a .o" is not the signal.

AND WHY "ADDED A .o NOT IN THE BASE" IS NOT THE SIGNAL EITHER.  Onboarding a
model legitimately commits the closed layer straight out of an ASUS GPL drop -
`rc/prebuild/<MODEL>/`, `shared/prebuild/<MODEL>/`, `router-sysdep.<model>/`,
`bootloaders/obj.<model>/`.  The GT-BE19000 import added 109 such objects, none
of which exist in the base and every one of which belongs there.

The real discriminator, measured on both commits:

                              build-system droppings   objects under prebuilt paths
  warm-tree sweep 95a1ee8ac3            2,035                     -
  GT-BE19000 GPL import                     0            105 of 109

A source tree never authors `.deps/`, `.libs/`, `autom4te.cache/`,
`config.status` or `libtool`.  A build does.  So:

  1. HARD, no override - a build-system dropping absent from the pinned base.
  2. HARD, overridable  - an object/library absent from the base and NOT under
                          a recognised prebuilt path (--allow-binaries says it
                          is deliberate).  Objects under a prebuilt path are
                          counted and reported, never refused.
  3. SOFT               - a file count far outside a rung's norm.  Legitimately
                          large commits exist (a vendor import, a mass rename),
                          so --allow-large is the acknowledgement.

Usage:
    check_commit_shape.py [--repo DIR] [--rev REV] [--base REF]
                          [--max-files N] [--allow-large] [--allow-binaries]

Exit 0 = the shape is fine.  Exit 1 = refused.  Exit 2 = could not run.
"""
import argparse
import os
import subprocess
import sys

DEFAULT_REPO = "/home/reaper/asuswrt-be96u"
DEFAULT_BASE = "a7ebfa133a"
DEFAULT_MAX = 200

# Things a BUILD writes and a source tree never authors.  These are fatal on
# sight when absent from the pinned base: there is no legitimate reason for a
# commit to introduce one.
BUILD_SYSTEM_DIRS = ("/.deps/", "/.libs/", "/autom4te.cache/")
BUILD_SYSTEM_NAMES = ("config.status", "config.log", "config.cache",
                      "libtool", "stamp-h1", ".dirstamp")

# Compiled output.  Legitimate when it is a vendor/GPL prebuilt drop, which in
# this tree always lands under one of the markers below.
OBJECT_SUFFIXES = (".o", ".lo", ".a", ".la", ".Plo", ".Po", ".gcno", ".gcda")
PREBUILT_MARKERS = ("/prebuild/", "/prebuilt/", "/router-sysdep",
                    "/bootloaders/obj.")


def run(repo, args):
    proc = subprocess.run(["git", "-C", repo] + args,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        sys.stderr.write("git %s failed: %s\n"
                         % (" ".join(args),
                            proc.stderr.decode("utf-8", "replace")[:300]))
        sys.exit(2)
    return proc.stdout.decode("utf-8", "surrogateescape")


def classify(path):
    """'build-system', 'object', or None."""
    base = path.rsplit("/", 1)[-1]
    if base in BUILD_SYSTEM_NAMES:
        return "build-system"
    for marker in BUILD_SYSTEM_DIRS:
        if marker in "/" + path:
            return "build-system"
    for suf in OBJECT_SUFFIXES:
        if path.endswith(suf):
            return "object"
    if base.endswith(".so") or ".so." in base:
        return "object"
    return None


def is_prebuilt(path):
    return any(m in "/" + path for m in PREBUILT_MARKERS)


def top_dirs(paths, n=5):
    counts = {}
    for p in paths:
        d = p.rsplit("/", 1)[0]
        counts[d] = counts.get(d, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--max-files", type=int, default=DEFAULT_MAX)
    ap.add_argument("--allow-large", action="store_true",
                    help="acknowledge a deliberately large commit")
    ap.add_argument("--allow-binaries", action="store_true",
                    help="acknowledge compiled objects outside a prebuilt path")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(args.repo, ".git")):
        sys.stderr.write("not a git repo: %s\n" % args.repo)
        return 2

    changed = []
    for line in run(args.repo, ["show", "--name-status", "--format=",
                                "-M", args.rev]).split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        changed.append((parts[0][0], parts[-1]))

    if not changed:
        if not args.quiet:
            print("commit-shape: %s touches no files - nothing to check"
                  % args.rev[:10])
        return 0

    added = [p for st, p in changed if st == "A"]
    kinds = {p: classify(p) for p in added}
    candidates = [p for p in added if kinds[p]]

    novel_bs, novel_prebuilt, novel_stray = [], [], []
    if candidates:
        base_paths = set(run(args.repo, ["ls-tree", "-r", "--name-only",
                                         args.base]).split("\n"))
        for p in candidates:
            if p in base_paths:
                continue
            if kinds[p] == "build-system":
                novel_bs.append(p)
            elif is_prebuilt(p):
                novel_prebuilt.append(p)
            else:
                novel_stray.append(p)

    problems = []

    if novel_bs:
        problems.append(
            "%d added path(s) are BUILD-SYSTEM output absent from the pinned "
            "base (%s) - a source tree never authors these, so this is a warm "
            "build tree being committed.\n"
            "    worst directories:\n%s\n"
            "    examples: %s"
            % (len(novel_bs), args.base,
               "\n".join("      %6d  %s" % (n, d)
                         for d, n in top_dirs(novel_bs)),
               ", ".join(novel_bs[:3])))

    if novel_stray and not args.allow_binaries:
        problems.append(
            "%d compiled object(s)/librar(ies) added outside any recognised "
            "prebuilt path and absent from the pinned base.\n"
            "    worst directories:\n%s\n"
            "    examples: %s\n"
            "    If this is a deliberate vendor/GPL drop, re-run with "
            "--allow-binaries."
            % (len(novel_stray),
               "\n".join("      %6d  %s" % (n, d)
                         for d, n in top_dirs(novel_stray)),
               ", ".join(novel_stray[:3])))

    if len(changed) > args.max_files and not args.allow_large:
        problems.append(
            "%d files in one commit (limit %d). Every commit in the v3.1.2 rung "
            "touched 1-30. If this is a deliberate vendor import or a bulk "
            "rename, re-run with --allow-large to say so."
            % (len(changed), args.max_files))

    if not args.quiet:
        print("commit-shape: %s  %d file(s), %d added | novel: %d build-system, "
              "%d prebuilt-path object(s), %d stray object(s)"
              % (args.rev[:10], len(changed), len(added), len(novel_bs),
                 len(novel_prebuilt), len(novel_stray)))
        if novel_prebuilt:
            print("  note: %d object(s) under a recognised prebuilt path "
                  "(closed-layer import) - allowed" % len(novel_prebuilt))
    for why in problems:
        print("REFUSED: %s" % why)
    if problems:
        return 1
    if not args.quiet:
        print("commit-shape: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
