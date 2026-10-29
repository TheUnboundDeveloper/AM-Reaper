# RT-BE Series "Reaper" — Backlog

> **Doc status:** current as of **v3.6.2** · 2026-10-28 <!--@stamp-->

What is left to do, one or two lines per item, grouped by area. Status where known: **[owed]** (must be done), **[blocked]** (external cause), **[shelved]** / **[deferred]** (deliberately set aside),
**[watch]** (not a defect today; a guard to keep), **[needs data]** (waiting on a capture or report),
**[awaiting field]** (fixed; closes when a field tester confirms on the named image).

**Priority** by impact on user-facing function: **[P1]** core function broken or at risk ·
**[P2]** degraded function, meaningful annoyance, or privacy exposure · **[P3]** cosmetic, polish,
internal quality, or deferred by decision.

> This file only *identifies* each item. The full record behind it — evidence, code references,
> hypotheses ranked, what to capture next — lives in the maintainer's private notes, one file per
> item, named after each entry as `↳ notes: <file>`. Applied security fixes are tracked in
> [`REAPER-FIXES.md`](REAPER-FIXES.md); the per-version history in [`CHANGELOG.md`](CHANGELOG.md).
> **Completed items are not kept here** — when something ships it is recorded in the changelog and
> dropped from this file. The per-pass change log of this file lives in the private notes too
> (`HISTORY.md`).

---

## Contents

- [Waiting on field response](#waiting-on-field-response)
- [Open bugs / under investigation](#open-bugs--under-investigation)
- [UI / UX polish](#ui--ux-polish)
- [Potential features to add](#potential-features-to-add)
- [Documentation](#documentation)
- [Code quality / deferred (with reason)](#code-quality--deferred-with-reason)
- [Reported, investigated, closed as working-as-designed
  (#reported-investigated-closed-as-working-as-designed)
- [Blocked by closed-source components — for ASUS / Broadcom
  (#blocked-by-closed-source-components--for-asus--broadcom)

---

## Waiting on field response

*Solved and shipped in a cut or a successful test build; waiting on the reporter. One line each,
highest priority first - what was fixed and what to ask the tester for is in the notes. A "still broken"
answer moves the item back to Open bugs.*

- **[P1] RT-BE86U: 5 GHz radio down after a Guest Network Pro save (live Wi-Fi driver reload)**
  ↳ notes: `be86u-5ghz-driver-reload.md`
- **[P1] WAN 802.1Q switch did nothing on GT-BE98 (rebooted, came back off)**
  ↳ notes: `wan-vlan-mswan.md`
- **[P2] Reaper pages: settings written into page scripts without escaping**
  ↳ notes: `nvram-get-js-escaping.md`
- **[P2] firewall-start "not honoured": custom scripts kept no trace of failing**
  ↳ notes: `custom-script-output.md`
- **[P2] Translated labels wrap, spill, or push past their space** ↳ notes: `i18n-fit.md`
- **[P2] Browsers kept old pages after a flash or a setting change (cache bust)**
  ↳ notes: `httpd-cache-bust.md`
- **[P2] Wallguard: removable built-in lists, your own sources, API sources**
  ↳ notes: `wallguard-sources.md`
- **[P2] Bastion tools independent: Dreadwatch no longer needs Warden**
  ↳ notes: `bastion-independent.md`
- **[P2] Header bar truncates English at 1080p** ↳ notes: `header-chip-truncation.md`
- **[P2] Backups: the DDNS hostname lost, and the settings file blind to the newer tools**
  ↳ notes: `backup-coverage.md`
- **[P2] Doubled menu after a language switch (the dashboard inside the settings frame)**
  ↳ notes: `doubled-menu-language-switch.md`
- **[P2] DHCP manual assignment: device names gone from the Host Name column**
  ↳ notes: `dhcp-reservation-names.md`
- **[P3] The Warden menu is Bastion** ↳ notes: `bastion-menu.md`
- **[P3] System Log: lines are not wrapped** ↳ notes: `system-log-filter.md`
- **[P3] Wireless Log: one box per network** ↳ notes: `wireless-log-networks.md`
- **[P3] Wireless Log: client rows run past the page edge** ↳ notes: `wireless-log-overflow.md`
- **[P3] Dreadwatch: removable built-in lists, your own sources, API sources**
  ↳ notes: `dreadwatch-custom-feeds.md`
- **[P3] Wallguard / Dreadwatch: an API key inside the source address (`$APIkey`)**
  ↳ notes: `wallguard-sources.md`
- **[P3] Wallguard: abuse.ch templates in "Add a source"** ↳ notes: `wallguard-sources.md`

## Open bugs / under investigation

*Not fixed yet — work still to start or finish.*

- **[P2] AiMesh: the preferred uplink node is ignored** (field report, BQ16, v3.5.0) — a node set
  to prefer one node joins another; no Reaper change on that path found in the code.
  **[needs data]** ↳ notes: `aimesh-preferred-uplink.md`
- **[P3] Review 2026-10-24: the owner-only decisions and the merges that would change behaviour**
  (adversarial and quality agents over the whole pending delta) — decide: the hidden-input key lists
  (Q-C1-11), the Wallguard / Encrypted DNS look on the kit stylesheet (Q-C2-12 CSS), the ten stock rail
  glyphs and the firewall rail badge (Q-C2-8), refusing an all-zero WAN MAC (Q-C1-6), the `http_enable`
  default (S-B-1), the Wireless Log 5 s default; merges left because they change behaviour: one request
  helper with one timeout (Q-C1-7), the mask checks (Q-C1-6), the other sortable tables and the QoS /
  firewall address rules (Q-C2-11). **[all security, correctness and performance items in canon for
  _r36 2026-10-25; the flash items (comment strip, 82 unused tokens, kit helpers + 33 shared style
  rules, Wallguard / Encrypted DNS closures) and the `vts_rulelist` bench (JFFS-stored, kept whole) done the
  same night, unbuilt]** ↳ notes: `review-2026-10-24.md`
- **[P2] AI Advisor arming code ord and lockout move to reset-proof `/data/reaper/advisor/`.
  **[plan written 2026-10-19, replaces the WPS-button plan; not scheduled]**
  ↳ notes: `advisor-arming-code-admin-reset.md`
- **[P2] Add Packet Loss to connection tab** — Investigate if packet loss can be recorded or
  monitored on the connections tab by connection. No per-flow counter exists (hardware-forwarded
  flows); feasible only as an on-demand measure for the selected connection, TCP only.
  **[researched 2026-10-18; not scheduled]** ↳ notes: `conn-packet-loss.md`
- **[P2] Research no PIN point** - Look into setting a new pin point or fully diverging from
  a PIN build.
  **[options written 2026-10-18; owner decision]** ↳ notes: `pin-strategy.md`
- **[P2] LAN › DHCP: the manually assigned (bound) devices list is missing** (field, reported again 2026-10-26) — the
  list renders on the owner's box (same format as stock); the user's case is not reproduced yet. **[not started; need the
  user's screenshot + diag]**
  ↳ notes: `dhcp-manual-list-missing.md`
- **[P2] Russian: switching the GUI to Russian changes and duplicates parts of it; word spacing** (field, Russian users,
  2026-10-26) — the packs are in step (checked); long words: see the next entry; open: screenshots, the language switch.
  **[layout part built 2026-10-26 (below); rest not started]** ↳ notes: `russian-ui-layout.md`
- **[P2] Wi-Fi start-up script fixes from GPL 40585** (Merlin review, 2026-10-26) — hndnvram.sh stops stacking a second
  defaults mount (can swallow nvram commits), quoting, taskset hex; Merlin: an ASUS GPL change he has no details on.
  **[owner investigating; not carried]** ↳ notes: `merlin-40585-review-2026-10-26.md`
- **[P2] Merge the whole 102_40585 GPL (rebase onto Merlin main)** (2026-10-26) — Merlin: pieces of a GPL are not
  sustainable; brings AiMesh, the Ookla rework + quota (decide). Trial merge: ~200 real code hunks in ~30 files, the rest
  mechanical; est. 85-90% complete with every fix kept, 60-70% clean first image. **[scheduled after the open bugs;
  plan: bulk, code, checks, metal rungs]** ↳ notes: `merlin-40585-review-2026-10-26.md`
- **[P3] HW QoS inert behind an ISP/IPTV profile** — the WAN name is the virtual device there; take the port from
  `wan_if_eth()` as Merlin f5334a33d23 does (the mswan half needs 40585). **[not started]** ↳ notes: `merlin-40585-review-2026-10-26.md`
- **[P3] Update-manifest signature stays inert (R09)** — accepted trade.
  **[accepted]** ↳ notes: `manifest-signature-inert-r09.md`

---

## UI / UX polish

- **[P3] Loading/Restarting overlay: native redesign remainder** — 24 stock `confirm()` dialogs on 9
  pages. **[owed: the confirm() pass]** ↳ notes: `loading-overlay-redesign.md`
- **[P3] Reaper QoS: no unsaved-changes cue** (metal, 2026-10-22) — the × on a rule edits only the
  page and nothing says Apply is still owed (the owner's first delete was never written). A
  pending-changes bar on the Reaper pages that edit lists.
  **[not started]** ↳ notes: `reaper-native-ui.md`

---

## Potential Features to add

- **[P1] Reaper-native UI: convert every stock ASUS page, then remove the stock pages and the theme
  switch** (owner, 2026-10-22) — Reaper is its own product, not a re-theme. Ten waves: foundations
  (component kit, one menu model, httpd plumbing, parity tests) and urgent fixes first; then System,
  LAN, WAN, Wireless/Networks, USB apps, Parental/speed, VPN (one slot-model section), Logs/tools;
  AiMesh and the Repeater/Media Bridge/node flows last (no test hardware; the setup wizard stays for
  those until a tester confirms); then the cutover deletes the stock pages, the never-visible pages,
  `reaper_inject` and the stock JS/CSS.
  Owner 2026-10-23: every page, so the stock pages can go (1 GB RT-BE86U; the cutover frees flash,
  the RAM levers are in `ram-dedupe.md`).
  **[waves 0 + 1 (System, SNMP, Tweaks) on metal; System Log group built 2026-10-23 (_r25); LAN + WAN
  built 2026-10-23 (_r32, metal owed); next: VPN, Wireless]** ↳ notes: `reaper-native-ui.md` (plan + progress), `native-page-migration.md`
- **[P3] Security review: watch more settings** (owner, 2026-10-23) — it compares 24 settings and
  hashes 3 lists; candidates: admin access and passwords (hash only), the second WAN, FTP / Samba /
  SNMP / VPN servers, DNS and DDNS, Reaper's own protections switched off, the update chain, open
  Wi-Fi. Newly watched keys must not alarm after an upgrade.
  **[part done 2026-10-24 (owner, with the _r35 diag): Reaper's own protections are watched - rwarden_enable / dns /
  dns_feeds / self / dir / feeds, gk_enable / default / captive, wallguard_enable, reaper_fw_enable, reaper_pbr_enable,
  reaper_dot_srv, the country list and custom feeds hashed; a setting the accepted baseline predates is adopted into
  it silently with one log line (`test_rwatch_review.py`). The rest (admin access, second WAN, servers, DNS/DDNS,
  the update chain, open Wi-Fi) not started]** ↳ notes: `security-review-coverage.md`
- **[P3] Dreadwatch lists on USB: a higher name limit while a USB store is attached** (owner,
  2026-10-22) — a Long-Term Storage row "Dreadwatch lists" (USB only, like Wallguard's): each list's
  download and the compiled copy on the volume through `rstore`, restored after a reboot without
  downloading; limit 3,000,000 with the volume present (the free-memory guard still applies),
  1,000,000 without it. The list in use always loads into RAM, never from the stick. USB does not
  reduce memory use: the one mapped table holds the names (~12 B each since 2026-10-24; ~54 B in each
  dnsmasq instance before that).
  **[proposed 2026-10-22; owner 2026-10-24: decide after the RAM item - now built, 3,000,000 names would be
  ~36 MB mapped once (about 650 MB across the old copies), so the limit itself is the lever to revisit]** ↳ notes: `dreadwatch-limit.md`
- **[P1] Image size: the RT-BE96U root filesystem is within ~1 MB of its flash slot** (68.4 of 69.5
  MB) — every added file now competes with the slot; measure the staged image, then remove or
  deduplicate what ships (the 1.7 MB logo PNG, stock pages Reaper replaced, the OUI table shipped
  twice, unused modules, compression settings; Samba/Tor/speedtest/DLNA are owner calls).
  **[2026-10-22: orphans removed in canon (1,978,368 B, headroom now ~2.7 MB); _r16 metal PASS: no
  missing-file errors, Samba tools resolve every library; image re-encodes and owner-decision
  features next]** ↳ notes: `image-size-hunt.md`
- **[P2] Encrypted DNS: split the block into two switches (DoT/DoQ on 853, DoH to known resolvers)**
  (owner, 2026-10-21) — new `reaper_dot_block`, each with its own counter; canaries and the DoH name
  list follow the DoH switch.
  **[designed 2026-10-21, not started; first job 2026-10-22]** ↳ notes: `encrypted-dns.md`
- **[P2] Code signing: manifest + images, with a pre-upload verdict.** **[scheduled]** ↳ notes:
  `manifest-signing-shelved.md`
- **[P2] Firmware rollback + trial boot from the second slot** (owner, 2026-10-23) — every flash
  already keeps the previous image in the other slot; add "roll back to the previous firmware" (no
  download) and a trial boot that returns to the known-good slot unless the new image is confirmed.
  **[researched 2026-10-18; not started]** ↳ notes: `firmware-dual-slot-rollback.md`
- **[P3] Language packs on demand: English-only image, the admin installs their language**
  (owner, 2026-10-23) — ~2.9 MB of flash back, room for more than 24 languages; packs signed (needs
  code signing above), picked by their own name and fetched in one click from the Reaper release.
  **[idea, measured; not started]** ↳ notes: `language-packs-on-demand.md`
- **[P2] Encrypted DNS Step B: DNS-over-HTTPS on the router** — Windows and browsers encrypt to the
  router. **[planned in outline; after Step A is proven on metal]** ↳ notes: `encrypted-dns.md`
- **[P3] Diag: flag a replacing `/jffs/configs/dnsmasq.conf` and a dead local DNS upstream**
  (GT-BE98 ControlD report).
  **[built 2026-10-25 as diag v1.3.49, v3.4.9, test image _r39: section 5 says when the file replaces the generated
  config and when a local upstream has nothing listening, each with a FINDING; the rdnshc half not done]** ↳ notes:
  `controld-leftover-dnsmasq-conf.md`
- **[P3] Encrypted DNS: Flow Explorer names for DoT clients** — rednsd feeds rdnsmapd.
  **[deferred]** ↳ notes: `encrypted-dns.md`
- **[P4] Advanced tier: TLS interception for URL-level inspection** — opt-in, router CA on every
  device; own threat model first.
  **[idea]** ↳ notes: `encrypted-dns.md`
- **[P3] Wi-Fi VLANs: the two missing pieces.** **[project]** ↳ notes: `wifi-vlans-residual.md`
- **[P3] Unbound beside the existing resolver path.** **[project]** ↳ notes: `unbound-resolver.md`
- **[P3] Staged ("batch") changes — one save, minimal restarts.** **[project]** ↳ notes:
  `staged-batch-changes.md`
- **[P3] Mimic — hardware port mirror to an external IDS** (WAN Ports page, every wired port,
  dual-WAN aware) — Phase 0 mostly proven.
  **[owed: accelerated-flow + restart tests, then build]** ↳ notes: `port-mirroring-ids.md`
- **[P3] Policy Routing on Warden's country sets.** **[feature, owner call]** ↳ notes:
  `pbr-warden-country-sets.md`
- **[P2] Security review: harden the baseline against tampering** — anyone with an admin session
  or root can accept a new baseline. Accept logging what it folded in is done (v3.4.8); open: the
  tick flags a baseline rewritten outside Accept; Accept asks for the admin password.
  **[offered 2026-10-19; owner call]** ↳ notes: `security-review.md`
- **[P2] Two-tier admin credential** — a second, rarely typed secret (the unused `shell_username`
  account) required for root-equivalent actions; SSH only through that account. A phished GUI
  password could then run the router but not own it.
  **[designed 2026-10-19; owner call]** ↳ notes: `two-tier-admin-credential.md`
---

## Documentation

- **[P3] Add-on integration points** — publish what an external audit may read; decide on a format
  marker. **[owner call]** ↳ notes: `secaudit-external-addon.md`

---

## Code quality / deferred (with reason)

- **[P3] haveged 1.9.22 → 1.9.27** (Merlin a274d80d0d7, 2026-10-26) — we ship it; low risk, low value.
  **[not started]** ↳ notes: `merlin-40585-review-2026-10-26.md`
- **[P3] Faster local builds** (Merlin 0e562d854a5 parallel bootloader, ec279401070 no second image/OpenSSL build) —
  build time only. **[not started]** ↳ notes: `merlin-40585-review-2026-10-26.md`
- **[P3] Delete the dead ASUS DDNS code** (owner, 2026-10-23) — asuscomm is unreachable from v3.4.9
  (boot clears it, `start_ddns()` refuses it, no GUI or app route sets it). Left in place:
  `rc/asus_ddns.c`, the asus branches of `start_ddns()` and the watchdog, the inadyn asuscomm
  plugins, the Warden asuscomm seed and its test. **[not started]** ↳ notes: `asuscomm-removal.md`
- **[P3] Kit and httpd duplicates to fold into one copy** (owner rule, 2026-10-23) — table CSS in 7
  pages, the runner request helper in 3, two ping-preset loaders, two hand-written double forks in
  httpd. No behaviour change; the http_id token stays on every runner call.
  **[listed 2026-10-23; not started]** ↳ notes: `kit-dedupe.md`
- **[P3] Web-interface login lock is per LAN/WAN side, not per source** (stock httpd: five failures
  lock the whole side for five minutes). Per-source would need a table httpd does not keep; the
  review card's login notices name the source instead, and management off the WAN removes the
  exposure. **[deferred]** ↳ notes: `security-review.md`
- **[P3] Bandwidth tab — Cloudflare's speed test in the firmware** — built and metal-tested as
  v3.4.2 test rungs r9-r12, then removed: Cloudflare serves its 100 MB+ downloads only to a browser
  request, so the router's run had to work around that and froze the UI for its whole length; the
  device-side run alone adds nothing over speed.cloudflare.com in a browser. Internet Speed (Ookla)
  stays. **[dropped 2026-10-13]** ↳ notes: `bandwidth-tab.md`
- **[P3] Code review 2026-10-07: plain-HTTP login default (G2), factory posture (G5)** — owner
  accepted, no change. **[accepted]** ↳ notes: `audit-2026-10-07-remediation.md`
- **[P2] The code-review MEDIUM/LOW tail, batch B.** **[owed: the two deferred items]** ↳ notes:
  `code-review-tail.md`
- **[P2] Only Gatekeeper knows AiMesh exists** — wants one shared `reaper_aimesh_exempt()`.
  **[owed — before a fourth enforcement surface]** ↳ notes: `aimesh-exempt-helper.md`
- **[P2] Network page: Delete does nothing on a main-network card** — development-based, not
  firmware-wide. ↳ notes: `sdn-mainfh-delete-dead.md`
- **[P3] Second review of the v3.1.0–v3.1.5 code** — seven slices, reachability before any finding.
  **[planned — not started]** ↳ notes: `review-carry-forward-queue.md` §4
- **[P3] Sibling port misses adds, renames and deletes** — local sibling builds break; CI immune.
  **[owed]** ↳ notes: `sibling-port-add-rename-delete.md`
- **[P3] Policy Routing: recapture of flows that leaked while the rules were absent.**
  **[deferred]** ↳ notes: `pbr-conntrack-recapture.md`
- **[P3] GitHub release retention — betas 5+ versions behind are pruned.** First run 2026-10-19
  (152 removed, tags kept, manifest-advertised releases kept); repeat at each publish.
  **[recurring, owner call]** ↳ notes: `release-retention-prune.md`
- **[P3] Sibling worktrees carry build detritus.**
  **[hygiene]** ↳ notes: `sibling-worktree-detritus.md`
- **[P3] Local sibling images** — four siblings are source-only locally; CI unaffected.
  **[hygiene]** ↳ notes: `local-sibling-images.md`
- **[P3] Build one `stable` image** — the stable channel path has never run.
  **[owed]** ↳ notes: `channel-marker.md`
- **[P3] `poll_fcache` O(n²) pairing · `do_reaper_dev_cgi` snapshot arrays.**
  **[shelved]** ↳ notes: `shelved-perf-items.md`
- **[P3] Theme-token vocabulary consolidation (remainder of D4).**
  **[owed — to the page migration]** ↳ notes: `theme-token-consolidation.md`
- **[P3] Inherited httpd core: two pre-auth robustness gaps.**
  **[inherited; deferred]** ↳ notes: `httpd-inherited-preauth-gaps.md`
- **[P3] avahi CVE-2024-52615 / -52616 (wide-area)** — nothing on the box makes a wide-area lookup.
  **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] avahi CVE-2021-3468 / CVE-2025-59529 (local socket)** — reachable only by root processes on
  the router. **[not reachable — benign]** ↳ notes: `avahi-residual-cves.md`
- **[P3] OSPF + BGP dynamic routing.** **[Not Needed]** ↳ notes: `ospf-bgp-dynamic-routing.md`
- **[P3] Encrypted DNS answers guest/VLAN networks over IPv4 only.** **[deferred]** ↳ notes:
  `encrypted-dns.md`
- **[P3] Wallguard: network profiles IPv4-only; merged identical lookups share one CNAME verdict.**
  **[deferred / accepted]** ↳ notes: `wallguard.md`
- **[P3] WireGuard server starts before NTP sync** — the clients wait for `ntp_ready` and retry from
  cron; the server does not. Investigate gating it the same way. **[working as intended]** 
  ↳ notes: `wgs-start-before-ntp.md`

---

## Reported, investigated, closed as working-as-designed

*Not defects. Recorded so the same report is not re-investigated.*

- **GT-BE98: no DNS after ControlD was removed, downgrades did not help** — a leftover
  `/jffs/configs/dnsmasq.conf` (add-on residue). **[closed 2026-10-21]** ↳ notes: `controld-leftover-dnsmasq-conf.md`
- **Guest network VPN not applied, OpenVPN Killswitch blocked the LAN** (forum, BQ16) — the
  guest network had "Use main subnet" on, so it shared br0. User configuration, not Reaper code:
  the reporter turned it off and is working (owner, 2026-10-18).
  **[closed 2026-10-18]** ↳ notes: `sdn-vpn-main-subnet-killswitch.md`
- **ASUS CVE-2026-14157 (VPN-file format string) and CVE-2026-13313 (Telnet debug function) do not
  apply** — Merlin's `vpnupload.cgi` → libovpn import path has no format-string sink; telnetd is not
  built. The 2026-10-07 batch was assessed the same week.
  **[closed 2026-10-13]** ↳ notes: `CODE-AUDIT-2026-10-13-v3.4.2.md`
- **Dual-WAN: both NextDNS profiles receive DNS logs** — stubby round-robins every DoT endpoint.
  ↳ notes: `wad-dual-wan-nextdns.md`
- **Investigated, not a bug (do not re-raise).**
  ↳ notes: `wad-investigated-not-a-bug.md`
- **Translations — closed 2026-09-08, kept as a guard** (do-not-translate list).
  ↳ notes: `translations-residual.md`
- **SNMP `rwuser` — keep as-is** (owner, 2026-08-19): `rouser` would remove SNMP-SET.
  ↳ notes: `snmp-rwuser.md`
- **`rwatch: FAILURE detected: warden-self-drop:<n>` is the feature reporting.**
  ↳ notes: `wad-warden-self-drop-failure.md`
- **Firewall rule negation — not building.**
  ↳ notes: `wad-firewall-rule-negation.md`
- **`dig` on the Network Tools page — declined.**
  ↳ notes: `wad-dig-network-tools.md`
- **DNS-rebind warnings for names a LAN filter blocks** — use NXDOMAIN blocking.
  ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **DNSSEC on the router fails every blocked name in a signed zone** — validate in the filter.
  ↳ notes: `wad-rebind-lan-filter-blocks.md`
- **DDNS *Interface* selector on dual WAN is stock ASUS.**
  ↳ notes: `wad-ddns-interface-selector.md`
- **Mobile device metrics reported incorrect** — a rendering report.
  ↳ notes: `mobile-device-metrics.md`
- **AiMesh nodes refuse the firmware** — a reset cured it.
  **[watch]** ↳ notes: `aimesh-node-firmware-refused.md`
- **AiMesh node: a PC on the node's WAN/LAN-1 jack gets no DHCP/RA for ~30 s** — stock AiMesh
  handling of the node's uplink jack; `lan_stp=0` does not change it; use a LAN port.
  ↳ notes: `wad-aimesh-node-wan-jack-delay.md`
- **Service Intercept redirect-to-router with nothing listening** — enable the router's service.
  ↳ notes: `intercept-redirect-no-listener.md`
- **Boot: three "consumer-less" daemons are kept; no VPN/firewall start is reordered.**
  ↳ notes: `boot-efficiency.md`
- **Boot: what is not to be reordered, and why.**
  ↳ notes: `boot-efficiency.md`
- **Throughput: dataplane IRQs land on CPU0** — no pressure; no change.
  ↳ notes: `idle-cpu-burners.md`
- **Rule Status walker: repair-on-red — refused by design** (owner, 2026-09-16); report-only.
  ↳ notes: `firewall-witness-catalog.md`
- **Rule Status walker: 8 catalog rows not built** (B4 C8 D4 D7 G3 G5 G6 H4) — each with a stated
  reason.
  ↳ notes: `firewall-witness-catalog.md`
- **Gatekeeper's admin escape hatch under the ASUS admin allowlist** — the administering device is
  on the list.
  ↳ notes: `firewall-witness-catalog.md`
- **USB storage attaches after `services-start` on every boot** — stock order; `/opt` services
  before the mount fail.
  ↳ notes: `usb-boot-mount-chain.md`
- **"Every flash rewrites the bootloader" — it does not** — only `_loader.pkgtb` writes the loader
  partition.
  ↳ notes: `uboot-in-bootfs-not-loader.md`
- **Minimum width on Auto in an AiMesh: phones stay on the router** — channel sync mirrors the
  floor's pick onto nodes.
  ↳ notes: `bwfloor-aimesh-roaming.md`

---

## Blocked by closed-source components — for ASUS / Broadcom

> Root-caused on RT-BE96U hardware; the responsible code lives in prebuilt Broadcom blobs.

- **B-1. Classful QoS WRR is non-functional on eth ports.**
  ↳ notes: `blocked-b1-classful-wrr.md`
- **B-3. [P3] Guest Network Pro breaks the 2.5G-1 LAN port with a manual WAN VLAN** (GT-BE98).
  **[blocked — blob; risk-accepted]** ↳ notes: `blocked-b3-guestpro-vlan-port.md`
- **B-3b. [P2] Diag section 5 reports the wrong link for a LAN-port WAN** (GT-BE98).
  **[owed]** ↳ notes: `diag-lanport-wan-link.md`
- **B-4. [P3] Broadcom's own dynamic puncturing needs the 2025 SDK.**
  **[blocked — SDK]** ↳ notes: `blocked-b4-dynamic-puncturing.md`
- **B-5. [P1] Internet speed test fails on 10 Gbit/s links** — owner ruling: not chased.
  **[blocked — development]** ↳ notes: `speedtest-10g-links.md`
- **B-6. [P2] Internet speed test may stop on 2026-10-01** — ASUS retires the Ookla setup Reaper
  uses. **[blocked — GPL]** ↳ notes: `speedtest-embed-key-retired.md`
- **B-7. [P3] Source to ask the vendors for** — ranked: ASUS-owned first (AiMesh, the httpd login
  check, networkmap); Broadcom's under NDA (ask for errata and docs); nine GPL-labelled modules
  shipped as prebuilt objects are the one licence-based ask.
  **[list written 2026-10-19; owner call on the ASUS-facing page]**
  ↳ notes: `blob-source-wishlist-2026-10-19.md`
