#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest networks: the rc side of the opt-in cross-boundary switches (owner, 2026-11-19, Image 2).

WHY. Guest isolation (rc/reaper_guest.c) closed guest / IoT / VLAN networks to the main LAN. The owner approved three
narrow, OFF-by-default switches: per network "Reach chosen main devices" (apgN_rg_devs) and "Device discovery"
(apgN_rg_mdns), and one Firewall-page switch "Zone policies may open one-way paths from the main network into isolated
guest networks" (reaper_fw_zpol_guest). test_guest_isolation.py checks the rules they produce; test_mdns_reflector.py
the discovery plan; test_review_2026_11_18_batch.py the batched load. This test covers the rest of the rc wiring:

  1. the shared zone-policy reader (shared/reaper_jfile.c REAPER-ZPOL-PURE) is run beside the rules engine's own
     emitter (rc/reaper_fw.c rfw_emit_zpol, compiled from the source) on the same lists: for every interface pair the
     reader says "opens" exactly when the engine's FIRST zone-policy rule for that pair is an ACCEPT; wildcards and
     same-zone policies never open a path; the 64-policy cap is the engine's;
  2. the lists read are the ones the engine RUNS (reaper_fw_list_live: the draft only while a change is armed);
  3. the guest layer re-runs after an engine apply / Keep / revert (rc service handlers, outside the firewall lock)
     and after the deadline revert (the cron watcher script, generated and RUN here under stand-in tools);
  4. a reservation edit (restart_dnsmasq, restart_net_and_phy) re-runs it only when the reservations changed;
  5. the new rc service restart_reaper_guest; prototypes; the three defaults; the comments that said "deny-only".
Exit 0 pass, 1 fail, 77 skipped (no gcc / sh, or no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, random, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "reaper_guest.c")):
    skip("no router tree with rc/reaper_guest.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
SH = shutil.which("sh")
if not CC or not SH:
    skip("no host C compiler or no sh")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

def extract(src, signature):
    i = src.index(signature); j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        if src[k] == "{": depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0: return src[i:k + 1]
        k += 1
    raise ValueError("unbalanced braces after " + signature)

gsrc = read("rc/reaper_guest.c"); fw = read("rc/reaper_fw.c"); jf = read("shared/reaper_jfile.c")
svc = read("rc/services.c"); rch = read("rc/rc.h"); shh = read("shared/shared.h"); dfl = read("shared/defaults.c")
hook = read("rc/reaper_hook.c"); hookh = read("rc/reaper_hook.h")

# ======================================================================= 1. the zone-policy reader vs the engine
mz = re.search(r"/\* REAPER-ZPOL-PURE-BEGIN.*?\*/(.*?)/\* REAPER-ZPOL-PURE-END \*/", jf, re.S)
check("shared/reaper_jfile.c carries the REAPER-ZPOL-PURE block (reaper_zpol_load / reaper_zpol_open)", mz is not None)
mt = re.search(r"typedef struct \{[^}]*\} rfw_cfg_t;", fw)
defs = "\n".join(re.findall(r"^#define (?:RFW_VAL_MAX|RFW_MAX_ZPOL|RFW_MAX_IFACE|RFW_NAME_MAX|RFW_CHAIN_FWD|RFW_CAPLOG_\w+)\b.*$", fw, re.M))
try:
    eng = "\n".join(extract(fw, s) for s in ("static int rfw_field(", "static int rfw_find(", "static int rfw_valid_iface(",
                                              "static int rfw_valid_zpol_action(", "static int rfw_zone_ifaces(",
                                              "static void rfw_emit_zpol("))
except ValueError as e:
    eng = None
check("reaper_fw.c: the engine's zone-policy emitter and its helpers are there to compare with", mt is not None and eng is not None)
check("reaper_fw.c keeps its own static rfw_field (test_review_2026_11_18_batch.py extracts it) - the reader is a copy, not a move",
      "static int rfw_field(const char *rec, int idx, char *out, size_t ol)" in fw)
check("the reader's caps are the engine's (64 policies, 8 interfaces per zone, names / records as long)",
      "#define RFW_MAX_ZPOL        64" in fw and "#define RFW_MAX_IFACE        8" in fw and "#define RFW_NAME_MAX 25" in fw
      and "#define RFW_VAL_MAX  2048" in fw and mz is not None and "#define RZP_MAX\t\t64" in mz.group(1)
      and "#define RZP_IFMAX\t8" in mz.group(1) and "#define RZP_NAMELEN\t27" in mz.group(1) and "#define RZP_REC\t\t2048" in mz.group(1))

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <net/if.h>
#define logmessage(...) do { } while (0)
static size_t t_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t k = l < n - 1 ? l : n - 1; memcpy(d, s, k); d[k] = 0; } return l; }
#define strlcpy t_strlcpy
@@DEFS@@
static unsigned rfw_caplog;
@@CFG@@
@@ENG@@
@@ZPOL@@
int main(int argc, char **argv)
{
	if (!strcmp(argv[1], "e")) {	/* the engine: argv[2] zone, argv[3] zpol -> its FORWARD lines */
		rfw_cfg_t c;
		memset(&c, 0, sizeof(c));
		c.zone = argv[2]; c.zpol = argv[3];
		rfw_emit_zpol(stdout, &c, 0);
		return 0;
	}
	{	/* the reader: argv[2] zone, argv[3] zpol, then pairs a b ... -> one 0/1 per pair */
		struct reaper_zpol *z = reaper_zpol_load(argv[2], argv[3]);
		int i;
		for (i = 4; i + 1 < argc; i += 2)
			printf("%d", reaper_zpol_open(z, argv[i], argv[i + 1]));
		printf("\n");
		free(z);
	}
	return 0;
}
'''
tmp = tempfile.mkdtemp()
try:
    if mz and mt and eng:
        c = os.path.join(tmp, "z.c"); exe = os.path.join(tmp, "z")
        open(c, "w").write(HARNESS.replace("@@DEFS@@", defs).replace("@@CFG@@", mt.group(0)).replace("@@ENG@@", eng)
                           .replace("@@ZPOL@@", mz.group(1)))
        r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-Wno-unused-variable", "-o", exe, c], capture_output=True, text=True)
        check("the reader and the engine's emitter compile together on the host (-Wall -Werror)", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            def engine(zone, zpol):
                out = subprocess.run([exe, "e", zone, zpol], capture_output=True, text=True).stdout
                L = []
                for l in out.splitlines():
                    m_ = re.match(r"RFWR iptables -A REAPER_FWF -i (\S+) -o (\S+) -j (ACCEPT|DROP|REJECT)", l)
                    if m_: L.append(m_.groups())
                return L
            def ifm(pat, name):
                return name.startswith(pat[:-1]) if pat.endswith("+") else pat == name
            def first(L, a, b):
                for i_, o_, act in L:
                    if ifm(i_, a) and ifm(o_, b): return act
                return None
            def reader(zone, zpol, pairs):
                args = [exe, "o", zone, zpol]
                for a, b in pairs: args += [a, b]
                return subprocess.run(args, capture_output=True, text=True).stdout.strip()
            IF = ["br0", "br54", "br55", "br56", "eth0", "wgc1"]
            PAIRS = [(a, b) for a in IF for b in IF if a != b]
            rnd = random.Random(20261119)
            bad = []; opened = closed = 0
            for case in range(160):
                names = ["Z%d" % i for i in range(6)]
                zrec = []
                for nm in names + rnd.sample(names, 2):		# a repeated name: the FIRST record counts
                    ifs = rnd.sample(IF, rnd.randint(0, 4)) + rnd.choice([[], [], ["bad!"], ["a+b"], [""], ["x" * 17]])
                    zrec.append("<%s>%s>c" % (nm, ",".join(ifs)))
                if case % 7 == 0: zrec.append("<%s>br0>c" % ("L" * 26))	# a name too long for the engine
                prec = []
                for _ in range(rnd.randint(1, 12)):
                    s_, d_ = rnd.sample(names + ["NOPE"], 2)		# never the same zone on both sides here
                    prec.append("<%s>%s>%s" % (s_, d_, rnd.choice(["accept", "accept", "drop", "reject", "log", "ACCEPT"])))
                if case % 7 == 0: prec.insert(0, "<%s>Z1>accept" % ("L" * 26))
                zone, zpol = "".join(zrec), "".join(prec)
                L = engine(zone, zpol)
                got = reader(zone, zpol, PAIRS)
                want = "".join("1" if first(L, a, b) == "ACCEPT" else "0" for a, b in PAIRS)
                if got != want:
                    bad.append((zone, zpol, got, want))
                opened += want.count("1"); closed += sum(1 for a, b in PAIRS if first(L, a, b) in ("DROP", "REJECT"))
            check("160 random lists: the reader opens a -> b exactly when the engine's first zone-policy rule for it is an ACCEPT",
                  not bad and opened > 100 and closed > 100, (bad[:1], opened, closed))
            Z = "<LAN>br0>c<IOT>br54>c<ALL>br+>c<HOME>br0,br54>c<TUN>tun+>c"
            check("a wildcard ACCEPT never opens a path, but a wildcard DROP / REJECT first still closes one",
                  reader(Z, "<ALL>IOT>accept", [("br0", "br54")]) == "0"
                  and reader(Z, "<ALL>IOT>drop<LAN>IOT>accept", [("br0", "br54")]) == "0"
                  and reader(Z, "<LAN>IOT>accept<ALL>IOT>drop", [("br0", "br54")]) == "1"
                  and reader(Z, "<ALL>IOT>accept<LAN>IOT>accept", [("br0", "br54")]) == "0")
            check("a policy inside one zone (HOME -> HOME) never opens a path, and decides first if it matches first",
                  reader(Z, "<HOME>HOME>accept", [("br0", "br54")]) == "0" and reader(Z, "<HOME>HOME>accept<LAN>IOT>accept", [("br0", "br54")]) == "0"
                  and reader(Z, "<LAN>IOT>accept<HOME>HOME>accept", [("br0", "br54")]) == "1")
            check("a wildcard or empty name asked for, or a == b: never",
                  reader(Z, "<LAN>IOT>accept", [("br+", "br54"), ("br0", "br+"), ("br0", "br0"), ("", "br54")]) == "0000")
            many = "".join("<X%d>IOT>drop" % i for i in range(64))
            check("the engine's cap: policy 65 and later never count, policy 64 still does",
                  reader(Z, many + "<LAN>IOT>accept", [("br0", "br54")]) == "0"
                  and reader(Z, many[:-len("<X63>IOT>drop")] + "<LAN>IOT>accept", [("br0", "br54")]) == "1"
                  and first(engine(Z, many + "<LAN>IOT>accept"), "br0", "br54") is None)
            check("nothing to read: no policies = nothing opens", reader(Z, "", [("br0", "br54")]) == "0" and reader("", "<LAN>IOT>accept", [("br0", "br54")]) == "0")

    # ======================================================================= 3. the deadline revert (cron watcher)
    gcc_ = extract(fw, "static void rfw_gen_cc(void)")
    check("reaper_fw.c: the deadline watcher re-runs the guest layer after the revert (restart_reaper_guest, through rc)",
          'fputs("service restart_reaper_guest >/dev/null 2>&1\\nexit 0\\n", f);' in gcc_
          and gcc_.index("reaper_cc_gen(RFW_CC, RFW_ARMED, RFW_DEADLINE, RFW_ROLLBACK);") < gcc_.index("restart_reaper_guest"))
    d = os.path.join(tmp, "cc"); os.mkdir(d)
    c2 = os.path.join(tmp, "cc.c"); e2 = os.path.join(tmp, "ccgen")
    open(c2, "w").write('#include <stdio.h>\n#include <stdlib.h>\n#define nvram_get_int(k) 0\n#include "reaper_cc.h"\n'
                        '#define RFW_CC "%s/cc_check.sh"\n#define RFW_ARMED "%s/armed"\n#define RFW_DEADLINE "%s/deadline"\n'
                        '#define RFW_ROLLBACK "%s/rollback.sh"\n%s\nint main(void) { rfw_gen_cc(); return 0; }\n' % (d, d, d, d, gcc_))
    r = subprocess.run([CC, "-Wall", "-o", e2, c2, "-I", os.path.join(SRC, "rc")], capture_output=True, text=True)
    check("the watcher's generator compiles on the host", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        subprocess.run([e2]); sc = os.path.join(d, "cc_check.sh")
        txt = open(sc).read()
        check("the generated watcher ends: revert, then the guest layer, then exit 0", txt.endswith('sh %s/rollback.sh\nservice restart_reaper_guest >/dev/null 2>&1\nexit 0\n' % d), txt[-300:])
        b = os.path.join(tmp, "bin"); os.mkdir(b); out = os.path.join(tmp, "out")
        for nm, body in (("service", 'echo "service $*" >> "$OUT"\n'),):
            p_ = os.path.join(b, nm); open(p_, "w", newline="\n").write("#!/bin/sh\n" + body); os.chmod(p_, 0o755)
        open(os.path.join(d, "rollback.sh"), "w", newline="\n").write('echo rollback >> "$OUT"\n')
        env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""), OUT=out)
        def runcc():
            open(out, "w").close()
            p_ = subprocess.run([SH, sc], capture_output=True, text=True, env=env)
            return open(out).read(), p_.returncode
        os.mkdir(os.path.join(d, "armed")); open(os.path.join(d, "deadline"), "w").write("1")
        o, rc_ = runcc()
        check("deadline passed: the revert runs, then restart_reaper_guest", o == "rollback\nservice restart_reaper_guest\n" and rc_ == 0, o)
        open(os.path.join(d, "deadline"), "w").write("99999999999")
        o, rc_ = runcc()
        check("deadline not reached: nothing runs (no guest re-run every minute)", o == "" and rc_ == 0, o)
        os.rmdir(os.path.join(d, "armed"))
        o, rc_ = runcc()
        check("nothing armed: nothing runs", o == "" and rc_ == 0, o)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ======================================================================= 2. the lists the engine runs
live = extract(jf, "char *reaper_fw_list_live(const char *key)")
check("reaper_fw_list_live: the draft (through reaper_fw_list_get) ONLY while a change is armed",
      live.index("if (d_exists(REAPER_FW_ARMED_DIR))") < live.index("return strdup(reaper_fw_list_get(key));")
      < live.index('REAPER_FW_LASTGOOD_DIR "/.committed"'))
check("reaper_fw_list_live: else the confirmed copy (a confirmed snapshot without the file = empty), else nvram; always a copy",
      'snprintf(p, sizeof(p), REAPER_FW_LASTGOOD_DIR "/%s", key);' in live and 'return strdup(ex && v ? v : "");' in live
      and 'snprintf(nv, sizeof(nv), "reaper_fw_%s", key);' in live and "return strdup(nvram_safe_get(nv));" in live)
m_ = re.search(r'#define RFW_DIR\s+"([^"]+)"', fw)
check("the armed path is the engine's own (RFW_ARMED = RFW_DIR \"/armed\")",
      m_ is not None and '#define RFW_ARMED    RFW_DIR "/armed"' in fw and ('#define REAPER_FW_ARMED_DIR "%s/armed"' % m_.group(1)) in shh)
check("shared.h declares the reader, the zone-policy loader (opaque) and the test",
      "extern char *reaper_fw_list_live(const char *key);" in shh and "struct reaper_zpol;" in shh
      and "extern struct reaper_zpol *reaper_zpol_load(const char *zone, const char *zpol);" in shh
      and "extern int reaper_zpol_open(const struct reaper_zpol *z, const char *a, const char *b);" in shh)

# ======================================================================= 3/4/5. rc wiring
for verb in ("reaper_fw_apply", "reaper_fw_confirm", "reaper_fw_rollback"):
    check("rc service %s: the guest layer follows afterwards, outside the firewall lock (MULTILAN builds)" % verb,
          ("\t\tif(action & RC_SERVICE_START) %s();\n#ifdef RTCONFIG_MULTILAN_CFG\n"
           "\t\tif(action & RC_SERVICE_START) reaper_guest_zpol_follow();" % verb) in svc)
check("rc service reaper_fw (engine on / off): the guest layer follows",
      "\t\tif(action & RC_SERVICE_START) start_reaper_fw();\n#ifdef RTCONFIG_MULTILAN_CFG\n\t\treaper_guest_zpol_follow();" in svc)
zf = extract(gsrc, "void reaper_guest_zpol_follow(void)")
check("reaper_guest_zpol_follow: only with the switch on (with it off an engine change leaves the layer alone), and it takes the lock itself",
      'if (nvram_match("reaper_fw_zpol_guest", "1"))\n\t\treaper_guest_apply(0);' in zf)
ra = extract(gsrc, "void reaper_guest_apply(int have_lock)")
check("reaper_guest_apply(0) takes file_lock(\"firewall\") itself - the engine released it before the follow",
      'if (!have_lock)\n\t\tlk = file_lock("firewall");' in ra)
check("restart_dnsmasq (the DHCP page's reservation save): the chosen devices follow, MULTILAN builds",
      "#ifdef RTCONFIG_MULTILAN_CFG\n\t\t/* reaper 2026-11-19 REAPER-GUEST-RESV:" in svc
      and "\t\tif (action & RC_SERVICE_START)\n\t\t\treaper_guest_resv_follow();\n#endif\n\t}\n#ifdef RTCONFIG_DNSPRIVACY" in svc)
npi = svc.index('else if (strcmp(script, "net_and_phy") == 0) {'); npj = svc.index('else if (!strcmp(script, "subnet"))', npi)
check("restart_net_and_phy (the DHCP page's other save): the chosen devices follow after dnsmasq starts",
      svc[npi:npj].count("reaper_guest_resv_follow();") == 1
      and svc[npi:npj].index("start_dnsmasq(ALL_SDN);") < svc[npi:npj].index("reaper_guest_resv_follow();"))
rf = extract(gsrc, "void reaper_guest_resv_follow(void)")
rch_ = extract(gsrc, "int reaper_guest_resv_changed(void)")
check("reaper_guest_resv_follow: re-applies only when reaper_guest_resv_changed() says so",
      "if (reaper_guest_resv_changed())\n\t\treaper_guest_apply(0);" in rf)
rs = extract(gsrc, "static void rg_resv_sig(char *out, size_t n, int anydev)")
check("the reservation signature: the reservations, their switch, the LAN address and mask, the AiMesh node list; \"-\" when no network names a device",
      all(('nvram_safe_get("%s")' % k) in rs for k in ("dhcp_static_x", "dhcp_staticlist", "lan_ipaddr", "lan_netmask"))
      and "reaper_aimesh_macs(am, REAPER_AIMESH_MAX, NULL)" in rs and 'snprintf(out, n, "-");' in rs)
# review follow-up (LOW): a reserved device that later joins as an AiMesh node must leave the layer - the node list is in
# the signature, and the AiMesh sync asks rc for a rebuild (queued, never run inline: layer scripts holding the
# firewall lock run that applet too)
am_ = read("rc/reaper_aimesh.c")
sync_ = extract(am_, "int reaper_aimesh_sync_main(int argc, char *argv[])")
check("reaper_aimesh_sync: after the set swap, a changed signature queues restart_reaper_guest (notify_rc, never an inline rebuild)",
      "#ifdef RTCONFIG_MULTILAN_CFG\n" in sync_ and "\tif (getpid() != 1 && reaper_guest_resv_changed())\t/* an applet process; never from inside rc (PID 1) */\n\t\tnotify_rc(\"restart_reaper_guest\");" in sync_
      and sync_.index("file_unlock(lock);") < sync_.index("reaper_guest_resv_changed()") and "reaper_guest_apply" not in sync_
      and "notify_rc_and_wait" not in sync_)
check("rc.h declares reaper_guest_resv_changed (MULTILAN block)", "extern int reaper_guest_resv_changed(void);" in rch)
SIGH = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define REAPER_AIMESH_MAX 256
#define RG_DIR "@@DIR@@"
static const char *NV[8][2] = { { "dhcp_static_x", "1" }, { "dhcp_staticlist", "<AA:BB:CC:DD:EE:01>192.168.50.10>>nas" },
	{ "lan_ipaddr", "192.168.50.1" }, { "lan_netmask", "255.255.255.0" } };
static const char *AIM[4]; static int NAIM;
static const char *nvram_safe_get(const char *k) { int i; for (i = 0; i < 4; i++) if (!strcmp(NV[i][0], k)) return NV[i][1]; return ""; }
static int reaper_aimesh_macs(char m[][18], int max, int *d) { int i; for (i = 0; i < NAIM && i < max; i++) snprintf(m[i], 18, "%s", AIM[i]); if (d) *d = 0; return NAIM; }
static int f_read_string(const char *p, char *b, int max) { FILE *f = fopen(p, "r"); int n; if (!f) return -1; n = (int)fread(b, 1, max - 1, f); fclose(f); b[n > 0 ? n : 0] = 0; return n; }
@@SIG@@
@@CHG@@
int main(int argc, char **argv)
{
	char s[16];
	int i;
	for (i = 2; i < argc; i++) AIM[NAIM++] = argv[i];
	if (!strcmp(argv[1], "sig")) { rg_resv_sig(s, sizeof(s), 1); printf("%s\n", s); }
	else if (!strcmp(argv[1], "none")) { rg_resv_sig(s, sizeof(s), 0); printf("%s\n", s); }
	else if (!strcmp(argv[1], "lan")) { NV[2][1] = "192.168.60.1"; rg_resv_sig(s, sizeof(s), 1); printf("%s\n", s); }
	else printf("%d\n", reaper_guest_resv_changed());
	return 0;
}
'''
tmp2 = tempfile.mkdtemp()
try:
    c3 = os.path.join(tmp2, "s.c"); e3 = os.path.join(tmp2, "s")
    open(c3, "w").write(SIGH.replace("@@DIR@@", tmp2).replace("@@SIG@@", rs).replace("@@CHG@@", rch_))
    r = subprocess.run([CC, "-Wall", "-Werror", "-o", e3, c3], capture_output=True, text=True)
    check("the reservation signature and its change test compile on the host", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        def sg(*a):
            return subprocess.run([e3] + list(a), capture_output=True, text=True).stdout.strip()
        s0, s1 = sg("sig"), sg("sig", "aa:bb:cc:00:00:01")
        check("the signature changes when an AiMesh node joins (and when the LAN address changes); the same list in other case does not",
              s0 != s1 and sg("sig", "AA:BB:CC:00:00:01") == s1 and sg("lan") != s0 and sg("none") == "-", (s0, s1, sg("none")))
        sf = os.path.join(tmp2, "resv.sig")
        check("no signature file (the layer never ran): no rebuild", sg("chg") == "0")
        open(sf, "w").write("-")
        check("\"-\" (no network names a device): no rebuild, whatever joins", sg("chg", "aa:bb:cc:00:00:01") == "0")
        open(sf, "w").write(s0)
        check("built with no node: unchanged = no rebuild; a node joins = rebuild asked",
              sg("chg") == "0" and sg("chg", "aa:bb:cc:00:00:01") == "1")
        open(sf, "w").write(s1)
        check("built with that node: a node leaves = rebuild asked; the same list = none",
              sg("chg") == "1" and sg("chg", "AA:BB:CC:00:00:01") == "0")
finally:
    shutil.rmtree(tmp2, ignore_errors=True)
check("AiMesh nodes are known by MAC only (cfg_relist holds MACs, no addresses): a reserved device is refused by its MAC",
      "cfg_relist_x (`<reMac>maclist2g>maclist5g>ts`" in am_ and "rg_mac_eq(aim[k], p)" in gsrc)
sv_i = svc.find('else if (strcmp(script, "reaper_guest") == 0)')
check("rc service restart_reaper_guest (start_ / restart_): the guest layer, then the mDNS plan; MULTILAN builds",
      sv_i > 0 and svc.rfind("#ifdef RTCONFIG_MULTILAN_CFG", 0, sv_i) > svc.rfind("#endif", 0, sv_i)
      and "\t\tif (action & RC_SERVICE_START) {\n\t\t\treaper_guest_apply(0);\n#if defined(RTCONFIG_MDNS)\n\t\t\treaper_mdns_follow();\n#endif\n\t\t}" in svc[sv_i:sv_i + 400])
check("rc.h: the two follow helpers and the mDNS guest list", "extern void reaper_guest_resv_follow(void);" in rch
      and "extern void reaper_guest_zpol_follow(void);" in rch
      and "extern void reaper_mdns_ifaces(char *deny, size_t dn, char *refl, size_t rn, char *why, size_t wn, char *guest, size_t gn);" in rch
      and rch.index("#ifdef RTCONFIG_MULTILAN_CFG", rch.index("reaper_sdn_applied_stamp") - 200) < rch.index("reaper_guest_zpol_follow"))
check("defaults.c: apg_rg_devs (512) and apg_rg_mdns (256) template rows, empty; reaper_fw_zpol_guest off",
      '\t{ "apg_rg_devs", "", CKN_STR512, CKN_TYPE_DEFAULT, CKN_ACC_LEVEL_DEFAULT, CKN_ENC_DEFAULT, 0 },' in dfl
      and '\t{ "apg_rg_mdns", "", CKN_STR256, CKN_TYPE_DEFAULT, CKN_ACC_LEVEL_DEFAULT, CKN_ENC_DEFAULT, 0 },' in dfl
      and '\t{ "reaper_fw_zpol_guest", "0", CKN_STR1, CKN_TYPE_DEFAULT, CKN_ACC_LEVEL_DEFAULT, CKN_ENC_DEFAULT, 0 },' in dfl
      and dfl.index('"apg_ap_isolate"') < dfl.index('"apg_rg_devs"') < dfl.index('"apg_macmode"'))
_rows = dfl[dfl.index('"apg_rg_devs"') - 200:dfl.index('"apg_macmode"')]
check("defaults.c: the two template rows carry no Reaper / date marker (test_backup_coverage.py reads three lines back - the stock rows after them stay stock)",
      not re.search(r"[Rr]eaper|20\d\d-\d\d-\d\d|\bv[23]\.\d", _rows[_rows.index('"apg_rg_devs"') - 5:]))
check("comments: guest isolation no longer says it never ACCEPTs (REAPER_GUA), hook.h names the second ACCEPT layer, hook.sh's order line",
      "This layer is DENY-ONLY" not in gsrc and "The one\n * ACCEPT of this layer is its own chain REAPER_GUA" in gsrc
      and "guest isolation's REAPER_GUA is the one other ACCEPT" in hookh
      and "Warden -> guest isolation -> Gatekeeper -> rules engine -> guest exceptions (FORWARD)" in hook)
check("hook.sh is written once per boot: the reason a firmware with REAPER_GUA always has it is stated (a flash reboots, /tmp is new)",
      "A firmware change always reboots, so /tmp/reaper/hook.sh" in hookh)
for f_, t_ in (("rc/reaper_guest.c", gsrc), ("shared/reaper_jfile.c", jf), ("rc/services.c", svc), ("rc/reaper_hook.c", hook)):
    nl = [l for l in t_.split("\n") if "2026-11-19" in l and any(ord(ch) > 127 for ch in l)]
    check(f_ + ": the 2026-11-19 lines are ASCII", not nl, nl[:2])

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
