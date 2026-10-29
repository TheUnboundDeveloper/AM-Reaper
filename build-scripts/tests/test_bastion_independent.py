#!/usr/bin/env python3
"""The four Bastion tools run independently of each other (owner, 2026-10-26).

WHY. Bastion holds four separate tools - Warden (addresses), Dreadwatch (threat domains), Wallguard (ads and
trackers) and Encrypted DNS. Wallguard and Encrypted DNS were already separate (their own switches, services and
dnsmasq lines). Dreadwatch was not: it rode Warden's start, list updater, fold job and include gate, so with Warden
off nothing it listed was blocked and its counters were wiped, and the page said "Warden must be on".

WHAT IT DOES. Source checks: start_rwarden returns only when BOTH switches are off; Warden's chains, stats and fold
job are generated only with Warden on; the shared updater (rw_gen_update(warden)) skips Warden's feeds, countries,
sets and cache when Warden is off and keeps the threat-domain block; the 15-minute checkpoint and the stop-time bank
use dns.sh with Dreadwatch alone (same root-owned 0700 rule); the dnsmasq include, the page's "enable", the httpd
fallback, the counter reset and the diag finding key on rwarden_dns alone; the Dreadwatch page has no Warden banner
and no Warden condition; RDWT_02 is gone and RDWT_40 names Dreadwatch in all 25 packs; Wallguard and Encrypted DNS
still read no other tool's switch.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwarden.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

rw = rd("rc", "rwarden.c")
st = rw[rw.index("void start_rwarden(void)"):]
st = st[:st.index("\n}\n")]
check("start_rwarden returns early only when Warden AND Dreadwatch are off",
      'warden = nvram_match("rwarden_enable", "1");\n\tif (!warden && !nvram_match("rwarden_dns", "1"))\n\t\treturn;' in st
      and 'if (!nvram_match("rwarden_enable", "1"))\n\t\treturn;' not in st)
wb = st[st.index("\tif (warden) {\n"):st.index("\trw_gen_update(warden);")]
check("Warden's own pieces (front chains, apply, stats, fold) are generated only with Warden on",
      all(x in wb for x in ("reaper_hook_gen();", "rw_gen_apply();", "rw_gen_stats();", "rw_gen_fold();")))
check("the shared updater and the hit collector are generated for either tool",
      "\trw_gen_update(warden);\n\trw_gen_dns();" in st and "chmod(RW_UPDATE, 0700);" in st)
check("Warden's apply runs only with Warden on",
      "if (warden && !f_exists(REAPER_FW_BUILT_MARK))" in st and 'else if (warden && (!reaper_script_ok(RW_APPLY) || system("sh " RW_APPLY) != 0))' in st)
check("the 15-minute checkpoint banks Dreadwatch's hits through dns.sh when Warden is off",
      'eval("cru", "a", "rwarden_ck", warden ? "*/15 * * * * sh " RW_FOLD : "*/15 * * * * sh " RW_DNSSH " fold");' in st)
check("the list schedule is set for either tool", 'eval("cru", "a", "rwarden", line);' in st)

up = rw[rw.index("static void rw_gen_update(int warden)"):rw.index("static void rw_gen_fold(void)")]
i_f6 = up.index("rw_f6() {"); i_go = up.index("goto domains;"); i_set = up.index('"ipset create rw_threat hash:net')
i_dom = up.index("\ndomains:\n"); i_geo = up.index("rwarden_geo"); i_tail = up.index("\ntail:\n")
check("update.sh: without Warden it jumps from the shared fetch helpers straight to the threat-domain block",
      i_f6 < i_go < i_set < i_geo < i_dom and up.index('"# ---- threat domains (2026-10-19)') > i_dom)
check("update.sh: without Warden the set cache, rwarden_lastupd and the flow-cache flush are skipped; the dnsmasq restart stays",
      'if (!warden) {\n\t\tfprintf(f, "rm -f $TMP $TMP.rst\\n");\n\t\tgoto tail;\n\t}' in up
      and up.index("goto tail;") < up.index("rwarden_lastupd=") < up.index('fprintf(f, "fc flush 2>/dev/null\\n");') < i_tail
      < up.index("DNS_CHANGED\\\" = 1 ] && service restart_dnsmasq"))
check("update.sh: the threat-domain block still gates itself on rwarden_dns", "\"if [ \\\"$(_nv rwarden_dns)\\\" = 1 ]; then\\n\"" in up)

cf = rw[rw.index("const char *reaper_warden_dns_conf(void)"):rw.index("static void rw_dns_sync(void)")]
check("dnsmasq include: Dreadwatch's own switch only", 'if (!nvram_match("rwarden_dns", "1"))' in cf and "rwarden_enable" not in cf)
check("page JSON: enable = Dreadwatch's switch", '"  EN=0; [ \\"$(_nv rwarden_dns)\\" = 1 ] && EN=1\\n"' in rw)
sp = rw[rw.index("void stop_rwarden(void)"):rw.index("static int rw_seed_has(")]
check("stop: Dreadwatch alone banks through dns.sh fold, root-owned 0700 only",
      'const char *sh = warden ? RW_FOLD : nvram_match("rwarden_dns", "1") ? RW_DNSSH : NULL;' in sp
      and 'system(warden ? "sh " RW_FOLD " 2>/dev/null" : "sh " RW_DNSSH " fold 2>/dev/null");' in sp)
check("stop: Dreadwatch's counters reset on its own switch only (turning Warden off keeps them)",
      'if (!nvram_match("rwarden_dns", "1")) {\n\t\tunlink(RW_DNS_CTRS);' in sp)

web = rd("httpd", "web.c")
check("httpd: the dns_status fallback reports Dreadwatch's switch",
      'nvram_match("rwarden_dns", "1") ? 1 : 0);' in web and 'nvram_match("rwarden_enable", "1") && nvram_match("rwarden_dns", "1")' not in web)
dg = rd("others", "reaper_diag")
check("diag: the empty-list finding needs only Dreadwatch on",
      '[ "$_td" = 1 ] && [ "$_tdn" = 0 ] && finding WARN "threat domains are switched on but no list is loaded' in dg)

pg = rd("www", "Reaper_Dreadwatch.asp")
check("Dreadwatch page: no Warden banner, no Warden condition",
      "wardenoff" not in pg and "NV.warden" not in pg and "RDWT_02" not in pg and "if(updateNow || (dnsOn && changed)){" in pg)
www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(www) if f.endswith(".dict") and f != "temp.dict")
bad = []
for f in packs:
    t = open(os.path.join(www, f), encoding="utf-8", errors="replace").read()
    m = re.search(r"(?m)^RDWT_40=(.*)$", t)
    if re.search(r"(?m)^RDWT_02=", t) or not m or "Dreadwatch" not in m.group(1) or "Warden" in m.group(1):
        bad.append(f)
check("all 25 packs: RDWT_02 gone, RDWT_40 names Dreadwatch", len(packs) == 25 and not bad, bad)

wg = rd("rc", "wallguard.c"); ed = rd("rc", "encdns.c")
check("Wallguard's and Encrypted DNS's starts read no other Bastion switch",
      not re.search(r'nvram_\w+\("(rwarden_enable|rwarden_dns|reaper_dot_srv|reaper_doh_block)"', wg)
      and not re.search(r'nvram_\w+\("(rwarden_enable|rwarden_dns|wallguard_enable)"', ed))
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
