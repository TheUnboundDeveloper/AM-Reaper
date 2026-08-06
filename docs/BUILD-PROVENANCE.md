# Build Provenance — from published image back to source

This document lets anyone verify, end to end, that a published Reaper firmware
image was built from exactly the source published in this repository — with
**nothing added or left out** — without having to trust us and without us
re-hosting the multi-gigabyte vendor tree.

The machine-readable record is [`provenance/manifest.json`](../provenance/manifest.json);
the CI workflow [`.github/workflows/verify-provenance.yml`](../.github/workflows/verify-provenance.yml)
re-checks every reproducible entry on each run.

> **Reviewers:** for the narrative walkthrough — the trust model, why these
> choices, a step-by-step verification session, and what to do if your
> reproduction doesn't match — see [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).
> This file is the compact reference.

## The chain

```
  upstream base commit  ──(git am the published patches)──▶  source tree  ──(make)──▶  firmware image
  3006.102.8-beta2                                          (tree hash)              (SHA-256, published)
  a7ebfa133a
```

Each link is pinned and independently checkable:

1. **Base** — Asuswrt-Merlin `3006.102.8-beta2`, commit
   `a7ebfa133ad7e5efc23ed6bb8ee912bc72fd00b3`, from upstream
   `RMerl/asuswrt-merlin.ng`. **This pin never moves.** Reaper changes ride the
   [`patches/`](../patches) series; upstream carry-forwards (e.g. the Merlin
   3006.102.8 update that became v2.1.2) are **cherry-picked, not rebased**, so
   the base — and therefore this recipe — stays constant across releases.
2. **Patches** — the `patches/NNNN-*.patch` series, applied with
   `git am --keep-cr` (the `--keep-cr` matters: a few third-party files are
   CRLF and the series fails without it).
3. **Source tree** — after applying the first *N* patches for a given release,
   the Git **tree hash** of `release/src/router` is a content-addressed
   fingerprint of the complete corresponding source. It depends only on file
   content — not on commit author, date, or message — so it is reproducible by
   anyone and reveals nothing about the build host.
4. **Image** — the firmware `.pkgtb`, whose SHA-256 is published in each
   release's `SHA256SUMS-*.txt` and recorded in the manifest.

## Verify it yourself

```sh
# 1. Get the pinned upstream base (includes the vendor blobs upstream ships)
git clone https://github.com/RMerl/asuswrt-merlin.ng
cd asuswrt-merlin.ng
git checkout a7ebfa133a          # 3006.102.8-beta2

# 2. Apply this repo's published patches for the release you want to verify
#    (use the first <patch_count> patches from provenance/manifest.json)
git config user.email you@example.com && git config user.name you
git am --keep-cr /path/to/AM-Reaper/patches/[0-9]*.patch

# 3. Hash the corresponding source and compare to the manifest
git rev-parse HEAD:release/src/router
#  -> must equal releases[].source_tree["release/src/router"] for that version

# 4. Confirm the image you downloaded matches the published hash
sha256sum RT-BE96U_3006_102.8_Reaper_<ver>_nand_squashfs.pkgtb
#  -> must equal releases[].images[].sha256
```

If step 3 matches, the published patches reproduce the published source exactly.
If step 4 matches, the image you hold is the one that was built. CI does steps
1–3 automatically for every `verifiable` release.

## Per-release record (RT-BE96U, the primary model)

| Version | Base | Patches | `release/src/router` tree | Source reproducible in CI |
|---|---|---|---|---|
| **v2.1.5** | `a7ebfa133a` | `0001`–`0322` | `9c98f7483f8eb3f8c0d1b5250b8bf3d38803f63c` | ✅ yes |
| **v2.1.4** | `a7ebfa133a` | `0001`–`0318` | `066a89ce574f3bdccbdb1af40d354f6ded822574` | ✅ yes |
| **v2.1.3** | `a7ebfa133a` | `0001`–`0315` | `6ac67c56c668efbb85ae80fd550350a0f7d6b012` | ✅ yes |
| **v2.1.2** | `a7ebfa133a` | `0001`–`0310` | `b2c357fa4a340d51a1cd6ef8777693781db92c56` | ✅ yes |
| **v2.1.1** | `a7ebfa133a` | `0001`–`0290` | `3ae0d9144034bfc3a62fb5814d798a45b7db3ac6` | ✅ yes |
| **v2.1.0** | `a7ebfa133a` | `0001`–`0289` | `96e3ea406837de4d26558c2a9f411eeeb17cb105` | ✅ yes |
| *(base)* | — | none | `91ac46a9fde7714dbed651d02c04898b4e134be0` | — |

Every shipped RT-BE96U image through v2.1.5 is reproducible from the published
patches: patches `0290`–`0322` (the v2.1.1 changes, the v2.1.2 Merlin 3006.102.8
carry-forward, the v2.1.3/v2.1.4 feature and field fixes, and the v2.1.5 field
fixes) were exported and **verified** to reproduce the trees above — applying
`0001`–`0290` yields `3ae0d914…` (v2.1.1), `0001`–`0310` yields `b2c357fa…`
(v2.1.2), `0001`–`0315` yields `6ac67c56…` (v2.1.3), `0001`–`0318` yields
`066a89ce…` (v2.1.4), and `0001`–`0322` yields `9c98f748…` (v2.1.5). The
19 carry-forward patches (`0291`–`0309`) retain their original Asuswrt-Merlin
authorship; the Reaper-authored patches use the Reaper identity. CI reproduces
every tree on each run. **The built fleet is ahead of the exported series:** the
v2.1.6 → v2.1.9 rungs are built + shipped on all five models but not yet exported
to patches (the series is regenerated for those rungs at publish). The RT-BE86U /
RT-BE88U / GT-BE98 / GT-BE98 Pro images (current at v2.1.9) are produced by
porting the shared code onto each per-model branch (banner / target.mak / blob
overlay); the patch series is RT-BE96U-only, so the tree hash above is the
RT-BE96U reference and the siblings are not independently patch-reproducible
(their image SHAs are in each `SHA256SUMS-<MODEL>-Reaper_<version>.txt` on the
release ladder).

## Build & verification logs

Each release's build and `reaper_verify` (19-check packaging gate) logs are
summarized under [`provenance/logs/<version>/`](../provenance/logs) — the
meaningful lines (configured build profile, `MAKE_EXIT=0`, the "Done! Image"
marker, every verify check, and the built image hashes), with the build-host
path normalized. The full raw logs are large (~10 MB of compiler output) and
are attached to the corresponding GitHub Release.

## History & coverage

Provenance is recorded for the **RT-BE96U** — the primary development platform.
The [manifest](../provenance/manifest.json) covers it back to **v1.8.6**:

- **v2.1.0 – v2.1.5** carry the full record and are **reproducible in CI**
  (`verifiable: true`): source-tree hash, image SHA-256s, and logs, with the
  published patch series proven to reproduce the tree. (The built fleet has since
  advanced to **v2.1.9**; those rungs are shipped but not yet exported to patches —
  the series and provenance are regenerated for them at publish time.)
- **v1.8.6 – v2.0.8** are **historical** entries (`verifiable: false`): the build
  log + `reaper_verify` summary and the `release/src/router` source-tree
  fingerprint are recorded, but the firmware images themselves are not retained,
  so these carry logs + metadata rather than a CI-reproduced image. (The
  `reaper_verify` gate itself was introduced at **v1.8.6a**; v1.8.6 predates it
  and records build success via `MAKE_EXIT=0` only. v1.9.8 and v2.0.9 have no
  entry — the former was never separately logged, the latter was reverted.)

**Anything before v1.8.6 is not available.** The project was in its infancy then
and was not being developed as an official build for anyone other than the
developer, so no release-grade build/verification record was kept. Provenance
begins where the project began shipping as a reproducible, for-others build.

## Why the full tree isn't re-hosted

Not a size limit — the constraint is that the buildable tree contains
proprietary **Broadcom / ASUS / Trend Micro** prebuilt blobs that we cannot
redistribute. Everything in *this* document sidesteps them: a tree hash and a
build log expose nothing proprietary, and the base checkout that reviewers use
already contains the same blobs upstream ships. The complete corresponding
source for the GPL components is the pinned base plus the `patches/` series;
see [`SOURCE-AVAILABILITY.md`](SOURCE-AVAILABILITY.md).
