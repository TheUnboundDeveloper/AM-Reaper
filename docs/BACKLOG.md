# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.3.4** · 2026-10-06 <!--@stamp-->

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

The ordered short list. *v3.3.4 is the newest rung (cut 2026-10-06); earlier releases are in
[`CHANGELOG.md`](CHANGELOG.md).*

1. **[P2] Code signing, fully automated** — CI-signed images + manifest, router verify, pre-upload
   verdict; gate test first. **[scheduled]** ↳ notes: `manifest-signing-shelved.md`
2. **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — every cru job dead on that box.
   **[needs data]** ↳ notes: `gt-be98-empty-crontab.md`
3. **[P2] GT-BE98 LAN5 (1G LAN-5) links but gets no DHCP** (field, v3.3.3) — the model's only 1 GbE port
   (internal GPHY: eth2 on the RTL8372 board, eth5 on the BCM board); Reaper touches no port membership or
   PHY state; stock paths that isolate one port: LAN-port Dual WAN (`wans_lanport=5`), SDN wired binding
   (blob), ebtables isolation, or the GPHY at 100 Mb/s. Diag gap owed (wans_lanport, apg dut_list, ebtables,
   per-port counters). **[needs data]** ↳ notes: `gt-be98-lan5-no-dhcp.md`
4. **[P2] Warden chain missing after an add-on update** (amtm + Diversion) — defensive half built;
   root cause wants a syslog. **[needs data]** ↳ notes: `warden-crash-addon-update.md`
5. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1). **[owed: repro]**
   ↳ notes: `firewall-hosts-paste-blanks-gui.md`
6. **[P3] Build one `stable` image** — the stable channel path has never run. **[owed]**
   ↳ notes: `channel-marker.md`
7. **[P3] Local sibling images** — RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro are source-only
   locally; CI unaffected. **[hygiene]**
8. **[P3] CVE check 2026-08-30 residue** — kernel one-hunk set; CVE-2026-90110 backport in v3.2.8
   needs the soak. **[owed]** ↳ notes: `cve-check-2026-08-30.md`
9. **[P3] Code-review tail, batch B** — two owner-deferred items. **[deferred]**
   ↳ notes: `code-review-tail.md`
10. **[P2] ZenWiFi BQ16 (BE25000) on the roster since v3.3.2** — onboarded from the ASUS 102_39256 GPL drop +
   stock radio firmware; first CI build passed in v3.3.3 (MCP + noMCP, the clean-room proof of its
   platform archive), published as a prerelease. Prerelease-only until a unit boots one. **[owed: a tester]**
   ↳ notes: `bq16-onboarding.md`
11. **[P2] ZenWiFi BQ16 Pro (BQ16_PRO) onboarding** — from its own 102_39256 GPL drop + stock radio firmware
    (2.4/5/6/6, the GT-BE98 Pro's layout); placeholder banner = the BQ16's art; MCP + noMCP built, overlay +
    platform archive in v3.3.4. **[owed: the CI run, a tester, Pro banner art]**
    ↳ notes: `bq16-pro-onboarding.md`

---

## Waiting on field response

*Fixed (in the named image or earlier) and waiting on the reporting tester to confirm. No new work
is planned; a "still broken" answer moves the item back to Open bugs. Each note says what to ask for.*

- **[P2] Warden outbound blocks appear to have stopped** — `rwarden_log` read 0/1/0. **[owed: the
  owner's recollection or a repro]** ↳ notes: `warden-outbound-quiet.md`
- **[P3] Firewall DNAT / Redirect: the residual gaps.** **[project]**
  ↳ notes: `firewall-dnat-redirect-residual.md`
- **[P3] Rule Status walker: fixtures from a second and third topology** — RT-BE88U, GT-BE98 with
  VLANs. Ask for: `reaper_fwsim --dump-inputs DIR`. **[needs data]**
  ↳ notes: `firewall-witness-catalog.md`
- **[P3] Wireless Settings: scheduler grid opens mid-page, far from its toggle** — the modal centres in the shell's
  auto-grown frame, so "viewport centre" is the document middle; now opens upper left over the clicked row. **[in v3.3.4 r1, metal owed]** ↳ notes: `wifi-scheduler-modal-position.md`
- **[P3] Diag section 3 shows two shadowed mounts with /tmp's figures** — rc's /tmp tmpfs hides the platform's
  /tmp/mnt + defaults mounts; cosmetic. Diag v1.3.26 labels the hidden rows (owner's choice). **[in v3.3.4 r1, metal owed]** ↳ notes: `diag-shadowed-mounts.md`
- **[P3] rpunctd resets on a transient chanspec read** — a scan-time iovar read logs "below 80 MHz" then
  "monitoring afresh" and drops the baseline (6x in 13 h on wl1, no CSA); a second read must agree. **[in v3.3.4 r1, metal owed]** ↳ notes: `rpunctd-scan-chanspec-reset.md`
- **[P3] System Log page: two severity dropdowns, only one filters.** Both hints now say what each
  does. **[in v3.3.4 r1, metal owed]** ↳ notes: `syslog-level-dropdowns.md`
- **[P3] Firmware page: the download phase has no true cancel** — resolved by removing the button there (owner):
  nothing can be dismissed during a download or the flash; Close on failure, Cancel only while an upload is in flight. **[in v3.3.4 r2, metal owed]** ↳ notes: `firmware-veil-cancel.md`
- **[P3] About page: the ASUS and Broadcom credit boxes read as jokes** (owner) — reworded to what each vendor
  supplies, 25 packs (`RABT_25`/`RABT_26`); page untouched. **[in v3.3.4 r2, metal owed]** ↳ notes: `about-vendor-credits.md`
- **[P3] Rule Status does not witness masquerade** — A1b added: the LAN→WAN flow must leave source-translated
  (judged on POSTROUTING like F6), n/a while NAT is off; the per-egress-interface audit is not built. **[in v3.3.4 r2, metal owed]** ↳ notes: `rule-status-masquerade-witness.md`
- **[P3] English tokens in the 24 non-English packs** — recount found 113 (the 39 plus everything seeded since);
  94 translated, 19 brand/acronym tokens kept English by design. **[in v3.3.4 r2; native review owed]** ↳ notes: `english-tokens-residual.md`
- **[P3] Chain-integrity watchdog covers the Warden drop chains only** — invariant defined and built for the rules
  engine: apply.sh signs REAPER_FW* (md5 of `-S`), rwatch 3f recomputes, a two-tick mismatch is `rules-chain-drift`, heal = the committed apply.sh, capped at two. **[in v3.3.4 r2, metal owed]** ↳ notes: `chain-integrity-scope.md`
- **[P3] Smart Connect band-mask hazards** — the dead `return 7` fallback is gone from the mask builder (no behaviour
  change); the 6 GHz-outside-Smart-Connect default stays an owner RF decision. **[in v3.3.4 r2, metal owed]** ↳ notes: `smart-connect-band-mask.md`
- **[P3] Diagnostics v1.3.28 read on r11: three small defects** — the name-map counters line called `od`, which this busybox has no
  applet for (line printed blank) -> the `hexdump` applet; a log kept on /jffs is reached through /tmp symlinks, so the rotated file was
  listed and read twice in 19b -> one entry per resolved path; the syslog mirror read "none" on a USB store with `slog` on, because rwatch
  rotated the 8 MB mirror AFTER appending and the live file was absent until the next tick -> rwatch rotates first, and the diag names
  the rotated copy. Diag v1.3.29. **[in v3.3.4 r12, metal owed]** ↳ notes: `diag-syslog-rotated-boot.md`
- **[P3] The image shipped the toolchain's x86-64 libexpat.so** — a stock Makefile line (`# why precompiled?`) copied `$(TOOLCHAIN)/lib/libexpat.so`
  into /lib of every image: 197 KB no ARM process could load (the real one is expat-2.0.1's /usr/lib/libexpat.so.1). Line removed;
  reaper_verify gained `host-arch` (no non-ARM ELF in the staged fs; engine synced). **[in v3.3.4 r12, metal owed]**
- **[P2] Site Survey stops at channel 44 (RT-BE86U)** — a 5 GHz radio under radar monitoring refuses every scan request on
  this platform (full, passive, own block, prohibited type; owner probes 2026-10-04); the stock core gets its list by moving the radio
  off the radar channel and back (prebuilt wlcscan_core_escan), which costs every 5 GHz client the change and a radar check. **Owner
  ruling 2026-10-04: option 1 - Reaper never moves the radio; the page states the limit per radio (err 4) and stops at the first
  refusal.** Built in canon, needs r6; 6 GHz and 2.4 GHz survey fine on r5. Owner 2026-10-05: r6 works; channel cards replace the bars (channel, count, 0-1/2-3/4+ colour, this router marked),
  radar line shortened to the owner's sentence - canon, needs r7. Owner 2026-10-05 (r7 metal): the 6 GHz line carried the old radar wording -> RSVY_26 re-texted (Own channel block only; the radio
  refused a full-band scan.), radio lines stacked, a bare Error now carries the exit code; and the ruling is revised: **Scan with
  channel move** - an explicit two-step button moves a radar-bound 5 GHz radio to 36/80 (or 149/80), scans the whole band, returns
  it (restore file for a killed worker; clients drop, radar check on return, AiMesh nodes follow - said on the page).
  r12 metal: the move never left 40/160 (a bare `chanspec` set only changes the configured value; stock adds the `acs_update` iovar and returns through `dfs_ap_move` when the driver has `bgdfs`) and every exit code read -1 (the worker inherits httpd's SIGCHLD reaper). Fixed in canon 2026-10-05: stock method (chanspec + acs_update, operating-chanspec check, dfs_ap_move return when bgdfs), SIGCHLD reset, click decides, raw radar line on the page, RSVY_32 re-texted (batch R). **[in v3.3.4 r13, metal owed]** ↳ notes: `site-survey-page.md`
- **[P3] Flow Explorer labels VLAN / guest sources with the WAN address** — the CGI's lan flag was the nvram br0
  subnet only; now every live `br*` subnet, nvram as the fallback. **[in v3.3.4 r3, metal owed]** ↳ notes: `conn-lan-flag-br0-only.md`
- **[P3] stop_lan trace says "wl radio off eth1..eth4"** — the marker now fires for `wl*` names only; the stock
  wlconf/wl calls are untouched. **[in v3.3.4 r3, metal owed]** ↳ notes: `stop-lan-trace-eth-label.md`
- **[P3] A hand-set `wlcsm_bindfix=1` logs "retired ... ignored" on every boot** — the retired branch logs once more,
  then unsets and commits the key. **[in v3.3.4 r3, metal owed]** ↳ notes: `wlcsm-bindfix-stale-nvram.md`
- **[P1] ntp_ready never set when the clock is already right at the first NTP reply** (RT-BE86U, two diags 2026-10-04) —
  busybox ntpd runs `/sbin/ntpd_synced` with "step" only after a step (threshold 1 s); a clock pre-set by amtm RouterDate is slewed,
  the hook ignored "stratum" and "periodic", and ntp_ready stayed 0 for 36+ min with WireGuard, OpenVPN, diskmon, ddns and every
  add-on NTP wait behind it. Fix: "stratum"/"periodic" with the exported stratum below 16 count as the first sync (logged as slewed).
  **[in v3.3.4 r5 (RT-BE96U); a BE86U build is the real test; tester confirm: `Started ntpd` lines without `Initial clock set` + `nvram get ntp_ready` 0 with the clock right]**
  ↳ notes: `be86u-warm-reboot-ntp-never-syncs.md`
- **[P3] reaper_diag syslog sections miss a rotated boot** — 19/19b read /tmp/syslog.log (+ mirror) only; a busy box rotates
  the boot into syslog.log-1 within ~25 min and span / syslogd-starts / custom_script counts then describe a window that
  starts after boot (BE86U 2026-10-04). Proposed: read syslog.log-1 first + findings "live log starts N min after boot",
  "ntp_ready=0 N min after boot", "probes 100 % loss"; print ls -l + first line of /tmp/syslog.log* /jffs/syslog.log*;
  section 5 prints ntp_ready / ntp_server0 / dns_local_cache. Built as diag v1.3.28: slog_files emits syslog.log-1 (jffs and tmp)
  ahead of the live file, 19b lists each file's size and first stamp and says how long after boot the live log starts (finding),
  section 5 prints the ntp line with a WARN when ntp_ready is not 1 after 5 min, section 16 WARNs when every probe lost 100 %.
  **[in v3.3.4 r8 (diag v1.3.28), metal owed]**
  ↳ notes: `diag-syslog-rotated-boot.md`
- **[P3] rdnshc fails a healthy resolver over whenever the uplink is down** — AdGuard on br55 answers a real-query probe only
  through the WAN, so every WAN blip costs a failover, a re-apply after wan_up's stock rewrite, a restore 3 hits later and two
  extra dnsmasq reloads (owner 2026-10-04 19:45-19:46, 93 s). Now a miss is not counted while `link_wan` reads 0 or `wan0_state_t` is set and not 2; hits always count. **[in v3.3.4 r4, metal owed]**
  ↳ notes: `wan-rehome-dns-blips-2026-10-04.md`
- **[P3] rwatch incident bundle swamps its own syslog tail** — `fcctl status` and `bpmctl status` print ~150 kernel lines
  before the dump takes its 200-line tail, so the owner's 19:45:08 bundle (reason wan-gw) held BPM tables and not the WAN
  loss; the dump now takes dmesg and a 300-line syslog tail first. **[in v3.3.4 r4, metal owed]** ↳ notes: `wan-rehome-dns-blips-2026-10-04.md`
- **[P3] Policy Routing rebuild is not atomic** (R07, second half) — every apply and every VPN event that regenerates tore the
  mark chain, the 9000-band rules and the bypass entries down before rebuilding: a window with no rules, new flows out the WAN,
  tunnel flows cut mid-stream. Now a swap-in: the new chain is built under the other name, the PREROUTING jump is replaced in
  place, the old chain dropped and the new one renamed; routing rules already live are kept and counted, the missing ones added,
  only OUR stale ones removed afterwards; bypass entries pruned to what the new config wants. Host test 34/34 (fresh, live jump,
  changed target). **[in v3.3.4 r8, metal owed]**
  ↳ notes: `pbr-rebuild-not-atomic.md`
- **[P1] v3.3.4 overwrote the user's DTIM on upgrade** (tester, 3 → 1) — `reaper_dtim_default()` keyed "once" on a new
  `/jffs/reaper/.dtim1` marker that no earlier image wrote, so EVERY dirty flash over an older Reaper forced `wlN_dtim=1`.
  Removed (init.c call, services.c function, rc.h); verify marker now requires the log line ABSENT. Default 1 stays only
  as the compiled default (fresh/reset nvram); the explainer still says 1. Lost values cannot be restored (old value
  only in the one syslog line) - affected users re-set it. v3.3.5 = v3.3.4 + this fix only; the v3.3.4 prereleases
  were withdrawn. **[in v3.3.5, metal owed]**
- **[P2] Flow Explorer: the Advanced detail panel stayed at the top while the list scrolled** (owner) — sticky inside a
  cell shrunk to the panel's own height, and inside the shell frame (grown to the page's height) sticky never engages at
  all; the panel now slides inside its stretched cell to the shell's published visible slice (--rv-top/--rv-h; standalone:
  the window's scroll). Same pass: the two columns needed ~1157 px but stacked only below 1040 - compact band to 1110 px,
  stack below. Measured in the mock: panel top 80 px vs -530 before at a 900 px scroll. **[in v3.3.4 r12, metal owed]**
  ↳ notes: `conn-detail-panel-follow.md`
- **[P3] Flow Explorer: friendly hostname in the Destination column** (tester; owner widened it to external
  flows) — internal: a free page change; external: a passive listener (rdnsmapd: AF_PACKET + kernel filter for UDP replies from port 53, a blocking recv, a 128 KB
  table in /tmp/reaper/dnsmap that httpd mmaps and probes in place), no PTR lookups, no query log; the name the device asked
  for renders over the address in Quick Look, Advanced and the detail panel, the router's own addresses read This router; default
  on, Names toggle on the page (off removes the table). Host test 22 checks incl. the kernel filter interpreted. Off wipes the table; on runs a one-shot reverse backfill of the addresses in flight (PTR to dnsmasq, ~50/s,
  muted until a forward reply takes over). **[in v3.3.4 r10, metal owed]** ↳ notes: `conn-destination-hostname.md`
- **[P3] Quagga (zebra/ripd) dropped from the Reaper model builds** — shipped inert (~790 KB; `quagga_enable` default 0,
  no page sets it, started only for an IPTV/VoIP WAN unit) with the vty password defaulting to "zebra" on every interface. **[in v3.3.4 r2, metal owed]** ↳ notes: `ospf-bgp-dynamic-routing.md`

---

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P1] Reboot loop on an Entware box after the USB mount** (RT-BE86U) — five logs: the box crashes within
  seconds of mount + swapon + Entware on every boot the SSD came up, and runs clean on the boots it did not;
  swap on the SSD under the boot storm is the prime suspect. `kernel.softlockup_panic=0` in r2, reads 0 on the
  RT-BE96U (a 20 s stall logs instead of panicking; the hardware watchdog still catches a real hang) - the cause is
  still open. Field 2026-10-02 (tester box, v3.3.3 USB build): booted clean, waited out four retries for the
  volume, no panic or loop - the root cause is still not isolated. The stock panic comes back in the next rung:
  the watchdog arms `softlockup_panic=1` once the box is up 600 s and no USB mount has been active for 300 s (in r4);
  `mount_partition` drops it to 0 itself and stamps the time, so a replug disarms it again. Trade: a post-boot
  lockup reboots in 5 s with no trace (no pstore), where v3.3.3 would have logged the stack. RT-BE96U r4 2026-10-02/03:
  reads 0 at 196 s and 285 s, then `soft-lockup panic armed: up 624 s, no USB mount activity for 530 s` and
  `softlockup_panic` = 1 (mount stamp 94 + 530 = 624; the first watchdog tick past 600) - the re-arm works as
  specified. Field 2026-10-04 (tester, v3.3.3 beta, swap file OFF): flash boot, cold reboot and two UI reboots
  all came back, no panic or loop (n=3 without swap; the boot logs were not seen - /tmp/syslog.log had rotated).
  **[needs data: syslog.log-1 of a UI-reboot boot]**
  ↳ notes: `usb-boot-mount-chain.md`
- **[P2] The dashboard says Connected while LAN clients have no name resolution** — wanduck's `link_internet=2` comes from the
  router's own resolver (`/tmp/resolv.conf` = the WAN DNS) resolving `dns_probe_host`, so it is green whenever the uplink works,
  even when the path clients use (dnsmasq -> unbound / a LAN resolver) is dead or the tunnels are down (BE86U 2026-10-04). Proposed:
  a client-path probe through 127.0.0.1:53 beside the uplink probe; the pill reads "Connected, LAN name resolution failing" and the
  System log says which upstream is silent. **[proposed, owner call]**
- **[P3] Policy Routing on Warden's country sets.** **[feature, owner call]**
  ↳ notes: `pbr-warden-country-sets.md`
- **[P3] Update-manifest signature stays inert (R09)** — accepted trade. **[accepted]**
- **[P2] MLO ON kills the AiMesh backhaul.** **[owed: needs a mesh]**
  ↳ notes: `mlo-kills-aimesh-backhaul.md`
  
---

## UI / UX polish

- **[P3] Loading/Restarting overlay: native redesign remainder** — every Reaper fixed overlay now anchors to the
  visible slice (the Wireless Settings scheduler modal was the last); 24 stock `confirm()` dialogs on 9 pages remain. The anchoring shipped in v3.3.4. **[owed: the confirm() pass]** ↳ notes: `loading-overlay-redesign.md`

---

## Potential Features to add

- **[P3] Wi-Fi VLANs: the two missing pieces.** **[project]** ↳ notes: `wifi-vlans-residual.md`
- **[P3] Attainder — control by names** (resolver-step domain blocker). **[project]**
  ↳ notes: `attainder-name-control.md`
- **[P3] Mimic — copy of the flows** (hardware port mirror to an external IDS) — Firewall-tab mock built
  2026-10-04 (`reaper-mockups/mimic/`); open: bandwidth mismatch (10G source, 2.5G tap). **[paused - owner thinking]** ↳ notes: `port-mirroring-ids.md`
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
- **[P3] rpunctd restarts its evidence window on a one-sample background-scan chanspec** - ~15/day
  on 5 GHz. **[owed]** ↳ notes: `rpunctd-scan-chanspec-reset.md`
- **[P3] reaper_diag prints the stored puncturing gain (0) instead of the effective one (15%).**
  **[owed]** ↳ notes: `diag-punct-gain-display.md`
- **[P3] Second review of the v3.1.0–v3.1.5 code** — seven sequential slices, reachability before any
  finding. **[planned — not started]** ↳ notes: `review-carry-forward-queue.md` §4
- **[P2] Only Gatekeeper knows AiMesh exists** — wants one shared `reaper_aimesh_exempt()`.
  **[owed — before a fourth enforcement surface]** ↳ notes: `aimesh-exempt-helper.md`
- **[P3] Sibling port misses adds, renames and deletes** — local sibling builds break; CI immune.
  **[owed]** ↳ notes: `sibling-port-add-rename-delete.md`
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
- **[P3] Two stock hygiene items from the 2026-10-02 cppcheck of `rc/usb.c`** — `sd_partition_num()` reads the
  `/proc/partitions` name with an unbounded `%[^\n ]` into a 32-byte buffer (kernel-generated input, so not
  reachable; add a width), and `create_custom_passwd()` leaks its `FILE *` when the account list cannot be read
  (an rc process that exits). No behaviour change either way. ↳ notes: `usb-boot-mount-chain.md`
- **[P3] avahi CVE-2024-52615 / -52616 (wide-area: fixed source port, predictable query ID)** — wide-area is on,
  but only non-`.local` lookups use it and nothing on the box asks for one. **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] avahi CVE-2021-3468 / CVE-2025-59529 (local socket: HUP loop, no client cap)** — reachable only by
  processes on the router, all root. **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] OSPF + BGP dynamic routing.** **[Not Needed]** ↳ notes: `ospf-bgp-dynamic-routing.md`

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
- **USB storage attaches after `services-start` on every boot** — stock order: `start_usb()` loads
  usb-storage/`uas` after `start_services()` and `start_wan()`; anything started from `/opt` before the
  mount fails by design. ↳ notes: `usb-boot-mount-chain.md`
- **"Every flash rewrites the bootloader" — it does not** — the plain pkgtb carries bootfs + rootfs; the U-Boot the
  kernel names rides in bootfs (A/B slots); only the `_loader.pkgtb` writes the loader partition (2026-10-03). ↳ notes: `uboot-in-bootfs-not-loader.md`
- **Minimum width on Auto in an AiMesh: phones stay on the router** (RT-BE88U + RT-BE58) — the floor only shapes the
  router's channel pick, which AiMesh channel sync mirrors onto every node; a DFS pick silences the node 1-10 min (CAC), no roaming candidate. Floor on + DFS off, or fixed 36-48/80 (2026-10-04). ↳ notes: `bwfloor-aimesh-roaming.md`

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
