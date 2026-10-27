#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The guide's factory-defaults section agrees with the firmware's defaults table.

WHY THIS EXISTS. docs/REAPER-GUIDE.md section 8 lists every factory default (owner, 2026-10-12: "a
section that details ALL factory default settings"). The review that wrote it found the previous
edition wrong in five places: two different key counts, a psc6g row whose stock value was already 1
on every fleet model, a missing wl_crypto change, and three DNS Failover switches described as on
after their defaults had changed. A default changes in shared/defaults.c with a green build and the
guide keeps the old value for months. This suite resolves the table the way a factory reset applies
it and fails on any drift.

WHAT IT DOES.
  - resolves router_defaults[] for the configured build: the macro set is shared/rtconfig.h plus every
    -D on a configured package's CFLAGS (jansson-2.7/Makefile), comments stripped first, and where a
    key is listed twice the LATER active entry wins, because restore_defaults() nvram_set()s the table
    in order;
  - every "`key` `value`" pair written in section 8 names the value the table gives that key;
  - every row of the 8.1 table (stock setting, stock value, **Reaper value**) gives the table's value;
  - every Reaper-owned key in the table (reaper_, rwarden_, rwatch_, gk_, rtraf_, rchq_, rmcp_,
    rconn_, amas_bh_, the per-radio wl_punct / wl_bwfloor / wl_rmit) is named in section 8, so a new
    setting cannot ship undocumented;
  - section 8 states the number of entries Reaper adds and that every one of them is named.
Exit 0 pass, 1 fail, 77 skipped (no configured router source tree - pass release/src/router as argv[1]
or REAPER_ROUTER_SRC; rtconfig.h and jansson-2.7/Makefile exist only after a build).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
DEF = os.path.join(SRC, "shared", "defaults.c")
RTC = os.path.join(SRC, "shared", "rtconfig.h")
JMK = os.path.join(SRC, "jansson-2.7", "Makefile")
if not SRC or not os.path.isfile(DEF):
    skip("no router source tree with shared/defaults.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
if not (os.path.isfile(RTC) and os.path.isfile(JMK)):
    skip("router tree not configured (shared/rtconfig.h and jansson-2.7/Makefile appear after a build)")
HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE = os.path.join(HERE, "..", "..", "docs", "REAPER-GUIDE.md")
if not os.path.isfile(GUIDE):
    skip("docs/REAPER-GUIDE.md not found beside build-scripts/")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def rd(p):
    return open(p, encoding="utf-8", errors="replace").read()

macros = {}
for l in rd(RTC).split("\n"):
    m = re.match(r"\s*#define\s+(\w+)(?:\s+(.*))?", l)
    if m:
        macros[m.group(1)] = (m.group(2) or "1").strip()
for m in re.finditer(r"-D([A-Za-z_]\w*)(?:=(\S+))?", rd(JMK)):
    macros.setdefault(m.group(1), m.group(2) or "1")

def strip_comments(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 2 if s[j] == "\\" else 1
            out.append(s[i:j + 1]); i = j + 1
        elif s.startswith("/*", i):
            j = s.find("*/", i + 2); j = n if j < 0 else j + 2
            out.append("\n" * s.count("\n", i, j)); i = j
        elif s.startswith("//", i):
            j = s.find("\n", i); i = n if j < 0 else j
        else:
            out.append(c); i += 1
    return "".join(out)

def cexpr(e, M):
    e = re.sub(r"defined\s*\(\s*(\w+)\s*\)", lambda m: " 1 " if m.group(1) in M else " 0 ", e)
    e = re.sub(r"defined\s+(\w+)", lambda m: " 1 " if m.group(1) in M else " 0 ", e)
    def ident(m):
        w = m.group(0)
        if w in ("and", "or", "not"):
            return w
        v = M.get(w)
        if v is None:
            return " 0 "
        return " %s " % v.strip() if re.fullmatch(r"-?\d+[uUlL]*", v.strip()) else " 1 "
    e = e.replace("&&", " and ").replace("||", " or ")
    e = re.sub(r"!(?!=)", " not ", e)
    e = re.sub(r"\b[A-Za-z_]\w*\b", ident, e)
    e = re.sub(r"(\d+)[uUlL]+", r"\1", e)
    try:
        return bool(eval(e, {}, {}))
    except Exception:
        return False

def active_text(src, M):
    M = dict(M); stack = []; act = True; out = []
    for l in src.split("\n"):
        m = re.match(r"#\s*(ifdef|ifndef|if|elif|else|endif|define|undef)\b(.*)", l.strip())
        if not m:
            out.append(l if act else ""); continue
        d, rest = m.group(1), m.group(2).strip()
        if d in ("if", "ifdef", "ifndef"):
            if d == "ifdef":
                v = bool(rest) and rest.split()[0] in M
            elif d == "ifndef":
                v = bool(rest) and rest.split()[0] not in M
            else:
                v = cexpr(rest, M)
            stack.append([act, v and act]); act = act and v
        elif d == "elif":
            parent, taken = stack[-1]
            v = (not taken) and parent and cexpr(rest, M)
            stack[-1] = [parent, taken or v]; act = v
        elif d == "else":
            parent, taken = stack[-1]
            act = parent and not taken; stack[-1] = [parent, True]
        elif d == "endif":
            act = stack.pop()[0]
        elif d == "define" and act:
            mm = re.match(r"(\w+)(?:\s+(.*))?", rest)
            if mm:
                M[mm.group(1)] = (mm.group(2) or "1").strip()
        elif d == "undef" and act:
            M.pop(rest.split()[0], None)
        out.append("")
    return "\n".join(out), M

# string macros used as values (DEF_SECOND_WANIF "none" in wans_dualwan) come from shared/shared.h
_, hdr = active_text(strip_comments(rd(os.path.join(SRC, "shared", "shared.h"))), macros)
STRMAC = {k: v.strip().strip('"') for k, v in hdr.items() if re.fullmatch(r'"[^"]*"', v.strip())}

pre, _ = active_text(strip_comments(rd(DEF)), macros)
a = pre.find("struct nvram_tuple router_defaults[]")
body = pre[a:pre.find("};", a)]
table = {}
for m in re.finditer(r'\{\s*"([^"]+)"\s*,\s*((?:"(?:[^"\\]|\\.)*"|[A-Za-z_]\w*|\s)+?)\s*,', body):
    v = "".join(STRMAC.get(mac, "<%s>" % mac) if mac else lit
                for lit, mac in re.findall(r'"((?:[^"\\]|\\.)*)"|([A-Za-z_]\w*)', m.group(2)))
    table[m.group(1)] = v          # the later active entry wins, as on a reset
check("the defaults table resolves (more than 1500 keys)", len(table) > 1500, len(table))
check("reset semantics: sw_mode is router mode on this build", table.get("sw_mode") == "1", table.get("sw_mode"))

g = rd(GUIDE)
i8, i9 = g.find("## 8. Factory defaults"), g.find("## 9. Present but inactive")
check("the guide has section 8 before section 9", 0 < i8 < i9)
sec = g[i8:i9]

bad = []
for m in re.finditer(r"`([A-Za-z0-9_]+)` (?:\*\*)?`([^`]*)`", sec):
    k, v = m.group(1), m.group(2)
    if k in table and table[k] != v:
        bad.append("%s: guide %r, table %r" % (k, v, table[k]))
check("every `key` `value` pair in section 8 matches the table", not bad, bad)

s81 = sec[sec.find("### 8.1"):sec.find("### 8.2")]
bad = []
rows = 0
for line in s81.split("\n"):
    if not line.startswith("| `"):
        continue
    cols = [c.strip() for c in line.strip("|").split("|")]
    keys = re.findall(r"`([A-Za-z0-9_]+)`", cols[0])
    mv = re.search(r"\*\*`([^`]*)`\*\*", cols[2])
    if not keys or not mv:
        continue
    rows += 1
    want = mv.group(1)
    for k in keys:
        got = table.get(k) or ""
        if not (got == want or (want.endswith("\u2026") and got.startswith(want[:-1]))):
            bad.append("%s: guide %r, table %r" % (k, want, table.get(k)))
check("8.1 lists the changed stock settings (14 or more rows)", rows >= 14, rows)
check("every 8.1 Reaper value matches the table", not bad, bad)

OWN = re.compile(r"^(reaper_|rwarden_|rwatch_|gk_|rtraf_|rchq_|rmcp_|rconn_|amas_bh_)|^wl_(punct|bwfloor|rmit)$")
own = sorted(k for k in table if OWN.search(k))
missing = [k for k in own if "`%s`" % k not in sec]
check("every Reaper-owned key in the table is named in section 8 (%d keys)" % len(own), not missing, missing)

m = re.search(r"adds (\d+)\*\* entries of its own", sec)
check("section 8 states how many entries Reaper adds", m is not None)

# 2026-10-23: the "adds N / removes M" figures had gone stale (93 stated, 104 real) because nothing
# recomputed them. They are key-set differences between this tree's defaults.c and the stock tree's
# (every { "key", ...} entry, comments stripped, no #if evaluation - the method that reproduces the
# 93 / 18 written at v3.4.2). Checked when a stock tree is available: REAPER_STOCK_SRC, or the
# stock-base checkout beside this repository's clone (.../stock-base/release/src/router).
# 2026-10-27 (40585 rebase): "stock" is the PINNED base (build-scripts/patch_count.sh BASE=), not whatever the
# stock-base checkout happens to be at - against the old a7ebfa133a checkout the merged tree counted ASUS 40585's
# own 8 new keys as Reaper adds and its 4 dropped keys as Reaper removals. Order: REAPER_STOCK_SRC; the pin read
# from the router tree's own git history; the stock-base checkout only when its HEAD is the pin.
import subprocess
def _pin():
    try:
        m = re.search(r"^BASE=([0-9a-f]{7,40})\s*$", rd(os.path.join(HERE, "..", "patch_count.sh")), re.M)
        return m.group(1) if m else None
    except OSError:
        return None
def _git(d, *a):
    try:
        r = subprocess.run(["git", "-C", d] + list(a), capture_output=True, text=True, errors="replace")
        return r.stdout if r.returncode == 0 else None
    except OSError:
        return None
PIN = _pin()
stext, sref = None, None
if os.environ.get("REAPER_STOCK_SRC"):
    sdef = os.path.join(os.environ["REAPER_STOCK_SRC"], "shared", "defaults.c")
    if os.path.isfile(sdef):
        stext, sref = rd(sdef), sdef
if stext is None and PIN:
    t = _git(os.path.join(SRC, "shared"), "show", PIN + ":./defaults.c")
    if t:
        stext, sref = t, "pinned base " + PIN[:11]
if stext is None:
    stock = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(SRC))))),
                         "stock-base", "release", "src", "router")
    sdef = os.path.join(stock, "shared", "defaults.c")
    head = (_git(stock, "rev-parse", "HEAD") or "").strip()
    if os.path.isfile(sdef) and (not PIN or (head and head.startswith(PIN))):
        stext, sref = rd(sdef), sdef
    elif os.path.isfile(sdef):
        print("note: stock-base is at %s, not the pinned base %s - the adds/removes figures are not recomputed" % (head[:11], PIN[:11]))
mr = re.search(r"removes (\d+)\*\*", sec)
if stext is None:
    print("note: no stock tree (REAPER_STOCK_SRC / pinned base) - the adds/removes figures are not recomputed")
else:
    print("note: adds/removes recomputed against %s" % sref)
    KEY = re.compile(r'^\s*\{\s*"([A-Za-z0-9_.:\-]+)"\s*,', re.M)
    ours, theirs = set(KEY.findall(strip_comments(rd(DEF)))), set(KEY.findall(strip_comments(stext)))
    added, removed = len(ours - theirs), len(theirs - ours)
    check("section 8's \"adds N\" is the real count of keys Reaper adds over stock (%d)" % added,
          m is not None and int(m.group(1)) == added, m.group(1) if m else None)
    check("section 8's \"removes M\" is the real count of stock keys Reaper drops (%d)" % removed,
          mr is not None and int(mr.group(1)) == removed, mr.group(1) if mr else None)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
