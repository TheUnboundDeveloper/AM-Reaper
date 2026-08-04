# RT-BE Series "Reaper" — Changelog

High-level history of the Reaper build. One entry per version, big changes only —
the exhaustive security detail is in [`REAPER-FIXES.md`](REAPER-FIXES.md) and the
per-release summary in [`RELEASE-NOTES.md`](RELEASE-NOTES.md).

All versions are the `3006.102.8_Reaper_v<X>` firmware line, built on the
Asuswrt-Merlin 3006.102.8 base for the ASUS RT-BE Series (BCM4916 platform).
The RT-BEXXU is the primary, hardware-validated model; the **RT-BE86U**,
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

## v2.1.4 — Factory-reset lockout fixed, WireGuard peer-row polish, OpenVPN version label corrected
- **Factory reset no longer strands you at the credential step.** On a factory-fresh box, logging in with the default admin/admin could land you on the stock ASUS "Change the router login password" page, which then collided with Reaper's own first-boot credential page — the second attempt failed with "Could not apply credentials" and left you unable to continue (recoverable only by restoring the stock firmware). Reaper now routes a default-password box straight to its single themed first-boot page, so the credential change happens once and applies cleanly. Reported on the GT-BE98; the fix is shared code and applies to every model.
- **WireGuard peer list — the edit control is reachable and centered.** On the VPN client peer list, the three-dots edit toggle was cramped against the delete/export buttons and could clip off the right edge of the view; it is now centered in its circle with room to spare, and the action buttons no longer run off-screen. (This also brings the siblings up to the earlier WireGuard peer-list icon fixes, which had not reached them.)
- **OpenVPN now reports its real version (2.7.5).** The 2.7.5 update shipped in v2.1.2, but the version string the router displayed stayed "2.7.4": a stale generated build file left the label frozen at the old value even though the running binary was already 2.7.5. The label is now regenerated correctly and reads 2.7.5 — a display correction only, the code behavior was unchanged.
- Built + shipped, RT-BE96U both variants, 2026-08-04; the RT-BE86U, RT-BE88U, GT-BE98 and GT-BE98 Pro builds follow.

## v2.1.3 — Connections "Quick Look", baby-jumbo PPPoE, a stored-XSS fix, and UI polish
- **A stored cross-site-scripting hole in the stock client list is closed.** A device whose name or DHCP-hostname contained an apostrophe rendered broken on the stock Network Map client list — and the same flaw was a reachable stored XSS: the stock renderer placed the name in a single-quoted HTML attribute and encoded `& < > "` but not `'`, so a crafted name could break out of the attribute on a page the authenticated admin views. The name is now additionally apostrophe-encoded at the single point it is prepared, fixing both the display garble and the injection at once. Reaper's own Devices page was already safe.
- **Connections page — a "Quick Look" default view.** The Connections page now opens on a simple at-a-glance list — device name, local IP, remote IP:port, an internal-vs-external badge, protocol and TCP state — resolving device names from the client list rather than showing bare IP addresses. The existing live flow explorer is retained as "Advanced" (now with a Pause option, and the device name + connection state in its detail panel); a single slider switches modes and your choice is remembered.
- **Baby-jumbo PPPoE MTU (RFC 4638).** The WAN GUI now allows a 1500-byte PPPoE MTU/MRU (with the parent interface raised to 1508) for full-fibre lines that support it, instead of the usual 1492. It is opt-in — the nvram defaults are unchanged, so existing PPPoE users are unaffected.
- **Three UI touch-ups.** The all-bands Wireless Professional page no longer prints the raw nvram variable name beneath each setting; the AI Advisor's intro sentence is no longer truncated ("…read this router's **status and configuration.**"); and the dashboard radio tiles show the SSID in its real mixed case instead of all-caps.
- Built + shipped, both variants, 2026-08-03.

## v2.1.2 — Asuswrt-Merlin 3006.102.8 carry-forward
- **The fixes from the final Merlin 3006.102.8 release are folded in.** Reaper's base is pinned to the 3006.102.8 beta; this release carries forward the fixes Merlin landed between that beta and the final 3006.102.8 / 3006.102.8_2 production releases. There are no Reaper feature changes in this rung — it is purely an upstream carry-forward.
- **OpenVPN updated to 2.7.5.** This is the 2.7 line, which removes some long-deprecated server options. If you run an OpenVPN *server* with an older configuration, confirm it still connects after updating.
- **Security and package updates.** Dropbear (SSH) updated to 2026.94, a strongswan build fix (a missing executable), and a miniupnpd update; the default UPnP SSDP advertisement interval is now 900 s.
- **IPv6 address handling corrected.** The router now reports the correct IPv6 prefix length for the LAN address and clamps a delegated prefix to /64 where appropriate (mostly affects non-SDN / non-multilan setups; largely inert on this model). A custom DDNS update now also sets the IPv6 record on success.
- **Web-UI fixes carried over.** The client list now redraws incrementally instead of rebuilding the whole table, DHCP-reservation export works on iOS devices, the Traffic Analyzer no longer depends on the (removed) DPI engine to be available, and an obsolete USB-modem tweak was dropped.
- Carried as upstream commits with their original authorship preserved. Not carried: changes that don't apply to this model (a UI4-only popup, an OpenSSL bump for a different SoC, a sibling build-profile fix, and minor stock-page chart cosmetics).
- Built, both variants, 2026-08-03.

## v2.1.1 — Localized error messages, defense-in-depth hardening, and three UI fixes
- **The last hardcoded English is gone.** About three dozen error messages on the Devices and AI Advisor pages (e.g. "invalid MAC address", "the reservation store is full", "incorrect code") were shown in English regardless of your language; they now resolve through the translation dictionary in all 25 languages, with the English text kept as a safe fallback.
- **Two AI Advisor internals made structurally safe.** The Advisor daemon's secret-redaction — which strips passwords and keys from anything it returns — is now applied at the single point where every tool's output leaves the daemon, instead of tool-by-tool, so any future tool is covered automatically. And when a tool's output is too large to fit and gets truncated, the daemon now always returns valid JSON with a truncation marker rather than a cut-off response.
- **Extra escaping on three pages.** The Connections, QoS Diagnostics and QoS pages now pass system-supplied strings (port names, flow addresses, class names) through the same escape helper the other pages use — defense-in-depth; there was no reachable issue.
- **The Warden threat/geo block-lists load much faster.** Large feeds were added one address at a time — one process per entry — on every refresh; they now load in a single batched operation, with the old per-entry path kept as an automatic fallback if a malformed entry appears.
- **Three pages fit the window properly.** The Connections, QoS Diagnostics and all-bands Professional pages sat shifted to the right and could run off the edge of the frame; they now fill and left-align like every other Reaper page. The Connections page also gained a clearer **"QoS Class"** column header (was just "Q") and larger page and flow-detail titles.
- **Channel Lock now warns first.** On the Wireless Quality page, locking a channel restarts that radio (about a 20-second client drop on the band) exactly as unlocking does; Lock now shows the same Continue / Cancel confirmation that Unlock already had.
- Built + shipped, both variants, 2026-08-02.

## v2.1.0 — Pre-release code review, a hardening pass, and three more fully-translated pages
- **A full pre-release code review of every Reaper-authored component — no critical or high-severity issue found.** Six independent reviewers swept the web-server handlers, the background daemons, and the pages across six dimensions (security, memory/handle leaks, dead code, bloat, correctness, and privacy). The code came back clean of any reachable exploit or leak; the review's confirmed items are fixed in this release and the remainder is recorded in the backlog.
- **Hardening fixes applied.** Several admin-page JSON fields (a QoS-diagnostics value, the Advisor's saved client address, a couple of device band labels) are now escaped consistently, so an unusual stored value can never malform a status response. The live Connections feed's read of the flow accelerator is now single-flighted, so two open tabs can't pile concurrent reads onto that kernel surface. The Wireless status endpoint now carries the same anti-forgery token as the rest of the interface (it launches a short-lived helper per radio, which a background page should not be able to trigger). The Gatekeeper enable-time device snapshot now takes the same lock its sibling writer uses, and some dead code was removed. One developer device address left in a source comment was scrubbed.
- **The accelerator health probe is now opt-in.** The watchdog's check of the hardware forwarding pool — which reads a kernel accelerator file every few minutes — is now off by default and enabled with a single setting. The everyday probes (gateway reachability, loopback DNS, and the Warden self-lockout canary) stay on by default.
- **Three more pages fully localized.** The Connections, QoS Diagnostics, and all-bands Professional pages still carried hardcoded English; 132 strings across them are now translated into all 25 languages, and fourteen previously English-seeded interface labels were given real translations. No behavior change — localization only.
- Validation build (both variants) 2026-08-02.

## v2.0.8 — QoS Diagnostics dropdown fix + wording and localization touch-ups
- **The QoS Diagnostics port selector stays open now.** The port dropdown was being rebuilt on every refresh tick, which snapped it shut before you could pick a port; it is now rebuilt only when the port list actually changes (and never while you have it open), with the current selection kept in place.
- **"Wireless Diagnostics" is now "Wireless Quality," and a Devices label is corrected.** The Wireless tab was renamed to Wireless Quality across all 25 languages, and a Devices-page label that read "Network legible" is corrected to "Network Ledger" (each language had faithfully translated the typo's apparent meaning).
- Built + shipped, both variants, 2026-08-02.

## v2.0.7 — QoS Diagnostics reliability
- **The QoS Diagnostics page now reads the hardware traffic manager reliably.** It previously reached the accelerator through a shell alias that existed only by way of an untracked helper a rebuild could silently drop, so on some builds the page came up empty; it now calls the accelerator shell directly using the session id the router writes at boot. The page's live rate and drop figures are also now aware of the hardware's 32-bit byte counters wrapping (observed about every 15 seconds at ~2 Gbps), which had caused periodic zero-rate ticks; a counter reset is discarded rather than shown as a spike.
- Built + shipped, both variants, 2026-08-02.

## v2.0.6 — Connections: a live flow explorer with hardware-acceleration insight
- **The Connections page is now a live flow explorer.** It replaces the old list (source / destination / port / state only) with a per-flow view drawn from the router's Runner flow accelerator. For every active connection it shows source and destination, protocol, whether the flow is forwarded in hardware (the Runner) or by the CPU — with a real per-flow hardware-vs-CPU percentage split — plus the egress queue, DSCP, live throughput, total bytes, and true connection age. Summary cards show how many flows are hardware-accelerated and the overall hardware-vs-CPU forwarding split; filters narrow to accelerated or CPU-path flows, and a detail panel expands any flow.
- Live polling (500 ms – 4 s) runs only while the page is open. Connection age is tracked continuously by the resident traffic collector, so it stays accurate even for flows that started before you opened the page.
- The stock connection page is retained unchanged as a fallback.
- Built + shipped, both variants, 2026-08-01.

## v2.0.5 — Hardware QoS Diagnostics
- **New "QoS Diagnostics" page** under Traffic Manager (right of the QoS tab) — a live view of the router's hardware traffic manager (the Runner/XRDP egress scheduler). Per queue it shows live occupancy, drop rate, an estimated delay, the scheduling discipline (strict-priority / weighted round-robin) and weight, the AQM algorithm and the shaper rate, plus per-queue occupancy and drops graphs and a selected-queue detail card. It reads the accelerator directly (the on-box bdmf shell) — including occupancy, which the vendor CLI can't report — and adapts to your QoS mode: a single shaped queue under Hardware PI2, or the full weighted scheduler under HW Classful. A port selector exposes the per-port (WAN upload / LAN download) schedulers.
- Fast polling (250–500 ms) runs only while the page is open; the background collector stays at its normal cadence. Estimated delay is derived (backlog ÷ shaper rate); drops are the combined tail+AQM counter.
- Built + shipped, both variants, 2026-08-01.

## v2.0.4 — Safer out of the box: Wi-Fi Protected Setup off by default
- **WPS is now off by default.** On a fresh install or factory reset, Wi-Fi Protected Setup (the push-button / PIN pairing feature) no longer starts enabled. WPS — especially its PIN method — is a long-standing proximity attack surface, and Reaper's goal is that only physical access should be able to compromise the router; you add devices with the Wi-Fi password or a QR code instead. It remains a one-click toggle in the GUI for anyone who wants it.
- **UPnP master switch off by default.** The global UPnP flag now matches the per-WAN setting (which was already off), so automatic port-opening stays fully closed out of the box — belt-and-suspenders, with no change for anyone who wasn't already using UPnP.
- A full factory-default audit confirmed everything else unneeded is already off or not built: remote web admin, SSH, Telnet, WAN ping, FTP, media server (DLNA), DDNS, guest network, SNMP, custom-script execution, remote logging and IPv6 all default off, and TrendMicro DPI / AiProtection, LLTD, AiCloud/WebDAV, IFTTT and Alexa are compiled out entirely. USB-drive auto-sharing and the roaming assistant were deliberately kept at their defaults.
- Built + shipped, both variants, 2026-08-01.

## v2.0.3 — One Wi-Fi "Professional" page that fits every router
- **The all-bands Professional page now builds itself from your router's actual radios.** It previously assumed exactly three bands (2.4 / 5 / 6 GHz), so on a four-radio router like the GT-BE98 the fourth radio simply didn't appear. The page now reads the real radio list from the router and generates one column per radio, labeled by its frequency band — and a router with two same-band radios is labeled clearly (e.g. "5 GHz-1" / "5 GHz-2"). Per-band settings and their options follow each radio's band, so every control lands on the right radios automatically.
- **Tidier, easier-to-read layout.** The setting fields were far larger than the values they held; they're now compact with values centered, the table centered in the window, and the dropdown lists centered too — easier to track across bands and leaving room for four-radio models.
- Built + shipped, both variants, 2026-08-01.

## v2.0.2 — File sharing signs in properly, cleaner share names, faster updates
- **SMB file sharing now signs you in from a clean boot.** After the file server itself was fixed in v2.0.1, account-mode shares still refused *every* login: the password database came up empty on each boot, so Windows quietly fell back to a guest session and returned a cryptic "Encryption is not supported for guest access" error. The cause was that the boot-time step which registers each share account was calling the Samba password tool by a path that doesn't exist on this build (the tool moved location between Samba versions), so no account was ever written. It now calls the correct path, and your username and password work on the first try after any reboot.
- **A login prompt instead of a cryptic error.** When a computer connects without stored credentials, an account-mode share now asks for a username and password like any normal network drive, instead of silently dropping to a guest session and failing.
- **Cleaner share names.** A share is now named for its folder (e.g. `reaper`) instead of the old `folder (at DISK)` form — the spaces and parentheses in that name broke command-line access. The disambiguating "(at DISK)" suffix is kept automatically only when two disks hold a folder of the same name. (A per-router toggle still lets you choose the old form.)
- **~11 seconds off every firmware update.** A shutdown step that briefly power-cycles the LAN ports (to nudge clients into renewing their address) was already skipped on a normal reboot, but not on a firmware update — so every flash sat idle for ~11 seconds. It's now skipped on updates too.
- **Channel-quality alert threshold is tunable.** The passive channel monitor's "degraded" trigger — previously fixed at 20% undecodable airtime — can now be adjusted live via the `rchq_degraded` setting, with no rebuild and no restart needed.
- Built 2026-08-01, both variants.

## v2.0.1 — De-clouded, the file server starts again, quieter logs
- **The ASUS cloud connector is removed.** The ASUS AWS-IoT client — which carried off-network ("remote") ASUS-app access, ASUS-account binding, and ASUS-cloud push — was still compiled in and respawned at boot even after the earlier phone-home cleanup (a build config-generator quietly re-added it). It and the paired account-binding surface are now excluded from the build entirely. AiMesh and local-network app access are unaffected; only ASUS-cloud remote features are lost.
- **File sharing starts again (Samba 4).** v2.0.0's move to Samba 4 shipped a file server that never actually started — the daemon exited on every boot because its private libraries weren't on the loader search path and two runtime directories were missing, so Windows reported "can't find the path." The packaging is fixed and `smbd`/`nmbd` now start on boot. The Samba protocol dropdown was also relabeled to match Samba 4 (SMB2 only / SMB2 + SMB3 / SMB3 encrypted), and the obsolete SMB1 option removed.
- **A benign kernel debug flood is silenced.** A stock Broadcom flow-accelerator debug line (`blog_get_dstentry_by_id: match fails`) could flood the system log in bursts on this build, because its logger can't filter by severity. The harmless message is now gated off at the source. *(Flip the source define to re-enable it for debugging.)*
- Built + shipped, both variants, 2026-08-01.

## v2.0.0 — Security-hardening milestone: two full code audits, fixes applied
- **What 2.0.0 is.** This release marks a comprehensive security review of the whole firmware. Two end-to-end audits were run — one over all Reaper-authored code, and a second over the inherited ASUS/Merlin open-source code that Reaper ships — and the issues they surfaced were fixed. No critical or high-severity flaw was left open. The firmware base is unchanged (still Asuswrt-Merlin 3006.102.8); this release is about correctness and safety, not new features.
- **The web interface no longer trusts device-supplied names.** A device on your network can set its own hostname, and several admin pages displayed those names (and Wi-Fi/VPN/USB/mesh names) without neutralizing them first — so a malicious name could, in principle, run script in your browser when you opened the client list or a related page. Every one of those display points now encodes the text so it is shown, never executed — covering the dashboard and network-map client lists, the client picker used across many pages, the OpenVPN/WireGuard status pages, the AiMesh topology view, and the USB storage pages.
- **A malicious USB stick can no longer run commands as root.** The auto-mount path built a system command from a disk's volume label but allowed characters a label should never contain; a specially crafted label could have executed arbitrary commands when the stick was inserted. Labels are now restricted to safe characters.
- **Hardened the internal config database and the VPN pages against injection and overflow.** Values stored in the on-device statistics database are now escaped correctly; the VPN-profile page's fixed-size buffers are bounded to their real size; and the OpenVPN config-upload endpoint accepts only its own settings instead of any value.
- **Stronger request protection and safer defaults.** The Diagnostics and Warden "live status" tools now require the same anti-forgery token the rest of the interface uses, so another web page can't trigger them in the background. Outbound TLS made through the internal helper now verifies the server certificate against the shipped trust store and refuses rather than connect blindly. Threat-blocking now flushes the hardware flow cache so a newly blocked address is dropped immediately instead of after existing connections age out. JSON responses are served and encoded correctly.
- **Known limitations, stated plainly.** The bundled Samba is on an end-of-life branch (no reachable exploit found; a maintained-branch plan is tracked). The AiMesh config-sync and network-discovery services ship as closed vendor binaries and could not be source-audited. A full finding-by-finding status list is in the audit reports.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-31.

## v1.9.9b–c — Set every Wi-Fi band on one page, apply once
- **The Professional wireless page now shows all three radios at once.** Where the stock page let you configure one band at a time — each change forcing its own Wi-Fi restart — the Professional tab is now a single page laying 2.4, 5, and 6 GHz side by side. Set anything across all three bands and press **Apply all** once: only the settings you actually changed are written, and every radio restarts together a single time instead of once per band. Settings that don't apply to a given band are shown but disabled, so the full shape of each radio stays visible. *(The classic per-band page is retained unchanged — Region and the wireless scheduler still live there. New on-page text is English for now, with translations to follow.)*
- **SSID visibility and client isolation were kept off this page.** On this hardware the main network is served through a software-defined-network profile, so the radio-level "Hide SSID" and "AP isolation" switches only ever affected an internal interface — never the network you actually join, so toggling Hide SSID here didn't hide the SSID. Those controls stay on the General Wireless and Network pages, where they act on the real SSID.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-31.

## v1.9.9a — Wireless Diagnostics: clearer Unlock, and scanning the band you're on
- **Unlocking a channel now warns first.** Locking or unlocking a channel restarts that radio, dropping every client on it for about 20 seconds — which can look like the router has frozen. The **Unlock** button now asks for confirmation and explains the brief drop before proceeding. (Per-frequency restart isn't possible on this platform, so the radio restart is unavoidable.)
- **Auto Scan no longer stops after a single channel when you scan your own band.** Every channel the scan tests briefly restarts the radio; if your browser was on the band being scanned, that restart dropped your connection and the scan gave up after the first channel. The scan now tolerates those short reconnection gaps and works through the whole band. It is still cleanest to run a scan from a wired client or a different band.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-31.

## v1.9.9 — Wireless Diagnostics: Auto Scan & Capture made reliable
- **A stalled job no longer blocks the tools for minutes.** If a previous scan or capture ended abnormally — for example, interrupted by a Wi-Fi restart — a leftover marker could make every new Auto Scan and Targeted Capture report "busy" and leave their Start buttons disabled for up to ten minutes. The page now checks whether the earlier job is genuinely still running and clears a stale marker automatically, and a capture that can't start now shows the reason instead of silently doing nothing.
- **"Apply Best Channel" names the band you scanned.** The confirmation now shows the actual band and channel being pinned instead of always reading "6 GHz." The channel was already applied to the correct radio; the wording just made it look as though only 6 GHz was ever targeted.
- **Quad-band clarity.** On models with two 5 GHz radios, the band selectors now tell them apart instead of listing two identical "5 GHz" entries.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-31.

## v1.9.8 — Add-on menu fix, Warden persistence disclosure, change auditing, full localization pass
- **Third-party add-on menu links open correctly.** When an add-on such as scMerlin adds a "Help & Support" entry that points to an external site, the settings shell now opens it in a new browser tab instead of silently redirecting the frame to the Network Map. The same-origin iframe protection is unchanged — only genuine off-site menu links are affected.
- **Warden tells you when protection won't survive a reboot.** If Reaper Warden is enabled but `/jffs` is disabled or read-only, its threat/geo feed cache can't be saved: enforcement still runs from RAM, but there's no cross-reboot or no-internet-boot protection. The Warden page now shows a clear banner when this is the case, so the gap is visible instead of silent. (Disclosure only — by design the cache stays on internal flash, which must restore before the firewall arms.)
- **Change auditing.** Turning a Reaper feature on or off, or changing its settings, now writes a structured entry to the System Log — covering Gatekeeper (device-access changes, enable/disable, config), the Wireless channel monitor, and the Devices/Storage actions. These flow to remote syslog and the optional syslog storage dataset, giving an at-a-glance record of what changed and when.
- **Full 24-language localization pass.** The Devices, Long-Term Storage, and Warden pages — plus a handful of dashboard and QoS strings — were English-only in every language. All 219 remaining strings are now translated into the 24 supported languages; English remains selectable. (Machine-assisted; native review is still pending before public release.)
- Built + shipped on the RT-BEXXU, both variants, 2026-07-30.

## v1.9.7 — Traffic Analyzer accuracy (per-network + the router's own traffic) + dashboard client-list
- **The By-Network panel now reconciles with the live WAN chart.** With the flow accelerator on, the Traffic Analyzer only credited bytes to a network or a device when it could pair the upload and download halves of a connection — so **traffic the router itself generates** (the built-in speed test, DNS, firmware checks, the latency probe) was counted on the WAN line but dropped from every per-device and per-network view, and the By-Network total (br0) never matched the WAN chart. The collector now attributes each flow straight from its own LAN-side interface, and locally-terminated router traffic appears under a new **"Router"** row — so By-Network + Router + clients add up to the WAN line, and a client's download always lands on its network even when the return path isn't paired. Per-device client accounting is unchanged. *(This is the IPv4 path; the separate per-client IPv6 limitation is unchanged and only affects IPv6-enabled lines.)*
- **Dashboard "Clients" card.** The **View List** button now takes you to the full **Devices** page instead of a small in-place popup, and the client list grows to fill the lower part of its card instead of leaving an empty gap.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-30.

## v1.9.6 — Dashboard readability, Warden country picker, status at a glance
- **Security Posture now covers Gatekeeper and Warden.** The dashboard's Security Posture card gained rows for **Gatekeeper** (device access control) and **Reaper Warden** (threat/geo firewall), each showing enabled/off at a glance alongside the existing posture checks.
- **Warden country blocking is now a searchable checklist.** Choosing which countries to block moved from a fiddly multi-select list box to a **searchable checkbox grid** — type to filter, tick the countries you want, save. Any country codes the firmware doesn't recognize are still preserved on save.
- **USB storage shows up right after a boot.** The dashboard's USB tiles render once when the page loads, but USB drives don't mount until ~40–50 s into boot — so a freshly rebooted router showed no USB until you reloaded. The dashboard now re-polls USB status for the first ~90 s after load, so the drives and the storage ring fill in on their own.
- **Client list is easier to read.** The per-client detail text on the dashboard was small and grey; it's now larger and brighter with more card contrast.
- **System Info "Features" row reflects the real build.** The feature list now advertises Reaper's own packages — Gatekeeper, Warden, the Devices manager, unified storage, and the health watchdog — alongside the ones already listed.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.5 — First-boot: default credentials can no longer slip through
- **A factory-fresh router always forces you to set an admin username and password.** After the Reaper dashboard became the post-login landing page, a factory box could reach the interface on the default `admin`/`admin` without being sent through the forced credential-change step — the dashboard carried neither of the two enforcement paths the stock and Reaper first-boot flows rely on. Both the server-side post-login redirect and an early dashboard guard now send a default-credentials box to the first-boot setup page before anything else renders. The check only fires while the credentials are still default, so a configured or upgraded router never sees it.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.4 — Devices page: Wi-Fi clients no longer mislabeled "Wired"
- **Wired vs wireless is now decided by the bridge, not a guess.** The Devices page had been calling a client "Wired" whenever it wasn't in the Wi-Fi association list — but that list intermittently omits Wi-Fi 7 / 6 GHz / MLO stations, so real Wi-Fi clients were shown as Wired. The page now reads the LAN bridge's forwarding table to see which port (and which radio's band) a device was actually learned on, so wired and wireless — and the band — are classified correctly. It never downgrades a confirmed Wi-Fi client on a stale entry.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.3 — Devices page: Wi-Fi 7 multi-link devices shown as one
- **An MLO client is now a single device, not several.** With Wi-Fi 7 Multi-Link Operation, the driver reports each of a device's per-band links as its own address-randomized, lease-less entry, so a single laptop or phone could appear as several "Private address / No lease" rows. The Devices page now uses the driver's link-to-device mapping to fold those links into one device row showing its combined bands (e.g. "MLO · 5+6 GHz"). No effect when MLO is off.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.2 — Devices page: MLO awareness + an offline-device display fix
- **Multi-Link (Wi-Fi 7) links are labeled, not flagged as problems.** Before the full row-merge (v1.9.3), MLO clients' extra per-link addresses surfaced as alarming "Private address / No lease" rows. The page now detects when MLO is active and labels those links "MLO · <band>" with an explanatory tooltip, and stops counting them as unnamed / randomized / needs-attention.
- **Offline devices show a clean connection cell.** A never-seen or offline device printed a literal dash artifact in the Connection column (an escaping slip); it now renders correctly.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.1 — Device Identity Manager (Rung B): choose where long-term history lives
- **A Storage tab to pick where opt-in history is kept.** A new **Storage** page (under System Log) lets you select a durable location — **RAM**, **JFFS**, or a **USB** dot-directory — for the opt-in history datasets (devices, traffic, health-watch, channel-quality, syslog mirror), with per-dataset toggles and a health line. No new data store and no new background service are introduced; it simply directs the existing writers. The Traffic Analyzer's own storage selector becomes a read-only pointer to this one page, so there is a single place that controls where data is written.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.0 — Device Identity Manager (Rung A): one place for every device
- **A new "Devices" page that unifies what ASUS scatters.** ASUS keeps a device's identity across several separate places — its custom name, its DHCP reservation, its Gatekeeper access state, and its live presence (DHCP leases + address table + Wi-Fi association). The new **Devices** page (its own left-nav section, between USB Application and System Info) correlates all of them **per MAC** into one rounded view: inline rename, a pool-aware reservation ("Pin") dialog that warns when your DHCP pool is tight, a Gatekeeper state per row, an attention card for orphaned / duplicate reservations and pool exhaustion, filter chips and search, and a 24-hour traffic figure per device with a deep link to the Traffic page. Every change is a careful read-modify-write that preserves the other fields of each record — no sixth store is created — and presence is always computed from leases + address table + Wi-Fi, so it works even with Gatekeeper off. *(New page text is English-seeded across all 25 languages; translations to follow.)*
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.8.9 — WireGuard peer list: usable buttons, unclipped dialog
- **The peer-row buttons are visible again.** On **VPN Server › WireGuard**, the per-peer edit / QR / trash controls rendered as solid red rectangles — a Reaper button-recolor rule had overwritten the sprite-based icons. They are back to white glyphs on a crimson tile.
- **The peer-edit dialog no longer runs off-screen.** Expanding "More Settings for Site to Site Usage" grew the popup past its frame with no way to scroll to the rest; the dialog now refits when a section expands or collapses. *(That section's title, previously hard-coded English, is now translated.)* *(Metal-validated on hardware; the VPN pages can't be exercised in the mock.)*
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.8.8 — Warden: LAN-lockout fixes, persistence that actually works, and a new health watchdog
- **A Warden feed update can no longer lock your LAN off the internet.** A field incident traced to the scheduled threat-feed refresh: one feed (FireHOL level-1) includes private/bogon ranges (192.168/16, 127/8, …), which Warden ingested and then dropped, cutting all new LAN traffic until a power cycle. The updater now filters reserved/private ranges (IPv4 and IPv6) from every list it ingests, and the firewall chain order is rebuilt so the structural anti-lockout rules (loopback, DHCP, established connections, your allow-list, the LAN return path) always come **before** any feed or geo drop.
- **Warden's blocklist now survives a reboot.** The cache-save step had been calling `ipset save` in a way that silently wrote an empty file, so restoring on boot never actually worked; saves are now per-set and only non-empty caches are kept — so protection persists across reboots as intended. Entry validation was also tightened (bad country codes / CIDRs are rejected and logged instead of silently mangled).
- **New: `rwatch` health watchdog (on by default).** A lightweight probe runs every 5 minutes — a first-hop WAN ping (no external hosts), a loopback DNS check, a Warden "canary" that verifies your own LAN IP never matches a block set (re-applying the rules and logging a CRITICAL event if it ever does), and a check for the silent accelerator-wedge signature the stock firmware has no watchdog for. State transitions are written to the system log, and the first failure dumps bounded diagnostics to JFFS for later inspection.
- **Hardware QoS re-apply is now idempotent** — it skips a live-queue rewrite when the configuration hasn't changed, avoiding needless disruption.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.8.7 — Reaper Warden: IPv6 dual-stack + per-country block stats
- **Warden now protects IPv6 as well as IPv4.** The threat/geo firewall gained a parallel IPv6 stack — v6 threat-feed and country sets, v6 firewall chains, v6 CIDR validation, Spamhaus DROPv6 and per-country IPv6 ranges, and v6 anti-lockout for link-local / ULA / your delegated prefix. Manual block/allow entries are routed to the right family automatically.
- **New: Top blocked countries.** Each blocked country now has its own firewall rule and packet counter, so the Warden page shows a live **Blocked-hits** tile and a **Top blocked countries** card (refreshed every 30 s) — you can see which countries are actually hitting your router. The page wording was tightened, with an explicit "not a sole defense" caveat you can dismiss.
- **Full translation.** The complete Warden string set is now translated across all 24 non-English languages (was English-seeded).
- Built + shipped on the RT-BEXXU, both variants, 2026-07-28.

## v1.8.6 — Independent review of the audit remediation: clean, plus five hardening tightenings
- **Two independent adversarial code reviews — one of the v1.8.4/v1.8.5 audit fixes, one a fresh sweep of the Reaper-authored subsystems — found no live bugs, no security holes, and no performance regressions.** That is the sign-off on the whole audit-remediation arc below: the fixes landed cleanly. Each review verified every candidate against the source before reporting it, and the five low-risk, defense-in-depth items that survived are all closed here: a portability guard on the captive-portal cleanup path (so it compiles identically on every model), a belt-and-suspenders guard against a double-free on an out-of-memory error path in the traffic-history reader, a character-set gate on the LAN interface name used in the Gatekeeper teardown script (matching the guard its apply-path twin already carried), hard MAC-address validation before a device address reaches the Gatekeeper page's action buttons, and numeric emission of two Advisor status fields so a blank value can never malform the response. None was exploitable in normal use.

## v1.8.5 — Audit remediation: the low-severity batch
- **The remaining low-severity findings from the audit — 18 in all — are fixed.** These are the small robustness and hygiene items across the Reaper daemons and pages: an SNMPv3 config now refuses to emit a user with an empty passphrase (which the monitoring stack would silently reject anyway); the ping helper on the connection-diagnostics path now rejects anything but a valid host/IP before it runs; several file handles and buffers that could leak only on rare error paths are cleaned up; the captive-portal service frees all of its working memory on every exit path; the channel-quality monitor now logs its first event even in the first 15 minutes after boot; and a set of dead variables and duplicated render code in the dashboard and Traffic pages was removed. Three findings were deliberately left as-is with the reasons recorded (a duplicate default with no runtime effect, a kernel-accounting write that turned out to be load-bearing, and a no-behavior-change refactor).

## v1.8.4 — Audit remediation: the latent-issue batch
- **Twelve latent issues found by the audit are fixed** — real defects that the normal configuration doesn't trigger, closed defensively. Among them: the captive-portal config generator no longer treats a Wi-Fi network name as a text-format template; the threat/geo firewall (Warden) now keeps any stored country codes it doesn't recognize instead of dropping them when you save; the dashboard's by-band and history views guard against a malformed data response instead of blanking the page; the WAN firewall's SNMP allowance is narrowed to the single port the service actually uses; and the Advisor daemon's command runner, session-expiry check, and log redaction were tightened. None was reachable in normal use; each is now closed.

## v1.8.3 — Dashboard render fix + audit batches (Warden, redirects, i18n, build integrity)
- **Dashboard render fix.** A regression introduced with v1.8.2's new IPv6 logic (a scoping mistake) could leave the dashboard partly unrendered; the logic is moved to the correct scope and the dashboard renders fully again. The **IPv6 status icon** now also lights when the router has a working IPv6 gateway, not only a global address.
- **Warden anti-lockout + fail-safe corrections.** The threat/geo firewall's LAN anti-lockout rule was computing the wrong subnet, and its country-block updater could wipe its cached blocklist if a feed fetch failed mid-refresh. Both fixed — the updater now builds into a temporary set and only swaps it in on success (matching the threat-feed path), so a transient outage can't leave you unprotected, and the anti-lockout scope is corrected.
- **Login-redirect hardening.** Several standalone "no internet / redirecting" pages could be bounced to the admin login by the Reaper theme injector during a WAN outage — the exact moment those pages exist for. They are now excluded from injection.
- **Translation + build integrity.** A download-cap help string that gave inverted guidance in German and French was corrected; the new Warden page strings were seeded across all 24 non-English languages; and the Samba build stamp is now keyed to the patch contents, so an incremental rebuild can never ship a stale (unpatched) file server.

## v1.8.2 — Security batch: three high-impact fixes (start of the audit-remediation arc)
- **A large adversarial audit of the whole codebase drove this release and the four that follow.** An automated multi-agent audit swept every non-closed-source component — the Reaper-authored code, the shared ASUS/Merlin userspace, and the bundled third-party packages — and produced **73 verified findings**, each checked against the actual source, build config, and makefiles before it was called a defect. This release closes the three highest-impact: an IPsec configuration path where a profile name could reach a root shell, a port-forwarding field that could splice an extra rule into the firewall, and a file-read error path that freed the wrong pointer and could crash the web server. None was remotely exploitable in normal use, but each is the class of latent flaw the audit existed to find. A new IPv6 status indicator was also added to the dashboard this release (its scoping bug is fixed in v1.8.3). *(Every finding, verified, is catalogued in [`REAPER-FIXES.md`](REAPER-FIXES.md).)*

## v1.8.1 — Gatekeeper anti-lockout hardening + boot/teardown logging
- **Gatekeeper re-grandfathers your devices every time you enable it.** The grandfather-in step previously ran once; now every enable re-reads the router's full device knowledge (address table, DHCP leases, named-client list), so a device that happened to be asleep the first time can't be stranded on a later toggle.
- **More of the boot and shutdown sequence now leaves a log trail.** The LAN bring-up/teardown boundaries and Warden feed-fetch failures now write to the system log, so the several-minute boot-stabilization window and any feed problem are diagnosable from the log instead of invisible.

## v1.8.0a — Reaper Warden threat/geo firewall, a security-hardening pass, and Samba CVE backport
- **File sharing: Samba updated to 4.15.13a (backported security fix).** The SMB3 file server is
  built from Samba **4.15.13** — the last release that matches this router's compiler toolchain, and
  therefore no longer receiving upstream security updates. Rather than leave it untouched, this build
  **backports the upstream fix for CVE-2025-9640** (an uninitialized-memory disclosure in the
  `streams_xattr` module that could leak stray router memory into a file's alternate data stream) and
  marks the result **4.15.13a** (`smbd` reports `4.15.13-Reaper-a`). An audit of every Samba security
  advisory published since 4.15.13 confirmed the *rest* do not apply to this build — they're either in
  the Active-Directory/LDAP/Kerberos code that Reaper does not compile in, were introduced in a later
  Samba than 4.15.13, or depend on file-sharing options this build never enables. This one was
  backported as defense-in-depth. *(Applies to the **RT-BEXXU**, which is the model on Samba 4.)*
- **New: Reaper Warden — block malicious and by-country IP ranges at the router.** A new
  **Warden** page adds an optional, **default-OFF** firewall layer built on the kernel's `ipset`
  engine. It can automatically pull well-known **threat feeds** (known malware/botnet/attacker IP
  lists — FireHOL, Feodo, Spamhaus DROP, DShield) and refresh them on a schedule, block or allow
  **whole countries** by CIDR, and take your own **manual block / allow lists**. It has a strict
  **anti-lockout design** — your LAN, established connections, and an explicit allow-list are always
  let through *before* any drop rule — so turning it on can't strand you out of the router. Feeds
  are fetched over the router's own HTTPS and cached to JFFS so protection survives a reboot, and the
  rules **re-arm automatically** after any firewall restart or a cold boot. Optional drop-logging is
  available for auditing. *(Off until you enable it; costs nothing when unused.)*
- **Security-hardening pass (verified audit fixes).** A methodical firmware audit found and closed a
  set of latent issues in the Reaper-owned and adjacent code — all fixed and re-verified in this
  build: a format-string flaw in the network-tools handler; shell-injection hardening on the VPN
  Fusion (NordVPN/HMA) region fields, the WireGuard route path, and the Wi-Fi client-scan path; an
  out-of-bounds path check in the web server; an open-redirect guard on a login-redirect page; and
  input-sanitizing of the values spliced into the generated Gatekeeper firewall script. None were
  remotely exploitable in normal use, but each is now closed. *(Full technical detail in
  `REAPER-FIXES.md`.)*
- **Under the hood: cleaner theming and a lighter Traffic page.** The Reaper-native pages
  (Gatekeeper, Diagnostics, Wireless, Warden) no longer load the stock-page theme stylesheet that
  slightly fought their own layout, so they render cleaner. The **Traffic** page also stopped making
  a redundant second data request every refresh cycle — same information, half the polling.

## v1.7.9 — VPN page buttons restored, speed test made reliable, 2.4 GHz name fix completed
- **VPN client page: the buttons work again.** On the VPN client list ("VPN Fusion"-style page),
  the per-client controls rendered as solid **red blocks** and could not be used. Cause: a Reaper
  theme rule that recolors device icons in the Network Map "View List" was applied **site-wide**,
  and on the VPN page it painted the icon shapes into unreadable red squares. The rule is now
  scoped to the one place it was designed for, so the VPN page (and any other page using device
  icons) renders its controls normally — with the Reaper look unchanged where it belongs.
- **Internet speed test: no more first-try failures.** The built-in speed test could fail on the
  first run and then work on the second — reported across models. The test tool fetches its
  configuration from the internet exactly **once, with no retry**, so a just-booted or long-idle
  router could miss on a cold DNS lookup or a not-yet-synced clock and give up. The page now
  **retries once, silently,** before reporting an error — a real internet outage still reports
  immediately. In practice the "failed for no reason" case disappears.
- **2.4 GHz dashboard name: the remaining case.** v1.7.8 fixed the 2.4 GHz tile showing an
  internal ID when MLO reordered the network entries; field testing found one more path — when
  **2.4 GHz is excluded from MLO**, the band was dropped from the network's membership mask
  entirely, so the tile again fell back to the internal hex ID even though 2.4 GHz still
  broadcasts your network name. The dashboard now uses the network's real name for any band the
  mask misses (when a single main network exists), closing the loop.
- *Also this cycle (no firmware change):* a firmware-wide audit re-verified that the **ASUS
  cloud/remote-app tunnel is severed on every Reaper model** — reports of the ASUS app "still
  working" are local-network access only, which is expected and harmless. The teardown audit
  found no dangling references, broken shims, or dead-code hazards in the Reaper-owned surface.

## v1.7.8 — Encrypted SMB3 file sharing, SNMPv3-only, and SFTP as the secure default
- **Encrypted SMB3 file sharing (new "SMBv3" option).** The router's file-sharing service moves
  from the old Samba 3.6 (SMB2 at best) up to **Samba 4**, which speaks modern **SMB3 / SMB3.1.1**.
  A new **"SMBv3 (encrypted)"** choice on the Samba page turns on SMB3-only sharing with the
  transfer **encrypted end to end** (AES-GCM/CCM), so files copied to and from a USB drive on the
  router are no longer sent in the clear on your LAN. Current Windows, macOS, and Linux clients
  connect faster and more reliably over SMB3. *(Ships on the **RT-BEXXU** first; the other models
  stay on the older Samba for now.)*
- **SNMP is now SNMPv3-only — no more cleartext monitoring.** If you use SNMP to monitor the
  router, the insecure legacy versions (**SNMPv1 / SNMPv2c**, which send a plaintext "community
  string" password over the network) are **removed** — from both the service and the settings page.
  SNMP now requires authenticated, encrypted **SNMPv3** (default **SHA + AES**). This closes a
  common router-hygiene weakness that internet scanners actively look for.
- **SFTP is the recommended way to move files (FTP is now the deliberate legacy choice).** The
  **FTP** page gains a **"File transfer method"** selector with **SFTP pre-selected**. SFTP runs
  over the router's existing SSH service — your transfers and login are encrypted — whereas plain
  FTP is unencrypted. Picking FTP is now an explicit "I want the old, unencrypted way" decision;
  the page links you to the SSH settings (it never silently enables SSH for you). An `sftp-server`
  is bundled in the image so SFTP works out of the box once SSH is on.
- **USB dashboard: hubs no longer show "empty."** On the Reaper dashboard, plugging a **USB hub**
  into a port used to leave that port's tile reading "empty." Ports are now grouped by their
  physical slot, so a hub shows as connected and a port with several drives shows the **device
  count**.
- **2.4 GHz dashboard tile shows the right name again (with MLO on).** Turning on **MLO** could
  reorder the Wi-Fi entries so the dashboard's 2.4 GHz tile displayed a raw internal ID instead of
  the network name. The dashboard now reads all the radio entries, so each band's tile shows its
  correct SSID regardless of MLO.
- *Under the hood:* the bundled **net-snmp** was modernized (5.7.2 -> 5.9.4) for current CVE
  hygiene; SNMPv3 already worked, this is maintenance.

## v1.7.7a — GT-BE98: Wireless Log shows all four bands again (model-specific hotfix)
- **The Wireless Log page now lists every radio on the GT-BE98.** On the quad-band **GT-BE98**,
  **System Log &rsaquo; Wireless Log** was falling into the generic three-band layout, so the
  **second 5 GHz band was missing** and the **2.4 GHz radio and its connected clients were dropped**
  from the page. The GT-BE98 is now handled like its quad-band sibling (GT-AXE16000, which shares the
  same band order), so all four sections — 5 GHz, 5 GHz-2, 6 GHz, and 2.4 GHz — and their client lists
  appear correctly. *(This is a **GT-BE98-only** hotfix; the RT-BEXXU, RT-BE86U, RT-BE88U, and
  GT-BE98 Pro were not affected. The same fix is folded into the shared code for the next release of
  every model, where it is a harmless no-op on the non-quad-band units.)*

## v1.7.7 — VPN pages: no theme flash, plus a Network-Map lighting-control fix
- **No more stock-color flash on the VPN pages.** Opening **VPN &rsaquo; VPN Client** (PPTP/L2TP)
  or **VPN Server** could show the original blue ASUS styling for a split second before the Reaper
  theme took over. The nested settings panel now stays hidden over a dark background until it is
  fully themed, then fades in — so only the Reaper look is ever visible.
- **AURA/RGB lighting: no stray scrollbar.** On models with AURA/RGB lighting, the effect-scheme
  selector on the **Network Map** router panel showed an unnecessary horizontal scrollbar. That list
  already pages with its own left/right arrows, so the scrollbar has been removed. *(Affects the
  RGB-capable models; the RT-BEXXU has no AURA hardware.)*

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
- All four changes are in shared code, so every model (RT-BEXXU / RT-BE86U / RT-BE88U /
  GT-BE98 / GT-BE98 Pro) carries them; RT-BEXXU is the primary, hardware-validated build.

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
- RT-BEXXU flashed on hardware 2026-07-21 (core UI and Network Map verified). All 5 models built + shipped, both variants each
  (RT-BEXXU / GT-BE98 / GT-BE98 Pro / RT-BE86U on 2026-07-21, RT-BE88U on 2026-07-22).

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
  enumerated at most three radios (a value carried over from the tri-band RT-BEXXU), so on a
  four-radio model it hid the 4th radio and refused a channel capture on it. The ceiling is
  raised to four; it is self-configuring — a radio with no interface is skipped — so the
  RT-BEXXU still shows exactly its three. No visible change on the RT-BEXXU.

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
- Flashed to the physical RT-BEXXU 2026-07-16.

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
  access. Metal-validated on the RT-BEXXU.

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
  no functional change to the RT-BEXXU image.

## v1.5.0e — Factory-reset recovery fix + first sibling-model builds
- **Fixed the factory-reset redirect loop.** On a factory-clean box the first-run gate pages and
  Reaper's serve-time bounce redirected each other forever, so the UI never loaded and the router
  appeared bricked (recoverable only via the ASUS rescue tool). Setup/QIS pages are now excluded
  from the bounce. *Reported by tester PorscheT — credit him in the public release notes.*
- **First builds for sibling BCM4916 models.** GT-BE98 Pro, GT-BE98, and RT-BE86U (plus RT-BEXXU)
  each built in both variants — closing the "wider BE-series support" investigation.
  Sibling models: flash only with a recovery path ready. (A GT-BE98 field report is tracked in
  `BACKLOG.md`.)
- **Reproducible branch builds.** The `BEXXU-only` branch now builds cleanly from a fresh
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
  firmware, as OFL 1.1 requires. Part of the 2026-07-13 release-compliance pass.

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
- **Metal-validated** on the RT-BEXXU: the AI Advisor and its diagnostics tier verified on hardware.

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
- Single-model tree: RT-BEXXU only; all sibling BE models stripped.
