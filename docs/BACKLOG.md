# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.8.1** · 2026-11-16 <!--@stamp-->

What is left to do, one line per item, grouped by area. Status where known: **[owed]** (must be done), **[blocked]** (external cause), **[shelved]** / **[deferred]** (deliberately set aside),
**[watch]** (not a defect today; a guard to keep), **[needs data]** (waiting on a capture or report).

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

- [Open bugs / under investigation](#open-bugs--under-investigation)
- [Audit Findings](#audit-findings)
- [UI / UX polish](#ui--ux-polish)
- [Potential features to add](#potential-features-to-add)
- [Documentation](#documentation)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Reported, investigated, closed as working-as-designed](#reported-investigated-closed-as-working-as-designed)

---

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P1] Guest Portal: passcode refused on a phone though it matches the router (v3.7.9)** **[one cause fixed; data asked]** ↳ notes: `guest-portal-passcode-refused-v379.md`
- **[P2] GT-BE98: a 5 GHz Wi-Fi bridge (WDS) station drops for ~30 s** **[data asked of the reporter]** ↳ notes: `gt-be98-wds-drop-log-noise.md`
- **[P2] USB 3 writes run at half of reads on BCM4912 / BCM4916 models** **[A/B run owed]** ↳ notes: `usb3-write-ceiling.md`
- **[P2] AI Advisor: arming code and lockout move to reset-proof `/data/reaper/advisor/`** **[not scheduled]** ↳ notes: `advisor-arming-code-admin-reset.md`
- **[P2] MLO on: a soft restart can leave Wi-Fi accepting no devices until a power cycle** **[owner call]** ↳ notes: `mlo-restart-radio-link.md`
- **[P2] Guest networks bound to a WireGuard client: routing after WAN events** **[not started]** ↳ notes: `guest-vpn-binding-robustness.md`
- **[P2] Guest Portal on AiMesh nodes: sign-in and network separation for guests joining through a node** **[not verified]** ↳ notes: `guest-portal-aimesh-nodes.md`
- **[P2] Devices: named devices shown as "unnamed" (v3.7.9)** **[no cause in code; re-test on the next release]** ↳ notes: `devices-named-shown-unnamed-v379.md`
- **[P3] Devices: a device wired to an AiMesh node is shown as a Wi-Fi client** **[two causes fixed; router data asked]** ↳ notes: `aimesh-node-wired-client-shown-wifi.md`
- **[P3] Update-manifest signature stays inert (R09)** **[accepted]** ↳ notes: `manifest-signature-inert-r09.md`
- **[P3] DDNS: intermittent updates (v3.7.9)** **[reporter still checking]** ↳ notes: `ddns-flaky-v379.md`
- **[P2] BQ16: the Devices page reportedly does not show MLO devices properly** **[details needed]** ↳ notes: `bq16-devices-mlo-display.md`
- **[P3] IPv6: the factory prefix request (/64) leaves guest networks without public IPv6 where the provider honours it** **[found in review; not started]** ↳ notes: `ipv6-pd-hint-guest-networks.md`
- **[P3] RADIUS: the Network page and the RADIUS tab keep the main network's server in two places** **[fix designed; not built]** ↳ notes: `radius-two-stores.md`, `bug-review-2026-11-16.md`
- **[P3] mDNS: avahi-daemon aborted once during back-to-back Wi-Fi restarts (restarted by the next one)** **[not investigated]** ↳ notes: `avahi-abort-wifi-restarts.md`
- **[P2] GT-BE98 on the alpha line: conn_diag (AiMesh diagnostics) crashes repeatedly on v3.8.0** **[likely fixed by the 102.40585 set; re-test on v3.8.1 alpha]** ↳ notes: `gt-be98-gpl-40585.md`
- **[P2] Wallguard: SafeSearch on the Default profile is not enforced (v3.8.0; Google country domain, Edge)** **[reported; not investigated]** ↳ notes: `wallguard-safesearch-not-enforced.md`

---

## Audit Findings

*Open items from the security and code reviews, one line each. `↳ report:` names the maintainer's
private review report and the finding ID in it; review reports are never published.*

- **[P3] Review 2026-10-28: AiMesh add-node on 3006.102.10 and a header-key list source on a router** **[owed]** ↳ report: `review-2026-10-28`
- **[P3] Boot chain: the image-signature key** **[owner call]** ↳ report: `review-2026-11-03` E-12
- **[P3] Unused closed programs to remove after a consumer check** **[group B: router checks owed]** ↳ report: `review-2026-11-03` F-11 · notes: `unused-programs-2026-11-09.md`
- **[P3] About 30 stock pages no menu reaches are still served** **[8 removed in v3.7.3; the rest with the native-UI cutover]** ↳ report: `review-2026-11-03` B-6
- **[P3] AiMesh: the mesh daemon listens while no node is paired** **[owner call]** ↳ notes: `audit-findings-2026-11-05.md`
- **[P3] AI Advisor: one connection at a time; pin the client by default** **[owner call]** ↳ report: `review-2026-11-03` D-6
- **[P3] jQuery Mobile 1.4.5 (end of life) ships for the AiMesh add-node wizard** **[with the wizard rewrite]** ↳ report: `review-2026-11-03` B-4
- **[P3] Review coverage not reached: closed listener parsers, closed ioctl handlers, some stock pages** **[watch]** ↳ report: `review-2026-11-03` (Not reached)
- **[P3] dnsmasq keeps its network administration capability** **[owner call]** ↳ report: `review-2026-11-11` A-6 · notes: `review-2026-11-11-remediation.md`
- **[P3] Web login lock for IPv6 LAN devices: backstop into open code** **[owner call]** ↳ report: `review-2026-11-11` B-1 · notes: `review-2026-11-11-remediation.md`
- **[P3] USB share and WAN action handlers: session token inside each handler** **[owner call]** ↳ report: `review-2026-11-11` B-2 (part 2) · notes: `review-2026-11-11-remediation.md`
- **[P3] Kernel review items left unchanged** **[owner call]** ↳ report: `review-2026-11-11` A-2, A-3, A-4, A-5, Appendix A · notes: `review-2026-11-11-remediation.md`
- **[P3] Kernel nvram notifications still carry the value** **[owner call]** ↳ report: `review-2026-11-11` A-1 · notes: `review-2026-11-11-remediation.md`
- **[P3] Firewall log collector: run it under its own account** **[owner call]** ↳ report: `review-2026-11-11` D-5 · notes: `review-2026-11-11-remediation.md`
- **[P3] Encrypted DNS and AiMesh leftovers from the 2026-11-11 review** **[owner call]** ↳ report: `review-2026-11-11` C-8 · notes: `review-2026-11-11-remediation.md`
- **[P3] DNS queries with two OPT records** **[owner call]** ↳ report: `review-2026-11-11` Appendix A · notes: `review-2026-11-11-remediation.md`
- **[P3] Channel picker control port: a local firewall rule by process owner** **[owner call]** ↳ report: `review-2026-11-11` D-C1 · notes: `review-2026-11-11-remediation.md`
- **[P3] Two kernel checks from the 2026-11-11 fixes: a test program on a router** **[owner call]** ↳ report: `review-2026-11-11` A-1, A-C2 · notes: `review-2026-11-11-remediation.md`
- **[P3] Maintainer tooling proposals (2026-11-11)** **[approved 2026-11-11; in progress]** ↳ notes: `tooling-proposals-2026-11-11.md`

---

## UI / UX polish

- **[P3] Reaper pages: the polishing redesign and formatting pass** **[not started]** ↳ notes: `loading-overlay-redesign.md`
- **[P3] Rule Status: a zone ACCEPT held back by guest isolation should say so, not read as a failed policy** **[not started]** ↳ notes: `zone-policy-into-isolated-networks.md`

---

## Potential Features to add

- **[P1] Reaper-native UI: convert every stock page, then remove the stock pages** **[left: the cutover]** ↳ notes: `reaper-native-ui.md`, `native-page-migration.md`
- **[P1] Image size: the RT-BE96U root filesystem is within ~2.2 MB of its flash slot** **[v3.8.1: 2,244,608 B spare]** ↳ notes: `image-size-hunt.md`
- **[P2] Code signing: manifest + images, with a pre-upload verdict** **[scheduled]** ↳ notes: `manifest-signing-shelved.md`
- **[P2] Security review: harden the baseline against tampering** **[owner call]** ↳ notes: `security-review.md`
- **[P2] Two-tier admin credential for root-equivalent actions** **[designed 2026-10-19; owner call]** ↳ notes: `two-tier-admin-credential.md`
- **[P2] GT-BE98: move onto GPL 102.40585 (gnuton's prebuilts) via the line unification** **[on the alpha line from v3.8.1; tester needed]** ↳ notes: `gt-be98-gpl-40585.md`
- **[P2] Policy Routing by ASN (e.g. AS2906)** **[assessed; on hold (owner 2026-11-15)]** ↳ notes: `pbr-asn-objects.md`
- **[P2] Encrypted DNS stage 2: fall back to plain upstream when DNS-over-TLS stops answering** **[planned]** ↳ notes: `encrypted-dns.md`
- **[P3] Security review: watch more settings** **[part done 2026-10-24; the rest not started]** ↳ notes: `security-review-coverage.md`
- **[P3] Dreadwatch lists on USB: a higher name limit while a USB store is attached** **[proposed; the limit to revisit]** ↳ notes: `dreadwatch-limit.md`
- **[P3] Language packs on demand: English-only image, the admin installs their language** **[idea, measured]** ↳ notes: `language-packs-on-demand.md`
- **[P2] Network page: several changes with one Wi-Fi restart (a "changes waiting" bar, Delete selected, no restart where none is needed)** **[planned; design approved 2026-11-16]** ↳ notes: `network-page-deferred-restart.md`
- **[P2] Firewall: zone policies may open one-way paths into an isolated guest network (opt-in switch, off by default)** **[assessed; not started]** ↳ notes: `zone-policy-into-isolated-networks.md`
- **[P3] Staged ("batch") changes: one save, minimal restarts** **[project]** ↳ notes: `staged-batch-changes.md`
- **[P3] Policy Routing on Warden's country sets** **[owner call]** ↳ notes: `pbr-warden-country-sets.md`
- **[P3] Tweaks: the login-page redirect goes to an address the admin types (name, port), not only www.asusrouter.com** **[not started]** ↳ notes: `login-redirect-custom-domain.md`
- **[P3] mDNS across networks: reflect only chosen service types (avahi `reflect-filters`)** **[idea; not started]** ↳ notes: `mdns-reflect-filters.md`
- **[P3] Wallguard: "pause and record" - list what would have been blocked while a device was paused** **[idea; not started]** ↳ notes: `wallguard-pause-and-record.md`
- **[P3] Wallguard: show per device when its DNS bypasses the router** **[idea; not started]** ↳ notes: `wallguard-device-bypass-hint.md`
- **[P4] Advanced tier: TLS interception for URL-level inspection** **[threat model first]** ↳ notes: `encrypted-dns.md`, `security-leftovers-plan-2026-11-10.md`

---

## Documentation

- **[P3] Add-on integration points: what an external audit may read** **[owner call]** ↳ notes: `secaudit-external-addon.md`

---

## Code quality / deferred (with reason)

- **[P2] Network page: Delete does nothing on a main-network card** **[not found in code; router repro needed]** ↳ notes: `sdn-mainfh-delete-dead.md`
- **[P2] Research no PIN point: a new pin point, or diverging from a PIN build** **[deferred]** ↳ notes: `pin-strategy.md`
- **[P2] Add packet loss to the connections tab** **[deferred]** ↳ notes: `conn-packet-loss.md`
- **[P2] AiMesh: the preferred uplink node is ignored (BQ16, v3.5.0)** **[deferred]** ↳ notes: `aimesh-preferred-uplink.md`
- **[P3] Kit and httpd duplicates to fold into one copy** **[not started]** ↳ notes: `kit-dedupe.md`
- **[P3] Bandwidth tab: Cloudflare's speed test in the firmware** **[dropped 2026-10-13]** ↳ notes: `bandwidth-tab.md`
- **[P3] Code review 2026-10-07: plain-HTTP login default (G2), factory posture (G5)** **[accepted]** ↳ notes: `audit-2026-10-07-remediation.md`
- **[P3] Sibling port misses adds, renames and deletes** **[owed]** ↳ notes: `sibling-port-add-rename-delete.md`
- **[P3] Policy Routing: recapture of flows that leaked while the rules were absent** **[deferred]** ↳ notes: `pbr-conntrack-recapture.md`
- **[P3] GitHub release retention: betas 5+ versions behind are pruned** **[recurring, owner call]** ↳ notes: `release-retention-prune.md`
- **[P3] Sibling worktrees carry build detritus** **[hygiene]** ↳ notes: `sibling-worktree-detritus.md`
- **[P3] Local sibling images: four siblings are source-only locally** **[hygiene]** ↳ notes: `local-sibling-images.md`
- **[P3] `poll_fcache` O(n²) pairing · `do_reaper_dev_cgi` snapshot arrays** **[shelved]** ↳ notes: `shelved-perf-items.md`
- **[P3] Theme-token vocabulary consolidation (remainder of D4)** **[owed — to the page migration]** ↳ notes: `theme-token-consolidation.md`
- **[P3] avahi CVE-2024-52615 / -52616 (wide-area)** **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] avahi CVE-2021-3468 / CVE-2025-59529 (local socket)** **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] OSPF + BGP dynamic routing** **[Not Needed]** ↳ notes: `ospf-bgp-dynamic-routing.md`
- **[P3] Encrypted DNS answers guest/VLAN networks over IPv4 only** **[deferred]** ↳ notes: `encrypted-dns.md`
- **[P3] Wallguard: network profiles IPv4-only; merged identical lookups share one CNAME verdict** **[deferred / accepted]** ↳ notes: `wallguard.md`
- **[P3] VLAN page: Add is refused 2 to 5 networks early (the main-network rows are counted)** **[deferred (owner 2026-11-16)]** ↳ notes: `bug-review-2026-11-16.md`
- **[P3] WPS page: the router's PIN is shown without pressing Show (as the stock page)** **[deferred (owner 2026-11-16)]** ↳ notes: `bug-review-2026-11-16.md`
- **[P3] GT-BE98: its bootloader objects stay at GPL 102_39274 (the 102.40585 set needs a bootloader build port)** **[deferred (owner 2026-11-16)]** ↳ notes: `gt-be98-gpl-40585.md`
- **[P4] Firewall log day files: split today's file so the store cap can remove parts** **[deferred]** ↳ notes: `fwlog-storage-row-layout.md` (item 2)

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report is not re-investigated.*

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
