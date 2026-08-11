# RT-BE Series "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done), **[blocked]** (external cause), **[shelved]**
(deliberately deferred), **[cosmetic]** (polish, non-blocking).

**Priority** (by impact on user-facing functionality): **[P1]** core function
broken or at risk for users · **[P2]** degraded function, meaningful annoyance, or
privacy exposure · **[P3]** cosmetic, polish, internal quality, or deferred-by-decision.

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md). Completed items are moved
> to the changelog and removed from this file. **This backlog lists only work that is
> not yet done** — on-hardware validation of already-shipped features is not tracked here.

---

## Open bugs / under investigation

- **[P1] VPN speedtest hang → `sched: RT throttling activated` → wireless-only drop —
  ROOT-CAUSED at source; a decisive on-box diagnostic is the next step before any fix.**
  (Field 2026-08-04, BE96U: built-in Ookla test over an active VPN, QoS off, 4 Gbps ISP —
  hung at ~1.1 Gbps; syslog `sched: RT throttling activated`; wireless clients dropped,
  wired stayed up.)

  - **Cause chain (stock-inherent, not Reaper):** the platform boots with
    `sched_rt_runtime_us=99000/100000` and `CONFIG_RT_GROUP_SCHED` off, so blowing the
    99 ms/100 ms RT budget on a CPU throttles **every** RT task on that core. Broadcom's
    `rtpolicy` promotes **ksoftirqd to SCHED_RR prio 5** and pins `bcmsw_rx`/`spu_rx`/`pdc_rx`
    (RR/5) to CPU0. VPN crypto is not runner-accelerated → runs in softirq → RT-promoted
    ksoftirqd saturates a core at ~1.1 Gbps → throttle fires → the Wi-Fi driver kthreads (RT,
    policy set inside the closed `wl.ko`) freeze with it → wireless drops; wired survives
    because it is runner-offloaded. Reaper daemons request no RT priority (verified).

  - **Decisive diagnostic (no build):** on-box, demote ksoftirqd to normal scheduling —
    `chrt -o -p 0 <pid of ksoftirqd/N>` per thread (or `echo -1 > /proc/sys/kernel/sched_rt_runtime_us`)
    — then rerun the same VPN speedtest. Hang + wireless drop gone ⇒ confirms the chain. Record
    **which VPN engine** was active (WireGuard/OpenVPN ⇒ ksoftirqd path; IPSec ⇒ the SPU
    `spu_rx`/`pdc_rx` RR/5 threads on CPU0 instead).

  - **Candidate fix (after the diagnostic confirms):** remove ksoftirqd's RT promotion in
    `rtpolicy/scripts/rt_settings_kthreads.txt` (restores the mainline default, keeps the RT
    throttle as a safety valve); optionally + affinity separation and RPS spread for tunnel
    softirq. `sched_rt_runtime_us=-1` rejected as the primary fix (removes the safety valve).

- **[P1] BE98 Speed Test crashes/freezes with class-based QoS enabled.** Field reports that with
  QoS enabled on the BE98, the speed test crashes — not everyone is affected (config-dependent).
  Owner also observes a **momentary freeze on the built-in speed test in HW Classful mode
  (`qos_type=11`, the 8-queue WRR scheduler) but NOT in the HW Classless modes**.

  - **Source trace (blob/metal-bound):** the built-in Ookla test is **router-originated** traffic;
    its WAN egress traverses `QOSO` at `POSTROUTING`, so in type-11 it is CONNMARK'd into the
    default class → default egress queue and is subject to that queue's PI2 shaper + the WRR
    schedule + the **aggregate port shaper** (`setportshaper=qos_obw`). type-10 has none of these
    (qid0 shaper only) — which is why the freeze is classful-only. Both `ookla_exec` and the rdpa
    runner are **blobs** — not safely fixable from the auditable source.

  - **Metal diagnostics to split it:** run the built-in test on type-11 while capturing
    `logread`+`dmesg`+`fc status`+`tmctl getqstats`; repeat on type-10 (control); run an
    **external/LAN-client** test under type-11 (if it does NOT freeze, the router-local path is the
    confound); set `qos_pshaper=0` or raise `qos_obw` to line rate → re-run. **Interim workaround:**
    run the built-in test with QoS on a classless mode or off, or use a LAN-client/external test.

- **[P2] Smart Connect Rules — enabled/connected band shows `--` for every field (field 2026-08-08,
  BE96U tri-band).** On **Smart Connect Rules** (`Advanced_Smart_Connect.asp`, menu
  `<#smart_connect_rule#>`), the "5 GHz-1" band shows `--` on all config fields. Two candidate causes,
  very different fixes: (a) **label/mapping bug** — the label comes from `wl_nband_title` (`state.js`),
  which only appends the `-1`/`-2` suffix when a band type appears more than once, so a tri-band
  2.4/5/6 box should render "5 GHz" not "5 GHz-1"; and the page builds column **headers** band-ordered
  (`get_wl_unit_by_band`) while filling **cells** by raw unit index, so a mismatch can label one radio
  and show another's (empty) policy → `--`. (b) **not-a-bug** — `--` simply means no steering rule is
  configured for that band. Disambiguate with: do the 2.4/6 GHz columns show values or also `--`, plus
  `nvram show | grep -E "^wlnband_list=|^smart_connect_x=|^smart_connect_selif_x=|^bsd_(steering|sta_select)_policy"`.
  Any fix must enumerate **dual / tri / quad-band** correctly, like `Reaper_WiFiPro.asp`. [owed]

- **[P2] MLO: individual per-link rows no longer shown for a device (owner report 2026-08-06).**
  Investigated: the name-unification rung did **not** touch MLO code; on the **Devices page this is by
  design** (`do_reaper_dev_cgi` folds affiliated randomized MLO links into their MLD device and the page
  hides `mlo_link` rows — v1.9.2/1.9.3 "merge Wi-Fi 7 MLO links into one row"). So the regressed screen
  is almost certainly **not** the Devices page — the owner needs to name **which view** used to show the
  per-link rows (stock Wireless Log, Connections, or a Network-Map client detail). Likely fix: have the
  target view *resolve* each link MAC to the parent's unified name ("MyLaptop · 5 GHz link") rather than
  fold it away. [owed — owner to name the exact screen; then scope]

- **[P2] AI Mesh Search** — investigate; reported non-functional a while back.

- **[P2] Dual-WAN failover: both NextDNS profiles receive DNS logs though only one WAN is live.**
  Secondary WAN (2.5 Gbps, DHCP, its own NextDNS profile) is active; the future primary (10 Gbps,
  PPPoE) is not yet connected. With only the secondary live, **both** NextDNS profiles show traffic;
  expected only the active WAN's profile to log.

- **[P3] The connection-health probe lists the router's own LAN IP (e.g. `192.168.50.1`) as a device
  row — field-confirmed 2026-08-08 as the ONLY remaining "IP in the MAC slot" row after the v2.3.0
  one-row-per-device dedup (owner confirmed the dedup itself looks good on metal).** Cosmetic — the
  probe pings the gateway/self IP and emits it like a client. Filter the router's own LAN address
  (or bucket it as the router, consistent with the Traffic Analyzer's hidden "Router" self-bucket)
  in rtrafd's health output. [cosmetic — owner: no fix needed now]

- **[P2] Shipped QoS preset rules classify by transferred bytes — streaming lands in the bulk queue
  (found 2026-08-10, live metal).** The stock `qos_rulelist` default
  (`Web Surf>>80>tcp>0~512>0<HTTPS>>443>tcp>0~512>0<File Transfer>>80>tcp>512~>3<File Transfer>>443>tcp>512~>3`)
  demotes any HTTPS flow past 512 KB to class 4 ("Downloads"). Streaming video is HTTPS and passes that
  in seconds, so a TV's flows — and under type 11 (upload-only) its **ACK stream** — ride the bulk queue,
  4th of 5 under strict priority. Metal proof: the queue named "Streaming" had **0 packets** while the
  video sat in "Downloads". Separately, `connbytes` matching forces per-packet re-evaluation, which the
  rule parser marks non-sticky (`rule_gum=0`), so these rules are incompatible with hardware flow
  offload — the guidance since the v2 metal validation has been "classify on port/proto/IP/MAC, never
  transferred bytes", which the shipped defaults themselves violate. **Fix:** replace the preset pack in
  `defaults.c` with port/proto rules carrying an empty `transferred` field, and have `Reaper_QoS.asp`
  warn when a user rule uses a transferred range under type 11. (Worked around on the owner's box by
  nvram only; the shipped default is unchanged.) [owed]

## Known issues (cause identified)

- **[P3] Unescaped `title='...'` attributes on the stock client lists — PARTIALLY DONE.** The reported
  apostrophe stored-XSS/garble was fixed in v2.1.3; the three client-popup tooltip fields were encoded
  in v2.2.0. Remaining defense-in-depth only: `client.vendor` / `deviceTypeName` are still emitted into
  single-quoted `title='...'` in `client_function.js`, but those are vendor/OUI-DB-sourced, not
  attacker-freeform. [owed — low, optional]

- **[P3] ASUS-CDN references remain in the non-shipping model UIs (`sysdep/FUNCTION/{ROG_UI,TUF_UI,UI4,
  MULTISERVICE_WAN,ADGUARDDNS_UI}`).** The v2.3.3 de-cloud closed every request in the files that ship
  on this model (verified against the staged `fs.install` tree); **115 references remain** in sysdep
  overlays that are not selected for the BE-series build. They cost nothing today, but they are shared
  source and the sibling branches are ported from this tree, so a future model that selects one of
  those overlays would reintroduce the surface. Needs a per-model shipping check before sweeping.
  [owed — low]

## UI / UX polish

- **[P3] Firmware-page translation pass.** The `RFWU_1–31` dict tokens for the native firmware page
  (v2.3.1) are English-seeded in all 25 language packs. [owed]

- **[P3] Loading/Restarting overlay — native redesign remains.** Full-screen coverage + nav/header
  blocking during an apply/reboot is done (v2.2.5, refined v2.3.0). Remaining: convert these modals to
  Reaper-native designs (do with the native-page migration). [owed — migration]

- **[P3] Loader z-index raise is class-wide (watch-item).** The z-index bump was applied to the shared
  `.popup_bg` class, so it also raises `#hiddenMask` (the confirm-dialog backdrop) — benign/positive.
  Watch-item: if any apply/error flow ever surfaces an in-page (non-native) `form_style` modal *while
  the loader is displayed*, it would render behind the loader. Scope the class to `#Loading` only if a
  concurrent-modal case turns up. [watch — cosmetic]

- **[P3] SDN Wi-Fi-key mask can be bypassed by an SSID containing a literal `<b>` tag (watch-item).**
  The shared `state.js showWlHintContainer()` injects the SSID into `innerHTML` unescaped, so an SSID
  literally containing `<b>…</b>` would shift the bold-element index and leave the key visible. Only
  weakens the *new* privacy feature (never a crash or XSS), and the root cause is the pre-existing
  unescaped-SSID behavior in the **shared** `state.js` (out of scope of the mask's design). Optional
  hardening: mask the LAST `<b>` per row instead of index 1. [watch — cosmetic/privacy]

- **Network Map** Review / Disconnect the "Network Map" page from the router GUI. The dashboard button
  should be removed from the header and put in the place of the Network Map item.

- **Addons** Currently when a user has addons the nav menu buttons for Addons is not showing. 
  Rearange the nav menu and add logic to deal with addon nav menu selections.

## Features to add

- **First Boot** The Reaper first boot continues to be problematic. Investigate and improve functionality.

- **Firmware Mesh Nodes** Add a feature to be able to see mesh nodes firmware version from the main 
  hub in the firmware menu. This feature should also allow the user to click on each one and chose the 
  file to update the firmware with or go directly to the node and flash it natively.

- **Firmware Manifest** The manifest is not updated by the automated publish workflow. Need to add that 
  to the workflow so user are notified of new versions.

- **[P2 — OWNER DECISION] Stop committing `.pkgtb` images in-tree under `releases/` (repo-size).**
  GitHub *Release assets* live outside the git repo (no repo-size impact, 2 GB/file limit) and are
  what the update manifest + in-GUI installer download from — the in-tree copies (~750 MB history
  growth per full release) are only for file-tree visibility and nothing consumes them. Option: drop
  the in-tree copy step in `stage_release.ps1` (one-line change) and optionally rewrite history later
  to reclaim past growth. Third-party hosts (OneDrive etc.) are NOT suitable for the on-router
  downloader: unstable direct-URL semantics and they'd break the upgrade script's GitHub host-pin.
  *Update 2026-08-10:* the CI release hand-off now publishes release assets straight from build
  artifacts, so nothing consumes the in-tree copies anymore — dropping them is purely the owner's call.
  (v2.3.1 images were still committed in-tree, so this is not yet done.)

- **[P2] NATIVE FIREWALL SUITE — replace the stock Firewall menu with Reaper-native pages + add engineer features.**
  Owner-approved (2026-08-08) design: a native
  `Reaper_Firewall.asp` hub replacing all four stock tabs (General / Network Services / URL /
  Keyword) plus new tabs — **Status** (live v4+v6 chains + hit counters), **custom Rules** engine
  (Basic form + Advanced DSL, dual-stack, `rc/reaper_fw.c` + `reaper_fw.cgi`, re-apply hook),
  **Egress** control (IoT containment, outbound geo), **Logging** viewer — all with
  **commit-confirm auto-rollback** and anti-lockout invariants. Backend stays iptables/ipset.
  Phased 0→3; each phase build + on-metal (rmcpd lab MCP as the test harness) + fleet fan-out.
  [owed — build; live inspection done]

- **[P3] NORTH STAR — progressively replace stock GUI pages with Reaper-native ones.** Over time,
  migrate stock ASUS/Merlin pages to Reaper-native equivalents (own theme, de-clouded, only the
  functions we want exposed), as already done for Dashboard/QoS/Traffic/Wireless/GK/Warden/Devices/
  Advisor/Conn/QoSDiag/Analytics/Storage/Firmware (v2.3.1). The Firewall suite (above) is the next
  candidate. [ongoing]

- **[P3] Staged ("batch") changes — one save, minimal restarts.** Today each control applies
  immediately (e.g. changing all three Wi-Fi bands = three applies + three `restart_wireless`). Add a
  staging layer: a control's Apply becomes "Add to changes", writing the intended nvram diff into a
  cross-page **pending basket**; a shell bar shows *"Pending changes (N) — Review / Apply / Discard"*;
  Apply validates all first (all-or-nothing), writes nvram in one commit, then runs the de-duplicated,
  correctly-ordered action set ONCE (reboot only if a staged change is reboot-class).

  - *Feasible — the backend already supports it:* one apply POST carries many nvram keys + a chained
    `action_script`, and `restart_wireless` cycles all radios at once, so "3 restarts" is a UI artifact.
  - *Hard parts:* an nvram-key → required-action map + safe ordering; a reboot-class table (most changes
    are service restarts, a few need a COLD reboot — MLO enable/disable, some SDN/op-mode switches);
    staleness/conflict if nvram changed underneath; and scope (clean for Reaper-authored pages, hard for
    stock ASUS pages). *Recommended path:* Reaper-native pages first; quick sub-win = a single Reaper
    Wireless page for all three bands that applies once. The full cross-page system is its own project.

- **Warden Counts** Warden hit counts are still not being persistant across reboots or firmware upgrades.  

- **[P3] Remote syslog push/fetch.** The router can already send its log to a remote collector
  (send-only). Add the ability to **push to / be fetched by** analytics systems (most SIEM pipelines are
  push-based). Pairs with the shipped health-metrics export (Data Export page). Also open from that
  feature: **wireless RSSI/PHY** per-device metrics were deliberately deferred and can be added later
  from the existing `web-broadcom-am.c` backend.

- **[P3] NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST baseline.

- **[P3] Diag: regulatory-mismatch warning.** Make `reaper_diag` (and possibly a Wireless-page hint)
  print an explicit `WARN: territory_code=EU/xx but wlX_country_code=US` line when the factory territory
  and per-radio country codes disagree — self-documents gray-market / region-switched units. Read-only
  compare, no behavior change (firmware must never auto-alter regulatory nvram). [shelved]

## Code quality / deferred (with reason)

- **[P3] `poll_fcache` O(n²)→hash pairing** (`rtrafd.c`). Bounded to ≤1536 flows every 5 s in the
  metal-validated per-client accounting path — a rewrite of a millisecond-scale loop isn't worth the
  regression risk. Revisit only if a flow-heavy box shows real cost. [shelved]

- **[P3] `poll_classes` 7× `tmctl` popen batch** (`rtrafd.c`). Metal measured 2–3 % CPU at the class
  cadence; treated as a non-issue. [shelved]

- **[P3] Theme-token vocabulary consolidation (remainder of D4).** The accidental same-name/different-
  value drift across the 15 Reaper pages was canonicalized in v2.2.7. Still deferred to the migration:
  the naming-vocabulary consolidation (`--panel2`/`--red*` → `--panel-2`/`--crimson*`) and the `--line`
  cream-vs-red divergence, both of which need per-page CSS **usage** rewrites (visual-regression risk).
  [owed — to migration]

- **[P3] `do_reaper_dev_cgi` function-local `static` snapshot arrays aren't re-entrant.** Latent only
  (httpd serialises these requests); a malloc refactor of the multi-return CGI would add leak risk to
  fix a can't-happen case. [shelved]

## Documentation

- **[P3]** Document the non-functional retained features (the firmware update-check UI's stock pieces,
  the removed security-check UI) that are kept only for potential future use.
- **[P3]** Annotate the system defaults.
- **[P3]** Write a user guide for other users.

## Known issues (cannot remediate — closed-source blob)

- **[P3] Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul BSS is
  created even when every feature that would use it is disabled, spamming the log with RADIUS codes for
  an unused radio. Traced to a **closed-source Broadcom blob**; a boot-time suppression script did not
  work and was reverted. [blocked — blob; risk-accepted]

- **[P3] Guest Network Pro (AP-isolation SDN) breaks the 2.5G-1 LAN port when a manual WAN VLAN is also
  active — GT-BE98.** Creating a Guest Pro network with AP isolation makes the 2.5G-1 port stop passing
  untagged main-LAN traffic (an 802.1Q VID-52 tag becomes required). On-metal captures proved there is
  **no userspace interface on this firmware to read or program the hardware switch VLAN/PVID table**, so
  neither a source fix nor a runtime correction hook is possible. **Workarounds:** keep Guest Pro off
  the 2.5G-1 port, move the device to another LAN port, or tag it VID-52; or avoid pairing a manual WAN
  VLAN with Guest Pro on that port. Almost certainly present on stock ASUS too (same blob). Full
  investigation: [`GUESTPRO-2.5G-VLAN-PLAN.md`](GUESTPRO-2.5G-VLAN-PLAN.md). [blocked — blob; risk-accepted]
