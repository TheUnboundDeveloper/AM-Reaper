#!/usr/bin/env python3
"""reaper_static_checks.py <router-src-dir>

Build gate: five static checks over the Reaper SOURCE tree (release/src/router),
promoting the ad-hoc checks the team runs by hand into one reaper_verify gate.
The argument is release/src/router; www is <arg>/www and the inject file is
<arg>/httpd/reaper_inject.c. Runs on SOURCE (real dict tokens, un-minified .asp),
never the staged fs.

Exit 0 = every check passed, 1 = one or more failed, 2 = bad usage.
Prints one summary line per check and a final tally.

The five checks
  1. dict-lockstep      Every <www>/*.dict EXCEPT temp.dict has an identical line
                        count (the `wc -l *.dict | sort -u` check). Fail names the
                        outliers and their counts.
  2. www-ascii          The Reaper-authored www pages must be ASCII-only: the
                        minify step strips non-ASCII from .asp/.js and would
                        silently corrupt a non-ASCII literal. Scope = the SAME
                        page set as reaper_langcheck.py's OUR[] (parsed from the
                        langcheck script in THIS directory, so the two tools
                        cannot drift). .dict files (intentionally non-ASCII) and
                        stock ASUS pages (UTF-8 BOM) are out of scope. Fail names
                        file:line of the first offending byte per file.
  3. control-bytes      No forbidden control byte (0x00-0x08, 0x0B, 0x0C,
                        0x0E-0x1F: everything below 0x20 except TAB/LF/CR) in any
                        OUR www page or any *.dict. Fail names file:line:offset and
                        the byte in hex.
  4. js-brace-parity    For each OUR page, every inline <script> block that is NOT
                        src=-loaded must have balanced {} () []. Lightweight stand-in
                        for the by-hand node-vm parse. See balance_js() for the
                        strip method. Fail names the file/block and the depth at EOF.
  5. macro-continuation In <httpd>/reaper_inject.c, a comment line that sits inside
                        a multi-line #define but lost its trailing backslash
                        silently truncates the macro (line-splicing happens before
                        comment removal). Fail names file:line.
"""
import os
import re
import sys


# ---------------------------------------------------------------------------
# OUR page set: parsed from reaper_langcheck.py in THIS script's directory, so
# reaper_static_checks and reaper_langcheck can never cover a different page set.
# ---------------------------------------------------------------------------
def load_our(script_dir):
    lc = os.path.join(script_dir, "reaper_langcheck.py")
    src = open(lc, "r", encoding="utf-8", errors="replace").read()
    m = re.search(r"\bOUR\s*=\s*\[(.*?)\]", src, re.S)
    if not m:
        raise RuntimeError("could not find OUR = [...] in %s" % lc)
    # pull every quoted literal out of the list body (comments in it are ignored)
    return re.findall(r"""['"]([^'"]+\.(?:asp|htm|html))['"]""", m.group(1))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def line_of_offset(data, off):
    """1-based line number of byte offset off in bytes `data`."""
    return data.count(b"\n", 0, off) + 1


CTRL = set(range(0x00, 0x09)) | {0x0B, 0x0C} | set(range(0x0E, 0x20))  # not TAB/LF/CR


# Keywords after which a `/` begins a regex literal, not a division.
_REGEX_KW = frozenset((
    "return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
    "do", "else", "case", "yield", "throw", "await",
))
# Single chars after which a `/` begins a regex (expression / statement context).
_REGEX_PUNCT = set("(,=:[!&|?{};~^%*+-<>")


def _regex_context(js, i):
    """True if a `/` at index i begins a regex literal rather than division.

    Decided by the preceding significant token (whitespace skipped): the start of
    input, an operator/opening-punctuator, or one of the expression-context
    keywords (return, typeof, ...) all put a `/` in regex position; an identifier,
    number, string/regex close, or a closing ) ] } is a value, so `/` divides.
    """
    k = i - 1
    while k >= 0 and js[k] in " \t\r\n":
        k -= 1
    if k < 0:
        return True
    ch = js[k]
    if ch in _REGEX_PUNCT:
        return True
    if ch.isalnum() or ch in "_$":
        e = k
        while k >= 0 and (js[k].isalnum() or js[k] in "_$"):
            k -= 1
        word = js[k + 1:e + 1]
        return word in _REGEX_KW  # a plain identifier/number -> division
    return False  # ) ] } . " ' ` etc. -> value context -> division


def balance_js(js):
    """Return the net bracket-balance report for a chunk of inline JS.

    Method (conservative, documented): a single left-to-right scan removes the
    spans in which brackets are DATA rather than structure -- line comments
    (// .. EOL), block comments (/* .. */), single/double-quoted strings,
    template literals (`..`, whose ${ } are skipped wholesale with the span), and
    regex literals. Regex vs. divide is disambiguated by the preceding significant
    token (see _regex_context): start-of-input, an operator/opening punctuator, or
    an expression-context keyword (return, typeof, ...) begins a regex; an
    identifier / number / closing bracket means division. Inside a regex a
    character class [ .. ] is tracked so a `/` within it does not end it. Only the
    characters left after those spans are removed are counted, so a bracket inside
    any string, comment or regex can never unbalance the result.

    Returns (ok, detail) where detail names the first offending bracket or the
    residual stack depth at EOF.
    """
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    opens = set("([{")
    i = 0
    n = len(js)
    while i < n:
        c = js[i]
        nxt = js[i + 1] if i + 1 < n else ""
        # line comment
        if c == "/" and nxt == "/":
            j = js.find("\n", i)
            i = n if j < 0 else j
            continue
        # block comment
        if c == "/" and nxt == "*":
            j = js.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        # string / template literal
        if c in "'\"`":
            quote = c
            i += 1
            while i < n:
                if js[i] == "\\":
                    i += 2
                    continue
                if js[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        # regex literal (context-sensitive on the preceding token)
        if c == "/" and _regex_context(js, i):
            i += 1
            in_class = False
            while i < n:
                ch = js[i]
                if ch == "\\":
                    i += 2
                    continue
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    i += 1
                    break
                elif ch == "\n":
                    break  # unterminated -> bail out of the regex scan
                i += 1
            continue
        # structural brackets
        if c in opens:
            stack.append((c, i))
        elif c in pairs:
            if not stack or stack[-1][0] != pairs[c]:
                return (False, "unmatched '%s' at index %d" % (c, i))
            stack.pop()
        i += 1
    if stack:
        kinds = "".join(s[0] for s in stack)
        return (False, "%d unclosed bracket(s) at EOF: %s" % (len(stack), kinds))
    return (True, "balanced")


SCRIPT_RE = re.compile(r"<script([^>]*)>(.*?)</script\s*>", re.S | re.I)


# ---------------------------------------------------------------------------
# the five checks -- each returns (ok: bool, summary: str, details: list[str])
# ---------------------------------------------------------------------------
def check_dict_lockstep(www):
    dicts = sorted(
        f for f in os.listdir(www)
        if f.endswith(".dict") and f != "temp.dict"
    ) if os.path.isdir(www) else []
    if not dicts:
        return (True, "no *.dict found (excluding temp.dict) -- nothing to check", [])
    counts = {}
    for d in dicts:
        data = open(os.path.join(www, d), "rb").read()
        counts[d] = data.count(b"\n")
    uniq = sorted(set(counts.values()))
    if len(uniq) <= 1:
        return (True, "%d dicts lockstep at %d lines" % (len(dicts), uniq[0]), [])
    # majority is the intended count; everything else is an outlier
    from collections import Counter
    majority = Counter(counts.values()).most_common(1)[0][0]
    outliers = ["%s=%d" % (d, c) for d, c in sorted(counts.items()) if c != majority]
    return (
        False,
        "dict line counts DIFFER (majority=%d): %s" % (majority, " ".join(outliers)),
        outliers,
    )


def check_www_ascii(www, our):
    details = []
    checked = 0
    for f in our:
        p = os.path.join(www, f)
        if not os.path.isfile(p):
            continue
        checked += 1
        data = open(p, "rb").read()
        for off, b in enumerate(data):
            if b > 0x7F:
                details.append("%s:%d first non-ASCII byte 0x%02X" %
                               (f, line_of_offset(data, off), b))
                break
    if details:
        return (False, "%d Reaper page(s) contain non-ASCII bytes" % len(details), details)
    return (True, "%d Reaper www page(s) are ASCII-only" % checked, [])


def check_control_bytes(www, our):
    details = []
    files = []
    for f in our:
        p = os.path.join(www, f)
        if os.path.isfile(p):
            files.append((f, p))
    if os.path.isdir(www):
        for d in sorted(os.listdir(www)):
            if d.endswith(".dict"):
                files.append((d, os.path.join(www, d)))
    for f, p in files:
        data = open(p, "rb").read()
        for off, b in enumerate(data):
            if b in CTRL:
                details.append("%s:%d:%d control byte 0x%02X" %
                               (f, line_of_offset(data, off), off, b))
                break
    if details:
        return (False, "%d file(s) contain forbidden control bytes" % len(details), details)
    return (True, "%d file(s) clean of control bytes" % len(files), [])


def check_js_parity(www, our):
    details = []
    pages = 0
    blocks = 0
    for f in our:
        p = os.path.join(www, f)
        if not os.path.isfile(p):
            continue
        pages += 1
        text = open(p, "r", encoding="utf-8", errors="replace").read()
        idx = 0
        for m in SCRIPT_RE.finditer(text):
            attrs, body = m.group(1), m.group(2)
            idx += 1
            if re.search(r"\bsrc\s*=", attrs, re.I):
                continue  # externally-loaded script: no inline body to balance
            blocks += 1
            ok, detail = balance_js(body)
            if not ok:
                details.append("%s block#%d: %s" % (f, idx, detail))
    if details:
        return (False, "%d inline script block(s) unbalanced" % len(details), details)
    return (True, "%d inline block(s) balanced across %d page(s)" % (blocks, pages), [])


def _looks_like_comment(s):
    s = s.strip()
    if s.startswith("/*") or s.startswith("*") or s.startswith("//"):
        return True
    if s.endswith("*/"):
        return True
    return False


def check_macro_continuation(inject_c):
    if not os.path.isfile(inject_c):
        return (True, "reaper_inject.c not present -- skipped", [])
    details = []
    lines = open(inject_c, "r", encoding="utf-8", errors="replace").read().split("\n")
    in_macro = False
    define_re = re.compile(r"^\s*#\s*define\b")
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\r")
        ends_bs = line.endswith("\\")
        if in_macro:
            if not ends_bs:
                # terminating line of the macro. If it looks like a comment, it
                # almost certainly lost its continuation backslash and silently
                # truncated the macro.
                if _looks_like_comment(line):
                    details.append("%s:%d comment line inside a #define lost its "
                                   "trailing backslash -- macro truncated here" %
                                   (os.path.basename(inject_c), n))
                in_macro = False
            # else: still inside the macro, keep going
        elif define_re.match(line) and ends_bs:
            in_macro = True
    if details:
        return (False, "%d dropped-backslash comment(s) inside a macro" % len(details), details)
    return (True, "all multi-line #define macros continue cleanly", [])


# ---------------------------------------------------------------------------
def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: reaper_static_checks.py <router-src-dir>\n")
        return 2
    router = argv[1]
    if not os.path.isdir(router):
        sys.stderr.write("error: not a directory: %s\n" % router)
        return 2
    www = os.path.join(router, "www")
    inject_c = os.path.join(router, "httpd", "reaper_inject.c")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        our = load_our(script_dir)
    except Exception as e:
        sys.stderr.write("error: %s\n" % e)
        return 2

    checks = [
        ("dict-lockstep",      check_dict_lockstep(www)),
        ("www-ascii",          check_www_ascii(www, our)),
        ("control-bytes",      check_control_bytes(www, our)),
        ("js-brace-parity",    check_js_parity(www, our)),
        ("macro-continuation", check_macro_continuation(inject_c)),
    ]

    npass = 0
    nfail = 0
    for name, (ok, summary, details) in checks:
        tag = "PASS" if ok else "FAIL"
        print("[%s] %-19s %s" % (tag, name, summary))
        if not ok:
            for d in details[:50]:
                print("        %s" % d)
        if ok:
            npass += 1
        else:
            nfail += 1
    print("reaper_static_checks: %d pass, %d fail (of %d checks)" %
          (npass, nfail, len(checks)))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
