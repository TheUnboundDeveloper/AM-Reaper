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

- **SSID Format** The dashboard SSIDs show all capitals vs. mixed case on the Network page.
- **Client ID** The traffic Analyser part, if checking the last 24 hours for example, if a 
  device goes offline - it will   just show the IP address and not the name - and when the 
  device comes back online - it will update the device name.

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
  (owner, RT-BEXXU). During boot the WAN/connection appears to initialize, drop, and
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

- **AWSIOT phone-home — removal plan (analyzed 2026-07-30 on v1.9.8; LINK-SAFE).** ASUS AWS-IoT
  cloud connector (`/usr/sbin/awsiot` + `/usr/lib/libawsiot_ipc.so`): carries ASUS-app remote
  (off-LAN) access, ASUS-account binding, and ASUS-cloud push. **Confirmed live on the RT-BEXXU
  itself, not just the siblings** — owner's v1.9.8 diag shows it running; the 2026-07-08
  phone-home audit missed it (its "no ASUS-cloud automatic outbound remains" claim is wrong).
  - *Why it runs despite `config_base` `# RTCONFIG_AWSIOT is not set`:* the behnd platform
    `Makefile` config-gen **force-re-adds** `RTCONFIG_AWSIOT=y` at `:1570` (`if [ "$(AWSIOT)"="y" ]`)
    and `:4195` (inside the non-`RP-` block, beside `RTCONFIG_ACCOUNT_BINDING=y`), so the generated
    `config_rt-BEXXU` carries `RTCONFIG_AWSIOT=y`. Result: `start_awsiot()` (services.c:13346) runs
    at boot and the **watchdog `awsiot_check()` (watchdog.c:8136) respawns it** — a runtime
    `killall awsiot` never sticks; it needs a build change.
  - *Removal IS link-safe (verified):* scanned every staged binary/lib — **nothing DT_NEEDs
    `libawsiot_ipc.so`** except awsiot, so dropping it does NOT hit the libcreduction/prebuilt-blob
    trap that blocked the AAE / libasc / conn_diag removals. No shim needed.
  - *Live vs inert:* AAE/mastiff IPC transport is already gone, but the closed awsiot binary may
    still open a direct AWS-IoT MQTT/TLS (:8883) session — confirm on metal before/after with
    `netstat -tnp | grep awsiot` or `conntrack -L | grep 8883`.
  - *Plan:* comment out the two `echo "RTCONFIG_AWSIOT=y"` lines in the behnd `Makefile` (`:1570`
    + `:4195`); the `#ifdef RTCONFIG_AWSIOT` gates then compile out start_awsiot + awsiot_check +
    the install lines. Weigh dropping the paired `RTCONFIG_ACCOUNT_BINDING` (same ASUS-cloud
    account surface) in the same pass. Edits the shared behnd Makefile → fleet-wide (all 5 models).
    VERIFY post-build: `config_rt-BEXXU` has no `RTCONFIG_AWSIOT=y`; `fs/usr/sbin/awsiot` absent;
    libcreduction clean; AiMesh + LAN-side app unaffected. Loses only ASUS-cloud remote/app
    features; nothing local depends on it. Candidate for v1.9.9. [owed]

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