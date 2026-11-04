#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A refused SMB login reaches the system log (2026-11-03, owner metal report: a wrong password left no trace).

WHY THIS EXISTS. Samba 4.15 logs authentication in the auth_audit debug class: a refusal at level 2
(auth/auth_log.c AUTH_FAILURE_LEVEL), a success at 3. write_smb_conf.c wrote `log level = 0` and relied on the
default syslog threshold (level 0 only), so a failed login was never even produced. Now, for SAMBA4 only:
`log level = 0 auth_audit:2` and `logging = syslog@2 file` (`logging` replaces the deprecated `syslog`).

WHAT IT DOES. Checks write_smb_conf.c emits both lines inside an RTCONFIG_SAMBA4 branch, keeps the plain
`log level = 0` for the other Samba versions, does not raise the auth class past 2 (successes would flood the log),
and that the Samba source the build uses still logs refusals at level 2 when it is present.
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
W = os.path.join(SRC, "libdisk", "write_smb_conf.c") if SRC else ""
if not W or not os.path.isfile(W):
    print("SKIP: no router source tree"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

t = open(W, encoding="utf-8", errors="replace").read()
m = re.search(r'fprintf\(fp, "log file = %s\\n", SAMBA_LOG\);\n#if defined\(RTCONFIG_SAMBA4\)\n(.*?)#else\n(.*?)#endif\n', t, re.S)
check("the log lines sit in an RTCONFIG_SAMBA4 / #else pair after `log file`", m is not None)
if m:
    s4, other = m.group(1), m.group(2)
    check("SAMBA4: log level = 0 auth_audit:2", 'fprintf(fp, "log level = 0 auth_audit:2\\n");' in s4)
    check("SAMBA4: logging = syslog@2 file", 'fprintf(fp, "logging = syslog@2 file\\n");' in s4)
    check("other Samba versions keep log level = 0", 'fprintf(fp, "log level = 0\\n");' in other)
lv = re.findall(r'auth_audit:(\d+)', t)
check("the auth class is never raised past 2 (level 3 = every successful login)", lv and all(int(x) <= 2 for x in lv), lv)
check("no deprecated `syslog =` line", not re.search(r'"syslog\s*=', t))

al = os.path.join(SRC, "samba-4.15.13", "build", "samba-4.15.13", "auth", "auth_log.c")
if os.path.isfile(al):
    a = open(al, encoding="utf-8", errors="replace").read()
    check("Samba logs a refused login at level 2 (AUTH_FAILURE_LEVEL)", re.search(r"#define AUTH_FAILURE_LEVEL 2\b", a) is not None)
    check("and a success at 3 (AUTH_SUCCESS_LEVEL), which stays out", re.search(r"#define AUTH_SUCCESS_LEVEL 3\b", a) is not None)
else:
    print("skip the Samba source checks (unpacked source not present)")

if fails:
    print("\n".join("FAILED: " + f for f in fails)); sys.exit(1)
print("all checks passed")
