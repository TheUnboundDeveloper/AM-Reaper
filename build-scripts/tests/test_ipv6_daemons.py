#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rtrafd and rmcpd over IPv6 (IPv6 remediation 2026-10-07, findings A6 and A8) - wiring pinned.

WHY THIS EXISTS. rtrafd attributed IPv6 flows to devices since v2.4.4 but probed, counted and
labelled over IPv4 only: an IPv6-only device had no RTT, no connection count and a bare MAC for
a label. rmcpd bound lan_ipaddr alone, so an Advisor client on an IPv6-only path could not reach
it. Neither daemon compiles on the host (hardware headers, libshared), so this test pins the
source: the shapes that make the feature exist, and the guards that keep it honest - the ICMPv6
reply must come from the address that slot was probed at (the same spoof guard as IPv4), the
IPv6 listener binds the LAN's own address and never [::], the fence rule has its ip6tables twin,
a pinned client is compared within its own family, and the ip6 label is runtime-only so the
on-disk history layout (DB_VER) does not change.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] or REAPER_ROUTER_SRC)."""
import glob, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rtrafd", "rtrafd.c")):
    skip("no router source tree with rtrafd (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def has_all(src, wants):
    return [w for w in wants if w not in src]

# ---------------------------------------------------------------- rtrafd (A6)
r = read("rtrafd/rtrafd.c")
check("rtrafd uses the shared neighbour cache (no private netlink dump left)",
      not has_all(r, ["static struct reaper_nd nd_tbl[NND];", "nd_n = reaper_nd_load(nd_tbl, NND);"]) and
      "req.nh.nlmsg_type  = RTM_GETNEIGH;" not in r, "")
check("the ip6 label is runtime-only: cli6[] beside cli[], never inside dbhdr_t / cli_t",
      "static char cli6[NCLI][46];" in r and "char ip[16];" in r and "ip6" not in r[r.index("typedef struct {\n\tchar key[20];"):r.index("} cli_t;")], "")
check("cli6_refresh() runs with the neighbour cache each conntrack pass and takes the MAC's first global address",
      not has_all(r, ["static void cli6_refresh(void)", "reaper_nd_addr_of(nd_tbl, nd_n, cli[i].key, a)", "\tcli6_refresh();"]), "")
check("ICMPv6 probe: a second raw socket with an echo-reply-only filter, non-blocking, close-on-exec",
      not has_all(r, ["#include <netinet/icmp6.h>", "static int hp_fd6 = -1;", "socket(AF_INET6, SOCK_RAW, IPPROTO_ICMPV6)",
                      "ICMP6_FILTER_SETPASS(ICMP6_ECHO_REPLY, &flt);", "fcntl(hp_fd6, F_SETFL, fl | O_NONBLOCK);", "fcntl(hp_fd6, F_SETFD, FD_CLOEXEC);"]), "")
check("send: an IPv6-only device (no IPv4 label) is probed at its ip6 with the same id/seq scheme",
      not has_all(r, ["if (hp_fd6 < 0 || !cli6[i][0]) continue;", "p6.icmp6_type = ICMP6_ECHO_REQUEST;",
                      "p6.icmp6_id = htons(hp_id);", "p6.icmp6_seq = htons((uint16_t)i);", "sendto(hp_fd6, &p6, sizeof(p6), 0, (struct sockaddr *)&to6, sizeof(to6));"]), "")
check("drain: an ICMPv6 reply counts only from the address the slot was probed at (the IPv4 spoof guard, twinned)",
      not has_all(r, ["if (i6->icmp6_type != ICMP6_ECHO_REPLY || ntohs(i6->icmp6_id) != hp_id) continue;",
                      "if (!cli6[slot][0] || inet_pton(AF_INET6, cli6[slot], &want) != 1) continue;",
                      "if (memcmp(&from6.sin6_addr, &want, 16) != 0) continue;", "hp_rtt_update(slot, &now);"]) and
      r.count("hp_rtt_update(slot, &now);") == 2, "")
check("the IPv4 drain and the IPv6 drain fold replies through one EWMA helper (no second copy of the arithmetic)",
      r.count("chealth[slot].jit_ms = chealth[slot].jit_ms * 0.75f + d * 0.25f;") == 1, "")
check("TCP counts: IPv6 TCP entries are counted for the neighbour-cache MAC's row",
      not has_all(r, ["static void hp_count_conn6(const char *src, const char *line)", "else hp_count_conn6(src, line);",
                      "!nd_lookup(a, mac, sizeof(mac), NULL)) return;", "if ((slot = cli_index_get(mac)) < 0) return;"]) and
      "if (hcount && !v6 && strcmp(proto, \"tcp\") == 0) hp_count_conn(src, line);" not in r, "")
check("emits: ip6 in the history client map, the live dev rows, health.json and as a metrics label",
      r.count('"ip6\\":\\"%s\\"') >= 3 and 'ip6=\\"%s\\"' in r and r.count("jesc(cli6[i], eb") >= 3 and "jesc(cli6[i], eb3, sizeof(eb3))" in r, r.count('"ip6\\":\\"%s\\"'))
t = read("www/Reaper_Traffic.asp")
check("Traffic page: an IPv6-only device row shows its address, not a bare MAC",
      "devCell(r.ip||r.ip6,r.mac)" in t and "ip=cli[k].ip||cli[k].ip6||''" in t, "")

# ---------------------------------------------------------------- rmcpd (A8)
m = read("rmcpd/rmcpd.c")
check("rmcpd binds the LAN's own IPv6 address (ipv6_rtr_addr), v6-only, never [::]",
      not has_all(m, ['nvram_safe_get(ipv6_nvname("ipv6_rtr_addr"))', "setsockopt(ls6, IPPROTO_IPV6, IPV6_V6ONLY, &one, sizeof(one));",
                      "inet_pton(AF_INET6, g_lan_ip6, &sa6.sin6_addr) != 1"]) and "in6addr_any" not in m and "sin6_addr = in6addr" not in m, "")
check("the IPv6 listener is best effort: a bind failure logs and leaves the IPv4 listener armed",
      not has_all(m, ['syslog(LOG_WARNING, "rmcpd: IPv6 listener [%s]:%d: %m - IPv4 only"', "ls6 = -1;\n\t\t\t\tg_lan_ip6[0] = 0;"]), "")
check("fence: an ip6tables twin; a pinned client belongs to one family and the other family's rule is not inserted",
      not has_all(m, ['static int fence_one(const char *tool, const char *op, const char *src)', 'fence_one("iptables", op, g_client_ip);',
                      'fence_one("ip6tables", op, pin6 ? g_client_ip : "")', "int pin6 = g_client_ip[0] && strchr(g_client_ip, ':') != NULL;"]), "")
check("accept: both listeners are polled and the client pin is compared within the peer's family",
      not has_all(m, ["if (ls6 >= 0) FD_SET(ls6, &rf);", "select((ls6 > ls ? ls6 : ls) + 1, &rf, NULL, NULL, &tv);",
                      "struct sockaddr_storage ca;", "accept(FD_ISSET(ls, &rf) ? ls : ls6, (struct sockaddr *)&ca, &cl);",
                      "inet_ntop(AF_INET6, &((struct sockaddr_in6 *)&ca)->sin6_addr, peer, sizeof(peer));",
                      "if (strcmp(peer, g_client_ip)) { close(cfd); continue; }", "if (ls6 >= 0) close(ls6);"]), "")
check("the pin sanitiser accepts an IPv6 literal and still refuses anything that is not an address",
      "inet_pton(AF_INET6, g_client_ip, &a6) != 1)\n\t\tg_client_ip[0] = 0;" in m and 'static char  g_client_ip[48]' in m, "")
w = read("httpd/web.c")
check("httpd: the arming reply names the IPv6 endpoint when the LAN holds an address; the session writer keeps an IPv6 pin",
      not has_all(w, ['",\\"url6\\":\\"%s://[%s]:%s/mcp\\""', 'inet_pton(AF_INET6, r6, &t6) == 1',
                      "if (!(isxdigit((unsigned char)*c) || *c == '.' || *c == ':')) { clbuf[0] = '\\0'; break; }"]), "")
a = read("www/Reaper_Advisor.asp")
check("Advisor page shows the IPv6 endpoint line", 'id="epUrl6"' in a and "d.url6||'-'" in a and "<#RADV_76#>" in a, "")
dicts = [d for d in glob.glob(os.path.join(SRC, "www", "*.dict")) if not d.endswith("temp.dict")]
if len(dicts) != 25: die("expected 25 dictionaries, found %d" % len(dicts))
for d in dicts:
    if not re.search(r"^RADV_76=", open(d, encoding="utf-8", errors="surrogateescape").read(), re.M):
        die("%s lacks RADV_76" % os.path.basename(d))
check("RADV_76 exists in all 25 dictionaries", True)
mk = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_markers.txt"), encoding="utf-8").read()
check("markers pin the staged rtrafd, rmcpd, httpd and page",
      all(x in mk for x in ('bin/rtrafd|"ip6":"%s"|1', 'bin/rtrafd|ip6="%s"|1', "bin/rmcpd|ip6tables|1", "bin/rmcpd|IPv6 listener|1",
                            'usr/sbin/httpd|"url6":|1', "www/Reaper_Advisor.asp|epUrl6|1")))

if fails:
    print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
print("all checks passed: rtrafd probes, counts and labels IPv6-only devices through the shared neighbour cache, and rmcpd answers on the LAN's IPv6 address with the same fence and pin discipline")
