#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Encrypted DNS: the DHCP option 162 offer goes exactly to the devices rednsd serves (v3.8.4, 2026-11-22).

WHY THIS EXISTS. Field report 2026-11-21: an iPhone with a DNS Director rule to another DNS server "kept being kicked
off Wi-Fi". rc/services.c offered the router's encrypted DNS (DHCP option 162, RFC 9463) to the whole LAN, while
rc/encdns.c told rednsd to refuse every device DNS Director sends elsewhere (deny-mac / deny-net). iPhones take the
offer by themselves; offered and then refused before TLS, the phone had no DNS at all.

THE RULE. A device is offered option 162 if and only if rednsd's policy_allows() serves it:
  network served, no rule refuses a device   dhcp-option=<tag>,162,...                 (the line as it always was)
  network served, some devices refused       dhcp-mac=set:rednodnr,<mac> per device + dhcp-option=tag:<tag>,tag:!rednodnr,162,...
  network sent elsewhere (global mode / row) dhcp-mac=set:reddnr,<mac> per device a rule keeps on the router +
                                             dhcp-option=tag:<tag>,tag:reddnr,162,...; no such device = no line
Both sides read DNS Director through ONE function (red_dd_each / red_dd_refused), so they cannot drift.

WHAT IT RUNS. The real reader, red_policy(), rednsd_dnr_option() and the digest are cut out of rc/encdns.c and
compiled on the host against small stand-ins; for a matrix of DNS Director states the devices rednsd's policy lines
serve are compared with the devices the dnsmasq lines offer the option to.

Exit 0 pass, 1 fail, 77 skipped (no router source tree or no host C compiler)."""
import os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
ENC = os.path.join(SRC, "rc", "encdns.c") if SRC else ""
if not ENC or not os.path.isfile(ENC):
    skip("no router source tree with rc/encdns.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
def cut(text, start, end):
    a = text.find(start); b = text.find(end, a + 1) if a >= 0 else -1
    return text[a:b] if 0 <= a < b else ""

enc = rd(ENC)
reader = cut(enc, "#ifdef RTCONFIG_DNSFILTER\n/* the router answers this DNS Director mode itself", "/* peers + DNS Director policy")
policy = cut(enc, "static void red_policy(struct rb *r)", "static int red_enabled(void)")
digest = cut(enc, "/* REAPER-DNR-STEP: a digest of DNS Director's part", "/* what a dnsmasq config written now publishes")
option = cut(enc, "/* REAPER-DNR-STEP: the devices the offer must skip", "/* end of start_dnsmasq(): record what this config publishes */")
state = cut(enc, "static void red_dnr_state(char *buf, size_t sz)", "struct red_dnr_tag")

# ---------------------------------------------------------------- source pins
check("one reader of DNS Director for both users (red_dd_each, red_dd_refused, red_policy_cb)",
      "static int red_dd_each(void (*cb)(const char *mac, int ok, void *arg), void *arg)" in reader
      and "static int red_dd_refused(int mode)" in reader and "static void red_policy_cb(" in reader, len(reader))
check("the reader checks the 17-character shape before ether_atoe() and passes on the normalised address",
      "!red_mac_shape(mac) || !ether_atoe(mac, ea)" in reader and "cb(ether_etoa(ea, macbuf), dnsf_router_ok(safe_atoi(mode)), arg);" in reader)
check("red_policy() reads the rules through the reader only (no second parser of dnsfilter_rulelist)",
      "red_dd_each(red_policy_cb, r);" in policy and "dnsfilter_rulelist" not in policy
      and 'if (red_dd_refused(nvram_get_int("dnsfilter_mode"))) {' in policy, policy[-700:])
check("rednsd_dnr_option() takes the network's DNS Director mode and tags through the same reader",
      "void rednsd_dnr_option(FILE *fp, const char *tag, const char *addr, int dd_mode)" in option
      and option.count("red_dd_each(red_dnr_tag_cb, &dt);") == 2 and "if (!red_dd_refused(dd_mode)) {" in option)
check("the state rc compares before restarting dnsmasq carries DNS Director's part (digest)",
      "unsigned int dg = red_dd_digest();" in state and '"%s %d %d %08x"' in state and '"%s %d %d"' in state)
sv = rd(os.path.join(SRC, "rc", "services.c")); sd = rd(os.path.join(SRC, "rc", "sdn.c")); rh = rd(os.path.join(SRC, "rc", "rc.h"))
check("the main network passes the global mode",
      sv.count('rednsd_dnr_option(fp, "lan", lan_ipaddr, nvram_get_int("dnsfilter_mode"));') == 1 and sv.count("rednsd_dnr_option(") == 1)
check("a guest/VLAN network passes its own DNS Director row; the isolation / portal condition stays",
      sd.count("rednsd_dnr_option(fp, pmtl->nw_t.ifname, pmtl->nw_t.addr, pmtl->sdn_t.dnsf_idx);") == 1 and sd.count("rednsd_dnr_option(") == 1
      and "if (!reaper_sdn_hide_lan_names(pmtl) && pmtl->sdn_t.cp_idx <= 0)" in sd)
check("prototype", "extern void rednsd_dnr_option(FILE *fp, const char *tag, const char *addr, int dd_mode);" in rh)
red = rd(os.path.join(SRC, "rednsd", "rednsd.c"))
acc = cut(red, "if (!policy_allows(&cfg, &a)) {", "continue;")
check("rednsd logs a refusal (one line per address an hour), next to its counter",
      "n_ref_policy++;" in acc and "refused_note(&a);" in acc and "static void refused_note(const sockaddr_u *a)" in red
      and "3600000LL" in cut(red, "static void refused_note(", "\n}\n")
      and 'logmsg(LOG_NOTICE, "rednsd: refused %s - DNS Director sends this device to another DNS server", txt);' in red)
dg = rd(os.path.join(SRC, "others", "reaper_diag"))
check("the diagnostics report counts the devices the offer leaves out (no addresses)",
      "option 162 offer  :" in dg and "'^dhcp-mac=set:rednodnr,'" in dg and "| sort -u | wc -l" in cut(dg, "option 162 offer  :", "\n"))

# ---------------------------------------------------------------- the real functions on the host
H = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>
#include <arpa/inet.h>
#define RTCONFIG_DNSFILTER 1
#define ETHER_ADDR_LEN 6
enum { DNSF_SRV_UNFILTERED = 0, DNSF_SRV_ROUTER = 11 };	/* rc/dnsfilter.h */
struct rb { char b[8192]; };
static void rb_add(struct rb *r, const char *fmt, ...) { va_list ap; size_t l = strlen(r->b); va_start(ap, fmt); vsnprintf(r->b + l, sizeof(r->b) - l, fmt, ap); va_end(ap); }
static int NA; static char **NV;
static const char *nvram_safe_get(const char *k) { int i; size_t l = strlen(k); for (i = 1; i < NA; i++) if (!strncmp(NV[i], k, l) && NV[i][l] == '=') return NV[i] + l + 1; return ""; }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int safe_atoi(const char *s) { return atoi(s); }
/* shared/strings.c: as many fields as there are pointers */
static int _vstrsep(char *buf, const char *sep, ...) { va_list ap; char **p; int n = 0; va_start(ap, sep);
  while ((p = va_arg(ap, char **)) != NULL) { if ((*p = strsep(&buf, sep)) == NULL) break; n++; } va_end(ap); return n; }
#define vstrsep(buf, sep, args...) _vstrsep(buf, sep, args, NULL)
/* shared: takes "zz:zz" as all zeros and ignores what follows the sixth group - the reason for the shape check */
static int ether_atoe(const char *a, unsigned char *e) { char *c = (char *)a; int i = 0; memset(e, 0, 6);
  for (;;) { e[i++] = (unsigned char)strtoul(c, &c, 16); if (!*c++ || i == 6) break; } return i == 6; }
static char *ether_etoa(const unsigned char *e, char *a) { sprintf(a, "%02X:%02X:%02X:%02X:%02X:%02X", e[0], e[1], e[2], e[3], e[4], e[5]); return a; }
static int lan_subnet(char *b, size_t n) { snprintf(b, n, "192.168.50.0/24"); return 1; }
static void red_dnr_state(char *buf, size_t sz) { snprintf(buf, sz, "%s", nvram_safe_get("t_state")); }
static size_t red_adn(unsigned char *o, size_t sz, const char *name) { (void)sz; (void)name; o[0] = 1; return 1; }
static size_t red_dnr_instance(unsigned char *o, size_t osz, int prio, const unsigned char *adn, size_t al, const unsigned char *ip, int doh)
{ (void)osz; (void)adn; (void)al; (void)ip; (void)doh; o[0] = (unsigned char)prio; return 1; }
''' + reader + policy + digest + option + r'''
int main(int argc, char **argv) { struct rb r; NA = argc; NV = argv; r.b[0] = 0;
  if (!strcmp(argv[1], "m=pol")) { red_policy(&r); fputs(r.b, stdout); }
  if (!strcmp(argv[1], "m=lan")) rednsd_dnr_option(stdout, "lan", "192.168.50.1", nvram_get_int("dnsfilter_mode"));
  if (!strcmp(argv[1], "m=sdn")) rednsd_dnr_option(stdout, "br52", "10.20.0.1", nvram_get_int("t_row"));
  if (!strcmp(argv[1], "m=dg")) printf("%08x\n", red_dd_digest());
  return 0; }
'''
tmp = tempfile.mkdtemp(prefix="dnrstep-")
c = os.path.join(tmp, "t.c"); x = os.path.join(tmp, "t")
open(c, "w", encoding="utf-8", errors="surrogateescape").write(H)
r = subprocess.run([CC, "-O1", "-Wall", "-Werror", "-Wno-unused-function", "-o", x, c], capture_output=True, text=True)
check("the real reader, policy, digest and option writer compile on the host", r.returncode == 0, r.stderr)

A, B, C, X = "AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02", "AA:BB:CC:DD:EE:03", "AA:BB:CC:DD:EE:99"
CUSTOM, ROUTER, NONE = 8, 11, 0	# DNSF_SRV_CUSTOM1, _ROUTER, _UNFILTERED
def rules(*pairs):
    return "".join("<dev>%s>%d" % p for p in pairs)
def run(mode, **kv):
    kv.setdefault("t_state", "router.example.net 1 1")
    return subprocess.run([x, "m=" + mode] + ["%s=%s" % i for i in kv.items()], capture_output=True, text=True).stdout
def served(pol, mac):
    """rednsd.c policy_allows(): allow-mac, then deny-mac, then deny-net"""
    L = pol.split("\n")
    if "allow-mac " + mac in L: return True
    if "deny-mac " + mac in L: return False
    return not any(l.startswith("deny-net ") for l in L)
def offered(out, tag, mac):
    """dnsmasq: dhcp-mac sets a tag for a MAC; tag:!x = not set"""
    L = out.split("\n"); no = {l.split(",")[1] for l in L if l.startswith("dhcp-mac=set:rednodnr,")}
    yes = {l.split(",")[1] for l in L if l.startswith("dhcp-mac=set:reddnr,")}
    opt = [l for l in L if ",162," in l]
    if len(opt) > 1: return None
    if not opt: return False
    o = opt[0]
    if o.startswith("dhcp-option=%s,162," % tag): return True
    if o.startswith("dhcp-option=tag:%s,tag:!rednodnr,162," % tag): return mac not in no
    if o.startswith("dhcp-option=tag:%s,tag:reddnr,162," % tag): return mac in yes
    return None

if r.returncode == 0:
    three = rules((A, CUSTOM), (B, ROUTER), (C, NONE))
    CASES = [
        ("DNS Director off (rules stored)", dict(dnsfilter_enable_x=0, dnsfilter_mode=CUSTOM, dnsfilter_rulelist=three)),
        ("on, no rule, global No filtering", dict(dnsfilter_enable_x=1, dnsfilter_mode=NONE, dnsfilter_rulelist="")),
        ("on, no rule, global Router", dict(dnsfilter_enable_x=1, dnsfilter_mode=ROUTER, dnsfilter_rulelist="")),
        ("on, one device sent elsewhere", dict(dnsfilter_enable_x=1, dnsfilter_mode=NONE, dnsfilter_rulelist=three)),
        ("on, global mode sends the LAN elsewhere, two devices kept", dict(dnsfilter_enable_x=1, dnsfilter_mode=CUSTOM, dnsfilter_rulelist=three)),
        ("on, global mode sends the LAN elsewhere, nobody kept", dict(dnsfilter_enable_x=1, dnsfilter_mode=CUSTOM, dnsfilter_rulelist=rules((A, CUSTOM)))),
        ("on, every rule keeps its device on the router", dict(dnsfilter_enable_x=1, dnsfilter_mode=ROUTER, dnsfilter_rulelist=rules((B, ROUTER), (C, NONE)))),
    ]
    bad = []
    for name, kv in CASES:
        pol = run("pol", **kv); lan = run("lan", **kv)
        for mac in (A, B, C, X):
            if offered(lan, "lan", mac) is not served(pol, mac):
                bad.append((name, mac, served(pol, mac), offered(lan, "lan", mac), lan))
    check("main network: a device is offered option 162 exactly when rednsd serves it (%d states x 4 devices)" % len(CASES), not bad, bad[:2])

    off = run("lan", dnsfilter_enable_x=0, dnsfilter_rulelist=three)
    check("no DNS Director part: the line is the one it always was, nothing else written",
          off.startswith("dhcp-option=lan,162,") and off.count("\n") == 1 and "dhcp-mac" not in off, off)
    one = run("lan", dnsfilter_enable_x=1, dnsfilter_mode=NONE, dnsfilter_rulelist=three)
    check("a device sent elsewhere: its tag line, then the option for everybody without that tag",
          one.split("\n")[0] == "dhcp-mac=set:rednodnr," + A and one.split("\n")[1].startswith("dhcp-option=tag:lan,tag:!rednodnr,162,")
          and one.count("dhcp-mac=") == 1, one)
    kept = run("lan", dnsfilter_enable_x=1, dnsfilter_mode=CUSTOM, dnsfilter_rulelist=three)
    check("a LAN sent elsewhere: only the devices a rule keeps on the router get the option",
          sorted(l for l in kept.split("\n") if l.startswith("dhcp-mac=")) == ["dhcp-mac=set:reddnr," + B, "dhcp-mac=set:reddnr," + C]
          and "dhcp-option=tag:lan,tag:reddnr,162," in kept and "rednodnr" not in kept, kept)
    check("a LAN sent elsewhere with nobody kept: no option line at all",
          run("lan", dnsfilter_enable_x=1, dnsfilter_mode=CUSTOM, dnsfilter_rulelist=rules((A, CUSTOM))) == "")
    check("nothing is written while the server publishes nothing (no certificate, switches off)",
          run("lan", dnsfilter_enable_x=1, dnsfilter_mode=NONE, dnsfilter_rulelist=three, t_state="") == "")

    # guest / VLAN network: its own row decides, never the global mode
    g_ok = run("sdn", dnsfilter_enable_x=1, dnsfilter_mode=CUSTOM, t_row=ROUTER, dnsfilter_rulelist=three)
    g_no = run("sdn", dnsfilter_enable_x=1, dnsfilter_mode=ROUTER, t_row=CUSTOM, dnsfilter_rulelist=three)
    check("guest network served by its own row (global mode elsewhere): everybody but the device a rule sends elsewhere",
          [offered(g_ok, "br52", m) for m in (A, B, C, X)] == [False, True, True, True], g_ok)
    check("guest network whose row sends it elsewhere (global mode Router): only the devices a rule keeps on the router",
          [offered(g_no, "br52", m) for m in (A, B, C, X)] == [False, True, True, False], g_no)
    check("guest network row ignored while DNS Director is off",
          run("sdn", dnsfilter_enable_x=0, t_row=CUSTOM, dnsfilter_rulelist=three).startswith("dhcp-option=br52,162,"))

    # the rule text: shape first, normalised address out
    junk = dict(dnsfilter_enable_x=1, dnsfilter_mode=NONE,
                dnsfilter_rulelist="<j>zz:zz:zz:zz:zz:zz>8<s>a:b:c:d:e:f>8<t>aa:bb:cc:dd:ee:07xyz\nserver=/x/1.2.3.4>8<two>" + A + "<e>>8<m>" + B + ">")
    pj = run("pol", **junk); oj = run("lan", **junk)
    check("a rule whose address is not 17 characters of hex and colons is skipped on both sides (never 00:00:00:00:00:00)",
          [l for l in pj.split("\n") if l and not l.startswith("peer ")] == ["deny-mac AA:BB:CC:DD:EE:07"]
          and "00:00:00:00:00:00" not in pj + oj, (pj, oj))
    check("text after the sixth group never reaches the dnsmasq config (one tag line, the normalised address)",
          oj.split("\n")[0] == "dhcp-mac=set:rednodnr,AA:BB:CC:DD:EE:07" and "server=" not in oj and oj.count("\n") == 2, oj)

    # the digest: 0 without a DNS Director part, changes with it
    d = lambda **kv: run("dg", **kv).strip()
    d_off = d(dnsfilter_enable_x=0, dnsfilter_mode=CUSTOM, dnsfilter_rulelist=three)
    d_none = d(dnsfilter_enable_x=1, dnsfilter_mode=ROUTER, dnsfilter_rulelist="")
    d_one = d(dnsfilter_enable_x=1, dnsfilter_mode=NONE, dnsfilter_rulelist=three)
    d_chg = d(dnsfilter_enable_x=1, dnsfilter_mode=NONE, dnsfilter_rulelist=rules((A, ROUTER), (B, ROUTER), (C, NONE)))
    d_glob = d(dnsfilter_enable_x=1, dnsfilter_mode=CUSTOM, dnsfilter_rulelist="")
    check("digest: 0 while DNS Director has no part (off, or on with no rule and the LAN served)", d_off == d_none == "00000000", (d_off, d_none))
    check("digest: set by a rule, changed by a rule's mode, set by a global mode that sends the LAN elsewhere",
          len({d_off, d_one, d_chg, d_glob}) == 4 and "00000000" not in (d_one, d_chg, d_glob), (d_one, d_chg, d_glob))

shutil.rmtree(tmp, ignore_errors=True)
print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  " + f)
sys.exit(1 if fails else 0)
