# Reaper firmware build scripts

The reusable toolkit that builds the Reaper images correctly across all six
models (five on BCM4916, plus the newer BCM6765 RT-BE92U). Canonical build clone lives at `/home/reaper/asuswrt-be96u`
(WSL Ubuntu-20.04, user `reaper`); these scripts live at
`/home/reaper/reaper_build/` on the build box — this folder is the tracked copy.

## Models / branches

| Model         | git branch     | make target | BUILD_NAME    | bands            |
|---------------|----------------|-------------|---------------|------------------|
| RT-BE96U      | `be96u-only`   | `rt-be96u`  | RT-BE96U      | tri  (2.4/5/6)   |
| RT-BE86U      | `rt-be86u`     | `rt-be86u`  | RT-BE86U      | dual (2.4/5)     |
| RT-BE88U      | `rt-be88u`     | `rt-be88u`  | RT-BE88U      | dual (2.4/5)     |
| GT-BE98       | `gt-be98`      | `gt-be98`   | GT-BE98       | quad (2.4/5/5/6) |
| GT-BE98 Pro   | `gt-be98-pro`  | `gt-be98_pro` | GT-BE98_PRO | quad (2.4/5/5/6) |
| RT-BE92U      | `rt-be92u`     | `rt-be92u`  | RT-BE92U      | tri  (2.4/5/6)   |

BE96U is canonical. Siblings = the BE96U shared tree (full diff, **not** a
whitelist) + a small per-model identity overlay (banner, `target.mak` block,
`version.conf`, model-only www/blobs). The five BCM4916 models share PROFILE
`96813GW`; **RT-BE92U** (BCM6765) builds to PROFILE **`96765GW`** instead, in a
git worktree (`REAPER_TREE`/`REAPER_TDIR`), and is experimental — not yet in the
CI matrix. Every image is built in both **MCP** and **noMCP** variants; NAND-only.

## Files

| Script                  | Role                                                                 |
|-------------------------|----------------------------------------------------------------------|
| `_reaper_env.sh`        | Resolves the Windows-side paths generically (`WINUSER` / `WIN_ASUS_ROOT`) so ship/mockup paths aren't pinned to one developer's username. Sourced by every launcher + the port script. |
| `_reaper_build_lib.sh`  | Build engine. `reaper_build()` runs both variants (flips `RTCONFIG_REAPER_MCP` off + `_noMCP` EXTENDNO for the 2nd, restores after), passes `FORCE=1` on both make passes, and runs `reaper_verify.sh` after each variant — **blocks ship on gate FAIL**. Sourced by every `build_<model>.sh`. |
| `build_<model>.sh`      | Thin per-model launcher: sets BRANCH/TARGET/PREFIX/VARIANTS/SHIP_DIR then `source _reaper_build_lib.sh; reaper_build "$@"`. |
| `port_sibling_v2.sh`    | Guarded overlay port: syncs the full shared diff from `be96u-only`, protects the per-model identity overlay, and aborts on wrong branch / base / banner-sha / BUILD_NAME / band mismatch. `port_sibling_v2.sh <MODEL> [--commit] [--version V]` (default dry-run). **Note (2026-08-05):** the port and the verify gate now share one `_port_protect.sh` classifier; the port syncs everything under `sysdep/FUNCTION/` (the shared, flag-keyed VPN/MSWAN/SDN pages that used to be skipped) and **aborts if any shared file still differs from canon after the commit**, and `reaper_verify` fails the build on a shared-parity miss. The only remaining manual step is the **dict supplement** (dicts stay per-model-protected): after a version port, `git checkout be96u-only -- www/*.dict` and re-check lockstep. |
| `ci/build_one.sh`       | CI launcher: ONE model, ONE variant, no ship. Same shape the engine documents (set BRANCH/TARGET/PREFIX/VARIANTS/STORAGE, call `reaper_build`), because the interactive launchers hardcode `VARIANTS="MCP noMCP"` and a Windows `SHIP_DIR`. Refuses any model but RT-BE96U — the published series reproduces `be96u-only` only. |
| `ci/container_build.sh` | Runs inside the Ubuntu 20.04 container on a GitHub runner: recreates the documented environment (`/home/reaper/asuswrt-be96u`, `/home/reaper/reaper_build`, `/opt/toolchains`, uid-1001 `reaper`, `sh`→bash, python2), fetches the pinned base, applies the series with `git am --keep-cr`, asserts the `release/src/router` tree hash against `provenance/manifest.json`, then calls `ci/build_one.sh`. Driven by `.github/workflows/public-build.yml`; user-facing docs in `docs/CI-PUBLIC-BUILD.md`. |
| `verify_markers.txt`    | Marker manifest read by `reaper_verify.sh` — one line per field-critical fix, proving it is physically inside every staged image. Previously build-box-only, which silently downgraded the CI gate from 19 checks to 18. |
| `reaper_verify.sh`      | 19-check post-build QA gate on the staged fs + packaged image (per-model banner sha + no foreign/stale banner, SAMBA4 + no libiconv, httpd NEEDED closure, FIT model-id via `dumpimage`, MCP/noMCP purity, ARM ELF, www presence/markers, i18n dict lockstep, **shared-code parity vs the RT-BE96U canon**, and **rung-critical patch markers in the staged image** — the last two added 2026-08-05 to make a missed cross-model patch un-shippable). |
| `_port_protect.sh`      | **Single source of truth** for the shared-vs-per-model classification, sourced by BOTH `port_sibling_v2.sh` (what to sync) and `reaper_verify.sh` (what must never lag) so they can never disagree. `PP_SYNC_ANYWAY_RE` force-syncs `www/sysdep/FUNCTION/` (flag-keyed shared VPN/MSWAN/SDN/theme code); protects per-model art/blobs/dicts/version/target.mak and the model-unique **`*_REAPER_Header.{png,mp4}`** (banner + animated login/logout/set-password header, each copied per-model from `reaper-mockups` and re-pointed in the `PP_BANNER_REFS` pages); provides `pp_parity_check`. Added after the 2026-08-05 MSWAN `/sysdep/` gap shipped siblings without the PPPoE-1500 fix. **Watch-item:** `pp_parity_check` skips protected (cls 0) files — it catches "should've synced but didn't", not a shared file *wrongly* protected. Today the only shared zone under a protected path is `www/sysdep/FUNCTION/` (force-synced); if shared code is ever added under `sysdep/` *outside* `FUNCTION/`, or under the non-www `router/sysdep/`, add a matching `PP_SYNC_ANYWAY_RE` clause or it will silently not reach the siblings. |

## Invocation rules (do not skip)

- **Run via the PowerShell tool, `wsl -u reaper bash /mnt/c/.../script.sh`.**
  Git-Bash mangles `/mnt/c/...` paths (silent `No such file`); nested
  `wsl bash -c "...$VAR..."` strips shell variables — always use a script file.
- **Always `-u reaper`.** Building as root trips `prebuild_checks` (`Attempting
  to build as root`) and leaves root-owned logs/artifacts.
- **Author scripts with LF line endings**, never PowerShell `Set-Content`
  (CRLF → `$'\r': command not found` → spurious exit 127).
- **Long builds go in the background task runner** (not `setsid`/`nohup` — WSL
  reaps detached children when `wsl.exe` returns).

## Per-model build procedure (siblings)

The launcher only compiles; the surrounding **prep → port → purge → ship** steps
carry the traps. Full sequence for a sibling `<MODEL>` at version `<VER>`:

1. **Prep** (from whatever branch you're on):
   - Revert build-artifact churn, then remove untracked files the target branch
     tracks (checkout blockers: `rc/init.prep`, `rmcpd`/`rtrafd`/`rchqd` objects…).
   - `git checkout <branch>`.
   - **TRAP #3b — platform-blob revert** (mandatory after any sibling build):
     `git checkout -- release/src-rt-5.04behnd.4916/{bcmdrivers,bootloaders,kernel,rdp} release/src/router/rc/prebuild`.
     A sibling build overwrites tracked per-model prebuilt blobs in the working
     tree; `git checkout <branch>` carries them over (identical across commits)
     → the next model links the wrong `dt_parsing.o` → `undefined reference to
     rtl8372_init_asus` / ld SIGSEGV. Reverting the platform dirs is safe (the
     autotools-mtime trap is about `release/src/router` package dirs, which must
     **not** be blanket-reverted).
   - Preflight: banner present + `REAPER1.png` gone; version.conf; for BE88U
     confirm the `EXTRA_KERNEL_CONFIGS` **full quoted form** with
     `BCM_MAX_MTU_SIZE=10240` (half-written form hangs `syncconfig` on a value
     prompt — kills non-interactive builds).

2. **Port**: `port_sibling_v2.sh <MODEL> --commit --version <VER>`.
   Syncs shared code (carries every fan-out fix), flips the `target.mak` SAMBA4
   selector for the model, bumps version.conf, enforces the banner overlay. All
   guards must print `[ok]`.

3. **SAMBA36X→SAMBA4 contamination purge** — required before a converted
   sibling's *first* Samba4 build (cost 4 failed builds on BE86U):
   - `rm` staged GNU iconv: `release/src/router/arm-glibc/stage/usr/{include/iconv.h,include/libcharset.h,lib/libiconv.so*,lib/libcharset.*}`.
   - `find release/src/router/wget -name '*.o' -delete` + `rm wget/{Makefile,config.status,config.cache,src/config.h}`.
   - Stale `wget/src/url.o` compiled against GNU `iconv.h` (`#define iconv_open
     libiconv_open`) makes wget link `undefined reference to libiconv_open` even
     though fresh configure correctly picks "iconv in libc". **Do NOT delete
     `libiconv-1.14/`** (886 tracked files, present on be96u too — its source
     header is not in wget's `-I` path; the *staged* copy is the culprit).
   - **`make clean` is UNUSABLE on this tree** — it deletes tracked prebuilts and
     distcleans tracked generated `configure` scripts (regen needs autoconf 2.71
     > installed). Stay incremental + surgical; recover damage via
     `git checkout -- release/`.

4. **Build**: `build_<model>.sh` (both variants; `FORCE=1` + verify gate baked
   in). Success = **`MAKE_EXIT=0` on BOTH variants** + `Done! Image 96813GW` +
   both `reaper_verify` **PASS (19/19)**. The bg wrapper can exit 0 even on
   failure — grep the log for `MAKE_EXIT` first, always.

5. **Ship** (never overwrite a prior rung): copy the 4 `.pkgtb` (squashfs +
   loader × MCP/noMCP) from
   `release/src-rt-5.04behnd.4916/targets/96813GW/` to the Windows ship folder
   `$WIN_ASUS_ROOT/asuswrt-merlin.ng/reaper-firmware/` (see below),
   verify built-sha == shipped-sha, and regen `SHA256SUMS-<VER>.txt`.

## Windows paths are not username-pinned

The ship folder and the `reaper-mockups` banner source live on the Windows
mirror under `/mnt/c/Users/<user>/AppData/Roaming/VSC/ASUS`. `_reaper_env.sh`
resolves `<user>` generically and exports `WIN_ASUS_ROOT`; every launcher and
`port_sibling_v2.sh` source it, so nothing is hard-coded to one developer.
Resolution order: an explicit `WINUSER` env var is honored as-is; otherwise it
auto-detects the profile **folder** — the basename of `%USERPROFILE%` (validated
against the ASUS mirror), then a scan of `/mnt/c/Users/*` for the mirror, then
`natha` (the original build box) as last resort. It deliberately resolves the
profile *folder*, not `%USERNAME%`: the two can differ (e.g. login "Nathan" but
folder `C:\Users\natha`). Override on a different box with
`WINUSER=<name> build_<model>.sh …`.

## Key traps (see the project `build-sop` memory for the full ledger)

- **New RTCONFIG flag** must be declared in `config/config.in` or Kconfig
  silently drops it (image builds clean, feature compiled out).
- **Two-build split**: any always-present reaper CGI/helper must sit OUTSIDE
  `#ifdef RTCONFIG_REAPER_MCP` — the MCP build hides the mistake; the noMCP
  build fails. Always confirm BOTH variants.
- **Prebuilt-blob link trap**: unsetting a flag can drop a symbol/lib a closed
  blob imports → link fails. Un-gate the provider or add an `#else` stub.
