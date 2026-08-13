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

- **[P3] Wi-Fi Professional: ~15 s first load after a firmware upgrade, fast on every load after.**
  Reported on metal 2026-08-13 (v2.3.9). Only the FIRST load following an upgrade is slow; once it
  has been pulled once the page is responsive, so this is a cold-state cost, not steady-state.

  - **Note the history before re-investigating:** the known slow-first-load cause was found and
    fixed for v2.3.7 (patches 0401/0404) — 116 server-side `nvram_get` calls collapsed into a single
    `wl_ifnames`-driven ej call. That fix IS in this build, and its timing was never measured on
    metal ("UNCOMPILED, timing unmeasured"). So this is either a residual second cause or evidence
    the collapse did not deliver what it promised. Do not re-find the nvram_get issue and call it
    solved.
  - **Most likely candidate is not the page at all:** an upgrade ends in a reboot, and the Pro page
    makes per-radio driver calls (`wl`) while the wireless stack is still settling — ACS/DFS
    selection on 5 GHz/6 GHz can block ioctls for tens of seconds after boot. That would explain
    "first load only" precisely, and would mean the page is a victim rather than the cause.
  - **Cheap way to separate the two:** load the page ~10 minutes after a reboot with no other
    change. Still slow → it is a genuine cold-cache/first-generation cost in the page. Fast → it is
    boot-time driver settling, and the fix is to show a loading state rather than to optimise
    anything. Timing `curl -o /dev/null -w '%{time_total}'` against the ASP separates server-side ej
    time from browser-side rendering.

- **[P2] Firewall engine master switch takes no action — most importantly it does not turn OFF.**
  Found on metal 2026-08-13 (v2.3.9, first time the engine ever ran). `reaper_fw.cgi?action=opts`
  is what the page's engine toggle calls (`Reaper_Firewall.asp` ~1148); it does
  `nvram_set("reaper_fw_enable", en)` and returns. There is no `notify_rc`, so nothing starts or
  stops.

  - **The OFF direction is the real bug.** `stop_reaper_fw()` is never reached, so disabling the
    engine leaves REAPER_FWI/FWF/FWO hooked and enforcing until a reboot or an unrelated apply. A
    master switch that does not disable is the wrong failure direction for a firewall.
  - The ON direction is merely confusing: the flag is set, no chains appear, and the engine looks
    broken. That is exactly how this was found — `reaper_fw_enable=1` + `service restart_firewall`
    produced `iptables: No chain/target/match by that name`. The re-apply hook in `firewall.c` only
    *runs* `/tmp/reaper_fw/apply.sh` **if it already exists**; it never generates it. `apply.sh` is
    written by `start_reaper_fw()`, and `/tmp` is tmpfs — so after a reboot with the engine
    disabled, nothing has ever written it and `restart_firewall` has nothing to run. The working
    verb is `service restart_reaper_fw`.
  - **Also check while fixing:** `opts` uses `nvram_set` with no `nvram_commit`, so a toggle that is
    never followed by an Apply/Confirm is lost on a power cut. That may be deliberate (the
    commit-confirm design deliberately holds the six editable lists in RAM and commits only on
    confirm) but `enable`/`confirm` are settings rather than staged drafts, so confirm the intent
    rather than assuming.
  - **FIXED in v2.4.0 (`b3589185e6`) — metal re-test owed.** `opts` now calls
    `notify_rc("restart_reaper_fw")`, but only when `enable` actually CHANGES value — the same
    action saves the commit-confirm timer, and rebuilding the ruleset every time that number is
    edited would be pointless work. **Deliberately still no `nvram_commit()`**: that call flushes
    the whole of nvram and would persist the six editable lists while they are an unconfirmed draft
    in RAM, which is exactly what S3 forbids. The flag persists on the next confirm, the only path
    meant to write flash — so the open question in the bullet above is now answered: the missing
    commit is correct, not an oversight.
  - **Re-test both directions on metal:** enable → chains appear without a reboot; disable → chains
    are gone (`iptables -S REAPER_FWF` returns "No chain/target/match by that name"). The OFF
    direction is the one that mattered.

- **[P3] Firmware flash overlay does not lock the page behind it.** Reported on metal 2026-08-13
  (v2.3.8, flashing v2.3.9). While the "Uploading image" curtain is up on `Reaper_Firmware.asp`, the
  page underneath is still scrollable, so the sticky header slides out from behind the dim layer:
  the screenshot shows the VARIANT / AI Advisor / MCP chips, "INSTALLED VERSION Reaper v2.3.8" and
  "BASE BUILD 3.0.0.6.102.8" rendering *over* the faded header, on top of the curtain. Cosmetic —
  the flash itself completed normally — but it appears during the one operation where the page also
  says "DO NOT POWER OFF OR RESTART THE ROUTER", so anything that looks like the UI misbehaving is
  worth more than its severity suggests.

  - **FIXED in v2.4.0 (`b3589185e6` + `49d61be6df`) — metal re-test owed. The cause was NOT what
    this entry first recorded**, and the owner's original description was the accurate one: the page
    behind the header comes forward over it. `.top` is `position:sticky; top:0; z-index:300` with an
    **opaque** `background:#040405`, and `#page_frame` is `scrolling="no"` — so the shell scrolls
    while the header stays put and page content slides underneath it, which is normal and invisible.
    But `shellChromeLock()` dimmed the header with **`opacity:.45`**, and opacity does not merely
    fade an element, it makes it **translucent** — so the content passing beneath showed straight
    *through* it. The header never moved and never lost a stacking contest; it just stopped being
    opaque at exactly the moment content was underneath.
    Fixed with `filter:brightness(.45)`, which dims identically while leaving the element fully
    opaque (any inline `opacity` is cleared on the same line so an upgraded image cannot keep a
    stale value). A scroll freeze is kept as a second line of defence and now scrolls to the top
    before locking: with nothing under the header there is nothing to bleed through even if a future
    style reintroduces translucency, and it puts the veil's message in view rather than leaving the
    operator parked halfway down a page that has stopped responding.
    **Lesson worth keeping: `opacity` to "dim" any element that overlaps scrolling content will do
    this again. Use `filter:brightness()` for chrome that must stay opaque.**
  - **Still verify carefully — this area has a regression history.** The overlays were re-anchored
    in v2.3.3 (`1d9d58a2be` fixed a field regression where the re-anchor inflated the framed doc by
    460 px and clipped QoS/Traffic), and the post-flash "frozen browser" trap on this same page was
    doubled poll chains rather than the veil itself. Re-test in both the framed (shell) and
    direct-URL cases.

## UI / UX polish

- **Quick List** Items int he "Security Posture" panel on the dashboard should be linked so when 
  clicked it takes the user to the page and view of where the item can be modified.

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

- **[P3] Devices page — export the client inventory (name, MAC, IP) as HTML, CSV or JSON.** Owner
  request 2026-08-13. A button on `Reaper_Devices.asp` that offers the three formats and downloads
  the current device list.

  - **Should need no C at all.** `reaper_dev.cgi?action=status` already returns the full list the
    table renders from, so the data is in the browser; build the file client-side (`Blob` +
    `<a download>`) rather than adding a server endpoint. There is no outbound file-serving path in
    httpd to reuse anyway — every `Content-Disposition` hit in `web.c` is *inbound* multipart upload
    parsing — and `reaper_dev.cgi*` is registered in `mime_handlers[]` as `application/json`, so a
    server-side download would mean a new handler and a new mime row for no benefit. Same
    conclusion the Mesh Nodes card reached.
  - **Name source is `custom_clientlist`**, which is the naming master (see the Device Identity
    Manager work) — export what the user actually sees on the page, not the raw DHCP hostname, or
    the file will disagree with the UI for every renamed device.
  - Suggested shapes: CSV with a header row (`name,mac,ip`) for spreadsheets; JSON as an array of
    objects for scripting; HTML as a standalone styled table for handing to someone. Include the
    router model and a generated-at timestamp in the HTML and JSON headers so an old file is
    identifiable later.
  - **PII note — say it in the UI.** Unlike `reaper_diag`, which sanitizes and carries a
    withheld-items ledger precisely because raw dumps are unsafe to post, this export is
    deliberately UNsanitized: it is the user's own inventory and its whole purpose is real names and
    addresses. It is therefore not safe to paste into a forum or a bug report. A one-line caution
    next to the button costs nothing and prevents the obvious mistake.

- **[P3] Firewall rule tracer (FIREWALL-PLAN Phase 3, the last unbuilt piece of it).** "Given a
  packet like *this*, which rule would match?" — a simulator that walks the committed config in C
  and reports the first match, rather than shelling out to iptables. Deferred from v2.4.0 as the
  cheapest thing to leave: it is a diagnostic aid, not a control, so nothing is unusable without it.
  Everything else in Phases 2 and 3 shipped in v2.4.0 (`a103b59d6d` engine, `fa1e5d634f` Egress and
  Forwards tabs + backup/restore).

- **[P3] dnsmasq `ipset=` for FQDN objects (FIREWALL-PLAN Phase 2 upgrade) — BLOCKED, and not for
  the reason the plan recorded.** The plan assumed the obstacle was that `/etc/dnsmasq.conf` is
  regenerated wholesale on every `restart_dnsmasq` with `dnsmasq.postconf` belonging to the
  operator. That part is surmountable: `rc` owns the generator and can emit its own lines just
  before `append_custom_config("dnsmasq.conf", fp)` (services.c ~2353), without touching the
  operator's hook at all.

  - **The real blocker: this dnsmasq is compiled WITHOUT ipset support.** `dnsmasq/src/config.h`
    defines *both* `HAVE_IPSET` and `NO_IPSET`, and resolves it at ~line 365 as
    `#if defined(NO_IPSET) → #undef HAVE_IPSET`. The shipped binary contains no `ipset` option
    string at all, so emitting `ipset=` lines today would just make dnsmasq reject its own config.
  - Enabling it means rebuilding dnsmasq with `HAVE_IPSET` — a change to the most critical service
    on the box, so it wants its own rung and its own metal pass rather than riding someone else's.
  - Until then FQDN objects resolve on the 10-minute `cru` timer (`rfw_gen_resolve()`), which is the
    documented trade-off: a host behind a large rotating CDN pool lags until the next refresh.

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
