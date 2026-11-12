#!/usr/bin/env python3
"""Review 2026-11-03 - the LOW, Latent and Bug fixes (the HIGH/MEDIUM ones are test_review_2026_11_03.py).

Each fix is pinned by the text it added and, where one existed, the text it replaced:
  rc / shared   C-2 f_write default 0644, /tmp/reboot and /tmp/upgrade honoured only when root made them,
                SDN / VPN resolver lists 0644; C-3 gencert umask 077 + key modes, /jffs/cert.tgz 0600;
                C-4 PPP/VPN option files 0600; C-5 root-run hooks 0700, web roots 0755; C-7 WireGuard PSK
                0600; D-3 chpass() through chpasswd's stdin; F-3 hostapd configs and cfg_server under
                umask 077; ssh authorized_keys 0600; the Gatekeeper sink no longer owns /dev/null; rexport
                refuses control characters; E-7 kptr_restrict / dmesg_restrict; panic_on_oops is a switch.
  httpd / www   A-1 the cross-site test on both listeners; A-2 three side-effect .asp pages; A-3 a fixed
                nvram key for the IPsec upload; Range "bytes=N" (both sites); get_file_md5 name charset;
                findasus name/address charset; repeater SSID escaped; B-2 Analytics POST bodies; Reaper_LAN
                CSV formula guard; Main_Password username as a JS literal; Firmware node button; AiMesh
                AP-mode names encoded at ingestion.
  daemons       D-1 Wallguard list gate (also RUN here against the real wallguardc and sh); D-2 rednsd
                evicts the oldest stalled handshake when full; D-4 diag secret classes; rednsd pid O_NOFOLLOW; rdnsmapd header
                re-check; rtrafd save stamp bound; libipt_TRIGGER negative ports; diag section 19 drops the
                lab exec echo; firmware download checked in /tmp/reaper before it reaches /tmp/linux.trx;
                wallguard unbreak minutes digits-only.
  kernel        E-6 ipt_TRIGGER lock held across lookup+use, flush frees only what it cancelled (2026-11-06:
                checkentry no longer flushes everything - a per-rule reference closes a deleted trigger's ports
                at once and keeps the others' through any table replace); ct NULL; E-8 bcm_mcast CAP_SYS_ADMIN; E-9 xt_webstr per-CPU state, bounded scan,
                linear-data length (v4 and v6); dnsmq copy_from_user; proc_cmd terminator; xhci
                ubus_credits upper bound.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] / REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "init.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
PLAT = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916"))
CC = shutil.which("gcc") or shutil.which("cc")
SH = shutil.which("sh")

def rd(p):
    return open(p, encoding="latin-1").read() if os.path.isfile(p) else ""
def nocomment(t):
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("//"))
def func(t, head):
    m = re.search(r"\n" + re.escape(head) + r".*?\n\}\n", t, re.S)
    return m.group(0) if m else ""

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def pin(rel, name, has=(), hasnt=(), count=None, base=SRC):
    t = rd(os.path.join(base, rel))
    if not t:
        check("%s: %s present" % (name, rel), False); return
    miss = [h for h in has if h not in t]
    left = [h for h in hasnt if h in t]
    ok = not miss and not left
    if ok and count:
        ok = t.count(count[0]) == count[1]
        miss = ["%r x%d (found %d)" % (count[0], count[1], t.count(count[0]))] if not ok else []
    check(name, ok, {"missing": miss, "still there": left})

# ---------------------------------------------------------------- rc / shared
pin("shared/files.c", "C-2: f_write's default mode is 0644", count=("if (cmode == 0) cmode = 0644;", 2),
    hasnt=("if (cmode == 0) cmode = 0666;",))
pin("shared/files.c", "C-2: f_root_owned / f_read_root_string exist",
    has=("int f_root_owned(const char *path)", "st.st_uid == 0", "int f_read_root_string(const char *path, char *buffer, int max)"))
pin("shared/shared.h", "C-2: ...and are declared", has=("extern int f_root_owned(const char *path);", "extern int f_read_root_string("))
for f in ("rc/watchdog.c", "rc/sched_daemon.c", "rc/check_watchdog.c"):
    pin(f, "C-2: %s reads /tmp/reboot and /tmp/upgrade only when root made them" % f,
        has=('f_read_root_string("/tmp/reboot",', 'f_read_root_string("/tmp/upgrade",'),
        hasnt=('f_read_string("/tmp/reboot",', 'f_read_string("/tmp/upgrade",'))
pin("httpd/web.c", "C-2: httpd's reboot-in-progress test needs a root-owned flag",
    has=('f_root_owned("/tmp/reboot")',), hasnt=('f_exists("/tmp/reboot")',))
pin("rc/sdn.c", "C-2: SDN resolver list 0644", has=("chmod(path, 0644);\t/* reaper (review 2026-11-03, C-2)",))
pin("rc/vpnc_fusion.c", "C-2: VPN Fusion resolv file 0644", has=("chmod(resolv_file, S_IRUSR|S_IWUSR|S_IRGRP|S_IROTH);",),
    hasnt=("S_IRGRP|S_IWGRP|S_IROTH|S_IWOTH);",))
pin("rc/wireguard.c", "C-7: WireGuard PSK file 0600", has=('nvram_pf_safe_get(c_prefix, "psk"), 0, 0600);',))
for f in ("pppd.c", "vpnc.c", "vpnc_legacy.c", "vpnc_fusion.c"):
    t = nocomment(rd(os.path.join(SRC, "rc", f)))
    check("C-4: rc/%s writes the options file under umask 077" % f, "mask = umask(0077);" in t and "umask(0000)" not in t)
svc = rd(os.path.join(SRC, "rc/services.c"))
pin("rc/services.c", "C-5: chilli hooks 0700, web roots 0755",
    has=("chmod(file_name, 0700);", "chmod(path, 0700);\t/* reaper (review 2026-11-03, C-5)",
         'chmod("/tmp/diag_db_cloud/upload", 0755);', 'chmod("/tmp/diag_db_cloud/download", 0755);'),
    hasnt=('chmod("/tmp/uamsrv/www", 0777);', 'chmod("/tmp/diag_db_cloud/upload", 0777);', 'chmod("/tmp/diag_db_cloud/download", 0777);'))
ch = nocomment(func(svc, "chpass(char *user, char *pass)"))
check("D-3: chpass() refuses ':' / line breaks and pipes the pair to chpasswd",
      'popen("chpasswd", "w")' in ch and "strpbrk(user" in ch and 'eval("chpasswd.sh"' not in ch, ch[:200])
pin("others/chpasswd.sh", "D-3: chpasswd.sh has no temp file and no ==",
    has=("printf '%s:%s\\n' \"$1\" \"$2\" | chpasswd",), hasnt=("/tmp/tmpchpw", '" == "'))
w = func(svc, "int reaper_start_hapd_wpasupp(int skip)")
check("F-3: reaper_start_hapd_wpasupp() wraps the closed generator in umask 077",
      "umask(077)" in w and "start_hapd_wpasupp(skip)" in w and "umask(um)" in w, w[:200])
bare = [m.start() for m in re.finditer(r"(?<![_a-z])start_hapd_wpasupp\(", nocomment(svc))]
check("F-3: services.c calls only the wrapper (the one bare call is inside it)", len(bare) == 1, len(bare))
for f in ("rc/rc.c", "rc/watchdog.c"):
    t = nocomment(rd(os.path.join(SRC, f)))
    check("F-3: %s calls the wrapper" % f, "reaper_start_hapd_wpasupp(" in t and not re.search(r"(?<![_a-z])start_hapd_wpasupp\(", t))
check("F-3: cfg_server starts under umask 077 (both sites)",
      svc.count("mode_t um = umask(077);\n\t\t\tret = _eval(cfg_server_argv") == 2)
pin("rc/ssh.c", "authorized_keys is 0600", has=('f_write_string("/root/.ssh/authorized_keys", buf, 0, 0600);',),
    hasnt=('f_write_string("/root/.ssh/authorized_keys", buf, 0, 0700);',))
pin("rc/gatekeeper.c", "the Gatekeeper sink logs to its own file, not /dev/null",
    has=('"log-facility=" GK_DIR "/sink.log',), hasnt=('"log-facility=/dev/null',))
pin("rc/rexport.c", "rexport refuses control characters in its settings", has=("control character in export settings - refusing",))
pin("httpd/gencert.sh", "C-3: gencert.sh runs under umask 077 and sets key modes",
    has=("cd /etc\n# reaper", "umask 077\n", "chmod 600 ${HTTPD_ROOTCA_KEY}", "chmod 600 server.pem /jffs/cert.tgz"))
init = rd(os.path.join(SRC, "rc/init.c"))
pin("rc/init.c", "C-3: /jffs/cert.tgz is made 0600 at boot", has=('chmod("/jffs/cert.tgz", 0600);',))
pin("rc/init.c", "E-7: kptr_restrict=2 and dmesg_restrict=1",
    has=('f_write_string("/proc/sys/kernel/kptr_restrict", "2", 0, 0);', 'f_write_string("/proc/sys/kernel/dmesg_restrict", "1", 0, 0);'))
pin("rc/init.c", "panic_on_oops is 1", has=('"/proc/sys/kernel/panic_on_oops", "1"',), hasnt=('"/proc/sys/kernel/panic_on_oops", "3"',))

# ---------------------------------------------------------------- httpd / www
pin("httpd/httpd.c", "A-1: the browser cross-site test applies on both listeners",
    has=("xsite = ua && !strncmp(ua, \"Mozilla/\", 8);",), hasnt=("xsite = !tls && ua",))
pin("httpd/httpd.c", "A-1: the no-header branch is braced (an unbraced else made the UA test run for every request)",
    has=("\telse {\n\t\t/* neither header: cross-site when a browser sent it, on either listener",
         "\t\t(void)tls;\n\t\txsite = ua && !strncmp(ua, \"Mozilla/\", 8);\n\t}\n"))
pin("httpd/httpd.c", "A-2: the three side-effect .asp pages get the cross-site check",
    # review 2026-11-11 (B-2): a list matched by file name now ("./apscan.asp" was not "apscan.asp" to strcmp)
    has=('{ "start_autodet.asp", "ajax_trigger_chk_sta.asp", "apscan.asp",', "hit = !strcmp(base, acting[i]);"))
pin("httpd/httpd.c", "Range: one parser (reaper_byte_range) for send_headers and do_file, 206 for a served range",
    has=("static int reaper_byte_range(const char *hdr, long long total, off_t *s, off_t *e)",
         "int rr = reaper_byte_range(request_content_range, request_file_size, &rr_s, &rr_e);", "status = 206;",
         "if (reaper_byte_range(request_content_range, request_file_size, &content_start, &content_end))"),
    hasnt=("content_end = strtoll(err+1, &err, 10);",))
web = rd(os.path.join(SRC, "httpd/web.c"))
pin("httpd/web.c", "A-3: the IPsec upload sets ipsec_profile_item, not the header's key",
    has=('nvram_set("ipsec_profile_item", value);\n\t\t\t\t\t\t\t\tsnprintf(upload_fifo, sizeof(upload_fifo), "/jffs/ipsec/%s.crt", value);',))
md = func(web, "get_file_md5(") or web[web.find("md5sum %s | cut -b-32") - 600: web.find("md5sum %s | cut -b-32")]
check("get_file_md5: the name is charset-gated before the md5sum command line",
      "strspn(file, \"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._/-\")" in md)
pin("httpd/web.c", "findasus: LAN-supplied model name and address kept to their characters",
    has=("asusdiscovery fills this list from LAN replies", "if(check_xss_blacklist(ssid, 0) || strchr(ssid, '\\\\'))"))
pin("httpd/sysdeps/web-broadcom-am.c", "the repeater SSID is escaped",
    has=("char rsb[200];", "str_escape_quotes(rsb,", '"\\"Repeater ( SSID local: %s )\\"", rsb);'))
W = lambda f: os.path.join("www", f)
pin(W("aimesh/aimesh_topology.html"), "AiMesh AP-mode names encoded at ingestion",
    has=("htmlEnDeCode.htmlEncode(String(d.name))", "htmlEnDeCode.htmlEncode(String(d.host))"))
pin(W("Main_Password.asp"), "Main_Password: the username is a JS literal",
    has=('postData.cur_username = <% nvram_get_js("http_username"); %>;',), hasnt=("postData.cur_username = '<% nvram_get(",))
pin(W("Reaper_Firmware.asp"), "Firmware: the node address travels in a data attribute",
    has=('data-ip="\' + esc(ip) + \'" onclick="openNode(this.dataset.ip)"',), hasnt=("onclick=\"openNode(\\''",))
pin(W("Reaper_LAN.asp"), "Reaper_LAN: CSV cells are formula-neutralised and the import strips the guard",
    has=("[r.mac, r.ip, r.dns, r.host].map(cell).join(',')", "replace(/^'(?=[=+\\-@])/, '')"))
anl = rd(os.path.join(SRC, W("Reaper_Analytics.asp")))
check("B-2: Analytics sends its state-changing calls (probe, save, test) as POST bodies; status stays a GET",
      "x.send(body);" in anl and not re.search(r"xhr\('GET', '/reaper_export\.cgi\?action=(probe|save|test)", anl)
      and "xhr('GET', q," not in anl and anl.count("xhr('POST',") >= 4)
for f in ("aimesh/aimesh_topology.html", "Main_Password.asp", "Reaper_Firmware.asp", "Reaper_LAN.asp", "Reaper_Analytics.asp"):
    b = open(os.path.join(SRC, W(f)), "rb").read() if os.path.isfile(os.path.join(SRC, W(f))) else b""
    check("www %s: the review lines are plain ASCII" % f,
          all(c < 128 for l in b.split(b"\n") if b"review 2026-11-03" in l for c in l))

# ---------------------------------------------------------------- daemons and scripts
wg = rd(os.path.join(SRC, "wallguard/wallguard.sh"))
pin("wallguard/wallguard.sh", "D-1: the update gates a download through list_gate before the swap",
    has=("list_gate() {", '[ -z "$why" ] && why=$(list_gate "$id" "$L/$id.new")'))
i_gate, i_mv = wg.find('why=$(list_gate "$id"'), wg.find('mv "$L/$id.new" "$L/$id"')
check("D-1: ...and the gate comes before the mv", 0 <= i_gate < i_mv, (i_gate, i_mv))
pin("wallguard/wallguard.sh", "wallguard unbreak: minutes are digits only", has=("case \"$mins\" in ''|*[!0-9]*|??????*) mins=15 ;; esac",))
rn = rd(os.path.join(SRC, "rednsd/rednsd.c"))
pin("rednsd/rednsd.c", "D-2: when every slot is taken, the oldest handshake (500 ms+) makes room",
    has=("} else if (same < PER_PEER) {", "conns[i].state == C_HANDSHAKE && (!h || conns[i].hs_deadline < h->hs_deadline)",
         "now_ms() + HS_MS - h->hs_deadline >= 500", "conn_close(h);"),
    hasnt=("hs_same",))	# the per-address cap of 2 was dropped: it broke the 8-per-device design (test_rednsd.py)
pin("rednsd/rednsd.c", "rednsd pid file never through a link",
    has=("O_WRONLY | O_CREAT | O_TRUNC | O_NOFOLLOW | O_CLOEXEC, 0644)",), hasnt=('FILE *pf = fopen(pidfile, "w");',))
rm = rd(os.path.join(SRC, "rdnsmapd/rdnsmapd.c"))
i_trim, i_chk, i_q = rm.find("n = l4 + ul;"), rm.find("if (dns + 12 > n)\t/* review 2026-11-03"), rm.find("q = p + dns;")
check("rdnsmapd: the DNS header is re-checked after the UDP trim", 0 <= i_trim < i_chk < i_q, (i_trim, i_chk, i_q))
pin("rtrafd/rtrafd.c", "rtrafd: an implausible save stamp is dropped", has=("h.saved > 4102444800LL", "h.saved = 0;"))
pin("iptables-1.4.x/extensions/libipt_TRIGGER.c", "libipt_TRIGGER: negative ports refused",
    has=("if (port <= 0 || port > 65535)", "if (maxport <= 0 || maxport > 65535)"), hasnt=("if (port == 0 || port > 65535)",))
pin("others/reaper_diag", "D-4: the diag secret classes cover WG keys, PSKs, IPsec, client lists, security strings, SSH keys",
    has=("|_priv$|_ppsk|ipsec_profile_|_clientlist$|_security$|sshd_authkeys/) cls=\"SEC\"",))
pin("others/reaper_diag", "diag section 19 drops the lab exec echo",
    has=("tail -150 /tmp/syslog.log 2>/dev/null | grep -vF 'rmcpd-lab: exec:' | sed",))
# -vF on purpose: test_reaper_diag_counters deletes the first "| grep -v 'rmcpd-lab: exec:' " to prove 19b's filter
# is checked, and this line comes first
up = rd(os.path.join(SRC, "rom/webs_scripts/reaper_webs_upgrade.sh"))
i_dl, i_sha, i_mv2, i_ls = up.find('-O "$DL"'), up.find('got=$(sha256sum "$DL"'), up.find('mv -f "$DL" "$FW"'), up.find('fw_ls=$(ls -ln "$FW"')
check("firmware download: fetched and hashed in /tmp/reaper, moved to the flash path, then checked",
      "DL=/tmp/reaper/webs_fw.trx" in up and 0 <= i_dl < i_sha < i_mv2 < i_ls and '-O "$FW"' not in up, (i_dl, i_sha, i_mv2, i_ls))
if SH:
    for s in ("wallguard/wallguard.sh", "rom/webs_scripts/reaper_webs_upgrade.sh", "others/reaper_diag", "others/chpasswd.sh", "httpd/gencert.sh"):
        r = subprocess.run([SH, "-n", os.path.join(SRC, s)], capture_output=True, text=True)
        check("sh -n %s" % s, r.returncode == 0, r.stderr)

# D-1 run for real: the tree's wallguardc and the script's own list_gate()
if CC and SH and wg:
    tmp = tempfile.mkdtemp(prefix="rev1103l_")
    try:
        x = os.path.join(tmp, "wallguardc")
        r = subprocess.run([CC, "-O1", "-o", x, os.path.join(SRC, "wallguard/wallguardc.c")], capture_output=True, text=True)
        check("D-1: wallguardc builds on the host", r.returncode == 0, r.stderr)
        m = re.search(r"\nlist_gate\(\) \{.*?\n\}\n", wg, re.S)
        if r.returncode == 0 and m:
            d = os.path.join(tmp, "d"); os.makedirs(d)
            open(os.path.join(tmp, "fn.sh"), "w").write(m.group(0))
            open(os.path.join(d, "build.json"), "w").write(
                '{"built":1,"names":4000,"allow":0,"full":0,"sources":[{"bit":1,"id":"oisd","missing":0,"lines":4000,'
                '"names":4000,"unique":4000,"allows":0,"unsupported":0,"invalid":0,"capped":0}]}\n')
            hosts = lambda n: "".join("0.0.0.0 ad%d.example.com\n" % i for i in range(n))
            page = "<!DOCTYPE html>\n" + "".join("<div>Service unavailable %d</div>\n" % i for i in range(200))
            cosm = hosts(3000) + "".join("example.com##.ad-banner%d\n" % i for i in range(5000))
            cases = [("oisd", hosts(4000), 0, "a same-size list is taken"), ("oisd", hosts(500), 0, "a list that shrank is taken"),
                     ("oisd", page, 1, "an HTML error page is refused"), ("oisd", page + hosts(10), 1, "an error page with stray names is refused"),
                     ("oisd", cosm, 0, "a list with many cosmetic rules is taken"), ("new", hosts(50), 0, "a first download is taken"),
                     ("new", page, 1, "a first download that is an error page is refused"), ("oisd", "", 1, "an empty file is refused")]
            for i, (lid, body, want, what) in enumerate(cases):
                f = os.path.join(tmp, "l%d" % i); open(f, "w").write(body)
                r = subprocess.run([SH, "-c", '. "$1"; list_gate "$2" "$3"', "sh", os.path.join(tmp, "fn.sh"), lid, f],
                                   capture_output=True, text=True, env=dict(os.environ, D=d, SC=x))
                check("D-1 list_gate: " + what, r.returncode == want, (r.returncode, r.stdout.strip()))
            check("D-1 list_gate leaves no scratch table behind", sorted(os.listdir(d)) == ["build.json"], os.listdir(d))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
else:
    print("SKIP (part): no host C compiler or sh - list_gate not run")

# ---------------------------------------------------------------- metal review of _r1 (batch 6)
wl = nocomment(rd(os.path.join(SRC, "rc/wireless.c")))
check("F-3 (metal): start_nas() - the boot path - generates the hostapd configs through the umask-077 wrapper",
      "reaper_start_hapd_wpasupp(0);" in wl and not re.search(r"(?<![_a-z])start_hapd_wpasupp\(", wl))
pin("rc/sysdeps/wps-broadcom.c", "F-3 (metal): the WPS hostapd restarts regenerate the config under umask 077",
    has=("static int reaper_hapd_wps_ob(int radio_idx)", "mode_t um = umask(077);"),
    count=("if(reaper_hapd_wps_ob(wps_band) != 0) {", 2), hasnt=("if(restart_hostapd_per_radio_wps_ob(wps_band) != 0)",))
pin("rc/services.c", "metal: /etc/pam.d is root 0755 (it holds the OpenVPN server's password policy)",
    has=('reaper_secure_dir("/etc/pam.d", 0755);',), hasnt=('mkdir_if_none("/etc/pam.d");',))
pin("shared/misc.c", "C-3 (metal): restore_cert() resets certificate 644 / key 600 after the untar",
    has=('chmod(rp_path, strstr(*v, "key") ? 0600 : 0644);',))
pin("rc/init.c", "metal: /var/state/parport sticky, /etc/email root 0755",
    has=('mkdir("/var/state/parport", 01777);', 'mkdir("/var/state/parport/svr_statue", 01777);', 'mkdir("/etc/email", 0755);'),
    hasnt=('mkdir("/var/state/parport", 0777);',))
pin("libdisk/disk_share.c", "metal: add_folder() restores the umask after its 0777 share folder",
    has=("mode_t um = umask(0000);\n\t\tresult = mkdir(full_path, 0777);\n\t\tumask(um);",), hasnt=("\tumask(0000);\n\tresult = mkdir(full_path, 0777);",))
usbc = rd(os.path.join(SRC, "rc/usb.c"))
i_sw, i_tv = usbc.find("reaper_share_files_private(mountpoint);"), usbc.find("test_of_var_files(mountpoint);")
check("metal: the share-permission files lose group/other write at every mount, before libdisk reads them",
      "static void reaper_share_files_private(const char *mnt)" in usbc and 0 <= i_sw < i_tv and "chmod(p, st.st_mode & 07755);" in usbc, (i_sw, i_tv))
pin("rc/services.c", "chilli: no ipup/ipdown pointing at scripts nothing generates",
    hasnt=('fprintf(fp, "ipup /tmp/chilli/ip-up.sh\\n");', 'fprintf(fp, "ipdown /tmp/chilli/ip-down.sh\\n");'))
pin("rc/services.c", "Gatekeeper: an HTTPS-only GUI still runs the plain-HTTP instance for the captive page",
    has=('if (enable != 1 || (nvram_match("gk_enable", "1") && !nvram_match("gk_captive", "0")))',))
pin("rc/gatekeeper.c", "Gatekeeper: start_gk() starts it when the GUI is HTTPS-only",
    has=('if (nvram_get_int("http_enable") == 1 && !nvram_match("gk_captive", "0"))\n\t\tstart_httpd();',))
hc = rd(os.path.join(SRC, "httpd/httpd.c"))
i_cap, i_red = hc.find("if (reaper_gk_captive_check(temp_ip_str)) {"), hc.find('if (!do_ssl && nvram_get_int("http_enable") == 1 && strcmp(temp_ip_str, "127.0.0.1")) {')
i_auth = hc.find("auth_result = auth_check(url, file, cookies, fromapp, &add_try);")
check("Gatekeeper: that instance sends everything but the waiting page to HTTPS, before auth", 0 <= i_cap < i_red < i_auth, (i_cap, i_red, i_auth))
if CC:
    m = re.search(r"\nstatic int reaper_byte_range\(.*?\n\}\n", hc, re.S)
    if m:
        tmp = tempfile.mkdtemp(prefix="rev1103r_")
        try:
            c = os.path.join(tmp, "r.c"); x = os.path.join(tmp, "r")
            open(c, "w").write("#include <stdio.h>\n#include <stdlib.h>\n#include <strings.h>\n#include <sys/types.h>\n" + m.group(0) +
                "int main(int n, char **v){ int i; for (i = 2; i < n; i++){ off_t s = -1, e = -1; int r = reaper_byte_range(v[i][0] ? v[i] : NULL, atoll(v[1]), &s, &e);"
                " printf(\"%d %lld %lld\\n\", r, (long long)(r ? s : -1), (long long)(r ? e : -1)); } return 0; }\n")
            r = subprocess.run([CC, "-std=gnu99", "-Wall", "-o", x, c], capture_output=True, text=True)
            check("Range: reaper_byte_range() compiles", r.returncode == 0, r.stderr)
            if r.returncode == 0:
                cases = [("bytes=0-99", "1 0 99"), ("bytes=0-", "1 0 999"), ("bytes=-100", "1 900 999"), ("bytes=990-2000", "1 990 999"),
                         ("bytes=1000-", "0 -1 -1"), ("bytes=5", "0 -1 -1"), ("items=0-1", "0 -1 -1"), ("bytes=10-5", "0 -1 -1"),
                         ("bytes=-0", "0 -1 -1"), ("", "0 -1 -1"), ("BYTES=1-1", "1 1 1")]
                out = subprocess.run([x, "1000"] + [k for k, _ in cases], capture_output=True, text=True).stdout.split("\n")
                for (k, want), got in zip(cases, out):
                    check("Range: %r of a 1000-byte file -> %s" % (k, want), got == want, got)
                out0 = subprocess.run([x, "0", "bytes=0-99"], capture_output=True, text=True).stdout.strip()
                check("Range: a file of unknown size (0) is never ranged", out0 == "0 -1 -1", out0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        check("Range: reaper_byte_range() found", False)

# ---------------------------------------------------------------- B-1, B-3, F-1, F-4 (batch 7) and E-10
inj = rd(os.path.join(SRC, "httpd/reaper_inject.c"))
check("B-1: the injector carries the token hook for start_apply*.htm, apply.cgi and applyapp.cgi (forms, XHR, fetch)",
      "#define REAPER_TOKEN_HEAD" in inj and "start_apply2?\\\\.htm|apply\\\\.cgi|applyapp\\\\.cgi" in inj
      and "HTMLFormElement.prototype.submit" in inj and "XMLHttpRequest.prototype" in inj and "window.fetch" in inj)
check("B-1: the hook is written only into authenticated responses, with a plain alphanumeric token",
      "if (reaper_req_authed && tn > 0 && tn <= 64 &&" in inj and 'strspn(tk, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") == tn' in inj)
check("B-1: skip-listed and QIS_* pages get the hook alone (mode 6), no theme",
      inj.count("return 6;") == 2 and "if (mode != 6)\n\t\t\tRP_PUT(conn_fp, RP_LINK_CSS);" in inj and "case 6:" in inj)
check("B-1: httpd marks a request authenticated only after auth_check() passed, and clears it per request",
      "int reaper_req_authed = 0;" in hc and "\treaper_req_authed = 0;\n\treaper_req_post" in hc
      # review 2026-11-11 (B-3): the connection deadline is switched off on the next line, still inside the #ifndef
      and re.search(r"\t\t\t\t\treaper_req_authed = 1;\n(\t\t\t\t\treaper_conn_deadline_off\(\);[^\n]*\n)?#endif\n", hc) is not None)
wb = rd(os.path.join(SRC, "httpd/web.c"))
ok_fn = func(wb, "static int reaper_apply_token_ok(")
check("B-1: browser applies need the token; the app, scripts, a pristine-stock UI and AiMesh nodes are exempt",
      "check_user_agent(user_agent) != FROM_BROWSER" in ok_fn and 'nvram_match("reaper_inject", "0")' in ok_fn and 'nvram_match("re_mode", "1")' in ok_fn)
check("B-1: start_apply*.htm and apply.cgi / applyapp.cgi enforce it",
      'reaper_apply_token_ok(websGetVar(wp, "http_id", NULL), "start_apply")' in wb and 'reaper_apply_token_ok(get_cgi_json("http_id", root), "apply.cgi")' in wb)
radp = rd(os.path.join(SRC, W("Reaper_RADIUS.asp")))
check("B-3: the RADIUS secrets are not printed; presence flags; only a typed secret is sent",
      'nvram_get_js("wl0_radius_key")' not in radp and "var KSET = {0:" in radp and "if (q('ky' + i).value !== '') ch[K(b, 'key')]" in radp)
dsh = rd(os.path.join(SRC, W("Main_ReaperDash.asp")))
check("B-3: the dashboard does not print the WPS PIN; it is read on Show", 'nvram_get_js("secret_code")' not in dsh and 'id="rid_pin_show"' in dsh
      and "appGet.cgi?hook=nvram_get(secret_code)" in dsh)
mlop = rd(os.path.join(SRC, W("Reaper_MLO.asp")))
check("B-3: MLO loads no 'security' field; the password is fetched on Show",
      "'disabled', 'security']" not in mlop and "appGet([v.dataset.key]" in mlop)
check("B-3: the WireGuard server page prints no key (wgs1_psk is the use-a-PSK switch, not a key)",
      "psk: '0'" in rd(os.path.join(SRC, W("Reaper_VPNServer.asp"))))
svc2 = rd(os.path.join(SRC, "rc/services.c"))
check("F-1: the LLTD responder and client are not started",
      "client; its only consumer is Windows' Network Map. */\n\treturn 0;" in svc2 and "\treturn 0;\t/* review 2026-11-03 (F-1): the LLTD client goes with the responder */" in svc2)
pin("httpd/Makefile", "F-4: httpd is PIE, full RELRO, FORTIFY", has=("CFLAGS += -fPIE -D_FORTIFY_SOURCE=2", "-pie -Wl,-z,relro,-z,now"))
pin("rc/Makefile", "F-4: rc's own objects PIE, full RELRO, no FORTIFY (PID 1)", has=("$(OBJS): CFLAGS += -fPIE", "-pie -Wl,-z,relro,-z,now"),
    hasnt=("FORTIFY_SOURCE=2",))
pin("infosvr/Makefile", "F-4: infosvr is PIE, full RELRO, FORTIFY", has=("-fPIE -D_FORTIFY_SOURCE=2", "-pie -Wl,-z,relro,-z,now"))
pin("Makefile", "F-4: dnsmasq is PIE, full RELRO, FORTIFY", has=("-std=gnu99 -fPIE -D_FORTIFY_SOURCE=2", "-Wl,--gc-sections $(EXTRALDFLAGS) -pie -Wl,-z,relro,-z,now"))
ENG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
lib, ver = rd(os.path.join(ENG, "_reaper_build_lib.sh")), rd(os.path.join(ENG, "reaper_verify.sh"))
if lib and ver:
    i_ex, i_mk = lib.find("export KBUILD_BUILD_USER=reaper KBUILD_BUILD_HOST=reaper"), lib.find('nice make "$TARGET"')
    check("E-10: the build library sets the kernel build user/host before make", 0 <= i_ex < i_mk, (i_ex, i_mk))
    check("E-10: reaper_verify checks the vmlinux banner and never prints it",
          '"kernel-banner"' in ver and '*"(reaper@reaper)")' in ver and 'echo "$_kb"' not in ver)
else:
    print("SKIP (part): engine files not beside this test")

# ---------------------------------------------------------------- kernel and BSP
if not os.path.isdir(PLAT):
    print("SKIP (part): no platform tree at %s - kernel pins not checked" % PLAT)
else:
    pin("bcmdrivers/opensource/char/mcast/impl1/bcm_mcast_netlink.c", "E-8: bcm_mcast netlink needs CAP_SYS_ADMIN",
        has=("if ( !netlink_capable(skb, CAP_SYS_ADMIN) )",), base=PLAT)
    pin("bcmdrivers/opensource/include/bcm963xx/proc_cmd.h", "proc_cmd leaves room for the terminator",
        has=("if (count > PROC_CMD_STRING_SIZE - 1)",), hasnt=("if (count > PROC_CMD_STRING_SIZE)\n",), base=PLAT)
    pin("bcmdrivers/opensource/bus/usb/impl1/bcm_bca_usb_xhci.c", "xhci ubus_credits has an upper bound",
        has=("if (ubus_credits > 32) {", "} else if (ubus_credits > 0) {"), base=PLAT)
    pin("kernel/linux-4.19/net/ipv4/netfilter/dnsmq.c", "dnsmq copies the user buffer with copy_from_user",
        count=("if (copy_from_user(s, buffer, length))", 2), hasnt=("memcpy(s, buffer, length);",), base=PLAT)
    ws = rd(os.path.join(PLAT, "kernel/linux-4.19/net/netfilter/xt_webstr.c"))
    check("E-9: xt_webstr keeps its HTTP state per CPU",
          "static DEFINE_PER_CPU(httpinfo_t, htinfo_pcpu);" in ws and not re.search(r"\nhttpinfo_t htinfo;", ws))
    check("E-9: find_pattern2 bounds the terminator scan before reading",
          "for (j = *numoff, k = 0; j < dlen && data[j] != term; j++, k++)" in ws)
    lin = "unsigned int datalen = (data < skb_tail_pointer(skb)) ? (unsigned int)(skb_tail_pointer(skb) - data) : 0;"
    gh, gh6 = func(ws, "static int get_http_info(const struct sk_buff"), func(ws, "static int get_http_info6(const struct sk_buff")
    check("E-9: get_http_info / get_http_info6 measure the data to the end of the linear buffer",
          lin in gh and lin in gh6 and "ntohs(ip6h->payload_len)" not in gh6, (len(gh), len(gh6)))
    tg = rd(os.path.join(PLAT, "kernel/linux-4.19/net/ipv4/netfilter/ipt_TRIGGER.c"))
    mac = tg[tg.find("#define LIST_FIND"): tg.find("struct ipt_trigger {")]
    check("E-6: LIST_FIND no longer drops the lock inside", "read_lock_bh" not in mac and "read_unlock_bh" not in mac and mac)
    check("E-6: each of the four lookups takes the read lock",
          len(re.findall(r"read_lock_bh\(&trigger_lock\);[^\n]*\n\ttrig = LIST_FIND\(", tg)) == 4)
    check("E-6: the refresh is mod_timer_pending under the caller's lock",
          "mod_timer_pending(&trig->timeout, jiffies + (TRIGGER_TIMEOUT * HZ));" in func(tg, "static void trigger_timer_refresh("))
    fl = func(tg, "static void trigger_flush(")
    check("E-6: flush frees only what it cancelled, conntrack sweep outside the lock",
          "if (del_timer(&trig->timeout))\n\t\t\tlist_move(&trig->list, &dead);" in fl
          and fl.find("write_unlock_bh") < fl.find("nf_ct_iterate_cleanup_net"))
    dn = func(tg, "static unsigned int trigger_dnat(")
    check("E-6: trigger_dnat returns when there is no conntrack entry, before the lookup",
          0 <= dn.find("if (ct == NULL)") < dn.find("LIST_FIND"))
    ce = nocomment(func(tg, "static int checkentry("))
    # 2026-11-06 (E-6 follow-up): the whole-list flush is gone - a removed rule still closes its ports, through a
    # per-rule reference (checkentry takes it, destroy drops it); test_kernel_round_2026_11_06.py runs that code
    check("checkentry takes the rule's reference instead of flushing every trigger",
          "trigger_flush();" not in ce and "trig_rule_get(info)" in ce and ".destroy = destroy," in tg)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
