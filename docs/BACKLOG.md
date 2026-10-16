# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.4.5** · 2026-10-16 <!--@stamp-->

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

- **[P2] A factory Reaper router could not be added as an AiMesh node** (field, a BQ16 under an
  MLO GT-BE98) — Reaper ships WPS off and the join's WPS arm sat inside that setting; a join now
  gets WPS on its onboarding band only, the setting untouched.
  **[in v3.4.5; owed: a Reaper-to-Reaper join with MLO on, the node logging the WPS line]**
  ↳ notes: `aimesh-factory-node-wps.md`
- **[P3] Operation Mode changes and the MLO "Get started" button handed off to the stock wizard**
  — AP, Media Bridge and Router run Reaper's step page; the MLO button opens the Wireless console;
  Repeater (rung B2) still uses the wizard.
  **[in v3.4.5; owed: AP dhcp/static, MB 5G + 6G WPA3, back to Router, a wrong MB password]**
  ↳ notes: `qis-aimesh-only.md`
- **[P2] AiMesh with a Reaper main router: the upgrade contract, the node version string, the
  setup notice** — mesh upgrade = download and verify only; `webs_state_info` in the Merlin shape;
  the firmware page's mesh path re-enabled; AiMesh.asp names the x_Setting gate.
  **[in v3.4.4; owed: a mesh - node sees the update and the right version, upgrade completes]**
  ↳ notes: `aimesh-node-firmware-refused.md`
- **[P3] USB: `restart_nasapps` ran once per mounted partition** — hotplug now restarts once per
  mount wave (3 s settle). **[in v3.4.4; owed: a 2-partition disk = one `restart_nasapps`]**
  ↳ notes: `nasapps-restart-per-mount.md`
- **[P3] Samba restarted on every WAN up (twice with the WireGuard server on)** — now only when SMB
  over the WAN is on or br0's IPv6 addresses changed.
  **[in v3.4.4; owed: an SMB session survives a PPPoE reconnect; an IPv6 prefix change restarts
  it once]** ↳ notes: `samba-restart-every-wan-up.md`
- **[P2] "skb->nr_frags N exceed max_sg_array 4" is a dropped packet, not noise** (field, GT-BE98)
  — stubby's interleaved DoT writes build >4-fragment non-GSO skbs once the upstream RTT is long
  (IPv6 DoT through a 6in4 tunnel); the Runner drops each one (1:1 with eth1 `tx_dropped`). Fix:
  `netif_skb_features()` linearizes them, `net.core.reaper_tx_sg_max` (0 = stock).
  **[in v3.4.3; the GT-BE98 reporter to confirm on the beta: IPv6 DoT kept, refused packets 0, the
  cap's fired count climbing]** ↳ notes: `runner-sg-frag-cap.md`
- **[P1] 5 GHz and 6 GHz radios dead after a network restart with Dynamic puncturing on** (owner
  RT-BE96U, twice) — `restart_net` (an IPv6 or LAN change) tore the radios down without stopping
  rpunctd / reaper_bwfloor / rchqd and never dropped `wlready`; the wl1 + wl2 dongle firmware
  trapped 7 s in and stayed down until a power cycle. The readers now stop beside `stop_acsd()` in
  every teardown branch, an armed window is waited out, and they key on `rc_service` themselves.
  **[in v3.4.3; owner-confirmed 2026-10-14 on the test rung (two `restart_net`, radios survived);
  the GT-BE98 tester to confirm on the beta]** ↳ notes: `wl-readers-quiesce.md`
- **[P2] The dashboard says Connected while LAN clients have no name resolution** — rdnshc now
  checks the LAN path; amber status + tooltip.
  **[in v3.4.2; owner to confirm the amber state]** ↳ notes:
  `dashboard-connected-lan-dns.md`
- **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — no hang path
  today; large list saves overran httpd's request line - now POSTed.
  **[in v3.4.2; reporter to confirm a large paste]** ↳ notes:
  `firewall-hosts-paste-blanks-gui.md`
- **[P3] Renaming the login name stopped every cron job until a reboot** (was "GT-BE98 v3.0.0 empty
  crontab") — cru now adopts the orphaned crontab.
  **[in v3.4.2; owner to confirm: rename the login, cru l]** ↳ notes:
  `gt-be98-empty-crontab.md`
- **[P3] The header's Internet tooltip showed on the dashboard only** (owner) — the shell framing
  every other page had the pill but not the tooltip, the amber state or the landns data; it now
  carries the dashboard's box, readings and colours, with the shared functions kept verbatim.
  **[in v3.4.2; owner to confirm: hover the Internet pill on any
  framed page]** ↳ notes: `shell-header-internet-tooltip.md`
- **[P1] SMB login refused after the first Samba start of a boot** — accounts were enrolled before
  `/var/lib/samba/private` existed; smbpasswd exits 1 silently without it, so the passdb stayed
  empty. The directories now precede enrollment; a failed enrollment is logged by account name.
  **[in v3.4.2; owner to confirm: reboot with Samba on, first-start
  login]** ↳ notes: `smb-login-refused-first-start.md`
- **[P3] Five kernel one-hunk CVEs from the 2026-08-30 check** (2023-52881, 2024-47684, 2024-50154,
  2023-6932, 2024-50299) — the 4.19.y hunks ported; all LOW, three reboot-class. The 2024-50154 hunk
  needed the from_timer guard below before it could ship.
  **[in v3.4.2; soak on the owner's box owed]** ↳ notes:
  `cve-check-2026-08-30.md`
- **[P3] Navigation rail icons differed between the dashboard and the shell** (owner) — Reaper menus
  fell to the circle-dot; one glyph per menu now, the same on both rails.
  **[in v3.4.2; owner to confirm on the shell rail]** ↳ notes:
  `nav-rail-icons.md`
- **[P1] v3.4.0 hung or rebooted under TCP load** (field, two boxes) — the CVE-2024-50154 hunk ran
  `del_timer_sync` from inside its own timer; a `from_timer` guard removes the self-deadlock. The
  v3.4.0 beta was withdrawn for this.
  **[in v3.4.2; owed: SYN-flood soak on the owner's box, the RT-BE88U reporters]**
  ↳ notes: `kernel-reqsk-timer-deadlock.md`
- **[P3] A first boot in a DST zone kept the stock DST rule** (field, US clock an hour off) — the
  setup page now writes `time_zone_dstoff` from the bundled zone table, as the retired wizard did.
  **[in v3.4.2; owed: a factory-reset first boot in a DST zone]** ↳ notes:
  `firstboot-dst-rule.md`
- **[P2] The stock setup wizard was still reachable outside AiMesh** — the default CGI, wanduck's
  first-use captive redirect, the LAN-subnet landing and a dead menu entry all led into it; every
  path is closed and the kept AiMesh window carries the Reaper palette.
  **[in v3.4.2; owner confirmed the window on _r2/_r3; owed: factory-reset captive
  test once a WAN exists, subnet landing on a tester]** ↳ notes: `qis-aimesh-only.md`
- **[P3] AiMesh add-node window: centred title, progressive wording, prerequisites box, all 25
  languages, long words clipped** (owner review) — the search page got its own dictionary keys; a
  gate proves every key the AiMesh pages use exists in every pack.
  **[in v3.4.2; owner confirmed on _r3; owed: a non-English pass on a phone]** ↳ notes:
  `qis-aimesh-only.md`
- **[P2] A new or factory-reset router still joined its WAN port to the LAN once** (owner) — stock
  Auto-detect was the factory default and can only find the WAN by bridging; the factory default is
  now the port labelled WAN with Auto off, and on that path lldpd no longer binds a WAN interface.
  An upgrade keeps the stored choice.
  **[in v3.4.2; owed: a factory-reset first boot with the cable in the WAN port, then in the 2.5G
  port]** ↳ notes: `autowan-wan-pin.md`
- **[P3] Three DNS Failover switches started on at factory** (owner) — Device names across networks,
  IPv6 device names and the LAN name resolution check now start off, like the other three on that
  row. An upgrade keeps the stored values.
  **[in v3.4.2; owed: a factory-reset first boot shows all six off]** ↳ notes:
  `defaults-optional-off-rule.md`
- **[P2] A diag marked CLEAN carried the owner's IPv6 prefix** (owner's report, 2026-10-12) — the
  sanitizer wanted a tail after `::`, so a routed prefix in a Warden or ip6tables line passed; the
  reverse-zone names spelled the same prefix as nibbles; a DHCPv6 DUID kept the router MAC's last
  four bytes. All three shapes are redacted now and the tripwire counts IPv6 residue (diag v1.3.35);
  the _r5 report then printed a device's own DHCP domain raw, so the sanitizer is a pipeline of
  targeted stages with a client-names stage, and the tripwire counts unmasked names (v1.3.36).
  **[in v3.4.2; confirmed on the owner's box: v1.3.35 (_r5), v1.3.36 (_r6: the domain
  reads [CLIENT-DOMAIN-1], residual client names 0, CLEAN)]** ↳ notes: `reaper-diag-counters.md`
- **[P3] Kernel CVE-2026-43198: a v6-mapped TCP child was used before its IPv6 state was set**
  (audit V8) — upstream fix ported to 4.19 with the exported API unchanged.
  **[in v3.3.8, metal owed: TCP to the router's listeners, SYN flood, 24 h soak]** ↳ notes:
  `audit-2026-10-06-remainder-plan.md`
- **[P3] rc ran with umask 0: files it created without a mode were world-writable** (field, GT-BE98)
  — ASUS's own `umask(022)` switched on after the boot directories.
  **[in v3.3.8; owed: 24 h add-on soak, reporter's two files]** ↳ notes: `rc-umask-zero.md`
- **[P2] Hardware QoS shaped nothing on a PPPoE line** (field, GT-BE98) — both engines programmed
  `ppp0`, which has no traffic-manager queues (rc=108); they now shape the physical port - and never
  a port that also carries the LAN (v3.3.9).
  **[in v3.3.7/v3.3.9; reporter to confirm]** ↳ notes: `hwqos-pppoe-shaping.md`
- **[P1] GT-BE98 / GT-BE98 Pro main router unusable on v3.3.8** (field, three units) — the v3.3.7
  parent resolution shaped the eth1 switch trunk when the WAN is the 2.5G WAN/LAN-1 jack (vlan4094);
  a LAN-member parent is never shaped now.
  **[in v3.3.9; confirmed on the test images, owed: the CI image]** ↳ notes:
  `be98-hwqos-lan-trunk.md`
- **[P2] BQ16 / BQ16 Pro client list empty on every page but Devices** (field) — httpd read
  networkmap's client table with a member missing (`subunit`, gated on Captive Portal); the member
  is pinned unconditional.
  **[in v3.3.9; tester to confirm counts + lists]** ↳ notes: `bq16-topology-zero-clients.md`
- **[P2] ZenWiFi BQ16 (BE25000)** — CI-built since v3.3.3; a five-node BQ16 mesh runs v3.3.8.
  **[owed: a tester]** ↳ notes: `bq16-onboarding.md`
- **[P3] GT-BE19000 shipped the GPL 39274 networkmap** — the clean room now copies the reference
  build over it, hash-pinned.
  **[in v3.3.9 CI; owed: a router-mode tester]** ↳ notes: `gt-be19000-networkmap-prebuilt.md`
- **[P1] Audit 2026-10-06 remediation** — VPN credential download row behind login, rdnsmapd
  LAN-only, strongSwan 6.0.6.
  **[in v3.3.6, metal owed]** ↳ notes: `audit-2026-10-06-remediation.md`
- **[P3] Audit 2026-10-06 remainder, released part** — `/tmp` hardening (F1/V3/V5), Survey CSV guard
  (V10), app installer removed (V11).
  **[in v3.3.7, metal owed]** ↳ notes: `audit-2026-10-06-remainder-plan.md`
- **[P3] IPv6 clients had no names in a LAN DNS filter** (owner) — `rv6names` maps each device's
  current IPv6 addresses to its DHCPv4 name for every network's resolver.
  **[in v3.3.7; 10 names seen on the owner's box (r28), owner to confirm in the filter]** ↳ notes:
  `ipv6-device-names.md`
- **[P3] Internet Card on the Dashboard did not refresh for IPv6** — v6 painted once at load; client
  v6 waited on networkmap.
  **[in v3.3.7, metal owed]** ↳ notes: `dashboard-ipv6-refresh.md`
- **[P3] Rule Status walker showed up in the Devices list** (owner) — a stand-in host held a real
  device's address; walker v1.10 picks only free ones.
  **[in v3.3.7; owner to confirm]** ↳ notes: `walker-standin-device-collision.md`
- **[P3] reaper_diag printed the stored puncturing gain (0) instead of the effective one (15%).**
  **[in v3.3.7 (diag v1.3.33), metal owed]** ↳ notes: `diag-punct-gain-display.md`
- **[P3] Two stock hygiene items from the 2026-10-02 cppcheck of `rc/usb.c`** — unbounded `%[^\n ]`,
  leaked `FILE *`; not reachable.
  **[in v3.3.7; nothing field-visible]** ↳ notes: `usb-boot-mount-chain.md`
- **[P3] Connections showed IPv6 flows as "2001" rows** (owner) — the accelerator-table reader cut
  IPv6 addresses at the first colon; both readers now skip IPv6 entries (conntrack lists them).
  **[in v3.3.7, metal owed]** ↳ notes: `HISTORY.md`
- **[P2] Code review 2026-10-07 remediation** — pre-auth IG/CTA/WPAD rows out, archive rows behind
  login, dead code, S1.
  **[in v3.3.7, metal owed]** ↳ notes: `audit-2026-10-07-remediation.md`
- **[P2] IPv6 remediation, phase 1** — GK captive, Service Intercept, rwatch, SNMP, DHCPv6 names,
  diag, feed markers dual-stack.
  **[in v3.3.7; Service Intercept IPv6 and rwatch IPv6 seen working on the owner's 6in4 box, the
  rest metal owed]** ↳ notes: `ipv6-remediation.md`
- **[P2] IPv6 remediation, phases 2-5** — Flow Explorer + names, Devices + DHCPv6 reservations,
  rtrafd probe/labels, Advisor listener.
  **[in v3.3.7; rtrafd IPv6 labels seen live (11 devices); the rest metal owed]** ↳ notes:
  `ipv6-remediation.md`
- **[P2] Firewall page: Apply / Keep / Revert looked dead on the first click** (owner) — the page
  re-read the state once before rc had armed; now it dims the button and polls until the state is
  real.
  **[in v3.3.7; r25 metal: no refused second Apply; owner to confirm the feel]** ↳ notes:
  `firewall-apply-confirm-clicks.md`
- **[P3] Diagnostics did not cover the 2026-10-08 work** — v1.3.31 adds per-network IPv6, the health
  check and order, the tunnel, the tunnelbroker rule and the per-family intercept gate.
  **[in v3.3.7, metal owed]** ↳ notes: `diag-coverage-2026-10-08.md`
- **[P3] Connections tab mangled IPv6 endpoints** (owner) — zero-padded addresses, IPv6 rows of a
  named device shown unnamed, LAN IPv6 labelled External.
  **[in v3.3.7, metal owed]** ↳ notes: `HISTORY.md`
- **[P3] Devices page clipped its last column at the right edge** (owner) — every block capped at
  1120 px under an unwrapped table; the table card now sets the page width and rows wrap before they
  scroll.
  **[in v3.3.7, metal owed]** ↳ notes: `HISTORY.md`
- **[P3] rwatch called a silent 6in4 server "normal" while the tunnel was down** (owner) —
  tunnel-aware note.
  **[in v3.3.7, metal owed]** ↳ notes: `firewall-tail-loss-2026-10-08.md`
- **[P1] Stock auto-WAN-port bridged the ISP port into the LAN** (owner) — WAN port pinned once
  known; WAN Ports page replaces the Dual WAN tab.
  **[in v3.3.6; owner: Auto across boots + a cable pull]** ↳ notes: `autowan-wan-pin.md`
- **[P1] rtrafd busy-loops on v3.3.4** (field, RT-BE88U) — a ~10.7k-entry conntrack table; pass now
  paced by its cost.
  **[in v3.3.6; RT-BE88U reporter to confirm with the crawler running]** ↳ notes:
  `rtrafd-conntrack-pacing.md`
- **[P2] Site Survey shows many WPA2/WPA3 networks as WEP** (field, v3.3.4-beta) — parser missed
  wl's `RSN (…):` header, fell back to the privacy bit.
  **[in v3.3.6; reporter to confirm]** ↳ notes: `site-survey-wep-security.md`
- **[P3] Site Survey polish after r4** (owner) — empty 6 GHz band reported as a refusal; raw
  security names; heading row scrolled away.
  **[in v3.3.6, metal owed]** ↳ notes: `site-survey-page.md`
- **[P3] Advanced Connections window smoothing** — one measurement per frame, eased glide.
  **[in v3.3.6, metal owed]** ↳ notes: `conn-detail-panel-follow.md`

- **[P3] rwatch could not write an incident bundle before the clock synced** (owner's diag) — a cold
  boot without NTP starts in 2023, so the dump throttle read the last bundle as recent and the
  outage timer ran on the wall clock; a `.last` ahead of the clock throttles nothing, the outage
  timer runs on uptime, the FAILURE line follows the dump and says what it did.
  **[in v3.4.2; owed: a no-WAN boot on metal]** ↳ notes: `chain-signature-watchdog.md`
- **[P3] lldpd read four bytes past a VLAN-tagged frame of MTU size (CVE-2026-46433)** —
  `lldpd_decode` moved `s-12` bytes from offset 16; any L2-adjacent host could crash the AiMesh
  wired-topology daemon. Fixed in both vendored trees.
  **[in v3.4.2; owed: a tagged LLDP frame of MTU size on metal]** ↳ notes:
  `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **[P3] Samba's private directory was world-writable** — `mkdir_if_none` makes 0777; it is 0700
  after the mkdirs now.
  **[in v3.4.2; owed: `ls -ld /var/lib/samba/private` after a Samba start]** ↳ notes:
  `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **[P3] OpenVPN 2.7.8 security fixes backported** (CVE-2026-88964, CVE-2026-84790 and two hardening
  commits) onto the 2.7.7 tree; the full 2.7.8 import stays for the next component rung.
  **[in v3.4.2; owed: an OpenVPN client and server session on metal]** ↳ notes:
  `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **[P3] The LAN name check's silent-upstream pass asks every upstream at once** — it was one wait
  per server inside rdnshc's loop (up to 6 s a minute while failing, slipping the health check's
  cadence).
  **[in v3.4.2; owed: a failing-upstream run with the silent list showing]** ↳ notes:
  `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **[P3] Diagnostics v1.3.37: a generic device/OS word used as a client name is masked at its
  template position only** — it used to blank that word across the whole report (`uname`, `ps`).
  **[in v3.4.2; owed: a diag on metal]** ↳ notes: `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **[P3] First-boot DST rule: Apply waits for tz_db.json** — a submit that beat the fetch sent no
  rule; the setup page holds the button until the reply, a failed fetch, or 8 s.
  **[in v3.4.2; owed: a factory-reset first boot]** ↳ notes: `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **[P3] IPv6 device names emptied the DNS cache every few minutes** — `rv6names` signalled every
  dnsmasq on any change and dnsmasq's SIGHUP flushes its cache; one instance per names file, a 15
  min hold and 5 min pacing now.
  **[in v3.4.2; owed: an hour of syslog: `rv6names/br0/hosts` reads a few per hour, br55 only on its
  own changes, `killall -USR1 dnsmasq` cache counts not reset]** ↳ notes: `dhcp-hostname-store.md`

---

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P2] MLO ON kills the AiMesh backhaul.** No Reaper code is on the MLO path; the lead is the
  warm-reboot MLO fabric (no station associates until a power cycle). A Reaper node failing under an
  MLO main router was a separate defect, fixed in v3.4.5 (Waiting).
  **[investigated 2026-10-15; owed: the power-cycle test, owner box then the reporter]**
  ↳ notes: `mlo-kills-aimesh-backhaul.md`
- **[P2] Traffic Analyzer non-functional on BQ16 firmware** — buttons, graphs and most of the page
  were missing in a user's screenshot; cause to investigate.
  **[needs data]** ↳ notes: `traffic-analyzer-bq16.md`
- **[P2] AI Advisor arming code resets from an admin shell** — `nvram unset rmcp_code_hash` + reboot
  = first-setup path. Direction: a missing or altered record locks the Advisor until a factory reset
  (log line + Dashboard warning); hash + salt move from nvram to a sealed root-only `/jffs` file.
  **[plan written; not scheduled]** ↳ notes: `advisor-arming-code-admin-reset.md`
- **[P3] Update-manifest signature stays inert (R09)** — accepted trade.
  **[accepted]** ↳ notes: `manifest-signature-inert-r09.md`

---

## UI / UX polish

- **[P3] Loading/Restarting overlay: native redesign remainder** — 24 stock `confirm()` dialogs on 9
  pages. **[owed: the confirm() pass]** ↳ notes: `loading-overlay-redesign.md`

---

## Potential Features to add

- **[P2] Code signing: manifest + images, with a pre-upload verdict.** **[scheduled]** ↳ notes:
  `manifest-signing-shelved.md`
- **[P3] Wi-Fi VLANs: the two missing pieces.** **[project]** ↳ notes: `wifi-vlans-residual.md`
- **[P3] Attainder — control by names** (resolver-step domain blocker). **[project]** ↳ notes:
  `attainder-name-control.md`
- **[P3] Unbound beside the existing resolver path.** **[project]** ↳ notes: `unbound-resolver.md`
- **[P3] North star — replace stock GUI pages with Reaper-native ones.** **[ongoing]** ↳ notes:
  `native-page-migration.md`
- **[P3] Staged ("batch") changes — one save, minimal restarts.** **[project]** ↳ notes:
  `staged-batch-changes.md`
- **[P3] Mimic — hardware port mirror to an external IDS** (WAN Ports page, every wired port,
  dual-WAN aware) — Phase 0 mostly proven.
  **[owed: accelerated-flow + restart tests, then build]** ↳ notes: `port-mirroring-ids.md`
- **[P3] Policy Routing on Warden's country sets.** **[feature, owner call]** ↳ notes:
  `pbr-warden-country-sets.md`
---

## Documentation

- **[P3] Add-on integration points** — publish what an external audit may read; decide on a format
  marker. **[owner call]** ↳ notes: `secaudit-external-addon.md`

---

## Code quality / deferred (with reason)
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
- **[P3] GitHub release retention — the prune is the owner's to run.**
  **[owner action]** ↳ notes: `release-retention-prune.md`
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
- **[P3] WireGuard server starts before NTP sync** — the clients wait for `ntp_ready` and retry from
  cron; the server does not. Investigate gating it the same way. **[working as intended]** 
  ↳ notes: `wgs-start-before-ntp.md`

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report is not re-investigated.*

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
