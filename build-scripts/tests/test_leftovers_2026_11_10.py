#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backlog leftovers closed on 2026-11-10 (image _r7): Encrypted DNS block, rednsd review notes, IPsec.

WHY THIS EXISTS.
  Encrypted DNS block: the firewall build read the two block switches several times (IPv4 rules, the sets, IPv6 rules),
    so a Save landing mid-build could give the two families different halves; and the page's Save restarted the
    device-facing server (dropping every encrypted connection) when only the block changed.
  rednsd: a TCP retry identified its query by slot and random id only - a slot freed by an HTTP/2 stream reset and
    reused with the same id (1 in 65,536) could take the old answer; and nghttp2 could hold 256 KB per connection.
  IPsec: a profile refused by the 2026-11-10 gate while its tunnel was up stayed up (only a reload ran); an IPv6 local
    subnet was cut to nothing by an IPv4-only filter; the VPN users of ipsec_client_list_N went into ipsec.secrets
    unchecked (a name opens a line unquoted); the page allowed '#' in an IPsec user name; the profile export wrote
    through a NULL pointer for a local subnet without a prefix length.

WHAT IT DOES. Compiles rc's real edns_block_rules() with stand-ins and flips a switch between the IPv4 and IPv6 calls;
compiles the IPsec checks and runs a table; pins the rest at the places a later edit must keep.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "encdns.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))
rd = lambda rel: open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()
def cut(text, start, end):
    a = text.find(start); b = text.find(end, a + 1) if a >= 0 else -1
    return text[a:b] if 0 <= a < b else ""
tmp = tempfile.mkdtemp(prefix="leftovers-")
def build(name, code):
    c = os.path.join(tmp, name + ".c"); x = os.path.join(tmp, name)
    open(c, "w").write(code)
    r = subprocess.run([CC, "-O1", "-Wall", "-Werror", "-Wno-unused-function", "-o", x, c], capture_output=True, text=True)
    return (x if r.returncode == 0 else None), r.stderr

# ------------------------------------------------------------------ A. Encrypted DNS block: one read per build
ec = rd("rc/encdns.c")
blk = cut(ec, "#define EDNS_SET4", "/* is name one the router itself encrypts to")
check("encdns: the block code is found", "void edns_block_rules(FILE *fp, int v6)" in blk)
H = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define REAPER_AIMESH_SET "reaper_aimesh"
#define RED_DIR "/tmp"
static int DOT = 1, DOH = 1, READS;
static const char *nvram_get(const char *k) { READS++; static char b[4]; if (!strcmp(k, "reaper_dot_block")) { snprintf(b, sizeof(b), "%d", DOT); return b; } return NULL; }
static int nvram_get_int(const char *k) { READS++; if (!strcmp(k, "reaper_doh_block")) return DOH; return 0; }
static const char *nvram_safe_get(const char *k) { (void)k; return ""; }
static int is_routing_enabled(void) { return 1; }
static int f_exists(const char *p) { (void)p; return 0; }
static int reaper_secure_dir(const char *p, int m) { (void)p; (void)m; return 0; }
static int EVALS;
#define eval(...) (EVALS++)
''' + blk + r'''
int main(void) {
  /* a build with both switches on, a "Save" turning the DoH half off between the IPv4 and the IPv6 call */
  FILE *f4 = fopen("/dev/null", "w"), *f6 = tmpfile(), *g4 = tmpfile();
  char b[4096]; size_t n;
  edns_block_rules(f4, 0);
  DOH = 0;
  edns_block_rules(f6, 1);
  rewind(f6); n = fread(b, 1, sizeof(b) - 1, f6); b[n] = 0;
  printf("v6-has-443=%d v6-has-853=%d\n", strstr(b, "--dport 443") != NULL, strstr(b, "--dport 853") != NULL);
  /* the next build reads again */
  edns_block_rules(g4, 0);
  rewind(g4); n = fread(b, 1, sizeof(b) - 1, g4); b[n] = 0;
  printf("next-has-443=%d next-has-853=%d\n", strstr(b, "--dport 443") != NULL, strstr(b, "--dport 853") != NULL);
  return 0; }
'''
x, err = build("edns", H)
check("encdns: the real rule builder compiles on the host", x is not None, err)
if x:
    o = subprocess.run([x], capture_output=True, text=True).stdout
    check("encdns: a switch changed between the IPv4 and IPv6 calls of one build - IPv6 gets the same halves as IPv4",
          "v6-has-443=1 v6-has-853=1" in o, o)
    check("encdns: the next build reads the switches again", "next-has-443=0 next-has-853=1" in o, o)
check("encdns: the sets take the DoH half from the snapshot (no read of their own)",
      "static void edns_sets_ensure(int doh)" in ec and "edns_sets_ensure(doh);" in ec and "if (!doh)\n\t\treturn;" in cut(ec, "static void edns_sets_ensure(int doh)", "\n}\n"))
pg = rd("www/Reaper_EncryptedDNS.asp")
sv = cut(pg, "function encSave(){", "\n}\n")
check("page: only a server switch restarts the server; the block switch no longer does",
      "if(srvChg) sv.push('restart_rednsd');" in sv and "f.reaper_doh_block.value !== (NV.blk === '1' ? '1' : '0')) sv.push('restart_rednsd')" not in sv)
check("page: the block still restarts dnsmasq and the firewall",
      "sv.indexOf('restart_dnsmasq') < 0) sv.push('restart_dnsmasq');" in sv and "f.reaper_dot_block.value !== DOTB) sv.push('restart_firewall');" in sv)

# ------------------------------------------------------------------ B. rednsd review notes
rn = rd("rednsd/rednsd.c")
check("rednsd: the HTTP/2 memory cap is 64 KB per connection", re.search(r"#define H2_MEM_MAX\t\(64 \* 1024\)", rn) is not None)
check("rednsd: every query gets a new, non-zero sequence number",
      "\tif (!++pend_seq)\n\t\t++pend_seq;\t\t/* 0 never names a query */\n\tp->seq = pend_seq;" in rn and "unsigned seq;" in cut(rn, "struct pending {", "};"))
check("rednsd: a TCP retry records the query's sequence number and matches it",
      "r->seq = p->seq;" in cut(rn, "static void tcpre_start(struct pending *p)", "\n}\n")
      and "return (p->used && p->up_id == r->up_id && p->seq == r->seq) ? p : NULL;" in rn and "unsigned seq;" in cut(rn, "struct tcpre {", "};"))
check("rednsd: a freed slot clears the sequence number with the rest", "memset(p, 0, sizeof(*p));" in cut(rn, "static void pend_free(struct pending *p)", "\n}\n"))

# ------------------------------------------------------------------ C. IPsec
ip = rd("rc/rc_ipsec.c")
s46 = cut(ip, "static void ipsec_subnet_sanitize46(char *subnet)", "\n}\n") + "\n}\n"
s4 = cut(ip, "static void ipsec_subnet_sanitize(char *subnet)", "\n}\n") + "\n}\n"
cu = cut(ip, "static int ipsec_cli_user_ok(const char *s)", "/* reaper ipsec-profile-gate: end */")
H2 = r'''
#include <stdio.h>
#include <string.h>
#include <strings.h>
''' + s46 + s4 + cu + r'''
int main(int argc, char **argv) {
  char b[256];
  if (!strcmp(argv[1], "s46")) { snprintf(b, sizeof(b), "%s", argv[2]); ipsec_subnet_sanitize46(b); printf("[%s]\n", b); }
  if (!strcmp(argv[1], "s4")) { snprintf(b, sizeof(b), "%s", argv[2]); ipsec_subnet_sanitize(b); printf("[%s]\n", b); }
  if (!strcmp(argv[1], "user")) printf("%d\n", ipsec_cli_user_ok(argv[2]));
  if (!strcmp(argv[1], "pass")) printf("%d\n", ipsec_cli_pass_ok(argv[2]));
  return 0; }
'''
x2, err = build("ipsec", H2)
check("ipsec: the real checks compile on the host", x2 is not None, err)
if x2:
    run = lambda *a: subprocess.run([x2] + list(a), capture_output=True, text=True).stdout.strip()
    check("ipsec: an IPv6 local subnet is kept", run("s46", "fd00:1:2::/64") == "[fd00:1:2::/64]" and run("s46", "2001:DB8::/48,192.168.50.0/24") == "[2001:DB8::/48,192.168.50.0/24]")
    check("ipsec: the local subnet filter still cuts at anything else", run("s46", "192.168.1.0/24;reboot") == "[192.168.1.0/24]" and run("s46", "fd00::/64 x") == "[fd00::/64]")
    check("ipsec: the virtual subnet stays IPv4 (it is completed to x.x.x.0/24)", run("s4", "fd00::/64") == "[]" and run("s4", "10.10.10") == "[10.10.10]")
    ok_users = ["alice", "bob.smith", "user_1", "o'neil", "Ünused".encode("utf-8").decode("latin-1")[:0] + "x-y"]
    bad_users = ["", "a b", "a:b", "a#b", 'a"b', "a\\b", "a<b", "a>b", "include", "INCLUDE", "a\tb", "x" * 65]
    check("ipsec: VPN user names that open an ipsec.secrets line safely are kept", all(run("user", u) == "1" for u in ok_users), [(u, run("user", u)) for u in ok_users])
    check("ipsec: names with whitespace, ':', '#', quotes, backslash, <>, 'include' or over 64 characters are refused",
          all(run("user", u) == "0" for u in bad_users), [(u, run("user", u)) for u in bad_users])
    check("ipsec: passwords - a double quote or a control character is refused, the rest kept",
          run("pass", "p@ss w0rd!'") == "1" and run("pass", 'a"b') == "0" and run("pass", "a\x01b") == "0" and run("pass", "") == "0" and run("pass", "a\\b") == "1")
sec = cut(ip, "if(nvram_get_int(\"ipsec_server_enable\") == 1){\n\t\t\t\t\t\tint cl_n = 0;", "#ifdef RTCONFIG_INSTANT_GUARD")
check("ipsec: every VPN user is checked before its line is written, and a refused one is logged and skipped",
      sec.find("if(!ipsec_cli_user_ok(name) || !ipsec_cli_pass_ok(passwd)){") < sec.find('snprintf(ipsec_client_list_buf') and "continue;" in sec
      and "VPN user %d of %s skipped: unsafe character in the %s" in sec)
check("ipsec: the gate records each refused slot; each pass starts empty and compares with the last",
      "ipsec_gate_refused[is_svr ? 1 : 0] |= 1u << (idx - 1);" in ip and "ipsec_gate_refused[0] = ipsec_gate_refused[1] = 0;" in cut(ip, "int pre_ipsec_prof_set()", "\n}\n")
      and "ipsec_gate_new_refusal = 1;" in cut(ip, "int pre_ipsec_prof_set()", "\n}\n"))
st = cut(ip, "void rc_ipsec_set(ipsec_conn_status_t conn_status, ipsec_prof_type_t prof_type)", "\n}\n")
i_r, i_rl = st.find("&& ipsec_gate_new_refusal){"), st.find("rc_ipsec_reload(fp);")
check("ipsec: a new refusal restarts strongSwan (its tunnel goes down) instead of the reload, once",
      0 < i_r < i_rl and "rc_ipsec_restart(fp);" in st[i_r:i_rl] and "ipsec_gate_new_refusal = 0;" in st[i_r:i_rl]
      and "if(IPSEC_INIT == conn_status)\n\t\t\tipsec_gate_new_refusal = 0;" in st)
check("ipsec: the refused profile's name is never written into the control script (no ipsec down for it)",
      "rc_ipsec_down(" not in st[i_r:i_rl] and "profilename" not in st[i_r:i_rl])
check("ipsec: the profile export does not write through a NULL for a subnet without '/'",
      "if ((p = strchr(buf, '/')) != NULL)\t/* reaper 2026-11-10: a subnet without a prefix length */\n\t\t\t\t\t*p = '\\0';" in ip
      and "p = strchr(buf, '/');\n\t\t\t\t*p = '\\0';" not in ip)
vp = rd("www/Reaper_VPNServer.asp")
check("page: '#' is refused in an IPsec user name, as in an OpenVPN one", "var IUSER_BAD = ' @*+|:?<>,./;[]\\\\=\"&#';" in vp)

shutil.rmtree(tmp, ignore_errors=True)
print("\n%d failed" % len(fails) if fails else "\nall passed")
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
