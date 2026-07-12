# RT-BE96U "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done/verified), **[blocked]** (external cause),
**[shelved]** (deliberately deferred), **[cosmetic]** (polish, non-blocking).

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md); strategy/roadmap is in
> [`ENTERPRISE-ROADMAP.md`](ENTERPRISE-ROADMAP.md).

---

## Testing / validation owed

- **Factory reset + first-boot manual setup.** Verify the full first-boot path after
  the QIS removal: reset → login → forced password change → dashboard, with **no** QIS
  redirect and **no** EULA modal. The **AiMesh add-node wizard and related setup menus
  are still in use** and must still work.

  **EXPERIMENTAL / OPTIONAL**

- **AI Advisor on hardware — remaining sub-tests.** Arming, LAN-only bind, token auth
  (good→200 / wrong+missing→401), and secret redaction are **confirmed on metal** (v1.4.1,
  re-confirmed v1.4.5 / v1.4.8). **Mode-B USB 3FA confirmed (2026-07-12):** enroll →
  arm-requires-stick → **pull-stick-locks** — verified live (the endpoint went from HTTP 200
  to *connection refused* within ~1s of pulling the key; the daemon's `cleanup()` removed the
  firewall ACCEPT rule and deleted the session file). The same `cleanup()` path also covers
  session-timeout teardown. **Still owed (physical / edge):** stick-without-the-enrolled-key
  rejected (a blank/other stick — note a **copied `reaper.key` on another stick still
  passes**; the USB check is content-hash based, not device-bound — see the hardware-token
  item under Features to add), Disable teardown, reboot-comes-up-dark, WAN-side refused.
  **v1.4.9 owed:** metal-test the new USB-binding (unenroll refused unless the enrolled stick
  is inserted; lost key → factory-reset only) and the Advisor page now flipping to "locked"
  within seconds of a key pull.
  **v1.5.0a done:** the bundled **Packet Capture** tool was **removed** in v1.5.0a (no metal-test
  owed). In an armed `_MCP` session the **network-diagnostics tier** is **metal-validated** (v1.5.0a,
  on the RT-BE96U): consent-gated `net_*` tools, ping/traceroute/DNS/netstat return bounded output,
  single-flight enforced, a private/off-LAN target is rejected, IPv6 loopback (`::1`) and `0.0.0.0`
  are rejected, an option-shaped DNS name (leading `-`) is rejected, and each run writes a syslog
  audit line. busybox probe applets resolve on-device.
  **v1.5.x shelved:** a bounded bufferbloat (latency-under-load) probe for the diagnostics tier.

- ~~**v1.4.5 hardened daemons run on hardware.**~~ **Done (metal, v1.4.5).** Confirmed via
  the live MCP session: `rmcpd` (PIE) armed, bound LAN-only `:5199`, served over TLS
  (router cert), and returned redacted reads; `rtrafd` (PIE) returned live per-device/
  per-class/probe data. Both position-independent executables load and run correctly — the
  PIE watch-item is cleared.

## UI / UX polish

- ~~**Remove the "Related Pages" block** at the bottom of the QoS panel.~~ **Done
  (v1.4.6).** Removed the `linkspanel` block from `Reaper_QoS.asp`; preserved the one
  kept link (the Bandwidth Limiter editor, `QoS_EZQoS.asp`) as a contextual link inside
  the Bandwidth Limiter mode card so that mode isn't stranded.
- ~~**Suppress old/replaced pages.** Stock pages that Reaper has superseded (e.g. the
  stock Traffic Monitor / Statistic pages and legacy QoS pages) are still reachable by
  URL — hide them.~~ **Done (v1.4.6).** Removed the 5 stock Traffic Monitor pages,
  `TrafficAnalyzer_Statistic.asp`, and the 2 legacy QoS editors
  (`Advanced_QOSUserPrio/UserRules_Content.asp`) from the menu, and added a suppression
  map to the injected bounce script (`reaper_inject.c`) that redirects any direct/framed
  hit on those 8 pages to their Reaper-native replacement (→ Reaper_Traffic / Reaper_QoS).
- ~~**Hide "Open NAT."** It's just port forwarding, already covered elsewhere.~~ **Done
  (v1.4.6).** Removed from the static menu, the `retArray` hide made unconditional, and
  the dashboard-rail tile removed. The port-forwarding feature itself stays reachable.
- ~~**Traffic Analyzer title line.** Update the summary/reading line next to the title
  to reflect the selected timeframe.~~ **Done (v1.4.7).** The reading pill was hardcoded
  `'Live - <store>'`; now a `setPill()` helper reflects the selected window label
  (Live / 24 hours / 14 days / 1 year / By month) plus the store, updated on window
  switch and on each live poll (`Reaper_Traffic.asp`).
- ~~**Scroll-to-top on page load.** Bounce every page to the top on load — inside the
  app-shell iframe a page can open scrolled down, hiding the tab strip and confusing
  users.~~ **Done (v1.4.7).** `reaper_shell.asp` iframe `load` handler now calls
  `window.scrollTo(0,0)` after the fit pass, so every framed page lands at the top with
  the tab strip visible.
- ~~**Network Map USB icon alignment.**~~ **Done (v1.4.7).** Glyph-only override in
  `reaper_content.css`:
  `div[id^="iconUSBdisk"]{transform:translateY(4px)!important;background-position:0px -10px!important}`
  (metal-tuned on the SanDisk Ultra Fit; `ring_USBdisk` sprite untouched). `!important`
  is required because index.asp's JS re-sets `background-position` inline each load.
- ~~**Network Map USB tile: remove the disk-quota bar + name-text clipping.**~~ **Done
  (v1.4.7).** `#diskquota{display:none!important}` (CSS hide; stock `index.asp` stays
  pristine) plus `[id^="deviceText_"]{font-size:12px!important}` so a long disk name fits.
- **VPN submenu colors.** A few off-theme colors still need correcting. 
- ~~**Device-icon red theme is incomplete.** ... extend to DHCP manual assignment,
  Parental Controls, Access Control / MAC filter, Open NAT, Time Scheduling.~~ **Done** —
  the `.clientIcon`/`.vendorIcon` theming in `reaper_content.css` covers the shared client
  icon across those pages (confirmed complete on metal, v1.4.5).
- ~~**AiMesh page background.** Change the image behind the router name to the ASUS
  logo.~~ **Done (v1.4.7).** Shipped `www/images/ASUSLogo.png` and overrode the
  `.translucent_bg` location backdrop (default Home.jpg) to the logo in `reaper_content.css`
  section 11 (`!important` beats every per-location variant; `contain` keeps it whole).
- ~~**Download Manager** the `download master` software being advertised in the ASUS router
  needs to be removed. It can be found on the USB Application page.~~ **Done (v1.4.8).** The
  `downloadmaster` tile is spliced out of `apps_array` unconditionally in `APP_Installation.asp`,
  so the advertised install tile never renders.
- ~~**Bandwidth Limiter** move the options and configuration of the bandwidth limiter to the
  Reaper QoS page and hide, supress, or remove the old QoS_EZQoS.asp page.~~ **Done (v1.4.8a).**
  A per-device cap editor (MAC/device + download/upload Mb/s, add/remove/enable, 32-device cap,
  writes `qos_bw_rulelist`) is folded into the Reaper QoS page's Bandwidth Limiter mode.
  `QoS_EZQoS.asp` is hidden from the menu (`menuTree.js`) and redirected to `Reaper_QoS.asp`
  for any direct/framed hit (`reaper_inject.c` SUP map). The old crimson "editor" link was
  removed from that mode card.
- **Restart/Boot Effciency** Investigate why the wifi and router reboots several times and 
  takes 10 min to stablize. Potential reordering of boot could make this quicker.

## Known issues (cause identified)

- **Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul
  BSS is still created even when every feature that would use it is disabled, spamming
  the log with RADIUS codes for an unused radio. Traced to a **closed-source Broadcom
  blob**; a boot-time script to suppress it based on device settings did not work and
  was reverted. [blocked — blob; risk-accepted]

## Features to add

- **Remote syslog push/fetch.** The router can already send its log to a remote
  collector (send-only). Add the ability to **push to / be fetched by** analytics
  systems — most SIEM/analytics pipelines are push-based.
- ~~**Idle session timeout.** Auto log-out and close idle admin sessions.~~ **Done
  (v1.4.7, 15 min).** Client-side idle-logout in the two top-level pages
  (`reaper_shell.asp` + `Main_ReaperDash.asp`) — resets on user activity in the shell
  chrome and inside the framed page (re-attached per iframe load), redirects to
  `/Logout.asp` after 15 min idle. (Server-side `auth_check` lives in the closed
  `web_hook.o`; a per-request timestamp would also be defeated by the UI's background
  polling — so client-side idle detection is the correct lever here.)
- **NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST
  baseline.
- **AI Advisor — hardware-token USB factor (FIDO2 / U2F / smartcard, e.g. a YubiKey).**
  **[optional — NOT committed; reminder of optionality]** The current USB factor is a
  *carried secret file* (`reaper.key`, verified by SHA-256), so it is copyable — anyone who
  can read the enrolled stick can clone it and the copy works (including for the v1.4.9
  binding, which checks possession of the key *file*). A hardware token doing
  challenge-response, where the private key never leaves the device, would make the third
  factor **clone-proof**: `rmcpd` would verify a signature instead of a file hash. Larger
  change (different hardware assumption + a crypto protocol in `rmcpd`); binding to a USB
  serial/VID/PID is only marginal (device-reported, spoofable). Recorded so the option is not
  lost — decide later.
- ~~**Language packs.** Rectify and apply, matching ASUS's language capability.~~ **Done
  (v1.4.8).** All 5 Reaper pages tokenized (`<#...#>`) so they follow `preferred_lang`;
  ~70% of the chrome reuses existing ASUS keys (localized now in all 25 languages), and new
  Reaper strings carry English fallback (350 keys added to all 25 dicts in lockstep). A
  language selector was added to the shell + dashboard topbars (the stock one is hidden by
  Reaper's chrome). Owner decision was reuse + English fallback; a real 24-language
  translation of the help prose is a future drop-in (same keys, per-language values).
  Detail in the `language-packs` memory + `docs/i18n-reuse-map.txt`.
- ~~**Remove the Download Master advert** from the USB Application page.~~ **Done (source).**
  `APP_Installation.asp` now splices the `downloadmaster` entry out of `apps_array`
  unconditionally (was gated on `nodm_support`), so the advertised tile never renders.
  Builds into the next image.

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

## Security hardening — LOW items (from the v1.4.2 code review) — ALL CLEARED

*The HIGH and MEDIUM findings from the review were fixed in v1.4.3; the LOW /
defense-in-depth items were cleared in v1.4.4, and the standalone exploit-mitigation
build-flags item in v1.4.5. None was a live vulnerability. This section is retained
as a record; nothing here is outstanding.*

**Cleared in v1.4.5:**

- ~~**Exploit-mitigation build flags.**~~ **Done (v1.4.5).** Both Reaper daemons now
  compile with `-D_FORTIFY_SOURCE=2 -fstack-protector-strong -Wformat -Wformat-security
  -fPIE` and link `-pie -Wl,-z,relro,-z,now` (rtrafd → both images; rmcpd → AI Advisor
  image). Done as its own release (two Makefiles, no source change) and verified on the
  built binaries: both are now PIE (`ET_DYN`) with full RELRO (`BIND_NOW`) and stack
  canaries — the stock base had neither. On-hardware run check of both daemons is the
  one remaining validation (PIE is the only behavioural change), folded into the v1.4.5
  metal test.

**Cleared in v1.4.4:**

- ~~**AI Advisor CSRF — belt-and-suspenders.**~~ **Done (v1.4.4).** Confirmed the Referer
  guard does *not* gate `reaper_mcp.cgi`: the `mime_referers[]` whitelist lives in the
  prebuilt/closed `web_hook.o` and predates the Reaper CGIs, so `do_referer` stays `0`
  and `referer_check()` never runs for it (`do_auth` only proves the login cookie). Since
  the closed table can't be edited, fixed at the application layer instead —
  `deprovision` and `usb_unenroll` now require proof of the current arming code
  (constant-time, with the same lockout accounting as `provision`-rotate); the arming
  page prompts for it. `arm` was already code-gated; `disarm`/`deprovision` are fail-safe
  directions.
- ~~**rtrafd USB history store hardening.**~~ **Done (v1.4.4).** `db_save` now creates the
  temp with `O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW, 0600` (published atomically via
  `rename`); `db_load` opens `O_RDONLY|O_NOFOLLOW`; both the JFFS and USB store dirs are
  `lstat`-checked (`dir_ok`) so a symlink planted on an attacker's mount can't redirect
  writes, and history is never world-readable.
- ~~**Stale-rule sweep on boot.**~~ **Done (v1.4.4).** `reaper_mcp_boot_sweep()` runs once
  in `start_services`: if `rmcpd` isn't running but a stale `/tmp/reaper_mcp/session`
  exists (unclean SIGKILL/SEGV exit), it reconstructs the exact LAN `INPUT ... ACCEPT`
  rule from `lan_ifname` + `rmcp_port` + the session's recorded (strictly validated)
  client and removes it, then deletes the session file. Never starts the daemon.
- ~~**Dashboard `eval()`.**~~ **Done (v1.4.4).** `Main_ReaperDash.asp` no longer `eval()`s
  the three stock CPU/temp/ports responses — a `pickJSON()` extractor + `JSON.parse`
  (plus a plain regex for the temperature string) replaces them. Confirmed all three
  endpoints emit single-line double-quoted JSON, so behaviour is unchanged.

## Platform / expansion

- **Wider BE-series support.** Investigate firmware support for the other ASUS BE-series
  routers built on the Broadcom BCM4916.
