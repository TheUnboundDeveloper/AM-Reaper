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

> **Shipped since (all built on RT-BE96U, in the Changelog / Release-Notes; NOT yet cut as public CI releases):**
> **v2.5.4** — the **P2-H6 QoS priority inversion**, the **speed-test `level_err_cnt`** counter, the
> **QoS WRR weight UI** removal, the **Wireless auto-scan auto-pin**, the **Warden blocklist maxelem**,
> the **SDN Wi-Fi-key mask** hardening, and the Firewall (245) + About + Warden **translations** (v2.5.4
> is on metal; only the P2-H6 **drain-under-load** confirmation still sits under
> [Pending verification](#pending-verification)). **v2.5.5** — the **ipset Policy Routing** engine and the
> **PPPoE post-boot re-dial** (bounce). **v2.5.6** — the **Policy Routing editor page** (`Reaper_VPNRouting.asp`).
> **v2.5.7** — five **security-audit** hardening fixes (`B1-SEC-003` OOB-read guard, `A1-SEC-003` gk-baseline
> skip, `A1-SEC-004` usbkey CRLF strip, `B1-SEC-006` ejusb guard, `A4-UI-006` chpass POST). The entries that
> follow are genuinely still open.
>
> **➤ Next highest-priority open ticket: the `[HIGH]` Firewall layer ordering** item under
> *ARCHITECTURAL — need owner decision* below. `reaper_fw` is hooked ahead of Warden and Gatekeeper
> and emits a terminal `ACCEPT` (they mostly `RETURN`), so a single allow rule can silently disable
> both — and the hook order is non-deterministic. It is blocked on an **owner decision** (a shared
> `REAPER_HOOK` front chain with a defined order, vs. converting the `reaper_fw` user-ACCEPT to
> RETURN+allow-mark). The other big-ticket open items are the `[HIGH/MED]` **Gatekeeper multi-network**
> redesign (also owner-decision) and the **AiMesh-search node-discovery** gate (needs mesh hardware);
> the remaining data-flow and efficiency findings are lower severity.

### SECURITY REVIEW 2026-08-18/19 — Phase 3 vulnerability pass: OPEN items only

> The fixes from this pass (the five corrected defective-reworks plus the new Phase 3 fixes) are
> recorded in the v2.5.0 **CHANGELOG** and **RELEASE-NOTES**, not here — this section carries only
> what is still open. **The v2.5.0 fixes are cut into the lean repo (patches 0463-0465); everything since — the v2.5.1 pre-public hardening, the v2.5.2 metal fixes, and the v2.5.3 code-review batch — lands in the v2.5.3 cut (patches 0466-0471). NOT yet pushed or released.**

**Before v2.5.0 can be cut — validation TODOs (applied but not yet hardware-proven):**

- **[P2-H6] QoS priority inversion — FIXED, metal-validated 2026-08-20 (staged for v2.5.4, pending flash).**
  Confirmed on the lab RT-BE96U: `tmctl` priority is a rank where a HIGHER value is served first
  (`priority = <0,7>, lower value, lower priority`), and the class queues shipped with `priority == qid`,
  so class 1 (qid1, "served first") was drained second-to-last. `delqcfg` exists; an in-place renumber is
  rejected (`Priority already in use`), so the fix deletes all five class queues and recreates them with
  `priority = 6 - qid` (q1=5 … q5=1), leaving reserved qid0/qid6 at stock — the only sequence the TM
  accepts, and the recreated priority survives the later `setqdropalg`/`setqshaper` (all verified on
  metal). Start and stop paths in `qos.c` both updated; QoSDiag's qid-based label is now correct with no
  change. Owed: on-flash confirmation of the drain order under real classified load.
- **[UI addressed v2.5.4 → weights removed from the QoS page ([Pending verification](#pending-verification)); root cause + the ASUS-actionable fix are in B-1 under *Blocked by closed-source components*.] QoS WRR weights (`qos_sched` `w<N>`) are structurally unsupported on RT-BE96U — silently no-op.**
  Discovered during the P2-H6 metal session: any WRR `setqcfg` fails with `get_wrr_queue_idx: No free
  queue index between min[8] and max[8]` / `No place for new WRR queue` (rc=108). **The pre-fix shipping
  code's own WRR emission fails identically**, so WRR weights have never applied — classful QoS has always
  run all strict-priority. All eight hardware queue indices are consumed by the SP queues (qid0–6 +
  reserve), leaving none to allocate a WRR queue. The v2.5.4 P2-H6 fix forces SP and logs a one-line
  notice when `qos_sched` requests WRR. A real fix needs a `porttminit`-level queue-layout change (fewer
  SP queues to free a WRR slot) or removing the WRR option from the QoS UI. Likely affects all siblings
  (same BCM491x TM). **[owner decision: fix layout vs drop the UI option]**
- **[chpass CSRF] applied — validate on a real factory-reset flow before cut.** The `http_id` check is
  gated to the default-password window and `Reaper_FirstBoot.asp` was updated to send the token, but
  the first-boot credential path has a lockout history ([[firstboot-login-loop]]); confirm a clean
  factory-reset setup still completes before shipping.
- **General:** metal-validation is now partial — v2.5.2 **confirmed on RT-BE96U** the Gatekeeper
  first-seen fix and the QoS shaper behaviour. Still build-validated only, and owed a metal pass: the
  QoS **priority** inversion (P2-H6 above), Gatekeeper enforcement on a guest/SDN network, the Warden
  manual-ban live-cut, the first-boot password flow, and the **IPSec resurrection** (v2.5.3 stages
  `starter`/`stroke`/`charon`/`swanctl` — confirm a tunnel establishes; see the IPSec item below).

**Shipped in v2.5.1 (cut into the lean repo via the v2.5.3 series, patches 0466-0471):**

- **[LOW, inherited] OpenVPN `if` newline — FIXED.** `write_ovpn_server_dnsmasq_config`
  (`openvpn_setup.c:101`) gates the `vpn_serverN_if` value through `ovpn_host_safe` before splicing
  it into the dnsmasq `interface=` directive — a newline can no longer inject config. Normal
  `"tun"`/`"tap"` pass; a bad value emits nothing (degrade-safe).
- **[COSMETIC] esc() consolidation — FIXED (3/3 pages).** `Reaper_GK.asp` + `Reaper_Warden.asp`
  gained the `<script src="/reaper_util.js">` tag; `gkEsc`/`rwEsc`/`bwlEsc` now delegate to the
  shared `window.esc`. `ReaperEsc` is byte-identical to all three (same regex/map/null→empty), so
  no behaviour change. §2.4 consolidation is now complete.

**Shipped in v2.5.3 — pending metal confirmation:**

- **[P1] IPSec Server — SERVER SIDE METAL-CONFIRMED on v2.5.4 (2026-08-20); client-tunnel-establishes still owed.**
  The strongSwan runtime (`/usr/lib/ipsec/{starter,stroke,charon}` + `swanctl`) was **absent from
  every prior shipped image** — a stale-configure trap left the daemons un-staged, so all three IPSec
  features were dead on hardware regardless of configuration. v2.5.3 first staged them; **v2.5.4 metal
  test (lab RT-BE96U): enabling IPSec Server brings the whole control plane up** — `starter` + `charon`
  running, `/var/run/charon.vici` present, **UDP 500 + 4500 bound by charon** (IPv4 + IPv6), and
  `swanctl --list-conns` shows BOTH profiles loaded from the ASUS config: `Host-to-Net` (IKEv1, PSK +
  XAuth) and `Host-to-Netv2` (IKEv2, cert + EAP-MSCHAPv2). strongSwan 6.0.4. So the nvram-profile →
  `rc_ipsec` → charon config path works end-to-end and the server is ready for clients. **Still owed:**
  (a) a client actually establishes a tunnel (SA goes `up` — owner to connect a phone/laptop); (b) the
  **IPSec client** (connect-out) and **Instant Guard** pairing paths, still un-exercised. Build/stage
  fix only — no config-page change. **[owed — client-connect confirmation + IPSec-client/Instant-Guard]**
- **The v2.5.3 code-review batch** — admin-management RETURN scoped to INPUT, port-forward
  empty/comma guards, atomic Gatekeeper + Warden `apply.sh`, the Warden fold/stats shared lock, the
  analytics-export staleness gate, the firewall zone-matrix save cap 2048→8192, the 11
  `reaper_export_*` declarations, and the left-nav rail geometry standardized to the Dashboard — is
  build-verified green. The firewall-emission changes owe a metal glance on the next flash. **[owed — metal glance]**

**Policy decision (2026-08-19, owner):**

- **[POLICY] SNMP `rwuser` — KEEP as-is.** SNMPv3-USM-authenticated (no unauthenticated exposure);
  `rouser` would remove SNMP-SET, a real feature. No code change.

**Deferred per owner (2026-08-19): the `/tmp` systemic dir-ownership issue** — `mkdir(,0700)` return
ignored, owner never checked, rc `umask(0)` → `fopen("w")` is 0666; ~11 sites. Fix = ONE shared
validate-or-refuse helper (`lstat` → `S_ISDIR && uid==0 && !(mode&077)`), pattern already at
`reaper_fw.c:2071`; targeted `umask(077)` per daemon `main()` is the cheap partial (done for rtrafd).
Covers the `rmcpd` DIAG_OUT dir-perm item too. **The sticky-bit half is already done** — `chmod("/tmp", 01777)` at `init.c:25607`, shipped in v2.5.0; what remains deferred here is the narrower owner-validation hardening (candidate-b).

**ARCHITECTURAL — need owner decision (do NOT patch unilaterally):**

- **[HIGH] Firewall layer ordering.** `reaper_fw` is hooked (`-I` pos 1) AHEAD of Warden + Gatekeeper
  (last `-I` wins), and it emits terminal `ACCEPT` (they mostly `RETURN`), so an allow rule silently
  disables both — and the order is non-deterministic (`restart_gk` re-inserts at pos 1). Options: a
  shared `REAPER_HOOK` front chain with a defined order, OR convert `reaper_fw` user-ACCEPT to
  RETURN+allow-mark.
- **[HIGH/MED] Gatekeeper multi-network** (broader than the P2-H1 rework): even with the right bridge
  field, the per-network DNS carve-out / captive DNAT / L3 "internet-only" logic is all br0-only, and
  "internet-only" has no L3 leg so linked SDNs defeat it. A coupled redesign.

**Also carried:** the Phase 1/2 (waste + data-flow) review findings remain **unworked** — **70
from Phase 1** (inefficiency / dead code: 5 high, 32 medium, 33 low) and **44 from Phase 2**
(function-flow / data-passing; the doc's own prose says 38 in one place — a minor internal
inconsistency). Mostly efficiency/dead-code, low security relevance. Catalogued in
`CODE-REVIEW-2026-08-18.md`, which lives in the **private working tree** (`asuswrt-merlin.ng/docs/`),
not synced into this lean repo — so that link resolves only in the mirror. (The earlier "~96"
figure here was an undercount.)

---

- **[FIXED v2.5.4 → [Pending verification](#pending-verification); mechanism kept here.] Speed test: `level_err_cnt` was consumed once per POLL, not once per error — this is
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

  - **Field Reports** Users in the field report beign able to fine mesh nodes and connect to them 
    just fine. This bug may have been fixed due to other corrective changes.

---

- **[FIXED v2.5.4 → [Pending verification](#pending-verification); detail kept here.] Wireless Quality Auto Scan pins the winner by itself; it should not.** Owner 2026-08-13:
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

- **Flash Steps** If a user cancles a firmware upgrade by slelecting no or cancle the page does 
  not return to previous state and has to be reloaded for the buttons work again.

---

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

  **[P2] Corroborating report — GT-BE98, v2.5.x, 2026-08-20 (deterministic variant of the above).**
  Field tester: on **router reboot**, the 10 Gbps WAN link drops to ~2.5 Gbps and pings to 1.1.1.1 /
  8.8.8.8 time out continuously; **restarting the ONT *after* the router has fully booted** restores
  full 10 Gbps and connectivity every time. The *ordering* (ONT must come up after a stable router
  PHY) and the **10G→2.5G rate drop** sharpen root cause **#1** above: this is a **boot-order
  link-training race** — the 10G WAN PHY negotiates with the ONT while still training, the ONT
  latches a lower NBASE-T rate and/or a stale UNI/PON session, and never re-trains up; an ONT
  power-cycle against the now-stable PHY re-negotiates clean. **Not our code path** — Reaper carries
  zero patches touching WAN link-speed / PHY autoneg (inherited stock Broadcom); this pattern is also
  widely reported on stock ASUS 10G-WAN + fiber-ONT setups, so it is almost certainly
  inherited/hardware, not a v2.5.x regression.

  **Proposed Reaper-side mitigation (automates the ONT-restart workaround):** after the router
  reaches a fully-booted, stable state, **bounce the WAN link once (down→up)** to force a fresh
  re-negotiation against the trained PHY — reproducing what the ONT power-cycle does, with no user
  action. Gate behind a knob (default on for 10G-WAN models; GT-BE98 first), with a short settle
  delay after boot-complete; if a DHCP re-kick proves necessary, chain `restart_wan_if` after the
  link comes back at 10G. **Do not build blind** — request three data points captured **in the bad
  state** (after router reboot, before the ONT restart): (1) WAN link speed —
  `cat /sys/class/net/$(nvram get wan0_ifname)/speed` (confirms `2500` vs `10000`); (2) whether WAN
  gets an IP — `nvram get wan0_ipaddr` (link-up-no-DHCP vs DHCP-ok-upstream-dead); (3) which 10G port
  is WAN (SFP+ combo vs 10GBASE-T) and the ISP / ONT model. That triage decides link-bounce-alone vs
  bounce-plus-DHCP-re-kick.

  **DIAG EVIDENCE 2026-08-20 (two sanitized REAPER-DIAG v1.2.0 captures, GT-BE98 Reaper_v2.5.3_noMCP,
  EU/IT PPPoE-over-VLAN835).** The WAN is **`eth0`, a 10GBASE-T RJ45 port** (Speed Caps
  `10G:5G:2.5G:1G:100M`, AN on; `netdev path vlan835 → eth0`, PPPoE, `ppp0 up with MTU 1492`).
  **CORRECTED READING (owner, 2026-08-20 — an earlier draft here wrongly called this "flapping =
  10GBASE-T marginality"; withdrawn).** Capture #1 (fresh boot, 3-min uptime) shows `eth0` coming **up
  once at 10G with NO drops** and probes Cloudflare 0% / **Google 33%** (mild). Capture #2 shows `eth0`
  drop→up **twice in quick succession at ~13:42, then stay stable**, with probes **0% loss to BOTH**
  Cloudflare and Google immediately after. That clustered pair-of-transitions-then-clean is almost
  certainly **the tester rebooting the ONT (his known fix), not the chronic fault** — an ONT power-cycle
  bounces the UNI link a couple of times, then the loss clears, which is exactly the dmesg shape. Each
  bounce does fire stock `wanduck → restart_wan_if` + a PPPoE re-dial (`Unable to complete PPPoE
  Discovery` on the first try, then success), but that is the *recovery*, not the defect. Chronic 10G
  marginality would scatter flaps over time and leave the probes lossy; instead they went to 0%.

  **So neither capture catches the bad state.** #1 = fresh boot (only a mild Google 33% on a 3-ping
  sample); #2 = *after* the ONT reboot (clean). The chronic symptom — continuous dropped packets after
  a **router** reboot, cured by an **ONT** reboot, with the **link staying up** — best fits **ONT/OLT
  session staleness** (root cause **#1** above): the OLT holds a stale MAC-bound session after the
  router re-PPPoEs and drops packets until the ONT is power-cycled. Still **not Reaper** (no WAN-PHY /
  session code) and it does **not** require a link flap. Red herrings confirmed: `default gateway
  loss=100%` is a normal ICMP-filtered PPPoE peer (`192.168.100.1`) — the internet DNS probes are the
  real signal; `services: apply rules error(24267)` is a transient during WAN bring-up.

  **Decisive next capture (ask the tester):** run the diag **while the packets are dropping — after a
  router reboot, BEFORE he reboots the ONT.** That one shows the real signature at once: `eth0` link
  state (stable 10G? 2.5G? actually flapping?), the connectivity-probe loss (should be high), and
  whether the WAN has an IP / PPPoE is up. Everything so far is a capture of the *recovery*, not the
  fault.

  **Mitigation, re-reconsidered:** because an ONT-side link bounce demonstrably cleared it (loss → 0%
  right after the 13:42 transitions), the original **router-side post-boot WAN link bounce (`eth0`
  down/up, ± a `restart_wan_if`)** is back to being the plausible automation of the ONT-reboot fix — IF
  a UNI-port transition prompts the OLT to re-establish the session. Confirm the bad-state signature
  first; forcing 2.5G/5G is only relevant if that capture actually shows a flapping/mis-trained link
  rather than a stable-but-lossy one. **[owed — tester: capture DURING the dropped-packet state, before
  the ONT reboot]**

  **MITIGATION IMPLEMENTED (staged, next build) — 2026-08-20, owner-requested.** Because the evidence
  best fits **session staleness with the link staying up** (not a PHY rate mis-train), the mitigation
  built is the **PPPoE-re-dial variant, not an `eth0` link bounce**: a one-shot **PPPoE stale-session
  bounce** riding the existing rwatch cron tick (`rc/rwatch.c`, "reaper v1.9.2" block; knob
  `reaper_wanbounce_enable` default ON in `shared/defaults.c`). Logic: **once per boot** (tmpfs latch
  `/tmp/reaper_wan_bounced`), after rwatch's 300 s boot grace, if the primary WAN is **`proto==pppoe`
  and `wanX_state_t==2` (link up) yet no internet is reachable** (its own probe: `wandog_target`, then
  1.1.1.1, then 8.8.8.8 — a bounce fires only if **all three** fail, so one dead host can't false-trip),
  it sends **`SIGHUP` to `/var/run/ppp-wanX.pid`** — the least-disruptive re-dial (keeps NAT/firewall/
  routes) — forcing the OLT to drop the stale session and accept the new dial. This automates the
  tester's manual ONT power-cycle for the *session-staleness* path. **Deliberately NOT an `eth0` down/up**
  (that PHY-retrain variant is only warranted if the owed bad-state capture shows a flapping/mis-trained
  link). Shell syntax validated (`sh -n` + `dash -n`). **[owed metal: confirm on a box that reproduces —
  a `logger -t rwatch` line records each fire; and still get the DURING-bad-state capture to confirm the
  root cause and whether a link bounce is additionally needed.]**

---

**Traffic Analyzer Issue IPV6 Devices:**
- Also I have noticed on the traffic analyser page - the 1 year - one of my devices that didn't update until the ipv6 patch - is still on 186 MB and some other devices (probably the ipv6 devices aren't getting updated either) Did more testing, some devices update, some don't on the Year tab.

Edit: Looked like the *The Month* tab gets reset when you do a firmware update - but the ipv6 devices do get updated on that tab. The Last 24 hours and Last 14 days are getting updated fine and not resetting after an update :)

Edit 2: More testing, had moved from usb to jffs and the year tab seems to be updating now with that sticky device.

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

### v2.6.0 (2026-08-21) — QoS Classful queue rebuild, awaiting confirmation

- **[P1] GT-BE98 (and any port that rejects the recreate) keeps IPv4 with QoS Classful on.**
  `rq_rebuild()` in the generated `/tmp/qos_hwc.sh`. **Settles when** the reporter, on a v2.6.0
  GT-BE98 image with `qos_type=11`, has IPv4 after boot AND `tmctl getqcfg --devtype 0 --if eth0
  --qid N` answers for N=1..5. Expected syslog on that box: `hwqos: setqcfg qid 1 priority 5
  REJECTED` + `class queues restored at the stock priority layout`, with NO `FATAL` line. A
  `FATAL` line means even the bare recreate failed and the delete itself must be abandoned on that
  port — report it. Also worth knowing WHY the recreate is rejected there (run the failing
  `tmctl setqcfg` by hand without `2>/dev/null`) so the priority correction can be made to work on
  that port rather than just fail safe. **[owed — reporter, GT-BE98 metal]**
- **[P2] RT-BE96U unchanged in behaviour.** **Settles when** a v2.6.0 BE96U shows qid 1..5 at
  priority 5..1 after `restart_qos` and no `hwqos` fallback line. **[owed — metal]**

### v2.5.9 (2026-08-21) — the trusted tester's batch, awaiting confirmation

- **[P1] Warden country sets populated after a reboot.** Per-set, members-only cache replay + no
  empty-set cache overwrite + `maxelem 262144` on `rw_g_*`. **Settles when** the reporter (or any
  box with countries selected) reboots on this image and `ipset -t list rw_g_<cc>` shows a non-zero
  "Number of entries" for every selected country, with no `rwarden: cache restore for set` lines in
  the log; the Warden tile should read the prefix count, not amber. First boot after upgrading from a
  pre-v2.5.9 cache is the interesting case. **[owed — reporter, reboot + ipset readback]**
- **[P2] Wireless AiMesh node shows its backhaul band on Devices, with the AiMesh Node chip.**
  `rdev_node_classify()` reads `CM_CLIENT_TABLE` by `realMacAddr` and maps `activePath`
  (2 → 2.4 GHz, 4/8 → 5 GHz, 128 → 6 GHz, 512 → MLO, 1/16/32/64 → Wired). **Settles when** the
  reporter's node row shows the band and the orphan backhaul-STA row is gone; a *cabled* node must
  still read Wired. **[owed — reporter, Devices page]**
- **[P2] Addons rail identical on dashboard and shell.** Shared `ReaperAddons` parser. **Settles
  when** a box with amtm/scMerlin-style addons shows the same entries, labels and order-within-group
  on the dashboard and on any framed page, including an external Help link opening in a new tab on
  both. **[owed — reporter, a box with addons]**
- **[P2] Policy Routing works with the Firewall engine OFF.** `reaper_fw_sets_only()` is called from
  `start_reaper_pbr()`. **Settles when** a routing rule keyed on a domain list steers traffic on a
  box with `reaper_fw_enable=0`: `ipset list rwfw_<list>` is populated, `iptables -t mangle -vnL
  REAPER_PBR` shows the match loading (not "set does not exist"), and `cru l` shows
  `reaper_fw_dns`. **[owed — metal, fw off]**
- **[P2] Domain lists survive a reboot.** `/jffs/reaper_fw/sets/rwfw_<name>` written after each
  resolver pass, replayed at set creation. **Settles when** after a reboot (before any client DNS
  lookup) `ipset -t list rwfw_<list>` is already non-empty. **[owed — metal, reboot]**
- **[P3] Edit flows on the Firewall page (8 lists) and Policy Routing (rules + domain lists) —
  page check.** Modify → Save replaces in place, Cancel restores Add, order/enable/comment preserved
  on rules, a renamed domain list updates the rules that referenced it. Mock-renderable except the
  CGI saves. **[owed — page check]**

### v2.5.8 (2026-08-20) — upstream 3006.102.8_4 alignment, awaiting confirmation

- **[P2] UPnP gaming fix (completed revert of the Asus jump patch) — needs a real UPnP game.** The
  FORWARD→FUPNP half of Asus patch `a1ce74be78` is now removed, completing the revert Merlin shipped
  as `085a2f2768` (the PREROUTING→VUPNP half was already reverted here on 2026-08-13). **Settles
  when** a game that forwards its port via UPnP (the PS5 is the known reproducer in this house)
  accepts inbound connections with UPnP enabled — the symptom upstream fixed was "cannot connect to
  gaming servers if a game forwards a port through UPnP". Also worth a glance:
  `iptables -t nat -vnL PREROUTING | grep VUPNP` and `iptables -vnL FORWARD | grep FUPNP` should
  both be empty, with the VSERVER→VUPNP jump still present. **[owed — metal, UPnP inbound connect]**

- **[P3] miniupnpd 2.3.11 + OpenVPN 2.7.6 report their real versions — glance.** Both packages carry
  version-stamp freeze traps (generated `config.h` gating); the stale files were purged before this
  build, but **settles when** the System Log / `miniupnpd -version` and the VPN page's
  `openvpn --version` line read 2.3.11 / 2.7.6 on the flashed image. **[owed — metal, glance]**

### v2.5.4 (2026-08-20) — staged batch, awaiting confirmation

- **[P2-H6] QoS strict-priority order corrected — queue config metal-validated; drain-under-load owed.**
  The class queues shipped with `priority == qid`, which inverts the intended order (class 1, the row
  "served first", held the second-lowest rank and the catch-all outranked it). Fixed to
  `priority = 6 - qid` (class 1 highest), applied by delete-then-recreate because the traffic manager
  refuses an in-place renumber (`Priority already in use`). **Read back on the lab RT-BE96U as correct**
  (q1=5…q5=1; q0/q6 left at stock 0/6), and the priority survives the later `setqdropalg`/`setqshaper`.
  **Settles when** a type-11 upload under real classified congestion shows the higher classes draining
  ahead of the catch-all — the one thing a queue-config read-back cannot prove.
  `tmctl getqcfg --devtype 0 --if <wan> --qid 1..5` should read priority 5,4,3,2,1. **[owed — metal, drain under load]**

- **[P2] Speed test no longer ends on a brief stall — needs the multi-run session.** `level_err_cnt`
  was consumed once per 200 ms poll, so a stalled tail entry was tallied ~5×/s and `LEVEL_ERR_MAX=50`
  became "10 s of a stall". It is now counted once per **new** buffer entry and reset on any progress
  (consecutive-error semantics; the run stays bounded by the existing `test_timeout`). **Settles when**
  several back-to-back runs — including one that stalls mid-transfer — complete or fail on the real
  timeout rather than the false 50-error trip. This is the multi-run-on-metal test the item always
  named; do not defer it a fourth time on "one pass proves nothing". **[owed — metal, multi-run]**

- **[P2] QoS WRR weights removed from the UI (strict priority only) — glance.** The per-class
  Weighted/weight controls were removed because this platform's egress scheduler cannot create a WRR
  queue at all (every queue slot is strict-priority; the stock code's own WRR `setqcfg` fails the same
  way). Root cause and the ASUS-actionable fix are under
  [Blocked by closed-source components](#blocked-by-closed-source-components--for-asus--broadcom) (B-1).
  **Settles on** a glance that the QoS class table shows strict priority only, `qos_sched` saves as
  `p,p,p,p,p`, and classification still works. **[owed — glance]**

- **[P3] Wireless Auto-Scan reports instead of auto-pinning — glance.** A clean sweep used to commit
  `wlN_chanspec` (which also switched auto-channel off for that radio); it now always restores the
  pre-sweep channel/width and leaves committing to the "Pin best" button. **Settles on** a glance: run
  a scan, confirm the radio's Control Channel is unchanged afterwards, and "Pin best" still applies the
  winner. **[owed — glance]**

---

- **[P2] AiMesh nodes now classified wired/wireless by RE-node awareness — needs a mesh box.**
  `do_reaper_dev` used to default any device it could not positively place to Wired, which stamped a
  **wireless-backhaul** AiMesh node Wired (its backhaul iface is often WDS/dpsta — neither `eth*` nor
  `wl*` — so the FDB pass left it unclassified). 2026-08-19 (field report): the last-resort fallback
  (`web.c` ~24460) is now RE-node-aware — `is_re_node()` (cfg_mnt shm) promotes an unplaced *active*
  node to **wireless**, guarded `#ifdef RTCONFIG_CFGSYNC` with a no-op `#else`, mirroring
  `rdev_scan_amesh`. **Shipped in v2.5.1** (recompiled clean again in the v2.5.3 build). **The
  maintainer has no mesh, so this cannot be self-tested** — `is_re_node()` is a constant 0 there, so
  behaviour is identical to before. **Settles when a field tester confirms BOTH:** a wireless-backhaul
  node reads Wireless, *and* a wired (cabled) node still reads Wired. **[owed — field test]**

- **[P3] Dashboard brand logo no longer jumps vs the other menus — SHIPPED v2.5.1 (logo padding) + v2.5.3 (whole left-nav rail geometry standardized to the Dashboard); needs a glance on the built image.**
  2026-08-19: `Main_ReaperDash.asp` `.top` padding was `10px 18px` while the shell (every framed menu)
  uses `14px 18px`, so the logo sat 4px higher on the dashboard and jumped when switching to/from it.
  Padding matched to `14px 18px`. www-only; **settles when the built image shows no vertical logo shift
  switching Dashboard ↔ any other menu.** **[owed]**

- **[P3] Firmware page — Mesh Nodes card moved to the bottom — SHIPPED v2.5.1.** 2026-08-19: on `Reaper_Firmware.asp`
  the Mesh Nodes card (`RFWU_32`) was swapped below the manual-upload card so it is the last section.
  www-only; **settles on a glance at the built Firmware page.** **[owed]**

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
  lookup always answered for the first connection. **v2.5.0 additionally widens the 802.1Q VLAN parent (`assert_vlan_parent_mtu`, `interface.c`) so a tagged-WAN line's `vlan6` is raised to 1508 instead of left at 1500 — the eth0-1508/vlan6-1500 field observation; check `ip link show vlan6` reads mtu 1508 while up.** **What is not established is whether the
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

- **[DONE v2.5.4] SDN Wi-Fi-key mask bypass via an SSID containing a literal `<b>` tag — fixed at the
  source.** The shared `state.js showWlHintContainer()` injected the SSID into `innerHTML` unescaped, so
  an SSID literally containing `<b>…</b>` shifted the bold-element index and could leave the key
  visible. Rather than the narrower "mask the last `<b>`" workaround, v2.5.4 **escapes the SSID, key and
  band at the source** (`_esc()` over `& < > "`), so the injected markup — and the index shift it caused —
  can no longer happen. Never a crash or XSS; this closes the mask-bypass root cause. Recorded in the
  Changelog (v2.5.4).

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

- **[P3] VPN ipset/domain policy routing — a UI (field-user request, 2026-08-19).** OpenWrt-style
  "Policy Based Routing" / a VPN-Director-equivalent, but **ipset-driven and authored in the Reaper
  UI**. The requester's words: *"a UI version, similar to your Firewall Rules, that would selectively
  mark and route packets to a certain VPN interface based on an ipset"* — offered as an addition to
  the existing geo firewall + firewall rules, to use the box's otherwise-idle routing capability.
  Equivalent to what the amtm **Domain VPN Routing / x3mRouting** script does today, brought native.
  Ipset based routing as concept and function would ideally be placed in the proximity of IP based 
  routing aka VPN Director. At that point you have a robust VPN (and WAN) routing solution.
  The firewall with all the smart additions is a totally different, solid and much improved function.  
  **Most of the mechanism already exists — the requester's screenshot shows the per-tunnel fwmark
  allocation that makes this cheap** (the amtm script's marks; a native feature would emit the same):

  | Tunnel | FWMark | Mask |
  |---|---|---|
  | OpenVPN Client 1 | `0x1000` | `0xf000` |
  | OpenVPN Client 2 | `0x2000` | `0xf000` |
  | OpenVPN Client 3 | `0x4000` | `0xf000` |
  | OpenVPN Client 4 | `0x7000` | `0xf000` |
  | OpenVPN Client 5 | `0x3000` | `0xf000` |
  | WireGuard Client 1 | `0xa000` | `0xf000` |
  | WireGuard Client 2 | `0xb000` | `0xf000` |
  | WireGuard Client 3 | `0xc000` | `0xf000` |
  | WireGuard Client 4 | `0xd000` | `0xf000` |
  | WireGuard Client 5 | `0xe000` | `0xf000` |

  Per-tunnel routing tables (`ovpnc1..5` / `wgc1..5`) and the `ip rule fwmark …/0xf000 lookup <table>`
  primitive already exist in-tree. With a dedicated `0xf000` mask per tunnel, a PBR rule is just:
  `iptables -t mangle -A PREROUTING -m set --match-set rwfw_<obj> dst -j MARK --set-xmark <tunnel-mark>/0xf000`
  — reusing a `reaper_fw` ipset/FQDN object and the tunnel's own mark. **This screenshot resolves the
  top "fwmark-space coordination" risk the feasibility note flagged:** the mark space is already
  partitioned so VPN owns the `0xf000` nibble — only verify QoS/MTWAN masks don't touch that nibble.
  That pushes the estimate from *Moderate* toward *Easy* for an MVP.

  Full implementation path + verdict is in the private working tree:
  `asuswrt-merlin.ng/docs/VPN ipset-based Routing Implmentation Check.md`. Reuse: `reaper_fw` ipset
  objects + the dnsmasq FQDN→ipset emitter + the commit-confirm/auto-revert engine; add one
  mangle-MARK emitter + a tab on `Reaper_Firewall.asp`, keyed to the ipset objects the geo/firewall
  work already builds. IPv4-first (VPN Director is v4-only). **Plan only — not built.**

  **PLACEMENT DECIDED (owner, 2026-08-20): the GUI is a new tab in the VPN area (near VPN Director),
  NOT on `Reaper_Firewall.asp`.** The firewall page only supplies the ipset objects; the routing
  editor lives with the VPN pages.

  **Feasibility gates checked live 2026-08-20 (lab rmcpd), deferred pending an active tunnel:**
  - Gate 1 (routing tables) PASS: `wgc1-5` (rt_tables 1-5) + `ovpnc1-5` (6-10) defined.
  - Gate 2 (mark space) PASS in the current config: mangle MARK table empty; QoS is HW type 10/11
    (no mangle marks), no MTWAN, so the `0xf000` nibble is uncontended.
  - Gate 3 (the load-bearing one) **RESOLVED 2026-08-20 → `from/to` form ⇒ MODERATE.** The GT-BE98
    field tester's box (live WireGuard `wgc1` + VPN Director) logs `vpndirector: Routing <name> from
    192.168.50.x to any through wgc1` — i.e. **source-IP `ip rule`s (`from <src> lookup wgc1`), NOT
    fwmark.** Stock VPN Director does not emit the fwmark form (that is x3mRouting's addition). Decisive
    because an `ip rule` cannot match an ipset — only a fwmark can (set via `iptables -m set` in mangle)
    — so the ipset feature MUST use the fwmark path regardless, and since VPN Director gives only
    from/to rules, **our feature emits BOTH the mangle-MARK and the `ip rule fwmark …/0xf000 lookup
    <tunnel-table>` itself.** (Diag-tool captures don't include `ip rule list`; the raw list is still
    worth grabbing once to pick a non-colliding rule priority — or add a VPN-routing section to
    `reaper_diag`.) **Build guardrails:** idempotent rule add; gate the MARK on tunnel-UP state so a
    down tunnel can't blackhole; IPv4-first. No longer blocked — ready to design/scope the MVP.

  **MVP CORE IMPLEMENTED (staged, next build) — 2026-08-20, owner delegated the design.** New
  subsystem `rc/reaper_pbr.c` (mirrors `reaper_fw`'s idempotent-generated-script discipline), wired
  into `rc/Makefile`, `rc/rc.h`, `rc/services.c` (start/stop cluster + `reaper_pbr` notify_rc handler),
  and the `start_firewall` re-apply hook in `rc/firewall.c`; knobs `reaper_pbr_enable` (default **OFF**)
  + `reaper_pbr_rulelist` in `shared/defaults.c`. **Contract (recorded in memory + `docs/VPN-Director-
  ipset-PBR-MVP-Plan.md`, supersedes the stale `0xf000`/`Reaper_Firewall.asp` mentions above):**
  fwmark field **bits 16-19 / mask `0x000F0000`** (the only free nibble on BE96U - bwdpi is compiled
  out so it's unconditional); `ip rule` pref base **9000, BELOW VPN Director's 10000** so PBR overrides
  it; reuses the existing `ovpnc1-5` tables + `reaper_fw` `rwfw_<obj>` sets. Data path: mangle
  `-m set --match-set rwfw_<obj> dst -j MARK --set-xmark <code>/mask` (+ CONNMARK restore/save so only
  the first packet is matched) then `ip rule fwmark <code>/mask lookup <table> pref 9000+code`, with a
  **fail-closed `prohibit`** below each tunnel lookup (no WAN leak when the tunnel drops). Record:
  `<en>desc>seltype>selval>proto>port>target`, all fields charset-validated in C, 50-rule blast cap.
  **MVP scope: targets OVPN1-5 / WAN-force / BLOCK, IPv4. WireGuard (WGC*) targets DEFERRED** - the
  BE96U WG data path is HW-offloaded and the accelerator ignores an `ip rule` unless the destination is
  fed to `hnd_skip_wg_network()`, which takes static CIDRs not a dynamic ipset; WGC rules are parsed,
  logged, and skipped (never silently "supported") until a mark-aware accel-skip is designed against
  on-box offload behaviour. **Remaining before ship:** (I4) route apply through `reaper_fw`'s
  commit-confirm/auto-revert; (I5) the VPN-area UI tab; then WG + IPv6. **Testable now from CLI/lab**
  once a build is cut.

  **MVP CORE METAL-VALIDATED 2026-08-20 (lab rmcpd, Reaper_v2.5.5).** Built green (MAKE_EXIT=0,
  `[rc] CC reaper_pbr.o`, both Done markers; new strings confirmed in the staged `rc` ELF). On-box
  via CLI: enabling a 5-rule set produced EXACTLY the designed rules — `9001 lookup ovpnc1` + `9101
  prohibit` (OVPN1 fail-closed), `9011 lookup main` (WAN-force), `9015 prohibit` (BLOCK); MARK rules
  `.240=0x10000 .241/.242=0xb0000 .50=0xf0000`; the empty-desc record `1>>src>…>WAN` parsed correctly
  (vstrsep); WGC1 emitted NO rule + `reaper_pbr: WGC target 'WGC1' is not supported yet …- rule
  skipped`; marks land in bits 16-19, band is 9000s below VPN Director, no errors. `ovpnc1`=table 6 so
  the lookup loads with the client down and the 9101 prohibit fails the flow CLOSED. Disable → fully
  clean teardown (chain gone, no jump, active=0). **Remaining: I4 commit-confirm, I5 UI, WG accel-skip,
  IPv6.** Data path is proven; the feature is real.

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

- **[DONE v2.5.4] Translations — Warden custom-feed labels (`RWDN_77`–`RWDN_85`) + About-page field
  labels and section headings — applied across all 24 non-English packs.** Lockstep preserved (each
  pack unchanged at its key count), placeholder keys `RWDN_80/81/82` verified free of double quotes.
  The About page's personal credits, descriptive prose and the licence / vendor / no-warranty text
  were intentionally left in English. Recorded in the Changelog (v2.5.4). Any future minor-language
  nuance pass is a native-speaker review, not a blocker.

---

## Code quality / deferred (with reason)

---

- **[P2] [owed] Work the Phase 1/2 code-review findings** — catalogue in the private working tree
  (`asuswrt-merlin.ng/docs/CODE-REVIEW-2026-08-18.md`), not synced into this lean repo. 70 Phase-1
  findings (5 high, 32 med, 33 low) + 44 Phase-2. **The §7 priority list is now fully resolved:**
  - HIGH items (Phase-1 H1–H5, Phase-2 P2-H1…P2-H11) — **all fixed in v2.5.0** (see that section).
  - §2.2 per-byte `fflush` in the JSON escapers — **fixed** (H3, v2.5.0).
  - §2.4 `esc()` / `reaper_util.js` consolidation — **fixed**: v2.5.0 landed the shared helper;
    v2.5.1 finished the last 3 pages (GK/Warden/QoS now delegate to `window.esc`).
  - §2.3 page-polling `document.hidden` gate — **fixed 2026-08-19**: `Reaper_GK` (5 s) and
    `Reaper_Traffic` (user-selectable down to 100 ms) now stop their timers when the tab is
    hidden, matching `Reaper_QoS`/`Reaper_Conn`/`Reaper_QoSDiag`.
  - §2.1 netfilter fork storms (Warden/GK → `iptables-restore` batching + the double teardowns) —
    **DEFERRED per owner (2026-08-19)**: high blast-radius on controls under active metal-test;
    revisit once v2.5.0's firewall/Gatekeeper is validated on hardware.
  - `services.c:8404` `reload_upnp()` full restart per firewall rebuild — **REFUTED (2026-08-19),
    do NOT "fix".** The restart is a deliberate 2026-08-11 field fix; the old SIGUSR1 was the *bug*
    (re-adds nothing → every UPnP/PCP mapping silently dies after a firewall flush). It already
    routes through `notify_rc("restart_upnp")` **asynchronously**, so the `sleep(5)` never stalls
    `start_firewall`. Reverting would reintroduce "UPnP stops working after a while".

  **What remains (the real [owed] work):** the discrete MEDIUM/LOW efficiency + data-flow tail —
  dead code, redundant nvram re-reads, per-device fork loops, etc. Each needs per-item reachability
  verification before it becomes a patch; the `reload_upnp` refutation and the `psc6g` deliberate
  duplicate prove some findings are stale or as-is by design.

  **Tail progress (2026-08-19) — SHIPPED in v2.5.1 (cut into the lean repo via the v2.5.3 series):**
  - *Fixed — dead code / cosmetic (bucket a):* dead `static ip2str()` removed (`rtrafd.c`); dead
    `nhex` counter removed (`rwarden.c` `rw_valid_cidr6`); 18 lines of orphaned CSS for the removed
    iptables chain-view removed (`Reaper_Firewall.asp` — `.chaincard`/`.owner*`/`table.ipt`,
    grep-confirmed zero references); broken `input.txt` selector → `input[type="text"]` so the
    custom-feed inputs get themed instead of browser-default (`Reaper_Warden.asp`); defined the
    missing `--panel-3` token so the `.railabout:hover` lift actually renders (`Main_ReaperDash.asp`);
    defined the missing `.btn.ghost` variant used by 3 buttons but never styled (`Reaper_Wireless.asp`).
  - *Fixed — hot-path MEDIUMs (bucket b):* `gk_client_name()` (`web.c`) now parses `custom_clientlist`
    **once per request** into a MAC→name index (rebuilt only when the value changes) instead of
    re-reading + strdup'ing + re-parsing per device — 300+ redundant nvram reads/parses per status
    request on a 5 s poll eliminated; first-match + 32-byte clamp preserved exactly, single-flight
    safe, no entry-count regression (index is dynamically sized). `sb_scrub_sec_tuples()` (`rmcpd.c`)
    hoists the constant `SEC_AUTH` token lengths out of the per-boundary match loop (kills the
    per-byte `strlen` storm on the ~256 KB posture payload); output byte-identical. `connseen_update()`
    (`rtrafd.c`) now rewrites `/tmp/reaper_conn_seen` only when a flow was **added or evicted** — the
    file holds only `(nfc, seen)` and neither changes for a live entry, so a stable set was rewriting
    ~40 KB every 5 s for byte-identical content (the reader keys by nfc, never checks mtime; zero
    functional risk). `Main_ReaperDash` client-list + eth-port tiles skip the `innerHTML` rebuild when
    the built HTML is unchanged (cached on the element) — preserves scroll position and text selection
    while the operator reads, mirroring the page's existing `ST_SIG` guard.
  - *Refuted (verified, NOT changed):* `rmcpd.c tool_firewall` "-S and -nvxL are redundant" — they
    carry **different** data (`-S` = rule syntax, `-nvxL` = hit counters/policies), documented in
    the code comment. `rexport.c:166` `if(mins<1)` clamp is confirmed dead but **retained** as a
    defensive bound (zero cost, guards a future floor change).
  - *Deliberately left:* the `rmcpd get_settings_audit` secret-redaction `sed` — it is a
    defense-in-depth **secret mask**; removing it to save one exec is the wrong risk trade even if
    the C scrubber "subsumes" it.
  - *Still [owed]:* **`do_reaper_conn_cgi` nested-scan-under-lock restructure** — reads conntrack
    before taking the single-flight lock and does a nested linear scan inside it; **deferred per owner
    (2026-08-19) as too risky to reorder locking on a control under metal-test** — wants a dedicated
    look. Also the "4 orphaned dashboard CSS blocks" (needs a usage audit — the review's line numbers
    have drifted; the dashboard CSS is mostly live so no blind removal). **[owed]**

---

- **[DONE v2.5.4 → Changelog] The whole `RFW_*` namespace — the entire firewall page (245 keys) — now
  translated across all 24 non-English packs.** Lockstep preserved; the RFW_229 double-quote and
  RFW_36/RFW_37 apostrophe constraints (below) were honored, and protocol/product tokens were kept
  verbatim. The RFW_252 "Both" note below stays relevant for keeping that selector consistent. Original
  finding, for the record: measured 2026-08-16 across the 24 non-EN packs, 306 Reaper-minted keys still
  carried the English string, and **244 of them were this one page** — every other Reaper namespace was
  in single digits or zero. The firewall shipped in v2.4.1 and the pass never followed until now.

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


- **[P3] Two residual limits on Warden custom feeds, found by the 2026-08-18 adversarial pass and
  deliberately left.** Neither is a security hole; both are ceilings a user can reach by accident.
  - **[DONE v2.5.4 (cap)] `rw_threat` was created with ipset's default `maxelem` (65536).** A custom
    feed large enough to push the merged set past that made `ipset restore` fail (then the per-entry
    fallback failed per entry once full) — a silently truncated block set with only a log line. Fixed
    v2.5.4: all `rw_threat`/`rw_threat6` create sites (live + swap-tmp, so the atomic swap stays
    header-compatible) now use an explicit `maxelem 524288`. **Still [owed], the smaller half:** surface
    the entry count the page already fetches against that limit in the Warden UI.
  - **Update runtime is now user-extensible.** Eight custom feeds at `--retry 2 --max-time 40` add up
    to ~16 minutes to a refresh on top of the curated feeds and the country lists. The
    concurrent-run half is now **addressed** — v2.5.1 added a per-run `flock` on `update.sh` (a
    scheduled refresh and a manual "update now" can no longer overlap), and v2.5.3 added a shared lock
    between `fold.sh` and `stats.sh`. What **remains**: a lower per-feed timeout for custom entries so
    one slow feed cannot stall the whole refresh window.

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

## Known issues (cannot remediate — closed-source blob or source)

---

- **Investigated — NOT a bug (do not re-raise):** `Reaper_Firewall.asp` `v4_src`/`lw_sip`/`lw_dip`
  "XSS" (renders via `td.textContent`); Warden `V6LAN`/`WANIPS`/`V6WAN` (the router's own ISP-assigned
  addresses, not reachably poisonable); dnsmasq `/etc/hosts` IP field (an admin can already edit hosts
  via custom config); `custom_clientlist` tail truncation (the reader uses `strdup`, no fixed buffer);
  scrape-token "fail-open stub" (already `CRYPTO_memcmp` + `!want[0]` fail-CLOSED); store-chooser TOCTOU
  (mitigated by the `O_NOFOLLOW` opens).

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

- **[P3] Inherited ASUS/Merlin `httpd` core — two pre-auth robustness gaps that ship in stock.**
  Unlike the entries above these are **not blobs and are technically remediable** — but they live in
  the inherited `httpd` core, are present in **every stock Asuswrt-Merlin build** (not
  Reaper-introduced), and a change there risks a regression on the login/serve path and breaks the
  upstream merge-cleanliness the fork depends on. Recorded here as **known and out of scope for the
  public release**, matching the review's stated bar (*"Reaper's own code contributes no exploitable
  surface"*); revisit only as deliberate opt-in hardening that goes beyond stock.
  - **`Content-Length` has no upper clamp** — only `< 0` is rejected, and four pre-auth body drains
    do `while (cl--) fgetc(...)`, so an oversized `Content-Length` spins ~2e9 syscalls and takes the
    whole single-flight GUI down until the tab is killed. Fix if taken: clamp `cl > 65535 → 413`.
  - **`url[128]` left unterminated for a path ≥ 128 bytes** (the bound test is `>`, not `>=`) → an
    out-of-bounds read via the following `strstr`/`snprintf`; same for `login_url`. Fix if taken:
    `>=` + `url[file_len] = 0`. Reachability unproven.
  [inherited stock; deferred — not a Reaper regression, present upstream]

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report does not get re-investigated from scratch, and so the
reasoning survives the person who made the call.*

---

Investigated — NOT a bug (do not re-raise): Reaper_Firewall.asp v4_src/lw_sip/lw_dip "XSS" (renders via td.textContent); Warden V6LAN/WANIPS/V6WAN (the router's own ISP-assigned addresses, not reachably poisonable); dnsmasq /etc/hosts IP field (an admin can already edit hosts via custom config); custom_clientlist tail truncation (the reader uses strdup, no fixed buffer); scrape-token "fail-open stub" (already CRYPTO_memcmp + !want[0] fail-CLOSED); store-chooser TOCTOU (mitigated by the O_NOFOLLOW opens).

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

## Blocked by closed-source components — for ASUS / Broadcom

> Defects and limitations root-caused on RT-BE96U hardware that we **cannot** fix because the
> responsible code lives in prebuilt Broadcom blobs (`libtmctl.so`, `tmctl`, `rdpa.o` / the runner &
> rdpa port-init) rather than in the buildable SDK sources. Each entry below is written so an engineer
> with the closed sources can act on it. Metal evidence was captured on RT-BE96U (BCM6813 / 4916,
> XRDP) via `tmctl`, `bdmf_shell`, and reading the shipped binaries' strings.

### B-1. Classful QoS "WRR" (weighted round-robin) is non-functional on eth ports — every class silently runs strict-priority

- **Symptom.** With `qos_type=11` (classful hardware QoS) and any class set to a WRR weight, the weight
  never takes effect — traffic is scheduled strict-priority regardless. The weights are inert.
- **Reproduced on metal.** `tmctl setqcfg --devtype 0 --if eth0 --qid N --schedmode 2 --weight W`
  fails, rc=108, with (from `libtmctl.so`):
  ```
  get_wrr_queue_idx: No free queue index between min[8] and max[8]
  No place for new WRR queue, qid[N]
  ```
  full chain: `get_wrr_queue_idx.2067` → `prepare_set_wrr_q_in_sp_wrr_mode_single_level.2171` →
  `prepare_set_q_in_singel_level.2904` → `prepare_set_q.2994` → `tmctl_RdpaTmQueueSet.3163`.
- **Root cause.** Every port's egress_tm is created with **`num_sp_elements = 8` of `num_queues = 8`**
  (confirmed live: `bdmf_shell -c <id> -cmd "/Bdmf/e egress_tm max_prints:-1"` shows `mode: sp_wrr`,
  `num_queues: 8`, `num_sp_elements: 8` on eth0/index=4 (WAN upload) **and every other port**). With all
  8 scheduler elements assigned to strict-priority, there is **no queue index left for a WRR queue**, so
  the SP_WRR single-level arbiter rejects any WRR queue.
- **Why it is blob-gated for us.** `num_sp_elements` for **eth** ports is set at egress_tm creation
  inside the closed rdpa driver (`rdpa.o`, prebuilt) — the symbol appears in *no* eth-port source in the
  SDK (only the GPON path `rdpa_cmd_llid.c` and the DSL path `xtmrt_runner_ex.c`). `tmctl` and
  `libtmctl.so` ship prebuilt with no source, so the `porttminit --flag` / `--profileid` encoding that
  would choose the SP/WRR split is not visible or modifiable. The GPL header
  `rdp/drivers/rdpa_gpl/include/rdpa_egress_tm.h` documents the valid splits —
  `rdpa_tm_num_sp_elem ∈ {0, 2, 4, 8, 16, 32}` — and explicitly marks `rdpa_tm_sched_sp_wrr` as
  `\XRDP_LIMITED`.
- **What ASUS / Broadcom can do (has the source).** Create the eth-port egress_tm with
  `num_sp_elements = 4` (4 SP + 4 WRR of 8 queues) — or expose a `porttminit` flag / TM profile that
  selects it — so `tmctl setqcfg --schedmode 2 --weight N` can place WRR queues. If XRDP genuinely cannot
  offer mixed SP/WRR on eth ports, please **document eth egress as SP-only** so integrators don't surface
  weight controls. A read-only `tmctl getportcaps`-style query returning `maxSpQueues` would also let
  userspace detect this instead of discovering it by a failed `setqcfg`.
- **Our mitigation (Reaper v2.5.4).** rc/qos.c forces strict-priority for all class queues and logs a
  one-line notice if `qos_sched` requested WRR; the QoS UI's per-class scheduler-mode + weight controls
  were removed so the page no longer offers a control the hardware ignores. See
  [[qos-classful-defects]] and the P2-H6 entry above (the *priority* half of classful QoS — the queue
  rank being inverted — **was** in our source and is fixed).

*(Other items we cannot remediate because they live in closed-source blobs are catalogued under
"Known issues (cannot remediate — closed-source blob or source)" above; this section collects the ones
that are specifically actionable by ASUS/Broadcom with the closed sources in hand.)*
