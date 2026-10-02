# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.3.2** · 2026-10-02 <!--@stamp-->

What is left to do, one line per item, grouped by area. Status where known: **[owed]** (must be
done), **[blocked]** (external cause), **[shelved]** / **[deferred]** (deliberately set aside),
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

- [Work next](#work-next)
- [Waiting on field response](#waiting-on-field-response)
- [Open bugs / under investigation](#open-bugs--under-investigation)
- [UI / UX polish](#ui--ux-polish)
- [Features to add](#features-to-add)
- [Documentation](#documentation)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Reported, investigated, closed as working-as-designed](#reported-investigated-closed-as-working-as-designed)
- [Blocked by closed-source components — for ASUS / Broadcom](#blocked-by-closed-source-components--for-asus--broadcom)

---

## Work next

The ordered short list. *v3.3.2 is the newest rung (cut 2026-10-02); earlier releases are in
[`CHANGELOG.md`](CHANGELOG.md).*

1. **[P2] Code signing, fully automated** — CI-signed images + manifest, router verify, pre-upload
   verdict; gate test first. **[scheduled]** ↳ notes: `manifest-signing-shelved.md`
2. **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — every cru job dead on that box.
   **[needs data]** ↳ notes: `gt-be98-empty-crontab.md`
3. **[P2] Warden chain missing after an add-on update** (amtm + Diversion) — defensive half built;
   root cause wants a syslog. **[needs data]** ↳ notes: `warden-crash-addon-update.md`
4. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1). **[owed: repro]**
   ↳ notes: `firewall-hosts-paste-blanks-gui.md`
5. **[P3] Build one `stable` image** — the stable channel path has never run. **[owed]**
   ↳ notes: `channel-marker.md`
6. **[P3] Local sibling images** — RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro are source-only
   locally; CI unaffected. **[hygiene]**
7. **[P3] CVE check 2026-08-30 residue** — kernel one-hunk set; CVE-2026-90110 backport in v3.2.8
   needs the soak. **[owed]** ↳ notes: `cve-check-2026-08-30.md`
8. **[P3] Code-review tail, batch B** — two owner-deferred items. **[deferred]**
   ↳ notes: `code-review-tail.md`
9. **[P2] ZenWiFi BQ16 (BE25000) on the roster since v3.3.2** — onboarded from the ASUS 102_39256 GPL drop +
   stock radio firmware; MCP and noMCP 34/34 locally; first CI build (the clean-room proof of its
   platform archive) and a tester owed. Prerelease-only until a unit boots one. **[owed: CI run, a tester]**
   ↳ notes: `bq16-onboarding.md`

---

## Waiting on field response

*Fixed (in the named image or earlier) and waiting on the reporting tester to confirm. No new work
is planned; a "still broken" answer moves the item back to Open bugs. Each note says what to ask for.*

- **[P3] Rule Status: VPN-server rows red on an RT-BE86U** — test address in `rw_threat`; the
  picker saw only 32 sets, **fixed v3.3.0**. Ask: version + blocked-country count. **[awaiting field]**
  ↳ notes: `fwsim-wansrc-set-cap.md`
- **[P2] AiMesh node cards show zero clients in a bridging mode** (GT-BE19000) — overlay from the device
  store, **fixed v3.3.1**. Ask: node card counts on the AP-mode box. **[awaiting field]** ↳ notes: `aimesh-card-zero-clients-bridge.md`
- **[P3] e2fsprogs CVE-2022-1304 via a crafted USB disk** — upstream `ab51d587bb9b` applied; host
  test 2026-09-28: the guard fires on a crafted empty leaf, repair converges. **[metal owed: USB scan
  of an ext4 + ext3 disk]** ↳ notes: `review-carry-forward-queue.md`
- **[P2] Warden outbound blocks appear to have stopped** — `rwarden_log` read 0/1/0. **[owed: the
  owner's recollection or a repro]** ↳ notes: `warden-outbound-quiet.md`
- **[P3] Firewall DNAT / Redirect: the residual gaps.** **[project]**
  ↳ notes: `firewall-dnat-redirect-residual.md`
- **[P3] Rule Status walker: fixtures from a second and third topology** — RT-BE88U, GT-BE98 with
  VLANs. Ask for: `reaper_fwsim --dump-inputs DIR`. **[needs data]**
  ↳ notes: `firewall-witness-catalog.md`
- **[P2] First-boot setup box: browser autofill put the router password into the Wi-Fi key; the apply
  bounced back to the page instead of showing the reboot** (GT-BE98) — Wi-Fi fields moved out of the
  credential form, nothing prepopulated, login name lowercase-only, "Apply & Reboot" ends in the
  REBOOTING screen; **fixed v3.3.2**. Ask: one factory reset through the box in Chrome.
  **[awaiting field]** ↳ notes: `firstboot-box-autofill-reboot.md`
- **[P1] A firmware flash left the Entware USB volume busy, then dirty; the next boot had no DNS**
  (RT-BE86U) — the flash now releases the USB volumes before the eject and a boot clears a pending
  `rc_service`; **fixed v3.3.2**. Ask: one upgrade with the drive attached (no busy lines in the log).
  The reported reboot loop is NOT explained - kept in Open bugs. **[awaiting field]**
  ↳ notes: `usb-release-before-flash.md`
- **[P2] IPv6 reaches some LAN hosts but not others** (GT-BE98) — Stateful had no SLAAC; `slaac`
  added to the Stateful range, **v3.3.1**. Ask: VM IPv6 + one diag. **[awaiting field]** ↳ notes: `gt-be98-ipv6-partial-lan.md`
- **[P3] Minimum width on Auto** (`reaper_bwfloor`, v3.3.1) — built; the floor is 80 MHz on both bands;
  re-arm while wide no longer restarts acsd2 (`picker-pending`). **[metal owed]** ↳ notes: `min-width-auto.md`
- **[P3] Static preamble puncturing** — built. **[metal owed]** ↳ notes: `preamble-puncturing-metal.md`

---

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P1] Reboot loop after a flash on an Entware box** (RT-BE86U) — the busy/dirty USB half is fixed
  in v3.3.2 (Waiting above); nothing in Reaper reboots on a dnsmasq failure, so the loop itself is
  unexplained. **[needs data: `sys_reboot_reason` + the pre-reboot syslog from the box]**
  ↳ notes: `usb-release-before-flash.md`
- **[P2] Warden chains absent 13 min after boot on a flapping WAN** — suspect `stop/start_firewall`
  racing the arm. **[owed: bench repro]** ↳ notes: `warden-chains-absent-wan-flap.md`
- **[P3] Duplicate menu entries after opening UPnP Media Server** (GT-BE19000). **[needs data]**
  ↳ notes: `duplicate-menus-mediaserver.md`
- **[P3] Policy Routing page: the first-open symptom was never identified.** **[needs the
  screenshot]** ↳ notes: `pbr-first-open-symptom.md`
- **[P3] System Log page: two severity dropdowns, only one filters.** **[owner call]**
  ↳ notes: `syslog-level-dropdowns.md`
- **[P3] Policy Routing rebuild is not atomic** (R07, second half). **[design]**
  ↳ notes: `pbr-rebuild-not-atomic.md`
- **[P3] Policy Routing on Warden's country sets.** **[feature, owner call]**
  ↳ notes: `pbr-warden-country-sets.md`
- **[P3] Update-manifest signature stays inert (R09)** — accepted trade. **[accepted]**
- **[P2] AiMesh: repeated pairing failures reported against Reaper.** **[needs data]**
  ↳ notes: `aimesh-pairing-failures-tester.md`, `aimesh-decompose-2026-09-09.md`
- **[P2] MLO ON kills the AiMesh backhaul.** **[owed: needs a mesh]**
  ↳ notes: `mlo-kills-aimesh-backhaul.md`

---

## UI / UX polish

- **[P3] Rule Status does not witness masquerade.** **[owner call]**
  ↳ notes: `rule-status-masquerade-witness.md`
- **[P3] Tx power's lowest step** writes `10` where stock writes `0`. **[owner call]**
  ↳ notes: `tx-power-lowest-step.md`
- **[P3] 39 tokens are English in the 24 non-English packs.** **[owed — next translation pass]**
  ↳ notes: `english-tokens-residual.md`
- **[P3] Firmware page: the download phase has no true cancel.** **[deferred — needs an rc stop
  service]** ↳ notes: `firmware-veil-cancel.md`
- **[P3] Chain-integrity watchdog covers the Warden drop chains only.** **[owed — needs the
  invariant defined]** ↳ notes: `chain-integrity-scope.md`
- **[P3] Loading/Restarting overlay: native redesign remainder.** **[owed]**
  ↳ notes: `loading-overlay-redesign.md`
- **[P3] Loader z-index raise is class-wide.** **[watch]** ↳ notes: `loader-zindex-watch.md`
- **[P3] Smart Connect band-mask hazards.** **[watch]** ↳ notes: `smart-connect-band-mask.md`

---

## Features to add

- **[P3] Dynamic puncturing: PHY trigger + client evidence** (v3.3.1 r6) — built; trigger levels are
  heuristics. **[metal owed: calibration + one proof line]** ↳ notes: `punct-detection-inputs.md`
- **[P3] Interference mitigation switch** (`wlN_rmit`, v3.3.1) — built (driver default / + HW ACI);
  `obss_dyn_bw` dropped (CSA width switch); 91 did not help clients. **[metal owed: restart re-apply]** ↳ notes: `punct-detection-inputs.md`
- **[P3] OSPF + BGP dynamic routing.** **[project]** ↳ notes: `ospf-bgp-dynamic-routing.md`
- **[P3] Wi-Fi VLANs: the two missing pieces.** **[project]** ↳ notes: `wifi-vlans-residual.md`
- **[P3] Attainder — control by names** (resolver-step domain blocker). **[project]**
  ↳ notes: `attainder-name-control.md`
- **[P3] Mimic — copy of the flows** (port mirroring to an external IDS) — Runner hardware mirror,
  user-chosen ports. **[planned: metal feasibility check first]**
  ↳ notes: `port-mirroring-ids.md`
- **[P3] Unbound beside the existing resolver path.** **[project]** ↳ notes: `unbound-resolver.md`
- **[P2] Code signing: manifest + images, with a pre-upload verdict.** **[scheduled]**
  ↳ notes: `manifest-signing-shelved.md`
- **[P3] North star — replace stock GUI pages with Reaper-native ones.** **[ongoing]**
  ↳ notes: `native-page-migration.md`
- **[P3] Staged ("batch") changes — one save, minimal restarts.** **[project]**
  ↳ notes: `staged-batch-changes.md`

---

## Documentation

*Nothing open.*

---

## Code quality / deferred (with reason)

- **[P2] The code-review MEDIUM/LOW tail, batch B.** **[owed: the two deferred items]**
  ↳ notes: `code-review-tail.md`
- **[P3] Second review of the v3.1.0–v3.1.5 code** — seven sequential slices, reachability before any
  finding. **[planned — not started]** ↳ notes: `review-carry-forward-queue.md` §4
- **[P2] Only Gatekeeper knows AiMesh exists** — wants one shared `reaper_aimesh_exempt()`.
  **[owed — before a fourth enforcement surface]** ↳ notes: `aimesh-exempt-helper.md`
- **[P3] Sibling port misses adds, renames and deletes** — local sibling builds break; CI immune.
  **[owed]** ↳ notes: `sibling-port-add-rename-delete.md`
- **[P2] Firewall engine: three silent caps** (`RFW_MAX_IFACE`/`_SETS`/`_ZPOL`) — each logs once
  per ruleset, the page refuses them (RFW_323-325); **v3.2.9**. **[metal owed]**
  ↳ notes: `rfw-silent-caps.md`
- **[P2] Warden chain build as one `iptables-restore --noflush` payload** (~3 s per rebuild) —
  shim + per-rule fallback, host-tested; **v3.2.9**. **[metal owed: soak + VPN reconnect during
  an apply; `start_rwarden()`'s direct apply is not under the firewall lock]**
  ↳ notes: `warden-restore-batch.md`
- **[P3] Policy Routing: recapture of flows that leaked while the rules were absent.** **[deferred]**
  ↳ notes: `pbr-conntrack-recapture.md`
- **[P3] GitHub release retention — the prune is the owner's to run.** **[owner action]**
  ↳ notes: `release-retention-prune.md`
- **[P3] Sibling worktrees carry build detritus.** **[hygiene]** ↳ notes: `sibling-worktree-detritus.md`
- **[P3] `/tmp` dir-ownership hardening.** **[deferred]** ↳ notes: `tmp-dir-ownership.md`
- **[P3] `poll_fcache` O(n²) pairing · `do_reaper_dev_cgi` snapshot arrays.** **[shelved]**
  ↳ notes: `shelved-perf-items.md`
- **[P3] Theme-token vocabulary consolidation (remainder of D4).** **[owed — to the page
  migration]** ↳ notes: `theme-token-consolidation.md`
- **[P3] Inherited httpd core: two pre-auth robustness gaps.** **[inherited; deferred]**
  ↳ notes: `httpd-inherited-preauth-gaps.md`
- **[P2] Network page: Delete does nothing on a main-network card.** development based issue no firmware wide
  ↳ notes: `sdn-mainfh-delete-dead.md`

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report is not re-investigated.*

- **Dual-WAN: both NextDNS profiles receive DNS logs** — stubby round-robins every DoT endpoint.
  ↳ notes: `wad-dual-wan-nextdns.md`
- **Investigated, not a bug (do not re-raise).** ↳ notes: `wad-investigated-not-a-bug.md`
- **Translations — closed 2026-09-08, kept as a guard** (do-not-translate list).
  ↳ notes: `translations-residual.md`
- **SNMP `rwuser` — keep as-is** (owner, 2026-08-19): `rouser` would remove SNMP-SET.
- **`rwatch: FAILURE detected: warden-self-drop:<n>` is the feature reporting.**
  ↳ notes: `wad-warden-self-drop-failure.md`
- **Firewall rule negation — not building.** ↳ notes: `wad-firewall-rule-negation.md`
- **`dig` on the Network Tools page — declined.** ↳ notes: `wad-dig-network-tools.md`
- **DNS-rebind warnings for names a LAN filter blocks** — use NXDOMAIN blocking.
  ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **DNSSEC on the router fails every blocked name in a signed zone** — validate in the filter.
  ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **DDNS *Interface* selector on dual WAN is stock ASUS.** ↳ notes: `wad-ddns-interface-selector.md`
- **Mobile device metrics reported incorrect** — a rendering report. ↳ notes: `mobile-device-metrics.md`
- **AiMesh nodes refuse the firmware** — a reset cured it. **[watch]**
  ↳ notes: `aimesh-node-firmware-refused.md`
- **Service Intercept redirect-to-router with nothing listening** — enable the router's service.
  ↳ notes: `intercept-redirect-no-listener.md`
- **Boot: three "consumer-less" daemons are kept; no VPN/firewall start is reordered.**
  ↳ notes: `boot-efficiency.md`
- **Boot: what is not to be reordered, and why.** ↳ notes: `boot-efficiency.md`
- **Throughput: dataplane IRQs land on CPU0** — no pressure; no change. ↳ notes: `idle-cpu-burners.md`
- **Rule Status walker: repair-on-red — refused by design** (owner, 2026-09-16); report-only.
  ↳ notes: `firewall-witness-catalog.md`
- **Rule Status walker: 8 catalog rows not built** (B4 C8 D4 D7 G3 G5 G6 H4) — each with a stated
  reason. ↳ notes: `firewall-witness-catalog.md`
- **Gatekeeper's admin escape hatch under the ASUS admin allowlist** — the administering device is
  on the list, so the hatch holds; unlisted devices are refused by the owner's own list (owner,
  2026-09-29). ↳ notes: `firewall-witness-catalog.md`

---

## Blocked by closed-source components — for ASUS / Broadcom

> Root-caused on RT-BE96U hardware; the responsible code lives in prebuilt Broadcom blobs.

- **B-1. Classful QoS WRR is non-functional on eth ports.** ↳ notes: `blocked-b1-classful-wrr.md`
- **B-2. [P3] Unused onboarding/backhaul BSS → RADIUS log spam.** **[blocked — blob;
  risk-accepted]** ↳ notes: `blocked-b2-onboarding-bss.md`
- **B-3. [P3] Guest Network Pro breaks the 2.5G-1 LAN port with a manual WAN VLAN** (GT-BE98).
  **[blocked — blob; risk-accepted]** ↳ notes: `blocked-b3-guestpro-vlan-port.md`,
  `GUESTPRO-2.5G-VLAN-PLAN.md`
- **B-3b. [P2] Diag section 5 reports the wrong link for a LAN-port WAN** (GT-BE98). **[owed]**
  ↳ notes: `diag-lanport-wan-link.md`
- **B-4. [P3] Broadcom's own dynamic puncturing needs the 2025 SDK.** **[blocked — SDK]**
  ↳ notes: `blocked-b4-dynamic-puncturing.md`
- **B-5. [P1] Internet speed test fails on 10 Gbit/s links** — owner ruling: not chased.
  **[blocked — development]** ↳ notes: `speedtest-10g-links.md`
- **B-6. [P2] Internet speed test may stop on 2026-10-01** — ASUS retires the Ookla setup Reaper uses;
  the new keys + quota wait for the ASUS GPL. **[blocked — GPL]** ↳ notes: `speedtest-embed-key-retired.md`
