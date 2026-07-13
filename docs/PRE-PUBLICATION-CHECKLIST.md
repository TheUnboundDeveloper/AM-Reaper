# Pre-Publication Checklist

Gate for making this repository (or any Reaper artifact) public. Derived from
[`COMPLIANCE-AUDIT-2026-07-13.md`](COMPLIANCE-AUDIT-2026-07-13.md). Items marked
**HELD** require your approval because they rewrite git history or edit
patch/code files — this remediation round did **not** perform them.

## Done in this repo (docs/licenses only — no code touched)
- [x] GPL source availability + §3(b) written offer — `SOURCE-AVAILABILITY.md`
- [x] Third-party notices + OFL license text — `../THIRD-PARTY-NOTICES.md`, `../LICENSES/OFL-1.1.txt`
- [x] Pinned build inputs + license status — `../DEPENDENCIES.md`
- [x] GPL §6 wording fix in `../README.md`
- [x] Coordinated-disclosure warning on `REAPER-FIXES.md`
- [x] Identity display canonicalized — `../.mailmap`
- [x] Stale patch counts corrected — `../patches/README.md`
- [x] Audit record + tracker — `COMPLIANCE-AUDIT-2026-07-13.md`

## HELD — needs your approval before public flip

### 1. Scrub personal data from git history (H1 + H2) — DONE 2026-07-13
The maintainer's personal Gmail (and an early author handle) lived in
pre-normalization patch-blob content in early history, and a maintainer
home-directory path was in the commit body of `patches/0038`. Both were
recoverable and were already on GitHub's servers while private.

**Executed:** a backup mirror was taken, then `git-filter-repo` rewrote all
history with a `--replace-text` map (personal address → project address; the old
home path → a neutral build-user path) plus a `--mailmap` canonicalizing every
author/committer to `reaper <theunbounddeveloper@outlook.com>`. The rewrite was
verified (history pickaxe + full-history grep both empty) and force-pushed. Every
commit hash changed as a result.

> After the force-push, GitHub may still cache old object views until it GCs
> them; if a cached blob is ever reachable, contact GitHub Support to purge it.
> Any pre-existing clones/forks still hold the old objects — there are none known
> for this private repo.

### 2. Add per-file license headers to new Reaper source (M2) — PATCH EDIT
New Reaper files carry no copyright/license header. Proposed header (SPDX form),
for your approval to apply to `rtrafd.c`, `rmcpd.c`, `reaper_inject.c/.h`, the new
`Makefile`s, `reaper_nav.js`, and the `Reaper_*`/`R_*` pages:

```
/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 the Reaper project maintainer
 * Part of the Reaper hardened Asuswrt-Merlin build. See LICENSE / LICENSE.reaper. */
```
Because these files live in the patch series, applying headers means editing the
patches (or adding a new patch) and regenerating — held for your approval.

### 3. OFL.txt in the built image (M1) — PATCH EDIT
Add a patch that installs `LICENSES/OFL-1.1.txt` → `www/fonts/OFL.txt` so the
font license travels in the flashed image, not just the source repo.

### 4. Owner / attorney actions
- [ ] **B2 (ATTORNEY):** clear whether images bundling proprietary blobs may be
      publicly redistributed at all, before re-hosting any `.pkgtb`.
- [ ] **H3 (OWNER):** consider renaming public artifacts project-first
      (`reaper-rt-be96u`), vendor/model in the tagline.
- [ ] **M3 (ATTORNEY/OWNER):** trademark review of `ASUSLogo.png`.
- [ ] **M6 (OWNER):** decide disclosure granularity of `REAPER-FIXES.md` vs.
      unpatched sibling models.
- [ ] If images are ever re-hosted: ship LICENSE + source/offer + THIRD-PARTY-NOTICES
      alongside them (`SOURCE-AVAILABILITY.md` § 3).
