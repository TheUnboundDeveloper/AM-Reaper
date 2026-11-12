#!/usr/bin/env python3
"""httpd -6: the IPv6-only option must be in the getopt string (audit finding, fixed 2026-11-10).

WHY. rc starts the IPv6 remote-access instance as `httpds -s -i <wan6 if> -p <port> -6`, and httpd.c has a
`case '6': http_ipv6_only = 1;` for it - but the option string was "sp:i:" (stock), so getopt() reported -6 as
unknown and the flag stayed 0. That instance then also bound IPv4 on the WAN interface, and it read and cleared
`httpds_reload_cert` (the LAN instance's certificate-reload flag) instead of `httpds6_reload_cert`.

WHAT IT DOES. Reads the real httpd/httpd.c and rc/services.c and checks that every option letter main() handles
in its getopt switch is present in the option string, that `6` is one of them, that the flag still selects the
IPv6-only bind and the httpds6 reload flag, and that rc still passes -6 to that instance.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: argv[1] or REAPER_ROUTER_SRC = .../release/src/router).
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "httpd.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

hc, svc = rd("httpd/httpd.c"), rd("rc/services.c")

m = re.search(r'while \(\(c = getopt\(argc, argv, "([^"]*)"\)\) != -1\) \{(.*?)\n\t\}\n', hc, re.S)
check("httpd.c: main()'s getopt loop found", bool(m))
if m:
    optstr, body = m.group(1), m.group(2)
    handled = re.findall(r"case '(.)':", body)
    letters = set(optstr.replace(":", ""))
    check("getopt string has an entry for every handled option", all(h in letters for h in handled),
          "string %r, handled %r" % (optstr, handled))
    check("getopt string accepts -6", "6" in letters, optstr)
    check("-6 takes no argument", "6:" not in optstr, optstr)
    check("case '6' sets http_ipv6_only", re.search(r"case '6':\s*\n\s*http_ipv6_only = 1;", body) is not None)

check("the IPv4 bind on the interface is skipped when http_ipv6_only", "!http_ipv6_only &&" in hc)
check("the IPv6-only instance reads its own reload flag",
      re.search(r'if \(http_ipv6_only\)\s*\n\s*reload_cert = nvram_get_int\("httpds6_reload_cert"\);', hc) is not None)
check("the IPv6-only instance clears its own reload flag",
      'else if (http_ipv6_only && nvram_get("httpds6_reload_cert"))' in hc)
check("rc passes -6 to the IPv6 remote-access instance (both start paths)",
      svc.count('https_ipv6_argv[https_ipv6_index++] = "-6";') >= 2,
      svc.count('https_ipv6_argv[https_ipv6_index++] = "-6";'))

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  " + f)
    sys.exit(1)
print("\nall checks passed")
