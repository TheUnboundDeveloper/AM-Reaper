#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The pre-build guard against stale objects in a warm tree (2026-11-14).

WHY THIS EXISTS. A local (warm) tree shipped objects that no longer matched their source, three times over:
  - bcmmcast.ko without the netlink privilege gate of the 2026-11-03 review. ASUS tracks bcmmcast.o in git; a
    `git checkout` of build byproducts on 2026-11-05 put the old committed bytes back with a new mtime, and
    kbuild never relinked it from the freshly compiled bcm_mcast_netlink.o;
  - wpa_supplicant compiled under the previous OpenSSL release (its makefiles do not see the OpenSSL headers);
  - stubby configured while the tree's OpenSSL lacked OSSL_PARAM_BLD_new, so it stayed on the legacy key API.
A clean tree (CI) never shows any of them, and no build step failed. build-scripts/reaper_stale_configure.sh runs
before every local build; this suite runs its two new sections against throwaway git trees.

WHAT IT CHECKS.
  1. a tracked object with a kbuild .cmd beside it that equals the committed copy loses its .cmd under --fix (kbuild
     then rebuilds it); one that differs from the committed copy (built here) keeps it; a tracked object with no
     .cmd (a shipped prebuilt nothing rebuilds) is never touched; --check changes nothing;
  2. wpa_supplicant naming another OpenSSL release than the tree's VERSION.dat is flagged, and --fix removes its
     untracked objects and built programs but no tracked file;
  3. getdns/build configured without OSSL_PARAM_BLD_new on an OpenSSL 3 tree is flagged and removed;
  4. a current tree is clean (exit 0), and the OpenSSL section is inert without RTCONFIG_OPENSSL35.
Exit 0 pass, 1 fail, 77 skip."""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "reaper_stale_configure.sh")
BASH = shutil.which("bash"); GIT = shutil.which("git")
if not BASH or not GIT:
    print("SKIP: needs bash and git"); sys.exit(77)
if not os.path.isfile(SCRIPT):
    print("FAIL: reaper_stale_configure.sh not found"); sys.exit(1)

fails = []
def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name); print("FAIL " + name + ((" :: " + str(detail)[:600]) if detail else ""))

src = open(SCRIPT, encoding="utf-8").read()
check("the guard carries both sections", "REAPER-STALE-OBJ-BEGIN" in src and "REAPER-STALE-OSSL-BEGIN" in src)
check("it judges by content, never by file dates, in the new sections",
      "stat -c" not in src[src.find("REAPER-STALE-OBJ-BEGIN"):src.find("REAPER-STALE-OSSL-END")])

SDK = "release/src-rt-9.99test"
KD = SDK + "/bcmdrivers/opensource/char/mcast/impl1"
WD = SDK + "/bcmdrivers/broadcom/net/wl/impl9/main/components/opensource/router_tools/wpa_supplicant"
RT = "release/src/router"

def w(root, rel, data):
    p = os.path.join(root, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(data if isinstance(data, bytes) else data.encode())

def git(root, *a):
    r = subprocess.run([GIT, "-C", root, "-c", "user.name=t", "-c", "user.email=t@example.invalid"] + list(a),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    if r.returncode != 0:
        print("FAIL: git %s: %s" % (" ".join(a), r.stdout)); sys.exit(1)
    return r.stdout

def tree(ossl_cfg=True, wpa_text="OpenSSL 3.5.8 25 Aug 2026", getdns_new=False):
    root = tempfile.mkdtemp(prefix="stale_")
    git(root, "init", "-q")
    # tracked: three kernel objects, a wpa source file, the OpenSSL version file
    w(root, KD + "/restored.o", b"OLD-COMMITTED\n")
    w(root, KD + "/rebuilt.o", b"OLD-COMMITTED\n")
    w(root, KD + "/shipped.o", b"PREBUILT\n")
    w(root, WD + "/wpa_supplicant/main.c", "int main(void){return 0;}\n")
    w(root, RT + "/openssl-3.5/VERSION.dat", 'MAJOR=3\nMINOR=5\nPATCH=9\nPRE_RELEASE_TAG=\nRELEASE_DATE="29 Sep 2026"\n')
    w(root, RT + "/Makefile", "all:\n")
    git(root, "add", "-A"); git(root, "commit", "-q", "-m", "base")
    # untracked build state
    w(root, KD + "/.restored.o.cmd", "cmd_restored := ld\n")     # kbuild built it, then it was restored from git
    w(root, KD + "/.rebuilt.o.cmd", "cmd_rebuilt := ld\n")
    w(root, KD + "/rebuilt.o", b"BUILT-HERE\n")                   # built here: differs from the committed copy
    w(root, KD + "/part.o", b"x")                                 # an untracked component object
    w(root, KD + "/.part.o.cmd", "cmd_part := gcc\n")
    w(root, RT + "/.config", "RTCONFIG_OPENSSL35=y\n" if ossl_cfg else "# RTCONFIG_OPENSSL35 is not set\n")
    w(root, WD + "/wpa_supplicant/wpa_supplicant", b"\x7fELF....." + wpa_text.encode() + b"\x00more")
    w(root, WD + "/wpa_supplicant/wpa_cli", b"\x7fELF")
    w(root, WD + "/wpa_supplicant/main.o", b"o")
    w(root, WD + "/src/crypto/tls_openssl.o", b"o")
    w(root, RT + "/getdns/build/config.h",
      "#define HAVE_DSA_SET0_KEY 1\n" + ("#define HAVE_OSSL_PARAM_BLD_NEW 1\n" if getdns_new else "/* #undef HAVE_OSSL_PARAM_BLD_NEW */\n"))
    w(root, RT + "/getdns/build/stubby/stubby", b"\x7fELF")
    return root

def run(root, mode):
    r = subprocess.run([BASH, SCRIPT, mode, root], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    return r.returncode, r.stdout

def ex(root, rel):
    return os.path.exists(os.path.join(root, rel))

roots = []
try:
    # ---- a tree with all three faults
    t = tree(); roots.append(t)
    rc, out = run(t, "--check")
    check("--check: the two OpenSSL faults are reported and the exit code says so", rc == 1 and "[STALE] wpa_supplicant" in out
          and "[STALE] getdns (stubby)" in out and "OpenSSL 3.5.8 25 Aug 2026, the tree has OpenSSL 3.5.9 29 Sep 2026" in out, out)
    check("--check: one tracked object equals the committed copy, one was built here", "1 equal the committed copy" in out and "1 built here" in out, out)
    check("--check changes nothing", ex(t, KD + "/.restored.o.cmd") and ex(t, WD + "/wpa_supplicant/main.o") and ex(t, RT + "/getdns/build/config.h"))
    rc, out = run(t, "--fix")
    check("--fix exits 0", rc == 0, out)
    check("--fix: the restored object's .cmd is gone, so kbuild rebuilds it", not ex(t, KD + "/.restored.o.cmd") and ex(t, KD + "/restored.o"), out)
    check("--fix: an object built here (differs from the committed copy) keeps its .cmd", ex(t, KD + "/.rebuilt.o.cmd"))
    check("--fix: untracked component objects and their .cmd are left alone", ex(t, KD + "/part.o") and ex(t, KD + "/.part.o.cmd"))
    check("--fix: a tracked object nothing rebuilds here (no .cmd) is never touched",
          open(os.path.join(t, KD + "/shipped.o"), "rb").read() == b"PREBUILT\n" and "shipped.o" not in git(t, "status", "--porcelain"))
    check("--fix: wpa_supplicant's objects and built programs are removed, its tracked source kept",
          not ex(t, WD + "/wpa_supplicant/main.o") and not ex(t, WD + "/src/crypto/tls_openssl.o")
          and not ex(t, WD + "/wpa_supplicant/wpa_supplicant") and not ex(t, WD + "/wpa_supplicant/wpa_cli")
          and ex(t, WD + "/wpa_supplicant/main.c"), out)
    check("--fix: getdns/build is removed (its make rule configures it again)", not ex(t, RT + "/getdns/build"), out)
    check("--fix: no tracked file was deleted or changed by it (only the object built here differs)",
          git(t, "status", "--porcelain", "--untracked-files=no").split() == ["M", KD + "/rebuilt.o"], git(t, "status", "--porcelain", "--untracked-files=no"))
    rc, out = run(t, "--check")
    check("after --fix a second look finds nothing stale", rc == 0 and "[STALE]" not in out, out)

    # ---- a current tree
    t = tree(wpa_text="OpenSSL 3.5.9 29 Sep 2026", getdns_new=True); roots.append(t)
    rc, out = run(t, "--fix")
    check("a current tree: nothing flagged, wpa_supplicant and getdns untouched",
          rc == 0 and "[STALE]" not in out and ex(t, WD + "/wpa_supplicant/main.o") and ex(t, RT + "/getdns/build/config.h"), out)

    # ---- OpenSSL 3.5 not selected: the section is inert (the kernel-object part still runs)
    t = tree(ossl_cfg=False); roots.append(t)
    rc, out = run(t, "--fix")
    check("without RTCONFIG_OPENSSL35 the OpenSSL section is inert", rc == 0 and "[STALE]" not in out and ex(t, WD + "/wpa_supplicant/main.o")
          and ex(t, RT + "/getdns/build/config.h") and not ex(t, KD + "/.restored.o.cmd"), out)

    # ---- a clean tree (as CI): no .cmd anywhere, nothing built
    t = tempfile.mkdtemp(prefix="stale_"); roots.append(t)
    git(t, "init", "-q"); w(t, KD + "/restored.o", b"x"); w(t, RT + "/Makefile", "all:\n"); git(t, "add", "-A"); git(t, "commit", "-q", "-m", "base")
    rc, out = run(t, "--fix")
    check("a clean tree is a no-op", rc == 0 and "tracked kernel objects" not in out and "[STALE]" not in out, out)
finally:
    for r in roots:
        shutil.rmtree(r, ignore_errors=True)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
