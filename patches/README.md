# patches/

The complete **Reaper** series for the RT-BE96U (**350 patches, v1.0 → v2.2.2**), as `git format-patch` files generated on top of Asuswrt-Merlin **`3006.102.8-beta2`** (base commit `a7ebfa133a`). Apply them to a stock upstream checkout to reproduce the full Reaper source — security hardening, the de-cloud removals, all Hardware QoS engines, the Traffic Analyzer, the Reaper UI, and the optional AI Advisor.

## Apply

```bash
git clone https://github.com/RMerl/asuswrt-merlin.ng.git
cd asuswrt-merlin.ng
git checkout 3006.102.8-beta2

# git am --keep-cr is REQUIRED:
#  - --keep-cr: several third-party files (e.g. lltdc) have CRLF line endings, so
#    the patch context carries CR. Without --keep-cr, git strips it and the patch
#    fails to apply (at lltdc/src/qospktio.c).
#  - git am (not plain `patch`): 4 patches carry git binary payloads (fonts, logo,
#    USB ring sprite) that `patch` cannot apply.
git am --keep-cr /path/to/AM-Reaper/patches/*.patch
```

Verified: applying the full series with `git am --keep-cr` onto a clean `3006.102.8-beta2` checkout reproduces the Reaper source tree exactly (0 differences under `release/src/router`). Build per [`../docs/DEV-SETUP.md`](../docs/DEV-SETUP.md). Per-version history is in [`../docs/CHANGELOG.md`](../docs/CHANGELOG.md).

## What the series contains (350 patches, v1.0 → v2.2.2)

The filenames carry the summary; the full per-finding security mapping (CVE-class, severity) is in [`../docs/REAPER-FIXES.md`](../docs/REAPER-FIXES.md). Roughly, in order:

### v1.0 — hardening + QoS + UI baseline (`0001`–`0087`)
- `0001`–`0021` — **Hardening round 1** (IPsec/rc command injection, httpd pre-auth overflow, snmpd/nvparse/usb/shared memory safety, format strings, temp-file races, perms).
- `0022` — build branding (`BUILDREV=-reaper`).
- `0023`–`0024` — **Hardening round 2** (network-reachable ASUS daemons; Tier-3 defense-in-depth: infosvr, libovpn, libcodb, rstats, lanauth).
- `0025`–`0028` — **Hardware QoS v1** (`qos_type=10`): Runner PI2 AQM + shaper with the flow accelerator on; GUI selector; flow-cache flush fixes.
- `0029`–`0033` — **Hardening round 3** (pre-auth login decode, QoS apply gate, dnsmasq/inadyn/iptables config-injection, libcodb SQL identifiers, CAKE format fix).
- `0034`–`0065` — **Reaper UI + branding**: Smart Connect master toggle, REAPER banner/recolor passes, live-wired dashboard, shell architecture, AiMesh/Captive-Portal/Ookla theming, the HW-QoS activation fix (`qos_type` nvram length), on-device review rounds 1–2.
- `0066`–`0070` — **Hardening round 4** (self-review of Reaper-authored code), on-device review round 3, and the **mergeability refactor**: theme moved to a single httpd serve-time injection filter; stock pages/CSS reverted to pristine.
- `0071`–`0084` — Phase-B CSS de-inline completion, **avahi 0.8 CVE backport** (mDNS DoS), **latent buffer hardening T1–T4**, login-page theme, **Hardware QoS v2 — Classful** (`qos_type=11`), v1.0 UI/QoS polish.
- `0085` — **v1.0 pre-release audit fixes**: bound the QoS `ip_range_checker` `strncpy` sites, a HW-QoS Classful blank-bandwidth guard, minor UI polish.
- `0086` — **scheduled firmware-check fix**: enable `RTCONFIG_MERLINUPDATE`, `firmware_check_enable` default **0** (no outbound update traffic unless opted in; notification-only).
- `0087` — version bump to **`3006.102.8_Reaper_v1.0`**.

### v1.1 → v1.2 — de-cloud / attack-surface removal (`0088`–`0115`)
- `0088`–`0091` — remove **Amazon Alexa / Google Assistant**; keep IFTTT-referenced symbols compiled for the kept blobs; begin **AiProtection (Trend Micro `bwdpi` DPI)** removal.
- `0092`–`0096` — v1.1-beta1; inert `bwdpi` blob shims (no-DPI stubs, `amas_lib.o` stubs, `libbwdpi.so` wrapper, `CLIENT_DETAIL_INFO_TABLE` shmem-ABI pin) so the kept prebuilt blobs still link.
- `0097`–`0100` — QoS menu rename (**Adaptive QoS → Traffic Manager**), drop dead bwdpi tabs, dashboard label; v1.1-beta2.
- `0101`–`0104` — lighttpd → captive-portal-only payload; **remove AiCloud / WebDAV / CloudSync** (Phase 1.3); v1.1-beta3.
- `0105`–`0107` — **AiDisk de-wizard** (Phase 1.4), repoint entry points to USB File Sharing; v1.1-beta4.
- `0108`–`0109` — **remove the AAE / `mastiff` cloud tunnel**, restore the local Ookla Speedtest (Phase 1.5); v1.1-beta5.
- `0110`–`0115` — un-gate `libws.so` from the removed tunnel flag; serve `.woff2`/favicon; post-login dashboard landing; **v1.2** (drop beta label); disable the UU game-accelerator plugin; theme-inject only `.asp`/`.htm` (never CGI).

### v1.2.1 → v1.2.9 — polish, more removals, QoS v3/v4 (`0116`–`0132`)
- `0116`–`0129` — v1.2.1–v1.2.6 point releases: post-login landing fix; **remove the `asd` phone-home daemon** (keep `libasc`); hide dead surfaces left by removals; frame auto-grow; USB ring sprite; GUI theming sweeps; code-scan hardening + perf; a WPS-backhaul-BSS gate (and its revert); `qos_type` apply-gate hardening.
- `0130` — **v1.2.7**: remove the first-boot **QIS EULA / privacy-consent** surface (keep the AiMesh add-node wizard); SNMP token guard.
- `0131` — **v1.2.8 — Hardware QoS v3** (aggregate cap, guaranteed minimums, DSCP trust, live per-class stats).
- `0132` — **v1.2.9 — Hardware QoS v4** (per-class WRR weights + experimental L4S).

### v1.3 — Traffic Analyzer (`0133`–`0136`)
- `0133` — **v1.3.0**: Traffic Analyzer (`rtrafd` collector + native page: per-device/network/class history, top talkers, quota, WAN probe, RAM/JFFS/USB storage).
- `0134`–`0136` — v1.3.1 offload-accurate per-device/network (reads the Runner flow table), v1.3.2 endpoint fix, v1.3.3 1-second dual-cadence live view + poll selector.

### v1.4 — AI Advisor (`0137`–`0139`)
- `0137` — **v1.4.0**: AI Advisor — read-only LAN MCP server (`rmcpd`), off by default, LAN-only, arming-code gated.
- `0138` — **v1.4.1**: AI Advisor **Mode B** (optional USB key) + the clean **with/without-MCP two-build split** (`RTCONFIG_REAPER_MCP`).
- `0139` — **v1.4.2**: AI Advisor **TLS via the router's own httpd cert** (`/etc/cert.pem` through `mssl`, else plain HTTP) + **friendly SSIDs** (from the SDN profiles, not the internal onboarding IDs).

### v1.4.3 → v1.5.0a — security-review remediation, UI polish, exploit-mitigation, network diagnostics (`0140`–`0150`)
- `0140`–`0142` — **security-review remediation** of Reaper-introduced code (v1.4.3/v1.4.4), and **v1.4.5 exploit-mitigation build hardening** (FORTIFY + stack-protector-strong + PIE + full-RELRO on the Reaper daemons).
- `0143`–`0148` — UI polish and metal-test fixes (v1.4.6–v1.4.9a): i18n language packs for the Reaper pages, narrower rail + in-rail language selector, AiMesh backdrop, network-map USB icon fixes, Bandwidth Limiter on the QoS page.
- `0149` — **v1.5.0**: Network Diagnostics — the tcpdump Packet Capture tab + the AI Advisor active-diagnostics tier (ping/traceroute/DNS/netstat, opt-in, fixed-argument exec).
- `0150` — **v1.5.0a**: remove the bundled tcpdump Packet Capture; harden the AI Advisor diagnostics.

### v1.5.0b → v1.5.0d — live view, compliance, rebrand (`0151`–`0153`)
- `0151` — **v1.5.0b**: Traffic Analyzer "Live (200ms)" refresh mode (rtrafd base tick 1s → 200ms, work-time-paced); diag-aware AI Advisor `initialize` instructions (branch on the per-session diagnostics consent instead of a static "read-only" blurb).
- `0152` — **v1.5.0c**: compliance hygiene — SPDX `GPL-2.0-only` + copyright headers on the Reaper-authored source files, and the SIL OFL 1.1 text installed as `www/fonts/OFL.txt` so the Inter/Rajdhani font license ships in the image. No functional change.
- `0153` — **v1.5.0d**: de-ASUS rebrand (UI only) — the `REAPER1.png` wordmark banner replaces the logo in the header, the login/logout card, and the stock-page banner; the AiMesh node-card backdrop uses `RLogo.png` (and the `ASUSLogo.png` asset is removed); the "ASUS · Merlin · Reaper" rail wordmark becomes a live, themed, 24-hour router-time clock (reusing the stock `<% uptime(); %>` hook, offset-proof).

### v1.5.0e → v1.5.4 — reset-loop fix, boot efficiency, QoS v5 (`0154`–`0163`)
- `0154`–`0155` — **v1.5.0e**: never bounce the first-run gate pages (fixes the factory-reset
  UI redirect loop that looked like a brick); make the branch buildable from a clean checkout.
- `0156`–`0157` — **v1.5.2** boot-efficiency round 1: no httpd restart on USB mount, unblocked
  watchdog waits. (v1.5.1 was the GT-BE98 sibling-model GPL re-base — no RT-BE96U change.)
- `0158`–`0161` — **v1.5.3**: **Hardware QoS v5 download side** (WAN-ingress RX policer +
  downstream DSCP→WMM class lift), Traffic Analyzer Live tightened to 100 ms (matched pair),
  device-identity rows (name + "IP · MAC"), i18n strings.
- `0162`–`0163` — **v1.5.4**: QoS v5.1 policer burst/rate fixes from on-hardware tuning.

### v1.5.5 → v1.6.0 — first-boot wizard, Advisor tool, audit fixes, wireless page, hardening + i18n (`0164`–`0181`)
- `0164` — **v1.5.5**: unbypassable first-boot / factory-reset credentials wizard
  (`Reaper_FirstBoot.asp`), AI Advisor IP-pin retention, themed waiting overlay,
  self-updating internet status during boot.
- `0165` — **v1.5.6**: AI Advisor `get_wireless_stations` curated read tool.
- `0166`–`0171` — **v1.5.7** audit-fix rung (from a 34-agent adversarial code sweep):
  un-hidden wl driver errors in the System Log, Smart Connect band-bitmask indexing,
  `rtrafd` hot-path/rate fixes, `rmcpd` per-command time bounds + earlier cleanup arming,
  QoS mangle flush / port-forward / cfgsync / Advisor-CSS fixes.
- `0172`–`0175` — **v1.5.8**: the `Reaper_Wireless.asp` diagnostics page (radio snapshot,
  channel Lock/Unlock pin, exclusion-list visibility, on-demand channel-quality capture),
  `psc6g` duplicate-default fix, a collector build fix.
- `0176`–`0178` — **v1.5.9**: Traffic Analyzer wedge-proof live polling + stalled indicator +
  history auto-refresh; the app shell's master page scrollbar themed.
- `0179`–`0180` — **v1.5.9 wireless backfill**: the `Reaper_Wireless.asp` radio-unit ceiling raised
  to quad-band, and the dashboard made radio-count-driven (both keep tri-band RT-BE96U behavior;
  they ship in the RT-BE96U image and were folded onto the RT-BE96U branch during the v1.6.0 sync).
- `0181` — **v1.6.0**: hardening pass (`rtrafd` per-tick nvram-read caching + open-once WAN counters
  + ~1 Hz Live-table throttle, all ring-alloc NULL-checks, `rmcpd` `popen` fd/child-leak fix,
  `rmcp_client` / `lan_ifname` input validation, AI Advisor "Save settings" `http_id` + response
  check) plus the full 24-language UI translation (with the truncate/hover-tooltip overflow helper
  and a Reaper favicon on the Login/Logout tab).

### v1.6.1 → v1.6.6 — Channel-Quality Auto Scan, rchqd syslog trail, UI/i18n fixes, QoS download + Cake tuning (`0182`–`0190`)
- `0182`–`0183` — **v1.6.1**: Channel-Quality **Auto Scan** on the wireless diagnostics page
  (+ Clear button, passive `rchqd` monitor), then Auto Scan refinements (dedup-by-block,
  terminate-on-leave, progress display, landscape report, QoL).
- `0184` — **v1.6.2**: Auto Scan generalized to **all bands** (band selector) + noise-settle fix.
- `0185` — **v1.6.3**: `rchqd` degraded-event **syslog trail** (edge-triggered per radio,
  throttled; opt-in via the diagnostics page).
- `0186`–`0188` — **v1.6.4**: VPN nested-frame theme 404 fix + SPA palette sweep, SDN/MLO
  expand cut-off fix, tablet viewport pan; i18n sweep (`Reaper_FirstBoot` tokenized,
  `RFB_01`–`14` translated in all 25 dictionaries); audit fixes (`rchqd` JSON/syslog
  decoupling + state close-out + monotonic throttle + halved fork load, www ResizeObserver
  disconnect + width-grow measurement).
- `0189` — **v1.6.5**: QoS download — the policer applies **90% headroom** by design + cake
  shaper 90% consistency both directions.
- `0190` — **v1.6.6**: first-boot wizard **language selector** (carries into the UI) + QoS
  Cake jitter tuning (ack-filter on the upload cake, 50 ms rtt target both directions with
  the `qos_cake_rtt` override).

### v1.6.7 — Reaper Diagnostics (`0191`–`0194`)
- `0191` — **v1.6.7**: one-click **Reaper Diagnostics** (Administration &rsaquo; Diagnostics) — a
  sanitized diagnostic report via an authenticated CGI + a `/usr/sbin/reaper_diag` collector,
  with `RDIAG_*` strings in all 25 dictionaries.
- `0192`–`0194` — diag polish + first-metal-run fixes (download-hint wording, CJK full-stops,
  redaction/layout corrections from the on-hardware run).

### v1.7.0 → v1.7.1 — Gatekeeper + security remediation (`0195`–`0204`)
- `0195`–`0196` — **Gatekeeper** (v1.6.8): opt-in **default-deny device access control** (nvram
  `gk_*`, the `gkd` watcher, `rc/gatekeeper.c` iptables/ebtables enforcement, `Reaper_GK.asp` +
  the captive "awaiting approval" page); noMCP-build fix (CGI helpers moved out of the MCP ifdef).
- `0197`–`0198` — UI fixes (first-boot loop, View-List modal, WAN DNS-List clip) + the first-boot
  credential apply (`saveNvram;restart_chpass`).
- `0199`–`0200` — **v1.7.0**: Gatekeeper promoted to release + 5 shared UI/credential fixes;
  BE96U-canon chanlist-shim OBJS guard.
- `0201`–`0204` — **v1.7.1**: security-remediation batch (Gatekeeper hardening — CSRF, MAC
  validation, device-table TTL eviction, self-heal throttle) + the **Network Map** client-status
  panel horizontal-scroll fix (widened box in `NM_style.css`).

### v1.7.2 → v1.7.4 — AiMesh onboarding, UI/i18n, Gatekeeper reliability (`0205`–`0211`)
- `0205`–`0209` — **v1.7.2**: AiMesh node onboarding restored (factory `x_Setting`/`w_Setting`
  back to stock so a fresh node beacons; QIS stays retired at the httpd layer), static-DHCP
  dropdown clip fix, stock-theme-flash pre-paint, full menu + page **translation pass** (24
  languages), version bump.
- `0210` — **v1.7.3**: **Gatekeeper reliability** — no admin lockout (turn-on grandfathers
  ARP + DHCP leases + the named-client list; the firewall always leaves the HTTPS admin page
  reachable) + dependable cold-boot arming (run-time LAN resolution, deferred until the bridge
  is up) + an "Arming" / "Not enforcing" status stamp.
- `0211` — **v1.7.4**: static-DHCP client picker re-anchored to its input and opened **upward**
  with an inner scroll; **Wireless/DHCP** theme-flash eliminated (framed page held dark until themed).

### v1.7.5 → v1.7.7 — libpasswd injection fix, VPN theme flash, AURA carousel (`0212`–`0215`)
- `0212`–`0213` — **v1.7.5**: **command-injection fix** — `libpasswd`'s
  `asus_libpasswd_openssl_crypt()` was a byte-identical copy of the C6 `openssl passwd`
  `popen()` bug (built the shell string with the user-supplied password + salt, reached from
  the HTTP basic-auth and lighttpd WebDAV/SMB basic-auth paths on the libc `crypt()==NULL`
  fallback, running as root). Replaced `popen()` with an explicit-argv fork/execvp/pipe helper —
  no shell, no behavioral change. Reported to ASUS PSIRT as the C6 twin (case 1006563); version bump.
- `0214` — **v1.7.6**: fix the **VPN Client+Server theme ping-pong** — two competing iframe
  resizers on the nested VPN SPA (reaper's grow vs. the SPA's own `resize_iframe_height`) fought
  each other into an endless-load reflow; the reaper-side ResizeObserver is removed and sizing
  deferred to the SPA. Firmware-wide (both VPN wrapper pages).
- `0215` — **v1.7.7**: VPN Client+Server **anti-flash veil** (hold the nested `#vpn{c,s}_iframe`
  hidden over `#0f0f12` until `reaper_content.css` loads inside the SPA — kills the split-second
  stock-blue flash on VPN Client PPTP/L2TP) + the **Network Map AURA/LEDG** scheme-carousel
  horizontal-scrollbar fix (`.setting_scheme` `overflow-x` auto→hidden; the carousel pages via
  its arrow controls, not native scroll).

### v1.7.8 — SMB3/Samba 4, SNMPv3-only + SFTP, USB-hub & MLO dashboard fixes (`0216`–`0226`)
- `0216` — **v1.7.7a**: **Wireless Log** page — add **GT-BE98** to the quad-band radio branch
  (`Main_WStatus_Content.asp`) so its four radios (`wl0=5 GHz-1, wl1=5 GHz-2, wl2=6 GHz, wl3=2.4 GHz`)
  map correctly instead of falling through the tri-band `else`.
- `0217` — **QoS download policer default OFF** (`qos_ipolicer` `1` → `0` in `defaults.c`): a policer
  drops rather than delays, so the WAN-ingress download cap is now opt-in (it clipped loss-sensitive
  real-time UDP). Fresh nvram only.
- `0218`–`0219` — **QoS UI + i18n**: warn on the download-cap toggle (`RQOS_117`) that it is off by
  default and, being a policer, can add packet loss to real-time video/voice; translated to all 24
  other languages (122-key lockstep).
- `0220` — **Reaper dash MLO fix**: the MWL SSID resolver now reads **all** `apmX_dut_list` entries
  (ORs the band bits) so enabling MLO no longer pushes 2.4 GHz out of slot 0 and shows a raw hex
  onboarding ID instead of the SSID on its tile.
- `0221` — **SNMP v3-only + SFTP default**: lock out SNMPv1/v2c (cleartext community strings removed
  from the daemon + UI), require authenticated **SNMPv3** (default SHA + AES); add a **File transfer
  method** selector on the FTP page with **SFTP pre-selected** (links to the SSH page, no
  auto-enable). Uses the in-image dropbear SFTP path.
- `0222` — **openssh-sftp package**: bundle an `sftp-server` binary (OpenSSH 9.8p1, sftp-server target
  only) so SFTP works over the existing dropbear SSH server.
- `0223` — **net-snmp 5.7.2 → 5.9.4** (CVE hygiene; SNMPv3 already worked).
- `0224` — **Reaper dash USB fix**: count hub sub-devices per physical port so a **USB hub** reads as
  connected (was "empty" because `usb_pathN` is blank for a hub) and multi-device ports show a count.
- `0225` — **Samba 4.15.13** (real **SMB3 / SMB3.1.1** with GnuTLS AES-GCM/CCM encryption) replacing
  Samba 3.6.25 (SMB2 max), **RT-BE96U only**; new **"SMBv3 (encrypted)"** option (`smbd_protocol=3` =
  SMB3-only + required encryption).
- `0226` — **v1.7.8**: version bump `EXTENDNO` → `Reaper_v1.7.8`.

### v1.7.9 — VPN buttons restored, reliable speed test, 2.4 GHz name fix (`0227`–`0230`)
- `0227`–`0229` — dashboard 2.4-GHz SSID when the band is excluded from MLO (fronthaul-SSID
  fallback), device-glyph recolor **scoped** to the Network Map View List (fixes the VPN client
  page's red-block buttons), and a single silent speed-test auto-retry on a transient cold-start
  failure.
- `0230` — version bump `EXTENDNO` → `Reaper_v1.7.9`.

### v1.8.0a — Reaper Warden threat/geo firewall + hardening pass + Samba CVE backport (`0231`–`0234`)
- `0231` — **Reaper Warden**: an optional, default-OFF `ipset` firewall layer — threat feeds
  (FireHOL/Feodo/Spamhaus DROP/DShield), country block/allow by CIDR, manual block/allow lists,
  strict anti-lockout, JFFS-cached and auto-re-arming.
- `0232`–`0233` — Batch-A verified audit hardening (format-string, VPN-Fusion / WireGuard /
  Wi-Fi-scan shell-injection, web-server path check, login open-redirect guard, Gatekeeper-script
  input sanitizing) + an `rwarden.c` build fix.
- `0234` — **Samba 4.15.13a**: backport CVE-2025-9640 (`streams_xattr` uninitialized-memory
  disclosure) + version suffix. *(RT-BE96U — the model on Samba 4.)*

### v1.8.1 — Gatekeeper anti-lockout + boot/teardown logging (`0235`–`0240`)
- `0235`–`0238` — boot efficiency + a syslog trail: skip the phy power-cycle + 10 s wait on
  reboot, log `start_services`/`stop_services` phase boundaries and the LAN boot/teardown
  boundaries + Warden feed-fetch failures, and an IPv6 status-icon fix on native DHCPv6.
- `0239` — version bump `EXTENDNO` → `Reaper_v1.8.1`.
- `0240` — Gatekeeper **re-grandfathers** all known devices on every enable (not just those
  talking at that instant), so a sleeping device can't be stranded on a later toggle.

### v1.8.2 → v1.8.3 — audit-remediation arc: high-impact fixes + batches (`0241`–`0243`)
- `0241` — **v1.8.2**: the three highest-impact findings from the 73-finding adversarial audit
  (IPsec profile-name → root shell, port-forward field splicing a firewall rule, a file-read
  error path freeing the wrong pointer) + a new IPv6 dashboard indicator; version bump.
- `0242`–`0243` — **v1.8.3**: fix the v1.8.2 dashboard-render regression (hoist `v6Up()` to the
  right scope; IPv6 icon also lights on a working gateway) + audit batches B/C/D/E (Warden
  anti-lockout subnet + fail-safe blocklist swap, login-redirect exclusions, i18n DE/FR
  download-cap wording, Samba build-stamp keyed to patch contents).

### v1.8.4 → v1.8.6 — latent + low-severity audit batches, independent-review sign-off (`0244`–`0245`)
- `0244` — records the shipped **v1.8.4** (12 latent issues), **v1.8.5** (18 low-severity items),
  and **v1.8.6** (two independent adversarial reviews found no live bugs; five defense-in-depth
  tightenings closed) audit-remediation rungs.
- `0245` — BE96U dashboard: 6 GHz made conditional (`HAS_6G`) for cross-model correctness.

### v1.8.6a → v1.8.6d — fan-out fixes: i18n quote-safety, inject buffering, GT-BE98 gate (`0246`–`0250`)
- `0246`–`0247` — **v1.8.6a/b**: www i18n quote-safety — dict tokens must not sit inside single
  quotes; BE96U-only follow-up fix.
- `0248` — `reaper_diag`: replace a field-observed bridge-id example.
- `0249` — **v1.8.6c**: `httpd`/`reaper_inject` buffer-then-inject (fixes stock-page garble).
- `0250` — **v1.8.6d**: restore the GT-BE98 sysinfo quad-band gate into shared canon (clobber-proof).

### v1.8.7 — Reaper Warden: IPv6 dual-stack + per-country block stats (`0251`)
- `0251` — parallel IPv6 threat/geo stack (v6 feeds, chains, CIDR validation, anti-lockout) + a
  live **Blocked-hits** tile and **Top blocked countries** card; full Warden translation.

### v1.8.8 — Warden LAN-lockout fixes + the `rwatch` health watchdog (`0252`)
- `0252` — filter reserved/private ranges from every ingested feed, rebuild chain order so
  anti-lockout rules always precede any drop, per-set non-empty `ipset save` (persistence now
  actually works), plus the new default-on **`rwatch`** health probe and idempotent HW-QoS re-apply.

### v1.8.9 — WireGuard peer list: usable buttons, unclipped dialog (`0253`)
- `0253` — restore the VPN-Server WireGuard per-peer edit/QR/trash glyphs (a button-recolor rule
  had painted them solid red) and refit the peer-edit dialog when a section expands.

### v1.9.0 → v1.9.1 — Device Identity Manager (`0254`–`0255`)
- `0254` — **v1.9.0** (Rung A): a new **Devices** page correlating name / DHCP reservation /
  Gatekeeper state / live presence **per MAC** — inline rename, pool-aware Pin dialog, attention
  card, filter/search, per-device 24 h traffic. No new store; read-modify-write preserves each record.
- `0255` — **v1.9.1** (Rung B): a **Storage** page to direct the opt-in history datasets to
  RAM / JFFS / USB (per-dataset toggles); the Traffic Analyzer selector becomes a pointer to it.

### v1.9.2 → v1.9.4 — Devices page: MLO awareness + accurate link classification (`0256`–`0258`)
- `0256` — **v1.9.2**: label MLO per-link addresses "MLO · <band>" (stop flagging them as
  unnamed/randomized) + an offline-device Connection-cell escaping fix.
- `0257` — **v1.9.3**: fold a Wi-Fi 7 MLO client's per-band links into one device row via the
  driver's link-to-device mapping.
- `0258` — **v1.9.4**: classify wired vs wireless (and the band) from the LAN bridge forwarding
  table instead of the Wi-Fi association list, which intermittently omits Wi-Fi 7 / 6 GHz / MLO stations.

### v1.9.5 — First-boot: default credentials can no longer slip through (`0259`)
- `0259` — a factory-fresh box landing on the Reaper dashboard is now forced through the
  credential-change step (server-side post-login redirect + an early dashboard guard); fires only
  while credentials are still default.

### v1.9.6 — Dashboard readability, Warden country picker, status at a glance (`0260`)
- `0260` — Security Posture card gains Gatekeeper + Warden rows, the Warden country selector
  becomes a searchable checkbox grid, USB tiles re-poll for ~90 s after boot, brighter client
  list, and a truthful System-Info Features row.

### v1.9.7 — Traffic Analyzer accuracy (per-network + the router's own traffic) (`0261`)
- `0261` — attribute each flow from its own LAN-side interface and surface locally-terminated
  router traffic under a new **"Router"** row, so By-Network + Router + clients reconcile with the
  WAN chart; the dashboard **View List** button now opens the full Devices page and the client list
  grows to fill its card.

### v1.9.8 — Add-on menu fix, Warden persistence disclosure, change auditing, full localization (`0262`)
- `0262` — external add-on menu links (e.g. scMerlin Help & Support) open in a new tab instead of
  redirecting the frame; a Warden banner when `/jffs` is off/read-only warns that feed-cache
  persistence (cross-reboot / no-internet-boot protection) is unavailable; structured change-audit
  syslog for Gatekeeper / Wireless-monitor / Devices-Storage actions; and the final 219 Devices /
  Storage / Warden strings translated across all 24 languages.

### v1.9.9 → v1.9.9a — Wireless Diagnostics robustness (`0263`–`0264`)
- `0263` — **v1.9.9**: PID-aware Auto-Scan / Targeted-Capture token reclaim (a stale busy-marker no
  longer disables Start for minutes), the "Apply Best Channel" confirmation names the real band, and
  quad-band models label their two 5 GHz radios distinctly.
- `0264` — **v1.9.9a**: the Unlock button confirms before the ~20 s radio restart, and Auto Scan
  survives scanning the band your own browser is on instead of stopping after one channel.

### v1.9.9b → v1.9.9d — All-bands Professional wireless page (`0265`–`0267`)
- `0265` — **v1.9.9b**: a single Professional page laying out 2.4 / 5 / 6 GHz side by side with one
  **Apply all** (only changed settings written; all radios restart once).
- `0266` — **v1.9.9c**: drop the radio-level Hide SSID + AP Isolation switches from this page (SDN
  governs the real SSID; those switches only ever affected an internal interface here).
- `0267` — **v1.9.9d**: left-justify the layout to fill width with a capped label column.

### v2.0.0 — Security-hardening milestone: two full code audits (`0268`–`0271`)
- `0268` — release audit fixes: version bump, Warden hardware flow-cache flush on rule-apply so a
  newly blocked address drops immediately, and JSON-CGI content-type + escaping hardening.
- `0269` — inherited ASUS/Merlin audit (AUDIT-2) fixes in the stock userspace: stored-XSS
  neutralization of a device-supplied DHCP hostname across admin views, a USB volume-label root
  command-injection fix at auto-mount, and an IPsec-profile CGI stack-overflow bound.
- `0270` — security-hardening batch (AUDIT-1 §2 + AUDIT-2 follow-ups): config-DB value escaping,
  `http_id`-guarded diag/warden CGIs, VPN-page buffer bounding + config-upload nvram-write
  restriction, the device-name HTML-encode sweep across the remaining pages, and internal-TLS
  server-certificate verification.
- `0271` — shell portability hygiene (POSIX `.` for `source`, `[ = ]` for `[ == ]`) in the generated
  and shipped on-router scripts.

### v2.0.1 → v2.0.2 — de-cloud completion + the Samba 4 file server working (`0272`–`0280`)
- `0272`–`0274` — **v2.0.1**: remove the ASUS **AWS-IoT** phone-home + **ACCOUNT_BINDING** cloud surface
  (a config-gen had silently re-added it after the earlier phone-home cleanup); keep `is_account_bound`
  linkable for the kept blobs; gate the benign `blog_get_dstentry_by_id` kernel debug flood at source.
- `0275`–`0277` — **v2.0.1** Samba 4: fix the file server that never started (private libs off the loader
  path + missing runtime dirs + guest-map), label the SMB-protocol dropdown for Samba 4 (drop SMB1), and
  the first `smbpasswd -c /etc/smb.conf` account-enrollment fix.
- `0278`–`0280` — **v2.0.2**: complete the smbpasswd-path account-enrollment fix + clean share names + a
  GUI login prompt; skip the 11 s `stop_lan` client-release wait on upgrade reboots too; make the `rchqd`
  "degraded" threshold nvram-tunable.

### v2.0.3 → v2.0.6 — router-generated WiFiPro, secure defaults, QoS Diagnostics, Connections (`0281`–`0284`)
- `0281` — **v2.0.3**: the all-bands `Reaper_WiFiPro` page is router-generated (per-radio columns from
  `wl_nband_info`, dual-band 5 GHz-1/-2 disambiguation, compact centered layout).
- `0282` — **v2.0.4**: secure factory-reset defaults — **WPS off** (`wps_enable`/`wps_enable_x=0`) + **UPnP
  master off** (`upnp_enable=0`); audit confirmed everything else unneeded already off or compiled out.
- `0283` — **v2.0.5**: **Hardware QoS Diagnostics** (`Reaper_QoSDiag.asp`) — live per-queue
  occupancy/drops/estimated-delay + scheduler from the Runner/XRDP `egress_tm` via bdmf-shell; new
  auth-gated `do_reaper_qdiag.cgi`.
- `0284` — **v2.0.6**: **Connections / Flow Explorer** (`Reaper_Conn.asp`) — live per-flow HW-vs-CPU view
  from `/proc/fcache/nflist` via `do_reaper_conn.cgi`; true connection age via an `rtrafd` first-seen tracker.

### v2.0.7 → v2.1.0 — QoS-Diag reliability, dropdown fix, i18n, pre-release hardening (`0285`–`0289`)
- `0285` — **v2.0.7**: QoS Diagnostics reliability — `do_reaper_qdiag.cgi` calls `bdmf_shell` directly via
  the boot-written `/var/bdmf_sh_id` (digit-validated) instead of the untracked `bs` alias; page rate/drop
  deltas made 32-bit-counter-wrap-aware.
- `0286`–`0287` — **v2.0.8**: QoS Diagnostics port-selector rebuilt only when the port list changes (was
  closing the dropdown every poll tick); dictionary text — Wireless tab → **Wireless Quality**, `RDEV_02`
  "Network legible" → **"Network Ledger"**, and the `RWAC_1..36` string set (dormant; reserved for the
  shelved Wi-Fi Accelerator page on branch `accel-experiment`).
- `0288` — **i18n completeness pass**: tokenize the three pages that shipped hardcoded-English
  (`Reaper_Conn`, `Reaper_QoSDiag`, the WiFiPro option words + Wireless printable report) — 132 new dict
  tokens translated across all 25 languages; dicts lockstep at 6155. Localization only.
- `0289` — **v2.1.0**: pre-release code-review hardening batch (six-agent audit; no critical/high) —
  JSON-escape parity (qdiag / band / `rmcp_client`), single-flighted `/proc/fcache/nflist` read, Wireless
  status CSRF token, `gk_baseline_snapshot` lock, the GDX/FPM `/proc` probes made opt-in (`rwatch_gdx`),
  plus dead-code removal and a PII-comment scrub.

### v2.1.1 — localization, hardening, UI fixes (`0290`)
- `0290` — **v2.1.1**: Tier-3 CGI error-string localization (RDEVE_/RADVE_ keys → dict), structural
  `rmcpd` secret-redaction + truncation-to-valid-JSON, `esc()` defense-in-depth on three pages, the
  `rwarden` feed load switched to a single `ipset restore` batch, three UI viewport fixes + a "QoS
  Class" column rename, and a Channel-Lock confirmation dialog.

### v2.1.2 — Asuswrt-Merlin 3006.102.8 carry-forward (`0291`–`0310`)
Upstream fixes cherry-picked from the final Merlin 3006.102.8 / 3006.102.8_2 releases. **These 19
patches (`0291`–`0309`) retain their original Asuswrt-Merlin authorship** (Eric Sauvageau, dave14305,
et al.) rather than the Reaper identity — they are upstream work, carried forward honestly.
- `0291` — OpenVPN updated to **2.7.5** (the 2.7 line; deprecated server options removed).
- `0292`–`0293` — dropbear → **2026.94**.
- `0294`–`0296` — miniupnpd → **2.3.10-g91eeeae**; default `upnp_ssdp_interval` 900 s.
- `0297` — strongswan build-recipe sync (fixes a missing executable).
- `0298`–`0301` — webui: drop obsolete USB-modem tweak; Traffic Analyzer no longer tied to the DPI
  engine; client list re-render replaced with an incremental DOM diff; DHCP export works on iOS.
- `0302`–`0307` — IPv6 prefix handling: clamp delegated prefix to /64 where appropriate, correct the
  LAN IPv6 prefix-length reporting, rework the user-defined IPv6 WAN prefix.
- `0308`–`0309` — webui/rc: restart mastiff when toggling the Asusnat tunnel; DDNS sets the IPv6 flag.
- `0310` — **v2.1.2**: version bump (Reaper-authored).

> **Reproduction is CI-enforced.** [`../.github/workflows/verify-provenance.yml`](../.github/workflows/verify-provenance.yml)
> applies this series onto a fresh `a7ebfa133a` and asserts, per release, that `git rev-parse
> HEAD:release/src/router` equals the tree hash in [`../provenance/manifest.json`](../provenance/manifest.json).
> The `0290`–`0310` checkpoints were validated to reproduce `3ae0d914…` (v2.1.1) and `b2c357fa…`
> (v2.1.2); see [`../docs/BUILD-PROVENANCE.md`](../docs/BUILD-PROVENANCE.md).

> **Model scope:** the v1.8.7 → v2.0.x rungs above were developed + shipped RT-BE96U-first; the
> RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro siblings have since been brought to the current **v2.1.9** on their
> own per-model branches (built + shipped, both variants, all passing the verify gate — 19 checks since v2.1.7). This
> published series is the RT-BE96U line; the siblings build from the same shared source via
> `port_sibling_v2` (full-diff shared sync + per-model identity overlay + a dict lockstep sync).

## Notes

- **Documentation commits are intentionally absent** — the docs ship in this repo's [`docs/`](../docs/) instead of as source patches, and doc hunks are stripped from mixed commits. The series is numbered sequentially with no gaps.
- **The "BE96U-only" strip is not a patch here.** Making the tree single-model (removing the other BE sibling models' artifacts) was a large mechanical deletion (~5,650 files). It is **optional** — `make rt-be96u` builds fine from the full upstream tree — so it's omitted.
- Regenerated for **v1.6.6** (2026-07-19) from the full commit stack; author identity normalized to `reaper <theunbounddeveloper@outlook.com>`; verified to reproduce the source tree exactly via `git am --keep-cr` onto a fresh `a7ebfa133a` worktree (matching `release/src/router` tree hash).
- Extended through **v1.7.7** (2026-07-24): patches `0191`–`0215` (v1.6.7 → v1.7.7) appended from the same commit stack with the same author normalization. Re-run the full `git am --keep-cr` reproduce-check before a public release.
- Extended through **v1.7.8** (2026-07-25): patches `0216`–`0226` appended from commit `a8d1569017` (the v1.7.7 tip == `0215`) through the v1.7.8 version-bump HEAD, same author normalization and message scrub. Verified `git am --keep-cr` clean onto an `a8d1569017` worktree; the only reproduce-check delta is three vendored `openssh-sftp` documentation files (`README.md`, `SECURITY.md`, `.github/ci-status.md`) intentionally stripped by the `*.md` docs/meta exclusion — no source/code file differs.
- Extended through **v1.9.7** (2026-07-30): patches `0227`–`0261` (v1.7.9 → v1.9.7) appended from the same commit stack with the same author normalization and message scrub. From **v1.8.7** onward these rungs shipped **RT-BE96U-only** (siblings owed). Re-run the full `git am --keep-cr` reproduce-check before a public release.
- Extended through **v2.0.0** (2026-08-01): patches `0262`–`0271` (v1.9.8 → v2.0.0) appended from the v1.9.7 tip (`2f84abb9`) through the v2.0.0 tip, same author normalization and message scrub (none needed — author already normalized, no build-path strings). Verified `git am --keep-cr` clean onto a fresh worktree at the v1.9.7 tip with a zero `release/src/router` diff vs the v2.0.0 tip. Still **RT-BE96U-only** (siblings owed).
- Extended through **v2.1.0** (2026-08-02): patches `0272`–`0289` (v2.0.1 → v2.1.0) appended from the v2.0.0 tip through the v2.1.0 tip (commit `57fed00617`), same author normalization and message scrub, doc hunks excluded. The published series stays the **RT-BE96U** line; the four siblings were then ported to v2.1.0 on their own per-model branches (via `port_sibling_v2` + a dict lockstep sync) and built + shipped, all 17/17 — GT-BE98 Pro converted SAMBA36X→SAMBA4 in the process.
- Extended through **v2.1.2** (2026-08-03): patch `0290` (v2.1.1, Reaper-authored) + patches `0291`–`0310` (the Merlin 3006.102.8 carry-forward — **19 upstream commits keep their original authorship**, plus the v2.1.2 version bump). **Reproduce-check: verified.** Applying `0290` onto the v2.1.0 tip yields `release/src/router` == `3ae0d914…` (v2.1.1) and the full `0291`–`0310` yields `b2c357fa…` (v2.1.2), matching [`../provenance/manifest.json`](../provenance/manifest.json). This is now enforced on every CI run by [`../.github/workflows/verify-provenance.yml`](../.github/workflows/verify-provenance.yml), which reproduces each release's tree from `a7ebfa133a`. RT-BE96U line; the v2.1.1/v2.1.2 sibling fan-out is owed.
- Extended through **v2.1.5** (2026-08-04): patch `0311` (apostrophe-XSS hardening) + `0312`–`0318` (v2.1.3 → v2.1.4) + `0319`–`0322` (v2.1.5) appended with the same author normalization and doc-hunk exclusion; the provenance manifest was updated and CI-verified at **322 patches**.
- Extended through **v2.2.2** (2026-08-06): patches `0323`–`0350` (v2.1.6 → v2.2.2) appended from the v2.1.5 tip (`780803a648` == `0322`) through the v2.2.2 tip (`f2eed0a655`), same author normalization and doc-hunk exclusion (PII scan clean; all `From:` normalized to `reaper <theunbounddeveloper@outlook.com>`). Covers the v2.1.6 update-check/IPv6/watchdog fixes, the v2.1.7 device-name unification + rtrafd flash-persistence + USB disk panel, the v2.1.8 WAN-MTU rollback, the v2.1.9 code-audit hardening, the v2.2.0 first-boot/Gatekeeper/de-cloud batch, the v2.2.1 field-fix batch, and **v2.2.2** (per-device connection-health metrics + analytics export). **Series is contiguous, no gaps (0001–0350).** Published series is the **RT-BE96U** line; the v2.1.6 → v2.2.2 sibling fan-out is owed, as is the `git am --keep-cr` reproduce-check + provenance-manifest update before a public release.
