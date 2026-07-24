# AM-Reaper

**Security-hardened, de-clouded [Asuswrt-Merlin](https://github.com/RMerl/asuswrt-merlin.ng) for the ASUS RT-BE Series** (WiFi 7 / Broadcom BCM4916), firmware line **3006.102.x** — branded `reaper`. Current: **v1.7.7**. Primary, hardware-validated model is the **RT-BE96U**; also built from per-model branches of the same tree for the **RT-BE86U**, **RT-BE88U**, **GT-BE98**, and **GT-BE98 Pro** (metal validation owed on all five).

The goal: harden the open-source userspace so that **only physical access** can compromise the device — eliminating remotely/LAN-reachable command injection, buffer overflows, format-string and auth-bypass bugs — remove cloud-coupled/AI-branded attack surface, and produce a flashable image that can be shared with other security-conscious BE-series owners.

> ~70+ security issues fixed across four audit rounds (command-injection, memory-safety, and defense-in-depth), each compile/link-verified by a full firmware build. See **[docs/REAPER-FIXES.md](docs/REAPER-FIXES.md)**. Version-by-version history: **[docs/CHANGELOG.md](docs/CHANGELOG.md)**.

Beyond hardening, Reaper adds router features ASUS never shipped — two **Hardware QoS** engines that keep the flow accelerator on, a native **Traffic Analyzer**, an **optional, read-only, LAN-only AI Advisor** (with an opt-in, bounded network-diagnostics mode), **on-router network diagnostics** (ping/traceroute/DNS/netstat via the AI Advisor), one-click sanitized **Reaper Diagnostics**, and **Gatekeeper** (opt-in, default-deny, on-router device access control) — and removes cloud/telemetry surface (Alexa/Google, Trend Micro DPI, AiCloud/WebDAV, the AAE cloud tunnel). See **[docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md)**.

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
- Root: [`LICENSE`](LICENSE) (GPL v2), [`LICENSE.reaper`](LICENSE.reaper) (the Reaper-specific notice), [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md), [`DEPENDENCIES.md`](DEPENDENCIES.md), [`LICENSES/`](LICENSES/) (license texts), plus `SECURITY.md` and `CONTRIBUTING.md`.
- **Compliance:** [`docs/SOURCE-AVAILABILITY.md`](docs/SOURCE-AVAILABILITY.md) (GPL source + written offer) and [`docs/COMPLIANCE-AUDIT-2026-07-13.md`](docs/COMPLIANCE-AUDIT-2026-07-13.md) (audit + remediation tracker). **Read the audit before making anything public.**

**Not in the repo (externally sourced — see [docs/DEV-SETUP.md](docs/DEV-SETUP.md) § "Get the inputs"):**
- The **upstream firmware source** — clone `RMerl/asuswrt-merlin.ng` at tag `3006.102.8-beta2`.
- The **proprietary Broadcom/ASUS/Trend Micro/Tuxera components** — licensed for ASUS hardware only; they come with the upstream source / ASUS GPL drop, never redistributed here.
- The **toolchains** — gcc-10.3 ARM/aarch64 from `RMerl/am-toolchains`.
- The **flashable `.pkgtb` images** — build artifacts, **not publicly hosted**; available **on request**, delivered with the complete corresponding source (see [docs/SOURCE-AVAILABILITY.md](docs/SOURCE-AVAILABILITY.md) § 3, *Requesting a build*).

## Documentation — read in this order

1. **[docs/PROJECT.md](docs/PROJECT.md)** — what this fork is, scope, hard rules, threat model, flashing, legal. (The collapsed version of the upstream READMEs.)
2. **[docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md)** — what the current release contains, the two build variants, and how to flash it.
3. **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — big changes per version, v1.0 → v1.7.7.
4. **[docs/DEV-SETUP.md](docs/DEV-SETUP.md)** — the hard-won contributor build/edit environment: WSL 20.04, gcc-10.3 toolchains, host deps, the build recipe and its traps, the editing/tooling gotchas, and how to verify a change. **If you want to build or patch the firmware, this is the one.**
5. **[docs/REAPER-FIXES.md](docs/REAPER-FIXES.md)** — authoritative list of every security fix applied (all audit rounds), with commits.
6. **[docs/GPL-MERGE.md](docs/GPL-MERGE.md)** — maintainer guide for rebasing the hardening onto a new upstream/GPL drop.
7. **[docs/ENTERPRISE-ROADMAP.md](docs/ENTERPRISE-ROADMAP.md)** — package-update candidates and feature ideas (what's in-tree-but-disabled, what to add via Entware).
8. **[patches/](patches/)** — the hardening itself, as patches you apply onto an upstream checkout.

Retained upstream originals kept for reference: `docs/README.proprietary` (the blob-licensing notice, summarized in `PROJECT.md` § Legal) and `docs/Changelog-3006.txt` (upstream 3006.102 history; Reaper's own history is in [docs/CHANGELOG.md](docs/CHANGELOG.md)). The other upstream READMEs (generic multi-model build notes, stale project blurbs, upstream support pointers) were out of date for this RT-BE-series fork; their still-relevant content was folded into `PROJECT.md` / `DEV-SETUP.md`.

## Quick start

- **Just want to flash it?** Builds are **available on request** (not publicly hosted) and come with the complete corresponding source — see [docs/SOURCE-AVAILABILITY.md](docs/SOURCE-AVAILABILITY.md) § 3 for the **request format**. There are **two variants** — a **Standard** image and an **AI Advisor** (`…_MCP`) image that adds the optional MCP server (off by default). First non-stock flash needs `nvram set DOWNGRADE_CHECK_PASS=1` (see [docs/PROJECT.md](docs/PROJECT.md) § Installation); flash via *Administration → Firmware Upgrade*.
- **Want to build it yourself / contribute?** Read **[docs/DEV-SETUP.md](docs/DEV-SETUP.md)** — it walks you from fetching the upstream source + toolchains, applying `patches/`, through the build and verification (including every trap we hit). The AI Advisor is compiled in or out via the `RTCONFIG_REAPER_MCP` build flag.

## Base & status

- Base: Asuswrt-Merlin **3006.102.8** (patches apply on tag `3006.102.8-beta2`; the sibling-model strip is optional — see [`patches/README.md`](patches/README.md)).
- Current version: **v1.7.7** (firmware line `3006.102.8_Reaper_v1.7.7`). Everything through v1.5.6 is validated on the physical RT-BE96U (security hardening rounds 1–4, the Hardware QoS engines, Traffic Analyzer, the de-cloud removals, the AI Advisor + its network-diagnostics tier, and the Reaper UI). The v1.6 line (hardening pass + full 24-language UI, QoS tuning, Channel-Quality Auto Scan / passive monitor, Reaper Diagnostics) and the **v1.7** line (v1.7.0/v1.7.3 **Gatekeeper** device access control; v1.7.1/v1.7.5 security remediation + the PSIRT `openssl passwd` class-fix; v1.7.2 AiMesh onboarding fix + full-menu i18n; v1.7.4 static-DHCP picker + theme-flash fixes; v1.7.6/v1.7.7 VPN-page + Network-Map polish) are built and shipped for all five models in both variants (20 images on 2026-07-24); metal validation is owed on every model. Per-version history: [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Legal

- **GPL:** the GPL portions are under GPL v2 ([`LICENSE`](LICENSE)); the Reaper modifications are likewise GPL v2, with a Reaper-specific notice in [`LICENSE.reaper`](LICENSE.reaper). Publish your changes if you redistribute the GPL code.
- **Proprietary components** (ASUS / Broadcom / Trend Micro / Tuxera) are **licensed for genuine ASUS hardware only** ([`docs/README.proprietary`](docs/README.proprietary)) and are intentionally **not** included here. This fork targets the ASUS RT-BE Series (RT-BE96U / RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro), all BCM4916.
- **No warranty:** provided as-is; keep a recovery path ready when flashing. See the Disclaimer above for redistribution and support terms.

Security reports: see [SECURITY.md](SECURITY.md). Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md).
