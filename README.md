# ASUS-Merlin-Reaper

**Security-hardened [Asuswrt-Merlin](https://github.com/RMerl/asuswrt-merlin.ng) for the ASUS RT-BE96U** (WiFi 7 / Broadcom BCM4916), firmware line **3006.102.x** — branded `reaper`.

The goal: harden the open-source userspace so that **only physical access** can compromise the device — eliminating remotely/LAN-reachable command injection, buffer overflows, format-string and auth-bypass bugs — and produce a flashable image that can be shared with other security-conscious BE96U owners.

> ~56 security issues fixed across two audit rounds (command-injection, memory-safety, and defense-in-depth), each compile/link-verified by a full firmware build. See **[REAPER-FIXES.md](REAPER-FIXES.md)**.

---

## What's in this repo (and what isn't)

This repo is **lean by design.** It contains *our work* — not the multi-GB vendor tree.

**In the repo:**
- **[`patches/`](patches/)** — the hardening, as patch files you apply onto an upstream Asuswrt-Merlin checkout.
- **[`REAPER-FIXES.md`](REAPER-FIXES.md)** — the authoritative fix list (per-finding, with commit hashes).
- **[`ENTERPRISE-ROADMAP.md`](ENTERPRISE-ROADMAP.md)** — package-update candidates + enterprise feature ideas.
- **[`docs/`](docs/)** — `PROJECT.md` (overview) and `DEV-SETUP.md` (the hard-won build/edit/verify guide), plus the retained upstream `License` / `README.proprietary` / `Changelog-3006.txt`.

**Not in the repo (externally sourced — see [docs/DEV-SETUP.md](docs/DEV-SETUP.md) § "Get the inputs"):**
- The **upstream firmware source** — clone `RMerl/asuswrt-merlin.ng` at tag `3006.102.8-beta2`.
- The **proprietary Broadcom/ASUS/Trend Micro/Tuxera components** — licensed for ASUS hardware only; they come with the upstream source / ASUS GPL drop, never redistributed here.
- The **toolchains** — gcc-10.3 ARM/aarch64 from `RMerl/am-toolchains`.
- The **flashable `.pkgtb` images** — build artifacts; published on **GitHub Releases** for users who only want to flash.

## Quick start

- **Just want to flash it?** Grab the `RT-BE96U_…_nand_squashfs.pkgtb` from **Releases** and flash via *Administration → Firmware Upgrade*. See [docs/PROJECT.md](docs/PROJECT.md) § Installation (first non-stock flash needs `nvram set DOWNGRADE_CHECK_PASS=1`).
- **Want to build it yourself / contribute?** Read **[docs/DEV-SETUP.md](docs/DEV-SETUP.md)** — it walks you from fetching the upstream source + toolchains, applying `patches/`, through the build and verification (including every trap we hit).

## Base & status

- Base: Asuswrt-Merlin **3006.102.8-beta2**
- Patches in this repo apply on top of that tag (the sibling-model strip is optional — see [`patches/README.md`](patches/README.md)).

## Legal

GPL components are GPL (`docs/License`); publish your changes if you redistribute. The **proprietary components are licensed for genuine ASUS hardware only** (`docs/README.proprietary`) and are intentionally **not** included here. This fork targets the RT-BE96U exclusively.
