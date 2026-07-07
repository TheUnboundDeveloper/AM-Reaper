# RT-BE96U "Reaper" — Release Notes

**Release:** v1.0 (2026-07-07)
**Firmware:** `RT-BE96U 3006.102.8_Reaper`
**Base:** Asuswrt-Merlin 3006.102.8 (upstream RMerl/asuswrt-merlin.ng)
**Model:** ASUS RT-BE96U **only** (WiFi 7, Broadcom BCM4916/BCM6813)
**Flash image:** `RT-BE96U_3006_102.8_reaper_nand_squashfs.pkgtb`

> A security-hardened, rebranded build of Asuswrt-Merlin for the RT-BE96U. This
> document is the release summary; the exhaustive security detail lives in
> [`REAPER-FIXES.md`](REAPER-FIXES.md) and the maintainer merge guide in
> [`GPL-MERGE.md`](GPL-MERGE.md).

---

## 1. What Reaper is

Reaper narrows stock Asuswrt-Merlin to a single model (RT-BE96U) and hardens the
open-source userspace against remote compromise, then rebrands the web UI.

**Design goal / threat model:** harden the device so that **only physical access
can compromise it** — eliminate every remotely reachable code-execution, memory-
safety, and injection flaw in the auditable userspace. Closed-source WiFi drivers
and prebuilt ASUS/Broadcom/TrendMicro blobs are explicitly **out of scope** and
documented as residual risk (see Section 5).

---

## 2. Security hardening (headline)

Four audit rounds plus a package-CVE backport. **The command-injection and
buffer-overflow classes are cleared** across the ASUS/Merlin-authored userspace;
~56+ issues fixed. Every fix is compiled into the RT-BE96U build and catalogued
by ID in `REAPER-FIXES.md`.

- **Rounds 1-3 — stock userspace audit** (httpd, rc, shared, libovpn, libcodb,
  libdisk, and the shipping daemons). Fixed **8 Critical, 12 High, 19 Medium,
  5 Low** plus internal IPsec-sink hardening. Highlights:
  - Pre-auth stack overflow in `web.c` `do_CoBrand_img` (ASan-verified).
  - IPsec certificate/PKCS#12 command injection → argv exec + validation.
  - Samba account/password shell-escape; DLNA NULL-deref.
  - snmpd config-injection (CR/LF strip) and SNMPv3 field injection.
  - Pre-auth login `b64_decode` clamp; dnsmasq/inadyn injection at the sink;
    firewall iptables rule-field injection guards; libcodb SQL-identifier
    allow-list; memory-safety fixes in snooper/urlfilterd/lltdc/wsdd2 listeners.
- **Round 4 — self-review** of the Reaper-authored changes (UI + Hardware QoS)
  for regressions we introduced (R4-1…R4-4): a pre-auth `b64_decode` underflow,
  an off-origin iframe framing, and two defense-in-depth encodings.
- **Package CVE backports — avahi 0.8 mDNS DoS** (`CVE-2023-38469`,
  `CVE-2023-38470`, `CVE-2023-38473`): a crafted mDNS packet could abort the
  auto-started `avahi-daemon` (UDP 5353). Backported the upstream production
  fixes with no version bump (ABI preserved).
- **Latent buffer hardening** (`REAPER-FIXES.md` T1-T4): bounded a class of
  pre-sized-buffer `strncat`/`alloca` sites (the libcodb SQL builder, the QoS
  IP-range translator, list dedup, and the DHCP RFC3397 handler) as
  defense-in-depth — no behavior change, overflow-safe if a size assumption is
  ever violated.
- **v1.0 pre-release code audit** (full multi-agent sweep of the Reaper-authored
  C and web UI): no Critical/High found. Closed the remaining unbounded
  `strncpy` sites in the QoS `ip_range_checker` (a stock pattern that could
  overflow a stack buffer on a malformed rule address) and a HW-QoS Classful
  edge where a blank upload bandwidth throttled every class; plus minor UI
  polish.

Reusable fix patterns, per-ID commit trail, and reachability triage are in
`REAPER-FIXES.md`.

---

## 3. New features

### Hardware QoS (upload-only) — a QoS engine ASUS never shipped
A third QoS mode (`qos_type=10`) that runs hardware rate-shaping + AQM (PI2) in
the Broadcom Runner **with the flow accelerator left on** — solving the stock
either/or (accelerator OR software QoS). Proven on live hardware: at a 20 Mbit
cap, upload packet loss went 6.5% → 0% and loaded latency 71 ms → 30 ms
(bufferbloat eliminated) with all four cores under 2% and HW acceleration still
enabled; re-validated at a 2.1 Gbit cap. Selectable in the QoS GUI; clearly
labelled upload-only (download-side aggregate AQM is pointed at software CAKE,
which is also compiled in).

### Hardware QoS — Classful (upload-only), validated on metal
A fourth engine (`qos_type=11`) extends Hardware QoS with per-class priority
queues: the Traditional-QoS rules editor classifies upload traffic into up to 5
classes, each mapped to its own Runner egress queue with PI2 AQM and a
per-class bandwidth ceiling — still with the flow accelerator on. Validated
end-to-end on the physical RT-BE96U: 7-queue PI2/shaper programming, class-mark
→ hardware-queue steering on accelerated flows, priority order under
saturating load. Two properties to know: (1) classification is fixed when a
connection starts, so **"transferred"-range rules do not reclassify long
flows** — build rules on device IP/MAC, port, or protocol instead; (2) queues
are capped individually with **no aggregate shaper**, so for a strict total
limit keep the class ceilings summing to ~100%.

### Reaper UI — full rebrand and redesign
Matte-black + crimson theme across the entire web UI: a live-wired landing
**dashboard**, an app-**shell** frame that loads stock settings pages unmodified
in an iframe (so all settings behavior is preserved), and consistent theming at
every page depth. The theme is applied at **serve time from a single httpd
filter** (not baked into pages), with a runtime kill-switch:
`nvram set reaper_inject=0; restart_httpd` returns the pristine stock UI with no
reflash.

### Retained Merlin/base capabilities
OpenVPN, WireGuard, CAKE QoS, SNMP, IPv6, USB storage / Samba / FTP / media
server, AiMesh, SDN/MLO, Smart Connect — all from the 3006.102.8 base.

---

## 4. For maintainers — mergeability

The theme was de-inlined so stock pages stay byte-pristine and merge cleanly with
each upstream Asuswrt-Merlin drop. The recurring merge cost is reduced to ~46
hardening C files plus a handful of package backports. Full procedure (rebase,
double-fix audit, re-apply the one httpd hook) is in `GPL-MERGE.md`.

---

## 5. Known issues & residual risk — READ BEFORE DEPLOYING

Hardening targets the **ASUS/Merlin-authored userspace**. The items below are
**not fixed** and are tracked with severities in
[`REAPER-FIXES.md` → "Open security items still requiring work"](REAPER-FIXES.md#open-security-items-still-requiring-work-2026-07-05).

**Must be worked (active):**
- **EOL system libraries ship frozen with known unpatched CVEs** — OpenSSL
  1.1.1w, Samba 3.6.x, net-snmp 5.7.2, lighttpd 1.4.39, expat 2.0.1, libgcrypt
  1.5.1. OpenSSL is in the remote TLS path and is the highest-priority backport.
  (For reference, zlib 1.2.12 and curl 8.17.0 are already current, and avahi is
  patched.) These will be addressed by surgical ABI-preserving CVE backports or
  an ASUS-led version bump.

**Cannot fix in this tree (monitor ASUS):**
- The **auth / token / session core** and the web input filter live in
  closed-source blobs (`web_hook.o`, `priv_webapi.o`) that cannot be
  source-verified; the WiFi drivers are likewise closed. This is the dominant
  residual risk versus the physical-access-only goal. Mitigation: keep remote
  web admin disabled; every downstream sink is hardened regardless. Watch for
  ASUS firmware/blob updates.

**Dormant unless you enable AiCloud:**
- AiCloud is **off by default** (`RTCONFIG_WEBDAV` not built). Do **not** enable
  it without first fixing the predictable sharelink token, mod_webdav path
  traversal, and `df|grep` popen (`REAPER-FIXES.md` T6-T8).

**Lower-priority latent hardening** (bounded/unreachable today) and design
decisions (default admin credentials, mitigated by the forced first-boot QIS
password change) are also listed in `REAPER-FIXES.md`.

---

## 6. Install & recovery

1. Log in to the router web UI → **Administration → Firmware Upgrade**.
2. Upload **`RT-BE96U_3006_102.8_reaper_nand_squashfs.pkgtb`** — the firmware
   image. **Do not** flash the `..._loader.pkgtb` (that is recovery-only).
3. Let the router reboot. On first boot, complete QIS and **set a strong,
   non-default admin password** (this is the mitigation for the default-creds
   item).
4. **Recovery:** if a flash fails, use **ASUS Firmware Restoration** in rescue
   mode with the `..._loader.pkgtb`.

---

## 7. Build & image verification

Built with the RT-BE96U userspace toolchain (gcc-10.3, 32-bit ARM) via
`make rt-be96u`, `MAKE_EXIT=0`, "Done! Image 96813GW has been built".

| Artifact | SHA-256 |
|---|---|
| `RT-BE96U_3006_102.8_reaper_nand_squashfs.pkgtb` (flash this) | `fa95b1d417b1ef6b075281b5c435e39fa9a6cf9c3ced2ea4263f8069e7f4f5f5` |
| `RT-BE96U_3006_102.8_reaper_nand_squashfs_loader.pkgtb` (recovery) | `e0be733645272bd61291a29c0d1d694622b5a8bba65e30a349478b80eb04f165` |

> Status (v1.0): validated on the physical RT-BE96U — security hardening
> rounds 1–4 + latent T1–T4, the avahi CVE backport, both Hardware QoS
> engines (v1 global and v2 Classful, end-to-end on metal), and the Reaper
> UI at all page depths. Both HW QoS engines and the serve-time theme
> kill-switch (`reaper_inject=0`) are confirmed working on this image line.

---

## 8. Distribution & license

Reaper distributes its **GPL userspace modifications** (source + patches in the
lean repo). The proprietary Broadcom/ASUS/TrendMicro binary blobs are **not
redistributable** and are not published; see `README.proprietary` / the base
Asuswrt-Merlin license terms. Reaper is provided **as-is, with no warranty**;
run it understanding the residual risks in Section 5.
