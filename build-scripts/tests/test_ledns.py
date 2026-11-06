#!/usr/bin/env python3
"""Let's Encrypt via DNS (rc/reaper_ledns.c, WAN > DDNS certificate; owner 2026-11-05: "a certificate without DDNS").

WHY. The closed libletsencrypt validates over HTTP (acme.sh --standalone on WAN port 80) and only starts after a
successful DDNS update, so a router with no DDNS hostname, a blocked port 80 or a Warden country block never gets
a certificate. Reaper adds DNS validation through the provider's API (Cloudflare, deSEC, DuckDNS) with the stock
acme.sh, installed through the IMPORTED-certificate path. The properties that are easy to lose:
  - le_enable=2 must be set only once a certificate is on disk: prepare_cert_in_etc() falls back to self-signed and
    DELETES /jffs/.cert when le_enable=2 has no usable files;
  - the API token must never reach argv, a log line or the page;
  - the name and token reach acme.sh (a shell script that writes them into files): only strict values pass;
  - rc dispatches applets by argv[0] only, so the applet needs its symlink, and the cron line needs it too.

WHAT IT DOES. Static pins over rc / httpd / www / acme.sh / defaults, and a host compile of the two validators
against accepted and refused names and tokens (the page's regex must agree with them).
Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "reaper_ledns.c")):
    print("SKIP: no router source tree with rc/reaper_ledns.c (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

c = rd("rc/reaper_ledns.c")
code = re.sub(r"/\*.*?\*/", "", c, flags=re.S)

# ---- the helper
argvs = re.findall(r"char \*argv\[\] = \{(.*?)\};", code, re.S)
check("acme.sh runs with --issue and --install-cert, Let's Encrypt, DNS mode, a settle time, an EC key",
      any("--issue" in a and '"--dns"' in a and "--dnssleep" in a and '"letsencrypt"' in a and "ec-256" in a for a in argvs)
      and any("--install-cert" in a and "--fullchain-file" in a and "--key-file" in a and "--ecc" in a for a in argvs))
check("the token never reaches argv (it travels in the environment, then is unset)",
      not any("tok" in a for a in argvs) and "setenv(p->env, tok, 1);" in code and "unsetenv(p->env);" in code)
check("acme.sh has its own home, not the closed library's /jffs/.le",
      '#define LD_HOME\t\t"/jffs/.le_dns"' in c and code.count('"--home", LD_HOME, "--config-home", LD_HOME') == 2)
inst = re.search(r"static int ld_install\(void\)\n\{(.*?)\n\}\n", code, re.S)
ib = inst.group(1) if inst else ""
check("install: checked first, files copied BEFORE le_enable=2, then prepare_cert_in_etc and the reload flags",
      ib and ib.find("illegal_cert_and_key") < ib.find("ld_copy(LD_OUT_KEY, UPLOAD_KEY") < ib.find('nvram_set("le_enable", "2")')
      < ib.find("prepare_cert_in_etc()") and '"httpds_reload_cert", "2"' in ib and "rednsd_cert_changed();" in ib)
check("install: an end-entity certificate - the uploaded CA pair and what it signed are removed",
      all(("unlink(%s);" % k) in ib for k in ("UPLOAD_CACERT", "UPLOAD_CAKEY", "UPLOAD_GEN_CERT", "UPLOAD_GEN_KEY")))
check("install: nothing happens if the switch went off during the run, or the files are already in place",
      'if (!nvram_match("reaper_ledns_enable", "1"))\n\t\treturn 0;' in ib and "ld_same(LD_OUT_CERT, UPLOAD_CERT)" in ib)
run = re.search(r"static int ld_run\(void\)\n\{(.*?)\n\}\n", code, re.S)
rb = run.group(1) if run else ""
check("run: validates provider, name and token before anything else",
      rb.find("reaper_ledns_domain_ok(dom, prov)") < rb.find("reaper_secure_dir") and "reaper_ledns_token_ok(tok)" in rb)
check("run: one at a time (non-blocking flock), exit 2 (not due) is success, Warden holes closed after the run",
      "flock(lock, LOCK_EX | LOCK_NB)" in rb and "rc == 0 || rc == 2" in rb and rb.find("ld_unallow(ips, nip);") > rb.find("--issue"))
check("Warden: only addresses not already allowed are added, and only while the router-traffic filter is on",
      'ld_ipset("test", set, ip) == 0' in code and 'nvram_match("rwarden_self", "1")' in rb)
check("the page's error text is sanitised and never carries the token",
      "memset(p, '*', strlen(tok));" in code and 'strchr(" .,:;_/()\'+-", c)' in code)
stop = re.search(r"void stop_reaper_ledns\(void\)\n\{(.*?)\n\}\n", code, re.S)
check("switched off: the cron line goes and acme.sh's home (account, token copy, keys) is deleted; on: only the cron line",
      stop and 'eval("cru", "d", "reaper_ledns");' in stop.group(1) and 'eval("rm", "-rf", LD_HOME);' in stop.group(1)
      and stop.group(1).find('if (nvram_match("reaper_ledns_enable", "1"))') < stop.group(1).find("rm"))
check("the daily line runs the applet by its symlink", '"%u %u * * * /sbin/reaper_ledns run"' in code)
check("the body is gated on RTCONFIG_LETSENCRYPT with stubs otherwise",
      "#ifdef RTCONFIG_LETSENCRYPT" in c and "#else\t/* !RTCONFIG_LETSENCRYPT" in c)

# ---- wiring
mk, rcc, rch, svc = rd("rc/Makefile"), rd("rc/rc.c"), rd("rc/rc.h"), rd("rc/services.c")
check("rc: object, applet table entry and the argv[0] symlink",
      "OBJS += reaper_ledns.o" in mk and "ln -sf rc reaper_ledns" in mk and '{ "reaper_ledns",\t\treaper_ledns_main' in rcc
      and "extern int reaper_ledns_main(int argc, char *argv[]);" in rch)
check("rc: restart_reaper_ledns = stop + start-now; boot re-adds the cron line only",
      'strcmp(script, "reaper_ledns") == 0' in svc and "start_reaper_ledns(1);" in svc
      and "\tstart_letsencrypt();\n\tstart_reaper_ledns(0);" in svc)
am = rd("acme.sh/Makefile")
check("acme.sh: the three provider scripts are installed beside dns_asusapi.sh",
      "dnsapi/dns_cf.sh dnsapi/dns_desec.sh dnsapi/dns_duckdns.sh $(INSTALLDIR)/usr/sbin/dnsapi/" in am)
df = re.sub(r"/\*.*?\*/", "", rd("shared/defaults.c"), flags=re.S)
dv = lambda k: re.findall(r'\{\s*"%s"\s*,\s*"([^"]*)"' % k, df)
check("defaults: off, Cloudflare preselected, nothing else set",
      dv("reaper_ledns_enable") == ["0"] and dv("reaper_ledns_provider") == ["cf"]
      and all(dv(k) == [""] for k in ("reaper_ledns_domain", "reaper_ledns_token", "reaper_ledns_state", "reaper_ledns_err", "reaper_ledns_when")))
web = rd("httpd/web.c")
check("settings file: the switch, provider, name and token travel; the token gets the token check; an import restarts it",
      '{ "cert",   "reaper_ledns_token", 201 }' in web and '|| !strcmp(nv, "reaper_ledns_token")) {' in web
      and 'RCFG_SVC(t & RCFG_T_CERT, "restart_reaper_ledns");' in web)

# ---- the page
pg = rd("www/Reaper_DDNS.asp")
check("page: the choice exists and posts the four keys", '<option value="3"><#RDDN_42#></option>' in pg
      and all(re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % k, pg[pg.rfind("<script>"):]) for k in ("reaper_ledns_enable", "reaper_ledns_provider", "reaper_ledns_domain", "reaper_ledns_token"))
      and 'name="reaper_ledns_' not in pg)   # Q-C1-11 (2026-11-05): rp.changed creates the inputs at Apply
check("page: the token is never read into the page (only whether one is saved)",
      not re.search(r'nvram_(get|char_to_ascii)\([^)]*reaper_ledns_token', pg) and 'nvram_match("reaper_ledns_token", "", "0")' in pg
      and "reaper_ledns_token: ''" in pg)
check("page: the DNS choice never posts le_enable=2 itself (rc does, once the files exist)",
      "c.le_enable = '2'" not in pg and "if (NV.le_enable === '1') c.le_enable = '0';" in pg)
check("page: Apply runs restart_reaper_ledns; the request state is polled; the stock DDNS apply hook exists",
      "if (ld) S.push('restart_reaper_ledns');" in pg and "nvram_get%28reaper_ledns_state%29" in pg
      and "window.checkDDNSReturnCode = function(){};" in pg)
dicts = [f for f in os.listdir(os.path.join(SRC, "www")) if re.fullmatch(r"[A-Z]{2}\.dict", f)]
miss = [d for d in dicts if any(("\n%s=" % k) not in rd("www/" + d) for k in ["RDDN_%02d" % n for n in range(42, 56)])]
check("every language pack carries RDDN_42..RDDN_55", not miss and len(dicts) >= 25, miss)

# ---- the validators, compiled on the host; the page's regex agrees
GOOD_D = [("router.example.com", "cf"), ("a-b.dedyn.io", "desec"), ("me.duckdns.org", "duckdns"), ("x1.y2.co", "cf")]
BAD_D = [("Router.example.com", "cf"), ("-a.example.com", "cf"), ("a-.example.com", "cf"), ("example", "cf"), ("a..b.com", "cf"),
         ("a.b.com.", "cf"), ("me.example.com", "duckdns"), ("duckdns.org", "duckdns"), ("a b.com", "cf"), ("a;b.com", "cf"),
         ("x" * 64 + ".com", "cf"), ("ab.c$", "cf"), ("a.b", "cf")]
GOOD_T = ["abcdEFGH1234", "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "tok_en.value-1"]
BAD_T = ["short", "has space here", "quote'inside", "dollar$sign1", "x" * 201, "back`tick12"]
js_d = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
js_t = re.compile(r"^[A-Za-z0-9._-]{8,200}$")
check("page regex: the accepted names pass", all(js_d.match(d) and (p != "duckdns" or d.endswith(".duckdns.org")) for d, p in GOOD_D))
check("page regex: the refused names fail", not any(js_d.match(d) and (p != "duckdns" or d.endswith(".duckdns.org")) for d, p in BAD_D),
      [d for d, p in BAD_D if js_d.match(d) and (p != "duckdns" or d.endswith(".duckdns.org"))])
check("page regex: tokens", all(js_t.match(t) for t in GOOD_T) and not any(js_t.match(t) for t in BAD_T))
CC = shutil.which("gcc") or shutil.which("cc")
fd = re.search(r"\nint reaper_ledns_domain_ok\(.*?\n\}\n", c, re.S)
ft = re.search(r"\nint reaper_ledns_token_ok\(.*?\n\}\n", c, re.S)
check("the validators lift", fd and ft)
if CC and fd and ft:
    w = tempfile.mkdtemp(prefix="ledns_")
    try:
        cases = "".join('  r |= (reaper_ledns_domain_ok("%s", "%s") != %d) << 0; if (r) { printf("D %s\\n"); r = 0; bad++; }\n' % (d, p, 1, d) for d, p in GOOD_D)
        cases += "".join('  r |= (reaper_ledns_domain_ok("%s", "%s") != %d); if (r) { printf("D %s\\n"); r = 0; bad++; }\n' % (d.replace('"', '\\"'), p, 0, d) for d, p in BAD_D)
        cases += "".join('  r |= (reaper_ledns_token_ok("%s") != 1); if (r) { printf("T %s\\n"); r = 0; bad++; }\n' % (t, t) for t in GOOD_T)
        cases += "".join('  r |= (reaper_ledns_token_ok("%s") != 0); if (r) { printf("T %s\\n"); r = 0; bad++; }\n' % (t.replace("'", "\\'"), t[:20]) for t in BAD_T)
        prog = "#include <stdio.h>\n#include <string.h>\n#include <ctype.h>\n" + fd.group(0) + ft.group(0) + \
               "int main(void){ int r = 0, bad = 0;\n" + cases + "  return bad != 0; }\n"
        open(os.path.join(w, "t.c"), "w").write(prog)
        cp = subprocess.run([CC, "-Wall", "-Werror", "-o", os.path.join(w, "t"), os.path.join(w, "t.c")], capture_output=True, text=True)
        check("host: the validators compile cleanly (-Wall -Werror)", cp.returncode == 0, cp.stderr)
        if cp.returncode == 0:
            rr = subprocess.run([os.path.join(w, "t")], capture_output=True, text=True)
            check("host: every accepted value passes and every refused one fails", rr.returncode == 0, rr.stdout)
    finally:
        shutil.rmtree(w, ignore_errors=True)
else:
    print("note: no C compiler - the host validator run is skipped")

print("\n%d failure(s)" % len(fails))
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
