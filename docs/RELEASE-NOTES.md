# RT-BE96U "Reaper" — Release Notes

**Release:** v1.8.0a (Reaper Warden threat/geo firewall + a verified security-hardening pass + Samba 4.15.13a CVE backport. Built for the **RT-BE96U** (MCP variant); noMCP variant and sibling models owed. Metal validation owed. Supersedes the never-released v1.8.0.)
**Firmware:** `3006.102.8_Reaper_v1.8.0a`
**Base:** Asuswrt-Merlin 3006.102.8 (upstream RMerl/asuswrt-merlin.ng)
**Models:** ASUS **RT-BE96U** (primary, hardware-validated) + **RT-BE86U**, **RT-BE88U**, **GT-BE98**, **GT-BE98 Pro** (per-model branches of the same tree). WiFi 7, Broadcom BCM4916.
**Flash images:** two variants per model — **with** or **without** the AI Advisor (see §2)

> A security-hardened, rebranded, de-clouded build of Asuswrt-Merlin for the
> RT-BE96U. This document is the release summary; the exhaustive security detail
> is in [`REAPER-FIXES.md`](REAPER-FIXES.md), the per-version history in
> [`CHANGELOG.md`](CHANGELOG.md), and the maintainer merge guide in
> [`GPL-MERGE.md`](GPL-MERGE.md).

---

## 1. What Reaper is

Reaper narrows stock Asuswrt-Merlin to the ASUS RT-BE Series (primary model RT-BE96U,
plus the RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro siblings), **hardens** the
open-source userspace against remote compromise, **removes** cloud-coupled and
AI-branded attack surface, **rebrands** the web UI, and adds a few genuinely-local
router features ASUS never shipped.

**Design goal / threat model:** harden the device so that **only physical access
can compromise it** — eliminate every remotely reachable code-execution, memory-
safety, and injection flaw in the auditable userspace, and cut the cloud/telemetry
surface that a de-cloud build shouldn't have. Closed-source WiFi drivers and
prebuilt ASUS/Broadcom/Trend Micro blobs are explicitly **out of scope** and
documented as residual risk (see §6).

---

## 2. Two build variants — with or without the AI Advisor

Starting with the v1.4 line, Reaper ships as **two images built from the same
source**, differing only by whether the optional AI Advisor (§3) is compiled in:

| Variant | Image | Contains the AI Advisor? |
|---|---|---|
| **Standard** | `RT-BE96U_…_Reaper_v1.8.0a_noMCP_nand_squashfs.pkgtb` | **No — never compiled in** |
| **+ AI Advisor** | `RT-BE96U_…_Reaper_v1.8.0a_nand_squashfs.pkgtb` | Yes (optional, off by default) |

The Standard image contains **zero** trace of the AI Advisor — no daemon, no page,
no menu entry, no settings, nothing hidden or merely disabled. Both are otherwise
identical. Pick whichever you prefer; the AI Advisor is opt-in even in the variant
that includes it.

> Naming note: the build artifacts are `…_Reaper_v1.8.0a_nand_squashfs.pkgtb`
> (**with** the Advisor) and `…_Reaper_v1.8.0a_noMCP_…` (**without**). §8 lists these
> exact filenames and their hashes.

---

## 3. New since v1.0

### Reaper Warden, a security-hardening pass, and a Samba CVE backport (v1.8.0a)
- **Reaper Warden — optional threat-feed / geo / manual-IP firewall.** A new **Warden** page adds a
  **default-OFF** blocking layer built on the kernel's `ipset` engine: auto-pull known
  malware/botnet/attacker IP lists (FireHOL, Feodo, Spamhaus DROP, DShield) on a schedule, block or
  allow whole countries by CIDR, and take your own manual block/allow lists. It has a strict
  **anti-lockout** design (your LAN, established connections, and an explicit allow-list always pass
  before any drop), fetches feeds over the router's own HTTPS with a JFFS cache that survives reboot,
  and **re-arms automatically** after a firewall restart or cold boot. Optional drop-logging for
  auditing. Off until you enable it.
- **Verified security-hardening pass.** A methodical audit found and closed a set of latent issues in
  the Reaper-owned and adjacent code (format-string, shell-injection guards on VPN Fusion / WireGuard
  / Wi-Fi-scan paths, an out-of-bounds path check, an open-redirect guard, and input-sanitizing of the
  generated Gatekeeper firewall script). None were remotely exploitable in normal use; each is now
  closed. Full technical detail in [`REAPER-FIXES.md`](REAPER-FIXES.md).
- **Samba 4.15.13a — backported CVE-2025-9640.** The SMB3 server (Samba 4.15.13, pinned to this
  router's toolchain and no longer receiving upstream updates) gets the **upstream fix for
  CVE-2025-9640** (uninitialized-memory disclosure in `streams_xattr`) backported as defense-in-depth;
  `smbd` now reports `4.15.13-Reaper-a`. Every other Samba advisory since 4.15.13 was audited and
  confirmed not applicable to this file-server-only, AD-DC-free build.

### VPN-page theming + Network-Map polish (v1.7.6 – v1.7.7)
- **VPN Client/Server pages render cleanly.** On **VPN &rsaquo; VPN Client** (PPTP/L2TP) and **VPN
  Server**, the settings panel no longer flashes the original ASUS blue before the Reaper theme
  loads (v1.7.7), and an earlier fault where the cards could stay stuck in stock colors while the
  page churned in the background — which some users read as "always loading" — is fixed (v1.7.6).
  The Internet Speed test (Adaptive QoS) now uses a single page scrollbar.
- **AURA/RGB lighting control.** On the RGB-capable models, the effect-scheme selector on the
  Network Map router panel no longer shows a stray horizontal scrollbar (v1.7.7). *(The RT-BE96U has
  no AURA hardware; this applies to the RGB-capable siblings.)*

### Gatekeeper — default-deny device access control (v1.7.0, hardened v1.7.3)
- **A new, fully-local device gate.** Gatekeeper lets you approve or block devices on your network:
  the devices the router already knows are grandfathered in when you enable it, anything new lands
  in a **"Pending approval"** list, and blocking is enforced in the firewall. It arms reliably after
  a cold power-cycle and always leaves the HTTPS admin page reachable, so it can never fence the
  administrator out of the control that turns it off. Off by default; entirely on-router, no cloud.

### Security remediation batch + PSIRT class-fix (v1.7.1, v1.7.5)
- **Another audit round (2026-07-21)** closed its findings in v1.7.1, and v1.7.5 class-fixed the last
  `openssl passwd` command-injection sink found while preparing the coordinated-disclosure material
  for **ASUS PSIRT (case 1006563)**. Exhaustive detail in [`REAPER-FIXES.md`](REAPER-FIXES.md).

### Hardening pass + full 24-language UI (v1.6.0)
- **The whole UI is now translated into all 24 non-English languages** it ships (previously the
  Reaper-authored pages fell back to English in every dictionary). Switch language from the
  left-rail selector and the QoS, Traffic Analyzer and AI Advisor pages — help prose included —
  follow, along with the dashboard and the rail clock's localized weekday/month names. Where a
  translated label runs longer than its space it truncates with an ellipsis and reveals the full
  text on hover, so the layout never stretches. *Machine-assisted translation; English stays
  selectable, and native review is recommended before relying on the non-English help text.*
- **Collector efficiency + robustness.** The traffic collector no longer re-reads settings from
  nvram on every 100 ms tick (cached, refreshed once a second), reads the WAN counters without
  reopening their files each tick, resolves each top-talker's MAC once, and throttles the Live
  tables to their real ~1 Hz data rate; every one of its allocations is now failure-checked, and
  the Advisor daemon closes a rare descriptor/child leak. No visible change — the page just costs
  less.
- **Defense-in-depth + fixes.** Input validation on the two spots that write a stored value into a
  session file / firewall command; an **AI Advisor "Save settings"** fix so a rejected save is
  reported instead of silently claimed (and its Refresh button moved next to the title); a
  **Reaper favicon** on the Login/Logout browser tab; and dead-code cleanups.

### Network Diagnostics — optional AI network probes (v1.5.0a)
- **No bundled packet capture.** An earlier internal build carried a `tcpdump`-based Packet
  Capture page; it is **not** shipped (a large legacy dependency for a niche need). Install
  `tcpdump` via Entware on a USB stick if you need capture.
- **AI Advisor diagnostics tier** (AI Advisor variant only): with **per-session, off-by-default**
  consent (a checkbox on the arming card, re-ticked each arm), the read-only Advisor may run
  bounded read-only probes — `ping` / `traceroute` / `DNS lookup` / `netstat` — to localize a
  problem to the **router, client, ISP, or WAN**. Each probe is fixed-argument (no shell),
  one-at-a-time, time-bounded, output-capped, audited to the system log, and target-scoped
  (private addresses that are not on this router's own LAN are refused, so it cannot be used to
  scan the internal network). It still cannot change any setting.

### AI Advisor — optional, read-only, LAN-only (v1.4.x)
An **optional** subsystem (present only in the AI Advisor variant &mdash; the image with no `noMCP` suffix &mdash; and **off by default**
there) that exposes the router as a read-only [Model Context Protocol](https://modelcontextprotocol.io)
server on the LAN. Your **own** AI client, using your **own** API key, connects and
can **read** the router's configuration and traffic to **audit and explain** it —
"is my firewall sane?", "why is my bufferbloat bad?", "what is this device doing?".
It is deliberately fenced to fit the threat model:

- **Read-only.** It exposes curated read tools only; there is no tool that can change
  a setting. The AI recommends; you apply.
- **Off by default and never boot-started.** Nothing listens until you explicitly
  arm it, and it never survives a reboot.
- **LAN-only.** Binds the router's LAN address; never reachable from the internet.
- **Second factor.** Arming needs the admin session **and** an out-of-band **arming
  code** (stored only as a salted hash — the code lives off the router). Optionally,
  a **USB physical key** (v1.4.2): when enrolled, arming also needs the stick, and
  pulling it locks the advisor within ~1 second.
- **Secrets never leave** and **no API key is stored on the router.** Wi-Fi
  passwords, admin credentials, and keys are redacted; the router itself sends
  nothing to any cloud. Network names are shown as your real SSIDs (from the SDN
  profiles), security mode only — never the PSK.
- **Encrypted with the router's own certificate (v1.4.2).** When the router has a web
  (httpd) certificate loaded, the advisor serves **HTTPS using that same certificate**
  — the one your router's web UI uses, **not** a separate cert — and the arming page
  hands you an `https://` URL. If the router has no certificate loaded, it serves plain
  HTTP. (A self-signed router certificate may need to be trusted by your AI client.)

The advisor self-terminates on a session timeout, on disable, or on repeated auth
failure.

### Traffic Analyzer (v1.3.x)
A native, Reaper-themed traffic monitor: **per-device, per-network, and
per-QoS-class** bandwidth with sub-daily history, a 1-second live view with live
top-talkers, an optional monthly-quota warning, and an opt-in WAN latency probe. You
choose where longer-than-a-day history lives (RAM / JFFS / USB). It reads the
Broadcom flow-accelerator's own flow table, so per-device numbers are correct **with
hardware acceleration on**.

### Hardware QoS v3 and v4 (v1.2.8 – v1.2.9)
Extends the Hardware QoS engines with an **aggregate rate cap, per-class guaranteed
minimums, DSCP trust, live per-class counters** (v3), and **per-class weighted
round-robin weights plus an experimental L4S low-latency flag** (v4) — all on a
native Traffic Manager page.

### De-cloud — attack-surface removal (v1.2)
Removed AI-branded and cloud-coupled features to shrink the attack surface, each
dropped with its hooks (closed blobs left unmodified): **Alexa / Google Assistant**,
the **Trend Micro DPI engine** (AiProtection / DPI-based Adaptive QoS / web history),
**AiCloud / WebDAV**, the **AiDisk** cloud-share wizard, the **AAE / AiHome cloud
tunnel**, and the first-boot **QIS EULA / privacy-consent** surface (v1.2.7). The
local Speedtest was restored.

---

## 4. Carried from v1.0

### Hardware QoS — two engines ASUS never shipped
`qos_type=10` runs hardware rate-shaping + PI2 AQM in the Broadcom Runner **with the
flow accelerator left on** (solving the stock accelerator-OR-software-QoS either/or);
`qos_type=11` **Classful** adds per-class priority queues. Both validated on live
hardware (at a 20 Mbit cap, upload loss 6.5% → 0% and loaded latency 71 ms → 30 ms,
all cores under 2%, acceleration still on). Upload-side; download-side aggregate AQM
is pointed at software CAKE, also compiled in. Two Classful properties to know:
classification is fixed when a connection starts (build rules on IP/MAC, port, or
protocol — not "transferred" ranges), and queues are capped individually with no
aggregate shaper (keep class ceilings summing to ~100% for a strict total limit).

### Reaper UI — full rebrand and redesign
Matte-black + crimson theme across the entire web UI: a live-wired landing
**dashboard** and an app-**shell** that loads stock settings pages unmodified in an
iframe (so all settings behavior is preserved). Applied at **serve time from a single
httpd filter**, with a runtime kill-switch: `nvram set reaper_inject=0; restart_httpd`
returns the pristine stock UI with no reflash.

### Scheduled firmware-availability check — fixed, opt-in, default off
The dead stock "scheduled check for new firmware" setting was fixed and set **default
off**: no scheduled check and no outbound update traffic unless you opt in;
notification only, never auto-upgrade.

### Retained Merlin/base capabilities
OpenVPN, WireGuard, IPsec/strongSwan, CAKE QoS, SNMP, IPv6, USB storage / Samba / FTP
/ media server, AiMesh, SDN/MLO, Smart Connect, VPN Director, DNS Director — all from
the 3006.102.8 base.

---

## 5. Security hardening (headline)

Four audit rounds plus a package-CVE backport, all landed in v1.0 and carried
forward. **The command-injection and buffer-overflow classes are cleared** across the
ASUS/Merlin-authored userspace; ~70+ issues fixed. Every fix is compiled into the
build and catalogued by ID in [`REAPER-FIXES.md`](REAPER-FIXES.md).

- **Rounds 1–3 — stock userspace audit** (httpd, rc, shared, libovpn, libcodb,
  libdisk, and the shipping daemons): 8 Critical, 12 High, 19 Medium, 5 Low plus
  internal IPsec-sink hardening.
- **Round 4 — self-review** of the Reaper-authored changes (UI + Hardware QoS) for
  regressions we introduced.
- **Package CVE backport — avahi 0.8 mDNS DoS** (`CVE-2023-38469/38470/38473`),
  ABI-preserving.
- **Latent buffer hardening** (T1–T4) and a **v1.0 pre-release multi-agent code
  audit** of the Reaper-authored C and web UI (no Critical/High found).
- **New-subsystem posture:** the QoS engines, Traffic Analyzer (`rtrafd`), and AI
  Advisor (`rmcpd`) were built to the same threat model — no new inbound listeners
  except the AI Advisor, which is the one deliberate, LAN-only, off-by-default,
  auth-gated exception (see §3).

Because most of the hardened userspace is shared with stock ASUS/Merlin firmware
across Broadcom-HND models, please practice **coordinated disclosure** for
base-firmware findings (see [`../SECURITY.md`](../SECURITY.md)).

---

## 6. Known issues & residual risk — READ BEFORE DEPLOYING

Hardening targets the **ASUS/Merlin-authored userspace**. The items below are **not
fixed** and are tracked in
[`REAPER-FIXES.md` → "Open security items"](REAPER-FIXES.md).

**Must be worked (active):**
- **EOL system libraries ship frozen with known unpatched CVEs** — OpenSSL 1.1.1w,
  Samba 3.6.x, net-snmp 5.7.2, lighttpd 1.4.39, expat 2.0.1, libgcrypt 1.5.1. OpenSSL
  is in the remote TLS path and is the highest-priority backport. (zlib and curl are
  current; avahi is patched.) To be addressed by ABI-preserving CVE backports or an
  ASUS-led version bump.

**Cannot fix in this tree (monitor ASUS):**
- The **auth / token / session core** and the web input filter live in closed-source
  blobs (`web_hook.o`, `priv_webapi.o`) that cannot be source-verified; the WiFi
  drivers are likewise closed. This is the dominant residual risk versus the
  physical-access-only goal. Mitigation: keep remote web admin disabled; every
  downstream sink is hardened regardless. Watch for ASUS firmware/blob updates.

**Resolved since v1.0:**
- **AiCloud / WebDAV** (which had high-severity findings in v1.0 and was disabled
  there) is now **removed** as part of the v1.2 de-cloud work — the stack is gone, not
  merely inert. Do not attempt to re-add it.

**Design decisions:** default admin credentials (mitigated by the forced first-boot
password change) and lower-priority latent hardening are listed in `REAPER-FIXES.md`.

---

## 7. Install & recovery

1. Log in to the router web UI → **Administration → Firmware Upgrade**.
2. Upload the **`…_nand_squashfs.pkgtb`** firmware image for your chosen variant (§2).
   **Do not** flash the `…_loader.pkgtb` (that is recovery-only).
3. First non-stock flash may need `nvram set DOWNGRADE_CHECK_PASS=1` over SSH first.
   A factory reset is recommended when coming from much older or another third-party
   firmware; do **not** reload a saved settings backup after a reset.
4. On first boot, complete setup and **set a strong, non-default admin password**
   (this is the mitigation for the default-creds item).
5. **Recovery:** if a flash fails, use **ASUS Firmware Restoration** in rescue mode
   with the matching `…_loader.pkgtb`.

You can return to stock anytime by flashing an official ASUS image.

---

## 8. Build & image verification

Built per model with the BCM4916 userspace toolchain (gcc-10.3, 32-bit ARM) via
`make <target>` (`rt-be96u` / `rt-be86u` / `rt-be88u` / `gt-be98` / `gt-be98_pro`), each
`MAKE_EXIT=0` with "Done! Image 96813GW has been built" and the noMCP staged filesystem
confirmed free of the AI Advisor.

**v1.8.0a flashable-image hash (SHA-256)** — current head, **RT-BE96U MCP variant** (the
noMCP variant and the four sibling models are owed and will be added on fan-out). Full set in
`SHA256SUMS-v1.8.0a.txt` on the `reaper-firmware/` ladder.

| Image (`3006_102.8_Reaper_v1.8.0a…`) | SHA-256 |
|---|---|
| `RT-BE96U_…_nand_squashfs.pkgtb` (+ AI Advisor) | `0f80ed7e941c2b615b339648d5f829c51887769af3932f6699cce0085ce8b804` |

The **v1.7.7** table below remains the last full five-model, both-variant fan-out for reference.

**v1.7.7 flashable-image hashes (SHA-256)** — the `…_nand_squashfs.pkgtb` you flash. The full
20-file set (both variants + the `…_loader.pkgtb` recovery images) is in `SHA256SUMS-v1.7.7.txt`
on the `reaper-firmware/` ladder.

| Image (`3006_102.8_Reaper_v1.7.7…`) | SHA-256 |
|---|---|
| `RT-BE96U_…_nand_squashfs.pkgtb` (+ AI Advisor) | `eb0391c9da30f82ca03a13ee6fdcc56f888f62fe68824430b65bb8314d61f76e` |
| `RT-BE96U_…_noMCP_nand_squashfs.pkgtb` (Standard) | `1338b4e1ed1862b895a2f130dc202f842055d7a9881879a146e49b8630e78ef0` |
| `RT-BE86U_…_nand_squashfs.pkgtb` (+ AI Advisor) | `12b96e1b1535d9b1d3d9733dc418072a85dbfe3e9400842a112e04dc5b74a9ea` |
| `RT-BE86U_…_noMCP_nand_squashfs.pkgtb` (Standard) | `c6dc3094a1a4025c7b40839c9f50d45bad9ba3de52c502eb2b6105b70806da5b` |
| `RT-BE88U_…_nand_squashfs.pkgtb` (+ AI Advisor) | `a5bfeb1621b30da4ae26d8a0910c42dfbac7a0d67ebeb95329df93a2d7df25f0` |
| `RT-BE88U_…_noMCP_nand_squashfs.pkgtb` (Standard) | `3ad3d6bd5ce99d500c5c3908c03df40d564e5cb293734c96704efb51aa6db26f` |
| `GT-BE98_…_nand_squashfs.pkgtb` (+ AI Advisor) | `69823f8c7788051f907a7cca736edbdae7c626477c1fb414f856deba9879c2d0` |
| `GT-BE98_…_noMCP_nand_squashfs.pkgtb` (Standard) | `10a7bcfb811c2cd4fbbeb13d8a3d77f2479dd921a773b1d10c14855d041923b5` |
| `GT-BE98_PRO_…_nand_squashfs.pkgtb` (+ AI Advisor) | `c2ed0f388699bcc5643947a50c5ebd8db7f795f3a333cbdc61a3a70a23759cb8` |
| `GT-BE98_PRO_…_noMCP_nand_squashfs.pkgtb` (Standard) | `c7c216fe7070e704fa30e492d4f493d47b1f4af2efb853f11e91b38f49ab2189` |

> All five models built + shipped 2026-07-24 (both variants, staged-fs verified) on the
> `reaper-firmware/` ladder alongside `SHA256SUMS-v1.7.7.txt` (which also lists the ten
> `…_loader.pkgtb` recovery images). Metal validation is owed on every model.

**Validation status.** Everything through **v1.3.3** is validated on the physical
RT-BE96U — security hardening rounds 1–4 + latent T1–T4, the avahi CVE backport, all
Hardware QoS engines (v1 global, Classful, v3, v4) end-to-end on metal, the Traffic
Analyzer, the de-cloud removals, and the Reaper UI at all page depths. The **AI Advisor**
(arming, LAN-only bind, token auth, secret redaction, USB third-factor, and the
network-diagnostics tier) is **metal-validated** on the RT-BE96U (v1.4.x–v1.5.0a). In the
v1.5.x line the newest fully metal-validated build is **v1.5.6**; every rung since —
through the current **v1.7.7** — is built + shipped and **awaits flashing** (RT-BE96U in
both variants for each rung; the v1.7.7 release adds the four sibling models, metal owed on
all five). Per-version metal-test checklists are in [`BACKLOG.md`](BACKLOG.md).

---

## 9. Distribution & license

Reaper distributes its **GPL userspace modifications** (source + patches in this
repo) under GPL v2 — see [`../LICENSE`](../LICENSE) and the Reaper-specific notice
[`../LICENSE.reaper`](../LICENSE.reaper). The proprietary Broadcom/ASUS/Trend Micro
binary blobs are **not redistributable**, are not published, and are licensed for
genuine ASUS hardware only (`README.proprietary`). Reaper is provided **as-is, with
no warranty**; run it understanding the residual risks in §6.
