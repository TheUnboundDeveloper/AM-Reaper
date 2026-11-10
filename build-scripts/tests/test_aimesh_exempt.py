#!/usr/bin/env python3
"""One AiMesh node list for every Reaper enforcement surface (2026-11-01).

WHY. AiMesh nodes are infrastructure, not clients. Gatekeeper exempted them from v2.7.3, but it was the
only surface that knew AiMesh existed: the rules engine (Service Intercept rewrites a service for every
LAN source, and a node is a LAN source) and Policy Routing carried no exemption, so one broad operator
rule could cut a node off. The registry parser now lives once, in rc/reaper_aimesh.c, and feeds a shared
hash:mac set that each surface matches before its own rules.

WHAT IT DOES. Compiles the parser on the build host and checks it on fixed registries (the live format,
duplicates across both lists and in mixed case, malformed and hostile tokens, a cut-off tail, no lists,
more than the cap). Then pins every consumer: Gatekeeper uses the shared parser (no copy of its own) and
refreshes the set, the rules engine refreshes and RETURNs in its input / forward / nat chains (not
OUTPUT), Policy Routing RETURNs ahead of its marks, rwatch refreshes every tick, and the applet is
registered AND has its /sbin link (`rc <applet>` does not dispatch on this tree).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "rc")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

am = rd("rc/reaper_aimesh.c") if os.path.exists(os.path.join(SRC, "rc/reaper_aimesh.c")) else ""
gk, fw, pbr, rw = rd("rc/gatekeeper.c"), rd("rc/reaper_fw.c"), rd("rc/reaper_pbr.c"), rd("rc/rwatch.c")
rch, rcc, mk = rd("rc/rc.h"), rd("rc/rc.c"), rd("rc/Makefile")
SET = '-m set --match-set " REAPER_AIMESH_SET " src -j RETURN'
SYNC = '[ -x /sbin/reaper_aimesh_sync ] && /sbin/reaper_aimesh_sync >/dev/null 2>&1'

# 2026-11-08 (owner: next release, decided 2026-11-01): the cap is 256 MACs (was 64, about 16 tri-band nodes)
m = re.search(r"^#define REAPER_AIMESH_MAX (\d+)", rch, re.M)
CAP = int(m.group(1)) if m else 0
check("REAPER_AIMESH_MAX is 256 (owner 2026-11-01: raise 64 to 256)", CAP == 256, CAP)
check("rc/reaper_aimesh.c holds the parser and the sync applet",
      "int reaper_aimesh_macs(char macs[][18], int max, int *dropped)" in am and "int reaper_aimesh_sync_main(" in am)

# --- the parser, compiled on the host
def func(src, sig):
    a = src.index(sig); return src[a:src.index("\n}\n", a) + 3]
parser_ok = False
if am and shutil.which("gcc"):
    c = "\n".join([
        "#include <stdio.h>", "#include <stdlib.h>", "#include <string.h>", "#include <strings.h>", "#include <ctype.h>",
        "static const char *L0, *L1;",
        "char *get_cfg_relist(int x){ const char *s = x ? L1 : L0; return s ? strdup(s) : NULL; }",
        "size_t strlcpy(char *d, const char *s, size_t n){ size_t l = strlen(s); if (n) { size_t k = l < n - 1 ? l : n - 1; memcpy(d, s, k); d[k] = 0; } return l; }",
        func(am, "static int aimesh_valid_mac(const char *m)"),
        func(am, "int reaper_aimesh_macs(char macs[][18], int max, int *dropped)"),
        "int main(int c, char **v){ char m[%d][18]; int d = 0, i, n; L0 = v[1][0] == 1 ? NULL : v[1]; L1 = v[2][0] == 1 ? NULL : v[2];" % max(CAP, 1),
        "  n = reaper_aimesh_macs(m, %d, &d); printf(\"%%d %%d\\n\", n, d); for (i = 0; i < n; i++) printf(\"%%s\\n\", m[i]); return 0; }" % max(CAP, 1)])
    d = tempfile.mkdtemp()
    open(d + "/t.c", "w").write(c)
    r = subprocess.run(["gcc", "-Wall", "-o", d + "/t", d + "/t.c"], capture_output=True, text=True)
    parser_ok = r.returncode == 0
    check("the parser compiles on the build host", parser_ok, r.stderr)
    def run(a, b):
        o = subprocess.run([d + "/t", a if a is not None else "\x01", b if b is not None else "\x01"], capture_output=True, text=True).stdout.split()
        return int(o[0]), int(o[1]), o[2:]
    if parser_ok:
        n, dr, m = run("<00:00:5E:00:53:10>00:00:5E:00:53:11>00:00:5E:00:53:18>1792199028", "")
        check("the live registry format: node LAN MAC + both STA MACs, in order",
              (n, dr, m) == (3, 0, ["00:00:5E:00:53:10", "00:00:5E:00:53:11", "00:00:5E:00:53:18"]), m)
        n, dr, m = run("<AA:BB:CC:00:00:01>AA:BB:CC:00:00:02>aa:bb:cc:00:00:03>17<AA:BB:CC:00:00:04>>>18",
                       "<AA:BB:CC:00:00:01>aa:bb:cc:00:00:02>AA:BB:CC:00:00:09>>")
        check("both lists read, duplicates dropped case-insensitively (cfg_relist_x = the 6 GHz MACs)",
              n == 5 and dr == 0 and m[-1] == "AA:BB:CC:00:00:09", m)
        n, dr, m = run("<ZZ:BB:CC:00:00:01>AA:BB:CC:00:00:0G>AA-BB-CC-00-00-05>AA:BB:CC:00:00:06;rm -rf />1", "")
        check("malformed tokens skipped; a hostile tail never reaches the script", (n, m) == (1, ["AA:BB:CC:00:00:06"]), m)
        check("a cut-off tail and missing lists are safe",
              run("<AA:BB:CC:00:00:07>AA:BB:CC:00", "")[:2] == (1, 0) and run(None, None)[:2] == (0, 0))
        big = "".join("<02:00:00:00:%02X:01>02:00:00:00:%02X:02>1" % (i, i) for i in range(CAP // 2 + 3))
        n, dr, m = run(big, "")
        check("more than the cap: %d kept, the overflow counted for the log" % CAP, (n, dr) == (CAP, 6), (n, dr))
else:
    check("gcc available to compile the parser", bool(shutil.which("gcc")))

# --- consumers
check("Gatekeeper uses the shared parser (no registry parser of its own) and refreshes the set",
      "nseen = reaper_aimesh_macs(seen, REAPER_AIMESH_MAX, &dropped);" in gk and "get_cfg_relist" not in gk
      and SYNC in gk and "ebtables -A REAPER_GK -s %s -j RETURN" in gk)
check("Gatekeeper keeps the owner's cap and logs the overflow",
      "cfg_relist exemption table full at %d - %d AiMesh MAC(s) NOT exempted" in gk)
check("rules engine: refreshes the set at run time and creates it even without the applet",
      SYNC in fw and 'ipset create " REAPER_AIMESH_SET " hash:mac -exist' in fw)
check("rules engine: input and forward chains RETURN a node first, not OUTPUT (no source MAC there)",
      "if (d != RFW_D_OUT)" in fw and 'fprintf(f, "RFWR %s -A %s ' + SET + '\\n", ipt, ch);' in fw
      and fw.index("rfw_emit_head(f, v6, d);") < fw.index('"RFWR %s -A %s ' + SET) < fw.index("rfw_emit_rules(f, c, v6, d);"))
check("Service Intercept: a node leaves the nat chain first (v4 and v6)",
      '"RFWR iptables -t nat -A " RFW_CHAIN_NAT " ' + SET in fw and '"RFWR ip6tables -t nat -A " RFW_CHAIN_NAT " ' + SET in fw
      and fw.index('"RFWR iptables -t nat -A " RFW_CHAIN_NAT " ' + SET) < fw.index("for (d = RFW_D_IN; d <= RFW_D_OUT; d++) {"))
check("Policy Routing: a node RETURNs right after replies, before any mark is restored or set",
      SYNC in pbr and '"  $T -t mangle -A $C -m conntrack --ctdir REPLY -j RETURN\\n"\n\t  "  $T -t mangle -A $C ' + SET in pbr)
check("rwatch refreshes the set every tick (gkd only runs with Gatekeeper on)",
      rw.index(SYNC) > rw.index('"STATE=" RWATCH_STATE "\\n"') if SYNC in rw else False)
check("the applet is declared, registered and has its /sbin link; the set name is one constant",
      "extern int reaper_aimesh_sync_main(int argc, char *argv[]);" in rch and '#define REAPER_AIMESH_SET "reaper_aimesh"' in rch
      and '{ "reaper_aimesh_sync",	reaper_aimesh_sync_main		},' in rcc
      and "ln -sf rc reaper_aimesh_sync" in mk and "OBJS += reaper_aimesh.o" in mk)
check("the set is refreshed by swap under a lock (never seen half-filled)",
      'file_lock("reaper_aimesh")' in am and '"swap", AIMESH_STAGE, REAPER_AIMESH_SET' in am)

if fails:
    print("\n%d failure(s)" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\n0 failure(s)")
