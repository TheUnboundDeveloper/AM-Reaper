# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.4.8** · 2026-10-20 <!--@stamp-->

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

- **[P2] Security review: drift of /jffs scripts, cron entries and exposure settings** (owner, from
  the IOCMON assessment) — new, off by default; rwatch 3h inventories and diffs against an accepted
  baseline, card on Firewall › Status, amber dashboard bar and posture row, one log line per change
  set, nothing undone.
  **[in v3.4.7; owner-confirmed 2026-10-19 on the r12 test build (34-item baseline accepted from
  the card, three injected changes listed first and logged once, the bar and the Review link seen,
  the revert cleared it without an Accept); owed: the posture row's four states on a tester's box]**
  ↳ notes: `security-review.md`
- **[P2] Reviewer feedback: Dreadwatch, Security Review rules, latency & loss chart** (senior
  engineer via the owner) — threat domains on their own counted page (dnsmasq hit hook), review
  watch rules + per-row accept + acceptance log, latency/loss on their own chart with a right axis.
  **[in v3.4.8; r3 ran on the owner's box (diag 2026-10-20): all three work; three rung faults
  found and fixed for r4 (see the note); owed: r4 flash, Test now, the 14:40 rwatch incident]**
  ↳ notes: `reviewer-feedback-2026-10-20.md`
- **[P2] Warden threat domains** (owner, from the IOCMON assessment; Dreadwatch from v3.4.8) —
  URLhaus + ThreatFox host names answered NXDOMAIN by every dnsmasq instance; per-feed keep-last-
  good, never-block set + exemptions, restart only on change, /jffs replay at boot.
  **[in v3.4.7; owner metal test owed: switch on → Update now → a LAN client on the router's DNS
  gets NXDOMAIN for a listed name, `grep conf-file /etc/dnsmasq.conf`, the SDN instance conf as
  well, dnssec on]** ↳ notes: `security-review.md`
- **[P2] Login watch + IPv6 SSH guard** (owner, from the IOCMON assessment) — failed SSH/web
  logins per source from a syslog cursor into the review card (rwatch 3h); `ip6tables -m recent`
  per /64 ahead of the WAN SSH accept at both firewall.c sites, no switch.
  **[in v3.4.7; owner test owed: 10+ wrong SSH passwords from one LAN host → notice + log line
  within one tick, Accept clears. The two rules parse on metal (`ip6tables-restore --test`, owner
  box 2026-10-19, a misspelt option rejected as the control). The limiter itself cannot run on the
  owner's box (IPv6 off, SSH LAN-only): owed to a tester with WAN SSH over IPv6, or
  `ip6tables -S INPUT` on such a box]**
  ↳ notes: `security-review.md`
- **[P2] Traffic Analyzer non-functional on BQ16 firmware** (field) — the collector ships off and
  the page hid that; it now says so once, with the switch.
  **[in v3.4.7; owner-confirmed on the r2 test build; owed: the reporter sees the guided page]**
  ↳ notes: `traffic-analyzer-bq16.md`
- **[P3] Traffic Analyzer Latency/Loss tiles vanish** (owner) — both hid while the live RTT read 0;
  the live figure now comes from the last 60 s of probes.
  **[in v3.4.7; owed: both tiles stay across a 5-minute boundary and an unreachable target]**
  ↳ notes: `traffic-latency-tiles.md`
- **[P3] Firmware page: every mesh node badged "Different version"** (field, BQ16 nodes) — the
  node's version string was compared with the router's display form; version keys now.
  **[in v3.4.7; owed: the reporter's nodes on the same build read as such]**
  ↳ notes: `firmware-node-version-badge.md`
- **[P3] Device Menu out of sync** (owner) — the page fetched once and never again, and stale
  neighbour entries counted as presence; 15 s refresh, live L2 evidence only, node clients
  labelled by their backhaul.
  **[in v3.4.7; owner-confirmed 2026-10-19 (an iPhone in airplane mode read offline within 10 s,
  labelled Wi-Fi via the node); owed: a reporter on a wired-backhaul mesh]**
  ↳ notes: `devices-presence-refresh.md`
- **[P2] Long-term storage split across USB partitions** (field, RT-BE86U) — with two volumes
  mounted, history landed on whichever mounted first; the store is now one pinned volume, adopted
  on the upgrade path.
  **[in v3.4.7; owed: the reporter's disk adopts the volume with the history and keeps it there
  across a reboot; the Storage page shows the pin]** ↳ notes: `usb-store-volume-pin.md`

- **[P2] AiMesh node fit: the AX92U's 5 GHz backhaul stayed off on v3.4.6** (owner) — the node
  drops 116-128 on a 30 min radar lock-out cycle and, being 160 MHz, cannot hold 100/160 then; the
  fit rated 100/160 usable (80 MHz cap) and read the router's cleared DFS block as non-DFS. Fix: a
  node that does the width needs the whole channel, flag 4 = DFS, a 6 h hold on channels a node
  stops listing; an unknown DFS status now counts as DFS.
  **[in v3.4.7; owner-confirmed 2026-10-18 on the r4 test build (37 fits, 100/160 excluded, the
  node's 5 GHz backhaul up on 149/80); owed: the first radar drop exercises the 6 h hold, then a
  second mesh and a node joining mid-plan]** ↳ notes: `aimesh-node-channel-fit.md`
- **[P1] BQ16 / BQ16 Pro: "Update check failed" on every check** (field) — the manifest held
  only beta lines for both models, and the router stops at a missing stable line. Fixed on the
  server: a never-offered 0.0.0 floor line per model; the publish tooling now writes one for any
  beta-only model.
  **[live 2026-10-18, no firmware change; owed: a BQ16 check offers v3.4.6 or reads up to date]**
  ↳ notes: `update-check-beta-only-model.md`
- **[P2] Guest portal passcodes of 16+ characters never matched** (field) — the field stops at 15
  and a longer stored value shows a hint.
  **[in v3.4.6; owed: the reporter signs in with a 15-character passcode]**
  ↳ notes: `captive-passcode-16-cap.md`
- **[P2] Steady packet loss behind a Nokia 10G ONT** (forum) — the WAN port is power-cycled at
  switch init on every model so the link renegotiates before EEE goes off (ASUS GPL 102_40585 via
  Merlin 3006.102.10).
  **[in v3.4.6; owed: the reporter's ONT stays clean through a reboot without
  `ethctl eth0 eee off`]** ↳ notes: `wan-eee-phy-reset.md`
## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P2] MLO ON kills the AiMesh backhaul.** No Reaper code is on the MLO path; the lead is the
  warm-reboot MLO fabric (no station associates until a power cycle). A Reaper node failing under an
  MLO main router was a separate defect, fixed in v3.4.5 (Waiting).
  **[investigated 2026-10-15; solved: the power-cycle test, owner box then the reporter]**
  ↳ notes: `mlo-kills-aimesh-backhaul.md`
- **[P2] AI Advisor arming code resets from an admin session** — a factory reset, an old backup
  restore or `nvram unset rmcp_code_hash` reopens first setup. Direction: an owner-held Ed25519 key
  signs the code record; key, record and lockout move to reset-proof `/data/reaper/advisor/`.
  **[plan written 2026-10-19, replaces the WPS-button plan; not scheduled]**
  ↳ notes: `advisor-arming-code-admin-reset.md`
- **[P2] Add Packet Loss to connection tab** — Investigate if packet loss can be recorded or
  monitored on the connections tab by connection. No per-flow counter exists (hardware-forwarded
  flows); feasible only as an on-demand measure for the selected connection, TCP only.
  **[researched 2026-10-18; not scheduled]** ↳ notes: `conn-packet-loss.md`
- **[P2] Research no PIN point** - Look into setting a new pin point or fully diverging from
  a PIN build.
  **[options written 2026-10-18; owner decision]** ↳ notes: `pin-strategy.md`
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
- **[P2] Security review: harden the baseline against tampering** — anyone with an admin session
  or root can accept a new baseline. Accept logging what it folded in is done (v3.4.8); open: the
  tick flags a baseline rewritten outside Accept; Accept asks for the admin password.
  **[offered 2026-10-19; owner call]** ↳ notes: `security-review.md`
- **[P3] Dreadwatch: its own switch, independent of Warden** — today it rides Warden's list
  updater, fold job and start/stop, so Warden must be on. Needs its own update job and include gate.
  **[offered 2026-10-20; owner call]** ↳ notes: `reviewer-feedback-2026-10-20.md`
- **[P2] Two-tier admin credential** — a second, rarely typed secret (the unused `shell_username`
  account) required for root-equivalent actions; SSH only through that account. A phished GUI
  password could then run the router but not own it.
  **[designed 2026-10-19; owner call]** ↳ notes: `two-tier-admin-credential.md`
---

## Documentation

- **[P3] Add-on integration points** — publish what an external audit may read; decide on a format
  marker. **[owner call]** ↳ notes: `secaudit-external-addon.md`

---

## Code quality / deferred (with reason)

- **[P3] Web-interface login lock is per LAN/WAN side, not per source** (stock httpd: five failures
  lock the whole side for five minutes). Per-source would need a table httpd does not keep; the
  review card's login notices name the source instead, and management off the WAN removes the
  exposure. **[deferred]** ↳ notes: `security-review.md`
- **[P3] Bandwidth tab — Cloudflare's speed test in the firmware** — built and metal-tested as
  v3.4.2 test rungs r9-r12, then removed: Cloudflare serves its 100 MB+ downloads only to a browser
  request, so the router's run had to work around that and froze the UI for its whole length; the
  device-side run alone adds nothing over speed.cloudflare.com in a browser. Internet Speed (Ookla)
  stays. **[dropped 2026-10-13]** ↳ notes: `bandwidth-tab.md`
- **[P3] Code review 2026-10-07: plain-HTTP login default (G2), factory posture (G5)** — owner
  accepted, no change. **[accepted]** ↳ notes: `audit-2026-10-07-remediation.md`
- **[P2] The code-review MEDIUM/LOW tail, batch B.** **[owed: the two deferred items]** ↳ notes:
  `code-review-tail.md`
- **[P3] Cut hygiene reports every `rule:value` PII-allowlist line as a missing path** — the
  check predates value entries; cosmetic, the cut continues.
  **[cause known, fix not applied]** ↳ notes: `cut-hygiene-allowlist-values.md`
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
- **[P3] GitHub release retention — betas 5+ versions behind are pruned.** First run 2026-10-19
  (152 removed, tags kept, manifest-advertised releases kept); repeat at each publish.
  **[recurring, owner call]** ↳ notes: `release-retention-prune.md`
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

- **Guest network VPN not applied, OpenVPN Killswitch blocked the LAN** (forum, BQ16) — the
  guest network had "Use main subnet" on, so it shared br0. User configuration, not Reaper code:
  the reporter turned it off and is working (owner, 2026-10-18).
  **[closed 2026-10-18]** ↳ notes: `sdn-vpn-main-subnet-killswitch.md`
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
- **B-7. [P3] Source to ask the vendors for** — ranked: ASUS-owned first (AiMesh, the httpd login
  check, networkmap); Broadcom's under NDA (ask for errata and docs); nine GPL-labelled modules
  shipped as prebuilt objects are the one licence-based ask.
  **[list written 2026-10-19; owner call on the ASUS-facing page]**
  ↳ notes: `blob-source-wishlist-2026-10-19.md`
