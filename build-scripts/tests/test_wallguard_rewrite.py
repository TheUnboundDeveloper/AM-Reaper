#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wallguard DNS rewrites (owner, 2026-11-05): local names on a page instead of dnsmasq.conf.add over SSH.

WHY THIS EXISTS. A rewrite answers a name with an address or another name, on every network, the way AdGuard
Home's and Pi-hole's local DNS records do. The rows become dnsmasq configuration, and dnsmasq refuses to START
on a duplicate alias or an alias loop - one bad row would take DNS down for every network. And Wallguard's
engine runs before the cache, so without its own check a block list would beat a rewritten name.

WHAT IT DOES.
  1. Compiles shared/reaper_rewrite.h (the one set of rules httpd and rc use) on the host, -Wall -Werror:
     names, answers, the "sub" flag, and the generator - every row type, duplicates, the alias rows that would
     stop dnsmasq (dropped and counted), characters that could start a second option (refused).
  2. Builds the patched dnsmasq and proves the generated file on it: --test accepts the output even for the
     rows dnsmasq itself refuses (shown on a raw file first); a running dnsmasq with --wallguard-dir and a
     table that lists the rewritten names answers the rewrites (A, AAAA, alias, name + subdomains, mixed
     case), keeps a rewrite exact (a subdomain is still the list's), and still blocks a name that is no rewrite.
  3. Pins the wiring: rc writes the include and restarts dnsmasq once on a change, every instance includes it,
     httpd checks and stores it with Wallguard's files (page save and settings import), the page's table and
     its strings in all 25 language packs.
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, random, re, shutil, socket, struct, subprocess, sys, tempfile, threading, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "reaper_rewrite.h")):
    skip("no router source tree with shared/reaper_rewrite.h (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host compiler")

def read(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()

work = tempfile.mkdtemp(prefix="wgrw_")
procs, stop = [], threading.Event()
try:
    # ---- 1. the shared rules
    H = r'''#define _GNU_SOURCE
#include <reaper_rewrite.h>
int main(int argc, char **argv) {
  static char in[200000], out[300000];
  size_t n = fread(in, 1, sizeof(in) - 1, stdin);
  in[n] = 0;
  if (!strcmp(argv[1], "parse")) {
    char *l, *s = NULL;
    for (l = strtok_r(in, "\n", &s); l; l = strtok_r(NULL, "\n", &s)) {
      struct rrw r;
      if (rrw_parse(l, &r)) printf("ok %d %s %s %d\n", r.type, r.name, r.ans, r.sub); else printf("bad\n");
    }
  } else {
    int sk = -1;
    size_t o = rrw_conf(in, out, argc > 2 ? (size_t)atoi(argv[2]) : sizeof(out), &sk);
    printf("%s#skipped %d bytes %zu\n", out, sk, o);
  }
  return 0;
}
'''
    hc = os.path.join(work, "h.c"); open(hc, "w").write(H)
    HX = os.path.join(work, "h")
    b = subprocess.run([CC, "-Wall", "-Wextra", "-Werror", "-I", os.path.join(SRC, "shared"), "-o", HX, hc], capture_output=True, text=True)
    check("shared/reaper_rewrite.h compiles on the host with -Wall -Wextra -Werror", b.returncode == 0, b.stderr[-800:])
    if b.returncode:
        raise SystemExit
    def run(mode, text, *extra):
        return subprocess.run([HX, mode] + list(extra), input=text, capture_output=True, text=True).stdout
    cases = [
        ("nas.home.arpa 192.168.50.20", "ok 1 nas.home.arpa 192.168.50.20 0"),
        ("nas.home.arpa fd00::20", "ok 2 nas.home.arpa fd00::20 0"),
        ("lab.test 10.1.2.3 sub", "ok 1 lab.test 10.1.2.3 1"),
        ("www.home.arpa nas.home.arpa", "ok 3 www.home.arpa nas.home.arpa 0"),
        ("nas 192.168.50.20", "ok 1 nas 192.168.50.20 0"),                       # one label
        ("_svc.x-1.example\t\t10.0.0.1", "ok 1 _svc.x-1.example 10.0.0.1 0"),     # tabs, underscore
        ("www.home.arpa nas.home.arpa sub", "bad"),     # an alias covers the name only
        ("a.example a.example", "bad"),                 # alias to itself
        ("a.example 1.2.3.4 all", "bad"),               # unknown flag
        ("a.example 1.2.3.4 sub x", "bad"),             # trailing text
        ("a.example", "bad"),
        ("A.example 1.2.3.4", "bad"),                   # upper case: httpd lowers it first
        ("a,b.example 1.2.3.4", "bad"),                 # a comma would split a host-record
        ("a/b.example 1.2.3.4", "bad"),                 # a slash would split an address=
        ("a.example 1.2.3.4,5.6.7.8", "bad"),
        ("a.example fe80::1%eth0", "bad"),
        ("a.example 1.2.3", "bad"),                     # a mistyped address is not taken as a name of digits
        ("a.example 1.2.3.4.5", "bad"), ("123.456 1.2.3.4", "bad"),
        ("-a.example 1.2.3.4", "bad"), ("a-.example 1.2.3.4", "bad"), ("a..example 1.2.3.4", "bad"),
        (".a.example 1.2.3.4", "bad"), ("a.example. 1.2.3.4", "bad"),
        ("x" * 64 + ".example 1.2.3.4", "bad"), ("localhost 127.0.0.2", "bad"), ("1.2.3.4 5.6.7.8", "bad"),
        ("a.example 01.2.3.4", "bad"),
    ]
    out = run("parse", "\n".join(c for c, _ in cases) + "\n").splitlines()
    got = dict(zip([c for c, _ in cases], out))
    wrong = [(c, got.get(c), w) for c, w in cases if got.get(c) != w]
    check("rrw_parse: addresses, aliases, the sub flag, one-label names; commas, slashes, zones, case, bad labels, mistyped addresses refused", not wrong, wrong)
    long_ok = ".".join(["a" * 63] * 3) + "." + "b" * 61    # 253 characters
    check("a 253-character name is taken, 254 refused",
          run("parse", long_ok + " 1.2.3.4\n" + long_ok + "b 1.2.3.4\n").splitlines() == ["ok 1 %s 1.2.3.4 0" % long_ok, "bad"])

    TABLE = ("nas.home.arpa 192.168.50.20\n"
             "nas.home.arpa fd00::20\n"
             "lab.test 10.1.2.3 sub\n"
             "lab.test fd00::3 sub\n"
             "www.home.arpa nas.home.arpa\n"
             "nas.home.arpa 192.168.50.20\n"           # the same row twice: once
             "www.home.arpa other.home.arpa\n"         # the alias again: dnsmasq would not start
             "nas.home.arpa www.home.arpa\n"           # an alias for a name that has addresses
             "chain.home.arpa www.home.arpa\n"         # an alias of an alias (a chain)
             "loop1.home.arpa loop2.home.arpa\n"       # a loop: dnsmasq dies on it
             "loop2.home.arpa loop1.home.arpa\n"
             "\n# a comment\n"
             "BAD LINE\n")
    conf = run("conf", TABLE)
    body, tail = conf.rsplit("#skipped ", 1)
    sk = int(tail.split()[0])
    want = ["host-record=nas.home.arpa,192.168.50.20", "host-record=nas.home.arpa,fd00::20", "address=/lab.test/10.1.2.3",
            "address=/lab.test/fd00::3", "cname=www.home.arpa,nas.home.arpa",
            "local=/nas.home.arpa/", "server=/*.nas.home.arpa/#", "local=/lab.test/"]
    check("rrw_conf: host-record for a name, address= for name + subdomains, cname= for an alias; duplicates once; "
          "then local= once per name and server=/*.name/# for a name without subdomains", body.splitlines() == want, body.splitlines())
    kid = run("conf", "kid.lab.test 10.6.6.6\nlab.test 10.1.2.3 sub\nLab.test 1.1.1.1\n").rsplit("#skipped", 1)[0].splitlines()
    check("rrw_conf: a name under a name-and-subdomains row gets no local= / server= line (the row above answers the rest)",
          kid == ["host-record=kid.lab.test,10.6.6.6", "address=/lab.test/10.1.2.3", "local=/lab.test/"], kid)
    check("rrw_conf: the repeated alias, the alias of a named address, the chain, both loop rows and the unreadable line are left out and counted",
          sk == 6, sk)
    check("rrw_conf: nothing to include is 0 bytes and an empty text",
          run("conf", "\n# only a comment\n") == "#skipped 0 bytes 0\n")
    small = run("conf", TABLE, "60")
    check("rrw_conf: a full buffer stops at a whole line, never half of one",
          all(l in want for l in small.rsplit("#skipped", 1)[0].splitlines()), small)
    many = "".join("h%d.example 10.0.%d.%d\n" % (i, i // 250, i % 250) for i in range(600))
    mc = run("conf", many)
    check("rrw_conf: at most 512 rows are read; the rest are counted", mc.count("host-record=") == 512 and "#skipped 88 " in mc, mc[-60:])

    # ---- 2. dnsmasq: the generated include, and a running instance with Wallguard on
    db = os.path.join(work, "dnsmasq")
    shutil.copytree(os.path.join(SRC, "dnsmasq"), db, symlinks=True, ignore=shutil.ignore_patterns("*.o", "dnsmasq"))
    b = subprocess.run(["make", "-C", db, "COPTS=-DNO_DBUS -DNO_INOTIFY -DHAVE_BROKEN_RTC", "CC=" + CC, "-j4"], capture_output=True, text=True, timeout=900)
    DB = os.path.join(db, "src", "dnsmasq")
    check("the patched dnsmasq builds for the host", b.returncode == 0 and os.path.exists(DB), (b.stdout + b.stderr)[-600:])
    warn = [l for l in (b.stdout + b.stderr).splitlines() if "warning" in l and "wallguard.c" in l]
    check("...without warnings from wallguard.c", not warn, warn[:5])
    if b.returncode or not os.path.exists(DB):
        raise SystemExit
    def dtest(text):
        p = os.path.join(work, "t%d.conf" % random.randint(0, 1 << 30)); open(p, "w").write(text)
        r = subprocess.run([DB, "--test", "-C", p], capture_output=True, text=True)
        return r.returncode, (r.stdout + r.stderr).strip()
    rc_dup, msg_dup = dtest("cname=a.example,b.example\ncname=a.example,c.example\n")
    rc_loop, msg_loop = dtest("cname=a.example,b.example\ncname=b.example,a.example\n")
    check("why rows are dropped: dnsmasq itself refuses a repeated alias and an alias loop",
          rc_dup != 0 and "CNAME" in msg_dup and rc_loop != 0 and "loop" in msg_loop.lower(), (msg_dup, msg_loop))
    rc_ok, msg_ok = dtest(body)
    check("the generated include passes dnsmasq --test (the same table, those rows dropped)", rc_ok == 0, msg_ok)

    SC = os.path.join(work, "wallguardc")
    b = subprocess.run([CC, "-O2", "-o", SC, os.path.join(SRC, "wallguard", "wallguardc.c")], capture_output=True, text=True)
    check("wallguardc builds", b.returncode == 0, b.stderr[-400:])
    SD = os.path.join(work, "sd"); os.makedirs(os.path.join(SD, "run"))
    rules = os.path.join(work, "rules")
    # My rules list every rewritten name (and so their subdomains) plus a name that is no rewrite
    open(rules, "w").write("nas.home.arpa\nwww.home.arpa\nlab.test\nblocked.example\n")
    b = subprocess.run([SC, "build", "--out", os.path.join(SD, "db"), "--rules", rules], capture_output=True, text=True)
    check("a table listing the rewritten names is built", b.returncode == 0, b.stderr[-400:])
    open(os.path.join(SD, "policy"), "w").write("default 7fffffff 0\n")

    UP, PORT = 5411, 5412
    def enc(name):
        return b"".join(bytes([len(l)]) + l.encode() for l in name.split(".")) + b"\0"
    def qname_end(m):
        i = 12
        while m[i]: i += m[i] + 1
        return i + 5
    us = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); us.bind(("127.0.0.1", UP)); us.settimeout(0.3)
    def serve():
        while not stop.is_set():
            try: m, a = us.recvfrom(4096)
            except socket.timeout: continue
            qe = qname_end(m)
            qt = struct.unpack(">H", m[qe - 4:qe - 2])[0]
            rr, an = b"", 0
            if qt == 1:
                rr, an = b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, 300, 4) + socket.inet_aton("192.0.2.53"), 1
            elif qt == 28:   # so a forwarded AAAA is told apart from the router's own empty answer
                rr, an = b"\xc0\x0c" + struct.pack(">HHIH", 28, 1, 300, 16) + socket.inet_pton(socket.AF_INET6, "2001:db8::53"), 1
            elif qt == 65:   # an HTTPS record (could carry address hints around a rewrite)
                rr, an = b"\xc0\x0c" + struct.pack(">HHIH", 65, 1, 300, 3) + b"\x00\x01\x00", 1
            us.sendto(m[:2] + b"\x81\x80" + m[4:6] + struct.pack(">HHH", an, 0, 0) + m[12:qe] + rr, a)
    threading.Thread(target=serve, daemon=True).start()
    extra = run("conf", "v4only.home.arpa 10.9.9.9\nv4sub.test 10.8.8.8 sub\nkid.v4sub.test 10.6.6.6\n").rsplit("#skipped", 1)[0]
    inc = os.path.join(work, "rewrite.conf"); open(inc, "w").write(body + extra)
    cf = os.path.join(work, "d.conf")
    open(cf, "w").write("port=%d\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\npid-file=\n"
                        "server=127.0.0.1#%d\nwallguard-dir=%s\nconf-file=%s\n" % (PORT, UP, SD, inc))
    dp = subprocess.Popen([DB, "-k", "-C", cf, "--log-facility=-"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    procs.append(dp); time.sleep(0.8)
    check("dnsmasq starts with the include and --wallguard-dir", dp.poll() is None, dp.stderr.read().decode()[-300:] if dp.poll() is not None else "")

    def q(name, qtype=1):
        m = struct.pack(">HHHHHH", random.randint(1, 65535), 0x0100, 1, 0, 0, 0) + enc(name) + struct.pack(">HH", qtype, 1)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(3); s.sendto(m, ("127.0.0.1", PORT))
        try: r = s.recv(4096)
        finally: s.close()
        rcode, an, ns_, ar = r[3] & 0x0f, *struct.unpack(">HHH", r[6:12])
        i, addrs, types = qname_end(r), [], []
        for _ in range(an):
            if r[i] & 0xc0 == 0xc0: i += 2
            else:
                while r[i]: i += r[i] + 1
                i += 1
            t, _c, _ttl, rdl = struct.unpack(">HHIH", r[i:i + 10]); i += 10
            types.append(t)
            if t == 1: addrs.append(socket.inet_ntoa(r[i:i + 4]))
            if t == 28: addrs.append(socket.inet_ntop(socket.AF_INET6, r[i:i + 16]))
            i += rdl
        return rcode, addrs, types

    check("control: a listed name that is no rewrite is still blocked", q("blocked.example")[1] == ["0.0.0.0"], q("blocked.example"))
    check("a rewritten name answers the rewrite although a list names it (A)", q("nas.home.arpa")[1] == ["192.168.50.20"], q("nas.home.arpa"))
    check("...and AAAA", q("nas.home.arpa", 28)[1] == ["fd00::20"], q("nas.home.arpa", 28))
    check("...in any letter case", q("NAS.Home.ARPA")[1] == ["192.168.50.20"], q("NAS.Home.ARPA"))
    r = q("www.home.arpa")
    check("an alias answers CNAME + its target's address, not the list's block", 5 in r[2] and r[1] == ["192.168.50.20"], r)
    check("name + subdomains: the name and a deep subdomain get the address (A and AAAA)",
          q("lab.test")[1] == ["10.1.2.3"] and q("a.b.lab.test")[1] == ["10.1.2.3"] and q("a.b.lab.test", 28)[1] == ["fd00::3"])
    check("an exact rewrite stays exact: its subdomain is still the list's to block", q("x.nas.home.arpa")[1] == ["0.0.0.0"], q("x.nas.home.arpa"))
    r1, r2 = q("v4only.home.arpa", 28), q("x.v4sub.test", 28)
    check("an IPv4-only rewrite answers AAAA empty from the router (exact and with subdomains), never forwarded",
          r1[0] == 0 and r1[1] == [] and r2[0] == 0 and r2[1] == [] and q("x.v4sub.test")[1] == ["10.8.8.8"], (r1, r2))
    r1, r2 = q("v4only.home.arpa", 65), q("x.v4sub.test", 65)
    check("...and HTTPS empty (no outside record can carry other addresses past the rewrite)",
          r1[0] == 0 and r1[2] == [] and r2[0] == 0 and r2[2] == [], (r1, r2))
    r1, r2 = q("www.v4only.home.arpa"), q("www.v4only.home.arpa", 28)
    check("a subdomain of an exact rewrite is looked up as usual (A and AAAA forwarded)",
          r1[1] == ["192.0.2.53"] and r2[1] == ["2001:db8::53"], (r1, r2))
    check("an exact name under a name-and-subdomains rewrite: its own address; the rest is the row above's",
          q("kid.v4sub.test")[1] == ["10.6.6.6"] and q("y.kid.v4sub.test")[1] == ["10.8.8.8"] and q("kid.v4sub.test", 28)[1] == [],
          (q("kid.v4sub.test"), q("y.kid.v4sub.test"), q("kid.v4sub.test", 28)))
    r = q("20.50.168.192.in-addr.arpa", 12)
    check("an exact rewrite answers the reverse lookup of its address (PTR)", r[0] == 0 and 12 in r[2], r)
    r = q("chain.home.arpa")
    check("a dropped row is simply not there: that name is looked up as usual", r[1] == ["192.0.2.53"] and 5 not in r[2], r)

    # ---- 3. the wiring
    rcw, web, svc, sdn, rch = read("rc/wallguard.c"), read("httpd/web.c"), read("rc/services.c"), read("rc/sdn.c"), read("rc/rc.h")
    eng, page = read("dnsmasq/src/wallguard.c"), read("www/Reaper_Wallguard.asp")
    check("rc: the include is built from /jffs/wallguard/rewrite with the shared rules, root 0644, tmp + rename",
          '#include <reaper_rewrite.h>' in rcw and 'rjf_get(SH_JFFS "/rewrite", &ex)' in rcw and "rrw_conf(" in rcw
          and "reaper_write_changed(SH_RW_CONF, out, n, 0644)" in rcw and '#define SH_RW_CONF	SH_DIR "/rewrite.conf"' in rcw)
    check("rc: no rows = no file (a missing include is fatal, so the line is only written while the file exists)",
          "unlink(SH_RW_CONF);" in rcw and "return f_exists(SH_RW_CONF) ? SH_RW_CONF : NULL;" in rcw)
    sync = re.search(r"\nstatic void sh_dns_sync\(void\)\n\{.*?\n\}\n", rcw, re.S)
    check("rc: a changed table, or an include that is missing or no longer wanted, is ONE dnsmasq restart beside the switch's",
          sync and "rw = sh_rw_write(0)" in sync.group(0) and "live != wanted || rw || inc != f_exists(SH_RW_CONF)" in sync.group(0)
          and sync.group(0).count("start_dnsmasq(") == 2 and 'notify_rc("' not in sync.group(0))
    check("rc: every instance includes it - the main one and each guest / VLAN network - Wallguard on or off",
          svc.count("reaper_wallguard_rewrite_conf()") == 1 and sdn.count("reaper_wallguard_rewrite_conf()") == 1
          and "extern const char *reaper_wallguard_rewrite_conf(void);" in rch
          and not re.search(r"reaper_wallguard_rewrite_conf\(void\)\n\{[^}]*wallguard_enabled", rcw))
    check("httpd: the rewrite file is one of Wallguard's files - the page's save and the settings import check it alike",
          '{ "rewrite", SH_JFFS "/rewrite", sh_chk_rewrite },' in web and "static int sh_chk_rewrite(char *l)" in web
          and '"reaper_rewrite.h"' in web and 'sh_json_file(stream, SH_JFFS "/rewrite");' in web
          and '{ "wallguard", "wallguard_rewrite", SH_LIST_MAX },' in web)
    chk = re.search(r"static int sh_chk_rewrite\(char \*l\)\n\{.*?\n\}\n", web, re.S)
    check("httpd: lower-cased, parsed by the shared rules, stored in its plain form (never longer than sent)",
          chk and "tolower(" in chk.group(0) and "rrw_parse(l, &r)" in chk.group(0) and "snprintf(l, n + 1," in chk.group(0))
    ca = re.search(r"static int wallguard_config_answer\(char \*name, unsigned short qtype\)\n\{.*?\n\}\n", eng, re.S)
    check("engine: the router's own records (rewrite, hosts, DHCP name) win; a cached upstream answer does not",
          ca and "cache_find_by_name(c, name, dnsmasq_time(), F_IPV4 | F_IPV6 | F_CNAME)" in ca.group(0)
          and "F_HOSTS | F_DHCP | F_CONFIG" in ca.group(0) and "time(NULL)" not in ca.group(0))
    check("page: the table, its inputs, Add, and the rows saved as \"rewrite\" with the rest",
          'id="rwbody"' in page and 'id="rw_name"' in page and 'id="rw_ans"' in page and 'id="rw_sub"' in page
          and 'data-act="addrw"' in page and "addrw: shAddRewrite," in page
          and "rewrite: cfg.rw.map(function(r){ return r.n + ' ' + r.a + (r.s ? ' sub' : ''); }).join('\\n')" in page)
    check("page: the same rules as the router - an alias never covers subdomains, never chains, never shares a name",
          "return (rwName(a) && a !== n && !sub) ? 'c' : '';" in page and "(r.t === 'c' && (r.n === a || r.a === n))" in page
          and "if(n.indexOf('*.') === 0){ n = n.slice(2); sub = true; }" in page)
    check("page: plain ASCII (the hidden-character gate)", all(ord(c) < 0x7f for c in page))
    toks = ["RSHD_%d" % n for n in range(164, 178)]
    check("page: every new string is used", all("<#%s#>" % t in page for t in toks), [t for t in toks if "<#%s#>" % t not in page])
    www = os.path.join(SRC, "www")
    packs = sorted(f for f in os.listdir(www) if re.fullmatch(r"[A-Z]{2}\.dict", f))
    lens = {p: len(open(os.path.join(www, p), encoding="utf-8").read().split("\n")) for p in packs}
    missing = {p: [t for t in toks if ("\n%s=" % t) not in open(os.path.join(www, p), encoding="utf-8").read()] for p in packs}
    check("all 25 language packs carry the strings, in lockstep", len(packs) == 25 and not any(missing.values()) and len(set(lens.values())) == 1,
          ({p: m for p, m in missing.items() if m}, sorted(set(lens.values()))))
except SystemExit:
    fails.append("stopped early: a step the rest depends on failed")
finally:
    stop.set()
    for p in procs:
        try: p.kill()
        except Exception: pass
    shutil.rmtree(work, ignore_errors=True)

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
