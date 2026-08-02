# Third-Party Notices

Reaper is a derivative of Asuswrt-Merlin / ASUS's GPL firmware and redistributes,
or builds against, third-party components. This file lists the third-party
material that ships in a Reaper firmware image and the license under which each
is included. It complements [`LICENSE`](LICENSE) (GPL v2, the primary license),
[`LICENSE.reaper`](LICENSE.reaper) (Reaper's own work), and
[`docs/SOURCE-AVAILABILITY.md`](docs/SOURCE-AVAILABILITY.md) (GPL source offer).

---

## 1. Reaper-added components

### Web fonts — SIL Open Font License 1.1
Added by the Reaper UI (patch `0041`); embedded via `@font-face` in the Reaper
pages. Full license text: [`LICENSES/OFL-1.1.txt`](LICENSES/OFL-1.1.txt).

| Font | Files | Copyright | License |
|---|---|---|---|
| **Inter** | `www/fonts/inter-400.woff2`, `inter-500.woff2`, `inter-600.woff2` | The Inter Project Authors (<https://github.com/rsms/inter>) | OFL 1.1 |
| **Rajdhani** | `www/fonts/rajdhani-500.woff2`, `rajdhani-600.woff2`, `rajdhani-700.woff2` | the Indian Type Foundry | OFL 1.1 |

> OFL 1.1 §2 requires the license to travel *with* the font files. Satisfied in
> **both** the source (this repo's [`LICENSES/OFL-1.1.txt`](LICENSES/OFL-1.1.txt))
> and the **built image** — patch `0152` (v1.5.0c) installs the OFL text as
> `www/fonts/OFL.txt`, verified present in the staged image.

### Other Reaper assets
- `www/images/REAPER.png`, `www/images/New_ui/rt_reaper.png`, `www/favicon.ico`,
  `www/images/New_ui/networkmap/white_05.gif` — project artwork supplied by the
  maintainer. See [`LICENSE.reaper`](LICENSE.reaper) § 3(c) (name/logo).
- `www/images/ASUSLogo.png` (patch `0144`) — an **ASUS-branded** asset. Flagged
  for trademark review.

### Reaper-added / upgraded software packages

Software components that Reaper **introduces or version-upgrades** beyond the
upstream tree and that ship in the built image, with the license each carries:

| Component | Version (from) | Introduced by | License |
|---|---|---|---|
| **Samba** | 4.15.13a (from upstream 3.6.25) | patches `0225`, `0234` (CVE-2025-9640 backport) | **GPL v3** ([`LICENSES/GPL-3.0.txt`](LICENSES/GPL-3.0.txt)) — the SMB3 file server (RT-BE96U). A **GPLv3** component in the image; complete corresponding source + the GPL v3 § 6 "Installation Information" are provided per [`docs/SOURCE-AVAILABILITY.md`](docs/SOURCE-AVAILABILITY.md) § 5 (buildable + flashable source: `patches/` + [`build-scripts/`](build-scripts/)). |
| **OpenSSH** `sftp-server` | 9.8p1 (sftp-server target only) | patch `0222` | BSD / ISC ([`LICENSES/OpenSSH.txt`](LICENSES/OpenSSH.txt)) |
| **net-snmp** | 5.9.4 (from upstream 5.7.2) | patch `0223` | Net-SNMP license, BSD-style ([`LICENSES/Net-SNMP.txt`](LICENSES/Net-SNMP.txt)) |
| **avahi** | 0.8 (CVE-backport into the upstream avahi) | patch `0071` | LGPL v2.1-or-later ([`LICENSES/LGPL-2.1.txt`](LICENSES/LGPL-2.1.txt)) |

Each package's own in-tree license text is present in the reconstructed source
tree (pinned upstream + `patches/`); see [`docs/SOURCE-AVAILABILITY.md`](docs/SOURCE-AVAILABILITY.md).

## 2. Upstream-bundled third-party libraries (from Asuswrt-Merlin / ASUS)

These are **not** Reaper additions; they arrive with the upstream tree and ship
with their own license files in-tree.

| Component | Path | License | Copyright |
|---|---|---|---|
| qrcode (jquery.qrcode) | `www/js/qrcode/` (`MIT-LICENSE.txt`) | MIT | © 2011 Jerome Etienne |
| jsTree | `www/js/jstree/` (`LICENSE-MIT`) | MIT | © 2014 Ivan Bozhanov |
| Roboto / ROG_Fonts / Xolonium fonts | `www/fonts/` | ASUS-supplied (upstream) | ASUS / respective foundries |

The wider upstream tree contains many additional open-source packages under a mix
of licenses: **GPL v2** (busybox, dnsmasq, iptables, hostapd, …), **GPL v3** (GNU
**wget**, GNU **nano**), **LGPL v2.1** (**glib**, **avahi**, **libdaemon**, …), and
BSD/MIT (openssl, net-snmp, …). Each retains its own in-tree license notice; the
full license texts are collected in [`LICENSES/`](LICENSES/) — [`GPL-3.0.txt`](LICENSES/GPL-3.0.txt),
[`LGPL-2.1.txt`](LICENSES/LGPL-2.1.txt), [`OFL-1.1.txt`](LICENSES/OFL-1.1.txt) (GPL v2
is the repo-root [`LICENSE`](LICENSE)) — mapped in [`LICENSES/README.md`](LICENSES/README.md),
and all are covered by the source availability in
[`docs/SOURCE-AVAILABILITY.md`](docs/SOURCE-AVAILABILITY.md).

## 3. Proprietary components — NOT redistributed by this repository

A compiled Reaper `.pkgtb` image depends on closed, proprietary components that
are **licensed for use on genuine ASUS hardware only** and are **not** included
in this repository. Per the upstream `README.proprietary`
([`docs/README.proprietary`](docs/README.proprietary)):

> This project contains proprietary components from ASUSTeK, Broadcom, Trend
> Micro and Tuxera (and possibly others). These components are only licensed for
> use on original ASUSTeK devices. Any use of these components on devices from
> other manufacturers is strictly forbidden…

| Family | Where (in the buildable upstream tree) |
|---|---|
| Broadcom WiFi drivers / RDP / platform daemons | `release/src-rt-5.04behnd.4916/{bcmdrivers,rdp,router-sysdep.<model>}` (e.g. `router-sysdep.rt-BEXXU`, one per RT-BE model) |
| ASUS closed prebuilt objects (auth/token core, `web_hook.o`, `spwenc`, …) | `release/src/router/{shared,httpd}/prebuild/` |
| Trend Micro DPI (`tdts*.ko`, `libshn_*.so`, signed rule/cert material) | `release/src/router/bwdpi_source/prebuild/` |
| Tuxera NTFS/exFAT kernel driver | `release/src/router/tuxera` (+ `ntfs-3g`) |

**These carry no redistribution grant.** This repository redistributes none of
them; they are obtained by the builder from the upstream source / ASUS GPL drop.
