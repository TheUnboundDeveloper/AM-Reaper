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

- **[P3] Translations owed for the 2026-08-14 rung (27 keys, English-seeded in all 25 packs).**
  `RWDN_69`–`RWDN_72` (Warden's router-self filter: toggle label, description, and the two-part
  risk warning), `RWDN_73`–`RWDN_76` (the block-count breakdown labels), and `RFW_229`–`RFW_251`
  (the firewall page's per-tab explainers, examples, and the help-button label). The packs are in
  lockstep at 6583 lines so nothing renders as a raw `<#KEY#>`; the non-English packs simply carry
  the English text until translated. **`RFW_229` is used as an HTML attribute value** (`title` /
  `aria-label`), so its translations must not contain a double quote.

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
  - **RESOLVED 2026-08-13 against the GitHub Releases API — the builds DID ship and the manifest was
    simply never refreshed.** Published releases, all five models with 3 assets each: **v2.3.0,
    v2.3.1, v2.3.2, v2.3.4, v2.3.7**. Newest published is **v2.3.7** (2026-08-13). v2.3.3, v2.3.5 and
    v2.3.6 are source rungs that were never published, which is why the two numbers drift.
  - **`provenance/manifest.json` is NOT a reliable "did it ship" signal — do not use it as one.**
    Image hashes are populated only for v2.1.0–v2.1.5 and v2.3.1; **every** v2.0.x and v1.x rung is
    zero too, including ones known to have shipped. Reading absence of a sporadically-populated
    field as evidence of non-release is what produced the contradiction above. Either populate it on
    every publish or stop treating it as a release record.
  - **"Current version" now means the newest PUBLISHED release** — the newest image a user can
    download — and both docs now say so explicitly rather than leaving it to inference. Fixed:
    `README.md` (v2.3.1 → v2.3.7, plus the "built + shipped at v2.3.1" model-scope claim),
    `docs/INSTALL-AND-ROLLBACK.md` (v2.3.2 → v2.3.7, dropped the stale "v2.3.3 is RT-BE96U-only"),
    `docs/CI-PUBLIC-BUILD.md` (pin `Reaper_v2.3.2`/`0001–0378` → `Reaper_v2.3.7`/`0001–0406`,
    verified against the workflow and a 406-file `patches/`), and **a third stale reference the
    original entry missed**: the comment at `public-build.yml:483` still said the pin was
    `Reaper_v2.3.1`.
  - **The same class of drift found again on 2026-08-13, in three more places, while cutting v2.4.1** —
    the fix above corrected the files it named, not the pattern:
    - `docs/RELEASE-NOTES.md` header claimed *"`Reaper_v2.3.5` — current head, source rung only: not
      built"* while the document's own lead section was v2.3.7, and separately claimed *"v2.3.2 is
      built + shipped on all five models"*. Both corrected, and "current head" is now stated
      alongside "newest PUBLISHED release" so the two cannot be confused again.
    - `docs/RELEASE-NOTES.md` also had a **`**Firmware:** …` line spliced into the middle of a
      sentence** in the v2.0.0 bullet ("A comprehensive security review of **Firmware:** … inherited
      ASUS/Merlin open source Reaper ships"), evidently from an earlier automated header update that
      matched the wrong line. Removed.
    - `patches/README.md` still advertised **374 patches, v1.0 → v2.3.1** with a section list ending
      at v2.1.2 — it had not been updated for eight rungs. Counts corrected to 424 / v2.4.1, sections
      written for `0311`–`0424`, and the fact that no per-rung note was written for `0375`–`0406` is
      now recorded rather than papered over.
  - **A third instance, 2026-08-14 — and one of a different kind.** Two more version-drift finds:
    `docs/RELEASE-NOTES.md` §8 still called **v2.3.1** "current head" (true until 2026-08-08), and
    the file now states the head in exactly one place, at the top. More usefully, this round also
    found the failure mode the automation above would *not* have caught: both `CHANGELOG.md` and
    `RELEASE-NOTES.md` recorded a **technical justification that was simply false** — that this
    router's dnsmasq is compiled without ipset support, which it never was. A version number is
    mechanical and can be generated; a reason is written by hand and can only be checked by someone
    re-deriving it. Both are now annotated in place rather than rewritten, so the record shows what
    was believed and when it was corrected.
  - **Remaining [P3]:** decide whether `cut_rung`/the publish path should write image hashes into the
    manifest automatically, so this cannot drift again. The three finds above argue the wider point:
    every doc that restates a version or a count is a copy that can rot, and `cut_rung` already knows
    the true values at cut time. Candidates it could own outright: the `patches/README.md` header
    count, the `docs/CI-PUBLIC-BUILD.md` pin row, and the `RELEASE-NOTES.md` "current head" line.

- **[P3] Decide whether two internal docs should be published here.** `docs/BACKLOG.md` and
  `docs/CHANGELOG.md` each referred readers to a document that does not exist in this repo —
  `GUESTPRO-2.5G-VLAN-PLAN.md` and `CODE-AUDIT-2026-08-05.md`. Both live in the private working tree
  (`asuswrt-merlin.ng/docs/`) and were never copied across, so the links were dead for every public
  reader. Found 2026-08-13 by a relative-link sweep of the repo (211 links, these the only two
  broken). **De-linked for now**, with the text kept and the docs named as unpublished — publishing
  them is an owner decision, not a cleanup, since neither has been through a PII/scope review.
  Either copy them in or leave the prose as-is; what should not persist is a link that 404s.

- **[P3]** Document the non-functional retained features (the firmware update-check UI's stock pieces,
  the removed security-check UI) that are kept only for potential future use.
- **[P3]** Annotate the system defaults.
- **[P3]** Write a user guide for other users. *(Started 2026-08-14:
  [`FIREWALL-GUIDE.md`](FIREWALL-GUIDE.md) covers the eleven firewall tabs — what each is for, how
  best to use it, a worked example, and the non-obvious traps — and every tab's **?** button links
  to its section. **Those links 404 until this repo is pushed.** The same treatment is owed for
  Warden, Gatekeeper, QoS, Traffic and the Devices pages.)*

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
