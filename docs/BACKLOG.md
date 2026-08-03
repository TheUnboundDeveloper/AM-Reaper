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

- **Wireless › Professional (`Reaper_WiFiPro.asp`) — drop the raw nvram field names.**
  Each setting row shows the underlying nvram variable name next to its friendly
  label (e.g. **"Enable Radio"** displays **`wlN_radio`**). Remove the variable
  name so only the friendly label shows (just "Enable Radio"). It's cosmetic —
  the field name is developer detail that shouldn't be user-facing.

- **AI Page Wording** "A read-only bridge that lets your own AI assistant read this 
  router's" is an incomplete sentance and needs to be corrected.

- **SSID Format** The dashboard SSIDs show all capitals vs. mixed case on the Network page.
- **Client ID** The traffic Analyser part, if checking the last 24 hours for example, if a 
  device goes offline - it will   just show the IP address and not the name - and when the 
  device comes back online - it will update the device name.

- Add07

## Known issues (cause identified)

- **[FIXED — patch 0311] Stock/old client list garbled device names containing an
  apostrophe (`'`) — and it was a reachable stored XSS, not just cosmetic.**
  Field report: a device named with a `'` renders broken on the **old (stock)
  client list** (Network Map client list / device-map popup) — "as if the name
  is treated as a string" — and renaming doesn't help until the `'` is removed.
  The **Reaper Devices tab shows the same names correctly.** **Cause:** the stock
  client-list JS (`www/client_function.js`, the incremental renderer) embedded the
  name in a **single-quoted** `value='...'` attribute via `htmlEnDeCode.htmlEncode()`,
  which encodes `& < > "` but **not** `'`. So a device whose name/DHCP-hostname
  contained an apostrophe broke out of the attribute — at best the editable name
  field truncated/garbled, at worst a name like `x' onmouseover='…'` injected an
  attribute into a page the authenticated admin views (**stored, LAN-reachable
  XSS** — the classic apostrophe-in-`'...'` issue, cf. reaper-ui rule 29, on a
  *stock* surface). Reaper's own Devices page was already safe via `esc()`.
  **Fix (v2.1.1-security-review, 2026-08-03):** additionally encode `'` → `&#39;`
  at the single point the name is prepared in `client_function.js`, closing both
  `value='...'` sinks and the display garble at once (also safe in the text
  contexts, where `&#39;` renders as `'`). The dashboard client list
  (`dashboard/js/clientlist.module.js`) was already safe — it HTML-encodes the
  name at ingestion and renders it in text context. **Residual (low, optional
  defense-in-depth, not the reported issue):** `client.vendor` / `deviceTypeName`
  are still emitted into single-quoted `title='...'` attributes unescaped in both
  files, but those are vendor/OUI-DB-sourced, not attacker-freeform. Surfaced by
  the 4-agent v2.1.1/v2.1.2 security review; **not built** (staged on `be96u-only`
  atop v2.1.2, rides the next rung).

- **Console error: stock ASUS privacy-policy fetch fails on the de-clouded build.**
  The browser console logs `Error fetching ASUS privacy policy: TypeError: Failed
  to fetch` — stock `asus_policy.js` `PolicyStatus()` (fired from `state.js` via a
  `setTimeout`) calls `httpApi.get(...)` to fetch the ASUS privacy policy and the
  request fails. **Cause:** Reaper is de-clouded, so that ASUS endpoint is
  removed/unreachable; the stock policy-status check still runs and throws.
  **Harmless** — console-only, no functional impact — but it's noise that a clean
  de-cloud build shouldn't emit. Fix: suppress/stub the stock policy fetch (or
  gate `PolicyStatus`) so it no longer runs, consistent with the other phone-home
  removals (see the phone-home surface map). [owed — cosmetic/de-cloud cleanup]

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

- **Warden Live block-count tracker not updating (v2.1.2).** On the Warden page
  (`Reaper_Warden.asp`), the **live blocked-count tracker does not update the
  count properly** — the displayed total does not track the actual blocks.
  Blocking itself appears to still work correctly (the system is functioning);
  this is a stats/display issue only. Likely in the live stats path
  (`do_reaper_warden_cgi` → `/tmp/rwarden/stats.sh` reading the live
  iptables/ip6tables `RW_DROP` packet counters) or its front-end refresh —
  check whether the counter read, the polling/refresh, or the display
  accumulation is at fault. Field-observed on v2.1.2. [owed]

- **BE98 Speed Test** Field reports that when QoS is enabled on the BE98 device 
  that the speed test crashes. Doesn't seem to affect everyone as some BE98 users 
  report no issues. Both claim to have the 1.8.6d installed which had the previous 
  fix for the crashing speed test. I have noticed potential soft crashes in speed testing 
  when I have class based QoS enabled.

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

- **Self-host the firmware update check on GitHub (remove Merlin's links/info from the
  update page).** The stock/Merlin update page shows Asuswrt-Merlin's update links and
  information, which **confuses Reaper users** about who provides their firmware. Explore
  pointing the update check at a **Reaper GitHub-hosted manifest** so the update page shows
  Reaper's own version info and release, with no Merlin references.
  - *Reference approach (gnuton's `webs_update.sh`):* the update-check script `wget`s a
    plain-text manifest from a GitHub raw URL
    (`https://raw.githubusercontent.com/<owner>/<repo>/<branch>/updates/manifest_3006.txt`),
    greps the line for `productid` (format `MODEL#...#FW<base.firm.build>#EXT<extendno>#`),
    parses base/firm/buildno/extendno, compares against the running `firmver`/`buildno`/
    `extendno`, and on a newer version sets the same stock nvram the GUI already reads:
    `webs_state_info=<base>_<firm>_<build>_<extendno>`, `webs_state_flag=1` (upgrade
    available), `webs_state_error`, `webs_state_update=1`, plus an optional `_note.txt`
    release note fetched the same way. The GUI update page renders from those nvram keys —
    so replacing the *source* + the page's Merlin text is the whole job for a notification.
  - *Reaper integration:* Reaper already declares `RTCONFIG_MERLINUPDATE` and hosts releases
    on GitHub (`AM-Reaper`) with `SHA256SUMS-*` and `provenance/manifest.json`. Generate the
    update manifest from the release process (`stage_release.ps1` / `release.yml`) so it
    stays in lockstep with what's actually published; per-model + **two-variant (MCP/noMCP)**
    awareness is required (the update must not offer to cross-flash a user from one variant
    to the other).
  - *Scope in phases:* **(1) notification-only** — tell the user a newer Reaper version
    exists and link to the GitHub release (low risk, removes the Merlin confusion now).
    **(2) download + flash** — needs a hosted `.pkgtb` URL in `webs_state_url`, the
    variant/model selection, and the on-request/GPL + image-signing considerations, so it's
    a larger, later step. Also rewrite the update page's Merlin-referencing text/links
    regardless of phase. [owed — explore]

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

**Pre-release code review 2026-08-02 — remaining item:**
- **GDX pool watchdog field-proving.** The accelerator pool-drain check is opt-in (`rwatch_gdx`,
  v2.1.0). Confirm the `/proc/gdx/skb_idx` read is non-destructive under sustained polling on
  hardware before it can be considered for default-on again. [owed — metal]

- **NOTE** *(The other five items from this review — Tier-3 error-string localization, structural rmcpd
  redaction, rmcpd truncation-to-valid-JSON, esc() on three pages, and the rwarden ipset-restore
  batch — shipped in v2.1.1; see the changelog.)*[DONE]

## Documentation

- **Note the non-functional retained features.** Document that the firmware
  update-check and the (removed) security-check UI do nothing on Reaper and are
  retained only for potential future use.

- **Annotate** the system defaults.

- **Write a user guide** for other users.

## Packages

*(OpenVPN 2.7.5 and the other Asuswrt-Merlin 3006.102.8 package updates — dropbear, miniupnpd,
strongswan — were carried forward in v2.1.2; see the changelog.)* [DONE]

## Platform / expansion

## Known issues (Cannot Remediate)

- **Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul
  BSS is still created even when every feature that would use it is disabled, spamming
  the log with RADIUS codes for an unused radio. Traced to a **closed-source Broadcom
  blob**; a boot-time script to suppress it based on device settings did not work and
  was reverted. [blocked — blob; risk-accepted]