#!/usr/bin/env python3
"""test_edns_block.py - Encrypted DNS > "Block encrypted DNS that goes around the router"
(2026-10-21).

WHY. A device that encrypts its DNS to an outside provider is invisible to Wallguard, Dreadwatch,
DNS Director and Gatekeeper. With the switch on, LAN and guest devices cannot do that: DoT/DoQ
(853) to anything is refused, HTTPS (443) to the known DoH resolvers' addresses is refused, the
DoH provider names answer NXDOMAIN and the browser canaries are answered. DNS Director's "No
filtering" devices are exempt.

2026-11-10: the block is two switches. reaper_dot_block = the port-853 pair; reaper_doh_block = the
443 pair to the resolver sets, the name list, its daily update and the canaries. reaper_dot_block
ships EMPTY, and empty (or absent) means "follow reaper_doh_block": a router upgraded with the one
old switch on keeps both halves on. A plain "0" default would have switched the port-853 half off on
every upgraded router; a key with no defaults row could not be saved by the page (httpd stores only
table names). The key stays empty until the page saves an explicit value - NOTHING writes it at boot.
(A first version did: it wrote "0" on every router whose block was off, and that explicit "0" then
survived the restore of a backup made before the split, which sets reaper_doh_block=1 and knows no
second key - "block on" came back as DoH only, port 853 open.) So the restore paths are part of this:
  - the stock settings-file restore (also the tail of a full-backup restore) is an OVERLAY - the nvram
    tool, a prebuilt, sets the file's keys and leaves the rest - so httpd drops reaper_dot_block before
    it runs (libwebapi do_upload_config); a file that has the key sets it again;
  - the Reaper settings import puts the key back to empty when the file carries reaper_doh_block and
    no reaper_dot_block (rcfg_import_json), and an import of that section restarts dnsmasq and the
    firewall, which it never did (the rules and names stayed as they were until the next restart).
The gates, the set split and the rules are compiled out of rc/encdns.c and run for every state: off,
upgraded, port 853 only, DoH only, both, and a router that does not route. The status CGI's block, the
settings import / export and the restore tail are compiled out of httpd/web.c and libwebapi/webapi.c
and run too (a pre-split file, a file with both keys, an empty value there and back, the service list).

WHAT IT DOES. Runs rednsd/encdns.sh under sh and busybox ash against a fake ipset (per-set
counts, swap) and a fake curl: line validation (addresses and CIDRs only, no duplicates), a good
update (sets swapped in, cache + state written), a failed update (previous list and last good
time kept), replay (loads only empty sets). Checks the shipped name and seed lists, and pins the
rc / firewall / dnsmasq / defaults / CGI / page wiring.

Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import json, os, re, shutil, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rednsd", "encdns.sh")):
    skip("no router source tree with rednsd/encdns.sh (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
def read(p): return open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond or detail == "" else " - " + str(detail)))
    if not cond: fails.append(name)

# ---------------------------------------------------------------- shipped lists
NAME = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
names = [l.strip() for l in read("rednsd/doh-names.txt").splitlines() if l.strip() and not l.startswith("#")]
check("names: %d DoH provider names, all valid host names, no duplicates" % len(names),
      len(names) >= 30 and all(NAME.match(n) for n in names) and len(names) == len(set(names)))
check("names: none sits under another listed name (address=/x/ already covers its subdomains)",
      not [n for n in names if any(n != m and n.endswith("." + m) for m in names)])
check("names: the big ones are there", all(n in names for n in ("dns.google", "cloudflare-dns.com", "dns.quad9.net", "doh.opendns.com", "dns.nextdns.io")))
seed = [l.strip() for l in read("rednsd/doh-seed.txt").splitlines() if l.strip() and not l.startswith("#")]
V4 = re.compile(r"^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$"); V6 = re.compile(r"^[0-9a-f:]+:[0-9a-f:]*(/\d{1,3})?$")
check("seed: %d resolver addresses, each an IPv4/IPv6 address or CIDR, v4 and v6 both present" % len(seed),
      len(seed) >= 40 and all(V4.match(s) or V6.match(s) for s in seed) and any(":" in s for s in seed) and "1.1.1.1" in seed and "8.8.8.8" in seed)
check("Makefile installs the script and both lists",
      all(x in read("rednsd/Makefile") for x in ("install -D -m 0755 encdns.sh $(INSTALLDIR)/usr/sbin/encdns.sh",
                                               "doh-names.txt $(INSTALLDIR)/usr/share/encdns/doh-names", "doh-seed.txt $(INSTALLDIR)/usr/share/encdns/doh-seed")))

# ---------------------------------------------------------------- wiring
ec, fw, sv, sd = read("rc/encdns.c"), read("rc/firewall.c"), read("rc/services.c"), read("rc/sdn.c")
check("rc: the chain refuses 853 tcp+udp to anything and 443 tcp+udp to the set, then hooks br+",
      all(x in ec for x in ('"-A REAPER_EDNS -p tcp --dport 853 -j REJECT --reject-with tcp-reset\\n"', '"-A REAPER_EDNS -p udp --dport 853 -j REJECT\\n"',
                            '"-A REAPER_EDNS -p tcp --dport 443 -m set --match-set %s dst -j REJECT --reject-with tcp-reset\\n"',
                            '"-A REAPER_EDNS -p udp --dport 443 -m set --match-set %s dst -j REJECT\\n"', '"-A FORWARD -i br+ -j REAPER_EDNS\\n"')))
i_ex, i_853 = ec.find("--mac-source %s -j RETURN"), ec.find("--dport 853 -j REJECT")
check("rc: DNS Director's No-filtering devices are exempt, ahead of every refusal", 0 < i_ex < i_853 and "DNSF_SRV_UNFILTERED" in ec)
check("rc: the sets exist before the rules name them (match-set on a missing set is dropped silently)",
      ec.find("edns_sets_ensure();") < ec.find('"-A REAPER_EDNS -p tcp --dport 853') and '"ipset", "create", EDNS_SET4' in ec)
check("firewall: REAPER_EDNS declared in all four filter headers, called beside DNS Director's DoT rules (v4 + v6, both builders)",
      fw.count('":REAPER_EDNS - [0:0]\\n"') == 4 and fw.count("edns_block_rules(fp, 0);") == 2 and fw.count("edns_block_rules(fp_ipv6, 1);") == 2
      and "edns_block_sync();" in fw)
check("dnsmasq: the DoH names are included in the main and every guest instance; the canaries follow the DoH switch",
      sv.count("reaper_edns_dns_conf()") == 1 and sd.count("reaper_edns_dns_conf()") == 1
      and "if ((n == 1) || edns_doh_block_enabled() ||" in sv and "if ((n == 1) || edns_doh_block_enabled() ||" in sd
      and "|| edns_block_enabled() ||" not in sv and "|| edns_block_enabled() ||" not in sd)
check("rc: the router's own DNS Privacy upstream names are never answered NXDOMAIN", "(up = edns_router_upstream(s)) == 1" in ec)
dfl = read("shared/defaults.c")
check("defaults: off (reaper_doh_block 0)", '{ "reaper_doh_block", "0", CKN_STR1' in dfl)
# ---- 2026-11-10: two switches
row = lambda k: next((l for l in dfl.splitlines() if l.lstrip().startswith('{ "%s",' % k)), "")
check("defaults: reaper_dot_block has a row (httpd stores only table names) and its default is EMPTY, never 0 or 1",
      row("reaper_dot_block").lstrip().startswith('{ "reaper_dot_block", "", CKN_STR1,') and dfl.count('{ "reaper_dot_block",') == 1)
check("defaults: each of the three Encrypted DNS rows carries one comment, its own (the block row once held two)",
      all(row(k).count("/*") == 1 and row(k).count("*/") == 1 for k in ("reaper_dot_srv", "reaper_doh_block", "reaper_dot_block"))
      and "rednsd" in row("reaper_dot_srv") and "rednsd" not in row("reaper_doh_block"))
check("rc: three gates - either / port 853 / DoH - and the stored port-853 value follows the DoH switch while empty",
      "int edns_dot_block_enabled(void)\n{\n\treturn is_routing_enabled() && edns_dot_nv();\n}" in ec
      and 'int edns_doh_block_enabled(void)\n{\n\treturn is_routing_enabled() && nvram_get_int("reaper_doh_block") == 1;\n}' in ec
      and "int edns_block_enabled(void)\n{\n\treturn edns_dot_block_enabled() || edns_doh_block_enabled();\n}" in ec
      and all("extern %s;" % p in read("rc/rc.h") for p in ("int edns_block_enabled(void)", "int edns_dot_block_enabled(void)",
                                                           "int edns_doh_block_enabled(void)")))
i_dg, i_hg, i_443, i_hk = (ec.find(x, ec.find("void edns_block_rules(FILE *fp, int v6)")) for x in ("\tif (dot) {\n", "\tif (doh) {\n",   # 2026-11-10: one snapshot per build
                                                "--dport 443 -m set --match-set", '"-A FORWARD -i br+ -j REAPER_EDNS\\n"'))
check("rc: the 853 pair sits under the port-853 gate, the 443 pair under the DoH gate, the hook after both",
      0 < i_ex < i_dg < i_853 < i_hg < i_443 < i_hk and ec.count("edns_dot_block_enabled()") == 2 and "--dport 853" not in ec[i_hg:])
check("rc: the name file, the daily update and 'Update list now' follow the DoH switch",
      '\tif (!edns_doh_block_enabled() || reaper_secure_dir(RED_DIR, 0755) != 0 || !(f = fopen(EDNS_NAMES, "r")))' in ec
      and '\tif (!edns_doh_block_enabled()) {\n\t\teval("cru", "d", "edns_doh");' in ec
      and "\tif (edns_doh_block_enabled() && f_exists(EDNS_SCRIPT))" in ec)
# nothing in rc writes the port-853 switch: an explicit value written at boot survives the restore of a pre-split backup
rcs = {f: open(os.path.join(SRC, "rc", f), encoding="utf-8", errors="surrogateescape").read()
       for f in sorted(os.listdir(os.path.join(SRC, "rc"))) if f.endswith((".c", ".h"))}
wr = [f for f, t in rcs.items() if re.search(r'nvram_(set|set_int|unset|pf_set)\s*\(\s*"reaper_dot_block"', t) or "edns_block_carry" in t]
check("rc: nothing writes reaper_dot_block - no carry-over at boot, no setter in any rc source (%d files read)" % len(rcs),
      len(rcs) > 100 and not wr and rcs["encdns.c"].count('"reaper_dot_block"') == 1
      and 'const char *v = nvram_get("reaper_dot_block");' in ec, wr)
check("rwatch: the activity line is written while either switch or the server is on",
      r'[ \"$(_nv reaper_doh_block)\" = 1 ] || [ \"$(_nv reaper_dot_block)\" = 1 ]; }; then\n"' in read("rc/rwatch.c"))
web = read("httpd/web.c")
check("CGI: the block's state rides the status, and 'Update list now' runs in rc's background",
      '",\\"blk\\":{\\"on\\":%d' in web and 'notify_rc("start_edns_doh");' in web and 'strcmp(script, "edns_doh") == 0' in sv)
check("CGI: reports both switches (an empty reaper_dot_block follows reaper_doh_block); counters when either is on, the list state under DoH",
      '",\\"blk\\":{\\"on\\":%d,\\"dot\\":%d,\\"doh\\":%d,\\"v4\\":%ld,' in web and "on, dot, doh, n4, n6, names, fst, okt, at, cnt, r853, r443);" in web
      and 'const char *dv = nvram_get("reaper_dot_block");\n\t\tint dset = (dv && *dv) ? (atoi(dv) == 1) : -1;' in web
      and "int dot = dset < 0 ? doh : dset;\n\t\tint on = dot || doh;" in web
      and "if (doh) {\n\t\t\trenc_set_sizes(&n4, &n6);\n\t\t}" in web
      and 'if (doh && (f = fopen("/tmp/rednsd/doh.conf", "r"))) {' in web and 'if (doh && (f = fopen("/tmp/rednsd/doh.state", "r"))) {' in web)
check("settings file: reaper_dot_block is carried beside reaper_doh_block", '{ "encdns", "reaper_doh_block", 2   }, { "encdns", "reaper_dot_block", 2 },' in web)
pg = read("www/Reaper_EncryptedDNS.asp")
check("page: two switches (tgdotb, tgblk), each saved with its own setting",
      'name="reaper_doh_block"' in pg and 'name="reaper_dot_block"' in pg and 'id="tgblk"' in pg and 'id="tgdotb"' in pg
      and "<#RENC_67#></span><span class=\"tg\" id=\"tgdotb\">" in pg and "<#RENC_68#></span><span class=\"tg\" id=\"tgblk\">" in pg
      and "f.reaper_dot_block.value = ($('tgdotb').className.indexOf('on') >= 0) ? '1' : '0';" in pg
      and "$('tgdotb').addEventListener('click', function(){ encTg(this); });" in pg)
check("page: an empty reaper_dot_block shows and compares as the DoH switch",
      "var DOTB = (NV.dotb === '') ? (NV.blk === '1' ? '1' : '0') : (NV.dotb === '1' ? '1' : '0');" in pg
      and 'dotb: <% nvram_get_js("reaper_dot_block"); %>,' in pg and "$('tgdotb').className = 'tg' + (DOTB === '1' ? ' on' : '');" in pg)
check("page: the DoH switch restarts dnsmasq; either switch restarts the firewall",
      # 2026-11-10: dnsmasq is pushed once (the upstream prompt may have pushed it already), and the firewall also
      # follows the two server switches (srvChg: the 853 / 443 belts)
      "if(f.reaper_doh_block.value !== (NV.blk === '1' ? '1' : '0') && sv.indexOf('restart_dnsmasq') < 0) sv.push('restart_dnsmasq');" in pg
      and "if(srvChg || f.reaper_doh_block.value !== (NV.blk === '1' ? '1' : '0') || f.reaper_dot_block.value !== DOTB) sv.push('restart_firewall');" in pg
      and "sv.push('restart_dnsmasq', 'restart_firewall')" not in pg)
check("page: the port-853 count shows under its switch, the list, the names, the 443 count and the update under the DoH switch",
      "dot = !!(b && b.dot), on = !!(b && b.doh)," in pg and "$('b_853').textContent = dot ? encNum(b.rej853) : D;" in pg
      and "$('b_443').textContent = on ? encNum(b.rej443) : D;" in pg and "$('b_upd').disabled = !on;" in pg)
dwp = read("www/Reaper_Dreadwatch.asp")
check("Dreadwatch: the coverage line is good only when both switches are on",
      "var blkAll = NV.blk === '1' && (NV.dotb === '' || NV.dotb === '1');" in dwp and "li7.className = blkAll ? 'good' : 'gap';" in dwp
      and 'dotb:   <% nvram_get_js("reaper_dot_block"); %>,' in dwp and "li7.className = NV.blk" not in dwp)
import glob
packs = sorted(glob.glob(os.path.join(SRC, "www", "[A-Z][A-Z].dict")))
pk = {os.path.basename(p)[:2]: open(p, encoding="utf-8", errors="replace").read() for p in packs}
bad = [l for l, t in pk.items() for k in ("RENC_67", "RENC_68", "RENC_69")
       if len(re.findall(r"(?m)^%s=(.+)$" % k, t)) != 1 or re.search(r"(?m)^%s=.*([`<\\\"\u2014]|\$\{)" % k, t)]
same = [l for l in pk if l != "EN" and any(re.findall(r"(?m)^%s=(.+)$" % k, pk[l]) == re.findall(r"(?m)^%s=(.+)$" % k, pk.get("EN", ""))
                                           for k in ("RENC_67", "RENC_68", "RENC_69"))]
check("strings: RENC_67..69 once in each of the 25 packs, safe inside a template literal, translated, packs in lockstep",
      len(pk) == 25 and not bad and not same and len(set(t.count("\n") for t in pk.values())) == 1, (len(pk), bad, same))

# ---------------------------------------------------------------- encdns.sh, run
SH = os.path.join(SRC, "rednsd", "encdns.sh")
BB = shutil.which("busybox")
if BB and subprocess.run([BB, "ash", "-c", "true"], capture_output=True).returncode != 0:
    BB = None
if not shutil.which("flock"):
    print("note: no flock - the run half is skipped")
else:
    r = subprocess.run(["sh", "-n", SH], capture_output=True, text=True)
    check("encdns.sh passes sh -n", r.returncode == 0, r.stderr)
    work = tempfile.mkdtemp(prefix="edns_")
    try:
        bindir = os.path.join(work, "bin"); os.makedirs(bindir)
        st = os.path.join(work, "sets"); os.makedirs(st)
        srv = os.path.join(work, "srv"); os.makedirs(srv)
        # fake ipset: a set = a file of its members
        open(os.path.join(bindir, "ipset"), "w").write(
            "#!/bin/sh\nS=%s\ncase \"$1\" in\n"
            "  create) [ -f $S/$2 ] || : > $S/$2 ;;\n"
            "  flush) : > $S/$2 ;;\n"
            "  add) shift; [ \"$1\" = -exist ] && shift; case \"$2\" in */25) exit 1;; esac; echo \"$2\" >> $S/$1 ;;\n"
            "  restore) rc=0; while read -r a s m; do [ \"$a\" = add ] || continue; case \"$m\" in */25) rc=1; break;; esac; echo \"$m\" >> $S/$s; done; exit $rc ;;\n"
            "  swap) mv $S/$2 $S/.x; mv $S/$3 $S/$2; mv $S/.x $S/$3 ;;\n"
            "  destroy) rm -f $S/$2 ;;\n"
            "  list) [ -f $S/$3 ] || exit 1; echo \"Name: $3\"; echo \"Number of entries: $(grep -c . $S/$3)\" ;;\n"
            "esac\nexit 0\n" % st)
        open(os.path.join(bindir, "curl"), "w").write(
            "#!/bin/sh\nout=; url=\nwhile [ $# -gt 0 ]; do case \"$1\" in -o) out=$2; shift;; --version) exit 0;; https://*) url=$1;; esac; shift; done\n"
            "[ -f %s/fail ] && exit 22\ncp %s/doh.txt \"$out\"\n" % (srv, srv))
        open(os.path.join(bindir, "logger"), "w").write("#!/bin/sh\necho \"$*\" >> %s/logger.out\n" % work)
        for f in ("ipset", "curl", "logger"):
            os.chmod(os.path.join(bindir, f), 0o755)
        seedf = os.path.join(work, "seed"); open(seedf, "w").write("# seed\n1.1.1.1\n2606:4700:4700::1111\n")
        for shell in ["sh"] + (["busybox"] if BB else []):
            tag = "sh" if shell == "sh" else "ash"
            for f in os.listdir(st): os.remove(os.path.join(st, f))
            D, J = os.path.join(work, tag, "d"), os.path.join(work, tag, "j")
            os.makedirs(D, exist_ok=True)
            env = dict(os.environ, EDNS_DIR=D, EDNS_JFFS=J, EDNS_SEED=seedf, EDNS_URL="https://test/doh.txt",
                       PATH=bindir + ":" + os.environ["PATH"], LC_ALL="C")
            def run(*a):
                cmd = (["sh", SH] if shell == "sh" else [BB, "ash", SH]) + list(a)
                return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
            mem = lambda s: open(os.path.join(st, s)).read().split() if os.path.exists(os.path.join(st, s)) else []
            run("replay")
            check("[%s] replay before any download: the seed is in both sets (works before the WAN is up)" % tag,
                  mem("redns_doh") == ["1.1.1.1"] and mem("redns_doh6") == ["2606:4700:4700::1111"], (mem("redns_doh"), mem("redns_doh6")))
            # review 2026-10-24 (S-A-7): the second half of the list is what a hostile or careless upstream could send -
            # private, loopback, link-local, multicast and short-prefix ranges, malformed IPv6 (nine groups, a triple
            # colon, ::/0) - none of it loads; 2026-10-25 (release review E-1): nor a range wider than IPv4 /24 or IPv6 /48
            # (198.18.0.0/16, 2606:4700::/47 and /20); 203.0.113.0/25 is well-formed but the fake ipset rejects it, as a real one
            # might any entry: restore stops there, and the per-entry fallback loads everything else
            open(os.path.join(srv, "doh.txt"), "w").write(
                "8.8.8.8\n8.8.8.8\n9.9.9.9 # quad9\n45.90.28.0/24\n300.1.1.1\n1.2.3.4/40\nnot-an-ip\n2001:4860:4860::8888\n<script>\n\n"
                "10.1.2.3\n192.168.1.1\n172.16.0.0/12\n100.64.0.0/10\n169.254.1.1\n127.0.0.1\n224.0.0.1\n0.0.0.0/1\n203.0.113.0/7\n198.18.0.0/16\n203.0.113.0/25\n192.0.2.6\n"
                "fe80::1\nfd00::1\nfc00::/7\nff02::1\n::1\n::/0\n2001:db8:::1\n1:2:3:4:5:6:7:8:9\n2606:4700::/48\n2606:4700::/47\n2606:4700::/20\n2001:db8::12345\n")
            r = run("update")
            stl = open(os.path.join(D, "doh.state")).read().split()
            V4 = ["1.1.1.1", "192.0.2.6", "45.90.28.0/24", "8.8.8.8", "9.9.9.9"]
            V6 = ["2001:4860:4860::8888", "2606:4700:4700::1111", "2606:4700::/48"]   # Python's string order: '4' sorts before ':'
            check("[%s] update: only well-formed public addresses and CIDRs survive, no duplicates; seed kept under the list; the entry ipset rejects is the only one missing" % tag,
                  sorted(mem("redns_doh")) == V4 and sorted(mem("redns_doh6")) == V6, (mem("redns_doh"), mem("redns_doh6"), r.stderr))
            check("[%s] update: state ok with the count, cache written, temp sets gone" % tag,
                  stl[0] == "ok" and stl[3] == "7" and os.path.exists(os.path.join(J, "doh.ips"))
                  and not os.path.exists(os.path.join(st, "redns_doh_t")), stl)
            okt = stl[1]
            open(os.path.join(srv, "fail"), "w").close(); time.sleep(1.1)
            run("update")
            st2 = open(os.path.join(D, "doh.state")).read().split()
            check("[%s] a failed update keeps the list, the cache and the last good time" % tag,
                  st2[0] == "failed" and st2[1] == okt and "8.8.8.8" in mem("redns_doh") and os.path.exists(os.path.join(J, "doh.ips")), st2)
            os.remove(os.path.join(srv, "fail"))
            for f in os.listdir(st): os.remove(os.path.join(st, f))
            run("replay")
            check("[%s] replay after a reboot: the cached list + seed come back from /jffs (the rejected entry still skipped)" % tag,
                  sorted(mem("redns_doh")) == V4, mem("redns_doh"))
            open(os.path.join(st, "redns_doh"), "a").write("192.0.2.77\n")
            run("replay")
            check("[%s] replay leaves loaded sets alone" % tag, "192.0.2.77" in mem("redns_doh"))
            # release review 2026-10-25 (E-3): IPv6 stops at its set's size (16384), so ipset restore never refuses the
            # list for size and falls back to one fork per address inside the firewall restart
            open(os.path.join(srv, "doh.txt"), "w").write("".join("2001:db8:%x::1\n" % i for i in range(16500)))
            for f in os.listdir(st): os.remove(os.path.join(st, f))
            run("update")
            check("[%s] E-3: an IPv6 list longer than the set loads its first 16384 entries" % tag,
                  len(mem("redns_doh6")) == 16384, len(mem("redns_doh6")))
            check("[%s] logged the update and the failure" % tag,
                  "address list updated: 7 addresses" in open(os.path.join(work, "logger.out")).read()
                  and "download failed, the previous list stays in use" in open(os.path.join(work, "logger.out")).read())
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ---------------------------------------------------------------- the DoH name file, run (2026-11-06, metal _r4)
# With DNS Privacy on family.cloudflare-dns.com the block once dropped the whole cloudflare-dns.com entry, so
# chrome.cloudflare-dns.com (Chrome "Secure DNS: Cloudflare") resolved for every device. The parent stays blocked;
# only the router's own names are carved out (server=/<host>/# - the longer match wins in dnsmasq, proven on 2.93).
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("note: no C compiler - the name-file run is skipped")
else:
    a, z = ec.find("static int edns_router_upstream"), ec.find("/* end of start_firewall")
    check("rc: the router's names under a blocked parent are carved out, the parent stays",
          0 < a < z and "static char *edns_router_carve(" in ec and "b = edns_router_carve(b, &len, s);" in ec)
    STUB = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <stdarg.h>
#define RED_DIR "."
#define EDNS_NAMES "names.txt"
#define EDNS_CONF "doh.conf"
static const char *RL;
static char *nvram_safe_get(const char *k) { (void)k; return (char *)RL; }
static int edns_doh_block_enabled(void) { return 1; }	/* 2026-11-10: the name file follows the DoH switch */
static int reaper_secure_dir(const char *d, int m) { (void)d; (void)m; return 0; }
static int reaper_write_changed(const char *p, const char *b, size_t n, int m)
{ FILE *f = fopen(p, "w"); (void)m; if (!f) return -1; fwrite(b, 1, n, f); fclose(f); return 0; }
static int _vstrsep(char *buf, const char *sep, ...)
{ va_list ap; char **p; int n = 0; va_start(ap, sep); while ((p = va_arg(ap, char **))) { if (!buf) break; *p = strsep(&buf, sep); n++; } va_end(ap); return n; }
#define vstrsep(buf, sep, args...) _vstrsep(buf, sep, args, NULL)
'''
    MAIN = r'''
int main(int c, char **v)
{
	const char *r;
	FILE *f;
	int ch;
	(void)c;
	RL = v[1];
	if (!(r = reaper_edns_dns_conf()))
		return 2;
	if (!(f = fopen(r, "r")))
		return 3;
	while ((ch = fgetc(f)) != EOF)
		putchar(ch);
	fclose(f);
	return 0;
}
'''
    work = tempfile.mkdtemp(prefix="edns_carve_")
    try:
        open(os.path.join(work, "h.c"), "w").write(STUB + ec[a:z] + MAIN)
        open(os.path.join(work, "names.txt"), "w").write("cloudflare-dns.com\ndns.google  # comment\n\n")
        r = subprocess.run([CC, "-std=gnu99", "-O2", "-Wall", "-Werror", "-o", os.path.join(work, "h"), os.path.join(work, "h.c")],
                           capture_output=True, text=True)
        check("name-file harness builds from rc/encdns.c", r.returncode == 0, r.stderr[-600:])
        if r.returncode == 0:
            def conf(rl):
                return subprocess.run([os.path.join(work, "h"), rl], capture_output=True, text=True, cwd=work).stdout
            fam = "<1.1.1.3>853>family.cloudflare-dns.com><1.0.0.3>853>family.cloudflare-dns.com>"
            check("router on family.cloudflare-dns.com: the parent stays blocked, the router's name carved out once",
                  conf(fam) == "address=/cloudflare-dns.com/\nserver=/family.cloudflare-dns.com/#\naddress=/dns.google/\n", conf(fam))
            check("router on dns.google itself: that exact name is left out, nothing carved",
                  conf("<8.8.8.8>853>dns.google>") == "address=/cloudflare-dns.com/\n", conf("<8.8.8.8>853>dns.google>"))
            check("a host name with a character outside [A-Za-z0-9.-] is never written into the dnsmasq file",
                  conf("<1.1.1.3>853>x/y.cloudflare-dns.com>") == "address=/cloudflare-dns.com/\naddress=/dns.google/\n",
                  conf("<1.1.1.3>853>x/y.cloudflare-dns.com>"))
            check("no DNS Privacy servers: every name blocked", conf("") == "address=/cloudflare-dns.com/\naddress=/dns.google/\n", conf(""))
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ---------------------------------------------------------------- the two switches, run (2026-11-10)
# The gates, the set split and the rule writer, compiled out of rc/encdns.c with a small nvram and run per state.
# What must hold: an empty or absent reaper_dot_block follows reaper_doh_block (an upgraded router keeps both
# halves); each pair is written under its own switch only; the exemptions come first in every state; the AiMesh
# set exists whenever the chain does (a match-set on a missing set makes the restore drop that line), the resolver
# sets and their replay only under the DoH switch; nothing at all on a router that does not route; and none of it
# writes nvram - the stored value is the same after a firewall build as before (absent stays absent).
if CC:
    a, z = ec.find("static int edns_dot_nv(void)"), ec.find("/* is name one the router itself encrypts to")
    check("rc: the gates, the set split and the rule writer sit together, ahead of the name file", 0 < a < z)
    STUB2 = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
#define RTCONFIG_DNSFILTER 1
#define ETHER_ADDR_LEN 6
#define DNSF_SRV_UNFILTERED 0
#define RED_DIR "/tmp/rednsd"
#define EDNS_SET4 "redns_doh"
#define EDNS_SET6 "redns_doh6"
#define EDNS_SCRIPT "/usr/sbin/encdns.sh"
#define REAPER_AIMESH_SET "reaper_aimesh"
static const char *NVK[8]; static char NVV[8][128]; static int NVN, ROUTING, WRITES;
static char *nvram_get(const char *k) { int i; for (i = 0; i < NVN; i++) if (!strcmp(NVK[i], k)) return NVV[i]; return NULL; }
static char *nvram_safe_get(const char *k) { char *v = nvram_get(k); return v ? v : (char *)""; }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
/* the test fills the store with put(); any nvram write made by the code under test is counted */
static void put(const char *k, const char *v)
{ int i; for (i = 0; i < NVN; i++) if (!strcmp(NVK[i], k)) break; if (i == NVN) NVK[NVN++] = k; snprintf(NVV[i], sizeof(NVV[i]), "%s", v); }
__attribute__((unused)) static int nvram_set(const char *k, const char *v) { WRITES++; put(k, v); return 0; }
__attribute__((unused)) static int nvram_unset(const char *k) { (void)k; WRITES++; return 0; }
__attribute__((unused)) static int nvram_commit(void) { WRITES++; return 0; }
static int is_routing_enabled(void) { return ROUTING; }
static int f_exists(const char *p) { (void)p; return 1; }
static int reaper_secure_dir(const char *d, int m) { (void)d; (void)m; return 0; }
static int _ev(const char *a, ...)
{ va_list ap; const char *s; printf("EVAL %s", a); va_start(ap, a); while ((s = va_arg(ap, const char *))) printf(" %s", s); va_end(ap); printf("\n"); return 0; }
#define eval(args...) _ev(args, NULL)
static int safe_atoi(const char *s) { return atoi(s); }
static int ether_atoe(const char *a, unsigned char *e)
{ unsigned int b[6]; int i; if (sscanf(a, "%x:%x:%x:%x:%x:%x", &b[0], &b[1], &b[2], &b[3], &b[4], &b[5]) != 6) return 0; for (i = 0; i < 6; i++) e[i] = (unsigned char)b[i]; return 1; }
static char *ether_etoa(const unsigned char *e, char *a)
{ sprintf(a, "%02X:%02X:%02X:%02X:%02X:%02X", e[0], e[1], e[2], e[3], e[4], e[5]); return a; }
static int _vstrsep(char *buf, const char *sep, ...)
{ va_list ap; char **p; int n = 0; va_start(ap, sep); while ((p = va_arg(ap, char **))) { if (!buf) break; *p = strsep(&buf, sep); n++; } va_end(ap); return n; }
#define vstrsep(buf, sep, args...) _vstrsep(buf, sep, args, NULL)
'''
    MAIN2 = r'''
/* argv: routing, reaper_dot_block ("-" = the key is absent), reaper_doh_block */
int main(int c, char **v)
{
	const char *d;
	if (c != 4)
		return 2;
	ROUTING = atoi(v[1]);
	if (strcmp(v[2], "-"))
		put("reaper_dot_block", v[2]);
	put("reaper_doh_block", v[3]);
	put("dnsfilter_enable_x", "1");
	put("dnsfilter_rulelist", "<tv>aa:bb:cc:dd:ee:01>0<pc>AA:BB:CC:DD:EE:02>1");
	printf("GATES dot=%d doh=%d any=%d\n", edns_dot_block_enabled(), edns_doh_block_enabled(), edns_block_enabled());
	printf("V4\n");
	edns_block_rules(stdout, 0);
	printf("V6\n");
	edns_block_rules(stdout, 1);
	d = nvram_get("reaper_dot_block");
	printf("STORE dot=%s doh=%s writes=%d\n", d ? d : "(absent)", nvram_safe_get("reaper_doh_block"), WRITES);
	return 0;
}
'''
    work = tempfile.mkdtemp(prefix="edns_split_")
    try:
        open(os.path.join(work, "g.c"), "w").write(STUB2 + ec[a:z] + MAIN2)
        r = subprocess.run([CC, "-std=gnu99", "-O2", "-Wall", "-Werror", "-o", os.path.join(work, "g"), os.path.join(work, "g.c")],
                           capture_output=True, text=True)
        check("two-switch harness builds from rc/encdns.c", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            def st(routing, dot, doh):
                return subprocess.run([os.path.join(work, "g"), str(routing), dot, doh], capture_output=True, text=True, cwd=work).stdout
            EX = "-A REAPER_EDNS -m mac --mac-source AA:BB:CC:DD:EE:01 -j RETURN\n-A REAPER_EDNS -m set --match-set reaper_aimesh src -j RETURN\n"
            P853 = "-A REAPER_EDNS -p tcp --dport 853 -j REJECT --reject-with tcp-reset\n-A REAPER_EDNS -p udp --dport 853 -j REJECT\n"
            P443 = lambda s: ("-A REAPER_EDNS -p tcp --dport 443 -m set --match-set %s dst -j REJECT --reject-with tcp-reset\n"
                              "-A REAPER_EDNS -p udp --dport 443 -m set --match-set %s dst -j REJECT\n" % (s, s))
            HK = "-A FORWARD -i br+ -j REAPER_EDNS\n"
            MESH = "EVAL ipset create reaper_aimesh hash:mac -exist\nEVAL /sbin/reaper_aimesh_sync\n"
            DOHS = ("EVAL ipset create redns_doh hash:net maxelem 65536 -exist\nEVAL ipset create redns_doh6 hash:net family inet6 maxelem 16384 -exist\n"
                    "EVAL sh /usr/sbin/encdns.sh replay\n")
            def want(dot, doh, dot_nv, doh_nv):
                g = "GATES dot=%d doh=%d any=%d\n" % (dot, doh, dot or doh)
                s = "STORE dot=%s doh=%s writes=0\n" % ("(absent)" if dot_nv == "-" else dot_nv, doh_nv)   # stored as it was
                if not (dot or doh):
                    return g + "V4\nV6\n" + s
                return (g + "V4\n" + MESH + (DOHS if doh else "") + EX + (P853 if dot else "") + (P443("redns_doh") if doh else "") + HK
                        + "V6\n" + EX + (P853 if dot else "") + (P443("redns_doh6") if doh else "") + HK + s)
            for name, (dot_nv, doh_nv), (dot, doh) in (
                    ("upgraded with the old switch on (no reaper_dot_block): both halves on, the key stays absent", ("-", "1"), (1, 1)),
                    ("factory (reaper_dot_block empty, DoH switch off): nothing written, the key stays empty", ("", "0"), (0, 0)),
                    ("empty reaper_dot_block with the DoH switch on: both halves, the key stays empty", ("", "1"), (1, 1)),
                    ("upgraded with the old switch off: nothing written, the key stays absent", ("-", "0"), (0, 0)),
                    ("port 853 only: the 853 pair, no 443 pair, the AiMesh set but no resolver sets and no replay", ("1", "0"), (1, 0)),
                    ("DoH only: the 443 pair per family, no 853 pair, every set", ("0", "1"), (0, 1)),
                    ("both on: both pairs, 853 first", ("1", "1"), (1, 1)),
                    ("both off: no chain content, no hook, no set touched", ("0", "0"), (0, 0))):
                got = st(1, dot_nv, doh_nv)
                check("run: " + name, got == want(dot, doh, dot_nv, doh_nv), got)
            got = st(0, "1", "1")
            check("run: a router that does not route writes nothing, whatever the switches say",
                  got == "GATES dot=0 doh=0 any=0\nV4\nV6\nSTORE dot=1 doh=1 writes=0\n", got)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # ---- the status CGI's "blk" object, run: the block of do_reaper_encdns_cgi that reads the two switches, compiled out
    # of httpd/web.c. The page shows and compares what this reports, so it must apply the same empty-follows-DoH rule as
    # rc, read the refusal counters when either switch is on, and the list state (set sizes, names, feed) only under DoH.
    a = web.find("\t/* 2026-10-21: block encrypted DNS that goes around the router */\n\t{\n", web.find("do_reaper_encdns_cgi(char *url, FILE *stream)"))
    z = web.find("\n}\n", a)
    check("CGI: the block-state code is the tail of do_reaper_encdns_cgi", 0 < a < z < a + 4000)
    STUB3 = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const char *NVK[4]; static const char *NVV[4]; static int NVN;
static char *nvram_get(const char *k) { int i; for (i = 0; i < NVN; i++) if (!strcmp(NVK[i], k)) return (char *)NVV[i]; return NULL; }
static int nvram_get_int(const char *k) { char *v = nvram_get(k); return v ? atoi(v) : 0; }
static void renc_rejects(const char *cmd, unsigned long long *p853, unsigned long long *p443) { (void)cmd; *p853 += 5; *p443 += 7; }
static void renc_set_sizes(long *v4, long *v6) { *v4 = 10; *v6 = 3; }
static FILE *my_fopen(const char *p, const char *m) { const char *b = strrchr(p, '/'); return fopen(b ? b + 1 : p, m); }
#define fopen(p, m) my_fopen(p, m)
#define websWrite(s, fmt, args...) fprintf(s, fmt, ##args)
static void blk(FILE *stream)
{
'''
    MAIN3 = r'''
}
/* argv: reaper_dot_block ("-" = the key is absent), reaper_doh_block */
int main(int c, char **v)
{
	if (c != 3)
		return 2;
	if (strcmp(v[1], "-")) { NVK[NVN] = "reaper_dot_block"; NVV[NVN++] = v[1]; }
	NVK[NVN] = "reaper_doh_block"; NVV[NVN++] = v[2];
	blk(stdout);
	return 0;
}
'''
    work = tempfile.mkdtemp(prefix="edns_cgi_")
    try:
        open(os.path.join(work, "c.c"), "w").write(STUB3 + web[a:z] + MAIN3)
        open(os.path.join(work, "doh.conf"), "w").write("address=/dns.google/\nserver=/x.dns.google/#\naddress=/cloudflare-dns.com/\n")
        open(os.path.join(work, "doh.state"), "w").write("ok 100 200 7\n")
        r = subprocess.run([CC, "-std=gnu99", "-O2", "-Wall", "-Werror", "-o", os.path.join(work, "c"), os.path.join(work, "c.c")],
                           capture_output=True, text=True)
        check("CGI harness builds from httpd/web.c", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            def blk(dot, doh):
                o = subprocess.run([os.path.join(work, "c"), dot, doh], capture_output=True, text=True, cwd=work).stdout
                try:
                    return json.loads('{"x":0' + o)["blk"]      # the code writes the tail of the reply: ,"blk":{...}}
                except Exception:
                    return o
            LIST = dict(v4=10, v6=3, names=2, feed={"st": "ok", "ok": 100, "at": 200, "n": 7})
            NOLIST = dict(v4=-1, v6=-1, names=0, feed={"st": "none", "ok": 0, "at": 0, "n": 0})
            for name, (dot_nv, doh_nv), want in (
                    ("upgraded with the old switch on (no reaper_dot_block): both reported on", ("-", "1"), dict(on=1, dot=1, doh=1, rej853=5, rej443=7, **LIST)),
                    ("an empty reaper_dot_block follows the DoH switch, on", ("", "1"), dict(on=1, dot=1, doh=1, rej853=5, rej443=7, **LIST)),
                    ("an empty reaper_dot_block follows the DoH switch, off: nothing read", ("", "0"), dict(on=0, dot=0, doh=0, rej853=0, rej443=0, **NOLIST)),
                    ("port 853 only: the counters, no list state (a name file left on disk is not counted)", ("1", "0"), dict(on=1, dot=1, doh=0, rej853=5, rej443=7, **NOLIST)),
                    ("DoH only: the counters and the list state", ("0", "1"), dict(on=1, dot=0, doh=1, rej853=5, rej443=7, **LIST)),
                    ("both off: nothing read", ("0", "0"), dict(on=0, dot=0, doh=0, rej853=0, rej443=0, **NOLIST))):
                got = blk(dot_nv, doh_nv)
                check("CGI run: " + name, got == want, got)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # ---- the Reaper settings file, run: export, import and the restart list, compiled out of httpd/web.c (everything
    # from the size limits above rcfg_rw_list down to the end of rcfg_import_json). The import writes only the keys a
    # file carries, so a file made before the split (reaper_doh_block, no reaper_dot_block) must put the port-853
    # switch back to empty = follow; a file with both keys is applied as written; an empty value survives export and
    # import; and an import of the section restarts dnsmasq and the firewall, with every service named once and the
    # whole list inside the 255 characters rc reads. json-c is replaced by five small functions over "section/key=value"
    # lines; the test turns the real exported JSON into that form for the way back in.
    a = web.find("#define RCFG_LIST_MAX\t8192\n")
    z = web.find("/* v2.7.2: the Reaper half of a full-backup restore", a)
    check("settings file: the import / export code sits together in httpd/web.c",
          0 < a < z and all(x in web[a:z] for x in ("static int rcfg_import_json(", "static void rcfg_export_json(", "static void rcfg_restart(", "static int rcfg_put(")))
    STUB4 = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <time.h>
#include <unistd.h>
#include <stdarg.h>
#include <sys/stat.h>
#include <sys/types.h>
/* ---- a small nvram */
#define NVMAX 256
static char *NVK[NVMAX], *NVV[NVMAX];
static int NVN, COMMITS;
static char *nvram_get(const char *k) { int i; for (i = 0; i < NVN; i++) if (NVK[i] && !strcmp(NVK[i], k)) return NVV[i]; return NULL; }
static char *nvram_safe_get(const char *k) { char *v = nvram_get(k); return v ? v : (char *)""; }
static int nvram_match(const char *k, const char *v) { char *c = nvram_get(k); return c && !strcmp(c, v); }
static int nvram_set(const char *k, const char *v)
{ int i; for (i = 0; i < NVN; i++) if (NVK[i] && !strcmp(NVK[i], k)) break; if (i == NVN) { NVK[NVN++] = strdup(k); } else free(NVV[i]); NVV[i] = strdup(v ? v : ""); return 0; }
static int nvram_commit(void) { COMMITS++; return 0; }
/* ---- the five json-c calls the import makes, over "section/key=value" lines */
typedef struct json_object { char *k, *s; struct json_object *kid[64]; int n, isobj; } json_object;
enum json_type { json_type_null, json_type_object, json_type_string };
static json_object *jnew(const char *k, const char *s, int isobj)
{ json_object *o = calloc(1, sizeof(*o)); o->k = strdup(k); o->s = s ? strdup(s) : NULL; o->isobj = isobj; return o; }
static json_object *jfind(json_object *o, const char *k) { int i; for (i = 0; o && i < o->n; i++) if (!strcmp(o->kid[i]->k, k)) return o->kid[i]; return NULL; }
static json_object *json_tokener_parse(const char *body)
{
	json_object *root = jnew("", NULL, 1), *sect;
	char *dup = strdup(body), *ln, *save = NULL, *eq, *sl;
	if (!strncmp(body, "!", 1)) return NULL;	/* "not JSON" */
	for (ln = strtok_r(dup, "\n", &save); ln; ln = strtok_r(NULL, "\n", &save)) {
		if (!(eq = strchr(ln, '='))) continue;
		*eq++ = 0;
		if ((sl = strchr(ln, '/'))) {
			*sl++ = 0;
			if (!(sect = jfind(root, ln))) sect = root->kid[root->n++] = jnew(ln, NULL, 1);
			sect->kid[sect->n++] = jnew(sl, eq, 0);
		} else
			root->kid[root->n++] = jnew(ln, eq, 0);
	}
	return root;
}
static enum json_type json_object_get_type(json_object *o) { return o->isobj ? json_type_object : json_type_string; }
static int json_object_put(json_object *o) { (void)o; return 1; }
static int json_object_object_get_ex(json_object *o, const char *k, json_object **out) { json_object *c = jfind(o, k); if (out) *out = c; return c != NULL; }
static const char *json_object_get_string(json_object *o) { return o ? o->s : NULL; }
/* ---- everything else the slice touches: the stores that are not nvram are empty and accept writes */
static size_t strlcat(char *d, const char *s, size_t n) { size_t l = strlen(d), m = strlen(s); if (l < n) { size_t c = m >= n - l ? n - l - 1 : m; memcpy(d + l, s, c); d[l + c] = 0; } return l + m; }
static int notify_rc(const char *s) { printf("NOTIFY %s\n", s); return 0; }
static void logmessage(const char *who, const char *fmt, ...) { (void)who; (void)fmt; }
#define websWrite(s, fmt, args...) fprintf(s, fmt, ##args)
static void websWriteData(FILE *s, const char *b, int n) { fwrite(b, 1, n, s); }
static void gk_json_esc(FILE *s, const char *v)
{ fputc('"', s); for (; v && *v; v++) { if (*v == '"' || *v == '\\') fputc('\\', s); if ((unsigned char)*v >= 0x20) fputc(*v, s); } fputc('"', s); }
#define REAPER_DHCP6_FILE "dhcp6"
#define RVIEW_RULES "rules"
#define RVIEW_RULES_BYTES 4096
#define RLOGF_FILE "logf"
#define RLOGF_BYTES 4096
#define RDW_KEYS "dwkeys"
#define RDW_SRC "dwsrc"
#define RDW_SRC_MAX 16384
#define SH_JFFS "wg"
#define SH_LIST_MAX 16384
#define SH_ADV_MAX 16384
typedef struct evp_cipher_ctx_st EVP_CIPHER_CTX;	/* named by the sealing type the slice declares; never used here */
#define RPBR_LIST_MAX 8192
#define REAPER_PBR_DRAFT "pbr"
#define RFW_REC_MAX 512
struct sh_file { const char *field, *file; int (*check)(const char *); };
static const struct sh_file sh_files[1] = { { "none", "none", NULL } };
#define SH_NFILES 0
static void reaper_dhcp6_walk(const char *v, void (*cb)(const char *, const char *, void *), void *arg) { (void)v; (void)cb; (void)arg; }
static int rjf_set(const char *f, const char *v, const char *who) { (void)f; (void)v; (void)who; return 0; }
static const char *rjf_get(const char *f, int *ex) { (void)f; *ex = 0; return NULL; }
static char *rw_list_get(const char *ln) { (void)ln; return NULL; }
static int rw_list_set(const char *ln, const char *v) { (void)ln; (void)v; return 0; }
static char *rview_slurp(const char *f, size_t n) { (void)f; (void)n; return NULL; }
static int rview_rules_ok(const char *v) { (void)v; return 0; }
static void rview_alog(const char *a, const char *b) { (void)a; (void)b; }
static int rlogf_ok(const char *v) { (void)v; return 0; }
static int src_keys_ok(const char *v) { (void)v; return 1; }
static int src_keys_save(const char *a, const char *b, const char *c, const char *v) { (void)a; (void)b; (void)c; (void)v; return 0; }
static int sh_keys_save(const char *v) { (void)v; return 0; }
static int sh_adv_ok(const char *v, size_t n) { (void)v; (void)n; return 1; }
static int rdw_chk_src(const char *l) { (void)l; return 0; }
static int sh_lines(const char *v, char *out, size_t cap, int (*chk)(const char *)) { (void)chk; snprintf(out, cap, "%s", v); return 0; }
static const char *gk_rl_get(void) { return ""; }
static int gk_rl_set(const char *v) { (void)v; return 0; }
static int gk_rl_merge(const char *v) { (void)v; return 0; }	/* review 2026-11-11 (B-6): the import merges */
static void gk_baseline_snapshot(void) { }
static const char *reaper_pbr_rl_get(void) { return ""; }
static const char *reaper_fw_list_get(const char *n) { (void)n; return ""; }
static int reaper_fw_list_stage(const char *n, const char *v) { (void)n; (void)v; return 0; }
static int base64_encoded_len(int n) { return n * 2; }
static int base64_encode(const unsigned char *in, char *out, int n) { (void)in; (void)out; (void)n; return 0; }
'''
    MAIN4 = r'''
static int rbk_make_cfg(const char *path) { (void)path; return -1; }	/* no embedded router settings here */
/* argv: <nvram file: k=v lines> export | import <body file> | svc <touch bits, hex> [all] */
int main(int c, char **v)
{
	char ln[4096], *body;
	FILE *f;
	long n;
	int i, a = 0, b = 0, r = 0, ret;

	if (c < 3 || !(f = fopen(v[1], "r")))
		return 2;
	while (fgets(ln, sizeof(ln), f)) {
		char *e = strchr(ln, '=');
		ln[strcspn(ln, "\n")] = 0;
		if (e) { *e = 0; nvram_set(ln, e + 1); }
	}
	fclose(f);
	if (!strcmp(v[2], "export")) {
		rcfg_export_json(stdout, 0);
		return 0;
	}
	if (!strcmp(v[2], "svc") && c >= 4) {
		rcfg_restart(c > 4, c > 4, c > 4, (unsigned)strtoul(v[3], NULL, 16));
		return 0;
	}
	if (strcmp(v[2], "import") || c != 4 || !(f = fopen(v[3], "r")))
		return 2;
	body = calloc(1, 65536);
	n = (long)fread(body, 1, 65535, f);
	fclose(f);
	body[n > 0 ? n : 0] = 0;
	ret = rcfg_import_json(body, &a, &b, &r);
	printf("RET %d flags=%d lists=%d rejected=%d commits=%d\n", ret, a, b, r, COMMITS);
	for (i = 0; i < NVN; i++)
		printf("NV %s=%s\n", NVK[i], NVV[i]);
	return 0;
}
'''
    work = tempfile.mkdtemp(prefix="edns_imp_")
    try:
        open(os.path.join(work, "i.c"), "w", encoding="utf-8", errors="surrogateescape").write(STUB4 + web[a:z] + MAIN4)
        r = subprocess.run([CC, "-std=gnu99", "-O1", "-Wall", "-Wno-unused-function", "-Wno-unused-variable", "-Werror=implicit-function-declaration",
                            "-o", os.path.join(work, "i"), os.path.join(work, "i.c")], capture_output=True, text=True)
        check("settings-file harness builds from httpd/web.c", r.returncode == 0, "\n".join(l for l in r.stderr.splitlines() if "error" in l)[-800:])
        if r.returncode == 0:
            def rc_run(nv, *args):
                open(os.path.join(work, "nv"), "w").write("".join("%s=%s\n" % kv for kv in nv.items()))
                return subprocess.run([os.path.join(work, "i"), "nv"] + list(args), capture_output=True, text=True, cwd=work).stdout
            def imp(nv, body):
                open(os.path.join(work, "body"), "w").write("reaper_cfg=1\n" + "".join(l + "\n" for l in body))
                o = rc_run(nv, "import", "body").splitlines()
                return ([l[7:] for l in o if l.startswith("NOTIFY ")], [l for l in o if l.startswith("RET ")],
                        dict(l[3:].split("=", 1) for l in o if l.startswith("NV ")))
            ENC = "restart_rednsd;restart_dnsmasq;restart_firewall"
            n, rt, nv = imp({"reaper_doh_block": "0", "reaper_dot_block": "0"}, ["encdns/reaper_doh_block=1"])
            check("import run: a file from before the split ('block on') onto a router with both switches off: DoH on, the port-853 switch back to empty = follow",
                  nv.get("reaper_doh_block") == "1" and nv.get("reaper_dot_block") == "" and rt == ["RET 0 flags=1 lists=0 rejected=0 commits=1"], (rt, nv))
            n, rt, nv = imp({"reaper_doh_block": "1", "reaper_dot_block": "1"}, ["encdns/reaper_doh_block=0"])
            check("import run: a file from before the split ('block off') onto a router with both on: DoH off, the port-853 switch follows it (empty)",
                  nv.get("reaper_doh_block") == "0" and nv.get("reaper_dot_block") == "", nv)
            n, rt, nv = imp({"reaper_doh_block": "0", "reaper_dot_block": "1"}, ["encdns/reaper_doh_block=1", "encdns/reaper_dot_block=0"])
            check("import run: a file with both keys is applied as written (DoH only)",
                  nv.get("reaper_doh_block") == "1" and nv.get("reaper_dot_block") == "0" and rt == ["RET 0 flags=2 lists=0 rejected=0 commits=1"], (rt, nv))
            n, rt, nv = imp({"reaper_doh_block": "0", "reaper_dot_block": "1"}, ["encdns/reaper_dot_block=", "encdns/reaper_doh_block=1"])
            check("import run: a file that carries the port-853 switch EMPTY sets it empty (whatever the order of the keys in the file)",
                  nv.get("reaper_doh_block") == "1" and nv.get("reaper_dot_block") == "" and "rejected=0" in rt[0], (rt, nv))
            n, rt, nv = imp({"reaper_doh_block": "0", "reaper_dot_block": "1"}, ["dns/reaper_dnshc_enable=0", "encdns/reaper_dot_srv=1"])
            check("import run: a file that does not carry the DoH switch leaves both block switches alone",
                  nv.get("reaper_doh_block") == "0" and nv.get("reaper_dot_block") == "1" and nv.get("reaper_dot_srv") == "1", nv)
            n, rt, nv = imp({"reaper_doh_block": "0", "reaper_dot_block": "1"}, ["encdns/reaper_doh_block=1;x"])
            check("import run: a refused DoH value changes neither switch", nv.get("reaper_doh_block") == "0" and nv.get("reaper_dot_block") == "1" and "rejected=1" in rt[0], (rt, nv))
            # export, then the same file back in
            for dot in ("", "1", "0"):
                try:
                    ex = json.loads(rc_run({"reaper_doh_block": "1", "reaper_dot_block": dot, "reaper_dot_srv": "0"}, "export"))
                except Exception as e:
                    ex = {"error": str(e)}
                body = ["%s/%s=%s" % (s, k, v) for s, d in ex.items() if isinstance(d, dict) for k, v in d.items() if isinstance(v, str) and "\n" not in v]
                n, rt, nv = imp({"reaper_doh_block": "0", "reaper_dot_block": "0" if dot != "0" else "1"}, body)
                check("export / import run: the port-853 switch %r is in the exported file and comes back the same" % dot,
                      ex.get("encdns", {}).get("reaper_dot_block", None) == dot and ex.get("encdns", {}).get("reaper_doh_block") == "1"
                      and nv.get("reaper_dot_block") == dot and nv.get("reaper_doh_block") == "1" and rt and "rejected=0" in rt[0],
                      (ex.get("encdns"), rt, nv.get("reaper_dot_block")))
            # the restart list
            n, rt, nv = imp({}, ["encdns/reaper_doh_block=1"])
            check("import run: the encdns section restarts rednsd, dnsmasq and the firewall - the page's own list", n == [ENC], n)
            n, rt, nv = imp({}, ["dns/reaper_dnshc_enable=0"])
            check("import run: the dns section alone restarts what it did before, no firewall", n == ["restart_dnsmasq;restart_rdnshc"], n)
            n, rt, nv = imp({}, ["warden/rwarden_enable=0", "dns/reaper_dnshc_enable=0", "encdns/reaper_doh_block=1", "encdns/reaper_dot_block=1"])
            check("import run: encdns + dns + warden: dnsmasq named once, the firewall last of the three sections",
                  n == ["restart_rwarden;restart_dnsmasq;restart_rdnshc;restart_rednsd;restart_firewall"], n)
            worst = [l[7:] for l in rc_run({"rchq_enable": "0"}, "svc", "1ff", "all").splitlines() if l.startswith("NOTIFY ")]
            parts = worst[0].split(";") if worst else []
            check("import run: every section at once: %d characters (rc reads 255), no service named twice" % (len(worst[0]) if worst else -1),
                  len(worst) == 1 and 200 < len(worst[0]) <= 255 and len(parts) == len(set(parts)) and "restart_firewall" in parts and parts.count("restart_dnsmasq") == 1, worst)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # ---- the stock settings-file restore, run: do_upload_config() compiled out of libwebapi/webapi.c. Both restore
    # handlers in httpd end in it (the stock upload.cgi and the full-backup / same-model settings-file restore), and it is
    # the only place the nvram tool's restore is run. That tool is a prebuilt on this platform and it OVERLAYS: it sets
    # the keys in the file and leaves the others (shown by running it under qemu with a logging nvram, 2026-11-10). So
    # the port-853 switch is dropped first, and only then are the file's keys applied.
    wa = read("libwebapi/webapi.c")
    a = wa.find("int do_upload_config(void)\n{\n")
    z = wa.find("\n}\n", a) + 3
    body_uc = wa[a:z]
    check("restore: do_upload_config drops reaper_dot_block right before the file's keys are applied, and is the one place the tool's restore runs",
          0 < a < z and body_uc.count('sys_upload("/tmp/settings_u.prf");') == 1
          and '\tnvram_unset("reaper_dot_block");\n\tsys_upload("/tmp/settings_u.prf");\n' in body_uc
          and wa.count("sys_upload(") == 2 and web.count("sys_upload(") == 1          # the macro, and this one call
          and len(re.findall(r'eval\("nvram", "restore"', web + wa)) == 2            # the two macro definitions
          and web.count("\t\tdo_upload_config();\n") == 2 and "OBJS = webapi.o" in read("libwebapi/Makefile"))
    STUB5 = r'''#include <stdio.h>
#include <stdarg.h>
static int nvram_unset(const char *k) { printf("UNSET %s\n", k); return 0; }
#define sys_upload(image) printf("RESTORE %s\n", image)
#define sys_reboot() printf("REBOOT\n")
static void httpd_nvram_commit(void) { printf("COMMIT\n"); }
static void logmessage(const char *who, const char *fmt, ...) { (void)who; (void)fmt; }
'''
    work = tempfile.mkdtemp(prefix="edns_rst_")
    try:
        open(os.path.join(work, "u.c"), "w").write(STUB5 + body_uc + "\nint main(void) { return do_upload_config(); }\n")
        r = subprocess.run([CC, "-std=gnu99", "-O1", "-Wall", "-Werror", "-o", os.path.join(work, "u"), os.path.join(work, "u.c")], capture_output=True, text=True)
        check("restore harness builds from libwebapi/webapi.c", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            got = subprocess.run([os.path.join(work, "u")], capture_output=True, text=True).stdout
            check("restore run: the key is dropped, then the file is applied, then nvram is committed, then the reboot is asked for",
                  got == "UNSET reaper_dot_block\nRESTORE /tmp/settings_u.prf\nCOMMIT\nREBOOT\n", got)
    finally:
        shutil.rmtree(work, ignore_errors=True)
else:
    print("note: no C compiler - the two-switch run is skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
