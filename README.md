# ASUS-Merlin-Reaper

**Security-hardened, de-clouded [Asuswrt-Merlin](https://github.com/RMerl/asuswrt-merlin.ng) for the ASUS RT-BE96U** (WiFi 7 / Broadcom BCM4916), firmware line **3006.102.x** — branded `reaper`. Current: **v1.4.1**.

The goal: harden the open-source userspace so that **only physical access** can compromise the device — eliminating remotely/LAN-reachable command injection, buffer overflows, format-string and auth-bypass bugs — remove cloud-coupled/AI-branded attack surface, and produce a flashable image that can be shared with other security-conscious BE96U owners.

> ~70+ security issues fixed across four audit rounds (command-injection, memory-safety, and defense-in-depth), each compile/link-verified by a full firmware build. See **[docs/REAPER-FIXES.md](docs/REAPER-FIXES.md)**. Version-by-version history: **[docs/CHANGELOG.md](docs/CHANGELOG.md)**.

Beyond hardening, Reaper adds router features ASUS never shipped — two **Hardware QoS** engines that keep the flow accelerator on, a native **Traffic Analyzer**, and an **optional, read-only, LAN-only AI Advisor** — and removes cloud/telemetry surface (Alexa/Google, Trend Micro DPI, AiCloud/WebDAV, the AAE cloud tunnel). See **[docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md)**.

---

## Disclaimer

This project is an independent, third-party firmware modification. Neither ASUS nor Eric Sauvageau (Asuswrt-Merlin) has participated in its development, reviewed it, approved it, or endorsed it.

References to ASUS and Asuswrt-Merlin are provided solely to identify the hardware manufacturer, acknowledge the upstream codebase, and credit the work on which this project is built.

Do not contact ASUS or the Asuswrt-Merlin developer for installation assistance, troubleshooting, debugging, compatibility questions, or issue reporting related to this firmware. Support requests and reports must be submitted through this repository or through the designated project email address, depending on the nature and sensitivity of the finding.

Redistribution or rehosting of compiled firmware images is not authorized. Official downloads must come directly from this project’s GitHub repository so that users receive the intended, current, and verifiable release.

Because this is an independently maintained project, updates may be intermittent or infrequent depending on available time, technical limitations, upstream changes, hardware access, and other project constraints.

Updates may be released when:

* ASUS publishes a new applicable GPL source release;
* Asuswrt-Merlin publishes changes relevant to this project;
* Newly discovered bugs or security vulnerabilities require remediation; or
* Upstream changes address issues involving proprietary or closed-source components that cannot be modified directly by this project.

No specific update schedule, support period, feature roadmap, or continued compatibility with future ASUS or Asuswrt-Merlin releases is guaranteed.

---

## What's in this repo (and what isn't)

This repo is **lean by design.** It contains *our work* — not the multi-GB vendor tree.

**In the repo:**
- **[`patches/`](patches/)** — the hardening, as patch files you apply onto an upstream Asuswrt-Merlin checkout.
- **[`docs/`](docs/)** — all project documentation (see **Documentation** below).
- Root: [`LICENSE`](LICENSE) (GPL v2) and [`LICENSE.reaper`](LICENSE.reaper) (the Reaper-specific notice), plus `SECURITY.md` and `CONTRIBUTING.md`.

**Not in the repo (externally sourced — see [docs/DEV-SETUP.md](docs/DEV-SETUP.md) § "Get the inputs"):**
- The **upstream firmware source** — clone `RMerl/asuswrt-merlin.ng` at tag `3006.102.8-beta2`.
- The **proprietary Broadcom/ASUS/Trend Micro/Tuxera components** — licensed for ASUS hardware only; they come with the upstream source / ASUS GPL drop, never redistributed here.
- The **toolchains** — gcc-10.3 ARM/aarch64 from `RMerl/am-toolchains`.
- The **flashable `.pkgtb` images** — build artifacts; published on **GitHub Releases** for users who only want to flash.

## Documentation — read in this order

1. **[docs/PROJECT.md](docs/PROJECT.md)** — what this fork is, scope, hard rules, threat model, flashing, legal. (The collapsed version of the upstream READMEs.)
2. **[docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md)** — what the current release contains, the two build variants, and how to flash it.
3. **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — big changes per version, v1.0 → v1.4.1.
4. **[docs/DEV-SETUP.md](docs/DEV-SETUP.md)** — the hard-won contributor build/edit environment: WSL 20.04, gcc-10.3 toolchains, host deps, the build recipe and its traps, the editing/tooling gotchas, and how to verify a change. **If you want to build or patch the firmware, this is the one.**
5. **[docs/REAPER-FIXES.md](docs/REAPER-FIXES.md)** — authoritative list of every security fix applied (all audit rounds), with commits.
6. **[docs/GPL-MERGE.md](docs/GPL-MERGE.md)** — maintainer guide for rebasing the hardening onto a new upstream/GPL drop.
7. **[docs/ENTERPRISE-ROADMAP.md](docs/ENTERPRISE-ROADMAP.md)** — package-update candidates and feature ideas (what's in-tree-but-disabled, what to add via Entware).
8. **[patches/](patches/)** — the hardening itself, as patches you apply onto an upstream checkout.

Retained upstream originals kept for reference: `docs/README.proprietary` (the blob-licensing notice, summarized in `PROJECT.md` § Legal) and `docs/Changelog-3006.txt` (upstream 3006.102 history; Reaper's own history is in [docs/CHANGELOG.md](docs/CHANGELOG.md)). The other upstream READMEs (generic multi-model build notes, stale project blurbs, upstream support pointers) were out of date for this BE96U-only fork; their still-relevant content was folded into `PROJECT.md` / `DEV-SETUP.md`.

## Quick start

- **Just want to flash it?** Grab the `RT-BE96U_…_nand_squashfs.pkgtb` from **Releases** and flash via *Administration → Firmware Upgrade*. From v1.4 there are **two variants** — a **Standard** image and a `…_MCP` image that adds the optional AI Advisor (off by default). Pick either; see [docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md) § 2. First non-stock flash needs `nvram set DOWNGRADE_CHECK_PASS=1` (see [docs/PROJECT.md](docs/PROJECT.md) § Installation).
- **Want to build it yourself / contribute?** Read **[docs/DEV-SETUP.md](docs/DEV-SETUP.md)** — it walks you from fetching the upstream source + toolchains, applying `patches/`, through the build and verification (including every trap we hit). The AI Advisor is compiled in or out via the `RTCONFIG_REAPER_MCP` build flag.

## Base & status

- Base: Asuswrt-Merlin **3006.102.8** (patches apply on tag `3006.102.8-beta2`; the sibling-model strip is optional — see [`patches/README.md`](patches/README.md)).
- Current version: **v1.4.1** (release candidate — everything through v1.3.3 is validated on the physical RT-BE96U; the v1.4.x AI Advisor is build-verified with on-hardware validation in progress). Per-version history: [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Legal

- **GPL:** the GPL portions are under GPL v2 ([`LICENSE`](LICENSE)); the Reaper modifications are likewise GPL v2, with a Reaper-specific notice in [`LICENSE.reaper`](LICENSE.reaper). Publish your changes if you redistribute the GPL code.
- **Proprietary components** (ASUS / Broadcom / Trend Micro / Tuxera) are **licensed for genuine ASUS hardware only** ([`docs/README.proprietary`](docs/README.proprietary)) and are intentionally **not** included here. This fork targets the RT-BE96U exclusively.
- **No warranty:** provided as-is; keep a recovery path ready when flashing. See the Disclaimer above for redistribution and support terms.

Security reports: see [SECURITY.md](SECURITY.md). Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md).
