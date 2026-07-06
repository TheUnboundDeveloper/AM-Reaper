# Security Policy

This project exists to harden the RT-BE96U firmware, so security reports are very welcome.

## Scope

- **In scope:** the changes in this repo — everything under [`patches/`](patches/) — and the published `reaper` images (GitHub Releases). That includes regressions introduced by the hardening itself.
- **Out of scope:** bugs in stock Asuswrt-Merlin or ASUS's GPL drop that this project hasn't touched — report those upstream to [RMerl/asuswrt-merlin.ng](https://github.com/RMerl/asuswrt-merlin.ng/security) or ASUS. (If a stock bug is remotely/LAN-reachable on the BE96U, we still want to hear about it — fixing that class of bug is the point of this fork.)
- The proprietary Broadcom/ASUS blobs are a documented residual risk (see [`docs/REAPER-FIXES.md`](docs/REAPER-FIXES.md)); reports there are appreciated but may only be addressable by mitigation, not by patching the blob.

## Reporting

Email **theunbounddeveloper@outlook.com** with:

- the affected patch/file or image version (`RT-BE96U_…_reaper_…`),
- reproduction steps or a PoC,
- whether the issue is reachable from WAN, LAN, or only with authentication.

Please use email rather than a public issue for anything exploitable. You'll get a response as soon as practical; fixes land as new numbered patches and a new release image.

## Threat model

The project's bar: **only physical access should be able to compromise the device.** Anything remotely or LAN-reachable that breaks that bar is a valid, wanted report — see [`docs/PROJECT.md`](docs/PROJECT.md) for the full threat model.
