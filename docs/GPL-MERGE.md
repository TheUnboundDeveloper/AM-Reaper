# Merging a new ASUS/Merlin GPL drop into the Reaper fork

A step-by-step developer guide for bringing a new upstream Asuswrt-Merlin (or raw
ASUS GPL) source drop into the RT-BEXXU "reaper" fork with the least pain.

It assumes the **mergeability refactor** (2026-07-05) is in place: the Reaper theme
is applied at serve time from one httpd hook, so the stock pages are pristine and
fast-forward cleanly. If you are reading this on a fork that still has the theme
inlined into 165 pages, do that refactor first (see "Appendix B").

- **Branch:** `BEXXU-only` (local only, **never pushed** upstream)
- **Build clone (authoritative):** `/home/reaper/asuswrt-BEXXU` on WSL `Ubuntu-20.04`, user `reaper`
- **Upstream base of the current stack:** `a7ebfa133a` (the last real Asuswrt-Merlin commit; everything after it is reaper work)
- **Models:** RT-BEXXU (primary) + RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro, plus the newer RT-BE92U (BCM6765 / 96765GW, experimental) (`release/src-rt-5.04behnd.4916`; targets `make rt-BEXXU` / `rt-be86u` / `rt-be88u` / `gt-be98` / `gt-be98_pro` / `rt-be92u`)

---

## 1. Mental model: what the fork actually changes

A merge is only as hard as your footprint on files upstream also edits. After the
refactor the reaper footprint is four layers, listed from cheapest to most costly
to merge:

| # | Layer | Files | Conflicts when... |
|---|---|---|---|
| 1 | **Theme injection** | `httpd/reaper_inject.c` + `.h` (new), one call in `httpd/httpd.c`, one `OBJS` line in `httpd/Makefile` | Almost never. New files never conflict; the hook is a 1-line change at the stable `do_ej` output site |
| 2 | **Theme styling** | `www/reaper/*` (additive), `www/reaper_shell.asp`, `www/Main_ReaperDash.asp` | Never (reaper-owned files upstream doesn't ship) |
| 3 | **SPA-bundle recolor** (deferred) | `www/sysdep/FUNCTION/RWD_UI/rwd_component.css`, `.../SDN/SDN/sdn.css`, `.../SDN/SDN/mlo.css` | Only if upstream edits those 3 files (recolor-only, easy to redo) |
| 4 | **C hardening** | ~46 `.c`/`.h` under `httpd/ rc/ shared/ libovpn/ libcodb/ ...` | The **real merge work** - genuine logic edits (see section 7 + Appendix A) |
| 5 | **Package CVE backports** | bundled third-party pkgs, e.g. avahi (`avahi-core/rr.c`, `avahi-common/{domain,alternative}.c`) | Almost never - these packages are ASUS-frozen; conflicts only if a drop re-imports the package tarball, then re-check each backport vs the new version (same double-fix audit as section 7). See `REAPER-FIXES.md` -> "Package CVE backports" |

Plus one special commit:

- **Model strip** (`48b0698465`) - a mechanical 5,650-file / ~1M-line deletion of
  the non-BEXXU sibling models. It is currently the **first** commit on top of the
  base. Treat it as **regenerable**, not something to hand-merge (section 6).

The whole point of the refactor: layers 1-2 are conflict-free, so a merge is
"rebase the ~75-commit stack and resolve the ~46 C files + maybe 3 CSS files."

---

## 2. How the theme injection works (so you can re-apply the 1 hook)

`httpd/httpd.c` serves every `text/html` document through `do_ej()`. The refactor
swaps the single output call (currently near `httpd.c:1826`):

```c
// was: handler->output(file, conn_fp);
reaper_output(handler, file, conn_fp);   // + #include "reaper_inject.h" near the top
```

`reaper_output()` (in `reaper_inject.c`) wraps the connection stream with a
`fopencookie()` streaming filter that inserts, exactly once, before the first
`</head>`:

```html
<link rel="stylesheet" type="text/css" href="/reaper/reaper_content.css">
<script>if(self===top){var rp=location.pathname.split("/").pop()||"index.asp";location.replace(rp==="index.asp"?"/Main_ReaperDash.asp":"/reaper_shell.asp#"+rp+location.search);}</script>
```

Properties you rely on when re-applying the hook after a merge:

- **Fail-open** - if `fopencookie` returns NULL the original output path runs unchanged.
- **`text/html` only** - `state.js`, JSON, XML, CSS, appcache are never touched (gated on `handler->mime_type`).
- **Basename skip-list** - the reaper-owned + login/captive pages are excluded (`Main_ReaperDash.asp`, `reaper_shell.asp`, `Main_Login.asp`, `Nologin.asp`, `Captive_Portal.asp`, `Captive_Portal_Advanced.asp`).
- **Fragment-boundary-safe `</head>` matcher** - byte-wise state machine, persistent hold across writes; a document with no `</head>` passes through byte-identical.
- **Runtime kill-switch** - `nvram get reaper_inject` (default on). `nvram set reaper_inject=0; restart_httpd` serves the pristine stock UI with no reflash.

Because the hook sits at `do_ej`, it reaches every iframe depth including the deep
SDN/MLO SPA docs (`SDN/sdn.html`, `mlo.html`, both `**.htm*`). The `Makefile`
change is a single line (near line 150): `OBJS += reaper_inject.o`.

---

## 3. Prerequisites and environment

- Work in **WSL `Ubuntu-20.04`** as user **`reaper`** (uid 1001). The default WSL
  user is root, which the build's `prebuild_checks` rejects.
- Two clones exist (see the repo-topology memory):
  - **Windows mirror** `.../asuswrt-merlin.ng` - `origin` points at upstream RMerl; this is where a new drop is fetched.
  - **WSL build clone** `/home/reaper/asuswrt-BEXXU` - its `origin` is the local Windows mirror (`file:///mnt/c/.../asuswrt-merlin.ng/.git`). This is where you rebase and build.
- **Never push** either full tree (`origin` is upstream). Only the separate lean
  repo (`TheUnboundDeveloper/AM-Reaper`) is pushable.
- Run multi-step git/build commands from a **scratchpad `.sh` file** invoked as
  `wsl -d Ubuntu-20.04 -u reaper bash /mnt/c/.../script.sh` - inline
  `VAR=...; cmd $VAR` in `wsl bash -c` arrives with the variable **empty**.
- Take a safety tag before you start: `git tag premerge-$(cat /some/date)` (or any
  fixed label) so `git reset --hard <tag>` restores the known-good stack.

---

## 4. Step 0 - inventory your current footprint

Before merging, snapshot exactly what you carry so you can verify nothing is lost:

```sh
cd /home/reaper/asuswrt-BEXXU
BASE=a7ebfa133a
# the reaper stack (should be ~75 commits, oldest first)
git log --oneline --reverse ${BASE}..HEAD
# the C/H hardening surface (the real merge work - ~46 files)
git diff --name-only ${BASE}..HEAD -- release/src/router | grep -E '\.(c|h)$' | sort -u
# confirm the stock theme surface is pristine (should print nothing but reaper-owned)
grep -rl 'reaper_content.css\|reaper_shell.asp' release/src/router/www \
  | grep -vE 'reaper/|reaper_shell.asp|Main_ReaperDash.asp'
```

---

## 5. Step 1 - import the new upstream drop

The drop enters through the Windows mirror, then the WSL clone fetches it:

```sh
# In the Windows mirror (origin = upstream RMerl):
#   git -C /mnt/c/Users/.../asuswrt-merlin.ng fetch origin
#   git -C .../asuswrt-merlin.ng branch import/<ver> <new-upstream-tag-or-sha>
# Then in the WSL build clone:
cd /home/reaper/asuswrt-BEXXU
git fetch origin
git branch import/<ver> origin/import/<ver>     # a pristine, reaper-free base
```

`import/<ver>` must have **no reaper commits** on it - it is the new pristine base
you rebase onto. Sanity-check that `a7ebfa133a` is an ancestor of it (same
lineage); if ASUS re-based their history, find the new equivalent base commit and
use that as `BASE` everywhere below.

---

## 6. Step 2 - rebase the reaper stack (and drop the model strip in one command)

The model strip (`48b0698465`) is the **first** reaper commit - a mechanical
5,650-file deletion of the non-BEXXU sibling models
(`router-sysdep.{gt-be98_pro,rt-be58_go,rt-be86u,rt-be88u,rt-be92u}` + sibling
dongle firmware and bootloader configs). It is **fully independent** of the reaper
work (it touches zero `release/src/router` shared source; nothing later depends on
it) and it is **not required to build** rt-BEXXU - the sibling dirs are dead
weight, not build inputs. So never *replay* it: replaying a mass-deletion just
invites modify/delete conflicts against upstream churn, for no benefit.

Because it is the first commit, you drop it **and** rebase all the real work onto
the pristine base in a single command - start the rebase from the strip's own sha
instead of the base:

```sh
git checkout BEXXU-only
git rebase --onto import/<ver> 48b0698465 BEXXU-only
```

This replays only the hardening + UI + refactor commits (which touch
`release/src/router` shared source present in both trees) onto full pristine
upstream, and simply omits the strip. Expect conflicts **only** in the layer 3-4
files (section 7); layers 1-2 and the 165 stock pages / 4 reverted CSS carry zero
reaper edits and never conflict.

### Re-strip (optional cleanup)

Re-stripping is **optional** - the build works with the sibling dirs present. If
you want the lean tree back, re-apply the deletion as a fresh **tip** commit
(keeping it trivially droppable next time):

```sh
# authoritative list of what the original strip removed:
git show 48b0698465 --diff-filter=D --name-only | grep '^release/' > /tmp/strip.txt
xargs -a /tmp/strip.txt rm -f 2>/dev/null
git add -A && git commit -m "strip non-BEXXU sibling models (regenerated)"
```

If a new drop adds sibling-model files under new paths, extend the deletion to the
new `router-sysdep.<model>` dirs plus the sibling entries under
`bcmdrivers/.../dongle/sysdeps/<MODEL>` and `bootloaders/build/configs`.

---

## 7. Step 3 - resolve the C hardening conflicts

This is the actual work. The ~46 `.c`/`.h` files (full list in Appendix A) carry
security logic that upstream also edits. For each conflict:

1. **Keep the reaper fix's intent**, re-expressed against the new upstream code.
   The fixes are bounds checks, `strlcpy`/`snprintf` conversions, format-string
   `"%s"` guards, command-injection argv conversions, and charset guards.
   `REAPER-FIXES.md` is the index: every fix has an ID (C1..C8, H*, M*, L*, N*,
   R4-*) and a one-line description of what it does and why.
2. **Cross-check against `REAPER-FIXES.md`** - if upstream already fixed the same
   issue (Merlin back-ports silently), drop the reaper hunk and note it.
3. **Watch the config-gated files.** `rc/multi_wan.c`, `multi_wan_ipv6.c` and the
   TR069 opt-125 path are **not compiled** on BEXXU (fixed defensively). Conflicts
   there are low-stakes but still resolve them to keep the source consistent.
4. **Never introduce non-ASCII** into any `www` file - the packaging minifier
   strips non-ASCII bytes. (C files are fine.)

Resolve, `git add`, `git rebase --continue`. Do the C files in small batches and
build between batches if a conflict looked risky.

### Post-rebase: audit for silent double-fixes

A rebase conflict only fires when reaper's fix and an upstream fix touch the
**same lines**. When upstream fixed the same vulnerability in a *different* spot,
git applies both cleanly and says nothing - leaving a silent **double-fix**:
redundant at best; a compounded off-by-one, a double-validation that rejects valid
input, or a now-dead branch at worst. git cannot detect this - you must, with
`REAPER-FIXES.md` as the checklist. Run this **after the whole rebase completes,
before building**:

```sh
NEW=import/<ver>
# Net reaper delta vs the NEW upstream, C/H only. Every hunk here should be a fix
# upstream does NOT already have; a hunk that duplicates protection already present
# in $NEW is a double-fix.
git diff $NEW..HEAD -- '*.c' '*.h'
# Which reaper commits still land on each co-edited file:
for f in $(git diff --name-only $NEW..HEAD -- '*.c' '*.h'); do
  echo "== $f =="; git log --oneline $NEW..HEAD -- "$f"
done
```

Then walk every `REAPER-FIXES.md` ID and open its target function in the merged
tree; confirm the vulnerability is closed **exactly once**:

- upstream now closes it **and** reaper adds a second guard -> **drop reaper's
  hunk** (edit it out / amend the commit) and note it in `REAPER-FIXES.md`;
- only reaper closes it -> keep it;
- both close it partially -> reconcile into **one** guard, never stack two.

Tell-tale double-fixes to look for: two adjacent length clamps on the same buffer,
the same nvram value sanitized twice, a reaper `strlcpy` sitting next to an
upstream `strlcpy`/`snprintf` of the same field, or a validation branch that is now
unreachable. `git blame` the region to separate the two solutions - reaper hunks
carry the reaper author, upstream hunks carry the ASUS/Merlin author.

This audit plus the build + boot + security retest (section 9) is what turns "git
did not complain" into assurance that each vulnerability is fixed exactly once.

---

## 8. Step 4 - re-assert pristineness and re-apply the theme hook

After the rebase completes, prove the stock surface is still pristine and the one
hook survived:

```sh
cd /home/reaper/asuswrt-BEXXU
NEW=import/<ver>
# 1) no reaper markers in any stock page (only reaper-owned should match)
grep -rl 'reaper_content.css\|reaper_shell.asp' release/src/router/www \
  | grep -vE 'reaper/|reaper_shell.asp|Main_ReaperDash.asp'      # -> empty
# 2) the 4 de-inlined CSS files are byte-identical to the new upstream
for f in www/form_style.css www/index_style.css \
         www/device-map/clientlist.css www/device-map/device-map.css; do
  echo -n "$f: "; git diff $NEW -- release/src/router/$f | wc -l   # -> 0
done
# 3) the theme hook is present
grep -n 'reaper_output' release/src/router/httpd/httpd.c            # -> the do_ej call
grep -n 'reaper_inject.o' release/src/router/httpd/Makefile         # -> OBJS line
```

If upstream moved the `do_ej` output call, re-apply the 1-line `reaper_output(...)`
swap at its new location and re-add `#include "reaper_inject.h"`.

---

## 9. Step 5 - rebuild and validate

Follow the BUILD SOP (see the build-SOP memory / `docs/DEV-SETUP.md`). Summary:

```sh
# pre-flight (as needed): /bin/sh -> bash; chown any root-owned files back to
# reaper (UNC edits flip ownership); restore the WL router symlink; add the
# gcc-10.3 toolchain bins to PATH.
cd release/src-rt-5.04behnd.4916 && nice make rt-BEXXU -j1     # ~25-30 min full build
```

Success criteria (verify all): log has `Done! Image 96813GW has been built`,
`MAKE_EXIT=0`, `reaper_inject.o` links into httpd, and the fresh
`RT-BEXXU_3006_102.8_Reaper_v<version>_nand_squashfs.pkgtb` mtime is newer than the build
start. Then verify the staged rootfs (`targets/96813GW/fs/www` is **minified** -
grep, do not diff):

```sh
FS=targets/96813GW/fs/www
grep -rl 'reaper_content.css' $FS | grep -vE 'reaper/|reaper_shell|Main_ReaperDash' | wc -l  # 0
grep -c 'Phase-B migration' $FS/reaper/reaper_content.css                                     # 2
```

**On-device (flash the squashfs, not the loader):** theme present at every depth
incl. the SDN/MLO SPA and the device-map View List; top-level pages bounce into the
shell; login/logout/reboot behave; HW QoS + CAKE still activate; and the
**kill-switch** works: `nvram set reaper_inject=0; restart_httpd` -> clean stock UI,
`=1` -> theme returns. A local **mock router** (`/home/reaper/mock_router.py`,
serves the staged fs on :8188 and reimplements the injection) validates the
renderable pages off-device, but cannot render the auth-gated SPA - that needs the
router.

---

## 10. Step 6 - update the records

- `REAPER-FIXES.md` - if you dropped any hunk because upstream fixed it, mark that
  row. Add a note for the new base version.
- `GPL-MERGE.md` (this file) - update `BASE` and any moved hook line.
- Bump the version string if the base version changed (`release/src-rt/version.conf`
  via `EXTENDNO=reaper`; see the build-SOP memory).
- Sync the lean repo (`REAPER-FIXES.md`, `patches/` = `git format-patch` of the
  hardening commits, and this guide), then push **the lean repo only**.

**Patch-series regeneration recipe (the series is now at 541 patches, `0541` = v2.7.7,
appended + full-replay verified — `git am --keep-cr` of the series onto a fresh
`a7ebfa133a` worktree returned `AM_EXIT=0` and reproduced `release/src/router` with the
only differences being vendored `*.md` files the pathspec
deliberately excludes. **Cutting a rung is now one command — [`../build-scripts/cut_rung.sh`](../build-scripts/cut_rung.sh)** — which does the export, identity normalization, gapless check, full-series replay, provenance update, overlay-overlap check, CI pin and PII scan in order; the manual recipe below is what it automates, kept for when something needs doing by hand.
It was 535 at v2.7.6; 528 at v2.7.3; 424 at v2.4.1; 406 at v2.3.7; 379 at v2.3.3; 374 at v2.3.1, repaired + replay-verified 2026-08-09; 325 at v2.1.5 (322 under the pre-repair numbering);
it was 215 at v1.7.7, and the 190-patch v1.6.6 run on 2026-07-19 was validated
`git am --keep-cr` clean onto a fresh `a7ebfa133a` worktree with a matching
`release/src/router` tree hash — as were the 181-patch v1.6.0, 178-patch v1.5.9 and
150-patch v1.5.0a runs. NOTE: every patch since `0211` (`0212`–`0271`, v1.7.5–v2.0.0)
was **appended** per-version to the existing series, not produced by a full regeneration, to avoid
re-introducing an old absolute build-path reference that a full regen would pull back in
from an unscrubbed commit message. The `0262`–`0271` (v1.9.8–v2.0.0) append was cut from
`2f84abb9..<v2.0.0-tip>` (v1.9.7 tip → v2.0.0 tip) with `--start-number 262`, author already normalized,
and validated `git am --keep-cr` clean onto a fresh worktree at the v1.9.7 tip (zero
`release/src/router` diff vs the v2.0.0 tip). When you do run a full regeneration, expect gapless
renumbering to `0271` and re-apply the message scrub below. NOTE the v1.6.0 sync also
cherry-picked the `radio-count` dashboard + the v1.6.0 commit onto `BEXXU-only` — they
had been built on the `rt-be86u` branch; always confirm `git branch --show-current` is
`BEXXU-only` before an RT-BEXXU build/commit.) One extra step since the 2026-07-13
compliance scrub: after
regenerating from the (unscrubbed) build clone, re-apply the message-level scrub
`s|/home/nathan|/home/builder|g; s|ASUS-Merlin-Reaper|AM-Reaper|g` to the patch
files — commit messages in the clone still carry the pre-scrub strings (patch 0038
is the known instance) and must not re-enter the public series:**

```bash
BASE=a7ebfa133a                      # last real upstream commit
STRIP=$(git rev-parse 48b0698465)    # the optional model-strip commit (excluded)

# 1. format-patch with a pathspec that EXCLUDES docs/meta -> doc hunks are stripped
#    from mixed commits (e.g. a version bump that also edits REAPER-FIXES.md) and
#    pure-doc commits are skipped automatically.
git format-patch $BASE..HEAD -o /tmp/stage -N --no-cover-letter -- \
  . ':(exclude)*.md' ':(exclude)docs' ':(exclude).mailmap' \
  ':(exclude).gitattributes' ':(exclude).gitignore'

# 2. drop the model-strip commit's patch (first line "From <hash> …"), renumber
#    survivors 0001.. with no gaps, and normalize the author line:
#    sed 's/^From: .*/From: reaper <theunbounddeveloper@outlook.com>/'

# 3. VALIDATE (do not skip): apply onto a fresh BASE worktree with --keep-cr and
#    confirm zero source diff vs HEAD.
git worktree add --detach /tmp/wt $BASE
cd /tmp/wt && git am --keep-cr /tmp/final/*.patch
git --git-dir=<clone>/.git --work-tree=/tmp/wt diff --name-only HEAD -- release/src/router   # must be empty
```

`--keep-cr` is mandatory when applying (some third-party files — `lltdc` — are
CRLF; without it the CR is stripped and the series fails at `qospktio.c`).

---

## 11. The durable exit: upstream the hardening

Layer 4 (the ~46 C files) is the only recurring cost. Every fix accepted into
Asuswrt-Merlin leaves the fork permanently. Maintain the fixes as a patch queue
(`git format-patch a7ebfa133a..HEAD -- <hardening files>`) and submit them as a
PR series; `REAPER-FIXES.md` is written to double as the submission changelog. As
fixes land upstream, delete them from the stack - a merge then gets cheaper every
release.

> Author identity: the historical hardening commits carry an early personal email
> as their raw author. The repo `.mailmap` fixes *display* only, and
> `git format-patch` emits the raw author regardless. So after **regenerating**
> patches, normalize the `From:` lines to `reaper <theunbounddeveloper@outlook.com>`
> before committing them to the lean repo (the current `patches/` are already
> normalized) - otherwise the personal email re-appears in the public series.

---

## 12. Rollback

- **Runtime (no reflash):** `nvram set reaper_inject=0; restart_httpd` -> stock UI.
- **Build:** the pre-merge tag - `git reset --hard <premerge-tag>` restores the
  known-good stack; or `git checkout <tag> -- httpd/ www/` for just the theme layer.
- **A bad flash:** ASUS Firmware Restoration + rescue mode (the `_loader.pkgtb` is
  recovery-only; never the flash target).

---

## Appendix A - the C hardening surface (~46 files)

These are the files that carry inline security logic and are the merge work each
drop. Grouped by area; `REAPER-FIXES.md` maps each to its fix IDs and commits.

- **httpd:** `httpd.c` (also the theme hook), `web.c`, `reaper_inject.c/.h` (theme)
- **rc:** `rc_ipsec.c`, `snmpd.c`, `usb.c`, `usb_devices.c`, `udhcpc.c`, `ntp.c`,
  `firewall.c`, `firewall_sdn.c`, `init.c`, `common.c`, `services.c`, `qos.c`,
  `rc.h`, `sysdeps/init-broadcom.c`, `multi_wan.c`*, `multi_wan_ipv6.c`* (*config-gated off)
- **shared:** `misc.c`, `nvparse.c`, `shutils.c/.h`, `shared.h`, `common_utils.c`,
  `mtlan_utils.c`, `wlif_utils.c`, `wlif_utils_ax.c`, `defaults.c`
- **daemons/libs:** `libovpn/*` (openvpn_{config,control,options,setup}.c,
  amvpn_routing.c), `libcodb/{codb_utils,cosql_utils}.c`, `libdisk/write_smb_conf.c`,
  `infosvr/common.c`, `lanauth/lanauth.c`, `rstats/rstats.c`, `urlfilterd/filter.c`,
  `wsdd2/{wsd,llmnr}.c`, `snooper/igmp.c`, `lltdc/src/qospktio.c`

## Appendix B - the reaper commit stack (shape)

75 commits on top of `a7ebfa133a`, in three bands:

1. **Model strip** (`48b0698465`) - mechanical, regenerable (section 6).
2. **Hardening rounds 1-4** (~24 commits) - the C fixes catalogued in `REAPER-FIXES.md`.
3. **Reaper UI + Hardware QoS + the mergeability refactor** (~50 commits) - theme,
   dashboard/shell, QoS feature, then the de-inline refactor (theme->httpd,
   CSS->reaper_content.css, the 4 quick code fixes, and this guide).

If you are porting the fork to a build that still inlines the theme, apply the
refactor before your first merge: move the per-page `</head>` block into
`reaper_inject.c`, add the httpd hook, strip the 165 pages
(`grep -rl 'href="/reaper/reaper_content.css"' www`, delete the reaper `<link>` +
bounce `<script>`, restore any severed symlinks), and consolidate stock-CSS
recolors into `reaper_content.css`. That is what turns a 165-file merge into a
1-hook merge.
