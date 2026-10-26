#!/usr/bin/env python3
"""Warden country lists: fall back to ipdeny's plain list when the aggregated one is empty.

WHY. From 10:05 UTC on 2026-10-22 ipdeny served all 241 aggregated country lists as empty HTTP 200s
(its MD5SUM listed the empty-file hash for every one) while the plain per-country lists beside them
were intact. Warden kept each country's last good copy, but a country with no copy yet (a new install,
a country added that day) blocked nothing. The updater now fetches the plain list when the aggregated
one downloads fine but is empty - and only then: a failed download is not retried there.

WHAT IT DOES. Lifts geo_get out of rc/rwarden.c's generated update.sh (the C string literals,
unescaped), runs it under busybox ash (or sh) with a fake curl serving prepared bodies per URL, and
checks every path. Static checks pin the two plain URLs, the closing log line, and that the two
fprintf calls carry one argument per %s.
"""
import os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", os.environ.get("REAPER_SRC", ""))
RW = os.path.join(SRC, "rc", "rwarden.c")
if not os.path.exists(RW):
    print("SKIP: rwarden.c not found (%s)" % RW); sys.exit(0)
rw = open(RW, encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def unc(lit):
    return lit.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")

# ---- static
a = rw.find('"GEO_PLAIN=\\"\\"\\n"')
b = rw.find('"}\\n"', a)
check("geo_get with the plain fallback is in the generated updater", a > 0 and b > a)
if a < 0 or b < 0:
    print("\n".join(fails)); sys.exit(1)
body = "".join(unc(m) for m in re.findall(r'"((?:[^"\\]|\\.)*)"', rw[a:b + 6]))
check("v4 fetch passes the plain per-country list and a label",
      '"https://www.ipdeny.com/ipblocks/data/aggregated/%s-aggregated.zone\\" "\n\t\t\t  "\\"https://www.ipdeny.com/ipblocks/data/countries/%s.zone\\" %s; then' in rw)
check("v6 fetch passes the plain per-country list and a (v6) label",
      '"https://www.ipdeny.com/ipv6/ipaddresses/aggregated/%s-aggregated.zone\\" "\n\t\t\t  "\\"https://www.ipdeny.com/ipv6/ipaddresses/blocks/%s.zone\\" \\"%s(v6)\\"; then' in rw)
check("one closing log line names the countries that used the plain list",
      "[ -n \\\"$GEO_PLAIN\\\" ] && logger -t rwarden \\\"geo: ipdeny's aggregated list came back empty for:$GEO_PLAIN - loaded its plain per-country list instead (same coverage)\\\"" in rw)
for fam, url in (("v4", "ipblocks/data/aggregated/%s-aggregated.zone"), ("v6", "ipv6/ipaddresses/aggregated/%s-aggregated.zone")):
    i = rw.find('"if geo_get \\"https://www.ipdeny.com/' + url)
    j = rw.find(" cc);", i) + 4
    k = rw.rfind("fprintf(f,", 0, i)
    blk = rw[k:j]
    fmt = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', blk))
    nargs = len(re.findall(r"\bcc\b", blk.split('",')[-1]))
    check("%s fprintf: one argument per %%s (%d placeholders)" % (fam, fmt.count("%s")), fmt.count("%s") == nargs, (fmt.count("%s"), nargs))

# ---- run geo_get
SH = shutil.which("busybox")
shell = [SH, "ash"] if SH and subprocess.run([SH, "ash", "-c", "true"], capture_output=True).returncode == 0 else ["sh"]
AGG = "https://www.ipdeny.com/ipblocks/data/aggregated/fr-aggregated.zone"
PLAIN = "https://www.ipdeny.com/ipblocks/data/countries/fr.zone"

with tempfile.TemporaryDirectory() as td:
    curl = os.path.join(td, "curl")
    open(curl, "w").write(
        "#!/bin/sh\n"
        "out=''; url=''\n"
        "while [ $# -gt 0 ]; do case \"$1\" in -o) out=$2; shift;; https://*) url=$1;; esac; shift; done\n"
        "echo \"$url\" >> \"$W/fetched\"\n"
        "key=$(echo \"$url\" | tr -c 'a-z0-9\\n' '_')\n"
        "[ -f \"$W/fail_$key\" ] && exit 22\n"
        "if [ -f \"$W/body_$key\" ]; then cat \"$W/body_$key\" > \"$out\"; else : > \"$out\"; fi\n")
    os.chmod(curl, 0o755)

    def key(u): return re.sub(r"[^a-z0-9\n]", "_", u)

    def run(agg=None, plain=None, agg_fail=False, plain_fail=False, budget=True):
        w = tempfile.mkdtemp(dir=td)
        if agg is not None: open(os.path.join(w, "body_" + key(AGG)), "w").write(agg)
        if plain is not None: open(os.path.join(w, "body_" + key(PLAIN)), "w").write(plain)
        if agg_fail: open(os.path.join(w, "fail_" + key(AGG)), "w").write("1")
        if plain_fail: open(os.path.join(w, "fail_" + key(PLAIN)), "w").write("1")
        script = ("CURLG='%s'\nTMP=%s/tmp\ngeo_budget_left() { %s; }\n" % (curl, w, "true" if budget else "false")
                  + body + "\n"
                  "if geo_get '%s' '%s' \"fr(v6)\"; then echo RC=0; else echo RC=1; fi\n"
                  "echo \"GT=$GT\"; echo \"PLAIN=[$GEO_PLAIN]\"\n" % (AGG, PLAIN))
        env = dict(os.environ, W=w)
        p = subprocess.run(shell + ["-c", script], capture_output=True, text=True, env=env)
        out = dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
        f = os.path.join(w, "fetched")
        out["fetched"] = open(f).read().split() if os.path.exists(f) else []
        out["tmp"] = open(os.path.join(w, "tmp")).read() if os.path.exists(os.path.join(w, "tmp")) else None
        out["err"] = p.stderr
        return out

    x = run(agg="192.0.2.0/24\n", plain="198.51.100.0/24\n")
    check("aggregated list has data: used, plain never fetched, no fallback noted",
          x.get("RC") == "0" and x["fetched"] == [AGG] and x["tmp"] == "192.0.2.0/24\n" and x.get("PLAIN") == "[]", x)
    x = run(agg="", plain="198.51.100.0/24\n203.0.113.0/24\n")
    check("aggregated list empty: the plain list is fetched, used, and the country noted",
          x.get("RC") == "0" and x["fetched"] == [AGG, PLAIN] and x["tmp"] == "198.51.100.0/24\n203.0.113.0/24\n" and x.get("PLAIN") == "[ fr(v6)]", x)
    x = run(agg="", plain="")
    check("both empty: a failure (geo_fail keeps last-good), nothing noted", x.get("RC") == "1" and x.get("GT") == "1" and x.get("PLAIN") == "[]", x)
    x = run(agg="", plain_fail=True)
    check("aggregated empty, plain fails: a failure", x.get("RC") == "1" and x.get("PLAIN") == "[]", x)
    x = run(agg_fail=True, plain="198.51.100.0/24\n")
    check("aggregated download FAILS (network/404): not retried on the plain list (the budget is spent once)",
          x.get("RC") == "1" and x["fetched"] == [AGG] and x.get("GT") == "1", x)
    x = run(agg="192.0.2.0/24\n", budget=False)
    check("budget gone: nothing fetched, GT=0 (counted as skipped, not failed)", x.get("RC") == "1" and x.get("GT") == "0" and x["fetched"] == [], x)
    check("the function runs clean under %s" % " ".join(shell), not x["err"].strip(), x["err"])

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
