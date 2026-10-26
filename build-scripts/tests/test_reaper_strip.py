#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reaper_strip.py - the build's comment strip for Reaper's own pages, scripts and stylesheets (review 2026-10-24, Q-C2-10).

WHY THIS EXISTS. The vendor minifier never removed /* */ or // comments from scripts (its strip_comments() hook returns
the text unchanged), so Reaper's commented sources shipped as they are. tools/reaper_strip.py removes them from the
STAGED copy at build time. A comment stripper that misreads a string, a template literal or a regex literal corrupts
the page silently, so this test proves on the whole source tree that the output means exactly what the input did.

WHAT IT DOES. Copies every file reaper_files() would strip, runs the stripper, and checks: (1) no file was left
unstripped by a lexer error; (2) stripping again changes nothing; (3) with node and acorn on the host (the Windows
side), every inline script and every .js file tokenizes to exactly the same token stream before and after (ej tags and
dictionary tokens replaced by the same placeholders in both), so only comments and blank lines went; stylesheets
compare equal after removing comments and whitespace; (4) every www verify marker for a stripped file still holds on
the stripped copy (positive markers present at their count, negative ones absent); (5) the Makefile runs it right
after the vendor compress step. Exit 0 pass, 1 fail, 77 skipped.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
TOOL = os.path.join(SRC, "tools", "reaper_strip.py") if SRC else ""
if not TOOL or not os.path.isfile(TOOL):
    print("SKIP: no router source tree with tools/reaper_strip.py"); sys.exit(77)
HERE = os.path.dirname(os.path.abspath(__file__))
MARKERS = os.path.join(HERE, "..", "verify_markers.txt")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))

sys.path.insert(0, os.path.dirname(TOOL))
import reaper_strip as RS   # noqa: E402

www = os.path.join(SRC, "www")
files = RS.reaper_files(www)
check("the stripper finds Reaper's pages, scripts and stylesheets (and no stock file)",
      len(files) >= 50 and all(os.path.basename(f).lower().startswith(("reaper", "main_reaperdash", "rp.", "menu.", "internet_speed_reaper"))
                               for f in files), [os.path.basename(f) for f in files][:80])

work = tempfile.mkdtemp(prefix="rstrip_")
try:
    pairs, errors = [], []
    before = after = 0
    for f in files:
        src = open(f, encoding="utf-8", errors="surrogateescape", newline="").read()
        try:
            out = RS.strip_text(f, src)
        except RS.LexError as e:
            errors.append("%s: %s" % (os.path.basename(f), e)); continue
        pairs.append((f, src, out))
        before += len(src.encode("utf-8", "surrogateescape")); after += len(out.encode("utf-8", "surrogateescape"))
    check("every file lexes to the end (none would be left unstripped)", not errors, errors)
    print("     %d files: %d -> %d bytes (%d removed, %.0f%%)" % (len(pairs), before, after, before - after, 100.0 * (before - after) / max(before, 1)))
    check("the strip removes a real amount (> 100 KB of comment across Reaper's www)", before - after > 100000, before - after)
    check("stripping twice changes nothing (idempotent)", all(RS.strip_text(f, o) == o for f, s, o in pairs),
          [os.path.basename(f) for f, s, o in pairs if RS.strip_text(f, o) != o][:5])
    # a dictionary token or ej tag may only go with a comment that held it - never appear, never multiply
    tok_bad = [os.path.basename(f) for f, s, o in pairs
               if not set(re.findall(r"<#[A-Za-z0-9_]+#>", o)) <= set(re.findall(r"<#[A-Za-z0-9_]+#>", s))
               or len(re.findall(r"<%", o)) > len(re.findall(r"<%", s))]
    check("no dictionary token or ej tag appears that the source did not have", not tok_bad, tok_bad)

    # (3) tokens, with node + acorn when the host has them
    node = shutil.which("node")
    acorn = os.environ.get("ACORN_DIR") or next((p for p in (
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "VSC", "playwright-automation", "node_modules", "acorn"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "VSC", "QA_Testcase_Helper", "node_modules", "acorn")) if os.path.isdir(p)), "")
    if node and acorn:
        jobs = []
        for f, s, o in pairs:
            ext = os.path.splitext(f)[1].lower()
            if ext == ".css":
                continue
            if ext == ".js":
                a_blocks, b_blocks = [s], [o]
            else:
                a_blocks = [m.group(2) for m in RS.SCRIPT_RE.finditer(s) if RS.js_block_ok(m.group(1))]
                b_blocks = [m.group(2) for m in RS.SCRIPT_RE.finditer(o) if RS.js_block_ok(m.group(1))]
            jobs.append({"f": os.path.basename(f), "a": a_blocks, "b": b_blocks})
        jp = os.path.join(work, "jobs.json"); json.dump(jobs, open(jp, "w", encoding="utf-8"))
        js = r'''
const acorn = require(process.argv[2]); const fs = require("fs");
const jobs = JSON.parse(fs.readFileSync(process.argv[3], "utf8")); const bad = []; let n = 0, skipped = 0;
// the same placeholders on both sides: an ej tag is a number, a dictionary token outside quotes a name
const prep = s => s.replace(/<%[\s\S]*?%>/g, "0").replace(/<#[A-Za-z0-9_]+#>/g, "TOK");
function toks(s) { const out = []; for (const t of acorn.tokenizer(prep(s), {ecmaVersion: "latest", allowHashBang: true}))
  out.push(t.type.label + ":" + (t.value === undefined ? "" : (t.value instanceof RegExp ? String(t.value) : JSON.stringify(t.value)))); return out; }
for (const j of jobs) {
  if (j.a.length !== j.b.length) { bad.push(j.f + ": script count " + j.a.length + " vs " + j.b.length); continue; }
  for (let i = 0; i < j.a.length; i++) {
    let ta; try { ta = toks(j.a[i]); } catch (e) { skipped++; continue; }   // a block acorn cannot read even before
    let tb; try { tb = toks(j.b[i]); } catch (e) { bad.push(j.f + " #" + i + ": stripped copy does not tokenize: " + e.message); continue; }
    n++;
    if (ta.length !== tb.length || ta.some((x, k) => x !== tb[k])) {
      let k = 0; while (k < ta.length && ta[k] === tb[k]) k++;
      bad.push(j.f + " #" + i + ": token " + k + " " + ta[k] + " -> " + tb[k]);
    }
  }
}
console.log(JSON.stringify({n, skipped, bad}));
'''
        sp = os.path.join(work, "tok.js"); open(sp, "w").write(js)
        r = subprocess.run([node, sp, acorn, jp], capture_output=True, text=True)
        try:
            res = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            res = {"n": 0, "skipped": 0, "bad": [r.stderr[-500:]]}
        print("     acorn: %d script(s) compared, %d not tokenizable before stripping (skipped)" % (res["n"], res["skipped"]))
        check("every stripped script has exactly the original's tokens (acorn) - only comments and blank lines went",
              res["n"] > 50 and not res["bad"], res["bad"][:10])
    else:
        print("note: node + acorn not found - the token comparison runs on the Windows side")
    # stylesheets: equal once comments and whitespace are gone
    def css_norm(t):
        return re.sub(r"\s+", "", re.sub(r"/\*[\s\S]*?\*/", "", t))
    css_bad = []
    for f, s, o in pairs:
        if f.endswith(".css"):
            if css_norm(s) != css_norm(o): css_bad.append(os.path.basename(f))
        elif not f.endswith(".js"):
            for a, b in zip(RS.STYLE_RE.finditer(s), RS.STYLE_RE.finditer(o)):
                if css_norm(a.group(2)) != css_norm(b.group(2)): css_bad.append(os.path.basename(f)); break
    check("every stylesheet is the same once comments and whitespace are removed", not css_bad, css_bad)

    # (4) the verify markers judge the strip's output the way they judged its input. (The source still carries the
    # HTML comments the vendor minifier removes, so a marker is compared before/after, not judged absolutely.)
    rel = lambda f: os.path.relpath(f, SRC).replace(os.sep, "/")
    orig = {rel(f): s for f, s, o in pairs}
    stripped = {rel(f): o for f, s, o in pairs}
    def holds(line, body):
        parts = line.split("|")
        if parts[1].startswith("!"):
            return parts[1][1:] not in body
        want = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        return sum(1 for l in body.split("\n") if parts[1] in l) >= want
    mbad = []
    for line in open(MARKERS, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#") or "|" not in line: continue
        path = line.split("|")[0]
        if path not in stripped: continue
        if holds(line, orig[path]) and not holds(line, stripped[path]):
            mbad.append(line)
    check("no www verify marker that holds on the source stops holding after the strip (a marker never quotes a comment)", not mbad, mbad[:15])
finally:
    shutil.rmtree(work, ignore_errors=True)

mk = open(os.path.join(SRC, "www", "Makefile"), encoding="utf-8", errors="replace").read()
i_c = mk.find("sh $(SRCBASE)/image/compress.sh"); i_s = mk.find("tools/reaper_strip.py")
check("www/Makefile runs the strip after the vendor compress step, on the staged www, never failing the build",
      0 < i_c < i_s and "python3 $(TOP)/tools/reaper_strip.py $(INSTALLDIR)/www" in mk and "|| true" in mk[i_s:i_s + 200])

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
