# Security Policy

> **Doc status:** current as of **v3.1.6** · 2026-09-13 <!--@stamp-->

This project exists to harden the RT-BE Series firmware — **RT-BE96U** (primary, hardware-validated)
plus the **RT-BE86U**, **RT-BE88U**, **GT-BE98**, **GT-BE98 Pro** and **GT-BE19000** siblings
(BCM4916 / WiFi 7), so security reports are very welcome.

## Scope

- **In scope:** the changes in this repo — everything under [`patches/`](patches/) — and the published `reaper` images (GitHub Releases), including both build variants (Standard and `_MCP`). That includes regressions introduced by the hardening itself, and the Reaper-authored subsystems (Hardware QoS, Traffic Analyzer, and the optional read-only LAN-only AI Advisor / MCP server — its arming, LAN-only binding, token auth, and secret redaction are all fair game).
- **Out of scope:** bugs in stock Asuswrt-Merlin or ASUS's GPL drop that this project hasn't touched — report those upstream to [RMerl/asuswrt-merlin.ng](https://github.com/RMerl/asuswrt-merlin.ng/security) or ASUS. (If a stock bug is remotely/LAN-reachable on any RT-BE Series model, we still want to hear about it — fixing that class of bug is the point of this fork. Base-firmware findings are handled by coordinated disclosure; a recent example is the `openssl passwd` class-fix reported under ASUS PSIRT case 1006563.)
- The proprietary Broadcom/ASUS blobs are a documented residual risk (see [`docs/REAPER-FIXES.md`](docs/REAPER-FIXES.md)); reports there are appreciated but may only be addressable by mitigation, not by patching the blob.

## Reporting

Email **theunbounddeveloper@outlook.com** with:

- the affected patch/file or image version (`RT-BE96U_…_reaper_…`),
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
| **netatalk 3.0.5** (Time Machine) | AFP file sharing enabled | The 2022 set is now closed. CVE-2022-43634 (pre-authentication heap overflow in the DSI write path) was fixed in v3.1.5 with an adaptation of the vendor fix, correcting a 2026-08-30 finding that had called the set absent. The other three were re-read in code rather than by version and all three were present: CVE-2022-23125 (`copyapplfile()`) and CVE-2022-45188 (`afp_getappl()`) each read an attacker-controlled 16-bit length out of the Desktop DB appl file into a fixed buffer with no bounds check - stack and heap respectively - and CVE-2022-23121 (`parse_entries()`) both allowed the entry bounds test to integer-overflow and let a rejected entry be logged and skipped while the caller carried on with a header it believed had parsed. All three fixed. The 3.0.5-to-3.1.13 delta beyond this set is not backported, so MEDIUM residual when enabled. |
| **wpa_supplicant 0.6.10** | WAN 802.1X configured | A 2010 release, used only for wired WAN authentication, and the build narrows it sharply: `CONFIG_EAP_MD5` is the only EAP method compiled, `CONFIG_NO_WPA` / `CONFIG_NO_WPA2` leave out the 4-way handshake, and `CONFIG_NO_CONFIG_BLOBS` / `CONFIG_NO_CONFIG_WRITE` the blob parser. That puts the era's headline advisories outside the compiled surface rather than merely unreachable - the KRACK set needs the handshake code, the EAP fragment-reassembly overflows need the TLS-based methods, and the P2P/WPS bugs need code this build does not contain. What remains is the EAPOL state machine, EAP-MD5 and the wired driver, exposed to whatever authenticator the WAN port is plugged into. MEDIUM when configured. |
| **lighttpd 1.4.39** | Captive portal enabled | CVE-2018-25103 (folded-header use-after-free, pre-authentication on port 8083) fixed in v3.1.5. The rest of the 1.4.39-to-current delta is not backported; reachable only with the captive portal or Chillispot switched on. Three of the commonly cited later advisories were checked against this build and do not apply: `mod_extforward` is not compiled (CVE-2022-22707), CVE-2019-11072 was introduced after 1.4.39, and CVE-2018-19052 needs an alias whose target is a directory while every alias the portal emits points at a single file. |
| **net-snmp 5.9.4.pre2** | SNMP with a read-write community | CVE-2022-44792 / -44793 fixed in v3.1.5 (a SET carrying a NULL varbind is rejected before dispatch). A read-only community never reached them. |
| **Quagga 0.99.24** (zebra) | Dynamic routing enabled | CVE-2016-1245 (stack overflow in the IPv6 router-advertisement read path - `rtadv_recv_packet()` was handed `BUFSIZ` as the size of a 4096-byte buffer) fixed with the upstream 0.99.24.1 change. Only `lib`, `zebra` and `ripd` are built; ospfd and bgpd are vendored but not compiled. The rest of the 0.99.24-to-1.x delta is not backported, and zebra runs only with `quagga_enable` set. |

A second review on 2026-09-12 (v3.1.5, adversarial, with a live-router observation) re-read each of these
in code rather than by version, which is how the netatalk correction above was found. The same round
backported the strongSwan 6.0.4 identity double free (CVE-2026-47895, IKEv2 EAP server), moved Tor to
its 2026-09-08 security release (0.4.9.12) and closed avahi's CNAME lookup crashes (CVE-2025-68468,
CVE-2025-68471, CVE-2026-24401).

A third pass on 2026-09-13 took the five entries above one at a time, again in code. It closed the
remaining netatalk 2022 set and CVE-2016-1245 in Quagga, and it retired two entries that had been
carried on their version alone: what the wpa_supplicant build actually compiles, and which later
lighttpd advisories reach this configuration. Both of those turned out narrower than the version
string suggests, which is the same lesson the netatalk correction taught in the other direction -
a version match is not a finding, and a version is not a clean bill of health either.

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
