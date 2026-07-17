# RT-BE96U "Reaper" — Changelog

High-level history of the Reaper build. One entry per version, big changes only —
the exhaustive security detail is in [`REAPER-FIXES.md`](REAPER-FIXES.md) and the
per-release summary in [`RELEASE-NOTES.md`](RELEASE-NOTES.md).

All versions are the `RT-BE96U 3006.102.8_Reaper_v<X>` firmware line, built for the
ASUS RT-BE96U only, on the Asuswrt-Merlin 3006.102.8 base.

> **Metal-validation note:** everything through v1.4.8 is validated on the physical
> RT-BE96U (including the USB third-factor flow). v1.4.8a–v1.4.9a are build-verified
> (both image variants); v1.5.0a's AI Advisor and its network-diagnostics tier are
> validated on the physical RT-BE96U. In the v1.5.x line, **v1.5.6** is the newest
> fully metal-validated build; the v1.5.7 checklist is owed, and **v1.5.8** was flashed
> to the router 2026-07-16 with its checklist owed. Sibling-model builds (v1.5.0e/v1.5.1)
> are build-validated only. See `RELEASE-NOTES.md` for the current release's status.

---

## v1.5.9 — Traffic Analyzer resilience + shell scrollbar
- **Traffic Analyzer can no longer freeze.** The live view could stick at its last paint while
  the browser kept polling (one stalled response wedged the poll loop's in-flight guard forever).
  The fetch path is rebuilt on a single always-fires completion point with a request timeout and
  a watchdog that aborts any hung request, so the loop always self-heals. When polls stop
  answering, the page now keeps its last data and flips the status pill to an amber
  **"No response"** marker instead of silently rendering zeros; the history windows
  (5 min / 24 h / 14 d / By month) also auto-refresh every 30 s instead of going stale.
- **Master page scrollbar themed everywhere.** The far-right top-window scrollbar was
  black-track/crimson-thumb on the dashboard but stock gray on every shell-framed page; the
  app shell (the top window for all framed pages) now carries the same red scrollbar rules.
- UI only, both images. Metal test owed.

## v1.5.8 — Wireless diagnostics page
- **New "Wireless" diagnostics page** (`Reaper_Wireless.asp`): a live radio-state snapshot for
  every band, a one-click **channel Lock/Unlock** that pins the currently-running channel through
  the stock apply flow (so automatic channel selection can never drift it), a decoded view of the
  channel **exclusion list** and regulatory/board branch actually in effect, and an **on-demand
  channel-quality capture** — a bounded 1 Hz channel-utilization sample written to CSV in RAM
  (never always-on, never syslog). This productizes the manual capture loop that located a
  real-world 320 MHz interferer on the 6 GHz band on 2026-07-16.
- **Factory-default fix:** two duplicate defaults for the 6 GHz PSC-channel setting (`psc6g`)
  disagreed, so a factory reset landed on the unintended value; aligned to the intended default.
- Flashed to the physical RT-BE96U 2026-07-16; the test checklist is owed.

## v1.5.7 — Audit fix rung
- Fixes from a 34-agent adversarial sweep of all Reaper-authored code (21 raw findings —
  12 upheld and fixed, 9 refuted and recorded so they are not re-found):
  - **Smart Connect:** the band bitmask is now indexed by slot, not by band count, so the
    toggle stays correct when a radio is disabled.
  - **System Log:** Broadcom wireless-driver errors are no longer filtered out of the log.
  - **Traffic Analyzer collector:** radio queries moved out of the hot sampling path, and
    rate reporting corrected.
  - **AI Advisor:** every tool command now carries a hard time bound, and session cleanup is
    armed before it can first be needed.
  - Smaller fixes: firewall mangle flush when leaving HW QoS, port-forward names with spaces,
    AiMesh config-sync client count, Advisor page CSS. Metal test owed.

## v1.5.6 — AI Advisor: wireless-stations read tool
- **New curated read tool `get_wireless_stations`** (AI Advisor image only): per-station
  signal/PHY/rate detail plus channel-utilization for every wireless interface, gathered by one
  fixed, no-caller-input pipeline — so the Advisor can reason about Wi-Fi health without shell
  access. Metal-validated on the RT-BE96U.

## v1.5.5 — First-boot security wizard + dashboard/UX fixes
- **Mandatory first-boot / factory-reset credentials wizard.** A fully Reaper-authored, themed
  setup page (`Reaper_FirstBoot.asp`) now forces the admin **username + password** on a
  factory-fresh box (default `admin/admin` is disabled once setup completes, and "admin" is
  rejected as a password), then forces the wireless page until a **WiFi PSK** is set, before any
  other UI is reachable. Replaces the stock forced password-change gate (which lives in a closed
  blob and only changed the password). Upgrade-safe: the gate derives from live state, so a
  configured or upgraded box never sees it. This is the concrete mitigation for deferred finding
  **H15 (default admin creds)** and the primary credential-hygiene item from advisory
  **AA26-194A** (see `BACKLOG.md`). *Factory-reset metal test still owed; known limitation: the
  WiFi step releases on "configured", so an explicitly-open network can skip the PSK.*
- **Internet status now updates itself during boot.** The dashboard Internet card **and** the
  shell-header WAN pill poll the WAN state on their own and flip to Connected without a manual
  refresh — fast (~4 s) while disconnected, slow (~30 s) once up.
- **Waiting overlay for Reaper pages.** A reusable themed "applying" modal (modeled on the reboot
  overlay) now covers apply/arm actions on the Reaper-native pages that lacked one.
- **AI Advisor IP pin persists.** The client-IP pin is prefilled from the router and survives
  visits, reboots, and a later Save Settings (it was previously wiped to empty).

## v1.5.4 — QoS v5.1: download-policer metal tuning
- **Burst/rate fixes for the new download-side policer** from on-hardware tuning
  (2026-07-15). Small correctness rung on top of v1.5.3; no new features.

## v1.5.3 — QoS v5 download side + Traffic Analyzer Live (100 ms) + device identity
- **QoS v5: the download side.** A WAN-ingress RX policer (driven by the download bandwidth
  setting) plus a downstream DSCP→WMM class lift, so download traffic is now policed and
  classified like upload — previously the classful engine shaped upload only. Metal
  validation owed.
- **Traffic Analyzer "Live" tightened to 100 ms.** The collector tick and the page's Live
  option move together (200 ms → 100 ms) as a matched pair, with an in-flight request guard
  so a slow response skips ticks instead of stacking against the single-threaded web server.
- **Device identity rows.** Top Talkers and Top Devices now show the device **name** with an
  "IP · MAC" subline (names from the same source as the dashboard's client list), instead of
  raw addresses.

## v1.5.2 — Boot efficiency, round 1
- First fixes from the boot-behavior recon: the web UI no longer restarts when a USB drive
  mounts during bring-up, and watchdog wait paths were unblocked — trimming avoidable UI
  drops in the several-minute boot-stabilization window. (The wider boot-efficiency
  investigation remains open in `BACKLOG.md`.)

## v1.5.1 — GT-BE98 blob re-base (sibling models)
- The GT-BE98 ports' closed-source blobs were **re-based from the second-hand community
  import onto the official ASUS GPL drop** (102_39274), and the GT-BE98 quad-band gap was
  closed (`HAS_6G` — the 6 GHz radio was never enabled in the v1.5.0e port, the prime suspect
  in the GT-BE98 field report tracked in `BACKLOG.md`). Sibling-model build rung;
  **build-validated only**, no functional change to the RT-BE96U image.

## v1.5.0e — Factory-reset recovery fix + first sibling-model builds
- **Fixed the factory-reset redirect loop.** On a factory-clean box the first-run gate pages and
  Reaper's serve-time bounce redirected each other forever, so the UI never loaded and the router
  appeared bricked (recoverable only via the ASUS rescue tool). Setup/QIS pages are now excluded
  from the bounce. *Reported by tester PorscheT — credit him in the public release notes.*
- **First builds for sibling BCM4916 models.** GT-BE98 Pro, GT-BE98, and RT-BE86U (plus RT-BE96U)
  each built in both variants — closing the "wider BE-series support" investigation.
  **Build-validated only, no metal test** on the sibling models; do not flash without a recovery
  path. (A GT-BE98 field report is tracked in `BACKLOG.md`.)
- **Reproducible branch builds.** The `be96u-only` branch now builds cleanly from a fresh
  checkout (it previously depended on uncommitted working-tree deletions).

## v1.5.0d — De-ASUS rebrand (UI only)
- **New wordmark banner.** The `REAPER1` wordmark banner replaces the previous logo everywhere it
  appeared: the dashboard and app-shell headers, the login/logout card, and the stock-page banner.
- **AiMesh backdrop.** The AiMesh node card now uses the `RLogo` artwork; the old ASUS logo asset is
  removed from the build entirely.
- **Live rail clock.** The "ASUS · Merlin · Reaper" wordmark at the top of the left rail is replaced
  by a themed, live, 24-hour **router-time clock** (date + seconds), on both the dashboard and the
  app shell. No functional/firmware change. Build-verified; pending metal validation.

## v1.5.0c — Compliance: license headers + font license (no functional change)
- **SPDX license headers** (`GPL-2.0-only` + copyright) added to every Reaper-authored source
  file (the Traffic Analyzer and AI Advisor daemons, the theme-injection filter, the Reaper
  pages, CSS, and Makefiles) — provenance hygiene, no behavior change.
- **Font license shipped in the image.** The SIL Open Font License 1.1 text is now installed as
  `www/fonts/OFL.txt` so the license for the bundled Inter/Rajdhani web fonts travels with the
  firmware, as OFL 1.1 requires. Part of the 2026-07-13 release-compliance pass
  (see `COMPLIANCE-AUDIT-2026-07-13.md`). Build-verified; pending metal validation.

## v1.5.0b — Traffic Analyzer "Live (200ms)" mode + diag-aware AI Advisor
- **New "Live (200ms)" refresh mode** on the Traffic Analyzer. The collector's base tick moves
  from 1 s to 200 ms (work-time-paced so heavy samples never stretch the interval), giving the
  live WAN view true 5 Hz updates; the 1 s / 10 s / 30 s options remain and 1 s stays the default.
- **AI Advisor `initialize` instructions are now diagnostics-aware.** When a session has network
  diagnostics enabled, the Advisor is told the probes are active and to run them itself, instead
  of the previous static "read-only" wording that made it defer network probes back to the user.
  Build-verified; pending metal validation.

## v1.5.0a — Network Diagnostics: AI network probes (+ security hardening)
- **AI Advisor network-diagnostics tier (AI Advisor image only).** When you explicitly allow it,
  the read-only Advisor can run bounded, read-only network probes — `ping`, `traceroute`,
  `DNS lookup`, `netstat` — so your own AI assistant can tell whether a problem sits at the
  **router, the client device, the ISP, or the wider internet**. It still cannot change a single
  setting.
  - **Off by default, per session.** An "Allow network diagnostics" checkbox on the arming
    card must be ticked *each time you arm*; the consent lives only in that session and never
    persists.
  - **Scoped + audited.** Every probe is fixed-argument (no shell), one-at-a-time, time-bounded,
    output-capped, and written to the system log. Targets are validated and resolved first, and
    loopback / link-local / ULA / private addresses that are **not** on this router's own LAN are
    refused — for IPv4 **and** IPv6 — so the Advisor cannot be turned into an internal-network scanner.
- **Security hardening.** The AI Advisor control endpoint now requires the router's request token
  on any state-changing action (CSRF protection); diagnostic input-validation, interface-name
  checks, and traffic-analyzer output escaping were tightened.
- **No bundled packet capture.** An earlier internal build carried a `tcpdump`-based "Packet
  Capture" page; it is **not** included — it pulled a large legacy dependency for a niche need.
  If you want packet capture, install `tcpdump` via Entware on a USB stick.
- **Metal-validated** on the RT-BE96U: the AI Advisor and its diagnostics tier verified on hardware.

## v1.4.9a — UI polish: navigation, in-rail language selector, AiMesh, System Info
- **Slimmer left navigation.** The side nav is back to just wide enough for the menu items and
  the "ASUS · Merlin · Reaper" wordmark on one line.
- **Language selector moved into the rail.** It now sits above the "General" heading as a compact
  "Language:" dropdown instead of in the topbar.
- **AiMesh card.** The router backdrop image now extends down behind the room selector so the
  dropdown sits on the image, up to the divider — closing the dark gap.
- **System Info "Features" row** now advertises Reaper's own packages (AI Advisor, Traffic
  Analyzer, HW QoS classful) alongside the stock
  capability list, so it reflects the true per-build feature set. UI/presentation only; both images.

## v1.4.9 — USB second factor made binding + AI Advisor lock-state UI fix
- **The USB key is now binding.** "Remove USB key" (unenroll) now requires the enrolled
  stick to be physically inserted — someone with only the admin login and the arming code can
  no longer strip the third factor, including via the deprovision-then-unenroll path. If the
  key is lost, a **factory reset / nvram clear** is the only way to clear it. This makes the
  USB factor tamper-resistant: removal is now at least as strong as arming.
- **The AI Advisor page reflects the lock immediately.** While a session is armed the page now
  re-polls the router every few seconds, so pulling the USB key (or a session timeout/disarm)
  flips the card to "locked" within seconds instead of counting down a session the router has
  already torn down. (The router-side teardown — firewall rule removed, session file deleted —
  already fired on key removal; this closes the front-end feedback gap.)
- Security/UI only, in the **AI Advisor image** (the standard/noMCP image has no Advisor, so it
  is unaffected).

## v1.4.8a — Bandwidth Limiter on the QoS page + language-selector fixes
- **Bandwidth Limiter moved onto the Reaper QoS page.** Choosing the Bandwidth Limiter mode
  now shows a per-device cap editor (pick a device or enter a MAC, set download/upload in
  Mb/s, enable/disable and remove rows — up to 32 devices) directly on the page instead of
  linking out to the stock editor. The old `QoS_EZQoS.asp` page is removed from the menu and
  any direct or framed hit redirects to the Reaper QoS page.
- **Language selector fixes (from v1.4.8 on-hardware testing):**
  - You can now switch **back to English**, and the dropdown shows the **active** language as
    selected. (ASUS's language list deliberately omits the current language, so it wasn't
    selectable; the current language is now included.)
  - The selector is more visible in the topbar — a globe icon, a crimson-tinted border, and
    brighter text.
- **"Traffic Analyzer" no longer scrolls the side nav sideways.** Five languages shipped that
  menu label as "English + native", which overflowed the rail; it now shows the native
  translation only, and nav labels ellipsize so no language can force a horizontal scrollbar.
- **Removed the red editor link** from the Bandwidth Limiter option (now that the editor lives
  on the page). Localization/UI only. Both images.

## v1.4.8 — Language packs + UI fixes
- **Language packs (i18n).** The five Reaper-native pages (dashboard, Traffic Manager,
  Traffic Analyzer, AI Advisor, and the app shell) were 100% hardcoded English and ignored
  the router's language setting. They are now fully tokenized (`<#...#>` dict entries) like
  every stock ASUS page, so they follow `preferred_lang`. Where a string already had an
  ASUS translation (menus, buttons, modes, common labels — ~70% of the chrome) the existing
  key is reused, so those localize **immediately in all 25 languages**. Reaper-specific
  strings (the QoS/Traffic/Advisor help prose) get new keys carrying English in every
  language for now — a translation drop-in point with no code change needed. 350 new dict
  keys added across all 25 language files, kept in lockstep.
- **Language selector in the Reaper topbar.** Reaper's chrome hid the stock language menu
  and offered no replacement, so the language could not be changed from the UI at all. A
  compact language dropdown now sits in the shell and dashboard topbars (populated with the
  router's compiled languages, localized names), applying the choice the same way the stock
  UI does.
- **Download Master advert removed** from the USB Application page — the advertised
  "PC-free download manager" install tile no longer appears.
- **Network Map USB icon** sizing corrected — the v1.4.7 change reframed the glyph because
  the icon is a sprite sheet; the slice is now scaled to its box so a plugged drive shows
  the clean centered glyph.
- **AiMesh backdrop** stretched to fill the card band so there is no dark gap below the ASUS
  logo and the room selector sits correctly.
- UI/localization only; no change to any underlying feature. Both images.

## v1.4.7 — UI polish + idle auto-logout
- **Idle auto-logout (15 min).** An unattended admin session now logs itself out after
  15 minutes of no activity (mouse/keyboard/touch), in the shell and inside the framed
  page alike. Closes the "walked away from the router page" exposure.
- **Traffic Analyzer** reading line now names the **selected timeframe** (Live / 24 hours /
  14 days / 1 year / By month) instead of always saying "Live".
- **Every page lands at the top** — switching pages in the app shell no longer leaves you
  scrolled down with the tab strip hidden.
- **Network Map USB tile:** the plugged-USB icon is centered in its ring, the disk-quota
  bar is removed, and a long disk name no longer clips.
- **AiMesh:** the backdrop behind the router/node name is now the ASUS logo instead of the
  stock room photo.
- Device/client icons already carry the red-on-black theme across the client-list pages
  (confirmed on hardware). UI/navigation only; no underlying feature change. Both images.

## v1.4.6 — Navigation cleanup: hide superseded and duplicate pages
- **Superseded stock pages are now hidden and redirected.** The stock Traffic Monitor
  and Statistic pages (replaced by the Reaper Traffic Analyzer) and the legacy QoS rule
  editors (replaced by the Reaper QoS page) are removed from the menu; visiting one by
  direct URL now bounces to its Reaper-native replacement instead of showing the dead
  stock page.
- **"Open NAT" removed from navigation.** It is just port forwarding, already covered by
  the Port Forwarding page — removed from the menu and the dashboard rail. The
  port-forwarding feature itself is unchanged and still reachable.
- **QoS page tidy-up.** Removed the "Related Pages" block at the bottom of the QoS panel;
  the one control it still pointed to (the per-device Bandwidth Limiter editor) now
  appears as a link inside the Bandwidth Limiter mode where it belongs.
- Navigation/UI only; no change to any underlying feature. Applies to both images.

## v1.4.5 — Exploit-mitigation build hardening (Reaper daemons)
- Compiles the two Reaper background daemons — the Traffic Analyzer collector
  (`rtrafd`, in both images) and the AI Advisor server (`rmcpd`, AI Advisor image
  only) — with modern exploit mitigations the stock BCM build omits: stack canaries
  (`-fstack-protector-strong`), buffer-overflow checks (`-D_FORTIFY_SOURCE=2`),
  format-string diagnostics (`-Wformat -Wformat-security`), position-independent
  executables (**PIE**), and **full RELRO** (`-Wl,-z,relro,-z,now`). The stock base
  ships neither stack canaries nor full RELRO, so this is a genuine hardening uplift
  for Reaper's own long-running processes.
- Build-only change (two Makefiles); no source or behaviour change. Verified on the
  built binaries: both are now position-independent with read-only relocations and
  stack-protection. Kept as its own release so the mitigation can be validated on
  hardware in isolation.
- Both images (Standard + AI Advisor) receive the `rtrafd` hardening; the AI Advisor
  image additionally hardens `rmcpd`.

## v1.4.4 — Security-review remediation, round 2 (defense-in-depth)
- Clears the remaining LOW / defense-in-depth items from the v1.4.2 code review
  (the HIGH/MEDIUM findings were fixed in v1.4.3). None was a live vulnerability;
  these tighten untrusted-input handling, cleanup, and CSRF posture.
- **Both images (Standard + AI Advisor):**
  - **Traffic Analyzer:** the persistent history database is now written safely on an
    untrusted USB mount — the file is created without following symlinks, is no longer
    world-readable, and the store directory is rejected if it isn't a real directory
    (blocking a planted symlink from redirecting history writes).
  - **Dashboard:** the live CPU/temperature/port tiles no longer evaluate the stock
    status responses as code — they parse them strictly as data, so an unexpected
    response can never execute.
- **AI Advisor image only:**
  - Clearing the arming code or removing the USB second factor now requires the current
    arming code, closing a cross-site-request path that a stale admin session could
    otherwise have ridden to weaken the advisor's setup. (Arming already required the
    code; this extends that to the two remaining state-changing actions.)
  - If the advisor ever exits uncleanly, its LAN firewall rule and session file are now
    swept away on the next boot instead of lingering.
- The Standard (no-AI-Advisor) image receives the Traffic Analyzer and Dashboard fixes
  and a matching version bump; the AI Advisor fixes are absent because that code isn't
  in it.

## v1.4.3 — Security-review remediation
- Fixes from a full multi-agent code review of the newest subsystems (AI Advisor,
  Traffic Analyzer, Hardware QoS, and the web UI). No router-compromise or
  secret-leak path was found; these harden availability and untrusted-input handling.
- **Both images (Standard + AI Advisor):**
  - **Traffic Analyzer:** a crafted history database (on a USB/JFFS store) could cause
    an out-of-bounds write — the on-disk header is now validated and its strings
    treated as untrusted. Per-client attribution no longer rescans the ARP table for
    every connection each second (a LAN device could otherwise spike router CPU); the
    optional latency-probe target is validated more strictly.
  - **Hardware QoS:** both ends of a QoS IP-range rule are now validated, closing a
    path where a malformed rule address could inject an extra firewall rule.
- **AI Advisor image only:**
  - A slow or stalled connection can no longer wedge the advisor and delay its
    self-lockdown — it now enforces a connection timeout, so session-expiry and
    USB-key-removal always take effect promptly.
  - Repeated bad-token attempts can no longer be used by an unauthenticated LAN device
    to shut down your active advisor session.
  - Constant-time token comparison and broader log-redaction as extra hardening.
- The Standard (no-AI-Advisor) image receives the Traffic Analyzer and QoS fixes and a
  matching version bump; the AI Advisor fixes are absent because that code isn't in it.

## v1.4.2 — AI Advisor: TLS via the router's own certificate
- The AI Advisor now serves **HTTPS using the router's own web (httpd) certificate**
  when one is loaded (the same `/etc/cert.pem` the router's web UI uses — **not** a
  separate cert), and falls back to plain HTTP when the router has no certificate.
  The arming page hands you the matching `https://` or `http://` connection URL
  automatically. (If the router's certificate is self-signed, your AI client may need
  to trust it.)
- **Friendly network names:** the advisor's wireless view now reports your real SSIDs
  (from the SDN profiles) instead of the internal onboarding IDs — still security
  *mode* only, never the Wi-Fi password.
- The **Standard (no-AI-Advisor) image was rebuilt to keep the version numbers in
  step** — it contains no AI Advisor code and is otherwise unchanged from v1.4.1.

## v1.4.1 — AI Advisor: optional USB second factor + clean two-build split
- **Mode B (optional USB key)** added to the AI Advisor: an opt-in physical second
  factor *on top of* the arming code. The router writes a generated key to your USB
  stick and stores only its fingerprint; when enrolled, arming also requires the
  stick, and removing it locks the advisor within ~1 second.
- **Two-build split finalized.** A single build flag (`RTCONFIG_REAPER_MCP`) produces
  either a build **with** the AI Advisor or one that **never compiled it in at all**
  (no daemon, no page, no menu, no settings — verified zero-trace), for users who
  want the MCP feature entirely absent.

## v1.4.0 — AI Advisor (optional, read-only LAN MCP server)
- New **optional** subsystem: a read-only [Model Context Protocol](https://modelcontextprotocol.io)
  server (`rmcpd`) that lets your **own** AI client (with your **own** API key) read
  the router's configuration and traffic to **audit and explain** it. It cannot
  change any setting - **yet**.
- Fenced hard to fit the project's threat model: **off by default**, never started at
  boot, **LAN-only**, read-only, secrets redacted, and gated behind a hashed **arming
  code** (a second factor beyond the admin password). Self-terminates on a session
  timeout. No API key is ever stored on the router; nothing is sent to any cloud by
  the router itself.

## v1.3.0 – v1.3.3 — Traffic Analyzer
- New native **Traffic Analyzer** subsystem (`rtrafd` collector + a Reaper-themed
  page): per-device, per-network, and per-QoS-class bandwidth with sub-daily history,
  live top-talkers, an optional monthly-quota warning, and an opt-in WAN latency
  probe. History storage is a required user choice (RAM / JFFS / USB).
- Accuracy reworked to read the Broadcom flow-accelerator's own flow table so
  per-device numbers are correct **with hardware acceleration on** (v1.3.1); endpoint
  and live-view fixes (v1.3.2); and a 1-second dual-cadence live view with a rolling
  chart and a refresh-rate selector (v1.3.3).

## v1.2.8 – v1.2.9 — Hardware QoS v3 and v4
- **QoS v3** (v1.2.8): aggregate rate cap, per-class guaranteed minimums, DSCP trust,
  and live per-class counters, on a native Traffic Manager page.
- **QoS v4** (v1.2.9): per-class weighted round-robin (WRR) weights and an
  experimental L4S (low-latency) flag.

## v1.2.7 — Remove the first-boot cloud-consent surface
- Removed the first-boot **QIS setup wizard's EULA / privacy-consent** screens and the
  Advanced privacy page (kept the AiMesh add-node wizard), and hardened an SNMP token
  path. Continues the de-cloud direction below.

## v1.2.1 – v1.2.6 — UI polish, stability, and code-scan hardening
- Post-login now lands directly on the Reaper dashboard (v1.2.1); a series of GUI
  theming sweeps and metal-tested fixes across VPN, USB, Network Analysis, and the QoS
  classful rule editor (v1.2.2 – v1.2.4); and a Reaper-authored-code security scan +
  performance pass (v1.2.5).

## v1.2 — De-cloud: attack-surface removal (consolidates the v1.1 betas)
- Removed AI-branded, cloud-coupled, and superfluous features to shrink the attack
  surface, consistent with the project's "local-only, no cloud, no fake-AI" direction:
  **Alexa / Google Assistant**, the **Trend Micro DPI engine** (AiProtection / DPI-based
  Adaptive QoS / web history), **AiCloud / WebDAV**, the **AiDisk** cloud-share wizard,
  and the **AAE / AiHome cloud tunnel** — each dropped along with its hooks, with the
  closed blobs left unmodified. Restored the local Speedtest.
- (These shipped incrementally as the `v1.1-beta1…beta5` images and were consolidated
  and released as **v1.2**, dropping the beta label.)

## v1.0 — Initial hardened release
- **Security hardening** of the open-source userspace: four audit rounds plus latent
  buffer hardening and an avahi mDNS CVE backport — the command-injection and
  buffer-overflow classes cleared across the ASUS/Merlin-authored userspace
  (per-finding detail in `REAPER-FIXES.md`).
- **Hardware QoS** — two engines ASUS never shipped: `qos_type=10` (hardware
  rate-shaping + PI2 AQM in the Broadcom Runner **with the flow accelerator left on**)
  and `qos_type=11` **Classful** (per-class priority queues), both validated on metal.
- **Reaper UI** — full matte-black + crimson rebrand and redesign: a live dashboard and
  an app-shell that loads stock settings pages unmodified, applied at serve time from a
  single httpd filter with a runtime kill-switch (`nvram set reaper_inject=0`).
- **Scheduled firmware-availability check** — fixed the dead stock setting and set it
  **default off** (no outbound update traffic unless you opt in; notification only,
  never auto-upgrade).
- Single-model tree: RT-BE96U only; all sibling BE models stripped.
