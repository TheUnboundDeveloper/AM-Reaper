#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bastion fixes found while rewriting the guide's section 4.3 (2026-11-02).

WHAT IT CHECKS, by running the shell where there is shell:
  (1) Encrypted DNS block: AiMesh nodes are exempt - the shared reaper_aimesh set is created (and filled once)
      before the rules load, and its RETURN sits after DNS Director's No-filtering exemptions and before every
      REJECT, in both address families;
  (2) Wallguard: Save runs `wallguard.sh sync`, which downloads when a subscribed list has no usable copy
      (newly ticked, or ticked again after its copy was pruned) and otherwise only rebuilds - run under sh with
      stubbed helpers;
  (3) Dreadwatch: the device tile counts every device the counters keep (dns.sh dstats "nclients"), not the 20
      listed - the awk is run on a counters file with 30 devices;
  (4) Warden: the global IPv6 prefix of every LAN-side bridge (a guest / VLAN network) is exempt like the main
      LAN prefix, inbound and in the destination group; the WAN's own address is left out - the collector is
      run against a stubbed `ip`;
  (5) the corrected page texts (RWDN_11/18/111/118, RSHD_133) in every pack.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "encdns.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
SH = shutil.which("sh")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
enc, wgc, wgs, rw, dwp = rd("rc/encdns.c"), rd("rc/wallguard.c"), rd("wallguard/wallguard.sh"), rd("rc/rwarden.c"), rd("www/Reaper_Dreadwatch.asp")

def c_unescape(s):
    return re.sub(r'\\(.)', lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s)
def c_lits(text):
    return "".join(c_unescape(m.group(1)) for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', text))
def run(script, env=None):
    return subprocess.run([SH, "-c", script], capture_output=True, text=True, env=dict(os.environ, **(env or {})))

# ---- (1) Encrypted DNS + AiMesh
ens = enc[enc.find("static void edns_sets_ensure(int doh)"):enc.find("void edns_block_rules(FILE *fp, int v6)")]   # 2026-11-10: the DoH half is passed in
check("the block creates the AiMesh set before the rules and fills it once",
      'eval("ipset", "create", REAPER_AIMESH_SET, "hash:mac", "-exist");' in ens and 'eval("/sbin/reaper_aimesh_sync");' in ens)
ebr = enc[enc.find("void edns_block_rules(FILE *fp, int v6)"):]
ebr = ebr[:ebr.find("\n}\n")]
i_un, i_am, i_rj = ebr.find("DNSF_SRV_UNFILTERED"), ebr.find('"-A REAPER_EDNS -m set --match-set " REAPER_AIMESH_SET " src -j RETURN\\n"'), ebr.find("-j REJECT")
check("the AiMesh RETURN comes after the No-filtering exemptions and before every REJECT (one line, both families)",
      0 < i_un < i_am < i_rj and ebr.count("REAPER_AIMESH_SET") == 1, (i_un, i_am, i_rj))
check("REAPER_AIMESH_SET is the shared set's name", re.search(r'#define REAPER_AIMESH_SET "reaper_aimesh"', rd("rc/rc.h")) is not None)

# ---- (2) Wallguard Save
check("Save (start_wallguard with a table) runs sync, not build", 'sh_run_bg("sync");' in wgc and 'sh_run_bg("build");\t\t/* a list or rule change' not in wgc)
m = re.search(r"^sync\(\) \{\n.*?^\}\n", wgs, re.S | re.M)
check("wallguard.sh has sync() and dispatches it", m is not None and "  sync) sync ;;\n" in wgs)
if m and SH:
    STUB = r'''log() { echo "LOG $*"; }
update() { echo UPDATE; }
build() { echo BUILD; }
st_lists() { :; }
feed_ok() { [ -n "$2" ]; }
list_path() { [ -f "$L/$1" ] && echo "$L/$1"; }
'''
    w = tempfile.mkdtemp(prefix="wgsync_")
    try:
        D, L = os.path.join(w, "d"), os.path.join(w, "l"); os.makedirs(D); os.makedirs(L)
        def sync(feeds, have):
            open(os.path.join(D, "feeds"), "w").write(feeds)
            for f in os.listdir(L): os.remove(os.path.join(L, f))
            for h in have: open(os.path.join(L, h), "w").write("x\n")
            r = run('D="%s"; L="%s"\n%s%ssync\n' % (D, L, STUB, m.group(0)))
            return r.stdout.strip().split("\n")[-1], r.stdout + r.stderr
        F = "2 hagezi_normal https://a.example/multi.txt p -\n5 oisd_small https://small.example/ p -\n10 svc_kids - s -\n"
        out, log = sync(F, ["hagezi_normal", "oisd_small"])
        check("every subscribed list has a copy -> rebuild only", out == "BUILD", log)
        out, log = sync(F, ["hagezi_normal"])
        check("a newly ticked list without a copy -> download (update), and the log names it",
              out == "UPDATE" and "LOG list(s) oisd_small not downloaded yet - downloading now" in log, log)
        out, log = sync("10 svc_kids - s -\n", [])
        check("a blocked-services list (kind s, compiled locally) never forces a download", out == "BUILD", log)
    finally:
        shutil.rmtree(w, ignore_errors=True)

# ---- (3) Dreadwatch device count
a0 = rw.find("  awk 'FILENAME==ARGV[1] { if ($1==\\\"SINCE\\\")")
a0 = rw.rfind('"', 0, a0) if a0 > 0 else -1		# the literal's opening quote
a1 = rw.find("}' \\\"$_O\\\" \\\"$_R\\\"\\n\"", a0)
prog = c_lits(rw[a0:rw.find("\n", a1)]) if a0 > 0 and a1 > a0 else ""
prog = prog[prog.find("'") + 1:prog.rfind("'")]
check("the dstats awk is found", a0 > 0 and a1 > a0 and "nclients" in prog, prog[:120])
if a0 > 0 and a1 > a0 and shutil.which("awk"):
    w = tempfile.mkdtemp(prefix="dwcnt_")
    try:
        c = os.path.join(w, "ctr"); r_ = os.path.join(w, "rec")
        open(c, "w").write("SINCE 1700000000\nTOTAL 300\n" + "".join("CLIENT 192.168.50.%d %d 1700000100\n" % (i + 10, 100 - i) for i in range(30)))
        open(r_, "w").write("")
        o = subprocess.run(["awk", prog, c, r_], capture_output=True, text=True)
        try: j = json.loads("{" + o.stdout)
        except ValueError: j = None
        check("30 devices kept -> nclients 30, the list still 20", j and j.get("nclients") == 30 and len(j.get("clients", [])) == 20, o.stdout[:300] + o.stderr)
    finally:
        shutil.rmtree(w, ignore_errors=True)
check("the tile shows nclients, with + at the 100 the counters keep",
      "var ndev = (j.nclients != null) ? j.nclients : (j.clients||[]).length;" in dwp and "(ndev >= 100 ? '+' : '')" in dwp
      and "(the 100 largest of each kept)" in rw)

# ---- (4) Warden: every LAN bridge's IPv6 prefix
v = re.search(r'fputs\("V6BR=\\"\\"\\n"(.*?), f\);', rw, re.S)
snip = c_lits('"V6BR=\\"\\"\\n"' + v.group(1)) if v else ""
check("the bridge-prefix collector is there", bool(snip) and "ip -6 -o addr show scope global" in snip)
if snip and SH:
    w = tempfile.mkdtemp(prefix="v6br_")
    try:
        ipf = os.path.join(w, "ip")
        open(ipf, "w").write('#!/bin/sh\ncat <<EOF\n'
            '5: br0    inet6 2001:db8:1:0::1/64 scope global dynamic\\       valid_lft 86000sec\n'
            '9: br52    inet6 2001:db8:1:52::1/64 scope global\\       valid_lft forever\n'
            '9: br52    inet6 2001:db8:1:52::1/64 scope global\\       valid_lft forever\n'
            '3: eth0    inet6 2001:db8:ffff::2/64 scope global\\       valid_lft forever\n'
            '12: br0    inet6 2001:db8:ffff::9/64 scope global\\       valid_lft forever\n'
            'EOF\n')
        os.chmod(ipf, 0o755)
        r = run('V6WAN="2001:db8:ffff::9 "\n' + snip + 'echo "[$V6BR]"\n', {"PATH": w + os.pathsep + os.environ.get("PATH", "")})
        check("every bridge's global prefix once; not the WAN interface, not the WAN address on a bridge",
              r.stdout.strip() == "[ 2001:db8:1:0::1/64 2001:db8:1:52::1/64]", r.stdout + r.stderr)
    finally:
        shutil.rmtree(w, ignore_errors=True)
check("inbound: each bridge prefix is RETURNed after the main LAN prefix, before the WireGuard / country / feed rules",
      0 < rw.find('[ -n \\"$V6LAN\\" ] && ip6tables -A REAPER_WARDEN -s') < rw.find('for _q in $V6BR; do ip6tables -A REAPER_WARDEN -s \\"$_q\\" -j RETURN; done')
      < rw.find('rw_emit_country_rules(f, "ip6tables", "REAPER_WARDEN", "src", "RW_DROP", 1);'))
dg = rw[rw.find('"%s -A %s -d ::1/128 -j RETURN\\n"'):]
dg = dg[:dg.find(");") + 2]
check("destination group: the bridge prefixes too, one ipt/chain pair per %s line", 'for _q in $V6BR; do %s -A %s -d \\"$_q\\" -j RETURN; done' in dg
      and dg.count("%s -A %s") * 2 == dg.count("ipt, chain") * 2 and dg.count("%s -A %s") == dg.count("ipt, chain"), dg)
check("the collector runs before the rules use it", 0 < rw.find('fputs("V6BR=') < rw.find("for _q in $V6BR; do ip6tables"))

# ---- (5) page texts
packs = sorted(f[:-5] for f in os.listdir(os.path.join(SRC, "www")) if re.match(r"^[A-Z]{2}\.dict$", f))
bad = []
for pk in packs:
    t = rd("www/%s.dict" % pk)
    g = dict(re.findall(r"^(RWDN_11|RWDN_18|RWDN_111|RWDN_118|RSHD_133)=(.*?)\r?$", t, re.M))
    ok = (len(g) == 5 and "Ctrl" not in g["RWDN_11"] and "2001:db8::/32" in g["RWDN_18"] and "abuse.ch" not in g["RWDN_111"]
          and ".lan" in g["RWDN_118"] and "GitHub" in g["RWDN_118"] and "VPN Director" in g["RSHD_133"] and "%1" in g["RSHD_133"]
          and "`" not in g["RSHD_133"])
    if not ok: bad.append(pk)
check("the five corrected texts in all %d packs (no Ctrl-click, IPv6 example, no abuse.ch, the never-block list, VPN Director)" % len(packs),
      len(packs) == 25 and not bad, bad)

print("\n%d failure(s)" % len(fails) if fails else "\nall checks passed")
if fails:
    print("\n".join(fails)); sys.exit(1)
