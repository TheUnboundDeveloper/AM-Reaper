# patches/

The complete **Reaper** series for the RT-BE96U (**178 patches, v1.0 → v1.5.9**), as `git format-patch` files generated on top of Asuswrt-Merlin **`3006.102.8-beta2`** (base commit `a7ebfa133a`). Apply them to a stock upstream checkout to reproduce the full Reaper source — security hardening, the de-cloud removals, all Hardware QoS engines, the Traffic Analyzer, the Reaper UI, and the optional AI Advisor.

## Apply

```bash
git clone https://github.com/RMerl/asuswrt-merlin.ng.git
cd asuswrt-merlin.ng
git checkout 3006.102.8-beta2

# git am --keep-cr is REQUIRED:
#  - --keep-cr: several third-party files (e.g. lltdc) have CRLF line endings, so
#    the patch context carries CR. Without --keep-cr, git strips it and the patch
#    fails to apply (at lltdc/src/qospktio.c).
#  - git am (not plain `patch`): 4 patches carry git binary payloads (fonts, logo,
#    USB ring sprite) that `patch` cannot apply.
git am --keep-cr /path/to/AM-Reaper/patches/*.patch
```

Verified: applying the full series with `git am --keep-cr` onto a clean `3006.102.8-beta2` checkout reproduces the Reaper source tree exactly (0 differences under `release/src/router`). Build per [`../docs/DEV-SETUP.md`](../docs/DEV-SETUP.md). Per-version history is in [`../docs/CHANGELOG.md`](../docs/CHANGELOG.md).

## What the series contains (178 patches, v1.0 → v1.5.9)

The filenames carry the summary; the full per-finding security mapping (CVE-class, severity) is in [`../docs/REAPER-FIXES.md`](../docs/REAPER-FIXES.md). Roughly, in order:

### v1.0 — hardening + QoS + UI baseline (`0001`–`0087`)
- `0001`–`0021` — **Hardening round 1** (IPsec/rc command injection, httpd pre-auth overflow, snmpd/nvparse/usb/shared memory safety, format strings, temp-file races, perms).
- `0022` — build branding (`BUILDREV=-reaper`).
- `0023`–`0024` — **Hardening round 2** (network-reachable ASUS daemons; Tier-3 defense-in-depth: infosvr, libovpn, libcodb, rstats, lanauth).
- `0025`–`0028` — **Hardware QoS v1** (`qos_type=10`): Runner PI2 AQM + shaper with the flow accelerator on; GUI selector; flow-cache flush fixes.
- `0029`–`0033` — **Hardening round 3** (pre-auth login decode, QoS apply gate, dnsmasq/inadyn/iptables config-injection, libcodb SQL identifiers, CAKE format fix).
- `0034`–`0065` — **Reaper UI + branding**: Smart Connect master toggle, REAPER banner/recolor passes, live-wired dashboard, shell architecture, AiMesh/Captive-Portal/Ookla theming, the HW-QoS activation fix (`qos_type` nvram length), on-device review rounds 1–2.
- `0066`–`0070` — **Hardening round 4** (self-review of Reaper-authored code), on-device review round 3, and the **mergeability refactor**: theme moved to a single httpd serve-time injection filter; stock pages/CSS reverted to pristine.
- `0071`–`0084` — Phase-B CSS de-inline completion, **avahi 0.8 CVE backport** (mDNS DoS), **latent buffer hardening T1–T4**, login-page theme, **Hardware QoS v2 — Classful** (`qos_type=11`), v1.0 UI/QoS polish.
- `0085` — **v1.0 pre-release audit fixes**: bound the QoS `ip_range_checker` `strncpy` sites, a HW-QoS Classful blank-bandwidth guard, minor UI polish.
- `0086` — **scheduled firmware-check fix**: enable `RTCONFIG_MERLINUPDATE`, `firmware_check_enable` default **0** (no outbound update traffic unless opted in; notification-only).
- `0087` — version bump to **`3006.102.8_Reaper_v1.0`**.

### v1.1 → v1.2 — de-cloud / attack-surface removal (`0088`–`0115`)
- `0088`–`0091` — remove **Amazon Alexa / Google Assistant**; keep IFTTT-referenced symbols compiled for the kept blobs; begin **AiProtection (Trend Micro `bwdpi` DPI)** removal.
- `0092`–`0096` — v1.1-beta1; inert `bwdpi` blob shims (no-DPI stubs, `amas_lib.o` stubs, `libbwdpi.so` wrapper, `CLIENT_DETAIL_INFO_TABLE` shmem-ABI pin) so the kept prebuilt blobs still link.
- `0097`–`0100` — QoS menu rename (**Adaptive QoS → Traffic Manager**), drop dead bwdpi tabs, dashboard label; v1.1-beta2.
- `0101`–`0104` — lighttpd → captive-portal-only payload; **remove AiCloud / WebDAV / CloudSync** (Phase 1.3); v1.1-beta3.
- `0105`–`0107` — **AiDisk de-wizard** (Phase 1.4), repoint entry points to USB File Sharing; v1.1-beta4.
- `0108`–`0109` — **remove the AAE / `mastiff` cloud tunnel**, restore the local Ookla Speedtest (Phase 1.5); v1.1-beta5.
- `0110`–`0115` — un-gate `libws.so` from the removed tunnel flag; serve `.woff2`/favicon; post-login dashboard landing; **v1.2** (drop beta label); disable the UU game-accelerator plugin; theme-inject only `.asp`/`.htm` (never CGI).

### v1.2.1 → v1.2.9 — polish, more removals, QoS v3/v4 (`0116`–`0132`)
- `0116`–`0129` — v1.2.1–v1.2.6 point releases: post-login landing fix; **remove the `asd` phone-home daemon** (keep `libasc`); hide dead surfaces left by removals; frame auto-grow; USB ring sprite; GUI theming sweeps; code-scan hardening + perf; a WPS-backhaul-BSS gate (and its revert); `qos_type` apply-gate hardening.
- `0130` — **v1.2.7**: remove the first-boot **QIS EULA / privacy-consent** surface (keep the AiMesh add-node wizard); SNMP token guard.
- `0131` — **v1.2.8 — Hardware QoS v3** (aggregate cap, guaranteed minimums, DSCP trust, live per-class stats).
- `0132` — **v1.2.9 — Hardware QoS v4** (per-class WRR weights + experimental L4S).

### v1.3 — Traffic Analyzer (`0133`–`0136`)
- `0133` — **v1.3.0**: Traffic Analyzer (`rtrafd` collector + native page: per-device/network/class history, top talkers, quota, WAN probe, RAM/JFFS/USB storage).
- `0134`–`0136` — v1.3.1 offload-accurate per-device/network (reads the Runner flow table), v1.3.2 endpoint fix, v1.3.3 1-second dual-cadence live view + poll selector.

### v1.4 — AI Advisor (`0137`–`0139`)
- `0137` — **v1.4.0**: AI Advisor — read-only LAN MCP server (`rmcpd`), off by default, LAN-only, arming-code gated.
- `0138` — **v1.4.1**: AI Advisor **Mode B** (optional USB key) + the clean **with/without-MCP two-build split** (`RTCONFIG_REAPER_MCP`).
- `0139` — **v1.4.2**: AI Advisor **TLS via the router's own httpd cert** (`/etc/cert.pem` through `mssl`, else plain HTTP) + **friendly SSIDs** (from the SDN profiles, not the internal onboarding IDs).

### v1.4.3 → v1.5.0a — security-review remediation, UI polish, exploit-mitigation, network diagnostics (`0140`–`0150`)
- `0140`–`0142` — **security-review remediation** of Reaper-introduced code (v1.4.3/v1.4.4), and **v1.4.5 exploit-mitigation build hardening** (FORTIFY + stack-protector-strong + PIE + full-RELRO on the Reaper daemons).
- `0143`–`0148` — UI polish and metal-test fixes (v1.4.6–v1.4.9a): i18n language packs for the Reaper pages, narrower rail + in-rail language selector, AiMesh backdrop, network-map USB icon fixes, Bandwidth Limiter on the QoS page.
- `0149` — **v1.5.0**: Network Diagnostics — the tcpdump Packet Capture tab + the AI Advisor active-diagnostics tier (ping/traceroute/DNS/netstat, opt-in, fixed-argument exec).
- `0150` — **v1.5.0a**: remove the bundled tcpdump Packet Capture; harden the AI Advisor diagnostics.

### v1.5.0b → v1.5.0d — live view, compliance, rebrand (`0151`–`0153`)
- `0151` — **v1.5.0b**: Traffic Analyzer "Live (200ms)" refresh mode (rtrafd base tick 1s → 200ms, work-time-paced); diag-aware AI Advisor `initialize` instructions (branch on the per-session diagnostics consent instead of a static "read-only" blurb).
- `0152` — **v1.5.0c**: compliance hygiene — SPDX `GPL-2.0-only` + copyright headers on the Reaper-authored source files, and the SIL OFL 1.1 text installed as `www/fonts/OFL.txt` so the Inter/Rajdhani font license ships in the image. No functional change.
- `0153` — **v1.5.0d**: de-ASUS rebrand (UI only) — the `REAPER1.png` wordmark banner replaces the logo in the header, the login/logout card, and the stock-page banner; the AiMesh node-card backdrop uses `RLogo.png` (and the `ASUSLogo.png` asset is removed); the "ASUS · Merlin · Reaper" rail wordmark becomes a live, themed, 24-hour router-time clock (reusing the stock `<% uptime(); %>` hook, offset-proof).

### v1.5.0e → v1.5.4 — reset-loop fix, boot efficiency, QoS v5 (`0154`–`0163`)
- `0154`–`0155` — **v1.5.0e**: never bounce the first-run gate pages (fixes the factory-reset
  UI redirect loop that looked like a brick); make the branch buildable from a clean checkout.
- `0156`–`0157` — **v1.5.2** boot-efficiency round 1: no httpd restart on USB mount, unblocked
  watchdog waits. (v1.5.1 was the GT-BE98 sibling-model GPL re-base — no RT-BE96U change.)
- `0158`–`0161` — **v1.5.3**: **Hardware QoS v5 download side** (WAN-ingress RX policer +
  downstream DSCP→WMM class lift), Traffic Analyzer Live tightened to 100 ms (matched pair),
  device-identity rows (name + "IP · MAC"), i18n strings.
- `0162`–`0163` — **v1.5.4**: QoS v5.1 policer burst/rate fixes from on-hardware tuning.

### v1.5.5 → v1.5.9 — first-boot wizard, Advisor tool, audit fixes, wireless page (`0164`–`0178`)
- `0164` — **v1.5.5**: unbypassable first-boot / factory-reset credentials wizard
  (`Reaper_FirstBoot.asp`), AI Advisor IP-pin retention, themed waiting overlay,
  self-updating internet status during boot.
- `0165` — **v1.5.6**: AI Advisor `get_wireless_stations` curated read tool.
- `0166`–`0171` — **v1.5.7** audit-fix rung (from a 34-agent adversarial code sweep):
  un-hidden wl driver errors in the System Log, Smart Connect band-bitmask indexing,
  `rtrafd` hot-path/rate fixes, `rmcpd` per-command time bounds + earlier cleanup arming,
  QoS mangle flush / port-forward / cfgsync / Advisor-CSS fixes.
- `0172`–`0175` — **v1.5.8**: the `Reaper_Wireless.asp` diagnostics page (radio snapshot,
  channel Lock/Unlock pin, exclusion-list visibility, on-demand channel-quality capture),
  `psc6g` duplicate-default fix, a collector build fix.
- `0176`–`0178` — **v1.5.9**: Traffic Analyzer wedge-proof live polling + stalled indicator +
  history auto-refresh; the app shell's master page scrollbar themed.

## Notes

- **Documentation commits are intentionally absent** — the docs ship in this repo's [`docs/`](../docs/) instead of as source patches, and doc hunks are stripped from mixed commits. The series is numbered sequentially with no gaps.
- **The "BE96U-only" strip is not a patch here.** Making the tree single-model (removing the other BE sibling models' artifacts) was a large mechanical deletion (~5,650 files). It is **optional** — `make rt-be96u` builds fine from the full upstream tree — so it's omitted.
- Regenerated for **v1.5.9** (2026-07-17) from the full commit stack; author identity normalized to `reaper <theunbounddeveloper@outlook.com>`; verified to reproduce the source tree exactly via `git am --keep-cr` onto a fresh `a7ebfa133a` worktree (zero diff under `release/src/router`).
