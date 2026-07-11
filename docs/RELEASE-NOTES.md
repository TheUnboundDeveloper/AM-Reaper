# RT-BE96U "Reaper" — Release Notes

**Release:** v1.4.2 (release candidate — pending final on-hardware validation)
**Firmware:** `RT-BE96U 3006.102.8_Reaper_v1.4.2`
**Base:** Asuswrt-Merlin 3006.102.8 (upstream RMerl/asuswrt-merlin.ng)
**Model:** ASUS RT-BE96U **only** (WiFi 7, Broadcom BCM4916/BCM6813)
**Flash images:** two variants — **with** or **without** the AI Advisor (see §2)

> A security-hardened, rebranded, de-clouded build of Asuswrt-Merlin for the
> RT-BE96U. This document is the release summary; the exhaustive security detail
> is in [`REAPER-FIXES.md`](REAPER-FIXES.md), the per-version history in
> [`CHANGELOG.md`](CHANGELOG.md), and the maintainer merge guide in
> [`GPL-MERGE.md`](GPL-MERGE.md).

---

## 1. What Reaper is

Reaper narrows stock Asuswrt-Merlin to a single model (RT-BE96U), **hardens** the
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
| **Standard** | `RT-BE96U_…_Reaper_v1.4.2_nand_squashfs.pkgtb` | **No — never compiled in** |
| **+ AI Advisor** | `RT-BE96U_…_Reaper_v1.4.2_MCP_nand_squashfs.pkgtb` | Yes (optional, off by default) |

The Standard image contains **zero** trace of the AI Advisor — no daemon, no page,
no menu entry, no settings, nothing hidden or merely disabled. Both are otherwise
identical. Pick whichever you prefer; the AI Advisor is opt-in even in the variant
that includes it.

> Naming note for maintainers: the current build artifacts are named
> `…_Reaper_v1.4.2_nand_squashfs.pkgtb` (with the Advisor) and
> `…_Reaper_v1.4.2_noMCP_…` (without). At release these are re-stamped to the
> convention above (plain = Standard, `_MCP` = with Advisor). Hashes in §8 are
> re-stamped for the final release build.

---

## 3. New since v1.0

### AI Advisor — optional, read-only, LAN-only (v1.4.x)
An **optional** subsystem (present only in the `_MCP` variant, and **off by default**
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

Built with the RT-BE96U userspace toolchain (gcc-10.3, 32-bit ARM) via
`make rt-be96u`, `MAKE_EXIT=0`, "Done! Image 96813GW has been built".

Release-candidate build hashes (SHA-256):

| Artifact | SHA-256 |
|---|---|
| `RT-BE96U_3006_102.8_Reaper_v1.4.2_MCP_nand_squashfs.pkgtb` (with Advisor, flash this) | `0e96f7378eb0da8da10c6e2ae2cdd4e099e84fafc9a073bd600e638e685709d0` |
| `RT-BE96U_3006_102.8_Reaper_v1.4.2_nand_squashfs.pkgtb` (Standard, flash this) | `3073c09091b973190d9defdb95974e46deff5ddb4e859997d00e4df3b41096a1` |

> Hashes above are the current build-candidate images (currently named
> `…_Reaper_v1.4.2` for the Advisor build and `…_Reaper_v1.4.2_noMCP` for Standard).
> They are re-stamped for the final release build once the version is finalized.

**Validation status.** Everything through **v1.3.3** is validated on the physical
RT-BE96U — security hardening rounds 1–4 + latent T1–T4, the avahi CVE backport, all
Hardware QoS engines (v1 global, Classful, v3, v4) end-to-end on metal, the Traffic
Analyzer, the de-cloud removals, and the Reaper UI at all page depths. The **v1.4.x AI
Advisor** is feature-complete and build-verified; its on-hardware validation (arming,
LAN-only bind, token auth, secret redaction, timeout/USB-key teardown) is **in
progress** and is the gating item for the final v1.4.2 release.

---

## 9. Distribution & license

Reaper distributes its **GPL userspace modifications** (source + patches in this
repo) under GPL v2 — see [`../LICENSE`](../LICENSE) and the Reaper-specific notice
[`../LICENSE.reaper`](../LICENSE.reaper). The proprietary Broadcom/ASUS/Trend Micro
binary blobs are **not redistributable**, are not published, and are licensed for
genuine ASUS hardware only (`README.proprietary`). Reaper is provided **as-is, with
no warranty**; run it understanding the residual risks in §6.
