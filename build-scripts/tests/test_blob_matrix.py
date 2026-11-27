#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Closed-object closure for the models built with an older GPL drop (2026-11-04).

WHY THIS EXISTS. GT-BE98, GT-BE19000, BQ16 and BQ16 Pro build from the same tree as the RT-BE96U, but
keep the model-specific closed objects of their own ASUS GPL drop (102_39274 / 102_39256), while the
closed objects shared by every 3006.102.10 model take the newer bytes. Mixing two drops is only safe
if every symbol one closed object needs from another is still provided inside the model's own set.
"Shared by the 102.10 models" is necessary but not sufficient: the BQ16's own libamas-utils.so
exports functions its cfg_server needs and the newer library does not, so the BQ16s keep theirs.
A wrong swap list links fine in the open code and fails only at run time on a box nobody can watch;
this suite fails it at the desk instead.

WHAT IT CHECKS, for each model it finds in the tree (or the one named by REAPER_MODEL):
  1. closure: every undefined symbol of the model's closed per-package objects
     (release/src/router/*/prebuil[dt]/<MODEL>/) that some closed object of the reference model
     (RT-BE96U) defines must be defined by the model's own closed set, or be one of the functions the
     compatibility layer provides (rc/reaper_legacy_blobs_shim.c, httpd/reaper_legacy_blobs_httpd.c).
     Symbols of objects the model never links (MULTISERVICE_WAN's mswan-broadcom.o) are ignored.
  2. the model's networkmap binary opens the OUI database this tree installs (ieee.oui.json).
  3. when the tree has a staged rootfs (a build ran: targets/96813GW/fs), its dynamic-link closure:
     every undefined dynamic symbol of every ELF there is exported by some ELF in the same rootfs.
     Check 1 only sees symbols the reference model's closed objects provide; a library this model keeps
     because it exports MORE (the BQ16s' libamas-utils.so) is only protected by this check. Proven
     2026-11-04: a BQ16 rootfs given the newer libamas-utils.so leaves six symbols of rc, cfg_server,
     cfg_client and amas-utils-cli unresolved. Six inert symbols are allowed (BASELINE below).
Needs a router source tree of a model branch (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)
and an ARM-capable nm (REAPER_NM, else the toolchain's aarch64-linux-nm). Exit 0 pass, 1 fail, 77 skip."""
import glob, os, re, shutil, subprocess, sys


def skip(msg):
    print("SKIP: " + msg); sys.exit(77)


SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "rc")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC)")
NM = os.environ.get("REAPER_NM") or next(iter(sorted(glob.glob(
    "/opt/toolchains/crosstools-aarch64-gcc-10.3*/usr/bin/aarch64-linux-nm"))), "") or shutil.which("nm") or ""
if not NM:
    skip("no nm")

REF = "RT-BE96U"
LEGACY = ["GT-BE98", "GT-BE19000", "BQ16", "BQ16_PRO"]
# 2026-11-16: the GT-BE98 carries its ASUS GPL 102_40585 closed objects and builds WITHOUT the compatibility
# layer, so its closure must hold with nothing supplied by the shim.
NO_SHIM = {"GT-BE98"}
SHIM = {  # provided by the compatibility layer (weak definitions)
    "wl_scb", "backup_eth_ob_log", "is_wan_port_ext_switch", "get_wifi_gen", "apg_is_wds_raw_if",
    "check_apply_nvram_lan_only", "ej_hw_accel_status", "find_dms_dbdir_candidate",
}
NOT_LINKED = {"mswan-broadcom.o"}  # MULTISERVICE_WAN only; none of the four sets it
BASELINE = {  # unresolved on every image of either line (2026-11-04), never reached at run time:
    "check_AQoS_only_enabled", "check_wan_2P5G_10G_speed",          # libbwdpi.so; BWDPI is off
    "find_domain_from_name", "find_our_domain",                      # Samba idmap/nss_info plugins,
    "get_global_winbindd_state_offline", "wcache_tdc_fetch_list",    # resolved only inside winbindd
}


def closed_files(model):
    out = []
    for d in glob.glob(os.path.join(SRC, "*", "prebuil[dt]", model)) + \
             glob.glob(os.path.join(SRC, "*", "*", "prebuil[dt]", model)):
        for root, _, files in os.walk(d):
            for f in files:
                p = os.path.join(root, f)
                if f in NOT_LINKED or os.path.islink(p):
                    continue
                with open(p, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        out.append(p)
    return sorted(out)


def syms(files, undefined):
    res = {}
    for p in files:
        for dyn in ([], ["-D"]):
            args = [NM] + dyn + (["-u"] if undefined else ["--defined-only"]) + [p]
            r = subprocess.run(args, capture_output=True, text=True)
            for line in r.stdout.splitlines():
                parts = line.split()
                if not parts:
                    continue
                name = parts[-1].split("@")[0]
                if undefined and parts[0] not in ("U", "w"):
                    continue
                if not undefined and len(parts) < 3:
                    continue
                res.setdefault(name, set()).add(os.path.relpath(p, SRC))
    return res


ref_files = closed_files(REF)
if not ref_files:
    skip("no %s closed objects under %s" % (REF, SRC))
ref_def = syms(ref_files, False)

wanted = os.environ.get("REAPER_MODEL")
models = [wanted] if wanted else [m for m in LEGACY if closed_files(m)]
if not models:
    skip("no closed objects of %s in this tree" % "/".join(LEGACY))

fails = 0
for m in models:
    files = closed_files(m)
    if not files:
        print("FAIL %s: no closed objects found" % m); fails += 1; continue
    mdef = syms(files, False)
    mund = syms(files, True)
    shim = set() if m in NO_SHIM else SHIM
    missing = sorted(s for s in mund if s in ref_def and s not in mdef and s not in shim)
    print("%-10s %3d closed objects, %5d imports; closure %s" %
          (m, len(files), len(mund), "ok" if not missing else "BROKEN (%d)" % len(missing)))
    for s in missing[:40]:
        print("      %-44s needed by %s; only %s provides it" %
              (s, ", ".join(sorted(mund[s])[:2]), ", ".join(sorted(ref_def[s])[:1])))
    if missing:
        fails += 1
    nmap = os.path.join(SRC, "networkmap", "prebuild", m, "networkmap")
    if os.path.isfile(nmap):
        with open(nmap, "rb") as fh:
            blob = fh.read()
        if b"ieee.oui.json" in blob:
            print("           networkmap opens ieee.oui.json: ok")
        else:
            print("FAIL       networkmap does not open ieee.oui.json (this tree installs no networkmap.oui.js)")
            fails += 1

FS = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "targets", "96813GW", "fs"))
if os.path.isdir(FS):
    exports, imports, n = set(), {}, 0
    for root, _, files in os.walk(FS):
        for f in files:
            p = os.path.join(root, f)
            if os.path.islink(p) or not os.path.isfile(p) or f.endswith((".ko", ".o")):
                continue
            try:
                with open(p, "rb") as fh:
                    if fh.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            n += 1
            for line in subprocess.run([NM, "-D", p], capture_output=True, text=True).stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[-2] not in ("U", "w", "v"):
                    exports.add(parts[-1].split("@")[0])
                elif len(parts) == 2 and parts[0] == "U":
                    imports.setdefault(parts[1].split("@")[0], set()).add(os.path.relpath(p, FS))
    bad = sorted(s for s in imports if s not in exports and s not in BASELINE)
    print("rootfs     %d ELF files, %d imported symbols; dynamic closure %s" %
          (n, len(imports), "ok" if not bad else "BROKEN (%d)" % len(bad)))
    for s in bad[:40]:
        print("      %-44s imported by %s" % (s, ", ".join(sorted(imports[s])[:3])))
    if bad:
        fails += 1
else:
    print("rootfs     no staged rootfs at %s - dynamic closure not checked" % FS)

if fails:
    print("\n%d check(s) failed" % fails); sys.exit(1)
print("all checks passed")
