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

- **AI Advisor (v1.4.1) on hardware.** Arming, LAN-only bind, token auth, secret
  redaction, session-timeout teardown, and the Mode-B USB-key flow (enroll →
  arm-requires-stick → pull-stick-locks-within-~1s → wrong-stick-rejected).

## UI / UX polish

- **Remove the "Related Pages" block** at the bottom of the QoS panel.
- **Suppress old/replaced pages.** Stock pages that Reaper has superseded (e.g. the
  stock Traffic Monitor / Statistic pages and legacy QoS pages) are still reachable by
  URL — hide them.
- **Hide "Open NAT."** It's just port forwarding, already covered elsewhere.
- **Traffic Analyzer title line.** Update the summary/reading line next to the title
  to reflect the selected timeframe.
- **Scroll-to-top on page load.** Bounce every page to the top on load — inside the
  app-shell iframe a page can open scrolled down, hiding the tab strip and confusing
  users.
- **Network Map USB icon alignment.** 
- **VPN submenu colors.** A few off-theme colors still need correcting. 
- **Device-icon red theme is incomplete.** The red-on-black device icons apply only to
  the Network Map client list; other pages that render device/client icons still show
  stock white-on-grey — extend to DHCP manual assignment, Parental Controls, Access
  Control / MAC filter, Open NAT, Time Scheduling. 
- **AiMesh page background.** Change the image behind the router name to the ASUS logo.

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
- **Idle session timeout.** Auto log-out and close idle admin sessions.
- **NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST
  baseline.
- **Language packs.** Rectify and apply, matching ASUS's language capability.

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

- **Wider BE-series support.** Investigate firmware support for the other ASUS BE-series
  routers built on the Broadcom BCM4916.
