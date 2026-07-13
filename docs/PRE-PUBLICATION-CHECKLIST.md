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

### 2. Per-file license headers on new Reaper source (M2) — DONE 2026-07-13
`SPDX-License-Identifier: GPL-2.0-only` + copyright headers were added to every
live Reaper source file (`rtrafd.c`, `rmcpd.c`, `reaper_inject.c/.h`, the two
`Makefile`s, the reaper CSS, and the `Reaper_*`/dashboard/shell pages) as patch
`0152` (v1.5.0c). A full firmware build passed with the headers in place. (The
`reaper_nav.js` / `R_*_Content.asp` from the original audit list no longer exist —
they were removed in the shell-architecture refactor.)

### 3. OFL.txt in the built image (M1) — DONE 2026-07-13
Patch `0152` installs the SIL OFL 1.1 text as `www/fonts/OFL.txt`; it is present
in the staged image (build-verified), so the font license now travels in the
flashed firmware, not just the source repo.

### 4. Owner / attorney actions
- [ ] **B2 (ATTORNEY):** clear whether images bundling proprietary blobs may be
      publicly redistributed at all, before re-hosting any `.pkgtb`. Removing
      logos does NOT address this — the closed Broadcom/ASUS/Trend Micro/Tuxera
      *binaries* are functionally required and cannot be removed. Safe default:
      publish source + patches only; do not re-host compiled images publicly.
- [ ] **H3 (OWNER):** consider renaming public artifacts project-first
      (`reaper-rt-be96u`), vendor/model in the tagline.
- [ ] **M3 (OWNER, planned):** remove `ASUSLogo.png` and revert the AiMesh-backdrop
      CSS in `reaper_content.css` §11 (or swap a Reaper asset) so no broken image
      reference remains. Keep written credit to ASUS/Merlin (legitimate nominative use).
- [ ] **M6 (OWNER):** decide disclosure granularity of `REAPER-FIXES.md` vs.
      unpatched sibling models.
- [ ] If images are ever re-hosted: ship LICENSE + source/offer + THIRD-PARTY-NOTICES
      alongside them (`SOURCE-AVAILABILITY.md` § 3).
