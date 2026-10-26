#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wallguard (2026-10-21): the updater / collector script, release/src/router/wallguard/wallguard.sh.

WHY THIS EXISTS. wallguard.sh downloads the subscribed lists, keeps the previous copy of one that fails,
compiles the table with wallguardc, folds dnsmasq's blocked-lookup records into counters and prints the
JSON the Wallguard page renders. It runs under the router's busybox ash; every awk program in it must also
run under busybox awk.

WHAT IT DOES. Builds wallguardc for the host, puts a fake curl first on PATH (it serves local files and
fails on demand) and runs every action under /bin/sh and busybox ash: update (ok, failed-with-previous,
missing), an unsubscribed list leaving the RAM disk, build after a rule change (no download), expired
temporary allows dropped, fold (junk records dropped, '# dropped' banked, per-list tallies from the
hex bit field, devices keyed by MAC), the stats JSON (valid, top names sorted, feeds with their state),
unbreak for one device, the live view JSON, reset, the counters banked on /jffs.
Exit 0 pass, 1 fail, 77 skipped.
"""
import hashlib, json, os, shutil, stat, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
SH_FILE = os.path.join(SRC, "wallguard", "wallguard.sh")
if not SRC or not os.path.isfile(SH_FILE):
    skip("no router source tree with wallguard/wallguard.sh")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC or not shutil.which("flock"):
    skip("needs a host compiler and flock")
BB = shutil.which("busybox")
if BB and subprocess.run([BB, "ash", "-c", "true"], capture_output=True).returncode != 0:
    BB = None

def build_rstore(dest, mnt, jffs):
    """the no-follow store writer (wallguard/rstore.c) for the host, trusting a temp tree"""
    r = subprocess.run([CC, "-std=gnu99", "-I", os.path.join(SRC, "shared"), '-DRSTORE_TRUST_MNT="%s"' % mnt,
                        '-DRSTORE_TRUST_JFFS="%s"' % jffs, "-DRSTORE_NEED_MOUNT=0", "-o", dest, os.path.join(SRC, "wallguard", "rstore.c")],
                       capture_output=True, text=True)
    return r.returncode == 0

work = tempfile.mkdtemp(prefix="wallguardsh_")
try:
    SC = os.path.join(work, "wallguardc")
    b = subprocess.run([CC, "-O2", "-o", SC, os.path.join(SRC, "wallguard", "wallguardc.c")], capture_output=True, text=True)
    check("wallguardc builds", b.returncode == 0, b.stderr[-300:])
    r = subprocess.run(["sh", "-n", SH_FILE], capture_output=True, text=True)
    check("wallguard.sh passes sh -n", r.returncode == 0, r.stderr)
    if BB:
        r = subprocess.run([BB, "ash", "-n", SH_FILE], capture_output=True, text=True)
        check("wallguard.sh passes busybox ash -n", r.returncode == 0, r.stderr)

    bindir = os.path.join(work, "bin"); os.makedirs(bindir)
    srv = os.path.join(work, "srv"); os.makedirs(srv)
    # fake curl: "... -o OUT URL"; https://test/<file> is served from srv/<file>; srv/<file>.fail = exit 22
    open(os.path.join(bindir, "curl"), "w").write(
        "#!/bin/sh\nout=; url=\nwhile [ $# -gt 0 ]; do case \"$1\" in -o) out=$2; shift;; --version) exit 0;; https://*) url=$1;; esac; shift; done\n"
        "case \"$url\" in https://www.google.com/supported_domains) url=https://test/supported_domains;; esac\n"
        "f=%s/${url#https://test/}\n[ -f \"$f.fail\" ] && exit 22\n[ -f \"$f\" ] || exit 22\ncp \"$f\" \"$out\"\n" % srv)
    # phase 2: wallguardc resolve stubbed (no real lookups from a test); resolve.fail = nothing resolves
    SCW = os.path.join(bindir, "wallguardc-test")
    open(SCW, "w").write(
        "#!/bin/sh\nif [ \"$1\" = resolve ]; then shift; [ -f %s/resolve.fail ] && exit 1\n"
        "  for n; do case $n in forcesafesearch.google.com) echo \"$n v4 216.239.38.120\"; echo \"$n v6 2001:4860:4802:32::78\";;\n"
        "    restrictmoderate.youtube.com) echo \"$n v4 216.239.38.119\";; restrict.youtube.com) echo \"$n v4 216.239.38.120\";;\n"
        "    strict.bing.com) echo \"$n v4 204.79.197.220\";; esac; done; exit 0; fi\nexec %s \"$@\"\n" % (work, SC))
    os.chmod(SCW, 0o755)
    os.chmod(os.path.join(bindir, "curl"), 0o755)
    open(os.path.join(bindir, "logger"), "w").write("#!/bin/sh\necho \"$*\" >> %s/logger.out\n" % work)
    # 2026-10-26 (metal): the router's busybox 1.25 flock refuses -w - the script runs under a flock that does the
    # same, so a lock taken the util-linux way fails here as it did on the router (every build was skipped)
    _rf = shutil.which("flock")
    if _rf:
        open(os.path.join(bindir, "flock"), "w").write(
            "#!/bin/sh\nfor a; do case \"$a\" in -w|-w*|--wait|--timeout) echo 'flock: invalid option' >&2; exit 1;; esac; done\nexec %s \"$@\"\n" % _rf)
        os.chmod(os.path.join(bindir, "flock"), 0o755)
    open(os.path.join(bindir, "usleep"), "w").write("#!/bin/sh\nexec sleep 0.2\n"); os.chmod(os.path.join(bindir, "usleep"), 0o755)
    os.chmod(os.path.join(bindir, "logger"), 0o755)

    for shell in ["sh"] + (["busybox"] if BB else []):
        tag = "sh" if shell == "sh" else "ash"
        D, J = os.path.join(work, tag, "d"), os.path.join(work, tag, "j")
        os.makedirs(D); os.makedirs(J)
        env = dict(os.environ, WALLGUARD_DIR=D, WALLGUARD_JFFS=J, WALLGUARDC=SCW, PATH=bindir + ":" + os.environ["PATH"], LC_ALL="C")
        def run(*a):
            cmd = (["sh", SH_FILE] if shell == "sh" else [BB, "ash", SH_FILE]) + list(a)
            return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
        def settle(limit=10):
            # 2026-10-25 (release review X-1): the history writer runs detached - wait for it before looking
            end = time.time() + limit
            while time.time() < end and (os.path.exists(os.path.join(D, "hist.work")) or os.path.exists(os.path.join(D, "hist.q"))):
                time.sleep(0.05)
        def logtxt(): return open(os.path.join(work, "logger.out")).read()
        open(os.path.join(srv, "one.txt"), "w").write("||ads.example^\n||track.example^\n")
        open(os.path.join(srv, "two.txt"), "w").write("0.0.0.0 host.example\n")
        open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n20 two https://test/two.txt c\n21 gone https://test/gone.txt c\n")
        open(os.path.join(D, "safe"), "w").write("router.lan\n")
        open(os.path.join(J, "block"), "w").write("mine.example\n")
        open(os.path.join(J, "allow24"), "w").write("%d expired.example\n%d still.example\n" % (time.time() - 10, time.time() + 3600))
        r = run("update")
        st = {l.split()[0]: l.split() for l in open(os.path.join(D, "state")).read().splitlines()}
        bj = json.load(open(os.path.join(D, "build.json"))) if os.path.exists(os.path.join(D, "build.json")) else {}
        check("[%s] update: lists fetched, state ok / missing, table built" % tag,
              r.returncode == 0 and st["one"][1] == "ok" and st["two"][1] == "ok" and st["gone"][1] == "missing" and bj.get("names") == 4, (r.stderr, st, bj))
        check("[%s] build: expired temporary allows dropped from the file, running ones passed on" % tag,
              open(os.path.join(J, "allow24")).read().count("example") == 1 and open(os.path.join(D, "allow24")).read().strip() == "still.example")
        open(os.path.join(srv, "one.txt.fail"), "w").close()
        open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n")
        run("update"); st = {l.split()[0]: l.split() for l in open(os.path.join(D, "state")).read().splitlines()}
        check("[%s] a failed download keeps the previous copy (state failed, last good time kept)" % tag,
              st["one"][1] == "failed" and int(st["one"][2]) > 0 and os.path.exists(os.path.join(D, "lists", "one")))
        check("[%s] an unsubscribed list leaves the RAM disk" % tag, not os.path.exists(os.path.join(D, "lists", "two")))
        check("[%s] the failure is logged" % tag, "download failed, previous copy kept" in open(os.path.join(work, "logger.out")).read())
        os.unlink(os.path.join(srv, "one.txt.fail"))
        open(os.path.join(J, "block"), "w").write("mine.example\nother.example\n")
        r = run("build")
        check("[%s] build after a rule change: no download, the new rule is in" % tag,
              r.returncode == 0 and json.load(open(os.path.join(D, "build.json")))["names"] == 4)

        # ---- release review 2026-10-25 (W-1): every download fails (a boot before the WAN is up). The table still
        # carries My rules, so the "no table yet" retries would never fire again; the pending mark keeps the lists owed
        # (rc fetches again at WAN up, rwatch every 10 min) and one good update clears it
        wl = os.path.join(D, "lists")
        for f in os.listdir(wl): os.remove(os.path.join(wl, f))
        os.remove(os.path.join(D, "db"))
        open(os.path.join(srv, "one.txt.fail"), "w").close()
        run("update")
        check("[%s] W-1: every list download failed - a My-rules table is built and the pending mark is set, logged" % tag,
              os.path.exists(os.path.join(D, "db")) and os.path.exists(os.path.join(D, "pending"))
              and "no block list could be downloaded" in logtxt())
        os.remove(os.path.join(srv, "one.txt.fail"))
        run("update")
        check("[%s] W-1: the next good update clears the mark" % tag,
              not os.path.exists(os.path.join(D, "pending")) and os.path.isfile(os.path.join(wl, "one")))
        # X-2: the lists kept in RAM stay under the cap together (one.txt 32 B is in RAM, two.txt 21 B would pass 40 B);
        # nothing is fetched while memory is short, and the copy already held stays
        env["WALLGUARD_RAM_CAP"] = "40"
        open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n20 two https://test/two.txt c\n")
        run("update")
        check("[%s] X-2: a list that would take the RAM-held lists past the cap is not taken, and says why" % tag,
              os.path.isfile(os.path.join(wl, "one")) and not os.path.exists(os.path.join(wl, "two"))
              and "list two: not taken, the lists kept in RAM would pass 0 MB" in logtxt(), logtxt()[-300:])
        del env["WALLGUARD_RAM_CAP"]; env["WALLGUARD_MEM_MIN_KB"] = "999999999"
        run("update")
        check("[%s] X-2: nothing is fetched while memory is short; the list held stays (state failed)" % tag,
              "list one: not fetched, less than" in logtxt() and os.path.isfile(os.path.join(wl, "one"))
              and open(os.path.join(D, "state")).read().startswith("one failed"), logtxt()[-300:])
        del env["WALLGUARD_MEM_MIN_KB"]
        open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n")
        run("update")

        now = int(time.time())
        RUN = os.path.join(D, "run"); os.makedirs(RUN, exist_ok=True)
        open(os.path.join(RUN, "hits"), "w").write(
            "%d 192.168.50.10 4 q 00:00:5e:00:53:01 ads.example\n%d 192.168.50.10 4 q 00:00:5e:00:53:01 ads.example\n"
            "%d 192.168.50.20 100004 c - edge.track.example\n# dropped 7\nnot a record\n"
            "%d 192.168.50.30 4 q - BAD\"name\n%d 192.168.50.30 zz q - x.example\n"
            # a forged address or MAC field never reaches the counters
            "%d 1.2.3.4\" 4 q - forged1.example\n%d 192.168.50.30 4 q aa:bb\"cc forged2.example\n"
            % (now - 5, now - 4, now - 3, now - 2, now - 1, now - 1, now - 1))
        open(os.path.join(RUN, "stats.%d" % os.getpid()), "w").write("%d 120 3 1" % now + " 0" * 31 + "\n")
        open(os.path.join(RUN, "stats.999999"), "w").write("%d 999 9 9\n" % now)
        r = run("stats")
        try:
            j = json.loads(r.stdout)
        except Exception as e:
            j = {}; check("[%s] stats: valid JSON" % tag, False, "%s %s %s" % (e, r.stdout[:300], r.stderr[:300]))
        if j:
            check("[%s] stats: valid JSON; queries summed over LIVE instances only (a dead pid's file removed)" % tag,
                  j["ok"] == 1 and j["queries"] == 120 and not os.path.exists(os.path.join(RUN, "stats.999999")), j.get("queries"))
            check("[%s] stats: totals, cname, '# dropped' banked, junk records never counted" % tag,
                  j["total"] == 3 and j["cname"] == 1 and j["dropped"] == 7, j)
            check("[%s] stats: per-list tallies from the hex bit field (0x100004 = bits 2 and 20)" % tag,
                  [f["blocked"] for f in j["feeds"]] == [3], j["feeds"])
            check("[%s] stats: top names sorted, devices keyed by MAC with their address" % tag,
                  j["top"][0]["d"] == "ads.example" and j["top"][0]["n"] == 2
                  and any(d["dev"] == "00:00:5e:00:53:01" and d["ip"] == "192.168.50.10" for d in j["devices"]), (j["top"], j["devices"]))
            check("[%s] stats: the build report rides along" % tag, j["build"]["names"] == 4)
        u = json.loads(run("unbreak", "00:00:5e:00:53:01", "15").stdout)
        check("[%s] unbreak: the device's recent blocked names (by MAC)" % tag, [x["d"] for x in u["names"]] == ["ads.example"], u)
        u = json.loads(run("unbreak", "192.168.50.20", "15").stdout)
        check("[%s] unbreak: by address too, CNAME hits included" % tag, [x["d"] for x in u["names"]] == ["edge.track.example"], u)
        open(os.path.join(RUN, "live"), "w").write("%d 192.168.50.10 1 b ads.example\n%d 192.168.50.10 1 - news.example\nbroken line\n"
                                                    "%d 1.2.3.4\" 1 b forged.example\n" % (now, now, now))
        lv = json.loads(run("live").stdout)
        check("[%s] live: rows as JSON, junk dropped" % tag, [x["d"] for x in lv["rows"]] == ["ads.example", "news.example"], lv)
        check("[%s] the counters are banked on /jffs" % tag, os.path.exists(os.path.join(J, "counters")))
        # ---- phase 2 (2026-10-21): a profile's blocked services (kind s) and safe search
        os.makedirs(os.path.join(D, "lists"), exist_ok=True)
        open(os.path.join(D, "lists", "svc_kids"), "w").write("*.tiktok.com\n*.tiktokv.com\n")
        open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n10 svc_kids - s\n11 svc_evil https://test/one.txt s\n")
        open(os.path.join(srv, "supported_domains"), "w").write(".google.com\n.google.de\n.google.co.uk\nnot-a-google-line\n")
        r = run("update")
        st2 = {l.split()[0]: l.split() for l in open(os.path.join(D, "state")).read().splitlines()}
        bj = json.load(open(os.path.join(D, "build.json")))
        src2 = {x["id"]: x for x in bj.get("sources", [])}
        check("[%s] a profile's service list (kind s) is built under its bit and never fetched; a kind-s line with a URL is refused" % tag,
              r.returncode == 0 and "svc_kids" in src2 and src2["svc_kids"]["unique"] == 2 and "svc_kids" not in st2
              and "svc_evil" not in src2, (src2.keys(), st2.keys()))
        ss = open(os.path.join(D, "safesearch")).read() if os.path.exists(os.path.join(D, "safesearch")) else ""
        check("[%s] update writes safesearch: Google's country domains (www. and bare), Bing, DuckDuckGo, YouTube names" % tag,
              all(x in ss for x in ("name g www.google.de\n", "name g google.co.uk\n", "name g www.google.com\n", "name b www.bing.com\n",
                                     "name d duckduckgo.com\n", "name y www.youtube.com\n")) and "not-a-google" not in ss, ss[:300])
        check("[%s] ...with the resolved enforcement addresses per group (y moderate, Y strict); an unresolved group has none" % tag,
              all(x in ss for x in ("addr g 216.239.38.120\n", "addr g 2001:4860:4802:32::78\n", "addr y 216.239.38.119\n",
                                     "addr Y 216.239.38.120\n", "addr b 204.79.197.220\n")) and "addr d " not in ss, ss[-300:])
        open(os.path.join(work, "resolve.fail"), "w").close()
        open(os.path.join(srv, "supported_domains.fail"), "w").close()
        run("safe")
        ss2 = open(os.path.join(D, "safesearch")).read()
        check("[%s] a refresh that cannot resolve or fetch keeps the previous addresses and country domains" % tag,
              "addr g 216.239.38.120\n" in ss2 and "addr Y 216.239.38.120\n" in ss2 and "name g www.google.de\n" in ss2, ss2[-300:])
        os.remove(os.path.join(work, "resolve.fail")); os.remove(os.path.join(srv, "supported_domains.fail"))
        open(os.path.join(RUN, "live"), "w").write("%d 192.168.50.10 1 s www.google.com\n" % now)
        lv2 = json.loads(run("live").stdout)
        check("[%s] live: the safe-search verdict 's' is shown" % tag, [x["v"] for x in lv2["rows"]] == ["s"], lv2)
        open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n")

        # review 2026-10-21: what reaches root from dnsmasq's run/ or a rewritten feeds file
        secret = os.path.join(work, "secret"); open(secret, "w").write("%d 10.0.0.1 4 q - leaked.example\n" % now)
        os.symlink(secret, os.path.join(RUN, "hits"))
        run("fold")
        check("[%s] a symlink planted at run/hits is dropped unread" % tag,
              "leaked.example" not in open(os.path.join(D, "counters")).read() and os.path.exists(secret))
        open(os.path.join(D, "feeds"), "w").write("2 ../../escape https://test/one.txt p\n2 one ftp://test/one.txt p\n")
        run("update")
        check("[%s] a feed line with a path in its id or a non-https URL is skipped" % tag,
              not os.path.exists(os.path.join(work, "escape")) and not os.path.exists(os.path.join(D, "escape"))
              and "is not valid - skipped" in open(os.path.join(work, "logger.out")).read())
        run("reset")
        j = json.loads(run("stats").stdout)
        check("[%s] reset: counters restart, recent list cleared" % tag,
              j["total"] == 0 and not os.path.exists(os.path.join(D, "recent")) and not os.path.exists(os.path.join(J, "counters")), j)

        # review 2026-10-24 (S-A-1): the counters hold the 200 busiest names and the 200 busiest devices, never every
        # distinct one - 261 names and 231 devices go in, 200 of each come out, the busiest first
        lines = ["%d 192.168.50.10 4 q - busy.example" % now] * 5
        lines += ["%d 192.168.50.10 4 q - n%03d.example" % (now, i) for i in range(260)]
        lines += ["%d 10.9.%d.%d 4 q - ads.example" % (now, i // 250, i % 250 + 1) for i in range(230)]
        open(os.path.join(RUN, "hits"), "w").write("\n".join(lines) + "\n")
        run("fold")
        ctr = open(os.path.join(D, "counters")).read().splitlines()
        names = [l.split() for l in ctr if l.startswith("NAME ")]; devs = [l.split() for l in ctr if l.startswith("DEV ")]
        check("[%s] fold caps the counters at the 200 busiest names and the 200 busiest devices" % tag,
              len(names) == 200 and len(devs) == 200, (len(names), len(devs)))
        check("[%s] ...busiest first, the rest of the rows intact (ads.example 230, busy.example 5, the device with 265)" % tag,
              names[0][1:3] == ["ads.example", "230"] and ["busy.example", "5"] in [n[1:3] for n in names]
              and devs[0][1:3] == ["192.168.50.10", "265"] and all(len(n) == 5 for n in names) and all(len(d) == 5 for d in devs), (names[:2], devs[:1]))
        check("[%s] ...the other counters unaffected (no stale helper files left)" % tag,
              any(l == "TOTAL 495" for l in ctr) and not os.path.exists(os.path.join(D, "counters.names")) and not os.path.exists(os.path.join(D, "counters.devs")), ctr[:4])
        j = json.loads(run("stats").stdout)
        check("[%s] ...and stats still reports the busiest name on top" % tag, j["top"][0]["d"] == "ads.example" and j["top"][0]["n"] == 230 and j["total"] == 495, (j["top"][:1], j["total"]))
        run("reset")

        # ---- Long-Term Storage (2026-10-21): lists on the pinned USB volume (shl), blocked-lookup
        # history (shh). The watchdog's published location is faked through the RSTORE_* variables.
        mnt = os.path.join(work, tag, "mnt"); vol = os.path.join(mnt, "RUSB"); base = os.path.join(vol, ".reaper")
        os.makedirs(base); open(os.path.join(base, "store.id"), "w").write("abcdef0123456789")
        jb = os.path.join(work, tag, "jb"); os.makedirs(jb)
        pub, mounts = os.path.join(work, tag, "store.base"), os.path.join(work, tag, "mounts")
        def publish(b, ds): open(pub, "w").write("%s\n,%s,\n" % (b, ds))
        def mount(*vols): open(mounts, "w").write("".join("/dev/sda1 %s ext4 rw 0 0\n" % v for v in vols))
        rsx = os.path.join(work, tag, "rstore")
        check("[%s] LTS: rstore builds for the host" % tag, build_rstore(rsx, mnt, jb))
        env = dict(env, RSTORE_PUB_F=pub, RSTORE_MNT_D=mnt, RSTORE_MOUNTS=mounts, RSTORE_JFFS_D=jb, RSTORE=rsx)
        S, L, DB = os.path.join(base, "wallguard", "lists"), os.path.join(D, "lists"), os.path.join(D, "db")
        def srcs():
            p = os.path.join(D, "build.json")
            return {x["id"] for x in json.load(open(p)).get("sources", [])} if os.path.exists(p) else set()
        def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
        def fail(on):
            for f in ("one.txt.fail", "two.txt.fail"):
                p = os.path.join(srv, f)
                if on: open(p, "w").close()
                elif os.path.exists(p): os.remove(p)
        publish(base, "shl,shh"); mount(vol); fail(False)
        open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n20 two https://test/two.txt c\n")
        r = run("update")
        sums = {l.split()[0]: l.split()[1] for l in open(os.path.join(J, "lists.sum")).read().splitlines()} if os.path.exists(os.path.join(J, "lists.sum")) else {}
        check("[%s] LTS: with Wallguard block lists on USB, downloaded lists move to the volume and leave RAM; sha256 kept on /jffs" % tag,
              all(os.path.isfile(os.path.join(S, x)) and not os.path.exists(os.path.join(L, x)) and sums.get(x) == sha(os.path.join(S, x))
                  for x in ("one", "two")), (r.stderr[-300:], sums, os.listdir(L) if os.path.isdir(L) else None))
        check("[%s] LTS: ...and the table is built from the volume's copies" % tag, {"one", "two"} <= srcs(), srcs())
        j = json.loads(run("stats").stdout)
        check("[%s] LTS: stats names the volume holding the lists and where the history goes" % tag,
              j.get("store") == "RUSB" and j.get("hist") == "usb" and j.get("histvol") == "RUSB", j.get("store"))
        os.remove(DB); fail(True)
        run("restore")
        check("[%s] LTS: restore - no table yet, no network: built from the volume" % tag,
              os.path.exists(DB) and {"one", "two"} <= srcs() and "building from the lists on the USB volume" in logtxt(), srcs())
        open(os.path.join(S, "one"), "a").write("||evil.example^\n"); os.remove(DB)
        run("restore")
        check("[%s] LTS: a list changed on the shared volume is never used" % tag,
              os.path.exists(DB) and "one" not in srcs() and "two" in srcs() and "does not match its last download" in logtxt(), srcs())
        mount(); ino = os.stat(DB).st_ino
        r = run("build")
        check("[%s] LTS: volume unmounted - a rebuild keeps the table in use and says why" % tag,
              r.returncode != 0 and os.stat(DB).st_ino == ino and "have no usable copy" in logtxt(), r.returncode)
        check("[%s] LTS: ...and stats no longer names a volume" % tag, json.loads(run("stats").stdout).get("store") == "")
        fail(False); run("update")
        check("[%s] LTS: ...while it is away, downloads land in RAM and the table is built from them" % tag,
              os.path.isfile(os.path.join(L, "one")) and os.path.isfile(os.path.join(L, "two")) and {"one", "two"} <= srcs())
        mount(vol)
        open(os.path.join(RUN, "hits"), "w").write("%d 192.168.50.10 4 q - ads.example\n" % now)
        run("fold"); settle()
        h = os.path.join(base, "wallguard", "blocked.log")
        check("[%s] LTS: Wallguard blocked lookups - folded records appended on the volume" % tag,
              os.path.exists(h) and open(h).read().endswith("192.168.50.10 4 q - ads.example\n"))
        # X-1 (release review 2026-10-25): a USB disk that is slow or hung never holds up the page's stats (httpd waits for
        # it) nor the next fold - the records are queued and one detached writer appends them
        slow = os.path.join(work, tag, "rstore-slow")
        open(slow, "w").write("#!/bin/sh\nsleep 3\nexec %s \"$@\"\n" % rsx); os.chmod(slow, 0o755)
        env["RSTORE"] = slow
        open(os.path.join(RUN, "hits"), "w").write("%d 192.168.50.10 4 q - slow.example\n" % now)
        t0 = time.time(); r1 = run("stats"); open(os.path.join(RUN, "hits"), "w").write("%d 192.168.50.10 4 q - next.example\n" % now)
        run("fold"); dt = time.time() - t0
        check("[%s] X-1: stats and the next fold return while the history writer still waits on the disk" % tag,
              dt < 2.5 and json.loads(r1.stdout).get("ok") == 1 and "slow.example" not in open(h).read(), dt)
        settle(); time.sleep(3.5); settle()
        env["RSTORE"] = rsx
        run("fold"); settle()
        check("[%s] X-1: ...and every queued record lands once the disk answers" % tag,
              "slow.example" in open(h).read() and "next.example" in open(h).read(), open(h).read()[-200:])
        publish(jb, "shh"); os.makedirs(os.path.join(jb, "wallguard"))
        big = os.path.join(jb, "wallguard", "blocked.log"); open(big, "w").write("x" * (2097152 + 10) + "\n")
        open(os.path.join(RUN, "hits"), "w").write("%d 192.168.50.11 4 q - track.example\n" % now)
        run("fold"); settle()
        check("[%s] LTS: past the cap (JFFS 2 MB) the history rolls to .1 before the append" % tag,
              os.path.getsize(big + ".1") > 2097152 and open(big).read().endswith("track.example\n") and os.path.getsize(big) < 200)
        publish(base, "shh"); j = json.loads(run("stats").stdout)
        check("[%s] LTS: lists not ticked - no volume for them, the history still goes to USB" % tag,
              j.get("store") == "" and j.get("hist") == "usb", (j.get("store"), j.get("hist")))
        evil = os.path.join(mnt, "EVIL"); os.makedirs(evil); os.symlink(base, os.path.join(evil, ".reaper"))
        mount(vol, evil); publish(os.path.join(evil, ".reaper"), "shl,shh"); j = json.loads(run("stats").stdout)
        check("[%s] LTS: a store base that is a symlink is never used" % tag, j.get("store") == "" and j.get("hist") == "", j.get("hist"))
        publish(base, "shl,shh"); mount(vol)
        for f in os.listdir(S): os.remove(os.path.join(S, f))
        os.remove(DB); run("restore")
        check("[%s] LTS: restore never builds a table from My rules alone (nothing usable on the volume)" % tag, not os.path.exists(DB))
        open(os.path.join(S, "two"), "w").write("0.0.0.0 old.example\n")
        open(os.path.join(D, "feeds"), "w").write("2 one https://test/one.txt p\n")
        run("update")
        precious = os.path.join(work, tag, "precious"); open(precious, "w").write("KEEP\n")
        hl = os.path.join(base, "wallguard", "blocked.log")
        if os.path.exists(hl): os.remove(hl)
        os.symlink(precious, hl); publish(base, "shl,shh")
        open(os.path.join(RUN, "hits"), "w").write("%d 192.168.50.12 4 q - planted.example\n" % now)
        run("fold"); settle()
        check("[%s] LTS: a link planted at blocked.log is never written through (review 2026-10-21)" % tag,
              open(precious).read() == "KEEP\n" and not os.path.islink(hl) and "planted.example" in open(hl).read())
        check("[%s] LTS: an unsubscribed list is removed from the volume too" % tag,
              not os.path.exists(os.path.join(S, "two")) and os.path.isfile(os.path.join(S, "one")) and os.path.exists(DB))
finally:
    shutil.rmtree(work, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
