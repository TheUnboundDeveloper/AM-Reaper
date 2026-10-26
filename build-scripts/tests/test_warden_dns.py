#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Warden threat domains (2026-10-19): URLhaus / ThreatFox hostfiles turned into one compiled table every dnsmasq
instance maps (2026-10-24; reaper-nx=/host/ lines held once per instance before that), restarted only when the
list changed.

WHY THIS EXISTS. The list is built by shell inside a C string (rc/rwarden.c rw_gen_update) that
nothing runs before a build, and it is the one Reaper list that reaches the resolver every LAN
client uses: a bad parse blocks nothing or blocks the feed host itself (then no update can ever
run again), and a restart on every nightly run would drop every client's DNS for a second each
night for nothing. The include is also fatal to dnsmasq when the file is missing, so the C side
must hand it out only when the file exists - the SDN instances have no guard. Since 2026-10-24 the
names live in ONE Wallguard-format table (wallguardc --subtree, one list per feed) that every instance
maps read-only - ~12 B a name once instead of ~54 B in each of five copies - so the include is two
constant lines, the "<feeds> <name>" list is kept gzipped on /jffs with its checksum, and rc has
to rebuild the table from that copy (or an older firmware's reaper-nx= copy) at boot.

WHAT IT DOES. Lifts the block out of rc/rwarden.c (C literal, its own #defines resolved), runs
it under /bin/sh and busybox ash with fake curl/_nv/logger/wallguardc against fixture hostfiles: TAB
and space forms, CRLF, upper case, junk and dotless names dropped, the built-in never-block set,
the operator's exemptions, the DoT and LAN-domain names, the cap, keep-last-good per feed, no
change = no restart, a deselected feed, a table wallguardc rejects, the memory guard, the switch off;
then the lifted boot rebuild script from the gzipped feeds list, from the older copy, with no copy,
and with a rejecting wallguardc. Then pins the C side: the end-of-run restart line and exit 0, the
stats keys, the NULL-when-missing helper, the two instance emitters behind it, the sync before the
early returns, the collector's record check, the CGI/export rows, the defaults, the page, the rwatch
check-2 retry and the CURLG redirect pin.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as argv[1]
or REAPER_ROUTER_SRC - or no /bin/sh).
"""
import gzip, hashlib, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

passed = 0
def ok(cond, what):
    global passed
    if not cond: die(what)
    passed += 1
    print("ok   " + what)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwarden.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
SH = "/bin/sh" if os.path.exists("/bin/sh") else shutil.which("sh")
if not SH:
    skip("no /bin/sh to run the lifted shell")
BB = shutil.which("busybox")
if BB and subprocess.run([BB, "ash", "-c", "true"], capture_output=True).returncode != 0:
    BB = None

def read(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        die("missing %s" % rel)
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

# ---- the C-literal lifter (test_front_narrow.py's shape; strings, comments and identifiers in order)
def macros_of(src):
    m = {}
    for line in src.splitlines():
        mm = re.match(r'\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$', line)
        if not mm: continue
        name, rest = mm.group(1), mm.group(2)
        rest = re.sub(r"/\*.*?\*/", "", rest)
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"|([A-Za-z_][A-Za-z0-9_]*)', rest)
        if not parts or not any(s for s, _ in parts): continue
        val, okay = "", True
        for s, ident in parts:
            if ident:
                if ident in m: val += m[ident]
                else: okay = False; break
            else:
                val += s
        if okay: m[name] = val
    return m

def c_unescape(s):
    out, i = [], 0
    table = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "'": "'", "?": "?", "a": "\a", "r": "\r"}
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in "01234567":
                j = i + 1
                while j < len(s) and j < i + 4 and s[j] in "01234567": j += 1
                out.append(chr(int(s[i + 1:j], 8))); i = j
            else:
                out.append(table.get(nxt, "\\" + nxt)); i += 2
        else:
            out.append(c); i += 1
    return "".join(out)

def lift_body(body, macros):
    text = ""
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|(/\*.*?\*/)|([A-Za-z_][A-Za-z0-9_]*)', body, re.S):
        if m.group(1) is not None:
            text += c_unescape(m.group(1))
        elif m.group(3) is not None:
            text += c_unescape(macros.get(m.group(3), ""))
    return text

def lifted_script(csrc, needle, macros):
    at = csrc.find(needle)
    if at < 0: die("%r not found in the generator" % needle)
    start = csrc.rfind("fputs(", 0, at)
    end = csrc.find(", f);", at)
    if start < 0 or end < 0: die("could not frame the fputs() around %r" % needle)
    return lift_body(csrc[start + 6:end], macros)

def lifted_array(csrc, name, macros):
    # 2026-10-24: a constant shell script in a char array (the boot rebuild), same lifting
    head = "static const char %s[] =" % name
    at = csrc.find(head)
    if at < 0: die("%s not found" % name)
    end = csrc.find(";\n", at)
    return lift_body(csrc[at + len(head):end], macros)

rw = read("rc/rwarden.c")
macros = macros_of(rw)
for k in ("RW_DNS_CONF", "RW_DNS_CACHE", "RW_DNS_LEGACY", "RW_DNS_UPD", "RW_DNS_FEEDS", "RW_HITS", "RW_CACHE",
          "RW_NX_DB", "RW_DNS_KGZ", "RW_DNS_KSUM", "RW_DNS_COUNT", "RW_DNS_FIRST", "RW_DIDS_STR"):
    ok(k in macros, "rwarden.c defines %s" % k)
block = lifted_script(rw, "# ---- threat domains", macros)
SPLIT = 'if [ "$(_nv rwarden_dns)" = 1 ]; then\n'
ok(block.startswith("# ---- threat domains") and SPLIT in block and block.rstrip().endswith("fi"), "the threat-domain block lifts whole")
ok("RW_DNSC=/tmp/rwarden/dns.conf\n" in block and "RW_DNSK=/jffs/rwarden/dns.nx\n" in block and "RW_DNSL=/jffs/rwarden/dns.cache\n" in block
   and "RW_DNSF=/jffs/rwarden/dns.feeds\n" in block and "RW_DNSH=/tmp/dreadwatch/dns.hits\n" in block and "RW_DNSA=/jffs/rwarden/dnsallow\n" in block
   and "RW_NXDB=/tmp/reaper_nx/threat.db\n" in block and "RW_DNSKG=/jffs/rwarden/dns.k.gz\n" in block and "RW_DNSKS=/jffs/rwarden/dns.k.sum\n" in block
   and "RW_DNSN=/tmp/rwarden/dns.count\n" in block and "RW_DNS1=/tmp/rwarden/dns.first\n" in block
   and 'RW_DIDS="urlhaus phish c2 crypto ransom certpl threatview threatfox"\n' in block,
   "the block's paths and the feed order come from the C defines (one source of truth)")
head_part, tail_part = block.split(SPLIT, 1)
tail_part = SPLIT + tail_part
rebuild_src = lifted_array(rw, "rw_nx_rebuild_sh", macros)
ok("D=/tmp/reaper_nx; K=/jffs/rwarden/dns.k.gz; O=/jffs/rwarden/dns.nx.gz; T=/tmp/rwarden/nx.rebuild.$$\n" in rebuild_src
   and '/usr/sbin/wallguardc build --subtree --out $D/threat.db.new --kfile $T.k --kids "urlhaus phish c2 crypto ransom certpl threatview threatfox other legacy"' in rebuild_src
   and "/usr/sbin/wallguardc check --db $D/threat.db.new" in rebuild_src and "$T.l." not in rebuild_src,
   "the boot rebuild script lifts whole: the C defines' paths, wallguardc reads the feeds list itself (--kfile, review 2026-10-24 Q-A-3b) + check, the feed order with 'other' and 'legacy' after it")

URLHAUS = ("# abuse.ch URLhaus Host file\n# Last updated: 2026-10-19\n#\n"
           "127.0.0.1\tevil.example\n127.0.0.1\tEVIL2.EXAMPLE\r\n127.0.0.1\tsub.x.asuscomm.com\n127.0.0.1\tmine.example\n"
           "127.0.0.1\tbad_host.example\n127.0.0.1\tlocalhost\n0.0.0.0 space.example\n127.0.0.1\tdeep.dns.quad9.net\n")
PHISH = "# malware-filter phishing hosts\n0.0.0.0 c2.example\n0.0.0.0 evil.example\n0.0.0.0 Home.LAN\n"
# 2026-10-21: the other list formats the parser takes - CSV (a FRONTING line never taken), adblock, bare names
C2 = "#domain,ioc\nc2real.example,Possible Cobalt Strike C2 Domain\ncdn.example,Possible Cobalt Strike C2 Fronting Domain\nfronted.example,Possible Cobalt Strike C2 Fronted Domain\n"
CRYPTO = "! adblock\n||miner.example^\nplainminer.example\n195.187.6.55 sinkholed.example\n"   # CERT Polska: any IPv4 in a hosts line
NV = {"rwarden_dns": "1", "rwarden_dns_feeds": "urlhaus phish", "lan_domain": "home.lan",
      "ddns_hostname_x": "my.asuscomm.com", "ntp_server0": "pool.ntp.org", "ntp_server1": "",
      "dnspriv_rulelist": "1.1.1.1>853>one.one.one.one><9.9.9.9>853>dns.quad9.net>"}

work = tempfile.mkdtemp(prefix="rwdns_")
try:
    bp = os.path.join(work, "block.sh"); open(bp, "w").write(block)
    r = subprocess.run([SH, "-n", bp], capture_output=True, text=True)
    ok(r.returncode == 0, "the block passes sh -n (%s)" % r.stderr.strip()[:200])
    rbp = os.path.join(work, "rebuild0.sh"); open(rbp, "w").write(rebuild_src)
    r = subprocess.run([SH, "-n", rbp], capture_output=True, text=True)
    ok(r.returncode == 0, "the boot rebuild script passes sh -n (%s)" % r.stderr.strip()[:200])
    if BB:
        r = subprocess.run([BB, "ash", "-n", bp], capture_output=True, text=True)
        ok(r.returncode == 0, "the block passes busybox ash -n (%s)" % r.stderr.strip()[:200])

    fix = os.path.join(work, "fix"); nvd = os.path.join(work, "nv"); logf = os.path.join(work, "logger.out")
    os.makedirs(fix); os.makedirs(nvd)
    open(os.path.join(fix, "urlhaus.txt"), "w", newline="").write(URLHAUS)
    open(os.path.join(fix, "phish.txt"), "w").write(PHISH)
    open(os.path.join(fix, "c2.txt"), "w").write(C2)
    open(os.path.join(fix, "crypto.txt"), "w").write(CRYPTO)
    open(os.path.join(fix, "threatfox.txt"), "w").write("# ThreatFox snapshot (bundled)\nsnapc2.example\nSNAP2.example\n")
    # 2026-10-22: a lower-priority list whose names sort FIRST, a child of a higher-priority listed name,
    # and a name longer than DNS allows (dnsmasq rejects the whole file over it)
    LONG = ".".join(["a" * 60] * 5) + ".example"
    open(os.path.join(fix, "ransom.txt"), "w").write("aaa1.example\naaa2.example\nx.c2.example\n" + LONG + "\n")
    def setnv(k, v): open(os.path.join(nvd, k), "w").write(v)

    HEAD = r'''
_nv() { cat "$NVDIR/$1" 2>/dev/null; }
logger() { printf "%s\n" "$*" >> "$LOGF"; }
curl() {
  o=""; u=""; p=""
  for a in "$@"; do [ "$p" = -o ] && o="$a"; case "$a" in https://*) u="$a";; esac; p="$a"; done
  case "$u" in *urlhaus*) id=urlhaus;; *phishing-filter*) id=phish;; *C2IntelFeeds*) id=c2;; *Prigent-Crypto*) id=crypto;; *blocklistproject*) id=ransom;; *abuse.ch*) id=abusech;; *) id=none;; esac
  echo "$u" >> "$WORK/fetched"
  case " $CURL_FAIL " in *" $id "*) printf 410; return 22;; esac
  case " $CURL_NOANSWER " in *" $id "*) printf 000; return 28;; esac
  cp "$FIX/$id.txt" "$o" 2>/dev/null || { printf 404; return 22; }; printf 200
}
CURL=curl
TMP=$WORK/feed.1
# 2026-10-24: the list is compiled by wallguardc into one table; the fake records its arguments and writes, as the
# table, "<feed> <name>" for every name of every --list it was handed (in that order) - or, for --kfile + --kids,
# every id's names in --kids order - so the test can read what
# went in. SC_FAIL=1 makes it reject, as a list with a bad name would.
wallguardc() {
  echo "$*" >> "$WORK/wallguardc.calls"
  [ "$SC_FAIL" = 1 ] && return 1
  case "$1" in
    build) o=""; p=""; kf=""; kids=""; : > "$WORK/sc.tbl"
      for a in "$@"; do
        [ "$p" = --out ] && o="$a"
        [ "$p" = --kfile ] && kf="$a"
        [ "$p" = --kids ] && kids="$a"
        if [ "$p" = --list ]; then id=$(echo "$a" | cut -d: -f2); sed "s/^/$id /" "${a#*:*:}" >> "$WORK/sc.tbl"; fi
        p="$a"
      done
      # --kfile (review 2026-10-24, Q-A-3b): every id's names in --kids order, each in list order - what the
      # per-feed --list files gave
      [ -n "$kf" ] && awk -v K="$kids" '{ L[NR] = $0 } END { n = split(K, ids, " "); for (i = 1; i <= n; i++) for (r = 1; r <= NR; r++) { split(L[r], x, " "); f = (x[1] == "-") ? "other" : x[1]; m = split(f, a, ","); for (j = 1; j <= m; j++) if (a[j] == ids[i]) print ids[i], x[2] } }' "$kf" >> "$WORK/sc.tbl"
      cp "$WORK/sc.tbl" "$o";;
  esac
  return 0
}
'''
    wtmp = os.path.join(work, "tmp"); wjffs = os.path.join(work, "jffs")
    CONF2 = ["reaper-hitlog=/tmp/dreadwatch/dns.hits", "reaper-nx-db=%s/nx/threat.db" % wtmp]
    TBL = os.path.join(wtmp, "nx", "threat.db")
    names = lambda kl: [l.split()[1] for l in kl]
    def envfor(extra):
        env = dict(os.environ, NVDIR=nvd, LOGF=logf, FIX=fix, WORK=work, LC_ALL="C")
        env.update(extra or {})
        return env
    def run(shell, env_extra=None):
        os.makedirs(wtmp, exist_ok=True); os.makedirs(wjffs, exist_ok=True)
        over = ('RW_DNSC=%s/dns.conf\nRW_DNSK=%s/dns.nx\nRW_DNSL=%s/dns.cache\nRW_DNSU=%s/dns.upd\nRW_DNSF=%s/dns.feeds\n'
                'RW_DNSH=/tmp/dreadwatch/dns.hits\nRW_DNSA=%s/dnsallow\nRW_DNS_CAP=${CAP:-200000}\n'
                'RW_NXDIR=%s/nx\nRW_NXDB=%s/nx/threat.db\nRW_DNSKG=%s/dns.k.gz\nRW_DNSKS=%s/dns.k.sum\nRW_DNSN=%s/dns.count\nRW_DNS1=%s/dns.first\nRW_WALLGUARDC=wallguardc\n'
                % (wtmp, wjffs, wjffs, wtmp, wjffs, wjffs, wtmp, wtmp, wjffs, wjffs, wtmp, wtmp))
        sp = os.path.join(work, "run.sh")
        open(sp, "w").write(HEAD + head_part + over + tail_part + '\necho "DNS_CHANGED=$DNS_CHANGED"\n')
        cmd = [shell, sp] if shell != "busybox" else [BB, "ash", sp]
        p = subprocess.run(cmd, capture_output=True, text=True, env=envfor(env_extra), cwd=work, timeout=60)
        if p.returncode != 0:
            die("block failed under %s:\n%s" % (shell, p.stderr[-800:]))
        changed = re.search(r"DNS_CHANGED=(\d)", p.stdout)
        conf = os.path.join(wtmp, "dns.conf")
        lines = open(conf).read().splitlines() if os.path.exists(conf) else None
        logs = open(logf).read().splitlines() if os.path.exists(logf) else []
        kg = os.path.join(wjffs, "dns.k.gz")
        kl = gzip.open(kg, "rt").read().splitlines() if os.path.exists(kg) else None
        return (changed.group(1) if changed else "?"), lines, logs, kl
    def rebuild(shell, env_extra=None):
        # the boot script with the work paths in place of the C defines, the fake in place of /usr/sbin/wallguardc
        os.makedirs(wtmp, exist_ok=True)
        m2 = dict(macros); m2.update(RW_NX_DIR=wtmp + "/nx", RW_DNS_KGZ=wjffs + "/dns.k.gz", RW_DNS_CACHE_GZ=wjffs + "/dns.nx.gz",
                                     RW_DNS_CACHE=wjffs + "/dns.nx", RW_DNS_LEGACY=wjffs + "/dns.cache", RW_DNS_COUNT=wtmp + "/dns.count", RW_DNS_FIRST=wtmp + "/dns.first")
        text = lifted_array(rw, "rw_nx_rebuild_sh", m2).replace("T=/tmp/rwarden/nx.rebuild.$$", "T=%s/nx.rebuild.$$" % wtmp).replace("/usr/sbin/wallguardc ", "wallguardc ")
        sp = os.path.join(work, "rebuild.sh"); open(sp, "w").write(HEAD + text)
        cmd = [shell, sp] if shell != "busybox" else [BB, "ash", sp]
        p = subprocess.run(cmd, capture_output=True, text=True, env=envfor(env_extra), cwd=work, timeout=60)
        cp = os.path.join(work, "wallguardc.calls"); calls = open(cp).read() if os.path.exists(cp) else ""
        tbl = open(TBL).read().splitlines() if os.path.exists(TBL) else None
        rd = lambda f: open(os.path.join(wtmp, f)).read().strip() if os.path.exists(os.path.join(wtmp, f)) else None
        return p.returncode, calls, tbl, rd("dns.count"), rd("dns.first")
    def clear_tmp():
        shutil.rmtree(os.path.join(wtmp, "nx"), ignore_errors=True)
        for f in (os.path.join(wtmp, "dns.count"), os.path.join(wtmp, "dns.first"), os.path.join(work, "wallguardc.calls")):
            if os.path.exists(f): os.unlink(f)

    def reset_state():
        for d in ("tmp", "jffs"):
            shutil.rmtree(os.path.join(work, d), ignore_errors=True)
        for f in (logf, os.path.join(work, "wallguardc.calls")):
            if os.path.exists(f): os.unlink(f)
        for k, v in NV.items(): setnv(k, v)

    shells = [SH] + (["busybox"] if BB else [])
    for shell in shells:
        tag = "sh" if shell == SH else "ash"
        reset_state()
        os.makedirs(wjffs, exist_ok=True)
        # 2026-10-22: asuscomm.com is a seeded entry of this list now, not a hard-coded exemption
        open(os.path.join(wjffs, "dnsallow"), "w").write("MINE.example, other.test asuscomm.com\n")

        open(os.path.join(wjffs, "dns.cache"), "w").write("address=/legacy.example/\n")   # an older firmware's copy
        ch, lines, logs, kl = run(shell)
        # 2026-10-24: the feeds list is "<ids> <name>" (a name two lists carry says both, list order); the include is
        # two constant lines - the hit log and the table. Review 2026-10-24 (Q-A-4): the list keeps the kept names'
        # own order - priority (URLhaus before Phishing), then list order - instead of a sort of up to a million lines
        ok(kl == ["urlhaus,phish evil.example", "urlhaus evil2.example", "urlhaus space.example", "phish c2.example"] and lines == CONF2,
           "[%s] first run: TAB and space forms, CRLF and upper case normalised; junk, dotless, never-block, DoT, LAN-domain and exempted names out; the feeds list is \"<ids> <name>\" in priority + list order; the include is the hit-log and table lines (got %s / %s)" % (tag, kl, lines))
        tbl = open(TBL).read().splitlines() if os.path.exists(TBL) else None
        calls = open(os.path.join(work, "wallguardc.calls")).read()
        ok(ch == "1" and tbl == ["urlhaus evil.example", "urlhaus evil2.example", "urlhaus space.example", "phish evil.example", "phish c2.example"]
           and ("build --subtree --out %s.new --kfile " % TBL) in calls and "--kids urlhaus phish c2 crypto ransom certpl threatview threatfox other" in calls
           and "--list" not in calls and ("check --db %s.new" % TBL) in calls,
           "[%s] first run: changed; wallguardc compiled one list per feed (bit = position in RW_DIDS, --subtree) and checked the table before it was installed (got %s)" % (tag, calls[-300:]))
        gzp = os.path.join(wjffs, "dns.nx.gz")
        ok(os.path.exists(gzp) and gzip.open(gzp, "rt").read().splitlines() == [
               "reaper-hitlog=/tmp/dreadwatch/dns.hits", "# feed phish", "reaper-nx=/c2.example/", "# feed urlhaus", "reaper-nx=/evil2.example/",
               "reaper-nx=/space.example/", "# feed urlhaus,phish", "reaper-nx=/evil.example/"]
           and not os.path.exists(os.path.join(wjffs, "dns.nx")) and os.path.exists(os.path.join(wtmp, "dns.upd"))
           and open(os.path.join(wjffs, "dns.k.sum")).read().strip() == hashlib.md5(("\n".join(kl) + "\n").encode()).hexdigest()
           and open(os.path.join(wtmp, "dns.count")).read().strip() == "4" and open(os.path.join(wtmp, "dns.first")).read().strip() in names(kl),
           "[%s] first run: the older reaper-nx= form is still kept gzipped for a downgrade (no uncompressed copy), the feeds list's checksum, the count and a sample name for httpd, the stamp" % tag)
        ok(not os.path.exists(os.path.join(wjffs, "dns.cache")),
           "[%s] the older firmware's address= copy is retired once the counted copy exists (a downgrade then rebuilds its own)" % tag)
        fm = {l.split()[0]: l.split() for l in open(os.path.join(wjffs, "dns.feeds")).read().splitlines()}
        ok(set(fm) == {"urlhaus", "phish", "c2", "crypto", "ransom", "certpl", "threatview", "threatfox"} and fm["urlhaus"][1:4] == ["1", "6", "3"] and fm["phish"][1:4] == ["1", "3", "2"]
           and fm["c2"][1] == "0" and fm["c2"][6] == "off"
           and fm["urlhaus"][6] == "ok" and fm["urlhaus"][4] == fm["urlhaus"][5] and int(fm["urlhaus"][4]) > 0,
           "[%s] feed metadata: selected, names downloaded, names kept in the list (a shared name counts for both), last-ok = last-try on success (got %s)" % (tag, fm))
        ok(len(logs) == 1 and "threat domains: 4 loaded (urlhaus 6, phish 3); 4 never-block, 0 covered by a listed parent, list changed - dnsmasq restarts" in logs[0],
           "[%s] first run: one log line with the counts and the restart notice (%s)" % (tag, logs[:1]))
        ok(not any(n in " ".join(kl) for n in ("asuscomm", "quad9", "home.lan", "mine.example", "bad_host", "localhost")), "[%s] nothing from the never-block set reached the list" % tag)

        ch, lines2, logs, kl2 = run(shell)
        ok(ch == "0" and lines2 == lines and kl2 == kl and len(logs) == 2 and "list changed" not in logs[1], "[%s] unchanged feeds: no restart (the checksum matched, no table rebuilt), same list, log says so" % tag)

        # 2026-10-22: the operator removes the seeded asuscomm.com entry -> the name is blockable again;
        # the operator's own DDNS name (my.asuscomm.com) stays exempt from its setting
        open(os.path.join(wjffs, "dnsallow"), "w").write("MINE.example, other.test\n")
        ch, lx, logs, kx = run(shell)
        ok(ch == "1" and "urlhaus sub.x.asuscomm.com" in kx and "my.asuscomm.com" not in " ".join(kx),
           "[%s] a removed never-block entry is no longer exempt (no hidden copy in the code) (got %s)" % (tag, kx))
        open(os.path.join(wjffs, "dnsallow"), "w").write("MINE.example, other.test asuscomm.com\n")
        ch, lines2, logs, kl2 = run(shell)

        okb = {l.split()[0]: l.split() for l in open(os.path.join(wjffs, "dns.feeds")).read().splitlines()}["urlhaus"][4]
        ch, lines3, logs, kl3 = run(shell, {"CURL_FAIL": "urlhaus"})
        fm3 = {l.split()[0]: l.split() for l in open(os.path.join(wjffs, "dns.feeds")).read().splitlines()}
        ok(ch == "0" and kl3 == kl and any("urlhaus fetch FAILED (HTTP 410: the list host refuses it) - keeping the previous download" in l for l in logs[2:]),
           "[%s] one feed down: its previous download is kept, the list does not shrink, no restart" % tag)
        ok(fm3["urlhaus"][6] == "failed" and fm3["urlhaus"][4] == okb and fm3["phish"][6] == "ok",
           "[%s] feed metadata: a failed fetch says so and keeps the last good time (got %s)" % (tag, fm3["urlhaus"]))

        ch, lines4, logs, kl4 = run(shell, {"CAP": "2"})
        fm4 = {l.split()[0]: l.split() for l in open(os.path.join(wjffs, "dns.feeds")).read().splitlines()}
        ok(ch == "1" and kl4 == ["urlhaus,phish evil.example", "urlhaus evil2.example"]
           and "2 loaded" in logs[-2] and "the 2-name limit left out 2 names from the lowest-priority lists:" in logs[-1]
           and "urlhaus 1" in logs[-1] and "phish 1" in logs[-1] and fm4["urlhaus"][7] == "1" and fm4["phish"][7] == "1",
           "[%s] the limit is filled in list order (URLhaus before Phishing), each list's left-out names counted in the log and dns.feeds (got %s / %s)" % (tag, kl4, logs[-2:]))

        setnv("rwarden_dns_feeds", "urlhaus")
        ch, lines5, logs, kl5 = run(shell)
        fm5 = {l.split()[0]: l.split() for l in open(os.path.join(wjffs, "dns.feeds")).read().splitlines()}
        ok(fm5["phish"][1] == "0" and fm5["phish"][6] == "off", "[%s] feed metadata: a deselected feed is off" % tag)
        ok(ch == "1" and kl5 == ["urlhaus evil.example", "urlhaus evil2.example", "urlhaus space.example"] and lines5 == CONF2
           and not os.path.exists(os.path.join(wtmp, "dns.conf.phish.last")) and "(urlhaus 6)" in logs[-1],
           "[%s] a deselected feed contributes nothing and its previous download is dropped (got %s)" % (tag, kl5))
        setnv("rwarden_dns_feeds", "urlhaus phish")

        # 2026-10-21: CSV / adblock / bare-name lists; a FRONTING or FRONTED CSV line is never taken
        reset_state(); setnv("rwarden_dns_feeds", "c2 crypto")
        ch, lc, logs, kc = run(shell)
        ok(kc is not None and names(kc) == ["c2real.example", "miner.example", "plainminer.example", "sinkholed.example"],
           "[%s] CSV, adblock, bare-name and any-IPv4 hosts lines parse; a domain-fronting entry (a legitimate CDN) is never blocked (got %s)" % (tag, kc))
        # ThreatFox is a snapshot bundled with the firmware (abuse.ch closed free downloads 2026-10-21): read
        # from its file through RW_TFX, never fetched, part of Reaper's Basics
        reset_state(); setnv("rwarden_dns_feeds", "urlhaus threatfox")
        if os.path.exists(os.path.join(work, "fetched")): os.unlink(os.path.join(work, "fetched"))
        ch, lt, logs, kt = run(shell, {"RW_TFX": os.path.join(fix, "threatfox.txt")})
        fmt = {l.split()[0]: l.split() for l in open(os.path.join(wjffs, "dns.feeds")).read().splitlines()}
        fetched = open(os.path.join(work, "fetched")).read() if os.path.exists(os.path.join(work, "fetched")) else ""
        ok(fmt["threatfox"][6] == "ok" and fmt["threatfox"][1:4] == ["1", "2", "2"] and "abuse.ch" not in fetched
           and "threatfox snapc2.example" in kt and "threatfox snap2.example" in kt,
           "[%s] ThreatFox: the bundled snapshot is read from its file (lower-cased), never fetched, state ok (got %s)" % (tag, fmt["threatfox"]))
        # review 2026-10-24 (Q-A-4): the bundled snapshot is parsed once per copy of it (its date and size kept beside
        # the parse), not every night; a changed copy - a new firmware's - is parsed again
        import time
        tfl = os.path.join(wtmp, "dns.conf.threatfox.last"); tfs = os.path.join(wtmp, "dns.conf.threatfox.src")
        m1 = os.path.getmtime(tfl); time.sleep(0.05)
        ch, lt2, logs, kt2 = run(shell, {"RW_TFX": os.path.join(fix, "threatfox.txt")})
        ok(os.path.exists(tfs) and len(open(tfs).read().split()) == 2 and os.path.getmtime(tfl) == m1 and kt2 == kt,
           "[%s] ThreatFox snapshot: the parse is kept (date + size recorded beside it) - the next night does not re-read the file" % tag)
        time.sleep(0.05)
        with open(os.path.join(fix, "threatfox.txt"), "a") as tf: tf.write("snap3.example\n")
        ch, lt3, logs, kt3 = run(shell, {"RW_TFX": os.path.join(fix, "threatfox.txt")})
        ok(os.path.getmtime(tfl) != m1 and "threatfox snap3.example" in kt3, "[%s] ThreatFox snapshot: a changed copy is parsed again (got %s)" % (tag, kt3))
        open(os.path.join(fix, "threatfox.txt"), "w").write("# ThreatFox snapshot (bundled)\nsnapc2.example\nSNAP2.example\n")
        # 2026-10-22: priority order, parent coverage, the DNS length limit
        reset_state(); setnv("rwarden_dns_feeds", "phish ransom")
        ch, lr, logs, kr = run(shell)
        ok(kr is not None and sorted(names(kr)) == ["aaa1.example", "aaa2.example", "c2.example", "evil.example"]
           and "4 loaded" in logs[-1] and "1 covered by a listed parent" in logs[-1] and "1 over 253 characters (not DNS names)" in logs[-1],
           "[%s] a child of a listed name is dropped (counted), a name over 253 characters never reaches the list (counted) (got %s / %s)" % (tag, kr, logs[-1:]))
        ch, lr2, logs, kr2 = run(shell, {"CAP": "2"})
        fr = {l.split()[0]: l.split() for l in open(os.path.join(wjffs, "dns.feeds")).read().splitlines()}
        ok(sorted(names(kr2)) == ["c2.example", "evil.example"]
           and fr["ransom"][7] == "2" and fr["phish"][7] == "0" and "ransom 2" in logs[-1],
           "[%s] a lower-priority list whose names sort first cannot push out a higher one (alphabetical would keep aaa1/aaa2) (got %s)" % (tag, kr2))
        # wallguardc rejects the new list: it is never installed, the list in use stays
        ch, lr3, logs, kr3 = run(shell, {"SC_FAIL": "1"})
        ok(ch == "0" and kr3 == kr2 and any("the new list failed wallguardc's own check - the list in use stays" in l for l in logs),
           "[%s] a list wallguardc rejects is not installed and nothing restarts (got %s)" % (tag, logs[-2:]))
        # the free-memory guard lowers the limit (1 kB available -> 1024 / 4 / 90 = 2 names: one copy, ~90 B a name while built)
        mi = os.path.join(work, "meminfo"); open(mi, "w").write("MemTotal: 2047968 kB\nMemAvailable:       1 kB\n")
        setnv("rwarden_dns_feeds", "phish ransom")
        ch, lr4, logs, kr4 = run(shell, {"RW_MEMINFO": mi})
        ok(len(kr4) == 2 and "the 2-name limit (lowered from 200000 to fit free memory) left out" in logs[-1],
           "[%s] the free-memory guard lowers the limit and says so (got %s)" % (tag, logs[-1:]))

        reset_state(); setnv("rwarden_dns_feeds", "urlhaus phish")
        ch, lines6, logs, kl6 = run(shell, {"CURL_FAIL": "urlhaus", "CURL_NOANSWER": "phish"})
        ok(ch == "0" and lines6 is None and kl6 is None and any("nothing fetched and no earlier list" in l for l in logs)
           and any("phish fetch FAILED (no answer, curl exit 28" in l and "no previous download" in l for l in logs),
           "[%s] both lists down on a fresh box: no list, no restart; the log names the cause and never claims a last-good copy (got %s)" % (tag, logs))

        reset_state(); run(shell)
        setnv("rwarden_dns", "0")
        ch, lines7, logs, _ = run(shell)
        ok(ch == "1" and lines7 is None and not os.path.exists(TBL) and not os.path.exists(os.path.join(wtmp, "dns.count"))
           and not [f for f in os.listdir(wtmp) if f.endswith(".last")],
           "[%s] switch off with a list present: include, table, count and previous downloads removed, one restart" % tag)
        ch, lines8, logs, _ = run(shell)
        ok(ch == "0" and lines8 is None, "[%s] switch off, nothing present: nothing to do" % tag)

        # ---- 2026-10-24 boot: the table is rebuilt from the /jffs copy (the lifted rw_nx_rebuild_sh)
        setnv("rwarden_dns", "1"); reset_state(); _, _, _, kb = run(shell)   # one full update leaves dns.k.gz + dns.nx.gz on "jffs"
        # what the fake wallguardc writes: every feed's names in list order, each in the feeds list's order
        exp = [f + " " + l.split()[1] for f in ("urlhaus", "phish") for l in kb if f in l.split()[0].split(",")]
        clear_tmp()
        rc_, calls, tbl, cnt, first = rebuild(shell)
        ok(rc_ == 0 and len(kb) >= 4 and tbl == exp and cnt == str(len(kb)) and first == kb[0].split()[1]
           and "build --subtree --out" in calls and "--kfile " in calls and "--kids urlhaus phish c2 crypto ransom certpl threatview threatfox other legacy" in calls
           and "check --db" in calls,
           "[%s] boot: the table is rebuilt from the gzipped feeds list - wallguardc reads it itself (--kfile), checked, the count and a sample name written (got %s / %s)" % (tag, tbl, calls[-200:]))
        os.unlink(os.path.join(wjffs, "dns.k.gz")); clear_tmp()
        rc_, calls, tbl, cnt, first = rebuild(shell)
        # (the older copy is grouped by feed, so its order differs from the feeds list's priority order)
        ok(rc_ == 0 and tbl is not None and sorted(tbl) == sorted("legacy " + n for n in names(kb)) and "other legacy" in calls and cnt == str(len(kb)) and first in names(kb),
           "[%s] boot right after an upgrade: the older reaper-nx= copy builds the table under one 'legacy' feed (got %s)" % (tag, tbl))
        clear_tmp()
        if os.path.exists(logf): os.unlink(logf)
        rc_, calls, tbl, cnt, first = rebuild(shell, {"SC_FAIL": "1"})
        blog = open(logf).read() if os.path.exists(logf) else ""
        ok(rc_ == 1 and tbl is None and "the /jffs copy would not build into a table - blocking nothing until the next update" in blog,
           "[%s] boot: a copy wallguardc rejects leaves no table, exit 1, and the script logs it itself (it runs detached now) (got %r)" % (tag, blog[-200:]))
        os.unlink(os.path.join(wjffs, "dns.nx.gz")); clear_tmp()
        rc_, calls, tbl, cnt, first = rebuild(shell)
        ok(rc_ == 2 and tbl is None, "[%s] boot with no copy at all: exit 2, no table (the helper hands out no include)" % tag)
finally:
    shutil.rmtree(work, ignore_errors=True)

# ---- pins in source
ok('fprintf(f, "[ \\"$DNS_CHANGED\\" = 1 ] && service restart_dnsmasq >/dev/null 2>&1\\nexit 0\\n");' in rw,
   "update.sh: a changed list restarts dnsmasq once at the end of the run, and the script exits 0")
ok('"\\"dns\\":%d,\\"dns_n\\":%d,\\"dns_upd\\":%d,\\"dns_live\\":%d}\\\\n\' "' in rw and '\\"$DNE\\" \\"$DN\\" \\"$DNU\\" \\"$DNL\\"' in rw,
   "stats.sh: the four dns keys are emitted with their values")
ok('"DN=$(cat " RW_DNS_COUNT " 2>/dev/null); case' in rw and '"  N=$(cat \\"$CNT\\" 2>/dev/null); case' in rw,
   "stats.sh / dns.sh: the name count comes from rc's count file (the table has no lines to count)")
helper = rw[rw.index("static const char rw_nx_rebuild_sh[] ="):rw.index("static void rw_dns_sync(void)")]
# review 2026-10-24 (Q-A-3, owner's call): the rebuild is DETACHED - dnsmasq starts at once and maps the table when it
# lands; the include is handed out whenever there is a copy to build from; one rebuild at a time (pid file)
ok("static void rw_nx_rebuild_bg(void)" in helper and 'char *argv[] = { "sh", "-c", (char *)rw_nx_rebuild_sh, NULL };' in helper
   and '_eval(argv, ">/dev/null", 0, &pid)' in helper and "if (pid > 0 && kill(pid, 0) == 0)\n\t\t\treturn;" in helper
   and '#define RW_NX_REBUILD_PID\tRW_DIR "/nx.rebuild.pid"' in helper
   and "if (!f_exists(RW_NX_DB)) {" in helper and "rw_nx_rebuild_bg();" in helper
   and "if (!f_exists(RW_DNS_KGZ) && !f_exists(RW_DNS_CACHE_GZ) && !f_exists(RW_DNS_CACHE) && !f_exists(RW_DNS_LEGACY))\n\t\t\treturn NULL;" in helper
   and 'eval("sh", "-c", (char *)rw_nx_rebuild_sh)' not in helper and 'logmessage("rwarden", "threat domains: the /jffs copy would not build' not in helper
   and 'fprintf(f, "reaper-hitlog=%s\\nreaper-nx-db=%s\\n", RW_HITS, RW_NX_DB);' in helper
   and "if (!f_exists(RW_DNS_CONF))\n\t\treturn NULL;" in helper and "rw_hits_dir();" in helper
   and helper.index("reaper_secure_dir(RW_DIR, 0700);") < helper.index("rw_nx_rebuild_bg();")
   and "else exit 2; fi" in helper and '[ -s $T.k ] || { rm -f $T.*; logger -t rwarden \\"threat domains: the /jffs copy would not build into a table' in helper
   and helper.count("the /jffs copy would not build into a table - blocking nothing until the next update") == 2,
   "reaper_warden_dns_conf: a missing table starts ONE detached rebuild from the /jffs copy (the script logs a copy that will not build; no copy = no include), hands out the two-line include meanwhile, prepares the hit directory")
ok('#define RW_DNS_CACHE_GZ RW_DNS_CACHE ".gz"' in rw and "RW_DNS_CAP=1000000\\n" in rw
   and 'RW_DPRIO=\\"urlhaus phish c2 threatfox crypto ransom certpl threatview\\"' in rw,
   "2026-10-22: limit 1,000,000; filled in priority order, Reaper's Basics first; the /jffs copy gzipped")
ok('#define RW_DNS_CACHE "/jffs/rwarden/dns.nx"' in rw and '#define RW_DNS_LEGACY "/jffs/rwarden/dns.cache"' in rw
   and '#define RW_NX_DB     RW_NX_DIR "/threat.db"' in rw and '#define RW_DNS_KGZ   "/jffs/rwarden/dns.k.gz"' in rw,
   "the counted list keeps its own /jffs names (an older firmware replays dns.cache verbatim), the table and the feeds list have theirs")
ok("_dvalid() { awk '(NF == 3 || NF == 4) && $1 ~ /^[0-9]+$/ && $2 ~ /^[0-9A-Fa-f.:-]+$/ && $3 ~ /^[a-z0-9.-]+$/ && (NF == 3 || $4 ~ /^[a-z0-9,-]+$/)'; }" in rw
   and 'if (NF >= 4 && $4 != \\"-\\") lf[$3]=$4;' in rw and "FILENAME==ARGV[3]" not in rw[rw.index("Dreadwatch hit collector"):],
   "dns.sh: a hit record carries the feed ids (4th field, charset-checked); attribution reads them, no text list is parsed")
hd = rw[rw.index("static void rw_hits_dir(void)"):rw.index("static const char rw_nx_rebuild_sh[] =")]
ok('getpwnam("nobody")' in hd and "lstat(RW_HITS_DIR, &st) != 0 || !S_ISDIR(st.st_mode)" in hd and "chown(RW_HITS_DIR, u, g)" in hd and "0700" in hd,
   "rw_hits_dir: a real directory (never through a link), owned by dnsmasq's run user, 0700")
ok('"[ -f " RW_DNSSH " ] && sh " RW_DNSSH " fold\\n"' in rw and rw.index('"[ -f " RW_DNSSH " ] && sh " RW_DNSSH " fold\\n"') < rw.index('"iptables -nL RW_DROP >/dev/null 2>&1 || exit 0\\n"'),
   "fold.sh banks the domain hits first, ahead of its IP-counter early exits")
ok(rw.index("rw_dns_sync();") < rw.index("if (!is_routing_enabled())"), "start_rwarden: the dnsmasq sync runs before the early returns (the off case included)")
ok('"  CURLG=\\"$CURLG --proto =https --proto-redir =https\\"\\n"' in rw, "update.sh: the geo fetch is redirect-pinned to https like the others")
ok("function ok(d) { return d ~ /^[a-z0-9]([a-z0-9-]{0,62}\\\\.)+[a-z][a-z0-9-]{0,62}$/ }" in rw and "NF == 1 { print tolower($1) }' | grep -E" not in rw
   and "{ sub(/\\\\r$/, \\\"\\\") }" in rw and "rw_dom() { tr -d" not in rw,
   "update.sh: a feed name needs a dot and a letter-led last label - checked inside the one parsing awk, which strips the CR too (review 2026-10-24 Q-A-1: no tr, no grep pass)")

for rel, needle, what in (
    ("rc/rc.h", "extern const char *reaper_warden_dns_conf(void);", "rc.h: the helper is declared for the two emitters"),
    ("rc/services.c", 'const char *wd = reaper_warden_dns_conf();\n\t\tif (wd)\n\t\t\tfprintf(fp, "conf-file=%s\\n", wd);', "services.c: the main instance includes the list only when the helper hands it out"),
    ("rc/sdn.c", 'const char *wd = reaper_warden_dns_conf();\n\t\t\tif (wd)\n\t\t\t\tfprintf(fp, "conf-file=%s\\n", wd);', "sdn.c: every guest/VLAN instance includes it under the same guard"),
    ("rc/rwatch.c", 'nslookup localhost 127.0.0.1 >/dev/null 2>&1 || { sleep 3; nslookup localhost 127.0.0.1 >/dev/null 2>&1; } || FAIL=', "rwatch check 2: one retry after 3 s, so a dnsmasq restart on the tick boundary is not an outage"),
    ("shared/defaults.c", '{ "rwarden_dns", "0", CKN_STR1', "defaults.c: the switch defaults off"),
    ("shared/defaults.c", '{ "rwarden_dns_feeds", "urlhaus phish c2 threatfox", CKN_STR64', "defaults.c: Reaper's Basics (URLhaus mirror, phishing, C2, the ThreatFox snapshot) selected once the switch goes on"),
    ("shared/reaper_tmpsafe.h", '{ "/tmp/reaper_nx",\t\t0755 }', "reaper_tmpsafe.h: the table's directory is root's, 0755 (dnsmasq, as nobody, only reads it)"),
    ("httpd/web.c", 'fopen("/tmp/rwarden/dns.first", "r")', "web.c: the self-test takes its sample name from rc's dns.first (no text list to parse)"),
    ("httpd/web.c", 'strcmp(name, "cfeeds") && strcmp(name, "dnsallow")) return 0;', "web.c: the page can read the dnsallow list"),
    ("httpd/web.c", '{ "ban", "allow", "cfeeds", "dnsallow", NULL };', "web.c: save_lists stores dnsallow"),
    ("httpd/web.c", '!strcmp(nv + 8, "cfeeds") || !strcmp(nv + 8, "dnsallow"))', "web.c: the settings export carries the dnsallow list"),
    ("httpd/web.c", '{ "warden", "rwarden_dns",      2   }, { "warden", "rwarden_dns_feeds", 64 },', "web.c: the switch and the list ids travel with a settings export"),
    # 2026-10-20: the settings moved to their own page, Dreadwatch (reviewer: a resolver answer and
    # an address drop are different enforcement points)
    ("www/Reaper_Dreadwatch.asp", "lf.append('dnsallow', dnsallow.ok);", "Dreadwatch: the exemptions ride the gated save_lists POST"),
    ("www/Reaper_Dreadwatch.asp", "if(dnsallow.bad.length){", "Dreadwatch: a bad exemption line refuses the whole save"),
    # 2026-10-21 (owner): the three default lists as one built-in row, "Reaper's Basics"
    ("www/Reaper_Dreadwatch.asp", "var DNS_BASICS = ['urlhaus','phish','c2','threatfox'];", "Dreadwatch: Reaper's Basics = the three live lists + the ThreatFox snapshot"),
    ("rc/rwarden.c", "threatfox ${RW_TFX:-/usr/share/dreadwatch/threatfox-snapshot.txt}", "update.sh: ThreatFox comes from the bundled snapshot file"),
    ("rc/rwarden.c", "then rw_dom < \\\"$2\\\" > $RW_DNSC.$1.last 2>/dev/null; echo \\\"$_sid\\\" > $RW_DNSC.$1.src; fi", "update.sh: a list given as a file is read, not fetched (and the parse is kept beside its date + size - review 2026-10-24 Q-A-4)"),
    ("www/Reaper_Dreadwatch.asp", 'id="fd_basics"', "Dreadwatch: one built-in row for the Basics (nothing on the tab is removable)"),
    ("www/Reaper_Dreadwatch.asp", "if(id === 'basics') DNS_BASICS.forEach(function(b){ dfeeds.push(b); }); else dfeeds.push(id);", "Dreadwatch: saving the Basics row writes its three ids"),
    ("www/Reaper_Dreadwatch.asp", "$('fd_'+id).checked = (id === 'basics') ? DNS_BASICS.some(function(b){ return !!dfs[b]; }) : !!dfs[id];", "Dreadwatch: the Basics row reads as on when any of its lists is on"),
    ("www/Reaper_Dreadwatch.asp", "if(updateNow || (dnsOn && changed && NV.warden === '1')){", "Dreadwatch: a changed domain setting fetches the list at once"),
    ("www/Reaper_Dreadwatch.asp", '<input type="hidden" name="rwarden_dns_feeds" value="">', "Dreadwatch: the list ids are applied through the form"),
    ("www/Reaper_Dreadwatch.asp", "function dwStats(){ dwGet('action=dns_status', dwRender); }", "Dreadwatch: the status follows the gated dns_status poll"),
):
    ok(needle in read(rel), what)
page = read("www/Reaper_Dreadwatch.asp")
rend = page[page.index("function dwRender(j){"):page.index("\n}\n", page.index("function dwRender(j){"))]
ok("innerHTML" not in rend and "innerHTML" not in page[page.index("function dwRows("):page.index("\n}\n", page.index("function dwRows("))],
   "Dreadwatch: everything the router reports is rendered with textContent")
wpage = read("www/Reaper_Warden.asp")
ok('name="rwarden_dns"' not in wpage and 'name="rwarden_dns_feeds"' not in wpage and "lf.append('dnsallow'" not in wpage and "rwDnsStat" not in wpage
   and 'href="/reaper_shell.asp#Reaper_Dreadwatch.asp"' in wpage,
   "Warden: no longer posts the domain switch, list ids or exemptions (a Warden save cannot change them) and points to Dreadwatch")

print("PASS: %d checks" % passed)
