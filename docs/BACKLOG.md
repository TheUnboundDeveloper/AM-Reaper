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

- **[P2] Speed test: `level_err_cnt` is consumed once per POLL, not once per error — this is
  probably the real cause of a run dying mid-test.** Found 2026-08-16 while the owner pushed back
  on the v2.4.5 changelog entry claiming the counter-leak fix addressed hanging/erroring speed
  tests. It does not, and the entry was corrected.

  **Mechanism** (`internet_speed.html`). `process_speedTest_result()` runs on every poll —
  `setTimeout("get_speedTest_result();", 200)` keeps firing until a `type == "result"` entry
  appears (`get_next = false`, line ~517). Each pass re-reads the WHOLE buffer from
  `ookla_speedtest_get_result()` and tests `speedTest_result[speedTest_result.length - 2]`. If
  that entry has `level == "error"`, `level_err_cnt++`. **There is no index or dedupe** — if the
  buffer does not grow between polls, the SAME error entry is counted again 200 ms later. So
  `LEVEL_ERR_MAX = 50` is not a tolerance of 50 errors; it is **10 seconds of a stalled tail**
  (5/sec). A single persistent error at the end of the output ends the run.

  **Why this fits the reports better than the leak.** The v2.4.5 fix (`fb606fcc3b`) only explains
  *later* tests in a session failing sooner than earlier ones. It cannot explain the **first**
  test of a session dying mid-run, which is what "hangs partway through" usually describes. This
  can.

  **Fix shape:** count an error entry once — track the buffer length (or the entry's index) at
  which the last increment happened and only increment when it has moved. **The run stays bounded
  either way:** `get_speedTest_result()` already returns `error_handling(ERR_TIMEOUT)` once
  `get_result_time - test_start_time >= test_timeout`, so a genuinely stalled test still ends;
  this only stops a *stall* being reported as an *error* ten seconds in.

  **Owner decision 2026-08-16: deferred to v2.4.6.** Not done in v2.4.5 on purpose — it changes how
  a run is bounded, not just when a counter is cleared, and by the time it was found the rung was
  cut *and pushed*, so adding a patch would have put `patch_count` out of agreement with the
  published provenance entry. Deferring also buys the thing it actually needs: a **multi-run**
  on-metal session. One pass proves nothing here — the whole failure signature is "it depends how
  many tests you have run and whether the output stalls."

  **Related, same counter, lower priority:** `level_err_cnt` is cumulative across a run and resets
  only on completion (line ~574), never on progress. Even with per-entry counting, 50 scattered
  non-fatal errors over a long run would terminate a test that is succeeding. Consecutive-error
  semantics are the right shape.

- When I ping 8.8.8.8 or 1.1.1.1, I get a lot of request timeouts. This happens both right 
  after a firmware update and randomly throughout the day. The only solution is to reboot the 
  ONT, and the connection becomes stable again. What could be causing this? Thanks a lot. I’m 
  attaching a screenshot to prove it’s me.

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

  - **Instrumentation is compiled and shipped** — cut into the v2.3.7 rung as patch `0401`, and
    v2.3.7 published images on all five models, so it is in the field. It has still **never been
    exercised**, because that needs a failed search on a live mesh. Three
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

- **[P2] Wireless Quality Auto Scan pins the winner by itself; it should not.** Owner 2026-08-13:
  a scan should rank and report, and pinning should be the separate **Pin best** button
  (`scanpin` / `scanPin()`) that already exists. Today a clean sweep commits the winner without
  being asked.

  - **Where:** `web.c` ~22563-22575. On `!aborted && n > 0` the worker does
    `nvram_set(wlN_chanspec, r[order[0]].cs)` + `wlN_bw`, then `nvram_commit()` and
    `notify_rc("restart_wireless")`. Only an aborted/stopped sweep restores `orig_cs`/`orig_bw`.
  - **This reverses a deliberate v2.3.7 decision** ("winner auto-locked+committed"), so it is a
    change of mind, not an oversight — do not "fix" it back later without reading this.
  - **The source already contradicts itself about it.** `Reaper_Wireless.asp` ~480 states the worker
    "ranks them, and RESTORES the original channel. This page only polls results and, on the user's
    click, pins the winner." That is what the owner expects and what the button implies — but it is
    not what `web.c` does. Whichever way this is settled, **one of those two comments must change**;
    leaving both is how the next person loses an afternoon.
  - **Why it matters beyond preference:** pinning sets `wlN_chanspec` to a fixed value, and a radio
    only joins `acs_ifnames` while that is `"0"` — so an auto-pin silently turns **auto-channel
    selection off** for that radio until someone sets Control Channel back to Auto. A user who ran a
    scan just to *look* comes away with a changed, committed configuration.
  - **Verify while fixing — the two pin paths may not agree.** `scanPin()` applies
    `pinTarget(...)`, i.e. the wider block CONTAINING the winner, whereas the auto-pin applies
    `r[order[0]].cs` verbatim with `bw` derived from it. If the sweep samples narrower than the
    radio runs, the auto-pin could leave the radio at the swept width. The `scanPin()` comment says
    5 GHz is "swept at bw=20", but the v2.3.7 rework claims 5 GHz now sweeps 80 MHz blocks so
    "ranked==applied" — so that comment may simply be stale. Confirm which is true before trusting
    either.
  - **Fix shape:** take the `!aborted` branch out, i.e. always restore `orig_cs`/`orig_bw` after a
    sweep, and leave every pin to `scanPin()`. Then correct whichever comment is left lying.

- **[P2] Dual-WAN failover: both NextDNS profiles receive DNS logs though only one WAN is live.**
  Secondary WAN (2.5 Gbps, DHCP, its own NextDNS profile) is active; the future primary (10 Gbps,
  PPPoE) is not yet connected. With only the secondary live, **both** NextDNS profiles show traffic;
  expected only the active WAN's profile to log. [Requires_Research]

- **[P2] Field report: heavy ping loss to 8.8.8.8 / 1.1.1.1, cured only by rebooting the ONT.**
  Third-party report on v2.4.4, 2026-08-15: timeouts start right after a firmware update and also
  appear at random through the day; rebooting the **ONT** restores it. No configuration supplied.
  **Investigated from the code; not reproduced, no fix applied — the reporter's own strongest clue
  argues against our firmware.**

  **Warden CAN produce this symptom, but not this cure.** With `rwarden_dir=out|both`, a LAN
  device's echo request carries `dst=8.8.8.8`, and `RW_OUT`'s destination group drops it if that
  address is in `rw_threat` or any `rw_g_<cc>` set — 8.8.8.8 is US-registered and 1.1.1.1 sits in
  APNIC space, so a coarse country pick catches both. With `rwarden_self=1` the same applies to the
  router's own pings via `RW_SELF`. The inbound *reply* is not the failure mode: `REAPER_WARDEN`
  returns on `ESTABLISHED,RELATED` at slot 3, above the source drops.
  **But `rw_threat` and `rw_g_*` are created `-exist` and never flushed on re-apply** (only
  `rw_allow`/`rw_ban` are), so a WAN bounce does **not** clear Warden blocking. If Warden were the
  cause, rebooting the ONT would change nothing.

  **What does fit an ONT reboot,** in order:
  1. **ISP/ONT session state.** A firmware update reboots the router, which re-DHCPs while the OLT
     still holds the previous MAC-bound lease — a well-known GPON behaviour that presents as
     intermittent loss until the ONT is power-cycled. Fits both triggers and is not ours.
  2. **Hardware flow-accelerator wedge.** A link down/up flushes flow state, which an ONT reboot
     forces and a router reboot does not necessarily. We already have the detector for this
     signature — rwatch check 4, `/proc/gdx/skb_idx` pool exhausted — but it is **opt-in and default
     OFF** (`rwatch_gdx=1`). Worth asking the reporter to enable it; see [[accel-triage-surfaces]].

  **The one diagnostic that separates all three,** to request before doing anything else — during an
  outage: `iptables -nvxL RW_OUT RW_ODROP` (counters climbing ⇒ Warden), `ipset test rw_g_us
  8.8.8.8` (⇒ geo pick is the cause), `/proc/gdx/skb_idx` (0 available ⇒ accelerator), and whether
  loss is also seen from the router's own shell (⇒ upstream, not forwarding).
  **The v2.4.5 `RW_ODROP` change makes this materially easier:** an outbound Warden drop now logs
  `REAPER-WARDEN-OUT` instead of being indistinguishable from an inbound one, so `grep` answers the
  first question outright.

## UI / UX polish

- **[P3] Dashboard linking — rows that land on the wrong page.** The Security Posture panel became
  clickable in v2.4.1 (all fourteen rows carry a destination). Corrections as they are found:

  - **Wi-Fi Encryption should go to `/reaper_shell.asp#SDN.asp`** (owner, 2026-08-14). It currently
    carries `data-go="Advanced_Wireless_Content.asp"` (`Main_ReaperDash.asp` ~489), which is the
    stock per-radio Wireless page. On this MULTILAN_MWL build that is the wrong place to send
    someone: the user's main SSID and its security live in the **SDN MAINFH profile**, which is what
    the Network section of the menu already points at (standing rules 4 and 6). The row *reads* the
    right thing — `wlX_auth_mode_x` at radio level is correct, and that is what `encInfo()` reports —
    it just offers a page that cannot change it.
    - **Fix is one token, and do NOT paste the full URL in.** The click handler
      (`Main_ReaperDash.asp` ~1447) already does `location.href = '/reaper_shell.asp#' + p`, so the
      value must be the bare page name: `data-go="SDN.asp"`. Writing the whole path would produce
      `/reaper_shell.asp#/reaper_shell.asp#SDN.asp`.
    - **Check the fan-out before shipping it.** `SDN.asp` is not in base `www/` — it ships from the
      `sysdep/FUNCTION/SDN` overlay, and the menu reaches it conditionally:
      `isSupport("mtlancfg") ? "SDN.asp" : "Guest_network.asp"` (`menuTrees/menuTree.js:63`). A
      hardcoded `SDN.asp` dead-ends on any model or build where `mtlancfg` is not supported, and the
      dashboard rail is shared across all five models. Mirror the menu's conditional rather than
      hardcoding, or confirm every shipped model asserts `mtlancfg`.

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

- **[P2] Flash overlay: hide the poll heartbeat, and remove the Close button while an install is
  running.** Owner, 2026-08-14, seen live while flashing v2.4.2. The overlay reads
  `0:58 &middot; pollUpBack &middot; 3` and offers a **CLOSE** button beneath it. Three changes wanted:

  - **`pollUpBack` must not be on screen.** It is the literal name of the internal polling function,
    passed to `veilBeat('pollUpBack')` and rendered by `veilTick()` into `#veilTick` as
    `mm:ss · <phase> · <pollcount>` (`Reaper_Firmware.asp` ~470). It reads as a leaked debug string.
  - **The poll count must go with it.** Same line, `veilPolls`.
  - **No Close button during an install, and the overlay must persist until the poll succeeds.**
    Today `#veilAct` is revealed unconditionally by a timer — `VEIL_ESCAPE_MS = 25000` (~line 462) —
    so it appears about 25 s in whether or not the flash is progressing normally, which is why it is
    on screen at 0:58. `veilDismiss()` only removes the overlay; it cannot stop a flash already
    running, so dismissing it mid-flash leaves a user looking at a live page while the router is
    mid-write.

  **This reverses a deliberate v2.3.2 decision — read this before putting it back.** The Close
  button, Esc handler and the heartbeat were added *together* in v2.3.2 so that "a stalled flash can
  no longer look like a frozen browser". The reason they were needed has since been removed: the tab
  was not stalling, it was **locking up**, because every failed poll round scheduled two successors
  and the chain doubled every two seconds until the tab died (standing rule 34, fixed in
  `a0c115dc45` — the changelog for that release says outright that "v2.3.2's Close button treated the
  symptom; this is the cause"). With the cause fixed, the escape hatch is now mostly a way to
  dismiss a *working* flash. That is the justification for removing it, and it is why this is a
  change of mind rather than an oversight.

  **Decide while implementing — do not silently drop it:** `veilFail()` reveals the same button on a
  *terminal* state (a flash that genuinely failed, a rejected image). Removing the button everywhere
  would trap the user on a dead overlay with no way back. The ask is specifically about the install
  path, so the likely shape is: no timer-based reveal at all, no button while polling, and the
  button still offered on terminal failure — plus keeping the elapsed `mm:ss`, which is the part of
  the heartbeat that is useful to a person rather than to a developer. The Esc handler
  (~line 500) is gated on the button being visible and follows it automatically.

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

## Features to add

- **[P2] [owed] Metal-validate the v2.4.4 IPv6 per-device attribution on a box that actually has
  IPv6.** The maintainer's RT-BE96U runs `wan_proto=dhcp` with no IPv6 up, so it cannot exercise the
  new path at all — which is precisely why the gap survived to a field report. The reporting
  **RT-BE88U** has native IPv6 with a delegated /56 and is the natural test box. What to check with a
  large download running: the device's row tracks the WAN line rather than showing only its ACK
  stream; a dual-stack device stays **one** row rather than splitting; and the neighbour table the
  collector reads (`nd_n`) agrees with `ip -6 neigh show dev br0`. The netlink reader was tested
  against seeded bridge and non-bridge neighbours on the host, and the code cross-compiles with zero
  new warnings, but neither proves behaviour on real traffic.

- **[P3] A v6-only device shows a blank address label (v2.4.4).** Attribution is keyed on the
  hardware address, so such a device is counted correctly and merges properly — only the display
  label is empty until the network map names it. `cli_t.ip` is a 16-byte IPv4 field living inside the
  persisted `dbhdr_t`, so widening it to hold a v6 literal would change the on-disk layout and
  discard every saved history file (the `DB_VER` 1→2 precedent). Options if it ever matters: show the
  hardware address as the fallback label, or carry a separate display field outside the persisted
  header. Not worth a history-invalidating format bump on its own.

- **Warden Plus** Requests have been made for custom feeds input by the user.

- **[P3] Warden: decide whether country rules should be evaluated BEFORE the threat feeds.**
  Left as an explicit owner decision by the 2026-08-14 block-count work, not an oversight. Both rule
  families jump to the same drop target, so the order is purely **attribution** — it changes which
  counter increments, never whether a packet is dropped. Today the feed rule runs first, and because
  the large feeds overlap heavily with the countries people block, the feed absorbs the hit and the
  per-country counters barely move; that is the whole reason the total and the country table looked
  unrelated. Putting geo first would give real country attribution at zero enforcement cost.
  **Why it was not just done:** it silently changes the meaning of a statistic users have been
  accumulating — banked country counts would suddenly grow much faster and the feed count would
  flatten, with no way to explain the discontinuity after the fact. The breakdown shipped in the
  unreleased rung makes both numbers visible, so this is now a free choice rather than a fix.

- **[P3] Firewall rule tracer (FIREWALL-PLAN Phase 3, the last unbuilt piece of it).** "Given a
  packet like *this*, which rule would match?" — a simulator that walks the committed config in C
  and reports the first match, rather than shelling out to iptables. Deferred from the firewall rung as
  the cheapest thing to leave: it is a diagnostic aid, not a control, so nothing is unusable without it.
  Everything else in Phases 2 and 3 shipped in v2.4.1 (`a103b59d6d` engine, `fa1e5d634f` Egress and
  Forwards tabs + backup/restore).

- **[P2] NATIVE FIREWALL SUITE — the remaining pieces.** The suite itself **shipped in v2.4.1**
  (engine, hub, Status posture view, Phase 2 egress defaults, Phase 3 hardened forwards, their
  authoring tabs, backup/restore, and a measured engine-active signal); see
  [`CHANGELOG.md`](CHANGELOG.md). What is left:

  - **Advanced DSL for the Rules tab** — the approved 2026-08-08 design called for a Basic form
    *and* an advanced text syntax; only the Basic form was built (`grep -ci 'dsl\|advanced'` on
    `Reaper_Firewall.asp` = 0). Decide whether it is still wanted: the Basic form plus the compile
    preview may already cover the need the DSL was meant to serve.
    *(The Logging viewer tab from that design IS built — `tab_logging` + `loadDrops()` + the `fw_log`
    CGI path — so do not re-raise it as missing.)*
  - **Fleet fan-out — BLOCKED until the overlays are regenerated.** The rung touches
    `www/Main_ReaperDash.asp` and `www/reaper_shell.asp`, which all four per-model overlays also
    carry, so `RT-BE86U` / `RT-BE88U` / `GT-BE98` / `GT-BE98_PRO` cannot take this series until those
    overlays are rebuilt against it. Everything else in the rung is model-neutral.
  - The rule tracer is tracked as its own entry above. *(The dnsmasq `ipset=` upgrade is no longer
    listed here — it was implemented 2026-08-14 and is in the unreleased rung; the "dnsmasq is
    compiled without ipset" blocker this file used to record was a misreading and must not be
    re-raised. See [`CHANGELOG.md`](CHANGELOG.md).)*

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

- **[P2] [owed] The whole `RFW_*` namespace — the entire firewall page, 244 keys — has never had a
  translation pass.** Measured 2026-08-16 across the 24 non-EN packs: 306 Reaper-minted keys still
  carry the English string, and **244 of them are this one page**. Every other Reaper namespace is
  in single digits or zero. The firewall shipped in v2.4.1 and the pass never followed.

  **This is why `RFW_252` ("Both") was minted English in v2.4.5 and deliberately left untranslated.**
  It is one option of the logged-packets selector, whose other three options (`RFW_100` None,
  `RFW_138` Accept, `RFW_139` Drop) are English in every pack. Translating one option alone renders
  *"None / Drop / Accept / Beide"* — worse than a consistently English set. Do this namespace as one
  job, not piecemeal.

  **Do not "fix" it by reusing ASUS's `option_both_direction`.** It is translated 24/24 and its
  English is exactly "Both", which makes it look ideal — but it means *bidirectional* (CN renders it
  `双向`), and this selector is a logged-packets **type**, not a direction. Checked and rejected
  2026-08-16.

  Constraints when the pass happens: `RFW_229` is used as an HTML attribute value (`title` /
  `aria-label`), so its translations must not contain a double quote; see also the two `RFW_36`/
  `RFW_37` single-quote contexts below.

- **[P3] Translations owed for the 2026-08-14 rung — Warden's router-self filter.** `RWDN_69`–
  `RWDN_72` (toggle label, description, and the two-part risk warning) are English-seeded in all 25
  packs. The packs stay in lockstep so nothing renders as a raw `<#KEY#>`; the non-English packs
  simply carry the English text until translated. *(`RWDN_73`–`RWDN_76`, the block-count breakdown
  labels, were translated in v2.4.5 when the breakdown became a visible strip.)*

- **[P3] Two pre-existing rule-29 single-quote contexts on `Reaper_Firewall.asp`.** `RFW_36`
  ("Time") and `RFW_37` ("Action") are interpolated into a single-quoted JavaScript string in the
  log-table header builder. **Latent only** — every pack still carries the untranslated English, so
  nothing breaks today — but the standing rule exists because a translation containing an apostrophe
  turns this into a syntax error for that language alone, which is how the v1.8.6a EU breakage
  happened. Convert both to backticks next time that code is touched. Verified 2026-08-14 that the
  per-tab help work introduced no new such contexts; these two predate it.

- **[P3] `do_reaper_dev_cgi` function-local `static` snapshot arrays aren't re-entrant.** Latent only
  (httpd serialises these requests); a malloc refactor of the multi-return CGI would add leak risk to
  fix a can't-happen case. [shelved]

## Documentation

- **[P1] `Reaper_Firewall.asp` IPv6 protocol select cannot be safely tokenized as-is — and must not
  be.** Found by the 2026-08-15 i18n audit. Line 243:

  ```html
  <select id="v6_proto"><option>TCP</option><option>UDP</option>
                        <option>BOTH</option><option>OTHER</option></select>
  ```

  Those `<option>` elements carry **no `value=` attribute**, so the visible text *is* the submitted
  value — and line 1129 reads it straight back with `$('v6_proto').value`. Wrapping `BOTH`/`OTHER`
  in dict tokens, which is the obvious "make it translatable" fix, would submit the **translated**
  string to the firewall backend: a German user would send `Beide` where the rule format expects
  `BOTH`. That is a functional break in 24 languages, produced by an i18n change, with nothing in
  the build to catch it.

  **Correct fix, in this order:** confirm the literals the backend actually expects, add explicit
  `value="TCP|UDP|BOTH|OTHER"` attributes so the wire format is pinned independently of the label,
  *then* tokenize the labels (`RFW_252` already exists for "Both"; "Other" still needs a key).
  Marked P1 not because it is broken today — it is not, English submits correctly — but because the
  obvious fix breaks it, so the trap needs to be written down before someone tidies the page.

- **[P3] [owed] One remaining hardcoded UI string needs a new key.** The 2026-08-15 audit scanned
  all 19 Reaper pages for user-visible text without a `<#TOKEN#>`. **Four of the five findings are
  now fixed** (see `CHANGELOG` when the rung is cut): `Drop`/`Accept` on the two firewall log-level
  selects reuse `RFW_139`/`RFW_138`; `QoS Diagnostics` reuses `RQD_00`, which already carried that
  exact wording and brings the page in line with every other Reaper `<title>`; the shell's brand
  link and content-iframe titles reuse `Reaper_c_dashboard` and `Settings`. Only **`RFW_252=Both`**
  had to be minted, and it is appended to all 25 packs (lockstep 6585 → 6586, key order verified
  identical across every pack).

  **Still owed:** a key for `OTHER` on the IPv6 protocol select — blocked behind the P1 above, since
  tokenizing that select before pinning its `value=` attributes is the thing that breaks it.

  **`option_both_direction` was rejected as the reuse for "Both" and must stay rejected:** its
  EN/DE/FR/ES/IT/RU values are a generic "both", but **JP `双方向`, CN `双向`, TW `雙向` all mean
  *bidirectional*** — right for a direction picker, wrong for "log both drops and accepts".

  *Deliberately left literal, verified during the same audit so they are not re-raised:* the Splunk
  index/sourcetype placeholders, the Diag sanitization-ledger preview (it mirrors the English `.txt`
  artifact), the Broadcom counter names on the Wireless page (`nopkt`, `txop`, `glitch`, `chspec`,
  `obss`, `doze`, `knoise`), the firewall schedule placeholders (`Mon,Tue|09:00|17:00` is *parsed*,
  so translating it would break the field), third-party product names, and `title="hidden"` on three
  `display:none` iframes. `Reaper_Devices.asp`'s `title="' + esc(T('RDEV_xx')) + '"` attributes are
  already tokenized through a `T()` helper.

- **[P2] [owed] Retranslate the three Traffic Analyzer accounting strings (v2.4.4).** `RTRF_45`
  (where the per-device numbers come from) was rewritten in all 25 packs and its 24 non-English
  translations were **deliberately discarded**: the old text said the numbers come from the
  accelerator table (untrue since v2.3.3) and that IPv6 is "not yet split per-device" (now the
  opposite of what the code does), so leaving the translations would have had 24 languages
  asserting the reverse of the truth. `RTRF_75` / `RTRF_76` (the "Upload only" badge and its
  tooltip) are new and English-seeded. All three read in English outside EN until a translation
  pass. Precedent for why this matters: the DE.dict `RQOS_117` drift left non-English users
  double-derating their download cap.

- **[P3] Make `cut_rung` own the version/count restatements, so doc drift cannot recur.**
  *(All the corrections from the 2026-08-12/13/14 drift sweeps are DONE — `README.md`,
  `INSTALL-AND-ROLLBACK.md`, `CI-PUBLIC-BUILD.md`, `RELEASE-NOTES.md`, `patches/README.md` and the
  `public-build.yml` pin comment. Only the automation below is left.)*

  Every doc that restates a version or a count is a copy that can rot, and `cut_rung` already knows
  the true values at cut time. Candidates it could own outright: the `patches/README.md` header
  count, the `docs/CI-PUBLIC-BUILD.md` pin row, and the `RELEASE-NOTES.md` "current head" line —
  plus writing image hashes into `provenance/manifest.json` on publish.

  **Two findings from those sweeps that must not be re-derived:**
  - **`provenance/manifest.json` is NOT a "did it ship" signal.** Image hashes are populated only
    for v2.1.0–v2.1.5 and v2.3.1; every v2.0.x and v1.x rung is zero too, *including ones known to
    have shipped*. Reading absence of a sporadically-populated field as evidence of non-release is
    what produced a day of contradiction. The authoritative record is the GitHub Releases API.
  - **"Current version" means the newest PUBLISHED release** — the newest image a user can download
    — as distinct from "current head", the newest source rung. Both are now stated explicitly, each
    in exactly one place, because leaving it to inference is what let them drift apart.
  - **Automation would not have caught the worst instance.** The 2026-08-14 round found that
    `CHANGELOG.md` and `RELEASE-NOTES.md` both carried a *technical justification that was false* —
    that this router's dnsmasq is compiled without ipset support, which it never was. A version
    number is mechanical and can be generated; a reason is written by hand and can only be caught by
    someone re-deriving it.

- **[P3] Decide whether two internal docs should be published here.** `GUESTPRO-2.5G-VLAN-PLAN.md`
  and `CODE-AUDIT-2026-08-05.md` live in the private working tree and were referenced by dead links
  from this file and `CHANGELOG.md` (found 2026-08-13 by a 211-link sweep; those were the only two
  broken). **The links are already removed** and the prose names the docs as unpublished — so
  nothing 404s today. What remains is the owner call: copy them in, or leave as-is. Neither has been
  through a PII/scope review, which is why this is a decision rather than a cleanup.

- **[P3]** Document the non-functional retained features (the firmware update-check UI's stock pieces,
  the removed security-check UI) that are kept only for potential future use.
- **[P3]** Annotate the system defaults.
- **[P3]** Write a user guide for other users. *(Started 2026-08-14:
  [`FIREWALL-GUIDE.md`](FIREWALL-GUIDE.md) covers the eleven firewall tabs — what each is for, how
  best to use it, worked examples, and the non-obvious traps — and every tab's **?** button links to
  its section. The guide is tracked and pushed, so those links now resolve; the "404 until pushed"
  caveat that used to sit here is stale and has been removed. Extended 2026-08-15 with the
  allowlist recipe — "allow only these destinations, block everything else" — after a field request
  for rule negation turned out to be a documentation gap rather than a missing feature. The same
  treatment is owed for Warden, Gatekeeper, QoS, Traffic and the Devices pages.)*

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
  investigation: `GUESTPRO-2.5G-VLAN-PLAN.md` — **not published in this repo**; it lives in the private
  working tree. (Was a link here, which was dead for every public reader.) [blocked — blob; risk-accepted]

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report does not get re-investigated from scratch, and so the
reasoning survives the person who made the call.*

- **`rwatch: FAILURE detected: warden-self-drop:<n>` is the feature reporting, not a fault.**
  Reported from the field on v2.4.4 (2026-08-14), with a large BCM/BPM kernel dump attached.

  `warden-self-drop` fires only when `rwarden_self=1` — the **opt-in** router-origin filter
  (`RW_SELF` on OUTPUT, drops to `RW_SDROP`). `<n>` is the number of the router's own outbound
  packets dropped since the previous rwatch tick. `rc/rwatch.c` classifies it **FAIL rather than
  CRIT on purpose**, and the in-code comment says why: *"dropping a flagged destination is the
  feature working, and only the operator can say which it is."*

  It is reported at all because the failure mode is silent — feed refresh, DDNS or a VPN client
  simply stop, and nobody watches OUTPUT counters. An alert that occasionally says "this is
  working" is the price of not discovering a mute router weeks later.

  **The BPM kernel dump is not part of the fault.** It is rwatch's bounded first-failure
  diagnostic collection (kept to 3, written to `/jffs/rwatch`). In the reported instance the pool
  was healthy — `no_buf_err = 0`, `skb_fail_cnt = 0`, `buf_exp_fail_count = 0`, 1493 buffers
  available — so it carried no signal. Same misreading risk as the `blog_get_dstentry_by_id`
  debug flood: a scary-looking Broadcom dump next to an unrelated event.

  **To act on one:** `RW_SDROP` always logs regardless of `rwarden_log`, so
  `grep REAPER-WARDEN-SELF` in syslog names the destination. dnsmasq's upstream resolvers and NTP
  are already carved out, so a hit is usually a feed host, DDNS endpoint, or a VPN peer that has
  landed in a geo or threat set. Turning `rwarden_self` off stops both the filtering and the alert.

  *Possible future UX work, not a fix: the alert could name the top destination inline so the
  operator does not have to go to syslog to triage it.*

- **Firewall rule negation / "not" on source and destination — considered, not building.**
  Field request on v2.4.4 (2026-08-15): negate a rule's source or destination.

  **The engine already does what it was wanted for.** An empty source or destination means "any"
  (`rfw_emit_rule`: an empty field matches anything, while a *named* object resolving to nothing
  emits no rule at all — fail-closed to a missing rule, never an unrestricted one). So an allowlist
  is an ordered pair, `Accept` to the allowed object above `Drop` with the field left empty. Two
  further layers exist for posture — per-device Egress defaults and Zone policy — with a fixed
  precedence: *explicit rule > Egress default > Zone policy*. Documented with a worked example in
  [`FIREWALL-GUIDE.md`](FIREWALL-GUIDE.md) §Rules as a result of this request; the gap was the guide,
  not the engine.

  **Two reasons not to add it anyway.** First, negation does not distribute over the engine's
  (src set × dst set) expansion — `NOT in (A ∪ B)` is not `(NOT in A) OR (NOT in B)`, and the second
  form matches almost everything — so any negated object resolving to more than one set (a group, or
  anything dual-stack) would silently mean far more than asked. Second, and the larger cost: it would
  add a *second, overlapping* way to express default-deny, per-rule and less visible than the two
  layers designed for it, making a ruleset materially harder to audit later.

  **The narrow case it would genuinely serve**, if it is ever asked for specifically: a single rule
  needing "everything except X" as one condition, where the ordered-pair form would mean placing two
  rules carefully among many others — e.g. "drop SSH to anywhere except the jump host". If that
  request arrives, the implementation gate is: single-set objects only, groups refused loudly, and
  the inverted match spelled out in plain language in Preview before commit.

  - **[P2] `/tmp` is `0777` with NO sticky bit — it turns any unprivileged foothold into root.**
  Found 2026-08-14 by the v2.4.2 security audit, which kept arriving at it from three unrelated
  directions. `rc/init.c:25601` does `chmod("/tmp", 0777)` and nothing anywhere in `rc/` or
  `shared/` ever sets `S_ISVTX` (grepped). The sticky bit is what normally stops one uid from
  unlinking or renaming another's entry in a shared directory; without it, **any non-root process
  can delete a root-owned file in `/tmp` and recreate it with its own content**, or substitute a
  whole directory before root creates it.

  This is stock ASUS/Merlin behaviour, not a Reaper regression — which is exactly why it is easy to
  keep walking past. Three live consumers found in one afternoon:
  - `httpd` (root) parses `/tmp/allwclientlist.json` and `/tmp/wiredclientlist.json` on a
    **CSRF-exempt** endpoint (`reaper_dev.cgi?action=status`). The v2.4.2 fix hardened the parser
    against a hostile document, but the write primitive is still there.
  - `rc` writes and then executes `/tmp/rwarden/{apply,fold,stats}.sh` **as root**, on a cron tick
    and on every UI poll. `mkdir(RW_DIR, 0700)` ignores `EEXIST` and never checks owner or mode, so
    a directory pre-created by another uid is used as-is.
  - `reaper_fw` has the same unchecked `mkdir` for `/tmp/reaper_fw`, and on a default box that
    directory does not exist until the firewall engine is first enabled — a wide pre-creation
    window. Its `dnsmasq.ipset` fragment is spliced into a **root-parsed** config.

  **Reachability today is LATENT**, and that is the only reason this is not P1: nearly everything on
  this firmware runs as root. The privilege-dropping services found were dnsmasq (`user=nobody`) and
  `in.tftpd -u nobody`, plus any jffs/Entware addon that drops privilege. So it needs a prior
  non-root code-execution bug — but it converts one into root across several subsystems at once.

  **Deferred deliberately, not overlooked:** setting the sticky bit changes behaviour for every
  program on the box, including closed ASUS blobs that may rely on cross-uid unlink in `/tmp`. It
  deserves its own rung and its own on-hardware pass rather than riding a feature release. Two
  candidate shapes: (a) `chmod("/tmp", 01777)` in `init.c` — one line, broad blast radius; or
  (b) leave `/tmp` alone and move the root-executed scratch to a root-only parent
  (`/var/run/rwarden`, `/var/run/reaper_fw`), plus `lstat` the directory and refuse it if it is not
  a root-owned `0700`, and open scratch files `O_CREAT|O_EXCL|O_NOFOLLOW`. (b) is narrower and
  fixes the cases we actually own; (a) fixes the class. Doing (b) first is the safer order.
