# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.1.1** · 2026-09-09 <!--@stamp-->

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

1. **[P2] Apply and Confirm on Policy Routing rebooted the router** — no reboot primitive in the
   path; needs the three captures on the next occurrence.
2. **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — every cru-driven job dead on that box.
3. **[P2] Warden "crash" on the BE92U addon box** — hypotheses ranked, tester data requested.
4. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — needs a repro.
5. **[P3] CVE check 2026-08-30 residue** — the cheap backports; the known-limitation notes are done.
6. **[P3] Code-review tail, batch B** — two items owner-deferred; `pinTarget()` closed.

***v3.1.1 is the beta** (Dev, 2026-09-09; patches 0621–0636). It carries the Failover tab — the
LAN resolver health check and the three dnsmasq switches — the OpenVPN certificate fixes, the
firmware-page Cancel for the upload phase, the Gatekeeper connection-method, MLO-fold and
stale-band fixes, the announced-hostname store, the dashboard clock regression, and the ECS
help-text correction. Items closed by it have been removed from this file and are recorded in
[`CHANGELOG.md`](CHANGELOG.md). Two of them ship **without hardware validation** and are the first
things to check on the beta — the OpenVPN repair path (needs a box with a VPN server configured)
and the Gatekeeper stale-band branch (needs a client moved between radios) — so both stay listed
under Open bugs until a capture exists.*

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
- **[P2] Apply and Confirm on Policy Routing rebooted the router** (owner, logs dated Aug 27) — the
  flicker half shipped fixed in v3.0.5; the reboot half is unexplained, no reboot primitive exists in
  the path, not reproduced on v3.0.5. **[needs data]** ↳ notes: `pbr-apply-confirm-reboot.md`
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
  ↳ notes: `aimesh-pairing-failures-tester.md`
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

- **[P3] Firmware page: the download phase still has no true cancel** — the upload half shipped in
  v3.1.1 (the hatch reads **Cancel** and aborts the in-flight POST). During a download from the
  update server the button still says **Close** and only leaves the overlay, honestly labelled:
  the generic `webs_*` rc dispatch handles START only (`services.c` ~20175), so `stop_webs_upgrade`
  is a no-op, and `reaper_webs_upgrade.sh` runs download → verify → flash in one shot on the router.
  A real cancel there means a kill on a flash-adjacent path, which is a service change and not a UI
  one. **[deferred — needs an rc stop service]** ↳ notes: `firmware-veil-cancel.md`
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

*Nothing open — the `cut_rung` restatement item closed 2026-09-08 and shipped with the v3.1.1 cut.*


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
