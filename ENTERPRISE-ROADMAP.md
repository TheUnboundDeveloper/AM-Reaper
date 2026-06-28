# BE96U "reaper" — package updates + enterprise hardening survey (2026-06-28)

Constraint reminder: we cannot edit the Broadcom blobs (wl/dhd/runner/archer fast-path, eapd, acsd, networkmap, wlceventd, cfg_mnt, spwenc). Everything below is in the open-source userspace / kernel modules / sysctl / runtime packages — the layers we **can** change.

Hardware budget (RT-BE96U): quad-core ARM Cortex-A53, 2 GB RAM, NAND. Comfortably runs Go static binaries and moderate daemons; the pressure valve for anything heavy is **Entware on USB** (no firmware rebuild).

---

## A. Package versions — current vs stale (security-update candidates)

| Package | In tree (built) | Status | Notes |
|---|---|---|---|
| **OpenSSL** | **1.1.1w** (Sep 2023) | **EOL** | Both `openssl/` and `openssl-1.1/` are 1.1.1w. No more upstream security fixes. Links into ~everything (httpd, openvpn, curl, lighttpd, wpa_supplicant…). **#1 risk, highest effort.** |
| **Samba** | **3.5.8 / 3.6.x** | **Ancient/EOL** | SMB1-era, EOL since ~2015, large CVE history. SMB3 / Samba 4 = big rewrite. |
| **expat** | **2.0.1** (2007) + `expat/` | **Ancient** | XML parser; many CVEs since. Verify which dir builds; if 2.0.1, update to 2.6.x. |
| **lighttpd** | **1.4.39** (2016) | Old | AiCloud/WebDAV front; CVEs since. Update to 1.4.7x. |
| **net-snmp** | **5.7.2** (2012) | Old | snmpd ships. Update to 5.9.x (also better SNMPv3). |
| **pcre** | **8.31** (2012) | EOL (PCRE1) | Move to PCRE2 (consumers permitting). |
| **zlib** | **1.2.12** (2022) | Minor | →1.3.1 (low urgency). |
| curl | **8.17.0** | **Current ✓** | `curl-7.21.7` is dead legacy; modern curl builds. |
| strongSwan | **6.0.4** | **Current ✓** | IPsec userspace is modern. |
| dropbear (SSH) | **~2026.x** | **Current ✓** | SSH server fine. |
| wireguard-tools | 1.0.20210914 | Fine | Stable. |

**Recommendation order (security):** expat → lighttpd → net-snmp → pcre are *contained* updates (fewer consumers, moderate effort, real CVE wins). **OpenSSL 1.1.1→3.x** and **Samba 3→4** are the two big, disruptive ones — worth planning but stage carefully (OpenSSL 3 changes ABI + deprecates APIs that httpd/openvpn/lighttpd call).

---

## B. Already in the tree but NOT shipped — cheap enterprise wins (low effort, no new ports)

These exist in `release/src/router` and just need to be built/installed/wired:

1. **Quagga OSPF / BGP / IS-IS** — source has `ospfd, ospf6d, bgpd, isisd, ripngd`; **only `zebra`+`ripd` ship today.** `RTCONFIG_QUAGGA=y`. Enabling ospfd/bgpd turns this into a real dynamic-routing edge device (site-to-site, multi-router campus). *Highest value / lowest effort.*
2. **freeradius-server-3.0.0** — in tree, not shipped. Enables **802.1X / WPA-Enterprise** auth and a local RADIUS for VPN/switch auth. Pairs with the existing `chilli` captive portal.
3. **fprobe (NetFlow)** — `fprobe-1.1` in tree, not built. **Flow export to a NetFlow/IPFIX collector** = enterprise traffic visibility.
4. **sch_cake (CAKE qdisc)** — source present. Modern SQM/bufferbloat control (see Perf below).
5. **Tor** — already shipped (`/usr/sbin/Tor`, `RTCONFIG_TOR=y`); just confirm/expose policy.
6. **stubby (DNS-over-TLS)** — already shipped, `RTCONFIG_DNSPRIVACY=y`. Could extend to DoH.

---

## C. New additions for an "enterprise, SSH-managed" posture (ports or Entware)

"Entware" = runtime ipkg packages on USB, no firmware rebuild — the safe, reversible way to add heavy software.

**Visibility / monitoring**
- **prometheus node_exporter** (Go static, Entware) → metrics to Prometheus/Grafana.
- **collectd** or **telegraf** → push metrics/SNMP to a TSDB.
- **rsyslog remote** (already in tree) → ship logs to a SIEM (Graylog/ELK/Loki).
- **NetFlow via fprobe** (B-3) → ntopng/Elastiflow.

**Threat defense**
- **CrowdSec** (Go, Entware) — modern, community-blocklist fail2ban/IPS; complements the existing `protect_srv` brute-force daemon.
- **Suricata** (Entware, needs RAM — BE96U's 2 GB is enough for a moderate ruleset) — real IDS/IPS on the WAN.
- **Unbound** (validating recursive resolver + DNSSEC, Entware/port) — enterprise DNS independence; pair with stubby for DoT upstream.
- **AdGuardHome** (Go, Entware) — DNS filtering + DoH/DoT server + per-client policy.

**Connectivity / VPN**
- **WireGuard server** — `wg` already ships; script a server config (ASUS GUI also exposes it). Modern road-warrior + site-to-site.
- **Tailscale / ZeroTier** (Entware) — zero-config mesh / SD-WAN overlay; ideal for SSH-only management of remote units.
- **OpenVPN** already hardened (Round-2 fixes) — keep for compatibility.

**Identity / access**
- **freeradius** (B-2) for 802.1X.
- Harden SSH: dropbear is current, but for enterprise key/cert policy consider **OpenSSH** (Entware) — CA-signed host/user certs, match blocks, richer ciphers.

---

## D. Performance (within our reach — the datapath fast-path is blob-owned)

- **CAKE / fq_codel SQM** (sch_cake in tree): the single biggest *felt* win — kills bufferbloat, keeps latency low under load. Caveat: software shaping bypasses Broadcom HW NAT accel, so it caps shaped throughput to what the CPUs can push (fine at typical WAN speeds; a tradeoff at multi-Gbit). Make it opt-in per-WAN-speed.
- **sysctl tuning for high connection counts**: raise `nf_conntrack_max`, `netdev_max_backlog`, `somaxconn`, `rmem/wmem_max`, `tcp_fastopen` — enterprise concurrency.
- **TCP BBR** (kernel 4.19 supports it) for connections the *router itself* terminates (VPN, AiCloud); marginal for pure forwarding.
- **Entropy**: `haveged` + `jitterentropy-rngd` already present → good TLS/VPN setup latency.
- **IRQ/CPU affinity**: `wlaffinity` present; tune RX queues across the 4 cores for high PPS.
- Keep Broadcom flow-accel (runner/archer/pktrunner) ON — don't let SQM/iptables rules silently disable it unless intended.

---

## Suggested first moves (when we pick this up)
1. **Cheap / high-value:** enable Quagga ospfd/bgpd + fprobe NetFlow + a CAKE SQM option (all in-tree).
2. **Contained security updates:** expat, lighttpd, net-snmp (real CVE wins, bounded blast radius).
3. **Runtime enterprise layer via Entware:** node_exporter + CrowdSec + Tailscale (no firmware risk, reversible).
4. **Plan the big one:** scope an OpenSSL 1.1.1 → 3.x migration (separate branch, staged per-consumer).

---

*This is a planning document, not a fix list. Security fixes already applied are tracked in `REAPER-FIXES.md` (same folder).*
