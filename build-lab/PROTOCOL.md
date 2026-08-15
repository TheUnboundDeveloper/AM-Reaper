# Measurement protocol

The standard this directory holds itself to, and the ledger of what has been
proven so far.

---

## Acceptance criteria

A change is promoted out of `build-lab/` only when an `ab_compare.sh` session
satisfies all three, in this order of importance.

### 1. Content equality — mandatory, non-negotiable

The **normalised** staged-filesystem digest must be identical between arms, per
variant, in every replicate, **and** no file may differ between arms that does
not also differ between two builds of identical configuration.

Normalised, not raw: this build is not bit-reproducible and never has been.
Five staged files differ between *any* two builds of identical source — three
literal timestamps, one unsorted `depmod` output, and one binary carrying a
compiled-in build stamp. They are listed with their evidence in
`nondeterministic.txt`. The first session here failed on exactly this: the gate
demanded bit-equality, and the two *baseline* builds could not satisfy it
either. A gate no correct build can pass is broken, not strict.

The second half of the criterion is what keeps the first half honest. Excluding
paths shrinks what the proof covers, so the measured noise floor — the warm-up
against arm A, same configuration — is compared against the candidate's
difference set independently of any digest. That is why the warm-up is a
control and not a throwaway.

This is first because it is the criterion that catches the failure mode this
project actually experiences. Every silent-divergence defect on record —
libtool emitting no link command, a stripped Thai dictionary, a strongswan
configure that never re-ran and cost three weeks of a missing IPSec stack — was
a build that **passed every gate it had**. `reaper_verify` inspects proxies:
line counts, file presence, banner hashes. A dictionary can lose 5,565 of its
5,579 non-ASCII lines with the line count unchanged. A digest cannot miss that.

If the digests differ, stop. Do not read the timing; a faster build that
produces different output is not a faster build of the same thing.

### 2. QA gate clean

`reaper_verify` reports zero FAIL in every run, both arms. WARN counts should
match between arms; a new WARN is not a blocker but is worth reading before
promoting.

### 3. Faster in every replicate

Not faster on average, and not faster in the best run. A change that wins once
and loses once has not been demonstrated. The aggregate is reported for
context only.

---

## Controls, and what they are controlling for

**The warm-up build is discarded.** The tree state after any completed build is
the steady state. The first build after a source edit, a branch change or an
idle stretch is not, and comparing against it measures the history rather than
the change.

**Arms alternate A B A B.** Each build leaves the tree warmer than it found it,
so a fixed A A B B order systematically flatters whichever arm runs second.
Alternation spreads any residual drift across both arms.

**One flag per session.** `ab_compare.sh` takes a single `--compare` target.
Two changes measured together produce a number attributable to neither, and if
the digests differ there is no way to tell which change did it.

**The baseline arm is the canonical engine's behaviour, not a lab default.**
`run.env` records the sha256 of both `_reaper_build_lib.lab.sh` and
`build-scripts/_reaper_build_lib.sh`. If the canonical file changes, prior
results describe a baseline that no longer exists and the session should be
re-run.

**Nothing is measured while anything else runs.** Pre-flight refuses to start
when a build is already in flight against the tree. Two concurrent makes in one
tree do not merely contend for CPU; they interleave writes into shared staging
directories, and the result is an image with an indeterminate mixture that
still passes the gate.

---

## Known confounds not controlled for

Recorded honestly, because a protocol that claims to control everything is
usually hiding something.

- **Host load.** The measurements run on the same box the owner uses. A build
  competing with a browser or another VM is slower for reasons unrelated to the
  change. `run.env` captures nproc and RAM but not contemporaneous load. If a
  replicate looks anomalous, re-run rather than averaging it away.
- **Windows Defender and drvfs.** Two host-side changes cut the build 28% in a
  single day (Defender exclusions on `C:\wsl\focal`, and
  `appendWindowsPath=false`). Any host-level change of that kind invalidates
  comparison against earlier sessions. Timings are only comparable *within* a
  session.
- **Only RT-BE96U is measured by default.** The single-model blind spot has bitten
  this project twice — a default that is accidentally correct for BE96U silently
  wins for the other four. Before promoting anything that touches the model
  profile or the config invalidation, run at least one sibling.
- **A warm tree is not a cold tree.** Every result here describes the local
  iteration case. CI builds cold, so a local win does not transfer, and the
  single-pass change is designed to be inert there by construction. Do not
  quote a lab number as a CI expectation.

---

## Running a session

```sh
LAB=/mnt/c/Users/<you>/AppData/Roaming/VSC/ASUS/ASUS-Merlin-Reaper/build-lab

# 0. Confirm the harness and the tree agree, building nothing.
bash "$LAB/lab_build.sh" --model RT-BE96U --variants MCP --dry-run

# 1. The L2 measurement. 5 builds, roughly 45 minutes.
bash "$LAB/ab_compare.sh" --model RT-BE96U --variants MCP --repeat 2

# 2. Only after L2 is settled, and on its own:
bash "$LAB/ab_compare.sh" --model RT-BE96U --variants MCP --repeat 2 \
     --compare config-keep --base-single-pass auto
```

Launch through the background task runner, as `reaper`, from a script on disk —
not inlined. WSL reaps children the moment `wsl.exe` returns, so a detached
launch never actually runs.

Do not touch the tree while a session is in flight. Make reads the working tree
live, and a source edit landing mid-build produces an image containing an
indeterminate mixture of before and after.

---

## Results ledger

One row per completed session. A change may not be promoted without a row here
whose verdict is PROMOTE.

| date | experiment | model | variants | digest equal | verify | A (s) | B (s) | delta | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 2026-08-15 | single-pass (L2) | RT-BE96U | MCP | yes, normalised (3328/3333 identical) | 20/20 ×3 | 724 | 388 | **−46%** | **PROMOTE** (warm tree, 1 replicate) |
| 2026-08-15 | config-keep (L4) | RT-BE96U | MCP + noMCP | yes, both variants | 20/20 ×6 | 779 | 781 | **+0.3%** | **REJECT — no gain** |

**L2** — session `ab-20260815-155150-RT-BE96U-single-pass`. Candidate ran first
(`--order BA`) so the figure is conservative. Cold-tree path not exercised; the
two-pass fallback there is correct by construction, not by evidence.

**L4 — HYPOTHESIS REFUTED, do not re-test without a new reason.** Session
`ab-20260815-163332-RT-BE96U-config-keep`. The predicate fired correctly on both
variants (`config-keep: .config already declares BUILD_NAME=RT-BE96U`), output was
equivalent for both MCP and noMCP, and the time was **identical within noise**
(779s vs 781s; the warm-up was 776s, so the whole spread is 5s).

The hypothesis was that the second variant costs a full pass because deleting
`.config` forces a config regeneration. **It does not.** Preserving a
model-matching `.config` changes nothing measurable. The second variant's ~6:10
is therefore spent in tree traversal, rootfs re-staging and image repackaging —
not in configuration. That redirects the remaining local work away from config
invalidation and toward the packaging tail (L6 and the `configure` re-runs).

Kept in the harness anyway, defaulted off: it is content-proven, and it makes the
model-switch protection precise rather than blunt. That is a correctness argument,
not a performance one, and it does not justify promotion on its own.

**L2 replicated as a side effect.** All six variant builds in the L4 session ran
single-pass and skipped pass 2 correctly, at 367–373s each. Two variants =
779s ≈ 13:00, which matches the 13:00 projected from the L2 session exactly.

### Baseline expectations, for comparison when the first session lands

From the five most recent rungs on the canon tree, two variants, warm:

| rung | MCP p1 | MCP p2 | noMCP p1 | noMCP p2 | total |
|---|---|---|---|---|---|
| v2.3.8 | 8:47 | 7:38 | 8:34 | 7:39 | 32:40 |
| v2.3.9 | 8:53 | 7:44 | 8:34 | 7:49 | 33:03 |
| v2.4.1 | 6:16 | 5:39 | 6:04 | 5:49 | 23:50 |
| v2.4.3 | 6:24 | 6:00 | 6:07 | 5:53 | 24:43 |
| v2.4.4 | 6:25 | 5:49 | 6:12 | 5:48 | 24:17 |

`pass1_exit=0` in all five. The v2.3.x rungs predate the host-side Defender and
PATH changes, which is the step down to the v2.4.x range — a reminder that
cross-session timing comparison is not valid.

**Predicted single-variant result:** A ≈ 12:15, B ≈ 6:25. The prediction is
recorded before the measurement deliberately. If B lands far below ~6:00,
suspect that pass 1 did less work than the baseline's pass 1 rather than
celebrating — and go look at the digest.
