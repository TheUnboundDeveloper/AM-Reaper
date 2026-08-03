# Release Process — GitHub as the distribution channel

End-to-end path from a local build to a published GitHub Release, and what the
CI workflows check along the way.

## Why CI does not compile the firmware

The buildable tree (Asuswrt-Merlin base + proprietary Broadcom/ASUS prebuilts)
is not in this repository and cannot be redistributed, so GitHub runners can
never produce an image. **Compiling stays local** (WSL Ubuntu 20.04, see
`build-scripts/README.md` and `docs/DEV-SETUP.md`). Everything after the build
is automated here.

## The pipeline

```
1. BUILD (local, WSL)     build-scripts/build_<model>.sh  → images land in the
                          local firmware ladder (asuswrt-merlin.ng/reaper-firmware/)

2. STAGE (local)          build-scripts/stage_release.ps1 -Version vX.Y.Z
                          → copies images into releases/<Model>/<MODEL>-REAPER-vX.Y.Z/
                          → writes per-model SHA256SUMS, verifies every copy
                          → refreshes releases/latest.json
                          → commits locally (never pushes)

3. REVIEW + PUSH (owner)  git push origin main
                          → "Repo hygiene" workflow validates the push

4. TAG (owner)            git tag vX.Y.Z && git push origin vX.Y.Z
                          → "Publish release" workflow verifies checksums,
                            extracts the CHANGELOG section, and creates the
                            GitHub Release with all firmware assets attached
```

Update `docs/CHANGELOG.md` (a `## vX.Y.Z — Title` section) **before** tagging —
the release notes are extracted from it automatically.

## The workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `repo-hygiene.yml` | every push/PR | Patch series gapless + single `From:` identity; PII scan (allowlist: `.github/pii-allowlist.txt`); no file at GitHub's 100 MB hard limit; every `SHA256SUMS-*` in `releases/` verifies |
| `release.yml` | tag push `v*` (or manual re-run) | Verifies staged checksums, builds combined `SHA256SUMS-<ver>.txt`, extracts CHANGELOG notes, creates/updates the GitHub Release with all `.pkgtb` + sums files |
| `patch-apply-check.yml` | manual, or PR touching `patches/` | Fetches the pinned upstream base (`3006.102.8-beta2`, `a7ebfa133a`) and applies all patches with `git am --keep-cr` — mechanical proof the published corresponding source is complete |

## Fixing a release

- **Bad or missing assets on an existing release:** re-run "Publish release"
  via *Actions → Publish release → Run workflow* with the tag name — it
  re-uploads with `--clobber` and refreshes the notes.
- **Wrong firmware staged:** fix `releases/…` on main, push, then either move
  the tag (`git tag -f` + force-push the tag; the workflow re-runs) or cut a
  point release (`vX.Y.Za`) — point releases are the safer default.
- **Hygiene failure on push:** the error annotation names the file; checksum
  failures mean the staged image no longer matches its SHA256SUMS (restage).

## Notes

- **Loaders** (`*_loader.pkgtb`, recovery-only) stay in the local ladder and are
  not distributed; they're available on request.
- `releases/latest.json` is a machine-readable manifest (version, file, sha256,
  size, release-asset URL per model) — the foundation for a future in-firmware
  update check. It always describes the most recently staged version.
- Each full release adds ~750 MB of binaries to git history. Keeping images
  in-tree was a deliberate choice (visibility in the file tree); if clone size
  ever becomes a problem, the fallback is release-assets-only distribution —
  the `release.yml` workflow needs no change for past releases, only the
  staging step would stop committing images.
