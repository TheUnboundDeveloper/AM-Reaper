# Reaper — the owner's guide

> **Doc status:** current as of **v3.8.5** · 2026-11-27 <!--@stamp-->

**Applies to:** Reaper firmware for the ASUS RT-BE96U (primary model) and the sibling RT-BE86U, RT-BE88U, GT-BE98, GT-BE98 Pro, GT-BE19000, ZenWiFi BQ16 and ZenWiFi BQ16 Pro, in two lines with the same Reaper version: `3006.102.10_Reaper_v<X>` (RT-BE96U, RT-BE86U, RT-BE88U, GT-BE98 Pro) and `3006.102.8_Reaper_v<X>` (GT-BE98, GT-BE19000, BQ16, BQ16 Pro; see 2.1). This guide describes the feature set as of the v3.8.5 <!--@treever--> source tree. The newest *published* release may be behind that; where a feature is newer than the image you are running, the page simply will not be there yet. See [`CHANGELOG.md`](CHANGELOG.md) for what each version added and [`BACKLOG.md`](BACKLOG.md) for what is still pending confirmation.

Reaper is based on **Asuswrt-Merlin by Eric "Merlin" Sauvageau**. Every line of Reaper is a patch on top of that work; the base firmware, most of its features, and most of what is good about the result are his. Reaper is an independent fork. Neither ASUS nor the Asuswrt-Merlin project has reviewed, approved or endorsed it, and neither should be contacted about it (see [Where to report issues](#214-where-to-report-issues)).

This guide is written for someone who will install and run the firmware: technically literate, not a developer. Everything in it comes from the project's own documentation, changelog, backlog and the text on the pages themselves.

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
   - 2.3 [First boot: one banner, one box](#23-first-boot-one-banner-one-box)
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
     - 4.1.1a [Rule Status](#411a-rule-status)
     - 4.1.1b [Security Review](#411b-security-review)
     - 4.1.2 [General](#412-general)
     - 4.1.3 [Rules](#413-rules)
     - 4.1.4 [Objects](#414-objects)
     - 4.1.5 [Zones](#415-zones)
     - 4.1.6 [Egress](#416-egress)
     - 4.1.7 [Forwards](#417-forwards)
     - 4.1.8 [Service Intercept](#418-service-intercept)
     - 4.1.9 [Network Services](#419-network-services)
     - 4.1.10 [URL Filter](#4110-url-filter)
     - 4.1.11 [Keyword Filter](#4111-keyword-filter)
     - 4.1.12 [Logging](#4112-logging)
     - 4.1.13 [Limits, and things deliberately not built](#4113-limits-and-things-deliberately-not-built)
   - 4.2 [Gatekeeper](#42-gatekeeper)
     - 4.2.1 [The four states](#421-the-four-states)
     - 4.2.2 [Turning it on safely](#422-turning-it-on-safely)
     - 4.2.3 [How it enforces, and the way back in](#423-how-it-enforces-and-the-way-back-in)
     - 4.2.4 [Internet-only, and the LAN DNS trap](#424-internet-only-and-the-lan-dns-trap)
     - 4.2.5 [Guest networks](#425-guest-networks)
     - 4.2.6 [Reading the status](#426-reading-the-status)
     - 4.2.7 [Examples](#427-examples)
     - 4.2.8 [Limits and gotchas](#428-limits-and-gotchas)
   - 4.3 [Bastion](#43-bastion)
     - 4.3.1 [Warden](#431-warden)
     - 4.3.2 [Dreadwatch](#432-dreadwatch)
     - 4.3.3 [Wallguard](#433-wallguard)
     - 4.3.4 [Encrypted DNS](#434-encrypted-dns)
   - 4.4 [Policy Routing](#44-policy-routing)
     - 4.4.1 [How it works](#441-how-it-works)
     - 4.4.2 [The page](#442-the-page)
     - 4.4.3 [What a rule matches](#443-what-a-rule-matches)
     - 4.4.4 [Domain lists](#444-domain-lists)
     - 4.4.4a [ASN lists and country lists](#444a-asn-lists-and-country-lists)
     - 4.4.5 [Where a rule sends traffic](#445-where-a-rule-sends-traffic)
     - 4.4.6 [Order and precedence](#446-order-and-precedence)
     - 4.4.7 [Fail-closed or fail-open: the Killswitch decides](#447-fail-closed-or-fail-open-the-killswitch-decides)
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
   - 4.10 [Wireless Quality and Wi-Fi Settings (all bands)](#410-wireless-quality-and-wi-fi-settings-all-bands)
     - 4.10.1 [Preamble puncturing: what it is](#4101-preamble-puncturing-what-it-is)
     - 4.10.2 [The parts and how they connect](#4102-the-parts-and-how-they-connect)
     - 4.10.3 [The four modes and what each puts in effect](#4103-the-four-modes-and-what-each-puts-in-effect)
     - 4.10.4 [Dynamic: sensitivity presets](#4104-dynamic-sensitivity-presets)
     - 4.10.5 [Dynamic: monitoring sources](#4105-dynamic-monitoring-sources)
     - 4.10.6 [What the controller measures, and what it costs](#4106-what-the-controller-measures-and-what-it-costs)
     - 4.10.7 [What keeps clients connected](#4107-what-keeps-clients-connected)
     - 4.10.8 [What each client sees](#4108-what-each-client-sees)
     - 4.10.9 [Minimum width on Auto](#4109-minimum-width-on-auto)
     - 4.10.10 [Interference mitigation (all bands)](#41010-interference-mitigation-all-bands)
     - 4.10.11 [Driver functions Reaper leaves alone](#41011-driver-functions-reaper-leaves-alone)
     - 4.10.12 [Where to look](#41012-where-to-look)
     - 4.10.13 [AiMesh backhaul parking](#41013-aimesh-backhaul-parking)
   - 4.11 [Long-Term Storage and Data Export](#411-long-term-storage-and-data-export)
   - 4.12 [USB Disks](#412-usb-disks)
   - 4.13 [Diagnostics](#413-diagnostics)
   - 4.14 [Firmware](#414-firmware)
   - 4.14a [Resolver health check](#414a-resolver-health-check-administration--dns-failover-v311)
   - 4.14b [Device names across networks](#414b-device-names-across-networks-administration--dns-failover)
   - 4.15 [About](#415-about)
   - 4.16 [AI Advisor (MCP build only)](#416-ai-advisor-mcp-build-only)
   - 4.17 [Administration → Tweaks: the Reaper setting](#417-administration--tweaks-the-reaper-setting)
   - 4.18 [Site Survey (Network Tools)](#418-site-survey-network-tools)
   - 4.19 [WAN Ports](#419-wan-ports)
   - 4.20 [VPN](#420-vpn)
     - 4.20.1 [VPN Status](#4201-vpn-status)
     - 4.20.2 [VPN Director](#4202-vpn-director)
     - 4.20.3 [Policy Routing](#4203-policy-routing)
     - 4.20.4 [VPN Server](#4204-vpn-server)
     - 4.20.5 [VPN Client](#4205-vpn-client)
     - 4.20.6 [Tor](#4206-tor)
   - 4.21 [Network: guest networks, VLANs and the Guest Portal](#421-network-guest-networks-vlans-and-the-guest-portal)
     - 4.21.1 [The page and the network types](#4211-the-page-and-the-network-types)
     - 4.21.2 [The network editor: every setting](#4212-the-network-editor-every-setting)
     - 4.21.3 [What a guest network may reach (guest isolation)](#4213-what-a-guest-network-may-reach-guest-isolation)
     - 4.21.4 [A network that uses a VPN](#4214-a-network-that-uses-a-vpn)
     - 4.21.5 [IoT networks and the Default IoT Network](#4215-iot-networks-and-the-default-iot-network)
     - 4.21.6 [DNS for a network](#4216-dns-for-a-network)
     - 4.21.7 [The Guest Portal](#4217-the-guest-portal)
     - 4.21.8 [mDNS across networks](#4218-mdns-across-networks)
     - 4.21.9 [How the other features treat guest networks](#4219-how-the-other-features-treat-guest-networks)
     - 4.21.10 [Examples](#42110-examples)
     - 4.21.11 [Limits and gotchas](#42111-limits-and-gotchas)
     - 4.21.12 [Several changes, one Wi-Fi restart](#42112-several-changes-one-wi-fi-restart)
   - 4.22 [LAN](#422-lan)
     - 4.22.1 [LAN IP and DHCP server](#4221-lan-ip-and-dhcp-server)
     - 4.22.2 [DNS](#4222-dns)
     - 4.22.3 [IPTV](#4223-iptv)
     - 4.22.4 [VLAN](#4224-vlan)
   - 4.23 [WAN](#423-wan)
     - 4.23.1 [Internet Connection](#4231-internet-connection)
     - 4.23.2 [NAT and Port Forwarding](#4232-nat-and-port-forwarding)
     - 4.23.3 [DDNS](#4233-ddns)
   - 4.24 [IPv6](#424-ipv6)
   - 4.25 [Wireless settings](#425-wireless-settings)
     - 4.25.1 [Wi-Fi Settings](#4251-wi-fi-settings)
     - 4.25.2 [WPS](#4252-wps)
     - 4.25.3 [WDS](#4253-wds)
     - 4.25.4 [Wireless MAC Filter](#4254-wireless-mac-filter)
     - 4.25.5 [RADIUS Setting](#4255-radius-setting)
     - 4.25.6 [Roaming Block List](#4256-roaming-block-list)
     - 4.25.7 [MLO](#4257-mlo)
     - 4.25.8 [Smart Connect Rule](#4258-smart-connect-rule)
   - 4.26 [System Log](#426-system-log)
     - 4.26.1 [General Log](#4261-general-log)
     - 4.26.2 [Wireless Log](#4262-wireless-log)
     - 4.26.3 [DHCP leases](#4263-dhcp-leases)
     - 4.26.4 [IPv6](#4264-ipv6)
     - 4.26.5 [Routing Table](#4265-routing-table)
     - 4.26.6 [Port Forwarding](#4266-port-forwarding)
     - 4.26.7 [Connections and Long-Term Storage](#4267-connections-and-long-term-storage)
   - 4.27 [Administration](#427-administration)
     - 4.27.1 [System: how the page works](#4271-system-how-the-page-works)
     - 4.27.2 [System > Login and access](#4272-system--login-and-access)
     - 4.27.3 [System > SSH](#4273-system--ssh)
     - 4.27.4 [System > Time and NTP](#4274-system--time-and-ntp)
     - 4.27.5 [System > Hardware](#4275-system--hardware)
     - 4.27.6 [System > Maintenance](#4276-system--maintenance)
     - 4.27.7 [System > Accessibility](#4277-system--accessibility)
     - 4.27.8 [Backup & Restore](#4278-backup--restore)
     - 4.27.9 [SNMP](#4279-snmp)
     - 4.27.10 [Tweaks: the other settings](#42710-tweaks-the-other-settings)
     - 4.27.11 [System Information](#42711-system-information)
     - 4.27.12 [The security banner](#42712-the-security-banner)
   - 4.28 [USB Application](#428-usb-application)
     - 4.28.1 [The USB Application page](#4281-the-usb-application-page)
     - 4.28.2 [Accounts and folder rights (Samba and FTP)](#4282-accounts-and-folder-rights-samba-and-ftp)
     - 4.28.3 [Network Place (Samba) Share](#4283-network-place-samba-share)
     - 4.28.4 [FTP Share](#4284-ftp-share)
     - 4.28.5 [Media Server](#4285-media-server)
     - 4.28.6 [NFS Exports](#4286-nfs-exports)
     - 4.28.7 [A USB volume for the long-term store](#4287-a-usb-volume-for-the-long-term-store)
   - 4.29 [Network Tools](#429-network-tools)
     - 4.29.1 [Network Analysis](#4291-network-analysis)
     - 4.29.2 [Netstat](#4292-netstat)
     - 4.29.3 [Wake on LAN](#4293-wake-on-lan)
     - 4.29.4 [Smart Connect Rule and Site Survey](#4294-smart-connect-rule-and-site-survey)
   - 4.30 [Parental Controls: Time Scheduling](#430-parental-controls-time-scheduling)
   - 4.31 [Other menus](#431-other-menus)
     - 4.31.1 [AiMesh](#4311-aimesh)
     - 4.31.2 [Traffic Manager > Internet Speed](#4312-traffic-manager--internet-speed)
     - 4.31.3 [Network Printer Server](#4313-network-printer-server)
     - 4.31.4 [Time Machine](#4314-time-machine)
5. [Efficiency and good practice](#5-efficiency-and-good-practice)
6. [Troubleshooting quick table](#6-troubleshooting-quick-table)
7. [Glossary](#7-glossary)
8. [Factory defaults, and what Reaper changes](#8-factory-defaults-and-what-reaper-changes)
   - 8.1 [Stock settings whose default Reaper changes](#81-stock-settings-whose-default-reaper-changes)
   - 8.2 [Reaper's own settings and their defaults](#82-reapers-own-settings-and-their-defaults)
   - 8.3 [Every feature and function at factory](#83-every-feature-and-function-at-factory)
   - 8.4 [What a factory reset actually restores](#84-what-a-factory-reset-actually-restores)
9. [Present but inactive](#9-present-but-inactive)
   - 9.1 [The stock firmware-update page](#91-the-stock-firmware-update-page)
   - 9.2 [AiProtection](#92-aiprotection)
   - 9.3 [The setup wizard](#93-the-setup-wizard)
   - 9.4 [Kept for an AiMesh node](#94-kept-for-an-aimesh-node)
   - 9.5 [Kept because closed code names them](#95-kept-because-closed-code-names-them)
   - 9.6 [Kept for add-ons](#96-kept-for-add-ons)
   - 9.7 [Why these were kept](#97-why-these-were-kept)

---

## 1. What Reaper is, and is not

Reaper is a security-hardened, de-clouded rebuild of Asuswrt-Merlin (3006.102.10; 3006.102.8 for four models, see 2.1) for the ASUS RT-BE series (Broadcom BCM4916, Wi-Fi 7). Its stated goal is that **only physical access** should be able to compromise the router: the open-source userspace has been audited and patched against remotely or LAN-reachable command injection, buffer overflows, format-string bugs and authentication bypasses, across several audit rounds. That hardening is invisible in normal use. What you will notice is the de-cloud work (the router no longer talks to ASUS), the different interface, and the features listed below.

Reaper is distributed as a patch series applied to the public Asuswrt-Merlin source. Releases are compiled in a public GitHub Actions clean room from pinned inputs, and the About page in the firmware states the patch count, upstream commit and build date of the image you are running so that it can be rebuilt and checked.

### 1.1 What it keeps

- **Everything Asuswrt-Merlin ships** for this platform that is not cloud-coupled: user scripts (firewall/services events), cron, custom service configs, Entware via `amtm`, `nano`, NTP, SNMP (SNMPv3 only, see below), OpenVPN client and server, WireGuard, IPsec/strongSwan (built and staged from v2.5.3 onward), VPN Director, DNS Director, Cake SQM, Tor, ipset, USB sharing (Samba 4 SMB3, vsftpd, minidlna, AFP). The stock traffic statistics collector is retired; the Traffic Analyzer (4.7) keeps the history.
- **AiMesh.** It has been retained because no suitable open-source replacement is known, and replacing it would require a compatible implementation on every mesh node. The AiMesh config-sync and discovery services ship as closed vendor binaries and could not be source-audited.
- **The closed Broadcom blobs**, unmodified (see 1.5).

### 1.2 What it removes

- **The first-boot QIS setup wizard**, with its EULA and privacy-consent screens, and the Advanced privacy page. From v3.4.2 every route into the wizard is closed (the default setup address, the first-use redirect while the WAN is down, the landing after a LAN subnet change, a dead menu entry); the one part kept is the **AiMesh add-node** window, which carries the Reaper look (9.3).
- **Quagga** (the `zebra` and `ripd` routing daemons, v3.3.4): it shipped inert with a default management password.
- **ASUS DDNS (`asuscomm.com`, v3.4.9; its client code deleted in v3.7.7).** A saved ASUS DDNS setting is switched off once at boot, with a log line, and does nothing; the DDNS page says so and offers the other providers and Let's Encrypt via DNS (4.23.3).
- **The USB application network installer** (v3.3.7): it installed plain-HTTP packages as root. The USB Application page, the mount chain and the disk check stay.
- **Phone-home.** The ASUS AWS-IoT cloud connector and account binding, the AAE/AiHome cloud tunnel, AiCloud/WebDAV, the AiDisk cloud-share wizard, the stock privacy-policy check, the stock "Security Update" (Trend Micro signature) panel, and every browser-side callback to ASUS servers — device and app icons, the FAQ index, DNS-provider and ISP lists, the Open NAT game database, timezone tables and so on. The build now fails if an ASUS CDN reference reaches the shipped web root, so this cannot silently creep back. Nothing in the web interface contacts ASUS any more; the only outbound checks the firmware makes on its own are the opt-in firmware check, which goes to the Reaper GitHub release channel, and — with the LAN name resolution check switched on (4.14a, off at factory) — one DNS query a minute for a random name under the domain you set there, or the stock network-monitoring name, which that domain's DNS servers see.
- **Adaptive QoS / Trend Micro DPI.** AiProtection, DPI-based Adaptive QoS and the web-history feature are gone with the engine that powered them. Reaper's own hardware QoS and Traffic Analyzer take their place.
- **Alexa / Google Assistant** integration, the Download Master advert, the stock Network Map page (its device list and per-device detail now live on the dashboard and the Devices page), the Open NAT menu entry (it was port forwarding, which is still there), and the legacy SNMPv1/v2c protocols (SNMPv3 only; SHA with AES is the default and the choice to keep, MD5, DES and no privacy remain selectable for old managers, 4.27.9).
- **Instant Guard and the VPN Fusion app.** Both needed the ASUS account and phone app that the phone-home removal took out, so they could never pair. Their old addresses open the VPN Server and VPN Client pages, where every server and client type they offered is configured instead.
- **Unused stock request addresses and page hooks (v3.8.4).** 51 request addresses and 36 page hooks that no
  shipped page and no part of the firmware calls are gone. Among them: the stock /jffs archive download and restore
  (`backup_jffs*.tar`, `jffsupload.cgi`; the restore erased `/jffs` and unpacked the upload - the full backup, 2.5,
  carries `/jffs` instead), `set_fw_path.cgi`, the AiProtection and DNS-filter addresses of the Trend Micro engine
  Reaper does not ship, the IPsec profile and certificate upload addresses, the stock captive-portal page upload
  (the Guest Portal has its own), the stock "deregister DDNS" address, and the addresses only the ASUS Router phone
  app used: family groups, per-device blocking, remote control, the notification centre, creating or resetting
  networks and Wi-Fi settings outside the Network page, and the iperf3 speed test between AiMesh nodes. The app is
  not a supported way to manage a Reaper router. A request for a removed address gets "not found"; until the next
  stable version the router also writes one system-log line per address per boot naming it and the client that
  asked, so an add-on that still uses one can be found (System Log: `a request for the removed address ...`). The
  release notes list every name. strongSwan no longer loads its `vici` control plugin, which nothing in the
  firmware uses (the IPsec server works as before).
- **Stock hooks and addresses the native interface left without a caller.** The stock pages the native interface
  replaced were the last callers of 48 page hooks and 29 request rows; those are gone too, with the code only they
  reached. Among them: the stock generic hook reader `update.cgi`, the hooks that connected or disconnected the WAN,
  switched the USB shares and started USB application installs, the stock ROG first-QoS address
  `rog_first_qos.cgi`, and the rows of the stock offline, manifest and network-map files. A request for
  `update.cgi` or `rog_first_qos.cgi` also writes the system-log line described above.
- **No packet-capture page is bundled.** If you want `tcpdump`, install it through Entware on a USB stick.

### 1.3 What it adds

In short: two hardware QoS engines that keep the flow accelerator on, a native Traffic Analyzer, a native firewall rules engine, Gatekeeper device access control, the Bastion menu (Warden threat and country blocking, Dreadwatch DNS threat blocking, the Wallguard ad and tracker blocker, Encrypted DNS for devices), an advisory Security Review, Policy Routing, a Device Identity Manager, a live Connections explorer with destination names, wireless channel diagnostics, Wi-Fi 7 preamble puncturing (static or dynamic) with a minimum channel width on Auto and an optional receiver interference-mitigation setting, a one-click sanitized diagnostics report, a native firmware page with a verified one-click update, long-term storage with analytics export, Reaper-native settings pages across most of the menu (3), and (in one of the two builds) a read-only LAN-only AI Advisor. Each gets its own section in part 4.

Around them, the stock features are tightened where they were open: guest networks are isolated from the main network and the router on every path, with narrow paths you open on purpose (chosen devices, device discovery, zone policies; 4.21), a Guest Portal whose guests get only the internet and a filtered resolver (4.21.7), mDNS across the main network and the networks you link to it (4.21.8), AP Isolation that keeps wired devices reachable (4.21.3), a firewall log that no longer floods the system log (4.1.12), a system log that caps a flood (2.12), Let's Encrypt without DDNS (4.23.3), DHCP leases kept across a restart and one rule for device names (4.26.3, 4.8.1), and custom scripts whose failures are logged (2.9).

Secure factory defaults: WPS is off, UPnP is off, the scheduled firmware check is off, and remote web admin, SSH, WAN ping, FTP, DLNA, DDNS, guest networks, SNMP, custom-script execution, remote logging and IPv6 all default off; no Telnet server ships at all. From v3.2.5 the SMB file server and the Traffic Analyzer collector also default off. From v3.4.2 the internet port is the port labelled WAN with automatic port detection off, so the provider's port is never bridged into the LAN, and every switch on the DNS Failover page starts off. Section 8 lists every factory default. The admin session logs out after 30 idle minutes (Administration → System → *Auto Logout*; 0 turns it off), on Reaper's own pages as on the stock ones.

### 1.4 The two builds: Standard (noMCP) and AI Advisor (MCP)

Every model ships in two variants:

| Variant | File name contains | What is different |
|---|---|---|
| **Standard** | `noMCP` | The AI Advisor / MCP server is **not compiled in at all** — no daemon, no page, no menu entry, no settings. This is not a disabled feature; the code is absent. |
| **AI Advisor** | `_MCP` | Adds the optional, read-only, LAN-only MCP server. It is **off by default and never started at boot**; it runs only after you arm it for a timed session. |

The noMCP build is the right choice if you never want the MCP feature present. The MCP build is safe to run without ever enabling it. Pick one; the firmware page refuses to install an image of the other variant over the top (you can still switch deliberately with a manual upload, accepting the warning).

### 1.5 The closed Broadcom parts

The Wi-Fi drivers and a set of prebuilt objects (`wl`/`dhd`, `eapd`, `acsd`, `networkmap`, `wlceventd`, `cfg_mnt`, the Broadcom `hostapd`/`wpa_supplicant` forks, `libnvram`, `libtmctl`, the rdpa driver) are proprietary, are licensed for genuine ASUS hardware only, and are never modified. Reaper hardens the userspace around them. Some defects live inside them and can only be worked around, not fixed:

- The **"settings will not save" freeze** in `libnvram.so` / `libwlcsm.so`. Since v3.1.8 every image ships the vendor's own corrected pair, unmodified: from v3.6.0 the four 3006.102.10 models take the pair that comes with ASUS's 102_40585 release, and the four 3006.102.8 models keep the pair from ASUS stock 9.0.0.6.102_42015 (the same fix, without 40585's check on which programs may write certain settings). Reaper's earlier socket bind shim is retired. The watchdog still kills a hung `nvram` reader as a safety net (log tag `reaper-nv`).
- **Weighted (WRR) QoS classes** cannot be created on the Ethernet egress scheduler; every class runs strict priority. The UI no longer offers the weight control.
- On the **GT-BE98**, a Guest Network Pro network with AP isolation combined with a manual WAN VLAN can stop the 2.5 Gbps-1 LAN port passing untagged main-LAN traffic. There is no userspace interface to correct the switch programming. Workarounds: keep Guest Pro off that port, move the device, or tag it with the guest VLAN.
- A known over-the-air **5 GHz denial-of-service** in the Broadcom radio software (a malformed frame can drop the 5 GHz radio until reboot) cannot be patched from this firmware.

---

## 2. Requirements and rules for running it properly

This section is the one to read before you flash and again after you have been running for a week. Several of Reaper's features store their state differently from stock firmware, and two of them deliberately undo your changes unless you confirm them. Knowing that in advance saves a lot of confusion.

### 2.1 Supported models and the right file

- **RT-BE96U** — primary model; every rung is built first for it.
- **RT-BE86U, RT-BE88U, GT-BE98 Pro** (3006.102.10 line) and **GT-BE98** (3006.102.8 line) — built from per-model branches of their line's tree, from that line's patch series. Each is published with both variants.
- **GT-BE19000** — joined the fleet at v3.1.4. The same BCM4916 silicon and NAND layout as the RT-BE96U, built from its own per-model branch on the 3006.102.8 line and published as a **prerelease**: it is in the clean-room CI matrix and the `all` fan-out, but it does not land as a standard release until field testers have run it.
- **ZenWiFi BQ16** (BE25000, quad-band 2.4/5/5/6 GHz, v3.3.2) and **ZenWiFi BQ16 Pro** (BE30000, quad-band 2.4/5/6/6 GHz, v3.3.4) — built from the ASUS 102_39256 GPL drop with radio firmware taken from the matching stock image, and published as **prereleases** on the same terms as the GT-BE19000. The BQ16 Pro carries the BQ16's header art until its own is drawn.

**Two base lines (from v3.6.0).** The RT-BE96U, RT-BE86U, RT-BE88U and GT-BE98 Pro are built on Asuswrt-Merlin 3006.102.10 (ASUS GPL 102_40585); their file names say `3006_102.10`. The GT-BE98, GT-BE19000, ZenWiFi BQ16 and BQ16 Pro stay on 3006.102.8 (`3006_102.8`): ASUS has not published a 40585-era GPL for them, and their closed components cannot link against the newer source. Both lines carry the same Reaper changes and the same version number; the four move to 3006.102.10 once ASUS publishes their GPL.

**Flash only the image built for your exact model.** Cross-flashing between models can brick the router. The release assets for each model are:

| File | What it is |
|---|---|
| `<MODEL>_3006_102.10_<build>_nand_squashfs.pkgtb` (`3006_102.8` on the four 3006.102.8 models) | The AI Advisor (MCP) firmware you flash. |
| `<MODEL>_..._noMCP_...pkgtb` | The Standard firmware without the Advisor. |
| `SHA256SUMS` | Checksums. Verify the download before flashing; a truncated image is a common cause of a failed flash. |

Recovery `_loader.pkgtb` images are not published; they are available on request (see [`SOURCE-AVAILABILITY.md`](SOURCE-AVAILABILITY.md)). Never flash a loader as your firmware from the web interface.

Images are hosted on the project's GitHub Releases page. The project asks that images be obtained from there rather than re-hosted copies: the compiled image bundles proprietary components with no redistribution grant, and the release channel is what the router's update check verifies against.

### 2.2 Flashing from stock ASUS or from Merlin

Before you start, every time:

1. **Save a full backup** (Administration → Backup & Restore → Download full backup) and keep the `.rbk` off the router.
2. **Download the stock ASUS firmware for your exact model** and keep it next to the Reaper image. It is your rollback and your rescue image.
3. Be on a reasonably recent stock or Merlin firmware first, to avoid nvram and bootloader-format mismatches.
4. **Use a wired connection.** Never flash over Wi-Fi.
5. Do not lose power during the flash. A failed *firmware* write is recoverable through rescue mode; an interrupted *bootloader* write generally is not.
6. Note your admin password and LAN IP; plan on a factory reset afterwards.

Then:

1. Log in, go to **Administration → Firmware Upgrade**, choose **Manual upload**, pick the `_nand_squashfs.pkgtb` (Standard or MCP — not the `_loader`), and let it flash. The router reboots on its own; allow several minutes.
2. **The first non-stock flash may need** `nvram set DOWNGRADE_CHECK_PASS=1` over SSH first. If the upload is refused, that is why.
3. After the first successful boot, a **factory reset is recommended** when coming from much older firmware, another third-party firmware, stock-with-VPN, or across a major version. Do **not** reload an old settings backup across a reset; reconfigure by hand (or restore only if the versions are close).
4. Verify: the firmware version on the Administration/About page reads `…_Reaper_v<X>`, System Info → Capabilities lists the feature flags it was built with, and internet and Wi-Fi work.

**Rolling back to stock** is the same operation with the stock ASUS `.pkgtb`, followed by a factory reset. There is no cloud or account tie-in to undo. If the web interface is unreachable, use ASUS rescue mode (Firmware Restoration utility or TFTP) with the stock image.

The project's install guide ([`INSTALL-AND-ROLLBACK.md`](INSTALL-AND-ROLLBACK.md)) marks the following as **not yet bench-confirmed on this hardware**: which button enters rescue mode (Reset or WPS) and the LED sequence, which image the rescue flow expects, whether a usable second image partition exists, and whether any anti-rollback gate blocks a downgrade to an older stock build. The Firmware page's own note says the previous firmware remains in the standby partition and that bootloader rescue mode can always reflash over Ethernet; do not rely on an automatic A/B failover.

**AiMesh nodes.** A router that you intend to add as a *new* Reaper node must be factory-reset on this firmware to become discoverable. A mesh that was already built under stock or Merlin and then flashed to Reaper is unaffected. Nodes can be updated from the main router's Firmware page (see 4.14). Reaper's theming stands aside entirely on a node, which is what fixed the blank-page loop some node owners saw in earlier versions.

### 2.3 First boot: one banner, one box

There is no setup wizard and nothing blocks a page. A factory-fresh or factory-reset router boots usable on `admin` / `admin`, with its Wi-Fi **open** on the factory network name (`ASUS_xx…`), so it can be reached for setup over Wi-Fi without running a cable. Until both the router login and the Wi-Fi have left their factory values, every top-level admin page carries a banner that cannot be dismissed. Since v3.1.0 it has one button:

- **Set up this router** (both still factory) opens Reaper's setup box: **network name**, **Wi-Fi password** and **router login password** in one step. The box writes exactly what the stock Wireless apply writes on every band — one name, WPA2/WPA3 on 2.4 and 5 GHz, WPA3 on 6 GHz, Smart Connect on — changes the login through the same committed path as the password page, marks setup complete and reboots (**Apply & Reboot**, v3.3.1–v3.3.2). The page shows the same reboot countdown as the GUI's Reboot and then returns to the login page; the reboot is what creates the main network's all-band card. Nothing is prefilled. The login name follows the stock rule (v3.8.0; earlier builds forced it to lower case): 2 to 32 characters, letters, digits, `-` and `_` in either case, starting with a letter or digit, and not `root`, `guest` or `anonymous` in any case. The sign-in compares the name exactly, so `Admin2` and `admin2` are different names. A Wi-Fi key must be 8–63 characters (or a 64-digit hex key); a shorter key is refused in the page and in the router, because the access-point daemon silently drops a short key and would come up with no Wi-Fi at all. A network name is 1–32 printable characters.
- If only the login is still factory, the button goes to the password page; if only the Wi-Fi is, it opens the box (which asks for all three fields).

Why a Reaper box rather than the stock Wireless page: on this build the stock page edits each radio's primary network, which AiMesh turns into its hidden backhaul; the network your devices join lives on the virtual networks the mesh daemon rebuilds after every wireless apply. The box writes to the right place. The stock Wireless page is untouched for engineers.

**Time zone.** The first password change also sets the router's time zone from the browser's. From v3.4.2 it writes the daylight-saving rule for that zone too (`time_zone_dstoff`, from the bundled zone table, the US rule when the zone has none), as the retired wizard did. Before v3.4.2 a router in a daylight-saving zone kept the stock rule, which matches no real zone, and could run an hour off around the October changeover; check Administration → System on an older install.

**The internet cable.** Plug the provider's cable into the port labelled **WAN**. From v3.4.2 that port is the factory internet port and automatic port detection is off; a cable in the other WAN-capable port gets no internet until that port is chosen on **WAN → WAN Ports** (4.19).

Every factory value is listed in section 8. A one-page walkthrough of this first setup is in [`QUICK-START.md`](QUICK-START.md).

The banner only ever appears on a genuinely unconfigured router — an upgrade of a configured router never sees it. The forced first-boot page and its six gates were removed in v2.9.1 after they produced the login loops of the v2.1.x line; there is nothing to release over SSH any more, and no page is ever withheld.

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
| Wallguard settings, rules, profiles, rewrites and keys | `/jffs/wallguard/` (4.3.3; the downloaded lists stay in RAM or on USB) | v3.4.9 |
| DHCP lease lists and the names devices announced (restored at start, 4.26.3) | `/jffs/reaper/leases/` (root only) | v3.8.0 |
| Warden custom-feed API keys | `/jffs/rwarden/cfkeys` (root only; not in a settings export) | v3.8.0 |

An existing list is migrated once, automatically, at the first boot on a firmware that moved it, and the migration is logged (for example `gatekeeper: device list migrated from nvram to /jffs/gatekeeper/rl`). The ceilings are gone: Gatekeeper is tested to 300 devices and its tables are sized for 512; twenty-plus routing rules and 40-domain objects save and survive a reboot. The lists' own limits (8 KB per firewall list, about 1,900 characters per domain object, 64 addresses per routing rule) are now the real ones.

**What that means for you:**

- `/jffs` is **always mounted**. The "Enable JFFS custom scripts and configs" switch on the Administration page controls only whether `/jffs/scripts` and `/jffs/configs` are honoured; it does not control whether Reaper can use the partition.
- Reaper uses **well under 4 MB** of it. The diagnostics report (v1.3.4) prints the partition's size, free space, read-only state, a write test and the space Reaper's stores use, and raises a FINDING if the partition is unmounted, read-only, nearly full or unwritable — the cases in which Reaper changes would stop persisting. Warden also shows a banner on its page if `/jffs` is off or read-only.
- **A factory reset with *clear all content and data logs* ticked, and "Format JFFS partition at next boot", erase all of these lists.** That option is ticked by default in the factory-reset box on Backup & Restore; a reset with it unticked keeps `/jffs` (8.4). For Gatekeeper that is the correct default-deny outcome (nothing is approved after a reset); for the rest it means your rules are gone. **Export first** — see 2.5.
- **The stock settings backup does not contain them** (it is an nvram export). Again: export first.
- Approving or removing a Gatekeeper device no longer forces a full nvram commit per click, so those actions are quicker than they were.
- The v2.6.x/v2.7.0 migrations are recent. The expected evidence after upgrading is one migration line per feature in the system log, and a list that is still there after a reboot; anything still open about them is in [`BACKLOG.md`](BACKLOG.md).

### 2.5 Two backups, not one

Both live on **Administration → Backup & Restore** (the Reaper page that replaced the stock Restore/Save/Upload Setting page in v2.9.8).

| Backup | Button | What it contains | What it does not |
|---|---|---|---|
| **Full backup** (`.rbk`, v2.7.2; carries `/jffs` since v3.0.6) | **Download full backup** | **One file** carrying the stock settings (in the stock `.CFG` format, still restorable by stock/Merlin if carved out), the Reaper settings below, the firewall's resolved domain-set cache, and — since v3.0.6 — **the whole `/jffs` partition** as a gzip tar: addon scripts, certificates, every Reaper data store. | — (this is the everything-in-one option). It restores only to the same model. |
| **Reaper settings backup** (v2.7.0; embeds the `.CFG` since v3.0.6) | **Export settings** | One JSON file, `reaper-settings-<model>-<version>-<date>.json`: the stock settings (`.CFG`, embedded as base64) plus every Reaper feature's own settings: Gatekeeper (switches and the device list), Policy Routing (switch and rules), the Firewall engine (switches and all eight lists), Warden (countries, feeds, ban/allow lists, reset interval), Dreadwatch (lists, removed rows, never-block names, your own sources and their API keys), Wallguard (switch, answer mode, lists and your sources with their API keys, rules, profiles, assignments, blocked services, schedules, safe search), the DNS options (strict order, no cache, reverse sharing, IPv6 names, the LAN DNS check, the DNS health check), Encrypted DNS, the Security Review and self-monitor settings, the System Log's saved exclusions, DHCPv6 reservations, Traffic, the data export (tokens included), the Advisor's client pin, beta-firmware offers, connection names, the UPnP guard and the channel-quality monitor. | `/jffs` itself — addon scripts, certificates and the domain-set cache are not in it. On a **different model** the router settings stay behind, and with them what belongs to one router: radio tuning, AiMesh, the USB store, QoS (it extends the stock QoS settings) and the update-check hour. |

The **full backup** is the file to keep before a factory reset, a reflash or a hardware swap. Restore checks that the archive matches this router model, that `/jffs` is healthy, and that the `/jffs` tar lists cleanly before touching anything; then it replaces `/jffs` (wipe and extract, as the stock JFFS restore did), restores the stock settings and reboots. Everything is live when the router returns — there is nothing to click afterwards. An archive made **before v3.0.6** has no `/jffs` part and keeps the two-phase flow: after the reboot, log back in and click **Complete restore** when prompted; its firewall and routing lists are then staged as drafts to **Apply** then **Keep**.

The **settings file** is the small, portable one. Importing it **on the same model** restores the router settings and reboots, then Complete restore finishes the Reaper half exactly as above. Importing it **on a different model or firmware** skips the router settings inside and imports only the Reaper configuration, with no reboot: every feature it carries takes effect at once (each one's service restarts, Dreadwatch's and Wallguard's lists download again), and the Firewall and Policy Routing lists are loaded as **drafts** — open each page, **Apply**, then **Keep** — so a restored rule that cuts off your own access still reverts on its own (2.7). Nothing is written to `/jffs/configs`. The page reports `Imported: N setting(s), M list(s), K rejected`.

Either file **contains credentials**: the Wi-Fi passwords, the admin password, VPN keys, the DDNS and PPPoE logins and the API keys of your own list sources — and the full backup adds the HTTPS and SSH private keys and the traffic-history databases. Each card says so under its buttons. The stock `.CFG` save options ("remove password from file", "transfer DDNS") are gone with the stock panel: both files keep passwords. Both keep your **DDNS hostname** too (since 27 October 2026; before that it was left out as stock does for an ASUS asuscomm.com name, which belongs to the router it was registered on — Reaper has no ASUS DDNS, so the name with your provider now comes back with its login). Since v3.0.8 there are two ways to hold such a file safely, and one guard on the way in:

**Sealing (v3.0.8).** Every export asks for your **admin password** (checked on the router, on that request — a stolen session or a script foothold in the browser is not enough to pull the file; five wrong answers lock exports for a minute) and offers an optional **backup passphrase**. Give one and the file is **sealed**: encrypted with AES-256-GCM under a key derived from the passphrase with scrypt. A sealed file cannot be opened without the passphrase, and it refuses to open at all if a byte of it was changed, so a backup that someone "fixed" for you fails before the router parses any of it. The passphrase is **not stored anywhere** — lose it and the file is gone. Leave the field blank and the file is the plain one described above. Sealed files carry a second extension (`.rbk.enc`, `.json.enc`); restore and import recognise them and ask for the passphrase. A sealed settings file is opened on the router rather than in the browser and then behaves exactly like the plain one (same model: settings + reboot; other model: the Reaper half, no reboot).

For the record, the sealed container is plain enough to open without a router: a line `REAPER-SEALED 1`, one JSON line with `salt`, `iv` (base64), the scrypt cost `n`/`r`/`p` and the plaintext `len`, then `len` bytes of AES-256-GCM ciphertext and the 16-byte tag; the two header lines are the authenticated additional data, the key is 32 bytes of scrypt over the passphrase. The plaintext is byte-for-byte the unsealed file.

**On the way in.** Every export, import and refused request is logged with the client's address. A restore refuses a `/jffs` archive in which a later entry would be written **through** a symlink the archive itself planted (the one way a crafted archive could reach outside `/jffs`); links that nothing is written through restore as before, so addon setups are unaffected.

### 2.6 A USB disk for the long-term store

Live data — the traffic graphs, device presence, channel quality, the Flow Explorer's destination-name table — is kept in RAM and resets at reboot. If you want history over long spans, you choose a **durable location** on the Long-Term Storage page (System Log → Long-Term Storage): **RAM only**, **Internal (JFFS)**, or **USB storage**, per dataset. The datasets are device history and the action audit trail, Traffic Analyzer history, watchdog (`rwatch`) incident dumps, channel-quality history, a syslog mirror, Wallguard's block lists (USB only), Wallguard's and Dreadwatch's blocked lookups, and Encrypted DNS activity. Warden's cache and the Encrypted DNS blocked-address list are locked to JFFS regardless. Connection-health history for analytics export lands in the same location.

A USB disk is the right place for anything that grows: it has the most space and no flash-wear concern, so the Traffic Analyzer saves to it every 15 minutes (JFFS stays hourly to protect the router's NAND). History is written under `/.reaper/` on the volume with restricted permissions, but anyone with file-share access to that volume can read it — it maps every device with timestamps — so prefer JFFS if the share is open to untrusted users. Writes are batched and low-priority; pulling the stick loses history, never policy or performance.

**Which filesystem.** Format from the USB Disks page (4.12):

- **ext4 — recommended** for a disk that stays on the router: journaled, fast, large files. Not readable by Windows or macOS without extra software.
- **ext3 / ext2** — older Linux formats; pick ext4 unless something you own needs these.
- **FAT32** — readable everywhere, but **no file larger than 4 GB and no journal**; use it for a disk you move between devices, not for the store.
- **NTFS / HFS+** — available; formatting these from the Reaper page had never worked before v2.6.8 (the disk came back untouched).

The ext4/ext3/ext2 options arrived in v2.6.8. The USB health scan runs a real `e2fsck` on ext4.

**Timing.** USB drives mount roughly 40–50 seconds into boot. The Traffic collector waits for the store to appear (retrying for up to 15 minutes), restores the saved history, and never overwrites a database it did not first load; it also parks itself if the store vanishes during a firmware flash and re-attaches when it returns. The dashboard re-polls USB status for the first 90 seconds after load so the tiles fill in on their own.

**Flashes, reboots and late disks (v3.3.2–v3.3.3).** A firmware flash, a reboot and a factory reset first stop the services you started from `services-stop` (Entware and the like), then any process still holding a file on the disk, and release every swap file on it, before the disk is unmounted, so the volume comes back clean. A dnsmasq whose configuration points at a USB path that is not mounted yet drops that one line and is restarted once the path appears, instead of leaving the LAN without DNS and DHCP. A mount watchdog re-sends a lost mount event for a partition that never mounted (three tries in 30 minutes). The kernel's soft-lockup panic is held off through boot and while a disk mounts, and re-armed after 600 s of uptime with no mount activity (the system log says `soft-lockup panic armed`).

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
- On the Firewall and Policy Routing pages, **Keep is what writes flash**; each page's confirmed lists are its snapshot on `/jffs`. A Policy Routing Keep also saves the address objects and groups it uses into the firewall's snapshot, because the two pages share them. If `/jffs` is too full to save, Keep leaves the rules live, keeps your edits as a draft and says so on the page; the previous confirmed rules are what a reboot brings back.
- Test from a device that is **not** itself affected by the rule you are testing, so that the browser you are using is not the thing that gets cut off while you look for the Keep button.

The Firewall page's other tabs (General, Network Services, URL Filter, Keyword Filter) are the long-standing Asuswrt controls and apply straight away with no countdown. The Firewall Status tab tells you what is actually live; what you configured and what is live can differ while a restart is in flight or if a ruleset failed to build.

### 2.8 MLO needs a cold power cycle

Enabling or disabling Wi-Fi 7 Multi-Link Operation (the MLO switch) needs a **full power cycle** — unplug the router, wait, plug it back in — not a software reboot, for the change to settle. If MLO appears to have half-applied (clients seeing one band only, the dashboard's MLO row reading *Partial*), power-cycle before investigating anything else. *(This rule comes from the project's working notes rather than the changelog; it is recorded here because it is a common cause of confusion.)*

From v3.8.4 the router notices the common case itself: when MLO is on and a restart without a
power-off left the link the radios use for MLO down, the system log says so (`mlo: MLO is on, but this start was a
restart without a power-off ...`) and the dashboard shows a crimson **Wi-Fi needs a power cycle** banner until the
router is unplugged and plugged back in. The MLO switch's confirmation says the same before it reboots. The router does
not reboot itself for this. The check first learns what a good start looks like on this router's radios: it warns only
after the router has once started with the MLO link up (normally the first start with MLO on), so a router whose radios
report the link differently is never warned by mistake.

### 2.9 Custom scripts and Reaper's firewall chains

Merlin's user scripts (`firewall-start`, `nat-start`, `services-start` and the rest) and Entware add-ons all keep working. But be aware of how Reaper's own layers are built, so that a script does not fight them:

- Since v2.6.2, every Reaper firewall layer registers into **one shared front chain per base chain** (`REAPER_HOOK_*`, at position 1 of INPUT/FORWARD/OUTPUT), in a **fixed order: Warden → guest isolation → Gatekeeper → rules engine** — every deny-only layer before the one that can accept. Guest isolation's one accept, the main-network devices you let a guest network reach (4.21.3), is hooked last, after the rules engine. A single script rebuilds that order after any layer applies, so it converges whichever service restarted.
- Gatekeeper and Warden **self-heal**: Gatekeeper repairs a lost hook within about 30 seconds and re-applies when a bridge appears without one; Warden re-arms after any firewall restart; the `rwatch` watchdog re-applies Policy Routing mark rules if the live chain is short of what it meant to load.
- Since v3.1.2 `rwatch` also checks **chain integrity** every tick, which is what catches another script quietly disarming a layer. Two things: each of Warden's block chains must still *end* in the block itself with nothing inserted ahead of it that would let traffic through, and nothing that can let traffic past unchecked may sit in front of Reaper's chains in INPUT/FORWARD/OUTPUT. A chain found disarmed is reported as critical. **Since v3.1.3 the second check looks at *what* is in front rather than insisting on position 1**, because a narrow carve-out ahead of Reaper is sometimes deliberate and occasionally required — a DNS rule that has to beat Gatekeeper so restricted devices keep resolving, for instance. A rule that can only affect a narrowed class of traffic is tolerated and logged once — in INPUT and OUTPUT that means a port or a destination; in FORWARD, since v3.2.8, a destination only, because a port-only or interface-only accept there would pass every device to every host on that port past all three layers (a negated match narrows nothing). A chain you jump to is judged by its own accepts; its returns do not count, since a return simply resumes the base chain where Reaper's jump comes next. So is any **user chain** you list, one name per line, in **`/jffs/reaper/front_exempt`** — chain names only: built-in targets such as `ACCEPT`, `RETURN` or `DROP` are ignored there (and logged once), because listing `ACCEPT` would exempt every blanket accept. A rule that could wave anything through is still re-pinned and the displacement logged — but if the repair is undone twice, `rwatch` says so and stops re-pinning rather than trading places with whatever keeps inserting itself. Note the Gatekeeper and rules-engine chains are deliberately **not** checked the first way — they interleave allow and deny by design, so "ends in a block" is not a property they have.

**What happens to a script that inserts at position 1.** An `ACCEPT` placed above Reaper's hook lets traffic past Warden, Gatekeeper and the rules engine entirely — the defect v2.6.2 fixed inside Reaper. Your rule is not removed. After the 5-minute boot grace, the next `rwatch` tick (every 5 minutes) moves Reaper's hook back above it, logs `FAILURE detected: front-chain-drift` with an incident dump in `/jffs/rwatch`, and names the rule (`rule(s) ahead of the Reaper hook ...`); it repeats at most twice, 600 s apart, then stops and says so. Your script runs again on the next firewall rebuild, so the pattern repeats every boot: drift logged about 8 minutes after each start. VPN helpers (Tailscale, WireGuard, OpenVPN) commonly do this with an interface rule such as `iptables -I FORWARD 1 -i tailscale0 -j ACCEPT`.

**Insert after Reaper's hook instead.** In `firewall-start` (or `nat-start`), find the hook and insert right behind it. `-A` (append) does not work: the stock FORWARD chain ends in drop rules, so an appended accept is never reached.

```sh
# position just after Reaper's jump in a base chain (1 if Reaper's hook is absent)
after_hook() {
  n=$(iptables -S "$1" | grep -n -- "-j $2\$" | head -1 | cut -d: -f1)
  [ -n "$n" ] && echo "$n" || echo 1
}
P=$(after_hook INPUT REAPER_HOOK)
iptables -I INPUT "$P" -i tailscale0 -j ACCEPT
P=$(after_hook FORWARD REAPER_HOOK_F)
iptables -I FORWARD "$P" -i tailscale0 -j ACCEPT
iptables -I FORWARD "$((P+1))" -o tailscale0 -j ACCEPT
```

`iptables -S` prints the policy line first, so the hook's line number is its rule position plus one — which is exactly the position just behind it. Do the same with `ip6tables` for IPv6 rules. A rule that genuinely has to sit ahead of Reaper should be **narrow** (a destination in FORWARD; a port or destination in INPUT/OUTPUT) or live in a chain of its own listed in `front_exempt` — knowing that a listed chain's accepts bypass all three layers. Or use the Firewall page's Rules tab, which was built for this.

Flushing INPUT or FORWARD in a script changes the layer order too; Reaper's layers re-apply, but do not rely on it. Scripts that loop calling bare `nvram get` should also be avoided: the closed nvram library can hang a reader forever (1.5); Reaper's own generated scripts read through a five-second guard and `rwatch` reaps any `nvram` process older than two minutes, but a hung reader in your script still holds whatever lock your script took. Scripts that read kernel accelerator files on a timer are another thing to avoid; the project shelved its own accelerator probe after it caused reboot loops in the field.

**Chain signatures (v3.3.4).** Each firewall apply records a checksum of every Reaper filter and nat chain. `rwatch` recomputes it on each tick; two ticks in a row that disagree re-apply the confirmed rules under the firewall lock, at most twice and 600 s apart, and never while a change is waiting for Keep. A script that edits a Reaper chain in place is therefore undone within about ten minutes.

**Security review.** The review that watches `/jffs`, cron and the exposure settings for changes you did not make has its own section now: **4.1.1b**. Its baseline and the baseline's seal travel together in the **full backup** (`.rbk`: `/jffs` and the router settings); the settings export (JSON) carries the switch and the watch rules, not the baseline and not the seal. Restoring a full backup made before v3.8.4 leaves the baseline without a seal (amber row, accept once); restoring only router settings that are older than your last Accept shows the red row (accept once).

**SSH over IPv6 from the internet (2026-10-19).** The stock brute-force guard covers IPv4 only; the IPv6 rule for a WAN-open SSH port was a plain accept. Now, when SSH is open to the WAN (`sshd_enable` **1**) and the IPv6 firewall is on, the sixth new connection from one /64 network within 60 seconds is dropped and a continuing flood keeps the block fresh. LAN SSH is untouched, and there is no switch: it hardens an exposure you chose, and five new SSH sessions a minute from one network is not a use anyone has.

**File modes (v3.3.8).** `rc` and everything it starts now run with umask 022, so a file created without an explicit mode is 0644, not world-writable 0666. An add-on that writes into such a file as a non-root user must set the mode itself.

**Files from before that (v3.4.8).** The umask only shapes new files: a file created earlier kept 0666 through every later rewrite, and restoring a full backup brings old modes back. Among them were the SSH authorized keys (`/jffs/nvram/sshd_authkeys`), the VPN and HTTPS private keys and the rule lists, which a compromised service running as another user (dnsmasq, avahi, lldpd) could have changed. At every boot, right after `/jffs` is mounted and before anything runs from it, the router removes write access for other users from every file and folder on `/jffs` and logs how many it changed (`reaper: jffs: write access for all users removed from N file(s) and folder(s)`). Symlinks are never followed, and FIFOs and sticky shared folders keep their modes. With the Security Review on, a file or folder that has the permission again is listed on the review card and the dashboard; the diagnostics report counts them in section 3. The long-term store on a USB disk is checked the same way, and the router removes the permission there when the disk is attached. A store on a FAT, exFAT or NTFS partition is the exception: those file systems keep no file permissions (every file reads as writable by everyone and nothing can change that), so the review does not list its files one by one; the card and the review panel show one note instead. A partition formatted as ext4 keeps permissions. An add-on that relied on a world-writable file or folder under `/jffs` should give it its own owner instead (`chown` it to the user that writes it).

**IPsec's certificate folder (2026-10-21).** `/jffs/ca_files` holds the IPsec server's CA, server and client private keys and the setup scripts the router runs from it as root. The stock IPsec code rewrote those scripts with mode 0777 every time IPsec started, after the boot sweep had run, and created the keys readable by every user. Now the folder is root's alone: mode 0700, and no file in it has group or other permissions. The boot sweep enforces this whether IPsec is on or not (`reaper: jffs: the IPsec keys and scripts in /jffs/ca_files made root-only`), and so does every IPsec start and certificate generation. The scripts are created fresh at 0700 and run only when they are root's and nobody else can write them. strongSwan's own key folder, `/tmp/etc/ipsec.d/private`, gets the same treatment. Nothing that is not root uses either folder, so the IPsec server, its certificate export and its import work as before.

**VPN provider profiles kept from the stock firmware (2026-11-10).** The stock firmware's provider logins (Surfshark, NordVPN) are not part of Reaper: from v3.7.1 the router no longer signs in to a provider's service to fetch and renew a profile's keys, so a provider profile carried over from stock stops connecting. Set the provider up as an ordinary WireGuard client instead: in your provider account choose the manual or router WireGuard setup, download the configuration file it makes, and import it on **VPN → VPN Client**, WireGuard tab (a file without a valid private and public key is refused and nothing is changed). On a router upgraded from stock without a factory reset, a provider entry left in the old VPN list used to switch its WireGuard or OpenVPN client off again at every boot, which looked like a lost key; from the image after v3.7.5 that list no longer switches a client on or off. A saved private key or pre-shared key is never sent back to the page: the field is empty, **Show** only unmasks what you type, and the text beside it says **A key is saved (hidden)** or **No key saved**.

**IPsec profile checks (2026-11-10).** A saved IPsec profile is not applied when it holds a control character anywhere, has fewer fields than the format needs, holds the word `include` followed by a space outside a key or password, or breaks a field rule. The local and remote ID and the remote gateway take letters, digits and `@ . _ : + % -` only (or a hex key ID, `@#` and hex digits); a certificate DN is not accepted. Subnets, certificate and key file names, authentication methods and the EAP identity take no space or `=`. The pre-shared key, the XAUTH password and the key file name take no double quote. The DNS/WINS list takes addresses only. The system log names the profile and the reason (`... profile N skipped: unsafe character in <field>`, `include directive in <field>` or `malformed saved value`); the saved value is left as it is. An Instant Guard client whose name is not 1 to 32 letters or digits gets no login (`Instant Guard client N skipped: unsafe name`). A VPN user of the IPsec server whose name holds a space, `:`, `#`, a quote, a backslash, `<` or `>`, is `include` or is longer than 64 characters, or whose password holds a double quote or a control character, gets no login (`VPN user N of ipsec_client_list_M skipped: unsafe character in the user name` / `password`); the page now refuses `#` in a name too. When a profile is refused while the IPsec server runs, strongSwan is restarted once so a tunnel that profile had up goes down (a reload alone kept it). A local subnet may be IPv6. The IPsec server certificate is only made for a well-formed WAN IPv4 address, or for a valid DDNS host name; without one the log says `No usable WAN address yet, CA files are not created.`

**Mount options (2026-11-10).** `/tmp`, `/var` and `/jffs` are mounted `nosuid,nodev`: a file placed there cannot run as another user through a setuid bit and cannot act as a device node. Scripts and programs in `/jffs/scripts`, `/jffs/addons` and `/tmp` run as before; USB volumes are unchanged. A failure to set the flags is one log line (`cannot set nosuid,nodev on ...`) and nothing else changes. Section 3c of the diagnostics report shows the flags.

**Settings that hold a line break (v3.8.2, from ASUS GPL 102_39448).** A setting whose value contains a line break is read as empty, and the read is logged, except the multi-line settings ASUS allows (VPN custom configurations, SSH keys). A line break stored in a setting by a script can therefore no longer add lines to a configuration file the router generates from it. A script that stores multi-line text in another setting should keep it in a file under `/jffs` instead.

**Conntrack helpers by rule only (v3.7.2).** The FTP and PPTP connection helpers attach only where they are needed: to the router's own FTP and PPTP servers and to a port forward to an FTP server, always; to LAN devices' outgoing FTP only with **FTP Passthrough** on (WAN → NAT, off by default; 4.23.2). A script that loads a helper module expecting it to attach to every connection on its port must add its own raw-table `CT --helper` rule. Section 3c of the diagnostics report counts the rules.

The diagnostics report lists "an old direct firewall hook left over or the shared front chain missing" as a FINDING, which will catch most script conflicts.

**When a script seems not to run.** A custom script runs only from `/jffs/scripts/<name>`, only while *Enable JFFS custom scripts and configs* (System) is on, and only when it is executable (`chmod +x`); each refusal is logged as `custom_script: Found <name>, but …`. The router also keeps what the script printed on its last run in `/tmp/reaper/script-<name>.log` (the first 64 KB) and logs one line when it exits with an error, quoting the last thing it printed - so a command this router does not have (`iptables -w`: its iptables is 1.4; BusyBox options such as `flock -w` or `find -type`) shows up as `custom_script: /jffs/scripts/firewall-start exited with status 2: iptables v1.4.18: unknown option "-w" …` instead of looking like the script never ran. A script saved with Windows line endings is named too: its first line then asks for `/bin/sh\r`, which does not exist. Section 13 of the diagnostics report lists every script with these facts. It judges only the names the firmware runs (the hooks such as `services-start`, `firewall-start` or `ddns-start`, and `*.postconf`); any other file there - a helper a hook calls, a `.log` it writes - is listed as not a hook name, with no finding. A hook that is a symlink runs (the router follows the link) and is listed as one.

### 2.10 The diagnostics report and how to share it safely

**Administration → Diagnostics** has one button: **Download Report**. It gathers in one pass what a network engineer would collect by hand — model and firmware identity, uptime and memory, each radio's channel, width, signal health and client counts, wired port link states and speeds, hardware-acceleration and QoS readings, DHCP lease count, running services and open ports, recent kernel and system log excerpts — and, since v1.3.0 of the report, a **FINDINGS** block at the top, syslog history over the live log *and* the `rwatch` mirror (days, not hours), process health, the state of every Reaper layer, the data plane, nvram hygiene, a network inventory, and `/jffs` health. It takes roughly 20–30 seconds. Since v3.3.3 the collector runs as a separate background job, so the rest of the web interface stays usable; the page checks on it every 2 seconds and downloads the file when it is ready (it gives up after 5 minutes). The same collector is available over SSH as `reaper_diag`.

**Recent additions to the report.** The syslog history section reads the *rotated* log file ahead of the live one, so on a
busy router the boot is in the report even when the live file starts twenty minutes later (and a finding says so); the WAN
section prints the NTP state with a warning when the clock never synchronised, since every service that waits for the
first sync sits behind it; the connectivity section warns when every probe from the router itself failed; and the
conntrack section prints the destination-name table's counters (how many DNS replies were read, how many names kept -
counts only, never a name). Report v1.3.34 (v3.4.0) adds the LAN name resolution check to the WAN section: switch, state,
how long, and which servers stayed silent, by role. Report v1.3.42 (v3.4.8) adds the Gatekeeper sinkhole to section 14b, and v1.3.43 a Dreadwatch line to section 14:
blocked lookups in total and per feed, how many were not recorded, how many devices tried, the hits waiting for the
next collection and each feed's last result - counts only, never a name or a device address. Report v1.3.45 counts the
files and folders under `/jffs` that any user can write (section 3), with a finding when there are any.

Later reports add: Dreadwatch's compiled table and how many DNS instances map it (v1.3.46, section 14); each custom
script, whether it can run and how its last run ended (v1.3.51, section 13); the firewall log collector's counts and its
remote forward (v1.3.57, section 14); the radio-call stall section with the three Wireless stability switches (v1.3.59,
12d); each radio's driver and firmware version, AP Isolation per network and Wallguard's switch (v1.3.60). **Report
v1.3.62** covers the features of v3.4.9 - v3.8.3:

| Section | What it shows (counts, states and bridge names only) |
|---|---|
| 3c Hardening | `/tmp`, `/var` and `/jffs` mount flags; conntrack helpers (automatic or by rule, the raw rules, FTP / PPTP passthrough); how many times the system log held back a repeating message; any USB 3 write lever that is set |
| 4d Guest networks | per enabled network: its type word, bridge, isolated or not (the live rules), Access Intranet with the main network, Guest Portal, VPN binding and Kill Switch, AP Isolation and *Wi-Fi and LAN ports*, the number of chosen main-network devices against the live rules, the discovery service types; the guest isolation chains and their hooks, the guest DNS redirect, bridge-port isolation (Wi-Fi and wired ports), the Guest Portal processes and watchdog restarts, the mDNS reflector's interfaces |
| 6 IPv6 | the delegated prefix length and how many networks fell back to a private prefix |
| 11 DHCP leases | the lease copies saved to `/jffs` and when, leases per guest network, how many device Names, reservations and announced hostnames exist |
| 12c Services | SNMP (switch, WAN access, running) and AiMesh backhaul parking |
| 14c Layer order | guest isolation in the front-chain order; the AiMesh exemption set against the registered nodes |
| 14d Policy Routing | the fetched lists (ASN / country): how many are in use, each saved list's source, size and last check, the daily update job; no list name and no address |
| 14h Bastion | the four Bastion switches; Wallguard's table, which DNS instances map it, each subscribed list's state and last good download, the last build, your rules counted, pauses and counters; Encrypted DNS listeners by protocol, queries, refusals, devices by protocol, the option 162 offer, how many devices DNS Director leaves out of it, and the block chain; how many devices skip Dreadwatch and how many listed lookups were let through (counts only); Let's Encrypt via DNS state and the web certificate's issuer and expiry |

Each new section adds FINDINGS for the states that need action: a Guest Portal without its isolation rules or without
chilli, chosen devices with no live rule, a guest DNS redirect that is written but not hooked, a Wallguard list that
failed or a skipped table build, Encrypted DNS switched on but not running or a listener that could not bind, the
Encrypted DNS block without its chain, the AiMesh exemption set empty while nodes are registered, a failed Let's Encrypt
via DNS run, an expired web certificate, a mount without `nosuid,nodev` and automatic conntrack helpers.

**What the report masks.** The whole document passes through a redaction engine before a byte is written:

- Passwords, Wi-Fi keys and tokens are **never collected** — the report only notes SET or EMPTY.
- Every **MAC address** becomes a consistent pseudonym (`MAC-3` and so on), including MACs written without colons.
- **Usernames, device names, hostnames** (including guest-network lease hostnames) and **Wi-Fi network names** become tokens.
- **Your public IPv4 address and all IPv6 addresses** are masked. **E-mail addresses** are redacted wherever they appear (from v2.4.6).
- From report **v1.3.35** (v3.4.2) three IPv6 shapes that earlier reports printed are masked too: a **routed prefix that ends in `::`** (a tunnel broker's `2001:db8:abcd::/48` in a Warden or IPv6 firewall line), a **reverse zone** (`…ip6.arpa`, the same prefix written backwards in dnsmasq's log, now `[IP6-ARPA-n]`), and a **DHCPv6 DUID**, which embeds the router's MAC (its lease-file line is no longer printed). The bare well-known prefixes `fe80::`, `fc00::`, `fd00::`, `ff02::1`-style multicast and `2001:db8::` stay readable, because they identify nothing. **A report from an older image that shows a `2001:` or `2a0x:` prefix, an `ip6.arpa` name or a `MAC-n:xx:xx…` tail has leaked; do not post it.**
- From report **v1.3.36** the redaction runs as a **pipeline of targeted stages**, one per kind of data, each with its own ledger lines: values the router knows to be private (passwords, usernames, network and host names), then **names and domains your devices wrote into the log themselves**, then e-mail, MAC, IPv6 and IPv4 addresses. The client-names stage reads the DHCP and Gatekeeper log lines where a device supplies its own name (`Ignoring domain … for DHCP host name …`, the name on a DHCP acknowledgement, `not giving name …`, a Gatekeeper `host (…)`), masks each name as `[CLIENT-NAME-n]` and each domain as `[CLIENT-DOMAIN-n]` everywhere in the report, and keeps generic domains such as `lan` and `local` readable. Before v1.3.36 a device's own domain, which can name its owner's employer, was printed as it was, and a short device name in older log lines could slip through. A stage that fails stops the report: no partly redacted file is ever written.
- From report **v1.3.56** the **names on the router's own certificates** are masked as host names: the DNS-over-TLS / Let's Encrypt name and the names on the web interface's certificate, including any extra names you added to it. dnsmasq writes the first into the system log every time it starts and the web server writes the second at boot, so both sat in section 19. **A report from an older image, taken on a router that uses such a name, shows it in the system-log section; do not post that report as it is.** The firmware's own names (`router.asus.com`, `www.asusrouter.com`) stay readable.
- From report **v1.3.61** (v3.8.2) a stage masks **secrets written into free text**, which no setting holds: a `name=value` whose name ends in *token*, *password*, *secret*, *apikey* and the like, the `user:password` part of a URL, and a `Bearer` value. They turn up in a cron job you added yourself (section 13 lists the cron table), in a process's command line (the process lists) or in an add-on's log line. The **domain your internet provider hands out** (dnsmasq names it in the system log), a **time server** you typed (the shipped `pool.ntp.org` servers stay readable), the **remote log server** and your **VPN clients' servers** are masked as host names. **A report from an older image, taken on a router with such a cron job or add-on, may carry the secret; read it before posting.**
- **Local-only addresses** (192.168.x.x) are kept — they identify nothing outside your own network.
- Pseudonyms stay consistent inside one report, so a device can be followed across sections without revealing which device it is; a new report gets a new set.
- The report opens with a **ledger** counting exactly what was withheld, and the finished file is **re-scanned** for anything that still looks like a public IPv4 address, an IPv6 address or reverse zone (from v1.3.35), a hardware address, an e-mail, or an unmasked device-supplied name in those log lines (from v1.3.36), and marked either clean or "review before sharing" (counts only — printing what it found would put the leak into the file).
- WireGuard appears as **peer counts only**.
- From report **v1.3.62** nothing new needs masking: a guest network is shown by its bridge and the firmware's type word (*Guest*, *IoT*, *Portal* ...; any other name reads *custom*), never its name or Wi-Fi name; chosen devices, Wallguard rules and API keys are counted, never listed; a Wallguard list by its id, never its address; Encrypted DNS devices by protocol, never their addresses; the Let's Encrypt via DNS name and token as SET or EMPTY. The certificate names that 14h prints are the ones v1.3.56 already masks.

It is plain text. **Open it and read it before you share it.** The router never transmits it anywhere; the file downloads to your browser. It is the right thing to attach to a bug report. The Devices page's **Export list** is the opposite — deliberately unsanitised, with real names, MACs and IPs — and is not safe to post anywhere.

### 2.11 The firmware update check

- The scheduled check is **off by default** and is switched on from the Firmware page (**Scheduled Check**). It is notify-only: a crimson "New firmware available" banner on the dashboard and the release notes on the Firmware page. Nothing is ever downloaded or installed automatically.
- It reads a **Reaper-published manifest on GitHub** — never ASUS, never the stock Merlin endpoint — and knows your model *and* variant, so it never offers the wrong image.
- You can choose the **hour** of the nightly check (leave it on *Automatic (overnight)* for the old 2–6 am behaviour). The **minute is random on purpose**, so every router that kept the default does not hit the release channel in the same second.
- **Check for Update** on the page is user-initiated and goes to the same channel.
- **Download and Install** (one click) verifies the manifest's SHA-256 and size, refuses any download URL outside the Reaper release channel, re-checks the image is for this exact model and variant, runs the platform's own image check, and only then flashes. If any step fails the download is discarded and nothing is written. A manifest without checksums downgrades the page to notify-only.

### 2.12 Reading the system log

Read it on the **System Log** page, or over SSH as the file `/tmp/syslog.log`. **`logread` returns nothing on this platform** (the log is written to a file, not the in-memory buffer). If you have a USB or JFFS store with the syslog mirror enabled, the mirror holds days of history; the diagnostics report reads both.

**Narrowing the view.** **Find** and **Exclude** each take a comma-separated list: a line shows when it contains any Find word and no Exclude word (`dnsmasq, wlceventd` in Exclude hides both). Upper and lower case match alike. **Saved exclusions**, below the log, is your own version of the stock `logFilter.json` (which is part of the read-only image): one entry per line, and an entry may contain commas. The System log view hides any line containing one of them while **Apply saved exclusions** is ticked. **Add the Exclude words** moves what is in the Exclude box into the saved list. The list is kept in `/jffs/reaper/logfilter` (up to 64 entries of 128 characters; you can edit it over SSH too) and travels with the Reaper settings file. Only the view changes: the log file, **Save** and a remote syslog server still get every line. Long lines are not wrapped: each log line keeps one row, and the box scrolls sideways.

**The Firewall view (v3.7.5).** Firewall lines are not in the system log any more: the firewall log collector (`rflogd`, 4.1.12) keeps them in its own RAM ring (`/tmp/reaper/fwlog`). The **Firewall** view of the System Log page shows that ring, with the same Find and Exclude boxes. With the collector stopped, the firewall falls back to plain log lines in the system log, at most 10 a second.

**The flood cap (v3.7.7).** One kind of message repeating fast (a device looping on DHCP, a driver printing per packet) is written at most 300 times at once and 10 times a second after that; when it slows down, one line says how many like it were held back (`… lines like … were suppressed`). The log on flash therefore keeps its history through a flood. Critical messages and the remote log server are not limited. Section 3c of the diagnostics report counts the held-back notices.

**Log settings**, at the bottom of the page, change what is kept: *Level of the router's own messages* is the priority the firmware gives its own lines, and *Log only messages more urgent than* drops everything at that priority and below from the file (and from a remote syslog server). The Wi-Fi driver writes two lines of its own at warning priority: `SBF: dhdN: INIT [device]` once each time a device joins or rejoins a radio, and `dhd_pktfwd_lut_lkup: pool 0 and unit N mismatched` while a wireless bridge (WDS) link - a repeater, a media bridge or a mesh node over Wi-Fi - goes down. A burst of them counts reconnections; it is not a fault of its own, and the disconnect behind it is what to look at. Both come from closed driver objects, so their wording and rate cannot be changed in this firmware. To hide them from the view without losing other warnings, add `SBF:` and `pktfwd_lut_lkup` to Saved exclusions; raising the cut to warning would drop the router's notices as well.

Reaper's own tags in the log: `reaper_fw` (firewall engine), `reaper_pbr` (Policy Routing), `reaper_survey` (a Site Survey channel move and its return), `gatekeeper` / `gkd`, `rwarden` and `REAPER-WARDEN` / `REAPER-WARDEN-SELF` (Warden and its drop lines), `rwatch` (the health watchdog), `reaper_cfg` (settings import/export), `reaper-nv` (a killed hung nvram reader), `hwqos` (QoS queue programming), `disk_format` (USB formatting; its log is also at `/tmp/disk_format/<dev>.log`), `aimesh:` (node-search drop reasons), `IGD desc` (UPnP description served to each client), `reaper_punct` (the preamble puncturing applier: a slice switched off or cleared, or refused by the driver; also an interference-mitigation mode set, restored or refused), `rpunctd` (the dynamic puncturing controller: one line per decision, saying why), `reaper_bwfloor` (the minimum channel width: a floor lifted after radar, re-armed, a channel-picker restart deferred or run, or not applied), `rdnshc` (the resolver health check and the LAN name resolution check: a failover, a restore, a LAN name failure and its silent servers), `amaspark` (AiMesh backhaul parking), `reaper` (general Reaper events: the WAN port pin, a pin cleared or a detection restarted, the soft-lockup panic armed). Turning a Reaper feature on or off, or changing its settings, writes a structured audit entry too.

### 2.13 Keep management off the WAN

Do not enable remote (WAN) web administration or WAN SSH. The real-world attacks on ASUS routers target the internet-facing management surface, and keeping admin LAN-only is the single best protection you have. The dashboard's Security Posture card shows you at a glance whether anything is reachable from the WAN, and the Firewall Status tab's **exposure** card lists precisely what is.

### 2.14 Where to report issues

- **Bugs and questions:** open an issue on the project's GitHub repository, `TheUnboundDeveloper/AM-Reaper` (the link is in the README and on the About page). Attach a **diagnostics report** (2.10) and say which model, variant and version. A well-written report is, in the maintainer's words, worth as much as a donation.
- **Security findings:** see `SECURITY.md` in the repository — please do not open a public issue for an exploitable bug.
- **Do not contact ASUS or the Asuswrt-Merlin developer** about this firmware. Stock bugs in code Reaper has not touched belong upstream, but if a stock bug is remotely or LAN-reachable on a BE-series model the project still wants to hear about it.
- Updates are intermittent and depend on the maintainer's time and hardware; no schedule, support period or future compatibility is promised.

---

## 3. The dashboard and navigation

**After login you land on the dashboard** (`Main_ReaperDash.asp`). It replaced the stock Network Map, which is retired. Everything else in the interface opens inside the **app shell**: a header, a left navigation rail, and a framed content area that loads either a Reaper-native page or a stock Asuswrt page with the Reaper theme applied at serve time. Since v3.4.9 the settings pages for System (with SNMP and Tweaks), LAN, WAN, VPN and Parental Controls, and the System Log group (log, wireless log, leases, routes, port forwards, IPv6, analysis, netstat, wake on LAN), are Reaper-native. Since v3.6.5 so are Wireless › WPS, WDS, Wireless MAC Filter, RADIUS Setting, Roaming Block List and MLO, and LAN › VLAN (Switch and Profiles tabs, on models with guest/VLAN networks), and since v3.7.1 USB Application, Media Server, Network Place (Samba) Share and FTP Share (4.28): they keep the stock settings and apply them the way stock does, the stock pages they replace no longer ship, and the old addresses open the new pages. The Roaming Block List is read from all three radios; MLO's *Add a Network* opens the Network page's MLO wizard; RADIUS Setting shows the main network's server and whether it is in use. **AiMesh** and **Network** keep the stock layout and link a Reaper stylesheet of their own.

**Dashboard cards**

- **Internet** — WAN state (it updates itself during boot without a refresh), your real WAN IPv6 address (never a `fe80::` link-local; the IPv6 half is re-read on every poll since v3.3.7), gateway and DNS, and an **internet on/off switch**. The switch is persistent across a reboot and asks before turning the internet off; the router's web interface stays reachable over the LAN. With the **LAN name resolution check** on (4.14a, v3.4.0), the Internet dot and word turn **amber** while LAN devices cannot resolve names even though the WAN is up, and the tooltip on the card and on the header's WAN pill names the state, how long it has lasted and the servers that did not answer. Since v3.4.0 that tooltip is on the header of every page, not only the dashboard; the pill shows the mode name in Access Point, repeater and bridge modes. **What Connected means (v3.7.7).** The header and the card say **Connected** only while the router has a WAN address *and* its own internet check (Network Monitoring, 4.19) passes on that line; with an address but a failing check they say **No internet** in red, matching the WAN LED. IPv6 counts as up only while the router has a working IPv6 default route, not merely an address. After an ISP outage the router asks for Native IPv6 again once, so IPv6 returns without a reboot.
- **Clients** — the connected-device list grouped by band; **View List** opens the full Devices page.
- **Security Posture** — sixteen rows: firewall (SPI), DDoS protection, remote/cloud access, admin login (HTTPS only / HTTP + HTTPS, LAN-only / WAN reachable), SSH access, JFFS partition and custom scripts, DNS rebind + DNSSEC, Wi-Fi encryption, MLO, WPS, UPnP, QoS engine, **Gatekeeper**, **Warden**, **Rule Status** (the cached result of 4.1.1a; it never starts a walk) and **Security Review** (2.9): amber *Disabled* or *No baseline*, green *Baseline* with the last check time, red *Review* with the number of changes and login notices waiting — the same report the amber bar reads. After a boot the row shows *Baseline* in amber until the first check, which can take up to 10 minutes. Every row is clickable and takes you to the page (and tab) that owns the setting. The Security Review row also reads *Review* (red) when the accepted baseline or the watch rules were changed, or the baseline deleted, outside the Firewall page, and an amber *Baseline* while the baseline has no seal yet (once after updating to v3.8.4); the bar above the dashboard is red in the first two cases (4.1.1b).
- **Radio tiles** for each band, showing the SSID in its real case, and **USB tiles** per physical port (a hub shows as connected with a device count). A disk selector appears on the Storage card once two or more disks are attached.
- **System** — CPU load, memory, temperature, uptime, and the **firmware-update banner** at the top of the page when the check has found a release. A second crimson
  banner, **Wi-Fi needs a power cycle**, appears only while MLO is on and the last start was a restart without a
  power-off that left the radios' MLO link down (2.8).
- **Mesh Nodes** and **AiMesh** cards where applicable.

**Navigation**

- The **left rail** is identical on every page. At the top is a live 24-hour router-time clock; above the "General" heading is the **Language** selector (all 25 languages; the active language is shown selected and English can always be chosen). Menu entries are the stock sections plus Reaper's own (Devices, Gatekeeper, Bastion, AI Advisor on the MCP build). Installed **addons** (amtm, Diversion, scMerlin and the like) are gathered into one dedicated **Addons** section at the end of the rail (v2.7.5) instead of being scattered through the stock menus. It behaves like every other menu entry: clicking it **opens the first installed addon page**, and the rest appear as tabs across the top. Until v3.1.2 it was the one rail item that did not navigate — it unfolded a sub-list instead, which read as the menu misbehaving. An add-on registers its page by inserting a line into the menu tree after the stock page it extends; since v3.2.8 the stock lines Reaper retired (the firewall, wireless, firmware, backup, Sysinfo, QoS, statistics and connections pages) are kept as hidden anchors, so an installer written for stock Merlin, Skynet among them, still lands its tab in the Addons section. An external "Help & Support" link opens in a new tab. At the foot of the rail a small **scythe mark** opens the About page; it stays at the bottom of the window while a long menu scrolls beneath it.
- **Tabs** run across the top of pages that have them (QoS / QoS Diagnostics under Traffic Manager; Warden / Dreadwatch / Wallguard / Encrypted DNS under Bastion; USB Disks as the last tab of USB Application (v3.4.9); Long-Term Storage and Data Export under System Log; Diagnostics and Firmware under Administration; Policy Routing next to VPN Director under VPN).
- **Unsaved changes.** A Reaper page that keeps your edits until Apply or Save says so: *Unsaved changes: N* and a **Discard** button (QoS, Policy Routing, WAN Ports, Wallguard and Dreadwatch as well since v3.6.3).
- Every page lands scrolled to the top. The admin session logs itself out after the idle time set under Administration → System → *Auto Logout* (**30 minutes** at factory; 0 turns it off). Before v3.1.2 the dashboard used a fixed 15 minutes whatever that setting said.
- **Overlays.** An apply, reboot or firmware flash puts up a full-screen veil that locks the header and rail; it shows an elapsed-time heartbeat so a stalled operation looks different from a working one, and on the firmware page a Close button appears on any terminal state. After a firmware flash the page polls for the router's return and sends you back to sign-in. A stock pop-up panel inside the frame (the AiMesh client card, for example) opens centred in the part of the page on screen, however far down it is scrolled (v3.6.5).
- **Theme.** The Reaper look (matte black, crimson, jade and amber accents) is applied to stock pages by a web-server filter. It is always on: the switch that turned it off left Administration → Tweaks in v2.5.9, because Reaper's own pages, and the stock pages it replaces, depend on it. The AiMesh and Network pages are the exception: since v3.6.5 they link a Reaper stylesheet of their own with the same look, the router injects nothing into them, and their stock white / ROG / TUF themes are gone. The sign-in, set-password and logout screens show an animated model header that plays once.
- **Tablets** are supported (the frame pans horizontally when a page is wider than the column). **Phones** get a first fit since v3.1.0: below 680 px the rail collapses into a sticky strip of icons under the header and the page takes the full width. Since v3.6.5 every Reaper page fits the screen at 402, 375 and 320 px: a settings row is one column and a data table scrolls sideways in its own box with its headers whole, and the header's ? / Reboot / Logout buttons are one group that fits beside the logo or wraps whole.

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

The page no longer runs `iptables`, so auto-refresh is cheap; raw chains are still available over SSH. The **Auto refresh** switches on Status and Rule Status are settings of the router: they stay as set through a reboot, a firmware update and from any browser, and are part of the settings backup.

**Example.** You add a port forward, apply it, and the Forwards table shows your rule — but Status still reports the engine inactive. That means the generated ruleset did not run (most often the LAN was not up yet at boot). The rule exists in your configuration and does nothing until it does.

<a id="412-rule-status"></a>
#### 4.1.1a Rule Status

**What it is.** The firewall saying what it is actually doing, per feature, after every change. Each feature owns a few **witness packets** — an ingress interface, source and destination addresses, a protocol and port, a connection state — and the verdict it promises. A small read-only walker (`reaper_fwsim`) pushes each witness through the **live** tables in kernel order (raw, mangle, nat PREROUTING, the routing decision, filter INPUT or FORWARD, POSTROUTING) and reports the verdict together with the rule that decided it. It runs at the end of every firewall apply, on a timer from the watchdog, and when you press **Re-check now**.

The rows are grouped the way the features are: core reachability (LAN to WAN, DNS at the router, WAN unsolicited dropped, management ports, DHCP), port forwards (one pair per saved rule: translated, then passes FORWARD — plus, for a forward restricted to certain sources, a row proving a *different* source is **not** translated), UPnP, VPN (the servers you have enabled, each policy-routing rule's mark, the Killswitch), Gatekeeper (a blocked device is refused everything, DNS included, except the router's own admin page — the escape hatch; an internet-only device reaches the WAN but not the LAN), Warden (the router and its LAN are never in a ban set; the allow list is consulted before the ban list; each blocked country has its rule; the drop chains end in DROP; outbound is checked separately from inbound), the rules engine, Service Intercept (the service is redirected, *and* the host it is redirected to is exempt from its own redirect), the front hooks, each guest network (isolated from the LAN, reaches the WAN, DNS at its gateway), the flood guard, and IPv6 equivalents where the router has IPv6.

Two kinds of row are not packets. Some are **shape** checks — the walker looks at the tables rather than sending anything through them, because the promise is about structure: a chain exists, a chain ends in an unconditional DROP, the allow list is checked before the ban list, the flood guard is rate limited. (A rate limit always lets a flow's *first* packet through, and the first packet is the only one a walker has, so "is the guard armed?" is the only honest question to ask of it.) And **Killswitch** rows read somewhere else entirely: a VPN client's Killswitch is not in the firewall tables at all — it is a routing rule that refuses the marked traffic — so the walker reads the router's routing policy alongside the tables. That row is the difference between a Killswitch that is working and one that was never installed, which otherwise looks exactly the same from inside the firewall.

Finally there is one row that is always **Not applicable** on purpose, named *Out of scope for the walker*. It lists what a walk of the tables cannot see: reverse-path filtering, hardware-accelerated flows that bypass the firewall entirely, traffic between two devices on the *same* network (switched, not routed, and enforced by ebtables — the Gatekeeper row for an internet-only device therefore witnesses the cross-network leg), and drops inside the closed-source wireless and AiMesh components. It is there so a board full of green rows cannot be read as a clean bill of health for things nothing here checked.

**It is advisory.** Everything on this tab is information: the walker reads the tables and writes a report, and nothing reads that report to act on it. A red row is something to look at, not a fault the router has confirmed — the two commonest reasons a healthy box shows one are the witness address itself (see below) and a match the walker does not model — so the count never lights the menu, never turns the dashboard red, and never makes the watchdog declare a failure or write an incident bundle. The watchdog logs one advisory line when the set of red rows changes, and the diagnostics bundle lists them under 14g as information.

**The witness addresses are chosen, not fixed.** On the WAN side the walker tests its candidate source against every address set the live tables match on — a documentation-range address can sit inside a threat feed, and a witness that is itself banned tests the ban, not the port forward — and takes the first one nothing claims; the report says which. On the LAN side, when *Administration › System › Only allow specified IP address* is on, the witness host is one the list allows, because that is the only client the router promises anything to. The same is done for the IPv6 WAN source, and when the admin list allows an address *outside* the LAN, WAN management and WAN SSH are witnessed from that one (with only LAN addresses listed, those rows say so instead of failing). All choices are shown in the report's `wansrc`, `wan6src` and `lanhost` fields.

**It knows an intended exposure from an accident.** A DMZ host turns the "unsolicited WAN traffic never reaches a LAN host" rows into notes and adds a row that witnesses the DMZ itself (handed to the host, and passes). Networks you have deliberately linked in SDN access turn the guest-isolation row into a note, because isolation is then a per-pair question. With dual WAN the rows aim at whichever unit is primary. Two rows watch what no configuration asks for: an unforwarded high port on the router's own address must not be translated anywhere (a leftover catch-all forward would show here), and invalid-state packets from the WAN must be dropped both toward the LAN and toward the router — the latter is an explicit stock rule an early accept can shadow. Your own port forward of WAN port 80 to a LAN server turns the "WAN port 80 is closed" row into a note naming the server: the router's own port 80 stays closed, and the forward is witnessed in its own rows.

**Reading a row.** *OK*: the promise holds and the rule column names what delivered it. *Unsuccessful*: the live tables do not deliver it, and the rule column names what caught the packet instead — that is the thing to fix. *Held*: a zone policy that allows a path into or out of an isolated guest network. The policy is saved correctly, but guest isolation (4.21) runs before the rules engine and keeps the path closed, by design. The note under the rule names the guest network (the bridge in the isolation rule that held it); to open the path, link the two networks with Access Intranet on the Network page. A held row is never counted as Unsuccessful: the tab's summary, the Status note, the confirm window and the dashboard count it on its own, and neither the watchdog nor the diagnostics bundle treats it as a fault (14g lists held rows with their note). Each guest network also shows the paths you opened for it (4.21): **reaches chosen device** rows, one per main-network device you picked that the router actually opens (it has a DHCP reservation inside the main LAN and is not an AiMesh node) - a guest opening a connection to it must be accepted, and if your own Firewall rule decides first, the rule column names that rule and the note says it is yours; and a **discovery (mDNS)** row, open while the network has service types picked and **AP Isolation** is off, closed otherwise. The *isolated from the main LAN* row is still checked against a main-network host you did not pick. With *Zone policies may open one-way paths from the main network into isolated guest networks* on, a zone policy from the main network into a guest network is checked like any other policy, and a second row (*reverse stays closed*) checks that the guest network still cannot open a connection back; with the switch off, such a policy is *Held* and its note names the switch. A policy into a Guest Portal network is always held; a policy whose source is a guest network stays held with the Access Intranet hint. *Inconclusive*: a match the walker does not model (string, u32, time, policy) sits on the path, so the row is not judged rather than guessed — note this does **not** mean the row is degraded or half-working; nothing is known to be wrong with it, the walker simply declined to assert. *Not applicable*: the router has no such network yet (no IPv6, no WAN address). The pill colours still carry the same reading at a glance — jade for OK, amber for Inconclusive, outlined amber for Held, red for Unsuccessful, grey for Not applicable — but the word is what the row means, so the tab stays readable to anyone who does not separate those colours. A banner above the table says when the filter table is still the boot-time skeleton, which means the full ruleset never loaded and nothing else on the tab matters until it does.

**How to use it.** Look at it after every Apply and after a reboot, the same way as Status; the difference is that this tab tells you *which* promise broke and *where*. Two rows are worth knowing by name: a Gatekeeper-blocked device that reaches the WAN, and a port forward that is translated but then dropped — both have been real field incidents, and both are exactly what a red row here would have shown on day one. Nothing on the tab changes the firewall; the walker only reads the tables and writes a report, and nothing acts on that report. The same report appears in the diagnostics bundle (section 14g, as information), is logged by the watchdog as one advisory line when the set of red rows changes, and is shown in the Rules tab's confirm window before you press Keep.

**Example.** You add a guest network. Its three rows appear at once: isolated from the LAN (drop), reaches the WAN (accept), DNS at its gateway (accept). If "reaches the WAN" is red and the rule column says `filter/FORWARD policy DROP`, no rule accepts that bridge toward the WAN — the network exists, its clients get addresses, and nothing they send leaves the router.

#### 4.1.1b Security Review

**What it is.** A change detector for the places router malware and mistakes persist: `/jffs` scripts, configs, SSH keys and add-ons, the cron table, the settings that expose the router to the internet and Reaper's own protection switches. It is a card on **Firewall → Status**, an amber bar on the dashboard and a row of the dashboard's Security Posture card. It only reports; it never undoes anything.

**How to use it.**

1. **Firewall → Status**, Security Review card: switch it on.
2. Look at what the router holds now (your scripts, keys and add-ons), then press **Accept current state as baseline**. Nothing is reported before a baseline exists.
3. From then on, check the card when the dashboard shows the amber bar or the posture row reads *Review*. For each listed item decide: your own change → tick it and **Accept**; a file that legitimately changes all the time → tick it and choose **Existence only**, **Ignore** or **Ignore folder** (each writes a watch rule); something you did not do → investigate before accepting (start with the file's contents and the system log around its date).
4. Add watch rules for add-ons you run (below) so their normal churn stops showing up.

**Security review (2026-10-19).** Off by default; the switch is on the Firewall page's Status tab. Once on, every self-monitor tick inventories `/jffs/scripts`, `/jffs/configs` and `/jffs/.ssh/authorized_keys` (content hashes and modes), the other files in `/jffs/.ssh` (size, date and mode — a private key is never hashed), `/jffs/addons` (name, size and date), every cron entry that is not one of Reaper's own (a Reaper job counts as its own only with the exact command the firmware installs for it, in each of its forms), and the settings that expose the router to the internet (NAT, port forwards, DMZ, UPnP, remote web access, SSH, Telnet, custom scripts, the WAN DNS servers, remote syslog, the firewall master switch, cloud sync; since v3.8.4 also the admin user name, Access restriction and its list, the router's web ports, SSH password logins, WAN ping replies, the second WAN's NAT, UPnP and DNS switches, FTP, Samba and its share mode, SNMP, the PPTP, IPsec, WireGuard and OpenVPN servers, the LAN and IPv6 DNS servers, DNS-over-TLS and its servers, DNS Director and its rules, static routes, DDNS, the DoS, network-service, URL and keyword filters, the firmware update check, the beta channel and the signature override, WPS and the Encrypted DNS block), together with Reaper's own protection switches (Warden and its feeds, country list and self-filter, Dreadwatch and its feeds, Gatekeeper and its default, Wallguard, the rules engine, policy routing, the Encrypted DNS server) — a protection turned off is listed like any other change. Since v3.8.4 the lists that let traffic through are watched as files too: Warden's Whitelist and custom feeds, and Dreadwatch's never-block names, its sources and the devices that skip it (`/jffs/rwarden`); a list that only blocks (Warden's Ban list) is not. When a firmware update widens what is watched, the newly watched settings — and, once, those list files — are adopted into your accepted baseline as they stand, with one log line naming them, rather than reported as changes; after that, an edited or a new list file is a change like any other. Nothing is reported until you press **Accept current state as baseline**; after that, anything added, changed or removed is listed on the card, announced once in the system log (`rwatch: security review: N change(s) …`) and shown as an amber bar on the dashboard until you accept the new state. It is advisory end to end: nothing is undone, no failure is declared and no incident dump is written, because the changes it sees are most often your own — a new script, a port forward, an add-on update. What it is for: persistence and exposure are how router malware survives a reboot, and a change you did not make is the signal. A baseline you accept is written to `/jffs/reaper/review/baseline`; the full backup carries it. The check waits for the 5-minute boot grace and skips a tick while a Firewall rules change is waiting for Keep. The report itself is not kept across a reboot, so after a boot the card says *no report yet* and the posture row shows **Baseline** in amber until the first check, which runs 5 minutes after boot (the grace) whatever the tick's alignment.

**Watch rules (v3.4.8; a list since v3.5.0).** `/jffs` has expected churn — an add-on rewriting its stats file every hour — so the card keeps **Watch rules**, shown as a list under the report: each rule is a mode and a pattern. The **Add** form under the list takes a mode and a pattern; a new rule goes first, and the first matching rule wins. Each row has **Delete**; **Delete selected** and **Delete all rules** act on several at once, and **Edit as text** shows the raw rules, one per line, for pasting or bulk edits. With no rules, every item is watched in full. `hash` reports any change of content, `meta` a change of size, date or mode, `exist` only a file appearing or disappearing, `ignore` stops watching. A pattern is a full path with `*` and `?` wildcards (`/jffs/addons/diversion/*`), `cron:` and a cron-line pattern, or `nvram:` and a setting name. The first matching rule wins, and anything no rule matches keeps its default: `hash` for `/jffs/scripts`, `/jffs/configs` and `authorized_keys`, `meta` for the rest of `/jffs/.ssh` and for `/jffs/addons`. A private SSH key is never hashed, whatever a rule says. At most 100 rules; quotes, backslashes and backticks are refused. The rules live in `/jffs/reaper/review/rules`, so they survive firmware updates, and they travel with the settings export. They are part of the seal (below): edit them on this card. A rules file edited over SSH, or replaced by importing a settings file with different rules, shows the red row until you accept the current state again. An ignored path disappears from the report without being reported as removed. When a rule changes how an item is watched, its row turns grey with the status *rule changed*: that is not a change to the file, it is not counted as unreviewed, and **Accept** records the new mode.

**Accepting (one bar for the ticked rows, v3.4.9).** Every row has a tick box, and the header has a select-all; at most 100 rows at a time. The bar above the list shows *N selected* and the actions that fit every ticked row (a greyed action says why on hover): **Accept** takes the ticked items into the baseline, **Existence only** (files only) and **Ignore** write a rule for each exact path, and **Ignore folder** writes one for each directory (`dir/*`). The rules are saved once, ahead of the existing ones, without duplicates; a save that would pass 100 rules or 8 KB is refused before it is sent. Accepting a selection is one request and one log line naming the items; an item that is no longer listed refuses the whole selection and nothing is written. **Accept current state as baseline** still takes everything at once. Every acceptance and every rules save is written three ways: a `reaper-audit: review …` line in the system log naming what was taken in (counts by status and up to 20 items), the router's audit trail, and the **Acceptance log** on the card — time, the address that did it, the action and what it covered. The card shows the newest 10; `/jffs/reaper/review/accept.log` keeps 200.

**The seal (v3.8.4).** When you accept a baseline, the router stores a fingerprint (SHA-256) of the baseline file and the watch rules file together, outside `/jffs`. Every check recomputes it. If it no longer matches, the baseline or the rules were changed by something other than this card, and the card says so in a row at its top:

| Row | Colour | What happened | What to do |
|---|---|---|---|
| *The accepted baseline or the watch rules were changed outside this page.* | red | The baseline file or the rules file was edited, replaced or restored without an Accept on this card: over SSH, by a script, or by importing a settings file that carries different watch rules. | Read the whole list (every item is shown as unreviewed, what differs from the file on disk first). If it is all yours, **Accept current state as baseline**. If not, investigate first. |
| *The accepted baseline was deleted outside this page.* | red | The baseline file is gone but its seal is still stored. | As above; or **Reset baseline** to start over. |
| *This baseline has no seal.* | amber | The baseline was accepted by a firmware older than v3.8.4, or the seal was cleared (a factory reset of the settings that kept `/jffs`, a full backup made before v3.8.4). **Every router with an accepted baseline shows this once after updating to v3.8.4.** | Check the list and **Accept current state as baseline** once. |

While one of these rows is shown, nothing on the router is trusted to compare against: every watched item is listed as unreviewed, single rows cannot be accepted (only **Accept current state as baseline** records a new state), and the dashboard shows the bar - red for the two red rows, amber for the third - and *Review* (or an amber *Baseline*) in the Security Posture row. One line per change of that state goes to the system log (`rwatch: security review: the accepted baseline or the watch rules were changed outside the Firewall page (fingerprint sealed at the last Accept: ..., found now: ...)`). Nothing is repaired or undone. The check that follows a correct Accept removes the row. When a firmware update widens the list of watched settings, the router adds them to your baseline itself and renews the seal; that does not show a row.

**What this does not stop.** Someone who already has root on the router (an SSH session, a custom script) can change the stored fingerprint as well as the files; the seal does not protect against that. Nor does it stop a signed-in admin session (yours, or one left open or taken over): that session can accept changes, as it can restore a full backup, flash firmware or import a settings file. What the seal does is make an edit of the baseline or of the rules by anything that only writes `/jffs` show up instead of passing unnoticed. A settings file, or a page that posts settings, cannot switch the review (or the self-monitor that runs it) off: that is refused and logged, and only this card's switch does it. Watch rules replaced by an import show the red row until you accept.

The same card lists **failed-login bursts**: ten or more failed SSH or web-interface logins from one source inside one check (5 minutes) become a notice — source, count, time — plus one log line per source per hour (`rwatch: security review: N failed ssh logins from …`); **Accept** clears them. The self-monitor reads the system log from where it left off, so a rotated log loses nothing. It only reports: the IPv4 SSH brute-force lock-out is the stock one, and the web interface has its own lock (4.27.2): five wrong passwords refuse that address, and 20 failures on one side within 5 minutes lock that side.

#### 4.1.2 General

**What it is.** The base Asuswrt firewall: the master on/off switch, DoS protection, whether the router answers pings from the internet, which packets get logged, an allow-list of addresses permitted to reach the router's own services from the WAN, and the separate IPv6 firewall.

**How to use it.** Leave the master switch on (it is on at factory). DoS protection is off at factory; turn it on unless a service of yours needs bursts of new connections from the internet. Leave "respond to ping from WAN" off unless you have a specific reason — answering it confirms the address is live to anyone scanning. Remember that the IPv6 firewall is genuinely separate: IPv6 traffic is not translated, so every device on your LAN has a globally routable address and only this switch stands in front of it.

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
- **Direction decides what a rule can see.** An **Inbound** rule sees only traffic addressed to the router itself (DNS, DHCP, the admin page), so its destination is always one of the router's own addresses. To keep one network away from another, use **Forwarded**. An Inbound "home → kids: Drop" rule does not isolate anything; it can only match the router's kids-side address, which is how it ends up blocking the kids network's DNS and DHCP.
- **Objects that overlap act as both.** If a `home` subnet object also covers the kids range (a `/16` where a `/24` was meant, say), every kids device is also "home" and matches rules written for home. Keep each network's object to exactly that network. A red Rule Status row whose rule column names one of your own rules is the usual first sign.
- **An empty source or destination means "anything". A named object that currently resolves to nothing is not the same thing** — that rule is left out entirely rather than becoming a rule that matches everything. A domain object that has not resolved yet, or an emptied group, therefore fails to a missing rule, never to an unintended block.
- **AiMesh nodes are exempt (v3.6.5).** Traffic a paired node sends itself skips the Inbound and Forwarded rules and every Service Intercept, so one broad rule cannot cut a node off. The node list is the shared `reaper_aimesh` set, refreshed from the router's AiMesh registry each time the rules apply and on every watchdog tick; Gatekeeper and Policy Routing read the same set. Devices connected *through* a node are not exempt.

#### 4.1.4 Objects

**What it is.** Named things you can point rules at, so you write `printer` instead of an address you have to remember. Three kinds live here: address objects (a host or subnet, an address range, a MAC address, a domain name, or a country), address groups that bundle several objects under one name, and service objects that name a protocol and a set of ports.

**How to use it.** Name objects after what they are, not where they are — `printer`, `kids-tablet`, `nas` — so a rule still reads correctly after you renumber your network. Edit the object when a device moves and every rule using it follows automatically. Use a group when the same set of devices keeps appearing in rules.

**Example.** Create an address object `nas` of type host with value `192.168.50.20`, and a service object `smb` with protocol TCP and ports `139,445`. A rule blocking `smb` to `nas` from your guest zone then reads as plain English and needs no comment.

**Worth knowing.**

- **Domain-name objects** fill in as the router resolves the name, and entries expire after about an hour so a rotating content network does not accumulate stale addresses forever. They only see lookups the router's own resolver answers — a device using its own DNS server, or encrypted DNS, is invisible to them. A background refresh every ten minutes covers the common case. Members are saved to flash after each pass and replayed at boot.
- **A long list pastes in one go.** Domain and address lists take one entry per line or comma-separated, and the editor normalises the whitespace and line endings for you, so a forty-domain object goes in as a single paste rather than a few entries at a time. If something in the paste cannot be accepted the editor says so and keeps saying so — it never silently drops the remainder. These lists live on the router's internal flash (`/jffs`), not in nvram, which is what lifted the old size ceiling; a 40-domain object therefore saves only from v2.6.9 onward.
- **MAC objects** only work as a *source* on traffic into or through the router. A MAC address does not survive being routed, so it cannot be used as a destination or on outbound traffic.
- **Object names** are restricted to letters, digits and underscores; anything else is dropped and logged.
- **A group holds at most 16 members.** The page refuses a larger one; split it into two groups.
- **Country objects** are owned by Warden, not by this engine — set them up on the Warden page.

#### 4.1.5 Zones

**What it is.** A zone is a name for a set of interfaces — `lan` for your bridge, `wan` for the internet, `vpn` for tunnel interfaces. A zone policy then says what happens by default when traffic moves from one zone to another.

**How to use it.** Zones let you write intent once instead of repeating interface names in every rule. Start with the broad policy — for example guest to LAN denied — and then write specific Rules for the exceptions you actually want. Interface names accept a trailing `+` as a wildcard, so `tun+` covers every tunnel interface without listing them.

**Example.** Define a zone `guest` with interface `br1`, and a zone `lan` with `br0`. Add a zone policy: source `guest`, destination `lan`, action `Drop`. Guests can now reach the internet but nothing on your home network — and you have not written a single address anywhere.

**Worth knowing.** A zone policy is the weakest statement in the engine; both explicit Rules and Egress defaults override it. That is what makes "deny everything, then allow what I need" workable. A zone holds at most 8 interfaces (a `+` wildcard counts as one), and at most 64 zone policies can be saved; the page refuses more.

**Guest networks.** Guest isolation (4.21.3) runs before the rules engine, so a zone policy cannot open a path into an isolated guest network; Rule Status shows such rows as *Held*. The Zones tab switch **Zone policies may open one-way paths from the main network into isolated guest networks** (`reaper_fw_zpol_guest`, off by default; needs the rules engine on) changes one case: an Accept policy whose source is the main network, or a network paired with it through Access Intranet, and whose destination is an isolated guest network (not a Guest Portal) opens that path. Replies come back, but the guests still cannot start connections toward the main network. The first policy that matches a pair decides. A guest network as source, guest to guest, WAN, VPN and wildcard zones never open anything. Apply restarts the firewall.

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

#### 4.1.8 Service Intercept

**What it is.** A forward sends traffic *arriving from the internet* to a device inside your
network. Service Intercept is the other direction: traffic **leaving** a device on your network
for a chosen service is sent to a server *you* pick, whatever address the device thought it was
using. It exists for the devices that ignore what DHCP tells them and have a public server
compiled into their firmware — the classic case is time (NTP), where a thermostat or a TV will
happily ask a hard-coded internet server forever.

Two modes: **Send to a server** points the traffic at a machine on your network; **Send to the
router** points it at the router itself, for when the router *is* the service.

**How to use it.** Pick the zone the clients are on, the service port to catch, and the server to
send it to. The classic NTP setup is: From `LAN`, protocol UDP, intercept port `123`, server
`192.168.50.10`, server port `123`, return path **Auto**.

**Two things it does for you, which are the whole reason this is not a raw firewall rule:**

- **The server is always exempt from its own rule.** Without that, the server's own request to
  its upstream would be caught and pointed back at itself — it could never sync, and the fallback
  the whole arrangement exists for would be dead. You do not have to remember this; it is
  automatic. The **Exempt** field is for anything *else* that should be left alone.
- **The return path.** If the server sits on the same network as the clients, it answers them
  directly from its own address and the client throws the reply away — it was expecting the
  address it originally asked. **Auto** detects exactly that case and adds the address
  translation that routes the answer back through the router. If the server is on a different
  VLAN it correctly adds nothing, because the reply already comes back through the router.
  **Always** adds it everywhere, which hides the client's address from your server — fine for
  time, wrong for anything that logs per client. **Never** omits it.

**The router is never intercepted.** Its own traffic is generated locally and never passes the
point where interception happens, so the router keeps its own route to the outside no matter what
you set here. The same property means a Rules-tab block on forwarded traffic cannot cut the router
off either.

**What you give up.** Interception removes the *clients'* fallback. If the server is down, a
client asking a public server is sent to a dead address and gets nothing — it does not fall
through to the internet. A firewall rule cannot health-check. For time this is usually an easy
trade (clocks drift slowly), but decide it deliberately. The one exception (v3.1.9): an intercept
aimed at the DNS server the resolver health check watches (4.14a) is closed while that server is
down and reopened when it answers.

**IPv6 (v3.3.7).** **Send to the router** works on both IPv4 and IPv6. **Send to a server** needs a
concrete IPv6 host to redirect to, so it covers IPv6 only when you give the server's IPv6 address in
the optional IPv6 field; without one, a device on a dual-stack network can still reach a public
server over IPv6, and a Rules-tab block for the service on IPv6 closes that path.

**Limits.** It matches on a port, so it cannot catch a device that fetches the same thing over HTTPS.

**Not for DNS.** Reaper already ships **DNS Director** for exactly this job on DNS, and it is the
better tool: per-client policy, a choice of upstream resolvers, and it blocks DNS-over-TLS on port
853 as well — which a port-53 intercept would sail straight past. Use DNS Director for DNS.

#### 4.1.9 Network Services

**What it is.** The long-standing Asuswrt service filter. It matches traffic leaving your LAN by source address, destination address, port and protocol, and either blocks the listed traffic or permits only the listed traffic, within a daily time window.

**How to use it.** Choose the mode deliberately. Block-list blocks what you list and allows the rest. Allow-list allows only what you list and blocks everything else — which is far stricter, and will cut off things you forgot, so add DNS and the rest of your essentials before you switch it on.

The time window applies to the whole list, not per entry. If you need per-device or per-rule scheduling, use the Rules or Egress tabs instead.

**Example.** To stop devices using outside DNS servers and force them through the router: mode Block-list, source blank (meaning every device), destination blank, destination port `53`, protocol UDP. Add a second entry for TCP. The router's own resolver still works because that traffic never leaves the LAN.

**Worth knowing.** This filter needs the router's clock to be correct for the time window to mean anything. If time has not synchronised yet, the page says so.

#### 4.1.10 URL Filter

**What it is.** Blocks web requests whose address contains one of the keywords you list.

**How to use it.** Keep the entries short and distinctive — a fragment of the domain rather than a full address, because the same site is reached by many different URLs. Test with one entry before adding a long list.

Be realistic about the limits. This matches the request as it goes past, so it works on plain, unencrypted requests and misses almost everything on the modern web, which is encrypted. Treat it as a nudge for casual use, not a control. For blocking that holds, use a domain-name Object in a Rule, or block at the DNS level.

**Example.** Entry `example-game.com`. Plain requests to that domain are refused; the same site over HTTPS is not, which is why this tab is the weakest of the blocking options here.

#### 4.1.11 Keyword Filter

**What it is.** Blocks web pages whose content contains one of the words you list.

**How to use it.** The same realism applies, more so: the filter has to be able to read the page to match a word in it, so encrypted sites pass untouched. It also matches inside ordinary text, so a short or common word will block pages you did not intend — prefer distinctive phrases, and add them one at a time.

**Example.** Entry `freegamedownload`. A plain page containing that string is blocked. A page that is encrypted, or that spells it differently, is not.

#### 4.1.12 Logging

**What it is.** Chooses which firewall decisions are logged — nothing, dropped packets, accepted packets, or both — and shows the recent entries. Since v3.7.5 the lines go to the firewall log collector (`rflogd`), not to the system log: it keeps them in RAM (`/tmp/reaper/fwlog`), on the long-term store when that lists the firewall log (4.11), and sends each one to the remote log server set on the System Log page.

**How to use it.** Leave it off for normal running. A busy connection can log thousands of lines a minute: they cost CPU, fill the collector's RAM ring so the lines you wanted roll out of it, and with a long-term store use flash or disk space. Read the lines on this tab or in the System Log page's **Firewall** view (2.12). Each logging rule may write up to 10,000 lines a second, with bursts of 10,000; past that the lines are held back, never the packets, and counted. If the collector is not running, the rules fall back to the system log at 10 lines a second with bursts of 50, so under **Accept** or **Both** a busy network then shows a sample of its connections, not every one. The line under the setting shows the collector's counts: lines recorded, lost, and held back by the limit.

**Remote log server (from the image after v3.7.5).** Each firewall line goes to the server as one UDP syslog message (RFC 3164, facility kern, severity notice, tagged `rflogd`), to the same address and port as the system log (`log_ipaddr`, `log_port`). The server must be an IP address: a name is not looked up, and the page then says that nothing is forwarded. A second line under the setting shows how many lines were sent and how many could not be (amber when any could not); a line that could not be sent is still in the router's own firewall log, and the first one in each minute is noted in the system log. The router keeps a send queue of about 2 MB for these messages, so a burst at the limit does not overflow it. At the full rate this is roughly 3 MB a second of log traffic, so give the receiving server a large enough receive buffer as well. UDP has no delivery guarantee: a message lost on the way or dropped by the server is not seen by the router. The diag reports the same counts in section 14.

Turn on **Drop** while you are diagnosing a rule that is not doing what you expect, look at the entries, then turn it back off. **Accept** and **Both** are for short, deliberate investigations only.

**Example.** A device cannot reach a service and you do not know which rule is stopping it. Set logging to Drop, reproduce the failure, and read the entries — each logged line names the addresses and ports, which tells you which of your rules matched.

**Reading the table.** The columns are Action, Time, Interface, Source, Destination, Protocol and Port. *Interface* is the interface the traffic **arrived on**, which is usually what tells you whether something came from your own network or from the internet. (Before v3.1.2 the first two headings were transposed and the third was labelled "Chain", which it never was.)

The Action badge distinguishes the source of each entry, and for Warden it distinguishes the **direction** too:

| Badge | Meaning |
|---|---|
| `DROP` / `ACCEPT` | the stock firewall or the rules engine |
| `WARDEN` | Warden blocked something **coming in** |
| `WARDEN-OUT` | Warden blocked something on your network **reaching out** to a flagged address |
| `WARDEN-SELF` | Warden blocked **the router itself** reaching out (see 4.3.1.8) |

Those three carry distinct prefixes in the firewall log as well (`REAPER-WARDEN`, `REAPER-WARDEN-OUT`, `REAPER-WARDEN-SELF`), so they can be told apart there too. If you are looking for outbound blocks and seeing none, that is usually not a fault — see 4.3.1.11.

#### 4.1.13 Limits, and things deliberately not built

- **Rule negation ("not") does not exist**, because an empty field already means "any" and an ordered pair expresses an allowlist (4.1.3). There is no tracer for an arbitrary packet you type in; Rule Status (4.1.1a) walks each feature's own witness packets.
- **The layer order is fixed**: Warden, then Gatekeeper, then the rules engine. An Accept rule here cannot let a geo-blocked source or a quarantined device through (v2.6.2).
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

**A Guest Portal network is the exception (from the image after v3.7.5).** A network with a guest portal has its own gate, the portal's sign-in page, so Gatekeeper leaves that network alone: its devices are not held, not listed on the Gatekeeper page and not shown the waiting room, and the system log names the exempt network (`gatekeeper: Guest Portal network(s) ... exempt`) each time Gatekeeper is applied. Devices on your other networks that are held or marked *Internet only* still cannot reach it. What a guest is asked for is set on the portal itself: the Terms of Service tick box, and a passcode when you switch on **Add your own Passcode** (up to 15 characters) - from the same image that switch is offered while you create the Guest Portal on the Network page, not only when you edit the network afterwards.

The waiting-room page works on an isolated guest network for an *unknown* device. An **approved** device on that network still cannot reach the router's pages — again, that is what *Access Intranet: off* means, and it is not a Gatekeeper decision. Devices on guest networks do get their hostnames.

#### 4.2.6 Reading the status

The page shows one of four states, and it is designed never to claim it is protecting you when it is not:

- **Enabled** — armed and enforcing.
- **Arming** — waiting for the network to come up after a boot. Normal for a short time.
- **Not enforcing — check the System Log** — red, and it appears if arming has not completed after 60 seconds. Devices are **not** being held. This is a real fault; the log will say why.
- **Off**.

A held device that opens a web page sees a themed **"Awaiting approval"** notice, shown automatically through the sign-in popup on phones and laptops, rather than a dead connection. That page is generated by the web server and stays in English.

While a device is held, the router answers its name lookups itself: every name resolves to the router's own
address, which is what lets the sign-in sheet appear, and nothing is looked up on the device's behalf - a held
device cannot reach, or tunnel through, the outside resolvers. The only other router service it can reach is
the sign-in page on the admin port, which keeps its usual login lock (see the limits below).

#### 4.2.7 Examples

**Seal the IoT.** Enable Gatekeeper, let everything grandfather in, then walk the Devices list and set every camera, TV, speaker and plug to **Internet only**. Nothing of yours changes; those devices lose the ability to reach your computers and storage. If your DNS is a LAN host, make sure it is set to **Approved** first (4.2.4).

**An evening visitor.** Set **Guest pass**, 8 hours. They get internet, never your LAN, and the pass expires without you having to remember.

**A new device you did not expect.** It appears in **Pending approval** with its name, connection type, band, and a flag if it is using a private address. Leave it pending — pending is already blocked — until you know what it is.

**Back out entirely.** Set *New devices* to **Alert only**, or switch Gatekeeper off. The admin page is reachable in every state, so this is always possible from a LAN device.

#### 4.2.8 Limits and gotchas

- **Phones using rotating private addresses reappear as new devices.** The pending list flags them. This is the single most common source of unexpected pending entries; it is the phone's privacy feature working, not a fault.
- **The device list is not in the stock settings backup.** It lives on the router's internal flash, and a factory reset with *clear all content and data logs* ticked (the default) clears it. Keep it with **Download full backup** or **Export settings** on **Administration → Backup & Restore** (2.5) if you have spent time on it.
- **Capacity is 512 devices**, tested to 300. The old 45-device ceiling is gone, and existing lists migrate at first boot. A write failure is logged rather than swallowed.
- The grandfathering step refuses to overwrite its list if that list is ever too large to load, and logs instead of failing quietly.
- Before v2.5.0, Block and quarantine were enforced only on the main LAN. That is fixed, and a quarantined device on a guest network now also gets the waiting page.
- A device's state is keyed on its hardware address, so it follows the device across address changes — but not across a deliberate address change by the device.
- **AiMesh nodes are never held.** Gatekeeper exempts every paired node; since v3.6.5 it reads the node list from the same shared `reaper_aimesh` set as the rules engine and Policy Routing (4.1.3).
- **A held device can still reach the admin sign-in page.** That is the lockout escape hatch: a computer that
  was asleep when Gatekeeper was enabled must be able to log in and turn it off. The page keeps the usual
  five-attempts lock. Everything else from a held device - your LAN, the internet, name lookups beyond the
  sign-in sheet - is closed.

### 4.3 Bastion

**The Bastion menu** holds Reaper's four blocking tools, one tab each: **Warden | Dreadwatch | Wallguard | Encrypted DNS**. Earlier versions called the whole menu Warden, after its first tab; the tabs are unchanged. **Each tool has its own switch and works on its own**: turn on any one, any combination or all four. All four are **off at the factory**.

They work at three different layers, and that decides what each one can and cannot see:

| Tool | Decides on | Where it acts | What a blocked device gets | Switch (nvram) | Default |
|---|---|---|---|---|---|
| **Warden** (4.3.1) | IP addresses: threat feeds, countries, your own lists | the firewall: chains `REAPER_WARDEN`, `RW_OUT`, `RW_SELF`, kernel `ipset` sets | the packet is dropped, no answer | `rwarden_enable` | `0` (off) |
| **Dreadwatch** (4.3.2) | host names on threat lists | inside the router's DNS resolver (dnsmasq), every network | NXDOMAIN ("no such name") | `rwarden_dns` | `0` (off) |
| **Wallguard** (4.3.3) | host names on ad, tracker and service lists, per device | inside the router's DNS resolver, every network | `0.0.0.0` / `::` (or NXDOMAIN, your choice) | `wallguard_enable` | `0` (off) |
| **Encrypted DNS** (4.3.4), server half | nothing: it carries lookups | `rednsd`, a DNS-over-TLS (port 853) and DNS-over-HTTPS (port 443) server | - | `reaper_dot_srv` | `0` (off) |
| **Encrypted DNS**, block half: port 853 switch | DNS-over-TLS and DNS-over-QUIC (TCP and UDP 853) to any outside server | the firewall chain `REAPER_EDNS` | a refused connection | `reaper_dot_block` | empty (off; follows `reaper_doh_block` until it is set) |
| **Encrypted DNS**, block half: DNS-over-HTTPS switch | port 443 to known DoH resolvers, DoH provider names | the firewall chain `REAPER_EDNS` and the resolver | a refused connection; NXDOMAIN for the provider names | `reaper_doh_block` | `0` (off) |

**Which tool for which job.**

| You want to | Use | Notes |
|---|---|---|
| Stop the internet's background scanning and known-bad addresses reaching the router and your forwarded services | Warden, threat feeds, Direction *Inbound only* | Works for every protocol, not just web traffic |
| Refuse traffic from or to whole countries | Warden, Country blocking | Review the list first (4.3.1.6) |
| Stop an infected device reaching a known command-and-control address | Warden, Direction *Both directions* | Address-based; complements Dreadwatch |
| Stop devices resolving malware, phishing and command-and-control names | Dreadwatch | Same answer for every device, except the devices on its own list (4.3.2.5a); Wallguard profiles cannot lift it |
| Block ads, trackers and telemetry | Wallguard | Per-device profiles, Unbreak, Why? |
| Different filtering per device or per guest network; block TikTok at bedtime; force safe search | Wallguard profiles (4.3.3.5, 4.3.3.6) | |
| Let devices encrypt their DNS and still be filtered | Encrypted DNS, server half | Add DNS-over-TLS upstream on LAN › DNS for the hop to the internet |
| Stop devices going around the router with their own encrypted DNS | Encrypted DNS, block half, plus DNS Director *Router* | |
| Stop devices using another plain DNS server | DNS Director (LAN › DNS), not Bastion | Global mode *Router* |
| Cut one LAN device off completely | Gatekeeper (4.2) | Warden's manual block list also can (4.3.1.7) |
| Allow or deny by port, schedule or object | Firewall rules (4.1.3) | |

**The order a connection meets them.** For traffic passing through or into the router, Reaper's layers run in a fixed order in the shared front chains: **Warden first**, then **Gatekeeper** (4.2), then the **Firewall rules engine** (4.1). A packet Warden drops never reaches the other two, so **a Firewall Allow rule cannot re-admit a Warden drop**; use Warden's whitelist for that. DNS Director's rules for port 853 and the Encrypted DNS block (`REAPER_EDNS`) sit after the front chains, among the stock firewall's own forward rules. Traffic the router itself starts meets only `RW_SELF` (Warden's router-traffic filter, if switched on) ahead of the rules engine's output chain.

**The order a DNS lookup meets them.** A lookup a device sends to the router (plain DNS on port 53, or over Encrypted DNS, which hands it to the same resolver) passes through:

1. **Wallguard safe search** (only for a device whose profile has it): a search engine's name is answered with its restricted address.
2. **Wallguard's lists** - checked before the resolver's cache, so a cached answer is covered too. If the resolver has its own answer for the name (your LAN's local names, an `address=` line, a DoH provider name or browser canary answered by the Encrypted DNS block, or a Dreadwatch threat name), Wallguard stands aside and that answer is given.
3. The resolver's **cache**.
4. **Dreadwatch** - a listed name, or a name under it, is answered NXDOMAIN and counted.
5. Forwarded upstream (your WAN DNS servers, or DNS-over-TLS upstream if switched on under LAN › DNS).
6. On the way back, **Wallguard checks every name in the reply's CNAME chain** (hidden trackers) for the device that asked.

A lookup that never reaches the router's resolver passes through none of this. That is the one limit all the DNS tools share.

**Living with the rest of the router.**

- **DNS Director** (LAN › DNS) decides *which* resolver a device uses. A device it sends to another server (a per-device rule, a guest-network profile or the global mode) is answered by that server, so Dreadwatch and Wallguard do not see its lookups; Encrypted DNS refuses it and, from v3.8.4, is not offered to it by DHCP (4.3.4.5), so it stays on plain DNS where DNS Director applies. Global mode **Router** sends every device's port-53 lookups to the router and rejects DNS-over-TLS and DNS-over-QUIC (TCP and UDP 853) to anything else; that is the setting that makes the DNS tools cover everything.
- **A LAN AdGuard Home or Pi-hole.** If devices ask the Pi-hole and the Pi-hole forwards to the router, both filter, but the router sees one device (the Pi-hole) for all of them: Wallguard profiles cannot tell devices apart and Dreadwatch counts everything under the Pi-hole's address. If the Pi-hole forwards straight to the internet, the router sees none of those lookups and Dreadwatch and Wallguard do nothing for them. If a DNS Director rule or a Service Intercept rule (4.1.8) redirects port 53 to the Pi-hole, Wallguard's page shows a banner naming the address the lookups go to; it names the server a router VPN client in *Exclusive* DNS mode sends lookups to as well. Pick one place to filter; if you keep the Pi-hole, set its upstream to the router so Dreadwatch still applies.
- **VPN.** A device running its own VPN app resolves through the VPN: no DNS tool sees it, and Warden sees only the VPN server's address. A router VPN client that is set to send its clients' DNS to the VPN provider takes those lookups past the resolver as well. Warden's whitelist must cover any VPN server you reach from a blocked country with the router-traffic filter on (4.3.1.8). Warden exempts the listen ports of enabled **WireGuard** servers; OpenVPN and IPsec servers are not exempted, so a client connecting from a blocked country or a listed address is dropped.
- **Policy Routing** (4.4) and Firewall FQDN objects learn addresses from the resolver's answers. A name Wallguard or Dreadwatch blocks is answered by the router itself and never resolves, so it adds nothing to those lists either.
- **Gatekeeper** (4.2): Warden runs before it. A device Gatekeeper holds or blocks is answered by Gatekeeper's own sinkhole resolver and cannot use Encrypted DNS.
- **AiMesh**: nodes are devices on your LAN, so Warden's LAN exemption covers them like any other LAN device. The Encrypted DNS block never refuses a node's own traffic: it skips the shared AiMesh node list, as Gatekeeper, the rules engine and Policy Routing do. Devices connected through a node use the main router's resolver like any other LAN device.

**Shared pieces.**

- Warden and Dreadwatch share one **list updater** and its schedule (Administration › Tweaks, **Warden feed update schedule**, `rwarden_sched`; empty = 04:30 daily), and the **Save block statistics** and **Reset interval** settings on the Warden page. With Warden off, the updater fetches only Dreadwatch's lists. Wallguard updates at 05:15 daily; the Encrypted DNS block's address list at 05:25.
- **Backups.** The Reaper settings file (2.5) carries all four tools' settings, lists, sources and API keys.
- **Security Review** (the dashboard's Security Posture card) reports a protection switched off like any other change.

**What is kept where.**

| Tool | Settings | Downloaded data | Counters |
|---|---|---|---|
| Warden | nvram `rwarden_*`; whitelist, manual blocks and custom feeds in `/jffs/rwarden/allow`, `ban`, `cfeeds` | kernel sets in RAM; cache `/jffs/rwarden/sets.ipset` | `/jffs/rwarden/counters` (Long-Term Storage: locked to JFFS) |
| Dreadwatch | nvram `rwarden_dns`, `rwarden_dns_feeds`; `/jffs/rwarden/dnsallow`, `dnssrc`, `dnskeys` (root only) | table `/tmp/reaper_nx/threat.db` (RAM); compressed copy `/jffs/rwarden/dns.k.gz` | `/jffs/rwarden/dns.counters` (RAM if statistics saving is off); optional history on Long-Term Storage |
| Wallguard | nvram `wallguard_enable`, `wallguard_mode`; `/jffs/wallguard/` (`lists`, `block`, `allow`, `allow24`, `profiles`, `assign`, `services`, `sched`, `safe`, `rewrite`, `keys`) | lists in RAM `/tmp/wallguard/lists` or on a USB volume; table `/tmp/wallguard/db` (RAM, always) | RAM, copied to `/jffs/wallguard/counters` at most hourly; optional history on Long-Term Storage |
| Encrypted DNS | nvram `reaper_dot_srv`, `reaper_doh_block`, `reaper_dot_block` | DoH address list `/jffs/encdns/doh.ips` | totals in RAM; optional activity log on Long-Term Storage |

Long-Term Storage (4.11) has a row for each optional history: **Wallguard block lists** (USB only), **Wallguard blocked lookups**, **Dreadwatch blocked lookups**, **Encrypted DNS activity**, and the **Encrypted DNS blocked-address list** (locked to JFFS).

<a id="43-warden"></a>
#### 4.3.1 Warden

##### 4.3.1.1 What it is, and when to use it

Warden is an opt-in **address firewall**. It drops traffic to and from IP ranges on public threat feeds, ranges assigned to countries you select, and addresses you list yourself. It is enforced in the kernel with `ipset` sets on IPv4 and IPv6; one set lookup decides however long the lists are. **Off by default** (`rwarden_enable` `0`).

**Use it** on a router with a public WAN address, to stop answering the constant background scanning; to refuse whole countries you never deal with; to stop an infected LAN device reaching known command-and-control addresses (Direction *Both*); or to keep your own block list.

**What it is not.** It decides on addresses only. A VPN, a proxy or a compromised host in an allowed country passes it; a malicious site on a shared CDN address is not on an IP feed. Treat it as a way to shrink exposure, not as a complete defence. Blocking by host name is Dreadwatch (4.3.2).

##### 4.3.1.2 Setting it up

1. Switch on **Warden** at the top of the tab.
2. Tick the **Threat feeds** you want (4.3.1.5). FireHOL Level 1 alone is the usual start.
3. Optionally add **Custom feeds**: up to eight lists of your own.
4. Tick countries under **Country blocking** (4.3.1.6). Review the list before you save.
5. Choose the **Direction** (4.3.1.8): *Inbound only* to start.
6. Add **Whitelist** and **Manual block list** entries, one address or CIDR per line (4.3.1.7).
7. Decide on **Log dropped packets**, **Also filter the router itself** and the statistics settings.
8. Press **Save & Apply**, then **Update feeds now** for the first download. Afterwards the lists refresh on the schedule in Administration › Tweaks (default 04:30 daily).

At boot, Warden arms at the first firewall build after the WAN comes up (the log says `boot: Warden arms at the first firewall build (WAN up)`), loading the last downloaded sets from `/jffs`, so a router that boots without internet still enforces the previous lists.

##### 4.3.1.3 The page, control by control

| Control | What it does |
|---|---|
| **Warden** switch and status pill | On/off (`rwarden_enable`). The pill reads *Enforcing* or *Disabled*. |
| Warning banner | The "noise-reduction layer, not a complete security measure" caveat. The × hides it in this browser. |
| *Protection is live but not persistent* banner | `/jffs` is off or read-only: blocking works, but the feed cache and counters cannot be saved. |
| Tiles | **Blocked packets** (since the date under the country table), **Last feed update**, **Feeds enabled** (built-in and custom), **Countries blocked** (amber with *N country list(s) empty* when a selected country has no addresses loaded), **Protocols** (IPv4, or IPv4 · IPv6 when IPv6 rules are active). |
| **Top blocked countries** | The five source countries with the most drops, a breakdown strip (below) and a *Live* pill that is green while the chains are armed. Refreshes every 30 seconds. |
| **Threat feeds** | FireHOL Level 1, Feodo Tracker (botnet C2), Spamhaus DROP, DShield top attackers. Rows marked *IPv4 only* have no IPv6 list. |
| **Country blocking** | A searchable checklist of 89 countries (**Filter countries** searches name or code). Tick to block, untick and save to unblock. |
| **Threat domains** card | A link to Dreadwatch, which blocks names; it is a separate tool. |
| **Custom feeds** | **Add feed** adds a row: **Name**, **List URL (https)**, **IPv6 list URL (optional)**; **Remove** deletes it. Up to 8. |
| **Direction** | *Inbound only* or *Both directions* (`rwarden_dir`, default `in`). |
| **Also filter the router itself** | Applies the destination checks to connections the router starts (`rwarden_self`, default `0`). Switching it on shows *Read this before turning it on*. |
| **Log dropped packets** | Writes a kernel log line before each inbound or outbound drop (`rwarden_log`, default `0`). |
| **Save block statistics** | Keeps the counters on internal flash across reboots, restarts and upgrades (`rwarden_stats_save`, default `1`). Off: counts since the last firewall rebuild only. Also governs Dreadwatch's counters. |
| **Reset interval** | Never / 24 Hours / 7 Days / 1 Month / 3 Months (`rwarden_reset`, default `off`): clears the saved counts when the period has passed. Also governs Dreadwatch's counters. |
| **Manual block list** / **Whitelist (never block)** | One IPv4 or IPv6 address or CIDR per line (4.3.1.7). |
| **Save & Apply** | Stores the lists, applies the settings and rebuilds the rules. |
| **Update feeds now** | Saves, then downloads every selected feed and country list (and Dreadwatch's lists) at once. |
| **How Warden works** / **What the block count means** | Reference cards. |

##### 4.3.1.4 The order it decides in

This order answers most "why was this blocked / not blocked" questions. Traffic entering `REAPER_WARDEN` (from `INPUT` and `FORWARD`) is tested in this order; **the first match decides**:

| # | Test | Result |
|---|---|---|
| 1 | Arrived on loopback | exempt |
| 2 | DHCP (UDP 67/68; IPv6 546/547) | exempt |
| 3 | Part of an established connection | exempt |
| 4 | *Both directions only:* the destination checks (`RW_OUT`, below) | dropped if the destination is listed, otherwise continue |
| 5 | Source is on the **Whitelist** | exempt |
| 6 | Source is on the **Manual block list** | **dropped** |
| 7 | Source is on your LAN (IPv4: the LAN subnet; IPv6: link-local `fe80::/10`, ULA `fc00::/7`, the LAN's delegated prefix, and the global prefix of every other LAN-side network, guest and VLAN networks included) | exempt |
| 8 | UDP to the listen port of an enabled WireGuard server, addressed to the router | exempt |
| 9 | Source is in a blocked **country** | **dropped** |
| 10 | Source is on a **threat feed** | **dropped** |

The destination checks at step 4 run in this order: destination is loopback, the LAN or one of the router's own WAN addresses → skip the rest of step 4; destination on the Whitelist → skip; on the Manual block list, in a blocked country or on a feed → dropped.

What follows from the order:

- **Your LAN is exempt (step 7) before any feed or country is consulted.** No feed and no country can cut off a device on your network. Guest and VLAN networks use private ranges, which are stripped from every feed and country list (4.3.1.5), so no list can hold them either.
- **Established connections are exempt (step 3).** Enabling Warden or a feed update does not cut the session you are working in.
- **The Manual block list (step 6) comes before the LAN exemption.** That is how you block a LAN device, and it means **a manual entry covering your LAN blocks your LAN**. It is the one way to lock yourself out with Warden. A Whitelist entry (step 5) beats it and is the way back.
- **Outbound is checked at step 4, before the source exemptions.** On outbound traffic your own device is the source, so if the Whitelist came first, an entry covering the LAN would switch outbound blocking off for the whole network.
- **WireGuard (step 8)** sits after the manual block list and before countries and feeds. A phone on mobile data has a carrier address that changes and can sit in a feed or a blocked country; WireGuard answers nothing it cannot authenticate, so the exemption opens nothing to strangers. A banned sender stays banned, and a port forward of the same number to a LAN host is still filtered. OpenVPN and IPsec servers are not exempted.
- **Countries are checked before feeds.** Both drop; the order only decides which counter counts the packet, so per-country counts are real and the feed counter holds what no country matched.

##### 4.3.1.5 Threat feeds and custom feeds

| Feed | Source | IPv6 |
|---|---|---|
| FireHOL Level 1 | `raw.githubusercontent.com/firehol/blocklist-ipsets/.../firehol_level1.netset` | no |
| Feodo Tracker (botnet C2) | `feodotracker.abuse.ch/downloads/ipblocklist.txt` | no |
| Spamhaus DROP | `www.spamhaus.org/drop/drop.txt` and `dropv6.txt` | yes |
| DShield top attackers | `raw.githubusercontent.com/firehol/blocklist-ipsets/.../dshield.netset` | no |

All selected feeds and custom feeds merge into **one de-duplicated set** (`rw_threat` / `rw_threat6`, up to 524,288 entries each), so overlap costs nothing. **FireHOL Level 1 already contains Spamhaus DROP, DShield and Feodo**; ticking them as well adds little, except Spamhaus's IPv6 list.

**Every list is filtered before it is loaded.** Private, loopback, link-local, CGNAT (`100.64.0.0/10`), multicast and reserved ranges are removed from every feed and country list, IPv4 and IPv6. FireHOL Level 1 contains `10.0.0.0/8`, `192.168.0.0/16` and `127.0.0.0/8` on purpose (it is meant for a WAN interface); loaded unfiltered, it once took a whole network offline. A careless or hostile list cannot block your own network.

**Custom feeds.** Up to 8, each a **Name** (up to 24 characters: letters, digits, space, `.`, `_`, `-`), an **https** address of up to 200 characters with no quotes, spaces or `@`, and an optional IPv6 list address. The router pulls every IPv4 address or CIDR out of the file (any text format works) and loads them into the same set, so they appear in the same counters. Only add lists you trust: whatever they contain is dropped.

**A feed that needs an API key (v3.8.0).** Type `$APIkey` in the address where the key belongs (for example
`https://example.com/list?key=$APIkey`); a box for the key appears in that row. Type the key and save the page. The key is
kept on the router alone (`/jffs/rwarden/cfkeys`, root only): it is not in the feed list, not shown on the page again
(the row says a key is saved) and not in a settings export, so after restoring a backup on another router you type it
again. The router puts it into the address only when it fetches the feed. `$` is allowed in an address only as
`$APIkey`, after the host. Renaming the feed or changing its host clears the key; type it again.

**How a download behaves.** Every fetch is https only, including redirects, and capped at 32 MB. Built-in feeds get 2 retries of up to 40 s; custom feeds 1 retry of up to 15 s, so eight unreachable custom feeds cost about 4 minutes at most. The merged set is rebuilt from the feeds that arrived in that run; **a feed that fails while others succeed is missing from the set until its next good download**. If every feed fails, the previous set stays and the log says `feed update: no feed produced data (all fetches failed)`. A second update started while one runs is skipped (`feed update already in progress`).

##### 4.3.1.6 Countries

Country lists come from ipdeny (`www.ipdeny.com`) and refresh with the feeds. Each country has its own set (`rw_g_<cc>`, IPv6 `rw_g6_<cc>`, code in lower case; up to 262,144 entries each) and its own rule, which is what makes per-country counts possible.

Warden downloads ipdeny's aggregated list for each country; if that file arrives empty, it loads ipdeny's plain list for the same country instead (same coverage, more entries) and the log names the countries it did that for. A download that fails keeps the country's previous set. Each fetch gets 1 retry of up to 20 s, and the whole country loop has a **15-minute budget**: fetches past it are not attempted that run (`geo: update time budget (900 s) ran out`). North Korea publishes no IPv6 list; it is not fetched.

After each update the log names every selected country that is blocking nothing (`geo: selected but NO data loaded, NOT blocked: ...`), and a failed fetch says whether the country kept its previous list or has none. On the page, **Countries blocked** turns amber with *N country list(s) empty*. **Take that warning seriously: an empty set blocks nothing.**

**Review the list before you save.** Blocking a country you depend on (a VPN exit, a CDN edge, a game server region, a mail provider) breaks services in a way that looks like the remote service being down.

**The ipdeny address is in your whitelist.** ipdeny is hosted in France. With France blocked and **Also filter the router itself** on, the router would block its own country downloads, every fetch would time out and countries added after that would never load. So `51.15.12.186` is added to the Whitelist once (4.3.1.7). If you delete it, keep France unblocked or the router-traffic filter off.

##### 4.3.1.7 Whitelist and manual block list

Both boxes take one IPv4 or IPv6 address or CIDR per line. Both are checked on the source of incoming traffic and, with *Both directions*, on the destination of outgoing traffic.

- **Whitelist (never block)** beats the Manual block list, countries and feeds. Use it for anything you must never lose: a remote management address, a monitoring host, a VPN peer, a partner in an otherwise blocked country. You do not need a whitelist entry for your LAN; step 7 already exempts it.
- **Manual block list** beats the LAN exemption (4.3.1.4). Entries that are single addresses (bare, `/32` or `/128`) also have their existing connections cut when you apply; a range only stops new connections.

**Invalid entries are refused on save**, with a message naming them, and nothing is saved. Fix the named line and save again.

**Entries the router adds once.** So that no feed, country or manual block can cut the router off from its own lists and services, these addresses are added to the Whitelist the first time Warden starts on a release that carries them (the log line reads `whitelist: added ... once - remove it on the Warden page if not wanted`):

| Address | Why |
|---|---|
| `51.15.12.186` | `www.ipdeny.com`, the country lists (France) |
| `151.101.2.49`, `151.101.66.49`, `151.101.130.49`, `151.101.194.49` | the abuse.ch feed hosts (Feodo Tracker), served by Fastly from the United States list. These are shared CDN addresses: the entries exempt whatever else Fastly serves from them |
| `172.65.32.248`, `2606:4700:60:0:f53d:5624:85c7:3a2c` | Let's Encrypt, added only once the Let's Encrypt certificate is switched on (the next time DDNS starts) |
| `185.199.108.133` to `185.199.111.133`, `2606:50c0:8000::154` to `2606:50c0:8003::154` | `raw.githubusercontent.com` (ipverse, the first source of Policy Routing's ASN and country lists), added only once such a list is used by a rule (4.4.4a). These are shared GitHub addresses: the entries exempt whatever else GitHub serves from them, Warden's own two GitHub-hosted feeds included |
| `193.0.6.150`, `2001:67c:2e8:22::c100:696` | `stat.ripe.net` (RIPEstat, the Netherlands), the second source of ASN lists; added at the same moment |
| `45.33.65.164` | `api.hackertarget.com` (HackerTarget), the third source of ASN lists; added at the same moment |

Each address is added only if it is missing; nothing you entered is changed or reordered. **Delete any of them and it is never put back**: the one-time markers live in `/jffs/rwarden`, so they survive reboots and upgrades. Only erasing `/jffs` starts over. If you delete the Let's Encrypt entries while **Also filter the router itself** is on, the log warns once per boot that renewals can fail. GitHub (FireHOL, DShield) and Spamhaus are not added; whitelist them if you block the country they are served from with the router-traffic filter on. Let's Encrypt via DNS (4.3.4.3) adds nothing here: it lets its DNS provider's API and Let's Encrypt through only for the length of each request.

##### 4.3.1.8 Direction, and filtering the router itself

**Direction.** *Inbound only* drops listed sources: unsolicited arrivals at the router and at forwarded services. *Both directions* also drops LAN devices' traffic **to** listed destinations, which is what catches a device that is already compromised and calling home. (An older *Outbound only* setting produced the same rules as *Both* and was removed; a stored `out` is read as `both`.)

**Also filter the router itself** (off by default) runs the destination checks on connections the router starts (`RW_SELF`, on `OUTPUT`). It cannot lock you out: management traffic arrives from the LAN and its replies go to a LAN address, both exempt, so the web interface and SSH stay reachable and the switch stays revocable. Built-in exemptions: established connections, loopback, the LAN and the router's own WAN addresses, the upstream DNS servers the resolver uses, and NTP (UDP 123), because a dead clock breaks TLS everywhere.

It **can** stop the router reaching a list server, DDNS, a certificate authority or a VPN server if a blocked country or list covers it. Updates then fail and the previous data stays in use. The addresses in 4.3.1.7 are whitelisted for that reason; any other list host or service in a blocked country needs its own Whitelist entry. Wallguard names this case on its Lists table (*blocked by Warden (FR)*, 4.3.3.13).

Drops here **always** go to the log with the prefix `REAPER-WARDEN-SELF`, whatever **Log dropped packets** says, and the self-monitor reports them as `warden-self-drop`. That is the feature working. Malware with full control of the router can remove these rules, so treat this as a speed bump and a detection signal, not containment.

##### 4.3.1.9 Logging

With **Log dropped packets** on, each drop writes a kernel log line: `REAPER-WARDEN` for inbound, `REAPER-WARDEN-OUT` for outbound. `REAPER-WARDEN-SELF` is always on. In Firewall › Logging (4.1.12) they show as the `WARDEN`, `WARDEN-OUT` and `WARDEN-SELF` badges. Logging is useful while tuning and noisy if left on; the counters work without it.

##### 4.3.1.10 Reading the statistics

**Blocked packets** is every packet Warden dropped (inbound, outbound and the router's own, IPv4 and IPv6) since the date shown in the breakdown strip. The strip under **Top blocked countries** shows:

| Item | Meaning |
|---|---|
| *Countries:* / *Threat feeds:* / *Manual blocks:* | Drops by each rule group; they add up to the total |
| *Unclassified:* | Shown only for counts saved by an older firmware, before the groups existed |
| *Prefixes loaded:* | Country ranges loaded, all selected countries together |
| *Threat entries:* | Entries in the merged feed set against its limit (`n / 524,288`); entries past the limit are not loaded |
| *Counting since* / *Since the last firewall rebuild* | The window the counts cover (the second when **Save block statistics** is off) |

- It counts **packets, not connection attempts**: a scanner retries each SYN and a LAN device retries a blocked destination, so one attempt can add dozens.
- The log is a different view: one line per drop, only while logging is on, in a rotating buffer that drops lines under a burst. The counter is always the larger and the reliable figure.
- Counts are banked to `/jffs/rwarden/counters` every 15 minutes (only when something new was dropped) and on every apply, so they survive reboots, rebuilds and upgrades. **Turning Warden off resets them.**
- *Stats unavailable - retrying* on the *Live* pill means the status request timed out (a firewall restart was holding the counter lock); the page keeps polling.

##### 4.3.1.11 "I never see any outbound blocks"

**An empty outbound log is the normal case.** Inbound blocks are constant because the internet supplies a steady stream of unsolicited traffic. An outbound block needs a device on your network to reach for a listed address, which on a healthy network may not happen for weeks.

The self-monitor says which state applies, in a log line tagged `rwatch` beginning `Warden outbound:`, written whenever the state changes:

| What it says | What to do |
|---|---|
| *not filtering outbound - Direction is inbound only* | Set Direction to *Both directions* if you want outbound filtering. |
| *armed but NOT logging* | Outbound blocking works; switch on **Log dropped packets** while you investigate. |
| *armed and logging (prefix REAPER-WARDEN-OUT)* | It is working. The count for this statistics window is on the same line; 0 means nothing has matched. |
| *armed; whether it is logging could not be read this tick* | A busy moment; the next tick says. |
| *enabled for out/both but the RW_ODROP chain is ABSENT* | A fault: the chain should exist. Report it with the diagnostics report (2.10). |

To confirm it end to end, use **Catch a device calling home** below and connect from a LAN device to an address you know is on a feed you have enabled.

##### 4.3.1.12 Examples

**Stop the background scanning, change nothing else.** FireHOL Level 1, no countries, *Inbound only*, logging off. Nothing on the LAN is affected.

**Refuse countries you never deal with.** Tick them, keep *Inbound only*, and watch **Top blocked countries** for a week before considering *Both directions*. If a service breaks, check the country list first.

**Catch a device calling home.** *Both directions*, FireHOL Level 1 plus Feodo Tracker. A LAN device reaching a listed command-and-control address is dropped and, with logging on, logged as `REAPER-WARDEN-OUT`.

**Keep one address reachable through a country block.** Put it on the Whitelist.

**Block one LAN device outright.** Put its address on the Manual block list. Gatekeeper (4.2) does the same by MAC address, which survives a changed IP address.

**Reach your WireGuard server from anywhere with countries blocked.** Nothing to do: enabled WireGuard servers' ports are exempt (step 8).

##### 4.3.1.13 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| A website or service stopped working after enabling Warden | Its address is in a blocked country or on a feed (with *Both directions*) | Log dropped packets on, look for `REAPER-WARDEN-OUT` with the destination; whitelist it or untick the country |
| **Countries blocked** amber, *N country list(s) empty*; log `geo: selected but NO data loaded, NOT blocked` | The country's list never downloaded | **Update feeds now**; if it persists, read the `rwarden` lines (`geo v4 fetch FAILED for <cc>`). With the router-traffic filter on, check that `51.15.12.186` is still whitelisted |
| Log `geo: update time budget (900 s) ran out` | Too many countries, or the list host is slow | The rest load on the next run; select fewer countries |
| **Last feed update** stays *Never* / old; log `threat feed fetch FAILED` | The router cannot reach the feed host | Check the WAN; with the router-traffic filter on, look for `REAPER-WARDEN-SELF` lines naming the feed host and whitelist it |
| Save refused with a list of entries | They are not valid addresses or CIDRs (for example `192.168.1.*`) | Correct them; nothing was saved |
| Log `rwarden_allow: N invalid entries IGNORED` | A list written outside the page holds invalid entries | Open the page and save the list again |
| A remote VPN user cannot connect | OpenVPN and IPsec are not exempted; their address is in a blocked country or feed | Whitelist them, or use WireGuard |
| DDNS updates or the Let's Encrypt certificate stop | Router-traffic filter on, the service's address in a blocked country | Restore the whitelist entry (4.3.1.7) or switch the filter off |
| `REAPER-WARDEN-SELF` lines / `warden-self-drop` in the self-monitor | The router reached for a listed address | Read the destination: a known service (whitelist it) or something to investigate |
| Log `Warden chain REAPER_WARDEN is STILL missing after a re-apply` | The apply script is failing | Run `/tmp/rwarden/apply.sh` over SSH and read its output; send the diagnostics report |

##### 4.3.1.14 Limits

- Addresses only; see 4.3.1.1. A connection to a listed **name** on a clean address is Dreadwatch's job.
- A feed that fails while others succeed is missing until its next good download (4.3.1.5).
- A range, country or feed entry blocks new connections; connections established before the entry was loaded run until they close. Single addresses on the Manual block list are cut at once.
- Threat set: 524,288 entries per address family; each country set: 262,144.
- Router-originated traffic is filtered only with **Also filter the router itself**; testing from the router's own shell with it off shows no blocking, by design.
- The self-monitor checks every few minutes that neither the router's LAN address nor `127.0.0.1` is in a block set; if one is, it logs a critical line and re-applies. It is a backstop, not something you should see.

<a id="4310-dreadwatch"></a>
#### 4.3.2 Dreadwatch

##### 4.3.2.1 What it is, and when to use it

Dreadwatch blocks **host names on threat lists** at the router's resolver: malware-distribution sites, phishing, command-and-control and more. A lookup for a listed name, or any name under it, is answered **NXDOMAIN**, so the device never gets an address to connect to. It applies to every device that uses the router for DNS, on the main network and on every guest and VLAN network, and every blocked lookup is counted. **Off by default** (`rwarden_dns` `0`).

**Use it** on any network where devices use the router for DNS. It complements Warden: Warden blocks addresses, Dreadwatch blocks names, and a malicious site on a shared CDN address can only be blocked by name. It also complements Wallguard: Dreadwatch's answer is the same for every device, and no Wallguard profile, Bypass included, lifts it.

**When it does nothing.** Devices that do not ask the router: a device or browser with its own encrypted DNS provider, a device with a hard-coded DNS server, a device on a VPN, and devices behind a LAN resolver that does not forward to the router (4.3, *Living with the rest of the router*). The **Coverage** card says which gaps are open on your network.

Dreadwatch has its own switch and works with Warden on or off. It shares Warden's list updater and schedule, **Save block statistics** and **Reset interval** (4.3, *Shared pieces*).

##### 4.3.2.2 Setting it up

1. Switch on **Block threat domains** at the top of the tab.
2. In the **Feeds** table, keep **Reaper's Basics** ticked and tick any optional list you want.
3. Add anything that must never be blocked to **Never block these names**.
4. **Save & Apply.** A save that changes anything fetches the lists at once; afterwards they refresh with Warden's schedule (default 04:30 daily). **Update feeds now** fetches again at any time.
5. Press **Test now**: *Blocked: ... was answered NXDOMAIN* means the list is in force.

##### 4.3.2.3 The built-in lists

All are free and need no account or key. Each built-in row shows the address its list is downloaded from, as a link under the row's name (shortened; the full address on hover), so you can open the list in a new tab and read it before you tick it. The Basics row shows its three downloaded lists; the ThreatFox snapshot has no address because it ships inside the firmware, and the row says so.

| Row | Lists | Source | Default |
|---|---|---|---|
| **Reaper's Basics** (malware sites, phishing, command-and-control) | URLhaus (mirror) | `malware-filter.gitlab.io/malware-filter/urlhaus-filter-hosts.txt` | on |
| | Phishing | `malware-filter.gitlab.io/malware-filter/phishing-filter-hosts.txt` | on |
| | Command-and-control (C2IntelFeeds) | `raw.githubusercontent.com/drb-ra/C2IntelFeeds/master/feeds/domainC2s.csv` | on |
| | ThreatFox snapshot (abuse.ch, 21 October 2026) | bundled with the firmware | on |
| **Cryptojacking and mining (Prigent Crypto)** | browser-mining and mining-pool names; can catch cryptocurrency sites | `v.firebog.net/hosts/Prigent-Crypto.txt` | off |
| **Ransomware hosts (Blocklist Project)** | ransomware hosts | `blocklistproject.github.io/Lists/ransomware.txt` | off |
| **Phishing and fraud domains aimed at Poland (CERT Polska)** | about 125,000 names from Poland's national CERT | `hole.cert.pl/domains/v2/domains_hosts.txt` | off |
| **High-confidence threat domains (Threatview)** | threat domains, high-confidence feed | `threatview.io/Downloads/DOMAIN-High-Confidence-Feed.txt` | off |

**Reaper's Basics** is one switch for its four lists; the row shows their names, blocks and newest download added up, and *failed* if any one failed. The factory selection is `rwarden_dns_feeds` `urlhaus phish c2 threatfox`. A selection saved by an older build that had only some of the four shows as Basics on, and the next save turns on all four.

In C2IntelFeeds, entries marked as domain *fronting* name legitimate CDNs and services; they are never taken.

**abuse.ch.** abuse.ch closed its free URLhaus and ThreatFox downloads in October 2026; they now need a free abuse.ch account key. URLhaus comes from the mirror above. **ThreatFox is a snapshot of its last free list (21 October 2026, about 30,800 names), carried inside the firmware: it does not update and will age.** With an abuse.ch key, the **abuse.ch ThreatFox** and **abuse.ch URLhaus** templates under **Add a source** bring both back as live lists (4.3.2.4). For a much larger free threat list, tick **HaGeZi Threat Intelligence** in Wallguard (4.3.3.3).

**Removing a row.** Every built-in row, Basics included, has **Delete**: the list is no longer fetched and its names leave the table. *Removed built-in lists:* under the table lists them with **Restore**.

##### 4.3.2.4 Your own sources (lists and APIs)

**Add a source** opens a form; up to **8** sources. The form is Wallguard's, and the download goes through Wallguard's fetcher, so a source behaves the same on both tabs.

| Field | Use |
|---|---|
| **Template** | *Your own list (a web address)*, *abuse.ch ThreatFox - API, needs your Auth-Key*, *abuse.ch URLhaus - API, needs your Auth-Key*. A template fills every field except the key. |
| **Name** | Up to 40 characters, no quotes or `< > &`. |
| **Address (https://)** | Up to 400 characters, https only. |
| **Answer format** | *A list (hosts, domains, `\|\|name^` or dnsmasq lines)*, or *JSON*. |
| **JSON field that holds the names** | For JSON: letters, digits or `_`. A URL in that field is cut to its host; IP addresses are skipped. |
| **Request** | GET or POST (hidden under **Request · API key header ›** until needed). |
| **Request body (sent with POST)** | Up to 1,024 printable characters; a body starting with `{` or `[` is sent as JSON. |
| **API key header** | The header name the supplier wants (abuse.ch: `Auth-Key`). |
| **API key** | Your key, up to 200 characters, no spaces or quotes. |

A plain list accepts hosts files (any IPv4 address before the name), plain names, Adblock `||name^`, CSV (`name,description`) and dnsmasq lines (`address=/name/`, `server=/name/`, `local=/name/`).

**A key inside the address.** For a supplier that takes the key in the URL, type `$APIkey` where the key goes (for example `https://example.com/feed?api_token=$APIkey`) and leave the header empty; the router puts your saved key there at each download. `$APIkey` is accepted only after the host name.

**Where keys are kept.** In `/jffs/rwarden/dnskeys`, readable by root only. The page never shows a key again: the row says *API · key saved*, and leaving the key box empty on **Modify** keeps the saved key. A key reaches the download tool in a root-only file, never on a command line. A source that sends its key in a header never follows a redirect (the log says to give its final address). Both backup files carry the sources and keys (2.5).

Each source has its own row with a tick, figures and state; **Modify** edits it, **Delete** removes it with its download and key. A source that needs a key it does not have is not fetched; its row and the log say so. A source's own host is never blocked. Your sources fill the name limit after the built-in lists (4.3.2.6).

##### 4.3.2.5 Never block these names

One name per line; each entry also covers its subdomains. A line that is not a valid host name refuses the whole save.

Never blocked, with their subdomains:

- everything in **Never block these names**;
- names from your own settings: the LAN domain, your DDNS name, your NTP servers, your DNS-over-TLS upstream servers, and the hosts of your own sources;
- the local zones `local`, `arpa` and `lan`.

**Entries the router adds once.** The names the router needs are entries in the box, not built into the firmware: `abuse.ch`, `ipdeny.com`, `pool.ntp.org`, `asuscomm.com`, `asus.com`, `github.com`, `githubusercontent.com`, `spamhaus.org`, `malware-filter.gitlab.io`, `v.firebog.net`, `blocklistproject.github.io`, `hole.cert.pl` and `threatview.io`. They are added the first time Warden or Dreadwatch starts on a release that carries this, and the log names them. Remove any you do not trust; it is never put back. A built-in exemption would outlive a list host that is later compromised, or a lapsed domain someone else buys. If you remove a list host, Dreadwatch can block it when a list names it, and that list's next update can fail. Two more names are added the first time a Policy Routing ASN or country list is used by a rule: `ripe.net` and `hackertarget.com`, two of the sources those lists are downloaded from (4.4.4a). They take effect at the next list update.

**What an exemption can do.** It removes list entries equal to it or under it. It cannot carve a subdomain out of a listed parent: if `example.com` is listed, exempting `www.example.com` does nothing; exempt `example.com`. Blocking applies to the name a device asks for, not to the names an answer points on to, so a CDN name such as `p2.shared.global.fastly.net` never needs an entry.

##### 4.3.2.5a Devices that skip Dreadwatch

*From v3.8.4.* A card on the Dreadwatch tab lists up to 16 devices whose lookups are not checked against the threat lists. Use it for a device that must be unfiltered without sending it to another DNS server: the device keeps the router's resolver, its local names and Encrypted DNS.

- **Add a device**: pick it in the list (Name, else Hostname) or type its MAC address, press **Add device**, then **Save**. **Remove** and **Save** puts it back under Dreadwatch. Nothing changes before Save, and DNS is not restarted: the resolver reads the list again within two seconds.
- **What it lifts**: Dreadwatch only. Wallguard (the device's profile; **Bypass** lifts that), Warden and the Encrypted DNS block still apply. A name on both Dreadwatch's and Wallguard's lists stays blocked by Wallguard unless the device's profile is Bypass.
- **Other devices are not affected**: an exempt device's lookup of a listed name is never answered from the resolver's cache and never stored there, so the next device asking for the same name is still blocked.
- **What is recorded**: the column **Listed lookups let through** counts them per device. The names are not recorded anywhere. **Reset counters** (the **Test now** card) restarts the counts.
- **How a device is recognised**: by its MAC address, over plain DNS, Encrypted DNS and IPv6 alike. A phone on a *Rotating* private Wi-Fi address changes its MAC address and drops off the list: set Private Wi-Fi Address to *Fixed* or *Off* for this network on the phone. A device behind another router or a LAN resolver cannot be recognised.
- **Wallguard's Bypass does not put a device here**, and no existing Bypass device is exempted by an update.
- **Storage**: `/jffs/rwarden/dnsexempt` (MAC addresses), carried by the settings file and the full backup. The resolver reads `/tmp/reaper_nx/dns.exempt`.

##### 4.3.2.6 How a list becomes the table

At each update:

1. Each selected list is downloaded (https, certificate checked, at most 16 MB for a built-in list, 32 MB for your own source) and parsed into host names: lower case, one per line, dropped if it has no dot or a last label that does not start with a letter. A list that fails, or downloads but holds no usable names, **keeps its previous download** (that previous copy is held in RAM, so it covers failures after the first good download since the last boot). The log gives the cause: the HTTP status, or *no answer* with curl's exit code.
2. The names are merged in **priority order**: Reaper's Basics (URLhaus, Phishing, Command-and-control, ThreatFox), then the optional lists in table order, then your sources in slot order. Each name is kept once; a name whose parent is already on the list is dropped (the parent covers it); names longer than 253 characters are dropped.
3. The never-block names are removed.
4. The list fills up to **1,000,000 names** in that order, so a list that grows suddenly can only push out the lists below it, never Basics. If the router's free memory at that moment would not hold the list in a quarter of it, the limit is lowered for that run. The log (`the 1000000-name limit ... left out N names from the lowest-priority lists`) and a line under the table name the lists that were partly left out.
5. The list is compiled into one table, `/tmp/reaper_nx/threat.db` (about 12 bytes a name), which every dnsmasq instance (main network and each guest or VLAN network) maps from the same file, so it is held once in RAM. The compiler checks every new table before it replaces the old one; a table that fails the check is never installed (`the new list failed wallguardc's own check - the list in use stays`).
6. **A changed list restarts the resolver once**, at the end of the update, so its cache forgets answers given before the change. An unchanged list restarts nothing.

The log summarises each run: `threat domains: N loaded (urlhaus ..., phish ...); X never-block, Y covered by a listed parent, list changed - dnsmasq restarts`.

**At boot** the table is rebuilt from the compressed copy `/jffs/rwarden/dns.k.gz` in the background (`threat domains: rebuilding the table from the /jffs copy in the background`). The resolver starts at once and picks the table up within two seconds of it appearing; the list is in force about 15 to 20 seconds after DNS starts, and until then listed names resolve.

A listed name and its subdomains are answered NXDOMAIN. If the router's own configuration has an entry for an equal or longer name (a local name, an `address=` line), that entry's answer wins.

##### 4.3.2.7 Reading the page

| Part | What it shows |
|---|---|
| Pill | *Enforcing* when the switch is on, the resolver uses the list and it holds names; otherwise *Disabled*. |
| **Blocked lookups** | Blocked lookups since the counters were last reset (*Counted since* under **Test now**). |
| **Names on the list** | Names in the table now. |
| **Devices that tried** | The number of devices that looked up a listed name. The counters keep the 100 busiest, so the tile reads *100+* beyond that; the device table below lists the top 20. |
| **List updated** | The last successful list build; it survives a reboot (the boot rebuild from the saved copy restores it). |
| **Devices that skip Dreadwatch** | The devices not checked against the lists, with the listed lookups let through for each (4.3.2.5a). |
| **Not recorded** | Shown only when non-zero: blocked lookups the resolver blocked but did not record (see below). |
| **Feeds** table | Per row: tick; **Names** (its names on the list after the exemptions; a name on two lists counts for both, so the rows can add up to more than the total); **Blocked** (lookups it blocked); **Last good download**; **State**: *ok*, *failed, previous download kept*, *off*, or, for a source of yours, *This source sends an API key - type the key.* |
| Status line | *N names blocked at the resolver, updated ...*, or *Not loaded yet ...*, or *List built (N names) but dnsmasq is not using it yet ...*. Below it, where the blocked-lookup history is kept (Long-Term Storage). |
| **Most-blocked names** | The top 20 list entries by blocks, with their feed and when last seen. |
| **Devices that looked up blocked names** | The top 20 devices, by the name on the Devices page where known. |
| **Recent blocked lookups** | The newest 100 of up to 500 kept in RAM (cleared at reboot). |
| **Test now** | Asks the router's resolver for one name on the list; the answer must be NXDOMAIN. The test lookup is counted, as *this router (self-test)*. |
| **Reset counters** | Clears the counters and the recent list (log: `Dreadwatch counters reset by the operator`). |
| **Coverage** | Whether DNS Director sends every device's lookups to the router; whether Firefox's DoH canary answers NXDOMAIN; the gaps that are never covered (other DoH clients, VPNs); the remedy for encrypted DNS (LAN › DNS › DNS-over-TLS); whether Encrypted DNS for devices is on; whether encrypted DNS around the router is blocked; Wallguard, with a link. |

**What is counted.** The resolver records each NXDOMAIN it gives from the list: the time, the device that asked, the **list entry** that matched (a lookup of `a.b.bad.example` is recorded as `bad.example`) and its feed. Only blocked lookups are recorded, and nothing goes to the system log per lookup. A device using Encrypted DNS is recorded by its own address. The records are collected every 15 minutes and on each page refresh (every 30 seconds while the page is open). The resolver keeps at most 50 records a second and 256 KB between collections; the rest is counted as **Not recorded**. The counters keep the 100 busiest names and the 100 busiest devices, in `/jffs/rwarden/dns.counters` (in RAM if **Save block statistics** is off), and follow Warden's **Reset interval**. **Turning Dreadwatch off clears them**; turning Warden off does not.

*Counting is not active yet* means the resolver is running a list built before counting existed; blocking works, and counting starts with the next list update (**Update feeds now**).

##### 4.3.2.8 Encrypt at the router, not on each device

A device set to a **named** encrypted DNS provider (Secure DNS in Chrome, Edge or Firefox set to a provider, Android Private DNS set to a provider host name, iCloud Private Relay) sends its lookups straight to that provider, past Dreadwatch. Keep the encryption but move it to the router:

- for the hop from the router to the internet, switch on **Encrypt upstream DNS** under **LAN › DNS › DNS-over-TLS** and leave devices on their automatic DNS setting;
- for the hop from the device to the router, switch on **Encrypted DNS for devices** (4.3.4).

The *automatic* settings are fine as they are: Chrome and Edge upgrade to encrypted DNS only when the system resolver is a known public provider (the router is not), and Android's *Automatic* Private DNS falls back to the router. To stop devices that are set to a named provider, use **Block encrypted DNS that goes around the router** (4.3.4.6).

##### 4.3.2.9 Examples

**Threat blocking for the whole house.** Switch on, keep Basics, save, **Test now**. Set DNS Director's global mode to *Router* so devices with their own DNS server are covered too, and set each guest network's row to *Router* as well: a network's row starts at *No redirection*, which keeps that network out of the global mode (4.22.2).

**Add ThreatFox live with your abuse.ch key.** **Add a source**, Template *abuse.ch ThreatFox - API, needs your Auth-Key*, paste the key, OK, **Save & Apply**. The row reads *API · key saved* and fills after the fetch. Untick or delete the bundled snapshot only if you want; both can run.

**A list blocks a site you need.** Find the entry in **Most-blocked names** or **Recent blocked lookups**, add it (or its parent) to **Never block these names**, save.

##### 4.3.2.10 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| **Test now** says *Not blocked* | The list is not in the resolver yet | **Update feeds now**; check the status line |
| **Test now**: *No list is loaded yet* | No list has downloaded | **Update feeds now**; read the `rwarden: threat domains:` log lines |
| *Blocked* on Test now, but nothing counted from devices | Devices resolve elsewhere | Read **Coverage**; DNS Director *Router*; 4.3.2.8 |
| A row reads *failed, previous download kept*; log `threat domains: <id> fetch FAILED (no answer, curl exit ...)` | The list host cannot be reached | Check the WAN. CERT Polska (Poland) and Threatview (France) each sit on one server: with Warden blocking that country and **Also filter the router itself** on, whitelist the host's address in Warden |
| Log `fetch FAILED (HTTP 401/403/410: the list host refuses it)` | The host refuses the download, or wants a key | For your source, check the key (**Modify**) |
| Row says *This source sends an API key - type the key.* | No key saved for a source that sends one | **Modify**, type the key |
| Log `the server redirects, and a source that sends its API key in a header never follows a redirect` | The address redirects | Use the final address |
| Line under the table: *The name limit was reached ...* | The selected lists exceed 1,000,000 names (or the memory-lowered limit) | Untick a large optional list |
| Log `nothing fetched and no earlier list - threat domains block nothing until a list downloads` | First update failed | Fix the WAN, **Update feeds now** |
| Log `reaper-nx-db: ... is not there - the threat list blocks nothing until rc rebuilds it` | The table went missing while the resolver ran | **Update feeds now** |

##### 4.3.2.11 Limits

- Only lookups that reach the router's resolver (4.3.2.1).
- The device counted is the address that asked the router. A LAN resolver forwarding to the router counts as one device; a lookup over IPv6 counts under the device's IPv6 address.
- Names, not addresses: a connection to a bare IP address is Warden's job.
- The lists are time-boxed upstream (entries expire), so the list shrinks as well as grows. The bundled ThreatFox snapshot does not update.
- After a reboot, a list that fails its first download of the session has no previous copy in RAM and leaves the table at that update; the next good download brings it back.
- A firmware downgrade to v3.4.7 does not inherit the list; that release builds its own at its first update.
- A device that skips Dreadwatch (4.3.2.5a) is recognised by its MAC address only; an address that changes is judged like any other device.

<a id="4311-wallguard"></a>
#### 4.3.3 Wallguard

##### 4.3.3.1 What it is, and when to use it

Wallguard is the router's own **ad and tracker blocker**: what Pi-hole or AdGuard Home do, inside the router's resolver, for every device on every network, with nothing to install on the devices. Block lists name advertising, tracking and telemetry hosts; a lookup for one is answered `0.0.0.0` (or NXDOMAIN, your choice), so the ad or tracker never loads. Profiles give devices or guest networks different lists, blocked services (TikTok, Roblox and others), schedules and safe search. **DNS rewrites** answer names of your choice with your own addresses, on and off alike (4.3.3.14). **Off by default** (`wallguard_enable` `0`).

**Use it** to remove ads and tracking for the whole house; to give a child's devices stricter filtering, bedtime service blocks and enforced safe search; to exempt a work laptop. **Do not expect it** to remove ads served from the same host name as the content (YouTube video ads, some streaming apps) or page elements; it blocks by name only. It sees only lookups that reach the router (4.3, *Living with the rest of the router*); the page shows a banner when a firewall rule sends devices' DNS elsewhere.

**The page (v3.8.4).** The master switch **Block ads and trackers** and the status pill sit in the header, with a **?**
button that opens *How to use* and *How it works* (the **Reset counters** button is there). Six tabs sit below; **Save &
Apply** is at the right end of the tab row, and a tab that holds an unsaved change shows an amber dot. The page reopens on
the tab you used last (kept in your browser).

| Tab | What is on it |
|---|---|
| **Overview** | The warning banners, the five counter tiles, **Fix a device** (Unbreak), **Pause** and **Why?** (4.3.3.7) |
| **Lists** | The block lists and your own sources (4.3.3.3), **Update lists now**, where the lists are kept, the build warning, **Blocked answer** (4.3.3.8). The tab label shows *N problems* when the table in use lacks lists |
| **Rules** | **My rules** and **Advanced rules** (4.3.3.4), **DNS rewrites** (4.3.3.14), **Services and safe search** (4.3.3.6) |
| **Allowed** | **Allowed for 24 hours**, **Never block** and **Always block** as tables: remove, extend or keep a 24-hour allow, remove a name or move it to the other list, each at once (4.3.3.4) |
| **Devices** | **Devices and networks**: every device and guest network, its profile, its blocked lookups in the last 15 minutes, **Fix** and **Pause**; the **Profiles** grid (4.3.3.5) |
| **Activity** | **Live view**, **Most-blocked names**, **Devices with the most blocked lookups** (4.3.3.11) |

##### 4.3.3.2 Setting it up

1. Switch on **Block ads and trackers** and press **Save & Apply**. One balanced list, **HaGeZi Normal**, is subscribed the first time. The lists download in the background; the pill reads *Waiting for lists* until the first table is built, then *Blocking*.
2. Choose lists on the **Lists** tab (4.3.3.3) and press **Save & Apply**. A list with no downloaded copy yet (newly ticked, or ticked again after it was removed) is downloaded then, alone and in the background (the lists already downloaded are not fetched again), and the table is rebuilt; otherwise a save only rebuilds the table from the lists already downloaded. The daily update at 05:15 fetches every list again; a row's **Update** fetches that list alone.
3. If a site or app breaks, open **Overview › Fix a device**, pick the device and allow the name (4.3.3.7).
4. On the **Devices** tab, give devices or guest networks a profile of their own (4.3.3.5).
5. On the **Rules** tab, under **Services and safe search**, pick a profile to block services, set a schedule and switch on safe search (4.3.3.6).

##### 4.3.3.3 Lists

| List | Character (page wording) | Downloaded from |
|---|---|---|
| HaGeZi Light | light - very few false blocks | `raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/light.txt` |
| HaGeZi Normal | balanced - recommended (subscribed at first switch-on) | `.../adblock/multi.txt` |
| HaGeZi Pro | strict | `.../adblock/pro.txt` |
| HaGeZi Pro++ | very strict - some sites may break | `.../adblock/pro.plus.txt` |
| OISD Small | light - very few false blocks | `small.oisd.nl` |
| OISD Big | balanced - recommended | `big.oisd.nl` |
| StevenBlack Unified | balanced - recommended | `raw.githubusercontent.com/StevenBlack/hosts/master/hosts` |
| AdGuard DNS filter | balanced - recommended | `adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt` |
| HaGeZi Threat Intelligence (Medium) | malware and phishing domains (about 435,000 names; the full list is past the size limits) | `.../adblock/tif.medium.txt` |

Each built-in row shows the address its list is downloaded from, as a link under the list's name (shortened; the full address on hover), so you can open a list in a new tab and read it before you tick it. One balanced list is usually enough; lists overlap heavily, and a second list of the same kind adds little.

**The table's columns.** Tick (subscribed); **Names** (names this list adds that no list above it already has; a source made only of exception lines reads *N allowed*); **Blocked** (blocked lookups this list matched; a lookup on two lists counts for both); **Last good download**; **State**: *ok*, *failed, previous copy kept*, *not downloaded yet*, or *blocked by Warden (FR / ban list / threat feed)* when Warden's router-traffic filter drops the list's server (hover for the address). Under the table: *N names in the table, built ...*, and *The table is full (1,000,000 names)* when it is.

**Delete** removes a built-in list from the table; *Removed built-in lists:* brings it back with **Restore**. **Update lists now** downloads every subscribed list now; **Update** on a row downloads that list alone, which suits list servers that dislike repeated full downloads.

**Your own sources.** **Add a source**: up to 8, with the same form, formats, API options, `$APIkey` rule and key handling as Dreadwatch (4.3.2.4), without the Template row. Keys are kept in `/jffs/wallguard/keys` (root only) and are never shown again. Wallguard's list compiler also accepts `*.name` (name and subdomains), `|name^` (that name only), `||name^$dnsrewrite=` to a sinkhole (`ad-block.dns.adguard.com`, `0.0.0.0`, `::`, `NXDOMAIN`, `REFUSED` — AdGuard DNS's *Popup Hosts* list is written that way; a rewrite to a real address is not a block and is left out), and `@@||name^` / `@@|name^` exception lines. **An exception line allows**: in any list, or in a source made only of such lines (an allowlist by address), it lets that name and its subdomains through for every device and every profile, like **Never block**. Dreadwatch ignores `@@` lines; its only exemption is its own Never block list. Hosts-file and plain-name lines block exactly that name; `||name^`, `*.name` and dnsmasq lines block the name and its subdomains. Regular-expression and cosmetic (`##`) lines are skipped and counted.

##### 4.3.3.4 My rules, and the names never blocked

**Always block** and **Never block**: one name per line; a name covers its subdomains. **Never block beats everything**, every list and Always block included, at any level: never-blocking `example.com` allows `ads.example.com` even if a list names it. A name allowed from Unbreak for 24 hours is listed under the boxes as *Allowed for 24 hours* with its expiry; within 15 minutes of that time it leaves the block table by itself (the router checks every 15 minutes and rebuilds the table when an allow has run out). A rule change takes effect within seconds of **Save & Apply** (the table is rebuilt from the lists on disk, no download).

**The Allowed tab.** The same three lists as tables, for changing one name at a time without editing the boxes:

| Table | Buttons |
|---|---|
| **Allowed for 24 hours** (name, time left) | **Remove**; **+24 h** (24 hours more, at most 7 days from now - for longer, keep it); **Make permanent** (moves the name to Never block). Tick names, or the box in the header for every row shown, then **Remove selected** or **+24 h**; **Remove all** asks first |
| **Never block** | **Remove**; **Move to Always block** |
| **Always block** | **Remove**; **Move to Never block** |

A **Filter names** box narrows all three tables. Every button acts at once: the table is rebuilt from the lists already
on the router within seconds, no download and no **Save & Apply** (one log line per name in the System Log,
`reaper-audit: wallguard allow 24h removed <name>` and so on). The boxes on the Rules tab still edit Never block and
Always block in bulk; while one of them holds changes you have not saved, the Allowed tab refuses to change that list
(save or discard first), so a later Save cannot undo the change.

The test loop this is for: a site breaks -> **Fix a device**, **Allow 24 h** on a few names -> still broken -> allow
more -> once it works, **Remove** the names one at a time on the Allowed tab until it breaks again; **Make permanent**
the one that matters and remove the rest.

**Entries the router adds once.** The names the router depends on are entries in your **Never block** box, added the first time Wallguard starts on a release that carries this, so you can remove any of them: `asus.com`, `asusrouter.com`, `asuscomm.com`, `abuse.ch`, `spamhaus.org`, `www.ipdeny.com`, `iplists.firehol.org`, the safe-search hosts `forcesafesearch.google.com`, `strict.bing.com`, `safe.duckduckgo.com`, `restrict.youtube.com` and `restrictmoderate.youtube.com` (blocking one breaks safe search for profiles that use it), `github.com`, `raw.githubusercontent.com`, `objects.githubusercontent.com`, `pool.ntp.org`, `time.google.com`, `time.cloudflare.com`, and the hosts of the built-in lists (`small.oisd.nl`, `big.oisd.nl`, `adguardteam.github.io`). A removed entry is never put back.

Never blocked automatically: your DDNS name, NTP servers and LAN domain, the server names of the router's OpenVPN and WireGuard clients, your DNS-over-TLS upstream servers, and the hosts of your own sources.

To answer a name with an address of your own rather than block or allow it, use **DNS rewrites** (4.3.3.14).

**Advanced rules (AdGuard Home syntax).** The **Advanced rules** card on the Rules tab takes an AdGuard Home rule list
pasted as it is, up to 40,000 characters. Use it when you already keep rules for AdGuard Home, or need a rule for some
devices only.

| Rule | Meaning |
|---|---|
| `\|\|name^` | block the name and its subdomains |
| `\|name\|` | block that name only |
| `@@\|\|name^` | allow (an exception) |
| `$important` | the rule wins over exceptions that lack it |
| `$client=` | only for these devices: an address, a MAC or a device's name (its Devices-page name or DHCP reservation name); `~` before a client means everyone else |
| `$ctag=` | only for the devices of this Wallguard profile |
| `$dnstype=` | only for these record types (`AAAA`, `HTTPS` ...) |
| `$dnsrewrite=NOERROR` / `NXDOMAIN` / `REFUSED` | answer with that code instead of the blocked answer |
| `*` wildcards, `/regex/` | pattern rules |

A rule with `$client=` or `$ctag=` applies to those devices only; everyone else is unaffected. A block is never put on a
name the router itself needs (the entries in 4.3.3.4 above). After **Save & Apply** the card shows *N rules in use, N left
out, N notes* and lists every line it could not use, with the reason. Invisible characters pasted with a list (zero-width
spaces, byte-order marks, direction marks) are removed before saving and counted in a note. The rules are kept in
`/jffs/wallguard/adv` and compiled beside the block table at every build (log `Advanced rules: N in use, N left out`); a
list that does not compile leaves the previous rules in use (log `the Advanced rules could not be compiled`). A long list
belongs in a custom list source (4.3.3.3) instead: the box refuses more than 40,000 characters.

Example: block a game for one tablet only, and let a work laptop past a list entry:

```
||roblox.com^$client=00:00:5e:00:53:21
@@||tracking.example.com^$client=Work-Laptop
```

##### 4.3.3.5 Profiles, devices and networks

A **profile** is a set of lists. The **Profiles** grid (Devices tab) has one row per profile and one column per subscribed list plus **My rules**; a tick means that profile blocks with that list.

- **Default** applies to every device without a profile of its own. Until you change its row it uses every subscribed list and My rules.
- **Bypass** blocks nothing (no lists, no services, no safe search). Use it for equipment that must not be filtered. Dreadwatch still applies to a Bypass device; to lift that too, add the device under **Devices that skip Dreadwatch** (4.3.2.5a). The Devices tab says so under the profiles.
- **Add profile** (name box under the grid) creates one with **My rules** only ticked: tick the lists it should use.
- **Edit** on a row opens that profile in **Services and safe search** on the Rules tab (4.3.3.6). **Remove** deletes a profile and its assignments.

**Devices and networks** (the table above the grid) has one row per device and per guest or VLAN network:

| Column | Shows |
|---|---|
| **Device / Network** | the device's label (4.8.1) or the network's name |
| **Profile** | a menu: the profile it uses. *No profile of its own* means Default (or, for a device, its network's profile) |
| **Blocked, 15 min** | lookups blocked for it in the last 15 minutes |
| **State** | *paused until ...* while a pause holds it |
| (actions) | devices only: **Fix** opens Overview › Fix a device on this device; **Pause 10 min** / **Resume** |

To assign, pick a profile in the row's menu and press **Save & Apply**; **Fix** and **Pause** act at once. A device rule
beats a network rule, which beats Default. The main network cannot be assigned as a whole; its devices use Default
unless assigned.

How the device is recognised: by MAC address, looked up from the address that asked; a device whose MAC the router cannot find gets its network's profile or Default. A **network** rule matches the network's IPv4 subnet, so a device on that network asking over IPv6 gets Default unless it has a device rule. Devices using Encrypted DNS are recognised by their real address. The router applies up to 22 profiles of your own.

Changes to profiles and assignments take effect within seconds of **Save & Apply**; no list is downloaded.

##### 4.3.3.6 Blocked services, schedules and safe search

The editor is the **Services and safe search** card on the Rules tab: pick the profile in its menu (or press **Edit** on
the profile's row in the Profiles grid, which opens it there). Default and your own profiles can be edited; Bypass
cannot.

- **Blocked services**: tick services by name, in seven groups: Social media, Video & streaming, Games, Messaging, Shopping, Dating, AI chat (45 services; their domains are maintained with the firmware in `/usr/share/wallguard/services`). The profile then blocks every domain of those services with their subdomains. A service a list does not cover fully can be topped up with **Always block**. Up to **13 profiles** can block services (each gets a list slot of its own); the editor says when the limit is reached. Bypass never blocks anything.
- **Schedule for the blocked services**: *Always blocked*, or *Blocked only at these times*: up to 8 time ranges, each with its days, **from** and **to**. A range that ends before it starts runs past midnight (21:00 to 07:00 on school nights is one range, counted from the day it starts); "allowed only 16:00-18:00" is the range 18:00 to 16:00; a range whose start equals its end is the whole day. The schedule switches **the blocked services only**; the profile's lists and safe search stay on. The router follows its own clock and time zone, and **until the clock is set after a boot, the services stay blocked**. To take a device off the internet entirely at bedtime, use Parental Controls › Time Scheduling (the editor links to it).
- **Safe search**: *Google, Bing and DuckDuckGo SafeSearch* (On/Off) and *YouTube Restricted Mode* (Off / Moderate / Strict). For that profile's devices, the router answers those sites' names (Google's country domains included, from Google's own list) with the addresses the providers run for enforced safe search (`forcesafesearch.google.com`, `strict.bing.com`, `safe.duckduckgo.com`, `restrictmoderate.youtube.com` / `restrict.youtube.com`), and answers their HTTPS/SVCB records empty so a browser cannot learn another way in. The setting cannot be switched off in the browser. The addresses are looked up through the router at each list update (and at once when a profile first asks for safe search); a failed lookup keeps the previous ones. **Until the first lookup succeeds, searches are not restricted**, and the editor says so. After a reboot the addresses are gone (they are kept in memory) and the first lookup runs before the internet is up: from v3.8.1 the router logs which engines are not restricted yet (`safe search: no enforcement address could be looked up for …`), looks them up again as soon as the internet comes up, then after 10 minutes, doubling up to 6 hours while a lookup still fails, and logs when every engine has its address. Before v3.8.1 they came back only with the daily full list update, and the **Update** button of a single list did not fetch them. A profile with YouTube among its blocked services keeps YouTube blocked: a block wins.

A **pause** never lifts a profile's blocked services or safe search. **Unbreak** shows a name that only a profile's blocked services refused as *Blocked service (profile)* with no Allow button (an allow would apply to everyone); untick the service in the profile instead. **Why?** names the profile whose services block a name.

##### 4.3.3.7 Pause, Unbreak and Why?

All three are on the **Overview** tab.

- **Pause**: pick *Everyone* or a device, then *5 minutes*, *10 minutes* (the default), *1 hour* or *Until 06:00* (by your browser's clock), and **Pause**; **Resume** ends it early. **Pause 10 min** on a device's row of the Devices tab does the same for that device. A pause lifts the lists and My rules, not blocked services, safe search or Dreadwatch. Pauses are held in RAM: a reboot ends them, and they end by themselves. The list under the buttons names each pause and its end time; while everyone is paused the pill reads *Paused* and a banner gives the end time.
- **Fix a device (Unbreak)**: pick the device that has a problem. The menu lists first the devices that had lookups blocked in the last 15 minutes, with the count. The table lists the names Wallguard refused that device in the last 15 minutes, with how often and when last, and **Allow 24 h** and **Always allow**. *Always allow* adds the entry to **Never block**; *Allow 24 h* adds it to the 24-hour list. Several names in a row usually belong to one service; allow them one at a time, newest first, and retry the app after each. The **Allowed** tab lists every 24-hour allow with its time left, to remove, extend or keep it (4.3.3.4).
  - **What a row names.** For an ordinary block, the **list entry** that matched (`doubleclick.net`, not the full name asked), so an allow covers its subdomains. For a block caught in a CNAME chain (4.3.3.8) the row reads *asked name (blocked via listed name)*, for example `saa.example.com (blocked via metrics.tracker.example)`: the device asked for the first name, and the list holds the second. **Allow** on such a row allows the **asked** name, which lifts the block for it (the note under the button says so) without allowing the tracker for every other site.
  - **How the device is found.** Every blocked record carries the MAC of the device that asked, so a device is found by its MAC even after its address changed; an older record without a MAC is matched by the addresses the device holds now. The router keeps the blocked records of the last hour (at most 20,000, in RAM), so a busy network no longer pushes one device's 15 minutes out of view.
  - **After Allow** the row reads *Allowed - takes effect for new lookups*, and a name you have allowed (Never block, or a 24-hour allow still running) is left out of the table from then on. A device keeps its cached answer until it asks again: restart the app, or wait a minute.
- **Why?**: type a name and **Check**. It says *Blocked by:* the lists or rules that hold it (or *Allowed by a Never block entry or a list exception*, or *Not on any list*), then, for each profile, whether it is blocked for that profile, and *The router answers:* what the router answers right now (an address, `nxdomain` or `none`).

**Finding what broke a streaming app.** Open **Fix a device**, pick the TV or streaming box, and start the app. Rows
that appear while it fails are the candidates; a *blocked via* row is a common cause for streaming services, whose own
names are often aliases for a measurement host on a list. Allow 24 h on the newest row, retry, and make it permanent
with Always allow once the app works. If nothing appears, the block is not Wallguard's: check **Dreadwatch** (4.3.2) and
**Warden** (4.3.1).

##### 4.3.3.8 What it checks, and how it answers

- **The name asked and every parent name**, for entries that cover subdomains (4.3.3.3).
- **Before the cache**, so a cached answer is covered and a pause or an allow shows at once.
- **Hidden trackers (CNAME cloaking)**: a site's own name that is an alias for a tracker's name is caught by checking every name in the reply's CNAME chain, for the device that asked. Such answers are never cached. The **Hidden trackers caught** tile counts them. Since v3.8.0 such a block is recorded under the name the device **asked** for, with the listed chain name beside it (*asked name (blocked via listed name)* in Fix a device and Live view), and an allow for the asked name (Never block, a 24-hour allow, or an `@@` exception) lets that name's answer through even though its chain leads to a listed name. The listed name stays blocked when asked for directly.
- **The router's own answers win**: a name the router answers itself (local names, a device's DHCP name, a DNS rewrite (4.3.3.14), an `address=` line, the DoH provider names and browser canaries answered by the Encrypted DNS block, or a Dreadwatch threat name) gets that answer. A threat name on both is answered and counted by Dreadwatch.
- **The answer**: **Blocked answer** below the Profiles card chooses *0.0.0.0 (fastest, recommended)* (`wallguard_mode` `null`, the default: `0.0.0.0` for IPv4, `::` for IPv6, an empty answer for other record types) or *NXDOMAIN* (`nx`). Blocked answers carry a 10-second lifetime and the Extended DNS Error code *Blocked*. Changing the mode applies with **Save & Apply**.

##### 4.3.3.9 How it runs

- **One table for every network.** The lists compile (`wallguardc`) into one table, `/tmp/wallguard/db`, which every resolver on the router maps and shares: one million names take about 12 MB once, not once per network. The table holds up to **1,000,000 names**; when full, My rules and the earlier lists win and names only later lists carry are left out (the page and each list's figures say so).
- **No DNS interruption.** A new table is swapped in and each resolver picks it up within two seconds, without a restart: DNS and DHCP keep running and the cache is kept. Only switching Wallguard on or off restarts the resolvers (log: `Wallguard on - restarting dnsmasq`). A missing or damaged table makes Wallguard pass everything; it never fails closed.
- **Downloads.** Daily at 05:15 and by **Update lists now**: https with the certificate checked, at most 32 MB per list (built-in lists: 2 retries, up to 90 s; your sources: 1 retry, up to 25 s). A failed download keeps the previous copy. The lists held in RAM together stay under 96 MB, and nothing is downloaded while less than 160 MB of memory is available; both cases are logged and shown as the list's state. One update runs at a time. A row's **Update** and a save that adds lists fetch only those lists. A list that could not be downloaded is tried again on its own after 10 minutes, then at double the wait each time up to 6 hours (log `list(s) ... still owed - tried again in N min`); a successful full update clears the retry.
- **At boot**, nothing is downloaded until the internet is up and the clock has been set (log `the internet is not up yet - the lists are fetched when it is`); until then the table holds My rules only, and the lists kept on a USB volume are used as soon as the store is attached, with no download (4.3.3.10). The download follows within seconds of the clock being set (the first NTP sync), and the self-monitor keeps trying every 5 minutes while any list is still owed, fetching only the lists that are missing (`Wallguard has no block lists yet - fetching them` when there is no table at all).
- **Where things live**: 4.3, *What is kept where*.

##### 4.3.3.10 Lists on a USB volume

Downloaded lists live in RAM and come down again after every restart. Tick **Wallguard block lists** on System Log › Long-Term Storage (4.11) with the location set to USB storage, and each list moves to `<volume>/.reaper/wallguard/lists` when it downloads. After a restart the table is built from those copies once the router's USB watchdog sees the volume mounted, with no internet needed.

- **The table always stays in RAM.** The volume is read only while a table is built, never during lookups, so a stick that is pulled, sleeps or fails cannot stop DNS.
- Each list's SHA-256 is recorded on `/jffs` when it downloads; a copy that no longer matches (changed through the file share) is not used (log: `list ... on the USB volume does not match its last download - not used`).
- **Lists downloaded while the volume was away are copied to it later (v3.8.0).** A list downloaded before the store was mounted (the boot-time update), or whose write to the volume failed, stays in RAM and is written to the volume on the next build once it is there, so the stored copy and its recorded sum agree again. Before v3.8.0 such a list was refused from the volume after the next restart.
- If the volume is missing when a table must be rebuilt (a rule change), the table in use stays and the log says so; downloads go to RAM until the volume is back.
- The Lists tab says where the lists are kept. This is USB only because internal flash has no room for lists of this size.

**When a rebuild is skipped (v3.8.0).** A rebuild that could not use every subscribed list is reported on the Lists tab
(and as a banner on Overview, with **Show lists**), and the Lists tab label shows *N problems*:

| Message | Meaning | What to do |
|---|---|---|
| *The last rebuild (time) was skipped: list has no usable copy (USB volume not mounted, or its copy changed)* | A rule change needed a rebuild while a stored list was unreadable; the previous table stays in use | Reattach or remount the volume, or **Update** that list |
| *The last rebuild (time) was skipped: another build was still running* | Several saves in a row | Save again after a minute |
| *The last rebuild (time) failed* | The compiler failed; the previous table stays in use | Read the `wallguard:` lines in the system log |
| *The block table in use was built from N of M subscribed lists - no usable copy yet of: ...* | Some lists are still owed (first download, or a failed one) | Wait for the retry, or **Update** the list |

##### 4.3.3.11 Counters, live view and privacy

| Tile / card | Meaning |
|---|---|
| **Lookups** | Every lookup the resolvers have handled since they last started |
| **Blocked** | Blocked lookups recorded since the counters were last reset |
| **Blocked share** | Blocked as a percentage of Lookups, since the resolvers last started |
| **Names on the lists** | Names in the current table |
| **Hidden trackers caught** | CNAME-cloaked trackers blocked since the last reset |
| **Most-blocked names** / **Devices with the most blocked lookups** | The top 50 of each; the counters keep the 200 busiest names and devices |
| **Live view** | Every lookup as it happens (newest 150 shown, refreshed every 3 s), with its verdict: *blocked*, *allowed by a rule*, *listed, not for this device*, *passed*, *safe search* |

The tiles are on **Overview**; Live view and the two top-50 tables on **Activity**. **Live view** can be narrowed to one
device with the menu beside its button.

**Privacy.** Only **blocked** lookups are recorded. A record holds the time, the device's address and MAC, and the **list entry** that matched (`doubleclick.net`), not the name as asked; a CNAME block (4.3.3.8) records the asked name and the listed name. The counters, the top lists, the Devices tab counts and Fix a device come from those records; the records of the last hour stay in RAM (at most 20,000) and are never written to flash. The resolver keeps at most 50 records a second and 512 KB between collections; the rest is counted, not recorded. The **Live view** is the only place names as asked, and lookups that were not blocked, appear: **Start live view** starts it (only while Wallguard is on), it is kept in RAM only, never saved, and switches itself off after an hour (*N min left*).

Records are collected every 15 minutes and on each page refresh; the counters are copied to `/jffs/wallguard/counters` at most hourly. **Reset counters** (in **How it works**) clears them. With **Wallguard blocked lookups** ticked on Long-Term Storage, every record is also appended to `<store>/wallguard/blocked.log` (rolled to `.1` past 16 MB on USB, 2 MB on JFFS); on USB, anyone with access to the volume's share can read it.

##### 4.3.3.12 Examples

**Ads off for the house.** Switch on, keep HaGeZi Normal, save. Check after a few minutes that the pill reads *Blocking*.

**A child's tablet.** Devices tab: **Add profile** "Kids"; tick HaGeZi Pro and My rules in its row; **Edit**: tick TikTok, Roblox and YouTube, schedule *Blocked only at these times*, school nights 21:00 to 07:00; Safe search On, YouTube Strict. Back on the Devices tab, set the tablet's **Profile** to Kids. **Save & Apply**.

**A work laptop that must not be filtered.** Assign it to **Bypass**. Dreadwatch still applies to it unless you also add it to **Devices that skip Dreadwatch** (4.3.2.5a).

**A guest network with lighter filtering.** Add a profile with HaGeZi Light only and assign the guest network to it.

**A shopping site's checkout breaks.** **Overview › Fix a device**, pick the device, **Allow 24 h** on the name that appeared when it broke; if that fixes it, **Always allow**.

**A streaming app shows an error on the TV.** Devices tab: the TV's **Blocked, 15 min** count rises while the app fails.
**Fix** on its row, then follow *Finding what broke a streaming app* (4.3.3.7). To test quickly whether Wallguard is the
cause at all, **Pause 10 min** on the same row and retry the app.

##### 4.3.3.13 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Pill stays *Waiting for lists* | The first download has not finished (nothing is fetched until the internet is up and the clock is set) | Check the WAN; **Update lists now**; read `wallguard:` log lines |
| Banner *Devices' DNS lookups are sent straight to ... by a firewall rule* | A Service Intercept rule (4.1.8) or DNS Director sends port 53 elsewhere | Remove the redirect, or accept that Wallguard cannot filter those devices |
| Wallguard on, nothing blocked | Devices resolve elsewhere, or only My rules are loaded | **Why?** with a listed name; check the banner and the Lists states; log `no block list could be downloaded - only My rules are blocked` |
| A newly ticked list stays *not downloaded yet* | Its download failed (the list's *State* and the log `wallguard` say why), or the internet was down | Check the connection, then that row's **Update** (it is retried on its own anyway, 10 minutes on) |
| A list reads *blocked by Warden (FR)* | Warden's router-traffic filter drops the list's server | Whitelist the address shown (hover) in Warden, change that block, or untick the list |
| A list reads *failed, previous copy kept* | The host cannot be reached, or refuses | Log `list <id>: download failed`; for your source check its address and key |
| Log `not fetched, less than 160 MB of memory available` | Low memory at update time | Fewer lists; free memory |
| Log `not taken, the lists kept in RAM would pass 96 MB` | Too many large lists in RAM | Fewer lists, or keep them on USB (4.3.3.10) |
| A site or app stopped working | A list blocks a name it needs | **Overview › Fix a device** (4.3.3.7) |
| Fix a device shows nothing for a device that is clearly blocked | The block is not Wallguard's (Dreadwatch, Warden, the Encrypted DNS block), or the device uses its own DNS (banner) | **Pause 10 min** on its row: if the app still fails, look at Dreadwatch and Warden |
| A row reads *name (blocked via other name)* | A CNAME block: the asked name is an alias of a listed name | **Allow** on that row allows the asked name only (4.3.3.8) |
| Lists tab shows *N problems*, or a rebuild warning | A rebuild was skipped or a list has no usable copy | The warning says which; see *When a rebuild is skipped* (4.3.3.10) |
| Safe search not applied | The device has another profile; the enforcement addresses are not looked up yet; or the browser uses its own encrypted DNS | **Why?**; **Update lists now**; Encrypted DNS block (4.3.4.6) |
| A blocked service still partly works | It also runs on shared cloud hosts or plain IP addresses, or the schedule is off now | Top up with **Always block**; check the schedule and the router's clock |
| A DNS rewrite does not answer | The table was not saved; the device resolves elsewhere (banner); the device asked with the LAN domain added; or an alias points at a name the router does not answer | **Why?** shows *The router answers:*; save; add the name with the LAN domain; give the alias's target a rewrite with an address |
| Log `DNS rewrites: N row(s) left out` | A row in `/jffs/wallguard/rewrite` (edited by hand, or restored) is unreadable, repeats an alias, or points an alias at another alias | Remove or correct that row on the page and save |
| Log `another block table build is still running - this one was skipped` | Two builds at once (several saves in a row) | Save again after a minute |
| Log (dnsmasq) `wallguard: the block table is damaged - passing everything until it is rebuilt` | A damaged table | **Update lists now** |
| Advanced rules: *N left out* | Those lines use syntax that cannot work in a DNS resolver (cosmetic rules, unsupported modifiers) | The card lists each line with the reason; remove or rewrite them |

##### 4.3.3.14 DNS rewrites

The **DNS rewrites** card, under My rules, answers names with an address or another name you choose: local names for servers, virtual machines and containers (`nas.home.arpa`, `*.k8s.lan`), or another address for an outside name. AdGuard Home calls these DNS rewrites; Pi-hole calls them local DNS records. Rewrites apply **on every network** (the main LAN, guest and VLAN networks) and **whether or not Wallguard is switched on**. No list, pause or profile changes them.

Type the **Name** and the **Answer**, tick **Subdomains too** if wanted, and press **Add rewrite** (or Enter). **Delete** removes a row. **Save & Apply** applies the table.

| Answer | Subdomains too | The router answers | Written as |
|---|---|---|---|
| An IPv4 or IPv6 address | off | the name only; a reverse lookup of the address returns the name | `host-record=name,address` |
| An IPv4 or IPv6 address | on | the name and every name under it (`lab.test` also answers `a.b.lab.test`) | `address=/name/address` |
| Another name (an alias) | not available | the name only: a CNAME to the other name, with that name's addresses | `cname=name,other` |

- **What a rewrite does not give is answered empty.** A name rewritten to an IPv4 address only gets an empty AAAA answer (and the reverse), and its HTTPS records are empty too, so no answer from outside can carry another address past the rewrite. To answer both families, add the name twice, once with each address. (The router adds `local=/name/` for each name; dnsmasq would otherwise send those lookups upstream.)
- **Subdomains of an exact rewrite** are looked up as usual (`server=/*.name/#`): rewriting `example.com` leaves `www.example.com` alone. A name inside a **Subdomains too** row (`kid.lab.test` under `lab.test`) answers its own address and leaves everything else (its subdomains, the other family) to the row above.
- **`*.name`** typed in the Name box (AdGuard Home's spelling) is read as the name with **Subdomains too**. Unlike AdGuard Home, the name itself is answered as well.
- **Aliases** work only for a name the router answers itself: one of your devices (its DHCP name) or a rewrite with an address. The resolver ignores an alias to an outside name. An alias cannot point at another alias, and a name that has an address cannot also be an alias; the page refuses both. The resolver will not start on a repeated alias or an alias loop, so the router leaves out any such row it finds in the file (log `DNS rewrites: N row(s) left out ...`).
- **Names**: lower-case letters, digits, `-` and `_`; labels of up to 63 characters, 253 in all; a name of digits and dots only is refused (it is a mistyped address). A one-label name such as `nas` is allowed, but devices usually ask with the LAN domain added, so add `nas.<LAN domain>` as well. The page takes up to 200 rows.
- **The lists never block a rewritten name.** A rewrite wins over every block list, My rules, pauses and profiles, and so does any name the router answers from its own records (a device's DHCP name, `/etc/hosts`). For an exact rewrite this covers that name only; its subdomains are still checked against the lists.
- **Applying a change restarts the resolvers once** (a second or two; log `DNS rewrites changed - restarting dnsmasq`). Saving the page with the table unchanged does not.
- **Where it is kept**: `/jffs/wallguard/rewrite`, one row per line (`<name> <answer>` or `<name> <answer> sub`). The router writes `/tmp/wallguard/rewrite.conf` from it at every resolver start and includes it in every resolver. The settings file (2.5) carries it with the other Wallguard files.
- **Lines of your own** in `/jffs/configs/dnsmasq.conf.add` still work beside the table. Do not define the same alias in both places: the resolver refuses to start on a repeated alias.

**Example: a lab of containers.** Add `nas.home.arpa` → `192.168.50.20`; `*.k8s.lan` → `192.168.50.40` (every service name under `k8s.lan` reaches the ingress); `plex.home.arpa` → `nas.home.arpa` (an alias). Save. **Why?** with `grafana.k8s.lan` shows *The router answers: 192.168.50.40*.

##### 4.3.3.15 Limits

- Only lookups that reach the router's resolver. A browser or app with its own encrypted DNS, a hard-coded DNS server, or a VPN go around it; DNS Director *Router* closes the plain-DNS route, the Encrypted DNS block (4.3.4.6) the encrypted one.
- By name only: ads served from the content's own host, and page elements, are not blocked.
- A LAN resolver forwarding to the router is one device for all its clients.
- Blocked services can leak where a service uses shared cloud hosts or plain IP addresses. YouTube's restrictions are Google's own and follow Google's rules for what Restricted Mode hides.
- Up to 22 profiles of your own; up to 13 of them with blocked services; up to 8 schedule ranges per profile.

<a id="4312-encrypted-dns"></a>
#### 4.3.4 Encrypted DNS

##### 4.3.4.1 What it is: two halves

The tab has two halves, each switched on its own: a server for your devices, and a block with two switches.

- **Encrypted DNS for devices** makes the router an encrypted DNS server (`rednsd`) for your devices. It has a switch per protocol, both off by default: **DNS-over-TLS** on port 853 (`reaper_dot_srv`) and, from the image after v3.7.5, **DNS-over-HTTPS** on port 443 (`reaper_doh_srv`), the protocol Windows 11 and web browsers use. A device that encrypts its DNS to an outside provider never reaches the router, so Dreadwatch, Wallguard, DNS Director and Gatekeeper cannot see or block its lookups. With this on, devices encrypt to the router instead: the lookup is encrypted on your network, answered by the router's resolver with all its rules, and sent on encrypted if DNS-over-TLS upstream is on.
- **Block encrypted DNS that goes around the router** stops devices encrypting their DNS to outside providers, so their lookups come to the router. It has two switches, both off by default: one for DNS-over-TLS and DNS-over-QUIC on port 853 (`reaper_dot_block`) and one for DNS-over-HTTPS (`reaper_doh_block`); see 4.3.4.6.

**Use the server half** when devices should keep encrypted DNS and still be filtered. **Use the block half** when devices or browsers set to their own provider are going around Dreadwatch and Wallguard, typically together with DNS Director global mode *Router*.

<a id="4342-setting-up-the-router-as-a-dot-server"></a>
##### 4.3.4.2 Setting up the router as an encrypted DNS server

1. Switch on **DNS-over-TLS**, **DNS-over-HTTPS** or both (the two switches at the top of the tab) and press **Save & Apply**. The pill reads *Running*. If DNS-over-TLS to your upstream servers is off, the Save offers to switch that on as well (4.3.4.5).
2. Check the **Certificate** card. *Trusted* works for every kind of device. *Self-signed* works only for Android phones on the *Automatic* setting.
3. Set up each kind of device (4.3.4.4).
4. **Stop devices going around the router:** in DNS Director, set the global mode to *Router*, and each guest network's row to *Router* (a row left on *No redirection* keeps its network out of the global mode, 4.22.2). Plain DNS from every device is then answered by the router, and DNS-over-TLS and DNS-over-QUIC (TCP and UDP 853) to any other server are rejected.
5. **Check it works:** *Connected now* rises as devices connect, and Android shows Private DNS as connected.
6. To stop devices going around the router altogether, switch on **Block encrypted DNS that goes around the router** (4.3.4.6).

##### 4.3.4.3 Certificates

The server uses the certificate the router's web interface uses (`/etc/cert.pem`, `/etc/key.pem`), so anything set up under **WAN › DDNS** works: Let's Encrypt for your DDNS name, **Let's Encrypt via DNS** for a name in a domain you control (no DDNS needed, below), or an uploaded certificate. The **Certificate** card shows **Name to use** (your DDNS name when the certificate covers it, otherwise its first plain name), **Issued by**, **Valid until** and the state:

| State | Meaning |
|---|---|
| *Trusted: devices can use it by name.* | It chains to the router's public CA bundle |
| *Self-signed: only Android's Automatic setting can use it.* | Add a Let's Encrypt (with DDNS, or via DNS) or uploaded certificate under WAN › DDNS |
| *Not publicly trusted* | Issued by a private authority; devices that check the name refuse it |
| *Expired* | Renew it under WAN › DDNS |

Android's *Automatic* setting does not check the name, which is why it accepts any certificate. A renewed or newly uploaded certificate restarts the server, which reads it again. Without a trusted certificate, the Android hostname line, the Apple profile and the Linux lines are replaced by *needs a trusted certificate*.

**Let's Encrypt via DNS (no DDNS, no open port).** Under WAN › DDNS, set **Certificate** to *Let's Encrypt via DNS (no DDNS)*, pick the DNS provider that hosts your domain (Cloudflare, deSEC or DuckDNS), enter a name in that domain and the provider's API token, and Apply. The router writes a temporary TXT record through the provider's API and Let's Encrypt checks that record, so nothing reaches the router from the Internet and the name does not have to point at the router. A phone connects to the router's LAN address and only checks that the certificate carries the name. The request takes about two minutes. The page shows *Requesting the certificate*, then *Issued* with the date, or the error the request ended with. The certificate is installed as the router's imported certificate and a daily check renews it about 30 days before it expires. The web interface uses a new certificate after you next sign in; Encrypted DNS restarts with it at once.

| Provider | Token | Name |
|---|---|---|
| Cloudflare | An API token with *Zone / DNS / Edit* and *Zone / Zone / Read* for the zone | Any name in a zone on your account |
| deSEC | A token from *Token management* | A free `name.dedyn.io`, or a name in your own domain hosted there |
| DuckDNS | The account token | A name ending in `.duckdns.org` |

The token is never shown on the page again; leave the field empty to keep it, and enter the new provider's token when you change provider. Choosing another certificate switches the feature off and deletes its working folder `/jffs/.le_dns` (the Let's Encrypt account key and acme.sh's copy of the token); the certificate already installed stays until the one you chose replaces it. With Warden's **Also filter the router itself** on, the provider's API and Let's Encrypt are let through for the length of each request and closed again; the log names them.

##### 4.3.4.4 Setting up devices

The tab fills these steps with your certificate's name and the router's LAN address.

- **Android 9 or later**: Settings › Network & internet › Private DNS. **Automatic** is right for phones: encrypted to the router on this network, normal elsewhere. Choose **Private DNS provider hostname** with the certificate's name only on a device that **never leaves this network** (a TV box): that setting applies on every network, and away from home, where port 853 is closed, Android has no DNS at all.
- **iPhone, iPad, Mac**: enter your home Wi-Fi names (prefilled from the router's radios, comma-separated), **Download the Apple profile** and install it (iPhone/iPad: Settings › General › VPN & Device Management; Mac: System Settings › Privacy & Security › Profiles). The profile switches encrypted DNS on **only on those Wi-Fi networks** and connects to the router's LAN address, so it also works behind another router. It is not signed, so the device shows it as *Unverified*.
- **Linux (systemd-resolved)**: on a computer that stays on this network, add `DNS=<router LAN address>#<certificate name>` and `DNSOverTLS=yes` to `/etc/systemd/resolved.conf` and restart systemd-resolved. On a laptop that travels, set it for this network only, in its network manager.
- **Windows 11 and web browsers**: they set up encrypted DNS as DNS-over-HTTPS. With the **DNS-over-HTTPS** switch on and a trusted certificate, the tab shows the address `https://<certificate name>/dns-query` with a **Copy** button. In Firefox, Chrome or Edge choose a custom provider in the secure DNS setting and paste it. In Windows 11 open Settings › Network & internet › your connection › DNS server assignment › Edit › Manual, enter the router's LAN address as the DNS server, set *DNS over HTTPS* to *On (manual template)* and paste the same address. With the switch off, leave them on their automatic setting; they then use the router's plain DNS, which Dreadwatch and Wallguard filter.
- **iPhone, iPad, Mac over DNS-over-HTTPS**: **Download the Apple profile (DNS-over-HTTPS)** makes the same profile for that protocol. Use one profile or the other, not both.

##### 4.3.4.5 How the server runs and what it respects

- **Where it answers** (the card of that name): the main LAN address (IPv4 and IPv6), each guest/VLAN network's address, and, when the WAN address is public, the WAN address *for devices on this network that look the name up* (the certificate's name resolves to the WAN address; the connection still arrives through the LAN bridge). An address marked *could not listen here* is held by something else. It accepts a connection only from a LAN or guest/VLAN subnet, and port 853 is dropped on every other interface (WAN, VPN) while it runs. A device connected through the router's VPN server is therefore not served: its lookups reach the router's DNS inside the tunnel, as plain DNS (the page says so under *How it works*).
- **Each lookup** goes to the resolver of the device's **own** network over the router's loopback, tagged with the device's address in a private field the resolver reads (only from the router itself) and removes before anything leaves the router. Dreadwatch, Wallguard profiles, the cache, DNS-over-TLS upstream and each guest network's settings apply exactly as for plain DNS, and Dreadwatch and Wallguard record the device itself. Answers too large for UDP are fetched again over TCP.
- **DNS Director**: a device it sends to another DNS server (per device, per guest network, or by the global mode) is refused before the TLS handshake. Android's *Automatic* setting then falls back to plain DNS, where DNS Director applies; a device on the hostname setting fails instead. Devices set to *Router* or *No redirection* are served.
- **Gatekeeper**: a held or blocked device cannot use it and keeps plain DNS, where Gatekeeper's rules apply.
- **Limits**: 128 connections, 8 per device, 16 lookups in flight per connection, TLS 1.2 or later; a connection that does not finish its handshake in 5 s, or sits idle for 30 s, is closed.
- **Logging**: nothing per lookup. The tiles are totals since it last started: **Connected now**, **Lookups answered**, **Refused** (not from a LAN subnet, refused by DNS Director, or over a limit). The **Encrypted DNS activity** row on Long-Term Storage writes one summary line per self-monitor tick.
- It starts as root to open port 853 and read the key, then runs as `nobody`. The self-monitor restarts it if it stops while switched on (`rednsd is not running with Encrypted DNS on - starting it`), but not after a certificate or listen error, which the page shows.

**DNS-over-HTTPS (from the image after v3.7.5).** The same server answers `https://<certificate name>/dns-query` on TCP 443 of the main LAN address (IPv4 and IPv6) and of each guest/VLAN network's address, not on the WAN address. It speaks HTTP/2 only (what browsers, Windows 11 and Apple devices use), accepts `POST` with `application/dns-message` and `GET ?dns=`, and refuses every other path, method or content type. A lookup takes the same route as a DNS-over-TLS one, so everything in this section applies to it. Port 443 is dropped on every non-LAN interface while it listens. Limits on top of the ones below: 8 lookups in flight per connection and a 4,096-byte question. The HTTP/2 framing is done by nghttp2 1.71.0, compiled into `rednsd` and used by nothing else.

DNS-over-HTTPS is **not started while TCP 443 on the router is already in use**: the web interface set to HTTPS port 443 (Administration › System), or an OpenVPN server on TCP 443. The tab says which in red, the log has `rednsd: DNS-over-HTTPS for devices is not started: TCP 443 on the router is in use`, and DNS-over-TLS is not affected. Move the web interface to another port and save the tab again. A port forward of 443 to a device is no conflict.

**Is every lookup encrypted?** A lookup has two legs, and the card of that name shows both: green when it works, red with the reason when it does not.

| Line | Red when |
|---|---|
| **Device to router** | A switch is on but the server is not running or not listening; DNS-over-HTTPS cannot use port 443; the certificate is not publicly trusted (only Android's *Automatic* setting then uses it) |
| **Router to upstream** | DNS-over-TLS to the upstream servers is off, or no upstream DNS-over-TLS server is set (*NOT ENCRYPTED*: every lookup leaves the router in the clear); the forwarder is not running; the clock is not set yet; the upstream servers do not answer a test lookup; the automatic fallback below is in force (it names the reason and the time it started) |

The upstream line is shown whether or not the server for devices is on: it covers every lookup the router's own DNS answers, plain ones too. The test is one lookup of the root's name servers through the forwarder, at most every 30 seconds while the tab is open. With the *Strict* profile nothing is resolved while the upstream servers do not answer; with *Opportunistic* lookups may leave in the clear, and the line says so. When you save the tab with a server switch on while upstream DNS-over-TLS is off and a server for it is already set, the Save asks whether to switch it on as well; *Cancel* saves without it and the red line stays. The router never switches it on by itself and never picks a provider. A device that DNS Director sends to another server, a network with its own outside DNS server and a network bound to a VPN client do not use the router's upstream.

**When the upstream leg stops working (from v3.8.4).** The router checks the upstream leg by itself every 30 seconds, whether or not the tab is open and whether or not the DNS health check is switched on: one lookup through the DNS-over-TLS forwarder that only an upstream server can answer and, with the *Opportunistic* profile, a direct DNS-over-TLS lookup to your servers at least every two minutes (every check while something is wrong). Nothing is judged before the clock is set or while the WAN is down. What happens after three failed checks in a row (about 90 seconds) depends on the profile:

| Profile | What failed | What the router does | Line on the tab |
|---|---|---|---|
| *Opportunistic* | The forwarder is not running, or none of your servers answers it | The router's DNS uses the plain WAN DNS servers (IPv4 and IPv6) instead of the forwarder, until the forwarder answers again | *NOT ENCRYPTED: ... the router has used the plain WAN DNS servers since ...* |
| *Opportunistic* | The forwarder answers, but no server completes an encrypted lookup (port 853 blocked on the way, for example) | Nothing is moved: the forwarder already asks your servers in the clear by itself in this profile, so your chosen servers keep answering | *NOT ENCRYPTED: ... the forwarder has asked the same servers in the clear since ...* |
| *Strict* | Any of the above | Nothing: Strict never sends a lookup in the clear, so lookups fail until the servers answer | *NOT WORKING: ... With the Strict profile nothing is sent in the clear, so lookups have failed since ...* |

Two good checks in a row end it by themselves: the router's DNS uses the forwarder again, and after the *in the clear* state the forwarder is restarted, because after failed connections it keeps asking in the clear for up to 15 minutes. Switching DNS-over-TLS off, or to *Strict*, ends a fallback at once. A WAN reconnect or a VPN client that rewrites the router's DNS list while the fallback lasts is undone within seconds. The log has one line when a fallback starts, changes or ends, for example `rdnshc: Encrypted DNS: the upstream DNS-over-TLS forwarder does not answer (3 checks) - Opportunistic profile: dnsmasq now asks the plain WAN DNS servers (2), ...` and `rdnshc: Encrypted DNS: the upstream DNS-over-TLS forwarder answers again (2 checks) after 210 s - dnsmasq asks it again`. The check covers the main network; a guest/VLAN network with DNS-over-TLS of its own is not watched.

**Which devices use it.** *Using encrypted DNS* lists the devices that reached the server since it started, with the protocol, the number of lookups and the time of the last one (64 devices at most). *Plain DNS only* lists devices on the router's own networks that asked port 53 in the last few minutes and are not in the first list. Names come from the DHCP leases. A device that has looked nothing up is in neither list.

**Automatic setup (DHCP option 162).** With a server switch on and a publicly trusted certificate, the router's DHCP names itself as an encrypted DNS server (RFC 9463): the certificate's name, the router's address on that network, and the protocols that are on. A device that supports the option switches to encrypted DNS by itself; every other device ignores it and is set up as in 4.3.4.4. It is offered on the main network unless you gave DHCP clients other DNS servers (LAN › DNS › *Handed to clients*), and on each guest/VLAN network that has no DNS server of its own, **except an isolated guest network and a Guest Portal network** (v3.8.0): their devices may reach the router for DHCP and plain DNS only, so an offer would name a resolver they cannot use. A guest network counts as not isolated only with **Main Network** ticked in its Access Intranet list (4.21.3); **Reach these main-network devices** and **Device discovery with the main network** open chosen devices and service announcements, not the router, so they do not bring the offer back. A device DNS Director sends to another DNS server is refused by the router's encrypted DNS server, so from v3.8.4 it is not offered either: a per-device rule leaves that device out, and a global mode or a guest network's row that redirects leaves the whole network out, except the devices a rule keeps on *Router* or *No filtering*. Before that, an iPhone with such a rule took the offer, was refused and showed *No Internet Connection*. A device that already holds the offer keeps it until its lease renews: switch its Wi-Fi off and on once. The log has `rednsd: refused <address> - DNS Director sends this device to another DNS server`, one line per address an hour. iPhones and iPads take the offer by themselves and lost DNS on such networks before v3.8.0; Android ignores it. The card's **Automatic setup** line shows the name while it is offered; the log has `rednsd: automatic setup for devices (DHCP option 162) is offered` / `is withdrawn` when that changes, and the DHCP server is restarted once at that moment. Nothing is offered with a self-signed or private certificate, because the device checks the name against a public authority and would only fail. The router does not publish the other discovery record, `_dns.resolver.arpa` (RFC 9462): a device verifies that one by finding the router's LAN address inside the certificate, which no public authority issues.

##### 4.3.4.6 Block encrypted DNS that goes around the router

A card on the same tab with two switches. Each works on its own and covers devices on the main network and every guest/VLAN network, IPv4 and IPv6. With both on, a device cannot encrypt its DNS to an outside provider.

**DNS-over-TLS and DNS-over-QUIC to outside servers (port 853)** (`reaper_dot_block`):

- TCP and UDP 853 to any server are refused (TCP with a reset). The router's own Encrypted DNS is not affected: devices reach it on the router itself.

**DNS-over-HTTPS to outside providers (known resolver addresses)** (`reaper_doh_block`):

- **The resolvers' addresses**: HTTPS (TCP and UDP 443) to the known public DoH resolvers' addresses is refused, TCP with a reset, so a browser gives up at once instead of waiting. The addresses are in the sets `redns_doh` and `redns_doh6`: a built-in list of the major resolvers (Cloudflare, Google, Quad9, OpenDNS, AdGuard, NextDNS, CleanBrowsing, Control D, Mullvad and others) is always loaded, and HaGeZi's maintained encrypted-DNS address list (`raw.githubusercontent.com/hagezi/dns-blocklists/main/ips/doh.txt`) is added daily at 05:25, at once the first time the router is online with this switch on, and by **Update list now**. Each entry is checked before it is loaded: private, loopback, link-local and multicast ranges and any range wider than an IPv4 `/24` or IPv6 `/48` are refused, because each entry refuses HTTPS for the whole network. The list is kept in `/jffs/encdns/doh.ips` so it applies from boot; a failed download keeps the previous list.
- **The DoH providers' host names** a device looks up first (`dns.google`, `cloudflare-dns.com`, `dns.quad9.net`, `doh.opendns.com`, `dns.nextdns.io` and about 40 more, with their subdomains; maintained with the firmware in `/usr/share/encdns/doh-names`) are answered NXDOMAIN. A name the router itself uses as its DNS-over-TLS upstream is never on it.
- **The browser canaries** `use-application-dns.net`, `mask.icloud.com` / `mask-h2.icloud.com` and `_dns.resolver.arpa` are answered NXDOMAIN, so Firefox's automatic DoH and iCloud Private Relay stand down. Without this switch, **Prevent client auto DoH** on LAN › DNS decides this (*Auto* answers them when DNS-over-TLS upstream or DNS Director's global mode is on).

Changing the port 853 switch rebuilds the firewall. Changing the DNS-over-HTTPS switch rebuilds the firewall and restarts the resolvers once; list updates restart nothing. Devices set to **No redirection** in DNS Director are exempt from both switches. A Firewall rules-engine Allow rule is evaluated first and can let such traffic through.

**With one switch on, the other route stays partly open.** Port 853 only: a device can still use DNS-over-HTTPS to an outside provider. DNS-over-HTTPS only: port 853 stays open, so DNS-over-TLS or DNS-over-QUIC to a server reached by its address, or by a name that is not on the provider list, still works. The provider names and the browser signal follow the DNS-over-HTTPS switch, so a device set to one of those provider names for DNS-over-TLS (Android *Private DNS provider hostname* `dns.google`, for example) is stopped by that switch as well: the name is not answered. Dreadwatch's Coverage card reads the block as on only when both switches are on.

**Upgrading from a version with one switch.** Earlier versions had a single switch for both halves. A router that had it on comes up with both switches on, and one that had it off with both off: `reaper_dot_block` is empty until it is set, and empty means *follow the DNS-over-HTTPS switch*. It stays empty until **Save & Apply** is pressed on the tab, which stores both switches as they are shown; from then on each keeps its own setting. A backup or settings file made before the split restores the same way: the port 853 switch goes back to following, so both halves take the state the old switch had.

##### 4.3.4.7 How devices react to the block

- A DNS-over-TLS or DNS-over-QUIC client (Android *Private DNS provider hostname*, a resolver set to DNS-over-TLS) is refused by the port 853 switch; a DNS-over-HTTPS client (browsers, Windows) by the DNS-over-HTTPS switch. The provider names that are not answered under the DNS-over-HTTPS switch also stop a client that looks its provider up by name first.
- An **automatic** setting (Chrome, Edge, Firefox, Windows, Android *Automatic*) falls back to the router's DNS by itself.
- A device set to **one named outside provider** (Android *Private DNS provider hostname* set to a provider, a browser set to one provider with no fallback) has **no DNS** until it is set back to automatic or to the router's Encrypted DNS. The card says so.
- To let one device keep its own encrypted DNS, set it to **No redirection** in DNS Director.

**Not stopped:** an encrypted DNS server on an address not on the list (self-hosted, a new provider), VPNs and proxies, and anything a Firewall Allow rule lets through first.

##### 4.3.4.8 Reading the page

| Part | Meaning |
|---|---|
| Pill, banner | *Running* or *Off*; when switched on but not running, the banner says why: *waiting for the router's certificate*, *the certificate could not be loaded*, *no address to listen on* |
| **Connected now** / **Lookups answered** / **Refused** | 4.3.4.5 |
| **Certificate**, **Where it answers** | 4.3.4.3, 4.3.4.5. *This router's WAN address is private* appears behind another router |
| **Devices** | 4.3.4.4 |
| **Resolver addresses on the list** | IPv4 plus IPv6 entries in the DoH address sets; a dash while the DNS-over-HTTPS switch is off |
| **Provider names not answered** | Names answered NXDOMAIN; a dash while the DNS-over-HTTPS switch is off |
| **DNS-over-TLS / QUIC refused**, **DNS-over-HTTPS refused** | Refused **packets** since the last firewall rebuild (not connections). The first counts under the port 853 switch, the second under the DNS-over-HTTPS switch; each shows a dash while its switch is off |
| List line | *List updated ... (N addresses)*, *The last list update failed; the list from ... stays in use*, or *The list has not been downloaded yet; the built-in addresses are in use* |

##### 4.3.4.9 Examples

**Encrypted and filtered phones.** Let's Encrypt on your DDNS name, or Let's Encrypt via DNS on a name in your own domain (WAN › DDNS, 4.3.4.3); switch on Encrypted DNS for devices; leave Android on *Automatic*; install the Apple profile on iPhones. Dreadwatch's Coverage card then shows Encrypted DNS as on, and the phones appear by their own address in Dreadwatch and Wallguard.

**Close every route around the filters.** DNS Director global mode *Router* (and each guest network's row *Router*), Encrypted DNS for devices on, both block switches on. Then set any device with a named Private DNS provider back to *Automatic*.

**One device keeps its own provider.** DNS Director, per-device rule *No redirection* for that device.

##### 4.3.4.10 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| A device does not connect | Self-signed certificate (only Android *Automatic* works); DNS Director sends the device elsewhere (refused on purpose) | Add a trusted certificate; check DNS Director |
| *Not running: waiting for the router's certificate*; log `Encrypted DNS for devices waits for the router's certificate` | The web interface has no certificate yet | Set one up under WAN › DDNS, or wait for it to be generated |
| An address marked *could not listen here* | Another service holds port 853 there | Stop that service |
| A phone has no internet away from home | Android set to *Private DNS provider hostname* | Use *Automatic* on phones |
| The hostname works at home but not behind a second router | Double NAT: the name points at the outer router | Android *Automatic* or the Apple profile, which use the LAN address |
| A phone or browser has no DNS after the block was switched on | It is set to one named outside provider | Set it to automatic or to the router's Encrypted DNS, or DNS Director *No redirection* |
| The block's list shows only the built-in addresses; log `encrypted-DNS address list: download failed, the previous list stays in use` | The list host cannot be reached | **Update list now**; check that `raw.githubusercontent.com` is reachable from the router |
| A browser still bypasses with the block on | Its DoH server's address is not on the list | Report the provider; DNS Director per-device rules or a Firewall rule can block it meanwhile |
| The upstream line says the router uses the plain WAN DNS servers | The DNS-over-TLS forwarder is not running, or none of your DNS-over-TLS servers answers it (blocked by the ISP or a firewall upstream, a server down) | Nothing to do for DNS to work; to get encryption back check that the servers in WAN › DNS are reachable on their port (853 by default). With *Strict* there is no fallback by design |

##### 4.3.4.11 Limits

- The WAN-address route needs the public address on this router. Behind another router, Android *Automatic* and the Apple profile still work; the hostname settings do not.
- DNS-over-HTTPS (since v3.7.6) speaks HTTP/2 only, on port 443 of the LAN networks. A browser or Windows 11 uses it only when set up with the router's DoH address (4.3.4.4); Apple devices may also find it from the DHCP option 162 offer. Guest networks without Access Intranet are never offered it (4.21).
- Guest/VLAN networks are served over IPv4.
- Flow Explorer's destination names are learned from plain DNS replies; lookups made over Encrypted DNS add no names there.
- The block covers known resolvers only (4.3.4.7).
- The automatic fallback of the upstream leg watches the main network's DNS-over-TLS forwarder only; a guest/VLAN network with its own DNS-over-TLS servers has no fallback.

### 4.4 Policy Routing

**What it is.** A page in the VPN menu, next to VPN Director, that decides *which traffic* uses *which path* — an OpenVPN client, a WireGuard client, the plain WAN, or nowhere at all — by a rule you write. It adds the piece VPN Director lacks: rules keyed on a named **Firewall object or domain list** (destination), or on a **device by IP/CIDR or MAC** (source).

It is **off by default**, and turning it on changes nothing until you add a rule.

**When to use it.** Routing a *set of sites* through a tunnel; carving an exception out of a full-tunnel VPN; forcing one device through a VPN and **blocking** it if the tunnel drops; a hard "this device goes nowhere". If you only need plain source routing without those properties, VPN Director alone is fine.

#### 4.4.1 How it works

A rule has two halves: **what to match**, and **where to send it**. When traffic matches, the router marks it and steers it through the routing table for the target you chose — a VPN client's table, the normal WAN table, or a dead end.

It is built entirely from mechanisms already in the firmware — a firewall mark plus a routing-policy rule — so it adds no new moving parts and reuses the routing tables your OpenVPN clients already set up. Nothing here dials a tunnel or changes a VPN's own settings; it only decides what rides through one that is already connected.

**Applying never interrupts routed flows.** Since v3.3.4 an apply - and a VPN client's Killswitch change, which regenerates
the rules - builds the new marking chain beside the live one and swaps the hook in a single step, keeps every routing
rule that is unchanged, and adds the new ones before any stale one is removed. Earlier versions tore everything down
first, so each apply had a moment with no rules in which a new flow could reach the WAN directly and a flow in a tunnel
lost its path.

**Policy Routing and VPN Director are meant to sit side by side.** Use VPN Director for the broad posture ("send everything through the tunnel", or "send this subnet through the tunnel"), and Policy Routing for the exceptions that need an object or a device — because a Policy Routing rule **wins** over a VPN Director rule for the same traffic. That is what lets you say "tunnel everything, *except* send this one streaming service straight out the WAN."

#### 4.4.2 The page

**The master switch** turns the whole engine on or off. With it off, no marks and no routing rules are placed, whatever is in the table.

**The rule table** lists your rules in order, with the match on the left and the target on the right, each with its own enable checkbox so you can park a rule without deleting it.

**The add-rule form** builds one rule: pick the selector type, fill in its value, choose the target, and add it. Every row also has **Modify**: it loads the rule back into the form, the Add button becomes Save, and saving replaces the rule in place.

**Apply and confirm** puts the whole list into effect at once and starts the same auto-revert countdown the Firewall Rules tab uses (the timer is set on the Firewall page): press **Keep** to make it permanent, or let it expire — or press **Revert** — and the previous rules come back on their own. The router owns that deadline, so closing the tab does not cancel it. Keep is the only thing that writes flash.

**The Domain lists card** is where you build and maintain the lists the rules point at (4.4.4). You no longer have to go to the Firewall page for this.

**The ASN lists and Country lists cards** (from v3.8.4, marked *Advanced*) build lists the router fills by itself from published address ranges: everything a network operator announces, or everything in one country (4.4.4a).

#### 4.4.3 What a rule matches

Each rule matches traffic one of three ways:

- **Domain list / object (destination)** — a named list of domains built on this page, or any Firewall address object or group, chosen from the dropdown. The rule matches traffic whose **destination** is in that list. This is the powerful one: name a set of streaming sites, a network operator or a country, and route everything headed *to* it in one rule. An ASN list or a country list (4.4.4a) is chosen from the same dropdown.
- **Device by IP / CIDR (source)** — a single address or a range on your LAN, or a list of them (IPv4 or IPv6, one per line or comma-separated, up to 64). The rule matches traffic **from** it.
- **Device by MAC (source)** — a device's hardware address. The rule matches traffic **from** that device, wherever it picked up its IP.

##### VPN Director already routes by source IP — what do the device rules add?

A fair question; VPN Director's source rule and a device rule here do steer the same packets. The device rules exist for what they add on top:

- **Block as a target.** "This device goes nowhere", without a firewall rule.
- **MAC keying.** A MAC rule follows the device across DHCP changes; an IP rule does not.
- **Precedence.** A rule here **overrides** a VPN Director rule for the same device, so you can carve one device out of a broad "route this subnet" policy.

If none of those matter to you, VPN Director alone is fine — use whichever you find clearer.

#### 4.4.4 Domain lists

A domain list is a Firewall object of type *Domain name*: a name plus the domains it covers. The card on this page lets you **add, modify and delete** them without leaving Policy Routing; the Firewall page sees the same lists, so nothing is duplicated.

- **Entering domains.** The box takes one domain per line, or a comma- or space-separated paste from a text file. Blank lines and duplicates are dropped, everything is lower-cased, and each name is checked before it is saved. A list can hold as many domains as fit in about 1,900 characters — if a service needs more, split it into two lists and two rules.
- **How a list becomes addresses.** Two mechanisms feed it: every DNS answer the router's own resolver gives for a listed name lands in the list immediately, and a timer re-resolves every name **every 10 minutes** as a floor — which covers clients that use their own DNS, names already cached, and the cold start after a reboot. Addresses expire an hour after they were last seen, so a CDN that rotates its pool prunes itself.
- **Across reboots.** After every timer pass the lists are **saved to the router's flash** — only when their content changed (v3.8.1) — and restored the moment they are re-created at boot, so a rule is not blind until the first lookup. The saved copy is restored only into an **empty** list (v3.8.1): a list that already holds addresses keeps its own expiry times, so an address the names no longer resolve to is not kept alive by firewall restarts. A rule whose set was a moment late at boot is re-applied by `rwatch` (logged, at most every two minutes).
- **A list matches addresses, not names.** A rule sees the address a packet is going to. Many sites share addresses (one content network serves thousands of them), so a site you never listed can be routed by a list that holds its address, and with *first match wins* (4.4.6) the list **higher up** takes an address two lists share. If a listed site leaves by the wrong path, find which list holds its address — `ipset test rwfw_<list> <address>` for each list, in rule order — and move the more specific list above the broad one.
- **Whose lookups fill a list.** Only answers from the **router's own resolver** add addresses at once. A device that asks another resolver adds nothing by its lookups: a browser with its own encrypted DNS, a device with a hand-set DNS server, and a device that **VPN Director** sends to a VPN client with a DNS server of its own (its lookups go to that server, inside the tunnel). For such a device the 10-minute timer still resolves the names you typed, but not the sub-names a site uses. This is the main difference in what a device sees between a VPN Director rule and a Policy Routing source rule for the same tunnel.
- **CDNs change.** When a service starts reaching out to a domain you did not list, the traffic is not matched. That is the one piece no timer can fix for you — come back and **Modify** the list.
- **The Firewall engine does not need to be on.** The lists are built whenever Policy Routing is enabled, engine or no engine. If the Firewall engine *is* on and you edit a list here, the routing side uses the new list on Apply; the Firewall's own rules pick it up on the Firewall page's Apply, as its commit-and-confirm flow requires.

#### 4.4.4a ASN lists and country lists

*From v3.8.4. Advanced.* Two more kinds of list for the **Domain list / object** selector. The router fills them itself from published address ranges instead of from names you type:

- An **ASN list** holds everything one or more network operators announce. Every operator on the internet has an AS number (ASN); Netflix's own network is AS2906. Enter `AS2906` or `2906`, up to 16 numbers in one list. Use it for a destination that is defined by who runs it - a VoIP trunk provider, a service that checks where you connect from - where a hand-kept address list goes stale and a domain list misses addresses an app has built in.
- A **Country list** holds the address ranges of one country, chosen from the same country table Warden uses.

Select either in a rule exactly like a domain list. Nothing else changes: the target, the Killswitch, the order of rules and the Keep / Revert timer work as for any other rule, and the router only decides which of its own interfaces the traffic leaves by.

**When a list is loaded.** Only while Policy Routing is on and an enabled rule uses the list (directly or through a group), after **Apply**. A list no rule uses is not downloaded and takes no memory; its row says *not used by a rule*. The **Loaded** column shows how many IPv4 and IPv6 ranges are in the list right now.

**Where the ranges come from.** The **Source** column names the source in use and the time of the last check.

| List | Sources, in this order |
|---|---|
| ASN list | **ipverse** (`raw.githubusercontent.com/ipverse/as-ip-blocks`), then **RIPEstat** (`stat.ripe.net`), then **HackerTarget** (`api.hackertarget.com`) |
| Country list | **Warden's own list** when Warden already blocks that country and holds both its IPv4 and IPv6 ranges (copied on the router, nothing is downloaded), then **ipdeny** (`www.ipdeny.com`), then **ipverse** (`raw.githubusercontent.com/ipverse/country-ip-blocks`) |

The next source is asked only when the one before it gave no usable range. The request carries the AS number or the country code and nothing about your network. HackerTarget's free service answers a small number of requests a day, which is why it is last.

**When the lists are refreshed.** Once a day (05:17), and when you press **Update now**. A list that has never been fetched is fetched right after Apply; if that download fails (at boot, for example, before the internet connection is up), the list is asked for again as soon as the WAN connects and then every 15 minutes until it arrives. A list every source answers with no ranges at all (an AS number that announces nothing) is not asked for every 15 minutes: it is tried again at the daily refresh, when the WAN connects and at boot. Each list is saved on the router's flash (`/jffs/reaper_fw/lists`, rewritten only when it changed) and put back from there at boot before anything is downloaded. When the last rule that uses a list is removed, the list's address sets, its saved copy and the daily job go when you press **Keep** (or **Revert**, for a list only the reverted change used).

**The sources are in your "do not block" lists.** Warden and Dreadwatch can stop the router's own downloads: with **Also filter the router itself** on, a blocked country or a feed that covers a source's address, or a threat list that names the source. So the first time an ASN or country list is used by a rule, the router adds the sources once - their addresses to Warden's **Whitelist** (the table in 4.3.1.7: `raw.githubusercontent.com`, `stat.ripe.net`, `api.hackertarget.com`; `www.ipdeny.com` has its entry already) and the names `ripe.net` and `hackertarget.com` to Dreadwatch's **Never block these names** (`githubusercontent.com` and `ipdeny.com` were there already). The log names what was added. Nothing you entered is changed, a router that never uses such a list gets nothing added, and **an entry you delete is never put back**.

**What happens when a download fails.** The list already loaded stays in use, and the row says *no source answered* with what each source said (*name not resolved*, *no connection*, *not found*, *no prefixes in the reply*, *covers too much of the internet, not used*). If **Also filter the router itself** is on and a blocked country covers a source whose Whitelist entry you removed, or whose address has changed since the entry was added, the router blocks its own download: RIPEstat is hosted in the Netherlands, ipdeny in France. The page says so when a source could not be reached with that switch on; put the address back in the Whitelist, or use the other sources. When one half of a reply fails while the other arrives (the IPv6 file times out, say), the saved ranges of the failed half stay in use; only a source that answers it has none of them removes them.

**What is kept out of a list.** A downloaded list decides where your traffic goes, so the router does not take it on trust:

- Only entries of the form address/length are read; everything else in a reply is ignored.
- Private, loopback, link-local, carrier-NAT, multicast and reserved ranges are dropped, and so is any wider range that contains one of them (`192.0.0.0/8` holds `192.168.0.0/16`) and anything wider than /8 (IPv4) or /16 (IPv6).
- A reply that adds up to more than half of the internet (over 2,147,483,648 IPv4 addresses, or half of the IPv6 unicast space) is not used at all, since no network operator or country holds that much: the next source is asked, and the row says *covers too much of the internet, not used*. With the rule above, a wrong list cannot capture your LAN or the whole internet.
- A list is replaced whole or not at all. One with more ranges than its set can hold (65,536 per family for an ASN list, 262,144 for a country), or more than a quarter of the free memory, is refused: the row says *too large, not loaded* or *not enough free memory, not loaded* and the previous list stays.
- The new list is built beside the old one and swapped in, so a rule never matches an empty or half-loaded list during a refresh.

**Limits to know before you rely on one.**

- **Content served from inside your ISP is not in the operator's AS number.** Netflix places servers inside many ISPs; those use the ISP's own addresses, so AS2906 alone does not catch all Netflix traffic. Add a domain list where that matters.
- **Only the AS numbers you list.** A customer network that announces its own addresses has its own number and must be added on its own.
- **A large shared network carries thousands of unrelated sites.** Routing Amazon's or Google's AS number moves far more than one service.
- **A daily snapshot from third parties.** A range announced since the last refresh is missed until the next one, and a wrong list sends traffic by the wrong path until it is corrected upstream.
- **Flows already running keep their path** when a list changes, until they end - the same as for a domain list.
- **Traffic to a country Warden blocks is dropped whatever its route.** The row says so. A country list is for a country you reach, not one you block.
- **In use at once:** 32 different AS numbers and 8 different countries. A list that would pass that is not loaded and the log says so.
- **ASN lists exist only on this page.** They are not offered to Firewall rules and do not appear in the Firewall page's object table. A country list is an ordinary country object: on this page it gets its own address set; in a Firewall rule the same object still means Warden's set for that country (4.1).

**To check what a list holds:** `ipset list -t rwfw_<list>` (IPv6: `rwfw6_<list>`) and `ipset test rwfw_<list> <address>`. The log tag is `reaper_fw: lists:`.

#### 4.4.5 Where a rule sends traffic

Every rule has one target:

- **A VPN client (OpenVPN 1–5)** — matched traffic goes through that OpenVPN client's tunnel, using the routing table the client already created. The tunnel does not have to be the default route; this steers only the traffic you named through it.
- **WAN** — matched traffic is forced out the normal internet connection, **bypassing** a full-tunnel VPN and any VPN Director rule for it. This is how you carve an exception out of "route everything through the tunnel". The row simply reads `WAN`; the bypass is stated once in the notes under the table, and as a hint when you pick WAN as a target (v3.1.5).
- **Block** — matched traffic is dropped. Useful as a hard "this device, or this destination, goes nowhere" that does not depend on the firewall rule order.
- **WireGuard 1–5** — supported since v2.6.7, with a cost described in 4.4.9. A WireGuard rule whose client is switched off lets the selected traffic use the WAN: a switched-off client blocks nothing, whatever its Killswitch says (4.4.7). Since v2.7.7 the target list **hides tunnels that are not enabled**, so a rule cannot be pointed at a target that was never going to carry it; a rule that already names a switched-off client keeps its target and shows *Inactive · WAN* in the Status column (v3.1.5). The accelerator-bypass table (4.4.9) has **eight IPv4 and eight IPv6 slots**, shared with VPN Director's WireGuard rules and the WireGuard server's peers. A WireGuard rule is never refused for it: the marking and routing rules go in regardless. If no slot is free, the apply reports a **partial failure**, the log names the entry, and until a slot is freed flows from that source that the accelerator has already learned keep their old path. If the tunnel's interface is not up yet when the rules are applied (at boot, Policy Routing applies with the firewall, before the WireGuard client starts), the bypass is recorded as **pending** and installed the moment the client starts (v3.1.7); the diagnostics bundle's section 14d shows each bypass as *new*, *pre* or *pending*.

**IPv6 is covered** (v2.6.7): a destination list matches its IPv6 addresses, a MAC rule follows the device on both families, and a source rule may name an IPv6 prefix. If the chosen tunnel carries no IPv6, the selected IPv6 traffic is blocked when that client's Killswitch is on and uses the WAN when it is off - the same rule as for a tunnel that is down (4.4.7).

#### 4.4.6 Order and precedence

Rules read **top to bottom, first match wins** — put specific rules above broad ones. A device that should mostly use a tunnel but reach one site directly needs the "reach this site directly" rule *above* the "send this device to the tunnel" rule.

Between features, **a Policy Routing rule takes precedence over a VPN Director rule** covering the same traffic. So you do not have to unpick VPN Director to make an exception — you add the exception here and it wins.

#### 4.4.7 Fail-closed or fail-open: the Killswitch decides

A rule chooses the **path**. What happens when that path is gone — the tunnel is down — is decided by that VPN client's own **Killswitch**, on its VPN page, exactly as it is for VPN Director; a client that is switched off is not a path at all, and its traffic uses the WAN:

- **Killswitch on** — the matched traffic is **blocked** until the tunnel is back. This is the setting to use when the whole point of the rule is that the traffic must *never* touch the internet directly.
- **Killswitch off** — the matched traffic **falls back to the WAN** while the tunnel is down, and returns to the tunnel when it is up.
- **Client switched off** — the Killswitch does not apply to a client that is not enabled (v3.1.5, the same condition VPN Director puts on its own rule): the matched traffic **uses the WAN** until you enable the client again.
- **OpenVPN client with Redirect Internet traffic set to *No*, or a TAP client** — the Killswitch does not apply either (from the image after v3.8.0). Such a client carries only the networks its server pushes, so there is no "tunnel down" for general traffic to be protected from; the VPN Client page hides the switch in that mode, and a switch saved earlier is ignored, not changed. Before this, a Policy Routing rule to such a client with a saved Killswitch was refused Internet access even while the tunnel was up. Set Redirect to *VPN Director rules* to send a rule's traffic through the tunnel with the Killswitch behind it.

Reaper does not override that choice. Before v3.1.3 every VPN-client rule was blocked regardless of the Killswitch, which meant Policy Routing and VPN Director disagreed about the same client; now one setting governs both. A rule to an OpenVPN client whose Redirect Internet traffic is *No* reads *Active · pushed routes only* (only the networks that client's server pushes use the tunnel; everything else uses the WAN), a rule to a TAP client reads *Inactive · WAN · TAP* (it has no effect), and TAP clients are not offered as a target for a new rule (from the image after v3.8.0). The rules table's **Status** column says which applies to each rule: *Active*, *Active · Killswitch* (a dropped tunnel blocks rather than leaks) or *Inactive · WAN* (the client is switched off); the notes under the table state the rule once.

What the router actually installs is the same pair VPN Director installs, keyed by the rule's mark instead of its source address. For a rule to WireGuard 2 whose client is enabled with its Killswitch on:

```
9007:  from all fwmark 0x70000/0xf0000 lookup wgc2
9107:  from all fwmark 0x70000/0xf0000 prohibit      <- only with the Killswitch on and the client enabled
...
11410: from 192.168.1.230 lookup wgc2               <- VPN Director's own pair, for comparison
12216: from 192.168.1.230 prohibit
32766: from all lookup main
```

The `prohibit` sits directly beneath the lookup and above `main`, on both IPv4 and IPv6, so a flushed tunnel table blocks the flow instead of leaking it. The whole 9000 band sits above VPN Director's 10000 band on purpose: a Policy Routing rule is evaluated first and overrides VPN Director for the flows it names. Codes are 1–5 OpenVPN, 6–10 WireGuard, 11 WAN (`lookup main`, never a prohibit) and 15 Block (`prohibit` at 9015). With the Killswitch off, or the client switched off, the 9107 line is simply not installed.

The same decision covers IPv6: a tunnel that carries no IPv6 blocks the selected IPv6 traffic when the Killswitch is on, and lets it use the WAN when it is off.

#### 4.4.8 Examples

**Send a set of streaming sites through a VPN, leave everything else direct.**
Build a domain list `streaming` in the card on this page, listing the services' domains. Then add a rule: selector **Object** = `streaming`, target **OpenVPN 1**. Only traffic to those domains uses the tunnel; the rest of the house is untouched.

**Tunnel the whole house, but send one service straight out the WAN.**
Set VPN Director (or a broad rule) to route everything through the tunnel. Then here: selector **Object** = `work-app` (a domain list for the service that dislikes the VPN's exit address), target **WAN**. Because Policy Routing wins over VPN Director, that one service goes direct and everything else stays tunnelled.

**Force one device down a VPN, and nowhere else if it drops.**
Selector **Source MAC** = the device's address, target **OpenVPN 2**, and OpenVPN 2's **Killswitch on** (its VPN page). If OVPN 2 is connected the device uses it; if OVPN 2 goes down the device has no internet rather than quietly falling back to your real address. With the Killswitch off it would fall back to the WAN instead.

**Send a device — or a destination — nowhere at all.**
Selector **Source IP** (or **Object**), target **Block**. A hard stop that does not depend on where it sits in the firewall's own rule order.

#### 4.4.9 Limits and gotchas

- **WireGuard costs hardware acceleration.** The traffic accelerator does not honour a routing rule whose exit is a WireGuard tunnel, so Policy Routing does what VPN Director does and tells the accelerator to leave the affected flows alone. A **source** rule bypasses only that address. A **destination-list or MAC** rule must bypass the **whole LAN** — LAN traffic loses hardware acceleration while such a rule exists. The note under the rules table says so whenever a WireGuard rule exists, and the log says so on every apply. Prefer a source rule over a destination-list rule where you can. Entries VPN Director or the WireGuard server placed are never removed.
- **Why the bypass has to exist, and what it cannot do.** The accelerator decides a flow's path on its first packets; once a flow has been handed to it, the marking chain and the routing rules never see that flow again. A bypass entry is checked on packets the router's CPU sees, so it cannot pull back a flow that was accelerated *before* the entry existed — which is why every apply that installs a WireGuard bypass also clears the accelerator's learned flows, so that every flow is judged afresh. A *new* connection from a bypassed source always takes the CPU path and is judged by your rule. If a source rule to a WireGuard client still reaches the internet directly, look at the bypass first (section 14d of the diagnostics bundle: *pending* means the client interface was down at apply time — before v3.1.7 nothing installed it later; a *table full* log line means the eight slots for that address family were taken), then at the tunnel's own routing table (14d warns when a rule targets a client whose table has no default-covering route: check the client's Allowed IPs). Before v3.1.7 a rule whose target was changed from one WireGuard client to another also kept routing existing connections by the old, now unrouted verdict; those connections used the WAN until they ended.
- **Replies come home (v3.2.4).** Before v3.2.4 a source rule to a WireGuard client sent the request into the tunnel correctly, but the reply was routed straight back into the tunnel, because the WireGuard client's table has no route to the LAN; the device saw no answer at all. The marking chain now leaves reply traffic to the main table. OpenVPN targets and VPN Director were never affected.
- **Protocol and port matching is not offered.**
- **A list that has not resolved yet, or an emptied group, produces no rule** rather than a rule that matches everything — the same fail-to-nothing behaviour the firewall uses.
- **Objects are shared with the Firewall.** Domain lists are edited here or on Firewall → Objects; they are the same objects. Address and MAC objects are still created on the Firewall page; address objects appear in the dropdown, a MAC object cannot be selected here. A country object made on either page is the same object. An ASN list exists only on this page (4.4.4a).
- **A confirmed set survives a reboot on its own** (v2.7.6/v2.7.7). The marking chain and the routing rules come back complete at boot with no visit to this page, and if the routing half is ever lost the router re-applies it the way it already did for a lost firewall chain.
- **Rules live on the router's internal flash** (`/jffs`), not in the stock settings backup — use **Download full backup** or **Export settings** on **Administration → Backup & Restore** (2.5). Twenty rules and more save without trouble.
- **Add rules from a device that is not itself being routed** by the rule you are testing.
- **To check what actually loaded**, the rules appear as routing-policy entries and a marking chain on the router; if something is not behaving, the system log names any rule that was skipped and why.
- **AiMesh nodes are never policy-routed (v3.6.5).** A node's own traffic skips the marking chain, from the shared `reaper_aimesh` set (4.1.3), so a broad source or destination rule cannot send a node down a tunnel or into a Block.

### 4.5 QoS (Traffic Manager)

**What it is.** Five modes, two of which are Reaper's own hardware engines. Those two shape traffic inside the Broadcom traffic manager **with the NAT and flow accelerator left on** — which is the thing ASUS never shipped. Stock forces a choice: hardware acceleration *or* software QoS. These give you both.

**When to use it.** Any line where upload saturation makes calls stutter or games lag. If your calls are fine and nothing ever feels slow while something is uploading, you do not need this page.

#### 4.5.1 Choosing a mode

| Mode | What it does | Accelerator |
|---|---|---|
| **HW QoS Classful** (type 11) — *recommended* | Five strict-priority classes with guaranteed minimums and per-class ceilings, hardware AQM on every queue, and an opt-in download policer. | **On** |
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

**Link overhead (Traditional and Cake).** Below the bandwidth fields, the **Link overhead** row tells the shaper how many bytes each packet really costs on the line, so it does not overbook it: pick the preset that matches your connection (Ethernet with VLAN, cable, the ADSL/VDSL variants) or enter the bytes yourself; **Framing** is Ethernet, ATM (ADSL: every packet rounds up to 53-byte cells) or PTM (VDSL2: 1/65 off the rate); **MPU** (Cake only) is the smallest size a packet is counted as. Ethernet with 0 bytes means no compensation. These are the same `qos_overhead`, `qos_atm` and `qos_mpu` settings the stock QoS page offered; they were unreachable on Reaper from the QoS rewrite until 22 October 2026.

#### 4.5.3 Setting up the classful engine

1. Enter the bandwidth figures as above.
2. Select **HW QoS Classful** and let the router reboot.
3. The classes ship as a measured profile — **Web/VoIP**, **Gaming**, **Streaming**, **Downloads**, **Default** — with starter rules for conferencing, SIP, game consoles, Steam, BitTorrent and web traffic. The factory minimums and ceilings are Web/VoIP 15-90%, Gaming 15-90%, Streaming 20-90%, Downloads 5-95%, Default 25-95% (`qos_orates`, 8.1). No class starts at a 100% ceiling (Web/VoIP did until v3.8.0); a router that already holds its own rates keeps them.
4. Leave the **Aggregate cap (port shaper)** on.
5. **Guaranteed minimums** is on at factory; turn on **Trust DSCP marking** only as below.
6. **Apply.**

**Trust DSCP marking is off by default, deliberately.** DSCP is a claim the sending device makes about its own traffic, and any device on your LAN can mark its packets however it likes. Turn it on only if you control what is on your network and something on it marks correctly.

#### 4.5.4 Priority and ceilings: the two knobs

The class editor has two independent controls, and confusing them is the second most common mistake.

- **Order is priority.** The top row is served first under contention. Rank by how much the traffic suffers from waiting: interactive and voice at the top, bulk at the bottom.
- **Ceiling % is the most a class may ever take**, as a share of your upload figure.
- **Min % is a floor** the class is guaranteed under load. Minimums must total 100% or less.

**Never give the top class a 100% ceiling.** Its ceiling is the only thing protecting everything below it.

**The counter-intuitive part: bulk traffic wants a low priority and a *high* ceiling.** Strict priority means it yields instantly the moment anything above it has traffic, so it cannot hurt you — and the high ceiling lets it use the whole line when nothing else wants it. A backup class at the bottom with a 95% ceiling is correct.

**Traditional QoS (type 0).** When Traditional is selected the page shows its own **Traditional QoS priorities** table: five classes, Highest to Lowest, served strictly in that order, each with an upload minimum and maximum and a download maximum as percentages of the bandwidth above (a class with a 0 maximum is unused), plus the **Prioritise small packets** switches (ACK, SYN, FIN, RST, ICMP) that lift those packets into the top class. The upload figures are the same `qos_orates` the classful editor edits. This panel restores the stock priority page's settings, which had no control on Reaper until 22 October 2026.

#### 4.5.5 Classification rules

Rules match traffic to a class on port, protocol, address or MAC. From 22 October 2026 they are edited on the QoS page itself, in the **User-defined QoS rules** table that appears for Traditional QoS and HW QoS Classful (the two engines that use them). Each rule has a name, a source (empty for every device; an IPv4 address; a range such as `192.168.50.10-20`, `192.168.50.*` or `192.168.50.0/24`; or a MAC address), a destination port (empty for any; one port; a range such as `3478:3481`; or a comma-separated list of up to 15 entries), a protocol, an optional transferred range in KB, and a priority. Under the classful engine the priority menu lists your classes in table order, so renaming or reordering a class relabels the rules. The **Select the service name** menu fills the row from the stock catalogue of about 60 services (web, mail, VoIP, games...); nothing is added until you press Add. Up to 128 rules, within 4,096 characters of router storage; the line under the table shows both counts. Apply saves the rules with the rest of the page; the firewall restarts, no reboot.

> **Do not classify by transferred bytes.** Rules that match on "how much this connection has transferred" cannot be offloaded to hardware. An accelerated flow keeps whatever class it was given when the connection *started*, so a rule meaning "once this download passes 512 KB, treat it as bulk" never fires for the flows that matter most — the long ones. The page warns about this. Some stock default rules are written this way, which is why the shipped Reaper rule set replaces them.

Unmatched traffic lands in the class named **Default**.

#### 4.5.6 Why download is different

The hardware engines shape **upload only**, and this is a hardware limit rather than an omission.

The traffic manager's queues are an *egress* object: they exist on the way out of a port. On the download side the chip offers a single **aggregate policer** — one rate limit for everything arriving — with no queues and no per-class split. There is no hardware path that could prioritise one kind of download over another, and the CLI cannot bind the per-flow policers that exist deeper in the silicon.

So:

- **Download bufferbloat** is handled by the aggregate policer (classful mode), or properly by **Cake**, which shapes in software at the cost of the accelerator.
- **Download prioritisation** is not offered. The Wi-Fi WMM lift that once tried to deliver it measurably halved wireless throughput in both directions and was removed; the policer is a cap, not a priority scheme.
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
- Classes were served in **inverted priority order** until v2.5.4.
- On a **GT-BE98**, the v2.5.4 queue rebuild could be rejected by the traffic manager, taking all IPv4 off the air while IPv6 still worked. v2.6.0 made the rebuild transactional: on rejection the queues are restored to the stock layout and a log line says the priority correction was not applied. Worst case is now the old priority order, never no internet.
- **An ISP / IPTV profile (v3.6.3).** With an ISP profile (`switch_wantag`) and an STB port or a WAN VLAN tag, the WAN device is the profile's VLAN interface, which the traffic manager refuses; both hardware engines now shape the physical port under it, as Asuswrt-Merlin's HW AQM does (Eric "Merlin" Sauvageau). A port that also carries the LAN is still refused (next item), and the QoS page's "LAN trunk" note shows only for the GT-BE98 family's shared jack.
- **PPPoE, PPTP and L2TP lines (v3.3.7).** Both hardware engines shape the physical port the session rides on (an ISP VLAN is resolved to its parent port), not the `ppp0` interface, which has no hardware queues; earlier images shaped nothing on these lines. The shaper then counts PPPoE's 8-byte header, so set the upload a little under the line rate. The system log names the port each engine shapes.
- **A port that also carries the LAN is never shaped (v3.3.9).** On the GT-BE98 family the 2.5G WAN/LAN-1 jack is a VLAN on the switch trunk that also carries LAN 2–4 and a wired AiMesh backhaul; shaping that trunk at the upload rate made the router unusable on v3.3.8. When the resolved port is a bridge member or a LAN port, both hardware engines refuse to arm with one log line, and the QoS page says so beside the engine choice. Use Cake on that layout, or move the WAN to a dedicated WAN port.
- **Leftover settings from a previous mode stay in place, inert.** Switching from classful to type 10 leaves the classful keys set. They do nothing, but they can make a perfectly healthy type-10 configuration look like a broken classful one when you go looking.
- Cake mode filters redundant upload acknowledgements and targets a 50 ms base round-trip time.

### 4.6 QoS Diagnostics

**What it is.** A tab to the right of QoS under Traffic Manager: a live view of the hardware traffic manager (the Runner/XRDP egress scheduler) — per-queue occupancy, scheduler discipline, drops per second (tail + AQM combined), shaper rate and configured size, an *estimated* delay (backlog ÷ shaper rate; the hardware has no direct latency counter), live trend graphs and a port selector for the WAN-upload and LAN-download schedulers.

**When to use it.** To verify that shaping is engaging, to see which queue is dropping under load, or to confirm after a firmware upgrade that the five class queues exist (the GT-BE98 IPv4 incident in 4.5 showed up here as queues that were simply gone).

**What to expect.** Fast polling (250–500 ms) runs only while the page is open. The view adapts to your mode: a single shaped queue under Hardware QoS, the full scheduler under HW Classful; "No egress traffic-manager data" means QoS or the accelerator is not active. Occupancy reads 0 on an idle link and fills under load. Counters are 32-bit and wrap about every 15 seconds at ~2 Gb/s; a wrap is discarded rather than drawn as a spike. Trends fill from the left and flow smoothly.

**How to use it.**

1. Open **Traffic Manager → QoS Diagnostics** with QoS on (Hardware QoS or HW QoS Classful, 4.5). Pick the scheduler with the port selector: the WAN port for uploads, a LAN port for downloads.
2. Start a load that fills the line (a large upload for the WAN scheduler) and watch **occupancy** and **drops/s**. Under load, a shaped queue should fill and its drops rise; that is the shaper working. A queue that stays at 0 while the line is full means traffic is not reaching it (the class rules in 4.5.5 do not match, or the accelerator is off).
3. Read the **estimated delay**: it is the queue's backlog divided by the shaper rate. A delay that climbs and stays high at a modest load means the shaper is set above what the line really carries; lower the rate on the QoS page and check again.
4. After a firmware update, open the page once with QoS on and check that the expected queues exist (one under Hardware QoS, five under HW Classful).

### 4.7 Traffic Analyzer

**What it is.** A native bandwidth and usage page driven by the `rtrafd` collector: live WAN throughput, an optional latency and loss chart, per-QoS-class upload, per-network totals, top devices, live top talkers by destination-port bucket, and a monthly data cap. **Off by default:** switch it on with the page's toggle; nothing is recorded before that.

**When to use it.** To see who is using the line and when, to confirm QoS classes are actually receiving traffic, and to keep an eye on a metered connection.

**On privacy.** The collector **adds no listening ports** and sends nothing anywhere. It reads counters the kernel already keeps. The one thing that leaves the router is the optional latency probe, and only if you give it a target.

#### 4.7.1 Turning it on, and where history lives

1. In **Settings**, turn on **Collect traffic history**. Without it the realtime monitor still works, but there is no history and no per-device accounting.
2. **History storage** is a pointer to the Long-Term Storage page (4.11), where you choose RAM, JFFS or USB.
3. Optionally set a **WAN latency probe** target and a **Monthly data cap**.

> **The storage choice is the one that matters.** The default is **RAM**, and on RAM every number you see is lost at the next reboot. If you want history that outlives a restart — and the 14-day, monthly and yearly views only mean anything if it does — set the store to JFFS or USB *before* you start collecting. USB is the right answer if you have a stick in the router: it is larger and it spares the internal flash the write cycles.

The **latency probe** sends one ping every 5 seconds to the target you name. **Leave it blank and nothing is sent at all.** With a target set, the **Latency & loss** chart under WAN throughput draws the round-trip time on the left axis (ms) and the share of probes lost over the last minute on the right axis (%), on every window: live, it moves with the throughput chart (the last reply is held until the next probe arrives, so the line is continuous rather than a dot every 5 seconds); on the history windows, a period with no reply leaves a gap rather than a zero. The **Latency** and **Loss** tiles show the one-minute figures. With the probe off the chart says so and points to Settings.

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
- **Guest Portal panel (v3.7.7).** On the **Live** window, a router with a Guest Portal network shows a panel listing each signed-in guest with their current speed and session time. A guest network you remove leaves the live view.
- **A chosen timeframe lists only devices that moved traffic in it** (v3.7.7), and each row's bar is that row's share of the window's total, so the bars of a table add up to the whole.
- A guest network's accelerated uploads are counted for its devices, not also as the router's own traffic (v3.7.7).
- The collector rewrites its live file ten times a second only while a page shows the live view, and the page stops polling while its browser tab is hidden (v3.8.2), so leaving the page open in a background tab costs nothing.

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
- **Top Devices and Top Talkers show 10, 20, 30 or 50 rows** (v3.3.8), chosen per table and remembered in the browser; the collector keeps 64 top-talker slots.
- **A busy connection table does not cost a CPU core (v3.3.6).** The collector paces its pass over the connection table by its own measured cost (about 3 % of one core, every 2 to 30 seconds) and logs a line when the pace changes; every rate uses the measured interval.
- In Access Point, repeater or media-bridge mode the collector is deliberately idle: it accounts from the connection tracking table, which a bridging box never populates. Since v3.2.0 the page says so and names the mode instead of staying blank.

### 4.8 Devices

**What it is.** The **Device Identity Manager**: one page that correlates everything the firmware otherwise scatters about a device — custom name, DHCP reservation, Gatekeeper access state, and live presence (leases, address table, Wi-Fi association, band, last seen, 24-hour traffic) — keyed on hardware address.

It is a **lens, not a second engine**. Every action writes to the same stores the rest of the firmware reads, and access states are enforced by Gatekeeper. Nothing here has its own private copy of anything.

**When to use it.** Naming devices, pinning addresses, checking who is online, spotting reservation problems, and changing a device's access without leaving the page.

#### 4.8.1 Naming

Click a name to rename it inline. **Your custom name wins everywhere** over whatever the device calls itself, and it propagates to every page — the client list, Gatekeeper, Traffic Analyzer, Connections, and the DHCP lease log.

There is one master name store behind that, deliberately, because there used not to be. Renames could appear to revert, or show the old name on some pages and the new one on others, and deleting a single offline client could wipe every custom name you had set. Those were real defects with a single cause — several parts of the firmware parsing the same store differently — and the fix was to make one store authoritative. Field devices with duplicate records left over from that period clean themselves up on the next reboot.

**Name and Hostname: one rule on every page (v3.8.0).**

| Label | Where it comes from | When it is empty |
|---|---|---|
| **Name** | The name you gave the device **on this page** (the one master list, `custom_clientlist`) | You have not named it |
| **Hostname** | The name the device sent when it asked for an address (DHCP option 12) | No name sent: the **maker** of its network card, from the MAC prefix, for a real MAC; the text `Private-Address` for a randomized (private) MAC |

- A page with **one** label (Gatekeeper, Wallguard, Encrypted DNS, Traffic Analyzer, Connections and the rest) shows
  **Name**, else **Hostname**. The **DHCP Leases** page (System Log) shows both columns; Name stays empty unless you named
  the device here.
- A **DHCP reservation's name** (the reservations on the LAN page) is the device's **DNS name**: what other devices reach it by, what
  `$client=` in Wallguard's Advanced rules can use. It is not a Name and is never shown as one; the reservation page
  labels it *DNS name*. Give the device a Name here to change what the pages show.
- Parental Controls and Wake on LAN keep their own entry names; they show this page's Name for the same MAC, and their
  own name only when the device has no Name.
- Changing a label changes only what is **shown**. Enforcement (Gatekeeper, Wallguard profiles, firewall rules) keys
  on the MAC or address, never on a label, so renaming a device never changes what applies to it.

#### 4.8.2 Pinning an address

**Pin IP** opens a pool-aware dialog. It recommends an address **outside** the DHCP pool, which keeps the pool free for new arrivals; the device moves to it at its next lease renewal rather than immediately. You can also keep the address it currently has, inside the pool.

**Widen pool** extends the DHCP range toward the usable subnet when the pool is tight.

**IPv6.** The IP column also shows a device's IPv6 address (its first global one, learned from the router's
neighbour table and from DHCPv6 leases), and a device that has only an IPv6 address is chipped *IPv6 only*
rather than *No lease*. **Pin IPv6** reserves a DHCPv6 address the same way: you give only the host part
(`::10`, or up to four hex groups), the router prepends whatever IPv6 prefix it currently holds, so the
reservation survives a prefix change from your provider, and the device is matched by its hardware address.
The reservation takes effect when the device next renews or reconnects; it rides along in a full backup.
Devices that do not run a DHCPv6 client (most Android, some IoT) keep choosing their own addresses and cannot
be pinned - that is the device, not the router.

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
- **After a restart (v3.8.0)** every device that still holds a DHCP lease is listed and named at once: the router keeps
  its lease lists in flash and puts them back when it starts (see *DHCP leases kept across a restart* in 4.26.3).

#### 4.8.5 Filtering and export

Filter chips: All, Online, Offline, Unnamed, Reserved, Randomized, Blocked. Search matches name, address or hardware address.

**Export list** saves the whole inventory as CSV, JSON or HTML, with an `ipv6` column beside the IPv4 one.

> **The export is unsanitised.** It contains every device name, hardware address and IP address on your network. It is meant for your own records. Do not attach it to a forum post or a bug report — unlike the diagnostic bundle (4.13), nothing in it is redacted.

#### 4.8.6 Limits and gotchas

- **A phone using a private (randomized) address reappears as a new device** each time it rotates, until you turn that feature off for your network on the phone. This is the single most common source of unexpected new entries here and in Gatekeeper.
- The reservation store is limited by NVRAM size; the ledger warns before you reach it.
- The router's own address can still appear as a row rather than being folded into a router bucket the way the Traffic Analyzer does it. Known, deferred, harmless.

### 4.9 Connections

**What it is.** A live **flow explorer** drawn from the Runner flow accelerator. **Quick Look** (the default) lists device name, local IP, remote IP:port, an internal/external badge, protocol and TCP state. **Advanced** shows, per flow, whether it is forwarded in hardware or by the CPU (with a real per-flow percentage split), egress queue and QoS class, DSCP, live rate, total bytes and true age; summary cards show how many flows are accelerated and the overall hardware-versus-CPU split; filters narrow to accelerated or CPU-path flows; a **Pause** control freezes the view. Polling (500 ms – 4 s) runs only while the page is open. The stock connection page no longer ships (v3.4.9); its address opens this one.

**Destination names.** Since v3.3.4 the Destination column shows a name over the address: a LAN destination by its
device name (the router's own addresses as *This router*), an external one by the name the device asked DNS for. The names
come from a small listener on the router that reads the DNS replies your devices receive as they pass - nothing is looked up,
nothing is logged, and the table it keeps (128 KB, in RAM) names only what the household resolved. A name stays on a row while
the address is listed and is forgotten when the flow is gone; a small *+N* marks an address that answered for several names
(a shared CDN host). The **Names** button in the header turns the listener off and removes the table. Devices using DNS over
HTTPS or TLS, and a wired device talking to a wired LAN resolver on the same switch, never get a name - the reply never passes
the router.

Switching **Names** off removes the table. Switching it back on runs a one-off reverse lookup of the addresses already in
flight, through the router's own resolver, so the column fills at once; those names are shown in italics because they are
what the address's owner registered rather than what the device asked for, and each is replaced the moment a real DNS
reply for that address is seen. The lookup runs only on that switch, never at boot.

**IPv6.** IPv6 connections are listed too, with addresses in brackets (`[2606:4700::6810:84e5]:443`) and
named from the same DNS listener (AAAA replies are kept alongside A records). They come from the kernel's
connection tracker rather than the flow accelerator, which does not report its IPv6 flows to the page, so an
IPv6 row shows an *IPv6* badge instead of Runner/CPU and is left out of the accelerated-share cards and
filters; rate, bytes, state and age behave as for IPv4. The device side of an IPv6 flow is recognised through
the router's neighbour table, so a flow neither end of which is a LAN device (transit through a tunnel, for
instance) is not shown.

**When to use it.** To see what a device is talking to right now, to confirm that bulk traffic is hardware-accelerated, or to understand why a WireGuard Policy Routing rule cost acceleration (you will see the affected flows on the CPU path).

**Gotchas.** "No active flows in the accelerator cache" means there is no traffic or the accelerator/QoS is off. Queue numbers are mostly zero under Hardware QoS (a single shaped queue) and richer under HW Classful.

<a id="410-wireless-quality-and-wifi-professional-all-bands"></a>
### 4.10 Wireless Quality and Wi-Fi Settings (all bands)

**Wireless Quality** (the Wireless tab) is a diagnostics page:

- **Radio State** for every band — channel, width, **Lock current channel / Unlock**. With the channel on Auto the radio re-picks channel and width on every boot and wireless restart; Lock pins the running channel through the supported path. Both Lock and Unlock restart that radio, dropping its clients for about 20 seconds, and warn first.
- **Channel Selection Constraints** — the decoded auto-select exclusion list and the territory/board branch actually in effect.
- **Channel Quality Capture** — an on-demand 1 Hz sample (undecodable energy, free airtime, PHY glitches) written to RAM, downloadable as CSV. Nothing keeps running afterwards.
- **Auto Scan** — sweeps a radio's channels *at the width it will actually run* (6 GHz in 320 MHz blocks, 5 GHz in 80 MHz blocks, 2.4 GHz as 20 MHz channels), ranks them by cleanliness, and **restores the original channel when it finishes**; only **Pin best** commits the winner (an owner decision from v2.5.4 — the page text still describes the earlier auto-pin behaviour in one place). Each candidate restarts the radio, so run it from a wired client or another band; DFS channels are deliberately not swept (each needs a 60-second listening period). Pinning takes that radio off automatic selection until you set it back to Auto. The report can be printed to PDF or downloaded as HTML with a spectrum plot.
- **Passive Channel Monitor** (`rchqd`, opt-in) watches only the current channel and flags *degrading — consider Auto Scan*; it never changes a channel. Degraded/recovered transitions are logged, edge-triggered and rate-limited; the threshold is tunable (`rchq_degraded`).

**Wireless › Settings** (v3.2.2) is the one tab that configures every radio setting a user can change; it replaces the stock General and Professional tabs, which redirect to it. It lays every radio side by side (it builds itself from the router's real radio list, so a four-radio GT-BE98 gets four columns) and applies once: only changed fields are written and all radios restart together (~10 s). Network name, security, Wi-Fi 6 and Wi-Fi 7 mode and Smart Connect are set on the Network menu, because on this hardware the main network is an SDN profile. Channel and bandwidth offer what the driver reports for each band; the wireless scheduler opens a 7×24 grid. A greyed control is locked by another setting: Legacy mode parks what stock parks (beamforming, modulation scheme, AMPDU RTS and RTS Threshold), WMM is a choice in Legacy only, Fragmentation Threshold is editable in Legacy only, MU-MIMO follows the OFDMA choice, the scheduler is held off while MLO is enabled, *Disable 802.11b* is the master for the 2.4 GHz preamble control, and a fixed channel parks the auto-channel options. From v3.2.3 a greyed control names its reason when you hover it. **AP Isolation** is not on this tab: on this build it is a per-network setting on the Network menu, with a choice of what it keeps apart: **Wi-Fi only** (the default: Wi-Fi clients cannot reach each other, wired devices stay reachable) or **Wi-Fi and LAN ports** (the LAN ports are kept apart too) (4.21.2, 4.21.3). Roaming assistant: -90 to -40 dBm, 0 = off. **Wireless Mode** (v3.2.1) is per radio with stock's option sets (2.4 GHz Auto / N only / Legacy; 5 GHz Auto / AX only / N-AC-AX mixed / Legacy; 6 GHz Auto / AX only; the firmware has no Wi-Fi 7-only mode). Every mode except Auto, N/AC/AX mixed and AX only switches Wi-Fi 6 and Wi-Fi 7 off on that band, and Apply asks first; applying an Auto or AX-capable mode restores them, which the firmware alone never did. The radio toggle refuses to switch a radio off while MLO is enabled, and switching a radio off asks for confirmation on an AiMesh router because the setting reaches the nodes. A value a rule forces is written at apply as a derived heal when the stored value disagrees.

**Gotchas.** Smart Connect excludes 6 GHz by default on some configurations (visible in the Smart Connect Rules table as "- -" columns, which is normal).

#### 4.10.1 Preamble puncturing: what it is

A Wi-Fi 7 radio can switch off one **slice** of a wide channel - a 20, 40 or 80 MHz segment excluded from transmission - and keep using the rest, instead of dropping the whole channel to a narrower width. It is for the dense case: a neighbour's 80 MHz network inside your 320 MHz block, where excluding that 80 keeps 240 MHz instead of falling to 160. It is not a cure for half the block being noisy; a cleaner channel is.

- **Where it works.** 5 and 6 GHz, Wi-Fi 7 on, 80 MHz or wider: a fixed width, or Auto bandwidth with **Minimum width on Auto** (4.10.9). 2.4 GHz runs at 20 or 40 MHz and cannot be punctured (the driver refuses any pattern there).
- **What the driver accepts** (measured on the RT-BE96U, driver 17.10.369.39012). Exactly one slice, never the primary: at 80 MHz one 20 that is not the primary; at 320 MHz one aligned 40 or 80 outside the primary 80; at 160 MHz the driver judges. Anything else is refused (`rc=211`) and nothing changes.
- **How it applies.** `wl eht dissubchan <bitmap>`, bit 0 = the lowest 20 MHz of the block. It takes effect live, with no radio restart; the beacon's EHT Operation element advertises it, and the driver narrows the HE Operation width by itself where the slice sits inside the 160 MHz that Wi-Fi 6 clients use. A wireless restart clears it; the router puts it back (4.10.2).
- **Stock firmware never calls it.** Broadcom's own dynamic puncturing (`punct_features`) is compiled out of this SDK, and nothing in wlconf, acsd2, hostapd or the OFDMA setting sets a pattern. Every slice on the air is Reaper's.

#### 4.10.2 The parts and how they connect

| Part | What it is | When it runs |
|---|---|---|
| **Applier** `/sbin/reaper_punct` | The only program that writes a pattern. Waits up to 60 s for the radio (radio up and one of its networks up), checks the shape, applies, reads back, records the result in `/tmp/reaper/reaper_punct.state`, and clears only a pattern it set itself. A second pass applies interference mitigation (4.10.10), recorded in `/tmp/reaper/reaper_wlmit.state`. | Boot, every wireless start, an Apply of the puncturing or mitigation rows, the rwatch tick (every 5 min) and on request from the controller. One run at a time. With every radio Off and nothing of ours on the air it issues no `wl` command. |
| **Controller** `rpunctd` | Dynamic mode's decision-maker: measures, decides, writes its choice to `/tmp/reaper/reaper_punct.dyn` and runs the applier. Never calls `wl eht dissubchan` itself. | Only while some radio is set to Dynamic; exits by itself when none is. Paused for the whole of a wireless restart and while the applier runs. Restarted by rwatch if it dies. |
| **Minimum width** `reaper_bwfloor` | Keeps the channel picker at 80 MHz or wider on Auto bandwidth, so puncturing stays possible (4.10.9). | While a radio has the floor set; a 15 s watcher. |
| **rwatch** | Backstop: re-runs the applier every 5 minutes (which also moves a Follow pattern after a channel change, since acsd2 has no change hook) and restarts a dead controller. | Every 5 min, only when puncturing or mitigation is set. |

#### 4.10.3 The four modes and what each puts in effect

| Mode | Who picks the slice | What runs | Channel needed | After a channel change |
|---|---|---|---|---|
| **Off** (default) | - | Nothing. A slice of ours still on the air is cleared once. | - | - |
| **Fixed channel** | You, for one exact chanspec | Applier only | A fixed channel at 80 MHz or wider | Not applied ("different channel or width") until the radio is back on that chanspec |
| **Follow channel** | You, by position ("upper 80 MHz") for a width | Applier only | That width; works on Auto channel | Re-applied wherever that position is legal at the same width; skipped at another width |
| **Dynamic** | The controller | Controller + applier | 80 MHz or wider; works on Auto | The controller forgets its slice and its statistics and starts afresh on the new channel |

Stored in one key, `wlN_punct` (8.2). An Apply that changes only puncturing or mitigation rows runs the applier directly - no wireless restart, no client dropped.

#### 4.10.4 Dynamic: sensitivity presets

The controller switches a slice off only when all of these hold: the slice has stayed above the **trigger** for the **hold**, the shape is legal, the expected capacity gain clears the **minimum gain**, and the **change interval** since the last change has passed. It puts a slice back after the slice has read below the **restore** level for the **clean hold**. Temporary interference never changes anything.

| | Conservative (default) | Balanced | Aggressive |
|---|---|---|---|
| Trigger (busy on a slice) | 80 % | 65 % | 50 % |
| Held for | 60 s | 30 s | 15 s |
| Minimum capacity gain | 20 % | 15 % | 10 % |
| Change interval | 300 s | 180 s | 60 s |
| Restore below / clean hold | 35 % / 240 s | 35 % / 120 s | 30 % / 60 s |
| Evaluation step | 60 s | 45 s | 30 s |
| Scan cooldown | 900 s | 600 s | 300 s |
| PHY impairment trigger | 35 % | 25 % | 20 % |

**Minimum gain** and **hold** can be overridden on the Settings tab (5-50 %, 60-3600 s; blank = the preset). The **score** of a pattern is the kept width times the airtime left free on it, with a punctured transmission counted at 97 % efficiency; the gain is the score change against the current pattern. **Self-correction:** a restore that does not hold doubles the next clean hold (up to eight times); a change that disturbed clients (4.10.7) triples the clean hold, change interval and scan cooldown; three refused applies, or two disturbing changes, put the radio in **fallback**, where it makes no change for 30 minutes; a refused slice is not offered again on that channel; no valid measurement for 60 s is **error**, and the current pattern is held.

#### 4.10.5 Dynamic: monitoring sources

What the radio's counters can see depends on the width. They resolve the primary 20, the other 20 of the primary 40, the other 40 of the primary 80 and the other 80 of the primary 160 - nothing finer, and nothing for the far half of a 320. A candidate the counters cannot resolve needs a **confirmation scan**: a passive listen on that candidate's own 20 MHz channels (`escanresults -t passive`, about a second off-channel for four channels, measured), read back through the per-channel statistics.

| Source | Sees | Confirmation scan | Restore of a slice |
|---|---|---|---|
| **Passive telemetry** | The counters only. At 320 MHz: the secondary 80 of the primary 160 only. At 160 MHz the legal slices are finer than the counters, so it can never act there. | Never; an unresolved candidate logs "needs a confirmation scan" | By the counters |
| **Passive + idle confirmation** | Counters, plus scans | Only while your own airtime is under **10 %**, at most once per scan cooldown | Only after a fresh scan of the switched-off channels agrees they are clean |
| **Active confirmation** | Counters, plus scans | Whenever needed, but never while your own airtime is above **30 %** (the scan ceiling), at most once per scan cooldown | As idle |

A scan also lists the networks heard on those channels - channel, width and signal only, no names or addresses - and each channel's noise floor and PHY error counts. A neighbour's home channels take the busy the counters saw (weighted by signal: full at -70 dBm or stronger, 70 % to -80, 40 % to -88, none below), and a channel whose noise or errors are high counts as busy even when carrier sense reads low. A scan reading stays usable for 5 minutes and stands in for the live counters for 2.5. For a busy far half at 320 MHz, the idle source is the setting that resolves it; Aggressive does not.

#### 4.10.6 What the controller measures, and what it costs

| Input | How | How often | Disturbs clients? |
|---|---|---|---|
| **Carrier-sense window** | A timed `chanim_stats` window armed and read through the driver (`wl_iovar_getbuf`, no process started): busy, own airtime and the per-sub-band counters, as permille. An empty or short window is discarded. | 4 s window every 10 s, all Dynamic radios armed in the same second | No - it never goes off-channel and never resets the driver's own accumulators (acsd2 reads those) |
| **PHY figures** | `wl chanim_stats`: glitches and bad PLCP headers per second, background noise in dBm. Impairment = noise above this radio's own quiet baseline (more than 5 dB, 4.5 % per dB) or glitches + bad PLCP above 50/s. The baseline follows a quieter reading at once and a louder one over about an hour, and starts over on a channel change or a mitigation change. | Each tick, after the window closes | No |
| **Station table** | `wl bs_data -noreset` on the radio and its networks: per-client acked packets, retries, rate and the width each client used. `-noreset` is essential - a plain read clears the table that band steering (bsd) also reads. | Every 30 s; every 10 s during a 120 s proof | No |
| **Confirmation scan** | 4.10.5 | At most once per scan cooldown, gated by source | About a second off-channel; see 4.10.7 |

The PHY trigger can only ask for a scan of the channels a slice could be taken from; it never applies anything by itself. Client widths break ties: when two slices qualify, the one that does not cut into the width narrower clients use is preferred. 120 s after each change, every client with traffic before and after is compared: **worse** = rate down a quarter and retries up 5 points. If at least two were compared, at least two and at least half got worse, and worse outnumber better, the change comes off - an applied slice is not retried on that channel, a restore waits twice as long next time.

Cost per Dynamic radio: one driver request pair and one `wl` call every 10 s, one station-table read per network every 30 s. Nothing runs on a radio that is not Dynamic.

#### 4.10.7 What keeps clients connected

- **Nothing here restarts a radio.** Slices and mitigation apply live; the controller never runs `restart_wireless`.
- **No radio access while wireless restarts.** The controller reads nothing while `wlready` is 0 or the applier is waiting, and rc stops it at the top of `restart_wireless` and starts it after.
- **Scans are short, rare and load-gated** (4.10.5): passive, only the candidate's own channels, cooldown-limited, never above 10 % (idle) or 30 % (Active) own airtime.
- **A scan that loses a client stops scanning.** If the radio's client count drops during a confirmation scan, scans are off on that radio (Passive from then) until the setting is saved again or the controller restarts.
- **A change that disturbs clients is undone.** A channel-switch announcement, a moved chanspec, two or more clients lost, or every client lost marks an apply as disruptive: the slice is taken off at once and the controller slows down.
- **Measured.** No client was disconnected by a set or a clear on the RT-BE96U; the change rides the next beacon.

#### 4.10.8 What each client sees

A client's width is anchored on the radio's primary channel: an 80 MHz client on a 160 or 320 MHz channel lives on the primary 80, a 160 MHz client on the primary 160. The driver accepts no slice inside the primary 80 at 320 MHz (measured) and, by the same rule, at 160 MHz (driver-judged), so at those widths an 80 MHz client is untouched by any slice. A 160 MHz client is affected only when the slice falls inside its 160 (at 320 MHz: the secondary 80 of the primary 160): a Wi-Fi 7 client skips the slice and keeps the rest of its width; a Wi-Fi 6 client, which cannot understand puncturing, is narrowed by the driver to the widest width free of the slice (measured at 320 MHz: HE Operation went from 160 to 80 for a slice in the secondary 80). A slice in the far half of a 320 MHz channel touches nothing a Wi-Fi 6 client can use. Only an 80 MHz channel puts a slice inside every client's width, because there the one legal slice is a 20 in the primary 80: Wi-Fi 7 clients keep 60 MHz, others are told the 40 or 20 MHz the slice leaves whole. The controller scores the channel's airtime, not the widths of the clients on it.

#### 4.10.9 Minimum width on Auto

With Channel bandwidth on Auto the channel picker (acsd2) chooses the width as well as the channel, and narrows the whole channel to 40 or 20 MHz when it judges part of a wide one busy - exactly the case puncturing exists for. The switch (`wlN_bwfloor`, 5 and 6 GHz) keeps the picker at 80 MHz or wider: **80/160 MHz** on 5 GHz, **80/160/320 MHz** on 6 GHz. Each client still uses what it supports within the width the radio is on, and 160 MHz on 5 GHz still needs Enable 160 MHz.

- **How.** The radio's 20 and 40 MHz chanspecs are added to the picker's exclusion list (`wlN_acs_excl_chans`, the list Channel Selection Constraints decodes), only those not already there, and recorded on `/jffs` so exactly those - never a stock DFS or user exclusion - come out again. Nothing is added when no wide channel would be left (acsd2 would otherwise discard the whole list).
- **Radar escape.** A 15 s watcher lifts the floor for that radio when it stays below the floor for 120 s or off the air for 180 s outside a DFS listening period: its entries come out and acsd2 restarts so the radio can use any width. The lift lasts 30 minutes (the DFS non-occupancy period), doubling on a repeat within 2 hours, 4 hours at most, then the floor re-arms by itself.
- **Re-arm without a channel move.** When the floor re-arms while the radio is already at 80 MHz or wider, acsd2 is not restarted - a restart makes it pick the channel again from scratch, which moves clients for nothing. The watcher marks the restart as pending (`note=picker-pending`) and restarts acsd2 only if the radio later narrows. When the radio is narrow at re-arm, acsd2 restarts at once.
- **Needs** Auto channel and Auto bandwidth; the cell says why it is locked otherwise. With the floor on, the puncturing rows unlock on Auto bandwidth (Follow lists the slices of the width the radio is on now; Dynamic follows the radio); without it they stay locked, because the picker could narrow below 80 MHz.

#### 4.10.10 Interference mitigation (all bands)

The radio's receiver has its own interference defences, run by the driver per frame (`wl interference`, a bit mask). They are **on by default on every radio**: mode **75** = glitch-based receiver desense (1) + hardware-ACI packet-gain limit (2) + preemption (8) + hardware OBSS detection and mitigation (64), as read on the RT-BE96U. The Settings row **Interference mitigation** (`wlN_rmit`) offers:

- **Driver default** (default, recommended) - Reaper writes nothing; the radio runs its own mode.
- **Add hardware ACI mitigation** - the driver's mode plus bit 16 (75 becomes 91): the receiver also limits its gain when a strong signal sits on a neighbouring channel.

How it is applied: the applier's second pass (4.10.2) reads the driver's mode, records it as the base, sets base + 16 and reads it back; it re-applies after every wireless start and on the rwatch tick, and going back to Driver default writes the recorded base back - only a mode Reaper set is ever undone. It applies live on any band, with no channel change and no radio restart. A change restarts the controller's noise baseline and PHY average (twice: at once and 30 s later), because desense moves those figures by design. Results: applied / the driver already runs it / refused / waiting.

**Measured** on the RT-BE96U at 2.4 GHz under microwave interference, with a phone held on 2.4 GHz and streaming: with mode 91 the radio counted about 30 % fewer glitches, but the phone's retries rose (to about 79 % of transmissions in one run) and its rate fell to 16-52 Mbit/s, against a steady 206-229 Mbit/s with the driver's own mode. The radio's noise reading also rose from about -92 to -76 dBm for one 91 interval, which other 91 intervals did not show. A lower glitch count is the receiver hearing less, not clients doing better - keep Driver default unless a specific problem points at adjacent-channel interference, and judge the change by client speed, not by the glitch figure.

#### 4.10.11 Driver functions Reaper leaves alone

| Function | What it does | Why it is not a setting |
|---|---|---|
| **Dynamic bandwidth switch** (`obss_dyn_bw`, default 0) | Narrows the whole network when neighbours occupy a secondary channel | Measured: within a minute of enabling it, the driver channel-switched a 5 GHz network from 40/160 to 20 MHz and it stayed narrow after the switch was turned off. That overrides both the minimum width and puncturing, and with the floor on it led to two channel moves that disconnected clients. |
| **Spatial reuse** (OBSS-PD, `wlN_bss_sr` 1 = on for HE frames) | Lets the radio transmit over distant overlapping networks | Already on by default, and the stock watchdog re-asserts the stored setting within seconds (a live change was reverted in 5-10 s). No measured benefit to expose. |
| **EDCRS_HI channel escape** (`edcrs_hi_event_mode` -1 = automatic) | Changes channel on sustained high energy | The driver enables it by band and regulation: on the RT-BE96U it is active on 6 GHz (events and an in-driver channel change) and off on 2.4 and 5 GHz. A regulatory function - never overridden. acsd2 does not manage the 6 GHz radio, so an unexplained 6 GHz channel move can be this. The diagnostics report shows it. |
| **Energy-detect threshold** (`phy_ed_thresh`) | The level at which the radio treats a channel as busy | Regulatory (EU adaptivity). Read for diagnostics only. |

#### 4.10.12 Where to look

- **Settings cell** - the applier's result for puncturing (Active on the radio now / refused / waiting / different channel or width), the controller's state in Dynamic, the floor's state (Holding / Lifted / Not active / Not applied), and the mitigation result.
- **Wireless › Wireless Quality** - the Dynamic puncturing card: busy per slice, the current candidate and how long it has been bad, the last change and why, the last scan's channels and the networks heard.
- **System log** - `rpunctd` (one line per decision, saying why; scans with their clients-before/after; PHY impairment edges with the raw figures; client evidence after a change), `reaper_punct` (a slice or mitigation mode set, cleared or refused), `reaper_bwfloor` (lifts, re-arms, a pending picker restart).
- **Diagnostics report, section 7** per radio: `interference: mode= setting= applier= edcrs= sr=`, `puncturing: setting= live= applier=`, `dynamic puncturing:` (the controller's state line) and `min width:`.
- **State files** - `/tmp/reaper/reaper_punct.state`, `/tmp/reaper/reaper_wlmit.state`, `/tmp/reaper/reaper_punct.dyn.state` and `.json`, `/tmp/reaper_bwfloor/state`.

A wireless restart clears the driver's pattern and mode; the router re-applies both. The controller then resumes with its slice if the channel is the one it chose it on, and forgets it after a channel move. Every ten seconds it checks the applier's record against its own: a slice that fell off the radio is forgotten, and one it did not choose is taken off.

#### 4.10.13 AiMesh backhaul parking

**AiMesh backhaul parking (v3.0.8, off by default).** Even with no mesh node paired, AiMesh keeps its
hidden backhaul network on the air on every band: the primary BSS of each radio carries a hashed
SSID, beacons like any other network, and accepts WPA connections with a key derived inside the
AiMesh components rather than chosen by you. On 2.4 and 5 GHz each network beacons on its own, so
the idle carrier is a full beacon stream (about two percent of 2.4 GHz airtime, the band most IoT
devices use). On 6 GHz the co-located networks share one beacon and the primary is the one that
transmits it, so there is nothing to save there.

Turn parking on and the 2.4 and 5 GHz carriers are taken off the air whenever this router is the
AiMesh primary, no node is paired, and no search or onboarding is running. The moment you press
**Search** or **Add node** on the AiMesh page they come back within five seconds, so a node can
find and join them; if the search ends without a node, they park again. A paired mesh is never
parked and a radio you have switched off is never touched. The daemon never parks 6 GHz by hand,
but with MLO enabled the three carriers are one link set: parking one drops them all, and the
daemon logs the linked drops and raises the whole set on release. Every park and
release is written to the system log with the interface, the band and the reason
(`amaspark: parked wl1 (5 GHz backhaul carrier): no AiMesh node is paired and no search or onboarding
is running`), and the Wireless page shows the last state. Your own networks are unaffected: the
virtual networks on each band keep serving while the carriers are down, which was verified on the
RT-BE96U with MLO on and clients attached on all three bands. The gain is mostly hygiene, a listener fewer and a quieter channel,
rather than speed.

**DTIM Interval defaults to 1.** A router with no DTIM value set, such as a new box or one just factory reset, uses
1 on every radio: a sleeping client wakes at every beacon, so phones, watches and smart-home devices answer at once and
multicast (casting, AirPlay, discovery) is never held back, for a small battery cost. A firmware update never changes
the value you already have. Raise it on the Wi-Fi Settings page if you prefer longer client sleeps (Apple recommends 3).

<a id="411-long-term-storage-data-export-and-the-reaper-settings-backup"></a>
### 4.11 Long-Term Storage and Data Export

These share the **Storage** page under System Log.

**Long-Term Storage** — choose the durable **Location** (RAM only / Internal (JFFS) / USB storage) and toggle each **dataset** (device history and action audit, traffic history, rwatch incident dumps, channel-quality history, syslog mirror; Warden is locked to JFFS). Four more rows: **Wallguard block lists** (USB only; the lists move off RAM and come back from the volume after a restart; the block table stays in RAM, see 4.3.3.10), **Wallguard blocked lookups** and **Dreadwatch blocked lookups** (every blocked lookup, time, device and name, appended each time the feature collects its records; `<store>/wallguard/blocked.log` and `<store>/dreadwatch/blocked.log`, rolled to `.1` past 16 MB on USB or 2 MB on JFFS), and **Encrypted DNS activity** (one line per watchdog tick while Encrypted DNS or its block is on: devices connected, lookups answered and refused by the router's DoT server, outside DoT and DoH refused, addresses on the block list; `<store>/ednshist.log`, rolled to `.1` past 4 MB; the router's DoT server still never records a lookup). **Firewall log** (v3.7.5; USB store only): the firewall log collector (4.1.12) also writes each line to `<store>/fwlog/YYYY-MM-DD.log`, one file a day, keeping up to 30 days or 256 MB (the oldest day goes first). It is ticked by default on a new or reset router; on an upgraded router tick it here. The RAM ring the Firewall view reads (2.12) is kept either way. The **Encrypted DNS blocked-address list** row is locked to JFFS like Warden's: the firewall loads it at boot, before any USB volume is mounted. Blocked-lookup history shows which device asked for which blocked name and when; on USB anyone with access to the volume's file share can read it (the page says so). Every write into the store (and Wallguard's read of its stored lists) goes through `/usr/sbin/rstore`, which never follows a link: a USB store is a volume other people can write - in guest share mode the firmware maps share guests to the admin account - so a file or folder they plant there cannot redirect the router's writes onto its own files. Wallguard checks a stored list's SHA-256 on a copy in RAM and builds from that copy. The table shows written size, size cap and **Collecting since** per dataset; the health line reports free space and falls back to RAM if no writable USB volume is attached. Once a durable location is collecting, each device gains a timeline (first seen, renames, reservations, offline spans, cumulative traffic). See 2.6 for the filesystem and USB guidance. Policy (rules and lists) is not a dataset here: the Reaper lists live on `/jffs` (2.4).

**Data export** (mode control here; destination on **Administration → Data Export**) — per-device connection-health metrics (round-trip latency, jitter, loss, TCP connection count and state, throughput, online state). Modes: **Off** (nothing retained or sent), **Store only** (history on the router, nothing leaves), **Store + Export**, **Export only**. Any mode other than Off turns on the **Health probe**, which can also be enabled on its own for the live view and **Preview payload**. Targets: Splunk HEC, Datadog, Dynatrace, Elastic, generic HTTP/JSON, OpenTelemetry, TLS syslog (push), or a **Prometheus** OpenMetrics scrape endpoint (pull, bearer token required). TLS verification is on by default; the API token is stored masked and kept out of process lists and logs; an option hashes device MACs before they leave. **Test connection** and **Preview payload** show exactly what will go out. The probe is light enough to leave on (spread across ticks, at most 16 pings per tick, skipped while the link is saturated; default interval 60 s); the exporter refuses to push a snapshot older than three minutes, so a crashed collector never masquerades as live data. Not included by choice: wireless RSSI/PHY metrics and TCP retransmit counts.

How to set up an export:

1. **Administration → Data Export**: choose the target (Splunk HEC, Datadog, Dynatrace, Elastic, generic HTTP/JSON, OpenTelemetry, TLS syslog or Prometheus), enter its address and its API token, and leave TLS verification on unless the collector uses a private certificate you trust. Tick *hash device MACs* if the collector is not yours alone.
2. Press **Test connection**: it sends one request and shows the collector's answer. Fix the address or token until it succeeds.
3. Press **Preview payload** to see exactly what one push contains.
4. On **System Log → Storage**, set the Data export mode to **Store + Export** (or **Export only**) and apply. For Prometheus, point your scraper at the endpoint the page shows, with the bearer token; nothing is pushed.

**Reaper settings backup** — moved. Export and import now live on **Administration → Backup & Restore**, alongside the full `.rbk` backup, so every backup is in one place (2.5).

### 4.12 USB Disks

The last tab of **USB Application** (v3.4.9; it was the first): each attached disk with its partitions, usage and a badge on the one that **holds the long-term store**; a **health scan** (a real `e2fsck` on ext4, with a pass/fail verdict and the check log; the result stays on screen); **Format** with a volume label and a filesystem selector (ext4 / ext3 / ext2 / FAT32 / NTFS / HFS+, with a one-line hint per choice — see 2.6); and **Safely remove** (eject), which now requires the anti-forgery token. Formatting permanently erases the disk and asks first. Formatting logs to `/tmp/disk_format/<dev>.log`. The format confirmation dialog is still stock-styled (backlog, cosmetic). Samba shares are named for their folder (`reaper`), with "(at DISK)" added only when two disks hold a folder of the same name. Disks larger than 2 TB show their real size (v3.7.4; they read 0 B before). A FAT or HFS+ partition whose check crashes or hangs is logged once and not checked again, and a damaged or crafted FAT or HFS+ volume that would crash the check is refused (v3.8.2).

**USB 3 write-speed levers (v3.7.0, advanced).** On BCM4912 / BCM4916 models five USB controller parameters can be set from the `reaper_usb3_*` settings (`credits`, `dcm`, `parkoff`, `rdattr`, `txthr_burst` / `txthr_cnt`) for A/B tests of the write speed. They have no page and are unset at factory; nothing changes unless one is set over SSH (`nvram set reaper_usb3_dcm=1; nvram commit`, then reboot). Section 3c of the diagnostics report lists any that are set. If a disk misbehaves after setting one, unset it (`nvram unset`) and reboot.

### 4.13 Diagnostics

**Administration → Diagnostics**: the sanitized report described in 2.10. The page lists what is collected and what is removed or masked, shows what the top of the report (the ledger) looks like, and has one **Download Report** button. The report takes 20–30 seconds and downloads by itself; since v3.3.3 the rest of the interface stays usable meanwhile. The FINDINGS block at the top is the first thing to read when something is wrong (5, item 9).

**How to use it when you need help.**

1. Reproduce the problem first, or take the report soon after it happened: the report reads the live state and the recent log, so a report from the next morning may no longer show it.
2. **Administration → Diagnostics → Download Report** (or `reaper_diag` over SSH; the file lands in `/tmp`).
3. Read the **FINDINGS** block: each line names a state that needs action and the section to look in. Many problems end here.
4. Check the **ledger** at the top says the report is clean. If it says *review before sharing*, search the file for what it counts before posting it.
5. Attach the file to your GitHub issue with the model, the variant (MCP / noMCP) and what you did just before the problem (2.14). The sections a helper usually needs: 4b - 4d for guest networks, 5 for the internet connection, 7 for Wi-Fi, 14 - 14h for the firewall layers, Bastion and Encrypted DNS, 19 for the log.

### 4.14 Firmware

**Administration → Firmware Upgrade** is a Reaper page:

- **Installed Firmware** — model, variant (Standard / AI Advisor), Reaper version, base build.
- **Updates** — **Check for Update**, the release notes inline, **Download and Install** (verified end-to-end, 2.11), **Scheduled Check** with **Check at** hour, and (v3.1.0) **Beta Channel**: off by default; on, the check also reads the Dev branch's beta line and offers a beta only when this router already runs the newest stable release and the beta's number is higher than that stable's — a beta with the stable's own number is never offered. A beta offer is labelled **Beta** here and on the dashboard badge, and its release note opens with the beta warning. The previous firmware stays in the standby partition either way.
- **Manual Upload** — with a real progress bar; it warns if the file does not look like an image for this model or variant. The page gives a good image up to ~5 minutes to be verified before calling it rejected. If the router **refuses** the image - it was not written (too large for the flash slot, or a damaged file) or it failed validation (not an image for this router) - the page says so at once instead of waiting for a reboot, the system log records the reason (`firmware upgrade FAILED`), and the page shows that last refusal on every later visit until an upgrade succeeds. The router restarts on its current firmware in that case; nothing is lost. Behind the scenes the build itself now refuses to produce an image whose root filesystem would not fit this model's flash slot.
- **Mesh Nodes** (at the bottom) — every AiMesh node with name, address, reported firmware version and online state; **Update** opens that node's own firmware page in a new tab where you flash it natively (the image is never relayed through this router), and **Update all nodes** pushes the current firmware the way the stock AiMesh upgrade does. Update one node at a time and let it come back.

The flashing overlay shows download, upload and flash phases with an elapsed-time heartbeat. It has no Cancel button: neither an upload nor a download from the update server can be stopped cleanly once it has started, and a button that did nothing was removed in v3.3.4. A **Close** button appears on any error. After the flash the page waits for the router and returns you to sign-in.

<a id="414a-resolver-health-check-administration--failover-v311"></a>
### 4.14a Resolver health check (Administration → DNS Failover, v3.1.1)

dnsmasq, the router's resolver, keeps no memory of an upstream that stopped answering. In strict order it
tries the first server again for every new name and only a client's retransmission moves the query to the
next one, so an outage of a LAN resolver such as AdGuard or Pi-hole costs a client timeout per uncached
name, and a client that lists the router as its second DNS server can need three attempts before the
router's own second server answers. The **Reaper resolver health check** lives on the **DNS Failover** tab
of the Administration group (between System and Firmware Upgrade) together with the six switches of the
**DNSMASQ** row below, and watches **one DNS server you name** with a real query every 10 seconds by
default (off at factory); the tab's
state strip shows Watch / Fail over / Restore and lights the middle step while the server is down.
The server can
be an IPv4 address or, while IPv6 is enabled on the router, an IPv6 address: the probe goes out over the
matching family, and the server is found in the router's list whatever spelling the list uses for it. An
IPv6 server named while IPv6 is off is refused by the page, and a daemon that finds one that way (IPv6
switched off later) idles and says so once in the system log. After the number
of **misses** you set it moves that server to the **end of the router's upstream list** and reloads
dnsmasq, so the first server asked is one that answers; after the number of **hits** you set it puts the
server back first. A server reachable over both families (its IPv6 address in the second field) is probed
over both every time: its IPv6 line is kept directly behind its IPv4 line whatever order the firmware wrote,
a face that stops answering is moved behind the other servers on its own while the live face keeps the
server's place, and the DNS intercept's gate closes for that family alone; the log names the face that
moved and the moment it is back. While IPv6 is disabled on the router the IPv6 address is left alone
entirely. You choose the interval, the reply timeout, the name queried, and whether any reply
counts as alive or only a real answer. The **Status** line shows the live state and how long it has held;
every switch is written to the system log with the reason. The server has to be in the router's own DNS
list (the WAN DNS servers, or a VPN client's) for the move to have any effect, and clients that talk to
the LAN resolver directly still pay one retry against it before they reach the router.

**Upstream order** on the same tab turns on dnsmasq's strict order: the router asks its DNS servers in
the listed order and moves on only when one does not answer, instead of its default of probing all of
them every 50 queries and settling on the fastest, which sends a share of every query past a LAN filter.
Pair the two: strict order keeps the LAN resolver first while it is healthy, the health check supplies
the memory of a dead one that strict order lacks.

**Device names across networks**, the next switch on this tab, has its own section: 4.14b.

One more switch sits beneath, for the layout where **clients are handed the router alone as their DNS**
and the router forwards to the LAN filter, which makes the failover complete (no client ever retries)
and catches devices with a hard-coded DNS when paired with the port-53 intercept.
**Router DNS cache** off turns the router into a pure forwarder: a per-client decision is never served
from the router's cache to a different client, and the filter sees every lookup, as it does when clients
talk to it directly. The filter keeps its own cache.

**The DNSMASQ row at a glance.** Every switch on it is off at factory from v3.4.2; an upgrade keeps the
values a router already has.

| Switch | On means | Key |
|---|---|---|
| Upstream order | dnsmasq strict order (above) | `reaper_dns_strict` |
| Router DNS cache | the switch reads *Do not cache*: on = no cache (above) | `reaper_dns_nocache` |
| Device names across networks | reverse lookups between the main LAN and each VLAN (4.14b) | `reaper_dns_revshare` |
| IPv6 device names | IPv6 addresses named from the DHCPv4 name (4.14b) | `reaper_dns_v6names` |
| DNS-over-TLS order | DNS Privacy servers used in the listed order (below) | `reaper_dot_strict` |
| LAN name resolution check | the dashboard reports when LAN devices cannot resolve (below) | `reaper_landns_enable` |

**DNS-over-TLS order.** With DNS Privacy (DNS-over-TLS) on, the router normally rotates between its
DoT servers so they share the traffic. This switch uses them in the listed order instead and keeps the
rest in reserve, so a filtering DoT server you put first sees every query while it answers. It does
nothing while DNS Privacy is off, and the page says so.

**The router's own lookups under DNS-over-TLS (2026-11-10).** With DNS-over-TLS on, the router's own lookups (time sync, DDNS, list downloads, the update check) go through the router's resolver and leave encrypted, as a device's do. Under the Strict profile nothing falls back to plain DNS; under Opportunistic the WAN DNS servers stay behind it as the fallback. Until the clock is set after a boot the lookups are plain, because a certificate cannot be checked without the time. With DNS-over-TLS on, the health check sends no plain lookup either (below). The health check's daemon also runs the automatic fallback of the upstream DNS-over-TLS leg, whether or not the check is switched on (4.3.4.5); if the daemon is not running in router mode, the `rwatch` watchdog starts it again on its next tick (after the 5-minute boot grace).

**The health check under DNS-over-TLS (from the image after v3.7.5).** While DNS-over-TLS is on (the same test the router's own lookups use: the switch on the DNS page, router mode, and a server with an address), the check never asks on port 53. If the watched server is one of your DNS-over-TLS servers (by either of its addresses), it is asked over DNS-over-TLS on that server's port, and its certificate is checked against the server's name when the DNS page gives one (as the router's DNS-over-TLS forwarder checks it); it gets three times the timeout for the encrypted connection. If the watched server is not one of them, the check asks the router's DNS-over-TLS forwarder instead, over the router's loopback, so it still sees whether encrypted lookups work. In both cases it **moves nothing**: under DNS-over-TLS the router's DNS list holds the forwarder alone, and the forwarder uses its other servers by itself. The status line says *Answering over DNS-over-TLS* or *NOT answering over DNS-over-TLS*, a note under it says which of the two ways is in use, and the log says so when DNS-over-TLS is switched on or off (`DNS Health Check: DNS-over-TLS is on - ...`). Until the clock is set after a boot no certificate can be judged, so misses are not counted (`HOLD`). A failover made on port 53 before DNS-over-TLS came on is undone at once. The diagnostics report names the probe in section 5 (`health probe`).

**LAN name resolution check (v3.4.0).** The WAN can hold an address while LAN devices cannot resolve a
single name (a dead LAN filter, a broken upstream list). With this switch on (off at factory from v3.4.2), once a minute while the WAN
is up the router asks its own DNS service, the way a LAN device would, for its own name and for a fresh
random name under the domain you set (empty = the router's network-monitoring name, so no cache can
answer it; that domain's own DNS servers see these lookups). Two failures in a row turn the dashboard's
Internet status **amber**, and the tooltip on the card and the header's WAN pill says why, for how long
and which servers stayed silent; the system log names them under `rdnshc`. It only reports: nothing is
moved, reloaded or restarted. The diagnostics report shows it in section 5. The status word in the tooltip and on the DNS Failover page is **Active** (names resolve), **Inactive** (the check is switched off) or **Fault** (two checks in a row failed); it read *working*, *check switched off* and *FAILING* up to v3.7.5.

### 4.14b Device names across networks (Administration → DNS Failover)

**What it does.** The router runs one resolver for the main LAN and one for each VLAN (each network you
create in the Network editor). Each knows the names of only its own devices: the host name a device sent
when it took its address over DHCP. Without help, a reverse lookup (address to name) for a device on
another network fails. This switch connects them, in both directions:

- the main LAN's resolver passes a lookup for a VLAN address to that VLAN's resolver;
- each VLAN's resolver passes a lookup for a main-LAN address to the main LAN's resolver.

The point is a DNS filter that lives on a VLAN. AdGuard Home on VLAN 52 asks its gateway who
192.168.50.97 is and gets the PC's name back, so its query log and per-client view show names.

**What is shared, and what never is.**

| Network | Shares names with the main LAN |
|---|---|
| Main LAN | yes, with every eligible VLAN |
| A VLAN you created (Customized, Kids, IoT, Employee, VPN, MLO profiles) | yes |
| Guest or Portal profile, or any network with a captive portal | never, either way |
| One VLAN with another VLAN | never |

Anyone on a shared network can list the device names of the other side by asking for each address in
turn. That is why guest-type networks are left out. Turn the switch off to keep every network's names to
itself.

**Turning it on or off.** Administration → DNS Failover → **Device names across networks**. It is off at
factory from v3.4.2 (earlier builds turned it on by default; an upgrade keeps the stored value). Changing it restarts the router's resolvers, a pause of about a second. Adding, removing,
readdressing or retyping a network restarts them once by itself, so the new network is covered without a
reboot. The system log says `networks changed - restarting the resolvers so each one can name the others'
devices` when that happens. The switch does nothing when **Forward local domain queries to upstream DNS**
(WAN → Internet Connection → WAN DNS Setting) is on, because the router then sends private reverse lookups upstream by your choice.

**Using it with a DNS filter on a VLAN.** Point the filter's reverse lookups at its own gateway, the
VLAN's router address. The router does the rest.

- *AdGuard Home:* Settings → DNS settings → **Private reverse DNS servers** = the VLAN gateway, for example
  `10.20.0.1`. Tick **Use private reverse DNS resolvers**. One address is enough; do not list the main
  LAN's router address, because AdGuard on a VLAN cannot reach that resolver directly.
- *Pi-hole:* Settings → DNS → **Conditional forwarding**: local network in CIDR = the network you want
  names for (for example `192.168.50.0/24`), router IP = the VLAN gateway (`10.20.0.1`).

Devices on the main LAN need nothing: they ask the router as always.

**Checking it.** From a computer on either network:

```
nslookup 192.168.50.97 10.20.0.1      # a main-LAN address, asked of the VLAN gateway
nslookup 10.20.0.98 192.168.50.1      # a VLAN address, asked of the main router address
```

Both should return a name. On the router (SSH), the lines the firmware wrote:

```
grep rev-server /etc/dnsmasq.conf /etc/dnsmasq-*.conf
```

The main file lists each eligible VLAN, each VLAN file lists the main LAN, and no file lists its own
network.

**What stays on the router, and what does not.** A reverse lookup for a private IPv4 address never
leaves the router. The lines the firmware writes name only the router's own addresses, so the question
goes from one resolver to the other inside the router. Any private range that is not one of your networks
is answered "no such name" on the spot (dnsmasq's `bogus-priv`). A filter such as AdGuard Home sends
private reverse lookups only to its private reverse server, the VLAN gateway, never upstream. Two cases
differ:

- **Forward local domain queries to upstream DNS** (WAN → Internet Connection → WAN DNS Setting) turns
  `bogus-priv` off and sends private reverse lookups to your upstream DNS, as stock firmware does. This
  feature then stands aside. Leave that setting off to keep these lookups at home.
- **IPv6 addresses from a public prefix are not private.** A tunnel broker or ISP prefix (for example
  `2001:470:xxxx::/48`) is public address space, so a reverse lookup for one of your IPv6 devices goes
  through your filter to the internet and on to the prefix owner. It carries the address, not a device
  name. To keep those lookups in, tell the filter the prefix is local. In AdGuard Home, add it to
  `dns.private_networks` in `AdGuardHome.yaml` (stop AdGuard first). Setting that list replaces
  AdGuard's built-in private ranges, so list them too:

  ```yaml
  dns:
    private_networks:
      - 10.0.0.0/8
      - 172.16.0.0/12
      - 192.168.0.0/16
      - fd00::/8
      - 2001:470:xxxx::/48
  ```

  Then the reverse lookups for that prefix go to AdGuard's private reverse server instead. The router
  has no IPv6 names to give back, so they end as "no such name" without leaving your network.

**IPv6 device names** (the next switch; off at factory from v3.4.2, on by default in earlier builds, and an
upgrade keeps the stored value) covers IPv6. Devices pick their own IPv6
addresses (SLAAC and privacy addresses), so the router never hands them out and has no name for them. Once
a minute the router matches each IPv6 address it sees on a network to the device using it and gives the
address that device's IPv4 (DHCP) name. A reverse lookup of the address, and a forward lookup of the name,
then answer with it: `DESKTOP-EXAMPL1` also returns its current IPv6 addresses. Each network's own IPv6
reverse zone is answered by the router and never sent upstream; between networks the same main LAN / VLAN
rule applies as for IPv4. A new address gets its name within about five minutes, and an address the device stops using keeps its name for 15 minutes: each network's resolver is told about changes at most once every five minutes, because telling it empties its whole DNS cache. A device that has no DHCP name gets none for IPv6 either. The switch does nothing
while IPv6 is off on the router. For AdGuard on a VLAN, mark your IPv6 prefix as private (see above) so its
IPv6 reverse lookups come to the router.

**If you set this up by hand before.** A `rev-server=` line you added to `/jffs/configs/dnsmasq.conf.add`
or `/jffs/configs/dnsmasq-<n>.conf.add` keeps working and wins over the firmware's line. It is no longer
needed. Delete the file, or just that line, then run `service restart_dnsmasq` or toggle the switch.

**Limits.**

- IPv6 names come from the **IPv6 device names** switch below, not from this one.
- A device gets a name only if it took its address from the router by DHCP and sent a host name. A device
  with a fixed address configured on the device itself has no name to share.
- The name is the device's own DHCP host name, not the friendly name you set on the Devices page.
- A device cannot take a name the router already answers for: the router's own name, another device's
  static-lease name, or a name in the hosts file. The DNS server already refuses such a DHCP name for
  IPv4; the IPv6 side refuses it too, and the system log names the device once (`rv6names`).

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

**IPv6.** When the router holds an IPv6 address on the LAN, the Advisor also listens on it and the page shows
a second line, **Endpoint (IPv6)** (`https://[2001:db8::1]:port/mcp`). The same fences apply: it binds the
LAN's own address only, never every address, and the matching firewall rule is opened for the session.
A client-IP pin may be an IPv4 or an IPv6 literal; a pinned session answers only on the family it was
pinned on.

**Limits.** Repeated wrong codes lock arming temporarily. The diagnostics tier refuses loopback, link-local, ULA and private targets that are not on this router's own LAN, so it cannot be turned into an internal scanner; every probe is logged. If the key is lost, only a factory reset clears the USB factor.

### 4.17 Administration → Tweaks: the Reaper setting

The menu names this tab **Tweaks**, under **Administration**. There is no Tools menu. The page has four panels: **Warden** (below), **Connection tracking**, **Advanced tweaks** (including *mDNS across networks*) and **Wireless stability**; 4.27.10 describes the other three. The Warden panel has one setting, with a **?** beside it:

- **Warden feed update schedule** — cron format; empty = 04:30 daily.

Two earlier rows are gone: the interface theme switch (v2.5.9; the theme is always on, see 3) and the socket bind shim (v3.1.8; the vendor's corrected nvram libraries replace it, see 1.5).

Saving on this page no longer logs you out unless the setting needs a web-server restart.

---

### 4.18 Site Survey (Network Tools)

**Network Tools → WiFi Site Survey.** Every network each radio can hear, on every channel its regulatory
domain allows - not only the channel the radio runs on. Pick one radio or all of them and press **Scan
now**. Each radio in turn listens across its whole band (a few seconds; its clients may stutter briefly)
and the table fills as the radios report: name (hidden networks are marked), BSSID, band, control channel,
channel width, signal with a strength bar, SNR, security (named from the AKM suites the network advertises - WPA2-Personal,
WPA2/WPA3-Personal, WPA3-Personal, WPA2-Enterprise, OWE, Open, WEP), Wi-Fi generation (4/5/6/6E/7 from the capability elements) and which radio
heard it. Filter by name or address, sort by any column (the heading row stays in view while the list scrolls), export the list as CSV. **Networks per channel**
below the table shows one card per control channel in use, per band: the channel number and how many networks
sit on it, coloured green (0-1, quiet), amber (2-3, shared) or red (4 or more, crowded). The card of the channel
this router runs on is marked *This router* and is shown even when nobody else is there; hovering a card lists
the networks heard on it. A crowded channel is a poor home for your own network, and the Wireless Quality
page's Auto Scan is the tool that measures the cleanest one. Results stay until the next scan.

Under the progress bar each radio reports its own outcome: how many networks it heard and how long it
listened, *radio off*, or the wireless utility's own error text. A radio whose active scan returns nothing is
asked once more a second later and then listened to passively; a passive result is marked as such. An empty
radio is therefore always a result with a reason, never a blank.

A 5 GHz radio that runs on a block containing radar channels (36/160 or 40/160 under in-service monitoring,
the usual Wi-Fi 7 setting) refuses every scan request while it watches for radar - the full band, a passive
listen, even its own channels - with *Scan Rejected*. The survey tries each of those in turn, then says so on the
radio's line: *On a radar channel under monitoring; a full scan needs it moved to a non-radar channel.* The stock
survey gets a list from such a radio by moving it to a non-radar channel for the scan and setting it back
afterwards, which costs every 5 GHz client the channel change and a fresh radar check on return; Reaper never does
that behind your back. **Scan with channel move** does it on request: a 5 GHz radio that heard nothing in place is moved to 36 or
149 at 80 MHz the way the stock scan core moves it, the scan starts only once the radio really operates there,
and it is moved back afterwards. A confirm step comes first because that radio's clients drop for the scan and
AiMesh nodes follow the channel. The way back waits for a radar check of about a minute: a radio with background
radar checks keeps serving on the scan channel meanwhile, others stay quiet, and a second move inside that minute
is refused. A radio that does not change channel says so and is not scanned; hovering a radio's line shows its
raw radar status. Every other radio scans in place, and the radio's line then reads *full scan after a channel move via 36/80*. A radio
that refused a full-band scan for some other reason reports *Own channel block only; the radio refused a full-band
scan.*, and an error with no text of its own now carries the utility's exit code.

What changed and why: the stock page under this tab ran the router's built-in scan core, which collects the
driver's scan events into a fixed buffer and keeps only the networks that fit, in channel order - on a
single-radio 5 GHz band in a busy block that cut the list at channel 44 while a quad-band router four feet
away listed the rest. The Reaper page reads the wireless utility's own text per radio instead, so nothing
is dropped. The scan never changes a channel or width; preamble puncturing and the minimum-width floor do
not bound a scan either. The survey refuses to start while a Channel Quality capture or an Auto Scan is
running on the Wireless Quality page, and those refuse while a survey runs.

<a id="wan-ports"></a>
### 4.19 WAN Ports

**WAN → WAN Ports** replaces the stock Dual WAN tab (the stock page no longer ships since v3.4.9; its address
opens this one). In router mode the tab shows whenever the model supports Dual WAN (v3.6.3). It saves the same settings the stock page saves, so a configuration made on either page reads back
the same on the other.

- **Internet port** — the port the internet cable is in, or **Auto**. The factory default is the port
  labelled WAN (from v3.4.2; earlier builds defaulted to Auto, and an upgrade keeps whatever is set). If
  the cable is in the other WAN-capable port, choose that port here. Auto works only by trying: every
  WAN-capable port is joined to the LAN bridge and the router asks for an address on the bridge until the
  provider answers on one of them. That happens even with Dual WAN off. Once a port has carried the WAN,
  Reaper keeps it (`reaper_wanport`) and never joins it to the LAN again, not at boot and not when the
  link drops; the status line says **Found by Auto and kept out of the local network**. **Detect again**
  forgets the kept port and searches again (the candidates are on the LAN during the search). Picking a
  fixed port turns Auto off and clears the kept port. Auto is not offered while Dual WAN, WAN aggregation,
  IPTV/VLAN tagging, a static WAN address, MAC clone or a second WAN service is in use, and the card says
  which one is the reason. A LAN port used as the WAN has its own port picker.
- **Dual WAN** — a second connection that takes over when the first fails (**Fail Over**, with optional
  **Allow failback**) or shares the traffic (**Load Balance**, with a ratio). **Hot standby** keeps the
  second connection up while idle. **USB backup** keeps a USB modem as the backup without enabling Dual WAN.
- **Network Monitoring** — DNS query, ping, or both, with the interval, the failures before a switch and the
  successes before failback. With Dual WAN off it only feeds the connection status.
- **Load Balance rules** — up to 64 source/destination pairs pinned to one connection (each address is an IP,
  IP/netmask or `all`) and the ISP profile per connection.

IPTV (LAN → IPTV), Switch Control and the Internet Connection page are separate pages; Internet Connection names
the WAN port actually in use, resolved the way this page resolves it (v3.6.3).

### 4.20 VPN

The **VPN** menu holds six tabs: **VPN Status**, **VPN Director**, **Policy Routing**, **VPN Server**, **VPN Client**
and **Tor**. The menu shows in router mode only (not in access point, repeater or media bridge mode). Each tab, and
each sub-tab inside VPN Server and VPN Client, is shown only where the firmware is built with the function behind it
(`openvpnd`, `wireguard`, `ipsec_srv`, `pptpd`, `vpnc`, `tor`). All eight models on both lines
(3006.102.10: RT-BE96U, RT-BE86U, RT-BE88U, GT-BE98 Pro; 3006.102.8: GT-BE98, GT-BE19000, BQ16, BQ16 Pro) are built
with all of them, so every tab described here is present on every model.

The pages are Reaper's own (v3.4.9) and replace the stock VPN pages; the stock addresses open the Reaper page. The
engines behind them are Asuswrt-Merlin's (OpenVPN client and server, WireGuard, VPN Director) and ASUS's (IPsec,
PPTP, the PPTP / L2TP client, Tor's firewall rules). Each page posts only the settings you changed. A stored password,
WireGuard private key or pre-shared key is never sent to the page: the field shows `********` (or says that a key is
saved) and is written only when you type a new value. The OpenVPN key and certificate boxes are the exception: they load
the stored PEM text so it can be edited.

Apart from Policy Routing, these pages use a plain **Apply**: the change is saved to flash at once, with no
Keep / Revert timer (2.7). Every Apply that would drop a running tunnel or disconnect clients asks first and names what happens.

What a VPN client and its **Killswitch** do to traffic is the same on every page:

- A device is sent into a client tunnel by a VPN Director rule (4.20.2), a Policy Routing rule (4.4), an OpenVPN client
  set to redirect all traffic, or a network bound to the client on the Network page.
- **Killswitch on, client enabled, tunnel down** - that traffic is blocked. It does not fall back to the WAN.
- **Killswitch off** - that traffic uses the WAN while the tunnel is down and returns to the tunnel when it is up.
- **Client switched off** - the Killswitch does not apply; the traffic uses the WAN (4.4.7).

#### 4.20.1 VPN Status

**What it is.** A live, read-only view of every VPN server and client on the router. It writes nothing: there is no
form and no Apply. It refreshes every 10 seconds while the page is visible, stops while the browser tab is hidden, and
**Refresh** asks again at once. Reaper's own page; the stock status page no longer ships.

**How to use it.**

1. Open **VPN > VPN Status**. The pill at the top reads *Updated hh:mm:ss* after each successful read, or *Some data
   could not be read* when one of the requests failed.
2. Choose **Servers** to see the OpenVPN, WireGuard, IPsec and PPTP servers and who is connected to each.
3. Choose **Clients** to see the five OpenVPN clients, the five WireGuard clients and the PPTP / L2TP profiles.
4. Each instance has a **Settings** link that opens the tab on VPN Server or VPN Client where it is configured.

**What each section shows.**

| Section | What it shows |
|---|---|
| OpenVPN servers 1 and 2 | State (*Running*, *Starting*, *Stopped*, *Error* with the reason: IP/Routing conflict, Authentication failed, Configuration error, No network to the server). Connected clients: username, common name, real address, virtual address, bytes received and sent, connected since, data-channel cipher. The routes table: virtual address, common name, real address, last used. |
| WireGuard server | *Running* or *Off*, and each peer: name, the first 12 characters of its public key, *Connected* / *Idle* / *Never*, endpoint, allowed IPs, last handshake, transfer. A peer counts as connected when its last handshake is under three minutes old. |
| IPsec server | *Running* or *Off*, and the connected clients per IKE version: remote IP, status, access time, username, PSK re-authentication, bytes received and sent. |
| PPTP server | *Running*, *Stopped* (enabled but no daemon) or *Off*, and the connected clients: username, interface, remote IP, client IP. |
| OpenVPN clients 1-5 | Description, state, an *Enabled* tag, server address:port/protocol, the Internet routing mode (*No Internet traffic*, *Redirect all Internet traffic*, *VPN Director*). While connected: local tunnel IP, public IP, the OpenVPN traffic statistics and the time they were updated. |
| WireGuard clients 1-5 | Description, *Off* / *Connected* / *No recent handshake* / *Waiting for data*, server endpoint. While enabled: local IP, public IP, and the peer's endpoint, allowed IPs, last handshake, transfer and keepalive. |
| PPTP / L2TP | Each saved profile: type, description, state, server, username. Only the profile in use carries a state; the others read *Off*. Passwords are never sent to the page. |

**The settings.**

| Setting | What it does | Default |
|---|---|---|
| **Servers** / **Clients** | Switches between the two views. The choice is remembered for the browser tab; `?tab=servers` or `?tab=clients` in the address opens one directly. | Servers |
| **Refresh** | Reads everything again now. Does not clear the cached public addresses. | - |
| **Settings** (per instance) | Opens that instance's configuration tab. | - |

**Limits and gotchas.**

- Every instance is listed with its state, including stopped servers and disabled clients; the stock page hid them.
- A server whose state key says running but whose daemon is gone is shown *Stopped*.
- The WireGuard dumps (`wg show`, run by the web server on each read) are fetched only for the view that is open.
- The stock Refresh posted a reset of the cached tunnel addresses, which made the router look its public address up
  again over HTTP. Reaper's Refresh writes nothing.
- *No recent handshake* on a WireGuard client means it is enabled and has had no handshake for three minutes. The
  router's watchdog restarts such a client on its own (4.20.5, *WireGuard client watchdog*).

#### 4.20.2 VPN Director

**What it is.** VPN Director is Eric Sauvageau's (Asuswrt-Merlin) policy-routing table: rules that send LAN traffic
through an OpenVPN client, a WireGuard client or out the WAN, chosen by **source** address (a LAN device or subnet) and
**destination** address. Each rule becomes a plain `ip rule` (priority 10000 and up) that points at the client's
routing table. Reaper keeps Merlin's engine and replaces the page.

The rules apply to an OpenVPN client only while its **Redirect Internet traffic** is set to **VPN Director rules**
(4.20.5). A WireGuard client has no such setting: it carries only what VPN Director, Policy Routing or a network
binding sends to it.

**How to use it.**

*Route one device through a VPN client.*

1. Set up and enable the client on **VPN Client** (4.20.5). For OpenVPN, set **Redirect Internet traffic** to
   **VPN Director rules**.
2. Open **VPN > VPN Director**. The **VPN clients** cards show each client's state and tags: *Enabled* / *Off*,
   *VPN Director* or *Redirect all* (OpenVPN), *Killswitch*.
3. In the rule form choose **Interface** = the client, for example *WireGuard 1*.
4. In **Local IP** pick the device from the list, or type its address, for example `192.168.50.20`. Picking a device
   fills **Description** with its name while that field is empty or still holds the last name filled in.
5. Leave **Remote IP** empty (any destination).
6. Press **Add**. The rule appears in the table under its interface's heading; nothing is saved yet.
7. Press **Apply**. The router rebuilds every VPN routing rule, Killswitch and exclusive-DNS rule, then Policy
   Routing's rules.

*Route a whole subnet, but keep one device on the WAN.*

1. Rule 1: Interface *OpenVPN 1*, Local IP `192.168.50.0/24`.
2. Rule 2: Interface *WAN*, Local IP `192.168.50.30`.
3. Apply. WAN rules are evaluated before VPN rules, so 192.168.50.30 uses the WAN.

*Send traffic to one destination network through a tunnel.* Interface *WireGuard 2*, Local IP empty, Remote IP
`203.0.113.0/24`. The page asks before adding a rule with neither address: it matches every connection, the router's
own included.

**The settings.**

| Setting | What it does | Default |
|---|---|---|
| **VPN clients** cards | Read-only: each OpenVPN and WireGuard client's description, state, routing mode and Killswitch. Enabling a client, its routing mode and its Killswitch are set on **VPN Client** (link on the card heading). | - |
| **Interface** | Where matched traffic goes: *WAN*, *OpenVPN 1-5*, *WireGuard 1-5*. | WAN |
| **State** (form) | Whether the new or edited rule is on. | On |
| **Description** | A label, up to 32 characters; no `<` `>` `'` `%` `"` or `\`. | empty |
| **Local IP** | Source: one IPv4 address or an IPv4 network in CIDR form. Empty = any. The list offers the devices the router knows. | empty |
| **Remote IP** | Destination: one IPv4 address or network. Empty = any. | empty |
| **Add** / **Save** | Adds the rule, or saves the rule being edited, into the table. Nothing reaches the router until Apply. | - |
| **Cancel** | Leaves edit mode and clears the form. | - |
| **State** (table, *On* / *Off*) | Click to switch a rule on or off without deleting it. | - |
| **Edit** | Loads a rule into the form; **Add** becomes **Save**. | - |
| **x** (delete) | Removes the rule from the table. | - |
| **Apply** | Saves the list and runs `restart_vpnrouting0`. | - |
| **Discard** | Reloads the page and drops unsaved edits. | - |

**Examples.**

- *A streaming box through a provider tunnel, everything else direct.* WireGuard 1 imported from the provider's
  `.conf`, rule Interface *WireGuard 1*, Local IP `192.168.50.40`. The rest of the LAN does not use the tunnel.
- *Tunnel the house, exempt a work laptop.* OpenVPN 1 set to VPN Director rules; rule *OpenVPN 1* for
  `192.168.50.0/24`; rule *WAN* for `192.168.50.25`.

**Limits and gotchas.**

- **IPv4 only.** Local IP and Remote IP take IPv4 addresses and networks. To steer IPv6, or to match a device by MAC
  address or a destination by domain name, use Policy Routing (4.4).
- **Order.** WAN rules win over VPN rules. Inside one interface the order does not matter: every rule of the group
  routes to the same table. The table is grouped by interface for display; the stored order is kept (stock re-sorted
  the list on every Apply).
- **Policy Routing wins.** A Policy Routing rule for the same traffic is evaluated first (priority 9000 band) and
  overrides a VPN Director rule (4.4.6).
- **A rule to a switched-off client** is marked on its group heading, and Apply asks before saving such a rule. Its
  traffic uses the WAN while the client is off (4.4.7).
- **A rule to an OpenVPN client that is not set to VPN Director rules** has no effect until the client's routing mode
  is changed. From the image after v3.8.0 the group heading says so (*not in VPN Director mode, rule not used*) and
  Apply asks first, as it does for a rule to a switched-off client. A switched-off client blocks nothing, even with
  its Killswitch on: its rules' traffic uses the WAN. The one case that stays blocked is a guest network bound to the
  client with the network's own Kill Switch on (4.21.4).
- **WireGuard and the hardware accelerator.** A WireGuard source rule also keeps that device's traffic off the
  hardware accelerator so the tunnel sees it (4.4.9 describes the shared bypass table).
- **Capacity.** Up to 199 rules and 7999 characters in all; the counter under the table shows both. The list is kept in
  a file on `/jffs` (`/jffs/openvpn/vpndirector_rulelist`), not in nvram.
- A duplicate rule (same interface, Local IP and Remote IP) is refused. A stored record that is not five fields is
  shown dimmed with *not five fields, ignored by the router* and can only be deleted.
- **Guest networks.** A rule whose Local IP is a guest network's subnet routes that network. Since v3.8.0 such a
  network reaches the internet through the tunnel; this does not apply to a Guest Portal network or to a network with
  its own Kill Switch on (4.2.5).
- Removed from the stock page: the client on/off switches and the Edit jumps. They saved client settings from a rules
  page; the client cards now link to VPN Client instead.

#### 4.20.3 Policy Routing

**What it is.** Reaper's own routing engine, in the VPN menu next to VPN Director. It sends traffic chosen by a
**destination domain list or Firewall object**, a **source IP / CIDR** (IPv4 or IPv6) or a **source MAC** to an OpenVPN
client, a WireGuard client, the WAN, or a block. Its rules take precedence over VPN Director's, follow each client's
Killswitch, and use the Keep / Revert timer. Section 4.4 describes the page in full: matching (4.4.3), domain lists
(4.4.4), ASN lists and country lists (4.4.4a), targets (4.4.5), order (4.4.6), the Killswitch (4.4.7), examples (4.4.8) and limits (4.4.9). It is off by
default (`reaper_pbr_enable` `0`, 8.2).

Details of the page that 4.4 does not state:

- Each rule has an optional **Description** (up to 48 characters), shown in the rules table.
- A domain list's **Name** takes letters, digits and underscore, up to 25 characters; its **Description** takes up to
  60. All Firewall objects together are limited to 8191 characters, and a save that would pass that is refused.
- Deleting a domain list that a rule still uses asks first.
- The source IP / CIDR box takes up to 64 entries per rule; more must be split over two rules (4.4.3 states the
  limit).
- Apply can end with one of these messages: *No confirmed snapshot exists yet. Reboot once on this firmware, then
  apply again*; *A change is already awaiting confirmation. Keep or revert it first*; *The new rules could not be
  built and were rolled back*; *Some rules did not load. The watchdog keeps retrying; the system log names them*;
  *Kept, but the saved copy is incomplete. Apply and keep again so it survives a reboot*.

#### 4.20.4 VPN Server

**What it is.** The servers this router runs for devices connecting from outside: two **OpenVPN** instances, one
**WireGuard** server with up to ten peers, an **IPsec** server (IKEv1 and IKEv2) and a **PPTP** server, each on its own
sub-tab. All are off at factory (`vpn_serverx_start` empty, `wgs_enable` `0`, `ipsec_server_enable` `0`,
`pptpd_enable` `0`; 8.3). The OpenVPN and WireGuard servers are Merlin's; IPsec (strongSwan) and PPTP are ASUS's. The
page is Reaper's own.

The pill at the top lists the servers that are on. Each server tab has a **Server address** row: the DDNS host name
when DDNS is on, otherwise the WAN address. When that address is private (10/8, 172.16/12, 192.168/16, or the carrier
range 100.64/10), the row warns that clients outside cannot reach it without a port forward on the upstream router.

**How to use it: a WireGuard server and a phone.**

1. Open **VPN > VPN Server > WireGuard** and switch **Enable WireGuard server** on. Leave the defaults
   (tunnel address `10.6.0.1/32`, port `51820`, keepalive `25`).
2. Press **Apply**. The first start generates the server's key pair; **Public Key** then shows it.
3. In **Peer** press **Add**. The editor suggests the next free address in the server's /24, for example
   `10.6.0.2/32`, server-side Allowed IPs = that address, client-side Allowed IPs = `0.0.0.0/0`.
4. Enter a **Username** (the peer's name), for example `phone`, and press **Save peer**. The peer is saved at once,
   not with Apply. A running server takes it without dropping the other peers.
5. Press **Export** on the peer's row. The configuration appears, with **Download** (`wgs_client.conf`) and **QR**.
6. In the WireGuard app on the phone, add a tunnel by scanning the QR code. The file and the code contain the peer's
   private key: hand them to that device only.
7. Connect from mobile data. **Server status** shows the peer's handshake; VPN Status lists it as *Connected*.

**How to use it: an OpenVPN server for a laptop.**

1. Open **VPN > VPN Server > OpenVPN**, choose **Server 1** in **Instance**, switch **Enable OpenVPN Server** on.
2. Choose **Client will use VPN to access**: *Local network only*, *Internet only* or *Internet and local network*.
3. Under **Username and Password** add an account, for example `laptop` with a password. Username and password
   authentication is on by default, so the client presents this account as well as its certificate.
4. Press **Apply**. The first start generates the certificates and can take a minute.
5. When the instance shows *Running*, press **Export** to download `client1.ovpn`, and import that file into the
   laptop's OpenVPN client.
6. The laptop connects to the **Server address** shown, on UDP 1194 (instance 2: UDP 1195).

**How to use it: IPsec for the built-in VPN client of a phone or a PC.**

1. Open **VPN > VPN Server > IPsec**, switch **Enable IPSec VPN Server** on and enter a **Pre-shared Key** of 8 to 32
   characters.
2. Add an account under **Username and Password** and choose its **Supported IKE version**.
3. Press **Apply**.
4. IKEv1 clients use the server address, the pre-shared key and the account. IKEv2 clients use the account and must
   trust the server certificate: download it with **For Windows** (`.der`) or **For Mobile** (`.pem`) under
   **IKEv2 certificate** and install it on the device.

**The settings: OpenVPN.**

The two instances are configured one at a time. Clicking the other instance in **Instance** saves the choice on the
router and reloads the page (it asks first when there are unsaved changes). The user list is shared by both instances;
everything else is per instance.

| Setting | What it does | Default |
|---|---|---|
| **Instance** | Server 1 or Server 2. The dot shows running (green), starting (amber) or failed (red). | Server 1 |
| **Enable OpenVPN Server** | Starts this instance now and at every boot; off disconnects its clients. The line beside it gives *Running*, *Starting*, *Failed*, *Enabled* or *Disabled*, and a failure reason (routing conflict, certificate or key problem, weak or missing DH parameters, configuration error). | Off |
| **Server address** | Read-only: what clients connect to (see above). | - |
| **Client will use VPN to access** | *Local network only*: the LAN route is pushed and clients reach the router and LAN. *Internet only*: clients are told to send all traffic through the tunnel and reach only the Internet. *Internet and local network*: both. | Local network only |
| **RSA Encryption** | 1024 or 2048-bit keys for the certificates generated at the first start. Shown only while no certificate exists. | 2048 bit |
| **Export OpenVPN configuration file** | Downloads a ready-to-import `.ovpn` profile for this instance. Available while the instance runs. | - |
| **Keys and certificates: Edit** | Opens a panel with `ca.crt`, `server.crt`, `server.key`, `dh.pem`, `crl.pem`, `static.key` and extra chain certificates as PEM text, up to 7999 characters each. An empty box is generated at the next start. **OK** keeps the edit for Apply. | - |
| **Renew Certificate** | Marks the certificates for renewal: Apply blanks the CA, certificate, key, DH and CRL and the server makes new ones at start. Every client then needs a new profile. Enabled only while certificates exist and the instance is on. | - |
| **Export Current Certificate** | Downloads the instance's certificate set as a `.cert` file. | - |
| **Import Original Certificate** | Uploads a `.cert` file exported earlier and restores it; the page reloads. | - |
| **Reset this instance** | Stops the instance and returns every setting, key and certificate of it to factory values. Every client profile for it stops working. | - |
| **Username and Password** table | Accounts for username and password authentication, shared by both instances, up to 32 and 2048 characters in all. The router's login account is always listed and always allowed. Usernames may not contain spaces or `@ * + \| : ? < > , . / ; [ ] \ = " & #`; passwords are 1-64 characters without `< > & "`. **Show passwords** reveals them. The first column shows whether each account is connected to the selected instance. | router login only |
| **Interface Type** | TUN routes IP packets. TAP bridges Ethernet frames into the LAN and uses a client address pool. | TUN |
| **Protocol** | UDP or TCP. | UDP |
| **Port** | The port clients connect to, 1-65535. The two instances cannot share a port on the same protocol. | 1194 (instance 1), 1195 (instance 2) |
| **Username and password authentication** | Clients must present an account from the list in addition to their certificate. | On |
| **Username / Password Auth. Only** | Shown when the above is on. Accepts the account alone; the client certificate is not checked. | Off |
| **TLS control channel security** | *Disable*, *TLS auth* (bi-directional, incoming 0, outgoing 1), *TLS encryption (tls-crypt)*, *TLS encryption v2 (tls-crypt-v2)*. Signs or encrypts the TLS handshake with a shared key so unknown clients are dropped before authentication; tls-crypt-v2 gives every client its own key. | Disable |
| **Generate client key** | Shown when tls-crypt-v2 is saved and the instance runs. Generates a key for one client to paste into that client's profile as its tls-crypt-v2 block; **Copy** copies it. The router does not keep it. | - |
| **Auth digest** | HMAC digest for the control channel. Choosing MD5 or RSA-MD4 shows a warning. | Default |
| **VPN Subnet / Netmask** | TUN only. The private network handed to clients; netmask /16 to /29, no host bits set. Must not overlap the LAN, the other instance or the WireGuard server's /24. | 10.8.0.0 / 255.255.255.0 (instance 2: 10.16.0.0) |
| **IPv6** | TUN only, shown when the router has IPv6. Gives clients IPv6. | Off |
| **IPv6 NAT** | Translates clients' IPv6 addresses to the router's. Off hands them routable addresses from the IPv6 subnet. | On |
| **IPv6 VPN Subnet / Netmask** | The IPv6 prefix for clients. | `fd00:ac68:1::/64` |
| **Allocate from DHCP** | TAP only. The LAN's DHCP server addresses the clients; off uses the pool below. | On |
| **Client Address Pool** | TAP with DHCP off: first and last address, inside the LAN subnet, not covering the router's address. | 192.168.1.50 - 192.168.1.55 |
| **Local / remote endpoint addresses** | Point-to-point addresses for a single TUN client with a fixed peer. Leave both empty for the usual subnet mode. | - |
| **IPv6 Local / remote endpoint addresses** | The IPv6 equivalent. | empty |
| **Advertise DNS to clients** | Tells clients to use this router for DNS (and the LAN domain). Changing it also restarts the DNS server. | Off |
| **Data ciphers** | Colon-separated list negotiated with the client, strongest first, for example `AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305`. Letters, digits, colon and hyphen only. | built-in list |
| **Log verbosity** | 0 (silent) to 6. | 3 |
| **Manage Client-Specific Options** | Turns on the per-client table and the two switches below. Off, several clients may connect with the same certificate. | Off |
| **Allow Client <-> Client** | Clients of this instance can reach each other. | Off |
| **Allow only specified clients** | Only clients named in the table may connect; others are refused after authentication. | Off |
| Client-specific table | Per client: **Common name** (the **Username** when Username / Password Auth. Only is on), **Subnet** and **Netmask** of a network that lives behind that client, **Push**. The router routes that subnet to the client. **Push = Yes** announces the subnet to the other clients, and only while Allow Client <-> Client is on. Up to 128 rows; the counter shows the byte budget (the list is held in nvram and limited to about 1 KB). | empty |
| **Custom Configuration** | Extra OpenVPN directives appended to the server configuration, one per line, up to 4095 characters. Kept in `/jffs/openvpn`, not nvram. | empty |
| **Connection Status** | Read-only: common name, real address, VPN address and connected-since of each client of the selected instance. | - |

**The settings: WireGuard.**

| Setting | What it does | Default |
|---|---|---|
| **Enable WireGuard server** | Starts the server now and at every boot; off disconnects every peer. | Off |
| **Server address** | Read-only: what peers connect to. | - |
| **Access Intranet** | Peers reach devices on the LAN. Off: peers reach only the Internet through the router. | On |
| **Tunnel IPv4 and / or IPv6 Address** | The router's own tunnel address with prefix; add an IPv6 one after a comma if peers need IPv6. Must not overlap the LAN. | `10.6.0.1/32` |
| **Listen Port** | UDP port peers connect to, 1-65535. | 51820 |
| **Persistent Keepalive** | Seconds between keepalive packets a peer sends so NAT mappings stay open; 0 disables. | 25 |
| **Push router as DNS** | Peers use this router for DNS. Changing it restarts the DNS server. | On |
| **Enable NAT - IPv6** | Shown when the router has IPv6. Translates the peers' IPv6 addresses to the router's. | On |
| **Pre-shared Key (Secret)** | Adds a pre-shared key to every peer. Peers must import a new configuration after a change. | Off |
| **Public Key** | Read-only: the server's public key. | - |
| **Private Key** / **Renew keys** | The private key is never shown. **Renew keys** marks a new key pair for Apply; every peer must then import a new configuration. | generated at first start |
| **Peer** table | Up to ten peers: connection dot, name, address, allowed IPs, and **Edit**, **Export** and **x** (delete). | empty |
| **Add** / **Edit** (peer editor) | **Username**: the peer's name, up to 64 characters. **Address**: the peer's tunnel address with /32 (or /128), unique among peers and different from the server's. **Allowed IPs (server side)**: what the server routes to this peer, normally its own address. **Allowed IPs (client side)**: what the peer sends through the tunnel; `0.0.0.0/0` sends everything, the LAN subnet alone sends only LAN traffic. | next free address; client side `0.0.0.0/0`. On a server that also has an IPv6 tunnel address (from the image after v3.8.0): the same host number in both families, for example `10.6.0.3/32,fd00::3/128`, and client side `0.0.0.0/0,::/0`, so the peer's IPv6 uses the tunnel too. Existing peers are never changed |
| **Save peer** | Saves this peer at once. A running server takes it live without dropping the others; a stopped server uses it at its next start. | - |
| **Renew keys** (peer) | New key pair for this peer; its current configuration stops working and must be exported again. | - |
| **Export** | Shows the peer's configuration with **Download** and **QR**. Available once the server runs and the peer has keys. | - |
| **x** (delete peer) | Deletes the peer and its keys. On a running server this restarts the server: connected peers drop for a few seconds and reconnect on their own. | - |
| **Server status** | Live `wg show` output for the server interface, every 10 seconds while the tab is open. | - |

**The settings: IPsec.**

| Setting | What it does | Default |
|---|---|---|
| **Enable IPSec VPN Server** | Starts the server now and at every boot. Changing any IPsec setting while it runs makes connected clients reconnect (Apply asks). | Off |
| **Server address** | Read-only: what clients connect to. | - |
| **Pre-shared Key** | 8 to 32 characters, no spaces, no `< > & "`; typed into every IKEv1 client. **Show** reveals what you type. | - |
| **Client will use VPN to access** | *Internet only* or *Internet and local network*. | Internet and local network |
| **Client IP address** | The first three octets of the private network handed to clients; they get .1 to .254. Must not overlap the LAN, an OpenVPN instance, the WireGuard server or the PPTP pool. | `10.10.10` (`10.10.11` when the LAN itself is 10.10.10.x) |
| **Dead Peer Detection** / **DPD Checking Interval** | Drops clients that stopped answering so their addresses are freed; interval 10-900 seconds. | On, 10 s |
| **DNS Server1 / 2**, **WINS Server1 / 2** | Servers pushed to clients. Empty pushes the router. | empty |
| **IKE / ISAKMP Port** / **NAT-T Port** | Read-only: UDP 500 and 4500, fixed on this build. | 500 / 4500 |
| **Instant Guard** | Shown only when an Instant Guard profile from stock firmware is still saved. Its app and page are gone, but the router keeps an IPsec server running for those accounts until **Turn off and remove** is pressed and applied. | - |
| **Username and Password** | Up to eight accounts. Usernames up to 32 characters, without spaces or `@ * + \| : ? < > , . / ; [ ] \ = " & #`; passwords 5-32 characters. **Supported IKE version**: *IKEv1 + IKEv2* or *IKEv1*. | empty |
| **IKEv2 certificate** | **Status** (*Authenticated* / *Not Authenticated*), issued to / from / expiry, **For Windows** and **For Mobile** downloads, **Renew Certificate**. A note asks for a renewal when a network change was detected. | - |
| **Connection Status** | Read-only: real address, status with IKE version, access time, username; Instant Guard sessions are marked. | - |
| **System Log** | The strongSwan log: **Refresh**, **Clear** (asks), **Save** (`ipsec.log`). | - |

**The settings: PPTP.**

| Setting | What it does | Default |
|---|---|---|
| **Enable VPN Server** | Starts the PPTP server now and at every boot; off disconnects its clients. | Off |
| **Server address** | Read-only: what clients connect to. | - |
| **Authentication** | Fixed: MS-CHAPv2 with 128-bit MPPE required. When the stored setting still allows the older options (the factory value does), **Apply now** marks the strict setting for Apply, and any PPTP Apply saves it. | MS-CHAPv2 + MPPE-128 from the first PPTP Apply |
| **Network Place (Samba) Support** | Announces the router as WINS server so Windows network browsing works over the tunnel; forces Broadcast Support on. | On |
| **Broadcast Support** | Relays LAN broadcasts to connected clients. | Off |
| **Connect to DNS Server automatically** / **DNS Server1 / 2** | On pushes the router. Off: enter one or two DNS servers to push instead. | On |
| **Connect to WINS Server automatically** / **WINS Server1 / 2** | The same for WINS. | On |
| **MTU / MRU** | 576 to 1492. Lower both if clients stall behind PPPoE. | 1450 / 1450 |
| **Client IP address** | First address and last octet of the client pool, up to 30 addresses, outside the DHCP pool and away from the router's own address. A pool containing the router's LAN address is refused; overlap with the DHCP pool or a reservation is shown as a note. | - |
| **Username and Password** | Up to 32 accounts (4096 characters in all), with the connection status of each. **Static Route** per account: a network or host behind that client, with netmask, routed through its tunnel while it is connected. | empty |

**Examples.**

- *Phone reaches LAN devices, Internet stays local.* WireGuard peer with client-side Allowed IPs = `192.168.50.0/24`,
  server **Access Intranet** on. Only LAN traffic uses the tunnel.
- *Laptop uses the home connection on public Wi-Fi.* OpenVPN instance 1 with *Internet and local network*; the laptop
  sends all its traffic through the tunnel.
- *A site behind a client.* OpenVPN with **Manage Client-Specific Options** on, a row with Common name `branch`,
  Subnet `198.51.100.0`, Netmask `255.255.255.0`. The router routes 198.51.100.0/24 to the client `branch`.

**Limits and gotchas.**

- **Warden.** While Warden blocks countries or uses feeds, only enabled WireGuard servers' listen ports are exempt.
  OpenVPN and IPsec users from a blocked address cannot connect; whitelist their address (4.3.1.13, section 6).
- **UPnP** cannot map a port the router listens on for VPN (`upnp_protect_svc`, 8.2).
- **Port clashes.** The page refuses a save that puts two listeners on one port and protocol: either OpenVPN instance,
  the WireGuard server, and the IPsec ports 500 and 4500 (from the image after v3.8.0 the check covers all of them,
  including switching on an instance whose saved port clashes; the message names the listener in the way). TCP
  OpenVPN on the same number as UDP WireGuard is fine. If the WireGuard server still cannot start, the system log
  says `WireGuard server did not start: the interface could not be brought up (is UDP port N in use?)`.
- **Guest networks.** Clients of the router's WireGuard and OpenVPN servers can open connections into an isolated guest
  network (v3.7.8); the server's own LAN-access setting still decides. Not into a Guest Portal network, and not while
  that network's Kill Switch is on.
- **OpenVPN DH.** A DH group under 2048 bits is replaced with the built-in RFC 3526 2048-bit group (v3.2.6). On the
  3006.102.10 models certificates are issued with Easy-RSA 3 (v3.6.0).
- **OpenVPN client-specific table** is held in nvram and limited to about 1 KB per instance. Larger setups can put
  files in `/jffs/configs/openvpn/ccd1` (or `ccd2`); they are copied into the instance's client-config directory at
  start.
- **WireGuard peer saves are immediate** and separate from Apply. Saving or deleting a peer with other unsaved changes
  on the page asks first, because the page reloads.
- **Turning the WireGuard server on** does not happen behind your back: adding the first peer does not enable it
  (stock did).
- **PPTP** authentication is weak; prefer WireGuard or OpenVPN. MS-CHAPv1, MPPE-40 and *No encryption* are no longer
  offered.
- **IKEv2 certificate.** IKEv2 clients identify the server by the DDNS host name, or by the WAN address when DDNS is
  off. Renew the certificate after the WAN address or the DDNS name changes; every IKEv2 client must then install the
  new one.
- **Renewing** any server key or certificate breaks every existing client profile of that server until it is
  re-exported.

#### 4.20.5 VPN Client

**What it is.** The tunnels this router opens to other networks: five **OpenVPN** clients, five **WireGuard** clients
and one **PPTP / L2TP** connection with up to ten saved servers. Which devices use a tunnel is decided by VPN Director,
Policy Routing or a network binding, not on this page (an OpenVPN client can also take all traffic). The OpenVPN and
WireGuard clients are Merlin's; the PPTP / L2TP client is ASUS's. The page and the WireGuard client watchdog are
Reaper's.

Apply restarts only the client you changed. A change to a description or a Killswitch alone does not restart the
tunnel; the routing and Killswitch rules are re-applied instead.

**How to use it: add a WireGuard client from a provider's `.conf`.**

1. Open **VPN > VPN Client > WireGuard** and pick a free instance (1-5) in the strip at the top.
2. Under **Import configuration** press **Choose file**, pick the provider's `.conf`, then **Upload**. The file is
   checked first: a file without a valid `[Interface] PrivateKey` or `[Peer] PublicKey` is refused and nothing
   changes. An accepted file replaces every setting of the instance, and the page reloads.
3. Enter a **Description**, for example `provider-nl`.
4. Check **Killswitch**: on, the devices you route here lose Internet access while the tunnel is down instead of using
   the WAN.
5. Switch **Enable** on and press **Apply**. The status line reads *Connected* with the tunnel and public address once
   the first handshake arrives.
6. Route devices to it on VPN Director (4.20.2) or Policy Routing (4.4). A WireGuard client carries nothing until a
   rule or a network binding sends traffic to it.

**How to use it: route one device through a provider's OpenVPN profile.**

1. Open **VPN > VPN Client > OpenVPN** and pick an instance (1-5). Switching instance reloads the page.
2. Under **Import .ovpn file** press **Choose file**, pick the profile, then **Upload**. The instance's settings and
   keys are replaced; its description, routing mode and Killswitch are kept. The page names any key or certificate the
   file did not contain; paste it under **Keys and Certificate**.
3. If the provider uses accounts, switch **Username and password** on and enter them.
4. Set **Redirect Internet traffic** to **VPN Director rules**, switch **Killswitch** on if wanted, switch **Enable** on
   and press **Apply**.
5. On VPN Director add a rule: Interface *OpenVPN N*, Local IP = the device (4.20.2).

**The settings: OpenVPN client.**

| Setting | What it does | Default |
|---|---|---|
| Instance strip | Clients 1-5 with state dot and description. Switching saves the selected instance on the router and reloads; unsaved changes on the tab are lost (it asks). | 1 |
| **Enable** | Starts the client now and after every reboot or WAN reconnect (`vpn_clientx_eas`). | Off |
| **Status** | *Connected* with tunnel and public address, *Connecting...*, *Connection failed* with the reason (IP/Routing conflict, SSL / TLS problem, DH parameter problem, Authentication failed), *Disconnected* or *Disabled*. | - |
| **Description** | Up to 25 characters; shown on VPN Director and VPN Status. | `Client N` |
| **Import .ovpn file** | See above. | - |
| **Reset: Default** | Stops the instance and deletes all its settings, keys and certificates (asks). | - |
| **Interface Type** | TUN routes IP traffic. TAP bridges Ethernet frames and cannot use VPN Director rules. | TUN |
| **Protocol** | UDP or TCP. | UDP |
| **Server** | Host name or address of the server, and its port. Required when the client is enabled. | port 1194 |
| **Server is on the same subnet** | TAP only. Off: distinct subnets cannot be bridged, the tunnel is routed instead. | On |
| **NAT on the tunnel** | Translates LAN addresses to the tunnel address. Off: the far side must route your LAN back. Hidden for a bridged TAP client. | On |
| **Block inbound traffic** | On: connections coming in through the tunnel are dropped. Off: the tunnel is treated like the LAN. | On |
| **Accept DNS configuration** | What to do with DNS servers the server pushes: *Ignore*; *Relaxed* (add them); *Strict* (use them first); *Exclusive* (devices routed through this client by VPN Director use only them). | Relaxed |
| **Redirect Internet traffic** | *No*: only routes the server pushes. *Yes, all traffic*: every LAN device uses the tunnel. *VPN Director rules*: the rules decide (TUN only). For TAP with redirection a **Gateway** field appears. | No |
| **Killswitch** | Shown when Redirect is not *No*. On: routed devices lose Internet access while the tunnel is down. With *Yes, all traffic* that is every device on the LAN. With Redirect *No* (or a TAP client) a saved Killswitch does nothing, for VPN Director and for Policy Routing alike (4.4.7); changing Redirect away from *No* with a Killswitch still saved asks first, because it starts to count. | Off |
| **Username and password** / **Username** / **Password** | Account authentication; username and password up to 64 characters, required when enabled. | Off |
| **Username / Password Auth. Only** | No client certificate is sent; the server is verified with the certificate authority only, which must be present. | Off |
| **Keys and Certificate: Edit** | Static key (tls-auth / tls-crypt), certificate authority, client certificate, client key, CRL (optional), extra chain certificates (optional). Paste each whole `-----BEGIN ... -----END` block, up to 7999 characters. Private keys are masked until **Show private keys** is ticked. The summary lists what is present. | empty |
| **Data ciphers** | Ciphers offered for the data channel, colon separated. | built-in list |
| **TLS control channel security** | *Disabled*, *Bi-directional auth*, *Incoming auth (0)*, *Outgoing auth (1)*, *Encrypt channel (tls-crypt)*, *Encrypt channel v2 (tls-crypt-v2)*; uses the static key and must match the server. | Disabled |
| **Auth digest** | HMAC digest; must match the server. | Default |
| **Log verbosity** | 0 to 6. | 3 |
| **Compression** | *Disabled*, *None*, *LZO*, *LZO adaptive*, *LZ4*, *LZ4-V2*, *Stub*, *Stub-V2*. Compression weakens VPN security; use it only when the server requires it. | Disabled |
| **TLS renegotiation time** | Seconds, -1 to 32767; -1 keeps the OpenVPN default. | -1 |
| **Connection retry attempts** | 0 to 999; 0 retries forever. | 15 |
| **Verify server certificate name** | *No*, *Common name*, *Common name prefix*, *Subject*, with the value to match; a server whose certificate name does not match is refused. Characters OpenVPN would not accept are refused by the page. | No |
| **Custom Configuration** | Extra OpenVPN directives, one per line, up to 4095 characters. | empty |
| **VPN Director** | Read-only: the VPN Director rules for this client and the WAN rules. Shown when Redirect is *VPN Director rules*. | - |

**The settings: WireGuard client.**

| Setting | What it does | Default |
|---|---|---|
| Instance strip | Clients 1-5. Switching is immediate (no reload); unsaved changes on the tab are lost (it asks). | 1 |
| **Enable** | Starts the client now and after every reboot or WAN reconnect (`wgcN_enable`). | Off |
| **Status** | *Connected* with tunnel and public address, *No handshake yet*, *Enabled* or *Disabled*. | - |
| **Description** | Up to 25 characters; required when enabled. | empty |
| **Import configuration** | See above. Resets the description, NAT, firewall and Killswitch to their defaults. | - |
| **Reset: Default** | Stops the instance and deletes all its settings (asks). | - |
| **Enable NAT** | Translates LAN addresses to the tunnel address. Off: the far side must route your LAN back. | On |
| **Block inbound traffic** | On: connections coming in through the tunnel are dropped. | On |
| **Killswitch** | On: devices routed through this client lose Internet access while the tunnel is down. | Off |
| **Private Key** | The `[Interface] PrivateKey`, 44 base64 characters ending with `=`. Never shown; the line beside it says *A key is saved (hidden)* or *No key saved*. **Show** reveals what you type. | - |
| **MTU** | 576 to 1500; empty keeps the WireGuard default. | empty |
| **Address** | Tunnel address(es) with prefix length, comma separated, for example `10.8.0.2/32, 2001:db8::2/128`. Required when enabled. | - |
| **DNS Server** | DNS server addresses the tunnel provides, comma separated (addresses only). Used by VPN Director's exclusive-DNS rules for this client. | empty |
| **Public Key** | The server's `[Peer] PublicKey`, 44 characters. | - |
| **Pre-shared Key** | Optional, 44 characters. | - |
| **Allowed IPs** | Destinations sent through the tunnel, comma separated with prefix length; `0.0.0.0/0` and `::/0` mean everything. Limited to 996 bytes; the counter shows the budget. | - |
| **Endpoint** | Host name or address of the server, and its UDP port. | - |
| **Persistent keepalive** | Seconds between keepalive packets, 1 to 65535. | 25 |
| **VPN Director** | Read-only: the VPN Director rules for this client and the WAN rules. | - |

**The settings: PPTP / L2TP client.**

| Setting | What it does | Default |
|---|---|---|
| **Enable** | Connects now and after every reboot or WAN reconnect. Turning it off keeps the settings. | Off |
| **Status** | *Connected*, *Connecting...*, *Connection failed* (authentication failed, IP/Routing conflict), *Disconnected*, *Disabled*. | - |
| **VPN type** | PPTP or L2TP. | PPTP |
| **Server**, **Username**, **Password** | The connection; required when enabled. | - |
| **Encryption** | PPTP only. New saves use MPPE 128-bit with MS-CHAPv2. A weaker stored value is shown marked *weak encryption* and is replaced at the next save of the connection. | MPPE 128-bit |
| **Use the server's DNS** | Uses the DNS servers the PPTP / L2TP server hands out while the tunnel is up. | On |
| **Route all Internet traffic through the tunnel** | Off: only static routes whose interface is VPN use the tunnel (link to the Static Route List). | On |
| **Saved servers** | Up to ten servers: description, type, server, username, password. **Use** copies a server into the connection and switches Enable on; **Edit** loads it into the form; **x** deletes it. The dot marks the one in use. | empty |

**WireGuard client watchdog (Reaper).** Once a minute, while the primary WAN is connected, the router looks at every
enabled WireGuard client that is not connected (no handshake in the last three minutes) and restarts it when one of
these holds:

- its interface is missing;
- its server name resolves now, but no address was stored when the client started (DNS was not up yet at boot);
- its server name now resolves to an address other than the stored one;
- it has had no handshake for 5 minutes. The client always sends a keepalive, so a working tunnel is never that quiet.

The first restart happens at once; after that the watchdog waits 1, 2, 4 and 8 minutes, then 15 minutes between
restarts. The count starts again once the client has been connected (or the WAN down) in between. Each restart is
logged:

```
WireGuard: client 2 is not connected: no handshake for 5 minutes - restarting it (try 3)
```

The state is kept in `/etc/wg/wd<N>` (RAM). The stock check compared the stored address with the new one in a way that
was always true when nothing was stored, and ignored a client whose server was given as an address; such a client
stayed down until it was switched off and on by hand (v3.7.8). The address the name resolved to is kept in
`wgcN_ep_addr_r` and is the endpoint the tunnel uses: do not clear it by hand.

**On-demand start (Reaper).** When a network on the Network page is bound to a VPN profile, choosing the profile
switches that client on in the same save, and every network change starts a bound WireGuard client that is switched on
but not running, once the router's clock is set. The log says
`WireGuard: client N is used by a network and was not running - starting it`. The router never switches a client on by
itself. On the 3006.102.10 models, a tunnel that drops and comes back also gets its DNS servers back, so a network
bound to it keeps resolving names (v3.7.9); the 3006.102.8 base has no such recovery path.

**Examples.**

- *Two providers side by side.* WireGuard 1 for one provider, WireGuard 2 for another; VPN Director rules send the
  television to 1 and a laptop to 2. Each client's Killswitch is set for its own devices.
- *All traffic through one OpenVPN client.* Redirect Internet traffic *Yes, all traffic*, Killswitch on. Every LAN
  device uses the tunnel and has no Internet while it is down. A VPN Director *WAN* rule (4.20.2) or a Policy Routing
  *WAN* rule (4.4) exempts a device or a destination.

**Limits and gotchas.**

- **Killswitch and a switched-off client.** The Killswitch applies only while the client is enabled; a switched-off
  client's traffic uses the WAN (4.4.7).
- **TAP** OpenVPN clients cannot use VPN Director rules; the option is disabled and a saved value falls back to
  *Yes, all traffic*.
- **WireGuard Allowed IPs.** A VPN Director or Policy Routing rule that sends a device's Internet traffic to a
  WireGuard client needs `0.0.0.0/0` (and `::/0` for IPv6) here; the diagnostics bundle's section 14d warns when a
  rule's client has no default-covering route (4.4.9). The value is held in nvram, hence the 996-byte limit.
- **Keys are never shown.** An empty key field with *A key is saved (hidden)* means the stored key stays; type a new one
  only to replace it.
- **The PPTP / L2TP Apply** no longer stops the OpenVPN clients (stock's dispatch stopped every OpenVPN client and did
  not restart them).
- PPTP authentication is weak and L2TP without IPsec is not encrypted; keep them only for servers that offer nothing
  else.
- A WireGuard or OpenVPN client kept from the stock firmware's provider list is no longer switched off at every boot
  (v3.7.7).

#### 4.20.6 Tor

**What it is.** A transparent Tor proxy on the router (ASUS's feature; Tor itself is the Tor Project's daemon). The
selected LAN devices have their TCP connections and DNS queries redirected into Tor; everything else the router would
forward for them (UDP, ping, voice, games) is dropped so nothing leaks around Tor. Tor runs as its own user with its
database in `/tmp`, backed up to `/jffs`, and needs a few minutes after a start before connections work. Off at factory
(`Tor_enable` `0`). The page is Reaper's own.

**How to use it: one device through Tor.**

1. Open **VPN > Tor** and switch **Enable Tor** on.
2. Set **Redirect** to **Selected devices only**.
3. In **Devices** pick the device from the list or type its MAC address, for example `00:00:5E:00:53:21`, and press
   **Add**.
4. Press **Apply**. The page asks first: the device's TCP and DNS traffic goes through Tor and all its other traffic is
   dropped. Tor and the firewall restart.
5. Wait a few minutes for Tor to connect. The pill reads *Running* while the daemon runs, *Enabled, not running* when it
   is enabled but not running.

**The settings.**

| Setting | What it does | Default |
|---|---|---|
| **Enable Tor** | Starts the Tor daemon and redirects the selected devices through it. | Off |
| **SOCKS port** | Port for LAN applications that speak SOCKS5 to Tor directly. | 9050 |
| **Transparent port** | Port the redirected TCP connections land on. | 9040 |
| **DNS port** | Port the redirected DNS queries land on. The three ports must differ (1-65535). | 9053 |
| **Redirect** | *Every LAN device* or *Selected devices only*. | Every LAN device (an empty list) |
| **Devices** | The redirected devices by MAC address, with their names; **Add** and **x** (delete). About 55 devices fit; the counter shows the byte budget. | empty |
| **Apply** / **Discard** | Saves and restarts Tor and the firewall / reloads the page. | - |

**Limits and gotchas.**

- **Every LAN device** means the whole main LAN depends on Tor: while Tor is down or still connecting, those devices
  have no Internet, and nothing but TCP and DNS works for them at any time. The page asks before turning Tor on or
  widening to the whole LAN.
- *Selected devices only* with an empty list is refused: the router reads an empty list as every device.
- **IPv6.** A device selected by MAC address is redirected and filtered on IPv6 as well. An entry by IPv4 address or
  range (rc accepts them; the page keeps any present but adds MAC addresses only) does not cover that device's IPv6.
- NTP queries (UDP 123) from the redirected devices are redirected to the router.
- The device list is held in nvram and limited to about 1 KB (about 55 MAC addresses).
- Tor is not a VPN client: VPN Director and Policy Routing cannot target it.

### 4.21 Network: guest networks, VLANs and the Guest Portal

**What it is.** The **Network** page (menu *Network*; on a model without the Wi-Fi-per-network feature the menu reads
*Guest Network*) is a Reaper page (`Reaper_Network.asp`) with the functions and rules of the stock ASUS **Guest Network
Pro** editor, which it replaces in the menu. Each card on it
is one network: a Wi-Fi name (SSID) on chosen bands and AiMesh nodes, usually with its own subnet, bridge (`br5x`),
DHCP server and resolver, and optionally a VLAN tag, a VPN client, a schedule and a guest portal. The settings live
in the `sdn_rl`, `subnet_rl`, `vlan_rl`, `apgN_*` and `sdn_access_rl` NVRAM keys.

What is stock and what is Reaper's:

| Part | Owner |
|---|---|
| The network types, their settings and rules, what a save stores and which services it restarts, the portal pages | Stock ASUS behaviour, kept by the Reaper page: it stores the same settings in the same form, so a network made on the stock page is the same network here |
| The page itself: layout, dialogs, a refused value named under its field, the Wi-Fi share code | Reaper |
| **Guest isolation** (what a guest network may reach), its DNS rules, the VPN and policy-routing exits | Reaper (`rc/reaper_guest.c`) |
| Guest Portal DNS (Cloudflare for Families by default), the portal secret, the passcode checks | Reaper |
| mDNS across networks (the reflector), the Default IoT Network port fix, the VPN client switched on with its network | Reaper |
| No Wi-Fi key on screen after Apply; the Wi-Fi share sheet (code, name, key) with its own print button | Reaper |
| **Hold Wi-Fi restarts until Apply**, **Delete selected**, an Access Intranet / VPN / DNS / DHCP edit without a Wi-Fi restart | Reaper |
| The LAN-port (VLAN) assignment per AiMesh node | Stock logic, Reaper page (LAN > VLAN, 4.22.4) |

All supported models have this editor. The separate stock pages **Guest Network**, **Free WiFi** and **Captive
Portal** appear in the menu only on a model without it, so on Reaper's models the Guest Portal is a network type
on this page (4.21.7). The Network page and the LAN pages apply at once; they do not use the Apply-and-Keep
countdown of 2.7. Saving a network restarts Wi-Fi (`restart_wireless;restart_sdn N`), so wireless devices on every
network drop for a moment. Three exceptions: an edit that changes only Access Intranet, the VPN binding / Kill Switch or
the network's DNS / DHCP settings restarts no radio (4.21.2); with **Hold Wi-Fi restarts until Apply** on, several
changes share one restart (4.21.12); and **Delete selected** removes several networks with one restart (4.21.12).

#### 4.21.1 The page and the network types

The page shows one card per network: its name, its connection types (wired, Wi-Fi, Wi-Fi 7), tags (**VPN Client**,
**VPN Server**, **Free WiFi**, **Message Board**, a countdown for one-time access) and an on/off switch. Clicking a
card opens its editor beside the list; **Add a Network** opens the type list, each type with its description.
The model sets the maximum number of networks; when it is reached the page says *Your rules have reached the
maximum*.

If the router has no **main network** card yet (a router still in its factory state), a Reaper notice at the top
points to **Set up this router** (2.3); the main network is created at the first boot after that setup.

| Type | Made for | What the wizard sets by default |
|---|---|---|
| **Guest Network** | Visitors | Own subnet; **AP Isolation on** (Wi-Fi only); **WiFi Scheduling on**, with *Scheduled* or *One Time Access*; no intranet access |
| **Kid's Network** | Children's devices | Own subnet; WiFi Scheduling on; no intranet access; where the model offers it, **Portal Type** preselected to **Message Board** (choose None for no page) |
| **IoT Network** | Cameras, speakers, plugs | **Use same subnet as main network: on**; 2.4 GHz only; optional *Sync to all AiMesh node(s)* (the Default IoT Network, 4.21.5) |
| **VPN Network** | Devices that must leave by a VPN | Own subnet; **Access Intranet to the Main Network on**; a VPN client with its Kill Switch on |
| **Multi-Link Operation (MLO)** | Wi-Fi 7 devices | An MLO network over at least two bands; see 2.8 |
| **Customized Network** | Anything else | Own subnet; every switch off |
| **Guest Portal** | Walk-in guests | Own subnet; **AP Isolation** on (Wi-Fi only); a sign-in page (4.21.7). Not on BQ16 / BQ16 Pro |
| **Employee**, **Scheduled Network** | Offices | Only on ASUS business models |

The type only chooses the starting values. After creation every network has the same editor; the type is shown
as the card's title and decides which extra tabs appear (Portal for Guest Portal and, with a Message Board, Kid's
Network).

**How to use it: add a network.**

1. **Network > Add a Network**, pick the type.
2. Enter the **Network Name (SSID)** and, unless the type allows Open, the **Network Password**.
3. Open **More Config** for the Wi-Fi band, the AiMesh nodes, the schedule, the bandwidth limiter and *Use same
   subnet as main network*.
4. **Apply**. Wi-Fi restarts; the new card appears. The router builds the bridge, its DHCP server and resolver, and
   re-applies guest isolation, Gatekeeper (4.2.5) and mDNS for every network.
5. Open the card to set what the wizard does not ask: Access Intranet, DNS, IPv6, MAC filter, VPN (4.21.2).

#### 4.21.2 The network editor: every setting

The editor has the tabs **Network**, **VPN**, **Clients** and, where it applies, **Portal**. The Network tab has
three sections: **General**, **Advanced Settings** and **AiMesh**.

**General**

| Setting | What it does | Default |
|---|---|---|
| **WiFi7 Mode** | Wi-Fi 7 (802.11be) for this SSID. On requires WPA2/WPA3-Personal or WPA3 (or the Enterprise equivalents); choosing another method turns it off, with a warning | Per type |
| **MLO Fronthaul for Clients** | Main network on MLO models: offer MLO to clients on this SSID | Off |
| **Network Name (SSID)** | The Wi-Fi name, up to 32 characters, no `"` | - |
| **WiFi Band** | 2.4 / 5 / 6 GHz combinations, or **None**: a wired-only network (no SSID; the Wi-Fi rows hide). The main network has band check boxes instead | 2.4 + 5 GHz (IoT: 2.4 GHz) |
| **Security** | Guest and Guest Portal: **Open** or **Password**. Main network: Open, Password or **RADIUS Setting** (Enterprise) | Password (Guest Portal: Open) |
| **Authentication Method** | WPA2-Personal, WPA/WPA2-Personal, WPA2/WPA3-Personal, WPA3-Personal. 6 GHz: WPA3-Personal only. MLO: WPA2/WPA3 or WPA3. RADIUS: WPA2-, WPA/WPA2-, WPA2/WPA3-, WPA3-Enterprise and WPA3-Enterprise 192-bit | WPA2-Personal; 6 GHz WPA3-Personal |
| **WPA Encryption** | AES, TKIP, TKIP+AES, AES+GCMP256, Suite B (as the method allows) | AES |
| **Network Password** | 8 to 63 characters, or 64 hex digits; no spaces | - |
| **Server IP Address / Server Port / Connection Secret** | The RADIUS server, with Enterprise security | - |
| **WiFi Share** (button at the top of the editor) | The code a phone scans to join, with the network name and key, and a Free WiFi passcode if one is set. **Print the WiFi quick connect sheet** prints it; **QR Code (PNG)** saves the code. Not offered for an Enterprise or wired-only network, or while the schedule holds the SSID off | - |
| **Bandwidth Limiter** | Download and upload caps in Mb/s for the whole network. Turning it on **turns hardware acceleration off** (the page asks first). Not offered on IoT, Default IoT, main or portal networks | Off |
| **Access Intranet** | Which other networks this one may reach: **Main Network** and each network that has its own subnet (`SSID (VLAN n)`). See 4.21.3 | Unticked, except VPN Network (Main Network ticked) |
| **Reach these main-network devices** | Router mode; a network with its own subnet that is not a Guest Portal and does not have Main Network ticked in Access Intranet. Lists the main-network devices with a reserved address (LAN > DHCP Server, Manual Assignment on) by Name, else Hostname, with their address. AiMesh nodes and the router are never listed. Guests may open connections to the ticked devices only; those devices cannot open connections to the guests. At most 16. A ticked device whose reservation was removed shows *no reserved address* and is skipped until unticked. See 4.21.3 | None |
| **Device discovery with the main network** | Same conditions. On: pick **Printing**, **AirPlay**, **Google Cast**, **HomeKit / Matter**, **Spotify / Sonos** and/or **Other service types** (`_name._tcp` / `_name._udp`, separated by commas; at most 16 service types in all). Switching on starts with Printing, AirPlay and Google Cast. Devices of those kinds show up between this network and the main network in both directions; never between two guest networks; the router's own names are not announced here. Not available while **AP Isolation** is on. Discovery only shows devices: to use one, tick it in the list above. See 4.21.8 | Off |
| **WiFi Scheduling** | When the SSID is on. **Scheduled**: weekly time slots. **One Time Access** (Guest Network): the SSID runs for a set time (2 hours preselected, quick choices or Custom) and the card counts down | Guest and Kid's: on; others off |
| **Enable MAC Filter** | **Disable**, **Accept** (only listed devices may join) or **Reject** (listed devices may not), with a MAC list | Disable |

The setup wizards do not offer **Reach these main-network devices** or **Device discovery**; set them after the network is created. A save that changes only these two applies them without restarting Wi-Fi.

A save that changes only **Access Intranet**, the **VPN** tab (client, server, Kill Switch, and a client switched on
with it), or the network's **DHCP** pool, lease time, reservations or **DNS Server** (IPv4 and IPv6 servers,
encrypted DNS) also restarts no radio: only that network's own services (DHCP / DNS server, routing, VPN and the
Access Intranet rules of every network) are restarted, and Wi-Fi devices stay connected. Anything else in the same
save - SSID, password, bands, schedule, AP Isolation, the Bandwidth Limiter, LAN IP or mask, VLAN ID, IPv6 on / off,
the portal - restarts Wi-Fi as before.

The stock **AdGuard** switch is not shipped (Reaper removed the ASUS cloud DNS service); use Wallguard (4.3.3)
instead.

**Advanced Settings** (router mode; only for a network with its own subnet)

| Setting | What it does | Default |
|---|---|---|
| **Enable the DHCP Server** | The network's own DHCP server | As the main LAN when created |
| **LAN IP** | The router's address on this network; the network is the subnet around it. The pool is `.1`-`.254` of a new /24 | Picked by the router |
| **Subnet Mask** | 255.255.255.0 (253 clients) down to 255.255.255.240 (13 clients) | The main LAN's |
| **Lease time** | Seconds, 120 to 604800 | The main LAN's when created |
| **Manually Assigned IP around the DHCP list** | Reservations for this network: MAC, address inside the pool, optional DNS server and host name (the device's DNS name on this network) | Empty |
| **VLAN ID** | The 802.1Q tag of the network, 3 to 4093. **Assign** opens the VLAN profiles (4.22.4) | Picked by the router |
| **Hide SSID** | The SSID is not broadcast; devices must enter it by hand | Off |
| **DNS Server** | **Default** (the router's resolver for this network) or **Assign**: a provider from the list or two addresses. See 4.21.6 | Copied from the main LAN's *Handed to clients* servers (4.22.2) when the network is created; empty = Default |
| **AP Isolation** | Wi-Fi devices on this SSID cannot reach each other. While it is on, **Isolate** picks what else it keeps apart: **Wi-Fi only** - wired devices on the network stay reachable unless its VLAN profile sets **Port Isolation** (4.22.4); **Wi-Fi and LAN ports** - the network's LAN ports are kept apart too, from each other and from Wi-Fi (devices behind one external switch still reach each other; the uplink port, VLAN trunk ports and a port with an AiMesh node behind it are never isolated). On a guest network the trunk to AiMesh nodes keeps the firmware's own isolation with either choice, so Wi-Fi guests on different nodes stay apart. On a Reaper AiMesh node the choice does not apply: the node keeps the firmware's own behaviour (on 3006.102.10 that isolates its wired LAN ports too while AP Isolation is on), never less isolation than stock. On models whose LAN ports partly sit behind an external switch chip (the GT-BE98 Pro, and the GT-BE98 on the test line), isolation between the ports behind that chip is left as the firmware sets it: with **Wi-Fi only**, devices on those ports may not reach each other while AP Isolation is on (they still reach the router, the internet, Wi-Fi and the other LAN ports). The main network's choice covers every network on the main subnet; a network with its own subnet keeps its own. Switched off, the choice is kept for the next time. Also keeps the network out of the mDNS reflector (4.21.8) | Guest and Guest Portal: on; **Isolate**: Wi-Fi only |
| **IPv6** | IPv6 for this network: **Auto Configuration Setting** *Auto* (SLAAC) or *Stateful* (DHCPv6), the pool's first and last host part (up to 4 hex digits), up to three IPv6 DNS servers. Reaper keeps these on screen for a wired-only network (WiFi Band None), where stock hid them | Off |

**AiMesh**: the router and each node, with a tick for the nodes that broadcast this SSID and the bands each can
carry. A node whose bands are full for SSIDs cannot take another network; older nodes cannot sync every band.

**VPN tab** (router mode, not for a network on the main subnet): **VPN** on/off; a list of **VPN Client** profiles
(`OVPN1..5`, `WG1..5`) and, if any, the router's own **VPN Server** profiles; **VPN Client Kill Switch**; **Go Setting**
opens the VPN client or VPN server page. On the 102.8 firmware line (GT-BE98, GT-BE19000, BQ16, BQ16 Pro) the tab follows
that line's stock page: there is no Kill Switch control, and the tab is also shown for a network on the main subnet.
See 4.21.4.

**Clients tab**: the devices online on this network, each marked wired or wireless, with its MAC and IP address.

**Portal tab**: 4.21.7.

**Delete** (the button at the top of the editor) removes the network.

#### 4.21.3 What a guest network may reach (guest isolation)

Reaper's rule: **a guest or Guest Portal network never reaches devices on non-guest networks or the router's own
features.** It reaches the internet (or its VPN client) and the router only for DHCP and DNS. That holds on every
path, including while its VPN tunnel is down: there is no fallback onto the main LAN.

Which networks are isolated:

| Network | Isolated by Reaper |
|---|---|
| A network with its own subnet and **Main Network not ticked** in Access Intranet (Guest, Kid's, Customized, an IoT network with its own subnet, a VLAN-only network from 4.22.4) | **Yes** |
| Two such networks **ticked in each other's** Access Intranet list | **Yes, both**: their devices reach each other, and nothing else changes for either (below) |
| A **Guest Portal** network (and a Kid's Network with a **Message Board**), whatever Access Intranet says | **Yes** |
| A network with its own subnet and **Main Network ticked** in Access Intranet | No: treated as part of your own network |
| A network with **Use same subnet as main network** on (the IoT wizard's default, the Default IoT Network) | No: its devices are on the main LAN |
| The main network | Never |

What an isolated network gets, IPv4 and IPv6 (rules `REAPER_GUI` for the router, `REAPER_GUF` for forwarding;
deny-only, so the stock rules, Gatekeeper and the firewall still decide what they let through):

| Direction | Allowed | Dropped |
|---|---|---|
| To the router | DHCP (UDP 67 / 547), DNS (port 53) to the network's own gateway address, IPv6 neighbour discovery, replies to connections the router started, the redirects the router itself made (Gatekeeper's waiting room, DNS Director), AiMesh nodes; a portal also its sign-in ports; mDNS (UDP 5353, IPv4) while **Device discovery** is on | Everything else on every router address: the web interface, SSH, ping, NTP, mDNS (unless Device discovery is on), the encrypted DNS server |
| Out through the router | The WAN; the network's bound VPN client; a VPN client that VPN Director, an OpenVPN *redirect all* client or a Policy Routing rule sends it to (4.21.4); DNS queries DNS Director redirected (port 53 only); the main-network devices ticked in **Reach these main-network devices** (new connections from the guest only) | The main LAN, every other guest network, the router's VPN clients it is not routed to |
| Into the network | Replies; port forwards from the WAN; connections from clients of the router's **own** WireGuard / OpenVPN server (the server's own access setting still decides); with the Firewall switch **Zone policies may open one-way paths from the main network into isolated guest networks** on, connections an Accept zone policy from the main network allows (4.1.5) | Everything from the main LAN and from other networks |

Consequences an owner meets:

- **A printer, NAS or Chromecast on the main LAN** is unreachable from an isolated network until you open it: tick
  the device in **Reach these main-network devices** (it needs a DHCP reservation), and turn on **Device discovery**
  for that kind of device so the guest network sees it (4.21.8). Or tick Main Network in Access Intranet, and the
  network is then not isolated.
- **No switch opens** the router's pages, SSH or services, another guest network, or the WAN while the network's VPN
  is down. Caveat: a ticked device that itself routes or proxies traffic gives the guests a way around the network's
  VPN Kill Switch - pick devices, not gateways.
- **A DNS server on the main LAN cannot be set as the network's DNS Server** (4.21.6): the guests cannot reach it.
  Use DNS Director's row for the network instead (4.22.2); a redirected query on port 53 passes.
- **Linking two guest networks (from the image after v3.8.0).** Ticking another network (not Main Network) in
  Access Intranet links exactly those two: a device on either can open connections to a device on the other. Both
  stay isolated from the main LAN and from the router's own services, keep their own DNS and VPN rules, and stay
  out of mDNS relaying. A link to a network that itself has Main Network ticked is not honoured (that network holds
  your own devices). Before this, any tick took both networks out of guest isolation altogether: they got the
  router's pages and main-LAN names back. If you relied on that, tick **Main Network** for the network instead.
- **A Guest Portal with Main Network ticked** reaches the **main LAN only**: never another guest network, never
  the router, and nothing on the main LAN can open a connection into the portal. A portal ticked together with
  any other network gets nothing from that tick (from the image after v3.8.0; before, it opened the main LAN to
  the portal's guests).
- **AP Isolation** is a different control: it stops Wi-Fi devices on the same SSID reaching each other. With
  **Wi-Fi only** (the default) wired devices stay reachable: on the main network (from the image after v3.8.2), and
  on a guest network unless its VLAN profile sets Port Isolation (4.22.4). With **Wi-Fi and LAN ports** (from the
  image after v3.8.2) the network's LAN ports are kept apart too, from each other and from Wi-Fi; devices behind one
  external switch still reach each other, and AiMesh backhaul ports are never isolated. Isolation between networks
  works without it.
- Saving any network, a firewall restart and every VPN Director change rebuild the rules; existing connections from
  the network are dropped so that they meet the new rules. A rule the kernel refuses is logged as
  `guest isolation: N rule(s) refused`. The generated script is `/tmp/rguest/apply.sh`.

Checking it over SSH:

```
iptables -nvL REAPER_GUF | head -40     # per-network forward rules
iptables -nvL REAPER_GUI | head -40     # per-network rules to the router
grep '^#' /tmp/rguest/apply.sh          # one comment line per isolated network and its exits
```

#### 4.21.4 A network that uses a VPN

**Binding a network to a VPN client** (VPN tab): every device on the network leaves by that client. The clients
are defined on the VPN pages (4.20 VPN); the list shows `OVPNn` and `WGn` profiles. Reaper behaviour:

- **Choosing a client switches it on** with the same save (v3.7.8). A WireGuard client is started when the network
  is applied; taking the binding away never switches a client off.
- **The Kill Switch starts on** for a new binding (Reaper; a saved network keeps its own setting). On: the network
  leaves **only** by the tunnel, IPv4 and IPv6; while the tunnel is down it has no internet. Off: it leaves by the
  tunnel while it is up and by the WAN while it is down. **Neither** falls back onto the main LAN.
- IPv6 of a bound network goes into the tunnel (v3.7.9), as does its DNS: a bound network uses the tunnel's DNS
  servers, and they are rebuilt when a WireGuard tunnel reconnects by itself.
- The Kill Switch can only be switched on with a VPN **client** selected; with a VPN Server profile the page refuses.
- A VPN Network (wizard) has **Access Intranet to Main Network ticked**, so Reaper does not isolate it (4.21.3).
  Untick it for a VPN network guests use.

**Routing a network into a VPN without binding it (v3.8.0).** A guest network that VPN Director (4.20 VPN) or an
OpenVPN client set to *redirect all* traffic sends into a tunnel reaches the internet through it. Reaper reads, at
every firewall build and network change:

- each enabled VPN Director rule whose target is `OVPN1..5` (only while that client is in VPN Director mode) or
  `WGC1..5`, and whose source is empty / `0.0.0.0` or overlaps the network's IPv4 subnet; the exit keeps the rule's
  own source and destination;
- each OpenVPN client with *redirect all* (`vpn_clientN_rgw` `1`);
- Policy Routing rules (4.4) that send the network's devices to a VPN client.

Not on a Guest Portal network, and not on a network whose Kill Switch is on (it keeps its bound client only).
Changing VPN Director's rules re-applies isolation at once. IPv4 only, as VPN Director is.

**How to use it: a network that leaves by WireGuard.**

1. Set up and test the WireGuard client (4.20 VPN).
2. **Network > Add a Network > VPN Network** (or open an existing network, **VPN** tab).
3. Switch **VPN** on, pick `WGn`, leave **VPN Client Kill Switch** on. For a guest network, untick **Main Network**
   under Access Intranet.
4. **Apply**. The client starts if it was off.
5. Check from a device on the network that its public address is the VPN's.

A network bound to a VPN client keeps its routing through a WAN reconnect: from the image after v3.8.2 the
router puts the network's VPN routing rules back as soon as the WAN routes are rebuilt (before, the network
left by the WAN until the VPN client restarted, unless its Kill Switch held it).

**Example: one guest VLAN through OpenVPN by VPN Director.** Guest network `198.51.100.0/24`, OpenVPN client 1 in
VPN Director mode, rule *enabled, source `198.51.100.0/24`, target OVPN1*. The guest network leaves by `tun11`; the
main LAN stays closed to it. With the network's own Kill Switch on, only a binding counts and the rule is ignored by
the isolation layer.

#### 4.21.5 IoT networks and the Default IoT Network

The IoT wizard starts with **Use same subnet as main network on**: its devices get main-LAN addresses and **can
reach your computers**. That suits smart-home devices an app on your phone must find. To fence them off, switch it
**off**: the network gets its own subnet and Reaper isolates it.

**Sync to all AiMesh node(s)** (IoT wizard, AiMesh models) makes the network the **Default IoT Network**
(`sdn_name` `LEGACY`): one 2.4 + 5 GHz SSID on every node, with no AiMesh section in its editor. Only one may exist.
Its LAN ports are assigned on LAN > VLAN (Access mode, 4.22.4). **From v3.8.0, editing the Default IoT Network on
this page keeps its per-node LAN-port rows**; earlier an edit reset them to *All (Default)*.

**How to use it: an IoT network that cannot reach the PCs.**

1. **Add a Network > IoT Network**. Name it, set a password.
2. Switch **Use same subnet as main network** off. Leave the band at 2.4 GHz unless the devices support 5 GHz.
3. **Apply**. Open the card: leave **Access Intranet** unticked. Optionally switch **AP Isolation** on
   so the Wi-Fi devices cannot reach each other either.
4. Join the devices. They reach the internet and nothing on the main LAN; the phone app controls them through the
   vendor's cloud. For a device the phone must reach directly (casting, a local hub), use the main network instead.
5. Optionally give the network a Wallguard profile (4.3.3.5).

#### 4.21.6 DNS for a network

Each network with its own subnet has its own resolver (a dnsmasq instance on its gateway address) with Dreadwatch,
Wallguard and the encrypted-DNS block in it, as on the main LAN.

| Situation | What devices use for DNS |
|---|---|
| **DNS Server** = Default | The network's gateway (its resolver). Encrypted DNS is offered by DHCP option 162 only where the network may reach the router for it: not on an isolated network and not on a portal (4.3.4.5). To have it offered on a guest network, tick **Main Network** in Access Intranet (the network then counts as part of your own network, 4.21.3); **Reach these main-network devices** and **Device discovery** do not change this |
| **DNS Server** = assigned addresses | Those addresses are handed out by DHCP, and no encrypted DNS is offered: option 162 would name the router, which is not this network's DNS server. On an isolated network an address on the main LAN is unreachable (4.21.3) |
| Network bound to a VPN client | The tunnel's DNS |
| **Guest Portal** network | Always the network's own resolver: a hand-set DNS server on the device is redirected to it and DNS-over-TLS (port 853) is dropped. The **DNS Server** setting picks the resolver's upstream (below) |
| DNS Director row for the network (LAN > DNS) | Forced to the chosen resolver (4.22.2) |

**Names.** The resolver of an isolated network or a portal does not read the router's host list
(`no-hosts`): guests cannot look up the main LAN's reservation names. A network with Main Network ticked in Access Intranet keeps them.
Reverse names between the main LAN and VLANs: 4.14b.

**Guest Portal upstream (Reaper).** On a portal network without a VPN binding, the DNS Server setting decides where
guest lookups go after the router's own filters:

| DNS Server | Upstream |
|---|---|
| Empty (Default) | **Cloudflare for Families** (`1.1.1.3`, `1.0.0.3`) over DNS-over-TLS: malware and adult content blocked |
| Every address a known provider (Cloudflare, Quad9, Google, CleanBrowsing, Control D, CIRA Canadian Shield) | Those providers over DNS-over-TLS |
| At least one other address (for example your own resolver) | Plain DNS to the address(es) set |

The certificate is checked once the router's clock is set. A portal bound to a VPN uses the tunnel's DNS. The
editor shows this rule under the DNS Server row of a portal network.

#### 4.21.7 The Guest Portal

**What it is.** A network whose devices see a sign-in page before they get the internet (the stock captive portal,
`chilli`). Reaper's models offer the **Free WiFi** portal type and, on the Kid's Network, the **Message Board**.
**BQ16 and BQ16 Pro have no captive portal**: the type is not offered. The wizard type is shown only in router (or
WISP) mode and only when the model reports portal support (`captivePortal` and `cp_freewifi`).

**Portal tab settings (Free WiFi)**

| Setting | What it does | Default |
|---|---|---|
| **Portal Type** | **None** (no portal) or **Free WiFi**. Each portal type serves one network; a type in use is marked *(Used)*, and only one type can be active at a time | Free WiFi (Guest Portal) |
| **Brand Name** | The title on the sign-in page, up to 40 characters | - |
| Background image | **Modify** opens the picture list: one of the bundled pictures, or your own JPG, PNG or SVG, up to 10 MB (2 MB after it is scaled) | Stock image |
| **Connection Timeout** (minutes) | The guest's session time; when it expires, the connection is cut and the guest signs in again | 60 |
| **Landing Page (Redirect to your website)** | Where the guest is sent after signing in, up to 256 characters. Empty: the success page | Empty |
| **Add your own Passcode** / **Passcode** | Guests must enter this code. Up to **15** characters, printable ASCII, no spaces, no `<` or `>` | Off |
| **Add your own Terms of Service** / **Terms of Service** | A tick box the guest must accept, with your text (up to 5120 characters; a template is filled in) | On |

**Message Board** (Kid's Network, where offered): **Description** (up to 80 characters) and a background image,
shown on a page before the device gets the internet. A network with a Message Board is treated as a portal by guest
isolation.

**What Reaper adds and changes**

- The passcode can be set **in the wizard**, not only on the Portal tab afterwards (v3.7.6), and a passcode longer
  than 15 characters is refused at Apply (longer ones never signed in).
- **The passcode is matched by the portal network's subnet (v3.8.0)**, so a correct passcode and the terms page are
  accepted on every subnet size.
- Each router makes its own **portal secret** the first time a portal starts (stock used one public value on every
  router); it is never shown (8.2).
- The portal network is **exempt from Gatekeeper** (4.2.5): its sign-in page is its gate.
- Isolation: guests reach the internet and the router's DHCP, DNS and sign-in ports only; **IPv6 gets nothing** on
  a portal (the portal is IPv4-only); Access Intranet opens the main LAN only (4.21.3). VPN Director routing does
  not apply to a portal; a VPN binding does.
- Guest DNS: 4.21.6.
- The Traffic Analyzer's Live tab has a Guest Portal panel with each guest's speed and session time (4.7).
- The portal starts and stops with its network, and a saved change is applied even on a router with AiMesh, where
  stock built nothing until a reboot (v3.7.7).

**How to use it: a Guest Portal with a passcode.**

1. **Network > Add a Network > Guest Portal**.
2. **Network Name**: for example `Cafe-Guest`. Security stays **Open**: the portal is the gate.
3. **Portal Type**: Free WiFi. Enter the **Brand Name**; upload a background if wanted.
4. Switch **Add your own Passcode** on and enter the code (15 characters at most).
5. Keep or edit the **Terms of Service**; set **Connection Timeout** (for example 120 minutes).
6. **Apply**. Join from a phone: the *Sign in to network* sheet opens; accept the terms, enter the code.
7. Optional: the network's **DNS Server** picks the guests' filter (4.21.6); a Wallguard profile adds ad blocking.

**Limits and gotchas**

- One Free WiFi network per router.
- **The portal restarts itself (v3.8.2).** When a Guest Portal network is on and its portal process has died, the
  watchdog starts it again after two missed checks a minute apart, at most three times per boot, with one log line
  each time (`watchdog: a Guest Portal network is on and its portal is not running - starting it (N of 3 this
  boot)`). Past three, it stays down until the next reboot or a save of the network; section 4d of the diagnostics
  report counts the restarts.
- The portal is IPv4 only; guests' devices get no IPv6 on a portal network.
- A portal guest cannot use its own DNS-over-TLS; a browser with DNS-over-HTTPS to an outside provider still works
  through the internet (the encrypted-DNS block of 4.3.4.6 covers that).

#### 4.21.8 mDNS across networks

Casting, AirPlay and printer discovery use mDNS, which does not cross networks by itself. With **mDNS across
networks** on (Administration > Tweaks, `reaper_mdns_reflect` `1`, the default; 8.2), the router relays mDNS between:

- the main network, and
- every network with **Main Network** ticked in Access Intranet (its devices are main-network devices on another
  SSID),

leaving out any network with **AP Isolation** on (the main network too, if a radio has it on), every
isolated network and every Guest Portal. On isolated networks and portals the router no longer answers mDNS at all.
A relayed announcement never goes back to the network it came from. The system log lists the left-out bridges with
the reason (for example `br54 AP isolated, br55 no intranet access`).

**Only chosen kinds of devices** (v3.8.4; Administration > Tweaks, under mDNS across networks; off at
factory, `reaper_mdns_types` empty; 8.2). Off: every kind of device is relayed between the networks above, as before.
On: only the kinds you tick (Printing, AirPlay, Google Cast, HomeKit / Matter, Spotify / Sonos) and the service types
you enter (such as `_ipp._tcp`, at most 16 in total) are relayed between the main network and the Access Intranet
networks - the same filter as Device discovery below: a service's announcements, its name records, and a device's
address only when a relayed service of a chosen type names it; nothing else crosses. Each network still sees all of
its own devices. The router's own name and services are announced as before, and a guest network's Device discovery
keeps its own choice on the Network page. The system log says which types are relayed (`mdns: across the main side
only these service types are relayed: ...`).

**Device discovery with the main network** (from the image after v3.8.2; per network, off by default) relays only
chosen service types between the main network and one isolated guest network, without Access Intranet. Phones and
computers on that network find the main network's devices of the types you pick (Printing, AirPlay, Google Cast,
HomeKit / Matter, Spotify / Sonos, or your own entries), and main-network devices find the same kinds of device on
that network. It is a star: the main network and that network only, never one guest network to another. Only the
picked types cross, in both directions; a device's name and address cross only for a service of a picked type. The
router's own name and services are not announced on that network, and a device there cannot take over the name of
a main-network device that has announced itself recently. Discovery is not access: a guest device can open a
connection to a main device only if that device is ticked in **Reach these main-network devices** (4.21.2). IPv4
only; not available while **AP Isolation** is on; **mDNS across networks** off turns it off too.

To cast from a guest network to a TV on the main LAN while keeping the network isolated: turn on Device discovery
with **Google Cast** or **AirPlay** and tick the TV under Reach these main-network devices. Ticking Main Network in
Access Intranet also works, but the network is then no longer isolated.

#### 4.21.9 How the other features treat guest networks

| Feature | On guest networks | See |
|---|---|---|
| Gatekeeper | Enforced on every network except a Guest Portal | 4.2.5 |
| Wallguard | A network can have its own profile; a device rule beats it | 4.3.3.5 |
| Dreadwatch, Warden | Every network's resolver and the shared firewall chains | 4.3.1, 4.3.2 |
| Encrypted DNS server | Answers on each guest/VLAN address; not offered by DHCP on isolated networks or portals | 4.3.4.5 |
| DNS Director | One row per network on LAN > DNS; the global mode does not cover a network whose row is *No redirection* | 4.22.2 |
| Policy Routing / VPN Director | Exits honoured by isolation (4.21.4) | 4.4, 4.20 VPN |
| Device names | Hostnames from the network's DHCP; reverse names between the main LAN and VLANs | 4.8.1, 4.14b |

#### 4.21.10 Examples

**A guest Wi-Fi for visitors.**

1. **Add a Network > Guest Network**. Name `Home-Guest`, Security **Password**, a password you can read out.
2. **WiFi Scheduling**: on, **One Time Access**, 4 hours, for an evening; or **Scheduled** for regular hours.
3. **Apply**. **WiFi Share** in the network's editor shows the QR code and prints the quick connect sheet for visitors.
4. Leave Access Intranet unticked and **AP Isolation** on: visitors reach the internet and nothing else.

**A kids' network with a schedule.**

1. **Add a Network > Kid's Network**. Name, password.
2. **WiFi Scheduling** is on: set the weekly hours (for example school days 07:00 to 21:00).
3. **Apply**. Outside those hours the SSID is off.
4. For content filtering: Wallguard profile with safe search (4.3.3.6), or DNS Director's row for the network set to
   a family filter (4.22.2).
5. Note: the network is isolated; a printer on the main LAN is not reachable unless you tick Main Network.

**A wired-only VLAN for a switch port.** Add a **Customized Network**, **WiFi Band: None**, then assign the LAN port
on LAN > VLAN in Access mode (4.22.4). The IPv6 switch stays available on a wired-only network.

#### 4.21.11 Limits and gotchas

- **IoT wizard default.** *Use same subnet as main network* is on; such an IoT network is not separated from your
  PCs (4.21.5).
- **VPN Network default.** Access Intranet to the main network is ticked; the network is not isolated (4.21.4).
- **Bandwidth Limiter** turns the router's hardware acceleration off (the page asks first); flows then run on the
  CPU (4.9 shows the split).
- **A new network copies the main LAN's DHCP DNS servers** (LAN > DNS > *Handed to clients*) into its own DNS Server
  setting. If those name a resolver on the main LAN, an isolated network cannot reach it: set the network's DNS
  Server back to Default.
- **Kid's Network with a Message Board** is a portal network for isolation: no IPv6, no Access Intranet beyond the
  main LAN (4.21.7).
- **Wi-Fi restarts on most saves** on this page; wireless devices on all networks reconnect. Access Intranet / VPN /
  DNS / DHCP-only edits do not (4.21.2), and **Hold Wi-Fi restarts until Apply** lets several changes share one
  restart (4.21.12).
- **A network on the main subnet** has no Advanced address settings, no VPN tab and no Access Intranet: it is the
  main LAN on another SSID.
- **MLO**: one active MLO network at most (the model's limit), at least two bands; power-cycle after switching MLO
  (2.8).
- **6 GHz** requires WPA3-Personal; a network on 6 GHz with an older device must also offer 2.4 or 5 GHz.
- **IPv4 only** for VPN Director exits and for the portal.
- The LAN page refuses a main LAN address that overlaps a guest network's subnet (4.22.1).

#### 4.21.12 Several changes, one Wi-Fi restart

**Hold Wi-Fi restarts until Apply.** A switch at the top of the Network page (and of the MLO page), off at factory
(`reaper_sdn_defer` `0`; kept in the settings backup). On:

- A network you **create**, **edit** or **switch on** is saved at once, but the Wi-Fi restart waits. The card shows
  **Waiting**, and a bar at the top lists the waiting networks (*new*, *edited*, *switched on*) with **Apply now**.
  **Apply now** restarts Wi-Fi once for all of them; the AiMesh nodes receive all the waiting settings in that one
  apply. Password and MAC-filter edits wait like the rest.
- Anything that has to run at once still runs at once and takes the waiting changes with it: **switching a network
  off**, **deleting** one, a change that needs the LAN ports restarted (a bound LAN port or VLAN trunk), a Guest
  Portal change, or a save with a restart on any other page. A network switched off or deleted is never left
  broadcasting without its guest isolation.
- While changes wait, the dashboard shows **Network changes are waiting for Apply** with a link to the Network page.
- If something else restarts Wi-Fi meanwhile (the Wireless page, an AiMesh node, a script), the router finishes the
  waiting networks' DHCP / DNS / firewall setup by itself afterwards. With AiMesh nodes the networks stay listed as
  waiting until **Apply now** (or the next change that runs at once): the nodes receive the waiting settings only then.
- Nothing waiting is lost by a reboot: a reboot applies everything saved. There is no Discard: the settings are
  already stored; to undo one, edit it back before **Apply now**.
- Switching the option off while changes wait applies them.

**Delete selected.** **Delete several** at the top of the page puts a tick box on every network that can be removed
this way; tick the networks and press **Delete selected**. The confirm names them; they are removed in one request
and Wi-Fi restarts once. The main network, the backhaul and a network with a bound LAN port or a VLAN while VLAN
trunks exist are not offered: delete those one at a time with the card's **Delete**. Delete selected always runs at
once and takes any waiting changes with it.

**Delete on a main network (v3.8.4).** The card's **Delete** keeps one main network that broadcasts: it refuses the
last main network with a name and bands, and the only main-network card. An empty main-network card (no name, no
bands — a Smart Connect change can leave one behind) can always be deleted. Saving a guest or other network
never removes a main network; only saving a main network on bands another main network uses replaces that one
(the stock Smart Connect rule). The confirm, and the notice that a main network must stay, are brought into view
when **Delete** is pressed on a card further down the page.

### 4.22 LAN

**What it is.** Four Reaper pages replace the stock LAN pages, saving the same NVRAM keys: **LAN** (`Reaper_LAN.asp`:
address, DHCP server, switch, multicast), **DNS** (`Reaper_DNS.asp`), **IPTV** (`Reaper_IPTV.asp`) and **VLAN**
(`Reaper_VLAN.asp`). Each page posts only the settings you changed, writes nothing on load, and restarts only what
the change needs; a change that drops connections asks first. A tab that did not load says so, and Apply then leaves
its settings unchanged. The stock **Multi-subnet** page (`Advanced_MultiSubnet_Content.asp`) appears only on models
with ASUS's tag-based VLAN feature; none of Reaper's models has it.

#### 4.22.1 LAN IP and DHCP server

**LAN** has four tabs: **Addressing**, **DHCP Server**, **Switch Control** and **Multicast** (a tab is hidden where
stock hid the page: Multicast in access point mode, for example).

**Addressing**

| Setting | What it does | Default |
|---|---|---|
| **Host Name** | The router's name on the LAN (letters, digits, `-` and `_`, at least two characters, not starting with `-` or `_`). Devices reach it as *name* or *name.domain* | - |
| **Router's Domain Name** | Optional. Appended to device names handed out by DHCP, e.g. `laptop.home.arpa`. One field (stock had two) | Empty |
| **Get LAN IP Automatically?** | Access point mode only: on takes the address from the main router; off uses the fields below | - |
| **IP Address** | The router's own LAN address. Changing it moves every device to the new subnet | `192.168.50.1` |
| **Subnet Mask** | /1 to /30 | `255.255.255.0` |
| **Default Gateway**, **Connect to DNS Server automatically**, **DNS Server1/2** | Access point mode only: the main router's address and DNS | - |

A new LAN address recomputes the DHCP pool (network + 2 to broadcast - 1) and the page shows where it moves. Apply
then lists what still points at the old subnet (reservations, port forwards, static routes, DMZ, VPN Fusion rules),
asks, restarts the network (about 35 seconds without connection) and reopens the page at the new address. Changing
the host name or domain restarts only the services that use them (and regenerates the router's self-signed
certificate). The page refuses an address that overlaps the WAN (both WANs with Dual WAN) or any guest network's
subnet.

**DHCP Server**

| Setting | What it does | Default |
|---|---|---|
| **Enable the DHCP Server** | The main LAN's DHCP server. Off: devices get no address when their lease ends (the page warns) | On |
| **IP Pool Starting / Ending Address** | The range handed out. Must be inside the LAN subnet; a reversed pair is swapped; a pool outside the subnet's block is offered a correction | `192.168.50.2` - `192.168.50.254` |
| **Lease time** | Seconds, 120 to 604800 | `86400` (24 hours) |
| **Default Gateway** | Optional gateway handed to devices. Empty: the router | Empty |
| **Log DHCP and RA queries** | Off keeps every lease and router advertisement out of the system log (stock *Hide DHCP/RA queries*, shown the plain way round) | On (`dhcpd_querylog` `1`) |

The DNS and WINS servers handed to devices are on LAN > DNS (4.22.2). Changes here restart the DHCP / DNS service
only, not the network.

**Manual Assignment (DHCP reservations)**

| Setting | What it does | Default |
|---|---|---|
| **Enable Manual Assignment** | Reservations take effect only while this is on. Adding a reservation turns it (and the DHCP server) on | Off (`dhcp_static_x` `0`) |
| **MAC address** | The device. The field lists this LAN's connected devices that have no reservation yet (name and address); picking one fills the address | - |
| **IP Address** | Inside the LAN subnet; not the router's own address; not already reserved | - |
| **DNS (optional)** | A DNS server handed to this device only, IPv4 | Empty |
| **DNS name** | The device's **DNS name**: other devices reach it as *name* and *name.domain*, and Wallguard's `$client=` can use it. It is **not** the device's Name (4.8.1) and is never shown as one; the **Name** column beside it shows the Devices page name, read-only | Empty |

Up to **64** reservations; the counter shows the use. **Edit** puts a row back into the add fields; **Delete** asks
first when a VPN Fusion policy uses the address. **Export CSV** saves `dhcp_manual_list.csv`; **Import CSV** replaces
the whole list (columns MAC, IP, DNS, hostname; the first line is a header; every row is checked, and the import
stops at the first bad line with its number). The Devices page's **Pin IP** (4.8.2) writes into the same list.

**How to use it: a DHCP reservation.**

1. **LAN > LAN > DHCP Server**. In **Manual Assignment**, open the MAC list and pick the device (or type its MAC).
2. Enter the address, for example `192.168.50.20`. Prefer an address outside the pool; shrink the pool if needed.
3. Optional: a **DNS name** such as `nas`; the device is then `nas` and `nas.<domain>` for every device on the main LAN.
4. **Add**, then **Apply**. The device moves to the address at its next lease renewal (or reconnect).
5. To change what the pages *show* for it, rename it on the Devices page instead (4.8.1).

**Switch Control**

| Setting | What it does | Default |
|---|---|---|
| **Jumbo Frame** | Frames up to 9000 bytes on the LAN ports. Every device on the path must support them. Reboots the router. Hidden on models without it | Off |
| **Spanning Tree Protocol** | Stops loops when switches are cabled in a ring. Restarts the network for about 35 seconds | On (`lan_stp` `1`) |
| **Bonding / Link aggregation** | 802.3ad for one wired client on two ports (the page names them: LAN1 + LAN2 on RT-BE96U / BE88U / BE86U; a port pair choice on the GT-BE98 family; LAN4 + LAN5 on BQ16). Reboots | Off |

Bonding is refused, with the reason, while one of its ports is the Dual WAN LAN port, the IPTV set-top box port or
carries a guest-network VLAN, or while automatic WAN port detection is on (WAN Ports, 4.19).

**Multicast**

| Setting | What it does | Default |
|---|---|---|
| **Enable multicast routing** | The IGMP proxy, so LAN devices can join multicast streams from the WAN (IPTV) | Off |
| **Default IGMP version** | IGMP v1, v2 or v3 (shown with multicast routing on) | v3 |
| **Fast leave** | Stop a stream as soon as the last device leaves it | Off |
| **Enable efficient multicast forwarding (IGMP Snooping)** | Send multicast only to the Wi-Fi clients that asked for it | Off on the wired bridge (8.3) |
| **UDP Proxy (Udpxy)** | Port 1024 to 65535: relays multicast streams to devices as HTTP. 0 or empty: off | `0` |

An ISP profile on the IPTV page can fix some of these; the page then hides them and says so. With an IPTV set-top
box port in use, multicast routing is locked off (a hardware limit of the platform).

**Examples.** Renumber the LAN to `192.168.60.1/24`: set the address, Apply, read the list of rules still on the old
subnet, confirm; reconnect devices that kept a fixed address. Reserve a printer at `192.168.50.30` with DNS name
`printer`.

**Limits and gotchas**

- A reservation outside the LAN subnet does nothing; the Devices page's Network Ledger flags it (4.8.3).
- The reservation list is limited by NVRAM size; the counter and the ledger warn.
- A device with a private (randomized) MAC needs that feature off for this network before a reservation sticks.
- Guest networks have their own pools and reservations on the Network page (4.21.2).

#### 4.22.2 DNS

**DNS** has three tabs, by direction: **Router upstream** (what the router asks), **Handed to clients** (what DHCP
gives devices) and **DNS Director** (forced redirection). DNS changes restart DNS only, never the internet
connection. The status line shows *DoT* or *Plain DNS*, and DNS Director's mode when it is on. The encrypted DNS
server for devices and the blocking of DNS that goes around the router are on Bastion > Encrypted DNS (4.3.4).

**Router upstream: WAN DNS Setting** (one block per WAN; both with Dual WAN)

| Setting | What it does | Default |
|---|---|---|
| **Connect to DNS Server automatically** | Use the servers the ISP gives the WAN; the servers in use are shown beside it | On |
| **Preset** | Fills the two fields from a provider list | - |
| **DNS Server1 / DNS Server2** | Your own upstream servers (automatic off). A static WAN gets none from the ISP | Empty |

**Router upstream: Resolver**

| Setting | What it does | Default |
|---|---|---|
| **Forward local domain queries to upstream DNS** | Off answers names in the LAN domain locally and never asks the ISP about them | Off |
| **Enable DNS Rebind protection** | Drops answers that point public names at private addresses | Off |
| **Enable DNSSEC support** / **Validate unsigned DNSSEC replies** | Validate signed answers; a failed answer is dropped | Off / on |
| **Prevent client auto DoH** | *Auto* and *Yes* tell browsers to keep using the router's DNS instead of their own DNS-over-HTTPS | Auto |

**Router upstream: DNS-over-TLS** (the router's own upstream queries)

| Setting | What it does | Default |
|---|---|---|
| **Encrypt upstream DNS** | Queries go only to the servers in the list; the WAN DNS servers are not used while this is on | Off (`dnspriv_enable` `0`) |
| **DNS-over-TLS Profile** | **Strict** refuses a server whose certificate does not match; **Opportunistic** falls back to plain DNS | Strict |
| Server list | **IP Address**, **TLS Port** (empty = 853), **TLS Hostname**, **SPKI Fingerprint** (optional pin); **Preset servers** fills a row. At least one server when on | Empty |

**Handed to clients: DNS and WINS Server Setting** (main LAN DHCP)

| Setting | What it does | Default |
|---|---|---|
| **DNS Server 1 / 2** | What the DHCP server tells devices. Empty: the router itself, the usual choice. A device given another server bypasses the router's filtering | Empty |
| **Advertise router's IP in addition to user-specified DNS** | Also hand out the router after the servers above | On |
| **IPv6 DNS Server** | Handed out over DHCPv6 (shown with IPv6 on) | Empty |
| **WINS Server** | For old Windows name resolution | Empty |

With either DNS Server field set, the router does not offer its encrypted DNS by DHCP option 162 (4.3.4.5).

**DNS Director**

Forces devices' plain DNS (port 53) to a chosen resolver, whatever server the device is set to use (stock Merlin
feature; Reaper's page validates the custom servers, allows one rule per MAC, and writes the guest-network column into
a fresh read of `sdn_rl` so that a save never undoes a Network page change).

| Setting | What it does | Default |
|---|---|---|
| **Enable DNS Director** | The redirection on or off | Off (`dnsfilter_enable_x` `0`) |
| **Redirect to** (global) | The mode for every device without a rule: *No redirection*; **Router** (the router's own DNS: Dreadwatch, Wallguard and the encrypted DNS features rely on it); **User defined 1-3**; *Unfiltered*: Cloudflare; *Security filters*: CleanBrowsing Security, Comodo Secure DNS, OpenDNS Home, Quad9, Yandex Safe; *Family filters*: CleanBrowsing Adult, CleanBrowsing Family, Cloudflare Family, OpenDNS Family, Yandex Family | No redirection (`dnsfilter_mode` `0`) |
| **User defined 1 / 2 / 3** | Your own resolver addresses, IPv4 and (on HND models) IPv6. A mode that names an empty one is refused | Empty |
| **Per-device rules** | Device (picker of connected devices), MAC, mode. A rule overrides the global mode for that device. Up to 64 | Empty |
| **Guest Network Pro profiles** | One row per network with its own subnet, with its own mode | *No redirection* |

**Order:** a device rule, then the device's network row, then the global mode. A network row set to **No
redirection** exempts that network from the global mode: with the global mode on *Router*, a guest network is
covered only when its own row says *Router* (or another resolver). On guest networks a redirect to a resolver on the
main LAN passes guest isolation on port 53 only; it does not apply on a Guest Portal or with the network's Kill Switch
on (4.21.3).

**How to use it: DNS Director per device.**

1. **LAN > DNS > DNS Director**, switch **Enable DNS Director** on.
2. Global **Redirect to**: **Router**, so every device's plain DNS reaches the router's filters.
3. Under **Per-device rules**, pick a device (for example a lab VM that must use `192.0.2.53`): enter
   `192.0.2.53` as **User defined 1** above, then add the device's rule with mode *User defined 1*.
4. A device that must keep its own provider: rule *No redirection*.
5. Under **Guest Network Pro profiles**, set each guest network's row (for example *Router*, or *CleanBrowsing
   Family* for the kids' network).
6. **Apply**. Only DNS restarts.

**Limits and gotchas**

- DNS Director redirects plain DNS only. DNS-over-TLS / QUIC / HTTPS to an outside provider goes around it; the
  Encrypted DNS block covers that (4.3.4.6).
- A device sent elsewhere by DNS Director is not filtered by Dreadwatch or Wallguard and is refused by the router's
  encrypted DNS server; from v3.8.4 the router does not offer it encrypted DNS by DHCP either (4.3.4.5).
  To leave a device unfiltered without sending it elsewhere, use Wallguard's **Bypass** profile and
  **Devices that skip Dreadwatch** (4.3.2.5a).
- New guest networks start with their row on *No redirection*: set it when the global mode should cover them.

#### 4.22.3 IPTV

**What it is.** IPTV and VoIP over the internet line: an ISP profile, or the LAN port a set-top box (STB) uses, and
the VLAN tags (stock function on a Reaper page; the multicast settings moved to LAN > Multicast, 4.22.1).

| Setting | What it does | Default |
|---|---|---|
| **Select ISP Profile** | **None** (no IPTV tagging), a provider's profile (sets the VLANs and ports), or **Manual** (enter the VLAN IDs your provider gave you). A saved profile this firmware does not list is shown as Manual and kept unless changed | None (`switch_wantag` `none`) |
| **Choose IPTV STB Port** | With profile None: a LAN port bridged straight to the WAN, untagged, for a set-top box | None |
| **Internet** VID / PRIO | Manual: the VLAN ID (2 to 4094) and priority (0 to 7) for internet traffic. A wrong ID takes the internet down; empty sends it untagged | Empty |
| IPTV port VID / PRIO, VoIP port VID / PRIO | Manual, where the manual profile has those ports: the VLAN for the STB port and for the VoIP port. Empty: the port is not used for that service | Empty |
| **IPTV STB port**, **VoIP port**, **Bridge port** | With a provider profile: the ports it uses (read-only) | - |
| **IPTV connection**, **VoIP connection** | A profile that runs its own WAN connection for the service: WAN Connection Type (Automatic IP, Static IP, PPPoE ...), address, DNS, authentication (802.1x MD5), user name, password, MTU / MRU, service name, access concentrator, pppd options. A blank password keeps the saved one | Per profile |
| **Use DHCP routes** | Accept the classless static routes some IPTV providers send by DHCP: Disable, Microsoft (249), RFC3442 (121), both | Microsoft (`dr_enable_x` `1`) |

**What Apply does.** Changing the profile, the STB port or any VLAN ID / priority **reboots the router** (the page
says for how long and asks first); everything else restarts the network (20 to 30 seconds). Turning IPTV on also
turns off, after one confirmation listing them: Dual WAN, automatic WAN port detection (the WAN is pinned to the
default WAN port), WAN aggregation when it uses the STB port, bonding when one of its ports is an IPTV port, the
Multi-Service WAN profiles and 802.1Q on the WAN. Nothing is changed if you cancel. Choosing **None** after a profile
also clears the STB port (stock left the port bridged).

**How to use it: IPTV on a provider VLAN.**

1. Find what the provider uses: an ISP profile name, or the VLAN IDs for internet, IPTV and VoIP.
2. **LAN > IPTV**. If the provider is listed, pick it; the ports it uses appear. Otherwise pick **Manual** and enter
   the **Internet** VID (for example `10`) and priority, and the IPTV VID for the STB port.
3. If the provider sends routes by DHCP, leave **Use DHCP routes** on Microsoft or RFC3442 as the provider says.
4. **Apply**, read the list of what will be turned off, confirm. The router reboots.
5. Plug the set-top box into the port the page names. For multicast IPTV on LAN devices (not the STB port), turn on
   multicast routing on LAN > Multicast; it cannot run together with an STB port.

**Limits and gotchas**

- With an ISP profile, hardware QoS shapes the physical port, not the VLAN interface (4.5.9).
- Automatic WAN port detection (4.19) is not available while IPTV tagging is on.
- A port used by IPTV is locked to *All* on LAN > VLAN (4.22.4).

#### 4.22.4 VLAN

**What it is.** The LAN ports of the router and of every AiMesh node, each set to carry the main network, one guest
network, or tagged VLANs; and the list of VLAN profiles. One Reaper page with two tabs replaces the two stock VLAN
pages and saves the same settings. Shown on models with Guest Network Pro, in router and access point modes.

**VLAN tab (VLAN Switch Control Settings).** One block per node that reports its Ethernet ports, with the live link
state of each port:

| Mode | What the port carries |
|---|---|
| **All (Default)** | The main network untagged and every VLAN tagged. Needed for a port that is also an AiMesh Ethernet backhaul |
| **Access** | One network, untagged: pick the network (a Guest Network Pro network or a VLAN profile). The device on the port is on that network |
| **Trunk** | Tagged VLANs: **Allow all tags** (default) or one VID. A trunk that carries several VIDs (set elsewhere) is kept as it is |

A port is locked to *All*, with the reason, when it is the Dual WAN LAN port, the WAN aggregation port, a bonding
port, an IPTV port, an external-switch port or a live WAN port. Assigning every LAN port leaves no LAN port to reach
the router's pages; use Wi-Fi then. **Apply** restarts the network.

**VLAN Profile tab.** The VLAN rows and the networks bound to them, with **Network Name (SSID)**, **VLAN ID** and
**Port Isolation**. **Add** creates a **VLAN-only network**: VLAN ID 3 to 4093, a Customized network with no Wi-Fi on
any node, its own subnet (the main LAN's first two octets, the VID or the first free number from 100 as the third)
with **DHCP off**. For a VLAN with DHCP and Wi-Fi, use the Network page (4.21). **Modify** changes the VID or Port
Isolation; **Delete** removes the network, its rows and its intranet-access pairs.

**How to use it: put a wired camera on the IoT network.**

1. Create the IoT network on the Network page with its own subnet (4.21.5).
2. **LAN > VLAN > VLAN**, find the router's block (or the node's), set the camera's port to **Access** and pick the
   IoT network.
3. **Apply**. The network restarts; the camera gets an address from the IoT network.

**How to use it: a trunk to a managed switch.** Set the uplink port to **Trunk**, *Allow all tags*; on the switch,
tag each network's VID on the uplink. Use the VLAN ID shown on each network's card (VLAN Profile tab).

**Limits and gotchas**

- A VLAN-only network has no Access Intranet ticked, so Reaper isolates it like a guest network (4.21.3); with the
  router's DHCP off, its devices need fixed addresses in its subnet or a DHCP server of their own on that VLAN.
- The Default IoT Network keeps its Access ports when edited on the Network page (v3.8.0, 4.21.5).
- A port in Access or Trunk mode cannot be an AiMesh Ethernet backhaul.

### 4.23 WAN

The WAN menu holds four tabs: **Internet Connection**, **WAN Ports** (4.19, shown when the model supports Dual WAN),
**NAT and Port Forwarding** and **DDNS**. The menu shows only in the modes that route (router and WISP). All three pages
below are Reaper pages that replace the stock ASUS pages and save the same settings the stock pages saved, so a value
set on either reads back the same. What they share:

- **Nothing is written when the page opens.** The stock Internet Connection page copied settings around in NVRAM on every
  load; these pages only read.
- **Apply posts only what you changed.** The header counts **Unsaved changes**; **Discard** reloads the page.
- **Every restart is announced first.** A change that drops the internet connection or reboots the router asks before it
  runs and says for how long.
- **Passwords are never written into the page.** A password or token field is empty; a hint says whether one is saved.
  Leaving it empty keeps the saved value, typing replaces it.
- A panel that failed to load is marked *This section did not load, so Apply leaves its settings unchanged*. Reload the
  page; Apply never writes the settings of a broken panel.

#### 4.23.1 Internet Connection

**What it is.** The settings of each internet connection (WAN): connection type, login, the provider's special
requirements, VLAN tagging, UPnP and the USB modem. The page is split into five windows - **Connection**, **ISP
requirements**, **VLAN**, **UPnP** and **USB modem** - and a window with nothing to show for the selected connection
type is hidden. The pill in the header names the connection being edited and its type.

**Where the DNS servers are.** The WAN DNS servers, **Forward local domain queries**, DNS rebind protection, DNSSEC and
the DNS-over-TLS client are on **LAN > DNS** (4.22), not here. The Connection window shows the DNS servers in use for
this WAN (*From the provider (automatic)* or *Set by hand: ...*) with a link **Set on the DNS page**.

**Units.** With Dual WAN on (4.19) a **WAN Unit** bar above the windows switches between the primary and secondary
connection; each keeps its own settings (`wan0_*`, `wan1_*`). The switch happens in the browser; with unsaved changes
the page asks before it drops them. A USB modem used as a WAN shows its own window instead of the Ethernet ones.

**Multi-Service WAN profiles.** On models that support it (`mswan`), **Add profile** adds a second service on the
same WAN cable, carried on its own VLAN - up to seven profiles per WAN (`wan101`...`wan107` on the first WAN,
`wan111`...`wan117` on the second). A profile offers Automatic IP, Static IP, PPPoE or **Bridge**; Bridge passes the
profile's VLAN straight to the LAN without routing it, for a device that dials the service itself, and switches PPPoE
relay on. **Profile active** off deletes the profile on Apply. A profile is brought up by restarting its base WAN, so
that WAN drops too. A profile and IPTV cannot both tag the WAN: saving a profile while IPTV is set asks first, then
turns IPTV off and reboots.

**How to use it.**

*Log in with PPPoE (most DSL and many fibre lines):*

1. **WAN > Internet Connection > Connection.** Set **WAN Connection Type** to **PPPoE**.
2. Leave **Get the WAN IP automatically** on unless the provider gave you a fixed address for the PPP link.
3. Under **Account Settings**, enter the **Username** and **Password** from the provider.
4. Leave **MTU** and **MRU** at 1492, and **Service Name**, **Access Concentrator Name** and **Host-Uniq** empty,
   unless the provider gives values.
5. If the provider needs a VLAN on the line (many fibre services), open **VLAN**, turn **802.1Q** on and enter the
   **VLAN ID** (and **802.1P** priority if given). On models without that row see *VLAN* below.
6. Press **Apply** and confirm. The connection drops for up to a minute while the session is set up; the header pill
   and the dashboard show it come back.

*Use a fixed address from the provider:*

1. Set the WAN's DNS servers by hand on **LAN > DNS** first. A switch to **Static IP** is refused until that WAN has
   DNS servers set by hand, because a static connection gets none from the provider.
2. Set **WAN Connection Type** to **Static IP** and enter **IP Address**, **Subnet Mask** and **Default Gateway**.
3. Apply. The confirmation warns that a wrong address, mask or gateway leaves the connection offline; fix it from a
   device on the LAN.

*Clone a MAC address (a provider that locks the line to one device):* **ISP requirements > MAC Address**, then
**Use this device's MAC** (shown when the router knows the MAC of the device you are browsing from) or type the
address, and Apply. The confirmation notes that some providers hold the old lease for several minutes.

**The settings.** Rows appear only for the connection types they apply to.

*Connection window*

| Setting | What it does | Default |
|---|---|---|
| WAN Connection Type | Automatic IP (DHCP), Static IP, PPPoE, PPTP, L2TP; on models that report it (`s46`), the Japanese IPv4-over-IPv6 types v6plus, OCN Virtual Connect, DS-Lite and IPv6 Option; Bridge for a Multi-Service WAN profile. A help line under the selector says what the type is for. | Automatic IP (`wan_proto` `dhcp`) |
| Enable WAN | Off takes this connection down until you turn it back on. | On |
| Enable NAT | Shares the one public address with the LAN. Turn it off only if the provider routes a subnet to you. Not shown for Bridge. | On (`wan_nat_x` `1`) |
| Get the WAN IP automatically | PPPoE, PPTP, L2TP: on, the provider assigns the address of the PPP or VPN link; off, enter it below. | On |
| IP Address, Subnet Mask, Default Gateway | Static IP, or a PPP type with the switch above off. The gateway is optional for PPP types and may not equal the address. | - |
| DNS servers | Read-only line and link to LAN > DNS (4.22). On a Multi-Service WAN profile the DNS rows are on this page instead: **Connect to DNS Server automatically**, **DNS Server1**, **DNS Server2**. | From the provider |
| Authentication | Automatic IP and Static IP: **802.1x MD5** only if the provider asks for it; it uses the username and password below. | None |
| Username, Password | PPP types, and 802.1x MD5. The password field stays empty; *Show password* shows only what you typed. | - |
| PPP Authentication | Auto, PAP or CHAP. | Auto |
| Disconnect after time of inactivity | PPPoE and PPTP: seconds without traffic before the link hangs up; 0 keeps it up. | 0 |
| MTU, MRU | PPPoE, 128 to 1500. A value above 1492 asks for RFC 4638 baby jumbo frames; the page then raises the other value to match so both sides agree. | 1492, 1492 |
| Service Name, Access Concentrator Name | PPPoE, only when the provider names them. | Empty |
| Host-Uniq | PPPoE tag, hexadecimal digits only. | Empty |
| PPTP Options | Auto, No Encryption, MPPE 40, MPPE 128. | Auto |
| Internet Detection | PPP types: how a dead link is noticed - Disable, **PPP Echo** or **DNS Probe**. | PPP Echo |
| PPP Echo Interval, PPP Echo Max Failures | With PPP Echo: seconds between echo requests, and misses before the link is restarted. | 6, 10 |
| DNS probe max failures | With DNS Probe: failed lookups in a row before the link is restarted. One value shared by every WAN (`dns_delay_round`). | 2 |
| Additional pppd options | PPP types: extra options passed to pppd as typed. | Empty |

*ISP requirements window*

| Setting | What it does | Default |
|---|---|---|
| Class-identifier (Option 60) | Automatic IP: the DHCP vendor class some providers require. | Empty |
| Client-identifier (Option 61) | Automatic IP: a typed identifier, or tick **IAID/DUID** to send the RFC 4361 identifier instead. | Empty |
| VPN Server | PPTP and L2TP: host name or address of the provider's server, up to 64 characters. | Empty |
| Enable VPN + DHCP Connection | PPPoE: the stock option that also keeps a DHCP lease on the WAN port alongside the PPPoE session. | On |
| Host Name | The name the router gives the provider (letters, digits, dot, dash, underscore; 32 characters). | Empty |
| MAC Address | Only if the provider locks the line to one MAC; empty uses the router's own. **Use this device's MAC** fills in the browsing device's address. | Empty |
| DHCP query frequency | Automatic IP: Normal Mode, Aggressive Mode or Continuous Mode for lease requests. | Aggressive Mode |
| MTU | Not PPPoE: 1280 to 1500; empty or 1500 for almost every line. Saving a switch to PPPoE puts it back to 1500. | 1500 |
| Enable DHCP Filter | Bridge profiles only. | On (new profile) |
| DS-Lite: Connection type, AFTR Address, B4 IPv4 Address | DS-Lite: Auto, or Manual with the AFTR (IPv6 address or host name) and B4 address. With Auto, the AFTR and B4 the router learned are shown, refreshed every 10 seconds. | Auto |
| Update MAP | v6plus, OCN Virtual Connect, IPv6 Option: asks the provider for a new MAP rule. The internet drops for one to two minutes; it asks first. | - |
| Extend the TTL value | Adds one to the TTL of incoming packets, so devices behind the router look one hop closer. | Off (`ttl_inc_enable` `0`) |
| Spoof LAN TTL value | Sends every LAN packet out with the same TTL, for providers that detect shared connections. | Off (`ttl_spoof_enable` `0`) |

A change to the two TTL switches alone reloads the firewall only; the connection is not restarted.

*VLAN window*

| Setting | What it does | Default |
|---|---|---|
| 802.1Q, VLAN ID, 802.1P | Tags this connection with a VLAN (ID 2 to 4094, priority 0 to 7) for providers that need one. A wrong VLAN ID takes the connection down. Turning 802.1Q on while IPTV is set asks first, turns IPTV off and reboots. | Off |
| Enable WAN Aggregation | Joins the WAN port and a LAN port into one faster link to a modem that supports it (models with `wanbonding`; Automatic IP or Static IP only). Turning it on or off reboots the router; with Dual WAN on, Dual WAN is turned off, and with IPTV on LAN 4, IPTV is turned off, each asked first. Switching the WAN to a PPP type turns aggregation off. | Off |

The 802.1Q rows exist only on models with Multi-Service WAN. On the others (for example the GT-BE98, GT-BE19000 and
BQ16) the window says so instead: set the provider's VLAN on **LAN > IPTV** with ISP profile *Manual Setting* and the
VLAN ID as *Internet VID*; saving it there reboots the router.

*UPnP window* (the base WANs only; not shown for a profile)

| Setting | What it does | Default |
|---|---|---|
| Enable UPnP | Lets LAN devices open ports on this connection by themselves (games and consoles use it). Per WAN (`wan0_upnp_enable`). | Off (8.1) |
| Allow IPv6 pinholes (IGD:2) | Lets devices open IPv6 firewall holes through UPnP. Shown on models with IGD:2 support. | Off |
| Secure UPnP mode | A device may open ports only to itself. | On |
| Protect router service ports | Refuses a mapping that would take over a port the router itself uses for VPN or SSH (Reaper, 8.2). | On |
| Allowed internal ports | The range of LAN-side ports a mapping may point at. | 1024 - 65535 |
| Allowed external ports | The range of WAN-side ports a mapping may claim. Reaper starts it at 1024 so no device can claim 22, 53 or 443. | 1024 - 65535 |

A UPnP-only change reloads the firewall and the UPnP service; the connection stays up.

*USB modem window* (shown when USB is one of the WANs on WAN Ports)

| Setting | What it does | Default |
|---|---|---|
| Select USB Device | **Auto**, or **Legacy** for phones and modems that act as a network card (only the MTU applies to them). | Auto |
| APN Configuration | Auto reads APN, dial number and user from the SIM (shown read-only); Manual Setting shows the fields. | Auto |
| Telecommunications Standards | WCDMA (UMTS) / LTE, CDMA2000 (EVDO), TD-SCDMA (WiMAX where supported). | WCDMA / LTE |
| APN Service, Dial Number, Username, Password | Manual only. | - |
| Authentication | None, PAP, CHAP, PAP / CHAP. | None |
| PIN code | Shown when the SIM asks for one; empty keeps the saved PIN. | - |
| USB Adapter | Auto or a named modem model. | Auto |
| USB MTU | 0 or empty keeps the modem's own value. | - |

Every USB modem save reboots the router (as stock).

**What Apply restarts.** A connection setting restarts that WAN (`restart_wan_if <unit>`): its devices lose the
internet for about 10 to 30 seconds, up to a minute for PPPoE. The confirmation adds, as they apply: the old and new
connection type, *This connection is turned off*, the static-address warning, the MAC/VLAN warning. The router
**reboots** instead for WAN aggregation, an IPTV conflict answer, a USB modem change, and an automatic-port pin: with
automatic WAN port detection on (4.19), switching to Static IP, PPTP or L2TP, turning 802.1Q or aggregation on, or
saving a Multi-Service WAN profile pins the WAN to the default WAN port, asks first and reboots. Switching into v6plus,
OCN Virtual Connect or IPv6 Option resets the MAP rule first.

**Examples.**

- *Fibre with PPPoE on VLAN 10:* type PPPoE, username and password, VLAN window 802.1Q on, VLAN ID `10`. Apply once;
  the confirmation lists the drop and the VLAN change.
- *Cable modem that remembers the old router:* Automatic IP; ISP requirements > MAC Address = the old router's WAN MAC
  (`00:00:5e:00:53:10`), or power the modem off for a few minutes after connecting the new router.
- *Provider needs a DHCP vendor class:* Automatic IP, Class-identifier = the string the provider gives.

**Limits and gotchas.**

- **Static IP needs DNS first**, on LAN > DNS (above).
- **PPPoE MTU and the WAN MTU are separate settings.** The WAN MTU row is hidden for PPPoE; the PPP link uses MTU/MRU.
- **Reaper re-dials a dead PPPoE link** on its own: the self-monitor's WAN bounce (`reaper_wanbounce_enable`, on at
  factory, 8.2) fires only after the link has failed all three reachability probes after the boot grace period.
- **UPnP is off at factory** and opens ports without asking when on. Prefer explicit port forwards (4.23.2) and keep
  Secure mode and the service-port protection on.
- **Management stays off the WAN** (2.13): nothing on this page opens the web interface or SSH to the internet.
- The second-WAN copies that only some ASUS builds read (`MULTIWAN_CFG`), the mobile country/ISP picker and the S46
  MAP-E table are not carried over from the stock page.

#### 4.23.2 NAT and Port Forwarding

**What it is.** One page for the four stock NAT pages, one window each: **Port Forwarding**, **Port Trigger**, **DMZ**
and **NAT Passthrough**. The lists keep the stock record formats (`vts_rulelist`, `autofw_rulelist`), and a row
nobody edited is written back byte for byte. Nothing is saved until **Apply**; most changes reload only the firewall,
which takes a few seconds. These are IPv4 rules; IPv6 has no NAT, and letting inbound IPv6 reach a device is a firewall
rule (4.1).

**This page or Firewall > Forwards?** Both forward ports. This page is the stock list, applied at once with no
countdown. **Firewall > Forwards** (4.1.7) is Reaper's rules engine: source restriction by objects, schedules, and the
Apply-and-Keep countdown (2.7). Use one place per port, so a forward is never defined twice. **System Log > Port
Forwarding** (4.26.6) lists every forward in effect, from both; the link **See the forwards in effect now** opens it.

**How to use it.** Before any forward or DMZ, give the target device a fixed address (**Devices**, 4.8.2), or the
rule will one day point at whatever device picked up that address.

*Forward a port to a game console:*

1. **WAN > NAT and Port Forwarding > Port Forwarding.** Turn **Enable Port Forwarding** on.
2. In **Quick Select**, pick the game (for example *Xbox Live*: external port `3074`, protocol BOTH). The preset fills
   the editor; it saves nothing yet.
3. Enter the console's address in **Internal IP Address** (`192.168.50.20`; the field offers the known devices).
4. Press **Add**, then **Apply**.

*Forward HTTPS to a NAS, from one office only:*

1. Service Name `NAS`, Protocol `TCP`, External Port `8443`, Internal Port `443`, Internal IP `192.168.50.30`,
   Source IP `198.51.100.0/24`.
2. **Add**, **Apply**. Only addresses in 198.51.100.0/24 can connect; everyone else scanning port 8443 finds nothing.

*Open everything to one device (DMZ):*

1. **DMZ** window: turn **Enable DMZ** on and enter **IP Address of Exposed Station** (`192.168.50.40`).
2. Apply. Every unsolicited connection from the internet that no other rule takes goes to that device.

**The settings.**

*Port Forwarding*

| Setting | What it does | Default |
|---|---|---|
| Enable Port Forwarding | Off keeps the rules but forwards nothing. | Off (`vts_enable_x` `0`) |
| Quick Select | Presets: the stock server list (FTP, HTTP, SMTP, DNS, SNMP, GRE, IPv6 Tunnel, IPSec, OpenVPN, PPTP, L2TP and others) and game list (Age of Empires, BitTorrent, Counter Strike, PlayStation2, Warcraft III, WOW, Xbox Live). Fills the editor only. | - |
| Service Name | A label, up to 30 printable characters (no angle brackets, apostrophe or percent). | - |
| Protocol | TCP, UDP, BOTH (TCP and UDP) or OTHER (an IP protocol by number). | TCP |
| External Port | Single ports and ranges, comma separated: `80,443,8000:8010`. Each 1 to 65535, ranges ascending. Stored normalised (spaces and leading zeros removed, `-` and `~` written as `:`), because the firewall drops a rule whose port has a dash. With OTHER the field is **Protocol number**, 1 to 255 (GRE is 47). | - |
| Internal Port | Optional, one port; empty keeps the external port. Not used with OTHER. | Empty |
| Internal IP Address | The LAN device. The router's own address and the LAN network and broadcast addresses are refused; an address off the LAN subnet asks first. | - |
| Source IP | Optional: only this IPv4 address or subnet (`a.b.c.d/nn`) may connect. | Empty (anyone) |

Limits: 64 rules and 8192 bytes for the whole list; a line under the table shows *N of 64 rules, X of 8192 bytes*. The
same source, external port and protocol twice is refused as a duplicate (BOTH collides with TCP and with UDP). Click
**Edit** on a row to load it into the editor (the button reads **Save**), the cross to delete it. A row the firewall
cannot read is greyed and tagged *Ignored by the router*.

**Also forwarded by the router** lists the other rules in the same forwarding chain, set on their own pages: remote web
access (*TCP port to the router*, when web access from the WAN is on), Open NAT game rules, and the DMZ target.

*Port Trigger*

| Setting | What it does | Default |
|---|---|---|
| Enable Port Trigger | Off keeps the rules but opens nothing. | Off (`autofw_enable_x` `0`) |
| Well-Known Applications | Presets (Quicktime 4 Client, Real Audio). | - |
| Description | Up to 18 characters. | - |
| Trigger Port, Protocol | When a LAN device sends to this port (a port or a range `a:b`), TCP or UDP... | - |
| Incoming Port, Protocol | ...the router opens this port or range to that device for a while. | - |

Limits: 32 rules, 2048 bytes. Triggering suits an application that calls out first and expects the far end to connect
back; a forward is the better choice for a server.

*DMZ*

| Setting | What it does | Default |
|---|---|---|
| Enable DMZ | Off clears the address. | Off (`dmz_ip` empty) |
| IP Address of Exposed Station | The device that receives every unsolicited connection no other rule takes. Use it only for a device that protects itself: it is reachable on every port. | - |

An FTP server behind the DMZ still needs a forward: **Add the FTP rule** opens the FTP preset in the Port Forwarding
editor.

*NAT Passthrough*

| Setting | What it does | Default |
|---|---|---|
| PPTP, L2TP, IPSec Passthrough | Protocol helpers for VPNs from LAN devices to the internet. Turning one off blocks that VPN type. | On |
| RTSP, H.323 Passthrough | Helpers for streaming and video calls. | Off |
| SIP Passthrough | The SIP helper. Turning it on restarts the whole network (about 30 seconds); it asks first. | Off (`fw_pt_sip` `0`) |
| PPPoE Relay | Lets LAN devices dial their own PPPoE session through the router. A change restarts only the relay. | Off |
| PPPoE relay interface | Primary or Secondary WAN; shown with Dual WAN in Load Balance. | Primary |
| FTP Passthrough | Active-mode FTP from LAN devices to outside servers. Off by default because the FTP helper lets a hostile FTP server open connections towards the device. Passive FTP, the router's own FTP server and a forwarded FTP port work either way (Reaper). | Off (`nf_ftp` `0`) |
| FTP ALG port | The FTP helper follows port 21 and this port, 1 to 65535. | 2021 |

A helper works only on its own ports while its switch is on (8.3).

**Examples.**

- *Remote desktop to one PC, from a known address:* TCP, External `53389`, Internal `3389`, IP `192.168.50.25`,
  Source `203.0.113.7`.
- *Forward a GRE tunnel:* Protocol OTHER, Protocol number `47`, Internal IP of the tunnel endpoint.
- *A range for a game server:* BOTH, External `27015:27030`, Internal Port empty.

**Limits and gotchas.**

- **A forward of the remote-web-access port never matches.** With web access from the WAN on, the router takes that TCP
  port first; the page warns *A rule uses TCP port N, which remote web access already sends to the router*. Keep remote
  access off (2.13).
- **Forwarding TCP 21 while the USB FTP server is on** makes the FTP server unreachable from the internet; the page warns.
- **DMZ exposes the device completely.** A forward of the ports it needs is almost always enough.
- **Japanese v6plus, OCN Virtual Connect and IPv6 Option lines with a shared address** reach only the provider's port
  set; a port outside it asks before it is saved.
- The second-WAN lists (`vts1_rulelist`, `dmz1_ip`) belong to ASUS builds no Reaper model uses and are not shown.
- This page has no NAT-acceleration switch; Connections (4.9) shows which flows the accelerator carries.

#### 4.23.3 DDNS

**What it is.** Two panels. **DDNS Setting** keeps a host name pointed at the router's WAN address through a dynamic
DNS provider; it opens no ports by itself. **HTTPS/SSL Certificate** chooses the certificate the router's HTTPS web
interface and its other TLS services use (Encrypted DNS, 4.3.4; FTP over TLS).

ASUS DDNS (`asuscomm.com`) is not part of Reaper (1.2): it is not offered, and a router that had it saved shows *ASUS
DDNS (asuscomm.com) is no longer part of this firmware, so this saved setting does nothing. Choose another provider*.
The ASUS deregister, transfer and privacy-policy flows went with it. **Let's Encrypt via DNS** and the `ddns-start`
script checks are Reaper's; the **Custom** provider (`ddns-start`) is Merlin's; the rest is stock.

**How to use it.**

*A DDNS name with a Let's Encrypt certificate:*

1. Create the host name at your DDNS provider (for example `home.example.com`) and note the user name and password or
   key it gives you.
2. **WAN > DDNS.** Turn **DDNS** on, choose the provider under **Server**, enter **Host Name**, **Username or E-mail
   Address** and **Password or DDNS Key**.
3. Under **Certificate**, choose **Free Certificate from Let's Encrypt**. It can be chosen once DDNS is on with a
   provider; until then it is greyed and the hint says what it needs. Leave **I agree to Let's Encrypt** ticked.
4. Make sure TCP port 80 on the WAN reaches the router: Let's Encrypt checks the name over it.
5. Apply. The page asks first: *The new certificate is used after you sign out; browsers that trusted the old one ask
   again*. The **Server Certificate** status reads *Authorizing*, then *Updating...*, then *Active* with the new issuer
   and expiry. The certificate renews by itself.

*A certificate without DDNS or an open port:* choose **Let's Encrypt via DNS (no DDNS)** and follow 4.3.4.3 (Cloudflare,
deSEC or DuckDNS API token; about two minutes; renewed daily from 30 days before expiry).

*Your own certificate:* choose **Import Your Own Certificate**, pick the **Private Key** (`.pem`/`.key`, no passphrase)
and the **SSL Certificate** (`.pem`/`.crt`/`.cer`), press **Upload**, then **Apply**.

**The settings.**

| Setting | What it does | Default |
|---|---|---|
| DDNS | Publishes the WAN address under your host name. | Off (`ddns_enable_x` `0`) |
| Interface | Auto, Primary WAN or Secondary WAN; shown with Dual WAN in Load Balance. | Auto (`ddns_wan_unit` `-1`) |
| Server | The provider: DynDNS (plain, CUSTOM, STATIC), selfHOST.de, ZoneEdit, DNS-O-Matic, HE.NET, Dynu, Cloudflare, Pubyun, Tunnelbroker, No-IP, Oray (on builds that carry it), Namecheap, FreeDNS (afraid.org), FreeMyIP, deSEC (dedyn.io), or **Custom (ddns-start script)**. Google Domains is listed, marked *(service closed)*, only while it is the saved provider. | None |
| Host Name | The name to publish. Labelled **Tunnel ID** for Tunnelbroker. | - |
| Username or E-mail Address | Labelled **Domain name** for Namecheap, **Username** for FreeDNS, **Account name** for Tunnelbroker; not shown for HE.NET. | - |
| Password or DDNS Key | Labelled **Update key** for Tunnelbroker. Empty keeps the saved one. | - |
| Enable wildcard | Also publishes `*.hostname`, on providers that support it (not Tunnelbroker, HE.NET, selfHOST.de, Dynu, Cloudflare, Pubyun). | Off |
| IPv6 Update | Also publishes the router's IPv6 address. Shown when IPv6 is on (4.24); not for Pubyun. | On (`ddns_ipv6_update` `1`) |
| WAN IP and hostname verification, Check every | Checks now and then that the name still points at the WAN address and updates it if not; every N minutes, 30 or more. | Off; 60 minutes |
| Forced update every (days) | 0 to 365; 0 updates only when the address changes. | 21 |
| Registration | The provider's last answer (*Registration is successful*, *Authentication failed*, *No response from the DDNS server*, and so on) and **Update**, which sends an update now without saving anything. | - |
| Certificate | **Free Certificate from Let's Encrypt** (needs DDNS on and TCP port 80 reachable), **Let's Encrypt via DNS (no DDNS)** (4.3.4.3), **Import Your Own Certificate**, **Self-signed (made by the router)**. The two Let's Encrypt choices are offered only on builds with Let's Encrypt. | Self-signed (`le_enable` `0`) |
| DNS provider, Domain name, API token, Certificate request | Let's Encrypt via DNS only (4.3.4.3, 8.2). | Cloudflare |
| I agree to Let's Encrypt | Shown when switching to either Let's Encrypt choice. Applying with it unticked asks, then falls back to Self-signed. | Ticked |
| Server Certificate | Status, Issued to, Issued by, Expires on, and **Export**. | - |
| Root / intermediate certificate | Shown for the self-signed certificate (and an import that carried its CA): the router's own root, with **Export**, to install on devices that should trust the self-signed certificate. | - |

Renewing the self-signed certificate is on **Administration > System**.

**Custom provider.** **Custom** runs `/jffs/scripts/ddns-start` on every update; JFFS custom scripts must be on
(Administration > System). The page checks the script: a missing file (*the router runs only that exact name, with no
extension*, with the name of a near miss such as `ddns-start.sh` to rename), or a file that is not executable (*chmod +x
/jffs/scripts/ddns-start*).

**Examples.**

- *Update a Hurricane Electric tunnel endpoint (4.24):* Server Tunnelbroker, Tunnel ID, Account name and Update key from
  the broker; the tunnel follows a changing WAN IPv4 address.
- *deSEC name with a DNS-validated certificate:* DDNS with Server deSEC for the address, and Certificate *Let's Encrypt
  via DNS* with provider deSEC for the certificate - nothing inbound needed for the certificate.

**Limits and gotchas.**

- **DDNS opens nothing.** Reaching a service by name still needs a forward (4.23.2) or the service on the router.
- **A Let's Encrypt certificate needs HTTPS on the web interface to be useful.** With the web interface on HTTP only,
  the hint says browsers are not served it; set *Web access protocol* on Administration > System to HTTPS or HTTP +
  HTTPS.
- **A new certificate reaches the web interface after you sign out;** Encrypted DNS and FTP over TLS restart with it.
- **An update with nothing changed** (same server, host and address as the last update) asks before forcing another.
- Behind a provider's carrier-grade NAT the WAN address is not public; DDNS then publishes an address nobody can reach.

### 4.24 IPv6

**What it is.** **IPv6** (its own menu, in router and WISP mode on models with IPv6) sets how the router gets IPv6
from the provider and hands it to the LAN. It replaces the stock IPv6 page with the same eight connection types and the
same row rules. IPv6 is **Disabled** at factory (8.3). Apply reconnects the WAN (`restart_net`, plus `restart_ftpd` when
the FTP server is on); IPv6 comes back in about 30 seconds. Two differences from stock: switching the type no longer
blanks the values saved for another type, and the header pill shows the type in use with the live LAN prefix.

**When IPv6 counts as up (v3.7.7).** The header and the dashboard count IPv6 as up only while the router has a working
IPv6 default route, not merely an address. When Native IPv6 does not come back after the provider's outage (the
router's DHCPv6 client stays in its back-off), the router asks for it again once per outage as soon as the WAN is back,
so IPv6 returns without a reboot.

The IPv6 firewall is on the Firewall page (4.1; on at factory, `ipv6_fw_enable` `1`). The live IPv6 state is on
**System Log > IPv6**. On a v6plus, OCN Virtual Connect, DS-Lite or IPv6 Option WAN (4.23.1) the type selector is
locked: the WAN type owns the IPv6 setup.

**The connection types.**

| Type | What it is |
|---|---|
| Disable | IPv6 off; LAN devices get no IPv6 from the router. |
| Native | The provider assigns IPv6 with DHCPv6 and router advertisements. Most providers use this. |
| Static IPv6 | WAN address, gateway and LAN address entered by hand, as the provider gave them. |
| Passthrough | The router relays the provider's IPv6 to the LAN (router advertisements, DHCPv6 and neighbour discovery) instead of routing a prefix of its own. Shown on models that support it. |
| FLET'S IPv6 service | Passthrough for the NTT FLET'S service in Japan. |
| Tunnel 6to4 | Builds a `2002::/48` prefix from the public IPv4 address and tunnels through a public relay. Few networks still support it. |
| Tunnel 6in4 | A tunnel from a broker such as Hurricane Electric. |
| Tunnel 6rd | A tunnel run by the provider; settings from the provider's DHCP (option 212) or entered by hand. |

**How to use it.**

*Native IPv6 with a /56 from the provider:*

1. **IPv6.** Set **Connection type** to **Native**.
2. With a PPPoE, PPTP or L2TP WAN, set **Interface**: **PPP** asks for IPv6 inside the PPP session, **Ethernet** on the
   WAN port directly. Most PPPoE providers use PPP; leave **Accept Default Route** on.
3. Leave **Prefix delegation (DHCP-PD)** on.
4. Set **WAN Prefix Length** to `56`. With DHCP-PD this is the prefix size the router asks the provider for: 48 to
   64, or empty / `0` to let the provider choose. From the image after v3.8.0 the page refuses another value (before,
   it was saved and silently ignored), and the system log says `Requested: none (provider default)` when no size
   is asked. Each guest and VLAN network gets its own public /64 cut from the delegated prefix. A /56 or
   larger has room for every network; from the image after v3.8.2 a /57 to /63 works too, with room for networks
   numbered up to 2^(64 - length) - 1 (a /60: up to 15, a /62: up to 3; the main LAN is 0 and keeps the first
   /64). A network beyond that, and every network under a /64, gets a private (ULA) address (even with `ipv6_prefix_div`), and the system log
   says so once per boot ("... uses a private (ULA) prefix"). From the image after v3.8.2 a new or reset router
   asks for a /56 (`ipv6_prefix_len_wan` `56`, 8.1); an upgraded router keeps its value, often 64. With Static
   IPv6 the same field is the WAN address length: when Static is picked on a router that still holds that 56,
   the page fills in 64. With a /57 to /63 the main LAN keeps its own address and range; a guest network whose
   /64 would equal the main LAN's gets a private (ULA) address instead.
5. **Auto Configuration Setting**: Stateless (SLAAC) suits nearly every network. Leave **Enable Router
   Advertisement** and **Connect to DNS Server automatically** on.
6. Apply. Within about 30 seconds **LAN IPv6 Prefix** and **LAN Prefix Length** show what the provider delegated
   (for example `2001:db8:4400::` and 56), and **LAN IPv6 Address** the router's own address.

*A 6in4 tunnel from a broker:*

1. Create the tunnel at the broker with your WAN IPv4 address as the client endpoint. Some brokers require that the
   address answers ping while the tunnel is created; WAN ping is off at factory (Firewall > General, 8.3).
2. **IPv6 > Connection type: Tunnel 6in4.**
3. **Server IPv4 Address**: the broker's server (`203.0.113.1`). **Client IPv6 Address** and its length: your side of
   the tunnel (`2001:db8:a::2` / `64`). **Server IPv6 Address** (optional): the broker's side (`2001:db8:a::1`).
4. **LAN IPv6 Prefix** and **LAN Prefix Length**: the routed prefix the broker gave you (`2001:db8:b::` / `64`).
5. **Tunnel MTU** `0` (automatic) or the broker's value (1280 to 1480); **Tunnel TTL** `255`.
6. Leave **Enable Router Advertisement** on, enter **IPv6 DNS Server 1** (`2001:db8:53::53` here; use a real resolver),
   Apply.
7. If your WAN IPv4 address changes, keep the tunnel endpoint current with the broker's DDNS updater (4.23.3).

**The settings.** Rows appear only for the types they apply to.

| Setting | What it does | Default |
|---|---|---|
| Connection type | The eight types above. | Disable (`ipv6_service` `disabled`) |
| Interface | Native, Static, Passthrough on a PPP-type WAN: PPP or Ethernet. FLET'S always uses Ethernet. | PPP |
| Accept Default Route | Native over PPP: use the default route the provider announces on the PPP link. | On |
| Prefix delegation (DHCP-PD) | Native: ask the provider for a prefix to number the LAN. Turn it off only if the provider gave you a fixed LAN address to enter below. | On |
| Release prefix on exit | Native and Passthrough: tells the provider to release the delegated prefix when the router disconnects. | On |
| IPv4 Anycast Relay | 6to4: the relay address. | `192.88.99.1` |
| Server IPv4 Address, Client IPv6 Address / length, Server IPv6 Address | 6in4 (above). | - |
| DHCP Option | 6rd: on, take the 6rd settings from the provider's DHCP (option 212); off, enter them below. | On |
| IPv6 Prefix / length, IPv4 Border Router, IPv4 Router Mask Length | 6rd by hand, as the provider gives them (mask 0 to 32). | - |
| Tunnel MTU | Tunnels: 0 picks it automatically; otherwise 1280 to 1480. | 0 |
| Tunnel TTL | Tunnels: 0 to 255. | 255 |
| WAN IPv6 Address, WAN Prefix Length, WAN IPv6 Gateway | Static: the WAN side (gateway optional). Native with DHCP-PD: only WAN Prefix Length, the size requested (above). | WAN Prefix Length 64 |
| LAN IPv6 Address | Static, and Native without DHCP-PD: the router's LAN address; the LAN prefix is derived from it. Read-only for the other types. | - |
| LAN IPv6 Prefix, LAN Prefix Length | 6in4: entered. Static and Native without PD: length entered (3 to 126; 112 at most with Stateful). Otherwise shown as received; *Not assigned yet* until it arrives. | - |
| Auto Configuration Setting | Native and Static: **Stateless (SLAAC)** - devices pick their own addresses; **Stateful (DHCPv6)** - the router also hands out addresses from a pool; devices without a DHCPv6 client still use SLAAC. | Stateless |
| IP Pool Starting / Ending Address | Stateful: the last group only, 1 to 4 hex digits; the prefix in front comes from the LAN address. Start not above end. | `1000` - `2000` |
| Lease time | Stateful: seconds, 120 to 604800. | 86400 |
| Connect to DNS Server automatically | Native and Passthrough: take the provider's IPv6 DNS servers. | On |
| IPv6 DNS Server 1 to 3 | When not automatic (and always for Static and tunnels); each optional. | Empty |
| Enable Router Advertisement | Native, Static, tunnels: announce the router and its prefix so devices set up IPv6 on their own. Off: devices get no IPv6 unless configured by hand. | On (`ipv6_radvd` `1`) |

**Examples.**

- *Provider gives a /64 only:* Native, DHCP-PD on, WAN Prefix Length `64`.
- *Provider with a fixed LAN prefix and no PD:* Native, DHCP-PD off, LAN IPv6 Address `2001:db8:4400::1`, LAN Prefix
  Length `64`.
- *Passthrough on a v6plus line:* the page notes that **Connect to DNS Server automatically** is recommended there.

**Limits and gotchas.**

- **The router's own prefix shows only for the saved type.** While another type is selected but not applied, the live
  rows read *Not assigned yet*.
- **Apply reconnects the WAN** - IPv4 included - for about 30 seconds.
- **Changing IPv6 does not open anything inbound.** The IPv6 firewall keeps unsolicited inbound traffic out; UPnP IPv6
  pinholes are a separate, off-at-factory switch (4.23.1).
- The second-WAN IPv6 page of some ASUS builds (`ipv61_*`) and the "IPv6 Only" type are not carried: no Reaper model
  builds them.

### 4.25 Wireless settings

The Wireless menu (hidden in Repeater and Media Bridge mode) has these tabs: **Settings** (4.25.1), **WPS**, **WDS**,
**Wireless MAC Filter**, **RADIUS Setting**, **Roaming Block List**, **MLO** and **Wireless Quality** (4.10). Smart
Connect Rule (4.25.8) sits under Network Tools. Each tab is a Reaper page that replaced the stock page; from v3.6.5 the
stock WPS, WDS, MAC Filter, RADIUS, Roaming Block List and MLO pages no longer ship and their addresses open the Reaper
pages. The pages keep the stock settings and apply them the stock way - a save restarts the wireless
(`restart_wireless`; Wi-Fi drops for the restart) unless a section says otherwise. The per-band pages (WDS, MAC Filter,
RADIUS) show every radio on one page, so a four-radio GT-BE98 shows four panels; the stock pages showed one band at a
time.

**Where each tab shows.** **WDS** hides on models with the ASUS UI4 layout; **Wireless MAC Filter** and **RADIUS
Setting** hide on a model whose main network is a Network-menu profile with its own filter and server (`sdn_mainfh`);
**Roaming Block List** shows only when this router is the AiMesh router; **MLO** shows on models with MLO and
multi-network support (`mlo`, `mtlancfg`). The 3006.102.10 and 3006.102.8 lines use the same pages.

**The Network menu holds the network itself.** On these models the main Wi-Fi network is a profile on the Network menu
(4.21). The **network name, security (including Enterprise), the bands the network uses (one name on all bands is Smart
Connect) and the Wi-Fi 6/7 mode** are set there, not on the Wireless tabs. Guest Network Pro networks keep their own MAC
filter and RADIUS server there too.

#### 4.25.1 Wi-Fi Settings

**What it is.** **Wireless > Settings** is the one tab for every radio setting, every radio in a column, applied once
(4.10 describes the page, the locks between settings, Wireless Mode, preamble puncturing, minimum width on Auto and
interference mitigation; this section lists every control). Only changed fields are written, and all radios restart
together (about 10 seconds). A greyed cell is locked by another setting and names the reason when you hover it; a dash
means the row does not apply to that band.

**How to use it.**

*One network name on all bands with WPA2/WPA3:* this is set on the **Network** menu (4.21): open the main network,
choose every band (that is Smart Connect), set the network name, choose **WPA2/WPA3-Personal** and a password, and
Apply. 6 GHz admits only WPA3 (or Enhanced Open), by the standard, so a WPA2-only device joins on 2.4 or 5 GHz under
the same name. The band-steering rules are on Smart Connect Rule (4.25.8).

*Fix a channel for a WDS link or an old device:* **Control Channel** on the band, a fixed **Channel bandwidth**, Apply.
The radio leaves automatic selection until you set Auto again.

*Turn Wi-Fi off at night:* **Enable wireless scheduler** on the band opens a 7 x 24 grid; green hours are radio on.
Click a cell, a day or an hour; **All on** clears it. Apply. The scheduler is held off while MLO is on.

**The settings.**

| Setting | What it does | Default |
|---|---|---|
| **Radio & Operating Mode** | | |
| Enable Radio | Switches the radio. Refused while MLO is on; on an AiMesh router it asks first, because the setting reaches the nodes. To keep a radio off at all times use this, not the scheduler. | On |
| Enable wireless scheduler | The weekly on/off grid (above). Locked while MLO is on or the radio is off. | Off |
| Wireless Mode | Per band: 2.4 GHz Auto / N only / Legacy; 5 GHz Auto / AX only / N/AC/AX mixed / Legacy; 6 GHz Auto / AX only. N only and Legacy switch Wi-Fi 6 and 7 off on that band and Apply asks first; Auto, N/AC/AX mixed and AX only turn them back on (4.10). | Auto |
| **Channel & Bandwidth** | | |
| Channel bandwidth | The widths the driver reports for the band, or Auto. | Auto |
| Enable 160 MHz | 5 GHz: include 160 MHz when the bandwidth is Auto (uses DFS channels). | Off (`wl_bw_160` `0`) |
| Minimum width on Auto | 5 and 6 GHz: keep Auto at 80 MHz or wider (4.10.9). | Off |
| Fit channels to AiMesh nodes | 5 and 6 GHz, one switch: keep the channel picker on channels every registered node can use (8.2). The cell shows its state, for example *No AiMesh node registered* or *Every node can use this channel*. | On (`amas_chanfit` `1`) |
| Control Channel | Auto or a channel. | Auto |
| BW320 Channel Range | 6 GHz at 320 MHz: which 320 MHz block (needs a fixed control channel). | - |
| Extension Channel | 2.4 GHz at 40 MHz with a fixed channel: Above or Below. | - |
| Auto channel options | Extra channels automatic selection may pick: 2.4 GHz channels 12 and 13; 5 GHz DFS channels and U-NII-4; 6 GHz preferred scanning channels (PSC) only. Editable while the channel is Auto; a fixed DFS channel still moves when radar is detected. | 12/13 off; DFS on (`acs_dfs` `1`); U-NII-4 off; PSC on (`psc6g` `1`) |
| Preamble puncturing, Punctured slice, Dynamic sensitivity, Monitoring source, Minimum gain, Minimum hold time | 5 and 6 GHz (4.10.1 to 4.10.8). | Off |
| Interference mitigation | Driver default, or Add hardware ACI mitigation (4.10.10). | Driver default |
| **Clients & Roaming** | | |
| Max Number of Client Connection | 1 to 128 clients on the band. | 128 |
| Roaming assistant | Disconnects a client whose signal drops below the threshold so it can move to a stronger router or node: -90 to -40 dBm, or off. | -70 dBm |
| WiFi Agile Multiband | Wi-Fi Alliance MBO signalling for steering; needs Protected Management Frames, set on the Network menu. | - |
| Target Wake Time | Wi-Fi 6 clients schedule their wake-ups; needs 802.11ax on the band. | Off (`wl_twt` `0`) |
| Group Key Rotation Interval | Seconds between WPA group key changes, 0 to 2592000; 0 = never. | 3600 |
| **Rates, Modulation & Aggregation** | | |
| 802.11b mode (preamble) | 2.4 GHz: Long or Short; shows *Disable 802.11b* and locks while that is set. | Long |
| Disable 802.11b | 2.4 GHz: drops the 1, 2, 5.5 and 11 Mbps rates so no 802.11b client can join and slow the band. | - |
| Multicast Rate (Mbps) | Auto or a fixed rate (CCK rates on 2.4 GHz only). | Auto |
| Modulation Scheme | Highest QAM for Wi-Fi 4 and 5 clients: 2.4 GHz up to MCS 7, 9 or 11; 5/6 GHz up to MCS 9 or 11. Locked in Legacy. | - |
| Optimize AMPDU aggregation | Optimises the number of MPDUs in an AMPDU. | Off |
| AMPDU RTS | RTS for every AMPDU; off also parks RTS Threshold. | On |
| RTS Threshold | 0 to 2347. | 2347 |
| Fragmentation Threshold | 256 to 2346 bytes; editable in Legacy only, as stock. | 2346 |
| **Spatial - OFDMA, MU-MIMO & Beamforming** | | |
| OFDMA / MU-MIMO | Disable, DL OFDMA, DL / UL OFDMA, DL/UL OFDMA + MU-MIMO; needs 802.11ax on the band. | DL/UL OFDMA + MU-MIMO (`wl_ofdma` `3`) |
| Multi-User MIMO | Follows the OFDMA choice, as stock derives it at every apply. | On |
| Explicit Beamforming | Client and router exchange channel estimates; MU-MIMO requires it. | On |
| Universal Beamforming | Implicit beamforming for clients that cannot report estimates. | Off |
| **Coexistence & Multicast** | | |
| Bluetooth Coexistence | 2.4 GHz: Disable, Enable, Pre-emptive (no 1/2 Mbps rates and no TX bursting). | Disable |
| Enable IGMP Snooping | Optimises wireless multicast by watching IGMP. | On (`wl_igs` `1`) |
| Reducing USB 3.0 interference | Shown in the 2.4 GHz column on models with USB 3: runs the USB ports at USB 2.0 speed. A change reboots the router. | - |
| **WMM / Airtime QoS** | | |
| Enable WMM | Auto, Enable, Disable; a choice in Legacy only, always on otherwise. | On |
| Enable WMM No-Acknowledgement | More throughput, more errors in a noisy band. | Off |
| Enable WMM APSD | WMM power-save delivery. | On |
| Airtime Fairness | Shares airtime between links. | - |
| **Beacon & Timing** | | |
| DTIM Interval | 1 to 255 (4.10.13: Reaper sets 1). | 1 |
| Beacon Interval | 20 to 1000 ms. | 100 |
| Enable TX Bursting | Frame bursting. | On |
| **Power** | | |
| Tx power adjustment | Performance (100), Good, Fair, Balanced, Power saving (0). | Performance |

**Limits and gotchas.**

- **One Apply restarts every radio**, so every Wi-Fi client reconnects. A change to puncturing or mitigation rows only is
  applied live, with no restart (4.10.3).
- **MLO locks parts of this page**: the scheduler, and switching a radio off.
- A value a rule forces (for example MU-MIMO following OFDMA) is written at Apply if the stored value disagrees.

#### 4.25.2 WPS

**What it is.** Wi-Fi Protected Setup: joins a device by a button press or a PIN instead of typing the password. WPS is
**off at factory** (8.1); its PIN method is weak by design. Turn it on only for a device with no other way in, and off
again afterwards. Stock feature, Reaper page.

**How to use it.**

1. **Wireless > WPS.** Choose the band in **Current Frequency** first (2.4 or 5 GHz; 6 GHz cannot run WPS). The band can
   only be changed while WPS is off.
2. Turn **Enable WPS** on. This applies at once and restarts the wireless.
3. **WPS Method**: **Push button**, then **Start** and press the WPS button on the device; or **Client PIN Code**, type
   the device's 8-digit PIN (one space or hyphen in the middle is accepted) and press **Start**.
4. **Connection Status** follows the exchange (a spinner while it runs).
5. Turn **Enable WPS** off.

**The settings.**

| Setting | What it does | Default |
|---|---|---|
| Enable WPS | On/off; applies at once with a wireless restart. Refused, with the reason, when the band's network is hidden, uses WPA or WEP only, uses WPA3-Personal, or the radio is off. | Off |
| Current Frequency | The radio WPS runs on. Locked while WPS is on. | - |
| Connection Status | The WPS state; *Not used* while off. | - |
| Configured | Yes/No. With Yes, **Reset** generates a new network name and key on that band; it asks first. | - |
| AP PIN Code | The router's own PIN, for a device that asks for the access point's PIN. | - |
| WPS Method | Push button or Client PIN Code. A PIN must be 8 digits with a valid checksum. | Push button |

**Limits and gotchas.** WPS is refused for a hidden network, for WPA-only or WEP security and for WPA3-Personal alone;
WPA2-Personal and WPA2/WPA3-Personal work. **Reset** changes the network name and password on that band: every device
must be joined again.

#### 4.25.3 WDS

**What it is.** WDS (Wireless Distribution System) links this router's radio directly to other access points, bridging
their networks into one. Each peer must list this router's radio MAC address, and both ends need the same band and the
same fixed channel. Stock feature, Reaper page; the peer scan uses Reaper's site survey, which covers 6 GHz and runs only
when you press **Scan now**.

**How to use it (a WDS bridge between two routers):**

1. On both routers, set the band to the same fixed **Control Channel** (and width) on Wireless > Settings. A band on
   Auto shows *This band uses the Auto channel. WDS peers must share one fixed channel* with a link.
2. **Wireless > WDS** on this router: note the band's **MAC address** shown at the top of its panel.
3. Set **AP Mode** to **Hybrid** (access point and WDS) or **WDS Only** (bridge only, no clients on that band).
4. Turn **Connect to APs in list** on, then add the peer: **Scan now** and pick it under **AP Survey**, or type its
   radio MAC address, and press **Add**.
5. Apply (the wireless restarts). Do the same on the peer with this router's MAC address.

**The settings.** Per band:

| Setting | What it does | Default |
|---|---|---|
| AP Mode | **AP Only** (no WDS), **WDS Only**, **Hybrid**. With AP Only the list is greyed. | AP Only (`wlN_mode_x` `0`) |
| Connect to APs in list | On: bridge only to the listed peers. Off: accept any WDS peer (lazy WDS). | Off |
| Remote AP List | Up to 4 peer MAC addresses, with the network name from the last scan. | Empty |
| AP Survey, Scan now | Scans this radio's channels and lists the networks heard, strongest first. The radio leaves its channel briefly. Refused while a capture or Auto Scan runs on Wireless Quality. | - |

**Limits and gotchas.** A band that serves as the router's repeater uplink is not editable. Wireless channel, width and
mode are not posted from this page (stock re-sent stale copies). With **Connect to APs in list** off, any WDS peer that
knows the band can attach; keep it on. AiMesh (the AiMesh menu) is the other way to extend coverage between ASUS
routers.

#### 4.25.4 Wireless MAC Filter

**What it is.** A per-band list of device MAC addresses the radio admits (**Accept**) or refuses (**Reject**). It acts
on the main network of each radio; guest networks keep their own filter on the Network menu (4.21). Stock feature,
Reaper page; changing between Accept and Reject keeps the list (stock emptied it).

**How to use it (block one device from Wi-Fi):**

1. Find the MAC address the device uses on this network: **Devices** (4.8). Phones use a private address per network,
   so take the one shown there, not the one printed on the device.
2. **Wireless > Wireless MAC Filter.** On each band's panel, turn **Enable MAC Filter** on and set **MAC Filter Mode** to
   **Reject**.
3. Pick the device under **Device** (wireless devices online now) or type its MAC (`00:00:5e:00:53:21`), press **Add**.
4. Repeat on every band the device could use, then Apply (the wireless restarts).

**The settings.** Per band:

| Setting | What it does | Default |
|---|---|---|
| Enable MAC Filter | Off: no filtering. | Off (`wlN_macmode` `disabled`) |
| MAC Filter Mode | **Accept**: only the devices in the list can connect. **Reject**: the devices in the list cannot connect. | Accept (when first turned on) |
| List (Device, MAC address) | Up to 64 entries per band; names come from the Devices page. | Empty |

**Limits and gotchas.**

- **Accept with an empty list is refused**: it would cut off every wireless device on that band.
- **A MAC filter is not access control.** A device can change its MAC, and a phone's private address changes when the
  private-address setting is reset. Gatekeeper (4.2) holds devices at the gate across wired and wireless.
- Accept mode keeps out every new device, including a new phone of your own, until its MAC is added on each band.

#### 4.25.5 RADIUS Setting

**What it is.** The RADIUS server used when a network is set to an Enterprise mode (WPA2-Enterprise, WPA3-Enterprise
and their mixes; 802.1X). **Enterprise Wi-Fi is available in Reaper**: the main network's security, including the
Enterprise modes and their RADIUS server, is chosen on the **Network** menu (4.21); Employee networks there take their
own server. Once the main network is a Network-page network (every configured router), this tab shows the main
network's server **read-only**: its mode (*In use: the main network uses WPA2/WPA3-Enterprise*, or *Not in use: ...*),
the server address and port, and whether its secret is set - never the secret itself. **Open the Network page** takes
you there to change it. A router whose main network is not a Network-page network yet (factory state, before the first
apply) still gets the per-radio editor described below. Stock feature, Reaper page.

**How to use it (enterprise Wi-Fi with a RADIUS server):**

1. Set up the RADIUS server (for example on a LAN host at `192.168.50.5`, UDP port 1812) with this router as a client
   and a shared secret.
2. **Network** menu (4.21): open the main network, set its security to **WPA2-Enterprise** (or WPA3-Enterprise where
   offered) and enter the server address, port and secret in its RADIUS settings. Apply.
3. **Wireless > RADIUS Setting** shows that server and *In use*. To change the server or rotate the secret, use the
   Network page again; this tab does not edit it.
4. Join a device with its user name and password (or certificate) as the RADIUS server requires.

**The settings.** (Per-radio editor, shown only while the main network is not a Network-page network.) Per band:

| Setting | What it does | Default |
|---|---|---|
| Server IP Address | IPv4, or IPv6 in router mode. Empty clears the server. | Empty |
| Server Port | 1 to 65535. | 1812 |
| Connection Secret | The shared secret, up to 64 printable characters, no double quote at either end. The field stays empty; a saved secret shows as dots, and typing replaces it. **Show password** shows what you typed. | Empty |

**Limits and gotchas.** The read-only view shows one panel per distinct main-network setting (with Smart Connect off
the Network page keeps one entry per band; alike entries are shown once). If the saved server list cannot be read
safely (a secret containing `<` or `>`), no server is shown and the page says so - check it on the Network page. With
Smart Connect grouping bands, the per-radio editor's lead-band server is copied to the others at the wireless restart.
Guest and portal networks do not offer RADIUS.

#### 4.25.6 Roaming Block List

**What it is.** A list of wireless devices the Roaming Assistant leaves alone: they are not steered between the AiMesh
router and its nodes. The list goes to the nodes through AiMesh. Shown only when this router is the AiMesh router.
Stock feature, Reaper page; the list is read from all three radios and written to all three, so a list that had drifted
apart on stock no longer loses entries.

**How to use it (keep a device on the main router):**

1. Join the device where it should stay (near the main router).
2. **Wireless > Roaming Block List.** Turn **Enable roaming deny list** on.
3. Pick the device under **Device** or type its MAC address, press **Add**, then Apply (the wireless restarts).

The device then stays on the router or node it chose itself; the router no longer disconnects it to push it towards a
stronger one. Whether it later roams on its own is the device's decision.

**The settings.**

| Setting | What it does | Default |
|---|---|---|
| Enable roaming deny list | On: the listed devices are exempt from roaming steering. | Off (`rast_static_cli_enable` `0`) |
| List (Device, MAC address) | Up to 64 devices; the same list on every radio (`wl0/1/2_rast_static_client`). | Empty |

**Limits and gotchas.** The Roaming Assistant itself (threshold, or off) is on Wireless > Settings, per band. A separate
Tweaks switch (8.2, `disable_exap`) stops the assistant disconnecting a device an AiMesh node reports as its own.

#### 4.25.7 MLO

**What it is.** Wi-Fi 7 Multi-Link Operation: a device connects on several bands at once. The **MLO** switch is the
master for both MLO backhaul (AiMesh links) and MLO fronthaul (networks for clients). Below it, **Profile List** shows
the MLO networks: the **AiMesh Wireless Backhaul** first, then each MLO fronthaul network with its status and any time
remaining. Stock feature, Reaper page.

**How to use it (turn MLO on):**

1. **Wireless > MLO.** Turn the **MLO** switch on.
2. The confirmation lists what changes on every band: radios that are off are switched on, wireless schedules are
   switched off; Wi-Fi 7 is turned on with AES + GCMP-256 encryption. Then *Your router and node(s) in the AiMesh system
   are going to reboot* and *If Wi-Fi accepts no devices after the restart, unplug the router for about 10 seconds and
   plug it back in*. Confirm.
3. The router (and its AiMesh nodes) reboot; the page returns when the router answers again.
4. If afterwards no wireless device can join, the dashboard shows **Wi-Fi needs a power cycle**, or its MLO row reads
   *Partial*, unplug the router for about 10 seconds (2.8). Turning MLO off shows the same note.
5. To add a network for MLO clients, press **Add a Network**: it opens the MLO wizard on the Network page (4.21). An MLO
   fronthaul network is edited or removed there; **Modify** on its row opens that page.

**The settings.**

| Setting | What it does | Default |
|---|---|---|
| MLO | On: as above, then reboot. Off: every MLO fronthaul network goes off with it (the main network loses MLO and keeps its bands - the bands of every stored entry, and the band list is left alone when none can be read; other MLO networks are disabled), then reboot; it says so first. | Off (8.3) |
| Wireless Setting > GO | Opens Wireless > Settings. | - |
| Profile List | The MLO networks with Status (Active / Inactive). | - |
| AiMesh Wireless Backhaul: Network Name (SSID), Hide SSID | **Modify** on the backhaul row opens them; 1 to 32 bytes. Apply restarts the wireless and that network only. | - |
| Authentication Method | WPA3-Personal (shown). | - |
| Wireless Security | The backhaul password, masked; **Show** fetches it on click. | - |

**Limits and gotchas.** While MLO is on, Wireless > Settings refuses to switch a radio off and holds the scheduler off.
With MLO on, the three AiMesh backhaul carriers are one link set (4.10.13). A change of the MLO switch always reboots.

#### 4.25.8 Smart Connect Rule

**What it is.** **Network Tools > Smart Connect Rule** sets how Smart Connect (band steering) moves devices between the
bands that share one network name. The rules apply only to bands in the Smart Connect group; a band outside it shows
`- -` (*Not in the Smart Connect group*), which is normal, and its settings come back when it is added. 6 GHz is left
out of the group by default on some models. Wireless clients per band are on **System Log > Wireless Log**. Stock
feature (Broadcom band steering), Reaper page; three stock faults are not carried (load balance could not be turned
off, a capability choice piled bits onto the previous ones, and Restore defaults also reset the TX chain mask).

**Smart Connect on or off.** On these models the main network is a Network-menu profile; the page then says so and
**Open the Network page** opens it, where the bands of the main network are chosen (4.25.1). On a model without it,
**Turn on** / **Turn off** switches Smart Connect here and restarts the wireless.

**How to use it.** Change a value in a band's column, Apply (the wireless restarts). **Restore defaults** puts every rule
back to its factory value, asks first and restarts the wireless.

**The settings.** Per band in the group:

| Setting | What it does | Default |
|---|---|---|
| **Steering trigger** - when a band starts moving its devices to another band | | |
| Load balance | On: steer to balance load; the threshold rows below are greyed. | - |
| Bandwidth utilisation | Steer when the band is busier than this, 0 to 100 %. | - |
| RSSI | Steer a device whose signal is Less or Greater than the value, -100 to 0 dBm. | - |
| PHY rate less than / greater than | Steer a device whose link rate is below / above the value, 0 to 11530 Mbps. | - |
| Wireless mode | Which devices may be steered: All, 802.11ac/ax only, 802.11a/b/g/n, 802.11ax only, 802.11a/b/g/n/ac. | - |
| **Device selection** - which devices are moved | | |
| RSSI, PHY rate less than / greater than, Wireless mode | As above, choosing the devices to move. | - |
| **Target bands** - where moved devices go | | |
| Target 1, Target 2 ... | The other bands in order of preference; from the second choice on, `-` ends the list. | - |
| Bandwidth utilisation, Wireless mode | When a band qualifies as a target. | - |
| **Bounce detection** - stops a device being moved back and forth | | |
| Window time, Counts, Dwell time | Within the window (s), a device moved this many times is left where it is for the dwell time (s); 0 to 9999. | 60 s, 2, 180 s |

**Limits and gotchas.** Every Apply restarts the wireless. Values out of range are refused before anything is sent. A
device that keeps its own band choice (many do) may ignore steering.

### 4.26 System Log

The **System Log** menu holds the router's read-out pages: **General Log**, **Wireless Log**, **DHCP leases**,
**IPv6**, **Routing Table**, **Port Forwarding**, **Connections** and **Long-Term Storage**. All are Reaper pages; apart
from the static-route editor on Routing Table and the settings at the foot of General Log they only read. DHCP leases,
IPv6, Routing Table, Port Forwarding and Connections are shown in router mode only; IPv6 only while IPv6 is enabled.

#### 4.26.1 General Log

The system log, with **Find** / **Exclude**, **Saved exclusions** and the **Log settings**: section 2.12 describes the
page in full, with the tags Reaper writes.

**Auto refresh** reloads the log every 10 seconds while the page is in view. It is on the first time; after that the
page keeps your choice in the browser (from the image after v3.8.0 - before, it switched itself back on at every
visit). A private window cannot keep the choice, so there it starts on.

#### 4.26.2 Wireless Log

**What it is.** The devices connected to each radio, per network, with signal and link rate; Reaper's page, replacing
the stock text dump.

**Two addresses for one Wi-Fi 7 device.** A Wi-Fi 7 phone or PC joins a radio with a link address that can differ
from the device's own address. This page reads the radios, so it lists the link address; the Devices page, DHCP
leases and Gatekeeper list the device's own address. The name is the same in both places. Switching off the
phone's private (random) address does not change this.

**How to use it.**

1. Open **System Log › Wireless Log**. Each radio has a card: **Channel**, **Channel use** and **Mode** in its
   heading, *This radio is off.* when it is.
2. Under each radio the networks it carries are listed by name and type (*Main network*, *Guest Network*, *IoT
   Network*, *Guest Portal*, *Multi-Link Operation (MLO)* and the other Network-page profiles); the radio's own
   *Primary BSS (mesh backhaul)* carries AiMesh nodes, marked *AiMesh Node*.
3. Each client row: **Name** (the device label, 4.8.1), **IP address**, **MAC address**, **RSSI** (signal in dBm), **Rx / Tx
   Mbps**, **Connected** (how long), **Link** (spatial streams, PHY and channel width) and **Flags**. The list opens
   sorted by signal, strongest first; click a column heading to sort another way (kept in your browser).
4. **Refresh every** *Off* / 3 s / 5 s / 10 s (10 s until you pick one; your pick is kept in your browser). **Refresh**
   reads once now. Reading stops while the browser tab is hidden.
5. **Show driver details** under **Driver details** opens the wireless driver's own low-level dump, for
   troubleshooting (*The driver returned no details.* when it has none).

**Flags**: P power save, S short guard interval, T STBC, M MU-MIMO, A associated, U authorised. A client that is
associated but not authorised (no U) has not finished the key exchange: a wrong Wi-Fi password, or a device stuck
mid-join.

**When to use it.** To see which band and network a device is on, whether it has a usable link rate, and whether a
device that cannot get online is associated at all. For the history of a device's signal, use Wireless Quality
(4.10.12).

#### 4.26.3 DHCP leases

**What it is.** Every address the router's DHCP servers have handed out, on the main LAN and on every guest or VLAN
network, with the time left on each lease.

| Column | Shows |
|---|---|
| **Name** | The name you gave the device on the Devices page; empty if you have not named it (4.8.1) |
| **Hostname** | The name the device sent; else the maker of its network card; `Private-Address` for a randomized MAC |
| **IP address** / **MAC address** | The lease |
| **Lease time left** | Days, hours and minutes; *Address set on the device (no DHCP)* for a device on a DHCP network that is active but holds no lease, because its address was typed in on the device itself |
| **VLAN** | The network the lease belongs to; shown only when a lease on a guest or VLAN network exists |

The pill counts the leases. Click a heading to sort (kept in your browser); rows with the same value fall back to
address order. **Refresh** asks the DHCP servers for fresh times and reloads the page; the button shows *Working...*
until the new list is there (about a second, longer on a big network).

**DHCP leases kept across a restart (v3.8.0).** The DHCP server keeps its lease lists in RAM, so after a reboot a
device that still held a lease was missing from this page, the Devices page and every name lookup until it renewed,
which for a wired device can take half a day. The router now keeps a copy in flash, `/jffs/reaper/leases/` (root
only), together with the names devices announced:

- the copy is written when the set of leases changes, at least hourly while the times change, and at every reboot or
  shutdown, before the services stop;
- at start the copy is put back before the DHCP servers start, only where no live list exists, and only if every line
  of it is well formed (a damaged copy is not restored);
- the lists hold the time **left** on each lease, not an expiry date, so no clock is needed to restore them. The time
  the router was off is not subtracted: a device that left while the router was off keeps its row until that time
  runs out.

The result: every device that still holds a lease is listed and named right after a restart. A row with *Address set
on the device (no DHCP)* is now almost always a device with a typed-in address.

**There is no Remove button.** A DHCP server has no way to make a device ask for a new address at once (the
FORCERENEW message exists but almost no device supports it), so removing a lease would only hide a device that still
uses its address until it next renews. To move a device to another address, reserve one on the LAN page or with **Pin
IP** on the Devices page (4.8.2); it moves at its next renewal, or at once if you reconnect it.

#### 4.26.4 IPv6

Shown while IPv6 is enabled (*IPv6 is not enabled.* otherwise). Three cards:

- **IPv6 configuration**: the router's IPv6 connection as the router reports it (connection type, addresses, prefix,
  DNS servers), one item per row.
- **IPv6 clients**: each device with its **Name**, **Hostname** (4.8.1), **MAC address** and every **IPv6 address** the router
  has seen it use, one per line.
- **IPv6 firewall pinholes**: the inbound IPv6 openings devices asked for over UPnP IGD2: **Protocol**, **Remote
  address** / **port**, **Local address** / **port**. *Pinholes are off (UPnP IGD2 setting).* when the setting
  `upnp_pinhole_enable` is off. Shown on builds with UPnP IGD2 only.

**Refresh** reads again. Use it to check that a device has a global IPv6 address, and which address to use for a
firewall rule or a ping test.

#### 4.26.5 Routing Table

Two tabs.

**Routing table (read-only).** Every routing table on the router and the rules that choose between them, for IPv4 and
IPv6: the **rules** (**Priority**, **Rule**, **Table**) in the order the kernel consults them, then each table in that
order (**Main table**, **Default table**, each VPN client's table, Policy Routing's tables), with **Destination**,
**Gateway**, **Interface**, **Source address**, **Metric** and **Origin / scope**. **Show the local table** adds the
table of the router's own addresses, hidden by default. The stock page showed the main IPv4 table only, which hid
every VPN Director and Policy Routing route (4.4, 4.20.2); this one is where to check that a rule points at the table
you expect.

**Static routes.** Routes to networks behind another router on your LAN or WAN (a lab router, a second site behind a
VPN appliance).

1. Switch **Enable static routes** on.
2. Fill **Network/Host IP**, **Netmask**, **Gateway**, **Metric** (0-999, optional) and **Interface**: *LAN* (a
   gateway on your LAN), *WAN* / *MAN* (the provider side), *VPN* (the PPTP / L2TP client's interface).
3. **Add**. **Edit** loads a row back into the form; **Delete** removes it.
4. **Apply**. The page asks first: the LAN and the Internet connection restart for about 10 seconds.

The page refuses a network address with bits outside its netmask, a duplicate, and a list that would not fit: up to
64 routes, and the list must stay under about 990 bytes (the counter shows rows and bytes; the router's settings
store silently drops a longer value, so the page refuses it instead). **Discard** drops unsaved edits.

Example: a lab network `198.51.100.0/24` behind a router at `192.168.50.2` on your LAN: Network/Host IP
`198.51.100.0`, Netmask `255.255.255.0`, Gateway `192.168.50.2`, Interface *LAN*. The lab router needs a route back
to your LAN (or NAT) as well.

#### 4.26.6 Port Forwarding

**What it is.** The port forwards in force right now, read-only:

- **Port forwarding rules**: the forwarding (DNAT) rules in the firewall, with **Source**, **Protocol**, **External
  port**, **Forward to**, **Local port** and **Created by**: *Port forwarding* (your rules on WAN › NAT and Port
  Forwarding, 4.23) or *Gatekeeper (held device page)* (the redirect Gatekeeper uses to show a held device its page,
  4.2.3).
- **UPnP, NAT-PMP and PCP**: the forwards devices opened themselves, with **Description** and **Time left**. *UPnP is
  off, so no device can open ports.* when UPnP is off.

Use it to confirm a forward you made is active, and to see what a game console or a NAS opened without asking. To
change a rule, use WAN › NAT and Port Forwarding; to stop devices opening ports, switch UPnP off there.

#### 4.26.7 Connections and Long-Term Storage

**Connections** is the live flow explorer (4.9). **Long-Term Storage** chooses where history is kept and which datasets
are collected (4.11).

### 4.27 Administration

The **Administration** menu holds the router-wide settings. Its tabs, in menu order:

| Tab | Page | Owner | Section |
|---|---|---|---|
| Operation Mode | `Reaper_OpMode.asp` | Reaper page, stock choices | Below (shown unless the model hides the mode switch) |
| System | `Reaper_System.asp` | Reaper page, stock settings | 4.27.1 to 4.27.6 |
| DNS Failover | `Reaper_Failover.asp` | Reaper | 4.14a, 4.14b (routing modes only) |
| Firmware Upgrade | `Reaper_Firmware.asp` | Reaper | 4.14 |
| Backup & Restore | `Reaper_Backup.asp` | Reaper | 4.27.8 |
| System Temperature | `Advanced_PerformanceTuning_Content.asp` | Stock | Only on a model with fan control; none of the current models has it |
| SNMP | `Reaper_SNMP.asp` | Reaper page, Merlin agent | 4.27.9 |
| Tweaks | `Reaper_Tweaks.asp` | Reaper | 4.17 and 4.27.10 |
| Diagnostics | `Reaper_Diag.asp` | Reaper | 4.13 |
| Data Export | `Reaper_Analytics.asp` | Reaper | 4.11 |

**System Info** is a menu of its own (4.27.11). `Reaper_SecBanner.asp` is not a page (4.27.12).

**Operation Mode** (`Reaper_OpMode.asp`) switches the router between the operation modes the model offers (wireless
router and the others); it lists them, marks the one in use and describes the one you pick. The mode decides which menus exist: in a mode that does not route (access point, repeater,
media bridge), Parental Controls, the Firewall, Traffic Manager, DNS Failover and the other routing features are
hidden, as on stock.

**How to switch mode.** Pick the mode on **Operation Mode** and press **Save**. For **Access Point**, **Media Bridge**
and a return to **Router** the router opens Reaper's step page (`Reaper_ModeSetup.asp`, v3.4.5), which shows the mode
you are in and the one you are going to at the top:

| Switching to | Steps | What happens |
|---|---|---|
| Access Point | **Address** (automatic from the main router, or a fixed address, mask, gateway and DNS), **Review** | Cable this router's WAN port to a LAN port of the main router. The main router keeps routing; this one adds Wi-Fi and wired ports. |
| Media Bridge | **Main network** (a scan of nearby networks, strongest first, or a hidden network typed with its band and security), **Password** (skipped for an open or OWE network), **Address**, **Review** | Joins the main router over Wi-Fi and gives its LAN ports to wired devices; it broadcasts no Wi-Fi of its own. WEP, Enterprise-only and unknown security are not offered. |
| Router | **Review** | Becomes the main router again: the modem goes into its WAN port. |

**Apply** on Review saves the stock wizard's keys for that mode and reboots; the page waits through the reboot. After
a switch to Access Point or Media Bridge the router takes the address the main router gives it (or the fixed one):
find it in the main router's client list, or open `<hostname>.local`. On models with guest networks, a switch between
Router and Access Point asks first, because the guest networks are rebuilt for the new mode. **Repeater** and **AiMesh Node** still open the stock
setup wizard for their steps (9.3).

#### 4.27.1 System: how the page works

**What it is.** Reaper's replacement for the stock System page (`Advanced_System_Content.asp`, which no longer
ships). Every setting the stock page posted is here, under the same nvram keys, in five tabs: **Login and access**,
**SSH**, **Time and NTP**, **Hardware** and **Maintenance**; a sixth, **Accessibility**, holds the colour-blind mode
switch (4.27.7). A tab whose panels do not apply to the model or the
operation mode is hidden. On a phone (from the image after v3.8.2) the menu's tab bar keeps its size: a page wider than the screen
pans sideways instead of shrinking the tabs, and long values such as the remote-access address wrap inside the screen.

- **Apply** (top right) saves every tab at once. It posts only the settings that differ from what the router holds,
  and restarts only the services those settings need: the time service for the time zone, NTP and the reboot
  schedule; SSH for the SSH settings; the LEDs; USB hibernation; the web server for the protocol and the ports;
  the firewall for remote access, access restrictions, SSH, the WAN-down notice and the local NTP server.
  A change that needs nothing restarted is only saved; a change of colour-blind mode reloads the whole window.
- **Unsaved changes: N** counts the edited settings; each tab with an edit carries a dot. **Discard** reloads the page.
- A setting that fails its check opens its tab, marks the row in red and names the rule. Nothing is saved until every
  check passes.
- A panel that fails to load says so (*This section did not load, so Apply leaves its settings unchanged*). Apply then
  leaves that panel's settings as they are rather than posting blanks.
- Changing the **web protocol or a web port** restarts the web server; the page follows the interface to its new
  address after about 10 seconds.
- Changing the **USB mode** asks first and reboots the router.

The header pill shows the time zone in effect (amber while none is chosen).

#### 4.27.2 System > Login and access

**What it is.** The router login, the web interface on the LAN, its certificate, web access from the internet and the
list of addresses allowed to reach the interface and SSH.

**How to use it: change the login**

1. Open **Administration > System**, tab **Login and access**, panel **Router Account**. The current login name is
   shown; press **Change login**.
2. Enter the **Current login password** (not asked while the password is still the factory one).
3. Enter the **New login name** and the **New password** twice. Press the box's own **Apply**.
4. The router saves the account and signs you out. Sign in with the new name and password.

The new password is also the SSH password (4.27.3). The login name is also the SNMPv3 user name (4.27.9) and the
first account of the USB file services (4.28.2), so those follow the change.

**Rules for the login.** Name: 2 to 32 letters, digits, `-` or `_`, starting with a letter or digit; not `root`,
`guest` or `anonymous` in any case; the sign-in compares the name exactly (2.3). Password: 5 to 32 printable ASCII
characters, not starting or ending with `"`, not equal to the login name and not the factory default. On a model that
reports the secure-default flag the password needs 10 or more characters with a letter, a digit and a symbol. A wrong
current password is refused; repeated failures sign you out as the login page does.

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Router Login Name / **Change login** | The admin account for the web interface and SSH (`http_username`, `http_passwd`). | `admin` / `admin` (8.3) |
| Enable Login Captcha | Shows a CAPTCHA on the login page to slow password guessing (`captcha_enable`). Shown where the model offers it. | Off |
| Web access protocol | HTTP, HTTPS, or HTTP + HTTPS on the LAN (`http_enable` 0 / 1 / 2). Greyed out at HTTP on a model without HTTPS. | HTTP + HTTPS |
| HTTP LAN port | Port of the plain-HTTP interface (`http_lanport`), 1 to 65535. Hidden with HTTPS only. | 80 |
| HTTPS LAN port | Port of the HTTPS interface (`https_lanport`), 1 to 65535; the link beside it opens that address. Must differ from the HTTP port. | 8443 |
| Auto Logout | Minutes of inactivity before the session ends (`http_autologout`); 0 keeps it open, otherwise 10 to 999. Applies to Reaper and stock pages alike. | 30 |
| Installed server certificate | Issued to, Issued by and Expires of the web interface certificate (HTTPS models). Read only. | - |
| Export Server Certificate | Downloads the certificate with its key (`cert_key.tar`). | - |
| Export root certificate | Downloads the root certificate (`cert.crt`) to install as trusted on your computers. | - |
| Renew server certificate / Renew root certificate | Generates a new self-signed certificate (the root renewal asks first). The web interface reloads; sign in again. | - |
| Enable Web Access from WAN | Opens the web interface on the WAN (`misc_http_x`). Router mode only. On an HTTPS model it is HTTPS only; switching it on while the LAN protocol is HTTP only changes the protocol to HTTP + HTTPS. | Off |
| HTTPS Port of Web Access from WAN | The WAN port (`misc_httpsport_x`), 1024 to 65535; must differ from the SSH port while SSH is on. (`misc_httpport_x`, 8080, on a model without HTTPS.) | 8443 |
| Reachable at | The address the interface answers at from the internet: the DDNS host name when DDNS is on, else the WAN address. Read only. | - |
| Enable Access Restrictions | Only the listed addresses may open the web interface or SSH (`enable_acc_restriction`, `restrict_rulelist`; the legacy `http_client` and `http_clientlist` are kept in step). The list takes IPv4 addresses, and **IPv6 access to the web interface and SSH is blocked while this is on** (otherwise any device could go around the list over IPv6); the page says so, and asks first when you are connected over IPv6 yourself. Router mode only. | Off |
| Address list | Up to 4 entries: an IPv4 address or subnet (`192.168.50.10`, `192.168.50.0/24`), each with **Enabled**, **Web interface** and **SSH** ticks. | Empty |

The certificate buttons shown depend on the certificate type chosen on **WAN > DDNS** (4.23): with a Let's Encrypt
certificate only the server certificate can be exported, and with an imported certificate the root certificate cannot
be renewed here. With the protocol at HTTP only, the renew buttons are hidden. The link
**Manage the certificate on the DDNS page** opens that page.

**Examples**

- Admin only over HTTPS on port 8443: protocol **HTTPS**, HTTPS LAN port `8443`, **Apply**. The browser moves to
  `https://192.168.50.1:8443/`. Install the exported root certificate on your computer, or accept the warning once.
- Only one management PC: **Enable Access Restrictions** on, add `192.168.50.10` with **Web interface** and **SSH**
  ticked, **Apply**. Every other device on every network now gets no answer on the web and SSH ports.

**Limits and gotchas**

- Keep **Enable Web Access from WAN** off (2.13). The Firewall Status tab's exposure card (4.1.1) lists what is open.
- An access restriction list needs at least one enabled entry with **Web interface** ticked; the page refuses one
  without, because it would lock everyone out of the interface.
- The access restriction is enforced by the firewall on the web ports and the SSH port, from every side, the LAN
  included. Its addresses are IPv4 only, and once the list holds an entry, the web interface and SSH are refused over
  **IPv6** altogether (the IPv6 rule ends in a drop with no entry that could match).
- A device whose address changes falls out of the list. Pin it first (4.8.2).
- The certificate buttons and a protocol or port change all restart the web server; open sessions end.
- **Wrong passwords lock one address, not the LAN (v3.7.5).** Five wrong passwords from one address refuse that
  address for 5 minutes; the login page then says that other addresses can still sign in. Twenty failures on one side
  (LAN or WAN) within 5 minutes stop new sign-ins on that side for 5 minutes - except from an address that signed in
  correctly before and has not failed since - and a device that is already signed in keeps working (before, they
  turned away every browser on that side). On the LAN every device is counted by its own address, IPv6 included.
  A connection on the remote-access listener counts as the
  WAN side, and an IPv6 address is judged by its own address (before v3.7.5 five failures locked every browser on that
  side, signed-in admins included, and any IPv6 address counted as the LAN). Locked out of your own PC: wait 5 minutes or
  sign in from another device. The Security Review (4.1.1b) reports bursts of 10 or more failures from one source.
- **A sign-in must finish within 15 seconds (v3.7.6)**, so a slow or stalled client cannot hold the interface for
  everybody. Every save from a page carries a per-boot page token; a save without it is refused and logged as
  `apply without the page token refused` (v3.7.0). Scripts that post settings are not affected.
- **The ASUS Router phone app is not supported (v3.8.4).** Manage the router from a browser. The app's ASUS
  account and remote connection went with the phone-home code (1.2), and from v3.8.4 the request addresses only
  the app used - family groups, per-device internet blocking, the remote-control switch, the notification centre,
  its own way of creating guest and IoT networks, the speed test between AiMesh nodes - are gone. Whatever the app
  still shows or changes on the LAN is not tested and can stop working in any release. A request that names the app
  in its User-Agent gets the same checks as a browser - the cross-site and Referer checks, the page token on a
  save, saves by POST only - because any client can claim that name.

#### 4.27.3 System > SSH

**What it is.** The router's SSH server (dropbear, from Asuswrt-Merlin). It gives a root shell, and SFTP: an
`sftp-server` ships in the image, so files on a USB disk can be copied over SSH without FTP. No Telnet server ships
at all (8.3).

**How to use it: allow SSH with a key, from the LAN only**

1. On your computer, make a key pair if you have none (`ssh-keygen -t ed25519`) and copy the one line of the
   **public** key (`~/.ssh/id_ed25519.pub`).
2. Open **Administration > System**, tab **SSH**. Set **Enable SSH** to **LAN only**.
3. Leave **SSH Port** at 22 or choose another (1 to 65535, not a web or OpenVPN server port).
4. Paste the public key line into **Authorized Keys** (one key per line).
5. Switch **Allow Password Login** off, so only the key is accepted. The page refuses this with no key present.
6. Press **Apply**, then connect: `ssh admin@192.168.50.1` (the router login name, 4.27.2).

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Enable SSH | **No**, **LAN only** (`sshd_enable` 2) or **LAN and WAN** (`1`). The WAN choice exists in router mode only; in other modes a stored `1` reads as LAN only. | No |
| SSH Port | The port SSH listens on (`sshd_port`). | 22 |
| Allow Password Login | Accept the router password as well as keys (`sshd_pass`). Off = keys only. | On |
| Allow SSH port forwarding | Lets an SSH client open local and remote tunnels through the router (`sshd_forwarding`). | Off |
| Authorized Keys | Public keys allowed to log in, one per line (`sshd_authkeys`; written to root's `authorized_keys` when SSH starts). | Empty |
| Idle Timeout | Minutes before an idle shell session is closed (`shell_timeout`, stored in seconds); 0 keeps it open, otherwise 10 to 999. Shown even with SSH off. | 20 (1200 s) |

**Examples**

- SFTP to a USB disk: `sftp admin@192.168.50.1`, then `cd /mnt/<volume label>`.
- A non-standard port: SSH Port `2222`, then `ssh -p 2222 admin@192.168.50.1`.

**Limits and gotchas**

- **LAN and WAN** puts a root login on the internet. Do not use it (2.13); a VPN into the LAN is the safer path. When
  it is on with the IPv6 firewall, Reaper drops a flood of new connections from one /64 (2.9).
- Combine SSH with **Enable Access Restrictions** (4.27.2) and tick **SSH** on the entries that may use it.
- With the Security Review on (2.9), a change to the authorized keys is reported as a change.
- The idle timeout ends a shell left open; a running copy over SFTP is not idle.

#### 4.27.4 System > Time and NTP

**What it is.** The time zone, its daylight-saving rule, the time servers and an optional NTP server for the LAN.
The router's clock drives every schedule (reboot, Parental Controls, Wallguard service schedules, the firmware check).

**How to use it: set the time zone and NTP**

1. Open **Administration > System**, tab **Time and NTP**.
2. Choose the **Time Zone**. A zone with daylight saving shows two more rows, **DST start** and **DST end**
   (month, week, weekday, hour), pre-filled from the bundled zone table. Change them only if your region differs.
3. In **NTP Server** keep `pool.ntp.org` or pick `time.nist.gov` or `time.cloudflare.com` from the list; add a
   **Secondary NTP server** if you want a fallback. A host name or an IPv4 address.
4. Optional, router modes only: **Enable local NTP server** serves time to the LAN; **Intercept NTP client
   requests** then answers every NTP request passing the router, so devices with hard-coded servers stay in sync.
5. Press **Apply**. The header pill shows the zone.

A reminder appears under the zone when it is more than an hour away from your browser's own offset.

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Time Zone | The stock zone list (`time_zone`). A zone with DST sets `time_zone_dst` to 1. | `GMT0`; set from the browser at the first password change (2.3) |
| DST start / DST end | The daylight-saving rule (`time_zone_dstoff`, e.g. `M3.2.0/2,M10.5.0/3`). Start and end may not be the same day. | From the zone table |
| NTP Server | Primary time server (`ntp_server0`). | `pool.ntp.org` |
| Secondary NTP server | Second time server (`ntp_server1`). | Empty |
| Enable local NTP server | The router answers NTP on the LAN (`ntpd_enable`). Routing modes, where the model has it. | Off |
| Intercept NTP client requests | Redirects LAN NTP traffic to the router's server (`ntpd_server_redir`). Shown while the local server is on. | Off |

**Limits and gotchas**

- Until the first successful sync after a boot the clock is not trusted: the Parental Controls page warns, Wallguard
  keeps scheduled services blocked (4.3.3.6), and certificate checks can fail. The diagnostics report warns when the
  clock never synchronised (2.10).
- Warden's **Also filter the router itself** exempts NTP (UDP 123), so it cannot stop the sync (4.3.1).
- The local NTP server's switch also restarts DNS and the firewall.

#### 4.27.5 System > Hardware

**What it is.** LEDs and buttons, power and memory, and the USB port behaviour. Each row appears only on a model that
has the hardware; the tab is hidden when none applies.

| Setting | What it does | Default |
|---|---|---|
| Enable LEDs | All front LEDs on or off (`AllLED`). | On |
| WPS Button behavior | What the WPS button does: **WPS**, **Wi-Fi on/off** or **LED on/off** (`btn_ez_radiotoggle`, `btn_ez_mode`). Shown when the model offers more than one choice. | Model default |
| Boost key | What the boost button does: **LED on/off**, **Aura RGB** or **DFS channels** (the last only with a DFS region) (`turbo_mode`). Models with a boost key. | Model default |
| Power Save Mode | **Performance**, **Auto** or **Power Save** (`pwrsave_mode`). Models that offer it. | Model default |
| Maximum page cache ratio | Share of memory the kernel may use as file cache, 5 to 90 % (`pagecache_ratio`). Models that offer it. | 90 |
| Enable PLC sleep automatically | Powerline models only (`plc_sleep_enabled`). | Off |
| USB Mode | USB 2.0 or USB 3.0 (`usb_usb3`). Changing it asks first and reboots the router. | USB 3.0 |
| Enable HDD Hibernation | Spins idle USB disks down (`usb_idle_enable`). | Off |
| Spin down idle USB disks after | Idle seconds before spin-down, 60 to 9999 (`usb_idle_timeout`). | 300 |
| Keep spinning | Disks (`sda` to `sdi`) excluded from spin-down (`usb_idle_exclude`). | None |

**Limits and gotchas**

- A USB mode change takes effect only through the reboot it triggers.
- A disk that holds the long-term store (4.11) or Entware wakes often; spinning it down saves little. Exclude it.

#### 4.27.6 System > Maintenance

**What it is.** The reboot schedule, WAN network monitoring (dual-WAN models), custom scripts and the WAN-down notice.

**How to use it: schedule a reboot**

1. Open **Administration > System**, tab **Maintenance**, panel **Reboot schedule**.
2. Switch **Enable Reboot Scheduler** on.
3. Where the firmware offers it, choose **Weekly** or **Monthly**. Weekly: tick the **Day(s) to Reboot**. Monthly:
   pick the **Day of month** (1 to 31).
4. Enter the **Time to Reboot** as hour (0 to 23) and minute (0 to 59). Press **Apply**.

The router reboots at that time by its own clock (4.27.4). A weekly schedule needs at least one day ticked.

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Enable Reboot Scheduler | Reboots on the schedule below (`reboot_schedule_enable`). | Off |
| Day(s) of week / Day of month | Weekly or monthly (`reboot_schedule_type`). The choice is offered only where the firmware reports monthly support; switching type clears the other schedule. | Weekly |
| Day(s) to Reboot | Weekdays for a weekly schedule (`reboot_schedule`, seven 0/1 flags from Sunday, then HHMM). | Sunday |
| Day of month | Day for a monthly schedule (`reboot_schedule_month`, DD then HHMM). | 1 |
| Time to Reboot | Hour and minute. | 03:00 |
| DNS Query / Resolve Hostname | Network monitoring: the WAN is judged by a DNS lookup of this name (`dns_probe`, `dns_probe_host`). Dual-WAN models in router mode; the same switches as WAN > WAN Ports (4.19). | Name `dns.msftncsi.com` |
| Ping / Ping Target | Network monitoring by ping to a host name or IPv4 address (`wandog_enable`, `wandog_target`). Same keys as 4.19. | Off |
| Enable JFFS custom scripts and configs | Runs `/jffs/scripts` and honours `/jffs/configs` (`jffs2_scripts`). `/jffs` itself is always mounted (2.4, 2.9). | Off |
| Enable WAN down browser redirect notice | While the WAN is down, web requests from the LAN are answered with a notice page instead of timing out (`nat_redirect_enable`). Router mode. | On |

**Limits and gotchas**

- A scheduled reboot ends whatever is running at that time (a USB copy, a VPN session). Pick a quiet hour; RAM-only
  history is lost at each reboot (2.6).
- With the WAN-down notice on, the router replaces its NAT rules with redirect rules while the WAN is down and puts
  them back when it returns. Turn it off if a WAN outage should leave LAN traffic untouched.
- A custom script that does not run: see *When a script seems not to run* in 2.9.

#### 4.27.7 System > Accessibility

**What it is.** One switch, **Colour-blind mode**, which swaps the interface's red, green, teal and amber for colours
that stay distinct with colour-blind vision. Only colours change: no page, control, word or behaviour changes, and the
Reaper logo pictures (the header and the animated sign-in logo) keep their own colours.

**How to use it**

1. Open **Administration > System**, tab **Accessibility**, panel **Colour vision**.
2. Switch **Colour-blind mode** on and press **Apply**. The whole window reloads in the new colours.

Under the switch, **Preview** shows the same few controls twice - a button, a switch, three status labels and a small
download / upload chart - in the standard colours on the left and in colour-blind mode on the right, whichever mode is
on.

**What changes**

| Today | Used for | Colour-blind mode |
|---|---|---|
| Red, the accent | The selected menu item, buttons, active tabs, headings, client bars | Blue `#3B82F6` |
| Green | Connected, secure, OK, active; a switch that is on | Cyan `#38BDF8` |
| Green / teal on charts | The download line and the rate figures | Light sky blue `#7DD3FC` |
| Amber | Warnings, a gauge in its middle range, the BETA badge, latency | Gold `#FACC15` |
| Red that means a problem | A field that fails its check, a link or node that is down, a denied slot, dropped traffic, errors; the upload and loss lines | Orange `#FB923C` |
| Dark red boxes | The tinted boxes behind icons and highlighted rows | Slate blue `#1E293B` |

The charts with several series (Traffic Analyzer classes and networks, QoS diagnostics queues) take a set of colours
chosen to stay apart for every kind of colour-blind vision.

| Setting | What it does | Default |
|---|---|---|
| Colour-blind mode | The colour-blind palette on every page (`reaper_cbmode`). | Off |

**Limits and gotchas**

- The choice is saved on the router, not in the browser: it applies on every device and browser that signs in, the
  sign-in page included, and travels with the settings backup.
- States already differ by more than colour where it matters (a switch is filled when on and hollow when off; status
  labels carry a word); the new colours add separation, they do not replace the words.
- The stock setup wizard that Operation Mode still runs for Repeater and AiMesh Node follows the switch as far as Reaper restyles it.

#### 4.27.8 Backup & Restore

**What it is.** Reaper's page for both backups and the factory reset. It replaced the stock Restore/Save/Upload
Setting page in v2.9.8. What each file holds, sealing, and what a restore does are in **2.5**; the factory reset and
the `/jffs` checkbox are in **8.4**. This section lists the page's controls.

**The controls**

| Control | What it does |
|---|---|
| Header chips | Model, Reaper version, and `/jffs ON` or `OFF` (amber when off). |
| Steps 01 / 02 / 03 | **Save**, **Restore**, **Complete**. Step 03 lights up while a restore waits for its second half. |
| **Complete restore** ribbon | Appears after the reboot of a restore that has a second half (an archive from before v3.0.6, or a settings file on the same model). One click finishes it (2.5). The same ribbon appears on the dashboard. |
| **Download full backup** | Asks for the admin password and an optional backup passphrase (twice); downloads the `.rbk` (`.rbk.enc` when sealed). |
| **Restore full backup...** | Picks a `.rbk` or `.rbk.enc` (up to 128 MB); asks for the passphrase of a sealed file; checks model, `/jffs` health and the archive, then restores and reboots. |
| **Export settings** | Asks for the admin password and an optional passphrase; downloads `reaper-settings-<model>-<version>-<date>.json` (`.json.enc` when sealed). |
| **Import settings** | Picks a `.json` or `.json.enc` (up to 12 MB). Same model: settings restore and reboot. Other model: only the Reaper half, no reboot; the page reports *Imported: N setting(s), M list(s), K rejected*. |
| Factory default: **Restore to factory default settings while clearing all content and data logs** | Ticked by default: the reset also erases `/jffs`. Unticked: only nvram is cleared (8.4). |
| Factory default: **Restore** | Asks for confirmation, then resets and reboots. |

**How to use it**

1. Before a reflash or a reset: **Download full backup**, give a passphrase, and keep the file off the router.
2. To move your Reaper configuration to a different model: **Export settings** on the old router, **Import
   settings** on the new one, then open Firewall and Policy Routing and press **Apply** and **Keep** (2.7).
3. To reset: decide whether `/jffs` should survive (8.4), set the checkbox, **Restore**. Reconnect to the open
   factory network `ASUS_xx` or a wired port and open the address the page shows.

**Limits and gotchas**

- Five wrong admin passwords lock exports for a minute. A lost passphrase cannot be recovered.
- If the router has not gone down within 3 minutes of a reset request, the page says the reset was not accepted and
  releases itself; nothing was changed.
- The page's **?** opens 2.5 of this guide.

#### 4.27.9 SNMP

**What it is.** Reaper's page for the router's SNMP agent (net-snmp, from Asuswrt-Merlin). Only **SNMPv3** is
served: v1 and v2c send the community string in clear text and are not configured at all, whatever the old
`roCommunity` / `rwCommunity` values say (since v1.7.8). The tab shows on models built with SNMP.

**How to use it**

1. Open **Administration > SNMP** and switch **Enable SNMP** on.
2. Optionally fill **System name**, **System location** and **System contact** (reported as `sysName`,
   `sysLocation`, `sysContact`).
3. Under **SNMPv3 user**, the **User name** is the router login name (4.27.2). Keep **Authentication** at **SHA** and
   **Privacy** at **AES**, and enter the two passwords (8 to 64 printable characters, no spaces).
4. Leave **Allow access from WAN** off unless a monitoring server outside your network must poll the router.
5. Press **Apply**. The pill reads **Agent on**.
6. Poll from the LAN, for example:
   `snmpwalk -v3 -l authPriv -u admin -a SHA -A '<auth password>' -x AES -X '<privacy password>' 192.168.50.1 system`

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Enable SNMP | Starts the agent (`snmpd_enable`). It listens on UDP 161 of the main LAN address only, and of the LAN's global IPv6 address when the router holds one. | Off |
| Allow access from WAN | Opens UDP 161 on the WAN interface only and makes the agent answer on the WAN address (`snmpd_wan`). The agent listens on the WAN address only while that address is up, and starts again when the WAN comes up or changes address; it never listens on every interface. Over the WAN nothing can be changed by SNMP (read-only), and SNMPv3 with your passwords is still required. Before the image after v3.8.0 the switch opened the firewall but the agent answered on the LAN address only, so a server outside got no answer over IPv4. Router mode only. | Off |
| System name / location / contact | Free text the agent reports (`sysName`, `sysLocation`, `sysContact`). | Empty |
| User name | The router login name. Read only. | `admin` |
| Authentication | **SHA** or **MD5** (`v3_auth_type`). | SHA |
| Authentication password | `v3_auth_passwd`. Never sent back to the page: a stored password shows as `********`; an empty field keeps it. | Empty |
| Privacy (encryption) | **AES**, **DES** or **None** (`v3_priv_type`). None = authenticated but unencrypted. | AES |
| Privacy password | `v3_priv_passwd`, same rules. Hidden with Privacy None. | Empty |
| Show passwords | Unmasks the two fields while you type. | - |

**Limits and gotchas**

- The agent is not created without the passwords it needs; the page refuses to enable SNMP without them.
- Changing the router login renames the SNMPv3 user; update the monitoring server.
- **What SNMP SET can change (from the image after v3.8.0).** The user reads the whole tree and can SET three objects only: `sysContact`, `sysName` and `sysLocation`. Everything else answers *noAccess* to a SET: interface state, the agent's own user and access tables, the tunnel tables. Stock gave the user write access to every writable object (`rwuser`), which included a module loader that loads a library by path as root; that module is no longer in the build. With **WAN access** on, nothing is writable. For a wider SET, add your own `view` / `access` lines to `/jffs/configs/snmpd.conf.add`.
- A guest or IoT network does not reach the agent: it answers on the main LAN address only.

#### 4.27.10 Tweaks: the other settings

**Administration > Tweaks** (`Reaper_Tweaks.asp`) has four panels. 4.17 describes the first, **Warden** (the feed
update schedule). The other three:

**Connection tracking.** How many connections the router tracks and how long an idle one is kept. The defaults suit
almost every network; Apply restarts connection tracking.

| Setting | What it does | Default |
|---|---|---|
| Connection limit | Maximum tracked connections, 256 to 300000 (`ct_max`). The default is also the maximum, so it can only be lowered. If the log reports the table as full, look for a device that opens very many connections, or shorten the idle timeouts. | 300000 |
| TCP: established | Seconds before an idle established connection is dropped, 1 to 432000 (`ct_tcp_timeout`). | 2400 |
| TCP: SYN sent / SYN received / FIN wait / TIME wait / close / CLOSE wait / last ACK | Timeouts of connections that are opening or closing, 1 to 86400 s each (`ct_tcp_timeout`). | 120 / 60 / 120 / 120 / 10 / 60 / 30 |
| UDP: assured / UDP: unreplied | A UDP flow is assured once replies have been seen (`ct_udp_timeout`). | 180 / 30 |

**Advanced tweaks.**

| Setting | What it does | Default |
|---|---|---|
| Redirect the login page to the router domain name | Opening the router by its IP address switches the browser to `www.asusrouter.com`, or to the address in **Redirect to** below (`http_dut_redir`). | Off |
| Redirect to | Shown while the switch above is on: your own address for the router - protocol (`https` / `http`), name and port (`reaper_dut_redir_proto`, `reaper_dut_redir_host`, `reaper_dut_redir_port`). An empty name keeps `www.asusrouter.com`; an empty port uses the router's own port for that protocol (8443 for https, 80 for http, unless changed). The name: letters, digits and `-` in parts joined by dots, no `-` at either end of a part, up to 57 characters, not an IP address; the port 1 to 65535. The name must lead to this router for the devices on your network (your DNS, or a DNS rewrite in Wallguard, 4.3.3.14) and, with https, needs a certificate for that name (Let's Encrypt or an uploaded certificate under WAN › DDNS, the one the web interface uses - 4.3.4.3, or your own). The login page moves only when the address answers, so a wrong one changes nothing. The address is sent to the login page only while the redirect is switched on. The web interface's cross-site check follows the same switch: the name counts as the router's own only while the redirect is on. Saved only, nothing restarts. | https / empty / empty |
| Drop IPv6 neighbour solicitation floods on the WAN | Drops multicast neighbour solicitations arriving on the WAN, for providers that flood them (`ipv6_ns_drop`). Restarts the firewall. | Off |
| Answer WPAD requests with an empty entry | The DHCP server answers the WPAD option with an empty value, so Windows stops searching for a proxy file (`dhcpd_send_wpad`). Restarts DNS and DHCP. | On |
| mDNS across networks | Devices on the main network and on every network with **Main Network** ticked in Access Intranet find each other (casting, printers, AirPlay); avahi relays mDNS between those networks (`reaper_mdns_reflect`). Networks with **AP Isolation**, networks without intranet access and Guest Portals are left out, and the router does not answer mDNS on the last two. Routing modes. | On |
| Only chosen kinds of devices | Under mDNS across networks: relay only the ticked kinds of device and the service types you enter (such as `_ipp._tcp`, at most 16 in total) between the main network and the Access Intranet networks (`reaper_mdns_types`, 4.21.8). The router's own services and the guest networks' Device discovery are not affected. Restarts mDNS. Routing modes, shown while mDNS across networks is on. | Off (every kind) |

**Wireless stability** (see also 8.2). For a router that freezes or drops every device at once. Switch on one at a
time and give each a few days.

| Setting | What it does | Default |
|---|---|---|
| Radio call timeout | How long the router waits for a radio to answer one call, 2000 to 5000 ms (`reaper_dhd_ioto`); recommended 3000. The driver's own wait is 5000 ms. Too short can make the driver give up on a radio. Applied at once, no Wi-Fi restart. | Off |
| Keep devices that a node claims | The router no longer disconnects a device because an AiMesh node reported it joined the node (`disable_exap`); a device that really moved leaves by inactivity. | Off |
| ASUS background DFS rule | The router stops checking radar channels in the background (`reaper_bgdfs_stock`); a later move to a DFS channel then waits for the full check (about 1 minute, 10 on weather-radar channels). Wi-Fi restarts. | Off |

**Not on the page any more: Portal secret.** The Guest Portal sign-in secret has no control here. Each router makes
a random secret of its own the first time a portal starts, and keeps it.

#### 4.27.11 System Information

**What it is.** A read-only Reaper page (its own menu, **System Info**) that replaced the stock `Tools_Sysinfo.asp`
in v3.1.8. It reads the same router data as the stock page, grouped by question. Nothing on it changes a setting.
Uptime sits in the header.

| Card | What it shows |
|---|---|
| This router | Model, serial number, LAN MAC address, firmware, build, bootloader, wireless driver version per radio, operation mode, uptime. |
| Processor | CPU, cores, clock, load average over 1, 5 and 15 minutes against the core count, per-core usage bars, CPU and per-radio temperatures. |
| Memory | Used, buffers, cache and free as one bar; total, **Available** and swap. *Available* is the figure that matters: buffers and cache are handed back on demand, so a low *Free* on a busy router is normal. |
| Storage | NVRAM used of its fixed size, and JFFS used. A full NVRAM is what stops settings saving (2.4). |
| Network capacity | Active connections against the router's connection-tracking maximum, with the headroom left (the limit is set on Tweaks, 4.27.10); hardware acceleration state; per radio the wireless clients associated, authorised and authenticated. An off radio reads *off*. |
| Add-on board | Model, hardware, firmware and address of an add-on board; shown only on a router that reports one. |
| Capabilities | The features this image was built with, by name. They decide which pages and options exist, which is why a setting another model has can be absent here. |

The figures refresh every 2.5 to 5 seconds while the page is open. Band labels come from each radio's band, so a
quad-band model is labelled correctly.

#### 4.27.12 The security banner

`Reaper_SecBanner.asp` is not a page and has no menu entry. It is the text of the first-boot banner (2.3), fetched by
every signed-in admin page while the login or the Wi-Fi is still at its factory value; it is never served before
login. Opening its address shows nothing useful, and since v3.7.1 the login no longer lands on it.

---

### 4.28 USB Application

The **USB Application** menu exists on models with USB. Its tabs: **USB Application** (the overview), **Media
Server**, **Network Place (Samba) Share**, **NFS Exports** (only where built), **FTP Share** and **USB Disks** (4.12).
The overview, Media Server, Samba and FTP are Reaper pages since v3.7.1; they write the stock settings through the
stock handlers, and the stock pages they replace no longer ship (their old addresses open the new pages). The
Printer Server and Time Machine pages are Reaper pages as well (4.31). Formatting, the health scan and safe removal are on **USB
Disks** (4.12); filesystems are in 2.6.

The services are off at factory (8.3). The USB application network installer is gone (1.2).

#### 4.28.1 The USB Application page

One card per USB service with its state (**Enabled** / **Disabled**): Network Place (Samba) Share, FTP Share, Media
Server (on when DLNA or iTunes is on), Network Printer Server, Time Machine, 3G/4G (router mode on models with modem
support; it opens WAN > Internet Connection) and USB Disks. A card opens its page. Below, every partition with its
free and total space and a **read-only** tag where it is mounted read-only; the file services share these partitions.

#### 4.28.2 Accounts and folder rights (Samba and FTP)

**What it is.** Samba and FTP share one set of accounts and one folder tree; each page shows the same panels and sets
that protocol's rights.

- **Accounts.** The first account is the router login (tagged *router login*); it cannot be renamed or deleted here,
  and follows the router login (4.27.2). **Add account**, **Modify account** and **Delete account** manage the others.
  A name starts with a letter and holds letters, digits and `-`, not `root`, `guest` or `anonymous`; a password is
  1 to 32 printable ASCII characters. The number of accounts is capped by **Maximum number of concurrent connections**
  (stock behaviour).
- **Folders and access rights.** For the selected account, one row per partition and per top-level folder on it, with
  one radio per right. Samba: **Read/write**, **Read**, **No**. FTP: **Read/write**, **Write**, **Read**, **No**.
  Changes collect as pending (**Unsaved changes: N**) and are written by **Save**; **Discard** drops them. Each
  changed folder is saved on its own and Samba and FTP restart each time, so transfers in progress are interrupted.
  With guest or anonymous access on, the rights grid is greyed out.
- **Folders.** **Add folder** on a partition row creates a top-level folder; **Rename** and **Delete** act on a folder
  row. A name holds letters, digits, spaces, `-` and `_`; one over 12 characters asks first (some Windows versions do
  not show it). **Delete removes the folder and every file in it**; type `DELETE` to confirm. A read-only partition
  offers no folder actions.

#### 4.28.3 Network Place (Samba) Share

**What it is.** The SMB file server (Samba 4, from Asuswrt-Merlin) sharing the USB disks with Windows, macOS and
Linux. Shares are named after their folder (4.12). A refused SMB login is written to the system log with the user,
the client's address and the reason; successful logins are not logged.

**How to use it: share a USB folder over SMB with a password**

1. Plug the disk in; check it on **USB Disks** (4.12).
2. Open **USB Application > Network Place (Samba) Share**. Switch **Enable Share** on; leave **Allow guest login** off.
3. Keep **Samba protocol version** at **SMB2 + SMB3**, or choose **SMB3 only (encrypted)** if every client is recent.
4. Press **Apply** and confirm. Samba starts.
5. Under **Accounts**, **Add account**: name `family`, a password twice, **Add**.
6. Select `family`; under **Folders and access rights**, **Add folder** on the partition, name `Photos`, then set
   `Photos` to **Read/write** and the other folders to **No**. Press **Save**.
7. Connect: `\\192.168.50.1\Photos` on Windows, `smb://192.168.50.1/Photos` on macOS, with the account's name and
   password.

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Enable Share | Starts Samba (`enable_samba`). Saved with Apply after a confirmation. | Off |
| Allow guest login | Anyone on the LAN reaches every share without a password (`st_samba_mode` share mode). Asks first. Not offered in Korean-territory units. | Off (accounts) |
| Device Name | NetBIOS name (`computer_name`), up to 15 letters, digits and `-`, stored in upper case. Empty = the router's LAN host name. | Empty |
| Work Group | Windows workgroup (`st_samba_workgroup`), up to 15 characters, upper case. | `WORKGROUP` |
| Samba protocol version | **SMB2 only**, **SMB2 + SMB3**, **SMB3 only (encrypted)** (`smbd_protocol` 1 / 2 / 3). | SMB2 + SMB3 |
| Maximum number of concurrent connections | 1 to 99 (`st_max_user`). Shared with FTP; also the account cap. | 5 |
| Simpler share names | Shares named after the folder without the disk name (`smbd_simpler_naming`). | On |
| Force as master browser | Samba claims the network browse master role (`smbd_master`). | Model default |
| Set as WINS server | Samba acts as a WINS server (`smbd_wins`). | Off |

Apply restarts Samba, FTP and DNS.

**Limits and gotchas**

- Guest login opens every share to every LAN device, and the firmware maps share guests to the admin account (4.11).
  Do not use it on a disk that holds the long-term store.
- **SMB3 only** refuses every client that cannot speak SMB3 (Windows 7 and many older players and NAS boxes).
- Samba's Spotlight search is off (v3.7.2).

#### 4.28.4 FTP Share

**What it is.** The FTP server (vsftpd, from Asuswrt-Merlin). The page warns that FTP sends passwords and files
unencrypted unless TLS is on, and links to SSH, where SFTP is encrypted (4.27.3).

**How to use it: FTP with TLS**

1. Open **USB Application > FTP Share**. Switch **Enable FTP** on; leave **Enable WAN access** and **Allow anonymous
   login** off.
2. Keep **Enable TLS support** on (factory value).
3. Press **Apply** and confirm.
4. Give an account **Read/write** or **Read** on the folders it needs (4.28.2) and **Save**.
5. Connect with a client set to **explicit FTP over TLS** on port 21 (FileZilla: *Require explicit FTP over TLS*),
   host `192.168.50.1`. The server presents the web interface certificate (4.27.2); accept it or trust the exported
   root certificate.

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Enable FTP | Starts the FTP server on TCP 21 (`enable_ftp`). Asks first. | Off |
| Enable WAN access | Opens TCP 21 and the passive ports `ftp_pasvport` to +30 (57530 to 57560) on the WAN, IPv4 and IPv6 (`ftp_wanac`). Asks first. Router mode. | Off |
| Allow anonymous login | Anyone may log in without a password, with upload rights (`st_ftp_mode` share mode). Asks first. Cannot be saved together with TLS. Not offered in Korean-territory units. | Off (accounts) |
| Enable TLS support | FTPS with the web interface certificate (`ftp_tls`). Shown on models with FTP TLS. With it on, logins and transfers must use TLS. | On |
| Maximum number of concurrent connections | 1 to 99 (`st_max_user`). Shared with Samba. | 5 |
| Character set on FTP Server | **UTF-8**, **Big5**, **GBK**, **Russian**, **Czech** (`ftp_lang`), for clients that send file names in a legacy code page. | UTF-8 |

**Limits and gotchas**

- Plain FTP clients cannot log in while TLS is on. Turning TLS off shows *TLS disabled is insecure*.
- A port forward that sends WAN port 21 to another LAN host conflicts with the router's FTP server; the page says so.
  Give that forward another external port.
- With WAN access on, the port is open to every address Warden (4.3.1) does not block, and the internet can try
  passwords. Prefer SFTP over SSH from the LAN, or a VPN.

#### 4.28.5 Media Server

**What it is.** Two media servers from Asuswrt-Merlin: **DLNA** (minidlna) for TVs, consoles and media players, and
**iTunes** (DAAP, mt-daapd) for music clients. DLNA serves the main LAN only.

**How to use it: serve media to a TV**

1. Open **USB Application > Media Server**. In **DLNA**, switch **Enable UPnP Media Server** on.
2. Set **Media Server Name** (a valid host name; empty or invalid = the router's name).
3. **Media Server Path Setting**: **All Disks Shared**, or **Manual Media Server Path** to list folders: pick the
   partition and folder, tick **Audio**, **Images** and/or **Video**, **Add**. Repeat up to 10 folders.
4. Press **Apply**. **Media Server Status** reads **Scanning...** while the library is built, then **Idle**.
5. On the TV, open its media or DLNA source and choose the server by its name.

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Enable iTunes Server | Starts the DAAP server (`daapd_enable`). It serves the whole disk area (`dms_dir`), not the DLNA folder list. | Off |
| iTunes Server Name | `daapd_friendly_name`; empty or invalid = the router's name. | Empty |
| Enable UPnP Media Server | Starts DLNA (`dms_enable`) on the main LAN. | Off |
| Media Server Name | `dms_friendly_name`; the page flags a name the router would replace. | Empty |
| Media Server Status | **Scanning...** or **Idle**, polled every 5 s while DLNA is on. | - |
| Rebuild the whole database at start | Full rescan at each start (`dms_rebuild`). Use once after moving many files. | Off |
| Enable the status web page | minidlna's status page on port 8200 (`dms_web`). | Off |
| Media Server Path Setting | **All Disks Shared** or **Manual Media Server Path** (`dms_dir_manual`). | All Disks Shared |
| Folder list | Up to 10 rows of folder and content types (`dms_dir_x`, `dms_dir_type_x`); the stored paths may total 128 characters. **New folder** creates a folder; the picker never deletes. | Empty |

Apply restarts both media servers. New files are picked up while the server runs, without a rebuild.

**Limits and gotchas**

- Devices on guest or IoT networks do not see the DLNA server.
- A folder list over 128 characters is refused rather than cut (stock lost it).
- The library database is kept on the largest writable USB volume (`.minidlna`), else in RAM.

#### 4.28.6 NFS Exports

`Advanced_AiDisk_NFS.asp` is the stock Asuswrt-Merlin NFS page (enable, NFS v2 legacy support, up to 64 exports of
path, access list and options). The tab shows only on a model built with the NFS server. The RT-BE96U, RT-BE86U,
RT-BE88U, GT-BE98 and GT-BE98 Pro are built without it, so the tab does not appear there.

#### 4.28.7 A USB volume for the long-term store

Long-Term Storage (4.11) can keep its history on a USB volume: choose **USB storage** there. The data is written
under `/.reaper/` on the volume, the volume is pinned by its own id, and Wallguard can keep its block lists there.
Anyone with Samba or FTP access to that volume can read the history, which maps every device with timestamps (2.6),
so keep that volume off guest login and anonymous FTP, or keep the store on JFFS. Filesystem choice and USB timing:
2.6.

---

### 4.29 Network Tools

**Network Tools** holds Reaper's diagnostic pages: **Network Analysis**, **Netstat** and **Wake on LAN** (all Reaper
pages since v3.4.9, replacing `Main_Analysis_Content.asp`, `Main_Netstat_Content.asp` and `Main_WOL_Content.asp`),
plus **Smart Connect Rule** (4.25.8) and **WiFi Site Survey** (4.18).

The three share one runner on the router: the page sends a tool and a target, the router checks the target (host
name, IPv4, IPv6 or MAC address), builds the command from fixed options and runs it without a shell. One test runs at
a time across the three pages (*Another network test is running*), each has a hard time limit, output is capped at
256 KB, and every run is logged (`reaper_net: <tool> <target>`).

#### 4.29.1 Network Analysis

**What it is.** Ping, continuous ping with a latency graph, traceroute and name lookup, run **from the router**.

**How to use it: ping and traceroute a host**

1. Open **Network Tools > Network Analysis**. **Tool**: **Ping**. **Target**: `www.example.com` (a list offers
   well-known DNS servers). **IP version**: IPv4. **Count**: 5. Press **Run** (or Enter).
2. The output fills below; the **Latency** panel shows replies, loss, min, avg, max and jitter.
3. For the path: **Tool**: **Traceroute**, same target, **Maximum hops** 30, tick **Do not resolve names** for a
   faster run. **Run**.
4. **Stop** ends a run early. A run started earlier (another tab, a reload) is shown when the page opens.

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Tool | **Ping**, **Continuous ping (graph)**, **Traceroute**, **Name lookup (nslookup)**. | Ping |
| Target | Host name, IPv4 or IPv6 address. | Empty |
| IP version | IPv4 or IPv6 (ping and traceroute). | IPv4 |
| Count | Ping: 1 to 100 packets. Continuous ping: 1 to 240 seconds, one ping a second. | 5 / 120 |
| Maximum hops | Traceroute, 1 to 30; each probe waits 3 s. | 30 |
| Do not resolve names | Traceroute prints addresses only. | Off |

The time limits: ping count + 10 s, traceroute 10 s per hop + 10 s, name lookup 30 s; a run cut at its limit says
*Stopped at the time limit*. Jitter is the mean difference between consecutive replies; the graph marks each lost
reply with a tick on the axis.

**Examples**

- A Wi-Fi complaint at night: continuous ping, 240 s, to the provider's gateway, then to `198.51.100.1`. Loss on both
  points upstream; loss only on the second, past the provider.
- Name lookup of `www.example.com` shows what the router's own resolver answers, with the router's DNS settings in
  effect (DNS page, 4.21).

**Limits and gotchas**

- The tests run from the router, not from a LAN device: Policy Routing rules for devices do not apply, and Warden's
  self-filter (4.3.1) applies only when it is on.
- Name lookup always asks the router's own resolver; there is no server field.

#### 4.29.2 Netstat

**What it is.** The sockets open **on the router itself** (its own services and connections). Connections passing
through the router are on **Connections** (4.9); the page links there.

**How to use it.** The page runs once when it opens with the defaults. Choose **Display listening server sockets** or
**Display all sockets**, tick the protocols and columns, **Run**. Type in the search box to filter the rows; click a
column heading to sort. UNIX sockets and other lines are shown as text below the table.

| Setting | What it does | Default |
|---|---|---|
| Display listening server sockets / Display all sockets | Listening sockets only, or every socket. | Listening |
| TCP / UDP / RAW / UNIX | Socket types to list. | TCP, UDP |
| Program | Adds the process name and PID. | On |
| Numeric addresses | Addresses and ports as numbers. | On |

**Example.** To check that SSH listens only on the expected port after a change: listening sockets, TCP, search `22`.

#### 4.29.3 Wake on LAN

**What it is.** Sends a Wake on LAN magic packet to a computer on the network it is on (from the image after v3.8.0; before, on the main LAN only), and keeps a short list of devices to
wake.

**How to use it: wake a PC**

1. Enable Wake on LAN in the PC's firmware (BIOS/UEFI) and network adapter settings. Use a wired connection.
2. Open **Network Tools > Wake on LAN**. In **Device**, pick the PC (offline devices are listed first), or type its
   MAC address, for example `00:00:5E:00:53:10`. Press **Wake**.
3. The page confirms *Magic packet sent to 00:00:5E:00:53:10*. The PC starts if it can receive the packet.
4. To keep it: under **Saved devices**, **Add a device** (picking the device fills the name and MAC), **Add**, then
   **Apply**. Each saved row has its own **Wake** button.

| Setting | What it does | Default |
|---|---|---|
| Device | The Devices page list (4.8); picking one fills the MAC fields. | - |
| MAC address / **Wake** | Sends the packet as a broadcast on the device's own network: the router looks the MAC up in its address table, then in each network's DHCP leases, and sends on that network's bridge. The page says which network it used. A device the router has never seen on any network gets the packet on the main network, with a note. | - |
| Saved devices | Name (up to 32 characters, no `<` or `>`) and MAC per entry (`wollist`). The list must stay under 1000 bytes; the page shows the count. **Apply** saves, **Discard** reverts. | Empty |

**Entry names.** A saved entry shows the **Devices page Name** for the same MAC (4.8.1), and its own stored name only
when the device has none. Renaming the device on the Devices page changes what this list shows; the stored name is
not rewritten.

**Limits and gotchas**

- A device on a guest, IoT or VLAN network is woken on its own network (from the image after v3.8.0). The router must
  have seen the device there: it is found by its address-table entry or its DHCP lease. If neither exists (for
  example a device with a fixed address that has been off since the router restarted), the packet goes to the main
  network and the page says so; start the device once so the router sees it, then it can be woken. The packet is
  never sent on every network: that would show a device's address to networks it never joined.
- A Wi-Fi device usually cannot be woken: its radio is off while it sleeps.
- The list lives in nvram; keep it short.

#### 4.29.4 Smart Connect Rule and Site Survey

**Smart Connect Rule** (band-steering rules) is in 4.25.8; **WiFi Site Survey** is in 4.18.

---

### 4.30 Parental Controls: Time Scheduling

**What it is.** Per-device internet schedules. Reaper's page (`Reaper_Parental.asp`, since v3.4.9) over the stock
enforcement: the firewall drops a listed device's traffic towards the internet in the times you set, by the router's
clock. A device is matched by its **MAC address**. Devices on the LAN stay reachable; only routed traffic is cut.
The stock *Web & Apps Filters* and *Web History* tabs need the Trend Micro engine Reaper does not ship (1.2), so the
menu shows this tab only. It needs a routing mode; in other modes the page says so and Apply is off.

**The DNS-level alternative.** Wallguard's per-profile **Blocked services** and their schedule (4.3.3.6) block named
services (social media, games, video) at set times while the rest of the internet keeps working. Time Scheduling
takes the device off the internet entirely. The two combine.

**How to use it: block a child's device on school nights**

1. Find the device's MAC on the **Devices** page (4.8). If the phone uses a private (random) Wi-Fi address, that
   address is the one to list; it changes if the phone forgets the network.
2. Open **Parental Controls > Time Scheduling**. In **Device MAC address**, pick the device from the list or type
   `00:00:5E:00:53:21`. **State**: **On schedule**. **Add**. (Adding a device switches **Enable Time Scheduling** on.)
3. The schedule editor opens with stock's two starter windows, both off: Mon-Fri 21:00 to 07:00 and Sat-Sun 22:00 to
   08:00. Keep **Mode** at **Block the Internet during these times**.
4. Edit the first window: days **Sun, Mon, Tue, Wed, Thu**, **from** `21:00` **to** `07:00` (it runs past midnight
   into the next day), and switch it on. Leave the second off or delete it.
5. Check the week preview, press **Done**, then **Apply**. Devices that are now blocked lose their open connections.

**The settings**

| Setting | What it does | Default |
|---|---|---|
| Enable Time Scheduling | Enforces the device list (`MULTIFILTER_ALL`). Off keeps the list but enforces none of it. | Off |
| Block all devices | Every device on every network of the router loses internet access, whatever the list says (`MULTIFILTER_BLOCK_ALL`); independent of the switch above. The router's pages stay reachable. Asks first. | Off |
| State (per device) | **On schedule** (apply the times), **Blocked** (cut off at all times), **Off** (listed, unrestricted) (`MULTIFILTER_ENABLE` 1 / 2 / 0). A row whose MAC the router cannot use reads **Not usable** and can only be deleted. | On schedule |
| Device | The name shown (see below); the MAC is stored in `MULTIFILTER_MAC`, the entry's own name in `MULTIFILTER_DEVICENAME` (31 characters). | - |
| Schedule | Summary: *Internet blocked in N time window(s)*, *Internet only in N time window(s)*, *Blocked at all times* or *No times set: not restricted*. **Edit** opens the editor. | - |
| Mode (editor) | **Block the Internet during these times**, or **Allow the Internet only during these times** (all other times blocked). | Block |
| Time windows (editor) | Each: on/off, days, **from**, **to** (`MULTIFILTER_MACFILTER_DAYTIME_V2`). An end before the start runs past midnight; 00:00 to 00:00 is the whole day; start equal to end otherwise is refused. **Add a time window** adds one. | Two starter windows, off |

The header shows the router's time and how many listed devices are active. A banner warns while the clock has not
been set from a time server (4.27.4).

**Entry names.** A row shows the **Devices page Name** for the same MAC (4.8.1); else the entry's own stored name;
else the device's hostname; else the MAC. The stored name is never rewritten. A stored name that begins with `@` is
the stock firmware's marker for a permission group (a group of devices from the stock account system); the page keeps
such an entry as it is and never creates one (a leading `@` typed into a name is removed).

**Examples**

- Homework hours only: Mode **Allow the Internet only during these times**, one window Mon-Fri 16:00 to 18:00, one
  Sat-Sun 09:00 to 20:00, both on.
- Grounded for a day: set the device's State to **Blocked**, **Apply**; back to **On schedule** the next day.
- Bedtime for every device on a guest network: **Block all devices** is all-or-nothing for the whole router; use
  per-device rows instead.

**Limits and gotchas**

- Up to 16 devices (or the model's own limit), 64 windows per device and 128 windows in all; the MAC and state lists
  must also fit nvram's 1 KB limit. The page shows the budget and refuses a change that does not fit.
- **Allow only** with no window switched on is refused: the router would leave that device unrestricted.
- A device that changes its private MAC, or joins over a VPN, is not matched. Gatekeeper (4.2) and Wallguard profiles
  (4.3.3.5) are the tools for unknown devices.
- Schedule entries the editor does not model are kept unchanged and counted under the editor.
- If the stored lists are out of step (an older edit), the page says so; the next change rewrites all of them.

---

### 4.31 Other menus

#### 4.31.1 AiMesh

**AiMesh** (`Reaper_AiMesh.asp`) is the AiMesh page on a Reaper page, with the stock page's functions and rules. The
**Topology** tab draws the mesh as a tree: each node sits under the member it connects to, with its uplink type and
connection quality in words (the coloured bar repeats it), and its count of connected devices. **Add AiMesh Node**
finds nodes in range and pairs one; **Optimization** asks the wireless nodes to look for a better uplink. Selecting
a member shows its location (28 presets or a custom text), connection quality and signal, and firmware version, and
three views. **Clients** lists the devices connected through it; a wireless device can be reconnected, bound to a
node or unbound, and a click on a connected device opens **Devices** (4.8). **Network** shows the WAN status (the
router) or the uplink (a node), the port states, the backhaul link and one card per radio, with traffic figures when
the connection diagnostics are on. **Management**, for a node, holds the settings the node reports it supports: LED,
backhaul connection priority, preferred Wi-Fi uplink AP, link aggregation, the radios, reconnect, reboot and remove.
The **System Settings** tab holds Ethernet-only backhaul, the system LED switch with its schedule (the stock
scheduler), the roaming block list (4.25), and system reset and reboot. The menu shows on a router that can be an
AiMesh router in its current mode. AiMesh's sync and discovery services are closed vendor binaries (1.1). Related: adding a new Reaper node (2.2), node firmware updates (4.14), backhaul parking (4.10.13), the
roaming block list (4.25) and **Keep devices that a node claims** (4.27.10).

From the image after v3.8.2 a device connected with MLO shows the MLO icon on the AiMesh tab, and *MLO* as its band
in the client list, whenever Reaper's own device scan knows it is MLO: on the main router and in Access Point mode,
for devices on the router and on a node (the stock list the page reads left out devices that join with a private
address per band). The mark only adds MLO, never removes it, and follows the MLO switch (4.25.7). In a node's MLO
backhaul details each band's signal row is named 2.4 GHz, 5 GHz (5 GHz-1 / 5 GHz-2) or 6 GHz, as in the rest of the
interface.

#### 4.31.2 Traffic Manager > Internet Speed

**Internet Speed** (`Reaper_Speed.asp`) is the Ookla speed test on a Reaper page, shown on models built with it
(all current models): **Go**, the result tiles (download, upload, ping, jitter), the server menu (**Auto** or a
server nearby), the interface menu when a VPN client is up, the speed **Level** and the **History** of the last 50
results. A test you start sends traffic to Ookla's servers; nothing runs on its own. All models use ASUS's
102_40585 setup: 100 free tests, then 3 per 24 hours once setup is complete, and the page says when the quota is used
up (v3.6.3). A run never freezes the browser or gives up early, and a failed run says why; while QoS is on the page says what
rate QoS caps the result at. Several runs at a quiet hour give the upload figure QoS needs
(4.5.2).

#### 4.31.3 Network Printer Server

`Reaper_Printer.asp`, opened from its card on the USB Application page (4.28.1); it has no tab of its own. It switches
the USB printer server on or off (`usb_printer`, off at factory; saved with **Apply**, which restarts the LPR and USB
printer services) and names the two ways to print: ASUS's EZ printer sharing utility and LPR. Shown on models with
printer support. The stock page's address opens this page.

#### 4.31.4 Time Machine

`Reaper_TimeMachine.asp` sets up macOS Time Machine backups over AFP (netatalk); it is opened from its card on the USB
Application page and has no tab of its own. Settings: **Enable Time Machine** (`timemachine_enable`, off at factory),
the **Backup Path** (a menu of the mounted partitions with their free and total space; one with 1 GB free or less
cannot be chosen) and a **volume size** limit in GB (`tm_vol_size`; 0 = no limit, at most the partition's free space;
choosing another partition clears it). The stock page's address opens this page. The AFP server has Reaper's CVE fixes and
offers the DHX2 login only (v3.7.2). The backup folder is root's own on the volume.

---

## 5. Efficiency and good practice

1. **Know the layer order.** Traffic meets **Warden → guest isolation → Gatekeeper → the rules engine**, in that order, on every base chain (the guest networks' chosen-device accept comes last, 2.9). Use Warden for "never talk to these ranges or countries", Gatekeeper for "which devices are allowed at all", the Firewall rules for the specific policy between them, and Egress defaults for the short "this device gets no internet". Do not re-express a Warden block as a firewall rule, or a Gatekeeper block as a Policy Routing Block; one layer, one job.
2. **Keep lists small and named for what they are.** A country object points at Warden's set rather than copying it; a domain list should hold one service, split if it is long; an address object is `printer`, not `192-168-50-20`. Warden's feeds merge and de-duplicate, so FireHOL Level 1 alone covers three of the four built-ins.
3. **Mind the WireGuard bypass cost.** A Policy Routing rule that sends a *device (by MAC)* or a *destination list* to a WireGuard client bypasses hardware acceleration for the **whole LAN** for as long as the rule exists. If you can express the rule as a **source IP/CIDR**, only that address loses acceleration. If you can use an OpenVPN client as the target, nothing loses acceleration.
4. **VPN Director or Policy Routing?** Use VPN Director for the broad posture — "everything (or this subnet) through the tunnel". Use Policy Routing for what needs an object or a device, or one of its three properties: a Block target, MAC keying, and precedence over VPN Director. Whether traffic blocks or falls back to the WAN when a tunnel drops is that VPN client's Killswitch, for both features. If you need none of those, VPN Director alone is fine and simpler.
5. **Set the QoS bandwidth honestly.** 90–95 % of the *lowest measured* upload. Too high and the ISP's buffer takes over and nothing here can help; too low just wastes headroom. Put your priority classes in order of latency-sensitivity, not importance, and never give the top class a 100 % ceiling.
6. **USB choice.** An ext4 stick that stays in the router is the right home for traffic history, the syslog mirror and incident dumps. FAT32 is for disks you carry about. Keep the file share closed to untrusted users if the store is on it.
7. **Apply, test, then Keep.** On the Firewall and Policy Routing pages, make the change from a device the rule does not touch, confirm what you meant to allow still works, then press Keep. If you are not sure, let the timer run; reverting is free.
8. **After every upgrade**, look at: the System Log for migration lines (`gatekeeper: device list migrated …`, `rule list migrated …`, `N list(s) migrated …`) and any `hwqos … REJECTED` or `FATAL` line; the Firewall **Status** tab (engine active? exposure as expected?); the Warden tile (countries amber?); the Gatekeeper state (Enabled, not Arming/Not enforcing); the About page's patch count; and — if you run QoS Classful — that you still have IPv4. Then take a fresh Reaper settings export.
9. **Read the diag FINDINGS first.** The report's top block is a list of one-line verdicts the script derives itself: an nvram value near the 1 KB cap, an un-migrated Gatekeeper list, a stuck `nvram`/`iptables` reader, a D-state process, a daemon enabled but not running, a missing cron line, an old direct firewall hook or a missing front chain, rules that failed to load, a conntrack table over 80 %, a WAN link stuck at 10/100 Mb/s, a Wi-Fi station with hundreds of disassociations, or a `/jffs` that is unmounted, read-only, nearly full or unwritable. Most field problems to date would have been named there; check it before reading the sections. The syslog-history part of the report (station churn, deauth errors, DHCP discover sources, boot and panic counts) is what separates "the router did it" from "one client is flapping".
10. **Leave logging off** on the Firewall Logging tab and Warden's drop log except while you are diagnosing something; a busy line can write thousands of lines a minute, which costs CPU and rolls the entries you need out of the firewall log's RAM ring (4.1.12).
11. **Leave the extras off** unless you use them: the Advisor's network-diagnostics tick-box, the router-self filter in Warden, the Traffic latency probe, and the accelerator health probe in `rwatch` (`rwatch_gdx=1`) are all opt-in for a reason.

---

## 6. Troubleshooting quick table

| Symptom | Where to look | Fix |
|---|---|---|
| Settings will not save; one CPU core busy; everything else works | System Log for `reaper-nv` lines; diag FINDINGS "stuck nvram reader" | The closed-library freeze (1.5), fixed in v3.1.8 by the vendor's corrected libraries. On an older image a reboot clears it. On v3.1.8 or later, report it with a diagnostics report. |
| A Firewall rule or Policy Routing rule "disappeared" | Firewall / Policy Routing page: did you press **Keep**? Log tag `reaper_fw` / `reaper_pbr`: `commit-confirm: reverted …` | It auto-reverted (2.7). Re-apply and press Keep within the timer; lengthen the timer if you need more time. |
| Firewall table shows a rule but Status says engine inactive | Firewall → Status; log `reaper_fw` | LAN was not up when the rules ran, or part of the ruleset failed; the log counts failures. Apply again after the LAN is up. |
| Gatekeeper shows **Not enforcing** | Gatekeeper page; log `gatekeeper` / `gkd` "enforcement chains missing" | Its rules keep dropping — usually a script or add-on flushing the chains (2.9). Remove the conflict; the daemon repairs within ~30 s. |
| Gatekeeper shows **Arming** for minutes after boot | Log `gatekeeper` | Normal for the several-minute boot-stabilisation window; it arms when the bridge is up. If it never leaves Arming, read the log. |
| 46th+ approved device stays Pending (old images) | Log `gatekeeper: device list migrated …`; diag §14b | Upgrade to v2.6.3 or later; the list moves to `/jffs` (2.4). |
| "Internet only" device has no working internet | Gatekeeper; DHCP's advertised DNS | If your DNS server is on the LAN, it must itself be an approved (full) device in Gatekeeper (4.2). |
| Unknown device on a guest network gets a hung page instead of "awaiting approval" | Log `gatekeeper`; `SDN_FI` admit rule | Fixed in v2.6.5; requires an isolated SDN to reproduce. |
| Whole LAN lost the internet right after a Warden feed update | Log `rwarden`, `rwatch` canary CRITICAL | Fixed since v1.8.8 (private ranges are stripped); `rwatch` re-applies rules and logs if your LAN IP ever matches a block set. Check custom feeds for private ranges; they are stripped too. A `CRITICAL: chain-disarmed:…` line is different: something else put an ACCEPT or RETURN into one of Warden's drop chains; the same repair runs. |
| Warden blocks total is large but the country table is near zero | Warden count bar (Countries / Threat feeds / Manual / Unclassified) | Not a fault: before v2.5.0 feeds were credited first. Now countries are evaluated first; expect a kink in history at that version. |
| Warden country tile is amber "N country list(s) empty" after a reboot | Warden; log `rwarden: cache restore for set …`; `ipset -t list rw_g_<cc>` | Press **Update feeds now**. v2.5.9 fixed the per-set cache replay. |
| Dreadwatch is on but shows no blocked lookups | Bastion › Dreadwatch: **Test now**, the Coverage card; log `rwarden: threat domains:` | Press **Test now**. *Blocked* means the list works and no device has looked up a listed name through this router — or they resolve elsewhere (Coverage), typically a device set to its own encrypted DNS provider: move the encryption to the router (4.3.2.8, *Encrypt at the router*). *Not blocked* means the list is not loaded yet: **Update feeds now**. *Counting is not active yet*: the next list update starts it (4.3.2.7). |
| Wallguard: safe search or YouTube Restricted Mode not applied | Bastion › Wallguard: the profile's **Edit** (a warning under *Safe search*), **Why?** | The device has another profile (Devices and networks), the enforcement addresses have not been looked up yet (warning; since v3.8.1 the system log names the engines and the router tries again when the internet comes up and on a back-off; **Update lists now** fetches them at once), or the browser uses its own encrypted DNS (4.3.4.6). |
| Wallguard: a blocked service still works on a schedule | The profile's schedule, the router's time (System Log › General) | Outside the schedule's ranges the service is allowed by design; check the days and that the range is not reversed. A wrong router time zone moves every range. |
| Wallguard: a site or app stopped working | Bastion › Wallguard › Overview: **Fix a device**, pick the device | Allow the name it was refused for 24 hours or always (4.3.3.7). Several names in a row usually belong to one service; allow them one at a time. A device that must never be filtered: give it the **Bypass** profile. |
| Wallguard: a rule change does not take effect after the USB stick was removed | Bastion › Wallguard: the line under *Lists*; the system log (`wallguard`) | The lists live on the USB volume (Long-Term Storage, *Wallguard block lists*) and it is not mounted: the table in use stays rather than lose those names. Reattach the volume, or **Update lists now** to download into RAM. |
| Wallguard is on but nothing is blocked | Bastion › Wallguard: the pill, *Lists*, **Why?** with a listed name | *Waiting for lists*: the first download has not finished — the WAN must be up; **Update lists now**. A list in state *failed*: its host cannot be reached. *Why?* says blocked but the device still shows ads: it resolves elsewhere (its own encrypted DNS, a VPN) or the ads share the content's host name (4.3.3.14). |
| Encrypted DNS: a device does not connect | Bastion › Encrypted DNS: the state banner, *Refused*, the Certificate and *Where it answers* cards | *Self-signed* on the Certificate card: only Android's *Automatic* setting works — add a Let's Encrypt or uploaded certificate (4.3.4.3). A device DNS Director sends elsewhere is refused on purpose. *Not running: waiting for the router's certificate*: the web interface has no certificate yet. An address marked *could not listen here*: another service holds port 853 there. |
| A phone or browser has no DNS after *Block encrypted DNS that goes around the router* was switched on | The device's Private DNS / secure-DNS setting | It is set to one named outside provider, which the block refuses on purpose. Set it to automatic (Android *Automatic*, the browser's default) or to the router's Encrypted DNS; or exempt the device with DNS Director *No redirection* (4.3.4.7). |
| *Block encrypted DNS*: the list shows only the built-in addresses | Encrypted DNS card: the list line; log `encdns:` | The first download runs once the router is online and then daily at 05:25; *failed* keeps the previous list. **Update list now**; check that raw.githubusercontent.com is reachable from the router. |
| Encrypted DNS: a phone has no internet away from home | The phone's Private DNS setting | It is set to *Private DNS provider hostname*, which applies on every network; the router (rightly) cannot be reached from outside. Use *Automatic* on phones (4.3.4.4). |
| Encrypted DNS: the hostname works at home on Wi-Fi but not behind a second router | Encrypted DNS: the WAN-address note | Double NAT: the name points at the outer router. Use Android's *Automatic* setting or the Apple profile, which connect to the LAN address (4.3.4.11). |
| Dreadwatch shows a *Not recorded* tile | Bastion › Dreadwatch | More than 50 blocked lookups a second, typically one device retrying a blocked name in a loop. Blocking is unaffected; the records beyond the limit are counted, not kept. The *Devices* card shows which device. |
| Wallguard: a newly ticked list stays *not downloaded yet* after **Save** | Bastion › Wallguard, the list's *State*; log `wallguard` | Save downloads a list that has no copy yet; if it still reads *not downloaded yet*, that download failed and the State says why. Check the internet connection, then **Update lists now** (4.3.3.2). |
| Wallguard: a list reads *blocked by Warden (…)* | Bastion › Wallguard, the list's *State* (hover for the address) | Warden's router-traffic filter drops the list's server. Whitelist that address on the Warden tab, or untick the list (4.3.1.8). |
| Wallguard shows a banner that devices' DNS lookups are sent straight to another address | Bastion › Wallguard; Firewall › Service Intercept; LAN › DNS › DNS Director; a VPN client in *Exclusive* DNS mode with VPN Director rules | A port-53 redirect sends lookups past the router's resolver, so Wallguard and Dreadwatch never see them. Remove the redirect, or point that server's upstream at the router (4.3). |
| A remote OpenVPN or IPsec user cannot connect while Warden blocks countries or uses feeds | Warden with **Log dropped packets** on; log `REAPER-WARDEN` | Only enabled WireGuard servers' listen ports are exempt. Whitelist the user's address, or connect through WireGuard (4.3.1.13). |
| Dreadwatch or Wallguard: a source of your own says it sends an API key but no key is saved | The source's **Modify** | Enter the key there; it is stored write-only and never shown again (4.3.2.4). |
| Dashboard shows an amber bar: *N unreviewed change(s) to scripts, cron entries or exposure settings* | Firewall › Status, the Security review card; log `rwatch: security review:` | The self-monitor found a difference from the baseline you accepted (4.1.1b). Read the list: your own change → **Accept**; a script, cron entry or forward you did not make → treat it as a compromise and check the diagnostics report. Nothing has been undone. |
| Security Review row is amber *Baseline* after a reboot; the review card says *no report yet* | Dashboard; Firewall › Status, the Security review card | Not a fault: the report lives in RAM, and the first check after a boot waits out the 5-minute boot grace and the next five-minute tick — up to 10 minutes. The row turns green (or red) on its own. |
| Log line `httpd: reaper: a request for the removed address <name> came from <address> (written once per boot)` | System Log | Something on your network asked for a request address that v3.8.4 or a later release removed (1.2): an add-on page, a script, the ASUS app. Harmless; it tells you what to update. The notice is temporary and goes away after the next stable version. |
| Security Review card shows an amber row *This baseline has no seal* after updating | Firewall › Status, the Security review card; log `rwatch: security review: the baseline on this router has no seal` | Expected once after updating to v3.8.4: older firmware did not seal the baseline. Check the list and press **Accept current state as baseline**. |
| Red row *The accepted baseline or the watch rules were changed outside this page*; dashboard bar is red | The same card; log `rwatch: security review: the accepted baseline or the watch rules were changed outside the Firewall page (fingerprint sealed ..., found now: ...)` | `/jffs/reaper/review/baseline` or `/jffs/reaper/review/rules` was changed without an Accept on the card (SSH, a script, a settings import with other rules, a restore of older router settings). Review the whole list; accept it if it is yours. |
| The Security Review is still on after a settings import or a script that posts settings; log `review: switching the security review off through a settings file REFUSED` (or `through the settings handler`) | System Log; Firewall › Status, the Security review card | Intended (v3.8.4): only the card's own switch turns the review off. The import reports that value as rejected; everything else in the file is applied. |
| `rwatch: security review: N failed ssh logins from <address>` and a notice on the review card | Firewall › Status, the Security review card; `/jffs/security_recored.log`; the dropbear lines in the system log | A password-guessing run. Over IPv4 the stock guard locks the source after its own threshold; over IPv6 from the internet the router now allows 5 new SSH connections a minute per /64 (2.9). If you do not need SSH from the internet, set SSH to LAN only on the Administration page — the notice is information, nothing has been undone. |
| `rwatch: FAILURE detected: front-chain-drift` about 8 minutes after every boot, with an incident dump each time | Log `rwatch` line `rule(s) ahead of the Reaper hook ...` (names the rule); `iptables -S FORWARD` | A `firewall-start` / `nat-start` script or an add-on inserts a broad `ACCEPT` at position 1 — typically a VPN helper's interface rule. Make it insert after `REAPER_HOOK` / `REAPER_HOOK_F` (2.9). Listing `ACCEPT` in `front_exempt` does nothing. |
| A phone on mobile data cannot reach the router's WireGuard server while Warden blocks countries or uses feeds | Firmware version; Warden page | Fixed in v3.6.5: Warden lets UDP through to the listen port of each enabled WireGuard server (packets to the router only) and re-applies when a server is switched on or off or its port changes. OpenVPN and IPsec servers are not exempted (4.3.1.13). |
| Router itself cannot reach feeds / DDNS / a VPN peer with Warden's self filter on | Log `REAPER-WARDEN-SELF`; `rwatch: FAILURE detected: warden-self-drop` | That is the feature reporting. The log names the destination; whitelist it or turn the self filter off. |
| Policy Routing dropdown is empty / a domain rule matches nothing | Log `reaper_pbr`; `ipset list rwfw_<list>` | Fixed in v2.5.9 (token and shared object layer). Check the list has resolved; lists fill from the router's own resolver, so a client on its own DNS or DoH does not feed them. |
| Some routing mark rules missing after a reboot | Log `rwatch: policy routing: N of M mark rule(s) live — re-applying` | Self-heals within two minutes (v2.6.9); no action needed unless the line repeats forever. |
| WireGuard rule shows "not supported yet — rule inactive" | Policy Routing page | You are on v2.6.1–v2.6.6; WireGuard targets arrived in v2.6.7. |
| LAN throughput dropped after adding a routing rule | Policy Routing page: the WireGuard note under the rules table; log on apply | A destination-list or MAC rule to WireGuard bypasses acceleration for the LAN (4.4). Use a source rule, or an OpenVPN target. |
| A source rule to a WireGuard client still goes out the WAN, while the same rule to OpenVPN works | Diag §14d (bypass *new/pre/pending*, `table wgcN` route count, last handshake, per-rule packets); log `reaper_pbr: … skip-bypass …` / `blog skip table full`; from the device, `traceroute` to a public address | The accelerator, not the rule, is carrying the flow (4.4.9). A *pending* bypass or a full table means the flow was never diverted; upgrade to v3.1.7 (the bypass is installed when the client starts and a changed target no longer keeps stale verdicts), free a slot if the table is full, and check the client's Allowed IPs cover the destination. |
| A device behind a source rule to a WireGuard client gets no replies at all | Policy Routing page; firmware version | Fixed in v3.2.4: replies were routed back into the tunnel (4.4.9). Upgrade. |
| An ASN list or a country list reads *not used by a rule*, *loads after Apply* or *no source answered* | Policy Routing: the list's **Loaded** and **Source** columns; System Log `reaper_fw: lists:` | A list is loaded only while an enabled rule uses it, after **Apply**. *no source answered* names what each source said; with Warden's **Also filter the router itself** on, a blocked country that covers a source stops the router's own download (4.4.4a). The list already loaded stays in use. Press **Update now** after fixing the cause. |
| An AS number is routed but some of that service's traffic still leaves by the other path | `ipset test rwfw_<list> <address>` for the address in question | The address is not announced under that AS number: content served from inside your ISP, or a customer network with its own number (4.4.4a). Add a domain list, or the other AS number. |
| An AiMesh node drops off after adding a broad firewall, Service Intercept or Policy Routing rule | Firmware version; Firewall → Rule Status | Fixed in v3.6.5: the rules engine, Service Intercept and Policy Routing skip a paired node's own traffic, as Gatekeeper does (4.1.3). A node that joins after the rules were applied is exempt within one watchdog tick (5 minutes). |
| A firewall rule blocks a network's own DNS or DHCP at the router | Firewall → Rule Status: the red row's rule column; Rules tab: the rule's direction; Objects: the subnet values | Usually an Inbound rule meant to separate two networks, or two subnet objects that overlap (4.1.3). Change the rule to Forwarded and narrow the object. |
| IPv4 stopped working entirely, IPv6 fine, QoS Classful on | Log `hwqos: setqcfg qid N … REJECTED` / `class queues restored …`; QoS Diagnostics queues 1–5 | v2.6.0 makes the rebuild transactional. A `FATAL` line means even the bare recreate failed — report it with a diag. |
| Games/consoles cannot open ports or connect with UPnP on | Log `IGD desc` lines (which description the console fetched); Firewall Status exposure card | IGD:1 is advertised by default (v2.4.6) and the upstream "all traffic through UPnP" patch is reverted (v2.5.8). If you enabled IPv6 pinholes, IGD:2 is served — that configuration broke the PS5. |
| UPnP mappings stop working hours after boot | UPnP page vs actual forwarding | Fixed v2.3.5 (the daemon is genuinely restarted on firewall rebuilds). Do not "optimise" that restart away. |
| PPPoE set to 1500 runs at 1492 | `grep -i "up with MTU" /tmp/syslog.log` | `MTU 1492 (requested >1492; peer declined RFC 4638)` means your provider declined; nothing to fix on the router. Both MTU and MRU must be above 1492 (they move together). Not the LAN Jumbo Frame setting. |
| No internet after a router reboot until the ONT is power-cycled (PPPoE) | Log `rwatch` bounce line | v2.5.5 re-dials once after the 300 s boot grace when all three probes fail (`reaper_wanbounce_enable`, on by default). |
| Firmware page frozen during a flash | — | Since v2.3.3 the poll chain is one-shot and the overlay has a Close on errors. If an old image: wait for the router, then End Task the tab. |
| Mesh node shows a blank page with a cycling URL after flashing Reaper | Node's own firmware page | Fixed v2.4.6 (theming stands aside on a node). A node already stuck must be updated from the main router's AiMesh flow. |
| "Search for node" finds nothing | Log `aimesh:` drop-reason lines | The two silent gates are now logged; recent reports say discovery works. A new Reaper node must be factory-reset on this firmware first. |
| USB format "did nothing", log says "w/o tool" | Log `disk_format`; `/tmp/disk_format/<dev>.log` | NTFS/HFS+ dispatch fixed in v2.6.8. Prefer ext4 for a disk that stays in the router. |
| Traffic history gone after a reboot or flash | Long-Term Storage page; USB mounted? | Choose JFFS or USB (RAM is volatile). Since v2.1.5/v2.1.9 the collector waits for the USB store and never overwrites a database it did not load; `rtraf.db.prev` is the at-risk copy. |
| Devices page lists a Wi-Fi device as Wired | Devices | Fixed v1.9.4 (bridge table) and v2.4.2 (mesh clients); a wireless-backhaul *node* is fixed v2.5.9. |
| Device names keep reverting | Devices; stock client list | Fixed v2.1.9 (three root causes). Existing duplicates self-heal on the first reboot. |
| Speed test dies partway through | Traffic Manager → Internet Speed | Counter fixes in v2.4.5/v2.5.4. A genuine outage still fails on the real timeout. |
| Reaper settings import reports rejections | Log `reaper_cfg: settings imported: N flag(s), M list(s), K rejected` | The rejected entries failed the same validation as typing them; fix them on the page. Firewall/routing lists still need Apply + Keep. |
| Diag report tripwire says "review before sharing" | The report's ledger | Something still looked like a public address, MAC or e-mail. Read the file and redact by hand before attaching it. |
| Login loop or credential page rejects everything after a factory reset | — | Fixed v2.1.5 / v2.2.0 / v2.3.5; the forced first-boot page and its gates were removed altogether in v2.9.1 (2.3). Power-cycle and log in with the new credentials. |
| A guest device cannot cast, print or AirPlay to a main-network device | Network page, the guest network's General settings; diag section 4d | Guest networks are isolated by design (4.21). Either tick **Device discovery with the main network** with the service types it needs and **Reach these main-network devices** for the target (it needs a DHCP reservation), or link the network with Access Intranet. A Guest Portal network never gets either. |
| An iPhone, iPad or Mac on a guest network does not switch to encrypted DNS by itself (DHCP option 162) | Bastion › Encrypted DNS, the **Automatic setup** line; the network's **DNS Server** and **Access Intranet** rows | Expected on an isolated guest network, a Guest Portal network and a network with its own DNS Server addresses (4.3.4.5, 4.21.6). To offer it, set the network's DNS Server back to Default and tick **Main Network** in Access Intranet, only for a network you trust: it then reaches your own devices. **Reach these main-network devices** and **Device discovery** do not bring it back. Android ignores the option on every network. |
| An iPhone with a DNS Director rule to another DNS server shows *No Internet Connection*, or leaves Wi-Fi for mobile data | System Log: `rednsd: refused ...`; Bastion › Encrypted DNS, the **Plain DNS only** list | Fixed in v3.8.4: the router no longer offers its encrypted DNS to a device it refuses (4.3.4.5). Switch the phone's Wi-Fi off and on once so it drops the old offer. On an older image: set the rule to *No filtering*, or switch Encrypted DNS for devices off. |
| A device on Wallguard's **Bypass** profile is still refused some names | Bastion › Dreadwatch, the blocked lookups of that device | Bypass lifts Wallguard only. The name is on a threat list: add the name to **Never block these names** (for every device), or the device to **Devices that skip Dreadwatch** (4.3.2.5a). |
| A TV or phone on Wi-Fi cannot find a NAS or printer on a LAN port after AP Isolation was switched on | Network page: the network's **AP Isolation** choice; diag section 4d bridge-port line | Choose **Wi-Fi only** (the default since v3.8.3): Wi-Fi devices stay apart, wired devices stay reachable. **Wi-Fi and LAN ports** keeps the LAN ports apart too. |
| Guest Portal: the phone never shows the sign-in page, or signed-in guests have no internet | Diag section 4d (portal networks, chilli, the portal listener, watchdog restarts, REAPER_GUN); log `watchdog` / `chilli` | chilli not running: save the network on the Network page (the watchdog restarts it at most three times a boot). REAPER_GUN written but not hooked: a firewall restart puts it back. |
| Header says **No internet** in red, or IPv6 is missing after an ISP outage | Header WAN pill tooltip; **WAN → WAN Ports**, Network Monitoring; diag section 5 | *No internet* means the router's own internet check fails on the line (v3.7.7) - check the targets on WAN Ports. IPv6 is asked for again once after an outage; if it stays missing, apply the IPv6 page once. |
| The login page says this address is refused | Wait 5 minutes, or sign in from another device | Five wrong passwords lock that address for 5 minutes (4.27.2). |
| `custom_script: /jffs/scripts/<name> exited with status N: …` | `/tmp/reaper/script-<name>.log`; diag section 13 | The script ran and a command in it failed (2.9). The log line quotes the last thing it printed. |
| Firewall page: the collector line shows *lost* or *held back* lines | Firewall → Logging; diag section 14 | *Held back*: a rule passed 10,000 lines a second; the packets were handled, only lines were skipped. *Lost*: the kernel dropped a batch under load. Log less (Drop instead of Both). |
| Wallguard or Encrypted DNS behaves differently than the page says | Diag section 14h (table, list states, last build, rednsd listeners, the block chain) | The FINDINGS name what is missing: a list that failed, a skipped build, a listener that could not bind, the block chain absent. |
| `logread` shows nothing | — | Expected on this platform. Use the System Log page or `/tmp/syslog.log`. |
| A DNS filter on a VLAN (AdGuard, Pi-hole) shows main-LAN devices as bare addresses | Administration → DNS Failover: **Device names across networks**; the filter's private reverse setting | Turn the switch on and point the filter's private reverse server at the VLAN's gateway, not the main router address (4.14b). Guest and Portal networks are never shared. |
| A reverse lookup between networks returns NXDOMAIN with the switch on | `grep rev-server /etc/dnsmasq*.conf`; WAN → Internet Connection | Check the network is not a Guest or Portal profile and has no captive portal; check **Forward local domain queries** is off; a device with a fixed address has no DHCP name to return (4.14b). |
| Puncturing set but the Settings cell says "Not applied" | Settings cell status; `/tmp/reaper/reaper_punct.state`; diag section 7 | *Refused*: the driver rejected that slice (it touches the primary 80, or the shape is not legal at this width) - choose another. *Different channel or width*: a Fixed pattern belongs to another channel; use Follow channel or re-pick. Needs Wi-Fi 7 on the band, the radio on, and 80 MHz or wider: a fixed width, or Auto bandwidth with Minimum width on Auto. |
| Dynamic puncturing never switches anything off | Wireless Quality › Dynamic puncturing card; log `rpunctd` | Usually correct: the channel is clean, the busy slice is short-lived, or the gain is below the minimum. At 320 MHz Passive telemetry can act only on the secondary 80 MHz; a busy far half logs "needs a confirmation scan" - choose a scan source if you want it resolved. |
| Dynamic puncturing is set but the card shows no radio | Diag section 7 "dynamic puncturing: daemon=" | The controller is not running; the rwatch tick restarts it within five minutes and says so in the log. If it stays down, report it with a diagnostics report. |
| Clients slower on a band after choosing Add hardware ACI mitigation | Settings cell; diag section 7 `interference:` line; client speed | Expected on some setups: the receiver limits its gain, which can cost rate and range (4.10.10). Set the row back to Driver default; the router restores the radio's own mode at once. |
| Interference mitigation set but the cell says refused or waiting | Settings cell; `/tmp/reaper/reaper_wlmit.state`; log `reaper_punct` | *Refused*: the driver did not accept the mode on that radio. *Waiting*: the radio was not up within 60 s; the rwatch tick retries within five minutes. |
| Dynamic puncturing with the Active source never scans | Wireless Quality card; log `rpunctd` "WAIT: own airtime ... above the scan ceiling" | By design: no confirmation scan while your own airtime is above 30 % (4.10.5). It scans when traffic eases. |
| Minimum width set but the Settings cell says Lifted or Not applied | Settings cell status; `/tmp/reaper_bwfloor/state`; log `reaper_bwfloor`; diag section 7 "min width:" | *Lifted*: the radio could not hold 80 MHz or wider (radar, or no wide channel free); the floor is off for 30 minutes and re-arms by itself. *Not applied*: no channel at 80 MHz or wider is left after the existing exclusions (DFS channels off?), so nothing was excluded. *Not active*: needs Auto channel and Auto bandwidth. |
| No internet on a new or factory-reset router; the WAN light is on | **WAN → WAN Ports**: which port is the internet port; the cable's port | From v3.4.2 the factory internet port is the one labelled WAN and automatic detection is off. With the cable in the other WAN-capable port, choose that port on WAN Ports, or move the cable (4.19). |
| Dashboard Internet status is amber though the WAN is up | Tooltip on the Internet card or the header's WAN pill; log `rdnshc` "LAN name resolution FAILING"; diag section 5 "LAN name check" | The LAN name resolution check found that LAN devices cannot resolve names (4.14a). The tooltip and the log name the silent servers: check the LAN filter (AdGuard, Pi-hole) or the upstream list. The check only reports; turn it off on DNS Failover if you do not want it. |
| A diagnostics report shows a `2001:`/`2a0x:` prefix, an `ip6.arpa` name, or a domain after "Ignoring domain" | The report's version line | Reports older than v1.3.35 printed routed IPv6 prefixes and reverse zones; older than v1.3.36, a device's own DHCP domain. Do not post such a report; on v3.4.2 those are masked (2.10). |
| An add-on (Skynet and others) installed but has no tab | `grep -n user /www/require/modules/menuTree.js`; the add-on's own log | From v3.2.8 the stock menu lines add-on installers anchor on are kept as hidden entries, so the tab lands in the Addons section. On an older image, or if the add-on's own startup never reached its web-page step, it has no tab. |

---

## 7. Glossary

- **AQM (PI2)** — active queue management in the hardware traffic manager; drops or marks packets early so queues stay short. Drops rising while a class is held to its rate is the system working.
- **Accelerator / Runner / flow cache** — the Broadcom hardware forwarding path. Reaper's hardware QoS engines keep it on; Cake and Traditional QoS turn it off; a WireGuard Policy Routing rule can bypass it for some or all LAN traffic.
- **Apply and Keep / commit-confirm** — the two-step change on the Firewall and Policy Routing pages: changes go live at once and revert on their own unless you press Keep within the auto-revert timer (2.7).
- **Auto-revert timer** — 15–3600 seconds, default 60, never off; set on the Firewall Rules tab.
- **Bastion** — the menu holding Warden, Dreadwatch, Wallguard and Encrypted DNS (4.3); since v3.6.0 none of the four needs another switched on.
- **Egress default** — a per-device rule for traffic leaving toward the internet only (Firewall → Egress).
- **Fail-closed** — an enabled VPN client whose **Killswitch** is on: traffic routed to it, by VPN Director or a Policy Routing rule, is *blocked* while the tunnel is down rather than let out the WAN. With the Killswitch off, or the client switched off, it falls back to the WAN (v3.1.5 matches VPN Director on the switched-off case).
- **Encrypted DNS** — the router's encrypted DNS server for the LAN's devices (`rednsd`: DNS-over-TLS on port 853, DNS-over-HTTPS on port 443), with an optional block on encrypted DNS that goes around the router (4.3.4).
- **FINDINGS** — the verdict block at the top of the diagnostics report.
- **Front chain (`REAPER_HOOK_*`)** — the single shared chain at the head of INPUT/FORWARD/OUTPUT into which Warden, Gatekeeper and the rules engine register, in that fixed order.
- **Gatekeeper** — device access control; states are Pending, Full access, Internet only, Guest (timed), Blocked.
- **Guest pass** — a timed (4/8/24/48 h) internet-only approval in Gatekeeper.
- **HW QoS Classful (type 11) / Hardware QoS (type 10)** — Reaper's two hardware QoS engines.
- **IGD:1 / IGD:2** — the two revisions of the UPnP gateway description. Reaper advertises IGD:1 by default; enabling IPv6 pinholes switches to IGD:2.
- **ipset** — kernel address sets; one lookup regardless of list size. Warden, the firewall objects and Policy Routing all use them.
- **/jffs** — the router's internal flash partition, always mounted; where Reaper's lists and Warden's cache live (2.4).
- **Long-term store** — the durable location (RAM / JFFS / USB) chosen on the Storage page for history datasets.
- **MCP / AI Advisor** — the optional read-only LAN-only Model Context Protocol server in the `_MCP` build; absent from `noMCP`.
- **MLO** — Wi-Fi 7 Multi-Link Operation; needs a cold power cycle to change (2.8).
- **Minimum width on Auto** — a per-radio switch that keeps the channel picker at 80 MHz or wider on Auto bandwidth ("80/160 MHz" on 5 GHz, "80/160/320 MHz" on 6 GHz), the widths preamble puncturing works at; lifts itself after radar (4.10).
- **Object / group / service / zone** — the named things Firewall rules refer to (4.1).
- **Policy Routing (PBR)** — rules that steer matched traffic to a VPN client, the WAN, or a block; they take precedence over VPN Director.
- **Pseudonym (`MAC-3`)** — a consistent stand-in for a real MAC inside one diagnostics report.
- **Preamble puncturing** — a Wi-Fi 7 radio excluding one slice of a wide channel from transmission and keeping the rest; Off, Fixed channel, Follow channel or Dynamic per radio (4.10).
- **rchqd** — the opt-in passive channel-quality monitor.
- **rdnshc** — the resolver health check and the LAN name resolution check (4.14a); its log tag too.
- **rdnsmapd** — the listener that learns the Connections page's destination names from DNS replies passing the router (4.9); controlled by the page's **Names** switch.
- **rv6names** — the daemon behind **IPv6 device names**: once a minute it names each LAN device's IPv6 addresses from its DHCPv4 name (4.14b).
- **WAN port pin (`reaper_wanport`)** — the port Auto detection last found the WAN on; Reaper keeps it out of the LAN bridge from then on (4.19). Unused while a fixed internet port is chosen, the factory state from v3.4.2.
- **rpunctd** — the dynamic puncturing controller; runs only while a radio is set to Dynamic.
- **Interference mitigation** — the radio receiver's own defences against nearby interference (`wl interference`, mode 75 by default); the Settings row can add hardware ACI mitigation (4.10.10).
- **Scan ceiling** — the own-airtime level above which dynamic puncturing never runs a confirmation scan: 10 % on the idle source, 30 % on Active (4.10.5).
- **Slice** — the frequency segment a puncturing pattern excludes from transmission: one 20, 40 or 80 MHz part of the channel, never the primary.
- **RFC 4638 / baby jumbo** — the PPPoE extension that allows a 1500-byte MTU by widening the WAN port to 1508; requires provider support and both MTU and MRU above 1492.
- **rtrafd** — the Traffic Analyzer collector.
- **rwatch** — the health watchdog (every 5 minutes): WAN first-hop ping, loopback DNS, the Warden self-lockout canary, Policy Routing self-heal, hung-nvram reaping, the optional accelerator probe, the PPPoE stale-session re-dial; writes incident dumps on first failure.
- **Security review** — the self-monitor's advisory drift check (2.9): `/jffs` scripts, configs and SSH keys, add-on files, cron entries and the exposure settings, compared against a baseline you accepted on the Firewall page's Status tab; amber dashboard bar and one log line per change set, nothing undone. Watch rules set what is hashed, checked for existence only or ignored; every acceptance is logged.
- **SDN / Guest Network Pro** — ASUS's per-network profiles (guest, IoT, VLAN). Gatekeeper enforces on every one; the Traffic Analyzer labels each by name and VLAN.
- **Warden** — the threat-feed, country and manual IP blocking layer.
- **Wallguard** — the router's ad and tracker blocker (4.3.3): block lists compiled into one table every resolver on the router shares, with per-device profiles, Unbreak and Why?.
- **Dreadwatch** — Warden's DNS counterpart (4.3.2): threat host names answered NXDOMAIN at the router's resolver, with per-feed, per-name and per-device counts of what it blocked.
- **Zone policy** — the default action between two zones; the weakest statement in the firewall engine, overridden by Egress defaults and explicit rules.

---

## 8. Factory defaults, and what Reaper changes

"Factory default" means the value a setting takes on a **factory reset**, or on a first boot with
clean NVRAM. Every setting below can be changed afterwards from the GUI. This section exists so you
can tell *what the firmware chose for you* from *what you chose*, and put anything back.

**Where the values come from.** The firmware's defaults table (`shared/defaults.c`), resolved for the
RT-BE96U build. A reset writes every entry in table order, so where the table lists a key twice the
later entry wins; the values here follow that rule. After the table, the model's own start-up code sets
a few hardware-specific keys (the interface lists, the factory network name `ASUS_xx…`, transmit power
calibration, the MLO capability), some of it in closed vendor code; those are described rather than
given a number. The sibling models share the table, so their values are the same unless a row says
otherwise.

**An upgrade never applies these values to a setting you already have.** On a normal boot the
firmware fills in only keys that are missing. A router upgraded from an older Reaper therefore keeps,
for example, Auto WAN detection or the DNS switches it had; to take the new defaults, change the
setting by hand or reset.

To read the live value of any key over SSH: `nvram get <key>`.

### 8.1 Stock settings whose default Reaper changes

Nineteen ASUS/Merlin defaults ship with a different value under Reaper. Each is a deliberate choice,
and each is reversible from the GUI.

| Setting | Stock | Reaper | Why |
|---|---|---|---|
| `wps_enable`, `wps_enable_x` | `1` | **`0`** | WPS is off out of the box. Its PIN method is broken by design and cannot be made safe. Turn it on in Wireless only if a device has no other pairing method. |
| `upnp_enable` | `1` | **`0`** | UPnP lets any LAN device open a hole in your firewall without asking. Enable it per WAN if you need console or game-server port mapping. |
| `upnp_min_port_ext` | `1` | **`1024`** | When UPnP is on, it may no longer map privileged ports. A compromised LAN device cannot claim port 22, 53 or 443. |
| `upnp_ssdp_interval` | `60` | **`900`** | SSDP announcements every 15 minutes instead of every minute. Far less multicast chatter, which is noticeable on Wi-Fi. |
| `autowan_enable` | `1` | **`0`** (v3.4.2) | The internet port is the one labelled WAN (`wan_ifname_x` = `eth0` on every model). Stock Auto detection can only find the WAN by bridging every candidate port into the LAN and asking for an address on the bridge, which puts the provider's network on your LAN for the length of the search (4.19). Auto stays a choice on WAN Ports. |
| `wl_crypto` | `tkip+aes` | **`aes`** | WPA encryption is AES only on every radio once a password is set. TKIP is deprecated and caps a client at legacy rates. The factory Wi-Fi is open until the setup box secures it (2.3). |
| `firmware_check_enable` | `1` | **`0`** | The stock automatic update check phones ASUS. Reaper checks its own GitHub release manifest instead, and only when you turn the check on (4.14, 9.1). |
| `ASUS_EULA`, `ASUS_NEW_EULA` | `0` | **`1`** | Pre-accepted, because the setup wizard that would have presented them was removed. Nothing is transmitted; this only stops the firmware blocking on a dialog that no longer exists. |
| `qos_default` | `3` | **`4`** | The catch-all class for unmatched traffic. Stock pointed at class 3, named "Downloads", so unclassified traffic — including game traffic, which is unmarked UDP — queued alongside bulk transfers. It now points at the class actually named "Default". |
| `qos_orates` | `80-100,10-100,…` | **`15-90,15-90,20-90,5-95,25-95,…`** | Per-class minimum and maximum rates. The stock profile committed effectively the whole link to class 1. Reaper's leaves headroom, keeps the committed total under 85% of your configured upload, and gives no top class a 100% ceiling (Web/VoIP was 100% until v3.8.0). |
| `qos_rulelist` | Web / HTTPS / File Transfer | **Conferencing, SIP, Game Console, Steam, BitTorrent, Web** | The starting classification rules. The stock set predates modern traffic and classified by transferred bytes, which accelerated flows never match (4.5.5). |
| `enable_samba`, `smbd_enable` | `1` | **`0`** | SMB file sharing is off until you turn it on (USB Application → Network Place). Stock started an SMB server on the LAN the moment a disk was plugged in. |
| `smbd_simpler_naming` | `0` | **`1`** | USB shares are named after the volume rather than a generated string. |
| `v3_auth_type` | *(empty)* | **`SHA`** | SNMPv3 authentication defaults to SHA rather than nothing chosen. |
| `v3_priv_type` | *(empty)* | **`AES`** | SNMPv3 privacy defaults to AES. Both matter only if you enable SNMP at all. |
| `ipv6_prefix_len_wan` | `64` | **`56`** (image after v3.8.2) | With Native IPv6 and prefix delegation this is the prefix size asked of the provider; a /56 gives every guest and VLAN network its own public /64 (4.24). The same key is the Static IPv6 WAN address length; the IPv6 page shows 64 when Static is picked on an untouched router. |

Earlier editions of this guide also listed `psc6g` (6 GHz preferred scanning channel) as changed from
`0` to `1`. On every model in the fleet the stock factory value was already `1`; the stock table's
second, conflicting entry applies only to two unrelated ASUS models.

Reaper also **adds 133** entries of its own (8.2) and **removes 18** that belong to features it strips
out: AiCloud and WebDAV (`enable_webdav`, `st_webdav_mode`, `webdav_proxy`, `webdav_aidisk`,
`webdav_http_port`, `webdav_https_port`, `acc_webdavproxy`, `enable_webdav_captcha`,
`enable_webdav_lock`, `webdav_acc_lock`, `webdav_lock_interval`, `webdav_lock_times`,
`webdav_last_login_info`), cloud sync (`enable_cloudsync`, `cloud_sync`) and the share-link plumbing
(`share_link_param`, `share_link_result`, `share_link_host`).

### 8.2 Reaper's own settings and their defaults

Grouped by the feature that owns them. **Every optional feature ships off**, and no Reaper feature
enforces anything until you turn it on. Four exceptions are on at factory, each because it only
watches, only names or only narrows a choice: the self-monitor (`rwatch_enable`), which acts only on
features you have enabled; its PPPoE re-dial (`reaper_wanbounce_enable`); the Connections page's
destination names (`rconn_names`), which keeps a name table in RAM and sends nothing; and AiMesh node
channel fit (`amas_chanfit`), which keeps the 5 and 6 GHz automatic channel on channels every paired
node can use and changes nothing while no node is paired. Keys marked *per radio* are written
for every radio as `wl0_…`, `wl1_…` and so on.

**Firewall engine** (4.1) — `reaper_fw_enable` `0`, `reaper_fw_active` `0`, `reaper_fw_armed` `0`,
`reaper_fw_confirm` `60`, `reaper_fw_st_auto` `0`, `reaper_fw_wt_auto` `0`, `reaper_fw_zpol_guest` `0` (zone policies may open one-way paths from the main network into isolated guest networks, 4.1.5). `reaper_fw_confirm` is the
auto-revert timer in seconds (15–3600): after you apply a ruleset, the firewall reverts unless you press
Keep in time (2.7). `reaper_fw_st_auto` and `reaper_fw_wt_auto` are the **Auto refresh** switches of the
Status and Rule Status tabs. The list keys
(`reaper_fw_rules`, `reaper_fw_obj`, `reaper_fw_grp`, `reaper_fw_svc`, `reaper_fw_zone`,
`reaper_fw_zpol`, `reaper_fw_nat`, `reaper_fw_edef`) and `reaper_fw_err` start empty; the confirmed
lists themselves live on `/jffs` (2.4).

**Warden** (4.3.1) — `rwarden_enable` `0`, `rwarden_dir` `in` (inbound only), `rwarden_self` `0` (the
router's own connections are not filtered), `rwarden_log` `0`, `rwarden_stats_save` `1` (block counts
are saved to flash), `rwarden_reset` `off` (the counters are never zeroed on a schedule; `24h`, `7d`,
`30d` and `90d` are the choices), `rwarden_dns` `0` (Dreadwatch, 4.3.2: off until you switch it
on) and `rwarden_dns_feeds` `urlhaus phish c2 threatfox` (all four lists selected once it is on). The list keys (`rwarden_feeds`, `rwarden_cfeeds`, `rwarden_geo`,
`rwarden_ban`) and `rwarden_sched` (feed schedule; empty = 04:30 daily) start empty, and the whitelist
(`rwarden_allow`) holds only the five list-host addresses the router adds once (4.3.1.7), so a freshly
enabled Warden blocks nothing until you choose feeds or countries. `rwarden_lastupd` is
the time of the last feed update, empty until the first.

**Gatekeeper** (4.2) — `gk_enable` `0`, `gk_default` `0`, `gk_captive` `1`, `gk_notify` `1`,
`gk_guest_hours` `24`, `gk_rl` empty (the device list lives on `/jffs`). `gk_default` `0` means a
device Gatekeeper has never seen is **held at the gate** (quarantined), not allowed; enabling it
approves every device already present first (4.2.2). `gk_captive` shows held devices the waiting-room
page, `gk_notify` notifies on a new device, and a Guest pass lasts 24 hours unless you pick another
length.

**Policy routing** (4.4) — `reaper_pbr_enable` `0`, `reaper_pbr_rulelist` empty, `reaper_pbr_armed`
`0`, `reaper_pbr_active` `0`, `reaper_pbr_err` empty.

**DNS Failover** (4.14a, 4.14b) — the resolver health check: `reaper_dnshc_enable` `0`,
`reaper_dnshc_target` and `reaper_dnshc_target6` empty (the server to watch), `reaper_dnshc_name`
`localhost` (the name queried), `reaper_dnshc_interval` `10` seconds, `reaper_dnshc_timeout` `1000`
milliseconds, `reaper_dnshc_fail` `3` misses before failing over, `reaper_dnshc_recover` `3` answers
before restoring, `reaper_dnshc_strict` `0` (any reply counts as alive). The DNSMASQ row, every switch
off from v3.4.2: `reaper_dns_strict` `0`, `reaper_dns_nocache` `0`, `reaper_dns_revshare` `0`
(was `1`), `reaper_dns_v6names` `0` (was `1`), `reaper_dot_strict` `0`, `reaper_landns_enable` `0`
(was `1` in v3.4.0), `reaper_landns_domain` empty (the router's network-monitoring name is used).

**QoS, classful engine** (4.5) — `qos_class_names` `Web/VoIP,Gaming,Streaming,Downloads,Default`,
`qos_pshaper` `1` (aggregate cap on), `qos_minrates` `1` (guaranteed minimums on), `qos_dscp_trust`
`0` (DSCP marks are not trusted), `qos_ipolicer` `0` (download policer off), `qos_cake_rtt` `50`
milliseconds (Cake's base round-trip time). `qos_sched` `p,p,w20,w5,w15` keeps stock's format; the
weights are not used, because every class runs strict priority on this hardware (4.5.9). QoS itself is
off at factory (8.3).

**Traffic Analyzer** (4.7) — `rtraf_enable` `0` (turn it on from the page's toggle), `rtraf_cap_gb`
`0` (no data cap), `rtraf_path` and `rtraf_probe` empty (no latency probe is sent).

**Connections** (4.9) — `rconn_names` `1`: the destination-name listener runs. The page's **Names**
switch turns it off and deletes its table.

**Channel quality** (4.10) — `rchq_enable` `0` (the passive channel monitor is off).

**Per radio** (4.10) — `wl_punct` empty (preamble puncturing off), `wl_bwfloor` `0` (no minimum width
on Auto), `wl_rmit` empty (interference mitigation: driver default). While every radio's keys are at
these values no `wl` command is issued and no watcher runs. `amas_bh_park` `0`: AiMesh backhaul
parking is off (4.10.13). `amas_chanfit` **`1`**: AiMesh node channel fit is on (Wireless › Settings,
one switch for the 5 and 6 GHz radios). With a node paired and the channel on Auto, the picker is kept
to channels every node's radio can use, and a radio left outside them is moved back after a minute;
with no node paired it does nothing.

**Wireless stability** (Administration › Tweaks) — three switches, all off. `reaper_dhd_ioto` `0`: the Wi-Fi
driver keeps its own 5000 ms wait for a radio call (on: 2000 to 5000 ms, 3000 recommended). `disable_exap`
empty: the roaming assistant disconnects a device an AiMesh node reports as its own (on: `1`, it does
not). `reaper_bgdfs_stock` `0`: background DFS scanning stays as shipped (on: `1`, each radio's
`acs_bgdfs_enab` and `acs_bgdfs_ahead` go to 0 and `acs_ignore_txfail` to 1; the earlier values come back
when the switch goes off).

**mDNS across networks** (Administration › Tweaks) — `reaper_mdns_reflect` `1`: devices on the main network and
on every network with Main Network ticked in Access Intranet can find each other (casting, printers, AirPlay); avahi relays mDNS between
those networks only. A network with **AP Isolation** on, a network without intranet access and a Guest
Portal are left out, and on the last two the router no longer answers mDNS at all. Off (`0`): each network sees only its own devices. `reaper_mdns_types` empty (v3.8.4): every kind of device is relayed. Set from **Only chosen kinds of devices** to presets (`print`, `airplay`, `cast`, `homekit`, `audio`) and service types, comma-separated, at most 16 types expanded: only those are relayed between the main network and the Access Intranet networks (4.21.8). Carried by the settings file. Per guest network (stored with the network's own Wi-Fi settings; their three template rows are in this count): `apgN_rg_devs` (the devices ticked in Reach these main-network devices) and `apgN_rg_mdns` (the Device discovery service types), both empty at factory and cleared when the network is deleted (4.21.2), and `apgN_ap_isolate_lan` `0` (the network's **AP Isolation** choice: `0` Wi-Fi only, `1` Wi-Fi and LAN ports; set to `0` for a new network and cleared when the network is deleted).

**Login page redirect address** (Administration › Tweaks, 4.27.10) — `reaper_dut_redir_proto` `https`,
`reaper_dut_redir_host` empty, `reaper_dut_redir_port` empty: with the redirect switch (`http_dut_redir`) on, the
login page moves to the stock router domain name, as before. A name typed here replaces it (with that protocol, and
that port or the router's own one). Kept in the settings file (Backup).

**AP Isolation choice of the main network** (Network menu, the main network's card, 4.21.2) — `reaper_ap_isolate_lan` `0`: while the main network's **AP Isolation** is on, it keeps Wi-Fi clients apart and the
wired devices stay reachable (Wi-Fi only). `1` (Wi-Fi and LAN ports): the router's LAN ports are kept apart too, from each other and from Wi-Fi; devices behind one external switch still reach each other and AiMesh backhaul
ports are never isolated. It covers every network on the main subnet.

**Hold Wi-Fi restarts until Apply** (Network menu, top of the page, 4.21.12) — `reaper_sdn_defer` `0`: each network
save restarts Wi-Fi at once, as stock. `1`: a create / edit / switch-on is saved at once and its Wi-Fi restart waits
for **Apply now** (or for the next change that runs at once); kept in the settings backup.

**Colour-blind mode** (Administration › System, tab Accessibility, 4.27.7) — `reaper_cbmode` `0`: the standard
colours. `1`: every page, the sign-in page included, uses the colour-blind palette; kept in the settings backup.

**Guest Portal secret** — the portal's sign-in secret is a random one the router makes for itself the first time a
portal starts and keeps (the stock value was the same on every router). The secret is never shown. The Tweaks control
for a secret of your own (`reaper_cp_secret_own`) was removed from the page on 2026-11-12.

**Long-term storage and export** (4.11) — `reaper_store` `ram`, `reaper_store_ds` `dev,traf,watch,fwlog`,
`reaper_store_vid` `` and `reaper_store_vname` `` (both empty until you pin a USB volume on the
Long-Term Storage page; the id is the volume's own `.reaper/store.id`, the name is its label).
On `ram`, history is lost at reboot; point it at JFFS or USB to keep it. The exporter is entirely off:
`reaper_export_mode` empty, `reaper_export_interval` `300` seconds, `reaper_export_tlsverify` `1`,
`reaper_export_maskmac` `0`, and `reaper_export_engine`, `reaper_export_url`, `reaper_export_token`,
`reaper_export_index`, `reaper_export_source`, `reaper_export_metrics` and
`reaper_export_scrape_token` empty.

**Encrypted DNS** (4.3.4) — `reaper_dot_srv` `0` (the DNS-over-TLS server for devices is off), `reaper_doh_srv` `0` (the DNS-over-HTTPS server for devices is off),
`reaper_doh_block` `0` (the block's DNS-over-HTTPS switch is off) and `reaper_dot_block` empty (the block's
port 853 switch). Empty means *follow `reaper_doh_block`*, so at the factory the port 853 switch is off as
well. It is left empty on purpose: a router upgraded from a version with one block switch keeps both halves
in the state that switch had (4.3.4.6).

**Let's Encrypt via DNS** (4.3.4.3) — `reaper_ledns_enable` `0` (off until you choose it as the
certificate under WAN › DDNS), `reaper_ledns_provider` `cf`, `reaper_ledns_domain` and
`reaper_ledns_token` empty. `reaper_ledns_state`, `reaper_ledns_err` and `reaper_ledns_when` start
empty: they are the last request's state, written by the router for the page.

**Self-monitor** (2.9, 4.13) — `rwatch_enable` **`1`**, `rwatch_iv` `5` minutes, `rwatch_review` `0` (the
security review, Firewall › Status: off until you switch it on; its watch rules file starts empty, so
the built-in defaults apply),
`reaper_wanbounce_enable` **`1`**. The WAN bounce fires only on a PPPoE link that has failed all
three reachability probes after the boot grace period.

`rwatch_review_seal` is not a setting and has no default: the router writes it when you accept a Security Review baseline (the fingerprint, the time and the address that accepted). A factory reset of the settings clears it; a baseline that survived in `/jffs` then shows the amber row once (4.1.1b).

**UPnP guard** — `upnp_protect_svc` `1`: when UPnP is on, it may not map a port the router itself
listens on for VPN or SSH, so a LAN device cannot steal the WireGuard or OpenVPN port.

**Firmware update** (2.11, 4.14) — `reaper_fwbeta` `0` (the update check ignores the beta channel),
`firmware_check_hour` empty (the scheduled check runs at a random minute overnight), and
`reaper_fwsig_override` `0` (a one-shot override for manifest signature checking; signing is built but
inert on current images, so the key has no effect, see `SECURITY.md`). `reaper_upg_fail` starts empty:
it records a refused firmware upload as `<time> <1|2>` (1 = not written, 2 = failed validation) for the
Firmware page, and the next successful upload clears it.

**MLO restart check** — `reaper_mlo_coldboot_owed` `0`: state, not a setting. Each boot the router sets it to `1` when
MLO is on and a restart without a power-off left the radios' MLO link down (the dashboard banner, 2.8), else `0`. Full
backup only.

**AI Advisor, MCP build only** (4.16) — `rmcp_port` `5199`, `rmcp_timeout` `60` minutes,
`rmcp_client` empty (no client pin). There is deliberately **no enable key**: the Advisor is armed by
a session file in `/tmp`, so every reboot comes up dark.

**Keys with no factory value.** These are absent after a reset, and absent means the behaviour shown:

| Key | Absent means |
|---|---|
| `reaper_wanport` | No WAN port pinned. Written only when Auto detection finds the WAN (4.19). |
| `rwatch_gdx` | The accelerator probe in `rwatch` is off (5, item 11). |
| `rmcp_code_hash`, `rmcp_code_salt` | No Advisor arming code is set (4.16). |
| `rmcp_usb_enable`, `rmcp_usb_hash` | No Advisor USB key is enrolled. |
| `rmcp_fails`, `rmcp_lock_until` | No wrong-code lockout is running. |
| `rtraf_hint`, `rtraf_hprobe` | Internal Traffic Analyzer markers, written by the collector. |
| `reaper_dnshc_state`, `reaper_landns_state`, `amas_bh_state` | Live state written by the daemons, not settings. |

### 8.3 Every feature and function at factory

What a factory-reset RT-BE96U looks like, area by area. "Off" means the feature does nothing until you
turn it on. The key column is what to read with `nvram get` when you want to check.

**Administration and access**

| Feature | At factory | Key |
|---|---|---|
| Router login | `admin` / `admin`; the setup banner stays until it and the Wi-Fi are changed (2.3) | `http_username`, `http_passwd` |
| Web interface on the LAN | HTTP and HTTPS, HTTP on port 80, HTTPS on 8443 | `http_enable` `2`, `http_lanport` `80`, `https_lanport` `8443` |
| Web interface from the WAN | Off (ports 8080 / 8443 when turned on) | `misc_http_x` `0` |
| Enable Access Restrictions (only the listed addresses reach the web interface and SSH) | Off | `http_client` `0` |
| Idle logout | 30 minutes | `http_autologout` `30` |
| SSH | Off; port 22 and password login when turned on | `sshd_enable` `0`, `sshd_port` `22`, `sshd_pass` `1` |
| Telnet | No Telnet server ships in the image | — |
| Custom scripts and configs on `/jffs` | Off (`/jffs` itself is always mounted, 2.4) | `jffs2_scripts` `0` |
| Time zone and DST | `GMT0`, no DST; both set from the browser at the first password change (2.3) | `time_zone`, `time_zone_dst`, `time_zone_dstoff` |
| Time servers | `pool.ntp.org`; the router's own NTP server for the LAN is off | `ntp_server0`, `ntpd_enable` `0` |
| Scheduled reboot | Off | `reboot_schedule_enable` `0` |
| LEDs | On | `AllLED` `1` |
| Remote syslog | Off (port 514 when set) | `log_ipaddr` empty, `log_port` `514` |
| System log levels | Log level 7, message level 5 (2.12) | `log_level`, `message_loglevel` |
| Firmware update check | Off; beta channel off (8.1, 8.2) | `firmware_check_enable` `0` |
| SNMP | Off; SNMPv3 with SHA and AES when turned on | `snmpd_enable` `0` |
| Operation mode | Wireless router | `sw_mode` `1` |
| Setup state | Not set up: the banner shows until login and Wi-Fi leave their factory values | `x_Setting` `0`, `w_Setting` `0` |

**LAN**

| Feature | At factory | Key |
|---|---|---|
| Router address | `192.168.50.1/24` | `lan_ipaddr`, `lan_netmask` |
| DHCP server | On, pool `192.168.50.2`–`192.168.50.254`, lease 24 hours, the router advertised as DNS | `dhcp_enable_x` `1`, `dhcp_start`, `dhcp_end`, `dhcp_lease` `86400`, `dhcpd_dns_router` `1` |
| Jumbo frames | Off | `jumbo_frame_enable` `0` |
| Spanning tree on the LAN bridge | On | `lan_stp` `1` |
| IGMP snooping | Off on the wired bridge, on for wireless | `emf_enable` `0`, `wl_igs` `1` |

**WAN and internet**

| Feature | At factory | Key |
|---|---|---|
| Connection type | Automatic IP (DHCP), NAT on, DNS from the provider, MTU 1500 | `wan_proto` `dhcp`, `wan_nat_x` `1`, `wan_dnsenable_x` `1`, `wan_mtu` `1500` |
| Internet port | The port labelled WAN; automatic port detection off (v3.4.2) | `wan_ifname_x` `eth0`, `autowan_enable` `0` |
| Dual WAN | Off (Fail Over with failback once turned on); network monitoring off | `wans_dualwan` `wan none`, `wans_mode` `fb`, `wandog_enable` `0` |
| IPTV / VLAN tagging | None | `switch_wantag` `none` |
| UPnP | Off; when on: secure mode, external ports 1024 and up, IPv6 pinholes off, announcements every 900 s, the router's VPN and SSH ports protected | `upnp_enable` `0`, `upnp_secure` `1`, `upnp_min_port_ext` `1024`, `upnp_pinhole_enable` `0`, `upnp_ssdp_interval` `900`, `upnp_protect_svc` `1` |
| Port forwarding, port triggering, DMZ | Off, off, none | `vts_enable_x` `0`, `autofw_enable_x` `0`, `dmz_ip` empty |
| NAT passthrough | PPTP, L2TP and IPsec on; FTP, RTSP, H.323, SIP and PPPoE relay off. A protocol helper (ALG) works only on its own ports while its switch is on; FTP and PPTP addressed to the router itself (its FTP server, a forwarded FTP port, its PPTP server) always get theirs | `fw_pt_pptp`, `fw_pt_l2tp`, `fw_pt_ipsec` `1`; `nf_ftp`, `fw_pt_rtsp`, `fw_pt_h323`, `fw_pt_sip`, `fw_pt_pppoerelay` `0` |
| Redirect browsers to a notice page while the WAN is down | On | `nat_redirect_enable` `1` |
| DDNS | Off | `ddns_enable_x` `0` |
| DNS rebind protection | Off | `dns_norebind` `0` |
| DNSSEC | Off (when on, unsigned replies are checked) | `dnssec_enable` `0`, `dnssec_check_unsigned_x` `1` |
| DNS Privacy (DNS-over-TLS) | Off | `dnspriv_enable` `0` |
| DNS Director | Off | `dnsfilter_enable_x` `0` |
| Forward local domain queries upstream | Off | `dns_fwd_local` `0` |
| DNS Failover page | Health check off, every DNSMASQ switch off (8.2) | `reaper_dnshc_enable`, `reaper_dns_*`, `reaper_dot_strict`, `reaper_landns_enable` |
| IPv6 | Disabled; when turned on: IPv6 firewall on, stateless autoconfiguration, router advertisements on, prefix delegation on | `ipv6_service` `disabled`, `ipv6_fw_enable` `1`, `ipv6_autoconf_type` `0`, `ipv6_radvd` `1`, `ipv6_dhcp_pd` `1` |

**Firewall**

| Feature | At factory | Key |
|---|---|---|
| Base firewall (SPI) | On | `fw_enable_x` `1` |
| DoS protection | Off | `fw_dos_x` `0` |
| Respond to ping from the WAN | Off | `misc_ping_x` `0` |
| Firewall logging | None | `fw_log_x` `none` |
| URL filter, keyword filter, network services filter | Off | `url_enable_x` `0`, `keyword_enable_x` `0`, `fw_lw_enable_x` `0` |
| Reaper rules engine, Warden, Gatekeeper, Policy Routing | Off (8.2) | `reaper_fw_enable`, `rwarden_enable`, `gk_enable`, `reaper_pbr_enable` |
| Dreadwatch (DNS threat blocking) | Off | `rwarden_dns` `0` |
| Wallguard (ad and tracker blocking, 4.3.3) | Off; blocked answer `0.0.0.0` | `wallguard_enable` `0`, `wallguard_mode` `null` |
| Encrypted DNS (DNS-over-TLS server for devices, 4.3.4) | Off | `reaper_dot_srv` `0` |
| Encrypted DNS (DNS-over-HTTPS server for devices, 4.3.4) | Off | `reaper_doh_srv` `0` |
| Block encrypted DNS that goes around the router (4.3.4.6), both switches | Off | `reaper_doh_block` `0`, `reaper_dot_block` empty (follows `reaper_doh_block`) |
| Security review | Off | `rwatch_review` `0` |
| Parental controls | Off | `MULTIFILTER_ALL` `0` |

**Wireless** (every radio unless a row says otherwise)

| Feature | At factory | Key |
|---|---|---|
| Network name | The model's factory name, `ASUS_xx…`, broadcast | `wl_ssid` (set per model at reset), `wl_closed` `0` |
| Security | **Open** until the setup box secures it (2.3); AES once a password is set | `wl_auth_mode_x` `open`, `wl_crypto` `aes`, `wl_wpa_psk` empty |
| Protected management frames | Off | `wl_mfp` `0` |
| Radios | On | `wl_radio` `1` |
| Wireless mode | Auto, Wi-Fi 6 and Wi-Fi 7 on | `wl_nmode_x` `0`, `wl_11ax` `1`, `wl_11be` `1` |
| Channel and bandwidth | Auto and Auto; auto channel may use DFS channels | `wl_chanspec` `0`, `wl_bw` `0`, `acs_dfs` `1`, `acs_band3` `0` |
| DTIM interval, beacon interval | 1, 100 ms | `wl_dtim` `1`, `wl_bcn` `100` |
| Transmit power | 100 % (calibrated per model at start-up) | `wl_txpower` `100` |
| WMM, frame bursting | On, on | `wl_wme` `on`, `wl_frameburst` `on` |
| MU-MIMO, OFDMA, beamforming | MU-MIMO on; OFDMA down- and uplink with MU-MIMO; explicit beamforming on, implicit off | `wl_mumimo` `1`, `wl_ofdma` `3`, `wl_txbf` `1`, `wl_itxbf` `0` |
| Roaming assistant | -70 dBm | `wl_user_rssi` `-70` |
| AP isolation, MAC filter, wireless scheduler | Off, off, off | `wl_ap_isolate` `0`, `wl_macmode` `disabled`, `wl_timesched` `0` |
| Smart Connect | Off; the setup box turns it on | `smart_connect_x` `0` |
| MLO | Off (2.8) | `mld_enable` `0` |
| WPS | Off | `wps_enable` `0` |
| 6 GHz preferred scanning channel | On | `psc6g` `1` |
| Preamble puncturing, minimum width on Auto, interference mitigation | Off, off, driver default (8.2) | `wl_punct`, `wl_bwfloor`, `wl_rmit` |
| AiMesh backhaul parking | Off | `amas_bh_park` `0` |
| AiMesh node channel fit | On; acts only with a node paired and the channel on Auto (8.2) | `amas_chanfit` `1` |
| Guest networks / VLAN profiles | None | — |

**USB and file sharing**

| Feature | At factory | Key |
|---|---|---|
| SMB file sharing (Network Place) | Off; SMB2 and SMB3 when turned on; shares named after the volume | `enable_samba` `0`, `smbd_enable` `0`, `smbd_protocol` `2`, `smbd_simpler_naming` `1` |
| FTP | Off; FTP over TLS on when turned on | `enable_ftp` `0`, `ftp_tls` `1` |
| Media server (DLNA), iTunes server | Off, off | `dms_enable` `0`, `daapd_enable` `0` |
| Time Machine | Off | `timemachine_enable` `0` |
| Long-term store | RAM (8.2) | `reaper_store` `ram` |

**VPN**

| Feature | At factory | Key |
|---|---|---|
| OpenVPN servers | Off | `VPNServer_enable` `0`, `vpn_serverx_start` empty |
| OpenVPN clients | None start at boot | `vpn_clientx_eas` empty |
| WireGuard server, clients | Off, none enabled | `wgs_enable` `0`, `wgc_enable` `0` |
| IPsec server | Off | `ipsec_server_enable` `0` |
| PPTP server | Off | `pptpd_enable` `0` |
| VPN Director, Policy Routing | No rules; Policy Routing off | `reaper_pbr_enable` `0` |

**Traffic Manager and monitoring**

| Feature | At factory | Key |
|---|---|---|
| QoS | Off; no bandwidth figures entered | `qos_enable` `0`, `qos_obw`, `qos_ibw` empty |
| QoS classes and rules when turned on | Reaper's five-class profile and starter rules (8.1, 8.2) | `qos_class_names`, `qos_orates`, `qos_rulelist` |
| Traffic Analyzer | Off | `rtraf_enable` `0` |
| Traffic latency probe (and the latency & loss chart) | Off; no target, nothing sent | `rtraf_probe` empty |
| Stock traffic statistics | Retired: the stock collector (`rstats`) no longer ships; the Traffic Analyzer keeps the traffic history | `rstats_enable` `1` (read by nothing) |
| Connections destination names | On | `rconn_names` `1` |
| Passive channel monitor | Off | `rchq_enable` `0` |
| Data export, health probe | Off | `reaper_export_mode` empty |
| Self-monitor and PPPoE re-dial | On, every 5 minutes | `rwatch_enable` `1`, `rwatch_iv` `5`, `reaper_wanbounce_enable` `1` |
| AI Advisor (MCP build) | Never armed; no arming code | `rmcp_port` `5199` |

### 8.4 What a factory reset actually restores

A factory reset clears NVRAM, so everything above returns to the value in the tables above. Whether
it also erases `/jffs`, where the firewall, Warden, Gatekeeper and policy-routing rule stores live,
depends on one checkbox in the factory-reset box on **Administration → Backup & Restore**:

- **Ticked** (*Restore to factory default settings while clearing all content and data logs*, the
  default): `/jffs` is erased at the reboot. This is the genuinely clean box, and your rules are
  gone; take a full backup first (2.5).
- **Unticked**: only NVRAM is cleared and `/jffs` survives. If you are resetting to clear a bad
  *setting*, this keeps your rules and you do not have to rebuild them.

Every reset comes up the same way on every model: `admin` / `admin` and the open factory Wi-Fi,
whatever key is printed on the unit's label (v3.3.1); secure it with the setup box (2.3).

**What the page shows (v3.1.0).** A reset started from Backup & Restore puts up a veil that says how to
get back: the router returns on its **open factory network** (`ASUS_xx…`) at its default address, with a
link to it — rejoin that network before the page can see the router again. The page treats the web
server's few busy seconds before the reboot as busy, not gone, so it no longer bounces to a sign-in page
that is about to vanish; if the router has not gone down within three minutes it says so and hands the
page back. On the router side three waits that did no work are gone (see the changelog), and the system
log carries a timestamp at each step (`factory reset: begin` … `nvram erased, handing off to init`).

---

## 9. Present but inactive

Every page in the menu is a Reaper page, and the stock ASUS interface is no longer in the firmware: there is no setting
that brings it back. A few stock files are still inside the image, each kept for one reason given below; **none is in
the menu**. This section lists them, so that finding one by typing its address does not look like a discovery. The
stock pages a Reaper page replaced no longer ship; their old addresses open the Reaper page.

### 9.1 The stock firmware-update page

`Advanced_FirmwareUpgrade_Content.asp` no longer ships; its address opens Reaper's own Firmware page (4.14), which
replaces it. It is listed here because Reaper's page reuses the stock update variables (`webs_state_update`,
`webs_state_info`, `webs_state_url`, `webs_state_flag`, `webs_state_error`, `webs_state_upgrade`, `webs_state_sha`)
rather than inventing parallel ones, so those keys are still present.

The automatic check it used to drive is off (`firmware_check_enable` `0`, see 8.1), because it queried ASUS. Reaper
checks its own GitHub release manifest instead, over HTTPS with certificate validation and a pinned host, and verifies
each image's SHA-256 and size before flashing (2.11).

### 9.2 AiProtection

The `AiProtection_*.asp` pages no longer ship; their addresses open Warden (4.3.1). The engine behind them is gone.
AiProtection is a TrendMicro product: the router ships traffic metadata to TrendMicro's cloud for classification,
which is precisely the arrangement Reaper exists to remove. The DPI engine that fed those pages is compiled out of the
build.

What replaces them, and what does not:

- **Malicious-site and threat blocking** - Warden (4.3.1), using public IP threat feeds and country blocks, and
  Dreadwatch (4.3.2), which answers known malware and botnet host names with NXDOMAIN at the router's resolver and
  counts what it blocked. Both work on addresses and names rather than on inspected content, and neither needs a cloud
  service.
- **Per-device access control** - Gatekeeper (4.2).
- **Content and keyword filtering** - the firewall's URL Filter and Keyword Filter tabs (4.1).
- **Deep packet inspection, and signature-based intrusion prevention** - **nothing replaces this.** It cannot be done
  locally at line rate on this hardware without a commercial signature feed. If that specific capability is what you
  need, Reaper is not the firmware for you. That is an honest trade, not an oversight.

### 9.3 The setup wizard

The stock Quick Internet Setup page (`QIS_wizard.htm`, with the `mobile/` files and the stock scripts it loads) stays
for two choices of Operation Mode (4.27): **Repeater** and **AiMesh Node** run the stock wizard's steps for those
modes. Access Point, Media Bridge and the return to Router use Reaper's own step page, and AiMesh → Add node is part of
the AiMesh page. The other setup routes into the wizard are closed: the default setup address sends you to the
dashboard, there is no first-use redirect while the WAN is down, and the landing after a LAN subnet change is the
dashboard. The wizard follows the colour-blind switch (4.27.7).

### 9.4 Kept for an AiMesh node

The stock `PrinterServer.asp` and `Advanced_TimeMachine.asp` stay, with the stock scripts they load, because an AiMesh
node serves them. On the main router their addresses open Reaper's Network Printer Server and Time Machine pages.

### 9.5 Kept because closed code names them

`SDN/sdn.html` (the stock network editor) and `internet_speed.html` (the stock speed test) stay, with the files they
load, because a closed library in the firmware names them and it cannot be checked when it asks for one. They are not
in the menu, carry no Reaper styling, and Reaper's Network (4.21) and Internet Speed pages replace them.

### 9.6 Kept for add-ons

A few small stock scripts that third-party Merlin add-on pages may load (`detect.js`, `base64.js`, `ajax.js`, the
chart scripts and the like) stay, and so does the stock menu file `require/modules/menuTree.js`, which add-on
installers edit to add their tab (Reaper reads the add-on entries from it).

### 9.7 Why these were kept

Each file above is still loaded by something that works, or may be: a mode change, an AiMesh node, closed code, or an
add-on. Removing one would break that flow for no benefit a user can see. Everything else the stock interface used
was removed from the image, including the language-pack strings that only the removed pages displayed (about 430 KB
across the 25 languages). Every string a shipped page displays is still present in every language.
