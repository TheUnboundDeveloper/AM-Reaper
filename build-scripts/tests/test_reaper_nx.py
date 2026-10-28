#!/usr/bin/env python3
"""Dreadwatch's threat table in dnsmasq (backlog "[P1] RAM: the Dreadwatch name list is held in RAM five times",
owner 2026-10-23; built 2026-10-24).

WHY. The threat list reached dnsmasq as --reaper-nx=/host/ lines: ~54 B a name as a struct server in EVERY
instance (the main one and one per extra network) plus the 21 MB text include in tmpfs - the same 683k names
five times over, ~125 MB on the RT-BE96U, against the RT-BE86U's 1 GB budget. Now rc compiles the list
with wallguardc (--subtree: every name covers its subdomains, as reaper-nx did) into one Wallguard-format table that
every instance maps read-only and shared (dnsmasq/src/reaper_nx.c): one copy, ~12 B a name, and the include
shrinks to two lines. The answer has to stay what it was - NXDOMAIN + EDE 15 for the name and its subdomains,
one hit record per answer (now with the feed ids), the longest entry wins between the list and dnsmasq's own
config entries, Dreadwatch ahead of Wallguard - and the table must swap without a restart and fail OPEN when it
is missing or damaged: the resolver never fails over the block list.

WHAT IT DOES. Builds wallguardc and the patched dnsmasq for the host (temporary copies), compiles a two-feed
table, runs dnsmasq against a fake upstream and proves every rule above over UDP and TCP, the swap, the
damaged and the missing table, two instances sharing one mapping (/proc/PID/maps), then pins the rc, httpd
and tmp-layout side in source. rc still restarts dnsmasq when the list changes (the cache is flushed with
it), so the swap is tested on names not yet cached.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] or REAPER_ROUTER_SRC - or no gcc).
"""
import json, os, random, re, shutil, socket, struct, subprocess, sys, tempfile, threading, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "dnsmasq", "src", "reaper_nx.c")):
    skip("no router source tree with dnsmasq/src/reaper_nx.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host compiler")
def read(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()

work = tempfile.mkdtemp(prefix="rnx_")
procs, stop = [], threading.Event()
try:
    # ---- 1. host builds
    SC = os.path.join(work, "wallguardc")
    b = subprocess.run([CC, "-O2", "-Wall", "-Wextra", "-o", SC, os.path.join(SRC, "wallguard", "wallguardc.c")], capture_output=True, text=True)
    check("wallguardc builds for the host without warnings", b.returncode == 0 and not b.stderr.strip(), b.stderr[-600:])
    db = os.path.join(work, "dnsmasq")
    shutil.copytree(os.path.join(SRC, "dnsmasq"), db, symlinks=True, ignore=shutil.ignore_patterns("*.o", "dnsmasq"))
    b = subprocess.run(["make", "-C", db, "COPTS=-DNO_DBUS -DNO_INOTIFY -DHAVE_BROKEN_RTC", "CC=" + CC, "-j4"], capture_output=True, text=True, timeout=900)
    DB = os.path.join(db, "src", "dnsmasq")
    check("the patched dnsmasq builds for the host", b.returncode == 0 and os.path.exists(DB), (b.stdout + b.stderr)[-800:])
    warn = [l for l in (b.stdout + b.stderr).splitlines() if "warning" in l and re.search(r"(reaper_nx|forward|domain-match|option|wallguard)\.c|dnsmasq\.h", l)]
    check("...without warnings from reaper_nx.c or the patched files", not warn, warn[:5])
    if fails:
        raise SystemExit

    # ---- 2. the table, built as rc builds it: one --list per feed (bit = position in RW_DIDS), --subtree
    L = os.path.join(work, "lists"); os.makedirs(L)
    def wf(name, text):
        p = os.path.join(L, name); open(p, "w").write(text); return p
    NX = os.path.join(work, "nx"); os.makedirs(NX)
    TABLE = os.path.join(NX, "threat.db")
    def build(urlhaus, phish, stats=None):
        a = [SC, "build", "--subtree", "--out", TABLE + ".new"] + (["--stats", stats] if stats else []) + \
            ["--list", "1:urlhaus:" + wf("urlhaus", urlhaus), "--list", "2:phish:" + wf("phish", phish)]
        r = subprocess.run(a, capture_output=True, text=True)
        if r.returncode != 0: return r.stderr
        if subprocess.run([SC, "check", "--db", TABLE + ".new"], capture_output=True).returncode != 0: return "check failed"
        os.rename(TABLE + ".new", TABLE); return ""
    URLHAUS = "evil.example\nshared.example\nbad.cfg.example\ncfg.example\nbad.zone.example\nzone.example\nboth.example\nhost.lan\n"
    PHISH = "shared.example\nphish.example\n"
    st = os.path.join(work, "stats.json")
    check("wallguardc builds the table from one list per feed", build(URLHAUS, PHISH, st) == "" and os.path.exists(TABLE))
    # review 2026-10-24 (Q-A-3b): the same table from the "<feeds> <name>" list read directly (--kfile) - byte for
    # byte the per-feed build, apart from the build time in the header (offset 24, 8 bytes)
    kf = wf("k", "".join("urlhaus " + n + "\n" for n in URLHAUS.split() if n != "shared.example")
              + "urlhaus,phish shared.example\nphish phish.example\n- orphan.example\n"
              + "bogus,phish x.notafeed.example\n")
    TABLE2 = TABLE + ".kf"
    r2 = subprocess.run([SC, "build", "--subtree", "--out", TABLE2, "--kfile", kf, "--kids", "urlhaus phish other"], capture_output=True, text=True)
    # the per-feed build of the same names: the shell split's files (other = the "-" names; an unknown id dropped)
    a3 = [SC, "build", "--subtree", "--out", TABLE + ".lf", "--list", "1:urlhaus:" + wf("lu", URLHAUS), "--list",
          "2:phish:" + wf("lp", PHISH + "x.notafeed.example\n"), "--list", "3:other:" + wf("lo", "orphan.example\n")]
    r3 = subprocess.run(a3, capture_output=True, text=True)
    k1 = bytearray(open(TABLE2, "rb").read()) if r2.returncode == 0 else b""
    l1 = bytearray(open(TABLE + ".lf", "rb").read()) if r3.returncode == 0 else b""
    if k1 and l1:
        k1[24:32] = b"\0" * 8; l1[24:32] = b"\0" * 8
    check("wallguardc --kfile builds the same table as the per-feed --list files (feeds, '-' as other, bits by --kids order)",
          r2.returncode == 0 and r3.returncode == 0 and k1 and k1 == l1, (r2.stderr, r3.stderr, len(k1), len(l1)))
    check("--kfile without --kids (or the reverse) is refused",
          subprocess.run([SC, "build", "--out", TABLE + ".x", "--kfile", kf], capture_output=True).returncode != 0
          and subprocess.run([SC, "build", "--out", TABLE + ".x", "--kids", "a b"], capture_output=True).returncode != 0)
    sj = json.load(open(st)); src = {s["id"]: s for s in sj.get("sources", [])}
    check("a name two feeds carry is stored once (unique counted for the earlier feed)",
          sj.get("names") == 9 and src["phish"]["unique"] == 1 and src["phish"]["names"] == 2, sj)
    def explain(name):
        return json.loads(subprocess.run([SC, "explain", "--db", TABLE, name], capture_output=True, text=True).stdout)
    e = explain("a.b.evil.example")
    check("--subtree: a plain name covers its subdomains (as reaper-nx=/host/ did)", e["verdict"] == "blocked" and e["lists"] == ["urlhaus"], e)
    check("the shared name carries both feeds", set(explain("shared.example")["lists"]) == {"urlhaus", "phish"}, explain("shared.example"))

    # ---- 3. dnsmasq + a fake upstream (test_wallguard.py's harness)
    UP, PORT, PORT2, PORT3 = 5411, 5412, 5413, 5414
    seen = {}
    def enc(name):
        return b"".join(bytes([len(l)]) + l.encode() for l in name.split(".")) + b"\0"
    def qname_of(m):
        i, parts = 12, []
        while m[i]:
            parts.append(m[i + 1:i + 1 + m[i]].decode()); i += m[i] + 1
        return ".".join(parts), i + 5
    def upstream_answer(m):
        name, qend = qname_of(m)
        qtype = struct.unpack(">H", m[qend - 4:qend - 2])[0]
        seen[name.lower()] = seen.get(name.lower(), 0) + 1
        if qtype == 1:
            rr = b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, 300, 4) + socket.inet_aton("192.0.2.53"); an = 1
        else:
            rr = b""; an = 0
        opt = b"\0" + struct.pack(">HHIH", 41, 1232, 0, 0) if struct.unpack(">H", m[10:12])[0] else b""
        return m[:2] + b"\x81\x80" + m[4:6] + struct.pack(">HHH", an, 0, 1 if opt else 0) + m[12:qend] + rr + opt
    us = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); us.bind(("127.0.0.1", UP)); us.settimeout(0.3)
    def serve():
        while not stop.is_set():
            try: m, a = us.recvfrom(4096)
            except socket.timeout: continue
            us.sendto(upstream_answer(m), a)
    threading.Thread(target=serve, daemon=True).start()

    # Wallguard beside it, as on the router: a name both list has to stay Dreadwatch's
    SD = os.path.join(work, "sd"); RUN = os.path.join(SD, "run"); os.makedirs(RUN)
    subprocess.run([SC, "build", "--out", os.path.join(SD, "db"), "--list", "1:ads:" + wf("ads", "ads.example\nboth.example\n")], check=True, capture_output=True)
    open(os.path.join(SD, "policy.tmp"), "w").write("default 7fffffff\n"); os.rename(os.path.join(SD, "policy.tmp"), os.path.join(SD, "policy"))
    HITLOG, LOG = os.path.join(work, "dns.hits"), os.path.join(work, "dnsmasq.log")
    def start(port, log):
        conf = os.path.join(work, "d%d.conf" % port)
        open(conf, "w").write("port=%d\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\npid-file=\n"
                              "server=127.0.0.1#%d\nserver=/zone.example/127.0.0.1#%d\naddress=/cfg.example/1.2.3.4\nlocal=/lan/\n"
                              "wallguard-dir=%s\nreaper-hitlog=%s\nreaper-nx-db=%s\nlog-facility=%s\n" % (port, UP, UP, SD, HITLOG, TABLE, log))
        p = subprocess.Popen([DB, "-k", "-C", conf], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE); procs.append(p); return p
    dp = start(PORT, LOG); time.sleep(0.8)
    check("dnsmasq starts with --reaper-nx-db", dp.poll() is None, dp.stderr.read().decode()[-300:] if dp.poll() is not None else "")
    if dp.poll() is not None:
        raise SystemExit

    def q(name, qtype=1, port=PORT, tcp=False):
        m = struct.pack(">HHHHHH", random.randint(1, 65535), 0x0100, 1, 0, 0, 1) + enc(name) + struct.pack(">HH", qtype, 1)
        m += b"\0" + struct.pack(">HHIH", 41, 1232, 0, 0)
        if tcp:
            s = socket.create_connection(("127.0.0.1", port), timeout=3); s.sendall(struct.pack(">H", len(m)) + m)
            try:
                r = b""
                while len(r) < 2 or len(r) < 2 + struct.unpack(">H", r[:2])[0]:
                    c = s.recv(4096)
                    if not c: break
                    r += c
            finally: s.close()
            r = r[2:]
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(3); s.sendto(m, ("127.0.0.1", port))
            try: r = s.recv(4096)
            finally: s.close()
        rcode, an, ns, ar = r[3] & 0x0f, struct.unpack(">H", r[6:8])[0], struct.unpack(">H", r[8:10])[0], struct.unpack(">H", r[10:12])[0]
        _, i = qname_of(r)
        addrs, ede = [], False
        for _ in range(an + ns + ar):
            if r[i] & 0xc0 == 0xc0: i += 2
            else:
                while r[i]: i += r[i] + 1
                i += 1
            t, _c, _ttl, rdl = struct.unpack(">HHIH", r[i:i + 10]); i += 10
            if t == 1: addrs.append(socket.inet_ntoa(r[i:i + 4]))
            if t == 41:
                j = i
                while j + 4 <= i + rdl:
                    c, l = struct.unpack(">HH", r[j:j + 4]); ede = ede or (c == 15 and r[j + 4:j + 6] == b"\x00\x0f"); j += 4 + l
            i += rdl
        return rcode, addrs, ede
    hits = lambda: [l.split() for l in open(HITLOG).read().splitlines() if not l.startswith("#")] if os.path.exists(HITLOG) else []
    sh = lambda: [l.split() for l in open(os.path.join(RUN, "hits")).read().splitlines() if not l.startswith("#")] if os.path.exists(os.path.join(RUN, "hits")) else []

    rc, a, ede = q("evil.example")
    check("a listed name: NXDOMAIN with EDE 15 Blocked", rc == 3 and a == [] and ede, (rc, a, ede))
    h = hits()
    check("one hit record: epoch (a date), client, the listed name, its feed",
          len(h) == 1 and len(h[0]) == 4 and h[0][1] == "127.0.0.1" and h[0][2:] == ["evil.example", "urlhaus"] and abs(int(h[0][0]) - time.time()) < 120, h)
    rc, a, ede = q("a.b.EVIL.Example")
    check("a subdomain, in any case: NXDOMAIN, recorded under the listed name, lower-cased", rc == 3 and hits()[-1][2:] == ["evil.example", "urlhaus"], (rc, hits()[-1:]))
    check("a name two feeds carry: both ids, comma-joined", q("shared.example")[0] == 3 and hits()[-1][2:] == ["shared.example", "urlhaus,phish"], hits()[-1:])
    check("the other feed's name", q("x.phish.example")[0] == 3 and hits()[-1][2:] == ["phish.example", "phish"], hits()[-1:])
    check("an unlisted name is forwarded as usual", q("news.example")[1] == ["192.0.2.53"])
    n = len(hits())
    check("dnsmasq's own entry of the same length wins: address=/cfg.example/ answers 1.2.3.4 for it and its subdomains, no record",
          q("cfg.example")[1] == ["1.2.3.4"] and q("other.cfg.example")[1] == ["1.2.3.4"] and len(hits()) == n, hits()[n:])
    check("...but a longer listed name under it is Dreadwatch's (the longest entry wins, as before)",
          q("bad.cfg.example")[0] == 3 and hits()[-1][2] == "bad.cfg.example", hits()[-1:])
    check("an explicit server=/zone/ of the same length keeps its zone (forwarded); a longer listed name under it is blocked",
          q("zone.example")[1] == ["192.0.2.53"] and q("www.zone.example")[1] == ["192.0.2.53"] and q("bad.zone.example")[0] == 3
          and seen.get("zone.example") == 1 and "bad.zone.example" not in seen, dict(seen))
    check("local=/lan/ answers its zone itself (no record); a longer listed name under it is Dreadwatch's (recorded)",
          q("other.lan")[0] == 3 and not any(x[2] == "other.lan" for x in hits()) and q("host.lan")[0] == 3 and hits()[-1][2] == "host.lan", hits()[-2:])
    check("Wallguard blocks its own names beside it (0.0.0.0, its own log)", q("ads.example")[1] == ["0.0.0.0"] and any(x[5] == "ads.example" for x in sh()), sh())
    check("a name on both lists is Dreadwatch's: NXDOMAIN, counted in ITS log, not Wallguard's",
          q("both.example")[0] == 3 and hits()[-1][2] == "both.example" and not any(x[5] == "both.example" for x in sh()), (hits()[-1:], sh()))
    n = len(hits())
    rc, a, ede = q("evil.example", tcp=True)
    check("TCP: the same answer and record", rc == 3 and a == [] and len(hits()) == n + 1 and hits()[-1][2] == "evil.example", (rc, a, ede, hits()[-1:]))
    check("no record for anything but a listed answer", all(len(x) == 4 and x[2] in ("evil.example", "shared.example", "phish.example", "bad.cfg.example", "bad.zone.example", "host.lan", "both.example") for x in hits()), hits())

    # ---- 4. the table changes under a running instance
    pid0 = dp.pid
    check("a new table is built and renamed into place", build(URLHAUS + "fresh.example\n", "") == "")
    time.sleep(2.4)
    check("within 2 s the new table is in use - same process, no restart; a name no longer listed is forwarded again",
          q("fresh.example")[0] == 3 and q("phish.example")[1] == ["192.0.2.53"] and dp.poll() is None and dp.pid == pid0, (q("fresh.example"), q("phish.example")))
    good = open(TABLE, "rb").read()
    tmp = TABLE + ".new"; open(tmp, "wb").write(good[:-5]); os.rename(tmp, TABLE); time.sleep(2.4)
    check("a damaged table blocks nothing (fail open), is logged, and dnsmasq stays up",
          q("evil.example")[1] == ["192.0.2.53"] and dp.poll() is None and "damaged" in open(LOG).read(), open(LOG).read()[-300:])
    os.unlink(TABLE); time.sleep(2.4)
    check("a missing table: fail open, logged", q("x.evil.example")[1] == ["192.0.2.53"] and "is not there" in open(LOG).read(), open(LOG).read()[-300:])
    open(tmp, "wb").write(good); os.rename(tmp, TABLE); time.sleep(2.4)
    check("the table back: blocking again, the mapping logged with its count",
          q("y.evil.example")[0] == 3 and re.search(r"9 threat names mapped", open(LOG).read()), open(LOG).read()[-300:])
    dp2 = start(PORT2, LOG + "2"); time.sleep(0.8)
    check("a second instance (an extra network's) starts on the same table and blocks", dp2.poll() is None and q("z.evil.example", port=PORT2)[0] == 3)
    def maps(p):
        try: return [l for l in open("/proc/%d/maps" % p.pid).read().splitlines() if l.endswith(TABLE)]
        except OSError: return None
    m1, m2 = maps(dp), maps(dp2)
    check("both map the one file read-only and SHARED (r--s): one copy of the list in RAM for every instance",
          m1 and m2 and all(" r--s " in l for l in m1 + m2), (m1, m2))

    # ---- 4b. review 2026-10-24 (Q-A-3): rc rebuilds the table in the background at boot, so an instance may start
    # BEFORE the table exists - it answers (fail open) without the "is not there" warning, and maps the table when it lands
    os.rename(TABLE, TABLE + ".away"); time.sleep(0.2)
    LOG3 = LOG + "3"; dp3 = start(PORT3, LOG3); time.sleep(0.8)
    check("an instance started before the table exists is up and forwards", dp3.poll() is None and q("w.evil.example", port=PORT3)[1] == ["192.0.2.53"])
    time.sleep(2.4)
    check("...and says nothing about it (a table still being built is not a fault)", "is not there" not in (open(LOG3).read() if os.path.exists(LOG3) else ""),
          open(LOG3).read()[-300:] if os.path.exists(LOG3) else "")
    os.rename(TABLE + ".away", TABLE); time.sleep(2.4)
    check("...then maps the table when it lands and blocks", q("w2.evil.example", port=PORT3)[0] == 3 and "threat names mapped" in open(LOG3).read(), open(LOG3).read()[-300:])
    check("an instance that HAD the table warns when it goes away", "is not there" in open(LOG).read())

    # ---- 5. the rc / httpd / layout side
    rw = read("rc/rwarden.c")
    for needle, what in (
        ('echo \\"reaper-nx-db=$RW_NXDB\\"; } > $RW_DNSC.new', "update.sh: the include is two lines - the hit log and the table"),
        # 2026-10-27: the ids gain your own sources' slots ($RW_DCUST)
        ('build --subtree --out $RW_NXDB.new --kfile $DN.k --kids \\"$RW_DIDS other $RW_DCUST\\"', "update.sh: wallguardc compiles the feeds list itself (--kfile, review 2026-10-24 Q-A-3b) with --subtree, then checks the table before it is installed"),
        ("check --db $RW_NXDB.new >/dev/null 2>&1 && mv -f $RW_NXDB.new $RW_NXDB", "update.sh: ...renamed into place only when the check passes"),
        ('#define RW_DIDS_STR  "urlhaus phish c2 crypto ransom certpl threatview threatfox"', "rwarden.c: the feed order is one define (bit = position in it)"),
        ('--kids \\"$RW_DIDS other $RW_DCUST\\"', "update.sh: a name no feed claims goes under 'other', never left out"),
        ("static const char rw_nx_rebuild_sh[] =", "boot: the table is rebuilt from the /jffs copy before the first update"),
        ('fprintf(f, "reaper-hitlog=%s\\nreaper-nx-db=%s\\n", RW_HITS, RW_NX_DB);', "boot: the two-line include is written when missing"),
        ("_dvalid() { awk '(NF == 3 || NF == 4)", "dns.sh: a record may carry the feed ids (4th field), charset-checked"),
        ("if (NF >= 4 && $4 != \\\"-\\\") lf[$3]=$4;", "dns.sh: attribution comes from the record, not from a text list"),
        ("_mc=$((_ma * 1024 / 4 / 90))", "update.sh: the memory guard counts one copy (~90 B a name while built), not one per instance"),
    ):
        check(what, needle in rw)
    check("tmp layout: /tmp/reaper_nx is root's 0755 (dnsmasq, as nobody, only reads it)", '{ "/tmp/reaper_nx",\t\t0755 }' in read("shared/reaper_tmpsafe.h"))
    check("httpd self-test reads one listed name from dns.first (no text list to parse)", 'fopen("/tmp/rwarden/dns.first", "r")' in read("httpd/web.c"))
    check("the instance emitters are unchanged (conf-file= under the helper's guard)",
          'fprintf(fp, "conf-file=%s\\n", wd);' in read("rc/services.c") and 'fprintf(fp, "conf-file=%s\\n", wd);' in read("rc/sdn.c"))
    check("dnsmasq Makefile links reaper_nx.o", "wallguard.o reaper_nx.o" in read("dnsmasq/Makefile"))
    check("wallguardc usage names --subtree", "build [--subtree] --out DB" in read("wallguard/wallguardc.c"))
except SystemExit:
    pass
finally:
    stop.set()
    for p in procs:
        if p.poll() is None: p.terminate()
        try: p.wait(3)
        except Exception: p.kill()
    shutil.rmtree(work, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + x) for x in fails]; sys.exit(1)
print("\nall checks passed")
