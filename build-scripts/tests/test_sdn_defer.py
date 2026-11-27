#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Network page: several changes, one Wi-Fi restart; Delete selected (v3.8.4, plan item 1, stages 1 and 2).

WHY THIS EXISTS. Router evidence 2026-11-16 (one AiMesh node paired): four Network-page actions in nine minutes made
nine Wi-Fi restarts, each dropping every client on every band; three of them were requested by the AiMesh sync
service after httpd handed it the save. Owner-approved design (2026-11-16): with a switch on the page (OFF at
factory, kept in backups) a create / edit / switch-on is stored at once and its restart held; Apply now - or the
next request that runs: a switch-off, a delete, a LAN-port change, a save on any page - takes the held list and the
held settings with it in ONE hand-off. A change is held only when every enabled network stays enabled with the same
VLAN, bridge, portal type and radio group: a network stored as off or deleted while its bridge is up would lose its
guest isolation at the next firewall build. rc runs the rest when another change restarts the radios meanwhile.
Delete selected removes ticked networks in one request through the stock multi-delete form.

WHAT IT RUNS. Compiles httpd's RDEFER-PURE block (httpd/web.c) on the host: the service order / de-duplication /
256-character cap of the combined list, which lists may wait, the safety predicate (switch-off, delete, VLAN /
bridge / portal / radio-group change refused), the waiting-network items, the marker file. Compiles rc's
RDEFER-RC-PURE block (rc/sdn.c): the radio-restart test and the remainder. Runs www/reaper/reaper_sdn_defer.js
under node with stubs (the save wrapper, the held-save after-code, the names) and sdn.js's Delete-selected helpers
(eligibility, the one request). Then pins every call site and the tokens in every language pack.

Exit 0 pass, 1 fail, 77 skipped (no router tree, or no gcc; node runs are skipped without node)."""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    skip("no router tree with httpd/web.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")
NODE = shutil.which("node")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read().replace("\r\n", "\n")

def between(s, a, b):
    i = s.find(a)
    if i < 0:
        return ""
    j = s.find(b, i + len(a))
    return s[i:j] if j > 0 else ""

web, sdn, svc, rch = read("httpd/web.c"), read("rc/sdn.c"), read("rc/services.c"), read("rc/rc.h")
dfl = read("shared/defaults.c")
SJ = "www/sysdep/FUNCTION/SDN/SDN/"
sj, shtml, mhtml = read(SJ + "sdn.js"), read(SJ + "sdn.html"), read(SJ + "mlo.html")
dj, dash = read("www/reaper/reaper_sdn_defer.js"), read("www/Main_ReaperDash.asp")
TMP = tempfile.mkdtemp()

def build(name, code):
    c = os.path.join(TMP, name + ".c"); exe = os.path.join(TMP, name)
    open(c, "w").write(code)
    r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
    return exe if r.returncode == 0 else None, r.stderr

COMMON = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
static size_t strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l < n - 1 ? l : n - 1; memcpy(d, s, c); d[c] = 0; } return l; }
'''

# ---------------------------------------------------------------- 1. httpd pure block
m = re.search(r"/\* RDEFER-PURE-BEGIN.*?\*/(.*?)/\* RDEFER-PURE-END \*/", web, re.S)
check("httpd/web.c carries the RDEFER-PURE block once", m is not None and web.count("RDEFER-PURE-BEGIN") == 1)
if m:
    code = COMMON + r'''
static int fake_root = 1;
static int t_fstat(int fd, struct stat *st) { int r = fstat(fd, st); if (r == 0 && fake_root) st->st_uid = 0; return r; }
#define fstat(a, b) t_fstat(a, b)
''' + m.group(1) + r'''
#undef fstat
int main(int argc, char **argv)
{
	char out[512], items[RDEFER_ITEMS], l[300];
	long t = 0;
	switch (argv[1][0]) {
	case 'c': {	/* c a b [cap] */
		size_t cap = argc > 4 ? (size_t)atoi(argv[4]) : RDEFER_MAX + 1;
		int r = rdefer_combine(argv[2], argv[3], out, cap);
		printf("%d|%s\n", r, r == 0 ? out : "");
		break; }
	case 'o': printf("%d\n", rdefer_list_ok(argv[2])); break;
	case 's': printf("%d\n", rdefer_safe(argv[2], argv[3], argv[4], argv[5], argv[6], argv[7])); break;
	case 'i': rdefer_items(argv[2], argv[3], argv[4], argv[5], argv[6], argv[7], argv[8], argv[9], items, sizeof(items)); printf("%s\n", items); break;
	case 'w': printf("%d\n", rdefer_mark_write(argv[2], atol(argv[3]), argv[4], argv[5])); break;
	case 'r': fake_root = argc < 4;
		{ int ok = rdefer_mark_read(argv[2], &t, l, sizeof(l), items, sizeof(items));
		  printf("%d|%ld|%s|%s\n", ok, ok ? t : 0, ok ? l : "", ok ? items : ""); }
		break;
	}
	return 0;
}
'''
    exe, err = build("rdefer", code)
    check("RDEFER-PURE compiles with -Wall -Werror", exe is not None, err)
    if exe:
        def run(*a):
            return subprocess.run([exe] + [str(x) for x in a], capture_output=True, text=True).stdout.strip()
        # combine: order, de-dup, plain restart_sdn, cap
        check("combine: two creates -> one radio restart, both networks, tails once, in service order",
              run("c", "restart_wireless;restart_sdn 4;restart_qos;restart_firewall;", "restart_firewall;restart_wireless;restart_sdn 5;restart_qos;")
              == "0|restart_wireless;restart_sdn 4;restart_sdn 5;restart_qos;restart_firewall;")
        check("combine: ledg first, delete before the radio restart, plain restart_sdn with a delete",
              run("c", "restart_wireless;restart_sdn 4;", "restart_ledg;start_sdn_del;restart_wireless;restart_qos;")
              == "0|restart_ledg;start_sdn_del;restart_wireless;restart_sdn;restart_qos;")
        check("combine: restart_net_and_phy replaces restart_wireless",
              run("c", "restart_wireless;restart_sdn 4;", "restart_net_and_phy;") == "0|restart_net_and_phy;restart_sdn 4;")
        check("combine: more than three networks -> plain restart_sdn",
              run("c", "restart_wireless;restart_sdn 1;restart_sdn 2;restart_sdn 3;", "restart_wireless;restart_sdn 5;") == "0|restart_wireless;restart_sdn;")
        check("combine: three networks stay per network",
              run("c", "restart_wireless;restart_sdn 1;restart_sdn 2;", "restart_wireless;restart_sdn 3;") == "0|restart_wireless;restart_sdn 1;restart_sdn 2;restart_sdn 3;")
        check("combine: portal, guest, stubby and VPN tails in their places",
              run("c", "restart_wireless;restart_sdn 4;start_vpnclient2;restart_stubby;", "restart_wireless;restart_sdn 6;restart_chilli;restart_uam_srv;restart_reaper_guest;")
              == "0|restart_wireless;restart_sdn 4;restart_sdn 6;restart_chilli;restart_uam_srv;restart_reaper_guest;restart_stubby;start_vpnclient2;")
        check("combine: another page's service runs after the Network page's, in its own order",
              run("c", "restart_wireless;restart_sdn 4;", "restart_dnsmasq;restart_wireless;restart_vpnclient1;")
              == "0|restart_wireless;restart_sdn 4;restart_dnsmasq;restart_vpnclient1;")
        check("combine: a reboot runs alone (a boot applies everything stored)",
              run("c", "restart_wireless;restart_sdn 4;", "reboot;") == "0|reboot;")
        check("combine: empty pieces and duplicates dropped", run("c", ";;restart_wireless;;", "restart_wireless;restart_sdn 4;;") == "0|restart_wireless;restart_sdn 4;")
        check("combine: whole names only (restart_sdnx / start_vpnclient / restart_sdn x are other services)",
              run("c", "", "restart_sdnx;start_vpnclient;restart_sdn x;restart_wireless;") == "0|restart_wireless;restart_sdnx;start_vpnclient;restart_sdn x;")
        long_a = "restart_wireless;" + "".join("restart_sdn %d;" % i for i in (11, 12, 13))
        many = ";".join("restart_custom_service_%02d" % i for i in range(12)) + ";"
        r = run("c", long_a, many)
        check("combine: the result never exceeds 255 characters (rc's nv[256]); too long -> -1",
              r == "-1|", r)
        r = run("c", "restart_wireless;restart_sdn 4;", "restart_qos;", "42")
        check("combine: per-network form does not fit -> plain restart_sdn retried", r == "0|restart_wireless;restart_sdn;restart_qos;", r)
        r = run("c", "restart_wireless;" + "".join("restart_sdn %d;" % i for i in range(1, 34)), "")
        check("combine: more than 32 distinct services -> refused", r == "-1|", r)
        # which lists may wait
        check("may wait: create / edit / switch-on lists (radio restart + own network + qos / firewall / stubby / VPN / LED)",
              run("o", "restart_wireless;restart_sdn 4;") == "1" and run("o", "restart_ledg;restart_wireless;restart_sdn 4;restart_qos;restart_firewall;restart_stubby;start_vpnclient3;") == "1")
        check("may not wait: delete, LAN ports, reboot, portal, light guest save, plain restart_sdn, no radio restart, other services",
              all(run("o", x) == "0" for x in ("start_sdn_del;restart_wireless;", "restart_net_and_phy;", "restart_wireless;restart_sdn 4;reboot;",
                                                 "restart_wireless;restart_sdn 4;restart_chilli;restart_uam_srv;", "restart_reaper_guest;",
                                                 "restart_wireless;restart_sdn;", "restart_sdn 4;restart_firewall;", "restart_wireless;restart_dnsmasq;", "")))
        # safety predicate
        VL = "<1>52>0<2>53>0"
        SU = "<1>br52>192.168.52.1>255.255.255.0>1<2>br53>192.168.53.1>255.255.255.0>1"
        S0 = "<0>DEFAULT>1>0>0>0>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0<4>Guest>1>1>1>4>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0"
        S_NEW = S0 + "<5>IoT>1>2>2>5>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0"
        S_OFF5 = S0 + "<5>IoT>0>2>2>5>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0"
        check("safe: a new network (nothing that is up changes)", run("s", S0, VL, SU, S_NEW, VL, SU) == "1")
        check("safe: an off network switched on", run("s", S_OFF5, VL, SU, S_NEW, VL, SU) == "1")
        check("safe: an edit that keeps the identity (VPN field)", run("s", S0, VL, SU, S0.replace("<4>Guest>1>1>1>4>0", "<4>Guest>1>1>1>4>6"), VL, SU) == "1")
        check("safe: an edit of an off network", run("s", S_OFF5, VL, SU, S_OFF5.replace("IoT", "IoT2"), VL, SU) == "1")
        check("refused: switch-off of an enabled network", run("s", S0, VL, SU, S0.replace("<4>Guest>1", "<4>Guest>0"), VL, SU) == "0")
        check("refused: delete of an enabled network", run("s", S_NEW, VL, SU, S0, VL, SU) == "0")
        check("refused: VLAN id of an enabled network changed", run("s", S0, VL, SU, S0, "<1>60>0<2>53>0", SU) == "0")
        check("refused: VLAN row of an enabled network re-pointed", run("s", S0, VL, SU, S0.replace("<4>Guest>1>1", "<4>Guest>1>2"), VL, SU) == "0")
        check("refused: bridge of an enabled network changed", run("s", S0, VL, SU, S0, VL, SU.replace("br52", "br60")) == "0")
        check("refused: portal type of an enabled network changed",
              run("s", S0, VL, SU, S0.replace("<4>Guest>1>1>1>4>0>0>0>0>0>0", "<4>Guest>1>1>1>4>0>0>0>0>0>2"), VL, SU) == "0")
        check("refused: radio group of an enabled network changed", run("s", S0, VL, SU, S0.replace("<4>Guest>1>1>1>4", "<4>Guest>1>1>1>7"), VL, SU) == "0")
        check("refused: an enabled network whose VLAN / subnet row is missing", run("s", S0, "", SU, S0, "", SU) == "0" and run("s", S0, VL, "", S0, VL, "") == "0")
        check("refused: a malformed row (no index)", run("s", S0 + "<>x>1", VL, SU, S0, VL, SU) == "0")
        check("refused: more networks than the table holds",
              run("s", "".join("<%d>n>0>0>0>%d" % (i, i) for i in range(70)), "", "", S0, VL, SU) == "0")
        # items
        check("items: new / switched on / edited, judged from before and after",
              run("i", "", "restart_wireless;restart_sdn 5;", S0, VL, SU, S_NEW, VL, SU) == "5n"
              and run("i", "", "restart_wireless;restart_sdn 5;", S_OFF5, VL, SU, S_NEW, VL, SU) == "5o"
              and run("i", "", "restart_wireless;restart_sdn 4;", S0, VL, SU, S0, VL, SU) == "4e")
        check("items: merged with the earlier ones, the strongest kind kept",
              run("i", "5n,4e", "restart_wireless;restart_sdn 5;restart_sdn 4;", S_NEW, VL, SU, S_NEW, VL, SU) == "5n,4e"
              and run("i", "4e", "restart_wireless;restart_sdn 5;", S_OFF5, VL, SU, S_NEW, VL, SU) == "4e,5o")
        check("items: junk in the old list dropped; a network missing after the save not listed",
              run("i", "x9,4q,5e", "restart_wireless;restart_sdn 9;", S0, VL, SU, S0, VL, SU) == "5e")
        # marker
        mk = os.path.join(TMP, "mark")
        check("marker written root-only (0600) as '<uptime> <list>' + items, and read back",
              run("w", mk, 1234, "restart_wireless;restart_sdn 4;", "4n") == "0" and (os.stat(mk).st_mode & 0o777) == 0o600
              and open(mk).read() == "1234 restart_wireless;restart_sdn 4;\n4n\n"
              and run("r", mk) == "1|1234|restart_wireless;restart_sdn 4;|4n")
        check("marker: not root's -> refused; junk items -> no items", run("r", mk, "x") == "0|0||"
              and (open(mk, "w").write("7 restart_wireless;\n<b>\n") and run("r", mk) == "1|7|restart_wireless;|"))
        check("marker: absent / malformed -> 0", run("r", mk + "x") == "0|0||"
              and (open(mk, "w").write("abc\n") and run("r", mk) == "0|0||")
              and (open(mk, "w").write("12 \n\n") and run("r", mk) == "0|0||"))

# ---------------------------------------------------------------- 1b. the settings merge, against the tree's json-c
# (release/src/router/json-c, or REAPER_JSONC_DIR; skipped when neither is there - a sparse tree has no json-c)
JSONC = next((d for d in (os.path.join(SRC, "json-c"), os.environ.get("REAPER_JSONC_DIR", ""))
              if d and os.path.isfile(os.path.join(d, "json_object.c")) and os.path.isfile(os.path.join(d, "config.h"))), "")
jfn = between(web, "static void rdefer_json_merge(json_object *dst, json_object *src)", "\n}\n")
JMAIN = r'''
int main(int argc, char **argv)
{
	json_object *a = json_tokener_parse(argv[1]), *b = json_tokener_parse(argv[2]);
	rdefer_json_merge(a, b);
	printf("%s\n", json_object_to_json_string_ext(a, JSON_C_TO_STRING_PLAIN));
	return 0;
}
'''
if not JSONC:
    print("SKIP: no json-c source next to the tree - the settings-merge runs are skipped")
elif jfn:
    jd = os.path.join(TMP, "jc")
    shutil.copytree(JSONC, jd)
    open(os.path.join(TMP, "jm.c"), "w").write('#include <stdio.h>\n#include <string.h>\n#include "json.h"\n' + jfn + "\n}\n" + JMAIN)
    srcs = [x for x in ("arraylist.c", "debug.c", "json_c_version.c", "json_object.c", "json_object_iterator.c", "json_tokener.c",
                        "json_util.c", "linkhash.c", "printbuf.c", "random_seed.c") if os.path.isfile(os.path.join(jd, x))]
    r = subprocess.run([CC, "-w", "-I" + jd, "-o", os.path.join(TMP, "jm"), os.path.join(TMP, "jm.c")] + [os.path.join(jd, x) for x in srcs] + ["-lm"],
                       capture_output=True, text=True)
    check("settings merge compiles against json-c", r.returncode == 0, r.stderr[-400:])
    if r.returncode == 0:
        def jm(a, b):
            return json.loads(subprocess.run([os.path.join(TMP, "jm"), a, b], capture_output=True, text=True).stdout)
        check("merge: a later save's value wins, new keys added, the earlier ones kept",
              jm('{"wl0_ssid":"a","apg4_enable":"1"}', '{"wl0_ssid":"b","sdn_rl":"<4>x"}') == {"wl0_ssid": "b", "apg4_enable": "1", "sdn_rl": "<4>x"})
        check("merge: an object value merged one level down (no key name assumed)",
              jm('{"g":{"x":"1","y":"2"}}', '{"g":{"y":"9","z":"8"}}') == {"g": {"x": "1", "y": "9", "z": "8"}})
        check("merge: action_script never carried over",
              jm('{}', '{"k":"v","action_script":"restart_wireless;restart_sdn 4;"}') == {"k": "v"})
        check("merge: a non-object value replaced by an object; arrays and null kept as they are",
              jm('{"g":"s"}', '{"g":{"o":1},"a":[1,2],"n":null}') == {"g": {"o": 1}, "a": [1, 2], "n": None})

# ---------------------------------------------------------------- 2. rc pure block
m = re.search(r"/\* RDEFER-RC-PURE-BEGIN.*?\*/(.*?)/\* RDEFER-RC-PURE-END \*/", sdn, re.S)
check("rc/sdn.c carries the RDEFER-RC-PURE block once", m is not None and sdn.count("RDEFER-RC-PURE-BEGIN") == 1)
if m:
    exe, err = build("rcdefer", COMMON + m.group(1) + r'''
int main(int argc, char **argv)
{
	char out[256];
	if (argv[1][0] == 'r') printf("%d\n", reaper_sdn_defer_radio(argv[2]));
	else { rdefer_remainder(argv[2], out, sizeof(out)); printf("[%s]\n", out); }
	return 0;
}
''')
    check("RDEFER-RC-PURE compiles with -Wall -Werror", exe is not None, err)
    if exe:
        def run(*a):
            return subprocess.run([exe] + list(a), capture_output=True, text=True).stdout.strip()
        check("rc: restart_wireless / restart_net_and_phy are radio restarts (whole names)",
              run("r", "restart_qos;restart_wireless;") == "1" and run("r", "restart_net_and_phy;") == "1"
              and run("r", "restart_wireless_x;restart_sdn 4;") == "0" and run("r", "") == "0")
        check("rc: the remainder drops only the radio restarts",
              run("m", "restart_ledg;restart_wireless;restart_sdn 4;restart_sdn 5;restart_qos;") == "[restart_ledg;restart_sdn 4;restart_sdn 5;restart_qos;]"
              and run("m", "restart_wireless;") == "[]")

# ---------------------------------------------------------------- 3. httpd call sites
ac = between(web, "static int\napply_cgi(", "\nAPPLY_FINISH:")
i_snap = ac.find("rdefer_snap_take(&rdefer_s, root);")
i_val = ac.find("if (!validate_apply(wp,root)) {")
i_plus = ac.find("static char reaper_rcsvc[1024];")
i_call = ac.find("if (rdefer_apply(root, &rdefer_s, &action_para, res))\n\t\t\taction_para = NULL;\n\t\trdefer_snap_free(&rdefer_s);")
i_hand = ac.find("if(action_para && strlen(action_para) > 0 && !check_xss_blacklist(action_para, 0)) {")
check("apply_cgi: snapshot before validate_apply; decision after the '+' fix and before the hand-off; held = nothing sent",
      0 < i_snap < i_val < i_plus < i_call < i_hand, (i_snap, i_val, i_plus, i_call, i_hand))
check("apply_cgi: the stock hand-off (pending record, signal) is untouched",
      "reaper_sdn_pending(action_para);	/* reaper 2026-11-12: the router applies its own guest-network request */\n\n\t\t\t\t/* trigger cfg_server to send notification */\n\t\t\t\tkill_pidfile_s(CFG_SERVER_PID, SIGUSR2);" in ac)
ra = between(web, "static int rdefer_apply(json_object *root,", "\n}\n")
check("rdefer_apply: holds only a Network-page save (snapshot taken), never on Apply now, only a list that may wait, only when safe",
      "if (s->sdn && !apply_now && *a && rdefer_list_ok(a) &&" in ra and "rdefer_safe(s->sdn, s->vlan, s->subnet, nvram_safe_get(\"sdn_rl\")" in ra
      and "rdefer_list_ok(combined)" in ra)
check("rdefer_apply: a held save clears cfg_changed and never records a pending request or signals the sync service",
      "cfg_changed = 0;" in ra and "reaper_sdn_pending" not in ra and "SIGUSR2" not in ra and "notify_rc" not in ra
      and '"reaper_deferred", json_object_new_string("1")' in ra)
check("rdefer_apply: the held settings for the nodes are merged in (when the sync service is ready) before the hold",
      "(!cfg_changed || !is_cfg_server_ready() || rdefer_keys_add_cfg() == 0)" in ra)
check("rdefer_apply: flush merges held + this request's settings into the hand-off file under its lock, a fresh cfg_ver on Apply now",
      "lk = file_lock(CFG_APPLY_LOCK);" in ra and "rdefer_json_merge(m, c);" in ra and "json_object_to_file(CFG_JSON_FILE, m);" in ra
      and 'nvram_set("cfg_ver", ver);' in ra and ra.find("rdefer_json_merge(m, c)") < ra.find("json_object_to_file(CFG_JSON_FILE, m)"))
check("rdefer_apply: marker and settings removed before the combined list goes on; a list too long leaves them waiting",
      ra.find("unlink(RDEFER_MARK);") < ra.find("*act = combined;") and "unlink(RDEFER_KEYS);" in ra
      and "they stay waiting for Apply" in ra)
check("rdefer_apply: a save with no list while changes wait keeps the held settings the newest",
      "if (!*a && !apply_now) {" in ra and "rdefer_keys_add_cfg();\n\t\treturn 0;" in ra)
jm = between(web, "static void rdefer_json_merge(json_object *dst, json_object *src)", "\n}\n")
check("merge: key by key, no key name assumed, nested objects merged, action_script never kept",
      "json_object_object_foreach(src, key, val)" in jm and 'strcmp(key, "action_script") == 0' in jm and "rdefer_json_merge(old, val);" in jm
      and jm.count('"') == 2)
ka = between(web, "static int rdefer_keys_add_cfg(void)", "\n}\n")
check("held settings file: written root-only (mkstemp + 0600 + rename) inside the hardened /tmp/reaper",
      "mkstemp(tmp)" in ka and "fchmod(fd, 0600)" in ka and "rename(tmp, RDEFER_KEYS)" in ka and "reaper_secure_dir(REAPER_TMPDIR, 0700);" in ka)
sn = between(web, "static void rdefer_snap_take(struct rdefer_snap *s, json_object *root)", "\n}\n")
check("snapshot only for a save marked by the page while the switch is on",
      'get_cgi_json("reaper_defer", root)' in sn and 'nvram_match("reaper_sdn_defer", "1")' in sn)
check("everything under RTCONFIG_CFGSYNC and RTCONFIG_MULTILAN_CFG; files RAM-only in /tmp/reaper",
      web.count("#if defined(RTCONFIG_CFGSYNC) && defined(RTCONFIG_MULTILAN_CFG)") >= 4
      and '#define RDEFER_MARK\tREAPER_TMPDIR "/sdn_defer"' in web and '#define RDEFER_KEYS\tREAPER_TMPDIR "/sdn_defer.json"' in web)
ej = between(web, "static int ej_reaper_sdn_defer(", "\n}\n")
check("ej hook registered; prints only a checked service list and digit / kind items",
      '{ "reaper_sdn_defer", ej_reaper_sdn_defer},' in web and 'strspn(list, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_ ;")' in ej
      and 'strspn(p, "0123456789") == (size_t)(q - p - 1)' in ej)
check("new setting: default OFF in shared/defaults.c and carried by the settings file (rcfg_flags)",
      '{ "reaper_sdn_defer", "0", CKN_STR1, CKN_TYPE_DEFAULT, CKN_ACC_LEVEL_DEFAULT, CKN_ENC_DEFAULT, 0 },' in dfl
      and '{ "misc",   "reaper_sdn_defer", 2 },' in web)

# ---------------------------------------------------------------- 4. rc call sites
hn = between(svc, "void handle_notifications(void)\n{", "\nskip:\n")
tail = between(svc, "\nskip:\n\n\trun_custom_script(\"service-event-end\"", "_dprintf(\"handle_notifications() end")
check("rc: the whole list and its start time kept right after rc_service is read",
      "strlcpy(reaper_defer_nv, nv, sizeof(reaper_defer_nv));\n\treaper_defer_t0 = uptime();" in hn
      and hn.find('strlcpy(nv, nvram_safe_get("rc_service"), sizeof(nv));') < hn.find("reaper_defer_t0 = uptime();") < hn.find("again:"))
check("rc: the backstop runs after the last service, before rc_service is cleared",
      "reaper_sdn_defer_backstop(reaper_defer_nv, reaper_defer_t0);\n#endif\n\tnvram_set(\"rc_service\", \"\");" in tail)
bs = between(sdn, "void reaper_sdn_defer_backstop(const char *list, long t0)", "\n}\n")
check("rc: the backstop starts the settle applet in its own process, only after a radio restart while changes wait",
      "if (!reaper_sdn_defer_radio(list) || access(RDEFER_MARK, F_OK) != 0)" in bs and '"/sbin/reaper_sdn_settle", "defer"' in bs and "_eval(argv, NULL, 0, &pid);" in bs)
bm = between(sdn, "static int rdefer_backstop_main(long t0)", "\n}\n")
check("settle 'defer': waits for rc to go idle, runs the remainder, clears the marker only when every change predates the restart",
      'for (i = 0; i < RSDN_SETTLE_MAX && *nvram_safe_get("rc_service"); i++)' in bm and "rdefer_remainder(list, rest, sizeof(rest));" in bm
      and ("if (t < t0)\n\t\tunlink(RDEFER_MARK);" in bm or "if (t < t0 && access(RDEFER_KEYS, F_OK) != 0)\n\t\tunlink(RDEFER_MARK);" in bm)
      and "notify_rc_and_wait_2min(rest);" in bm)
if "REAPER-SDN-DEFER-KEYS" in sdn:                    # 2026-11-24 (cut-readiness review)
    check("settle 'defer': the marker stays while httpd holds settings for the AiMesh nodes (sent only with a service list), so Apply now still sends them",
          '#define RDEFER_KEYS\tRSDN_DIR "/sdn_defer.json"' in sdn and "/tmp/reaper" in sdn
          and "if (t < t0 && access(RDEFER_KEYS, F_OK) != 0)\n\t\tunlink(RDEFER_MARK);" in bm
          and bm.find("else if (t < t0)") > bm.find("unlink(RDEFER_MARK);") and "the AiMesh nodes have not received" in bm)
sm = between(sdn, "int reaper_sdn_settle_main(int argc, char *argv[])", "\n}\n")
check("settle: the 'defer' mode is dispatched before the pending-request time is parsed",
      0 < sm.find('strcmp(argv[1], "defer") == 0') < sm.find("(t0 = strtol(argv[1], NULL, 10)) <= 0"))
check("rc.h declares the two entry points", "extern int reaper_sdn_defer_radio(const char *list);" in rch
      and "extern void reaper_sdn_defer_backstop(const char *list, long t0);" in rch)

# ---------------------------------------------------------------- 5. pages
tag = '<script type="text/javascript" src="/reaper/reaper_sdn_defer.js"></script>'
check("sdn.html / mlo.html load the script once, after sdn.js (and mlo.js)",
      shtml.count(tag) == 1 and shtml.find('src="/SDN/sdn.js"') < shtml.find(tag)
      and mhtml.count(tag) == 1 and mhtml.find('src="/SDN/mlo.js"') < mhtml.find(tag))
bar = '<div id="rsdn_defer_bar" style="display:none;"></div>'
for nm, h in (("sdn.html", shtml), ("mlo.html", mhtml)):
    check("%s: the bar sits between the page title and the network list" % nm,
          h.count(bar) == 1 and h.find('<div class="function_desc_container">') < h.find(bar) < h.find('<div class="content_container">'))
check("dashboard: a server-rendered notice, read through an array (absent hook = no notice), linking the Network page",
      "var d=[<% reaper_sdn_defer(); %>][0];" in dash and 'id="rsdn_wait_badge" href="/reaper_shell.asp#Reaper_Network.asp"' in dash
      and "<#RSDN_44#>" in dash)
check("the page script keeps its state in a closure (no page globals besides the loaded mark)",
      dj.lstrip().startswith("/* REAPER-SDN-DEFER") and "\n(function(){\n\t'use strict';" in dj and dj.rstrip().endswith("})();")
      and re.search(r"^(var|let|const|function) ", dj, re.M) is None)
check("the page script: switch save carries no list; Apply now = reaper_defer_apply with no list; switch-off with changes waiting applies them",
      '{"action_mode": "apply", "reaper_sdn_defer": on ? "1" : "0"}' in dj and '{"action_mode": "apply", "reaper_defer_apply": "1"}' in dj
      and 'apply_now({"reaper_sdn_defer": "0"});' in dj)
check("www additions are ASCII", all(ord(c) < 128 for c in dj + shtml + mhtml + between(sj, "/* REAPER-SDN-MULTIDEL-BEGIN", "/* REAPER-SDN-MULTIDEL-END */")))

# ---------------------------------------------------------------- 6. Delete selected (sdn.js)
md = between(sj, "/* REAPER-SDN-MULTIDEL-BEGIN", "/* REAPER-SDN-MULTIDEL-END */")
check("sdn.js carries the REAPER-SDN-MULTIDEL block once", sj.count("/* REAPER-SDN-MULTIDEL-BEGIN") == 1 and md != "")
single = between(sj, "Get_Component_Del_Profile().appendTo($(\".popup_container.popup_element_second\")).find(\"[data-btn=del]\").click(function(e){",
                 "httpApi.nvramSet(nvramSet_obj, function(){")
for key in ('"_enable"] = "0";', '"_disabled"] = "0";', '"_rg_devs"] = "";', '"_rg_mdns"] = "";', '"_ap_isolate_lan"] = "";'):
    check("multi-delete clears what the single delete clears: %s" % key.split('"')[1], key in single and key in md)
check("multi-delete: one start_sdn_del + one radio restart, stock tails (qos / firewall, stubby, LED group), every row into sdn_rl_x",
      '"rc_service": "start_sdn_del;restart_wireless;"' in md and 'nvramSet_obj.rc_service += "restart_qos;restart_firewall;";' in md
      and 'nvramSet_obj.rc_service += "restart_stubby;";' in md and 'nvramSet_obj.rc_service = "restart_ledg;" + nvramSet_obj.rc_service;' in md
      and "$.extend(nvramSet_obj, parse_JSONToStr_del_sdn_all_rl(del_sdn_rl));" in md)

if NODE:
    # sdn.js helpers with stubs
    stub = r'''
var vlan_trunklist_orig = "", support_adguard_dns = false, support_gaming = false, support_ledg_sdn = true, ledg_sdn_json = {"Gaming": "1", "Kids": "1", "VPN": "0"};
var selected_sdn_idx = "4", game_vts_rulelist_json = [];
function mk(idx, name, vid, extra){ return Object.assign({"sdn_rl": {"idx": String(idx), "sdn_name": name, "subnet_idx": String(idx)},
  "apg_rl": {"apg_idx": String(idx), "dut_list": "<AA:BB:CC:DD:EE:FF>3>", "mlo": "0", "ssid": name + idx},
  "vlan_rl": {"vlan_idx": String(idx), "vid": String(vid)}, "subnet_rl": {"subnet_idx": String(idx), "dot_enable": "0"},
  "sdn_access_rl": [], "dhcpres_rl": {}}, extra || {}); }
var sdn_all_rl_json = [mk(0, "DEFAULT", 0), mk(1, "MAINFH", 0), mk(4, "Guest", 52), mk(5, "Kids", 53), mk(6, "IoT", 54)];
sdn_all_rl_json[4].sdn_access_rl = [{"access_sdn_idx": "4", "sdn_idx": "6"}, {"access_sdn_idx": "0", "sdn_idx": "6"}];
sdn_all_rl_json[3].dhcpres_rl = {"idx": "5"};
var vlan_rl_json = [{"vlan_idx": "4", "vid": "52"}, {"vlan_idx": "5", "vid": "53"}, {"vlan_idx": "6", "vid": "54"}];
var $ = {"each": function(a, f){ for(var i = 0; i < a.length; i++) f(i, a[i]); }, "extend": Object.assign,
  "isEmptyObject": function(o){ return !o || Object.keys(o).length == 0; }};
var httpApi = {"nvramGet": function(){ return {"qos_enable": "1"}; }};
var LAST = {};
function parse_JSONToStr_sdn_all_list(p){ LAST.left = p.sdn_all_rl.map(function(x){ return x.sdn_rl.idx; }); LAST.vlan = p.vlan_rl.map(function(x){ return x.vlan_idx; });
  LAST.acc = p.sdn_all_rl.filter(function(x){ return x.sdn_rl.idx == "6"; })[0].sdn_access_rl; return {"sdn_rl": "L"}; }
function parse_JSONToStr_del_sdn_all_rl(a){ return {"sdn_rl_x": a.map(function(x){ return x.sdn_rl.idx; }).join(",")}; }
function parse_JSONToStr_game_vts_rulelist_json(){ return ""; }
'''
    code = stub + md + r'''
const R = [];
function t(n, g, w){ R.push([n, JSON.stringify(g), JSON.stringify(w)]); }
t("eligible: a guest network", reaper_mdel_ok(sdn_all_rl_json[2], ""), true);
t("not offered: the main network / MAINFH / backhaul", [reaper_mdel_ok(sdn_all_rl_json[0], ""), reaper_mdel_ok(sdn_all_rl_json[1], ""),
  reaper_mdel_ok(mk(7, "MAINBH", 0), ""), reaper_mdel_ok(Object.assign(mk(8, "MLO", 0), {"apg_rl": {"apg_idx": "8", "mlo": "1"}}), "")], [false, false, false, false]);
t("not offered: a bound LAN port", reaper_mdel_ok(Object.assign(mk(9, "IoT", 55), {"apg_rl": {"apg_idx": "9", "dut_list": "<AA:BB:CC:DD:EE:FF>3>LAN1"}}), ""), false);
t("not offered: a VLAN while trunks exist; a network without one is", [reaper_mdel_ok(sdn_all_rl_json[2], "x"), reaper_mdel_ok(mk(10, "IoT", 0), "x")], [false, true]);
t("LED group: a type with none left goes off, others kept", reaper_mdel_ledg(["Kids"], [mk(4, "Guest", 1)], ledg_sdn_json), "1<0<0");
t("LED group: a type still present stays", reaper_mdel_ledg(["Kids"], [mk(4, "Kids", 1)], ledg_sdn_json), "1<1<0");
t("refused: an ineligible network in the selection", reaper_sdn_multi_del(["4", "1"]), null);
t("refused: an unknown index / nothing ticked", [reaper_sdn_multi_del(["4", "77"]), reaper_sdn_multi_del([])], [null, null]);
const o = reaper_sdn_multi_del(["4", "5"]);
t("one request: delete + one radio restart, LED group first, qos / firewall", o.rc_service, "restart_ledg;start_sdn_del;restart_wireless;restart_qos;restart_firewall;");
t("both rows to remove, the rest kept", [o.sdn_rl_x, LAST.left], ["4,5", ["0", "1", "6"]]);
t("their VLAN rows dropped", LAST.vlan, ["6"]);
t("Access Intranet pairs naming a removed network dropped", LAST.acc, [{"access_sdn_idx": "0", "sdn_idx": "6"}]);
t("each removed radio group off and its guest keys cleared", [o.apg4_enable, o.apg4_disabled, o.apg5_enable, o.apg5_rg_devs, o.apg5_rg_mdns, o.apg5_ap_isolate_lan], ["0", "0", "0", "", "", ""]);
t("its reservations cleared; LED value for the removed Kids type", [o.dhcpres5_rl, o.ledg_sdn], ["", "1<0<0"]);
t("the page forgets the selected network", selected_sdn_idx, "");
console.log(JSON.stringify(R));
'''
    f = os.path.join(TMP, "md.js"); open(f, "w").write(code)
    r = subprocess.run([NODE, f], capture_output=True, text=True)
    if r.returncode != 0:
        check("Delete-selected helpers run under node", False, r.stderr)
    else:
        for n, g, w in json.loads(r.stdout.strip().splitlines()[-1]):
            check(n, g == w, "got %s want %s" % (g, w))

    # the page script with stubs
    harness = r'''
var window = globalThis, document = {"getElementById": function(){ return {}; }, "createElement": function(){ return {}; }, "head": {"appendChild": function(){}}};
var CALLS = [], HOOK = {"on": 1, "wait": 0, "list": "", "items": []}, TIMERS = [];
var J = new Proxy(function(){}, {"get": function(t, k){ if(k == "length") return 1; if(k == "each") return function(a, f){ (a || []).forEach(function(x, i){ f(i, x); }); };
  if(k == "extend") return Object.assign; return J; }, "apply": function(t, self, args){ if(typeof args[0] == "function") args[0](); return J; }});
var $ = J;
window.setTimeout = function(fn, ms){ TIMERS.push(ms); return 0; };
window.showLoading = function(s){ CALLS.push("load:" + s); };
window.isWLclient = function(){ return true; };
var httpApi = {"nvramSet": function(post, handler){ CALLS.push(JSON.stringify(post)); if(handler) handler.call(RESP); },
  "hookGetAsync": function(q){ CALLS.push("hook"); q.success(HOOK); }};
var RESP = {};
''' + dj + r'''
const R = [];
function t(n, g, w){ R.push([n, JSON.stringify(g), JSON.stringify(w)]); }
t("loaded once; the old save function kept underneath", typeof window.reaperSdnDefer, "object");
CALLS = []; RESP = {"modify": "1"};
httpApi.nvramSet({"action_mode": "apply", "rc_service": "restart_wireless;restart_sdn 4;"}, function(){});
t("switch on: a save with a list is marked for httpd", CALLS[0], JSON.stringify({"action_mode": "apply", "rc_service": "restart_wireless;restart_sdn 4;", "reaper_defer": "1"}));
CALLS = [];
httpApi.nvramSet({"action_mode": "apply", "reaper_sdn_defer": "1"}, null);
t("a save without a list is not marked", CALLS[0], JSON.stringify({"action_mode": "apply", "reaper_sdn_defer": "1"}));
CALLS = []; TIMERS = []; RESP = {"modify": "1", "reaper_deferred": "1"};
var seen = {};
httpApi.nvramSet({"action_mode": "apply", "rc_service": "restart_wireless;restart_sdn 5;"}, function(){
  seen.wl = isWLclient(); showLoading(20); setTimeout(function(){}, 20000); seen.self = this; });
t("held: the page's after-save code runs with a one-second wait and no reconnect card", [seen.wl, CALLS.indexOf("load:1") != -1, TIMERS], [false, true, [1000]]);
t("held: the response reaches the page's code, the bar is refreshed", [seen.self === RESP, CALLS.indexOf("hook") != -1], [true, true]);
TIMERS = []; showLoading(9); setTimeout(function(){}, 9000);
t("held: the page's helpers are restored afterwards", [isWLclient(), CALLS.indexOf("load:9") != -1, TIMERS], [true, true, [9000]]);
console.log(JSON.stringify(R));
'''
    f = os.path.join(TMP, "dj.js"); open(f, "w").write(harness)
    r = subprocess.run([NODE, f], capture_output=True, text=True)
    if r.returncode != 0:
        check("page script runs under node with stubs", False, r.stderr)
    else:
        for n, g, w in json.loads(r.stdout.strip().splitlines()[-1]):
            check(n, g == w, "got %s want %s" % (g, w))
    names_h = r'''
var window = globalThis, httpApi = {"nvramSet": function(){}, "hookGetAsync": function(){}};
var $ = function(f){ return {"length": 0}; };
''' + dj + r'''
const nets = [{"sdn_rl": {"idx": "4", "sdn_name": "Guest"}, "apg_rl": {"ssid": "Visitors"}}, {"sdn_rl": {"idx": "5", "sdn_name": "IoT"}, "apg_rl": {"ssid": ""}}];
const n = reaperSdnDefer.names([[4, "n"], [5, "e"], [9, "o"], ["x", "n"], [4, "q"], "junk"], nets);
console.log(JSON.stringify([n, reaperSdnDefer.kinds(n)]));
'''
    f = os.path.join(TMP, "dn.js"); open(f, "w").write(names_h)
    r = subprocess.run([NODE, f], capture_output=True, text=True)
    want = [[{"idx": "4", "name": "Visitors", "kind": "n"}, {"idx": "5", "name": "IoT", "kind": "e"}, {"idx": "9", "name": "#9", "kind": "o"}],
            "Visitors (<#RSDN_40#>), IoT (<#RSDN_41#>), #9 (<#RSDN_42#>)"]
    check("names: SSID, else the type, else the index; junk items dropped; kinds labelled",
          r.returncode == 0 and json.loads(r.stdout.strip()) == want, r.stdout + r.stderr)
else:
    print("SKIP: node not found - the page-script runs are skipped")

# ---------------------------------------------------------------- 7. tokens
KEYS = ["RSDN_%d" % i for i in range(35, 49)]
_www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(_www) if re.match(r"^[A-Z]{2}\.dict$", f))
bad, lens = [], set()
for f in packs:
    t = read(os.path.join("www", f))
    lens.add(t.count("\n"))
    for k in KEYS:
        mm = re.findall(r"^" + k + r"=(.*)$", t, re.M)
        if len(mm) != 1 or mm[0].strip() == "" or any(x in mm[0] for x in ('"', "'", "`", "\\", "${", "</")):
            bad.append(f + ":" + k)
check("%d tokens once in all %d packs, non-empty, quote-safe; packs in lockstep" % (len(KEYS), len(packs)),
      len(packs) >= 25 and not bad and len(lens) == 1, (bad[:10], lens))
used = dj + dash
check("every token is used (page script or dashboard)", all(("<#%s#>" % k) in used for k in KEYS),
      [k for k in KEYS if ("<#%s#>" % k) not in used])
en = read("www/EN.dict")
m46 = re.search(r"^RSDN_46=(.*)$", en, re.M)
check("the Delete selected confirm names the networks (#NAMES) and says the Wi-Fi restarts once",
      m46 is not None and "#NAMES" in m46.group(1) and "once" in m46.group(1))

shutil.rmtree(TMP, ignore_errors=True)
if fails:
    print("\n%d check(s) failed:" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
