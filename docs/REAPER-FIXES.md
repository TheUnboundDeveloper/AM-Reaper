# RT-BEXXU "reaper" — Hardened Build Fix List

> ⚠️ **Coordinated-disclosure notice.** Many fixes below live in the ASUS/Merlin-authored
> userspace that is **shared source common to other Broadcom HND Asuswrt-Merlin models**,
> so the same flaws exist on those models running **stock, currently-shipping firmware**.
> This document names affected components, functions, and input vectors. Treat it as a
> coordinated-disclosure surface: before publishing it, ensure base-firmware findings have
> been reported to ASUS / Asuswrt-Merlin and given reasonable time to remediate, or reduce
> the disclosure to class-level detail for still-unpatched issues. See
> [`COMPLIANCE-AUDIT-2026-07-13.md`](COMPLIANCE-AUDIT-2026-07-13.md) item **M6** and
> [`../SECURITY.md`](../SECURITY.md).
>
> **Reachability / PoC dossier (ASUS PSIRT case 1006563):** the per-item "direct utilization"
> analysis PSIRT requested for the `shared/` items C5/C6, H10–H14, and the `shared/` M/L set is in
> [`REAPER-POC-DISCLOSURE-2026-07-23.md`](REAPER-POC-DISCLOSURE-2026-07-23.md) — **confidential, do not
> publish while unremediated.** That analysis surfaced one new defect of our own: the C6 fix was
> point-fixed in `shared/misc.c` but an independent twin (`asus_libpasswd_openssl_crypt`) also shipped
> in `libpasswd/passwd.c` — tracked as **C6b** (commit `19638dba8d`). Drafted during PSIRT coordination on
> 2026-07-23 (still reported as unpatched in `REAPER-POC-DISCLOSURE-2026-07-23.md` §4.1, which predates
> the fix), it was **built and shipped in v1.7.5 (2026-07-24)**, class-fixing every `openssl passwd`
> sink. See the C6b row below.

Custom hardened build of Asuswrt-Merlin for the **ASUS RT-BEXXU**.

- **Base version:** 3006.102.8_beta2
- **Custom version string:** the base-firmware security hardening catalogued here landed in **v1.0** and is carried through the current **v2.0.0** release. Most later versions added features and de-cloud removals rather than new *stock-firmware* findings, with two exceptions: **C6b**, a `libpasswd/passwd.c` twin of C6 that surfaced during ASUS PSIRT coordination on 2026-07-23, was class-fixed and **built + shipped in v1.7.5** (2026-07-24); and **v2.0.0**'s inherited-code audit (AUDIT-2) surfaced and fixed fresh *stock-firmware* findings in the ASUS/Merlin-authored userspace — a stored-XSS chain from a device-supplied DHCP hostname into several admin views, a USB volume-label root command-injection at auto-mount, and an IPsec-profile CGI stack overflow — the first new base-firmware findings since C6b; the security work since v1.0 — post-feature injection re-audits, the v1.4.3 / v1.4.4 security-review remediation of Reaper-introduced changes, v1.4.5 exploit-mitigation build hardening (FORTIFY + stack-protector-strong + PIE + full-RELRO on the Reaper daemons), the injection-safe design of the v1.5.0 network-diagnostics tools (fixed-argument exec, never a shell), the **v1.6.0** defense-in-depth pass on the Reaper daemons (CR/LF + dotted-quad validation of the Advisor session-file client value, `lan_ifname` validation before the boot-sweep `iptables` call, plus a `popen` fd/child-leak fix and full allocation-NULL hardening in `rmcpd`/`rtrafd`), the **v1.7.1** remediation of the post-Gatekeeper audit round (2026-07-21 — Wireless-diagnostics CSRF guard, Gatekeeper device-list race + MAC validation, and related hardening), the **v1.7.5** class-closure of C6 across every `openssl passwd` sink (**C6b**, ASUS PSIRT case 1006563), the **v1.8.0a** Reaper Warden threat/geo firewall + Samba **4.15.13a** CVE-2025-9640 backport, the large multi-agent **audit-remediation arc** (73 verified findings closed across v1.8.2–v1.8.6), the v1.8.7/v1.8.8 Warden IPv6 + anti-lockout hardening plus the default-on `rwatch` health watchdog, and the **v2.0.0** two-audit security milestone (a full re-review of all Reaper-authored code and of the inherited ASUS/Merlin open source, every finding fixed with no critical or high left open) — is summarized in [`CHANGELOG.md`](CHANGELOG.md). The v1.0 image details below are the record of when these base-firmware fixes shipped.
- **Branch:** `BEXXU-only` (local only — never pushed upstream)
- **Release:** **v1.0 (2026-07-07).** Image sha256 `fa95b1d417b1ef6b075281b5c435e39fa9a6cf9c3ced2ea4263f8069e7f4f5f5` (loader `e0be733645272bd61291a29c0d1d694622b5a8bba65e30a349478b80eb04f165`). Contents: hardening rounds 1-4 + round-3 injection pass + avahi CVE backport + T1-T4 latent hardening + the v1.0 pre-release audit fixes, plus both Hardware QoS engines and the Reaper UI. The predecessor image `b81e482c` was flashed to the physical RT-BEXXU 2026-07-05 and ran clean; v1.0's QoS + UI additions were validated on metal through 2026-07-07.
- **Build target / applicable model:** at v1.0, **RT-BEXXU only** — the tree was stripped to the RT-BEXXU (`release/src-rt-5.04behnd.4916`). The fixes below live in the ASUS/Merlin-authored userspace, most of which is **shared source common to other Broadcom HND Asuswrt-Merlin models** — so the same flaws exist on those models running stock firmware. *(Currency note: since v1.5.0e the sibling BCM4916 models — RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro — were reintroduced from per-model branches and all five shipped in lockstep through **v1.8.6c**; since then **v1.8.7 → v2.0.0 have shipped on the RT-BEXXU only**, with the sibling ports owed. Because these fixes are in shared source, every model carries them; RT-BEXXU remains the primary, hardware-validated build.)* The "Model" column reflects what this build delivers.

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
