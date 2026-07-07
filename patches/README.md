# patches/

The complete **Reaper** series for the RT-BE96U, as `git format-patch` files generated on top of Asuswrt-Merlin **`3006.102.8-beta2`** (base commit `a7ebfa133a`). Apply them to a stock upstream checkout to reproduce the full Reaper source — security hardening, both Hardware QoS engines, and the Reaper UI.

## Apply

```bash
git clone https://github.com/RMerl/asuswrt-merlin.ng.git
cd asuswrt-merlin.ng
git checkout 3006.102.8-beta2

# git am is REQUIRED (4 patches carry git binary payloads - fonts, logo,
# USB ring sprite - which plain `patch` cannot apply):
git am /path/to/ASUS-Merlin-Reaper/patches/*.patch
```

They touch only the shared open-source userspace (`release/src/router/{httpd, rc, shared, www, libovpn, snooper, urlfilterd, lltdc, wsdd2, infosvr, libcodb, avahi, …}`), so they apply cleanly to a stock tree. Build per [`../docs/DEV-SETUP.md`](../docs/DEV-SETUP.md).

## What the series contains (84 patches, v1.0)

The filenames carry the summary; the full per-finding security mapping (CVE-class, severity) is in [`../docs/REAPER-FIXES.md`](../docs/REAPER-FIXES.md). Roughly, in order:

- `0001`–`0021` — **Hardening round 1** (IPsec/rc command injection, httpd pre-auth overflow, snmpd/nvparse/usb/shared memory safety, format strings, temp-file races, perms).
- `0022` — build branding (`BUILDREV=-reaper`).
- `0023`–`0024` — **Hardening round 2** (network-reachable ASUS daemons; Tier-3 defense-in-depth: infosvr, libovpn, libcodb, rstats, lanauth).
- `0025`–`0028` — **Hardware QoS v1** (`qos_type=10`): Runner PI2 AQM + shaper with the flow accelerator on; GUI selector; flow-cache flush fixes.
- `0029`–`0033` — **Hardening round 3** (pre-auth login decode, QoS apply gate, dnsmasq/inadyn/iptables config-injection, libcodb SQL identifiers, CAKE format fix).
- `0034`–`0065` — **Reaper UI + branding**: `3006.102.8_reaper` version, Smart Connect master toggle, REAPER banner/recolor passes, live-wired dashboard, shell architecture, AiMesh/Captive-Portal/Ookla theming, the HW-QoS activation fix (`qos_type` nvram length), on-device review rounds 1–2.
- `0066`–`0070` — **Hardening round 4** (self-review of Reaper-authored code), on-device review round 3, and the **mergeability refactor**: theme moved to a single httpd serve-time injection filter; stock pages/CSS reverted to pristine.
- `0071`–`0084` — Phase-B CSS de-inline completion, **avahi 0.8 CVE backport** (mDNS DoS), **latent buffer hardening T1–T4**, login-page theme, **Hardware QoS v2 — Classful** (`qos_type=11`, per-class hardware queues), and the v1.0 UI/QoS polish (incl. the `qos_type` apply-gate raise for type 11).

## Notes

- **Documentation commits are intentionally absent** — the docs ship in this repo's [`docs/`](../docs/) instead of as source patches. The series is numbered sequentially with no gaps.
- **The "BE96U-only" strip is not a patch here.** Making the tree single-model (removing the other BE sibling models' artifacts) was a large mechanical deletion (~5,650 files). It is **optional** — `make rt-be96u` builds fine from the full upstream tree — so it's omitted.
- Regenerated for **v1.0** (2026-07-07) from the full commit stack; author identity normalized to `reaper <theunbounddeveloper@outlook.com>`.
