# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.7.0** · 2026-11-03 <!--@stamp-->

What is left to do, one line per item, grouped by area. Status where known: **[owed]** (must be done), **[blocked]** (external cause), **[shelved]** / **[deferred]** (deliberately set aside),
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
- [Audit Findings](#audit-findings)
- [UI / UX polish](#ui--ux-polish)
- [Potential features to add](#potential-features-to-add)
- [Documentation](#documentation)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Reported, investigated, closed as working-as-designed](#reported-investigated-closed-as-working-as-designed)
- [Blocked by closed-source components — for ASUS / Broadcom](#blocked-by-closed-source-components--for-asus--broadcom)

---

## Waiting on field response

*Solved: shipped in a cut or a successful test build, or fixed in canon for the next cut;
waiting on the reporter. One line each, highest priority first - what was fixed and what to ask
the tester for is in the notes. A "still broken" answer moves the item back to Open bugs.*

- **[P2] Internet speed test after ASUS retired the old Ookla setup** ↳ notes: `speedtest-embed-key-retired.md`
- **[P2] Wi-Fi start-up script fixes from GPL 40585** ↳ notes: `hndnvram-defaults-mount.md`
- **[P2] Wireless Log: device names lost, every extra network called a guest network** ↳ notes: `wireless-log-names-types.md`
- **[P2] Guest Network Pro: a network sent through a VPN has no Internet** ↳ notes: `sdn-vpn-binding-no-internet.md`
- **[P2] Only Gatekeeper knows AiMesh exists** ↳ notes: `aimesh-exempt-helper.md`
- **[P2] Warden blocked the WireGuard server from mobile data** ↳ notes: `warden-wg-listen-port.md`
- **[P2] Encrypted DNS block: no AiMesh exemption** ↳ notes: `edns-aimesh-exempt.md`
- **[P2] Russian GUI: parts of it change and duplicate; word spacing** ↳ notes: `russian-ui-layout.md`
- **[P2] Security review (2026-11-03): kernel privilege checks, root-only files, page token** ↳ notes: `security-review-2026-11-03.md`
- **[P3] WAN Ports tab missing from the WAN menu on a router** ↳ notes: `wanports-tab-wlc-band.md`
- **[P3] Internet Connection names the default WAN port, not the one in use** ↳ notes: `internet-wan-port-label.md`
- **[P3] System Info: `<i>off</i>` shown as text for a radio that is off** ↳ notes: `sysinfo-radio-off-markup.md`
- **[P3] HW QoS inert behind an ISP/IPTV profile** ↳ notes: `hwqos-isp-profile.md`
- **[P3] Reaper QoS: no unsaved-changes cue** ↳ notes: `unsaved-changes-cue.md`
- **[P3] DNS Director: pick the device from a list of connected devices** ↳ notes: `dns-director-device-picker.md`
- **[P3] VPN Director: picking a device does not fill the description** ↳ notes: `vpn-director-device-picker.md`
- **[P3] DHCP manual assignment: no device list when adding a reservation** ↳ notes: `dhcp-reservation-device-picker.md`
- **[P3] Diagnostics: engine version and WDS link names masked as addresses** ↳ notes: `diag-address-shaped-names.md`
- **[P3] Rule Status: G2 reds a VPN guest network with its Kill Switch on** ↳ notes: `rule-status-g2-vpn-guest.md`
- **[P3] Header on an iPhone 17 (portrait): Restart and Log off bounce and resize** ↳ notes: `header-buttons-bounce-mobile.md`
- **[P3] DNS Director: per-device rules show only the MAC, not the device name** ↳ notes: `dns-director-rule-names.md`
- **[P3] Bastion help links open the top of the guide** ↳ notes: `warden-help-anchor.md`
- **[P3] Dreadwatch and Wallguard: each list's address on its row** ↳ notes: `feed-list-addresses.md`
- **[P3] Bastion page texts that contradict the code** ↳ notes: `bastion-page-texts.md`
- **[P3] Warden: the IPv6 LAN exemption covers only the main LAN prefix** ↳ notes: `warden-v6-guest-prefix.md`
- **[P3] Wallguard's DNS-bypass banner misses VPN Director's Exclusive DNS** ↳ notes: `wallguard-bypass-vpndirector.md`
- **[P3] Gatekeeper: the waiting page never showed with an HTTPS-only GUI** ↳ notes: `gk-https-only-waiting-page.md`

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P2] USB 3 writes run at half of reads on BCM4912 / BCM4916 models** **[levers in v3.7.0, off by default; owed: an A/B run on a UASP SSD]** ↳ notes: `usb3-write-ceiling.md`
- **[P2] AI Advisor: arming code and lockout move to reset-proof `/data/reaper/advisor/`** **[plan written 2026-10-19; not scheduled]** ↳ notes: `advisor-arming-code-admin-reset.md`
- **[P2] MLO on: a soft restart can leave Wi-Fi accepting no devices until a power cycle** **[options offered 2026-11-01; owner call]** ↳ notes: `mlo-restart-radio-link.md`
- **[P3] Update-manifest signature stays inert (R09)** **[accepted]** ↳ notes: `manifest-signature-inert-r09.md`

---

## Audit Findings

*Open items from the security and code reviews, one line each. `↳ report:` names the maintainer's
private review report and the finding ID in it; review reports are never published.*

- **[P2] Owed router checks for the 2026-11-03 fixes: a save on each kind of page, a held device's waiting page** **[owed]** ↳ report: `review-2026-11-03` (Still owed)
- **[P2] Vendor security reports to send (two drafted, one to write)** **[owner]** ↳ notes: `vendor-reports-owed.md`
- **[P2] Kernel: the next stable-fix round (CVE-2024-26921, ipset, net/sched)** **[deferred: own port and soak]** ↳ report: `review-2026-11-03` E-5
- **[P2] Code review 2026-08-18 tail, batch B: two deferred items** **[owed]** ↳ report: `CODE-REVIEW-2026-08-18` · notes: `code-review-tail.md`
- **[P3] Review 2026-10-24: owner decisions not yet coded, Q-C1-11 to decide, behaviour-changing merges** **[decided 2026-10-30; not coded]** ↳ report: `review-2026-10-24` · notes: `review-2026-10-24.md`
- **[P3] Review 2026-10-28: AiMesh add-node on 3006.102.10 and a header-key list source on a router** **[owed]** ↳ report: `review-2026-10-28`
- **[P3] Boot chain: the image-signature key** **[owner call]** ↳ report: `review-2026-11-03` E-12
- **[P3] FTP connection-tracking helper on for every LAN client by default** **[owner call]** ↳ report: `review-2026-11-03` E-13
- **[P3] Hardened-build flags for lighttpd and libwebapi** **[deferred]** ↳ report: `review-2026-11-03` F-4
- **[P3] LLTD responder: remove the binary from the image (no longer started)** **[packaging]** ↳ report: `review-2026-11-03` F-1
- **[P3] Unused closed programs to remove after a consumer check** **[owner call]** ↳ report: `review-2026-11-03` F-11
- **[P3] Closed programs leave three world-writable pid and marker files** **[closed code]** ↳ report: `review-2026-11-03` F-10
- **[P3] Security Review card: the world-writable check covers `/jffs` only** **[deferred]** ↳ report: `review-2026-11-03` C-8
- **[P3] Long-term store: legacy entries keep their old file modes** **[deferred]** ↳ report: `review-2026-11-03` C-8
- **[P3] Port trigger: each firewall rebuild drops live trigger sessions (needs a per-rule generation)** **[deferred]** ↳ report: `review-2026-11-03` E-6
- **[P3] WireGuard apply temp files and the USB auto-created-dir marker in shared folders** **[deferred]** ↳ report: `review-2026-11-03` Latent C
- **[P3] Kernel: never-loaded netfilter modules and options with no user** **[owner call]** ↳ report: `review-2026-11-03` Latent E
- **[P3] Mount options `nosuid,nodev` on `/tmp`, `/var` and `/jffs`** **[owner call]** ↳ report: `review-2026-11-03` (owner decisions)
- **[P3] About 40 stock pages no menu reaches are still served** **[with the native-UI cutover]** ↳ report: `review-2026-11-03` B-6
- **[P3] AiMesh: the mesh daemon listens while no node is paired** **[owner call]** ↳ report: `review-2026-11-03` F-6
- **[P3] infosvr: replace the closed `interface.o` with open code** **[owner call]** ↳ report: `review-2026-11-03` F-7
- **[P3] A parental-control request before login stores a setting nothing reads** **[not started]** ↳ report: `review-2026-11-03` A-4
- **[P3] AI Advisor: one connection at a time; pin the client by default** **[owner call]** ↳ report: `review-2026-11-03` D-6
- **[P3] Wallguard compiler: bound its memory on a hostile list** **[not started]** ↳ report: `review-2026-11-03` D-7
- **[P3] Retire `wlcsm_bindfix` (built, not in the image)** **[owner call]** ↳ report: `review-2026-11-03` D-8
- **[P3] Wireless Log reads its status as script, not JSON** **[not started]** ↳ report: `review-2026-11-03` B-5
- **[P3] Three read-only Reaper CGIs outside `reaper_gate()`** **[not started]** ↳ report: `review-2026-11-03` A-6
- **[P3] jQuery Mobile 1.4.5 (end of life) ships for the AiMesh add-node wizard** **[with the wizard rewrite]** ↳ report: `review-2026-11-03` B-4
- **[P3] Third-party component changes: a compliance note** **[owner call]** ↳ report: `review-2026-11-03` D-10
- **[P3] Review coverage not reached: closed listener parsers, closed ioctl handlers, some stock pages** **[watch]** ↳ report: `review-2026-11-03` (Not reached)
- **[P3] Web-interface login lock is per LAN/WAN side, not per source (closed code)** **[deferred]** ↳ report: `review-2026-11-03` A-8 · notes: `security-review.md`
- **[P3] Inherited httpd core: two pre-auth robustness gaps** **[inherited; deferred]** ↳ notes: `httpd-inherited-preauth-gaps.md`
- **[P3] Second review of the v3.1.0–v3.1.5 code** **[planned — not started]** ↳ notes: `review-carry-forward-queue.md` §4

---

## UI / UX polish

- **[P3] Reaper pages: the polishing redesign and formatting pass** **[not started]** ↳ notes: `loading-overlay-redesign.md`

---

## Potential Features to add

- **[P1] Reaper-native UI: convert every stock page, then remove the stock pages and the theme switch** **[left: the cutover]** ↳ notes: `reaper-native-ui.md`, `native-page-migration.md`
- **[P1] Image size: the RT-BE96U root filesystem is within ~2.2 MB of its flash slot** **[v3.7.0: 2,183,168 B spare]** ↳ notes: `image-size-hunt.md`
- **[P2] Encrypted DNS: split the block into two switches (DoT/DoQ on 853, DoH)** **[designed 2026-10-21, not started]** ↳ notes: `encrypted-dns.md`
- **[P2] Code signing: manifest + images, with a pre-upload verdict** **[scheduled]** ↳ notes: `manifest-signing-shelved.md`
- **[P2] Firmware rollback + trial boot from the second slot** **[researched 2026-10-18; not started]** ↳ notes: `firmware-dual-slot-rollback.md`
- **[P2] Encrypted DNS Step B: DNS-over-HTTPS on the router** **[planned in outline]** ↳ notes: `encrypted-dns.md`
- **[P2] Security review: harden the baseline against tampering** **[owner call]** ↳ notes: `security-review.md`
- **[P2] Two-tier admin credential for root-equivalent actions** **[designed 2026-10-19; owner call]** ↳ notes: `two-tier-admin-credential.md`
- **[P3] Security review: watch more settings** **[part done 2026-10-24; the rest not started]** ↳ notes: `security-review-coverage.md`
- **[P3] Dreadwatch lists on USB: a higher name limit while a USB store is attached** **[proposed; the limit to revisit]** ↳ notes: `dreadwatch-limit.md`
- **[P3] Language packs on demand: English-only image, the admin installs their language** **[idea, measured]** ↳ notes: `language-packs-on-demand.md`
- **[P3] Diag: flag a replacing `/jffs/configs/dnsmasq.conf` and a dead local DNS upstream** **[diag half in v3.4.9; rdnshc half not done]** ↳ notes: `controld-leftover-dnsmasq-conf.md`
- **[P3] Encrypted DNS: Flow Explorer names for DoT clients** **[deferred]** ↳ notes: `encrypted-dns.md`
- **[P3] Wi-Fi VLANs: several VIDs per network and the inter-VLAN ACL page** **[not started]** ↳ notes: `wifi-vlans-residual.md`
- **[P3] Wallguard: DNS rewrite fields in the GUI, instead of SSH or direct Firewall edits** **[not started]** ↳ notes: `dns-rewrites-page.md`
- **[P3] Staged ("batch") changes: one save, minimal restarts** **[project]** ↳ notes: `staged-batch-changes.md`
- **[P3] Mimic: hardware port mirror to an external IDS** **[owed: flow and restart tests, then build]** ↳ notes: `port-mirroring-ids.md`
- **[P3] Policy Routing on Warden's country sets** **[owner call]** ↳ notes: `pbr-warden-country-sets.md`
- **[P4] Advanced tier: TLS interception for URL-level inspection** **[idea]** ↳ notes: `encrypted-dns.md`

---

## Documentation

- **[P3] Add-on integration points: what an external audit may read** **[owner call]** ↳ notes: `secaudit-external-addon.md`

---

## Code quality / deferred (with reason)

- **[P2] Network page: Delete does nothing on a main-network card** ↳ notes: `sdn-mainfh-delete-dead.md`
- **[P2] Research no PIN point: a new pin point, or diverging from a PIN build** **[deferred]** ↳ notes: `pin-strategy.md`
- **[P2] Add packet loss to the connections tab** **[deferred]** ↳ notes: `conn-packet-loss.md`
- **[P2] AiMesh: the preferred uplink node is ignored (BQ16, v3.5.0)** **[deferred]** ↳ notes: `aimesh-preferred-uplink.md`
- **[P3] haveged 1.9.22 → 1.9.27** **[not started]** ↳ notes: `merlin-40585-review-2026-10-26.md`
- **[P3] Faster local builds (two Merlin build changes)** **[not started]** ↳ notes: `merlin-40585-review-2026-10-26.md`
- **[P3] Delete the dead ASUS DDNS code** **[not started]** ↳ notes: `asuscomm-removal.md`
- **[P3] Kit and httpd duplicates to fold into one copy** **[not started]** ↳ notes: `kit-dedupe.md`
- **[P3] Bandwidth tab: Cloudflare's speed test in the firmware** **[dropped 2026-10-13]** ↳ notes: `bandwidth-tab.md`
- **[P3] Code review 2026-10-07: plain-HTTP login default (G2), factory posture (G5)** **[accepted]** ↳ notes: `audit-2026-10-07-remediation.md`
- **[P3] AiMesh exemption cap: raise 64 to 256** **[owner: next release]** ↳ notes: `aimesh-exempt-cap.md`
- **[P3] Sibling port misses adds, renames and deletes** **[owed]** ↳ notes: `sibling-port-add-rename-delete.md`
- **[P3] Policy Routing: recapture of flows that leaked while the rules were absent** **[deferred]** ↳ notes: `pbr-conntrack-recapture.md`
- **[P3] GitHub release retention: betas 5+ versions behind are pruned** **[recurring, owner call]** ↳ notes: `release-retention-prune.md`
- **[P3] Sibling worktrees carry build detritus** **[hygiene]** ↳ notes: `sibling-worktree-detritus.md`
- **[P3] Local sibling images: four siblings are source-only locally** **[hygiene]** ↳ notes: `local-sibling-images.md`
- **[P3] Build one `stable` image** **[owed]** ↳ notes: `channel-marker.md`
- **[P3] `poll_fcache` O(n²) pairing · `do_reaper_dev_cgi` snapshot arrays** **[shelved]** ↳ notes: `shelved-perf-items.md`
- **[P3] Theme-token vocabulary consolidation (remainder of D4)** **[owed — to the page migration]** ↳ notes: `theme-token-consolidation.md`
- **[P3] avahi CVE-2024-52615 / -52616 (wide-area)** **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] avahi CVE-2021-3468 / CVE-2025-59529 (local socket)** **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] OSPF + BGP dynamic routing** **[Not Needed]** ↳ notes: `ospf-bgp-dynamic-routing.md`
- **[P3] Encrypted DNS answers guest/VLAN networks over IPv4 only** **[deferred]** ↳ notes: `encrypted-dns.md`
- **[P3] Wallguard: network profiles IPv4-only; merged identical lookups share one CNAME verdict** **[deferred / accepted]** ↳ notes: `wallguard.md`
- **[P3] WireGuard server starts before NTP sync** **[working as intended]** ↳ notes: `wgs-start-before-ntp.md`
- **[P3] The main Wi-Fi's RADIUS server is set in two places** **[deferred]** ↳ notes: `radius-two-stores.md`
- **[P3] 3006.102.8 line: three lean gaps** **[not started]** ↳ notes: `lean-102-8-gaps.md`

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report is not re-investigated.*

- **GT-BE98: no DNS after ControlD was removed (a leftover `/jffs/configs/dnsmasq.conf`)** **[closed 2026-10-21]** ↳ notes: `controld-leftover-dnsmasq-conf.md`
- **Guest network VPN not applied, OpenVPN Killswitch blocked the LAN: "Use main subnet" was on** **[closed 2026-10-18]** ↳ notes: `sdn-vpn-main-subnet-killswitch.md`
- **ASUS CVE-2026-14157 and CVE-2026-13313 do not apply** **[closed 2026-10-13]** ↳ notes: `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **Dual-WAN: both NextDNS profiles receive DNS logs** ↳ notes: `wad-dual-wan-nextdns.md`
- **Investigated, not a bug (do not re-raise)** ↳ notes: `wad-investigated-not-a-bug.md`
- **Translations: closed 2026-09-08, kept as a guard (do-not-translate list)** ↳ notes: `translations-residual.md`
- **SNMP `rwuser`: keep as-is** ↳ notes: `snmp-rwuser.md`
- **`rwatch: FAILURE detected: warden-self-drop:<n>` is the feature reporting** ↳ notes: `wad-warden-self-drop-failure.md`
- **Firewall rule negation: not building** ↳ notes: `wad-firewall-rule-negation.md`
- **Unbound on the router: not building** ↳ notes: `unbound-resolver.md`
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

---

## Blocked by closed-source components — for ASUS / Broadcom

> Root-caused on RT-BE96U hardware; the responsible code lives in prebuilt Broadcom blobs.

- **B-1. Classful QoS WRR is non-functional on eth ports** ↳ notes: `blocked-b1-classful-wrr.md`
- **B-3. [P3] Guest Network Pro breaks the 2.5G-1 LAN port with a manual WAN VLAN (GT-BE98)** **[blocked — blob; risk-accepted]** ↳ notes: `blocked-b3-guestpro-vlan-port.md`
- **B-3b. [P2] Diag section 5 reports the wrong link for a LAN-port WAN (GT-BE98)** **[owed]** ↳ notes: `diag-lanport-wan-link.md`
- **B-4. [P3] Broadcom's own dynamic puncturing needs the 2025 SDK** **[blocked — SDK]** ↳ notes: `blocked-b4-dynamic-puncturing.md`
- **B-5. [P1] Internet speed test fails on 10 Gbit/s links** **[blocked — development; not chased]** ↳ notes: `speedtest-10g-links.md`
- **B-7. [P3] Source to ask the vendors for (ranked)** **[list written 2026-10-19; owner call]** ↳ notes: `blob-source-wishlist-2026-10-19.md`
