# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.4.9** · 2026-10-25 <!--@stamp-->

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
- **[P2] Files under /jffs left writable by every user** (field, RT-BE88U) — files written before
  v3.3.8 kept mode 0666 through every rewrite and a backup restore, the SSH authorized keys and VPN
  keys among them. Every boot now removes write-for-everyone under /jffs before anything runs from
  it; the Security Review card and the diagnostics count any that come back.
  **[in v3.4.8; owed: on the reporter's box the first boot logs the files it fixed and their check
  lists none]** ↳ notes: `jffs-world-writable.md`
- **[P2] IPsec's /jffs/ca_files: root-run scripts 0777, private keys readable by everyone** (field,
  follow-up to the /jffs fix) — rc_ipsec.c rewrote ca_init.sh / generate.sh / awk.sh /
  pki_genkey.sh (and two /tmp scripts) 0777 on every IPsec start, after the boot sweep, and ran
  them as root. The folder and strongSwan's private/ are now root's alone (0700, no group/other
  bits), enforced at boot and on every IPsec start; scripts created fresh at 0700 and run only via
  reaper_script_ok. **[in v3.4.9, test image _r12; boot sweep confirmed on the owner's box (_r5); owed: the
  reporter's `ls -lan /jffs/ca_files` after an IPsec restart]** ↳ notes: `ipsec-ca-files-perms.md`
- **[P2] Wallguard — ad & tracker blocker, phases 1 + 2** (owner; Warden › Wallguard) —
  **[in v3.4.9, test image _r12; blocking, list swap, pause, Unbreak, on/off and Security Review cron ids
  proven on the owner's box (_r6/_r7); owed: profiles, services, safe search; release review 2026-10-25 fixes in
  v3.4.9, test image _r39 (lists fetched again after a boot before the WAN, RAM cap, history off the page's path) - owed: a
  reboot with the WAN cable out, the lists arrive within minutes of WAN up]** ↳ notes: `wallguard.md`,
  `release-review-2026-10-25.md`
- **[P2] Warden threat domains on/off did not take effect until the next dnsmasq restart** (found
  with Wallguard) — the restart request was queued from inside the running Warden service and dropped;
  dnsmasq is now restarted directly. **[in v3.4.9, test image _r12; confirmed on the owner's box: off and on
  each restart dnsmasq with the include removed / restored]** ↳ notes: `wallguard.md`
- **[P2] Encrypted DNS for devices — Step A** (owner; rednsd, DoT server) —
  **[in v3.4.9, test image _r12; owed: a phone on Private DNS connects, filtered under its own profile]** ↳
  notes: `encrypted-dns.md`
- **[P2] Encrypted DNS: block encrypted DNS that goes around the router** (owner) —
  **[in v3.4.9, test image _r12; DoH list fetch proven on metal; owed: the switched-on device checks; release review
  2026-10-25 in v3.4.9, test image _r39: ranges wider than /24 and /48 refused, the one-provider caution in amber]** ↳
  notes: `encrypted-dns.md`, `release-review-2026-10-25.md`
- **[P2] Wi-Fi Settings: Roaming Assistant cannot be switched off** (field, GT-BE98, v3.4.8) —
  Disabled hid the input carrying the 0 and Apply skips hidden inputs, so nothing was posted (since
  v3.2.2).
  **[in v3.4.9, test image _r12; owed: the reporter switches it off, `nvram get wlX_user_rssi` = 0]** ↳
  notes: `roamast-apply-inactive.md`
- **[P2] Long-Term Storage rows: Wallguard lists on USB, Wallguard / Dreadwatch blocked lookups, Encrypted
  DNS activity** (owner) — the block table stays in RAM.
  **[in v3.4.9, test image _r12; owed: metal on the owner's USB volume]** ↳ notes: `wallguard.md`
- **[P3] Wi-Fi Settings: a Time Scheduling edit could drop out of Apply; a shared row counted
  twice** (once-over after the Roaming Assistant fix) — the counter now counts both as Apply posts
  them.
  **[in v3.4.9, test image _r12; owed: a schedule edit, then another edit undone, keeps Apply live]** ↳
  notes: `roamast-apply-inactive.md`
- **[P1] Pre-build review 2026-10-21: root wrote into the USB store by path; Wallguard MAC check let a
  command through** — store writes now go through `rstore` (never follows a link); strict MAC check;
  merged-query verdicts, FIFO hang, concurrent builds fixed.
  **[in v3.4.9, test image _r12; owed: on the owner's box the Wallguard lists land on RUSB and rebuild without
  internet, Unbreak takes a real MAC, history keeps writing after the conversion]** ↳ notes:
  `review-2026-10-21.md`
- **[P2] Older store writers followed links too (rwatch device / channel / syslog history and
  incident dumps, httpd audit log, rtrafd database and health log)** — all go through `rstore` now,
  same rings and rotation.
  **[in v3.4.9, test image _r12; owed: device history, channel history, syslog mirror and audit log keep
  growing on RUSB]** ↳ notes: `review-2026-10-21.md`
- **[P1] Dreadwatch threat domains: both feeds return HTTP 410** (field + owner's box, 2026-10-21) —
  abuse.ch closed the keyless hostfiles; Dreadwatch moves to free lists (URLhaus mirror, phishing,
  C2 on; crypto, ransomware, CERT Polska, Threatview offered; the three defaults plus a frozen
  ThreatFox snapshot (owner's choice, 21 Oct 2026) as one built-in "Reaper's Basics" row).
  **[in v3.4.9, test image _r12; the snapshot in _r14; Basics + free lists confirmed on _r12 metal
  2026-10-22]** ↳ notes: `dreadwatch-abusech-410.md`
- **[P1] Test images _r8-_r10 could not be flashed and nothing said so** (owner, 2026-10-21) — 31
  backup files left in `www/` grew the rootfs past the RT-BE96U flash slot; the flasher refused the
  image and the router rebooted on the old firmware while the Firmware page reported success.
  Backups removed, the build now fails on stray files or an oversized rootfs; httpd and the page
  report a refused upload.
  **[in v3.4.9, test image _r12; owed: a refused upload shows on the Firmware page and in the system log]**
  ↳ notes: `review-2026-10-21.md`
- **[P1] DDNS certificate stuck on "Unknown or processing..." or blank** (field, 2026-10-22) — with
  Warden's router-traffic filter on and the United States blocked, the ASUS DDNS server and Let's
  Encrypt (both US-only) were dropped; the certificate is issued through a DDNS update. Both are now
  whitelisted once while ASUS DDNS / the certificate is in use.
  **[in v3.4.9, test image _r14; owed: reporters confirm]** ↳ notes: `ddns-cert-warden.md`
- **[P1] Dreadwatch: the name limit cut alphabetically, so a large optional list pushed out Reaper's
  Basics** (owner, _r12 metal, 2026-10-22) — Threatview grew to 550,170 names; one 359-character
  name would have stopped dnsmasq. Limit now filled in priority order (Basics first), 1,000,000
  names with a free-memory guard, parent-covered and over-length names dropped, every list checked
  by dnsmasq before install, /jffs copy gzipped, page names the lists left out.
  **[in v3.4.9, test image _r15; metal PASS 2026-10-22: 673,732 names, Basics fully in force, nothing left
  out, DNS 38 MB per instance, 3 s restart]** ↳ notes: `dreadwatch-limit.md`
- **[P2] Hard-coded never-block names could not be removed (Dreadwatch, Wallguard)** (owner,
  2026-10-22) — a built-in exemption outlives a compromised service or a lapsed domain bought by
  someone else. They are now one-time entries in each page's Never block box (Warden's IP whitelist
  already worked this way); names from the operator's own settings stay automatic.
  **[in v3.4.9, test image _r16; metal 2026-10-22: Dreadwatch seed PASS (13 names, logged once); Wallguard seed
  owed when Wallguard is next on]** ↳ notes: `visible-exemptions.md`
- **[P3] Samba log noise: "Unknown parameter use spnego" and "sys_path_to_bdev() failed"** (field,
  2026-10-23) — both harmless. The smb.conf generator still writes `use spnego` (and `auth methods` in
  guest mode), which Samba 4 removed; and a client's free-space query also tries a quota lookup that
  cannot match the share to a mount, logged at level 0. Stop writing the two removed lines on SAMBA4
  builds; build Samba `--without-quotas` (the router never sets quotas). Owed after: free space shown
  correctly from Windows and macOS.
  **[fixed 2026-10-23 (v3.4.9) with the CP850 and passdb lines too; _r31 on metal: no line left]**
  ↳ notes: `samba-log-noise.md`
- **[P3] Sort the Devices and Gatekeeper lists** (owner, 2026-10-23) — sortable columns on both
  pages (name, IP, connection, status...), one shared sort helper in the kit.
  **[built 2026-10-24, v3.4.9, test image _r35 (metal owed): a header click sorts, a second reverses, remembered per
  browser; one comparator in the kit (`rp.cmp`: IPs by octet, names without case, online rows ahead on a
  name sort); `tests/test_devices_gk_sort.py`; since 2026-10-25 both pages share one kit sorter (`rp.sorter`) - same
  behaviour, checked by the same vectors]** ↳ notes: `devices-gatekeeper-sort.md`
- **[P1] RAM: the Dreadwatch name list is held in RAM five times** (owner, 2026-10-23, 1 GB
  RT-BE86U) — one tmpfs file plus one copy in every dnsmasq (main + each extra network; ~37 MB each
  on the BE96U). Share one copy without letting a guest network resolve unfiltered.
  **[built 2026-10-24, v3.4.9, test image _r35 (metal owed): rc compiles the list with `wallguardc --subtree` (one list per
  feed) into one Wallguard-format table, `/tmp/reaper_nx/threat.db`, that every dnsmasq instance maps read-only
  and shared (`dnsmasq/src/reaper_nx.c`, `--reaper-nx-db`); the include shrinks to two lines; ~12 B a name
  once instead of ~54 B in each instance plus the 21 MB text (expected ~125 MB -> ~8 MB for the owner's 683k
  names - measure on metal); the longest entry still wins against dnsmasq's own config lines, Dreadwatch still
  ahead of Wallguard; hit records carry the feed ids; the table is rebuilt from `/jffs/rwarden/dns.k.gz` at boot
  (an older firmware's `dns.nx.gz` too); `tests/test_reaper_nx.py`, `test_warden_dns.py`]** ↳ notes: `ram-dedupe.md`
- **[P2] Wireless Scheduler: the SSID is not broadcast when the schedule turns Wi-Fi back on**
  (RT-BE88U tester via the owner, 2026-10-23) — the networks came back on schedule but sent no
  SSID until a reboot. Leading suspect: Reaper's backhaul parking keeps the primary BSS down, and
  the scheduler then cannot raise the network; else the stock raw driver call behind hostapd.
  **[parking side fixed 2026-10-25 (v3.4.9, test image _r38, metal owed): while a client network that is enabled in the
  settings is down - a schedule's off window - backhaul parking holds every carrier up, so the scheduler's turn-on
  runs as on stock firmware; parking resumes 60 s after every client network is back (`tests/test_amaspark_vif.py`).
  Open: the stock path (parking off) is not proven either way - the reporter's `amas_bh_park` is still unknown, and
  the one-band lab repro needs the owner's go]** ↳ notes: `wifi-scheduler-ssid-not-broadcast.md`
- **[P3] Security review: select several rows and act once** (owner, 2026-10-23) — a checkbox per
  row and select-all under Firewall › Status › Security review, with one Accept / Ignore / Existence
  only for the selection: one request, one audit record and one log line instead of one per row.
  **[built 2026-10-25 (v3.4.9, test image _r38, metal owed): checkbox column + select-all, a bar with Accept / Existence only /
  Ignore / Ignore folder valid for every selected row (a disabled one says why), Accept = one `ack_many` request,
  the rules = one save; `tests/test_review_cgi.py` runs the real CGI branch]** ↳ notes: `security-review-bulk-select.md`
- **[P3] Connections: the flow detail panel stretches on long names** (owner, 2026-10-22) — a long
  destination (`03s0.signaling.access.vivint.ai`) widens the panel: the title overflows, the
  ACCELERATED badge is cut off, the destination wraps and a horizontal scrollbar appears. Keep the
  panel's width fixed; truncate or wrap long names inside it (full name on hover).
  **[built 2026-10-25 (v3.4.9, test image _r38, metal owed): the title and the destination are cut with an ellipsis and
  shown whole on hover, the badge never shrinks, the panel never scrolls sideways]** ↳ page: `www/Reaper_Conn.asp`

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P3] Review 2026-10-24: the owner-only decisions and the merges that would change behaviour**
  (adversarial and quality agents over the whole pending delta) — decide: the hidden-input key lists
  (Q-C1-11), the Wallguard / Encrypted DNS look on the kit stylesheet (Q-C2-12 CSS), the ten stock rail
  glyphs and the firewall rail badge (Q-C2-8), refusing an all-zero WAN MAC (Q-C1-6), the `http_enable`
  default (S-B-1), the Wireless Log 5 s default; merges left because they change behaviour: one request
  helper with one timeout (Q-C1-7), the mask checks (Q-C1-6), the other sortable tables and the QoS /
  firewall address rules (Q-C2-11). **[all security, correctness and performance items in canon for
  _r36 2026-10-25; the flash items (comment strip, 82 unused tokens, kit helpers + 33 shared style
  rules, Wallguard / Encrypted DNS closures) and the `vts_rulelist` bench (JFFS-stored, kept whole) done the
  same night, unbuilt]** ↳ notes: `review-2026-10-24.md`
- **[P2] Reaper pages: settings written into page scripts without escaping** (owner, 2026-10-23) —
  httpd's `nvram_get` escapes `"` `&` `<` `>` but not `'` or backslash, so a stored value holding
  them can end the script string it is written into and run as code in the admin's browser. 319
  reads (220 settings) across 41 Reaper files. Review each and move them to
  `nvram_char_to_ascii`; a crafted backup file, an AiMesh node or the ASUS app could store such a value.
  **[found 2026-10-23 on the IPv6 page (fixed there); not started]** ↳ notes: `nvram-get-js-escaping.md`
- **[P2] AI Advisor arming code ord and lockout move to reset-proof `/data/reaper/advisor/`.
  **[plan written 2026-10-19, replaces the WPS-button plan; not scheduled]**
  ↳ notes: `advisor-arming-code-admin-reset.md`
- **[P2] Add Packet Loss to connection tab** — Investigate if packet loss can be recorded or
  monitored on the connections tab by connection. No per-flow counter exists (hardware-forwarded
  flows); feasible only as an on-demand measure for the selected connection, TCP only.
  **[researched 2026-10-18; not scheduled]** ↳ notes: `conn-packet-loss.md`
- **[P2] Research no PIN point** - Look into setting a new pin point or fully diverging from
  a PIN build.
  **[options written 2026-10-18; owner decision]** ↳ notes: `pin-strategy.md`
- **[P3] Gatekeeper device list: wrong connection type for some devices** (owner, 2026-10-25) — the
  Devices page is right for the same devices; the two pages read different data and label it by
  different rules (Gatekeeper tests the band first and has no MLO case).
  **[fixed 2026-10-25, v3.4.9, test image _r39 (metal owed): the page reads the type from the Devices data (`reaper_dev.cgi`, every
  15 s) in the Devices order (MLO, wired, band), gkd's record wired-first as the fallback; metal owed: the
  owner's rows match the Devices page]** ↳ notes: `gatekeeper-connection-type.md`
- **[P3] AiMesh: the "feedback" link after a failed node join goes nowhere** (metal audit,
  2026-10-25) — it opens `Advanced_Feedback.asp`, which Merlin's build removes and which has no
  gone-page bounce; proposed: a bounce to the Diagnostics page.
  **[fixed 2026-10-25, v3.4.9, test image _r39 (metal owed): a gone-page row bounces it to the Diagnostics page]** ↳ notes:
  `aimesh-feedback-dead-link.md`
- **[P3] Update-manifest signature stays inert (R09)** — accepted trade.
  **[accepted]** ↳ notes: `manifest-signature-inert-r09.md`

---

## UI / UX polish

- **[P3] Loading/Restarting overlay: native redesign remainder** — 24 stock `confirm()` dialogs on 9
  pages. **[owed: the confirm() pass]** ↳ notes: `loading-overlay-redesign.md`
- **[P3] USB Application: opening a sub-page from the main menu leaves its tab unhighlighted**
  (owner, 2026-10-22) — choosing a USB option from the USB Application landing menu opens the right
  sub-page, but the tab row above does not highlight it; opening the same sub-page from the tab row
  does. Cosmetic.
  **[fixed 2026-10-25, v3.4.9, test image _r39 (metal owed): the shell marks a menu page the frame opened by itself (rail, tab
  strip, address), so a reload stays on it too]** ↳ page: `www/reaper_shell.asp`
- **[P3] Reaper QoS: no unsaved-changes cue** (metal, 2026-10-22) — the × on a rule edits only the
  page and nothing says Apply is still owed (the owner's first delete was never written). A
  pending-changes bar on the Reaper pages that edit lists.
  **[not started]** ↳ notes: `reaper-native-ui.md`

---

## Potential Features to add

- **[P1] Reaper-native UI: convert every stock ASUS page, then remove the stock pages and the theme
  switch** (owner, 2026-10-22) — Reaper is its own product, not a re-theme. Ten waves: foundations
  (component kit, one menu model, httpd plumbing, parity tests) and urgent fixes first; then System,
  LAN, WAN, Wireless/Networks, USB apps, Parental/speed, VPN (one slot-model section), Logs/tools;
  AiMesh and the Repeater/Media Bridge/node flows last (no test hardware; the setup wizard stays for
  those until a tester confirms); then the cutover deletes the stock pages, the never-visible pages,
  `reaper_inject` and the stock JS/CSS.
  Owner 2026-10-23: every page, so the stock pages can go (1 GB RT-BE86U; the cutover frees flash,
  the RAM levers are in `ram-dedupe.md`).
  **[waves 0 + 1 (System, SNMP, Tweaks) on metal; System Log group built 2026-10-23 (_r25); LAN + WAN
  built 2026-10-23 (_r32, metal owed); next: VPN, Wireless]** ↳ notes: `reaper-native-ui.md` (plan + progress), `native-page-migration.md`
- **[P3] Security review: watch more settings** (owner, 2026-10-23) — it compares 24 settings and
  hashes 3 lists; candidates: admin access and passwords (hash only), the second WAN, FTP / Samba /
  SNMP / VPN servers, DNS and DDNS, Reaper's own protections switched off, the update chain, open
  Wi-Fi. Newly watched keys must not alarm after an upgrade.
  **[part done 2026-10-24 (owner, with the _r35 diag): Reaper's own protections are watched - rwarden_enable / dns /
  dns_feeds / self / dir / feeds, gk_enable / default / captive, wallguard_enable, reaper_fw_enable, reaper_pbr_enable,
  reaper_dot_srv, the country list and custom feeds hashed; a setting the accepted baseline predates is adopted into
  it silently with one log line (`test_rwatch_review.py`). The rest (admin access, second WAN, servers, DNS/DDNS,
  the update chain, open Wi-Fi) not started]** ↳ notes: `security-review-coverage.md`
- **[P3] Dreadwatch: add your own domain lists** (owner, 2026-10-23) — an Add feed on the Dreadwatch
  page like Warden's (which takes IP lists only): https URL, up to 8 lists, same name limit and
  never-block names as the built-in lists. **After the RAM item above** - every custom list would
  otherwise be held five times.
  **[not started; unblocked 2026-10-24 - the RAM item is built, a custom list is one more table bit (30
  available); check the 1 KB nvram wall on the feed-list key first]** ↳ notes: `dreadwatch-custom-feeds.md`
- **[P3] Dreadwatch lists on USB: a higher name limit while a USB store is attached** (owner,
  2026-10-22) — a Long-Term Storage row "Dreadwatch lists" (USB only, like Wallguard's): each list's
  download and the compiled copy on the volume through `rstore`, restored after a reboot without
  downloading; limit 3,000,000 with the volume present (the free-memory guard still applies),
  1,000,000 without it. The list in use always loads into RAM, never from the stick. USB does not
  reduce memory use: the one mapped table holds the names (~12 B each since 2026-10-24; ~54 B in each
  dnsmasq instance before that).
  **[proposed 2026-10-22; owner 2026-10-24: decide after the RAM item - now built, 3,000,000 names would be
  ~36 MB mapped once (about 650 MB across the old copies), so the limit itself is the lever to revisit]** ↳ notes: `dreadwatch-limit.md`
- **[P1] Image size: the RT-BE96U root filesystem is within ~1 MB of its flash slot** (68.4 of 69.5
  MB) — every added file now competes with the slot; measure the staged image, then remove or
  deduplicate what ships (the 1.7 MB logo PNG, stock pages Reaper replaced, the OUI table shipped
  twice, unused modules, compression settings; Samba/Tor/speedtest/DLNA are owner calls).
  **[2026-10-22: orphans removed in canon (1,978,368 B, headroom now ~2.7 MB); _r16 metal PASS: no
  missing-file errors, Samba tools resolve every library; image re-encodes and owner-decision
  features next]** ↳ notes: `image-size-hunt.md`
- **[P2] Encrypted DNS: split the block into two switches (DoT/DoQ on 853, DoH to known resolvers)**
  (owner, 2026-10-21) — new `reaper_dot_block`, each with its own counter; canaries and the DoH name
  list follow the DoH switch.
  **[designed 2026-10-21, not started; first job 2026-10-22]** ↳ notes: `encrypted-dns.md`
- **[P2] Code signing: manifest + images, with a pre-upload verdict.** **[scheduled]** ↳ notes:
  `manifest-signing-shelved.md`
- **[P2] Firmware rollback + trial boot from the second slot** (owner, 2026-10-23) — every flash
  already keeps the previous image in the other slot; add "roll back to the previous firmware" (no
  download) and a trial boot that returns to the known-good slot unless the new image is confirmed.
  **[researched 2026-10-18; not started]** ↳ notes: `firmware-dual-slot-rollback.md`
- **[P3] Language packs on demand: English-only image, the admin installs their language**
  (owner, 2026-10-23) — ~2.9 MB of flash back, room for more than 24 languages; packs signed (needs
  code signing above), picked by their own name and fetched in one click from the Reaper release.
  **[idea, measured; not started]** ↳ notes: `language-packs-on-demand.md`
- **[P2] Encrypted DNS Step B: DNS-over-HTTPS on the router** — Windows and browsers encrypt to the
  router. **[planned in outline; after Step A is proven on metal]** ↳ notes: `encrypted-dns.md`
- **[P3] Diag: flag a replacing `/jffs/configs/dnsmasq.conf` and a dead local DNS upstream**
  (GT-BE98 ControlD report).
  **[built 2026-10-25 as diag v1.3.49, v3.4.9, test image _r39: section 5 says when the file replaces the generated
  config and when a local upstream has nothing listening, each with a FINDING; the rdnshc half not done]** ↳ notes:
  `controld-leftover-dnsmasq-conf.md`
- **[P3] Encrypted DNS: Flow Explorer names for DoT clients** — rednsd feeds rdnsmapd.
  **[deferred]** ↳ notes: `encrypted-dns.md`
- **[P4] Advanced tier: TLS interception for URL-level inspection** — opt-in, router CA on every
  device; own threat model first.
  **[idea]** ↳ notes: `encrypted-dns.md`
- **[P3] Wi-Fi VLANs: the two missing pieces.** **[project]** ↳ notes: `wifi-vlans-residual.md`
- **[P3] Unbound beside the existing resolver path.** **[project]** ↳ notes: `unbound-resolver.md`
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

- **[P3] Delete the dead ASUS DDNS code** (owner, 2026-10-23) — asuscomm is unreachable from v3.4.9
  (boot clears it, `start_ddns()` refuses it, no GUI or app route sets it). Left in place:
  `rc/asus_ddns.c`, the asus branches of `start_ddns()` and the watchdog, the inadyn asuscomm
  plugins, the Warden asuscomm seed and its test. **[not started]** ↳ notes: `asuscomm-removal.md`
- **[P3] Kit and httpd duplicates to fold into one copy** (owner rule, 2026-10-23) — table CSS in 7
  pages, the runner request helper in 3, two ping-preset loaders, two hand-written double forks in
  httpd. No behaviour change; the http_id token stays on every runner call.
  **[listed 2026-10-23; not started]** ↳ notes: `kit-dedupe.md`
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
- **[P3] Encrypted DNS answers guest/VLAN networks over IPv4 only.** **[deferred]** ↳ notes:
  `encrypted-dns.md`
- **[P3] Wallguard: network profiles IPv4-only; merged identical lookups share one CNAME verdict.**
  **[deferred / accepted]** ↳ notes: `wallguard.md`
- **[P3] WireGuard server starts before NTP sync** — the clients wait for `ntp_ready` and retry from
  cron; the server does not. Investigate gating it the same way. **[working as intended]** 
  ↳ notes: `wgs-start-before-ntp.md`

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report is not re-investigated.*

- **GT-BE98: no DNS after ControlD was removed, downgrades did not help** — a leftover
  `/jffs/configs/dnsmasq.conf` (add-on residue). **[closed 2026-10-21]** ↳ notes: `controld-leftover-dnsmasq-conf.md`
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
