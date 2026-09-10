# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.1.2** · 2026-09-10 <!--@stamp-->

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

1. **[P1] Build the five siblings** — the kernel fix is committed on every branch, but only the
   BE96U has been compiled since; the others are source-only. The published CI matrix builds
   them from the series, so this is about a local image to hold, not about the release path.
2. **[P3] Build one `stable` image** — the channel marker has now been through a real beta
   build end to end, but the stable path has never been exercised, and that is the path a
   release goes out on.
3. **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — every cru-driven job dead on that box.
4. **[P2] Warden "crash" on the BE92U addon box** — hypotheses ranked, tester data requested.
5. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — needs a repro.
6. **[P3] CVE check 2026-08-30 residue** — the cheap backports; the known-limitation notes are done.
7. **[P3] Code-review tail, batch B** — two items owner-deferred; `pinTarget()` closed.

***v3.1.2 is the next beta** (cut 2026-09-10; patches 0637–0643). It carries the kernel fix for the
WireGuard Policy Routing panic on all six models, the `_BETA` channel marker in every build's
filename and on the dashboard, the firewall chain-integrity watchdog, the Warden outbound
logging contract and its regression suite, the Firewall › Logging heading and badge fixes, the
Addons rail item that navigates, DoT strict failover order, the dual-stack resolver health
check, the auto-logout idle timer, and the AiMesh backhaul-parking guards. Items closed by it
have been removed from this file and are recorded in [`CHANGELOG.md`](CHANGELOG.md).*

*Earlier, in v3.1.1 (2026-09-09): the Failover tab — the LAN resolver health check and the three
dnsmasq switches — the OpenVPN certificate fixes, the firmware-page Cancel for the upload phase,
the Gatekeeper connection-method, MLO-fold and stale-band fixes, the announced-hostname store,
and the ECS help-text correction. Two of those shipped without hardware validation and stay
listed under Open bugs until a capture exists: the OpenVPN repair path (needs a box with a VPN
server configured) and the Gatekeeper stale-band branch (needs a client moved between radios).*

*Earlier, in v3.1.0 (2026-09-06): OpenSSL 3.5, the first-boot box, the faster factory reset,
backhaul-parking reconcile, the phone-width shell, the update check's beta channel.*

---

## Open bugs / under investigation

- **[P1] OpenVPN server: an empty GUI field deletes the certificate, and the firmware cannot repair
  it** (field report, v3.1.0, 2026-09-08) — `set_ovpn_key()` **unlinks** the stored key on an empty
  value (`libovpn/openvpn_config.c`), and `httpd/web.c:4088` calls it for every cert field on a save
  without checking the return. Recovery is then impossible: `ovpn_write_server_keys()` only
  regenerates when CA **and** key **and** cert are *all* absent, so a partial loss takes the copy
  branch, `ovpn_write_key()` returns -1 for the missing item, and that return is discarded — an
  incomplete runtime config, no log, and no GUI action can re-trigger generation while the CA
  exists. **Ruled out: OpenSSL 3.5** — MD5 signing was tested on the box and succeeds, so the
  easy-rsa `openssl-1.0.0.cnf` is not the blocker. Not TAP/TUN-specific. **Fixed 2026-09-08,
  shipped in v3.1.1:** `set_ovpn_key()` no longer deletes on an empty value (it keeps the stored
  key and logs); deliberate clearing moved to a new `clear_ovpn_key()`, which the one legitimate caller
  (`reset_ovpn_setting`, 16 sites) now uses; `ovpn_write_server_keys()` repairs a partial set by
  regenerating **only the server leaf** from the existing CA — never the CA itself, which would
  invalidate every deployed client — and every `ovpn_write_key()` return is now checked and logged.
  libovpn compiles clean. **Metal validation owed: needs a box with an OpenVPN server configured.**
  **[shipped in v3.1.1; metal owed]** ↳ notes: `ovpn-server-cert-unrecoverable.md`
- **[P2] IPv6 reaches some LAN hosts but not others** (GT-BE98 tester, 2026-09-06) — WAN on DHCP,
  IPv6 native and stateful, working until about v2.7.1; since then the router shows its IPv6, a laptop
  and a NAS get it, but hosts behind a Proxmox server do not — a Windows VM fails testipv6.com even
  with a static address. The tester also sees `nmbd: queue_query_name: interface 0 has NULL IP
  address` in the log. Whether this is the router (RA/DHCPv6 behind an SDN bridge, an ip6tables
  change in that window) or the hypervisor bridge is undecided; more detail promised.
  **[needs data]** ↳ notes: `gt-be98-ipv6-partial-lan.md`
- **[P3] Auto-logout setting has no effect** (GT-BE98 tester, 2026-09-06) — the session drops every
  few minutes, and on returning to the tab, whatever the Administration timeout says; reported as
  present since before Reaper. Which page, which browser, and whether a second login from another
  device or tab is involved, still to be captured. **[needs data]** ↳ notes: `auto-logout-ineffective.md`
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
- **[P3] Gatekeeper shows a stale band for a multi-link client** (owner, on metal 2026-09-07) — with
  the wired/wireless fix in, Nates-PC lists as Wi-Fi **5 GHz** while it is associated on **6 GHz**.
  The live-list correction only fills a band that is missing or replaces a "wired" record, so it can
  fix an absent band but never a stale one; the watcher wrote 5 GHz once, never clears a band, and can
  no longer see that MAC on any radio because the client associates under its link address. The live
  list has the right answer and is not consulted. **Fixed 2026-09-08, shipped in v3.1.1**
  (`gk_live_conn`): a live band may now override a stale one, but only from an entry under the
  CAP's **own** node key, which is first-hand — a mesh node's entry still may not, which is what the v3.0.9 gate was
  protecting. httpd compiles clean. **The confirming capture was never taken** (the lab MCP was
  down), so the mechanism is still inferred, not proven; metal owed.
  **[shipped in v3.1.1; capture + metal owed]** ↳ notes: `gk-stale-band-multilink.md`
- **[P1] Applying a WireGuard Policy Routing rule reboots the router** (owner, logs dated Aug 27;
  re-reported 2026-09-10 as reproducible with the simplest by-device rule) — **ROOT-CAUSED AND FIXED
  2026-09-10.** It was never a reboot at all, which is why no reboot primitive was ever found in the
  path: it is a **kernel panic**. Broadcom's `skip_wg_network_proc_read()` in
  `kernel/bcmkernel/net/core/blog.c` builds its listing with `sprintf()` straight into the
  `char __user *` buffer — a kernel-mode store to a user address. This kernel sets
  `CONFIG_ARM64_PAN=y` and `CONFIG_ARM64_SW_TTBR0_PAN=y`, so that faults at EL1;
  `CONFIG_PANIC_ON_OOPS=y` turns the oops into a panic and `CONFIG_PANIC_TIMEOUT=5` reboots the box
  about five seconds later — "shortly after pressing Apply and Confirm", exactly as reported. The
  loop body is only reached when the table already holds an entry, so an empty table reads back
  harmlessly, and **nothing upstream ever reads these files** (stock code only ever writes them) —
  which is why only Reaper trips it, and only on a WireGuard target: `pbr_skip_add` in
  `rc/reaper_pbr.c` greps the proc file to honour the no-refcount contract, and it is the only
  reader in the system. OVPN, WAN and BLOCK targets never touch it, which is precisely why they
  "work like a charm". Both read handlers now build in kernel memory and use
  `simple_read_from_buffer()`; both write handlers now bound `cnt` against `sizeof(proc_data)` (the
  unbounded `copy_from_user()` beside them was a kernel stack smash) and NUL-terminate. Applied to
  both platform trees in the repo; the same class was found and fixed in the 675x tree's `biqos`
  proc handler, together with a one-byte stack overflow in its write path. Pinned by the new
  `wg-blog-proc` static check, because a kernel file outside `release/src/router` is exactly what a
  sibling port drops and the fix leaves no string a build marker could pin.
  **Cut into v3.1.2 as patch 0641** (2026-09-10). The fix adds no strings, so no build marker can
  see it; presence in an image is established instead from the object and the link — `blog.o`
  recompiled with undefined refs to `simple_read_from_buffer` and `scnprintf` and none to
  `sprintf`, and `vmlinux` relinked before the image is packed. Keep that technique for any
  kernel or library change that leaves no string behind.
  **[fixed + built; metal owed — one WireGuard PBR rule, Apply + Confirm]**
  ↳ notes: `pbr-apply-confirm-reboot.md`
- **[P1] The same kernel panic was live on all five sibling models** (found 2026-09-10 as a
  consequence of the above) — **FIXED 2026-09-10 in every worktree.** `RT-BE86U`, `RT-BE88U`,
  `GT-BE98`, `GT-BE98 Pro` and `RT-BE92U` share the handler, the PAN/`PANIC_ON_OOPS` kernel config
  and the `pbr_skip_add` reader, so a WireGuard Policy Routing rule rebooted those boxes exactly as
  it did the BE96U. All five are worktrees of the one repo, so the same surgical patch was applied
  to each — the four proc handlers and nothing else, so it drags no other canon change into a
  sibling branch. Both platform trees per worktree (`src-rt-5.04behnd.4916` and the 675x tree,
  which also carried the identical bug in its `biqos` proc read plus a one-byte stack overflow in
  its write). `wg-blog-proc` now passes on all six trees. **What is left is a BUILD**: the fix is in
  source on every branch, compiled on none of them but the BE96U.
  Each branch now carries it as its own commit, and the series carries canon's, so the CI
  clean room builds every sibling with the fix in place.
  **[fixed in source on all six and in the series; five local builds owed]**
  ↳ notes: `pbr-apply-confirm-reboot.md`
- **[P2] Warden outbound blocks appear to have stopped** (owner, 2026-09-10: none seen in syslog for
  several releases) — **no defect found in the emitter.** `RW_ODROP` is built whenever direction is
  out/both, carries its own `REAPER-WARDEN-OUT ` LOG rule under the same `rwarden_log` gate as
  inbound, and its counters are banked. Silence has four different causes that looked identical from
  outside: outbound filtering off, the chain absent, logging off, or armed with nothing matched —
  the last being the normal case, since an outbound hit needs a LAN device to reach *for* a flagged
  address, where inbound gets a free stream of them from the internet. The box now says which:
  rwatch section 3e logs the state once per change, and the Firewall → Logging viewer no longer
  collapses `REAPER-WARDEN-OUT` and `-SELF` into one `WARDEN` badge (which had quietly undone the
  point of giving them separate prefixes in v2.4.4). Both halves are in v3.1.2, patches 0642–0643.
  **[instrumented; needs one `rwatch: Warden outbound: …` line from the box to close]**
  ↳ notes: `warden-outbound-quiet.md`
- **[P2] The rest of v3.1.2 wants a session on the box** (2026-09-10) — five changes beyond the
  kernel fix, each of which needs to be looked at once: the rwatch chain-integrity watchdog
  (should stay silent on a healthy box), the rwatch Warden-outbound state line, the Firewall →
  Logging heading correction and the split `WARDEN-OUT` / `WARDEN-SELF` badges, and the Addons menu
  opening its first page instead of unfolding a list. Grouped rather than split into five entries
  because one session on the box settles all of them. **[metal owed]**
  ↳ notes: `v312-r2-validation.md`
- **[P3] Policy Routing page: the first-open symptom was never identified** — the screenshot did not
  reach the record; the strongest candidate shipped fixed in v3.0.5. **[needs the screenshot]**
  ↳ notes: `pbr-first-open-symptom.md`
- **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — rwatch, Warden refresh and the PBR
  deadline watcher all dead on that box. **[needs the GT-BE98 syslog]** ↳ notes: `gt-be98-empty-crontab.md`
- **[P3] CVE / component check 2026-08-30 residue** — no reachable HIGH, nothing MED at defaults.
  **Documentation half done 2026-09-08:** the five off-by-default inherited components (netatalk,
  wpa_supplicant, lighttpd, net-snmp, Quagga) and the accepted update-manifest-signature trade are
  now stated in [`../SECURITY.md`](../SECURITY.md) under *Known limitations*, following the Samba
  precedent. **Remaining:** the cheap backports (strongSwan, avahi CNAME trio, the kernel one-hunk
  set) — each needs a build, so they want their own rung. ↳ notes: `cve-check-2026-08-30.md`
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
  (found by the 2026-09-09 decompose) — `amaspark`'s park decision requires the paired-node
  registry to be non-empty, and both `cfg_obstatus` and `cfg_relist` are written only by
  `cfg_server`, which is a blob: if the registry lags the window closing, the daemon parks the
  2.4/5 GHz carriers within one 5 s tick of a node completing its join. Whether that lag exists
  is **not provable from source**, so this is a latent risk rather than a proven defect — but it
  is closable without knowing. **Fixed in tree 2026-09-09:** a carrier with a station associated
  to it is never parked (`wl assoclist`) whatever the registry says, and parking is held off for
  120 s after a search/onboarding window closes; both log on transition only. Also logged the
  previously silent case where a radio switched off under a parked carrier. Type-checked on the
  host with `-Wall -Wextra`, 0 warnings. Parking is opt-in and off by default, so this cannot
  explain any report from a tester who never enabled it. **Built into the v3.1.2 RT-BE96U MCP test
  image** (2026-09-09, sha `ee9e0726e00f79f7…`, reaper_verify 25/25); all four new log strings
  confirmed present in the packaged `/sbin/rc`. **[built; metal owed — needs a node to pair]**
  ↳ notes: `aimesh-decompose-2026-09-09.md`, `aimesh-park-idle-backhaul.md`
- **[P2] MLO ON kills the AiMesh backhaul; MLO OFF restores it** (tester, GT-BE98 CAP + RT-AX92U
  nodes) — rule out the nodes' MLO capability, the cold-cycle rule and dirty-install residue before
  calling it Reaper's; a missing guardrail would be ours. **[owed: needs a mesh]** ↳ notes: `mlo-kills-aimesh-backhaul.md`
- **[P2] Hardware QoS on the RT-BE92U: PI2 AQM is not supported by the Archer traffic manager**
  (BCM6765; drop algorithms stop at WRED), so both hardware engines most likely fail at the first
  `setqdropalg` call and the QoS Diagnostics tab has no data source on that chip. Runtime PI2→RED
  fallback designed; a 30-second tmctl probe from a forum tester decides whether to build it.
  **[needs data: no BE92U in the lab]** ↳ notes: `hwqos-be92u-archer-fallback.md`
- **[P2] Firewall hosts rule: pasting an IP list blanks the GUI until httpd restarts** (BE88U,
  v2.7.1) — no blocking operation visible in the save/apply path. **[owed: repro]**
  ↳ notes: `firewall-hosts-paste-blanks-gui.md`
- **[P2] Heavy ping loss after a router reboot, cured only by rebooting the ONT** (GT-BE98, PPPoE
  over VLAN 835) — best fit a stale PPPoE session at the OLT; v2.5.5 ships a one-shot re-dial.
  **[owed: a capture during the fault]** ↳ notes: `ping-loss-after-reboot-ont.md`

---

## UI / UX polish

- **[P3] Firmware page: the download phase still has no true cancel** — the upload half shipped in
  v3.1.1 (the hatch reads **Cancel** and aborts the in-flight POST). During a download from the
  update server the button still says **Close** and only leaves the overlay, honestly labelled:
  the generic `webs_*` rc dispatch handles START only (`services.c` ~20175), so `stop_webs_upgrade`
  is a no-op, and `reaper_webs_upgrade.sh` runs download → verify → flash in one shot on the router.
  A real cancel there means a kill on a flash-adjacent path, which is a service change and not a UI
  one. **[deferred — needs an rc stop service]** ↳ notes: `firmware-veil-cancel.md`
- **[P3] Chain-integrity watchdog covers the Warden drop chains only** (scope note, 2026-09-10) —
  rwatch 3d asserts "ends in DROP, nothing ahead of it that ACCEPTs or RETURNs" for `RW_DROP`,
  `RW_ODROP` and `RW_SDROP`, and asserts hook position for the three front chains. The Gatekeeper
  and rules-engine chains have **no equivalent invariant checked**, deliberately: they interleave
  DROP and RETURN by design, so "ends in DROP" is not a property they have and asserting it would
  produce noise, not safety. If those need guarding, the invariant has to be defined first —
  probably "the chain still contains the rules the generator emitted", which is a different and
  more expensive check. Note also that only chains are checked, not ipset **contents**; the Warden
  poison canary (rwatch 3) is the only set-level guard. **[owed — needs the invariant defined]**
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
- **[P2] Firmware-update manifest signing** — implemented for v2.7.3, shelved inert by owner
  decision; re-enable = flip two switches + rebuild. **[shelved — inert]** ↳ notes: `manifest-signing-shelved.md`
- **[P3] North star — progressively replace stock GUI pages with Reaper-native ones.** Done for
  Dashboard/QoS/Traffic/Wireless/GK/Warden/Devices/Advisor/Conn/QoSDiag/Analytics/Storage/Firmware/
  Firewall/VPNRouting/About. **[ongoing]**
- **[P3] Staged ("batch") changes — one save, minimal restarts.** **[project]** ↳ notes: `staged-batch-changes.md`
- **[P3] Switch port mirroring to an external IDS** — the software `tc mirred` path is present;
  whether it sees accelerated flows is the decisive unknown. **[project]** ↳ notes: `port-mirroring-ids.md`

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
- **[P3] `reaper_hiddencheck.py` aborted on an unreadable path** (found 2026-09-10) — **FIXED
  2026-09-10.** An unhandled `OSError` in `scan_file()` killed the whole run on the first dangling
  symlink, so any scope containing one produced no result at all rather than a result with a gap.
  Unreadable paths are now collected and reported as a `[NOTE]` line, and the scan continues.
  Verified both ways: a scoped run over a directory holding a deliberately broken symlink now
  reports it and passes, and the full `release/src/router` scan completes (152,478 files, 57.8 M
  lines) where it used to die.
  **Correction to how this was first written up:** the entry claimed the gate "can only ever be run
  on subsets". Running it tree-wide is not actually the goal and never was — the vendor tree
  contributes ~132 k hits of its own (glib, tor, ethtool long lines; stock `eval(` sites), so a
  whole-tree run is noise by construction. The gate's scopes are our patches and overlays, per
  `cut_rung` step 3b. The abort was still worth fixing, because it applied to those scopes too.
  The symlink itself is expected debris: `sysdep/www/…` points at `../../RT-AC66U/www/…`, a model
  directory removed by the sibling strip. **[fixed]**
- **[P3] The channel marker: BETA exercised, STABLE not yet** (2026-09-10) — the first real beta
  build (`v3.1.2_BETA`, 11:07) went end to end and **found one integration defect the desk checks had
  missed**: `gen_provenance.sh` extracted the version with a `Reaper_vX.Y.Z` pattern that stopped at
  the number, so the About page said `v3.1.2` while the filename and every other surface said
  `_BETA` — and `reaper_verify`'s `provenance-stamp` compared the two and failed the build, exactly
  as a fail-closed gate should. Fixed to take the whole `EXTENDNO` minus the `_noMCP` variant tag
  (which is reported separately and would break the comparison the other way), with a fallback to
  the old extraction; verified against all six `EXTENDNO` shapes. The rebuilt image is 25/25 and the
  marker is confirmed present in the filename, the staged provenance (`version: "v3.1.2_BETA"`) and
  the dashboard chip. **What is still unexercised is the STABLE path** — no image has been built
  with `stable` since the change, and that is the path a release goes out on.
  **[owed — build one `stable` image before the next release cut]** ↳ notes: `channel-marker.md`
- **[P2] Nothing checked the channel at publish time** (added 2026-09-10) — **DONE 2026-09-10 in
  `stage_release.ps1`**, which is the step that decides what lands in `releases/` and therefore what
  users can download. It gained `-Channel Beta|Stable`, defaulting to **Beta** for the same reason
  the build does; the channel now selects which FILES are staged, so asking for the wrong one is
  reported as a missing image instead of quietly staging the other channel. It also refuses to stage
  into a version folder that already holds an image of the *other* channel — one release folder
  holding both a marked and an unmarked image of the same version is precisely the confusion the
  marker exists to prevent, and it would reach the people least able to spot it. This was also a
  hard requirement, not just a nicety: the script's `-Version` pattern rejects uppercase, so before
  this change a `_BETA` image could not be staged at all.
  **Not done, on purpose:** no equivalent assertion in `release.yml`. Staging is the gate that
  decides the contents, so the hole is closed; a CI-side cross-check of the assets against the
  `prerelease` flag would be belt-and-braces on a path that cannot be exercised from here.
  **[done at staging; the CI-side echo of it remains optional]** ↳ notes: `channel-publish-guard.md`
- **[P3] v3.1.2 `_r2` and `_BETA` were built from a dirty tree** (2026-09-10) — **CLOSED at the
  v3.1.2 cut.** Both images' shas mapped to no commit. The tree is now committed as patches
  0637–0643 and the shipped image is taken from the commit, so the provenance gap is closed and
  the About page's build commit is real. **[closed]**
- **[P2] A commit made from a warm build tree can sweep in thousands of generated files**
  (found at the v3.1.2 cut, 2026-09-10) — `95a1ee8ac3` was meant to be a thirty-file DNS change
  and added **10,110** build-output files across some fifty vendored packages: objects, `.deps`
  and `.libs`, dependency stubs, autom4te caches, and the configured `Makefile`, `libtool` and
  `config.h`. Consequences, all real: `overlays/openssl-3.5-source.tar.gz` went from 50 MB to
  **108 MB**, past GitHub's 100 MB hard limit; the exported patch would have been **217 MB**; and
  the hidden-character gate refused the cut over the control bytes autotools embeds by
  construction. Shipping it would have been worse than noise — a configured `Makefile` and
  `libtool` carry the build host's absolute paths, and dropping those into the CI clean room is
  the stale-configure trap that has cost this project a fleet before. Corrected at source before
  the export. **The guards worked; nothing guards the commit itself.** A pattern-based
  `.gitignore` is not available for the vendor tree at large — it legitimately tracks 1,452 `.o`,
  609 `Makefile` and 284 `.so` files from the pinned upstream base, so every candidate pattern
  would shadow real content. `openssl-3.5` is the one directory where the classes provably
  cannot occur in source, and it now has a scoped guard. What is still wanted is a pre-commit
  or cut-time check on the *shape* of a rung commit — a file count far outside the one-to-four
  every other commit in this rung had, or added paths absent from the pinned base.
  **[owed — the openssl half is done; the general check is not]**
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
- **[P2] Mobile device metrics reported incorrect** (owner report, 2026-09-05) — the per-device figures
  shown for phones and tablets do not match what the devices see; which page, which metric, and against
  what reference still to be captured. **[working as designed]** — a page-rendering report,
  not a data one. ↳ notes: `mobile-device-metrics.md`
- **[P2] AiMesh nodes refuse the firmware** (owner report, 2026-09-05) — nodes decline the image the
  router offers them; which models, which message, and whether the refusal is the node's version check,
  the signature check, or the transfer are all unknown. User reset the device and it worked fine. 
  **[watch]** ↳ notes: `aimesh-node-firmware-refused.md`
- **[P2] Service Intercept in redirect-to-router mode with nothing listening** (owner, 2026-09-06) —
  an NTP intercept set to redirect to the router silently sent every client's time request to a closed
  port because "Enable local NTP server" was off; clients then polled every public server they knew.
  The page should refuse or warn when the redirect target port has no listener, or offer to switch the
  local server on. **[enabled router NTPS]** ↳ notes: `intercept-redirect-no-listener.md`
- **[P2] Warden "crash" on the BE92U addon box** after an amtm + Diversion update — one code-plausible
  path (addon nvram storm → wlcsm wedge → Warden chain missing). The defensive half is built: rwatch
  re-applies a missing chain. The root cause still wants the tester's syslog.
  **[owed: shelved support]** ↳ notes: `warden-crash-be92u-addons.md`
  
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
  BE96U. **[blocked — development]** ↳ notes: `speedtest-10g-links.md`
