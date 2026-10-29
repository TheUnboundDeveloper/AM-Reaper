#!/usr/bin/env python3
"""test_edns_block.py - Encrypted DNS > "Block encrypted DNS that goes around the router"
(2026-10-21).

WHY. A device that encrypts its DNS to an outside provider is invisible to Wallguard, Dreadwatch,
DNS Director and Gatekeeper. With the switch on, LAN and guest devices cannot do that: DoT/DoQ
(853) to anything is refused, HTTPS (443) to the known DoH resolvers' addresses is refused, the
DoH provider names answer NXDOMAIN and the browser canaries are answered. DNS Director's "No
filtering" devices are exempt.

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
check("dnsmasq: the DoH names are included in the main and every guest instance; the canaries follow the switch",
      sv.count("reaper_edns_dns_conf()") == 1 and sd.count("reaper_edns_dns_conf()") == 1
      and "if ((n == 1) || edns_block_enabled() ||" in sv and "if ((n == 1) || edns_block_enabled() ||" in sd)
check("rc: the router's own DNS Privacy upstream names are never answered NXDOMAIN", "edns_router_upstream(s)" in ec)
check("defaults: off (reaper_doh_block 0)", '{ "reaper_doh_block", "0", CKN_STR1' in read("shared/defaults.c"))
web = read("httpd/web.c")
check("CGI: the block's state rides the status, and 'Update list now' runs in rc's background",
      '",\\"blk\\":{\\"on\\":%d' in web and 'notify_rc("start_edns_doh");' in web and 'strcmp(script, "edns_doh") == 0' in sv)
pg = read("www/Reaper_EncryptedDNS.asp")
check("page: own switch saved with reaper_doh_block; a change restarts dnsmasq + the firewall",
      'name="reaper_doh_block"' in pg and "sv.push('restart_dnsmasq', 'restart_firewall');" in pg and 'id="tgblk"' in pg)

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

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
