# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.8.6** · 2026-11-28 <!--@stamp-->

What is left to do, one line per item, grouped by area. Status where known: **[owed]** (must be done), **[blocked]** (external cause), **[shelved]** / **[deferred]** (deliberately set aside),
**[watch]** (not a defect today; a guard to keep), **[needs data]** (waiting on a capture or report).
Fixed items move to **Pending Cut** until they ship; **[partial: ...]** there names what stays open.

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

- [Pending Cut](#pending-cut)
- [Open bugs / under investigation](#open-bugs--under-investigation)
- [Audit Findings](#audit-findings)
- [UI / UX polish](#ui--ux-polish)
- [Potential features to add](#potential-features-to-add)
- [Documentation](#documentation)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Reported, investigated, closed as working-as-designed](#reported-investigated-closed-as-working-as-designed)

---

## Pending Cut

*Fixed in the source; ships with the next version. At the cut every line here leaves the backlog
(recorded in the changelog), except a **[partial: ...]** line: it goes back to its section with only the open part.*


---

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P2] MLO on: a soft restart can leave Wi-Fi accepting no devices until a power cycle** **[cause open]** ↳ notes: `mlo-restart-radio-link.md`
- **[P3] Security review: the firmware's own one-time list entries show as changes to review** **[not started]** ↳ notes: `review-2026-11-24-cut-readiness.md`
- **[P2] GT-BE98: a 5 GHz Wi-Fi bridge (WDS) station drops for ~30 s** **[data asked of the reporter]** ↳ notes: `gt-be98-wds-drop-log-noise.md`
- **[P2] USB 3 writes run at half of reads on BCM4912 / BCM4916 models** **[A/B run owed]** ↳ notes: `usb3-write-ceiling.md`
- **[P2] AI Advisor: arming code and lockout move to reset-proof `/data/reaper/advisor/`** **[not scheduled]** ↳ notes: `advisor-arming-code-admin-reset.md`
- **[P2] Guest Portal on AiMesh nodes: sign-in and network separation for guests joining through a node** **[not verified]** ↳ notes: `guest-portal-aimesh-nodes.md`
- **[P3] Update-manifest signature stays inert (R09)** **[accepted]** ↳ notes: `manifest-signature-inert-r09.md`
- **[P3] DDNS: intermittent updates (v3.7.9)** **[reporter still checking]** ↳ notes: `ddns-flaky-v379.md`
- **[P2] BQ16: the Devices page reportedly does not show MLO devices properly** **[details needed]** ↳ notes: `bq16-devices-mlo-display.md`
- **[P2] Aqara G410 doorbell: control works but no video in the Aqara app or Apple Home (Bastion off)** **[reported; data asked]** ↳ notes: `aqara-g410-doorbell-no-video.md`
- **[P2] Alpha line: check the rest of the closed-object swap list for pairs that must cross together (the conn_diag case)** **[parked]** ↳ notes: `conn-diag-crash-bq16-alpha.md`

---

## Audit Findings

*Open items from the security and code reviews, one line each. `↳ report:` names the maintainer's
private review report and the finding ID in it; review reports are never published.*

- **[P1] Every supported model and hardware revision ships the drivers and radio firmware it needs: full per-model review** **[tester readings owed]** ↳ notes: `model-driver-completeness-review.md`
- **[P3] jQuery Mobile 1.4.5 (end of life) ships for the AiMesh add-node wizard** **[with the wizard rewrite]** ↳ report: `review-2026-11-03` B-4
- **[P3] Review coverage not reached: closed listener parsers, closed ioctl handlers, closed packet-path objects, some stock pages** **[watch]** ↳ report: `review-2026-11-17` (section 10)
- **[P3] Maintainer tooling proposals (2026-11-11)** **[approved 2026-11-11; 7 of 19 done]** ↳ notes: `tooling-proposals-2026-11-11.md`
- **[P2] ASUS releases of 2026-11-17 (firmware 394xx, GPL 39441-39448): what Reaper should take** **[B1-B4, B6 shipped; BQ16 waits for its GPL]** ↳ report: `drop-intake-2026-11-18` · notes: `asus-drop-intake-2026-11-18.md`
- **[P3] Unused closed programs to remove after a consumer check** **[group B left; ceventd stays]** ↳ report: `review-2026-11-03` F-11 · notes: `unused-programs-2026-11-09.md`

---

## UI / UX polish

- **[P3] Reaper pages: the polishing redesign and formatting pass** **[not started]** ↳ notes: `loading-overlay-redesign.md`
- **[P3] Option 162 log line says the offer changed when only a DNS Director rule did** **[not started]** ↳ notes: `review-2026-11-24-cut-readiness.md`
- **[P3] Traffic Analyzer: download and upload use different colours in the tiles and the chart** **[reported; not started]** ↳ notes: `traffic-download-upload-colours.md`

---

## Potential Features to add

- **[P2] Code signing: manifest + images, with a pre-upload verdict** **[scheduled]** ↳ notes: `manifest-signing-shelved.md`
- **[P2] Two-tier admin credential for root-equivalent actions** **[designed 2026-10-19; owner call]** ↳ notes: `two-tier-admin-credential.md`
- **[P3] Security review: watch more settings** **[left: Wi-Fi security mode]** ↳ notes: `security-review-coverage.md`
- **[P3] Aura RGB lighting: merge ASUS's Aura LED support into every model that has the lights** **[not started]** ↳ notes: `aura-rgb-supporting-models.md`
- **[P3] Encrypted DNS on isolated guest networks: DoT / DoH to the network's own gateway, with the option 162 offer** **[field request 2026-11-22; owner call]** ↳ notes: `guest-isolated-encrypted-dns.md`
- **[P3] Dreadwatch lists on USB: a higher name limit while a USB store is attached** **[proposed; the limit to revisit]** ↳ notes: `dreadwatch-limit.md`
- **[P3] Language packs on demand: English-only image, the admin installs their language** **[idea, measured]** ↳ notes: `language-packs-on-demand.md`
- **[P3] Staged ("batch") changes: one save, minimal restarts** **[project]** ↳ notes: `staged-batch-changes.md`
- **[P3] Wallguard: "pause and record" - list what would have been blocked while a device was paused** **[idea; not started]** ↳ notes: `wallguard-pause-and-record.md`
- **[P3] Wallguard: show per device when its DNS bypasses the router** **[idea; not started]** ↳ notes: `wallguard-device-bypass-hint.md`
- **[P3] System Log: review the level each Reaper log line is written at (error, warning, info) and correct it** **[not started]** ↳ notes: `log-levels-review.md`
- **[P4] Advanced tier: TLS interception for URL-level inspection** **[threat model first]** ↳ notes: `encrypted-dns.md`, `security-leftovers-plan-2026-11-10.md`

---

## Documentation

- **[P3] Add-on integration points: what an external audit may read** **[owner call]** ↳ notes: `secaudit-external-addon.md`

---

## Code quality / deferred (with reason)

- **[P2] Add packet loss to the connections tab** **[deferred]** ↳ notes: `conn-packet-loss.md`
- **[P2] AiMesh: the preferred uplink node is ignored (BQ16, v3.5.0)** **[deferred]** ↳ notes: `aimesh-preferred-uplink.md`
- **[P3] Kit and httpd duplicates to fold into one copy (incl. the helpers left by review 2026-11-17 phase 4)** **[not started]** ↳ notes: `kit-dedupe.md`, `review-2026-11-17-remediation.md`
- **[P3] Rules engine and Policy Routing: one shared arm / confirm / revert (review C-D2)** **[loads and deadline watcher shared in v3.8.2]** ↳ report: `review-2026-11-17` · notes: `review-2026-11-17-remediation.md`
- **[P3] Test suites that need the firmware source: keep them with the maintainer's tooling, the self-contained ones here** **[not started]** ↳ notes: `public-tests-split.md`
- **[P3] Policy Routing: recapture of flows that leaked while the rules were absent** **[deferred]** ↳ notes: `pbr-conntrack-recapture.md`
- **[P3] GitHub release retention: betas 5+ versions behind are pruned** **[recurring, owner call]** ↳ notes: `release-retention-prune.md`
- **[P3] `poll_fcache` O(n²) pairing · `do_reaper_dev_cgi` snapshot arrays** **[shelved]** ↳ notes: `shelved-perf-items.md`
- **[P3] Theme-token vocabulary consolidation (remainder of D4)** **[owed — to the page migration]** ↳ notes: `theme-token-consolidation.md`
- **[P3] avahi CVE-2025-59529 (local socket)** **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] Encrypted DNS answers guest/VLAN networks over IPv4 only** **[deferred]** ↳ notes: `encrypted-dns.md`
- **[P3] Wallguard: network profiles IPv4-only; merged identical lookups share one CNAME verdict** **[deferred / accepted]** ↳ notes: `wallguard.md`
- **[P3] VLAN page: Add is refused 2 to 5 networks early (the main-network rows are counted)** **[deferred (owner 2026-11-16)]** ↳ notes: `bug-review-2026-11-16.md`
- **[P3] WPS page: the router's PIN is shown without pressing Show (as the stock page)** **[deferred (owner 2026-11-16)]** ↳ notes: `bug-review-2026-11-16.md`
- **[P3] GT-BE98: its bootloader objects stay at GPL 102_39274 (the 102.40585 set needs a bootloader build port)** **[deferred (owner 2026-11-16)]** ↳ notes: `gt-be98-gpl-40585.md`
- **[P3] wifi_dsps.sh not installed: EDPD power-down and the fast radio recovery stay off (all models)** **[deferred (owner 2026-11-20)]** ↳ notes: `wifi-dsps-not-installed.md`
- **[P3] RT-BE88U: the AiMesh revert-firmware button does nothing (scripts not installed)** **[deferred (owner 2026-11-20)]** ↳ notes: `rt-be88u-revert-scripts.md`
- **[P4] Firewall log day files: split today's file so the store cap can remove parts** **[deferred]** ↳ notes: `fwlog-storage-row-layout.md` (item 2)
- **[P3] RT-BE86U bootloader: cma=48M (stock now 64M) and an RTL8372 blob stock does not link** **[deferred (owner 2026-11-27)]** ↳ notes: `rt-be86u-uboot-cma-rtl8372.md`

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report is not re-investigated.*

- **AiMesh: the mesh daemon listens while no node is paired** **[accepted 2026-11-24]** ↳ notes: `audit-findings-2026-11-05.md`
- **AI Advisor: one connection at a time** **[accepted 2026-11-24]** ↳ report: `review-2026-11-03` D-6
- **dnsmasq keeps its network administration capability** **[accepted 2026-11-24]** ↳ report: `review-2026-11-11` A-6 · notes: `review-2026-11-11-remediation.md`
- **USB share and WAN action handlers: session token inside each handler** **[accepted 2026-11-24]** ↳ report: `review-2026-11-11` B-2 (part 2) · notes: `review-2026-11-11-remediation.md`
- **Kernel review items left unchanged** **[accepted 2026-11-24]** ↳ report: `review-2026-11-11` A-2, A-3, A-4, A-5, Appendix A · notes: `review-2026-11-11-remediation.md`
- **Kernel nvram notifications still carry the value** **[accepted 2026-11-24]** ↳ report: `review-2026-11-11` A-1 · notes: `review-2026-11-11-remediation.md`
- **Firewall log collector: run it under its own account** **[accepted 2026-11-24]** ↳ report: `review-2026-11-11` D-5 · notes: `review-2026-11-11-remediation.md`
- **Channel picker control port: a local firewall rule by process owner** **[accepted 2026-11-24]** ↳ report: `review-2026-11-11` D-C1 · notes: `review-2026-11-11-remediation.md`
- **Boot chain: images are signed with the vendor SDK's key; an own key needs fused secure boot, which cannot be undone** **[accepted 2026-11-23]** ↳ report: `review-2026-11-03` E-12
- **Guest networks: no encrypted DNS offer (DHCP option 162) on an isolated guest network, a portal, or a network with its own DNS servers** **[closed 2026-11-22]** ↳ notes: `guest-dnr-option-162.md`
- **Image size: the RT-BE96U image fits its flash slot, 10,223,616 B spare in v3.8.3** **[closed 2026-11-20]** ↳ notes: `image-size-hunt.md`
- **Boot log: "failed to set WLC_E_CAC_STATE_CHANGE bit" from the Wi-Fi driver (closed driver, cosmetic)** **[closed 2026-11-20]** ↳ notes: `cfg80211-cac-event-bit-boot-noise.md`
- **PIN point: the 3006.102.10 base since v3.6.0 (RT-BE96U, RT-BE86U, RT-BE88U, GT-BE98 Pro)** **[closed 2026-11-20]** ↳ notes: `pin-strategy.md`
- **Sibling port misses adds, renames and deletes: not fixing (local builds are RT-BE96U only)** **[closed 2026-11-20]** ↳ notes: `sibling-port-add-rename-delete.md`
- **Sibling worktrees carry build detritus: not fixing (local builds are RT-BE96U only)** **[closed 2026-11-20]** ↳ notes: `sibling-worktree-detritus.md`
- **Local sibling images: the siblings are source-only locally (RT-BE96U only; CI builds the rest)** **[closed 2026-11-20]** ↳ notes: `local-sibling-images.md`
- **Bandwidth tab (Cloudflare's speed test in the firmware): not building** **[dropped 2026-10-13]** ↳ notes: `bandwidth-tab.md`
- **Code review 2026-10-07: plain-HTTP login default (G2), factory posture (G5): accepted** **[closed 2026-11-20]** ↳ notes: `audit-2026-10-07-remediation.md`
- **OSPF + BGP dynamic routing: not building (not needed)** **[closed 2026-11-20]** ↳ notes: `ospf-bgp-dynamic-routing.md`
- **A Wi-Fi 7 device shows two addresses: its own (Devices, leases, Gatekeeper) and its 6 GHz link address (Wireless log)** **[closed 2026-11-16]** ↳ notes: `wifi7-link-address-two-macs.md`
- **WireGuard server starts before NTP sync: working as intended** **[closed 2026-11-15]** ↳ notes: `wgs-start-before-ntp.md`
- **Devices page after a reboot: an offline device is listed only if it has a DHCP reservation or a Gatekeeper entry (BQ16 report)** **[closed 2026-11-13]** ↳ notes: `devices-offline-after-reboot-bq16-2026-11-12.md`
- **GT-BE98: no DNS after ControlD was removed (a leftover `/jffs/configs/dnsmasq.conf`)** **[closed 2026-10-21]** ↳ notes: `controld-leftover-dnsmasq-conf.md`
- **Guest network VPN not applied, OpenVPN Killswitch blocked the LAN: "Use main subnet" was on** **[closed 2026-10-18]** ↳ notes: `sdn-vpn-main-subnet-killswitch.md`
- **ASUS CVE-2026-14157 and CVE-2026-13313 do not apply** **[closed 2026-10-13]** ↳ notes: `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **Dual-WAN: both NextDNS profiles receive DNS logs** ↳ notes: `wad-dual-wan-nextdns.md`
- **Investigated, not a bug (do not re-raise)** ↳ notes: `wad-investigated-not-a-bug.md`
- **Translations: closed 2026-09-08, kept as a guard (do-not-translate list)** ↳ notes: `translations-residual.md`
- **SNMP SET: kept, limited to sysContact / sysName / sysLocation (the write-everything user is gone)** **[owner 2026-11-16]** ↳ notes: `snmp-rwuser.md`
- **`rwatch: FAILURE detected: warden-self-drop:<n>` is the feature reporting** ↳ notes: `wad-warden-self-drop-failure.md`
- **Firewall rule negation: not building** ↳ notes: `wad-firewall-rule-negation.md`
- **Unbound on the router: not building** ↳ notes: `unbound-resolver.md`
- **Mimic (hardware port mirror to an external IDS): not building** **[owner 2026-11-07]** ↳ notes: `port-mirroring-ids.md`
- **Wi-Fi VLANs (several VIDs per network, inter-VLAN ACL page): not building** **[owner 2026-11-07]** ↳ notes: `wifi-vlans-residual.md`
- **Firmware rollback / trial boot from the second slot: not building** **[owner 2026-11-07]** ↳ notes: `firmware-dual-slot-rollback.md`
- **`dig` on the Network Tools page: declined** ↳ notes: `wad-dig-network-tools.md`
- **DNS-rebind warnings for names a LAN filter blocks: use NXDOMAIN blocking** ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **DNSSEC on the router fails every blocked name in a signed zone: validate in the filter** ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **DDNS *Interface* selector on dual WAN is stock ASUS** ↳ notes: `wad-ddns-interface-selector.md`
- **Mobile device metrics reported incorrect: a rendering report** ↳ notes: `mobile-device-metrics.md`
- **AiMesh nodes refuse the firmware: a reset cured it** **[watch]** ↳ notes: `aimesh-node-firmware-refused.md`
- **AiMesh node: a PC on the node's WAN/LAN-1 jack gets no DHCP/RA for ~30 s** ↳ notes: `wad-aimesh-node-wan-jack-delay.md`
- **Service Intercept redirect-to-router with nothing listening: enable the router's service** ↳ notes: `intercept-redirect-no-listener.md`
- **Boot: three "consumer-less" daemons are kept; no VPN/firewall start is reordered** ↳ notes: `boot-efficiency.md`
- **Boot: what is not to be reordered, and why** ↳ notes: `boot-efficiency.md`
- **Throughput: dataplane IRQs land on CPU0; no pressure, no change** ↳ notes: `idle-cpu-burners.md`
- **Rule Status walker: repair-on-red refused by design; report-only** ↳ notes: `firewall-witness-catalog.md`
- **Rule Status walker: 8 catalog rows not built, each with a stated reason** ↳ notes: `firewall-witness-catalog.md`
- **Gatekeeper's admin escape hatch under the ASUS admin allowlist** ↳ notes: `firewall-witness-catalog.md`
- **USB storage attaches after `services-start` on every boot (stock order)** ↳ notes: `usb-boot-mount-chain.md`
- **"Every flash rewrites the bootloader": it does not** ↳ notes: `uboot-in-bootfs-not-loader.md`
- **Minimum width on Auto in an AiMesh: phones stay on the router** ↳ notes: `bwfloor-aimesh-roaming.md`
- **Guest Network Pro: no name resolution on a VPN-bound network while its VPN client is down** **[owner 2026-11-10]** ↳ notes: `guest-portal-wg-report-2026-11-10.md`
- **Boot log: "vlanIoctl: Failed to delete VLAN device wds..." (closed AiMesh guest-network code, harmless)** **[closed code]** ↳ notes: `vlanioctl-wds-delete-boot-noise.md`
