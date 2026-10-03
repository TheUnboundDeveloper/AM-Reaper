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

The ordered short list. *v3.3.3 is the newest rung (cut 2026-10-03); earlier releases are in
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

- **[P2] Security Posture card clipped its right column** — `1fr` tracks floored at the Wi-Fi row and `.card{overflow:hidden}`
  cut the second column's tags under ~1500 px, at 905-1090 px and on phones ("Safari" report, Chromium repro). Fixed in
  **v3.3.3 r5**: `minmax(0,1fr)` tracks, labels truncate with a tooltip. Ask: the reporter's Safari at its usual width.
  **[awaiting field]** ↳ notes: `dashboard-posture-clip.md`
- **[P3] A `dbg:` memory dump landed in syslog at the end of every boot** — stock `init.c` called the closed `slabdbg()`
  (rc/broadcom.o: meminfo, free, slabinfo, bpm status, ~230 lines, no gate) after `start_services()`; now behind the stock
  `dbg` nvram flag, **v3.3.3 r5**. Ask: one boot log with no `dbg: command:` line. **[awaiting field]** ↳ notes: `dbg-boot-dump.md`
- **[P2] Diagnostics button froze the whole GUI for the length of the collection** — httpd ran the collector inline (perf
  audit P2); now a detached worker, the page starts it, polls every 2 s and fetches the report, **v3.3.3 r5**. Ask: a diag
  run with a second tab still responsive, and the report still downloads. **[awaiting field]** ↳ notes: `diag-collector-detached.md`
- **[P2] Warden page poll forked ~360 processes every 30 s inside httpd** — `ipset -t list` + `sed` per set (audit P13);
  now one header listing parsed once, **v3.3.3 r5**. Ask: the Warden page open for a minute with the GUI responsive and the
  same threat / geo counts as before. **[awaiting field]** ↳ notes: `warden-stats-one-listing.md`
- **[P2] Warden cache replay re-fed every set on every firewall rebuild** — up to 800k add-lines into already-populated sets
  on each WAN bounce or Apply (audit P9); now skipped when the live set holds entries, **v3.3.3 r5**. Ask: `rwarden: cache
  replay: N set(s) already populated, skipped` after an Apply, and a boot that still restores. **[awaiting field]**
  ↳ notes: `warden-replay-skip.md`
- **[P3] rtrafd ran tmctl and ping through a four-process shell wrapper** — seven queries per 4 s under HW QoS, ~7 forks/s
  (the idle-churn item); now fork+exec with a poll() deadline, **v3.3.3 r5**. Ask: QoS class tiles still live, `ps | grep -c
  "[s]leep 3"` = 0, no `did not answer` line. **[awaiting field]** ↳ notes: `rtrafd-exec-no-shell.md`
- **[P3] Three needless writes: the fqdn set cache to /jffs every 10 min, `bondst` nvram every 10 s, a clientlist nvram
  write per poll** — each now only when the value changed (audit P14 / P35a / P30), **v3.3.3 r5**. Ask: the fqdn cache
  files' mtimes stop advancing on a static list. **[awaiting field]** ↳ notes: `write-only-when-changed.md`
- **[P2] A USB volume whose first mount fails is never mounted** — the hotplug add is one-shot; `rc/reaper_usbmon.c` re-sends
  the block event for an attached, never-mounted partition (3 tries, 30 s apart, 30 min window), in **r4**. Ask: a boot
  where `sending its mount event again` is followed by the mount. **[awaiting field]** ↳ notes: `usb-boot-mount-chain.md`
- **[P3] The 120 s pre-mount cap could cancel a long disk check** — 300 s for pre-mount only, in **r4**. **[awaiting field]**
  ↳ notes: `usb-boot-mount-chain.md`
- **[P3] RT-BE96U / RT-BE86U have no USB power control** — `pwr_usb_gpio` 255; the mount watchdog re-enumerates a disk-less
  storage device once at 10 min (`authorized` 0/1, else xhci unbind/bind), logged UNTESTED, in **r4**. **[metal owed]**
  ↳ notes: `usb-boot-mount-chain.md`
- **[P3] A flash that fails after the USB release left its flag** — the watchdog clears a flag older than 10 min with no
  image waiting, restarts rtrafd and remounts, in **r4**. **[awaiting field]** ↳ notes: `usb-release-before-flash.md`
- **[P3] dnsmasq `conf-file=`/`conf-dir=` into `/opt` was not guarded** — a missing one is dropped and logged, the watchdog
  restarts on its return, in **r4**; a `log-facility` in `dnsmasq-sdn.postconf` is still unguarded. **[awaiting field]**
  ↳ notes: `usb-boot-mount-chain.md`
- **[P2] Firewall engine: three silent caps** (`RFW_MAX_IFACE`/`_SETS`/`_ZPOL`) — each logs once per ruleset and the page
  refuses them (RFW_323-325), **v3.2.9**. **[metal owed]** ↳ notes: `rfw-silent-caps.md`
- **[P2] Warden chain build as one `iptables-restore --noflush` payload** (~3 s per rebuild) — shim + per-rule fallback,
  host-tested, **v3.2.9**. **[metal owed: soak + a VPN reconnect during an apply]** ↳ notes: `warden-restore-batch.md`
- **[P3] Rule Status: VPN-server rows red on an RT-BE86U** — test address in `rw_threat`; the
  picker saw only 32 sets, **fixed v3.3.0**. Ask: version + blocked-country count. **[awaiting field]**
  ↳ notes: `fwsim-wansrc-set-cap.md`
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
  REBOOTING screen; **fixed v3.3.2**. The form also shifted the login rows out of the layout rule (GT-BE98
  screenshot); selector fix in **r5**. Ask: one factory reset through the box in Chrome.
  **[awaiting field]** ↳ notes: `firstboot-box-autofill-reboot.md`
- **[P1] A firmware flash left the Entware USB volume busy, then dirty; the next boot had no DNS**
  (RT-BE86U) — release before the eject + `rc_service` cleared at boot, **fixed v3.3.2**; the 2026-10-02
  "still broken" report flashed FROM v3.3.1 (fix not exercised). RT-BE96U flash FROM v3.3.2 2026-10-02: release
  ran, rtrafd saved, clean mount next boot. Field 2026-10-02: the flash path now works; a GUI **reboot** brings the
  failure back - init's reboot path ran services-stop in the background and unmounted seconds later with Entware
  still up (35 busy retries, lazy detach). Checked 2026-10-02: a detached ext4 still unmounts cleanly once its last
  process dies, and `shutdn()` kills everything before `reboot()` - so a dirty volume on the reboot path needs a holder
  that is not a process: the swap file on the volume (amtm), whose hook `swapoff` can fail ENOMEM while Entware is still
  up. Reboot/halt now run `reaper_usb_release reboot` first (services-stop to completion, holder sweep, then `swapoff`
  of every swap under `/tmp/mnt` - the flash path gets the swapoff too), `stop_services()` skips the second
  services-stop; in r4. RT-BE96U r4 GUI reboot 2026-10-02: `reboot: releasing USB volumes before the unmount`, rtrafd
  saved, `init: USB partition unmounted` 12 s later with no busy line, the next boot (`BOOT REASON REBOOT`) mounted
  a clean journal first try at 94 s - the reboot path works on a box with no swap and no Entware. Still to ask: the
  same GUI reboot on the Entware box (`grep -E 'reaper:|unmounted|busy|swap' /jffs/syslog.log` from the shutdown -
  the `swap on ... turned off` line is the one unexercised here - and whether the next boot logs `recovery complete`).
  **[awaiting field]** ↳ notes: `usb-release-before-flash.md`
- **[P2] dnsmasq exits when its `log-facility` directory is missing; a USB volume never mounts when the
  pre-mount script outlives 120 s** (RT-BE86U, Entware/amtm) — `start_dnsmasq` drops a `log-facility` whose
  directory is missing, logs it, and the watchdog restarts dnsmasq once it exists; pre-mount's cap stops the
  whole process group and says so; `mount_r` waits out EBUSY up to 120 s; in r2 (RT-BE96U r2 boot clean, none
  triggered there). Field 2026-10-02: the tester's box booted with the SSD, four retries, waited for the
  volume - working. Still to ask: the `reaper:` lines from that boot (which mechanism fired) and one boot
  without the SSD. **[awaiting field]** ↳ notes: `usb-boot-mount-chain.md`
- **[P3] rtrafd store windows are wall-clock** — `STORE_RETRY_SECS`/`LATE_LOAD_SECS` now on CLOCK_MONOTONIC;
  in r2 (RT-BE96U r2: store attached at +15 s, before the NTP step, so the window was not exercised). Ask: no
  "never appeared within 900 s" at the NTP step on a USB-store box. **[awaiting field]** ↳ notes: `usb-boot-mount-chain.md`
- **[P2] IPv6 reaches some LAN hosts but not others** (GT-BE98) — Stateful had no SLAAC; `slaac`
  added to the Stateful range, **v3.3.1**. Ask: VM IPv6 + one diag. **[awaiting field]** ↳ notes: `gt-be98-ipv6-partial-lan.md`
- **[P3] Warden list boxes side by side at ~300 px on tablets; phones laid the shell out at 481 px** (tester
  screenshot) — `.duo` stacks below 400 px per box; the shell's phone topbar wraps instead of setting a
  width floor; in **r5**. Ask: the tester's width + one phone. **[awaiting field]** ↳ notes: `warden-list-boxes-wrap.md`
- **[P2] Every client list empty on a box that is not routing** (GT-BE19000, AP mode: Network page cards
  and Clients tab, Parental Controls, QoS pickers) — the `get_clientlist` hook now merges Reaper's device
  store with each device's network index; in **r5**. Ask: Main card count + Wired/Wireless tabs
  vs the Devices page. **[awaiting field]** ↳ notes: `sdn-clients-ap-mode.md`
- **[P3] Minimum width on Auto** (`reaper_bwfloor`, v3.3.1) — built; the floor is 80 MHz on both bands;
  re-arm while wide no longer restarts acsd2 (`picker-pending`). **[metal owed]** ↳ notes: `min-width-auto.md`
- **[P3] Static preamble puncturing** — built. **[metal owed]** ↳ notes: `preamble-puncturing-metal.md`

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
  specified. **[needs data: 3 reboots with swapon removed from post-mount]**
  ↳ notes: `usb-boot-mount-chain.md`
- **[P3] Local sibling port: canon adds and deletes did not reach a sibling branch** — RT-BE86U lacked 14 adds
  (rename detection hid 7, `\.bin$` protected OpenSSL's 7 test vectors) and kept 25 files canon deleted; CI
  images unaffected. Fixed in tooling: `--no-renames`, `openssl-3.5/test/` shared, the port removes a file whose
  blob canon once carried, parity reports it `STALE`. Dry run on rt-be86u: 21 sync, 25 delete. Sibling parity fails
  until each branch is ported (the next cut does it). **[proves at the next cut]** ↳ notes: `sibling-port-add-delete-gap.md`
- **[P2] Warden chains absent 13 min after boot on a flapping WAN** (GT-BE98, v3.2.7_BETA) — desk pass
  2026-10-02: rwatch's heal was not overdue at minute 13 (300 s grace + two-tick confirm), and every
  firewall build re-arms Warden under the lock; no reachable path found. Ask: `grep -E 'rwarden|rwatch'
  /jffs/syslog.log` over one boot + `/tmp/rwarden/failcount`. **[needs data]** ↳ notes: `warden-chains-absent-wan-flap.md`
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
- **[P2] Minimum width on Auto in an AiMesh: phones will not roam to the node** (RT-BE88U + RT-BE58) — the
  floor is CAP-only and never synced; hypothesis: it leaves only DFS channels at 80 MHz+, the node beacons
  after CAC and phones do not find a DFS BSS. **[needs data: region, backhaul, CAP + node chanspec floor on/off]** ↳ notes: `bwfloor-aimesh-roaming.md`

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
- **[P3] Flow Explorer: friendly hostname in the Destination column for internal hosts** (tester) — the
  Device cell's IP-keyed name lookup and the row's internal/external flag already exist; render name over
  address for internal destinations. **[owner: investigate]** ↳ notes: `conn-destination-hostname.md`
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
