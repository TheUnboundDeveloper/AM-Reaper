# RT-BEXXU "Reaper" — Project Overview

> **Doc status:** current as of **v2.8.4** · 2026-08-27 <!--@stamp-->

A security-hardened, **de-clouded** fork of **Asuswrt-Merlin** for the **ASUS RT-BE Series** (WiFi 7 / Broadcom), firmware line **3006.102.x**. The **RT-BEXXU** is the primary, hardware-validated model; the **RT-BE86U**, **RT-BE88U**, **GT-BE98**, and **GT-BE98 Pro** (BCM4916) are built from per-model branches of the same tree, with the newer **RT-BE92U** (BCM6765) as an experimental sixth model. Current version **v2.8.3** <!--@pubver--> — the newest **published** release (2026-08-27 <!--@pubdate-->), on all five main models plus the RT-BE92U, both variants each. The source tree is normally ahead of that: it currently sits at **v2.8.4** <!--@treever--> (RT-BE96U; the RT-BE92U's images are published as experimental prereleases). "Current version" always means the newest published release — the newest image a user can actually install — because source rungs are cut more often than releases are published. See [`CHANGELOG.md`](CHANGELOG.md) and [`RELEASE-NOTES.md`](RELEASE-NOTES.md).

> This file is the **collapsed, project-relevant** version of the documentation that shipped with the upstream tree. The retained upstream originals are preserved verbatim for reference and GPL compliance: the GPL text as [`LICENSE`](../LICENSE) at the repo root, `README.proprietary` and `ASUS-Merlin_Changelog-3006.txt` in this `docs/` folder.

---

## What this is

- **Base:** Asuswrt-Merlin (`RMerl/asuswrt-merlin.ng`), itself an enhanced fork of ASUS's stock Asuswrt firmware.
- **This fork's goal:** take the RT-BE Series slice of that tree, **harden the open-source userspace** against remote/network compromise, and produce flashable images that can be distributed to other security-conscious BE-series owners — free of charge.
- **Threat-model north star:** only **physical access** should be able to compromise the device. Eliminate remotely/LAN-reachable compromise (command injection, buffer overflows from network/nvram/WAN input, format strings, auth bypass). The hardening is invisible in normal use — its benefit is reduced attack surface.
- **Also de-cloud:** remove AI-branded and cloud-coupled surface (Alexa/Google Assistant, Trend Micro DPI, AiCloud/WebDAV, the AiDisk wizard, the AAE cloud tunnel, the first-boot consent screens) so the base image stays lean, local-only, and auditable.
- **And add genuinely-local features:** two Hardware QoS engines that keep the flow accelerator on, a native Traffic Analyzer, an **optional, read-only, LAN-only AI Advisor** (compiled out of the Standard build entirely; with an opt-in, per-session bounded network-diagnostics mode), **on-router network diagnostics** — ping/traceroute/DNS/netstat via the AI Advisor — a one-click sanitized **Reaper Diagnostics** report, and **Gatekeeper**, an opt-in, default-deny, on-router device access control (v1.7).
- **Branding:** `reaper`. The build version reads `<MODEL> 3006.102.8_Reaper_v<X>` (e.g. `RT-BEXXU …_Reaper_v2.5.3`).

## Scope & hard rules

- **Six-model RT-BE fleet.** RT-BEXXU is primary and hardware-validated; the four BCM4916 siblings and the newer BCM6765 **RT-BE92U** build from per-model branches of the same tree. Built from `release/src-rt-5.04behnd.4916` via `make <target>` (`rt-BEXXU` / `rt-be86u` / `rt-be88u` / `gt-be98` / `gt-be98_pro` / `rt-be92u`). Each model ships two variants (Standard / + AI Advisor).
- **The vendor tree is never redistributed.** The hardening is maintained as patches (this repo's `patches/`) on top of the upstream `3006.102.8-beta2` tag; the multi-GB source checkout stays local to each developer.
- **Don't modify the closed blobs.** Broadcom WiFi drivers and prebuilt objects (`wl`/`dhd`, `eapd`, `acsd`, `networkmap`, `wlceventd`, `cfg_mnt`, `spwenc`, the Broadcom `hostapd`/`wpa_supplicant` forks) are out of scope and treated as documented residual risk. Harden the userspace around them.

## Relationship to upstream Asuswrt-Merlin

Most of the source we patch is **shared across many Broadcom-HND Merlin models**, so the flaws we fix generally exist on those models' stock firmware too — and Reaper images are produced for the RT-BE Series (RT-BEXXU primary, plus the four BCM4916 siblings and the newer BCM6765 RT-BE92U). We track the **3006.102.x** line (checked out at tag `3006.102.8-beta2`). Upstream project, wiki, and support:

- Source/wiki: <https://github.com/RMerl/asuswrt-merlin.ng>
- Support forum (upstream, for *stock* Merlin — not this fork): SNBForums

## Relevant stock features (already in the build)

Carried over from Asuswrt-Merlin and present in the BEXXU image: user scripts (firewall/services events), cron, customizable service configs, **Entware** add-on support (via `amtm`), `nano`, NTP daemon, SNMP, OpenVPN client/server (hardened here) + WireGuard + IPsec/strongSwan, **VPN Director** policy routing, **DNS Director**, **Cake SQM QoS**, Tor, ipset, USB sharing (Samba/minidlna/vsftpd/AFP), traffic stats.

**Reaper adds** (see [`RELEASE-NOTES.md`](RELEASE-NOTES.md) / [`CHANGELOG.md`](CHANGELOG.md)): Hardware QoS (`qos_type=10` and the `qos_type=11` Classful engine, plus v3/v4 aggregate cap, minimums, DSCP, WRR, L4S) with the flow accelerator left on; a native **Traffic Analyzer** (per-device/network/class history, live view, quota); a **Wireless diagnostics** page with Channel-Quality Auto Scan and an opt-in passive monitor; a one-click sanitized **Reaper Diagnostics** report; **Gatekeeper** (opt-in, default-deny, on-router device access control, v1.7); an **optional AI Advisor** (read-only LAN MCP server, off by default, present only in the `+ AI Advisor` build variant, with an opt-in per-session bounded network-diagnostics tier); and **on-router network diagnostics** — the AI Advisor's opt-in ping/traceroute/DNS/netstat probe tier. **Reaper removes** (de-cloud): Alexa/Google Assistant, the Trend Micro DPI engine (AiProtection / DPI Adaptive QoS / web history), AiCloud/WebDAV, the AiDisk cloud-share wizard, the AAE/AiHome cloud tunnel, and the first-boot EULA/consent surface.

## Security status

See [`REAPER-FIXES.md`](REAPER-FIXES.md) for the authoritative fix list (all audit rounds: command-injection, memory-safety, and defense-in-depth fixes across `httpd`, `rc`, `shared`, `libdisk`, `libovpn`, `snooper`, `urlfilterd`, `lltdc`, `wsdd2`, `infosvr`, `libcodb`, and more — all compile/link-verified). The prebuilt blobs remain a binary-RE-only coverage gap.

## Installation / flashing (summary)

Flash the **`…_nand_squashfs.pkgtb`** (firmware-only) image via **Administration → Firmware Upgrade**.
- First non-stock flash may need `nvram set DOWNGRADE_CHECK_PASS=1` over SSH first.
- Factory-reset is recommended when coming from much older firmware, another third-party firmware, or stock-with-VPN; do **not** reload a saved settings backup after a reset.
- You can return to stock anytime by flashing an official ASUS image. Recovery: ASUS Firmware Restoration tool / rescue mode, or the `…_loader.pkgtb`.

(Full upstream flashing/feature documentation: the [Asuswrt-Merlin wiki](https://github.com/RMerl/asuswrt-merlin.ng/wiki).)

## Legal

- **GPL:** the GPL portions are under the GPL (see [`LICENSE`](../LICENSE)). The Reaper modifications are likewise GPL v2, with a Reaper-specific notice in [`LICENSE.reaper`](../LICENSE.reaper). If you redistribute, publish your changes to the GPL code.
- **Proprietary components** (ASUS / Broadcom / Trend Micro / Tuxera and possibly others) are **licensed for use on genuine ASUS hardware only** — using them on other manufacturers' hardware is forbidden and may be illegal in your jurisdiction (see [`README.proprietary`](README.proprietary)). This fork is for the ASUS RT-BE Series; do not port the blobs elsewhere.
- **No warranty:** provided as-is. This is a community hardening effort with no guarantee — use at your own risk, and keep a recovery path ready when flashing.
- **Privacy:** the de-cloud work removed the AI-assistant, Trend Micro DPI, AiCloud, and AAE-tunnel telemetry/cloud paths. The scheduled new-firmware-availability check is now **default off** (no outbound update traffic unless you opt in; notification only, never auto-upgrade). The optional AI Advisor, when present and armed, talks only to *your* AI client on the LAN — the router itself sends nothing to any cloud and stores no API key.

## Credits

Built on the work of Eric Sauvageau (RMerlin) and the Asuswrt-Merlin project, ASUS's GPL release, and the broader OpenWrt/Tomato/DD-WRT lineage.
