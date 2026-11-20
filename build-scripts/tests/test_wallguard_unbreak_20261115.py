#!/usr/bin/env python3
"""Wallguard Unbreak / build-status / USB-store fixes (owner-approved, 2026-11-15).

WHY. Field reads on the owner's RT-BE96U: (D5) `recent` kept the last 500 records of ALL devices, so on a busy network
Unbreak's 15 minutes for one device came back short; (D4) the engine wrote "-" as the MAC of every record and Unbreak
matched the MAC the page sends - a streaming box had 26 blocks of saa.paramountplus.com
that Unbreak never showed; (D6) after Allow the page asked Unbreak again and the same name came back, so Allow looked
like it did nothing; (D7) a rebuild skipped for a list without a usable copy left only a syslog line; (D9) every
rebuild logged "list <id> on the USB volume does not match its last download" for every list - a list downloaded
while the USB store was not up yet (the boot update) or whose write failed stays in RAM with its NEW sum recorded,
the volume keeps the OLDER copy, and list_path asked the volume first. The engine (agent A, same day) records the MAC,
and for a CNAME block (reason c) a 7th field - the listed chain entry - with field 6 the name the device asked for;
the live view has no MAC field and a 6th field for verdict c only.

WHAT IT DOES.
  - runs the real wallguard.sh (sh and busybox ash) with a host-built wallguardc and rstore, a fake ip/arp/curl:
    fold of 6- and 7-field records (a CNAME block counts under its chain entry), recent trimmed by time with a line
    cap, unbreak by MAC (upper case too), by the addresses the MAC holds now for "-" records (ip neigh, arp, leases),
    never through another device's MAC on a reused address, the via name of a CNAME row, names allowed now (allow,
    a running 24 h allow, an allowed via name; subdomains) left out; live with the c record replacing the query's;
    the build status (skip miss / built with fewer lists) in stats; D9: the newer RAM copy is used without the
    mismatch warning and moved to the volume, a copy changed on the volume with no RAM copy is still refused.
  - source pins: the page (CNAME rows, Allow marks the row and no longer re-asks Unbreak, the build warning, the live
    c verdict), the CGI's allow still writes the plain allow files, the 25 packs carry RSHD_185..191 in lockstep.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
SH_FILE = os.path.join(SRC, "wallguard", "wallguard.sh") if SRC else ""
if not SRC or not os.path.isfile(SH_FILE):
    print("SKIP: no router tree with wallguard/wallguard.sh (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail != "" else ""))
def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

sh = rd("wallguard/wallguard.sh")
# ============================================================ syntax
r = run(["sh", "-n", SH_FILE]); check("wallguard.sh passes sh -n", r.returncode == 0, r.stderr)
BB = shutil.which("busybox")
if BB and run([BB, "ash", "-c", "true"]).returncode != 0: BB = None
if BB:
    r = run([BB, "ash", "-n", SH_FILE]); check("wallguard.sh passes busybox ash -n", r.returncode == 0, r.stderr)
# no apostrophe inside a single-quoted awk program of the functions touched today
for fn in ("unbreak", "live", "mac_ips"):
    m = re.search(r"^%s\(\) \{\n(.*?)^\}\n" % fn, sh, re.S | re.M)
    body = m.group(1) if m else ""
    progs = re.findall(r"awk [^']*'(.*?)'", body, re.S)
    check("%s(): present, its awk programs carry no apostrophe" % fn, m is not None and progs and all("'" not in p for p in progs))

# ============================================================ the real script on the host
if not CC or not shutil.which("flock"):
    print("SKIP (runtime part): needs a host compiler and flock")
else:
    work = tempfile.mkdtemp(prefix="wgub_")
    try:
        SC = os.path.join(work, "wallguardc")
        b = run([CC, "-O2", "-o", SC, os.path.join(SRC, "wallguard", "wallguardc.c")])
        check("wallguardc builds on the host", b.returncode == 0, b.stderr[-300:])
        bindir = os.path.join(work, "bin"); os.makedirs(bindir)
        def tool(name, text):
            p = os.path.join(bindir, name); open(p, "w").write(text); os.chmod(p, 0o755)
        tool("logger", "#!/bin/sh\necho \"$*\" >> %s/logger.out\n" % work)
        tool("usleep", "#!/bin/sh\nexec sleep 0.2\n")
        _rf = shutil.which("flock")
        tool("flock", "#!/bin/sh\nfor a; do case \"$a\" in -w|-w*|--wait|--timeout) exit 1;; esac; done\nexec %s \"$@\"\n" % _rf)
        # the FireTV's neighbours: IPv4 in ip neigh (upper-case MAC as some tools print it), IPv6 in ip -6 neigh,
        # an older address in arp; the leases file adds one more
        tool("ip", "#!/bin/sh\ncase \"$*\" in\n"
                   "  '-6 neigh show') echo 'fe80::200:5eff:fe00:539e dev br0 lladdr 00:00:5e:00:53:9e STALE' ;;\n"
                   "  'neigh show') echo '192.168.50.109 dev br0 lladdr 00:00:5E:00:53:9E REACHABLE'; echo '192.168.50.7 dev br0 lladdr 00:11:22:33:44:55 STALE'; echo '192.168.50.99 dev br0  FAILED' ;;\n"
                   "esac\nexit 0\n")
        tool("arp", "#!/bin/sh\necho '? (192.168.50.110) at 00:00:5e:00:53:9e [ether]  on br0'\necho '? (192.168.50.7) at 00:11:22:33:44:55 [ether]  on br0'\n")
        tool("curl", "#!/bin/sh\nexit 22\n")
        rsx = os.path.join(work, "rstore")
        shells = ["sh"] + (["busybox"] if BB else [])
        for shell in shells:
            tag = "sh" if shell == "sh" else "ash"
            D, J = os.path.join(work, tag, "d"), os.path.join(work, tag, "j")
            RUN = os.path.join(D, "run"); os.makedirs(RUN); os.makedirs(J)
            leases = os.path.join(work, tag, "leases")
            open(leases, "w").write("%d 00:00:5e:00:53:9e 192.168.50.111 FireTV-Box *\n%d 00:11:22:33:44:55 192.168.50.7 nas *\n" % (time.time() + 3600, time.time() + 3600))
            env = dict(os.environ, WALLGUARD_DIR=D, WALLGUARD_JFFS=J, WALLGUARDC=SC, WALLGUARD_WAN="1", WALLGUARD_LEASES=leases,
                       PATH=bindir + ":" + os.environ["PATH"], LC_ALL="C", RSTORE_PUB_F=os.path.join(work, tag, "none"))
            def wg(*a, extra=None):
                cmd = (["sh", SH_FILE] if shell == "sh" else [BB, "ash", SH_FILE]) + list(a)
                return run(cmd, env=dict(env, **(extra or {})), timeout=120)
            def logtxt():
                p = os.path.join(work, "logger.out"); return open(p).read() if os.path.exists(p) else ""
            # the host busybox ash runs its own ip / arp / logger applets ahead of PATH (standalone shell): the fakes
            # answer under sh only - under ash the neighbour lookups and the log lines are not asserted
            fk = shell == "sh"
            now = int(time.time())
            FT, FIP = "00:00:5e:00:53:9e", "192.168.50.109"
            # ---- fold: 6 and 7 fields
            open(os.path.join(RUN, "hits"), "w").write("".join([
                "%d %s 4 q - saa.paramountplus.com\n" % (now - 60, FIP),                      # old engine: "-"
                "%d %s 4 q - saa.paramountplus.com\n" % (now - 50, FIP),
                "%d 192.168.50.110 4 q - pings.example\n" % (now - 40),                       # its arp address
                "%d 192.168.50.111 4 q - lease.example\n" % (now - 40),                       # its lease address
                "%d fe80::200:5eff:fe00:539e 4 q - six.example\n" % (now - 40),              # its IPv6 neighbour
                "%d %s 4 q %s mac.example\n" % (now - 30, FIP, FT),                           # new engine: MAC
                "%d %s 4 c %s www.asked.example cdn.listed.example\n" % (now - 20, FIP, FT),  # CNAME block
                "%d %s 4 c %s nochain.example -\n" % (now - 20, FIP, FT),                     # chain unknown
                "%d %s 4 q 00:11:22:33:44:55 other.example\n" % (now - 10, FIP),              # ANOTHER device, reused address
                "%d 192.168.50.7 4 q - nas.example\n" % (now - 10),
                "%d %s 4 q %s bad7.example extra\n" % (now - 5, FIP, FT),                     # 7 fields on q: junk
                "%d %s 4 c %s bad.example BAD\"chain\n" % (now - 5, FIP, FT),                 # bad chain: junk
                "%d %s 4 q %s allowed.example\n" % (now - 5, FIP, FT),
                "%d %s 4 q %s sub.allow24.example\n" % (now - 5, FIP, FT),
                "%d %s 4 q %s gone24.example\n" % (now - 5, FIP, FT),
                "%d %s 4 c %s cdnasked.example allowedvia.example\n" % (now - 5, FIP, FT)]))
            r = wg("fold")
            rec = open(os.path.join(D, "recent")).read() if os.path.exists(os.path.join(D, "recent")) else ""
            ctr = open(os.path.join(D, "counters")).read()
            check("[%s] fold: 6- and 7-field records reach recent, a 7th field on q and a bad chain entry are dropped" % tag,
                  "www.asked.example cdn.listed.example\n" in rec and "nochain.example -\n" in rec and "bad7.example" not in rec
                  and "bad.example" not in rec and "TOTAL 14" in ctr, (r.stderr, ctr[:200]))
            check("[%s] fold: a CNAME block counts under its chain entry, an unknown chain under the asked name; CNAME tallied" % tag,
                  re.search(r"^NAME cdn\.listed\.example 1 ", ctr, re.M) and not re.search(r"^NAME www\.asked\.example ", ctr, re.M)
                  and re.search(r"^NAME nochain\.example 1 ", ctr, re.M) and "CNAME 3" in ctr, ctr)
            # ---- unbreak
            open(os.path.join(J, "allow"), "w").write("allowed.example\nALLOWEDVIA.example\n")
            open(os.path.join(J, "allow24"), "w").write("%d allow24.example\n%d gone24.example\n" % (now + 3600, now - 10))
            r = wg("unbreak", FT.upper(), "15")
            try: u = json.loads(r.stdout)
            except Exception as e: u = {"names": []}; check("[%s] unbreak: valid JSON" % tag, False, (e, r.stdout[:300], r.stderr[:300]))
            got = {x["d"]: x for x in u["names"]}
            check("[%s] D4: by MAC (sent in upper case) - records with the MAC, and '-' records through the addresses it holds now (ip neigh, IPv6, arp, leases)" % tag,
                  all(n in got for n in ("mac.example", "lease.example") + (("saa.paramountplus.com", "pings.example", "six.example") if fk else ())), sorted(got))
            check("[%s] D4: the owner's case - 2 blocks of saa.paramountplus.com from the FireTV's address with no MAC are counted" % tag,
                  got.get("saa.paramountplus.com", {}).get("n") == 2 or not fk, got.get("saa.paramountplus.com"))
            check("[%s] D4: a record with ANOTHER device's MAC on a reused address never matches; nor another device's '-' records" % tag,
                  "other.example" not in got and "nas.example" not in got, sorted(got))
            check("[%s] CNAME row: the asked name, with the chain entry as via; an unknown chain has none" % tag,
                  got.get("www.asked.example", {}).get("via") == "cdn.listed.example" and got.get("nochain.example", {}).get("via") == ""
                  and got.get("mac.example", {}).get("via") == "", (got.get("www.asked.example"), got.get("nochain.example")))
            check("[%s] D6: names allowed now are left out (allow; a running 24 h allow covers subdomains; an allowed via name)" % tag,
                  "allowed.example" not in got and "sub.allow24.example" not in got and "cdnasked.example" not in got, sorted(got))
            check("[%s] D6: an expired 24 h allow does not hide a name" % tag, "gone24.example" in got, sorted(got))
            check("[%s] unbreak leaves no temp file behind" % tag, not [f for f in os.listdir(D) if f.startswith("unbreak.allow")], os.listdir(D))
            u2 = json.loads(wg("unbreak", FIP, "15").stdout)
            check("[%s] unbreak by address still works (every record from that address)" % tag,
                  {"saa.paramountplus.com", "mac.example", "other.example"} <= {x["d"] for x in u2["names"]}, u2)
            u3 = json.loads(wg("unbreak", FT, "0").stdout)
            check("[%s] unbreak with a 0-minute window finds nothing" % tag, u3["names"] == [], u3)
            # ---- D5: the trim - an hour, at most RECMAX records
            old = "".join("%d 192.168.50.5 4 q - old%d.example\n" % (now - 7200 - i, i) for i in range(30))
            fresh = "".join("%d 192.168.50.5 4 q - new%d.example\n" % (now - 100 + i, i) for i in range(40))
            open(os.path.join(D, "recent"), "w").write(old + fresh)
            open(os.path.join(RUN, "hits"), "w").write("%d 192.168.50.5 4 q - last.example\n" % now)
            wg("fold")
            lines = open(os.path.join(D, "recent")).read().splitlines()
            check("[%s] D5: records older than an hour leave recent, the last hour stays whole (well past the old 500-line idea)" % tag,
                  len(lines) == 41 and not any("old" in l for l in lines) and lines[-1].endswith("last.example"), len(lines))
            open(os.path.join(RUN, "hits"), "w").write("%d 192.168.50.5 4 q - last2.example\n" % now)
            wg("fold", extra={"WALLGUARD_REC_MAX": "10"})
            lines = open(os.path.join(D, "recent")).read().splitlines()
            check("[%s] D5: ...and never more than the line cap (RAM only)" % tag, len(lines) == 10 and lines[-1].endswith("last2.example"), len(lines))
            busy = "".join("%d 192.168.50.%d 4 q - n%d.example\n" % (now - 800 + i // 4, 20 + i % 50, i) for i in range(3000))
            open(os.path.join(D, "recent"), "w").write(busy)
            open(os.path.join(RUN, "hits"), "w").write("%d 192.168.50.20 4 q - x.example\n" % now)
            wg("fold")
            u4 = json.loads(wg("unbreak", "192.168.50.20", "15").stdout)
            check("[%s] D5: a busy network (3000 records in 15 min) - one device's whole 15 minutes is still there" % tag,
                  len(u4["names"]) == 61, len(u4["names"]))
            # ---- live: 5 fields, c with a 6th, the c record replaces the query's own
            open(os.path.join(RUN, "live"), "w").write(
                "%d %s 1 - www.asked.example\n%d %s 1 b ads.example\n%d %s 1 c www.asked.example cdn.listed.example\n"
                "%d %s 28 - www.asked.example\n%d 192.168.50.7 1 c x.example -\n%d %s 1 b junk.example extra\n"
                % (now - 3, FIP, now - 3, FIP, now - 2, FIP, now - 1, FIP, now, now, FIP))
            lv = json.loads(wg("live").stdout)["rows"]
            check("[%s] live: the c record replaces the query's earlier row (same address and name); a later lookup stays" % tag,
                  [(x["v"], x["d"], x["via"]) for x in lv] == [("b", "ads.example", ""), ("c", "www.asked.example", "cdn.listed.example"),
                                                             ("-", "www.asked.example", ""), ("c", "x.example", "")], lv)
            # ---- D7 + D9: the build status, the USB store
            if not os.path.exists(rsx):
                mntx, jbx = os.path.join(work, "mnt"), os.path.join(work, "jb")
                rb = run([CC, "-std=gnu99", "-I", os.path.join(SRC, "shared"), '-DRSTORE_TRUST_MNT="%s"' % mntx,
                          '-DRSTORE_TRUST_JFFS="%s"' % jbx, "-DRSTORE_NEED_MOUNT=0", "-o", rsx, os.path.join(SRC, "wallguard", "rstore.c")])
                check("rstore builds on the host", rb.returncode == 0, rb.stderr[-300:])
            mnt, jb = os.path.join(work, "mnt"), os.path.join(work, "jb")
            vol = os.path.join(mnt, "RUSB" + tag); base = os.path.join(vol, ".reaper"); os.makedirs(base); os.makedirs(jb, exist_ok=True)
            open(os.path.join(base, "store.id"), "w").write("abcdef0123456789")
            pub, mounts = os.path.join(work, tag, "store.base"), os.path.join(work, tag, "mounts")
            open(pub, "w").write("%s\n,shl,\n" % base)
            open(mounts, "w").write("/dev/sda1 %s ext4 rw 0 0\n" % vol)
            env.update(RSTORE_PUB_F=pub, RSTORE_MNT_D=mnt, RSTORE_MOUNTS=mounts, RSTORE_JFFS_D=jb, RSTORE=rsx)
            L, S = os.path.join(D, "lists"), os.path.join(base, "wallguard", "lists")
            os.makedirs(L); os.makedirs(S)
            sha = lambda b: hashlib.sha256(b).hexdigest()
            newc, oldc = b"||new1.example^\n||new2.example^\n", b"||old.example^\n"
            # the boot case: the download landed in RAM (the store was not up), its sum recorded; the volume holds yesterday's
            open(os.path.join(L, "one"), "wb").write(newc); open(os.path.join(S, "one"), "wb").write(oldc)
            open(os.path.join(J, "lists.sum"), "w").write("one %s %d\n" % (sha(newc), len(newc)))
            open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n")
            open(os.path.join(D, "state"), "w").write("one ok %d %d\n" % (now, now))
            open(os.path.join(work, "logger.out"), "w").close()
            r = wg("build")
            bj = json.load(open(os.path.join(D, "build.json"))) if os.path.exists(os.path.join(D, "build.json")) else {}
            check("[%s] D9: the newer RAM copy is built from, with no 'does not match' warning" % tag,
                  r.returncode == 0 and any(x["id"] == "one" and x["names"] == 2 for x in bj.get("sources", []))
                  and ("does not match" not in logtxt() or not fk), (r.stderr[-300:], logtxt()[-300:], bj.get("sources")))
            check("[%s] D9: ...and it moved to the volume through rstore (stored copy = the recorded sum, RAM copy gone)" % tag,
                  open(os.path.join(S, "one"), "rb").read() == newc and not os.path.exists(os.path.join(L, "one")), os.listdir(L))
            r = wg("build")
            check("[%s] D9: the next build reads the volume's copy, quietly" % tag, r.returncode == 0 and ("does not match" not in logtxt() or not fk), logtxt()[-300:])
            st = json.loads(wg("stats").stdout).get("bstat") or {}
            check("[%s] D7: stats carries the build status - built, 1 of 1 lists" % tag,
                  st.get("skip") == "" and st.get("want") == 1 and st.get("used") == 1 and st.get("none") == "", st)
            # a copy changed on the volume with no RAM copy: still refused (and the table in use stays - skip miss)
            open(os.path.join(S, "one"), "ab").write(b"||evil.example^\n")
            r = wg("build")
            st = json.loads(wg("stats").stdout).get("bstat") or {}
            check("[%s] D9: a stored copy changed on the volume (no RAM copy) is still refused, and logged" % tag,
                  r.returncode != 0 and ("does not match its last download" in logtxt() or not fk), logtxt()[-300:])
            check("[%s] D7: ...the skipped rebuild is in stats (skip miss, the list named)" % tag,
                  st.get("skip") == "miss" and st.get("none") == "one" and st.get("used") == 0, st)
            # fewer lists than subscribed: a list never downloaded is built around and reported
            open(os.path.join(L, "one"), "wb").write(newc); os.remove(os.path.join(S, "one"))
            open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n3 two https://test/two.txt p\n")
            r = wg("build"); st = json.loads(wg("stats").stdout).get("bstat") or {}
            check("[%s] D7: built from fewer lists than subscribed - used 1 of 2, the missing one named" % tag,
                  r.returncode == 0 and st.get("skip") == "" and st.get("want") == 2 and st.get("used") == 1 and st.get("none") == "two", st)
            open(os.path.join(D, "build.st"), "w").write('{"t":1,"skip":"<b>","want":1,"used":1,"none":""}\n')
            check("[%s] D7: a build status of any other shape reaches the page as null" % tag,
                  json.loads(wg("stats").stdout).get("bstat", 0) is None)
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ============================================================ source pins
check("wallguard.sh: recent is trimmed by time with a line cap, never the fixed 500",
      "tail -n 500 \"$REC\"" not in sh and "tail -n \"$RECMAX\" \"$REC\" | awk -v since=\"$(( $(date +%s) - RECKEEP ))\" '$1 >= since'" in sh)
check("wallguard.sh: fold takes 6 or 7 fields (the 7th for reason c only)",
      "(NF != 6 && NF != 7) ||" in sh and "NF == 7 && ($4 != \"c\" || ($7 != \"-\" && $7 !~ re)) { next }" in sh)
check("wallguard.sh: list_path asks the RAM copy first, build pushes it to the volume (st_push), bstat written on every outcome",
      re.search(r"list_path\(\) \{\n  \[ -s \"\$L/\$1\" \][^\n]*\n  st_get \"\$1\"\n\}", sh) is not None and "st_push \"$id\"" in sh
      and all(x in sh for x in ("bstat lock;", "bstat miss \"$miss\"", "bstat \"\" \"$_bn\"", "bstat fail \"$_bn\"", '\\"bstat\\":%s')))
web = rd("httpd/web.c")
a = web.find('if (!strcmp(action, "allow")) {'); blk = web[a:a + 2500]
check("CGI: Allow still writes the plain allow files (the engine honours the table's allows, not Advanced rules)",
      a > 0 and 'SH_JFFS "/allow24" : SH_JFFS "/allow"' in blk and "/adv" not in blk)
pg = rd("www/Reaper_Wallguard.asp")
check("page: CNAME rows show the asked name and the via name (Unbreak and live), Allow offers the asked name with a note",
      "r.via ? `<#RSHD_185#>`.replace('%1', r.d).replace('%2', r.via) : r.d" in pg and pg.count("`<#RSHD_185#>`") == 2
      and "if(r.via) td.appendChild(shEl('span', 'sub', `<#RSHD_187#>`" in pg and "shAllow(r.d, '24h')" in pg)
check("page: Allow marks the row at once (RSHD_186) and no longer re-asks Unbreak after 2.5 s",
      "function shAllow(name, dur){ var fin = ReaperBusy.startLast();" in pg and "shUbMark(name)" in pg
      and "tr.setAttribute('data-ub', r.d);" in pg and "`<#RSHD_186#>`" in pg and "shUnbreak(); }, 2500)" not in pg)
check("page: the build warning (RSHD_188..191) from stats bstat, shown only while Wallguard is on",
      'id="buildwarn"' in pg and "shBuildWarn(on);" in pg and all("`<#RSHD_%d#>`" % k in pg for k in (188, 189, 190, 191)))
check("page: the live c verdict is shown as blocked", "if(r.v === 'c') r.v = 'b';" in pg and "c.className = 'v-' + r.v;" in pg)
check("page: ASCII only; every new token (RSHD_185..191) sits in a template literal, never a quoted string",
      all(ord(c) < 128 for c in pg) and len(re.findall(r"<#RSHD_(?:18[5-9]|19[01])#>", pg)) == 8
      and len(re.findall(r"`<#RSHD_(?:18[5-9]|19[01])#>`", pg)) == 8)
packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if not p.endswith("temp.dict"))
counts, pos, bad = set(), set(), []
for p in packs:
    t = open(p, encoding="utf-8", errors="replace").read().split("\n")
    counts.add(len(t))
    where = tuple(next((i for i, l in enumerate(t) if l.startswith("RSHD_%d=" % k)), -1) for k in range(185, 192))
    pos.add(where)
    vals = [t[i].split("=", 1)[1] if i >= 0 else "" for i in where]
    if -1 in where or not all(vals) or any("`" in v or "${" in v for v in vals) \
       or not ("%1" in vals[0] and "%2" in vals[0] and "%2" in vals[3] and "%3" in vals[6]):
        bad.append(os.path.basename(p))
check("packs: RSHD_185..191 in all 25, translated with their %%n, at the same lines, the 25 files in lockstep",
      len(packs) == 25 and not bad and len(counts) == 1 and len(pos) == 1, (bad, counts, len(pos)))
en = open(os.path.join(SRC, "www", "EN.dict"), encoding="utf-8").read()
others = [p for p in packs if not p.endswith("EN.dict")]
same = [os.path.basename(p) for p in others
        if re.search(r"^RSHD_188=(.*)$", open(p, encoding="utf-8").read(), re.M).group(1) == re.search(r"^RSHD_188=(.*)$", en, re.M).group(1)]
check("packs: the long strings are really translated (none is the English text)", not same, same)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for x in fails: print("  " + x)
    sys.exit(1)
print("\nall checks passed")
