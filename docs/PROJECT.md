# RT-BE96U "Reaper" — Project Overview

A security-hardened, single-model fork of **Asuswrt-Merlin** focused exclusively on the **ASUS RT-BE96U** (WiFi 7 / Broadcom BCM4916), firmware line **3006.102.x**.

> This file is the **collapsed, project-relevant** version of the documentation that shipped with the upstream tree. The retained upstream originals (`License`, `README.proprietary`, `Changelog-3006.txt`) are preserved verbatim in this `docs/` folder for reference and GPL compliance.

---

## What this is

- **Base:** Asuswrt-Merlin (`RMerl/asuswrt-merlin.ng`), itself an enhanced fork of ASUS's stock Asuswrt firmware.
- **This fork's goal:** take the BE96U slice of that tree, **harden the open-source userspace** against remote/network compromise, and produce a flashable image that can be distributed to other security-conscious BE96U owners — free of charge.
- **Threat-model north star:** only **physical access** should be able to compromise the device. Eliminate remotely/LAN-reachable compromise (command injection, buffer overflows from network/nvram/WAN input, format strings, auth bypass). The hardening is invisible in normal use — its benefit is reduced attack surface.
- **Branding:** `reaper`. The build version reads `…_beta2-g<commit>` (or `…_beta2-reaper` if forced).

## Scope & hard rules

- **One model: RT-BE96U.** The tree was stripped of the other BE sibling models; built from `release/src-rt-5.04behnd.4916`, target `rt-be96u`.
- **Never push.** Work lives on the local `be96u-only` branch; `origin` is the upstream/mirror.
- **Don't modify the closed blobs.** Broadcom WiFi drivers and prebuilt objects (`wl`/`dhd`, `eapd`, `acsd`, `networkmap`, `wlceventd`, `cfg_mnt`, `spwenc`, the Broadcom `hostapd`/`wpa_supplicant` forks) are out of scope and treated as documented residual risk. Harden the userspace around them.

## Relationship to upstream Asuswrt-Merlin

Most of the source we patch is **shared across many Broadcom-HND Merlin models**, so the flaws we fix generally exist on those models' stock firmware too — but this hardened image is produced for the RT-BE96U exclusively. We track the **3006.102.x** line (checked out at tag `3006.102.8-beta2`). Upstream project, wiki, and support:

- Source/wiki: <https://github.com/RMerl/asuswrt-merlin.ng>
- Support forum (upstream, for *stock* Merlin — not this fork): SNBForums

## Relevant stock features (already in the build)

Carried over from Asuswrt-Merlin and present in the BE96U image: user scripts (firewall/services events), cron, customizable service configs, **Entware** add-on support (via `amtm`), `nano`, NTP daemon, SNMP, OpenVPN client/server (hardened here) + WireGuard + IPsec/strongSwan, **VPN Director** policy routing, **DNS Director**, **Cake SQM QoS**, Tor, ipset, USB sharing (Samba/minidlna/vsftpd/AFP), traffic stats. See [`ENTERPRISE-ROADMAP.md`](../ENTERPRISE-ROADMAP.md) for what's in-tree-but-not-yet-enabled and what's worth adding.

## Security status

See [`REAPER-FIXES.md`](../REAPER-FIXES.md) for the authoritative fix list (Round 1 + Round 2: command-injection, memory-safety, and defense-in-depth fixes across `httpd`, `rc`, `shared`, `libdisk`, `libovpn`, `snooper`, `urlfilterd`, `lltdc`, `wsdd2`, `infosvr`, `libcodb`, and more — all compile/link-verified). The prebuilt blobs remain a binary-RE-only coverage gap.

## Installation / flashing (summary)

Flash the **`…_nand_squashfs.pkgtb`** (firmware-only) image via **Administration → Firmware Upgrade**.
- First non-stock flash may need `nvram set DOWNGRADE_CHECK_PASS=1` over SSH first.
- Factory-reset is recommended when coming from much older firmware, another third-party firmware, or stock-with-VPN; do **not** reload a saved settings backup after a reset.
- You can return to stock anytime by flashing an official ASUS image. Recovery: ASUS Firmware Restoration tool / rescue mode, or the `…_loader.pkgtb`.

(Full upstream flashing/feature documentation: the [Asuswrt-Merlin wiki](https://github.com/RMerl/asuswrt-merlin.ng/wiki).)

## Legal

- **GPL:** the GPL portions are under the GPL (see [`License`](License)). If you redistribute, publish your changes to the GPL code.
- **Proprietary components** (ASUS / Broadcom / Trend Micro / Tuxera and possibly others) are **licensed for use on genuine ASUS hardware only** — using them on other manufacturers' hardware is forbidden and may be illegal in your jurisdiction (see [`README.proprietary`](README.proprietary)). This fork is for the RT-BE96U; do not port the blobs elsewhere.
- **No warranty:** provided as-is. This is a community hardening effort with no guarantee — use at your own risk, and keep a recovery path ready when flashing.
- **Privacy:** the only automatic phone-home in the base firmware is the new-version availability check, which can be disabled in the webui (Administration → Firmware Upgrade → auto-check off).

## Credits

Built on the work of Eric Sauvageau (RMerlin) and the Asuswrt-Merlin project, ASUS's GPL release, and the broader OpenWrt/Tomato/DD-WRT lineage.
