#!/usr/bin/env python3
"""Assert that overlays/<MODEL>.patch contains ONLY per-model identity.

Why this exists
---------------
`git apply` is not a correctness check. On 2026-08-10 the sibling overlays had
been generated from stale branch tips; they applied *cleanly* and silently
reverted 7 files per model to v2.1.4-era content -- including reintroducing the
first-boot login loop that had already been fixed. A clean apply proved nothing,
because a stale overlay is still a well-formed patch.

The invariant that WOULD have caught it: an overlay is a model's identity, not a
place where shared code differs. Concretely, for the seven files that reference
the banner, every changed line must be a banner-filename swap. Anything else in
those files means canon moved and the sibling branch did not -- i.e. the overlay
is about to revert shared work.

This needs only overlays/, so it runs in seconds with no base clone and no patch
replay. It complements, and does not replace, the `git apply` the build already
does with the real tree.

Usage:  check_overlays.py <overlays-dir> [MODEL ...]      (default: all four)
"""
import os
import re
import sys

# Canon's own banner. A sibling overlay always removes this pair and adds its own.
CANON_BANNER = "RT-96U"

# model -> the banner basename that model's overlay must install
MODEL_BANNER = {
    "RT-BE86U":    "RT-BE86U",
    "RT-BE88U":    "RT-BE88U",
    "GT-BE98":     "GT-BE98",
    "GT-BE98_PRO": "GT-BE98P",
}

# The files that embed the banner filename. port_sibling_v2.sh re-points exactly
# these after syncing them from canon, so in the overlay they must differ ONLY by
# that filename. This is the set the 2026-08-10 regression damaged.
BANNER_REF_FILES = {
    "release/src/router/www/Logout.asp",
    "release/src/router/www/Main_Login.asp",
    "release/src/router/www/Main_Password.asp",
    "release/src/router/www/Main_ReaperDash.asp",
    "release/src/router/www/Reaper_FirstBoot.asp",
    "release/src/router/www/reaper_shell.asp",
    "release/src/router/www/state.js",
}

# Text files that legitimately carry a model CAPABILITY difference rather than a
# banner reference. Keep this list short and explicit: every entry is a standing
# claim that the file genuinely differs per model.
IDENTITY_TEXT = {
    "release/src-rt/target.mak",                              # model block, BUILD_NAME, SAMBA4
    "release/src-rt/version.conf",                            # EXTENDNO
    "release/src/router/www/Tools_Sysinfo.asp",               # band/temp gating per model
    "release/src/router/www/Main_WStatus_Content.asp",        # GT-BE98_PRO band layout
    "release/src/router/rc/reaper_chanlist_shim.c",           # GT-BE98 only
    "release/src-rt-5.04behnd.4916/router-sysdep/.dummy",
}

# Non-source blobs and build byproducts committed on the sibling branches. Not
# ideal that they are in the tree at all, but they are model-specific and inert.
IDENTITY_BLOB_RE = [
    re.compile(r"^release/src/router/www/images/[A-Za-z0-9_-]*_REAPER_Header(_anim)?\.png$"),
    re.compile(r"^release/src-rt-5\.04behnd\.4916/bcmdrivers/.*\.(o|so[0-9.]*)$"),
    re.compile(r"^release/src-rt-5\.04behnd\.4916/bcmdrivers/.*/airiq/prebuilt/.*$"),
    re.compile(r"^release/src-rt-5\.04behnd\.4916/bootloaders/.*$"),
    re.compile(r"^release/src/router/rc/prebuild/.*\.o$"),
    # bdmf_*.h are SYMLINKS in canon and REGULAR FILES on the BCM6813 siblings.
    # git spells that type change as a delete+create pair sharing one path, so
    # the "changed lines" are a whole header file and can never be banner-only.
    re.compile(r"^release/src-rt-5\.04behnd\.4916/rdp/projects/.*/bdmf/framework/bdmf_\w+\.h$"),
]

BANNER_RE = re.compile(r"[A-Za-z0-9_-]*_REAPER_Header(_anim)?\.png")


def is_identity_blob(path):
    return any(rx.match(path) for rx in IDENTITY_BLOB_RE)


def parse(patch_path):
    """-> {path: {"binary": bool, "changed": [lines]}}"""
    files, cur = {}, None
    hdr = re.compile(r"^diff --git a/(.*) b/(.*)$")
    for line in open(patch_path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        m = hdr.match(line)
        if m:
            a, b = m.group(1), m.group(2)
            # A path may appear twice (the symlink->file type change above);
            # merge rather than overwrite so nothing is silently dropped.
            cur = files.setdefault(a if a == b else b, {"binary": False, "changed": []})
            continue
        if cur is None:
            continue
        if line.startswith("GIT binary patch"):
            cur["binary"] = True
        elif line.startswith(("+++", "---")):
            continue
        elif line[:1] in ("+", "-") and not cur["binary"]:
            cur["changed"].append(line)
    return files


def check(model, patch_path):
    problems = []
    files = parse(patch_path)
    if not files:
        return ["overlay parsed to zero files - wrong format or empty"]

    mine = MODEL_BANNER[model]
    for path, info in sorted(files.items()):
        # (1) dictionaries must never ride in an overlay: CI siblings take their
        # translations from the patch series, which is what keeps all 25 packs in
        # lockstep across the fleet. An overlay dict would pin a sibling to a
        # stale language set that no lockstep check would notice.
        if path.endswith(".dict"):
            problems.append("%s: dictionaries must never appear in an overlay" % path)
            continue

        if is_identity_blob(path):
            continue
        if path in IDENTITY_TEXT:
            continue

        if path in BANNER_REF_FILES:
            # (2) THE CORE GATE: banner-filename swaps only.
            offending = [l for l in info["changed"] if not BANNER_RE.search(l)]
            if offending:
                problems.append(
                    "%s: %d changed line(s) are NOT banner references - the overlay is "
                    "reverting shared code (port the rung to the sibling branch first, "
                    "then regenerate). First: %s"
                    % (path, len(offending), offending[0][:120])
                )
            # (3) and the swap must install THIS model's banner, not another's.
            #     This is the v1.8.6 clobber class: a wholesale copy from canon
            #     left every sibling showing "RT-BE96U" in its own header.
            added = {n for l in info["changed"] if l.startswith("+")
                     for n in re.findall(r"([A-Za-z0-9_-]*)_REAPER_Header", l)}
            if added and added != {mine}:
                problems.append(
                    "%s: installs banner(s) %s but %s must install %s (foreign-banner clobber)"
                    % (path, sorted(added), model, mine)
                )
            continue

        # (4) anything else is a shared file that has no business being here.
        problems.append(
            "%s: unexpected file in the overlay. Either it is genuine model identity - "
            "add it to IDENTITY_TEXT/IDENTITY_BLOB_RE with a reason - or canon and the "
            "sibling branch have drifted and the rung needs porting." % path
        )

    # (5) the canon banner pair must be removed, or the image ships two banners
    # and reaper_verify's identity check fails late instead of here.
    imgs = [p for p in files if "_REAPER_Header" in p]
    if not any(CANON_BANNER in p for p in imgs):
        problems.append("overlay never removes canon's %s banner pair" % CANON_BANNER)
    if not any(mine in p for p in imgs):
        problems.append("overlay never installs %s's own banner pair" % mine)
    return problems


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "overlays"
    models = sys.argv[2:] or sorted(MODEL_BANNER)
    rc = 0
    for model in models:
        p = os.path.join(d, "%s.patch" % model)
        if not os.path.exists(p):
            print("::error::missing overlay %s" % p)
            rc = 1
            continue
        problems = check(model, p)
        if problems:
            rc = 1
            print("  %s: %d problem(s)" % (model, len(problems)))
            for msg in problems:
                print("::error title=%s overlay::%s" % (model, msg))
        else:
            n = len(parse(p))
            print("  %s: OK - %d file(s), identity only" % (model, n))
    print("\noverlay shape gate: %s" % ("FAIL" if rc else "pass"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
