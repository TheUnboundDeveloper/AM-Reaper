# docs/ — RT-BE96U "reaper" documentation

Project-focused documentation for the hardened RT-BE96U fork. Start here.

## Read in this order

1. **[PROJECT.md](PROJECT.md)** — what this fork is, scope, hard rules, threat model, flashing, legal. (The collapsed version of the upstream READMEs.)
2. **[RELEASE-NOTES.md](RELEASE-NOTES.md)** — what each published image contains and how to flash it.
3. **[DEV-SETUP.md](DEV-SETUP.md)** — the hard-won contributor build/edit environment: WSL 20.04, gcc-10.3 toolchains, host deps, the build recipe and its traps, the editing/tooling gotchas, and how to verify a change. **If you want to build or patch the firmware, this is the one.**
4. **[REAPER-FIXES.md](REAPER-FIXES.md)** — authoritative list of every security fix applied (all audit rounds), with commits.
5. **[GPL-MERGE.md](GPL-MERGE.md)** — maintainer guide for rebasing the hardening onto a new upstream/GPL drop.
6. **[ENTERPRISE-ROADMAP.md](ENTERPRISE-ROADMAP.md)** — package-update candidates and feature ideas (what's in-tree-but-disabled, what to add via Entware).
7. **[../patches/](../patches/)** — the hardening itself, as patches you apply onto an upstream checkout.

## Upstream originals kept for reference

- **[`../LICENSE`](../LICENSE)** (repo root) — the GPL text that governs the open-source components.
- **`README.proprietary`** — the upstream blob-licensing notice (summarized in `PROJECT.md` § Legal).
- **`Changelog-3006.txt`** — upstream version history for the 3006.102 line this fork is based on.

The other upstream READMEs (generic multi-model build notes, stale project blurbs, upstream support pointers) were out of date for this BE96U-only fork; their still-relevant content was folded into `PROJECT.md` / `DEV-SETUP.md`.

## Not in the git tree

- **GitHub Releases** — the flashable `.pkgtb` images for end users who only want to flash (build artifacts, not source).
