# Port plan — GT-BE19000 · ZenWiFi BQ16 · ZenWiFi BQ16 Pro

*Drafted 2026-08-24 for owner review. Investigation is code/history-verified against the canonical
tree (`/home/reaper/asuswrt-be96u`, branch `be96u-only`); no code was changed. This is a plan only.*

---

## TL;DR verdict

**All three are BCM4916 / 6813 — confirmed, you were right.** They are NOT buildable from the current
tree, but there is **no fundamental barrier** to bringing them in: it is the same job already done for
GT-BE98 (a Tier-B, GPL-drop port). The single hard prerequisite is **an ASUS GPL source drop per
model**, which only you can obtain — their proprietary blobs and even their build stanza are absent
from the tree and its entire git history. It is **feasible but blocked on those drops**, and it is a
**significant per-model effort with a real safety caveat** (no hardware to validate radio bring-up).

- **GT-BE19000** — tri-band, BE96U-identical radio order → the easy one (RT-BE92U-class effort + a GPL drop).
- **BQ16 / BQ16 Pro** — quad-band **mesh** systems → GT-BE98-class effort (radio-order UI gates) **plus**
  mesh-node considerations.

Recommended: do **GT-BE19000 first**, prove the Tier-B-from-GPL pipeline on the low-risk one, then the
two BQ16 mesh SKUs. **Do not flash any of them on real hardware without a tester on that exact model** —
see Safety.

---

## What is present vs. absent (verified)

| Layer | GT-BE19000 | BQ16 | BQ16 Pro | Source of truth |
|---|---|---|---|---|
| `*_CHIP_PROFILE=6813` (BCM4916) | ✅ | ✅ | ✅ | `chip_profile.mak:46,47,59` |
| `model.c` enum (`MODEL_*`) | ✅ | ✅ | ✅ | `shared/model.c:233,235,240` |
| Radio/band table entry | ✅ | ✅ | ✅ | `shared/wlif_utils_ax.c:5095,5117,5125` |
| **target.mak build stanza** | ❌ | ❌ | ❌ | absent in current tree **and** in `48b0698465^` |
| **Platform `router-sysdep.<model>`** | ❌ | ❌ | ❌ | **0 commits in all history** |
| **Bootloader `obj.<model>`** | ❌ | ❌ | ❌ | **0 commits in all history** |
| **Userspace prebuild dirs** | ❌ | ❌ | ❌ | **0 commits in all history** |
| **Dongle firmware `dongle/sysdeps/<model>`** | ❌ | ❌ | ❌ | **0 commits in all history** |
| `www/sysdep` model art | ❌ | ❌ | ❌ | not in tree |

**Key distinction from the existing siblings.** RT-BE86U/88U/GT-BE98_PRO/RT-BE58_GO/RT-BE92U were
*stripped* by commit `48b0698465` and are **git-restorable** from its parent (the pinned CI base
`a7ebfa133a` still carries their `router-sysdep`). These three were **never in the repo at all** — the
strip commit does not touch them, and the pinned base carries `router-sysdep` for
`gt-be98_pro / rt-be58_go / rt-be86u / rt-be88u / rt-be92u / rt-be96u` **only**. So there is nothing to
restore; the blobs must come from **outside** the repo. This is exactly the GT-BE98 (non-Pro) situation,
which was solved with a gnuton fork drop + ASUS GPL `102_39274`.

---

## Per-model characterization

### GT-BE19000 (ROG Rapture) — LOWEST RISK
- **Tri-band**, radio order `"2 1 0 -1"` = **identical to RT-BE96U** (2.4 / 5 / 6). Grouped with
  `MODEL_RTBE96U`/`RTBE92U` in the radio table.
- Consequence: **no `Tools_Sysinfo.asp` `based_modelid` gate and no dashboard radio-count change** are
  needed — it behaves like BE96U on the UI side, the same happy case as RT-BE92U.
- Distinct SKU note: `GT-BE19000AI` also exists (6813, its own enum/profile) — **not in scope**, but it
  would ride the identical path if ever wanted.

### ZenWiFi BQ16 — quad-band mesh
- Radio table `"2 1 0 -1"`, annotated `(5562) 5G_L + 5G_H + 6G` — a **quad-band** SKU (dual-5G + 6G +
  2.4). The band mapping must be **verified on the GPL drop's config** before trusting the dashboard.
- Sold as a **mesh system** (router + node(s) run the same image) → AiMesh backhaul / DWB / onboarding
  are first-class, not incidental.

### ZenWiFi BQ16 Pro — quad-band mesh, dual-6G
- Radio table `"1 0 2 -1"`, annotated `(5662) 5G + 6G_L + 6G_H` — quad-band with **dual 6 GHz**.
- Different radio order → **needs the `Tools_Sysinfo.asp` `based_modelid` quad-band remap** in the three
  gates (client counts / temperatures / driver rows), exactly like GT-BE98/GT-BE98_PRO. Grep
  `based_modelid ===` in shared `www` when adding it.
- Also a **mesh system**.

---

## Is it safe to bring them in?

**Yes to attempt, with one firm gate.** Nothing here is architecturally unsafe — it is the proven
GT-BE98 pipeline. The real risk is **shipping an image we cannot validate**:

1. **`rc/broadcom.o` is model-specific board/radio bring-up and must come from THIS model's own GPL
   drop — never cross-flashed.** The v1.5.0e GT-BE98 field failure (3-of-4 radios, no 6 GHz, empty
   client list) was caused by linking GT-BE98_PRO's closed objects into the non-Pro. Same closed
   objects here: `rc/broadcom.o`, `rc/private.o`, `shared/spwenc.o`, `shared/nvpriv.o`. Getting these
   from the wrong SKU bricks radios. **This is the #1 safety rule for all three.**
2. **No target hardware = build-validation only.** We can build and pass `reaper_verify`, but that
   proves the image is *well-formed*, not that radios come up. On a quad-band/mesh box the failure mode
   is exactly the GT-BE98 one. **Do not publish any of these without a tester on that exact SKU** who
   can confirm all radios, 6 GHz, WAN, and (for BQ16) mesh backhaul on metal — mirroring the GT-BE98
   hold-until-field-data discipline.
3. **Mesh bricking is worse than router bricking** (BQ16/Pro): a node with no console, possibly
   physically inaccessible, is the higher-stakes case. Treat BQ16 flashes as node-aware.
4. **ABI/prebuilt skew** (the GT-BE98 `networkmap` empty-client-list bug): whenever a GPL drop's
   userspace prebuild is older than the in-tree 39995-level source it links against, expect SHM/struct
   skew. Budget a per-model prebuild-vs-source audit.

**Conclusion:** safe to develop and build-validate now (given the GPL drops); **not safe to ship
without per-SKU metal validation.** That is a hold condition, not a blocker to starting.

---

## The hard prerequisite (blocker)

**An ASUS GPL source drop per model** — e.g. `GPL_GT-BE19000_3.0.0.6.102_<build>.tgz`,
`GPL_BQ16_…`, `GPL_BQ16_PRO_…` (or a gnuton fork branch carrying them, as used for GT-BE98). Each drop
supplies the four missing layers: platform `router-sysdep.<model>`, bootloader `obj.<model>` (+ any
`RTL_OBJS.o`-class untracked blobs — see the CI defect-4 lesson), userspace prebuilds, and dongle
`rtecdc.bin`. **Without the drops, none of these can be built** — this is the entire gate. You have
sourced per-SKU GPL drops before; that is the action that unblocks this plan.

---

## Port recipe (per model) — the GT-BE98 Tier-B pattern

Once a model's GPL drop is in hand, per model:

1. **Branch + worktree** off canon: `git branch <model> hub/be96u-only`; `git worktree add
   /home/reaper/port/<model> <model>` (the current sibling mechanism; drive with `REAPER_TREE`).
2. **Author the `target.mak` stanza** — this is net-new for these three. Copy the BE96U shape:
   `export <MODEL> := $(HND-96813_BASE)` + `BUILD_NAME`, `EXT_PHY`, `NVSIZE`, `DHDAP`, band flags
   (`HAS_6G=y`, `QUADBAND` for BQ16/Pro), `IPV6SUPP`, `HTTPS`, `ARM`, the **8 de-cloud tokens off**
   (`BWDPI NATNL_AICLOUD ALEXA NATNL_AIHOME UUPLUGIN ASD GOOGLE_ASST GEARUPPLUGIN =n`), and
   `SAMBA4=y SAMBA3=`. Verify generated `config_<model>` after (RouterOptions maps tokens → RTCONFIG).
3. **Import the GPL blobs** into the worktree: `router-sysdep.<model>`, `bootloaders/obj.<model>`,
   userspace prebuilds, dongle `rtecdc.bin`. Keep the four closed objects (`rc/broadcom.o`,
   `rc/private.o`, `shared/spwenc.o`, `shared/nvpriv.o`) **from this model only**.
4. **`reaper_chanlist_shim.c`** if the drop's blobs predate the in-tree helpers (the GT-BE98 case:
   `wl_scb`, `backup_eth_ob_log`, `is_wan_port_ext_switch` stubs).
5. **Reaper feature sync** via `port_sibling_v2.sh <MODEL>` (overlays the full be96u-only shared diff,
   protects per-model identity) + the dict supplement (`[A-Z][A-Z].dict`, never `*.dict`).
6. **Per-model identity:** banner PNG (owner art or a placeholder like RT-BE92U got), `version.conf`,
   productid/CFE board-id/odmpid. **BQ16 Pro only:** add the `based_modelid` quad-band gate to
   `Tools_Sysinfo.asp` (3 places).
7. **Bootloader gates:** grep `bcmbca/Makefile` `ifeq ($(or $(MODEL)…))` for RTL8372/switch tokens the
   new model needs (the RT-BE86U `$(RTBE86U)` / RT-BE92U `$(RTBE92U)` lesson); stage any untracked
   u-boot blob the Makefile enables.
8. **Build** (`build_<model>.sh`, `-u reaper`, cold-worktree libtool + qemu-binfmt pins) → `reaper_verify`.
9. **CI wiring** (once green locally): `overlays/<MODEL>.patch`, `check_overlays.py MODEL_BANNER`,
   `container_build.sh` branch/UB_SYM/PROFILE, `build_one.sh`, `public-build.yml` matrix, `cut_fleet.sh`
   MODELS, `_port_protect`. Publish as **prerelease** until metal-validated (the BE92U convention).
10. **HOLD publication** until a per-SKU tester confirms radios/6 GHz/WAN/mesh on metal.

---

## Recommended sequence & effort

1. **GT-BE19000** first — tri-band, BE96U radio order, no UI gate. Proves the "author the target.mak
   stanza + import a fresh GPL drop" path on the lowest-risk SKU. Effort ≈ RT-BE92U + a GPL drop.
2. **BQ16**, then **BQ16 Pro** — quad-band mesh; add radio-order handling (Pro) and mesh-node
   validation. Effort ≈ GT-BE98 each, plus mesh.

**Blocking dependency for all three:** the ASUS GPL drops. **Shipping dependency:** a metal tester per
SKU. Until both, this stays build-validation-only.

---

## One-line answer to "is there a safe way in?"

Yes — via the established GT-BE98 GPL-drop pipeline, all three being confirmed BCM4916 — but it cannot
start until you supply a per-model ASUS GPL drop, and it cannot ship until each SKU is validated on real
hardware. It is blocked-on-inputs, not impossible.
