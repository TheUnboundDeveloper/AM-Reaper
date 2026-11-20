#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-17, remediation phase 1 (security and correctness): pins for each fix as it lands.

WHY THIS EXISTS. The 2026-11-17 review found a small set of defects worth fixing before anything else:
  - a board driver's netlink message handler released a message that the kernel's netlink code releases again
    after the handler returns; the handler no longer does, and the family joins the ones a sender needs
    CAP_SYS_ADMIN for;
  - four tunables of the kernel's packet-release thread under /proc were writable by every local user;
  - the Guest Portal's DNS answer builders copied a received frame, and appended an answer record, without
    checking the size of the buffers they write into.

WHAT IT DOES. Reads the real files of the tree, cuts out the functions concerned and checks the order of the
statements in them; compiles the netlink verdict on the host and runs it over every family.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile


def skip(msg):
    print("SKIP: " + msg); sys.exit(77)


SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "coovachilli", "src", "dhcp.c")):
    skip("no router source tree with coovachilli/src/dhcp.c (argv[1] or REAPER_ROUTER_SRC)")
PLAT = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916"))
CC = shutil.which("gcc") or shutil.which("cc")

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))


def rd(path):
    return open(path, encoding="utf-8", errors="surrogateescape").read()


def nocomment(s):
    return re.sub(r"/\*.*?\*/", " ", s, flags=re.S)


def body(src, head):
    """text of the function whose definition line contains `head`: from its opening brace to the first closing
    brace in column 0 (counting braces fails in dhcp.c, where #ifdef branches open a block twice)"""
    i = src.find(head)
    if i < 0:
        return ""
    j = src.find("{", i)
    k = src.find("\n}", j)
    return src[j:k + 2] if j >= 0 and k > j else ""


# ---------------------------------------------------------------- kernel: the board monitor netlink handler
bu = os.path.join(PLAT, "bcmdrivers", "opensource", "char", "board", "bcm963xx", "impl1", "board_util.c")
if os.path.isfile(bu):
    h = nocomment(body(rd(bu), "void kerSysRecvFrmMonitorTask(struct sk_buff *skb)"))
    check("kernel: the board monitor handler is found", bool(h))
    check("kernel: the handler does not release the message (the netlink code does, after it returns)",
          bool(h) and "kfree_skb" not in h and "consume_skb" not in h and "dev_kfree_skb" not in h, h[:300])
else:
    check("kernel: board_util.c present", False, bu)

nl = os.path.join(PLAT, "kernel", "linux-4.19", "net", "netlink", "af_netlink.c")
if os.path.isfile(nl):
    k = rd(nl)
    a, b = k.find("#define REAPER_NL_BRCM_A"), k.find("/* reaper-nl-gate: end */")
    check("kernel: the netlink gate block is found", 0 <= a < b)
    core = nocomment(body(k, "static int netlink_unicast_kernel("))
    check("kernel: the netlink code still releases a message after the kernel-side handler ran",
          "nlk->netlink_rcv(skb);" in core and core.find("consume_skb(skb)") > core.find("nlk->netlink_rcv(skb);") > 0, core[:400])
    if 0 <= a < b and CC:
        tmp = tempfile.mkdtemp(prefix="rev1117p1_")
        code = ("#include <stdio.h>\n#include <stdbool.h>\n#include <errno.h>\n" + k[a:b] + r"""
int main(void)
{
	int p, bad = 0;
	for (p = 0; p < 40; p++) {
		int closed = (p == 22 || p == 23 || p == 25 || p == 29);
		int plain = reaper_nl_closed_verdict(p, false), admin = reaper_nl_closed_verdict(p, true);
		if (admin != 0) { printf("family %d refused with the capability\n", p); bad++; }
		if (closed && plain != -EPERM) { printf("family %d open to every sender\n", p); bad++; }
		if (!closed && plain != 0) { printf("family %d touched\n", p); bad++; }
	}
	return bad ? 1 : 0;
}
""")
        src = os.path.join(tmp, "nl.c"); exe = os.path.join(tmp, "nl")
        open(src, "w").write(code)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, src],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
        ok, out = r.returncode == 0, r.stdout
        if ok:
            r = subprocess.run([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
            ok, out = r.returncode == 0, r.stdout
        check("kernel: families 22, 23, 25 and 29 need CAP_SYS_ADMIN to send; every other family is untouched", ok, out)
        shutil.rmtree(tmp, ignore_errors=True)
    elif not CC:
        print("note: no host compiler - the netlink verdict was not run")
else:
    check("kernel: af_netlink.c present", False, nl)

# ---------------------------------------------------------------- kernel: /proc/skb_free_thread modes
sf = os.path.join(PLAT, "kernel", "bcmkernel", "net", "core", "bcm_skb_free.c")
if os.path.isfile(sf):
    s = nocomment(rd(sf))
    calls = re.findall(r"proc_create\s*\(([^;]*?)\)\s*;", s, flags=re.S)
    world = [c for c in calls if "S_IWUGO" in c or "S_IWOTH" in c or "S_IWGRP" in c or re.search(r"\b0?666\b", c)]
    check("kernel: no tunable of the packet-release thread is writable by other users", len(calls) >= 4 and not world,
          "calls %d, writable by others %d" % (len(calls), len(world)))
    check("kernel: its four tunables stay writable by root", sum(1 for c in calls if "S_IWUSR" in c) == 4,
          [c.split(",")[0].strip() for c in calls])
else:
    check("kernel: bcm_skb_free.c present", False, sf)

# ---------------------------------------------------------------- Guest Portal: chilli's DNS answer builders
d = rd(os.path.join(SRC, "coovachilli", "src", "dhcp.c"))
dn = nocomment(d)
nak = body(dn, "int dhcp_nakDNS(struct dhcp_conn_t *conn, uint8_t *pack, size_t len)")
g, c = nak.find("if (len > sizeof(answer))"), nak.find("memcpy(answer, pack, len)")
check("portal: the refusal answer checks the frame length before it copies the frame", 0 < g < c, nak[:300])
dns = body(dn, "int dhcp_dns(struct dhcp_conn_t *conn, uint8_t *pack,")
g, c = dns.find("if (*plen > sizeof(answer))"), dns.find("memcpy(answer, pack, *plen)")
check("portal: the stand-in answer checks the frame length before it copies the frame", 0 < g < c)
q, r0 = dns.find("if (query_len + 16 > sizeof(query))"), dns.find("query[query_len++] = 0xc0;")
check("portal: room for the answer record is checked before the record is appended", 0 < q < r0)
check("portal: both checks leave by return 0 (the frame is dropped, nothing is sent)",
      re.search(r"if \(\*plen > sizeof\(answer\)\)\s*return 0;", dns) is not None
      and re.search(r"if \(query_len \+ 16 > sizeof\(query\)\)\s*return 0;", dns) is not None
      and re.search(r"if \(len > sizeof\(answer\)\)\s*return 0;", nak) is not None)
m = re.search(r"uint8_t\s+query\[(\d+)\]", dns)
check("portal: the record appended after the check is 16 bytes (12 fixed + a 4-byte address)",
      dns[r0:r0 + 900].count("query[query_len++] =") == 12 and "memcpy(query + query_len, reply, 4);" in dns[r0:r0 + 900]
      and m is not None and int(m.group(1)) >= 64)
# every copy of a received frame into a stack answer buffer in the code that is built is one of the two checked ones
built = re.sub(r"#ifdef ENABLE_PPPOE.*?#endif", " ", dn, flags=re.S)
check("portal: no other copy of a whole received frame into answer[] in the code that is built",
      len(re.findall(r"memcpy\(answer, pack(?:et)?,", built)) == 2, re.findall(r"memcpy\(answer, [^;]*;", built))
cfg = os.path.join(SRC, "coovachilli", "config.h")
if os.path.isfile(cfg):
    check("portal: the PPPoE server code (two more such copies) is not built", "#define ENABLE_PPPOE" not in rd(cfg))

# ---------------------------------------------------------------- httpd: device labels keep a non-ASCII last character
dv = rd(os.path.join(SRC, "httpd", "reaper_devname.c"))
a = dv.find("static void rdn_copy(char *out, size_t n, const char *s, size_t len)")
b = dv.find("\n}", a)
check("httpd: the label copy function is found", 0 <= a < b)
if 0 <= a < b and CC:
    tmp = tempfile.mkdtemp(prefix="rev1117p1b_")
    code = "#include <stdio.h>\n#include <string.h>\n" + dv[a:b + 2] + r"""
static int t(const char *in, size_t n, const char *want)
{
	char out[64];
	memset(out, 'X', sizeof(out));
	rdn_copy(out, n, in, strlen(in));
	if (strcmp(out, want)) { printf("in <%s> n=%u: got <%s> want <%s>\n", in, (unsigned)n, out, want); return 1; }
	return 0;
}
int main(void)
{
	int bad = 0;
	bad += t("Printer", 64, "Printer");
	bad += t("Caf\xc3\xa9", 64, "Caf\xc3\xa9");			/* ends in a complete 2-byte character */
	bad += t("\xe5\xae\xa2\xe5\x8e\x85", 64, "\xe5\xae\xa2\xe5\x8e\x85");	/* two 3-byte characters */
	bad += t("TV \xf0\x9f\x93\xba", 64, "TV \xf0\x9f\x93\xba");		/* ends in a complete 4-byte character */
	bad += t("Caf\xc3\xa9", 5, "Caf");				/* room for 4 bytes: the 2-byte character is cut, so it goes */
	bad += t("\xe5\xae\xa2\xe5\x8e\x85", 6, "\xe5\xae\xa2");		/* the second character is cut after 2 of 3 bytes */
	bad += t("\xe5\xae\xa2\xe5\x8e\x85", 5, "\xe5\xae\xa2");		/* ... after 1 of 3 bytes */
	bad += t("ab\xc3", 64, "ab");					/* a lead byte with nothing after it */
	bad += t("ab\xa9", 64, "ab");					/* a continuation byte with no lead byte */
	bad += t("\xa9\xa9", 64, "");					/* nothing but continuation bytes */
	bad += t("Name  ", 64, "Name");					/* trailing spaces still go */
	bad += t("a\x01" "b\x7f" "c", 64, "abc");			/* control characters still go */
	return bad ? 1 : 0;
}
"""
    src = os.path.join(tmp, "rdn.c"); exe = os.path.join(tmp, "rdn")
    open(src, "w", encoding="utf-8", errors="surrogateescape").write(code)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, src],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    ok, out = r.returncode == 0, r.stdout
    if ok:
        r = subprocess.run([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
        ok, out = r.returncode == 0, r.stdout
    check("httpd: a label ending in an accented, CJK or 4-byte character keeps it; only a cut sequence is removed", ok, out)
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- httpd: the requester's MAC, one resolver for all
w = rd(os.path.join(SRC, "httpd", "web.c"))
wn = nocomment(w)
check("httpd: the ARP-only requester lookup is gone", "reaper_requester_mac" not in wn)
check("httpd: both 'do not block the device you are using' guards ask the resolver that knows IPv6",
      wn.count("if (reaper_client_mac(self, sizeof(self)) && !strcasecmp(self, umac)) {") == 2)
hook = body(wn, "static int login_state_hook(int eid, webs_t wp, int argc, char_t **argv)")
check("httpd: the login-state hook starts no shell", bool(hook) and "popen(" not in hook and "ip neigh" not in hook
      and "reaper_client_mac(mac_str, sizeof(mac_str))" in hook, hook[:200])

# ---------------------------------------------------------------- iperf3 client request: checked in httpd, bounded in rc
cg = body(wn, "do_set_iperf3_cli_cgi(char *url, FILE *stream)")
check("iperf3: the port test can fail (conditions joined with ||, range 1-65535)",
      "if(!isValid_digit_string(iperf3_cli_port) || atoi(iperf3_cli_port)<1 || atoi(iperf3_cli_port)>65535){" in cg)
sv = nocomment(rd(os.path.join(SRC, "rc", "services.c")))
ic = body(sv, "start_iperf3_client(void)")
decl = re.search(r"char host\[(\d+)\], port\[(\d+)\], time\[(\d+)\], parallel\[(\d+)\], window\[(\d+)\], omit\[(\d+)\], buf_len\[(\d+)\], interval\[(\d+)\];", ic)
names = ["host", "port", "time", "parallel", "window", "omit", "buf_len", "interval"]
check("iperf3: rc copies every field with its buffer's size", bool(ic) and "strcpy(" not in ic.replace("strlcpy(", "")
      and all('strlcpy(%s, nvram_safe_get("iperf3_cli_%s"), sizeof(%s));' % (n, n, n) in ic for n in names), ic[:300])
lim = dict(re.findall(r"strlen\(iperf3_cli_(\w+)\) > (\d+)", cg))
check("iperf3: every length httpd accepts fits the buffer rc copies it into",
      decl is not None and all(n in lim and int(lim[n]) < int(decl.group(i + 1)) for i, n in enumerate(names)),
      (lim, decl.groups() if decl else None))

# ---------------------------------------------------------------- portal web server: only the modules it configures
uc = body(sv, "gen_uam_srv_conf(")
mods = re.findall(r'server\.modules\+=\(\\"(\w+)\\"\)', uc)
check("portal: its web server loads mod_alias and the sign-in module, nothing else", mods == ["mod_alias", "mod_captive_portal_uam"], mods)
uc = "\n".join(l for l in uc.split("\n") if not l.lstrip().startswith("//"))	# the stock file keeps old lines as // comments
check("portal: no setting is written for a module that is not loaded",
      "compress." not in uc and "url.rewrite" not in uc and "url.redirect" not in uc and "usertrack." not in uc and "userdir." not in uc)

# ---------------------------------------------------------------- Firewall page: the label works its switch
fwp = os.path.join(SRC, "www", "Reaper_Firewall.asp")
if os.path.isfile(fwp):
    fw = rd(fwp)
    check("firewall page: a click on the words beside an Auto refresh switch is passed to the switch (once)",
          "['st_auto','wt_auto'].forEach(function(id){var sw=$(id),lab=sw&&sw.parentNode;if(lab)lab.addEventListener('click',"
          "function(e){if(e.target!==sw)sw.click();});});" in fw and fw.count("REAPER-B5-LABEL") == 1)

# ---------------------------------------------------------------- rc: SNMP config mode, firewall-log writer, engine switch
sn = nocomment(rd(os.path.join(SRC, "rc", "snmpd.c")))
check("snmp: the agent's configuration file (it holds the SNMPv3 passphrases) is created new and root-only",
      'fp = reaper_fopen_new("/tmp/snmpd.conf", 0600);' in sn and 'fopen("/tmp/snmpd.conf", "w")' not in sn)
fl = nocomment(rd(os.path.join(SRC, "rc", "reaper_fwlog.c")))
rw = body(fl, "static int rfl_write(const char *path, const char *text)")
check("firewall log: its state writer goes through the shared writer (no descriptor left open on a failed write)",
      "return reaper_write_atomic(path, text, strlen(text), 0600);" in rw and "open(" not in rw, rw)
k = wn.find('int changed = (strcmp(nvram_safe_get("reaper_fw_enable"), en) != 0);')
seg = wn[k:k + 900] if k > 0 else ""
check("rules engine: switching it on or off is committed before the restart request",
      0 < seg.find("httpd_nvram_commit();") < seg.find('notify_rc("restart_reaper_fw");'), seg[:300])
check("rules engine: a changed confirm timer is committed, an unchanged one is not written",
      'if (strcmp(nvram_safe_get("reaper_fw_confirm"), b) != 0) {' in seg and seg.count("httpd_nvram_commit();") == 2)

# ---------------------------------------------------------------- rc: the two firewall writers carry the same input checks
fc = rd(os.path.join(SRC, "rc", "firewall.c"))
fcn = nocomment(fc)
i1 = fcn.find("\nfilter_setting(int wan_unit, char *lan_if, char *lan_ip, char *logaccept, char *logdrop)\n")
i2 = fcn.find("\nfilter_setting2(char *lan_if, char *lan_ip, char *logaccept, char *logdrop)\n")
check("firewall: both filter writers are found", 0 < i1 < i2)
one = fcn[i1:i2]
two = fcn[i2:fcn.find("\n}\n", i2) + 3] if i2 > 0 else ""
V6 = "if ((srcip[0] && !_fw_field_safe(srcip)) || (dstip[0] && !_fw_field_safe(dstip)) || !_fw_field_safe(port))"
KW = "if(*filterstr && _fw_keyword_safe(filterstr))"
for name, text in (("single-WAN writer", one), ("load-balance writer", two)):
    check("firewall, %s: IPv6 firewall rule fields are checked before they are written" % name, text.count(V6) == 1)
    check("firewall, %s: a keyword is checked, and written quoted in every build variant" % name,
          text.count(KW) == 1 and "--string %s --algo" not in text and text.count('--string \\"%s\\" --algo') >= 2)
    check("firewall, %s: SNMP from the WAN is pinned to a WAN interface" % name,
          len(re.findall(r'"-A INPUT -i %s -p udp --dport 161 -j %s\\n", (?:wan_if|snmp_if), logaccept', text)) == 1
          and '"-A INPUT -p udp --dport 161' not in text)

# ---------------------------------------------------------------- rules engine: Keep and revert cannot both go ahead
rf = rd(os.path.join(SRC, "rc", "reaper_fw.c"))
gr = body(nocomment(rf), "static void rfw_gen_rollback(void)")
t1 = gr.find('"rmdir " RFW_ARMED " 2>/dev/null || { logger -t reaper_fw')
t2 = gr.find('"rm -rf " REAPER_FW_DRAFT_DIR')
t3 = gr.find('"reaper_lockrun " RFW_ROLLBACK ".rules >/dev/null 2>&1 || {')
check("rules engine: the revert script takes the arm marker first and stops when there is none", 0 < t1 < t2 < t3
      and "exit 0; }" in gr[t1:t1 + 200], (t1, t2, t3))
check("rules engine: the marker is removed once (not again after the rebuild)", gr.count("RFW_ARMED") == 1)
check("rules engine: the revert rebuilds under the firewall lock, from a file only root can write",
      '"sh " RFW_ROLLBACK ".rules' not in gr and 'chmod(RFW_ROLLBACK ".rules", 0700);' in gr)
cf = body(nocomment(rf), "void reaper_fw_confirm(void)")
check("rules engine: Keep test-and-clears the same marker", "if (rmdir(RFW_ARMED) != 0) {" in cf)
lk = body(nocomment(rd(os.path.join(SRC, "rc", "rwatch.c"))), "int reaper_lockrun_main(int argc, char *argv[])")
check("rules engine: the lock wrapper lists the revert's rebuild script",
      '"/tmp/reaper_fw/rollback.sh.rules"' in lk and '#define RFW_DIR      "/tmp/reaper_fw"' in rf
      and '#define RFW_ROLLBACK RFW_DIR "/rollback.sh"' in rf)

# ---------------------------------------------------------------- the stock lease hook's file on flash is bounded
svf = rd(os.path.join(SRC, "rc", "services.c"))
a = svf.find('#define REAPER_NMPVC_FILE\t"/jffs/nmp_vc_json.js"')
b = svf.find("int dnsmasq_script_main(int argc, char **argv)\n")
check("lease hook: the cap helper sits in front of the lease script's entry point", 0 < a < b)
check("lease hook: the stock hook is called once, and only through the cap",
      svf.count("nmp_get_vendorclass(argc, argv);") == 1 and svf.count("reaper_nmpvc_ok(argc, argv))") == 1
      and "\tif (reaper_nmpvc_ok(argc, argv))\t/* review 2026-11-17 (C-closed-1) */\n\t\tnmp_get_vendorclass(argc, argv);\n\treturn 0;\n}\n" in svf)
if 0 < a < b and CC:
    tmp = tempfile.mkdtemp(prefix="rev1117nmp_")
    fpath = os.path.join(tmp, "vc.js")
    code = r"""#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
static int locks, unlocks, logs;
static int isValidMacAddress(const char *m) { return m && strlen(m) == 17 && m[2] == ':'; }
static int file_lock(const char *n) { locks += !strcmp(n, "nmpvc"); return 7; }
static void file_unlock(int l) { unlocks += (l == 7); }
static void logmessage(const char *t, const char *f, ...) { (void)t; (void)f; logs++; }
""" + svf[a:b].replace('"/jffs/nmp_vc_json.js"', '"%s"' % fpath) + r"""
static void fill(long n) { FILE *f = fopen(REAPER_NMPVC_FILE, "w"); long i; for (i = 0; i < n; i++) fputc('x', f); fclose(f); }
static int there(void) { struct stat st; return lstat(REAPER_NMPVC_FILE, &st) == 0; }
int main(void)
{
	char *add[] = { "s", "add", "00:00:5e:00:53:01", "192.0.2.10", NULL };
	char *old[] = { "s", "old", "00:00:5e:00:53:01", "192.0.2.10", NULL };
	char *del[] = { "s", "del", "00:00:5e:00:53:01", "192.0.2.10", NULL };
	char *v6[]  = { "s", "add", "00:03:00:01:00:00:5e:00:53:01", "2001:db8::10", NULL };
	int bad = 0;
	fill(1000);
	if (reaper_nmpvc_ok(4, add) != 1 || reaper_nmpvc_ok(4, old) != 1) { puts("a lease or a renewal must reach the hook"); bad++; }
	if (reaper_nmpvc_ok(4, del) != 0) { puts("a released lease reached the hook"); bad++; }
	if (reaper_nmpvc_ok(4, v6) != 0) { puts("a DHCPv6 event reached the hook"); bad++; }
	if (reaper_nmpvc_ok(2, add) != 0) { puts("a short argument list reached the hook"); bad++; }
	if (!there() || logs) { puts("a small file was touched"); bad++; }
	fill(REAPER_NMPVC_MAX); if (reaper_nmpvc_ok(4, add) != 1 || !there()) { puts("a file exactly at the limit was removed"); bad++; }
	fill(REAPER_NMPVC_MAX + 1L);
	if (reaper_nmpvc_ok(4, del) != 0 || !there()) { puts("a release touched an oversized file"); bad++; }
	if (reaper_nmpvc_ok(4, add) != 1 || there()) { puts("an oversized file survived a lease"); bad++; }
	if (locks != 1 || unlocks != 1 || logs != 1) { printf("lock %d unlock %d log %d (want 1 1 1)\n", locks, unlocks, logs); bad++; }
	if (symlink("/etc/passwd", REAPER_NMPVC_FILE) != 0 || reaper_nmpvc_ok(4, add) != 1 || there()) { puts("a link in the file's place was kept"); bad++; }
	if (reaper_nmpvc_ok(4, add) != 1) { puts("no file: the hook must still run (it creates the file)"); bad++; }
	return bad ? 1 : 0;
}
"""
    src = os.path.join(tmp, "n.c"); exe = os.path.join(tmp, "n")
    open(src, "w", encoding="utf-8", errors="surrogateescape").write(code)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, src],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    ok, out = r.returncode == 0, r.stdout
    if ok:
        r = subprocess.run([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
        ok, out = r.returncode == 0, r.stdout
    check("lease hook: leases and renewals pass, releases and DHCPv6 events do not, a file past 64 KB (or a link) is started again under the hook's lock", ok, out)
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- a Guest Portal whose daemon is gone is started again
check("portal watch: 'a wanted portal has no process' is decided from the saved settings and the process list",
      "int reaper_portal_down(void)\n{\n\tint want = reaper_portals_wanted();\n" in svf
      and 'if ((want & 1) && reaper_chilli_count("/tmp/chilli.conf", 0) <= 0)' in svf
      and 'if ((want & 2) && reaper_chilli_count("/tmp/chilli-cp.conf", 0) <= 0)' in svf)
check("portal watch: the service verb runs the existing reconcile (start only what the settings ask for)",
      "void reaper_portal_heal(void)\n{\n\treaper_portal_reconcile(NULL);\n}\n" in svf
      and '\telse if (strcmp(script, "reaper_portal_heal") == 0)' in svf and "if(action & RC_SERVICE_START) reaper_portal_heal();" in svf)
wdc = rd(os.path.join(SRC, "rc", "watchdog.c"))
lk = wdc[wdc.find("static void reaper_portal_look(void)"):]
lk = lk[:lk.find("\n}\n") + 3]
check("portal watch: one look a minute, two misses in a row, three starts a boot, nothing when no portal was started",
      "if (now - last < 60)" in lk and "if (++miss < 2)" in lk and "heals >= 3" in lk
      and '!f_exists("/tmp/chilli.conf") && !f_exists("/tmp/chilli-cp.conf")' in lk
      and 'notify_rc("start_reaper_portal_heal");' in lk, lk[:300])
check("portal watch: built only where the portal is, and called from the watchdog's regular pass",
      wdc.count("#if defined(RTCONFIG_COOVACHILLI) && defined(RTCONFIG_MULTILAN_CFG)\n\treaper_portal_look();") == 1
      and wdc.count("reaper_portal_look") == 2)

# ---------------------------------------------------------------- daemons: a command's output is read with a time limit
ts = rd(os.path.join(SRC, "shared", "reaper_tmpsafe.c"))
th = rd(os.path.join(SRC, "shared", "reaper_tmpsafe.h"))
a = ts.find("/* ---- reaper 2026-11-17 (review D-3 / D-24) REAPER-POPEN-BOUNDED")
check("runner: the shared time-limited popen is defined once and declared",
      a > 0 and ts.count("FILE *reaper_popen_bounded(const char *cmd, int secs, int *status)\n{") == 1
      and "FILE *reaper_popen_bounded(const char *cmd, int secs, int *status);" in th)
for dn, want in (("rpunctd", 6), ("rchqd", 2), ("gkd", 3)):
    dsrc = nocomment(rd(os.path.join(SRC, dn, dn + ".c")))
    check("runner: %s reads %d command output(s) through it and has no popen() / pclose() left" % (dn, want),
          dsrc.count("reaper_popen_bounded(") == want and "pclose(" not in dsrc
          and "popen(" not in dsrc.replace("reaper_popen_bounded(", ""), dsrc.count("reaper_popen_bounded("))
if a > 0 and CC:
    tmp = tempfile.mkdtemp(prefix="rev1117run_")
    code = ("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <errno.h>\n#include <fcntl.h>\n#include <unistd.h>\n"
            "#include <sys/types.h>\n#include <sys/wait.h>\n#include <poll.h>\n#include <signal.h>\n#include <time.h>\n" + ts[a:] + r"""
int main(void)
{
	char l[256]; int st = 99, bad = 0, n = 0; FILE *f; long t0, t1;
	f = reaper_popen_bounded("echo one; echo two", 5, &st);
	if (!f || !fgets(l, sizeof(l), f) || strcmp(l, "one\n") || !fgets(l, sizeof(l), f) || strcmp(l, "two\n") || fgets(l, sizeof(l), f) || st != 0) { puts("plain output wrong"); bad++; }
	if (f) fclose(f);
	f = reaper_popen_bounded("exit 3", 5, &st); if (!f || st != 3) { printf("exit status %d (want 3)\n", st); bad++; } if (f) fclose(f);
	t0 = reaper_mono_ms(); f = reaper_popen_bounded("echo early; sleep 37; echo late", 1, &st); t1 = reaper_mono_ms();
	if (!f || !fgets(l, sizeof(l), f) || strcmp(l, "early\n") || fgets(l, sizeof(l), f) || st != -1 || t1 - t0 > 4000) { printf("time limit: status %d after %ld ms\n", st, t1 - t0); bad++; }
	if (f) fclose(f);
	if (system("pgrep -f '[s]leep 37' >/dev/null") == 0) { puts("the command killed at its time limit left a child running"); bad++; }
	f = reaper_popen_bounded("yes x | head -c 400000", 5, &st); if (f) { while (fgetc(f) != EOF) n++; fclose(f); }
	if (n != 256 * 1024) { printf("size limit: %d bytes kept (want 262144)\n", n); bad++; }
	if (reaper_popen_bounded(NULL, 5, NULL) || reaper_popen_bounded("true", 0, NULL)) { puts("bad arguments accepted"); bad++; }
	return bad ? 1 : 0;
}
""")
    src = os.path.join(tmp, "r.c"); exe = os.path.join(tmp, "r")
    open(src, "w", encoding="utf-8", errors="surrogateescape").write(code)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, src],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    ok, out = r.returncode == 0, r.stdout
    if ok:
        r = subprocess.run([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
        ok, out = r.returncode == 0, r.stdout
    check("runner: output and exit status come back; a command past its limit is killed with its children; output is capped", ok, out)
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- SNMP: the three names are writable, the page wins
def hostrun(tag, csrc, args=(), extra=()):
    """compile `csrc` on the host and run it; returns (ok, output)"""
    tmp = tempfile.mkdtemp(prefix="rev1117%s_" % tag)
    src, exe = os.path.join(tmp, "t.c"), os.path.join(tmp, "t")
    open(src, "w", newline="\n").write(csrc)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror"] + list(extra) + ["-o", exe, src],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    if r.returncode != 0:
        return False, "compile: " + r.stdout, tmp
    r = subprocess.run([exe] + [os.path.join(tmp, a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=120)
    return r.returncode == 0, r.stdout, tmp


snp = os.path.join(SRC, "rc", "snmpd.c")
if os.path.isfile(snp):
    sn = rd(snp); snc = nocomment(sn)
    check("snmp: the three names are written in the agent's writable form, none in the read-only form",
          all(('fprintf(fp, "p%s %%s\\n", cval);' % t) in snc for t in ("sysname", "syslocation", "syscontact"))
          and not re.search(r'fprintf\(fp, "sys(Name|Location|Contact) %s', snc))
    st = body(sn, "void start_snmpd(void)")
    i, j = st.find('snmp_drop_saved_sys("/var/net-snmp/snmpd.conf");'), st.find('eval("snmpd", "-c", "/tmp/snmpd.conf")')
    check("snmp: the agent's saved copies are dropped before every start (a change on the page takes effect)", 0 < i < j)
    fn = body(sn, "static void snmp_drop_saved_sys(const char *path)")
    if CC and fn:
        keep = "engineBoots 5\n" + "usmUser " + "x" * 1015 + "psysname inside-a-long-line\n" + "oldEngineID 0x80001f88\n"
        ok, out, tmp = hostrun("snmp", """
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
static FILE *reaper_fopen_new(const char *p, int mode) { (void)mode; return fopen(p, "w"); }
static void snmp_drop_saved_sys(const char *path)
%s
int main(int argc, char **argv) { int i; for (i = 1; i < argc; i++) snmp_drop_saved_sys(argv[i]); return 0; }
""" % fn, args=())
        if ok:
            a, b = os.path.join(tmp, "saved"), os.path.join(tmp, "plain")
            lines = keep.split("\n")
            open(a, "w", newline="\n").write(lines[0] + "\npsysname Example\n" + lines[1] + "\nPsysLocation Somewhere\n"
                                             "psyscontact someone\n" + lines[2] + "\n")
            open(b, "w", newline="\n").write(keep)
            r = subprocess.run([os.path.join(tmp, "t"), a, b, os.path.join(tmp, "absent")], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
            ok = (r.returncode == 0 and open(a).read() == keep and open(b).read() == keep
                  and sorted(os.listdir(tmp)) == ["plain", "saved", "t", "t.c"])
            out = r.stdout + " files=%s" % sorted(os.listdir(tmp))
        check("snmp: only the three saved lines go (any case); a long line that holds the word is kept whole; "
              "no temp file is left", ok, out)
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        check("snmp: the saved-copy filter is present", bool(fn))

# ---------------------------------------------------------------- AI Advisor: cut marks, the IPv6 pin, device text
rmp = os.path.join(SRC, "rmcpd", "rmcpd.c")
if os.path.isfile(rmp):
    rm = rd(rmp); rmc = nocomment(rm)
    INC = """
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <signal.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <poll.h>
#include <netinet/in.h>
#include <arpa/inet.h>
"""
    i = rm.find("typedef struct { char *p; size_t len, cap; int truncated; } sbuf_t;")
    j = rm.find("/* structural egress scrub")
    j = rm.rfind("/* ----", 0, j) if j > 0 else -1
    if CC and 0 < i < j:
        ok, out, tmp = hostrun("adv", INC + "#define TOOLOUT_MAX (256 * 1024)\n" + rm[i:j] + r"""
static int has(const sbuf_t *t, const char *w) { return t->p && strstr(t->p, w) != NULL; }
int main(int argc, char **argv)
{
	sbuf_t t; int bad = 0;
	const char *M = "[cut here: this source is limited to ";
	if (argc < 3) return 2;
	sb_init(&t); sb_addfile(&t, argv[1], 100);
	if (!has(&t, M) || !has(&t, "limited to 100 bytes") || strncmp(t.p, "aaaaaaaaaa", 10) || t.len <= 100) { puts("file longer than its limit: no mark"); bad = 1; }
	sb_free(&t); sb_init(&t); sb_addfile(&t, argv[2], 100);
	if (has(&t, M) || t.len != 100) { puts("file of exactly the limit: marked"); bad = 1; }
	sb_free(&t); sb_init(&t); sb_addfile(&t, argv[1], 1000);
	if (has(&t, M) || t.len != 300) { puts("file under its limit: marked"); bad = 1; }
	sb_free(&t); sb_init(&t); sb_addcmd(&t, "head -c 9000 /dev/zero | tr '\\000' a", 4096);
	if (!has(&t, "limited to 4096 bytes") || t.len <= 4096) { puts("command longer than its limit: no mark"); bad = 1; }
	sb_free(&t); sb_init(&t); sb_addcmd(&t, "head -c 4096 /dev/zero | tr '\\000' a", 4096);
	if (has(&t, M) || t.len != 4096) { printf("command of exactly the limit: marked (len %lu)\n", (unsigned long)t.len); bad = 1; }
	sb_free(&t); sb_init(&t); sb_addcmd(&t, "printf abc", 4096);
	if (!t.p || strcmp(t.p, "abc")) { puts("short command: changed"); bad = 1; }
	sb_free(&t); sb_init(&t); sb_json_str(&t, "a\"b\n");
	if (!t.p || strcmp(t.p, "\"a\\\"b\\n\"")) { puts("json string: changed"); bad = 1; }
	sb_free(&t); sb_init(&t); sb_puts(&t, "\""); sb_json_body(&t, "x\t"); sb_json_body(&t, "y\\"); sb_json_body(&t, NULL); sb_puts(&t, "\"");
	if (!t.p || strcmp(t.p, "\"x\\ty\\\\\"")) { puts("json parts: wrong"); bad = 1; }
	sb_free(&t); sb_init(&t); sb_json_str(&t, NULL);
	if (!t.p || strcmp(t.p, "null")) { puts("json null: changed"); bad = 1; }
	return bad;
}
""", extra=("-Wno-unused-function",))
        if "compile:" not in out:
            open(os.path.join(tmp, "long"), "w").write("a" * 300)
            open(os.path.join(tmp, "exact"), "w").write("a" * 100)
            r = subprocess.run([os.path.join(tmp, "t"), os.path.join(tmp, "long"), os.path.join(tmp, "exact")],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
            ok, out = r.returncode == 0, r.stdout
        check("advisor: a file or a command longer than its limit ends with the cut line; one of exactly the limit "
              "or shorter does not; the JSON escaper is unchanged", ok, out)
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        check("advisor: the buffer helpers are found", 0 < i < j)
    hb = rm[rm.find("static void handle_rpc("):] if "static void handle_rpc(" in rm else rm
    a, b = hb.find("tout.truncated = was_trunc;"), hb.find("sb_mark_truncated(&tout);")
    check("advisor: the whole-result cut mark is written after the scrub passes (the flag is carried over them)",
          0 < hb.find("sb_scrub_secrets(&tout);") < a < b)
    fn = body(rm, "static void sanitize_client_ip(void)")
    if CC and fn:
        ok, out, tmp = hostrun("pin", INC + "static char g_client_ip[48];\nstatic void sanitize_client_ip(void)\n" + fn + r"""
static int t(const char *in, const char *want)
{
	snprintf(g_client_ip, sizeof(g_client_ip), "%s", in);
	sanitize_client_ip();
	if (strcmp(g_client_ip, want)) { printf("%s -> '%s', wanted '%s'\n", in, g_client_ip, want); return 1; }
	return 0;
}
int main(void)
{
	return t("192.168.50.5", "192.168.50.5") | t("2001:DB8:0:0::1", "2001:db8::1") | t("2001:0db8:0000:0000:0000:0000:0000:0001", "2001:db8::1")
	     | t("fd00::AB", "fd00::ab") | t("", "") | t("not-an-address", "") | t("2001:db8::g", "");
}
""")
        check("advisor: an IPv6 pin is kept in the printed form (capitals, leading zeros, long zero runs); IPv4 and "
              "refusals are unchanged", ok, out)
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        check("advisor: the pin check is found", bool(fn))
    check("advisor: the client list and the log lines are fenced with a per-start random tag, as one JSON string",
          'return !strcmp(name, "get_clients") || !strcmp(name, "get_logs");' in rmc
          and 'open("/dev/urandom", O_RDONLY | O_CLOEXEC)' in rmc and "env_tag_init();" in body(rm, "int main(")
          and re.search(r'if \(tool_device_text\(tname\)\) \{.*?DEVICE-WRITTEN TEXT %s BEGIN.*?sb_json_body\(&r, tout\.p \? tout\.p : ""\);'
                        r'.*?DEVICE-WRITTEN TEXT %s END\]", g_env_tag\);.*?\} else\s+sb_json_str\(&r, tout\.p \? tout\.p : ""\);', rmc, re.S) is not None)
    note = re.search(r'#define ADV_UNTRUSTED_NOTE (.*?)\n\n', rm, re.S)
    check("advisor: both initialize texts say what the markers mean, in text that needs no JSON escaping",
          rmc.count('" ADV_UNTRUSTED_NOTE "\\"}");') == 2 and note is not None
          and "DEVICE-WRITTEN TEXT markers" in note.group(1) and "\\" not in note.group(1).replace("\\\n", ""))
    # owner 2026-11-17: at most 20 DNS lookups in one armed session (a lookup is the one way out for what a model read)
    h = rm.find("static void tool_net_dns_lookup(struct json_object *args, sbuf_t *out)")
    d = rm.rfind("#define ADV_DNS_LOOKUP_MAX", 0, h) if h > 0 else -1
    e = rm.find("\n}\n", h) if h > 0 else -1
    if CC and h > 0 and e > h:
        ok, out, tmp = hostrun("dnscap", r"""
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <ctype.h>
#include <syslog.h>
struct json_object { int x; };
typedef struct { char p[512]; } sbuf_t;
static const char *g_host; static int g_ran;
static const char *diag_arg_host(struct json_object *a) { (void)a; return g_host; }
static void sb_puts(sbuf_t *s, const char *t) { snprintf(s->p, sizeof(s->p), "%s", t); }
static void sb_printf(sbuf_t *s, const char *f, ...) { va_list ap; va_start(ap, f); vsnprintf(s->p, sizeof(s->p), f, ap); va_end(ap); }
static void run_diag(const char *tool, const char *target, char *const argv[], int t, sbuf_t *out)
{ (void)tool; (void)target; (void)argv; (void)t; g_ran++; sb_puts(out, "ran"); }
""" + rm[(d if d > 0 else h):e + 3] + r"""
int main(void)
{
	sbuf_t o; int i, refused = 0;
	for (i = 0; i < 5; i++) { g_host = "bad name!"; tool_net_dns_lookup(NULL, &o); }
	if (g_ran) { puts("an invalid name was run"); return 1; }
	for (i = 0; i < 20; i++) { g_host = "example.com"; o.p[0] = 0; tool_net_dns_lookup(NULL, &o); if (strcmp(o.p, "ran")) { printf("lookup %d of 20 refused: %s\n", i + 1, o.p); return 1; } }
	for (i = 0; i < 6; i++) { g_host = "example.org"; o.p[0] = 0; tool_net_dns_lookup(NULL, &o); if (strstr(o.p, "used its 20 DNS lookups")) refused++; }
	if (g_ran != 20 || refused != 6) { printf("ran %d (want 20), refused %d (want 6)\n", g_ran, refused); return 1; }
	return 0;
}
""")
        check("advisor: one session answers 20 DNS lookups; refused requests are not counted; the 21st and later are "
              "refused with a reason", ok and d > 0, out if d > 0 else "no ADV_DNS_LOOKUP_MAX: every lookup is answered")
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        check("advisor: the DNS lookup tool is found", h > 0)
    wb = os.path.join(SRC, "httpd", "web.c")
    if os.path.isfile(wb):
        check("advisor: the settings backup carries a full IPv6 pin (46 bytes)", '{ "advisor", "rmcp_client",    46   }' in rd(wb))

# ---------------------------------------------------------------- diagnostics report v1.3.60: the login name, new lines
dgp = os.path.join(SRC, "others", "reaper_diag")
if os.path.isfile(dgp):
    dg = rd(dgp)
    check("diag: v1.3.60 in the script and on the page", 'VER="REAPER-DIAG v1.3.61"' in dg
          and "REAPER-DIAG v1.3.61</span>" in rd(os.path.join(SRC, "www", "Reaper_Diag.asp")))
    check("diag: both process lists pass through the login-name rewrite",
          "top -bn1 2>/dev/null | head -12 | san_usercol | sed 's/^/  /'" in dg
          and "\nps w 2>/dev/null | san_usercol | sed 's/^/  /'\n" in dg and dg.count("san_usercol") == 4)
    check("diag: the name comes from the account file (the nvram dump holds it encrypted) and joins the literal list",
          "ADMU=\"$(awk -F: '$3 == 0 && $1 != \"\" && $1 != \"root\" && $1 != \"admin\" { printf \"%s \", $1 }' /etc/passwd 2>/dev/null)\"" in dg
          and "for _u in $ADMU; do [ \"${#_u}\" -ge 5 ] && printf 'USR\\t%s\\n' \"$_u\" >> \"$SLIST\"; done" in dg)
    check("diag: the radio version line, AP isolation and Wallguard's switch are printed",
          'echo "  radio sw : $_w ${_wv:-version not readable}"' in dg and 'echo "  ap isolation      : ${_iso:-off on every network}"' in dg
          and 'echo "  wallguard         : wallguard_enable=' in dg)
    SHL = [x for x in (shutil.which("busybox"), shutil.which("dash"), shutil.which("sh")) if x]
    a = dg.find("ADMU=\"$(awk"); b = dg.find("\n}\n", dg.find("san_usercol() {")) + 3
    if SHL and 0 < a < b:
        tmp = tempfile.mkdtemp(prefix="rev1117diag_")
        pw = os.path.join(tmp, "passwd")
        open(pw, "w").write("Examplelongname1:x:0:0:root:/root:/bin/sh\nnobody:x:65534:65534::/dev/null:/dev/null\nbob:x:0:0::/root:/bin/sh\n")
        sc = os.path.join(tmp, "t.sh")
        open(sc, "w").write('SLIST="%s/slist"; : > "$SLIST"\n' % tmp + dg[a:b].replace("/etc/passwd", pw) + r"""
printf '  PID USER       VSZ STAT COMMAND\n    1 Examplel 21700 S    /sbin/init\n 4431 nobody    6048 S    dnsmasq --log-async\n  900 bob       2204 S    /usr/sbin/envrams bob\n' | san_usercol
printf '  PID  PPID USER     STAT   VSZ %%VSZ CPU %%CPU COMMAND\n 6417     1 Examplel S    26712  1.3   2  0.0 amas_lib\n' | san_usercol
echo "LIST:$(cat "$SLIST" | tr '\t\n' '=;')"
""")
        sh = SHL[0]
        r = subprocess.run([sh, "ash", sc] if os.path.basename(sh) == "busybox" else [sh, sc],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
        o = r.stdout
        check("diag: a long login name (cut to 8 characters by ps) and a short one are both replaced in the USER column",
              "    1 admin 21700 S    /sbin/init" in o and "  900 admin       2204 S    /usr/sbin/envrams bob" in o
              and " 6417     1 admin S    26712" in o and " Examplel " not in o, o)
        check("diag: other users and the command column are left alone", " 4431 nobody    6048 S    dnsmasq --log-async" in o
              and o.rstrip().endswith("bob\n 6417     1 admin S    26712  1.3   2  0.0 amas_lib\nLIST:USR=Examplelongname1;".rstrip())
              or ("envrams bob" in o and "LIST:USR=Examplelongname1;" in o), o)
        check("diag: only a name of 5 or more characters joins the literal list (a short one would match inside words)",
              "LIST:USR=Examplelongname1;" in o and "USR=bob" not in o, o)
        shutil.rmtree(tmp, ignore_errors=True)
    # a filler value (the stock default wps_sta_pin=00000000) must not become a literal: it replaced the zero half
    # of every register in a crash dump with the secret token (owner diag 2026-11-17)
    m = re.search(r"awk -F= '\n(.*?)' \"\$NVS\" > \"\$SLIST\"", dg, flags=re.S)
    check("diag: the nvram literal collector is found", bool(m))
    awkp = shutil.which("busybox") or shutil.which("awk")
    if m and awkp:
        tmp = tempfile.mkdtemp(prefix="rev1117fill_")
        prog = os.path.join(tmp, "collect.awk"); nvs = os.path.join(tmp, "nvs")
        open(prog, "w", newline="\n").write(m.group(1))
        open(nvs, "w", newline="\n").write("wps_sta_pin=00000000\nwl0_wpa_psk=examplepsk77\nwl1_key1=ffffffffff\n"
                                           "http_username=exampleuser\nwl0_ssid=aaaaaa\nwps_device_pin=12345670\n")
        r = subprocess.run(([awkp, "awk"] if os.path.basename(awkp) == "busybox" else [awkp]) + ["-F=", "-f", prog, nvs],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
        got = sorted(r.stdout.split("\n"))
        check("diag: a one-character filler value is not a literal; real values still are",
              got == sorted(["", "SEC\texamplepsk77", "USR\texampleuser", "SEC\t12345670"]), r.stdout)
        shutil.rmtree(tmp, ignore_errors=True)
    for shn in ("busybox", "dash"):
        shp = shutil.which(shn)
        if shp:
            r = subprocess.run([shp, "ash", "-n", dgp] if shn == "busybox" else [shp, "-n", dgp],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
            check("diag: the script parses under %s" % shn, r.returncode == 0, r.stdout)

print()
if fails:
    print("%d check(s) FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
