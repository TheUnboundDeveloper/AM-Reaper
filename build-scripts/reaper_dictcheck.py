#!/usr/bin/env python3
"""reaper_dictcheck.py <staged-www>

reaper_verify gate "dict-tokens" (REAPER-CUT8-DICT, 2026-11-27). On the STAGED www:
  1. the language packs are lockstep (every *.dict except temp.dict has the same line count) - httpd reads the
     renumbered 102.8 packs by line position, so one pack off by a line shows every later string in the wrong place;
  2. every dictionary token <#...#> in a shipped page, script or stylesheet resolves to a non-empty string in EVERY
     pack (a page shows the viewer's language): named form (102.10: KEY=text lines) - the key is in the pack with
     text; numbered form (102.8: text-only lines) - the number is a line of the pack and that line is not empty.
A token that resolves to nothing prints nothing where the page expected a label. This is what makes the install-time
dictionary prune (router/tools/reaper_dict_prune.py) safe to grow, and it catches a page naming a key no pack has.
KNOWN lists the gaps the stock files already had before Reaper pruned anything (upstream ships the page, not the keys).
Exit 0 pass, 1 fail, 2 usage.
"""
import os, re, sys

TOK = re.compile(rb'<#([A-Za-z0-9_]+)#>')
KV = re.compile(rb'^[A-Za-z][A-Za-z0-9_]*=')
BOM = b'\xef\xbb\xbf'
EXT = ('.asp', '.htm', '.html', '.js', '.css', '.json', '.xml')
# (file relative to www, key regex): stock gaps present before any Reaper prune (102.10 packs lack the AiBoard EULA)
KNOWN = [('js/asus_policy.js', re.compile(r'^ASUS_Aiboard_EULA_'))]


def main(argv):
    if len(argv) != 2 or not os.path.isdir(argv[1]):
        sys.stderr.write('usage: reaper_dictcheck.py <staged-www>\n')
        return 2
    www = argv[1]
    packs = sorted(f for f in os.listdir(www) if f.endswith('.dict') and f != 'temp.dict')
    if 'EN.dict' not in packs:
        print('FAIL: no EN.dict in %s' % www)
        return 1
    counts = {p: open(os.path.join(www, p), 'rb').read().count(b'\n') for p in packs}
    bad = []
    if len(set(counts.values())) != 1:
        bad.append('packs not lockstep: ' + ' '.join('%s=%d' % kv for kv in sorted(counts.items())))
    lines = open(os.path.join(www, 'EN.dict'), 'rb').read().split(b'\n')
    nonempty = [l for l in lines if l.strip()]
    named = sum(1 for l in nonempty if KV.match(l[3:] if l.startswith(BOM) else l)) > 0.9 * len(nonempty)
    # every pack, not only EN: a page shows the viewer's language, so a label must have text in all 25
    res = {}
    for pk in packs:
        pl = open(os.path.join(www, pk), 'rb').read().split(b'\n')
        if named:
            text = {}
            for l in pl:
                l = l[3:] if l.startswith(BOM) else l
                if b'=' in l:
                    k, v = l.split(b'=', 1)
                    text[k.decode('utf-8', 'replace')] = v.strip()
            res[pk] = text
        else:
            res[pk] = pl
    def has_text(pk, m):
        if named:
            return bool(res[pk].get(m))
        pl = res[pk]
        return m.isdigit() and int(m) < len(pl) and bool(pl[int(m)].lstrip(BOM).strip())
    seen = set()
    nfile = known = 0
    for root, _, files in os.walk(www):
        for f in files:
            p = os.path.join(root, f)
            if not f.endswith(EXT) or os.path.islink(p) or not os.path.isfile(p):
                continue
            rel = os.path.relpath(p, www).replace(os.sep, '/')
            toks = TOK.findall(open(p, 'rb').read())
            if toks:
                nfile += 1
            for m in sorted(set(toks)):
                m = m.decode()
                seen.add(m)
                empty = [pk for pk in packs if not has_text(pk, m)]
                if not empty:
                    continue
                if any(rel == kf and kr.search(m) for kf, kr in KNOWN):
                    known += 1
                    continue
                where = 'every pack' if len(empty) == len(packs) else ' '.join(pk[:-5] for pk in empty)
                bad.append('%s <#%s#> resolves to nothing in %s' % (rel, m, where))
    for b in bad[:60]:
        print('  ' + b)
    print('reaper_dictcheck: %s packs, %d packs at %d lines, %d distinct tokens in %d files, %d unresolved (%d known stock gaps)'
          % ('named' if named else 'numbered', len(packs), counts.get('EN.dict', 0), len(seen), nfile,
             len([b for b in bad if 'resolves' in b]), known))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
