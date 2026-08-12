# RT-BE Series "Reaper" — Backlog

Working list of what's left to accomplish, grouped by area. Status is noted where
known: **[owed]** (must be done), **[blocked]** (external cause), **[shelved]**
(deliberately deferred), **[cosmetic]** (polish, non-blocking).

**Priority** (by impact on user-facing functionality): **[P1]** core function
broken or at risk for users · **[P2]** degraded function, meaningful annoyance, or
privacy exposure · **[P3]** cosmetic, polish, internal quality, or deferred-by-decision.

> Applied security fixes are tracked in [`REAPER-FIXES.md`](REAPER-FIXES.md); the
> per-version history is in [`CHANGELOG.md`](CHANGELOG.md). Completed items are moved
> to the changelog and removed from this file. **This backlog lists only work that is
> not yet done** — on-hardware validation of already-shipped features is not tracked here.

---

## Open bugs / under investigation

- **[P1] VPN speedtest hang → `sched: RT throttling activated` → wireless-only drop —
  ROOT-CAUSED at source; a decisive on-box diagnostic is the next step before any fix.**
  (Field 2026-08-04, BE96U: built-in Ookla test over an active VPN, QoS off, 4 Gbps ISP —
  hung at ~1.1 Gbps; syslog `sched: RT throttling activated`; wireless clients dropped,
  wired stayed up.)

  - **Cause chain (stock-inherent, not Reaper):** the platform boots with
    `sched_rt_runtime_us=99000/100000` and `CONFIG_RT_GROUP_SCHED` off, so blowing the
    99 ms/100 ms RT budget on a CPU throttles **every** RT task on that core. Broadcom's
    `rtpolicy` promotes **ksoftirqd to SCHED_RR prio 5** and pins `bcmsw_rx`/`spu_rx`/`pdc_rx`
    (RR/5) to CPU0. VPN crypto is not runner-accelerated → runs in softirq → RT-promoted
    ksoftirqd saturates a core at ~1.1 Gbps → throttle fires → the Wi-Fi driver kthreads (RT,
    policy set inside the closed `wl.ko`) freeze with it → wireless drops; wired survives
    because it is runner-offloaded. Reaper daemons request no RT priority (verified).

  - **Decisive diagnostic (no build):** on-box, demote ksoftirqd to normal scheduling —
    `chrt -o -p 0 <pid of ksoftirqd/N>` per thread (or `echo -1 > /proc/sys/kernel/sched_rt_runtime_us`)
    — then rerun the same VPN speedtest. Hang + wireless drop gone ⇒ confirms the chain. Record
    **which VPN engine** was active (WireGuard/OpenVPN ⇒ ksoftirqd path; IPSec ⇒ the SPU
    `spu_rx`/`pdc_rx` RR/5 threads on CPU0 instead).

  - **Candidate fix (after the diagnostic confirms):** remove ksoftirqd's RT promotion in
    `rtpolicy/scripts/rt_settings_kthreads.txt` (restores the mainline default, keeps the RT
    throttle as a safety valve); optionally + affinity separation and RPS spread for tunnel
    softirq. `sched_rt_runtime_us=-1` rejected as the primary fix (removes the safety valve).

- **[P1] BE98 Speed Test crashes/freezes with class-based QoS enabled.** Field reports that with
  QoS enabled on the BE98, the speed test crashes — not everyone is affected (config-dependent).
  Owner also observes a **momentary freeze on the built-in speed test in HW Classful mode
  (`qos_type=11`, the 8-queue WRR scheduler) but NOT in the HW Classless modes**.

  - **Source trace (blob/metal-bound):** the built-in Ookla test is **router-originated** traffic;
    its WAN egress traverses `QOSO` at `POSTROUTING`, so in type-11 it is CONNMARK'd into the
    default class → default egress queue and is subject to that queue's PI2 shaper + the WRR
    schedule + the **aggregate port shaper** (`setportshaper=qos_obw`). type-10 has none of these
    (qid0 shaper only) — which is why the freeze is classful-only. Both `ookla_exec` and the rdpa
    runner are **blobs** — not safely fixable from the auditable source.

  - **Metal diagnostics to split it:** run the built-in test on type-11 while capturing
    `logread`+`dmesg`+`fc status`+`tmctl getqstats`; repeat on type-10 (control); run an
    **external/LAN-client** test under type-11 (if it does NOT freeze, the router-local path is the
    confound); set `qos_pshaper=0` or raise `qos_obw` to line rate → re-run. **Interim workaround:**
    run the built-in test with QoS on a classless mode or off, or use a LAN-client/external test.

- ~~**[P2] Smart Connect Rules — band shows `- -` for every field (field 2026-08-08, BE96U tri-band).**~~
  **CLOSED 2026-08-11 — NOT A BUG on the owner's box. Confirmed from live nvram; hypothesis (a) refuted
  by simulation. Two unrelated real defects found and fixed in tree along the way (unbuilt).**

  - **Live nvram, RT-BE96U v2.3.4, 2026-08-11:** `wlnband_list=2g1<5g1<6g1`, `smart_connect_selif_x=10`,
    `smart_connect_selif=10`, `smart_connect_x=2`. `shared.h:5575-5579` defines the mask bits in C —
    `SMRTCONN_SEL_2G 0x0001`, `SMRTCONN_SEL_5G 0x0002`, `SMRTCONN_SEL_5G2 0x0004`, `SMRTCONN_SEL_6G
    0x0008`, `SMRTCONN_SEL_6G2 0x0010` — so **10 = 0x0A = SEL_5G | SEL_6G**: Smart Connect steers
    between 5 GHz and 6 GHz with **2.4 GHz deliberately excluded**. Running that exact config through
    the simulator reproduces the screen precisely: 2.4 GHz `- -`, 5 GHz values, 6 GHz values.
    `smart_connect_x=2` is *derived* from the mask by `Advanced_Wireless_Content.asp`
    (`binaryString.slice(-1) === "1" ? "1" : "2"` — "with 2.4 GHz return 1, without 2.4 GHz return 2");
    `1010` ends in `0` → `2`. All three nvrams are mutually consistent — the page was reporting the
    configured state correctly. The band-slot interpretation is the **firmware's own**, not a GUI
    convention.
  - **Note on the original 2026-08-08 "5 GHz-1" sighting:** this box's labels are "2.4 GHz / 5 GHz /
    6 GHz" — `wl_nband_title` appends `-1`/`-2` only when a band type occurs more than once, which
    needs two 5 GHz radios. So that report was either informal naming of the 5 GHz column or a
    different (quad-band) unit. Re-open with its `nvram show` output if it recurs.

  - **What `- -` actually means.** It is emitted at 13 sites in `Advanced_Smart_Connect.asp`, every one
    of them gated on `isSmartConnectSelifBand(bandList[i])` being false — i.e. **that band's slot bit is
    clear in `smart_connect_selif_x`**. It does *not* mean the band has no policy: the page has already
    parsed `wl<n>_bsd_steering_policy` &co. into `bsd_steering_policy_array[i]` for **every** band before
    it decides to print `- -`.
  - **The bit index is a BAND SLOT**, not a wl unit and not a position among the bands present — slots
    are the fixed five-element `bandName = ["2G","5G1","5G2","6G1","6G2"]` in `state.js`. On a tri-band
    2.4/5/6 box, 6 GHz therefore needs **bit 3**, so masks **3 and 7 render identically** (bit 2 is
    `5G2`, a radio that does not exist). Any code deriving the mask as `2^N-1` from the band count writes
    7 and silently means "2G + 5G1 + phantom", never 6 GHz. Reaper already fixed its own write path to
    compute by slot (→ 11); simulation confirms 11 lights all three bands.
  - **(a) label/mapping mismatch — REFUTED.** A simulator was built from the *real* `bandName`,
    `get_wl_unit_by_band`, `wl_nband_title` (state.js) and `bandList` + `isSmartConnectSelifBand`
    (the page), then run across the dual / tri-2.4-5-6 / tri-2.4-5-5 / quad matrix. **Labels and cells
    agree in every configuration** — the header uses `wl_nband_title[get_wl_unit_by_band(bandList[i])]`
    and the policy arrays are remapped through the *same* shift, so no column can show another radio's
    policy. Also: `wl_nband_title` only appends `-1`/`-2` when a band type occurs more than once, so a
    column literally labelled **"5 GHz-1" implies the box has two 5 GHz radios** — on a 2.4/5/6 BE96U it
    renders plain "5 GHz".
  - **(b) not-a-bug — CONFIRMED for the 6 GHz column.** `shared/defaults.c:1576` ships
    `smart_connect_selif_x = "3"` for `RTCONFIG_HAS_6G` models, commented *"don't invole 6GHz band in
    smart connect by default"*. So on a BE96U, **6 GHz showing `- -` out of the box is stock intent.**
    Changing that default alters RF behaviour for every user — owner's call, not done.
  - **`smart_connect_selif_x` is GUI-side selection state.** The only C consumer,
    `gen_bcmbsd_def_policy()`, is `extern`-declared with **no definition in the auditable source** (a
    Broadcom blob) and is called only on the `reset_bsd_def` path (`rc/init.c:26281`) and from the manual
    `rc bsdsel` CLI (`rc/rc.c:946`) — which reads `smart_connect_selif`, **not** the `_x` variable the
    GUI reads and writes. Nothing syncs the two.
  - **Fixed in tree.** (i) **Real markup bug** in `genSteerLoadBalance()`: the suppressed branch opened a
    `<td>`, wrote `- -`, then `continue`d — skipping the `code += '</td>'` at the loop foot, so the cell
    was never closed and later cells nested inside it. All 13 sites now route through one
    `scExcludedCell()` helper that emits a complete cell. (ii) **The bare `- -` now explains itself** —
    a hover title on the cell plus a note above the tables (shown only when a column is actually
    suppressed) saying the band is not in the Smart Connect group, that its policy is *not* lost, where
    to change the selection, and that 6 GHz is excluded by default on this model. Verified: inline JS
    parses, no bare emitters left, `<td>` opens == closes, all 13 sites routed, note wired into
    `initial()`.
  - **Reference table** (`wlnband_list=2g1<5g1<6g1`) for reading any future screenshot of this page:
    mask **3 or 7** → 6 GHz `- -`; **10** → 2.4 GHz `- -` (the owner's config); **11 or 15** → all three
    editable; **9** → 5 GHz `- -`; **2** → 2.4 and 6 GHz `- -`. Simulator kept at
    `scratchpad/smartconnect_sim.js` — it extracts the real `bandName` / `get_wl_unit_by_band` /
    `wl_nband_title` / `isSmartConnectSelifBand` from the tree, so it stays honest as the code changes.
  - **Latent trap recorded (not currently reachable).** `Advanced_Wireless_Content.asp`'s mask builder
    has a `return 7;` fallback. On a tri-band 2.4/5/6 box, 7 = 2G + 5G + **5G2**, a radio that does not
    exist — it silently drops 6 GHz out of the steering group. It is dead code today (guarded by
    `smartConnectEnable`), but any future edit to that guard would resurrect it. Same arithmetic hazard
    as the `2^N-1` mask Reaper already replaced with a slot-indexed loop in `Advanced_Smart_Connect.asp`.

- **[P2] AI Mesh Search** — investigate; reported non-functional a while back.

- **[P2] Dual-WAN failover: both NextDNS profiles receive DNS logs though only one WAN is live.**
  Secondary WAN (2.5 Gbps, DHCP, its own NextDNS profile) is active; the future primary (10 Gbps,
  PPPoE) is not yet connected. With only the secondary live, **both** NextDNS profiles show traffic;
  expected only the active WAN's profile to log.

## UI / UX polish

- **[P3] Loading/Restarting overlay — native redesign remains.** Full-screen coverage + nav/header
  blocking during an apply/reboot is done (v2.2.5, refined v2.3.0); the overlays are now anchored to
  the browser viewport rather than the framed document (fixed in tree, rides the next rung — the shell
  publishes the frame's visible slice as `--rv-top`/`--rv-h` and re-anchors `#Loading`, `#LoadingBar`
  and the Reaper pages' own overlays to it). Measured in a headless browser against the shipped
  block, 1200×900 window, long page scrolled to y=2000: the stock "please wait / N%" block moved from
  **1693 px above the top of the screen** to the centre of the visible area, and a Reaper page's flash
  veil from 416 px above it to the same place. Remaining: convert these modals to Reaper-native designs
  (do with the native-page migration), and confirm the anchoring **on the router** with the real pages.
  [owed — migration]

- **[P3] Loader z-index raise is class-wide (watch-item).** The z-index bump was applied to the shared
  `.popup_bg` class, so it also raises `#hiddenMask` (the confirm-dialog backdrop) — benign/positive.
  Watch-item: if any apply/error flow ever surfaces an in-page (non-native) `form_style` modal *while
  the loader is displayed*, it would render behind the loader. Scope the class to `#Loading` only if a
  concurrent-modal case turns up. [watch — cosmetic]

- **[P3] SDN Wi-Fi-key mask can be bypassed by an SSID containing a literal `<b>` tag (watch-item).**
  The shared `state.js showWlHintContainer()` injects the SSID into `innerHTML` unescaped, so an SSID
  literally containing `<b>…</b>` would shift the bold-element index and leave the key visible. Only
  weakens the *new* privacy feature (never a crash or XSS), and the root cause is the pre-existing
  unescaped-SSID behavior in the **shared** `state.js` (out of scope of the mask's design). Optional
  hardening: mask the LAST `<b>` per row instead of index 1. [watch — cosmetic/privacy]

- **Addons** Currently when a user has addons the nav menu buttons for Addons is not showing. 
  Rearange the nav menu and add logic to deal with addon nav menu selections. [Requires_Research]

- ~~**DHCP Leases** The DHCP Leases Log GUI does not always show the "Device Name" field even though
  it exists, often showing "__" as the Device Name. The HostName field is always shown. In menu option
  for "Devices", it shows the device name in contrast, where it is defined for every host.~~
  **ROOT-CAUSED + FIXED in tree 2026-08-11 (unbuilt, METAL OWED).** [DONE]

  - **Cause — wrong source, not a missing name.** The Device Name column was an entirely client-side
    overlay: `Main_DHCPStatus_Content.asp` fetched `appGet.cgi?hook=get_clientlist()` and looked each
    lease MAC up in it. That hook's universe is **networkmap's shared-memory client table**
    (`httpd/web.c`, `shmget` on `CLIENT_DETAIL_INFO_TABLE`); `custom_clientlist` is consulted there only
    to *decorate* entries that table already holds. So a device that holds a DHCP lease but is missing
    from networkmap's table — aged out, or never catalogued; **networkmap is a closed blob, so its
    retention rules are neither inspectable nor fixable** — produced no entry at all, the lookup missed,
    and the cell fell back to an em-dash (the "__" in the report). `Reaper_Devices.asp` and the
    Gatekeeper page read `custom_clientlist` **directly** (`gk_client_name()`), which is exactly why they
    showed a name for every host. The Hostname column always worked because it comes from the lease file
    itself. It is a source mismatch, not a naming bug — the earlier name-unification rung (`d8fe13ba12`)
    added the column but wired it to the networkmap-backed hook.
  - **Fix.** `ej_get_leases_array()` (`httpd/data_arrays.c`) now resolves the admin-assigned name
    server-side from `custom_clientlist` via a new `lease_client_name()` (mirrors `gk_client_name()`,
    case-insensitive MAC compare — dnsmasq writes lowercase, `custom_clientlist` stores uppercase) and
    appends it as the **last** field of each row, so existing column indices and the MULTILAN `vlanid`
    slot are untouched. The page pops it off and uses it first, keeping the `get_clientlist()` overlay as
    a **second** source so networkmap's auto-derived names still appear for devices never renamed; the
    em-dash now means genuinely no name from either source. Only `Main_DHCPStatus_Content.asp` consumes
    `leasearray` (verified), so appending a field is safe.
  - **Two escaping defects fixed on the way past.** The lease hostname — chosen by any LAN client — was
    written **raw** into a JS array literal, so a single quote in a hostname broke the array and blanked
    the whole page. And the table API writes every cell with jQuery `.html()` (`js/table/table.js`), so
    that hostname landed in an **HTML sink** — this page is an instance of the DHCP-hostname stored-XSS
    class recorded as H1 in [`code-audit-2026-07-31-inherited`]. Both fields now go through a new
    `lease_js_escape()` that covers `' " \`, drops control characters, and emits `<` as `\x3c` (quote
    escaping alone cannot help: a literal `</script>` ends the script element in the HTML parser before
    any JS is parsed), and the page HTML-escapes the hostname cell before rendering. **Note:** this
    closes *this page's* instance only — H1 also covers the networkmap → 3-admin-view path, still open.
  - **Verified without a build:** the real `show_leases()` was extracted and run against both row shapes
    (plain and MULTILAN) — 13/13 checks, every column under its correct header, custom name beating the
    overlay, overlay used when there is no custom name, em-dash only when truly nameless, hostile
    hostname HTML-escaped. The real `lease_client_name()` was compiled and exercised on actual
    `custom_clientlist` tuple shapes — 12/12 (9-field and 3-field tuples, lowercase/mixed-case MACs,
    absent MAC, empty list, malformed tuple, empty name, 32-char truncation). The real `lease_js_escape()`
    was compiled and its output confirmed to contain no raw `</script`, to parse as JavaScript, and to
    decode back to the exact original string.
  - **Metal owed:** confirm the Device Name column populates for a host that is named in Devices but
    currently offline / not in networkmap; confirm a client with a quote or angle bracket in its DHCP
    hostname renders literally and does not blank the table. [DONE]

## Features to add

- **Research** Integrate Suricata or Snort (IDS/IPS) optimized for multi-threading, or use eBPF 
  (Extended Berkeley Packet Filter) for lightweight, kernel-level traffic analysis.

- ~~**UPNP** Research advanced UPNP packages.~~ **DONE 2026-08-11 — evaluated, then fixed in tree
  (unbuilt, METAL OWED). Three functional fixes + one hardening fix; no package change.**

  **Evaluation result: there is nothing newer to move to.** The tree already carries miniupnpd
  **2.3.10 + post-release git** (Changelog to 2026/06/16, via Merlin `9cb5d563f4`); upstream's newest
  *tagged* release is still 2.3.10 (2026/03/24). UPnP Forum → OCF in 2016 and **IGD:2 (2010) is still
  the latest gateway spec — there is no IGD:3**. The genuinely modern protocol is **PCP (RFC 6887)**,
  and miniupnpd already implements it (`ENABLE_PCP`, gated on `upnp_mnp`, default on) — it was simply
  never surfaced. No credible alternative daemon exists (OpenWrt/pfSense/OPNsense/DD-WRT/FreshTomato
  all ship miniupnpd); the in-tree `libupnp-1.3.1` is a library for `wsc_upnp`/WPS, not an IGD daemon.
  **The breakage was all in ASUS's wiring around the package.** [DONE]

  - **U1 [P1] — every firewall rebuild silently killed all live mappings.** `firewall.c` applies its
    rulesets with `iptables-restore` *without* `--noflush`, and the payloads declare `:VUPNP - [0:0]`,
    `:PUPNP - [0:0]`, `:FUPNP - [0:0]` → every rebuild flushes every UPnP/NAT-PMP/PCP mapping (~29
    `restart_firewall` sites: WAN reconnect, DDNS, VPN toggles, saving any firewall/port-forward
    setting, NAS changes, watchdog — plus Reaper's Warden/Gatekeeper arming). The only recovery hook,
    `reload_upnp()`, sent **SIGUSR1**, whose handler only sets `should_send_public_address_change_notif`
    — it re-adds nothing. miniupnpd kept the mappings in memory and in `/tmp/upnp.leases` and kept
    answering clients *"that mapping already exists"*, so clients never retried and the GUI still listed
    them, while zero packets forwarded. `clean_ruleset_interval` only ever *removes* rules. Silent,
    non-self-healing, reported healthy by every layer — the actual "UPnP is broken" field report.
    **Fix:** `reload_upnp()` now does a real restart via `notify_rc("restart_upnp")` (async — `start_upnp()`
    can block 5 s on the `RTCONFIG_GETREALIP` probe). miniupnpd writes its lease file on clean shutdown
    and `reload_from_lease_file()` re-adds every mapping at startup **with remaining lifetime**
    (`LEASEFILE_USE_REMAINING_TIME` is compiled in), so a stop/start restores exactly what was flushed.
    Same approach OpenWrt uses.[DONE]
  - **U2 [P2] — the IGDv2 daemon was invisible to three call sites.** `pidof()`/`killall()` are exact
    name matches (`shared/process.c:71`) but the IGDv2 build runs as `miniupnpd-igdv2`. `stop_upnp()`
    killed both names; `reload_upnp()` and two NAS/USB paths asked only for `miniupnpd`. **Fix:** new
    `pidof_upnp()` helper checks both, used at all sites.[DONE]
  - **U3 [P2] — the "IGDv2 (IPv6 pinhole)" toggle silently cost IPv4 features.** `--igd2` was passed
    only to the `miniupnpd-igdv2` build, so leaving pinholes off (the default) also dropped IPv4 clients
    to **IGD:1**, losing `AddAnyPortMapping` ("that port is taken, give me any free one" — the
    two-consoles / two-torrent-clients collision, made more likely here because `CHECK_PORTINUSE` is on)
    and `GetListOfPortMappings`. **Fix:** the default daemon is now built `--igd2` too. Verified by
    preprocessor probe that `--igd2` *without* `--ipv6` leaves **only** `IGD_V2` + `ENABLE_PCP` on —
    `ENABLE_6FC_SERVICE`/`ENABLE_UPNPPINHOLE` are nested inside both `#ifdef IGD_V2` and
    `#ifdef ENABLE_IPV6`, so every pinhole path is compiled out. Backward-compatible: `UPNP_STRICT` is
    unset, so `minissdp.c` matches M-SEARCH by prefix and answers IGD:1 searches with an IGD:1 ST per
    UDA v1.1. The toggle now means only what its name says.[DONE]
  - **U4 [P2, security] — UPnP could hijack the router's own inbound service ports.** The shipped
    default emitted `allow 1-65535` (`upnp_min_port_ext` defaulted to `1`), making the `else` branch
    that promises *"by default allow only redirection of ports above 1024"* unreachable. The deny list
    covered virtual servers, the HTTPS admin port, WebDAV, AiCloud and DownloadMaster — but **not**
    OpenVPN/WireGuard/IPSec/SSH, and the plain-HTTP admin deny was dead code behind `#if 0` (`enable`
    was declared inside the HTTPS-only block, so it could not have compiled). Since VUPNP hooks
    `nat/PREROUTING`, ahead of the routing decision, a LAN host could map ext:51820 → itself and
    intercept inbound WireGuard; `secure_mode=yes` does not help, because mapping the VPN port *to
    itself* is the attack. **Fix:** `upnp_min_port_ext` default 1 → 1024, the `#if 0` HTTP-admin deny
    repaired, and new `upnp_protect_svc` (default 1) emits denies for the router's own OpenVPN,
    WireGuard, IPSec, SSH and web-admin ports regardless of the allowed range (so it also protects
    existing boxes still set to 1).[DONE]

  **GUI:** `Advanced_WAN_Content.asp` — pinhole row relabelled *"UPnP: Allow IPv6 pinholes (IGD:2
  firewall control)"* with a note that IPv4/PCP are unaffected, and a new *"UPnP: Protect router service
  ports"* Yes/No row, both wired into `display_upnp_options()`.[DONE]

  **Metal owed:** map a port from a console/client, force `restart_firewall` (e.g. save a firewall
  setting), confirm the mapping still forwards; confirm a second client requesting the same port gets a
  different one (AddAnyPortMapping); confirm a UPnP request for the WireGuard port is refused.
  **Build note:** `miniupnpd/config.h` is a generated artifact regenerated only when `shared/version.h`
  is newer — it has been deleted in-tree so the next build picks up `--igd2`.[DONE]

- ~~**First Boot** The Reaper first boot continues to be problematic. Investigate and improve functionality.~~
  **ROOT-CAUSED + REWORKED in tree 2026-08-11 (unbuilt, FACTORY-RESET METAL OWED).** Goal set by owner:
  the Reaper modal is the **only** first-boot surface, and it must force **both** the admin
  username/password **and** the Wi-Fi password before the rest of the GUI is reachable (no-default-
  credentials baseline — ETSI EN 303 645 / PSTI, the "safe router" recommendation).

  - **Why the previous attempts kept failing — two structural holes, not a logic slip.**
    1. **The Wi-Fi step was never reached.** The credential step ended with
       `top.location.href = "/Main_ReaperDash.asp"`, and the dashboard **deliberately does not load
       `state.js`** (it carries its own credential guard instead). The Wi-Fi gate lived *only* in
       `state.js`. So the moment credentials were set, the box landed somewhere the Wi-Fi gate could
       not run — and sailed into the GUI on the factory Wi-Fi password. That alone explains the
       "still not working" reports.
    2. **The gate was bypassable by URL.** Enforcement was entirely client-side, but only **128 of the
       245** `.asp` pages carry a `state.js` include — typing the URL of any of the other 117 walked
       straight past the wizard.
  - **Fix — enforcement moved to the one chokepoint that sees every request: httpd.**
    New `reaper_firstboot_pending()` / `reaper_firstboot_allowed()` in `httpd/httpd.c`, called from
    `handle_request()` just after the Gatekeeper captive intercept. Any `.asp`/`.htm` load is bounced
    to the wizard while first boot is incomplete. **Page loads only** — CGIs, assets and the
    `update_*` pollers are untouched, and the cheap string tests run before any nvram read.
    Allow-list: the wizard, `Main_Login`/`Logout`/`Nologin`, `find_device`,
    `Advanced_Wireless_Content.asp` (the wizard frames it) and `QIS_`/`amas`/`cfg_onboarding` so
    **AiMesh onboarding keeps working**.
  - **The wizard now owns both steps.** `Reaper_FirstBoot.asp` leaves only when credentials *and*
    Wi-Fi are done; step 2 activates the previously-dead `#step2bar` and **frames the stock wireless
    page inside the Reaper card**. That was deliberate: this model is `RTCONFIG_MULTILAN_MWL`, so the
    main Wi-Fi is SDN-driven (`sdn_rl` / per-band profiles) — hand-rolling a PSK write here is exactly
    how a setting ships that *looks* saved and silently is not. The wizard owns the chrome and the
    exit; the apply stays the proven stock path. It polls `w_Setting` and leaves to the dashboard when
    it flips. `state.js` gates 2 and 3 now target the wizard instead of the stock page, so there is one
    surface and one place that decides first boot is finished.
  - **Lockout safety** (this gate can strand a user in their own router if it misfires):
    fires only from **live** state, so an already-configured/upgraded box never sees it; the Wi-Fi
    condition applies to **router and AP modes only** (`sw_mode` 1/3) because a repeater/media bridge
    legitimately leaves `w_Setting=0` — that exclusion is mirrored in all four layers; and
    `reaper_fbdone=1` is an unconditional escape hatch honoured by the C gate, `state.js` and the
    dashboard guard alike (`nvram set reaper_fbdone=1 && nvram commit` over SSH). It is deliberately
    **not** written by the wizard — the gate opens on its own when the live conditions clear, so there
    is no new write path to get wrong.
  - **Verified without a build:** a state-machine simulator (`scratchpad/firstboot_sim.js`) models all
    four redirect layers and walks each scenario to a fixed point, **failing on any cycle** — the
    historical failure mode here (v2.1.2 dead-end, v2.1.6 refresh loop). **24/24 across factory reset,
    credentials-set/Wi-Fi-pending, both-done, upgraded box, escape hatch, repeater mode, theme
    kill-switch and operator-forced change — no loops.** It caught two real bugs in the first cut (the
    escape hatch was ignored by `state.js`; the repeater exclusion was missing from the dashboard guard
    and the wizard). Plus: inline JS of both pages parses, `state.js` parses after ASP substitution,
    all 22 wizard tokens resolve, the new C functions balance and the call site is wired.
  - **Files:** `httpd/httpd.c`, `shared/defaults.c` (`reaper_fbdone`), `www/Reaper_FirstBoot.asp`,
    `www/Main_ReaperDash.asp`, `www/state.js`, 25 dicts (`RFB_15`/`RFB_16`, lockstep 6312).
  - **METAL OWED (factory reset, all of it):** wizard is the only surface; dashboard and a random
    deep-link URL both bounce to it; step 2 appears after credentials and the framed wireless apply
    sticks; the wizard exits once `w_Setting` flips; new credentials survive a reboot; an AiMesh
    add-node still runs; a repeater-mode box is never gated; `reaper_fbdone=1` frees a wedged GUI.

- **Firmware Mesh Nodes** Add a feature to be able to see mesh nodes firmware version from the main 
  hub in the firmware menu. This feature should also allow the user to click on each one and chose the 
  file to update the firmware with or go directly to the node and flash it natively.

- **[P2] NATIVE FIREWALL SUITE — replace the stock Firewall menu with Reaper-native pages + add engineer features.**
  Owner-approved (2026-08-08) design: a native
  `Reaper_Firewall.asp` hub replacing all four stock tabs (General / Network Services / URL /
  Keyword) plus new tabs — **Status** (live v4+v6 chains + hit counters), **custom Rules** engine
  (Basic form + Advanced DSL, dual-stack, `rc/reaper_fw.c` + `reaper_fw.cgi`, re-apply hook),
  **Egress** control (IoT containment, outbound geo), **Logging** viewer — all with
  **commit-confirm auto-rollback** and anti-lockout invariants. Backend stays iptables/ipset.
  Phased 0→3; each phase build + on-metal (rmcpd lab MCP as the test harness) + fleet fan-out.
  [owed — build; live inspection done]

- **[P3] NORTH STAR — progressively replace stock GUI pages with Reaper-native ones.** Over time,
  migrate stock ASUS/Merlin pages to Reaper-native equivalents (own theme, de-clouded, only the
  functions we want exposed), as already done for Dashboard/QoS/Traffic/Wireless/GK/Warden/Devices/
  Advisor/Conn/QoSDiag/Analytics/Storage/Firmware (v2.3.1). The Firewall suite (above) is the next
  candidate. [ongoing]

- **[P3] Staged ("batch") changes — one save, minimal restarts.** Today each control applies
  immediately (e.g. changing all three Wi-Fi bands = three applies + three `restart_wireless`). Add a
  staging layer: a control's Apply becomes "Add to changes", writing the intended nvram diff into a
  cross-page **pending basket**; a shell bar shows *"Pending changes (N) — Review / Apply / Discard"*;
  Apply validates all first (all-or-nothing), writes nvram in one commit, then runs the de-duplicated,
  correctly-ordered action set ONCE (reboot only if a staged change is reboot-class).

  - *Feasible — the backend already supports it:* one apply POST carries many nvram keys + a chained
    `action_script`, and `restart_wireless` cycles all radios at once, so "3 restarts" is a UI artifact.
  - *Hard parts:* an nvram-key → required-action map + safe ordering; a reboot-class table (most changes
    are service restarts, a few need a COLD reboot — MLO enable/disable, some SDN/op-mode switches);
    staleness/conflict if nvram changed underneath; and scope (clean for Reaper-authored pages, hard for
    stock ASUS pages). *Recommended path:* Reaper-native pages first; quick sub-win = a single Reaper
    Wireless page for all three bands that applies once. The full cross-page system is its own project.

- ~~**Warden Counts** Warden hit counts are still not being persistant across reboots or firmware upgrades.~~
  **FIXED in tree 2026-08-11 (unbuilt — METAL OWED).** Root cause was three separate defects, not one:
  (1) the only place the live iptables counters were banked was the top of `apply.sh`, but
  `start_rwarden()` and `stop_services()` call `rw_teardown_rules()` from C *first*, so on every reboot,
  Save & Apply and shutdown the counters were destroyed before anything read them; (2) the per-country
  "Top Blocked Countries" table had **no** persistence at all — it read the live `REAPER_WARDEN` rule
  counters, and that chain is flushed and deleted on every rule rebuild (this is why the feed cache
  survived but the counts did not); (3) nothing checkpointed on a timer, so an unclean reset lost
  everything since the last arm.
  Fix: a new generated `/tmp/rwarden/fold.sh` banks total + per-country into `/jffs/rwarden/counters`
  (`SINCE` / `TOTAL` / `CC <XX> <n>`) and zeroes what it banked, so it is idempotent; it is invoked from
  `stop_rwarden()` *before* the teardown, from the `restart_firewall` path via `apply.sh`, and from a new
  15-minute `rwarden_ck` cron checkpoint. `stats.sh` now reports store + live and the window start.
  New settings on the Warden page: **Save block statistics** (`rwarden_stats_save`, default on) and
  **Reset interval** (`rwarden_reset`: Never / 24 Hours / 7 Days / 1 Month / 3 Months). The Storage page's
  Warden row no longer hardcodes an em-dash — it shows the real window-start date and on-disk size.
  Metal check owed: note the total, reboot, confirm total **and** the per-country rows carry over.

- **[P3] Remote syslog push/fetch.** The router can already send its log to a remote collector
  (send-only). Add the ability to **push to / be fetched by** analytics systems (most SIEM pipelines are
  push-based). Pairs with the shipped health-metrics export (Data Export page). Also open from that
  feature: **wireless RSSI/PHY** per-device metrics were deliberately deferred and can be added later
  from the existing `web-broadcom-am.c` backend.

- **[P3] NIST-grade auditing.** Consider adding audit capabilities aligned to a NIST baseline.

- **[P3] Diag: regulatory-mismatch warning.** Make `reaper_diag` (and possibly a Wireless-page hint)
  print an explicit `WARN: territory_code=EU/xx but wlX_country_code=US` line when the factory territory
  and per-radio country codes disagree — self-documents gray-market / region-switched units. Read-only
  compare, no behavior change (firmware must never auto-alter regulatory nvram). [shelved]

## Code quality / deferred (with reason)

- **[P3] `poll_fcache` O(n²)→hash pairing** (`rtrafd.c`). Bounded to ≤1536 flows every 5 s in the
  metal-validated per-client accounting path — a rewrite of a millisecond-scale loop isn't worth the
  regression risk. Revisit only if a flow-heavy box shows real cost. [shelved]

- **[P3] `poll_classes` 7× `tmctl` popen batch** (`rtrafd.c`). Metal measured 2–3 % CPU at the class
  cadence; treated as a non-issue. [shelved]

- **[P3] Theme-token vocabulary consolidation (remainder of D4).** The accidental same-name/different-
  value drift across the 15 Reaper pages was canonicalized in v2.2.7. Still deferred to the migration:
  the naming-vocabulary consolidation (`--panel2`/`--red*` → `--panel-2`/`--crimson*`) and the `--line`
  cream-vs-red divergence, both of which need per-page CSS **usage** rewrites (visual-regression risk).
  [owed — to migration]

- **[P3] `do_reaper_dev_cgi` function-local `static` snapshot arrays aren't re-entrant.** Latent only
  (httpd serialises these requests); a malloc refactor of the multi-return CGI would add leak risk to
  fix a can't-happen case. [shelved]

## Documentation

- **[P3]** Document the non-functional retained features (the firmware update-check UI's stock pieces,
  the removed security-check UI) that are kept only for potential future use.
- **[P3]** Annotate the system defaults.
- **[P3]** Write a user guide for other users.

## Known issues (cannot remediate — closed-source blob)

- **[P3] Unused BSS/BSSID generated when disabled → RADIUS log spam.** An onboarding/backhaul BSS is
  created even when every feature that would use it is disabled, spamming the log with RADIUS codes for
  an unused radio. Traced to a **closed-source Broadcom blob**; a boot-time suppression script did not
  work and was reverted. [blocked — blob; risk-accepted]

- **[P3] Guest Network Pro (AP-isolation SDN) breaks the 2.5G-1 LAN port when a manual WAN VLAN is also
  active — GT-BE98.** Creating a Guest Pro network with AP isolation makes the 2.5G-1 port stop passing
  untagged main-LAN traffic (an 802.1Q VID-52 tag becomes required). On-metal captures proved there is
  **no userspace interface on this firmware to read or program the hardware switch VLAN/PVID table**, so
  neither a source fix nor a runtime correction hook is possible. **Workarounds:** keep Guest Pro off
  the 2.5G-1 port, move the device to another LAN port, or tag it VID-52; or avoid pairing a manual WAN
  VLAN with Guest Pro on that port. Almost certainly present on stock ASUS too (same blob). Full
  investigation: [`GUESTPRO-2.5G-VLAN-PLAN.md`](GUESTPRO-2.5G-VLAN-PLAN.md). [blocked — blob; risk-accepted]

- ~~**[P2] Smart Connect Rules — band shows `- -` for every field (field 2026-08-08, BE96U tri-band).**~~
  **CLOSED 2026-08-11 — NOT A BUG on the owner's box. Confirmed from live nvram; hypothesis (a) refuted
  by simulation. Two unrelated real defects found and fixed in tree along the way (unbuilt).**