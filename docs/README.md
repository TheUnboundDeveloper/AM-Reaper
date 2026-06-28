# docs/ — RT-BE96U "reaper" documentation

Project-focused documentation for the hardened RT-BE96U fork. Start here.

## Read in this order

1. **[PROJECT.md](PROJECT.md)** — what this fork is, scope, hard rules, threat model, flashing, legal. (The collapsed version of the upstream READMEs.)
2. **[DEV-SETUP.md](DEV-SETUP.md)** — the hard-won contributor build/edit environment: WSL 20.04, gcc-10.3 toolchains, host deps, the build recipe and its traps, the editing/tooling gotchas, and how to verify a change. **If you want to build or patch the firmware, this is the one.**
3. **[../REAPER-FIXES.md](../REAPER-FIXES.md)** — authoritative list of every security fix applied (Round 1 + Round 2), with commits.
4. **[../ENTERPRISE-ROADMAP.md](../ENTERPRISE-ROADMAP.md)** — package-update candidates and enterprise feature ideas (what's in-tree-but-disabled, what to add via Entware).
5. **[../patches/](../patches/)** — the hardening itself, as patches you apply onto an upstream checkout.

## Other references

- **`../CLAUDE.md`** — guidance for AI coding agents working in this repo (layout, working-copy rules, where the project DB lives).
- **GitHub Releases** — the flashable `.pkgtb` images for end users who only want to flash (not in the git tree; they're build artifacts).
- **Upstream originals (kept in this folder)** — verbatim, for legal/compliance and history: **`License`** (GPL), **`README.proprietary`** (blob licensing), **`Changelog-3006.txt`** (3006.102 history). The out-of-date upstream readmes were folded into the project docs and removed.

## What "collapsing the old docs" means here

The upstream tree shipped several overlapping docs. The ones out of date with this BE96U-only fork were **folded into the project docs and deleted**; the still-current legal/historical ones were **kept here in `docs/`**:

| Old doc | Disposition |
|---|---|
| `README-merlin.txt` | **Deleted.** Generic upstream readme; its device list doesn't match this stripped repo. Relevant content (features, flashing, no-warranty, version-check privacy) folded into `PROJECT.md`. |
| `README.md` | **Deleted.** Stale upstream blurb (referenced the ~2017 v382 / dropped 380 branch). Superseded by `PROJECT.md`. |
| `README.TXT` | **Deleted.** Generic ASUS multi-SoC build readme (gcc-5.3 / Ubuntu 14.04 / MIPS-Ralink-QCA). Superseded by `DEV-SETUP.md`. |
| `SUPPORT.md` | **Deleted.** Pointed to the upstream SNBForums/issue tracker — N/A to this private fork. |
| `README.proprietary` | **Kept** in `docs/` — current, binding legal text (summarized in `PROJECT.md` § Legal). |
| `License` | **Kept** in `docs/` — GPL, legally required. |
| `Changelog-3006.txt` | **Kept** in `docs/` — accurate version history for the 3006.102 line this fork is based on. |

Deletions are local-only (the Windows mirror is never pushed). The kept files are the legal/compliance and historical record.
