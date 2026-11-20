#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-17, remediation phase 3 (background work): pins for each change as it lands.

WHY THIS EXISTS. The review measured steady background costs. The first: the self-monitor's script read 39 settings
through one guarded `nvram get` each - about 300 process starts and a second of wall time on every tick, 288 ticks
a day. Its settings (not its states) are now read once. A batch read is only safe while (a) a value can never be
run as shell text, (b) states that are read again after a wait stay live, and (c) a failed batch falls back to the
old read - each is pinned here by running the generated lines.

WHAT IT DOES. Cuts the generated shell lines out of rc/rwatch.c, turns the C string literals back into text with
the host compiler, and runs them under busybox ash (or dash) against a stand-in `nvram`.
Exit 0 pass, 1 fail, 77 skipped (no router source tree, no C compiler or no shell)."""
import os, re, shutil, stat, subprocess, sys, tempfile


def skip(msg):
    print("SKIP: " + msg); sys.exit(77)


SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwatch.c")):
    skip("no router source tree with rc/rwatch.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
BB = shutil.which("busybox")
SH = [BB, "ash"] if BB else ([shutil.which("dash")] if shutil.which("dash") else None)
fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))


rw = open(os.path.join(SRC, "rc", "rwatch.c"), encoding="utf-8", errors="surrogateescape").read()

# ---------------------------------------------------------------- the self-monitor reads its settings once
i = rw.find("REAPER-RWATCH-NVC")
j = rw.find('"_nvc() {', i)
k = rw.find("\n", j)
lits = re.findall(r'^\t  ("(?:[^"\\]|\\.)*")\s*$', rw[rw.find("*/", i):k + 1], re.M) if 0 < i < j else []
check("rwatch: the batch read and its `_nvc` reader are in the generated script", len(lits) >= 9, len(lits))
m = re.search(r"_nvs ([a-z0-9_ ]+)\)", " ".join(lits))
names = m.group(1).split() if m else []
code = rw          # not comment-stripped: the script text holds globs such as /tmp/mnt/*/ that a comment regex would eat
check("rwatch: every batched name is read through `_nvc`, none of them through `_nv` any more",
      bool(names) and all(re.search(r"\$\(_nvc %s\)" % n, code) for n in names)
      and not any(re.search(r"_nv %s\b" % n, code) for n in names), names)
STATES = ("wan0_state_t", "wan_state_t", "wlready", "reaper_pbr_active", "wan0_ipaddr", "wan0_gateway", "wan_gateway",
          "wan_primary", "ipv6_rtr_addr", "wan0_ifname")
check("rwatch: states stay live reads (several are read again after a wait) - none is in the batch",
      not (set(names) & set(STATES)) and all(re.search(r"_nv %s\b" % s, code) for s in ("wan0_state_t", "wlready", "reaper_pbr_active")),
      sorted(set(names) & set(STATES)))
check("rwatch: only fixed lower-case identifiers become variable names; a value is assigned through a variable",
      any("''|*[!a-z0-9_]*) continue" in x for x in lits) and any('NVC_$_nvk=' in x and '$_nvv' in x for x in lits))

if CC and SH and lits:
    tmp = tempfile.mkdtemp(prefix="rev1117p3_")
    c = os.path.join(tmp, "g.c")
    open(c, "w", newline="\n").write('#include <stdio.h>\n#include "reaper_nv.h"\nint main(void) { fputs(REAPER_NV_HELPER REAPER_NVS_HELPER\n'
                                     + "\n".join(lits) + "\n, stdout); return 0; }\n")
    r = subprocess.run([CC, "-I", os.path.join(SRC, "rc"), "-o", os.path.join(tmp, "g"), c], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    check("rwatch: the generated lines are valid C string literals", r.returncode == 0, r.stdout)
    if r.returncode == 0:
        head = subprocess.run([os.path.join(tmp, "g")], stdout=subprocess.PIPE, universal_newlines=True).stdout
        binp = os.path.join(tmp, "bin"); os.mkdir(binp)
        evil = 'both"; touch %s/PWNED; echo "$(touch %s/PWNED2)`touch %s/PWNED3`' % (tmp, tmp, tmp)

        def tool(name, body):
            p = os.path.join(binp, name)
            open(p, "w", newline="\n").write("#!/bin/sh\n" + body)
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)

        open(os.path.join(tmp, "dump"), "w", newline="\n").write(
            "rwarden_enable=1\nrwarden_dir=%s\nwandog_target=a b  c\nsw_mode=1\nreaper_store=usb\nBAD-KEY=x\nwan0_state_t=2\n" % evil)
        tool("nvram", 'echo "$1 $2" >> %s/calls\ncase "$1" in show) [ -f %s/fail ] && exit 1; cat %s/dump ;; get) [ "$2" = wan0_state_t ] && echo 2; [ "$2" = sw_mode ] && echo 1 ;; esac\n'
             % (tmp, tmp, tmp))
        tool("logger", "exit 0\n")
        tool("usleep", "exit 0\n")
        body = ('echo "A=[$(_nvc rwarden_enable)]"\necho "B=[$(_nvc rwarden_dir)]"\necho "C=[$(_nvc wandog_target)]"\n'
                'echo "D=[$(_nvc rwatch_review)]"\necho "E=[$(_nvc wan0_state_t)]"\necho "F=[$(_nvc sw_mode)]"\n')
        sp = os.path.join(tmp, "s.sh")
        open(sp, "w", newline="\n").write("#!/bin/sh\n" + head + body)
        env = dict(os.environ, PATH=binp + os.pathsep + os.environ.get("PATH", ""))
        r = subprocess.run(SH + [sp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=env, timeout=60)
        o = r.stdout
        calls = open(os.path.join(tmp, "calls")).read().split("\n") if os.path.isfile(os.path.join(tmp, "calls")) else []
        check("rwatch: batched settings come back exactly (spaces kept; an unset one is empty)",
              "A=[1]" in o and "C=[a b  c]" in o and "D=[]" in o and "F=[1]" in o and ("B=[%s]" % evil) in o, o)
        check("rwatch: a value full of shell syntax is returned as text and nothing in it runs",
              not any(os.path.exists(os.path.join(tmp, n)) for n in ("PWNED", "PWNED2", "PWNED3")))
        check("rwatch: one `nvram show` serves every batched name; a name outside the batch is read live",
              calls.count("show ") == 1 and "get wan0_state_t" in calls and "E=[2]" in o
              and not any(c.startswith("get rwarden") or c.startswith("get sw_mode") for c in calls), calls)
        # the fallback: an empty batch (the read failed) -> every _nvc call is a live _nv read
        sp2 = os.path.join(tmp, "s2.sh")
        open(sp2, "w", newline="\n").write("#!/bin/sh\n" + head.replace('_nvq="$(_nvs ', '_nvq="$(false && _nvs ') + 'echo "G=[$(_nvc sw_mode)]"\n')
        os.remove(os.path.join(tmp, "calls"))
        r = subprocess.run(SH + [sp2], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=env, timeout=60)
        calls = open(os.path.join(tmp, "calls")).read().split("\n") if os.path.isfile(os.path.join(tmp, "calls")) else []
        check("rwatch: when the batch read fails, a setting is read the old way (nothing reads as 'unset')",
              "G=[1]" in r.stdout and "get sw_mode" in calls, (r.stdout, calls))
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- the DNS name mapper taps LAN bridges and lo only
rdp = os.path.join(SRC, "rdnsmapd", "rdnsmapd.c")
if os.path.isfile(rdp):
    rd_ = open(rdp, encoding="utf-8", errors="surrogateescape").read()
    mainp = rd_[rd_.find("int main(void)"):]
    check("name mapper: every packet socket is bound to an interface (index 0 = every interface is refused)",
          "sll.sll_ifindex = idx;" in rd_ and "if (idx <= 0 || bind(sk, (struct sockaddr *)&sll, sizeof(sll)) != 0)" in rd_
          and rd_.count("socket(AF_PACKET") == 1)
    check("name mapper: sockets are opened for br* and lo only, and the set is refreshed every 30 s",
          "(p->if_name[0] == 'b' && p->if_name[1] == 'r') || strcmp(p->if_name, \"lo\") == 0" in rd_
          and "if (now - synced >= 30 || now < synced || rdm_nsk == 0)" in mainp and "r = poll(pf, npk, 30000);" in mainp)
    check("name mapper: a frame still passes the interface test and the loopback test before the parser",
          re.search(r"lanv = rdm_lan_if\(from\.sll_ifindex, now\);\s+if \(!lanv\)\s+return 1;.*?rdm_lo_keep\(.*?rdm_parse\(buf, n, map",
                    rd_, re.S) is not None)
    UNS = shutil.which("unshare"); IP = shutil.which("ip")
    if CC and UNS and IP:
        # not under /tmp: the namespace below mounts an empty /tmp for the daemon's own folder
        home = os.path.expanduser("~")
        tmp = tempfile.mkdtemp(prefix=".rev1117rdm_", dir=home if os.access(home, os.W_OK) and not home.startswith("/tmp") else os.getcwd())
        exe = os.path.join(tmp, "rdnsmapd")
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-O2", "-I", os.path.join(SRC, "shared"), "-o", exe, rdp],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
        check("name mapper: compiles on the host with -Wall -Wextra -Werror", r.returncode == 0, r.stdout)
        if r.returncode == 0:
            ns = os.path.join(tmp, "ns.sh")
            open(ns, "w", newline="\n").write(
                "mount -t tmpfs none /tmp || exit 9\nip link set lo up\n"
                "ip link add br0 type bridge 2>/dev/null || ip link add br0 type dummy || exit 9\n"
                "ip link add eth9 type dummy 2>/dev/null\nip link set br0 up\n"
                + exe + " & D=$!\nsleep 1\n"
                "echo \"START $(awk 'NR>1 {printf \"%s:%s \", $4, $5}' /proc/net/packet)\"\n"
                "echo \"IDX lo=$(ip -o link show lo | cut -d: -f1) br0=$(ip -o link show br0 | cut -d: -f1)\"\n"
                "ip link add br7 type bridge 2>/dev/null || ip link add br7 type dummy\nip link set br7 up\n"
                "echo \"IDX7 $(ip -o link show br7 | cut -d: -f1)\"\nsleep 33\n"
                "echo \"LATER $(awk 'NR>1 {printf \"%s:%s \", $4, $5}' /proc/net/packet)\"\n"
                "kill $D; wait $D 2>/dev/null\n")
            r = subprocess.run([UNS, "-Urnm", "sh", ns], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
            o = dict(l.split(" ", 1) for l in r.stdout.strip().split("\n") if " " in l)
            if r.returncode == 9 or "START" not in o:
                print("note: no usable network namespace here - the run-time check of the name mapper is skipped (%s)" % r.stdout.strip()[:120])
            else:
                idx = dict(x.split("=") for x in o.get("IDX", "").split())
                st = sorted(x.split(":")[1] for x in o["START"].split())
                lt = sorted(x.split(":")[1] for x in o.get("LATER", "").split())
                check("name mapper, run: it taps exactly lo and the bridge - not every interface, not the other port",
                      st == sorted([idx.get("lo"), idx.get("br0")]) and "0" not in st, r.stdout)
                check("name mapper, run: a bridge created later is tapped within 30 s",
                      lt == sorted([idx.get("lo"), idx.get("br0"), o.get("IDX7", "").strip()]), r.stdout)
        shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- the traffic daemon's live file follows the viewer
rtp = os.path.join(SRC, "rtrafd", "rtrafd.c")
if os.path.isfile(rtp):
    rt = open(rtp, encoding="utf-8", errors="surrogateescape").read()
    a = rt.find("static int viewer_active(const char *path, time_t now)")
    b = rt.find("\n}\n", a)
    fn = rt[a:b + 3] if 0 < a < b else ""
    check("traffic: the daemon looks for the viewer stamp once a second and writes the live file every tick only then",
          bool(fn) and "live_viewer = viewer_active(RTRAF_VIEWER, time(NULL));" in rt
          and re.search(r"if \(live_viewer \|\| tick % TPS == 0\)[^\n]*\n\s+write_live\(store\);", rt) is not None
          and rt.count("write_live(store);") == 1)
    check("traffic: the tick itself is unchanged (the other cadences are counted in ticks)",
          "#define TICK_MS\t\t100" in rt and "nap_ms = TICK_MS - (" in rt)
    web = open(os.path.join(SRC, "httpd", "web.c"), encoding="utf-8", errors="surrogateescape").read()
    c = web.find("do_reaper_traffic_cgi(char *url, FILE *stream)")
    cg = web[c:web.find("\n}\n", c)] if c > 0 else ""
    check("traffic: httpd stamps the viewer file when it serves the live window - after its request check, never through a link",
          0 < cg.find("reaper_gate()") < cg.find('if (strcmp(want, "live") == 0) {') < cg.find('open("/tmp/rtraf/.viewer", O_WRONLY | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0600)')
          < cg.find("futimens(vfd, NULL);") < cg.find('snprintf(path, sizeof(path), "/tmp/rtraf/%s.json", want);'))
    if CC and fn:
        tmp = tempfile.mkdtemp(prefix="rev1117rtv_")
        src = os.path.join(tmp, "v.c")
        open(src, "w", newline="\n").write(r"""
#include <stdio.h>
#include <errno.h>
#include <time.h>
#include <utime.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#define RTRAF_VIEWER_SECS 15
""" + fn + r"""
static void stamp(const char *p, time_t t) { struct utimbuf u; int fd = open(p, O_WRONLY | O_CREAT, 0600); if (fd >= 0) close(fd); u.actime = u.modtime = t; utime(p, &u); }
int main(int argc, char **argv)
{
	char p[512], q[512];
	time_t now = time(NULL);
	int bad = 0;
	if (argc < 2) return 2;
	snprintf(p, sizeof(p), "%s/.viewer", argv[1]);
	snprintf(q, sizeof(q), "%s/.viewer/x", argv[1]);
	if (viewer_active(p, now) != 0) { puts("never stamped: read as a viewer"); bad = 1; }
	stamp(p, now);
	if (viewer_active(p, now) != 1) { puts("fresh stamp: no viewer"); bad = 1; }
	if (viewer_active(q, now) != 1) { puts("a stamp that cannot be read (not a folder): not read as a viewer"); bad = 1; }
	stamp(p, now - 15);
	if (viewer_active(p, now) != 1) { puts("15 s old: no viewer"); bad = 1; }
	stamp(p, now - 16);
	if (viewer_active(p, now) != 0) { puts("16 s old: still a viewer"); bad = 1; }
	stamp(p, now + 3600);
	if (viewer_active(p, now) != 1) { puts("a stamp in the future (clock set back): no viewer"); bad = 1; }
	return bad;
}
""")
        exe = os.path.join(tmp, "v")
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, src], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
        ok, out = r.returncode == 0, r.stdout
        if ok:
            r = subprocess.run([exe, tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
            ok, out = r.returncode == 0, r.stdout
        check("traffic: no stamp = no viewer; fresh up to 15 s = viewer; older = none; unreadable or future-dated = viewer",
              ok, out)
        shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- pages do not poll the router from a hidden tab
def page(name):
    p = os.path.join(SRC, "www", name)
    return open(p, encoding="utf-8", errors="surrogateescape").read() if os.path.isfile(p) else ""


dash = page("Main_ReaperDash.asp")
if dash:
    for fn, ms in (("poll", "60000"), ("pollSys", "2500"), ("pollTemp", "5000"), ("clientTick", "ROUTING ? 10000 : 30000"),
                   ("pollPorts", "5000"), ("pollWit", "60000")):
        check("dashboard: %s skips its request while the tab is hidden and runs when it is shown again" % fn,
              ("setInterval(function(){ if(!document.hidden) %s(); }, %s);" % (fn, ms)) in dash
              and ("document.addEventListener('visibilitychange', function(){ if(!document.hidden) %s(); });" % fn) in dash
              and ("setInterval(%s," % fn) not in dash.replace(" ", ""))
    check("dashboard: the visible refresh rates are unchanged (2.5 s, 5 s, 10 / 30 s, 5 s, 60 s)",
          all(x in dash for x in ("pollSys(); }, 2500)", "pollTemp(); }, 5000)", "clientTick(); }, ROUTING ? 10000 : 30000)",
                                  "pollPorts(); }, 5000)", "pollWit(); }, 60000)")))
si = page("Reaper_Sysinfo.asp")
if si:
    check("system information: the three chained polls wait while the tab is hidden (a look each second, no request)",
          all(("setTimeout(function w(){ if(document.hidden) setTimeout(w, 1000); else %s(); }, %s);" % (f, m)) in si
              for f, m in (("pollSysinfo", "3000"), ("pollTemp", "5000"), ("pollCores", "2500")))
          and not re.search(r"setTimeout\(poll(Sysinfo|Temp|Cores),", si))
for name, fn, ms in (("Reaper_Warden.asp", "rwStats", "30000"), ("Reaper_Dreadwatch.asp", "dwStats", "30000"),
                     ("Reaper_WPS.asp", "status", "3000"), ("Reaper_Wallguard.asp", "tick", "3000")):
    pg = page(name)
    if pg:
        check("%s: %s is not requested from a hidden tab" % (name, fn),
              ("setInterval(function(){ if(!document.hidden) %s(); }, %s);" % (fn, ms)) in pg
              and ("setInterval(%s," % fn) not in pg.replace(" ", ""))
for name in ("Main_ReaperDash.asp", "Reaper_Sysinfo.asp", "Reaper_Warden.asp", "Reaper_Dreadwatch.asp", "Reaper_WPS.asp", "Reaper_Wallguard.asp"):
    pg = page(name)
    if pg:
        check("%s stays ASCII" % name, not any(ord(c) > 126 for c in pg))
syp = os.path.join(SRC, "httpd", "sysinfo.c")
if os.path.isfile(syp):
    sy = re.sub(r"/\*.*?\*/", " ", open(syp, encoding="utf-8", errors="surrogateescape").read(), flags=re.S)   # code only
    check("httpd: the active-connection count reads the kernel's table where it is - no `cp`, no file in /tmp",
          'fp = fopen("/proc/net/nf_conntrack", "r");' in sy and "/tmp/conntrack.tmp" not in sy
          and 'eval("cp", "/proc/net/nf_conntrack"' not in sy)

# ---------------------------------------------------------------- Firewall page: the Auto refresh switches live on the router
fwp = page("Reaper_Firewall.asp")
if fwp:
    webc = open(os.path.join(SRC, "httpd", "web.c"), encoding="utf-8", errors="surrogateescape").read()
    dfl = open(os.path.join(SRC, "shared", "defaults.c"), encoding="utf-8", errors="surrogateescape").read()
    check("firewall page: the router's two values are in the page and are read before the browser's copy",
          'var RFW_AUTO_NV={reaper_fw_st_auto:<% nvram_get_js("reaper_fw_st_auto"); %>,reaper_fw_wt_auto:<% nvram_get_js("reaper_fw_wt_auto"); %>};' in fwp
          and "function autoGet(k){var v=RFW_AUTO_NV[k];if(v==='1'||v==='0')return v==='1';try{return localStorage.getItem(k)==='1';}catch(e){return false;}}" in fwp)
    check("firewall page: a change is sent to the router through the page's own request (st_auto / wt_auto)",
          "fwcgi('action=opts&'+(k==='reaper_fw_st_auto'?'st_auto':'wt_auto')+'='+(on?'1':'0'));" in fwp
          and "autoSet('reaper_fw_st_auto',this.classList.contains('on'))" in fwp and "autoSet('reaper_fw_wt_auto',this.classList.contains('on'))" in fwp)
    a = webc.find('if (strcmp(action, "opts") == 0) {')
    op = webc[a:webc.find('if (strcmp(action, "dryrun") == 0) {', a)] if a > 0 else ""
    check("httpd: action=opts stores each switch only as 0 or 1, and commits only when one changed",
          '{ "st_auto", "reaper_fw_st_auto" }, { "wt_auto", "reaper_fw_wt_auto" }' in op
          and '(!strcmp(av, "0") || !strcmp(av, "1")) && strcmp(nvram_safe_get(ak[ai][1]), av) != 0' in op
          and re.search(r"if \(adirty\)\s+httpd_nvram_commit\(\);", op) is not None)
    check("httpd: both settings are in the settings backup; both default to off",
          '{ "fw",     "reaper_fw_st_auto", 2  }, { "fw",     "reaper_fw_wt_auto", 2 },' in webc
          and '{ "reaper_fw_st_auto", "0", CKN_STR1,' in dfl and '{ "reaper_fw_wt_auto", "0", CKN_STR1,' in dfl)

print()
if fails:
    print("%d check(s) FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
