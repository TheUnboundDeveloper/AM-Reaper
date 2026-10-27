#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Samba 4 account enrollment runs after its runtime directories exist (2026-10-11).

WHY THIS EXISTS. start_samba() (rc/usb.c) enrolls the guest and the acc_list accounts with
smbpasswd before it launches nmbd/smbd. As root, Samba 4.15's smbpasswd calls secrets_init()
before anything else, which opens <private dir>/secrets.tdb (/var/lib/samba/private) and returns 1
without a message when that directory is missing. The directories used to be created just before
the daemons, i.e. AFTER the enrollment, so on the first Samba start of a boot (fresh tmpfs) every
enrollment failed silently, smbd created an empty /etc/samba/smbpasswd and every SMB login was
refused until something restarted Samba (field: RT-BE96U v3.4.0, the owner's box; the syslog tell
is smbd's "startsmbfilepwent_internal: file /etc/samba/smbpasswd did not exist. File successfully
created."). The fix makes the directories first and logs an enrollment failure by account name.

WHAT IT DOES. Reads rc/usb.c, isolates start_samba(), and checks that /var/lib/samba/private is
made before the first smbpasswd call, that the SAMBA4 enrollment results are checked and logged,
and that no log line in the function can carry the password buffers. A negative self-test moves
the mkdir back below the enrollment and expects the ordering check to fail. Exit 0 pass, 1 fail,
77 skipped (no router source tree - argv[1] or REAPER_ROUTER_SRC)."""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
USB = os.path.join(SRC, "rc", "usb.c") if SRC else ""
if not USB or not os.path.isfile(USB):
    skip("no router source tree with rc/usb.c (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

src = open(USB, encoding="utf-8", errors="replace").read()

def start_samba_body(text):
    m = re.search(r"^start_samba\(void\)\n\{\n", text, re.M)
    if not m:
        return ""
    end = text.find("\n}\n", m.end())
    return text[m.end():end] if end > 0 else ""

# the enrollment command forms (every build flavour); a comment or an unlink() naming the
# passdb file is not an invocation
ENROLL_FORMS = ('|/usr/bin/smbpasswd', '|/usr/sbin/smbpasswd', '"/usr/sbin/smbpasswd', '"smbpasswd ',
                'tsmb-passwd')

def first_enrollment(body):
    hits = [i for i in (body.find(f) for f in ENROLL_FORMS) if i >= 0]
    return min(hits) if hits else -1

def dirs_precede_enrollment(body, d="/var/lib/samba/private"):
    """True when the directory is created before the first smbpasswd invocation."""
    mk = body.find('mkdir_if_none("%s")' % d)
    first_enroll = first_enrollment(body)
    return mk >= 0 and first_enroll >= 0 and mk < first_enroll

body = start_samba_body(src)
check("usb.c: start_samba() found", bool(body))
check("usb.c: an smbpasswd enrollment command is present", first_enrollment(body) >= 0)
check("usb.c: /var/lib/samba/private is made before the first smbpasswd call",
      dirs_precede_enrollment(body))
for d in ("/var/run/samba", "/var/log/samba", "/var/lib/samba", "/var/cache/samba"):
    check("usb.c: %s is made before the first smbpasswd call" % d, dirs_precede_enrollment(body, d))
pm = body.find('chmod("/var/lib/samba/private", 0700);')
check("usb.c: the private dir goes back to 0700 after the 0777 mkdirs, before the first smbpasswd call (2026-10-13)",
      pm > body.find('mkdir_if_none("/var/lib/samba/private")') > -1 and 0 < pm < first_enrollment(body))
check("usb.c: the directory block is guarded for SAMBA4 and sits inside start_samba()",
      "#if defined(RTCONFIG_SAMBA4)\n\t/* reaper: the Samba 4 runtime dirs must exist BEFORE" in body)
check("usb.c: guest enrollment result is checked and logged",
      'if (system("echo -e \\"\\n\\n\\" |/usr/bin/smbpasswd -c /etc/smb.conf -s -a nobody") != 0)' in body
      and 'logmessage("Samba Server", "guest account enrollment failed' in body)
# 40585 base (merge stop 60): ASUS enrolls through fork/pipe/execl (no shell); the log reads waitpid()'s status
check("usb.c: account enrollment result is checked and logged by name",
      re.search(r"waitpid\(_pid, &_st, 0\);(?:\s*/\*.*?\*/)?\s*if \(!WIFEXITED\(_st\) \|\| WEXITSTATUS\(_st\) != 0\)\s*"
                r'logmessage\("Samba Server", "account enrollment failed for %s[^"]*", char_user\);', body, re.S) is not None)
leaks = [l for l in body.splitlines()
         if "logmessage(" in l and re.search(r"\b(cmd|suit_passwd|char_passwd|dec_passwd|tmp_ascii_passwd)\b", l)]
check("usb.c: no log line in start_samba() carries a password buffer", not leaks, leaks)

# negative self-test: the pre-fix ordering must be caught
pre = body.replace('\tmkdir_if_none("/var/lib/samba/private");\n', "", 1)
pre = pre.replace('\tmkdir_if_none("/var/run/samba");\t/* SAMBA4: the full set is made above, before enrollment */\n',
                  '\tmkdir_if_none("/var/run/samba");\n\tmkdir_if_none("/var/lib/samba/private");\n', 1)
check("self-test: the ordering check fails on the pre-fix layout",
      body and not dirs_precede_enrollment(pre))

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails:
    print(" - " + f)
sys.exit(1 if fails else 0)
