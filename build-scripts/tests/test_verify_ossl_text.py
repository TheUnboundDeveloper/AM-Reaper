#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reaper_verify: every staged program names the OpenSSL release the image ships (2026-11-14).

WHY THIS EXISTS. Local images carried a wpa_supplicant that said "OpenSSL 3.5.8" for six weeks after the tree moved
to 3.5.9: it had been compiled under the old headers and nothing recompiled it (its makefiles do not depend on
them). A clean CI tree never shows it and no existing check looked. Section 22b of reaper_verify.sh compares the
"OpenSSL 3.x.y <date>" text of every staged file with libcrypto.so.3's.

WHAT IT DOES. Lifts the REAPER-OSSL-TEXT block out of reaper_verify.sh and runs it under bash against throwaway
staged trees: all agree = PASS; a program this tree compiles naming another release = FAIL (named); an unknown file
naming another release = WARN; no libcrypto.so.3 = silent; a libcrypto without the text = WARN.
Exit 0 pass, 1 fail, 77 skip."""
import os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFY = os.path.join(HERE, "..", "reaper_verify.sh")
BASH = shutil.which("bash")
if not BASH:
    print("SKIP: needs bash"); sys.exit(77)
src = open(VERIFY, encoding="utf-8").read()
m = re.search(r"# REAPER-OSSL-TEXT-BEGIN\n(.*?)# REAPER-OSSL-TEXT-END\n", src, re.S)
if not m:
    print("FAIL: the REAPER-OSSL-TEXT block is not in reaper_verify.sh"); sys.exit(1)

fails = []
def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name); print("FAIL " + name + ((" :: " + str(detail)[:500]) if detail else ""))

PRE = 'pass() { echo "PASS|$1|$2"; }\nfail() { echo "FAIL|$1|$2"; }\nwarn() { echo "WARN|$1|$2"; }\nFS="$1"\n'
NEW = b"OpenSSL 3.5.9 29 Sep 2026"; OLD = b"OpenSSL 3.5.8 25 Aug 2026"

def run(files):
    fs = tempfile.mkdtemp(prefix="ossl_")
    try:
        for rel, data in files.items():
            p = os.path.join(fs, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(b"\x7fELF\x00\x01" + data + b"\x00tail")
        for d in ("bin", "sbin", "usr/bin", "usr/sbin", "usr/lib", "lib"):
            os.makedirs(os.path.join(fs, d), exist_ok=True)
        sp = os.path.join(fs, "sec.sh"); open(sp, "w", newline="\n").write(PRE + m.group(1))
        r = subprocess.run([BASH, sp, fs], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        return r.stdout.strip()
    finally:
        shutil.rmtree(fs, ignore_errors=True)

o = run({"usr/lib/libcrypto.so.3": NEW, "usr/sbin/wpa_supplicant-2.7": NEW, "usr/sbin/Tor": NEW, "usr/sbin/openssl": NEW, "usr/sbin/httpd": b"no text"})
check("all agree: PASS, counting the files that carry the text", o.startswith("PASS|ossl-version-text|4 staged file(s)") and "OpenSSL 3.5.9 29 Sep 2026" in o, o)
o = run({"usr/lib/libcrypto.so.3": NEW, "usr/sbin/wpa_supplicant-2.7": OLD, "usr/sbin/Tor": NEW})
check("wpa_supplicant compiled under the previous release: FAIL, the file and its text named",
      o.startswith("FAIL|ossl-version-text|") and "usr/sbin/wpa_supplicant-2.7(OpenSSL 3.5.8 25 Aug 2026)" in o and "Tor" not in o, o)
o = run({"usr/lib/libcrypto.so.3": NEW, "usr/sbin/vendor_daemon": b"OpenSSL 3.0.2 15 Mar 2022"})
check("an unknown (closed) file naming another release: WARN, not FAIL",
      o.startswith("WARN|ossl-version-text|") and "usr/sbin/vendor_daemon(OpenSSL 3.0.2 15 Mar 2022)" in o, o)
o = run({"usr/lib/libcrypto.so.3": NEW, "usr/sbin/vendor_daemon": b"OpenSSL 3.0.2 15 Mar 2022", "usr/sbin/stubby": OLD})
check("a known program wins over an unknown one: FAIL", o.startswith("FAIL|ossl-version-text|") and "usr/sbin/stubby(" in o, o)
o = run({"usr/lib/libcrypto.so.3": NEW, "usr/sbin/legacy_tool": b"OpenSSL 1.1.1w  11 Sep 2023"})
check("an OpenSSL 1.1 text is not this check's business (check 22 owns the 1.1 consumers)", o.startswith("PASS|ossl-version-text|1 staged file(s)"), o)
o = run({"usr/sbin/httpd": b"x"})
check("an image without libcrypto.so.3: nothing said", o == "", o)
o = run({"usr/lib/libcrypto.so.3": b"stripped of its text"})
check("a libcrypto.so.3 without the text: WARN", o.startswith("WARN|ossl-version-text|libcrypto.so.3 carries no release text"), o)
check("the block sits between check 22 and check 23",
      src.find("# ---- 22. who may still link") < src.find("# REAPER-OSSL-TEXT-BEGIN") < src.find("# ---- 23. the OpenVPN PKI chain"))

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
