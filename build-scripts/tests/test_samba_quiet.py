#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Samba 4.15 starts and serves without four noise lines in the log.

WHY THIS EXISTS (2026-10-23). With Samba on, the router logged, per connection or per start:
  1. dos charset 'CP850' unavailable - using ASCII
       smbd uses glibc's native iconv; the image shipped no /usr/lib/gconv, so CP850 (smbd's
       default dos charset) could not load. Fix: the samba-4.15.13-install recipe ships
       IBM850.so and a gconv-modules holding only its alias/module lines.
  2. startsmbfilepwent_internal: file /etc/samba/smbpasswd did not exist. File successfully created.
       start_samba() deletes the passdb and the first `smbpasswd -a` recreated it. Fix: start_samba
       creates it empty (0600) after the unlink and before the first enrollment.
  3. sys_get_quota: sys_path_to_bdev() failed for path [.]!
       waf auto-enabled quotas. Fix: --without-quotas, asserted after configure, and the
       build-reaper.sh stamp now covers the script itself - before, a configure-option change
       alone was skipped as "already built" and the old smbd reshipped.
  4. Unknown parameter encountered: "use spnego"   (and "auth methods" in guest mode)
       write_smb_conf.c still emitted Samba-3 parameters. Fix: guarded off for RTCONFIG_SAMBA4.

WHAT IT DOES. Static checks for 1-3. For 4, a small preprocessor evaluates write_smb_conf.c with
this tree's .config (RTCONFIG_SAMBA4 on, Tuxera off; a condition on anything the .config does not
decide keeps both branches) and asserts every parameter name the SAMBA4 path can emit is in Samba
4.15's own parameter table (bin/default/lib/param/param_table_gen.c from the extracted build tree),
compared the way Samba compares them: case- and whitespace-insensitive ("map read only" IS
"map readonly"). A negative self-test proves the checker flags an unguarded "use spnego".

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass the tree's release/src/router as
argv[1] or REAPER_ROUTER_SRC). The parameter half skips (with a note) when the Samba build tree or
.config is absent. REAPER_SMBCONF_SRC overrides the write_smb_conf.c path (to show red on the old file).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
USB = os.path.join(SRC, "rc", "usb.c")
if not SRC or not os.path.isfile(USB):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

# ---- 3: quotas off, asserted, and the stamp covers the recipe
br = read("samba-4.15.13/build-reaper.sh")
cfg = br[br.find("./configure --cross-compile"):]
cfg = cfg[:cfg.find("\n\n")]
check("Samba configure carries --without-quotas", "--without-quotas" in cfg)
check("build-reaper.sh hard-fails if WITH_QUOTAS survives configure",
      "grep -q '^#define WITH_QUOTAS' bin/default/include/config.h" in br)
m = re.search(r'^STAMP_SIG="\$\(cat (.*?) 2>/dev/null', br, re.M)
check("the rebuild stamp hashes build-reaper.sh itself (a configure change must rebuild)",
      m is not None and '"$PKGDIR/build-reaper.sh"' in m.group(1), m.group(1) if m else "STAMP_SIG not found")

# ---- 1: CP850 for glibc iconv
mk = read("Makefile")
rec = mk[mk.find("\nsamba-4.15.13-install:"):]
rec = rec[:rec.find("\n\n", 1)]
check("the install recipe ships usr/lib/gconv/IBM850.so",
      "$(SMB4_GCONV)/IBM850.so $(INSTALLDIR)/samba-4.15.13/usr/lib/gconv/IBM850.so" in rec)
check("gconv-modules is reduced to the IBM850 lines, and the recipe fails if that left nothing",
      """awk '$$2 == "IBM850//" || $$3 == "IBM850//"' $(SMB4_GCONV)/gconv-modules""" in rec
      and "grep -q '^module[[:space:]]*IBM850//'" in rec)
check("the recipe fails when the toolchain gconv files are missing",
      'test -f "$(SMB4_GCONV)/IBM850.so" && test -f "$(SMB4_GCONV)/gconv-modules"' in rec)

# ---- 2: passdb created empty between the unlink and the first enrollment
usb = read("rc/usb.c")
st = usb.find("start_samba(")
st = usb.find("{", st)
body = usb[st:usb.find("\n}\n", st)]
i_un = body.find('unlink("/etc/samba/smbpasswd");')
i_mk = body.find('open("/etc/samba/smbpasswd", O_WRONLY | O_CREAT | O_TRUNC, 0600)')
i_en = body.find("smbpasswd -c /etc/smb.conf -s -a nobody")
check("start_samba creates an empty 0600 passdb after the unlink and before the first enrollment",
      0 <= i_un < i_mk < i_en, (i_un, i_mk, i_en))

# ---- 4: every parameter the SAMBA4 path emits is a Samba 4.15 parameter
PT = os.path.join(SRC, "samba-4.15.13", "build", "samba-4.15.13", "bin", "default", "lib", "param", "param_table_gen.c")
CONF = os.path.join(SRC, ".config")

def norm(name):
    return re.sub(r"\s+", "", name).lower()

def strip_comments(text):
    """drop C comments, keeping string literals (which may hold '/*') and line numbers"""
    def rep(m):
        s = m.group(0)
        if s.startswith('"'):
            return s
        return "\n" * s.count("\n")
    return re.sub(r'"(?:\\.|[^"\\\n])*"|/\*.*?\*/|//[^\n]*', rep, text, flags=re.S)

def make_eval(on, off):
    def ev(expr):
        e = expr.strip()
        e = re.sub(r"defined\s*\(\s*(\w+)\s*\)|defined\s+(\w+)",
                   lambda m: " D_%s " % (m.group(1) or m.group(2)), e)
        def val(m):
            n = m.group(1)
            if n in on:
                return "1"
            if n in off or n.startswith("RTCONFIG_"):
                return "0"
            return "U"
        e = re.sub(r"\bD_(\w+)\b", val, e)
        if "U" in e.split() or re.search(r"[A-Za-z_]", e.replace("U", "")):
            return None
        e = e.replace("&&", " and ").replace("||", " or ").replace("!", " not ")
        try:
            return bool(eval(e, {"__builtins__": {}}))
        except Exception:
            return None
    return ev

def live_lines(text, ev):
    """(lineno, line) for every line an evaluation can reach; unknown conditions keep both branches"""
    out, stack, active = [], [], True
    for no, line in enumerate(text.split("\n"), 1):
        s = line.strip()
        d = re.match(r"#\s*(ifdef|ifndef|if|elif|else|endif)\b(.*)", s)
        if not d:
            if active:
                out.append((no, line))
            continue
        kw, rest = d.group(1), d.group(2)
        if kw in ("if", "ifdef", "ifndef"):
            expr = {"ifdef": "defined(%s)", "ifndef": "!defined(%s)"}.get(kw, "%s") % rest.strip()
            v = ev(expr)
            stack.append([active, v])
            active = active and v is not False
        elif kw == "elif":
            parent, taken = stack[-1]
            if taken is True:
                active = False
            else:
                v = ev(rest)
                active = parent and v is not False
                stack[-1][1] = True if v is True else (None if (v is None or taken is None) else False)
        elif kw == "else":
            parent, taken = stack[-1]
            active = parent and taken is not True
        elif kw == "endif":
            active = stack.pop()[0] if stack else True
    return out

EMIT = re.compile(r'fprintf\s*\(\s*fp\s*,\s*"([a-z][a-z0-9 ]*?)\s*=')
# runtime-dead on SAMBA4: the condition carries "&& 0" (checked below), so the name never reaches smb.conf
RUNTIME_DEAD = {"use recvfile"}

def unknown_params(text, known, ev):
    bad = []
    for no, line in live_lines(strip_comments(text), ev):
        for m in EMIT.finditer(line):
            n = m.group(1)
            if norm(n) not in known and n not in RUNTIME_DEAD:
                bad.append((n, no))
    return bad

if not os.path.isfile(PT) or not os.path.isfile(CONF):
    print("note: Samba build tree or .config absent - parameter-table half not checked")
else:
    known = {norm(l) for l in re.findall(r'\.label\s*=\s*"([^"]+)"', open(PT, encoding="utf-8", errors="replace").read())}
    conf = open(CONF, encoding="utf-8", errors="replace").read()
    on = set(re.findall(r"^(RTCONFIG_\w+)=y", conf, re.M))
    off = set(re.findall(r"^# (RTCONFIG_\w+) is not set", conf, re.M))
    check("this tree builds Samba 4 and not the Tuxera smbd (the path this check evaluates)",
          "RTCONFIG_SAMBA4" in on and "RTCONFIG_TUXERA_SMBD" not in on)
    ev = make_eval(on, off)
    wsc_path = os.environ.get("REAPER_SMBCONF_SRC") or os.path.join(SRC, "libdisk", "write_smb_conf.c")
    wsc = open(wsc_path, encoding="utf-8", errors="surrogateescape").read()
    bad = unknown_params(wsc, known, ev)
    check("every parameter write_smb_conf.c can emit for Samba 4 is a Samba 4.15 parameter",
          not bad, ", ".join("%r (line %d)" % b for b in bad))
    check("the one runtime-dead name keeps its && 0 guard (use recvfile)",
          re.search(r"defined\(RTCONFIG_SAMBA4\)\s*\n\s*&& 0\s*\n#endif\s*\n\s*\)\s*\n\s*fprintf\(fp, \"use recvfile = yes", wsc) is not None)
    # negative self-test: the checker must flag the pre-fix emission
    probe = '#if defined(RTCONFIG_SAMBA4)\n\tfprintf(fp, "use spnego = %s\\n", "yes");\n#endif\n'
    check("negative self-test: an unguarded \"use spnego\" is flagged",
          [b[0] for b in unknown_params(probe, known, ev)] == ["use spnego"])
    probe2 = '#if !defined(RTCONFIG_SAMBA4)\n\tfprintf(fp, "use spnego = %s\\n", "yes");\n#endif\n\tfprintf(fp, "map read only = no\\n");\n'
    check("self-test: a SAMBA4-guarded line and a whitespace variant (map read only) pass",
          unknown_params(probe2, known, ev) == [])

if fails:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
print("PASS test_samba_quiet")
