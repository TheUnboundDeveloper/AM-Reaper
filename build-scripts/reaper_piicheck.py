#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 reaper <theunbounddeveloper@outlook.com>
"""Personal-data scan for everything the public repo carries.

WHY THIS EXISTS. Test fixtures, docs and source comments were written from a live
network, and real values (MAC addresses, a routed IPv6 prefix, host names, a DDNS
account) reached the public repo. None of that looks like a secret to a secrets
scanner, and the old check knew two patterns. This one knows the shapes.

TWO KINDS OF RULE.
- deny-list: exact strings that must never appear anywhere, read from --denylist FILE
  and/or the PII_DENYLIST environment variable (one string per line, case-insensitive,
  '#' comments). Applied to EVERY line, including the deleted and context lines of a
  patch - a deleted line is published too. The list itself is private: it lives in a
  repository secret in CI and in a private file locally, never in this repo. A match is
  reported without the value.
- generic detectors: shapes that are almost never legitimate in Reaper-authored text.
  Applied to whole files, but only to the ADDED lines (and message header) of a
  .patch, so vendored upstream content being deleted does not trip them.

Use documentation values in tests and docs: IPv4 192.0.2.0/24, 198.51.100.0/24,
203.0.113.0/24 (RFC 5737); IPv6 2001:db8::/32 (RFC 3849) or 3fff::/20 (RFC 9637);
MAC 00:00:5e:00:53:xx (RFC 7042; 02:00:5e:00:53:xx for a locally administered one);
host names under example.com/org/net. Never paste a value read off a real network.

ALLOWLIST (.github/pii-allowlist.txt, public): a line is either a path or glob (the
generic detectors skip that file - for vendored upstream context only), or
'rule:value' to accept one value everywhere (public infrastructure such as a public
DNS resolver). The deny-list cannot be allowlisted.

Exit 0 clean, 1 findings, 2 usage error.
"""
import argparse, base64, fnmatch, ipaddress, os, re, sys

SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}
SKIP_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.gz', '.tgz',
            '.zip', '.pkgtb', '.bin', '.pdf', '.xz', '.bz2', '.7z', '.so', '.o', '.a')
MAX_BYTES = 32 * 1024 * 1024

PERSONAL_MAIL = r'(?:gmail|googlemail|yahoo|ymail|hotmail|outlook|live|msn|icloud|me|mac|aol|gmx|proton|protonmail|pm|yandex|mail|zoho|fastmail|tutanota)\.[a-z.]{2,6}'
RX_MAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@' + PERSONAL_MAIL + r'\b', re.I)
RX_HOME = re.compile(r'(?:/home/|/Users/|[A-Za-z]:\\\\?Users\\\\?)([A-Za-z0-9._-]+)')
RX_MAC = re.compile(r'(?<![0-9A-Fa-f:-])([0-9A-Fa-f]{2})([:-])((?:[0-9A-Fa-f]{2}\2){4}[0-9A-Fa-f]{2})(?![0-9A-Fa-f:-])')
RX_V4 = re.compile(r'(?<![\w.])((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})(?![\w.])')
RX_V6 = re.compile(r'(?<![\w:])([23][0-9A-Fa-f]{3}:[0-9A-Fa-f:]{2,}[0-9A-Fa-f])(?![\w:])')
RX_HOST = re.compile(r'\b(?:(?:DESKTOP|LAPTOP)-[A-Z0-9]{7}|WIN-[A-Z0-9]{11})\b')
RX_BASIC = re.compile(r'Authorization:\s*Basic\s+([A-Za-z0-9+/]{8,}={0,2})', re.I)
RX_URLCRED = re.compile(r'\b[a-z][a-z0-9+.-]*://([^/\s:@"\'<>]+):([^/\s@"\'<>]+)@[A-Za-z0-9.-]+', re.I)

OK_HOME = {'reaper', 'builder', 'runner', 'user', 'username', 'USER', 'you', 'example', 'name',
           'Public', 'Default', 'All', '<user>', 'xxx', 'me', 'reaper_build', 'runneradmin'}
# In a .patch, generic detectors only read ADDED lines of files Reaper itself writes
# (vendored packages - tor, openvpn, openssh, net-snmp... - carry upstream test data).
RX_OWN = re.compile(r'^release/src/router/(?:rc|httpd|shared|www|others|rom)/'
                    r'|^release/src/router/[^/]*reaper[^/]*/|/[^/]*reaper[^/]*$'
                    r'|^release/src/router/r(?:trafd|mcpd|punctd|dnsmapd|dnshc|watch|meshchan)[^/]*/'
                    r'|^release/src-rt[^/]*/(?:version\.conf|target\.mak)$')
# Well-known public infrastructure (anycast DNS/NTP services) - never personal.
PUBLIC_INFRA = [ipaddress.ip_network(n) for n in (
    '1.1.1.0/24', '1.0.0.0/24', '8.8.8.0/24', '8.8.4.0/24', '9.9.9.0/24', '149.112.112.0/24',
    '208.67.216.0/21', '94.140.14.0/23', '76.76.2.0/24', '76.76.10.0/24', '185.228.168.0/24',
    '185.228.169.0/24', '162.159.200.0/24', '64.6.64.0/24', '64.6.65.0/24', '4.2.2.0/24',
    '45.90.28.0/22', '193.110.81.0/24', '185.253.5.0/24', '66.220.2.74/32', '216.66.0.0/16',
    # public DNS presets the GUI lists (Yandex, DNS.WATCH, Dyn, FreeNom, Level3, Neustar/UltraDNS,
    # SafeDNS, Comodo, Baidu, Alibaba, CIRA Canadian Shield, FDN)
    '77.88.8.0/24', '84.200.69.80/32', '84.200.70.40/32', '216.146.35.35/32', '216.146.36.36/32',
    '37.235.1.174/32', '37.235.1.177/32', '209.244.0.3/32', '209.244.0.4/32', '156.154.70.0/23',
    '195.46.39.0/24', '8.26.56.26/32', '8.20.247.20/32', '180.76.76.76/32', '223.5.5.5/32',
    '223.6.6.6/32', '149.112.121.0/24', '149.112.122.0/24', '89.234.186.112/32',
    '2606:4700::/32', '2001:4860:4860::/48', '2620:fe::/48', '2620:119:35::/48',
    '2620:119:53::/48', '2a10:50c0::/32', '2a0d:2a00::/32', '2001:470:20::/48', '2a07:a8c0::/29',
    '2620:74:1b::/48', '2620:74:1c::/48', '2620:10a:80bb::/48', '2620:10a:80bc::/48',
    '2606:1a40::/32', '2a00:5884::/32')]
RX_SVG = re.compile(r'<path\b|\bd="M|viewBox=')


def placeholder_mac(v):
    o = v.split(':')
    if all(x[0] == x[1] for x in o):                      # aa:bb:cc:dd:ee:ff, 11:22:..., 00:...
        return True
    s = ''.join(o)
    return s in ('001122334455', '112233445566', '123456789abc', '0123456789ab', '010203040506',
                 'abcdef123456', '123456abcdef', 'fedcba987654') or s.startswith('deadbeef') \
        or s.startswith('cafebabe') or s.startswith('020000') or s.startswith('aabbcc') \
        or s.startswith('0000000000') or '11223344' in s or s.startswith('02005e0053')
OK_MAIL = {'theunbounddeveloper@outlook.com'}
PLACEHOLDER_PW = {'pass', 'password', 'secret', 'hunter2', 'x', 'xxx', 'changeme', 'example',
                  'examplekey1', 'admin', 'pw', 'passwd', 'token', 'key', 'apikey', 'p', 'test'}
DOC4 = [ipaddress.ip_network(n) for n in ('192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24')]
DOC6 = [ipaddress.ip_network(n) for n in ('2001:db8::/32', '3fff::/20')]


def load_allow(path):
    paths, values = [], set()
    if path and os.path.isfile(path):
        for ln in open(path, encoding='utf-8', errors='replace'):
            ln = ln.strip()
            if not ln or ln.startswith('#'):
                continue
            m = re.match(r'^(mail|home|mac|ipv4|ipv6|host|basic|urlcred):(.+)$', ln)
            if m:
                values.add((m.group(1), m.group(2).strip().lower()))
            else:
                paths.append(ln)
    return paths, values


def load_deny(path, env):
    out = []
    srcs = []
    if path and os.path.isfile(path):
        srcs.append(open(path, encoding='utf-8', errors='replace').read())
    if env and os.environ.get(env):
        srcs.append(os.environ[env])
    for s in srcs:
        for ln in s.splitlines():
            ln = ln.strip()
            if ln and not ln.startswith('#') and len(ln) >= 4:
                out.append(ln.lower())
    return sorted(set(out))


def mask(v):
    v = str(v)
    return '%s...(%d chars)' % (v[:2], len(v)) if len(v) > 4 else '***'


def generic(line, allow_values):
    """Yield (rule, value) for generic detector hits on one line."""
    for m in RX_MAIL.finditer(line):
        v = m.group(0).lower()
        if v not in OK_MAIL and ('mail', v) not in allow_values:
            yield 'mail', v
    for m in RX_HOME.finditer(line):
        u = m.group(1).rstrip('._-')
        if u and u not in OK_HOME and not u.startswith('$') and ('home', u.lower()) not in allow_values:
            yield 'home', u
    if RX_SVG.search(line):          # SVG path data is full of dotted number runs
        line = RX_SVG.split(line)[0]
    for m in RX_MAC.finditer(line):
        v = (m.group(1) + m.group(2) + m.group(3)).lower().replace('-', ':')
        first = int(v[:2], 16)
        if v.startswith(('00:00:5e:00:53:', '02:00:5e:00:53:')) or v in ('00:00:00:00:00:00', 'ff:ff:ff:ff:ff:ff') \
           or first & 1 or placeholder_mac(v) or ('mac', v) in allow_values:
            continue
        yield 'mac', v
    for m in RX_V4.finditer(line):
        v = m.group(1)
        try:
            ip = ipaddress.ip_address(v)
        except ValueError:
            continue
        if not ip.is_global or ip.is_multicast or any(ip in n for n in DOC4) \
           or any(ip in n for n in PUBLIC_INFRA if n.version == 4) or ('ipv4', v) in allow_values:
            continue
        yield 'ipv4', v
    for m in RX_V6.finditer(line):
        v = m.group(1)
        try:
            ip = ipaddress.ip_address(v)
        except ValueError:
            continue
        if not ip.is_global or any(ip in n for n in DOC6) or any(ip in n for n in PUBLIC_INFRA if n.version == 6) \
           or ('ipv6', str(ip)) in allow_values:
            continue
        yield 'ipv6', str(ip)
    for m in RX_HOST.finditer(line):
        v = m.group(0)
        if 'EXAMPL' in v or ('host', v.lower()) in allow_values:
            continue
        yield 'host', v
    for m in RX_BASIC.finditer(line):
        try:
            dec = base64.b64decode(m.group(1) + '==', validate=False).decode('utf-8', 'strict')
        except Exception:
            continue
        if ':' in dec:
            pw = dec.split(':', 1)[1].lower()
            if pw not in PLACEHOLDER_PW and ('basic', m.group(1).lower()) not in allow_values:
                yield 'basic', m.group(1)
    for m in RX_URLCRED.finditer(line):
        pw = m.group(2).lower()
        if pw.startswith('$') or pw.startswith('%') or pw.startswith('{') or pw in PLACEHOLDER_PW \
           or ('urlcred', pw) in allow_values:
            continue
        yield 'urlcred', m.group(2)


def iter_files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for dp, dn, fn in os.walk(p):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for f in fn:
                yield os.path.join(dp, f)


def scan(paths, deny, allow_paths, allow_values, root, max_details, generic_patches_full=False, show_values=False):
    findings = []
    nfiles = 0
    for path in iter_files(paths):
        rel = os.path.relpath(path, root).replace(os.sep, '/')
        if rel.lower().endswith(SKIP_EXT):
            continue
        try:
            if os.path.getsize(path) > MAX_BYTES:
                continue
            raw = open(path, 'rb').read()
        except OSError:
            continue
        if b'\0' in raw[:8192]:
            continue
        nfiles += 1
        text = raw.decode('utf-8', 'replace')
        is_patch = rel.endswith('.patch') or rel.endswith('.diff')
        gen_ok = not any(fnmatch.fnmatch(rel, g) for g in allow_paths)
        in_header = True
        own = True
        for i, line in enumerate(text.split('\n'), 1):
            if deny:
                ll = line.lower()
                for d in deny:
                    if d in ll:
                        findings.append(('DENY', rel, i, 'deny-list entry #%d' % (deny.index(d) + 1)))
            if not gen_ok:
                continue
            if is_patch and not generic_patches_full:
                if line.startswith('diff --git'):
                    in_header = False
                    m = re.search(r' b/(\S+)', line)
                    own = bool(m and RX_OWN.search(m.group(1)))
                    continue
                if not in_header and (not own or not (line.startswith('+') and not line.startswith('+++'))):
                    continue
            for rule, v in generic(line, allow_values):
                findings.append((rule, rel, i, v if show_values else mask(v)))
    return nfiles, findings


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--root', default='.', help='paths are reported relative to this')
    ap.add_argument('--allowlist', default='.github/pii-allowlist.txt')
    ap.add_argument('--denylist', help='private file of exact strings (never committed)')
    ap.add_argument('--denylist-env', default='PII_DENYLIST')
    ap.add_argument('--require-denylist', action='store_true',
                    help='fail if no deny-list entries were loaded (CI on the main repo)')
    ap.add_argument('--max-details', type=int, default=40)
    ap.add_argument('--show-values', action='store_true',
                    help='print generic-detector values unmasked (local review only; never in CI)')
    a = ap.parse_args()
    deny = load_deny(a.denylist, a.denylist_env)
    if a.require_denylist and not deny:
        print('::error::PII deny-list is empty - set the PII_DENYLIST repository secret')
        return 2
    allow_paths, allow_values = load_allow(a.allowlist)
    nfiles, f = scan(a.paths, deny, allow_paths, allow_values, a.root, a.max_details,
                     show_values=a.show_values)
    dn = sum(1 for x in f if x[0] == 'DENY')
    print('reaper_piicheck: %d file(s), %d deny-list entr%s, %d allowlist path(s), %d allowlisted value(s)'
          % (nfiles, len(deny), 'y' if len(deny) == 1 else 'ies', len(allow_paths), len(allow_values)))
    if not f:
        print('OK: no personal data found')
        return 0
    by = {}
    for r, p, i, v in f:
        by.setdefault(r, []).append((p, i, v))
    for r in sorted(by, key=lambda k: (k != 'DENY', k)):
        print('%s: %d hit(s)' % (r, len(by[r])))
        for p, i, v in by[r][:a.max_details]:
            print('  %s:%d  %s' % (p, i, v))
        if len(by[r]) > a.max_details:
            print('  ... %d more' % (len(by[r]) - a.max_details))
    print('FAIL: %d finding(s) (%d deny-list). Replace real values with documentation values; '
          'allowlist only public infrastructure or vendored upstream files.' % (len(f), dn))
    return 1


if __name__ == '__main__':
    sys.exit(main())
