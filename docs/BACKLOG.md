# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.4.5** · 2026-10-16 <!--@stamp-->

What is left to do, one or two lines per item, grouped by area. Status where known: **[owed]** (must be done), **[blocked]** (external cause), **[shelved]** / **[deferred]** (deliberately set aside),
**[watch]** (not a defect today; a guard to keep), **[needs data]** (waiting on a capture or report),
**[awaiting field]** (fixed; closes when a field tester confirms on the named image).

**Priority** by impact on user-facing function: **[P1]** core function broken or at risk ·
**[P2]** degraded function, meaningful annoyance, or privacy exposure · **[P3]** cosmetic, polish,
internal quality, or deferred by decision.

> This file only *identifies* each item. The full record behind it — evidence, code references,
> hypotheses ranked, what to capture next — lives in the maintainer's private notes, one file per
> item, named after each entry as `↳ notes: <file>`. Applied security fixes are tracked in
> [`REAPER-FIXES.md`](REAPER-FIXES.md); the per-version history in [`CHANGELOG.md`](CHANGELOG.md).
> **Completed items are not kept here** — when something ships it is recorded in the changelog and
> dropped from this file. The per-pass change log of this file lives in the private notes too
> (`HISTORY.md`).

---

## Contents

- [Waiting on field response](#waiting-on-field-response)
- [Open bugs / under investigation](#open-bugs--under-investigation)
- [UI / UX polish](#ui--ux-polish)
- [Features to add](#features-to-add)
- [Documentation](#documentation)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Reported, investigated, closed as working-as-designed
  (#reported-investigated-closed-as-working-as-designed)
- [Blocked by closed-source components — for ASUS / Broadcom
  (#blocked-by-closed-source-components--for-asus--broadcom)

---

## Waiting on field response

*Fixed (in the named image or earlier) and waiting on the reporting tester to confirm. No new work
is planned; a "still broken" answer moves the item back to Open bugs. Each note says what to ask for.*

- **[P2] A factory Reaper router could not be added as an AiMesh node** (field, a BQ16 under an
  MLO GT-BE98) — Reaper ships WPS off and the join's WPS arm sat inside that setting; a join now
  gets WPS on its onboarding band only, the setting untouched.
  **[in v3.4.5; owed: a Reaper-to-Reaper join with MLO on, the node logging the WPS line]**
  ↳ notes: `aimesh-factory-node-wps.md`
- **[P3] Operation Mode changes and the MLO "Get started" button handed off to the stock wizard**
  — AP, Media Bridge and Router run Reaper's step page; the MLO button opens the Wireless console;
  Repeater (rung B2) still uses the wizard.
  **[in v3.4.5; owed: AP dhcp/static, MB 5G + 6G WPA3, back to Router, a wrong MB password]**
  ↳ notes: `qis-aimesh-only.md`
- **[P2] AiMesh with a Reaper main router: the upgrade contract, the node version string, the
  setup notice** — mesh upgrade = download and verify only; `webs_state_info` in the Merlin shape;
  the firmware page's mesh path re-enabled; AiMesh.asp names the x_Setting gate.
  **[in v3.4.4; owed: a mesh - node sees the update and the right version, upgrade completes]**
  ↳ notes: `aimesh-node-firmware-refused.md`
- **[P3] USB: `restart_nasapps` ran once per mounted partition** — hotplug now restarts once per
  mount wave (3 s settle). **[in v3.4.4; owed: a 2-partition disk = one `restart_nasapps`]**
  ↳ notes: `nasapps-restart-per-mount.md`
- **[P3] Samba restarted on every WAN up (twice with the WireGuard server on)** — now only when SMB
  over the WAN is on or br0's IPv6 addresses changed.
  **[in v3.4.4; owed: an SMB session survives a PPPoE reconnect; an IPv6 prefix change restarts
  it once]** ↳ notes: `samba-restart-every-wan-up.md`
- **[P2] "skb->nr_frags N exceed max_sg_array 4" is a dropped packet, not noise** (field, GT-BE98)
  — stubby's interleaved DoT writes build >4-fragment non-GSO skbs once the upstream RTT is long
  (IPv6 DoT through a 6in4 tunnel); the Runner drops each one (1:1 with eth1 `tx_dropped`). Fix:
  `netif_skb_features()` linearizes them, `net.core.reaper_tx_sg_max` (0 = stock).
  **[in v3.4.3; the GT-BE98 reporter to confirm on the beta: IPv6 DoT kept, refused packets 0, the
  cap's fired count climbing]** ↳ notes: `runner-sg-frag-cap.md`
- **[P1] 5 GHz and 6 GHz radios dead after a network restart with Dynamic puncturing on** (owner
  RT-BE96U, twice) — `restart_net` (an IPv6 or LAN change) tore the radios down without stopping
  rpunctd / reaper_bwfloor / rchqd and never dropped `wlready`; the wl1 + wl2 dongle firmware
  trapped 7 s in and stayed down until a power cycle. The readers now stop beside `stop_acsd()` in
  every teardown branch, an armed window is waited out, and they key on `rc_service` themselves.
  **[in v3.4.3; owner-confirmed 2026-10-14 on the test rung (two `restart_net`, radios survived);
  the GT-BE98 tester to confirm on the beta]** ↳ notes: `wl-readers-quiesce.md`

---

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P2] MLO ON kills the AiMesh backhaul.** No Reaper code is on the MLO path; the lead is the
  warm-reboot MLO fabric (no station associates until a power cycle). A Reaper node failing under an
  MLO main router was a separate defect, fixed in v3.4.5 (Waiting).
  **[investigated 2026-10-15; owed: the power-cycle test, owner box then the reporter]**
  ↳ notes: `mlo-kills-aimesh-backhaul.md`
- **[P2] Traffic Analyzer non-functional on BQ16 firmware** — buttons, graphs and most of the page
  were missing in a user's screenshot; cause to investigate.
  **[needs data]** ↳ notes: `traffic-analyzer-bq16.md`
- **[P2] AI Advisor arming code resets from an admin shell** — `nvram unset rmcp_code_hash` + reboot
  = first-setup path. Direction: a missing or altered record locks the Advisor until a factory reset
  (log line + Dashboard warning); hash + salt move from nvram to a sealed root-only `/jffs` file.
  **[plan written; not scheduled]** ↳ notes: `advisor-arming-code-admin-reset.md`
- **[P3] Update-manifest signature stays inert (R09)** — accepted trade.
  **[accepted]** ↳ notes: `manifest-signature-inert-r09.md`

---

## UI / UX polish

- **[P3] Loading/Restarting overlay: native redesign remainder** — 24 stock `confirm()` dialogs on 9
  pages. **[owed: the confirm() pass]** ↳ notes: `loading-overlay-redesign.md`

---

## Potential Features to add

- **[P2] Code signing: manifest + images, with a pre-upload verdict.** **[scheduled]** ↳ notes:
  `manifest-signing-shelved.md`
- **[P3] Wi-Fi VLANs: the two missing pieces.** **[project]** ↳ notes: `wifi-vlans-residual.md`
- **[P3] Attainder — control by names** (resolver-step domain blocker). **[project]** ↳ notes:
  `attainder-name-control.md`
- **[P3] Unbound beside the existing resolver path.** **[project]** ↳ notes: `unbound-resolver.md`
- **[P3] North star — replace stock GUI pages with Reaper-native ones.** **[ongoing]** ↳ notes:
  `native-page-migration.md`
- **[P3] Staged ("batch") changes — one save, minimal restarts.** **[project]** ↳ notes:
  `staged-batch-changes.md`
- **[P3] Mimic — hardware port mirror to an external IDS** (WAN Ports page, every wired port,
  dual-WAN aware) — Phase 0 mostly proven.
  **[owed: accelerated-flow + restart tests, then build]** ↳ notes: `port-mirroring-ids.md`
- **[P3] Policy Routing on Warden's country sets.** **[feature, owner call]** ↳ notes:
  `pbr-warden-country-sets.md`
---

## Documentation

- **[P3] Add-on integration points** — publish what an external audit may read; decide on a format
  marker. **[owner call]** ↳ notes: `secaudit-external-addon.md`

---

## Code quality / deferred (with reason)
- **[P3] Bandwidth tab — Cloudflare's speed test in the firmware** — built and metal-tested as
  v3.4.2 test rungs r9-r12, then removed: Cloudflare serves its 100 MB+ downloads only to a browser
  request, so the router's run had to work around that and froze the UI for its whole length; the
  device-side run alone adds nothing over speed.cloudflare.com in a browser. Internet Speed (Ookla)
  stays. **[dropped 2026-10-13]** ↳ notes: `bandwidth-tab.md`
- **[P3] Code review 2026-10-07: plain-HTTP login default (G2), factory posture (G5)** — owner
  accepted, no change. **[accepted]** ↳ notes: `audit-2026-10-07-remediation.md`
- **[P2] The code-review MEDIUM/LOW tail, batch B.** **[owed: the two deferred items]** ↳ notes:
  `code-review-tail.md`
- **[P2] Only Gatekeeper knows AiMesh exists** — wants one shared `reaper_aimesh_exempt()`.
  **[owed — before a fourth enforcement surface]** ↳ notes: `aimesh-exempt-helper.md`
- **[P2] Network page: Delete does nothing on a main-network card** — development-based, not
  firmware-wide. ↳ notes: `sdn-mainfh-delete-dead.md`
- **[P3] Second review of the v3.1.0–v3.1.5 code** — seven slices, reachability before any finding.
  **[planned — not started]** ↳ notes: `review-carry-forward-queue.md` §4
- **[P3] Sibling port misses adds, renames and deletes** — local sibling builds break; CI immune.
  **[owed]** ↳ notes: `sibling-port-add-rename-delete.md`
- **[P3] Policy Routing: recapture of flows that leaked while the rules were absent.**
  **[deferred]** ↳ notes: `pbr-conntrack-recapture.md`
- **[P3] GitHub release retention — the prune is the owner's to run.**
  **[owner action]** ↳ notes: `release-retention-prune.md`
- **[P3] Sibling worktrees carry build detritus.**
  **[hygiene]** ↳ notes: `sibling-worktree-detritus.md`
- **[P3] Local sibling images** — four siblings are source-only locally; CI unaffected.
  **[hygiene]** ↳ notes: `local-sibling-images.md`
- **[P3] Build one `stable` image** — the stable channel path has never run.
  **[owed]** ↳ notes: `channel-marker.md`
- **[P3] `poll_fcache` O(n²) pairing · `do_reaper_dev_cgi` snapshot arrays.**
  **[shelved]** ↳ notes: `shelved-perf-items.md`
- **[P3] Theme-token vocabulary consolidation (remainder of D4).**
  **[owed — to the page migration]** ↳ notes: `theme-token-consolidation.md`
- **[P3] Inherited httpd core: two pre-auth robustness gaps.**
  **[inherited; deferred]** ↳ notes: `httpd-inherited-preauth-gaps.md`
- **[P3] avahi CVE-2024-52615 / -52616 (wide-area)** — nothing on the box makes a wide-area lookup.
  **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] avahi CVE-2021-3468 / CVE-2025-59529 (local socket)** — reachable only by root processes on
  the router. **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] OSPF + BGP dynamic routing.** **[Not Needed]** ↳ notes: `ospf-bgp-dynamic-routing.md`
- **[P3] WireGuard server starts before NTP sync** — the clients wait for `ntp_ready` and retry from
  cron; the server does not. Investigate gating it the same way. **[working as intended]** 
  ↳ notes: `wgs-start-before-ntp.md`

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report is not re-investigated.*

- **ASUS CVE-2026-14157 (VPN-file format string) and CVE-2026-13313 (Telnet debug function) do not
  apply** — Merlin's `vpnupload.cgi` → libovpn import path has no format-string sink; telnetd is not
  built. The 2026-10-07 batch was assessed the same week.
  **[closed 2026-10-13]** ↳ notes: `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **Dual-WAN: both NextDNS profiles receive DNS logs** — stubby round-robins every DoT endpoint.
  ↳ notes: `wad-dual-wan-nextdns.md`
- **Investigated, not a bug (do not re-raise).**
  ↳ notes: `wad-investigated-not-a-bug.md`
- **Translations — closed 2026-09-08, kept as a guard** (do-not-translate list).
  ↳ notes: `translations-residual.md`
- **SNMP `rwuser` — keep as-is** (owner, 2026-08-19): `rouser` would remove SNMP-SET.
  ↳ notes: `snmp-rwuser.md`
- **`rwatch: FAILURE detected: warden-self-drop:<n>` is the feature reporting.**
  ↳ notes: `wad-warden-self-drop-failure.md`
- **Firewall rule negation — not building.**
  ↳ notes: `wad-firewall-rule-negation.md`
- **`dig` on the Network Tools page — declined.**
  ↳ notes: `wad-dig-network-tools.md`
- **DNS-rebind warnings for names a LAN filter blocks** — use NXDOMAIN blocking.
  ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **DNSSEC on the router fails every blocked name in a signed zone** — validate in the filter.
  ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **DDNS *Interface* selector on dual WAN is stock ASUS.**
  ↳ notes: `wad-ddns-interface-selector.md`
- **Mobile device metrics reported incorrect** — a rendering report.
  ↳ notes: `mobile-device-metrics.md`
- **AiMesh nodes refuse the firmware** — a reset cured it.
  **[watch]** ↳ notes: `aimesh-node-firmware-refused.md`
- **AiMesh node: a PC on the node's WAN/LAN-1 jack gets no DHCP/RA for ~30 s** — stock AiMesh
  handling of the node's uplink jack; `lan_stp=0` does not change it; use a LAN port.
  ↳ notes: `wad-aimesh-node-wan-jack-delay.md`
- **Service Intercept redirect-to-router with nothing listening** — enable the router's service.
  ↳ notes: `intercept-redirect-no-listener.md`
- **Boot: three "consumer-less" daemons are kept; no VPN/firewall start is reordered.**
  ↳ notes: `boot-efficiency.md`
- **Boot: what is not to be reordered, and why.**
  ↳ notes: `boot-efficiency.md`
- **Throughput: dataplane IRQs land on CPU0** — no pressure; no change.
  ↳ notes: `idle-cpu-burners.md`
- **Rule Status walker: repair-on-red — refused by design** (owner, 2026-09-16); report-only.
  ↳ notes: `firewall-witness-catalog.md`
- **Rule Status walker: 8 catalog rows not built** (B4 C8 D4 D7 G3 G5 G6 H4) — each with a stated
  reason.
  ↳ notes: `firewall-witness-catalog.md`
- **Gatekeeper's admin escape hatch under the ASUS admin allowlist** — the administering device is
  on the list.
  ↳ notes: `firewall-witness-catalog.md`
- **USB storage attaches after `services-start` on every boot** — stock order; `/opt` services
  before the mount fail.
  ↳ notes: `usb-boot-mount-chain.md`
- **"Every flash rewrites the bootloader" — it does not** — only `_loader.pkgtb` writes the loader
  partition.
  ↳ notes: `uboot-in-bootfs-not-loader.md`
- **Minimum width on Auto in an AiMesh: phones stay on the router** — channel sync mirrors the
  floor's pick onto nodes.
  ↳ notes: `bwfloor-aimesh-roaming.md`

---

## Blocked by closed-source components — for ASUS / Broadcom

> Root-caused on RT-BE96U hardware; the responsible code lives in prebuilt Broadcom blobs.

- **B-1. Classful QoS WRR is non-functional on eth ports.**
  ↳ notes: `blocked-b1-classful-wrr.md`
- **B-3. [P3] Guest Network Pro breaks the 2.5G-1 LAN port with a manual WAN VLAN** (GT-BE98).
  **[blocked — blob; risk-accepted]** ↳ notes: `blocked-b3-guestpro-vlan-port.md`
- **B-3b. [P2] Diag section 5 reports the wrong link for a LAN-port WAN** (GT-BE98).
  **[owed]** ↳ notes: `diag-lanport-wan-link.md`
- **B-4. [P3] Broadcom's own dynamic puncturing needs the 2025 SDK.**
  **[blocked — SDK]** ↳ notes: `blocked-b4-dynamic-puncturing.md`
- **B-5. [P1] Internet speed test fails on 10 Gbit/s links** — owner ruling: not chased.
  **[blocked — development]** ↳ notes: `speedtest-10g-links.md`
- **B-6. [P2] Internet speed test may stop on 2026-10-01** — ASUS retires the Ookla setup Reaper
  uses. **[blocked — GPL]** ↳ notes: `speedtest-embed-key-retired.md`
