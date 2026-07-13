# Release Compliance Audit — 2026-07-13

Adversarial, read-only pre-publication audit of the Reaper project (licensing,
copyright, redistribution, GPLv2, trademark, secrets, U.S. legal risk). This
document is the audit record **and** the live remediation tracker. It is not
legal advice; items marked for attorney review require a qualified lawyer.

**Overall verdict at audit time:** DO NOT RELEASE (public) until the blockers
below are cleared. **Compliance confidence at audit time: 34/100.**

## Status legend
`FIXED` remediated in this repo · `DOC` documented/mitigated, residual risk noted
· `NEEDS-APPROVAL` requires editing patch/code files or a destructive git action,
held for maintainer approval · `ATTORNEY` legal question, not an engineering fix
· `OWNER-ACTION` a GitHub/account action only the owner can take.

---

## Critical blockers

| ID | Finding | Status |
|---|---|---|
| **B1** | The public image-hosting repo distributed GPL binaries with no LICENSE and no corresponding source / conforming §3(b) offer. | **Partly FIXED.** The offending repo was taken **offline** by the owner. The source-availability mechanism is now documented + a §3(b) written offer added: [`SOURCE-AVAILABILITY.md`](SOURCE-AVAILABILITY.md). **Do not re-publish images** without shipping LICENSE + source/offer + notices alongside (checklist in that doc § 3). |
| **B2** | Compiled images bundle proprietary Broadcom/ASUS/Trend Micro/Tuxera components that carry **no redistribution grant** (`README.proprietary` restricts them to genuine ASUS hardware). | **ATTORNEY.** Documented honestly in [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md) § 3. Whether images may be publicly redistributed at all is unresolved and must be reviewed by counsel before any image is re-hosted. |

## High risk

| ID | Finding | Status |
|---|---|---|
| **H1** | The maintainer's personal Gmail (and an early author handle) was recoverable in **git history** (initial commit + the author-normalize commit) as pre-normalization patch-blob content. | **FIXED (2026-07-13).** History rewritten with `git-filter-repo` (replace-text + mailmap), verified clean, force-pushed. See [`PRE-PUBLICATION-CHECKLIST.md`](PRE-PUBLICATION-CHECKLIST.md). |
| **H2** | A maintainer home-directory path (real-name-adjacent) appeared in the commit-message body of `patches/0038`. | **FIXED (2026-07-13).** Same history rewrite neutralized the path across all history and the working tree. |
| **H3** | Public repo name led with the ASUS/ASUSWRT trademark (origin/endorsement risk). | **OWNER-ACTION.** In-text disclaimers are good. Recommend project-first naming (e.g. `reaper-rt-be96u`) with the vendor/model relegated to a descriptive tagline. This lean repo is also named `ASUS-Merlin-Reaper` — consider the same rename. |

## Medium risk

| ID | Finding | Status |
|---|---|---|
| **M1** | Inter + Rajdhani fonts shipped without the required SIL OFL 1.1 notice. | **FIXED (source)** via [`../LICENSES/OFL-1.1.txt`](../LICENSES/OFL-1.1.txt) + [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md). **NEEDS-APPROVAL** to also ship `OFL.txt` into `www/fonts/` in the built image (patch edit). |
| **M2** | New Reaper source files (`rtrafd.c`, `rmcpd.c`, `reaper_inject.c/.h`, new `Makefile`s, `reaper_nav.js`, `Reaper_*`/`R_*` pages) lack per-file copyright/license headers. | **NEEDS-APPROVAL.** Adding SPDX/copyright headers edits the patch/source files; a header block is drafted and awaiting approval. |
| **M3** | `ASUSLogo.png` (ASUS trademark asset) added by patch `0144`. | **DOC / ATTORNEY.** Flagged in THIRD-PARTY-NOTICES § 1; trademark-use review recommended. Removal/replacement would be a patch edit (NEEDS-APPROVAL). |
| **M4** | README clause "Redistribution or rehosting of compiled firmware images is not authorized" over-restricted the GPL portion (GPL v2 §6). | **FIXED.** Reworded in [`../README.md`](../README.md) to scope the restriction to the *proprietary* components while preserving GPL redistribution freedoms. |
| **M5** | Toolchain + Focal rootfs + `LnxDictPrep` unpinned; redistribution status unaddressed. | **FIXED (documented)** in [`../DEPENDENCIES.md`](../DEPENDENCIES.md), with the unverified items explicitly flagged. |
| **M6** | `REAPER-FIXES.md` names file+function+input-vector for stock-ASUS vulns shared with unpatched sibling models (coordinated-disclosure exposure if published). | **DOC.** A coordinated-disclosure warning was added to the top of [`REAPER-FIXES.md`](REAPER-FIXES.md). Whether to reduce granularity before public release is a maintainer judgment call. |

## Low risk

| ID | Finding | Status |
|---|---|---|
| L1 | Second git author handle `nvaitehiarna`. | **FIXED (display)** via [`../.mailmap`](../.mailmap). Underlying commit objects unchanged unless history is rewritten (H1). |
| L2 | Ignored `CLAUDE.md` present on disk. | **VERIFIED** gitignored (`.gitignore` lines 11–14); confirm it is never force-added. |
| L3 | Stale `patches/README.md` counts (said 139/v1.4.2). | **FIXED** — corrected to 150/v1.5.0a. |

## Good (no action)
Clean, single-identity patch series (150 gapless, `reaper <theunbounddeveloper@outlook.com>`);
no secrets/keys added; no third-party code imported; upstream notices removed only
via whole-file feature deletions; well-scoped `LICENSE.reaper`; strong disclaimers;
AI-assisted authorship disclosed via `Co-Authored-By` trailers.

## AI provenance
All new Reaper code is AI-assisted under maintainer direction (disclosed). It is
**not** copied/leaked-repo code, **not** reverse-engineered (the project avoids
RE/decompilation of the blobs), and **not** proprietary-SDK-derived. U.S.
copyright registrability of AI-assisted portions is an attorney question that
affects ownership claims, not the GPL redistribution obligation.

---

## What this remediation round changed (files added/edited in this repo)
- **Added:** `docs/SOURCE-AVAILABILITY.md`, `DEPENDENCIES.md`, `THIRD-PARTY-NOTICES.md`,
  `LICENSES/OFL-1.1.txt`, `.mailmap`, `docs/PRE-PUBLICATION-CHECKLIST.md`, this file.
- **Edited (docs only, no code):** `README.md` (M4 wording), `patches/README.md`
  (L3 counts), `docs/REAPER-FIXES.md` (M6 warning header).
- **Not touched:** any `patches/*.patch` file or source code (per maintainer
  instruction — those changes are listed as NEEDS-APPROVAL above).
