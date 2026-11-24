#!/usr/bin/env python3
"""reaper_diag v1.3.62: the features of v3.4.9 - v3.8.3 in the report (owner 2026-11-20).

WHY. A report from v1.3.61 said almost nothing about Wallguard, Encrypted DNS, guest isolation and its v3.8.3
opt-ins, the Guest Portal, the mDNS reflector, the AiMesh exemption set, the conntrack helpers, the saved DHCP
leases or the mount hardening, so a field question about any of them needed a second round of commands.

WHAT IT DOES. Checks the version on the script and the page, then lifts each new block out of others/reaper_diag by
its marker (3c, 4d, 11 saved leases, 14c AiMesh set, 14h Bastion), points every path it reads at a scratch folder,
stubs nvram / iptables / ip6tables / ipset / pidof / netstat, and runs it under sh and busybox ash (when present)
over fixtures that make every finding fire. It also checks what must never be printed: list addresses, API keys,
device addresses, the DNS name in the option 162 file and the chosen devices' MACs.
"""
import os, re, shutil, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "others", "reaper_diag") if SRC else ""
if not P or not os.path.isfile(P):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
d = open(P, encoding="utf-8", errors="surrogateescape").read()
asp = open(os.path.join(SRC, "www", "Reaper_Diag.asp"), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))

check("diag: v1.3.62 in the script and on the page", 'VER="REAPER-DIAG v1.3.62"' in d and "REAPER-DIAG v1.3.62</span>" in asp)
for m in ("REAPER-DIAG-V1362", "REAPER-DIAG-3C-BEGIN", "REAPER-DIAG-3C-END", "REAPER-DIAG-4D-BEGIN", "REAPER-DIAG-4D-END",
          "REAPER-DIAG-6PD", "REAPER-DIAG-11-SAVED", "REAPER-DIAG-12C-SNMP", "REAPER-DIAG-14C-AIMESH",
          "REAPER-DIAG-14H-BEGIN", "REAPER-DIAG-14H-END"):
    check("marker %s exactly once" % m, d.count(m) == 1, d.count(m))
for h in ('sec "3c. HARDENING', 'sec "4d. GUEST NETWORKS', 'sec "14h. BASTION'):
    check("section header %s" % h, d.count(h) == 1)
order = [d.find(x) for x in ('sec "3b. NVRAM HYGIENE', 'sec "3c. HARDENING', 'sec "4. LAN / BRIDGE', 'sec "4c. DNS DIRECTOR',
                            'sec "4d. GUEST NETWORKS', 'sec "5. WAN', 'sec "14g. FIREWALL WITNESSES', 'sec "14h. BASTION',
                            'sec "15. DATAPLANE')]
check("sections stay in order", all(a < b for a, b in zip(order, order[1:])) and min(order) > 0, order)
check("the certificate names stay on the literal list (they print in 14h)", "san_rednsd_names /tmp/rednsd/run/status.json" in d)
check("14c names the guest layer in the front-chain order", "Warden -> guest isolation (REAPER_GUI/GUF, v3.7.7) -> Gatekeeper" in d)


def block(begin, end):
    i, j = d.find(begin), d.find(end)
    assert 0 <= i < j, (begin, end)
    return d[i:j]


B3C = block("# REAPER-DIAG-3C-BEGIN", "# REAPER-DIAG-3C-END")
B4D = block("# REAPER-DIAG-4D-BEGIN", "# REAPER-DIAG-4D-END")
B14H = block("# REAPER-DIAG-14H-BEGIN", "# REAPER-DIAG-14H-END")
B11 = block("# REAPER-DIAG-11-SAVED", 'sec "11b. CONNTRACK')
B14C = block("# REAPER-DIAG-14C-AIMESH", 'echo "  -- rules engine (reaper_fw) --"')
check("no list file, key file or option 162 name is printed whole",
      "cat $_wgj/keys" not in B14H and "cat $_wgj/lists" not in B14H and "cat $_wgd/feeds" not in B14H
      and 'echo "$_dnr"' not in B14H.replace('echo "$_dnr" | awk', ""))

NOW = int(time.time())
NV = {
    "sdn_rl": "<0>MAINFH>1>0>0>0>0>0>0>0>0>0>0>0>0>0"
              "<1>Guest>1>0>1>1>0>0>0>0>0>0>0>0>0>0"
              "<2>Portal>1>0>2>2>0>0>0>0>0>1>0>0>1>0"
              "<3>My Wifi>1>0>3>3>5>0>0>0>0>0>0>0>0>0"
              "<4>IoT>0>0>4>4>0>0>0>0>0>0>0>0>0>0",
    "subnet_rl": "<1>br52<2>br53<3>br54<4>br55",
    "sdn_access_rl": "<0>3",
    "apg1_rg_devs": "<00:00:5e:00:53:01><00:00:5e:00:53:02>",
    "apg1_rg_mdns": "print,cast,_foo._tcp",
    "apg1_ap_isolate": "1", "apg1_ap_isolate_lan": "1",
    "reaper_fw_zpol_guest": "1", "reaper_fw_enable": "0",
    "rwarden_enable": "1", "rwarden_dns": "1", "wallguard_enable": "1", "wallguard_mode": "nx",
    "reaper_dot_srv": "1", "reaper_doh_srv": "1", "reaper_dot_block": "1", "reaper_doh_block": "0",
    "reaper_ledns_enable": "1", "reaper_ledns_provider": "cloudflare", "reaper_ledns_domain": "router.example.com",
    "reaper_ledns_token": "SuperSecretTokenValue", "reaper_ledns_state": "fail", "reaper_ledns_when": str(NOW - 3600),
    "reaper_ledns_err": "provider refused the record", "le_enable": "0",
    "nf_ftp": "0", "fw_pt_pptp": "1",
    "cfg_relist": "<00:00:5E:00:53:0A>00:00:5E:00:53:0B>00:00:5E:00:53:0C",
    "gk_enable": "1", "ipv6_prefix_length": "60",
}
NVS_TEXT = "".join("%s=%s\n" % kv for kv in NV.items()) + (
    "reaper_usb3_dcm=1\nreaper_usb3_credits=\nwl0_ap_isolate=1\napm1_ap_isolate=0\n"
    "custom_clientlist=<Phone>00:00:5e:00:53:21>0>0>>><Laptop>00:00:5e:00:53:22>0>0>>>\n"
    "dhcp_staticlist=<00:00:5e:00:53:21>192.0.2.21>>phone\n")

STUBS = r'''
sec() { echo "#### $1 ####"; }
finding() { echo "FINDING [$1] $2"; }
have() { return 1; }
nvram() { [ "$1" = get ] || return 0; sed -n "s/^$2=//p" "$NVS" | head -1; }
pidof() { case "$1" in dnsmasq) echo "101 102";; rednsd) echo 201;; chilli) echo "";; stubby) echo 301;; avahi-daemon) echo 401;; snmpd) echo "";; *) echo "";; esac; }
netstat() { :; }
ipset() { case "$*" in "list -t redns_doh") printf 'Name: redns_doh\nNumber of entries: 12\n';; "list -t redns_doh6") printf 'Name: redns_doh6\nNumber of entries: 3\n';; *) return 1;; esac; }
iptables() {
  case "$*" in
    "-S REAPER_GUI") printf -- '-N REAPER_GUI\n-A REAPER_GUI -i br52 -p udp --dport 67 -j RETURN\n-A REAPER_GUI -i br52 -j DROP\n-A REAPER_GUI -i br54 -j DROP\n';;
    "-S REAPER_GUA") printf -- '-N REAPER_GUA\n';;
    "-nL REAPER_GUI") printf 'Chain REAPER_GUI\ntarget prot opt source destination\nRETURN all\nDROP all\nDROP all\n';;
    "-nL REAPER_GUF") printf 'Chain REAPER_GUF\ntarget prot opt source destination\n';;
    "-nL REAPER_GUA") printf 'Chain REAPER_GUA\ntarget prot opt source destination\n';;
    "-nL REAPER_HOOK") printf 'Chain REAPER_HOOK\ntarget\nREAPER_WARDEN\nREAPER_GUI\n';;
    "-nL REAPER_HOOK_F") printf 'Chain REAPER_HOOK_F\ntarget\nREAPER_WARDEN\nREAPER_GUF\nREAPER_GUA\n';;
    "-t nat -nL REAPER_GUN") printf 'Chain REAPER_GUN\ntarget\nDNAT udp\n';;
    "-t nat -S PREROUTING") printf -- '-P PREROUTING ACCEPT\n-A PREROUTING -j VSERVER\n';;
    "-t raw -S REAPER_CTH") printf -- '-N REAPER_CTH\n-A REAPER_CTH -d 192.0.2.1 -p tcp --dport 21 -j CT --helper ftp\n';;
    "-t raw -S REAPER_CTHO") printf -- '-N REAPER_CTHO\n';;
    *) return 1;;
  esac
}
ip6tables() { case "$*" in "-nL REAPER_GUI") printf 'Chain\nt\nDROP\n';; *) return 1;; esac; }
'''


def make_root(w):
    T, J = os.path.join(w, "tmp"), os.path.join(w, "jffs")
    def put(rel, text, base=None):
        p = os.path.join(base or w, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(text)
    put("nvs", NVS_TEXT)
    put("mounts", "tmpfs /tmp tmpfs rw,nosuid,nodev,relatime 0 0\n/dev/mtdblock9 /jffs jffs2 rw,relatime 0 0\n")
    put("helper", "1\n")
    put("uptime", "160.42 300.00\n")
    put("syslog.log", "Nov 20 01:00:00 syslogd: 120 lines like `kernel: wl1: foo` were suppressed\n"
                      "Nov 20 01:00:09 syslogd: 15 lines like `dnsmasq-dhcp: bar` were suppressed\n"
                      "Nov 20 01:01:00 watchdog: a Guest Portal network is on and its portal is not running - starting it (1 of 3 this boot)\n")
    put("reaper/leases.saved", "100\n", T)
    put("reaper/v6split_ula.60.3", "", T)
    put("reaper/leases/dnsmasq.leases", "x\n", J); put("reaper/leases/dnsmasq-52.leases", "x\n", J)
    put("misc/dnsmasq-52.leases", "duid 00:01:00:01:00:00:5e:00:53:99\n100 00:00:5e:00:53:31 192.0.2.31 a *\n100 00:00:5e:00:53:32 192.0.2.32 b *\n", T)
    put("misc/reaper_hostnames", "00:00:5e:00:53:21\tphone\n00:00:5e:00:53:22\tlaptop\n00:00:5e:00:53:23\ttv\n", T)
    # guest isolation runtime
    put("rguest/apply.sh", "iptables -t nat -A REAPER_GUN -i br53 -p udp --dport 53 -j DNAT --to 192.0.2.1\n", T)
    put("rguest/devskip", "00:00:5e:00:53:02 (no reservation)\n", T)
    for port, iso in (("eth1", "1"), ("eth2", "0"), ("wl0", "1")):
        os.makedirs(os.path.join(w, "sys", "br0", "brif", port), exist_ok=True)
        put("sys/%s/brport/isolated" % port, iso + "\n")
    os.makedirs(os.path.join(w, "sys", "br52", "brif"), exist_ok=True)
    os.makedirs(os.path.join(w, "sys", "tun22"), exist_ok=True)
    put("avahi/avahi-daemon.conf", "[reflector]\nenable-reflector=yes\nreflect-interfaces=br0,br54\ndeny-interfaces=br53\n"
                                   "reflect-guest=br52:_ipp._tcp:_googlecast._tcp\n", T)
    # wallguard
    put("wallguard/db", "x" * 1000, T)
    put("wallguard/lists/hagezi_pro", "a.example\n", T)
    put("wallguard/state", "hagezi_pro ok %d %d\noisd_big failed 0 %d warden:US 192.0.2.80\n" % (NOW - 7200, NOW - 7200, NOW), T)
    put("wallguard/build.st", '{"t":%d,"skip":"miss","want":2,"used":1,"none":"oisd_big"}\n' % NOW, T)
    put("wallguard/pause", "all 9999999999\nmac 00:00:5e:00:53:41 9999999999\n", T)
    put("wallguard/live.on", "", T)
    put("wallguard/pending", "", T); put("wallguard/tries", "2\n", T)
    put("wallguard/lists", "hagezi_pro\ncustom 1 https://lists.example.com/mine.txt\n", J)
    put("wallguard/keys", "1 KeyValueNeverPrinted\n", J)
    put("wallguard/profiles", "1 3 kids\n", J); put("wallguard/assign", "mac 00:00:5e:00:53:21 1\n", J)
    put("wallguard/counters", "SINCE 1700000000\nTOTAL 42\nDROPPED 1\nCNAME 3\n", J)
    put("maps.101", "7f00 r--s /WALLGUARD_DB_PATH\n")
    put("maps.102", "7f00 r--s /lib/libc.so\n")
    put("etc/dnsmasq.conf", "x\n"); put("etc/dnsmasq-52.conf", "x\n")
    # encrypted DNS
    put("rednsd/run/status.json",
        '{"state":"running","pid":201,"up":60,"listen":[{"a":"192.0.2.1","p":853,"wan":0,"ok":1,"proto":"dot"},'
        '{"a":"192.0.2.1","p":443,"wan":0,"ok":0,"proto":"doh"}],"conns":2,"conns_total":9,"queries":100,'
        '"refused_peer":1,"refused_policy":0,"refused_busy":0,"hs_fail":3,"servfail":0,"doh_queries":40,"h2_errors":0,'
        '"cert":{"trusted":1,"names":["router.example.com"]},"clients":[{"a":"192.0.2.20","proto":"dot","q":5,"last":1},'
        '{"a":"192.0.2.21","proto":"doh","q":7,"last":1}]}\n', T)
    put("rednsd/note.json", '{"state":"ok"}\n', T)
    put("rednsd/dnr", "router.example.com 1 1\n", T)
    return T, J


def repoint(body, w, T, J):
    pairs = [("/tmp/wallguard", T + "/wallguard"), ("/jffs/wallguard", J + "/wallguard"), ("/tmp/rednsd", T + "/rednsd"),
             ("/tmp/avahi", T + "/avahi"), ("/tmp/rguest", T + "/rguest"), ("/jffs/reaper/leases", J + "/reaper/leases"),
             ("/tmp/reaper/", T + "/reaper/"), ("/var/lib/misc", T + "/misc"), ("/sys/class/net", w + "/sys"),
             ("/proc/mounts", w + "/mounts"), ("/proc/sys/net/netfilter/nf_conntrack_helper", w + "/helper"),
             ("/tmp/syslog.log", w + "/syslog.log"), ("/proc/uptime", w + "/uptime"), ("/etc/dnsmasq", w + "/etc/dnsmasq"),
             ("/proc/$_p/maps", w + "/maps.$_p")]
    for a, b in pairs:
        body = body.replace(a, b)
    return body


shells = [["sh"]] + ([["busybox", "ash"]] if shutil.which("busybox") else [])
for shell in shells:
    tag = "ash" if shell[0] == "busybox" else "sh"
    w = tempfile.mkdtemp(prefix="diag1362_")
    try:
        T, J = make_root(w)
        # the maps fixture must name the repointed table path
        mp = os.path.join(w, "maps.101"); open(mp, "w").write("7f00 r--s %s/wallguard/db\n" % T)
        body = "\n".join(repoint(b, w, T, J) for b in (B3C, B4D, B11, B14C, B14H))
        sp = os.path.join(w, "run.sh")
        # LEGACY is set earlier in the real 14c; the lifted block ends after the line that reads it
        open(sp, "w").write("NVS=%s/nvs\nDFS=%s/dfs\nLEGACY=0\n%s\n%s" % (w, w, STUBS, body))
        r = subprocess.run(shell + [sp], capture_output=True, text=True, timeout=60)
        o = r.stdout
        check(tag + ": nothing on stderr", r.stderr.strip() == "", r.stderr[:800])
        # 3c
        check(tag + ": 3c mount flags", "mount /tmp        : nosuid,nodev" in o and "mount /jffs        : SUID-ALLOWED,DEV-ALLOWED" in o
              and "mount /var        : not a separate mount" in o, o[:900])
        check(tag + ": 3c a mount without nosuid/nodev is a WARN", "FINDING [WARN] /jffs is mounted without nosuid/nodev" in o)
        check(tag + ": 3c conntrack helpers", "automatic=1 (0 = only by rule)  raw CT rules=1" in o and "FINDING [WARN] the kernel attaches conntrack helpers" in o, o)
        check(tag + ": 3c the flood cap count", "log flood cap     : 2 line(s)" in o)
        check(tag + ": 3c a USB 3 lever that is set, and only that one", "usb3 levers       : dcm=1" in o and "credits" not in o)
        # 4d
        net = {m.group(1): m.group(0) for m in re.finditer(r"  sdn=(\d) .*", o)}
        check(tag + ": 4d main network row", "sdn=0 main network on br0" in o)
        check(tag + ": 4d a guest network: isolated, opt-ins counted, presets named, typed types counted",
              "br52 type=Guest  isolated=yes(2 rules)" in net.get("1", "") and "chosen-devices=2 (live REAPER_GUA rules 0)" in o
              and "discovery=print+cast+1-typed" in o and "lan-ports-too=1" in o, (net, o[o.find("#### 4d"):][:1500]))
        check(tag + ": 4d a portal without isolation rules is a WARN", "portal=yes" in net.get("2", "") and "FINDING [WARN] Guest Portal network br53 has no guest isolation rules" in o)
        check(tag + ": 4d a name is never printed (type word only), Access Intranet with main, VPN binding",
              "type=custom" in net.get("3", "") and "My" not in net.get("3", "") and "intranet-with-main=yes" in net.get("3", "")
              and "vpn=client-5" in net.get("3", ""), net.get("3"))
        check(tag + ": 4d a disabled network is left out", "sdn=4" not in o)
        check(tag + ": 4d chosen devices without a live rule is a WARN", "FINDING [WARN] network br52 names 2 main-network device(s)" in o)
        check(tag + ": 4d chosen devices' MACs come only from the devskip file (sanitized later)", "00:00:5e:00:53:01" not in o)
        check(tag + ": 4d chain counts and jumps", "REAPER_GUI  v4=3 v6=1 rules" in o and "PREROUTING jump 0" in o
              and "HOOK->GUI v4 1" in o and "HOOK_F->GUA v4 1" in o, o[o.find("-- guest isolation chains"):][:700])
        check(tag + ": 4d an empty REAPER_GUF after apply.sh is a WARN", "FINDING [WARN] guest isolation wrote its rules" in o)
        check(tag + ": 4d REAPER_GUN written but not hooked is a WARN", "FINDING [WARN] the guest DNS redirect (nat REAPER_GUN) is written but not hooked" in o)
        check(tag + ": 4d zone paths without the rules engine is an INFO", "FINDING [INFO] zone paths into guest networks are switched on but the rules engine is off" in o)
        check(tag + ": 4d bridge-port flags by kind", "br0  isolated ports: wifi 1/1  wired 1/2" in o and "FINDING [INFO] br0 has 1 isolated wired port(s)" in o, o)
        check(tag + ": 4d Guest Portal line and the dead-chilli WARN", "portal networks=1  chilli=0  tunnels=1" in o and "watchdog restarts=1" in o
              and "FINDING [WARN] a Guest Portal network is on but chilli is not running" in o, o)
        check(tag + ": 4d mDNS reflector lines", "enable-reflector=yes" in o and "reflect-interfaces=br0,br54" in o and "deny-interfaces=br53" in o
              and "discovery star    : br52(2 types)" in o, o[o.find("-- mDNS"):][:500])
        # 11 and 14c
        check(tag + ": 11 saved leases and name stores", re.search(r"saved lease copies: 2 file\(s\) in \S+/jffs/reaper/leases, last written 60s ago", o)
              and "dnsmasq-52=2" in o and "given (custom_clientlist)=2  reservations (dhcp_staticlist)=1  announced hostnames=3" in o, o[o.find("saved lease"):][:500])
        check(tag + ": 14c AiMesh set absent with nodes registered is a WARN", "aimesh exemption  : set reaper_aimesh absent entries  cfg_relist MAC records 3" in o
              and "FINDING [WARN] AiMesh nodes are registered but the shared exemption set reaper_aimesh is absent" in o, o[o.find("aimesh exemption"):][:400])
        # 14h
        check(tag + ": 14h Bastion switches", "bastion switches  : warden=1 dreadwatch=1 wallguard=1 encrypted-dns dot=1 doh=1  block 853=1 block doh=0" in o)
        check(tag + ": 14h Wallguard table, mapping and config counts",
              "table=1000 bytes mapped_by=1/2 dnsmasq instance(s)" in o and "lists=2 profiles=1 assignments=1" in o and "api-keys=1" in o, o[o.find("wallguard         :"):][:600])
        check(tag + ": 14h list states and the failed-list WARN", "hagezi_pro=ok(last good 2h ago)" in o and "oisd_big=failed(last good never ago)" in o
              and "FINDING [WARN] Wallguard: list(s) oisd_big(failed)" in o, o[o.find("list states"):][:400])
        check(tag + ": 14h a skipped build is a WARN", '"skip":"miss"' in o and "FINDING [WARN] Wallguard: the last table build was skipped (miss)" in o)
        check(tag + ": 14h pauses, live view, retry owed, counters", "pauses            : all=1 devices=1  live view=on  retry owed=yes (tries 2)" in o
              and "blocked=42 via-cname=3 not_recorded=1 since=1700000000" in o, o[o.find("pauses"):][:400])
        check(tag + ": 14h never prints a list address or an API key", "lists.example.com" not in o and "KeyValueNeverPrinted" not in o)
        check(tag + ": 14h rednsd state, listeners by protocol, traffic", "state=running up=60s" in o and "dot:853(wan=0,ok=1) x1" in o
              and "doh:443(wan=0,ok=0) x1" in o and "queries=100 doh_queries=40 refused peer=1" in o and "tls_fail=3" in o, o[o.find("rednsd   "):][:900])
        check(tag + ": 14h devices by protocol, never their addresses", "devices           : doh=1 dot=1" in o and "192.0.2.20" not in o and "192.0.2.21" not in o, o)
        check(tag + ": 14h a listener that could not bind is a WARN", "FINDING [WARN] Encrypted DNS: a listener could not bind" in o)
        check(tag + ": 14h option 162 published without the name", "dhcp option 162   : published (dot=1 doh=1)" in o
              and o.count("router.example.com") == 1 and "certificate       : {" in o, o.count("router.example.com"))
        check(tag + ": 14h the block chain absent while the block is on is a WARN", "block chain iptables: REAPER_EDNS absent" in o
              and "FINDING [WARN] the Encrypted DNS block is switched on but the REAPER_EDNS chain is absent" in o)
        check(tag + ": 14h DoH set sizes", "redns_doh=12 redns_doh6=3" in o)
        check(tag + ": 14h Let's Encrypt via DNS: SET/EMPTY only, the failure is a WARN", "provider=cloudflare domain=SET token=SET state=fail" in o
              and "SuperSecretTokenValue" not in o and "FINDING [WARN] Let's Encrypt via DNS failed on its last run" in o, o[o.find("lets encrypt"):][:500])
    finally:
        shutil.rmtree(w, ignore_errors=True)

for f in fails:
    print("  - " + f)
print("%d failed" % len(fails))
sys.exit(1 if fails else 0)
