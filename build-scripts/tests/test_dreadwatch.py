#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dreadwatch (threat domains, 2026-10-20): every blocked lookup is counted, per feed, name and device.

WHY THIS EXISTS. Reviewer feedback: "a control whose effect can't be independently measured can't be
trusted" - the threat-domain list answered NXDOMAIN and kept no record of doing so. The fix spans three
places nothing else exercises before metal: a dnsmasq patch (--reaper-nx= entries, which answer exactly
like address=/x/, and --reaper-hitlog=, one record per answer from such an entry, bounded), the shell
collector rc/rwarden.c generates (dns.sh: fold the records into per-feed / per-name / per-client
counters on /jffs, report them as JSON, reset), and the Dreadwatch page + CGI.

WHAT IT DOES.
  1. Lifts dns.sh out of rc/rwarden.c and runs it under /bin/sh and busybox ash against fixtures:
     attribution by the feed ids the record carries (2026-10-24, from the compiled table's list bits; a name
     in two feeds counts for both; a record without them keeps the feed the name was banked under), invalid
     records dropped, "# dropped N" banked, banked + new merged on the next fold, a fold with nothing new
     does not touch /jffs, the 500-line recent log, the JSON (newest first, top lists sorted, junk never
     emitted), the stats-save opt-out (counters in /tmp), the retention reset, the operator reset.
  2. Builds the patched dnsmasq for the host in a temporary copy (never in the tree) and runs it: a listed
     name, a subdomain, AAAA and TCP answer NXDOMAIN and are recorded under the LISTED name with the client
     address (and "-" for the feed: a reaper-nx= entry names none - the table path is test_reaper_nx.py's);
     local=/lan/ and address=/x/ answers are not recorded; the 50-a-second bound reports the
     excess as one "# dropped" line; the 256 KB bound holds; a moved file is recreated; reaper-nx= with
     an answer is a config error.
  3. Pins the wiring: the C helpers, the CGI actions, the page, the menu, the markers.
Exit 0 pass, 1 fail, 77 skipped (no router source tree, or no /bin/sh).
"""
import json, os, re, shutil, socket, struct, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

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
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()

# ---- the C-literal lifter (test_warden_dns.py's shape)
def macros_of(src):
    m = {}
    for line in src.splitlines():
        mm = re.match(r'\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$', line)
        if not mm: continue
        name, rest = mm.group(1), re.sub(r"/\*.*?\*/", "", mm.group(2))
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"|([A-Za-z_][A-Za-z0-9_]*)', rest)
        if not parts or not any(s for s, _ in parts): continue
        val, okay = "", True
        for s, ident in parts:
            if ident:
                if ident in m: val += m[ident]
                else: okay = False; break
            else: val += s
        if okay: m[name] = val
    return m

def c_unescape(s):
    out, i = [], 0
    table = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "'": "'", "?": "?", "a": "\a", "r": "\r"}
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in "01234567":
                j = i + 1
                while j < len(s) and j < i + 4 and s[j] in "01234567": j += 1
                out.append(chr(int(s[i + 1:j], 8))); i = j
            else:
                out.append(table.get(nxt, "\\" + nxt)); i += 2
        else:
            out.append(s[i]); i += 1
    return "".join(out)

def lifted_script(csrc, needle, macros):
    at = csrc.find(needle)
    start = csrc.rfind("fputs(", 0, at); end = csrc.find(", f);", at)
    if at < 0 or start < 0 or end < 0:
        return None
    text = ""
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|(/\*.*?\*/)|([A-Za-z_][A-Za-z0-9_]*)', csrc[start + 6:end], re.S):
        if m.group(1) is not None: text += c_unescape(m.group(1))
        elif m.group(3) is not None: text += c_unescape(macros.get(m.group(3), ""))
    return text

rw = read("rc/rwarden.c")
macros = macros_of(rw)
macros.update(macros_of(read("shared/reaper_store.h").replace("\\\n", " ")))	# RSTORE_SH_DIR (2026-10-21), a multi-line define
script = lifted_script(rw, "# ---- Dreadwatch hit collector", macros)
check("dns.sh lifts whole out of rw_gen_dns", script is not None and "dfold() {" in script and "dstats() {" in script and "dreset() {" in script)
if script is None:
    print("\n".join(fails)); sys.exit(1)
for k, v in (("HF", "/tmp/dreadwatch/dns.hits"), ("CONF", "/tmp/rwarden/dns.conf"), ("DCTR", "/jffs/rwarden/dns.counters"),
             ("FEEDS", "/jffs/rwarden/dns.feeds"), ("REC", "/tmp/rwarden/dns.recent"), ("UPD", "/tmp/rwarden/dns.upd")):
    check("dns.sh: %s comes from the C define (%s)" % (k, v), ("\n%s=%s\n" % (k, v)) in script)

# 2026-10-24: the include is two lines (the names live in the compiled table), and each record carries the
# feed ids of the entry that matched; a record with a fifth field or a bad feed charset is junk
CONF = "reaper-hitlog=/tmp/dreadwatch/dns.hits\nreaper-nx-db=/tmp/reaper_nx/threat.db\n"
HITS1 = ("1792500000 192.168.50.10 evil.example urlhaus,threatfox\n1792500001 192.168.50.10 evil.example urlhaus,threatfox\n"
         "1792500002 192.168.50.20 c2.example threatfox\n"
         "# dropped 5\nnot a record\n1792500003 192.168.50.20 BAD\"name threatfox\n1792500004 192.168.50.30 evil2.example extra junk\n"
         "1792500005 192.168.50.30 evil2.example Bad\"feed\n")

CC = shutil.which("gcc") or shutil.which("cc")
def build_rstore(dest, mnt, jffs):
    """the no-follow store writer (wallguard/rstore.c) for the host, trusting a temp tree"""
    r = subprocess.run([CC, "-std=gnu99", "-I", os.path.join(SRC, "shared"), '-DRSTORE_TRUST_MNT="%s"' % mnt,
                        '-DRSTORE_TRUST_JFFS="%s"' % jffs, "-DRSTORE_NEED_MOUNT=0", "-o", dest, os.path.join(SRC, "wallguard", "rstore.c")],
                       capture_output=True, text=True)
    return r.returncode == 0

work = tempfile.mkdtemp(prefix="dreadw_")
try:
    J = os.path.join(work, "jffs"); T = os.path.join(work, "tmp"); HD = os.path.join(work, "hits"); NV = os.path.join(work, "nv")
    def setnv(k, v): open(os.path.join(NV, k), "w").write(v)
    def run(shell, mode, extra=None):
        body = re.sub(r"^(HF|CONF|CNT|DCTR|FEEDS|REC|UPD)=.*$", lambda m: {
            "HF": "HF=%s/dns.hits" % HD, "CONF": "CONF=%s/dns.conf" % T, "CNT": "CNT=%s/dns.count" % T, "DCTR": "DCTR=%s/dns.counters" % J,
            "FEEDS": "FEEDS=%s/dns.feeds" % J, "REC": "REC=%s/dns.recent" % T, "UPD": "UPD=%s/dns.upd" % T}[m.group(1)],
            script, flags=re.M)
        body = body.replace("LOCK=/tmp/rwarden/dns.lock", "LOCK=%s/dns.lock" % T)
        body = body.replace("DCTR=/tmp/rwarden/dns.counters", "DCTR=%s/dns.counters.tmpfs" % T)
        body = body.replace("W=/tmp/rwarden/dns.work.$$", "W=%s/dns.work.$$" % T)
        head = '_nv() { cat "$NVDIR/$1" 2>/dev/null; }\nlogger() { printf "%s\\n" "$*" >> "$LOGF"; }\n'
        sp = os.path.join(work, "dns.sh"); open(sp, "w").write(head + body)
        env = dict(os.environ, NVDIR=NV, LOGF=os.path.join(work, "logger.out"), LC_ALL="C", **(extra or {}))
        cmd = [shell, sp, mode] if shell != "busybox" else [BB, "ash", sp, mode]
        return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    def ctr(path=None):
        p = path or os.path.join(J, "dns.counters")
        return open(p).read().splitlines() if os.path.exists(p) else []

    r = subprocess.run([SH, "-n", "/dev/stdin"], input=script, capture_output=True, text=True)
    check("dns.sh passes sh -n", r.returncode == 0, r.stderr)
    if BB:
        r = subprocess.run([BB, "ash", "-n", "/dev/stdin"], input=script, capture_output=True, text=True)
        check("dns.sh passes busybox ash -n", r.returncode == 0, r.stderr)

    for shell in [SH] + (["busybox"] if BB else []):
        tag = "sh" if shell == SH else "ash"
        for d in (J, T, HD, NV):
            shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        for k, v in (("rwarden_enable", "1"), ("rwarden_dns", "1"), ("rwarden_stats_save", "1"), ("rwarden_reset", "off")):
            setnv(k, v)
        open(os.path.join(T, "dns.conf"), "w").write(CONF)
        open(os.path.join(T, "dns.count"), "w").write("2\n")   # rc's count of the names in the table
        open(os.path.join(J, "dns.feeds"), "w").write("urlhaus 1 6 2 1792400000 1792400000 ok\nthreatfox 1 3 2 1792400000 1792400000 ok\nbad\"id 1 1 1 1 1 ok\n")
        open(os.path.join(HD, "dns.hits"), "w").write(HITS1)

        r = run(shell, "fold")
        c = ctr()
        check("[%s] fold: the records are moved away from dnsmasq's directory" % tag, r.returncode == 0 and not os.path.exists(os.path.join(HD, "dns.hits")), r.stderr)
        check("[%s] fold: TOTAL counts the valid records only; DROPPED banks dnsmasq's '# dropped' lines" % tag,
              "TOTAL 3" in c and "DROPPED 5" in c, c)
        check("[%s] fold: per feed by the record's ids - a name in two feeds counts for both" % tag,
              "FEED urlhaus 2" in c and "FEED threatfox 3" in c, c)
        check("[%s] fold: per name with its feeds and last time, per client with its last time" % tag,
              "NAME evil.example 2 urlhaus,threatfox 1792500001" in c and "NAME c2.example 1 threatfox 1792500002" in c
              and "CLIENT 192.168.50.10 2 1792500001" in c and "CLIENT 192.168.50.20 1 1792500002" in c, c)
        check("[%s] fold: a malformed record (quote, fifth field, bad feed charset, junk) never reaches the counters" % tag,
              not any("BAD" in l or "extra" in l or "Bad" in l or "192.168.50.30" in l for l in c), c)
        rec = open(os.path.join(T, "dns.recent")).read().splitlines()
        check("[%s] fold: the recent log holds the three valid records" % tag, len(rec) == 3 and rec[-1].split()[2] == "c2.example", rec)

        mt = os.path.getmtime(os.path.join(J, "dns.counters"))
        time.sleep(1.1)
        r = run(shell, "fold")
        check("[%s] fold with nothing new: /jffs is not rewritten" % tag, os.path.getmtime(os.path.join(J, "dns.counters")) == mt and ctr() == c)

        # review 2026-10-24 (S-A-6): a directory or a link planted at the hit file is dropped unread, nothing left behind
        os.makedirs(os.path.join(HD, "dns.hits"))
        r = run(shell, "fold")
        check("[%s] fold: a directory at the hit file is removed unread, no work directory stays, the counters stand" % tag,
              r.returncode == 0 and not os.path.exists(os.path.join(HD, "dns.hits")) and not [f for f in os.listdir(T) if f.startswith("dns.work")] and ctr() == c,
              (r.stderr, os.listdir(T)))
        secret = os.path.join(work, "secret.txt"); open(secret, "w").write("1792500009 10.0.0.9 leaked.example -\n")
        os.symlink(secret, os.path.join(HD, "dns.hits"))
        run(shell, "fold")
        check("[%s] fold: a link at the hit file is never read through (the target stays, nothing of it is counted)" % tag,
              os.path.exists(secret) and "leaked.example" not in open(os.path.join(J, "dns.counters")).read() and not os.path.exists(os.path.join(HD, "dns.hits")))

        # a three-field record (an older dnsmasq's form) is still taken
        open(os.path.join(HD, "dns.hits"), "w").write("1792500100 192.168.50.10 evil.example urlhaus,threatfox\n1792500101 fe80::1 gone.example\n")
        r = run(shell, "fold")
        c = ctr()
        check("[%s] fold: banked + new are merged; an IPv6 client is counted" % tag,
              "TOTAL 5" in c and "NAME evil.example 3 urlhaus,threatfox 1792500100" in c and "CLIENT fe80::1 1 1792500101" in c, c)
        check("[%s] fold: a record naming no feed, for a name never banked, is counted unattributed" % tag,
              "NAME gone.example 1 - 1792500101" in c and "FEED - 1" in c, c)
        # a record without feed ids for a banked name keeps the feed it was banked under
        open(os.path.join(HD, "dns.hits"), "w").write("1792500200 192.168.50.20 c2.example\n")
        run(shell, "fold"); c = ctr()
        check("[%s] fold: a record without feed ids keeps the feed the name was banked under" % tag,
              "NAME c2.example 2 threatfox 1792500200" in c and "FEED threatfox 5" in c, c)

        r = run(shell, "stats")
        try:
            j = json.loads(r.stdout)
        except Exception as e:
            j = None
            check("[%s] stats: valid JSON" % tag, False, "%s %s" % (e, r.stdout[:400]))
        if j:
            check("[%s] stats: valid JSON with the state, list size and pending count" % tag,
                  j["ok"] == 1 and j["enable"] == 1 and j["hitlog"] == 1 and j["names"] == 2 and j["pending"] == 0, j)
            check("[%s] stats: per-feed metadata (junk lines skipped)" % tag,
                  [f["id"] for f in j["feeds"]] == ["urlhaus", "threatfox"] and j["feeds"][0]["kept"] == 2 and j["feeds"][0]["st"] == "ok", j["feeds"])
            check("[%s] stats: totals and per-feed counts" % tag,
                  j["total"] == 6 and j["dropped"] == 5 and {f["id"]: f["n"] for f in j["fcount"]} == {"urlhaus": 3, "threatfox": 5, "-": 1}, j)
            check("[%s] stats: top names sorted by count, with feeds" % tag,
                  [t["d"] for t in j["top"]][:2] == ["evil.example", "c2.example"] and j["top"][0]["n"] == 3 and j["top"][0]["f"] == "urlhaus,threatfox", j["top"])
            check("[%s] stats: top devices sorted by count" % tag, j["clients"][0]["ip"] == "192.168.50.10" and j["clients"][0]["n"] == 3, j["clients"])
            check("[%s] stats: recent lookups newest first" % tag,
                  [x["d"] for x in j["recent"]][:2] == ["c2.example", "gone.example"] and j["recent"][0]["t"] == 1792500200, j["recent"][:3])
            check("[%s] stats: coverage hints present (DNS Director, DoH canary)" % tag, "director" in j and "canary" in j)
        # a counters file that someone edited: junk is never emitted
        with open(os.path.join(J, "dns.counters"), "a") as f:
            f.write('NAME bad"name 9 urlhaus 1\nCLIENT x"y 9 1\nFEED bad"id 9\n')
        r = run(shell, "stats")
        check("[%s] stats: a quote or other junk in the counters file never reaches the JSON" % tag,
              r.returncode == 0 and '"' not in "".join(re.findall(r'"d":"([^"]*)"', r.stdout)) and "bad" not in r.stdout and json.loads(r.stdout)["ok"] == 1, r.stdout[:300])

        # retention: the Warden interval applies
        open(os.path.join(J, "dns.counters"), "w").write("SINCE 1000\nTOTAL 7\n")
        setnv("rwarden_reset", "24h")
        run(shell, "fold"); c = ctr()
        check("[%s] retention: past the Warden interval the counters restart" % tag,
              len(c) == 1 and c[0].startswith("SINCE ") and int(c[0].split()[1]) > 1000, c)
        setnv("rwarden_reset", "off")
        # stats-save opt-out: counters live in tmpfs, /jffs untouched
        setnv("rwarden_stats_save", "0")
        jbefore = ctr()
        open(os.path.join(HD, "dns.hits"), "w").write("1792500300 192.168.50.10 evil.example\n")
        run(shell, "fold")
        check("[%s] stats saving off: the counters are kept in /tmp and /jffs is not written" % tag,
              ctr() == jbefore and "TOTAL 1" in ctr(os.path.join(T, "dns.counters.tmpfs")), ctr(os.path.join(T, "dns.counters.tmpfs")))
        setnv("rwarden_stats_save", "1")
        # operator reset
        open(os.path.join(HD, "dns.hits"), "w").write("1792500400 192.168.50.10 evil.example\n")
        r = run(shell, "reset"); c = ctr()
        check("[%s] reset: the store restarts, the recent log and pending records go" % tag,
              len(c) == 1 and c[0].startswith("SINCE ") and not os.path.exists(os.path.join(T, "dns.recent")) and not os.path.exists(os.path.join(HD, "dns.hits")), c)
        check("[%s] reset: logged" % tag, "Dreadwatch counters reset by the operator" in open(os.path.join(work, "logger.out")).read())
        # the recent log is bounded
        open(os.path.join(HD, "dns.hits"), "w").write("".join("%d 10.0.0.1 evil.example\n" % (1792600000 + i) for i in range(620)))
        run(shell, "fold")
        rec = open(os.path.join(T, "dns.recent")).read().splitlines()
        check("[%s] the recent log keeps the last 500 records" % tag, len(rec) == 500 and rec[-1].startswith("1792600619 "), len(rec))

        # Long-Term Storage (2026-10-21): "Dreadwatch blocked lookups" appended on the store; the
        # watchdog's published location is faked through the RSTORE_* variables
        shutil.rmtree(os.path.join(work, "st"), ignore_errors=True)
        st = os.path.join(work, "st", "VOL", ".reaper"); os.makedirs(st)
        open(os.path.join(st, "store.id"), "w").write("abcdef0123456789")
        pub, mts = os.path.join(work, "store.base"), os.path.join(work, "mounts")
        open(mts, "w").write("/dev/sda1 %s ext4 rw 0 0\n" % os.path.dirname(st))
        rsx = os.path.join(work, "rstore")
        if not os.path.exists(rsx): build_rstore(rsx, os.path.join(work, "st"), os.path.join(work, "stj"))
        lts = dict(RSTORE_PUB_F=pub, RSTORE_MNT_D=os.path.join(work, "st"), RSTORE_MOUNTS=mts, RSTORE=rsx)
        hl = os.path.join(st, "dreadwatch", "blocked.log")
        open(pub, "w").write("%s\n,dev,\n" % st)
        open(os.path.join(HD, "dns.hits"), "w").write("1792700000 192.168.50.10 evil.example\n")
        run(shell, "fold", lts)
        check("[%s] LTS: Dreadwatch blocked lookups not ticked - nothing written to the store" % tag, not os.path.exists(hl))
        open(pub, "w").write("%s\n,dev,dw,\n" % st)
        open(os.path.join(HD, "dns.hits"), "w").write("1792700001 192.168.50.10 evil.example\n# dropped 2\n1792700002 192.168.50.20 BAD\"x\n")
        run(shell, "fold", lts)
        check("[%s] LTS: ticked - the validated records (only) are appended on the store" % tag,
              os.path.exists(hl) and open(hl).read() == "1792700001 192.168.50.10 evil.example\n", open(hl).read() if os.path.exists(hl) else None)
        j = json.loads(run(shell, "stats", lts).stdout)
        check("[%s] LTS: stats says the history goes to USB volume VOL" % tag, j.get("hist") == "usb" and j.get("histvol") == "VOL", j.get("hist"))
        open(mts, "w").write("")
        j = json.loads(run(shell, "stats", lts).stdout)
        check("[%s] LTS: volume unmounted - no history destination reported" % tag, j.get("hist") == "", j.get("hist"))

    # ---- 2. the patched dnsmasq, built for the host in a temporary copy
    CC = shutil.which("gcc") or shutil.which("cc")
    DSRC = os.path.join(SRC, "dnsmasq")
    if not CC or not os.path.isfile(os.path.join(DSRC, "Makefile")):
        print("note: no host compiler or no dnsmasq source - the dnsmasq hook run is skipped")
    else:
        db = os.path.join(work, "dnsmasq")
        shutil.copytree(DSRC, db, symlinks=True, ignore=shutil.ignore_patterns("*.o", "dnsmasq"))
        b = subprocess.run(["make", "-C", db, "COPTS=-DNO_DBUS -DNO_INOTIFY", "CC=" + CC, "-j4"], capture_output=True, text=True, timeout=900)
        BIN = os.path.join(db, "src", "dnsmasq")
        check("the patched dnsmasq builds for the host", b.returncode == 0 and os.path.exists(BIN), (b.stdout + b.stderr)[-800:])
        warn = [l for l in (b.stdout + b.stderr).splitlines() if "warning" in l and re.search(r"(domain-match|forward|option|edns0)\.c|dnsmasq\.h", l)]
        check("...without warnings from the patched files", not warn, warn[:5])
        if os.path.exists(BIN):
            hits = os.path.join(work, "dhits", "dns.hits"); os.makedirs(os.path.dirname(hits))
            port = 5399
            conf = os.path.join(work, "d.conf")
            open(conf, "w").write("port=%d\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\npid-file=\n"
                                  "local=/lan/\naddress=/old.example/\nreaper-hitlog=%s\nreaper-nx=/bad.example/\nreaper-nx=/two.test/three.test/\n" % (port, hits))
            p = subprocess.Popen([BIN, "-k", "-C", conf, "--log-facility=-"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.7)
            def q(name, qtype=1, tcp=False):
                msg = struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0) + b"".join(bytes([len(l)]) + l.encode() for l in name.split(".")) + b"\0" + struct.pack(">HH", qtype, 1)
                if tcp:
                    s = socket.create_connection(("127.0.0.1", port), timeout=2); s.sendall(struct.pack(">H", len(msg)) + msg); rr = s.recv(4096)[2:]; s.close()
                else:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(2); s.sendto(msg, ("127.0.0.1", port)); rr = s.recv(4096); s.close()
                return rr[3] & 0x0f
            try:
                rc = [q("bad.example"), q("x.y.bad.example"), q("bad.example", 28), q("www.three.test", tcp=True), q("printer.lan"), q("old.example")]
                time.sleep(0.2)
                ln = open(hits).read().splitlines() if os.path.exists(hits) else []
                check("dnsmasq: reaper-nx answers NXDOMAIN like address= (name, subdomain, AAAA, TCP)", rc[:4] == [3, 3, 3, 3], rc)
                check("dnsmasq: each answer is recorded under the LISTED name with the client address ('-' for the feed: a reaper-nx= entry names none)",
                      [l.split()[1:] for l in ln] == [["127.0.0.1", "bad.example", "-"]] * 3 + [["127.0.0.1", "three.test", "-"]], ln)
                check("dnsmasq: local=/lan/ and address=/x/ answers are not recorded", rc[4:] == [3, 3] and len(ln) == 4, ln)
                for i in range(120): q("r%d.bad.example" % i)
                time.sleep(1.1); q("after.bad.example"); time.sleep(0.1)
                ln = open(hits).read().splitlines()
                dl = [l for l in ln if l.startswith("# dropped ")]
                # 2026-10-25 (suite flake: 70 recorded + 56 dropped): the limiter's 50-a-second window runs on dnsmasq's own clock
                # (uptime in this no-RTC build), whose second boundary is not the records' wall-clock one, so a burst under a second
                # can touch two windows - up to 100 records, the rest dropped. What always holds: nothing is lost (recorded + dropped =
                # the 120 asked), something was dropped, and no more than two windows' worth was recorded. Records carry the LISTED
                # name, so the burst is counted by position: every record but the 4 above and the 'after.' one.
                recs = [l for l in ln if not l.startswith("#")]
                nb = len(recs) - 4 - 1
                dropped = sum(int(d.split()[2]) for d in dl)
                check("dnsmasq: at most 50 records a second; the excess is counted on '# dropped N' lines riding the next record",
                      bool(dl) and nb <= 100 and nb + dropped == 120, (nb, dl))
                with open(hits, "a") as f: f.write("x" * (256 * 1024))
                sz = os.path.getsize(hits); time.sleep(1.1); q("capped.bad.example"); time.sleep(0.1)
                check("dnsmasq: the file stops growing at 256 KB", os.path.getsize(hits) == sz)
                os.rename(hits, hits + ".work"); time.sleep(1.1); q("fresh.bad.example"); time.sleep(0.1)
                fr = open(hits).read().splitlines()
                check("dnsmasq: a file the collector moved away is recreated (and the record it could not write is reported)",
                      fr[0] == "# dropped 1" and fr[1].endswith("127.0.0.1 bad.example -"), fr)
            finally:
                p.terminate(); p.wait(timeout=5)
            bad = os.path.join(work, "bad.conf"); open(bad, "w").write("port=%d\nreaper-nx=/x.example/1.2.3.4\n" % (port + 1))
            r = subprocess.run([BIN, "--test", "-C", bad], capture_output=True, text=True)
            check("dnsmasq: reaper-nx= with an answer is a configuration error", r.returncode != 0 and "reaper-nx" in (r.stdout + r.stderr), r.stdout + r.stderr)

            # ---- 2b. Encrypted DNS (2026-10-21): rednsd names the device in EDNS0 option 65400.
            # Believed only from loopback; cut out of every query so it never reaches an upstream.
            import threading
            REAPER_OPT = 65400
            hits2 = os.path.join(work, "dhits2", "dns.hits"); os.makedirs(os.path.dirname(hits2))
            port2, up = 5397, 5396
            seen = []
            def answer(msg):
                return msg[:2] + bytes([0x81, 0x80]) + msg[4:6] + b"\0\0\0\0\0\0" + msg[12:12 + qlen(msg)]
            def qlen(msg):
                i = 12
                while msg[i]: i += msg[i] + 1
                return i + 1 + 4 - 12
            def opts_of(msg):
                """The EDNS0 options of a query with one question and no answers: [(code, data)], or None."""
                i = 12 + qlen(msg)
                for _ in range(struct.unpack(">H", msg[10:12])[0]):
                    if msg[i] != 0: return None
                    t, _c, _ttl, rdl = struct.unpack(">HHIH", msg[i + 1:i + 11]); i += 11
                    if t == 41:
                        out, j = [], i
                        while j + 4 <= i + rdl:
                            c, l = struct.unpack(">HH", msg[j:j + 4]); out.append((c, msg[j + 4:j + 4 + l])); j += 4 + l
                        return out
                    i += rdl
                return None
            us = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); us.bind(("127.0.0.1", up)); us.settimeout(0.5)
            ut = socket.socket(socket.AF_INET, socket.SOCK_STREAM); ut.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            ut.bind(("127.0.0.1", up)); ut.listen(4); ut.settimeout(0.5)
            stop = threading.Event()
            def serve_udp():
                while not stop.is_set():
                    try: m, a = us.recvfrom(4096)
                    except socket.timeout: continue
                    seen.append(("udp", m)); us.sendto(answer(m), a)
            def serve_tcp():
                while not stop.is_set():
                    try: c, _ = ut.accept()
                    except socket.timeout: continue
                    c.settimeout(2)
                    try:
                        while True:
                            h = c.recv(2)
                            if len(h) < 2: break
                            m = c.recv(struct.unpack(">H", h)[0]); seen.append(("tcp", m))
                            a = answer(m); c.sendall(struct.pack(">H", len(a)) + a)
                    except OSError:
                        pass
                    c.close()
            th = [threading.Thread(target=f, daemon=True) for f in (serve_udp, serve_tcp)]
            for t in th: t.start()
            conf2 = os.path.join(work, "d2.conf")
            open(conf2, "w").write("port=%d\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\npid-file=\n"
                                   "server=/fwd.test/127.0.0.1#%d\nreaper-hitlog=%s\nreaper-nx=/bad.example/\n" % (port2, up, hits2))
            p2 = subprocess.Popen([BIN, "-k", "-C", conf2, "--log-facility=-"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.7)
            def qo(name, opts=(), tcp=False):
                msg = struct.pack(">HHHHHH", 0x4321, 0x0100, 1, 0, 0, 1 if opts is not None else 0) + \
                      b"".join(bytes([len(l)]) + l.encode() for l in name.split(".")) + b"\0" + struct.pack(">HH", 1, 1)
                if opts is not None:
                    rd = b"".join(struct.pack(">HH", c, len(d)) + d for c, d in opts)
                    msg += b"\0" + struct.pack(">HHIH", 41, 1232, 0, len(rd)) + rd
                if tcp:
                    s = socket.create_connection(("127.0.0.1", port2), timeout=2); s.sendall(struct.pack(">H", len(msg)) + msg); rr = s.recv(4096)[2:]; s.close()
                else:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(2); s.sendto(msg, ("127.0.0.1", port2)); rr = s.recv(4096); s.close()
                return rr[3] & 0x0f
            v4 = lambda a: bytes([1]) + socket.inet_pton(socket.AF_INET, a)
            v6 = lambda a: bytes([2]) + socket.inet_pton(socket.AF_INET6, a)
            try:
                rc2 = [qo("bad.example", [(REAPER_OPT, v4("192.0.2.7"))]),
                       qo("x.bad.example", [(REAPER_OPT, v6("2001:db8::7"))]),
                       qo("bad.example", [(REAPER_OPT, v4("198.51.100.9"))], tcp=True),
                       qo("bad.example", None),
                       qo("bad.example", [(REAPER_OPT, b"\x01\x0a\x00")]),
                       qo("bad.example", [(65500, b"keep"), (REAPER_OPT, v4("192.0.2.8"))])]
                time.sleep(0.2)
                ln2 = [l.split()[1] for l in open(hits2).read().splitlines()] if os.path.exists(hits2) else []
                check("client option: still NXDOMAIN for a listed name, with and without the option", rc2 == [3] * 6, rc2)
                check("client option: from loopback the hit records the device rednsd named (IPv4, IPv6, TCP)",
                      ln2[:3] == ["192.0.2.7", "2001:db8::7", "198.51.100.9"], ln2)
                check("client option: no option, or a malformed one, records the query's own source as before",
                      ln2[3:5] == ["127.0.0.1", "127.0.0.1"], ln2)
                check("client option: found among other options", ln2[5:] == ["192.0.2.8"], ln2)
                del seen[:]
                qo("a.fwd.test", [(65500, b"keep"), (REAPER_OPT, v4("192.0.2.9"))])
                qo("b.fwd.test", [(REAPER_OPT, v4("192.0.2.9"))], tcp=True)
                time.sleep(0.3)
                ou = [opts_of(m) for k, m in seen if k == "udp"]; ot = [opts_of(m) for k, m in seen if k == "tcp"]
                check("client option: a forwarded query reaches the upstream WITHOUT it, over UDP and TCP",
                      ou and ot and all(o is not None and REAPER_OPT not in [c for c, _ in o] for o in ou + ot), (ou, ot))
                check("client option: the client's other options are forwarded untouched", ou and (65500, b"keep") in ou[0], ou)
            finally:
                stop.set(); p2.terminate(); p2.wait(timeout=5)
                for t in th: t.join(timeout=2)
                us.close(); ut.close()
finally:
    shutil.rmtree(work, ignore_errors=True)

# ---- 3. wiring
dh = read("dnsmasq/src/dnsmasq.h"); dm = read("dnsmasq/src/domain-match.c"); fw = read("dnsmasq/src/forward.c"); op = read("dnsmasq/src/option.c")
check("dnsmasq.h: the marker bit, the widened flags, the hitlog path", "#define SERV_REAPER_NX      65536" in dh and dh.count("u32 flags; u16 domain_len;") == 4 and "char *reaper_hitlog;" in dh)
check("forward.c: a hit is recorded right after a successful lookup, for UDP and TCP",
      fw.count("if (flags & F_NXDOMAIN)") >= 2 and "reaper_hit(first, reaper_client(udpaddr));" in fw and "reaper_hit(first, reaper_client(&peer_addr));" in fw)
e0 = read("dnsmasq/src/edns0.c")
check("edns0.c: the client option is believed from loopback only, cut from every query, read before anything else",
      "static int reaper_from_loopback(union mysockaddr *source)" in e0 and "if (reaper_from_loopback(source))" in e0
      and "memmove(q, q + 4 + len, end - (q + 4 + len));" in e0
      and e0.index("plen = reaper_take_client(header, plen, source);") < e0.index("plen  = add_mac(header, plen, outlen, source, now, cacheable);"))
check("domain-match.c: only reaper-nx entries are recorded, bounded by rate and size, never through a link",
      "if (!(s->flags & SERV_REAPER_NX) || !s->domain)" in dm and "#define REAPER_HIT_RATE 50" in dm and "#define REAPER_HIT_MAX  (256 * 1024)" in dm and "O_NOFOLLOW" in dm)
check("option.c: reaper-nx parses as an answer-less address=, reaper-hitlog once", '{ "reaper-nx", 1, 0, LOPT_REAPER_NX },' in op and "flags = SERV_LITERAL_ADDRESS | SERV_REAPER_NX;" in op and "LOPT_REAPER_HITLOG, ARG_ONE" in op)

web = read("httpd/web.c"); page = read("www/Reaper_Dreadwatch.asp"); menu = read("www/require/menuTrees/menuTree.js")
cgi = web[web.index("do_reaper_warden_cgi(char *url, FILE *stream)"):]
cgi = cgi[:cgi.index("\n}\n")]
check("CGI: dns_status / dns_reset / dns_test behind the existing reaper_gate, the collector run only as root's own file",
      cgi.index("reaper_gate()") < cgi.index('!strcmp(action, "dns_status")') and 'reaper_script_ok(RDW_SH) && (p = popen("sh " RDW_SH " stats 2>/dev/null", "r"))' in cgi
      and 'eval("sh", RDW_SH, "reset");' in cgi and 'reaper_audit("dreadwatch", "reset", "counters");' in cgi
      and "rdw_query(name, &rc)" in cgi and 'reaper_audit("dreadwatch", "self-test", name);' in cgi)
check("CGI: the self-test asks 127.0.0.1:53 with a 1.5 s ceiling for a charset-checked list name (rc's dns.first since 2026-10-24)",
      "htonl(INADDR_LOOPBACK)" in web and "struct timeval tv = { 1, 500000 };" in web
      and 'fopen("/tmp/rwarden/dns.first", "r")' in web and 'strspn(ln, "abcdefghijklmnopqrstuvwxyz0123456789.-") != n' in web)
check("menu: Dreadwatch is the Warden menu's second tab; httpd treats it as a native page",
      '{url: "Reaper_Dreadwatch.asp", tabName: "<#RDWT_00#>"}' in menu and menu.index("Reaper_Warden.asp") < menu.index("Reaper_Dreadwatch.asp")
      and '"Reaper_Dreadwatch.asp",' in read("httpd/reaper_inject.c"))
check("page: per-feed table, top names, devices, recent lookups, self-test, reset, coverage - all from dns_status",
      all(w in page for w in ('id="fn_basics"', 'id="fn_certpl"', 'id="topbody"', 'id="clibody"', 'id="recbody"', "onclick=\"dwTest()\"", "onclick=\"dwReset()\"", 'id="cov"', "ReaperNames.byIp(ip, '')")))
check("page: pure ASCII (the www-ascii gate)", all(ord(c) < 128 for c in page))
# 2026-10-24 (owner, _r35): the Long-Term Storage rows for Wallguard / Dreadwatch / Encrypted DNS could not be switched on -
# Save posted a hard-coded five-key list; it must post every switchable catalog row
stp = read("www/Reaper_Storage.asp")
check("Storage page: Save posts every switchable catalog row (Dreadwatch, Wallguard, Encrypted DNS included), USB-only rows only on USB",
      "var order = DSETS.filter(function(d){ return !d.locked && !(d.usbonly && loc !== 'usb'); }).map(function(d){ return d.k; });" in stp
      and "{k:'dw'," in stp and "{k:'shh'," in stp and "{k:'edns'," in stp and "{k:'shl'," in stp)
check("httpd store_set accepts the four tokens", '"slog", "shl", "shh", "dw", "edns", NULL' in web)
mk = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_markers.txt"), encoding="utf-8").read()
check("markers: dnsmasq option, rc list + collector, httpd report, the page",
      all(w in mk for w in ("usr/sbin/dnsmasq|reaper-hitlog|1", "sbin/rc|reaper-nx=/|1", "sbin/rc|Dreadwatch hit collector|1",
                            "usr/sbin/httpd|sh /tmp/rwarden/dns.sh stats|1", "www/Reaper_Dreadwatch.asp|dwStats|1")))
lc = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reaper_langcheck.py"), encoding="utf-8").read()
check("the i18n gate checks the new page", "'Reaper_Dreadwatch.asp'," in lc)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
