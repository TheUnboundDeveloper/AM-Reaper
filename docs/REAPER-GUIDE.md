# Reaper — the owner's guide

> **Doc status:** current as of **v2.8.6** · 2026-08-27 <!--@stamp-->

**Applies to:** Reaper firmware, line `3006.102.8_Reaper_v<X>`, for the ASUS RT-BE96U (primary, hardware-validated) and the sibling RT-BE86U, RT-BE88U, GT-BE98, GT-BE98 Pro, and the newer RT-BE92U (BCM6765, experimental). This guide describes the feature set as of the v2.8.6 <!--@treever--> source tree. The newest *published* release may be behind that; where a feature is newer than the image you are running, the page simply will not be there yet. See [`CHANGELOG.md`](CHANGELOG.md) for what each version added and [`BACKLOG.md`](BACKLOG.md) for what is still pending confirmation.

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
   - 4.2 [Gatekeeper](#42-gatekeeper)
   - 4.3 [Warden](#43-warden)
   - 4.4 [Policy Routing](#44-policy-routing)
   - 4.5 [QoS (Traffic Manager)](#45-qos-traffic-manager)
   - 4.6 [QoS Diagnostics](#46-qos-diagnostics)
   - 4.7 [Traffic Analyzer](#47-traffic-analyzer)
   - 4.8 [Devices](#48-devices)
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

**What it is.** One page, eleven tabs: live chain state, the stock Asuswrt controls, and Reaper's own rules engine. The engine is **off by default**; nothing changes until you enable it. It adds policy *on top of* the stock firewall rather than replacing it, so Gatekeeper, Warden, SDN and the base rules keep working underneath. The per-tab reference behind each **?** button is [`FIREWALL-GUIDE.md`](FIREWALL-GUIDE.md); this section is the summary.

**When to use it.** When you want rules about *things* — "the TV may not reach the internet during work hours", "guests may not reach the LAN", "only my office may use this port forward" — without memorising addresses or writing iptables by hand. If all you need is "this device gets no internet", the Egress tab alone does it.

**The tabs, in order**

- **Status** — read-only: whether the base firewall and the Reaper engine are *actually* up, counts of rules, objects and zones loaded, which content filters are on, the state of Gatekeeper and Warden, and an **exposure** card listing what of yours is reachable from the internet right now (NAT, forwards, triggering, DMZ, UPnP with its advertised IGD version, the remote-admin port, SSH from the WAN). Check it after every Apply and after every reboot. The page no longer runs `iptables`, so auto-refresh is cheap; raw chains are still available over SSH.
- **General** — the stock master switch, DoS protection, WAN ping, logged packets, the WAN access allow-list for the router's own services, and the separate **IPv6 firewall** (IPv6 has no NAT; an inbound rule is the only thing between the internet and a LAN host).
- **Rules** — the engine. Each rule has a direction (**Inbound** into the router, **Forwarded** through it, **Outbound** from it), an action (Accept / Drop / Reject), an optional source and destination as zones or objects, an optional service, schedule (`Mon,Tue|09:00|17:00`), rate limit, and a log flag. Also here: **Enable the rules engine**, the **Auto-revert timer**, **Preview**, **Apply and confirm**, and the confirmation card.
- **Objects** — address objects (host or subnet, address range, MAC address, domain name, **Country (Warden)**), address groups, and service objects (protocol + ports).
- **Zones** — a zone names a set of interfaces (`br0` as `lan`, `tun+` as `vpn`); a **zone policy** sets the default between two zones.
- **Egress** — per-device internet defaults: pick an object, choose Drop/Reject, optionally schedule it. Anchored to the internet-facing side only, so the device can still reach the printer and NAS.
- **Forwards** — port forwards with a source restriction (including "only from this country") and a schedule; each forward installs its translation *and* the matching permission together. **Backup and restore** (Export / Import) of the whole firewall configuration as text lives here too.
- **Network Services**, **URL Filter**, **Keyword Filter** — the stock filters, in one place. The URL and keyword filters cannot see encrypted sites; for blocking that holds, use a domain-name object in a rule.
- **Logging** — which decisions go to the system log (off / Drop / Accept / Both) and the recent entries.

**Setting it up, step by step**

1. On **Objects**, define what you will refer to: `nas` = host `192.168.50.20`; `kids-tablet` = a MAC; `smb` = TCP `139,445`; `streaming` = a domain list (one per line, or paste a comma/space-separated list — up to about 1,900 characters per object; split larger lists). Country objects are not created here: add the country on the **Warden** page first, then point a Country (Warden) object at it so both features share one list.
2. On **Zones**, name your interfaces and set the broad policy (guest → lan: Drop).
3. On **Rules**, write the exceptions. First match wins; put specific exceptions above broad blocks. An allowlist is an ordered pair: *Accept `iot` → `vendor-cloud`* above *Drop `iot` → (empty)*. Leaving a source or destination empty means "anything".
4. Press **Preview** — it compiles the draft and shows the exact commands the router would run, generated by the same code that would apply them. Nothing is applied.
5. Press **Apply and confirm**, check you can still reach the router and that the things you meant to allow still work, then press **Keep these changes** before the timer ends (2.7).
6. On **Forwards**, press **Export** and keep the text somewhere safe.

Every list has **Modify**: the record loads back into the add-row, Add becomes Save, and saving replaces it in place.

**What to expect.** The master switch shows "Working…" and then the measured outcome — the engine sets a marker as its final act, only when its rules really went on, so a boot where the LAN was not ready yet reports as *inactive* rather than claiming success. Failures to load part of the ruleset are counted and reported; a partial load is distinguishable from "LAN not ready, will retry". Precedence within forwarded traffic is **explicit rule > Egress default > Zone policy**.

**Limits and gotchas**

- **Rate-limited rules are skipped** (and logged) when the kernel module is missing, never silently applied without the limit.
- **A named object that resolves to nothing produces no rule**, not a rule that matches everything — so a domain list that has not resolved yet fails to a missing rule, never to an unintended block. Domain lists are fed by every DNS answer the router's own resolver gives plus a 10-minute re-resolve; entries expire after an hour; members are saved to flash after each pass and replayed at boot. A device using its own DNS, or encrypted DNS, is invisible to them.
- **MAC objects work only as a source** on inbound or forwarded traffic.
- **Forwards bypass Zone policy by design.** Put a forwarded device in its own zone if you want it reachable but isolated.
- **Object names** are restricted to letters, digits and underscores; anything else is dropped and logged.
- A 40-domain object saves only from v2.6.9 (lists moved to `/jffs`); on older images the nvram 1 KB wall applied. The move is pending field confirmation.
- Deliberately not built: rule negation ("not"), because an empty field already means "any" and an ordered pair expresses an allowlist; a rule tracer is deferred.
- **Gatekeeper / Warden quick access.** The Status tab shows both layers' state and the Rules page links to them; the engine relies on the fixed layer order (Warden → Gatekeeper → rules engine), so an Accept rule here can no longer let a geo-blocked source or a quarantined device through (v2.6.2; pending metal confirmation).

### 4.2 Gatekeeper

**What it is.** Opt-in, default-deny **device access control** enforced on the router. When it is on, every device already on the network is approved automatically; from then on each new device is **held at the gate** — no internet, no access to your other devices — until you decide: **Approve** (full), **Internet only**, a timed **Guest pass**, or **Block**. Off by default. It is a second wall, not the first: a MAC address is identity, not proof, and someone who already has your Wi-Fi password could imitate an approved device. What it stops is rogue gadgets, shared-password guests, and anything plugged into an open port.

**When to use it.** Households and small offices where new devices should not get access simply by knowing the Wi-Fi password; IoT gear that should never see the LAN ("Internet only" is right for cameras, TVs and smart-home devices); visitors who need the internet for an evening.

**Setting it up**

1. Open **Gatekeeper**. Read the *How it works & honest limits* card.
2. Under **Settings → New devices**, choose **Quarantine until approved** (the default) or **Alert only (allow, notify)**. Set the **Guest pass length** (4, 8, 24 or 48 hours). Decide whether quarantined devices see the **waiting-room page** and whether to **notify on new device** (log and dashboard alert).
3. Switch it **on**. Every device the router already knows — its address table, DHCP leases and named-client list — is grandfathered in, so nothing you own breaks; this re-runs on every enable so a device that was asleep the first time is not stranded later.
4. Watch the **Pending approval** list. New arrivals appear the moment they join, with name, connection type and band, and a private-address flag. Choose a state per device; you can also change it from the **Devices** page's Access dropdown, which now reads **Pending** for an un-enrolled device.

**What to expect**

- The page shows **Enabled / Arming / Not enforcing / Off**. *Arming* means it is waiting for the network to come up after a boot and will arm itself; *Not enforcing — check the System Log* means its rules keep dropping and devices are **not** being held. It never reads "on" while silently off.
- A held device that opens a web page sees a themed **"Awaiting approval"** notice (shown automatically through the sign-in popup on phones and laptops) instead of a dead connection. That page is generated by the web server and stays in English.
- Enforcement self-heals within seconds if a stock service flushes the rules; the HTTPS admin page is always left reachable so you cannot be fenced out of the control that turns Gatekeeper off.
- **Internet-only** devices stay sealed from the LAN permanently, with exactly one carve-out: DNS (and ARP) to the resolver your DHCP advertises, if that resolver lives on the LAN (AdGuard/Pi-hole setups). The DNS server device itself must be an approved (full) device. Since v2.6.2 the block also covers routes to *other* networks (main LAN and every SDN, enumerated), and since v2.6.5 IPv6 global addresses, rebuilt when the delegated prefix changes.
- **Multi-network (Guest Network Pro / SDN).** Enforcement follows discovery onto every network the router runs. Creating, editing or deleting an SDN re-applies Gatekeeper on every bridge immediately (logged), and the watcher re-checks every 30 seconds. The waiting-room page works on an isolated SDN (*Access Intranet* off) for an *unknown* device only; an approved device on that network still cannot reach the router's pages, and the admin escape hatch remains main-LAN only — that is what the Access Intranet switch means. Devices on guest networks get their hostnames. All of the v2.6.2–v2.6.5 multi-network work is pending confirmation on a router with an SDN.
- **Capacity.** The device list lives at `/jffs/gatekeeper/rl` (2.4). The old 45-device ceiling is gone: tested to 300, and the daemon's and Devices backend's tables are sized for **512** devices. Existing lists migrate at first boot; a later write failure is logged, never swallowed.

**Limits and gotchas**

- Phones using a rotating private address reappear as new devices; the pending list flags them.
- A settings backup (nvram) no longer includes the Gatekeeper list, and a factory reset clears it — export from the Storage page (2.5).
- Before v2.5.0, Block and quarantine were only enforced on the main LAN; that is fixed, and a quarantined device on a guest network now also gets the waiting page.
- The "grandfather" step refuses to overwrite its list if the list is ever too large to load (v2.5.7) and logs instead.

### 4.3 Warden

**What it is.** An opt-in **threat and geo firewall**: it drops traffic to and from known-malicious IP ranges (public reputation feeds), selected countries, and addresses you specify, enforced in-kernel with ipset across IPv4 and IPv6 at near-zero overhead. Your LAN, established connections and whitelist are always matched first and exempt, so it cannot lock you out. **Default OFF.** It is a noise-reduction layer, not a complete defence: a VPN or proxy changes an address's apparent country, so use it to shrink exposure, not as a sole control.

**When to use it.** Any router with a public WAN address that you would like to stop answering the constant background scanning; households that want to refuse whole countries they never talk to; anyone who keeps their own blocklist.

**Setting it up**

1. On **Warden**, tick the **threat feeds** you want: FireHOL Level 1, Feodo Tracker (botnet C2), Spamhaus DROP, DShield top attackers. They merge into one de-duplicated set, so overlapping feeds never double-block or slow matching — and FireHOL Level 1 already includes Spamhaus DROP, DShield and Feodo, so ticking those alongside it is redundant (Spamhaus still adds its IPv6 list).
2. Optionally add up to **8 custom feeds**: a name, an HTTPS list URL, and an optional IPv6 list URL. HTTPS only; the address may not contain quotes, spaces or `@`; the router follows no redirect to plain HTTP and caps the download size. Private, loopback and reserved ranges are stripped from *every* list before it is loaded, so a careless list cannot blackhole your own network.
3. Choose **countries** from the searchable checklist (source: ipdeny, updated with the feeds). Review the list before enabling: blocking a country you depend on (a VPN exit, a CDN) can cut off services.
4. Choose the **direction**: **Inbound only** protects the router and blocks unsolicited hits; **Both directions** also stops LAN devices *reaching* flagged addresses. ("Outbound only" was removed in v2.5.0 because it produced identical rules to Both.)
5. Add any **manual block list** entries and **whitelist** entries (one IPv4/IPv6 address or CIDR per line). Invalid entries are refused on save with a message naming them.
6. Decide on **Log dropped packets** (syslog prefix `REAPER-WARDEN`; useful for tuning, noisy if left on), the **block statistics** options (save to flash; reset interval Never / 24 Hours / 7 Days / 1 Month / 3 Months), and whether to **Also filter the router itself** (see below).
7. **Save & Apply**. Press **Update feeds now** for the first fetch; afterwards feeds refresh on the schedule set in Tools → Other Settings (default 04:30 daily).

**What to expect**

- The status card shows **Enforcing** or **Disabled**, the last feed update, feeds enabled, and **Countries blocked** — with an amber *N country list(s) empty* warning if a selected country has no addresses loaded. The count bar beneath shows **Countries / Threat feeds / Manual blocks / Unclassified** and **Prefixes loaded**.
- **Blocked hits** and **Top blocked countries** (refreshed every 30 s). Countries are evaluated *before* the feeds since v2.5.0, so per-country counts are real and the feed count carries only what no country matched; totals are saved to internal flash every 15 minutes and on every path that would otherwise lose them, so they survive reboots, firewall rebuilds and upgrades. Outbound blocks have their own log label and counter.
- Feeds are cached to `/jffs`; a router that boots with no internet still enforces the last download. If `/jffs` is off or read-only, a banner says protection is live but not persistent.
- Blocking a single address severs its live connections immediately; a newly blocked address is dropped at once because the hardware flow cache is flushed.
- **Also filter the router itself** (off by default) applies the same blocking to connections the router starts. It cannot lock you out — the web interface and SSH stay reachable — but it *can* stop the router reaching feed updates, DDNS or a VPN peer if a list happens to cover them; DNS resolvers and time servers are exempted automatically. Blocks here always go to the system log (`REAPER-WARDEN-SELF`) and the watchdog reports them as `warden-self-drop`, which is the feature reporting, not a fault. Malware with full control of the router can remove these rules, so treat it as a speed bump and a detection signal.

**Limits and gotchas**

- The threat and country sets are created with an explicit cap of 524,288 entries; the entry count against that cap is not yet shown in the UI (backlog).
- Eight custom feeds at the default timeouts can add about 16 minutes to an update window; a per-feed timeout is still owed.
- North Korea publishes no IPv6 zone; the nightly update no longer logs a failed fetch for it (v2.6.1).
- The country-list cache is replayed per set, members only, and an empty live set never overwrites a good cache entry (v2.5.9). This fixed country lists coming up empty after a reboot; pending reporter confirmation on the first boot after upgrading from an older cache.
- Turning Warden off resets its counters.

### 4.4 Policy Routing

**What it is.** A page in the VPN menu next to VPN Director that decides *which traffic* uses *which path* — an OpenVPN client, a WireGuard client, the plain WAN, or nowhere — by a rule you write. It adds the piece VPN Director lacks: rules keyed on a named **Firewall object or domain list** (destination), or on a **device by IP/CIDR or MAC** (source). A Policy Routing rule **wins** over a VPN Director rule for the same traffic, so you can "tunnel everything, except send this one service straight out the WAN". Built entirely from a firewall mark plus a routing-policy rule; it never dials a tunnel or changes a VPN's settings. Off by default.

**Note:** the per-page reference [`VPN-ROUTING-GUIDE.md`](VPN-ROUTING-GUIDE.md) is current as of v2.6.7+ — it covers WireGuard targets, IPv6, and apply-and-confirm with the auto-revert countdown.

**When to use it.** Routing a *set of sites* through a tunnel; carving an exception out of a full-tunnel VPN; forcing one device through a VPN and **blocking** it if the tunnel drops; a hard "this device goes nowhere". If you only need plain source routing without those properties, VPN Director alone is fine.

**Setting it up**

1. On **Policy Routing**, build any **Domain lists** you need in the card at the bottom: a name and the domains (one per line, or paste a list). These are Firewall objects of type *Domain name*; the Firewall page sees the same lists. Example: `streaming` = `netflix.com, nflxvideo.net, nflximg.net`. Address, MAC and country objects are still created on the Firewall page and simply appear in the dropdown.
2. Add a rule: a description, **Match by** — *Domain list / object (destination)*, *Device by IP / CIDR (source)* (one or more addresses or CIDRs, IPv4 or IPv6, comma-separated or one per line, up to 64), or *Device by MAC (source)* — and a **Target**: an OpenVPN client, a WireGuard client, **Out the WAN (VPN bypass)**, or **Block**. Each rule has its own enable checkbox and a **Modify** button.
3. Turn on **Enable policy routing**, then **Apply**. Rules go live at once and the confirmation card appears; press **Keep** within the auto-revert timer (set on the Firewall page) or the previous rules come back (2.7).

**What to expect**

- Rules read top to bottom, first match wins. Put "reach this site directly" *above* "send this device to the tunnel".
- **Fail-closed.** A rule targeting a VPN client blocks the matched traffic while that tunnel is down; it is never leaked out the WAN. If you want "use the tunnel when up, otherwise direct", that is a WAN rule, not a VPN rule. A WireGuard rule whose client is switched off is marked *client not enabled — traffic blocked*.
- **IPv6 is covered.** A destination list matches its IPv6 addresses, a MAC rule follows the device on both families, and a source rule may name an IPv6 prefix. If the chosen tunnel carries no IPv6, the selected IPv6 traffic is blocked rather than leaked around it.
- Domain lists are refreshed every 10 minutes, fed live by dnsmasq answers, saved to flash and replayed at boot; they are built whether or not the Firewall engine is enabled. A rule whose set was a moment late at boot is re-applied by `rwatch` (logged, at most every two minutes).
- The rule list lives on `/jffs` (2.4); twenty rules and more save.

**Limits and gotchas**

- **WireGuard costs hardware acceleration.** The traffic accelerator does not honour a routing rule whose exit is a WireGuard tunnel, so Policy Routing does what VPN Director does and tells the accelerator to leave the affected flows alone. A **source** rule bypasses only that address (*accel bypass: this source*). A **destination-list or MAC** rule must bypass the **whole LAN** (*accel bypass: whole LAN*) — LAN traffic loses hardware acceleration while such a rule exists. The page says so on the rule and the log says so on every apply. Entries VPN Director or the WireGuard server placed are never removed.
- Protocol/port matching is not offered.
- All of v2.6.7 (WireGuard targets, IPv6, apply-and-confirm, the `/jffs` move) and the v2.6.9 address lists are pending on-metal confirmation; the WireGuard and IPv6 legs need a WireGuard client and an IPv6 line to test.
- A list that has not resolved yet, or an emptied group, produces no rule rather than a rule that matches everything.
- CDNs change: when a service starts using a domain you did not list, the traffic is not matched. Come back and Modify the list.

### 4.5 QoS (Traffic Manager)

**What it is.** The Reaper QoS page offers five modes. Two are Reaper's own hardware engines, which shape in the Broadcom traffic manager **with the NAT/flow accelerator left on** — the thing ASUS never shipped:

| Mode | What it does | Accelerator |
|---|---|---|
| **HW QoS Classful** (type 11) — *recommended* | Five strict-priority classes with guaranteed minimums and per-class ceilings, hardware PI2 AQM on every queue, a download ingress policer and Wi-Fi WMM stamping. | On |
| **Hardware QoS** (type 10) | A single shaped upload queue plus AQM. The simplest bufferbloat fix, no classes. | On |
| **Cake** | Software shaper with the best *download* control; one CPU core does all shaping. Fine below about 1 Gb/s. | Off |
| **Traditional** | The classic software engine. | Off |
| **Bandwidth Limiter** | Hard per-device caps (up to 32 devices, both directions), edited on this page. Not bufferbloat control. | — |

**When to use it.** Any line where upload saturation makes calls stutter or games lag; the classful engine when you want calls and games served ahead of downloads; Cake only if download bufferbloat is your main problem and your line is under ~1 Gb/s; the Bandwidth Limiter for capping guests' or children's devices.

**Setting it up (HW QoS Classful)**

1. Run a few speed tests at a quiet hour. Take the **lowest consistent upload** and enter **90–95 % of it** as the Upload figure; enter your **measured download** as the Download figure (the router keeps ~10 % headroom on the download policer automatically — do not do that maths yourself).
2. Pick **HW QoS Classful**. Changing mode (or turning QoS on) **reboots the router** so the accelerator can be reconfigured; edits within a mode apply live.
3. The classes ship as a measured profile: **Web/VoIP**, **Gaming**, **Streaming**, **Downloads**, **Default**, with starter rules for conferencing, SIP, game consoles, Steam, BitTorrent and web traffic. Reorder with move up/down; the **top row is served first**. Set **Min %** (a guaranteed floor under load; mins must total ≤ 100 %) and **Ceiling %** (the most a class may ever take; never give the top class 100 %, since its ceiling is what protects everyone below it). Suggested setups are in the page's FAQ.
4. Leave the **Aggregate cap (port shaper)** on. Optionally enable **Guaranteed minimums**, **Trust DSCP marking** (off by default because any LAN host can mark its own packets), **L4S marking** (experimental), and **Wi-Fi downstream priority (WMM)** (opt-in; lift-only).
5. **Apply**.

**What to expect.** Saturate the upload with a large backup and watch the live columns: the bulk class pins near its ceiling, its drop counter ticks up (PI2 holding it to rate — that is the system working), and a simultaneous call or speed test stays responsive. If nothing changes, your upload figure is above what the line really delivers. Unmatched traffic lands in the class named **Default**. The Traffic Analyzer's "By QoS class" chart shows **upload only**, because the hardware engine shapes upload only.

**Limits and gotchas**

- **Strict priority only.** The per-class "Weighted (WRR)" option was removed in v2.5.4 because the hardware's egress scheduler cannot create a weighted queue (a closed-driver limit). The page describes classes as what they are. Any text on the page that still mentions a weighted pool refers to that removed option.
- The classes were being served in **inverted priority order** until v2.5.4; the fix is confirmed at the queue-configuration level on the RT-BE96U, and the drain behaviour under sustained classified load is still owed a test.
- On a **GT-BE98**, the v2.5.4 queue rebuild could be rejected by the traffic manager, taking all IPv4 off the air while IPv6 still worked (v2.5.4–v2.5.9). v2.6.0 made the rebuild transactional — on any rejection the queues are restored to the stock layout and a `hwqos` syslog line says the priority correction was not applied. Worst case is now the old priority order, never no internet. Pending reporter confirmation.
- Rules that classify by **transferred bytes** cannot be hardware-offloaded and put long flows in the wrong class; the page warns about them. Match on port, protocol, IP or MAC instead.
- With empty bandwidth fields the engine behaves as QoS-off rather than reclassifying without a shaper.
- Cake mode filters redundant upload ACKs and targets a 50 ms base RTT (tunable as `qos_cake_rtt`).

### 4.6 QoS Diagnostics

**What it is.** A tab to the right of QoS under Traffic Manager: a live view of the hardware traffic manager (the Runner/XRDP egress scheduler) — per-queue occupancy, scheduler discipline, drops per second (tail + AQM combined), shaper rate and configured size, an *estimated* delay (backlog ÷ shaper rate; the hardware has no direct latency counter), live trend graphs and a port selector for the WAN-upload and LAN-download schedulers.

**When to use it.** To verify that shaping is engaging, to see which queue is dropping under load, or to confirm after a firmware upgrade that the five class queues exist (the GT-BE98 IPv4 incident in 4.5 showed up here as queues that were simply gone).

**What to expect.** Fast polling (250–500 ms) runs only while the page is open. The view adapts to your mode: a single shaped queue under Hardware QoS, the full scheduler under HW Classful; "No egress traffic-manager data" means QoS or the accelerator is not active. Occupancy reads 0 on an idle link and fills under load. Counters are 32-bit and wrap about every 15 seconds at ~2 Gb/s; a wrap is discarded rather than drawn as a spike. Trends fill from the left and flow smoothly.

### 4.7 Traffic Analyzer

**What it is.** A native bandwidth and usage page driven by the `rtrafd` collector: live WAN throughput with an optional latency trace, per-QoS-class upload, per-network totals (main LAN, guest and each SDN, labelled with the network's name and VLAN), top devices for the window, live top talkers by destination-port bucket, and a monthly data cap. Windows: **Live** (100 ms, 1 s, 10 s, 30 s), **24 hours**, **14 days**, **1 year**, **By month**. The collector adds no listening ports; it only reads local counters.

**When to use it.** To see who is using the line and when, to confirm QoS classes are receiving traffic, and to keep an eye on a metered connection.

**Setting it up**

1. On the page's **Settings** panel, turn on **Collect traffic history**. Without it the realtime interface monitor still works, but there is no history or per-device accounting.
2. **History storage** is a read-only pointer to the Long-Term Storage page (4.11): choose RAM, JFFS or USB there. Anything longer than the live view needs JFFS or USB to outlast a reboot.
3. Optionally set a **WAN latency probe** target (a single ping per sample; blank = nothing is sent) and a **Monthly data cap** in GB (a warning is logged at 80 % and 100 %; nothing is cut off).

**What to expect**

- Per-device numbers come from the kernel's connection-tracking table, which already includes bytes the hardware accelerator forwarded, so offloaded flows are counted. Both **IPv4 and IPv6** are attributed per device (from v2.4.4), keyed on MAC so a dual-stack device is one row; the router's own traffic is a hidden **Router** bucket so By-Network + clients add up to the WAN line. Inbound connections (port forwards, UPnP) are attributed to the device that received them.
- Offline devices keep the names you gave them. The graphs draw on the display's refresh and place readings by arrival time, so they flow rather than step.
- A loss of polls flips the status pill to amber **No response** rather than drawing zeros.

**Limits and gotchas**

- **By QoS class** is upload-only and only populates under HW QoS Classful.
- A device with no IPv4 traffic shows a blank address until the network map names it.
- A device-name mis-attribution is possible only when a DHCP lease is reused by an offline device's IP; a negligible byte undercount when a duplicate row is folded away. Both are documented trade-offs.
- The IPv6 per-device attribution and the "1 year" totals for IPv6 devices on a USB store are pending field confirmation.

### 4.8 Devices

**What it is.** The **Device Identity Manager**: one page, between USB Application and System Info, that correlates everything ASUS scatters about a device — its custom name, DHCP reservation, Gatekeeper access state and live presence (leases + address table + Wi-Fi association, band, last seen, 24-hour traffic) — per MAC. It is the lens, not a second engine: every action writes to the same stores the rest of the firmware reads, and access states are enforced by Gatekeeper.

**When to use it.** Naming devices (the name propagates to every page: client list, Gatekeeper, Traffic, Connections, the DHCP-leases log), pinning addresses, checking who is online, spotting reservation problems, and changing a device's Gatekeeper state without leaving the page.

**How to use it**

- **Rename** inline — click the name. Your custom name wins everywhere over the device's self-reported hostname.
- **Pin IP** opens a pool-aware reservation dialog that recommends an address *outside* the DHCP pool (keeps the pool free for new devices; the device moves at its next lease renewal) or lets you keep the current address inside it. **Widen pool** extends the DHCP range to the usable subnet when it is tight.
- The **Access** dropdown sets Gatekeeper state (**Pending** for an un-enrolled device; Full access, Internet only, Guest, Blocked).
- The **Network Ledger** card flags what needs attention: pool exhausted or running low, reservation store nearly full (an nvram limit), reservations outside the current subnet (dnsmasq ignores them), duplicate reservations, Wi-Fi-associated devices that cannot get an address.
- Filter chips (All, Online, Offline, Unnamed, Reserved, Randomized, Blocked) and search by name, MAC or IP.
- **Export list** saves the whole inventory as CSV, JSON or HTML — **unsanitised**; keep it private.

**What to expect.** Wired versus wireless is decided from the LAN bridge's forwarding table, not a guess, so Wi-Fi 7 / 6 GHz clients are no longer mislabelled Wired. A Wi-Fi 7 **MLO** device appears as one row showing its combined bands (`MLO · 5+6 GHz`), with its affiliated links labelled rather than flagged as problems. Devices behind an **AiMesh node** are reported as Wi-Fi on their real band; the node itself gets an **AiMesh Node** chip and shows its backhaul band (or Wired if cabled), and the phantom lease-less "device" its backhaul radio used to add is folded away (pending confirmation on a real mesh). First-seen stamping waits for the clock to be set, so "first seen 961 days ago" no longer happens.

**Limits and gotchas.** A phone using a private (randomized) address reappears as a new MAC until that feature is turned off for your network. The reservation store is nvram-limited.

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
