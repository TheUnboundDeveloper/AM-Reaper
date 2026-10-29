#!/usr/bin/env python3
"""Backups know every option (owner, 2026-10-27) and keep the DDNS hostname (field report, 2026-10-27).

WHY. The full .rbk carries every nvram value (the embedded router settings) and the whole /jffs, but the settings file
is a JSON allowlist (httpd/web.c rcfg_flags): on another model it is ALL that travels, and on the same model it is
what carries the /jffs stores. Wallguard (2026-10-21) and Dreadwatch's sources (2026-10-27) were never added, so a
settings restore brought Wallguard back switched on with no lists, rules or profiles. And rbk_make_cfg() copied
stock's "DDNS not transferred" step, blanking the hostname in both files - a no-ip name came back empty while its
login came back (Reaper has no ASUS DDNS since 2026-10-23, so every hostname is the operator's own).

WHAT IT DOES.
  - Coverage: every Reaper nvram key in shared/defaults.c (a Reaper prefix, or a defaults line whose comment marks
    it as Reaper's) is either carried by the settings file or named below as full-backup-only WITH a reason, or as
    a stock key whose default Reaper changed. A new option in neither list FAILS here - place it.
  - The table: sections contiguous (the export opens each once), every carried key exists, sources before their keys.
  - Round trip on the host: the region of web.c that holds the validators, the key store, rcfg_get and rcfg_put is
    compiled with stub nvram / files; router A's values are exported, router B (empty) imports them: nvram, the
    Warden list store, Wallguard's files and both key files come back byte for byte; a file router A never had is
    left out (router B keeps its own); bad values are refused and nothing is written.
  - DDNS: rbk_make_cfg no longer blanks ddns_hostname_x.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
web, defaults, page = rd("httpd/web.c"), rd("shared/defaults.c"), rd("www/Reaper_Backup.asp")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:700] if detail else ""))

# ---- the settings table
m = re.search(r"rcfg_flags\[\] = \{(.*?)\n\};", web, re.S)
check("web.c: the settings table is there", m)
rows = re.findall(r'\{\s*"([a-z]+)",\s*"([A-Za-z0-9_]+)",', m.group(1)) if m else []
sects = [s for s, _ in rows]
seen, contiguous = [], True
for s in sects:
    if seen and seen[-1] == s: continue
    if s in seen: contiguous = False
    seen.append(s)
check("the sections are contiguous (the export opens each once)", contiguous, seen)
carried = {n for _, n in rows}
idx = {n: i for i, (_, n) in enumerate(rows)}
check("sources come before their keys (keys are pruned against the sources just written)",
      idx.get("rwarden_dnssrc", 99) < idx.get("rwarden_dnskeys", -1) and idx.get("wallguard_lists", 99) < idx.get("wallguard_keys", -1))
# carried in the settings file's list part, not the flag table
LISTS = {"gk_rl", "reaper_pbr_rulelist", "reaper_fw_obj", "reaper_fw_grp", "reaper_fw_svc", "reaper_fw_zone",
         "reaper_fw_zpol", "reaper_fw_rules", "reaper_fw_edef", "reaper_fw_nat"}
# not nvram: a /jffs file or the Warden list store, named in the table
STORE = {"rwarden_ban", "rwarden_allow", "rwarden_dnsallow", "rwarden_dnssrc", "rwarden_dnskeys", "rdev_dhcp6",
         "rwatch_rules", "rlog_filter", "wallguard_lists", "wallguard_block", "wallguard_allow", "wallguard_profiles",
         "wallguard_assign", "wallguard_services", "wallguard_sched", "wallguard_safe", "wallguard_keys"}
FULL_ONLY = {   # in the full .rbk (all nvram + /jffs) only, on purpose
    "amas_bh_park": "AiMesh: this mesh's backhaul", "amas_chanfit": "AiMesh: this mesh's node channels",
    "firmware_check_hour": "spread per router (one shared minute would hit the manifest host at once)",
    "qos_cake_rtt": "QoS: extends the stock QoS settings (router settings only)", "qos_class_names": "QoS: as above",
    "qos_dscp_trust": "QoS: as above", "qos_ipolicer": "QoS: as above", "qos_minrates": "QoS: as above",
    "qos_pshaper": "QoS: as above", "qos_sched": "QoS: as above",
    "reaper_fw_active": "state", "reaper_fw_armed": "state", "reaper_fw_err": "state",
    "reaper_pbr_active": "state", "reaper_pbr_armed": "state", "reaper_pbr_err": "state",
    "reaper_fwsig_override": "one-shot confirm, cleared by its consumer", "reaper_upg_fail": "state",
    "rwarden_lastupd": "state",
    "reaper_store": "this router's USB store", "reaper_store_ds": "this router's USB store",
    "reaper_store_vid": "this router's USB volume pin", "reaper_store_vname": "this router's USB volume pin",
    "rtraf_path": "a USB path on this router",
    "reaper_wanbounce_enable": "this router's WAN port",
    "wl_bwfloor": "radio tuning", "wl_punct": "radio tuning", "wl_rmit": "radio tuning",
}
STOCK = {   # stock keys whose default Reaper changed: the router settings carry them like any stock setting
    "ASUS_EULA", "ASUS_NEW_EULA", "computer_name", "dns_norebind", "enable_samba", "enable_samba_tuxera",
    "http_dut_redir", "message_loglevel", "qos_enable", "smbd_cpage", "smbd_cset", "smbd_enable", "st_max_user",
    "upnp_pinhole_enable", "wrs_cc_enable", "wrs_mals_enable", "wrs_protect_enable", "x_Setting",
}
PREFIX = ("reaper_", "rwarden_", "wallguard_", "gk_", "rwatch_", "rtraf_", "rmcp_", "rchq_", "rconn_", "rdev_", "rlog_",
          "rdns", "renc", "rexport_")
dl = defaults.split("\n")
reaper_keys = set()
all_keys = set()
for i, l in enumerate(dl):
    mm = re.match(r'\s*\{ "([A-Za-z0-9_]+)"', l)
    if not mm: continue
    k = mm.group(1); all_keys.add(k)
    ctx = " ".join(dl[max(0, i - 3):i + 1])
    if k.startswith(PREFIX) or re.search(r"[Rr]eaper|20\d\d-\d\d-\d\d|\bv[23]\.\d", ctx) or k in FULL_ONLY:
        reaper_keys.add(k)
placed = carried | LISTS | set(FULL_ONLY) | STOCK
check("every Reaper option is placed: carried by the settings file, full-backup-only with a reason, or stock",
      not (reaper_keys - placed), sorted(reaper_keys - placed))
check("nothing is both carried and full-backup-only", not (carried & set(FULL_ONLY)), sorted(carried & set(FULL_ONLY)))
check("every carried nvram key exists in defaults.c (a typo would carry nothing)",
      not (carried - STORE - all_keys), sorted(carried - STORE - all_keys))
fields = re.findall(r'\{ "([a-z]+)", SH_JFFS "/\1", sh_chk_[a-z]+ \}', web)
check("every Wallguard settings file (sh_files) is in the settings file",
      len(fields) == 8 and all("wallguard_" + f in carried for f in fields), fields)
check("the Wallguard page's save and the import share sh_files", "for (i = 0; i < SH_NFILES; i++) {" in web
      and "char *v = get_cgi((char *)sh_files[i].field);" in web and "static const struct { const char *field, *file; int (*check)(char *); } F[]" not in web)
sect_rst = {"wallguard": "restart_wallguard;start_wallguard_update", "dns": "restart_dnsmasq;restart_rdnshc", "encdns": "restart_rednsd",
            "watch": "restart_rwatch", "traffic": "restart_rtraf", "export": "restart_rexport", "misc": "restart_upnp"}
check("an import restarts each section's service, in ONE notify_rc", all(v in web for v in sect_rst.values())
      and "rcfg_restart(touch_gk, touch_warden, dw_any, touch);" in web and 'if (touch_gk) notify_rc("restart_gk");' not in web)
check("an import commits every section that writes nvram (pbr / fw keep their own Keep)",
      "if (touch_gk || touch_warden || touch) nvram_commit();" in web and '{ "pbr", 0 }, { "fw", 0 }' in web)

# ---- DDNS
mk = re.search(r"\nstatic int rbk_make_cfg\(const char \*path\)\n\{.*?\n\}\n", web, re.S)
check("rbk_make_cfg keeps the DDNS hostname (no blanking, no stash)", mk and 'nvram_set("ddns_hostname_x", "")' not in mk.group(0)
      and "ddns_hostname_tmp" not in mk.group(0) and "sys_download((char *)path);" in mk.group(0))
check("page: the same-model restore takes up to 512 KB of settings, another model keeps the 60 KB form limit",
      "jsonBlob.size > 524288" in page and page.count("jsonBlob.size > 60000") == 1
      and page.find("jsonBlob.size > 60000") > page.find("if(cfg && String(j.model) === MODEL){"))
check("httpd: the pending settings half may be 512 KB", "#define RCFG_PENDING_MAX\t(512 * 1024)" in web)

# ---- round trip on the host
CC = shutil.which("gcc") or shutil.which("cc")
def cfun(name):
    mm = re.search(r"\nstatic [a-z_ ]+\*?%s\([^)]*\)\n\{.*?\n\}\n" % name, web, re.S)
    return mm.group(0) if mm else ""
a = web.find("static const char *sh_presets[]")
b = web.find("static void fw_json_frag(FILE *stream, const char *s);", a)
region = web[a:b] if a > 0 and b > a else ""
tbl = re.search(r"static const struct \{ const char \*sect; const char \*nv; size_t max; \} rcfg_flags\[\] = \{.*?\n\};\n#define RCFG_NFLAGS[^\n]*\n", web, re.S)
fns = [cfun(n) for n in ("rcfg_rw_list", "rcfg_ok", "rcfg_flag_ok", "rcfg_wg_file", "rcfg_get", "rcfg_put")]
check("the import / export region lifts", region and tbl and all(fns), [n for n, f in zip(("rcfg_rw_list", "rcfg_ok", "rcfg_flag_ok", "rcfg_wg_file", "rcfg_get", "rcfg_put"), fns) if not f])
if CC and region and tbl and all(fns):
    w = tempfile.mkdtemp(prefix="bkcov_")
    try:
        STUB = r'''#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>
#include <arpa/inet.h>
/* the router's /jffs is the working directory (router A exports, router B imports) */
#define SH_JFFS "./wallguard"
#define SH_LIST_MAX 16384
#define SH_CATALOG "./services"
#define REAPER_RW_DIR "./rwarden"
#define RDW_SRC REAPER_RW_DIR "/dnssrc"
#define RDW_KEYS REAPER_RW_DIR "/dnskeys"
#define RDW_SRC_MAX 16384
#define REAPER_DHCP6_FILE "./reaper/dhcp6_static"
#define RVIEW_RULES "./reaper/review/rules"
#define RVIEW_RULES_BYTES 8192
#define RLOGF_FILE "./reaper/logfilter"
#define RLOGF_BYTES 4096
static char rjbuf[65536];
static char *rjf_get(const char *p, int *ex) { FILE *f = fopen(p, "r"); size_t n = 0; rjbuf[0] = 0; *ex = f != NULL;
  if (f) { n = fread(rjbuf, 1, sizeof(rjbuf) - 1, f); rjbuf[n] = 0; fclose(f); while (n && rjbuf[n-1] == '\n') rjbuf[--n] = 0; } return rjbuf; }
static int rjf_set(const char *p, const char *v, const char *tag) { FILE *f = fopen(p, "w"); (void)tag; if (!f) return -1; fputs(v, f); fclose(f); return 0; }
static char *rw_list_get(const char *n) { char p[600]; int ex; snprintf(p, sizeof(p), "./rwarden/%s", n); return strdup(rjf_get(p, &ex)); }
static int rw_list_set(const char *n, const char *v) { char p[600]; snprintf(p, sizeof(p), "./rwarden/%s", n); return rjf_set(p, v, "rwarden"); }
static char *rview_slurp(const char *p, size_t max) { int ex; char *v = rjf_get(p, &ex); (void)max; return ex ? strdup(v) : NULL; }
static int rview_rules_ok(const char *v) { return strchr(v, '`') ? -1 : 0; }
static void rview_alog(const char *a, const char *b) { (void)a; (void)b; }
static int rlogf_ok(const char *v) { return strchr(v, '`') ? -1 : 0; }
static int rdev_dhcp6_import(const char *v) { return rjf_set(REAPER_DHCP6_FILE, v, "dev"); }
static int gk_valid_mac(const char *s) { int i; if (strlen(s) != 17) return 0; for (i = 0; i < 17; i++) if (i % 3 == 2 ? s[i] != ':' : !isxdigit((unsigned char)s[i])) return 0; return 1; }
static char NK[256][64], NV[256][300]; static int nn;
static char *nvram_safe_get(const char *k) { int i; for (i = 0; i < nn; i++) if (!strcmp(NK[i], k)) return NV[i]; return ""; }
static int nvram_set(const char *k, const char *v) { int i; for (i = 0; i < nn; i++) if (!strcmp(NK[i], k)) break;
  if (i == nn) { if (nn == 256) return -1; snprintf(NK[nn++], 64, "%s", k); } snprintf(NV[i], 300, "%s", v); return 0; }
'''
        MAIN = r'''
static void hexout(const char *s) { for (; *s; s++) printf("%02x", (unsigned char)*s); }
static char *unhex(const char *h) { size_t n = strlen(h) / 2, i; char *o = malloc(n + 1); for (i = 0; i < n; i++) { unsigned v; sscanf(h + 2 * i, "%2x", &v); o[i] = (char)v; } o[n] = 0; return o; }
int main(int argc, char **argv) {
  char line[200000]; int i;
  if (!strcmp(argv[1], "export")) {
    /* nvram comes from stdin as k=hexvalue lines */
    while (fgets(line, sizeof(line), stdin)) { char *e = strchr(line, '='); if (!e) continue; *e = 0; line[strcspn(e + 1, "\n") + (e + 1 - line)] = 0; nvram_set(line, unhex(e + 1)); }
    for (i = 0; i < RCFG_NFLAGS; i++) { int have; char *v = rcfg_get(i, &have); if (!have) continue; printf("%s=", rcfg_flags[i].nv); hexout(v); printf("\n"); free(v); }
    return 0;
  }
  while (fgets(line, sizeof(line), stdin)) {
    char *e = strchr(line, '='); if (!e) continue; *e = 0; e[strcspn(e + 1, "\n") + 1] = 0;
    for (i = 0; i < RCFG_NFLAGS; i++) if (!strcmp(rcfg_flags[i].nv, line)) { printf("PUT %s %d\n", line, rcfg_put(i, unhex(e + 1))); break; }
  }
  for (i = 0; i < nn; i++) { printf("NV %s=", NK[i]); hexout(NV[i]); printf("\n"); }
  return 0;
}
'''
        c = os.path.join(w, "t.c")
        open(c, "w").write(STUB + region + "\n" + fns[0] + fns[1] + tbl.group(0) + "".join(fns[2:]) + MAIN)
        exe = os.path.join(w, "t")
        r = subprocess.run([CC, "-Wall", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
        check("the region compiles on its own", r.returncode == 0, r.stderr[-1500:])
        if r.returncode == 0:
            A, B = os.path.join(w, "A"), os.path.join(w, "B")
            for root in (A, B):
                for d in ("wallguard", "rwarden", "reaper/review"): os.makedirs(os.path.join(root, d))
                open(os.path.join(root, "services"), "w").write("tiktok social TikTok\nroblox gaming Roblox\n")
            fa = lambda rel, v: open(os.path.join(A, rel), "w").write(v)
            fa("wallguard/lists", "hagezi_normal\nhidden oisd_small\ncustom 2 https://api.example/v1/ name=TFox fmt=json:ioc hdr=Auth-Key\n")
            fa("wallguard/block", "ads.example\n")
            fa("wallguard/profiles", "kids 7fffffff Kids\n")
            fa("wallguard/keys", "2 WgKEY-1\n")
            fa("rwarden/dnssrc", "hidden basics\ncustom 1 https://lists.example/hosts.txt name=My%20list\noff 1\n")
            fa("rwarden/dnskeys", "1 DwKEY-9\n")
            fa("rwarden/ban", "203.0.113.0/24\n")
            fa("reaper/logfilter", "dhcp\n")
            NVA = {"wallguard_enable": "1", "wallguard_mode": "nx", "reaper_dot_srv": "1", "reaper_dnshc_target": "10.20.0.98",
                   "reaper_export_url": "https://splunk.example:8088/services/collector?x=1&y=2", "reaper_export_token": "Tok-123/abc=",
                   "rwatch_iv": "5", "rconn_names": "1", "rmcp_client": "192.168.50.97", "rwarden_reset": "7d", "rtraf_probe": "1.1.1.1"}
            r = subprocess.run([exe, "export"], cwd=A, input="".join("%s=%s\n" % (k, v.encode().hex()) for k, v in NVA.items()), capture_output=True, text=True)
            exp = dict(l.split("=", 1) for l in r.stdout.split("\n") if "=" in l)
            dec = {k: bytes.fromhex(v).decode() for k, v in exp.items()}
            check("export: Wallguard's files and keys, Dreadwatch's sources and keys, the new switches",
                  dec.get("wallguard_lists", "").startswith("hagezi_normal") and dec.get("wallguard_keys") == "2 WgKEY-1"
                  and dec.get("rwarden_dnssrc", "").startswith("hidden basics") and dec.get("rwarden_dnskeys") == "1 DwKEY-9"
                  and dec.get("wallguard_enable") == "1" and dec.get("reaper_dot_srv") == "1" and dec.get("reaper_export_token") == "Tok-123/abc=",
                  {k: dec.get(k) for k in ("wallguard_lists", "wallguard_keys", "rwarden_dnssrc", "rwarden_dnskeys", "wallguard_enable")})
            check("export: a file router A never had is left out (allow, assign, services, sched, safe)",
                  all(k not in dec for k in ("wallguard_allow", "wallguard_assign", "wallguard_services", "wallguard_sched", "wallguard_safe")), sorted(dec))
            # router B already has its own Wallguard allow file and a stale key: the restore must leave allow alone
            open(os.path.join(B, "wallguard/allow"), "w").write("keep.example\n")
            open(os.path.join(B, "rwarden/dnskeys"), "w").write("5 StaleKEY\n")
            r = subprocess.run([exe, "import"], cwd=B, input="".join("%s=%s\n" % (k, v) for k, v in exp.items()), capture_output=True, text=True)
            puts = dict(l.split()[1:3] for l in r.stdout.split("\n") if l.startswith("PUT "))
            nvb = {l[3:].split("=", 1)[0]: bytes.fromhex(l[3:].split("=", 1)[1]).decode() for l in r.stdout.split("\n") if l.startswith("NV ")}
            rb = lambda rel: open(os.path.join(B, rel)).read() if os.path.exists(os.path.join(B, rel)) else None
            ra = lambda rel: open(os.path.join(A, rel)).read()
            check("import: every exported value was taken", puts and all(v == "0" for v in puts.values()), {k: v for k, v in puts.items() if v != "0"})
            check("import: Wallguard's files and Dreadwatch's sources come back as written",
                  rb("wallguard/lists") == ra("wallguard/lists") and rb("wallguard/block") == ra("wallguard/block")
                  and rb("wallguard/profiles") == ra("wallguard/profiles") and rb("rwarden/dnssrc") == ra("rwarden/dnssrc")
                  and rb("rwarden/ban") in (ra("rwarden/ban"), ra("rwarden/ban").rstrip("\n")),
                  [rb("wallguard/lists"), rb("rwarden/dnssrc")])
            check("import: both key files are the backup's (router B's stale key is gone)",
                  rb("wallguard/keys") == "2 WgKEY-1\n" and rb("rwarden/dnskeys") == "1 DwKEY-9\n", [rb("wallguard/keys"), rb("rwarden/dnskeys")])
            check("import: a file the backup did not carry is left as router B had it", rb("wallguard/allow") == "keep.example\n")
            check("import: the switches land in nvram, URL and token included",
                  all(nvb.get(k) == v for k, v in NVA.items()), {k: (nvb.get(k), v) for k, v in NVA.items() if nvb.get(k) != v})
            # refusals: nothing written
            bad = {"wallguard_block": "not a name!\n", "rwarden_dnssrc": "custom 9 https://x.example/l\n",
                   "reaper_export_url": 'https://x.example/"q', "wallguard_keys": "2 has space", "reaper_dot_srv": "1;reboot",
                   "wallguard_lists": "custom 1 http://plain.example/\n"}
            before = {rel: rb(rel) for rel in ("wallguard/block", "rwarden/dnssrc", "wallguard/keys", "wallguard/lists")}
            r = subprocess.run([exe, "import"], cwd=B, input="".join("%s=%s\n" % (k, v.encode().hex()) for k, v in bad.items()), capture_output=True, text=True)
            puts = dict(l.split()[1:3] for l in r.stdout.split("\n") if l.startswith("PUT "))
            check("import: a bad value in any store is refused", len(puts) == len(bad) and all(v == "-1" for v in puts.values()), puts)
            check("import: a refused value writes nothing", all(rb(rel) == v for rel, v in before.items()), {rel: rb(rel) for rel in before})
    finally:
        shutil.rmtree(w, ignore_errors=True)
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
