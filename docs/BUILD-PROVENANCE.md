# Build Provenance — from published image back to source

This document lets anyone verify, end to end, that a published Reaper firmware
image was built from exactly the source published in this repository — with
**nothing added or left out** — without having to trust us and without us
re-hosting the multi-gigabyte vendor tree.

The machine-readable record is [`provenance/manifest.json`](../provenance/manifest.json);
the CI workflow [`.github/workflows/verify-provenance.yml`](../.github/workflows/verify-provenance.yml)
re-checks every reproducible entry on each run.

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
| **v2.1.2** | `a7ebfa133a` | *(0290+ export owed)* | `b2c357fa4a340d51a1cd6ef8777693781db92c56` | pending patch export |
| **v2.1.1** | `a7ebfa133a` | *(0290+ export owed)* | `3ae0d9144034bfc3a62fb5814d798a45b7db3ac6` | pending patch export |
| **v2.1.0** | `a7ebfa133a` | `0001`–`0289` | `96e3ea406837de4d26558c2a9f411eeeb17cb105` | ✅ yes |
| *(base)* | — | none | `91ac46a9fde7714dbed651d02c04898b4e134be0` | — |

> **Known gap being closed:** the published patch series currently ends at
> v2.1.0 (`0289`), while v2.1.1 and v2.1.2 images exist. Their source trees are
> fingerprinted above, but they are not yet reproducible from *published*
> patches until the `0290+` series is exported. That export is the last step to
> make every shipped image independently reproducible; the manifest marks these
> `"verifiable": false` until then, and CI will not claim to have verified them.

## Build & verification logs

Each release's build and `reaper_verify` (17-check packaging gate) logs are
summarized under [`provenance/logs/<version>/`](../provenance/logs) — the
meaningful lines (configured build profile, `MAKE_EXIT=0`, the "Done! Image"
marker, every verify check, and the built image hashes), with the build-host
path normalized. The full raw logs are large (~10 MB of compiler output) and
are attached to the corresponding GitHub Release.

## Why the full tree isn't re-hosted

Not a size limit — the constraint is that the buildable tree contains
proprietary **Broadcom / ASUS / Trend Micro** prebuilt blobs that we cannot
redistribute. Everything in *this* document sidesteps them: a tree hash and a
build log expose nothing proprietary, and the base checkout that reviewers use
already contains the same blobs upstream ships. The complete corresponding
source for the GPL components is the pinned base plus the `patches/` series;
see [`SOURCE-AVAILABILITY.md`](SOURCE-AVAILABILITY.md).
