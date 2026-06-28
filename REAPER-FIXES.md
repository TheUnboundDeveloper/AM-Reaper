# RT-BE96U "reaper" — Hardened Build Fix List

Custom hardened build of Asuswrt-Merlin for the **ASUS RT-BE96U**.

- **Base version:** 3006.102.8_beta2
- **Custom version string:** `3006.102.8_beta2-reaper` (image: `RT-BE96U_..._beta2-reaper.trx`)
- **Branch:** `be96u-only` (local only — never pushed upstream)
- **Build target / applicable model:** **RT-BE96U only.** This tree was stripped to the RT-BE96U (`release/src-rt-5.04behnd.4916`). The fixes below live in the ASUS/Merlin-authored userspace, most of which is **shared source common to other Broadcom HND Asuswrt-Merlin models** — so the same flaws exist on those models running stock firmware, but this hardened image is produced for the RT-BE96U exclusively. The "Model" column reflects what this build delivers.

> Scope note: a few items are present in the source but **not compiled/active** in the RT-BE96U build (gated off by config). They were fixed defensively where cheap, and are flagged below.

---

## Summary

| Severity | Fixed | Deferred (design decision) | Not in BE96U build |
|---|---|---|---|
| Critical | C1 C2 C3 C4 C5 C6 C7 C8 (8) | — | — |
| High | H1 H2 H5 H6 H7 H8 H9 H10 H11 H12 H13 H14 (12) | H15 | H3, H4 |
| Medium | M1 M2 M3 M4 M5 M6 M7 M8 M9 M10 M11 M12 M13 M14 M15 M16 M17 M18 M19 (19) | M20, M21 | M22 |
| Low | L1 L2 L3 L4 L5 (5) | — | — |
| Internal | N1 N2 N3 N4 (IPsec shell sinks) | — | — |

Every Critical/High/Medium/Low present in the RT-BE96U-built source is fixed except the three deferred design items (H15, M20, M21).

---

## Fixes

All rows apply to **RT-BE96U**. "Commit" is the short hash on `be96u-only`.

### Critical
| ID | Component | Fix | Commit |
|---|---|---|---|
| C1 | httpd/web.c | `do_CoBrand_img` pre-auth stack overflow — bounded file extension copy | 54c17164cb |
| C2 | rc/rc_ipsec.c | IPsec cert-gen command injection via `ddns_hostname_x` — argv `eval()` + hostname validation | c950d8cf35 |
| C3 | rc/rc_ipsec.c | IPsec PKCS#12 import command injection — argv exec, password via file not `echo` | c950d8cf35 |
| C4 | rc/snmpd.c | snmpd.conf config-injection → RCE — strip CR/LF from community/sysName/Location/Contact | cbbbb83db3 |
| C5 | shared/nvparse.c | `get_wds_wsec` stack overflow — `strcpy`→`strlcpy` | 50d6fe9a59 |
| C6 | shared/misc.c | `asus_openssl_crypt` command injection — `popen`→argv exec helper | 8bc3189fa6 |
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
| H11 | shared/misc.c | `set_crt_parsed` cert-accumulation overflow — bounded | 7f831fa82a |
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

---

## Deferred — design decisions (NOT patched)

| ID | Component | Why deferred |
|---|---|---|
| H15 | shared/defaults.c | Default `http_username=admin` / `http_passwd=admin` (effectively u:admin p:NULL on stock). **Decision: keep** — the first-boot QIS wizard forces a username/password change (`x_Setting=0`), and leaving it unsecured is the owner's explicit choice. Changing the default risks the first-boot flow. |
| M20 | shared/shutils.c | `enc_str`/`dec_str` are a keyless bit-shift "encryption". In this tree their **only** caller is a debug `_dprintf` in `rc/rc.c` — they don't protect any production secret (real credential storage uses the `pw_enc`/`spwenc.o` blob). **Decision: keep** — replacing it breaks stored values for no practical gain. |
| M21 | shared/shutils.c | `generate_wireless_key` derives a default WiFi key from the (public) MAC. It has **zero callers in the buildable source** (dead code), and the live default-key path is already mitigated by forced first-boot setup. **Decision: keep.** |

## Not present in the RT-BE96U build (no action needed)
| ID | Reason |
|---|---|
| H3, H4 | `multi_wan.c`/`multi_wan_ipv6.c` gated on `RTCONFIG_MULTIWAN_IF` (off for BE96U). Fixed defensively in commit 433d008797. |
| H5 | TR069/TR181 opt-125 path not compiled (`RTCONFIG_TR069/TR181` off). Fixed defensively. |
| M22 | DSL-AX82U "optus" branch (`case MODEL_DSLAX82U` / `#if defined(DSL_AX82U)`) — not the BE96U model. |

## Coverage gap (not source-auditable)
Prebuilt binary blobs (`networkmap`, `wlceventd`, `asd`, `libbcm`, `pw_enc`/`spwenc.o`, `cfg_mnt`, login token-cookie generator) ship without source and were not assessed — would require binary reverse engineering.

---

## Round 2 — second-wave audit (2026-06-28): previously un-audited ASUS daemons

A follow-up pass over ASUS-authored userspace that **ships in the RT-BE96U image but was outside the first audit** (which covered httpd/rc/shared/libdisk). Every finding was **reachability-triaged** against `config_rt-be96u` + the built rootfs + the rc start paths — only in-build, reachable issues were fixed. Two daemons the raw audit flagged as "Critical" were proven **not in the BE96U build** and correctly dropped (see "Not in build" below).

Verified by a full `make rt-be96u` rebuild (gcc-10.3, 32-bit ARM): all changed files **compile and link** with zero new warnings at the edit sites; the `nand_squashfs` image repackaged successfully.

### Round 2 summary
| Tier | Count | Class | Commit |
|---|---|---|---|
| Tier 1 — root command/config injection | 5 | libovpn (same class as the IPsec fixes C2/C3/C7/N1–N4) | `59619bbdfa` |
| Tier 2 — memory safety in network listeners | 5 | OOB read/write, NULL-deref DoS | `59619bbdfa` |
| Tier 3 — defense-in-depth | 8 | perms, bounds, sanitize, format | `4b9439fd68` |

### Tier 1 — root command / config injection (libovpn)
| ID | Component | Fix | Commit |
|---|---|---|---|
| R-T1.1 | libovpn/openvpn_control.c | OpenVPN client up-handler ran `system()` on **remote-server-pushed** env (route_*/metric/trusted_ip/gateways) → `eval()` argv + per-token validation (inet_pton IPs, numeric metric, alnum dev) | `59619bbdfa` |
| R-T1.2 | libovpn/openvpn_control.c | Server-pushed `foreign_option DOMAIN` injected into the dnsmasq config — charset-validated before write | `59619bbdfa` |
| R-T1.3 | libovpn/openvpn_setup.c | `sed`+`system()` with DDNS hostname (nvram) — host/IP-validated, else safe placeholder | `59619bbdfa` |
| R-T1.4 | libovpn/openvpn_setup.c | `verify-x509-name` (nvram cn) directive injection (`"`/newline → `up`/`script-security`) — rejected | `59619bbdfa` |
| R-T1.5 | libovpn/openvpn_setup.c | `ccd_val` client-name path traversal + addr/netmask directive injection — name allowlist + IPv4 validation | `59619bbdfa` |

### Tier 2 — memory safety in network-listening daemons
| ID | Component | Fix | Commit |
|---|---|---|---|
| R-T2.1 | snooper/igmp.c | IGMPv3: unvalidated `ip_hl` advance → unsigned length underflow bypassing every size check; bounded + group-record walk bounded | `59619bbdfa` |
| R-T2.2 | urlfilterd/filter.c | NFQUEUE HTTP parser: header-length pointer math + `strstr` on a non-NUL-terminated payload → OOB read; length threaded in + bounded NUL-terminated copy | `59619bbdfa` |
| R-T2.3 | lltdc/src/qospktio.c | LLTD QoS reflect: copy length computed against the wrong buffer base (`g_txbuf` vs `g_rxbuf`) → size_t underflow OOB write; fixed base + clamped to TXBUFSZ | `59619bbdfa` |
| R-T2.4 | wsdd2/wsd.c | NULL-deref DoS: unchecked `strstr("\r\n")` on a TCP `POST` without CRLF (port 3702) | `59619bbdfa` |
| R-T2.5 | wsdd2/llmnr.c | LLMNR name label-walk + qtype/qclass read past packet end (UDP 5355) — bounded | `59619bbdfa` |

### Tier 3 — defense-in-depth
| ID | Component | Fix | Commit |
|---|---|---|---|
| R-T3.1 | infosvr/common.c | GETINFO response builders `strcpy`/`sprintf` → `strlcpy`/`snprintf` (dangerous `MANU_CMD system()` stays `#if 0`) | `4b9439fd68` |
| R-T3.2 | libcodb/codb_utils.c | `get_backup_db_path_by_datetime` source-length `strncpy/strncat`+`sprintf` into a 125-byte buffer → sized `snprintf` (latent; ~6 sibling path builders share the pattern — follow-up) | `4b9439fd68` |
| R-T3.3 | libovpn/openvpn_config.c, amvpn_routing.c | custom-config + VPN-director rule files written group-rw (0660) → 0600 | `4b9439fd68` |
| R-T3.4 | libovpn/openvpn_options.c | residual-parse `logmessage` format/arg mismatch; sanitize connecting client's username/addresses before `client_status` write | `4b9439fd68` |
| R-T3.5 | libovpn/openvpn_setup.c | `unlink` predictable `/tmp/ovpn_client_key_%d` before openvpn writes the tls-crypt-v2 secret | `4b9439fd68` |
| R-T3.6 | rstats/rstats.c | `get/set_meter_file` used `sizeof(pointer)` as the I/O length → real 64-byte size | `4b9439fd68` |
| R-T3.7 | lanauth/lanauth.c | zero the `challenge` buffer before each server read (no stale-byte hashing) | `4b9439fd68` |

### Round 2 — NOT in the RT-BE96U build (proven, no action)
| Component | Reason |
|---|---|
| aupnpc (IPC→`system()` command injection) | `RTCONFIG_AUPNPC` not set; no binary in the rootfs |
| wsc_upnp / wscd (base64 OOB-write, WSC memcpy) | builds `wscd` but it is **not installed** in this profile's rootfs |
| srvauth (TCP 8314 digest-offset OOB read) | separate binary, not shipped (only the lanauth client ships) |
| dblog/colog, psictl | not in the rootfs |

Same prebuilt-blob coverage gap as Round 1 (`networkmap`, `wlceventd`, `asd`, `cfg_mnt`, `eapd`, `wl/dhd`, `spwenc`) — binary RE only.

---

## Verification
**Round 1** changed files were compiled with the real RT-BE96U userspace toolchain (gcc-10.3, 32-bit ARM) and confirmed to build clean with no new warnings at the edit sites; `rc_ipsec.c` additionally passed a warning-diff vs the pre-hardening baseline. `httpd/web.c` and `libdisk/write_smb_conf.c` were syntax-checked at the time.

**Round 2** (both commits) was verified by a **full `make rt-be96u` end-to-end rebuild** on the gcc-10.3 toolchain: every changed file compiles **and links** in-context with zero new warnings at the edit sites, and the `nand_squashfs.pkgtb` image repackaged successfully ("Success!"). All remaining warnings in those files pre-date these changes.

> Flashable image: **`RT-BE96U_3006_102.8_beta2-g4b9439fd68_nand_squashfs.pkgtb`** (74 MB) in this folder is the current build — it contains every Round-1 and Round-2 fix and its baked version string is `beta2-g4b9439fd68` (matches the branch tip). The `_loader` variant (76 MB) is the firmware+bootloader/recovery image. For a normal upgrade, flash the **non-`loader`** `nand_squashfs.pkgtb` via Administration → Firmware Upgrade. (sha256 of squashfs image: `ebc1b1c26677456e4f2dda49d86bb8038220d33b9acdbe0ce754177dbe5488c2`.)

## Round 2 commits (branch `be96u-only`, local only — never pushed)
- `59619bbdfa` — Tier 1+2 (libovpn injection class; snooper/urlfilterd/lltdc/wsdd2 memory safety)
- `4b9439fd68` — Tier 3 (infosvr, libovpn perms/sanitize/tmp, libcodb path, rstats, lanauth)
