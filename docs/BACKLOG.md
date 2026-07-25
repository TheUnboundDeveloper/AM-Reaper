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
- ~~**VPN Fusion client-list — broken/unusable action buttons + menu.**~~ **[FIXED v1.7.9]** Root
  cause: `reaper_content.css` recolored all device/vendor icon glyphs theme-red with an *unscoped*
  `!important` rule written for the Network-Map View List; on the VPN Fusion client rows the CSS-masked
  icons rendered as solid red blocks. Rule scoped to `.clientlist_viewlist`. See `CHANGELOG.md` v1.7.9.
  **Metal check owed** on an affected box (RT-BE86U reporter) once the sibling fan-out lands.

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

## Known issues (under investigation)

- ~~**Speed test intermittently fails — CROSS-BOX.**~~ **[FIXED v1.7.9 — root-caused 2026-07-25]**
  Stock-inherent, not a Reaper edit: the `ookla` binary fetches its `config.speedtest.net`
  configuration exactly **once with no retry**, and the Go button was gated only on WAN carrier —
  no NTP-clock or DNS-readiness check — so the first run after boot/idle aborted on cold DNS or a
  pre-NTP TLS clock error and the retry succeeded. Fix: `internet_speed.html` now performs **one
  silent auto-retry** per run (2 s backoff) on transient errors; a real WAN-down still errors
  immediately. Also absorbs the page-load server-list fetch racing a quick Go click. (Reaper's
  QIS removal made the window easier to hit by letting users reach the page earlier after boot.)
  **Residual, separate:** on one heavily-loaded RT-BE86U (5+ VPN tunnels, unbound, Diversion,
  993 MB RAM) the test also froze the box ~30 s and self-recovered — resource starvation:
  router-*originated* traffic is not flow-accelerated, so a multi-gig test runs on CPU, worst if
  it egresses a software-crypto VPN tunnel. Stock behavior; guidance is "expect a busy router
  during the test on heavy configs." [risk-accepted unless field data worsens]
- **Firmware-wide teardown audit (2026-07-25) — COMPLETE.** 4-agent walk + cross-check against the
  current tree. Results: **no dangling references** to removed services (all compile-guarded), **no
  broken shims**, `reaper_inject.c` filter sound; VPN Fusion glyph CSS + speed-test findings fixed
  in v1.7.9 (above). The **ASUS-app question resolved: the AAE remote tunnel
  (`mastiff`/`aaews`/`asusnatnl`) is severed on ALL five image models** — every sibling branch sets
  `NATNL_AICLOUD=n`/`NATNL_AIHOME=n` (RT-BE96U removed entirely; v1.7.8 image verified clean) — so
  "app still works" reports are **local-LAN access, benign**. Two hygiene leftovers: (1)
  `be96u-only`'s *unused* copies of sibling target.mak blocks still show stock `NATNL=y` (build
  nothing today, but a recreation trap — normalize to `=n` someday); (2) `RTCONFIG_ASUSCTRL=y` is
  still compiled in — no phone-home path traced; verify or drop on a future rung. [low]

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

- **SNMP hardening. [DONE v1.7.8]** Default state **verified off** in the live audit 2026-07-19
  (`snmpd_enable=0`, `snmpd_wan=0`, no snmpd listening) — the primary advisory vector is closed
  by default. The previously shelved SNMPv3-`authPriv` / reject-common-strings enhancement for
  users who *enable* SNMP is now **delivered in v1.7.8**: SNMPv1/v2c cleartext community strings
  are removed from the daemon and the UI, SNMP requires authenticated **SNMPv3** (default SHA +
  AES), and net-snmp was modernized **5.7.2 -> 5.9.4**. Full posture in `LIVE-AUDIT-2026-07-19.md`.

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

- **QoS download policer — DEFAULT OFF (decided 2026-07-24; code change pending next build).** The
  WAN-ingress RX policer (`qos_ipolicer`) shipped **default ON** with kill-switch semantics, so any
  box with a download bandwidth set engaged it. A policer has **no queue** — it drops (not delays)
  excess — so it clips loss-sensitive real-time UDP (metal 2026-07-20: Teams-call packet loss; the
  RT-BE96U owner mitigated by hand with `qos_ipolicer=0`). **Decision:** flip the `defaults.c` default
  to **`"0"` (opt-in)** so no fresh install hits the footgun; the download cap stays available for
  users who specifically want bulk-download bufferbloat control and accept the loss-for-latency trade
  (v5 metal measured ~90% held full rated speed with lower ping). One-line `defaults.c` flip on
  `be96u-only` (shared source); applies to **fresh nvram only** (existing boxes keep their value).
  Rides the next QoS/build rung. **Doc note DONE (English):** the download-cap toggle description
  (`RQOS_117`, `Reaper_QoS.asp`) now warns it is off by default and, being a policer, can add packet
  loss to real-time video/voice — commit `225399d2fc` on `be96u-only`. **Translated to all 24 other
  languages** (commit `b29d33f8d1`; `RQOS_117` still 122-key lockstep) — machine-assisted, native
  review owed. `qos_dscp_wmm` (the benign WMM-lift half) stays default ON.
  - **Residue sub-thread CLOSED:** the `(0,160,0)` `getportrxrate` readback is a sub-legal inactive
    descriptor (rate 0 < 100K CIR min, burst 160 < 1K CBS min per `rdpa_policer.h`) — cosmetic, not an
    active bucket — and it clears on reboot (RT-BE96U diag 2026-07-24 read a clean `(0,0,0)` with the
    policer off after 6h uptime). It was never the packet-loss cause; the active policer was. The
    optional teardown log-hygiene tweak (treat rate 0 as "already off") is deferred as non-blocking.

 - Users report that when using a USB Hub with the router that nothing is sidplayed under the USB 
   image in the Network Map page. Clicking the dropdown arrow shows the list of devices. Currently 
   plugging in a single drive shows the drive name that wont change. What we should do is that if 
   mutiple device names are detected the count of the devices be displayed under the icon. Example, 
   "3 Devices". 

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

## Packages

*(Done in v1.7.8, moved to `CHANGELOG.md`: the **Samba 3.0+ investigation** landed as
**Samba 4.15.13** — real SMB3 / SMB3.1.1 with GnuTLS AES-GCM/CCM encryption, replacing Samba
3.6.25 (SMB2 max), with a new "SMBv3 (encrypted)" option on the Samba page (`smbd_protocol=3`),
RT-BE96U only for now; and the **net-snmp update / SNMPv3** landed as net-snmp 5.7.2 -> 5.9.4 with
SNMPv3-only hardening. The EOL residual risk that had these shelved is resolved for those two
packages.)*

- **SMB3 / Samba 4 hardware test on RT-BE96U. [metal test owed — v1.7.8]** Verify on real
  hardware that a client negotiates **SMB3 / SMB3.1.1** to the router (not SMB1/SMB2), that the new
  **SMBv3 (encrypted)** option (`smbd_protocol=3`) actually forces GnuTLS AES-GCM/CCM encryption on
  the wire (confirm with a capture / `smbstatus` showing an encrypted session), that share
  read/write and browse still work, and that RAM/CPU headroom under a sustained transfer is
  acceptable on the BE96U. Build only so far.
- **Samba 4 / SMB3 sibling fan-out. [owed]** Samba 4.15.13 shipped **RT-BE96U only**; the siblings
  (**RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro**) remain on **Samba 3.6.x** (SMB2 max) today. Port
  the Samba-4 package + the SMBv3 UI option onto those branches once the RT-BE96U metal test passes
  (shared source; a clean rung when those branches are next bumped).
- **SMB3 follow-ups. [shelved]** Optional nice-to-haves on top of the Samba-4 base: **ACL support**
  (`vfs_acl_xattr` / extended-ACL config) and **per-model UI gating** of the "SMBv3 (encrypted)"
  option so it only surfaces on models that ship Samba 4 (hide it on siblings still on 3.6.x until
  the fan-out lands).

## Platform / expansion

**Model version status (updated 2026-07-25):**
- **v1.7.9 (building)** — RT-BE96U (primary, hardware-validated line). v1.7.8 (SMB3/Samba4 +
  SNMPv3-only + SFTP + dashboard fixes; **MCP built + on metal**, noMCP owed) plus the v1.7.9
  fixes: VPN Fusion buttons, speed-test auto-retry, 2.4 GHz MLO-excluded-band name. Earlier stack:
  v1.7.0 Gatekeeper → v1.7.7 VPN anti-flash (see `CHANGELOG.md`).
- **v1.7.7** — RT-BE86U, RT-BE88U, GT-BE98 (v1.7.7a hotfix), GT-BE98 Pro (v1.7.7 fleet, 20 images
  + SHA256SUMS). The **v1.7.8/v1.7.9 fan-out onto these branches is owed** (Samba4 port waits on
  the RT-BE96U SMB3 metal test; the v1.7.9 www fixes are clean shared-source cherry-picks).

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

- **GT-BE98: Hardware QoS can't attach to the WAN (`vlan4094`). [owed — investigate; found 2026-07-24]**
  Reaper Diagnostics v1.0.1 on GT-BE98 v1.7.7 (§10 QoS) shows every `tmctl` readback failing —
  `portshaper`, `portrxrate`, and all seven `qcfg` queues return `is_port_wan.126: failed to
  communicate with dev vlan4094` / `get_root_tm.687: Failed to get tm owner for vlan4094, ret[-5]`.
  The GT-BE98's WAN egresses on **`vlan4094`** (a VLAN over the multi-gig WAN port), and `tmctl --if`
  can't map that virtual netdev to an rdpa TM port. QoS was **disabled** on the reporting box
  (`qos_enable=0`) so it was harmless there, but it means that if a GT-BE98 owner enables **Hardware
  QoS**, the port shaper / download policer / classful queues will **silently fail to apply** on the
  WAN. The engine resolves `$WANIF` to the raw WAN device; on models where the WAN rides a VLAN,
  `tmctl` needs the **underlying physical port**, not the VLAN netdev. Fix direction: give the
  HW-QoS `$WANIF` resolver a VLAN-aware path (resolve `vlan4094` → its base port for the `tmctl --if`
  argument), or gate/adapt per model. Ties into the download-policer thread (the RT-BE96U 160-byte
  residue work) — on GT-BE98 the policer wouldn't even attach. Build/diag observation only; no
  GT-BE98 QoS metal test yet.

- **GT-BE98: Wireless Log page mis-maps the quad-band radios (missing 5 GHz-2 + most clients).**
  **[FIX in v1.7.7a — built 2026-07-24, metal test owed].** `Main_WStatus_Content.asp`'s `redraw()`
  special-cases only `GT-AXE16000` and `GT-BE98_PRO`; **`GT-BE98` (non-Pro) fell into the generic
  tri-band `else`**, which assumes `dataarray0 = 2.4 GHz` and can't render two 5 GHz radios plus
  6 GHz at once. On GT-BE98 the units are `wl0=5 GHz-1, wl1=5 GHz-2, wl2=6 GHz, wl3=2.4 GHz`, so the
  page mislabeled 5 GHz-1 as "2.4 GHz" (showed channel 48), dropped the real 2.4 GHz radio (`wl3`,
  which held 6 of 8 Wi-Fi clients), and omitted the 5 GHz-2 section. Confirmed by diag v1.0.1
  (`productid=GT-BE98`, §7 radio map) — **not** a model-identity bug and **not** a Reaper regression
  (the block is byte-identical to stock Merlin, which never added a GT-BE98 case). **Fix:** add
  `GT-BE98` to the existing `GT-AXE16000` branch (identical band plan). Upstream-worthy.

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
