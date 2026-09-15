#!/usr/bin/env python3
"""Parse-check the inline JavaScript of a Reaper .asp page.

WHY THIS EXISTS. A Reaper page is not valid JavaScript on its own: it carries
`<% ejs %>` calls and `<#TOKEN#>` dictionary placeholders that httpd resolves at
serve time. So a plain parser cannot read one, and a hand edit that unbalances a
brace is not caught by any existing gate - it ships, and the page dies in the
browser with the whole card blank. This stubs both kinds of markup the way the
server would and then runs a REAL parser over the result.

A real parser, deliberately: an earlier version of this script tried to track
strings and comments with a hand-rolled scanner and reported both an edited and
an untouched page as broken, because JS regex literals (/\\./g) look like comment
starts and comments contain apostrophes. A brace counter cannot read JavaScript.

Usage:  jscheck.py <page.asp> [more.asp ...]
Exit:   0 = every page parses, 1 = at least one does not, 77 = no JS engine.
"""
import io, os, re, shutil, subprocess, sys, tempfile

NODE = os.environ.get("REAPER_NODE") or shutil.which("node")
if not NODE:
    for c in ("/mnt/c/Users/natha/AppData/Roaming/VSC/node-v24.18.0-win-x64/node.exe",
              "C:/Users/natha/AppData/Roaming/VSC/node-v24.18.0-win-x64/node.exe"):
        if os.path.exists(c):
            NODE = c
            break
if not NODE:
    print("jscheck: no node on PATH (set REAPER_NODE) - skipped")
    sys.exit(77)

def check(path):
    s = io.open(path, encoding="utf-8", errors="replace").read()
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", s, re.S | re.I)
    if not blocks:
        print("ok   %s (no inline script)" % os.path.basename(path))
        return True
    js = "\n;\n".join(blocks)
    # <% ... %> and <# ... #> always sit INSIDE a quoted string or an attribute in
    # these pages, so a bare word is a faithful stand-in for what httpd emits.
    js = re.sub(r"<%[^%]*%>", "STUB", js)
    js = re.sub(r"<#[^#>]*#>", "STUB", js)
    if "<%" in js or "<#" in js:
        print("FAIL %s: unstubbed template markup remains" % os.path.basename(path))
        return False
    fd, tmp = tempfile.mkstemp(suffix=".js")
    os.close(fd)
    try:
        io.open(tmp, "w", encoding="utf-8").write(js)
        # The build runs in WSL while the only JS engine on this machine is the
        # WINDOWS node.exe, which cannot resolve a Linux path - it reported
        # MODULE_NOT_FOUND, which looks exactly like a parse failure. Hand it the
        # UNC form of the same file instead.
        arg = tmp
        if NODE.lower().endswith(".exe") and not sys.platform.startswith("win"):
            try:
                arg = subprocess.run(["wslpath", "-w", tmp], capture_output=True,
                                     text=True, check=True).stdout.strip() or tmp
            except Exception:
                pass
        p = subprocess.run([NODE, "--check", arg], capture_output=True, text=True)
        if p.returncode == 0:
            print("ok   %s (%d block(s), %d lines)" % (os.path.basename(path), len(blocks), js.count("\n") + 1))
            return True
        print("FAIL %s:\n%s" % (os.path.basename(path), (p.stdout + p.stderr).strip()[:2000]))
        return False
    finally:
        os.unlink(tmp)

ok = True
for a in sys.argv[1:]:
    ok = check(a) and ok
sys.exit(0 if ok else 1)
