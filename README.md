# AM-Reaper

**Security-hardened, de-clouded [Asuswrt-Merlin](https://github.com/RMerl/asuswrt-merlin.ng) for the ASUS RT-BE Series** (WiFi 7 / Broadcom BCM4916), firmware line **3006.102.x** — branded `reaper`. Current: **v2.1.4**. Primary, hardware-validated model is the **RT-BEXXU**; also built from per-model branches of the same tree for the **RT-BE86U**, **RT-BE88U**, **GT-BE98**, and **GT-BE98 Pro** (metal validation owed on all five).

The goal: harden the open-source userspace so that **only physical access** can compromise the device — eliminating remotely/LAN-reachable command injection, buffer overflows, format-string and auth-bypass bugs — remove cloud-coupled/AI-branded attack surface, and produce a flashable image that can be shared with other security-conscious BE-series owners.

> ~70+ security issues fixed across four audit rounds (command-injection, memory-safety, and defense-in-depth) at v1.0, plus a later multi-agent **audit-remediation arc** (73 verified findings closed across v1.8.2–v1.8.6) — each compile/link-verified by a full firmware build. See **[docs/REAPER-FIXES.md](docs/REAPER-FIXES.md)**. Version-by-version history: **[docs/CHANGELOG.md](docs/CHANGELOG.md)**.

Beyond hardening, Reaper adds router features ASUS never shipped — two **Hardware QoS** engines that keep the flow accelerator on, a native **Traffic Analyzer**, an **optional, read-only, LAN-only AI Advisor** (with an opt-in, bounded network-diagnostics mode), **on-router network diagnostics** (ping/traceroute/DNS/netstat via the AI Advisor), one-click sanitized **Reaper Diagnostics**, **Gatekeeper** (opt-in, default-deny, on-router device access control), **Reaper Warden** (opt-in threat/geo firewall — ipset threat feeds + by-country blocking, IPv6 dual-stack, strict anti-lockout), and a **Device Identity Manager** (a per-device "Devices" page unifying name, reservation, access state, and presence) — and removes cloud/telemetry surface (Alexa/Google, Trend Micro DPI, AiCloud/WebDAV, the AAE cloud tunnel). See **[docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md)**.

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
- **Compliance:** [`docs/SOURCE-AVAILABILITY.md`](docs/SOURCE-AVAILABILITY.md) (GPL source + written offer).

**Not in the repo (externally sourced — see [docs/DEV-SETUP.md](docs/DEV-SETUP.md) § "Get the inputs"):**
- The **upstream firmware source** — clone `RMerl/asuswrt-merlin.ng` at tag `3006.102.8-beta2`.
- The **proprietary Broadcom/ASUS/Trend Micro/Tuxera components** — licensed for ASUS hardware only; they come with the upstream source / ASUS GPL drop, never redistributed here.
- The **toolchains** — gcc-10.3 ARM/aarch64 from `RMerl/am-toolchains`.
- The **flashable `.pkgtb` images** — build artifacts, **not publicly hosted**; available **on request**, delivered with the complete corresponding source (see [docs/SOURCE-AVAILABILITY.md](docs/SOURCE-AVAILABILITY.md) § 3, *Requesting a build*).

## Documentation — read in this order

1. **[docs/PROJECT.md](docs/PROJECT.md)** — what this fork is, scope, hard rules, threat model, flashing, legal. (The collapsed version of the upstream READMEs.)
2. **[docs/RELEASE-NOTES.md](docs/RELEASE-NOTES.md)** — what the current release contains, the two build variants, and how to flash it.
3. **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — big changes per version, v1.0 → the current release.
4. **[docs/DEV-SETUP.md](docs/DEV-SETUP.md)** — the hard-won contributor build/edit environment: WSL 20.04, gcc-10.3 toolchains, host deps, the build recipe and its traps, the editing/tooling gotchas, and how to verify a change. **If you want to build or patch the firmware, this is the one.**
5. **[docs/REAPER-FIXES.md](docs/REAPER-FIXES.md)** — authoritative list of every security fix applied (all audit rounds), with commits.
6. **[docs/GPL-MERGE.md](docs/GPL-MERGE.md)** — maintainer guide for rebasing the hardening onto a new upstream/GPL drop.
7. **[patches/](patches/)** — the hardening itself, as patches you apply onto an upstream checkout.

Retained upstream originals kept for reference: `docs/README.proprietary` (the blob-licensing notice, summarized in `PROJECT.md` § Legal) and `docs/ASUS-Merlin_Changelog-3006.txt` (upstream 3006.102 history; Reaper's own history is in [docs/CHANGELOG.md](docs/CHANGELOG.md)). The other upstream READMEs (generic multi-model build notes, stale project blurbs, upstream support pointers) were out of date for this RT-BE-series fork; their still-relevant content was folded into `PROJECT.md` / `DEV-SETUP.md`.

## Quick start

- **Just want to flash it?** Builds are **available on request** (not publicly hosted) and come with the complete corresponding source — see [docs/SOURCE-AVAILABILITY.md](docs/SOURCE-AVAILABILITY.md) § 3 for the **request format**. There are **two variants** — a **Standard** image and an **AI Advisor** (`…_MCP`) image that adds the optional MCP server (off by default). First non-stock flash needs `nvram set DOWNGRADE_CHECK_PASS=1` (see [docs/PROJECT.md](docs/PROJECT.md) § Installation); flash via *Administration → Firmware Upgrade*.
- **Want to build it yourself / contribute?** Read **[docs/DEV-SETUP.md](docs/DEV-SETUP.md)** — it walks you from fetching the upstream source + toolchains, applying `patches/`, through the build and verification (including every trap we hit). The AI Advisor is compiled in or out via the `RTCONFIG_REAPER_MCP` build flag.

## Base & status

- Base: Asuswrt-Merlin **3006.102.8** (patches apply on tag `3006.102.8-beta2`; the sibling-model strip is optional — see [`patches/README.md`](patches/README.md)).
- Current version: **v2.1.4** (firmware line `3006.102.8_Reaper_v2.1.4`). Everything through v1.5.6 is validated on the physical RT-BEXXU (security hardening rounds 1–4, the Hardware QoS engines, Traffic Analyzer, the de-cloud removals, the AI Advisor + its network-diagnostics tier, and the Reaper UI); later rungs are built + shipped with on-metal validation owed. The **v1.6–v1.7** lines added the full 24-language UI, QoS tuning, Channel-Quality Auto Scan, Reaper Diagnostics, **Gatekeeper** device access control, and the PSIRT `openssl passwd` class-fix. The **v1.8** line added **Reaper Warden** (threat/geo firewall — IPv6 dual-stack + per-country block stats + the `rwatch` health watchdog), the **Samba 4.15.13a** SMB3 file server with a backported CVE fix, and a multi-agent **audit-remediation arc** (73 verified findings closed across v1.8.2–v1.8.6). The **v1.9** line added the **Device Identity Manager** ("Devices" page + unified storage), first-boot credential enforcement, and the Traffic Analyzer per-network/Router accuracy fix. **v2.0.0** is a security-hardening milestone: two full end-to-end audits (all Reaper-authored code, plus the inherited ASUS/Merlin open source Reaper ships) with every finding fixed and no critical or high-severity flaw left open — stored-XSS neutralization of device-supplied names across the admin UI, a USB volume-label root-injection fix, config-DB/VPN-page injection + overflow hardening, CSRF-token enforcement on the live diagnostics tools, and internal-TLS certificate verification. The **v2.0.x → v2.1.0** line completed the de-cloud (ASUS AWS-IoT / account-binding removal), fixed and shipped the **Samba 4** file server, set **secure factory defaults** (WPS + UPnP off), added the **Hardware QoS Diagnostics** and **Connections flow-explorer** pages, and closed with a **pre-release code-review hardening pass** (six-agent audit; no critical/high). The **v2.1.x** line added full localization of the last hardcoded strings and a defense-in-depth pass (**v2.1.1**), carried forward the final **Asuswrt-Merlin 3006.102.8** upstream fixes incl. **OpenVPN 2.7.5** (**v2.1.2**), added the Connections **"Quick Look"** view, **RFC 4638 baby-jumbo PPPoE MTU**, and closed an apostrophe-in-name **stored-XSS** hole in the stock client list (**v2.1.3**), and fixed a **factory-reset credential lockout**, a WireGuard peer-row UI clip, and the OpenVPN version-label (which had shown 2.7.4 for the 2.7.5 binary) (**v2.1.4**). **Model scope:** the full five-model fleet (RT-BEXXU / RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro) was built + shipped through **v2.1.2**, both variants each and all passing the 17-check verify gate; **RT-BEXXU is at v2.1.4** and the v2.1.3/v2.1.4 sibling fan-out is in progress. On-metal validation is owed on all; RT-BEXXU remains the primary, hardware-validated build. Per-version history: [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Legal

- **GPL:** the GPL portions are under GPL v2 ([`LICENSE`](LICENSE)); the Reaper modifications are likewise GPL v2, with a Reaper-specific notice in [`LICENSE.reaper`](LICENSE.reaper). Publish your changes if you redistribute the GPL code.
- **Proprietary components** (ASUS / Broadcom / Trend Micro / Tuxera) are **licensed for genuine ASUS hardware only** ([`docs/README.proprietary`](docs/README.proprietary)) and are intentionally **not** included here. This fork targets the ASUS RT-BE Series (RT-BEXXU / RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro), all BCM4916.
- **No warranty:** provided as-is; keep a recovery path ready when flashing. See the Disclaimer above for redistribution and support terms.

Security reports: see [SECURITY.md](SECURITY.md). Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md).
