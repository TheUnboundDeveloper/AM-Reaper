#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Warden never drops the WireGuard server's own handshakes from the internet (field, GT-BE98 v3.6.2, 2026-11-01).

WHY THIS EXISTS. Warden drops inbound traffic by SENDER (threat feeds, blocked countries). A phone on mobile
data reaches the WireGuard server from a carrier address that changes all the time and can sit in a feed or a
blocked country, so the server was unreachable from outside and the allow list (fixed addresses) cannot help.
Now the listen port of every ENABLED server is exempt for packets addressed to the router itself. That is safe
because WireGuard answers nothing it cannot authenticate: an initiation not keyed to the server's public key is
dropped silently and a handshake completes only for a configured peer key.

WHAT IT CHECKS, by running the generated shell (not by grepping it):
  (1) the port collection (RW_SH_WGPORTS_BODY) with stubbed nvram: only ENABLED servers, only ports 1-65535,
      a hostile value ("51820; reboot", "$(x)") never reaches a rule;
  (2) the emitted v4 and v6 rules against a stub iptables/ip6tables: UDP, that port, the ROUTER as
      destination (v4 addrtype LOCAL; v6 each of the router's own addresses), RETURN - never ACCEPT;
  (3) placement in rw_gen_apply(): after the manual-ban drop (a banned sender stays banned), before the geo and
      feed drops, only in REAPER_WARDEN (never RW_OUT / RW_SELF), the port list built before the chain;
  (4) the unit list matches shared/vpn_utils.h WG_SERVER_MAX;
  (5) restart_wgs re-runs Warden's apply.sh under the firewall lock, so on/off and port changes apply at once.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
RW = os.path.join(SRC, "rc", "rwarden.c") if SRC else ""
if not RW or not os.path.isfile(RW):
    print("SKIP: no router source tree"); sys.exit(77)
SH = shutil.which("sh")
if not SH:
    print("SKIP: no sh"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(RW, encoding="utf-8").read()
svc = open(os.path.join(SRC, "rc", "services.c"), encoding="utf-8").read()

def c_lits(text):
    """concatenate the C string literals in text, decoded"""
    out = []
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', text):
        s = m.group(1)
        s = re.sub(r'\\(.)', lambda x: {"n": "\n", "t": "\t"}.get(x.group(1), x.group(1)), s)
        out.append(s)
    return "".join(out)

m = re.search(r'#define RW_SH_WGPORTS_BODY \\\n((?:[^\n]*\\\n)*[^\n]*\n)', src)
check("RW_SH_WGPORTS_BODY exists", m is not None)
body = c_lits(m.group(1)) if m else ""
units = re.search(r'#define RW_WG_UNITS (\d+)', src)
vpn = os.path.join(SRC, "shared", "vpn_utils.h")
wmax = re.search(r'#define WG_SERVER_MAX\s+(\d+)', open(vpn).read()) if os.path.isfile(vpn) else None
check("the fallback unit count equals shared/vpn_utils.h WG_SERVER_MAX",
      units and wmax and units.group(1) == wmax.group(1), (units and units.group(1), wmax and wmax.group(1)))
n = int(wmax.group(1)) if wmax else 2

def wgports(nv):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    for k, v in nv.items(): env["NV_" + k] = v
    script = ('_nv() { eval "printf %s \\"\\${NV_$1}\\""; }\n'
              'WGPORTS=""\nfor _u in ' + " ".join(str(i) for i in range(1, n + 1)) + body + 'printf "[%s]" "$WGPORTS"\n')
    r = subprocess.run([SH, "-c", script], capture_output=True, text=True, env=env)
    return r.stdout.strip(), r.stderr.strip()

if body:
    for label, nv, want in (
        ("no server enabled", {}, "[]"),
        ("server 1 on, 51820", {"wgs1_enable": "1", "wgs1_port": "51820"}, "[ 51820]"),
        ("server 1 OFF keeps its port filtered", {"wgs1_enable": "0", "wgs1_port": "51820"}, "[]"),
        ("both servers on", {"wgs1_enable": "1", "wgs1_port": "51820", "wgs2_enable": "1", "wgs2_port": "51821"}, "[ 51820 51821]"),
        ("only the enabled one of two", {"wgs1_enable": "0", "wgs1_port": "51820", "wgs2_enable": "1", "wgs2_port": "443"}, "[ 443]"),
        ("port 0 refused", {"wgs1_enable": "1", "wgs1_port": "0"}, "[]"),
        ("port 70000 refused", {"wgs1_enable": "1", "wgs1_port": "70000"}, "[]"),
        ("empty port refused", {"wgs1_enable": "1", "wgs1_port": ""}, "[]"),
        ("hostile port value never reaches a rule", {"wgs1_enable": "1", "wgs1_port": "51820; reboot"}, "[]"),
        ("command substitution in the port is inert", {"wgs1_enable": "1", "wgs1_port": "$(echo 1)"}, "[]"),
        ("a range is not a port", {"wgs1_enable": "1", "wgs1_port": "1:65535"}, "[]"),
    ):
        got, err = wgports(nv)
        check("ports: " + label, got == want, (got, err))

def emitted(after):
    """the fprintf literal that follows `after` in rw_gen_apply"""
    i = src.find(after)
    if i < 0: return ""
    j = src.find("fprintf(f,", i)
    k = src.find(");", j)
    return c_lits(src[j:k])

v4 = emitted("WireGuard listen ports, to the router only")
v6 = emitted("WireGuard listen ports, to the router's own v6 addresses only")
check("a v4 rule is emitted", "iptables -A REAPER_WARDEN" in v4, v4)
check("a v6 rule is emitted", "ip6tables -A REAPER_WARDEN" in v6, v6)

def run_rules(line, wgp, v6wan=""):
    script = ('iptables() { echo "iptables $*"; }\nip6tables() { echo "ip6tables $*"; }\n'
              'WGPORTS="%s"\nV6WAN="%s"\n' % (wgp, v6wan)) + line
    return subprocess.run([SH, "-c", script], capture_output=True, text=True).stdout.strip().splitlines()

if v4:
    out = run_rules(v4, " 51820")
    check("v4: UDP 51820 to a LOCAL address returns (skips the geo/feed drops), never ACCEPTs",
          out == ["iptables -A REAPER_WARDEN -p udp --dport 51820 -m addrtype --dst-type LOCAL -j RETURN"], out)
    check("v4: no server enabled -> no rule", run_rules(v4, "") == [])
if v6:
    out = run_rules(v6, " 51820", "2001:db8::1  fd00::1")
    check("v6: one RETURN per router address, UDP 51820 only",
          out == ["ip6tables -A REAPER_WARDEN -p udp --dport 51820 -d 2001:db8::1 -j RETURN",
                  "ip6tables -A REAPER_WARDEN -p udp --dport 51820 -d fd00::1 -j RETURN"], out)
    check("v6: no router address -> no rule (never an address-less exemption)", run_rules(v6, " 51820", " ") == [])
check("never an ACCEPT (Warden is deny-only; the layers behind it still run)", "ACCEPT" not in v4 + v6)

# placement inside rw_gen_apply
g = src[src.find("static void rw_gen_apply(void)"):]
pos = lambda s: g.find(s)
ban4, wg4, geo4 = pos('rw_ban src -j RW_DROP'), pos("WireGuard listen ports, to the router only"), pos('rw_emit_country_rules(f, "iptables", "REAPER_WARDEN"')
ban6, wg6, geo6 = pos('rw_ban6 src -j RW_DROP'), pos("WireGuard listen ports, to the router's own v6"), pos('rw_emit_country_rules(f, "ip6tables", "REAPER_WARDEN"')
check("v4: after the manual ban, before the geo/feed drops", -1 not in (ban4, wg4, geo4) and ban4 < wg4 < geo4, (ban4, wg4, geo4))
check("v6: after the manual ban, before the geo/feed drops", -1 not in (ban6, wg6, geo6) and ban6 < wg6 < geo6, (ban6, wg6, geo6))
check("the port list is built before the chain (and after V6WAN, which the v6 rule reads)",
      -1 < pos('V6WAN=') < pos("fputs(RW_SH_WGPORTS_BODY") < pos('"iptables -N REAPER_WARDEN'))
check("only REAPER_WARDEN carries it (not RW_OUT, not RW_SELF)", src.count("--dport \\\"$_p\\\"") == 2)

# restart_wgs re-applies
blk = svc[svc.find('strcmp(script, "wgs") == 0'):]
blk = blk[:blk.find('strcmp(script, "wgsc") == 0')]
check("restart_wgs re-runs Warden's apply.sh when Warden is on, under the firewall lock",
      'nvram_match("rwarden_enable", "1")' in blk and 'sh /tmp/rwarden/apply.sh' in blk
      and 'file_lock("firewall")' in blk and "file_unlock(" in blk and "reaper_script_ok(" in blk, blk[-600:])

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
