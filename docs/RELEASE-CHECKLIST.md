# Release Checklist — local rung → published firmware

Work top to bottom. Every box is something that has broken a release at least
once when skipped.

`RELEASE-PROCESS.md` explains *why* each step exists; this file is the running
order. Replace `vX.Y.Z` throughout with the version you are cutting.

**The split to keep in your head:** everything in phases 1–5 needs the firmware
source, so it can only happen locally. Everything from phase 6 needs only the
published inputs (`patches/` + `overlays/`), which is why CI can do it. The
sibling port sits firmly in the first group — it needs canon *and* the four
sibling branches at once, and neither is on GitHub.

---

## Phase 1 — Preconditions

- [ ] Canon clone is on `be96u-only` with **no uncommitted tracked changes**
      `git -C /home/reaper/asuswrt-be96u status --short --untracked-files=no`
- [ ] The rung is **already committed on canon**, including the `version.conf`
      bump — `EXTENDNO=Reaper_vX.Y.Z`. `cut_fleet.sh` refuses to run otherwise.
- [ ] The previous rung's sibling commits are **in the hub** (phase 5 of last
      time). If they are not, phase 2 aborts on the ancestry check.
- [ ] `.github/workflows/public-build.yml` is **writable** — a stray Windows
      read-only attribute makes the `EXPECTED_VERSION` pin fail silently.
      `cut_fleet.sh` checks this in preflight.

---

## Phase 2 — Cut the rung and port the fleet (local, one command)

```bash
wsl -d Ubuntu-20.04 -u reaper -- \
  bash /mnt/c/Users/natha/AppData/Roaming/VSC/ASUS/ASUS-Merlin-Reaper/build-scripts/cut_fleet.sh \
  --version vX.Y.Z
```

This runs, in the only safe order: `cut_rung.sh` → port the four siblings →
**then** the overlays. Order is not negotiable — regenerating overlays before
the port writes an overlay that *reverts* the rung on every sibling, and it
applies cleanly, so nothing downstream would catch it.

- [ ] Patch count went up by the number of commits in the rung, and the series
      is **gapless**
- [ ] The full-series **replay passed** — `EXTENDNO` matches and the only diff
      vs canon HEAD is `*.md`
- [ ] All four ports report **`post-commit parity: 0 unsynced shared files`**
- [ ] Dicts committed per model and **lockstep** (one line count across all 25)
- [ ] The **overlay identity gate passes** at the end

If the gate fails, it names the file and the offending line. It almost always
means canon moved and a sibling branch did not — re-run the port, do not hand-edit
the overlay.

---

## Phase 3 — Write the prose (local, not automatable)

- [ ] `provenance/manifest.json` → this release's **`summary`** (what changed and
      why, in prose) and **`models_note`** (fleet/port status)
- [ ] `docs/CHANGELOG.md` → a `## vX.Y.Z — <headline>` section

> **Release notes are extracted from the changelog.** A missing section ships a
> release with no notes, and the router's "what's new" box falls back to a bare
> link. Bullets must be `- **Headline.** body` — that shape is what the on-router
> note builder parses.

- [ ] If you edit `manifest.json` with a script, write it in **binary mode with
      LF**. Windows text mode flips the whole file to CRLF and turns a 7-line
      edit into a 961-line diff.

---

## Phase 4 — Review

- [ ] `git diff` and `git status` in the lean repo — expect: new `patches/`,
      `provenance/manifest.json`, `docs/CHANGELOG.md`, and `public-build.yml`
      only if the version pin moved
- [ ] Overlays: **unchanged is the normal, correct outcome.** After a port,
      `diff(canon, sibling)` is back to pure identity. `cut_fleet.sh` skips a
      rewrite when only `index` blob-hash lines differ — CI applies overlays
      without `--3way`, so those hashes are never read, and rewriting would add
      megabytes of blobs for no behavioural change.

---

## Phase 5 — Commit the lean repo

- [ ] Commit. Keep the five coupled artifacts **in one commit**: `patches/`,
      `EXPECTED_VERSION`, `provenance/manifest.json`, `overlays/*` (if they
      genuinely changed), `.github/pii-allowlist.txt` (paths are position-matched,
      so any renumber invalidates it).

---

## Phase 6 — Push the hub (local, easy to forget)

```bash
git -C /home/reaper/asuswrt-be96u push hub \
  be96u-only rt-be86u rt-be88u gt-be98 gt-be98-pro
```

- [ ] Canon **and all four ported branches** are in the bare hub

> Not optional any more. `cut_fleet.sh` force-moves each local sibling ref onto
> `hub/<branch>` after proving the local is an ancestor. If this rung's sibling
> commits never reach the hub, next time local is *ahead* of hub, the ancestry
> check fails, and the script stops with "resolve by hand". It fails safe rather
> than losing work — but it will block the next rung.

---

## Phase 7 — Push the lean repo

Choose one:

- [ ] **Via PR into `main`** (recommended for any rung touching `patches/`) —
      this is the only way `patch-apply-check` and `verify-provenance` run.
- [ ] **Straight to `main`** — faster, but runs **only `repo-hygiene`**. Both
      other checks are pull-request gated on `patches/**` and
      `provenance/manifest.json`. Pushing a rung directly silently skips them;
      dispatch them manually if you go this route.

- [ ] The push is green

---

## Phase 8 — Build (remote)

**Actions → Public build → Run workflow**

- [ ] `model` = the model, or `all` for the fleet (`all` × `both` = 10 jobs,
      ~1.5 h each)
- [ ] `variant` = `both`
- [ ] `version` = **blank** — blank uses the pin. Fill it only to override
      deliberately; the pin is where the version lives.
- [ ] `publish` = **unchecked** for this first run

Publishing needs **two** gates: the branch must be `main` **and** `publish` must
be ticked. So a dispatch on main with the box clear builds and verifies without
shipping anything.

Watch for:

- [ ] **Overlay identity gate** passes (seconds, before the matrix — it gates the
      build, so a bad overlay costs seconds instead of 10 × 1.5 h)
- [ ] `EXPECTED_VERSION` assertion passes after the series applies
- [ ] Series tree matches `provenance/manifest.json`
- [ ] Packaging/verify gate passes for every model × variant

---

## Phase 9 — Metal (nothing above proves a router boots)

- [ ] Flash **one** image on the primary model before fanning out
- [ ] Boot, sign in, dashboard renders
- [ ] Factory-reset path if the rung touched first-boot, QIS, or nvram defaults
- [ ] Anything the rung specifically changed

---

## Phase 10 — Publish

- [ ] Re-dispatch `public-build.yml` from `main` with **`publish` ticked**

  *or*, to ship a build you already have green without rebuilding:

- [ ] Dispatch `release.yml` with **Use workflow from = `main`**, the tag as an
      input, and the green build's **`run_id`** (artifacts are kept 30 days)

> **Trap:** a manual `release.yml` dispatch does **not** trigger
> `refresh_manifest`. The Release exists, but routers keep seeing the old version
> on their update check until you run `build-scripts/refresh_manifest.py`. This
> shipped v2.3.2 while the manifest still advertised v2.3.1.

> **Trap:** GitHub's *re-run* buttons replay the workflow file from the run's
> original commit, so a workflow fix will not apply. Use a fresh
> `workflow_dispatch` from `main`.

---

## Phase 11 — Verify the published result

- [ ] One Release per model, assets attached, checksums present
- [ ] `updates/manifest_3006.txt` advertises the new version
- [ ] A release asset actually downloads (that is the router's update path)
- [ ] Router → Firmware Upgrade → Check sees it
      (the on-router note is cached in `/tmp/release_note0.txt` and Check does
      not force a re-fetch — `rm -f` it and reload)

---

## If it goes wrong

| Symptom | Cause / fix |
|---|---|
| Overlay gate fails naming a `www` file | Canon moved, sibling did not. Re-run the port, then re-run `cut_fleet.sh`. Never hand-edit the overlay. |
| Phase 1 aborts "not an ancestor" | Phase 5 was skipped last time — push the branches to the hub, or reconcile by hand. |
| Build aborts on the version assertion | The pin and the series disagree. The series sets `EXTENDNO`; fix the pin, not the series. |
| `repo-hygiene` PII hit inside `patches/` | Fix the **source commit message** and re-export. Do not add the path to the allowlist. |
| Wrong firmware published | Cut a point release (`vX.Y.Za`). Moving a tag works but point releases are safer. |
| Assets missing from a Release | Re-dispatch `release.yml` with the tag — it re-uploads with `--clobber`. |

---

## What is deliberately *not* automated

- **The port** — needs canon and the sibling branches simultaneously; neither is
  on GitHub, so CI can never do it.
- **The prose** — summary, `models_note`, changelog.
- **Metal validation.**
- **The decompose-and-diff cross-check** (CI image vs local image). It is the
  only check that has ever caught container-only divergence; a passing
  `reaper_verify` missed both the dictionary damage and the strongswan defect.
