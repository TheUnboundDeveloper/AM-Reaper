# RT-BE Series "Reaper" — Changelog

High-level history of the Reaper build. One entry per version, big changes only —
the exhaustive security detail is in [`REAPER-FIXES.md`](REAPER-FIXES.md) and the
per-release summary in [`RELEASE-NOTES.md`](RELEASE-NOTES.md).

All versions are the `3006.102.8_Reaper_v<X>` firmware line, built on the
Asuswrt-Merlin 3006.102.8 base for the ASUS RT-BE Series (BCM4916 platform).
The RT-BE96U is the primary, hardware-validated model; the **RT-BE86U**,
**RT-BE88U**, **GT-BE98**, and **GT-BE98 Pro** are built from per-model branches
of the same tree. See `RELEASE-NOTES.md` for each release's validation status.

Throughout this document, you will see references to AI and MCP functionality. Reaper is 
distributed in two distinct build variants. The MCP-enabled build includes a custom Model 
Context Protocol implementation that allows authorized AI agents on the local LAN to connect 
to the router, perform basic diagnostics, and provide the user with recommendations for 
improving performance or remediating identified issues. Any firmware image with noMCP in 
its name is compiled without MCP or AI functionality. This is not a disabled feature or 
a runtime setting; the relevant components are excluded from the build entirely.

AiMesh has been retained because no suitable open-source replacement is currently known. 
Replacing AiMesh would also require a compatible replacement implementation on every mesh 
node, not only on the primary router.

---

## v1.7.7 — VPN pages: no theme flash, plus a Network-Map lighting-control fix
- **No more stock-color flash on the VPN pages.** Opening **VPN &rsaquo; VPN Client** (PPTP/L2TP)
  or **VPN Server** could show the original blue ASUS styling for a split second before the Reaper
  theme took over. The nested settings panel now stays hidden over a dark background until it is
  fully themed, then fades in — so only the Reaper look is ever visible.
- **AURA/RGB lighting: no stray scrollbar.** On models with AURA/RGB lighting, the effect-scheme
  selector on the **Network Map** router panel showed an unnecessary horizontal scrollbar. That list
  already pages with its own left/right arrows, so the scrollbar has been removed. *(Affects the
  RGB-capable models; the RT-BE96U has no AURA hardware.)*

## v1.7.6 — VPN theming: no stuck colors, no endless loading, single scrollbar
- **VPN Client/Server pages theme correctly and settle down.** On **VPN &rsaquo; VPN Client**
  (PPTP/L2TP) and **VPN Server**, the server-list cards could stay stuck in the original ASUS
  blue/teal, and the page never went idle — a constant churn of background activity that some users
  saw as the page "always loading." Two routines were fighting over the panel's size and fell into a
  loop; the build now lets the page size itself and simply keeps the Reaper theme on top, so the
  pages render in the Reaper colors and go quiet once loaded.
- **One scrollbar on the Internet Speed test.** Under **Traffic Manager &rsaquo; Internet Speed**
  (Adaptive QoS), the page could show a second, inner scrollbar. The speed-test panel now grows to
  fit its content, so the page uses a single page scrollbar.

## v1.7.5 — Security: close the last `openssl passwd` command-injection path (ASUS PSIRT case 1006563)
- **Removed a root command-injection path in password verification.** An internal helper that
  falls back to the `openssl passwd` command-line tool (used only when the C library's own
  password hasher is unavailable) built that command as a shell string with the *supplied
  password* embedded in it — so a password containing shell metacharacters could have run
  arbitrary commands as root. This was a second, independent copy of a flaw already fixed
  elsewhere in v1.0 (finding **C6**); this copy lived in the `libpasswd` helper reached from the
  HTTP and WebDAV/SMB basic-authentication paths, with the attacker-supplied password as the
  injected value. The helper now runs `openssl` directly with the password as a literal
  argument — never through a shell — so no metacharacter can be interpreted. No change for
  normal logins.
- Found and closed while preparing the coordinated-disclosure proof-of-concept material
  requested by **ASUS PSIRT (case 1006563)**; the C6 fix was point-fixed in v1.0 and is now
  class-fixed across every `openssl passwd` sink. See [`REAPER-FIXES.md`](REAPER-FIXES.md).

## v1.7.4 — DHCP client picker + Wireless page theme-flash (on-metal fixes)
- **Static-DHCP client picker back on the button.** On **LAN &rsaquo; DHCP Server**, the
  "select a client" dropdown for the Manually Assigned IP table is again anchored to its
  input and now opens **upward** with its own scroll — instead of floating detached in the
  middle of the page (a side effect of the earlier clip fix). Opening upward also keeps the
  full list on screen without the framed page having to grow.
- **Wireless page no longer flashes stock colors.** The heavier settings pages (Wireless,
  DHCP) could still show the old ASUS styling for a split second when opened, because the
  framed content was revealed a touch too early. The frame now stays dark until it is fully
  themed, so the flash is gone there too.

## v1.7.3 — Gatekeeper reliability: no lockout, dependable cold-boot arming
- **No more admin lockout.** With Gatekeeper on, a device that was asleep or idle when you
  enabled the feature — potentially including the computer you administer from — could be held
  at the gate with no route back to the page that turns Gatekeeper off, and enabling it could
  quarantine much of the household at once. Turn-on now grandfathers every device the router
  already knows (its address table, its DHCP leases, and its named-client list), not only the
  ones talking at that instant, and the firewall now always leaves the HTTPS admin page
  reachable, so the owner can never be fenced out of the control that disables the feature.
- **Dependable arming after a cold boot.** After a full power-cycle, Gatekeeper could come up
  reading "on" without actually enforcing, because it tried to build its rules before the
  network was ready. It now resolves the network details when the rules are applied and
  re-applies them the moment the bridge is up, so enforcement is in place on its own.
- **Clear on/off state.** The Gatekeeper page now shows an "Arming" state while enforcement is
  coming up, and escalates to a visible "Not enforcing — check the System Log" warning if it
  ever fails to arm — so the feature is never silently off while appearing on.

## v1.7.2 — AiMesh node onboarding fix + UI polish + full menu translation
- **AiMesh node onboarding restored.** A factory-fresh router running Reaper could not be
  **found** when another router searched for a new AiMesh node — the search would run and
  return nothing. Cause: the v1.2.7 first-boot cleanup set the "already configured" flags on
  by default, which (as a side effect deep in the closed Wi-Fi stack) stopped the onboarding
  radio beacon a fresh node uses to announce itself, and left WPS onboarding enrollment
  disabled. The factory defaults are back to stock, and the first-boot setup wizard stays
  retired the intended way — at the web-server layer — so nothing about the login/first-run
  experience changes. A mesh already built under stock/Merlin firmware and then flashed to
  Reaper was never affected; this only concerns onboarding a **new** Reaper node. (After
  updating, a router intended as a node must be factory-reset on this firmware to become
  discoverable.)
- **Static-DHCP client picker no longer clips.** On **LAN &rsaquo; DHCP Server**, the
  "select a client" dropdown on the Manually Assigned IP table was cut off at the bottom of
  the page (adding a few rows to the table was a partial workaround). It now floats centered
  with its own scroll, so the full client list is always reachable.
- **No more stock-style flash.** Some settings pages briefly showed the old ASUS blue for a
  split second before the Reaper theme took over. Pages now paint dark from the first frame,
  and the framed content stays hidden until it is themed, so the flash is gone.
- **Full menu + page translation pass.** A sweep for untranslated interface text found that
  the **Gatekeeper** page and the **Wireless** diagnostics page still carried English in the
  24 non-English languages, and fourteen menu/tab labels (AI Advisor, System Info, VPN Status,
  VPN Director, DNS Director, Site Survey, Traffic Limiter, NFS Exports, Temperature,
  Notification, Tweaks, and others) were hard-coded English. All are now translated across the
  full language set (machine-assisted; native review still recommended before public release).
  Product and protocol names (Gatekeeper, AiMesh, VPN, IPv6, SNMP, MAC, Wi-Fi&hellip;) stay in
  their standard form, matching the stock UI's own convention. *Known limit:* the Gatekeeper
  "awaiting approval" waiting-room page is generated by the web server itself, outside the
  translation system, and remains English.
- All four changes are in shared code, so every model (RT-BE96U / RT-BE86U / RT-BE88U /
  GT-BE98 / GT-BE98 Pro) carries them; RT-BE96U is the primary, hardware-validated build.

## v1.7.1 — Security remediation batch + Network Map panel fix
- **Post-release security review — every finding fixed.** A full security audit of the v1.7.0
  release (centered on the new Gatekeeper subsystem) found no critical or high-severity issues;
  all ten findings — two medium, five low, three informational — are fixed in this rung:
  - **Wireless Diagnostics CSRF guard.** The Wireless page's control endpoint now requires the
    router's request token on every state-changing action (channel scans, captures, the
    channel-quality monitor toggle), the same guard the other Reaper endpoints already carried —
    a page you were tricked into visiting can no longer bounce a radio.
  - **Gatekeeper device-list race closed.** A decision saved at the same moment a guest pass
    expires can no longer be silently lost — both writers now re-read the device list under a
    lock before updating it.
  - **Gatekeeper MAC validation (defense-in-depth).** Every stored device entry is validated as
    a real MAC address before it reaches the firewall apply script, so a corrupted or hand-seeded
    hostile value is dropped, never executed.
  - **Robustness and hardening:** the Gatekeeper daemon ages out stale devices so its table can't
    fill over long uptimes; the first-boot wizard now submits the new password by POST (not in
    the URL) and actually checks the result — a failed credential save shows an error instead of
    redirecting as if it worked; reduced Gatekeeper self-heal fork churn; duplicate new-device
    log entries suppressed across daemon restarts; Traffic Analyzer per-queue QoS counter reads
    batched.
- **Network Map client panel fixed.** The client-status panel could overflow sideways into a
  horizontal scrollbar; the panel and its content box are now sized to fit, and the map's
  content area was widened to use the space properly.
- RT-BE96U flashed on hardware 2026-07-21 (core UI and Network Map verified; Gatekeeper's first
  on-hardware exercise still pending). All 5 models built + shipped, both variants each
  (RT-BE96U / GT-BE98 / GT-BE98 Pro / RT-BE86U on 2026-07-21, RT-BE88U on 2026-07-22).

## v1.7.0 — Gatekeeper: device access control + field-test fixes
- **Gatekeeper — you decide who gets on your network.** A new opt-in, **default-deny device
  access control** with its own page and menu entry. When you enable it, everything already on
  the network is grandfathered in; from then on each newly seen device is **held at the gate** —
  no internet, no reaching other LAN devices — until you choose: **Block**, **Full access**,
  **Internet only**, or a **timed Guest pass**. A held device that opens a web page sees a themed
  "awaiting approval" notice instead of a dead connection, and every new arrival is recorded in
  the system log. Enforcement lives at the firewall/bridge layer and **self-heals** — if a stock
  service flushes the rules, they are re-applied within seconds. Off by default. The page states
  the honest limitation: a MAC address *identifies* a device, it doesn't *authenticate* it — a
  determined user behind your Wi-Fi password can spoof one.
- **Factory-reset first-run fixes** (found in GT-BE98 field testing, applied to all models):
  a factory-fresh box could bounce forever between the dashboard and the first-run wizard (the
  wizard's Wi-Fi step was being rewritten into the app shell, which re-fired the gate — no
  settings reachable at all); and credentials entered in the first-boot wizard could fail to
  actually apply, locking the new login out after a factory reset. Both fixed.
- **UI fixes (series-wide).** The dashboard client panel's "VIEW LIST" control — previously an
  inert placeholder — now opens a client-list modal grouped by band (6 / 5 / 2.4 GHz / Wired)
  with name, IP, IPv6 and MAC; the WAN page's assigned-DNS list no longer clips its lower rows
  off-screen; the Network Map no longer stacks a double scrollbar.
- **Diagnostics v1.0.1** — fixes from the diagnostic report's first on-hardware run: MAC
  addresses written *without* colons are now pseudonymized like every other form (a redaction
  gap); over-eager masking of short brand words fixed; hardware-acceleration and QoS sections no
  longer come back empty on tools the shell lacks; per-station detail now covers guest and
  secondary interfaces; and the page layout was tightened around the download button.
- Consolidates the internal v1.6.8 build. All 5 models, both variants, built + shipped
  2026-07-21.

## v1.6.7 — Reaper Diagnostics
- **One-click sanitized diagnostic report.** New **Administration &rsaquo; Diagnostics** tab with a
  single Download button. It collects everything a network engineer would gather by hand — model
  and firmware identity, per-radio channel/width/signal health and client counts, wired port link
  states, hardware-acceleration and QoS engine readings, DHCP lease and service overview, and
  recent kernel/system log excerpts — in one pass, then pushes the **entire report through a
  redaction engine** before a single byte is written out.
- **Privacy by architecture, not by checklist.** Passwords, Wi-Fi keys and tokens are *never
  collected* (the report only notes SET/EMPTY); every MAC address becomes a consistent pseudonym
  (`MAC-3`), Wi-Fi names, usernames and hostnames become tokens, and all public IPv4/IPv6
  addresses are masked. Pseudonyms stay consistent within one report — a device can be followed
  across sections without revealing which device it is — and every report opens with a ledger
  counting exactly what was withheld. Because the whole document passes through the engine, even
  log lines nothing anticipated cannot leak identifiers.
- **Plain text, downloaded, never transmitted.** The report saves through the browser as a
  readable text file for review before sharing; the router sends nothing anywhere on its own.
  A busy overlay guards the 20–30 second collection. Available in all 25 interface languages,
  and the same collector is callable from SSH as `reaper_diag`.
- Both images built + shipped 2026-07-20.

## v1.6.6a — GT-BE98 System Info fix (GT-BE98 only)
- **Quad-band radio mapping on System Info.** Field testing on the GT-BE98 showed the System Info
  page mishandling this model's unusual radio order (both 5 GHz radios first, 6 GHz third, 2.4 GHz
  *last*): wireless client counts appeared under the wrong band headings with the 6 GHz row empty,
  the Temperatures panel rendered blank, and the fourth radio was missing from the Wireless Driver
  Version list. The page's per-model mapping had entries for the GT-BE98 Pro but never for the
  non-Pro — it now handles both, restoring correct client counts per band, all four radio
  temperatures with live charts, and the full driver-version list.
- GT-BE98 images only; built + shipped 2026-07-20.

## v1.6.6 — First-boot language selector, QoS Cake jitter tuning
- **Language selector on the first-boot wizard.** The initial setup card (administrator
  username/password and Wi-Fi) now carries a language selector at the top, so the interface
  language can be chosen *before* credentials are set. The selection carries through into the rest
  of the UI. Previously the wizard was English-only until setup was finished and the language could
  be changed from the main interface.
- **Cake QoS — ACK filtering on upload.** In Cake mode the upload shaper now filters redundant TCP
  ACKs. On an asymmetric line the upstream carries the ACK flood for every download; thinning those
  ACKs frees upstream capacity and cuts the upload-direction jitter that asymmetry creates. Applied
  to the upload direction only (the constrained one).
- **Cake QoS — tighter latency target.** Cake's AQM now targets a realistic broadband base RTT
  (50 ms) instead of its 100 ms internet default, trimming the standing queue and jitter. The value
  is adjustable via the `qos_cake_rtt` setting for per-line tuning without a rebuild.
- Both images built + shipped 2026-07-19.

## v1.6.5 — QoS download tuning
- **Download cap made foolproof.** The Hardware-Classful ingress policer now applies **10%
  headroom automatically** — you enter your measured download speed and the router caps at 90% of
  it. Previously the field expected you to do that math yourself, and entering your full line rate
  (a natural mistake) collapsed download throughput. The help text now says to enter your measured
  speed; no manual 90% math.
- **Cake mode consistency.** The Cake QoS mode applies the same 10% headroom to both upload and
  download, so both QoS engines read the bandwidth fields the same way — as your measured speeds.
- Both images built + shipped 2026-07-19.

## v1.6.4 — VPN theme fix, tablet layout, i18n sweep, audit hardening
- **VPN pages themed correctly.** The VPN Client and VPN Server pages had kept the stock ASUS
  blue accents. The cause was a cache-busting query string on the theme stylesheet request that
  the router's web server rejected, so the Reaper theme never loaded inside those nested frames.
  The query is removed and a dedicated palette pass recolors the remaining stock blues (buttons,
  checkboxes, input focus rings, dropdowns) to the Reaper crimson/jade/amber set, including
  retheming a stock cyan notice box on the VPN Server page.
- **Tablet / iPad layout.** On narrower tablet viewports some fixed-width pages could render past
  the screen edge with no way to pan to the cut-off content. The framed content area now pans
  horizontally when a page is wider than the column, and the header condenses so it always fits.
  (Phone-size screens remain out of scope by design.)
- **Network (SDN) page cut-off fixed.** Expanding a profile's General settings while Advanced
  settings were collapsed could push content past the frame with no way to scroll to it. The
  frame now grows to fit its content in that case.
- **Language coverage.** A full pass over every Reaper page confirmed all user-facing text follows
  the selected language. The first-boot setup wizard — which postdated the earlier translation
  work — was fully tokenized and translated across all 25 languages (machine-assisted; native
  review still recommended before public release).
- **`rchqd` monitor — syslog trail.** The passive channel-quality monitor now records
  degraded/recovered transitions to the system log (edge-triggered and rate-limited per radio),
  so interference events leave a timestamped trail even when the Wireless page is not open. It
  remains strictly read-only — it never changes a channel.
- **Audit hardening.** A pre-build security and quality review of the release drove a set of
  robustness fixes: the monitor's logging no longer depends on its JSON status file being
  writable (so a full RAM disk cannot silence it), a partial status write can no longer overwrite
  the last good one, radio state is cleanly closed out on a wireless restart, the log rate-limit
  now uses a monotonic clock (immune to time-sync steps), and its per-tick diagnostic overhead is
  roughly halved. On the web side, per-frame observers are now released on navigation and the
  tablet width logic was made convergent. No exploitable issues were found.
- Both images built + shipped 2026-07-19.

## v1.6.3 — Channel-quality syslog trail
- **`rchqd` degraded-event logging.** The opt-in passive channel-quality monitor gained a system
  log trail: when a radio's current channel deteriorates past the advisory threshold it writes one
  warning to the system log (with the channel and the measured interference), and a matching notice
  when it recovers. Logging is **edge-triggered** (only on the transition, not every sample) and
  **rate-limited per radio** so a channel hovering near the threshold cannot flood the log. This
  gives a timestamped record of interference events — useful for correlating intermittent Wi-Fi
  problems — without anyone needing to have the Wireless page open. The monitor stays opt-in and
  strictly read-only. Both images built + shipped 2026-07-19.

## v1.6.2 — Auto Scan across all bands
- **Band selector.** Auto Scan now runs on any radio, one band at a time via a selector, with a
  **separate report per band** and **Pin-best pinning the winner to that radio** — so you build up
  the best 6 GHz / 5 GHz / 2.4 GHz channels independently.
- **5 GHz + 2.4 GHz coverage.** 6 GHz is unchanged (the distinct 320 MHz blocks). **5 GHz** sweeps
  the nine non-DFS 20 MHz channels (UNII-1 36–48 + UNII-3 149–165) — **DFS 52–144 is skipped** so a
  scan stays quick — and Pin-best pins the **80 MHz block** around the winner. **2.4 GHz** sweeps
  1 / 6 / 11.
- **Band-aware report + plot.** The spectrum plot uses a per-band frequency axis and moves labels
  outside the bar for the narrow 20 MHz channels; the report names the band in its title.
- **Measurement hardening.** The first `chanim` sample after each channel change is discarded and a
  short settle added, fixing the occasional bogus post-restart noise-floor reading.
- Both images built + shipped 2026-07-18.

## v1.6.1 — Channel-Quality Auto Scan + passive monitor
- **Auto Scan (6 GHz).** A one-click sweep on the Wireless Diagnostics page that measures every
  6 GHz 320 MHz channel and ranks them by cleanliness, so a user can move to a clean channel
  without reading `chanim` output. It pins each candidate through the same supported
  channel-lock path (a live `wl chanspec` set does not stick on a running AP), samples the radio
  on it, then **restores the original channel**; the operator clicks **Pin best** to commit the
  winner (with a best-vs-current comparison shown first). It is the only path on the page that
  changes a channel — deliberately disruptive, warned before it runs. The candidate set is the
  distinct physical 320 blocks (one PSC representative each) across the whole band, validated
  against real hardware output.
- **Sweep is unattended-safe.** Closing the tab or navigating away stops the sweep immediately
  (unload beacon) and, as a crash backstop, a stale browser heartbeat aborts it — either way the
  radio is returned to its original channel. A progress bar with an ETA shows how far along it is,
  and the admin session is kept alive during the scan (the normal idle timeout resumes when it
  ends).
- **Downloadable report.** The results can be printed or saved as a **landscape PDF**, or
  downloaded as a self-contained **HTML** document — a ranked table (channel, frequency span,
  occupancy, free airtime, glitches, noise floor, score) plus a left-to-right **spectrum plot**
  that places each 320 block by frequency and colors it by occupancy, so the clean and dirty parts
  of the band are visible at a glance.
- **Clear-results button** on the on-demand capture panel (resets the view without a page reload).
- **Passive channel-quality monitor (`rchqd`) — opt-in, read-only.** A new background daemon
  (off by default) that watches only the *current* operating channel — the same non-disruptive
  on-channel read the capture panel uses — and raises a soft "degrading — consider Auto Scan"
  advisory when it deteriorates. It never changes a channel or restarts wireless; the remedy is
  always the user running Auto Scan. Modeled on `rtrafd`.
- **i18n.** All new strings tokenized across the 25 language dicts.
- Both images built + shipped 2026-07-18.

## v1.6.0 — hardening pass + full 24-language UI
- **Traffic collector (`rtrafd`) efficiency.** The live-view writer took the nvram lock three
  times on every 100 ms tick for values that only change on a settings apply (~30 lookups/s for
  the router's whole uptime); those are now cached and refreshed once a second (**30/s → 3/s**).
  The WAN byte counters are read by holding the sysfs files open and using `pread` instead of
  reopening them every tick; each top-talker's MAC is resolved once when its row is built rather
  than re-scanned on every write; and the Traffic Analyzer Live view rebuilds its per-device /
  per-network / top-talker tables at ~1 Hz (their data only changes every 5 s) while the rolling
  charts still draw every poll. All bounded — no behavior change.
- **Robustness.** All 83 of `rtrafd`'s ring allocations are NULL-checked at startup (was 4); the
  Advisor daemon (`rmcpd`) no longer leaks a pipe descriptor and a zombie child if a command's
  output handle fails to open after the fork.
- **Input-validation hardening (defense-in-depth).** The Advisor arm handler strips CR/LF and
  validates the client pin as a dotted-quad before writing it into its newline-delimited session
  file; the boot-time firewall sweep validates `lan_ifname` before splicing it into an `iptables`
  command.
- **AI Advisor — "Save settings" now confirmed.** It was posting to the apply CGI without the CSRF
  token and reporting success unconditionally; it now sends the token and checks the response, so a
  rejected save is reported instead of silently claimed. The **Refresh** button was also moved in
  next to the title.
- **Login / Logout favicon.** Both screens show the Reaper emblem in the browser tab (were the
  stock ASUS icon).
- **Full UI translation — 24 languages.** Every Reaper-authored page string is now translated into
  all 24 non-English languages the firmware ships (was English-in-every-dict fallback). A
  completeness sweep also caught the last hardcoded strings — the rail clock's weekday/month names,
  the AI Advisor "Copy snippet" button, the traffic-quota line, the Wi-Fi encryption labels, the
  dashboard tab title — and tokenized them. Where a translated label runs longer than its space it
  now truncates with an ellipsis and reveals the full text on hover, instead of stretching the
  layout. *Machine-assisted translation; English stays selectable.*
- **Cleanup.** Removed a never-fired QoS mode-link branch; stranded the disabled EULA-policy check
  as a no-op stub; corrected a stale watchdog comment about the acsd cooldown.
- Both images, built + shipped 2026-07-17.
- **RT-BE88U brought directly to v1.6.0** (2026-07-18): the full v1.5.2 → v1.6.0 line
  cherry-picked onto the RT-BE88U branch (its first build since the v1.5.0e port), both
  image variants. The RT-BE86U / GT-BE98 / GT-BE98 Pro branches remain at v1.5.9.

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
- UI only, both images, built and shipped 2026-07-17.
- **Wireless page — quad-band radio ceiling.** The v1.5.8 Wireless diagnostics backend
  enumerated at most three radios (a value carried over from the tri-band RT-BE96U), so on a
  four-radio model it hid the 4th radio and refused a channel capture on it. The ceiling is
  raised to four; it is self-configuring — a radio with no interface is skipped — so the
  RT-BE96U still shows exactly its three. No visible change on the RT-BE96U.

### v1.5.9 — sibling models RT-BE86U, GT-BE98, and GT-BE98 Pro
- **Both GT-BE98 variants and the RT-BE86U brought up to v1.5.9** (all of the above, plus
  the whole v1.5.2 → v1.5.9 line they had been missing: boot-efficiency, QoS v5 download
  side, the first-boot credentials wizard, the AI Advisor wireless-stations tool, the
  audit-fix rung, and the Wireless diagnostics page). All built in both variants — the
  cherry-pick applied with zero conflicts on each branch.
- **GT-BE98 (non-Pro) field-report fix.** A tester's GT-BE98 showed only three of four
  radios (no 6 GHz), an empty Wi-Fi client list, and roughly half the expected wired
  throughput. Root cause: the earlier GT-BE98 port linked four **GT-BE98 Pro** closed
  binaries as a stopgap — including the model-specific radio/board bring-up object — and the
  Pro's radio layout differs from the non-Pro's. All four are now the **official ASUS GT-BE98**
  binaries (from ASUS's GT-BE98 GPL source drop), with the build-compat shim reworked
  accordingly.
- Sibling-model images: flash only with a recovery path ready.

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
- Flashed to the physical RT-BE96U 2026-07-16.

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
    AiMesh config-sync client count, Advisor page CSS.

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
  **AA26-194A** (see `BACKLOG.md`). *Known limitation: the WiFi step releases on "configured",
  so an explicitly-open network can skip the PSK.*
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
  classified like upload — previously the classful engine shaped upload only.
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
  no functional change to the RT-BE96U image.

## v1.5.0e — Factory-reset recovery fix + first sibling-model builds
- **Fixed the factory-reset redirect loop.** On a factory-clean box the first-run gate pages and
  Reaper's serve-time bounce redirected each other forever, so the UI never loaded and the router
  appeared bricked (recoverable only via the ASUS rescue tool). Setup/QIS pages are now excluded
  from the bounce. *Reported by tester PorscheT — credit him in the public release notes.*
- **First builds for sibling BCM4916 models.** GT-BE98 Pro, GT-BE98, and RT-BE86U (plus RT-BE96U)
  each built in both variants — closing the "wider BE-series support" investigation.
  Sibling models: flash only with a recovery path ready. (A GT-BE98 field report is tracked in
  `BACKLOG.md`.)
- **Reproducible branch builds.** The `be96u-only` branch now builds cleanly from a fresh
  checkout (it previously depended on uncommitted working-tree deletions).

## v1.5.0d — De-ASUS rebrand (UI only)
- **New wordmark banner.** The `REAPER1` wordmark banner replaces the previous logo everywhere it
  appeared: the dashboard and app-shell headers, the login/logout card, and the stock-page banner.
- **AiMesh backdrop.** The AiMesh node card now uses the `RLogo` artwork; the old ASUS logo asset is
  removed from the build entirely.
- **Live rail clock.** The "ASUS · Merlin · Reaper" wordmark at the top of the left rail is replaced
  by a themed, live, 24-hour **router-time clock** (date + seconds), on both the dashboard and the
  app shell. No functional/firmware change.

## v1.5.0c — Compliance: license headers + font license (no functional change)
- **SPDX license headers** (`GPL-2.0-only` + copyright) added to every Reaper-authored source
  file (the Traffic Analyzer and AI Advisor daemons, the theme-injection filter, the Reaper
  pages, CSS, and Makefiles) — provenance hygiene, no behavior change.
- **Font license shipped in the image.** The SIL Open Font License 1.1 text is now installed as
  `www/fonts/OFL.txt` so the license for the bundled Inter/Rajdhani web fonts travels with the
  firmware, as OFL 1.1 requires. Part of the 2026-07-13 release-compliance pass
  (see `COMPLIANCE-AUDIT-2026-07-13.md`).

## v1.5.0b — Traffic Analyzer "Live (200ms)" mode + diag-aware AI Advisor
- **New "Live (200ms)" refresh mode** on the Traffic Analyzer. The collector's base tick moves
  from 1 s to 200 ms (work-time-paced so heavy samples never stretch the interval), giving the
  live WAN view true 5 Hz updates; the 1 s / 10 s / 30 s options remain and 1 s stays the default.
- **AI Advisor `initialize` instructions are now diagnostics-aware.** When a session has network
  diagnostics enabled, the Advisor is told the probes are active and to run them itself, instead
  of the previous static "read-only" wording that made it defer network probes back to the user.

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
