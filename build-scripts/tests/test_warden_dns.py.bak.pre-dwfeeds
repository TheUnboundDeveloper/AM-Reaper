#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Warden threat domains (2026-10-19): URLhaus / ThreatFox hostfiles turned into dnsmasq
address=/host/ lines, included by every dnsmasq instance, restarted only when the list changed.

WHY THIS EXISTS. The list is built by shell inside a C string (rc/rwarden.c rw_gen_update) that
nothing runs before a build, and it is the one Reaper list that reaches the resolver every LAN
client uses: a bad parse blocks nothing or blocks the feed host itself (then no update can ever
run again), and a restart on every nightly run would drop every client's DNS for a second each
night for nothing. The include is also fatal to dnsmasq when the file is missing, so the C side
must hand it out only when the file exists - the SDN instances have no guard.

WHAT IT DOES. Lifts the block out of rc/rwarden.c (C literal, its own #defines resolved), runs
it under /bin/sh and busybox ash with fake curl/_nv/logger against fixture hostfiles: TAB and
space forms, CRLF, upper case, junk and dotless names dropped, the built-in never-block set, the
operator's exemptions, the DoT and LAN-domain names, the cap, keep-last-good per feed, no change
= no restart, a deselected feed, the switch off. Then pins the C side: the end-of-run restart
line and exit 0, the stats keys, the NULL-when-missing helper, the two instance emitters behind
it, the sync before the early returns, the CGI/export rows, the defaults, the page, the rwatch
check-2 retry and the CURLG redirect pin.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as argv[1]
or REAPER_ROUTER_SRC - or no /bin/sh).
"""
import os, re, shutil, subprocess, sys, tempfile

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

def lifted_script(csrc, needle, macros):
    at = csrc.find(needle)
    if at < 0: die("%r not found in the generator" % needle)
    start = csrc.rfind("fputs(", 0, at)
    end = csrc.find(", f);", at)
    if start < 0 or end < 0: die("could not frame the fputs() around %r" % needle)
    body = csrc[start + 6:end]
    text = ""
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|(/\*.*?\*/)|([A-Za-z_][A-Za-z0-9_]*)', body, re.S):
        if m.group(1) is not None:
            text += c_unescape(m.group(1))
        elif m.group(3) is not None:
            text += c_unescape(macros.get(m.group(3), ""))
    return text

rw = read("rc/rwarden.c")
macros = macros_of(rw)
for k in ("RW_DNS_CONF", "RW_DNS_CACHE", "RW_DNS_LEGACY", "RW_DNS_UPD", "RW_DNS_FEEDS", "RW_HITS", "RW_CACHE"):
    ok(k in macros, "rwarden.c defines %s" % k)
block = lifted_script(rw, "# ---- threat domains", macros)
SPLIT = 'if [ "$(_nv rwarden_dns)" = 1 ]; then\n'
ok(block.startswith("# ---- threat domains") and SPLIT in block and block.rstrip().endswith("fi"), "the threat-domain block lifts whole")
ok("RW_DNSC=/tmp/rwarden/dns.conf\n" in block and "RW_DNSK=/jffs/rwarden/dns.nx\n" in block and "RW_DNSL=/jffs/rwarden/dns.cache\n" in block
   and "RW_DNSF=/jffs/rwarden/dns.feeds\n" in block and "RW_DNSH=/tmp/dreadwatch/dns.hits\n" in block and "RW_DNSA=/jffs/rwarden/dnsallow\n" in block,
   "the block's paths come from the C defines (one source of truth)")
head_part, tail_part = block.split(SPLIT, 1)
tail_part = SPLIT + tail_part

URLHAUS = ("# abuse.ch URLhaus Host file\n# Last updated: 2026-10-19\n#\n"
           "127.0.0.1\tevil.example\n127.0.0.1\tEVIL2.EXAMPLE\r\n127.0.0.1\tsub.x.asuscomm.com\n127.0.0.1\tmine.example\n"
           "127.0.0.1\tbad_host.example\n127.0.0.1\tlocalhost\n0.0.0.0 space.example\n127.0.0.1\tdeep.dns.quad9.net\n")
THREATFOX = "# ThreatFox IOCs: host file\n127.0.0.1\tc2.example\n127.0.0.1\tevil.example\n127.0.0.1\tHome.LAN\n"
NV = {"rwarden_dns": "1", "rwarden_dns_feeds": "urlhaus threatfox", "lan_domain": "home.lan",
      "ddns_hostname_x": "my.asuscomm.com", "ntp_server0": "pool.ntp.org", "ntp_server1": "",
      "dnspriv_rulelist": "1.1.1.1>853>one.one.one.one><9.9.9.9>853>dns.quad9.net>"}

work = tempfile.mkdtemp(prefix="rwdns_")
try:
    bp = os.path.join(work, "block.sh"); open(bp, "w").write(block)
    r = subprocess.run([SH, "-n", bp], capture_output=True, text=True)
    ok(r.returncode == 0, "the block passes sh -n (%s)" % r.stderr.strip()[:200])
    if BB:
        r = subprocess.run([BB, "ash", "-n", bp], capture_output=True, text=True)
        ok(r.returncode == 0, "the block passes busybox ash -n (%s)" % r.stderr.strip()[:200])

    fix = os.path.join(work, "fix"); nvd = os.path.join(work, "nv"); logf = os.path.join(work, "logger.out")
    os.makedirs(fix); os.makedirs(nvd)
    open(os.path.join(fix, "urlhaus.txt"), "w", newline="").write(URLHAUS)
    open(os.path.join(fix, "threatfox.txt"), "w").write(THREATFOX)
    def setnv(k, v): open(os.path.join(nvd, k), "w").write(v)

    HEAD = r'''
_nv() { cat "$NVDIR/$1" 2>/dev/null; }
logger() { printf "%s\n" "$*" >> "$LOGF"; }
curl() {
  o=""; u=""; p=""
  for a in "$@"; do [ "$p" = -o ] && o="$a"; case "$a" in https://*) u="$a";; esac; p="$a"; done
  case "$u" in *urlhaus*) id=urlhaus;; *threatfox*) id=threatfox;; *) id=none;; esac
  case " $CURL_FAIL " in *" $id "*) return 22;; esac
  cp "$FIX/$id.txt" "$o"
}
CURL=curl
TMP=$WORK/feed.1
'''
    def run(shell, env_extra=None):
        wtmp = os.path.join(work, "tmp"); wjffs = os.path.join(work, "jffs")
        os.makedirs(wtmp, exist_ok=True); os.makedirs(wjffs, exist_ok=True)
        over = ('RW_DNSC=%s/dns.conf\nRW_DNSK=%s/dns.nx\nRW_DNSL=%s/dns.cache\nRW_DNSU=%s/dns.upd\nRW_DNSF=%s/dns.feeds\n'
                'RW_DNSH=/tmp/dreadwatch/dns.hits\nRW_DNSA=%s/dnsallow\nRW_DNS_CAP=${CAP:-100000}\n'
                % (wtmp, wjffs, wjffs, wtmp, wjffs, wjffs))
        sp = os.path.join(work, "run.sh")
        open(sp, "w").write(HEAD + head_part + over + tail_part + '\necho "DNS_CHANGED=$DNS_CHANGED"\n')
        env = dict(os.environ, NVDIR=nvd, LOGF=logf, FIX=fix, WORK=work, LC_ALL="C")
        env.update(env_extra or {})
        cmd = [shell, sp] if shell != "busybox" else [BB, "ash", sp]
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=work, timeout=60)
        if p.returncode != 0:
            die("block failed under %s:\n%s" % (shell, p.stderr[-800:]))
        changed = re.search(r"DNS_CHANGED=(\d)", p.stdout)
        conf = os.path.join(wtmp, "dns.conf")
        lines = open(conf).read().splitlines() if os.path.exists(conf) else None
        logs = open(logf).read().splitlines() if os.path.exists(logf) else []
        return (changed.group(1) if changed else "?"), lines, logs

    def reset_state():
        for d in ("tmp", "jffs"):
            shutil.rmtree(os.path.join(work, d), ignore_errors=True)
        if os.path.exists(logf): os.unlink(logf)
        for k, v in NV.items(): setnv(k, v)

    shells = [SH] + (["busybox"] if BB else [])
    for shell in shells:
        tag = "sh" if shell == SH else "ash"
        reset_state()
        os.makedirs(os.path.join(work, "jffs"), exist_ok=True)
        open(os.path.join(work, "jffs", "dnsallow"), "w").write("MINE.example, other.test\n")

        open(os.path.join(work, "jffs", "dns.cache"), "w").write("address=/legacy.example/\n")   # an older firmware's copy
        ch, lines, logs = run(shell)
        # 2026-10-20 (Dreadwatch): reaper-nx= lines in per-feed sections (C-locale order of the feed ids),
        # after a reaper-hitlog= line; a name both feeds list sits in the "urlhaus,threatfox" section
        ok(lines is not None and lines[0].startswith("#") and lines[1:] == [
               "reaper-hitlog=/tmp/dreadwatch/dns.hits",
               "# feed threatfox", "reaper-nx=/c2.example/",
               "# feed urlhaus", "reaper-nx=/evil2.example/", "reaper-nx=/space.example/",
               "# feed urlhaus,threatfox", "reaper-nx=/evil.example/"],
           "[%s] first run: TAB and space forms, CRLF and upper case normalised; junk, dotless, never-block, DoT, LAN-domain and exempted names out; reaper-nx=/host/ lines in per-feed sections behind the hit-log line (got %s)" % (tag, lines))
        ok(ch == "1" and os.path.exists(os.path.join(work, "jffs", "dns.nx")) and open(os.path.join(work, "jffs", "dns.nx")).read().splitlines() == lines
           and os.path.exists(os.path.join(work, "tmp", "dns.upd")), "[%s] first run: changed, /jffs copy equals the live list, stamp written" % tag)
        ok(not os.path.exists(os.path.join(work, "jffs", "dns.cache")),
           "[%s] the older firmware's address= copy is retired once the counted copy exists (a downgrade then rebuilds its own)" % tag)
        fm = {l.split()[0]: l.split() for l in open(os.path.join(work, "jffs", "dns.feeds")).read().splitlines()}
        ok(set(fm) == {"urlhaus", "threatfox"} and fm["urlhaus"][1:4] == ["1", "6", "3"] and fm["threatfox"][1:4] == ["1", "3", "2"]
           and fm["urlhaus"][6] == "ok" and fm["urlhaus"][4] == fm["urlhaus"][5] and int(fm["urlhaus"][4]) > 0,
           "[%s] feed metadata: selected, names downloaded, names kept in the list (a shared name counts for both), last-ok = last-try on success (got %s)" % (tag, fm))
        ok(len(logs) == 1 and "threat domains: 4 loaded (URLhaus 6, ThreatFox 3), 4 exempted or over the cap, list changed - dnsmasq restarts" in logs[0],
           "[%s] first run: one log line with the counts and the restart notice (%s)" % (tag, logs[:1]))
        ok(not any(n in " ".join(lines) for n in ("asuscomm", "quad9", "home.lan", "mine.example", "bad_host", "localhost")), "[%s] nothing from the never-block set reached the list" % tag)

        ch, lines2, logs = run(shell)
        ok(ch == "0" and lines2 == lines and len(logs) == 2 and "list changed" not in logs[1], "[%s] unchanged feeds: no restart, same list, log says so" % tag)

        okb = fm["urlhaus"][4]
        ch, lines3, logs = run(shell, {"CURL_FAIL": "urlhaus"})
        fm3 = {l.split()[0]: l.split() for l in open(os.path.join(work, "jffs", "dns.feeds")).read().splitlines()}
        ok(ch == "0" and lines3 == lines and any("urlhaus fetch FAILED - keeping the previous download" in l for l in logs[2:]),
           "[%s] one feed down: its previous download is kept, the list does not shrink, no restart" % tag)
        ok(fm3["urlhaus"][6] == "failed" and fm3["urlhaus"][4] == okb and fm3["threatfox"][6] == "ok",
           "[%s] feed metadata: a failed fetch says so and keeps the last good time (got %s)" % (tag, fm3["urlhaus"]))

        ch, lines4, logs = run(shell, {"CAP": "2"})
        ok(ch == "1" and [l for l in lines4 if l.startswith("reaper-nx=")] == ["reaper-nx=/c2.example/", "reaper-nx=/evil.example/"]
           and "2 loaded" in logs[-1] and "6 exempted or over the cap" in logs[-1],
           "[%s] the cap holds the first N sorted names and is counted" % tag)

        setnv("rwarden_dns_feeds", "urlhaus")
        ch, lines5, logs = run(shell)
        fm5 = {l.split()[0]: l.split() for l in open(os.path.join(work, "jffs", "dns.feeds")).read().splitlines()}
        ok(fm5["threatfox"][1] == "0" and fm5["threatfox"][6] == "off", "[%s] feed metadata: a deselected feed is off" % tag)
        ok(ch == "1" and lines5[1:] == ["reaper-hitlog=/tmp/dreadwatch/dns.hits", "# feed urlhaus", "reaper-nx=/evil.example/", "reaper-nx=/evil2.example/", "reaper-nx=/space.example/"]
           and not os.path.exists(os.path.join(work, "tmp", "dns.conf.threatfox.last")) and "(URLhaus 6, ThreatFox 0)" in logs[-1],
           "[%s] a deselected feed contributes nothing and its previous download is dropped (got %s)" % (tag, lines5))
        setnv("rwarden_dns_feeds", "urlhaus threatfox")

        reset_state(); setnv("rwarden_dns_feeds", "urlhaus threatfox")
        ch, lines6, logs = run(shell, {"CURL_FAIL": "urlhaus threatfox"})
        ok(ch == "0" and lines6 is None and any("nothing fetched and no previous download" in l for l in logs), "[%s] both feeds down on a fresh box: no list, no restart, said once" % tag)

        reset_state(); run(shell)
        setnv("rwarden_dns", "0")
        ch, lines7, logs = run(shell)
        ok(ch == "1" and lines7 is None and not [f for f in os.listdir(os.path.join(work, "tmp")) if f.endswith(".last")],
           "[%s] switch off with a list present: list and previous downloads removed, one restart" % tag)
        ch, lines8, logs = run(shell)
        ok(ch == "0" and lines8 is None, "[%s] switch off, nothing present: nothing to do" % tag)
finally:
    shutil.rmtree(work, ignore_errors=True)

# ---- pins in source
ok('fprintf(f, "[ \\"$DNS_CHANGED\\" = 1 ] && service restart_dnsmasq >/dev/null 2>&1\\nexit 0\\n");' in rw,
   "update.sh: a changed list restarts dnsmasq once at the end of the run, and the script exits 0")
ok('"\\"dns\\":%d,\\"dns_n\\":%d,\\"dns_upd\\":%d,\\"dns_live\\":%d}\\\\n\' "' in rw and '\\"$DNE\\" \\"$DN\\" \\"$DNU\\" \\"$DNL\\"' in rw,
   "stats.sh: the four dns keys are emitted with their values")
helper = rw[rw.index("const char *reaper_warden_dns_conf(void)"):rw.index("static void rw_dns_sync(void)")]
ok("const char *k = f_exists(RW_DNS_CACHE) ? RW_DNS_CACHE : f_exists(RW_DNS_LEGACY) ? RW_DNS_LEGACY : NULL;" in helper
   and "if (!k)\n\t\t\treturn NULL;" in helper and 'eval("cp", "-f", (char *)k, RW_DNS_CONF);' in helper
   and "if (!f_exists(RW_DNS_CONF))\n\t\t\treturn NULL;" in helper and "rw_hits_dir();" in helper,
   "reaper_warden_dns_conf: replays the counted /jffs copy (else an older firmware's), answers NULL when neither exists, prepares the hit directory")
ok('#define RW_DNS_CACHE "/jffs/rwarden/dns.nx"' in rw and '#define RW_DNS_LEGACY "/jffs/rwarden/dns.cache"' in rw,
   "the counted list has its own /jffs name - an older firmware replays dns.cache verbatim and would not start dnsmasq on reaper-nx=")
hd = rw[rw.index("static void rw_hits_dir(void)"):rw.index("const char *reaper_warden_dns_conf(void)")]
ok('getpwnam("nobody")' in hd and "lstat(RW_HITS_DIR, &st) != 0 || !S_ISDIR(st.st_mode)" in hd and "chown(RW_HITS_DIR, u, g)" in hd and "0700" in hd,
   "rw_hits_dir: a real directory (never through a link), owned by dnsmasq's run user, 0700")
ok('"[ -f " RW_DNSSH " ] && sh " RW_DNSSH " fold\\n"' in rw and rw.index('"[ -f " RW_DNSSH " ] && sh " RW_DNSSH " fold\\n"') < rw.index('"iptables -nL RW_DROP >/dev/null 2>&1 || exit 0\\n"'),
   "fold.sh banks the domain hits first, ahead of its IP-counter early exits")
ok(rw.index("rw_dns_sync();") < rw.index("if (!is_routing_enabled())"), "start_rwarden: the dnsmasq sync runs before the early returns (the off case included)")
ok('"  CURLG=\\"$CURLG --proto =https --proto-redir =https\\"\\n"' in rw, "update.sh: the geo fetch is redirect-pinned to https like the others")
ok("grep -E '^[a-z0-9]([a-z0-9-]{0,62}\\\\.)+[a-z][a-z0-9-]{0,62}$'" in rw, "update.sh: a feed name needs a dot and a letter-led last label")

for rel, needle, what in (
    ("rc/rc.h", "extern const char *reaper_warden_dns_conf(void);", "rc.h: the helper is declared for the two emitters"),
    ("rc/services.c", 'const char *wd = reaper_warden_dns_conf();\n\t\tif (wd)\n\t\t\tfprintf(fp, "conf-file=%s\\n", wd);', "services.c: the main instance includes the list only when the helper hands it out"),
    ("rc/sdn.c", 'const char *wd = reaper_warden_dns_conf();\n\t\t\tif (wd)\n\t\t\t\tfprintf(fp, "conf-file=%s\\n", wd);', "sdn.c: every guest/VLAN instance includes it under the same guard"),
    ("rc/rwatch.c", 'nslookup localhost 127.0.0.1 >/dev/null 2>&1 || { sleep 3; nslookup localhost 127.0.0.1 >/dev/null 2>&1; } || FAIL=', "rwatch check 2: one retry after 3 s, so a dnsmasq restart on the tick boundary is not an outage"),
    ("shared/defaults.c", '{ "rwarden_dns", "0", CKN_STR1', "defaults.c: the switch defaults off"),
    ("shared/defaults.c", '{ "rwarden_dns_feeds", "urlhaus threatfox", CKN_STR32', "defaults.c: both lists selected once the switch goes on"),
    ("httpd/web.c", 'strcmp(name, "cfeeds") && strcmp(name, "dnsallow")) return 0;', "web.c: the page can read the dnsallow list"),
    ("httpd/web.c", '{ "ban", "allow", "cfeeds", "dnsallow", NULL };', "web.c: save_lists stores dnsallow"),
    ("httpd/web.c", '!strcmp(nv + 8, "cfeeds") || !strcmp(nv + 8, "dnsallow"))', "web.c: the settings export carries the dnsallow list"),
    ("httpd/web.c", '{ "warden", "rwarden_dns",      2   }, { "warden", "rwarden_dns_feeds", 32 },', "web.c: the switch and the list ids travel with a settings export"),
    # 2026-10-20: the settings moved to their own page, Dreadwatch (reviewer: a resolver answer and
    # an address drop are different enforcement points)
    ("www/Reaper_Dreadwatch.asp", "lf.append('dnsallow', dnsallow.ok);", "Dreadwatch: the exemptions ride the gated save_lists POST"),
    ("www/Reaper_Dreadwatch.asp", "if(dnsallow.bad.length){", "Dreadwatch: a bad exemption line refuses the whole save"),
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
