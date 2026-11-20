#!/usr/bin/env python3
"""The guests' DNS redirect survives a nat-table restore (found on the owner's router, test image _r1, 2026-11-14).

WHY. A Guest Portal's DNS is redirected to the guest network's own resolver by a nat chain (REAPER_GUN, hooked in
PREROUTING; rc/reaper_guest.c, 2026-11-13). start_nat_rules() replaces the whole nat table with iptables-restore.
start_chilli() and start_CP() call it right AFTER their own firewall restart - whose last step had just installed the
redirect - and wanduck calls it on a WAN change. So on the router the chain was gone the moment the portal started
(post-flash check r9:dns-redirect: "3 portal DNS rule(s) missing"): a guest with a hand-set resolver went around the
guest DNS, its family filter and Wallguard. Nothing put the chain back until some later firewall restart.

WHAT CHANGED. reaper_guest_nat_reassert() runs the nat lines of the last generated guest script again after every
restore in start_nat_rules(). Nat only and idempotent: no firewall lock (the call is also reached from inside
start_firewall, which holds it), nothing regenerated, no connection touched.

WHAT IT DOES. Takes the shell command out of the C source, runs it on the host against a script shaped like the one the
router generated (iptables replaced by a recorder) and checks exactly the nat lines ran, in order; also the teardown
form (no guest network left) and a script without nat lines. Pins the call site and the prototype. Exit 0 pass, 1 fail,
77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router - or no sh)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
GC = os.path.join(SRC, "rc", "reaper_guest.c") if SRC else ""
if not GC or not os.path.isfile(GC):
    skip("no router tree with rc/reaper_guest.c (argv[1] or REAPER_ROUTER_SRC)")
SH = shutil.which("sh")
if not SH:
    skip("no sh on the host")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

g = read("rc/reaper_guest.c")
i = g.find("void reaper_guest_nat_reassert(void)")
fn = g[i:g.find("\n}\n", i)] if i > 0 else ""
check("reaper_guest.c: reaper_guest_nat_reassert is there", bool(fn))
m = re.search(r'eval\("sh", "-c", "((?:[^"\\]|\\.)*)" RG_APPLY "((?:[^"\\]|\\.)*)"\);', fn)
check("the command can be read out of the source", m is not None, fn[-300:])
check("no firewall lock is taken, nothing is regenerated (it is reached from inside start_firewall)",
      "file_lock" not in fn and "reaper_guest_gen" not in fn and "reaper_script_ok(RG_APPLY)" in fn)

def unc(s):   # C string literal -> text
    return s.replace('\\"', '"').replace("\\\\", "\\")

ROUTER = '''#!/bin/sh
RG_FAIL=0
R() { "$@" 2>/dev/null || RG_FAIL=$((RG_FAIL+1)); }
for T in iptables ip6tables; do
  for C in REAPER_GUI REAPER_GUF; do $T -N $C 2>/dev/null; $T -F $C; done
done
# 2026-11-13 (owner): a portal guest's DNS goes to the guest network's own resolver, wherever it was sent
iptables -t nat -N REAPER_GUN 2>/dev/null; iptables -t nat -F REAPER_GUN
iptables -t nat -D PREROUTING -j REAPER_GUN 2>/dev/null
R iptables -t nat -I PREROUTING 1 -j REAPER_GUN
# network 4: tun22 (portal, bridge br55)
R iptables -t nat -A REAPER_GUN -i tun22 -p udp --dport 53 -j REDIRECT --to-ports 53
R iptables -t nat -A REAPER_GUN -i tun22 -p tcp --dport 53 -j REDIRECT --to-ports 53
R iptables -A REAPER_GUI -i tun22 -j DROP
R iptables -A REAPER_GUF -i tun22 -p tcp --dport 853 -j DROP
[ "$RG_FAIL" = 0 ] || logger -t reaper "guest isolation: $RG_FAIL rule(s) refused"
'''
GONE = '''#!/bin/sh
for T in iptables ip6tables; do
  $T -D REAPER_HOOK -j REAPER_GUI 2>/dev/null; $T -D REAPER_HOOK_F -j REAPER_GUF 2>/dev/null
  for C in REAPER_GUI REAPER_GUF; do $T -F $C 2>/dev/null; $T -X $C 2>/dev/null; done
done
iptables -t nat -D PREROUTING -j REAPER_GUN 2>/dev/null; iptables -t nat -F REAPER_GUN 2>/dev/null; iptables -t nat -X REAPER_GUN 2>/dev/null
exit 0
'''
NONAT = "#!/bin/sh\nR() { \"$@\"; }\nR iptables -A REAPER_GUI -i br54 -j DROP\n"

def run(script):
    with tempfile.TemporaryDirectory() as td:
        ap = os.path.join(td, "apply.sh"); open(ap, "w", newline="\n").write(script)
        os.mkdir(os.path.join(td, "bin")); calls = os.path.join(td, "calls")
        for tool in ("iptables", "ip6tables", "logger"):
            p = os.path.join(td, "bin", tool)
            open(p, "w", newline="\n").write('#!/bin/sh\necho "%s $*" >> "%s"\n' % (tool, calls)); os.chmod(p, 0o755)
        cmd = unc(m.group(1)) + ap + unc(m.group(2))
        env = dict(os.environ, PATH=os.path.join(td, "bin") + os.pathsep + os.environ.get("PATH", ""))
        r = subprocess.run([SH, "-c", cmd], capture_output=True, text=True, env=env)
        out = open(calls).read().strip().split("\n") if os.path.exists(calls) else []
        return r.returncode, [l for l in out if l], r.stderr

if m:
    rc, calls, err = run(ROUTER)
    want = ["iptables -t nat -N REAPER_GUN", "iptables -t nat -F REAPER_GUN", "iptables -t nat -D PREROUTING -j REAPER_GUN",
            "iptables -t nat -I PREROUTING 1 -j REAPER_GUN",
            "iptables -t nat -A REAPER_GUN -i tun22 -p udp --dport 53 -j REDIRECT --to-ports 53",
            "iptables -t nat -A REAPER_GUN -i tun22 -p tcp --dport 53 -j REDIRECT --to-ports 53"]
    check("a portal's script: exactly the nat lines run again, in order - chain, hook, both redirects", calls == want, (calls, err))
    check("... and no filter rule, no ip6tables, no log line is touched", not any("REAPER_GUI" in c or "REAPER_GUF" in c or c.startswith(("ip6tables", "logger")) for c in calls))
    rc, calls, err = run(GONE)
    check("no guest network left: only the nat teardown runs (the chain stays gone)",
          calls == ["iptables -t nat -D PREROUTING -j REAPER_GUN", "iptables -t nat -F REAPER_GUN", "iptables -t nat -X REAPER_GUN"], (calls, err))
    rc, calls, err = run(NONAT)
    check("a script without nat lines: nothing runs, no error", calls == [] and rc == 0, (rc, calls, err))

svc = read("rc/services.c")
a = svc.find("\nint start_nat_rules(void)\n")
body = svc[a:svc.find("\nint stop_nat_rules", a)] if a > 0 else svc[a:a + 6000]
check("start_nat_rules: the redirect is put back right after the table is restored",
      'rule_apply_checking("services", __LINE__, NAT_RULES, ret);\n#ifdef RTCONFIG_MULTILAN_CFG\n\treaper_guest_nat_reassert();' in svc
      and svc.count("reaper_guest_nat_reassert();") == 1
      and 0 < svc.find('eval("iptables-restore", NAT_RULES)', a) < svc.find("reaper_guest_nat_reassert();"))
check("rc.h: prototype", "extern void reaper_guest_nat_reassert(void);" in read("rc/rc.h"))

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
