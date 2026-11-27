#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One system-log line when a removed request address is asked for (REAPER-REMOVED-LOG, v3.8.4).

WHY THIS EXISTS. v3.8.4 removed 48 request addresses nothing shipped calls (34 REAPER-UNUSED-V384B, 14 REAPER-UNUSED-V384C), after 3 on
2026-11-20 and 2 on 2026-11-17. An add-on, a script or a bookmark could still ask for one. For one beta period
httpd writes one system-log line when that happens, so the caller can be found before the net is taken out again.
The owner's conditions: the answer stays the 404 any unknown name gets; the line carries the name and the client
address, never the query string or the body; nobody on the LAN can flood the log (one line per name per boot);
and it must not become a way to tell a signed-in client from a signed-out one.
REAPER-UNUSED-CUT8 (stage 5 follow-up, owner 2026-11-27) appended two more at the end: update.cgi* and
rog_first_qos.cgi* (55 names).

WHAT IT DOES. Static: the table and the function are in httpd/httpd.c under the tag, with the delete-me note; the
one call sits first in handle_request()'s no-handler branch (after the handler loop, where no login check ran), is
handed the query-less url and the client address only; every address in the table has no row left in
mime_handlers[] and every v3.8.4 removal is in the table. Compiled: the block is built on the host with httpd.c's
own match() / match_one() and a recording logmessage(), then driven: one line per name, none on repeats, none for
other names, none from a second process sharing the seen-file (the other listener, or httpd restarted), again after
a "reboot" (file gone), the client text reduced to address characters, a symlinked seen-file not followed, and no
surviving handler pattern of web.c matches a removed name (it would be served, not answered 404).

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
HC = os.path.join(SRC, "httpd", "httpd.c")
if not SRC or not os.path.isfile(HC):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

FAILS = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond or not detail else ": " + str(detail)[:500]))
    if not cond:
        FAILS.append(name)

hc = open(HC, encoding="utf-8", errors="surrogateescape").read()
web = open(os.path.join(SRC, "httpd", "web.c"), encoding="utf-8", errors="surrogateescape").read()

# the addresses the net must know: (table pattern, a concrete request name it stands for)
OLD = [("renew_ikev2_cert_mobile.pem", "renew_ikev2_cert_mobile.pem"), ("renew_ikev2_cert_windows.der", "renew_ikev2_cert_windows.der"),
       ("jffsupload.cgi*", "jffsupload.cgi"), ("set_fw_path.cgi", "set_fw_path.cgi"), ("backup_jffs*.tar", "backup_jffs_RT-BE96U.tar")]
B1 = ["blocking.cgi", "get_nt_db.cgi*", "update_InfectedEventJson_security.cgi*", "get_ccevent_data.cgi*",
      "get_dns_block_stats.cgi", "get_dns_block_list.cgi", "get_dns_block_list_insert_or_update.cgi",
      "set_ipsec_profile.cgi*", "ipsecupload.cgi*", "ipsec_s2s_upload.cgi*", "upload_server_ipsec_cert.cgi*",
      "caupload.cgi*", "exec_force_cable_diag.cgi", "feedback_mail.cgi*", "dfb_log.cgi", "networkmap.tar",
      "set_app_mnt.cgi*", "get_app_mnt.cgi*", "ftpServerTree.cgi*", "set_usb_bk.cgi*"]
B2 = ["set_family_group.cgi", "block_device_internet.cgi", "internet_ctrl.cgi*", "del_client_data.cgi*",
      "set_pc_reward.cgi*", "get_pc_reward.cgi*", "enable_remote_control.cgi", "get_custom_clientlist.cgi",
      "nc_exist_wifi_notice.cgi", "nc_new_wifi_notice.cgi", "nc_exist_wifi_notice_app.cgi",
      "nc_new_wifi_notice_app.cgi", "nc_notice.cgi", "get_nc_conf.cgi*"]
# batch C (owner 2026-11-21, REAPER-UNUSED-V384C): appended at the end of the table
BC = ["set_iperf3_svr.cgi", "set_iperf3_cli.cgi", "get_iperf3_state.cgi", "splash_page.cgi*", "splash_page_del.cgi*",
      "create_sdn_profile.cgi*", "create_sdn_mwl.cgi*", "create_sdn_legacy.cgi*", "reset_sdn_rule.cgi*",
      "auto_guestnetwork.cgi", "wl_apply.cgi*", "set_wl_band.cgi*", "mld_enable.cgi*", "clean_ddns.cgi*"]
# REAPER-UNUSED-CUT8 (stage 5 follow-up, owner 2026-11-27): appended after batch C
CUT8 = ["update.cgi*", "rog_first_qos.cgi*"]
WANT = OLD + [(p, p.rstrip("*")) for p in B1 + B2 + BC + CUT8]

# ------------------------------------------------------------------------------------------------ static
a = hc.find("/* REAPER-REMOVED-LOG (v3.8.4)")
b = hc.find("\nint web_write(const char *buffer, int len, FILE *stream)")
have = a >= 0 and b > a
check("httpd.c: the REAPER-REMOVED-LOG block is there, before web_write()", have)
block = hc[a:b] if have else ""
check("the block says it is to be deleted after one stable version",
      "DELETE THIS BLOCK AND ITS ONE CALL AFTER ONE STABLE VERSION" in block)
tm = re.search(r"static const struct \{ const char \*head, \*rest; \} reaper_removed_addr\[\] = \{(.*?)\n\};", block, re.S)
pairs = re.findall(r'\{ "([^"]*)", "([^"]*)" \}', re.sub(r"/\*.*?\*/", "", tm.group(1), flags=re.S)) if tm else []
table = [h + r for h, r in pairs]
check("the table is a const array of two-piece names ending in { NULL, NULL }",
      bool(table) and re.search(r"\{ NULL, NULL \}\s*\n\};", block) is not None)
check("every name is split after its first four characters",
      bool(pairs) and all(len(h) == 4 and r for h, r in pairs), [x for x in pairs if len(x[0]) != 4][:3])
lits = re.findall(r'"((?:\\.|[^"\\\n])*)"', re.sub(r"/\*.*?\*/", "", hc, flags=re.S))
# update.cgi is a tail of a longer removed name of the table itself (dns_block_list_insert_or_update.cgi), so the
# substring test cannot hold for it; the image proves its removal by the handler's own text (verify_markers !arg%d)
INSIDE = {"update.cgi"}
whole = sorted(set(t.rstrip("*") for t in table if t.rstrip("*") not in INSIDE and any(t.rstrip("*") in l for l in lits)))
check("httpd.c holds no removed address as one string literal (the image check 'usr/sbin/httpd|!name' stays provable)",
      bool(table) and not whole, whole)
check("update.cgi is in no string literal of httpd.c except inside the longer removed name dns_block_list_insert_or_update.cgi",
      not [l for l in lits if "update.cgi" in l and "dns_block_list_insert_or_" not in l])
missing = [p for p, _ in WANT if p not in table]
check("the table holds the 2 addresses of 2026-11-17, the 3 of 2026-11-20, the 34 + 14 of v3.8.4 and the 2 of REAPER-UNUSED-CUT8 (55)",
      not missing and len(table) == len(set(table)) == 55,
      "missing %s, %d entries" % (missing, len(table)))
check("hooks are not in the table (addresses only)", not [t for t in table if "." not in t])
check("batch C and then REAPER-UNUSED-CUT8 sit at the END of the table (a name's position is its byte in the seen-file: older positions did not move)",
      table[:39] == [p for p, _ in OLD] + B1 + B2 and table[39:53] == BC and table[53:] == CUT8, table[50:])

mh = re.search(r"struct mime_handler mime_handlers\[\] =\s*\{(.*?)\n\};", web, re.S)
def nocomment_c(text):
    """C comments out, string literals untouched (an address pattern such as "js/*" is not a comment start)"""
    return re.sub(r'"(?:\\.|[^"\\\n])*"|/\*.*?\*/|//[^\n]*',
                  lambda m: m.group(0) if m.group(0).startswith('"') else " ", text, flags=re.S)

rows_txt = nocomment_c(mh.group(1)) if mh else ""
rows = re.findall(r'^\s*\{\s*"([^"]+)"\s*,', rows_txt, re.M)
check("web.c: mime_handlers[] found", len(rows) > 200, len(rows))
still = [t for t in table if t in rows]
check("no address in the table still has a row in mime_handlers[]", not still, still)

fm = re.search(r"static void reaper_removed_note\(const char \*u, const char \*client\)\n\{(.*?)\n\}\n", block, re.S)
body = fm.group(1) if fm else ""
check("reaper_removed_note(u, client) is defined in the block", bool(body))
check("the function is given two strings and reads no request global (file, cookies, referer, post data, login state)",
      not re.search(r"\b(file|cookies|referer|referer_url|post_buf|conn_fp|login_state|auth_result|url_do_auth|reaper_req_authed|host_name|useragent)\b", body), body[:200])
lm = re.findall(r"logmessage\((.*?)\);", body, re.S)
check("one logmessage call: two %s - the table's own name (pat, built from the two pieces only) and the cleaned client address",
      len(lm) == 1 and lm[0].count("%s") == 2 and re.search(r"\bpat\b", lm[0]) is not None and re.search(r"\bwho\b", lm[0]) is not None
      and re.search(r"[,(]\s*u\s*[,)]", lm[0]) is None and "client" not in lm[0]
      and 'snprintf(pat, sizeof(pat), "%s%s", reaper_removed_addr[i].head, reaper_removed_addr[i].rest);' in body
      and body.count("snprintf(pat,") == 1 and "char pat[64]" in body and max([len(t) for t in table] or [99]) < 64, lm)
check("the seen-file is opened without following a link, mode 0600, and locked without waiting",
      "O_NOFOLLOW" in body and "0600" in body and "LOCK_EX | LOCK_NB" in body and '"/tmp/reaper/httpd.removed"' in block)

hs = hc.find("static void\nhandle_request(void)")
hr = hc[hs:hc.find("\nuaddr *uaddr_ston(", hs)] if hs >= 0 else ""
calls = [m.start() for m in re.finditer(r"reaper_removed_note\(", hc)]
check("exactly one call beside the definition", len(calls) == 2, len(calls))
loop = hr.find("for (handler = &mime_handlers[0]; handler->pattern; handler++) {")
nob = hr.find("\tif (!handler->pattern){\n")
call = hr.find("reaper_removed_note(url, temp_ip_str);")
check("the call is the first statement of the no-handler branch, after the handler loop",
      0 <= loop < nob < call and hr[nob:call].strip() == "if (!handler->pattern){", hr[nob:nob + 120] if nob >= 0 else "")
tail = hr[call:] if call >= 0 else ""
check("the answer is unchanged: the long-name bounce and the plain 404 follow as before",
      'send_error( 404, "Not Found", (char*) 0, "File not found." );' in tail and "cloud_sync.asp?flag=%s" in tail
      and tail.find("reaper_removed_note") == 0 and "auth_check(" not in tail and "send_login_page(" not in tail)
check("it is handed the url without its query string (url is cut at '?') and the client address",
      re.search(r"if \(\(query = index\(file, '\?'\)\) != NULL\) \{", hr) is not None
      and "temp_ip_str = safe_uaddr_ntop(&login_uip_tmp, uip_tmp, sizeof(uip_tmp));" in hr)
check("no login decision is made between the handler loop's end and the call (same path signed in or out)",
      nob >= 0 and "auth" not in hr[nob:call] and "login" not in hr[nob:call])
check("tagged at both sites (the block and the call)", block.count("REAPER-REMOVED-LOG") >= 1 and "REAPER-REMOVED-LOG" in hr[call:call + 120])

# ------------------------------------------------------------------------------------------------ compiled
ma = hc.find("int\nmatch( const char* pattern, const char* string )")
mb = hc.find("\nint web_write(const char *buffer, int len, FILE *stream)")
check("httpd.c: match() / match_one() found for the harness", 0 <= ma < mb)
if not (have and body and 0 <= ma < mb):
    print("%d FAILED" % len(FAILS)); sys.exit(1)
matcher = hc[ma:a]
tmp = tempfile.mkdtemp(prefix="rmlog_")
seen = os.path.join(tmp, "httpd.removed")
blk = block.replace('"/tmp/reaper/httpd.removed"', '"%s"' % seen)
survivors = [r for r in rows if r not in table]
harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <ctype.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/file.h>
int match( const char* pattern, const char* string );
int match_one( const char* pattern, int patternlen, const char* string );
static int nlog;
static char lastlog[512];
static void logmessage(const char *tag, const char *fmt, ...)
{
	va_list ap;
	(void)tag;
	va_start(ap, fmt); vsnprintf(lastlog, sizeof(lastlog), fmt, ap); va_end(ap);
	nlog++;
	printf("LOG %s\n", lastlog);
}
''' + matcher + blk + r'''
static const char *const survivors[] = { ''' + ", ".join('"%s"' % s.replace("\\", "\\\\") for s in survivors) + r''', NULL };
int main(int argc, char **argv)
{
	int i, j, n;
	if (argc > 1 && !strcmp(argv[1], "one")) {	/* one request: name, client */
		reaper_removed_note(argv[2], argv[3]);
		return nlog;
	}
	if (argc > 1 && !strcmp(argv[1], "flood")) {	/* the same and other names, many times */
		for (i = 0; i < 20000; i++) {
			reaper_removed_note(argv[2], "192.168.50.77");
			reaper_removed_note("no_such_thing.cgi", "192.168.50.77");
			reaper_removed_note("index.asp", "192.168.50.77");
		}
		return nlog;
	}
	if (argc > 1 && !strcmp(argv[1], "all")) {	/* every concrete name given, twice */
		for (j = 0; j < 2; j++)
			for (i = 2; i < argc; i++)
				reaper_removed_note(argv[i], "fe80::1");
		printf("N %d\n", nlog);
		return 0;
	}
	if (argc > 1 && !strcmp(argv[1], "served")) {	/* would a surviving handler pattern take a removed name? */
		n = 0;
		for (i = 2; i < argc; i++)
			for (j = 0; survivors[j]; j++)
				if (match(survivors[j], argv[i])) {
					printf("SERVED %s by %s\n", argv[i], survivors[j]);
					n++;
				}
		return n ? 1 : 0;
	}
	return 99;
}
'''
src = os.path.join(tmp, "h.c")
exe = os.path.join(tmp, "h")
open(src, "w", encoding="utf-8", errors="surrogateescape").write(harness)
r = subprocess.run([CC, "-Wall", "-Wextra", "-Wno-unused-parameter", "-O1", "-o", exe, src], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
out = r.stdout.decode("utf-8", errors="replace")
check("the block compiles on the host with httpd.c's own matcher", r.returncode == 0, out[-800:])
check("... without a warning", r.returncode == 0 and "warning" not in out, out[-800:])
if r.returncode != 0:
    print("%d FAILED" % len(FAILS)); sys.exit(1)

def run(*args):
    p = subprocess.run([exe] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", errors="replace")
def reboot():
    if os.path.lexists(seen):
        os.unlink(seen)

reboot()
rc, o = run("one", "blocking.cgi", "192.168.50.23")
check("a removed address: one line with the name and the client address",
      rc == 1 and o.strip() == "LOG reaper: a request for the removed address blocking.cgi came from 192.168.50.23 (written once per boot)", o)
rc, o = run("one", "blocking.cgi", "192.168.50.99")
check("the same address from a second process (the other listener, or httpd restarted): no second line", rc == 0 and o == "", o)
check("the seen-file is private (0600)", os.path.isfile(seen) and (os.stat(seen).st_mode & 0o777) == 0o600, oct(os.stat(seen).st_mode) if os.path.exists(seen) else "absent")
reboot()
rc, o = run("one", "blocking.cgi", "192.168.50.99")
check("after a boot (the file under /tmp is gone) the line is written again, once", rc == 1 and "192.168.50.99" in o, o)
reboot()
rc, o = run("flood", "set_family_group.cgi")
check("60000 requests, a third of them for one removed address: exactly one line", rc == 1 and o.count("LOG ") == 1, o[:300])
rc, o = run("flood", "set_family_group.cgi")
check("... and none when the flood is repeated by another process", rc == 0 and o == "", o[:300])
reboot()
conc = [c for _, c in WANT]
rc, o = run("all", *conc)
lines = [l for l in o.split("\n") if l.startswith("LOG ")]
named = set(re.findall(r"removed address (\S+) came", o))
check("every one of the 55 addresses is recognised by a concrete request name; each line once though asked twice",
      "N 55" in o and len(lines) == 55 and named == set(p for p, _ in WANT), "%d lines; missing %s" % (len(lines), sorted(set(p for p, _ in WANT) - named)))
check("the line names the table's entry, never the requested text (backup_jffs_RT-BE96U.tar is logged as backup_jffs*.tar)",
      "backup_jffs*.tar" in o and "backup_jffs_RT-BE96U" not in o, o[:200])
check("IPv6 client addresses are kept", o.count("came from fe80::1 ") == 55)
reboot()
for nm in ("blocking.cgi?x=1", "sub/blocking.cgi", "blocking.cgix", "xblocking.cgi", "Blocking.cgi", "blocking.asp", "appGet.cgi", "", "set_family_group.cgi/../x"):
    rc, o = run("one", nm, "192.168.50.23")
    if rc != 0:
        check("a name that is not a removed address writes nothing: %r" % nm, False, o)
        break
else:
    check("names that are not a removed address (a query left on, another folder, another case, a longer name) write nothing", True)
check("... and leave no seen mark", not os.path.exists(seen) or not open(seen, "rb").read().strip(b"\0"))
reboot()
rc, o = run("one", "nc_notice.cgi", "10.0.0.5\nJan  1 00:00:00 kernel: forged <b>line</b> %s%n")
check("a hostile client text is reduced to address characters (digits, a-f, dot, colon), one log line",
      rc == 1 and o.count("\n") == 1 and re.search(r"came from 10\.0\.0\.5[0-9a-fA-F.:]* \(written", o) is not None and "forged" not in o and "%" not in o.split("came from")[1], o)
reboot()
rc, o = run("one", "nc_notice.cgi", "")
check("no client address known: the line says so", rc == 1 and "came from an unknown address" in o, o)
reboot()
victim = os.path.join(tmp, "victim")
open(victim, "w").write("precious")
os.symlink(victim, seen)
rc, o = run("one", "dfb_log.cgi", "192.168.50.23")
check("a symlink planted as the seen-file is not followed; the process still writes its one line",
      rc == 1 and open(victim).read() == "precious", (rc, open(victim).read()))
reboot()
rc, o = run("served", *conc)
check("no surviving mime_handlers[] pattern matches a removed address (so the request reaches the no-handler 404)", rc == 0, o[:400])
shutil.rmtree(tmp, ignore_errors=True)

if FAILS:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
print("all passed")
