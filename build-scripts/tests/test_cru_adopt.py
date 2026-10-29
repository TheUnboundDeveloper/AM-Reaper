#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cru adopts a crontab orphaned by a login-name change (2026-10-10).

WHY THIS EXISTS. cru keeps the jobs in /var/spool/cron/crontabs/<login name>; busybox crond skips a
crontab whose name is not a user in /etc/passwd; a login-name change (Administration > System via the
closed do_chpass, or the pre-v3.3.1 setup box) rebuilds /etc/passwd under the new name without a
reboot. Every job registered at boot then sat in a file crond ignores while "cru l" read the new
name's empty file (field: GT-BE98 on v3.0.0, every cru job dead). cru now folds such an orphan into
the current crontab under its own lock, on add, delete and list.

WHAT IT DOES. Runs the real others/cru under /bin/sh in a sandbox: the spool, lock and passwd paths
rewritten to a temp dir, `nvram` and `logger` stubbed on PATH. Checks the adoption, the #id#
precedence, that a real user's crontab and an unreadable passwd are left alone, and that ordinary
add / delete / list behave exactly as before. Exit 0 pass, 1 fail, 77 skipped (no router source tree
- argv[1] or REAPER_ROUTER_SRC - or no sh / flock on the host)."""
import os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
CRU = os.path.join(SRC, "others", "cru") if SRC else ""
if not CRU or not os.path.isfile(CRU):
    skip("no router source tree with others/cru (argv[1] or REAPER_ROUTER_SRC)")
SH = shutil.which("sh"); FLOCK = shutil.which("flock")
if not SH or not FLOCK:
    skip("no sh or flock on this host")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

src = open(CRU, encoding="utf-8").read()
check("cru: adopt() runs under the cru lock on add/delete and on list",
      src.count("flock -x 278\n\t\tadopt\n") == 2 and "adopt() {" in src)
check("cru: nothing moves unless /etc/passwd is readable and lists the current login",
      '[ -n "$ME" ] && [ -r "$P" ] || return 0' in src and "awk -F: -v n=\"$ME\" '$1==n{f=1} END{exit !f}' \"$P\" || return 0" in src)
check("cru: a crontab named for a user that still exists is never touched",
      "awk -F: -v n=\"$B\" '$1==n{f=1} END{exit !f}' \"$P\" && continue" in src)
check("cru: the log line names no login", 'logger -t cru "moved $C cron job(s) left under a login name that no longer exists' in src)

class Box:
    def __init__(self, login, passwd_users, files):
        self.t = tempfile.mkdtemp(prefix="cru-")
        self.spool = os.path.join(self.t, "spool"); os.makedirs(self.spool)
        self.passwd = os.path.join(self.t, "passwd")
        if passwd_users is not None:
            open(self.passwd, "w").write("".join("%s:x:%d:0::/root:/bin/sh\n" % (u, i) for i, u in enumerate(passwd_users)))
        for name, body in files.items():
            open(os.path.join(self.spool, name), "w").write(body)
        bindir = os.path.join(self.t, "bin"); os.makedirs(bindir)
        open(os.path.join(bindir, "nvram"), "w").write('#!/bin/sh\n[ "$1" = get ] && [ "$2" = http_username ] && echo "%s"\n' % login)
        open(os.path.join(bindir, "logger"), "w").write('#!/bin/sh\necho "$@" >>"%s/log"\n' % self.t)
        for b in ("nvram", "logger"): os.chmod(os.path.join(bindir, b), 0o755)
        s = (src.replace('D="/var/spool/cron/crontabs"', 'D="%s"' % self.spool)
                .replace('L="/var/lock/cron.lock"', 'L="%s/cron.lock"' % self.t)
                .replace('P="/etc/passwd"', 'P="%s"' % self.passwd)
                # by absolute path: a busybox ash built to prefer applets runs its own
                # `logger` and never looks at PATH (the router does, rightly)
                .replace("logger -t cru", '"%s/logger" -t cru' % bindir))
        self.cru = os.path.join(self.t, "cru"); open(self.cru, "w").write(s)
        self.env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""))
    def run(self, *a):
        return subprocess.run([SH, self.cru] + list(a), capture_output=True, text=True, env=self.env)
    def files(self):
        return sorted(os.listdir(self.spool))
    def read(self, name):
        p = os.path.join(self.spool, name)
        return open(p).read() if os.path.exists(p) else None
    def log(self):
        p = os.path.join(self.t, "log"); return open(p).read() if os.path.exists(p) else ""
    def done(self):
        shutil.rmtree(self.t, ignore_errors=True)

OLD = "*/5 * * * * sh /tmp/rwatch.sh #rwatch#\n15 3 * * * /usr/sbin/rwarden update #rwarden#\n"

# 1. the field case: renamed login, an add -> both old jobs + the new one, orphan gone, crond told
b = Box("user1", ["user1", "nobody"], {"admin": OLD})
r = b.run("a", "fw", "*/1 * * * * true")
f = b.read("user1") or ""
check("rename then add: the old jobs and the new one end up in the current crontab",
      r.returncode == 0 and "#rwatch#" in f and "#rwarden#" in f and f.rstrip().endswith("#fw#"), f)
check("rename then add: the orphan is removed and crond is told (cron.update)",
      b.files() == ["cron.update", "user1"] and "user1" in (b.read("cron.update") or ""), b.files())
check("rename then add: one log line with the count and no login name",
      "moved 2 cron job(s)" in b.log() and "admin" not in b.log() and "user1" not in b.log(), b.log())
b.done()

# 2. cru l adopts too, and lists the truth
b = Box("user1", ["user1"], {"admin": OLD})
r = b.run("l")
check("rename then list: cru l shows the adopted jobs", r.stdout == OLD and b.files() == ["cron.update", "user1"], (r.stdout, b.files()))
b.done()

# 3. an #id# already in the current crontab wins
b = Box("user1", ["user1"], {"admin": OLD, "user1": "*/7 * * * * sh /tmp/rwatch.sh #rwatch#\n"})
b.run("l")
f = b.read("user1") or ""
check("an #id# already in the current crontab wins; the other old job is added once",
      f.count("#rwatch#") == 1 and "*/7 " in f and f.count("#rwarden#") == 1 and "moved 1 cron job(s)" in b.log(), f)
b.done()

# 4. a crontab named for a user that still exists is left alone
b = Box("user1", ["user1", "nobody"], {"nobody": "0 * * * * true #n#\n"})
b.run("a", "x", "0 0 * * * true")
check("a real user's crontab is never moved", b.read("nobody") == "0 * * * * true #n#\n" and "#n#" not in (b.read("user1") or ""))
b.done()

# 5. passwd unreadable, or not listing the current login: nothing moves
for label, users in (("missing /etc/passwd", None), ("passwd without the current login", ["admin"])):
    b = Box("user1", users, {"admin": OLD})
    b.run("l")
    check("%s: the old crontab is left where it is" % label, b.read("admin") == OLD and not b.log(), (b.files(), b.log()))
    b.done()

# 6. ordinary use is unchanged: add, replace by id, delete, list
b = Box("admin", ["admin"], {})
b.run("a", "j1", "1 * * * * one"); b.run("a", "j2", "2 * * * * two"); b.run("a", "j1", "3 * * * * three")
mid = b.read("admin"); b.run("d", "j2"); fin = b.read("admin"); ls = b.run("l").stdout
check("ordinary add / replace-by-id / delete / list behave as before",
      mid == "2 * * * * two #j2#\n3 * * * * three #j1#\n" and fin == "3 * * * * three #j1#\n" and ls == fin and not b.log(), (mid, fin))
b.done()

# 7. the usage text still prints for no arguments
b = Box("admin", ["admin"], {})
check("usage text unchanged", "Cron Utility" in b.run().stdout)
b.done()

here = os.path.dirname(os.path.abspath(__file__))
mk = os.path.join(here, "..", "verify_markers.txt")
if os.path.isfile(mk):
    check("verify_markers pins the adoption in the staged cru",
          "usr/sbin/cru|left under a login name that no longer exists|1" in open(mk, encoding="utf-8").read())

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("all checks passed")
