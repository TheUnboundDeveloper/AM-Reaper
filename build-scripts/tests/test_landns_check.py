#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The dashboard's LAN name resolution check (2026-10-10) - decision logic on the host, wiring pinned.

WHY THIS EXISTS. The dashboard's Internet status said "Connected" whenever the WAN held an address
(wanN_state_t), so a box whose LAN devices could not resolve a single name still read green
(RT-BE86U 2026-10-04: unbound up, its WireGuard upstream down). rc/rdnshc.c now asks the path LAN
devices use once a minute - the router's DNS for "localhost" (nothing leaves the box) and for a
random name under reaper_landns_domain (past every cache), or the servers DHCP hands out when the
admin set any - and publishes nvram reaper_landns_state "<state> <s> <silent|->". The dashboard keeps
the word "Connected", turns the dot and word amber while the check fails, and explains the state in
a tooltip on the WAN pill and on the Internet card. Status only: nothing moved, nothing reloaded,
link_internet (WAN LEDs, Dual-WAN fail-over) never touched.

WHAT IT DOES. Compiles the LANDNS-PURE block of rc/rdnshc.c on the host behind a small main and
checks the reply verdict, the two-in-a-row state machine and the domain validator; then pins the
wiring in rdnshc.c, defaults.c, Main_ReaperDash.asp, Reaper_Failover.asp, the 25 language packs and
verify_markers.txt. 2026-10-11: the shell header (reaper_shell.asp, which frames every other page)
carries the same tooltip, state and colours; its shared functions must stay verbatim copies of the
dashboard's. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - argv[1] or
REAPER_ROUTER_SRC = .../release/src/router)."""
import glob, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rdnshc.c")):
    skip("no router source tree with rc/rdnshc.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

rd = read("rc/rdnshc.c")
m = re.search(r"/\* LANDNS-PURE-BEGIN.*?\*/(.*?)/\* LANDNS-PURE-END \*/", rd, re.S)
check("rdnshc.c carries the LANDNS-PURE block", m is not None)
if not m:
    print("\n1 check failed"); sys.exit(1)

MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
%s
int main(int argc, char **argv)
{
	int a;
	for (a = 1; a < argc; a++) {
		char *s = argv[a];
		if (s[0] == 'r') printf("%%d\n", landns_rcode_ok(atoi(s + 1)));
		else if (s[0] == 'd') printf("%%d\n", landns_domain_ok(s + 1));
		else if (s[0] == 's') {
			/* s<cur>:<r1>,<r2>,...  -> the state after each check */
			int cur = atoi(s + 1), bad = 0;
			char *p = strchr(s, ':') + 1, *tok;
			for (tok = strtok(p, ","); tok; tok = strtok(NULL, ",")) {
				cur = landns_step(cur, atoi(tok), &bad);
				printf("%%d%%s", cur, strchr(tok, 0)[0] ? "" : " ");
			}
			printf("\n");
		}
	}
	return 0;
}
''' % m.group(1)
td = tempfile.mkdtemp(prefix="landns-")
try:
    c = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    open(c, "w").write(MAIN)
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
    if p.returncode != 0 or "warning" in p.stderr:
        print(p.stderr); check("the LANDNS-PURE block compiles clean with -Wall -Wextra", False); raise SystemExit
    check("the LANDNS-PURE block compiles clean with -Wall -Wextra", True)

    def run(args):
        r = subprocess.run([exe] + args, capture_output=True, text=True)
        return [l.strip() for l in r.stdout.splitlines()]

    # reply verdict: NOERROR and NXDOMAIN prove the path; SERVFAIL, REFUSED, others and silence do not
    want = {"-1": "0", "0": "1", "1": "0", "2": "0", "3": "1", "4": "0", "5": "0", "15": "0"}
    got = run(["r" + k for k in want])
    check("reply verdict: NOERROR/NXDOMAIN = path alive; SERVFAIL/REFUSED/other/silence = not", got == list(want.values()), got)

    # domains
    dom = {"example.com": "1", "dns.msftncsi.com": "1", "a-b.c-d.net": "1", "localhost": "0", ".example.com": "0",
           "example..com": "0", "example.com.": "0", "ex_ample.com": "0", "a.b": "1", "ab": "0",
           ("x" * 64) + ".com": "0", ("x" * 63) + ".com": "1", "exa mple.com": "0"}
    got = run(["d" + k for k in dom])
    check("domain validator: dot-separated labels of 1-63 [A-Za-z0-9-], two or more labels", got == list(dom.values()), list(zip(dom, got)))

    # state machine: 0 UNK 1 OK 2 FAIL 3 SVC 4 DFAIL 5 HELD 6 OFF
    seqs = {
        "s0:1": "1",                 # first good check -> ok
        "s0:2": "0",                 # one bad check from unknown -> still unknown
        "s0:2,2": "02",              # two in a row -> fail
        "s1:2": "1",                 # one bad check does not flip a good state
        "s1:2,1": "11",              # ...and a good one resets the count
        "s1:2,2": "12",
        "s1:3,3": "13",              # the router's DNS dead
        "s1:4,4": "14",              # the DHCP-handed servers dead
        "s2:1": "1",                 # one good check clears at once
        "s1:2,2,3": "123",           # already bad: the next bad check names the new cause at once
        "s1:5": "5",                 # WAN down: held, counter reset
        "s5:2": "0",                 # back from held: unknown until judged
        "s5:2,2": "02",
        "s1:2,5,2": "150",           # a hold in between restarts the count
        "s6:2": "0",                 # switched back on: unknown, not the stale state
    }
    got = run(list(seqs))
    check("state machine: two bad checks in a row turn it bad, one good check clears, a hold resets",
          [g.replace(" ", "") for g in got] == list(seqs.values()), list(zip(seqs, got)))
except SystemExit:
    pass
finally:
    shutil.rmtree(td, ignore_errors=True)

# ---------------------------------------------------------------- wiring: the daemon
check("probe_addr() is the old probe on top of dns_ask() (same verdict, port 53, the configured name)",
      "static int dns_ask(const char *addr, int af, int port, const char *name, int timeout_ms, int *ancount)" in rd
      and "int an = 0, rc = dns_ask(addr, af, 53, c->name, c->timeout_ms, &an);" in rd
      and "if (!c->strict) return 1;" in rd and "return (rc == 0 && an > 0);" in rd)
loop = rd[rd.find("int rdnshc_main("):]
check("the check runs every pass, before the health check's own off-branch (so it works with that switch off)",
      0 < loop.find("landns_tick(&ld);") < loop.find("if (!enabled) {"))
check("it paces itself: a check every 60 s, the first 15 s after start", "#define LDNS_EVERY\t60" in rd and "#define LDNS_FIRST\t15" in rd)
tick = rd[rd.find("static void landns_tick("):rd.find("int rdnshc_main(")]
check("the router's DNS is asked for localhost on lan_ipaddr:53 and for a random label under the domain",
      'dns_ask(lan, AF_INET, 53, "localhost", LDNS_LOCAL_MS, NULL) < 0' in tick
      and 'snprintf(q, sizeof(q), "rq%08x.%s", (unsigned)rand(), d);' in tick
      and "dns_ask(lan, AF_INET, 53, q, LDNS_FRESH_MS, NULL)" in tick)
check("the domain falls back to dns_probe_host, then a fixed name, when the setting is empty or invalid",
      'nvram_safe_get("reaper_landns_domain")' in tick and 'nvram_safe_get("dns_probe_host")' in tick)
check("the servers DHCP hands out are checked instead when the admin set any",
      "landns_dhcp_targets(tg)" in tick and '"dhcp_dns1_x", "dhcp_dns2_x"' in rd and 'nvram_match("dhcp_enable_x", "1")' in rd)
check("no check while the primary WAN is down (state 'wan')", "if (landns_uplink_down())" in tick and "wan_primary_ifunit()" in rd)
check("a failing fresh name asks each upstream directly to name the silent ones (port kept, under the resolv lock)",
      "landns_silent_upstreams(q, silent, sizeof(silent));" in tick and 'lock = file_lock("resolv");' in rd
      and 'snprintf(nm, sizeof(nm), "%s#%d", addr[i], port[i]);' in rd)
check("the silent-upstream pass asks every upstream at once: one wait within LDNS_UP_MS, not one per server (2026-10-13)",
      "static void dns_ask_many(int n, char addr[][INET6_ADDRSTRLEN], const int *fam, const int *port," in rd
      and "dns_ask_many(n, addr, fam, port, qname, LDNS_UP_MS, ok);" in rd and "gettimeofday(&t0, NULL);" in rd
      and "dns_build(pkt, sizeof(pkt), name, &id[i])" in rd
      and not re.search(r"for \(i = 0; i < n && !g_stop; i\+\+\) \{\s*char nm\[[^\n]*\n\s*if \(landns_rcode_ok\(dns_ask\(", rd))
check("published as reaper_landns_state '<state> <s> <silent|->', cleared when the daemon stops",
      'snprintf(v, sizeof(v), "%s %ld %s", landns_name(ld->st), t - ld->since, *ld->silent ? ld->silent : "-");' in rd
      and 'nvram_set("reaper_landns_state", v);' in rd and 'nvram_set("reaper_landns_state", "");' in rd)
check("syslog: one line when it turns bad, one when it recovers (no line per check)",
      tick.count('logmessage(HC_TAG, "LAN name resolution FAILING') == 4 and tick.count("LAN name resolution restored after") == 1
      and "if (landns_is_bad(ld->st) && ld->st != prev)" in tick)
check("status only: the check never moves the DNS list, reloads dnsmasq, or writes link_internet",
      "assert_order" not in tick and "hc_reload" not in tick and "update_resolvconf" not in tick
      and not re.search(r'nvram_set(_int)?\(\s*"link_internet"', rd))
check("switched off with reaper_landns_enable=0 (a missing key counts as on; the defaults table always fills the key)",
      'if (nvram_match("reaper_landns_enable", "0"))' in tick)

df = read("shared/defaults.c")
check("defaults: reaper_landns_enable=0 (off at factory, owner 2026-10-12) and reaper_landns_domain empty",
      '{ "reaper_landns_enable", "0", CKN_STR1,' in df and '{ "reaper_landns_domain", "", CKN_STR128,' in df)

# ---------------------------------------------------------------- wiring: the dashboard
db = read("www/Main_ReaperDash.asp")
check("dashboard reads the state at render and in the live poll",
      "landns:   '<% nvram_get(\"reaper_landns_state\"); %>'," in db
      and "'reaper_landns_state'];" in db and "if(typeof j.reaper_landns_state==='string') NET.lan=j.reaper_landns_state;" in db)
check("both Internet paints end in netPaint() (amber wins while failing; colours handed back when it clears)",
      db.count("netPaint();") >= 2 and "e.style.background = amber ? 'var(--amber)' : '';" in db
      and "e.style.color = amber ? 'var(--amber)' : '';" in db)
check("amber only while the WAN is up; the word itself is never replaced",
      "amber=any && landnsBad(landnsGet().st)" in db and "textContent = amber" not in db)
check("one tooltip box at page level, anchored on the WAN pill and the Internet card's status",
      '<div id="ntip" class="ntip" role="tooltip" hidden></div>' in db
      and 'id="p_wan_pill" tabindex="0" role="button" aria-describedby="ntip"' in db
      and 'id="i_state_box" tabindex="0" role="button" aria-describedby="ntip"' in db)
check("the box is outside the clipping pill strip, fixed, width-capped and wrapping",
      ".ntip{position:fixed;" in db and "max-width:min(320px,calc(100vw - 32px))" in db and "overflow-wrap:anywhere" in db
      and db.find('<div id="ntip"') > db.find("</main>"))
tip = db[db.find("var NET={v4:false"):db.find("function tipPlace(a){")]
check("tooltip text goes in as text nodes, never as HTML", "innerHTML" not in tip and "document.createTextNode(p)" in tip and "b.textContent=t;" in tip)
check("hover opens for a mouse, focus and tap open, a click pins; Esc / tap elsewhere / scroll / resize close",
      "e.pointerType==='mouse'" in db and "a.addEventListener('focus'" in db and "TIP.pinned=true;" in db
      and "e.key==='Escape' && TIP.open" in db and "window.addEventListener('scroll'" in db and "window.addEventListener('resize'" in db)
check("no tooltip in AP / repeater / bridge mode (the two spots are plain text again)",
      "if(!ROUTING || !TIP.el){" in db and "a.removeAttribute('tabindex');" in db)

# ---------------------------------------------------------------- wiring: the shell header (every framed page)
sh = read("www/reaper_shell.asp")
check("shell reads the state at render and in the live poll (with the IPv6 face, for the Internet line)",
      "lan:'<% nvram_get(\"reaper_landns_state\"); %>'" in sh
      and "%3bnvram_get(reaper_landns_state)%3bwan_ipv6_network()&_=" in sh
      and "if(typeof j.reaper_landns_state==='string') NET.lan=j.reaper_landns_state;" in sh
      and "if(j.wan_ipv6_network && typeof j.wan_ipv6_network==='object') WAN6=j.wan_ipv6_network;" in sh)
check("shell: first render and the poll paint through one painter that ends in netPaint()",
      "function paintWan(p){" in sh and "function apply(p){ return paintWan(p); }" in sh
      and "paintWan(wanPickIp({wan0_state_t:" in sh and sh.count("netPaint();") >= 1)
pills = sh[sh.find("var WANS_LB="):]
check("shell: amber only while the WAN is up; danger when down; the mode name in steel without a WAN; no literal crimson left",
      "amber=any && landnsBad(landnsGet().st)" in sh and "d.style.background='var(--danger)'" in sh
      and "if(!ROUTING){" in sh and "n.style.background='var(--steel)'" in sh and "'#E10600'" not in pills)
check("shell: one tooltip box at page level, anchored on the WAN pill, above the sticky header (300)",
      '<div id="ntip" class="ntip" role="tooltip" hidden></div>' in sh
      and 'id="p_wan_pill" tabindex="0" role="button" aria-describedby="ntip"' in sh
      and sh.find('<div id="ntip"') > sh.find("</main>") and ".ntip{position:fixed;z-index:310;" in sh
      and "max-width:min(320px,calc(100vw - 32px))" in sh and "overflow-wrap:anywhere" in sh)
check("shell: focus leaving for the framed page closes the box; Esc / tap elsewhere / scroll / resize as on the dashboard",
      "window.addEventListener('blur', function(){ if(TIP.open) tipHide(); });" in sh
      and "e.key==='Escape' && TIP.open" in sh and "window.addEventListener('scroll', function(){ if(TIP.open) tipHide(); }, true);" in sh)
check("shell: no tooltip in AP / repeater / bridge mode (the pill is plain text again)",
      "if(!ROUTING || !TIP.el){" in sh and "a.removeAttribute('tabindex');" in sh)

def fn_body(src, name):
    """The text of `function name(...){...}` with each line stripped (the shell indents its copy)."""
    i = src.find("function %s(" % name)
    if i < 0:
        return None
    j = src.find("{", i); depth = 0; k = j
    while k < len(src):
        c = src[k]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: break
        k += 1
    return "\n".join(l.strip() for l in src[i:k + 1].splitlines())
SHARED = ("v6Up", "landnsGet", "landnsBad", "durTxt", "tipRow", "tipB", "tipFill", "tipPlace", "tipShow", "tipHide", "tipBind")
differ = [n for n in SHARED if fn_body(db, n) is None or fn_body(db, n) != fn_body(sh, n)]
check("shell: the readings, their colours and the open/close rules are the dashboard's functions verbatim (%d shared)" % len(SHARED),
      not differ, differ)
check("shell: tooltip text goes in as text nodes, never as HTML",
      "innerHTML" not in sh[sh.find("var NET={v4:false"):sh.find("function tipPlace(a){")])

# ---------------------------------------------------------------- wiring: DNS Failover page
fo = read("www/Reaper_Failover.asp")
check("DNS Failover: switch, domain field, live status, and both keys posted with restart_rdnshc",
      'id="landns" <% nvram_match("reaper_landns_enable", "1", "checked"); %>' in fo and 'id="landns_dom"' in fo
      and 'id="ld_v"' in fo and "reaper_landns_enable: on('landns'), reaper_landns_domain: $id('landns_dom').value" in fo
      and "v.reaper_landns_enable !== ORIG.landns || v.reaper_landns_domain !== ORIG.landnsdom) svc += 'restart_rdnshc;'" in fo
      and "nvram_get(reaper_dnshc_state)%3bnvram_get(reaper_landns_state)" in fo)
check("DNS Failover validates the domain the way the daemon does (empty, or 1-63-char labels)",
      "/^([A-Za-z0-9-]{1,63}\\.)+[A-Za-z0-9-]{1,63}$/" in fo)

# ---------------------------------------------------------------- packs
packs = [x for x in glob.glob(os.path.join(SRC, "www", "*.dict")) if not x.endswith("temp.dict")]
need = ["RDSH_%d=" % k for k in range(91, 104)] + ["RDHC_%d=" % k for k in range(59, 65)]
miss = [os.path.basename(x) for x in packs if any(t not in open(x, encoding="utf-8", errors="replace").read() for t in need)]
check("RDSH_91..103 and RDHC_59..64 exist in all 25 language packs", len(packs) == 25 and not miss, miss)
counts = {sum(1 for _ in open(x, "rb")) for x in packs}
check("the 25 packs stay in lockstep", len(counts) == 1, counts)

here = os.path.dirname(os.path.abspath(__file__))
mk = os.path.join(here, "..", "verify_markers.txt")
if os.path.isfile(mk):
    t = open(mk, encoding="utf-8").read()
    check("verify_markers pins the daemon's log line and key and both pages",
          "sbin/rc|LAN name resolution FAILING|1" in t and "sbin/rc|reaper_landns_state|1" in t
          and "www/Main_ReaperDash.asp|reaper_landns_state|2" in t and "www/Reaper_Failover.asp|reaper_landns_enable|2" in t)
    check("verify_markers pins the shell header's copy (state read + the shared tooltip body + the painter)",
          "www/reaper_shell.asp|reaper_landns_state|2" in t and "www/reaper_shell.asp|function tipFill(){|1" in t
          and "www/reaper_shell.asp|function paintWan(p){|1" in t)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
