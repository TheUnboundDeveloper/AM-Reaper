# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v2.8.6** · 2026-08-28 <!--@stamp-->

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done), **[blocked]** (external cause), **[shelved]**
(deliberately deferred), **[cosmetic]** (polish, non-blocking).

**Priority** (by impact on user-facing functionality): **[P1]** core function
broken or at risk for users · **[P2]** degraded function, meaningful annoyance, or
privacy exposure · **[P3]** cosmetic, polish, internal quality, or deferred-by-decision.

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md). **Completed items are not kept here** —
> when something ships it is recorded in the changelog and dropped from this file. A shipped change
> is treated as done unless a problem is reported against it; this file no longer tracks per-version
> confirmations.

*Updated 2026-08-30 (6th pass) — six items moved to FIXED IN TREE for the v2.9.4 test image
(commit `4387547afa`), each pinned by a new `verify_markers` regression rule so a later change
cannot silently drop it: Firewall Status forwards/intercepts rows; the Smart Connect dead switch
(RESOLVED AS THE POINTER, not the sdn_rl driver — rewriting sdn_rl from a classic page risks every
SSID, so the migrated state repoints the button and both stale hints at the Network page while
un-migrated boxes keep the working classic toggle); the rail-clock re-sync (shared
`js/reaper_clock.js`, fed by a new `data-now` attribute on the banner fragment — no new endpoint);
the Devices export reserved_ip + state columns (owner chose new columns over overloading `ip`);
the QoS drops-interpretation note (RQOS_124); and the diag VIF ssid_len off-by-one (REAPER-DIAG
v1.3.10 — marker moved in the same change in BOTH the engine and this repo's build-scripts copy,
which was found still pinned at v1.3.8). All metal owed on the v2.9.4 image.*

*Updated 2026-08-29 (5th pass) — owner decided the Diagnostics numbering item: DROP the numbers from
the two preamble blocks rather than renumber the body. Entry rewritten from a choice into a
five-step work item, including the report's own prose reference to `0b` and a REAPER-DIAG version
bump so a report can be told apart from a pre-change one.
Earlier: 2026-08-29 (4th pass) — three more from v2.9.0 metal: Firewall Status omits Forwards and
Service Intercepts (a posture page silently not reporting two live enforcement surfaces — [P2]); the
Status refresh button gives no visual acknowledgement though the request does fire; and the
Diagnostics preamble blocks are numbered `0.`/`0b.`, which turns out NOT to need a renumber — the
body already starts at 1, so dropping two numbers beats shifting 28 sections and breaking every
cross-reference by number.
Earlier: 2026-08-29 (3rd pass) — added the Gatekeeper "Guest pass length" unit-label gap, found on
v2.9.0 metal: the select offers 4/8/24/48 with no unit and neither label says hours, while the
per-device grant button is the only place that shows one (a hardcoded `' h'` that bypasses the dict).
Scoped with the real cost stated — one token minted and translated across 24 packs, not a one-liner.
Earlier: 2026-08-29 (2nd pass) — added the Devices export gap: an offline device that holds a
reservation or a pin exports with a blank IP because `expRows()` emits the live lease only. Scoped
against the page — the fix is one function, but it needs a decision on not passing a reserved
address off as a lease, and on how broken reservations (orphan / duplicate) are marked in the file.
Earlier: 2026-08-29 — added two owner-reported Traffic Analyzer investigations, both open and
neither root-caused: the occasional visual reset (characterisation owed — the page-reload path is
ruled out, a clock step on this RTC-less board is the first candidate) and the class breakdown
reading almost all "Default"/"Streaming" (the D2/D3 label-and-map inversions are confirmed closed in
tree, so the open question is classifier coverage vs the panel being upload-only).
Earlier: 2026-08-28 (5th pass) - added the rtrafd rt_bound() pipe-inheritance regression (Traffic
Analyzer live freeze on v2.8.6+ metal), root-caused, lab-confirmed and fixed in tree the same day;
ships v2.8.8.
Earlier: 2026-08-28 (4th pass) — closed the three documentation items (retained-but-inert
features, system defaults, per-page user guides): REAPER-GUIDE.md is now the single manual and is
pushed, with the two old guides left as anchor-preserving stubs so shipped ? buttons still work.
Added a follow-up to retire those stubs once the per-tab links are repointed. Fixed one stale
FIREWALL-GUIDE cross-reference the merge left behind.
Earlier: 2026-08-28 (3rd pass) — closed the `RFW_*` IPv6 protocol-label item (`RFW_257` minted and
translated in all 25 packs) and the `pinTarget()` sub-item of batch B, which turned out to need no
decision at all — the substitution it asked about was removed deliberately, so only the caller's
stale comment and a dead ternary needed clearing. Recorded a reachability finding on the `rexport`
mask loop.
Earlier: 2026-08-28 (2nd pass) — removed three items that shipped in v2.7.8 and are recorded in the changelog: the UPnP two-key desync, the QoS live-stats blank, and the Gatekeeper access-level menu closing under the 5 s poll. Verified against the tree, not just the notes: both UPnP commits are on `be96u-only` with the shared helpers in place, and we are 15 commits past them on v2.8.6.
Earlier the same day: added the two `reaper_diag` counter defects (QoS readback truncation and
wireless-churn line-counting), both found on v2.8.6 metal and remediated in tree for the next
diag build, with a CI regression guard.
Earlier: 2026-08-26 — added the QoS live-stats and Gatekeeper dropdown defects (both found on v2.7.7 metal, remediated in tree
for v2.7.8). Last cleaned 2026-08-25 (after v2.7.7) — removed what v2.7.7 shipped (Gatekeeper
re-list count; the translation pass) and added the UPnP key-desync defect found in the field the
same day.
Earlier: 2026-08-24 retired the Pending-verification confirmation list and removed all
shipped/closed items. Only genuinely open work remains.*

---

## Contents

- [Work next](#work-next)
- [Open bugs / under investigation](#open-bugs--under-investigation)
- [UI / UX polish](#ui--ux-polish)
- [Features to add](#features-to-add)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Documentation](#documentation)
- [Reported, investigated, closed as working-as-designed](#reported-investigated-closed-as-working-as-designed)
- [Blocked by closed-source components — for ASUS / Broadcom](#blocked-by-closed-source-components--for-asus--broadcom)

---

## Work next

The ordered short list. Each line points at its full entry below.

1. **[P2] Warden "crash" on the BE92U addon box** (amtm + Diversion update) — hypotheses ranked,
   tester data requested. → [Open bugs](#open-bugs--under-investigation)
2. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — needs a repro on
   v2.7.6+. → [Open bugs](#open-bugs--under-investigation)
3. **[P3] Code-review tail, batch B** (`do_reaper_conn_cgi` lock order, `rexport` mask loop,
   §2.1 iptables-restore batching — the first and last are owner-deferred; `pinTarget()` is
   **closed**).
   → [Code quality](#code-quality--deferred-with-reason)

---

## Open bugs / under investigation

- **[P1] AiMesh "Add Node" finds nothing whenever the CAP heard the node only on 2.4 GHz — the
  parent-presence gate throws away a parent that would have worked (owner, field, 2026-08-30;
  GT-BE98 CAP + 3x RT-AX92U).** Neither wireless nor wired search offers any node. Field log:
  ```
  aimesh: onboarding: parent 60:CF:84:XX:XX:EA skipped for node 04:42:1A:XX:XX:C0 - missing rssi_5g rssi_5g2
  aimesh: onboarding: parent 04:42:1A:XX:XX:61 skipped for node 04:42:1A:XX:XX:C0 - missing rssi_5g rssi_5g2
  aimesh: onboarding: node 04:42:1A:XX:XX:C0 (RT-AX92U) seen but no parent selected - not offered
  ```
  **Root cause.** `select_best_onboarding_re()` (`httpd/web.c:43499`) requires ALL FIVE of `rssi`,
  `rssi_5g`, `rssi_5g2`, `source`, `ts_eth` to be present on a candidate parent before that parent
  contributes anything. `cfg_server` (closed) writes `/tmp/onboarding.json` with only the bands it
  actually heard the node on — here 2.4 GHz alone — so every parent is discarded, no parent is
  selected, and the node is dropped from the list. The wizard's "no node found" is that EJ returning
  empty; nothing else signals it.
  **The bitter part: the fallback that would fix this already exists and is unreachable.** Each band
  is scored independently with its own `!= 0` guard (`:43521-43538`), and at `:43586` there is an
  explicit 2.4 GHz fallback — `else if (rssi2g < 0 && rssi2g > invalidRssi) { reMac = reMac2g; }` —
  that selects a 2.4 GHz parent when no valid 5 GHz RSSI exists. It can never run, because the
  presence gate discards the parent first. The gate is there to avoid dereferencing a missing key,
  NOT because all three bands are required.
  **This answers a question recorded as OPEN on 2026-08-23** (see memory `aimesh-onboarding-gk.md`):
  *"whether the blob POPULATES rssi_5g2 on a tri-band box at runtime is only answerable from the
  field log lines."* It does not. It also explains the original "works great for some, not at all for
  others" report shape — it depends entirely on whether the CAP happened to hear the node on 5 GHz,
  which varies with model, band plan and placement.
  **Fix shape (narrow, no blob work, in a file we own):** replace the all-five gate with
  per-dereference guards — keep `sourceObj` required (structural; `*source |=` needs it), require
  `tsEthObj` only on the ethernet branch (`source & 0x2`), and guard each band's comparison with its
  own object presence. Nothing downstream changes; `reMac2g` populates and the existing fallback
  selects it.
  **Why this is low risk:** the 2026-08-23 review established these gates affect the SEARCH LISTING
  ONLY — the join path (`ob_selection` / `onboarding`+macs, `web.c:14609/14616`) never reads
  `onboarding.json`. Worst case a node is offered with a 2.4 GHz-chosen parent and the join proceeds
  through its normal stock path.
  **Scope:** verified present in canon (`be96u-only`, v2.9.2) AND on the `gt-be98` branch (v2.8.8),
  so the owner's CAP has this exact code. Fix in canon, then port. The logic being changed is STOCK
  ASUS; our only prior change here was the v2.3.7 `aimesh:` diagnostic logging — **which is the sole
  reason this was diagnosable at all**, and is a good argument for keeping that instrumentation.
  **Metal:** needs a real node to prove; owner's mesh is the only rig - AND the CAP is a
  GT-BE98 on v2.8.8, so the sibling port must land before his mesh can exercise it.
  **[FIXED IN TREE v2.9.3, commit `3a6507bfbf` - rides the next image; metal owed]**

- **[P1] A settings restore can quarantine the admin who performed it — Gatekeeper lockout with no
  shell (owner, metal, 2026-08-29, v2.9.2).** `gk_rl` restored from a backup is trusted verbatim, so
  if the restoring client's MAC is not in that file the box reboots, arms Gatekeeper and locks the
  operator out. Hit for real with SSH disabled, i.e. no shell recovery path. **The HTTPS admin-port
  carve-out saved it** — `https://<lan_ip>:8443` reached the login page while quarantined, which is
  the first on-metal proof of the v1.7.3 `REAPER_GKI` escape hatch (the cert warning is irrelevant;
  the carve-out is a firewall RETURN, not a TLS decision). A likely aggravator: changing the Wi-Fi
  password makes client OSes treat the SSID as a new network profile and present a **fresh
  randomized MAC** that no restored whitelist can contain.
  **Fix shape:** capture the requesting client's MAC at `do_reaper_restore_cgi` time (connection IP
  → ARP) and force it into the restored `gk_rl` as approved-full before the reboot; apply the same
  to the stock `.CFG` restore, which carries `gk_*` too. Same self-exempting principle as Service
  Intercept's automatic source exemption. Consider also re-deriving the baseline union (ARP +
  dnsmasq leases + `custom_clientlist`) after a restore instead of trusting the file — that is the
  fix that cured the original first-activation lockout. **[FIXED IN TREE v2.9.3, commit `3a6507bfbf` - rides the next image; metal owed]**

- **[P2] TEST/CHARACTERIZE - field report: MLO ON kills the AiMesh backhaul; MLO OFF restores it
  (tester, 2026-08-30).** Verbatim: "if you configure aimesh in official firmware then dirty
  install yours, aimesh works, but if you set MLO to on, no more aimesh connection, when MLO is
  off all is ok." Setup believed to be the GT-BE98 CAP + 3x RT-AX92U mesh from the onboarding
  report. Reproducible and reversible per the report, which makes it characterizable.
  **Before calling it a Reaper bug, three things to rule in order:**
  1. **The nodes are Wi-Fi 6 (RT-AX92U) - NOT MLO-capable.** Enabling MLO on a BE-class CAP moves
     fronthaul/backhaul onto MLD-linked profiles that an AX node cannot join; "MLO on = mesh gone"
     may be a hardware constraint working as designed. The real question is whether STOCK firmware
     refuses/warns when MLO is enabled with legacy nodes onboarded (check `SDN/mlo.js` and the
     stock MLO enable path for a capability gate) and whether Reaper LOST that guardrail - a
     missing "your nodes do not support MLO" refusal would be OUR defect even if the breakage is
     inherent.
  2. **[[mlo-cold-boot]]: MLO enable/disable needs a COLD power cycle** on this platform. A
     warm-toggled MLO state is half-applied; the report must be reproduced with cold cycles on
     both transitions before the on/off asymmetry is trusted.
  3. **Dirty-install residue**: the config came from stock via dirty flash - MLO/SDN nvram written
     by stock may interact with Reaper's sdn_rl state (see the MAINFH migration item above). A
     clean-configured mesh should be tested alongside.
  **Also check:** the v2.7.3 Gatekeeper cfg_relist exemptions and the AiMesh onboarding-gate fix
  (v2.9.3) are on the CAP side - confirm the tester's CAP build carries them, and that MLO-on does
  not change the backhaul MAC set out from under `cfg_relist` (a NEW MLD MAC that is not in the
  registry would get quarantined if Gatekeeper is armed - same failure signature).
  **Deliverable:** a verdict (stock constraint / missing guardrail / genuine regression) + if
  guardrail: block or warn on MLO enable while non-MLO nodes are onboarded. **[owed - needs the
  tester's mesh or the owner's]**

- **[P2] After a factory reset the main Wi-Fi network sits on the primary BSS instead of subunit 1,
  because the SDN MAINFH/MAINBH profiles are never created (owner, metal, 2026-08-30, v2.9.2).**
  OWNER DIRECTION: get the main network hosted where it belongs. **We do NOT have to reach that
  state the way ASUS does** - any alternate method that reaches the same end state with no negative
  behaviour is acceptable.
  **The state machine, now measured on hardware.** Factory `sdn_rl` is a SINGLE row
  (`<0>DEFAULT`, `defaults.c:5701`, `apg0_enable=0`), so there are no main-fronthaul profiles and
  the main SSID lives on the primary BSS `wlN`. In the migrated state `sdn_rl` carries SIX rows -
  `DEFAULT`, the guest `Customized`, one `MAINBH` and **three `MAINFH` (one per band)** - the main
  SSID moves to `wlN.1` on all three bands (a `wl2.1` is created for 6 GHz), the guest network is
  pushed down to `wlN.2`, and the primary BSSes become hidden internal carriers with a generated
  32-hex SSID (`wl0_closed=1`).
  **What performs the migration: `cfg_server`, the closed AiMesh control-plane daemon.** Syslog:
  `Aug 29 23:16:28 rc_service: cfg_server 8768:notify_rc restart_wireless;restart_sdn 1;`
  It is NOT `validate_apply` calling `sync_apgx_to_wlunit()` directly - that path
  (`httpd/web.c:5211`, gated on `nvram_modified_sdn==1`, set by an apply touching `sdn_rl`,
  `vlan_rl`, `radius_list` or `vlan_trunklist`) appears to be the nudge, not the actor.
  **Why it does not happen on a factory box - and this is the crux.** `cfg_server` requires
  `x_Setting==1`; a factory Reaper box ships `x_Setting=0` **deliberately**, restored to stock by
  `fe082ffe64` so the box stays discoverable as an AiMesh node (`no_need_obd()` bails when it is 1).
  `x_Setting` only flips on the first apply. So the box sits un-migrated from factory reset until
  the first apply AND `cfg_server` gets round to reconciling - on the owner's unit that gap ran from
  the reset until 23:16. **This is the third distinct defect caused by the same `x_Setting` 0-vs-1
  tension.** Note a settings restore does NOT close the gap either: it writes nvram directly without
  going through `validate_apply`, so it can import a guest network while leaving the box un-migrated.
  **What is visible while un-migrated:** the Wireless Log reports the GUEST network as the radio
  (SSID/BSSID read from `wlN.1`), the main network appears on no page, its clients are missing, and
  6 GHz reads "Not associated / Mode: undefined" because no `wl2.1` exists yet. All of that
  self-heals the moment the migration runs.
  **>>> TWO CORRECTIONS TO THE EARLIER WRITE-UP OF THIS ITEM - DO NOT ACT ON THE OLD FRAMING. <<<**
  1. `wl_status_array()` hardcoding `"wl%d.1_"` (`httpd/sysdeps/web-broadcom-am.c:296`) is **CORRECT
     CODE**, from Eric "Merlin" Sauvageau's `bff9ecb15a` ("main network now being subunit 1"). It is
     right for the migrated state and must NOT be changed. The earlier entry blamed it; that was
     wrong.
  2. `sdn_mainfh` is **NOT** in this box's `rc_support` (verified on metal - zero SDN tokens), so
     `isSupport("sdn_mainfh")` is false and line 108 of `Advanced_Wireless_Content.asp` is NOT what
     hides the SSID/security rows. They ARE hidden in the migrated state (the page correctly reduces
     to RF-only and SSID/security move to the Network page), but **by what mechanism is still
     unknown** - do not assume this one.
  **The two questions that need a wipeable box** (`cfg_server` is closed, so source cannot answer):
  (a) on a clean factory box with `x_Setting=0` and NO restore, does `cfg_server` ever migrate on its
      own, or never until an apply? (b) what is the minimum trigger - is `x_Setting=1` sufficient, or
      is an SDN-touching apply also required? (a) decides whether there is anything to fix at all;
      (b) decides whether the fix is one flip at the right moment or a real reconciliation call.
  **THE ARCHITECTURAL READ (owner, 2026-08-30) - this defines what "fixed" means.** QIS was not
  just UX: it was the STATE AIRLOCK. On stock firmware the wizard's completing applies flip
  `x_Setting` and give `cfg_server` its reconcile, so the un-migrated state exists only INSIDE the
  wizard - by the time a user first sees the Wireless page or Log, the box is on subunit 1. That is
  why upstream could hardcode `wl%d.1_` and ship `get_fh_ap_ssid_by_unit()` with no fallback: the
  state where those are wrong is unreachable behind the wizard. Reaper replaced QIS's credential
  function (the banner) and its WAN hand-holding (the audience does that themselves) and replaced
  the state transition with NOTHING - it now fires whenever some unrelated apply trips it. So the
  fix is not "patch the pages that misbehave un-migrated"; it is: **Reaper's no-wizard first-boot
  flow must perform the transition QIS used to own, at a deliberate moment** (candidate: the first
  successful credential change, which already flips `x_Setting` via the chpass blob), while never
  forcing `x_Setting=1` at factory. Still inference until measured: whether the `x_Setting` flip
  alone migrates or an SDN-touching apply is also required - the owner's reset-then-restore run
  today captures exactly that.
  **Constraint on any fix:** do not simply force `x_Setting=1` at factory - that is exactly what
  `fe082ffe64` reverted, and it kills AiMesh node discoverability. Whatever is chosen has to leave
  `obd` able to advertise. **[owed]**

- **[P2] Every restore message can be silently dropped, success or failure (found while diagnosing
  the field report, 2026-08-29).** The backup card's `msg()` helper (`httpd/reaper_inject.c:119`)
  opens with `var m=document.getElementById("rbk_msg"); if(!m)return;` — if that element is not on
  the page, the result of a restore is discarded with no console trace. This is the likeliest
  explanation for the owner's "it returns 200 OK and just does nothing", and it means the per-cause
  `ec` codes added in v2.9.2 never reach the operator. Fix this BEFORE chasing the restore failure
  itself: until a restore can report its own outcome, every restore report is unfalsifiable.
  **[FIXED IN TREE v2.9.3, commit `3a6507bfbf` - rides the next image; metal owed]**

- **[P2] Firewall Status omits Forwards and Service Intercepts entirely — the posture page does not
  report two enforcement surfaces that are live (owner, metal, 2026-08-29).** The "Rules engine"
  card at `Reaper_Firewall.asp:1195-1200` counts `nrules / nobj / ngrp / nsvc / nzone / nzpol` and
  stops there. The `nat` record store — which holds BOTH port forwards and Service Intercepts, since
  v2.9.0 distinguishes them by the record's `mode` field (`forward | intercept | redirect`) — has no
  row anywhere on the tab, and neither does the `REAPER_FWM` masquerade chain that Intercept's
  hairpin return path installs. The page's stated job is to report posture; an operator who has just
  redirected all LAN NTP to an internal server can read this page top to bottom and see no trace of
  it. That is worse than a missing count, because the absence reads as "nothing configured" rather
  than "not shown". Note the draft-state machinery already treats `nat` as a first-class key — the
  `dirty` flag in `web.c` walks `obj, grp, svc, zone, zpol, rules, edef, nat` — so Status is the odd
  one out, not the store.
  **Scope:** the CGI must emit the counts (`action=status` in `httpd/web.c`, alongside the six it
  already sends), and the page renders them with `kvCount`. Worth deciding whether forwards and
  intercepts are one row or two — two is more useful (they are operationally different things) and
  the `mode` field already separates them, at the cost of one extra minted token across 25 packs.
  Whether the `REAPER_FWM` chain deserves its own row is a smaller call; the Intercept row implies
  it. **[FIXED IN TREE v2.9.4, commit `4387547afa` - regression marker pinned; rides the v2.9.4 test image; metal owed]**

- **[P3] Traffic Analyzer resets visually every so often — reported 2026-08-29, not yet
  characterised.** The page occasionally snaps back as if it had just loaded: what is not yet
  established is *what* resets (the live WAN chart only, the per-window history, or the whole page)
  and whether any stored data is actually lost. That distinction sets the priority — a redraw with
  the dataset intact is cosmetic; a history that genuinely zeroes is **[P2]**. **Do not assume this
  is the v2.8.8 freeze** (`rt_bound()` pipe inheritance, closed above): that symptom was a *stall*
  followed by a lurch, not a return to empty. Candidates worth separating, cheapest first:
  (a) a **clock step**, which this box takes on every boot and every NTP re-sync because the
  RT-BE96U has no battery-backed RTC — `rtrafd.c` zeroes ring slots by wrapped index specifically to
  survive that, and the same mechanism is what produced the historical "Month tab resets on a
  firmware update" field report (see `rtrafd.c` ~413-490 / ~2311-2371), so a step in the wrong
  direction is the first thing to rule in or out; (b) an **rtrafd restart** re-seeding `live.json`
  from scratch — visible as a fresh daemon PID or a `healthhist spool reset` line in syslog;
  (c) a **page-side** rebuild, where the fetch helper's single `onloadend` hands `ok=false` to a
  draw path that rebuilds its series from an empty response rather than holding the last good frame.
  The only page-initiated `location.reload()` is in `applySettings()` (user-driven, 6 s after
  Apply), so a spontaneous reset is *not* that. **Data to collect at the moment it happens:** which
  window tab was open, whether the Month/Day tabs also went empty or only the live view, `uptime`
  plus `pidof rtrafd` before and after, and syslog around the event grepped for `rtrafd`, `ntpd`,
  `crond: time disparity` and `settimeofday`. 
  **CORROBORATION FOR CANDIDATE (a), 2026-08-30:** a clock step is now OBSERVED on this unit, not just theorised. The live syslog interleaves `Aug 29 23:16:28` and `Aug 30 03:14:19` lines in the same contiguous block - i.e. the clock jumped forward ~4 h mid-log when NTP corrected, exactly the no-RTC behaviour described above. That does not yet prove it causes the visual reset, but it removes the need to establish that steps happen at all; the remaining work is correlating a step with an observed reset. **[owed - characterisation]**

- **[P2] QoS class breakdown reads almost entirely "Default" and "Streaming" while gaming and
  web/VoIP traffic is live — reported 2026-08-29 (owner's own box), cause not established.** Two
  readings, and the data to tell them apart is cheap. **(1) The chart is right and the classifier is
  the problem.** This is the structural shape D1 predicts: the catch-all is `qos_default=4` -> qid5
  "Default", and essentially nothing on a modern LAN marks DSCP, so unmarked game UDP and TLS web
  both land in the catch-all. The DSCP map itself is *not* the old inverted one — verified in tree
  2026-08-29: `qos.c` sends CS4/AF41-43 to class 2 and `shared/defaults.c` ships
  `qos_class_names=Web/VoIP,Gaming,Streaming,Downloads,Default`, so class 2 is genuinely "Gaming"
  (the D2/D3 label-and-map inversions were closed in `cef37f5cea` / `0df80aff0b`). What is left is
  that beyond DSCP and the preset rules there is no classifier at all — no port, protocol or
  connbytes rule puts a game or a browser anywhere but the catch-all. **(2) The chart is
  mis-summarising.** The "By class" panel is **upload-only** (it carries the `updonly` badge and
  reads the egress queue counters), so it can never describe download-dominated traffic, and a
  reader comparing it against what they know is on the network would call that wrong even when
  every counter is correct. **Decisive check, no build needed:** on the live box run
  `tmctl getqstats` per qid while a known flow is running and compare `txPackets` against what the
  panel draws — if they agree, this is (1) and the work is classification rules; if they disagree,
  it is (2) and the work is on the page. Note also that the panel is meaningless unless
  `qos_type=11` is actually armed with a non-empty `qos_obw` (D5). Related: the qid5-only drop
  signature already confirmed on metal 2026-08-19. **[owed - triage]**

- **[P2] Traffic Analyzer live metrics froze/flatlined on v2.8.6-v2.8.7 metal, lurching forward every ~20-30 s
  (field, 2026-08-27 night; root-caused and fixed in tree 2026-08-28, lands v2.8.8).** A regression from the
  2026-08-26 audit remediation itself: the `rt_bound()` popen timeout wrapper added to rtrafd let its watcher
  subshell - and the `sleep` it forks, which `kill $_w` never reaches - inherit the pipe write fd, so the
  reader gets EOF only when the timeout expires. Every tmctl answered in milliseconds but still cost the
  collector the full 3 s of blocked fgets(): with HW classful QoS on, 7 queues x 3 s every 4 s class poll plus
  6 s per ping-probe cycle blocked the single-threaded collector ~27 s per loop pass, so live.json updated
  once per lurch instead of 10x/s. Confirmed on the RT-BE96U lab: live.json mtime frozen 22 s then a burst;
  the shipped wrapper measured 3 s / the fixed one 0 s for an instant child on the router's own busybox
  (v1.25.1). Why the audit's metal check missed it: it verified rtrafd CPU (flat - correct, the daemon was
  *blocked*, not spinning), not collector latency. Fix (canon 0562c23e57, cut as patch 0562 on the v2.8.8 rung): detach the watcher from the
  pipe (`>/dev/null 2>&1` before its `&`); harness-proven 3.008 s -> 0.005 s fast path with the hung-child
  kill still firing at the deadline. All five sibling branches carry the same wrapper and take the fix at the
  next port (done on the v2.8.8 cut). First field check of the v2.8.8 MCP test image on the owner's
  RT-BE96U looks good (owner, 2026-08-28). **[owed - v2.8.8 release publication]**

- **[P2] Warden "crash" on the BE92U tester after an amtm + Diversion 6.1 update — hypothesis only,
  tester data requested (2026-08-23).** No fix yet. Ranked: (1) the stuck-nvram wlcsm bug tripped by
  the addon installers' bare `nvram get` storm (our `_nv` guard covers only our own scripts — look
  for `rwatch: reaped hung nvram` / `reaper-nv` lines); (2) `restart_firewall` via Diversion's
  service-event racing `apply.sh` vs `update.sh`/`fold.sh`; (3) Skynet updated by amtm in the same
  pass (ipset / INPUT position-1 conflict). Data requested from the tester: uptime, syslog greps,
  `/jffs/rwatch` dumps, `pidof nvram` + ps, ipset/iptables listings, the addon list, and what
  "crashed" actually means. Note v2.7.6 already hardened the adjacent surfaces (Warden page never
  fails silently; layer re-applies under the firewall lock; PBR teardown deletes only our fwmark
  rules).

  **Code review 2026-08-24:** H2 (`restart_firewall` race) and H3 (Skynet conflict) are
  **code-refuted** — v2.7.6's firewall lock serialises the Reaper re-apply and Reaper/Skynet use
  disjoint chain/ipset namespaces. H1 is the only code-plausible path (an addon `nvram get` storm
  trips the wlcsm netlink wedge → Warden's `apply.sh` reads an empty LAN IP and exits "lan not ready
  — deferred" *after* the chain was flushed, leaving `REAPER_WARDEN` gone until nvram recovers) but is
  not confirmable without the tester's syslog. A defensive fix is designed but **HELD** pending that
  data (owner decision 2026-08-24): rwatch heals a *poisoned* Warden chain but not a *missing* one
  (exactly H1's end-state); a missing-chain re-apply in `rwatch.c` mirroring the PBR short-chain heal
  would close it, no new nvram/proc readers. Ask the tester for syslog around the update grepped for
  `reaper-nv`, `reaped hung nvram`, `rwarden`, `lan not ready - deferred`, plus `/jffs/rwatch/inc-*`.
  **[owed — tester data]**

---

- **[P2] Firewall hosts rule: pasting an IP list blanks the GUI until httpd restarts (BE88U,
  v2.7.1).** **Code review 2026-08-24: no httpd-blocking operation is visible in the firewall
  save/apply path.** The save stages a file (no nvram write/commit, no fork, no synchronous reload),
  apply is async via `notify_rc`, httpd's firewall CGI never takes the firewall lock, and the parses
  are bounded (8192 / 2048-byte caps). **v2.7.6 does NOT fix this** — its firewall change was a
  correctness fix (objects ≥768 bytes silently unenforced), not a hang. Residual suspect is the
  platform stuck-nvram/wlcsm class, but even that does not fire on save/apply (no `nvram_commit`
  until *confirm*). Needs a hardware repro: reproduce the blank, grep syslog for `reaper-nv` /
  `reaped hung nvram` / `rwatch: FAILURE` at that moment; if none appear and httpd is wedged, capture
  `cat /proc/$(pidof httpd)/stack`. **[owed — repro]**

---

- **[P2] Field report: heavy ping loss to 8.8.8.8 / 1.1.1.1 after a router reboot, cured only by
  rebooting the ONT (GT-BE98, 10GBASE-T WAN, PPPoE-over-VLAN835).** Investigated from code and two
  sanitized diags; **not a Reaper code path** (no WAN-PHY / session code is patched) and Warden is
  ruled out as the *cure* (its sets are never flushed by a WAN bounce). Best fit: **OLT holds a stale
  PPPoE session** after the router re-dials; an ONT power-cycle clears it. Both captures so far show
  the *recovery*, not the fault.

  **Mitigation shipped v2.5.5:** one-shot PPPoE stale-session bounce on the rwatch tick
  (`reaper_wanbounce_enable`, default on) — after the 300 s boot grace, if the primary WAN is PPPoE,
  link-up, and **all three** probes (`wandog_target`, 1.1.1.1, 8.8.8.8) fail, `SIGHUP` the pppd
  (re-dial, keeps NAT/routes). Logs a `rwatch` line when it fires. Deliberately **not** an `eth0`
  link bounce — that variant is only warranted if a bad-state capture shows a mis-trained link.

  **Still owed from the tester:** a diag captured **during** the dropped-packet state (after router
  reboot, before the ONT reboot) — it shows `eth0` link state (10G? 2.5G? flapping?), probe loss,
  and whether PPPoE is up. And whether the v2.5.5 bounce line appears and clears it. Separating
  signals: `iptables -nvxL RW_OUT RW_ODROP` climbing ⇒ Warden; `ipset test rw_g_us 8.8.8.8` ⇒ geo
  pick; `/proc/gdx/skb_idx` 0 available ⇒ accelerator (`rwatch_gdx=1` to auto-detect); loss from the
  router's own shell ⇒ upstream.

  **Code review 2026-08-24:** the v2.5.5 bounce is present and logically sound (`rc/rwatch.c`: 300 s
  boot grace, PPPoE-only, link-up, all-three-probes-fail, one-shot latch, `SIGHUP` keeps NAT/routes).
  No code change warranted — this is an upstream OLT stale-session issue. **[owed — tester capture]**

- **[P2] `reaper_diag` under-reported QoS and over-reported wireless churn — two counter defects
  found on RT-BE96U v2.8.6 metal, 2026-08-28.** Both made the diag misreport a state rather than
  fail, which is the worst way for a triage tool to be wrong: the output looked healthy and
  authoritative either way.
  - **Section 10 (QoS) could not tell "shaping" from "armed but toothless."** The per-queue
    readback piped `tmctl getqcfg` through `head -3`, keeping `qid`/`priority`/`qsize` and cutting
    `weight`/`minBufs`/`schedMode`/**`shaper`** plus the `ret code` status line. The three
    survivors are programmed by `setqcfg` unconditionally, while every rate element sits behind
    its own guard (`cap>0`, `obw>0`, `obw>0 && qos_pshaper!=0`) — so a box whose class rates never
    landed printed a per-queue block byte-identical to a healthy one. The port shaper *is* printed
    in full, so a wholly empty `qos_obw` still shows as `(0,0,0)`; what was invisible is the case
    that matters more — port shaper correct, per-class rates from `qos_orates` wrong or absent
    underneath, i.e. exactly the rate arithmetic the classful engine has historically got wrong.
    Sharpening the irony, that block had **already** been rewritten in v1.3.7 for a
    truncation-shaped misdiagnosis (the `QOSDIAG-1` comment: reading the port shaper
    unconditionally "made a healthy type-10 box report (0,0,0) and look uncapped — which is exactly
    what sent the 2026-08-01 investigation down a blind alley"). The fix split the engines and left
    the same bug on the other side of it: the **type-10** branch reads `getqcfg --qid 0` untruncated
    with the shaper visible, while the **type-11** branch — the one with seven shapers to verify
    instead of one — was the truncated loop.
  - **Section 19b counted syslog lines, not events.** `hostapd` repeats the same
    `IEEE 802.11: disassociated` line for one flap — commonly twice, in bursts of up to ten
    identical lines inside a single second. Measured over a 48 h span on metal: **2810 disassoc
    lines → 411 unique `(timestamp, MAC)` events, 6.8x inflation**; the top station was reported as
    `disassoc=1057 (~21/h)` when the truth was **218 events ≈ 4.5/h**. Both the 19b table and the
    section 0b `finding INFO` line were fed from the raw line count. An inflated churn figure makes
    a device that has already been ruled benign look like a router fault, and is precisely what
    drags a closed item back into triage.

  **Fixed in tree, not yet built (REAPER-DIAG v1.3.7 → v1.3.8, `release/src/router/others/reaper_diag`).**
  Section 10 now prints one line per queue carrying every field — and is *shorter* than the form it
  replaces (7 lines vs 21) — plus a `[TMCTL-ERR]` tag when `ret code` is non-zero, which the old
  truncation discarded along with everything else. Both churn counters dedup on
  `(timestamp, MAC, event)` before incrementing; 1-second granularity means a same-second burst
  counts as the one flap it is. The `finding INFO` threshold (200) is deliberately left alone —
  against deduped events it stops firing on ordinary roaming while the real 218-event loop still
  trips it. Verified against live metal: all seven queue shapers read back exactly per `qos_orates`
  (qid1–3 = 1980000 = 90%, qid4–5 = 2090000 = 95%, qid0/qid6 uncapped at 2200000).

  **Regression guard added:** `build-scripts/ci/check_diag_counters.sh` — layer A greps the source
  for the invariants (no `head -3` on `getqcfg`, shaper captured, `TMCTL-ERR` present, dedup at both
  churn sites, `VER >= 1.3.8`), layer B *extracts the real awk programs out of the diag source* and
  runs them against fixtures, so the tests cannot drift from what ships. Confirmed to fail in the
  right direction: 8/8 pass against the fixed source, 7/7 fail against pre-fix v1.3.7 — including
  the old churn awk scoring a 7-line fixture as 6 events where the fixed one scores 3. **[owed —
  ships with the next diag build]**

---

## UI / UX polish

---

- **[P3] Firewall Status refresh button gives no sign it did anything (owner, metal, 2026-08-29;
  owner confirmed via devtools that the request DOES fire).** `Reaper_Firewall.asp:1673` wires
  `$('st_refresh').onclick = loadStatus` and nothing else — no busy state, no completion cue. When
  the posture has not changed, `loadStatus()` rewrites the same `innerHTML` into the same five
  cards, so a successful refresh is pixel-identical to no refresh and the operator cannot tell a
  working button from a dead one. (The control is labelled `RFW_19` = "Refresh"; it is the only
  button on the Status tab.) A few seconds of acknowledgement is enough — the card header already
  carries an empty `<span class="hint" id="st_hint">` at `:178` built for exactly this, so a
  timestamp or a brief "updated" there needs no new markup.
  **Constraint that shapes the fix (standing rule 34):** this button shares `loadStatus` with the
  10 s auto-refresh `setInterval` at `:1250`, so the cue must hang off the ONE always-fires
  completion point in the `xhr` helper (the guarded handler at ~`:661-672`, which already exists
  because `readyState 4 / status 0` fires alongside error and timeout). Setting a busy flag on click
  and clearing it only on success would wedge the button the first time a poll fails. **[FIXED IN TREE v2.9.3, commit `3a6507bfbf` - rides the next image; metal owed]**

- **[P2] Wireless Apply looks like it did nothing, because its feedback rides the connection it
  destroys (owner, metal, 2026-08-29, v2.9.2).** `Advanced_Wireless_Content.asp:3607` calls
  `httpApi.nvramSet(postObject, function(){ showLoading(restartTime); … location.reload(); })` —
  the loading overlay lives INSIDE the success callback. Applying a Wi-Fi password restarts the
  radio and deauths the operator, so the response to that very request never arrives, the callback
  never runs, and the page sits inert while the router applies the change perfectly. Owner only
  realised it had worked when he tried to leave the page and found himself disconnected. This is
  now the FIRST-BOOT path, not an edge case: factory Wi-Fi is open again as of v2.9.2, so the
  intended flow is join-over-Wi-Fi then set a password — which always deauths.
  **Fix:** raise `showLoading()` BEFORE the request, and when the browser is on Wi-Fi replace the
  auto-reload-and-hope with a persistent instruction ("your Wi-Fi password changed — reconnect with
  the new password, then continue") rather than a countdown that reloads into a dead connection.
  Note the security fields are stripped from `postObject` under `isSupport("sdn_mainfh")`
  (`:3587-3605`) and travel the SDN main-fronthaul path instead — metal-confirmed working, so do
  not "fix" that. **[FIXED IN TREE v2.9.3, commit `3a6507bfbf` - rides the next image; metal owed]**

- **[P3] Firewall sub-editor Apply buttons give no visual feedback at all (owner, metal,
  2026-08-29).** `Reaper_Firewall.asp:684` `fwApply()` does `f.submit()` into the hidden `fw_hidden`
  iframe (`fwform`, `:617`, `action=/start_apply.htm`) and then, seven seconds later, blindly
  `location.reload()`. Between the click and that reload there is no busy state, no spinner and no
  message — the operator gets a dead-looking button for 7 s and then a page that flashes. Seven
  call sites go through it: the URL filter (`:1384`), keyword filter (`:1399`), log level
  (`:1403`) and the four at `:1314/:1324/:1363`.
  **Do NOT "fix" the Rules-tab Apply — it is already correct.** `$('rf_apply')` (`:1652`) takes a
  different path entirely: `fwcgi('action=apply', …)` with `showSaved(S,true,<#RFW_154#>)` on
  success plus an `rfwLoad()` refresh, and its pending-changes banner was metal-confirmed working
  in v2.9.0. The gap is only the `fwApply()` family.
  **Shape of the fix:** the acknowledgement has to be raised *before* `f.submit()`, not after —
  the form posts into a hidden iframe, so there is no navigation to hang a completion cue on and no
  callback that reliably fires. A busy state on click plus the existing `showSaved()` helper (used
  by the Rules tab) is enough; the 7 s timer then becomes the completion cue rather than the only
  observable event. Same symptom class as the wireless-page Apply (see the wireless item), but a
  DIFFERENT root cause — there the feedback sits inside an `httpApi.nvramSet` success callback that
  can never fire because applying the change deauths the client. Worth fixing together as one
  "every Apply must acknowledge itself" pass. **[FIXED IN TREE v2.9.3, commit `3a6507bfbf` - rides the next image; metal owed]**

- **[P3] Diagnostics preamble blocks are numbered `0.` and `0b.` — DECIDED 2026-08-29: drop the
  numbers (owner).** `others/reaper_diag:938` emits `#### 0. SANITIZATION LEDGER (what was found and
  withheld) ####` and `:881` emits `#### 0b. FINDINGS (derived by the script; read these first)
  ####`; `www/Reaper_Diag.asp:114` mirrors the `0.` literal in the on-page example. The report body
  is NOT affected — all 28 `sec()` calls already run `1. IDENTITY / VERSION` through
  `19b. SYSLOG HISTORY`. Only these two preamble blocks, assembled ahead of `$BODY` and never part
  of the numbered sequence, carry a zero.
  **The work, in full:**
  1. `others/reaper_diag:938` -> `#### SANITIZATION LEDGER (what was found and withheld) ####`
  2. `others/reaper_diag:881` -> `#### FINDINGS (derived by the script; read these first) ####`
  3. `www/Reaper_Diag.asp:114` -> same edit to the sample line, so the page and the artefact agree
  4. The report's own guidance prose at `:955` says "Start with 0b (FINDINGS), then 19b (history)" —
     it must lose the `0b` too, or the file will point at a label that no longer exists. Nothing
     else in that prose moves: `:950` and `:952-955` cite sections 14 and 16, which keep their
     numbers.
  5. Bump `REAPER-DIAG` version (`www/Reaper_Diag.asp:72` carries the string) so a report can be
     told apart from a pre-change one.
  **Why not renumber:** shifting `1->2 ... 19b->20b` so the ledger could become `1.` would silently
  invalidate every reference by number — the report's own prose, the script comments at `:43` and
  `:759`, the DIAG findings in this backlog and in project memory, and prior session rows citing
  sections 11b and 19b. Removing two numbers achieves "the numbering starts at 1" at none of that
  cost. **[FIXED IN TREE v2.9.3, commit `3a6507bfbf` - rides the next image; metal owed]**

- **[P3] Gatekeeper "Guest pass length" shows a bare number with no unit (owner, metal, 2026-08-29).**
  `www/Reaper_GK.asp:162` renders `<select id="s_hours">` with the options `4 / 8 / 24 / 48` and
  nothing anywhere says what they are. Neither surrounding label helps: `RGK_25` is "Guest pass
  length" and `RGK_26` is "Timed internet-only access for visitors". The operator is left to infer
  hours from the value 24, which is a guess that happens to be right — the nvram key and the CGI
  parameter are both `guest_hours`. Getting it wrong is not free on this feature: someone reading
  `48` as days or `4` as minutes mis-sets a visitor's access window.
  The page already knows the unit and shows it **one place only** — the per-device grant button at
  `:306` renders `gkEsc(j.guest_hours) + ' h'` — so the settings row and the button currently
  disagree about whether a unit is worth displaying.
  **Cost is the honest part: this is a dict change, not a one-liner.** All 25 packs move in lockstep
  (identical line counts, `LnxDictPrep` maps named tokens to line indices at build), so any of these
  costs one token minted and translated 24 times:
  - a unit suffix rendered after the `<select>` — smallest diff, keeps the option values clean, and
    is the shape most locales handle without word-order trouble;
  - unit text folded into each `<option>` — reads best in English, but multiplies the translation
    surface by four and invites "24 hours" being pluralised wrongly in packs that inflect;
  - re-word `RGK_26` to carry the unit in the sublabel — no new token, but it re-translates an
    existing one across 24 packs, so it is not actually cheaper, and it hides the unit from anyone
    scanning the control rather than the description.
  Recommended: the suffix, and take `:306`'s hardcoded `' h'` through the same token while there.
  **Secondary finding:** that `' h'` at `:306` is a hardcoded English abbreviation that never goes
  through the dict at all — same class as the Tier-3 i18n item (hardcoded CGI error strings), and it
  is the reason the unit "already appears" without any pack having been asked to translate it.
  **[FIXED IN TREE v2.9.3, commit `3a6507bfbf` - rides the next image; metal owed]**

- **[P3] Diag over-reports VIF SSID length by one (found reading a live v1.3.9 report,
  2026-08-30).** `others/reaper_diag:456` emits `ssid_len=$(nvram get ${VIF}_ssid | wc -c)` -
  `wc -c` counts the trailing newline `nvram get` appends, so every VIF line reads +1: a live
  report showed `ssid_len=7` for a 6-char SSID, 6 for 5, and 33 for the 32-hex onboarding BSS,
  consistently. The primary-radio path reports its length correctly (32), so the two disagree
  within one report. Cosmetic, but a diag that miscounts invites false "the SSID changed"
  conclusions when comparing reports - the whole value of printing a length instead of the
  (withheld) SSID is that it can be compared exactly.
  **Fix:** one line - `wc -c` -> `awk '{print length($0)}'` or `tr -d '
' | wc -c` (busybox-safe;
  the diag runs under /bin/sh). Bump REAPER-DIAG to v1.3.10 and, per the build-gate lesson of
  2026-08-30, update the pinned `REAPER-DIAG v1.3.9` marker in the engine's `verify_markers.txt`
  AND the lean repo's build-scripts copy in the same change - the v2.9.3 first build failed
  verify on exactly that pairing. **[FIXED IN TREE v2.9.4, commit `4387547afa` - regression marker pinned; rides the v2.9.4 test image; metal owed]**

- **[P3] QoS class table: add a drops-interpretation note under the priority/weighted explainer
  (owner ask 2026-08-30, wording direction his).** `Reaper_QoS.asp` shows per-class DROPS counters
  with no guidance on when a number is alarming, and the metal lesson of 2026-08-30 is that it
  reads scary precisely when the system is working: Default went 441 -> 1191 during two speed
  tests (~0.01% of the packets moved, PI2 signaling at the 95% ceiling) and then froze at idle -
  predicted, tested, confirmed. The owner's first read of 441 was "large amount of drops...not
  sure if these are during settings changes". The AQM card ("drops rise briefly when a class is
  held to its rate; that is the system working") states the mechanism but not the operator's rule
  of thumb.
  **The work:** one new sentence-length token (RQOS_124 - next free; 123 exist) placed directly
  AFTER the priority/weighted explainer paragraph below the class table, saying in substance:
  drop counters are cumulative since the last QoS restart and normally grow only during
  saturation such as a speed test; counters that climb while the link is idle, or while a class
  sits well below its ceiling, are the signal of an actual problem. Append to all 25 packs
  (lockstep - currently 6781 lines; English-seed, translate pass owed with RGK_61/RSEC).
  Standard rules apply: reaper_langcheck OUR[] already lists Reaper_QoS.asp, no line-index moves.
  **[FIXED IN TREE v2.9.4, commit `4387547afa` - regression marker pinned; rides the v2.9.4 test image; metal owed]**

- **[P2] The Smart Connect master toggle is a dead switch in the migrated SDN state, and the Rule
  page's help text points at a control that no longer exists (owner, metal, 2026-08-30).** Owner
  enabled Smart Connect from our toggle on `Advanced_Smart_Connect.asp` (commit `8f560e59b1`);
  nothing happened - the Network page kept three per-band main cards and every band on the Rule
  page read "- -".
  **Why:** the toggle sets the CLASSIC pair (`smart_connect_x=1` + `smart_connect_selif_x` mask)
  and fires a bare `restart_wireless`. Post-migration the main network is owned by the SDN MAINFH
  profiles (`mainfh_smart_connect.status` / `.band_bitwise`, consumed by `SDN/sdn.js:547/2309/6592`),
  and nothing in the classic path regenerates them - no `restart_sdn`, no `sync_apgx_to_wlunit` -
  so the per-band profiles come back unchanged. Not the nvram length trap: `selif_x` is CKN_STR64.
  Same family as the whole migration saga: classic-nvram controls that do not drive the SDN layer
  are dead once migrated.
  **The working path (told to the owner):** Network page -> main network card -> Wi-Fi band
  checkboxes (the `checkbox_wifi_band` control, which carries `SDN_MainFH_Smart_Connect_Hint`) ->
  select all bands -> Apply. Goes through the SDN apply and merges the cards properly.
  **RESOLVED v2.9.4 — option (a)-as-pointer chosen, (b) and (c) partially:** the page detects the
  migrated state from `sdn_rl` (`MAINFH` present); the button becomes a pointer to
  `/reaper_shell.asp#SDN.asp` and the click-guard stops the inert classic post; both stale hints
  (the "- -" cell title and the top banner, now `#scWhereHint`) reword to the Network page when
  migrated. Hand-forging `sdn_rl` was deliberately rejected — the SDN app posts a fully
  re-serialized list and a bad serialization takes down every SSID. RESIDUAL, deliberately left:
  the Rule page still reads `smart_connect_selif_x` for its in-group display, which can desync
  from the MAINFH profiles; once bands are merged via the Network page, whether stock populates
  the steering tables (bsd) is a metal observation, not a code question.
  **The work:** (a) make the toggle state-aware - in the migrated state either drive the MAINFH
  band_bitwise through the same path the SDN app uses, or replace the button with a pointer to the
  Network page edit; do NOT leave a control that silently no-ops. (b) Fix our "- -" cell hint on
  the Rule page (`Advanced_Smart_Connect.asp:202`): it says "add the band under Wireless > General",
  but post-migration that page is RF-only and the band membership lives on the Network page - a
  dead pointer we wrote. (c) While in there, decide what the Rule page should read as "in the
  group" when MAINFH owns membership - it currently reads `smart_connect_selif_x`, which can
  desync from the profiles (observed: button label said "Disable" = x is 1, yet every band read
  "- -"). **[FIXED IN TREE v2.9.4, commit `4387547afa` - regression marker pinned; rides the v2.9.4 test image; metal owed]**

- **[P3] Rail clock never re-syncs with the router - add a periodic refresh (owner ask
  2026-08-30).** The date/time in the nav rail (`.railclock`, `#rc_time`/`#rc_date` -
  `reaper_shell.asp:223-224` and `Main_ReaperDash.asp:398-399`, two copies of the same inline
  script) seeds its base ONCE from `<% uptime(); %>` at page render, then extrapolates with
  `Date.now()-t0` on a 1 s `setInterval`. It ticks forever but NEVER re-reads the router's clock, so
  it silently diverges whenever the router's time steps - and on this board that is routine, not
  exotic: no battery RTC, so every boot and every NTP correction is a step (observed on metal
  2026-08-30: syslog interleaved `Aug 29 23:16` and `Aug 30 03:14` in one contiguous block, a ~4 h
  jump). The shell is exactly the page people leave open for days, framing everything else.
  **The work:** one shared re-sync helper - every few minutes (and on `visibilitychange`, so a tab
  waking from overnight sleep corrects immediately) fetch the router time from a lightweight
  endpoint and re-base `b`/`t0`; keep the 1 s local tick between syncs. Candidates for the source:
  an existing polled endpoint that already carries a timestamp (zero new httpd surface - check what
  the shell already polls before adding anything), else a tiny ej that emits epoch seconds. Constraints:
  (i) the two copies should collapse into one shared function while in there - they are already
  byte-identical twins and will drift apart otherwise; (ii) rule 34 shape for the poller - one
  always-fires completion, no success-only state, and a failed fetch must leave the clock ticking on
  its current base rather than blanking it; (iii) don't tick-skip visibly on re-base - if the
  correction is under ~2 s, slew or just apply it, but a large step (the NTP case) should snap.
  Related: the Traffic Analyzer visual-reset item above - same root phenomenon (clock steps),
  different victim. **[REDESIGNED v2.9.5-pending, commit `cec0b187a0` - the v2.9.4 cut FAILED ON METAL the same day: a page loaded in the pre-NTP window (every boot on this RTC-less board) ticked SUN 31 DEC 2023 confidently, and the first re-sync was 5 minutes out. The redesign never displays an implausible time (year<2026 shows the --:--:-- placeholder), syncs at ~2 s and retries every 8 s until BOTH sides are sane - correcting IN PLACE, no refresh or navigation - rejects a still-pre-NTP server answer, and only then settles to visibilitychange + a 10-min safety heartbeat. Regression marker unchanged. Rides the next build; metal owed]**

- **[P3] Dashboard per-band device list: cap the viewport at FOUR items, scroll for the rest
  (owner ask 2026-08-30).** The clients card on `Main_ReaperDash.asp` groups live devices by band
  (`LIVE_CLIENTS` keyed '24'/'5'/'6'/'eth', band-coded from networkmap `isWL` at ~`:1258`; the
  band filter is `.cl-filter`, the rows render into `#cl_list`). When five or more devices sit on
  one band the list should show four rows and scroll for the remainder, not grow.
  **Current mechanism (read 2026-08-30):** `.cl-list` (~`:53`) is `flex:1 1 auto; min-height:170px;
  overflow-y:auto` inside `.clcard`, whose height is whatever the row it shares with Security
  Posture happens to be - the comment says "fixed height (not max-height): the card must not
  grow/shrink with the device count", so the bound is INDIRECT: it holds only while the sibling
  card is the taller one. With enough devices (or a short posture card) the row stretches and the
  four-item intent is lost.
  **The work:** make the cap explicit - a `max-height` on `.cl-list` sized to four `.cl-item` rows
  (measure a rendered row rather than hardcoding a pixel guess; items are two text lines + 9px
  vertical padding, so ~4x that plus the 6px gaps), keeping `overflow-y:auto` and the existing
  crimson scrollbar styling. MUST preserve the identical-rebuild skip at ~`:1244`
  (`box._rh` compare) - that is what keeps the scroll position and text selection stable across
  the poll cycle, and a naive re-render would snap the user back to the top every refresh.
  Check both the shared-row desktop layout and the stacked mobile layout (~`:355` media rules
  restyle the rail; verify the card column too). **[owed]**

- **[P3] Loading/Restarting overlay — native redesign remains.** Full-screen coverage and viewport
  re-anchoring (`--rv-top`/`--rv-h`) exist since v2.3.3, but **owner 2026-08-12: several overlays
  still centre on the shell viewport**, ignoring the nav rail and header. The `--rv-*` mechanism only
  covers the overlays it was pointed at. Remaining, in order: (i) enumerate **every** overlay/modal and
  re-anchor the rest; (ii) replace **every stock overlay** with a Reaper-themed one; (iii) confirm on
  the router with real pages, not headless. v2.7.3's `reaperConfirm` themed dialog (USB format /
  eject use it) is the shared replacement for (ii) to adopt page by page. **[owed]**

---

- **[P3] Loader z-index raise is class-wide (watch-item).** Applied to the shared `.popup_bg`, so it
  also raises `#hiddenMask` — benign. If an in-page `form_style` modal ever surfaces *while the loader
  is displayed* it would render behind it; scope to `#Loading` then. **[watch]**

---

- **[P3] Smart Connect band-mask hazards (watch-items).** (i) `Advanced_Wireless_Content.asp`'s mask
  builder has a `return 7;` fallback = 2G + 5G + **5G2** on a tri-band box, silently dropping 6 GHz;
  unreachable today (guarded by `smartConnectEnable`) but any edit to that guard resurrects it — the
  mask is indexed by band **slot**, so `2^N-1` arithmetic is always wrong here. (ii) `defaults.c`
  ships `smart_connect_selif_x = "3"` for HAS_6G models — 6 GHz deliberately out of Smart Connect;
  changing it is an owner RF decision. Simulator: `scratchpad/smartconnect_sim.js`. **[watch]**

---

## Features to add

---

- **[P3] OSPF + BGP dynamic routing — ACHIEVABLE, the daemons are already in the tree (investigated
  2026-08-30).** A complete Quagga 0.99.24 source tree is vendored (`quagga/configure.ac:10`) with
  full `bgpd/`, `ospfd/`, `ospf6d/`, `babeld/`, `isisd/`, `pimd/`, `vtysh/`, and rc integration
  already exists (`start_quagga`/`stop_quagga`, `rc/services.c:14937-15065`; `service quagga`
  dispatch `:21763-21768`; nvram `quagga_enable`/`zebra_passwd`/`rip_*`, `shared/defaults.c:4693-4699`).
  It is simply switched off and stripped: `RTCONFIG_QUAGGA` is unset (`config_base:53`) and the
  configure line disables every daemon but `ripd` (`Makefile:5443-5446`
  `--disable-ospfd --disable-ospf6d --disable-bgpd --disable-bgp-announce --disable-babeld ...`);
  `quagga-install` (`:5456-5468`) installs only zebra/ripd/watchquagga. The one stock caller is
  IPTV-scoped (`rc/wan.c:4205-4210`) and `start_quagga` hardcodes `network vlan2/vlan3`
  (`rc/services.c:15039-15042`) — dead on this board. Stock "dynamic routing" otherwise is only DHCP
  option 33/121/249 classless routes (`rc/udhcpc.c:950-957`), not a protocol.
  - **Kernel is ready:** `IP_ADVANCED_ROUTER`, `IP_MULTIPLE_TABLES`, `IP_ROUTE_MULTIPATH`,
    `IP_MULTICAST` (OSPF 224.0.0.5/6), `NET_IPGRE`, MROUTE/PIMSM, `IPV6_MULTIPLE_TABLES` all =y
    (`config_base.6a.4916:677-694,735`). **Off: `TCP_MD5SIG` (`:713`)** → no BGP MD5 authentication
    without a kernel config change; run BGP sessions inside WireGuard instead.
  - **Ship path = enable Quagga's own ospfd/bgpd, not port bird2/frr.** FRR needs libyang +
    protobuf-c + python — none in `router/`; bird2 would need bison added and a new package; deleting
    the `--disable-*` flags is strictly less work. Flash ≈ zebra+lib 450 KB, ospfd 400 KB, bgpd
    700 KB stripped. Quagga 0.99.24 is 2014-era/EOL: bind vty to 127.0.0.1, never expose on WAN.
  - **Config belongs in /jffs, and the hooks already exist:** `append_custom_config()` /
    `use_custom_config()` / `run_postconf()` (`rc/services.c:15026-15032,15053-15057`) — so
    `/jffs/configs/zebra.conf.add` works today; do the same for `ospfd.conf`/`bgpd.conf`. Neighbour /
    area lists never go in nvram (project rule).
  - **Interaction with what we ship:** `route_add` is a plain `SIOCADDRT` (`rc/interface.c:460-463`)
    with no accelerator call, and no `fc flush` fires on a route change (all flush sites are
    QoS/PC: `rc/lan.c:2942,5073`, `rc/pc.c:777...`). Runner follows the FIB for NEW flows, so
    learned routes accelerate normally, but already-offloaded flows may outlive an OSPF reconverge
    → add `fc flush` on route change. Learned routes land in `main` (pref 32766) — no collision
    with PBR pref 9000–9199 or VPN Director 10000+, which override them by design.
  - **Useful for:** multi-router homes / SMB with several L3 segments (OSPF instead of hand-kept
    `sr_rulelist`), BGP over WireGuard to a VPS or homelab core for real failover. Marginal for a
    single-router home. **Effort:** ~1–2 days for "enable ospfd+bgpd, jffs config, vty loopback";
    ~1–2 weeks with a status page modelled on `Advanced_GWStaticRoute_Content.asp` + fc-flush
    handling. **[project]**

---

- **"Wi-Fi VLANs" — ALREADY SHIPPED by the SDN subsystem; reclassified 2026-08-30 into the two
  pieces that are actually missing.** What the RT-BE96U does today: every SDN profile is a VLAN
  (`sdn_rl`→`vlan_rl`/`subnet_rl`, `shared/mtlan_utils.c:426-448`); the **VLAN ID is user-settable
  3–4093** with duplicate checking (`sdn.js:7269,10295,10302-10312`; 52+ is only the seed,
  `sdn.js:11428`); **wired-only VLAN networks** exist (band "None", `sdn.js:87,872-882`); **LAN-port
  Access/Trunk modes** exist on `Advanced_VLAN_Switch_Content.asp:156,1409-1410` (Access →
  `apgX_dut_list` lanport `:1664-1692`; Trunk → `vlan_trunklist` `<MAC>L1#51,91` `:1723-1751`, re-keyed
  to `vlan_trunk_rl` at `httpd/web.c:5049-5053`, applied by cfg_server via `restart_net_and_phy`);
  inter-VLAN traffic is default-deny with pairwise allows from `sdn_access_rl`
  (`rc/firewall_sdn.c:2053-2093`). Ceiling per band is main + 2 guest SSIDs (3 VIF slots), so at most
  two VLAN-carrying guest SSIDs per band; further profiles are wired-only. The L2 programming of
  trunk ports has **no open-source consumer** — it lives in `rc/prebuild/RT-BE96U/amas_apg.o` /
  `shared/prebuild/RT-BE96U/amas_apg_shared.o` and cfg_server — so anything needing NEW L2
  semantics (native VLAN/PVID per port, VLAN on the AiMesh backhaul) is blob-blocked.
  - **[P3] Multi-VID trunk port (S, ~1–2 days, UI-only).** nvram and the blob already accept a VID
    LIST per trunk port (`vlan_trunk_rule_st.vid[512]`, `shared/amas_apg_shared.h:317-321`; the
    `#51,91` syntax), but the UI hard-limits a trunk to ONE profile or "all"
    (`getTrunkListVID()` "suppose flag is the only one vid binded",
    `Advanced_VLAN_Switch_Content.asp:1752-1763`; same assumption `sdn.js:331`,
    `Advanced_VLAN_Profile_Content.asp:204`). A selector that writes a chosen subset unlocks a real
    selective trunk to a downstream managed switch — the SMB case. Prove on metal that the blob
    honours a multi-VID list before building the UI.
  - **[P3] Inter-VLAN ACL page (M, ~3–5 days, pure open source).** `sdn_access_rl` is honoured by
    `rc/firewall_sdn.c:2081-2087` for ANY pair, but httpd only ever writes `<0>N` (br0↔SDN;
    `httpd/web.c:23762,44069,44239,44525`) and no page lets the user pair two guest/IoT VLANs or
    express "IoT may reach the NAS but nothing else". Firewall side is free; this is a Reaper-native
    card (fits the Networks companion-page idea).
  **[project]**

---

- **"Firewall DNAT or Redirect options" — MOSTLY COVERED; reclassified 2026-08-30 into the residual
  gaps.** Surfaces that exist: **Reaper Forwards** (proto/port-range/source objects incl. geo
  ipsets/schedule/log, DNAT + companion ACCEPT — but pinned to `-i $WANIF`, WAN-in only, IPv4);
  **Service Intercept** (v2.8.9: `intercept` = DNAT to an internal host from any source zone,
  `redirect` = `REDIRECT --to-ports` to the router itself, auto-exempt of the target as a source,
  `snat=auto` hairpin; IPv4, port-based, no nat OUTPUT, DNS out of scope by design — see
  SPEC-service-intercept.md); stock port forward / trigger / DMZ / UPnP / NAT loopback
  (`rc/firewall.c:1403-1490,2066-2080,2164,8100-8109`); **DNS Director** (`rc/dnsfilter.c:183-382`:
  udp+tcp 53 from `br+`/`tun+`/`wgs+`, per-MAC, per-SDN interface, per-iprange, REDIRECT to router
  or DNAT to a custom server, IPv6, DoT block `:574-600`); NTP redirect (`rc/firewall.c:1924-1926`,
  UDP only, whole `lan_if`, no source scoping); and the `firewall-start`/`nat-start` user scripts
  (`rc/firewall.c:9390`, `rc/services.c:5652,23624`) as the escape hatch for anything else.
  **"Force all DNS to the router regardless of client setting" is already shipped and better than a
  generic rule would be — do not rebuild it.** Kernel targets are all present: `NF_NAT_REDIRECT`,
  `XT_NAT`, `XT_TARGET_NETMAP`, `XT_TARGET_REDIRECT`, `IP_NF_TARGET_MASQUERADE/NETMAP/REDIRECT` =y
  (`config_base.6a.4916:795-947`); `TPROXY`/`xt_socket` are =m (same class as the `xt_hashlimit=m`
  trap — treat as unavailable).
  - **[P3] 1:1 NETMAP** — nobody offers it; the only occurrence is dead `#if 0` code
    (`rc/firewall.c:2005-2019`). Use case: overlapping subnets across a site-to-site VPN. Small
    extension of the Service Intercept record (a `netmap` mode + target CIDR), ~40–60 lines + tokens.
  - **[P3] Per-VLAN/SDN forced NTP (and generic per-zone service forcing)** — `ntpd_server_redir` is
    all-or-nothing on the primary bridge (`rc/firewall.c:1925`). Service Intercept's `redirect` mode
    with `szone` = a specific SDN already expresses this for the router as target; verify it against
    canon source and, if it does, this is a preset + doc item, not code.
  - **[P4] Raw-protocol DNAT** (non-tcp/udp) exists only in the stock port-forward parser
    (`rc/firewall.c:1490`); niche, add to Intercept only on request.
  - **Design rule: extend Service Intercept, never a new page** — it already owns commit-confirm,
    teardown, `fc flush` on apply, the /jffs draft store and geo-resolve; a second DNAT page would
    duplicate all of it. REDIRECTed traffic terminates on the CPU (no flow-cache) — say so in the UI.
  **[project]**

---

- **[P3] Devices export drops the IP of an offline device that holds a reservation or a pin (owner
  ask 2026-08-29).** `expRows()` in `www/Reaper_Devices.asp` emits `ip: (d.ip || '')` — the *current
  lease* — so a device that is pinned or statically reserved but offline at export time exports with
  an empty IP, even though the router knows exactly which address it owns. That is the wrong answer
  for the file's stated purpose: the comment above it calls this an **inventory**, and deliberately
  exports every device rather than the filtered view for precisely that reason. An inventory that
  blanks the addresses an operator went to the trouble of assigning is the same class of surprise.
  The data is already in hand — the render path uses `d.resv` / `d.resv_ip` a few lines below, so
  the change is confined to `expRows()` and all three formats (CSV, JSON, HTML) inherit it from that
  one function. **Decide before writing it:**
  - **Do not silently pass a reserved address off as a lease.** `ip` today means "has this address
    right now"; a reservation means "is entitled to it". Collapsing the two makes the CSV read as
    though an offline device were online. Preferred shape: keep `ip` as the live lease and add a
    second field (`reserved_ip`, plus a source/state column) so the distinction survives into the
    file — JSON and HTML carry it for free; CSV grows a column, which is a format change worth a
    conscious nod.
  - **Reservations that are broken must not export as fact.** The page already distinguishes
    `d.orphan` (pinned to a MAC that no longer appears) and `d.dup` (two devices pinned to the same
    address) and renders both with the `pindead` chip. Those addresses are exactly the ones an
    operator should not copy into another system unqualified, so whatever field carries the
    reservation must carry that state too.
  - `d.resv_in_pool` (reserved inside vs outside the DHCP pool) is worth carrying for the same
    reason — an out-of-pool reservation is a legitimate config, but it reads as an anomaly without
    the flag.
  No CGI or httpd work: `action=status` already delivers every field named here, and the export is
  built entirely in the browser by design. **[FIXED IN TREE v2.9.4, commit `4387547afa` - regression marker pinned; rides the v2.9.4 test image; metal owed]**

- **[P2] Sign the firmware-update manifest — IMPLEMENTED for v2.7.3, then SHELVED INERT (owner
  decision 2026-08-23).** All machinery ships but nothing enforces: `REAPER_SIG_ENFORCE=0` in
  `reaper_webs_update.sh` skips the whole verify (no sig fetch, no refusal, error 9 / the
  type-to-confirm override UI stay dormant), and `build-scripts/signing.conf`
  (`MANIFEST_SIGNING=off`) makes stage_release / refresh_manifest / the CI signature-status step /
  repo-hygiene all skip quietly. **Re-enable = flip both switches + rebuild** — keypair (owner's
  offline media), sign_manifest.sh, embedded pubkey, verify code, override flow and docs all remain
  ready. Original implementation detail below for that day:
  RSA-4096/SHA-256 (the shipped OpenSSL 1.1.1 CLI has no one-shot Ed25519 — `pkeyutl -rawin` is a
  3.0 feature, verified empirically; Merlin's OpenSSL 3.x-with-shim port is the future path to an
  Ed25519 key via the rotation procedure). The check script verifies
  `updates/manifest_3006.txt.sig` against a public key baked into the firmware BEFORE parsing any
  field; missing/invalid signature refuses the whole manifest, **fail closed**, logged. Signing =
  `build-scripts/sign_manifest.sh` (signs + self-verifies against the shipped pubkey); the private
  key lives at `…\ASUS\reaper-keys\` **outside every repository** and must never enter one or CI —
  **owner: move it to offline media and point `REAPER_MANIFEST_KEY` at it when signing.**
  **RELEASE-FLOW CHANGE: every publish that touches the manifest (CI `refresh_manifest` included)
  must be followed by `sign_manifest.sh` + a commit of the `.sig`, or every fielded ≥v2.7.3 box
  reports "check failed".** The current manifest is already signed (sig staged uncommitted).
  Rotation: new pair → replace `manifest_pub.pem` + the embedded key in `reaper_webs_update.sh` →
  ship that firmware → then switch signing keys. Tamper-tested on host (genuine=pass;
  tampered/garbage/empty sig=refused). Shipped inert in v2.7.3; nothing is pending while shelved.
  When re-enabled, closes when a fielded box verifies a signed manifest (check succeeds) and
  refuses an unsigned one. **[shelved — inert]**

---

- **[P3] North star — progressively replace stock GUI pages with Reaper-native ones.** Done for
  Dashboard/QoS/Traffic/Wireless/GK/Warden/Devices/Advisor/Conn/QoSDiag/Analytics/Storage/Firmware/
  Firewall/VPNRouting/About. **[ongoing]**

---

- **[P3] Staged ("batch") changes — one save, minimal restarts.** A cross-page pending basket
  ("Pending changes (N) — Review / Apply / Discard"), all-or-nothing validation, one nvram commit, a
  de-duplicated ordered action set, reboot only if a staged change is reboot-class (MLO, some
  SDN/op-mode switches). Backend already supports a multi-key apply + chained `action_script`.
  Recommended path: Reaper-native pages first; quick sub-win = one Wireless page for all bands
  applying once. **[project]**

---

- **[P3] Remote syslog push/fetch** for SIEM pipelines (push-based); pairs with the Data Export page.
  Also deferred from that feature: per-device **wireless RSSI/PHY** metrics from `web-broadcom-am.c`.

---

- **[P3] Diag: regulatory-mismatch warning** — `reaper_diag` prints `WARN: territory_code=EU/xx but
  wlX_country_code=US` when they disagree. Read-only; firmware must never auto-alter regulatory
  nvram. **[shelved]**

---

- **[P3] Switch port mirroring → external IDS (owner-backlogged 2026-08-30; INVESTIGATE AFTER
  v3.0.0).** One-click "mirror port A (in/out/both) to port B" so a Zeek/Suricata box on port B sees
  traffic at line rate with zero router CPU — the answer to the in-firmware-IDS question that was
  closed as infeasible (eBPF hard-blocked, CPU budget). Tree recon done 2026-08-30; the hardware path
  is NOT yet proven reachable on this board:
  - **SF2 mirror exists in source but probably does not apply here.** `ioctl_extsw_port_mirror_ops`
    (`bcmdrivers/opensource/net/enet/impl7/sw_common.c:335`, `ETHSWMIRROR` ioctl in
    `bcmenet_ioctl_compat.c:2808`) programs SF2 switch registers (`REG_MIRROR_CAPTURE_CTRL` etc.).
    The RT-BE96U DTS (`kernel/dts/6813/RT-BE96U.dts`) puts all six ports — eth0 = internal 10G xphy,
    eth5 = 10G via BCM84891L serdes, eth1–4 = 1G gphy — under `switch0`, which in `6813.dtsi` is
    `compatible = "simple-bus"` (Runner/XRDP ports). There is no SF2 switch on this board, only an
    `mdio-sf2` PHY bus. The rt-be96u prebuilt `ethswctl` (43 KB) contains no "mirror" string at all.
  - **Runner-side mirror (RDPA `port mirror_cfg`) NOT located yet** — the headers checked did not
    carry it. First thing to settle: find `rdpa_port.h` in this SDK and check `bs`/bdmf_shell strings
    for `mirror`. If Runner has no port mirror, hardware mirroring is dead on 4916 and only the
    software path remains.
  - **Software path CONFIRMED present:** `kernel/linux-4.19/config_base.6a.4916` has
    `NET_SCH_INGRESS`, `NET_CLS_ACT`, `NET_CLS_FLOWER`, `NET_CLS_U32`, `NET_ACT_MIRRED` = y
    (lines 1077–1102) and `tc` is installed from iproute2 (router `Makefile:6244`). So
    `tc filter add dev ethX ingress matchall action mirred egress mirror dev ethY` is available today.
    enet's own tc offload (`bcmenet_tc.c`) recognises `mirred egress mirror` only inside its
    VLAN-manipulation chain (mirror to `wan_virt`), not as general port mirroring — so this is CPU
    mirroring, with the cost that implies.
  - **The decisive unknown (reachability before design):** does `tc mirred` on a Runner port see
    accelerated flows, or only the CPU-path first packets — the same blind spot iptables has once
    flow-cache takes a flow? If only first packets, software mirroring is useless for IDS and the
    feature stands or falls on the RDPA path. Test on metal: iperf across two 1G LAN ports with a
    mirror to a third, count mirrored packets vs. `fcctl`/conntrack byte counts; then CPU cost at 1G
    and 10G.
  - **Shape if feasible:** a Reaper card (Firewall or a new Network Tools tab): source port(s),
    direction, destination port; destination pulled out of `br0` while mirroring; loud throughput
    warning; persisted in the /jffs store, OFF by default; cleared at boot unless persisted.
    **[project]**

---

## Documentation

---

- **[P3] Translations — one residual left.** The functional-token pass across all 24 languages
  **shipped in v2.7.7**. The RABT credits and jokes (`RABT_16`–`RABT_26`, `RABT_41` "GOAT
  whisperer") stay English **by choice** — prose and humour where a mechanical pass reads worse
  than English; the `RABT_29/30/32/33` taglines are translated. That is a settled decision, not
  owed work. What remains:
  - **`RFW_*` IPv6 protocol labels on `Reaper_Firewall.asp` — DONE in tree 2026-08-28, unbuilt.**
    `RFW_257` ("Other") minted and **translated** in all 25 packs (lockstep 6745→6746); the `BOTH`
    label now uses the already-translated `RFW_252`. `TCP`/`UDP` stay literal — they are protocol
    names. Did **not** reuse `Adaptive_Others` (plural, and it names an Adaptive QoS category).
    Translations are not a native pass; the gender-dependent ones (CZ/PL/RU/UK/SL, DA/NO/SV/NL) are
    worth a speaker's skim.
    The `value="TCP|UDP|BOTH|OTHER"` attributes are pinned — **do not remove them**: `rc/firewall.c`
    `strcmp`s the submitted value, so an unpinned translated label would break the rule format in 24
    languages. **Do not reuse ASUS's `option_both_direction`** for "Both" — JP/CN/TW render it as
    *bidirectional*.
  - *Deliberately left literal (verified 2026-08-15, do not re-raise):* Splunk placeholders, the Diag
    ledger preview, Broadcom counter names on the Wireless page, the firewall schedule placeholder
    (`Mon,Tue|09:00|17:00` is parsed), product names, `title="hidden"` on hidden iframes.

---

- **[P3] Make `cut_rung` own the version/count restatements** so doc drift cannot recur: the
  `patches/README.md` header count, the `CI-PUBLIC-BUILD.md` pin row, the `RELEASE-NOTES.md`
  "current head" line, and writing image hashes into `provenance/manifest.json` on publish.
  Two findings that must not be re-derived:
  - **`provenance/manifest.json` is NOT a "did it ship" signal** — image hashes are populated only
    sporadically; the authoritative record is the GitHub Releases API.
  - **"Current version" = newest PUBLISHED release; "current head" = newest source rung.** Each is
    stated in exactly one place.
  Automation would not have caught the worst instance (a *false technical justification* copied into
  two docs); a reason is written by hand and can only be caught by re-deriving it.

---

- **[P3] The user-guide set — DONE 2026-08-28 and pushed.** All three items here (retained-but-inert
  features, the system defaults, and per-page user guides) closed together.
  [`REAPER-GUIDE.md`](REAPER-GUIDE.md) is now the single manual, 1429 lines / ~25k words:
  - **§8 Factory defaults** — the fifteen stock defaults Reaper changes with the reason for each
    (taken from a real diff of `shared/defaults.c` against the base pin), all sixty Reaper-owned
    keys grouped by feature, and what a factory reset does *not* clear (`/jffs`, so every rule
    store survives).
  - **§9 Present but inactive** — the stock firmware page (kept because Reaper reuses its
    `webs_state_*` variables) and the thirteen `AiProtection_*` pages (engine compiled out), each
    mapped to what replaces it, and stating plainly that **nothing replaces DPI / signature IPS**.
  - **§4 deepened** for Firewall (168 lines), Warden (114), Policy Routing (105), QoS (103),
    Gatekeeper (98), Traffic (67) and Devices (51).
  `FIREWALL-GUIDE.md` and `VPN-ROUTING-GUIDE.md` are now **stubs** that keep their original
  headings, so the **?** buttons in already-shipped firmware still resolve.
  In tree, unbuilt: twelve more pages gained a **?** link (QoS, QoS Diagnostics, Traffic, Devices,
  Connections, Wireless, WiFi Pro, Diagnostics, Firmware, Analytics, Policy Routing, AI Advisor),
  reusing the existing `RABT_43` key — **no new i18n keys, no translation pass owed**.

- **[P3] Retire the two guide stubs.** `FIREWALL-GUIDE.md` and `VPN-ROUTING-GUIDE.md` exist only so
  the deep links in already-installed firmware keep resolving. They can be deleted once a release
  ships whose Firewall/Policy-Routing **?** buttons point straight at `REAPER-GUIDE.md` anchors,
  **and** enough time has passed that older images are out of circulation. Repointing those 14
  per-tab links is the prerequisite and has not been done. **[owed]**

---

## Code quality / deferred (with reason)

---

- **[P2] [owed] The code-review MEDIUM/LOW tail** (`CODE-REVIEW-2026-08-18.md`, private working
  tree only). The HIGH tier (Phase-1 H1–H5, Phase-2 P2-H1…H11), the per-byte `fflush` escapers, the
  `esc()` consolidation, the `document.hidden` polling gates and the first tail batch (dead
  `ip2str`/`nhex`, orphaned CSS, `gk_client_name()` index, `sb_scrub_sec_tuples()` hoist,
  `connseen_update()` write-on-change, dashboard `innerHTML` skip) shipped in v2.5.0–v2.5.3. What
  remains is the discrete efficiency/data-flow tail — dead code, redundant nvram re-reads, per-device
  fork loops. **Each item needs reachability verification first**: `reload_upnp()` full restart was
  **REFUTED** (deliberate 2026-08-11 field fix — reverting reintroduces "UPnP dies after a while"),
  `rmcpd tool_firewall` `-S`+`-nvxL` carry different data, the `get_settings_audit` redaction `sed`
  is defense-in-depth, `Reaper_QoSDiag` `fmtBytes` 1024-base is *correct* (queue buffer sizes).
  **Batch A (10 mechanical items) shipped in v2.6.2.** Batch B, deferred with reasons:
  **`pinTarget()` — CLOSED in tree, no decision needed.** The framing above was wrong: the 20→80 MHz
  substitution was not "never implemented", it was **removed deliberately** because it made "best"
  and "applied" disagree in the field — the reason is recorded above the function. Implementing it
  would reintroduce that bug. What was actually wrong was drift in the caller: `scanPin()` still
  described the removed behaviour and appended a `← <original>` suffix behind a condition that can
  never be true. Dead ternary removed, comment corrected, `pinTarget()` kept (deliberate, per its
  own comment). No behaviour change. `rexport.c:77` O(devices) MAC-mask rewrite — **reachability checked 2026-08-28: narrow.** The loop
  runs only when `reaper_export_maskmac=1` **and** `reaper_export_mode` is `both`/`exportonly`; both
  ship off, and the script exits before the loop otherwise. It forks printf+md5sum+cut+`sed -i` per
  MAC and rewrites the whole file each time, on the export interval (default 300 s). The cheap fix is
  one batched `sed -i -f` instead of N in-place rewrites; the md5 forks have to stay (no hash in awk).
  Not done: it is an export path under active metal-test and the gain is small at this reachability; `rwarden.c:1117` stats.sh chain
  re-lists (shell contract with `web.c`); `rchqd`↔`web.c` duplicate `chanim_stats` parser (needs a
  shared header); `rtrafd.c:1727` `metrics.prom` scrape-token semantics; `rtrafd` ping-probe
  blocking / `write_live` 10 Hz (timing-sensitive); dashboard client/port-tile `innerHTML` change
  detection (behavioural).

  - **`do_reaper_conn_cgi` nested-scan-under-lock restructure** — deferred per owner (2026-08-19):
    too risky to reorder locking on a control under metal-test; wants a dedicated look. **[owed]**

  - **Four "orphaned" dashboard CSS blocks** — needs a usage audit (line numbers drifted; most of the
    dashboard CSS is live, no blind removal). **[owed]**

  - **§2.1 netfilter fork storms** (Warden/GK → `iptables-restore` batching, double teardowns) —
    **DEFERRED per owner (2026-08-19)**: high blast radius on controls under active metal-test.
    Revisit once Gatekeeper/firewall are validated on hardware.

- **[P3] Sibling port gap: `Tools_Sysinfo.asp` — ROOT-CAUSED AND FIXED IN-TREE 2026-08-25, needs a
  commit per branch + a build.** Investigated 2026-08-25. The page was listed in
  `_port_protect.sh`'s `PP_PROTECT_GLOB` as one of "the two radio-gated pages", so the port
  skipped it — but it does not gate per *branch* at all: it gates at **runtime** on
  `based_modelid`, so one shared copy serves every model. Measured lag against canon:
  rt-be86u / rt-be88u / gt-be98-pro `11+/76-`, gt-be98 `8+/73-`, **rt-be92u byte-identical**.
  The sibling-only lines are just the pre-rewrite code (the 20-slot `labels:[0,3,…,57]` category
  axis, `animation:false`, direct `data:` arrays) plus an *older* subset of the model checks
  (`GT-AXE16000` only, where canon has `GT-AXE16000 || GT-BE98` **and** `GT-BE98_PRO`) — canon is
  the strict superset for every model.
  - **Worse than a plain lag: the four siblings ship HALF of one two-file rewrite.**
    `Reaper_QoSDiag.asp` is *not* protected and synced normally, so those images render a
    time-based x axis on the QoS Diagnostics chart and the old sideways-snapping category axis on
    the Sysinfo temperature chart.
  - **Proof no divergence is needed:** rt-be92u carries canon's copy byte-for-byte and shipped
    v2.7.6 + v2.7.7.
  - **Done:** `Tools_Sysinfo.asp` removed from `PP_PROTECT_GLOB` (now classifies as shared, so the
    parity check surfaces this instead of hiding it), and canon's copy written into all four
    lagging worktrees — each now byte-identical to canon, one file changed per branch.
  - **Still owed:** commit on each of the four branches (`pp_parity_check` compares *commits*, so
    it reports UNSYNCED until then), rebuild those models, and run `sync_local_engine.sh` so the
    engine copy of `_port_protect.sh` picks up the new rule. **[owed — commit + build]**

  **The `searchIspNameProfile.js` half of this item was wrong — struck.** It is not a sibling lag;
  canon *deliberately* deleted it in v2.3.3's de-cloud pass (`c2162344cc`, "0 shipped pages
  included it"), and that justification still holds: the only reference is in the **base**
  `www/Advanced_WAN_Content.asp:120`, which never ships — `RTCONFIG_MULTISERVICE_WAN=y` means the
  `sysdep/FUNCTION/MULTISERVICE_WAN` overlay overwrites it at install, and that overlay has no
  reference. Confirmed against the staged rootfs: no shipped page includes it, so there is no 404.
  The four older siblings still carry the 3,270 B orphan (rt-be92u correctly does not); harmless,
  delete it for parity whenever those branches are next touched.

  **`Main_WStatus_Content.asp` — same verdict, also fixed 2026-08-25.** It was the other entry in
  that protect glob, and it maps radios at runtime too (`GT-AXE16000||GT-BE98` quad-band /
  `GT-BE98_PRO` / generic tri-band). Four of five siblings were already byte-identical; only
  gt-be98-pro differed, and only by *missing* canon's `2ea3eafaf2` ("add GT-BE98 to the quad-band
  radio branch"). That omission is **inert on GT-BE98_PRO hardware** — `based_modelid` takes the
  `GT-BE98_PRO` branch either way — so nothing was ever visibly wrong; it was drift the port could
  not heal. Un-protected and synced. `PP_PROTECT_GLOB` is now just the dicts and the GT-BE98
  chanlist shim.

- **[P3] Warden custom feeds — both residual ceilings FIXED in-tree 2026-08-25, ride the next
  build.** Confirmed still open before touching anything: `threat_n` was already in the stats JSON
  but **no page ever read it** (`RWDN_89` "Prefixes loaded" is the *geo* count, not the threat
  set), and a single `$CURL` served curated, custom **and** ipdeny geo fetches alike.
  - **Occupancy is now surfaced.** `rwarden.c` gained `RW_THREAT_MAXELEM`/`_S` — the ceiling had
    been a bare `524288` repeated at six `ipset create` sites, so there was no single number to
    quote — and the stats JSON now emits `threat_max` from that same define, so the page cannot
    drift from what the sets are actually built with. `Reaper_Warden.asp` renders
    `<#RWDN_100#>` = "Threat entries: N / 524,288" in the existing breakdown list, next to the geo
    prefix count. Entries past `maxelem` are silently dropped by ipset, which is exactly what a
    user piling on custom feeds could not see before.
  - **Custom feeds are on a shorter leash.** New `CURLC` (`--retry 1 --max-time 15`) is used at
    the two custom-feed fetch sites ONLY; curated feeds and the ipdeny geo fetches keep `$CURL`
    (`--retry 2 --max-time 40`) because those are known-good hosts worth waiting on. Worst case
    for eight custom feeds drops from 8x3x40s ≈ **16 min** to 8x2x15s ≈ **4 min**. `CURLC` gets
    the same `--proto/--proto-redir =https` upgrade when curl supports it, so the redirect pin is
    not weakened. A timeout still logs `custom feed fetch FAILED` and the previous set is kept
    (swap-if-nonempty), so a slow feed degrades to "no refresh", never "no data".
  - **i18n:** `RWDN_100` appended to all 25 dicts in lockstep (6744 → 6745). **`RWDN_92`–`RWDN_99`
    were deliberately SKIPPED** — they are reserved by the shelved port-forward-exemption patch at
    `/home/reaper/shelved/warden-fwd-exempt-v2.7.8.patch`; reusing them would silently relabel that
    feature's strings if it is ever restored. Numbering gaps cost nothing (LnxDictPrep re-indexes
    named tokens at build time).
  **[owed — build]**

- **[P3] The `/tmp` systemic dir-ownership hardening — deferred per owner (2026-08-19).** `mkdir(,0700)`
  return ignored, owner never checked, rc `umask(0)` → `fopen("w")` is 0666; ~11 sites. Fix = ONE
  shared validate-or-refuse helper (`lstat` → `S_ISDIR && uid==0 && !(mode&077)`), pattern at
  `reaper_fw.c:2071`; targeted `umask(077)` per daemon `main()` is the cheap partial (done for
  rtrafd). The sticky-bit half shipped in v2.5.0 (`chmod("/tmp", 01777)`). **[deferred]**

- **[P3] `poll_fcache` O(n²)→hash pairing** (`rtrafd.c`) — bounded to ≤1536 flows / 5 s; not worth
  the regression risk. **[shelved]**
- **[P3] `poll_classes` 7× `tmctl` popen batch** (`rtrafd.c`) — measured 2–3 % CPU. **[shelved]**
- **[P3] `do_reaper_dev_cgi` function-local `static` snapshot arrays aren't re-entrant** — latent
  only (httpd serialises); a malloc refactor adds leak risk for a can't-happen case. **[shelved]**

- **[P3] Theme-token vocabulary consolidation (remainder of D4).** Same-name/different-value drift
  was canonicalized in v2.2.7; still deferred: `--panel2`/`--red*` → `--panel-2`/`--crimson*` and the
  `--line` cream-vs-red divergence — per-page CSS usage rewrites with visual-regression risk.
  **[owed — to the page migration]**

- **[P3] Inherited ASUS/Merlin `httpd` core — two pre-auth robustness gaps that ship in stock.**
  Technically remediable but present in every stock Asuswrt-Merlin build; a change there risks the
  login/serve path and upstream merge-cleanliness. Out of scope for the public release; revisit only
  as deliberate opt-in hardening.
  - `Content-Length` has no upper clamp — four pre-auth body drains `while (cl--) fgetc()`, so an
    oversized value spins ~2e9 syscalls and holds the single-flight GUI. Fix if taken: `cl > 65535 → 413`.
  - `url[128]` unterminated for a path ≥ 128 bytes (`>` not `>=`) → OOB read via the following
    `strstr`/`snprintf`; same for `login_url`. Reachability unproven.
  **[inherited stock; deferred]**

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report does not get re-investigated, and so the reasoning
survives the person who made the call.*

---

- **Dual-WAN: both NextDNS profiles receive DNS logs — NOT a Reaper defect (code review 2026-08-24).**
  "NextDNS" is a DNS-over-TLS upstream, not a firmware feature. With DNS Privacy on, stubby
  round-robins across **every** DoT endpoint in one WAN-agnostic list (`round_robin_upstreams: 1`;
  `start_stubby` in `rc/sdn.c` / `rc/services.c`), and dual-WAN failover deliberately skips per-WAN
  DNS when DoT is enabled (`wan.c` / `multi_wan.c` `if (dnspriv_enable) continue;`). So two NextDNS
  endpoints entered → both are queried regardless of which WAN is live. All stock Merlin / upstream
  code (zero Reaper authorship). **Resolution:** enter ONE NextDNS DoT endpoint. A per-WAN DoT
  profile would be a net-new feature in inherited code, not a bug fix. Do not re-raise as a defect.

---

- **Investigated — NOT a bug (do not re-raise):** `Reaper_Firewall.asp` `v4_src`/`lw_sip`/`lw_dip`
  "XSS" (renders via `td.textContent`); Warden `V6LAN`/`WANIPS`/`V6WAN` (the router's own addresses,
  not reachably poisonable); dnsmasq `/etc/hosts` IP field (an admin can already edit hosts); 
  `custom_clientlist` tail truncation (reader uses `strdup`); scrape-token "fail-open stub" (already
  `CRYPTO_memcmp` + `!want[0]` fail-CLOSED); store-chooser TOCTOU (mitigated by `O_NOFOLLOW`).

---

- **SNMP `rwuser` — KEEP as-is (owner, 2026-08-19).** SNMPv3-USM-authenticated; `rouser` would
  remove SNMP-SET, a real feature.

---

- **`rwatch: FAILURE detected: warden-self-drop:<n>` is the feature reporting, not a fault.** Fires
  only with `rwarden_self=1` (opt-in router-origin filter); `<n>` = the router's own outbound packets
  dropped since the last tick. Classified FAIL rather than CRIT on purpose — only the operator can
  say whether a dropped flagged destination is the feature working. The BPM kernel dump beside it is
  rwatch's bounded first-failure collection, not part of the fault. To act on one: `grep
  REAPER-WARDEN-SELF` in syslog names the destination (usually a feed host, DDNS endpoint or VPN peer
  in a geo/threat set). *Possible UX work: name the top destination inline in the alert.*

---

- **Firewall rule negation / "not" on source and destination — considered, not building.** An empty
  source/destination already means "any", so an allowlist is an ordered pair (Accept to the object
  above Drop with the field empty), with Egress defaults and Zone policy for posture (*explicit rule
  > Egress default > Zone policy*). Documented in [`REAPER-GUIDE.md`](REAPER-GUIDE.md#413-rules).
  Not adding it: negation does not distribute over the engine's (src set × dst set) expansion, and it
  would add a second, less visible way to express default-deny. If the narrow "everything except X in
  one condition" case is asked for specifically: single-set objects only, groups refused loudly, the
  inverted match spelled out in Preview.

---

- **`dig` on the Network Tools page — considered, DECLINED (owner, 2026-08-24).** Security review:
  the Network Analysis page runs through the legacy `apply.cgi`→`SystemCmd` path, guarded by a
  per-page command whitelist + a strict input-character whitelist (`alnum : - _ . whitespace` only)
  + CR/LF rejection. Adding `dig` to that page's prefix whitelist induces **no** injection
  vulnerability — it rides the identical guard as the existing `nslookup`/`ping`/`traceroute`, and
  every shell metacharacter is already blocked. **But** `@` and `+` are not in the allowed charset,
  so `dig @server` and `dig +short/+trace/+dnssec` are refused as-is; a *full-featured* dig would
  require **widening that shared character filter**, which weakens the injection guard protecting
  the three existing tools — that WOULD be an induced vulnerability, so it is off the table. A
  restricted dig (record-type + reverse queries via the system resolver, charset unchanged) is safe
  but adds little over the busybox nslookup (LEDE) already shipped, which does query types
  (A/AAAA/MX/TXT/NS/SOA/PTR/CNAME/ANY) + retry/timeout/port/stats. And there is **no dig binary in
  the tree or toolchain** (no BIND, no ldns; busybox has no dig applet), so it would mean vendoring
  a new upstream package. Owner's call given all that: **don't add it.**

---

## Blocked by closed-source components — for ASUS / Broadcom

> Defects root-caused on RT-BE96U hardware that we **cannot** fix because the responsible code lives
> in prebuilt Broadcom blobs (`libtmctl.so`, `tmctl`, `rdpa.o`). Written so an engineer with the
> closed sources can act on it. Evidence captured on RT-BE96U (BCM6813 / 4916, XRDP).

### B-1. Classful QoS "WRR" (weighted round-robin) is non-functional on eth ports — every class silently runs strict-priority

- **Symptom.** With `qos_type=11` and any class set to a WRR weight, the weight never takes effect.

- **Reproduced on metal.** `tmctl setqcfg --devtype 0 --if eth0 --qid N --schedmode 2 --weight W`
  fails rc=108: `get_wrr_queue_idx: No free queue index between min[8] and max[8]` / `No place for
  new WRR queue, qid[N]` (chain `get_wrr_queue_idx` → `prepare_set_wrr_q_in_sp_wrr_mode_single_level`
  → `prepare_set_q_in_singel_level` → `prepare_set_q` → `tmctl_RdpaTmQueueSet`).

- **Root cause.** Every port's egress_tm is created with **`num_sp_elements = 8` of `num_queues = 8`**
  (`bdmf_shell … egress_tm` shows `mode: sp_wrr`, `num_queues: 8`, `num_sp_elements: 8` on every
  port), so no scheduler element is left for a WRR queue.

- **Why it is blob-gated.** `num_sp_elements` for eth ports is set inside the closed rdpa driver; the
  `porttminit --flag/--profileid` encoding is not visible. `rdpa_egress_tm.h` documents the valid
  splits (`{0,2,4,8,16,32}`) and marks `rdpa_tm_sched_sp_wrr` `\XRDP_LIMITED`.

- **What ASUS / Broadcom can do.** Create the eth egress_tm with `num_sp_elements = 4` (4 SP + 4 WRR),
  or expose a `porttminit` flag / TM profile that selects it; or document eth egress as SP-only and
  expose a `getportcaps`-style `maxSpQueues` so userspace can detect it.

- **Our mitigation (v2.5.4).** `rc/qos.c` forces strict priority and logs a notice if `qos_sched`
  requested WRR; the per-class scheduler/weight controls were removed from the UI.

- **Blocked by closed-source components**(#blocked-by-closed-source-components--for-asus--broadcom)).
  v2.5.4 removed the weight controls from the UI. A real fix needs a `porttminit`-level layout change
  that the closed rdpa driver owns; the standing decision is "UI option removed". Revisit only if
  Broadcom/ASUS expose the split.

---

### B-2.

- **[P3] Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul BSS is
  created even when every feature that would use it is disabled. Closed-source Broadcom blob; a
  boot-time suppression script did not work and was reverted. **[blocked — blob; risk-accepted]**

---

### B-3.

- **[P3] Guest Network Pro (AP-isolation SDN) breaks the 2.5G-1 LAN port when a manual WAN VLAN is
  also active — GT-BE98.** The port stops passing untagged main-LAN traffic (VID-52 tag required).
  On-metal captures proved there is **no userspace interface to read or program the switch VLAN/PVID
  table**. Workarounds: keep Guest Pro off the 2.5G-1 port, move the device, or tag it VID-52.
  Almost certainly present on stock too. Investigation: `GUESTPRO-2.5G-VLAN-PLAN.md` (private tree).
  **[blocked — blob; risk-accepted]**

---
