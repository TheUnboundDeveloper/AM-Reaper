# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.1.1** · 2026-09-07 <!--@stamp-->

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

1. **[P2] Devices/Gatekeeper: wrong connection method, MLO combining broken** — root-caused and
   fixed in tree 2026-09-07 (a multi-link client is listed under its link MAC); **metal check owed**.
2. **[P2] Apply and Confirm on Policy Routing rebooted the router** — no reboot primitive in the
   path; needs the three captures on the next occurrence.
3. **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — every cru-driven job dead on that box.
4. **[P2] Warden "crash" on the BE92U addon box** — hypotheses ranked, tester data requested.
5. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — needs a repro.
6. **[P3] CVE check 2026-08-30 residue** — cheap backports and known-limitation notes.
7. **[P3] Code-review tail, batch B** — two items owner-deferred; `pinTarget()` closed.

*In beta (v3.1.0 on Dev, 2026-09-06): OpenSSL 3.5, the first-boot box, the faster factory reset,
backhaul-parking reconcile, the phone-width shell, the update check's beta channel. Building toward
v3.1.1: the LAN resolver health check and the three dnsmasq switches. Neither is listed here.*

---

## Open bugs / under investigation

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
- **[P2] Devices/Gatekeeper: wrong connection method, and MLO combining no longer works**
  (owner, 2026-09-05; narrowed 2026-09-07 to "mostly Gatekeeper", "Nates-PC is on 6Ghz but Gatekeeper
  shows wired") — **root-caused and fixed in tree, metal owed.** The live client list keys a
  multi-link client under its per-link MAC and names the device's MLD MAC in a field every reader
  ignored, while the lease, the ARP entry and every Reaper row are keyed by that MLD MAC. So the
  device was never found in the list: Gatekeeper kept the cached "wired" (it has no bridge-FDB pass
  to correct it, which is why the Devices page was mostly right), and the MLO fold, which asked the
  driver for a line this client no longer prints, left two rows. None of the three bisect candidates
  was the cause. **[fixed in tree `e8c0995520`, metal owed]**
  ↳ notes: `devices-conn-method-mlo-regression.md`
- **[P2] Apply and Confirm on Policy Routing rebooted the router** (owner, logs dated Aug 27) — the
  flicker half shipped fixed in v3.0.5; the reboot half is unexplained, no reboot primitive exists in
  the path, not reproduced on v3.0.5. **[needs data]** ↳ notes: `pbr-apply-confirm-reboot.md`
- **[P3] Policy Routing page: the first-open symptom was never identified** — the screenshot did not
  reach the record; the strongest candidate shipped fixed in v3.0.5. **[needs the screenshot]**
  ↳ notes: `pbr-first-open-symptom.md`
- **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — rwatch, Warden refresh and the PBR
  deadline watcher all dead on that box. **[needs the GT-BE98 syslog]** ↳ notes: `gt-be98-empty-crontab.md`
- **[P3] CVE / component check 2026-08-30 residue** — no reachable HIGH, nothing MED at defaults;
  what it queues: cheap backports, known-limitation notes, the inert manifest signature, hygiene.
  ↳ notes: `cve-check-2026-08-30.md`
- **[P2] MLO ON kills the AiMesh backhaul; MLO OFF restores it** (tester, GT-BE98 CAP + RT-AX92U
  nodes) — rule out the nodes' MLO capability, the cold-cycle rule and dirty-install residue before
  calling it Reaper's; a missing guardrail would be ours. **[owed: needs a mesh]** ↳ notes: `mlo-kills-aimesh-backhaul.md`
- **[P2] Warden "crash" on the BE92U addon box** after an amtm + Diversion update — one code-plausible
  path (addon nvram storm → wlcsm wedge → Warden chain missing). The defensive half is built: rwatch
  re-applies a missing chain. The root cause still wants the tester's syslog.
  **[owed: tester data]** ↳ notes: `warden-crash-be92u-addons.md`
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

- **[P2] Firmware page: the overlay's "Close" should be "Cancel", and cancel** (owner, 2026-09-07)
  — the escape hatch that appears on the blocking overlay during a download or upload only hides the
  overlay; the transfer it was covering keeps running to the end. It should read Cancel, close the
  overlay AND abort the upload or download it covers, and it must not be offered once the upload has
  completed (the router is being written from that point and nothing can stop it, which the page
  already knows). **[owed]** ↳ notes: `firmware-veil-cancel.md`
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
- **[P3] DNS Privacy (DoT): sequential failover instead of round-robin** — stubby is configured
  `round_robin_upstreams: 1`, so several DoT servers rotate rather than fail over, and DoT replaces the
  WAN DNS list outright; a switch to sequential order is one line, the LAN-filter interaction needs
  a note. **[project]** ↳ notes: `dot-strict-order.md`
- **[P3] Resolver health check: IPv6 first, not IPv6 only** (owner, 2026-09-07) — today an IPv6
  server is honoured only while the router's IPv6 service is on, and idles otherwise. Instead let
  the watched server carry both addresses: probe over IPv6 first and fall back to the IPv4 address
  when IPv6 is down, disabled, or not supported on the path, so the check keeps watching the same
  server through an IPv6 outage; the failover then moves whichever address family's line is in the
  router's list. Needs a second address field (or an IPv4/IPv6 pair in one), a family-aware probe
  order, and a status line that says which family answered. **[project]** ↳ notes: `dnshc-ipv6-first.md`
- **[P3] Switch port mirroring to an external IDS** — the software `tc mirred` path is present;
  whether it sees accelerated flows is the decisive unknown. **[project]** ↳ notes: `port-mirroring-ids.md`

---

## Documentation

- **[P3] Translations — one residual** — the pinned protocol values and the deliberately literal
  strings; the About-page humour stays English by choice. ↳ notes: `translations-residual.md`
- **[P3] Make `cut_rung` own the version/count restatements** across the docs. ↳ notes: `cut-rung-restatements.md`

---

## Code quality / deferred (with reason)

- **[P2] The code-review MEDIUM/LOW tail, batch B** — `do_reaper_conn_cgi` lock order and the
  iptables-restore batching are owner-deferred; `pinTarget()` is closed; the `rexport` batched sed
  and the dashboard CSS audit shipped. **[owed: the two deferred items]** ↳ notes: `code-review-tail.md`
- **[P3] Policy Routing: recapture of flows that leaked while the rules were absent** — healer path
  only, if ever; never a blanket `conntrack -F`. **[deferred]** ↳ notes: `pbr-conntrack-recapture.md`
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
- **B.5. [P1] Internet speed test fails on 10 Gbit/s links** (GT-BE98 field diag, v3.0.0) — not explainable
  from source; instrumented in v3.0.5. Also a first-run-after-boot "Latency test failed" on the
  BE96U. **[blocked — development]** ↳ notes: `speedtest-10g-links.md`
