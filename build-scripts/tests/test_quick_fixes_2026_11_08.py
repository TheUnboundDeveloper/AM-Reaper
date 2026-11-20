#!/usr/bin/env python3
"""Four backlog items fixed together on 2026-11-08 (field RT-BE88U + owner requests).

WHY.
- Custom DDNS + the built-in Let's Encrypt never issued a certificate: restart_ddns_le sets le_rc_notify and restarts
  DDNS, but only the inadyn success hook (ddns_updated) acted on it. A Custom ddns-start script reports through
  ddns_custom_updated, which recorded success and left the request pending for ever.
- A WireGuard .conf without its keys was imported anyway: read_wgc_config_file resets every wgcN_ setting first, so
  the instance was left with an empty or broken key and no word why.
- The DDNS page said nothing when Custom was chosen and /jffs/scripts/ddns-start was missing (the tester had saved it
  as ddns-start.sh), nor that an HTTP-only web interface never serves the certificate it was asking for.
- The Storage page re-flowed when the firewall-log row's size changed: its retention text sat in the nowrap size cell.

WHAT IT DOES. Pins the shared Let's Encrypt helper and both callers; compiles httpd's .conf key check on the build
host and runs it, and the page's JavaScript copy (under node, when present), over the same set of files, which must
agree; compiles the DDNS script probe against a scratch folder; pins the page wiring; checks every language pack.
"""
import glob, json, os, re, shutil, subprocess, sys, tempfile

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

svc, web = rd("rc/services.c"), rd("httpd/web.c")
vpn, ddns, sto = rd("www/Reaper_VPNClient.asp"), rd("www/Reaper_DDNS.asp"), rd("www/Reaper_Storage.asp")

# ---------------------------------------------------------------- Let's Encrypt on the Custom DDNS path
check("one le_rc_notify consumer: the shared helper", svc.count('nvram_match("le_rc_notify", "1")') == 1
      and "static void\nddns_le_rc_notify(void)\n{\n#ifdef RTCONFIG_LETSENCRYPT\n" in svc)
h = func(svc, "static void\nddns_le_rc_notify(void)") if "ddns_le_rc_notify(void)" in svc else ""
check("the helper keeps the whole block: restart, reload flags, Encrypted DNS",
      all(x in h for x in ('nvram_set("le_rc_notify", "0");', "stop_letsencrypt();", "start_letsencrypt();",
                            'nvram_set("httpds_reload_cert", "2");', "rednsd_cert_changed();", 'nvram_set("httpds6_reload_cert", "2");')))
u = func(svc, "int\nddns_updated_main(int argc, char *argv[])")
check("ddns_updated (inadyn) calls it", "\tddns_le_rc_notify();\n" in u and "le_rc_notify\", \"1\"" not in u)
cu = func(svc, "int\nddns_custom_updated_main(int argc, char *argv[])")
ok_branch = cu[:cu.find("} else {")]
check("ddns_custom_updated calls it on success only", "ddns_le_rc_notify();" in ok_branch and "ddns_le_rc_notify();" not in cu[cu.find("} else {"):])
check("the helper is defined before both callers", 0 < svc.index("ddns_le_rc_notify(void)\n{") < svc.index("int\nddns_updated_main("))

# ---------------------------------------------------------------- WireGuard .conf key check: httpd + page
K1 = "yAnz5TF+lXXJte14tji3zlMNq+hd2rYUIgJBgB3fBmk="
K2 = "xTIBA5rboUvnH4htodjb6e697QjLERt1NAB4mZqp8Dg="
CASES = [
    ("valid", "[Interface]\nPrivateKey = %s\nAddress = 10.8.0.2/32\n\n[Peer]\nPublicKey = %s\nEndpoint = 192.0.2.1:51820\n" % (K1, K2), 0),
    ("valid CRLF, no spaces", "[Interface]\r\nPrivateKey=%s\r\n[Peer]\r\nPublicKey=%s\r\n" % (K1, K2), 0),
    ("no PrivateKey", "[Interface]\nAddress = 10.8.0.2/32\n[Peer]\nPublicKey = %s\n" % K2, 1),
    ("no PublicKey", "[Interface]\nPrivateKey = %s\n[Peer]\nEndpoint = 192.0.2.1:51820\n" % K1, 2),
    ("empty file", "", 3),
    ("a key one character short", "[Interface]\nPrivateKey = %s\n[Peer]\nPublicKey = %s\n" % (K1[1:], K2), 1),
    ("a key with a bad character", "[Interface]\nPrivateKey = %s\n[Peer]\nPublicKey = %s\n" % (K1, "*" + K2[1:]), 2),
    ("PublicKey under [Interface] only", "[Interface]\nPrivateKey = %s\nPublicKey = %s\n" % (K1, K2), 2),
    ("an indented key (the importer reads column 0)", "[Interface]\n  PrivateKey = %s\n[Peer]\nPublicKey = %s\n" % (K1, K2), 1),
    ("a longer name is not the key", "[Interface]\nPrivateKeyFile = %s\n[Peer]\nPublicKey = %s\n" % (K1, K2), 1),
    ("an empty value", "[Interface]\nPrivateKey =\n[Peer]\nPublicKey = %s\n" % K2, 1),
    ("lower-case section names", "[interface]\nPrivateKey = %s\n[peer]\nPublicKey = %s\n" % (K1, K2), 0),
]
cgi = func(web, "static void\ndo_upload_wgc_config_cgi(char *url, FILE *stream)")
check("httpd checks the keys before read_wgc_config_file resets the instance",
      0 < cgi.find("(kb = reaper_wgc_conf_keys(WGC_CONFIG_FILE)) != 0") < cgi.find("read_wgc_config_file(WGC_CONFIG_FILE, unit)")
      and 'snprintf(st, sizeof(st), "keys%d", kb);' in cgi and 'nvram_set("wgc_upload_state", st);' in cgi
      and "else if (ret == 0)" in cgi)
d = tempfile.mkdtemp(prefix="q6_")
try:
    for i, (_, body, _) in enumerate(CASES):
        open(os.path.join(d, "c%d.conf" % i), "w", newline="").write(body)
    cres = None
    if shutil.which("gcc"):
        c = "\n".join(["#include <stdio.h>", "#include <string.h>", "#include <strings.h>", "#include <ctype.h>",
                       func(web, "static int\nreaper_wgc_key_ok(const char *v)"),
                       func(web, "static int\nreaper_wgc_conf_keys(const char *path)"),
                       "int main(int c, char **v){ int i; for (i = 1; i < c; i++) printf(\"%d\\n\", reaper_wgc_conf_keys(v[i])); return 0; }"])
        open(d + "/k.c", "w").write(c)
        r = subprocess.run(["gcc", "-Wall", "-Werror", "-o", d + "/k", d + "/k.c"], capture_output=True, text=True)
        check("httpd's key check compiles on the build host (-Wall -Werror)", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            o = subprocess.run([d + "/k"] + [d + "/c%d.conf" % i for i in range(len(CASES))] + [d + "/absent.conf"],
                               capture_output=True, text=True).stdout.split()
            cres = [int(x) for x in o[:len(CASES)]]
            for (name, _, want), got in zip(CASES, cres):
                check("httpd: %s -> %d" % (name, want), got == want, got)
            check("httpd: a file it cannot open -> refused (3)", o[-1] == "3", o[-1:])
    else:
        check("gcc available to compile httpd's key check", False)
    m = re.search(r"function isWgKey\(s\)\{.*?\n", vpn)
    js_funcs = (m.group(0) if m else "") + func(vpn, "function wgKeysMissing(text){").rstrip()
    node = shutil.which("node")
    if node:
        js = js_funcs + "\nvar fs = require('fs'), out = [];\nfor (var i = 0; i < %d; i++) out.push(wgKeysMissing(fs.readFileSync(%s + '/c' + i + '.conf', 'utf8')));\nconsole.log(JSON.stringify(out));\n" % (len(CASES), json.dumps(d))
        open(d + "/k.js", "w").write(js)
        r = subprocess.run([node, d + "/k.js"], capture_output=True, text=True)
        jres = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
        check("the page's check runs under node", jres is not None, r.stderr[:300])
        if jres is not None:
            for (name, _, want), got in zip(CASES, jres):
                check("page: %s -> %d" % (name, want), got == want, got)
            if cres is not None:
                check("page and httpd agree on every file", jres == cres, (jres, cres))
    else:
        print("note: node not found - the page's check is pinned by text only")
finally:
    shutil.rmtree(d, ignore_errors=True)
wi = func(vpn, "function wgImport(){")
ws = func(vpn, "function wgSend(f){")
check("page: the file is read and checked before anything is sent; the confirm and the upload follow",
      "new FileReader()" in wi and "wgKeysMissing(rd.result)" in wi and "wgSend(f)" in wi and "upload_wgc_config.cgi" not in wi
      and "confirm(`<#RVCL_158#>`)" in ws and "/upload_wgc_config.cgi" in ws)
check("page: httpd's refusal (keys1..3) is shown with what is missing",
      "if (/^keys[123]$/.test(v)){ impMsg('wg_impmsg', wgKeysMsg(+v.charAt(4)));" in ws
      and ws.index("/^keys[123]$/") < ws.index("if (v !== '0')"))
check("page: the message names the config lines and what a key is",
      "miss.push('[Interface] PrivateKey')" in vpn and "miss.push('[Peer] PublicKey')" in vpn
      and "return `<#RVCL_164#>` + ' ' + miss.join(', ') + '. ' + `<#RVCL_137#>`;" in vpn)

# ---------------------------------------------------------------- DDNS page: the Custom script, HTTP only
check("httpd: reaper_ddns_script registered next to httpd_cert_info (same RTCONFIG_HTTPS block)",
      '\t{ "httpd_cert_info", ej_httpd_cert_info},\n\t{ "reaper_ddns_script", ej_reaper_ddns_script},\n' in web)
ej = func(web, "static int\nej_reaper_ddns_script(int eid, webs_t wp, int argc, char **argv)")
d = tempfile.mkdtemp(prefix="q6d_")
try:
    if shutil.which("gcc"):
        S = os.path.join(d, "scripts")
        c = "\n".join(["#include <stdio.h>", "#include <string.h>", "#include <strings.h>", "#include <dirent.h>", "#include <sys/stat.h>",
                       "typedef FILE *webs_t;", "#define websWrite fprintf",
                       "size_t strlcpy(char *d, const char *s, size_t n){ size_t l = strlen(s); if (n) { size_t k = l < n - 1 ? l : n - 1; memcpy(d, s, k); d[k] = 0; } return l; }",
                       ej.replace('"/jffs/scripts/ddns-start"', json.dumps(S + "/ddns-start")).replace('"/jffs/scripts"', json.dumps(S)),
                       "int main(void){ ej_reaper_ddns_script(0, stdout, 0, NULL); return 0; }"])
        open(d + "/e.c", "w").write(c)
        r = subprocess.run(["gcc", "-Wall", "-o", d + "/e", d + "/e.c"], capture_output=True, text=True)
        check("the DDNS script probe compiles on the build host", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            probe = lambda: json.loads(subprocess.run([d + "/e"], capture_output=True, text=True).stdout)
            os.makedirs(S)
            check("probe: no script -> s 0, nothing near", probe() == {"s": 0, "near": ""}, probe())
            open(S + "/ddns-start.sh.bak", "w").write("#\n")
            check("probe: only a backup -> not offered", probe() == {"s": 0, "near": ""}, probe())
            open(S + "/ddns-start.sh", "w").write("#\n")
            check("probe: the field case -> s 0, near ddns-start.sh", probe() == {"s": 0, "near": "ddns-start.sh"}, probe())
            open(S + "/ddns-start", "w").write("#\n"); os.chmod(S + "/ddns-start", 0o644)
            check("probe: there but not executable -> s 1", probe()["s"] == 1, probe())
            os.chmod(S + "/ddns-start", 0o755)
            check("probe: ready -> s 2", probe() == {"s": 2, "near": ""}, probe())
    else:
        check("gcc available to compile the DDNS script probe", False)
finally:
    shutil.rmtree(d, ignore_errors=True)
check("probe: a near name holds only [A-Za-z0-9._-] (it is printed into the page)",
      '"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")] != \'\\0\')' in ej)
check("DDNS page: reads the probe and names a missing / non-executable script on the Custom note",
      "var DSCRIPT = {}; try { DSCRIPT = [<% reaper_ddns_script(); %>][0] || {}; } catch (e) {}" in ddns
      and "if (DSCRIPT.s === 0) return ' ' + `<#RDDN_56#>` + (DSCRIPT.near ? ' ' + `<#RDDN_57#>` + ' ' + rp.esc(DSCRIPT.near) : '');" in ddns
      and "if (DSCRIPT.s === 1) return ' ' + `<#RDDN_58#>`;" in ddns
      and "(JFFS_SCRIPTS ? '' : ' ' + `<#RDDN_26#>`) + ddnsScriptNote()) : '');" in ddns)
cs = func(ddns, "function certSync(){")
check("DDNS page: the certificate hint says when the web interface is HTTP only",
      "if (HTTP_ENABLE === '0') h += ' ' + `<#RDDN_59#>`;" in cs and cs.index("RDDN_59") < cs.index("q('h_cert').textContent = h;"))

# ---------------------------------------------------------------- Storage page: the firewall-log row
check("Storage: the firewall-log retention is in the description, not the size cell",
      "{k:'fwlog', name:`<#RDST_113#>`, write:`<#RDST_114#>` + '; ' + `<#RDST_115#>`, cap:'', usbonly:1}," in sto
      and "cap += ' - ' + `<#RDST_115#>`" not in sto and sto.count("RDST_115") == 1)
check("Storage: the size column has a minimum width (a size arriving later cannot move the columns)",
      "td.dscap{color:var(--steel);white-space:nowrap;min-width:8.5em}" in sto)

# ---------------------------------------------------------------- packs
packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if not p.endswith("temp.dict"))
miss = []
for p in packs:
    t = open(p, encoding="utf-8").read()
    kv = dict(re.findall(r"^(R[A-Z]+_\d+)=(.*)$", t, re.M))
    for k in ("RDDN_56", "RDDN_57", "RDDN_58", "RDDN_59", "RVCL_164"):
        if not kv.get(k): miss.append("%s:%s" % (os.path.basename(p), k))
    if kv.get("RDDN_59") and kv.get("RADM_09") and kv["RADM_09"] not in kv["RDDN_59"]:
        miss.append("%s: RDDN_59 does not name its RADM_09 (%s)" % (os.path.basename(p), kv["RADM_09"]))
    if kv.get("RDDN_56") and "/jffs/scripts/ddns-start" not in kv["RDDN_56"]:
        miss.append("%s: RDDN_56 lost the path" % os.path.basename(p))
    if kv.get("RDDN_58") and "chmod +x /jffs/scripts/ddns-start" not in kv["RDDN_58"]:
        miss.append("%s: RDDN_58 lost the command" % os.path.basename(p))
check("every language pack carries RDDN_56..59 and RVCL_164 (RDDN_59 names its own System label)",
      not miss and len(packs) >= 25, miss)

print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
