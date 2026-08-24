# Source Availability & Written Offer (GPL v2 & v3)

This document is how **Reaper** satisfies the "complete corresponding source"
obligation of the GNU General Public License — **version 2** for the base and the
bulk of the firmware (see [`../LICENSE`](../LICENSE)), and **version 3** for the
GPLv3 components it bundles (Samba, GNU wget, GNU nano — see § 5) — for every
GPL-covered portion of the firmware.

Read this together with [`../LICENSE.reaper`](../LICENSE.reaper) (what is and is not
Reaper's own work) and [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md)
(bundled third-party and proprietary components).

---

## 1. What the complete corresponding source is

The Reaper firmware is a derivative of Asuswrt-Merlin, which is a derivative of
ASUS's GPL firmware release. The **complete corresponding source** for the
GPL-covered portions of any Reaper build is, deterministically:

1. **The upstream Asuswrt-Merlin source**, at the exact pinned base:
   - Repository: <https://github.com/RMerl/asuswrt-merlin.ng>
   - Tag: `3006.102.8-beta2`
   - Commit: **`a7ebfa133a`**
   - (Equivalently, ASUS's own GPL source tarball for the applicable RT-BE
     model — RT-BEXXU / RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro / RT-BE92U — from
     <https://www.asus.com/support> provides the same GPL/Broadcom sources.)
2. **The Reaper patch series** in [`../patches/`](../patches/) — the full set of
   `git format-patch` files that transform the pinned upstream tree into the
   Reaper source tree, including all build scripts, Makefiles, and configuration
   changes needed to control compilation and installation.
3. **The build instructions** in [`DEV-SETUP.md`](DEV-SETUP.md) and the
   pinned build inputs (toolchain, host environment) in
   [`../DEPENDENCIES.md`](../DEPENDENCIES.md).

Applying the patch series to the pinned upstream commit reproduces the Reaper
source tree byte-for-byte under `release/src/router` (verified with
`git am --keep-cr`; see [`../patches/README.md`](../patches/README.md)). That
reconstructed tree, built per `DEV-SETUP.md`, is the complete corresponding
source for the GPL portions of the image.

**Per-release verification.** [`BUILD-PROVENANCE.md`](BUILD-PROVENANCE.md) and the
machine-readable [`../provenance/manifest.json`](../provenance/manifest.json) pin,
for each published image, the exact **Git tree hash** of `release/src/router` it
was built from, together with the image SHA-256 and the build/verification logs.
The [`verify-provenance`](../.github/workflows/verify-provenance.yml) CI workflow
re-derives that tree hash from the published patches on every run, so anyone can
confirm — automatically — that the published image corresponds to the published
source with nothing added or omitted.

> **Why patches instead of a source dump.** The full buildable tree (~10.6 GB)
> contains proprietary Broadcom/ASUS/Trend Micro/Tuxera components that are
> **licensed for use on genuine ASUS hardware only** and that this project has
> **no right to redistribute** (see [`README.proprietary`](README.proprietary)
> and [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md)). Pinning the exact
> public upstream commit and shipping the GPL delta as patches provides the
> complete corresponding source for the GPL parts **without** redistributing the
> proprietary parts. GPL v2's obligation attaches to the GPL-covered work.

---

## 2. Written Offer (GPL v2 §3(b))

> **The maintainer of Reaper offers, to any third party, for a period of at
> least three (3) years from the date on which any Reaper binary firmware image
> was last distributed, to provide a complete machine-readable copy of the
> complete corresponding source code for the GPL-covered portions of that image,
> under the terms of the GNU General Public License, version 2, for a charge no
> greater than the maintainer's actual cost of physically performing the source
> distribution.**
>
> To request source, open an issue on this repository, or email the project
> address in [`../SECURITY.md`](../SECURITY.md) / [`../LICENSE.reaper`](../LICENSE.reaper)
> with the subject line "GPL source request" and the exact version string of the
> image you received. The corresponding source is also published directly in
> this repository (upstream pin + `patches/`) per §1, which independently
> satisfies GPL v2 §3(a) for any recipient who obtains a binary accompanied by
> this repository.

This offer is honored regardless of whether ASUS or Asuswrt-Merlin ever
incorporate any change upstream. It is **not** conditioned on any future event.

---

## 3. Getting a build

Reaper firmware images are **publicly hosted in this GitHub repository.** A
flashable build for every model in the ASUS RT-BE Series (RT-BEXXU / RT-BE86U /
RT-BE88U / GT-BE98 / GT-BE98 Pro, plus the experimental RT-BE92U) is published two ways:

- the [**Releases**](https://github.com/TheUnboundDeveloper/AM-Reaper/releases)
  page — one per-model release per version (`v<version>-<MODEL>`), each carrying
  both variants plus a `SHA256SUMS-<MODEL>-<version>.txt`, and
- in-tree under [`../releases/`](../releases/)`<MODEL>/<MODEL>-REAPER-<version>/`
  for direct file-tree browsing, with the same checksums.

Each image is published **from the same repository as its complete corresponding
source** (§1: the `patches/` series against the pinned upstream commit, plus
`provenance/` tying each published image back to its source tree). Hosting the
binary and its source together is a GPL v2 **§3(a)** delivery — every downloader
receives the source alongside the image, with no separate request or written
offer required.

**Which file.** Pick your **model**, then the **variant** — `Standard` (no AI
Advisor) or the `…_MCP` **AI Advisor** image (the optional, off-by-default MCP
build). Verify the download against the release's `SHA256SUMS` file before
flashing. Recovery `_loader.pkgtb` images are not published (see the release
process notes); they are available on request if you need one.

**Older or unlisted versions.** If you need a specific version that is no longer
on the Releases page, email **theunbounddeveloper@outlook.com** with the model,
variant, and version and it will be provided with its corresponding source.

Under GPL v2 you may use, study, modify, and redistribute the GPL-covered
portions freely; if you ship a modified build, please brand it as your own (see
[`../LICENSE.reaper`](../LICENSE.reaper) § 3(c)).

> **Note.** A build bundles proprietary Broadcom/ASUS/Trend Micro/Tuxera
> components licensed for use on genuine ASUS hardware only. They are provided for
> flashing your own ASUS RT-BE Series router and are **not** separately licensed
> for redistribution. See § Proprietary components in
> [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md).

---

## 4. If you redistribute a Reaper image

GPL v2 requires that GPL binaries travel with either the corresponding source
(**§3(a)**) or a copy of a written offer like §2 above (**§3(b)/§3(c)**), and
with the GPL license text itself; GPL v3 imposes the equivalent, plus the
Installation Information of § 5. Concretely, any place that hosts a Reaper
`.pkgtb` image **must** also carry, at minimum:

- [ ] the applicable license texts — GPL v2 ([`../LICENSE`](../LICENSE)) and, for the
      bundled GPLv3 / LGPL components, [`../LICENSES/`](../LICENSES/),
- [ ] either the corresponding source (this repo / the `patches/` series against
      the pinned upstream commit) **or** a verbatim copy of the §2 written offer,
- [ ] [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md).

A firmware-image host that carries **only** the images, a README, and checksums
does **not** satisfy GPL v2. (This was the defect that took the earlier
image-hosting repository offline; do not re-publish images without the above.)

> **Separate, unresolved question — proprietary components.** A compiled `.pkgtb`
> image also bundles the proprietary Broadcom/ASUS/Trend Micro/Tuxera binaries,
> which are licensed for genuine ASUS hardware only and are **not** covered by
> the GPL offer above. Whether, and how, compiled images that bundle those
> components may be redistributed publicly is a question for a qualified
> attorney — it is **not** resolved by this document, which addresses only the
> GPL source obligation. See [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md)
> § Proprietary components.

---

## 5. GPL v3 & LGPL components — source + Installation Information (GPL v3 § 6)

The firmware bundles components licensed under **GPL v3** — notably **Samba
4.15.13a** (the SMB3 file server), **GNU wget**, and **GNU nano** — and **LGPL
v2.1** shared libraries (glib, avahi, libdaemon, …). Their license texts ship in
[`../LICENSES/`](../LICENSES/): [`GPL-3.0.txt`](../LICENSES/GPL-3.0.txt) and
[`LGPL-2.1.txt`](../LICENSES/LGPL-2.1.txt), alongside the GPL v2 text at the repo
root and the per-license map in [`../LICENSES/README.md`](../LICENSES/README.md).

**Complete corresponding source** for these components is provided by the same
mechanism as § 1: the pinned upstream tree plus the [`../patches/`](../patches/)
series reconstructs the exact source of every GPL- and LGPL-covered component in
the image. No additional step is required for the v3 parts.

**Installation Information (GPL v3 § 6 / anti-tivoization).** A Reaper firmware
image is a "User Product" running on a consumer device, so GPL v3 additionally
requires the information needed to install a modified version of the GPLv3
components on that device. Reaper imposes **no lock** of its own:

- the complete **build** procedure is [`DEV-SETUP.md`](DEV-SETUP.md) +
  [`../build-scripts/`](../build-scripts/) + the pinned inputs in
  [`../DEPENDENCIES.md`](../DEPENDENCIES.md);
- the **flash / recovery** procedure is
  [`INSTALL-AND-ROLLBACK.md`](INSTALL-AND-ROLLBACK.md) (GUI *Administration →
  Firmware Upgrade*, and ASUS Firmware Restoration for recovery).

Together these are the Installation Information: you can build a modified image
from this source and flash it to the same class of ASUS RT-BE device by the same
path Reaper itself is installed. Reaper neither requires nor withholds any signing
key. (The stock ASUS bootloader's own signature handling is a vendor property of
the hardware, unchanged by Reaper — Reaper adds no cryptographic restriction on
user-built firmware.)
