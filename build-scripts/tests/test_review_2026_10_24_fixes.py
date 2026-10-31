#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The 2026-10-24 review's low findings and correctness items, fixed 2026-10-25 - the pins, and the secret-masking
helpers run on the host.

WHY THIS EXISTS. An adversarial review of the whole pending delta found, below its high and medium items, thirteen
low findings and five correctness slips. Each fix is a few lines in a file that nothing compiles before the image
build (generated shell, page scripts) or that only metal exercises (httpd). This file pins every one of them in
source so a later edit cannot quietly undo one, cross-checks the Security Review's cron command table against the
commands rc really installs, and compiles the secret-masking helpers out of web.c to prove the mask and the unmask
round-trip the lists the pages post.

WHAT IT DOES. Static pins: S-A-4 wallguard.sh fold refuses a directory or link at the hit file; S-A-5 rwatch reads
rednsd's status file only as a plain file; S-A-6 the Dreadwatch collector drops a link or directory unread; S-A-7
encdns.sh validates IPv6 shape and refuses private / short ranges, with a per-entry fallback; S-A-8 the review skips
a Reaper cron id only with rc's command (table == the #defines); S-A-9 rednsd never keeps root; S-B-3 the status
file's JSON goes first; S-B-4 every Wallguard checker reads the whole line and sh_json_file escapes markup; S-B-5 the
Network Tools argv store fits a host name; Q-B-1 the diag uses date -r; Q-C2-1 the Wallguard page keeps every chosen
target across the poll; the Encrypted DNS Save compares with !==; the Gatekeeper token sits in backticks. Then the
rsec_* helpers (mask, split, unmask) compiled with stubs: masks per key, unmask by key, by position, missing row.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape") as f:
        return f.read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

web, hc, rw, rwd, red, enc, sh, diag = (read("httpd/web.c"), read("httpd/httpd.c"), read("rc/rwatch.c"), read("rc/rwarden.c"),
                                        read("rednsd/rednsd.c"), read("rednsd/encdns.sh"), read("wallguard/wallguard.sh"), read("others/reaper_diag"))

# ---- S-A-4 / S-A-5 / S-A-6: planted files
check("S-A-4 wallguard.sh fold: only a plain non-empty file is moved; a directory or link at run/hits is removed unread, the work copy too",
      '[ -f "$RUN/hits" ] && [ ! -L "$RUN/hits" ] || { rm -rf "$RUN/hits" 2>/dev/null; return 0; }' in sh
      and 'if [ -L "$D/hits.work" ] || [ ! -f "$D/hits.work" ]; then rm -rf "$D/hits.work"; return 0; fi' in sh and sh.count('rm -rf "$D/hits.work"') == 2)
check("S-A-5 rwatch: rednsd's status.json is read through $_rsj, a plain file or /dev/null",
      '_rsj=/tmp/rednsd/run/status.json; [ -f \\"$_rsj\\" ] && [ ! -L \\"$_rsj\\" ] || _rsj=/dev/null' in rw and "/tmp/rednsd/run/status.json 2>/dev/null" not in rw)
check("S-A-6 Dreadwatch collector: what moved must be a plain file, else it is removed and the fold returns",
      'if [ -L \\"$W\\" ] || [ ! -f \\"$W\\" ]; then rm -rf \\"$W\\"; return 0; fi' in rwd and rwd.find('mv -f \\"$HF\\" \\"$W\\"') < rwd.find('if [ -L \\"$W\\" ]'))

# ---- S-A-7: the DoH address list
check("S-A-7 encdns.sh: v4 and v6 validators (groups, one ::, prefix floors, no private / loopback / link-local / multicast), fallback to one add per entry",
      "function v4ok(s,   p)" in enc and "function v6ok(s," in enc and "if (p[5] != \"\" && (p[5] < 24 || p[5] > 32)) return 0" in enc
      and "a[2] < 48 || a[2] > 128" in enc and "if (dc > 1) return 0" in enc and "(dc == 0 && ng != 8) || (dc == 1 && ng > 7)" in enc
      and "k[1] ~ /^f[cd]/ || k[1] ~ /^fe[89ab]/ || k[1] ~ /^ff/" in enc
      and 'if ! grep -E "$pat" "$list" | sed "s/^/add $tmp /" | ipset restore -! 2>/dev/null; then' in enc
      and 'while read -r a; do ipset add -exist "$tmp" "$a" 2>/dev/null; done' in enc)

# ---- S-A-8: the cron command table equals what rc installs
defs = {}
for rel in ("rc/rwatch.c", "rc/rwarden.c", "rc/rexport.c", "rc/reaper_fw.c", "rc/reaper_pbr.c", "rc/wallguard.c", "rc/encdns.c"):
    for m in re.finditer(r'#define\s+(RWATCH_SH|RW_UPDATE|RW_FOLD|REXPORT_SH|RFW_DIR|RFW_CC|RFW_RESOLVE|PPBR_DIR|PPBR_CC|SH_SCRIPT|EDNS_SCRIPT)\s+(.+)', read(rel)):
        defs[m.group(1)] = m.group(2).split("/*")[0].strip()
def val(d):
    s = defs.get(d, "")
    s = s.replace("RFW_DIR", defs.get("RFW_DIR", "")).replace("PPBR_DIR", defs.get("PPBR_DIR", ""))
    return "".join(re.findall(r'"([^"]*)"', s))
table = {}
tm = re.search(r'_rv_cron_cmd\(\) \{ case(.*?)esac; \}', rw, re.S)
for m in re.finditer(r"([A-Za-z0-9_|\[\]-]+)\) echo '([^']*)';;", tm.group(1) if tm else ""):
    table[m.group(1)] = m.group(2)
want = {"rwatch": "sh " + val("RWATCH_SH"), "rwarden": "sh " + val("RW_UPDATE"), "rwarden_ck": "sh " + val("RW_FOLD"), "rexport": "sh " + val("REXPORT_SH"),
        "reaper_fw_dns": "sh " + val("RFW_RESOLVE"), "reaper_fw_cc": "sh " + val("RFW_CC"), "reaper_pbr_cc": "sh " + val("PPBR_CC"),
        "wallguard": "sh " + val("SH_SCRIPT") + " update", "wallguard_ck": "sh " + val("SH_SCRIPT") + " fold",
        "wallguard_sp|wallguard_e[0-9][0-9][0-9][0-9]": "service start_wallguard_policy >/dev/null 2>&1", "edns_doh": "sh " + val("EDNS_SCRIPT") + " update"}
check("S-A-8 the review's cron table names exactly the commands rc installs (%d ids)" % len(want), table == want, (table, want))
check("S-A-8 the skip compares the line's command with the table, never the id alone",
      "_ex=$(_rv_cron_cmd \\\"$id\\\"); if [ -n \\\"$_ex\\\" ]; then _cm=${l#* * * * * }; _cm=${_cm% #*}; [ \\\"$_cm\\\" = \\\"$_ex\\\" ] && continue; fi" in rw
      and "RV_IDS" not in rw)
check("S-A-8 rc still installs those commands (rwarden fold / update, wallguard update / fold / policy, edns update, pbr / fw checkers)",
      '"*/15 * * * * sh " RW_FOLD' in rwd and '"15 5 * * * sh " SH_SCRIPT " update"' in read("rc/wallguard.c") and '"*/15 * * * * sh " SH_SCRIPT " fold"' in read("rc/wallguard.c")
      and "service start_wallguard_policy >/dev/null 2>&1" in read("rc/wallguard.c") and '"25 5 * * * sh " EDNS_SCRIPT " update"' in read("rc/encdns.c")
      and '"* * * * * sh " PPBR_CC' in read("rc/reaper_pbr.c") and '"* * * * * sh " RFW_CC' in read("rc/reaper_fw.c") and '"*/10 * * * * sh " RFW_RESOLVE' in read("rc/reaper_fw.c"))

# ---- S-A-9 / S-B-3 / S-B-4 / S-B-5
check("S-A-9 rednsd stops rather than keep root when the nobody account is missing",
      re.search(r"if \(!pw\) \{\s*/\* review 2026-10-24 \(S-A-9\)", red) is not None and "no 'nobody' account - stopping rather than serving as root" in red
      and re.search(r"if \(getuid\(\) != 0\)\s+return;", red) is not None and "if (!pw || getuid() != 0)" not in red)
check("S-B-3 the Encrypted DNS status prints rednsd's file first, the router's fields after it",
      '"{\\"st\\":%s,\\"ok\\":1,\\"enabled\\":%d' in web and '",\\"blk\\":{\\"on\\":%d' in web)
check("S-B-4 every Wallguard save checker reads the whole line (%n lands on its end) and the JSON file emitter escapes < > &",
      # 2026-10-26: a custom list line may carry options after its URL; the rest of that line goes to
      # sh_chk_opts(), which refuses any token it does not know - still "the whole line is read"
      web.count("sh_whole(l, n)") == 6 and 'sscanf(l, "%23s %lx %39[^\\n]%n", id, &m, name, &n)' in web
      and 'sscanf(l, "custom %d %419s%n", &slot, url, &n) == 2 && slot >= 1 && slot <= 8 && sh_url(url) && sh_chk_opts(l + n)' in web
      and 'sscanf(l, "%23s %1099s%n", id, ids, &n)' in web
      and 'sscanf(l, "%23s %x %7s %7s%n", id, &d, a, z, &n)' in web and 'sscanf(l, "%23s %u%n", id, &f, &n)' in web
      and 'sscanf(l, "mac %39s %23s%n", a, id, &n)' in web and 'sscanf(l, "net %39s %23s%n", a, id, &n)' in web
      # Q-B-9: the JSON file emitter is the firewall page's fw_json_frag (one escaper), which escapes < > &
      and 'fw_json_frag(stream, ex > 0 ? v : "");' in web[web.find("static void sh_json_file("):web.find("static void sh_popen(")]
      and "else if (c == '<' || c == '>' || c == '&') fprintf(stream, \"\\\\u%04x\", c);" in web[web.find("\nfw_json_frag(FILE *stream, const char *s)"):][:600])
check("S-B-5 the Network Tools argv store takes a 253-byte host name whole", "char store[16][256];" in web and "len > 253" in web)

# ---- the correctness items
check("Q-B-1 reaper_diag reads the /jffs copy's time with date -r (no stat applet), v1.3.47",
      "_tdu=$(date -r /jffs/rwarden/dns.k.gz +%s 2>/dev/null)" in diag and "stat -c" not in diag and 'VER="REAPER-DIAG v1.3.53"' in diag)
shp = read("www/Reaper_Wallguard.asp")
check("Q-C2-1 the Wallguard page keeps the Assign, Pause and Unbreak targets across the 15 s poll",
      "kt = t.value, kp = p.value, keep = u.value;" in shp and "if(kt) t.value = kt;" in shp and "if(kp) p.value = kp;" in shp and "if(keep) u.value = keep;" in shp)
check("Encrypted DNS: a Save that changes nothing no longer restarts rednsd (!== where === was)",
      "f.reaper_doh_block.value !== (NV.blk === '1' ? '1' : '0')) sv.push('restart_rednsd');" in read("www/Reaper_EncryptedDNS.asp")
      and "f.reaper_doh_block.value === (NV.blk === '1' ? '1' : '0')) sv.push" not in read("www/Reaper_EncryptedDNS.asp"))
gk = read("www/Reaper_GK.asp")
check("Gatekeeper: the guest-hours token sits inside backticks (no token in a single-quoted string)",
      "gkEsc(j.guest_hours) + ` <#RGK_61#></button>`" in gk and "' <#RGK_61#></button>'" not in gk)

# ---- the secret-masking helpers, compiled on the host (S-C1-1 / S-C2-2)
CC = shutil.which("gcc") or shutil.which("cc")
a = web.find("#define RSEC_MASK")
# the table and helpers end at the first ej hook after them (the default-password MD5 hook sits there since the
# remainder pass; ej hooks need httpd's webs_t and are not part of the host harness)
b = min([x for x in (web.find("static int ej_reaper_default_pw_md5("), web.find("static int ej_reaper_masked_list(")) if x > a] or [-1])
c = web.find("static int rsec_split(")
d = web.find("/* called for every posted name in validate_apply()")
check("web.c carries the masking table and helpers, the ej hook row and the validate_apply() call",
      0 < a < b < c < d and '{ "reaper_masked_list", ej_reaper_masked_list}' in web
      and "value = reaper_rsec_unmask(wp, name, value, rsec_buf, sizeof(rsec_buf));" in web
      and web.find("value = reaper_rsec_unmask(") < web.find("if((ckn_ret = nvram_check(name, value, t, dec_passwd)) == 1)"))
if not CC:
    print("note: no host compiler - the mask/unmask run is skipped")
elif 0 < a < b < c < d:
    harness = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const char *nvram_safe_get(const char *k) { (void)k; return ""; }
''' + web[a:b] + web[c:d] + r'''
static int bad;
#define T(name, cond) do { if (!(cond)) { printf("FAIL %s\n", name); bad++; } } while (0)
static const struct rsec_list *L(const char *n) { return rsec_of(n); }
int main(void)
{
	char out[8200], buf[8200];
	rsec_mask(L("vpn_serverx_clientlist"), "<alice>pw1<bob>pw2<carol>", out, sizeof(out));
	T("mask users", !strcmp(out, "<alice>********<bob>********<carol>"));
	rsec_mask(L("vpnc_clientlist"), "<home>PPTP>vpn.example>u>secret>1>5<work>L2TP>w.example>v>s2>0>6", out, sizeof(out));
	T("mask profiles", !strcmp(out, "<home>PPTP>vpn.example>u>********>1>5<work>L2TP>w.example>v>********>0>6"));
	rsec_mask(L("ipsec_profile_1"), "4>Host-to-Net>null>null>wan>>1>MyPskHere>null>null>1>", out, sizeof(out));
	T("mask psk", !strcmp(out, "4>Host-to-Net>null>null>wan>>1>********>null>null>1>"));
	rsec_mask(L("ipsec_profile_1"), "4>Host-to-Net>null>null>wan>>1>>null", out, sizeof(out));
	T("empty psk stays empty", !strcmp(out, "4>Host-to-Net>null>null>wan>>1>>null"));
	T("unmask by key", !strcmp(rsec_unmask(L("vpn_serverx_clientlist"), "<alice>********<dave>new<bob>********", "<alice>pw1<bob>pw2", buf, sizeof(buf)), "<alice>pw1<dave>new<bob>pw2"));
	T("unmask by position when the key changed", !strcmp(rsec_unmask(L("pptpd_clientlist"), "<alice2>********", "<alice>pw1", buf, sizeof(buf)), "<alice2>pw1"));
	T("unmask: no stored row leaves the field empty, never the mask", !strcmp(rsec_unmask(L("pptpd_clientlist"), "<a>x<b>y<zed>********", "<a>x<b>y", buf, sizeof(buf)), "<a>x<b>y<zed>"));
	T("unmask profiles by four keys", !strcmp(rsec_unmask(L("vpnc_clientlist"), "<work>L2TP>w.example>v>********>0>6<home>PPTP>vpn.example>u>********>1>5",
		"<home>PPTP>vpn.example>u>secret>1>5<work>L2TP>w.example>v>s2>0>6", buf, sizeof(buf)), "<work>L2TP>w.example>v>s2>0>6<home>PPTP>vpn.example>u>secret>1>5"));
	T("unmask psk", !strcmp(rsec_unmask(L("ipsec_profile_1"), "4>Host-to-Net>null>null>wan>>1>********>null>10.10.10>1", "4>Host-to-Net>null>null>wan>>1>MyPskHere>null>10.10.11>1", buf, sizeof(buf)),
		"4>Host-to-Net>null>null>wan>>1>MyPskHere>null>10.10.10>1"));
	T("a stored mask is never handed back as a secret", !strcmp(rsec_unmask(L("pptpd_clientlist"), "<a>********", "<a>********", buf, sizeof(buf)), "<a>"));
	T("a typed password passes through", !strcmp(rsec_unmask(L("pptpd_clientlist"), "<a>typed", "<a>old", buf, sizeof(buf)), "<a>typed"));
	printf(bad ? "harness: %d failed\n" : "harness: all passed\n", bad);
	return bad != 0;
}
'''
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "h.c"); exe = os.path.join(td, "h")
        open(p, "w").write(harness)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-o", exe, p], capture_output=True, text=True)
        check("the masking helpers compile cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr[-600:])
        if r.returncode == 0:
            o = subprocess.run([exe], capture_output=True, text=True)
            check("mask / unmask round trip: users, profiles, the PSK; by key, by position, missing row, a stored mask, typed text", o.returncode == 0, o.stdout)

# ---- the performance items (owner 2026-10-25 PM: "fix these performance findings as well before you build _r36")
inj, nx, sio, nvh = read("httpd/reaper_inject.c"), read("dnsmasq/src/reaper_nx.c"), read("shared/reaper_store_io.h"), read("rc/reaper_nv.h")
shell, shr, encp, logp, qos = read("www/reaper_shell.asp"), read("www/Reaper_Wallguard.asp"), read("www/Reaper_EncryptedDNS.asp"), read("www/Reaper_Log.asp"), read("www/Reaper_QoS.asp")
vc, vs, vst, v6, inet = read("www/Reaper_VPNClient.asp"), read("www/Reaper_VPNServer.asp"), read("www/Reaper_VPNStatus.asp"), read("www/Reaper_IPv6Setup.asp"), read("www/Reaper_Internet.asp")
check("Q-A-1 update.sh: one awk parses a list (CR strip and the name rule inside it) - no tr, no grep pass",
      "rw_dom() { awk 'function ok(d) { return d ~ /^[a-z0-9]([a-z0-9-]{0,62}\\\\.)+[a-z][a-z0-9-]{0,62}$/ }" in rwd and "NF == 1 { print tolower($1) }' | grep -E" not in rwd
      and "rw_dom() { tr -d" not in rwd)
check("Q-A-2 update.sh: per-feed kept / cut counts come from one pass each ($DN.kc / $DN.cc), not a pass over the list per feed",
      "c[a[i]]++ } END { for (i in c) print i, c[i] }' $DN.k > $DN.kc" in rwd and "_kept=$(awk -v id=$_id '$1 == id { print $2; exit }' $DN.kc)" in rwd
      and "_cut=$(awk -v id=$_id '$1 == id { print $2; exit }' $DN.cc)" in rwd and "for(i=1;i<=n;i++) if(a[i]==id) c++} END{print c+0}' $DN.k" not in rwd)
check("Q-A-4 update.sh: one pass filters, dedupes and counts; the list keeps its order (the downgrade copy sorts); the snapshot is parsed once per copy; the dead merged copy is gone",
      "awk -v CF=$DN.c 'length($1) > 253 { lg++; next }" in rwd and "END { print cov + 0, lg + 0 > CF }' $DN.o > $DN.u" in rwd and "read DC DLONG < $DN.c" in rwd
      and "$DN.m $DN.f > $DN.k\\n" in rwd and "sort $DN.k | awk '{ if ($1 != c)" in rwd and "$DN.v $DN.v" not in rwd and "awk 'length($1) <= 253' $DN.o" not in rwd
      and "_sid=\\\"$(date -r \\\"$2\\\" +%s 2>/dev/null) $(wc -c < \\\"$2\\\" 2>/dev/null | tr -d ' ')\\\"" in rwd
      and "cat $RW_DNSC.$1.last >> $DN" not in rwd and "DN=$TMP.dn; : > $DN" not in rwd and "$RW_DNSC.*.src" in rwd)
check("Q-A-3 boot: the table rebuild is detached (one at a time), the include is handed out while it runs, the script logs its own failure; dnsmasq is quiet about a table that is not there yet",
      "static void rw_nx_rebuild_bg(void)" in rwd and '_eval(argv, ">/dev/null", 0, &pid)' in rwd and "kill(pid, 0) == 0" in rwd and 'RW_DIR "/nx.rebuild.pid"' in rwd
      and "rw_nx_rebuild_bg();" in rwd and 'eval("sh", "-c", (char *)rw_nx_rebuild_sh)' not in rwd
      and rwd.count("the /jffs copy would not build into a table - blocking nothing until the next update") == 2
      and "switch (wallguard_table_refresh(&nx.t, daemon->reaper_nx_db))" in nx and "    case -1:" in nx and "warned" not in nx)
# ---- the remainder pass (owner 2026-10-25 late: "review and correct the remainder of the items left")
shc, sdb, sdb2, dsh, stio, tmps, rcsh, encc, rtd = (read("wallguard/wallguardc.c"), read("wallguard/wallguard_db.h"), read("dnsmasq/src/wallguard_db.h"),
                                                   read("dnsmasq/src/wallguard.c"), read("shared/reaper_store_io.h"), read("shared/reaper_tmpsafe.c"),
                                                   read("rc/wallguard.c"), read("rc/encdns.c"), read("rtrafd/rtrafd.c"))
check("Q-A-3b wallguardc reads the feeds list itself (--kfile/--kids); update.sh and the boot rebuild use it, no split files",
      "static void read_kfile(const char *file, struct src *kid, int nk, int all_sub)" in shc and '"--kids"' in shc
      and '--kfile $DN.k --kids \\"$RW_DIDS other $RW_DCUST\\"' in rwd and '--kfile $T.k --kids \\"" RW_DIDS_STR " other legacy " RW_DCUST_STR "\\"' in rwd
      and "$DN.l." not in rwd and "$T.l." not in rwd)
check("Q-A-8 the Wallguard policy reads the network table once, and identical policy / DoH-name files are not rewritten",
      "int mread = 0;" in rcsh and "get_mtlan(pmtl, &msz);" in rcsh and rcsh.count("get_mtlan(") == 1
      and "return reaper_write_changed(path, text, strlen(text), 0644);" in rcsh and "reaper_write_changed(EDNS_CONF, b, len, 0644)" in encc
      and "int reaper_write_changed(const char *path, const void *data, size_t len, mode_t mode)" in tmps)
check("Q-A-9 one mapper and one label walk in wallguard_db.h (both copies byte-identical); dnsmasq's two readers and wallguardc use them",
      sdb == sdb2 and "static inline int wallguard_walk(" in sdb and "static inline int wallguard_table_refresh(struct wallguard_table *t, const char *path)" in sdb
      and "wallguard_table_refresh(&sh.t, p)" in dsh and "mmap(" not in dsh and "mmap(" not in nx and "wallguard_hash(s, n)" not in nx
      and "wallguard_walk(&nx.t.v, name, bits, at, &n, 1)" in nx and "wallguard_table_refresh(&t, path)" in shc)
check("Q-A-10 one append opener in the store helper", "static inline int rstore_open_append(" in stio and stio.count("renameat(dfd, name, dfd, old)") == 1)
check("Q-A-11 dead locals and parameters gone",
      "char tmp[160];" not in rtd[rtd.find("static void db_save("):rtd.find("static void db_save(") + 600] and "(void)now;" not in dsh
      and 'wallguard_append("live", WALLGUARD_LIVE_MAX, line, n, 1);' in dsh and '!strcmp(leaf, "live")' not in dsh)
check("Q-A-12 rednsd's build outputs are ignored by git", os.path.isfile(os.path.join(SRC, "rednsd", ".gitignore")))
check("Q-A-5 rstore ring: streaming line count, a tenth of slack before the trim, the file read into memory for the trim only",
      "lines <= maxlines + maxlines / 10" in sio and "chunk[16384]" in sio and "lseek(fd, 0, SEEK_SET)" in sio)
check("Q-A-6 rwatch review: the single-line settings come from ONE guarded nvram show (_nvs, 0600 temp); a hung read skips the tick; the hashed ones stay on _nv",
      '"_nvs() {\\n"' in nvh and "(umask 077; set -C; : > \\\"$_f\\\")" in nvh and "REAPER_NVS_HELPER" in rw
      and "if _nvs $RV_NV_S > $RV_TMP/review.nvs; then" in rw and ": > $RV_TMP/review.nvfail" in rw
      and "if [ -f $RV_TMP/review.nvfail ]; then rm -f $RV_TMP/review.nvfail $RV_TMP/review.walk; return 1; fi" in rw
      and "for k in $RV_NV_S; do" not in rw and "for k in $RV_NV_H; do v=\\\"$(_nv $k)\\\"" in rw)
check("Q-A-7 rwatch: an existing since-stamp is not re-offered", '[ -f \\"$BASE/$_ds.since\\" ] || /usr/sbin/rstore stamp' in rw)
_ro = inj[inj.find("void reaper_output("):]
check("Q-B-3 / Q-B-4 inject: one copy of each piece, written per mode - stock pages get no banner loader, native pages the small bounce (no SUP map), gate and banner-only pages keep the banner",
      "static const char RP_SECBANNER[] = REAPER_SECBANNER_JS;" in inj and "#define REAPER_NATIVE_JS" in inj
      and "static const char REAPER_BLOCK[]" not in inj and inj.count("REAPER_SECBANNER_JS;") == 1
      and "case 2:\n\t\t\tRP_PUT(conn_fp, RP_NATIVE_JS);" in _ro and "case 3:\n\t\t\tRP_PUT(conn_fp, RP_CSS_LINK);\n\t\t\tRP_PUT(conn_fp, RP_SECBANNER);" in _ro
      and "case 5:\n\t\t\tRP_PUT(conn_fp, RP_SECBANNER);" in _ro and "RP_PUT(conn_fp, RP_BOUNCE_HEAD);\n\t\t\tfwrite(sup, 1, sl, conn_fp);" in _ro
      and 'if(self===top){var rp=location.pathname.split(\\"/\\").pop()||\\"index.asp\\";' in inj)
check("Q-B-6 inject: the gone-page file test runs for .asp names only", 'if (ext && !strcasecmp(ext, ".asp") && access(file, R_OK) != 0) {' in inj)
enc_h = web[web.find("do_reaper_encdns_cgi(char *url, FILE *stream)"):web.find("do_reaper_encdns_cgi(char *url, FILE *stream)") + 7000]
check("Q-B-7 encdns status: one pidof + kill, one shell for both reject counters, one for both set sizes",
      'int rpid = pidof("rednsd");' in enc_h and "kill(rpid, SIGUSR1);" in enc_h and 'pids("rednsd")' not in enc_h and 'killall("rednsd"' not in enc_h
      and 'renc_rejects("iptables -nvxL REAPER_EDNS 2>/dev/null; ip6tables -nvxL REAPER_EDNS 2>/dev/null", &r853, &r443);' in enc_h
      and 'popen("ipset list -t redns_doh 2>/dev/null; echo --; ipset list -t redns_doh6 2>/dev/null", "r")' in web and "renc_set_size(" not in web
      and "renc_set_sizes(&n4, &n6);" in enc_h)
wg_h = web[web.find("wgsc_status_loop:") - 600:web.find("wgsc_status_loop:")]
check("Q-C1-2 web.c: no sync() after wg show (it flushed every filesystem per poll)", 'system(buf);' in wg_h and "sync();" not in wg_h and "no sync() - stock flushed every filesystem" in wg_h)
check("Q-C2-2 shell: no jquery.js, state.js or require.js; menuTree.js fetched as text and lifted by ReaperAddons.fromText; the static fallback stays",
      '"/js/jquery.js"' not in shell and '"/state.js"' not in shell and "require([" not in shell
      and "x.open('GET','/require/modules/menuTree.js?_='" in shell and "res=ReaperAddons.fromText(x.responseText||'')" in shell
      and "ad=[{menuName:'', index:'menu_Addons', tab:addons.entries.map(" in shell and "function railFallback(){" in shell and "setTimeout(function(){ go(null); }, 4000);" in shell)
check("Q-C2-3 shell pills: one request for both hooks, 30 s, hidden gate, visibilitychange",
      "hook=get_clientlist()%3bget_cfg_clientlist()" in shell and "setInterval(pollPills, 30000)" in shell and "function pollPills(){\n    if(document.hidden) return;" in shell
      and "document.addEventListener('visibilitychange', function(){ if(!document.hidden) pollPills(); });" in shell)
check("Q-C2-7 shell: the overlay anchor is measured once per animation frame",
      "raf=window.requestAnimationFrame(function(){ raf=0; anchorNow(); });" in shell and "function anchorNow(){" in shell and "window.reaperAnchorOverlays=anchor;" in shell)
check("Q-C2-4 Wallguard / Encrypted DNS: hidden gate + visibilitychange; the Wallguard list table and target menus repaint only on a change",
      "setInterval(function(){ if(!document.hidden) shStatus(); }, 15000);" in shr and "function(){ if(!document.hidden) shStatus(); });" in shr
      and "if(sl !== shSigLists){ shSigLists = sl; shPaintLists(); }" in shr and "if(stg !== shSigTargets){ shSigTargets = stg; shPaintTargets(); }" in shr
      and "setInterval(function(){ if(!document.hidden) encGet(); }, 10000);" in encp and "function(){ if(!document.hidden) encGet(); });" in encp)
check("Q-C2-5 Log: the auto-refresh is 10 s", "if (!document.hidden) load(false); }, 10000);" in logp and "load(false); }, 5000);" not in logp)
check("Q-C2-6 QoS: class names read once per render, relabelled in place on input, no second boot render",
      "function prioOptions(cur, names){" in qos and "pn = prioNames();" in qos and "prioOptions(r.prio, pn)" in qos and "function prioRelabel(){" in qos
      and "addEventListener('input', function(){ if (sel === '11') prioRelabel(); });" in qos and "pollStats(); fetchPresets(); ohInit();" in qos)
check("Q-C1-1 VPN Client: 10 s poll, hidden gate, visibilitychange, instance strips rebuilt on a state change only",
      vc.count("POLL_T = setTimeout(poll, 10000);") == 2 and "if (document.hidden){ POLL_T = setTimeout(poll, 10000); return; }" in vc
      and "if (!document.hidden && POLL_T){ clearTimeout(POLL_T); poll(); }" in vc
      and "if (sig !== INST_SIG){ INST_SIG = sig; if (TAB_ON.ovpn) ovInst(); if (TAB_ON.wg) wgInst(); }" in vc and "setTimeout(poll, 5000)" not in vc)
check("Q-C1-4 VPN Client: ppSync redraws the profile table only when its three inputs changed; the no-op show loop is gone",
      "if (sig !== PL_SIG){ PL_SIG = sig; plDraw(); }" in vc and "['r_pp_proto', 'r_pp_server', 'r_pp_user', 'r_pp_pass', 'r_pp_dns', 'r_pp_defroute'].forEach" not in vc)
check("Q-C1-2 VPN Server: only the open tab is polled, a tab switch polls at once, poll-driven tables are rewritten on a change only",
      "var t = TAB_CUR;" in vs and "if (TAB_ON.wg && t === 'wg') pollWg();" in vs and "if (was && was !== t) tick();" in vs
      and "function setHtml(id, h){ if (LASTH[id] === h) return; LASTH[id] = h; q(id).innerHTML = h; }" in vs
      and all(("setHtml('%s'," % i) in vs for i in ("ousersbody", "oconnbody", "wgpeersbody", "ipconnbody", "ppusersbody")))
check("Q-C1-3 VPN Status: the poll carries state keys only; WireGuard dumps per open tab; a tab switch polls",
      "['state', 'errno', 'rip'].forEach(function(k){ POLL_KEYS.push('vpn_client'" in vst and "['enable', 'rip'].forEach(function(k){ POLL_KEYS.push('wgc'" in vst
      and "'desc', 'addr', 'port', 'proto', 'rgw'" not in vst and "else if (CUR_TAB === 'servers'){" in vst and "if (CUR_TAB !== 'clients') continue;" in vst
      and "if (was && was !== t && ROUTING) poll();" in vst)
check("Q-C1-4 IPv6 / Internet: the live polls run every 10 s and not while hidden",
      "if (document.hidden || svc() !== ORIG || ORIG === 'disabled'){ setTimeout(poll, 10000); return; }" in v6 and "sync(); setTimeout(poll, 10000);" in v6
      and "if (document.hidden || !(NVU[UNIT] && NVU[UNIT].proto === 'dslite'" in inet and "setTimeout(poll, 10000);\n  };" in inet
      and v6.count("setTimeout(poll, 3000)") == 1 and inet.count("setTimeout(poll, 3000)") == 1)   # the one left is each page's boot kick-off

if fails:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
print("PASS test_review_2026_10_24_fixes")
