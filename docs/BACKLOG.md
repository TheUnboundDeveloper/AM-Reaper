# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.1.6** · 2026-09-13 <!--@stamp-->

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
   the box is running the boot skeleton. The refused line itself is still wanted from the reporter's
   router (one command) — see the entry under Open bugs.
2. **[P1] v3.1.5 — the beta is out; what only hardware can settle.** The v3.1.5 beta was built by
   the public clean-room pipeline and published as a prerelease for all six models, both variants,
   on 2026-09-13. Every fix from the 2026-09-12 security review, the two OpenVPN certificate causes,
   the DDNS fix and the WireGuard kernel fix are in those images. The metal-owed list is one entry
   under Open bugs. v3.1.5 becomes the stable release when Dev is merged to main after the beta has
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
   confirming capture from the same box on a v3.1.6 image. The model stays a prerelease until the
   glitch list is closed.
   ↳ memory: `gt-be19000-port.md`
3b. **[P2] Code signing, fully automated — scheduled for a release later this week** (owner,
   2026-09-13), after v3.1.6 is stable and the GT-BE19000 glitch list is triaged: images signed in
   CI with an Ed25519 trailer, the manifest signing re-enabled and automated, router-side verify on
   both install paths, and the Firmware page's pre-upload signed / NOT-signed verdict. The gate test
   (a trailered image flashing on the BE96U) runs first and alone. Details under Features.
4. **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — every cru-driven job dead on that box.
5. **[P2] Warden chain missing after an add-on update** (amtm + Diversion) — the defensive half is
   built; the root cause still wants a syslog. The suspected fault is in shared Warden code, so it
   would affect every model.
6. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — needs a repro.
7. **[P3] Build one `stable` image** — the channel marker has been through real beta builds end to
   end, but the stable path has never been exercised, and that is the path a release goes out on.
8. **[P3] Local sibling images** — the RT-BE96U and the GT-BE19000 have local images from the
   current tree; the RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro are source-only locally. The CI
   matrix builds all six from the series, so this is about a local image to hold, not the release path.
9. **[P3] CVE check 2026-08-30 residue** — the kernel one-hunk set; everything else landed in v3.1.5.
10. **[P3] Code-review tail, batch B** — two items owner-deferred; `pinTarget()` closed.

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

- **[P1] Port forwards dead on an RT-BE88U since v3.1.0 — the FULL FILTER TABLE never loads on the
  reporter's box** (review R15; reopened 2026-09-13). The first verdict — the nat emitter is fine —
  still stands, and it was never the bug. The reporter's second trace (v3.1.4 noMCP, PPPoE, Tailscale
  via `firewall-start`) shows VSERVER's DNAT counters climbing and a FORWARD chain of exactly six
  rules ending in policy DROP: rule for rule, the boot-time skeleton `start_default_filter()` lays
  down before every `start_firewall()`. The real table's `ctstate DNAT` accept, TCPMSS, the INVALID
  drop, SECURITY and every VPN server chain are absent. `iptables-restore` is atomic, so one rejected
  line in `/tmp/filter_rules` leaves the skeleton in place — the router logs `firewall: apply rules
  error(6363)` and copies the file to `/tmp/err_rules/`. The nat table lands, hence "translated, then
  dropped". Which line is rejected cannot be determined from here: the v3.0.0 → v3.1.0 delta touches
  nothing that writes the filter file, and the owner's RT-BE96U on the v3.1.5 beta loads its filter
  file cleanly with the DNAT accept in place and nothing under `/tmp/err_rules`. The TCPMSS theory is
  dead (the lab emits it on DHCP too). **v3.1.5 diagnoses this and changes nothing in the path**:
  `reaper_diag` 14f prints the "DNAT live but no ctstate-DNAT accept" finding and lists
  `/tmp/err_rules`. Stopgap for the reporter until the hotfix: `iptables -I FORWARD -m conntrack
  --ctstate DNAT -j ACCEPT` in `firewall-start`, with the warning that the rest of their firewall is
  equally absent while the skeleton runs. **Next:** the reporter runs `iptables-restore --test` on the
  `err_rules` copy (exit 2 names the line on this firmware); then a hotfix; then decide whether an
  rwatch or `reaper_diag` check for "the filter table is the boot skeleton" is worth adding. The
  reporter also says the v3.0.0-beta / v3.0.7-beta RT-BE88U assets are gone from GitHub — check
  whether that predates the retention rule.
  **Second field round, 2026-09-13 evening.** The reporter's two saved copies under `/tmp/err_rules`
  (written 95 s into the current boot, before syslogd was up — which is why this boot's log carries no
  `apply rules error` line) both pass `iptables-restore --test` with exit 0, and every
  `service restart_firewall` hours later still leaves the boot skeleton: a deterministic, kernel-side
  refusal of one line — not a parse error, not a boot race. The stopgap works. Ruled out on the owner's
  RT-BE96U before anything was written: this kernel commits a `policy --dir out` match in an
  INPUT-reachable chain and even a chain-jump loop (both exit 0), so the refused line is of neither
  class; the IPsec `-m policy` emitters — the one thing the reporter enables and the lab does not —
  sit only in INPUT-reachable chains; the `upnp` ipset rule is not compiled for any model; the TCPMSS
  clamp in `PControls` is never jumped to; every match the file can use is built in or autoloads.
  And `_eval()` sends the restore's own `line N failed` to `/dev/null`, so the router never could say.
  The reporter's two side observations: the Reaper hook chains are installed by the layers that use
  them (Gatekeeper, Warden, the rules engine), all off on that box, so absent is expected; and
  `service restart_firewall` returns before the firewall is rebuilt, so an `iptables -S` taken straight
  after it sees the skeleton before `firewall-start` has run (their script sleeps 8 s inside).
  **BUILT 2026-09-13 in the canon tree (mk-rc clean; host test 17/17):** `reaper_restore_rules()` wraps
  the four filter restores — the restore's own words are kept under `/tmp/err_rules/<file>.err`, the
  refused line is named verbatim in syslog, and the table is applied WITHOUT it (up to eight lines): a
  firewall missing one rule the kernel would never have enforced beats a skeleton that enforces none.
  Declaration, table and COMMIT lines are never stripped; a refusal that names no line is logged and
  left alone. rwatch 3f reports `filter-skeleton` (INPUT_ICMP and SECURITY absent in router mode after
  boot grace) and requests one `restart_firewall` per boot; `reaper_diag` 1.3.16 §14f prints the table's
  state, the `err_rules` listing and each `.err` file's first line, with a FINDING.
  `build-scripts/tests/test_firewall_restore_skip.py` compiles the wrapper on the host and drives it
  with a fake restore. **Still wanted: the line.** `/usr/sbin/iptables-restore -v` on the saved copy
  gives it now (a failure names the line and changes nothing; a success installs the intended firewall);
  otherwise the next beta's syslog carries it. Then a targeted fix. The "v3.0.0-beta / v3.0.7-beta
  RT-BE88U assets are gone" question is answered: the retention prune ran (166 releases → 30) and
  retired every beta below v3.1.3 by rule; the RT-BE88U keeps v2.8.8 and v3.1.0 stable and the
  v3.1.3–v3.1.5 betas. Nothing to fix; tell the reporter v3.1.0 is the last stable.
  **[fixed in tree — general fix built, image owed; the refused line still wanted]**
  ↳ notes: `r15-port-forwards-rt-be88u.md`; `R15-NOTES.md` (v3.1.5 review, R15 — "Field update 2026-09-13, evening")
- **[P1] v3.1.5 — metal owed for every fix that landed, on the published beta images.** Sixteen
  items (R01–R16) from an independent adversarial review, re-verified and remediated in the v3.1.5
  tree; the decisions are in `REAPER-FIXES.md` ("Security review 2026-09-12"). What only hardware can
  prove: Time Machine discovery + first and incremental backup + an interrupted transfer (netatalk
  R01, the DSI struct grew — every module rebuilt cold); an IKEv2 EAP-MSCHAPv2 connect + reconnect
  (strongSwan R02); Tor transparent proxying v4 + DNS after the 0.4.9.12 bump (R03); toggling a
  client's Killswitch and its enable INSIDE the Policy Routing confirm window, then Keep and separately
  Revert — the live 91xx prohibit must follow the switch both ways (R04); a full WireGuard bypass table
  producing E_PARTIAL on the page with the syslog line naming it (R05); a saved rule on a geo object
  dropped with its reason, a group expanding into its members (R06); `ip rule add` failure surfacing
  as E_PARTIAL and rwatch healing an IPv6 shortfall (R07); a slow TLS handshake against an armed
  Advisor dropped at 20 s (R10); an SNMP SET with a NULL varbind answered wrongType (R13); an OpenVPN
  server certificate repaired AND a new server created on an OpenSSL 3.5 image (R16 — the RANDFILE
  cause on top of the AKID one, both fixed, the first proven on the box against a throwaway CA before
  it was built). From the rungs before it, on the same images: one WireGuard Policy Routing rule,
  Apply + Confirm, on any model (the v3.1.2 kernel fix); DDNS on a dual-WAN box whose IPv6 lives on
  the other WAN staying quiet (v3.1.4, the reporter's confirmation); the Gatekeeper stale-band branch
  (v3.1.1, needs a client moved between radios). **[metal owed]**
- **[P2] The Policy Routing page wants a browser** (v3.1.5) — the behaviour half is confirmed on
  metal: the Killswitch A/B passed both ways from the nvram toggle plus a vpnrouting restart alone,
  and the front-chain classifier was proven on the same box and the same rule that raised a FAILURE
  on v3.1.2. What a lab session cannot see is the page as v3.1.5 left it: the Target column reading
  the interface and nothing else (`WAN` on the WAN row, the explanation as a hint in the add-rule
  list), the new **Status** column (`Active`, `Active · Killswitch`, `Inactive · WAN`), the single
  note under the table, the Apply overlay persisting until the Keep / Revert bar, and the
  Administration tab reading *DNS Failover*. **[metal owed — needs a browser, not the lab]**
- **[P2] The rest of v3.1.2 and v3.1.3 wants a session on the box** — each of these needs to be
  looked at once: the rwatch chain-integrity watchdog (should stay silent on a healthy box, and
  tolerate a narrowed rule ahead of it), the rwatch Warden-outbound state line, the Firewall →
  Logging heading correction and the split `WARDEN-OUT` / `WARDEN-SELF` badges, the Addons menu
  opening its first page, the first-boot Wi-Fi page header on a sibling. Grouped because one session
  on the box settles all of them. **[metal owed]** ↳ notes: `v312-r2-validation.md`
- **[P2] Warden outbound blocks appear to have stopped** (owner, 2026-09-10) — **no defect found in
  the emitter**; the outbound state line and the split badges shipped in v3.1.2. The line's first
  real capture (2026-09-11) found two defects in the instrumentation itself, so this stays open.
  **(a) `blocked so far` is a 15-minute window presented as a total** — it reads the live `RW_ODROP`
  counter, which `fold.sh` banks and zeroes on its own `*/15` cron, so on a healthy box the figure
  reads `0` most of the time; it should quote the durable total. **(b) 3e cannot tell "logging is
  off" from "I could not read the flag"** — an `nvram get` killed at `_nv`'s 5 s ceiling returns
  empty and takes the same branch as `0`, telling the operator to switch on something already on.
  (b) was ruled out at the captured timestamps (no hung-read lines near them), which leaves
  `rwarden_log` genuinely reading 0, 1, 0 inside 25 minutes; its only writer is the Warden page's own
  form post, and that hidden field is filled at submit time from the toggle's CSS class, so a submit
  that beats the toggle being painted posts `0`. **Both instrumentation defects fixed in tree
  2026-09-13:** fold.sh banks the outbound drops under their own durable `OUT` key (reset with the
  window), the rwatch 3e line and the stats `out_n` figure quote banked + live, and an nvram read
  that does not answer is its own state ("could not be read this tick") instead of the "turn on
  logging" advice. **Next: confirm with the owner whether the Warden page was applied around 23:05
  and again around 23:20 on 2026-09-11.**
  **[instrumentation fixed in tree, image owed; the 0/1/0 flag question still open]** ↳ notes: `warden-outbound-quiet.md`
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
  **[fixed in tree, metal owed — no lab box runs in AP mode]**
- **[P2] Dashboard reports zero clients while the Devices page lists them all** (GT-BE19000 tester,
  2026-09-13; **not model-specific**). Two different presence sources: the dashboard polls stock
  `get_clientlist()` and skips every row failing `String(c.isOnline)!=='1'`
  (`www/Main_ReaperDash.asp:1309`), while the Devices page reads Reaper's own
  `reaper_dev.cgi?action=status` (`www/Reaper_Devices.asp:348`) and never consults `isOnline`. In AP
  mode networkmap has nothing to derive presence from — the same capture shows **0 DHCP leases and 0
  conntrack entries** — so the dashboard counts nothing while 16 stations are associated on the VIFs.
  The AiMesh card is reported the same way and probably shares the cause, but that was not proved.
  **Fixed in tree for v3.1.6.** The band coding was the open question and the store does carry it:
  `rdev` holds `band` ("2.4"/"5"/"6"/"" for wired) filled from the `wl` assoclists and corrected by
  the bridge FDB, and `online` comes from the assoclists, the FDB and `/proc/net/arp` — none of
  which needs a lease or a conntrack entry. In a non-routing mode the tiles now read
  `reaper_dev.cgi`, folding MLO links and AiMesh nodes the way the Devices page does, and poll at
  30 s rather than 10 because `action=status` `popen()`s `wl` per radio, VIF and station on a
  single-flight httpd — which is why the Devices page reads it on demand and never on a timer.
  Routing mode keeps `get_clientlist()` untouched. Settled by the same box on a v3.1.6 image
  counting its sixteen stations. The AiMesh card was left alone: same symptom, but the shared cause
  is still unproved. **[fixed in tree, metal owed]**
- **[P3] Internet card reads "Disconnected" in Access Point mode** (GT-BE19000 tester, 2026-09-13;
  **not model-specific**) — the tester guessed the cause correctly. `www/Main_ReaperDash.asp:837`
  derives `wanUp` from `wan0_state_t==='2'`, which is structurally `0` in AP mode, and then paints
  the state red (`var(--danger)`). The page already resolves the operation mode a few lines later
  (`get_operation_mode()`, line 876) — the WAN card simply does not consult it. Cosmetic, but it
  reads as a fault on a router that is working, which is the worst kind of cosmetic. **Fixed in tree
  for v3.1.6:** both the card and the header pill now name the operation mode in a neutral colour,
  and the live WAN poll — whose "fast while it is down" cadence would otherwise have run a
  four-second request for the life of the page against a state that cannot change — is not started
  at all in those modes. **[fixed in tree, metal owed]**
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
  **[fixed in tree, metal owed]**
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
  state on the status span, no dictionary change). **[done in tree, image owed]**
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
  **[shipped; metal owed — needs a node to pair]**
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

- **[P3] Nothing stops the Diagnostics page's version drifting from the script again** (owner,
  2026-09-13). The symptom is fixed — `www/Reaper_Diag.asp` had a hardcoded `REAPER-DIAG v1.0.1`
  while `others/reaper_diag` was at v1.3.16, so the page and the report it generated contradicted
  each other on the same screen; the literal now matches. But it is still a **second copy of the
  version**, re-pinned rather than derived, and the next `VER` bump can silently desync it exactly
  as before. Runtime derivation is not cheap here: the page runs the diag only on click and streams
  the report straight to a download, so there is no report text on screen at load to read the
  version out of — it would need a light `reaper_diag.cgi` action that returns `VER` alone (a web.c
  change). The cheaper durable answer is a gate, not a derivation: a `reaper_verify` check that
  compares the literal in the staged `www/Reaper_Diag.asp` against `VER` in the staged
  `usr/sbin/reaper_diag` and fails the build when they disagree. That has to live in the engine
  (`reaper_verify.sh` + both copies, lean first then `sync_local_engine.sh`), because the lean repo
  carries no source files for a `build-scripts/tests/` host test to read. A `verify_markers.txt`
  rule cannot do it — markers assert one literal on one page and would pass while the script moved
  underneath. **[owed — the gate, not the number]**
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
  Firewall/VPNRouting/Failover/About. **[ongoing]**
- **[P3] Staged ("batch") changes — one save, minimal restarts.** **[project]** ↳ notes: `staged-batch-changes.md`
- **[P3] Switch port mirroring to an external IDS** — the software `tc mirred` path is present;
  whether it sees accelerated flows is the decisive unknown. **[project]** ↳ notes: `port-mirroring-ids.md`
- **[P2] Firewall table walker + Firewall Rule Status page** (owner, 2026-09-13; scheduled AFTER
  v3.1.6 and the R15 line) — the firewall says what it is actually doing, per feature, after every
  change. Not by reasoning about rule combinations: each feature owns a handful of **witness packets**
  (ingress interface, addresses, protocol/port, conntrack state) and the verdict it promises; a small
  walker pushes each one through the LIVE tables in kernel order (raw → mangle → nat PREROUTING →
  filter) modelling only the matches our rules use, and returns the verdict with the rule that produced
  it — so "port forward 443 is blocked by FORWARD rule 3 (Skynet)" or "every feature red: FORWARD
  policy DROP, the boot skeleton" comes for free. Runs at the end of every firewall apply and on
  demand; one JSON file; the page polls it; the rules engine's confirm window shows it before Keep.
  What it retires: the position-based watchdog fights (rwatch 3d's re-pin vs the Gatekeeper DNS
  carve-out becomes two witnesses — restricted device resolves, restricted device cannot reach the
  WAN — and repair fires only when one is red), the exemption file, and most of 3c/3f as heuristics.
  What it does not do: fix ordering by itself (that is the layers declaring their own placement),
  reverse-path or accelerated-flow behaviour, or the blob's drops — "depends" is a result. Cost:
  walker ~500–800 lines of C as a helper binary, the catalog as a table, a page the size of Firewall
  Status, plus a host-side release check over saved `iptables-save` fixtures and a lab-only TRACE
  validation of the walker's path. **Done now, at no cost:** the witness catalog (58 rows across
  core reachability, port forwards, VPN, Gatekeeper, Warden, rules engine/intercept, SDN/VLAN/AiMesh,
  the rest) and the first fixture (the owner's BE96U, v3.1.5 beta, WAN masked, private); the
  reporter's RT-BE88U dump is requested and a GT-BE98 with VLANs is wanted. Order: walker as a CLI +
  reaper_diag 14g + the release check; then the page; then the confirm-window preview.
  **[project — start after v3.1.6 stable; the R15 line is the first fixture]**
  ↳ notes: `firewall-witness-catalog.md`; fixtures in `ASUS/audits/firewall-fixtures/`

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
