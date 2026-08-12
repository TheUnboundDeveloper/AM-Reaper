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

  - *Re-check 2026-08-12 — partly superseded, needs re-confirmation before more work:* **v2.2.6**
    (`80fc8bfa88`) fixed a *different* speed-test freeze — `internet_speed.html` polled the result
    buffer with a **synchronous** `hookGet` every 200 ms, so while the ookla binary pegged the CPU
    each blocking XHR stalled the browser main thread ("page unresponsive"). That one hit everyone
    regardless of QoS, and the original "crashes" field reports predate the fix, so they may already
    be resolved. The classful-only *momentary* freeze below is a separate, QoS-mode-dependent
    observation and still stands. **Re-confirm on a v2.2.6+ image before spending metal time.**

  - **Source trace (blob/metal-bound):** the built-in Ookla test is **router-originated** traffic;
    its WAN egress traverses `QOSO` at `POSTROUTING`, so in type-11 it is CONNMARK'd into the
    default class → default egress queue and is subject to that queue's PI2 shaper + the WRR
    schedule + the **aggregate port shaper** (`setportshaper=qos_obw`). type-10 has none of these
    (qid0 shaper only) — which is why the freeze is classful-only. Both `ookla_exec` and the rdpa
    runner are **blobs** — not safely fixable from the auditable source.

  - **Metal diagnostics to split it:** run the built-in test on type-11 while capturing
    `/tmp/syslog.log`+`dmesg`+`fc status`+`tmctl getqstats` (**not `logread`** — syslogd always runs
    with `-O <file>` and never `-C`, so `logread` returns empty on every unit); repeat on type-10 (control); run an
    **external/LAN-client** test under type-11 (if it does NOT freeze, the router-local path is the
    confound); set `qos_pshaper=0` or raise `qos_obw` to line rate → re-run. **Interim workaround:**
    run the built-in test with QoS on a classless mode or off, or use a LAN-client/external test.

- **[P2] AI Mesh Search — "Search for node" finds no new node.** Pre-existing meshes keep working
  after flashing to Reaper; only *new-node discovery* is affected. Reported on GT-BE98/PRO, but
  **do not assume it is BE98-specific**: the only add-node metal test *ever* was BE96U v1.5.0e
  (2026-07-14), so onboarding is untested on every model since, and BE98-only reports may simply
  reflect who uses AiMesh. CAP-side source is **clean** — no Reaper commit touches `www/aimesh`,
  QIS_V3 or the onboarding CGIs. Flow: `aimesh_topology.html` → `/cfg_onboarding.cgi` →
  **`cfg_server` (blob)** scans → `/tmp/onboarding.json` → `ej_get_onboardinglist()` → wizard.

  - **REFUTED — do not re-raise:** the ABI/key-skew theory (GT-BE98 running 39274-era AMAS blobs
    against 39995-level source, as with the networkmap bug). Its `cfg_server` *does* emit `ts_eth`,
    verified. The skew class is real elsewhere; it is not the cause here.

  - **Found 2026-08-12 — there are TWO silent drop gates, not one.** Both are in our auditable
    source and neither logs anything:
    1. `ej_get_onboardinglist()` (`web.c`) requires `model_name` **and** `ts_eth`, else the
       candidate is skipped.
    2. `select_best_onboarding_re()` (`web.c`) requires **all five** of `rssi`, `rssi_5g`,
       **`rssi_5g2`**, `source`, `ts_eth` on a parent before it contributes. If no parent
       qualifies it returns an empty MAC and the node is dropped **even though it passed gate 1**.
       Note `rssi_5g2` is demanded regardless of whether the model even has a second 5 GHz radio.
    Gate 2 was not named in the original investigation and is the better suspect, because a node can
    be discovered perfectly and still never reach the wizard.

  - **Instrumentation is now cut into the v2.3.7 rung (patch 0401) — still UNCOMPILED and
    never exercised.** Three
    `logmessage("aimesh", …)` lines on the failure paths of both gates, naming the MAC and exactly
    which keys were absent. No behaviour change. This exists because the triage has been blocked
    since July on a runtime capture nobody can conveniently take — with this in, the *next* failed
    search writes its own diagnosis to `/tmp/syslog.log`.

  - **Runtime triage (still the decisive step; read-only, needs a spare factory-reset node).**
    Before search `nvram get cfg_obstatus` (expect 1); during (expect 2); after
    `cat /tmp/onboarding.json`; plus `ps w | grep -E "cfg_server|obd|wlceventd"`. Decision tree:
    never reaches 2 ⇒ trigger/httpd (likely all models); reaches 2 but JSON empty ⇒ discovery layer
    (wlceventd/driver VSIE); JSON **has** entries but UI empty ⇒ one of the two gates above, and the
    new log lines say which. Run it on the BE96U too — that splits a Reaper regression from a
    BE98-port issue.

- **[P2] Dual-WAN failover: both NextDNS profiles receive DNS logs though only one WAN is live.**
  Secondary WAN (2.5 Gbps, DHCP, its own NextDNS profile) is active; the future primary (10 Gbps,
  PPPoE) is not yet connected. With only the secondary live, **both** NextDNS profiles show traffic;
  expected only the active WAN's profile to log. [Requires_Reaserch]

## UI / UX polish

- **[P3] Loading/Restarting overlay — native redesign remains.** Full-screen coverage + nav/header
  blocking during an apply/reboot is done (v2.2.5, refined v2.3.0); the overlays are now anchored to
  the browser viewport rather than the framed document — the shell publishes the frame's visible slice
  as `--rv-top`/`--rv-h` and re-anchors `#Loading`, `#LoadingBar` and the Reaper pages' own overlays to
  it (in tree since v2.3.3; that re-anchor's own field regression — the parked FAQ fly-out inflating
  the framed doc by 460 px and clipping QoS/Traffic — was fixed in `1d9d58a2be`).
  **STILL BROKEN — owner, 2026-08-12: several overlays continue to centre on the shell viewport rather
  than the user's screen**, taking no account of the nav rail and header, so they land off-centre. The
  `--rv-*` mechanism only covers the overlays it was explicitly pointed at; the rest were never
  re-anchored and need finding and converting. Measured in a headless browser against the shipped
  block, 1200×900 window, long page scrolled to y=2000: the stock "please wait / N%" block moved from
  **1693 px above the top of the screen** to the centre of the visible area, and a Reaper page's flash
  veil from 416 px above it to the same place — but that measurement covered only those two blocks,
  which is why the rest went unnoticed. Remaining, in order: (i) enumerate **every** overlay/modal in
  the UI and re-anchor the ones still centring on the shell viewport; (ii) replace **every stock
  overlay** with a Reaper-themed equivalent — none should survive in stock styling; (iii) confirm the
  anchoring **on the router** with the real pages, not just headless. [owed]

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

- **[P3] Smart Connect band-mask hazards (watch-items, from the v2.3.5 investigation).**
  Two things worth not re-deriving. (i) `Advanced_Wireless_Content.asp`'s mask builder has a
  `return 7;` fallback; on a tri-band 2.4/5/6 box 7 means 2G + 5G + **5G2** — a radio that
  does not exist — silently dropping 6 GHz from the steering group. Unreachable today
  (guarded by `smartConnectEnable`), but any edit to that guard resurrects it. The mask is
  indexed by **band slot** in the fixed five-element `bandName` array, not by how many radios
  the model has, so `2^N-1` arithmetic is always wrong here; the same bug was already fixed on
  the Smart Connect page's write path. (ii) `shared/defaults.c` ships
  `smart_connect_selif_x = "3"` for HAS_6G models — 6 GHz is deliberately **out** of Smart
  Connect out of the box. Changing that alters RF behaviour for every user, so it is an owner
  decision, not a bug. A simulator that extracts the real band helpers from the tree is kept at
  `scratchpad/smartconnect_sim.js` for reading any future screenshot of that page.
  [watch — no action unless the guard changes]

- **Addons** Currently when a user has addons the nav menu buttons for Addons is not showing. 
  Rearange the nav menu and add logic to deal with addon nav menu selections. [Requires_Research]

## Features to add

- **[P3] Research: IDS/IPS (Suricata/Snort) or eBPF traffic analysis — RESEARCHED 2026-08-12,
  conclusion: DO NOT ship in-firmware.** Findings kept here rather than in a separate document:

  - **Throughput: ~90–98 % loss on the inspected path.** Forwarding is done by the Runner
    (`CONFIG_BCM_RUNNER_MAX_FLOWS=16384`); accelerated packets never reach the Linux stack.
    Inspection requires pulling flows *out* of the accelerator, so the cost is losing hardware
    forwarding, not the detection engine. Anchor: the open `[P1] VPN speedtest` item measured this
    platform's software path saturating a core at **~1.1 Gbps** — with a workload *cheaper per
    packet* than IDS. NFQUEUE inline adds a userspace copy per packet on top.
  - **It would re-create an open P1 defect.** Softirq saturation here triggers RT throttling, which
    freezes the Wi-Fi kthreads inside `wl.ko` and **drops wireless clients while wired survives** —
    precisely the P1 symptom above. That, not the throughput number, is the strongest objection.
  - **eBPF is blocked outright:** `# CONFIG_BPF_SYSCALL is not set` in the shipped 4.19.294 kernel —
    no `bpf()` syscall, so no programs, maps or XDP. Enabling it via `EXTRA_KERNEL_CONFIGS` is
    possible (BE88U jumbo-frame precedent) but 4.19 eBPF is pre-BTF/CO-RE, **and** generic XDP/`tc`
    only sees packets that already lost acceleration — the fastest flows are invisible to it.
  - **Plumbing is present** should a narrow design ever be wanted: `libpcap` and
    `libnetfilter_queue` are in-tree, `NETFILTER_NETLINK_QUEUE` + `XT_TARGET_NFQUEUE` + conntrack +
    `XT_MATCH_STRING` are all `y`. Capability is not the objection; cost is.
  - **Security is a trade, not a win:** a WAN-facing C parser running with `CAP_NET_ADMIN` turns a
    decoder bug into pre-auth RCE on the gateway; rule feeds re-introduce the phone-home the
    de-cloud gate exists to prevent; rulesets are a continuous third-party supply-chain input; and
    IPS false positives are an anti-lockout hazard. Image is ~74 MB — rules alone (30–80 MB) rule
    out shipping them.
  - **Recommended instead:** scope any inline inspection to narrow low-volume traffic (inbound to
    exposed ports, DNS) as an extension of the native firewall suite; prefer flow-*metadata* anomaly
    detection, which costs nothing because it reads the accelerator's own counters (as the Traffic
    Analyzer already does); and if a full IDS is wanted, document an **opt-in Entware/USB install**
    rather than shipping it.

  - **"Sentinel" flow-metadata page: BUILT then REMOVED on the same day — owner decision
    2026-08-12. DO NOT REBUILD.** A native page (`Reaper_Sentinel.asp`) was built under Traffic
    Analyzer showing per-host fan-out / port-sweep / uncommon-port / not-accelerated signals from
    the `reaper_conn.cgi` flow feed. It worked and cost nothing, but it was **rejected on
    presentation grounds, which the mockup made obvious**: it renders *inferred* signals with the
    visual authority of measured fact. A media box hitting many CDN edges was flagged `warn`
    identically to a device actually scanning the internet. Users cannot tell those apart from the
    output, so the page would teach people to mistrust normal traffic — or worse, to trust the
    verdict. **A confident-looking UI over heuristic data is a liability, not a feature.**
    - Fully reverted: page deleted, `reaper_inject.c` / `menuTree.js` / dashboard rail unwired, all
      22 `RSEN_` tokens removed from all 25 dicts (verified: zero mentions tree-wide, dicts back to
      6321 lines uniform, the three wiring files diff-clean against HEAD).
    - **The wider lesson applies to any successor:** flow metadata can say *what shape* traffic has,
      never *what it means*. Anything built on it must either present raw measurements without a
      verdict, or not ship.

  - **Not built, and now unlikely to be:** (i) narrow NFQUEUE inspection scoped to inbound/DNS —
    belongs with the native firewall suite, which is still mock-ups; (ii) DNS-layer controls, the
    one remaining direction with *true* data rather than inference (`dnsmasq` + Merlin's DNSFilter
    are already in-tree) though DoH/DoT increasingly bypasses it; (iii) an opt-in Entware/USB
    install note for users who want full Suricata — **unverified whether Entware even packages
    Suricata for aarch64**; check before documenting it. [researched — no build]

- **[P2] NATIVE FIREWALL SUITE — replace the stock Firewall menu with Reaper-native pages + add engineer features.**
  Owner-approved (2026-08-08) design: a native
  `Reaper_Firewall.asp` hub replacing all four stock tabs (General / Network Services / URL /
  Keyword) plus new tabs — **Status** (live v4+v6 chains + hit counters), **custom Rules** engine
  (Basic form + Advanced DSL, dual-stack, `rc/reaper_fw.c` + `reaper_fw.cgi`, re-apply hook),
  **Egress** control (IoT containment, outbound geo), **Logging** viewer — all with
  **commit-confirm auto-rollback** and anti-lockout invariants. Backend stays iptables/ipset.
  Phased 0→3; each phase build + on-metal (rmcpd lab MCP as the test harness) + fleet fan-out.

  - *Checked 2026-08-12 — **NOT shipped; still in planning**.* Files exist in the tree
    (`www/Reaper_Firewall.asp` 42 KB, tabs `general`/`netsvc`/`url`/`keyword`/`status`/`logging`;
    `rc/reaper_fw.c` 14.7 KB) and were committed under the v2.3.3 rung (`c2162344cc`), but these are
    **mock-ups from the design phase, not a working feature**. Nothing in any menu or nav file
    references `Reaper_Firewall`, so the page is unreachable in a running image — deliberately so.
    **Do not read presence in the source ladder as delivery.** Design approved, live inspection done,
    build not started. [owed — build]

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

- **[P2] "Current version" is stated inconsistently across docs, and nobody can tell which release
  actually shipped.** Found 2026-08-12 while updating docs for the v2.3.7 rung; deliberately **not**
  guessed at, because these are user-facing claims about which firmware exists.
  - `README.md` says *"Current version: **v2.3.1**"*; `docs/INSTALL-AND-ROLLBACK.md` says
    *"current release **v2.3.2**"*. They cannot both be right.
  - `provenance/manifest.json` is the only authoritative record and it says **v2.3.1 is the last
    release carrying image hashes (2)** — every rung from v2.3.2 through v2.3.7 has **zero images**.
    `cut_rung` writes each entry as source-only and image hashes are added when a build ships, so
    on that evidence nothing after v2.3.1 has shipped. That contradicts the working record, which
    has v2.3.2 published via CI and v2.3.3 built and metal-passed.
  - So either those builds shipped and the manifest was never refreshed with their hashes, or they
    did not ship. **Resolve against the actual GitHub Releases**, then fix both docs to match and
    decide whether "current version" means *newest published image* or *newest source rung* — the
    two have been six rungs apart and the docs do not say which they mean.
  - `docs/CI-PUBLIC-BUILD.md` also states a stale pin (`Reaper_v2.3.2 … patch series 0001–0378`);
    the pin is now `Reaper_v2.3.7` with 406 patches. Refresh once the above is settled.

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
