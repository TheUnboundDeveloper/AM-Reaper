# RT-BE96U "Reaper" — Changelog

High-level history of the Reaper build. One entry per version, big changes only —
the exhaustive security detail is in [`REAPER-FIXES.md`](REAPER-FIXES.md) and the
per-release summary in [`RELEASE-NOTES.md`](RELEASE-NOTES.md).

All versions are the `RT-BE96U 3006.102.8_Reaper_v<X>` firmware line, built for the
ASUS RT-BE96U only, on the Asuswrt-Merlin 3006.102.8 base.

> **Metal-validation note:** every version listed as released was validated on the
> physical RT-BE96U. The newest line (v1.4.x — AI Advisor) is feature-complete and
> build-verified; its on-hardware validation is in progress. See `RELEASE-NOTES.md`
> for the current release's exact status.

---

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
- Single-model tree: RT-BE96U only; all sibling BE models stripped.
