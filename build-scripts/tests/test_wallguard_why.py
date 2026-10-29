#!/usr/bin/env python3
"""Wallguard says why it cannot work: Warden-blocked list servers and DNS sent past the router (2026-10-26).

WHY. On the owner's box (_r41) two things looked like Wallguard faults and were not:
  - OISD Small never downloaded. small.oisd.nl sits on OVH in France, France was in Warden's country list and
    Warden's router-traffic filter (rwarden_self) dropped the router's own HTTPS to it. The log said only
    "download failed".
  - Nothing was blocked. A Service Intercept rule DNATed every LAN client's port 53 straight to the AdGuard host,
    so no client lookup reached dnsmasq, where Wallguard (and Dreadwatch) live.
wallguard.sh now names Warden (country code, ban list or threat feed, and the address) in the log, the state
file and the page, and its stats carry "bypass": the DNAT targets for port 53 that are not the router.

WHAT IT DOES. Lifts warden_why() and dns_bypass() out of wallguard/wallguard.sh and runs them under sh and
busybox ash (when present) with fake nvram / iptables / ip6tables / ipset / nslookup / ip: a picked country, an
allow-listed address, the router filter off, a set Warden does not apply to router traffic, the ban list, a
URL with a port, IPv6 answers ignored; DNAT to another host (IPv4 and IPv6) reported, to the router itself, a
REDIRECT and port 5353 not, the one-minute cache. Then checks update() and stats() carry the reason through.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "wallguard", "wallguard.sh") if SRC else ""
if not P or not os.path.isfile(P):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
sh_src = open(P, encoding="utf-8").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def lift(fn):
    m = re.search(r"^%s\(\) \{\n.*?^\}\n" % fn, sh_src, re.S | re.M)
    return m.group(0) if m else ""
WW, DB = lift("warden_why"), lift("dns_bypass")
check("warden_why() and dns_bypass() are in wallguard.sh", WW and DB)

FAKES = {
 "nvram": r'''#!/bin/sh
[ "$1" = get ] || exit 0
case "$2" in
  rwarden_enable) echo "${F_EN:-1}" ;; rwarden_self) echo "${F_SELF:-1}" ;;
  rwarden_geo) echo "CN FR RU" ;; lan_ipaddr) echo 192.168.50.1 ;;
esac''',
 "iptables": r'''#!/bin/sh
if [ "$1" = -S ] && [ "$2" = RW_SELF ]; then [ "${F_SELF:-1}" = 1 ] || exit 1; cat "$W/rwself"; exit 0; fi
if [ "$1" = -t ] && [ "$2" = nat ] && [ "$3" = -S ]; then cat "$W/nat4" 2>/dev/null; exit 0; fi
exit 1''',
 "ip6tables": r'''#!/bin/sh
if [ "$1" = -t ] && [ "$2" = nat ] && [ "$3" = -S ]; then cat "$W/nat6" 2>/dev/null; exit 0; fi
exit 1''',
 "ipset": r'''#!/bin/sh
[ "$1" = test ] && grep -qx "$2 $3" "$W/members"''',
 "nslookup": r'''#!/bin/sh
echo "Server:    127.0.0.1"; echo "Address 1: 127.0.0.1 localhost"; echo
echo "Name:      $1"; i=1
for a in $F_ADDRS; do echo "Address $i: $a"; i=$((i+1)); done''',
 "ip": r'''#!/bin/sh
echo "1: lo    inet 127.0.0.1/8 scope host lo"
echo "9: br0    inet 192.168.50.1/24 brd 192.168.50.255 scope global br0"
echo "12: br55    inet 10.20.0.1/24 brd 10.20.0.255 scope global br55"''',
}
# as rwarden writes them (rc/rwarden.c lower-cases the code): rw_g_fr, never rw_g_FR - the first version of
# warden_why matched the nvram spelling and found nothing on metal
RWSELF = "-N RW_SELF\n-A RW_SELF -m set --match-set rw_ban dst -j RW_SDROP\n-A RW_SELF -m set --match-set rw_g_fr dst -j RW_SDROP\n-A RW_SELF -m set --match-set rw_g_cn dst -j RW_SDROP\n"
NAT4 = """-N REAPER_FWHC
-A REAPER_FWHC ! -s 10.20.0.98/32 ! -d 10.20.0.98/32 -i br0 -p tcp -m tcp --dport 53 -m set ! --match-set rwfw_LDNS src -j DNAT --to-destination 10.20.0.98:53
-A REAPER_FWHC ! -s 10.20.0.98/32 ! -d 10.20.0.98/32 -i br0 -p udp -m udp --dport 53 -m set ! --match-set rwfw_LDNS src -j DNAT --to-destination 10.20.0.98:53
-A REAPER_GKN -p udp -m udp --dport 53 -j REDIRECT --to-ports 5300
-A DNSFILTER -s 192.168.50.20/32 -p udp -m udp --dport 53 -j DNAT --to-destination 192.168.50.1
-A VSERVER -p udp -m udp --dport 5353 -j DNAT --to-destination 192.168.50.9:5353
"""
NAT6 = "-A REAPER_FWHC6 -i br0 -p udp -m udp --dport 53 -j DNAT --to-destination [2001:db8::98]:53\n"

shells = [["sh"]] + ([["busybox", "ash"]] if shutil.which("busybox") else [])
work = tempfile.mkdtemp(prefix="wgwhy_")
try:
    bindir = os.path.join(work, "bin"); os.makedirs(bindir)
    for n, body in FAKES.items():
        p = os.path.join(bindir, n); open(p, "w").write(body + "\n"); os.chmod(p, 0o755)
    open(os.path.join(work, "rwself"), "w").write(RWSELF)
    # busybox ash runs its own applets (nslookup, ip) before PATH; a shell function wins over both
    SHIM = "".join('%s() { "$W/bin/%s" "$@"; }\n' % (n, n) for n in FAKES)
    def run(shell, body, **env):
        e = dict(os.environ, PATH=bindir + ":" + os.environ["PATH"], W=work, LC_ALL="C", **env)
        sp = os.path.join(work, "run.sh"); open(sp, "w").write(SHIM + body)
        return subprocess.run(shell + [sp], capture_output=True, text=True, env=e, timeout=30)
    for shell in shells:
        tag = "ash" if shell[0] == "busybox" else "sh"
        def why(url, members, **env):
            open(os.path.join(work, "members"), "w").write("".join(m + "\n" for m in members))
            r = run(shell, WW + 'warden_why "%s"; echo "rc=$?"\n' % url, **env)
            return r.stdout.strip()
        A = {"F_ADDRS": "203.0.113.7 2001:db8:41d0::8a86"}
        check(tag + ": a picked country names its code and the address",
              why("https://small.oisd.nl/", ["rw_g_fr 203.0.113.7"], **A) == "FR 203.0.113.7\nrc=0", why("https://small.oisd.nl/", ["rw_g_fr 203.0.113.7"], **A))
        check(tag + ": a whitelisted address is not blamed on Warden",
              why("https://small.oisd.nl/", ["rw_g_fr 203.0.113.7", "rw_allow 203.0.113.7"], **A) == "rc=1")
        check(tag + ": the router-traffic filter off -> nothing", why("https://small.oisd.nl/", ["rw_g_fr 203.0.113.7"], F_SELF="0", **A) == "rc=1")
        check(tag + ": Warden off -> nothing", why("https://small.oisd.nl/", ["rw_g_fr 203.0.113.7"], F_EN="0", **A) == "rc=1")
        check(tag + ": a country set RW_SELF does not carry (RU) is not blamed",
              why("https://small.oisd.nl/", ["rw_g_ru 203.0.113.7"], **A) == "rc=1")
        check(tag + ": the ban list is named", why("https://x.example/l.txt", ["rw_ban 203.0.113.7"], **A) == "ban 203.0.113.7\nrc=0")
        check(tag + ": a URL with a port and path still finds its host", why("https://small.oisd.nl:443/x/y?z", ["rw_g_cn 203.0.113.7"], **A) == "CN 203.0.113.7\nrc=0")
        check(tag + ": IPv6 answers are not tested", why("https://h/", ["rw_g_fr 2001:db8:41d0::8a86"], F_ADDRS="2001:db8:41d0::8a86") == "rc=1")
        check(tag + ": not in any set -> nothing", why("https://small.oisd.nl/", [], **A) == "rc=1")
        # dns_bypass
        D = os.path.join(work, tag + "_D"); os.makedirs(D, exist_ok=True)
        open(os.path.join(work, "nat4"), "w").write(NAT4); open(os.path.join(work, "nat6"), "w").write(NAT6)
        r = run(shell, 'D="%s"\n%secho "[$(dns_bypass)]"\n' % (D, DB))
        check(tag + ": DNAT of port 53 to another host is reported (IPv4 and IPv6); the router, REDIRECT and 5353 are not",
              r.stdout.strip() == "[10.20.0.98 2001:db8::98 ]", (r.stdout, r.stderr))
        open(os.path.join(work, "nat4"), "w").write(""); open(os.path.join(work, "nat6"), "w").write("")
        r = run(shell, 'D="%s"\n%secho "[$(dns_bypass)]"\n' % (D, DB))
        check(tag + ": the answer is cached for a minute (a rule change shows on the next minute)", r.stdout.strip() == "[10.20.0.98 2001:db8::98 ]", r.stdout)
        os.utime(os.path.join(D, "bypass"), (0, 0))
        r = run(shell, 'D="%s"\n%secho "[$(dns_bypass)]"\n' % (D, DB))
        check(tag + ": no DNAT rule -> empty", r.stdout.strip() == "[]", r.stdout)
finally:
    shutil.rmtree(work, ignore_errors=True)

# the reason travels: update() -> state -> stats() JSON; the log names the cause; the page shows it
check("update() asks warden_why only after a real download failure, and writes the reason into the state line",
      'wr=$(warden_why "$url") && [ -n "$wr" ]' in sh_src and 'echo "$id $st ${prev:-0} $now $wd" >> "$D/state.new"' in sh_src)
check("the log line names Warden, the address and the way out",
      "drops this server ($wi) for the router's own traffic; whitelist $wi on the Warden page" in sh_src)
check("stats() reads only a well-formed reason and prints warden / wip per list and the bypass list",
      "$5 ~ /^warden:([A-Z][A-Z]|ban|threat)$/ && $6 ~ /^[0-9.]+$/" in sh_src and '\\"warden\\":\\"%s\\",\\"wip\\":\\"%s\\"' in sh_src
      and '-v bypass="$(dns_bypass)"' in sh_src and 'gsub(/[^0-9a-fA-F.: ]/, "", bypass)' in sh_src)
check("the build log reports the table total, not the last list's count",
      """log "block table built: $(grep -o '"names":[0-9]*' "$D/build.json" | head -1 | cut -d: -f2) names\"""" in sh_src)
pg = open(os.path.join(SRC, "www", "Reaper_Wallguard.asp"), encoding="utf-8").read()
check("the page shows the bypass banner while Wallguard is on", 'id="bypass"' in pg and "var by = (on && stat && stat.bypass)" in pg)
check("the page names Warden in the list's status cell, with the address in the tooltip",
      "f.warden && f.st !== 'ok'" in pg and "stc.title = `<#RSHD_135#>`" in pg)
check("the page stays ASCII", all(ord(c) < 128 for c in pg))
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
