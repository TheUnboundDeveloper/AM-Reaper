# Build Dependencies & Pinned Inputs

Everything an independent developer needs to reproduce a Reaper build, with each
input's provenance and license status. Companion to
[`docs/DEV-SETUP.md`](docs/DEV-SETUP.md) (the how) and
[`docs/SOURCE-AVAILABILITY.md`](docs/SOURCE-AVAILABILITY.md) (the GPL obligation).

> Items marked **UNVERIFIED** are provenance/redistribution facts the maintainer
> has not independently confirmed. They are flagged so no one assumes a
> redistribution right that has not been established. Verifying them is a
> pre-publication task, not a claim of clearance.

## Pinned source inputs

| Input | Pin | Source | License |
|---|---|---|---|
| Upstream base tree | tag `3006.102.8-beta2`, commit `a7ebfa133a` | <https://github.com/RMerl/asuswrt-merlin.ng> | GPL v2 (GPL parts) + proprietary vendor components (see below) |
| Reaper patch series | `patches/0001`–`0181` (v1.0 → v1.6.0) | this repo | GPL v2 ([`LICENSE.reaper`](LICENSE.reaper)) |

Applying the series to the pinned commit with `git am --keep-cr` reproduces the
Reaper source tree exactly (see [`patches/README.md`](patches/README.md)).

## Toolchain

| Input | Pin | Source | License / redistribution |
|---|---|---|---|
| ARM crosstools | `crosstools-arm-gcc-10.3-linux-4.19-glibc-2.32-binutils-2.36.1` | <https://github.com/RMerl/am-toolchains> | GCC/binutils/glibc are GPL/LGPL; the packaged toolchain's exact redistribution terms are **UNVERIFIED** — obtain from the upstream `am-toolchains` repo rather than rehosting until confirmed. |
| aarch64 crosstools | `crosstools-aarch64-gcc-10.3-linux-4.19-glibc-2.32-binutils-2.36.1` | same | same |
| `LnxDictPrep` (host tool) | ships in the upstream tree (`tools/`) | upstream Asuswrt-Merlin | Provenance/license **UNVERIFIED**; it is an upstream 32-bit host build tool, not a Reaper artifact. |

> gcc-13.2 is **not** required — it is dead code for this SDK
> (`WIFI7_SDK_20231126`). See DEV-SETUP.md §3.

## Host build environment

| Requirement | Detail | Notes |
|---|---|---|
| OS | Ubuntu 20.04 (Focal) under WSL | Modern Ubuntu lacks python2 and defaults `/bin/sh`→dash, which corrupts `Kconfig.autogen`. Focal rootfs pin (URL/hash) is **UNVERIFIED** — record the exact image you import. |
| `/bin/sh` | must be `bash` (`ln -sf bash /bin/sh`) | dash `echo -e` breaks the Kconfig autogen. |
| python2 | `update-alternatives --install /usr/bin/python python /usr/bin/python2 1` | build scripts assume python2. |
| Build user | non-root (`prebuild_checks` aborts as root) | see DEV-SETUP.md §2. |
| apt packages + multiarch | exact list in DEV-SETUP.md §4 | includes i386 multiarch for `LnxDictPrep`. |

## Build command

```bash
cd release/src-rt-5.04behnd.4916
nice make rt-be96u -j1     # -j1 required; fresh tree builds twice
```

Success + verification criteria are in DEV-SETUP.md §5–§7.

## Proprietary vendor components (NOT redistributable here)

The buildable tree includes closed Broadcom, ASUS, Trend Micro, and Tuxera
components licensed for genuine ASUS hardware only. They arrive with the upstream
source / ASUS GPL drop and are **never** redistributed by this repository. See
[`docs/README.proprietary`](docs/README.proprietary) and
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).
