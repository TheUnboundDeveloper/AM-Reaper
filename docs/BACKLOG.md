# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.2.6** · 2026-09-23 <!--@stamp-->

What is left to do, one line per item, grouped by area. Status where known: **[owed]** (must be
done), **[blocked]** (external cause), **[shelved]** / **[deferred]** (deliberately set aside),
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

- [Work next](#work-next)
- [Open bugs / under investigation](#open-bugs--under-investigation)
- [UI / UX polish](#ui--ux-polish)
- [Features to add](#features-to-add)
- [Documentation](#documentation)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Reported, investigated, closed as working-as-designed](#reported-investigated-closed-as-working-as-designed)
- [Blocked by closed-source components — for ASUS / Broadcom](#blocked-by-closed-source-components--for-asus--broadcom)

---

## Work next

The ordered short list.

1. **[P1] Port forwards dead on an RT-BE88U since v3.1.0 — the full filter table never loads on
   that box** (review R15, reopened 2026-09-13). The general fix is built in the canon tree: a refused
   restore now names the line and applies the table without it, and rwatch and the diag report say when
   the box is running the boot skeleton. **Root cause found 2026-09-14 and fixed in v3.1.7: it is a RACE,
   not a bad ruleset.** This iptables (1.4.x) has no xtables lock, so `xt_replace_table()` returns EAGAIN
   when another process changes the table between the `*filter` snapshot and `COMMIT` — and `nat-start` is
   FORKED by `start_nat_rules()` inside `nat_setting()`, which runs BEFORE `filter_setting()`, so a user
   `nat-start` script that touches iptables (the reporter's is `tailscale-fw.sh`) races every boot. A
   COMMIT-line failure is now retried with the identical file up to five times (100/200/400/800 ms) before
   any hoist/probe/drop is considered; the same loop guards the nat restore. The refused line is still
   wanted from the reporter's router to confirm the diagnosis on that box (one command) — see the entry
   under Open bugs. **[fix in the v3.1.7_BETA image; reporter confirmation owed]**
2. **[P1] v3.2.3 — the stable candidate.** v3.2.3 (patches 0695–0698, cut 2026-09-20) is v3.2.2 plus the hover
   reasons on locked Settings cells, the four-radio tester fixes (AP Isolated leaves the tab) and the
   Warden boot deferral, autowan rate limit, rtrafd orphan fix and boot polls; v3.2.2 (0690–0694,
   2026-09-20) added the Wireless Settings tab that replaces General and Professional (the seven rows
   back, locked as stock locks them), the Warden counter fix and the Download/Upload labels; v3.2.1
   (0685–0689, 2026-09-19)
   added the Wireless Mode row's return with its 11ax coupling and the Rule Status walker fixes (C7
   cap, H6 note, VPN label); v3.2.0 (0681–0684) added the Professional row removal, the Traffic
   bridging-mode note and the two help-link fixes over v3.1.9. Reviewed against this file 2026-09-19: no open P1 is unfixed in tree, and the current
   stable line, v3.1.0 (2026-09-08), lacks the v3.1.2 WireGuard kernel fix, the v3.1.5 review fixes,
   the v3.1.7 restore-race fix and the v3.1.8 WLCSM swap. Before the stable cut: the stable channel
   path has never run with the channel marker (v3.1.0 predates it) — a miss there is a mis-named
   release, recoverable by re-dispatch; the manifest half is now proven — on 2026-09-19 the current
   `refresh_manifest.py` replayed the v3.1.0 stable publish into a scratch directory and reproduced
   main's `manifest_3006.txt` and `latest.json` byte for byte — and the image-naming half runs at
   the first main publish;
   GT-BE19000 stays a prerelease by design and gains no stable line; the release retention prune runs
   after the stable (owner, 2026-09-18); code signing (3b) is not a stability item and is the same
   posture as every stable so far. Known issues to carry in the notes: the WireGuard source-rule
   report (fix candidates in v3.1.7 and the v3.1.9 order; reporter unconfirmed), the R15 reporter
   confirmation. v3.2.3 becomes the stable release when Dev is merged to main after the beta has
   soaked.
3. **[P2] GT-BE19000 — on the roster since v3.1.4; the write-up and the diag ARRIVED 2026-09-13.**
   The tester's report (four items) and a `reaper_diag` v1.3.14 capture from a v3.1.4_BETA_noMCP box
   are in. **The decisive fact the report did not state: that router is in Access Point mode
   (`sw_mode=3`)** — and three of the four items are AP-mode behaviour in Reaper code shared by every
   model, not GT-BE19000 port defects. **All three are fixed in tree for v3.1.6**, together with a
   fourth from the same capture (the diag's false `rtrafd` warning): the socket ceilings now load in
   every operation mode, the dashboard counts clients from Reaper's own device store when networkmap
   has no leases to count from, and the Internet card names the operation mode instead of painting a
   working router red. The fix is scoped to the operation mode rather than to the model (owner,
   2026-09-13), so a routing box behaves exactly as before and a box of any model later switched to
   AP mode is covered too. The fifth item (duplicate menus off UPnP) is the only one still wanting
   data. So the port itself is so far clean — nothing in the report is specific to this model. Still
   owed with the tester: the networkmap 39995 pin check for the GT-BE98 SHM-skew class, and a
   confirming capture from the same box on a v3.1.9 or later image (v3.1.6 is superseded and on the
   retention prune list). The model stays a prerelease until the
   glitch list is closed.
   ↳ memory: `gt-be19000-port.md`
4. **[P2] Code signing, fully automated — scheduled for a release later this week** (owner,
  2026-09-13), after v3.1.6 is stable and the GT-BE19000 glitch list is triaged: images signed in
  CI with an Ed25519 trailer, the manifest signing re-enabled and automated, router-side verify on
  both install paths, and the Firmware page's pre-upload signed / NOT-signed verdict. The gate test
  (a trailered image flashing on the BE96U) runs first and alone. Details under Features.
5. **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — every cru-driven job dead on that box.
6. **[P2] Warden chain missing after an add-on update** (amtm + Diversion) — the defensive half is
   built; the root cause still wants a syslog. The suspected fault is in shared Warden code, so it
   would affect every model.
7. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — needs a repro.
8. **[P3] Build one `stable` image** — the channel marker has been through real beta builds end to
   end, but the stable path has never been exercised, and that is the path a release goes out on.
9. **[P3] Local sibling images** — the RT-BE96U and the GT-BE19000 have local images from the
   current tree; the RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro are source-only locally. The CI
   matrix builds all six from the series, so this is about a local image to hold, not the release path.
10. **[P3] CVE check 2026-08-30 residue** — the kernel one-hunk set; everything else landed in v3.1.5.
11. **[P3] Code-review tail, batch B** — two items owner-deferred; `pinTarget()` closed.

***v3.2.6 is the current beta** (cut 2026-09-23; patches 0703–0715). It carries Asuswrt-Merlin
3006.102.9's OpenVPN 2.7.7, tzdata 2026c, Wireless Log and amtm updates, and raises the OpenVPN
server's DH floor to 2048 bits; items closed by it are recorded in [`CHANGELOG.md`](CHANGELOG.md).*

*Earlier, in v3.2.5 (2026-09-23): Samba and the Traffic Analyzer ship off. In v3.2.4 (2026-09-22):
the WireGuard policy-routing reply fix. In v3.2.3 (2026-09-20): the hover reasons on locked Settings cells, the four-radio tester
fixes and the Warden, idle-CPU and boot-wait efficiency items. In v3.2.2 (2026-09-20): the Wireless Settings tab, the Warden counter fix and the
Download/Upload labels. In v3.2.1 (2026-09-19): the Wireless Mode row's return with its Wi-Fi 6
coupling, the Professional row removals and radio links, and the Rule Status walker fixes.*

*Earlier, in v3.2.0 (2026-09-19): the WiFi Professional row removal, the Traffic bridging-mode note
and the two help-link fixes.*

*Earlier, in v3.1.9 (2026-09-17): Policy Routing first-match order, the firewall rebuild contention
fixes, retried rule adds, the DNS intercept failing open, L4S and WMM removed, DoS armed state. In
v3.1.8 (2026-09-16): the vendor WLCSM libraries, Rule Status false reds, System Information. In
v3.1.7: the Rule Status walker, the firewall restore race, the Gatekeeper and VLAN apply fixes. In
v3.1.6 (2026-09-14): a refused filter line is survivable, Access Point mode as a first-class mode.
In v3.1.5 (2026-09-12): the security-review remediation (netatalk, strongSwan, Tor, avahi, lighttpd
and net-snmp), the Policy Routing failure paths, the second OpenVPN certificate cause, the Policy
Routing Target and Status columns. In v3.1.4 (2026-09-12): the first OpenVPN certificate cause, the dual-WAN DDNS restart loop,
the removal of EDNS Client Subnet, and the GT-BE19000 joining the fleet. In v3.1.3 (2026-09-11): the
Killswitch decides, the first-boot Wi-Fi page header on every sibling, the front-chain classifier,
the diagnostic report's six overstated figures, and the build test suites running in CI. In v3.1.2
(2026-09-10): the kernel fix for the WireGuard Policy Routing panic on every model, the `_BETA`
channel marker, the chain-integrity watchdog, the Warden outbound logging contract, the resolver
health check's dual-stack fallback, DoT strict order, and the auto-logout idle timer.*

---

## Open bugs / under investigation

- **[P2] Source-IP Policy Routing rule to a WireGuard client does not use the tunnel; the same rule
  to OpenVPN does** (field report 2026-09-14 on v3.1.6, follow-up 2026-09-16: "the router is fully
  functional", and the reporter's own reading of the guide — the accelerator is carrying the flow, "the
  slot is not applied to the live flow, or the flow is offloaded first"). That reading is the right
  mechanism: the flow-cache bypass is checked only on packets the CPU sees, so a flow accelerated before
  the bypass existed is never diverted; the apply script has always cleared learned flows after
  installing the bypass, so it only holds when the bypass was never installed. Two v3.1.6 gaps made
  exactly that possible and both are closed in v3.1.7: the bypass was skipped silently when the client
  interface was down at apply time (boot order) and nothing installed it later; and a rule whose target
  changed from one WireGuard client to another kept routing existing connections by the old verdict.
  A full bypass table (eight IPv4 slots, shared with VPN Director rules and WireGuard-server peers) is
  the third path and is named in the log. Neither is proven to be the reporter's cause: no capture yet.
  Wanted from the reporter on a v3.1.7 image: `reaper_diag` (section 14d), `ip rule`, `ip route show
  table wgcN`, `iptables -t mangle -nvL REAPER_PBR`, `cat /proc/blog/skip_wireguard_network`,
  `cat /tmp/reaper_pbr/skipnets`, syslog `reaper_pbr:` lines, and from the routed device a `traceroute`
  to a public address — plus which of Killswitch on/off gave WAN egress and which gave no connectivity.
  The v3.1.9 first-match order is the strongest untested candidate: the same tester's list was being
  decided by position rather than by the rule they expected. Ask for a retest on v3.1.9 or later before
  any more WireGuard work. Tester 2026-09-20: it "still does not work" on the v3.2 beta line, and they
  offer to re-create it together when there is time — that session is the capture this entry waits on.
  **Root cause found 2026-09-22 from the tester's capture and fixed in v3.2.4:** the `REAPER_PBR` jump has
  no `-i`, so the REPLY arriving on `wgcN` had the flow's mark restored and was routed by `lookup wgcN`,
  a table with no LAN route — the reply went back into the tunnel. The chain now opens with
  `-m conntrack --ctdir REPLY -j RETURN` (both families); reproduced in a network namespace, 0/10 → 10/10.
  **[fixed in v3.2.4, ships in v3.2.5 and v3.2.6; reporter confirmation on metal owed]**
  ↳ notes: `pbr-wg-livetunnel-gaps.md`
- **[P1] WLCSM protocol-31 netlink socket leak ("stuck nvram") - shipped in v3.1.8.** ASUS stock
  `9.0.0.6.102_42015` (GT-BE98 Pro image, same Broadcom BSP as our base) passes the forced-collision
  regression 10/10 where Merlin `3006.102.8_4` wedges. The fix is in two closed blobs, nothing in
  source (`/bin/nvram` is byte-identical): `libnvram.so` - `_wlcsm_init` closes its fds on re-init,
  the port candidate gets its own `wlcsm_agent+28` field instead of aliasing the saved PID, plus
  error-path cleanup - and `libwlcsm.so`, where `wlcsm_nvram_getall`'s retry is bounded with `usleep`
  backoff. Both swapped from the vendor's own copies: a blob SWAP with provenance, not a binary patch.
  All six models ship the identical pair, so canon patch `0673` carries the RT-BE96U swap, each
  sibling branch carries it on its own `router-sysdep.<model>` tree, and the clean-room build takes it
  from the hash-pinned `overlays/wlcsm-42015-blobs.tar.gz`. The `wlcsm_bindfix` LD_PRELOAD shim is
  retired and its Tools > Other Settings toggle removed; the rwatch hung-nvram reaper stays as the
  safety net until the fix has field history. Blobs, hashes and both disassemblies in
  `ASUS/audits/socket-leak-42015/` (private). The CI fleet step is proven: the v3.1.8 and v3.1.9
  Dev builds tagged all six models, and the step errors rather than skips when a tree lacks either
  file. Lab check 2026-09-19 on the v3.2.0 beta (RT-BE96U, 15 h up): both libraries hash-identical
  to the overlay, proto-31 sockets 42 against a baseline of 44, and zero orphaned sockets once every
  socket is joined to its owning process - the stage-one signature that fired on every unmitigated
  boot. **Owed:** the reproducer bundle on the cut image (10 runs, `rc=0`, no `X+1..X+9`
  accumulation). **[shipped in v3.1.8; reproducer run owed]**
- **[P1] Port forwards dead on an RT-BE88U since v3.1.0 - the full filter table never loads**
  (review R15, reopened 2026-09-13). The nat emitter was never the bug. The reporter's trace shows
  VSERVER's DNAT counters climbing and a FORWARD chain of exactly six rules ending in policy DROP -
  the boot-time skeleton `start_default_filter()` lays down before every `start_firewall()`.
  `iptables-restore` is atomic, so one rejected line in `/tmp/filter_rules` leaves the skeleton in
  place while the nat table lands: translated, then dropped.
  **Root cause 2026-09-14: a RACE, not a bad ruleset.** This iptables (1.4.x) has no xtables lock, so
  `xt_replace_table()` returns EAGAIN when another process changes the table between the `*filter`
  snapshot and `COMMIT` - and `nat-start` is FORKED by `start_nat_rules()` inside `nat_setting()`,
  which runs BEFORE `filter_setting()`, so a user `nat-start` script that touches iptables (the
  reporter's is `tailscale-fw.sh`) races every boot.
  **Shipped in v3.1.7:** a COMMIT-line failure is retried with the identical file up to five times
  (100/200/400/800 ms) before any hoist, probe or drop is considered; the same loop guards the nat
  restore. v3.1.6 shipped the surrounding work - the refused line named in syslog, the table applied
  without it, rwatch `3f` recognising the skeleton, diag `14f` reporting which table is running.
  **Owed:** the reporter's confirmation on a v3.1.7-or-later image, and the refused line from their
  `err_rules` copy (`iptables-restore --test`, exit 2 names it) to confirm the diagnosis on that box.
  **[shipped in v3.1.7; reporter confirmation owed]**
  ↳ notes: `r15-port-forwards-rt-be88u.md`; `R15-NOTES.md`
- **[P2] Warden outbound blocks appear to have stopped: the `rwarden_log` 0/1/0 question** (owner,
  2026-09-10). The emitter was never at fault and both instrumentation defects shipped fixed in
  v3.1.2 and v3.1.6 (the durable `OUT` key, and an nvram read that does not answer being its own
  state). What is left: `rwarden_log` genuinely read 0, then 1, then 0 inside 25 minutes. Its only
  writer is the Warden page's own form post, whose hidden field is filled at submit time from the
  toggle's CSS class, so a submit beating the toggle being painted would post `0`. Wanted: whether
  the Warden page was applied around 23:05 and again around 23:20 on 2026-09-11.
  **[owed — the owner's recollection or a repro]** ↳ notes: `warden-outbound-quiet.md`
- **[P2] The AiMesh card shows zero clients in a bridging mode** (GT-BE19000 tester, 2026-09-13).
  The dashboard tiles were fixed in v3.1.6 (in a non-routing mode they read Reaper's own device
  store rather than `get_clientlist()`, which needs DHCP leases and conntrack a bridging box does
  not have). The AiMesh card shows the same symptom and the shared cause is unproved — it was never
  established that the card reads the same source. **[owed — confirm the card's source, then fix or
  close]**
- **[P3] Duplicate menu entries after opening UPnP** (GT-BE19000 tester, 2026-09-13) — "UPnP" here is
  `mediaserver.asp` (UPnP Media Server, `RTCONFIG_MEDIA_SERVER=y`), not the IGD console. Not
  reproduced and not root-caused. Two candidates, both cheap to separate with one screenshot and the
  tester's add-on list: (a) the add-on overlay class — `reaper_util.js:232` records that `menuTree.js`
  is exactly the file third-party add-ons bind-mount over, and the capture reports `amtm-ish mounts: 4`
  on that box; (b) a menuTree variant mismatch — six trees ship (`menuTree.js`, `_v4`, `_GS`,
  `_BUSINESS`, `_ROG`, `_TUF`) and the GT-BE19000 is the first ROG-class model on the roster, so a
  tree Reaper's injection does not cover would show stock and injected entries together. Reaper's own
  injector dedupes by URL, which argues against (b) alone. **[needs data — a screenshot and the
  add-on list]**
- **[P2] IPv6 reaches some LAN hosts but not others** (GT-BE98 tester, 2026-09-06) — WAN on DHCP,
  IPv6 native and stateful, working until about v2.7.1; since then the router shows its IPv6, a laptop
  and a NAS get it, but hosts behind a Proxmox server do not — a Windows VM fails testipv6.com even
  with a static address. The tester also sees `nmbd: queue_query_name: interface 0 has NULL IP
  address` in the log. Whether this is the router (RA/DHCPv6 behind an SDN bridge, an ip6tables
  change in that window) or the hypervisor bridge is undecided; more detail promised.
  **[needs data]** ↳ notes: `gt-be98-ipv6-partial-lan.md`
- **[P3] Auto-logout setting has no effect** (GT-BE98 tester, 2026-09-06) — reported as present
  since before Reaper. v3.1.2 replaced the timer on every page with a true idle timer and made the
  dashboard read the setting, which covers the two shapes the report could have had; whether the
  tester's symptom survives on a v3.1.2+ image is not yet known. Which page, which browser, and
  whether a second login from another device or tab is involved, still to be captured.
  **[needs data — re-check on the current beta]** ↳ notes: `auto-logout-ineffective.md`
- **[P2] Network page: Delete does nothing on a main-network card** (owner, 2026-09-06) — two empty
  Main Network cards (per-band profiles left behind by a Smart Connect off-and-on) could not be removed
  from the page; the same writes applied by hand cleared them. Whether the delete popup, the nvram set
  or an injected-script interaction is at fault is still to be found. **[owed: repro on a spare
  profile]** ↳ notes: `sdn-mainfh-delete-dead.md`
- **[P2] Router UI on mobile-device browsers: compatibility investigation** (owner, 2026-09-06)
  — survey how the web UI behaves in phone and tablet browsers (iOS Safari, Android Chrome,
  Samsung Internet): layout at narrow widths, touch targets, the theme and loading overlays, the
  Devices/QoS/Traffic tables, and whether every page is reachable and applies correctly. Which
  pages break, on which browser, and how, still to be captured before any fix is scoped. The
  first fit shipped in v3.1.0: the shell and the dashboard collapse the rail into an icon strip
  below 680px, so a phone gets the full width; framed stock pages pan sideways until each is
  replaced by a native one. **[minor adjustments]** ↳ notes: `mobile-browser-ui-compat.md`
- **[P3] Policy Routing page: the first-open symptom was never identified** — the screenshot did not
  reach the record; the strongest candidate shipped fixed in v3.0.5. **[needs the screenshot]**
  ↳ notes: `pbr-first-open-symptom.md`
- **[P3] Two dropdowns on the System Log page offer the same severity names and only one filters**
  (found 2026-09-12 while answering "I set the log level to CRITICAL and was still spammed"). *Default
  message log level* (`message_loglevel`) sets the priority `logmessage()` stamps on its own messages
  and filters nothing; *Log only messages more urgent than* (`log_level`) is the one wired to syslogd's
  `-l` — and busybox logs priorities strictly below `-l`, so the option named *critical* excludes
  critical itself. Both labels are ASUS's. A clarifying explainer is a candidate, at the usual i18n
  cost; the labels are not dict tokens, so the scope wants checking first. (The two `log_level`
  defaults in `shared/defaults.c` noted here were the same value; the dead second copy was removed
  2026-09-13.) **[owner call]**
- **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — rwatch, Warden refresh and the PBR
  deadline watcher all dead on that box. **[needs the GT-BE98 syslog]** ↳ notes: `gt-be98-empty-crontab.md`
- **[P3] CVE / component check 2026-08-30 residue** — no reachable HIGH, nothing MED at defaults.
  The five off-by-default inherited components and the accepted update-manifest-signature trade are
  stated in [`../SECURITY.md`](../SECURITY.md) under *Known limitations*. v3.1.5 landed strongSwan
  (CVE-2026-47895), the avahi CNAME trio, Tor 0.4.9.12, netatalk CVE-2022-43634 (which the 08-30 check
  had wrongly called absent — `SECURITY.md` corrected), lighttpd CVE-2018-25103 and net-snmp
  CVE-2022-44792/3. **Remaining:** the kernel one-hunk set. ↳ notes: `cve-check-2026-08-30.md`
- **[P3] Policy Routing rebuild is not atomic (review R07, second half).** The generated script tears
  the live chain and pref band down before rebuilding, so every apply has a window with no rules.
  Design as shipped since v2.5; the window was never measured. A swap-in rebuild (build under a
  staging chain name, then rename) would close it. **[design]**
- **[P3] Policy Routing on Warden's country sets.** A geo object now drops the rule (it never matched
  anything before); the firewall engine resolves the same object to Warden's `rw_g_<cc>` set when
  Warden manages that country, and PBR could do the same — "route everything bound for country X
  through the tunnel" is a real ask. Needs the Warden set lifecycle (swap vs destroy) checked
  against a live iptables reference first. **[feature, owner call]**
- **[P3] Update-manifest signature stays inert (review R09)** — re-recorded as an accepted trade, not
  reopened. **[accepted]**
- **[P3] Review carry-forward queue (not findings):** kernel 4.19.294 CVE set (CVE-2023-52340 IPv6
  route GC and the 08-30 list), wpa_supplicant 0.6.10 on the wired 802.1X path (needs an EAP-MD5-
  specific match), the BusyBox/Quagga/e2fsprogs/wget inventory against current binaries, and the
  proprietary runtime. A second adversarial sweep of the v3.1.5 window is queued, to be run as
  sequential slices. **[queue]**
- **[P2] AiMesh: repeated pairing failures reported against Reaper** (tester via owner, 2026-09-09)
  — seven failed pairings, attributed to Reaper by the reporter; the owner is not convinced.
  Establish what "seven" counts (attempts, nodes, or reporters) before anything else. The syslog
  line offered as evidence — `parent ... partial for node ... - missing rssi_5g rssi_5g2 (still
  usable)` — is the **fixed** path, not the v2.9.3 defect, which read `skipped` and discarded the
  parent; on a CAP that heard the node on 2.4 GHz alone the `partial` line is expected output and
  is not an error. Split the problem on whether the node ever reaches the Add Node list (the
  listing gates and the join path are independent), then rule out Gatekeeper quarantine, MLO (may
  be the item below rather than a new one), and the versions on each end. **[needs data]**
  A full decompose of the feature (2026-09-09) found nothing in the listing path that accounts
  for it, and established that AiMesh ships with **no source at all** — see
  `aimesh-decompose-2026-09-09.md`, which also carries the triage of every AiMesh item below.
  ↳ notes: `aimesh-pairing-failures-tester.md`, `aimesh-decompose-2026-09-09.md`
- **[P2] AiMesh backhaul parking could park a carrier on top of a node that has just joined**
  (found by the 2026-09-09 decompose) — whether the paired-node registry lags the join is **not
  provable from source** (both files are written only by the closed `cfg_server`), so this is a
  latent risk rather than a proven defect. **Closed without knowing, shipped in v3.1.2:** a carrier
  with a station associated to it is never parked whatever the registry says, and parking is held off
  for 120 s after a search/onboarding window closes; both log on transition only. Parking is opt-in
  and off by default, so this cannot explain any report from a tester who never enabled it.
  **[CLOSED 2026-09-17 — shipped in v3.1.2. Parking is opt-in and off by default. NOTE a pairing test would need a second node, which no lab box has, so this closes on the shipped behaviour rather than on a mesh trial.]**
  ↳ notes: `aimesh-decompose-2026-09-09.md`, `aimesh-park-idle-backhaul.md`
- **[P2] MLO ON kills the AiMesh backhaul; MLO OFF restores it** (tester, GT-BE98 CAP + RT-AX92U
  nodes) — rule out the nodes' MLO capability, the cold-cycle rule and dirty-install residue before
  calling it Reaper's; a missing guardrail would be ours. **[owed: needs a mesh]** ↳ notes: `mlo-kills-aimesh-backhaul.md`
- **[P2] Warden chain missing after an add-on update** (amtm + Diversion; one field report,
  2026-08-23) — one code-plausible path (add-on `nvram get` storm → wlcsm wedge → Warden's `apply.sh`
  reads an empty LAN IP and exits after the chain was flushed). The two other hypotheses are
  code-refuted. The defensive half is built (v3.0.9, rwatch check 3c re-applies a missing
  `REAPER_WARDEN` chain once per ten minutes). The root cause still wants a syslog from a box that
  reproduces it; the original reporter's model has since left the roster, so that capture will have
  to come from elsewhere. **[needs data]** ↳ notes: `warden-crash-addon-update.md`
- **[P2] Firewall hosts rule: pasting an IP list blanks the GUI until httpd restarts** (BE88U,
  v2.7.1) — no blocking operation visible in the save/apply path. **[owed: repro]**
  ↳ notes: `firewall-hosts-paste-blanks-gui.md`
- **[P2] Heavy ping loss after a router reboot, cured only by rebooting the ONT** (GT-BE98, PPPoE
  over VLAN 835) — best fit a stale PPPoE session at the OLT; v2.5.5 ships a one-shot re-dial.
  **[owed: a capture during the fault]** ↳ notes: `ping-loss-after-reboot-ont.md`
- **[P2] Firewall engine: a failed `lastgood` snapshot may boot with no user policy** (found
  2026-09-23 answering the external audit). `rfw_write_lastgood()` unlinks `.committed` first, and a
  failed file write leaves it absent; boot then falls back to nvram, "which holds this very config"
  per the comment — stale since v2.6.9, whose migration unsets the `reaper_fw_<key>` nvram lists. So
  a confirm whose snapshot fails partway (full `/jffs`, power cut mid-write) would boot empty lists
  with the engine enabled, and `reaper_fw_confirm()` deletes the draft regardless. Reachability
  unproven: needs a failed JFFS write. **[owed: reachability, then fix]**
  ↳ memory: `reaper-fw-audit-2026-09-23.md`

---

## UI / UX polish

- **[P3] Rule Status does not witness masquerade** (tester question, 2026-09-19). The walker already
  models POSTROUTING source NAT (the hairpin row F6) but asserts nothing about LAN→WAN masquerade; a
  one-row `A1b` (expect SNAT, gated on `wan_nat_x=1`) would, and a tunnel-side row needs the walker
  to read routing tables (mark → `ip rule` → table). Restated by the tester 2026-09-20 as a catalog
  check, the same shape as "is this port-forward really in the table": for every egress interface
  (wan0, wan1, each OpenVPN and WireGuard client, a guest uplink) — is there a MASQUERADE/SNAT rule
  with `-o` naming it; is it unrestricted or scoped (`-s`, a mark, `! -d` private ranges); does a rule
  exist for an interface that is down. Advisory posture: not built. **[owner call]**
- **[P3] Tx power's lowest step** (2026-09-19). The lowest step writes `10` where stock's slider
  writes `0`, and the consumer is the prebuilt wlconf, so which is right is metal-only. Fragmentation
  Threshold follows stock from v3.2.2 (editable in Legacy mode only). **[owner call]**
- **[P3] 39 tokens are English in the 24 non-English packs** — `RQOS_117`, `RQOS_121`, `RFW_321`,
  `RFW_322` (v3.1.9), `RTRF_77` (v3.2.0), `RWFP_39` (v3.2.1) and, from v3.2.2, the Settings row texts
  `RWFP_40–43`, `RWFP_45–66` and the Warden card `RWDN_102–108`, seeded in English to keep lockstep
  (v3.2.3's 17 new tokens arrived translated, so the count is unchanged). **[owed — the next translation
  pass; owner: they stay English for v3.2.3]**
- **[P3] Firmware page: the download phase still has no true cancel** — the upload half shipped in
  v3.1.1 (the hatch reads **Cancel** and aborts the in-flight POST). During a download from the
  update server the button still says **Close** and only leaves the overlay, honestly labelled:
  the generic `webs_*` rc dispatch handles START only (`services.c` ~20175), so `stop_webs_upgrade`
  is a no-op, and `reaper_webs_upgrade.sh` runs download → verify → flash in one shot on the router.
  A real cancel there means a kill on a flash-adjacent path, which is a service change and not a UI
  one. **[deferred — needs an rc stop service]** ↳ notes: `firmware-veil-cancel.md`
- **[P3] Chain-integrity watchdog covers the Warden drop chains only** (scope note, 2026-09-10) —
  rwatch 3d asserts "ends in DROP, nothing ahead of it that ACCEPTs or RETURNs" for `RW_DROP`,
  `RW_ODROP` and `RW_SDROP`, and checks what sits ahead of the three front chains (since v3.1.3 by
  classifying it, rather than requiring position 1 — see the changelog). The Gatekeeper
  and rules-engine chains have **no equivalent invariant checked**, deliberately: they interleave
  DROP and RETURN by design, so "ends in DROP" is not a property they have and asserting it would
  produce noise, not safety. If those need guarding, the invariant has to be defined first —
  probably "the chain still contains the rules the generator emitted", which is a different and
  more expensive check. Note also that only chains are checked, not ipset **contents**; the Warden
  poison canary (rwatch 3) is the only set-level guard. (The "bare inline ACCEPT judged broad even
  with `--dport`" gap was closed in v3.1.3b — the rule is judged the way a chain is; the line that
  said otherwise here was stale, corrected 2026-09-13.) **[owed — needs the invariant defined]**
  ↳ notes: `chain-integrity-scope.md`
- **[P3] Loading/Restarting overlay: native redesign remainder** — several overlays still centre on
  the shell viewport; adopt the themed dialog page by page. **[owed]** ↳ notes: `loading-overlay-redesign.md`
- **[P3] Loader z-index raise is class-wide** — benign; scope to `#Loading` if a modal ever renders
  behind it. **[watch]** ↳ notes: `loader-zindex-watch.md`
- **[P3] Smart Connect band-mask hazards** — a `return 7;` fallback that drops 6 GHz if its guard is
  ever edited; the 6 GHz-out-of-Smart-Connect default is an owner RF decision. **[watch]**
  ↳ notes: `smart-connect-band-mask.md`

---

## Features to add

- **[P3] OSPF + BGP dynamic routing** — achievable: Quagga's ospfd/bgpd are vendored and switched
  off; kernel ready except BGP MD5. **[project]** ↳ notes: `ospf-bgp-dynamic-routing.md`
- **[P3] Wi-Fi VLANs: the two missing pieces** — a multi-VID trunk port (UI-only) and an inter-VLAN
  ACL page; everything else already ships via SDN. **[project]** ↳ notes: `wifi-vlans-residual.md`
- **[P3] Firewall DNAT / Redirect: the residual gaps** — 1:1 NETMAP, per-zone forced NTP,
  raw-protocol DNAT; extend Service Intercept, never a new page. **[project]**
  ↳ notes: `firewall-dnat-redirect-residual.md`
- **[P3] Attainder — control by names** — a generic domain blocker at the resolver step
  (Diversion-shaped, Warden-like): subscribed lists, custom entries, exceptions, per-name statistics,
  and a page that says what was refused and why. Names are answered or refused; no traffic is copied.
  Not tied to one resolver: it has to sit in front of dnsmasq's upstreams, DoT through stubby, or
  Unbound alike. **[project]**
- **[P3] Mime — copy of the flows** — switch port mirroring to an external IDS: copy the traffic of a
  port or a network to a host that inspects it (Suricata, Zeek); the router never judges it. The
  software `tc mirred` path is present; whether it sees hardware-accelerated flows is the decisive
  unknown. This is the "witness as a mirror of the flows" a tester asked for on 2026-09-20; the Rule
  Status witness is a synthetic packet and is not this. **[project]** ↳ notes: `port-mirroring-ids.md`
- **[P3] Unbound beside the existing resolver path** (tester, 2026-09-20) — a recursive, DNSSEC-validating
  resolver with its own cache, shipped in the image and selectable on the DNS page, with dnsmasq
  forwarding to it. Today the path is dnsmasq → the configured upstreams (the resolver health check in
  front, DoT through stubby); Merlin users bootstrap Unbound by hand through Entware. Needs the package
  and its libraries, the page switch, the forwarder wiring, root-hints and trust-anchor upkeep, and a
  memory-footprint check on the RT-BE96U. **[project]**
- **[P2] Code signing: manifest + images, with a pre-upload verdict** — the manifest half was
  implemented for v2.7.3 and shelved inert (re-enable = flip two switches + rebuild). Reviewed again
  2026-09-13 with the clone threat in mind: the manifest signature covers only the router-initiated
  update path; a lookalike image arrives through the Firmware Upgrade upload or a first install, so
  the images themselves need a signature (an Ed25519 trailer, now possible on the router since the
  OpenSSL 3.5 move) plus a router-side verify in the upload handler and a page-side check that shows
  a signed / NOT-signed choice before the upload starts, with the existing typed gate to proceed
  unsigned. **Owner decision 2026-09-13 (evening): SCHEDULED, fully automated, for a release later
  this week, after v3.1.6 is stable and the GT-BE19000 glitch list is triaged.** No manual signing
  step per publish: the manifest key and a separate image key live as GitHub Actions secrets, the
  release job signs each image as it publishes it, the manifest-refresh job signs the manifest in
  the commit it already makes, and the publish job runs under GitHub environment protection so the
  secrets are readable only from the release workflow on the release branch. The trade — a CI
  compromise could sign a clone — is the exposure the project already carries (whoever controls CI
  controls what is published as Reaper); signing adds a rotation path, not a new risk. Order of
  work: **(1) the gate test first and alone — a trailered image must flash cleanly on the BE96U
  through the stock flash writer and bootloader; if trailing bytes are refused, the signature moves
  inside the image and the effort roughly doubles;** (2) Ed25519 keys generated, both public keys
  shipped in the firmware (rotation path for the v2.7.3 RSA manifest key); (3) CI signing of images
  + manifest, `.sig` release assets, GitHub build attestations; (4) router-side verify in the upload
  handler and `webs_upgrade.sh`, result recorded for the About page; (5) the Firmware page's
  pre-upload verdict modal (signed → Install/Cancel; unsigned or bad → danger dialog, Cancel default,
  typed gate to proceed); (6) README/SECURITY.md key fingerprints and a "verify before you flash"
  section; RELEASE-PROCESS updated. Estimated two to three days. Ships before the firewall walker.
  **[scheduled — this week, after v3.1.6 stable]** ↳ notes: `manifest-signing-shelved.md`
- **[P3] North star — progressively replace stock GUI pages with Reaper-native ones.** Done for
  Dashboard/QoS/Traffic/Wireless/GK/Warden/Devices/Advisor/Conn/QoSDiag/Analytics/Storage/Firmware/
  Firewall/VPNRouting/Failover/About/Sysinfo — the last of those, System Information, shipped in
  v3.1.8. **[ongoing]**
- **[P3] Staged ("batch") changes — one save, minimal restarts.** **[project]** ↳ notes: `staged-batch-changes.md`
- **[P2] Firewall table walker + Rule Status page** (owner, 2026-09-13; **shipped in v3.1.8**).
  `reaper_fwsim` walks each feature's witness packets through the live tables in kernel order and
  reports the verdict plus the deciding rule. **Advisory by design** (owner, 2026-09-16): passive and
  informative, never authoritative. Five inputs - iptables/ip6tables, ipsets, the routing policy
  database, Warden's ban list, and the router's own listening sockets from `/proc/net/{tcp,udp}`.
  Catalog coverage 51 of 59 rows; host suites at 214 checks plus 23 advisory-posture checks. The
  design history, the per-row build notes and the two convergence passes are in the changelog
  (v3.1.7, v3.1.8) and the memory file; only what is still open is kept below.
  ↳ notes: `firewall-witness-catalog.md`; memory `firewall-walker-plan`; fixtures in
  `ASUS/audits/firewall-fixtures/`
  - **[P3] 8 catalog rows have no emitter** (was 14; F2 F3 F6 F7 G7 and a re-scoped H3 landed
    2026-09-15, taking coverage to 51 of 59): B4, C8, D4, D7, G3, G5, G6, H4. Each carries a stated
    reason; none is merely unwritten. G3 is deferred rather than owed because `sdn_access_rl` links
    SDNs by index.
  - **[P2] TRACE validation of the deciding rule.** Tiers 1 and 2 check the walker's verdicts against
    synthetic and fixture tables; nothing checks its **path / deciding rule** against real kernel
    TRACE output, which is its most useful and least verified output. **This cannot be done on a lab
    router:** the shipped kernel carries `# CONFIG_NETFILTER_XT_TARGET_TRACE is not set`, so `-j
    TRACE` does not exist in the firmware at all, and arming it needs a kernel config change and a
    rebuild. `CONFIG_NF_LOG_IPV4` and `xt_LOG` are in, which is what the fallback uses.
    `test_fwsim_trace.py` exists and needs root for a network namespace. **[owed]**
  - **[P3] Fixtures from a second and third topology.** Only the owner's BE96U fixture exists, so
    tier 2 proves the walker against one topology. Wanted: the R15 reporter's RT-BE88U, the box that
    motivated the feature, and a GT-BE98 with VLANs, which would exercise the four uncovered G rows.
    Collection is one command, `reaper_fwsim --dump-inputs DIR`, which masks the WAN v4 and v6
    addresses and takes nvram from an explicit allowlist rather than a prefix sweep, so a fixture
    cannot carry a key or a client list off the box. The collector lives behind `#ifndef FWSIM_HOST`,
    so no host gate covers it; read the `nv` and `topology.txt` files before sending one on.
    **[needs data]**
  - **[P3] repair-on-red - refused by design** (owner, 2026-09-16). rwatch 3g is report-only and the
    position-based heals it was meant to retire are still in `rwatch.c`, with `front_exempt` still
    referenced from `rc/reaper_hook.h`, so the walker sits alongside the heuristics rather than
    instead of them. Nothing will ever act on a red row. **[refused by design]**
  - **[P3] `rfwWitPreview` is the one walker surface never exercised** - the Rules-tab confirm-window
    preview. One arm/confirm cycle closes it. **[owed]**
  - **[P3] The ASUS admin allowlist defeats Gatekeeper's escape hatch.** With *Only allow specified IP
    address* on, `REAPER_GKI#1` RETURNs the blocked device toward the admin port and INPUT then lands
    in `ACCESS_RESTRICTION`, whose tail DROPs any source not in the admin's list - normally including
    the blocked device's. The hatch exists so that blocking the device you administer from is
    recoverable; on such a box it is not. The walker reports this as a note rather than a red, because
    it is the admin's own list deciding. Candidate fixes: emit the GK admin RETURN after the
    allowlist, or exempt the hatch port from `ACCESS_RESTRICTION` for LAN sources - each changes a
    stock chain and wants the owner's call. **[needs decision]**

---

## Documentation

- **[P3] Guide: `reaper_fw_confirm()` is not the only writer of `lastgood`** (2026-09-23).
  `reaper_fw_promote_objects()` also writes `obj`/`grp` into `/jffs/reaper_fw/lastgood/` when a
  Policy Routing change is confirmed. Reword wherever the guide or code comments call confirm "the
  only path that writes flash". **[owed]** ↳ memory: `reaper-fw-audit-2026-09-23.md`

---

## Code quality / deferred (with reason)

- **[P2] The code-review MEDIUM/LOW tail, batch B** — `do_reaper_conn_cgi` lock order and the
  iptables-restore batching are owner-deferred; `pinTarget()` is closed; the `rexport` batched sed
  and the dashboard CSS audit shipped. **[owed: the two deferred items]** ↳ notes: `code-review-tail.md`
- **[P2] Only Gatekeeper knows AiMesh exists** (structural, found 2026-09-09) — `reaper_fw.c`
  (the rules engine, including Service Intercept's DNAT chain `REAPER_FWN`), `rwarden.c` and
  `reaper_pbr.c` carry **zero** `cfg_relist` references. Not a defect today (no default deny,
  zone policy is FORWARD-only, Warden returns on LAN subnets first, PBR only marks), so harm
  needs an operator-authored rule — but it is exactly the trap recorded after the v2.7.3
  quarantine incident, and Service Intercept is the sharp edge because an intercept rewrites a
  service for every LAN source and a node is a LAN source. Wants one shared
  `reaper_aimesh_exempt()` helper rather than three open-coded copies of the registry parser.
  **[owed — before a fourth enforcement surface is added]**
  ↳ notes: `aimesh-decompose-2026-09-09.md`
- **[P3] Sibling port misses adds, renames and deletes** (found 2026-09-22 on an RT-BE86U test
  build). `port_sibling_v2` syncs files that differ from canon but not files canon added, renamed or
  deleted, so the sibling branches still hold `onion_tap.*` without `tor1_crypt_st.h`, lack twelve
  OpenSSL 3.5 files (including `include/openssl/ecdsa.h`), and keep canon-deleted www files
  (`Reaper_WiFiPro.asp`, `Reaper_BackupCard.asp`, the AdGuard images, `searchIspNameProfile.js`);
  some also carry a stale `config_base`. CI is immune (it builds each model from the series plus its
  overlay); a local sibling build breaks. Fix: have the port apply A/R/D from the canon diff, then
  re-port all five. **[owed]**
- **[P2] Firewall engine: three silent caps** (2026-09-23). A zone's interfaces past 8
  (`RFW_MAX_IFACE`), a group's resolved sets past 16 (`RFW_MAX_SETS`) and zone-policy records past 64
  (`RFW_MAX_ZPOL`) are dropped with no log line, so a DROP rule or zone policy leaves the overflow
  unmatched. Every other cap in `reaper_fw.c` logs. Fix: log each (and surface in the page), or refuse
  at save. **[owed]** ↳ memory: `reaper-fw-audit-2026-09-23.md`
- **[P3] Firewall engine: stale comments** (2026-09-23). The Phase 3 block in `reaper_fw.c` names
  nat field 7 `desc`; the parser reads it as the schedule (the file header is right). `web.c`
  `do_reaper_fw_cgi` still says drafts live in "nvram RAM"; since v2.6.9 they are files under
  `/tmp/reaper_fw/draft/`. **[owed]**
- **[P2] Warden apply runs twice at boot, once for nothing** (measured 2026-09-20 on the RT-BE96U).
  `start_services()` runs `sh /tmp/rwarden/apply.sh` synchronously in pid 1 (~6 s: awk split of the 1.7 MB
  cache 0.6 s, per-set `ipset restore` 1.6 s, counter snapshot 0.6 s, 317 iptables calls ~3 s), then the
  WAN-up `start_firewall()` deletes the chains and re-runs the same script under the firewall lock. The
  boot-time run protects nothing (no WAN exists yet) and delays `start_wan` by its whole length. Fix: on
  the first `start_rwarden()` after boot, generate the scripts and skip the apply, exactly as the existing
  LAN-not-ready deferral does, keyed on a tmpfs marker `apply.sh` writes at its tail; the WAN-up hook
  arms it, rwatch's missing-chain heal is the fallback for a router with no WAN (log that case, so the
  Warden card explains itself). Checked per configuration: AP/repeater/media-bridge unchanged; static
  WAN arms inside `start_wan`; DHCP/PPPoE/USB-modem at `wan_up`; dual WAN per unit's `wan_up`; routed
  IPTV units pass `wan_up`, bridged IPTV never traverses the chains; captive portal arms inside
  `start_services`. Gatekeeper (LAN-facing, small) and the native firewall (operator rules) stay
  synchronous. Not async: an apply overlapping the WAN-up apply is the v3.1.9 watcher fight.
  **Built in v3.2.3**, with one change to the design: the marker is written by the firewall build itself
  (`/tmp/.reaper_firewall_built`, also by a completed apply), not by Warden alone, so enabling Warden
  from the page after boot arms at once; rwatch words the no-WAN case. **[metal measure owed: the boot
  gap, the chains after WAN-up, rwatch's first tick]** ↳ notes: `boot-efficiency.md`
- **[P2] pid 1 burns 4.5 % of a core at idle: two wake sources, one of them ours** (measured 2026-09-20,
  owner-confirmed by pausing wanduck: 72 → 38 cs per 15 s). Every wake of init's signal loop runs
  `check_services()`, four full `/proc` scans, 34 ms each. (a) Stock: `wanduck.c` `chk_proto()` requests
  `restart_autowan` on every 5 s scan for single-WAN configs with no state gate, so rc kills and respawns
  the port prober forever while the WAN is connected. Fix: rate-limit to once a minute while
  `WAN_STATE_CONNECTED`, keep 5 s otherwise — the blob's contract is unknown, so probing is slowed, not
  removed; dual WAN is already excluded by the `wans_dualwan` condition; IPTV/VPN uninvolved. Metal:
  move the cable between ports. (b) Ours: `rtrafd` `rt_bound()` kills its watcher subshell but not the
  `sleep` the watcher forked, so seven `sleep 3` per 4 s class poll are orphaned to pid 1 (eight seen
  parented to init at once). Fix: the watcher traps TERM and kills and reaps its own sleep (one
  format-string change; the long-term shape is fork+exec with a poll deadline). Gate: the v2.8.6 popen
  harness plus `pgrep -P 1 sleep` empty on the box. Expected idle busy ~2 % instead of 3.7 %.
  **Built in v3.2.3** (the watcher forks its sleep before arming the trap, on purpose; the main shell
  reaps the watcher too). **[metal measure owed: init cs per 15 s, autowan once a minute, no sleep
  parented to pid 1, the moved-cable re-detection]** ↳ notes: `idle-cpu-burners.md`
- **[P3] Boot: fixed sleeps that guard an observable condition** (measured boot 133 s to settled;
  `/proc` start-time timeline in the notes). Reached on this build: two `sleep 3` around the `/data`
  mount and `bcm_knvram` load (readiness = `/data` being a mount point, then the wlcsm netlink family
  the module registers — there is no `/dev/nvram` on this platform, and `/proc` is not mounted yet at
  that point, so neither poll reads it), `sleep(1)` after `hotplug2`, and a 300 ms wait in
  `start_dhd_monitor` that only serves a previous instance. Polls with a 10 s ceiling are never earlier
  than the fixed sleep on a slow model and shorter on a fast one; both flash layouts share them. ~7 s.
  Hold the two `sleep 3` conversions at beta until a sibling-model boot report arrives; the USB power
  cycle stays where it is (USB-modem WAN and boot-time mount ordering). **Built in v3.2.3** — the hotplug2
  poll watches for its uevent netlink socket, the debug_monitor wait runs only when an instance exists.
  **[beta soak]**
  ↳ notes: `boot-efficiency.md`
- **[P3] Boot: three daemons that looked consumer-less — kept** (re-checked 2026-09-20 at the moment of
  change, as the entry asked): `netool` answers `/netool.cgi` for the installed Network Analysis and
  Netstat pages; `sysstate` writes the CPU, RAM and temperature logs the feedback report packs;
  `dns_dpi_check` supervises `dnsqd`, which the Bandwidth Monitor page starts (reachable because
  `dns_dpi` is in `rc_support`). None is dropped; the earlier claim came from a grep against the wrong
  path. `rstats` stays too — its history files may be read by user scripts. Deferring VPN- or firewall-adjacent starts
  (`wgsall`, `pptpd`, OpenVPN, PBR, Gatekeeper, native firewall) past `start_wan` is **not** proposed:
  their order relative to the firewall build matters. **[closed — no change]** ↳ notes: `boot-efficiency.md`
- **[P2] Warden chain build as one `iptables-restore --noflush` payload per stack** — the 317 iptables
  calls in `apply.sh` (each a full table read-modify-write on a ~500-rule filter) are ~3 s of every
  firewall rebuild: boot, WAN-up, every `restart_firewall`, every Apply. Verified in the tree: iptables
  1.4.18's restore with `--noflush` flushes and rebuilds only the user chains the payload declares and
  touches nothing else, so a payload naming only `REAPER_WARDEN`/`RW_*` cannot reach OpenVPN, WireGuard,
  IPTV, Gatekeeper, native-firewall or stock chains. Conditions: the jump into the shared front chain
  stays a separate insert; runs under the firewall lock (1.4.18 has no xtables lock or `-w`, and a
  restore COMMIT overwrites the table image, so an unlocked concurrent writer loses its rule — the same
  race the P1 above records, per call, so total exposure drops); a failed COMMIT falls back to the
  per-rule script. This is the batching item deferred in the code-review tail, now with a number.
  **[owed — own rung: metal soak plus a VPN reconnect during an apply]** ↳ notes: `boot-efficiency.md`
- **[P3] Boot: what is not to be reordered, and why** (so the question is not re-opened): the three radio
  dongle probes run sequentially in the kernel from one `insmod dhd` and interfaces are named by probe
  order (a prebuilt `wl_ifname_align_war()` already exists) — no async probe; radio configuration is
  MLO-ordered — no parallel `wlconf`; `start_wan` follows `start_services` because the WAN-up rebuild
  is an iptables-restore without `--noflush` that would flush every NAT-touching service started after
  it, and wanduck (started inside `start_lan`) is what kicks NTP; `start_service_ready` and
  `success_start_service` are the watchdog's boot barrier. The remaining budget is kernel 20 s, radio
  firmware 17 s, closed-source wireless bring-up 34 s, DHCP 12 s, NTP 10 s. **[recorded; closed]**
  ↳ notes: `boot-efficiency.md`
- **[P3] Throughput: every dataplane interrupt lands on CPU0 by GIC default** — affinity masks say all
  four cores, delivery goes to the lowest; NET_RX softirq is ~70 % on CPU0. No CPU-path pressure on a
  hardware-forwarded box (softnet squeezed 3, dropped 10 in 80 min; Runner healthy; GDX pool full), so
  nothing to change by default — this is the packet-steering item in Open bugs, which stays gated on
  `fc_disable=1` or an active VPN, runtime-reversible, measured. Optional for many-flow boxes: a larger
  conntrack hash (buckets 16384 for max 300000). **[recorded; no change]** ↳ notes: `idle-cpu-burners.md`
- **[P3] Policy Routing: recapture of flows that leaked while the rules were absent** — healer path
  only, if ever; never a blanket `conntrack -F`. **[deferred]** ↳ notes: `pbr-conntrack-recapture.md`
- **[P3] The channel marker: BETA exercised, STABLE not yet** — the beta path has been through the
  local build, the staging step (`stage_release.ps1 -Channel`, which refuses to mix channels in one
  version folder) and the public pipeline end to end. No image has been built with `stable` since the
  marker was added, and that is the path a release goes out on. A CI-side cross-check of the published
  assets against the `prerelease` flag remains optional belt-and-braces.
  **[owed — build one `stable` image before the next release cut]** ↳ notes: `channel-marker.md`
- **[P3] GitHub release retention — the prune is the owner's to run.** The retention plan and
  `prune_releases.sh` are written (166 releases → 18 kept), and v3.1.5 made the pruner fail closed on
  an empty or comment-only manifest. The delete itself has not been run. **[owner action]**
- **[P3] Sibling worktrees carry build detritus** — the five port worktrees hold untracked build
  output from earlier local builds; `git checkout -- .` before any archive or overlay regeneration.
  The stale `rt-be88u-v300` worktree can go. **[hygiene]**
- **[P3] `/tmp` dir-ownership hardening** — one shared validate-or-refuse helper, ~11 sites.
  **[deferred]** ↳ notes: `tmp-dir-ownership.md`
- **[P3] `poll_fcache` O(n²) pairing · `do_reaper_dev_cgi` static
  snapshot arrays** — bounded, measured small, or latent-only. **[shelved]** (the `poll_classes`
  `tmctl` popen moved to the idle-CPU entry above, 2026-09-20)
- **[P3] Theme-token vocabulary consolidation (remainder of D4)** — `--panel2`/`--red*` and the
  `--line` divergence. **[owed — to the page migration]** ↳ notes: `theme-token-consolidation.md`
- **[P3] Inherited httpd core: two pre-auth robustness gaps** (an unclamped `Content-Length` drain;
  a `url[128]` off-by-one) — present in every stock build; opt-in hardening only.
  **[inherited; deferred]** ↳ notes: `httpd-inherited-preauth-gaps.md`

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report is not re-investigated.*

- **Dual-WAN: both NextDNS profiles receive DNS logs** — stubby round-robins every DoT endpoint;
  enter one. ↳ notes: `wad-dual-wan-nextdns.md`
- **Investigated, not a bug (do not re-raise)** — the `Reaper_Firewall.asp` field "XSS", Warden's own
  addresses, the `/etc/hosts` IP field, `custom_clientlist` truncation, the scrape-token stub, the
  store-chooser TOCTOU. ↳ notes: `wad-investigated-not-a-bug.md`
- **Translations — closed 2026-09-08, kept as a guard.** The functional-token pass across all 24
  languages shipped in v2.7.7 and nothing is owed: the RABT credits and jokes stay English **by
  choice**, and the rest of the entry was always a do-not-translate list — the pinned
  `value="TCP|UDP|BOTH|OTHER"` attributes that `rc/firewall.c` compares, and the deliberately
  literal strings (Splunk placeholders, Broadcom counter names, the parsed schedule placeholder,
  product names). Re-read before any translation work; do not re-file as a task.
  ↳ notes: `translations-residual.md`
- **SNMP `rwuser` — keep as-is** (owner, 2026-08-19): `rouser` would remove SNMP-SET.
- **`rwatch: FAILURE detected: warden-self-drop:<n>` is the feature reporting**, not a fault.
  ↳ notes: `wad-warden-self-drop-failure.md`
- **Firewall rule negation — considered, not building**; an ordered allow-above-drop pair already
  expresses it. ↳ notes: `wad-firewall-rule-negation.md`
- **`dig` on the Network Tools page — declined** (owner, 2026-08-24): a full dig would widen the
  shared input filter that guards the existing tools. ↳ notes: `wad-dig-network-tools.md`
- **`possible DNS-rebind attack detected` for names a LAN filter blocks** (owner, 2026-09-06) — the
  filter's `0.0.0.0` block answers trip the router's rebind guard once clients go through the router;
  set the filter's blocking mode to NXDOMAIN, keep the guard. ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **DNSSEC validation on the router fails every blocked name in a signed zone** (owner, 2026-09-06)
  — `limit exceeded: per-query subqueries` / `resource limit exceeded`: a validator downstream of a
  filter cannot validate answers the filter invents; validate in the filter, not the router.
  ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **The DDNS *Interface* selector on a dual-WAN box is stock ASUS**, present since the RT-AC86U GPL
  drop and gated by `RTCONFIG_MULTIWAN_IF` — not new in Reaper. Worth setting explicitly: `Auto`
  resolves to `wan_primary_ifunit()`, which in a load-balance pair is not a stable answer.
- **Mobile device metrics reported incorrect** (owner report, 2026-09-05) — a page-rendering
  report, not a data one. ↳ notes: `mobile-device-metrics.md`
- **AiMesh nodes refuse the firmware** (owner report, 2026-09-05) — the user reset the device and it
  worked. **[watch]** ↳ notes: `aimesh-node-firmware-refused.md`
- **Service Intercept in redirect-to-router mode with nothing listening** (owner, 2026-09-06) —
  an NTP intercept set to redirect to the router silently sent every client's time request to a closed
  port because "Enable local NTP server" was off; clients then polled every public server they knew.
  Enabling the router's NTP server is the answer; a page warning when the redirect target port has no
  listener remains a candidate. ↳ notes: `intercept-redirect-no-listener.md`

---

## Blocked by closed-source components — for ASUS / Broadcom

> Root-caused on RT-BE96U hardware; the responsible code lives in prebuilt Broadcom blobs.

- **B-1. Classful QoS WRR is non-functional on eth ports** — every port's egress_tm is created with
  8 of 8 SP elements inside the closed rdpa driver; v2.5.4 forces strict priority and removed the
  weight controls. ↳ notes: `blocked-b1-classful-wrr.md`
- **B-2. [P3] Unused onboarding/backhaul BSS generated when disabled → RADIUS log spam.** A boot-time
  suppression script did not work and was reverted. **[blocked — blob; risk-accepted]**
- **B-3. [P3] Guest Network Pro breaks the 2.5G-1 LAN port when a manual WAN VLAN is active
  (GT-BE98)** — no userspace interface to the switch VLAN/PVID table. **[blocked — blob;
  risk-accepted]** ↳ notes: `blocked-b3-guestpro-vlan-port.md`, `GUESTPRO-2.5G-VLAN-PLAN.md`
- **B-4. [P3] Dynamic preamble puncturing needs the 2025 Broadcom SDK** — only the static bitmap
  exists on this SDK. **[blocked — SDK]** ↳ notes: `blocked-b4-dynamic-puncturing.md`
- **B-5. [P1] Internet speed test fails on 10 Gbit/s links** (GT-BE98 field diag, v3.0.0) — not explainable
  from source; instrumented in v3.0.5. Also a first-run-after-boot "Latency test failed" on the
  BE96U. Owner ruling 2026-09-05: not chased further. **[blocked — development]** ↳ notes: `speedtest-10g-links.md`
