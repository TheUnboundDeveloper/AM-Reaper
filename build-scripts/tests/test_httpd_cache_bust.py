#!/usr/bin/env python3
"""httpd cache bust: a new firmware reaches the browser without anyone clearing a cache (owner, 2026-10-26).

WHY. Three ways a browser kept old files after a flash or a settings change:
  - stylesheets had a 1 h lifetime with no question asked;
  - an ETag was the hash of the FILE, but httpd fills scripts with dictionary text, so a translation change in a new
    image left the ETag - and the browser's copy - as it was;
  - scripts holding <% %> tags (menu.js: operation mode, dual WAN; rp.js: http_id; stock state.js) were hashed too,
    so a changed value answered "304 Not Modified" and the browser kept the old values.
On the 40585 base (merge stop 64) ASUS rewrote the ETag machinery: append_etag_header(file, handler, ...) with a
query-stripped path, mtime Last-Modified for static files, a `|ui_rev=` variant (lang/firmver/buildno/extendno/
productid) on every rendered handler's ETag, no_cache for every rendered handler, no user-agent special case. The
three Reaper items sit inside it: (1) `|bi=<build stamp>` on EVERY ETag (reaper_append_buildinfo_to_etag);
(2) .css and flag-1 .js answer no-cache whatever the handler row says; (3) a do_ej response that is text/html or
whose file holds "<%" gets NO ETag (reaper_file_has_ej).

WHAT IT DOES. Lifts the real etag_filter_table + getEtagHeaderFlag() through append_etag_header() out of
httpd/httpd.c and no_cache[] out of httpd/web.c (never copied by hand), compiles them on the host with stub nvram /
md5 helpers, and checks the headers for: a stylesheet and a static script (no-cache + an ETag carrying the build
stamp and, for scripts, ui_rev; 304 on a match; a new build stamp = a new ETag; another language = a new script
ETag), a script with <% %> (no ETag), an HTML page (no ETag), an image (its hour kept, the stamp in the ETag), a .asp
(no ETag, no-cache), a query string (same ETag). Plus the call site passes the handler.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "httpd.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

h = open(os.path.join(SRC, "httpd", "httpd.c"), encoding="utf-8", errors="replace").read()
web = open(os.path.join(SRC, "httpd", "web.c"), encoding="utf-8", errors="replace").read()
check("the call site passes the handler (ASUS 40585 signature)",
      "status = append_etag_header(file, handler, if_none_match, title, sizeof(title), final_header, sizeof(final_header));" in h)
def lift(text, start, end):
    a = text.index(start); b = text.index(end, a); return text[a:b]
region = lift(h, "struct etag_filter_table etag_filter_table[] = {", "int append_etag_header(")
func = lift(h, "int append_etag_header(", "\n}\n") + "\n}\n"
check("the three cache-bust items are inside append_etag_header()",
      "reaper_file_has_ej(file_path)" in func and "reaper_append_buildinfo_to_etag(etag_value, sizeof(etag_value));" in func
      and 'if (revalidate)\n\t\textra_header = no_cache;' in func)
check("no user-agent special case left in append_etag_header()", "user_agent" not in func and "safari" not in func.lower())
nocache = lift(web, "char no_cache[] =", ";") + ";"
uilen = re.search(r"#define UI_REV_HASH_LEN \d+", h)
check("UI_REV_HASH_LEN defined in httpd.c", uilen is not None)
gcc = shutil.which("gcc") or shutil.which("cc")
if not gcc:
    print("note: no host C compiler - header run skipped")
elif uilen:
    d = tempfile.mkdtemp()
    def w(n, s):
        p = os.path.join(d, n); open(p, "w").write(s); return p
    css = w("rp.css", "body{color:red}\n"); js = w("rp.js", "var a = `<#RLOG_1#>`;\n")
    dyn = w("menu.js", "var m = '<% nvram_get(\"sw_mode\"); %>';\n"); png = w("logo.png", "PNG")
    htm = w("message.htm", "<html></html>\n"); asp = w("Reaper_Log.asp", "<html></html>\n")
    harness = r'''
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <time.h>
#include <sys/stat.h>
#define RFC1123FMT "%a, %d %b %Y %H:%M:%S GMT"
''' + uilen.group(0) + r'''
static size_t strlcpy(char *d, const char *s, size_t n){ size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
static size_t strlcat(char *d, const char *s, size_t n){ size_t l = strlen(d); return l + strlcpy(d + l, s, n > l ? n - l : 0); }
struct etag_filter_table { const char *file; int flag; };
struct mime_handler { char *pattern; char *mime_type; char *extra_header; void (*input)(char *, FILE *, int, char *); void (*output)(char *, FILE *); void (*auth)(char *, char *, char *); };
static void do_file(char *p, FILE *s){ (void)p; (void)s; }
static void do_ej(char *p, FILE *s){ (void)p; (void)s; }
''' + nocache + r'''
static char NV_BI[128] = "Mon Oct 26 16:43:40 UTC 2026 root@build", NV_LANG[8] = "EN";
static char *nvram_safe_get(const char *k){ return !strcmp(k, "buildinfo") ? NV_BI : !strcmp(k, "preferred_lang") ? NV_LANG : !strcmp(k, "extendno") ? "Reaper_v3.5.0_BETA" : ""; }
static int hsh(const char *s, char *out, int len){ unsigned long x = 5381; while (*s) x = x * 33 + (unsigned char)*s++; snprintf(out, len, "%032lx", x); return 0; }
static int get_string_md5(const char *s, char *out, int len){ return hsh(s, out, len); }
static char *str_to_md5(const char *s, int l, char *out){ (void)l; hsh(s, out, 33); return out; }
static int get_file_md5(char *f, char *out, int len){ char b[4096] = ""; FILE *fp = fopen(f, "r"); if (!fp) return -1; fread(b, 1, sizeof(b) - 1, fp); fclose(fp); return hsh(b, out, len); }
static char cached_buildinfo[128], cached_buildinfo_md5[33];
''' + region + "\n" + func + r'''
static void run(const char *tag, const char *file, const char *extra, const char *inm, int rendered, const char *mime){
  struct mime_handler hd = { "x", (char *)mime, (char *)extra, NULL, rendered ? do_ej : do_file, NULL };
  char title[64] = "", fh[512] = ""; int st = append_etag_header((char *)file, &hd, (char *)inm, title, sizeof(title), fh, sizeof(fh));
  char *p; for (p = fh; *p; p++) if (*p == '\r') *p = ' '; else if (*p == '\n') *p = '#';
  printf("%s\t%d\t%s\n", tag, st, fh);
}
int main(int argc, char **argv){
  const char *css = argv[1], *js = argv[2], *dyn = argv[3], *png = argv[4], *htm = argv[5], *asp = argv[6];
  char cssq[1100];
  (void)argc;
  snprintf(cssq, sizeof(cssq), "%s?v=2", css);
  run("css", css, "Cache-Control: max-age=3600", NULL, 0, "text/css");
  run("cssq", cssq, "Cache-Control: max-age=3600", NULL, 0, "text/css");
  run("js", js, "Cache-Control: max-age=60", NULL, 1, "text/javascript");
  run("dyn", dyn, "Cache-Control: max-age=60", NULL, 1, "text/javascript");
  run("png", png, "Cache-Control: max-age=3600", NULL, 0, "image/png");
  run("htm", htm, "Cache-Control: max-age=60", NULL, 1, "text/html");
  run("asp", asp, "Cache-Control: max-age=60", NULL, 1, "text/html");
  { struct mime_handler hd = { "x", "text/css", "Cache-Control: max-age=3600", NULL, do_file, NULL };
    char title[64] = "", fh[512] = ""; char etag[200] = "";
    append_etag_header((char *)css, &hd, NULL, title, sizeof(title), fh, sizeof(fh));
    sscanf(strstr(fh, "ETag: ") + 6, "%199s", etag);
    run("css304", css, "Cache-Control: max-age=3600", etag, 0, "text/css");
    strcpy(NV_BI, "Tue Oct 27 09:00:00 UTC 2026 root@build");
    run("cssnewbuild", css, "Cache-Control: max-age=3600", etag, 0, "text/css");
    strcpy(NV_LANG, "RU"); run("jsru", js, "Cache-Control: max-age=60", NULL, 1, "text/javascript"); }
  return 0;
}
'''
    c = w("h.c", harness); exe = os.path.join(d, "h")
    r = subprocess.run([gcc, "-w", "-o", exe, c], capture_output=True, text=True)
    check("the lifted functions compile on the host", r.returncode == 0, r.stderr[-600:])
    if r.returncode == 0:
        out = subprocess.run([exe, css, js, dyn, png, htm, asp], capture_output=True, text=True).stdout
        R = {l.split("\t")[0]: (int(l.split("\t")[1]), l.split("\t")[2]) for l in out.strip().split("\n")}
        et = lambda k: re.search(r"ETag: (\S+)", R[k][1]).group(1) if "ETag: " in R[k][1] else None
        NC = "Cache-Control: no-cache"
        check("stylesheet: no-cache + ETag with the build stamp (was: an hour, no question asked)",
              R["css"][0] == 200 and R["css"][1].startswith(NC + " #ETag: ") and "max-age" not in R["css"][1]
              and "|bi=" in (et("css") or ""), R["css"])
        check("a query string does not change the stylesheet's ETag (path query-stripped)", et("cssq") == et("css"), (R["css"], R["cssq"]))
        check("static script: no-cache + ETag with ui_rev and the build stamp",
              R["js"][1].startswith(NC + " #ETag: ") and "|ui_rev=" in (et("js") or "") and "|bi=" in (et("js") or ""), R["js"])
        check("script with <% %> tags: no ETag, no-cache", R["dyn"][1] == NC, R["dyn"])
        check("image: its hour kept, ETag carries the stamp",
              R["png"][1].startswith("Cache-Control: max-age=3600 #ETag: ") and "|bi=" in (et("png") or ""), R["png"])
        check("HTML page: no ETag (the theme is injected), no-cache", R["htm"][1] == NC, R["htm"])
        check(".asp: no ETag, no-cache", R["asp"][1] == NC, R["asp"])
        check("a matching If-None-Match answers 304", R["css304"][0] == 304, R["css304"])
        check("a new build stamp changes the ETag: the old one no longer matches (200)",
              R["cssnewbuild"][0] == 200 and et("cssnewbuild") != et("css"), (R["css"], R["cssnewbuild"]))
        check("another language changes a script's ETag", bool(et("jsru")) and et("jsru") != et("js"), (R["js"], R["jsru"]))
    shutil.rmtree(d, ignore_errors=True)
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
