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

*Updated 2026-08-30 (7th pass) — seventeen closed items removed and recorded in [`CHANGELOG.md`](CHANGELOG.md) under the versions that shipped them: the Warden feed ceilings (v2.7.8); the sibling `Tools_Sysinfo.asp` sync (v2.8.3 fleet cut); the diag counter fixes and the user-guide set (v2.8.7); the Traffic Analyzer live-view freeze (v2.8.8); the Firewall Status refresh cue, Wireless Apply and firewall sub-editor Apply feedback, the diag preamble numbers and the guest-pass unit (v2.9.3); the Firewall Status forwards/intercepts rows, the Smart Connect pointer, the Devices export reserved-IP columns, the QoS drops note and the diag SSID length (v2.9.4). The QoS class-breakdown and Traffic Analyzer visual-reset reports closed as working-as-designed (no DPI; no-RTC clock step) and are noted under v2.9.4.*

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
3. **[P2] CVE check 2026-08-30 fallout** — whitelist the DNS Traffic Analyzer SQL inputs
   (`web.c:39324-39370`), Tor 0.4.9 bump before the 2026-09-01 network sunset, the cheap
   strongSwan/avahi/kernel backports. → [Open bugs](#open-bugs--under-investigation)
4. **[P3] Code-review tail, batch B** (`do_reaper_conn_cgi` lock order, `rexport` mask loop,
   §2.1 iptables-restore batching — the first and last are owner-deferred; `pinTarget()` is
   **closed**).
   → [Code quality](#code-quality--deferred-with-reason)

---

## Open bugs / under investigation

- **[P2] CVE / component check 2026-08-30 (v2.9.4 staged rootfs) — results and the work it queues.**
  First dedicated inherited-component CVE pass: 6 research slices + 2 adversarial verification
  passes, every finding re-derived from the staged fs, the vendored source and the CVE record.
  Full report `audits/CVE-CHECK-2026-08-30.md` (ASUS root, internal); slice evidence in
  `audits/cve-2026-08-30/`. **No REACHABLE-HIGH survives; nothing REACHABLE-MED at factory
  defaults.** The default-on surface (dnsmasq 2.93, avahi, lldpd incl. the WAN port, Samba SMB2/3
  LAN-only, busybox udhcpc/ntpd, OpenSSL 1.1.1 at the June-2026 ESM level) carries its fixes.
  - **[P2] SQLi in ASUS's DNS-based Traffic Analyzer handlers, compiled in here** (CVE-2026-11851
    class). `httpd/web.c:39324-39370` `ej_dns_appStat / ej_dns_wanStat / ej_dns_wanStat_detail`
    pass raw `websGetVar("client"/"mode"/"dura"/"date")` into the prebuilt `dns_sqlite_Stat_hook()`
    (`SELECT %s FROM %s WHERE %s …`, `mac="%s"`); only `ej_dns_status` (`:39286`) validates.
    Registered unconditionally under `RTCONFIG_DNSQUERY_INTERCEPT=y`; `getAppTraffic_Dns.asp` /
    `getWanTraffic_Dns.asp` ship. Admin-auth (or CSRF'd admin) read of `/jffs/app_*.db`. **Fix =
    whitelist the four inputs exactly as `ej_dns_status` does; do not wait for ASUS's build#.**
    Add to the v3.0.0 security review's pre-seeded list.
  - **[P2] Tor 0.4.8.22 stops working 2026-09-01** — 0.4.8 EOL since 2026-06-01, the network
    rejects <0.4.9 from September 1 (torproject.org). Client-side TROVE-2026-009/011 also unfixed.
    Bump to 0.4.9.x (Merlin 102.9 carries 0.4.9.11 + an IPv6-leak fix) or drop the feature.
  - **[P3] Cheap backports, no default change** — strongSwan CVE-2026-47895 `clone_()` hunk
    (`identification.c:1712-1729`; unauth EAP-Identity/XAuth double-free, MED only when IPsec server
    is on, UDP 500/4500 closed by default); avahi CNAME trio CVE-2025-68468 / CVE-2025-68471 /
    CVE-2026-24401 (`browse.c:298/323/401-424`; LOW but **default-on** — the precondition exists
    because `nsswitch.conf` uses `mdns4_minimal` and nss-mdns ships, so any router-side `.local`
    lookup opens the record browser); kernel one-hunk set CVE-2024-50299 (SCTP OOTB — LAN path
    proven, impact a 2-byte tailroom read, LOW), CVE-2023-52881, CVE-2024-47684, CVE-2024-50154,
    CVE-2023-6932, plus CVE-2023-52340 (MED only with IPv6 WAN). No stable backports beyond
    4.19.294 exist in the tree — proven.
  - **[P3] Document as known limitations (Samba precedent)** — netatalk 3.0.5 / Time Machine:
    2022 pre-auth RCE set **confirmed absent in code** (CVE-2022-23125 `appl.c:86-111`,
    CVE-2022-45188 `appl.c:410-420`, CVE-2022-43634 `dsi_write.c:37`, CVE-2022-23121) — MED when
    enabled; wpa_supplicant **0.6.10 (2010)** used for WAN 802.1X (`rc/auth.c:216`) — MED when
    configured, no slice had inventoried it; lighttpd 1.4.39 behind the captive portal
    (CVE-2018-25103, pre-auth :8083 when `cp_enable`/`chilli_enable`=1); net-snmp 5.9.4.pre2
    CVE-2022-44792/93 with a RW community; Quagga 0.99.24 zebra CVE-2016-1245 when
    `quagga_enable=1`. Each is off by default. Own rung + metal test if any is upgraded.
  - **[P3] Supply-chain note** — `webs_update.sh:66` `REAPER_SIG_ENFORCE=0`: the manifest signature
    check is inert (owner-shelved 2026-08-23); protection is HTTPS + CA + GitHub host-pin + sha256.
    Residual = GitHub-account compromise. Re-enable or record as accepted.
  - **[P4] Hygiene** — OpenSSL 1.1.1zi pair (CVE-2026-63072 / -54874, no consumer); e2fsprogs
    CVE-2022-1304 (owner-triggered scans only — the hotplug-fsck claim was refuted); busybox
    `ash.c`/`tar.c` bumps (root-only residuals); stray x86-64 `lib/libexpat.so`; 19 blanket
    `-lxml2` links + expat 2.0.1 build (HIGH the day any binary parses network XML); the dead
    HTTP `app_*.sh` install path (`apps_ipkg_server` empty, APP_* unset) — remove the pages.
  - **Uninspectable, recorded so nobody re-finds them**: Broadcom `hostapd` (default-on, over the
    air), `cfg_server`/`cfg_client` 7788, `networkmap`, `infosvr` 9999, `protect_srv`, `dnsqd`,
    `asusdiscovery`, Tuxera `tntfs/tfat/thfsplus`. CVE-2025-15101 (ASUS web UI cmd-inj) stays
    INFERRED-fixed from sibling build numbers — no public endpoint to grep.
  - **Cadence**: delta check per minor release; full pass when the Merlin base moves (102.9's
    OpenSSL 3.5 migration is the next).

---


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

---

## UI / UX polish

---

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

- **[P3] Static preamble puncturing control for 320/160/80 MHz channels (`wl eht dissubchan`) —
  BUILDABLE, source-only (investigated 2026-08-31).** 802.11be preamble puncturing lets the AP keep a
  wide channel and transmit around a 20/40/80 MHz slice that is occupied (a neighbour's 6E/7 BSS parked
  inside our 320 block) instead of falling back to 160. Our SDK (`WIFI7_SDK_20231126`) has the
  **static** form: `WL_EHT_CMD_DISSUBCHAN` (`wlioctl.h:14489`, struct `wl_eht_dissubchan_cmd` with
  `dissubchans` + `pending_dissubchans` + `pending_csa_triggered` = applied live via CSA), and the
  shipped `wl` exposes `wl eht dissubchan [bitmap]`. `wl.ko` already computes the legacy-client width
  after puncturing (`wlc_eht_get_max_legacy_bw_after_puncturing`), so Wi-Fi 6/6E clients are served
  inside the un-punctured portion by the driver. **Nothing in the firmware drives it:** no nvram
  consumer, no GUI, no init hook; `wlconf`/`acsd2`/`rc` carry no reference.
  - **Shape:** nvram `wlX_punct_bitmap` (0 = off) applied after wlconf at radio bring-up
    (`rc/sysdeps/init-broadcom.c`, beside the `eht_features` assembly) and on `restart_wireless`;
    Wireless-page row of 20 MHz cells for the live chanspec constrained to the legal 802.11be
    patterns (320 MHz: one 40 or one 80 MHz slice, never the primary 20; 160: one 20 or 40; 80: one
    20) with a `Puncture pattern: 0x…` readback; diag section 7 gains `wl eht dissubchan` + a
    per-20 MHz `chanim_stats` so the dirty slice is visible. OFF by default.
  - **Metal gate first (zero build):** read `wl -i wl2 eht dissubchan`, set one 40 MHz bitmap on the
    pinned 320 block, confirm the pattern is reported and clients stay associated. If the driver
    reverts it the way a runtime `chanspec` set does, the hook must ride wlconf's bring-up path.
  - **Honest scope note:** the 2026-07 6 GHz sawtooth was occupancy across the ENTIRE upper 160 MHz
    of the 320-1 block (ch 33-61); puncturing removes at most 80 MHz of a 320, so it would not have
    fixed that case (avoidance did). It pays off for a narrower interferer. MRU needs nothing from
    us (EHT PHY capability, driver-scheduled). **Dynamic / interference-aware puncturing is blocked -
    see B-4.** **[project]**
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


### B-4. Dynamic (interference-aware) preamble puncturing needs the 2025 Broadcom SDK

- **[P3] The automatic form of 802.11be preamble puncturing - the AP measuring per-20 MHz occupancy
  and puncturing the dirty slice on its own - is not in the SDK this model ships with.** Source
  references it: `shared/wlif_utils_ax.c:4901` sends `WL_EHT_CMD_PUNCT_FEATURES` and `defaults.c:2046`
  seeds `wl_eht_punct_features=0` ("disable puncture features by default"), but both sit behind
  `#if defined(WIFI7_SDK_20250506)`; this build is `WIFI7_SDK_20231126` (`sdk_profile.mak:1`), the
  enum does not exist in our `wlioctl.h` (`wl_eht_cmd_e` ends at `EXT_NLTF = 12`), and no shipped
  blob (`wlconf`, `acsd2`, `wl`, `hostapd`) carries the string. `acsd2` has no puncture logic at all.
  Only the **static** bitmap (`WL_EHT_CMD_DISSUBCHAN`) exists - see the Features entry, metal-proven
  2026-08-31. Unblocks when ASUS publishes a GPL drop for this model on the 2025 SDK; until then the
  nvram default is inert. **[blocked - SDK]**

---
