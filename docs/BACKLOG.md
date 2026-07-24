# RT-BE96U "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done/verified), **[blocked]** (external cause),
**[shelved]** (deliberately deferred), **[cosmetic]** (polish, non-blocking).

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md); strategy/roadmap is in
> [`ENTERPRISE-ROADMAP.md`](ENTERPRISE-ROADMAP.md). Completed backlog items are
> moved to the changelog and removed from this file (housekeeping pass 2026-07-18).

---

## Testing / validation owed

- **v1.7.3 — Gatekeeper reliability (RT-BE96U), FIRST on-hardware exercise.** Gatekeeper had
  never run on real hardware before this rung, so v1.7.3 *is* its first metal test. Verify on
  device: (a) **anti-lockout** — enable Gatekeeper in quarantine mode from one device with
  another device asleep; the household is not mass-quarantined and the **HTTPS admin page stays
  reachable** so the feature can always be turned off; (b) **cold-boot arming** — with Gatekeeper
  on, full power-cycle, then confirm the syslog shows it arms and the enforcement chains are
  actually present (`iptables -nvL FORWARD | grep REAPER_GKF`; `ebtables -L FORWARD | grep
  REAPER_GK`), and that `/tmp/gk/apply.sh` has the real bridge in `LANIF`; (c) the page shows
  "Arming" then "Active", and toggling Gatekeeper off clears it. This image also folds in the
  v1.7.2 commits (AiMesh node onboarding, static-DHCP, theme-flash, full menu i18n).
- **v1.7.5 + v1.7.6 (RT-BE96U) — BUILT, metal test owed.** v1.7.5 = C6-twin command-injection fix
  in `libpasswd` (security rung; MCP+noMCP shipped). v1.7.6 (built 2026-07-23, MCP) = the VPN
  Client+Server theme **ping-pong resize-loop** fix (was: server-list cards stuck stock-colored +
  constant reflow/XHR churn = "endless loading"), plus the speedtest nested-iframe auto-size in
  `reaper_shell.asp`. Verify on device: VPN Client (all protocol tabs) + VPN Server render themed
  with no endless-loading churn; the Adaptive-QoS Internet-Speed page shows a single scrollbar.
- **Ship completion owed (v1.7.2–v1.7.6).** Only the RT-BE96U **MCP** variant is built for these
  rungs (v1.7.5 shipped both variants). Still owed before a full release: the **noMCP** RT-BE96U
  variant for v1.7.6, and the **sibling fan-out** (RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro)
  with an updated `SHA256SUMS-v1.7.6.txt`.

- **v1.6.4 — SHIPPED 2026-07-19 (both variants), metal test owed.** Tree at commit
  `0bf494a148` on `be96u-only`. MCP sha `7e1adcd7…`, noMCP `c126beb8…`, `SHA256SUMS-v1.6.4.txt`;
  both variants `MAKE_EXIT=0`, built==shipped verified, staged fs confirms the audit strings, the
  numeric-converted FirstBoot tokens, and the removed VPN cache-bust query. Batches four workstreams:
  1. **VPN nested-frame theme 404 fix + palette sweep** (VPN Client/Server; see `CHANGELOG.md`).
  2. **SDN/MLO expand cut-off fix** + **tablet/iPad viewport pan** (see `CHANGELOG.md`).
  3. **i18n full pass** — `Reaper_FirstBoot.asp` tokenized (it postdated the earlier sweeps and
     was 100% hardcoded English); 14 new `RFB_*` keys **translated across all 25 dicts** (reused
     `CTL_secure` / `PM_Confirm_Pwd` / `FreeWiFi_Continue`); the other 6 Reaper pages re-verified
     clean; dicts now 5692-key lockstep. Machine-assisted translation — native review owed.
  4. **Pre-build security/quality audit** (2-agent adversarial scan of the v1.6.2→v1.6.4 delta,
     reachability-disciplined). **No exploitable issues** (injection / XSS / memory-corruption
     all clean). Fixes applied: `rchqd` logging decoupled from the JSON file (full RAM disk can no
     longer silence it), torn-write can't clobber the last good snapshot, radio state closed out
     on wireless restart, log throttle moved to `CLOCK_MONOTONIC`, per-tick `wl` fork load halved;
     web-side ResizeObservers released on frame navigation, tablet width-grow made convergent; a
     permanent lint rule added for JS-context dict keys.
  - **Verify on device (v1.6.4):** a wide page (e.g. Advanced Wireless) pans on iPad in portrait +
    landscape and the dashboard is unaffected; the SDN cut-off repro (select a network, Advanced
    collapsed, expand General) plus the MLO page; the first-boot wizard renders in a non-English
    language; and a factory-reset flow still completes. (VPN Client/Server colors moved to the
    v1.7.6 check above — the ping-pong loop that masked them is fixed there; the v1.6.3 rchqd syslog
    check is done.)

- **First-boot credentials wizard (shipped v1.5.5) — factory-reset metal test.** Factory
  reset → wizard appears → no page/dashboard reachable until username+password set → forced
  to the wireless page until a WiFi PSK is set → dashboard → values persist → all editable
  later; also confirm an *upgrade* (no reset) does **not** trigger it. **Known limitation
  (v1.5.5):** the WiFi step releases once WiFi is *configured* (`sdn_rl` changes), so a user
  could save it **open** and skip a PSK — optional tightening is to require a non-empty PSK
  (currently uses the stock `sdn_rl` signal for stability). Feature record in
  [`CHANGELOG.md`](CHANGELOG.md) v1.5.5; it replaces the stock forced password gate and is
  the concrete mitigation for deferred finding **H15** (see the AA26-194A section below).

*(AI Advisor backlog retired 2026-07-19 per owner: functional as shipped — arming, LAN-only
bind, token auth, redaction, Mode-B USB 3FA, and the network-diagnostics tier are all
metal-confirmed; the remaining physical/edge sub-tests are waived. The Advisor is expected to
be expanded further for public use; that work will be scoped fresh when it starts. The
optional hardware-token (FIDO2/U2F) anti-clone idea is preserved in project memory.)*

- **Cron?** Asses users feedback: I've gone back to Merlin for now. The experience was great 
until I realised some of my custom logs weren't updating which, along with some observations, 
lead me to believe cron jobs weren't running right. No time to diagnose. I may be wrong.

- **Gatekeeper Feedback** We already adjusted the code but I didn't want to leave this feedback 
 out as it could be benifical in the case the new changes do not work we can roll it back and 
 take a different approach. 
 "One more observation regarding the "Gatekeeper" section: After a router reboot, the feature 
 works entirely as intended. The section activated fine, and all existing devices were 
 displayed as approved. I tested blocking a few devices—the restriction works properly. New 
 devices that haven't connected to the network before correctly land in the "Pending approval" 
 list. Everything functions as expected here: approving a device grants access, while rejecting 
 it blocks the connection. So it seems the glitch and router crash only occurred during the 
 initial activation of "Gatekeeper". After subsequent reboots, the section appears to be working 
 flawlessly."

## UI / UX polish

- **Restart/Boot Effciency** Investigate why the wifi and router reboots several times and 
  takes 10 min to stablize. Potential reordering of boot could make this quicker.
- **WD** REAPER Wireless Diagnostics need to be reworked for visual clarity and information.
- **Dungeon Master** The admin logged in when the Gatekeeper is activated is automatically 
  added to the approved list with full access.

*(Fixed items moved to `CHANGELOG.md`: the split-second **stock-theme flash** ("Old Style") —
first cut v1.7.2, completed for the heavy Wireless/DHCP pages in v1.7.4; the **static-DHCP client
picker** ("StaticDHCP") — un-clipped in v1.7.2, then re-anchored to its input and opened upward in
v1.7.4; the first-boot wizard language selector — v1.6.6; VPN submenu colors, tablet/iPad layout,
and the SDN page cut-off — all v1.6.4; Wireless Diagnostics reports follow the router language via
the v1.6.0/v1.6.1 page tokenization; and the v1.6.0 DICT translation pass + truncate/hover-tooltip
mechanism, the AI Advisor Refresh-button move, and the Login/Logout favicon.)*

## Known issues (cause identified)

- **Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul
  BSS is still created even when every feature that would use it is disabled, spamming
  the log with RADIUS codes for an unused radio. Traced to a **closed-source Broadcom
  blob**; a boot-time script to suppress it based on device settings did not work and
  was reverted. [blocked — blob; risk-accepted]

## Router hygiene — CISA/FBI/NSA advisory AA26-194A (Russian FSB "Static Tundra")

Joint advisory *"Improve Router Hygiene to Protect Against Russian State-Sponsored
Targeting"* (**AA26-194A**, 2026-07-13; NSA/CISA/FBI/DC3 + partners). FSB Center 16 actors
(Berserk Bear / Energetic Bear / Dragonfly / **Static Tundra**) scan internet-reachable
routers for **default or common SNMPv1/v2 community strings** and default/weak admin
credentials, then copy the device config and exfiltrate it (via TFTP on the exploited
Cisco path). The named exploit — **Cisco Smart Install / CVE-2018-0171** — is Cisco-specific
and **not applicable** to this platform; the transferable defenses are the router-hygiene
items below. Source: <https://www.cisa.gov/news-events/cybersecurity-advisories/aa26-194a>.
*(The primary credential item — the unbypassable first-boot wizard — shipped in v1.5.5; see
`CHANGELOG.md` and the metal-test entry at the top of this file.)*

- **SNMP hardening.** Default state **verified off** in the live audit 2026-07-19
  (`snmpd_enable=0`, `snmpd_wan=0`, no snmpd listening) — the primary advisory vector is closed
  by default. Remaining (optional, **[shelved]**): the SNMPv3-`authPriv` / reject-common-strings
  enhancement for users who *enable* SNMP (revisits the shelved SNMPv3 line in
  `PACKAGE-UPDATES.md`). Full posture in `LIVE-AUDIT-2026-07-19.md`.

- **Detection / logging for the advisory TTPs.** Surface and log config-exfil attempts and
  anomalous SNMP polling (spoofed-source reads). Ties into the **Remote syslog push/fetch**
  and **NIST-grade auditing** items under *Features to add*.

## Features to add

- **Remote syslog push/fetch.** The router can already send its log to a remote
  collector (send-only). Add the ability to **push to / be fetched by** analytics
  systems — most SIEM/analytics pipelines are push-based.
- **NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST
  baseline.
- **QoS download — latency-under-load baseline (optional).** The v1.6.5 download-cap footgun fix
  and cake headroom consistency shipped (see `CHANGELOG.md`); the per-class-HW-download question was
  investigated and closed as not-feasible/already-optimal (full analysis in
  [`QOS-DOWNLOAD-INVESTIGATION.md`](QOS-DOWNLOAD-INVESTIGATION.md)). The one open, optional item is a
  **latency-under-load measurement** (a download-saturation run with a concurrent ping) to quantify
  the bufferbloat baseline and confirm the policer headroom holds full rated speed with lower ping.
  Needs an active test; no wireless restart required.

*(Done in v1.6.1, moved to `CHANGELOG.md`: the Channel-Quality **Auto Scan** + downloadable
landscape report, the **Clear-results** button, and the opt-in passive channel-health daemon
`rchqd`.)*

## Code-scan findings — v1.5.9 6-agent sweep — SHIPPED in v1.6.0 (2026-07-17)

The v1.5.9 6-agent audit of the Reaper-owned surface (**no critical / high / reachable
external vuln**; ~87 hardening patches verified sound; both daemons judged "unusually
defensive") left a short list of survivors, **all addressed in v1.6.0** (see
[`CHANGELOG.md`](CHANGELOG.md)): the `rtrafd write_live()` nvram cache (30→3/s), the
top-talker MAC cache, `poll_ifaces` open-once + `pread`, the ~1 Hz throttle on the
Analyzer Live tables, all 83 ring-`calloc` NULL-checks, the `rmcpd popen_pid` fd/zombie
leak, the `rmcp_client` + `lan_ifname` input validation, the AI Advisor `saveSettings`
`http_id` + response check, and the `Reaper_QoS.asp` / `state.js` / `watchdog.c` SLOP
cleanups. (These live in files identical across all four model branches, so folding them
onto the sibling branches is a clean shared rung when those are next bumped.)

**Deliberately deferred (with reason), still open:**
- **`poll_fcache` O(n²)→hash pairing** (`rtrafd.c`). Bounded to ≤1536 flows every 5 s and
  it sits in the metal-validated per-client accounting path — a rewrite of a millisecond-
  scale loop isn't worth the regression risk. Revisit only if a flow-heavy box shows real
  cost. [shelved]
- **`poll_classes` 7× `tmctl` popen batch** (`rtrafd.c`). Metal already measured 2–3 % CPU
  at the class-poll cadence; treating this as a non-issue per the prior finding. [shelved]

## Documentation

- **Note the non-functional retained features.** Document that the firmware
  update-check and the (removed) security-check UI do nothing on Reaper and are
  retained only for potential future use.
- **Annotate the system defaults.**
- **Write a user guide** for other users.

## Packages — [shelved]

- **Samba 3.0+ investigation** and **net-snmp update / SNMPv3.** Captured in
  `PACKAGE-UPDATES.md` and currently **shelved** (the EOL residual risk is accepted as
  LAN-only and manageable). Listed here for visibility; revisit from that doc's
  execution-order table if the decision changes.

## Platform / expansion

**Model version status (updated 2026-07-23):**
- **v1.7.6** — RT-BE96U (primary, hardware-validated line; **MCP built**, noMCP owed). Carries the
  full v1.7.x stack: v1.7.0 Gatekeeper, v1.7.1 security remediation + Network Map fix, v1.7.2
  (AiMesh onboarding + UI/i18n), v1.7.3 Gatekeeper reliability (no lockout + cold-boot arming),
  v1.7.4 DHCP-dropdown + theme-flash, v1.7.5 libpasswd C6-twin fix (both variants), v1.7.6 VPN
  theme ping-pong + speedtest iframe autosize.
- **v1.7.1** — RT-BE86U, RT-BE88U, GT-BE98, GT-BE98 Pro (all shipped in the v1.7.1 fleet). The
  **v1.7.2–v1.7.6 fan-out onto these branches is owed** (all shared source; a clean rung once
  RT-BE96U metal-passes).

- **RT-BE86U — brought to v1.6.0, built + shipped (both variants). [metal test owed].** The v1.6.0
  rung (hardening + full i18n; all model-agnostic shared source) was already committed on the
  `rt-be86u` branch (`40ff2e0b39`) — no cherry-pick needed. Both variants built clean
  (`MAKE_EXIT=0`) from `build_model_v160.sh` and shipped to the `reaper-firmware/` ladder (MCP sha
  `7ab959a0…`, noMCP `43ced442…`), folded into `SHA256SUMS-v1.6.0.txt` (12 images verify OK).
  Safety-tagged `rt-be86u-pre-v160`. No metal test planned — build-validated only. Note the
  RT-BE86U-specific `LnxHtmlEnumDict` SIGSEGV on Captive-Portal templates is non-fatal (valid
  images) but may leave those pages' lang-pack dict incomplete — spot-check before a metal test.
  **No `target.mak` jumbo issue** (BE86U does not kernel-enable jumbo frames, unlike BE88U).
- **RT-BE88U — brought to v1.6.0, built + shipped (both variants). [metal test owed].** Clean start
  from v1.5.0e (first-ever BE88U build: blobs restored, target.mak de-clouded, dual-band 10G/SFP+),
  advanced to v1.6.0. **Model-specific build note (regression watch):** BE88U uniquely
  kernel-enables jumbo frames — its `rt-be88u` `target.mak` block needs the full
  `EXTRA_KERNEL_CONFIGS="BCM_JUMBO_FRAME=y BCM_MAX_MTU_SIZE=10240 CONFIG_BCM_IGNORE_BRIDGE_MTU=y"`
  (matching RT-BE96U). The stock line was half-written (`BCM_MAX_MTU_SIZE` present as a kernel
  symbol but unanswered), which hangs the two-pass build at kernel `syncconfig` on the new-value
  prompt; completing the line fixed it. Jumbo frames matter for NAS/SMB use, so this is a core
  function, not cosmetic. No metal test yet.

## Known issues — ported models (GT-BE98 / siblings)

- **GT-BE98: empty Wi-Fi client list + ~half wired throughput + missing 6 GHz radio.**
  **[FIX SHIPPED v1.5.9 2026-07-17 — metal test owed].** Root cause found: the v1.5.0e/v1.5.1
  non-Pro build linked **four GT-BE98_PRO** closed objects as a version-skew workaround
  (`rc/broadcom.o`, `rc/private.o`, `shared/spwenc.o`, `shared/nvpriv.o`). `rc/broadcom.o` is
  the closed half of model-specific radio/board bring-up, and the Pro board (2.4/5/6/6 GHz)
  differs from the non-Pro (2.4/5/5/6 GHz) — the prime suspect for all three symptoms.
  **Fixed:** all four swapped to the **official ASUS GT-BE98 GPL 102_39274** objects; the
  compat shim reworked for the three helpers those objects predate. A quad-band bug in the
  new Wireless page (`RWIFI_MAXUNIT`, hid the 4th radio) was fixed alongside. Both BE98
  variants built + shipped at v1.5.9. **Metal test owed** — checklist in
  `reaper-firmware/METAL-TEST-GT-BE98-v1.5.9.md`; the decisive check is 4 radio rows (incl.
  6 GHz) on the Wireless page. If it still shows 3, the next suspect layer is the wl/dhd
  driver or dongle firmware. Original diagnosis notes retained below for the record.
- **GT-BE98 product/port images are the Pro's copies. [cosmetic]** The five
  `www/sysdep/GT-BE98/www/images/*` product/port PNGs (`Model_product_20.png`,
  `model_port.png`, `wanport_plugin*.png`, `GT-bg_header_20.png`) are byte-identical to the
  GT-BE98_PRO assets; the ASUS GT-BE98 GPL 39274 drop carries no www assets to source the real
  ones. The non-Pro UI may therefore show Pro product art. Would need art from a stock GT-BE98
  firmware extraction to correct.

  *Original field report (retained):* (1) the **Wi-Fi client list appears empty**
  (associated stations not enumerated), and (2) a **speed test shows ~half the actual wired
  (Ethernet) rate**. This is almost certainly a **source/blob issue,
  not a build artifact** — so a rebuild alone won't fix it; it needs real diagnosis.
  - **First step: confirm which image the tester flashed** — the v1.5.0e build (imported
    *gnuton* `DEV_3006.102.7_2` blobs from ASUS GPL 39099) or the v1.5.1 build (blobs
    **re-based** onto official ASUS GPL 102_39274). GT-BE98 is **Tier B** (second-hand blobs +
    `reaper_chanlist_shim` + a HAS_6G/quad-band gap that was only fixed in the v1.5.1 rebase),
    so version matters a lot here.
  - **Empty client list** → suspect the wl/dhd driver ↔ userspace station-info path
    (`wl assoclist`/dhd → `networkmap`/`stainfo` → httpd client table); a driver/userspace
    version skew or the chanlist/station shim is the prime candidate.
  - **~Half wired throughput** → suspect hardware flow-acceleration not offloading (Broadcom
    Runner/Archer/CTF flow cache); traffic falling to the slow path halves wired speed. Check
    `fcctl`/`archer` status and runner state on-device, and whether a blob/kernel-accel
    mismatch disabled offload. (Also sanity-check port link/duplex.)
  - Was build-validated only until now (no prior GT-BE98 metal test), consistent with a
    latent blob/accel issue surfacing on real hardware.
  - **ROOT CAUSE LIKELY IDENTIFIED (2026-07-15):** the **4th radio `wl3` (6 GHz) is missing** —
    a tester's stock `3006.102.7_2_rog` GT-BE98 shows wl0–wl3, the Reaper build shows only
    wl0–wl2. GT-BE98 non-Pro is quad-band (2.4 / 5 / 5-2 / **6**); wl3 = the 6 GHz radio. The
    `target.mak` GT-BE98 block had **`HAS_6G` unset in v1.5.0e** (documented latent gap) → 6 GHz
    radio never enabled → dashboard radio-count logic sees `wl3_nband` empty and drops it →
    3 radios. This also explains the empty-client-list (no 6 GHz clients) + ~half-throughput
    (a whole radio down). **`HAS_6G=y` was added in v1.5.1** — but v1.5.1 is **build-validated
    only, never metal-confirmed to actually light up wl3.** NEXT: (1) confirm which Reaper
    version the tester flashed; if `< v1.5.1`, flash **v1.5.1** and check wl3. (2) If v1.5.1
    still shows only 3 radios, `HAS_6G=y` is necessary-but-insufficient → investigate the
    `MODEL_GTBE98` band table (`wlif_utils_ax.c`), the generated `config_gt-be98` wl3 defaults,
    and whether the imported Tier-B (GPL-39274) blobs support the 6 GHz radio — then rebuild +
    **metal-test the 4-radio bring-up.** (Deferred per owner's "RT-BE96U first" directive.)
