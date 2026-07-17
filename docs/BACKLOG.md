# RT-BE96U "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done/verified), **[blocked]** (external cause),
**[shelved]** (deliberately deferred), **[cosmetic]** (polish, non-blocking).

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md); strategy/roadmap is in
> [`ENTERPRISE-ROADMAP.md`](ENTERPRISE-ROADMAP.md). Completed backlog items are
> moved to the changelog and removed from this file (housekeeping pass 2026-07-17).

---

## Testing / validation owed

- **v1.5.9 metal test.** **Built + shipped 2026-07-17** (both variants on the
  `reaper-firmware/` ladder: MCP image sha `f1e21d19…`, noMCP `a79c68f0…`, hashes in
  `SHA256SUMS-v1.5.9.txt`) — awaiting flash. The Traffic Analyzer resilience fix + the shell
  master-scrollbar theme (see `CHANGELOG.md` v1.5.9); full 6-point checklist in
  `reaper-firmware/METAL-TEST-v1.5.9.md`. Highlights: (a) far-right scrollbar is
  black/crimson on shell-framed pages (e.g. Network Map); (b) Analyzer Live view rides
  through an apply / Wi-Fi drop — pill flips to amber "No response", then recovers on its
  own (no more permanent freeze); (c) history windows visibly refresh (~30 s); (d) Live view
  survives a laptop sleep/resume; (e) second-language spot-check of the new "No response"
  string (`RTRF_72`; English in all dicts for now).

- **First-boot credentials wizard (shipped v1.5.5) — factory-reset metal test.** Factory
  reset → wizard appears → no page/dashboard reachable until username+password set → forced
  to the wireless page until a WiFi PSK is set → dashboard → values persist → all editable
  later; also confirm an *upgrade* (no reset) does **not** trigger it. **Known limitation
  (v1.5.5):** the WiFi step releases once WiFi is *configured* (`sdn_rl` changes), so a user
  could save it **open** and skip a PSK — optional tightening is to require a non-empty PSK
  (currently uses the stock `sdn_rl` signal for stability). Feature record in
  [`CHANGELOG.md`](CHANGELOG.md) v1.5.5; it replaces the stock forced password gate and is
  the concrete mitigation for deferred finding **H15** (see the AA26-194A section below).

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

## UI / UX polish

- **VPN submenu colors.** A few off-theme colors still need correcting. 
- **Restart/Boot Effciency** Investigate why the wifi and router reboots several times and 
  takes 10 min to stablize. Potential reordering of boot could make this quicker.
- **Mobile Compatibility** Need to work on the UI so that it looks clean in a mobile format like and iPad.
- **Shell cut Off** SDN.asp gets cut off when a network is selected and "Advanced Settings" is not 
  exapnded then you try to expand just the general settings.
- **DICT** Run another pass through the whole firmware to ensure all items that can be are translated.
  where the area is too small use an abrevation in the lauguage requested. Truncate words instead of 
  expanding the page elements. Any truncated words or abbreviations should have a hover over tooltip 
  built in that shows the whole word when you hover over it with your mouse.

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

- **SNMP hardening — un-shelve.** **[owed]** The primary advisory vector is SNMP with
  default/common community strings. Ensure the shipped default is **off / LAN-only**, reject
  default and common community strings, **disable SNMPv1/v2**, and prefer **SNMPv3 with
  `authPriv`**. `RTCONFIG_SNMPD=y` in the build — verify the current default state. This
  revisits the SNMPv3 line currently **[shelved]** under *Packages* / `PACKAGE-UPDATES.md`;
  the advisory is grounds to re-evaluate that "LAN-only risk accepted" decision.

- **WAN-side management-exposure audit.** **[owed]** The advisory targets internet-reachable
  devices. Verify that the web UI, SSH, Telnet, SNMP, and TFTP are all **OFF on the WAN
  interface by default**, and that no admin/management daemon listens on the WAN out of the
  box. Document the default posture per service.

- **Detection / logging for the advisory TTPs.** Surface and log config-exfil attempts and
  anomalous SNMP polling (spoofed-source reads). Ties into the **Remote syslog push/fetch**
  and **NIST-grade auditing** items under *Features to add*.

## Features to add

- **Remote syslog push/fetch.** The router can already send its log to a remote
  collector (send-only). Add the ability to **push to / be fetched by** analytics
  systems — most SIEM/analytics pipelines are push-based.
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
- **QoS v6?** Look into further QoS improvements.

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

- **RT-BE88U port — build-validated (v1.5.0e, both variants).** First-ever RT-BE88U build:
  blobs restored, target.mak de-clouded, dual-band 10G/SFP+. Build-only, **no metal test**.
  Model-specific build note: BE88U uniquely sets `BCM_JUMBO_FRAME=y` + a NEW
  `BCM_MAX_MTU_SIZE` kernel symbol, so it must be built **clean, single-pass** (the standard
  two-pass model script re-triggers kernel `syncconfig` on that NEW symbol and errors).

## Known issues — ported models (GT-BE98 / siblings)

- **GT-BE98: empty Wi-Fi client list + ~half wired throughput.** **[owed — needs diagnosis]**
  Field report on the shipped GT-BE98 image: (1) the **Wi-Fi client list appears empty**
  (associated stations not enumerated), and (2) a **speed test shows ~half the actual wired
  (Ethernet) rate**. Not yet investigated. This is almost certainly a **source/blob issue,
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
