# Release Process — from source rung to published firmware

End-to-end path for a Reaper release, and what each workflow checks along the
way. **Read "Cutting a rung" first** — every release problem we have actually
hit came from that step being done by hand and missing a piece.

> **Doing a release right now?** Use [`RELEASE-CHECKLIST.md`](RELEASE-CHECKLIST.md)
> — the tick-box running order from local rung to published firmware. This file
> is the reference that explains *why* each step is there.

## Two build paths

| | Where | Used for |
|---|---|---|
| **CI clean-room** (`public-build.yml`) | GitHub runners, container, from `patches/` only | **The release path.** Builds every model × variant from the published series, so what ships is provably what the repo describes. |
| **Local** (`build-scripts/build_<model>.sh`) | WSL Ubuntu 20.04, canon clone | Fast iteration, metal validation before a fleet run, and the decomposed image diff (CI vs local) that catches container-only defects. Not the release path. |

The buildable tree (Asuswrt-Merlin base + proprietary Broadcom/ASUS prebuilts)
is not in this repository — CI reconstructs the *source* from `patches/` and
pulls the pinned toolchain/prebuilts at build time.

## Cutting a rung

A "rung" is one source release: the patches plus the four artifacts that keep
the series, the CI, and the provenance record in agreement. **All five belong in
the same commit.** Miss one and the failure shows up late and confusingly — a
build that aborts on a version assertion, siblings that fail to apply overlays,
or a release with no reproducible provenance.

| # | Artifact | Why it fails if you skip it |
|---|---|---|
| 1 | `patches/` | The build *is* the series. A missing rung silently builds the previous version. |
| 2 | `EXPECTED_VERSION` in `public-build.yml` | Asserted after the series is applied; a mismatch aborts the run by design. |
| 3 | `provenance/manifest.json` | `patch_count` is the key CI matches on; without an entry the build warns and the release is not self-verifying. |
| 4 | `overlays/*.patch` | Only if the rung touches a file a per-model overlay also patches — then sibling builds conflict. |
| 5 | `.github/pii-allowlist.txt` | Path-matched, so any renumber invalidates it. |

One command does all five, plus the sibling fan-out:

```bash
./build-scripts/cut_fleet.sh --version v2.3.4
```

`cut_fleet.sh` is the entry point. It runs `cut_rung.sh` (the five artifacts
above), then ports the rung onto the four sibling branches, then handles the
overlays — **in that order.** Regenerating an overlay before the port produces a
patch that *reverts* the rung on every sibling, and it applies cleanly, so
nothing downstream catches it. That is the 2026-08-10 regression, and the order
here is what prevents it. Run `cut_rung.sh` directly only for a canon-only
change you are deliberately not fanning out.

It refuses to run unless the canon clone is on the right branch, has no
uncommitted tracked changes, and already carries the version bump. Then it
exports the new patches (doc hunks excluded), normalizes the `From:` identity
and scrubs the build-host strings, replays the **whole** series onto the pinned
base to capture `source_tree_from_series` and prove the version and the tree,
writes the provenance entry, checks the rung against every overlay, moves the
CI pin, and re-runs the PII rules. It never commits and never pushes.

Two things it deliberately leaves to you: the provenance `summary` prose (it
writes a `TODO`) and the `docs/CHANGELOG.md` section (release notes are
extracted from it).

### Why the replay matters

Two source-tree hashes are recorded per release, and they are not the same:

- `source_tree` — the tree of the build commit on the model branch.
- `source_tree_from_series` — what `git am --keep-cr patches/[0-9]*.patch` onto
  the pinned base yields. **This is what CI computes and compares**, so this is
  the one that must be right.

They differ only by three vendored `openssh-sftp` `*.md` files that the series'
doc-hunk exclusion strips. `cut_rung.sh` asserts that nothing else differs — if
a source file shows up in that diff, the series does not reproduce the build and
the rung is not shippable.

## Publishing

```
1. CUT                cut_fleet.sh --version vX.Y.Z
                      (rung → sibling ports → overlays, in that order)

2. PROSE              provenance summary + models_note, CHANGELOG section
                      (release notes are extracted from the changelog)

3. COMMIT + HUB       commit the lean repo; push canon AND the four ported
                      branches to the bare hub -- skipping the hub push blocks
                      the NEXT rung on cut_fleet's ancestry check

4. PUSH               PR into main (runs patch-apply-check + verify-provenance)
                      or straight to main (runs repo-hygiene ONLY)

5. BUILD              Actions → Public build → Run workflow
                      model=all, both variants, version BLANK, publish UNTICKED
                      (the overlay identity gate runs first and gates the matrix)

6. TEST               flash one image on metal before fanning out

7. PUBLISH            re-dispatch with publish ticked, or dispatch release.yml
                      with the green run's run_id to publish without rebuilding
                      → one GitHub Release per model, "Reaper vX.Y.Z — <MODEL>"

8. MANIFEST           the refresh_manifest job rewrites updates/manifest_3006.txt,
                      latest.json and the release note from the PUBLISHED assets
```

Publishing is gated **twice**: `github.ref == 'refs/heads/main'` *and* the
`publish` input, which defaults to off. A dispatch on main with the box clear
builds and verifies without shipping.

Releases are **per-model** so models can version independently (RT-BE96U at
v2.3.3 while siblings catch up on the fan-out).

### Traps that have actually bitten

- **A manual per-model publish does not run `refresh_manifest`.** The release
  exists but routers keep seeing the old version on their update check. Run
  `build-scripts/refresh_manifest.py` yourself, or publish via the full path.
- **GitHub's re-run buttons replay the workflow file from the old commit.** To
  pick up a workflow fix you must `workflow_dispatch` from *Branch: main* and
  pass the tag as an input.
- **The on-router release note is cached** in `/tmp/release_note0.txt` and
  "Check for update" does not force a re-fetch. `rm -f` it and reload.
- **A sibling build leaves the clone on that model's branch.** Verify with
  `git branch --show-current` before any RT-BE96U build or commit; `cut_rung.sh`
  asserts this for you.

## The workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `public-build.yml` | manual dispatch | Clean-room build, model × variant matrix. Applies `patches/`, asserts `EXPECTED_VERSION`, compares the series tree against `provenance/manifest.json`, runs the packaging gate, uploads artifacts, optionally hands off to `release.yml` |
| ↳ `overlays` job | first, gates the matrix | Asserts each `overlays/<MODEL>.patch` carries **identity only** — in the seven banner-referencing files every changed line must be a banner swap, the banner must be that model's, and no `.dict` may appear. Seconds, no base clone. `git apply` cannot catch a stale overlay: one that reverts shared code still applies cleanly, which is how a fixed first-boot login loop was silently reintroduced in Aug 2026 |
| `release.yml` | per-model tag `v*-*`, dispatch, or called | Parses `v<version>-<MODEL>`, verifies checksums, extracts CHANGELOG notes, creates/updates the per-model Release. Accepts a `run_id` to publish an existing green build with no rebuild |
| `repo-hygiene.yml` | every push/PR | Series gapless; no disallowed `From:` identity; PII scan against `.github/pii-allowlist.txt`; no file at GitHub's 100 MB limit; staged checksums verify |
| `verify-provenance.yml` | dispatch, or PR touching `patches/`/manifest | Lints the manifest and reproduces `verifiable` entries from the pinned base |
| `patch-apply-check.yml` | manual, or PR touching `patches/` | Applies the whole series with `git am --keep-cr` — mechanical proof the corresponding source is complete |

## Fixing a release

- **Bad or missing assets:** re-run "Publish release" via dispatch with the tag
  name — it re-uploads with `--clobber` and refreshes the notes.
- **Wrong firmware published:** cut a point release (`vX.Y.Za`). Moving a tag
  works but point releases are the safer default.
- **Hygiene failure on push:** the annotation names the file. A PII hit inside
  `patches/` means fixing the source commit message and re-exporting — do not
  just add the path to the allowlist.

## Notes

- **Loaders** (`*_loader.pkgtb`, recovery-only) are not distributed; available
  on request.
- `updates/manifest_3006.txt` is what the router's update check reads (one line
  per model/variant: `MODEL#VARIANT#X.Y.Z#url#sha#size`); `releases/latest.json`
  is the machine-readable mirror.
- The base pin (`3006.102.8-beta2`, `a7ebfa133a`) never moves. Upstream
  carry-forwards are cherry-picked, not rebased, so the reproduction recipe
  stays stable across releases.
