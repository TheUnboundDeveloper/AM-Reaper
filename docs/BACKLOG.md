# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.0.7** · 2026-09-03 <!--@stamp-->

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

1. **[P1] Internet speed test fails on 10 Gbit/s links** — instrumented in v3.0.5; owed one diag
   (section 10b) after a failing run, plus the first-run-after-boot "Latency test failed" cause.
2. **[P2] Apply and Confirm on Policy Routing rebooted the router** — no reboot primitive in the
   path; needs the three captures on the next occurrence.
3. **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — every cru-driven job dead on that box.
4. **[P2] Main Wi-Fi network sits on the primary BSS after a factory reset** — the no-wizard
   first-boot flow must own the SDN migration QIS used to trigger.
5. **[P2] Warden "crash" on the BE92U addon box** — hypotheses ranked, tester data requested.
6. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — needs a repro.
7. **[P3] CVE check 2026-08-30 residue** — cheap backports and known-limitation notes.
8. **[P3] Code-review tail, batch B** — two items owner-deferred; `pinTarget()` closed.

---

## Open bugs / under investigation

- **[P2] Router UI on mobile-device browsers: compatibility investigation** (owner, 2026-09-06)
  — survey how the web UI behaves in phone and tablet browsers (iOS Safari, Android Chrome,
  Samsung Internet): layout at narrow widths, touch targets, the theme and loading overlays, the
  Devices/QoS/Traffic tables, and whether every page is reachable and applies correctly. Which
  pages break, on which browser, and how, still to be captured before any fix is scoped.
  **[needs data]** ↳ notes: `mobile-browser-ui-compat.md`
- **[P2] Devices page: wrong connection method, and MLO combining no longer works — REGRESSION**
  (owner, 2026-09-05) — devices show the wrong link type again, and the page no longer folds an MLO
  client's per-band links into one device. Both shipped working earlier (v3.0.9 read the live mesh
  client lists; MLO folding predates it), so a recent change broke one or both: candidates are the
  v3.0.9 Gatekeeper/Devices live-list read, the amaspark backhaul parking (MLO link-set handling in
  v3.0.8), and the OpenSSL rung's rebuild of every consumer. Bisect on the ladder first.
  **[needs data]** ↳ notes: `devices-conn-method-mlo-regression.md`
- **[P2] AiMesh nodes refuse the firmware** (owner report, 2026-09-05) — nodes decline the image the
  router offers them; which models, which message, and whether the refusal is the node's version check,
  the signature check, or the transfer are all unknown. **[needs data]** ↳ notes: `aimesh-node-firmware-refused.md`
- **[P2] Mobile device metrics reported incorrect** (owner report, 2026-09-05) — the per-device figures
  shown for phones and tablets do not match what the devices see; which page, which metric, and against
  what reference still to be captured. **[needs data]** ↳ notes: `mobile-device-metrics.md`
- **[P3] Connections page still labels the scheduler "WRR"** (owner, 2026-09-05) — the classful WRR
  path was removed for its defects, yet the Connections page shows "WRR" as the scheduler in use. Stale
  label or a stale read of the queue discipline; display only. **[owed]** ↳ notes: `conn-scheduler-wrr-label.md`
- **[P2] Apply and Confirm on Policy Routing rebooted the router** (owner, logs dated Aug 27) — the
  flicker half shipped fixed in v3.0.5; the reboot half is unexplained, no reboot primitive exists in
  the path, not reproduced on v3.0.5. **[needs data]** ↳ notes: `pbr-apply-confirm-reboot.md`
- **[P3] Policy Routing page: the first-open symptom was never identified** — the screenshot did not
  reach the record; the strongest candidate shipped fixed in v3.0.5. **[needs the screenshot]**
  ↳ notes: `pbr-first-open-symptom.md`
- **[P1] Internet speed test fails on 10 Gbit/s links** (GT-BE98 field diag, v3.0.0) — not explainable
  from source; instrumented in v3.0.5. Also a first-run-after-boot "Latency test failed" on the
  BE96U. **[owed: one diag after a failing run]** ↳ notes: `speedtest-10g-links.md`
- **[P2] GT-BE98 on v3.0.0 boots with an empty crontab** — rwatch, Warden refresh and the PBR
  deadline watcher all dead on that box. **[needs the GT-BE98 syslog]** ↳ notes: `gt-be98-empty-crontab.md`
- **[P3] CVE / component check 2026-08-30 residue** — no reachable HIGH, nothing MED at defaults;
  what it queues: cheap backports, known-limitation notes, the inert manifest signature, hygiene.
  ↳ notes: `cve-check-2026-08-30.md`
- **[P2] MLO ON kills the AiMesh backhaul; MLO OFF restores it** (tester, GT-BE98 CAP + RT-AX92U
  nodes) — rule out the nodes' MLO capability, the cold-cycle rule and dirty-install residue before
  calling it Reaper's; a missing guardrail would be ours. **[owed: needs a mesh]** ↳ notes: `mlo-kills-aimesh-backhaul.md`
- **[P2] Main Wi-Fi sits on the primary BSS after a factory reset** — the SDN MAINFH/MAINBH migration
  QIS used to trigger never runs until an unrelated apply; the no-wizard first-boot flow must own it,
  without forcing `x_Setting=1` at factory. **[owed]** ↳ notes: `main-wifi-primary-bss-after-reset.md`
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

- **[P3] Advisor page: the "Pin to one client IP (optional)" field's placeholder renders wrong**
  (owner, 2026-09-05) — the default text shown inside the empty input has formatting problems
  (clipping, wrapping, or the placeholder colour/size not matching the other fields). Display only.
  **[owed]** ↳ notes: `advisor-pin-ip-placeholder.md`
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
- **[P2] OpenSSL 3.5 migration, second attempt** — the v3.0.4 withdrawal was a warm-tree stale relink,
  not a missing build: hostapd is compiled here (impl103 wireless tree) and links whatever `openssl`
  points at, but its link rule never sees the library change and the artifact purge stopped at the
  router tree. Retry = widened purge + a gate naming every binary still allowed to link the 1.1 name,
  6 GHz WPA3 as the canary. **[project — test image v3.0.9a passed metal 2026-09-05; packaging + CI + licence paperwork next]** ↳ notes: `openssl35-retry.md`
- **[P3] Switch port mirroring to an external IDS** — the software `tc mirred` path is present;
  whether it sees accelerated flows is the decisive unknown. **[project]** ↳ notes: `port-mirroring-ids.md`

---

## Documentation

- **[P3] Fold `FIREWALL-GUIDE.md` and `VPN-ROUTING-GUIDE.md` into `REAPER-GUIDE.md`** — repoint
  the in-UI `?` links and the httpd doc whitelist as the files retire. ↳ notes: `fold-howto-guides.md`
- **[P3] Translations — one residual** — the pinned protocol values and the deliberately literal
  strings; the About-page humour stays English by choice. ↳ notes: `translations-residual.md`
- **[P3] Make `cut_rung` own the version/count restatements** across the docs. ↳ notes: `cut-rung-restatements.md`
- **[P3] Retire the two guide stubs** once the per-tab `?` links point at guide anchors and older
  images are out of circulation. **[owed]** ↳ notes: `retire-guide-stubs.md`

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
