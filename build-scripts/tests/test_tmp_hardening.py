#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reaper's /tmp hardening (audit 2026-10-03 F1 / 2026-10-06 V3 and V5, remediated 2026-10-09).

WHY THIS EXISTS. /tmp is sticky and world-writable and dnsmasq (every instance) runs as
nobody. A process with that foothold could pre-create a directory root writes scripts
into, or plant a file or symlink where root writes and then reads back - the exporter's
curl config and sed script, the update manifest and its key, the restore's staged
settings. The fix has four layers and each is pinned here:
  1. rc/init.c turns on fs.protected_symlinks/hardlinks/regular/fifos next to the /tmp chmod;
  2. every Reaper directory is created at boot from one table and checked at every use
     (shared/reaper_tmpsafe.c reaper_secure_dir);
  3. Reaper's loose files live in /tmp/reaper (0700), never bare in /tmp;
  4. a file that must sit at a stock path is created fresh with O_EXCL|O_NOFOLLOW, and a
     script is run only when it is a root-owned regular file nobody else can write.

WHAT IT DOES. Compiles shared/reaper_tmpsafe.c on the host (-Wall -Wextra -Werror) and runs
a harness through every helper: a missing, a too-open, a symlinked and a file-shaped
directory; an atomic write and a fresh open over a symlink; the script check on a good
file, a symlink and group/world-writable files. Ownership cases (another uid) run only
as root. Then it pins the wiring in the router source: the sysctls and the boot table, no
loose Reaper path left in /tmp, every Reaper mkdir and every script execution through the
helpers, the update/upgrade/diag scripts, and V5's links gone.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
C = os.path.join(SRC, "shared", "reaper_tmpsafe.c")
H = os.path.join(SRC, "shared", "reaper_tmpsafe.h")
if not SRC or not os.path.isfile(C) or not os.path.isfile(H):
    skip("no router source tree with shared/reaper_tmpsafe.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def rd(rel):
    with open(os.path.join(SRC, rel), "rb") as f:
        return f.read().decode("latin-1")

# ---------------------------------------------------------------- 1. the helpers, compiled
MAIN = r'''
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include "reaper_tmpsafe.h"
int main(int argc, char **argv)
{
	const char *op = argv[1], *p = argv[2];
	(void)argc;
	if (!strcmp(op, "dir")) { printf("%d\n", reaper_secure_dir(p, (mode_t)strtol(argv[3], NULL, 8))); return 0; }
	if (!strcmp(op, "atomic")) { printf("%d\n", reaper_write_atomic(p, "NEW\n", 4, 0600)); return 0; }
	if (!strcmp(op, "fresh")) { FILE *f = reaper_fopen_new(p, 0600); if (f) { fputs("NEW\n", f); fclose(f); } printf("%d\n", f ? 0 : -1); return 0; }
	if (!strcmp(op, "script")) { printf("%d\n", reaper_script_ok(p)); return 0; }
	return 2;
}
'''
td = tempfile.mkdtemp(prefix="tmpsafe.")
try:
    m = os.path.join(td, "main.c"); exe = os.path.join(td, "t")
    with open(m, "w") as f: f.write("#include <stdlib.h>\n" + MAIN)
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-I", os.path.dirname(H), "-o", exe, m, C],
                       capture_output=True, text=True)
    check("reaper_tmpsafe.c compiles warning-free on the host", p.returncode == 0, p.stderr[-400:])
    if p.returncode != 0:
        print(p.stderr)
        print("\nFAILED: the helper does not compile - nothing else can be judged")
        sys.exit(1)
    def run(*a):
        r = subprocess.run([exe] + list(a), capture_output=True, text=True)
        return r.stdout.strip()
    def mode(x): return oct(os.lstat(x).st_mode & 0o7777)
    w = os.path.join(td, "w"); os.mkdir(w)
    d = os.path.join(w, "d")
    check("secure_dir: a missing directory is created at the mode asked", run("dir", d, "0700") == "0" and mode(d) == "0o700", mode(d))
    check("secure_dir: asking again is a no-op", run("dir", d, "0700") == "0" and mode(d) == "0o700")
    d2 = os.path.join(w, "d2"); os.mkdir(d2); os.chmod(d2, 0o777)
    open(os.path.join(d2, "planted"), "w").close()
    r = run("dir", d2, "0700")
    aside = [x for x in os.listdir(w) if x.startswith("d2.bad.")]
    check("secure_dir: a world-writable directory is moved aside with what was planted in it, and recreated empty",
          r == "0" and mode(d2) == "0o700" and os.listdir(d2) == [] and len(aside) == 1 and os.path.exists(os.path.join(w, aside[0], "planted")), (r, aside))
    victim = os.path.join(w, "victimdir"); os.mkdir(victim); os.chmod(victim, 0o755)
    d3 = os.path.join(w, "d3"); os.symlink(victim, d3)
    r = run("dir", d3, "0700")
    check("secure_dir: a symlink is never followed - moved aside, a real directory made, the target untouched",
          r == "0" and not os.path.islink(d3) and os.path.isdir(d3) and mode(victim) == "0o755", (r, mode(victim)))
    d4 = os.path.join(w, "d4"); open(d4, "w").close()
    check("secure_dir: a file holding the name is moved aside", run("dir", d4, "0700") == "0" and os.path.isdir(d4))
    d5 = os.path.join(w, "d5")
    check("secure_dir: 0755 is honoured where a non-root reader needs it (rv6names)", run("dir", d5, "0755") == "0" and mode(d5) == "0o755")
    vf = os.path.join(w, "victim"); open(vf, "w").write("KEEP\n")
    t1 = os.path.join(w, "t1"); os.symlink(vf, t1)
    r = run("atomic", t1)
    check("write_atomic: replaces a symlink at the target and never writes through it",
          r == "0" and not os.path.islink(t1) and open(t1).read() == "NEW\n" and open(vf).read() == "KEEP\n" and mode(t1) == "0o600", r)
    check("write_atomic: leaves no temporary file behind", not [x for x in os.listdir(w) if x.startswith("t1.")])
    t2 = os.path.join(w, "t2"); os.symlink(vf, t2)
    r = run("fresh", t2)
    check("fopen_new: a symlink at a fixed path is removed, never followed; the file is created at the mode asked",
          r == "0" and not os.path.islink(t2) and open(t2).read() == "NEW\n" and open(vf).read() == "KEEP\n" and mode(t2) == "0o600", r)
    s1 = os.path.join(w, "s1.sh"); open(s1, "w").write("true\n"); os.chmod(s1, 0o700)
    check("script_ok: a private regular file may run", run("script", s1) == "1")
    s2 = os.path.join(w, "s2.sh"); os.symlink(s1, s2)
    check("script_ok: a symlink never runs, even to a good script", run("script", s2) == "0")
    s3 = os.path.join(w, "s3.sh"); open(s3, "w").write("true\n"); os.chmod(s3, 0o770)
    check("script_ok: a group-writable script never runs", run("script", s3) == "0")
    os.chmod(s3, 0o706)
    check("script_ok: a world-writable script never runs", run("script", s3) == "0")
    check("script_ok: a missing script is a quiet no", run("script", os.path.join(w, "absent.sh")) == "0")
    if os.geteuid() == 0:
        s4 = os.path.join(w, "s4.sh"); open(s4, "w").write("true\n"); os.chmod(s4, 0o700); os.chown(s4, 65534, 65534)
        check("script_ok (root): a script another uid owns never runs", run("script", s4) == "0")
        d6 = os.path.join(w, "d6"); os.mkdir(d6, 0o700); os.chown(d6, 65534, 65534)
        r = run("dir", d6, "0700")
        check("secure_dir (root): a directory another uid made first is moved aside and remade root's",
              r == "0" and os.lstat(d6).st_uid == 0, r)
    else:
        print("note the two other-uid cases run only as root")
finally:
    shutil.rmtree(td, ignore_errors=True)

# ---------------------------------------------------------------- 2. the boot table
h = rd("shared/reaper_tmpsafe.h")
for dname, md in [("REAPER_TMPDIR", "0700"), ('"/tmp/reaper_fw"', "0700"), ('"/tmp/reaper_pbr"', "0700"), ('"/tmp/rwarden"', "0700"),
                  ('"/tmp/gk"', "0700"), ('"/tmp/reaper_wifi"', "0700"), ('"/tmp/rtraf"', "0700"), ('"/tmp/reaper_chq"', "0700"),
                  ('"/tmp/reaper_mcp"', "0700"), ('"/tmp/reaper_bwfloor"', "0700"), ('"/tmp/err_rules"', "0700"), ('"/tmp/rv6names"', "0755")]:
    check("boot table: %s at %s" % (dname, md), re.search(r"\{\s*%s,\s*%s\s*\}" % (re.escape(dname), md), h) is not None)
check('boot table: REAPER_TMPDIR is "/tmp/reaper"', '#define REAPER_TMPDIR\t"/tmp/reaper"' in h)
init = rd("rc/init.c")
i = init.find('chmod("/tmp", 01777);')
blk = init[i:i + 1600] if i >= 0 else ""
check("init.c: all four fs.protected_* are written right after the /tmp chmod",
      all('f_write_string("/proc/sys/fs/protected_%s", "1", 0, 0);' % k in blk for k in ("symlinks", "hardlinks", "regular", "fifos")))
check("init.c: the Reaper directories are created there, before any service", "reaper_tmp_mkdirs();" in blk)
check("shared/Makefile builds reaper_tmpsafe.o into libshared", "OBJS += reaper_tmpsafe.o" in rd("shared/Makefile"))
check("shared.h exports the helpers", '#include "reaper_tmpsafe.h"' in rd("shared/shared.h"))

# ---------------------------------------------------------------- 3. no loose Reaper file left in /tmp
NAMES = (r"rwatch\.sh|rwatch\.state|rwatch_|rhist\.|reaper_wan_bounced|rexport\.|rdnshc\.|reaper_punct\.|"
         r"reaper_wlmit\.state|amaspark\.state|reaper_revzone\.sig|reaper_conn_seen|reaper_conn\.lock|"
         r"\.reaper_firewall_built|\.reaper_usb_|\.reaper_dnsmasq_logdrop|reaper_extra_filter\.warned|"
         r"reaper_nf_probe\.rules|filter_extra\.tmp|\.reaper_diag_busy|\.reaper_diag_state|reaper_cfgexp\.cfg|"
         r"reaper_full\.cfg|reaper_full_jffs\.tgz|qos_hwc?_state|\.http_id_boot|reaper_update\.|reaper_manifest_pub\.pem|\.rdiag_")
OLD = re.compile(r"/tmp/(?:" + NAMES + r")")
left = []
for top in ["rc", "httpd", "shared", "gkd", "rtrafd", "rpunctd", "rdnsmapd", "rchqd", "rmcpd", "reaper_fwsim", "rom", "www", "others"]:
    for dp, dn, fn in os.walk(os.path.join(SRC, top)):
        for x in fn:
            pth = os.path.join(dp, x)
            if not (x.endswith((".c", ".h", ".sh", ".asp", ".js")) or x.startswith("Makefile") or x == "reaper_diag"):
                continue
            try: t = open(pth, "rb").read().decode("latin-1")
            except OSError: continue
            for mm in OLD.finditer(t):
                left.append(os.path.relpath(pth, SRC) + ": " + t[mm.start():mm.start() + 40].split("\n")[0])
check("no Reaper working file is named bare in /tmp (all moved to /tmp/reaper)", not left, left[:6])

# ---------------------------------------------------------------- 4. every Reaper mkdir and exec through the helpers
MK = re.compile(r'\bmkdir\((RFW_DIR|PPBR_DIR|RW_DIR|GK_DIR|RWIFI_DIR|RCHQ_DIR|RMCP_STATE_DIR|BF_DIR|V6N_DIR|V6NAMES_DIR|'
                r'REAPER_HOOK_DIR|REAPER_ERR_RULES|ERR_RULES_PATH|"/tmp/(?:reaper|rtraf)")\s*,')
EXEC = re.compile(r'\b(system|doSystem|popen|run_locked)\("sh (/tmp/|" ?[A-Z_]+)')
SET = ["rc/reaper_fw.c", "rc/reaper_pbr.c", "rc/rwarden.c", "rc/gatekeeper.c", "rc/reaper_hook.c", "rc/rdnshc.c",
       "rc/firewall.c", "rc/services.c", "rc/rwatch.c", "rc/rexport.c", "rc/reaper_bwfloor.c", "rc/rv6names.c", "rc/sdn.c",
       "httpd/web.c", "gkd/gkd.c", "rtrafd/rtrafd.c", "rchqd/rchqd.c"]
mk_left, ex_left = [], []
for rel in SET:
    for n, l in enumerate(rd(rel).split("\n"), 1):
        if MK.search(l): mk_left.append("%s:%d" % (rel, n))
        if EXEC.search(l) and "reaper_script_ok" not in l and "RW_FOLD" not in l:
            ex_left.append("%s:%d %s" % (rel, n, l.strip()[:80]))
check("every Reaper /tmp directory is made through reaper_secure_dir", not mk_left, mk_left)
check("every Reaper script run checks reaper_script_ok first (the Warden fold keeps its own lstat check)", not ex_left, ex_left)
rw = rd("rc/rwarden.c")
check("the Warden fold's own owner/mode check is still there", re.search(r"lstat\(RW_FOLD, &fst\) == 0 && S_ISREG\(fst\.st_mode\)", rw) is not None)
rwt = rd("rc/rwatch.c")
i = rwt.find("int reaper_lockrun_main(")
check("reaper_lockrun runs a listed script only when reaper_script_ok agrees", i >= 0 and "reaper_script_ok(argv[1])" in rwt[i:i + 2500])
check("rwatch 3f takes only REAPER_FW* chain names from chainsig",
      'case \\"$_c\\" in REAPER_FW*) ;; *) continue;; esac' in rwt and 'case \\"$_c\\" in *[!A-Z0-9_]*) continue;; esac' in rwt)
check("rwatch and rexport write their scripts fresh in the private directory",
      "reaper_fopen_new(RWATCH_SH, 0700)" in rwt and "reaper_fopen_new(REXPORT_SH, 0700)" in rd("rc/rexport.c"))
web = rd("httpd/web.c")
check("the restore's staged settings (a stock path) are created fresh, never through a link",
      'reaper_fopen_new("/tmp/settings_u.prf", 0600)' in web and 'fopen("/tmp/settings_u.prf", "w")' not in web)
check("httpd opens the name map without following a link", "open(RDM_PATH, O_RDWR | O_NOFOLLOW)" in web)
check("httpd's Gatekeeper and Connections lock files are opened O_NOFOLLOW",
      web.count('open("/tmp/gk/rl.lock", O_CREAT | O_RDWR | O_NOFOLLOW, 0600)') == 2 and
      'open("/tmp/reaper/reaper_conn.lock", O_CREAT | O_RDWR | O_NOFOLLOW, 0600)' in web)
rdm = rd("rdnsmapd/rdnsmapd.c")
check("rdnsmapd maps only into a private /tmp/reaper and never through a link",
      "open(RDM_PATH, O_RDWR | O_CREAT | O_NOFOLLOW, 0600)" in rdm and 'lstat("/tmp/reaper", &st)' in rdm)
check("the walker never widens /tmp/reaper (F14)", "mkdir(FWSIM_DIR, 0700);" in rd("reaper_fwsim/reaper_fwsim.c"))
check("reaper_hook takes lstat, not stat, for 'already there'", "lstat(REAPER_HOOK_SH, &st) == 0" in rd("rc/reaper_hook.c"))
fw = rd("rc/firewall.c")
check("err_rules is 0700 at both sites (was 0777; F2)", "0777" not in "".join(l for l in fw.split("\n") if "ERR_RULES" in l and "mkdir" in l)
      and fw.count("reaper_secure_dir(REAPER_ERR_RULES, 0700)") == 1 and fw.count("reaper_secure_dir(ERR_RULES_PATH, 0700)") == 1)

# ---------------------------------------------------------------- 5. the scripts
upd = rd("rom/webs_scripts/reaper_webs_update.sh")
check("update check: the manifest, signature and key live in /tmp/reaper",
      "TMP=/tmp/reaper/reaper_update.txt" in upd and "PUBKEY=/tmp/reaper/reaper_manifest_pub.pem" in upd and "SIGBIN=/tmp/reaper/reaper_update.sig.bin" in upd)
check("update check: refuses to run unless /tmp/reaper is root's 0700 directory",
      'rt_ls=$(ls -lnd /tmp/reaper 2>/dev/null)' in upd and '"${rt_ls%% *}" != "drwx------"' in upd)
i = upd.find("rt_ls=$(ls -lnd /tmp/reaper")
check("update check: the directory check runs AFTER the state reset and completes the check the page waits on",
      upd.find('nvram set webs_state_channel=""') < i and "nvram set webs_state_update=1" in upd[i:i + 500])
upg = rd("rom/webs_scripts/reaper_webs_upgrade.sh")
i, j = upg.find('fw_ls=$(ls -ln "$FW"'), upg.find('firmware_check "$FW"')
check("upgrade: the image must be a root-owned regular file nobody else can write, checked before the flash",
      0 <= i < j and "not owned by root - not flashing" in upg[i:j])
# review 2026-10-09: rc runs with umask 0 (rc/init.c), so wget's image would be 0666 and the
# check above would refuse EVERY upgrade - the umask must be set before the download
k, wg = upg.find("umask 022\n"), upg.find('/usr/sbin/wget')
check("upgrade: umask 022 is set before the download (rc's umask is 0)", 0 <= k < wg, (k, wg))
check("rc really does run with umask 0 (the reason the line above exists)", "umask(0);" in rd("rc/init.c"))
check("PBR's variable-path runner checks the script too",
      "rc = reaper_script_ok(path) ? system(cmd) : -1;" in rd("rc/reaper_pbr.c"))
check("IPv6 names: hosts files written atomically (temp 0600, never 0666 under rc's umask 0)",
      "reaper_write_atomic(path, content, strlen(content), 0644)" in rd("rc/rv6names.c"))
check("IPv6 names: the per-bridge directory goes through reaper_secure_dir in sdn.c too",
      "reaper_secure_dir(dir, 0755);" in rd("rc/sdn.c"))
dg = rd("others/reaper_diag")
check("diag: scratch files in the private directory; the report created fresh under noclobber",
      'SCR=/tmp/reaper' in dg and 'RAW="$SCR/.rdiag_raw.$$"' in dg and 'rm -f "$OUT"\nset -C\n{' in dg and 'set +C' in dg)
check("diag v1.3.33 reports the four protections and the directories",
      'VER="REAPER-DIAG v1.3.33"' in dg and "protected_$k" in dg and "/tmp/rv6names:drwxr-xr-x" in dg and "*.bad.*" in dg)
check("diag page and marker follow the version",
      "REAPER-DIAG v1.3.33</span>" in rd("www/Reaper_Diag.asp"))
shell = shutil.which("bash")
if shell:
    for rel in ["rom/webs_scripts/reaper_webs_update.sh", "rom/webs_scripts/reaper_webs_upgrade.sh", "others/reaper_diag"]:
        r = subprocess.run([shell, "-n", os.path.join(SRC, rel)], capture_output=True, text=True)
        check("%s parses (bash -n)" % rel, r.returncode == 0, r.stderr[-200:])
    # the upgrade's private-file test, run against real files (mode half; the uid half needs root)
    snip = upg[i:upg.find("[ \"$(echo \"$fw_ls\"", i)]
    probe = tempfile.mkdtemp(prefix="upgck.")
    try:
        for md, want in [(0o644, "pass"), (0o664, "fail"), (0o646, "fail")]:
            fp = os.path.join(probe, "img"); open(fp, "w").write("x"); os.chmod(fp, md)
            sc = 'fail(){ echo fail; exit 0; }\nFW=%s\n%s\necho pass\n' % (fp, snip)
            out = subprocess.run([shell, "-c", sc], capture_output=True, text=True).stdout.strip()
            check("upgrade check: mode %o -> %s" % (md, want), out == want, out)
        os.remove(fp); os.symlink("/etc/hostname", fp)
        out = subprocess.run([shell, "-c", 'fail(){ echo fail; exit 0; }\nFW=%s\n%s\necho pass\n' % (fp, snip)], capture_output=True, text=True).stdout.strip()
        check("upgrade check: a symlink in place of the image -> fail", out == "fail", out)
        os.remove(fp)
        # end to end under rc's real umask: the script's own umask line, a download
        # stand-in (a plain redirect, as wget -O creates it), then the check
        sc = 'umask 0\nfail(){ echo fail; exit 0; }\nFW=%s\numask 022\nrm -f "$FW"\necho image > "$FW"\n%s\necho pass\n' % (fp, snip)
        out = subprocess.run([shell, "-c", sc], capture_output=True, text=True).stdout.strip()
        check("upgrade check: under rc's umask 0 the downloaded image passes once the script sets umask 022", out == "pass", out)
        sc = 'umask 0\nfail(){ echo fail; exit 0; }\nFW=%s\nrm -f "$FW"\necho image > "$FW"\n%s\necho pass\n' % (fp, snip)
        out = subprocess.run([shell, "-c", sc], capture_output=True, text=True).stdout.strip()
        check("upgrade check: (negative) without the umask line the same image is refused - the bug the review caught", out == "fail", out)
    finally:
        shutil.rmtree(probe, ignore_errors=True)

# ---------------------------------------------------------------- 5b. same-pass hygiene (2026-10-09)
usb = rd("rc/usb.c")
check("usb.c: /proc/partitions names are read with bounded widths (ptname[32], dev[64])",
      "%31[^" in usb and "%63[^" in usb and usb.count(" %d %d %d %[^") == 0 and usb.count(" %*d %*d %*d %[^") == 0)
check("usb.c: create_custom_passwd closes its file on the early return and checks the group file open",
      "fclose(fp);\t/* reaper 2026-10-09: was leaked" in usb and "unchecked before (fprintf into NULL)" in usb)
check("diag: dynamic puncturing prints the gain/interval rpunctd applies (0 = the preset's value)",
      "dynamic settings: preset=$PPN" in dg and 'PDG=15; PDH=180' in dg and 'PDG=20; PDH=300' in dg and 'PDG=10; PDH=60' in dg)

# ---------------------------------------------------------------- 5c. V11 (2026-10-09, owner): the app network installer is not shipped
rom = rd("rom/Makefile")
DROP = ["app_install.sh", "app_update.sh", "app_upgrade.sh", "app_base_packages.sh", "app_base_library.sh",
        "app_move_to_pool.sh", "app_switch.sh", "app_check_pool.sh", "app_cancel.sh"]
KEEP = ["app_base_link.sh", "app_check_folder.sh", "app_fsck.sh", "app_fsck_all.sh", "app_get_field.sh",
        "app_init_run.sh", "app_remove.sh", "app_set_enabled.sh", "app_stop.sh"]
check("V11: rom/Makefile no longer installs app_*.sh by wildcard", "apps_scripts/app_*.sh $(INSTALLDIR)" not in rom)
check("V11: every USB-chain script (disk check, mount/unmount, remove) is still installed",
      all("apps_scripts/" + k in rom for k in KEEP), [k for k in KEEP if "apps_scripts/" + k not in rom])
check("V11: none of the nine installer scripts is installed, and a warm tree's copies are removed",
      all("apps_scripts/" + d not in rom for d in DROP) and all("$(INSTALLDIR)/usr/sbin/" + d in rom for d in DROP))
svc = rd("rc/services.c")
check("V11: rc refuses an install/update/upgrade/switch/cancel with one log line instead of running a missing script",
      "the app network installer is not part of this firmware" in svc and "if (nvtmp[0] && !f_exists(nvtmp))" in svc)
check("V11: the per-disk app starter only refreshes lists where the refresher exists",
      "[ -x /usr/sbin/app_update.sh ]" in rd("rom/apps_scripts/asusrouter"))
wmk = rd("www/Makefile")
check("V11: ASUS's developer test form for the installer is not shipped", "rm -f $(INSTALLDIR)/www/apps_test.asp" in wmk)
# the USB Application hub is NOT the installer: the dashboard rail and eight USB pages link to it
check("V11: the USB Application hub page stays - no Reaper rule removes it",
      "rm -f $(INSTALLDIR)/www/APP_Installation.asp" not in wmk and 'href="/reaper_shell.asp#APP_Installation.asp"' in rd("www/Main_ReaperDash.asp"))

# ---------------------------------------------------------------- 6. V5
mk = rd("www/Makefile")
check("V5: no /www/fb_data.tgz.gz* link into /tmp is installed any more", "ln -sf /tmp/fb_data" not in mk and "rm -f $(INSTALLDIR)/www/fb_data.tgz.gz*" in mk)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: Reaper's /tmp directories are root's from boot, its working files are private, fixed-path files are created fresh, and nothing runs a script someone else could have written")
