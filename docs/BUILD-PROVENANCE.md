# Build Provenance — from published image back to source

> **Doc status:** current as of **v2.7.8** · 2026-08-26 <!--@stamp-->

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

**Read the right column.** Two tree hashes are recorded per release and they are
**not** the same value. `source_tree_from_series` is what applying the published
patches to the pinned base actually yields — that is the one CI compares
(`verify-provenance.yml` prefers it and only falls back to `source_tree`), and the
one to check your own replay against. `source_tree` is the build commit's tree in
the private build clone, which additionally contains the vendored `*.md` files the
doc-hunk exclusion strips from the series. Comparing a replay against the
build-commit column will never match, by design.

| Version | Base | Patches | `release/src/router` **from the series** (what CI compares) | build-commit tree | Release |
|---|---|---|---|---|---|
| **v2.4.3** | `a7ebfa133a` | `0001`–`0428` | `81025000fb194ea9b9a289418f07028a691a5fb1` | `e8742938df2766337b2d4c27cb1df4fb047cb6fd` | source rung |
| **v2.4.2** | `a7ebfa133a` | `0001`–`0426` | `1c8c908a0a7c14b12419a3720f9d5b2007b068a7` | `60e0a1e57e53b1562d01b4e484fcb6c797976864` | source rung — no images; folded into v2.4.3 |
| **v2.4.1** | `a7ebfa133a` | `0001`–`0424` | `1db8fe150ac99c2adc17041d696666cf0dc299c6` | `545e459661262bf79a3c2ed0aa597005f87e550a` | source rung |
| **v2.3.7** | `a7ebfa133a` | `0001`–`0406` | `7f48393d768d564fe8dbb5722fcfa26a8e6f6181` | `f1e0db6373976ae8740a2484f74bb577ed3efbaf` | ✅ published (all five models) |
| **v2.3.6** | `a7ebfa133a` | `0001`–`0399` | `3740a7192671ec39854d96f8383e202b46599e90` | `e9cc24c92d938b3abb4c62d06d7da50993c88c99` | source rung — never published |
| **v2.3.5** | `a7ebfa133a` | `0001`–`0397` | `a8b2d10782a78668a5fba30f53b61d5f0735ccec` | `5743597446a3c32eaeeed681d91473a8dfbf4e68` | source rung — never published |
| **v2.3.4** | `a7ebfa133a` | `0001`–`0390` | `ee23af634aaf311de2323c777de33530613b2ecc` | `a884fdee5db402c128b238056b654034d9857dba` | ✅ published (all five models) |
| **v2.3.3** | `a7ebfa133a` | `0001`–`0388` | `b034902b6905c04ab6d2934121fe15dc0619e840` | `24334ae677710d59615fcfecf1f317fe5a40325d` | source rung — never published |
| **v2.3.2** | `a7ebfa133a` | `0001`–`0378` | `1357bd3456802b1f063009e64b6ebbc12e0e45be` | `c24138c41233a6a1cec7ee2496518cddc2cc4950` | ✅ published (all five models) |
| **v2.3.1** | `a7ebfa133a` | `0001`–`0374` | `f45570426e350a29bba9245ee1b11ffab41ecd1a` | `45fed7610e4d1316f4fabd664f56e37d88cd47a5` | ✅ published |
| **v2.1.5** | `a7ebfa133a` | `0001`–`0325` | `ebbed045f4841b89a8c8d1eacce74961518445b9` | `9c98f7483f8eb3f8c0d1b5250b8bf3d38803f63c` | ✅ published |
| **v2.1.4** | `a7ebfa133a` | `0001`–`0321` | `e2c1828901d08089a951e14ec982212fcf337923` | `066a89ce574f3bdccbdb1af40d354f6ded822574` | ✅ published |
| **v2.1.3** | `a7ebfa133a` | `0001`–`0318` | `d89a6bec8ca5ca5189b723efa0f7b17ffa4bfecf` | `6ac67c56c668efbb85ae80fd550350a0f7d6b012` | ✅ published |
| **v2.1.2** | `a7ebfa133a` | `0001`–`0313` | `08bfbd2870471409144fdb51d9999cd87b44899a` | `b2c357fa4a340d51a1cd6ef8777693781db92c56` | ✅ published |
| **v2.1.1** | `a7ebfa133a` | `0001`–`0293` | `7d0c3e2fbe4fd3ce7672c9026b6cb43e635e5cd5` | `3ae0d9144034bfc3a62fb5814d798a45b7db3ac6` | ✅ published |
| **v2.1.0** | `a7ebfa133a` | `0001`–`0292` | `0a1eb6136cdacca581a95eac7f6aeba0ca08b740` | `96e3ea406837de4d26558c2a9f411eeeb17cb105` | ✅ published |
| *(base)* | — | none | — | `91ac46a9fde7714dbed651d02c04898b4e134be0` | upstream |

> Generated from [`../provenance/manifest.json`](../provenance/manifest.json) rather than
> transcribed. This table lists rungs through v2.4.3; the manifest itself is the complete, current
> ledger (through v2.7.7). Note the patch ranges for **v2.1.0 – v2.1.5** are the **post-repair** numbers: the
> 2026-08-09 series repair restored three never-extracted commits and shifted everything after
> `0245` by +3, so an older copy of this table showing `0289`/`0310`/`0322` was describing the same
> releases under the pre-repair numbering.

Every shipped RT-BE96U image through v2.1.5 is reproducible from the published
patches: patches `0290`–`0322` (the v2.1.1 changes, the v2.1.2 Merlin 3006.102.8
carry-forward, the v2.1.3/v2.1.4 feature and field fixes, and the v2.1.5 field
fixes) were exported and **verified** to reproduce the trees above — applying
`0001`–`0290` yields `3ae0d914…` (v2.1.1), `0001`–`0310` yields `b2c357fa…`
(v2.1.2), `0001`–`0315` yields `6ac67c56…` (v2.1.3), `0001`–`0318` yields
`066a89ce…` (v2.1.4), and `0001`–`0322` yields `9c98f748…` (v2.1.5). The
19 carry-forward patches (`0291`–`0309`) retain their original Asuswrt-Merlin
authorship; the Reaper-authored patches use the Reaper identity. CI reproduces
every tree on each run. **The exported series leads the fleet:** the series runs
to `0550` <!--@patchcount--> (v2.7.8 <!--@treever-->, RT-BE96U-only), while the newest **published** release is
v2.7.7 <!--@pubver-->. The RT-BE86U /
RT-BE88U / GT-BE98 / GT-BE98 Pro images (published at v2.7.6, alongside the
RT-BE92U's experimental prerelease) are produced by
porting the shared code onto each per-model branch (banner / target.mak / blob
overlay); the patch series is RT-BE96U-only, so the tree hash above is the
RT-BE96U reference and the siblings are not independently patch-reproducible
(their image SHAs are in each `SHA256SUMS-<MODEL>-Reaper_<version>.txt` on the
release ladder).

## Build & verification logs

Each release's build and `reaper_verify` (the packaging gate; its check list grows as
new classes of packaging defect are found) logs are
summarized under [`provenance/logs/<version>/`](../provenance/logs) — the
meaningful lines (configured build profile, `MAKE_EXIT=0`, the "Done! Image"
marker, every verify check, and the built image hashes), with the build-host
path normalized. The full raw logs are large (~10 MB of compiler output) and
are attached to the corresponding GitHub Release.

## History & coverage

Provenance is recorded for the **RT-BE96U** — the primary development platform.
The [manifest](../provenance/manifest.json) covers it back to **v1.8.6**:

- **Every rung in the table above is `verifiable: true`** — source-tree fingerprint,
  patch count and logs recorded, with the published series proven to reproduce the
  tree. **v2.3.2** was the first rung built and published end-to-end by the public
  clean-room pipeline.
- **`verifiable` means the source is reproducible, NOT that the release shipped.**
  These are independent facts and the manifest only tracks the first one reliably.
  Image SHA-256s are populated only for **v2.1.0–v2.1.5** and **v2.3.1**; every other
  rung — including v2.3.2, v2.3.4 and v2.3.7, which are all published on all five
  models — carries an empty `images` list simply because nothing refreshed it after
  the build shipped. **Do not read an empty `images` as "never released"**; that
  inference is what produced a documented contradiction on 2026-08-12. The
  authoritative record of what shipped is the
  [Releases page](https://github.com/TheUnboundDeveloper/AM-Reaper/releases).
- **Many rungs are source rungs that published no images** — v2.3.3, v2.3.5, v2.3.6,
  v2.3.8–v2.4.2, and a large share of the v2.4.x–v2.7.x line (e.g. v2.6.1–v2.6.9, v2.7.0,
  v2.7.2, v2.7.4–v2.7.6). They are still exported, replay-verified and CI-covered; they simply
  never became a download. v2.3.8, v2.3.9 and v2.4.0 in particular were the
  intermediate steps of the native-firewall work and were folded into the single
  v2.4.1 rung (`0407`–`0424`). v2.4.2 (`0425`–`0426`) is likewise folded into
  **v2.4.3** (`0427`–`0428`): a security audit of the v2.4.2 rung found six defects
  in the code it had just added, so the remediation was cut as its own rung rather
  than published under a version whose images already existed on the test ladder.
  **v2.4.3 is the first rung since v2.4.1 to carry image SHA-256s**, for both
  RT-BE96U variants.
- **v2.1.6 – v2.3.0** are shipped rungs with no per-release row here; the series and
  provenance were regenerated forward rather than backfilled per rung.
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
