#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_vts_emitter.py <router-src>  -- the port-forward (Virtual Server) emitter, compiled
and run on the host against known rule lists. reaper_verify check 24 ("vts-emitter").

WHY THIS EXISTS. A field report (2026-09-12, review R15) said every port forward on an
RT-BE88U stopped passing traffic after v3.1.0. The report's evidence could not tell whether
the DNAT lines were missing or merely unseen (it grepped nat/PREROUTING, where they never
are), and nothing in the tree could say either way without a router: the function that
turns `vts_rulelist` into `-A VSERVER ... -j DNAT` lines - rc/firewall.c
write_port_forwarding() - had never been executed outside a firmware. Reaper has touched
that function (the _fw_field_safe charset gate, the space-normalisation that keeps "80, 443"
alive), so a regression there is OURS to catch, at build time, on every rung.

WHAT IT DOES. Extracts write_port_forwarding() and its three Reaper helpers from the real
firewall.c (brace-matched, not copied), compiles them with an nvram stub that reads the
environment, and asserts the emitted lines for four rule lists: the reporter's exact list,
a list exercising source restrictions and a spaced port list, a metacharacter attempt that
MUST be dropped (it would abort the whole *nat restore), a raw-protocol rule, and a port range. Exit 0 pass, 1 fail, 77 skipped (no gcc).
"""
import os, re, shutil, subprocess, sys, tempfile

def die(msg):
    print(msg); sys.exit(1)

def extract(src, signature):
    i = src.find(signature)
    if i < 0: die("signature not found in firewall.c: %r" % signature)
    j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        c = src[k]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return src[i:k + 1]
        k += 1
    die("unbalanced braces after %r" % signature)

STUBS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <arpa/inet.h>
#define TYPE_IP      0
#define TYPE_MAC     1
#define TYPE_IPRANGE 2
static const char *NV(const char *k) { const char *v = getenv(k); return v ? v : ""; }
char *nvram_safe_get(const char *k) { return (char *)NV(k); }
int nvram_get_int(const char *k) { return atoi(NV(k)); }
int nvram_match(const char *k, const char *v) { return !strcmp(NV(k), v); }
int is_nat_enabled(void) { return 1; }
void logmessage(const char *tag, const char *fmt, ...) { va_list ap; va_start(ap, fmt); fprintf(stderr, "[%s] ", tag); vfprintf(stderr, fmt, ap); fputc('\n', stderr); va_end(ap); }
int addr_type_parse(const char *src, char *dst, int size) {
	if (!src || !*src) return -1;
	snprintf(dst, size, "%s", src);
	if (strchr(src, ':')) return TYPE_MAC;
	if (strchr(src, '-')) return TYPE_IPRANGE;
	return TYPE_IP;
}
int _vstrsep(char *buf, const char *sep, ...) {
	va_list ap; char **p; int n = 0;
	va_start(ap, sep);
	while ((p = va_arg(ap, char **)) != NULL) {
		*p = strsep(&buf, sep);
		if (!*p) break;
		n++;
	}
	va_end(ap);
	return n;
}
#define vstrsep(buf, sep, args...) _vstrsep(buf, sep, args, NULL)
'''
MAIN = r'''
int main(void) {
	write_port_forwarding(stdout, "vts_rulelist", "VSERVER", "192.168.50.1", "br0");
	return 0;
}
'''

# (label, rulelist, expected DNAT lines as token lists)
CASES = [
    ("the R15 reporter's list",
     "<Privoxy>8118>192.168.50.3>8118>TCP><Plex>18534>192.168.50.34>32400>BOTH>",
     ["-A VSERVER -p tcp -m tcp --dport 8118 -j DNAT --to-destination 192.168.50.3:8118",
      "-A VSERVER -p tcp -m tcp --dport 18534 -j DNAT --to-destination 192.168.50.34:32400",
      "-A VSERVER -p udp -m udp --dport 18534 -j DNAT --to-destination 192.168.50.34:32400"]),
    ("source restriction + spaced port list + no local port",
     "<web>80, 443>192.168.50.10>>TCP>203.0.113.7><cam>5000>192.168.50.11>5000>UDP>10.0.0.1-10.0.0.9>",
     ["-A VSERVER -s 203.0.113.7 -p tcp -m tcp --dport 80 -j DNAT --to 192.168.50.10",
      "-A VSERVER -s 203.0.113.7 -p tcp -m tcp --dport 443 -j DNAT --to 192.168.50.10",
      "-A VSERVER -m iprange --src-range 10.0.0.1-10.0.0.9 -p udp -m udp --dport 5000 -j DNAT --to-destination 192.168.50.11:5000"]),
    ("metacharacters in the port field are DROPPED, not emitted",
     "<evil>80 -j ACCEPT>192.168.50.3>80>TCP><ok>22>192.168.50.4>22>TCP>",
     ["-A VSERVER -p tcp -m tcp --dport 22 -j DNAT --to-destination 192.168.50.4:22"]),
    ("raw protocol number",
     "<gre>47>192.168.50.5>>OTHER>",
     ["-A VSERVER -p 47 -j DNAT --to 192.168.50.5"]),
    ("a port range in iptables form, and a local port that is not a port",
     "<range>1000:2000>192.168.50.6>>TCP><badl>25565>192.168.50.7>25565x>TCP>",
     ["-A VSERVER -p tcp -m tcp --dport 1000:2000 -j DNAT --to 192.168.50.6"]),
]

def main():
    if len(sys.argv) != 2: die("usage: check_vts_emitter.py <router-src>")
    fw = os.path.join(sys.argv[1], "rc", "firewall.c")
    if not os.path.isfile(fw): die("no rc/firewall.c under %s" % sys.argv[1])
    if not shutil.which("gcc"): print("gcc not available - emitter not exercised"); sys.exit(77)
    src = open(fw, encoding="utf-8", errors="replace").read()
    body = "\n".join([extract(src, "static int __attribute__((unused)) _fw_field_safe("),
                      extract(src, "static void __attribute__((unused)) _fw_strip_spaces("),
                      extract(src, "static int __attribute__((unused)) _fw_ports_ok("),
                      extract(src, "void write_port_forwarding(")])
    with tempfile.TemporaryDirectory(prefix="vts-emitter-") as td:
        cfile = os.path.join(td, "emit.c"); exe = os.path.join(td, "emit")
        open(cfile, "w").write(STUBS + body + MAIN)
        r = subprocess.run(["gcc", "-w", "-o", exe, cfile], capture_output=True, text=True)
        if r.returncode: die("the extracted emitter does not compile:\n" + r.stderr[:2000])
        failures = []
        for label, rl, want in CASES:
            env = dict(os.environ, vts_rulelist=rl, vts_enable_x="1", misc_http_x="0")
            out = subprocess.run([exe], env=env, capture_output=True, text=True, timeout=20).stdout
            got = [" ".join(l.split()) for l in out.splitlines() if l.strip()]
            if got != want:
                failures.append("%s:\n    expected:\n      %s\n    got:\n      %s" % (
                    label, "\n      ".join(want) or "(nothing)", "\n      ".join(got) or "(nothing)"))
        if failures:
            print("write_port_forwarding() emitted the wrong lines:"); print("\n".join(failures)); sys.exit(1)
    print("write_port_forwarding() from rc/firewall.c: %d rule lists, %d DNAT lines exactly as expected (incl. the R15 reporter's list); a metacharacter port is dropped" %
          (len(CASES), sum(len(w) for _, _, w in CASES)))

if __name__ == "__main__":
    main()
