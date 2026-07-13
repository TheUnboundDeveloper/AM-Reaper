# Release Compliance Audit — 2026-07-13

Adversarial, read-only pre-publication audit of the Reaper project (licensing,
copyright, redistribution, GPLv2, trademark, secrets, U.S. legal risk). This
document is the audit record **and** the live remediation tracker. It is not
legal advice; items marked for attorney review require a qualified lawyer.

**Overall verdict at audit time:** DO NOT RELEASE (public) until the blockers
below are cleared. **Compliance confidence at audit time: 34/100.**

**Post-remediation status (2026-07-13):** the live public GPL violation was
stopped (image repo taken offline); PII scrubbed from history; GPL source-offer,
third-party notices, font license, SPDX headers, and dependency docs added.
**Remaining before a public flip: B2 (attorney — proprietary-blob image
redistribution), H3/M3 (owner — naming + logo removal).** Source-and-patches
publication is in good shape; public *image* distribution is the open question.

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
| **H3** | Public repo name led with the ASUS/ASUSWRT trademark (origin/endorsement risk). | **IN PROGRESS (owner).** This repo is being renamed `ASUS-Merlin-Reaper` → **`AM-Reaper`** (all in-repo references updated 2026-07-13; GitHub rename by owner). "AM" is an abbreviation rather than the spelled-out mark — a clear improvement; the offline image repo (`ASUSWRT-Reaper`) should get the same treatment if re-created. In-text nominative credit to ASUS/Merlin stays. |

## Medium risk

| ID | Finding | Status |
|---|---|---|
| **M1** | Inter + Rajdhani fonts shipped without the required SIL OFL 1.1 notice. | **FIXED (2026-07-13).** Source: [`../LICENSES/OFL-1.1.txt`](../LICENSES/OFL-1.1.txt) + [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md). Image: patch `0152` (v1.5.0c) installs `www/fonts/OFL.txt`; build-verified present in the staged image. |
| **M2** | New Reaper source files (`rtrafd.c`, `rmcpd.c`, `reaper_inject.c/.h`, `Makefile`s, reaper CSS, `Reaper_*` pages) lacked per-file copyright/license headers. | **FIXED (2026-07-13).** Patch `0152` (v1.5.0c) adds `SPDX-License-Identifier: GPL-2.0-only` + copyright headers to every live Reaper source file; the full build passed with the headers in place. (`reaper_nav.js`/`R_*_Content.asp` from the audit list no longer exist — removed in the shell-architecture refactor.) |
| **M3** | `ASUSLogo.png` (ASUS trademark asset) added by patch `0144`, used as the AiMesh backdrop. | **OWNER-ACTION (planned removal).** Maintainer will remove ASUS-branded assets. Clean removal must also revert the AiMesh-backdrop CSS in `reaper_content.css` §11 (or swap in a Reaper asset) so no broken image reference remains. Written credit to ASUS/Merlin is legitimate nominative use and stays. |
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

## What this remediation round changed
**Round 1 (docs/licenses only):** added `docs/SOURCE-AVAILABILITY.md`,
`DEPENDENCIES.md`, `THIRD-PARTY-NOTICES.md`, `LICENSES/OFL-1.1.txt`, `.mailmap`,
`docs/PRE-PUBLICATION-CHECKLIST.md`, this file; edited `README.md` (M4),
`patches/README.md` (L3), `docs/REAPER-FIXES.md` (M6).

**Round 2 (with maintainer approval):**
- **History rewrite** (`git-filter-repo`): scrubbed personal Gmail + home path
  from all history, canonicalized identities, force-pushed (H1, H2, L1).
- **Firmware source** (in the build clone, exported as patches): SPDX headers +
  `www/fonts/OFL.txt`, build-verified, shipped as patch `0152` (v1.5.0c). The
  build clone's v1.5.0b was also exported as patch `0151`, bringing the public
  series current (v1.0 → v1.5.0c, 152 patches).
- **Still not done:** B2 (attorney), H3/M3 (owner) — see the tables above.
