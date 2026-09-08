#!/usr/bin/env python3
"""reaper_hiddencheck.py - refuse code a human reviewer cannot see.

    reaper_hiddencheck.py [--allowlist FILE] [--max-details N] [--no-warn]
                          <patch|file|directory>...

Scans NEW code for characters and shapes that are invisible or unreadable to a
person reading the diff: bidirectional overrides (the "Trojan Source" class),
zero-width and other format characters, control bytes, invalid UTF-8, letters
from look-alike scripts inside identifiers, and (as warnings) the shapes that
obfuscated JavaScript takes. A `.patch` argument is read as a git format-patch
file and only its ADDED lines are scanned - that is exactly "the new code" of a
rung. Any other file is scanned whole; a directory is walked (binary files are
skipped).

Runs at cut time on the freshly exported rung (cut_rung.sh step 3b, before the
patches touch the lean repo), on regenerated overlays (cut_fleet.sh), and in CI
over the whole series (repo-hygiene.yml). Stdlib only; Python 3.8+.

Exit 0 = nothing fatal (warnings may be present), 1 = fatal hit(s), 2 = usage.

FATAL classes (exit 1)
  bidi-control     U+202A-202E, U+2066-2069. Reorders what the reader sees.
                   Never allowed anywhere, not even in vendored text.
  zero-width       U+200B-200D, U+2060-2064, U+206A-206F, U+FEFF, U+00AD,
                   U+034F, U+180E, U+2028/2029, U+E0000-E007F (tags) and every
                   other Cf/Co character. Invisible, so a line can carry more
                   than it shows. One exception: U+FEFF as the first character
                   of a file is a UTF-8 BOM (stock ASUS pages have one).
  control-byte     Bytes 0x00-0x08, 0x0B, 0x0E-0x1F, 0x7F and C1 controls
                   U+0080-009F. TAB, LF, CR and FF (0x0C, GNU page breaks)
                   are allowed.
  bad-utf8         A text file that does not decode as UTF-8. Downgraded to a
                   warning inside allowlisted (vendored) paths - Latin-1
                   comments in imported packages are common and harmless.
  confusable       A letter from a script whose glyphs imitate Latin (Cyrillic,
                   Greek, Armenian, Cherokee, fullwidth and mathematical
                   alphanumerics, the letter-like symbols block, ...) inside a
                   word in a CODE file. The word "user" spelled with the
                   Cyrillic small ie in place of its e is a different
                   identifier that looks identical. Only code files are
                   checked (dictionaries and prose legitimately mix scripts:
                   Turkish text is full of the dotless i); under an
                   allowlisted path the hit is a warning.

WARN classes (reported, never fail)
  odd-space        Non-ASCII spaces (NBSP U+00A0, U+2000-200A, U+202F,
                   U+205F, U+3000). Visible-neutral, so not fatal, but not
                   something a person typed on purpose in code.
  bidi-mark        U+200E/200F/061C directional marks. Legitimate in RTL
                   dictionaries, worth a look in code.
  variation-sel    U+FE00-FE0F, U+E0100-E01EF (emoji presentation selectors).
  unassigned       A code point this Python does not know (Cn). Usually a newer
                   emoji; occasionally something stranger.
  obfuscation      In .js/.asp/.htm/.html only: eval(, new Function(, atob(,
                   unescape(, fromCharCode, a run of 24+ \\xNN escapes, 16+
                   \\uNNNN escapes, or a bare 160+ character base64 run on a
                   line that is not a data: URI.
  long-line        A code line over 2000 characters (content scrolls out of
                   sight in every diff viewer).

Allowlist (one entry per line, # comments)
  patches/NNNN-name.patch    that patch: bad-utf8 and confusable become warnings
  release/src/router/foo/    in-tree path PREFIX (trailing slash): same downgrade
  release/src/router/foo/x.c one exact in-tree file (no trailing slash)
  !<either form>             hard allow: EVERY class becomes a warning there.
                             Last resort, and only for third-party content.
The three always-fatal classes (bidi-control, zero-width, control-byte) stay
fatal under a plain entry; that is the point of the scan.

On Windows pass the patches DIRECTORY rather than a 600-file glob (the argument
list limit); a directory argument is walked and every .patch in it is parsed.
"""
import os
import re
import sys
import unicodedata

# --------------------------------------------------------------------------- sets
BIDI = frozenset([0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
                  0x2066, 0x2067, 0x2068, 0x2069])
BIDI_MARK = frozenset([0x200E, 0x200F, 0x061C])
ZERO_WIDTH = frozenset([0x200B, 0x200C, 0x200D, 0x2060, 0x2061, 0x2062, 0x2063,
                        0x2064, 0x206A, 0x206B, 0x206C, 0x206D, 0x206E, 0x206F,
                        0xFEFF, 0x00AD, 0x034F, 0x180E, 0x2028, 0x2029, 0x115F,
                        0x1160, 0x3164, 0xFFA0])
ODD_SPACE = frozenset([0x00A0, 0x1680, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004,
                       0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200A, 0x202F,
                       0x205F, 0x3000])
CTRL_BYTES = frozenset([b for b in range(0x20) if b not in (0x09, 0x0A, 0x0C, 0x0D)]
                       + [0x7F])

# Unicode names that begin with these belong to scripts / styles whose glyphs
# imitate Latin letters. Ordinary accented Latin ("Sauvageau", "café") is NOT
# in the list on purpose.
CONFUSABLE_PREFIXES = (
    "CYRILLIC", "GREEK", "ARMENIAN", "CHEROKEE", "FULLWIDTH", "MATHEMATICAL",
    "LISU", "ROMAN NUMERAL", "MODIFIER LETTER", "CANADIAN SYLLABICS",
    "SCRIPT SMALL", "SCRIPT CAPITAL", "DOUBLE-STRUCK", "BLACK-LETTER",
    "SMALL CAPITAL", "LATIN LETTER", "LATIN SMALL LETTER DOTLESS",
    "LATIN SMALL LETTER SCRIPT", "LATIN SMALL LETTER TURNED",
    "LATIN CAPITAL LETTER TURNED", "LATIN SMALL LETTER LONG S",
    "GEORGIAN", "COPTIC", "DESERET", "OSAGE", "OL CHIKI", "TIFINAGH",
)

CODE_EXT = (".c", ".h", ".cc", ".cpp", ".hpp", ".js", ".asp", ".htm", ".html",
            ".css", ".sh", ".py", ".pl", ".cgi", ".mk", ".mak", ".in", ".ac",
            ".am", ".m4", ".yml", ".yaml", ".json", ".xml", ".conf", ".cfg",
            ".patch", ".php", ".awk", ".sed", ".ld", ".S", ".s")
CODE_BASENAMES = ("Makefile", "makefile", "GNUmakefile", "Kconfig", "configure",
                  "Dockerfile")
JS_EXT = (".js", ".asp", ".htm", ".html")
BINARY_EXT = (".gz", ".tgz", ".xz", ".bz2", ".zip", ".7z", ".png", ".jpg", ".jpeg",
              ".gif", ".ico", ".mp4", ".webm", ".woff", ".woff2", ".ttf", ".otf",
              ".pkgtb", ".bin", ".img", ".o", ".so", ".a", ".pem", ".der", ".pyc")

WORD_RE = re.compile(r"\w+")
HUNK_RE = re.compile(rb"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
DIFF_RE = re.compile(rb"^diff --git a/(.*?) b/(.*)$")
OBF_RE = re.compile(
    r"(?:\beval\s*\(|\bnew\s+Function\s*\(|\batob\s*\(|\bunescape\s*\(|"
    r"fromCharCode|(?:\\x[0-9a-fA-F]{2}){24,}|(?:\\u[0-9a-fA-F]{4}){16,})")
B64_RE = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{160,}={0,2}(?![A-Za-z0-9+/=])")
LONG_LINE = 2000

FATAL_CLASSES = ("bidi-control", "zero-width", "control-byte", "bad-utf8", "confusable")
WARN_CLASSES = ("odd-space", "bidi-mark", "variation-sel", "unassigned",
                "obfuscation", "long-line")
ALWAYS_FATAL = ("bidi-control", "zero-width", "control-byte")


def cp_name(ch):
    return "U+%04X %s" % (ord(ch), unicodedata.name(ch, "?"))


def is_code_file(path):
    base = os.path.basename(path)
    if base in CODE_BASENAMES:
        return True
    return base.endswith(CODE_EXT)


def is_confusable_letter(ch):
    if ord(ch) < 0x80:
        return False
    if not unicodedata.category(ch).startswith("L"):
        return False
    o = ord(ch)
    if 0x2100 <= o <= 0x214F:          # letter-like symbols block
        return True
    name = unicodedata.name(ch, "")
    return name.startswith(CONFUSABLE_PREFIXES)


# ------------------------------------------------------------------- allowlist
class Allowlist:
    def __init__(self, path):
        self.patches = set()       # basenames of allowlisted patch files
        self.prefixes = []         # in-tree path prefixes (downgrade)
        self.hard = []             # in-tree path prefixes (everything warns)
        self.missing = []
        if not path:
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                hard = line.startswith("!")
                if hard:
                    line = line[1:].strip()
                if line.startswith("patches/") and line.endswith(".patch"):
                    self.patches.add(os.path.basename(line))
                elif hard:
                    self.hard.append(line)
                else:
                    self.prefixes.append(line)

    @staticmethod
    def _match(entries, path):
        """Trailing-slash entries are path prefixes (segment-aligned); others
        name one exact file. Both also match when the scanned path is
        relative to a deeper root (a tree scan from release/src/router)."""
        if not path:
            return False
        p = "/" + path.replace("\\", "/")
        for e in entries:
            if e.endswith("/"):
                if p.startswith("/" + e) or ("/" + e) in p:
                    return True
            elif p == "/" + e or p.endswith("/" + e):
                return True
        return False

    def level(self, patch_base, path):
        """0 = not allowlisted, 1 = downgrade, 2 = hard allow."""
        if self._match(self.hard, path):
            return 2
        if patch_base and patch_base in self.patches:
            return 1
        if self._match(self.prefixes, path):
            return 1
        return 0


# --------------------------------------------------------------------- scanner
class Scanner:
    def __init__(self, allow, max_details):
        self.allow = allow
        self.max_details = max_details
        self.findings = {}        # cls -> list of (severity, where, detail)
        self.counts = {}          # (cls, where-file) -> n
        self.files_seen = set()
        self.patches_seen = 0
        self.lines_seen = 0
        self.binary_skipped = 0
        self.nfatal = 0

    # -- recording -----------------------------------------------------------
    def hit(self, cls, severity, patch_base, path, line, col, detail):
        key = (cls, patch_base or "", path or "")
        n = self.counts.get(key, 0) + 1
        self.counts[key] = n
        if severity == "FATAL":
            self.nfatal += 1
        lst = self.findings.setdefault(cls, [])
        if n <= 3:
            where = ("%s:" % patch_base if patch_base else "") + (path or "(commit message)")
            lst.append((severity, "%s:%d:%d" % (where, line, col), detail))

    def severity(self, cls, patch_base, path, code):
        lvl = self.allow.level(patch_base, path)
        if cls in WARN_CLASSES:
            return "WARN"
        if lvl == 2:
            return "WARN"
        if cls in ALWAYS_FATAL:
            return "FATAL"
        if cls == "bad-utf8":
            return "WARN" if lvl == 1 else "FATAL"
        if cls == "confusable":
            return "FATAL" if (code and lvl == 0) else "WARN"
        return "FATAL"

    # -- one line ------------------------------------------------------------
    def scan_line(self, body, patch_base, path, line, message_only=False):
        """body: bytes without the '+' prefix and without the trailing LF."""
        self.lines_seen += 1
        code = is_code_file(path) if path else False
        # 1. raw control bytes (before decoding: they survive any encoding)
        for col, b in enumerate(body):
            if b in CTRL_BYTES:
                self.hit("control-byte", self.severity("control-byte", patch_base, path, code),
                         patch_base, path, line, col, "byte 0x%02X" % b)
                break
        # 2. decode
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as e:
            self.hit("bad-utf8", self.severity("bad-utf8", patch_base, path, code),
                     patch_base, path, line, e.start, "invalid UTF-8 at byte %d" % e.start)
            text = body.decode("utf-8", "replace")
        if text.endswith("\r"):
            text = text[:-1]
        # 3. per-character classes (only non-ASCII can be interesting here)
        if any(ord(ch) >= 0x80 for ch in text):
            for col, ch in enumerate(text):
                o = ord(ch)
                if o < 0x80:
                    continue
                if o in BIDI:
                    self.hit("bidi-control", "FATAL", patch_base, path, line, col, cp_name(ch))
                elif o in BIDI_MARK:
                    self.hit("bidi-mark", "WARN", patch_base, path, line, col, cp_name(ch))
                elif o == 0xFEFF and line == 1 and col == 0:
                    pass                                    # UTF-8 BOM
                elif o in ZERO_WIDTH or 0xE0000 <= o <= 0xE007F:
                    self.hit("zero-width", self.severity("zero-width", patch_base, path, code),
                             patch_base, path, line, col, cp_name(ch))
                elif 0x80 <= o <= 0x9F:
                    self.hit("control-byte", self.severity("control-byte", patch_base, path, code),
                             patch_base, path, line, col, cp_name(ch))
                elif o in ODD_SPACE:
                    self.hit("odd-space", "WARN", patch_base, path, line, col, cp_name(ch))
                elif 0xFE00 <= o <= 0xFE0F or 0xE0100 <= o <= 0xE01EF:
                    self.hit("variation-sel", "WARN", patch_base, path, line, col, cp_name(ch))
                else:
                    cat = unicodedata.category(ch)
                    if cat in ("Cf", "Co"):
                        self.hit("zero-width", self.severity("zero-width", patch_base, path, code),
                                 patch_base, path, line, col, cp_name(ch))
                    elif cat == "Cn":
                        self.hit("unassigned", "WARN", patch_base, path, line, col, "U+%04X" % o)
            # 4. confusable letters inside words - code files only
            if code and not message_only:
                for m in WORD_RE.finditer(text):
                    w = m.group(0)
                    conf = [ch for ch in w if is_confusable_letter(ch)]
                    if not conf:
                        continue
                    self.hit("confusable", self.severity("confusable", patch_base, path, code),
                             patch_base, path, line, m.start(),
                             "%s in %r" % (cp_name(conf[0]), w[:24]))
        if message_only or not path:
            return
        # 5. shapes (warnings)
        if len(text) > LONG_LINE and code:
            self.hit("long-line", "WARN", patch_base, path, line, 0, "%d characters" % len(text))
        if path.endswith(JS_EXT):
            m = OBF_RE.search(text)
            if m:
                self.hit("obfuscation", "WARN", patch_base, path, line, m.start(),
                         "%r" % m.group(0)[:24])
            elif "data:" not in text and B64_RE.search(text):
                self.hit("obfuscation", "WARN", patch_base, path, line,
                         B64_RE.search(text).start(), "bare base64 run")

    # -- inputs --------------------------------------------------------------
    def scan_patch(self, patch_path):
        self.patches_seen += 1
        base = os.path.basename(patch_path)
        with open(patch_path, "rb") as fh:
            data = fh.read()
        cur = None
        in_diff = False
        in_binary = False
        newln = 0
        msgln = 0
        for raw in data.split(b"\n"):
            m = DIFF_RE.match(raw)
            if m:
                cur = m.group(2).decode("utf-8", "replace").strip()
                self.files_seen.add(cur)
                in_diff = True
                in_binary = False
                newln = 0
                continue
            if not in_diff:
                msgln += 1
                self.scan_line(raw, base, None, msgln, message_only=True)
                continue
            if raw.startswith(b"GIT binary patch"):
                in_binary = True
                continue
            if in_binary:
                continue
            hm = HUNK_RE.match(raw)
            if hm:
                newln = int(hm.group(1))
                continue
            if raw.startswith(b"+++ ") or raw.startswith(b"--- "):
                if raw.startswith((b"+++ b/", b"+++ /dev/null", b"--- a/", b"--- /dev/null")):
                    continue
            if raw.startswith(b"\\ No newline"):
                continue
            if raw.startswith(b" "):
                newln += 1
                continue
            if raw.startswith(b"+"):
                self.scan_line(raw[1:], base, cur, newln)
                newln += 1
                continue
            # removed lines, index/mode/rename headers: nothing to see

    def scan_file(self, path, display=None):
        display = display or path.replace("\\", "/")
        if path.lower().endswith(BINARY_EXT):
            self.binary_skipped += 1
            return
        with open(path, "rb") as fh:
            head = fh.read(8192)
            if b"\x00" in head:
                self.binary_skipped += 1
                return
            data = head + fh.read()
        self.files_seen.add(display)
        for i, raw in enumerate(data.split(b"\n"), 1):
            self.scan_line(raw, None, display, i)

    def scan_dir(self, root):
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in (".git", "__pycache__", "node_modules")]
            for fn in sorted(fns):
                p = os.path.join(dp, fn)
                if p.endswith(".patch"):
                    self.scan_patch(p)
                else:
                    self.scan_file(p, os.path.relpath(p, root).replace("\\", "/"))

    # -- report --------------------------------------------------------------
    def report(self, show_warn=True):
        for cls in FATAL_CLASSES + WARN_CLASSES:
            total = sum(n for (c, _, _), n in self.counts.items() if c == cls)
            if total == 0:
                print("[PASS] %-14s none" % cls)
                continue
            sev_fatal = any(s == "FATAL" for s, _, _ in self.findings.get(cls, []))
            tag = "FAIL" if sev_fatal else "WARN"
            sites = len([1 for (c, _, _) in self.counts if c == cls])
            print("[%s] %-14s %d hit(s) in %d file(s)" % (tag, cls, total, sites))
            if tag == "WARN" and not show_warn:
                continue
            shown = 0
            for sev, where, detail in self.findings.get(cls, []):
                if shown >= self.max_details:
                    print("        ... (%d more listed site(s))" % (len(self.findings[cls]) - shown))
                    break
                print("        %s %s  %s" % ("!" if sev == "FATAL" else " ", where, detail))
                shown += 1
        print("reaper_hiddencheck: %d patch(es), %d file(s), %d line(s) scanned, "
              "%d binary skipped: %s" % (
                  self.patches_seen, len(self.files_seen), self.lines_seen,
                  self.binary_skipped,
                  ("FATAL (%d hit(s))" % self.nfatal) if self.nfatal else "no fatal hits"))
        return 1 if self.nfatal else 0


# ------------------------------------------------------------------------ main
def main(argv):
    # Findings quote the offending character; a cp1252 console must not be
    # the thing that crashes the scan.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    allow_path = None
    max_details = 12
    show_warn = True
    inputs = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--allowlist":
            i += 1
            allow_path = argv[i] if i < len(argv) else None
        elif a == "--max-details":
            i += 1
            max_details = int(argv[i]) if i < len(argv) else 12
        elif a == "--no-warn":
            show_warn = False
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        elif a.startswith("-"):
            sys.stderr.write("unknown option: %s\n" % a)
            return 2
        else:
            inputs.append(a)
        i += 1
    if not inputs:
        sys.stderr.write("usage: reaper_hiddencheck.py [--allowlist FILE] [--max-details N] "
                         "[--no-warn] <patch|file|dir>...\n")
        return 2
    if allow_path and not os.path.isfile(allow_path):
        sys.stderr.write("error: allowlist not found: %s\n" % allow_path)
        return 2
    allow = Allowlist(allow_path)
    sc = Scanner(allow, max_details)
    for p in inputs:
        if os.path.isdir(p):
            sc.scan_dir(p)
        elif os.path.isfile(p):
            if p.endswith(".patch"):
                sc.scan_patch(p)
            else:
                sc.scan_file(p)
        else:
            sys.stderr.write("error: no such file: %s\n" % p)
            return 2
    return sc.report(show_warn)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
