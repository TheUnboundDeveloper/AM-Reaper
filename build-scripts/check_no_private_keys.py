#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 reaper <theunbounddeveloper@outlook.com>
"""No private key may ship in the image.

WHY THIS EXISTS. Vendored source trees carry key files, and a model profile can copy
one into the read-only rootfs, where every unit of that model then shares it. No
Reaper image carries one today; this keeps it that way on every build and every port.

It walks the staged rootfs and fails on any regular file holding private-key material:
a PEM private-key header followed by a base64 body and an END line (RSA, EC, DSA,
OpenSSH, PKCS#8, encrypted, PGP), or a PuTTY key file. A binary that merely quotes the
header text (a key converter, a PEM parser) has no body after it and does not match.

Some libraries compile a PUBLIC test key in for their own power-up self-test (GnuTLS,
lib/crypto-selftests-pk.c). Those pass only through --allowlist FILE, one line per
block: the sha256 of the exact PEM block, the path glob it may live in, a comment.
A different block in that file, or the same block elsewhere, still fails.

Usage: check_no_private_keys.py [--allowlist FILE] DIR [DIR...]
Exit 0 clean, 1 findings (paths and header types only, never contents), 2 usage error.
"""
import argparse, fnmatch, hashlib, os, re, sys

RX_PEM = re.compile(rb'-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----[ \t]*\r?\n'
                    rb'(?:[A-Za-z0-9+/=,:. \t-]{1,120}\r?\n){2,}'
                    rb'-----END [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----')
RX_PUTTY = re.compile(rb'^PuTTY-User-Key-File-\d', re.M)
MAX_BYTES = 64 * 1024 * 1024


def load_allow(path):
    out = []
    if not path:
        return out
    if not os.path.isfile(path):
        print('check_no_private_keys: allowlist not found: %s' % path)
        return None
    for ln in open(path, encoding='utf-8', errors='replace'):
        ln = ln.split('#', 1)[0].strip()
        parts = ln.split()
        if len(parts) >= 2 and re.fullmatch(r'[0-9a-f]{64}', parts[0]):
            out.append((parts[0], parts[1]))
    return out


def scan(dirs, allow):
    hits, nfiles, nallowed = [], 0, 0
    for d in dirs:
        if not os.path.isdir(d):
            print('check_no_private_keys: not a directory: %s' % d)
            return None, None, None
        for dp, dn, fn in os.walk(d):
            for f in fn:
                p = os.path.join(dp, f)
                if os.path.islink(p) or not os.path.isfile(p):
                    continue
                try:
                    if os.path.getsize(p) > MAX_BYTES:
                        continue
                    data = open(p, 'rb').read()
                except OSError:
                    continue
                nfiles += 1
                rel = os.path.relpath(p, d).replace(os.sep, '/')
                bad = []
                for m in RX_PEM.finditer(data):
                    blk = m.group(0)
                    h = hashlib.sha256(blk).hexdigest()
                    if any(h == s and fnmatch.fnmatch(rel, g) for s, g in allow):
                        nallowed += 1
                        continue
                    bad.append(blk.split(b'\n', 1)[0].decode('ascii', 'replace').strip().strip('-'))
                if bad:
                    hits.append((rel, '%s%s' % (bad[0], ' +%d more block(s)' % (len(bad) - 1) if len(bad) > 1 else '')))
                elif RX_PUTTY.search(data):
                    hits.append((rel, 'PuTTY key file'))
    return nfiles, hits, nallowed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dirs', nargs='+')
    ap.add_argument('--allowlist', help='sha256 + path glob per allowed block (public self-test vectors only)')
    a = ap.parse_args()
    allow = load_allow(a.allowlist)
    if allow is None:
        return 2
    nfiles, hits, nallowed = scan(a.dirs, allow)
    if nfiles is None:
        return 2
    if hits:
        for p, what in hits:
            print('  %s  (%s)' % (p, what))
        print('FAIL: %d file(s) carry private-key material' % len(hits))
        return 1
    print('OK: no private-key material in %d file(s)%s' % (nfiles, ' (%d allowlisted self-test block(s))' % nallowed if nallowed else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
