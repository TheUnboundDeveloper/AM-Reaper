#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The image key gate must catch a key file and ignore a program that merely quotes the header.

WHY THIS EXISTS. build-scripts/check_no_private_keys.py is the reaper_verify check that stops
a key file from shipping in the rootfs. Key converters and PEM parsers carry the header string
in their binaries, so a naive grep would fail every image; this pins that the gate needs a
body, follows no symlink, and reports paths only.

Exit 0 pass, 1 fail.
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'check_no_private_keys.py')
fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))


def run(files, links=(), allow=None):
    d = tempfile.mkdtemp()
    for name, body in files.items():
        p = os.path.join(d, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(body)
    for name, target in links:
        try:
            os.symlink(target, os.path.join(d, name))
        except (OSError, NotImplementedError):
            return None, 'nosymlink'
    extra = []
    if allow is not None:
        ap = os.path.join(d, 'allow.txt')
        open(ap, 'w').write('# test\n' + ''.join('%s  %s  # self-test vector\n' % e for e in allow))
        extra = ['--allowlist', ap]
    r = subprocess.run([sys.executable, TOOL] + extra + [d], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


# the header is assembled at run time so this test file never holds one itself
HDR = b'-----BEGIN ' + b'RSA PRIVATE KEY-----\n'
BODY = b''.join(b'MIIEowIBAAKCAQEA' + bytes([65 + i % 26]) * 48 + b'\n' for i in range(6))
END = b'-----END ' + b'RSA PRIVATE KEY-----\n'
KEY = HDR + BODY + END
OSSH = b'-----BEGIN ' + b'OPENSSH PRIVATE KEY-----\n' + BODY + b'-----END ' + b'OPENSSH PRIVATE KEY-----\n'

rc, out = run({'usr/sbin/dropbearconvert': b'\x7fELF\x00\x00' + HDR.rstrip(b'\n') + b'\x00Short input\x00' + END + b'\x00',
               'usr/lib/libcrypto.so.3': b'\x7fELF\x00PRIVATE KEY\x00-----BEGIN \x00-----END \x00',
               'rom/etc/ssl/cert.pem': b'-----BEGIN CERTIFICATE-----\nMIIBszCCAVmgAwIBAgI=\n-----END CERTIFICATE-----\n'})
check("header strings inside binaries and a certificate pass", rc == 0, out)
rc, out = run({'rom/cakey.pem': KEY})
check("a PEM private key in the rootfs fails", rc == 1 and 'rom/cakey.pem' in out, out)
check("the key body is never printed", rc == 1 and BODY[:16].decode() not in out, out)
rc, out = run({'rom/etc/bluetooth/private.pem': OSSH})
check("an OpenSSH-format key fails", rc == 1 and 'bluetooth' in out, out)
rc, out = run({'etc/k.ppk': b'PuTTY-User-Key-File-3: ssh-ed25519\nEncryption: none\n'})
check("a PuTTY key file fails", rc == 1, out)
rc, out = run({'rom/readme.txt': b'keys are generated at first boot\n'}, links=(('rom/link.pem', '/nonexistent/key.pem'),))
if rc is None:
    print("skip symlink case (no symlink support here)")
else:
    check("a dangling symlink is skipped", rc == 0, out)

# a library's compiled-in self-test vector: allowed by exact block hash AND path, nothing looser
import hashlib
blk = KEY[:-1]                                   # the regex match ends at the END line, no trailing newline
h = hashlib.sha256(blk).hexdigest()
lib = b'\x7fELF\x00\x00' + KEY + b'\x00more\x00'
rc, out = run({'usr/lib/libgnutls.so.30': lib}, allow=[(h, 'usr/lib/libgnutls.so*')])
check("an allowlisted self-test block in its library passes", rc == 0 and 'allowlisted' in out, out)
rc, out = run({'usr/lib/libgnutls.so.30': lib + OSSH}, allow=[(h, 'usr/lib/libgnutls.so*')])
check("a second, different block in the same library still fails", rc == 1, out)
rc, out = run({'rom/cakey.pem': KEY}, allow=[(h, 'usr/lib/libgnutls.so*')])
check("the allowlisted block outside its path still fails", rc == 1, out)
rc, out = run({'rom/x.txt': b'ok\n'}, allow=[])
check("an allowlist with no entries changes nothing", rc == 0, out)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("\nall checks passed: key files are caught, header strings in binaries are not")
