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
       'Reaper_Conn.asp', 'Reaper_WiFiAccel.asp',
       'Reaper_USB.asp', 'Reaper_Analytics.asp', 'Reaper_Firmware.asp']

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

print(f'reaper_langcheck: {bad} breakers')
sys.exit(1 if bad else 0)
