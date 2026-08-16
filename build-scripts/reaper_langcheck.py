#!/usr/bin/env python3
"""reaper_langcheck.py <staged-www-dir>
Gate check (reaper-ui standing rule 29): in Reaper-owned www files, a dict token
embedded in a JS string must not be breakable by any language's translation.
  backtick ctx : translation must not contain ` or ${
  dq ctx       : translation must not contain an unescaped "
  sq ctx       : translation must not contain an unescaped '  (rule 29 says these
                 contexts should not exist at all; any hit is a violation)
Works on the STAGED fs (numeric tokens, line-indexed dicts). Exit 1 on any hit.
"""
import re, sys, pathlib

W = pathlib.Path(sys.argv[1])
OUR = ['reaper_shell.asp', 'Main_ReaperDash.asp', 'Reaper_Traffic.asp', 'Reaper_QoS.asp',
       'Reaper_GK.asp', 'Reaper_Warden.asp', 'Reaper_Advisor.asp', 'Reaper_Diag.asp',
       'Reaper_Wireless.asp', 'Reaper_FirstBoot.asp', 'Reaper_Devices.asp',
       'Reaper_Storage.asp', 'Reaper_WiFiPro.asp', 'Reaper_QoSDiag.asp',
       'Reaper_Conn.asp',
       'Reaper_USB.asp', 'Reaper_Analytics.asp', 'Reaper_Firmware.asp',
       # Added 2026-08-15. Reaper_Firewall.asp shipped in v2.4.1 with 11 tabs and
       # 158 RFW_* tokens and was never listed here, so the largest and newest
       # Reaper page was outside the i18n gate entirely - neither the rule-29
       # breakage scan nor the density warning ever looked at it.
       'Reaper_Firewall.asp',
       # Added 2026-08-16 with the page itself - caught by this file's own
       # LANGCOVERAGE assertion on the very first run, which is what it is for.
       'Reaper_About.asp']

# Dropped at the same time: 'Reaper_WiFiAccel.asp'. The accelerator page is
# shelved and the file is not in the tree, so the entry only ever hit the
# `if not p.exists(): continue` line. A list that silently skips its own
# entries cannot be read as a statement of coverage - which is exactly how the
# Firewall omission went unnoticed. See the coverage assertion below.

BT = re.compile(r'`([^`]*)`', re.S)
SQ = re.compile(r"'((?:[^'\\\n]|\\[^\n])*)'")
DQ = re.compile(r'"((?:[^"\\\n]|\\[^\n])*)"')
TOK = re.compile(r'<#(\d+)#>')

dicts = {}
for d in sorted(W.glob('*.dict')):
    dicts[d.stem] = d.read_text('utf-8', errors='replace').split('\n')

def val(lang, n):
    lines = dicts[lang]
    return lines[n] if n < len(lines) else ''

def unescaped(s, ch):
    i = 0
    while True:
        i = s.find(ch, i)
        if i < 0: return False
        if i == 0 or s[i-1] != '\\': return True
        i += 1

bad = 0
for f in OUR:
    p = W/f
    if not p.exists(): continue
    t = p.read_text('utf-8', errors='replace')
    # 1) backtick spans first (then strip them, so sq/dq scans don't mispair)
    for m in BT.finditer(t):
        for n in map(int, TOK.findall(m.group(1))):
            for L in dicts:
                v = val(L, n)
                if '`' in v or '${' in v:
                    print(f'LANGBREAK bt {f} <#{n}#> {L}: {v[:70]}'); bad += 1
    t2 = BT.sub('``', t)
    for rx, ctx, ch in ((SQ, 'sq', "'"), (DQ, 'dq', '"')):
        for m in rx.finditer(t2):
            for n in map(int, TOK.findall(m.group(1))):
                for L in dicts:
                    if unescaped(val(L, n), ch):
                        print(f'LANGBREAK {ctx} {f} <#{n}#> {L}: {val(L, n)[:70]}'); bad += 1

# density guard (added after v2.0.8 i18n pass): the breakage scan above cannot
# catch a page that ships with NO tokens at all (fully hardcoded English, like
# Reaper_Conn/Reaper_QoSDiag did before tokenization). An OUR page is by
# definition meant to be localized, so a near-zero token count means missing
# i18n. Non-fatal WARN so it never blocks a release, but it surfaces the gap.
DENS = re.compile(r'<#[A-Za-z0-9_]+#>')
LOW = 6
for f in OUR:
    p = W/f
    if not p.exists(): continue
    ntok = len(DENS.findall(p.read_text('utf-8', errors='replace')))
    if ntok < LOW:
        print(f'LANGDENSITY WARN {f}: only {ntok} dict tokens - likely hardcoded English (rule 24)')

# COVERAGE ASSERTION (added 2026-08-15). Every check above iterates OUR and
# skips anything absent, so a Reaper page that was never added to the list is
# indistinguishable from one that passed. Reaper_Firewall.asp sat outside the
# gate from v2.4.1 until this was noticed by a manual audit - eleven tabs and
# 158 tokens that nothing checked.
#
# Fails rather than warns: the fix is one line in OUR, the message says which
# file, and a warning here would be as easy to walk past as the original gap.
staged = sorted(p.name for p in W.glob('*.asp')
                if re.match(r'(Reaper_|Main_Reaper|reaper_shell)', p.name))
unlisted = [f for f in staged if f not in OUR]
for f in unlisted:
    print(f'LANGCOVERAGE {f}: Reaper page is not in OUR[] - nothing checked it. Add it.')
    bad += 1
stale = [f for f in OUR if not (W/f).exists()]
for f in stale:
    print(f'LANGCOVERAGE WARN {f}: listed in OUR[] but not staged - stale entry, remove it')

print(f'reaper_langcheck: {bad} breakers, {len(staged)} Reaper pages checked')
sys.exit(1 if bad else 0)
