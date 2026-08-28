# Reaper — the owner's guide

> **Doc status:** current as of **v2.8.7** · 2026-08-28 <!--@stamp-->

**Applies to:** Reaper firmware, line `3006.102.8_Reaper_v<X>`, for the ASUS RT-BE96U (primary, hardware-validated) and the sibling RT-BE86U, RT-BE88U, GT-BE98, GT-BE98 Pro, and the newer RT-BE92U (BCM6765, experimental). This guide describes the feature set as of the v2.8.7 <!--@treever--> source tree. The newest *published* release may be behind that; where a feature is newer than the image you are running, the page simply will not be there yet. See [`CHANGELOG.md`](CHANGELOG.md) for what each version added and [`BACKLOG.md`](BACKLOG.md) for what is still pending confirmation.

Reaper is based on **Asuswrt-Merlin by Eric "Merlin" Sauvageau**. Every line of Reaper is a patch on top of that work; the base firmware, most of its features, and most of what is good about the result are his. Reaper is an independent fork. Neither ASUS nor the Asuswrt-Merlin project has reviewed, approved or endorsed it, and neither should be contacted about it (see [Where to report issues](#214-where-to-report-issues)).

This guide is written for someone who will install and run the firmware: technically literate, not a developer. Everything in it comes from the project's own documentation, changelog, backlog and the text on the pages themselves. Where the project itself says something is not yet confirmed on hardware, this guide says so too.

---

## Contents

1. [What Reaper is, and is not](#1-what-reaper-is-and-is-not)
   - 1.1 [What it keeps](#11-what-it-keeps)
   - 1.2 [What it removes](#12-what-it-removes)
   - 1.3 [What it adds](#13-what-it-adds)
   - 1.4 [The two builds: Standard (noMCP) and AI Advisor (MCP)](#14-the-two-builds-standard-nomcp-and-ai-advisor-mcp)
   - 1.5 [The closed Broadcom parts](#15-the-closed-broadcom-parts)
2. [Requirements and rules for running it properly](#2-requirements-and-rules-for-running-it-properly)
   - 2.1 [Supported models and the right file](#21-supported-models-and-the-right-file)
   - 2.2 [Flashing from stock ASUS or from Merlin](#22-flashing-from-stock-asus-or-from-merlin)
   - 2.3 [The first-boot credential step](#23-the-first-boot-credential-step)
   - 2.4 [The internal /jffs partition: where Reaper keeps its lists](#24-the-internal-jffs-partition-where-reaper-keeps-its-lists)
   - 2.5 [Two backups, not one](#25-two-backups-not-one)
   - 2.6 [A USB disk for the long-term store](#26-a-usb-disk-for-the-long-term-store)
   - 2.7 [Apply and Keep: commit-confirm and the auto-revert timer](#27-apply-and-keep-commit-confirm-and-the-auto-revert-timer)
   - 2.8 [MLO needs a cold power cycle](#28-mlo-needs-a-cold-power-cycle)
   - 2.9 [Custom scripts and Reaper's firewall chains](#29-custom-scripts-and-reapers-firewall-chains)
   - 2.10 [The diagnostics report and how to share it safely](#210-the-diagnostics-report-and-how-to-share-it-safely)
   - 2.11 [The firmware update check](#211-the-firmware-update-check)
   - 2.12 [Reading the system log](#212-reading-the-system-log)
   - 2.13 [Keep management off the WAN](#213-keep-management-off-the-wan)
   - 2.14 [Where to report issues](#214-where-to-report-issues)
3. [The dashboard and navigation](#3-the-dashboard-and-navigation)
4. [Each feature page](#4-each-feature-page)
   - 4.1 [Firewall](#41-firewall)
     - 4.1.1 [Status](#411-status)
     - 4.1.2 [General](#412-general)
     - 4.1.3 [Rules](#413-rules)
     - 4.1.4 [Objects](#414-objects)
     - 4.1.5 [Zones](#415-zones)
     - 4.1.6 [Egress](#416-egress)
     - 4.1.7 [Forwards](#417-forwards)
     - 4.1.8 [Network Services](#418-network-services)
     - 4.1.9 [URL Filter](#419-url-filter)
     - 4.1.10 [Keyword Filter](#4110-keyword-filter)
     - 4.1.11 [Logging](#4111-logging)
     - 4.1.12 [Limits, and things deliberately not built](#4112-limits-and-things-deliberately-not-built)
   - 4.2 [Gatekeeper](#42-gatekeeper)
     - 4.2.1 [The four states](#421-the-four-states)
     - 4.2.2 [Turning it on safely](#422-turning-it-on-safely)
     - 4.2.3 [How it enforces, and the way back in](#423-how-it-enforces-and-the-way-back-in)
     - 4.2.4 [Internet-only, and the LAN DNS trap](#424-internet-only-and-the-lan-dns-trap)
     - 4.2.5 [Guest networks](#425-guest-networks)
     - 4.2.6 [Reading the status](#426-reading-the-status)
     - 4.2.7 [Examples](#427-examples)
     - 4.2.8 [Limits and gotchas](#428-limits-and-gotchas)
   - 4.3 [Warden](#43-warden)
     - 4.3.1 [Setting it up](#431-setting-it-up)
     - 4.3.2 [The order it decides in](#432-the-order-it-decides-in)
     - 4.3.3 [Threat feeds](#433-threat-feeds)
     - 4.3.4 [Countries](#434-countries)
     - 4.3.5 [Your own lists](#435-your-own-lists)
     - 4.3.6 [Direction, and filtering the router itself](#436-direction-and-filtering-the-router-itself)
     - 4.3.7 [Reading the statistics](#437-reading-the-statistics)
     - 4.3.8 [Examples](#438-examples)
     - 4.3.9 [Limits and gotchas](#439-limits-and-gotchas)
   - 4.4 [Policy Routing](#44-policy-routing)
     - 4.4.1 [How it works](#441-how-it-works)
     - 4.4.2 [The page](#442-the-page)
     - 4.4.3 [What a rule matches](#443-what-a-rule-matches)
     - 4.4.4 [Domain lists](#444-domain-lists)
     - 4.4.5 [Where a rule sends traffic](#445-where-a-rule-sends-traffic)
     - 4.4.6 [Order and precedence](#446-order-and-precedence)
     - 4.4.7 [Fail-closed](#447-fail-closed)
     - 4.4.8 [Examples](#448-examples)
     - 4.4.9 [Limits and gotchas](#449-limits-and-gotchas)
   - 4.5 [QoS (Traffic Manager)](#45-qos-traffic-manager)
     - 4.5.1 [Choosing a mode](#451-choosing-a-mode)
     - 4.5.2 [Getting the bandwidth numbers right](#452-getting-the-bandwidth-numbers-right)
     - 4.5.3 [Setting up the classful engine](#453-setting-up-the-classful-engine)
     - 4.5.4 [Priority and ceilings: the two knobs](#454-priority-and-ceilings-the-two-knobs)
     - 4.5.5 [Classification rules](#455-classification-rules)
     - 4.5.6 [Why download is different](#456-why-download-is-different)
     - 4.5.7 [Verifying it works](#457-verifying-it-works)
     - 4.5.8 [Examples](#458-examples)
     - 4.5.9 [Limits and gotchas](#459-limits-and-gotchas)
   - 4.6 [QoS Diagnostics](#46-qos-diagnostics)
   - 4.7 [Traffic Analyzer](#47-traffic-analyzer)
     - 4.7.1 [Turning it on, and where history lives](#471-turning-it-on-and-where-history-lives)
     - 4.7.2 [The windows](#472-the-windows)
     - 4.7.3 [How per-device numbers are counted](#473-how-per-device-numbers-are-counted)
     - 4.7.4 [Examples](#474-examples)
     - 4.7.5 [Limits and gotchas](#475-limits-and-gotchas)
   - 4.8 [Devices](#48-devices)
     - 4.8.1 [Naming](#481-naming)
     - 4.8.2 [Pinning an address](#482-pinning-an-address)
     - 4.8.3 [The Network Ledger](#483-the-network-ledger)
     - 4.8.4 [What the connection column tells you](#484-what-the-connection-column-tells-you)
     - 4.8.5 [Filtering and export](#485-filtering-and-export)
     - 4.8.6 [Limits and gotchas](#486-limits-and-gotchas)
   - 4.9 [Connections](#49-connections)
   - 4.10 [Wireless Quality and WiFi Professional (all bands)](#410-wireless-quality-and-wifi-professional-all-bands)
   - 4.11 [Long-Term Storage, Data Export and the Reaper settings backup](#411-long-term-storage-data-export-and-the-reaper-settings-backup)
   - 4.12 [USB Disks](#412-usb-disks)
   - 4.13 [Diagnostics](#413-diagnostics)
   - 4.14 [Firmware](#414-firmware)
   - 4.15 [About](#415-about)
   - 4.16 [AI Advisor (MCP build only)](#416-ai-advisor-mcp-build-only)
   - 4.17 [Tools → Other Settings: the Reaper switches](#417-tools--other-settings-the-reaper-switches)
5. [Efficiency and good practice](#5-efficiency-and-good-practice)
6. [Troubleshooting quick table](#6-troubleshooting-quick-table)
7. [Glossary](#7-glossary)
8. [Factory defaults, and what Reaper changes](#8-factory-defaults-and-what-reaper-changes)
   - 8.1 [Stock settings whose default Reaper changes](#81-stock-settings-whose-default-reaper-changes)
   - 8.2 [Reaper's own settings and their defaults](#82-reapers-own-settings-and-their-defaults)
   - 8.3 [What a factory reset actually restores](#83-what-a-factory-reset-actually-restores)
9. [Present but inactive](#9-present-but-inactive)
   - 9.1 [The stock firmware-update page](#91-the-stock-firmware-update-page)
   - 9.2 [The AiProtection pages](#92-the-aiprotection-pages)
   - 9.3 [Why they were not simply deleted](#93-why-they-were-not-simply-deleted)

---

## 1. What Reaper is, and is not

Reaper is a security-hardened, de-clouded rebuild of Asuswrt-Merlin 3006.102.8 for the ASUS RT-BE series (Broadcom BCM4916 — or BCM6765 on the RT-BE92U — Wi-Fi 7). Its stated goal is that **only physical access** should be able to compromise the router: the open-source userspace has been audited and patched against remotely or LAN-reachable command injection, buffer overflows, format-string bugs and authentication bypasses, across several audit rounds. That hardening is invisible in normal use. What you will notice is the de-cloud work (the router no longer talks to ASUS), the different interface, and the features listed below.

Reaper is distributed as a patch series applied to the public Asuswrt-Merlin source. Releases are compiled in a public GitHub Actions clean room from pinned inputs, and the About page in the firmware states the patch count, upstream commit and build date of the image you are running so that it can be rebuilt and checked.

### 1.1 What it keeps

- **Everything Asuswrt-Merlin ships** for this platform that is not cloud-coupled: user scripts (firewall/services events), cron, custom service configs, Entware via `amtm`, `nano`, NTP, SNMP (SNMPv3 only, see below), OpenVPN client and server, WireGuard, IPsec/strongSwan (built and staged from v2.5.3 onward; the server side is confirmed on hardware, a client tunnel is still owed confirmation), VPN Director, DNS Director, Cake SQM, Tor, ipset, USB sharing (Samba 4 SMB3, vsftpd, minidlna, AFP), traffic statistics.
- **AiMesh.** It has been retained because no suitable open-source replacement is known, and replacing it would require a compatible implementation on every mesh node. The AiMesh config-sync and discovery services ship as closed vendor binaries and could not be source-audited.
- **The closed Broadcom blobs**, unmodified (see 1.5).

### 1.2 What it removes

- **The first-boot QIS wizard's EULA and privacy-consent screens** and the Advanced privacy page. The AiMesh add-node wizard is kept.
- **Phone-home.** The ASUS AWS-IoT cloud connector and account binding, the AAE/AiHome cloud tunnel, AiCloud/WebDAV, the AiDisk cloud-share wizard, the stock privacy-policy check, the stock "Security Update" (Trend Micro signature) panel, and every browser-side callback to ASUS servers — device and app icons, the FAQ index, DNS-provider and ISP lists, the Open NAT game database, timezone tables and so on. The build now fails if an ASUS CDN reference reaches the shipped web root, so this cannot silently creep back. Nothing in the web interface contacts ASUS any more; the only outbound check the firmware makes on its own is the opt-in firmware check, and that goes to the Reaper GitHub release channel.
- **Adaptive QoS / Trend Micro DPI.** AiProtection, DPI-based Adaptive QoS and the web-history feature are gone with the engine that powered them. Reaper's own hardware QoS and Traffic Analyzer take their place.
- **Alexa / Google Assistant** integration, the Download Master advert, the stock Network Map page (its device list and per-device detail now live on the dashboard and the Devices page), the Open NAT menu entry (it was port forwarding, which is still there), and the legacy SNMPv1/v2c protocols (SNMPv3 with SHA + AES is the only option).
- **No packet-capture page is bundled.** If you want `tcpdump`, install it through Entware on a USB stick.

### 1.3 What it adds

In short: two hardware QoS engines that keep the flow accelerator on, a native Traffic Analyzer, a native firewall rules engine, Gatekeeper device access control, Warden threat and country blocking, Policy Routing, a Device Identity Manager, a live Connections explorer, wireless channel diagnostics, a one-click sanitized diagnostics report, a native firmware page with a verified one-click update, long-term storage with analytics export, and (in one of the two builds) a read-only LAN-only AI Advisor. Each gets its own section in part 4.

Secure factory defaults: WPS is off, UPnP is off, the scheduled firmware check is off, and remote web admin, SSH, Telnet, WAN ping, FTP, DLNA, DDNS, guest networks, SNMP, custom-script execution, remote logging and IPv6 all default off. Reaper also adds an idle auto-logout of 15 minutes on the admin session.

### 1.4 The two builds: Standard (noMCP) and AI Advisor (MCP)

Every model ships in two variants:

| Variant | File name contains | What is different |
|---|---|---|
| **Standard** | `noMCP` | The AI Advisor / MCP server is **not compiled in at all** — no daemon, no page, no menu entry, no settings. This is not a disabled feature; the code is absent. |
| **AI Advisor** | `_MCP` | Adds the optional, read-only, LAN-only MCP server. It is **off by default and never started at boot**; it runs only after you arm it for a timed session. |

The noMCP build is the right choice if you never want the MCP feature present. The MCP build is safe to run without ever enabling it. Pick one; the firmware page refuses to install an image of the other variant over the top (you can still switch deliberately with a manual upload, accepting the warning).

### 1.5 The closed Broadcom parts

The Wi-Fi drivers and a set of prebuilt objects (`wl`/`dhd`, `eapd`, `acsd`, `networkmap`, `wlceventd`, `cfg_mnt`, the Broadcom `hostapd`/`wpa_supplicant` forks, `libnvram`, `libtmctl`, the rdpa driver) are proprietary, are licensed for genuine ASUS hardware only, and are never modified. Reaper hardens the userspace around them. Some defects live inside them and can only be worked around, not fixed:

- The **"settings will not save" freeze** in `libnvram.so` (worked around by the socket bind shim, on by default — see 4.17).
- **Weighted (WRR) QoS classes** cannot be created on the Ethernet egress scheduler; every class runs strict priority. The UI no longer offers the weight control.
- On the **GT-BE98**, a Guest Network Pro network with AP isolation combined with a manual WAN VLAN can stop the 2.5 Gbps-1 LAN port passing untagged main-LAN traffic. There is no userspace interface to correct the switch programming. Workarounds: keep Guest Pro off that port, move the device, or tag it with the guest VLAN.
- A known over-the-air **5 GHz denial-of-service** in the Broadcom radio software (a malformed frame can drop the 5 GHz radio until reboot) cannot be patched from this firmware.

---

## 2. Requirements and rules for running it properly

This section is the one to read before you flash and again after you have been running for a week. Several of Reaper's features store their state differently from stock firmware, and two of them deliberately undo your changes unless you confirm them. Knowing that in advance saves a lot of confusion.

### 2.1 Supported models and the right file

- **RT-BE96U** — primary model; every release is built and validated on this hardware.
- **RT-BE86U, RT-BE88U, GT-BE98, GT-BE98 Pro** — built from per-model branches of the same tree, from the same patch series. Each is published with both variants. On-metal validation of each release on the four siblings is owed and is done by field testers; the project is honest that the primary model gets tested first.
- **RT-BE92U** (BCM6765 / 96765GW) — a newer sixth model, brought up in the v2.7.x line. Its source rides the same rungs and it ships as **experimental prereleases**. It is in the clean-room CI matrix and in the `all` fleet fan-out, but because it publishes as a prerelease it never lands as a standard release alongside the five BCM4916 models.

**Flash only the image built for your exact model.** Cross-flashing between models can brick the router. The release assets for each model are:

| File | What it is |
|---|---|
| `<MODEL>_3006_102.8_<build>_nand_squashfs.pkgtb` | The AI Advisor (MCP) firmware you flash. |
| `<MODEL>_..._noMCP_...pkgtb` | The Standard firmware without the Advisor. |
| `..._loader.pkgtb` | A recovery loader for rescue mode only. Do not flash it as your firmware from the web interface. |
| `SHA256SUMS` | Checksums. Verify the download before flashing; a truncated image is a common cause of a failed flash. |

Images are hosted on the project's GitHub Releases page (also mirrored in-tree under `releases/`). The project asks that images be obtained from there rather than re-hosted copies: the compiled image bundles proprietary components with no redistribution grant, and the release channel is what the router's update check verifies against.

### 2.2 Flashing from stock ASUS or from Merlin

Before you start, every time:

1. **Save your current configuration** (Administration → Restore/Save/Upload Setting → Save) and keep the `.cfg` off the router.
2. **Download the stock ASUS firmware for your exact model** and keep it next to the Reaper image. It is your rollback and your rescue image.
3. Be on a reasonably recent stock or Merlin firmware first, to avoid nvram and bootloader-format mismatches.
4. **Use a wired connection.** Never flash over Wi-Fi.
5. Do not lose power during the flash. A failed *firmware* write is recoverable through rescue mode; an interrupted *bootloader* write generally is not.
6. Note your admin password and LAN IP; plan on a factory reset afterwards.

Then:

1. Log in, go to **Administration → Firmware Upgrade**, choose **Manual upload**, pick the `_nand_squashfs.pkgtb` (Standard or MCP — not the `_loader`), and let it flash. The router reboots on its own; allow several minutes.
2. **The first non-stock flash may need** `nvram set DOWNGRADE_CHECK_PASS=1` over SSH first. If the upload is refused, that is why.
3. After the first successful boot, a **factory reset is recommended** when coming from much older firmware, another third-party firmware, stock-with-VPN, or across a major version. Do **not** reload an old settings backup across a reset; reconfigure by hand (or restore only if the versions are close).
4. Verify: the firmware version on the Administration/About page reads `…_Reaper_v<X>`, the System Info "Features" row lists the Reaper packages, and internet and Wi-Fi work.

**Rolling back to stock** is the same operation with the stock ASUS `.pkgtb`, followed by a factory reset. There is no cloud or account tie-in to undo. If the web interface is unreachable, use ASUS rescue mode (Firmware Restoration utility or TFTP) with the stock image.

The project's install guide ([`INSTALL-AND-ROLLBACK.md`](INSTALL-AND-ROLLBACK.md)) marks the following as **not yet bench-confirmed on this hardware**: which button enters rescue mode (Reset or WPS) and the LED sequence, which image the rescue flow expects, whether a usable second image partition exists, and whether any anti-rollback gate blocks a downgrade to an older stock build. The Firmware page's own note says the previous firmware remains in the standby partition and that bootloader rescue mode can always reflash over Ethernet; do not rely on an automatic A/B failover.

**AiMesh nodes.** A router that you intend to add as a *new* Reaper node must be factory-reset on this firmware to become discoverable. A mesh that was already built under stock or Merlin and then flashed to Reaper is unaffected. Nodes can be updated from the main router's Firmware page (see 4.14). Reaper's theming stands aside entirely on a node, which is what fixed the blank-page loop some node owners saw in earlier versions.

### 2.3 The first-boot credential step

On a factory-fresh or factory-reset router, the web server itself forces you through Reaper's **First-time setup** page before any other page is reachable, and it cannot be bypassed by typing another page's address:

1. Choose your **language** at the top of the card. The choice carries through to the rest of the interface.
2. Set a **router username** (letters, numbers, `-` and `_`; you may keep `admin` if the password is strong) and a **password** (5–32 characters; it must differ from the username and from the factory default; `admin` is rejected as a password).
3. You are then taken to **Set your Wi-Fi password**: the wireless network is still on its factory key until you change it. The wizard will not release you until both steps are done.

The gate only ever triggers on a genuinely unconfigured router — an upgrade of a configured router never sees it — and it does not apply in repeater or media-bridge modes, nor to AiMesh node onboarding. Earlier versions had a refresh-loop and a "rejects everything" failure at this step; both are fixed (v2.1.5, v2.2.0), and the page now self-recovers if a submit was applied but the confirmation did not reach the browser. If you are ever genuinely stuck, `nvram set reaper_fbdone=1` over SSH releases the interface. While the password is still the factory default the change form has no credential gate by design, so it carries the anti-forgery token instead; this is pending one clean factory-reset confirmation in the backlog.

### 2.4 The internal /jffs partition: where Reaper keeps its lists

This is the single most important thing to understand about running Reaper after v2.6.3.

**Background.** On this platform the kernel's nvram store silently refuses any value over 1 KB. No error reaches the caller; the save simply does not happen. That is what stopped Gatekeeper holding more than 45 devices, capped the Policy Routing list at about 15 rules, and refused a 40-domain firewall object. The stock mechanism for keeping big lists out of that limit is a fixed whitelist inside a closed library that Reaper cannot add to.

**What changed.** Reaper's lists now live as plain files on the router's internal flash partition, `/jffs`:

| Feature | Where it lives | Since |
|---|---|---|
| Gatekeeper device list | `/jffs/gatekeeper/rl` | v2.6.3 |
| Policy Routing rule list (the confirmed snapshot) | `/jffs/reaper_pbr/lastgood/` | v2.6.7 |
| Firewall engine lists (objects, groups, services, zones, zone policies, rules, egress defaults, forwards) | `/jffs/reaper_fw/lastgood/` | v2.6.9 |
| Warden feed cache and block counters | `/jffs` (locked there by design; it must restore before the firewall arms, earlier than any USB mount) | v1.8.0 |
| Saved domain-list members (replayed at boot) | `/jffs` | v2.5.9 |

An existing list is migrated once, automatically, at the first boot on a firmware that moved it, and the migration is logged (for example `gatekeeper: device list migrated from nvram to /jffs/gatekeeper/rl`). The ceilings are gone: Gatekeeper is tested to 300 devices and its tables are sized for 512; twenty-plus routing rules and 40-domain objects save and survive a reboot. The lists' own limits (8 KB per firewall list, about 1,900 characters per domain object, 64 addresses per routing rule) are now the real ones.

**What that means for you:**

- `/jffs` is **always mounted**. The "Enable JFFS custom scripts and configs" switch on the Administration page controls only whether `/jffs/scripts` and `/jffs/configs` are honoured; it does not control whether Reaper can use the partition.
- Reaper uses **well under 4 MB** of it. The diagnostics report (v1.3.4) prints the partition's size, free space, read-only state, a write test and the space Reaper's stores use, and raises a FINDING if the partition is unmounted, read-only, nearly full or unwritable — the cases in which Reaper changes would stop persisting. Warden also shows a banner on its page if `/jffs` is off or read-only.
- **A factory reset, and "Format JFFS partition at next boot", erase all of these lists.** For Gatekeeper that is the correct default-deny outcome (nothing is approved after a reset); for the rest it means your rules are gone. **Export first** — see 2.5.
- **The stock settings backup does not contain them** (it is an nvram export). Again: export first.
- Approving or removing a Gatekeeper device no longer forces a full nvram commit per click, so those actions are quicker than they were.
- The v2.6.x/v2.7.0 migrations are recent. The expected evidence after upgrading is one migration line per feature in the system log, and a list that is still there after a reboot; anything still open about them is in [`BACKLOG.md`](BACKLOG.md).

### 2.5 Two backups, not one

| Backup | Where | What it contains | What it does not |
|---|---|---|---|
| **Stock settings backup** | Administration → Restore/Save/Upload Setting | nvram: every stock setting, plus Reaper's switches, QoS configuration, storage choices, and so on. | The Reaper lists on `/jffs` (2.4). Device names and reservations *are* in nvram, so they are included. |
| **Reaper settings backup** (v2.7.0) | Storage page → *Reaper settings backup* card → **Export settings** | One JSON file, `reaper-settings-<model>-<version>-<date>.json`: Gatekeeper (switches and the device list), Policy Routing (switch and rules), the Firewall engine (switches and all eight lists) and Warden (countries, feeds, ban/allow lists). | Stock settings. |
| **Full backup** (`.rbk`, v2.7.2) | Administration → Restore/Save/Upload Setting → *Reaper full backup* card | **One file** carrying the stock settings (in the stock `.CFG` format, still restorable by stock/Merlin), the Reaper settings above, and the firewall's resolved domain-set cache — so a reset-and-restore keeps every Reaper store in a single archive. | — (this is the everything-in-one option). |

The one-file **`.rbk` full backup** (v2.7.2) is the simplest option and the one to reach for before a factory reset: it wraps the stock settings and every Reaper store together, checks the archive matches this router model and that `/jffs` is healthy before touching anything, restores the stock settings and reboots, and one click after you log back in completes the Reaper half (firewall and routing lists are staged as drafts to **Apply** then **Keep**). Otherwise, take both of the separate backups above, and take the Reaper one again after any significant change to those four features. Either Reaper file **contains your device addresses and your domain lists** — keep it with your other private backups.

**Import** replays the file through each feature's own save path, so it faces exactly the same validation as typing the values in. Gatekeeper and Warden take effect at once. The Firewall and Policy Routing lists are loaded as **drafts**: open each page, **Apply**, then **Keep** — so a restored rule that cuts off your own access still reverts on its own (2.7). Nothing is written to `/jffs/configs`. The page reports `Imported: N setting(s), M list(s), K rejected`. The round trip is believed to work and is pending on-metal confirmation.

### 2.6 A USB disk for the long-term store

Live data — the traffic graphs, device presence, channel quality — is kept in RAM and resets at reboot. If you want history over long spans, you choose a **durable location** on the Long-Term Storage page (System Log → Long-Term Storage): **RAM only**, **Internal (JFFS)**, or **USB storage**, per dataset. The datasets are device history and the action audit trail, Traffic Analyzer history, watchdog (`rwatch`) incident dumps, channel-quality history, and a syslog mirror. Warden's cache is locked to JFFS regardless. Connection-health history for analytics export lands in the same location.

A USB disk is the right place for anything that grows: it has the most space and no flash-wear concern, so the Traffic Analyzer saves to it every 15 minutes (JFFS stays hourly to protect the router's NAND). History is written under `/.reaper/` on the volume with restricted permissions, but anyone with file-share access to that volume can read it — it maps every device with timestamps — so prefer JFFS if the share is open to untrusted users. Writes are batched and low-priority; pulling the stick loses history, never policy or performance.

**Which filesystem.** Format from the USB Disks page (4.12):

- **ext4 — recommended** for a disk that stays on the router: journaled, fast, large files. Not readable by Windows or macOS without extra software.
- **ext3 / ext2** — older Linux formats; pick ext4 unless something you own needs these.
- **FAT32** — readable everywhere, but **no file larger than 4 GB and no journal**; use it for a disk you move between devices, not for the store.
- **NTFS / HFS+** — available; formatting these from the Reaper page had never worked before v2.6.8 (the disk came back untouched). Fixed, pending confirmation.

The ext4/ext3/ext2 options arrived in v2.6.8 and are also pending a round trip on a spare stick. The USB health scan runs a real `e2fsck` on ext4.

**Timing.** USB drives mount roughly 40–50 seconds into boot. The Traffic collector waits for the store to appear (retrying for up to 15 minutes), restores the saved history, and never overwrites a database it did not first load; it also parks itself if the store vanishes during a firmware flash and re-attaches when it returns. The dashboard re-polls USB status for the first 90 seconds after load so the tiles fill in on their own.

One field report (Traffic Analyzer "1 year" totals sticking for IPv6 devices) looked like a USB-store issue that cleared when the reporter moved the store to JFFS; it is being watched.

### 2.7 Apply and Keep: commit-confirm and the auto-revert timer

Two pages deliberately undo your changes unless you confirm them: the **Firewall** page (its Rules, Egress and Forwards tabs — the Reaper engine) and the **Policy Routing** page (from v2.6.7).

How it works:

1. You press **Apply**. The change goes live **immediately**.
2. A card appears: *A change is waiting for your confirmation — Reverting in N seconds*, with **Keep these changes** and **Revert now**.
3. If you do not press **Keep** before the timer ends, the router puts the previous ruleset back **by itself**.

Why you must press Keep: this is what stops a bad rule locking you out. The rollback is armed *before* the new rules go on, is driven by a scheduled task rather than the web server, and runs from a pre-written script — so it still fires if the thing you just broke is the web interface, or your browser, or your session. **Closing the tab does not cancel it.** As a last resort it removes Reaper's own rules and leaves the stock firewall in charge. A protective set of rules is always applied first, including the IPv6 neighbour-discovery traffic a network stops working without.

The **auto-revert timer** is set on the Firewall page (Rules tab): default **60 seconds**, clamped to **15–3600**. It can be lengthened but never switched off — a value of 0 is promoted. The same timer governs Policy Routing.

Three consequences worth knowing:

- **A change still awaiting confirmation at a reboot boots the last confirmed rules**, not the pending ones (v2.5.0 closed a hole where an unrelated save could have carried a pending rule across a reboot).
- On Policy Routing, **Keep is the only thing that writes flash**; the confirmed list is the snapshot on `/jffs`.
- Test from a device that is **not** itself affected by the rule you are testing, so that the browser you are using is not the thing that gets cut off while you look for the Keep button.

The Firewall page's other tabs (General, Network Services, URL Filter, Keyword Filter) are the long-standing Asuswrt controls and apply straight away with no countdown. The Firewall Status tab tells you what is actually live; what you configured and what is live can differ while a restart is in flight or if a ruleset failed to build.

### 2.8 MLO needs a cold power cycle

Enabling or disabling Wi-Fi 7 Multi-Link Operation (the MLO switch) needs a **full power cycle** — unplug the router, wait, plug it back in — not a software reboot, for the change to settle. If MLO appears to have half-applied (clients seeing one band only, the dashboard's MLO row reading *Partial*), power-cycle before investigating anything else. *(This rule comes from the project's working notes rather than the changelog; it is recorded here because it is a common cause of confusion.)*

### 2.9 Custom scripts and Reaper's firewall chains

Merlin's user scripts (`firewall-start`, `nat-start`, `services-start` and the rest) and Entware add-ons all keep working. But be aware of how Reaper's own layers are built, so that a script does not fight them:

- Since v2.6.2, every Reaper firewall layer registers into **one shared front chain per base chain** (`REAPER_HOOK_*`, at position 1 of INPUT/FORWARD/OUTPUT), in a **fixed order: Warden → Gatekeeper → rules engine** — every deny-only layer before the one that can accept. A single script rebuilds that order after any layer applies, so it converges whichever service restarted.
- Gatekeeper and Warden **self-heal**: Gatekeeper repairs a lost hook within about 30 seconds and re-applies when a bridge appears without one; Warden re-arms after any firewall restart; the `rwatch` watchdog re-applies Policy Routing mark rules if the live chain is short of what it meant to load.

So a script that inserts its own rules at the top of INPUT or FORWARD, or flushes those chains, will either be undone within seconds or will change the layer order — and an `ACCEPT` placed above Reaper's hook lets traffic past Warden and Gatekeeper entirely, which is exactly the defect v2.6.2 fixed inside Reaper. Put script rules *after* Reaper's hook, or use the Firewall page's Rules tab, which was built for this. Scripts that loop calling bare `nvram get` should also be avoided: the closed nvram library can hang a reader forever (4.17); Reaper's own generated scripts read through a five-second guard and `rwatch` reaps any `nvram` process older than two minutes, but a hung reader in your script still holds whatever lock your script took. Scripts that read kernel accelerator files on a timer are another thing to avoid; the project shelved its own accelerator probe after it caused reboot loops in the field.

The diagnostics report lists "an old direct firewall hook left over or the shared front chain missing" as a FINDING, which will catch most script conflicts.

### 2.10 The diagnostics report and how to share it safely

**Administration → Diagnostics** has one button: **Download Report**. It gathers in one pass what a network engineer would collect by hand — model and firmware identity, uptime and memory, each radio's channel, width, signal health and client counts, wired port link states and speeds, hardware-acceleration and QoS readings, DHCP lease count, running services and open ports, recent kernel and system log excerpts — and, since v1.3.0 of the report, a **FINDINGS** block at the top, syslog history over the live log *and* the `rwatch` mirror (days, not hours), process health, the state of every Reaper layer, the data plane, nvram hygiene, a network inventory, and `/jffs` health. It takes roughly 20–30 seconds; the web server is blocked while it runs, so do not navigate away. The same collector is available over SSH as `reaper_diag`.

**What the report masks.** The whole document passes through a redaction engine before a byte is written:

- Passwords, Wi-Fi keys and tokens are **never collected** — the report only notes SET or EMPTY.
- Every **MAC address** becomes a consistent pseudonym (`MAC-3` and so on), including MACs written without colons.
- **Usernames, device names, hostnames** (including guest-network lease hostnames) and **Wi-Fi network names** become tokens.
- **Your public IPv4 address and all IPv6 addresses** are masked. **E-mail addresses** are redacted wherever they appear (from v2.4.6).
- **Local-only addresses** (192.168.x.x) are kept — they identify nothing outside your own network.
- Pseudonyms stay consistent inside one report, so a device can be followed across sections without revealing which device it is; a new report gets a new set.
- The report opens with a **ledger** counting exactly what was withheld, and the finished file is **re-scanned** for anything that still looks like a public address, a hardware address or an e-mail, and marked either clean or "review before sharing" (counts only — printing what it found would put the leak into the file).
- WireGuard appears as **peer counts only**.

It is plain text. **Open it and read it before you share it.** The router never transmits it anywhere; the file downloads to your browser. It is the right thing to attach to a bug report. The Devices page's **Export list** is the opposite — deliberately unsanitised, with real names, MACs and IPs — and is not safe to post anywhere.

### 2.11 The firmware update check

- The scheduled check is **off by default** and is switched on from the Firmware page (**Scheduled Check**). It is notify-only: a crimson "New firmware available" banner on the dashboard and the release notes on the Firmware page. Nothing is ever downloaded or installed automatically.
- It reads a **Reaper-published manifest on GitHub** — never ASUS, never the stock Merlin endpoint — and knows your model *and* variant, so it never offers the wrong image.
- You can choose the **hour** of the nightly check (leave it on *Automatic (overnight)* for the old 2–6 am behaviour). The **minute is random on purpose**, so every router that kept the default does not hit the release channel in the same second.
- **Check for Update** on the page is user-initiated and goes to the same channel.
- **Download and Install** (one click) verifies the manifest's SHA-256 and size, refuses any download URL outside the Reaper release channel, re-checks the image is for this exact model and variant, runs the platform's own image check, and only then flashes. If any step fails the download is discarded and nothing is written. A manifest without checksums downgrades the page to notify-only.

### 2.12 Reading the system log

Read it on the **System Log** page, or over SSH as the file `/tmp/syslog.log`. **`logread` returns nothing on this platform** (the log is written to a file, not the in-memory buffer). If you have a USB or JFFS store with the syslog mirror enabled, the mirror holds days of history; the diagnostics report reads both.

Reaper's own tags in the log: `reaper_fw` (firewall engine), `reaper_pbr` (Policy Routing), `gatekeeper` / `gkd`, `rwarden` and `REAPER-WARDEN` / `REAPER-WARDEN-SELF` (Warden and its drop lines), `rwatch` (the health watchdog), `reaper_cfg` (settings import/export), `reaper-nv` (a killed hung nvram reader), `hwqos` (QoS queue programming), `disk_format` (USB formatting; its log is also at `/tmp/disk_format/<dev>.log`), `aimesh:` (node-search drop reasons), `IGD desc` (UPnP description served to each client). Turning a Reaper feature on or off, or changing its settings, writes a structured audit entry too.

### 2.13 Keep management off the WAN

Do not enable remote (WAN) web administration or WAN SSH. The real-world attacks on ASUS routers target the internet-facing management surface, and keeping admin LAN-only is the single best protection you have. The dashboard's Security Posture card shows you at a glance whether anything is reachable from the WAN, and the Firewall Status tab's **exposure** card lists precisely what is.

### 2.14 Where to report issues

- **Bugs and questions:** open an issue on the project's GitHub repository, `TheUnboundDeveloper/AM-Reaper` (the link is in the README and on the About page). Attach a **diagnostics report** (2.10) and say which model, variant and version. A well-written report is, in the maintainer's words, worth as much as a donation.
- **Security findings:** see `SECURITY.md` in the repository — please do not open a public issue for an exploitable bug.
- **Do not contact ASUS or the Asuswrt-Merlin developer** about this firmware. Stock bugs in code Reaper has not touched belong upstream, but if a stock bug is remotely or LAN-reachable on a BE-series model the project still wants to hear about it.
- Updates are intermittent and depend on the maintainer's time and hardware; no schedule, support period or future compatibility is promised.

---

## 3. The dashboard and navigation

**After login you land on the dashboard** (`Main_ReaperDash.asp`). It replaced the stock Network Map, which is retired. Everything else in the interface opens inside the **app shell**: a header, a left navigation rail, and a framed content area that loads either a Reaper-native page or a stock Asuswrt page with the Reaper theme applied at serve time.

**Dashboard cards**

- **Internet** — WAN state (it updates itself during boot without a refresh), your real WAN IPv6 address (never a `fe80::` link-local), gateway and DNS, and an **internet on/off switch**. The switch is persistent across a reboot and asks before turning the internet off; the router's web interface stays reachable over the LAN.
- **Clients** — the connected-device list grouped by band; **View List** opens the full Devices page.
- **Security Posture** — fourteen rows: firewall (SPI), DDoS protection, remote/cloud access, admin login (HTTPS only / HTTP + HTTPS, LAN-only / WAN reachable), SSH access, JFFS partition and custom scripts, DNS rebind + DNSSEC, Wi-Fi encryption, MLO, WPS, UPnP, QoS engine, **Gatekeeper** and **Warden**. Every row is clickable and takes you to the page (and tab) that owns the setting.
- **Radio tiles** for each band, showing the SSID in its real case, and **USB tiles** per physical port (a hub shows as connected with a device count). A disk selector appears on the Storage card once two or more disks are attached.
- **System** — CPU load, memory, temperature, uptime, and the **firmware-update banner** at the top of the page when the check has found a release.
- **Mesh Nodes** and **AiMesh** cards where applicable.

**Navigation**

- The **left rail** is identical on every page. At the top is a live 24-hour router-time clock; above the "General" heading is the **Language** selector (all 25 languages; the active language is shown selected and English can always be chosen). Menu entries are the stock sections plus Reaper's own (Devices, Gatekeeper, Warden, AI Advisor on the MCP build). Installed **addons** (amtm, Diversion, scMerlin and the like) are gathered into one dedicated **Addons** section at the end of the rail (v2.7.5) — a single unfolding group on both the dashboard and the shell, instead of being scattered through the stock menus; an external "Help & Support" link opens in a new tab. At the foot of the rail a small **scythe mark** opens the About page; it stays at the bottom of the window while a long menu scrolls beneath it.
- **Tabs** run across the top of pages that have them (QoS / QoS Diagnostics under Traffic Manager; USB Disks as the first tab of USB Application; Long-Term Storage and Data Export under System Log; Diagnostics and Firmware under Administration; Policy Routing next to VPN Director under VPN).
- Every page lands scrolled to the top. The admin session logs itself out after **15 minutes** of inactivity.
- **Overlays.** An apply, reboot or firmware flash puts up a full-screen veil that locks the header and rail; it shows an elapsed-time heartbeat so a stalled operation looks different from a working one, and on the firmware page a Close button appears on any terminal state. After a firmware flash the page polls for the router's return and sends you back to sign-in. (The backlog notes that a few stock overlays still centre on the shell viewport rather than the whole window; that is cosmetic.)
- **Theme.** The Reaper look (matte black, crimson, jade and amber accents) is applied to stock pages by a web-server filter. It can be switched off from **Tools → Other Settings → Reaper interface theme** to serve the unmodified ASUS interface without reflashing (the web server restarts). The sign-in, set-password and logout screens show an animated model header that plays once.
- **Tablets** are supported (the frame pans horizontally when a page is wider than the column); phone-size screens are out of scope by design.

---

## 4. Each feature page

Each section covers: what it is, when to use it, how to set it up, what to expect, and limits and gotchas.

### 4.1 Firewall

**What it is.** One page, eleven tabs: live chain state, the stock Asuswrt controls, and Reaper's own rules engine. The engine is **off by default**; nothing changes until you enable it. It adds policy *on top of* the stock firewall rather than replacing it, so Gatekeeper, Warden, SDN and the base rules keep working underneath.

**When to use it.** When you want rules about *things* — "the TV may not reach the internet during work hours", "guests may not reach the LAN", "only my office may use this port forward" — without memorising addresses or writing iptables by hand. If all you need is "this device gets no internet", the Egress tab alone does it.

If you only read one thing: the **Rules**, **Egress** and **Forwards** tabs use **commit-confirm** — a change applies immediately but reverts on its own unless you press Keep before the countdown ends. That is deliberate. A mistake that locks you out of the router undoes itself, so you can experiment from a browser without a serial cable standing by. The **General**, **Network Services**, **URL Filter** and **Keyword Filter** tabs are the long-standing Asuswrt controls, re-presented in one place; they apply straight away with no countdown.

**Setting it up, step by step**

1. On **Objects**, define what you will refer to: `nas` = host `192.168.50.20`; `kids-tablet` = a MAC; `smb` = TCP `139,445`; `streaming` = a domain list. Country objects are not created here: add the country on the **Warden** page first, then point a Country (Warden) object at it so both features share one list.
2. On **Zones**, name your interfaces and set the broad policy (guest → lan: Drop).
3. On **Rules**, write the exceptions. First match wins; put specific exceptions above broad blocks.
4. Press **Preview** — it compiles the draft and shows the exact commands the router would run, generated by the same code that would apply them. Nothing is applied.
5. Press **Apply and confirm**, check you can still reach the router and that the things you meant to allow still work, then press **Keep these changes** before the timer ends (2.7).
6. On **Forwards**, press **Export** and keep the text somewhere safe.

Every list has **Modify**: the record loads back into the add-row, Add becomes Save, and saving replaces it in place.

**What to expect.** The master switch shows "Working…" and then the measured outcome — the engine sets a marker as its final act, only when its rules really went on, so a boot where the LAN was not ready yet reports as *inactive* rather than claiming success. Failures to load part of the ruleset are counted and reported; a partial load is distinguishable from "LAN not ready, will retry". Precedence within forwarded traffic is **explicit rule > Egress default > Zone policy**.

The eleven tabs follow, in the order they appear in the interface.

#### 4.1.1 Status

**What it is.** A read-only picture of what is actually filtering traffic right now: whether the base firewall and the Reaper engine are up, how many rules, objects and zones are loaded, which content filters are on, the state of Gatekeeper and Warden, and an **exposure** card listing what of the router is reachable from the internet (NAT, forwards, triggering, DMZ, UPnP with its advertised IGD version, the remote-admin port, SSH from the WAN).

**How to use it.** Treat it as the answer to "is what I think I configured actually live?" — the two can differ while a restart is in flight, or if a ruleset failed to build. Check it after every Apply, and again after a reboot. The exposure card is the one worth a slow read: anything listed there can be reached from the WAN side.

The page no longer runs `iptables`, so auto-refresh is cheap; raw chains are still available over SSH.

**Example.** You add a port forward, apply it, and the Forwards table shows your rule — but Status still reports the engine inactive. That means the generated ruleset did not run (most often the LAN was not up yet at boot). The rule exists in your configuration and does nothing until it does.

#### 4.1.2 General

**What it is.** The base Asuswrt firewall: the master on/off switch, DoS protection, whether the router answers pings from the internet, which packets get logged, an allow-list of addresses permitted to reach the router's own services from the WAN, and the separate IPv6 firewall.

**How to use it.** Leave the master switch and DoS protection on. Leave "respond to ping from WAN" off unless you have a specific reason — answering it confirms the address is live to anyone scanning. Remember that the IPv6 firewall is genuinely separate: IPv6 traffic is not translated, so every device on your LAN has a globally routable address and only this switch stands in front of it.

**Example.** To let only your office reach the router's web interface from outside, turn on the WAN access allow-list and add a single entry — source `203.0.113.10`, port `8443`, TCP. Every other source is refused, whatever the port forwards say.

#### 4.1.3 Rules

**What it is.** The Reaper rules engine. Each rule names a direction (**Inbound** into the router, **Forwarded** through it, **Outbound** from it), an action (Accept / Drop / Reject), an optional source and destination — as zones, objects or both — an optional service, an optional schedule (`Mon,Tue|09:00|17:00`), an optional rate limit, and whether to log matches. Also here: **Enable the rules engine**, the **Auto-revert timer**, **Preview**, **Apply and confirm**, and the confirmation card.

**How to use it.** Build the pieces first: define your Objects and Zones, then write rules that refer to them by name. Rules read top to bottom and the first match wins, so put specific exceptions above broad blocks. Press **Preview** before **Apply** — it shows the exact commands the rule set will run without running any of them. After Apply, the countdown starts: press **Keep** only once you have confirmed you can still reach the router.

Within forwarded traffic the order of precedence is: an explicit rule here, then a per-device Egress default, then the broad Zone policy. So a specific allow beats a device block, which beats a zone-wide deny.

**Example.** To stop a smart TV reaching the internet during the working day: direction `Forward`, action `Drop`, source object `tv` (the TV's address), destination zone `wan`, schedule `Mon,Tue,Wed,Thu,Fri|09:00|17:00`. Leave the service empty so it covers every protocol.

##### Allowing only certain destinations, and blocking everything else

This is the most common thing people ask for, and it does not need a "not" or "invert" setting. **Leaving a source or destination empty means "anything"**, so an allowlist is two rules in the right order:

| # | direction | action | source | destination | meaning |
|---|---|---|---|---|---|
| 1 | Forward | Accept | `iot-devices` | `vendor-cloud` | the traffic you want to permit |
| 2 | Forward | Drop | `iot-devices` | *(leave empty)* | everything else from those devices |

First match wins, so rule 1 must sit above rule 2. Add more allow rules above the drop as you need them. The same shape works for a single device, a group, or a whole zone.

Three ways to express "deny by default" exist, and they differ in scope rather than in strength — pick the narrowest one that covers what you mean:

- **an ordered pair of rules**, as above — best when the exceptions are specific and you want them visible next to the block;
- **an Egress default** on the Egress tab — best for "this device gets nothing outbound unless listed", because it is anchored to the internet interface and so never cuts the device off from the printer or the NAS;
- **a Zone policy** on the Zones tab — best for a broad posture such as "guest may not reach lan".

Because an explicit rule beats an Egress default, which beats a Zone policy, you can set a strict default at the bottom layer and open specific holes at the top without editing the default again.

**Worth knowing.**

- Rate limiting needs a kernel module that is not always present. If it is missing, rules that use a rate limit are **skipped** rather than silently applied without the limit, and a line saying so is written to the system log.
- **An empty source or destination means "anything". A named object that currently resolves to nothing is not the same thing** — that rule is left out entirely rather than becoming a rule that matches everything. A domain object that has not resolved yet, or an emptied group, therefore fails to a missing rule, never to an unintended block.

#### 4.1.4 Objects

**What it is.** Named things you can point rules at, so you write `printer` instead of an address you have to remember. Three kinds live here: address objects (a host or subnet, an address range, a MAC address, a domain name, or a country), address groups that bundle several objects under one name, and service objects that name a protocol and a set of ports.

**How to use it.** Name objects after what they are, not where they are — `printer`, `kids-tablet`, `nas` — so a rule still reads correctly after you renumber your network. Edit the object when a device moves and every rule using it follows automatically. Use a group when the same set of devices keeps appearing in rules.

**Example.** Create an address object `nas` of type host with value `192.168.50.20`, and a service object `smb` with protocol TCP and ports `139,445`. A rule blocking `smb` to `nas` from your guest zone then reads as plain English and needs no comment.

**Worth knowing.**

- **Domain-name objects** fill in as the router resolves the name, and entries expire after about an hour so a rotating content network does not accumulate stale addresses forever. They only see lookups the router's own resolver answers — a device using its own DNS server, or encrypted DNS, is invisible to them. A background refresh every ten minutes covers the common case. Members are saved to flash after each pass and replayed at boot.
- **A long list pastes in one go.** Domain and address lists take one entry per line or comma-separated, and the editor normalises the whitespace and line endings for you, so a forty-domain object goes in as a single paste rather than a few entries at a time. If something in the paste cannot be accepted the editor says so and keeps saying so — it never silently drops the remainder. These lists live on the router's internal flash (`/jffs`), not in nvram, which is what lifted the old size ceiling; a 40-domain object therefore saves only from v2.6.9 onward.
- **MAC objects** only work as a *source* on traffic into or through the router. A MAC address does not survive being routed, so it cannot be used as a destination or on outbound traffic.
- **Object names** are restricted to letters, digits and underscores; anything else is dropped and logged.
- **Country objects** are owned by Warden, not by this engine — set them up on the Warden page.

#### 4.1.5 Zones

**What it is.** A zone is a name for a set of interfaces — `lan` for your bridge, `wan` for the internet, `vpn` for tunnel interfaces. A zone policy then says what happens by default when traffic moves from one zone to another.

**How to use it.** Zones let you write intent once instead of repeating interface names in every rule. Start with the broad policy — for example guest to LAN denied — and then write specific Rules for the exceptions you actually want. Interface names accept a trailing `+` as a wildcard, so `tun+` covers every tunnel interface without listing them.

**Example.** Define a zone `guest` with interface `br1`, and a zone `lan` with `br0`. Add a zone policy: source `guest`, destination `lan`, action `Drop`. Guests can now reach the internet but nothing on your home network — and you have not written a single address anywhere.

**Worth knowing.** A zone policy is the weakest statement in the engine; both explicit Rules and Egress defaults override it. That is what makes "deny everything, then allow what I need" workable.

#### 4.1.6 Egress

**What it is.** A per-device default for traffic leaving your network toward the internet. Pick an address object, pick what should happen to its outbound traffic, and optionally limit it to a schedule. It is anchored to the internet-facing side only, so the device can still reach the printer and the NAS.

**How to use it.** This is the short path for "this device should not be on the internet" without writing a full rule. It sits between explicit Rules and Zone policy in precedence, so you can set a device to Drop here and still allow one specific thing through with a Rule above it.

Prefer `Reject` over `Drop` for devices someone is sitting at: reject sends a refusal and the application fails immediately, while drop leaves it hanging until it times out. Use `Drop` for devices nobody is watching, which reveals less.

**Example.** Object `kids-tablet`, action `Reject`, schedule `Sun,Mon,Tue,Wed,Thu 21:00-07:00`. The tablet keeps working on the local network overnight — it can still reach the printer and a media server — but it cannot reach the internet, and it says so instead of hanging.

#### 4.1.7 Forwards

**What it is.** Port forwarding: traffic arriving at the router from the internet on a chosen port is sent to a device inside your network. You can restrict which outside addresses are allowed to use the forward, and put it on a schedule. Each forward installs its translation *and* the matching permission together. This tab also holds Export and Import for backing up the whole firewall configuration as text.

**How to use it.** A port forward is a hole in the firewall by definition, so make it as small as it can be. Restrict the source whenever you know who will connect. Use a non-obvious external port — forwarding external `8443` to internal `443` will not stop a determined attacker but removes you from the results of everyone scanning the standard port. Give the target device a fixed address first, or the forward will eventually point at whatever picked up that address.

Export before you make a large change. The result is plain text you can paste back to restore.

**Example.** To reach a home server's web interface: protocol TCP, external port `8443`, internal address `192.168.50.80`, internal port `443`, source restricted to an object holding your office address. Everyone else scanning port 8443 finds nothing.

**Worth knowing.** Forwards bypass your Zone policy by design — that is what a forward is. If you want traffic to reach the device but not the rest of the network, put the device in its own zone.

#### 4.1.8 Network Services

**What it is.** The long-standing Asuswrt service filter. It matches traffic leaving your LAN by source address, destination address, port and protocol, and either blocks the listed traffic or permits only the listed traffic, within a daily time window.

**How to use it.** Choose the mode deliberately. Block-list blocks what you list and allows the rest. Allow-list allows only what you list and blocks everything else — which is far stricter, and will cut off things you forgot, so add DNS and the rest of your essentials before you switch it on.

The time window applies to the whole list, not per entry. If you need per-device or per-rule scheduling, use the Rules or Egress tabs instead.

**Example.** To stop devices using outside DNS servers and force them through the router: mode Block-list, source blank (meaning every device), destination blank, destination port `53`, protocol UDP. Add a second entry for TCP. The router's own resolver still works because that traffic never leaves the LAN.

**Worth knowing.** This filter needs the router's clock to be correct for the time window to mean anything. If time has not synchronised yet, the page says so.

#### 4.1.9 URL Filter

**What it is.** Blocks web requests whose address contains one of the keywords you list.

**How to use it.** Keep the entries short and distinctive — a fragment of the domain rather than a full address, because the same site is reached by many different URLs. Test with one entry before adding a long list.

Be realistic about the limits. This matches the request as it goes past, so it works on plain, unencrypted requests and misses almost everything on the modern web, which is encrypted. Treat it as a nudge for casual use, not a control. For blocking that holds, use a domain-name Object in a Rule, or block at the DNS level.

**Example.** Entry `example-game.com`. Plain requests to that domain are refused; the same site over HTTPS is not, which is why this tab is the weakest of the blocking options here.

#### 4.1.10 Keyword Filter

**What it is.** Blocks web pages whose content contains one of the words you list.

**How to use it.** The same realism applies, more so: the filter has to be able to read the page to match a word in it, so encrypted sites pass untouched. It also matches inside ordinary text, so a short or common word will block pages you did not intend — prefer distinctive phrases, and add them one at a time.

**Example.** Entry `freegamedownload`. A plain page containing that string is blocked. A page that is encrypted, or that spells it differently, is not.

#### 4.1.11 Logging

**What it is.** Chooses which firewall decisions get written to the system log — nothing, dropped packets, accepted packets, or both — and shows the recent entries.

**How to use it.** Leave it off for normal running. A busy connection can log thousands of lines a minute, which fills the log and pushes out everything else you might have wanted to read.

Turn on **Drop** while you are diagnosing a rule that is not doing what you expect, look at the entries, then turn it back off. **Accept** and **Both** are for short, deliberate investigations only.

**Example.** A device cannot reach a service and you do not know which rule is stopping it. Set logging to Drop, reproduce the failure, and read the entries — each logged line names the addresses and ports, which tells you which of your rules matched.

#### 4.1.12 Limits, and things deliberately not built

- **Rule negation ("not") does not exist**, because an empty field already means "any" and an ordered pair expresses an allowlist (4.1.3). A rule tracer is deferred.
- **The layer order is fixed**: Warden, then Gatekeeper, then the rules engine. An Accept rule here cannot let a geo-blocked source or a quarantined device through (v2.6.2; pending metal confirmation).
- The Status tab shows both of those layers' state, and the Rules tab links to them.

### 4.2 Gatekeeper

**What it is.** Opt-in, default-deny **device access control**. When it is on, every device already on the network is approved automatically; from then on each new device is **held at the gate** — no internet, no access to your other devices — until you decide what it may do. **Off by default.**

**When to use it.** Households and small offices where knowing the Wi-Fi password should not by itself grant access; IoT gear that should never see the LAN; visitors who need the internet for an evening.

**What it is not.** A second wall, not the first. A MAC address is an identity claim, not proof, and anyone who already has your Wi-Fi password could imitate an approved device. What it reliably stops is rogue gadgets, shared-password guests, and anything plugged into an open ethernet port.

#### 4.2.1 The four states

Every device sits in exactly one state. You set it from the Gatekeeper page, or from the Access dropdown on the Devices page.

| State | Internet | Your LAN | Typical use |
|---|---|---|---|
| **Approved** | yes | yes | your own computers, phones, the DNS server |
| **Internet only** | yes | **no** | cameras, TVs, smart-home gear, anything you do not trust indoors |
| **Guest pass** | yes | no | a visitor; expires after 4, 8, 24 or 48 hours |
| **Blocked** | no | no | a device you have decided about |
| *Pending* | no | no | not yet decided — the default for anything new |

**Internet only is the state that earns Gatekeeper its keep.** A smart TV or a camera has no business reaching your NAS, and this is a single click that says so.

#### 4.2.2 Turning it on safely

The first enable is the step that has historically caused trouble, so it is worth doing deliberately.

1. Open **Gatekeeper** and read the *How it works & honest limits* card.
2. Under **Settings → New devices**, choose **Quarantine until approved** (the default) or **Alert only (allow, notify)**. If you are nervous, start on *Alert only* for a day: you get the notifications and the pending list without anything being held.
3. Set the **Guest pass length**, and decide whether held devices see the **waiting-room page** and whether to **notify on new device**.
4. Switch it on.

**What "everything already here is approved" actually means.** On enable, the router grandfathers in every device it knows about, from three sources combined: its address table, its DHCP leases, and the named-client list. Three sources rather than one because an early version used only the live address table, so any device that happened to be asleep, idle, or IPv6-only at that moment was quarantined — including, on at least one occasion, the administrator's own computer. The union re-runs on **every** enable, so a device that was asleep the first time is not stranded later.

Even so: **enable it from a device that is plugged in and awake**, and check the pending list immediately afterwards.

#### 4.2.3 How it enforces, and the way back in

Enforcement is in the router, not on the device, and it has two halves: firewall rules decide whether a device reaches the internet or the router, and a layer-2 rule keyed on the device's hardware address decides whether it reaches the rest of your LAN.

**The escape hatch.** The **HTTPS admin page is always left reachable**, in every state, by an explicit rule that runs ahead of the blocking. You cannot fence yourself out of the control that turns Gatekeeper off. If your router is configured for plain HTTP only, the plain-HTTP admin port takes that role instead, and the waiting-room page is suppressed so it cannot sit in front of the login.

That escape hatch is **main-LAN only**. It is not reachable from an isolated guest network, which is what an isolated guest network means.

**Self-healing.** If a stock service flushes the firewall, enforcement re-applies within seconds. A watcher re-checks every 30 seconds.

**Enforcement holds even when the status says it is still arming.** The internet and LAN blocks come up first; the part that arms slightly later is the waiting-room page. A held device is held either way.

#### 4.2.4 Internet-only, and the LAN DNS trap

An *Internet only* device is sealed from your LAN by a rule on its hardware address, which is thorough: it blocks everything on the local network, in both directions, including traffic you might not think of as "LAN traffic".

**If your DNS server is a device on your LAN** — a Pi-hole, AdGuard Home, or anything else your DHCP advertises as the resolver — then that seal would also block DNS, and an Internet-only device would have working internet and no way to look anything up. It presents as "no internet" and is confusing, because the firewall is wide open.

Gatekeeper handles this, with one requirement you must meet:

> **The DNS server device itself must be in the Approved (full) state.**

Given that, the router automatically carves out DNS to the advertised resolver for Internet-only and Guest devices — but only when that resolver is on the same subnet, and only per-device. Blocked and unknown devices stay dark. If your resolver is the router itself, or a public resolver, none of this applies and there is nothing to do.

Since v2.6.2 the LAN seal also covers routes to *other* networks — the main LAN and every guest network, enumerated — and since v2.6.5 it covers IPv6 global addresses, rebuilt when your delegated prefix changes.

#### 4.2.5 Guest networks

Enforcement follows onto every network the router runs. Creating, editing or deleting a guest network re-applies Gatekeeper on every bridge immediately, and it is logged.

The waiting-room page works on an isolated guest network for an *unknown* device. An **approved** device on that network still cannot reach the router's pages — again, that is what *Access Intranet: off* means, and it is not a Gatekeeper decision. Devices on guest networks do get their hostnames.

All of the multi-network work is pending confirmation on a router that actually runs a guest network.

#### 4.2.6 Reading the status

The page shows one of four states, and it is designed never to claim it is protecting you when it is not:

- **Enabled** — armed and enforcing.
- **Arming** — waiting for the network to come up after a boot. Normal for a short time.
- **Not enforcing — check the System Log** — red, and it appears if arming has not completed after 60 seconds. Devices are **not** being held. This is a real fault; the log will say why.
- **Off**.

A held device that opens a web page sees a themed **"Awaiting approval"** notice, shown automatically through the sign-in popup on phones and laptops, rather than a dead connection. That page is generated by the web server and stays in English.

#### 4.2.7 Examples

**Seal the IoT.** Enable Gatekeeper, let everything grandfather in, then walk the Devices list and set every camera, TV, speaker and plug to **Internet only**. Nothing of yours changes; those devices lose the ability to reach your computers and storage. If your DNS is a LAN host, make sure it is set to **Approved** first (4.2.4).

**An evening visitor.** Set **Guest pass**, 8 hours. They get internet, never your LAN, and the pass expires without you having to remember.

**A new device you did not expect.** It appears in **Pending approval** with its name, connection type, band, and a flag if it is using a private address. Leave it pending — pending is already blocked — until you know what it is.

**Back out entirely.** Set *New devices* to **Alert only**, or switch Gatekeeper off. The admin page is reachable in every state, so this is always possible from a LAN device.

#### 4.2.8 Limits and gotchas

- **Phones using rotating private addresses reappear as new devices.** The pending list flags them. This is the single most common source of unexpected pending entries; it is the phone's privacy feature working, not a fault.
- **The device list is not in the settings backup.** It lives on the router's internal flash, and a factory reset clears it. Export it from the Storage page (4.11) if you have spent time on it.
- **Capacity is 512 devices**, tested to 300. The old 45-device ceiling is gone, and existing lists migrate at first boot. A write failure is logged rather than swallowed.
- The grandfathering step refuses to overwrite its list if that list is ever too large to load, and logs instead of failing quietly.
- Before v2.5.0, Block and quarantine were enforced only on the main LAN. That is fixed, and a quarantined device on a guest network now also gets the waiting page.
- A device's state is keyed on its hardware address, so it follows the device across address changes — but not across a deliberate address change by the device.

### 4.3 Warden

**What it is.** An opt-in **threat and geo firewall**. It drops traffic to and from known-malicious IP ranges (public reputation feeds), countries you select, and addresses you specify — enforced in-kernel with `ipset` across IPv4 and IPv6, at near-zero cost per packet. **Off by default.**

**When to use it.** Any router with a public WAN address that you would like to stop answering the constant background scanning; a household that wants to refuse whole countries it never talks to; anyone who keeps their own blocklist.

**What it is not.** A noise-reduction layer, not a complete defence. It decides on **addresses**, so a VPN, a proxy or a compromised host in an allowed country walks straight past it. Use it to shrink your exposure, not as a sole control.

#### 4.3.1 Setting it up

1. Tick the **threat feeds** you want: FireHOL Level 1, Feodo Tracker (botnet command-and-control), Spamhaus DROP, DShield top attackers. They merge into one de-duplicated set, so overlapping feeds never double-block or slow matching.
2. Optionally add up to **eight custom feeds**: a name, an HTTPS list URL, and an optional IPv6 list URL.
3. Choose **countries** from the searchable checklist. Review that list before enabling — see 4.3.5.
4. Choose the **direction** (4.3.7).
5. Add any **whitelist** and **manual block** entries, one address or CIDR per line (4.3.6).
6. Decide on **Log dropped packets**, the statistics options, and whether to **also filter the router itself** (4.3.7).
7. **Save & Apply**, then press **Update feeds now** for the first fetch. Afterwards feeds refresh on the schedule in Tools → Other Settings (default 04:30 daily).

#### 4.3.2 The order it decides in

This is worth understanding, because it is what determines whether Warden can inconvenience you, and it answers most "why was this blocked / not blocked" questions. Traffic entering the Warden chain is tested in this order, and the **first match wins**:

| # | Test | Result |
|---|---|---|
| 1 | Loopback traffic | **exempt** |
| 2 | DHCP (ports 67/68, and 546/547 for IPv6) | **exempt** |
| 3 | Established and related connections | **exempt** |
| 4 | Outbound checks, if direction includes them | see below |
| 5 | Source is in your **whitelist** | **exempt** |
| 6 | Source is in your **manual block list** | **dropped** |
| 7 | Source is on your **LAN** | **exempt** |
| 8 | Source is in a blocked **country** | **dropped** |
| 9 | Source is in a **threat feed** | **dropped** |

Four things follow from that order, and they are the four that matter:

- **Your LAN is exempt (step 7) before any feed or country is consulted (steps 8–9).** No feed and no country block can cut off a device on your own network. This is the property that makes the feature safe to leave on.
- **Established connections are exempt (step 3) before everything.** Enabling Warden, or a feed update, does not sever the session you are configuring it from.
- **Your manual block list is checked at step 6, *before* the LAN exemption.** That is deliberate — it is how you block a local device — but it means **a manual block entry that covers a LAN range will block that LAN device**, and the LAN shield will not save it. This is the one way to shut yourself out with Warden. Whitelist entries (step 5) beat manual blocks, so a whitelist entry is the way back.
- **Outbound is evaluated at step 4, before the source exemptions.** It has to be: on outbound traffic your own LAN host is the *source*, so if the whitelist were consulted first, any whitelist entry covering your LAN would silently disable outbound blocking for the whole network. It used to, and that was a real defect; the outbound tests now sit in their own chain ahead of the source tests.

Countries are evaluated *before* the feeds (step 8 before 9). That is why per-country counts are meaningful and the feed counter carries only what no country matched.

#### 4.3.3 Threat feeds

The four built-in feeds merge into one set. **FireHOL Level 1 already contains Spamhaus DROP, DShield and Feodo**, so ticking those alongside it is largely redundant — Spamhaus still adds value for its IPv6 list, the others add little.

**Custom feeds** are HTTPS only. The URL may not contain quotes, spaces or `@`; the router follows no redirect down to plain HTTP, and caps the download size.

**Every list is filtered before it is loaded.** Private, loopback and reserved ranges are stripped from all of them — feeds, countries, IPv4 and IPv6 alike. This is not a nicety: FireHOL Level 1 legitimately contains `192.168.0.0/16`, `10.0.0.0/8` and `127.0.0.0/8`, because it is documented for use on a WAN interface only. Ingesting those unfiltered is precisely what caused an early Warden release to take an entire network offline at 04:30. A careless or hostile list can no longer blackhole your own network.

Feeds are cached to the router's internal flash, so a router that boots with no internet still enforces the last good download. If `/jffs` is unavailable or read-only, a banner says protection is live but not persistent.

#### 4.3.4 Countries

Country lists come from ipdeny and refresh with the feeds.

**Review the list before you enable it.** Blocking a country you actually depend on — a VPN exit, a CDN edge, a game server region, a mail provider — will cut off services in a way that is hard to attribute later, because the failure looks like the remote service being down.

The status card shows **Countries blocked**, and an amber *N country list(s) empty* warning if a selected country has no addresses loaded. Take that warning seriously: an empty set blocks nothing, so the country you think you have blocked is open.

To remove a country, Ctrl-click to deselect it in the multi-select.

#### 4.3.5 Your own lists

Both boxes take one IPv4 or IPv6 address or CIDR per line.

- **Whitelist** — checked before everything except the built-in exemptions. Use it for anything you must never lose: a remote management address, a monitoring host, a VPN peer, a business partner in an otherwise blocked country.
- **Manual blocks** — checked before the LAN exemption, so this is the sharpest tool on the page. It will block a LAN device if you tell it to.

**Invalid entries are refused on save**, with a message naming them. The whole save is rejected rather than silently accepting what it could parse. An earlier version stripped offending characters instead — which turned `192.168.1.*` into `192.168.1.` and left people believing a subnet was whitelisted when nothing was. If a save is refused, fix the named line; do not assume the rest went in.

#### 4.3.6 Direction, and filtering the router itself

**Direction** has two settings. **Inbound only** protects the router and blocks unsolicited arrivals. **Both directions** additionally stops LAN devices *reaching* flagged addresses, which is what catches a device that is already compromised and calling home. ("Outbound only" was removed in v2.5.0 because it produced rules identical to Both.)

**Also filter the router itself** (off by default) applies the same blocking to connections the router *starts*.

It cannot lock you out. Management traffic is inbound to the router and its replies carry a LAN destination, both of which are exempt, so the web interface and SSH stay reachable and the toggle stays revocable. DNS resolvers and time servers are exempted automatically — a router with a dead clock fails TLS everywhere, which would look like a total outage.

It *can* stop the router reaching a feed source, DDNS or a VPN peer if a list happens to cover them. That failure is to stale data, and it is logged.

Drops here always go to the system log with the `REAPER-WARDEN-SELF` prefix, whatever the logging setting, and the self-monitor reports them as `warden-self-drop`. **That is the feature working, not a fault.** The log line is most of the value: malware with full control of the router can unhook these rules, so treat this as a speed bump and a detection signal rather than containment.

#### 4.3.7 Reading the statistics

The status card shows **Enforcing** or **Disabled**, the last feed update, which feeds are on, and the counts — **Countries / Threat feeds / Manual blocks / Unclassified**, plus prefixes loaded.

**Blocked hits** and **Top blocked countries** refresh every 30 seconds. The total is broken out by bucket so that `total = countries + feeds + manual (+ unclassified)`. *Unclassified* is non-zero only on a statistics store written before those buckets existed; it is shown rather than quietly folded into a named bucket.

Totals are saved to internal flash every 15 minutes, and on every path that would otherwise lose them, so they survive reboots, firewall rebuilds and upgrades. **Turning Warden off resets the counters.**

Blocking a single address severs its live connections immediately — a newly blocked address is dropped at once, because the hardware flow cache is flushed on apply.

#### 4.3.8 Examples

**Stop the background scanning, change nothing else.** Tick FireHOL Level 1, leave countries empty, direction Inbound only, logging off. This is the lowest-risk useful configuration: nothing on your LAN is affected, and the router stops answering the internet's constant probing.

**Refuse a set of countries you never deal with.** Select them, keep direction Inbound only to start with, and watch *Top blocked countries* for a week before considering Both. If a service breaks, the country list is the first thing to check.

**Catch a device calling home.** Direction **Both**, FireHOL Level 1 plus Feodo Tracker. An infected LAN device reaching a known command-and-control address is now dropped on the way out, and logged.

**Keep one address reachable through a country block.** Put it in the **whitelist**. Whitelist beats country and feed, and beats a manual block too.

**Block one local device outright.** Put its address in **manual blocks**. Remember this is the one entry type that overrides the LAN exemption — which is why it works, and why a careless CIDR here is the way to cut off your own network.

#### 4.3.9 Limits and gotchas

- **A whitelist entry covering your LAN is not needed** and never was — the LAN exemption at step 7 already covers it. Historically the page said the opposite in one place and the guidance in another; the exemption is in the chain and you can see it.
- Threat and country sets are created with a cap of 524,288 entries. The count against that cap is not yet shown in the interface.
- Eight custom feeds at the default timeouts can add roughly 16 minutes to an update window. A per-feed timeout is still owed.
- North Korea publishes no IPv6 zone; the nightly update no longer logs a failed fetch for it (v2.6.1).
- The country cache is replayed per set, members only, and **an empty live set never overwrites a good cache entry** (v2.5.9). That fixed country lists coming up empty after a reboot. Pending reporter confirmation on the first boot after upgrading from an older cache.
- The self-monitor watches for your LAN address or `127.0.0.1` appearing in any block set, and if it finds one it logs a critical line and re-applies the rules. It is a backstop against exactly the class of failure described in 4.3.3, not something you should ever see fire.

### 4.4 Policy Routing

**What it is.** A page in the VPN menu, next to VPN Director, that decides *which traffic* uses *which path* — an OpenVPN client, a WireGuard client, the plain WAN, or nowhere at all — by a rule you write. It adds the piece VPN Director lacks: rules keyed on a named **Firewall object or domain list** (destination), or on a **device by IP/CIDR or MAC** (source).

It is **off by default**, and turning it on changes nothing until you add a rule.

**When to use it.** Routing a *set of sites* through a tunnel; carving an exception out of a full-tunnel VPN; forcing one device through a VPN and **blocking** it if the tunnel drops; a hard "this device goes nowhere". If you only need plain source routing without those properties, VPN Director alone is fine.

#### 4.4.1 How it works

A rule has two halves: **what to match**, and **where to send it**. When traffic matches, the router marks it and steers it through the routing table for the target you chose — a VPN client's table, the normal WAN table, or a dead end.

It is built entirely from mechanisms already in the firmware — a firewall mark plus a routing-policy rule — so it adds no new moving parts and reuses the routing tables your OpenVPN clients already set up. Nothing here dials a tunnel or changes a VPN's own settings; it only decides what rides through one that is already connected.

**Policy Routing and VPN Director are meant to sit side by side.** Use VPN Director for the broad posture ("send everything through the tunnel", or "send this subnet through the tunnel"), and Policy Routing for the exceptions that need an object or a device — because a Policy Routing rule **wins** over a VPN Director rule for the same traffic. That is what lets you say "tunnel everything, *except* send this one streaming service straight out the WAN."

#### 4.4.2 The page

**The master switch** turns the whole engine on or off. With it off, no marks and no routing rules are placed, whatever is in the table.

**The rule table** lists your rules in order, with the match on the left and the target on the right, each with its own enable checkbox so you can park a rule without deleting it.

**The add-rule form** builds one rule: pick the selector type, fill in its value, choose the target, and add it. Every row also has **Modify**: it loads the rule back into the form, the Add button becomes Save, and saving replaces the rule in place.

**Apply and confirm** puts the whole list into effect at once and starts the same auto-revert countdown the Firewall Rules tab uses (the timer is set on the Firewall page): press **Keep** to make it permanent, or let it expire — or press **Revert** — and the previous rules come back on their own. The router owns that deadline, so closing the tab does not cancel it. Keep is the only thing that writes flash.

**The Domain lists card** is where you build and maintain the lists the rules point at (4.4.4). You no longer have to go to the Firewall page for this.

#### 4.4.3 What a rule matches

Each rule matches traffic one of three ways:

- **Domain list / object (destination)** — a named list of domains built on this page, or any Firewall address object or group, chosen from the dropdown. The rule matches traffic whose **destination** is in that list. This is the powerful one: name a set of streaming sites, or a country, and route everything headed *to* it in one rule.
- **Device by IP / CIDR (source)** — a single address or a range on your LAN, or a list of them (IPv4 or IPv6, one per line or comma-separated, up to 64). The rule matches traffic **from** it.
- **Device by MAC (source)** — a device's hardware address. The rule matches traffic **from** that device, wherever it picked up its IP.

##### VPN Director already routes by source IP — what do the device rules add?

A fair question; VPN Director's source rule and a device rule here do steer the same packets. The device rules exist for what they add on top:

- **Fail-closed.** If the tunnel drops, a device routed here is **blocked** until it comes back. VPN Director's rule would quietly fall through to the WAN unless you also enabled its kill switch.
- **Block as a target.** "This device goes nowhere", without a firewall rule.
- **MAC keying.** A MAC rule follows the device across DHCP changes; an IP rule does not.
- **Precedence.** A rule here **overrides** a VPN Director rule for the same device, so you can carve one device out of a broad "route this subnet" policy.

If none of those matter to you, VPN Director alone is fine — use whichever you find clearer.

#### 4.4.4 Domain lists

A domain list is a Firewall object of type *Domain name*: a name plus the domains it covers. The card on this page lets you **add, modify and delete** them without leaving Policy Routing; the Firewall page sees the same lists, so nothing is duplicated.

- **Entering domains.** The box takes one domain per line, or a comma- or space-separated paste from a text file. Blank lines and duplicates are dropped, everything is lower-cased, and each name is checked before it is saved. A list can hold as many domains as fit in about 1,900 characters — if a service needs more, split it into two lists and two rules.
- **How a list becomes addresses.** Two mechanisms feed it: every DNS answer the router's own resolver gives for a listed name lands in the list immediately, and a timer re-resolves every name **every 10 minutes** as a floor — which covers clients that use their own DNS, names already cached, and the cold start after a reboot. Addresses expire an hour after they were last seen, so a CDN that rotates its pool prunes itself.
- **Across reboots.** After every timer pass the lists are **saved to the router's flash** and restored the moment they are re-created at boot, so a rule is not blind until the first lookup. A rule whose set was a moment late at boot is re-applied by `rwatch` (logged, at most every two minutes).
- **CDNs change.** When a service starts reaching out to a domain you did not list, the traffic is not matched. That is the one piece no timer can fix for you — come back and **Modify** the list.
- **The Firewall engine does not need to be on.** The lists are built whenever Policy Routing is enabled, engine or no engine. If the Firewall engine *is* on and you edit a list here, the routing side uses the new list on Apply; the Firewall's own rules pick it up on the Firewall page's Apply, as its commit-and-confirm flow requires.

#### 4.4.5 Where a rule sends traffic

Every rule has one target:

- **A VPN client (OpenVPN 1–5)** — matched traffic goes through that OpenVPN client's tunnel, using the routing table the client already created. The tunnel does not have to be the default route; this steers only the traffic you named through it.
- **WAN** — matched traffic is forced out the normal internet connection, **bypassing** a full-tunnel VPN. This is how you carve an exception out of "route everything through the tunnel".
- **Block** — matched traffic is dropped. Useful as a hard "this device, or this destination, goes nowhere" that does not depend on the firewall rule order.
- **WireGuard 1–5** — supported since v2.6.7, with a cost described in 4.4.9. A WireGuard rule whose client is switched off is fail-closed: it blocks the selected traffic until that client comes up. Since v2.7.7 the target list **hides tunnels you have not configured** and flags ones that are configured but currently down, so a rule cannot be pointed at a target that was never going to carry it. The accelerator-bypass table has only **eight slots**, so a rule that would overflow it — or that names a tunnel whose interface is absent — is **refused and logged** rather than applied.

**IPv6 is covered** (v2.6.7): a destination list matches its IPv6 addresses, a MAC rule follows the device on both families, and a source rule may name an IPv6 prefix. If the chosen tunnel carries no IPv6, the selected IPv6 traffic is blocked rather than leaked around the tunnel.

#### 4.4.6 Order and precedence

Rules read **top to bottom, first match wins** — put specific rules above broad ones. A device that should mostly use a tunnel but reach one site directly needs the "reach this site directly" rule *above* the "send this device to the tunnel" rule.

Between features, **a Policy Routing rule takes precedence over a VPN Director rule** covering the same traffic. So you do not have to unpick VPN Director to make an exception — you add the exception here and it wins.

#### 4.4.7 Fail-closed

A rule that targets a VPN client **fails closed**: if that tunnel is **down**, the matched traffic is **blocked, not sent out the WAN.** This is deliberate, and it is the safety property that matters most in a routing feature. The whole point of sending a device or a site through a VPN is usually that it must *not* touch the internet directly — so if the tunnel drops, leaking that traffic to the WAN would be the one failure you were trying to prevent. Instead it stops until the tunnel is back.

If you actually want "use the tunnel when it is up, otherwise go direct", that is a **WAN** rule, not a VPN-client rule — state it explicitly rather than relying on a failure.

#### 4.4.8 Examples

**Send a set of streaming sites through a VPN, leave everything else direct.**
Build a domain list `streaming` in the card on this page, listing the services' domains. Then add a rule: selector **Object** = `streaming`, target **OpenVPN 1**. Only traffic to those domains uses the tunnel; the rest of the house is untouched.

**Tunnel the whole house, but send one service straight out the WAN.**
Set VPN Director (or a broad rule) to route everything through the tunnel. Then here: selector **Object** = `work-app` (a domain list for the service that dislikes the VPN's exit address), target **WAN**. Because Policy Routing wins over VPN Director, that one service goes direct and everything else stays tunnelled.

**Force one device down a VPN, and nowhere else if it drops.**
Selector **Source MAC** = the device's address, target **OpenVPN 2**. If OVPN 2 is connected the device uses it; if OVPN 2 goes down the device has no internet (fail-closed) rather than quietly falling back to your real address.

**Send a device — or a destination — nowhere at all.**
Selector **Source IP** (or **Object**), target **Block**. A hard stop that does not depend on where it sits in the firewall's own rule order.

#### 4.4.9 Limits and gotchas

- **WireGuard costs hardware acceleration.** The traffic accelerator does not honour a routing rule whose exit is a WireGuard tunnel, so Policy Routing does what VPN Director does and tells the accelerator to leave the affected flows alone. A **source** rule bypasses only that address (*accel bypass: this source*). A **destination-list or MAC** rule must bypass the **whole LAN** (*accel bypass: whole LAN*) — LAN traffic loses hardware acceleration while such a rule exists. The page says so on the rule and the log says so on every apply. Prefer a source rule over a destination-list rule where you can. Entries VPN Director or the WireGuard server placed are never removed.
- **Protocol and port matching is not offered.**
- **A list that has not resolved yet, or an emptied group, produces no rule** rather than a rule that matches everything — the same fail-to-nothing behaviour the firewall uses.
- **Objects are shared with the Firewall.** Domain lists are edited here or on Firewall → Objects; they are the same objects. Address, MAC and country objects are still created on the Firewall page and simply appear in the dropdown.
- **A confirmed set survives a reboot on its own** (v2.7.6/v2.7.7). The marking chain and the routing rules come back complete at boot with no visit to this page, and if the routing half is ever lost the router re-applies it the way it already did for a lost firewall chain.
- **Rules live on the router's internal flash** (`/jffs`), not in the stock settings backup — use *Reaper settings backup* on the Storage page. Twenty rules and more save without trouble.
- **Add rules from a device that is not itself being routed** by the rule you are testing.
- **To check what actually loaded**, the rules appear as routing-policy entries and a marking chain on the router; if something is not behaving, the system log names any rule that was skipped and why.
- All of v2.6.7 (WireGuard targets, IPv6, apply-and-confirm, the `/jffs` move) and the v2.6.9 address lists are **pending on-metal confirmation**; the WireGuard and IPv6 legs need a WireGuard client and an IPv6 line to test.

### 4.5 QoS (Traffic Manager)

**What it is.** Five modes, two of which are Reaper's own hardware engines. Those two shape traffic inside the Broadcom traffic manager **with the NAT and flow accelerator left on** — which is the thing ASUS never shipped. Stock forces a choice: hardware acceleration *or* software QoS. These give you both.

**When to use it.** Any line where upload saturation makes calls stutter or games lag. If your calls are fine and nothing ever feels slow while something is uploading, you do not need this page.

#### 4.5.1 Choosing a mode

| Mode | What it does | Accelerator |
|---|---|---|
| **HW QoS Classful** (type 11) — *recommended* | Five strict-priority classes with guaranteed minimums and per-class ceilings, hardware AQM on every queue, a download policer, and Wi-Fi WMM stamping. | **On** |
| **Hardware QoS** (type 10) | One shaped upload queue plus AQM. The simplest bufferbloat fix, no classes. | **On** |
| **Cake** | Software shaper, the best *download* control. One CPU core does all the work. | Off |
| **Traditional** | The classic software engine. | Off |
| **Bandwidth Limiter** | Hard per-device caps, up to 32 devices, both directions. Not bufferbloat control. | — |

Pick **HW QoS Classful** unless you have a reason not to. Pick **Hardware QoS** if you want the bufferbloat fixed and do not care which traffic wins. Pick **Cake** only if *download* bufferbloat is your actual problem and your line is under about 1 Gb/s — it is the only mode that genuinely shapes download, and it costs you hardware acceleration and a CPU core to get there.

**Changing mode reboots the router**, because the accelerator has to be reconfigured. Edits *within* a mode apply live.

#### 4.5.2 Getting the bandwidth numbers right

This is the step that decides whether the page does anything at all, and it is where nearly every "QoS isn't working" report comes from.

**Upload.** Run a few speed tests at a quiet hour, take the **lowest consistent** upload figure, and enter **90–95% of it**.

Why not 100%? Because the shaper only controls a queue it owns. If your figure matches what the line really delivers, the bottleneck moves upstream into your ISP's buffer — which you cannot see, cannot manage, and which is exactly what was causing your latency in the first place. The 5–10% you give up is what buys the router the right to be the bottleneck.

**Download.** Enter your **measured download speed**. Do not apply the 90% yourself — **the router already keeps about 10% headroom on the download policer for you.**

> **Known translation defect:** the English help text says this correctly. Some non-English packs still instruct you to enter roughly 90% manually, which leaves you double-derated to about 81% of your line. If you are reading the interface in a language other than English, enter the **measured** figure and ignore help text that says otherwise.

**With the bandwidth fields empty**, the engine behaves as though QoS is off, rather than classifying traffic with no shaper behind it.

#### 4.5.3 Setting up the classful engine

1. Enter the bandwidth figures as above.
2. Select **HW QoS Classful** and let the router reboot.
3. The classes ship as a measured profile — **Web/VoIP**, **Gaming**, **Streaming**, **Downloads**, **Default** — with starter rules for conferencing, SIP, game consoles, Steam, BitTorrent and web traffic.
4. Leave the **Aggregate cap (port shaper)** on.
5. Optionally enable **Guaranteed minimums**, **Trust DSCP marking**, **L4S marking** (experimental), and **Wi-Fi downstream priority (WMM)**.
6. **Apply.**

**Trust DSCP marking is off by default, deliberately.** DSCP is a claim the sending device makes about its own traffic, and any device on your LAN can mark its packets however it likes. Turn it on only if you control what is on your network and something on it marks correctly.

#### 4.5.4 Priority and ceilings: the two knobs

The class editor has two independent controls, and confusing them is the second most common mistake.

- **Order is priority.** The top row is served first under contention. Rank by how much the traffic suffers from waiting: interactive and voice at the top, bulk at the bottom.
- **Ceiling % is the most a class may ever take**, as a share of your upload figure.
- **Min % is a floor** the class is guaranteed under load. Minimums must total 100% or less.

**Never give the top class a 100% ceiling.** Its ceiling is the only thing protecting everything below it.

**The counter-intuitive part: bulk traffic wants a low priority and a *high* ceiling.** Strict priority means it yields instantly the moment anything above it has traffic, so it cannot hurt you — and the high ceiling lets it use the whole line when nothing else wants it. A backup class at the bottom with a 95% ceiling is correct.

#### 4.5.5 Classification rules

Rules match traffic to a class on port, protocol, address or MAC.

> **Do not classify by transferred bytes.** Rules that match on "how much this connection has transferred" cannot be offloaded to hardware. An accelerated flow keeps whatever class it was given when the connection *started*, so a rule meaning "once this download passes 512 KB, treat it as bulk" never fires for the flows that matter most — the long ones. The page warns about this. Some stock default rules are written this way, which is why the shipped Reaper rule set replaces them.

Unmatched traffic lands in the class named **Default**.

#### 4.5.6 Why download is different

The hardware engines shape **upload only**, and this is a hardware limit rather than an omission.

The traffic manager's queues are an *egress* object: they exist on the way out of a port. On the download side the chip offers a single **aggregate policer** — one rate limit for everything arriving — with no queues and no per-class split. There is no hardware path that could prioritise one kind of download over another, and the CLI cannot bind the per-flow policers that exist deeper in the silicon.

So:

- **Download bufferbloat** is handled by the aggregate policer (classful mode), or properly by **Cake**, which shapes in software at the cost of the accelerator.
- **Download prioritisation** is delivered as far as it can be by the **Wi-Fi WMM lift**, which raises the marking on the top classes so your access point serves them first. It only ever lifts; demoting the bulk class was tried and reverted after it measurably hurt throughput.
- The Traffic Analyzer's "By QoS class" chart therefore shows **upload only**. That is correct, not a missing feature.

#### 4.5.7 Verifying it works

Saturate your upload with a large backup or file send, and watch the live columns.

**What success looks like:** the bulk class pins near its ceiling, **its drop counter ticks up**, and a simultaneous call or speed test stays responsive. The rising drop counter is the AQM holding that class to its rate — it is the system working, not a fault.

**What failure looks like:** nothing changes. That almost always means your upload figure is above what the line actually delivers, so the router never becomes the bottleneck and never gets to make a decision. Lower it and try again.

#### 4.5.8 Examples

**A home office on a fast symmetric line.** Web/VoIP top with a modest ceiling, gaming next, streaming below that, backups at the bottom with a 95% ceiling. On a multi-gigabit upload the engine will rarely engage at all — it is insurance for the day someone starts a large upload during a call.

**Fix the stutter, do not think about classes.** Choose **Hardware QoS** (type 10), enter 90–95% of measured upload, apply. One queue, correct AQM, accelerator still on.

**Download bufferbloat on a slower line.** Choose **Cake**. Accept the loss of hardware acceleration; below about 1 Gb/s the CPU keeps up and Cake's download control is better than anything the hardware path offers.

**Cap a child's tablet.** That is the **Bandwidth Limiter**, not the classful engine. Different tool, different page section.

#### 4.5.9 Limits and gotchas

- **Strict priority only.** The per-class "Weighted (WRR)" option was removed in v2.5.4: the hardware's egress scheduler on these ethernet ports cannot actually create a weighted queue, so every class silently ran strict-priority anyway. The page now describes the classes as what they are. Any remaining text mentioning a weighted pool refers to that removed option.
- **802.1p and 802.1Q are not required** and are not read by this engine. Classification is internal to the router's forwarding path. WAN VLAN tagging is only for ISPs that mandate a tag for link-up; 802.1p priority is not honoured across the ISP boundary anyway.
- Classes were served in **inverted priority order** until v2.5.4. The fix is confirmed at the queue-configuration level on the RT-BE96U; drain behaviour under sustained classified load is still owed a test.
- On a **GT-BE98**, the v2.5.4 queue rebuild could be rejected by the traffic manager, taking all IPv4 off the air while IPv6 still worked. v2.6.0 made the rebuild transactional: on rejection the queues are restored to the stock layout and a log line says the priority correction was not applied. Worst case is now the old priority order, never no internet. Pending reporter confirmation.
- **Leftover settings from a previous mode stay in place, inert.** Switching from classful to type 10 leaves the classful keys set. They do nothing, but they can make a perfectly healthy type-10 configuration look like a broken classful one when you go looking.
- Cake mode filters redundant upload acknowledgements and targets a 50 ms base round-trip time.

### 4.6 QoS Diagnostics

**What it is.** A tab to the right of QoS under Traffic Manager: a live view of the hardware traffic manager (the Runner/XRDP egress scheduler) — per-queue occupancy, scheduler discipline, drops per second (tail + AQM combined), shaper rate and configured size, an *estimated* delay (backlog ÷ shaper rate; the hardware has no direct latency counter), live trend graphs and a port selector for the WAN-upload and LAN-download schedulers.

**When to use it.** To verify that shaping is engaging, to see which queue is dropping under load, or to confirm after a firmware upgrade that the five class queues exist (the GT-BE98 IPv4 incident in 4.5 showed up here as queues that were simply gone).

**What to expect.** Fast polling (250–500 ms) runs only while the page is open. The view adapts to your mode: a single shaped queue under Hardware QoS, the full scheduler under HW Classful; "No egress traffic-manager data" means QoS or the accelerator is not active. Occupancy reads 0 on an idle link and fills under load. Counters are 32-bit and wrap about every 15 seconds at ~2 Gb/s; a wrap is discarded rather than drawn as a spike. Trends fill from the left and flow smoothly.

### 4.7 Traffic Analyzer

**What it is.** A native bandwidth and usage page driven by the `rtrafd` collector: live WAN throughput with an optional latency trace, per-QoS-class upload, per-network totals, top devices, live top talkers by destination-port bucket, and a monthly data cap.

**When to use it.** To see who is using the line and when, to confirm QoS classes are actually receiving traffic, and to keep an eye on a metered connection.

**On privacy.** The collector **adds no listening ports** and sends nothing anywhere. It reads counters the kernel already keeps. The one thing that leaves the router is the optional latency probe, and only if you give it a target.

#### 4.7.1 Turning it on, and where history lives

1. In **Settings**, turn on **Collect traffic history**. Without it the realtime monitor still works, but there is no history and no per-device accounting.
2. **History storage** is a pointer to the Long-Term Storage page (4.11), where you choose RAM, JFFS or USB.
3. Optionally set a **WAN latency probe** target and a **Monthly data cap**.

> **The storage choice is the one that matters.** The default is **RAM**, and on RAM every number you see is lost at the next reboot. If you want history that outlives a restart — and the 14-day, monthly and yearly views only mean anything if it does — set the store to JFFS or USB *before* you start collecting. USB is the right answer if you have a stick in the router: it is larger and it spares the internal flash the write cycles.

The **latency probe** sends one ping per sample to the target you name. **Leave it blank and nothing is sent at all.**

The **data cap** is informational: a warning is logged at 80% and again at 100%. Nothing is cut off, and nothing is throttled.

#### 4.7.2 The windows

| Window | Resolution | Good for |
|---|---|---|
| **Live** | 100 ms, 1 s, 10 s, 30 s | watching something happen right now |
| **24 hours** | hourly | "what happened last night" |
| **14 days** | daily | weekly patterns, a device that started misbehaving |
| **By month** | monthly | a metered connection |
| **1 year** | monthly | long-term totals |

Live at 100 ms is genuinely 100 ms. The chart places each reading by the time it arrived rather than by its position in a list, so it scrolls smoothly instead of jumping — and a missed poll shows as a smooth interpolation rather than a stutter.

The **per-class stack updates every 4 seconds** and visibly steps. That is inherent to how often the hardware reports queue statistics, and it is deliberately not smoothed: inventing values between real samples would be inventing data.

#### 4.7.3 How per-device numbers are counted

Per-device bytes come from the kernel's connection-tracking table, which on this platform **already includes the bytes the hardware accelerator forwarded**. Accelerated flows are counted; nothing is missed because it was offloaded.

This is worth stating because it was once wrong in a way that mattered. An earlier version accounted from the flow cache instead, which only ever sees *accelerated* flows — so everything on the software path was invisible, and large fast downloads in particular went missing, because those are exactly the flows that get evicted and re-learned most often. If you remember the Traffic Analyzer under-reporting big downloads, that is what it was, and it is fixed.

Other details worth knowing:

- **Both IPv4 and IPv6** are attributed per device, keyed on hardware address, so a dual-stack device is one row rather than two.
- **Guest and SDN networks are included.** Attribution reads your live bridges, so a new guest network appears without configuration. Earlier versions tested only the main LAN subnet and silently dropped every guest client.
- **The router's own traffic** goes to a hidden **Router** bucket, so per-network totals plus clients add up to the WAN line instead of leaving an unexplained gap.
- **Inbound connections** — port forwards, UPnP — are attributed to the device that received them.
- **Offline devices keep the names you gave them.**
- If polling stops, the status pill turns amber **No response** rather than drawing zeros. A flat line at zero means zero; amber means "not known".

#### 4.7.4 Examples

**Find what is saturating the line.** Live window, watch **Top devices** and **top talkers by port bucket** together. The first tells you which device, the second tells you roughly what kind of traffic.

**Confirm QoS is doing something.** Start a large upload and watch **By QoS class**. Traffic should appear in the class your rules predict. If everything lands in Default, your classification rules are not matching (4.5.5).

**Watch a metered line.** Set the monthly cap, use the **By month** view. The cap warns; it does not enforce.

**Catch an overnight talker.** 24-hour view the next morning. A device that transfers steadily at 03:00 is worth a second look.

#### 4.7.5 Limits and gotchas

- **By QoS class is upload-only**, and only populates under HW QoS Classful. That is a hardware property, not an omission — see 4.5.6.
- **RAM storage loses everything at reboot.** The longer windows are meaningless on RAM.
- A device with no IPv4 traffic shows a blank address until the network map names it.
- A device-name mis-attribution is possible when a DHCP lease is reused by an offline device's address, and a negligible byte undercount when a duplicate row is folded away. Both are accepted trade-offs.
- A store that attaches before the clock is set used to have the current month or day wiped — the "Month tab resets after a firmware update" symptom. Slot ageing is now driven by absolute time and nothing is aged while the clock is still unset.
- IPv6 per-device attribution and the one-year totals for IPv6 devices on a USB store are pending field confirmation.

### 4.8 Devices

**What it is.** The **Device Identity Manager**: one page that correlates everything the firmware otherwise scatters about a device — custom name, DHCP reservation, Gatekeeper access state, and live presence (leases, address table, Wi-Fi association, band, last seen, 24-hour traffic) — keyed on hardware address.

It is a **lens, not a second engine**. Every action writes to the same stores the rest of the firmware reads, and access states are enforced by Gatekeeper. Nothing here has its own private copy of anything.

**When to use it.** Naming devices, pinning addresses, checking who is online, spotting reservation problems, and changing a device's access without leaving the page.

#### 4.8.1 Naming

Click a name to rename it inline. **Your custom name wins everywhere** over whatever the device calls itself, and it propagates to every page — the client list, Gatekeeper, Traffic Analyzer, Connections, and the DHCP lease log.

There is one master name store behind that, deliberately, because there used not to be. Renames could appear to revert, or show the old name on some pages and the new one on others, and deleting a single offline client could wipe every custom name you had set. Those were real defects with a single cause — several parts of the firmware parsing the same store differently — and the fix was to make one store authoritative. Field devices with duplicate records left over from that period clean themselves up on the next reboot.

#### 4.8.2 Pinning an address

**Pin IP** opens a pool-aware dialog. It recommends an address **outside** the DHCP pool, which keeps the pool free for new arrivals; the device moves to it at its next lease renewal rather than immediately. You can also keep the address it currently has, inside the pool.

**Widen pool** extends the DHCP range toward the usable subnet when the pool is tight.

#### 4.8.3 The Network Ledger

The ledger card flags things that will bite you later:

- the DHCP pool is exhausted, or running low;
- the reservation store is nearly full — this is an NVRAM size limit, not a made-up one;
- **reservations outside the current subnet**, which the DHCP server silently ignores. This is the one people lose time to: the reservation looks fine on the page and does nothing, usually because the LAN was renumbered after it was made;
- duplicate reservations;
- devices associated to Wi-Fi that cannot get an address.

#### 4.8.4 What the connection column tells you

Wired versus wireless is read from the LAN bridge's forwarding table rather than guessed, so Wi-Fi 7 and 6 GHz clients are no longer mislabelled as Wired.

- A **Wi-Fi 7 MLO** device is one row showing its combined bands (`MLO · 5+6 GHz`), with its affiliated links labelled rather than flagged as faults.
- Devices behind an **AiMesh node** are shown as Wi-Fi on their real band. The node itself gets an **AiMesh Node** chip and shows its backhaul band, or Wired if it is cabled.
- **First-seen** stamping waits for the clock to be set, so a device does not claim to have been first seen 961 days ago.

#### 4.8.5 Filtering and export

Filter chips: All, Online, Offline, Unnamed, Reserved, Randomized, Blocked. Search matches name, address or hardware address.

**Export list** saves the whole inventory as CSV, JSON or HTML.

> **The export is unsanitised.** It contains every device name, hardware address and IP address on your network. It is meant for your own records. Do not attach it to a forum post or a bug report — unlike the diagnostic bundle (4.13), nothing in it is redacted.

#### 4.8.6 Limits and gotchas

- **A phone using a private (randomized) address reappears as a new device** each time it rotates, until you turn that feature off for your network on the phone. This is the single most common source of unexpected new entries here and in Gatekeeper.
- The reservation store is limited by NVRAM size; the ledger warns before you reach it.
- The router's own address can still appear as a row rather than being folded into a router bucket the way the Traffic Analyzer does it. Known, deferred, harmless.

### 4.9 Connections

**What it is.** A live **flow explorer** drawn from the Runner flow accelerator. **Quick Look** (the default) lists device name, local IP, remote IP:port, an internal/external badge, protocol and TCP state. **Advanced** shows, per flow, whether it is forwarded in hardware or by the CPU (with a real per-flow percentage split), egress queue and QoS class, DSCP, live rate, total bytes and true age; summary cards show how many flows are accelerated and the overall hardware-versus-CPU split; filters narrow to accelerated or CPU-path flows; a **Pause** control freezes the view. Polling (500 ms – 4 s) runs only while the page is open; the stock connection page is retained as a fallback.

**When to use it.** To see what a device is talking to right now, to confirm that bulk traffic is hardware-accelerated, or to understand why a WireGuard Policy Routing rule cost acceleration (you will see the affected flows on the CPU path).

**Gotchas.** "No active flows in the accelerator cache" means there is no traffic or the accelerator/QoS is off. Queue numbers are mostly zero under Hardware QoS (a single shaped queue) and richer under HW Classful.

### 4.10 Wireless Quality and WiFi Professional (all bands)

**Wireless Quality** (the Wireless tab) is a diagnostics page:

- **Radio State** for every band — channel, width, **Lock current channel / Unlock**. With the channel on Auto the radio re-picks channel and width on every boot and wireless restart; Lock pins the running channel through the supported path. Both Lock and Unlock restart that radio, dropping its clients for about 20 seconds, and warn first.
- **Channel Selection Constraints** — the decoded auto-select exclusion list and the territory/board branch actually in effect.
- **Channel Quality Capture** — an on-demand 1 Hz sample (undecodable energy, free airtime, PHY glitches) written to RAM, downloadable as CSV. Nothing keeps running afterwards.
- **Auto Scan** — sweeps a radio's channels *at the width it will actually run* (6 GHz in 320 MHz blocks, 5 GHz in 80 MHz blocks, 2.4 GHz as 20 MHz channels), ranks them by cleanliness, and **restores the original channel when it finishes**; only **Pin best** commits the winner (an owner decision from v2.5.4 — the page text still describes the earlier auto-pin behaviour in one place). Each candidate restarts the radio, so run it from a wired client or another band; DFS channels are deliberately not swept (each needs a 60-second listening period). Pinning takes that radio off automatic selection until you set it back to Auto. The report can be printed to PDF or downloaded as HTML with a spectrum plot.
- **Passive Channel Monitor** (`rchqd`, opt-in) watches only the current channel and flags *degrading — consider Auto Scan*; it never changes a channel. Degraded/recovered transitions are logged, edge-triggered and rate-limited; the threshold is tunable (`rchq_degraded`).

**WiFi Professional — All Bands** lays every radio side by side (it builds itself from the router's real radio list, so a four-radio GT-BE98 gets four columns) and applies once: only changed fields are written and all radios cycle together (~10 s) instead of once per band. It asks the router once rather than 116 times, so it opens quickly. Region and the wireless scheduler stay on the classic per-band page; main-network SSID visibility and client isolation are set on the General Wireless and Network pages because on this hardware the main network is an SDN profile. *Disable 802.11b* is the master for the 2.4 GHz preamble control; "B/G Protection" was removed because the driver resets it on every restart. Roaming assistant: 0 = off.

**Gotchas.** Smart Connect excludes 6 GHz by default on some configurations (visible in the Smart Connect Rules table as "- -" columns, which is normal). The Professional page's first load after an upgrade can take ~15 s; the cause is under investigation.

### 4.11 Long-Term Storage, Data Export and the Reaper settings backup

These share the **Storage** page under System Log.

**Long-Term Storage** — choose the durable **Location** (RAM only / Internal (JFFS) / USB storage) and toggle each **dataset** (device history and action audit, traffic history, rwatch incident dumps, channel-quality history, syslog mirror; Warden is locked to JFFS). The table shows written size, size cap and **Collecting since** per dataset; the health line reports free space and falls back to RAM if no writable USB volume is attached. Once a durable location is collecting, each device gains a timeline (first seen, renames, reservations, offline spans, cumulative traffic). See 2.6 for the filesystem and USB guidance. *(The page's intro line still says policy "always lives in nvram"; since v2.6.3–v2.6.9 the Reaper lists live on `/jffs` — see 2.4.)*

**Data export** (mode control here; destination on **Administration → Data Export**) — per-device connection-health metrics (round-trip latency, jitter, loss, TCP connection count and state, throughput, online state). Modes: **Off** (nothing retained or sent), **Store only** (history on the router, nothing leaves), **Store + Export**, **Export only**. Any mode other than Off turns on the **Health probe**, which can also be enabled on its own for the live view and **Preview payload**. Targets: Splunk HEC, Datadog, Dynatrace, Elastic, generic HTTP/JSON, OpenTelemetry, TLS syslog (push), or a **Prometheus** OpenMetrics scrape endpoint (pull, bearer token required). TLS verification is on by default; the API token is stored masked and kept out of process lists and logs; an option hashes device MACs before they leave. **Test connection** and **Preview payload** show exactly what will go out. The probe is light enough to leave on (spread across ticks, at most 16 pings per tick, skipped while the link is saturated; default interval 60 s); the exporter refuses to push a snapshot older than three minutes, so a crashed collector never masquerades as live data. Not included by choice: wireless RSSI/PHY metrics and TCP retransmit counts.

**Reaper settings backup** — **Export settings / Import settings** (2.5).

### 4.12 USB Disks

The first tab of **USB Application**: each attached disk with its partitions, usage and a badge on the one that **holds the long-term store**; a **health scan** (a real `e2fsck` on ext4, with a pass/fail verdict and the check log; the result stays on screen); **Format** with a volume label and a filesystem selector (ext4 / ext3 / ext2 / FAT32 / NTFS / HFS+, with a one-line hint per choice — see 2.6); and **Safely remove** (eject), which now requires the anti-forgery token. Formatting permanently erases the disk and asks first. Formatting logs to `/tmp/disk_format/<dev>.log`. The format confirmation dialog is still stock-styled (backlog, cosmetic). Samba shares are named for their folder (`reaper`), with "(at DISK)" added only when two disks hold a folder of the same name.

### 4.13 Diagnostics

**Administration → Diagnostics**: the sanitized report described in 2.10. The page lists what is collected and what is removed or masked, shows what the top of the report (the ledger) looks like, and has one **Download Report** button. Stay on the page for the 20–30 seconds it takes. The FINDINGS block at the top is the first thing to read when something is wrong (5.8).

### 4.14 Firmware

**Administration → Firmware Upgrade** is a Reaper page:

- **Installed Firmware** — model, variant (Standard / AI Advisor), Reaper version, base build.
- **Updates** — **Check for Update**, the release notes inline, **Download and Install** (verified end-to-end, 2.11), **Scheduled Check** with **Check at** hour.
- **Manual Upload** — with a real progress bar; it warns if the file does not look like an image for this model or variant. The page gives a good image up to ~5 minutes to be verified before calling it rejected.
- **Mesh Nodes** (at the bottom) — every AiMesh node with name, address, reported firmware version and online state; **Update** opens that node's own firmware page in a new tab where you flash it natively (the image is never relayed through this router), and **Update all nodes** pushes the current firmware the way the stock AiMesh upgrade does. Update one node at a time and let it come back.

The flashing overlay shows download, upload and flash phases with an elapsed-time heartbeat; a Close button appears on any error and during download/upload, but not during the flash itself. After the flash the page waits for the router and returns you to sign-in. Known open item: cancelling at the upgrade confirmation during an upload leaves the buttons dead until the page is reloaded.

### 4.15 About

Opened from the scythe mark at the foot of the rail. It states the image's **provenance** — **Patches applied** (the public series count, shown as *N — series as of vX* when the image is ahead of its cut), the **upstream base pin** (the exact Asuswrt-Merlin commit), the build date and the clean-room build environment — followed by the commands that rebuild the image from scratch. Those figures are written by the build, not typed into the page. Below are the credits (RMerlin first), the project links, the licence position (GPL v2 for Reaper and the Merlin base; proprietary ASUS/Broadcom components under their own terms; no warranty; not affiliated with ASUS or Broadcom), and a **Donate** button that goes to the project's own page so the destination can change without a new firmware.

### 4.16 AI Advisor (MCP build only)

**What it is.** A **read-only** Model Context Protocol server (`rmcpd`) that lets **your own** AI client, with **your own** API key, read this router's status and configuration to audit and explain it. It cannot change a setting. It is present only in the `_MCP` build; the noMCP build has no daemon, page, menu entry or settings.

Its fences: **off by default** and never started at boot; **LAN only** (it binds the LAN address and is never reachable from the internet; optionally pinned to one client IP); **two-factor** (arming needs an arming code of at least 12 characters, stored only as a one-way hash, in addition to the admin password; optionally an enrolled **USB key** that locks the Advisor within about a second when pulled and cannot be un-enrolled without the stick); **secrets never leave** (Wi-Fi passwords, credentials and keys are redacted at the single point every tool's output exits); **time-boxed sessions** (15–240 minutes; the door locks itself); **no API key on the router**; the router sends nothing to any cloud. It serves HTTPS with the router's own web certificate when one is loaded.

**Setting it up**

1. On **AI Advisor**, set an **arming code** and keep it in your password manager — it is not recoverable from the router. Optionally **Enroll USB key**.
2. Set the **LAN port**, **Session timeout** and optional client-IP pin; **Save settings**.
3. When you want a session: enter the code, optionally tick **Allow network diagnostics** (bounded, read-only ping / traceroute / DNS / netstat — off by default, per session, never persisted), and press **Arm**. The page shows the endpoint, a bearer token (shown once) and a **Claude Desktop config snippet** to copy.
4. Point your AI client at the endpoint. **Disable now** ends the session early.

**Limits.** Repeated wrong codes lock arming temporarily. The diagnostics tier refuses loopback, link-local, ULA and private targets that are not on this router's own LAN, so it cannot be turned into an internal scanner; every probe is logged. If the key is lost, only a factory reset clears the USB factor.

### 4.17 Tools → Other Settings: the Reaper switches

Three settings with a **?** beside each:

- **Reaper interface theme** — off serves the unmodified ASUS interface (the web server restarts).
- **Socket bind shim (nvram netlink)** — **on by default**; works around the closed-library defect that can leave settings unable to save until the router is restarted. Needs a reboot to change. Each rescue writes a log line naming the process.
- **Warden feed update schedule** — cron format; empty = 04:30 daily.

Saving on this page no longer logs you out unless the setting needs a web-server restart.

---

## 5. Efficiency and good practice

1. **Know the layer order.** Traffic meets **Warden → Gatekeeper → the rules engine**, in that order, on every base chain. Use Warden for "never talk to these ranges or countries", Gatekeeper for "which devices are allowed at all", the Firewall rules for the specific policy between them, and Egress defaults for the short "this device gets no internet". Do not re-express a Warden block as a firewall rule, or a Gatekeeper block as a Policy Routing Block; one layer, one job.
2. **Keep lists small and named for what they are.** A country object points at Warden's set rather than copying it; a domain list should hold one service, split if it is long; an address object is `printer`, not `192-168-50-20`. Warden's feeds merge and de-duplicate, so FireHOL Level 1 alone covers three of the four built-ins.
3. **Mind the WireGuard bypass cost.** A Policy Routing rule that sends a *device (by MAC)* or a *destination list* to a WireGuard client bypasses hardware acceleration for the **whole LAN** for as long as the rule exists. If you can express the rule as a **source IP/CIDR**, only that address loses acceleration. If you can use an OpenVPN client as the target, nothing loses acceleration.
4. **VPN Director or Policy Routing?** Use VPN Director for the broad posture — "everything (or this subnet) through the tunnel". Use Policy Routing for what needs an object or a device, or one of its four properties: fail-closed, a Block target, MAC keying, and precedence over VPN Director. If you need none of those, VPN Director alone is fine and simpler.
5. **Set the QoS bandwidth honestly.** 90–95 % of the *lowest measured* upload. Too high and the ISP's buffer takes over and nothing here can help; too low just wastes headroom. Put your priority classes in order of latency-sensitivity, not importance, and never give the top class a 100 % ceiling.
6. **USB choice.** An ext4 stick that stays in the router is the right home for traffic history, the syslog mirror and incident dumps. FAT32 is for disks you carry about. Keep the file share closed to untrusted users if the store is on it.
7. **Apply, test, then Keep.** On the Firewall and Policy Routing pages, make the change from a device the rule does not touch, confirm what you meant to allow still works, then press Keep. If you are not sure, let the timer run; reverting is free.
8. **After every upgrade**, look at: the System Log for migration lines (`gatekeeper: device list migrated …`, `rule list migrated …`, `N list(s) migrated …`) and any `hwqos … REJECTED` or `FATAL` line; the Firewall **Status** tab (engine active? exposure as expected?); the Warden tile (countries amber?); the Gatekeeper state (Enabled, not Arming/Not enforcing); the About page's patch count; and — if you run QoS Classful — that you still have IPv4. Then take a fresh Reaper settings export.
9. **Read the diag FINDINGS first.** The report's top block is a list of one-line verdicts the script derives itself: an nvram value near the 1 KB cap, an un-migrated Gatekeeper list, a stuck `nvram`/`iptables` reader, a D-state process, a daemon enabled but not running, a missing cron line, an old direct firewall hook or a missing front chain, rules that failed to load, a conntrack table over 80 %, a WAN link stuck at 10/100 Mb/s, a Wi-Fi station with hundreds of disassociations, or a `/jffs` that is unmounted, read-only, nearly full or unwritable. Most field problems to date would have been named there; check it before reading the sections. The syslog-history part of the report (station churn, deauth errors, DHCP discover sources, boot and panic counts) is what separates "the router did it" from "one client is flapping".
10. **Leave logging off** on the Firewall Logging tab and Warden's drop log except while you are diagnosing something; a busy line can write thousands of lines a minute and push out the entries you need.
11. **Leave the extras off** unless you use them: the Advisor's network-diagnostics tick-box, the router-self filter in Warden, the Traffic latency probe, and the accelerator health probe in `rwatch` (`rwatch_gdx=1`) are all opt-in for a reason.

---

## 6. Troubleshooting quick table

| Symptom | Where to look | Fix |
|---|---|---|
| Settings will not save; one CPU core busy; everything else works | System Log for `reaper-nv` / bind-shim lines; diag FINDINGS "stuck nvram reader" | The closed-library freeze (1.5). The shim is on by default (4.17); a reboot clears a stuck process. Each logged rescue is evidence for the bug. |
| A Firewall rule or Policy Routing rule "disappeared" | Firewall / Policy Routing page: did you press **Keep**? Log tag `reaper_fw` / `reaper_pbr`: `commit-confirm: reverted …` | It auto-reverted (2.7). Re-apply and press Keep within the timer; lengthen the timer if you need more time. |
| Firewall table shows a rule but Status says engine inactive | Firewall → Status; log `reaper_fw` | LAN was not up when the rules ran, or part of the ruleset failed; the log counts failures. Apply again after the LAN is up. |
| Gatekeeper shows **Not enforcing** | Gatekeeper page; log `gatekeeper` / `gkd` "enforcement chains missing" | Its rules keep dropping — usually a script or add-on flushing the chains (2.9). Remove the conflict; the daemon repairs within ~30 s. |
| Gatekeeper shows **Arming** for minutes after boot | Log `gatekeeper` | Normal for the several-minute boot-stabilisation window; it arms when the bridge is up. If it never leaves Arming, read the log. |
| 46th+ approved device stays Pending (old images) | Log `gatekeeper: device list migrated …`; diag §14b | Upgrade to v2.6.3 or later; the list moves to `/jffs` (2.4). |
| "Internet only" device has no working internet | Gatekeeper; DHCP's advertised DNS | If your DNS server is on the LAN, it must itself be an approved (full) device in Gatekeeper (4.2). |
| Unknown device on a guest network gets a hung page instead of "awaiting approval" | Log `gatekeeper`; `SDN_FI` admit rule | Fixed in v2.6.5 (pending confirmation); requires an isolated SDN to reproduce. |
| Whole LAN lost the internet right after a Warden feed update | Log `rwarden`, `rwatch` canary CRITICAL | Fixed since v1.8.8 (private ranges are stripped); `rwatch` re-applies rules and logs if your LAN IP ever matches a block set. Check custom feeds for private ranges; they are stripped too. |
| Warden blocks total is large but the country table is near zero | Warden count bar (Countries / Threat feeds / Manual / Unclassified) | Not a fault: before v2.5.0 feeds were credited first. Now countries are evaluated first; expect a kink in history at that version. |
| Warden country tile is amber "N country list(s) empty" after a reboot | Warden; log `rwarden: cache restore for set …`; `ipset -t list rw_g_<cc>` | Press **Update feeds now**. v2.5.9 fixed the per-set cache replay; pending confirmation on the first boot after upgrading an old cache. |
| Router itself cannot reach feeds / DDNS / a VPN peer with Warden's self filter on | Log `REAPER-WARDEN-SELF`; `rwatch: FAILURE detected: warden-self-drop` | That is the feature reporting. The log names the destination; whitelist it or turn the self filter off. |
| Policy Routing dropdown is empty / a domain rule matches nothing | Log `reaper_pbr`; `ipset list rwfw_<list>` | Fixed in v2.5.9 (token and shared object layer). Check the list has resolved; lists fill from the router's own resolver, so a client on its own DNS or DoH does not feed them. |
| Some routing mark rules missing after a reboot | Log `rwatch: policy routing: N of M mark rule(s) live — re-applying` | Self-heals within two minutes (v2.6.9); no action needed unless the line repeats forever. |
| WireGuard rule shows "not supported yet — rule inactive" | Policy Routing page | You are on v2.6.1–v2.6.6; WireGuard targets arrived in v2.6.7. |
| LAN throughput dropped after adding a routing rule | Policy Routing rule chips "accel bypass: whole LAN"; log on apply | A destination-list or MAC rule to WireGuard bypasses acceleration for the LAN (4.4). Use a source rule, or an OpenVPN target. |
| IPv4 stopped working entirely, IPv6 fine, QoS Classful on | Log `hwqos: setqcfg qid N … REJECTED` / `class queues restored …`; QoS Diagnostics queues 1–5 | v2.6.0 makes the rebuild transactional. A `FATAL` line means even the bare recreate failed — report it with a diag. |
| Games/consoles cannot open ports or connect with UPnP on | Log `IGD desc` lines (which description the console fetched); Firewall Status exposure card | IGD:1 is advertised by default (v2.4.6) and the upstream "all traffic through UPnP" patch is reverted (v2.5.8). If you enabled IPv6 pinholes, IGD:2 is served — that configuration broke the PS5. |
| UPnP mappings stop working hours after boot | UPnP page vs actual forwarding | Fixed v2.3.5 (the daemon is genuinely restarted on firewall rebuilds). Do not "optimise" that restart away. |
| PPPoE set to 1500 runs at 1492 | `grep -i "up with MTU" /tmp/syslog.log` | `MTU 1492 (requested >1492; peer declined RFC 4638)` means your provider declined; nothing to fix on the router. Both MTU and MRU must be above 1492 (they move together). Not the LAN Jumbo Frame setting. |
| No internet after a router reboot until the ONT is power-cycled (PPPoE) | Log `rwatch` bounce line | v2.5.5 re-dials once after the 300 s boot grace when all three probes fail (`reaper_wanbounce_enable`, on by default). The tester capture during the fault is still owed. |
| Firmware page frozen during a flash | — | Since v2.3.3 the poll chain is one-shot and the overlay has a Close on errors. If an old image: wait for the router, then End Task the tab. |
| Mesh node shows a blank page with a cycling URL after flashing Reaper | Node's own firmware page | Fixed v2.4.6 (theming stands aside on a node). A node already stuck must be updated from the main router's AiMesh flow. |
| "Search for node" finds nothing | Log `aimesh:` drop-reason lines | The two silent gates are now logged; recent reports say discovery works. A new Reaper node must be factory-reset on this firmware first. |
| USB format "did nothing", log says "w/o tool" | Log `disk_format`; `/tmp/disk_format/<dev>.log` | NTFS/HFS+ dispatch fixed in v2.6.8 (pending confirmation). Prefer ext4 for a disk that stays in the router. |
| Traffic history gone after a reboot or flash | Long-Term Storage page; USB mounted? | Choose JFFS or USB (RAM is volatile). Since v2.1.5/v2.1.9 the collector waits for the USB store and never overwrites a database it did not load; `rtraf.db.prev` is the at-risk copy. |
| Devices page lists a Wi-Fi device as Wired | Devices | Fixed v1.9.4 (bridge table) and v2.4.2 (mesh clients); a wireless-backhaul *node* is fixed v2.5.9, pending confirmation on a real mesh. |
| Device names keep reverting | Devices; stock client list | Fixed v2.1.9 (three root causes). Existing duplicates self-heal on the first reboot. |
| Speed test dies partway through | Adaptive QoS → Internet Speed | Counter fixes in v2.4.5/v2.5.4; pending a multi-run confirmation. A genuine outage still fails on the real timeout. |
| Reaper settings import reports rejections | Log `reaper_cfg: settings imported: N flag(s), M list(s), K rejected` | The rejected entries failed the same validation as typing them; fix them on the page. Firewall/routing lists still need Apply + Keep. |
| Diag report tripwire says "review before sharing" | The report's ledger | Something still looked like a public address, MAC or e-mail. Read the file and redact by hand before attaching it. |
| Login loop or credential page rejects everything after a factory reset | — | Fixed v2.1.5 / v2.2.0 / v2.3.5 (the gate lives in the web server). Power-cycle and log in with the new credentials; `nvram set reaper_fbdone=1` over SSH as a last resort. |
| `logread` shows nothing | — | Expected on this platform. Use the System Log page or `/tmp/syslog.log`. |

---

## 7. Glossary

- **AQM (PI2)** — active queue management in the hardware traffic manager; drops or marks packets early so queues stay short. Drops rising while a class is held to its rate is the system working.
- **Accelerator / Runner / flow cache** — the Broadcom hardware forwarding path. Reaper's hardware QoS engines keep it on; Cake and Traditional QoS turn it off; a WireGuard Policy Routing rule can bypass it for some or all LAN traffic.
- **Apply and Keep / commit-confirm** — the two-step change on the Firewall and Policy Routing pages: changes go live at once and revert on their own unless you press Keep within the auto-revert timer (2.7).
- **Auto-revert timer** — 15–3600 seconds, default 60, never off; set on the Firewall Rules tab.
- **Egress default** — a per-device rule for traffic leaving toward the internet only (Firewall → Egress).
- **Fail-closed** — a Policy Routing rule whose tunnel is down *blocks* the traffic rather than letting it out the WAN.
- **FINDINGS** — the verdict block at the top of the diagnostics report.
- **Front chain (`REAPER_HOOK_*`)** — the single shared chain at the head of INPUT/FORWARD/OUTPUT into which Warden, Gatekeeper and the rules engine register, in that fixed order.
- **Gatekeeper** — device access control; states are Pending, Full access, Internet only, Guest (timed), Blocked.
- **Guest pass** — a timed (4/8/24/48 h) internet-only approval in Gatekeeper.
- **HW QoS Classful (type 11) / Hardware QoS (type 10)** — Reaper's two hardware QoS engines.
- **IGD:1 / IGD:2** — the two revisions of the UPnP gateway description. Reaper advertises IGD:1 by default; enabling IPv6 pinholes switches to IGD:2.
- **ipset** — kernel address sets; one lookup regardless of list size. Warden, the firewall objects and Policy Routing all use them.
- **/jffs** — the router's internal flash partition, always mounted; where Reaper's lists and Warden's cache live (2.4).
- **L4S** — an experimental ECN-marking congestion signal for capable flows; harmless if unsupported.
- **Long-term store** — the durable location (RAM / JFFS / USB) chosen on the Storage page for history datasets.
- **MCP / AI Advisor** — the optional read-only LAN-only Model Context Protocol server in the `_MCP` build; absent from `noMCP`.
- **MLO** — Wi-Fi 7 Multi-Link Operation; needs a cold power cycle to change (2.8).
- **Object / group / service / zone** — the named things Firewall rules refer to (4.1).
- **Policy Routing (PBR)** — rules that steer matched traffic to a VPN client, the WAN, or a block; they take precedence over VPN Director.
- **Pseudonym (`MAC-3`)** — a consistent stand-in for a real MAC inside one diagnostics report.
- **rchqd** — the opt-in passive channel-quality monitor.
- **RFC 4638 / baby jumbo** — the PPPoE extension that allows a 1500-byte MTU by widening the WAN port to 1508; requires provider support and both MTU and MRU above 1492.
- **rtrafd** — the Traffic Analyzer collector.
- **rwatch** — the health watchdog (every 5 minutes): WAN first-hop ping, loopback DNS, the Warden self-lockout canary, Policy Routing self-heal, hung-nvram reaping, the optional accelerator probe, the PPPoE stale-session re-dial; writes incident dumps on first failure.
- **SDN / Guest Network Pro** — ASUS's per-network profiles (guest, IoT, VLAN). Gatekeeper enforces on every one; the Traffic Analyzer labels each by name and VLAN.
- **Socket bind shim** — the on-by-default workaround for the closed nvram library's netlink defect (4.17).
- **Warden** — the threat-feed, country and manual IP blocking layer.
- **Zone policy** — the default action between two zones; the weakest statement in the firewall engine, overridden by Egress defaults and explicit rules.

---

## 8. Factory defaults, and what Reaper changes

"Factory default" means the value a setting takes on a **factory reset**, or on a first boot with
clean NVRAM. Every setting below can be changed afterwards from the GUI. This section exists so you
can tell *what the firmware chose for you* from *what you chose*, and put anything back.

To read the live value of any key over SSH: `nvram get <key>`.

### 8.1 Stock settings whose default Reaper changes

Fifteen ASUS/Merlin defaults ship with a different value under Reaper. Each is a deliberate choice,
not an accident, and each is reversible from the GUI.

| Setting | Stock | Reaper | Why |
|---|---|---|---|
| `wps_enable`, `wps_enable_x` | `1` | **`0`** | WPS is off out of the box. Its PIN method is broken by design and cannot be made safe. Turn it on in Wireless only if a device has no other pairing method. |
| `upnp_enable` | `1` | **`0`** | UPnP lets any LAN device open a hole in your firewall without asking. Enable it per WAN if you need console or game-server port mapping. |
| `upnp_min_port_ext` | `1` | **`1024`** | When UPnP is on, it may no longer map privileged ports. A compromised LAN device cannot claim port 22, 53 or 443. |
| `upnp_ssdp_interval` | `60` | **`900`** | SSDP announcements every 15 minutes instead of every minute. Far less multicast chatter, which is noticeable on Wi-Fi. |
| `firmware_check_enable` | `1` | **`0`** | The stock automatic update check phones ASUS. Reaper checks its own GitHub release manifest instead — see 4.14 and 9.1. |
| `ASUS_EULA`, `ASUS_NEW_EULA` | `0` | **`1`** | Pre-accepted, because the setup wizard that would have presented them was removed. Nothing is transmitted; this only stops the firmware blocking on a dialog that no longer exists. |
| `qos_default` | `3` | **`4`** | The catch-all class for unmatched traffic. Stock pointed at class 3, named "Downloads", so unclassified traffic — including game traffic, which is unmarked UDP — queued alongside bulk transfers. It now points at the class actually named "Default". |
| `qos_orates` | `80-100,10-100,…` | **`15-100,15-90,20-90,5-95,25-95,…`** | Per-class minimum and maximum rates. The stock profile committed effectively the whole link to class 1. Reaper's leaves headroom and keeps the committed total under 85% of your configured upload. |
| `qos_rulelist` | Web / HTTPS / File Transfer | **Conferencing, SIP, Game Console, Steam, BitTorrent, Web** | The starting classification rules. The stock set predates modern traffic; Reaper's recognises conferencing and game traffic, which is what people actually want prioritised. |
| `psc6g` | `0` | **`1`** | Advertise the 6 GHz Preferred Scanning Channel, so 6 GHz clients find the band quickly instead of scanning the whole range. |
| `smbd_simpler_naming` | `0` | **`1`** | USB shares are named after the volume rather than a generated string. |
| `v3_auth_type` | *(empty)* | **`SHA`** | SNMPv3 authentication defaults to SHA rather than nothing chosen. |
| `v3_priv_type` | *(empty)* | **`AES`** | SNMPv3 privacy defaults to AES. Both matter only if you enable SNMP at all. |

Reaper also **adds 72** NVRAM keys of its own (8.2) and **removes 23** belonging to features it
strips out — AiCloud and WebDAV (`enable_webdav`, `acc_webdavproxy`, `st_webdav_mode`), cloud sync
(`cloud_sync`, `enable_cloudsync`), and the share-link plumbing.

### 8.2 Reaper's own settings and their defaults

Sixty keys, grouped by the feature that owns them. **Almost everything ships off.** No Reaper
feature enforces anything until you turn it on. The exceptions are the two passive ones that only
observe — `rtraf_enable` and `rwatch_enable` — plus `reaper_wanbounce_enable`.

**Firewall engine** (4.1) — `reaper_fw_enable` `0`, `reaper_fw_active` `0`, `reaper_fw_armed` `0`,
`reaper_fw_confirm` `60`. The rule-store keys (`reaper_fw_rules`, `_obj`, `_grp`, `_svc`, `_zone`,
`_zpol`, `_nat`, `_edef`, `_err`) all start empty. `reaper_fw_confirm` is the safety timer: after
you apply a ruleset, the firewall reverts unless you confirm within 60 seconds, so a rule that locks
you out undoes itself.

**Warden** (4.3) — `rwarden_enable` `0`, `rwarden_dir` `in` (inbound only), `rwarden_reset` `off`,
`rwarden_log` `0`, `rwarden_self` `0`, `rwarden_stats_save` `1`. The list keys (`rwarden_feeds`,
`rwarden_geo`, `rwarden_allow`, `rwarden_ban`, `rwarden_cfeeds`, `rwarden_sched`) start empty, so a
freshly enabled Warden blocks nothing until you choose feeds or countries.

**Gatekeeper** (4.2) — `gk_enable` `0`, `gk_default` `0`, `gk_captive` `1`, `gk_notify` `1`,
`gk_guest_hours` `24`, `gk_rl` empty. `gk_default` `0` means a device Gatekeeper has never seen is
**blocked**, not allowed. That is deliberate, and it is why enabling Gatekeeper before populating
the device list will cut off new arrivals.

**Policy routing** (4.4) — `reaper_pbr_enable` `0`, `reaper_pbr_rulelist` empty.

**Traffic Analyzer** (4.7) — `rtraf_enable` **`1`** (on, because it only records), `rtraf_cap_gb`
`0` (no cap), `rtraf_path` and `rtraf_probe` empty.

**Long-term storage and export** (4.11) — `reaper_store` `ram`, `reaper_store_ds`
`dev,traf,watch`. On `ram`, history is lost at reboot; point it at USB to keep it. The exporter is
entirely off: `reaper_export_mode` empty, `reaper_export_interval` `300`,
`reaper_export_tlsverify` `1`, `reaper_export_maskmac` `0`, and all URL, token and metric keys
empty.

**Self-monitor** (4.13) — `rwatch_enable` **`1`**, `rwatch_iv` `5` minutes,
`reaper_wanbounce_enable` **`1`**. The WAN bounce fires only on a PPPoE link that has failed all
three reachability probes after the boot grace period.

**Connections and QoS diagnostics** — `rchq_enable` `0`.

**AI Advisor, MCP build only** (4.16) — `rmcp_port` `5199`, `rmcp_timeout` `60` minutes,
`rmcp_client` empty. There is deliberately **no enable key**: the Advisor is armed by a session file
in `/tmp`, so every reboot comes up dark.

**Miscellaneous** — `reaper_fbdone` `0` (the first-boot card is still to be shown),
`reaper_fwsig_override` `0` (firmware-manifest signature checking stays on).

### 8.3 What a factory reset actually restores

A factory reset clears NVRAM, so everything above returns to the value in the tables above. It does
**not** erase `/jffs`, which is where the firewall, Warden, Gatekeeper and policy-routing rule
stores live. For a genuinely clean box, format JFFS as well, from Administration.

The useful consequence: if you are resetting to clear a bad *setting*, your rules survive and you do
not have to rebuild them.

---

## 9. Present but inactive

Some stock ASUS pages are still inside the firmware image but are **not reachable from the menu**.
They are not hidden bugs, and they are not doing anything. They were left in place rather than
deleted because each still shares state or code with something Reaper does use. This section lists
them, so that finding one by typing its address does not look like a discovery.

### 9.1 The stock firmware-update page

`Advanced_FirmwareUpgrade_Content.asp` is present, and **absent from the menu**. Reaper's own
Firmware page (4.14) replaces it.

It is kept because the two share NVRAM state. Reaper's page reuses the stock update variables —
`webs_state_update`, `webs_state_info`, `webs_state_url`, `webs_state_flag`, `webs_state_error`,
`webs_state_upgrade`, `webs_state_sha` — rather than inventing parallel ones. The stock page is the
other reader of that state.

The automatic check it used to drive is off (`firmware_check_enable` `0`, see 8.1), because it
queried ASUS. Reaper checks its own GitHub release manifest instead, and verifies a signature over
it.

### 9.2 The AiProtection pages

Thirteen `AiProtection_*.asp` pages remain in the image — Home Security, Malicious Sites Blocking,
Intrusion Prevention, Infected Device Prevention, Web Protector, Content Filter, Ad Block, Key
Guard, and their mobile variants. **None is in the menu.**

The engine behind them is gone. AiProtection is a TrendMicro product: the router ships traffic
metadata to TrendMicro's cloud for classification, which is precisely the arrangement Reaper exists
to remove. The DPI engine that fed those pages is compiled out of the build, so the pages have
nothing left to talk to.

What replaces them, and what does not:

- **Malicious-site and threat blocking** — Warden (4.3), using public IP threat feeds and country
  blocks. It works on addresses rather than on inspected content, and it needs no cloud service.
- **Per-device access control** — Gatekeeper (4.2).
- **Content and keyword filtering** — the firewall's URL Filter and Keyword Filter tabs (4.1).
- **Deep packet inspection, and signature-based intrusion prevention** — **nothing replaces this.**
  It cannot be done locally at line rate on this hardware without a commercial signature feed. If
  that specific capability is what you need, Reaper is not the firmware for you. That is an honest
  trade, not an oversight.

### 9.3 Why they were not simply deleted

Removing a page means removing every reference to it: menu entries, help mappings, redirect targets,
and any shared NVRAM. Each removal is a chance to break something that still works, for no benefit a
user can see — an unreachable page costs a few kilobytes of flash and nothing else. They may go in a
later release, once the shared state is untangled. Until then they are inert, unreferenced, and safe
to ignore.
