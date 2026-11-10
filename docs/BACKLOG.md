# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.7.5** · 2026-11-09 <!--@stamp-->

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

- **[P1] CVE-2026-98432: IPv4 TCP handshake use-after-free (kernel backport)** ↳ notes: `cve-2026-98432.md`
- **[P1] CVE check 2026-11-03: DHCP client, WireGuard, socket timestamp, 102.8 config upload** ↳ notes: `cve-check-2026-11-03.md`
- **[P1] CVE audit 2026-11-03: the hostapd High, 24 Mediums, 279 kernel fixes and the kernel config cleanup** ↳ notes: `cve-audit-fixes-2026-11-04.md`
- **[P2] Internet speed test after ASUS retired the old Ookla setup** ↳ notes: `speedtest-embed-key-retired.md`
- **[P2] Wi-Fi start-up script fixes from GPL 40585** ↳ notes: `hndnvram-defaults-mount.md`
- **[P2] Wireless Log: device names lost, every extra network called a guest network** ↳ notes: `wireless-log-names-types.md`
- **[P2] Guest Network Pro: a network sent through a VPN has no Internet** ↳ notes: `sdn-vpn-binding-no-internet.md`
- **[P2] Only Gatekeeper knows AiMesh exists** ↳ notes: `aimesh-exempt-helper.md`
- **[P2] Warden blocked the WireGuard server from mobile data** ↳ notes: `warden-wg-listen-port.md`
- **[P2] Encrypted DNS block: no AiMesh exemption** ↳ notes: `edns-aimesh-exempt.md`
- **[P2] Russian GUI: parts of it change and duplicate; word spacing** ↳ notes: `russian-ui-layout.md`
- **[P2] Security review (2026-11-03): kernel privilege checks, root-only files, page token** ↳ notes: `security-review-2026-11-03.md`
- **[P2] USB Application, Media Server, Samba and FTP on Reaper pages** ↳ notes: `usb-native-wave.md`
- **[P2] Login opened a blank page (the security banner's text)** ↳ notes: `login-landing-blank-page.md`
- **[P2] Audit Findings pass 2026-11-05: endpoint tokens, pre-login fixes, temp files, permissions, removals** ↳ notes: `audit-findings-2026-11-05.md`
- **[P2] Let's Encrypt via DNS: a trusted certificate without DDNS or port 80** ↳ notes: `letsencrypt-dns.md`
- **[P2] Audit Findings pass 2026-11-06: kernel round, port trigger, lighttpd PIE/FORTIFY, /tmp and /var folders, unreachable stock pages** ↳ notes: `audit-findings-2026-11-06.md`
- **[P2] Wallguard: Advanced rules in AdGuard Home syntax, with per-device rules (`$client=`)** ↳ notes: `wallguard-client-rules.md`
- **[P2] Encrypted DNS block: Chrome's Secure DNS (Cloudflare) got through** ↳ notes: `edns-chrome-cloudflare.md`
- **[P2] Wallguard: a 03:00 reboot left the lists owed until the 05:15 run (fetched at WAN up now; retries fetch only what is owed)** ↳ notes: `wallguard.md`
- **[P2] Wallguard: AdGuard DNS's Popup Hosts list and an allowlist stayed "not downloaded yet, 0 names"** ↳ notes: `wallguard-allow-lines.md`
- **[P2] USB disks past 2 TB read as 0 B / "not mounted"; two USB tiles on the one-port ZenWiFi BQ16** ↳ notes: `usb-disk-2tb-bq16.md`
- **[P2] Custom DDNS + the built-in Let's Encrypt never requested a certificate: ddns_custom_updated ignored the pending request (le_rc_notify) that only the inadyn path acted on** **[fixed in both canons 2026-11-08: one shared helper both DDNS success paths call; in v3.7.5; owner metal check with a DuckDNS ddns-start, then the RT-BE88U tester]** ↳ notes: `ddns-custom-letsencrypt.md`
- **[P2] WireGuard client: the old DNS rule (pref 1004 `to <dns> iif lo lookup wgcN`) stayed after a DNS change or removal and came back after a reboot** **[fixed in both canons 2026-11-08: a client's DNS rules are cleared by priority, `iif lo` and its table, whatever address they were made for, before every add, on stop and on delete; a removed DNS now empties `vpncN_dns`; in v3.7.5 - owner metal check: `ip rule` after a DNS change, a removal and a reboot; reporter's model / version still to ask]** ↳ notes: `wgc-dns-rule-stale.md`
- **[P2] Rule Status: 35 rows Inconclusive since the firewall-log change - the log chains' counter rule (`-A logaccept -m state --state NEW`, no target) was read as an unknown target** **[walker 1.14 in both canons 2026-11-08: a rule with no `-j` / `-g` is walked past, as iptables does; the owner's own tables replayed: 35 Inconclusive -> OK, no other row changed; in v3.7.5]** ↳ notes: `fwsim-counter-rule.md`
- **[P2] Rule Status fixture (`reaper_fwsim --dump-inputs`): the WAN address left the router in it - `topology.txt` listed every address in clear, the `addr` file kept the WAN broadcast, a second WAN unit was not masked, and look-alike addresses were cut** **[fixed in both canons 2026-11-08: every address on every WAN device, v4 and v6, and each IPv4 broadcast masked in every file, on whole-address boundaries; in v3.7.5]** ↳ notes: `fwsim-counter-rule.md`
- **[P2] Firewall "Logged packets type: Accepted / Both" logs every new connection to the flash syslog, saturating the CPU and starving DNS** **[in v3.7.5: every firewall log rule goes to the NFLOG collector (up to 10000 lines/s per rule) or a 10-a-second fallback; on the owner's box 2026-11-08 every log rule matched its counter, 0 lost]** ↳ notes: `firewall-accept-log-flood.md`, `fwlog-nflog-plan.md`
- **[P2] Encrypted DNS: a Let's Encrypt certificate read "Not publicly trusted" after every reboot until its renewal** **[in v3.7.5]** ↳ notes: `website-review-2026-11-09.md`
- **[P3] Firewall > Objects > Address groups: "Add does nothing" (RT-BE88U, v3.7.4_BETA)** **[fixed in both canons 2026-11-08: each add row shows its own message (they all went to the hidden Rules tab); a member that is not an address object is named; in v3.7.5]** ↳ notes: `fw-address-group-add-silent.md`
- **[P3] Diag: a misnamed custom DDNS script (`ddns-start.sh`) went unflagged; a `*.bak` hook was told to chmod +x** **[the `.bak` half fixed in diag v1.3.54 (2026-11-07); diag v1.3.55 (both canons 2026-11-08) names the file to rename when DDNS is Custom and `/jffs/scripts/ddns-start` is missing; in v3.7.5]** ↳ notes: `ddns-custom-letsencrypt.md` (also found)
- **[P3] DDNS page: says when the Custom script is missing or not executable, and when the web interface is HTTP only (the certificate is then not served)** **[fixed in both canons 2026-11-08; in v3.7.5]** ↳ notes: `ddns-custom-letsencrypt.md` (also found)
- **[P3] VPN Client: a WireGuard .conf without a valid [Interface] PrivateKey or [Peer] PublicKey is refused, saying what is missing (page and httpd), nothing changed** **[fixed in both canons 2026-11-08; in v3.7.5]** ↳ notes: `wgc-dns-rule-stale.md` (item 2)
- **[P3] Storage page: ticking "Firewall log" (USB) reflowed the page for a moment** **[fixed in both canons 2026-11-08: the retention text moved to the row's description, the size column has a minimum width; not reproduced in a browser - owner to confirm on the next test build]** ↳ notes: `fwlog-storage-row-layout.md`
- **[P3] AiMesh exemption cap: raised 64 to 256** **[fixed in both canons 2026-11-08; in v3.7.5]** ↳ notes: `aimesh-exempt-cap.md`
- **[P3] Web-interface login lock: per source now - 5 failed logins lock that address alone for 300 s (an IPv6 /64 counts as one); the whole-side lock needs 20 failures on that side within 300 s; the IPv6 remote-access listener counts as WAN** **[fixed in both canons 2026-11-08; in v3.7.5; owner metal check: web + app login, captcha on/off, two LAN hosts, remote access v4/v6]** ↳ report: `review-2026-11-03` A-8 · notes: `login-lock-per-source.md`
- **[P3] Wallguard page: empty scroll below the last card after a long panel had been open - the page frame grew but never shrank, on every page** **[fixed in both canons 2026-11-08: the shell re-measures the frame from its fallback height when the page's content ends above the frame; checked in the mock: grow and shrink, short pages, phone width, scroll position kept, no resize events at rest; in v3.7.5]** ↳ notes: `wallguard-page-trailing-space.md`
- **[P3] Diagnostics: section 13 told log and helper files in /jffs/scripts to chmod +x, and skipped a symlinked hook** ↳ notes: `gt-be98-wds-drop-log-noise.md`
- **[P3] Rule Status: "WAN port 80 is closed" red for the user's own port forward of port 80** ↳ notes: `gt-be98-wds-drop-log-noise.md`
- **[P3] rwatch: the CRITICAL log line named the Warden ingest breach for every value, chain-disarmed included** ↳ notes: `rwatch-critical-wording.md`
- **[P3] Security Review: the dashboard said "under /jffs" for a file in the USB long-term store** ↳ notes: `review-ww-store-fat.md`
- **[P3] Security Review: a long-term store on FAT / exFAT / NTFS flagged every file red** ↳ notes: `review-ww-store-fat.md`
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
- **[P3] Samba: a refused login left no line in the system log** ↳ notes: `smb-refused-login-log.md`
- **[P3] Wallguard: DNS rewrites on the page (local names, as in AdGuard Home and Pi-hole)** ↳ notes: `dns-rewrites-page.md`
- **[P3] Rule Status: C3 red for a working WireGuard server forwarded to the router's own address** ↳ notes: `fwsim-c3-self-dnat.md`
- **[P3] Devices: "no lease / private address" rows for MLO link addresses** ↳ notes: `devices-pseudo-mlo-rows.md`
- **[P3] System Info: capabilities shown as tokens, removed features listed** ↳ notes: `sysinfo-capability-names.md`
- **[P3] Rule Status: every "reaches the WAN" row red with the Encrypted DNS block on** ↳ notes: `fwsim-wandst-doh.md`
- **[P3] Wallguard: an Update button on each list row; Save fetches only the lists it adds** ↳ notes: `wallguard.md`
- **[P3] USB Application: the USB Disks headers sat left of their number cells** ↳ notes: `usb-disk-2tb-bq16.md`
- **[P3] Wireless Log: an AiMesh node's backhaul station read "-"** ↳ notes: `wireless-log-names-types.md`
- **[P3] Security review: the first run after a boot comes at exactly 5 min, not 5-10 by tick alignment** ↳ notes: `review-first-run-after-boot.md`
- **[P3] Dreadwatch: "List updated" blank after every reboot until the next feed run** ↳ notes: `dreadwatch-list-updated-stamp.md`
- **[P3] Dreadwatch: "Test now" said "No list is loaded yet" with a list loaded** **[in v3.7.5]** ↳ notes: `website-review-2026-11-09.md`
- **[P3] Wallguard: the empty rewrites, profile and live tables said "Nothing blocked yet."** **[in v3.7.5]** ↳ notes: `website-review-2026-11-09.md`
- **[P3] libwebapi: full RELRO and FORTIFY, and a check in front of its stock input checks** **[in v3.7.5]** ↳ report: `review-2026-11-03` F-4 · notes: `libwebapi-hardening.md`

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P2] GT-BE98: a Wi-Fi bridge (WDS) station on 5 GHz drops for ~30 s and the devices behind it disconnect** **[field diag 2026-11-07; reporter asked for the device, default log level, a diag after a drop and the first beta it started on]** ↳ notes: `gt-be98-wds-drop-log-noise.md`
- **[P2] USB 3 writes run at half of reads on BCM4912 / BCM4916 models** **[levers in v3.7.0, off by default; owed: an A/B run on a UASP SSD]** ↳ notes: `usb3-write-ceiling.md`
- **[P2] AI Advisor: arming code and lockout move to reset-proof `/data/reaper/advisor/`** **[plan written 2026-10-19; not scheduled]** ↳ notes: `advisor-arming-code-admin-reset.md`
- **[P2] MLO on: a soft restart can leave Wi-Fi accepting no devices until a power cycle** **[options offered 2026-11-01; owner call]** ↳ notes: `mlo-restart-radio-link.md`
- **[P3] Update-manifest signature stays inert (R09)** **[accepted]** ↳ notes: `manifest-signature-inert-r09.md`
- **[P3] System log with many devices: per-device messages (Wi-Fi joins, DHCP, band steering, driver) all go to flash at debug level - look at a RAM log with the durable copy on the USB store, quieter sources, a rate cap** **[not started; owner 2026-11-09; measured on the owner's box]** ↳ notes: `syslog-scaling-many-devices.md`

---

## Audit Findings

*Open items from the security and code reviews, one line each. `↳ report:` names the maintainer's
private review report and the finding ID in it; review reports are never published.*

- **[P2] Owed router checks for the 2026-11-03 fixes: a save on each kind of page, a held device's waiting page** **[owed]** ↳ report: `review-2026-11-03` (Still owed)
- **[P2] Vendor security reports to send (all three drafted)** **[owner]** ↳ notes: `vendor-reports-owed.md`
- **[P3] Review 2026-10-28: AiMesh add-node on 3006.102.10 and a header-key list source on a router** **[owed]** ↳ report: `review-2026-10-28`
- **[P3] Boot chain: the image-signature key** **[owner call]** ↳ report: `review-2026-11-03` E-12
- **[P3] Unused closed programs to remove after a consumer check** **[group A (about 45 files) out of the image in v3.7.5; group B owes a router check each]** ↳ report: `review-2026-11-03` F-11 · notes: `unused-programs-2026-11-09.md`
- **[P3] IPsec: the remote ID validation call passes its two arguments in swapped order (stock code)** **[owner call]** ↳ notes: `libwebapi-hardening.md`
- **[P3] Mount options `nosuid,nodev` on `/tmp`, `/var` and `/jffs`** **[owner call]** ↳ report: `review-2026-11-03` (owner decisions)
- **[P3] About 30 stock pages no menu reaches are still served** **[8 removed in v3.7.3; the rest with the native-UI cutover]** ↳ report: `review-2026-11-03` B-6
- **[P3] AiMesh: the mesh daemon listens while no node is paired** **[owner call: conflicts with the Devices page's pseudo-MLO mapping]** ↳ notes: `audit-findings-2026-11-05.md`
- **[P3] AI Advisor: one connection at a time; pin the client by default** **[owner call]** ↳ report: `review-2026-11-03` D-6
- **[P3] httpd ignores `-6`: its getopt string is `"sp:i:"`, so the IPv6 remote-access listener (started with `-6`) also binds IPv4 on the WAN interface and follows the LAN listener's certificate-reload flag (`httpds_reload_cert`, not `httpds6_reload_cert`)** **[found 2026-11-08; not fixed - owner call, it changes what the remote listener binds]** ↳ notes: `login-lock-per-source.md`
- **[P3] jQuery Mobile 1.4.5 (end of life) ships for the AiMesh add-node wizard** **[with the wizard rewrite]** ↳ report: `review-2026-11-03` B-4
- **[P3] Review coverage not reached: closed listener parsers, closed ioctl handlers, some stock pages** **[watch]** ↳ report: `review-2026-11-03` (Not reached)

---

## UI / UX polish

- **[P3] Reaper pages: the polishing redesign and formatting pass** **[not started]** ↳ notes: `loading-overlay-redesign.md`
- **[P3] Every button that gives no visual sign it was pressed (e.g. Encrypted DNS › Update lists: only the timestamp tells)** **[review not started; owner 2026-11-07]** ↳ notes: `button-click-feedback-review.md`

---

## Potential Features to add

- **[P1] Reaper-native UI: convert every stock page, then remove the stock pages and the theme switch** **[left: the cutover]** ↳ notes: `reaper-native-ui.md`, `native-page-migration.md`
- **[P1] Image size: the RT-BE96U root filesystem is within ~2.2 MB of its flash slot** **[v3.7.5: 2,433,024 B spare]** ↳ notes: `image-size-hunt.md`
- **[P2] Encrypted DNS: split the block into two switches (DoT/DoQ on 853, DoH)** **[designed 2026-10-21, not started]** ↳ notes: `encrypted-dns.md`
- **[P2] Code signing: manifest + images, with a pre-upload verdict** **[scheduled]** ↳ notes: `manifest-signing-shelved.md`
- **[P2] Encrypted DNS Step B: DNS-over-HTTPS on the router** **[planned in outline]** ↳ notes: `encrypted-dns.md`
- **[P2] Security review: harden the baseline against tampering** **[owner call]** ↳ notes: `security-review.md`
- **[P2] Two-tier admin credential for root-equivalent actions** **[designed 2026-10-19; owner call]** ↳ notes: `two-tier-admin-credential.md`
- **[P2] GT-BE98: move onto GPL 102.40585 (gnuton's prebuilts) via the line unification** **[not started; after Dev-unify CI]** ↳ notes: `gt-be98-gpl-40585.md`
- **[P2] Policy Routing by ASN (e.g. AS2906)** **[assessed 2026-11-06; not started]** ↳ notes: `pbr-asn-objects.md`
- **[P3] Security review: watch more settings** **[part done 2026-10-24; the rest not started]** ↳ notes: `security-review-coverage.md`
- **[P3] Dreadwatch lists on USB: a higher name limit while a USB store is attached** **[proposed; the limit to revisit]** ↳ notes: `dreadwatch-limit.md`
- **[P3] Language packs on demand: English-only image, the admin installs their language** **[idea, measured]** ↳ notes: `language-packs-on-demand.md`
- **[P3] Diag: flag a replacing `/jffs/configs/dnsmasq.conf` and a dead local DNS upstream** **[diag half in v3.4.9; rdnshc half not done]** ↳ notes: `controld-leftover-dnsmasq-conf.md`
- **[P3] Encrypted DNS: Flow Explorer names for DoT clients** **[deferred]** ↳ notes: `encrypted-dns.md`
- **[P3] Staged ("batch") changes: one save, minimal restarts** **[project]** ↳ notes: `staged-batch-changes.md`
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
- **[P4] Firewall log day files: roll today's file into numbered parts past a part size so the store cap can remove them** **[deferred: owner priority is throughput; storage is cheap and cleared by hand]** ↳ notes: `fwlog-storage-row-layout.md` (item 2)

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
- **Mimic (hardware port mirror to an external IDS): not building - a VLAN and routing rules do it** **[owner 2026-11-07]** ↳ notes: `port-mirroring-ids.md`
- **Wi-Fi VLANs (several VIDs per network, inter-VLAN ACL page): not building - little benefit, more complex data flows** **[owner 2026-11-07]** ↳ notes: `wifi-vlans-residual.md`
- **Firmware rollback / trial boot from the second slot: not building - ASUS's boot loader already recovers a failed image** **[owner 2026-11-07]** ↳ notes: `firmware-dual-slot-rollback.md`
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
- **B-8. [P3] Wi-Fi driver: "pool 0 and unit N mismatched" floods the log while a WDS link goes down (GT-BE98)** **[blocked — blob: dhd_pktfwd.o / wl_pktfwd.o are prebuilt and the .c beside them is never compiled; hide with Saved exclusions]** ↳ notes: `gt-be98-wds-drop-log-noise.md`
