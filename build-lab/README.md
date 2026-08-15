# build-lab — measurement harness for build-pipeline changes

A staging area for build-system experiments. Nothing in here is on the release
path, nothing in here is sourced by a real build, and nothing in here may be
promoted into `build-scripts/` until it has a recorded A/B result in
`RESULTS/` showing **identical staged-filesystem output** and a real time saving.

The rule this directory exists to enforce: *no change to the live build
environment without documented proof of its benefit.*

---

## What is here

| File | Role |
|---|---|
| `lab_env.sh` | Path resolution and the safety assertions every lab run must pass |
| `_reaper_build_lib.lab.sh` | The experimental build engine. A copy of `build-scripts/_reaper_build_lib.sh` with each proposed change behind a flag that **defaults to current behaviour** |
| `lab_build.sh` | Launcher — one model, chosen variants, no ship, logs into `RESULTS/` |
| `stagedfs_digest.sh` | Staged-rootfs digest, byte-identical in method to the one `ci/container_build.sh` already computes |
| `ab_compare.sh` | The A/B harness. Runs baseline and candidate alternately, captures evidence, writes a verdict |
| `PROTOCOL.md` | The measurement protocol and the acceptance criteria a change must clear |
| `RESULTS/` | Evidence. One directory per A/B session; this is the "documented proof" |

## What it does not do

- **Never ships.** `SHIP_DIR` is refused, not ignored. No lab build can reach the ladder.
- **Never writes `/home/reaper/build_*.log`.** Real build logs are untouched; lab logs live in `RESULTS/`.
- **Never edits firmware source.** It builds the tree as it stands.
- **Never modifies `build-scripts/` or `/home/reaper/reaper_build/`.** The live engines stay exactly as they are until a change is proven.

## What it unavoidably touches

There is one buildable tree, so a lab build does use it, and a build is not a
read-only operation. Specifically it regenerates `.config` and the model
profile, rewrites `targets/96813GW/fs`, and overwrites `targets/96813GW/*.pkgtb`
for the version currently in `version.conf`. That is the same footprint any
normal build has. Two protections are added on top of the live engine:

- **`config_base` and `version.conf` are asserted clean before the run and
  restored on every exit path**, including Ctrl-C and a kill. The live engine
  only restores at the end, which is why an aborted build currently leaves the
  noMCP flip in place and the next build silently produces a mislabelled image.
- **Single-variant runs never perform the noMCP flip at all**, so the most
  common lab run cannot reach that failure mode.

Preserved ladder images in `reaper-firmware/` are never touched — the lab has
no ship step to touch them with.

---

## Running it

From WSL, as `reaper` (never root):

```sh
LAB=/mnt/c/Users/<you>/AppData/Roaming/VSC/ASUS/ASUS-Merlin-Reaper/build-lab

# One baseline build, current behaviour, single variant. Proves the harness works.
bash "$LAB/lab_build.sh" --model RT-BE96U --variants MCP

# The measurement that matters: baseline vs single-pass, two replicates each.
bash "$LAB/ab_compare.sh" --model RT-BE96U --variants MCP --repeat 2
```

`ab_compare.sh` with the defaults runs five builds (one discarded warm-up, then
baseline/candidate twice each). At roughly 6–12 minutes per build that is about
45 minutes. Budget for it; the warm-up is not optional, because the first build
after any source change is not comparable to the ones after it.

Launch it the way the build SOP requires — through the background task runner,
as `reaper`, with the script on disk rather than inlined:

```
wsl -d Ubuntu-20.04 -u reaper bash /mnt/c/.../build-lab/ab_compare.sh ...
```

---

## The experiments, and what each is trying to prove

Each maps to an item in the build-throughput plan.

### `LAB_SINGLE_PASS` — plan item L2

**Claim.** Pass 2 is redundant on a warm tree. Pass 1 has returned 0 on every
recent rung, meaning it completed and produced the image; pass 2 then rebuilds
what already exists.

**Mechanism.** After pass 1: if it returned 0, *and* the expected `.pkgtb`
exists, *and* that file is newer than the pass-1 start time, skip pass 2. Any
other outcome runs pass 2 exactly as today. A cold tree keeps both passes
automatically, because there pass 1 genuinely dies at `setprofile` — which is
the CI case, so CI behaviour is unchanged by construction.

**Values.** `off` (default, baseline) · `auto` (the candidate) · `force` (skip
pass 2 unconditionally — diagnostic only, never a shipping mode).

**Proof required.** Staged-fs digest identical to the baseline arm, in both
replicates.

### `LAB_CONFIG_KEEP` — plan item L4

**Claim.** The unconditional `rm .config config_<target>` at the top of every
variant forces a config regeneration whose only purpose is protecting against a
model switch, and it can be made conditional without losing that protection.

**Mechanism.** Delete only when the existing profile is absent or names a
different model. Otherwise leave it and let make decide.

**Sequencing.** Measure this *after* L2 has landed, on its own. Turning both on
in one run makes the two effects inseparable, and this one touches the
MODEL NAME MISMATCH guard, which is the more delicate of the two.

**Proof required.** Digest equality, plus an explicit model-switch test: build
RT-BE96U, then a sibling, and confirm the profile regenerates.

### `LAB_VARIANTS` — plan item L3

Not an experiment, a convenience. Dev iteration does not need a noMCP image;
building one costs a second full pass. Setting a single variant is what makes an
iteration build ~6 minutes instead of ~24.

A single-variant build is a **development artifact only**. `lab_build.sh` stamps
every log and result with the variant set, and refuses to write a
`SHIP-CANDIDATE` marker for any incomplete set, so a dev image cannot be
mistaken for a release one later.

### Phase timing — plan item C0 (local half)

Always on, no behaviour change. Every run emits machine-readable lines:

```
[lab-timing] variant=MCP phase=pass1 seconds=385 rc=0
[lab-timing] variant=MCP phase=pass2 seconds=349 rc=0 skipped=no
```

These are what `ab_compare.sh` parses. The same treatment is owed to
`ci/container_build.sh`, where 77 of 80 minutes are currently unmeasured, but
that is a separate change to a file this directory does not touch.

---

## Promotion

A change leaves this directory only when `RESULTS/` contains a session where:

1. the staged-fs digests of both arms are identical, in every replicate;
2. `reaper_verify` reports no new FAIL and the same check count;
3. the timing improvement holds in both replicates, not just the best one;
4. the result has been read by the owner.

Then, and only then, the change is ported into `build-scripts/_reaper_build_lib.sh`
— **and only there.** The local copy at `/home/reaper/reaper_build/` is a
divergent fork of that file (plan item L1); converging the two is a prerequisite
for promotion, not an afterthought, or the change reaches only one of the two
engines that currently alternate between rungs.

Never push. The owner commits.
