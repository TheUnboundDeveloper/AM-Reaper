#!/usr/bin/env python3
"""Guest Portal SMB client stand-in (REAPER-SMBSTUB, review 2026-11-17 phase 6 slice 1, plan 2026-11-19 1d).

WHY THIS EXISTS. The Guest Portal web server (lighttpd, run as uamsrv for unauthenticated guests) carries
DT_NEEDED libsmbclient.so.0 and imports 29 smbc_* functions for the AiCloud SMB-share code. AiCloud is not built
and every one of those calls sits behind con->mode == SMB_BASIC / SMB_NTLM, which nothing that ships sets. The
image used to ship the 3.69 MB Samba 3.5.8 (2011) client library for it, plus an unused 140 KB Samba 4
libsmbclient.so.0.7.0 with the same soname. router/libsmbclient-stub/ replaces the first (same soname, the 29
names, each failing ENOSYS) and buildFS drops the second.

Two install facts this pins, because each one silently undoes the swap:
  - samba-3.5.8's OWN install step (an obj-y package) put its library back AFTER lighttpd's install (obj-y order
    = merge order into the root filesystem), so it must not be an obj-y package of the portal any more, while
    lighttpd still builds and links against it (its dependency stays);
  - samba-4.15.13 merges BEFORE lighttpd, so lighttpd's regular file replaces Samba 4's libsmbclient.so.0 link.
If the server ever imports a new smbc_* name, the stand-in must grow: the shipped-binary check below catches it.

WHAT IT DOES. Reads router/libsmbclient-stub/*, router/Makefile, src-rt-5.04behnd.4916/targets/buildFS and
samba-3.5.8/source3/include/libsmbclient.h; compiles the stand-in with the host gcc and calls every function
through ctypes; runs buildFS's reaper_rm_lib on a scratch tree; cross-checks the ARM build and the shipped lighttpd
when the toolchain / a built root filesystem are present.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] / REAPER_ROUTER_SRC)."""
import ctypes, errno, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "Makefile")) or not os.path.isdir(os.path.join(SRC, "lighttpd-1.4.39")):
    print("SKIP: no router source tree with Makefile + lighttpd-1.4.39 (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
PLAT = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916"))
STUB = os.path.join(SRC, "libsmbclient-stub")
fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))


def rd(p):
    return open(p, encoding="utf-8", errors="surrogateescape").read()


# name -> (return type as in the real prototype, failure value the stand-in returns)
FUNCS = {
    "smbc_open": ("int", "-1"), "smbc_creat": ("int", "-1"), "smbc_read": ("ssize_t", "-1"),
    "smbc_write": ("ssize_t", "-1"), "smbc_lseek": ("off_t", "(off_t)-1"), "smbc_close": ("int", "-1"),
    "smbc_unlink": ("int", "-1"), "smbc_rename": ("int", "-1"), "smbc_opendir": ("int", "-1"),
    "smbc_closedir": ("int", "-1"), "smbc_readdir": ("struct smbc_dirent*", "NULL"), "smbc_mkdir": ("int", "-1"),
    "smbc_rmdir": ("int", "-1"), "smbc_stat": ("int", "-1"), "smbc_parse_path": ("int", "-1"),
    "smbc_cli_stat": ("int", "-1"), "smbc_cli_opendir": ("SMBCFILE*", "NULL"),
    "smbc_cli_open_share": ("SMBCFILE*", "NULL"), "smbc_cli_rmdir": ("uint32_t", "STUB_NT_STATUS_NOT_IMPLEMENTED"),
    "smbc_cli_rename": ("uint32_t", "STUB_NT_STATUS_NOT_IMPLEMENTED"), "smbc_cli_readdir": ("struct smbc_dirent*", "NULL"),
    "smbc_cli_closedir": ("int", "-1"), "smbc_cli_ntcreate": ("smb_file_t*", "NULL"),
    "smbc_cli_open": ("smb_file_t*", "NULL"), "smbc_cli_lseek": ("uint32_t", "(uint32_t)-1"),
    "smbc_cli_write": ("size_t", "(size_t)-1"), "smbc_cli_read": ("size_t", "(size_t)-1"),
    "smbc_cli_close": ("uint32_t", "STUB_NT_STATUS_NOT_IMPLEMENTED"),
    "smbc_cli_unlink": ("uint32_t", "STUB_NT_STATUS_NOT_IMPLEMENTED"),
}
NAMES = sorted(FUNCS)
check("the list holds the 29 names the shipped server imports", len(NAMES) == 29, len(NAMES))

# ---------------------------------------------------------------- the stand-in's files
for f in ("Makefile", "README.md", "libsmbclient_stub.c", "libsmbclient.map"):
    check("libsmbclient-stub/%s exists" % f, os.path.isfile(os.path.join(STUB, f)))
if not all(os.path.isfile(os.path.join(STUB, f)) for f in ("Makefile", "libsmbclient_stub.c", "libsmbclient.map")):
    print("\n%d check(s) failed" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
smk = rd(os.path.join(STUB, "Makefile"))
csrc = rd(os.path.join(STUB, "libsmbclient_stub.c"))
smap = rd(os.path.join(STUB, "libsmbclient.map"))
check("stub Makefile: common.mak skeleton, PIC, -Os, hidden visibility, 64-bit off_t, FORTIFY, stack protector",
      smk.startswith("# REAPER-SMBSTUB") and "\ninclude ../common.mak\n" in smk
      and all(x in smk for x in ("-fPIC", "-Os", "-fvisibility=hidden", "-D_FILE_OFFSET_BITS=64", "-D_FORTIFY_SOURCE=2",
                                 "-fstack-protector-strong")))
check("stub Makefile: -z defs, full RELRO, non-executable stack, gc-sections",
      all(x in smk for x in ("-Wl,-z,defs", "-Wl,-z,relro", "-Wl,-z,now", "-Wl,-z,noexecstack", "-Wl,--gc-sections")))
check("stub Makefile: soname libsmbclient.so.0 with the version script",
      "-Wl,-soname,libsmbclient.so.0 " in smk and "-Wl,--version-script=libsmbclient.map" in smk)
check("stub Makefile: no forwarding (no -ldl, no dlopen)", "-ldl" not in smk and "dlopen" not in csrc)
check("stub Makefile: installs usr/lib/libsmbclient.so.0, stripped unless RTCONFIG_DEBUG",
      "install -D libsmbclient.so.0 $(INSTALLDIR)$(INSTALLSUBDIR)/usr/lib/libsmbclient.so.0" in smk
      and "$(if $(RTCONFIG_DEBUG),,$(STRIP) $(INSTALLDIR)$(INSTALLSUBDIR)/usr/lib/libsmbclient.so.0)" in smk)
check("stub C source: ASCII only", all(ord(c) < 128 for c in csrc))
check("stub C source: marker once", csrc.count("REAPER-SMBSTUB") == 1)

body = re.sub(r"/\*.*?\*/", "", smap, flags=re.S)
mg = re.search(r"^\s*\{\s*global:\s*(.*?)\blocal:\s*\*;\s*\};\s*$", body, re.S)
mapnames = sorted(x.strip() for x in mg.group(1).split(";") if x.strip()) if mg else []
check("map: an anonymous version node (the server imports the names unversioned), local: *", mg is not None, body[:300])
check("map: exports exactly the 29 names", mapnames == NAMES, sorted(set(mapnames) ^ set(NAMES)))

check("C: STUB_FAIL sets errno = ENOSYS and returns the value",
      "#define STUB_FAIL(val) do { errno = ENOSYS; return (val); } while (0)" in csrc)
check("C: NT_STATUS_NOT_IMPLEMENTED is 0xC0000002",
      "#define STUB_NT_STATUS_NOT_IMPLEMENTED ((uint32_t)0xC0000002u)" in csrc)
defs = {}
for m in re.finditer(r"^STUB_EXPORT\s+(.+?)\b(smbc_\w+)\(([^)]*)\)\s*\{(.*?)\}\s*$", csrc, re.M | re.S):
    defs[m.group(2)] = (re.sub(r"\s+", " ", m.group(1)).strip().replace(" *", "*"), m.group(4))
check("C: defines exactly the 29 exported functions", sorted(defs) == NAMES, sorted(set(defs) ^ set(NAMES)))
for n in NAMES:
    if n not in defs:
        continue
    rt, b = defs[n]
    want_rt, want_val = FUNCS[n]
    stmts = re.findall(r"STUB_FAIL\(([^;]*)\);", b)
    check("C: %s returns %s and fails with errno ENOSYS -> %s" % (n, want_rt, want_val),
          rt == want_rt and stmts == [want_val] and "return" not in b, (rt, stmts))
check("C: no exported definition outside the list", csrc.count("STUB_EXPORT ") == 29 + 1, csrc.count("STUB_EXPORT "))

# prototypes against the real header (return types)
H = os.path.join(SRC, "samba-3.5.8", "source3", "include", "libsmbclient.h")
if os.path.isfile(H):
    h = rd(H)
    bad = []
    for n in NAMES:
        m = re.search(r"^([A-Za-z_][\w \t\*]*?)\b%s\s*\(" % n, h, re.M)
        hrt = re.sub(r"\s+", "", m.group(1)) if m else None
        if hrt != re.sub(r"\s+", "", FUNCS[n][0]):
            bad.append((n, hrt))
    check("C: each return type matches samba-3.5.8's libsmbclient.h", not bad, bad)
else:
    print("note: samba-3.5.8/source3/include/libsmbclient.h not in this tree - prototype check not run")

# ---------------------------------------------------------------- host build: call every function
gcc = shutil.which("gcc")
tmp = tempfile.mkdtemp(prefix="smbstub_")
try:
    if gcc:
        so = os.path.join(tmp, "libsmbclient.so.0")
        r = subprocess.run([gcc, "-shared", "-fPIC", "-Os", "-Wall", "-Wextra", "-Werror", "-fvisibility=hidden",
                            "-D_FILE_OFFSET_BITS=64", "-Wl,-z,defs", "-Wl,-soname,libsmbclient.so.0",
                            "-Wl,--version-script=" + os.path.join(STUB, "libsmbclient.map"),
                            "-o", so, os.path.join(STUB, "libsmbclient_stub.c")],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        check("host: the stand-in compiles with -Wall -Wextra -Werror and links with -z defs", r.returncode == 0, r.stdout)
        if r.returncode == 0:
            lib = ctypes.CDLL(so, use_errno=True)
            NT_NI = 0xC0000002
            for n in NAMES:
                rt, val = FUNCS[n]
                f = getattr(lib, n)
                if rt.endswith("*"):
                    f.restype, want = ctypes.c_void_p, None
                elif rt in ("int",):
                    f.restype, want = ctypes.c_int, -1
                elif rt in ("ssize_t", "off_t"):
                    f.restype, want = ctypes.c_int64 if rt == "off_t" else ctypes.c_ssize_t, -1
                elif rt == "size_t":
                    f.restype, want = ctypes.c_size_t, ctypes.c_size_t(-1).value
                else:   # uint32_t
                    f.restype, want = ctypes.c_uint32, (0xFFFFFFFF if val == "(uint32_t)-1" else NT_NI)
                ctypes.set_errno(0)
                got = f()
                err = ctypes.get_errno()
                check("host call: %s -> %r, errno ENOSYS" % (n, want), got == want and err == errno.ENOSYS, (got, err))
            ro = shutil.which("readelf")
            if ro:
                d = subprocess.run([ro, "-dW", so], stdout=subprocess.PIPE, universal_newlines=True).stdout
                s = subprocess.run([ro, "-W", "--dyn-syms", so], stdout=subprocess.PIPE, universal_newlines=True).stdout
                exp = sorted(l.split()[7] for l in s.splitlines()
                             if len(l.split()) >= 8 and l.split()[0].endswith(":") and l.split()[6] != "UND" and l.split()[4] == "GLOBAL")
                check("host: soname libsmbclient.so.0, no symbol version definitions",
                      "Library soname: [libsmbclient.so.0]" in d and "VERDEF" not in d, d[-400:])
                check("host: the dynamic exports are exactly the 29 names", exp == NAMES, sorted(set(exp) ^ set(NAMES)))
    else:
        print("note: no host gcc - the host build and the calls are not run")

    # ---------------------------------------------------------------- the ARM build (when the toolchain is here)
    xcc = "/opt/toolchains/crosstools-arm_softfp-gcc-10.3-linux-4.19-glibc-2.32-binutils-2.36.1/usr/bin/arm-buildroot-linux-gnueabi-"
    if os.path.isfile(xcc + "gcc"):
        aso = os.path.join(tmp, "arm.so")
        r = subprocess.run([xcc + "gcc", "-shared", "-fPIC", "-Os", "-Wall", "-Wextra", "-Werror", "-march=armv7-a", "-marm",
                            "-fvisibility=hidden", "-D_FILE_OFFSET_BITS=64", "-D_FORTIFY_SOURCE=2", "-fstack-protector-strong",
                            "-Wl,-z,defs", "-Wl,-z,relro", "-Wl,-z,now", "-Wl,-z,noexecstack", "-Wl,--gc-sections",
                            "-Wl,-soname,libsmbclient.so.0", "-Wl,--version-script=" + os.path.join(STUB, "libsmbclient.map"),
                            "-o", aso, os.path.join(STUB, "libsmbclient_stub.c")],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        check("ARM: the stand-in cross-compiles (the router's arm_softfp gcc 10.3)", r.returncode == 0, r.stdout)
        if r.returncode == 0:
            s = subprocess.run([xcc + "readelf", "-W", "--dyn-syms", aso], stdout=subprocess.PIPE, universal_newlines=True).stdout
            d = subprocess.run([xcc + "readelf", "-dW", aso], stdout=subprocess.PIPE, universal_newlines=True).stdout
            rows = [l.split() for l in s.splitlines() if len(l.split()) >= 8 and l.split()[0].endswith(":")]
            exp = sorted(x[7] for x in rows if x[6] != "UND" and x[4] == "GLOBAL")
            und = sorted(x[7] for x in rows if x[6] == "UND" and x[4] == "GLOBAL")
            need = re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]", d)
            check("ARM: exports are exactly the 29 names", exp == NAMES, sorted(set(exp) ^ set(NAMES)))
            check("ARM: needs only libc, and imports only libc's errno accessor", need == ["libc.so.6"]
                  and all(u.startswith("__errno_location@") for u in und), (need, und))
            check("ARM: soname libsmbclient.so.0, BIND_NOW, no version definitions",
                  "Library soname: [libsmbclient.so.0]" in d and "BIND_NOW" in d and "VERDEF" not in d)
    else:
        print("note: no ARM toolchain - the cross build is not run")

    # ---------------------------------------------------------------- the shipped server's imports
    FS = os.path.join(PLAT, "targets", "96813GW", "fs")
    LT = os.path.join(FS, "usr", "sbin", "lighttpd")
    ro = (xcc + "readelf") if os.path.isfile(xcc + "readelf") else shutil.which("readelf")
    if os.path.isfile(LT) and ro:
        s = subprocess.run([ro, "-W", "--dyn-syms", LT], stdout=subprocess.PIPE, universal_newlines=True).stdout
        imp = sorted(l.split()[7] for l in s.splitlines()
                     if len(l.split()) >= 8 and l.split()[0].endswith(":") and l.split()[6] == "UND" and "smbc_" in l.split()[7])
        check("shipped lighttpd: imports exactly these 29 smbc_* names, unversioned", imp == NAMES,
              sorted(set(imp) ^ set(NAMES)))
    else:
        print("note: no built root filesystem (targets/96813GW/fs) - the shipped-binary import check is not run")

    # ---------------------------------------------------------------- router Makefile
    mk = rd(os.path.join(SRC, "Makefile"))
    check("Makefile: samba-3.5.8 is no longer an obj-y package of the portal (its install put the old library back)",
          "obj-$(RTCONFIG_CAPTIVE_PORTAL) += samba-3.5.8" not in mk and mk.count("REAPER-SMBSTUB-OBJ") == 1)
    objs = re.findall(r"^obj-\$\((\w+)\)\s*\+=.*\bsamba-3\.5\.8\b", mk, re.M)
    check("Makefile: the only obj line naming samba-3.5.8 is RTCONFIG_SAMBACLIENT's", objs == ["RTCONFIG_SAMBACLIENT"], objs)
    lo = mk.find("obj-$(RTCONFIG_CAPTIVE_PORTAL) += sqlite libxml2 pcre-8.31 lighttpd-1.4.39 libexif curl")
    s4 = mk.find("obj-$(RTCONFIG_SAMBA4) += samba-4.15.13")
    check("Makefile: lighttpd stays a portal package and merges after samba-4.15.13 (its file replaces Samba 4's link)",
          0 < s4 < lo, (s4, lo))
    dep = re.search(r"^lighttpd-1\.4\.39: (.*)$", mk, re.M)
    check("Makefile: lighttpd still builds against samba-3.5.8 and builds the stand-in first",
          dep is not None and " samba-3.5.8 " in dep.group(1) and " libsmbclient-stub " in dep.group(1),
          dep.group(1) if dep else "")
    i = mk.find("\nlighttpd-1.4.39-install:\n")
    j = mk.find("\nlighttpd-1.4.39-clean:", i)
    rec = mk[i:j] if 0 < i < j else ""
    INST = ("\t\t$(if $(RTCONFIG_SAMBACLIENT),install -D samba-3.5.8/source3/bin/libsmbclient.so.0 "
            "$(INSTALLDIR)/lighttpd-1.4.39/usr/lib/libsmbclient.so.0,"
            "$(MAKE) -C libsmbclient-stub install INSTALLDIR=$(INSTALLDIR)/lighttpd-1.4.39) ; \\\n")
    check("Makefile: lighttpd's install puts the stand-in in usr/lib (the real one only with RTCONFIG_SAMBACLIENT)",
          rec.count(INST) == 1 and rec.count("samba-3.5.8/source3/bin/libsmbclient.so.0") == 1, rec[-1500:])
    check("Makefile: the stand-in goes in after the WebDAV modules are dropped and before the strip lines",
          rec.find("mod_smbdav.so") < rec.find(INST) < rec.find("$(STRIP) -s $(INSTALLDIR)/lighttpd-1.4.39/usr/lib/*.so.0"))
    check("Makefile: the comment says what the library is now",
          "but is the REAPER-SMBSTUB stand-in\n" in mk[max(0, i - 900):i] and "libsmbclient.so.0 stays: DT_NEEDED" not in mk)
    check("Makefile: the stand-in's own target (phony) and its clean, once",
          mk.count("REAPER-SMBSTUB-TARGET") == 1 and ".PHONY: libsmbclient-stub libsmbclient-stub-clean\n" in mk
          and "\nlibsmbclient-stub:\n\t@$(MAKE) -C $@\n" in mk
          and "\nlibsmbclient-stub-clean:\n\t@$(MAKE) -C libsmbclient-stub clean\n" in mk
          and "lighttpd-1.4.39-clean:\n\t-@$(MAKE) -C lighttpd-1.4.39 clean\n\t@rm -f lighttpd-1.4.39/stamp-h1\n"
              "\t-@$(MAKE) -C libsmbclient-stub clean\n" in mk)
    check("Makefile: the stand-in is not an obj-y package of its own (only lighttpd installs it)",
          re.search(r"^obj-.*\blibsmbclient-stub\b", mk, re.M) is None)

    # samba-3.5.8 out of obj-y lost the "$(obj-y) ...: dummy" force; its target name is an existing directory, so
    # without its own dummy make took it as up to date and a clean tree never built the library lighttpd links.
    rule = re.search(r"^samba-3\.5\.8:([^\n]*)\n(\t[^\n]*\n)+", mk, re.M)
    force = re.search(r"^\$\(obj-y\) \$\(obj-n\) \$\(obj-clean\) \$\(obj-install\): dummy$", mk, re.M)
    oclean = re.search(r"^obj-clean := [^\n]*$", mk, re.M)
    oinst = re.search(r"^obj-install := [^\n]*$", mk, re.M)
    check("Makefile: samba-3.5.8's build rule is forced through dummy (REAPER-SMBSTUB-FORCE), once",
          rule is not None and rule.group(1).split() == ["dummy"] and mk.count("REAPER-SMBSTUB-FORCE") == 1
          and rule.group(2) == "\t@$(MAKE) -C samba-3.5.8 $(PARALLEL_BUILD)\n" and ".PHONY: dummy" in mk,
          rule.group(0) if rule else "")
    check("Makefile: the obj-y force line and the obj-clean / obj-install definitions are as the repro assumes",
          force is not None and oclean is not None and "$(obj-)" in oclean.group(0) and oinst is not None
          and "$(obj-y)" in oinst.group(0) and "$(obj-)" not in oinst.group(0))
    cfg = os.path.join(SRC, ".config")
    if os.path.isfile(cfg):
        check("tree .config: RTCONFIG_SAMBACLIENT unset (so obj- holds samba-3.5.8 and obj-clean cleans it)",
              re.search(r"^RTCONFIG_SAMBACLIENT=y", rd(cfg), re.M) is None)
    mkbin = shutil.which("make")
    if mkbin and rule and force and oclean and oinst:
        def repro(samba_rule):
            d = tempfile.mkdtemp(prefix="smbforce_", dir=tmp)
            for sub in ("samba-3.5.8", "lighttpd-1.4.39"):
                os.makedirs(os.path.join(d, sub))
            open(os.path.join(d, "samba-3.5.8", "Makefile"), "w").write("all:\n\t@echo SAMBA358-BUILT\n")
            open(os.path.join(d, "Makefile"), "w").write(
                "obj-y := lighttpd-1.4.39\nobj- := samba-3.5.8\nobj-n :=\n" + oclean.group(0) + "\n" + oinst.group(0) + "\n"
                + samba_rule + "lighttpd-1.4.39: samba-3.5.8\n\t@echo LIGHTTPD-LINK\n" + force.group(0) + "\n"
                + ".PHONY: dummy\n%-install:\n\t@echo INSTALL-$*\n%-clean:\n\t@echo CLEAN-$*\n"
                + "show:\n\t@echo '$($(V))'\n")   # not print-%: %-install / %-clean would win (shorter stem)
            run = lambda *a: subprocess.run([mkbin, "-s", "--no-print-directory", "-C", d] + list(a), stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, universal_newlines=True).stdout
            return run("lighttpd-1.4.39"), run("show", "V=obj-install"), run("show", "V=obj-clean")
        built, inst, clean = repro(rule.group(0))
        check("make repro (real rule text): building lighttpd-1.4.39 runs samba-3.5.8's build first",
              built.split() == ["SAMBA358-BUILT", "LIGHTTPD-LINK"], built)
        check("make repro: samba-3.5.8 is not installed (no samba-3.5.8-install in obj-install)",
              "samba-3.5.8-install" not in inst.split() and "lighttpd-1.4.39-install" in inst.split(), inst)
        check("make repro: make clean still cleans samba-3.5.8 (obj-clean via obj-)", "samba-3.5.8-clean" in clean.split(), clean)
        nb, _, _ = repro("samba-3.5.8:\n\t@$(MAKE) -C samba-3.5.8 $(PARALLEL_BUILD)\n")
        check("make repro control: without dummy the directory reads as up to date (the bug this guards)",
              nb.split() == ["LIGHTTPD-LINK"], nb)
    else:
        print("note: no make (or rule text not found) - the build-force repro is not run")

    # ---------------------------------------------------------------- buildFS
    bf = os.path.join(PLAT, "targets", "buildFS")
    if os.path.isfile(bf):
        b = rd(bf)
        code = "\n".join(l for l in b.split("\n") if not l.lstrip().startswith("#"))
        i = b.find("REAPER-RM-LIBS-1117")
        k = b.find("\n# sample configs", i)
        check("buildFS: the Samba 4 libsmbclient.so.0.7.0 goes through reaper_rm_lib, once, in the RM-LIBS-1117 block",
              code.count("reaper_rm_lib usr/lib/libsmbclient.so.0.7.0\n") == 1
              and 0 < i < b.find("reaper_rm_lib usr/lib/libsmbclient.so.0.7.0") < k and b.count("# REAPER-SMBSTUB") == 1)
        check("buildFS: nothing removes libsmbclient.so.0 itself (the stand-in)",
              re.search(r"libsmbclient\.so\.0(\s|$)", code) is None)
        check("buildFS: the old keep note is gone", "libsmbclient.so.0.7.0 (shares its soname" not in b)
        fm = re.search(r"^reaper_rm_lib\(\) \{.*?^\}\n", b, re.M | re.S)
        sh = shutil.which("sh")
        if fm and sh:
            for case, so0 in (("portal model", "file"), ("model without the portal", "link")):
                root = os.path.join(tmp, "fs_" + so0)
                ul = os.path.join(root, "usr", "lib")
                os.makedirs(ul)
                open(os.path.join(ul, "libsmbclient.so.0.7.0"), "w").write("samba4")
                if so0 == "file":
                    open(os.path.join(ul, "libsmbclient.so.0"), "w").write("stub")
                else:
                    os.symlink("libsmbclient.so.0.7.0", os.path.join(ul, "libsmbclient.so.0"))
                os.symlink("libsmbclient.so.0.7.0", os.path.join(ul, "libsmbclient.so"))
                open(os.path.join(ul, "libsmbconf.so.0.0.1"), "w").write("keep")
                os.symlink("libsmbconf.so.0.0.1", os.path.join(ul, "libsmbconf.so.0"))
                r = subprocess.run([sh, "-c", "R_FS=%s\n%s\nreaper_rm_lib usr/lib/libsmbclient.so.0.7.0\n" % (root, fm.group(0))],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                left = sorted(os.listdir(ul))
                want = ["libsmbclient.so.0", "libsmbconf.so.0", "libsmbconf.so.0.0.1"] if so0 == "file" \
                    else ["libsmbconf.so.0", "libsmbconf.so.0.0.1"]
                check("buildFS reaper_rm_lib (%s): 0.7.0 and its dangling links go, %s" %
                      (case, "the stand-in stays" if so0 == "file" else "nothing else"),
                      r.returncode == 0 and left == want, (r.stdout, left))
        else:
            print("note: reaper_rm_lib not found or no sh - the removal simulation is not run")
    else:
        print("note: no targets/buildFS next to this tree - the buildFS checks are not run")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
