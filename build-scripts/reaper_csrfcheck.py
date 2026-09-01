#!/usr/bin/env python3
"""
reaper_csrfcheck.py -- every CSRF-gated Reaper CGI must have callers that send
the token.

WHY THIS EXISTS. Twice now a Reaper CGI gained an http_id gate in a security
rung and the www page that calls it was never updated, so the endpoint answered
{"ok":0,...} forever and the page looked merely empty or dead. Both halves are
individually correct, so a green build, a clean cppcheck and a staged-symbol
grep are all blind to it.
    v2.7.7  Reaper_QoS.asp     -- live stats never arrived     (a23ff74c47)
    v2.8.5  Reaper_Conn.asp    -- Flow Explorer always empty   (this rung)
Self-tested against both: run over a7ebfa..a23ff74c47^ this flags Reaper_QoS,
and over 7dbc5469c5 (v2.8.3) it flags Reaper_Conn; over bd04f12dcf, which
predates the reaper_conn gate, it is clean.

WHAT IT DOES NOT COVER. The third report of the family, v2.8.4's Warden save
(78336b9ab0), is a DIFFERENT failure: the page sent the right token, but as
multipart/form-data into a url-encoded parser, so nothing parsed. That is a
transport mismatch, not a missing token, and this check cannot see it. Sweeping
www for a body encoding its CGI cannot read is a separate gate, still owed.

WHAT IT DOES. Reads httpd/web.c to learn, per handler, whether it gates and
which actions it exempts, so the allowlist is derived from the C and cannot
drift from it. Then scans the www tree and asserts every request to a gated
endpoint has the token in reach.

SCOPE, HONESTLY. Comments are stripped and the unit is the ENCLOSING FUNCTION:
a request passes if that function sends the token itself, or hands the URL to a
same-file helper that does (gkAct, xAct, reaperTok, ...). So this catches the
real failure -- a caller that never sends the token at all -- and would not
catch a function that sends it on a DIFFERENT request of its own. That is the
defect that has actually shipped three times; a full JS dataflow analysis would
cost more than it saves here.

CHPASS. chpass.cgi is the one non-reaper_ endpoint under the same contract, and
its do_chpass handler is a closed blob whose http_id gate cannot be parsed from
web.c, so it is asserted gated (KNOWN_GATED). Pages never hit it directly; they
call the shared helper httpApi.chpass() in www/js/httpApi.js. A call site is
compliant if that helper injects http_id (cross-file), if the page sends it in
scope, or if the page hands the factory-default case (the only window do_chpass
gates) off to the first-boot surface. This is what caught v2.9.1's deletion of
the only compliant caller, which left every chpass caller unable to set the
factory password (chpass-http-id contract).

Usage: reaper_csrfcheck.py <www-dir> <web.c>
Exit:  0 = clean, 1 = at least one caller would be refused, 2 = bad usage.
"""
import io, os, re, sys, glob

BACK, FWD = 4, 6          # fallback window for a request outside any function


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def readable(p):
    """The staged www ships user1..20.asp as symlinks into user/ ->
    /tmp/var/wwwext, which does not exist until the router mounts it. Skip
    anything we cannot actually open rather than dying on it."""
    try:
        return os.path.isfile(p) and os.access(p, os.R_OK)
    except OSError:
        return False


# ---------------------------------------------------------------- web.c side
DEF = re.compile(r"^\s*(?:static\s+void\s+)?do_reaper_(\w+?)_cgi\s*\(\s*char\s*\*\s*url\s*,", re.M)


def scan_webc(path):
    """endpoint -> set of exempt actions, for gated handlers only."""
    src = read(path)
    defs = []
    for m in DEF.finditer(src):
        tail = src[m.start():m.start() + 400]
        brace, semi = tail.find("{"), tail.find(";")
        if brace != -1 and (semi == -1 or brace < semi):   # definition, not prototype
            defs.append((m.start(), m.group(1)))
    out = {}
    for i, (pos, name) in enumerate(defs):
        body = src[pos:defs[i + 1][0] if i + 1 < len(defs) else len(src)]
        # A handler is gated if it runs the reaper_gate helper OR reads the
        # http_id token itself -- whether via get_cgi("http_id") or the JSON
        # body accessor (safe_)get_cgi_json("http_id", ...). The JSON form was
        # invisible before, so a handler that gated purely through
        # safe_get_cgi_json("http_id") looked ungated and its callers went
        # unchecked.
        gate = re.search(
            r"reaper_gate(_hid)?\s*\("
            r"|get_cgi\s*\(\s*\"http_id\"\s*\)"
            r"|(?:safe_)?get_cgi_json\s*\(\s*\"http_id\"", body)
        if not gate:
            continue                                        # ungated reader
        cond, last = "", None
        for last in re.finditer(r"if\s*\((.*?)\)\s*\{", body[:gate.start()], re.S):
            pass
        if last:
            cond = last.group(1)
        exempt = set(re.findall(r"strcmp\s*\(\s*\w+\s*,\s*\"([^\"]+)\"\s*\)\s*!=\s*0", cond)) \
            if ("strcmp" in cond and "!=" in cond) else set()
        out["reaper_%s.cgi" % name] = exempt
    return out


# Endpoints whose http_id gate cannot be parsed out of web.c because the
# handler is a CLOSED BLOB, asserted here instead. do_chpass_cgi lives in
# web_hook.o: it refuses a factory-default password change without http_id
# (the chpass-http-id contract), but that check runs inside the blob and is
# NOT visible in web.c source, so it can never be derived from the C. It is
# gated and exempts no action.
KNOWN_GATED = {"chpass.cgi": set()}


# ------------------------------------------------------------------ www side
def strip_comments(text):
    """Blank out /*...*/, //..., <!--...--> so prose that names an endpoint is
    never mistaken for a call. Line numbering is preserved."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"/\*.*?\*/", blank, text, flags=re.S)
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", blank, text)
    text = re.sub(r"(?m)^\s*\*.*$", blank, text)
    return text


CALL = re.compile(r"reaper_\w+\.cgi")
# Pages never touch chpass.cgi directly -- they call the shared JS helper
# httpApi.chpass(...), which lives in www/js/httpApi.js. Every such line is a
# request site for chpass.cgi; whether it is compliant depends on the helper
# (chpass_helper_injects) OR on the calling page's own scope.
CHPASS_CALL = re.compile(r"httpApi\.chpass\s*\(")
ACTION = re.compile(r"[?&]action=([A-Za-z0-9_]+)")
ALIAS = re.compile(r"\b(?:var|let|const)\s+(\w+)\s*=\s*[\"'][^\"']*?(reaper_\w+\.cgi)")
FUNC = re.compile(r"\bfunction\s*(\w*)\s*\([^)]*\)\s*\{")


def function_spans(text):
    """[(name, start, end)] by brace matching; innermost wins at lookup time."""
    out = []
    for m in FUNC.finditer(text):
        i, depth = m.end() - 1, 0
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append((m.group(1), m.start(), min(i + 1, len(text))))
    return out


def token_scope(text, spans, off):
    """The innermost function body containing `off`, plus the bodies of every
    same-file function it calls -- one level covers the helper pattern, where
    the request hands its URL to xAct/gkAct/reaperTok and that appends the
    token."""
    inner = None
    for name, a, b in spans:
        if a <= off < b and (inner is None or a > inner[1]):
            inner = (name, a, b)
    if inner is None:
        return None
    body = text[inner[1]:inner[2]]
    scope = [body]
    called = set(re.findall(r"\b(\w+)\s*\(", body))
    for name, a, b in spans:
        if name and name in called:
            scope.append(text[a:b])
    return "\n".join(scope)


def chpass_helper_injects(wwwdir):
    """Cross-file resolution for httpApi.chpass -> www/js/httpApi.js. True iff
    the body of the shared `chpass: function(...)` helper injects the http_id
    token (assigns it, e.g. from nvram_get("http_id"), into the postData it
    sends). When true, every httpApi.chpass call site is compliant without the
    page sending the token; when false (or the helper/file is absent), no page
    sends it and the helper does not either, so callers are breakers."""
    p = os.path.join(wwwdir, "js", "httpApi.js")
    if not readable(p):
        return False
    text = strip_comments(read(p))
    m = re.search(r"['\"]?chpass['\"]?\s*:\s*function\s*\([^)]*\)\s*\{"
                  r"|['\"]?chpass['\"]?\s*\([^)]*\)\s*\{", text)
    if not m:
        return False
    i, depth, n = m.end() - 1, 0, len(text)      # m.end()-1 is the opening brace
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = text[m.end() - 1:i + 1]
    return "http_id" in body


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip())
        return 2
    wwwdir, webc = sys.argv[1], sys.argv[2]
    if not os.path.isdir(wwwdir):
        print("no such www dir: %s" % wwwdir)
        return 2
    if not os.path.isfile(webc):
        print("no such web.c: %s" % webc)
        return 2

    gated = scan_webc(webc)
    if not gated:
        print("reaper_csrfcheck: parsed NO gated handlers out of %s - the parser is "
              "stale, refusing to pass vacuously" % webc)
        return 1
    # Blob-gated endpoints cannot be parsed from web.c; assert them. Merged
    # AFTER the emptiness check so a stale web.c parser is never masked by them.
    gated.update(KNOWN_GATED)
    chpass_ok = chpass_helper_injects(wwwdir)

    bad = checked = 0
    skipped = 0
    for f in sorted(glob.glob(os.path.join(wwwdir, "*.asp")) +
                    glob.glob(os.path.join(wwwdir, "*.js"))):
        if not readable(f):
            skipped += 1
            continue
        raw = read(f)
        if "reaper_" not in raw:
            continue
        text = strip_comments(raw)
        lines = text.splitlines()
        spans = function_spans(text)
        # chpass.cgi's do_chpass gate demands http_id ONLY while the password is
        # still the factory default (the gate is `if (is_def_pwd)`); once it is
        # set, do_chpass's own current-credential check is the gate and no token
        # is needed. So a page that hands the factory-default case straight to
        # the dedicated first-boot surface -- location.replace(...Reaper_FirstBoot
        # .asp) under a check_pw()/force_chgpass guard -- can only ever POST
        # chpass AFTER setup, and is not a breaker even with no token in sight.
        firstboot_delegate = bool(re.search(
            r"location\s*\.\s*(?:replace|assign|href)[^;\n]*Reaper_FirstBoot\.asp", text))
        # `var ENDPOINT="/reaper_conn.cgi"` only NAMES the endpoint; the requests
        # that use it are checked where they are issued.
        aliasdef = set(i for i, l in enumerate(lines) if ALIAS.search(l))
        alias = {m.group(1): m.group(2) for m in ALIAS.finditer(text)}

        for i, line in enumerate(lines):
            if i in aliasdef:
                continue
            eps = set(CALL.findall(line))
            for name, ep in alias.items():
                if re.search(r"\b%s\b" % re.escape(name), line):
                    eps.add(ep)
            if CHPASS_CALL.search(line):
                eps.add("chpass.cgi")
            for ep in eps:
                if ep not in gated:
                    continue
                checked += 1
                off = sum(len(l) + 1 for l in lines[:i])
                win = token_scope(text, spans, off)
                if win is None:                             # request at top level
                    win = "\n".join(lines[max(0, i - BACK): i + 1 + FWD])
                if "http_id" in win:
                    continue
                # Cross-file resolution: a chpass caller is also compliant when
                # the shared httpApi.chpass helper injects the token for it, or
                # when the page delegates the factory-default case (the only
                # window do_chpass gates) to the first-boot surface.
                if ep == "chpass.cgi" and (chpass_ok or firstboot_delegate):
                    continue
                act = ACTION.search(line) or ACTION.search(win)
                if (act.group(1) if act else "status") in gated[ep]:
                    continue
                bad += 1
                print("CSRF %s:%d: %s is CSRF-gated but this request sends no "
                      "http_id -- it will be refused" % (os.path.basename(f), i + 1, ep))
    print("reaper_csrfcheck: %d breakers, %d request sites over %d gated endpoints%s"
          % (bad, checked, len(gated),
             (", %d unreadable files skipped" % skipped) if skipped else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
