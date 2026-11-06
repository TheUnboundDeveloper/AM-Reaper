#!/usr/bin/env python3
"""Wallguard Advanced rules (2026-11-06, owner: "a custom box that would accept all of the text file ... fully switch
over to the router and off AdGuard").

The box takes an AdGuard Home rule list as it is. `wallguardc adv` compiles it (wallguard/wallguardc.c) into
SH_DIR/adv, which every dnsmasq instance loads with dnsmasq/src/wallguard_adv.h. This test compiles the tree's own
wallguardc and the engine header on the host, runs the compiler on a fixture list, evaluates queries through the
engine's evaluator, and pins the wiring: the engine's order, the shell step, rc's name map, httpd's request and
settings-file key, the page and the language files.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] / REAPER_ROUTER_SRC).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "wallguard", "wallguardc.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
def rd(rel): return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

FIXTURE = r"""! a comment
# another comment
@@||vendor.example^$important
@@||social.example^$client=10.0.0.20,important
@@/(^|\.)video\.[a-z0-9-]+$/$client=10.0.0.20,important
@@||work.example^$client='Lab Laptop'
@@||168.192.in-addr.arpa^$dnsrewrite
||social.example^
/(^|\.)video\.[a-z0-9-]+$/
||tv-ads.example^$important
||in-addr.arpa^$dnstype=PTR,dnsrewrite=NOERROR
||wpad.example^$dnsrewrite=0.0.0.0
||trk-*-*.cdn.example^
||meter.
||*.metrics.example^
|exact.example|
||tagged.example^$ctag=tv
||notes.example^ # trailing comment
||lst-*.vendor.example^
@@||lst-ok.vendor.example^$important
||router-needs.example^
||bad^$badfilter
||x.example^$dnsrewrite=1.2.3.4
@@||ghost.example^$client='No Such Device'
""" + (  # 2026-11-06: invisible characters - a rule is ASCII; a leading BOM is a file artifact; comments may be UTF-8
    "||zw​sp.example^\n"
    "/ab​c/\n"
    "﻿||bomrule.example^\n"
    "﻿# a comment after a BOM\n"
    "# Hannah’s phone – a UTF-8 comment\n")
CASES = [  # name, qtype, ip, mac, want (0 none 1 allow 2 block), important, resp
    ("social.example", 1, "10.0.0.20", None, 1, 1, 0),
    ("cdn.social.example", 28, "10.0.0.20", None, 1, 1, 0),
    ("social.example", 1, "10.0.0.5", None, 2, 0, 0),
    ("v1.video.tv", 1, "10.0.0.20", None, 1, 1, 0),
    ("v1.video.tv", 1, "10.0.0.5", None, 2, 0, 0),
    ("api.vendor.example", 1, "10.0.0.5", None, 1, 1, 0),
    ("tv-ads.example", 1, "10.0.0.5", None, 2, 1, 0),
    ("4.3.2.1.in-addr.arpa", 12, "10.0.0.5", None, 2, 0, 1),
    ("1.0.168.192.in-addr.arpa", 12, "10.0.0.5", None, 1, 0, 0),
    ("4.3.2.1.in-addr.arpa", 1, "10.0.0.5", None, 0, 0, 0),
    ("wpad.example", 1, "10.0.0.5", None, 2, 0, 4),
    ("trk-a-b.cdn.example", 1, "10.0.0.5", None, 2, 0, 0),
    ("meter.net", 1, "10.0.0.5", None, 2, 0, 0),
    ("a.metrics.example", 1, "10.0.0.5", None, 2, 0, 0),
    ("exact.example", 1, "10.0.0.5", None, 2, 0, 0),
    ("sub.exact.example", 1, "10.0.0.5", None, 0, 0, 0),
    ("tagged.example", 1, "10.0.0.7", "aa:bb:cc:dd:ee:02", 2, 0, 0),
    ("tagged.example", 1, "10.0.0.7", "aa:bb:cc:dd:ee:09", 0, 0, 0),
    ("work.example", 1, "10.0.0.8", "aa:bb:cc:dd:ee:01", 1, 0, 0),
    ("work.example", 1, "10.0.0.8", "aa:bb:cc:dd:ee:09", 0, 0, 0),
    ("notes.example", 1, "10.0.0.5", None, 2, 0, 0),
    ("lst-ok.vendor.example", 1, "10.0.0.5", None, 1, 1, 0),
    ("lst-no.vendor.example", 1, "10.0.0.5", None, 1, 1, 0),   # @@||vendor.example^$important covers it
    ("unrelated.example", 1, "10.0.0.5", None, 0, 0, 0),
]
HARNESS = r'''
#include "wallguard_adv.h"
int main(int argc, char **argv)
{
	struct wga A; FILE *f = fopen(argv[1], "r"); char line[512]; int fails = 0;
	memset(&A, 0, sizeof(A));
	if (wga_load(&A, f)) { printf("LOADFAIL\n"); return 2; }
	fclose(f);
	while (fgets(line, sizeof(line), stdin)) {
		char name[256], ip[64], mac[32]; int q, want, wimp, wresp, imp, resp, v; uint32_t ln;
		unsigned char a4[16]; uint8_t m[6]; struct wga_who w;
		if (sscanf(line, "%255s %d %63s %31s %d %d %d", name, &q, ip, mac, &want, &wimp, &wresp) != 7) continue;
		memset(&w, 0, sizeof(w));
		if (inet_pton(AF_INET, ip, a4) == 1) { w.family = AF_INET; w.addr = a4; }
		if (strcmp(mac, "-") && wga_mac_parse(mac, m)) w.mac = m;
		v = wga_eval(&A, name, q, &w, &imp, &resp, &ln);
		if (v != want || (want && (imp != wimp || resp != wresp))) { printf("BAD %s %d %s got %d/%d/%d\n", name, q, ip, v, imp, resp); fails++; }
	}
	wga_free(&A);
	printf("EVAL %d\n", fails);
	return 0;
}
'''

# ---- the wiring
eng = rd("dnsmasq/src/wallguard.c")
i_adv, i_tbl = eng.find("av = wga_eval(&sh.adv"), eng.find("r = wallguard_lookup_at(&sh.t.v, name, &bits, &listed);")
check("engine: Advanced rules are judged before the block table", 0 < i_adv < i_tbl, (i_adv, i_tbl))
check("engine: a plain block yields to the table's allows, an important one does not; Bypass/pause (bit 0) respected",
      "(mask & 1u) && (imp || !sh.t.ok || wallguard_lookup(&sh.t.v, name, &abits) != WALLGUARD_ALLOWED)" in eng)
check("engine: dnsmasq's own answers still win", "av == WGA_BLOCK && !wallguard_config_answer(name, qtype)" in eng)
check("engine: the file is reloaded on change and the MAC is looked up only when a rule needs it",
      "wallguard_adv_load();" in eng and "sh.adv.has_mac && client && find_mac(client, amac, 1, now) == 6" in eng)
check("engine: REFUSED / NXDOMAIN / NODATA / null answers", all(x in eng for x in (
      "setup_reply(header, 0, EDE_BLOCKED)", "setup_reply(header, F_NXDOMAIN, EDE_BLOCKED)", "setup_reply(header, F_NOERR, EDE_BLOCKED);")))
sh = rd("wallguard/wallguard.sh")
check("wallguard.sh compiles the box in every build (and drops it when the box is empty)",
      '"$SC" adv --in "$J/adv" --out "$D/adv" --stats "$D/adv.json" --clients "$D/clients" --safe "$D/safe"' in sh
      and 'rm -f "$D/adv" "$D/adv.json"' in sh)
rcw = rd("rc/wallguard.c")
check("rc writes the device/profile name map root-only, with the safe set",
      'reaper_write_changed(SH_DIR "/clients", b, strlen(b), 0600);' in rcw and "\tsh_write_clients();" in rcw)
check("rc: DHCP reservation names join the map (a reserved, offline device still resolves for $client=)",
      'nvram_safe_get("dhcp_staticlist")' in rcw and 'vstrsep(ent, ">", &mac, &ip, &dns, &nm) >= 4' in rcw)
web = rd("httpd/web.c")
check("httpd: its own request, base64url, 40,000 bytes, its own gate",
      'if (!strcmp(action, "adv")) {' in web and "#define SH_ADV_MAX 40000" in web and "if (!sh_adv_ok(txt, (size_t)n))" in web)
check("httpd: the settings file carries it through the same gate",
      '{ "wallguard", "wallguard_adv", SH_ADV_MAX + 1 },' in web and 'if (!strcmp(nv, "wallguard_adv"))' in web
      and 'else if (!strcmp(nv, "wallguard_adv")) f = SH_JFFS "/adv";' in web)
check("httpd: the page gets the text and the last build's report", '",\\"adv\\":"' in web and '",\\"adv_stats\\":"' in web)
pg = rd("www/Reaper_Wallguard.asp")
check("page: the box, its report (text only) and its own save request",
      'id="adv"' in pg and "shPost({action: 'adv', adv64: shB64(adv)}" in pg and "li.textContent = l.line" in pg
      and "o.adv = $('adv').value;" in pg)
check("page: ASCII only", all(ord(c) < 128 for c in pg))
check("page: invisible characters are removed (and odd spaces made plain) before saving, with a count",
      "\\u200B-\\u200D\\u2060\\uFEFF\\u00AD\\u200E\\u200F\\u202A-\\u202E\\u2066-\\u2069" in pg
      and "\\u00A0\\u2000-\\u200A\\u202F\\u205F\\u3000" in pg and "`<#RSHD_182#>`.replace('%1', cut)" in pg)
check("RSHD_182 in all 25 language files",
      all(re.search(r"^RSHD_182=.*%1", open(os.path.join(SRC, "www", d), encoding="utf-8").read(), re.M)
          for d in os.listdir(os.path.join(SRC, "www")) if d.endswith(".dict") and d != "temp.dict"))
dicts = sorted(f for f in os.listdir(os.path.join(SRC, "www")) if f.endswith(".dict") and f != "temp.dict")
have = [d for d in dicts if re.search(r"^RSHD_178=.+\n^RSHD_179=.+\n^RSHD_180=.*%1.*%2.*%3.*\n^RSHD_181=.+$",
        open(os.path.join(SRC, "www", d), encoding="utf-8").read(), re.M)]
check("RSHD_178..181 in all 25 language files, in order", len(dicts) == 25 and have == dicts, sorted(set(dicts) - set(have)))
check("the engine header has one copy (dnsmasq) and no stray second one", not os.path.exists(os.path.join(SRC, "wallguard", "wallguard_adv.h")))

# ---- compile and run
if not CC:
    print("note: no host compiler - the run was not done")
else:
    d = tempfile.mkdtemp()
    try:
        exe = os.path.join(d, "wallguardc")
        r = subprocess.run([CC, "-std=gnu99", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(SRC, "wallguard"),
                            "-o", exe, os.path.join(SRC, "wallguard", "wallguardc.c")], capture_output=True, text=True)
        check("wallguardc builds on the host with -Werror", r.returncode == 0, r.stderr[-400:])
        if r.returncode == 0:
            fx, cl, sf = (os.path.join(d, x) for x in ("rules.txt", "clients", "safe"))
            open(fx, "w", encoding="utf-8").write(FIXTURE)
            open(cl, "w").write("lab laptop\taa:bb:cc:dd:ee:01\nprofile:tv\taa:bb:cc:dd:ee:02\n")
            open(sf, "w").write("router-needs.example\n")
            out, st = os.path.join(d, "adv"), os.path.join(d, "adv.json")
            r = subprocess.run([exe, "adv", "--in", fx, "--out", out, "--stats", st, "--clients", cl, "--safe", sf], capture_output=True, text=True)
            check("wallguardc adv runs", r.returncode == 0, r.stderr)
            j = json.load(open(st)) if os.path.exists(st) else {}
            why = {l["line"]: l["why"] for l in j.get("lines", [])}
            src_ln = {l.strip(): i + 1 for i, l in enumerate(FIXTURE.splitlines())}
            check("report: badfilter, a rewrite to an address and a name the router needs are left out, with reasons",
                  "not supported" in why.get(src_ln["||bad^$badfilter"], "") and "rewrites table" in why.get(src_ln["||x.example^$dnsrewrite=1.2.3.4"], "")
                  and "router itself needs" in why.get(src_ln["||router-needs.example^"], ""), why)
            check("report: an unknown device is a note and the rule is left out",
                  "no such device" in why.get(src_ln["@@||ghost.example^$client='No Such Device'"], ""), why)
            check("counts", j.get("skipped") == 5 and j.get("warnings") == 1 and j.get("regex") == 2 and j.get("total") == 25, j)
            zw = [l for l in j.get("lines", []) if "U+200B" in l.get("why", "")]
            check("invisible characters: both rules left out, the character named and shown where it is",
                  len(zw) == 2 and all("zero-width space" in l["why"] and "<U+200B>" in l["text"] for l in zw), zw)
            check("a leading BOM is dropped: the rule after it is kept", "bomrule.example" in open(out).read())
            check("report text carries no line end (no stray '?' after each shown rule)",
                  bool(j.get("lines")) and not [l for l in j["lines"] if l.get("text", "").endswith("?")], j.get("lines"))
            hx = os.path.join(d, "h.c"); he = os.path.join(d, "h")
            open(hx, "w").write(HARNESS)
            r = subprocess.run([CC, "-std=gnu99", "-O2", "-Wall", "-Werror", "-I", os.path.join(SRC, "dnsmasq", "src"), "-o", he, hx],
                               capture_output=True, text=True)
            check("the engine header builds on the host", r.returncode == 0, r.stderr[-400:])
            if r.returncode == 0:
                inp = "".join("%s %d %s %s %d %d %d\n" % (n, q, ip, m or "-", w, i, rs) for n, q, ip, m, w, i, rs in CASES)
                r = subprocess.run([he, out], input=inp, capture_output=True, text=True)
                check("engine verdicts: %d cases (per-device allows, regex, typed sinkholes, globs, exact, profiles, names)" % len(CASES),
                      "EVAL 0" in r.stdout, r.stdout[-600:])
    finally:
        shutil.rmtree(d, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
