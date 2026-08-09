# Reaper Firewall — Enhancement Plan

> Status: **PROPOSED** (design approved in shape 2026-08-08; not yet built).
> Audience: tech-savvy users **and** network engineers.
> Decisions locked with the owner: prioritize **all four** gap areas · **Basic/Advanced**
> UI · **commit-confirm auto-rollback** · **stay on iptables/ipset** (no nftables).

## 1. Where the firewall is today

- **Backend:** pure `iptables`/`ip6tables`, kernel 4.19. One ~9,450-line `rc/firewall.c`
  monolith + `rc/firewall_sdn.c`. No nftables anywhere. Closed blobs (cfg_mnt, networkmap)
  and every stock chain emit iptables — so iptables is the only viable backend.
- **Discipline is sound:** default-drop tails on INPUT/FORWARD, DoS `SECURITY` chain on WAN,
  UPnP off per-WAN, `INVALID`-state drops.
- **Reaper already owns chains** via a re-apply hook (`firewall.c` ~9397/9402, re-run after any
  rebuild flush): `REAPER_WARDEN` (ipset inbound geo/threat), `REAPER_GKI/GKF` (Gatekeeper MAC
  allowlists). This is the exact extension point the new engine plugs into.

### Gaps this plan closes
1. **No user-defined rules in the GUI.** Custom allow/deny = SSH + `firewall-start` today.
2. **IPv6 is second-class.** ip6tables isn't even surfaced; stock v6 firewall page is bare.
3. **No egress/outbound control.** Everything is inbound; no IoT containment, no outbound geo.
4. **Logging off, no viewer.** `fw_log_x=none`; no live drops feed, no per-rule hit counters.
5. **No safety net.** A custom-rules feature needs commit-confirm/rollback (Warden lockout precedent).

## 2. Architecture (shared foundation)

- **New rc generator `rc/reaper_fw.c`** builds `REAPER_FWI` / `REAPER_FWF` / `REAPER_FWO`
  chains from an nvram ruleset, hooked into INPUT/FORWARD/OUTPUT and **re-applied from the same
  post-rebuild hook** GK/Warden use (survives `restart_firewall`, WAN events, service restarts).
- **Dual-stack by construction:** every rule is address-family aware and emits to `iptables`
  **and** `ip6tables` unless pinned to one family. This structurally fixes gap #2.
- **ipset-backed** for multi-address / device-group / geo rules (reuse Warden's ipset +
  `/jffs` persistence pattern; new rules may *reference* Warden/GK ipsets, not duplicate them).
- **Native page `Reaper_Firewall.asp`** — registered in `reaper_inject.c reaper_native[]`,
  theme tokens, `RFW_*` dict tokens ×25 lockstep, menuTree entry. Basic/Advanced toggle.
- **CGI `reaper_fw.cgi`** — validate / compile-preview / apply / confirm / read-back
  hit-counters. Never applies unvalidated input; the GUI edits a **safe rule DSL**, never raw
  iptables strings.
- **Storage:** nvram `reaper_fw_rules` (rulelist, like `qos_bw_rulelist`) + `/jffs` for large sets.
- **Boundary:** Warden (inbound geo/threat feeds) and Gatekeeper (per-device internet on/off)
  stay as-is. This is the *general-purpose* rules layer beside them; the page cross-links, does
  not absorb them.

### Safety model (applies to every write path)
- **Commit-confirm / auto-rollback:** apply → snapshot current ruleset + `iptables-save` →
  apply candidate → arm a revert (default 60 s) → GUI shows "Keep changes? [Confirm]" with a
  countdown → confirm cancels the revert; silence (you locked yourself out) restores the snapshot.
- **Anti-lockout invariants:** the engine refuses to generate a rule that would drop the current
  admin session's source or the management port(s) without an explicit override **and** a second
  confirm. Directly targets the Warden-lockout failure class.

### Validation reality
Firewall is **metal-only-validatable** (the mock can't run iptables) — same as Warden/GK. Each
phase = build + on-metal test. The **rmcpd lab MCP is now the test harness**: read live chains +
`-nvL` hit counters, `exec` to verify an apply took, `net_*` probes to confirm reachability
before/after. Every phase below lists its MCP-driven acceptance checks.

## 3. Phased build

### Phase 0 — Visibility + logging (low risk, ship first)
- Read-only **Firewall Status** view on `Reaper_Firewall.asp`: INPUT/FORWARD/OUTPUT for **v4 and
  v6 side by side**, per-rule **hit counters** (`iptables -nvL` / `ip6tables -nvL`), and which
  Reaper subsystem owns each chain (GK / Warden / custom).
- **Structured logging** toggle + **live drops viewer** (tail `DROP*`-prefixed syslog lines: top
  blocked sources, per-prefix counts) — feeds the existing analytics export.
- Extend the MCP `get_firewall_summary` to include **ip6tables + hit counters** (also improves the
  Advisor).
- *Acceptance (MCP):* `get_firewall_summary` returns v6 + counters; drops appear in the viewer
  after a `net_ping` to a blocked dst.

### Phase 1 — Custom rules engine + page (the core)
- `rc/reaper_fw.c` generator + the three chains + re-apply hook wiring.
- **Rule model:** enabled · direction · action (accept/drop/reject/log) · proto · src (ip/cidr/
  range/ipset/MAC/device) · dst · sport/dport(range) · in/out iface (WAN/LAN/VLAN/VPN) · schedule
  (reuse `timematch_conv`) · rate-limit · comment · order.
- **Page:** **Basic** = form builder + reorderable table, enable toggles, live hit counts;
  **Advanced** = raw ruleset editor in the safe DSL with validation + syntax help + a **dry-run
  "compile → preview exact iptables"** that shows what would apply without applying.
- **Commit-confirm/auto-rollback** lands here and gates all writes.
- *Acceptance (MCP):* add an allow rule, confirm it appears with counters climbing under a
  matching `net_ping`; let a rollback expire and confirm the snapshot restores via `exec`.

### Phase 2 — Egress / outbound control (after the safety net is proven)
- Per-device / per-VLAN **egress policy** on the rules engine + ipset device groups
  ("default-deny egress for group X except LAN, DNS, NTP, these dst/port"). **Outbound geo**
  (reuse Warden country ipsets on the FORWARD-out/OUTPUT side — today inbound-only).
- Device grouping UI leverages the existing Devices-page identity data.
- Riskiest for breakage → lands only after Phase 1 rollback is field-proven.

### Phase 3 — NAT / port-forward hardening + power tools
- **Source-restricted port forwards** (only from these IPs/CIDRs/countries), scheduled forwards,
  one-click "expose but Warden-geo-restrict," hairpin/loopback verification.
- **Rule tester** ("would a packet A:p→B:q match, and where?"), ruleset export/import, firewall
  section in the analytics export.

## 4. Cross-cutting
- i18n: `RFW_*` tokens, 25-lang lockstep, English-seeded (translation pass owed, per convention).
- Backend: iptables/ipset only; nftables explicitly out of scope.
- Every phase: build (all 5 models both variants), 19-check verify gate, on-metal test via the
  rmcpd lab MCP, then fleet fan-out.
- New page must be in `reaper_inject.c reaper_native[]` (own chrome, no stock-CSS inject) and
  left-aligned/full-bleed in the shell iframe (reaper-ui rule 32).

## 4b. Stock pages → native replacement map (menu group `menu_Firewall`, `<#menu5_5#>`)

The four stock tabs and the nvram each drives (captured 2026-08-08 from source + live box):

| Stock page | Tab token | Drives | Native replacement |
|---|---|---|---|
| `Advanced_BasicFirewall_Content.asp` | `menu5_1_1` | `fw_enable_x`, `fw_dos_x`, `fw_log_x`, `misc_ping_x` (respond to WAN ping), `fw_wl_enable_x` (WAN→LAN filter) | **General** tab |
| `Advanced_Firewall_Content.asp` | `menu5_5_4` | LAN→WAN Network Services filter: `fw_lw_enable_x`, `filter_lw_default_x` (white/black), `filter_lwlist` (≤128) + schedule (`filter_lw_date_x`/`time_x`/`time2_x`), `filter_lw_icmp_x` | **Network Services** tab |
| `Advanced_URLFilter_Content.asp` | `menu5_5_2` | `url_mode_x`, `url_rulelist` + schedule | **URL Filter** tab |
| `Advanced_KeywordFilter_Content.asp` | `menu5_5_5` | `keyword_rulelist` + schedule | **Keyword Filter** tab |

Apply flow for all: POST `start_apply.htm`, `action_script=restart_firewall`, `action_wait=5`.
Backends already exist in `firewall.c` (`write_UrlFilter`, `write_access_restriction`, the
`filter_*list` LAN/WAN builders) — the native General/NetworkServices/URL/Keyword tabs are
**www-only** (reuse the nvram + apply), no C. Only the **new** tabs (Status, Rules, Egress,
Logging) need the `rc/reaper_fw.c` engine + `reaper_fw.cgi`.

### Proposed tab order under the Firewall menu (native)
`Reaper_Firewall.asp` hub with tabs: **Status** · **General** · **Rules** · **Egress** ·
**Network Services** · **URL Filter** · **Keyword Filter** · **Logging**. (Stock pages kept on
disk as one-line-revert fallbacks, per the WiFiPro precedent.)

## 4c. Live posture snapshot (RT-BE96U, v2.3.1, 2026-08-08 — reference baseline)
iptables/ipset, default-drop tails present. Reaper chains live: `REAPER_WARDEN` (ipset inbound
geo/threat, ~45 country sets), `REAPER_GKI/GKF` (Gatekeeper MAC allow). `SECURITY` DoS chain on
WAN. `fw_log_x=none`. rmcpd `5219` LAN-only. UPnP off per-WAN. IPv6: `wan_proto=dhcp` (v6 not up
yet); ip6tables not surfaced by the MCP tool (visibility gap Phase 0 closes).

## 5. Open questions for later
- Rollback timer default (60 s?) and whether to persist "armed but unconfirmed" across an httpd restart.
- Whether the Advanced DSL should also accept a `firewall-start`-style escape hatch for true raw rules.
- Egress default-deny: opt-in per group only, or offer a whole-network "strict egress" mode.
