# RT-BE96U "Reaper" — Firmware Roadmap

*Planning document. Applied security fixes are tracked in `REAPER-FIXES.md` (same folder). This roadmap supersedes the earlier "enterprise additions" framing — that survey is demoted to Appendix A for reference.*

---

## Direction (north star)

The reaper build targets a **lean, local-only, predictable** RT-BE96U firmware. Every feature must earn its place by performing a real router function the owner controls — not by cloud convenience or "AI" branding. Threat model is unchanged: **only physical access should be able to compromise the device**; remote/network/cloud-reachable exposure is eliminated.

The project's emphasis has shifted from *adding* capability to **removing unnecessary surface**. Three rules govern everything below:

1. **Reduce surface first.** Prefer removing a feature to maintaining it.
2. **No cloud, no fake-AI, minimal hooks.** Where a feature does something genuinely useful, replace it with a simple local-only ("dumb") equivalent.
3. **Stability is non-negotiable.** Nothing is removed if it risks boot, core networking, the GUI, the build, or long-term maintainability.

Hard constraint (unchanged): the Broadcom closed blobs (wl/dhd/runner fast-path, eapd, acsd, networkmap, wlceventd, cfg_mnt, spwenc, bwdpi engine) are **not edited** — they are either left alone or, where a whole feature is being removed, **dropped** along with their hooks.

---

## Phase 0 — Done / in place (shipped through v1.7.7)

*Per-version detail in [`CHANGELOG.md`](CHANGELOG.md) and [`RELEASE-NOTES.md`](RELEASE-NOTES.md).*

- **Security hardening (Rounds 1–4 + latent T1–T4 + avahi CVE backport)** — see `REAPER-FIXES.md`. ~70+ issues across rc / httpd / shared / libdisk, the network-facing ASUS daemons, and libcodb. (v1.0) Extended since by the **v1.7.1** post-Gatekeeper audit remediation (2026-07-21) and the **v1.7.5** class-closure of C6 across every `openssl passwd` sink (**C6b**, ASUS PSIRT case 1006563).
- **Hardware QoS** — `qos_type=10` (PI2 AQM + shaper in the Broadcom Runner, accelerator stays on, upload) and the `qos_type=11` **Classful** engine (v1.0); extended with aggregate cap / guaranteed minimums / DSCP trust / live stats (**v3**, v1.2.8) and per-class WRR weights + experimental L4S (**v4**, v1.2.9). The local-only QoS the project favours over DPI-based Adaptive QoS.
- **Traffic Analyzer** (v1.3.x) — native per-device / per-network / per-class history, live view, top talkers, quota, opt-in WAN probe; offload-accurate (reads the Runner flow table).
- **AI Advisor** (v1.4.x) — **optional**, read-only, LAN-only MCP server; off by default; compiled out of the Standard build entirely (`RTCONFIG_REAPER_MCP`). Mode A arming code + optional Mode B USB key; **v1.5.0a** adds an opt-in, per-session bounded network-diagnostics tier (ping/traceroute/DNS/netstat). **EXPERIMENTAL**
- **Network Diagnostics** (v1.5.0a) — the AI Advisor's opt-in, per-session bounded network-probe tier (ping/traceroute/DNS/netstat); local, read-only, injection-safe (fixed-argument exec, never a shell; targets scoped so it can't scan the internal network). *A bundled `tcpdump` packet-capture page was evaluated and deliberately left out to keep the image lean — install `tcpdump` via Entware if you need capture.*
- **De-cloud removals (Phase 1 — EXECUTED, shipped v1.2):** Alexa/Google Assistant, Trend Micro DPI (`bwdpi`), AiCloud/WebDAV, the AiDisk wizard, the AAE/AiHome cloud tunnel, and the first-boot EULA/consent surface (v1.2.7).
- **Gatekeeper** (v1.7.0, hardened v1.7.3) — opt-in, **default-deny** device access control with its own page: known devices are grandfathered on enable, new devices are held at the gate (approve / block / internet-only / timed guest pass), enforced at the firewall/bridge layer with self-heal. Off by default, fully on-router (no cloud); arms reliably after a cold boot and always leaves the HTTPS admin page reachable so the owner can never be locked out.
- **Reaper UI** — full rebrand + serve-time theme injection with a runtime kill-switch (v1.0).
- **Multi-model fleet** — the v1.0 tree was stripped to the RT-BE96U; the sibling BCM4916 models (**RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro**) were reintroduced from per-model branches starting v1.5.0e, and all five ship as of **v1.7.7** in both variants. RT-BE96U remains the primary, hardware-validated build; sibling metal validation is owed.

---

## GUI / styling polish — backlog  *(address before advancing the roadmap)*

Observed 2026-06-30 on the flashed `3006.102.8_reaper` image (boots, stable, 17 clients). **Do not start until the on-device stability assessment is complete** — captured here so they are not lost. Working well and confirmed on-device: REAPER banner + red retheme, red device icons on the Network Map client list, Smart Connect master toggle, hardware-QoS GUI additions.

| # | Issue | Detail / where | Likely cause |
|---|---|---|---|
| G1 | **Device-icon red theme is incomplete** | The reaper red-on-black device icons (patch 0026 / `device-map.css`+`clientlist.css`) apply **only to the Network Map client list** (+ its "View List" popup). Other pages that render client/device icons still show the **stock white-on-grey** icons. Confirmed: **LAN → DHCP Server → "Manually Assigned IP around the DHCP list"** (per-row device icons). Audit & extend to every icon context: DHCP manual assignment, Parental Controls, Access Control / Wireless MAC filter, Open NAT, Time Scheduling, etc. | Those pages don't load `device-map/device-map.css`+`clientlist.css`, or render icons via a different tile/icon container class. Find the shared icon source (or where each page pulls icon CSS) and apply the reaper override there. |
| G2 | **Overlapping buttons** | Some buttons overlap (exact page to pinpoint during the pass). | Likely fallout from the red retheme (gradient/padding/margins in `form_style.css` / `index_style.css`). |
| G3 | **Buttons weirdly sized, text off-center** | Button sizing/padding off; label not centered. | Review `.button_gen` / tab-button (`.tab_NW`/`.tabclick_NW`) / nav-button metrics changed during the retheme. |

> Gate: these are GUI polish, not stability risks, but they should be cleaned up **before advancing Phase 1+** so the interface is coherent. Each fix is build-verified (`make rt-be96u`, gcc-10.3) and hardware-checked like everything else.

---

## Phase 1 — Feature removal / de-bloat  *(EXECUTED — shipped in v1.2; see CHANGELOG)*

> **Status: done.** The removals in the table below were executed and shipped across the `v1.1-beta*` images and consolidated into **v1.2** (AiCloud/WebDAV, Alexa/Google, Trend Micro DPI, AiDisk wizard, AAE/AiHome tunnel), with the first-boot EULA/consent surface removed in **v1.2.7**. AiMesh was kept as planned. The dependency maps below are retained as the historical record of how each removal was scoped.

Strip AI-branded, cloud-coupled, legacy, and superfluous features while keeping the router's core — routing, Wi-Fi, firewall, DHCP, DNS, VPN, and management — intact and stable.

**Process applied to every feature (no exceptions):**

1. Identify all code, assets, services, GUI references, and nvram tied to the feature.
2. Map cross-dependencies with anything we keep.
3. Remove or stub only what is safe.
4. Replace genuinely useful behaviour with a simple local-only function.
5. **Test on real hardware** before the change is considered complete.

### Targets

| Feature | Decision | Why / key dependency | Replacement |
|---|---|---|---|
| **AiCloud / WebDAV** | **Finish removal** | Not actually removed — only compiled out (`RTCONFIG_WEBDAV` unset). Full source, GUI, assets, hooks still dormant in the tree. Audit also found a weak (timestamp-based) share-link token and path-traversal gaps. | None (cloud file access is out of scope) |
| **Amazon Alexa** | **Full removal** | Cloud "skill" integration; no core router dependency. | None |
| **AiProtection** (TrendMicro `bwdpi` DPI) | **Remove** | Closed DPI engine. Removing it **also removes Adaptive QoS (`qos_type=1`), Web History, Traffic Analyzer, and DPI-based malware/IPS**. Owner runs hardware QoS, so no local loss — but a real capability cut for distribution, called out explicitly. | Keep time/schedule-based Parental Controls and basic traffic accounting (neither needs `bwdpi`) |
| **AiDisk** | **De-wizard; keep local sharing** | AiDisk is a GUI wizard over `smbd`/`vsftpd`/`minidlna` that also wires in external/DDNS access. | Keep local USB file sharing (Samba/FTP/DLNA) via a minimal local-only page; drop the wizard, cloud-share coupling, and branding |
| **AiMesh** | **Keep (for now)** | Removal needs a replacement onboarding/mesh-management mechanism for existing and new nodes; entangled with the `cfg_mnt` blob + `amas`. | Future: a simplified, non-cloud "dumb" mesh manager — designed and tested *before* any removal |

**Mechanics of a removal** (per feature): delete the dedicated source, rc service hooks (`start_*`/`stop_*`, `notify_rc`, `add_rc_support` tokens), GUI pages / JS / images / icons / menu entries / help-and-language tokens, nvram defaults, generated config writers, and any shipped binaries/blobs — while leaving shared infrastructure (e.g. lighttpd core, which the captive portal also uses via the separate `uamsrv`; Samba/FTP/DLNA, which local sharing needs) untouched.

**Further de-bloat review candidates** (assess during the sweep): the ASUS cloud account / **AAE / `mastiff` / `asuscomm` cloud tunnel** and token-binding endpoints — note this tunnel is currently **live and shared with the ASUS Router app (AiHome)**, so separate plain local DDNS (retain) from the cloud tunnel/remote-app access (review for removal); plus any other bolted-on branded wizards or marketing pages surfaced during reconnaissance.

> Detailed per-feature footprint + dependency maps are being compiled (read-only reconnaissance) to drive surgical removal. Execution is staged: one feature at a time, build-verified and hardware-tested before the next.

---

## Phase 2 — Security package currency *(serves "safer")*

Still aligned with the lean/safe goal, but **scoped down by Phase 1** — we do not update what we are about to delete:

- **Contained, real-CVE updates:** expat 2.0.1 → 2.6.x, net-snmp 5.7.2 → 5.9.x, pcre1 → pcre2. The lighttpd update becomes largely moot once AiCloud/WebDAV is removed and only the captive-portal use remains — **re-scope after Phase 1.**
- **Big, staged:** OpenSSL 1.1.1w (EOL) → 3.x (ABI break; stage per-consumer on a branch). Samba currency only matters if local sharing is retained (it is) — update if/when it earns the effort.

---

## Phase 3 — Local-only quality & performance

- Hardware QoS (done) is the bufferbloat answer; CAKE remains the software alternative.
- Conservative `sysctl`/conntrack tuning; **keep Broadcom flow-accel ON.**
- Entropy (`haveged` / `jitterentropy`) already healthy.

---

## Explicitly out of scope now

The earlier "enterprise additions" survey (dynamic routing/BGP-OSPF, freeradius, Suricata, CrowdSec, NetFlow, etc.) **conflicts with the lean direction and is not baked into the firmware.** Anything genuinely wanted is added via **Entware on USB** — reversible, no firmware bloat — not the image. Retained as Appendix A for reference only.

---

## Stability gates (apply to every change)

No removal ships if it introduces: boot instability, a broken build or dependency, GUI regressions, service crashes, missing assets, or unpredictable runtime behaviour. Every change is **build-verified** (`make rt-be96u`, gcc-10.3) **and hardware-tested** before it is called done. The intent throughout: make the firmware **smaller, cleaner, safer, and more predictable** while preserving core performance, stability, and reliability.

---

## Appendix A — Prior package + enterprise-additions survey *(reference only)*

*Kept for reference; most "additions" below are now out of scope per the lean direction. The **package-version table** remains relevant to Phase 2.*

### Package versions — current vs stale (security-update candidates)

| Package | In tree | Status | Notes |
|---|---|---|---|
| **OpenSSL** | 1.1.1w (Sep 2023) | **EOL** | Links ~everything (httpd, openvpn, curl, lighttpd, wpa_supplicant). #1 risk, highest effort; ABI break on → 3.x. |
| **Samba** | 3.5.x / 3.6.x | **Ancient/EOL** | SMB1-era; only matters if local sharing retained. |
| **expat** | 2.0.1 (2007) | **Ancient** | Many CVEs; contained update → 2.6.x. |
| **lighttpd** | 1.4.39 (2016) | Old | AiCloud/WebDAV front — largely moot post-removal. |
| **net-snmp** | 5.7.2 (2012) | Old | snmpd ships; → 5.9.x. |
| **pcre** | 8.31 (2012) | EOL (PCRE1) | → PCRE2. |
| **zlib** | 1.2.12 | Minor | → 1.3.1 (low urgency). |
| curl | 8.17.0 | **Current ✓** | |
| strongSwan | 6.0.4 | **Current ✓** | |
| dropbear (SSH) | ~2026.x | **Current ✓** | |

**NOTICE** OpenSSL version number is left unchanged but file is maintained and updated by developers. Finding is suspected false positive but warrants investigation.

### Potential Enterprise additions *(de-prioritised — Entware-on-USB, not firmware)*

Quagga OSPF/BGP/IS-IS (in tree, unshipped), freeradius (802.1X), fprobe (NetFlow), CrowdSec, Suricata, Unbound, AdGuardHome, Tailscale/ZeroTier, OpenSSH. These remain *possible* via the USB runtime layer but are **not** roadmap items for the image — they run counter to the de-bloat goal.
