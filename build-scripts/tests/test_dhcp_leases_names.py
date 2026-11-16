#!/usr/bin/env python3
"""DHCP leases that survive a restart and the device-label rule (owner, 2026-11-15).

WHY. After a restart the router's lease files (RAM) were empty, so a device still holding a valid lease that did not
rejoin (a PC cabled to an AiMesh node) was missing from DHCP Leases and showed no name on Encrypted DNS until it
renewed. The owner: a device with a lease that is still active must be shown; Name = only a name the admin gave on
the Devices page (the one master list; a reservation's name is its DNS name); Hostname = what the client sent, else
the maker of a real MAC, else "Private-Address"; one-label surfaces show Name else Hostname. Nothing may bypass
Gatekeeper. A "Remove lease" function was built, then dropped by the owner the same day (DHCP cannot make a client ask
again at once; leases are always shown, persistence covers the restart gap): its absence is pinned here.

WHAT IT DOES.
  - shared/reaper_leases.c compiled on the host with the real reaper_tmpsafe.c: restore (fresh boot only, refuses a
    malformed copy), save (on a change of the set, hourly, forced), file-name and line checks.
  - httpd/reaper_devname.c compiled on the host: Name / Hostname / label on real cases, the reservation name never
    counted as a client hostname, every record of each OUI table the tree ships found (a record with an empty maker
    gives none), private MACs never given a maker.
  - source pins: restore before each dnsmasq starts, save at reboot and in rwatch, the name store never filing the
    reservation name as client-sent, Gatekeeper's list untouched, the page (no-DHCP rows, busy feedback), no Remove
    anywhere (no handler, no dhcp_release, no page button, no RLOG_104/105), RLOG_106/107 in 25 packs.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import glob, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "reaper_leases.c")):
    print("SKIP: no router tree with shared/reaper_leases.c (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail != "" else ""))
def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

# ============================================================ shared/reaper_leases.c on the host
lc, ts = rd("shared/reaper_leases.c"), rd("shared/reaper_tmpsafe.c")
if CC:
    w = tempfile.mkdtemp(prefix="rls_")
    try:
        live, keep, tmp = (os.path.join(w, d) for d in ("live", "jffs", "tmp"))
        for d in (live, keep, tmp): os.makedirs(d)
        src = (lc.replace('"/jffs/reaper/leases"', '"%s/reaper/leases"' % keep).replace('"/jffs/reaper"', '"%s/reaper"' % keep)
                 .replace('"/var/lib/misc"', '"%s"' % live).replace('"/tmp/reaper/leases.saved"', '"%s/leases.saved"' % tmp)
                 .replace('"/tmp/reaper"', '"%s"' % tmp)
                 .replace('#include "shutils.h"\n#include "shared.h"\n#include "reaper_tmpsafe.h"\n', ''))
        hdr = r'''#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
static long g_up = 100; static int g_usr2 = 0;
long uptime(void){ return g_up; }
int killall(const char *n, int s){ (void)n; (void)s; g_usr2++; return 0; }
int f_read_string(const char *f, char *b, int m){ FILE *x = fopen(f, "r"); int n = 0; b[0] = 0; if (x){ n = (int)fread(b, 1, m - 1, x); b[n] = 0; fclose(x);} return n; }
void logmessage_normal(char *h, char *fmt, ...){ va_list a; va_start(a, fmt); fprintf(stderr, "%s: ", h); vfprintf(stderr, fmt, a); fputc('\n', stderr); va_end(a); }
#define logmessage logmessage_normal
#define REAPER_TMP_DIRS { { NULL, 0 } }
'''
        tsrc = re.sub(r'#include "[^"]+"\n', '', ts)
        # reaper_tmpsafe.c's directory table and a symlink test are kept; only its own includes are dropped
        main = r'''
int main(int argc, char **argv){
  if (!strcmp(argv[1], "ok")) { for (int i = 2; i < argc; i++) printf("%d", reaper_leases_name_ok(argv[i])); printf("\n"); return 0; }
  if (!strcmp(argv[1], "valid")) { printf("%d\n", reaper_leases_valid(argv[2], argv[3], strlen(argv[3]))); return 0; }
  if (!strcmp(argv[1], "restore")) { printf("%d\n", reaper_leases_restore(argv[2])); return 0; }
  if (!strcmp(argv[1], "save")) { g_up = atol(argv[2]); int r = reaper_leases_save(atoi(argv[3])); printf("%d %d\n", r, g_usr2); return 0; }
  return 2; }
'''
        c = os.path.join(w, "t.c"); open(c, "w").write(hdr + "#include <dirent.h>\n#include <ctype.h>\n#include <errno.h>\n#include <fcntl.h>\n#include <signal.h>\n" + tsrc + "\n" + src + main)
        exe = os.path.join(w, "t")
        r = run([CC, "-Wall", "-Wno-unused-function", "-o", exe, c])
        check("reaper_leases.c compiles on the host", r.returncode == 0, r.stderr[-900:])
        if r.returncode == 0:
            T = lambda *a: run([exe] + list(a)).stdout.strip()
            check("file names: the main lease file, each network's, the announced names; nothing else",
                  T("ok", "dnsmasq.leases", "dnsmasq-3.leases", "reaper_hostnames", "dnsmasq-.leases", "dnsmasq-3x.leases", "../dnsmasq.leases", "dnsmasq.leases.tmp", "hosts") == "11100000")
            L1 = "86000 70:85:c2:00:53:01 192.168.50.126 DESKTOP-EXAMPL1 01:70:85:c2:00:53:01\n43000 0c:83:cc:00:53:02 192.168.50.215 Security-Relay *\n"
            check("a lease file and the IPv6 server line are well formed", T("valid", "dnsmasq.leases", L1 + "duid 00:01:00:01:2a\n") == "1")
            check("malformed: a missing field, a shell quote, no final newline, a huge number",
                  T("valid", "dnsmasq.leases", "86000 aa:bb 1.2.3.4 x\n") == "0" and T("valid", "dnsmasq.leases", "1 a b c' d\n") == "1"
                  and T("valid", "dnsmasq.leases", L1.rstrip("\n")) == "0" and T("valid", "dnsmasq.leases", "123456789012 a b c d\n") == "0")
            check("the name store: tab fields, a MAC first", T("valid", "reaper_hostnames", "70:85:C2:00:53:01\tDESKTOP\tMSFT 5.0\t1794768353\n") == "1"
                  and T("valid", "reaper_hostnames", "notamac\tx\n") == "0")
            # save: nothing live yet -> nothing; then a lease appears -> written (and dnsmasq asked for fresh times)
            check("save with no lease files writes nothing", T("save", "100", "0") == "0 0")
            open(os.path.join(live, "dnsmasq.leases"), "w").write(L1)
            open(os.path.join(live, "reaper_hostnames"), "w").write("70:85:C2:00:53:01\tDESKTOP-EXAMPL1\tMSFT 5.0\t1794768353\n")
            open(os.path.join(live, "dnsmasq.leases.junk"), "w").write("x")
            out = T("save", "200", "0")
            kept = sorted(os.listdir(os.path.join(keep, "reaper", "leases")))
            check("a new set is saved (both files, nothing else), after asking dnsmasq for fresh times", out == "2 1" and kept == ["dnsmasq.leases", "reaper_hostnames"], (out, kept))
            mode = oct(os.stat(os.path.join(keep, "reaper", "leases")).st_mode & 0o777)
            check("the folder is the owner's alone", mode == "0o700", mode)
            open(os.path.join(live, "dnsmasq.leases"), "w").write(L1.replace("86000", "85000").replace("43000", "42000"))
            check("same leases, only the seconds moved, within the hour: not written", T("save", "300", "0") == "0 0")
            check("the hourly refresh writes the fresh seconds", T("save", "3900", "0").startswith("2 ") and
                  open(os.path.join(keep, "reaper", "leases", "dnsmasq.leases")).read().startswith("85000"))
            open(os.path.join(live, "dnsmasq.leases"), "a").write("80000 aa:bb:cc:dd:ee:01 192.168.50.30 Phone *\n")
            check("a lease added: written at once", T("save", "3950", "0").startswith("2 "))
            check("forced (reboot or halt): written", T("save", "3960", "1").startswith("2 "))
            # restore: only into a missing live file
            check("restore does nothing while the live file exists", T("restore", os.path.join(live, "dnsmasq.leases")) == "0")
            os.unlink(os.path.join(live, "dnsmasq.leases")); os.unlink(os.path.join(live, "reaper_hostnames"))
            r1 = T("restore", os.path.join(live, "dnsmasq.leases")); r2 = T("restore", os.path.join(live, "reaper_hostnames"))
            check("a fresh boot puts both files back, as saved", r1 == "1" and r2 == "1"
                  and "192.168.50.30" in open(os.path.join(live, "dnsmasq.leases")).read()
                  and oct(os.stat(os.path.join(live, "reaper_hostnames")).st_mode & 0o777) == "0o600", (r1, r2))
            check("restore refuses a path outside the lease folder or a foreign name",
                  T("restore", "/etc/passwd") == "-1" and T("restore", os.path.join(live, "hosts")) == "-1")
            os.unlink(os.path.join(live, "dnsmasq.leases"))
            open(os.path.join(keep, "reaper", "leases", "dnsmasq.leases"), "w").write("garbage line\n")
            check("a malformed saved copy is not restored", T("restore", os.path.join(live, "dnsmasq.leases")) == "-1"
                  and not os.path.exists(os.path.join(live, "dnsmasq.leases")))
    finally:
        shutil.rmtree(w, ignore_errors=True)
else:
    print("note: no host C compiler - reaper_leases.c was not run")

# ============================================================ httpd/reaper_devname.c on the host
dn = rd("httpd/reaper_devname.c")
if CC:
    w = tempfile.mkdtemp(prefix="rdn_")
    try:
        shutil.copy(os.path.join(SRC, "httpd", "reaper_devname.h"), w)
        open(os.path.join(w, "stub.h"), "w").write(r'''#include <string.h>
#include <strings.h>
#include <stdio.h>
static const char *nv_cust = "<Kids-PC>70:85:C2:00:53:01>0>0><Security-Relay>0C:83:CC:00:53:02>0>0>";
static const char *nv_resv = "<0C:83:CC:00:53:02>192.168.50.215>>Security-Relay<64:52:99:00:53:03>192.168.50.23>>Garage-Door";
static const char *nvram_safe_get(const char *k){ return !strcmp(k,"custom_clientlist") ? nv_cust : !strcmp(k,"dhcp_staticlist") ? nv_resv : ""; }
static int reaper_dhcpname_get(const char *mac, char *out, size_t n){ if(!strcasecmp(mac,"00:00:5e:00:53:27")){ snprintf(out,n,"Den-PC"); return 1;} out[0]=0; return 0; }
''')
        results = {}
        for tag, tbl in (("networkmap one-line", os.path.join(SRC, "networkmap", "db", "ieee.oui.json")), ("www one-per-line", os.path.join(SRC, "www", "ajax", "ouiDB.json"))):
            if not os.path.isfile(tbl):
                continue
            d = (dn.replace('"/usr/networkmap/ieee.oui.json"', '"%s"' % tbl).replace('"/www/ajax/ouiDB.json"', '"/nonexistent"')
                   .replace("#include <bcmnvram.h>", '#include "stub.h"').replace("#include <shared.h>\n", ""))
            open(os.path.join(w, "d.c"), "w").write(d)
            open(os.path.join(w, "t.c"), "w").write(r'''#include <stdio.h>
#include "d.c"
static void show(const char *mac, const char *lh){ char a[64],h[64],l[64]; rdn_admin_name(mac,a,sizeof a); rdn_hostname(mac,lh,h,sizeof h); rdn_label(mac,lh,l,sizeof l); printf("%s|%s|%s\n",a,h,l); }
int main(int argc, char **argv){
 (void)argc; show("70:85:c2:00:53:01","DESKTOP-EXAMPL1"); show("70:85:c2:00:53:01",""); show("0c:83:cc:00:53:02","Security-Relay");
 show("00:00:5e:00:53:27","Den-PC"); show("02:00:5e:00:53:6f","*"); show("02:00:5e:00:53:6f","iPhone"); show("fc:ff:fd:00:53:04","");
 show("64:52:99:00:53:03","Garage-Door");
 FILE *f=fopen(argv[1],"r"); static char buf[2000000]; size_t n=fread(buf,1,sizeof buf-1,f); buf[n]=0; fclose(f);
 int keys=0, ok=0, bad=0; char *p=buf;
 while((p=strchr(p,'"'))){ if(p[7]=='"'&&p[8]==':'&&p[9]=='"'&&(p==buf||p[-1]=='{'||p[-1]==','||p[-1]==10)){ char k[7]; memcpy(k,p+1,6); k[6]=0; int hx=1; for(int i=0;i<6;i++) if(!isxdigit((unsigned char)k[i])) hx=0;
   if(hx){ char mac[18], o[64]; snprintf(mac,18,"%c%c:%c%c:%c%c:00:00:01",k[0],k[1],k[2],k[3],k[4],k[5]); keys++; int r=rdn_oui(mac,o,sizeof o);
     if((rdn_mac_private(mac) || p[10]=='"') ? r==0 : r==1) ok++; else bad++; } } p++; }
 printf("%d %d %d\n", keys, ok, bad); return 0; }
''')
            r = run([CC, "-Wall", "-Wextra", "-O2", "-o", os.path.join(w, "t"), os.path.join(w, "t.c")])
            if r.returncode != 0:
                check("reaper_devname.c compiles on the host (%s)" % tag, False, r.stderr[-700:]); continue
            results[tag] = run([os.path.join(w, "t"), tbl]).stdout.strip().split("\n")
        # the 102.10 tree ships networkmap's one-line table (www links to it); the 102.8 tree only the www copy (older,
        # ~39 500 records, one "04208A" record with an empty maker)
        nm_tbl = os.path.isfile(os.path.join(SRC, "networkmap", "db", "ieee.oui.json"))
        check("the helper ran on every OUI table the tree ships (networkmap one-line where present, www one-per-line)",
              "www one-per-line" in results and (not nm_tbl or "networkmap one-line" in results), list(results))
        for tag, out in results.items():
            keys, ok, bad = (int(x) for x in out[-1].split())
            check("[%s] every record found, private prefixes and empty makers never given a maker (%d records)" % (tag, keys), keys > 30000 and ok == keys and bad == 0, out[-1])
        out = list(results.values())[0] if results else []
        if out:
            check("Name = the Devices page name; Hostname = what the client sent", out[0] == "Kids-PC|DESKTOP-EXAMPL1|Kids-PC", out[0])
            check("no client hostname, real MAC: the maker", out[1] == "Kids-PC|ASRock Incorporation|Kids-PC", out[1])
            check("a reserved device named on the Devices page: that Name; its reservation name never taken as its Hostname", out[2] == "Security-Relay|Alpha Networks Inc.|Security-Relay", out[2])
            check("no admin Name: the label is the client's hostname (announced name store first)", out[3] == "|Den-PC|Den-PC", out[3])
            check("a private MAC with no hostname: Private-Address", out[4] == "|Private-Address|Private-Address", out[4])
            check("a private MAC that sends a hostname keeps it", out[5] == "|iPhone|iPhone", out[5])
            check("a real MAC the table does not list: no maker invented", out[6] == "||", out[6])
            check("a reservation's name is its DNS name, never a Name (owner: one master Name list) nor its Hostname",
                  out[7].startswith("|The Chamberlain Group") and out[7].split("|")[2].startswith("The Chamberlain Group"), out[7])
    finally:
        shutil.rmtree(w, ignore_errors=True)

# ============================================================ source pins
svc, sdn, ini, rw, mk, web, da, rcc, rcm = (rd(p) for p in ("rc/services.c", "rc/sdn.c", "rc/init.c", "rc/rwatch.c", "Makefile", "httpd/web.c", "httpd/data_arrays.c", "rc/rc.c", "rc/Makefile"))
check("restore before the main dnsmasq starts (leases and announced names)",
      re.search(r'reaper_leases_restore\("/var/lib/misc/dnsmasq\.leases"\);\n\treaper_leases_restore\("/var/lib/misc/reaper_hostnames"\);\n\teval\("dnsmasq", "--log-async"\);', svc) is not None)
check("restore before each Guest Network Pro / VLAN dnsmasq starts",
      re.search(r'snprintf\(lpath, sizeof\(lpath\), "/var/lib/misc/dnsmasq-%d\.leases", pmtl->sdn_t\.sdn_idx\);\n\t+reaper_leases_restore\(lpath\);\n\t+eval\("dnsmasq", "-C", config_path, "--log-async"\);', sdn) is not None)
check("save at reboot and halt only, while dnsmasq still runs (before the services stop)",
      0 < ini.find("if (state == SIGTERM /* REBOOT */ || state == SIGQUIT /* HALT */)\n\t\t\t\treaper_leases_save(1);") < ini.find("stop_services();", ini.find("reaper_leases_save(1);")))
check("rwatch's tick saves (applet registered and linked)", '"[ -x /sbin/reaper_leases ] && /sbin/reaper_leases save >/dev/null 2>&1\\n"' in rw
      and '{ "reaper_leases",		reaper_leases_main		},' in rcc and "ln -sf rc reaper_leases" in rcm)
check("the name store never files the reservation name as client-sent", "if (!(sup && *sup) && *ln && reaper_resv_name_is(mac, ln))\n\t\t\t\tln = \"\";" in svc)
# owner 2026-11-15: no Remove lease - DHCP has no way to make a client ask again at once (FORCERENEW is unsupported),
# so a removed lease only left the device shown without one until its renewal
gone = [w for w, t in (("dhcp_release in the router Makefile", "dhcp_release" in mk), ("reaper_leases.cgi in httpd", "reaper_leases.cgi" in web),
                       ("do_reaper_leases_cgi in httpd", "do_reaper_leases_cgi" in web), ("rlease_find in httpd", "rlease_find" in web)) if t]
check("no Remove lease: no handler, no CGI row, dhcp_release not built", not gone, gone)
gk_free = [p for p, t in (("shared/reaper_leases.c", lc), ("httpd/reaper_devname.c", dn)) if re.search(r"gk_rl|gk_enable|REAPER_GK", t)]
check("Gatekeeper: none of this reads or writes its list or rules", not gk_free, gk_free)
check("DHCP Leases producer: Hostname / Name by the rule, active devices without a lease listed with -1",
      "rdn_hostname(mac, lease_host, host, sizeof(host));" in da and "rdn_admin_name(mac, name, sizeof(name));" in da and "rlease_row(wp, -1, mac, ip, \"\", nets[k].vlan);" in da)
check("Encrypted DNS names: the one label, from the lease or the neighbour table", web.count("rdn_label(mac, ") >= 2 and "/* addresses with no lease line: the neighbour table gives the MAC (IPv4) */" in web)

# ---- the rule across the router (the 2026-11-15 survey)
dn_src = rd("httpd/reaper_devname.c")
check("Name = the Devices page list only (the master list)", re.search(r"int rdn_admin_name\(.*?\n\}", dn_src, re.S) and "rdn_resv_name(mac, out, n)" not in dn_src)
check("the shared feed: appGet hook reaper_devnames registered, Name + Hostname + address per device",
      '{ "reaper_devnames", ej_reaper_devnames},' in web and "rdn_admin_name(f[i].mac, name, sizeof(name));" in web and "rdn_hostname(f[i].mac, f[i].lh, host, sizeof(host));" in web)
check("Gatekeeper rows and the Devices page host follow the rule; networkmap's label (gk_nmp_name) is gone",
      "rdn_label(mac, host, name, nlen);" in web and "if (rdn_client_host(dev[i].mac, dev[i].host, h, sizeof(h)))" in web and "gk_nmp_name(" not in web)
ut = rd("www/reaper_util.js")
check("ReaperNames: one request (get_clientlist + reaper_devnames), Name else Hostname, name()/host() apart, no networkmap label",
      "hook=get_clientlist();reaper_devnames()" in ut and "function label(m){ var n = nameOf[m]; if(n) return n; var h = hostOf[m]; return h ? h : ''; }" in ut
      and "name: function(mac)" in ut and "host: function(mac)" in ut and "c.nickName" not in ut)
dash, v6, lan, wol, par, cf, dg = (rd(p) for p in ("www/Main_ReaperDash.asp", "www/Reaper_IPv6.asp", "www/Reaper_LAN.asp", "www/Reaper_WOL.asp", "www/Reaper_Parental.asp", "www/client_function.js", "others/reaper_diag"))
check("dashboard tiles: the feed, Name else Hostname else MAC", "hook=get_clientlist();reaper_devnames()" in dash and "nm=dd.n||dd.h||macs[i];" in dash)
check("IPv6 clients: Name and Hostname in their own columns", "['name', `<#RLOG_49#>`], ['host', `<#RLOG_50#>`]" in v6 and "name: ReaperNames.name(r[1]), host: ReaperNames.host(r[1]) || lease" in v6)
check("LAN reservations: the field is the DNS name (RLAN_58); the master Name shown beside it; no Name in the DNS cell",
      "<th><#RLOG_49#></th><th><#MAC_Address#></th>" in lan and "<th><#RLAN_58#></th>" in lan and "function hostCell(r){ return r.host ? hx(r.host) : '-'; }" in lan)
check("Wake-on-LAN and Parental Controls: the master Name first, their own copy only as a fallback",
      "hx((dv && dv.name) || r.name || '-')" in wol and "return n || r.name || h || r.mac;" in par)
check("stock client card / tooltip: no maker looked up for a randomized MAC", "if (reaper_mac_private(mac)) return;" in cf and "if(reaper_mac_private(mac)) {" in cf)
check("diag: the Names, the reservations' DNS names and the announced hostnames are on its redaction list",
      "sed -n 's/^custom_clientlist=//p' \"$NVS\"" in dg and "sed -n 's/^dhcp_staticlist=//p' \"$NVS\"" in dg and "/var/lib/misc/reaper_hostnames >> \"$SLIST\"" in dg)
packs2 = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if not p.endswith("temp.dict"))
check("packs: RLAN_58 (DNS name) in all 25", len(packs2) == 25 and all(re.search(r"^RLAN_58=.+$", open(p, encoding="utf-8", errors="replace").read(), re.M) for p in packs2))

pg = rd("www/Reaper_Leases.asp")
check("page: -1 (a device whose address is set on the device, no DHCP) reads RLOG_106; no Name shows empty",
      "if (n === -1) return `<#RLOG_106#>`;" in pg and "hx(v || (c.k === 'dev' ? '' : '-'))" in pg)
check("page: Refresh shows it was pressed (ReaperBusy)", "q('b_refresh').addEventListener('click', function(){ ReaperBusy.start(this);" in pg
      and "ReaperBusy.words(`<#RBSY_1#>`, `<#RBSY_2#>`, `<#RBSY_3#>`);" in pg)
left = [w for w in ("data-rm", "removeLease", "reaper_leases.cgi", "RLOG_104", "RLOG_105", "http_id") if w in pg]
check("page: no Remove button, request or text", not left, left)
packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if not p.endswith("temp.dict"))
miss = [os.path.basename(p) for p in packs
        if not all(re.search(r"^RLOG_%d=.+$" % k, open(p, encoding="utf-8", errors="replace").read(), re.M) for k in (106, 107))
        or re.search(r"^RLOG_10[45]=", open(p, encoding="utf-8", errors="replace").read(), re.M)
        or re.search(r"^RLOG_107=.*DHCP.reserv", open(p, encoding="utf-8", errors="replace").read(), re.M)]
check("packs: RLOG_106/107 in all 25, RLOG_104/105 gone, the hint no longer names the reservation", len(packs) == 25 and not miss, miss)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for x in fails: print("  " + x)
    sys.exit(1)
print("\nall checks passed")
