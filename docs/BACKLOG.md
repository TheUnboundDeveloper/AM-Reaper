# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.1.7** · 2026-09-15 <!--@stamp-->

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

1. **[P1] 2026-09-17 apply-window fixes - CLOSED, cut in v3.1.9.** One
   `restart_qos;restart_firewall` on the owner's RT-BE96U set three Reaper layer applies, `hook.sh`,
   rwatch 3c and the out-of-tree `reaper_dnsi` watcher fighting over FORWARD position 1 for 50 s;
   restricted devices lost DNS four times. Six fixes: Gatekeeper RETURNs router-redirected DNS
   (`--ctstate DNAT --ctorigdstport 53`); `hook.sh` takes its pin position from rwatch 3d's
   `_front_pos` instead of `-I 1`; Warden creates and refills its sets before teardown and replays
   the cache in one awk pass (was 80 passes, 17 s measured); rwatch 3c confirms over two ticks and
   heals through `heal.sh` under the firewall lock; the rules engine parks a
   DNS-Health-Check-targeted intercept in `REAPER_FWHC` with `rdnshc` gating it; L4S and the WMM
   downstream stamp removed. Verified on the owner's box on `v3.1.8_BETA_r7`: Rule Status 95 green /
   0 red, both retry counters 0, Gatekeeper audit clean, intercept 0 leaks.
   ↳ notes: `apply-window-watchdog-fight.md`
2. **[P1] Port forwards dead on an RT-BE88U since v3.1.0 — the full filter table never loads on
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
3. **[P1] v3.1.5 — the beta is out; what only hardware can settle.** The v3.1.5 beta was built by
   the public clean-room pipeline and published as a prerelease for all six models, both variants,
   on 2026-09-13. Every fix from the 2026-09-12 security review, the two OpenVPN certificate causes,
   the DDNS fix and the WireGuard kernel fix are in those images. The metal-owed list is one entry
   under Open bugs. v3.1.5 becomes the stable release when Dev is merged to main after the beta has
   soaked.
4. **[P2] GT-BE19000 — on the roster since v3.1.4; the write-up and the diag ARRIVED 2026-09-13.**
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
   confirming capture from the same box on a v3.1.6 image. The model stays a prerelease until the
   glitch list is closed.
   ↳ memory: `gt-be19000-port.md`
3b. **[P2] Code signing, fully automated — scheduled for a release later this week** (owner,
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

***v3.1.5 is the current beta** (cut 2026-09-12; patches 0653–0661; published as a prerelease for all
six models on 2026-09-13). It carries the security-review remediation (netatalk, strongSwan, Tor,
avahi, lighttpd and net-snmp fixes; the Policy Routing failure paths; the Advisor's handshake clock;
the fail-closed release pruner), the second OpenVPN certificate cause, the two new release checks and
`reaper_diag` 14f, and the Policy Routing page's Target and Status columns. Items closed by it have
been removed from this file and are recorded in [`CHANGELOG.md`](CHANGELOG.md).*

*Earlier, in v3.1.4 (2026-09-12): the first OpenVPN certificate cause, the dual-WAN DDNS restart loop,
the removal of EDNS Client Subnet, and the GT-BE19000 joining the fleet. In v3.1.3 (2026-09-11): the
Killswitch decides, the first-boot Wi-Fi page header on every sibling, the front-chain classifier,
the diagnostic report's six overstated figures, and the build test suites running in CI. In v3.1.2
(2026-09-10): the kernel fix for the WireGuard Policy Routing panic on every model, the `_BETA`
channel marker, the chain-integrity watchdog, the Warden outbound logging contract, the resolver
health check's dual-stack fallback, DoT strict order, and the auto-logout idle timer.*

---

## Open bugs / under investigation

- **[P1] Gatekeeper apply silently loses rules under a concurrent iptables writer (found on metal 2026-09-17, v3.1.8_BETA_r4).** After the r4 boot the live IPv4 REAPER_GKF chain had 124 rules where a clean re-apply gives 126: the Lutron controller (internet-only) had no final RETURN, so every WAN-bound packet from it fell to the chain-end DROP - the walker's D3a.28 red row was right, the device had no internet. The apply script emits the rule (line 850); nothing in gkd or httpd deletes it; IPv6 and INPUT had theirs. Same class as R15: this iptables 1.4.x has no xtables lock, the Gatekeeper apply makes ~200 unchecked adds, and the owner's /jffs reaper_dnsi watcher was inserting FORWARD rules at 19:01:47/57 and 19:02:02 in the same window. A lost RETURN cuts a device off; a lost DROP would give it access it should not have, silently. FIX: wrap every add in the Gatekeeper apply (and Warden's) in a retry-once-then-log helper the way reaper_fw's RFWR does, and have gkd's self-heal compare the live rule count against the script's expected count. Interim: `service restart_gk` restores the chain. **FIXED, cut in v3.1.9 (2026-09-17): `_rt_add` retry-once wrapper shadowing iptables/ip6tables/ebtables in both apply scripts, `/tmp/gk/failcount` + `/tmp/rwarden/failcount`, gkd `heal_lost_rules()` (120 s throttle, 3 strikes); verified on the owner's RT-BE96U (v3.1.8_BETA_r7: both failcounts 0, Gatekeeper audit clean). The colliding writer, the owner's watcher, is retired.** ↳ notes: `apply-window-watchdog-fight.md`
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
  **[fix candidates in v3.1.7; reporter capture owed]** ↳ notes: `pbr-wg-livetunnel-gaps.md`
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
  `ASUS/audits/socket-leak-42015/` (private). **Owed:** the reproducer bundle on the cut image (10
  runs, `rc=0`, no `X+1..X+9` accumulation), and the first CI fleet run to prove the blob step on
  every sibling - it errors rather than skips when a model's tree lacks either file.
  **[shipped in v3.1.8; acceptance owed]**
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
- **[P1] v3.1.5 - the sixteen review fixes, on the published beta images.** R01-R16 from an
  independent adversarial review, re-verified and remediated in the v3.1.5 tree; the decisions are in
  `REAPER-FIXES.md` ("Security review 2026-09-12") and the shipped account is in CHANGELOG.md v3.1.5.
  The exercises only hardware can run were: Time Machine discovery, first and incremental backup and
  an interrupted transfer (netatalk R01, the DSI struct grew, every module rebuilt cold); an IKEv2
  EAP-MSCHAPv2 connect and reconnect (strongSwan R02); Tor transparent proxying v4 and DNS after the
  0.4.9.12 bump (R03); toggling a client's Killswitch and its enable inside the Policy Routing confirm
  window, then Keep and separately Revert (R04); a full WireGuard bypass table producing E_PARTIAL
  with the syslog line naming it (R05); a geo-object rule dropped with its reason and a group
  expanding into its members (R06); an `ip rule add` failure surfacing as E_PARTIAL with rwatch
  healing an IPv6 shortfall (R07); a slow TLS handshake against an armed Advisor dropped at 20 s
  (R10); an SNMP SET with a NULL varbind answered wrongType (R13); an OpenVPN server certificate
  repaired and a new server created on an OpenSSL 3.5 image (R16).
  **[CLOSED 2026-09-17 - all sixteen shipped in v3.1.5 and the rungs since; see CHANGELOG.md.]**
- **[P2] The Policy Routing page wants a browser** (v3.1.5) — the behaviour half is confirmed on
  metal: the Killswitch A/B passed both ways from the nvram toggle plus a vpnrouting restart alone,
  and the front-chain classifier was proven on the same box and the same rule that raised a FAILURE
  on v3.1.2. What a lab session cannot see is the page as v3.1.5 left it: the Target column reading
  the interface and nothing else (`WAN` on the WAN row, the explanation as a hint in the add-rule
  list), the new **Status** column (`Active`, `Active · Killswitch`, `Inactive · WAN`), the single
  note under the table, the Apply overlay persisting until the Keep / Revert bar, and the
  Administration tab reading *DNS Failover*. **[CLOSED 2026-09-17 — shipped in v3.1.5; the Target and Status columns and the greyed cell are described in CHANGELOG.md under v3.1.5 and v3.1.6.]**
- **[P2] The rest of v3.1.2 and v3.1.3 wants a session on the box** — each of these needs to be
  looked at once: the rwatch chain-integrity watchdog (should stay silent on a healthy box, and
  tolerate a narrowed rule ahead of it), the rwatch Warden-outbound state line, the Firewall →
  Logging heading correction and the split `WARDEN-OUT` / `WARDEN-SELF` badges, the Addons menu
  opening its first page, the first-boot Wi-Fi page header on a sibling. Grouped because one session
  on the box settles all of them. **[CLOSED 2026-09-17 — all of these shipped in v3.1.2 and v3.1.3; see CHANGELOG.md.]** ↳ notes: `v312-r2-validation.md`
- **[P2] Warden outbound blocks appear to have stopped** (owner, 2026-09-10). No defect in the
  emitter; the outbound state line and the split badges shipped in v3.1.2. The line's first real
  capture found two defects in the instrumentation itself. **(a)** "blocked so far" read the live
  `RW_ODROP` counter, which `fold.sh` banks and zeroes on its own `*/15` cron, so a healthy box read
  `0` most of the time - the figure an operator quotes to conclude outbound blocking is dead.
  **(b)** rwatch 3e could not tell "logging is off" from "I could not read the flag": an `nvram get`
  killed at `_nv`'s 5 s ceiling returns empty and took the same branch as `0`, advising the operator
  to switch on something already on. Both fixed and shipped in v3.1.6 - `fold.sh` banks outbound drops
  under their own durable `OUT` key, the 3e line and the stats `out_n` figure quote banked plus live,
  and an nvram read that does not answer is its own state.
  **STILL OPEN: the 0/1/0 flag question.** (b) was ruled out at the captured timestamps, which leaves
  `rwarden_log` genuinely reading 0, 1, 0 inside 25 minutes. Its only writer is the Warden page's own
  form post, and that hidden field is filled at submit time from the toggle's CSS class, so a submit
  beating the toggle being painted would post `0`. Wanted: whether the Warden page was applied around
  23:05 and again around 23:20 on 2026-09-11. ↳ notes: `warden-outbound-quiet.md`
- **[P2] Gatekeeper: a removed device re-appeared under Pending approvals** (owner, 2026-09-15).
  Removing a device that had been off the network ~16 h put it straight back into the pending list, and
  only a reboot made the removal stick. **Not DHCP** (the natural first theory): `scan_lease_file()` calls
  `find_dev()`, never `touch_dev()`, so a lease only NAMES a device another scanner already found. The
  cause is that `pending = seen but not in gk_rl` had **no presence gate**, while `gkd` deliberately
  RETAINS a device in `/tmp/gk/seen.tsv` for `DEV_TTL` = 24 h after its last sighting so the approved
  list can still show hostname, band and first-seen. Retention is not presence. The reboot "fix" is the
  confirming detail, not separate behaviour: `seen.tsv` is on tmpfs. Pending now also requires
  `online` in the current sweep **or** last-seen within `GK_PEND_TTL` (15 min); the two tests are
  separate because pre-NTP `touch_dev()` leaves `last=0` while `online=1`.
  **[CLOSED 2026-09-17 — shipped in v3.1.7; see CHANGELOG.md.]** ↳ memory `gatekeeper` field bug 4
- **[P2] "Applying settings" hangs forever on a VLAN / SDN change** (owner, 2026-09-15, latest Edge).
  Deleting a VLAN profile, creating one, or editing a MAC filter left the dialogue with no progress bar —
  sometimes indefinitely, sometimes counting up after ~3 minutes, sometimes working perfectly. The
  randomness was the diagnosis: the stock apply idiom is `showLoading()` (indefinite) then
  `httpApi.nvramSet(obj, cb)`, where `cb` — the only caller of `showLoading(seconds)` that starts the
  10..100% bar — runs from the ajax **success** path alone, and that ajax carried a literal
  `error: function(){}`. These applies restart networking (`restart_sdn`/`restart_net`/`restart_wireless`),
  which destroys the reply to the request that asked for it, so whether the response survives is a race;
  `dataType:'json'` widens it, since a truncated body is an error, not a success. The caller contract is
  deliberately unchanged (~75 call sites are written against success-only semantics); the error path now
  recovers the UI instead, polling `httpd_check.xml` until httpd answers and then reloading, and the async
  path gained a 45 s timeout. Note this makes the UI recover — it does not make the apply faster.
  **[CLOSED 2026-09-17 — shipped in v3.1.7; see CHANGELOG.md.]** ↳ memory `reaper-ui` rule 47
- **[P2] Access Point mode: the socket-buffer ceilings never load** (found 2026-09-13 from the
  GT-BE19000 diag; affects **every model**). `start_firewall()` opens with
  `if (!is_routing_enabled()) return -1;` (`rc/firewall.c:9228`), which returns in AP, repeater and
  media-bridge mode — **before** the Reaper block at `rc/firewall.c:9478` that raises
  `net.core.rmem_max`/`wmem_max` to 16 MB and `netdev_max_backlog` to 4096. The tester's capture
  shows exactly that: `rmem_max 524288`, `netdev_max_backlog 1000`, on a box whose syslog records
  three `restart_firewall` calls hours earlier. Any throughput tool that calls
  `setsockopt(SO_RCVBUF)` — the Ookla engine included — is capped accordingly, so this is a real
  contributor to the "speed test is not consistent" report. **Fixed in tree for v3.1.6:** the three
  writes moved out of `start_firewall()`'s body into `reaper_socket_ceilings()`, and the
  `!is_routing_enabled()` return calls it on the way out. They are not firewall state and had no
  reason to sit behind that guard. Routing mode still takes the call in the same place in the body,
  unchanged. Settled by a `reaper_diag` 12 capture from an AP-mode box on a v3.1.6 image showing
  `rmem_max 16777216` and `netdev_max_backlog 4096`.
  **[CLOSED 2026-09-17 — shipped in v3.1.6, and settled by the AP-mode diag capture quoted above.]**
- **[P2] Dashboard reports zero clients while the Devices page lists them all** (GT-BE19000 tester,
  2026-09-13; **not model-specific**). Two presence sources: the dashboard polled stock
  `get_clientlist()` and skipped every row failing `String(c.isOnline)!=='1'`, while the Devices page
  reads `reaper_dev.cgi?action=status` and never consults `isOnline`. In AP mode networkmap has
  nothing to derive presence from - the same capture shows 0 DHCP leases and 0 conntrack entries - so
  the dashboard counted nothing while 16 stations were associated. **Shipped in v3.1.6:** in a
  non-routing mode the tiles read `reaper_dev.cgi`, whose `rdev` store carries `band` from the `wl`
  assoclists corrected by the bridge FDB and `online` from the assoclists, the FDB and
  `/proc/net/arp`, none of which needs a lease or a conntrack entry. They poll at 30 s rather than 10
  because `action=status` `popen()`s `wl` per radio, VIF and station on a single-flight httpd. Routing
  mode keeps `get_clientlist()` untouched. Settled by the same box on a v3.1.6 image counting its
  sixteen stations. **STILL OPEN: the AiMesh card shows the same symptom and the shared cause is
  unproved.** **[CLOSED 2026-09-17 - shipped in v3.1.6.]**
- **[P3] Internet card reads "Disconnected" in Access Point mode** (GT-BE19000 tester, 2026-09-13;
  **not model-specific**) — the tester guessed the cause correctly. `www/Main_ReaperDash.asp:837`
  derives `wanUp` from `wan0_state_t==='2'`, which is structurally `0` in AP mode, and then paints
  the state red (`var(--danger)`). The page already resolves the operation mode a few lines later
  (`get_operation_mode()`, line 876) — the WAN card simply does not consult it. Cosmetic, but it
  reads as a fault on a router that is working, which is the worst kind of cosmetic. **Fixed in tree
  for v3.1.6:** both the card and the header pill now name the operation mode in a neutral colour,
  and the live WAN poll — whose "fast while it is down" cadence would otherwise have run a
  four-second request for the life of the page against a state that cannot change — is not started
  at all in those modes. **[CLOSED 2026-09-17 — shipped in v3.1.6.]**
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
- **[P3] `rtrafd` enabled but not running** (GT-BE19000 tester's capture, 2026-09-13) — the diag's own
  check reports `rtraf_enable=1 running=0`, which leaves the Traffic page with no collector behind it.
  **Root-caused 2026-09-13 without the syslog: it is the same AP-mode class as the three above.**
  `start_rtraf()` opens with `if (!is_routing_enabled()) return;`, as do `start_gk()` and
  `start_rchqd()` — and rtrafd accounts off conntrack, which a bridging box never populates. So the
  daemon is *correctly* not running and the finding was the defect. **Fixed in tree for v3.1.6**
  (`reaper_diag` v1.3.17): 12c's `svc()` reports the designed idle state for the operation mode
  instead of warning, the same correction rmcpd's line already carries. Only `sw_mode` 2 and 3 flip
  it, so an unreadable `sw_mode` keeps the louder behaviour rather than silencing a real fault.
  Deliberately **not** changed: rtrafd is left un-started in those modes, because per-device
  accounting off an empty conntrack table would report nothing whatever it did. The Traffic page
  therefore stays empty on a bridging box — worth a note on the page, which is not in this rung.
  **[CLOSED — in the v3.1.6_BETA image; the daemon is correctly idle in a bridging mode and the
  diag's warning was the only defect. The page-note remains unwritten and is the sole remainder.]**
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
- **[P3] Gatekeeper shows a stale band for a multi-link client** (owner, on metal 2026-09-07) —
  **fixed 2026-09-08, shipped in v3.1.1** (`gk_live_conn`): a live band may now override a stale
  one, but only from an entry under the CAP's **own** node key, which is first-hand — a mesh node's
  entry still may not, which is what the v3.0.9 gate was protecting. The confirming capture was
  never taken (the lab MCP was down), so the mechanism is inferred, not proven.
  **[shipped in v3.1.1; capture owed]** ↳ notes: `gk-stale-band-multilink.md`
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
- **[P2] Policy Routing Status column: configuration state, not an effective verdict (review R14).**
  The column reads the target's configuration (client enabled, Killswitch on) and not the rule's own
  On toggle, the master switch, or whether the tunnel is actually up; a switched-off client says
  `Inactive · WAN` although a VPN Director rule below the 9000 band can still capture that flow.
  The reviewer's replacement wording was the prose the Merlin reviewer had just asked to remove, so
  it was not taken. **Owner decision 2026-09-13: keep the column configuration-derived and grey the
  cell while the rule itself, or the master switch, is off** — done in tree the same day (a CSS
  state on the status span, no dictionary change). **[in the v3.1.6_BETA image — same commit
  `7c0fb3bb85` as the Warden instrumentation above; CLOSED 2026-09-17 — shipped in v3.1.6]**
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

---

## UI / UX polish

- **[P2] The Security Posture card was a snapshot and said so to nobody** (owner, 2026-09-15). Every
  row came from `SSI`, a server-rendered snapshot of about 20 nvram keys taken when the page was
  built, so a dashboard opened while the box was still coming up froze at whatever was true then. The
  Rule Status row was worse than frozen: the walker stamps its report with `time(NULL)`, so before the
  clock is set that row read "Checked" against a boot-epoch time. **Shipped in v3.1.7,** triggered on
  NTP sync - the moment the clock becomes true, and on a cold boot after the services the card reports
  have settled. The watcher arms only if the clock is unset at render, is self-terminating, and caps
  at 30 minutes so a box that never syncs cannot leave a poll running for the session. On the
  transition it re-reads the posture keys in one `appGet.cgi` hook and repaints that card alone.
  **Known edge:** it arms at page load only, so an NTP restart later in a session is not followed.
  **[CLOSED 2026-09-17 - shipped in v3.1.7.]**
- **[P3] The BETA tag was on the dashboard header only** (owner, 2026-09-15). `Main_ReaperDash.asp`
  is a top-level page and draws its own header; every other page is framed in `reaper_shell.asp`,
  which draws the shell header — and only the dashboard's copy of the firmware pill carried the
  amber `BETA` tag. So a beta build announced itself on the landing page and nowhere else, which is
  exactly backwards for a tag whose job is to stop someone forgetting what they are running.
  **Fixed 2026-09-15:** the same `p_fwbeta` span, the same `.btag` rule and the same reveal test
  (`/_beta(_|$)/i` against the raw `extendno`) added to the shell header. Same dictionary key
  (`RFWU_56`), so no new strings. The shell had never declared `--amber`, so on _r3 the tag rendered bone instead of amber; the token was added and _r4 carries it. **[built in v3.1.7; _r3 and _r4 both flashed and running 2026-09-15, owner reports normal operation]**

- **[P3] Rule Status table: cramped at 1120px with 400px of empty panel beside it** (owner,
  screenshot on a 1080p monitor, 2026-09-15). Three separate faults, all fixed 2026-09-15:
  (a) the page's shared reading column was **1120px**, set when every Firewall tab was a form — the
  Rule Status table is five columns, two of them monospace netfilter text, and it had nowhere to go.
  Widened **page-wide to 1560px** rather than only under Rule Status, because widening one tab leaves
  the shared tab strip and page head at the old width and reads as a mistake rather than a choice;
  the tab strip now fits on one row instead of two. **Prose was deliberately not widened** — `.lede`
  and `.tabintro p` keep their `ch`-based measures, so explanation stays readable and only data
  stretches. (b) the columns were auto-sized, so a single long deciding rule squeezed FEATURE and
  RESULT into ragged stacks that differed from group to group; now `table-layout:fixed` with stated
  proportions (23/27/10/14/26). (c) **`word-break:break-all` was splitting words that had a perfectly
  good space to wrap at** — that is why the table read "ESTA BLISHED", "ACC EPT" and "u dp". Replaced
  with `overflow-wrap:anywhere`, which wraps at spaces first and only splits a token that genuinely
  cannot fit, which is what a 60-character iptables rule needs. Plus a row hover and a little more
  vertical padding. **[built in v3.1.7; _r3 and _r4 both flashed and running 2026-09-15, owner reports normal operation]**

- **[P3] The Rule Status link read "open Rule Status"** (owner, 2026-09-15) — the leading verb is
  dropped; both link sites (the Rules-tab confirm preview and the Status-tab summary) now use
  `RFW_290`, the tab's own name, which is already translated in all 25 packs. **No dictionary edit
  and no lockstep change.** Note `RFW_318` ("open Rule Status") is now unused in the tree but still
  defined in all 25 packs — harmless, and pruning it is a separate lockstep-touching change.
  **[built in v3.1.7; _r3 and _r4 flashed 2026-09-15]**

- **[P2] A broken firewall promise was invisible unless the Firewall page was open** (owner,
  2026-09-15). The Rule Status tab, the watchdog's syslog line and diag `14g` are all places the user
  has to be looking already. **Shipped in v3.1.7:** a Rule Status row in the dashboard's Security
  posture card (green, red count, or **Partial** when the filter table is the boot skeleton - skeleton
  outranks the red count, since the witnesses are judging a stub); a one-line summary on the Firewall
  page's Status tab, rendered even when the status fetch fails; and a red count badge on the Firewall
  rail item, on every page, blank at zero because an always-present "0" trains people to ignore the
  spot. All read the cached report (`action=witness`, no `run=1`), so none can trigger a walk, and the
  shell outlives page navigation so one 60 s poll covers every framed page while the dashboard adds
  none. Numerals only, so no dictionary key was needed and the 25 packs stay lockstep. The rail is
  duplicated between `Main_ReaperDash.asp` and `reaper_shell.asp`, so the badge and its setter exist
  in both (reaper-ui rule 6), and because the rail builds asynchronously the last reading is cached
  and re-applied whenever it is drawn. **[CLOSED 2026-09-17 - shipped in v3.1.7.]**
  ↳ see the walker entry under *Features to add*; memory `firewall-walker-plan`
- **[P3] A bare `<a>` rendered in browser-default blue, which the theme forbids** (owner,
  2026-09-15, the Firewall Status tab's "open Rule Status" link). Nothing set a link colour, so it
  fell through to the user-agent default `#0000EE`, and visited links to purple, on a matte-black
  panel; blue is explicitly out of the palette. **Shipped in v3.1.7** as `REAPER_LINK_CSS` in
  `httpd/reaper_inject.c`, one rule prepended to every injected page, so stock pages are covered too
  without disturbing a page that styles its own links.
  **[CLOSED 2026-09-17 - shipped in v3.1.7.]**
- **[P3] Nothing stopped the Diagnostics page's version drifting from the script** (owner,
  2026-09-13). `www/Reaper_Diag.asp` carried a hardcoded `REAPER-DIAG v1.0.1` while
  `others/reaper_diag` was at v1.3.16, so the page and the report it generated contradicted each other
  on one screen. v3.1.6 re-pinned the literal, but a second copy of the version that is re-pinned
  rather than derived can desync again, and runtime derivation is not cheap here: the page runs the
  diag only on click and streams the report straight to a download, so there is no report text on
  screen to read a version out of. **Shipped in v3.1.7:** `reaper_verify` check 27 (`diag-version`)
  compares the literal in the staged `www/Reaper_Diag.asp` against `VER` in the staged
  `usr/sbin/reaper_diag` and fails the build on a mismatch, and
  `build-scripts/tests/test_diag_version.py` catches it at commit time - including a page carrying
  more than one version literal, which would defeat the re-pin.
  **[CLOSED 2026-09-17 - shipped in v3.1.7.]**
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
  Firewall/VPNRouting/Failover/About/**Sysinfo**. **[ongoing]**
  **System Information landed 2026-09-15 (v3.1.8, owner ask).** Same data as stock `Tools_Sysinfo.asp`,
  regrouped by the question being asked — what this box is, whether it is struggling, whether it is
  running out, how loaded it is — rather than by where each number comes from. **No new backend:** it
  reads the same `/ajax_sysinfo.asp` and `/ajax_coretmp.asp` the stock page does. Three things got
  better in passing rather than by design: the `rc_support` blob is rendered as scannable chips
  instead of a space-separated wall; RAM carries an explainer for *Available* vs *Free*, which is the
  most misread number on any router page; and the band labels come from `wlX_nband` rather than
  stock's hardcoded `based_modelid` switch, which mislabels the bands of any model not in its list.
  The page also **parses** those endpoints instead of executing them — stock pulls `/ajax_sysinfo.asp`
  with jQuery `dataType:'script'`, and a `!eval(` marker now guards against that coming back.
  Costs: 42 new `RSYS_*` tokens across all 25 packs (reuse took the rest — Model, Firmware, Uptime,
  Total/Used/Free, CPU, RAM, Operation Mode, Connections all already existed). Stock file untouched
  and still byte-pristine, so the rollback is the one SUP line. **[CLOSED 2026-09-17 — shipped in v3.1.8; see CHANGELOG.md, "System Information, native".]**
- **[P3] Staged ("batch") changes — one save, minimal restarts.** **[project]** ↳ notes: `staged-batch-changes.md`
- **[P3] Switch port mirroring to an external IDS** — the software `tc mirred` path is present;
  whether it sees accelerated flows is the decisive unknown. **[project]** ↳ notes: `port-mirroring-ids.md`
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

*Nothing open — the `cut_rung` restatement item closed 2026-09-08 and shipped with the v3.1.1 cut.*


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
- **[P3] `poll_fcache` O(n²) pairing · `poll_classes` 7× `tmctl` popen · `do_reaper_dev_cgi` static
  snapshot arrays** — bounded, measured small, or latent-only. **[shelved]**
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
