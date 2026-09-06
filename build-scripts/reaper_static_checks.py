#!/usr/bin/env python3
"""reaper_static_checks.py <router-src-dir>

Build gate: eight static checks over the Reaper SOURCE tree (release/src/router),
promoting the ad-hoc checks the team runs by hand into one reaper_verify gate.
The argument is release/src/router; www is <arg>/www and the inject file is
<arg>/httpd/reaper_inject.c. Runs on SOURCE (real dict tokens, un-minified .asp),
never the staged fs.

Exit 0 = every check passed, 1 = one or more failed, 2 = bad usage.
Prints one summary line per check and a final tally.

The eight checks
  8. pbr-fwmark-regex   The `fwmark 0x[0-9a-fA-F]+/0x0*[fF]0000` rule-form regex
                        is one literal that lives at FIVE consumer sites
                        (reaper_pbr.c x3 teardown/expect, rwatch.c heal count,
                        reaper_diag live count) and must stay byte-identical;
                        and the PRODUCER (`fwmark 0x%X0000/$MASK`, PPBR_MASK)
                        must render a string every one of them matches, in
                        both the written and the iproute2-printed mask form.
                        Change the mask nibble and every consumer silently
                        counts 0 with a green build.
  6. pbr-reassert       Every add_multi_routes() CALL in rc/*.c is followed by a
                        reaper_pbr_reassert() within REASSERT_LOOKAHEAD lines.
                        That blob opens with an unconditional IPv4 `ip rule
                        flush`; without the re-assert policy routing is left
                        FAIL-OPEN (marks set, no rule to select on, traffic
                        pinned to a tunnel egresses the WAN). A C call site
                        leaves no string in the binary, so verify_markers.txt
                        cannot express this. vpnc.c/vpnc_legacy.c are excluded:
                        their call sites are compiled out on CONFIG_BCMWL5.
  7. warden-log-prefix  Every --log-prefix rwarden.c emits is accepted by
                        fw_line_is_fwlog() in httpd/web.c (the sole filter on the
                        GUI drops viewer) and is known to others/reaper_diag.
                        A producer/consumer contract across files: both halves
                        stay valid C when it breaks, so the build stays green.
                        This is the shape that hid the v2.4.2 outbound-logging
                        regression until 2026-09-01.

  1. dict-lockstep     Every <www>/*.dict EXCEPT temp.dict has an identical line
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
# 6. pbr-reassert: every add_multi_routes() CALL must be followed by a
#    reaper_pbr_reassert(). A C call site leaves no string in the binary, so
#    verify_markers.txt structurally cannot express this - it has to be here.
# ---------------------------------------------------------------------------
# add_multi_routes() is the closed ASUS blob that opens with an unconditional
# IPv4 `ip rule flush`. That wipes Reaper's whole 9000-9115 policy-routing band
# while leaving the REAPER_PBR mangle chain intact, so the marks keep being set
# with no rule left to select on and IPv4 traffic pinned to a tunnel egresses the
# WAN in the clear (a BLOCK rule, realised solely as `prohibit`, stops blocking).
# Upstream re-asserts its own killswitch after every call for the same reason.
# Look-ahead is generous because the wan_up() site carries a long comment.
REASSERT_LOOKAHEAD = 25
# vpnc.c / vpnc_legacy.c call it inside `#if !defined(CONFIG_BCMWL5) &&
# defined(RTCONFIG_DUALWAN)`. CONFIG_BCMWL5 is defined on every model this tree
# builds, so those two are compiled OUT and are deliberately not required to
# re-assert. If a model ever builds without CONFIG_BCMWL5, drop this exclusion.
REASSERT_EXCLUDED = ("vpnc.c", "vpnc_legacy.c")


def _is_comment_line(line):
    s = line.strip()
    return s.startswith("/*") or s.startswith("*") or s.startswith("//")


def check_pbr_reassert(router):
    rc_dir = os.path.join(router, "rc")
    if not os.path.isdir(rc_dir):
        return (True, "rc/ not present -- skipped", [])
    call_re = re.compile(r"\badd_multi_routes\s*\(")
    def_re = re.compile(r"^\s*(?:static\s+)?(?:int|void)\s+add_multi_routes\s*\(")
    details = []
    nchecked = 0
    nexcluded = 0
    for fn in sorted(os.listdir(rc_dir)):
        if not fn.endswith(".c"):
            continue
        path = os.path.join(rc_dir, fn)
        try:
            lines = open(path, "r", encoding="utf-8", errors="replace").read().split("\n")
        except OSError:
            continue
        for i, line in enumerate(lines):
            if not call_re.search(line):
                continue
            if def_re.match(line) or _is_comment_line(line):
                continue
            if fn in REASSERT_EXCLUDED:
                nexcluded += 1
                continue
            nchecked += 1
            window = "\n".join(lines[i:i + REASSERT_LOOKAHEAD])
            if "reaper_pbr_reassert()" not in window:
                details.append("%s:%d add_multi_routes() call with no "
                               "reaper_pbr_reassert() within %d lines -- the ip "
                               "rule flush would leave policy routing FAIL-OPEN"
                               % (fn, i + 1, REASSERT_LOOKAHEAD))
    if details:
        return (False, "%d unguarded add_multi_routes() call site(s)" % len(details), details)
    if nchecked == 0:
        # the call sites moving wholesale is itself a change worth stopping on
        return (False, "no add_multi_routes() call sites found -- check moved or "
                       "renamed; re-verify the flush is still guarded", [])
    return (True, "%d add_multi_routes() call site(s) re-assert PBR (%d compiled-out "
                  "site(s) excluded)" % (nchecked, nexcluded), [])


# ---------------------------------------------------------------------------
# 7. warden-log-prefix: every LOG prefix rwarden.c emits must be accepted by the
#    GUI drops viewer's filter in web.c, and known to the diagnostics report.
# ---------------------------------------------------------------------------
# A producer/consumer contract across two files: each half is individually
# correct C, so a green build and a clean marker pass are both blind to a break.
# This is the class that hid the v2.4.2 regression for six months of rungs --
# fw_line_is_fwlog() tested for "REAPER-WARDEN " WITH a trailing space, which can
# never match "REAPER-WARDEN-OUT " (the next character is '-'), so every outbound
# Warden block was discarded server-side and the page looked like outbound
# logging had been turned off.
def check_warden_log_prefixes(router):
    rwarden = os.path.join(router, "rc", "rwarden.c")
    web_c = os.path.join(router, "httpd", "web.c")
    diag = os.path.join(router, "others", "reaper_diag")
    if not os.path.isfile(rwarden) or not os.path.isfile(web_c):
        return (True, "rwarden.c or web.c not present -- skipped", [])

    src = open(rwarden, "r", encoding="utf-8", errors="replace").read()
    # fprintf writes them escaped:  --log-prefix \"REAPER-WARDEN-OUT \"
    prefixes = sorted(set(re.findall(r'--log-prefix\s+\\"([A-Z0-9][A-Z0-9-]*)\s+\\"', src)))
    if not prefixes:
        return (False, "no --log-prefix emissions found in rwarden.c -- the "
                       "extraction pattern no longer matches; fix this check "
                       "before trusting it", [])

    web = open(web_c, "r", encoding="utf-8", errors="replace").read()
    m = re.search(r"fw_line_is_fwlog\s*\([^)]*\)\s*\{(.*?)\n\}", web, re.S)
    if not m:
        return (False, "could not locate fw_line_is_fwlog() in web.c -- fix this "
                       "check before trusting it", [])
    accepted = re.findall(r'strstr\s*\(\s*k\s*,\s*"([^"]+)"\s*\)', m.group(1))
    if not accepted:
        return (False, "fw_line_is_fwlog() exposes no strstr literals -- fix this "
                       "check before trusting it", [])

    diag_src = ""
    if os.path.isfile(diag):
        diag_src = open(diag, "r", encoding="utf-8", errors="replace").read()

    details = []
    for p in prefixes:
        emitted = p + " "          # the literal that reaches syslog
        if not any(emitted.startswith(lit) for lit in accepted):
            details.append('web.c fw_line_is_fwlog() drops "%s": no strstr literal '
                           "is a prefix of it, so the drops viewer discards every "
                           "one of these lines" % emitted)
        if diag_src and p not in diag_src:
            details.append('others/reaper_diag does not mention "%s" -- the '
                           "sanitized report will not count these blocks" % p)
    if details:
        return (False, "%d Warden LOG prefix contract break(s)" % len(details), details)
    return (True, "all %d Warden LOG prefix(es) accepted by the drops viewer%s"
                  % (len(prefixes), " and the diag report" if diag_src else ""), [])


# ---------------------------------------------------------------------------
# 8. pbr-fwmark-regex: the rule-form regex is a producer/consumer contract
#    across three files. reaper_pbr.c WRITES `fwmark 0x<code>0000/$MASK`, and
#    the same file (teardown + expect_rules), rwatch.c (the ip-rule heal's live
#    count) and others/reaper_diag (the FINDINGS live count) all READ it back
#    with one grep -E literal. iproute2 prints the mask with leading zeros
#    stripped (0xf0000, not 0x000F0000), which is why the literal carries
#    `0x0*[fF]0000`. If the literal drifts at one site, or the mask nibble
#    moves, that site counts 0 on a healthy box: the heal re-runs forever or the
#    diag WARNs about a fail-open that is not there - with a green build.
# ---------------------------------------------------------------------------
FWMARK_SITES = (("rc/reaper_pbr.c", 3), ("rc/rwatch.c", 1), ("others/reaper_diag", 1))
FWMARK_LITERAL_RE = re.compile(r"fwmark 0x\[[^\]]+\]\+/0x[0-9A-Fa-f*\[\]]+")
PPBR_MASK_RE = re.compile(r'#define\s+PPBR_MASK\s+"(0x[0-9A-Fa-f]+)"')


def check_pbr_fwmark_regex(router):
    details = []
    found = {}
    for rel, minc in FWMARK_SITES:
        path = os.path.join(router, rel)
        if not os.path.isfile(path):
            return (True, "%s not present -- skipped" % rel, [])
        src = open(path, "r", encoding="utf-8", errors="replace").read()
        lits = FWMARK_LITERAL_RE.findall(src)
        if len(lits) < minc:
            details.append("%s: %d fwmark rule-form literal(s), expected >= %d -- a "
                           "consumer site moved or was rewritten" % (rel, len(lits), minc))
        for l in lits:
            found.setdefault(l, []).append(rel)
    if len(found) > 1:
        details.append("the literal differs between sites: %s" %
                       "; ".join("%r in %s" % (k, ",".join(sorted(set(v)))) for k, v in found.items()))
    if details:
        return (False, "fwmark rule-form regex contract broken", details)
    if not found:
        return (False, "no fwmark rule-form literal found anywhere -- check moved or renamed", [])
    literal = next(iter(found))
    try:
        rx = re.compile(literal)
    except re.error as e:
        return (False, "the literal is not a valid regex: %s" % e, [literal])
    pbr = open(os.path.join(router, "rc/reaper_pbr.c"), "r", encoding="utf-8", errors="replace").read()
    m = PPBR_MASK_RE.search(pbr)
    if not m:
        return (False, "PPBR_MASK define not found in rc/reaper_pbr.c", [])
    mask = m.group(1)
    if "fwmark 0x%X0000/$MASK" not in pbr:
        return (False, "producer format `fwmark 0x%X0000/$MASK` not found in rc/reaper_pbr.c", [])
    # the producer format hardcodes the code into bits 16-19 (`0x%X0000`), so
    # the mask MUST be exactly those bits - a moved nibble is a silent miss at
    # every consumer, and the regex alone cannot see it (it is unanchored, so
    # `0x0*[fF]0000` happily matches a PREFIX of 0x00F00000; proven 2026-09-02)
    if int(mask, 16) != 0xF0000:
        return (False, "PPBR_MASK is %s but the producer writes the code at bits 16-19 "
                       "(0xF0000) -- every consumer would count 0" % mask, [])
    # what the producer writes, and what `ip rule show` prints back (mask with
    # leading zeros stripped); every consumer must match both WHOLE, for the
    # lowest and highest rule codes
    printed = "0x" + (mask[2:].lstrip("0") or "0")
    for code in (1, 0xF):
        for mk in (mask, printed):
            sample = "fwmark 0x%X0000/%s" % (code, mk)
            if not rx.fullmatch(sample):
                details.append("consumer regex %r does not match producer form %r in full" % (literal, sample))
    if details:
        return (False, "fwmark producer/consumer mismatch", details)
    nsites = sum(len(v) for v in found.values())
    return (True, "one fwmark rule-form literal at %d site(s) in %d file(s); producer "
                  "(mask %s) matches in both forms" % (nsites, len(FWMARK_SITES), mask), [])


# ---------------------------------------------------------------------------
# firstboot-wifi (v3.1.0): the first-boot box must stay wired end to end.
# Reaper_WiFiSetup.asp replaced the stock Wireless page as the banner's Wi-Fi
# target and sets SSID + key on every radio through reaper_wifisetup.cgi, then
# fires the credential apply chained with restart_wireless. Each piece lives in
# a different file (page, web.c, reaper_inject.c, 25 dicts) and any one of them
# regressing silently returns a factory box to the clunky path or, worse, ships
# a CGI that writes a weak auth mode or an unbounded key. Lock the contract:
#   page   : exists, calls the CGI with http_id, uses httpApi.chpass, enforces
#            the 8..63 key bound client-side, fires the exact action_script chain
#   web.c  : the CGI exists, gates BEFORE any nvram write, writes auth_mode_x
#            only as "sae"/"psk2sae", enforces 8..63, turns Smart Connect on,
#            commits, never restarts services itself, registered with do_auth
#   inject : the banner CTA points at the page; the page is in reaper_skip[] and
#            reaper_css_only[] (theme yes, bounce no) and NOT in reaper_banner_only[]
#   dicts  : every pack carries the same RWFS_ set as EN; the page uses only those
# ---------------------------------------------------------------------------
def check_firstboot_wifi(router):
    www = os.path.join(router, "www")
    page_p = os.path.join(www, "Reaper_WiFiSetup.asp")
    web_p = os.path.join(router, "httpd", "web.c")
    inj_p = os.path.join(router, "httpd", "reaper_inject.c")
    bad = []
    if not os.path.isfile(page_p):
        return (False, "www/Reaper_WiFiSetup.asp missing", ["the first-boot box page is not in the tree"])
    page = open(page_p, encoding="utf-8", errors="replace").read()
    for needle, why in [
        ("/reaper_wifisetup.cgi", "page does not call reaper_wifisetup.cgi"),
        ("http_id=", "page does not send http_id to the CGI"),
        ("httpApi.chpass(", "page does not change the login password through httpApi.chpass"),
        ('"saveNvram;restart_chpass;restart_wireless"', "page does not fire the saveNvram;restart_chpass;restart_wireless chain"),
        ('"saveNvram;restart_chpass"', "page has no password-only fallback apply (rule 28)"),
        ('current_page" value="Reaper_WiFiSetup.asp"', "form current_page is not the page itself"),
    ]:
        if needle not in page:
            bad.append(why)
    if not re.search(r"length\s*<\s*8\s*\|\|\s*v\.length\s*>\s*63", page):
        bad.append("page does not enforce the 8..63 Wi-Fi key bound client-side")
    if re.search(r"'[^'\n]*<#[A-Za-z_0-9]+#>[^'\n]*'", page):
        bad.append("a <#token#> sits inside a single-quoted JS string (rule 29)")

    web = open(web_p, encoding="utf-8", errors="replace").read()
    m = re.search(r"\ndo_reaper_wifisetup_cgi\(char \*url, FILE \*stream\)\n\{(.*?)\n\}\n", web, re.S)
    if not m:
        bad.append("web.c has no do_reaper_wifisetup_cgi")
    else:
        body = m.group(1)
        g = body.find("reaper_gate()")
        writes = [x for x in (body.find("nvram_set"), body.find("nvram_pf_set")) if x >= 0]
        first_write = min(writes) if writes else len(body)
        if g < 0 or g > first_write:
            bad.append("CGI does not gate (reaper_gate) before its first nvram write")
        auths = re.findall(r'auth\s*=\s*"([a-z0-9]+)"', body)
        if not auths or any(a not in ("sae", "psk2sae") for a in auths):
            bad.append("CGI auth modes are not limited to sae/psk2sae: %r" % auths)
        if 'nvram_pf_set(prefix, "auth_mode_x", auth)' not in body:
            bad.append("CGI does not write auth_mode_x from the checked auth value")
        if not re.search(r"len\s*<\s*8\s*\|\|\s*len\s*>\s*63", body):
            bad.append("CGI does not enforce the 8..63 key bound")
        if 'nvram_set("smart_connect_x", "1")' not in body:
            bad.append("CGI does not turn Smart Connect on")
        if "nvram_commit()" not in body:
            bad.append("CGI does not commit")
        if "notify_rc(" in body:
            bad.append("CGI restarts services itself (the page must chain the restart behind the password apply)")
    if not re.search(r'\{\s*"reaper_wifisetup\.cgi\*",[^\n]*do_reaper_wifisetup_cgi,\s*do_auth\s*\}', web):
        bad.append("reaper_wifisetup.cgi is not registered in mime_handlers with do_auth")

    inj = open(inj_p, encoding="utf-8", errors="replace").read()
    if 'href=\\"Reaper_WiFiSetup.asp\\"' not in inj:
        bad.append("banner Wi-Fi CTA does not point at Reaper_WiFiSetup.asp")
    if 'href=\\"Advanced_Wireless_Content.asp\\"' in inj:
        bad.append("banner still links the stock Wireless page")
    def in_list(name):
        i = inj.find("static const char *%s[] = {" % name)
        if i < 0:
            return False
        j = inj.find("NULL", i)
        return '"Reaper_WiFiSetup.asp"' in inj[i:j]
    if not in_list("reaper_skip"):
        bad.append("Reaper_WiFiSetup.asp is not in reaper_skip[] (it would be bounced into the shell)")
    if not in_list("reaper_css_only"):
        bad.append("Reaper_WiFiSetup.asp is not in reaper_css_only[] (it would render as raw stock)")
    if in_list("reaper_banner_only"):
        bad.append("Reaper_WiFiSetup.asp is in reaper_banner_only[] (must not be)")

    langs = "BR CN CZ DA DE EN ES FI FR HU IT JP KR MS NL NO PL RO RU SL SV TH TR TW UK".split()
    def rwfs(lang):
        p = os.path.join(www, lang + ".dict")
        try:
            return set(re.findall(r"^(RWFS_\d+)=", open(p, encoding="utf-8", errors="replace").read(), re.M))
        except OSError:
            return None
    en_keys = rwfs("EN") or set()
    if not en_keys:
        bad.append("EN.dict has no RWFS_ tokens")
    for L in langs:
        keys = rwfs(L)
        if keys is None:
            bad.append("%s.dict missing" % L)
        elif keys != en_keys:
            bad.append("%s.dict RWFS_ set differs from EN (%d vs %d)" % (L, len(keys), len(en_keys)))
    used = set(re.findall(r"<#(RWFS_\d+)#>", page))
    if used - en_keys:
        bad.append("page uses undefined tokens: %s" % sorted(used - en_keys))
    if bad:
        return (False, "%d contract break(s)" % len(bad), bad)
    return (True, "box page + gated CGI + banner CTA + %d RWFS_ tokens x 25 packs consistent" % len(en_keys), [])

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
        ("pbr-reassert",       check_pbr_reassert(router)),
        ("warden-log-prefix",  check_warden_log_prefixes(router)),
        ("pbr-fwmark-regex",   check_pbr_fwmark_regex(router)),
        ("firstboot-wifi",     check_firstboot_wifi(router)),
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
