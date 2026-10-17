#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The personal-data scan must catch real-looking values, pass documentation values, and never
print a deny-list entry.

WHY THIS EXISTS. Test fixtures and docs were once written from a live network and real values
reached the public repo; build-scripts/reaper_piicheck.py is the gate that stops that. A gate
nobody tests drifts into passing everything, so this pins both directions: every detector fires
on a real-looking value, none fires on the documentation ranges, the deny-list works from the
environment the way CI feeds it, and its values never reach the output.

Exit 0 pass, 1 fail.
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'reaper_piicheck.py')
fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))


def run(files, env_deny=None, extra=()):
    d = tempfile.mkdtemp()
    for name, body in files.items():
        p = os.path.join(d, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(body)
    allow = os.path.join(d, 'allow.txt')
    open(allow, 'w').write('ipv4:1.2.3.4\n')
    env = dict(os.environ)
    env.pop('PII_DENYLIST', None)
    if env_deny is not None:
        env['PII_DENYLIST'] = env_deny
    r = subprocess.run([sys.executable, TOOL, '--root', d, '--allowlist', allow] + list(extra) + [d],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


# 1. documentation values and public infrastructure pass
rc, out = run({'ok.txt': 'mac 00:00:5e:00:53:01 la 02:00:5e:00:53:27 v4 192.0.2.10 198.51.100.7 203.0.113.9\n'
                         'v6 2001:db8:1::5 3fff::1 dns 1.1.1.1 2606:4700:4700::1111 lan 192.168.50.1 fd00::1\n'
                         'mac placeholder aa:bb:cc:dd:ee:01 host DESKTOP-EXAMPL1 home /home/reaper/x\n'
                         'Authorization: Basic ZXhhbXBsZXVzZXI6cGFzcw== url https://user:pass@example.com/\n'
                         'allowlisted 1.2.3.4 multicast 239.255.255.250 33:33:00:00:00:01\n'})
check("documentation values, public infra, placeholders and allowlist entries pass", rc == 0, out)

# 2. every generic detector fires on a real-looking value (one file per rule)
cases = {
    'mac': 'neighbour 3c:22:fb:12:34:56\n',
    'ipv4': 'peer 84.17.40.12\n',
    'ipv6': 'prefix 2a02:1234:5678::9\n',
    'host': 'client DESKTOP-ABC1234\n',
    'mail': 'contact someone.real@gmail.com\n',
    'home': 'path C:\\Users\\someone\\project\n',
    'basic': 'Authorization: Basic cmVhbHVzZXI6UzNjcmV0IVZhbHVl\n',
    'urlcred': 'url https://realuser:Sup3rS3cret@ddns.example.net/update\n',
}
for rule, body in cases.items():
    rc, out = run({'%s.txt' % rule: body})
    check("generic detector '%s' fires on a real-looking value" % rule, rc == 1 and ('%s:' % rule) in out, out)

# 3. a patch: generic rules read only ADDED lines of Reaper-owned files
patch = ('From: x\nSubject: y\n\n'
         'diff --git a/release/src/router/tor/src/test/x.c b/release/src/router/tor/src/test/x.c\n'
         '+ vendored 84.17.40.12 3c:22:fb:12:34:56\n'
         'diff --git a/release/src/router/rc/reaper_x.c b/release/src/router/rc/reaper_x.c\n'
         '- removed 84.17.40.13\n'
         ' context 84.17.40.14\n')
rc, out = run({'0001-x.patch': patch})
check("patch: vendored adds, removed and context lines do not trip generic rules", rc == 0, out)
rc, out = run({'0002-x.patch': patch + '+ added 84.17.40.15\n'})
check("patch: an added line in a Reaper-owned file trips them", rc == 1 and 'ipv4:' in out, out)

# 4. the deny-list: from the environment, on EVERY line (removed lines too), never printed
secret = 'zq-owner-token-77'
rc, out = run({'0003-x.patch': patch + '- old ' + secret + '\n'}, env_deny='# comment\n' + secret + '\n')
check("deny-list from PII_DENYLIST catches a removed patch line", rc == 1 and 'DENY:' in out, out)
check("deny-list value never appears in the output", secret not in out and secret[:6] not in out, out)
rc, out = run({'a.txt': 'nothing here\n'}, env_deny='', extra=['--require-denylist'])
check("--require-denylist fails when the list is empty", rc == 2, out)

# 5. private-key material: any added line of any patch (vendored too), and any plain file;
#    the header is assembled here so this test file never holds one itself
pem = '-----BEGIN ' + 'RSA PRIVATE KEY-----'
vend = 'diff --git a/release/src/router/pkg/tests/k.pem b/release/src/router/pkg/tests/k.pem\n'
rc, out = run({'0004-x.patch': patch + vend + '+' + pem + '\n+MIIEowIBAAKCAQEA\n'})
check("patch: a private key added under a vendored path trips 'pemkey'", rc == 1 and 'pemkey:' in out, out)
rc, out = run({'0005-x.patch': patch + vend + '-' + pem + '\n-MIIEowIBAAKCAQEA\n'})
check("patch: a private key being removed does not", rc == 0, out)
rc, out = run({'0006-x.patch': patch + 'diff --git a/release/src/router/d/k.c b/release/src/router/d/k.c\n'
                                '+\tif (!strcmp(buffer, "' + pem + '\\n"))\n'})
check("patch: source that merely quotes the header does not", rc == 0, out)
rc, out = run({'k.txt': pem + '\nMIIEowIBAAKCAQEA\n'})
check("a plain file holding a private key trips 'pemkey'", rc == 1 and 'pemkey:' in out, out)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("\nall checks passed: real-looking personal data is caught, documentation values pass, "
      "the deny-list reads every line and stays out of the log")
