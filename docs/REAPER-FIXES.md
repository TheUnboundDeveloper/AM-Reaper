# RT-BEXXU "reaper" — Hardened Build Fix List

> ⚠️ **Coordinated-disclosure notice.** Many fixes below live in the ASUS/Merlin-authored
> userspace that is **shared source common to other Broadcom HND Asuswrt-Merlin models**,
> so the same flaws exist on those models running **stock, currently-shipping firmware**.
> This document names affected components, functions, and input vectors. Treat it as a
> coordinated-disclosure surface: before publishing it, ensure base-firmware findings have
> been reported to ASUS / Asuswrt-Merlin and given reasonable time to remediate, or reduce
> the disclosure to class-level detail for still-unpatched issues. See
> [`../SECURITY.md`](../SECURITY.md).
>
> **Reachability / PoC dossier (ASUS PSIRT case 1006563):** a per-item "direct utilization"
> analysis was prepared at ASUS PSIRT's request for the `shared/` items C5/C6, H10–H14, and the
> `shared/` M/L set — **confidential, do not publish while unremediated.** That analysis surfaced one
> new defect of our own: the C6 fix was point-fixed in `shared/misc.c` but an independent twin
> (`asus_libpasswd_openssl_crypt`) also shipped in `libpasswd/passwd.c` — tracked as **C6b** (commit
> `19638dba8d`). Drafted during PSIRT coordination on 2026-07-23 (when the twin was still unpatched),
> it was **built and shipped in v1.7.5 (2026-07-24)**, class-fixing every `openssl passwd` sink. See
> the C6b row below.

Custom hardened build of Asuswrt-Merlin for the **ASUS RT-BEXXU**.

- **Base version:** 3006.102.8_beta2
- **Custom version string:** the base-firmware security hardening catalogued here landed in **v1.0** and is carried through the current **v2.7.6** source rung (newest published **v2.7.3**). Most later versions added features and de-cloud removals rather than new *stock-firmware* findings, with two exceptions: **C6b**, a `libpasswd/passwd.c` twin of C6 that surfaced during ASUS PSIRT coordination on 2026-07-23, was class-fixed and **built + shipped in v1.7.5** (2026-07-24); and **v2.0.0**'s inherited-code audit (AUDIT-2) surfaced and fixed fresh *stock-firmware* findings in the ASUS/Merlin-authored userspace — a stored-XSS chain from a device-supplied DHCP hostname into several admin views, a USB volume-label root command-injection at auto-mount, and an IPsec-profile CGI stack overflow — the first new base-firmware findings since C6b; the security work since v1.0 — post-feature injection re-audits, the v1.4.3 / v1.4.4 security-review remediation of Reaper-introduced changes, v1.4.5 exploit-mitigation build hardening (FORTIFY + stack-protector-strong + PIE + full-RELRO on the Reaper daemons), the injection-safe design of the v1.5.0 network-diagnostics tools (fixed-argument exec, never a shell), the **v1.6.0** defense-in-depth pass on the Reaper daemons (CR/LF + dotted-quad validation of the Advisor session-file client value, `lan_ifname` validation before the boot-sweep `iptables` call, plus a `popen` fd/child-leak fix and full allocation-NULL hardening in `rmcpd`/`rtrafd`), the **v1.7.1** remediation of the post-Gatekeeper audit round (2026-07-21 — Wireless-diagnostics CSRF guard, Gatekeeper device-list race + MAC validation, and related hardening), the **v1.7.5** class-closure of C6 across every `openssl passwd` sink (**C6b**, ASUS PSIRT case 1006563), the **v1.8.0a** Reaper Warden threat/geo firewall + Samba **4.15.13a** CVE-2025-9640 backport, the large multi-agent **audit-remediation arc** (73 verified findings closed across v1.8.2–v1.8.6), the v1.8.7/v1.8.8 Warden IPv6 + anti-lockout hardening plus the default-on `rwatch` health watchdog, and the **v2.0.0** two-audit security milestone (a full re-review of all Reaper-authored code and of the inherited ASUS/Merlin open source, every finding fixed with no critical or high left open) — is summarized in [`CHANGELOG.md`](CHANGELOG.md). The v1.0 image details below are the record of when these base-firmware fixes shipped.
- **Branch:** `BEXXU-only` (local only — never pushed upstream)
- **Release:** **v1.0 (2026-07-07).** Image sha256 `fa95b1d417b1ef6b075281b5c435e39fa9a6cf9c3ced2ea4263f8069e7f4f5f5` (loader `e0be733645272bd61291a29c0d1d694622b5a8bba65e30a349478b80eb04f165`). Contents: hardening rounds 1-4 + round-3 injection pass + avahi CVE backport + T1-T4 latent hardening + the v1.0 pre-release audit fixes, plus both Hardware QoS engines and the Reaper UI. The predecessor image `b81e482c` was flashed to the physical RT-BEXXU 2026-07-05 and ran clean; v1.0's QoS + UI additions were validated on metal through 2026-07-07.
- **Build target / applicable model:** at v1.0, **RT-BEXXU only** — the tree was stripped to the RT-BEXXU (`release/src-rt-5.04behnd.4916`). The fixes below live in the ASUS/Merlin-authored userspace, most of which is **shared source common to other Broadcom HND Asuswrt-Merlin models** — so the same flaws exist on those models running stock firmware. *(Currency note: the sibling BCM4916 models — RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro — are built from per-model branches; the full five-model fleet is published at **v2.7.3**, both variants each (through the public clean-room CI pipeline). The newer BCM6765 **RT-BE92U** ships as experimental prereleases through v2.7.6. Because these fixes are in shared source, every model carries them; RT-BEXXU remains the primary, hardware-validated build.)* The "Model" column reflects what this build delivers.

> Scope note: a few items are present in the source but **not compiled/active** in the RT-BEXXU build (gated off by config). They were fixed defensively where cheap, and are flagged below.

---

## Summary

| Severity | Fixed | Deferred (design decision) | Not in BEXXU build |
|---|---|---|---|
| Critical | C1 C2 C3 C4 C5 C6 C6b C7 C8 (9) | — | — |
| High | H1 H2 H5 H6 H7 H8 H9 H10 H11 H12 H13 H14 (12) | H15 | H3, H4 (and H5 — fixed defensively but its TR069/TR181 opt-125 path is likewise not compiled; counted under Fixed, also listed in "Not present in build" below) |
| Medium | M1 M2 M3 M4 M5 M6 M7 M8 M9 M10 M11 M12 M13 M14 M15 M16 M17 M18 M19 (19) | M20, M21 | M22 |
| Low | L1 L2 L3 L4 L5 (5) | — | — |
| Internal | N1 N2 N3 N4 (IPsec shell sinks) | — | — |

Every Critical/High/Medium/Low present in the RT-BEXXU-built source is fixed except the three deferred design items (H15, M20, M21). **C6b** (`libpasswd/passwd.c` twin of C6) was drafted during ASUS PSIRT coordination on 2026-07-23 and **built + shipped in v1.7.5** (2026-07-24), class-fixing every `openssl passwd` sink (see the header note and the C6b row below); the Critical row above lists it as the ninth Critical finding.

Bundled third-party **package CVE backports** (avahi 0.8 mDNS DoS — CVE-2023-38469/-38470/-38473) are tracked in the [Package CVE backports](#package-cve-backports--bundled-system-libraries-2026-07-05) section. Items that are **still open and must be worked** (known-vulnerable EOL libraries, the closed-source blob auth boundary) plus the **abandoned AiCloud set** (disabled by decision, pending removal) and lower-priority latent hardening are catalogued with severities in [Open security items still requiring work](#open-security-items-still-requiring-work-2026-07-05) at the end of this file.

Rounds 1–2 (C/H/M/L/N above) audited the stock ASUS/Merlin userspace for the buffer-overflow and command-injection classes. A **[round-3 injection pass](#round-3--injection-class-fixes-post-feature-security-pass)** (`R3-1…R3-4`) closed four more config/rule/SQL-injection sinks found after the QoS + UI work landed, and a later **[Audit round 4](#audit-round-4--self-review-of-reaper-introduced-changes-2026-07-04)** re-reviewed the *reaper-authored* changes (UI flip, Hardware QoS) for regressions we introduced — 2 real defects + 2 defense-in-depth fixes (R4-1…R4-4). Firmware-correctness fixes made alongside the Hardware QoS feature are recorded in [Firmware correctness fixes](#firmware-correctness-fixes--qos-activation--flow-cache), and the final pre-ship review in [v1.0 pre-release audit](#v10-pre-release-audit-2026-07-07).

---

## Fixes

All rows apply to **RT-BEXXU**. "Commit" is the short hash on `BEXXU-only`.

### Critical
| ID | Component | Fix | Commit |
|---|---|---|---|
| C1 | httpd/web.c | `do_CoBrand_img` pre-auth stack overflow — bounded file extension copy | 54c17164cb |
| C2 | rc/rc_ipsec.c | IPsec cert-gen command injection via `ddns_hostname_x` — argv `eval()` + hostname validation | c950d8cf35 |
| C3 | rc/rc_ipsec.c | IPsec PKCS#12 import command injection — argv exec, password via file not `echo` | c950d8cf35 |
| C4 | rc/snmpd.c | snmpd.conf config-injection → RCE — strip CR/LF from community/sysName/Location/Contact | cbbbb83db3 |
| C5 | shared/nvparse.c | `get_wds_wsec` stack overflow — `strcpy`→`strlcpy` | 50d6fe9a59 |
| C6 | shared/misc.c | `asus_openssl_crypt` command injection — `popen`→argv exec helper | 8bc3189fa6 |
| C6b | libpasswd/passwd.c | `asus_libpasswd_openssl_crypt` command injection (**C6 twin** — an independent copy the C6 fix missed; reached via HTTP + WebDAV/SMB basic-auth on the libc-`crypt()` fallback) — `popen`→argv exec helper. Found during ASUS PSIRT case 1006563 coordination. **STATUS: built + shipped in v1.7.5 (2026-07-24)** — class-fixes every `openssl passwd` sink. | v1.7.5 (commit `19638dba8d`) |
| C7 | rc/rc_ipsec.c | IPsec `ca_txt_parse` unbounded copies — bounded + NUL-guarded | c950d8cf35 |
| C8 | httpd/web.c | `ej_cgi_get` format string — `websWrite(wp,"%s",v)` (defensive; handler unregistered) | 9096344d8a |

### High
| ID | Component | Fix | Commit |
|---|---|---|---|
| H1 | httpd/web.c | `do_CoBrand_img` `lowercase_pid`/`odmpid` overflow — bounded + terminated | 54c17164cb |
| H2 | httpd/web.c | multipart boundary stack overflow — clamp copy to `boundary[]` | 9096344d8a |
| H5 | rc/udhcpc.c | DHCP option-125 overflow in `stropt()` — size param + clamp (TR069 path, defensive) | 23103270af |
| H6 | rc/rc_ipsec.c | unbounded `ipsec_profile_str_parse` — dsize bound on all 26 call sites | 4f2c5327d9 |
| H7 | rc/usb.c | Samba account/password command injection — `shell_dquote_escape` | 433d008797 |
| H8 | rc/usb.c | DLNA `dms_friendly_name` NULL deref — `nvram_safe_get` | e0b01476c8 |
| H9 | rc/snmpd.c | SNMPv3 `createUser` field injection — sanitize user/passwords | cbbbb83db3 |
| H10 | shared/nvparse.c | port/filter `desc` format strings — `"%s"` | 50d6fe9a59 |
| H11 | shared/misc.c | `set_crt_parsed` cert-accumulation overflow — bounded (**note: the vulnerable `buffer[8000]` `#else` branch is `#ifdef`-excluded on the NAND/UBIFS RT-BEXXU — LATENT on this image, DIRECT on stock models built without a JFFS2/UBIFS/JFFS macro; see PoC dossier §4.2**) | 7f831fa82a |
| H12 | shared/mtlan_utils.c | `get_vpns_iprange` NULL deref — guard each `strpbrk` | e9f2c88ef6 |
| H13 | shared/wlif_utils.c | `wl_wlif_save_wpa_settings` negative-index write — clamp index | 28e7ebc511 |
| H14 | shared/mtlan_utils.c | `cpN_local_auth_profile` missing NUL-term — `strlcpy` | e9f2c88ef6 |

### Medium
| ID | Component | Fix | Commit |
|---|---|---|---|
| M1 | rc/rc_ipsec.c | p12 name length underflow | c950d8cf35 |
| M2 | rc/rc_ipsec.c | `left_ipaddr`/`local_pub_ip` `strcpy` → `snprintf` | 4f2c5327d9 |
| M3 | rc/init.c | `rm -rf` of `log_wlstat_dir` via `system` → `eval` | 5ed5029f78 |
| M4 | rc/usb_devices.c | `hotplug_dbg` unbounded `sprintf` → `snprintf` | a0b21a90fa |
| M5 | rc/usb.c | `start_dms` `dbdir` overflow — size-threaded + widened | e0b01476c8 |
| M6 | libdisk/write_smb_conf.c | three `snprintf(..., "%s", ...)` missing size arg — add `sizeof` | bcc18b85e4 |
| M7 | rc/ntp.c | `nslookup` hostname injection — validate host/IP | 433d008797 |
| M8 | rc/usb_devices.c | `device_type`/`blkdev` `strcpy` → `strlcpy` | a0b21a90fa |
| M9 | rc/common.c | predictable `/tmp/iprule_tmp` (symlink race) → `mkstemp` | bcc18b85e4 |
| M10 | httpd/web.c | `ftpServerTree_cgi` format string → `"%s"` | 9096344d8a |
| M11 | httpd/web.c | feedback `fb_*` format string → `"%s"` (both branches) | 9096344d8a |
| M12 | shared/common_utils.c | `strncpy_n(num==0)` wrap + `dest[-1]` — guard | 5519cb4ba0 |
| M13 | shared/shutils.c | `dec_str` over-read — bound by `strnlen` | f3a6247058 |
| M14 | shared/shutils.c | `fd2str` `size_t` read-error bug → `ssize_t` | f3a6247058 |
| M15 | shared/common_utils.c | `get_hex_data` source over-read — clamp to `strlen/2` | 5519cb4ba0 |
| M16 | shared/misc.c | `netdev_calc` `unit_buf` snprintf size — clamp | 7f831fa82a |
| M17 | shared/wlif_utils.c | `wl_wlif_block_mac` unchecked `malloc` — NULL check | 28e7ebc511 |
| M18 | shared/wlif_utils.c (+_ax) | `get_wsec` `ssid` missing NUL-term — `strlcpy` | 28e7ebc511 |
| M19 | shared/nvparse.c | `get_filter_url` `nvram_get` NULL + no NUL-term — `strlcpy(nvram_safe_get)` | bcc18b85e4 |

### Low
| ID | Component | Fix | Commit |
|---|---|---|---|
| L1 | rc/firewall_sdn.c | URL-filter keyword unescaped into iptables/`doSystem` — `_urlf_keyword_safe` gate | bcc18b85e4 |
| L2 | rc/usb_devices.c | `/tmp/usb_err` symlink-appendable as root — `O_NOFOLLOW`+0600 | a0b21a90fa |
| L3 | rc/usb.c | auto-mounted USB volume `chmod 0777` (world-writable) → `0775` | e0b01476c8 |
| L4 | shared/mtlan_utils.c | `inet_pton(...)<0`/`inet_ntop(...)<0` broken checks — `!=1` / `==NULL` | e9f2c88ef6 |
| L5 | httpd/web.c | `SystemCmd` `strncpy` no NUL-term (×4) → `strlcpy` | bcc18b85e4 |

### Internal (found while fixing IPsec)
| ID | Component | Fix | Commit |
|---|---|---|---|
| N1 | rc/rc_ipsec.c | `rc_ipsec_ca_export` ran its arg as a command — argv `eval` | f817f8b31d |
| N2 | rc/rc_ipsec.c | p12 password via `echo > file` — direct 0600 file write | f817f8b31d |
| N3 | rc/rc_ipsec.c | `miniupnpc-new` from WAN values via `system` — `eval` argv | 5048c990d7 |
| N4 | rc/rc_ipsec.c | residual `system()` grep/route sinks — validate/skip metachars | 5048c990d7 |

### Round 3 — injection-class fixes (post-feature security pass)

A second injection-focused sweep run after the Hardware QoS and UI work landed,
covering config-file, iptables, SQL, and pre-auth-decode sinks that the first
two rounds did not reach.

| ID | Sev | Component | Fix | Commit |
|---|---|---|---|---|
| R3-1 | High | rc/services.c | dnsmasq/inadyn **config-injection** — a newline in a static-lease MAC/hostname, `lan_domain`, or the DDNS host could inject extra `dnsmasq.conf`/inadyn directives; reject values containing CR/LF/config metacharacters at the sink | 9716b7adf5 |
| R3-2 | High | rc/firewall.c | **iptables-restore rule injection** — firewall rule-list fields written into the `iptables-restore` batch could inject rules/commands; validate and escape the rule-list fields before emission | a23ed46d5c |
| R3-3 | Medium | libcodb/codb_utils.c, cosql_utils.c | **SQL identifier injection** in the libcodb query builder (Traffic Analyzer / app-stats DB) + source-bounded `strncpy` on the same paths | 102fc2c703 |
| R3-4 | Medium (pre-auth) | httpd/web.c | Pre-auth **login base64 decode off-by-one** (`b64_decode` high-side clamp) on `login_captcha`/`login_authorization`; the paired `-1` malformed-input underflow was the round-4 follow-up (R4-1). The same commit added the QoS-apply numeric gate (see [Firmware correctness fixes](#firmware-correctness-fixes--qos-activation--flow-cache)). | ac418baf9d |

---

## Deferred — design decisions (NOT patched)

| ID | Component | Why deferred |
|---|---|---|
| H15 | shared/defaults.c | Default `http_username=admin` / `http_passwd=admin` (effectively u:admin p:NULL on stock). **Decision: keep** — the first-boot QIS wizard forces a username/password change (`x_Setting=0`), and leaving it unsecured is the owner's explicit choice. Changing the default risks the first-boot flow. |
| M20 | shared/shutils.c | `enc_str`/`dec_str` are a keyless bit-shift "encryption". In this tree their **only** caller is a debug `_dprintf` in `rc/rc.c` — they don't protect any production secret (real credential storage uses the `pw_enc`/`spwenc.o` blob). **Decision: keep** — replacing it breaks stored values for no practical gain. |
| M21 | shared/shutils.c | `generate_wireless_key` derives a default WiFi key from the (public) MAC. It has **zero callers in the buildable source** (dead code), and the live default-key path is already mitigated by forced first-boot setup. **Decision: keep.** |

## Not present in the RT-BEXXU build (no action needed)
| ID | Reason |
|---|---|
| H3, H4 | `multi_wan.c`/`multi_wan_ipv6.c` gated on `RTCONFIG_MULTIWAN_IF` (off for BEXXU). Fixed defensively in commit 433d008797. |
| H5 | TR069/TR181 opt-125 path not compiled (`RTCONFIG_TR069/TR181` off). Fixed defensively. |
| M22 | DSL-AX82U "optus" branch (`case MODEL_DSLAX82U` / `#if defined(DSL_AX82U)`) — not the BEXXU model. |

## Coverage gap (not source-auditable)
Prebuilt binary blobs (`networkmap`, `wlceventd`, `asd`, `libbcm`, `pw_enc`/`spwenc.o`, `cfg_mnt`, login token-cookie generator) ship without source and were not assessed — would require binary reverse engineering.

---

## Audit round 4 — self-review of reaper-introduced changes (2026-07-04)

After the UI "flip", the Hardware-QoS feature, and hardening rounds 1–3, the **reaper-authored diff** was re-reviewed for security issues introduced by *our own* changes (not stock code). Two real defects and two defense-in-depth gaps were found and fixed. Fixes are in commit `994724f10f`; image `RT-BEXXU_3006_102.8_reaper_nand_squashfs.pkgtb` sha256 `c76aac232b2eca251403640c02ccc7bb0426d4fe763fabc97547727d16a3d8fa`.

| ID | Severity | Component | Issue | Fix | Commit |
|---|---|---|---|---|---|
| R4-1 | Medium (pre-auth) | httpd/web.c | The round-3 login `b64_decode` clamp (ac418baf9d) guarded the `>= size` return but **not** the `-1` malformed-input return, so a non-base64 `login_captcha`/`login_authorization` forced `l == -1` and wrote `buf[-1]='\0'` — a 1-byte stack underflow on the pre-auth login path. | `if (l < 0) l = 0;` before the high-side clamp, both sites | 994724f10f |
| R4-2 | Low–Med | www/reaper_shell.asp | `frameUrl()` framed `location.hash` into the iframe `src` with only a `/` prefix; `#\evil.com` normalises (`\`→`/`) to `//evil.com`, loading an off-origin page **inside the trusted REAPER chrome** (phishing; cross-origin so no data/DOM access, no XSS). | allow-list the fragment to `^[A-Za-z0-9_.\-]+\.(asp\|html?)(\?…)?$`, else fall back to the dashboard | 994724f10f |
| R4-3 | Low (def-in-depth) | rc/qos.c | `start_hwqos` wrote `wan_ifname` into the generated **root** QoS script single-quoted but with no charset guard (value is kernel-derived `wanX_ifname`, so not realistically attacker-settable). | reject any non-`[A-Za-z0-9._-]` ifname → inert empty `WANIF` | 994724f10f |
| R4-4 | Low (def-in-depth) | www/Main_ReaperDash.asp | `ddns_hostname_x` / `usb_path{1,2}` nvram interpolated raw into JS string literals on the dashboard (admin-set / physical-access → self-XSS at worst). | encode via `nvram_char_to_ascii("",name)` + `decodeURIComponent`, matching the SSID handling | 994724f10f |

**Verified clean (no change needed):** the new HW-QoS numeric handling (`qos_obw` via `strtoul`+`%u`, guarded `-gt 0`); the dashboard client-list render (DHCP hostnames escaped via `esc()`/`textContent`); the 160-page theme-bake bounce script (target derived from `location.pathname`, never the hash); all captive-portal/login JS (unmodified — `Main_Login.asp` never touched); and all round-1–3 hardening fixes (bounds/escaping re-verified for regressions). OpenVPN pushed-DNS token (`openvpn_control.c`) left as-is — already `inet_aton`-gated before every use, so no metachar can reach the `server=` sink.

**Mock-validated:** R4-4 confirmed end-to-end — a hostile `ddns_hostname_x` value `evil'><img src=x onerror=…>` is served fully percent-encoded inside the JS literal (no breakout) and renders as inert text in the Internet card; the dashboard is otherwise intact.

**Addendum (2026-07-06) — gate regression fixed:** the `ac418baf9d` QoS apply numeric gate (httpd/web.c) rejected any `qos_type > 10`, written when HW QoS v1 (type 10) was the highest engine. HW QoS Classful (type 11, added later) was silently dropped on every GUI apply — Classful never persisted while v1 kept working (syslog-only `reject out-of-range qos_type=11`, confirmed on metal). Cap raised to 11 in commit `6ee4cf49ad`. Lesson: a new `qos_type` engine must clear **three** gates — the `defaults.c` CKN_STR length, this numeric-range gate, and the `rc` dispatch (`add_iQosRules`/`start_iQos`/`hnd_nat_ac_init`).

---

## Firmware correctness fixes — QoS activation & flow-cache

Not vulnerabilities, but functional-correctness fixes made while building the
Hardware QoS feature; several are input-validation-adjacent (an over-length or
out-of-range value being silently dropped). Recorded here so the fix list is
complete through v1.0.

| ID | Component | Problem | Fix | Commit |
|---|---|---|---|---|
| F1 | shared/defaults.c | **HW QoS never activated.** `qos_type` was `CKN_STR1` (max 1 char); `httpd`'s `nvram_check` silently dropped the 2-char value `"10"` (over-length), so selecting Hardware QoS fell back to Adaptive. | `qos_type` → `CKN_STR2` (both `#if` branches); requires a full libshared+httpd build | 8421d9263d |
| F2 | httpd/web.c | **QoS-apply numeric gate too tight.** The apply path rejected any `qos_type > 10` (written when v1 was the highest engine), so HW QoS **Classful** (type 11) was silently dropped and never persisted. | raise the cap to 11; the digit-only `strspn` guard (the real anti-injection check) is unchanged | 6ee4cf49ad |
| F3 | rc/services.c | **Stale flow-cache after disabling QoS.** Offloaded flows lingered, spamming `blog_get_dstentry_by_id`, until a reboot. | `eval("fc","flush")` in the QoS **stop** branch (moved out of the wrong `pms_device` branch) — no reboot needed | 2dcc66f2d6, 3a6024710c |
| F4 | rc/qos.c | `start_cake()` bandwidth printed with `%d` (signed) for an unsigned value. | `%d` → `%u` | c267a089b0 |

> Note: F1 and F2 are the same class of bug one layer apart — a new `qos_type`
> engine must clear **three** gates: the `defaults.c` CKN_STR length (F1), the
> `web.c` numeric-range gate (F2), and the `rc` dispatch (`add_iQosRules` /
> `start_iQos` / `hnd_nat_ac_init`). Both were found by "the engine silently
> reverts to Adaptive on apply."

---

## Mergeability refactor (2026-07-05)

The Reaper theme was de-inlined from the stock pages to cut the per-upstream-drop
merge surface. See `GPL-MERGE.md` for the full design and merge procedure.

- **Theme injection** moved from ~165 inline `</head>` blocks into one httpd
  serve-time filter: `httpd/reaper_inject.c` + `.h`, hooked at the `do_ej` output
  call in `httpd/httpd.c`, gated by `nvram reaper_inject` (default on; `=0` +
  `restart_httpd` = pristine stock UI, no reflash). 165 stock `.asp` reverted to
  pristine and 3 severed symlinks restored.
- **CSS** consolidated into the additive `reaper/reaper_content.css`. **All
  seven stock CSS files are now pristine.** Four (`form_style.css`,
  `index_style.css`, `device-map/clientlist.css`, `device-map/device-map.css`)
  were reverted first (recolors relocated to sections 15-16); the three SDN/MLO
  SPA-bundle files (`RWD_UI/rwd_component.css`, `SDN/sdn.css`, `SDN/mlo.css`)
  followed on 2026-07-05 (commit `19e6d7e44f`, recolors relocated to sections
  17-19). The SPA's runtime theme-variant CSS injection turned out to be gated
  on the WHITE/ROG/TUF themes — the RT-BEXXU runs the default (empty) theme, so
  those variant files never load and the httpd-injected `reaper_content.css` is
  the last/winning stylesheet on the SPA. The SDN/MLO SPA theme spot-check is
  part of the ongoing on-device validation of the flashed image.
- **Quick code fixes folded in:** R4-3's `wan_ifname` charset guard extended to
  `rc/qos.c start_cake()` (CAKE root script, same single-quoted sink); the
  `reaper_shell.asp frameUrl()` deny-list replaced by the R4-2 allow-list so the
  **code now matches this document**; dashboard `wan0_gateway`/`wan0_dns` encoded
  via `nvram_char_to_ascii("",name)` + `decodeURIComponent` (extends R4-4); dead
  `generate_wireless_key` removed from `shared/shutils.c` (0 callers, both header
  externs dropped).

---

## Package CVE backports — bundled system libraries (2026-07-05)

Rounds 1-4 hardened the **ASUS/Merlin-authored userspace**. This section tracks
security backports into the **bundled third-party packages** (the EOL system
libraries ASUS freezes). Each fix is a surgical backport of the official
upstream commit into the shipped version — **no version bumps** — so the ABI the
proprietary blobs link against (`libssl.so.1.1`, `libavahi-*.so`, ...) is
preserved and each patch rebases cleanly across upstream drops.

### avahi 0.8 — mDNS reachable-assertion DoS (commit `7e31549af2`)

`avahi-daemon` auto-starts (`start_mdns`, `RTCONFIG_MDNS=y`) and listens on
UDP 5353; a single crafted mDNS packet could trip a reachable assertion and
abort the daemon — a DoS of local `.local` service discovery (no RCE).
Backported the upstream production-code fixes (the accompanying unit-test hunks
were omitted; no runtime effect):

| CVE | File | Fix | Upstream |
|---|---|---|---|
| CVE-2023-38469 | `avahi-core/rr.c` | `avahi_record_is_valid`: reject a TXT record whose accumulated rdata exceeds `AVAHI_DNS_RDATA_MAX` | `a337a1ba` (lathiat/avahi #500) |
| CVE-2023-38470 | `avahi-common/domain.c` | `avahi_normalize_name`: require >= 2 bytes before writing the label separator, and bail when `avahi_escape_label` returns NULL | `94cb6489` + `20dec84b` |
| CVE-2023-38473 | `avahi-common/alternative.c` | `avahi_alternative_host_name`: unescape the input label first, then re-escape the derived name, so malformed escape sequences can't overrun the buffer | `b448c9f7` |

**Status: FIXED — shipped in image `b81e482c`, flashed 2026-07-05, running
clean.** The avahi-specific spot-check (`.local` service discovery /
`avahi-browse`) is still pending as part of the ongoing per-feature validation.

**Not applicable (not compiled):** CVE-2023-38471, CVE-2023-38472, CVE-2023-1981
are reachable only through the D-Bus API; this build is configured
`--disable-dbus`, so those code paths are absent.

**Deferred (out of scope for a low-risk pass):** CVE-2024-52615 / CVE-2024-52616
live in `avahi-core/wide-area.c` (unicast wide-area DNS). That path is inactive
unless `enable-wide-area` is set — this build is mDNS-only — and 52615 is an
invasive socket-lifecycle refactor.

### OPEN — not patched, documented residual (disclose in release notes)

`OpenSSL 1.1.1w`, `Samba 3.6.x`, `net-snmp 5.7.2`, `lighttpd 1.4.39`,
`expat 2.0.1`, and `libgcrypt 1.5.1` ship as ASUS-frozen EOL libraries.
Hardening targets the ASUS/Merlin userspace; these are tracked separately and
require either surgical CVE backports or an ASUS-led version bump (the blobs
link the old ABIs). For reference: `zlib 1.2.12` already carries the
CVE-2022-37434 fix, and `curl 8.17.0` / `dnsmasq 2.93` are current.

---

## v1.0 pre-release audit (2026-07-07)

Before tagging v1.0, all reaper-authored C and web-UI code was swept a final
time by a multi-agent review (HW QoS C, httpd C, dashboard/shell JS, QoS GUI
JS). **No Critical/High found**; the httpd injection filter (`reaper_inject.c`),
the `qos_type` gate, and the login-decode clamps were re-confirmed clean. Two
code fixes and minor UI polish resulted (commit `52afc5436f`, patch `0085`).

| ID | Sev | Component | Finding | Fix |
|---|---|---|---|---|
| R5-1 | Medium (admin/physical) | rc/qos.c `ip_range_checker` | Four unbounded `strncpy` into `a[4]`/`head[16]` could overflow the stack on a malformed QoS-rule address (`12345.1.1.*`, or a 5-octet address). A stock Asuswrt pattern the T2 `strncat` hardening had left — now exercised by HW QoS Classful rules. | Reject over-length octets (`>= sizeof a`) / addresses (`len_total >= sizeof head`) **before** each copy. **Completes T2** (the same function's `strncat` sites were bounded earlier). |
| R5-2 | Low | rc/qos.c `start_hwqos_classful` | With `qos_obw=0`, `calc()` floors to 2, so every 1–99% class was shaped to ~2 kbit instead of left unshaped. GUI `validForm` already requires non-zero bandwidth, so it is an nvram-edge only. | Gate the class shapers on `obw > 0` (matches `start_hwqos`). |

**Also (cosmetic, not tabled):** dashboard browser-tab title emitted a literal
`&mdash;` (JS string context → `—`); the unused secondary-WAN upload field
is hidden under HW QoS on dual-WAN. Verdict: v1.0 is sound — no remote or
pre-auth defect in the default configuration.

---

## Verification
Each changed file was compiled with the real RT-BEXXU userspace toolchain (gcc-10.3, 32-bit ARM) and confirmed to build clean with no new warnings at the edit sites; `rc_ipsec.c` additionally passed a warning-diff vs the pre-hardening baseline. The **round-4** fixes were validated by a full end-to-end `make rt-BEXXU` (MAKE_EXIT=0, "Done! Image 96813GW has been built"), with all four changes confirmed present in the staged rootfs (`web.c`/`qos.c` recompiled into httpd/rc; both www edits in the minified `fs/www`), plus the mock-router XSS round-trip above. Image sha256 `c76aac232b2eca251403640c02ccc7bb0426d4fe763fabc97547727d16a3d8fa`.

The **avahi CVE backport** was validated by a full `make rt-BEXXU` (MAKE_EXIT=0, "Done! Image 96813GW has been built"): `libavahi-core`, `libavahi-common` and `avahi-daemon` recompiled and relinked with no errors, and all three source hunks are staged. Interim avahi-validation build sha256 `07c86c4cc7ac6931a3abdf03f17a25d96324ed85294193755fb24d354cae73e5` (the combined image actually flashed to metal on 2026-07-05 is `b81e482c…`, per the avahi status note above).

The **latent buffer hardening (T1-T4, commit `f9c6d316e7`)** was validated by a full `make rt-BEXXU` (MAKE_EXIT=0, "Done! Image 96813GW has been built"): `libcodb`, `rc` (udhcpc/qos) and `libshared` recompiled with **zero errors and no new warnings at any edited line** (the surviving `strncat` "bound equals source length" warnings are pre-existing on the untouched string-literal calls). Current release image sha256 `b81e482cb3e027b1e7980b8376dda9d181a75532d75dc9cd200607b02de96e51` (loader `34eb84ff1f9a73740cdbbf687c4921f46f00cf3a2a983d06e94b5de6860ea240`).

**On-metal (2026-07-05):** image `b81e482c` was flashed to the physical
RT-BEXXU and is running in working order — no debug-category log issues. This
is the first on-metal confirmation of the T1-T4 + avahi build; none of the
defensive C edits broke runtime behavior. Per-feature spot-checks continue over
time: Traffic Analyzer / app-stats pages (libcodb SQL builder, T1), a QoS rule
with an IP range (T2), DHCP domain/search rendering (T4), mDNS `.local`
discovery (avahi), and theme at all page depths (SDN/MLO SPA).

The **v1.0 audit fixes (R5-1/R5-2, commit `52afc5436f`)** were validated by a
full `make rt-BEXXU` (MAKE_EXIT=0, "Done! Image 96813GW has been built"): `rc`
(`qos.o`) recompiled and both www edits staged into the minified `fs/www`. The
final **v1.0 release image** is sha256
`fa95b1d417b1ef6b075281b5c435e39fa9a6cf9c3ced2ea4263f8069e7f4f5f5` (loader
`e0be733645272bd61291a29c0d1d694622b5a8bba65e30a349478b80eb04f165`) — the image
distributed as the v1.0 GitHub release. Both Hardware QoS engines (v1 `qos_type=10`
global and v2 `qos_type=11` Classful) were validated end-to-end on the physical
RT-BEXXU through 2026-07-07 (queue programming, class-mark → hardware-queue
steering, priority order, accelerator stays on).

---

## Open security items still requiring work (2026-07-05)

Every subsection below carries an explicit status label: **OPEN** (still
unfixed, must be worked or tracked), **FIXED** (cleared after this section was
first written), or **DEFERRED** (kept as-is by documented decision — do not
"fix" without re-deciding). Rounds 1-4 plus the avahi
backport cleared the command-injection / buffer-overflow classes and the known
mDNS CVEs, and a fresh sink-pattern scan of the in-build userspace (`httpd rc
shared libovpn libcodb libdisk wsdd2 urlfilterd snooper lltdc infosvr lanauth
rstats`) found **no new Critical/High** injection or overflow. What remains is
below, grouped by urgency.

### >>> OPEN — VULNERABILITIES THAT MUST BE WORKED (NOT FIXED) <<<

These are genuine, currently-relevant vulnerabilities in the shipping firmware.
They are the priority backlog — fix them (or, where noted, wait for an ASUS
update) and keep them disclosed in the release notes until resolved. Detail rows
are in the tables further down (referenced by ID).

| Pri | Vulnerability | Where | Why it is still open | Fix path | Detail |
|---|---|---|---|---|---|
| **1 — active** | Known unpatched CVEs in frozen EOL system libraries (**OpenSSL 1.1.1w** first — it is in the remote TLS path; then Samba 3.6.x, net-snmp 5.7.2, lighttpd 1.4.39, expat 2.0.1, libgcrypt 1.5.1) | shipping image | ASUS froze these versions; upstream CVEs are unpatched here | Surgical ABI-preserving CVE backport (as done for avahi) **or** wait for an ASUS version bump | **T10** |
| **2 — watch ASUS** | Auth / token / session core and web input filter live in closed-source blobs (`web_hook.o`, `priv_webapi.o`) that cannot be source-verified | auth boundary | no source — not fixable in this tree | **Monitor ASUS firmware/blob updates**; mitigate by keeping remote admin off + hardened downstream sinks | **T9** |
| **3 — abandoned, pending removal** | Predictable sharelink token, mod_webdav path traversal, `df\|grep` popen | AiCloud (deliberately disabled) | AiCloud was **gutted and abandoned** *because of* these high-severity findings; `WEBDAV`/`CLOUDSYNC` are off so the stack is inert, but the vulnerable `mod_aicloud_*`/`mod_webdav` `.so` still ship and `AICLOUD_TUNNEL=y` | **Do not re-enable.** Slated for full removal in a later revision; not to be fixed-and-shipped | **T6, T7, T8** |

Everything below this callout is lower priority: latent low-risk hardening,
same-origin defense-in-depth, and design decisions. None is a confirmed
remotely-exploitable defect in the **default** configuration.

### FIXED — Latent buffer hardening, 2026-07-05 (commit `f9c6d316e7`, image `b81e482c`, on metal)

These latent items were bounded as defense-in-depth. The target buffers are
pre-sized, so the fixes do **not** change behavior in normal operation; they cap
the write only if a size assumption is ever violated. Built clean
(`MAKE_EXIT=0`, no new warnings at the edited lines).

| ID | Sev | File | Was | Fix |
|---|---|---|---|---|
| T1 | Low | `libcodb/cosql_utils.c` (16 sites) | `strncat(dst, src, strlen(src))` — bounded by *source* length, i.e. unbounded append | Each site bounded by its buffer's own allocation-size var (`match_query_string_size`, `sql_create_table_size`, `sql_insert_columns_size`, `sql_insert_values_size`, `sql_query_columns_size`, `sql_query_size`). The `sql_query` buffer reserves only `+1024` for WHERE clauses, so this adds real protection. |
| T2 | Low | `rc/qos.c` `ip_range_checker` | `strncat(new, s, strlen(s))` | bounded by the `new` buffer size (`len`). The same function's unbounded `strncpy` sites were closed in the v1.0 audit — see **R5-1**. |
| T3 | Info | `shared/shutils.c` `remove_dups` | `strncat(outlist, x, inlist_size - strlen(outlist))` off-by-one | added `- 1` for the NUL |
| T4 | Low | `rc/udhcpc.c` (both DHCP-RFC3397 sites) | `alloca(strlen(domain)+strlen(value)+2)` on DHCP-supplied strings | `alloca` capped at 2048 + bounded `snprintf` (removes stack-growth on a hostile DHCP `search`/`domain`) |

### DEFERRED — Reaper-authored code, defense-in-depth (post-auth, same-origin)

| ID | Sev | File:line | Finding | Decision |
|---|---|---|---|---|
| T5 | Low | `www/Main_ReaperDash.asp:693,736,895` | Dashboard `eval(x.responseText)` on three stock ASUS telemetry endpoints (`cpuInfo`/`memInfo`, `curr_cpuTemp`, `get_wan_lan_status`). Authenticated, same-origin, numeric/status payloads (no user strings) — not exploitable. | **DEFERRED (decision 2026-07-05).** Those endpoints emit JS assignments, not JSON, so `eval`→`JSON.parse` does not apply and `eval`→`new Function` is the same code-exec class (cosmetic). The genuine fix is an `httpApi`-hook rewrite that cannot be validated off-device — not worth the regression risk on live dashboard telemetry for a non-exploitable item. Revisit during an on-device dashboard pass. |

### ABANDONED — AiCloud disabled by decision, pending removal ("Tier E")

**AiCloud is not a future feature of this build.** It was **gutted and disabled
on purpose and is abandoned**, precisely because of the high-severity findings
below — do **not** re-enable it and do **not** treat T6-T8 as a "fix then ship"
backlog. `RTCONFIG_WEBDAV` and `RTCONFIG_CLOUDSYNC` are **off**, so the stack is
inert in v1.0.

Residual to remove: `RTCONFIG_AICLOUD_TUNNEL=y` is still set and the module
objects still ship in the image — `mod_webdav.so`, `mod_aicloud_invite.so`,
`mod_aicloud_sharelink.so`, `mod_aicloud_auth.so` (`fs/usr/lib/`). A later
revision will strip the tunnel flag and these objects. The findings stay
catalogued here as the **justification for abandonment** and because the
vulnerable objects remain on disk until that removal lands.

| ID | Sev (if it were enabled) | Component | Finding | Note |
|---|---|---|---|---|
| T6 | High | AiCloud sharelink | Share token = `sprintf("AICLOUD%d", abs(time(0)))` — time-seeded, brute-forceable. | One of the reasons AiCloud was abandoned. Not being fixed — the feature is going away. |
| T7 | High | mod_webdav (lighttpd) | Path-traversal in the webdav request-path handling. | Ditto — abandonment justification, not a remediation target. |
| T8 | Med | AiCloud disk-usage | `popen("df ... \| grep ...")` helper. | Ditto. |

### OPEN (residual) — accepted risk, documented; not code-fixable in this tree

| ID | Sev | Component | Finding | Suggested remediation |
|---|---|---|---|---|
| T9 | High (residual) | blobs `web_hook.o`, `priv_webapi.o` | The auth-decision + token/session core (`auth_check`, token/nonce generation) and the web input filter (`validate_apply_input_value`/`check_xss_blacklist` — disassembly shows no `\n`/`\r` checks) are closed-source; the auth boundary and token predictability can't be source-verified. This is *why* rounds 1-4 harden at each sink regardless. | Not fixable without source. Keep remote admin disabled (physical-access threat model), harden every downstream sink, track ASUS blob updates. |
| T10 | Med-High (residual) | EOL system libraries | `OpenSSL 1.1.1w`, `Samba 3.6.x`, `net-snmp 5.7.2`, `lighttpd 1.4.39`, `expat 2.0.1`, `libgcrypt 1.5.1` ship frozen (`zlib 1.2.12` and `curl 8.17.0` are current). | Surgical, ABI-preserving CVE backports (as done for avahi) where reachable. OpenSSL 1.1.1 post-`w` cherry-picks are the highest-value next tier. Disclose in release notes. |
| T11 | Low | avahi wide-area (deferred) | CVE-2024-52615/-52616 in `avahi-core/wide-area.c` — inactive on this mDNS-only build; 52615 is an invasive socket-lifecycle refactor. | Backport if wide-area unicast DNS is ever enabled. |

### DEFERRED — design decisions kept as-is (listed for completeness)

| ID | Sev | Component | Finding | Rationale / remediation |
|---|---|---|---|---|
| T12 | Low-Med | Default admin creds (H15) | Default admin account. | Mitigated by forced first-boot QIS password change. Consider also disabling WAN web admin by default. |
| T13 | Low | `enc_str`/`dec_str` (M20) | Keyless nvram string obfuscation. | Only a debug `_dprintf` caller is in-build; real credential crypto lives in the `spwenc.o` blob. Keep; revisit if a real caller appears. |

> Method note: findings are from a `grep`-based sink scan plus targeted reads,
> not a formal proof of absence. **T1-T4 are now fixed** (commit `f9c6d316e7`);
> **T5 is a documented deferral**; **T6-T8 (AiCloud) are abandoned** — resolved
> by removing the feature, not by patching it. The real open backlog is the
> priority callout at the top of this section: T10 by reachability (OpenSSL
> first) and T9 by watching ASUS.

---

## Stored XSS in the client-picker dropdown (2026-08-11, `e88ffc4d16` — shipped in v2.3.3, published from v2.3.4)

Stock ASUS/Merlin code, shared source, so the same flaw is expected on other
Broadcom HND models running stock firmware. Found while closing a `[P3]` backlog
item that described only a cosmetic tooltip residual.

| ID | Severity | Component | Issue | Fix | Commit |
|---|---|---|---|---|---|
| X1 | **High** (unauth LAN → admin, click-gated) | `www/client_function.js` `showDropdownClientList()` / `genClientItem()` | The device **name** is concatenated into an inline handler: `onclick="fn('<name>')"`. That position crosses **two** parsers — the HTML attribute decoder runs first, then JS — so the ingestion-time HTML encoding (v2.1.3) is not protection there: a DHCP hostname `x');<payload>;//` is stored as `x&#39;);<payload>;//`, the decoder restores the apostrophe, the JS string closes, and the remainder executes. Any LAN device sets its own hostname; ~20 shipped pages mount this dropdown (QoS, Parental Controls, VPN Director, Virtual Server, DNS Director, Key Guard, TOR, ACL, Guest Network, System), and those passing `name>mac` put the name into the handler. | `jsAttrArg()` — HTML-decode to the raw text, escape **that** for a JS single-quoted string, then HTML-encode the result. Applied to every inline-handler argument; `<a id=`/`title=` quoted and encoded. | `e88ffc4d16` |
| X2 | Cosmetic (same function) | as above | `clientName` was truncated at 30 chars **while HTML-encoded**, so a cut could land inside an entity (`&#39;` → `&#3`) and render as garble — the "garble" half of the original v2.1.3 report. | `clipEncodedName()` slices the decoded text, then re-encodes. | `e88ffc4d16` |

**Browser-verified, not reasoned:** with the callback defined as the real pages
define it, the injected statement **executed** on click before the fix and does
not after; the post-fix handler reads `setClientIP('x\');…')` — one string
argument. An earlier harness run that appeared safe was a **false negative** —
the callback was undefined, so the first call threw and aborted the rest of the
handler. Worth remembering as a PoC-design trap.

**Already correct, checked while here:** every `htmlEncode` in the tree escapes
the apostrophe (`&#39;` is in the default entity set), and the `vendor` /
`deviceTypeName` tooltips flagged by the backlog were already encoded in v2.2.0 —
that half of the item needed no change.

---

## UPnP redirect table applied to all traffic — carried upstream defect (2026-08-13, `968ab0e348`, v2.4.1)

**Inherited, not Reaper-authored.** The 3006.102.8 base carries `a1ce74be78`
("fix UPnP rules when port forwarding is not enabled", a patch from ASUS) whose
first hunk emits an unqualified jump. Reported by the upstream engineers during
the UPnP/console triage and confirmed here from the tree; ASUS resolved it
internally and Merlin is reverting it for 102.8_4.

| ID | Severity | Component | Issue | Fix | Commit |
|---|---|---|---|---|---|
| U1 | **Medium** (LAN traffic redirection; requires an active UPnP mapping) | `rc/firewall.c` `nat_setting()` | `-A PREROUTING -j VUPNP` is emitted **with no qualifier**. `VUPNP` holds miniupnpd's DNAT redirects and is meant to be entered only via `-A VSERVER -j VUPNP`, where `VSERVER` is itself reached as `-A PREROUTING -d <wan_ip> -j VSERVER` — i.e. only for packets addressed to this router's WAN address. Unqualified, **every** packet crossing `nat/PREROUTING` is tested against the UPnP redirects, **outbound traffic included**: a mapping on port *N* rewrites a LAN client's own outgoing connection to a remote server on port *N*. Any LAN device can create a mapping when UPnP is on, so a device can redirect other clients' outbound connections to itself. Field symptom: a console that cannot reach the game server at all while UPnP is enabled. | Revert **the first hunk only**. The patch's other hunk (`-A FORWARD -j FUPNP`) is deliberately **kept**: it is the sole hook into `FUPNP`, carries filter-table ACCEPTs, and cannot DNAT anything — dropping it would leave UPnP forwards translated and then dropped in `FORWARD`. The `char tmp[32]` the patch added goes with the reverted hunk. | `968ab0e348` |

**The patch was also unnecessary on this path**, which is why reverting it costs
nothing: the `VSERVER` jump is emitted whether or not port forwarding is enabled,
and `-A VSERVER -j VUPNP` is gated on `upnp_enable` rather than `vts_enable_x`, so
the UPnP redirects were already reachable. The problem the patch set out to fix
does not exist in this tree.

**Distinct from the IGD:1/IGD:2 description issue** fixed in the same release
(`ac485cfd4a`) — the upstream engineers were explicit that the two are unrelated.
That one is a compatibility fault, not a security one: an IGD:2 device
description left a PS5 unable to match any service type, so it could not create a
mapping at all. Both were reported together as "UPnP breaks Call of Duty", which
is worth recording as a reminder that one symptom had two independent causes.

---

## Code review 2026-08-18 — phase 1 & 2 remediation (in progress, v2.5.0)

A three-phase review of Reaper's own code: (1) waste, dead and unreachable code, (2) function flow
and data passing, (3) vulnerabilities — **phase 3 has not started**. Phases 1 and 2 produced 114
findings, 16 of them high. They were not security-scoped passes, but several findings are security
in substance and are recorded here; the rest are efficiency and data-flow work, tracked in
[`BACKLOG.md`](BACKLOG.md).

**This section is appended to as the campaign proceeds. It is not complete.**

| ID | Severity | Component | Issue | Fix | Status |
|---|---|---|---|---|---|
| CR-S1 | **Medium** (privilege-escalation *enabler*, not a standalone attack) | `rc/init.c` | `/tmp` is `chmod` `0777` with **no** `S_ISVTX`, and nothing in `rc/` or `shared/` ever sets it. Without the sticky bit any uid may unlink or rename another uid's entry in a shared directory, so a non-root process can delete a root-owned file and recreate it with its own content, or plant a directory before root creates one. Reaper keeps live control state under `/tmp` (`reaper_fw/`, `rwarden/`, `gk/`), including generated scripts that are executed as root. Not exploitable alone — almost everything on the box runs as root — but it converts any unprivileged foothold into root code execution. | `chmod("/tmp", 01777)`. `/tmp` is tmpfs, so the sticky bit costs nothing. | Fixed, compiles clean |
| CR-S2 | **Medium** (access control reports success, enforces nothing) | `www/Reaper_Devices.asp` | `gk` is `-1` for a device absent from `gk_rl`. The access `<select>` offers `{1,2,3,0}` with no `-1` case, so no option is marked `selected` and the browser renders the **first** — value 1, "Full access" — for every un-enrolled device, **including one `REAPER_GKF` is actively DROPping**. The handler is `onchange`, so re-picking the displayed value fires nothing and the page cannot correct itself. `Reaper_GK.asp` calls the same device Pending: two admin views disagree about enforcement state. | Explicit placeholder option rendered when `gk` is outside the known set; `setGk()` ignores an empty submission. New dict token `RDEV_91`, all 25 packs. | Fixed, compiles clean |
| CR-S3 | **Low** (remote resource exhaustion, pre-auth reachable surface) | `httpd/web.c` | Four JSON emitters escape a value one character at a time through `websWrite`, which is `fprintf` + `fflush` (`httpd.h:354`) on the client socket: one `write(2)` per byte, and one TLS record per byte under HTTPS. The firewall drops ring is `400 x 640` = 250 KB, so a single `reaper_fw.cgi?action=drops` is ~250,000 writes. httpd is single-flight, so this is head-of-line blocking for every other GUI request — a cheap way for anyone who can reach the interface to occupy it. | `fputc` / `fprintf` on the same stream, which do not flush; the stream is flushed by the `websWrite` that closes the JSON string. The review named three sites; a fourth (the `egress_tm` capture, flushing on every newline of a multi-KB shell dump) was found while fixing them. | Fixed, compiles clean |
| CR-S4 | **Low** (resource leak, defensive) | `rc/reaper_fw.c` | The teardown branch of `rfw_gen_apply()` returned before the keep-list ipset sweep, which only runs on the enabled path, so disabling the engine or rolling back left up to 256 `rwfw_*` sets resident until reboot — while the comment in `stop_reaper_fw()` stated the sweep had run. | Unconditional sweep emitted in the teardown branch; the chains are already gone at that point, so no set is still referenced. | Fixed, compiles clean |
| CR-S5 | **High** (access control reports success and enforces nothing) | `rc/gatekeeper.c` | Every enforcement hook bound `$LANIF` - `br0` - while `gkd` accepts an ARP row from any `br*` and sweeps every `wlN.M` VIF, which is where MULTILAN (`RTCONFIG_MULTILAN_CFG=y`) puts guest, IoT and SDN networks. A device on one of those was listed, offered Approve/Block/Guest, written to `gk_rl` and logged as newly seen - and never traversed a Gatekeeper chain. **Block reported success and changed nothing**; in quarantine mode the inverse, those devices were never held at the gate, so default-deny device access control was false for every network except the primary LAN. `self_heal()` only probes that the chains *exist*, so nothing surfaced it. | Hooks are emitted per MTLAN network (`GKIFS`, built from `get_mtlan()` as `pc.c:1891` does, each name passing the same charset gate as `LANIF`). Teardown sweeps a broader list (`GKALL`, plus every bridge present) so a network deleted since the last arm still loses its stale hook. All jumps are removed before any chain is flushed. `gk_teardown_rules()` rewritten to match, dropping the fixed buffer that had been silently truncating every teardown. | Fixed, compiles clean |
| CR-S6 | **Medium** (a half-loaded ruleset was recorded as applied) | `rc/reaper_fw.c` | `apply.sh` had no `set -e`, no per-command status check, and its last line was `fc flush`, so `system()` could only ever observe the flush. Arbitrarily many DROP rules could fail to load and the engine still reported success - and on Keep that set became both the confirmed flash config **and** the rollback target. | Every rule emission routes through an `RFWR` wrapper that counts failures; the script writes the count to `/tmp/reaper_fw/failcount` and exits **3**, distinct from the existing LAN-not-ready exit 1. The caller sets `reaper_fw_err` with the count and logs it. (A named helper rather than a shadowing function, because this busybox is built without the `command` builtin.) | Fixed, compiles clean |
| CR-S7 | **Medium** (stale telemetry keeps leaving the device) | `rc/services.c`, `httpd/web.c` | `stop_rtraf()` killed the collector and deleted nothing under `/tmp/rtraf`, and no reader tests freshness: rexport's only liveness check is a readability test, `health.json` carries no timestamp, and `metrics.prom` carries none either - OpenMetrics without timestamps is stamped at scrape time, so frozen gauges read as current. The collector stopped and the box kept POSTing the same per-device RTT/jitter/loss payload to Splunk or Datadog every interval indefinitely, while the Analytics page reported a 200. | `stop_rtraf()` sweeps `.json` and `.prom` from `/tmp/rtraf` (the healthhist spool is deliberately kept - it is staging for the durable store). The Prometheus endpoint refuses a snapshot older than 300 s, covering an unclean exit where the file survives. | Fixed, compiles clean |
| CR-S8 | **Medium** (defeats the anti-lockout safety net) | `rc/reaper_fw.c` | The engine holds its eight editable lists in nvram RAM and is designed to commit them only inside `reaper_fw_confirm()`. But `nvram_commit()` takes no key argument and flushes the **whole** store, and `web.c` alone calls it around 105 times (Apply on any stock page, Gatekeeper actions, Storage save, Analytics save), while `gkd` commits from a background daemon on guest-pass expiry with no operator action at all. Any one of those inside the confirm window persists an unconfirmed draft. The arm marker and the deadline both live in tmpfs and do not survive a reboot, and no cron job remains to time the change out - so the boot path re-applied the draft from nvram under the stated premise that what boots was already confirmed. **A rule that locked the admin out survived the reboot meant to undo it.** | `start_reaper_fw()` now loads the last CONFIRMED snapshot (`RFW_LASTGOOD`), falling back to nvram only when no snapshot exists, so a box that has never confirmed one is unaffected. Safe because `rfw_write_lastgood()` has exactly one caller - `reaper_fw_confirm()` - and `reaper_fw_apply()` always arms, so no legitimately-applied config exists only in nvram. A `reaper_fw_armed` flag with no tmpfs marker is also cleared at boot, so a stale flag cannot wedge the single-arm CAS. | Fixed, compiles clean |

Correctness fixes from the same pass, recorded for completeness rather than as security findings.
The Gatekeeper's wired/wireless flag could only ever hold one value, so **every** device - Ethernet
clients included - was labelled wireless (`gkd.c`); and `load_seen()` kept 3 of the 8 `seen.tsv`
columns, discarding hostname and band on every restart. The two compound, because the band is what
the corrected wired test reads, so both had to be fixed together. An IPv4 flow opened from the WAN
side was dropped before attribution, so every port-forwarded or UPnP-mapped connection was counted
on the WAN line and appeared against no device (`rtrafd.c`). All four traffic-history windows were
re-serialised together every 5 minutes - about 212,000 `fprintf` calls inside a loop budgeted at
100 ms - stalling the live sampler; the slow windows now rotate.

**P2-H5** (`rwarden_dir`) was resolved as *label matches code*, by owner decision: `"out"` and
`"both"` have always produced a byte-identical ruleset, because `do_out` gates only the `RW_OUT`
chain while the inbound source group and the `-I INPUT` hook are emitted unconditionally. The
unachievable option was removed from the page and a stored value migrated to `both`. **No
enforcement changed**, and `do_out` still accepts the legacy value.

**P2-H6** (QoS strict priority) was **confirmed on hardware** rather than inferred. The 4916
target's own shipped `tmctl` (`targets/96813GW/fs/bin/tmctl`) documents
`priority = <0,7(MAX_Q_PRIO-1)>, lower value, lower priority`, and a live read-back on RT-BE96U
returned qid 1 -> priority 1 and qid 5 -> priority 5. The generator passed the queue id as the
priority, so class 1 - the page's top row, described as served first - ranked below the catch-all
Default. The rank is now inverted within the same value set, so no rank can collide with a queue the
script does not reconfigure. **This is the one fix in the set that changes live traffic behaviour
and wants a metal test.**

> **Disclosure note for CR-S1.** The `/tmp` mode is **inherited stock ASUS/Merlin behaviour**, not a
> Reaper regression — it is present on the base firmware and therefore on other Broadcom HND
> Asuswrt-Merlin models running currently-shipping firmware. It falls under the coordinated-disclosure
> notice at the top of this document. It was found on 2026-08-14 by the v2.4.2 security audit, which
> reached it from three unrelated directions.

**Output escaping was consolidated before the security pass, not after.** The review recommended
this explicitly, and the reason is auditability: `esc()` existed in **eight** textually distinct
copies across the Reaper pages, four of which rendered a null or undefined value as the literal text
"null" while the rest rendered empty, and one of which emitted numeric character references where the
others emitted named ones. None of the differences was exploitable - every copy escaped the same five
characters - but a vulnerability review should have one implementation to reason about rather than
eight. There is now a single `window.ReaperEsc` in `reaper_util.js`; 13 local definitions were removed
and 10 pages gained the script tag. Verified afterwards that no page still defines its own, that every
caller loads the shared one, and that no page calls it before the tag (a load-order mistake would
throw at render time).

While doing it, one item the review had deferred **to** phase 3 was closed as a false lead:
`Reaper_Analytics.asp` defines an `esc()` it never calls, and the review flagged its `innerHTML` use
as a possible latent XSS. The page has exactly three `innerHTML` sinks and every one takes a
constant - two dict tokens and a lookup table whose values are all dict tokens. No attacker-influenced
data reaches any of them, so the unused function was dead code and was deleted rather than wired up.

*A caution for anyone reading the review's own figures: they were wrong on all four counts here (it
said five variants, twelve of fifteen pages, two null-renderers, and implied `esc` was already in
`reaper_util.js`). Verify before acting on a count.*

**Still open from these phases.** All 16 HIGH findings are fixed. The bulk of the MEDIUM/LOW tail was
then worked across v2.5.1–v2.5.4 (dead-code and hot-path cleanups, the store-resolver mount guards,
the MCP arm-time stale-session sweep, the Warden fold/stats shared lock, the analytics staleness
gate); what remains is tracked in [`BACKLOG.md`](BACKLOG.md) and is
efficiency / data-flow in nature rather than security. **Phase 3, the dedicated vulnerability pass,
ran and shipped in v2.5.0** — its corrected defective-reworks and new fixes are recorded in the
v2.5.0 CHANGELOG and RELEASE-NOTES; the two items it left open are architectural owner-decisions (the
firewall layer-ordering, and the deeper Gatekeeper multi-network redesign) tracked in the BACKLOG.

---

## Audit re-verification 2026-08-20 (v2.5.7)

The 13 findings still marked open from the 2026-07-31 inherited-code audit were re-verified by a
five-agent pass against the current tree: **0 Critical, 0 High**, and most already resolved by the
v2.5.0–v2.5.4 work. Five Low/Info items were fixed in **v2.5.7**:

| ID | Severity | Component | Issue | Fix |
|---|---|---|---|---|
| B1-SEC-003 | Low | `httpd/web.c` | An out-of-bounds read was reachable in the multipart-boundary scanners under a crafted header. | Bounds guards added at the three scan sites. |
| A1-SEC-003 | Info | `httpd/web.c` | `gk_baseline_snapshot` could iterate past a very large `gk_rl`. | Fail-safe skip when `gk_rl` ≥ 16 K (logs `gk_rl too large`). |
| A1-SEC-004 | Low | `httpd/web.c` | A `usbkey=` value could carry a stray CR/LF into a downstream write. | CR/LF stripped from the value. |
| B1-SEC-006 | Low | `httpd/web.c` | The `ejusb` disk parameter was unconstrained. | Numeric-or-`all` guard on the parameter. |
| A4-UI-006 | Info | `www/js/httpApi.js` | The change-password call used the wrong HTTP-method shape. | `chpass` now issues a proper `POST`. |

Not fixed, with cause: **A3-NET-002** — the "fix" would itself cause an admin lockout, and fail-open
is the correct posture here; **A6-REL-001** — needs upstream feed signatures that do not exist.
Deferred: **A6-PERF-001**, an rtrafd viewer-gate that is a performance item only validatable on a
live page, held for a focused follow-up. Already resolved earlier and re-confirmed: A6-PERF-002,
B4-SEC-001, A2-QUALITY-004, and the `0700` directory-mode item (A3-REL-005).

## Adversarial review 2026-08-22 (v2.7.1)

Three independent passes over everything changed since the 2026-07-31 audit (httpd CGIs + pages;
the rc script generators; daemons, the diagnostics report and the update check), plus a regression
check of about forty earlier findings — **none regressed**. Fixed in **v2.7.1**:

| ID | Severity | Component | Issue | Fix |
|---|---|---|---|---|
| R7-SEC-001 | **High** | `httpd/web.c`, `httpd/httpd.c`, `rc/services.c` | The `http_id` token every Reaper CGI compared requests against was ASUS's factory constant (`shared/defaults.c`), identical on every router and never regenerated; Reaper CGIs are not in the prebuilt referer whitelist, so a cross-site top-level GET could drive any Reaper action with a live admin session. | `http_id` generated per boot from `/dev/urandom` in `start_httpd`; every Reaper CGI additionally refuses a request whose Referer host is not this router (`reaper_referer_ok`); `referer_url` cleared per request. |
| R7-SEC-002 | Medium | `httpd/web.c` (`reaper_fw.cgi save`, `reaper_cfg.cgi import`) | A list saved during the commit-confirm window was snapshotted by Keep as the confirmed config without ever having been compiled or run. | Save and import of firewall lists refused while `reaper_fw_armed=1`. |
| R7-SEC-003 | Medium | `rc/reaper_fw.c` `rfw_emit_rule` | The over-length-field guard tested `< 0` but `rfw_field()` had returned 0 for "does not fit" since 2026-08-21 — dead code; a truncated match field silently widened the rule. Admin/root-gated data. | Guard tests `!rfw_field()`. |
| R7-SEC-004 | Medium | `others/reaper_diag` | A DHCP client named `HOST-` made sanitizer pass 1 loop forever (its token contained the literal), pinning the httpd that runs the report. Any LAN device could plant the name. | Pass 1 builds left-to-right; tokens carry a `\001` sentinel during the passes, stripped at print. |
| R7-SEC-005 | Low | `rc/reaper_fw.c`, `rc/reaper_pbr.c`, `rc/gatekeeper.c`, `gkd/gkd.c` | Generated root scripts / snippets called bare `nvram get` (the v2.6.1 hang guard rule). | `_nv` helper / C-side reads. |
| R7-SEC-006 | Low | `rc/reaper_pbr.c`, `rc/reaper_fw.c` | A routing candidate that failed to run still armed a timer; the list migration could promote a pre-confirm draft to "confirmed". | Exit status checked, rollback on failure; draft held aside during migration. |
| R7-SEC-007 | Low | `httpd/web.c` (`reaper_cfg.cgi`), `others/reaper_diag` | Import rejected Warden's CIDR / feed keys under the flag charset and skipped the Gatekeeper baseline snapshot when enabling it; the sanitizer missed hostnames present only in the syslog tail or truncated to 32 characters by Gatekeeper's log line. | Per-key charset (rc re-validates structurally), baseline on 0→1, 60 KB client cap; syslog seeding, 32-char prefixes, lease dump fields only. |

Recorded, not changed: **R7-DESIGN-001** — the firmware-update chain verifies TLS against the system
CA bundle, host pin, model/variant and the manifest's SHA-256, and nothing flashes without a click,
but the manifest carries no author signature (a compromised repository could offer a matching pair);
a key-custody decision, tracked in `BACKLOG.md`. **R7-REL-001** — the watchdog's routing self-heal
runs the idempotent apply script without the firewall lock (transient inconsistency at worst).
