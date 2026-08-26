# Reaper — the commands, and what each one is for

> **Doc status:** current as of **v2.7.8** · 2026-08-26 <!--@stamp-->

Everything in [`build-scripts/`](../build-scripts) exists to make one of four
things happen: **build an image**, **cut a rung**, **fan a rung out to the
fleet**, or **prove that what shipped is what the repo describes**. This file is
the map. [`RELEASE-PROCESS.md`](RELEASE-PROCESS.md) explains *why* each step is
there; [`RELEASE-CHECKLIST.md`](RELEASE-CHECKLIST.md) is the tick-box running
order for an actual release.

**If you have just cloned or forked this repository**, you cannot run most of
what is below — and that is by design, not an oversight. Read
[What a fork can and cannot run](#what-a-fork-can-and-cannot-run) first.

---

## The vocabulary

Three words get used precisely throughout the docs, and confusing them is the
usual source of "which command do I want?":

| Term | What it means |
|---|---|
| **build** | Compile one model × one variant into a flashable `.pkgtb`. Produces an image. Changes no repo state. |
| **rung** | One version's worth of source change, exported as patches with its provenance recorded and the CI pin moved. Produces repo state. No images. |
| **fleet** | A rung, plus the same change ported onto every sibling model branch, plus regenerated identity overlays. |

A rung is cut **once**; images can be built from it any number of times. The
patch series is the release — the images are just what that series compiles to.

---

## Building an image

```bash
build-scripts/build_be96u.sh            # build, leave the image in the tree
build-scripts/build_be96u.sh ship       # build, then copy to the release ladder
```

One launcher per model — `build_be96u.sh`, `build_be86u.sh`, `build_be88u.sh`,
`build_gtbe98.sh`, `build_gtbe98pro.sh`, `build_be92u.sh`. Each is a thin wrapper
that sets the model's branch, make target and banner, then calls the shared
engine `_reaper_build_lib.sh`. Both variants (**MCP** and **noMCP**) are built by
default; NAND only.

**This is also the compile check.** There is no faster one that means anything:
`make clean` is unusable on this tree, and a syntax check on a hunk does not link.
If C changed, a build is how you find out whether it compiles. Expect ~25–30
minutes for both variants on the maintainer's box.

Every build ends with the packaging gate, `reaper_verify.sh` — ARM ELF checks,
library link closure, Samba consistency, MCP-vs-noMCP purity, dictionary lockstep
and quote safety, model identity read back out of the packed image, per-model
banner hash, the rung-critical patch markers, and the About page's provenance
stamp. A build that does not end in `VERIFY OK` did not pass, whatever else it
printed.

---

## Cutting

### `cut_rung.sh` — one branch

```bash
build-scripts/cut_rung.sh --version v2.7.8
```

Exports the commits since the previous rung as patches (doc hunks excluded),
normalises the author identity, checks the series is gapless, replays the
**whole** series onto the pinned upstream base to prove both the version and the
tree hash, writes the provenance entry, checks the rung against every sibling
overlay, moves `EXPECTED_VERSION` in the CI workflow, and re-runs the PII scan.

Use it directly only for a canon-only change you are deliberately **not** fanning
out to the other models.

### `cut_fleet.sh` — the golden path

```bash
build-scripts/cut_fleet.sh --version v2.7.8
```

The entry point for a release. It runs, in this order and no other:

1. **preflight** — canon on the right branch, clean, already carrying the version
   bump; the CI workflow writable; the documentation claims agreeing with the repo
   (see [Keeping the docs honest](#keeping-the-docs-honest)).
2. `cut_rung.sh`
3. **port** the rung onto all five sibling branches, committing on each
4. **then** regenerate and gate the identity overlays

**The order is not negotiable.** Regenerating an overlay *before* the port
produces a patch that silently reverts the rung on every sibling — and it applies
cleanly, so nothing downstream catches it. That is a real regression this project
shipped on 2026-08-10, and the ordering here is what prevents a repeat.

It never commits in the lean repo and never pushes anything, anywhere.

| Flag | Effect |
|---|---|
| `--skip-cut` | skip step 2 (the rung is already cut) |
| `--skip-port` | skip step 3 |
| `--skip-overlay` | skip step 4 |
| `--skip-doccheck` | skip the documentation gate in preflight |

### A test build — there is no "cut test build"

A test build is not a cut. **Never cut a rung to test something**: a cut pins the
version, the provenance and the CI, and unpicking one is real work. To test:

- **locally** — `build_<model>.sh` with no `ship` argument. Builds and verifies,
  copies nothing to the ladder.
- **in the clean room** — dispatch **Actions → Build firmware from source** with
  `publish` **unticked**. Builds every model × variant you ask for from the
  published series, uploads artifacts, publishes nothing. Publishing needs *two*
  gates: the branch must be `main` **and** `publish` must be ticked.

---

## Proving what shipped

| Command | Answers |
|---|---|
| `patch_count.sh <tree>` | How many patches is this tree? The single source of truth for the About page's count. `--verify <dir>` asserts tree and `patches/` agree. |
| `reaper_verify.sh MODEL VARIANT VERSION` | Does this staged image pass the packaging gate? Run automatically by every build. |
| `gen_provenance.sh <tree>` | Record this build's source-tree hashes and logs into `provenance/`. |
| `ci/check_overlays.py overlays` | Does every sibling overlay contain identity changes *only*? Run in CI before the build matrix, so a bad overlay costs seconds rather than twelve builds. |
| `refresh_manifest.py` | Point the on-router update check at the newest published release. **A manual publish does not do this** — skip it and routers keep reporting "up to date". |
| `sync_local_engine.sh [--check]` | Is the build box running the same engine as CI? Drift here shipped a broken IPSec stack for three weeks. |

---

## Keeping the docs honest

```bash
build-scripts/reaper_docs.py --check     # the gate: fails on a stale claim
build-scripts/reaper_docs.py --fix       # rewrite stale claims, bump stamps
build-scripts/reaper_docs.py --report    # what still needs a human
```

Documentation drifts on exactly five values — current version, published version,
patch count, model count, fleet job count — and the repo already knows all five.
Each doc carries a **Doc status** stamp, and individual live claims are tagged
with an HTML comment (`<!--@pubver-->`, `<!--@patchcount-->`, …) directly after
the value. `--check` compares only the tagged claims, so the historical version
numbers throughout the changelog and release notes are ignored by construction.

`--check` runs in `cut_fleet` preflight. It is deliberately forgiving: only a
genuine mismatch stops a cut. A missing script, a missing `python3`, an
unreadable input — anything else warns and carries on, because a release must
never be blocked by its own linter.

`--report` writes `provenance/logs/<version>/doc-worklist.json` at the end of a
cut: the docs whose stamp predates the rung, and the docs with no claim markers
yet. That is the list to work while a fleet build is running.

---

## What a fork can and cannot run

**You can run:** the clean-room build (Actions → *Build firmware from source*),
`reaper_docs.py`, `patch_count.sh`, `ci/check_overlays.py`, and every
verification in [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) — replaying the patch
series onto the pinned base and comparing tree hashes needs nothing but this
repository and upstream.

**You cannot run** the local builders or either cut script, because they need
things this repository deliberately does not contain: the multi-gigabyte vendor
tree with its proprietary Broadcom/ASUS blobs (not redistributable — see
[`README.proprietary`](README.proprietary)), and the per-model branches, which
live only in the maintainer's clone and its bare hub.

That split is the whole design: **CI can verify anything derivable from the
published inputs, but it cannot produce them.** What ships is provably what this
repo describes, without the repo having to carry a vendor tree it has no right to
redistribute.
