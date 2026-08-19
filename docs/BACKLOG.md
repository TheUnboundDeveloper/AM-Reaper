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
> not yet done** — which includes work that is *believed* done but unconfirmed: see
> [Pending verification](#pending-verification). Routine on-hardware validation of a feature
> nobody has questioned is still not tracked here; that section is for a specific change awaiting
> a specific confirmation.

---

## Contents

- [Open bugs / under investigation](#open-bugs--under-investigation)
- [Pending verification](#pending-verification)
- [UI / UX polish](#ui--ux-polish)
- [Features to add](#features-to-add)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Documentation](#documentation)
- [Known issues (cannot remediate — closed-source blob)](#known-issues-cannot-remediate--closed-source-blob)
- [Reported, investigated, closed as working-as-designed](#reported-investigated-closed-as-working-as-designed)

---

## Open bugs / under investigation

---

### SECURITY REVIEW 2026-08-18/19 — Phase 3 vulnerability pass: OPEN items only

> The fixes from this pass (the five corrected defective-reworks plus the new Phase 3 fixes) are
> recorded in the v2.5.0 **CHANGELOG** and **RELEASE-NOTES**, not here — this section carries only
> what is still open. **Committed on `be96u-only` as v2.5.0 (HEAD `8be2150520`), cut into the lean repo (patches 0463-0465); NOT yet pushed or released.**

**Before v2.5.0 can be cut — validation TODOs (applied but not yet hardware-proven):**

- **[P2-H6] QoS priority — REVERTED, needs a metal-test session.** The defect is real (libtmctl's own
  help says `lower value, lower priority`, and the live queues read back inverted) but the in-place
  renumber fix is rejected by the hardware (`Priority already in use`), so it was reverted to the safe
  (inverted-but-stable) baseline. The correct fix is `delqcfg`-all-then-`setqcfg`-all (clear every
  queue, then reassign), which can only be validated on hardware. Land it in a metal session.
- **[chpass CSRF] applied — validate on a real factory-reset flow before cut.** The `http_id` check is
  gated to the default-password window and `Reaper_FirstBoot.asp` was updated to send the token, but
  the first-boot credential path has a lockout history ([[firstboot-login-loop]]); confirm a clean
  factory-reset setup still completes before shipping.
- **General:** the whole batch is build-validated only (compiles + packages, MAKE_EXIT=0). Metal-test
  at least the QoS priorities, Gatekeeper enforcement on a guest/SDN network, the Warden manual-ban
  live-cut, and the first-boot password flow before cutting the rung.

**Still open (verified real, not fixed):**

- **[LOW, inherited]** OpenVPN `if` field in `libovpn/openvpn_setup.c` (`write_ovpn_dnsmasq_config`)
  unvalidated (newline). Marginal — OpenVPN config is entirely admin-controlled (no privilege gain)
  and it is inherited Merlin/OpenVPN code.
- **[POLICY]** SNMP `rwuser` left as-is (SNMPv3-USM-gated; `rouser` would remove SNMP-SET, a real
  feature). Change only if the owner wants read-only SNMP.
- **[COSMETIC]** esc() consolidation on 3 pages (`gkEsc`/`rwEsc`/`bwlEsc` — GK + Warden don't load
  `reaper_util.js`).

**Deferred per owner (2026-08-19): the `/tmp` systemic dir-ownership issue** — `mkdir(,0700)` return
ignored, owner never checked, rc `umask(0)` → `fopen("w")` is 0666; ~11 sites. Fix = ONE shared
validate-or-refuse helper (`lstat` → `S_ISDIR && uid==0 && !(mode&077)`), pattern already at
`reaper_fw.c:2071`; targeted `umask(077)` per daemon `main()` is the cheap partial (done for rtrafd).
Covers the `rmcpd` DIAG_OUT dir-perm item too.

**Investigated — NOT a bug (do not re-raise):** `Reaper_Firewall.asp` `v4_src`/`lw_sip`/`lw_dip`
"XSS" (renders via `td.textContent`); Warden `V6LAN`/`WANIPS`/`V6WAN` (the router's own ISP-assigned
addresses, not reachably poisonable); dnsmasq `/etc/hosts` IP field (an admin can already edit hosts
via custom config); `custom_clientlist` tail truncation (the reader uses `strdup`, no fixed buffer);
scrape-token "fail-open stub" (already `CRYPTO_memcmp` + `!want[0]` fail-CLOSED); store-chooser TOCTOU
(mitigated by the `O_NOFOLLOW` opens).

**ARCHITECTURAL — need owner decision (do NOT patch unilaterally):**

- **[HIGH] Firewall layer ordering.** `reaper_fw` is hooked (`-I` pos 1) AHEAD of Warden + Gatekeeper
  (last `-I` wins), and it emits terminal `ACCEPT` (they mostly `RETURN`), so an allow rule silently
  disables both — and the order is non-deterministic (`restart_gk` re-inserts at pos 1). Options: a
  shared `REAPER_HOOK` front chain with a defined order, OR convert `reaper_fw` user-ACCEPT to
  RETURN+allow-mark.
- **[HIGH/MED] Gatekeeper multi-network** (broader than the P2-H1 rework): even with the right bridge
  field, the per-network DNS carve-out / captive DNAT / L3 "internet-only" logic is all br0-only, and
  "internet-only" has no L3 leg so linked SDNs defeat it. A coupled redesign.

**Also carried:** ~96 MEDIUM/LOW findings from the Phase 1/2 (waste + data-flow) passes remain
unworked — catalogued in [`CODE-REVIEW-2026-08-18.md`](CODE-REVIEW-2026-08-18.md). Mostly
efficiency/dead-code, low security relevance.

---


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

  **Owner decision 2026-08-16: deferred to v2.4.6. NOT DONE — v2.4.6 was cut on 2026-08-17 without
  it, so this now rolls to v2.4.7.** The original reasoning still holds and is why it keeps
  slipping rather than being forgotten: it changes how a run is *bounded*, not just when a counter
  is cleared, and it needs the one thing that is hard to schedule — a **multi-run on-metal
  session**. One pass proves nothing, because the whole failure signature is "it depends how many
  tests you have run and whether the output stalls."

  **Do not defer it a third time on the same grounds.** Two rungs have now been cut around it. If
  the metal session is the blocker, the honest move is either to book it or to mark this
  **[blocked]** on that session — a fix that is always one rung away is not deferred, it is
  quietly abandoned.

  **Related, same counter, lower priority:** `level_err_cnt` is cumulative across a run and resets
  only on completion (line ~574), never on progress. Even with per-entry counting, 50 scattered
  non-fatal errors over a long run would terminate a test that is succeeding. Consecutive-error
  semantics are the right shape.

---

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

---

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

---

- **[P2] Dual-WAN failover: both NextDNS profiles receive DNS logs though only one WAN is live.**
  Secondary WAN (2.5 Gbps, DHCP, its own NextDNS profile) is active; the future primary (10 Gbps,
  PPPoE) is not yet connected. With only the secondary live, **both** NextDNS profiles show traffic;
  expected only the active WAN's profile to log. [Requires_Research]

---

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

---

**Traffic Analyzer Issue IPV6 Devices:**
- Also I have noticed on the traffic analyser page - the 1 year - one of my devices that didn't update until the ipv6 patch - is still on 186 MB and some other devices (probably the ipv6 devices aren't getting updated either) Did more testing, some devices update, some don't on the Year tab.

Edit: Looked like the *The Month* tab gets reset when you do a firmware update - but the ipv6 devices do get updated on that tab. The Last 24 hours and Last 14 days are getting updated fine and not resetting after an update :)

Edit 2: More testing, had moved from usb to jffs and the year tab seems to be updating now with that sticky device.

**Baby Jumbo Frames not Fixed on IPV6**
- Seems firmware is setting eth0 to 1508 but leaving vlan6 at 1500.

## Pending verification

*A change has been made and is believed to fix the problem. What is missing is **confirmation**,
and only two things count as confirmation: a report back from the person who reported it, or
on-hardware validation of a path the maintainer cannot exercise. Build-verified, replay-verified
and gate-passed are none of these — they prove a change is **in** the image, not that it **works**.*

*Every item names the evidence that would settle it, because "we think it's fixed" with no stated
test is how something sits here for five rungs. Items leave in one of two directions: **confirmed**
→ moved to the changelog and deleted from here; **not confirmed** → moved back to
[Open bugs](#open-bugs--under-investigation) along with what the attempt ruled out, which is often
worth more than the attempt itself.*

> **Nothing in this section is done.** A fix shipped is not a fix proven.

---

- **[P3] The local-build provenance call is implemented but has never run through the build
  engine.** `_reaper_build_lib.sh` gained a `gen_provenance.sh` call in `_rb_variant()` on
  2026-08-18, but the v2.5.0 test image was built with a plain `make` rather than through the
  engine, and the stamp was invoked directly with the same arguments instead. So the *fix* is
  verified in effect - the image carries a real patch count and base commit rather than dashes - but
  the *wiring* has not been exercised. It will be the first time a build goes through
  `build_be96u.sh` (or CI's container path, which already had its own call). Nothing to do but
  notice whether the "provenance stamp" line appears in that build log. **[owed]**

- **[P2] Confirm the Warden country counters actually attribute after the geo-first change.**
  The rule order was flipped on 2026-08-18 (owner decision) so the per-country rules are evaluated
  before the threat feed; both still jump to the same drop target, so this is attribution only. What
  needs eyes on a live box is that the numbers now behave as intended: with at least one country
  blocked **and** at least one feed enabled, the **Top Blocked Countries** table should start moving
  in step with the total, and the feed figure in the breakdown strip should flatten relative to
  before. If the country table still sits near zero while the total climbs, the reorder did not take
  and this belongs back in [Open bugs](#open-bugs--under-investigation).

  ```
  iptables -nvxL REAPER_WARDEN | head -20
  ```

  → the per-country `rw_g_<cc>` rules must appear **above** the `rw_threat` rule, and their packet
  counts should be non-zero on a box that was previously attributing everything to the feed.
  **Expect a discontinuity in banked history at this version** - that is the accepted cost of the
  change, not a fault. **[owed]**

- **[P2] The 1500-byte PPPoE MTU fix is not yet confirmed against the line that reported it.**
  v2.4.9 fixed three real defects underneath that report: the widened WAN port was never recorded,
  so it was reverted before pppd negotiated; the MTU and MRU both have to exceed 1492 before the
  RFC 4638 extension is requested at all, and the page let you raise only one; and a dual-WAN
  lookup always answered for the first connection. **What is not established is whether the
  reporter's provider supports the extension**, which decides whether 1500 was ever achievable on
  that line. The decisive evidence is one log line, now emitted on every PPPoE connect:

  ```
  grep -i "up with MTU" /tmp/syslog.log
  ```

  → `pppd: ppp0 up with MTU 1500` means it negotiated. `pppd: ppp0 up with MTU 1492 (requested
  >1492; peer declined RFC 4638)` means the provider refused, and no router-side change will alter
  that. Worth capturing alongside it: `ifconfig $(nvram get wan0_ifname) | grep -i mtu` should read
  **1508** while the session is up — if it reads 1500, the record-the-width fix is not holding and
  this belongs back in [Open bugs](#open-bugs--under-investigation). If the log reports 1500 and
  `ping -f -l 1472` still fails, the constriction is beyond the provider's access equipment and is
  not ours. **Do not use `logread`** — it returns empty on this platform by design; read the file.
  **[owed]**

- **[P2] The Call of Duty / UPnP report is not yet confirmed fixed.** v2.4.6 removed two real
  dead ends — the phantom `WANPPPConnection` advertisement and the IGD:2 device description on
  the default daemon — and both were verified in the build (preprocessor probe on each configure
  line). **Neither has been confirmed against the reporter's console.** The decisive evidence is
  one line, now emitted by both description versions:

  ```
  grep -i "IGD desc" /tmp/syslog.log
  ```

  → `IGD desc: served v<1|2> to <ip> (User-Agent: <string>)`. It answers three things at once:
  whether the console reached the description fetch at all (no line = discovery never got that
  far, which is what the `WANPPPConnection` fix addresses), which version it was served, and the
  User-Agent — the string needed to give a specific client the same per-client downgrade upstream
  hardcodes for Microsoft clients. **Do not use `logread`** — it returns empty on this platform by
  design (see the note in the wlcsm/netlink material); read the file.

  Also still to confirm: the reporter's `upnp_pinhole_enable`. With pinholes on, the router
  legitimately serves the IGD:2 description, which is the configuration that broke the PS5
  originally. **[owed]**

- **[P2] The AiMesh-node theming fix is build-verified only.** `bb580b6370` was reasoned from the
  whitelist in `web.c` and the lockdown branch in `httpd.c`, and the change itself is a
  three-line guard, but **no node has been flashed with it.** The recovery path also needs
  confirming: a node already stuck in the loop cannot be reflashed through its own interface, so
  it must be updated from the main router's AiMesh firmware flow. **[owed]**

- **[P2] Metal-validate the v2.4.4 IPv6 per-device attribution on a box that actually has
  IPv6.** The maintainer's RT-BE96U runs `wan_proto=dhcp` with no IPv6 up, so it cannot exercise the
  new path at all — which is precisely why the gap survived to a field report. The reporting
  **RT-BE88U** has native IPv6 with a delegated /56 and is the natural test box. What to check with a
  large download running: the device's row tracks the WAN line rather than showing only its ACK
  stream; a dual-stack device stays **one** row rather than splitting; and the neighbour table the
  collector reads (`nd_n`) agrees with `ip -6 neigh show dev br0`. The netlink reader was tested
  against seeded bridge and non-bridge neighbours on the host, and the code cross-compiles with zero
  new warnings, but neither proves behaviour on real traffic. **[owed]**

---

## UI / UX polish

---

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

---

- **[P3] Loader z-index raise is class-wide (watch-item).** The z-index bump was applied to the shared
  `.popup_bg` class, so it also raises `#hiddenMask` (the confirm-dialog backdrop) — benign/positive.
  Watch-item: if any apply/error flow ever surfaces an in-page (non-native) `form_style` modal *while
  the loader is displayed*, it would render behind the loader. Scope the class to `#Loading` only if a
  concurrent-modal case turns up. [watch — cosmetic]

---

- **[P3] SDN Wi-Fi-key mask can be bypassed by an SSID containing a literal `<b>` tag (watch-item).**
  The shared `state.js showWlHintContainer()` injects the SSID into `innerHTML` unescaped, so an SSID
  literally containing `<b>…</b>` would shift the bold-element index and leave the key visible. Only
  weakens the *new* privacy feature (never a crash or XSS), and the root cause is the pre-existing
  unescaped-SSID behavior in the **shared** `state.js` (out of scope of the mask's design). Optional
  hardening: mask the LAST `<b>` per row instead of index 1. [watch — cosmetic/privacy]

---

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

---

## Features to add

---

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

---

- **[P3] Firewall rule tracer (FIREWALL-PLAN Phase 3, the last unbuilt piece of it).** "Given a
  packet like *this*, which rule would match?" — a simulator that walks the committed config in C
  and reports the first match, rather than shelling out to iptables. Deferred from the firewall rung as
  the cheapest thing to leave: it is a diagnostic aid, not a control, so nothing is unusable without it.
  Everything else in Phases 2 and 3 shipped in v2.4.1 (`a103b59d6d` engine, `fa1e5d634f` Egress and
  Forwards tabs + backup/restore).

---

- **[P3] NORTH STAR — progressively replace stock GUI pages with Reaper-native ones.** Over time,
  migrate stock ASUS/Merlin pages to Reaper-native equivalents (own theme, de-clouded, only the
  functions we want exposed), as already done for Dashboard/QoS/Traffic/Wireless/GK/Warden/Devices/
  Advisor/Conn/QoSDiag/Analytics/Storage/Firmware (v2.3.1). The Firewall suite (above) is the next
  candidate. [ongoing]

---

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

---

- **[P3] Remote syslog push/fetch.** The router can already send its log to a remote collector
  (send-only). Add the ability to **push to / be fetched by** analytics systems (most SIEM pipelines are
  push-based). Pairs with the shipped health-metrics export (Data Export page). Also open from that
  feature: **wireless RSSI/PHY** per-device metrics were deliberately deferred and can be added later
  from the existing `web-broadcom-am.c` backend.

---

- **[P3] NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST baseline.

---

- **[P3] Diag: regulatory-mismatch warning.** Make `reaper_diag` (and possibly a Wireless-page hint)
  print an explicit `WARN: territory_code=EU/xx but wlX_country_code=US` line when the factory territory
  and per-radio country codes disagree — self-documents gray-market / region-switched units. Read-only
  compare, no behavior change (firmware must never auto-alter regulatory nvram). [shelved]

---

- **[P3] [owed] Translations for the Warden custom-feed labels — `RWDN_77`–`RWDN_85`, 9 keys.**
  Minted 2026-08-18 with the custom-feeds feature and English-seeded into all 25 packs (lockstep
  6638 → 6647), so nothing renders as a raw `<#KEY#>`; the 24 non-English packs carry English until
  a pass. **Constraint for whoever does it:** `RWDN_80`, `RWDN_81` and `RWDN_82` are used as HTML
  **`placeholder=` attribute values**, so their translations must not contain a double quote — the
  same hazard already recorded for `RFW_229`.

---

## Code quality / deferred (with reason)

---

- **[P2] [owed] Work the Phase 1 code-review findings — see
  [`CODE-REVIEW-2026-08-18.md`](CODE-REVIEW-2026-08-18.md).** 70 findings across the ~25k lines
  of Reaper-owned and Reaper-changed code (5 high, 32 medium, 33 low). Two of the five high
  items are already fixed in tree; the document carries the rest with file:line, evidence and a
  fix shape, plus a "checked and cleared" section so the next pass does not re-derive what was
  already settled.

  **The four cross-cutting themes are worth more than the individual items:** Reaper builds
  netfilter state one process at a time (~260 spawns for a 20-country Warden config, and both
  Warden and Gatekeeper tear down twice per arm) while `firewall.c` already uses
  `iptables-restore` in 15 places; `websWrite` is `fprintf`+`fflush` and three JSON escapers
  emit one character at a time through it, so a 250 KB response is ~250k syscalls; page polling
  is gated on `document.hidden` in three pages and not in the two heaviest; and the
  `reaper_util.js` consolidation stalled with 12 of 15 pages unable to reach it, leaving `esc()`
  in five variants with divergent null handling.

  Suggested order and the reasoning behind it are in §7 of the document. **[owed]**

---

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

---

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
  - `rwarden`'s updater writes `/tmp/rwarden/feed.$$` and `$TMP.rst` **as root**, into a directory
    created by `mkdir(RW_DIR, 0700)` that likewise ignores `EEXIST` and never checks owner or mode.
    The 2026-08-18 custom-feed work added another root-written file on this path; it does not create
    the class, and the same fix (b) covers it.
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

---

- **[P3] Two residual limits on Warden custom feeds, found by the 2026-08-18 adversarial pass and
  deliberately left.** Neither is a security hole; both are ceilings a user can reach by accident.
  - **`rw_threat` is created with ipset's default `maxelem` (65536).** A custom feed large enough to
    push the merged set past that makes `ipset restore` fail, which falls back to the per-entry loop,
    which then fails per entry once full. The result is a silently truncated block set with a log
    line, not an error the user sees. Curated feeds are nowhere near the limit; a user-chosen list
    can be. Fix shape: create the threat sets with an explicit `maxelem`, and surface the entry count
    the page already fetches against it.
  - **Update runtime is now user-extensible.** Eight custom feeds at `--retry 2 --max-time 40` add up
    to ~16 minutes to a refresh on top of the curated feeds and the country lists, and nothing locks
    the cron refresh against a concurrent "update now" from the page. Daily cron makes overlap
    unlikely rather than impossible. Fix shape: a lock file around the updater, and/or a lower
    per-feed timeout for custom entries.

---

- **[P3] `poll_fcache` O(n²)→hash pairing** (`rtrafd.c`). Bounded to ≤1536 flows every 5 s in the
  metal-validated per-client accounting path — a rewrite of a millisecond-scale loop isn't worth the
  regression risk. Revisit only if a flow-heavy box shows real cost. [shelved]

---

- **[P3] `poll_classes` 7× `tmctl` popen batch** (`rtrafd.c`). Metal measured 2–3 % CPU at the class
  cadence; treated as a non-issue. [shelved]

---

- **[P3] Theme-token vocabulary consolidation (remainder of D4).** The accidental same-name/different-
  value drift across the 15 Reaper pages was canonicalized in v2.2.7. Still deferred to the migration:
  the naming-vocabulary consolidation (`--panel2`/`--red*` → `--panel-2`/`--crimson*`) and the `--line`
  cream-vs-red divergence, both of which need per-page CSS **usage** rewrites (visual-regression risk).
  [owed — to migration]

---

- **[P3] [owed] Translations for the About page — `RABT_00`–`RABT_40`, 41 keys.** Minted with the
  page and English-seeded in all 25 packs (lockstep 6586 → 6627), so nothing renders as a raw
  `<#KEY#>`; the non-English packs simply carry the English text. Most of it is prose rather than
  labels — the credit lines in particular are written to land as jokes, so a mechanical translation
  will flatten them and is worse than leaving them in English until someone can do it properly.

---

- **[P3] [owed] Translations for the renamed bind-shim labels — `RTWK_03` and `RTWK_04`.** Renamed
  2026-08-17 ("Socket bind shim (nvram netlink)" plus an "On by default" note) and English-seeded
  into all 25 packs, so the 24 non-English packs currently show English for these two keys. Small,
  and it rides the next translation pass rather than needing one of its own.

- **[P3] Translations owed for the 2026-08-14 rung — Warden's router-self filter.** `RWDN_69`–
  `RWDN_72` (toggle label, description, and the two-part risk warning) are English-seeded in all 25
  packs. The packs stay in lockstep so nothing renders as a raw `<#KEY#>`; the non-English packs
  simply carry the English text until translated. *(`RWDN_73`–`RWDN_76`, the block-count breakdown
  labels, were translated in v2.4.5 when the breakdown became a visible strip.)*

---

- **[P3] `do_reaper_dev_cgi` function-local `static` snapshot arrays aren't re-entrant.** Latent only
  (httpd serialises these requests); a malloc refactor of the multi-return CGI would add leak risk to
  fix a can't-happen case. [shelved]

---

## Documentation

---

- **[P3] [owed] `Reaper_Firewall.asp` IPv6 protocol select — labels still to tokenize.**
  *(The P1 half of this is FIXED, 2026-08-18. The `<option>` elements now carry explicit
  `value="TCP|UDP|BOTH|OTHER"`, so the wire format is pinned independently of the visible label and
  tokenizing the labels can no longer change what is submitted.)*

  The original trap, kept because it explains why the values are pinned and must stay pinned: the
  options carried **no `value=`**, so the visible text *was* the submitted value — line 1129 reads
  it straight back with `$('v6_proto').value`, and it is serialized into `ipv6_fw_rulelist` as the
  fifth `>`-separated field. `rc/firewall.c` compares it with `strcmp(proto, "TCP"|"BOTH"|"OTHER")`
  (lines ~1520-1525, ~1602-1615, ~1659-1663), so a tokenized label would have sent a German user's
  `Beide` straight into the rule format — a functional break in 24 languages produced by an i18n
  change, with nothing in the build to catch it. **Do not remove those `value=` attributes.**

  **What is left:** tokenize the four labels. `RFW_252` already exists for "Both"; "Other" still
  needs a key. No longer blocking, and no longer dangerous — but it belongs with the `RFW_*`
  namespace pass rather than being done piecemeal, for the same reason `RFW_252` was left English.

---

- **[P2] [owed] Retranslate the three Traffic Analyzer accounting strings (v2.4.4).** `RTRF_45`
  (where the per-device numbers come from) was rewritten in all 25 packs and its 24 non-English
  translations were **deliberately discarded**: the old text said the numbers come from the
  accelerator table (untrue since v2.3.3) and that IPv6 is "not yet split per-device" (now the
  opposite of what the code does), so leaving the translations would have had 24 languages
  asserting the reverse of the truth. `RTRF_75` / `RTRF_76` (the "Upload only" badge and its
  tooltip) are new and English-seeded. All three read in English outside EN until a translation
  pass. Precedent for why this matters: the DE.dict `RQOS_117` drift left non-English users
  double-derating their download cap.

---

- **[P3] [owed] One remaining hardcoded UI string needs a new key.** The 2026-08-15 audit scanned
  all 19 Reaper pages for user-visible text without a `<#TOKEN#>`. **Four of the five findings
  shipped in v2.4.5**: `Drop`/`Accept` on the two firewall log-level
  selects reuse `RFW_139`/`RFW_138`; `QoS Diagnostics` reuses `RQD_00`, which already carried that
  exact wording and brings the page in line with every other Reaper `<title>`; the shell's brand
  link and content-iframe titles reuse `Reaper_c_dashboard` and `Settings`. Only **`RFW_252=Both`**
  had to be minted, and it is appended to all 25 packs (lockstep 6585 → 6586, key order verified
  identical across every pack).

  **Still owed:** a key for `OTHER` on the IPv6 protocol select. **No longer blocked** — the
  `value=` attributes were pinned on 2026-08-18, so tokenizing those labels can no longer change
  what is submitted. It now rides the `RFW_*` namespace pass rather than being done on its own.

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

---

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

---

- **[P3] Decide whether two internal docs should be published here.** `GUESTPRO-2.5G-VLAN-PLAN.md`
  and `CODE-AUDIT-2026-08-05.md` live in the private working tree and were referenced by dead links
  from this file and `CHANGELOG.md` (found 2026-08-13 by a 211-link sweep; those were the only two
  broken). **The links are already removed** and the prose names the docs as unpublished — so
  nothing 404s today. What remains is the owner call: copy them in, or leave as-is. Neither has been
  through a PII/scope review, which is why this is a decision rather than a cleanup.

---

- **[P3]** Document the non-functional retained features (the firmware update-check UI's stock pieces,
  the removed security-check UI) that are kept only for potential future use.

---

- **[P3]** Annotate the system defaults.

---

- **[P3]** Write a user guide for other users. *(Started 2026-08-14:
  [`FIREWALL-GUIDE.md`](FIREWALL-GUIDE.md) covers the eleven firewall tabs — what each is for, how
  best to use it, worked examples, and the non-obvious traps — and every tab's **?** button links to
  its section. The guide is tracked and pushed, so those links now resolve; the "404 until pushed"
  caveat that used to sit here is stale and has been removed. Extended 2026-08-15 with the
  allowlist recipe — "allow only these destinations, block everything else" — after a field request
  for rule negation turned out to be a documentation gap rather than a missing feature. The same
  treatment is owed for Warden, Gatekeeper, QoS, Traffic and the Devices pages.)*

---

## Known issues (cannot remediate — closed-source blob)

---

- **[P3] Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul BSS is
  created even when every feature that would use it is disabled, spamming the log with RADIUS codes for
  an unused radio. Traced to a **closed-source Broadcom blob**; a boot-time suppression script did not
  work and was reverted. [blocked — blob; risk-accepted]

---

- **[P3] Guest Network Pro (AP-isolation SDN) breaks the 2.5G-1 LAN port when a manual WAN VLAN is also
  active — GT-BE98.** Creating a Guest Pro network with AP isolation makes the 2.5G-1 port stop passing
  untagged main-LAN traffic (an 802.1Q VID-52 tag becomes required). On-metal captures proved there is
  **no userspace interface on this firmware to read or program the hardware switch VLAN/PVID table**, so
  neither a source fix nor a runtime correction hook is possible. **Workarounds:** keep Guest Pro off
  the 2.5G-1 port, move the device to another LAN port, or tag it VID-52; or avoid pairing a manual WAN
  VLAN with Guest Pro on that port. Almost certainly present on stock ASUS too (same blob). Full
  investigation: `GUESTPRO-2.5G-VLAN-PLAN.md` — **not published in this repo**; it lives in the private
  working tree. (Was a link here, which was dead for every public reader.) [blocked — blob; risk-accepted]

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report does not get re-investigated from scratch, and so the
reasoning survives the person who made the call.*

---

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

---

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

---
