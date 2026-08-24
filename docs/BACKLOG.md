# RT-BE Series "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done), **[blocked]** (external cause), **[shelved]**
(deliberately deferred), **[cosmetic]** (polish, non-blocking).

**Priority** (by impact on user-facing functionality): **[P1]** core function
broken or at risk for users · **[P2]** degraded function, meaningful annoyance, or
privacy exposure · **[P3]** cosmetic, polish, internal quality, or deferred-by-decision.

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md). **Completed items are not kept
> here** — when something ships it moves to the changelog, and when its confirmation arrives it
> leaves [Pending verification](#pending-verification). This file lists only work that is not yet
> done, which includes work that is *believed* done but unconfirmed.

*Last cleaned 2026-08-24 (after v2.7.6). Everything marked FIXED/DONE/SHIPPED in earlier revisions
was moved to the changelog; only open work and open confirmations remain.*

---

## Contents

- [Work next](#work-next)
- [Open bugs / under investigation](#open-bugs--under-investigation)
- [Architectural — owner decision needed](#architectural--owner-decision-needed)
- [Pending verification](#pending-verification)
- [UI / UX polish](#ui--ux-polish)
- [Features to add](#features-to-add)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Documentation](#documentation)
- [Known issues (cannot remediate — closed-source blob or source)](#known-issues-cannot-remediate--closed-source-blob-or-source)
- [Reported, investigated, closed as working-as-designed](#reported-investigated-closed-as-working-as-designed)
- [Blocked by closed-source components — for ASUS / Broadcom](#blocked-by-closed-source-components--for-asus--broadcom)

---

## Work next

The ordered short list. Each line points at its full entry below.

1. **[P2] Confirmations owed on metal / from reporters** — v2.7.6 field fixes (PBR chain complete
   after a reboot with no UI Apply, 40-domain paste in one go, Warden "Stats unavailable —
   retrying", addon `ip rule`s survive `restart_firewall`), v2.7.5 Addons rail (a box with real
   addons), v2.7.4 first-boot gate fix (BE92U nav + factory-reset regression), v2.7.3 AiMesh
   onboard with quarantine ON + guide links + themed USB dialog + backup-card alignment, v2.7.2
   full-backup round-trip + Analyzer month/year, v2.7.1 per-boot token remainder (the other pages'
   controls, cross-site refusal, the ASUS app / scripts), v2.7.0 settings export/import, v2.6.9
   remainder (address lists, /jffs persistence), v2.6.8 USB ext format (a spare stick), v2.6.7
   Policy Routing close-out (needs a WireGuard client and/or IPv6), v2.6.5 Gatekeeper
   multi-network, v2.6.3 Gatekeeper 45-device fix (reporter), v2.6.2 firewall-order behaviour
   tests + L3 leg, v2.6.0 QoS queue rebuild (GT-BE98), v2.5.9 Warden country sets + node
   classification, v2.5.8 UPnP. (v2.7.4–v2.7.6 images exist for BE96U + BE92U only — the BE88U
   reporter needs a sibling build first.)
   → [Pending verification](#pending-verification)
2. **[P2] Warden "crash" on the BE92U addon box** (amtm + Diversion update) — hypotheses ranked,
   tester data requested. → [Open bugs](#open-bugs--under-investigation)
3. **[P2] Hosts-list paste blanks the GUI until httpd restarts** (BE88U, v2.7.1) — needs a repro on
   v2.7.6+. → [Open bugs](#open-bugs--under-investigation)
4. **[P2] RT-BE92U CI dry-run** — the CI wiring is in place; dispatch `model: RT-BE92U` to
   confirm it builds + publishes, then push `rt-be92u` to the hub. → [Features](#features-to-add)
5. **[P3] Code-review tail, batch B** (needs decisions / metal: `pinTarget()` 20→80 MHz intent,
   `do_reaper_conn_cgi` lock order, `rexport` mask loop, §2.1 iptables-restore batching).
   → [Code quality](#code-quality--deferred-with-reason)
6. **Translations owed** (RABT, RBKP_1–14, RFWU_49–53, RTWK_03/04, RWDN_69–72/89–91,
   RTRF_45/75/76, RVR_54–61, `Reaper_c_addons`, IPv6-proto labels). → [Documentation](#documentation)

---

## Open bugs / under investigation

- **[P2] About page patch count blank — FIXED 2026-08-24 (build-engine).** Root cause: the build's
  provenance stamp (`_reaper_build_lib.sh`) derived the series version from the **tip** patch's
  filename via `basename "$_tip" | grep -oE 'v…' | tail -1`. That only yields a version when the
  rung's last patch IS its version-bump patch. The v2.7.3 rung's tip was `0528-fwupdate-shelve-…`
  (a feature patch, no version token) — so `_sv` came back empty, the `[ -n "$_sv" ]` guard skipped
  `_pc`, and `reaper_provenance.js` stamped `patches:""` → the page shows a dash. This hit **both
  local and CI builds** and is exactly the "regressed before" history (it only works on rungs whose
  last patch is the bump). Fix: derive `_sv` from the **highest `reaper_v` token across all patch
  filenames** (`grep -oiE 'reaper[_-]v…' | sort -V | tail -1`) — order-independent, and it skips
  bare `v5.1`-style tokens inside feature-patch names (e.g. `0162-qos-v5.1-…`). Verified: now stamps
  `535 — series as of v2.7.6`. Applied to `build-scripts/_reaper_build_lib.sh` (canonical) + synced
  to the local engine. Not a firmware patch; takes effect on the next build. **Closes when** a
  rebuilt image's About page shows the count.

- **[P2] Warden "crash" on the BE92U tester after an amtm + Diversion 6.1 update — hypothesis only,
  tester data requested (2026-08-23).** No fix yet. Ranked: (1) the stuck-nvram wlcsm bug tripped by
  the addon installers' bare `nvram get` storm (our `_nv` guard covers only our own scripts — look
  for `rwatch: reaped hung nvram` / `reaper-nv` lines); (2) `restart_firewall` via Diversion's
  service-event racing `apply.sh` vs `update.sh`/`fold.sh`; (3) Skynet updated by amtm in the same
  pass (ipset / INPUT position-1 conflict). Data requested from the tester: uptime, syslog greps,
  `/jffs/rwatch` dumps, `pidof nvram` + ps, ipset/iptables listings, the addon list, and what
  "crashed" actually means. Note v2.7.6 already hardened the adjacent surfaces (Warden page never
  fails silently; layer re-applies under the firewall lock; PBR teardown deletes only our fwmark
  rules). **[owed — tester data]**

---

- **[P2] Firewall hosts rule: pasting an IP list blanks the GUI until httpd restarts (BE88U,
  v2.7.1).** No crash found in the page or CGI code; best fit is an httpd hang (the stuck-nvram
  class). v2.7.6's paste-tolerant normaliser may remove the trigger. Needs a repro on v2.7.6+ and,
  if it recurs, `/proc/<httpd-pid>/wchan`. **[owed — repro]**

---

- **[P3] Diag §14b "exempt input rules" count is over-broad** (seen on v2.7.3 metal): it greps ALL
  MAC-source rules in `REAPER_GKI`, so it counts the per-device `gk_rl` rules (34 on the owner's
  box) when the relist registry is 0. Fix on record: `gk_emit_relist` writes `echo N >
  /tmp/gk/relist.n` into `apply.sh` and the diag reads that file. **[cosmetic]**

---

- **[P2] Flash page — cancelling a firmware upgrade during file upload leaves the page dead.**
  **INVESTIGATED (v2.7.3): not reproducible in current source.** A node:vm harness executing the
  page's real script proved every Cancel path clean — install confirm, both upload confirms, the
  node-push confirm, and a veil dismiss all leave `busy=0`, every button enabled, no overlay. The
  symptom matches the pre-`a0c115dc45` (v2.3.4) doubled-poll freeze that was fixed then; the report
  likely predates it. One theoretical wedge remained — an uncaught throw after `busy=1` but before
  the veil paints (nothing on screen to dismiss, all buttons no-op) — v2.7.3's global error handler
  now clears the gate in that case. v2.7.3 shipped 2026-08-23 and is running on the owner's BE96U.
  **Closes when** no recurrence is reported over the field window; a repro on v2.7.x with exact
  steps reopens it. **[hardened — watch]**

---

- **[P2] AiMesh Search — "Search for node" finds no new node (reported GT-BE98/PRO, v2.3.x era).**
  Pre-existing meshes keep working; only *new-node discovery* was affected. CAP-side source is clean
  (no Reaper commit touches `www/aimesh`, QIS_V3 or the onboarding CGIs). Two silent drop gates
  exist in auditable source, both now instrumented (patch `0401`, shipped v2.3.7 on all models):
  1. `ej_get_onboardinglist()` (`web.c`) requires `model_name` **and** `ts_eth`.
  2. `select_best_onboarding_re()` (`web.c`) requires **all five** of `rssi`, `rssi_5g`, `rssi_5g2`,
     `source`, `ts_eth` on a parent — `rssi_5g2` is demanded even on models without a second 5 GHz
     radio. The better suspect.
  The ABI/key-skew theory (39274-era AMAS blobs) is **REFUTED** — do not re-raise.

  **Status:** field users now report finding and joining nodes fine; this may have been cured by
  other changes. **Closes when** one more tester confirms a fresh node onboards on a current image —
  or, on a failure, the `aimesh:` log lines name which gate dropped it. Runtime triage if it recurs:
  `nvram get cfg_obstatus` before (1) / during (2) search, `cat /tmp/onboarding.json` after,
  `ps w | grep -E "cfg_server|obd|wlceventd"`. **[owed — one field confirmation, then close]**

  **2026-08-23 full-path review (owner ask, "works for some / not at all for others"):** the
  CAP-side search/add chain was verified **100 % stock** (the only Reaper code in it is the three
  logging lines above and two icon de-cloud edits that cannot affect list membership;
  `cfg_string.h` confirms the blob's `onboarding.json` keys match the gates exactly, identical
  across all four models' `cfg_server` binaries). **A real, proven defect was found one layer
  down: no Reaper enforcement layer knew AiMesh existed.** With Gatekeeper in quarantine
  (`gk_default != 1`), `REAPER_GKI`'s allow-list (DHCP/DNS/80/admin → DROP) at INPUT position 1
  killed an unapproved node's cfg_server traffic the moment it had a lease — onboarding stalls
  right after association, and enabling quarantine on an established mesh kills node heartbeats
  (ebtables DROP + captive port-80 hijack too). Warden / rules engine / PBR / de-cloud each
  checked and proven safe. This cleanly explains the mixed reports: it tracks whether quarantine
  is on. **FIXED for v2.7.3:** `cfg_relist` MACs (cfg_server's own pairing registry) exempt from
  all four surfaces ahead of per-device rules; `gkd` re-applies when the registry changes and
  holds the INPUT gate open only while an onboarding is actually in progress; diag 14b shows the
  registry/exempt counts and window state. **Shipped in v2.7.3**, flashed on the owner's BE96U
  2026-08-23 — diag §14b renders the registry/window lines, and that box runs quarantine with 34
  devices, exactly the protected configuration. **[shipped — metal owed: onboard a node with
  quarantine ON]**

---

- **[P2] Dual-WAN failover: both NextDNS profiles receive DNS logs though only one WAN is live.**
  Secondary WAN (2.5 Gbps, DHCP, own NextDNS profile) active; primary (10 Gbps PPPoE) not yet
  connected. Both profiles show traffic; expected only the active WAN's. **[owed — research]**

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
  router's own shell ⇒ upstream. **[owed — tester capture + bounce confirmation]**

---

## Architectural

*Do not patch unilaterally.*

- **Gatekeeper multi-network — CLOSED in v2.6.5.** All three deferred pieces shipped: SDN
  create/edit/delete re-applies Gatekeeper (plus a self-heal bridge diff); captive page on an
  isolated SDN via one ctstate-DNAT admit rule in `SDN_FI` (self-healed when ASUS rebuilds it); IPv6
  GUA prefixes resolved live with a prefix-change re-apply. **Standing decision recorded:** the
  admin escape hatch stays main-LAN-only on an *Access Intranet = off* SDN — that switch means "no
  router UI", and opening it would contradict it. Confirmation is under
  [Pending verification](#pending-verification).

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

- **[P2] RT-BE92U in CI/CD — WIRED 2026-08-24 (dry-run + hub push owed).** RT-BE92U (BCM6765 /
  96765GW) is now fully registered in the CI/CD, locally validated (`bash -n`, YAML load,
  `check_overlays.py` passes all 6 models, overlay is the identity-only delta from canon):
  `overlays/RT-BE92U.patch` (12 files: `target.mak` + 6 banner-ref www + `state.js` + the
  RT-96U→RT-BE92U banner PNGs — no platform archive: its platform + the u-boot `$(RTBE92U)` rtl8372
  gate ship in the pinned base); `check_overlays.py` `MODEL_BANNER`; `container_build.sh`
  (branch case, `UB_SYM=RTBE92U`, `PROFILE`-parameterised `targets/96765GW`); `build_one.sh` (branch
  /banner/`REAPER_TDIR`/dict-gate profile); `_reaper_build_lib.sh` + `reaper_verify.sh`
  (`REAPER_TREE`/`REAPER_TDIR` honoured, default 96813GW unchanged); `public-build.yml` (added to the
  model dropdown — dispatchable on its own, **deliberately NOT in `all`** so the standard five-model
  fleet fan-out is unchanged and BE92U stays experimental/prerelease); `cut_fleet.sh` `MODELS` + a
  hub-missing-branch guard. **Owed:** a dry-run dispatch (`model: RT-BE92U`, `prerelease: true`) to
  confirm it builds + publishes end-to-end (not CI-testable locally); push `rt-be92u` to the hub;
  real (non-placeholder) banner art. **[wired — dry-run owed]**

- **Policy Routing — CLOSED in v2.6.7.** The MVP's three deferrals shipped: WireGuard targets via
  the same accelerator-bypass contract VPN Director uses (source rule → that CIDR; destination/MAC
  rule → whole LAN, logged + shown on the rule; entries recorded so only ours are removed), IPv6 on
  every selector with the fail-closed prohibit catching a v4-only tunnel, and apply-and-confirm with a
  cru-owned revert and a `/jffs` lastgood snapshot. **Standing decisions recorded:** the bypass is the
  documented ASUS/Merlin mechanism, not a kernel change (rule: no new kernel-facing code without
  field lineage); WG rules with a non-source selector cost LAN-wide acceleration by design — a
  mark-aware bypass would need a blog.c change and on-box proof. Proto/port matching remains
  deferred (never promised). Confirmation under [Pending verification](#pending-verification).

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

- **[P2] Native firewall suite — the remaining pieces.** Shipped v2.4.1 (engine, hub, Status posture,
  Egress defaults, hardened Forwards, backup/restore); dnsmasq `ipset=` FQDN emitter 2026-08-14 (the
  old "dnsmasq compiled without ipset" blocker was a misreading — do not re-raise).
  - **Advanced DSL for the Rules tab** — the 2026-08-08 design called for a Basic form *and* a text
    syntax; only Basic was built. Decide whether it is still wanted; the compile preview may already
    cover it. **[decision]**
  - **Rule tracer** ("given a packet like *this*, which rule matches?") — a C simulator over the
    committed config. Diagnostic aid, nothing is unusable without it. **[P3, owed]**

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

- **[P2] [owed] Translations.** All English-seeded in lockstep (nothing renders as a raw `<#KEY#>`);
  the 24 non-English packs simply show English for these until translated:
  - `RTRF_45` / `RTRF_75` / `RTRF_76` (Traffic Analyzer accounting strings, v2.4.4) — the old
    `RTRF_45` translations were **deliberately discarded** because they asserted the opposite of what
    the code now does. Precedent: the DE `RQOS_117` drift double-derated users' download cap.
  - `RABT_00`–`RABT_40` (About page, 41 keys) — mostly prose and jokes; a mechanical pass is worse
    than English. Needs a human.
  - `RTWK_03` / `RTWK_04` (bind-shim labels), `RWDN_69`–`RWDN_72` (Warden router-self filter).
  - v2.6.7: `RVR_54`/`54b`/`55`/`56`/`57`/`58` (Policy Routing WireGuard + confirm + IPv6 copy),
    `RABT_42` ("series as of"), `RWDN_89` ("Prefixes loaded:").
  - v2.6.8: `RDST_65`–`RDST_67` (USB format filesystem hints).
  - v2.6.9: `RVR_59`–`RVR_61` (address-list validation + placeholder).
  - v2.7.0: `RDST_68`–`RDST_77` (settings backup card).
  - v2.7.1: `RANL_51/52`, `RCON_41–43`, `RDEV_92`, `RFW_256`, `RFWU_48`, `RVR_62`, `RWDN_90`,
    `RWIF_83/84` (i18n sweep) and the refreshed `RDST_01`, `RWIF_31`, `RWIF_33` (English in all packs).
  - v2.7.2: `RBKP_1`–`RBKP_14` (full-backup card).
  - v2.7.3: `RABT_43`/`RABT_44`/`RABT_46` (guide links), `RFWU_49`–`RFWU_53` (signature-refusal
    UX — inert while signing is shelved, but seeded).
  - v2.7.5: `Reaper_c_addons` (Addons rail group). v2.7.6: `RWDN_91` ("Stats unavailable — retrying").
  - **IPv6 protocol select labels on `Reaper_Firewall.asp`** — `RFW_252` ("Both") exists; **"Other"
    still needs a key.** Safe now (the `value="TCP|UDP|BOTH|OTHER"` attributes are pinned — **do not
    remove them**: `rc/firewall.c` `strcmp`s the submitted value, so an unpinned translated label
    would have broken the rule format in 24 languages). Do the `RFW_*` namespace as one job, not
    piecemeal. **Do not reuse ASUS's `option_both_direction`** for "Both" — JP/CN/TW render it as
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

## Pending verification

*A change has been made and is believed to fix the problem. What is missing is **confirmation**,
and only two things count: a report back from the person who reported it, or on-hardware validation
of a path the maintainer cannot exercise. Build-verified, replay-verified and gate-passed prove a
change is **in** the image, not that it **works**.*

*Every item names the evidence that settles it. Items leave in one of two directions: **confirmed**
→ changelog, deleted from here; **not confirmed** → back to [Open bugs](#open-bugs--under-investigation)
with what the attempt ruled out.*

> **Nothing in this section is done.** A fix shipped is not a fix proven.

---

### v2.7.6 (2026-08-23) — PBR boot self-heal at the root, 40-domain paste, Warden status/lock/teardown

*Built + shipped for BE96U + BE92U only; the reporting RT-BE88U is on public v2.7.1 and needs a
sibling build (its branch sits at v2.7.3) before it can confirm anything below.*

- **[P1] A reboot brings up the full `REAPER_PBR` mangle chain with no UI Apply** (`apply.sh` now
  materialises the object sets itself; `firewall.c` re-applies under the firewall lock). **Settles
  when** a box reboots and `iptables -t mangle -S REAPER_PBR` is complete before anyone touches the
  UI; diag §14e reads `expected M live M`. Supersedes the v2.6.9 "post-reboot self-heal"
  confirmation — that attempt FAILED 2026-08-23 (chain short, a UI Apply healed it) and exposed
  this root cause. **[owed — reporter]**
- **[P1] A 40-domain object saves in one paste** (paste-tolerant normaliser, persistent error
  message, textarea/buffer limits raised). Supersedes the v2.6.9 one-paste check — the 2026-08-23
  attempt on v2.7.1 failed (a few at a time saved; one paste did not). **[owed — reporter]**
- **[P2] The Warden page under load shows "Stats unavailable — retrying"** (RWDN_91) instead of
  silent static placeholders; `time sh /tmp/rwarden/stats.sh` returns within the shortened lock
  wait. **[owed — reporter]**
- **[P2] An addon's `ip rule` at pref 9001–9115 survives `restart_firewall`** — the PBR teardown
  now deletes only rules carrying our fwmark/0xf0000, so domain_vpn_routing's rules are left
  alone. **[owed — reporter]**

### v2.7.5 (2026-08-23) — dedicated Addons rail section

- **[P2] The Addons section renders with a real addon installed** (scMerlin / YazFi on the BE92U
  tester): one "Addons N" group at the end of both the shell and dashboard rails unfolding the
  list, auto-open on an addon page; stock menus keep their tab bars with addon tabs stripped; an
  addon page's tab bar is the addon set. Mock-verified against three injection styles only — never
  a real addon. Supersedes the v2.5.9 "addons rail identical on dashboard and shell" confirmation:
  that rail was replaced wholesale by this one. **[owed — reporter with addons]**

### v2.7.4 (2026-08-23) — first-boot gate-3 fix (nav dead / "Secure Your Router" flash)

- **[P1] Nav works on a box with zero guest networks.** The state.js gate keyed on
  `sdn_rl == default` is gone (`w_Setting` is the only Wi-Fi-configured signal). **Settles when**
  the BE92U reporter navigates normally on v2.7.4+ after their factory reset. **[owed — reporter]**
- **[P2] Factory-reset regression:** both wizard steps still fire on a clean box (the `w_Setting`
  path is untouched, but the gate change owes the check). **[owed — metal]**

### v2.7.3 (2026-08-23) — Gatekeeper learns AiMesh, guide everywhere, themed dialogs

*Flashed on the owner's BE96U 2026-08-23 — diag v1.3.6 ran CLEAN (that run also confirmed the
v2.7.2 diag fixes: the churn rate reads `~197/h` with the band, and §14d's duplicate line is
gone). Remaining:*

- **[P1] AiMesh onboarding with quarantine ON.** **Settles when** a node onboards on a
  quarantine-enabled box, and mesh heartbeats survive quarantine being enabled on an established
  mesh; diag §14b shows the registry MACs and the onboarding window opening and closing. (The
  owner's box runs exactly this config — the next node add is the live test.) **[owed — metal]**
- **[P3] Guide links glance:** the `?` topbar buttons and the five page dots open
  `REAPER-GUIDE.md` at the right sections; the About button and the first-boot mention render.
  **[owed — glance]**
- **[P3] Themed USB format / eject dialog** (Enter must NOT confirm a format) and the
  **backup-card alignment** on the Administration page. **[owed — glance]**

### v2.7.2 (2026-08-23) — restore-proof Analyzer history, one-file full backup

- **[P2] Analyzer history survives reboots and flashes.** **Settles when** month-to-date survives
  a firmware flash and year totals track on a USB-store box (the reporter's IPv6 devices, or the
  owner's box — USB store + pre-NTP boots is exactly the fixed case; watch it across the coming
  reboots). **[owed — reporter / owner watch]**
- **[P2] Full backup round-trip.** **Settles when** a metal pass confirms: the `.rbk` downloads,
  restore on the same model round-trips (settings + gk list + fw lists + pbr rules + fqdn sets),
  a foreign-model archive is refused, and the post-reboot banner completes the Reaper half.
  **[owed — metal]**

### v2.7.1 (2026-08-22) — security review, i18n sweep

- **[P1] Per-boot `http_id` + Referer check.** **Settles when** after a reboot `nvram get http_id`
  is `TID` + 24 hex (not `TIDe855a6487043d70a`), every Reaper page's controls work (Gatekeeper
  actions, Firewall save/apply/keep, Policy Routing apply/keep, Storage export/import, Diag run),
  a stock page such as Wireless still applies, and a cross-site GET of
  `/reaper_gk.cgi?action=config&enable=0&http_id=<value>` from another origin is refused with
  `cross-site request refused` in the log. **Also check** anything external that talked to the
  router with the old constant (ASUS Router app, amtm/scripts): those read the token from a rendered
  page or use their own login, and must still work. **Partly confirmed 2026-08-22 (owner, v2.7.1
  metal):** `nvram get http_id` = `TID` + 24 hex after boot, and *Collect diagnostics* ran from the
  page through the new token + Referer check. Still owed: the other pages' controls (Gatekeeper
  actions, Firewall Apply/Keep, Storage export/import), a stock-page Apply, the cross-site GET
  refusal, and the ASUS app / scripts. **[owed — metal]**
- **[P2] Diag on a device named `HOST-`.** **Settles when** a client with hostname `HOST-` is on the
  LAN and *Collect diagnostics* completes in the usual ~12 s with the name shown as `[HOST-n]`.
  **[owed — metal]**
- **[P3] Translations glance.** **Settles on** switching the language selector to any non-English
  pack: every Reaper page renders (no blank page, no raw `<#...#>`), with the 12 new strings and the
  three refreshed ones in English. **[owed — glance]**

### v2.7.0 (2026-08-22) — Reaper settings backup, /jffs health

- **[P2] Export / import round-trip.** **Settles when** Export on the Storage page downloads
  `reaper-settings-<model>-<version>-<date>.json`, and importing it on a reset box logs
  `reaper_cfg: settings imported: N flag(s), M list(s), 0 rejected`, Gatekeeper's device list and
  Warden's country selection are back immediately, and the Firewall / Policy Routing pages show the
  lists as drafts that Apply + Keep make live. **[owed — metal]**

### v2.6.9 (2026-08-22) — field feedback (Policy Routing + Firewall objects)

- **[P1] Firewall lists on /jffs.** **Settles when** the first boot logs `N list(s) migrated from
  nvram to /jffs/reaper_fw/lastgood`, `nvram get reaper_fw_obj` is empty afterwards, and the
  Firewall page's Keep still writes `/jffs/reaper_fw/lastgood/.committed`. With the Firewall engine
  OFF, a domain list edited on the Policy Routing page must survive a reboot once the routing Keep
  is pressed. **Partly confirmed 2026-08-22 (owner, v2.7.1 metal):** engine ON with an empty config
  migrated to `store=/jffs` cleanly (nothing to move, nothing logged - correct). **The 40-domain
  one-paste check FAILED 2026-08-23** (reporter, v2.7.1: a few at a time saved, one paste did
  not) — root-caused to the page's paste handling, fixed in v2.7.6; that check now lives under
  v2.7.6 above. Still owed here: after-reboot persistence and the engine-OFF routing-Keep path.
  **[owed - reporter]**
- **[P1] Address-list source rule.** **Settles when** a rule with three addresses shows
  `a.b.c.d +2` in the table, `iptables -t mangle -S REAPER_PBR` carries three `-s` mark rules, and a
  bad entry in the paste is refused by the page with the entry named. (The reporter's IP-list paste
  on v2.7.1 blanked the page until httpd restarted — tracked as its own entry under
  [Open bugs](#open-bugs--under-investigation); v2.7.6's paste normaliser may be the cure.)
  **[owed — reporter]**
- **[P2] Post-reboot self-heal — NOT CONFIRMED, superseded.** The 2026-08-23 attempt failed (chain
  short after a reboot; a UI Apply healed it): the heal could not work because the object sets were
  never materialised at boot. Root cause fixed in v2.7.6 (`apply.sh` builds its own sets); the
  confirmation moved there.

### v2.6.8 (2026-08-22) — USB format: ext4 / ext3 / ext2

- **[P2] ext format round-trip.** **Settles when** a spare stick formatted as ext4 from the USB
  page comes back mounted (partition line shows `ext4`, the label given), `/tmp/disk_format/<dev>.log`
  holds mke2fs output, and Samba/the store can use it; ext3 and ext2 likewise. **[owed — metal]**
- **[P2] NTFS from the Reaper page.** **Settles when** formatting as NTFS from the Reaper USB page
  produces an NTFS disk (before v2.6.8 it silently did nothing). **[owed — metal]**

### v2.6.7 (2026-08-22) — Policy Routing close-out

- **[P1] Apply-and-confirm.** **Settles when** Apply on the Policy Routing page shows the Keep /
  Revert card with a live countdown, `cru l` lists `reaper_pbr_cc`, letting it expire restores the
  previous rules (log: `commit-confirm: reverted to the last confirmed routing rules`) and Keep
  writes `/jffs/reaper_pbr/lastgood/.committed`. A reboot inside the window must boot the last
  confirmed rules (log: `a change was still awaiting confirmation at reboot`). **[owed — metal]**

- **[P1] WireGuard target actually diverts.** **Settles when** a rule `src <host> → WGC1` makes that
  host's public IP become the tunnel's exit (and `cat /proc/blog/skip_wireguard_network` lists the
  host's /32), and a destination-list rule → WGC1 diverts the list with the LAN /24 listed and the
  `LAN-wide flow-cache bypass` log line present. Stopping the WG client must BLOCK the selected
  traffic (prohibit), not leak it. **[owed — metal, needs a WireGuard client]**

- **[P2] IPv6 leg.** **Settles when** `ip6tables -t mangle -S REAPER_PBR` carries a MARK per rule
  and `ip -6 rule` shows the 900x/910x pair; an IPv6-capable destination in a list routed to a
  v4-only tunnel is unreachable (blocked), not leaked. **[owed — metal, needs IPv6]**

- **[P2] Rule list on /jffs.** **Settles when** the first boot on v2.6.7 logs `rule list migrated
  from nvram to /jffs/reaper_pbr/lastgood/rulelist`, `nvram get reaper_pbr_rulelist` is empty
  afterwards, and a 20-rule list survives Keep + reboot (diag §14b-style check: file present,
  nvram value absent). **[owed — metal]**

- **[P2] About / Warden field items.** **Settles on** a glance: About shows `501 — series as of
  v2.6.5` (or the plain count after the cut); Warden's count bar carries `Prefixes loaded: N`.
  **[owed — glance]**

### v2.6.5 (2026-08-22) — Gatekeeper multi-network close-out

- **[P1] A new SDN is protected immediately.** **Settles when**, with Gatekeeper on, creating a
  Guest Network Pro profile logs `gatekeeper: network set changed - enforcement re-applied on every
  bridge` within seconds and `iptables -nL REAPER_HOOK_F` shows a `REAPER_GKF` jump for the new
  bridge; deleting it removes the jump. Also: `iptables -D REAPER_HOOK_F -i brN -j REAPER_GKF` by
  hand must be repaired by gkd within ~2 min with the `bridge(s) … not hooked` line. **[owed — metal, needs an SDN]**

- **[P1] Captive page on an isolated SDN.** **Settles when** an unknown device on an SDN with
  *Access Intranet off* gets the "awaiting approval" page (not a hang), while an *approved* device
  on the same SDN still cannot open the router UI. `iptables -nL SDN_FI | head -3` shows the
  `ctstate DNAT … dpt:80 ACCEPT` rule at the top, and it is back within 30 s after
  `service restart_sdn`. **[owed — metal, needs an SDN]**

- **[P2] IPv6 GUA covered.** **Settles when** on an IPv6-delegated box `ip6tables -nL REAPER_GKF |
  grep <mac>` for an internet-only device lists a DROP to the bridge's global prefix, and after a
  WAN reconnect (new prefix) the rule follows within ~1 min with the `IPv6 prefix changed` log line.
  **[owed — metal, needs IPv6]**

### v2.6.3 (2026-08-22) — Gatekeeper device list on /jffs (the 45-device wall)

- **[P1] More than 45 devices persist.** **Settles when** the reporter (RT-BE88U, ~58 devices)
  upgrades, sees `gatekeeper: device list migrated from nvram to /jffs/gatekeeper/rl (45 entries …)`
  in the log once, then approves the remaining devices and each one leaves "pending" and survives a
  reboot. Readback: `tr -cd '<' < /jffs/gatekeeper/rl | wc -c` = device count; `nvram get gk_rl`
  must be empty after migration. `reaper_diag` §14b shows the same numbers. (Owner-metal diags
  2026-08-22/23 read §14b's migrated counts correctly on a 34-device box; the >45-device wall
  itself still needs the reporter.) **[owed — reporter]**

- **[P2] Nothing else changed.** **Settles on** a glance: approve / block / guest / remove still
  apply immediately (no multi-second stall per click now that the nvram commit is gone), guest
  expiry still removes the entry, Devices page access chips still agree with the Gatekeeper page.
  **[owed — glance]**

### v2.6.2 (2026-08-21) — firewall layer order, Gatekeeper L3 leg, code-review batch A

- **[P1] Firewall layer order is fixed and survives every restart.** **Settles when**, on a box with
  Warden + Gatekeeper + the Firewall engine all enabled, `iptables -nvL REAPER_HOOK_F` lists
  `REAPER_WARDEN`, then `REAPER_GKF` (one per bridge), then `REAPER_FWF` — in that order — and
  `iptables -nvL FORWARD | head -3` shows exactly ONE Reaper jump (`REAPER_HOOK_F`) at position 1
  with no direct `REAPER_FWF`/`REAPER_WARDEN`/`REAPER_GKF` jumps left; then after each of
  `service restart_gk`, `service restart_rwarden`, `service restart_reaper_fw`,
  `service restart_firewall` the same listing is unchanged. The decisive behaviour test: a Firewall
  *allow* rule for a port must NOT let a geo-blocked source (`ipset test rw_g_<cc> <ip>`) or a
  Gatekeeper-blocked device through. Also: a hung-hook scenario (`iptables -D REAPER_HOOK_F -j
  REAPER_GKF` by hand) must be repaired by gkd within 30 s with the "enforcement chains missing"
  log line. **Partly confirmed:** diag §14c on owner metal (2026-08-22/23 runs) reads `@pos 1`
  with `legacy direct jumps … 0`. Still owed: the restart-survival listing, the decisive behaviour
  test, and the hung-hook repair. **[owed — metal]**

- **[P1] "Internet only" device cannot reach another network.** **Settles when** a state-2 device on
  an SDN that is *linked* to the main LAN in Guest Network Pro cannot ping/SMB a main-LAN host,
  still has WAN, and still resolves via a main-LAN AdGuard advertised by that SDN; a full-approved
  device on the same SDN is unchanged. `iptables -nvL REAPER_GKF | grep <mac>` shows the 53-RETURN,
  per-subnet DROP, RETURN sequence. **[owed — metal, needs an SDN]**

- **[P3] SDN devices show hostnames in Gatekeeper.** **Settles on** a glance at a guest-network
  device row. **[owed — glance]**

- **[P3] Batch A is behaviour-neutral.** **Settles on** a glance: Advisor `get_overview` still
  returns the three meminfo lines; Policy Routing and Traffic pages render; first-boot language
  picker works. **[owed — glance]**

### v2.6.1 (2026-08-21) — diag store section, kp v6
*(The nvram-read guard was CONFIRMED on owner metal 2026-08-23 — the diag reads `reaped hung
nvram: 2`, which is also field evidence for the underlying libnvram netlink bug. The WGC "rule
inactive" chip was superseded by v2.6.7's real WireGuard support — its confirmation lives there.)*

- **[P3] Diag section 17 reports the durable store.** **Settles on** a glance: `reaper_diag` §17 on a
  USB-store box prints the `syslog.mirror` path/size/span and "incident bundles: none (… absence is
  healthy)". **[owed — glance]**

- **[P3] Warden nightly update no longer logs `geo v6 fetch FAILED for kp`.** **Settles on** the next
  04:30 update log. **[owed — glance]**

### v2.6.0 (2026-08-21) — QoS Classful queue rebuild

- **[P1] GT-BE98 (and any port that rejects the recreate) keeps IPv4 with QoS Classful on.**
  `rq_rebuild()` in the generated `/tmp/qos_hwc.sh`. **Settles when** the reporter, on a v2.6.0
  GT-BE98 image with `qos_type=11`, has IPv4 after boot AND `tmctl getqcfg --devtype 0 --if eth0
  --qid N` answers for N=1..5. Expected syslog: `hwqos: setqcfg qid 1 priority 5 REJECTED` + `class
  queues restored at the stock priority layout`, with NO `FATAL` line (a `FATAL` means even the bare
  recreate failed — report it). Also worth capturing WHY the recreate is rejected there (run the
  failing `tmctl setqcfg` by hand without `2>/dev/null`). **[owed — reporter, GT-BE98 metal]**

- **[P2] RT-BE96U unchanged in behaviour.** **Settles when** a v2.6.0+ BE96U shows qid 1..5 at
  priority 5..1 after `restart_qos` and no `hwqos` fallback line. **[owed — metal]**

### v2.5.9 (2026-08-21) — the trusted tester's batch

- **[P1] Warden country sets populated after a reboot.** **Settles when** a box with countries
  selected reboots on this image and `ipset -t list rw_g_<cc>` shows a non-zero entry count for every
  selected country, no `rwarden: cache restore for set` lines, and the Warden tile reads the prefix
  count (not amber). First boot after upgrading from a pre-v2.5.9 cache is the interesting case.
  **[owed — reporter, reboot + ipset readback]**

- **[P2] Wireless AiMesh node shows its backhaul band on Devices, with the AiMesh Node chip.**
  **Settles when** the reporter's node row shows the band and the orphan backhaul-STA row is gone; a
  *cabled* node must still read Wired. (The maintainer has no mesh.) **[owed — reporter]**


- **[P2] Policy Routing works with the Firewall engine OFF.** **Settles when** a domain-list rule
  steers traffic with `reaper_fw_enable=0`: `ipset list rwfw_<list>` populated, `iptables -t mangle
  -vnL REAPER_PBR` shows the match loading, `cru l` shows `reaper_fw_dns`. **[owed — metal]**

- **[P2] Domain lists survive a reboot.** **Settles when** after a reboot, before any client lookup,
  `ipset -t list rwfw_<list>` is already non-empty. **[owed — metal]**

- **[P3] Edit flows on the Firewall page (8 lists) and Policy Routing — page check.** Modify → Save
  replaces in place, Cancel restores Add, a renamed domain list updates the rules that referenced
  it. **[owed — page check]**

### v2.5.8 (2026-08-20) — upstream 3006.102.8_4 alignment

- **[P2] UPnP gaming fix (completed revert of the Asus jump patch).** **Settles when** a game that
  forwards its port via UPnP (the PS5 is the known reproducer) accepts inbound connections.
  `iptables -t nat -vnL PREROUTING | grep VUPNP` and `iptables -vnL FORWARD | grep FUPNP` should both
  be empty, with the VSERVER→VUPNP jump present. **[owed — metal]**

- **[P3] miniupnpd 2.3.11 / OpenVPN 2.7.6 report their real versions.** **Settles on** a glance at
  the System Log / VPN page version lines on the flashed image. **[owed — glance]**

### v2.5.4 / v2.5.5 — staged batch

- **[P2] QoS strict-priority order corrected — drain-under-load owed.** Queue config read back
  correct on the lab RT-BE96U (q1=5…q5=1). **Settles when** a type-11 upload under real classified
  congestion shows the higher classes draining ahead of the catch-all. **[owed — metal, load]**

- **[P2] Speed test no longer ends on a brief stall.** `level_err_cnt` was consumed once per 200 ms
  poll (so `LEVEL_ERR_MAX=50` meant "10 s of a stalled tail"); now counted once per new buffer entry
  with consecutive-error semantics, run still bounded by `test_timeout`. **Settles when** several
  back-to-back runs — including one that stalls mid-transfer — complete or fail on the real timeout.
  This is the multi-run-on-metal test the item always needed; it slipped three rungs before the fix
  landed. **[owed — metal, multi-run]**

- **[P3] Wireless Auto-Scan reports instead of auto-pinning.** A sweep now always restores the
  pre-sweep channel/width; only "Pin best" commits. (This reversed a deliberate v2.3.7 choice —
  owner decision 2026-08-13; do not "fix" it back.) **Settles on** a glance: run a scan, Control
  Channel unchanged afterwards, "Pin best" still applies. **[owed — glance]**

- **[P2] PPPoE stale-session bounce (v2.5.5).** See the ONT item under Open bugs. **Settles when** a
  box that reproduces logs the `rwatch` bounce line and regains connectivity without an ONT reboot.
  **[owed — tester]**

- **[P2] chpass CSRF gate — validate on a real factory-reset flow.** The `http_id` check is gated to
  the default-password window and `Reaper_FirstBoot.asp` sends the token; the first-boot credential
  path has a lockout history. **Settles when** a clean factory-reset setup completes. **[owed — metal]**

### Older, still unconfirmed

- **[P1] IPSec — a client actually establishes a tunnel.** Server side is metal-confirmed on v2.5.4
  (charon up, UDP 500/4500 bound, both profiles loaded). **Settles when** a phone/laptop SA goes
  `up`; also un-exercised: the IPSec *client* (connect-out) and Instant Guard pairing. **[owed]**

- **[P2] The v2.5.3 firewall-emission changes owe a metal glance** (admin-management RETURN scoped to
  INPUT, port-forward guards, atomic GK/Warden `apply.sh`, zone-matrix cap). **[owed — glance]**

- **[P2] Warden country counters attribute after the geo-first reorder** (2026-08-18). `iptables
  -nvxL REAPER_WARDEN | head -20` → the `rw_g_<cc>` rules sit above `rw_threat` and carry non-zero
  counts on a box that previously attributed everything to the feed; the Top Blocked Countries table
  moves with the total. A discontinuity in banked history at this version is expected. **[owed]**

- **[P2] The 1500-byte PPPoE MTU fix against the line that reported it** (v2.4.9 + v2.5.0 VLAN-parent
  widening). `grep -i "up with MTU" /tmp/syslog.log` → `MTU 1500` = negotiated; `MTU 1492 (requested
  >1492; peer declined RFC 4638)` = provider refused (not ours). WAN iface should read mtu **1508**
  while up; `ip link show vlan6` should read 1508 on a tagged line. Do not use `logread`. **[owed]**

- **[P2] The Call of Duty / UPnP report** (v2.4.6 removed the phantom `WANPPPConnection` and the
  IGD:2 description on the default daemon). `grep -i "IGD desc" /tmp/syslog.log` → shows whether the
  console fetched the description, which version, and its User-Agent. Also confirm the reporter's
  `upnp_pinhole_enable` (pinholes on = IGD:2 served, the configuration that broke the PS5). **[owed]**

- **[P2] The AiMesh-node theming fix** (`bb580b6370`, three-line guard) has never been flashed on a
  node; a node already stuck in the loop must be updated from the main router's AiMesh flow. **[owed]**

- **[P2] IPv6 per-device attribution (v2.4.4) on a box that has IPv6** — the reporting RT-BE88U
  (native /56). With a large download: the device row tracks the WAN line (not just ACKs), a
  dual-stack device stays one row, and the collector's `nd_n` agrees with `ip -6 neigh show dev br0`.
  **[owed]**

- **[P3] Local-build provenance wiring** — the `gen_provenance.sh` call in `_rb_variant()` has now
  run through `build_be96u.sh` (v2.5.8+ builds print the "provenance stamp" line). **Closes on** the
  next look at a build log; drop this entry then. **[owed — glance]**

- **[P3] Dashboard logo no longer jumps vs other menus (v2.5.1/v2.5.3 rail geometry)** and
  **Firmware page Mesh Nodes card at the bottom (v2.5.1)** — two glances at the built image. **[owed]**

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

- **[P3] Sibling port gap: `Tools_Sysinfo.asp` sits in the protect set,** so rt-be88u (and likely
  every sibling) lags canon's 2026-08-17 temp-chart rewrite and `searchIspNameProfile.js` (found
  2026-08-23 during the BE92U port). Raise at the next sibling rung. **[owed]**

- **[P3] Warden custom feeds — two residual ceilings.** `rw_threat` now has `maxelem 524288`
  (v2.5.4); **still owed:** surface the entry count against that limit in the Warden UI. Update
  runtime is user-extensible (eight custom feeds at `--retry 2 --max-time 40` ≈ +16 min); overlap is
  solved (per-run `flock`, shared fold/stats lock); **still owed:** a lower per-feed timeout for
  custom entries so one slow feed cannot stall the window.

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
