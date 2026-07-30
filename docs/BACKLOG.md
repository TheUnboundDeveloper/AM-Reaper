# RT-BE Series "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done/verified), **[blocked]** (external cause),
**[shelved]** (deliberately deferred), **[cosmetic]** (polish, non-blocking).

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md); strategy/roadmap is in
> [`ENTERPRISE-ROADMAP.md`](ENTERPRISE-ROADMAP.md). Completed backlog items are
> moved to the changelog and removed from this file (housekeeping pass 2026-07-18).

---

## Testing / Validation

## UI / UX polish

- **Translation** Do a full pass to make sure all pages are translated.
- **No-JFFS graceful handling / disclosure.** Warden's feed cache is hardcoded to
  `/jffs/rwarden/sets.ipset`, but the project deliberately does **not** mandate JFFS. With
  JFFS off (or read-only) Warden still enforces fine (rules + ipsets are RAM/`/tmp`), but the
  cache write silently no-ops (`cache save produced no data`) and cross-reboot persistence /
  "last-good on a no-internet boot" never happens — with no UI indication of why. Detect
  no-JFFS and surface it (Warden page banner or the future storage tab: "protection is live
  but not persistent — enable JFFS or USB storage"). Note the cache must stay JFFS-locked in
  the Rung-B storage design (it has to restore *before* the firewall arms, earlier than any
  USB mount), so the honest fix is disclosure, not relocating it to USB. Applies to any other
  feature that assumes a writable `/jffs` (rwatch dumps already fall back; audit the rest).
- **802.1Q & P** Expose the options on the main WAN pages, BE98, IPTV tab under LAN?. [DONE][Ask USER]

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

- **Boot: connection comes up twice before it's ready.** Field-observed on metal
  (owner, RT-BE96U). During boot the WAN/connection appears to initialize, drop, and
  re-initialize before settling — clients may see a brief connect/disconnect flap at
  startup. Boot syslog shows the plausible chain: `start_services` runs, then
  `udhcpc_wan → restart_wan_if 0` + `restart_nasapps` + a `stop_ntpd/start_ntpd` and
  `stop_samba/start_samba` cycle, i.e. services start once, get torn down by the WAN
  bring-up, and start again. Investigate whether this is stock ASUS boot ordering
  (WAN DHCP landing after first service start) or something Reaper-introduced, and
  whether the re-init can be deferred until the WAN is actually up (single settle).
  Cosmetic/UX, not a fault — but worth understanding before the weekend audit.
  Cross-ref the boot-efficiency recon notes. [owed — investigate]

- **AI Mesh Search** Investigate the operation of search as it was reported 
  non-functional awhile back.  

- **BE98 Speed Test** Field reports that when QoS is enabled on the BE98 device 
  that the speed test crashes. Doesn't seem to affect everyone as some BE98 users 
  report no issues. Both claim to have the 1.8.6d installed which had the previous 
  fix for the crashing speed test.

## Features to add

- **Remote syslog push/fetch.** The router can already send its log to a remote
  collector (send-only). Add the ability to **push to / be fetched by** analytics
  systems — most SIEM/analytics pipelines are push-based.

- **NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST
  baseline.

- **Change Audting** Add more logging information and details such as when a feature 
  is turned on, off, or changed setting.

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

- **AWSIOT** Phone home tunnel still active and in code on the sibling devices. Remove them.

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