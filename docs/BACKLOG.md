# RT-BE Series "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done/verified), **[blocked]** (external cause),
**[shelved]** (deliberately deferred), **[cosmetic]** (polish, non-blocking).

**Priority** (assigned 2026-08-06, by impact on user-facing functionality):
**[P1]** core function broken or at risk for users · **[P2]** degraded function,
meaningful annoyance, or privacy exposure · **[P3]** cosmetic, polish, internal
quality, or deferred-by-decision.

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md). Completed backlog items are
> moved to the changelog and removed from this file (housekeeping passes 2026-07-18,
> 2026-08-06).

---

## Testing / Validation — [P1]

On-metal verification owed for shipped fixes. These stay P1 as a block: each
validates a shipped critical-path change, and an unverified fix is a latent field
regression.

- **v2.1.9 metal checks (fleet built 2026-08-05; audit-hardened respin of the unpublished
  v2.1.7/v2.1.8). [owed]**

  - *WAN-MTU rollback:* on a DHCP/static WAN the MTU field refuses >1500 (1508 no longer
    enterable/applyable); owner's BE96U: re-apply 1500 once (a 1508 from the pre-rollback
    build may persist in nvram/on the interface until re-applied) and confirm the WAN
    interface runs at exactly 1500 (`ip link`).

  - *Device-name unification:* rename a device on the Devices page → name appears on Client
    List / Network clients / Gatekeeper / Traffic Top Talkers / Connections / Wireless Log /
    DHCP-leases "Device Name" column, and **survives a reboot**; remove an *offline* client →
    no other custom names are lost; rename in the stock popup with the Devices page open in
    another tab → neither rename rolls the other back; a device that had duplicate name
    records shows the most recent name after one reboot.

  - *Siblings PPPoE-1500:* on a BE88U (or any sibling) v2.1.9, the WAN page accepts PPPoE
    MTU/MRU 1500 and the WAN interface raises to 1508 (`ip link` / `ifconfig`).

  - *Traffic flash-persistence:* flash v2.1.9 over an earlier build with USB history enabled →
    history intact after the flash; collector log shows a clean store re-attach.

  - *Storage USB panel:* disk info/health/format/eject work against a real stick; format
    refuses the active store without confirmation.

  - *Audit-fix behaviours (v2.1.9):* the three re-classified native pages (Connections, QoS
    Diagnostics, WiFi Professional) render with their own theme intact (no stock CSS bleed);
    the QoS Diagnostics live graph still updates (page now sends the `http_id` token); the QoS
    stats table stops updating in a backgrounded tab and resumes on return; a DHCP reservation
    entered with a non-canonical octet (e.g. `…050`) is stored canonicalised and honoured by
    dnsmasq. Full fix list: [`CODE-AUDIT-2026-08-05.md`](CODE-AUDIT-2026-08-05.md).

- **v2.2.0 metal checks (shipped all five models 2026-08-06). [owed]**

  - *First-boot loop fix (`137d96338a`):* factory-reset wizard end-to-end — no reload loop,
    password survives reboot; whether `do_chpass` (blob) kills the session token (if yes the
    hidden saveNvram apply dies → password RAM-only until reboot — decide follow-up);
    upgrade-in-place from a looping v2.1.6 box recovers without reset. Full analysis:
    [`LOGIN-LOOP-2026-08-06.md`](LOGIN-LOOP-2026-08-06.md).

  - *Gatekeeper internet-only DNS carve-out (`fe3b205604`):* on the owner's LAN (AdGuard at
    `.98` as DHCP DNS), set the Work_Laptop to internet-only → `nslookup` succeeds and
    browsing works; `ping 192.168.50.98` and file shares still fail; other LAN hosts
    unreachable; a blocked device still gets nothing; a quarantined unknown still lands on
    the captive page. Pre-flight on the router once: `ebtables -h` accepts `--ip-proto` /
    `--arp-ip-dst` (kernel side is confirmed `=y`). Also confirm disable now leaves no stray
    `REAPER_GK` chain (`ebtables -L` after turning Gatekeeper off — the teardown-truncation fix).

  - *WiFi Professional preamble lock:* setting 2.4 GHz "Disable 802.11b" locks the Preamble
    select to its Disable-802.11b state (dimmed); switching back to Allow restores the prior
    preamble; a box whose nvram already held `rateset=ofdm` shows **0** pending changes at
    page load.

  - *USB Disks tab:* the new first tab under USB Application lists disks and scan/format/eject
    work against a real stick; the Long-Term Storage page (System Log) keeps only the store
    selection and still saves it.

  - *De-cloud console quiet:* no "Error fetching ASUS privacy policy" in the console; the
    dashboard client list makes no requests to `nw-dlcdnet.asus.com`.

- **v2.2.1 metal checks (shipped all five models 2026-08-06). [owed]**

  - *Warden "total blocked" persistence (`54e2aad21f`):* total holds across a reboot and a
    reflash; turning Warden Off zeroes it; factory reset zeroes it.

  - *Per-dataset "collecting since" (`2b01195a64`):* on a JFFS/USB store, enable a dataset →
    its date appears after the first rwatch tick and survives a reboot (a dash means the
    dataset is off or the store is RAM).

  - *Health-scan result persistence (`40f91ba727`):* superseded by the ext4 scanner fix in
    Known issues below — verify with that item's metal test.

  - *Firmware page:* the Security Update section is gone; Check triggers the GitHub check and
    the result/badge reflect the published version; the scheduled toggle persists.

- **Older metal checks still owed.**

  - *v2.1.6 firmware-update check:* enable check → Check → badge + page show the published
    version; wrong-variant line never matched. *v2.1.6 wan-gw watchdog:* an ICMP-filtering
    first hop logs one informational note, no phantom FAILURE; a real PPPoE drop still alarms.
    *v2.1.6 menu labels:* RU "Administration" / TR label render clean on stock pages.

  - *v2.1.5 Traffic history:* reboot with `rtraf_path=usb` → logread shows "store came up
    late - attached" and history survives; power-pull loses ≤15 min (USB) / ≤1h (JFFS).

- **First-boot credentials wizard (shipped v1.5.5) — factory-reset metal test. [owed]** Factory
  reset → wizard appears → no page/dashboard reachable until username+password set → forced
  to the wireless page until a WiFi PSK is set → dashboard → values persist → all editable
  later; also confirm an *upgrade* (no reset) does **not** trigger it. **Known limitation
  (v1.5.5) [P3]:** the WiFi step releases once WiFi is *configured* (`sdn_rl` changes), so a
  user could save it **open** and skip a PSK — optional tightening is to require a non-empty
  PSK (currently uses the stock `sdn_rl` signal for stability). Feature record in
  [`CHANGELOG.md`](CHANGELOG.md) v1.5.5; it replaces the stock forced password gate and is
  the concrete mitigation for deferred finding **H15**.

## UI / UX polish

- **[P2] Loading/Restarting** The loading, percent wait, and the rebooting modals need to cover
  whole screen to prevent navigation or clicking on nav menu or header items. Currently it 
  only covers the viewport shell. All modals should also be converted to Reaper native designs.

- **[P2] Network (SDN) page: suppress or mask the post-apply SSID+password overlay.** (Owner
  request 2026-08-05; evaluated, no change made yet.) Editing a wireless network's
  SSID/auth on the Network page pops the stock ASUS card listing every band's SSID and
  **plaintext network key**. It is `showWlHintContainer()` (`state.js:4887`, key rendered
  ~5241-5249) — a client-side overlay, shown from `sdn.js` at 13 apply call sites
  (746-751 et al.) **only when `isWLclient()`** (the admin browser is itself on Wi-Fi;
  wired admins never see it) as a reconnect hint before `restart_wireless` bounces the
  admin's own connection. Plain unminified JS; survives packaging. Not a vuln
  (authenticated-GUI display only). The function is **shared** with `mlo.js`/`mlo.html` +
  three Advanced_VLAN/Roaming pages — scope any change to the `sdn.js` call sites, do NOT
  edit the `state.js` function body. Options: (i) skip the card in `sdn.js`, keep
  `check_isAlive_and_redirect` (med risk: Wi-Fi admin sees a spinner until reload);
  (ii) mask the key, keep the SSID hint (low risk); (iii) leave stock. [owed — owner
  to pick a direction]

- **[P3] i18n residuals.** English-only strings needing a translation pass across
  the dicts: (a) the AI Advisor intro was completed in `EN.dict` (RADV_01) but the other 24
  language dicts still carry the older truncated phrasing (translated); (b) the Connections
  "Quick Look" labels (Device / Scope / State / Internal / External / Quick Look / Advanced /
  Pause) are English literals pending tokenization across the 25 dicts; (c) the Warden
  feed-dedup note `RWDN_55` (v2.1.6) is English-seeded in all 25 dicts, translation pass
  owed. [owed — cosmetic/i18n]

- **[P2] Client ID** The traffic Analyser part, if checking the last 24 hours for example, if a 
  device goes offline - it will   just show the IP address and not the name - and when the 
  device comes back online - it will update the device name.
  *(2026-08-05 note: NOT closed by the v2.1.9 name unification — the Traffic page resolves
  names live from the client list, which only carries devices networkmap currently knows.
  A long-offline device falls out of that list, so its history rows fall back to IP/MAC.
  Proper fix = have rtrafd persist a MAC→last-known-name sidecar (or resolve against
  the master `custom_clientlist` directly, which does retain named offline devices) —
  pairs with the Traffic Analyzer month-view item below.)* [owed]

## Known issues (cause identified)

- **[P2] USB Health Scanner never actually scanned ext4 — result showed the raw XML wrapper
  (owner report 2026-08-06, v2.2.1). — FIXED 2026-08-06 (`9352c60a1d`), rides the next
  build, metal owed.** The v2.2.1 keep-result-on-screen fix exposed that the result was
  never real. Three stacked causes: (1) stock diskmon **skips every ext4 partition**
  (`rc/usb.c` "there's some problem with fsck.ext4" — a guard predating a usable e2fsck),
  so the scan ran START→FINISH doing nothing and wrote no log; (2) the `fsck.ext4` symlink
  was gated on `RTCONFIG_EXT4FS` (hard-set `n`), so `app_fsck.sh ext4` had no binary anyway
  (e2fsck 1.45.6 **is** on the image); (3) `Reaper_USB.asp` fell back to dumping the raw
  `disk_fsck.xml` responseText when `<disk1>` came back empty. Fix: ext4 skip removed
  (on-demand scan path only; the asusware mount-time auto-fsck keeps its skip), `fsck.ext4 →
  e2fsck` linked under `E2FSPROGS=y`, and the page now renders a verdict line from the
  `apps_fsck_ret` codes (stock tokens, persisted across panel rebuilds) plus the real log —
  never raw XML — and grace-polls so a second scan can't report done instantly off the
  previous run's stale status. **Metal:** scan the ext4 stick → e2fsck output + verdict stay
  on screen; a repeat scan shows fresh results. Sibling port owed (all three files are
  shared code).

- **[P3] [residual of the v2.1.3 apostrophe-XSS fix — low, optional] Unescaped `title='...'`
  attributes on the client lists — PARTIALLY DONE.** The reported stored-XSS/garble via an
  apostrophe in a device name was fixed in v2.1.3 (patch 0311; see the changelog). The three
  client-popup tooltip fields in `dashboard/js/clientlist.module.js` were encoded in v2.2.0
  (`0e8b791827`). Remaining defense-in-depth only: `client.vendor` / `deviceTypeName` are
  still emitted into single-quoted `title='...'` attributes unescaped in
  `client_function.js`, but those are vendor/OUI-DB-sourced, not attacker-freeform.
  [owed — low, optional]

- **[P2] ASUS-CDN device/app icon phone-home — PARTIALLY FIXED in v2.2.0; more sites remain
  (owner ask 2026-08-06 to remove the rest). NOT device-side.** Assessment 2026-08-06:
  the icon fetches are **entirely browser-side** — the admin's browser fetches
  `nw-dlcdnet.asus.com` directly; **no router-side C code or daemon fetches icons** (the
  only firmware-side `asus.com` strings are the FRS firmware-update URLs in the closed
  `frs_service.o`/`private.o` blobs — a separate phone-home surface, not icons). Each fetch
  leaks the presence/model of ASUS devices (and, on the QoS monitor, the app set) to ASUS.
  - **DONE (v2.2.0, `0e8b791827`):** the two fetches in `dashboard/js/clientlist.module.js`
    (per-device `productIcons/<name>.png` + the `extend_custom_svg_icon.json` catalog).
  - **STILL LIVE — remove these too:**
    - `index.asp:~1643` — stock client-list/networkmap device detail fetches
      `productIcons/${clientObj.name}.png` (same gate: ASUS device w/ default type icon).
    - `js/httpApi.js:~1383` — `checkCloudModelIcon()` helper fetches `productIcons/<model>.png`
      (used for AiMesh node/model icons); shared helper, find + neuter callers.
    - `AdaptiveQoS_Bandwidth_Monitor.asp:~785` — `app_icons/<...>.png` per-app icon fetch.
  - **WIDER same-class surface (cloud DATA, not icons — decide scope):** many `getJSON`/`fetch`
    to `nw-dlcdnet.asus.com/plugin/js/*` — `gameList`, `DNS_List`, `tz_db`, `pppIspList_V2`,
    `ui-model-name`, `opennat_pf`, `iptv_profile`, `collected_FAQ`, `gameProfile` — plus
    hardcoded ASUS-CDN game-image URLs in `css/gameprofile.css`. Note the `www/Makefile`
    (L30-39) also `wget`s several of these at **build time** into `ajax/` (that's a
    build-host fetch baked into the image, not a runtime phone-home — lower priority, but
    worth a bundled-copy policy). **Fix pattern (all):** drop the remote fetch, fall back to
    the bundled/local asset Reaper already ships (rule 17 asset-swap for icons), or gate off
    by default. See the phone-home surface map. [owed — de-cloud cleanup, extend the v2.2.0 fix]

## Known issues (under investigation)

- **[P1] VPN speedtest hang → `sched: RT throttling activated` → wireless-only drop —
  ROOT-CAUSED at source, DIAGNOSTIC TEST REQUIRED before any fix ships.** (Field
  2026-08-04 23:02, BE96U: built-in Ookla test over an active VPN, QoS off, 4 Gbps ISP —
  hung at ~1.1 Gbps; syslog `sched: RT throttling activated`; wireless clients dropped,
  wired stayed up. Distinct from the v1.7.9 cold-start retry fix and the BE98 classful-QoS
  freeze below.)

  - **Cause chain (stock-inherent, not Reaper):** the platform boots with
    `sched_rt_runtime_us=99000/100000` (`96813GW.RT-BE96U:106-107` via
    `system-config.sh:235-240`) and `CONFIG_RT_GROUP_SCHED` off, so blowing the 99 ms/100 ms
    RT budget on a CPU throttles **every** RT task on that core. Broadcom's `rtpolicy`
    (`rt_settings_kthreads.txt:48-54`) promotes **ksoftirqd to SCHED_RR prio 5** and pins
    `bcmsw_rx`/`spu_rx`/`pdc_rx` (RR/5) to CPU0. VPN crypto is not runner-accelerated →
    runs in softirq → RT-promoted ksoftirqd saturates a core at ~1.1 Gbps → throttle fires →
    the Wi-Fi driver kthreads (RT, per-CPU-bound by wlaffinity, policy set inside the closed
    `wl.ko`) freeze with it → wireless drops; wired survives because it is runner-offloaded.
    Reaper daemons request no RT priority (verified); the Ookla blob runs SCHED_OTHER and is
    only the load generator.

  - **DIAGNOSTIC TEST (no build, decisive):** on-box, demote ksoftirqd back to normal
    scheduling — for each thread: `chrt -o -p 0 <pid of ksoftirqd/N>` (or, blunter:
    `echo -1 > /proc/sys/kernel/sched_rt_runtime_us`) — then rerun the same VPN speedtest.
    Hang + wireless drop gone ⇒ confirms the chain. Also record **which VPN engine** was
    active (WireGuard/OpenVPN ⇒ ksoftirqd path; IPSec ⇒ the SPU `spu_rx`/`pdc_rx` RR/5
    threads on CPU0 instead).

  - **Candidate bake (after the test confirms):** remove ksoftirqd's RT promotion in
    `router-sysdep.rt-be96u/rtpolicy/scripts/rt_settings_kthreads.txt` (restores the
    mainline-Linux default, keeps the RT throttle as a safety valve for the closed wl
    threads); optionally + affinity separation (crypto RX threads off the wl cores) and RPS
    spread for tunnel softirq. `sched_rt_runtime_us=-1` rejected as the primary fix
    (removes the safety valve). [owed — diagnostic test required]

- **[P3] MLO: individual link connections no longer shown per device (owner report
  2026-08-06). — INVESTIGATED 2026-08-06: name-unification cleared as the cause;
  needs the owner to name the exact screen before a fix can be scoped.** Code
  read of the current tree:

  - The **name-unification rung (`d8fe13ba12`) did NOT touch any MLO code** — it
    only changed how `custom_clientlist` is parsed/read (`gk_client_name`, the
    tolerant 6..9-field parser, set_name RMW). MLO row folding is keyed on the
    `mlo_link` flag and `rdev_is_rand(mac)`/`mld`-grouping, **independent of
    naming**, so unification cannot hide or merge a link by resolved identity.
    The v2.1.9 audit commit (`b381e97e89`) likewise touched no MLO path.

  - On the **Devices page this is by design**: `do_reaper_dev_cgi` (web.c ~23799)
    folds an affiliated randomized MLO link into its MLD device (`v[idx].mlo=1`,
    one row) and flags stray links `mlo_link:1`; `Reaper_Devices.asp` then
    **hides `mlo_link` rows** from the unnamed/rand/attn filters on purpose
    (v1.9.2/v1.9.3 "merge Wi-Fi 7 MLO links into one row"). So "individual MLO
    links not shown" on the Devices page is the intended behavior, not a
    regression.

  - **Therefore the regressed screen is almost certainly NOT the Devices page.**
    Before any code change, the owner should identify **which view** used to show
    the per-link rows — candidates: the stock **Wireless Log**
    (`Main_WStatus_Content.asp`, driven by `wl assoclist`/`get_wlclient`), the
    **Connections** page (`Reaper_Conn.asp`, flow-cache), or a stock Network-Map
    client detail — and what it showed pre-unification.

  - **Remediation is view-specific and can only be scoped once the screen is
    known.** Likely shape: the target view should *resolve* each link MAC to the
    parent device's unified name (so links read "MyLaptop · 5 GHz link") rather
    than being deduped/folded away — keep unification, add per-link rows that
    share the resolved name. [owed — owner to name the exact screen; then scope]

- **[P2] AI Mesh Search** Investigate the operation of search as it was reported 
  non-functional awhile back.  

- **[P1] BE98 Speed Test** Field reports that when QoS is enabled on the BE98 device 
  that the speed test crashes. Doesn't seem to affect everyone as some BE98 users 
  report no issues. Both claim to have the 1.8.6d installed which had the previous 
  fix for the crashing speed test. I have noticed potential soft crashes in speed testing 
  when I have class based QoS enabled. **Also observed (owner): a momentary freeze on the
  speed test in HW Classful mode (`qos_type=11`, the 8-queue WRR scheduler), but NOT in the
  HW Classless modes** — points at the classful egress-scheduler path (per-class queue setup /
  the runner reconfiguring queues under load) rather than the PI2 shaper itself.

  - **Source trace (2026-08-04, no code change — blob/metal-bound):** the built-in Ookla test
    is **router-originated** traffic (`ookla_exec`, a libws blob, runs the ookla client on the
    router). Its WAN egress traverses `QOSO` at `POSTROUTING -o $WANIF` (`rc/qos.c` ~1013), so
    in type-11 it is CONNMARK'd into the **default class → default egress queue**, and is then
    subject to that queue's PI2 shaper + the WRR schedule + the **aggregate port shaper**
    (`setportshaper=qos_obw`). **type-10 has none of these** (qid0 shaper only, no port shaper,
    no per-class, no WRR) — which is exactly why the freeze is classful-only. So the router's
    own saturating test flow is scheduled through the full classful egress path; a momentary
    freeze at test start is the runner engaging the port shaper + WRR + PI2 on a sudden
    line-rate router-local flow (the owner's "runner reconfiguring queues under load"). Both
    `ookla_exec` and the rdpa runner are **blobs** — not reproducible or safely fixable from
    the auditable source; no QoS/accel toggle exists in the auditable ookla path. Per-user
    variance fits config differences (`qos_obw`/`qos_orates` ceilings/WRR weights).

  - **NOT shipping a speculative fix** (metal-first / reachability discipline; QoS enforcement
    path). **Metal diagnostics to split it:** (a) run built-in test on type-11 while capturing
    `logread`+`dmesg`+`fc status`+`tmctl getqstats` before/during/after; (b) run the SAME test
    on type-10 (owner: no freeze) as the control; (c) run an **external/LAN-client** speed test
    (forwarded, not router-local) under type-11 — if it does NOT freeze, the built-in test's
    router-local path is the confound; (d) set `qos_pshaper=0` (port shaper off) or raise
    `qos_obw` to line rate → re-run built-in test; freeze gone ⇒ port-shaper interaction;
    (e) watch `fc status` for an accel flip during the test ⇒ runner reconfig. **Interim
    workaround for users:** run the built-in test with QoS on a classless mode or off, or use
    a LAN-client/external speed test; under classful the built-in test measures *shaped*
    throughput, not the raw line. [owed — metal + blob-bound]

- **[P2] The router is configured for dual-WAN failover**
  The active secondary WAN uses the 2.5 Gbps LAN port with DHCP and its own NextDNS profile.
  The future primary WAN uses the 10 Gbps LAN port with PPPoE, but it is not yet connected. It 
  has a separate NextDNS profile and DNS server addresses. The router currently fails over to 
  the active 2.5 Gbps connection. Despite only one WAN being live, both NextDNS profiles are 
  receiving DNS log entries. The expected behavior was for only the active WAN’s profile to show 
  traffic.

- **[P2] Traffic Analyzer** Traffic Analyser also does not put the device names for every device when 
  you view say, for the past MONTH.
  *(2026-08-05 note: same root cause as the "Client ID" item above — rtrafd history stores
  only MAC/IP, names resolve live at page load, so anything not in the current client list
  shows bare. Fix together with that item.)* [owed]

## Features to add

- **[P3] Warden: explicit IPv6 enable option + broader IPv6 feed coverage. [HELD — owner
  2026-08-04: leave IPv6 always-on for now, revisit later.]** IPv6 enforcement is **already
  built and always-on** — `REAPER_WARDEN`/`RW_DROP` chains hooked with `ip6tables`, v6 sets
  (`rw_threat6`, `rw_ban6`/`rw_allow6`, `rw_g6_<cc>` geo). When picked up: (a) `rwarden_ipv6`
  nvram (default `1` = current behavior) gating just the v6 block in `rw_gen_apply` (the v6
  teardown already runs unconditionally, so toggling off cleans up), + a UI switch on
  `Reaper_Warden.asp` + a dict token (25-dict lockstep); **flag the security implication** —
  off drops ALL v6 Warden enforcement for an IPv6 user. (c) v4/v6 hit-count split in
  `stats.sh` is a small add; the "IPv4 · IPv6" label already follows the armed v6 chain.
  (b) **Feed reality (researched 2026-08-04):** the open, freely-redistributable IPv6
  *threat*-feed space is thin — FireHOL L1 is IPv4-only, Feodo/DShield effectively IPv4,
  Cymru v6 is bogons not threats. **Spamhaus DROPv6 (already ingested) is about the best
  available**; no strong additional feed to add. Treat as a watch-item, not a quick win.

- **[P2] PHASE 2 — native Reaper firmware page (`Reaper_Firmware.asp`) with in-GUI download + flash.**
  (owner ask 2026-08-04) Replace the whole stock firmware tab with a Reaper-native page (shell/
  inject-skip, theme tokens, dict lockstep — the `Reaper_QoS`/`Reaper_Traffic` convention). Surface
  functions the stock page **disables** (`afwupg_support=false`, `betaupg_support=false`): one-click
  download of the published `.pkgtb` from `webs_state_url` → verify SHA256 (already in the manifest)
  → flash; show the release note inline; guard model+variant so a noMCP box can't pull an MCP image;
  optional rollback awareness. Pulls in image-signing / GPL-delivery considerations (was the deferred
  Phase 2). Depends on Phase 1's manifest + nvram wiring (shipped v2.1.6). [owed — build]

- **[P3] NORTH STAR — progressively replace stock GUI pages with Reaper-native ones.** (owner direction
  2026-08-04) Over time, migrate stock ASUS/Merlin pages to Reaper-native equivalents (own theme,
  de-clouded, only the functions we want exposed), as already done for Dashboard/QoS/Traffic/Wireless/
  GK/Warden/Devices/Advisor/Conn/QoSDiag. Firmware tab (Phase 2 above) is the next candidate. Track
  per-page migrations here as they're scoped. [ongoing]

- **[P3] Staged ("batch") changes — one save, minimal restarts.** Owner request. Today each control
  applies immediately, so e.g. changing all three Wi-Fi bands = three applies + three
  `restart_wireless`. Add a staging layer: a control's Apply becomes "Add to changes", writing
  the intended nvram diff into a cross-page **pending basket** (localStorage, under the Reaper
  shell) instead of applying; a persistent shell bar shows *"Pending changes (N) — Review /
  Apply / Discard"*; a review modal lists every staged change (page → setting → old⇒new). On
  Apply, the engine validates ALL first (all-or-nothing, like the Warden save), writes nvram in
  one commit, then runs the **de-duplicated, correctly-ordered** action set ONCE — reboot only if
  a staged change is reboot-class.

  - *Feasible — backend already supports it:* one apply POST carries many nvram keys + a chained
    `action_script` (`restart_wireless;restart_qos;…`), and `restart_wireless` cycles all radios
    at once, so "3 restarts" is a UI artifact, not a firmware limit. The missing piece is the
    accumulate-then-fire UI.

  - *Hard parts:* (1) an nvram-key → required-action map + safe ordering (e.g. firewall after
    wireless); (2) a **reboot-class table** — most changes are service restarts (seconds), but a
    few need a COLD reboot (MLO enable/disable; some SDN / operation-mode switches) so the engine
    must not reboot needlessly; (3) staleness/conflict if nvram changed underneath between staging
    and apply; (4) **scope** — clean for Reaper-authored pages (we own their save handlers), hard
    for stock ASUS pages (vendor `applyRule`/`showLoading` JS is invasive to intercept).

  - *Recommended path:* Reaper-native pages first. Quick sub-win for the Wi-Fi case: a single
    Reaper Wireless page showing all three bands that applies once. The full cross-page
    transaction system is substantial — its own project, v-next.

- **[P3] Remote syslog push/fetch.** The router can already send its log to a remote
  collector (send-only). Add the ability to **push to / be fetched by** analytics
  systems — most SIEM/analytics pipelines are push-based.

- **Traffic Analyzer → analytics-engine export (Splunk/Datadog/Dynatrace/Elastic/
  Prometheus/OTLP/syslog) — IMPLEMENTED v2.2.2 (`f2eed0a655`); BE96U MCP built +
  compile-verified. Owed: noMCP build, 5-model fan-out, on-device validation.**
  Shipped as: per-device latency/jitter/loss (batched in-process ICMP) + TCP
  conn/state (offload-safe) + throughput/online in `rtrafd` (`rtraf_hprobe`,
  NCLI→192), `health.json` + OpenMetrics `metrics.prom`; a new `rc/rexport.c`
  cru-pusher (curl, TLS-verify default-on, token out of ps via `-K`); a new
  **Administration → Data Export** page (`Reaper_Analytics.asp`) with engine
  presets + Test + Preview; a `reaper_metrics.cgi` token-gated Prometheus scrape
  endpoint; and the Off/Store+Export/Export-only mode card on Long-Term Storage.
  Deliberately excluded: wireless RSSI/PHY (later) and TCP retransmits (can't be
  sourced cleanly). The original investigation notes are retained below for the
  on-device tuning that remains (NCLI/CPU budget, health-metric fidelity):**

  - *Collected today (`rtrafd`):* per device = **identity (MAC, IP) + bytes
    down/up** only, as a live rate (`live.json`) and as time-bucketed byte totals
    (5-min×288 / hour×336 / day×366 / month×24 rings). Everything is timestamped
    (`live.json` `t`; history `now`+`step`). Also per-network, per-QoS-class
    (q0-6, HW-classful only), WAN throughput, monthly quota, and Top Talkers
    (src/dst/**dport**/proto/rate/up/dn + LAN MAC — port-level, no DPI). The only
    health probe is a **single WAN-target** `ping -c1` (aggregate RTT/loss overlay,
    off by default) — **no per-device latency/loss/jitter, no packet counts, no
    retransmits, no TCP state, no per-device flow counts**. So today you can derive
    per-device *volume/throughput* health, not *connection-quality* health.

  - *Delivery today:* **pull-only** via the auth-gated `reaper_traffic.cgi?f={live|
    m5|hour|day|month}` JSON. The remote-syslog push path carries **only** the
    quota 80/100% warnings.

  - **Two additions needed:** (1) **per-device health metrics** — cheapest sources:
    conntrack TCP state + per-flow retransmit/age (caveat: offloaded flows freeze
    their conntrack counters under the accelerator — same reason bytes moved to
    fcache in v1.3.1 — so this may undercount; fcache exposes HW-hit ratio but not
    RTT/retransmits), and/or an **in-process ICMP batch probe** to each client on a
    slow cadence (NOT fork-per-ping — see overhead below); (2) a **push exporter**
    (Splunk HEC over HTTPS, or structured syslog) that serializes one record per
    device at each bucket close.

  - **Hard prerequisite for 100-150 clients: `NCLI` is 64** (`rtrafd.c:63`) — the
    per-device array caps at 64 devices today, so ~150 clients needs `NCLI`≈160+
    (each client ring is ~16 KB → client rings grow ~1 MB→~2.5 MB; trivial on the
    1 GB box).

  - **Overhead / scaling (see the response 2026-08-06):** the data plane for
    150 clients at multi-Gbps runs on the **BCM4916 hardware accelerator**, which
    `rtrafd` only *reads* — it never touches packet forwarding, and it runs
    **SCHED_OTHER (no RT priority, verified)**, so monitoring **cannot** starve the
    RT wireless/data-plane threads or reduce throughput. Current collector = 2-3%
    CPU (5% peak), dominated by the 5-s fcache parse which is **bounded by flow
    count (FC_MAX=1536), not client count**. The added health sampling is the new
    cost: budget ~+2-5% CPU at 150 clients **if** done right — batch/in-process
    probe on a 30-60 s cadence, health metrics not per-second, and **push to Splunk
    at bucket close (1-5 min), never streamed per-second**. Design pitfalls that
    would blow the budget: fork-per-ping across 150 clients, parsing full
    `/proc/net/nf_conntrack` every second at high flow counts, or per-second HEC
    posts. [owed — collector enhancement + push exporter; pairs with the Remote
    syslog push item above]

- **[P3] NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST
  baseline.

- **[P3] Diag: regulatory-mismatch warning.** Make `reaper_diag` (and possibly a Wireless-page
  hint) print an explicit `WARN: territory_code=EU/xx but wlX_country_code=US` style line
  when the factory territory and the per-radio country codes disagree — self-documents
  gray-market / region-switched units in field reports. Field-observed 2026-07-28 on two
  EU GT-BE98s (`territory EU/01`, all radios `US`); also a suspect in the "Wi-Fi 7 client
  refuses 6 GHz, camps on 5 GHz @80 MHz" report (strict EU clients may reject a US country
  IE). Read-only nvram compare, no behavior change — firmware must never auto-alter a
  unit's regulatory nvram. [shelved]

## Code-scan findings 

**Deliberately deferred (with reason), still open:**
- **[P3] `poll_fcache` O(n²)→hash pairing** (`rtrafd.c`). Bounded to ≤1536 flows every 5 s and
  it sits in the metal-validated per-client accounting path — a rewrite of a millisecond-
  scale loop isn't worth the regression risk. Revisit only if a flow-heavy box shows real
  cost. [shelved]

- **[P3] `poll_classes` 7× `tmctl` popen batch** (`rtrafd.c`). Metal already measured 2–3 % CPU
  at the class-poll cadence; treating this as a non-issue per the prior finding. [shelved]

**Pre-release code review 2026-08-02 — remaining item:**
- **[P3] GDX pool watchdog field-proving.** The accelerator pool-drain check is opt-in (`rwatch_gdx`,
  v2.1.0). Confirm the `/proc/gdx/skb_idx` read is non-destructive under sustained polling on
  hardware before it can be considered for default-on again. [owed — metal]

**Full code audit 2026-08-05 — deferred items (see [`CODE-AUDIT-2026-08-05.md`](CODE-AUDIT-2026-08-05.md)):**
The confirmed audit findings were fixed in v2.1.9; five items were deliberately deferred.
*(Re-reviewed later the same day: all five confirmed still open by design — D1/D3/D4 are
cross-page refactors to do WITH the native-page migration and its on-device verification,
not piecemeal on a just-shipped fleet; L1/L3 remain shelved on their recorded rationale.)*

- **[P3] D1 — shared device-name resolver JS (5→1).** The `get_clientlist`+`nickName||name` resolver is
  reimplemented in five pages (DHCP/Conn/Traffic/QoS/Dashboard) with different keying. Extract one
  `reaper_names.js`. Best done in the **native-page migration** (cross-file refactor + on-device
  verification). [owed — migration]

- **[P3] D3 — unify byte/rate formatters across pages** (SI vs binary drift). "Fixing" changes displayed
  values on some pages, so pair it with the migration rather than change output piecemeal. [owed — migration]

- **[P3] D4 — consolidate the per-page `:root` theme tokens/components** (two token vocabularies for the
  same hexes across 13 pages). Visual-regression risk; do it with metal verification in the
  migration. [owed — migration]

- **[P3] L1 — spurious leading `<` in the set_name/set_reserve RMW output.** Cosmetic, verified-harmless;
  not worth re-touching the just-stabilised `custom_clientlist` RMW. [shelved]
  
- **[P3] L3 — function-local `static` snapshot arrays in `do_reaper_dev_cgi` aren't re-entrant.** Latent
  only (httpd serialises these requests); a malloc refactor of the multi-return CGI would add leak
  risk to fix a can't-happen case. [shelved]

## Documentation

- **[P3] Note the non-functional retained features.** Document that the firmware
  update-check and the (removed) security-check UI do nothing on Reaper and are
  retained only for potential future use.

- **[P3] Annotate** the system defaults.

- **[P3] Write a user guide** for other users.

## Platform / expansion

## Known issues (Cannot Remediate)

- **[P3] Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul
  BSS is still created even when every feature that would use it is disabled, spamming
  the log with RADIUS codes for an unused radio. Traced to a **closed-source Broadcom
  blob**; a boot-time script to suppress it based on device settings did not work and
  was reverted. [blocked — blob; risk-accepted]
