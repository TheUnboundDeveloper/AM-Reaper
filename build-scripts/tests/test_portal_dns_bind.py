#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal: a portal network's resolver starts whether or not the portal is up yet (2026-11-13).

WHY THIS EXISTS. On the owner's router guests signed in and the phone then sat on "Successful!": its own connection
test never passed because a signed-in guest had no DNS. Each network has its own dnsmasq (rc/sdn.c), bound by
ADDRESS (bind-interfaces + listen-address=<router address on that network>). On a Guest Portal network that address
sits on the portal's tunnel (tun22 / tun23, shared/mtlan_utils.c) and exists only while the portal runs. Once the
portal was started a single time, at the end of the request, "restart_sdn <n>" ran first and dnsmasq stopped with
"failed to create listening socket for 192.168.52.1: Cannot assign requested address" - and nothing starts it again.

WHAT IT DOES. Compiles the real listen-header writer (rc/sdn.c REAPER-SDNBIND block) on the host and runs it: a
portal tunnel is bound by interface name (bind-dynamic, with the loopback left to the main resolver), every other
network keeps its address binding. Then pins the one call site. Where a host dnsmasq is installed it also starts
one with the portal header on an interface that does not exist and checks that it stays up, and that the old
header does not.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router).
Without a host C compiler only the pins run."""
import os, re, shutil, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "sdn.c")):
    print("SKIP: no router tree with rc/sdn.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="latin-1").read()

sdn, mtl = read("rc/sdn.c"), read("shared/mtlan_utils.c")

# ---- pins
m = re.search(r"\nstatic int _gen_sdn_dnsmasq_conf\(.*?\n\}\n", sdn, re.S)
body = m.group(0) if m else ""
check("_gen_sdn_dnsmasq_conf() found", bool(body))
check("the per-network resolver config takes its listen header from the helper",
      "\t\treaper_sdn_listen_conf(fp, pmtl->nw_t.ifname, pmtl->nw_t.addr);\n" in body)
check("no address-bound header is written past the helper",
      'fprintf(fp, "bind-interfaces\\n");' not in body and 'fprintf(fp, "listen-address=%s\\n"' not in body)
check("the helper is the only writer of bind-interfaces in rc/sdn.c", sdn.count("bind-interfaces") == 1,
      sdn.count("bind-interfaces"))
check("a portal network still carries the tunnel as its interface (the helper keys on it)",
      'strlcpy(nwlst[cnt].nw_t.ifname, "tun22"' in mtl and 'strlcpy(nwlst[cnt].nw_t.ifname, "tun23"' in mtl)
check("the resolver is still started from its own config file",
      'eval("dnsmasq", "-C", config_path, "--log-async");' in sdn)

# ---- the helper, compiled and run
blk = re.search(r"/\* REAPER-SDNBIND-BEGIN.*?\*/(.*?)/\* REAPER-SDNBIND-END \*/", sdn, re.S)
check("REAPER-SDNBIND block present", bool(blk))
CC = shutil.which("gcc") or shutil.which("cc")
PORTAL = "bind-dynamic\ninterface=%s\nexcept-interface=lo\n"
if blk and not CC:
    print("SKIP (part): no host C compiler - the helper was not run")
elif blk:
    prog = ("#include <stdio.h>\n#include <string.h>\n" + blk.group(1) +
            "\nint main(int argc, char **argv)\n{\n"
            "  if (argc < 2) return 2;\n"
            "  reaper_sdn_listen_conf(stdout, strcmp(argv[1], \"-\") ? argv[1] : NULL, argc > 2 ? argv[2] : NULL);\n"
            "  return 0;\n}\n")
    tmp = tempfile.mkdtemp()
    try:
        c, exe = os.path.join(tmp, "t.c"), os.path.join(tmp, "t")
        open(c, "w", encoding="latin-1").write(prog)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Werror", "-o", exe, c], capture_output=True, text=True)
        check("the helper compiles clean (-Wall -Werror)", r.returncode == 0, r.stderr[-400:])
        if r.returncode == 0:
            def out(*a):
                return subprocess.run([exe] + list(a), capture_output=True, text=True, timeout=30).stdout
            for tun in ("tun22", "tun23"):
                check("portal tunnel %s: bound by interface name, loopback left alone" % tun,
                      out(tun, "192.168.52.1") == PORTAL % tun, out(tun, "192.168.52.1"))
            for ifn, addr in (("br55", "192.168.55.1"), ("br0", "192.168.50.1"), ("tun2", "10.0.0.1"),
                              ("tun220", "10.0.0.1"), ("tun21", "10.6.0.1"), ("wgs1", "10.6.0.1"), ("", "10.0.0.1")):
                check("network on '%s': keeps its address binding" % ifn,
                      out(ifn, addr) == "bind-interfaces\nlisten-address=%s\n" % addr, out(ifn, addr))
            check("no interface name: address binding, no crash", out("-", "10.0.0.1") == "bind-interfaces\nlisten-address=10.0.0.1\n")
            check("no address either: still a whole header", out("br55") == "bind-interfaces\nlisten-address=\n")

            # ---- a real dnsmasq, where the host has one: the portal header survives a missing interface
            DM = shutil.which("dnsmasq") or (os.path.isfile("/usr/sbin/dnsmasq") and "/usr/sbin/dnsmasq") or ""
            if not DM:
                print("SKIP (part): no host dnsmasq - the start-up behaviour was not run")
            else:
                def start(header):
                    conf = os.path.join(tmp, "d.conf")
                    open(conf, "w").write(header + "port=45399\nno-resolv\nno-hosts\npid-file=%s\n"
                                          % os.path.join(tmp, "d.pid"))
                    p = subprocess.Popen([DM, "-k", "-C", conf], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    time.sleep(1.5)
                    alive = p.poll() is None
                    if alive:
                        p.terminate()
                    try:
                        o, _ = p.communicate(timeout=10)
                    except Exception:
                        p.kill(); o = ""
                    return alive, o
                alive, o = start(out("tun22", "192.0.2.77").replace("tun22", "reapernone0"))
                if "ermission" in o or "CAP_" in o:
                    print("SKIP (part): host dnsmasq cannot run here (%s)" % o.strip()[:120])
                else:
                    check("real dnsmasq: the portal header stays up with its interface missing", alive, o[-300:])
                    alive, o = start(out("br55", "192.0.2.77"))
                    check("real dnsmasq: the address-bound header does stop when its address is missing "
                          "(the fault this test guards)", not alive, o[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
