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

- **v1.6.3 (RT-BE96U) — SHIPPED 2026-07-19, metal test owed.** rchqd degraded-event syslog
  trail (edge-triggered per radio, throttled 15 min, recovery line at NOTICE; JSON/UI advisory
  unchanged). MCP sha `100851e1…`, noMCP `a22707cf…`, `SHA256SUMS-v1.6.3.txt`; both variants
  MAKE_EXIT=0, staged `rchqd` carries the new strings, built==shipped verified. **Verify on
  device (needs `rchq_enable=1`):** a degraded 6 GHz channel logs one WARNING with chanspec +
  avg nopkt, no repeat within 15 min, and a recovery NOTICE when it clears.
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
  - **Verify on device (v1.6.4):** VPN Client (all three protocol tabs) + VPN Server colors
    (buttons, checkboxes, focus rings, jade connected-status); a wide page (e.g. Advanced Wireless)
    pans on iPad in portrait + landscape and the dashboard is unaffected; the SDN cut-off repro
    (select a network, Advanced collapsed, expand General) plus the MLO page; the first-boot wizard
    renders in a non-English language; and a factory-reset flow still completes. Plus the v1.6.3
    rchqd syslog check.

- **v1.6.0 metal test (RT-BE96U).** **Built + shipped + FLASHED 2026-07-17** (both variants on the
  `reaper-firmware/` ladder: MCP sha `622b6ec2…`, noMCP `4d47f00c…`, hashes in
  `SHA256SUMS-v1.6.0.txt`). Includes all of v1.5.9 (Traffic Analyzer resilience fix + shell
  master-scrollbar theme), so the earlier standalone v1.5.9 RT-BE96U metal test is retired.
  **Confirmed on hardware:** the Wireless diagnostics page enumerates all three radios on
  6 GHz and channel **Lock/Unlock is live** (used it, plus the on-router `chanim` capture, to run
  the 6 GHz investigation below); dashboard live; 6 GHz reaches **1 Gbps+** on a clean 320 MHz
  channel. **Still owed:** (a) **Non-English UI spot-check** —
  switch language and confirm the rail clock shows localized weekday + month names, the QoS /
  Traffic / Advisor help prose is translated, and an over-long label truncates with a hover
  tooltip showing the full word (the `.rtip` mechanism). (b) **Traffic Analyzer under load** after
  the collector perf edits (per-device / per-network / top-talker rows populate; live rates sane;
  no freeze). *The 24-language translation is machine-assisted; native review is recommended
  before any public release.*

- **6 GHz 320 MHz latency "sawtooth" — RESOLVED (environmental, not firmware).** A long-running
  RT-BE96U symptom (a clean ~18 s latency ramp to ~128 ms then snap-back, 0% loss, only at 320 MHz,
  only on 6 GHz) was chased to ground on metal using the Wireless page + an on-router
  `chanim_stats` capture. **Router / wl driver / acsd all exonerated — nothing to patch.** The
  cause is **localized external RF**: a clean 320 MHz channel exists (`6g69/320-1`: `nopkt` ~1 %,
  `txop` ~99 %) while the low/high blocks sit at ~50 % occupancy. Both the 10G-WAN-PHY theory
  (unplugging the WAN didn't change `nopkt`) and the self-induced-320-bonding theory (a clean 320
  channel exists) were **refuted on metal**. A PC-desk RFI source (antenna feedline draped over a
  USB 3.0 hub + a patched audio wire) was the leading physical candidate, but a **2026-07-18
  recheck found the low blocks dirty again after re-routing the feedline** — so the **emitter's
  identity is still open**; what holds is that it is external and frequency-selective. **Fix =
  channel selection** (park 6 GHz in a clean window, e.g. ch 69 / 320, held by the Lock feature).
  The Channel-Quality **Auto Scan** feature (see *Features to add*) is the planned productization
  of this fix. The 10G-WAN auto-guard idea is **dropped** (wrong trigger). [resolved — no firmware
  change]

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

## UI / UX polish

- **Restart/Boot Effciency** Investigate why the wifi and router reboots several times and 
  takes 10 min to stablize. Potential reordering of boot could make this quicker.
- **WD** REAPER Wireless Diagnostics need to be reworked for visual clarity and information.

*(Fixed items moved to `CHANGELOG.md`: the first-boot wizard language selector — v1.6.6; VPN
submenu colors, tablet/iPad layout, and the SDN page cut-off — all v1.6.4; Wireless Diagnostics
reports follow the router language via the v1.6.0/v1.6.1 page tokenization; and the v1.6.0 DICT
translation pass + truncate/hover-tooltip mechanism, the AI Advisor Refresh-button move, and the
Login/Logout favicon.)*

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

- **WAN-side management-exposure audit — DONE (compliant), see `LIVE-AUDIT-2026-07-19.md`.** The
  live audit confirmed the web UI, SSH (`sshd_enable=2` LAN-only), Telnet, SNMP, FTP, and TFTP are
  all off or LAN-only, WAN INPUT default-denies with WAN ping dropped, no port-forwards/DMZ, UPnP
  off on WAN, and IPv6 fully disabled with an ip6tables DROP policy. No WAN-reachable management
  surface. Posture documented per service in the report.

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

**Model version status (2026-07-18):**
- **v1.6.2** — RT-BE96U (shipped; Auto Scan **all bands** + report + passive monitor; 6 GHz
  Auto Scan metal-validated, 5/2.4 GHz metal test owed).
- **v1.6.0** — RT-BE88U (shipped), RT-BE86U (shipped). RT-BE96U now at v1.6.2.
- **v1.5.9** — GT-BE98, GT-BE98_PRO (v1.6.x fold pending; metal test owed — see *Known issues —
  ported models* below).

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
