# AM-Reaper

> **Doc status:** current as of **v3.1.0** · 2026-09-06 <!--@stamp-->

**Security-hardened, de-clouded [Asuswrt-Merlin](https://github.com/RMerl/asuswrt-merlin.ng) for the ASUS RT-BE Series** (WiFi 7 / Broadcom), firmware line **3006.102.x** — branded `reaper`. Newest published release: **v2.8.8** <!--@pubver--> (all six models — see §"Current version" below); the source tree sits at **v3.1.0** <!--@treever-->. Primary, hardware-validated model is the **RT-BE96U**; also built from per-model branches of the same tree for the **RT-BE86U**, **RT-BE88U**, **GT-BE98**, and **GT-BE98 Pro** (BCM4916, metal validation owed on the four siblings), with the **RT-BE92U** (BCM6765) as the experimental sixth model.

The goal: harden the open-source userspace so that **only physical access** can compromise the device — eliminating remotely/LAN-reachable command injection, buffer overflows, format-string and auth-bypass bugs — remove cloud-coupled/AI-branded attack surface, and produce a flashable image that can be shared with other security-conscious BE-series owners.

> ~70+ security issues fixed across four audit rounds (command-injection, memory-safety, and defense-in-depth) at v1.0, plus a later multi-agent **audit-remediation arc** (73 verified findings closed across v1.8.2–v1.8.6) — each compile/link-verified by a full firmware build — with later review passes (the July 2026 audits and the v3.0.0 pre-release review) recorded alongside. See **[docs/REAPER-FIXES.md](docs/REAPER-FIXES.md)**. Version-by-version history: **[docs/CHANGELOG.md](docs/CHANGELOG.md)**.

Beyond hardening, Reaper adds router features ASUS never shipped — two **Hardware QoS** engines that keep the flow accelerator on, a native **Traffic Analyzer**, an **optional, read-only, LAN-only AI Advisor** (with an opt-in, bounded network-diagnostics mode), **on-router network diagnostics** (ping/traceroute/DNS/netstat via the AI Advisor), one-click sanitized **Reaper Diagnostics**, **Gatekeeper** (opt-in, default-deny, on-router device access control), **Reaper Warden** (opt-in threat/geo firewall — ipset threat feeds + by-country blocking, IPv6 dual-stack, strict anti-lockout), a **native firewall rules engine** (opt-in; named objects for devices/networks/services/countries, inbound + forward + outbound rules on IPv4 and IPv6, per-device internet defaults, source- and schedule-restricted port forwards, and commit-confirm auto-rollback so a bad ruleset cannot lock you out), and a **Device Identity Manager** (a per-device "Devices" page unifying name, reservation, access state, and presence), **Policy Routing** (per-device and per-destination VPN routing with commit-confirm), a **Connections** explorer (live flow table, accelerator state and QoS class per flow) with **QoS diagnostics**, per-device **Analytics**, **Wireless Quality** and **WiFi Pro** controls (channel lock, preamble lock, station health), **USB and storage** management, a **full Backup and Restore** (one passphrase-sealed archive carrying settings and `/jffs`, re-authenticated before download), a **GitHub-hosted firmware update check**, a **one-step first-boot setup** (network name, Wi-Fi password and router login in one box, replacing the wizard-less factory flow), and an **OpenSSL 3.5.8** library across the whole image in place of the end-of-life 1.1.1 — and removes cloud/telemetry surface (Alexa/Google, Trend Micro DPI, AiCloud/WebDAV, the AAE cloud tunnel). See **[docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md)**.

---

## Disclaimer

This project is an independent, third-party firmware modification. Neither ASUS nor Eric Sauvageau (Asuswrt-Merlin) has participated in its development, reviewed it, approved it, or endorsed it.

References to ASUS and Asuswrt-Merlin are provided solely to identify the hardware manufacturer, acknowledge the upstream codebase, and credit the work on which this project is built.

Do not contact ASUS or the Asuswrt-Merlin developer for installation assistance, troubleshooting, debugging, compatibility questions, or issue reporting related to this firmware. Support requests and reports must be submitted through this repository or through the designated project email address, depending on the nature and sensitivity of the finding.

The GPL-covered portions of this firmware are, and remain, freely redistributable under GPL v2 — nothing here restricts that (see [docs/SOURCE-AVAILABILITY.md](docs/SOURCE-AVAILABILITY.md)). However, a compiled `.pkgtb` **image** also bundles proprietary Broadcom/ASUS/Trend Micro/Tuxera components that are licensed for genuine ASUS hardware only and carry **no redistribution grant** ([docs/README.proprietary](docs/README.proprietary), [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)). For that reason the project does not authorize rehosting of the compiled images, and asks that flashable images be obtained from the official project release channel so users receive an intended, current, and verifiable build. If you redistribute the GPL code or images, you must comply with GPL v2 — publish the corresponding source and preserve the notices ([docs/SOURCE-AVAILABILITY.md](docs/SOURCE-AVAILABILITY.md)).

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
- **[`overlays/`](overlays/)** — the per-model identity overlays for the five siblings, the GT-BE98 platform archive, and the OpenSSL 3.5 source archive (hash-pinned; too large to ship as a patch).
- Root: [`LICENSE`](LICENSE) (GPL v2), [`LICENSE.reaper`](LICENSE.reaper) (the Reaper-specific notice), [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md), [`DEPENDENCIES.md`](DEPENDENCIES.md), [`LICENSES/`](LICENSES/) (license texts), plus `SECURITY.md` and `CONTRIBUTING.md`.
- **Compliance:** [`docs/SOURCE-AVAILABILITY.md`](docs/SOURCE-AVAILABILITY.md) (GPL source + written offer).

**Not in the repo (externally sourced — see [docs/DEV-SETUP.md](docs/DEV-SETUP.md) § "Get the inputs"):**
- The **upstream firmware source** — clone `RMerl/asuswrt-merlin.ng` at tag `3006.102.8-beta2`.
- The **proprietary Broadcom/ASUS/Trend Micro/Tuxera components** — licensed for ASUS hardware only; they come with the upstream source / ASUS GPL drop, never redistributed here.
- The **toolchains** — gcc-10.3 ARM/aarch64 from `RMerl/am-toolchains`.
- The **flashable `.pkgtb` images** are build artifacts. They *are* published here (GitHub [Releases](https://github.com/TheUnboundDeveloper/AM-Reaper/releases) and in-tree under [`releases/`](releases/)), and the complete corresponding source travels with them in [`patches/`](patches/) + [`provenance/`](provenance/) — see [docs/SOURCE-AVAILABILITY.md](docs/SOURCE-AVAILABILITY.md).

## Documentation — read in this order

1. **[docs/REAPER-GUIDE.md](docs/REAPER-GUIDE.md)** — **the owner's guide: start here.** What Reaper is, the requirements and rules for running it properly (the `/jffs` store, the two backups, USB, Apply and Keep, the sanitized report), every feature page, good practice, troubleshooting, glossary.
2. **[docs/FIREWALL-GUIDE.md](docs/FIREWALL-GUIDE.md)** — the firewall suite for its users: what each tab is for, how to use it, an example rule per tab.
3. **[docs/PROJECT.md](docs/PROJECT.md)** — what this fork is, scope, hard rules, threat model, flashing, legal. (The collapsed version of the upstream READMEs.)
4. **[docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md)** — what the current release contains, the two build variants, and how to flash it.
5. **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — big changes per version, v1.0 → the current release.
6. **[docs/DEV-SETUP.md](docs/DEV-SETUP.md)** — the hard-won contributor build/edit environment: WSL 20.04, gcc-10.3 toolchains, host deps, the build recipe and its traps, the editing/tooling gotchas, and how to verify a change. **If you want to build or patch the firmware, this is the one.**
7. **[docs/REAPER-FIXES.md](docs/REAPER-FIXES.md)** — authoritative list of every security fix applied (all audit rounds), with commits.
8. **[docs/GPL-MERGE.md](docs/GPL-MERGE.md)** — maintainer guide for rebasing the hardening onto a new upstream/GPL drop.
9. **[patches/](patches/)** — the hardening itself, as patches you apply onto an upstream checkout.
10. **[docs/CI-PUBLIC-BUILD.md](docs/CI-PUBLIC-BUILD.md)** — building the firmware in GitHub Actions from a fork, with no local setup: what each run proves, how to read the log, and current limits.

Retained upstream originals kept for reference: `docs/README.proprietary` (the blob-licensing notice, summarized in `PROJECT.md` § Legal) and `docs/ASUS-Merlin_Changelog-3006.txt` (upstream 3006.102 history; Reaper's own history is in [docs/CHANGELOG.md](docs/CHANGELOG.md)). The other upstream READMEs (generic multi-model build notes, stale project blurbs, upstream support pointers) were out of date for this RT-BE-series fork; their still-relevant content was folded into `PROJECT.md` / `DEV-SETUP.md`.

## Quick start

- **Just want to flash it?** Flashable builds are **hosted right here on GitHub** — grab the image for your model from the [**Releases**](https://github.com/TheUnboundDeveloper/AM-Reaper/releases) page (also mirrored in-tree under [`releases/`](releases/)), each with a `SHA256SUMS` file to verify the download. Every image ships with its complete corresponding source in this repo (`patches/` + `provenance/`); see [docs/SOURCE-AVAILABILITY.md](docs/SOURCE-AVAILABILITY.md). There are **two variants** — a **Standard** image and an **AI Advisor** (`…_MCP`) image that adds the optional MCP server (off by default). First non-stock flash needs `nvram set DOWNGRADE_CHECK_PASS=1` (see [docs/PROJECT.md](docs/PROJECT.md) § Installation); flash via *Administration → Firmware Upgrade*.
- **Want to build it yourself without setting anything up?** Fork this repo and run the **[Build firmware from source](.github/workflows/public-build.yml)** workflow from the Actions tab in your fork. It builds the model you pick — or all six — in a clean room on GitHub's runners — pinned upstream base, pinned toolchains, this repo's published patch series, this repo's own build engine and QA gate — and hands you the `.pkgtb` plus a full provenance record as artifacts. No Linux box, no toolchain, no Broadcom SDK required. **[docs/CI-PUBLIC-BUILD.md](docs/CI-PUBLIC-BUILD.md)** explains what a run proves, which log messages are normal noise, and what the limits are.
- **Want to build it yourself locally / contribute?** Read **[docs/DEV-SETUP.md](docs/DEV-SETUP.md)** — it walks you from fetching the upstream source + toolchains, applying `patches/`, through the build and verification (including every trap we hit). The AI Advisor is compiled in or out via the `RTCONFIG_REAPER_MCP` build flag.

## Base & status

- Commands: what each build/cut/verify script does, and what a fork can run — [`docs/COMMANDS.md`](docs/COMMANDS.md).
- Base: Asuswrt-Merlin **3006.102.8** (patches apply on tag `3006.102.8-beta2`; the sibling-model strip is optional — see [`patches/README.md`](patches/README.md)).
- Current version: **v2.8.8** <!--@pubver--> (firmware line `3006.102.8_Reaper_v<version>`) — *current* means the newest
  **published release**, i.e. the newest image you can actually download from
  [Releases](https://github.com/TheUnboundDeveloper/AM-Reaper/releases), for all six models
  (published 2026-08-28 <!--@pubdate-->). The **RT-BE92U** (BCM6765) ships as an experimental prerelease.
  Source rungs are cut more often than releases are published (many rungs — e.g. v2.6.1–v2.6.9, v2.7.0,
  v2.7.2 — exist in the patch series but were never published), so the source tree (**v3.1.0** <!--@treever-->) is normally
  ahead of this number. Every rung is built on the RT-BE96U and must pass the release gate (`reaper_verify`, the
  static checks and the patch-marker manifest) before it is cut; the maintainer's RT-BE96U runs each rung on metal,
  and the OpenSSL 3.5 move was validated there before its cut. The four BCM4916 siblings and the RT-BE92U are built
  clean-room in CI from the same patch series plus their identity overlays; on-metal validation is owed on them.

## Legal

- **GPL:** the GPL portions are under GPL v2 ([`LICENSE`](LICENSE)); the Reaper modifications are likewise GPL v2, with a Reaper-specific notice in [`LICENSE.reaper`](LICENSE.reaper). Publish your changes if you redistribute the GPL code.
- **Proprietary components** (ASUS / Broadcom / Trend Micro / Tuxera) are **licensed for genuine ASUS hardware only** ([`docs/README.proprietary`](docs/README.proprietary)) and are intentionally **not** included here. This fork targets the ASUS RT-BE Series (RT-BE96U / RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro on BCM4916, plus the newer RT-BE92U on BCM6765).
- **No warranty:** provided as-is; keep a recovery path ready when flashing. See the Disclaimer above for redistribution and support terms.

Security reports: see [SECURITY.md](SECURITY.md). Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md).
