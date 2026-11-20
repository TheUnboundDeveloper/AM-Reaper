#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Model headers as WebP (2026-11-17): the identity guards still hold for every model.

WHY THIS EXISTS. Each model ships its own header and animated header, and the header's FILE NAME is how the release
path knows a build carries the right model's identity (a foreign banner was the v1.8.6 clobber). The files became
WebP to give back about 1.5 MB of image per model. The name is spelled in four scripts and a checksum is pinned per
model; a switch that reaches only some of them either stops every sibling build or lets a wrong banner through.

WHAT IT DOES. Reads build_one.sh, check_overlays.py, _port_protect.sh, reaper_verify.sh and reaper-mockups/ of this
repository: every model names a .webp header, the pinned checksum is the checksum of that model's file in
reaper-mockups/, both files of every pair exist and are WebP, a header of either format under another name is
foreign. Runs the overlay gate on made-up overlays (a correct one, a foreign banner, a non-banner change, the old
format) and the name normaliser on sample lines. Exit 0 pass, 1 fail."""
import hashlib, importlib.util, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BS = os.path.normpath(os.path.join(HERE, ".."))
MOCK = os.path.normpath(os.path.join(BS, "..", "reaper-mockups"))
fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))


rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
STEMS = {"RT-BE96U": "RT-96U", "RT-BE86U": "RT-BE86U", "RT-BE88U": "RT-BE88U", "GT-BE98": "GT-BE98", "GT-BE98_PRO": "GT-BE98P",
         "RT-BE92U": "RT-BE92U", "GT-BE19000": "GT-BE19000", "BQ16": "BE25000", "BQ16_PRO": "BE30000"}

# ---------------------------------------------------------------- the art
bad = []
for m, s in STEMS.items():
    for n in (s + "_REAPER_Header.webp", s + "_REAPER_Header_anim.webp"):
        p = os.path.join(MOCK, n)
        if not os.path.isfile(p):
            bad.append(n + " missing")
            continue
        b = open(p, "rb").read()
        if b[:4] != b"RIFF" or b[8:12] != b"WEBP" or len(b) > 200000:
            bad.append("%s is not a WebP of at most 200 KB (%d B)" % (n, len(b)))
        if n.endswith("_anim.webp") and b"ANMF" not in b:
            bad.append(n + " is not animated")
check("art: every model has a WebP header and an animated WebP header in reaper-mockups/", not bad, bad)

# ---------------------------------------------------------------- build_one.sh
bo = rd(os.path.join(BS, "ci", "build_one.sh"))
rows = dict(re.findall(r"\n  ([A-Z0-9_-]+)\)\s+WANT_BANNER=(\S+?);;", bo))
check("build: each of the nine models must stage its own .webp header",
      rows == {m: s + "_REAPER_Header.webp" for m, s in STEMS.items()}, rows)
check("build: a header of either format under another name stops the build (this model's old .png included)",
      'ls "$BANNER_DIR"/*_REAPER_Header.png "$BANNER_DIR"/*_REAPER_Header.webp 2>/dev/null | grep -v "/$WANT_BANNER\\$"' in bo)

# ---------------------------------------------------------------- reaper_verify.sh
rv = rd(os.path.join(BS, "reaper_verify.sh"))
pins = {m: (h, f) for m, h, f in re.findall(r"\n  ([A-Z0-9_-]+)\)\s+want_ban=([0-9a-f]{64}); ban_file=(\S+?);;", rv)}
want = {}
for m, s in STEMS.items():
    p = os.path.join(MOCK, s + "_REAPER_Header.webp")
    want[m] = (hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else "missing", s + "_REAPER_Header.webp")
check("image check: every model's pinned checksum is the checksum of its header in reaper-mockups/",
      pins == want, {m: (pins.get(m), want[m]) for m in want if pins.get(m) != want[m]})
check("image check: a header of either format under another name fails it",
      'ls "$FS"/www/images/*_REAPER_Header.png "$FS"/www/images/*_REAPER_Header.webp 2>/dev/null | grep -v "/${ban_file}\\$"' in rv)
check("image check: the scan for pages that name a header that is not staged reads both formats",
      "grep -rhoE '[A-Za-z0-9-]+_REAPER_Header(_anim)?\\.(png|webp)' " in rv)
check("image check: two different models never share a checksum (except the BQ16 Pro's placeholder = the BQ16's art)",
      len(set(h for m, (h, f) in pins.items() if m != "BQ16_PRO")) == 8 and pins.get("BQ16_PRO", ("",))[0] == pins.get("BQ16", (" ",))[0])

# ---------------------------------------------------------------- the overlay gate, on made-up overlays
spec = importlib.util.spec_from_file_location("check_overlays", os.path.join(BS, "ci", "check_overlays.py"))
co = importlib.util.module_from_spec(spec); spec.loader.exec_module(co)
I = "release/src/router/www/images/"


def overlay(stem, ext="webp", canon_ext="webp", page_stem=None, extra=None):
    page_stem = page_stem or stem
    t = []
    for n in ("RT-96U_REAPER_Header", "RT-96U_REAPER_Header_anim"):
        t += ["diff --git a/%s%s.%s b/%s%s.%s" % (I, n, canon_ext, I, n, canon_ext), "deleted file mode 100644", "GIT binary patch", "literal 0", ""]
    for n in (stem + "_REAPER_Header", stem + "_REAPER_Header_anim"):
        t += ["diff --git a/%s%s.%s b/%s%s.%s" % (I, n, ext, I, n, ext), "new file mode 100644", "GIT binary patch", "literal 5", ""]
    for pg in sorted(co.BANNER_REF_FILES):
        t += ["diff --git a/%s b/%s" % (pg, pg), "--- a/" + pg, "+++ b/" + pg,
              '-<img src="images/RT-96U_REAPER_Header_anim.%s">' % canon_ext, '+<img src="images/%s_REAPER_Header_anim.%s">' % (page_stem, ext)]
        if extra and pg.endswith("reaper_shell.asp"):
            t += ["-<p>one</p>", "+<p>two</p>"]
    return "\n".join(t) + "\n"


tmp = tempfile.mkdtemp(prefix="hdrid_")


def gate(model, text):
    p = os.path.join(tmp, model + ".patch")
    open(p, "w", newline="\n").write(text)
    return co.check(model, p)


res = {m: gate(m, overlay(s)) for m, s in STEMS.items() if m != "RT-BE96U"}
check("overlay gate: a correct WebP overlay passes for each of the eight sibling models", not any(res.values()),
      {m: r for m, r in res.items() if r})
r = gate("GT-BE98", overlay("GT-BE98", page_stem="RT-BE88U"))
check("overlay gate: pages that name another model's header are refused", any("foreign-banner" in x for x in r), r)
r = gate("GT-BE98", overlay("RT-BE88U"))
check("overlay gate: an overlay that installs another model's header pair is refused", bool(r), r)
r = gate("GT-BE98", overlay("GT-BE98", extra=True))
check("overlay gate: a change in a header page that is not a header-name swap is refused",
      any("NOT banner references" in x for x in r), r)
r = gate("GT-BE98", overlay("GT-BE98", ext="png", canon_ext="png"))
check("overlay gate: an overlay still in the old format is read by the same rules (an older rung's overlay)", not r, r)
shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- the port classifier
pp = rd(os.path.join(BS, "_port_protect.sh"))
check("port: both header formats are per-model files (never synced from canon)",
      r"_REAPER_Header(_anim)?\.(png|webp|mp4)$)'" in pp)
m = re.search(r"pp_norm_banner\(\)\{ sed -E '([^']+)'; \}", pp)
sed = shutil.which("sed")
if m and sed:
    def norm(line):
        return subprocess.run([sed, "-E", m.group(1)], input=line, stdout=subprocess.PIPE, universal_newlines=True).stdout
    a = norm('<img src="images/RT-96U_REAPER_Header_anim.webp"><img src="/images/RT-96U_REAPER_Header.webp">\n')
    b = norm('<img src="images/GT-BE98P_REAPER_Header_anim.webp"><img src="/images/GT-BE98P_REAPER_Header.webp">\n')
    c = norm('<img src="images/GT-BE98P_REAPER_Header_anim.webp"><img src="/images/GT-BE98P_REAPER_Header.webp"> extra\n')
    check("port: a page that differs from canon's only by the header name compares equal; any other change does not",
          a == b and "REAPER_Header" not in a and a != c, (a, b, c))
else:
    check("port: the header-name normaliser is found", bool(m))

print()
if fails:
    print("%d check(s) FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
