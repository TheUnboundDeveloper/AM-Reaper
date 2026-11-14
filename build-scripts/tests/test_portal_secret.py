#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal secret: random per router, or the admin's own (review 2026-11-11 B-C4; owner 2026-11-11).

WHY. The secret that ties the portal's sign-in page (uamsrv's closed portal module) to chilli shipped as the same
public value on every router (defaults "chillispot" / "ua8k69fo92n"), so a guest who knows the protocol could
compute a valid chilli sign-in and skip the passcode or terms page.
Owner: "Make it random but also ensure that there is a way for a admin to put their own access secret".

WHAT IT CHECKS.
- rc: reaper_uam_secret_ensure() sits in the chilli block and runs before each of the four secret reads; compiled on
  the host with stand-ins (a reversible fake cipher) it replaces an empty, plaintext-default or encrypted-default
  secret ONCE with 16 random [A-Za-z0-9] characters stored encrypted, leaves an admin's own secret alone, two routers
  get different secrets, and a missing random source leaves the value as it is.
- lighttpd nvram_get_uamsecret(): hands the portal module the STORED secret, never decrypted, never NULL. The portal
  module decrypts the value it is handed itself, as rc does for chilli's config: the _r16 decrypt here made every
  sign-in fail (_r4 on the owner's router, 2026-11-12). The host run models the module that way (pw_dec of the
  returned value) and requires it to equal what rc gives chilli.
- defaults: reaper_cp_secret_own (kept); the Tweaks page has NO Guest Portal panel any more (owner 2026-11-12);
  RTWK_42..46 still in all 25 packs, packs in lockstep.
Exit 0 pass, 1 fail, 77 skip (no router source tree)."""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "services.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))
def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

svc = rd("rc", "services.c")
a = svc.find("static void __attribute__((unused)) reaper_uam_secret_ensure(const char *key)\n{")
b = svc.find("/* reaper-uam-secret: end */")
blk = svc.rfind("#if defined(RTCONFIG_CHILLISPOT) || defined(RTCONFIG_COOVACHILLI)", 0, a) if a > 0 else -1
check("rc: the helper opens the chilli block, ahead of every portal config writer",
      0 < blk < a < b < svc.find("void chilli_config(void)") and svc[blk:a].count("\n") < 12)
check("rc: it runs before each of the four secret reads (cp_uamsecret x2, chilli_uamsecret x2)",
      svc.count('\treaper_uam_secret_ensure("cp_uamsecret");	/* review 2026-11-11 (B-C4) */\n\tchar *enc_value =  nvram_safe_get("cp_uamsecret");') == 2
      and svc.count('\treaper_uam_secret_ensure("chilli_uamsecret");	/* review 2026-11-11 (B-C4) */\n\tchar *chilli_uamsecret =  nvram_safe_get("chilli_uamsecret");') == 2
      and svc.count('nvram_safe_get("cp_uamsecret")') == 2 and svc.count('nvram_safe_get("chilli_uamsecret")') == 2)
check("rc: the stock defaults are the weak list; the new secret is stored as httpd stores an encrypted setting",
      'static const char *const reaper_pub[] = { "chillispot", "ua8k69fo92n", NULL };' in svc
      and "set_enc_nvram((char *)key, val, enc);\n\t\tnvram_set(key, enc);" in svc and "pw_dec(raw, dec, strlen(raw), 1);" in svc)

STUBS = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define RTCONFIG_NVRAM_ENCRYPT 1
static char NV[64][2][256]; static int NN, COMMITS, URAND_OK = 1; static unsigned SEED = 1;
static char *nvram_get(const char *k){ int i; for (i = 0; i < NN; i++) if (!strcmp(NV[i][0], k)) return NV[i][1]; return NULL; }
static char *nvram_safe_get(const char *k){ char *v = nvram_get(k); return v ? v : ""; }
static int nvram_set(const char *k, const char *v){ int i; for (i = 0; i < NN; i++) if (!strcmp(NV[i][0], k)) break;
  if (i == NN) { strcpy(NV[NN][0], k); NN++; } strcpy(NV[i][1], v); return 0; }
static int nvram_commit(void){ COMMITS++; return 0; }
/* a reversible stand-in for the closed cipher: stored = "E:" + reversed text; anything else decrypts to garbage */
static int pw_dec(const char *in, char *out, int len, int salt){ int n, i; (void)len; (void)salt;
  if (strncmp(in, "E:", 2)) { strcpy(out, "\x01gb"); return 0; } n = strlen(in + 2); for (i = 0; i < n; i++) out[i] = in[2 + n - 1 - i]; out[n] = 0; return 0; }
static int set_enc_nvram(char *name, char *in, char *out){ int n = strlen(in), i; (void)name; out[0] = 'E'; out[1] = ':';
  for (i = 0; i < n; i++) out[2 + i] = in[n - 1 - i]; out[2 + n] = 0; return 1; }
static int f_read(const char *p, void *buf, int n){ int i; (void)p; if (!URAND_OK) return -1; for (i = 0; i < n; i++) ((unsigned char *)buf)[i] = (unsigned char)(rand_r(&SEED) >> 3); return n; }
static void logmessage(const char *a, const char *f, ...){ (void)a; (void)f; }
'''
if 0 < a < b and CC:
    helper = svc[a:b]
    MAIN = r'''
static void decrypted(const char *k, char *o){ pw_dec(nvram_safe_get(k), o, 0, 1); }
static int okval(const char *s){ int i; if (strlen(s) != 16) return 0; for (i = 0; i < 16; i++) if (!strchr("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", s[i])) return 0; return 1; }
int main(void){
  char d[256], first[256]; int bad = 0;
  /* 1 empty -> random, stored encrypted, committed */
  reaper_uam_secret_ensure("cp_uamsecret"); decrypted("cp_uamsecret", d);
  if (strncmp(nvram_safe_get("cp_uamsecret"), "E:", 2) || !okval(d) || COMMITS != 1) { printf("empty: %s / %s\n", nvram_safe_get("cp_uamsecret"), d); bad++; }
  strcpy(first, d);
  /* 2 run again: the router's secret is kept */
  reaper_uam_secret_ensure("cp_uamsecret"); decrypted("cp_uamsecret", d);
  if (strcmp(d, first) || COMMITS != 1) { printf("not kept\n"); bad++; }
  /* 3 plaintext default, 4 encrypted default, 5 the other default -> replaced */
  nvram_set("chilli_uamsecret", "chillispot"); reaper_uam_secret_ensure("chilli_uamsecret"); decrypted("chilli_uamsecret", d);
  if (!okval(d)) { printf("plain default kept\n"); bad++; }
  nvram_set("chilli_uamsecret", "E:topsillihc"); reaper_uam_secret_ensure("chilli_uamsecret"); decrypted("chilli_uamsecret", d);
  if (!okval(d) || !strcmp(d, "chillispot")) { printf("encrypted default kept\n"); bad++; }
  nvram_set("chilli_uamsecret", "E:n29of96k8au"); reaper_uam_secret_ensure("chilli_uamsecret"); decrypted("chilli_uamsecret", d);
  if (!okval(d)) { printf("ua8k default kept\n"); bad++; }
  /* 6 an admin's own secret is left alone */
  nvram_set("cp_uamsecret", "E:1terceSnwOyM"); reaper_uam_secret_ensure("cp_uamsecret");
  if (strcmp(nvram_safe_get("cp_uamsecret"), "E:1terceSnwOyM")) { printf("own replaced\n"); bad++; }
  /* 7 two routers get different secrets */
  nvram_set("cp_uamsecret", ""); reaper_uam_secret_ensure("cp_uamsecret"); decrypted("cp_uamsecret", d);
  if (!strcmp(d, first)) { printf("same secret twice\n"); bad++; }
  /* 8 no random source: nothing written */
  URAND_OK = 0; nvram_set("cp_uamsecret", "chillispot"); reaper_uam_secret_ensure("cp_uamsecret");
  if (strcmp(nvram_safe_get("cp_uamsecret"), "chillispot")) { printf("wrote without randomness\n"); bad++; }
  return bad;
}
'''
    tmp = tempfile.mkdtemp()
    try:
        c = os.path.join(tmp, "h.c"); x = os.path.join(tmp, "h")
        open(c, "w").write(STUBS + helper + MAIN)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Wno-unused-parameter", "-o", x, c], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        if r.returncode == 0:
            r = subprocess.run([x], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=30)
        check("rc helper (host run): empty / plaintext default / encrypted defaults replaced once by 16 random characters, "
              "stored encrypted and kept; an own secret untouched; different per router; no randomness = no write",
              r.returncode == 0, r.stdout[-500:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

nvc = rd("lighttpd-1.4.39", "src", "nvram_control.c")
m = re.search(r"\nchar \*nvram_get_uamsecret\(const char \*str\)\n\{.*?\n\}\n", nvc, re.S)
check("lighttpd: nvram_get_uamsecret hands the module the stored secret (no pw_dec - the module decrypts), never NULL",
      m is not None and "pw_dec" not in m.group(0).split("*/")[-1] and "reaper_dec" not in m.group(0)
      and 'return reaper_sec ? reaper_sec : "";' in m.group(0))
if m and CC:
    LM = r'''
/* the portal module decrypts the value it is handed (on the router a decrypted secret failed every sign-in) */
static void module_secret(const char *net, char *o){ const char *s = nvram_get_uamsecret(net); memset(o, 0, 256); pw_dec(s, o, strlen(s), 1); }
/* what rc writes into chilli's config (services.c chilli_config*: pw_dec(value, buf, strlen(value), 1)) */
static void chilli_secret(const char *k, char *o){ const char *s = nvram_safe_get(k); memset(o, 0, 256); pw_dec(s, o, strlen(s), 1); }
int main(void){
  int bad = 0; const char *s; char a[256], b[256];
  nvram_set("chilli_net", "192.168.182.0/24"); nvram_set("cp_uamsecret", "E:1terceSnwOyM"); nvram_set("chilli_uamsecret", "E:topsillihc");
  module_secret("10.0.0.1", a); chilli_secret("cp_uamsecret", b);
  if (strcmp(a, b) || strcmp(a, "MyOwnSecret1")) { printf("cp: module %s / chilli %s\n", a, b); bad++; }
  module_secret("192.168.182.1", a); chilli_secret("chilli_uamsecret", b);
  if (strcmp(a, b) || strcmp(a, "chillispot")) { printf("chilli: module %s / chilli %s\n", a, b); bad++; }
  s = nvram_get_uamsecret("10.0.0.1"); if (strcmp(s, "E:1terceSnwOyM")) { printf("not stored form: %s\n", s); bad++; }
  NN = 0; s = nvram_get_uamsecret("x"); if (!s || *s) { printf("unset not empty\n"); bad++; }
  return bad;
}
'''
    tmp = tempfile.mkdtemp()
    try:
        c = os.path.join(tmp, "l.c"); x = os.path.join(tmp, "l")
        open(c, "w").write(STUBS + m.group(0) + LM)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wno-unused-function", "-o", x, c], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        if r.returncode == 0:
            r = subprocess.run([x], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=30)
        check("lighttpd helper (host run): the portal module gets exactly what rc gives chilli, for either portal type; unset is \"\"",
              r.returncode == 0, r.stdout[-400:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

dfl = rd("shared", "defaults.c")
check("defaults: reaper_cp_secret_own, off", '{ "reaper_cp_secret_own", "0", CKN_STR1,' in dfl)
tw = rd("www", "Reaper_Tweaks.asp")
# 2026-11-12 (owner): the Tweaks "Guest Portal" panel is removed - the router keeps the random secret rc makes for it
# (above); nothing on the page reads, posts or restarts anything for the portal secret any more
check("Tweaks: the Guest Portal secret panel is gone and the page never touches the portal secret",
      'id="p_cpsec"' not in tw and "t_cp_own" not in tw and "i_cp_secret" not in tw
      and "reaper_cp_secret_own" not in tw and "uamsecret" not in tw and "restart_chilli" not in tw
      and "section('p_cpsec'" not in tw)
www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(www) if f.endswith(".dict") and f != "temp.dict")
missing = [f + ":" + k for f in packs for k in ("RTWK_42", "RTWK_43", "RTWK_44", "RTWK_45", "RTWK_46")
           if not re.search(r"(?m)^%s=\S" % k, open(os.path.join(www, f), encoding="utf-8", errors="replace").read())]
counts = {len(open(os.path.join(www, f), encoding="utf-8", errors="replace").read().split("\n")) for f in packs}
check("RTWK_42..46 in all 25 packs, the packs in lockstep", len(packs) == 25 and not missing and len(counts) == 1, (missing[:5], counts))

print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
