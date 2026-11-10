#!/usr/bin/env python3
"""The firewall log path: every log rule through one target helper (NFLOG plan section 7, 2026-11-08).

Owner: all firewall log sources go through NFLOG, with a fallback to syslog with a limiter "in case something
happens". shared/reaper_fwlog.h gives every emitter its target text:
  - NFLOG to the collector (rflogd), one group per source: 40 stock, 41 Warden, 42 the closed blob, 43 the rules engine;
  - else LOG behind `-m limit --limit 10/s --limit-burst 50` at --log-level 5 (kept by syslogd at log_level 6, off the
    serial console). The choice is /tmp/reaper/fwlog/path = "nflog", written by rc; absent / unreadable / a link = LOG.
Sites: the 12 stock logaccept / logdrop bodies (rc/firewall.c), Warden RW_SDROP / RW_DROP / RW_ODROP (rc/rwarden.c),
the rules engine's per-rule log (its own 6/min bucket on the fallback) and nat intercept / forward (rc/reaper_fw.c),
and the closed write_extra_filter / 6 output: its two LOG lines are rerouted in rc's copy pass, every other line passes
byte for byte; the raw IPv6 call is wrapped like the IPv4 one. This replaces test_fw_log_limit_2026_11_07.py
(REAPER_LOG_LIMIT, the rate limit alone). The real reaper_extra_log_reroute() is host-compiled and run.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "firewall.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
def rd(rel): return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def code_only(t):
    """C text with comments blanked (strings kept)"""
    out, i, n = [], 0, len(t)
    while i < n:
        if t.startswith("/*", i):
            j = t.find("*/", i + 2); j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", t[i:j])); i = j
        elif t.startswith("//", i):
            j = t.find("\n", i); j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif t[i] in "\"'":
            q, j = t[i], i + 1
            while j < n and t[j] != q:
                j += 2 if t[j] == "\\" else 1
            out.append(t[i:j + 1]); i = j + 1
        else:
            out.append(t[i]); i += 1
    return "".join(out)

# ---------------------------------------------------------------- the helper
h = rd("shared/reaper_fwlog.h")
check("reaper_fwlog.h: four groups 40-43", all(("#define %s\t%d" % (k, v)) in h for k, v in
      (("RFL_G_STOCK", 40), ("RFL_G_WARDEN", 41), ("RFL_G_BLOB", 42), ("RFL_G_REAPER", 43))))
check("reaper_fwlog.h: fallback = 10/s burst 50 at level 5",
      '#define RFL_LIMIT\t"-m limit --limit 10/s --limit-burst 50 "' in h and '#define RFL_LEVEL\t"5"' in h)
check("reaper_fwlog.h: the NFLOG form carries the flood ceiling, 10000/s (the most xt_limit takes)",
      '#define RFL_CEIL\t"-m limit --limit 10000/s --limit-burst 10000 "' in h
      and 'RFL_CEIL "-j NFLOG --nflog-group %d' in h)
check("reaper_fwlog.h: the state file is read without following a link",
      "O_RDONLY | O_NOFOLLOW | O_CLOEXEC" in h and '#define RFL_PATH\tRFL_DIR "/path"' in h)
check("reaper_fwlog.h: NFLOG form names group and prefix only (copy length is the collector's)",
      '"-j NFLOG --nflog-group %d --nflog-prefix \\"%s\\""' in h and "nflog-range" not in code_only(h))

rch = rd("rc/rc.h")
check("rc.h: REAPER_LOG_LIMIT is retired (no define left)", "#define REAPER_LOG_LIMIT" not in rch)

# ---------------------------------------------------------------- firewall.c
fw = rd("rc/firewall.c"); fwc = code_only(fw)
check("firewall.c includes reaper_fwlog.h", "#include <reaper_fwlog.h>" in fw)
calls = re.findall(r'rfl_stock_chain\((fp|fp_ipv6), "(logaccept|logdrop)", "(ACCEPT|DROP) ", "(ACCEPT|DROP)"\);', fw)
check("firewall.c: 12 stock bodies through rfl_stock_chain (3 functions x v4/v6 x accept/drop)",
      len(calls) == 12 and sorted(set(calls)) == [("fp", "logaccept", "ACCEPT", "ACCEPT"), ("fp", "logdrop", "DROP", "DROP"),
                                               ("fp_ipv6", "logaccept", "ACCEPT", "ACCEPT"), ("fp_ipv6", "logdrop", "DROP", "DROP")],
      calls)
check("firewall.c: the IPv6 bodies still stand under their `if (ipv6_enabled())` as ONE statement",
      fw.count("\tif (ipv6_enabled())\n\trfl_stock_chain(fp_ipv6,") == 4)
check("firewall.c: the blob's v4 output is rerouted before the copy",
      "\twrite_extra_filter(t);\n\tfclose(t);\n\treaper_extra_log_reroute(REAPER_EXTRA_TMP);" in fw
      and fw.index("reaper_extra_log_reroute(REAPER_EXTRA_TMP)") < fw.index("dropped = reaper_nf_copy_supported(REAPER_EXTRA_TMP"))
check("firewall.c: both raw write_extra_filter6(fp_ipv6) calls are wrapped",
      fw.count("\t\treaper_write_extra_filter6(fp_ipv6);\n") == 2 and "\t\twrite_extra_filter6(fp_ipv6);" not in fw)
check("firewall.c: the v6 wrapper reroutes, then copies with v6=1",
      "reaper_extra_log_reroute(REAPER_EXTRA6_TMP);\n\tdropped = reaper_nf_copy_supported(REAPER_EXTRA6_TMP, fp, 1, 0," in fw)

# ---------------------------------------------------------------- rwarden.c
rw = rd("rc/rwarden.c")
check("rwarden.c includes reaper_fwlog.h", "#include <reaper_fwlog.h>" in rw)
# Warden's apply.sh and the rules engine's scripts are RE-RUN by every restart_firewall: their log rules pick the
# target when they run (the state file), so a log-path change needs no regeneration - and never touches the rules
# engine's armed candidate or rollback.
for ipt in ("iptables", "ip6tables"):
    check("rwarden.c: %s RW_DROP / RW_ODROP chosen at run time, group 41, still gated by rwarden_log" % ipt,
          ('if (nvram_match("rwarden_log", "1"))\n\t\trfl_sh_rule(f, "%s -A RW_DROP", RFL_G_WARDEN, "REAPER-WARDEN ", NULL);' % ipt) in rw
          and ('if (nvram_match("rwarden_log", "1"))\n\t\t\trfl_sh_rule(f, "%s -A RW_ODROP", RFL_G_WARDEN, "REAPER-WARDEN-OUT ", NULL);' % ipt) in rw)
    check("rwarden.c: %s log rules precede their DROP" % ipt,
          rw.find('rfl_sh_rule(f, "%s -A RW_DROP"' % ipt) < rw.find('"%s -A RW_DROP -j DROP' % ipt)
          and rw.find('rfl_sh_rule(f, "%s -A RW_ODROP"' % ipt) < rw.find('"%s -A RW_ODROP -j DROP' % ipt))
sd = rw[rw.index("static void rw_emit_self_chain"):rw.index("rw_emit_local_dst(f, ipt, \"RW_SELF\", v6);")]
check("rwarden.c: RW_SDROP (always logs) chosen at run time, group 41, before its DROP; formats agree",
      'snprintf(sd, sizeof(sd), "%s -A RW_SDROP", ipt);' in sd
      and 'rfl_sh_rule(f, sd, RFL_G_WARDEN, "REAPER-WARDEN-SELF ", NULL);' in sd
      and sd.index("rfl_sh_rule(f, sd") < sd.index('"%s -A RW_SDROP -j DROP\\n"')
      and "fprintf(f,\n\t  \"%s -A RW_SDROP -j DROP\\n\"\n\t  \"%s -N RW_SELF; %s -F RW_SELF\\n\"\n"
          "\t  \"%s -A RW_SELF -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN\\n\"\n"
          "\t  \"%s -A RW_SELF -o lo -j RETURN\\n\",\n\t  ipt, ipt, ipt, ipt, ipt);" in sd, sd)

# ---------------------------------------------------------------- reaper_fw.c
rf = rd("rc/reaper_fw.c")
check("reaper_fw.c includes reaper_fwlog.h", "#include <reaper_fwlog.h>" in rf)
check("reaper_fw.c: the generated script defines RFLR after RFWR (a failed log rule is still counted)",
      rf.index('"RFWR() {') < rf.index('"RFLR() {') and 'RFWR \\"$@\\" " RFL_CEIL "-j NFLOG --nflog-group $_g' in rf
      and 'else RFWR \\"$@\\" $_l -j LOG --log-prefix \\"$_p\\" --log-level " RFL_LEVEL "; fi; }' in rf
      and '"RFL_NF=0; [ \\"$(cat " RFL_PATH " 2>/dev/null)\\" = nflog ] && RFL_NF=1\\n"' in rf)
check("reaper_fw.c: per-rule log through RFLR, group 43, its 6/min bucket on the LOG path only",
      '"RFLR %d \'REAPER-FW:%d \' \'-m limit --limit 6/min --limit-burst 12 \' %s -A %s%s%s%s\\n",\n\t\t        RFL_G_REAPER, ridx, ipt, ch, pre, schedfrag, ratefrag);' in rf)
check("reaper_fw.c: nat intercept / forward through RFLR, group 43, the 10/s bucket on the LOG path",
      '"RFLR %d \'REAPER-ICPT6 \' \'" RFL_LIMIT "\' ip6tables -t nat -A %s' in rf
      and '"%sRFLR %d \'%s\' \'" RFL_LIMIT "\' iptables -t nat -A %s"' in rf
      and 'fwdmode ? "REAPER-FWD " : "REAPER-ICPT "' in rf and "rfl_tgt(" not in code_only(rf))

# ---------------------------------------------------------------- rc wiring
fl = rd("rc/reaper_fwlog.c"); sv = rd("rc/services.c"); wd = rd("rc/watchdog.c"); mk = rd("rc/Makefile")
check("rc: reaper_fwlog.o built; rc.h declares rflog_sync / stop_rflogd / reaper_fwlog_watch",
      "OBJS += reaper_fwlog.o\n" in mk and "extern void rflog_sync(void);" in rch and "extern void stop_rflogd(void);" in rch
      and "extern void reaper_fwlog_watch(void);" in rch)
check("services.c: started at boot after rdnsmap, stopped with the cluster, an rflog verb, the logger verb refreshes it",
      "\tstart_rdnsmap();\t/* reaper v3.3.4 passive DNS name map (Flow Explorer destination names) */\n\trflog_sync();" in sv
      and "\tstop_rdnsmap();\t/* reaper v3.3.4 passive DNS name map */\n\tstop_rflogd();" in sv
      and 'strcmp(script, "rflog") == 0)' in sv and "if(action & RC_SERVICE_START) rflog_sync();" in sv
      and 'start_logger();\n\t\t\tif (pids("rflogd"))\n\t\t\t\trflog_sync();' in sv)
check("watchdog.c: the collector check runs every tick, before the 30 s gate",
      "watchdog_period2 = (watchdog_period2 + 1) % 10;\n#endif\n\treaper_fwlog_watch();" in wd
      and wd.index("reaper_fwlog_watch();") < wd.index("\tif (watchdog_period)\n\t\treturn;"))
check("reaper_fwlog.c: NFLOG only with the kernel's target AND a collector bound; a bind error is not retried",
      "rfl_set_path(alive == 1," in fl and "if (!rfl_kernel_ok()) {" in fl and r'\"bind_error\":' in fl
      and "alive >= 0 && tick % 60 == 0" in fl and '"/proc/net/ip_tables_targets"' in fl)
check("reaper_fwlog.c: down to LOG at once, back up to NFLOG not within 60 s of a change, firewall re-run only once built",
      "if (nflog && last && now - last < RFL_UPGUARD && now >= last)" in fl and "#define RFL_UPGUARD\t60" in fl
      and 'if (f_exists(REAPER_FW_BUILT_MARK))\n\t\tnotify_rc("restart_firewall");' in fl)
check("reaper_fwlog.c: a dead collector on the NFLOG path is restarted within 2-4 s",
      "if (++tick % 2 || !is_routing_enabled())" in fl and 'if (alive != 1 && now - kicked >= 4) {' in fl
      and 'notify_rc("restart_rflog");' in fl)
check("reaper_fwlog.c: the remote target is an address only, the host name sanitised",
      'strspn(ip, "0123456789abcdefABCDEF.:") == strlen(ip)' in fl and "isalnum((unsigned char)pid[i])" in fl)

# ---------------------------------------------------------------- the GUI reads the collector (area d)
web = rd("httpd/web.c"); fwp = rd("www/Reaper_Firewall.asp"); lgp = rd("www/Reaper_Log.asp")
fl_fn = web[web.index("fw_line_is_fwlog(const char *line)\n{"):]
fl_fn = fl_fn[:fl_fn.index("\n}\n")]
check("web.c: fw_line_is_fwlog takes the collector's ISO-stamped lines and the blob's DROP_DNS / DROP_IP",
      "isdigit((unsigned char)line[0]) && line[4] == '-' && line[10] == 'T'" in fl_fn
      and 'strstr(k, "DROP_DNS IN=")' in fl_fn and 'strstr(k, "DROP_IP IN=")' in fl_fn and 'strstr(k, "REAPER-WARDEN")' in fl_fn)
dr = web[web.index('if (strcmp(action, "drops") == 0) {'):]
dr = dr[:dr.index("websWrite(stream, \"{\\\"ok\\\":1,\\\"wlog\\\"")]
check("web.c: drops reads the collector's ring and syslog, the source in use last (newest lines kept)",
      dr.index("if (rfl_nflog()) {") < dr.index('RFL_DIR "/current.log"') and dr.count('RFL_DIR "/current.log"') == 2
      and dr.count("get_syslog_fname(0)") == 2)
check("web.c: action=fwlog_stats - the path, running, the collector's stats only when they are a JSON object",
      'if (strcmp(action, "fwlog_stats") == 0) {' in web and 'O_RDONLY | O_NOFOLLOW | O_CLOEXEC' in web
      and "(n > 1 && sb[0] == '{' && sb[n - 1] == '}') ? sb : \"null\"" in web and '#include "reaper_fwlog.h"' in web)
check("Firewall page: ISO times in the viewer, the collector status line (running counts / fallback warning)",
      "/^(\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\d|\\w{3}\\s+\\d+\\s+[\\d:]+)/" in fwp and 'id="l_coll"' in fwp
      and "action=fwlog_stats&http_id=" in fwp and "`<#RFW_413#>`.replace('%1'" in fwp and "e.textContent=`<#RFW_414#>`" in fwp)
check("System Log page: a Firewall view through the firewall reader, with the page token, saying where its lines come from",
      'data-v="fw"><#RLOG_102#></button>' in lgp and "'/reaper_fw.cgi?action=drops&http_id=' + encodeURIComponent(HID)" in lgp
      and "lastText = {sys: null, login: null, fw: null}" in lgp and "(view === 'fw' ? ' - ' + `<#RLOG_103#>` : '')" in lgp)
wd_ = os.path.join(SRC, "www")
pk_bad, pk_lines = [], set()
for d in sorted(f for f in os.listdir(wd_) if f.endswith(".dict") and f != "temp.dict"):
    t = open(os.path.join(wd_, d), encoding="utf-8").read()
    pk_lines.add(t.count("\n"))
    m = re.search(r"^RFW_412=.+\n^RFW_413=(.+)\n^RFW_414=(.+)\n^RLOG_102=(.+)\n^RLOG_103=(.+)$", t, re.M)
    if not m or not all(x in m.group(1) for x in ("%1", "%2", "%3")) or any(("`" in g or "${" in g) for g in m.groups()):
        pk_bad.append(d)
check("25 packs: RFW_413 / RFW_414 / RLOG_102 / RLOG_103 after RFW_412, %1-%3 kept, lockstep", not pk_bad and len(pk_lines) == 1,
      (pk_bad, pk_lines))

# ---------------------------------------------------------------- the fwlog dataset on the long-term store (_r3 follow-up)
st_pg = rd("www/Reaper_Storage.asp"); rwt = rd("rc/rwatch.c"); dfl = rd("shared/defaults.c")
dsl = '"dev", "traf", "watch", "chq", "fwlog", "slog", "shl", "shh", "dw", "edns", NULL };'
check("web.c: fwlog is a known dataset (store_set) and reports its since + size (store_status)",
      web.count(dsl) == 2 and 'websWrite(stream, "\\"fwlog_bytes\\":%lld,", rdev_dir_bytes(base, "fwlog"));' in web)
check("rwatch: the fwlog dataset gets its collecting-since stamp", "for _ds in dev traf watch chq fwlog slog shl shh dw edns; do" in rwt)
check("defaults: new installs keep the firewall log on the store (existing lists untouched)",
      '{ "reaper_store_ds", "dev,traf,watch,fwlog", CKN_STR64,' in dfl)
# 2026-11-08 (owner, _r4: the row re-flowed the page): the retention text is part of the description, the size cell
# holds the size only (test_quick_fixes_2026_11_08.py pins the layout)
check("Storage page: a USB-only fwlog row showing its own size, its retention in the description",
      "{k:'fwlog', name:`<#RDST_113#>`, write:`<#RDST_114#>` + '; ' + `<#RDST_115#>`, cap:'', usbonly:1}," in st_pg
      and "if(ds.usbonly) cap = (S && S[ds.k + '_bytes']) ? fmtBytes(S[ds.k + '_bytes']) : '&mdash;';" in st_pg
      and "cap += ' - ' + `<#RDST_115#>`" not in st_pg)
rd_bad = []
for d in sorted(f for f in os.listdir(wd_) if f.endswith(".dict") and f != "temp.dict"):
    t = open(os.path.join(wd_, d), encoding="utf-8").read()
    if not re.search(r"^RLOG_103=.+\n^RDST_113=.+\n^RDST_114=.+\n^RDST_115=.+$", t, re.M): rd_bad.append(d)
check("25 packs: RDST_113..115 after RLOG_103", not rd_bad, rd_bad)

# ---------------------------------------------------------------- every limit within what iptables takes
# _r2 (2026-11-08) shipped --limit-burst 20000: iptables' limit match takes 0-10000, so every NFLOG rule was refused
# on the box and the restore fallback left the log chains without a log rule. Read the bounds from the tree's own
# iptables, not from memory, and hold every `-m limit` text Reaper emits to them.
lx = rd("iptables-1.4.x/extensions/libxt_limit.c")
mb = re.search(r'\.name = "limit-burst".*?\.max = (\d+)', lx, re.S)
xh = ""
for cand in ("iptables-1.4.x/include/linux/netfilter/xt_limit.h",):
    if os.path.isfile(os.path.join(SRC, cand)): xh = rd(cand)
ms = re.search(r"#define XT_LIMIT_SCALE\s+(\d+)", xh)
check("iptables bounds found in the tree (libxt_limit.c burst max, xt_limit.h XT_LIMIT_SCALE)", mb is not None and ms is not None,
      (bool(mb), bool(ms)))
if mb and ms:
    bmax, scale = int(mb.group(1)), int(ms.group(1))
    per = {"s": 1, "sec": 1, "second": 1, "m": 60, "min": 60, "minute": 60, "h": 3600, "hour": 3600, "d": 86400, "day": 86400}
    texts = {"shared/reaper_fwlog.h": h}
    for fn in sorted(os.listdir(os.path.join(SRC, "rc"))):
        if fn.endswith(".c") or fn.endswith(".h"):
            texts["rc/" + fn] = rd("rc/" + fn)
    over, seen = [], 0
    for name, t in texts.items():
        for m in re.finditer(r"--limit (\d+)/([a-z]+)(?: --limit-burst (\d+))?", t):
            seen += 1
            rate, unit, burst = int(m.group(1)), m.group(2), int(m.group(3) or 5)
            if unit not in per or rate / per[unit] > scale or burst > bmax:
                over.append("%s: %s" % (name, m.group(0)))
    check("every -m limit Reaper emits is within iptables' bounds (rate <= %d/s, burst <= %d) - %d checked" % (scale, bmax, seen),
          seen >= 4 and not over, over)
    check("the NFLOG flood ceiling is exactly iptables' maximum (10000/s, burst 10000)",
          '#define RFL_CEIL\t"-m limit --limit %d/s --limit-burst %d "' % (scale, bmax) in h)

# ---------------------------------------------------------------- the sweep
left = []
for fn in sorted(os.listdir(os.path.join(SRC, "rc"))):
    if fn.endswith(".c") or fn.endswith(".h"):
        c = code_only(rd("rc/" + fn))
        cl = c.split("\n")
        for m in re.finditer(r"-j LOG\b", c):
            ln = c.count("\n", 0, m.start())
            if "sscanf(" in cl[ln] or "RFLR() {" in cl[ln - 1] or "else RFWR" in cl[ln]:
                continue	# the blob reroute's match pattern / the RFLR function's own LOG branch
            left.append("%s:%d" % (fn, ln + 1))
check("rc/: no -j LOG left in code - every log rule takes the helper's target", not left, left)

# ---------------------------------------------------------------- host run: the reroute and the helper
gcc = shutil.which("gcc") or shutil.which("cc")
a = fw.find("static void reaper_extra_log_reroute(const char *path)\n{")
b = fw.find("\n}\n", a)
if not gcc or a < 0:
    print("skip: no host compiler - the reroute run" if not gcc else "")
    if a < 0: fails.append("reaper_extra_log_reroute not found")
else:
    td = tempfile.mkdtemp()
    try:
        fl = os.path.join(td, "fwlog"); os.mkdir(fl)
        shutil.copy(os.path.join(SRC, "shared", "reaper_fwlog.h"), td)
        csrc = os.path.join(td, "t.c")
        with open(csrc, "w") as fh:
            fh.write('#define RFL_DIR "%s"\n#include "reaper_fwlog.h"\n#include <stdio.h>\n' % fl + fw[a:b + 3] +
                     r'''
int main(int argc, char **argv)
{
	if (argc > 2) { reaper_extra_log_reroute(argv[2]); return 0; }
	rfl_stock_chain(stdout, "logaccept", "ACCEPT ", "ACCEPT");
	puts(rfl_tgt(rfl_nflog(), RFL_G_REAPER, "REAPER-FW:7 ", "-m limit --limit 6/min --limit-burst 12 ", ""));
	return 0;
}
''')
        exe = os.path.join(td, "t")
        r = subprocess.run([gcc, "-std=gnu99", "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, csrc], capture_output=True, text=True)
        check("host: the header and the real reaper_extra_log_reroute() compile with -Wall -Werror", r.returncode == 0, r.stderr)
        blob = ('*filter\n:logdrop_dns - [0:0]\n'
                '-A logdrop_dns -j LOG --log-prefix "DROP_DNS " --log-tcp-sequence --log-tcp-options --log-ip-options\n'
                '-A logdrop_dns -j DROP\n:OUTPUT_DNS - [0:0]\n:logdrop_ip - [0:0]\n'
                '-A logdrop_ip -j LOG --log-prefix "DROP_IP " --log-tcp-sequence --log-tcp-options --log-ip-options\n'
                '-A logdrop_ip -j DROP\n'
                '-A OUTPUT -p udp --dport 53 -m u32 --u32 0>>22&0x3c@8>>15&1=0 -j OUTPUT_DNS\n'
                '-A OUTPUT_DNS -m string --icase --hex-string "|07|example|03|com|00|" --algo bm -j logdrop_dns\n'
                '-A OUTPUT -j OUTPUT_IP\n-A OUTPUT_IP -d 192.0.2.0/24 -j logdrop_ip\n'
                '-A odd -j LOG --log-prefix "ODD " --log-level 4; touch /x\n')
        def run(mode):
            p = os.path.join(td, "blob.txt")
            open(p, "w").write(blob)
            pf = os.path.join(fl, "path")
            if os.path.lexists(pf): os.remove(pf)
            if mode == "nflog": open(pf, "w").write("nflog\n")
            if mode == "link":
                tgt = os.path.join(td, "elsewhere"); open(tgt, "w").write("nflog\n"); os.symlink(tgt, pf)
            subprocess.run([exe, "x", p], check=False)
            o = subprocess.run([exe], capture_output=True, text=True).stdout
            return open(p).read(), o
        if r.returncode == 0:
            out, o = run("log")
            ls, bl = out.split("\n"), blob.split("\n")
            check("reroute, no collector: the two blob LOG lines become the limited LOG, their options kept, level 5",
                  '-A logdrop_dns -m limit --limit 10/s --limit-burst 50 -j LOG --log-prefix "DROP_DNS " --log-tcp-sequence --log-tcp-options --log-ip-options --log-level 5' in ls
                  and '-A logdrop_ip -m limit --limit 10/s --limit-burst 50 -j LOG --log-prefix "DROP_IP " --log-tcp-sequence --log-tcp-options --log-ip-options --log-level 5' in ls, out)
            same = [x for x in bl if "-j LOG" not in x]
            check("reroute: every other blob line passes byte for byte, in order", [x for x in ls if "-j LOG" not in x] == same, out)
            check("reroute: unexpected text after the prefix is not carried into the rule",
                  '-A odd -m limit --limit 10/s --limit-burst 50 -j LOG --log-prefix "ODD " --log-level 5' in ls and "touch" not in out, out)
            check("helper, no collector: stock chain = NEW + limited LOG with the stock options, a NEW counter, the verdict",
                  o.startswith('-A logaccept -m state --state NEW -m limit --limit 10/s --limit-burst 50 -j LOG --log-prefix "ACCEPT " '
                               '--log-tcp-sequence --log-tcp-options --log-ip-options --log-level 5\n'
                               '-A logaccept -m state --state NEW\n-A logaccept -j ACCEPT\n'), o)
            check("helper, no collector: the rules engine keeps its own 6/min bucket",
                  '-m limit --limit 6/min --limit-burst 12 -j LOG --log-prefix "REAPER-FW:7 " --log-level 5' in o, o)
            out, o = run("nflog")
            ls = out.split("\n")
            C = "-m limit --limit 10000/s --limit-burst 10000 "
            check("reroute, collector running: the blob lines go to NFLOG group 42 under the flood ceiling only",
                  ('-A logdrop_dns ' + C + '-j NFLOG --nflog-group 42 --nflog-prefix "DROP_DNS "') in ls
                  and ('-A logdrop_ip ' + C + '-j NFLOG --nflog-group 42 --nflog-prefix "DROP_IP "') in ls
                  and "--limit 10/s" not in out, out)
            check("helper, collector running: stock chain -> NFLOG group 40, rules engine -> group 43, no 6/min cap",
                  o.startswith('-A logaccept -m state --state NEW ' + C + '-j NFLOG --nflog-group 40 --nflog-prefix "ACCEPT "\n')
                  and (C + '-j NFLOG --nflog-group 43 --nflog-prefix "REAPER-FW:7 "') in o and "6/min" not in o, o)
            out, o = run("link")
            check("a symlinked state file is ignored (limited LOG)", "-j NFLOG" not in out and "-j NFLOG" not in o, o)

        # ---- the re-run scripts: Warden's rule line and the rules engine's RFLR, executed by sh with a stub iptables
        sh = shutil.which("sh")
        fmt_c = os.path.join(td, "sh.c")
        fwh = rf[rf.index('\tfprintf(f,\n\t  "RFW_FAIL=0\\n"'):rf.index('fi; }\\n\\n");') + len('fi; }\\n\\n");')]
        fl_dir = os.path.join(td, "fwlog")
        with open(fmt_c, "w") as fh:
            fh.write('#define RFL_DIR "%s"\n#include "reaper_fwlog.h"\nint main(void) { FILE *f = stdout;\n%s\n'
                     'rfl_sh_rule(f, "iptables -A RW_DROP", RFL_G_WARDEN, "REAPER-WARDEN ", NULL);\nreturn 0; }\n' % (fl_dir, fwh))
        gen = os.path.join(td, "gen")
        r2 = subprocess.run([gcc, "-std=gnu99", "-Wall", "-Werror", "-Wno-unused-function", "-o", gen, fmt_c, "-I", td],
                            capture_output=True, text=True)
        check("host: the rules engine's script preamble and a Warden rule line generate", r2.returncode == 0, r2.stderr)
        if r2.returncode == 0 and sh:
            pre = subprocess.run([gen], capture_output=True, text=True).stdout
            stub = os.path.join(td, "bin"); os.mkdir(stub)
            with open(os.path.join(stub, "iptables"), "w") as fh:
                fh.write('#!/bin/sh\nprintf "%s|" "$@" >> "$OUT"; echo >> "$OUT"\n')
            os.chmod(os.path.join(stub, "iptables"), 0o755)
            def runsh(mode):
                pf = os.path.join(fl_dir, "path")
                if os.path.lexists(pf): os.remove(pf)
                if mode: open(pf, "w").write(mode + "\n")
                outf = os.path.join(td, "out.txt"); open(outf, "w").close()
                script = pre + ("RFLR 43 'REAPER-FW:5 ' '-m limit --limit 6/min --limit-burst 12 ' iptables -A REAPER_FWF -s 192.0.2.4\n"
                                "RFLR 43 'REAPER-ICPT ' '" + "-m limit --limit 10/s --limit-burst 50 " + "' iptables -t nat -A REAPER_FWN -p udp --dport 123\n")
                env = dict(os.environ, PATH=stub + os.pathsep + os.environ.get("PATH", ""), OUT=outf)
                subprocess.run([sh, "-c", script], env=env, capture_output=True, text=True)
                return open(outf).read()
            o = runsh("nflog")
            exp = ["-A|RW_DROP|-m|limit|--limit|10000/s|--limit-burst|10000|-j|NFLOG|--nflog-group|41|--nflog-prefix|REAPER-WARDEN |",
                   "-A|REAPER_FWF|-s|192.0.2.4|-m|limit|--limit|10000/s|--limit-burst|10000|-j|NFLOG|--nflog-group|43|--nflog-prefix|REAPER-FW:5 |",
                   "-t|nat|-A|REAPER_FWN|-p|udp|--dport|123|-m|limit|--limit|10000/s|--limit-burst|10000|-j|NFLOG|--nflog-group|43|--nflog-prefix|REAPER-ICPT |"]
            check("scripts, collector running: Warden and the rules engine run NFLOG rules, prefixes intact (one argument each)",
                  o.split("\n")[:3] == exp, o)
            o = runsh("")
            exp = ["-A|RW_DROP|-m|limit|--limit|10/s|--limit-burst|50|-j|LOG|--log-prefix|REAPER-WARDEN |--log-level|5|",
                   "-A|REAPER_FWF|-s|192.0.2.4|-m|limit|--limit|6/min|--limit-burst|12|-j|LOG|--log-prefix|REAPER-FW:5 |--log-level|5|",
                   "-t|nat|-A|REAPER_FWN|-p|udp|--dport|123|-m|limit|--limit|10/s|--limit-burst|50|-j|LOG|--log-prefix|REAPER-ICPT |--log-level|5|"]
            check("scripts, no collector: the same scripts run the limited LOG (rules engine 6/min, intercept 10/s)",
                  o.split("\n")[:3] == exp, o)
    finally:
        shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
