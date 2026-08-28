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

*Updated 2026-08-28 — added the two `reaper_diag` counter defects (QoS readback truncation and
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

1. **[P1] UPnP silently half-works — daemon and firewall rules gate on different nvram keys**
   (confirmed on two boxes 2026-08-25; read side *and* the httpd Apply side now fixed in tree,
   both unbuilt — needs a build and a metal check).
   → [Open bugs](#open-bugs--under-investigation)
2. **[P2] Warden "crash" on the BE92U addon box** (amtm + Diversion update) — hypotheses ranked,
   tester data requested. → [Open bugs](#open-bugs--under-investigation)
3. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — needs a repro on
   v2.7.6+. → [Open bugs](#open-bugs--under-investigation)
4. **[P3] Code-review tail, batch B** (needs decisions / metal: `pinTarget()` 20→80 MHz intent,
   `do_reaper_conn_cgi` lock order, `rexport` mask loop, §2.1 iptables-restore batching).
   → [Code quality](#code-quality--deferred-with-reason)
5. **[P3] `RFW_*` IPv6 protocol labels** — the last translation residual: the "Other" label still
   needs a key minted, and the `RFW_*` proto set must be done as one job.
   → [Documentation](#documentation)
6. **[P2] QoS page live stats blank** — remediated for v2.7.8 (the poll never sent `http_id`, so the
   stats CGI refused it); needs the build and a look at the page.
   → [Open bugs](#open-bugs--under-investigation)

---

## Open bugs / under investigation

- **[P1] UPnP silently half-works: the daemon and the firewall rules gate on different nvram keys
  (confirmed on two boxes, 2026-08-25).** `start_upnp()` gates on the per-unit
  `wan<N>_upnp_enable`; `nat_setting()`/`nat_setting2()` gate the `-A VSERVER -j VUPNP` and
  `PUPNP` hooks on the generic `upnp_enable`. Nothing keeps the two in sync: `wan_defaults()` is
  "assign none-exist value" and copies the **defaults-table** value rather than the current
  setting, so once the per-unit key exists it is frozen, and the only writer is httpd's `wan_`
  propagation (`web.c:4541`), gated on `unit != -1` and on `validate_apply_input_value()` — which
  lives in the closed `priv_webapi.o`. Either half can be on while the other is off, and every
  status surface still reports UPnP healthy. Seen both ways:
  - **RT-BE88U v2.7.6 (field):** daemon up with real console mappings in `VUPNP` (udp 3074/9308),
    but `VSERVER -j VUPNP` **absent** — nothing was ever DNATed, and the console reported NAT type
    Moderate with the GUI listing the mappings as healthy. This was the reported bug; Warden was
    ruled out (filter-only, `INPUT`/`FORWARD`, never the nat table).
  - **RT-BE96U v2.7.7 (owner):** the jump installed and passing traffic, but the daemon never
    started — no `/tmp/upnp.leases`, `VUPNP` empty.

  **Fix in tree, not yet built:** both halves now derive from shared `upnp_wan_unit()` /
  `upnp_enabled()` helpers in `rc/services.c`, with all five gates in `rc/firewall.c` repointed at
  them, so the two cannot disagree by construction. **Field workaround meanwhile:**
  `nvram get upnp_enable; nvram get wan0_upnp_enable` — set whichever reads 0, `nvram commit`,
  then `service restart_firewall` (or `restart_upnp`).

  **The Apply half is now fixed in tree too (unbuilt).** `validate_apply()` gains an explicit
  `wan_upnp_enable` branch ahead of the generic `wan_` propagation: it resolves the unit from
  `wan_primary_ifunit()` when `wan_unit` is absent, validates the value as a boolean itself, and
  writes **both** `wan<N>_upnp_enable` and the generic `upnp_enable` in lockstep. The page only
  ever posted the unindexed `wan_upnp_enable`, so the generic key had **no writer on this path at
  all** — that part is proven from source and is fixed. Reading the apply loop also eliminated
  several suspects: the loop iterates `router_defaults`, so field order in the form is irrelevant
  and `wan_unit` (defaults.c:2494) is reached before `wan_upnp_enable` (2603); `nvram_check()`
  rejects only on over-length, so a 1-char boolean passes; and the radios are enabled for
  dhcp/pppoe/static/bridge by `fixed_change_wan_proto_type()`, so they do post. That leaves
  `validate_apply_input_value()` (closed `priv_webapi.o`) as the only unexplained gate — the new
  branch no longer depends on it either way. **Which gate was actually blocking on metal is still
  unproven**; confirm on the next flash by toggling UPnP and checking that `nvram get upnp_enable`
  and `nvram get wan0_upnp_enable` both flip. **[owed — build + metal confirmation]**

---

- **[P3] Gatekeeper: the 5 s poll closed an open access-level menu — remediated for v2.7.8
  (owner report, 2026-08-26).** `gkPaint()` → `gkRender()` rebuilds `#devrows` with a whole-table
  `innerHTML` assignment every poll, so a row's `.rowsel` `<select>` was destroyed with its row and
  the native popup shut mid-choice. Same class as rule 40's dashboard dropdown trap, and a
  signature compare would not have covered it — the rows carry relative "last seen" text that
  changes on most polls. **Fixed in tree for v2.7.8:** an open `<select>` holds focus, so
  `gkEditing()` tests focus and `gkRender()` defers the *paint* (never the fetch, so `GK.st` stays
  current), flushing on `focusout`; `gkAct()` blurs first so a committed choice still repaints at
  once; and the `s_def` / `s_hours` value writes are guarded the same way. `www`-only, no dict
  change. Verified without a build: `reaper_langcheck` 0 breakers, both edited pages structurally
  balanced. **[owed — build + a look at the page]**

---

- **[P2] QoS page: the live per-class stats never populated — remediated for v2.7.8
  (found 2026-08-26 on RT-BE96U v2.7.7 metal).** The Traffic Manager page showed no rate and no
  drop figures on any of the five class rows, on a box where the engine was demonstrably working
  (`qos_type=11` armed, port shaper at `qos_obw`, class queues at `priority` 5→1, live `tmctl
  getqstats` deltas on qid3 and qid5, zero drops). The engine was never the problem: `pollStats()`
  in `Reaper_QoS.asp` requested `/reaper_qos_stats.cgi?_=<ts>` with **no `http_id`**, and v2.5.0
  (`patches/0464`) had added a mandatory `http_id` CSRF gate to `do_reaper_qos_stats_cgi` —
  matching the other `popen()`ing Reaper readers. Without the token the handler returns
  `{"enabled":0,"error":"auth"}` before running a single `tmctl`, and the page's `if (!d.enabled)
  return;` leaves every cell blank. The page-side URL had been unchanged since v1.2.8
  (`patches/0131`) and was never updated when the gate landed, so the panel had been dead since
  **v2.5.0**. `Reaper_QoSDiag.asp` already sent the token, which is why the diagnostics page kept
  showing the same data.
  **Fixed in tree for v2.7.8:** the poll now sends
  `?http_id=<% nvram_get("http_id"); %>`, the same idiom as `Reaper_QoSDiag.asp`. `www`-only,
  no dict change. `Reaper_Conn.asp` polls without a token too but is unaffected —
  `do_reaper_conn_cgi` reads `/proc` and has no gate. **[owed — build + a look at the page]**

---

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

## Documentation

---

- **[P3] Translations — one residual left.** The functional-token pass across all 24 languages
  **shipped in v2.7.7**. The RABT credits and jokes (`RABT_16`–`RABT_26`, `RABT_41` "GOAT
  whisperer") stay English **by choice** — prose and humour where a mechanical pass reads worse
  than English; the `RABT_29/30/32/33` taglines are translated. That is a settled decision, not
  owed work. What remains:
  - **`RFW_*` IPv6 protocol labels on `Reaper_Firewall.asp`.** `RFW_252` ("Both") is translated, but
    the "Other" label **still needs a key minted**; do the `RFW_*` proto set as one job, not piecemeal.
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

- **[P3]** Document the non-functional retained features (stock pieces of the firmware update-check
  UI, the removed security-check UI) kept only for potential future use.
- **[P3]** Annotate the system defaults.
- **[P3]** User guides. [`FIREWALL-GUIDE.md`](FIREWALL-GUIDE.md) covers the eleven firewall tabs
  (every tab's **?** links to its section; extended with the allowlist recipe after a field request
  turned out to be a documentation gap). The same treatment is owed for **Warden, Gatekeeper, QoS,
  Traffic, Devices** and **Policy Routing** (`VPN-ROUTING-GUIDE.md`, linked from the page's ? dot —
  404s until written and pushed). **[owed]**

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
  `Reaper_Wireless.asp:547` `pinTarget()` is an identity function (the "← original" annotation is
  dead) — the intended 20→80 MHz block substitution was never implemented: implement (metal) or
  delete the annotation; `rexport.c:77` O(devices) MAC-mask rewrite; `rwarden.c:1117` stats.sh chain
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
  > Egress default > Zone policy*). Documented in [`FIREWALL-GUIDE.md`](FIREWALL-GUIDE.md) §Rules.
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
