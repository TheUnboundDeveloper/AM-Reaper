# Contributor Dev Setup — RT-BEXXU "reaper" hardened build

> **Doc status:** current as of **v2.7.8** · 2026-08-26 <!--@stamp-->

This is the **hard-won, known-good** setup for building and modifying this firmware. It exists because getting an Asuswrt-Merlin / Broadcom-HND tree to build is full of non-obvious traps; everything below is something that actually bit us. Follow it and you skip the trial-and-error.

---

## Ground rules (read first)

- **Primary target is the RT-BEXXU.** Built from `release/src-rt-5.04behnd.4916`, model `rt-BEXXU` (Broadcom BCM4916 / WiFi 7). The RT-BEXXU is the hardware-validated model; the same tree also builds the sibling BCM4916 models **RT-BE86U**, **RT-BE88U**, **GT-BE98**, and **GT-BE98 Pro** from per-model branches (`make rt-be86u` / `rt-be88u` / `gt-be98` / `gt-be98_pro`), plus the newer **RT-BE92U** (BCM6765, `make rt-be92u`, which builds to the `96765GW` profile in a worktree). This guide walks the RT-BEXXU path; the sibling builds are the same recipe with a different target.
- **Never push.** All work stays on the local `BEXXU-only` branch. `origin` points at the upstream/mirror — do **not** `git push`.
- **Don't touch the blobs.** The Broadcom WiFi drivers and prebuilt objects (`wl`/`dhd`, `eapd`, `acsd`, `networkmap`, `wlceventd`, `cfg_mnt`, `spwenc`, `hostapd`/`wpa_supplicant` Broadcom forks) are closed and driver-coupled. Harden the **open-source userspace** only; treat the blobs as documented residual risk.
- **Legal:** the proprietary components (ASUS/Broadcom/Trend Micro/Tuxera) are licensed for ASUS hardware only — see [`README.proprietary`](README.proprietary). The GPL parts are GPL — publish changes if you redistribute.

---

## Get the inputs (source · toolchains · reaper patches)

**This repo does not ship the firmware source or toolchains** — they're large and include proprietary Broadcom/ASUS components licensed for ASUS hardware only. You fetch them from the official sources, then apply the reaper changes from this repo on top.

1. **Upstream Asuswrt-Merlin source @ the matching tag.** This is the full buildable tree (it includes the Broadcom components the BEXXU build needs — which is exactly why we don't redistribute them here):
   ```bash
   git clone https://github.com/RMerl/asuswrt-merlin.ng.git
   cd asuswrt-merlin.ng
   git checkout 3006.102.8-beta2        # the base this fork was built on
   ```
   (Alternatively, ASUS's GPL release tarball for the RT-BEXXU from <https://www.asus.com/support> provides the same GPL/Broadcom sources.)

2. **Toolchains** — the gcc-10.3 ARM + aarch64 crosstools, from RMerlin's toolchain repo, installed under `/opt/toolchains` (details and the gcc-13.2-phantom explanation in §3):
   ```bash
   git clone https://github.com/RMerl/am-toolchains.git
   # copy the crosstools-arm-gcc-10.3-… and crosstools-aarch64-gcc-10.3-… dirs to /opt/toolchains
   ```

3. **Apply the reaper hardening** from this repo's [`../patches/`](../patches/) onto the upstream checkout:
   ```bash
   cd asuswrt-merlin.ng
   # --keep-cr is REQUIRED: some third-party files (lltdc) have CRLF line endings;
   # without it git strips the CR and the series fails to apply at qospktio.c.
   git am --keep-cr /path/to/AM-Reaper/patches/*.patch   # preserves authorship + messages
   # then the OpenSSL 3.5 source, which is too large for a patch (verify the sha256 first):
   tar -xzf /path/to/AM-Reaper/overlays/openssl-3.5-source.tar.gz
   #   (plain `patch -p1` will NOT work: 4 patches carry git binary payloads —
   #    fonts, logo, USB ring sprite — that `patch` cannot apply. Use git am.)
   ```
   The patches touch only the shared open-source userspace (`release/src/router/{httpd,rc,shared,libovpn,snooper,urlfilterd,lltdc,wsdd2,infosvr,libcodb,…}`), so they apply cleanly to a stock upstream tree. **Making the tree BEXXU-only (removing the sibling-model artifacts) is optional and not required to build `rt-BEXXU`** — see [`../patches/README.md`](../patches/README.md).

4. Then follow §2–§7 below to set up WSL/toolchains and build.

> Everything from here down is the hard-won environment detail for actually building the result.

---

## 1. Two-layer layout: Windows mirror + WSL build clone

| | Path | Role |
|---|---|---|
| **Windows mirror** | `C:\…\VSC\ASUS\asuswrt-merlin.ng` | Reference/editing mirror. Renders symlinks as text; **does not build.** |
| **WSL build clone** | `/home/<builduser>/asuswrt-BEXXU` | The real build tree (Linux, symlinks materialize). Build here. |

You **edit** through the Windows side (or over the UNC path into WSL) and **build** in WSL. The two stay in sync via git.

### Windows checkout caveats
- The tree contains **254 test-fixture paths with colons** (illegal on NTFS), e.g. `…/ipset-7.6/tests/…` and `…/udev/test/…`. A full Windows checkout fails at ~98% unless you use a **non-cone sparse-checkout** that excludes them:
  ```
  git config core.sparseCheckout true
  git config core.sparseCheckoutCone false
  # .git/info/sparse-checkout:
  /*
  !/release/src/router/ipset-6/tests/
  !/release/src/router/ipset-7.6/tests/
  !/release/src/router/udev/test/
  ```
- With `core.symlinks=false` (Windows default), **~138 files perpetually show as "modified"** (symlinks/line-endings in the non-BEXXU trees). **Ignore them. Never commit them.** The BEXXU sources (`release/src/router/{httpd,rc,shared,…}`) check out clean.

---

## 2. WSL distro: use Ubuntu **20.04** (Focal)

This is the single biggest time-saver. **Do not use a current Ubuntu (24.04/26.04).**

- Modern Ubuntu ships **Python 3 only (no python2)** and **dash as `/bin/sh`**. The Broadcom build needs **python2**, and dash's `echo -e` prints a literal `-e` that **corrupts `bcmdrivers/Kconfig.autogen`** (kernel `olddefconfig` then fails with "invalid statement"). Generation scripts also silently produce nothing.
- 20.04 has python2 and the right tooling. Import it (it's not in the WSL catalog anymore):
  ```powershell
  wsl --import Ubuntu-20.04 C:\wsl\focal C:\wsl\dl\focal-rootfs.tar.xz --version 2
  ```

### Two must-do fixes inside the distro
1. **`/bin/sh` → bash** (fixes the dash `echo -e` corruption):
   ```bash
   ln -sf bash /bin/sh
   ```
2. **Build as a non-root user.** `prebuild_checks` aborts if `whoami == root`. Create a dedicated user and always build as them:
   ```bash
   useradd -m -u 1001 reaper        # no sudo needed
   ```
   ⚠️ A **background** `wsl … -- bash` resolves to **root** even if your interactive default is someone else — so **always** pass `--user reaper` explicitly:
   ```powershell
   wsl -d Ubuntu-20.04 --user reaper -- bash /path/to/script.sh
   ```

---

## 3. Toolchains: gcc-10.3 (and the gcc-13.2 phantom)

This tree (`ASUSWRT_BRCM_SDK_VERSION=WIFI7_SDK_20231126`, kernel `linux-4.19`) builds with **gcc-10.3**, not gcc-13.2.

> **The gcc-13.2 trap:** `release/src-rt/platform.mak` *mentions* gcc-13.2/linux-5.15, but only behind `ifneq (,$(filter $(ASUSWRT_BRCM_SDK_VERSION),WIFI7_SDK_20250506 WIFI8_SDK_20251126))`. This tree's SDK isn't in that filter, so the gcc-13.2 branch is **dead code here** — it falls through to gcc-10.3/linux-4.19. The prebuilt aarch64 blobs report `GCC (Buildroot 2021.02.4) 10.3.0`, confirming 10.3 is correct. Don't go hunting for gcc-13.2; you don't need it for this SDK.

Install both real toolchains under `/opt/toolchains`:
- `crosstools-aarch64-gcc-10.3-linux-4.19-glibc-2.32-binutils-2.36.1` — kernel, bootloader, bcmdrivers (aarch64)
- `crosstools-arm-gcc-10.3-linux-4.19-glibc-2.32-binutils-2.36.1` (+ an `arm_softfp` alias symlink) — **32-bit ARM userspace** (this is what our security patches compile as)

**PATH must APPEND, not prepend** the toolchain bins:
```bash
export PATH=$PATH:/opt/toolchains/crosstools-aarch64-gcc-10.3-…/usr/bin:/opt/toolchains/crosstools-arm-gcc-10.3-…/usr/bin
```
(Prepending lets the toolchain's ancient `bison` — which needs `libreadline.so.6`, absent on modern distros — shadow the system one and break the build.)

### `-lnsl` and friends (link failures in vsftpd etc.)
The gcc-10.3 glibc-2.32 sysroot ships the runtime `libnsl.so.1` but **not** the unversioned linker dev symlink. Create it (and pre-empt the same for util/resolv/crypt/anl) in the sysroot:
```bash
cd <sysroot>/arm-buildroot-linux-gnueabi/sysroot/lib
for l in nsl util resolv crypt anl; do ln -sf lib$l.so.1 lib$l.so; done
```

---

## 4. Host packages (Ubuntu 20.04)

The generic ASUS GPL build-readme deps list (Ubuntu 14.04/16.04, gcc-5.3) is outdated. The **actual working set** on 20.04:

```bash
apt install build-essential bison flex gawk gettext libreadline-dev \
  autogen gtk-doc-tools u-boot-tools \
  python2 python2-dev \
  liblzo2-dev uuid-dev xxd patch gdisk bc lzop lz4 zstd kmod \
  libelf-dev libncurses5-dev
update-alternatives --install /usr/bin/python python /usr/bin/python2 1
```
Gotchas:
- **Reinstall `uuid-dev`** if the first pass left `uuid.pc` absent (a `.pc` missing breaks pkg-config lookups).
- **Do NOT** add `libextutils-makemaker-perl` to an apt batch — it doesn't exist on 20.04 and **aborts the whole `apt install`** (silently installing nothing). `ExtUtils::MakeMaker` is already in perl core.
- For the prebuilt **x86** host tool (`LnxDictPrep`), enable **i386 multiarch** (`dpkg --add-architecture i386`) and install its 32-bit libs.

---

## 5. Build recipe

From the platform tree, as the non-root user:
```bash
cd /home/reaper/asuswrt-BEXXU/release/src-rt-5.04behnd.4916
make rt-BEXXU            # NOTE: -j1 (see below)
```
(For the sibling models, build the corresponding target from that model's branch —
`make rt-be86u` / `rt-be88u` / `gt-be98` / `gt-be98_pro` / `rt-be92u` — same recipe, same caveats.)

The non-obvious parts:

1. **Build TWICE.** The first `make rt-BEXXU` generates the kernel/busybox/router config (`config_rt-BEXXU` from the tracked `config_base`) and then **dies at `setprofile`**. The **second** run proceeds. (A fresh clone needs this; a warm tree usually doesn't.)
2. **Use `-j1`.** `setprofile` (top `Makefile`) and the router clean-build (`rm -rf fs.build`) are **parallel-unsafe** — `-j>1` reliably races and fails. `make rt-BEXXU` with no `-j` is effectively -j1 and is the safe default.
3. **Restore the router symlink before each run.** During userspace staging the symlink
   `…/bcmdrivers/broadcom/net/wl/bcm96813/main/src/router` (→ `../../../../../../../../src/router`)
   sometimes gets clobbered into a real (empty) dir, after which staging can't find `rtconfig.h`. Restore it:
   ```bash
   L=…/bcm96813/main/src/router
   [ -L "$L" ] || { rm -rf "$L"; ln -s ../../../../../../../../src/router "$L"; }
   ```
4. **iptables-1.4.x** needs a few headers this drop omits: create the stub `include/linux/netfilter/xt_ethport.h`, overlay the behnd kernel netfilter headers into the iptables include dir, and disable the true-orphan extensions (`libipt_ROUTE`, `libip6t_ROUTE`, `libipt_geoip`, `libipt_webstr`). (See the helper scripts; this is a one-time tree fix-up.)

**Output** lands in `release/src-rt-5.04behnd.4916/targets/96813GW/`:
- `RT-BEXXU_…_nand_squashfs.pkgtb` — **firmware-only image** (flash this for a normal upgrade)
- `RT-BEXXU_…_nand_squashfs_loader.pkgtb` — firmware **+ bootloader** (recovery/full)

Format is **`.pkgtb`** (modern Broadcom NAND package), not the older `.trx`.

### Version label (`BUILDREV`)
`release/src-rt/Makefile` defaults `BUILDREV` to `-reaper`, but it's `export`ed, so recursive sub-makes see it non-empty and flip to `-g<commit>`. Net effect: the image is labeled **`…_beta2-g<hash>`** matching the branch tip (which is great — it pins the exact commit). To force the `-reaper` brand instead, pass it on the command line:
```bash
make rt-BEXXU BUILDREV=-reaper
```
> Edit the **real** `release/src-rt/Makefile`, not the per-platform `Makefile` (it's a symlink — editing through the link shows no git diff).

---

## 6. Editing + the tooling gotchas

- **Edit source over UNC:** `\\wsl.localhost\Ubuntu-20.04\home\reaper\asuswrt-BEXXU\release\src\router\…`. Read/Edit tools work fine against it; just match exact bytes (the tree uses **tabs** in most C files, **spaces** in a few like `lltdc/src/qospktio.c`).
- **PowerShell → WSL strips `$shell` variables.** Inline single-quoted commands containing `$var`/`$()`/`for` loops get mangled (the vars arrive empty). **Always write the shell logic to a `.sh` file** (e.g. under the scratchpad / `/mnt/c/…`) and run:
  ```powershell
  wsl -d Ubuntu-20.04 --user reaper -- bash /mnt/c/…/script.sh
  ```
  The Git-Bash tool has the same `$var`/`/unix/path` mangling — same fix.

---

## 7. Verifying a change

Per-file standalone compile is awkward here (the component Makefiles need the platform env: `../common.mak` errors without `platform.mak`). The reliable verification is a **full `make rt-BEXXU` re-entry**: make recompiles exactly the files you touched (newer mtime), relinks their components in-context, and repackages the image.

What "good" looks like:
- `make` exits **0** and prints `Done! Image 96813GW has been built`.
- **No NEW warnings at your edit sites.** ASUS code is noisy (lots of pre-existing `-Wformat`, unused-var, pointer-sign, `strncpy`-bound warnings) — diff against the baseline and make sure none of the warnings point at your lines.
- The new `…_g<tip>_nand_squashfs.pkgtb` appears, and `strings fs/usr/lib/libshared.so | grep beta2-g…` matches the branch tip (proves your commit is baked in).

> A full build is ~8–15 min at -j1. For a quick "does it still compile" loop, build once after a batch of edits rather than per-file.

---

## 8. Where things live

- **Fix list / what's been hardened:** [`REAPER-FIXES.md`](REAPER-FIXES.md) (this `docs/` folder)
- **Release notes (per published image):** [`RELEASE-NOTES.md`](RELEASE-NOTES.md)
- **The hardening changes:** [`patches/`](../patches/) — applied onto the upstream source (see "Get the inputs" above)
- **Flashable images:** not in git (build artifacts) — built into `release/src-rt-5.04behnd.4916/targets/96813GW/RT-BEXXU_…_nand_squashfs.pkgtb`, and published on the repo's **GitHub Releases** for end users who only want to flash.
- **Upstream originals (reference/GPL compliance):** [`LICENSE`](../LICENSE) (repo root), plus `README.proprietary` and `ASUS-Merlin_Changelog-3006.txt` in this `docs/` folder

---

## 9. Flashing & recovery (for testing your build)

- Flash the **non-`loader`** `…_nand_squashfs.pkgtb` via **Administration → Firmware Upgrade**.
- First time flashing a non-stock image, the webui may refuse it. Over SSH: `nvram set DOWNGRADE_CHECK_PASS=1`, then upload.
- A **factory reset** is recommended when coming from much older firmware, another third-party firmware, or stock-with-VPN. Don't reload a saved settings backup after a reset (it re-imports the bad state).
- **Recovery if it won't boot:** ASUS Firmware Restoration tool + the router's rescue mode, or flash the `_loader` image. You can always return to stock by flashing an official ASUS image.
- Success criterion for a hardening change = **functional parity / no regressions** (boots; WiFi/WAN/IPv6/DualWAN/VPN/Samba behave as stock). The hardening is invisible by design.
