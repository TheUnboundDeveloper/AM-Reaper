# Source Availability & Written Offer (GPL v2 §3)

This document is how **Reaper** satisfies the "complete corresponding source"
obligation of the GNU General Public License, version 2 (see [`../LICENSE`](../LICENSE)),
for the GPL-covered portions of the firmware.

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
   - (Equivalently, ASUS's own GPL source tarball for the RT-BE96U from
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

> **Why patches instead of a source dump.** The full buildable tree (~2.6 GB)
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

## 3. Requesting a build

Reaper firmware images are **not publicly hosted.** A flashable build for the
ASUS RT-BE96U is available **on request**, and is delivered together with the
complete corresponding source (§1) under GPL v2 — a §3(a) delivery to each
recipient. This keeps the images off public, scraped pages while remaining fully
GPL-compliant to everyone who receives one.

**Request format.** Email the project address **theunbounddeveloper@outlook.com**
(or open an issue if you have repository access) with:

- **Subject:** `Reaper build request — RT-BE96U`
- **Variant:** `Standard` (no AI Advisor) **or** `AI Advisor` (the optional,
  off-by-default MCP build)
- **Version:** a specific version (e.g. `v1.5.0d`) or `latest`

You receive the flashable `.pkgtb` (plus its recovery `_loader.pkgtb`) and the
complete corresponding source per §1. Under GPL v2 you may then use, study,
modify, and redistribute the GPL-covered portions freely; if you ship a modified
build, please brand it as your own (see [`../LICENSE.reaper`](../LICENSE.reaper) § 3(c)).

> **Note.** A build bundles proprietary Broadcom/ASUS/Trend Micro/Tuxera
> components licensed for use on genuine ASUS hardware only. They are provided for
> flashing your own RT-BE96U and are **not** separately licensed for
> redistribution. See § Proprietary components in
> [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md).

---

## 4. If you redistribute a Reaper image

GPL v2 requires that GPL binaries travel with either the corresponding source
(**§3(a)**) or a copy of a written offer like §2 above (**§3(b)/§3(c)**), and
with the GPL license text itself. Concretely, any place that hosts a Reaper
`.pkgtb` image **must** also carry, at minimum:

- [ ] the GPL v2 license text ([`../LICENSE`](../LICENSE)),
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
> § Proprietary components and [`COMPLIANCE-AUDIT-2026-07-13.md`](COMPLIANCE-AUDIT-2026-07-13.md).
