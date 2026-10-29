#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reaper's side of the AiMesh firmware-upgrade conventions (2026-10-15).

WHY THIS EXISTS. AiMesh drives four open Reaper surfaces, and each one had drifted
from the stock conventions in the GPL tree:

  1. webs_upgrade.sh. A mesh upgrade runs "start_webs_upgrade 1" on every unit.
     Stock ssl_webs_upgrade.sh (same directory) reads $1 as cfg_trigger:
     download + verify only, cfg_fwstatus=6, never reboot - AiMesh flashes all
     units itself afterwards. Reaper's script ignored $1 and flashed at once.
  2. webs_state_info. The stock layout is Merlin's firmbase_firmver_buildno_
     extendno, which the watchdog new-version notice reads with
     "%4[^_]_%3[^_]_%2[^_]_%15s" (rc/watchdog.c). "3006.102.8_Reaper_vX" put
     "Reaper" in the build-number slot, and nodes showed the main router's
     firmware as "3.0.0.6.Reaper_v...".
  3. Advanced_FirmwareUpgrade_Content.asp had the mesh path forced off, so a
     Reaper main router could not check or upgrade its nodes.
  4. The AiMesh controller is started by rc only once x_Setting=1 or
     cfg_master=1 (start_cfgsync, RTCONFIG_MASTER_DET); Reaper keeps x_Setting=0
     until setup, so AiMesh.asp says so (RAMS_10) and points at the setup box,
     the same cure as the Network page's main-network notice.
  plus the aimesh: onboarding log lines, which ran on every poll of the list.

WHAT IT DOES.
  A. Runs the real reaper_webs_upgrade.sh under sh against stub nvram / wget /
     firmware_check / rc, once with $1=1 and once without, and asserts the
     cfg_trigger run verified the image and stopped (cfg_fwstatus=6, fwpath=2,
     webs_state_upgrade=1, webs_state_error=0, no restart_upgrade, no eject)
     while the plain run still releases USB before ejusb and flashes.
  B. Expands the webs_state_info literal from reaper_webs_update.sh and feeds it
     through every reader of it (the node-side version display, the watchdog
     sscanf - pinned to the real source -, webs_note.sh's sed, the pages' regex).
  C. Static checks on the firmware page, AiMesh.asp, the 25 packs and web.c.

Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC).
"""
import hashlib, os, re, shutil, stat, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "rc")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        die("missing %s" % rel)
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

upg = read("rom/webs_scripts/reaper_webs_upgrade.sh")
upd = read("rom/webs_scripts/reaper_webs_update.sh")
note = read("rom/webs_scripts/reaper_webs_note.sh")
watchdog = read("rc/watchdog.c")
fwpage = read("www/Advanced_FirmwareUpgrade_Content.asp")
aimesh = read("www/AiMesh.asp")
web = read("httpd/web.c")

# ------------------------------------------------------------------ A. run it
SH = shutil.which("dash") or shutil.which("sh")
if not SH or not sys.platform.startswith("linux"):
    skip("no POSIX sh on a Linux host")

PAYLOAD = b"REAPER-TEST-IMAGE" * 4096
SHA = hashlib.sha256(PAYLOAD).hexdigest()
URL = ("https://github.com/TheUnboundDeveloper/AM-Reaper/releases/download/v9.9.9/"
       "RT-BE96U_3006_102.8_Reaper_v9.9.9_noMCP_nand_squashfs.pkgtb")

STUBS = {
    # file-backed nvram: get / set k=v / unset / commit
    "nvram": r'''#!/bin/sh
DB="$T/nv"; touch "$DB"
case "$1" in
get) grep "^$2=" "$DB" | tail -1 | cut -d= -f2- ;;
set) k="${2%%=*}"; grep -v "^$k=" "$DB" > "$DB.n"; echo "$2" >> "$DB.n"; mv "$DB.n" "$DB"; echo "set $2" >> "$T/nvset.log" ;;
unset) grep -v "^$2=" "$DB" > "$DB.n"; mv "$DB.n" "$DB" ;;
commit) echo commit >> "$T/calls.log" ;;
esac
''',
    "wget": r'''#!/bin/sh
out=""
while [ $# -gt 0 ]; do [ "$1" = "-O" ] && { out="$2"; shift; }; shift; done
cp "$T/payload" "$out"
''',
    "firmware_check": '#!/bin/sh\n[ -s "$1" ] && nvram set firmware_check=1\n',
    "rc": '#!/bin/sh\necho "rc $*" >> "$T/calls.log"\n',
    "logger": '#!/bin/sh\nexit 0\n',
    "reaper_usb_release": '#!/bin/sh\necho "reaper_usb_release" >> "$T/calls.log"\n',
    "ejusb": '#!/bin/sh\necho "ejusb $*" >> "$T/calls.log"\n',
    "sleep": '#!/bin/sh\nexit 0\n',
}

def run_upgrade(arg):
    T = tempfile.mkdtemp(prefix="aimesh_upg_")
    try:
        b = os.path.join(T, "bin"); os.mkdir(b)
        for n, body in STUBS.items():
            p = os.path.join(b, n)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, 0o755)
        with open(os.path.join(T, "payload"), "wb") as f:
            f.write(PAYLOAD)
        with open(os.path.join(T, "nv"), "w") as f:
            f.write("productid=RT-BE96U\nwebs_state_flag=1\nwebs_state_url=%s\n"
                    "webs_state_sha256=%s\nwebs_state_size=%d\n" % (URL, SHA, len(PAYLOAD)))
        s = upg
        # absolute paths -> the stubs / the temp dir; root-owner test -> this uid
        for a, z in (("/usr/sbin/wget", "wget"), ("/sbin/reaper_usb_release", "reaper_usb_release"),
                     ("/sbin/ejusb", "ejusb"), ("LOG=/tmp/webs_upgrade.log", "LOG=$T/upg.log"),
                     ("FW=/tmp/linux.trx", "FW=$T/linux.trx"), ("WGET_LOG=/tmp/fwget_log", "WGET_LOG=$T/fwget"),
                     ("df -k /tmp", "df -k $T")):
            if a not in s:
                die("reaper_webs_upgrade.sh: expected text not found for the harness: %s" % a)
            s = s.replace(a, z)
        owner = "[ \"$(echo \"$fw_ls\" | awk '{print $3}')\" = \"0\" ]"
        if owner not in s:
            die("reaper_webs_upgrade.sh: root-owner check changed shape (harness needs updating)")
        s = s.replace(owner, "[ \"$(echo \"$fw_ls\" | awk '{print $3}')\" = \"$(id -u)\" ]")
        sp = os.path.join(T, "upg.sh")
        with open(sp, "w") as f:
            f.write(s)
        env = dict(os.environ, T=T, PATH=b + ":" + os.environ.get("PATH", "/usr/bin:/bin"))
        r = subprocess.run([SH, sp] + ([arg] if arg else []), env=env, capture_output=True, text=True, timeout=60)
        nv = dict(l.split("=", 1) for l in open(os.path.join(T, "nv")).read().splitlines() if "=" in l)
        calls = open(os.path.join(T, "calls.log")).read().splitlines() if os.path.exists(os.path.join(T, "calls.log")) else []
        sets = open(os.path.join(T, "nvset.log")).read() if os.path.exists(os.path.join(T, "nvset.log")) else ""
        log = open(os.path.join(T, "upg.log")).read() if os.path.exists(os.path.join(T, "upg.log")) else ""
        return r, nv, calls, sets, log
    finally:
        shutil.rmtree(T, ignore_errors=True)

r, nv, calls, sets, log = run_upgrade("1")
if r.returncode != 0:
    die("cfg_trigger run exited %d: %s %s" % (r.returncode, r.stdout, r.stderr))
if "ABORT" in log:
    die("cfg_trigger run aborted: " + log)
if any("restart_upgrade" in c for c in calls):
    die("cfg_trigger run flashed (restart_upgrade) - AiMesh sequences the flash itself")
if any(c.startswith("ejusb") or c == "reaper_usb_release" for c in calls):
    die("cfg_trigger run ejected USB - rc's upgrade service does that when AiMesh flashes")
for k, v in (("cfg_fwstatus", "6"), ("fwpath", "2"), ("webs_state_upgrade", "1"),
             ("webs_state_error", "0"), ("auto_upgrade", "1"), ("firmware_check", "1")):
    if nv.get(k) != v:
        die("cfg_trigger run: nvram %s=%r, want %r" % (k, nv.get(k), v))
if "set webs_state_upgrade=2" in sets:
    die("cfg_trigger run set webs_state_upgrade=2 (the 'flashing' state)")
if sets.find("set cfg_fwstatus=6") > sets.find("set firmware_check=1"):
    die("cfg_fwstatus=6 must be set before the download, as stock does")
for want in ("rc rc_service stop_logger", "rc rc_service stop_jffs2 0"):
    if want not in calls:
        die("cfg_trigger run: missing %r (stock's end state for the flash step)" % want)
ok("start_webs_upgrade 1 (AiMesh): downloads, verifies, cfg_fwstatus=6 -> fwpath=2, upgrade=1/error=0, no flash, no eject")

r, nv, calls, sets, log = run_upgrade(None)
if r.returncode != 0 or "ABORT" in log:
    die("plain run failed: rc=%d log=%s" % (r.returncode, log))
try:
    i_rel = calls.index("reaper_usb_release")
    i_ej = next(i for i, c in enumerate(calls) if c.startswith("ejusb"))
    i_up = next(i for i, c in enumerate(calls) if "restart_upgrade" in c)
except (ValueError, StopIteration):
    die("plain run: expected reaper_usb_release, ejusb and restart_upgrade, got %r" % calls)
if not (i_rel < i_ej < i_up):
    die("plain run: order must be release -> ejusb -> restart_upgrade, got %r" % calls)
if "cfg_fwstatus" in nv:
    die("plain run touched cfg_fwstatus")
if nv.get("webs_state_upgrade") != "2":
    die("plain run: webs_state_upgrade=%r, want 2 (verified, flashing)" % nv.get("webs_state_upgrade"))
ok("start_webs_upgrade (Reaper_Firmware.asp): unchanged - release, eject, flash")

# ------------------------------------------------------------------ B. version string
m = re.search(r'nvram set webs_state_info="([^"]+)"', upd)
if not m:
    die("reaper_webs_update.sh: no webs_state_info literal")
info = m.group(1).replace("${rem_ver}", "3.4.4")
if "${" in info:
    die("webs_state_info literal has an unexpanded variable: %s" % info)

# node-side version display: the string split on "_" into firmver, build number and the
# rest, the 4-digit firmver shown digit by digit (the old string came out "3.0.0.6.Reaper_v...")
cm = re.match(r"([^_]+)_([^_]+)_(\S+)", info)
if not cm:
    die("webs_state_info does not split into firmver_buildno_rest: %r" % info)
firm, build, ext = cm.groups()
if not re.fullmatch(r"\d{4}", firm):
    die("node display: first field %r is not the 4-digit firmver" % firm)
if not re.fullmatch(r"[0-9.]+", build):
    die("node display: build-number slot is %r (was 'Reaper' before the fix)" % build)
shown = "%s.%s.%s.%s.%s_%s" % (firm[0], firm[1], firm[2], firm[3], build, ext)
if not re.search(r"Reaper_v\d", shown):
    die("node display would read %r" % shown)
ok("node display reads %s" % shown)

# watchdog new-version notice: the format is pinned to the real source
fmt = '"%4[^_]_%3[^_]_%2[^_]_%15s"'
if fmt not in watchdog:
    die("rc/watchdog.c: the webs_state_info sscanf format changed - re-check this contract")
wm = re.match(r"([^_]{1,4})_([^_]{1,3})_([^_]{1,2})_(\S{1,15})", info)
if not wm or wm.group(1) != "3006" or wm.group(4) != "Reaper_v3.4.4":
    die("watchdog parse of %r: %r" % (info, wm.groups() if wm else None))
ok("watchdog notice reads %s.%s.%s_%s" % wm.groups())

# webs_note.sh sed and the pages' regex
sed_ver = re.sub(r"[^0-9.].*", "", re.sub(r".*Reaper_v", "", info))
if sed_ver != "3.4.4" or "s/.*Reaper_v//; s/[^0-9.].*//" not in note:
    die("webs_note.sh version extraction gives %r" % sed_ver)
js = re.search(r"Reaper_v([0-9.]+)", info)
if not js or js.group(1) != "3.4.4":
    die("page regex Reaper_v([0-9.]+) fails on %r" % info)
ok("webs_note.sh and the Reaper pages still extract 3.4.4")

# ------------------------------------------------------------------ C. static
if re.search(r"if\(\s*0\s*&&\s*cfg_sync_support\s*\)", fwpage):
    die("Advanced_FirmwareUpgrade_Content.asp: the AiMesh path is still forced off")
if fwpage.count("cfg_sync_support && reaper_mesh_nodes") != 2 or "var reaper_mesh_nodes" not in fwpage:
    die("Advanced_FirmwareUpgrade_Content.asp: check + result poll must both use reaper_mesh_nodes")
ok("firmware page: AiMesh check/upgrade path back on whenever a node is paired")

for needle in ('id="rams_setup_notice"', "<#RAMS_10#>", "reaperAiMeshNotice();",
               'nvram_get("x_Setting")', 'nvram_get("cfg_master")', 'href="Reaper_WiFiSetup.asp"'):
    if needle not in aimesh:
        die("AiMesh.asp: missing %s" % needle)
ok("AiMesh.asp: setup notice wired (x_Setting / cfg_master, setup box link)")

packs = ["BR", "CN", "CZ", "DA", "DE", "EN", "ES", "FI", "FR", "HU", "IT", "JP", "KR", "MS",
         "NL", "NO", "PL", "RO", "RU", "SL", "SV", "TH", "TR", "TW", "UK"]
counts = set()
for p in packs:
    d = read("www/%s.dict" % p)
    counts.add(d.count("\n"))
    v = re.search(r"^RAMS_10=(.+)$", d, re.M)
    if not v or not v.group(1).strip():
        die("%s.dict: RAMS_10 missing or empty" % p)
    if '"' in v.group(1) or "'" in v.group(1):
        die("%s.dict: RAMS_10 carries a quote" % p)
if len(counts) != 1:
    die("language packs out of lockstep: %r" % sorted(counts))
ok("RAMS_10 in all 25 packs, lockstep %d" % counts.pop())

calls_aimesh = [m.start() for m in re.finditer(r'logmessage\("aimesh"', web)]
if len(calls_aimesh) < 4:
    die("httpd/web.c: expected the four aimesh: onboarding log lines")
for pos in calls_aimesh:
    ctx = web[max(0, pos - 220):pos]
    if "aimesh_log_due(" not in ctx:
        die("httpd/web.c: an aimesh: log line is not throttled: ...%s" % web[pos:pos + 80])
if "static int aimesh_log_due(" not in web:
    die("httpd/web.c: aimesh_log_due() missing")
ok("web.c: every aimesh: onboarding line goes through aimesh_log_due()")

print("PASS")
