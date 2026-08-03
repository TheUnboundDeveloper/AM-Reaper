# RT-BE Series "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done/verified), **[blocked]** (external cause),
**[shelved]** (deliberately deferred), **[cosmetic]** (polish, non-blocking).

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md). Completed backlog items are
> moved to the changelog and removed from this file (housekeeping pass 2026-07-18).

---

## Testing / Validation

## UI / UX polish

- **AI Page Wording** "A read-only bridge that lets your own AI assistant read this 
  router's" is an incomplete sentance and needs to be corrected.

- **SSID Format** The dashboard SSIDs show all capitals vs. mixed case on the Network page.
- **Client ID** The traffic Analyser part, if checking the last 24 hours for example, if a 
  device goes offline - it will   just show the IP address and not the name - and when the 
  device comes back online - it will update the device name.

- **Channel Lock confirmation modal.** On the Wireless Diagnostics page
  (`Reaper_Wireless.asp`), **locking** a channel restarts that radio (~20 s client
  drop on the band) — exactly like unlocking, but only **Unlock** currently warns
  first (added v1.9.9a). Add the matching confirmation modal to **Lock**: state that
  continuing will **restart the Wi-Fi and briefly drop clients on that band**, with
  Continue / Cancel, before it applies. (Per-frequency restart isn't possible on this
  platform, so the radio restart is unavoidable — the modal just makes it expected.)

- **Connections page (`Reaper_Conn.asp`) layout + labels.** (1) **Shift the content left** — the
  Connections page/flow table sits shifted right and runs outside the viewport, unlike every other
  Reaper page which fits inside it; align it to the viewport like the others. (2) **Rename the "Q"
  column header to "QoS Class"** (it is the egress QoS queue/class the flow maps to — see the QoS
  Diagnostics page). (3) **Increase the font size** in the page header and the flow-detail title
  area (both currently render small).

- **Wireless › Professional tab (`Reaper_WiFiPro.asp`) shifted right.** Same viewport-alignment
  issue as the Connections page above — the all-bands Professional page sits shifted right instead
  of fitting inside the viewport like the other Reaper pages; shift it left to match.

- **Traffic Manager › QoS Diagnostics (`Reaper_QoSDiag.asp`) shifted right.** Same viewport-shift
  again — shift the page left so it fits the viewport like the other Reaper pages.

> **Likely shared root cause:** three of the newest Reaper-native pages — **Connections**
> (`Reaper_Conn.asp`), **Wireless › Professional** (`Reaper_WiFiPro.asp`), and **Traffic Manager ›
> QoS Diagnostics** (`Reaper_QoSDiag.asp`) — all sit shifted right / overflow the viewport, while the
> older Reaper pages fit correctly. They almost certainly share a common container/margin in the
> newer page template; fix all three together (and re-check any future page built from that template).

## Known issues (cause identified)

- **First-boot credentials wizard (shipped v1.5.5) — factory-reset metal test.** Factory
  reset → wizard appears → no page/dashboard reachable until username+password set → forced
  to the wireless page until a WiFi PSK is set → dashboard → values persist → all editable
  later; also confirm an *upgrade* (no reset) does **not** trigger it. **Known limitation
  (v1.5.5):** the WiFi step releases once WiFi is *configured* (`sdn_rl` changes), so a user
  could save it **open** and skip a PSK — optional tightening is to require a non-empty PSK
  (currently uses the stock `sdn_rl` signal for stability). Feature record in
  [`CHANGELOG.md`](CHANGELOG.md) v1.5.5; it replaces the stock forced password gate and is
  the concrete mitigation for deferred finding **H15** (see the AA26-194A section below).

## Known issues (under investigation)

- **AI Mesh Search** Investigate the operation of search as it was reported 
  non-functional awhile back.  

- **BE98 Speed Test** Field reports that when QoS is enabled on the BE98 device 
  that the speed test crashes. Doesn't seem to affect everyone as some BE98 users 
  report no issues. Both claim to have the 1.8.6d installed which had the previous 
  fix for the crashing speed test. I have noticed potential soft crashes when I have 
  class based QoS enabled.

- **MTU PPOE** Merlin had changed firmware to support 1500, so that Baby Jumbo Frames 
  (supported in UK on full fibre) could be supported. I think that value translate the WAN 
  to encapsulate 1508 WAN packet size. Its in the RFC4638 standard too so not something that 
  isn't a standard. RFC 4638 allows the underlying physical Ethernet interface to handle slightly 
  larger frames (usually 1508 bytes) so that the upper PPPoE layer can maintain a clean 
  1500-byte MTU/MRU.

- **The router is configured for dual-WAN failover**
  The active secondary WAN uses the 2.5 Gbps LAN port with DHCP and its own NextDNS profile.
  The future primary WAN uses the 10 Gbps LAN port with PPPoE, but it is not yet connected. It 
  has a separate NextDNS profile and DNS server addresses. The router currently fails over to 
  the active 2.5 Gbps connection. Despite only one WAN being live, both NextDNS profiles are 
  receiving DNS log entries. The expected behavior was for only the active WAN’s profile to show 
  traffic.

  There are also two configuration questions:
  When both WANs are active, which public WAN IP does ASUS Dynamic DNS register?
  Why does the IPv6 configuration appear to be global rather than configurable separately for each 
  WAN in both stock ASUS firmware and Asuswrt-Merlin?

## Features to add

- **Staged ("batch") changes — one save, minimal restarts.** Owner request. Today each control
  applies immediately, so e.g. changing all three Wi-Fi bands = three applies + three
  `restart_wireless`. Add a staging layer: a control's Apply becomes "Add to changes", writing
  the intended nvram diff into a cross-page **pending basket** (localStorage, under the Reaper
  shell) instead of applying; a persistent shell bar shows *"Pending changes (N) — Review /
  Apply / Discard"*; a review modal lists every staged change (page → setting → old⇒new). On
  Apply, the engine validates ALL first (all-or-nothing, like the Warden save), writes nvram in
  one commit, then runs the **de-duplicated, correctly-ordered** action set ONCE — reboot only if
  a staged change is reboot-class.
  - *Feasible — backend already supports it:* one apply POST carries many nvram keys + a chained
    `action_script` (`restart_wireless;restart_qos;…`), and `restart_wireless` cycles all radios
    at once, so "3 restarts" is a UI artifact, not a firmware limit. The missing piece is the
    accumulate-then-fire UI.
  - *Hard parts:* (1) an nvram-key → required-action map + safe ordering (e.g. firewall after
    wireless); (2) a **reboot-class table** — most changes are service restarts (seconds), but a
    few need a COLD reboot (MLO enable/disable; some SDN / operation-mode switches) so the engine
    must not reboot needlessly; (3) staleness/conflict if nvram changed underneath between staging
    and apply; (4) **scope** — clean for Reaper-authored pages (we own their save handlers), hard
    for stock ASUS pages (vendor `applyRule`/`showLoading` JS is invasive to intercept).
  - *Recommended path:* Reaper-native pages first. Quick sub-win for the Wi-Fi case: a single
    Reaper Wireless page showing all three bands that applies once. The full cross-page
    transaction system is substantial — its own project, v-next.

- **Remote syslog push/fetch.** The router can already send its log to a remote
  collector (send-only). Add the ability to **push to / be fetched by** analytics
  systems — most SIEM/analytics pipelines are push-based.

- **NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST
  baseline.

- **Diag: regulatory-mismatch warning.** Make `reaper_diag` (and possibly a Wireless-page
  hint) print an explicit `WARN: territory_code=EU/xx but wlX_country_code=US` style line
  when the factory territory and the per-radio country codes disagree — self-documents
  gray-market / region-switched units in field reports. Field-observed 2026-07-28 on two
  EU GT-BE98s (`territory EU/01`, all radios `US`); also a suspect in the "Wi-Fi 7 client
  refuses 6 GHz, camps on 5 GHz @80 MHz" report (strict EU clients may reject a US country
  IE). Read-only nvram compare, no behavior change — firmware must never auto-alter a
  unit's regulatory nvram. [shelved]

## Code-scan findings 

**Deliberately deferred (with reason), still open:**
- **`poll_fcache` O(n²)→hash pairing** (`rtrafd.c`). Bounded to ≤1536 flows every 5 s and
  it sits in the metal-validated per-client accounting path — a rewrite of a millisecond-
  scale loop isn't worth the regression risk. Revisit only if a flow-heavy box shows real
  cost. [shelved]

- **`poll_classes` 7× `tmctl` popen batch** (`rtrafd.c`). Metal already measured 2–3 % CPU
  at the class-poll cadence; treating this as a non-issue per the prior finding. [shelved]

**Pre-release code review 2026-08-02 — deferred (six-agent review; no critical/high, and none of
the below is attacker-reachable today; the confirmed/reachable items were fixed in v2.1.0):**
- **Tier-3 CGI error strings not localized.** ~37 hardcoded English error messages in the Devices
  and Advisor CGI handlers (surfaced to the user via `alert(...)`), plus two web pages, bypass the
  translation dictionary. Localization gap only — no behavior or security impact. [owed]
- **`rmcpd` secret-redaction is by-convention, not structural.** Only two of the Advisor daemon's
  tools route their output through the secret scrubber; the others are safe today purely because of
  the specific sources chosen (MAC/IP/RSSI/firewall rules — no secrets). A future tool added to the
  same pattern would bypass redaction silently. Make the scrub structural before extending the MCP
  tool surface. [owed]
- **`rmcpd` output truncation can emit malformed JSON.** When a tool's combined output hits the size
  cap the buffer is cut mid-structure; emit a truncation marker / close it cleanly. Affects only the
  availability of that Advisor payload. [owed]
- **Three pages lack an escape helper (defense-in-depth).** `Reaper_Conn`, `Reaper_QoSDiag` and one
  `Reaper_QoS` field render server/system-supplied strings without the `esc()` wrapper their sibling
  pages use. The data feeding them is kernel/system-formatted or admin-set (not attacker-controlled),
  so there is no reachable XSS today; add the wrapper for consistency and future-proofing. [owed]
- **`rwarden` per-entry `ipset add` fork loop.** Large threat/geo feeds are added one fork per CIDR
  on every refresh; switch to a single `ipset restore` batch. Performance only, opt-in feature. [owed]
- **GDX pool watchdog field-proving.** The accelerator pool-drain check is now opt-in (`rwatch_gdx`,
  v2.1.0). Confirm the `/proc/gdx/skb_idx` read is non-destructive under sustained polling on
  hardware before it can be considered for default-on again. [owed — metal]

## Documentation

- **Note the non-functional retained features.** Document that the firmware
  update-check and the (removed) security-check UI do nothing on Reaper and are
  retained only for potential future use.

- **Annotate** the system defaults.

- **Write a user guide** for other users.

## Packages

## Platform / expansion

## Known issues (Cannot Remediate)

- **Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul
  BSS is still created even when every feature that would use it is disabled, spamming
  the log with RADIUS codes for an unused radio. Traced to a **closed-source Broadcom
  blob**; a boot-time script to suppress it based on device settings did not work and
  was reverted. [blocked — blob; risk-accepted]