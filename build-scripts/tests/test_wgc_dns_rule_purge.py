#!/usr/bin/env python3
"""WireGuard client: the old DNS policy rule must go when the DNS changes or is removed (field report 2026-11-08).

WHY. A VPN client's DNS rules ("ip rule add iif lo to <dns> table <client> priority 1000 + idx * 3 + i", made by
vpnc_up() from nvram vpncN_dns) were deleted by the addresses now in vpncN_dns. A WireGuard DNS change rewrites
vpncN_dns in start_wgc() before anything deletes, and a client restart (stop_wgc + start_wgc) never deleted at all,
so the rule for the old address stayed. With the DNS removed, vpncN_dns was not written at all: the old address
stayed in nvram, so the old rule came back after a reboot.

WHAT IT DOES.
- Compiles vpnc_purge_dns_rules() from rc/vpnc_fusion.c on the build host (-Wall -Werror) against a mock rule table
  that deletes the way the kernel does (an "ip rule del" without "to" matches any destination) and checks:
  the field-report case, duplicates, mixed IPv4 / IPv6, a third DNS whose priority overlaps the next client's,
  other clients' and other tables' rules kept, and the no-rule case costing one try per family.
- Compiles _wg_client_dns_setup_vpnc() from rc/wireguard.c with stubs and checks vpncN_dns for a set, a changed
  and a removed DNS.
- Pins the wiring: _set_network_routing_rule() clears before it adds and a delete is the clear alone, the add still
  uses the priority / iif / table the clear matches, stop_wgc() clears, rc.h declares it.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "rc")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def func(src, sig):
    a = src.index(sig); return src[a:src.index("\n}\n", a) + 3]

vf, wg, rch, sh, shu = rd("rc/vpnc_fusion.c"), rd("rc/wireguard.c"), rd("rc/rc.h"), rd("shared/shared.h"), rd("shared/shutils.h")

# ---------------------------------------------------------------- wiring
try:
    purge = vf[vf.index("#define REAPER_VPNC_DNS_RULES_MAX"):]
    purge = purge[:purge.index("\n}\n") + 3]
except ValueError:
    purge = ""
check("vpnc_fusion.c defines vpnc_purge_dns_rules()", "void vpnc_purge_dns_rules(const int vpnc_idx)" in purge)
check("rc.h declares vpnc_purge_dns_rules()", "extern void vpnc_purge_dns_rules(const int vpnc_idx);" in rch)
try:
    snr = func(vf, "static int _set_network_routing_rule(const VPNC_ROUTE_CMD cmd, const int vpnc_idx)\n{")
except ValueError:
    snr = ""
p_at, add_at = snr.find("vpnc_purge_dns_rules(vpnc_idx);"), snr.find('"rule", cmd_str, "iif", "lo", "to", tmp')
check("_set_network_routing_rule: clears this client's DNS rules before it adds", 0 < p_at < add_at, (p_at, add_at))
check("_set_network_routing_rule: the per-address loop runs on add only (a delete is the clear alone)",
      "if (cmd == VPNC_ROUTE_ADD && vpnc_dns[0] != '\\0')" in snr)
check("_set_network_routing_rule: the add uses the priority the clear walks (1000 + idx * 3 + i, table = client)",
      "IP_RULE_PREF_VPNC_POLICY_IF + vpnc_idx * 3 + i" in snr and "IP_ROUTE_TABLE_ID_VPNC_BASE + vpnc_idx" in snr
      and '"table", id_str, "priority", priority' in snr)
check("vpnc_purge_dns_rules: same priority / table formula, iif lo, both families",
      "IP_RULE_PREF_VPNC_POLICY_IF + vpnc_idx * 3 + i" in purge and "IP_ROUTE_TABLE_ID_VPNC_BASE + vpnc_idx" in purge
      and '"iif", "lo", "table", id_str' in purge and '"-6"' in purge)
try:
    stop = func(wg, "void stop_wgc(int unit)\n{")
except ValueError:
    stop = ""
check("stop_wgc: clears the DNS rules (a restart does not go through vpnc_down)",
      re.search(r"#ifdef RTCONFIG_VPN_FUSION\n(?:\s*/\*.*?\*/\n)?\s*vpnc_purge_dns_rules\(vpnc_idx\);\n#endif", stop, re.S) is not None)
check("stop_wgc: vpnc_idx is set before the clear", 0 <= stop.find("vpnc_idx = find_vpnc_idx_by_wgc_unit(unit);") < stop.find("vpnc_purge_dns_rules(vpnc_idx);"))

# ---------------------------------------------------------------- behaviour
cc = shutil.which("gcc") or shutil.which("cc")
fe = re.search(r"#define foreach_44\(word, wordlist, next\) \\\n(?:.*\\\n)*.*\n", shu)
try:
    setup = func(wg, "static void _wg_client_dns_setup_vpnc(char* prefix, char* ifname, int vpnc_idx)\n{")
except ValueError:
    setup = ""
pref = re.search(r"#define IP_RULE_PREF_VPNC_POLICY_IF\s+(\d+)", sh)
tbl = re.search(r"#define IP_ROUTE_TABLE_ID_VPNC_BASE\s+(\d+)", sh)
PREF, TBL = (int(pref.group(1)) if pref else 0), (int(tbl.group(1)) if tbl else 0)
check("shared.h: IP_RULE_PREF_VPNC_POLICY_IF / IP_ROUTE_TABLE_ID_VPNC_BASE", PREF > 0 and TBL > 0, (PREF, TBL))

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdarg.h>
#define IP_RULE_PREF_VPNC_POLICY_IF %(PREF)d
#define IP_ROUTE_TABLE_ID_VPNC_BASE %(TBL)d
%(FOREACH)s
struct rule { int v6, pref, table, live; char iif[16], dst[48]; };
static struct rule R[64]; static int NR, CALLS;
static void addr(int v6, int pref, const char *iif, int table, const char *dst)
{ struct rule *r = &R[NR++]; r->v6 = v6; r->pref = pref; r->table = table; r->live = 1;
  snprintf(r->iif, sizeof r->iif, "%%s", iif); snprintf(r->dst, sizeof r->dst, "%%s", dst); }
/* "ip -4|-6 rule del priority P iif I table T": first live rule with that family, priority, iif and table,
   whatever its destination (no "to" given) - the kernel's delete match; exit 2 when there is none */
static int _eval(char *const argv[], const char *path, int timeout, int *ppid)
{
	int i, v6, pref, table; (void)timeout; (void)ppid;
	CALLS++;
	if (!path || strcmp(path, ">/dev/null")) { printf("BADPATH\n"); return 9; }
	if (strcmp(argv[0], "ip") || strcmp(argv[2], "rule") || strcmp(argv[3], "del") || strcmp(argv[4], "priority")
	 || strcmp(argv[6], "iif") || strcmp(argv[8], "table") || argv[10]) { printf("BADARGV\n"); return 9; }
	v6 = !strcmp(argv[1], "-6"); pref = atoi(argv[5]); table = atoi(argv[9]);
	for (i = 0; i < NR; i++)
		if (R[i].live && R[i].v6 == v6 && R[i].pref == pref && R[i].table == table && !strcmp(R[i].iif, argv[7]))
		{ R[i].live = 0; return 0; }
	return 2;
}
static void dump(void)
{ int i; for (i = 0; i < NR; i++) if (R[i].live) printf("%%s:%%d:%%s:%%d:%%s ", R[i].v6 ? "v6" : "v4", R[i].pref, R[i].iif, R[i].table, R[i].dst);
  printf("| calls=%%d\n", CALLS); }
static void reset(void) { NR = 0; CALLS = 0; }

/* _wg_client_dns_setup_vpnc stubs */
static char WGDNS[128], NV[128], ROUTES[512];
static const char *nvram_pf_safe_get(const char *prefix, const char *k) { (void)prefix; (void)k; return WGDNS; }
static int nvram_set(const char *k, const char *v) { snprintf(NV, sizeof NV, "%%s=%%s", k, v); return 0; }
static char *trim_r(char *s) { size_t n = strlen(s); while (n && isspace((unsigned char)s[n-1])) s[--n] = 0; return s; }
static size_t h_strlcat(char *d, const char *s, size_t sz)
{ size_t n = strlen(d), m = strlen(s); if (n + 1 < sz) { size_t c = m < sz - n - 1 ? m : sz - n - 1; memcpy(d + n, s, c); d[n + c] = 0; } return n + m; }
#define strlcat h_strlcat
static int eval(const char *a0, ...)
{ va_list ap; const char *s; strcat(ROUTES, a0); va_start(ap, a0);
  while ((s = va_arg(ap, const char *))) { strcat(ROUTES, " "); strcat(ROUTES, s); } va_end(ap); strcat(ROUTES, ";"); return 0; }
#define eval(...) eval(__VA_ARGS__, (char *)0)

%(PURGE)s
%(SETUP)s
int main(int argc, char **argv)
{
	const char *s = argc > 1 ? argv[1] : "";
	int B1 = IP_RULE_PREF_VPNC_POLICY_IF + 1 * 3, B2 = IP_RULE_PREF_VPNC_POLICY_IF + 2 * 3;
	int T1 = IP_ROUTE_TABLE_ID_VPNC_BASE + 1, T2 = IP_ROUTE_TABLE_ID_VPNC_BASE + 2;
	if (!strcmp(s, "field")) {        /* the report: old and new address at + 1, plus rules that must stay */
		addr(0, B1 + 1, "lo", T1, "10.8.0.1"); addr(0, B1 + 1, "lo", T1, "10.9.0.1");
		addr(0, B1, "br54", T1, "");            /* the client's own device-policy rule at its base */
		addr(0, B2 + 1, "lo", T2, "10.2.0.1");  /* client 2's DNS rule */
		addr(0, 100, "lo", T1, "10.8.0.1");     /* another rule family on the same table */
		vpnc_purge_dns_rules(1); dump();
	} else if (!strcmp(s, "dups")) {  /* duplicates, IPv6 second, a third DNS on client 2's base priority */
		addr(0, B1 + 1, "lo", T1, "10.8.0.1"); addr(0, B1 + 1, "lo", T1, "10.8.0.1"); addr(0, B1 + 1, "lo", T1, "10.8.0.1");
		addr(1, B1 + 2, "lo", T1, "fd00::1"); addr(0, B1 + 3, "lo", T1, "10.8.0.3");
		addr(0, B2, "br55", T2, "");            /* client 2's base rule at the same priority as client 1's + 3 */
		vpnc_purge_dns_rules(1); dump();
	} else if (!strcmp(s, "none")) {
		addr(0, B2 + 1, "lo", T2, "10.2.0.1");
		vpnc_purge_dns_rules(1); dump();
	} else if (!strcmp(s, "two")) {   /* client 2's clear leaves client 1 alone */
		addr(0, B1 + 1, "lo", T1, "10.8.0.1"); addr(0, B2 + 1, "lo", T2, "10.2.0.1"); addr(1, B2 + 2, "lo", T2, "fd00::2");
		vpnc_purge_dns_rules(2); dump();
	} else if (!strncmp(s, "setup:", 6)) {
		snprintf(NV, sizeof NV, "vpnc1_dns=10.8.0.1");
		snprintf(WGDNS, sizeof WGDNS, "%%s", s + 6);
		_wg_client_dns_setup_vpnc("wgc1_", "wgc1", 1);
		printf("%%s | %%s\n", NV, ROUTES);
	}
	return 0;
}
'''

def run(tmp, arg):
    r = subprocess.run([os.path.join(tmp, "h"), arg], capture_output=True, text=True, timeout=30)
    return r.stdout.strip() if r.returncode == 0 else "<harness exit %d> %s" % (r.returncode, r.stdout.strip())

if not cc:
    check("host C compiler for the behaviour checks", False, "no gcc/cc")
elif purge and setup and fe and PREF and TBL:
    src = HARNESS % {"PREF": PREF, "TBL": TBL, "FOREACH": fe.group(0), "PURGE": purge, "SETUP": setup}
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "h.c"), "w").write(src)
        r = subprocess.run([cc, "-Wall", "-Werror", "-Wno-unused-function", "-o", os.path.join(tmp, "h"), os.path.join(tmp, "h.c")],
                           capture_output=True, text=True)
        check("the clear and the DNS setup compile on the host (-Wall -Werror)", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            B1, B2, T1, T2 = PREF + 3, PREF + 6, TBL + 1, TBL + 2
            o = run(tmp, "field")
            check("field report: both addresses' rules at %d go, whatever address they were made for" % (B1 + 1),
                  "calls=" in o and not any(x.startswith("v4:%d:" % (B1 + 1)) for x in o.split("|")[0].split()), o)
            check("field report: the client's device rule, client 2's DNS rule and the priority-100 rule stay",
                  all(x in o for x in ("v4:%d:br54:%d:" % (B1, T1), "v4:%d:lo:%d:10.2.0.1" % (B2 + 1, T2), "v4:100:lo:%d:10.8.0.1" % T1)), o)
            o = run(tmp, "dups")
            live = o.split("|")[0].split()
            check("duplicates, an IPv6 second DNS and a third DNS all go", live == ["v4:%d:br55:%d:" % (B2, T2)], o)
            o = run(tmp, "none")
            check("nothing to clear: one try per family, other clients untouched",
                  o.endswith("calls=2") and "10.2.0.1" in o, o)
            o = run(tmp, "two")
            check("client 2's clear removes its IPv4 and IPv6 rules and leaves client 1's",
                  o.split("|")[0].split() == ["v4:%d:lo:%d:10.8.0.1" % (B1 + 1, T1)], o)
            o = run(tmp, "setup:10.9.0.1/32")
            check("DNS set: vpnc1_dns is the new address, its route goes in the client table",
                  o.startswith("vpnc1_dns=10.9.0.1 |") and "ip route add 10.9.0.1 dev wgc1 table 1;" in o, o)
            o = run(tmp, "setup:10.9.0.1,fd00::1/128")
            check("two DNS: both, space separated, prefixes stripped", o.startswith("vpnc1_dns=10.9.0.1 fd00::1 |"), o)
            o = run(tmp, "setup:")
            check("DNS removed: vpnc1_dns is emptied (it kept the old address before)", o.startswith("vpnc1_dns= |"), o)
else:
    check("sources for the behaviour checks found (clear, setup, foreach_44)", False,
          (bool(purge), bool(setup), bool(fe), PREF, TBL))

print("%d checks failed" % len(fails) if fails else "all checks passed")
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
