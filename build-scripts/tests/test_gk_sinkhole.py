#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gatekeeper quarantine: a held device's DNS goes to the router's sinkhole, nowhere else.

WHY THIS EXISTS. Security review 2026-10-20 (F-6): in quarantine mode (gk_default=0) the
REAPER_GKI tail let a held device reach the router's resolver (udp/tcp 53), and dnsmasq
forwarded upstream for everyone - a device nobody had approved could look up any name or
tunnel through DNS. The fix is a second, tiny dnsmasq (rc/gatekeeper.c gk_gen_sink): no
upstream, no hosts, every name answered with the router's own address at TTL 0, on port
5300 of every hooked bridge; REAPER_GKN REDIRECTs a held device's port 53 there, so the OS
captive probe still resolves to the router (the sign-in sheet still appears) while nothing
can be learned. It is started by apply.sh from a root-private conf, reaped by the teardown
and restarted by gkd when it dies. r3 metal (2026-10-20): it runs as /tmp/gk/gksink, a symlink
to dnsmasq exec'd by that name, because rc's stop_dnsmasq() reaps by NAME (killall_tk, matching
comm and argv[0]) and took the sinkhole with every full resolver restart - a changed Dreadwatch
list, a DHCP change - leaving held devices without a sign-in sheet until gkd's next heal. A
rule that lands outside the quarantine branch, a
REDIRECT that moves ahead of the known-MAC RETURNs, or a shell slip in the generated text
would either hold every device's DNS or leave the chains unhooked, with a green build.

WHAT IT DOES. Reads rc/gatekeeper.c, gkd/gkd.c, others/reaper_diag and the lean markers and
asserts the conf keys, the rule set and its order, the start/stop/heal wiring, the diag
line and the markers; then rebuilds the F-6 shell fragments from the C literals and runs
them through `sh -n` when a shell is on the host.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
GK = os.path.join(SRC, "rc", "gatekeeper.c")
if not SRC or not os.path.isfile(GK):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="replace").read()

src = read("rc/gatekeeper.c")
gkd = read("gkd/gkd.c")
diag = read("others/reaper_diag")

# ---------------------------------------------------------------- the conf
for want in ('#define GK_SINK_CONF GK_DIR "/sink.conf"', '#define GK_SINK_PID  GK_DIR "/sink.pid"', '#define GK_SINK_PORT "5300"',
             "static void gk_gen_sink(const char *gkifs)", '"pid-file=" GK_SINK_PID "\\n"', '"port=" GK_SINK_PORT "\\n"',
             '"bind-dynamic\\n"', '"except-interface=lo\\n"', '"no-resolv\\n"', '"no-hosts\\n"', '"no-poll\\n"',
             '"cache-size=0\\n"', '"local-ttl=0\\n"', '"address=/#/%s\\n"', '"log-facility=/dev/null\\n"',
             'chmod(GK_SINK_CONF ".tmp", 0600);', 'rename(GK_SINK_CONF ".tmp", GK_SINK_CONF)'):
    check("gatekeeper.c sink conf: %s" % want, want in src)
check("the sinkhole port is not mDNS (5353) and not the resolver (53)", '"5353"' not in src and 'GK_SINK_PORT "53"' not in src)
gen = src[src.index("static void gk_gen_sink("):src.index("#define GK_SINK_KILL")]
check("the conf names the main bridge and every extra hooked bridge, charset-gated, and the answer address is dotted-decimal only",
      'fprintf(f, "interface=%s\\n", lanif);' in gen and 'fprintf(f, "interface=%s\\n", tok);' in gen
      and "isalnum((unsigned char)*q)" in gen and "isdigit((unsigned char)*q)" in gen
      and 'if (lanip[0] && !*q)' in gen and 'if (lanif[0] && !*q)' in gen, "")
apply = src[src.index("static void gk_gen_apply(void)"):]
check("gk_gen_apply regenerates the sink conf before it writes apply.sh (gk_refresh follows the network set)",
      "gk_gen_sink(gkifs);" in apply and apply.index("gk_gen_sink(gkifs);") < apply.index('fopen(GK_APPLY ".tmp", "w")'))

# ---------------------------------------------------------------- the rules, inside the quarantine branch only
q0 = src.index("if (quarantine) {", src.index("static void gk_gen_apply(void)"))
q1 = src.index("/* hooks at position 1", q0)
quar = src[q0:q1]
redir_u = '"  $T -t nat -A REAPER_GKN -p udp --dport 53 -j REDIRECT --to-ports " GK_SINK_PORT "\\n"'
redir_t = '"  $T -t nat -A REAPER_GKN -p tcp --dport 53 -j REDIRECT --to-ports " GK_SINK_PORT "\\n"'
check("the DNS REDIRECT (udp + tcp) is emitted for both families inside the quarantine branch",
      quar.count(redir_u) == 1 and quar.count(redir_t) == 1
      and quar.index('"for T in iptables ip6tables; do\\n"', quar.index("# held devices: DNS to the sinkhole")) < quar.index(redir_u))
check("the REDIRECT is emitted outside the quarantine branch nowhere", src.count("REDIRECT --to-ports \" GK_SINK_PORT") == 2)
check("the REDIRECT follows the per-device RETURNs (a known device is never redirected)",
      src.index("gk_emit_mac(f, mac, st, quarantine);") < q0 and 'REAPER_GKN -m mac --mac-source %s -j RETURN' in src)
check("the REDIRECT does not depend on gk_captive / http_enable (the port-80 redirect keeps its own gate)",
      quar.index(redir_u) < quar.index('"if [ \\"$(_nv gk_captive)\\" != \\"0\\" ] && [ \\"$GKHTTPEN\\" != \\"0\\" ]; then\\n"'))
for T in ("iptables", "ip6tables"):
    ret_u = '"%s -A REAPER_GKI -p udp --dport " GK_SINK_PORT " -j RETURN\\n"' % T
    ret_t = '"%s -A REAPER_GKI -p tcp --dport " GK_SINK_PORT " -j RETURN\\n"' % T
    drop = '"%s -A REAPER_GKI -j DROP\\n"' % T
    check("%s: the sink port RETURNs precede the terminal DROP of REAPER_GKI" % T,
          ret_u in quar and ret_t in quar and quar.index(ret_u) < quar.index(drop) and quar.index(ret_t) < quar.index(drop))
    check("%s: the port 53 RETURNs stay (a sinkhole that is down must not black-hole the captive probe)" % T,
          '"%s -A REAPER_GKI -p udp --dport 53 -j RETURN\\n"' % T in quar and '"%s -A REAPER_GKI -p tcp --dport 53 -j RETURN\\n"' % T in quar)
check("the admin escape hatch ($GKADMIN) is still RETURNed in both families",
      quar.count('--dport $GKADMIN -j RETURN') == 2)

# ---------------------------------------------------------------- start, stop, heal
start = quar[quar.index('"_sl=$(ls -ln " GK_SINK_CONF'):]
check("apply.sh starts the sink only from a root-owned 0600 regular file (the shell twin of reaper_script_ok)",
      '"  -rw-------*) [ \\"$(echo \\"$_sl\\" | awk \'{print $3}\')\\" = 0 ] && { ln -sf " GK_SINK_EXE " " GK_SINK_BIN " && " GK_SINK_BIN " -C " GK_SINK_CONF' in start
      and "{ dnsmasq -C" not in start
      and "logger -t gatekeeper 'DNS sinkhole for held devices failed to start'" in start
      and "logger -t gatekeeper 'DNS sinkhole conf is not a private root file - not started'" in start)
check("the start comes after the sdnfi.sh step, at the end of the quarantine branch",
      quar.index('"[ -x " GK_DIR "/sdnfi.sh ] && sh " GK_DIR "/sdnfi.sh\\n"') < quar.index('"_sl=$(ls -ln " GK_SINK_CONF'))
kill_def = src[src.index("#define GK_SINK_KILL"):src.index("#ifdef RTCONFIG_CFGSYNC", src.index("#define GK_SINK_KILL"))]
# metal 2026-10-20: rc ran apply.sh with its service signals blocked, the instance inherited a blocked
# TERM, the pidfile-and-TERM stop missed it and every later start died on the busy port
check("GK_SINK_KILL finds the sink by its exact command line (not the pidfile), TERMs, waits, then KILLs, and removes the pidfile",
      "grep -l -F \" GK_SINK_CONF \" /proc/[0-9]*/cmdline" in kill_def
      and "[ \\\"$(tr '\\\\000' ' ' < $_f 2>/dev/null)\\\" = \\\"\" GK_SINK_BIN \" -C \" GK_SINK_CONF \" \\\" ]" in kill_def
      and "kill $_sp 2>/dev/null;" in kill_def and "kill -9 $_sp 2>/dev/null;" in kill_def
      and kill_def.index("kill $_sp 2>/dev/null;") < kill_def.index("kill -9 $_sp") and "rm -f \" GK_SINK_PID \"" in kill_def
      and "cat \" GK_SINK_PID \"" not in kill_def)
check("GK_SINK_KILL carries no '%' (it is spliced into an fprintf format)", "%" not in kill_def[kill_def.index("#define"):])
check("both rc launchers of apply.sh use eval() (a clean signal mask for the sinkhole), not system()",
      'eval("sh", GK_APPLY)' in src and 'system("sh " GK_APPLY)' not in src
      and 'eval("sh", "/tmp/gk/apply.sh")' in read("rc/firewall.c") and 'system("sh /tmp/gk/apply.sh")' not in read("rc/firewall.c"))
teardown = src[src.index('"# ---- teardown ----') if '"# ---- teardown ----' in src else src.index("static void gk_gen_apply(void)"):q0]
check("apply.sh's teardown reaps the previous sink before the build", "GK_SINK_KILL" in teardown
      and teardown.index("GK_SINK_KILL") < teardown.index('"# ---- build ----\\n"'))
td0 = src.index("gk_teardown_rules(void)")
check("gk_teardown_rules() reaps the sink and stop_gk() removes the conf",
      src.index("GK_SINK_KILL", td0) < src.index('"for I in $(ls /sys/class/net', td0) and "unlink(GK_SINK_CONF);" in src[td0:]
      and "unlink(GK_SINK_BIN);" in src[td0:])
check("the sinkhole's name: a symlink to the real dnsmasq inside root's /tmp/gk, exec'd by that path (r3 metal: out of the stock name-based restart)",
      '#define GK_SINK_EXE  "/usr/sbin/dnsmasq"' in src and '#define GK_SINK_BIN  GK_DIR "/gksink"' in src
      and 'killall_tk("dnsmasq")' in read("rc/services.c") and "p->exe" not in read("shared/pids.c").split("find_pid_by_name(const char *procName)")[1].split("pids_main")[0])
heal = gkd[gkd.index("static void heal_sink(void)"):gkd.index("static void self_heal(void)")]
alive = gkd[gkd.index("static int sink_cmdline_is("):gkd.index("static void heal_sink(void)")]
check("gkd sink_alive: the pidfile pid only if its cmdline is the sink's, else a /proc scan for that exact cmdline",
      'static const char want[] = GK_DIR "/gksink\\0-C\\0" GK_DIR "/sink.conf";' in alive
      and "n == (ssize_t)sizeof(want) && memcmp(buf, want, sizeof(want)) == 0" in alive
      and 'GK_DIR "/sink.pid"' in alive and "if (pid[0] && sink_cmdline_is(pid)) return 1;" in alive
      and 'opendir("/proc")' in alive and "kill(" not in alive)
check("gkd heal_sink: quarantine only, cmdline liveness, two misses, once a minute, three strikes, re-applies under the lock, logs once",
      'nvram_match("gk_default", "1")' in heal and "if (sink_alive()) {" in heal
      and "if (++missed < 2) return;" in heal and "now - last < 60" in heal and "if (strikes >= 3) {" in heal
      and heal.index("if (strikes >= 3) {") < heal.index("now - last < 60") and "strikes++;" in heal
      and 'run_locked("sh " APPLY_SH, 0)' in heal and "reaper_script_ok(APPLY_SH)" in heal
      and "the DNS sinkhole for held devices is not running - re-applying" in heal and heal.count("logged = 1") == 1
      and "giving up until the next Gatekeeper restart" in heal)
sh = gkd[gkd.index("static void self_heal(void)"):]
check("self_heal calls heal_sink in the armed branch, after heal_lost_rules and before that branch returns",
      "heal_sink();" in sh and sh.index("heal_lost_rules();") < sh.index("heal_sink();")
      and sh[sh.index("heal_sink();"):].split("\n")[1].strip() == "return;")

# ---------------------------------------------------------------- diag, markers
check("reaper_diag 14b reports the sinkhole (pid, port, redirect rule counts) and is v1.3.48",
      'VER="REAPER-DIAG v1.3.53"' in diag and "dns sinkhole      : pid=" in diag and "grep -c 'redir ports 5300'" in diag
      and diag.index("captive redirect  :") < diag.index("dns sinkhole      :"))
mk = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_markers.txt"), encoding="utf-8").read()
check("markers pin the conf path, the redirect and the catch-all answer in the staged rc, and the heal line in the staged gkd",
      all(w in mk for w in ("sbin/rc|/tmp/gk/sink.conf|1", "sbin/rc|--to-ports 5300|1", "sbin/rc|address=/#/|1",
                            "bin/gkd|the DNS sinkhole for held devices is not running|1",
                            "sbin/rc|/tmp/gk/gksink|1", "bin/gkd|/tmp/gk/gksink|1")))

# ---------------------------------------------------------------- the generated shell parses
MACROS = {"GK_DIR": "/tmp/gk", "GK_SINK_CONF": "/tmp/gk/sink.conf", "GK_SINK_PID": "/tmp/gk/sink.pid", "GK_SINK_PORT": "5300",
          "GK_SINK_EXE": "/usr/sbin/dnsmasq", "GK_SINK_BIN": "/tmp/gk/gksink"}
def c_text(text):
    """the shell text of a run of adjacent C string literals and the F-6 macro names"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for m in re.finditer(r'"((?:\\.|[^"\\])*)"|\b(GK_DIR|GK_SINK_CONF|GK_SINK_PID|GK_SINK_PORT|GK_SINK_EXE|GK_SINK_BIN)\b', text):
        if m.group(1) is not None:
            out.append(m.group(1).encode("latin-1").decode("unicode_escape").replace("%%", "%"))
        else:
            out.append(MACROS[m.group(2)])
    return "".join(out)
frag = c_text(kill_def[kill_def.index("\\\n") + 2:]) + "\n" \
     + c_text(quar[quar.index('"# held devices: DNS to the sinkhole'):quar.index('"done\\n");', quar.index('"# held devices: DNS to the sinkhole')) + 9]) \
     + c_text(start[:start.index('"esac\\n"') + 8])
check("the F-6 shell fragments contain every rule and the start", "REDIRECT --to-ports 5300" in frag
      and "ln -sf /usr/sbin/dnsmasq /tmp/gk/gksink && /tmp/gk/gksink -C /tmp/gk/sink.conf" in frag
      and "rm -f /tmp/gk/sink.pid" in frag and "esac" in frag, frag)
SH = shutil.which("sh")
if SH:
    d = tempfile.mkdtemp(prefix="gksink-")
    try:
        fp = os.path.join(d, "f6.sh")
        with open(fp, "w", newline="\n") as f:
            f.write("#!/bin/sh\nLANIP=192.168.50.1\n" + frag)
        p = subprocess.run([SH, "-n", fp], capture_output=True, text=True)
        check("the F-6 shell fragments pass sh -n", p.returncode == 0, p.stderr)
        # run the stop for real: a fake sink with the exact command line and SIGTERM BLOCKED (the metal
        # state), beside a decoy whose command line merely contains the conf path. The stop must take
        # the fake (TERM is held off, so only the KILL escalation can) and leave the decoy alone.
        CC = shutil.which("gcc") or shutil.which("cc")
        if CC and os.path.isdir("/proc/self") and sys.platform.startswith("linux"):
            csrc = os.path.join(d, "fake.c"); exe = os.path.join(d, "fake")
            with open(csrc, "w") as f:
                f.write("#include <signal.h>\n#include <unistd.h>\nint main(void){sigset_t s;sigemptyset(&s);"
                        "sigaddset(&s,SIGTERM);sigprocmask(SIG_BLOCK,&s,0);for(int i=0;i<300;i++)sleep(1);return 0;}\n")
            if subprocess.run([CC, "-o", exe, csrc], capture_output=True).returncode == 0:
                fake = subprocess.Popen(["/tmp/gk/gksink", "-C", "/tmp/gk/sink.conf"], executable=exe)
                decoy = subprocess.Popen(["decoy", "/tmp/gk/sink.conf"], executable=exe)
                # a resolver started the old way must be left alone too: only the gksink command line is the sink
                decoy2 = subprocess.Popen(["dnsmasq", "-C", "/tmp/gk/sink.conf"], executable=exe)
                time.sleep(0.3)
                kp = os.path.join(d, "kill.sh")
                with open(kp, "w", newline="\n") as f:
                    f.write("#!/bin/sh\n" + c_text(kill_def[kill_def.index("\\\n") + 2:]))
                subprocess.run([SH, kp], capture_output=True, text=True, timeout=30)
                time.sleep(0.2)
                fake_rc, decoy_rc, decoy2_rc = fake.poll(), decoy.poll(), decoy2.poll()
                check("the stop kills a sink whose SIGTERM is blocked (KILL escalation), found by its exact command line",
                      fake_rc is not None and fake_rc != 0, fake_rc)
                check("the stop leaves a process alone whose command line only mentions the conf path", decoy_rc is None, decoy_rc)
                check("the stop leaves a plain 'dnsmasq -C <conf>' alone (the sink is the gksink command line only)", decoy2_rc is None, decoy2_rc)
                for pr in (fake, decoy, decoy2):
                    if pr.poll() is None:
                        pr.kill()
                    pr.wait()
            else:
                print("note: the fake-sink binary did not compile - the live stop test is skipped")
        else:
            print("note: no C compiler or no /proc - the live stop test is skipped")
    finally:
        shutil.rmtree(d, ignore_errors=True)
else:
    print("note: no sh on this host - the sh -n pass of the generated fragments is skipped")

if fails:
    print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
print("PASS test_gk_sinkhole: a held device's DNS lands on the router's sinkhole, which apply.sh starts, the teardown reaps and gkd restarts")
