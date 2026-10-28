#!/usr/bin/env python3
"""httpd cache bust: a new firmware reaches the browser without anyone clearing a cache (owner, 2026-10-26).

WHY. Three ways a browser kept old files after a flash or a settings change:
  - stylesheets had a 1 h lifetime with no question asked;
  - an ETag was the hash of the FILE, but httpd fills scripts with dictionary text, so a translation change in a new
    image left the ETag - and the browser's copy - as it was;
  - scripts holding <% %> tags (menu.js: operation mode, dual WAN; rp.js: http_id; stock state.js) were hashed too,
    so a changed value answered "304 Not Modified" and the browser kept the old values.
This is the 3006.102.8 line's suite (Dev-102.8: GT-BE98, GT-BE19000, BQ16, BQ16 Pro). On this base the ETag
machinery is the stock append_etag_header(file, extra_header, ..., rendered, mime) with its Safari special case;
the three Reaper items sit inside it: (1) the md5 of the build stamp (nvram buildinfo) appended to EVERY ETag;
(2) .css and flag-1 .js answer "Cache-Control: no-cache" whatever the handler row says, with or without an ETag;
(3) a rendered response that is text/html or whose file holds "<%" gets NO ETag and keeps the handler's own
Cache-Control. (The 3006.102.10 line carries a different suite for ASUS 40585's reworked machinery.)

WHAT IT DOES. Lifts the real etag_filter_table, getEtagHeaderFlag(), reaper_file_has_ej() and append_etag_header()
out of httpd/httpd.c (never copied by hand), compiles them on the host with stub nvram / md5 helpers, and checks the
headers for: a stylesheet and a static script (no-cache + an ETag carrying the build stamp; 304 on a match; a new
build stamp = a new ETag; another language = a new script ETag), a script with <% %> (no ETag), an HTML page (no
ETag), a Safari stylesheet (no ETag, still no-cache). Plus the call site passes rendered + mime.
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
check("the call site passes rendered (do_ej) and the mime type",
      re.search(r"status = append_etag_header\(file, handler->extra_header, if_none_match, title, sizeof\(title\), "
                r"final_header, sizeof\(final_header\),\s*handler->output == do_ej, handler->mime_type\);", h) is not None)
def lift(text, start, end):
    a = text.index(start); b = text.index(end, a); return text[a:b]
region = lift(h, "struct etag_filter_table etag_filter_table[] = {", "int append_etag_header(")
func = lift(h, "int append_etag_header(", "\n}\n") + "\n}\n"
check("the three cache-bust items are inside append_etag_header()",
      "reaper_file_has_ej(file)" in func and 'nvram_safe_get("buildinfo")' in func
      and 'strlcpy(final_header, "Cache-Control: no-cache\\r\\n", final_header_len);' in func
      and 'strlcpy(final_header, "Cache-Control: no-cache", final_header_len);' in func)
check("reaper_file_has_ej() is defined before append_etag_header()", "static int reaper_file_has_ej(const char *file)" in region)
gcc = shutil.which("gcc") or shutil.which("cc")
if not gcc:
    print("note: no host C compiler - header run skipped")
else:
    d = tempfile.mkdtemp()
    def w(n, s):
        p = os.path.join(d, n); open(p, "w").write(s); return p
    css = w("rp.css", "body{color:red}\n"); js = w("rp.js", "var a = `<#RLOG_1#>`;\n")
    dyn = w("menu.js", "var m = '<% nvram_get(\"sw_mode\"); %>';\n"); htm = w("message.htm", "<html></html>\n")
    harness = r'''
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <time.h>
#include <sys/stat.h>
#define RFC1123FMT "%a, %d %b %Y %H:%M:%S GMT"
static size_t strlcpy(char *d, const char *s, size_t n){ size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
static size_t strlcat(char *d, const char *s, size_t n){ size_t l = strlen(d); return l + strlcpy(d + l, s, n > l ? n - l : 0); }
struct etag_filter_table { char *file; int flag; };
static char user_agent[256] = "Mozilla/5.0 Chrome/130 Safari/537.36";
static char NV_BI[128] = "Mon Oct 26 16:43:40 UTC 2026 root@build", NV_LANG[8] = "EN";
static char *nvram_safe_get(const char *k){ return !strcmp(k, "buildinfo") ? NV_BI : !strcmp(k, "preferred_lang") ? NV_LANG : !strcmp(k, "extendno") ? "Reaper_v3.6.0_BETA" : ""; }
static int hsh(const char *s, char *out, int len){ unsigned long x = 5381; while (*s) x = x * 33 + (unsigned char)*s++; snprintf(out, len, "%032lx", x); return 0; }
static int get_string_md5(const char *s, char *out, int len){ return hsh(s, out, len); }
static int get_file_md5(char *f, char *out, int len){ char b[4096] = ""; FILE *fp = fopen(f, "r"); if (!fp) return -1; fread(b, 1, sizeof(b) - 1, fp); fclose(fp); return hsh(b, out, len); }
static char cached_buildinfo[128], cached_buildinfo_md5[33], cached_extendno[256], cached_extendno_md5[33];
''' + region + "\n" + func + r'''
static void run(const char *tag, const char *file, const char *extra, const char *inm, int rendered, const char *mime){
  char title[64] = "", fh[512] = ""; int st = append_etag_header((char *)file, (char *)extra, (char *)inm, title, sizeof(title), fh, sizeof(fh), rendered, mime);
  char *p; for (p = fh; *p; p++) if (*p == '\r') *p = ' '; else if (*p == '\n') *p = '#';
  printf("%s\t%d\t%s\n", tag, st, fh);
}
int main(int argc, char **argv){
  const char *css = argv[1], *js = argv[2], *dyn = argv[3], *htm = argv[4];
  (void)argc;
  run("css", css, "Cache-Control: max-age=3600", NULL, 0, "text/css");
  run("js", js, "Cache-Control: max-age=60", NULL, 1, "text/javascript");
  run("dyn", dyn, "Cache-Control: max-age=60", NULL, 1, "text/javascript");
  run("htm", htm, "Cache-Control: max-age=60", NULL, 1, "text/html");
  { char title[64] = "", fh[512] = ""; char etag[200] = "";
    append_etag_header((char *)css, "Cache-Control: max-age=3600", NULL, title, sizeof(title), fh, sizeof(fh), 0, "text/css");
    sscanf(strstr(fh, "ETag: ") + 6, "%199s", etag);
    run("css304", css, "Cache-Control: max-age=3600", etag, 0, "text/css");
    strcpy(NV_BI, "Tue Oct 27 09:00:00 UTC 2026 root@build");
    run("cssnewbuild", css, "Cache-Control: max-age=3600", etag, 0, "text/css");
    strcpy(NV_LANG, "RU"); run("jsru", js, "Cache-Control: max-age=60", NULL, 1, "text/javascript"); }
  strcpy(user_agent, "Mozilla/5.0 Version/17 Safari/605.1.15");
  run("safari_css", css, "Cache-Control: max-age=3600", NULL, 0, "text/css");
  return 0;
}
'''
    c = w("h.c", harness); exe = os.path.join(d, "h")
    r = subprocess.run([gcc, "-w", "-o", exe, c], capture_output=True, text=True)
    check("the lifted functions compile on the host", r.returncode == 0, r.stderr[-600:])
    if r.returncode == 0:
        out = subprocess.run([exe, css, js, dyn, htm], capture_output=True, text=True).stdout
        R = {l.split("\t")[0]: (int(l.split("\t")[1]), l.split("\t")[2]) for l in out.strip().split("\n")}
        et = lambda k: re.search(r"ETag: (\S+)", R[k][1]).group(1) if "ETag: " in R[k][1] else None
        NC = "Cache-Control: no-cache"
        check("stylesheet: no-cache + an ETag that carries the build stamp (was: an hour, no question asked)",
              R["css"][0] == 200 and R["css"][1].startswith(NC + " #ETag: ") and "max-age" not in R["css"][1]
              and len(et("css") or "") >= 64, R["css"])
        check("static script: no-cache + ETag", R["js"][1].startswith(NC + " #ETag: "), R["js"])
        check("script with <% %> tags: no ETag, the handler's own Cache-Control",
              "ETag" not in R["dyn"][1] and R["dyn"][1] == "Cache-Control: max-age=60", R["dyn"])
        check("HTML page: no ETag (the theme is injected)", "ETag" not in R["htm"][1], R["htm"])
        check("a matching If-None-Match answers 304", R["css304"][0] == 304, R["css304"])
        check("a new build stamp changes the ETag: the old one no longer matches (200)",
              R["cssnewbuild"][0] == 200 and et("cssnewbuild") != et("css"), (R["css"], R["cssnewbuild"]))
        check("another language changes a script's ETag", bool(et("jsru")) and et("jsru") != et("js"), (R["js"], R["jsru"]))
        check("Safari (no ETag on this base): a stylesheet still answers no-cache", R["safari_css"][1] == NC, R["safari_css"])
    shutil.rmtree(d, ignore_errors=True)
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
