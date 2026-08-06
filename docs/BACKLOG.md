# RT-BE Series "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done/verified), **[blocked]** (external cause),
**[shelved]** (deliberately deferred), **[cosmetic]** (polish, non-blocking).

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md). Completed backlog items are
> moved to the changelog and removed from this file (housekeeping pass 2026-07-18).

---

## Testing / Validation

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
  - *Post-v2.1.9 committed UI work (rides the next build; metal owed):* on the WiFi
    Professional page, setting 2.4 GHz "Disable 802.11b" locks the Preamble select to its
    Disable-802.11b state (dimmed); switching back to Allow restores the prior preamble,
    and a box whose nvram already held `rateset=ofdm` shows **0** pending changes at page
    load. The new **USB Disks** tab (first tab under USB Application) lists disks and
    scan/format/eject work against a real stick; the Long-Term Storage page (System Log)
    keeps only the store selection and still saves it.
  - *Gatekeeper internet-only DNS carve-out (committed 2026-08-06, `fe3b205604`; rides the
    next build):* on the owner's LAN (AdGuard at `.98` as DHCP DNS), set the Work_Laptop to
    internet-only → `nslookup` succeeds and browsing works; `ping 192.168.50.98` and file
    shares still fail; other LAN hosts unreachable; a blocked device still gets nothing; a
    quarantined unknown still lands on the captive page. Pre-flight on the router once:
    `ebtables -h` accepts `--ip-proto` / `--arp-ip-dst` (kernel side is confirmed `=y`).
    Also confirm disable now leaves no stray `REAPER_GK` chain (`ebtables -L` after turning
    Gatekeeper off — the teardown-truncation fix).
  - *Audit-fix behaviours (v2.1.9):* the three re-classified native pages (Connections, QoS
    Diagnostics, WiFi Professional) render with their own theme intact (no stock CSS bleed);
    the QoS Diagnostics live graph still updates (page now sends the `http_id` token); the QoS
    stats table stops updating in a backgrounded tab and resumes on return; a DHCP reservation
    entered with a non-canonical octet (e.g. `…050`) is stored canonicalised and honoured by
    dnsmasq. Full fix list: [`CODE-AUDIT-2026-08-05.md`](CODE-AUDIT-2026-08-05.md).

## UI / UX polish

- **Network (SDN) page: suppress or mask the post-apply SSID+password overlay.** (Owner
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

- **i18n residuals (from v2.1.3).** Two English-only strings need a translation pass across
  the dicts: (a) the AI Advisor intro was completed in `EN.dict` (RADV_01) but the other 24
  language dicts still carry the older truncated phrasing (translated); (b) the Connections
  "Quick Look" labels (Device / Scope / State / Internal / External / Quick Look / Advanced /
  Pause) are English literals pending tokenization across the 25 dicts. [owed — cosmetic/i18n]
- **Client ID** The traffic Analyser part, if checking the last 24 hours for example, if a 
  device goes offline - it will   just show the IP address and not the name - and when the 
  device comes back online - it will update the device name.
  *(2026-08-05 note: NOT closed by the v2.1.9 name unification — the Traffic page resolves
  names live from the client list, which only carries devices networkmap currently knows.
  A long-offline device falls out of that list, so its history rows fall back to IP/MAC.
  Proper fix = have rtrafd persist a MAC→last-known-name sidecar (or resolve against
  the master `custom_clientlist` directly, which does retain named offline devices) —
  pairs with the month-view item below.)* [owed]
- **Translation Token (RU "Administration" `&shy;` artifact) — RESOLVED (be96u-only
  `65d5d4d184`), SHIPPED v2.1.6 all five models, metal owed.** `menu5_6` (RU) carried an HTML soft-hyphen ENTITY
  (`Администри&shy;рование`, added for rail wrap). The Reaper dashboard substitutes the
  token straight into HTML (entity decodes, invisible) but the **stock left-menu renderer
  emits `menuName` as text**, so the entity showed literally — hence correct on Home, raw on
  every stock page. Fixed by making the value entity-free: RU dropped the `&shy;`; the same
  latent bug in **TR `menu5_2_1`** (`&#39;`) was fixed to U+2019 (renders as an apostrophe in
  a text context, can't break quoted JS). In-place edits, dicts stay lockstep. **Rule going
  forward:** menu-label dict tokens must not contain HTML entities — the stock menu renderer
  shows them raw; use literal Unicode characters.

## Known issues (cause identified)

- **Warden "total blocked" count does not survive reboot or reflash (owner report
  2026-08-06). — INVESTIGATED 2026-08-06: BY DESIGN in the current code, NOT a
  regression; v2.1.6 only fixed the firewall-restart reset, not reboot.** The
  v2.1.6 fix (`d3779f94e4`) banks the live `RW_DROP` packet count into a baseline
  so a routine `restart_firewall` no longer zeroes the UI total — but that baseline
  lives at `RW_BASE = /tmp/rwarden/blocked_base` (rwarden.c:57), and the code
  comment says so explicitly: *"/tmp clears on reboot, so this is a live/session
  total, not cross-reboot."* stats.sh reports `baseline + live`, both volatile. So
  a reboot or reflash starts the count at zero — exactly the report.
  **Remediation (small, self-contained):** move the baseline to the JFFS cache dir
  that Warden **already uses and already survives reboot/reflash** —
  `RW_CACHE = /jffs/rwarden` (rwarden.c:58, where `sets.ipset` is persisted). Point
  `RW_BASE` at `/jffs/rwarden/blocked_base`, keep the accumulate-on-re-arm write
  (rwarden.c:294-296) and the **disable-resets-it** semantics (`unlink(RW_BASE)` at
  :586 — turning Warden off should still zero the total). Guard the write for the
  no-JFFS case (the page already surfaces a `jffs` flag). A **factory reset** wipes
  /jffs, which correctly resets the count. Note the small NAND-write cadence
  (baseline rewrites on each re-arm/stats tick — batch or throttle if it proves
  chatty). [owed — build + metal (reboot + reflash keep the total; disable zeroes it)]

- **USB Health Scanner results flash for <100 ms then vanish (owner report
  2026-08-06, v2.2.0 metal). — INVESTIGATED 2026-08-06: root cause found.** On the
  new USB Disks tab (`Reaper_USB.asp`; same code previously on `Reaper_Storage.asp`),
  `dkPoll()`'s scan-complete branch populates the results log (`dklog_<port>`
  `textContent` + `display:block`) and then immediately calls
  `dkFresh(renderDisks)`. `renderDisks()` rebuilds the whole disk panel via
  `box.innerHTML = out`, which **destroys and recreates the `dklog` element** — so
  the just-shown scan output is wiped a moment after it appears. That is the
  sub-100 ms flash.
  **Remediation:** don't clobber the log on the post-scan refresh. Options:
  (i) after `dkFresh`, re-inject the captured scan text back into the rebuilt
  `dklog_<port>` (keep the fsck output in a JS var keyed by port and restore it in
  `renderDisks`); or (ii) skip the `renderDisks` rebuild on scan-complete (the
  inventory hasn't changed after a *scan* — only after a *format*), refreshing only
  the status line; or (iii) render the scan results into a element that
  `renderDisks` does not overwrite (a detail area outside the per-disk card
  innerHTML). Option (ii)+(iii) is cleanest: scan never needs the full rebuild.
  Page-only JS, no backend change; shared page → fans to all 5 models.
  [owed — build + metal]

- **First-boot credential flow ends in a constant page-refresh loop (v2.1.6 field
  reports; present through v2.1.9) — ROOT-CAUSED + FIXED 2026-08-06 (commit
  `137d96338a`), rides v2.2.0, factory-reset METAL TEST OWED.** httpd cached the
  landing page ONCE at startup (`get_index_page` → `indexpage`); on a factory box
  that cache was `Reaper_FirstBoot.asp` and the credential flow never restarts
  httpd — `/` kept serving the wizard, whose v2.1.5 leave-guard bounced back to
  `/` → infinite reload (re-login re-entered via the same stale global in
  `login_cgi`). Fix = live recompute at both consumers + FirstBoot leaves to the
  dashboard explicitly (loop-proof even if a stale cache ever recurs). Field
  workaround for v2.1.6/2.1.9 boxes: power-cycle, then log in with the new
  credentials. **Metal owed:** factory-reset wizard end-to-end (no loop, password
  survives reboot); whether `do_chpass` (blob) kills the session token (if yes the
  hidden saveNvram apply dies → password RAM-only until reboot — decide follow-up);
  upgrade-in-place from a looping v2.1.6 box recovers without reset. Full analysis:
  [`LOGIN-LOOP-2026-08-06.md`](LOGIN-LOOP-2026-08-06.md).

- **[residual of the v2.1.3 apostrophe-XSS fix — low, optional] Unescaped `title='...'`
  attributes on the client lists.** The reported stored-XSS/garble via an apostrophe in a
  device name was fixed in v2.1.3 (patch 0311; see the changelog). Remaining defense-in-depth
  only: `client.vendor` / `deviceTypeName` are still emitted into single-quoted `title='...'`
  attributes unescaped in `client_function.js` and `dashboard/js/clientlist.module.js`, but
  those are vendor/OUI-DB-sourced, not attacker-freeform. [owed — low, optional]

- **Console error: stock ASUS privacy-policy fetch fails on the de-clouded build.**
  The browser console logs `Error fetching ASUS privacy policy: TypeError: Failed
  to fetch` — stock `asus_policy.js` `PolicyStatus()` (fired from `state.js` via a
  `setTimeout`) calls `httpApi.get(...)` to fetch the ASUS privacy policy and the
  request fails. **Cause:** Reaper is de-clouded, so that ASUS endpoint is
  removed/unreachable; the stock policy-status check still runs and throws.
  **Harmless** — console-only, no functional impact — but it's noise that a clean
  de-cloud build shouldn't emit. Fix: suppress/stub the stock policy fetch (or
  gate `PolicyStatus`) so it no longer runs, consistent with the other phone-home
  removals (see the phone-home surface map). [owed — cosmetic/de-cloud cleanup]

- **Dashboard client list fetches device icons from the ASUS CDN (`nw-dlcdnet.asus.com`).**
  `www/dashboard/js/clientlist.module.js` (~L185) does
  `fetch('https://nw-dlcdnet.asus.com/plugin/productIcons/${this.name}.png')` to pull a
  product-icon image, keyed on the device model name. **Dormant, gated:** only fires when
  the dashboard client list is viewed AND the client is an ASUS device with the default
  type icon (`this.isASUS && this.type == this.defaultType && this.name != "ASUS"`), so it
  is not automatic outbound — but it is a direct browser→ASUS-CDN request that a de-clouded
  build should not make, and it leaks the presence/model of ASUS devices to ASUS. Pre-existing
  stock behavior (not introduced by any Reaper rung); surfaced incidentally during the
  v2.1.1/v2.1.2 security review. **Fix options:** (a) drop the remote fetch and fall back to
  the local/bundled icon set (Reaper already ships icons), or (b) gate it behind a setting
  that is off by default. See the phone-home surface map (the user-triggered /
  dormant tier). [owed — de-cloud cleanup]

- **First-boot credentials wizard (shipped v1.5.5) — factory-reset metal test.** Factory
  reset → wizard appears → no page/dashboard reachable until username+password set → forced
  to the wireless page until a WiFi PSK is set → dashboard → values persist → all editable
  later; also confirm an *upgrade* (no reset) does **not** trigger it. **Known limitation
  (v1.5.5):** the WiFi step releases once WiFi is *configured* (`sdn_rl` changes), so a user
  could save it **open** and skip a PSK — optional tightening is to require a non-empty PSK
  (currently uses the stock `sdn_rl` signal for stability). Feature record in
  [`CHANGELOG.md`](CHANGELOG.md) v1.5.5; it replaces the stock forced password gate and is
  the concrete mitigation for deferred finding **H15** (see the AA26-194A section below).

- **Watchdog false wan-gw failure on ICMP-filtering first hop — RESOLVED (be96u-only
  `fc17fa9406`), SHIPPED v2.1.6 all five models, metal owed.** rwatch check #1 pinged 
  `wan0_gateway` and flagged `wan-gw` purely on ICMP failure, so a first hop that drops 
  ICMP (ISP ONT/modem at 192.168.100.1 or the PPPoE peer, 100% loss over ppp0) produced 
  a phantom "FAILURE detected: wan-gw" every tick while the WAN was fully up. Fix: on 
  ping failure, corroborate with ASUS's own WAN state (`wan0_state_t`==2 = 
  `WAN_STATE_CONNECTED`); if connected, the first hop is merely ICMP-filtering — log a 
  one-shot informative note (throttled via a `/tmp` marker, re-armed when ICMP returns 
  or the WAN drops) and do **not** flag a failure. `wan-gw` stays a real failure only 
  when the WAN is not connected (a genuine PPPoE drop flips `wan0_state_t` via wanduck, 
  so real outages still alarm).

## Known issues (under investigation)

- **VPN speedtest hang → `sched: RT throttling activated` → wireless-only drop —
  ROOT-CAUSED at source, DIAGNOSTIC TEST REQUIRED before any fix ships.** (Field
  2026-08-04 23:02, BE96U: built-in Ookla test over an active VPN, QoS off, 4 Gbps ISP —
  hung at ~1.1 Gbps; syslog `sched: RT throttling activated`; wireless clients dropped,
  wired stayed up. Distinct from the v1.7.9 cold-start retry fix and the BE98 classful-QoS
  freeze above.)
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

- **Long-Term Storage screen: "Collecting since" column shows no dates (owner
  report 2026-08-06). — INVESTIGATED 2026-08-06: not a regression, working as
  designed; needs a design decision + likely a small plumbing add.** The since
  column (`RDST_09`) is filled **only** for the **Devices** dataset and **only**
  on a durable store: `since = (ds.k==='dev' && durable && S.dev_since) ?
  fmtDate(S.dev_since) : '&mdash;'`. Verified end-to-end and present since **before
  v2.1.6** (both the writer and reader exist at the v2.1.6 tag `feadc81214`), so
  the version is not the cause: `rc/rwatch.c:218` writes `$BASE/dev.since` (epoch
  hours) on the first durable collection tick **only if the file doesn't already
  exist**, and `web.c:24090` reads it back as `dev_since`. So the dash appears
  whenever: (i) the store is **RAM** (never durable → always dash — the default),
  (ii) the **Devices** dataset was never enabled long enough for rwatch to write
  the marker, or (iii) the owner expects dates on the **other** datasets
  (traf/watch/chq/slog), which are dash **by design** — only `dev` was ever
  wired.
  **Remediation (pick one):**
  1. *Minimal / clarify:* if the owner only cares about the Devices row, confirm
     on metal that their store is JFFS/USB and the Devices dataset is on, then
     verify `dev.since` exists (`ls $store/dev.since`); if missing, the first-tick
     write never fired — add a one-line rwatch log when it stamps, and consider
     writing it the first time ANY durable dataset collects, not just dev.
  2. *Full / per-dataset (recommended if the column is meant to be general):* have
     the store writers stamp a `<ds>.since` marker per dataset (traf/watch/chq/
     slog) the first time each writes durably, extend `store_status` to emit
     `traf_since`/`watch_since`/… beside `dev_since`, and change the page's `since`
     expression to look up `S[ds.k+'_since']` for every non-locked dataset. Small,
     contained (rwatch writer + one CGI block + one JS line); no dict change.
  [owed — owner picks dev-only vs per-dataset; then implement + metal-verify]

- **MLO: individual link connections no longer shown per device (owner report
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

- **AI Mesh Search** Investigate the operation of search as it was reported 
  non-functional awhile back.  

- **BE98 Speed Test** Field reports that when QoS is enabled on the BE98 device 
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

- **The router is configured for dual-WAN failover**
  The active secondary WAN uses the 2.5 Gbps LAN port with DHCP and its own NextDNS profile.
  The future primary WAN uses the 10 Gbps LAN port with PPPoE, but it is not yet connected. It 
  has a separate NextDNS profile and DNS server addresses. The router currently fails over to 
  the active 2.5 Gbps connection. Despite only one WAN being live, both NextDNS profiles are 
  receiving DNS log entries. The expected behavior was for only the active WAN’s profile to show 
  traffic.

- **Data Logs — ROOT-CAUSED + FIXED in v2.1.5 (commit `383f9019a3`), metal owed.** The
  "JFFS/USB history resets" reports are two distinct rtrafd defects, both confirmed at
  source: (a) **USB/external lost ALL history on every reboot** — `rtrafd` loaded its db
  once at startup, but USB mounts via hotplug *after* services start, so the store silently
  fell back to RAM (never loaded) and the first hourly save then overwrote the old
  `rtraf.db` with empty rings; (b) **JFFS/internal loses the tail** — saves were hourly and
  the shutdown save needs a clean SIGTERM, so an unclean reboot (power pull / watchdog)
  drops up to 1h of recent history, which reads as "not persistent." Fix: late store
  attach (retry resolve+load at 1 Hz for 15 min, logged), a never-save-over-an-unloaded-db
  clobber guard (preserves `rtraf.db.prev`), and 15-min save cadence on USB (JFFS stays
  hourly for NAND wear). Metal: reboot with `rtraf_path=usb` → logread shows "store came
  up late - attached" and history survives; power-pull loses ≤15 min (USB) / ≤1h (JFFS).
  [owed — metal only]

- **Traffic Analyzer** Traffic Analyser also does not put the device names for every device when 
  you view say, for the past MONTH.
  *(2026-08-05 note: same root cause as the "Client ID" item above — rtrafd history stores
  only MAC/IP, names resolve live at page load, so anything not in the current client list
  shows bare. Fix together with that item.)* [owed]

## Features to add

- **Warden: explicit IPv6 enable option + broader IPv6 feed coverage. [HELD — owner
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

- **Warden: feed dedup/overlap disclosure — DONE (be96u-only `d3779f94e4`).** New dict token
  `RWDN_55` (all 25 dicts, 6189→6190 lockstep) shown under the feed checkboxes and as a
  "How Warden works" bullet: all enabled feeds merge into one de-duplicated `hash:net` set
  (`sort -u` → `ipset restore` → atomic swap), so overlapping feeds never double-block or
  bloat matching; FireHOL Level 1 already aggregates Spamhaus DROP / DShield / Feodo
  (Spamhaus still adds its IPv6 list). Translation pass owed (English seeded in all 25).

- **Firmware update check on GitHub — PHASE 1 DONE (be96u-only `56a824a5a5`), SHIPPED
  v2.1.6 all five models, metal owed.**
  Replaced Merlin's `fwupdate.asuswrt-merlin.net` check with a Reaper GitHub-hosted manifest:
  `rom/webs_scripts/reaper_webs_update.sh` (busybox sh) reads `productid` + detects variant
  (MCP ships `rmcpd`/`Reaper_Advisor.asp`, noMCP neither), greps `PRODUCTID#VARIANT` from
  `updates/manifest_3006.txt` on the AM-Reaper raw tree, compares Reaper `X.Y.Z`, and sets the
  stock `webs_state_*` nvram. `stage_release.ps1` now emits that plain-text manifest alongside
  `latest.json` (lean repo `9d2e30f`). The firmware page is de-Merlined (links → AM-Reaper
  releases) and **Main_ReaperDash.asp shows a crimson "New firmware available" badge** (server-
  rendered from `webs_state_flag`, links to the firmware page). **Opt-in preserved:**
  `firmware_check_enable` default stays `0`; scheduled check runs only when enabled, manual
  "Check" works on demand. Notify-only — never downloads/flashes. **METAL:** enable check →
  Check → badge + page show the published version; wrong-variant line never matched; note fetch.
  Root cause it fixes: every Reaper release shares Merlin base `3006.102.8`, so the stock
  numeric compare (which zeroed our `Reaper_v…` extendno) could never see a Reaper update.
- **Firmware-upgrade page cleanup (owner request 2026-08-06). — INVESTIGATED
  2026-08-06: (c) is already correct; (a) and (b) confirmed still owed.** Findings
  against the current tree (`Advanced_FirmwareUpgrade_Content.asp` is the shipped
  page):
  - **(c) Scheduled Yes/No — ALREADY WIRED TO REAPER, no work needed.** The
    radio pair at lines ~2149-2150 is `name="firmware_check_enable"`, and
    `watchdog.c:12363/12381` gates the scheduled run on `firmware_check_enable`;
    the installed `/usr/sbin/webs_update.sh` **is** `reaper_webs_update.sh`
    (`rom/Makefile:180` copies it over the Merlin one), which checks the AM-Reaper
    manifest and never downloads/flashes. Default stays `0` (opt-in). Just
    **metal-verify** the toggle persists and a scheduled tick sets `webs_state_*`.
  - **(a) Security Update section — STILL PRESENT, remove it.** Lines ~2064-2092
    render `#switch_security_update_enable` bound to `httpApi.securityUpdate`
    (httpApi.js:1143) — stock TrendMicro signature-update cloud machinery, dead on
    the de-clouded build. Delete the section (and the now-unused httpApi shim if
    nothing else references it).
  - **(b) Check button + the STALE STOCK SCHEDULER — STILL STOCK, rework.** The
    page ALSO still carries the Merlin auto-firmware scheduler UI:
    `webs_update_enable` / `webs_update_time` / `check_beta` wiring
    (lines ~179-346) is separate from the reaper `firmware_check_enable` toggle,
    so the page has **two** update-scheduling surfaces — confusing and half-dead.
    Confirm what the manual **Check** button submits (stock `webs_update_enable`
    apply vs a reaper check trigger) and that the result panel reads the
    Reaper-set `webs_state_*` nvram; remove/replace the leftover
    `webs_update_enable`/`webs_update_time`/`check_beta` stock scheduler so only
    the reaper `firmware_check_enable` control remains.
  **Remediation:** delete the Security Update block (a); excise the stock
  `webs_update_*`/`check_beta` scheduler + point the Check button at the reaper
  flow (b); leave the `firmware_check_enable` toggle as-is (c). Page-only edit to
  a stock ASP that ships as-is (no sysdep variant for this page — verify with the
  www Makefile per standing rule 33). Fold into Phase 2 (native `Reaper_Firmware.asp`)
  if that lands first. [owed — build + metal]

- **PHASE 2 — native Reaper firmware page (`Reaper_Firmware.asp`) with in-GUI download + flash.**
  (owner ask 2026-08-04) Replace the whole stock firmware tab with a Reaper-native page (shell/
  inject-skip, theme tokens, dict lockstep — the `Reaper_QoS`/`Reaper_Traffic` convention). Surface
  functions the stock page **disables** (`afwupg_support=false`, `betaupg_support=false`): one-click
  download of the published `.pkgtb` from `webs_state_url` → verify SHA256 (already in the manifest)
  → flash; show the release note inline; guard model+variant so a noMCP box can't pull an MCP image;
  optional rollback awareness. Pulls in image-signing / GPL-delivery considerations (was the deferred
  Phase 2). Depends on Phase 1's manifest + nvram wiring (done). [owed — build]
- **NORTH STAR — progressively replace stock GUI pages with Reaper-native ones.** (owner direction
  2026-08-04) Over time, migrate stock ASUS/Merlin pages to Reaper-native equivalents (own theme,
  de-clouded, only the functions we want exposed), as already done for Dashboard/QoS/Traffic/Wireless/
  GK/Warden/Devices/Advisor/Conn/QoSDiag. Firmware tab (Phase 2 above) is the next candidate. Track
  per-page migrations here as they're scoped. [ongoing]

- **Staged ("batch") changes — one save, minimal restarts.** Owner request. Today each control
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

- **Remote syslog push/fetch.** The router can already send its log to a remote
  collector (send-only). Add the ability to **push to / be fetched by** analytics
  systems — most SIEM/analytics pipelines are push-based.

- **NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST
  baseline.

- **Diag: regulatory-mismatch warning.** Make `reaper_diag` (and possibly a Wireless-page
  hint) print an explicit `WARN: territory_code=EU/xx but wlX_country_code=US` style line
  when the factory territory and the per-radio country codes disagree — self-documents
  gray-market / region-switched units in field reports. Field-observed 2026-07-28 on two
  EU GT-BE98s (`territory EU/01`, all radios `US`); also a suspect in the "Wi-Fi 7 client
  refuses 6 GHz, camps on 5 GHz @80 MHz" report (strict EU clients may reject a US country
  IE). Read-only nvram compare, no behavior change — firmware must never auto-alter a
  unit's regulatory nvram. [shelved]

## Code-scan findings 

**Deliberately deferred (with reason), still open:**
- **`poll_fcache` O(n²)→hash pairing** (`rtrafd.c`). Bounded to ≤1536 flows every 5 s and
  it sits in the metal-validated per-client accounting path — a rewrite of a millisecond-
  scale loop isn't worth the regression risk. Revisit only if a flow-heavy box shows real
  cost. [shelved]

- **`poll_classes` 7× `tmctl` popen batch** (`rtrafd.c`). Metal already measured 2–3 % CPU
  at the class-poll cadence; treating this as a non-issue per the prior finding. [shelved]

**Pre-release code review 2026-08-02 — remaining item:**
- **GDX pool watchdog field-proving.** The accelerator pool-drain check is opt-in (`rwatch_gdx`,
  v2.1.0). Confirm the `/proc/gdx/skb_idx` read is non-destructive under sustained polling on
  hardware before it can be considered for default-on again. [owed — metal]

**Full code audit 2026-08-05 — deferred items (see [`CODE-AUDIT-2026-08-05.md`](CODE-AUDIT-2026-08-05.md)):**
The confirmed audit findings were fixed in v2.1.9; five items were deliberately deferred.
*(Re-reviewed later the same day: all five confirmed still open by design — D1/D3/D4 are
cross-page refactors to do WITH the native-page migration and its on-device verification,
not piecemeal on a just-shipped fleet; L1/L3 remain shelved on their recorded rationale.)*
- **D1 — shared device-name resolver JS (5→1).** The `get_clientlist`+`nickName||name` resolver is
  reimplemented in five pages (DHCP/Conn/Traffic/QoS/Dashboard) with different keying. Extract one
  `reaper_names.js`. Best done in the **native-page migration** (cross-file refactor + on-device
  verification). [owed — migration]
- **D3 — unify byte/rate formatters across pages** (SI vs binary drift). "Fixing" changes displayed
  values on some pages, so pair it with the migration rather than change output piecemeal. [owed — migration]
- **D4 — consolidate the per-page `:root` theme tokens/components** (two token vocabularies for the
  same hexes across 13 pages). Visual-regression risk; do it with metal verification in the
  migration. [owed — migration]
- **L1 — spurious leading `<` in the set_name/set_reserve RMW output.** Cosmetic, verified-harmless;
  not worth re-touching the just-stabilised `custom_clientlist` RMW. [shelved]
- **L3 — function-local `static` snapshot arrays in `do_reaper_dev_cgi` aren't re-entrant.** Latent
  only (httpd serialises these requests); a malloc refactor of the multi-return CGI would add leak
  risk to fix a can't-happen case. [shelved]

## Documentation

- **Note the non-functional retained features.** Document that the firmware
  update-check and the (removed) security-check UI do nothing on Reaper and are
  retained only for potential future use.

- **Annotate** the system defaults.

- **Write a user guide** for other users.

## Platform / expansion

## Known issues (Cannot Remediate)

- **Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul
  BSS is still created even when every feature that would use it is disabled, spamming
  the log with RADIUS codes for an unused radio. Traced to a **closed-source Broadcom
  blob**; a boot-time script to suppress it based on device settings did not work and
  was reverted. [blocked — blob; risk-accepted]