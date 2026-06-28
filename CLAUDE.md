# CLAUDE.md — Asuswrt-Merlin (RT-BE96U focus)

Guidance for Claude Code when working in this repository.

## What this is

A checkout of **Asuswrt-Merlin** (`asuswrt-merlin.ng`, upstream `RMerl/asuswrt-merlin.ng`) — enhanced firmware for ASUS routers, based on Asus's GPL Asuswrt source. This is a large Broadcom-based embedded-Linux firmware monorepo (~75k files, multi-GB `.git`).

**Project goal:** focus this codebase exclusively on the **ASUS RT-BE96U** (the owner's router, WiFi 7 / Broadcom BCM4916) and improve its firmware. Target firmware line: **3006.102.\*** (checked out at tag `3006.102.8-beta2`).

## Project Database (read this first)

Durable project knowledge lives in a **PostgreSQL "memory vault"**, reached via the `postgres` MCP server (load its tools with ToolSearch, e.g. `mcp__postgres__execute_sql`).

- Database: **`memory_vault`** (connected user `vault_rw`)
- This project's schema: **`proj_asus`** (registered in `vault.projects` under key `asus`)
- Memories table: **`proj_asus.memories`** — `id, type, title, body, tags text[], created_at, updated_at`. `type` ∈ `project | reference | feedback | user | note`.

Use it via the postgres MCP tools:
- **Recall on session start:** `SELECT type, title, body FROM proj_asus.memories ORDER BY id;`
- **Search:** `SELECT title, body FROM proj_asus.memories WHERE body ILIKE '%<term>%' OR tags && ARRAY['<tag>'];`
- **Add:** `INSERT INTO proj_asus.memories (type,title,body,tags) VALUES ('project','<title>',$$<body>$$, ARRAY['<tag>','src:<slug>']);`
- **Update:** `UPDATE proj_asus.memories SET body=$$<body>$$, updated_at=now() WHERE id=<id>;`

When you learn something durable about this project, write it to `proj_asus.memories` — don't duplicate it into this CLAUDE.md.

> The earlier file-based memory under `…\.claude\projects\…\memory\` has been migrated into Postgres and is superseded.

## Repository layout (blueprint)

Top level: `release/` (all firmware source), `tools/` (toolchains — not currently on disk), plus `README*`, `License`, `Changelog-3006.txt`.

`release/` contains per-**platform** source trees (each builds several router models that share kernel/drivers/userspace). Naming: `src-rt-<sdk>.<family>.<soc>` where `ax`/`axhnd` = WiFi 6, `behnd` = WiFi 7.

| Tree | Family | Notes |
|------|--------|-------|
| `src-rt-5.04behnd.4916` | **WiFi 7 (BE), BCM4916** | **Contains the RT-BE96U** and other BE models (GT-BE98_Pro, RT-BE58_GO, RT-BE86U, RT-BE88U, RT-BE92U). |
| `src-rt-5.04axhnd.675x` | WiFi 6 (AX) high-end | GT-AX11000_Pro, GT-AX6000, GT-AXE16000, RT-AX86U_Pro, … |
| `src-rt-5.02axhnd.675x` | WiFi 6 (AX) | RT-AX58U/82U/86U/68U, TUF/GS-AX, etc. (see `chip_profile.mak`). |
| `src-rt-5.02axhnd` | WiFi 6 (AX) | sibling AX tree. |
| `src-rt-5.02L.07p2axhnd` | WiFi 6 (AX) legacy | RT-AC68U_v4, RT-AX68U, RT-AX86U, GT-AXE11000. |
| `src-rt`, `src` | shared | Common source referenced by the platform trees via symlinks. |
| `image/` | — | `mklang.sh` and image helpers. |

Inside a platform tree, the build pieces are: `bcmdrivers/` (Broadcom drivers + WiFi dongle firmware), `kernel/`, `bootloaders/` (`obj.<model>/`, `build/configs/`), `router/` + `router-sysdep.<model>/` (userspace per model), `shared/`, `userspace/`, `hostTools/`, and model descriptors `chip_profile.mak` / `model-desc.mak` / `data-model/`. **A specific model is chosen at build time** (e.g. `make rt-be96u`) from these profiles — models are not standalone folders.

## RT-BE96U specifics

Built from `release/src-rt-5.04behnd.4916`. Model-specific paths: `router-sysdep.rt-be96u/`, `bootloaders/obj.rt-be96u/`, `bootloaders/build/configs/env_NAND_2M_RT-BE96U.conf`, `options_6813_nand.conf.RT-BE96U`, and dongle firmware `bcmdrivers/.../dongle/sysdeps/RT-BE96U/{6717a0,6726b0}/rtecdc.bin` (WiFi chips BCM6717 + BCM6726). See the `be96u-build-mapping` memory entry.

## Working copy (use this, not the Windows checkout)

The buildable tree is a **WSL clone**, where symlinks materialize correctly:

- WSL path: `/home/builder/asuswrt-be96u`  ·  from Windows: `\\wsl.localhost\Ubuntu\home\nathan\asuswrt-be96u`
- Branch **`be96u-only`** holds the sibling-strip commit (non-BE96U BE models removed; RT-BE96U + shared + AX trees kept) **plus the security-hardening commits**.
- **DO NOT push / write back to the repo.** `origin` points at this Windows `.git`; keep all work local to the WSL clone.

## Security hardening — the "reaper" build

This tree carries a hardened RT-BE96U build. **`REAPER-FIXES.md`** (repo root) is the authoritative fix list: 8 Critical, 12 High, 19 Medium, 5 Low + 4 internal IPsec fixes, all on `be96u-only`, all compile-verified with the real gcc-10.3 userspace toolchain. Full audit + fix-log detail lives in the `proj_asus.memories` "security audit & fix log" entry.

- **Custom version:** `BUILDREV` defaults to `-reaper` (`release/src-rt/Makefile`, reached via the per-platform `Makefile` symlink), so the version reads `…_beta2-reaper` and the image is `RT-BE96U_…_beta2-reaper.trx`. Passing `BUILDREV=` explicitly restores the stock `-g<hash>` behavior.
- **Deferred by decision** (do not "fix" without re-deciding): H15 default creds (forced first-boot setup is the mitigation, owner opted to keep), M20 keyless `enc_str`/`dec_str` (debug-only caller), M21 MAC-derived `generate_wireless_key` (dead code). See `REAPER-FIXES.md` and memory.
- **Build verify recipes** live in `/home/builder/*.sh` (`cc_one.sh` rc, `cc_shared.sh` shared, `cc_httpd.sh`, `warn_diff.sh`). web.c + libdisk are syntax-checked only (env-blocked full builds).

## Working notes / cautions

- **The Windows checkout (`c:\…\asuswrt-merlin.ng`) is now a synced reference mirror, not a build tree.** Its `be96u-only` branch is fetched + `reset --hard` from this WSL clone and requires a **non-cone sparse-checkout** (`.git/info/sparse-checkout` excludes `release/src/router/{ipset-6/tests,ipset-7.6/tests,udev/test}` — 254 colon-in-name paths illegal on NTFS). Symlinks render as text there (~138 perpetually "modified" files — ignore). **Build only in the WSL clone.** See the `windows-reference-mirror` memory entry.
- Asuswrt-Merlin relies heavily on **symlinks** → check out and build on **Linux or WSL**, not native Windows.
- **Removing "other routers" is surgical, not folder-per-model.** Follow the `strip-other-routers-plan` memory entry; do it on a branch and verify a BE96U build still completes. Don't delete shared trees, kernel, or core drivers.
- This is GPL firmware. **Project & contributor docs live in [`docs/`](docs/):** `docs/PROJECT.md` (collapsed overview), `docs/DEV-SETUP.md` (the hard-won WSL/gcc-10.3 build + edit + verify workflow — read before building). The retained upstream originals (`License`, `README.proprietary`, `Changelog-3006.txt`) now live in `docs/` alongside the project docs; the out-of-date upstream readmes were folded in and removed.
