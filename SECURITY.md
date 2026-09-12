# Security Policy

> **Doc status:** current as of **v3.1.0** · 2026-09-08 <!--@stamp-->

This project exists to harden the RT-BE Series firmware — **RT-BEXXU** (primary, hardware-validated)
plus the **RT-BE86U**, **RT-BE88U**, **GT-BE98**, **GT-BE98 Pro** and **GT-BE19000** siblings
(BCM4916 / WiFi 7) and the dormant **RT-BE92U** (BCM6765), so security reports are very welcome.

## Scope

- **In scope:** the changes in this repo — everything under [`patches/`](patches/) — and the published `reaper` images (GitHub Releases), including both build variants (Standard and `_MCP`). That includes regressions introduced by the hardening itself, and the Reaper-authored subsystems (Hardware QoS, Traffic Analyzer, and the optional read-only LAN-only AI Advisor / MCP server — its arming, LAN-only binding, token auth, and secret redaction are all fair game).
- **Out of scope:** bugs in stock Asuswrt-Merlin or ASUS's GPL drop that this project hasn't touched — report those upstream to [RMerl/asuswrt-merlin.ng](https://github.com/RMerl/asuswrt-merlin.ng/security) or ASUS. (If a stock bug is remotely/LAN-reachable on any RT-BE Series model, we still want to hear about it — fixing that class of bug is the point of this fork. Base-firmware findings are handled by coordinated disclosure; a recent example is the `openssl passwd` class-fix reported under ASUS PSIRT case 1006563.)
- The proprietary Broadcom/ASUS blobs are a documented residual risk (see [`docs/REAPER-FIXES.md`](docs/REAPER-FIXES.md)); reports there are appreciated but may only be addressable by mitigation, not by patching the blob.

## Reporting

Email **theunbounddeveloper@outlook.com** with:

- the affected patch/file or image version (`RT-BEXXU_…_reaper_…`),
- reproduction steps or a PoC,
- whether the issue is reachable from WAN, LAN, or only with authentication.

Please use email rather than a public issue for anything exploitable. You'll get a response as soon as practical; fixes land as new numbered patches and a new release image.

## Known limitations — inherited components

Components inherited from the ASUS/Merlin base that carry unfixed advisories. Each is **off by
default**: none is reachable on a factory-configured router, and the entry states what turning it on
exposes. Listed here rather than silently carried, on the same principle as the bundled Samba, which
remains on its EOL branch with its one flagged CVE backported and build-gated.

A dedicated inherited-component review on 2026-08-30 (v2.9.4 staged rootfs, every finding re-derived
from the staged filesystem, the vendored source and the CVE record) found **no reachable HIGH, and
nothing reachable at MEDIUM with factory defaults**. The default-on surface — dnsmasq, avahi, lldpd,
Samba (SMB2/3, LAN-only), busybox udhcpc/ntpd, and the TLS stack — carries its fixes.

| Component | Exposed when | Assessment |
|---|---|---|
| **netatalk 3.0.5** (Time Machine) | AFP file sharing enabled | The 2022 pre-auth RCE set (CVE-2022-23125, -45188, -43634, -23121) was checked **in code and is absent** in this version's paths. MEDIUM residual when enabled. |
| **wpa_supplicant 0.6.10** | WAN 802.1X configured | A 2010 release, used only for wired WAN authentication. MEDIUM when configured. |
| **lighttpd 1.4.39** | Captive portal enabled | CVE-2018-25103, pre-authentication on port 8083, reachable only with the captive portal or Chillispot switched on. |
| **net-snmp 5.9.4.pre2** | SNMP with a read-write community | CVE-2022-44792 / -44793. A read-only community does not reach them. |
| **Quagga 0.99.24** (zebra) | Dynamic routing enabled | CVE-2016-1245. |

If any of these is upgraded it gets its own release and hardware validation rather than riding along
with unrelated work — the versions are load-bearing for the features that use them.

### Update-manifest signature

The firmware update check verifies its manifest by **HTTPS with certificate validation, a pinned
GitHub host, and a SHA-256 over the image** — not by a cryptographic signature over the manifest
itself. Signing was implemented and is present but deliberately left inert. The residual risk this
accepts is a compromise of the publishing GitHub account, which the other four checks do not cover.
This is a recorded, accepted trade rather than an oversight.

## Threat model

The project's bar: **only physical access should be able to compromise the device.** Anything remotely or LAN-reachable that breaks that bar is a valid, wanted report — see [`docs/PROJECT.md`](docs/PROJECT.md) for the full threat model.
