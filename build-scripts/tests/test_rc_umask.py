#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rc runs with umask 022 after its boot-time directories (field report, GT-BE98, 2026-10-09).

WHY THIS EXISTS. Stock rc calls umask(0) in sysinit and never restores it (ASUS left its own
umask(022) commented out). Every process rc starts inherits it, so any file created without an
explicit mode - fopen("w"), a shell ">" - came out 0666, writable by the non-root services
(dnsmasq and tftpd as nobody, Entware daemons) between root writing it and root reading it.

WHAT IT PINS.
- rc/init.c turns umask(022) on, once, AFTER the directory block whose 0777 directories ASUS
  made on purpose (/var/lock, /var/state, /var/tmp/dhcp) and after /tmp's 01777, so those keep
  their stock modes; the commented-out line is gone.
- Each service that must create files as another user sets its own mode, so it does not depend
  on rc's umask: vsftpd local_umask=000, Samba force create/directory mode 0777, tftpd started
  without -p (tftp-hpa then uses its own umask 0), mkdir_if_none() creates with "mkdir -m 0777"
  (busybox chmods the final directory, so the umask does not apply).
- dnsmasq opens its lease file before it drops to nobody (it never creates one as nobody).

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass the tree's release/src/router as
argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
INIT = os.path.join(SRC, "rc", "init.c")
if not SRC or not os.path.isfile(INIT):
    skip("no router source tree with rc/init.c (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def read(rel):
    p = os.path.join(SRC, rel)
    return open(p, encoding="latin-1").read() if os.path.isfile(p) else None

init = read("rc/init.c")
code = re.sub(r"/\*.*?\*/", "", init, flags=re.S)          # comments out
code = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith("//"))

on = [m.start() for m in re.finditer(r"^\s*umask\(022\);", code, re.M)]
check("rc/init.c sets umask(022) exactly once", len(on) == 1, on)
check("the commented-out stock line is gone", "//umask(022);" not in init)
if len(on) == 1:
    at = on[0]
    for d in ('mkdir("/var/lock", 0777)', 'mkdir("/var/state", 0777)', 'mkdir("/var/tmp/dhcp", 0777)',
              'chmod("/tmp", 01777)'):
        i = code.find(d)
        check("%s runs before the umask, so it keeps its stock mode" % d, 0 <= i < at, i)
    z = [m.start() for m in re.finditer(r"^\s*umask\(0\);", code, re.M)]
    check("the stock umask(0) still comes first (the boot block relies on it)", z and z[0] < at, z)
    check("nothing resets rc to umask 0 after it", not any(p > at for p in z), z)

ftp = read("rc/usb.c") or ""
check("vsftpd sets its own local_umask=000", 'fprintf(fp, "local_umask=000\\n");' in ftp)
m = re.search(r'char \*tftpd_argv\[\] = \{ "in.tftpd", "(-[A-Za-z0-9]+)"', ftp)
check("tftpd starts without -p (keeps its own umask for uploads)", m is not None and "p" not in m.group(1),
      m.group(1) if m else "argv not found")

smb = read("libdisk/write_smb_conf.c")
if smb is None:
    print("note: libdisk/write_smb_conf.c not in this tree - Samba pin skipped")
else:
    check("Samba forces create mode 0777", 'fprintf(fp, "force create mode = 0777\\n");' in smb)
    check("Samba forces directory mode 0777", 'fprintf(fp, "force directory mode = 0777\\n");' in smb)

svc = read("rc/services.c") or ""
check("mkdir_if_none() creates with an explicit mode (mkdir -m 0777)", "\"mkdir -m 0777 -p '%s'\"" in svc)

dq = read("dnsmasq/src/dnsmasq.c")
if dq is None:
    print("note: dnsmasq/src/dnsmasq.c not in this tree - lease pin skipped")
else:
    li, su = dq.find("lease_init(now);"), dq.find("setuid(ent_pw->pw_uid)")
    check("dnsmasq opens its lease file before dropping to nobody", 0 <= li < su, (li, su))

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: rc hands every service umask 022, the stock 0777 directories keep their modes, "
      "and the services that write as another user set their own")
