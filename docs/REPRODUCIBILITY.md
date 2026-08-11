# Verifying a Reaper Build — a Guide for Reviewers

This document explains, for someone who does not trust us and shouldn't have to,
how to confirm that a published Reaper firmware image was built from exactly the
source in this repository — **with nothing added, removed, or hidden** — and how
our automation proves the same thing on every change.

It is the narrative companion to two precise artifacts:

- [`BUILD-PROVENANCE.md`](BUILD-PROVENANCE.md) — the per-release reference table and recipe.
- [`../provenance/manifest.json`](../provenance/manifest.json) — the machine-readable record the CI checks.

If you only read one section, read **[§3 Verify it yourself](#3-verify-it-yourself)**.

---

## 1. The guarantee, in one paragraph

Every published image is tied to an exact, **content-addressed** source
fingerprint. Take the pinned upstream base commit, apply this repository's
published patch series, and hash the `release/src/router` directory: you get a
Git tree hash that must equal the value we record for that release. Because a Git
tree hash is derived purely from file content — not from who committed it, when,
or with what message — anyone can recompute it and get the same 40 hex characters
we did, or catch us if the published patches don't actually produce the source we
claim. Our CI does exactly this reproduction on every change.

---

## 2. What is proven, what you trust, what is out of scope

Being explicit about the trust boundary is the point of this document.

**Mechanically proven (you do not have to trust us):**
- That the **published patches applied to the published base reproduce the exact
  source tree** we record for each release. This is a byte-for-byte content
  match, verifiable with stock `git`. If we quietly shipped a patch that isn't in
  the series, or the series doesn't produce the tree we claim, the hashes diverge
  and the check fails.
- That the **image you downloaded is the one we published** — its SHA-256 is in
  each release's `SHA256SUMS-*.txt` and in the manifest.

**What you still trust (and how we narrow it):**
- That the **compiler turned that source into that binary** faithfully. Full
  bit-for-bit binary reproducibility is a harder, separate goal (it needs a
  pinned toolchain *and* the proprietary blobs below). We narrow this by
  publishing the build and `reaper_verify` logs (§6) and pinning the toolchain in
  [`../DEPENDENCIES.md`](../DEPENDENCIES.md) — but we do not claim bit-for-bit
  binary reproduction today, and we would rather say so than overclaim.

**Out of scope (and why):**
- The proprietary **Broadcom / ASUS / Trend Micro prebuilt blobs**. These are not
  ours to relicense or re-host; they ship in-tree from upstream and from ASUS's
  own GPL release. They are *not* part of the corresponding source for the GPL
  work, and — importantly — **nothing in the verification below touches them**.
  The base checkout you use already contains the same blobs upstream ships.

---

## 3. Verify it yourself

The whole verification is stock `git` plus `sha256sum`. Using **v2.1.2** as the
worked example (substitute any release from the manifest):

```sh
# --- (a) Get the pinned upstream base -----------------------------------------
git clone https://github.com/RMerl/asuswrt-merlin.ng
cd asuswrt-merlin.ng
git checkout a7ebfa133a           # tag 3006.102.8-beta2 — the pin never moves

# --- (b) Apply this repo's published patches ----------------------------------
git config user.email you@example.com && git config user.name reviewer
git am --keep-cr /path/to/AM-Reaper/patches/[0-9]*.patch
#   --keep-cr matters: a few third-party files are CRLF and the series
#   fails without it. This applies all 379 patches (through v2.3.3).

# --- (c) Hash the corresponding source and compare ----------------------------
git rev-parse HEAD:release/src/router
#   expected after all 374 patches (v2.3.1):
#                         f45570426e350a29bba9245ee1b11ffab41ecd1a
#   (this value is releases[].source_tree_from_series["release/src/router"])
#
#   v2.3.3 (all 379 patches) build-commit tree:
#                         18c5fc0eefa28393cdf038eeb2adb3a411fb6876
#   Its source_tree_from_series counterpart is recorded at publish time; the two
#   differ only by the three openssh-sftp *.md files described just below. The
#   379-patch replay was verified clean on 2026-08-10 — `git am --keep-cr`
#   returned 0 and the only diff was exactly those three files.
#
#   Two hashes are recorded per release. source_tree is the tree of the commit
#   the firmware was built from; source_tree_from_series is what this replay
#   yields. They differ ONLY by three vendored openssh-sftp documentation files
#   (README.md, SECURITY.md, .github/ci-status.md) that the series' *.md
#   doc-hunk exclusion strips. No source or code file differs, and
#   release/src-rt is identical. Compare against source_tree_from_series.
#
#   To check an EARLIER release instead, apply only its patch_count patches:
#     ls patches/[0-9]*.patch | head -325 | xargs git am --keep-cr   # v2.1.5

# --- (d) Confirm the image you downloaded is the published one ----------------
sha256sum RT-BE96U_3006_102.8_Reaper_v2.1.2_nand_squashfs.pkgtb
#   expected:  eab8bdd393cf435ccfae8f71bb631511bd5594cda0d44b54f0d9bebcf0489419
```

If **(c)** matches, the published patches reproduce the published source exactly.
If **(d)** matches, the image you hold is the one that was built. That is the full
chain: **base → patches → source tree → image.**

To verify an **earlier** release, apply only its first *N* patches
(`patch_count` in the manifest) — e.g. `0001`–`0289` for v2.1.0 — and compare to
that release's tree hash. The series is strictly additive, so each release is a
prefix of the next.

---

## 4. Why these specific choices

**Why a tree hash, not a commit hash.** A commit hash changes if the author,
date, or message changes, so it is not something an independent party can
reproduce. A *tree* hash is a pure function of file content. It is the right
primitive for "did the same source come out," and it incidentally exposes nothing
about our build host.

**Why we cherry-pick upstream, never rebase.** When we carry forward an upstream
Asuswrt-Merlin update, we cherry-pick it onto our branch rather than moving our
base. That keeps the base pinned at `a7ebfa133a` forever, so the reproduction
recipe in §3 is identical for every release, past and future. (It is also why you
never have to "guess whether it's beta2" — the base is one fixed commit,
documented in [`SOURCE-AVAILABILITY.md`](SOURCE-AVAILABILITY.md) and every release
record.)

**Why the patches keep upstream authorship.** The carry-forward patches
(`0291`–`0309` for v2.1.2) are upstream work; their `From:` lines are the original
Asuswrt-Merlin authors (Eric Sauvageau, dave14305, …), not us. We deliberately do
not rewrite that — attributing their work to ourselves would be dishonest, and
the authorship is irrelevant to the tree-hash reproduction anyway.

**Why we publish source, not the full built tree.** Not a size limit — the
constraint is the proprietary blobs in §2, which we cannot redistribute. The
complete corresponding source for the GPL work is the pinned base plus the
`patches/` series, and everything above verifies it without those blobs.

---

## 5. What the automation does

You do not have to take our word that the check passes: it runs in CI.

[`.github/workflows/verify-provenance.yml`](../.github/workflows/verify-provenance.yml)
fetches the pinned base, applies the published patches to each release's
checkpoint with `git am --keep-cr`, and asserts that
`git rev-parse HEAD:release/src/router` equals the tree hash in the manifest — for
**every** release marked reproducible. Any drift between the published patches and
the recorded provenance turns the check red. It runs on demand and on every pull
request that touches `patches/` or the manifest.

A companion check, [`repo-hygiene.yml`](../.github/workflows/repo-hygiene.yml),
enforces that the patch series is gapless and carries no leaked personal data.

---

## 6. The build and verification logs

Each release's logs are summarized under
[`../provenance/logs/<version>/`](../provenance/logs) — the configured build
profile, the `MAKE_EXIT=0` markers, the "Done! Image" confirmation, the built
image hashes, and every line of the 19-check `reaper_verify` packaging gate
(which confirms, among other things, that the "no-AI" variant contains no trace
of the AI Advisor, that the dictionaries are language-consistent, and that the
web server's shared-library closure resolves). Build-host paths are normalized;
the full raw logs (large — mostly compiler output) are attached to each GitHub
Release.

---

## 7. If your reproduction does not match

That is the check working, and we want to hear about it. A mismatch at step
**3(c)** means the published patches do not produce the source we recorded —
either the series is incomplete, or the manifest is wrong. Please open an issue
with: the release version, the tree hash you computed, your `git` version, and
whether you used `--keep-cr`. A mismatch at **3(d)** means the image you have is
not the one we published — re-download from the official release and re-check.

---

## 8. Per-release fingerprints

The authoritative, machine-readable list is
[`../provenance/manifest.json`](../provenance/manifest.json). For quick reference
(RT-BE96U, the primary model):

| Release | Base | Patches | `release/src/router` tree hash |
|---|---|---|---|
| v2.1.5 | `a7ebfa133a` | `0001`–`0322` | `9c98f7483f8eb3f8c0d1b5250b8bf3d38803f63c` |
| v2.1.4 | `a7ebfa133a` | `0001`–`0318` | `066a89ce574f3bdccbdb1af40d354f6ded822574` |
| v2.1.3 | `a7ebfa133a` | `0001`–`0315` | `6ac67c56c668efbb85ae80fd550350a0f7d6b012` |
| v2.1.2 | `a7ebfa133a` | `0001`–`0310` | `b2c357fa4a340d51a1cd6ef8777693781db92c56` |
| v2.1.1 | `a7ebfa133a` | `0001`–`0290` | `3ae0d9144034bfc3a62fb5814d798a45b7db3ac6` |
| v2.1.0 | `a7ebfa133a` | `0001`–`0289` | `96e3ea406837de4d26558c2a9f411eeeb17cb105` |

The image SHA-256s for each release are in the manifest and in the release's
`SHA256SUMS-*.txt`. (The last full-fleet build is **v2.3.2**, published through the
clean-room CI pipeline. **v2.3.3** is exported to patches (`0379`) and built for the
RT-BE96U only; its manifest entry and image hashes are added at publish time.)
