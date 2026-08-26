#!/usr/bin/env python3
"""reaper_docs.py - keep the documentation in lock-step with the fleet.

WHY THIS EXISTS
---------------
Every release drifts the same handful of facts across the documentation: the
current version, the published version, the patch count, how many models are in
the fleet, how many jobs a fleet run costs. On 2026-08-26 a sweep of docs/ found
fifteen wrong statements; twelve of them were one of those five values, and the
repo already knew the right answer for every one. The docs were simply the last
place to hear about it.

THE HARD PART IS NOT FINDING VERSIONS - IT IS IGNORING MOST OF THEM.
CHANGELOG.md carries seventeen version references and RELEASE-NOTES.md
twenty-one, and nearly all of them are historical record that is correct
*because* it is old. A checker that asserts "every version string is current"
fails on dozens of lines that must never change, and a gate that cries wolf is a
gate everyone learns to skip.

So the unit of checking is one explicitly marked claim, never a file and never a
date. A claim is marked by an HTML comment straight after the value:

    the series runs to `0550` <!--@patchcount-->, and the newest published
    release is v2.7.6 <!--@pubver-->

HTML comments do not render, unmarked prose is ignored by construction, and
adoption is incremental: mark a claim the next time you touch it.

Numbers may be written as digits or as words ("six models", "12 jobs"); --fix
preserves whichever form is already there, so prose stays prose.

EXIT CODES  (cut_fleet.sh depends on these)
  0  every marked claim agrees
  1  at least one marked claim disagrees   <- the only hard failure
  2  bad usage
  3  cannot derive the fleet facts (missing/unreadable inputs) - the caller
     should WARN and carry on, never abort a release over this file
"""

import argparse
import datetime
import io
import json
import os
import re
import sys

# --------------------------------------------------------------------------
# derivation: every value comes from a file the repo already maintains, so
# there is no second source of truth to keep in step.
# --------------------------------------------------------------------------

NUM_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
    13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen",
    17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
}
WORD_NUMS = {v: k for k, v in NUM_WORDS.items()}


class Facts(object):
    """The fleet's current state, derived once."""

    def __init__(self, root):
        self.root = root
        self.problems = []
        self.treever = self._tree_version()
        self.pubver, self.pubdate = self._published()
        self.patchcount = self._patch_count()
        self.models = self._models()
        self.modelcount = len(self.models) if self.models else None
        self.fleetjobs = self.modelcount * 2 if self.modelcount else None

    def _read_json(self, rel):
        p = os.path.join(self.root, rel)
        try:
            with io.open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.problems.append("%s: %s" % (rel, e))
            return None

    def _tree_version(self):
        """Newest cut rung = newest provenance entry. Repo-local on purpose:
        the canon clone is not present in a fork or in CI."""
        m = self._read_json("provenance/manifest.json")
        if not m or not m.get("releases"):
            return None
        return m["releases"][0].get("version")

    def _published(self):
        j = self._read_json("releases/latest.json")
        if not j:
            return None, None
        return j.get("version"), j.get("date")

    def _patch_count(self):
        d = os.path.join(self.root, "patches")
        try:
            return len([f for f in os.listdir(d) if f.endswith(".patch")])
        except Exception as e:
            self.problems.append("patches/: %s" % e)
            return None

    def _models(self):
        """The model list the fleet actually builds, from the workflow's own
        dropdown - the same list cut_fleet.sh and the CI matrix are driven by."""
        p = os.path.join(self.root, ".github", "workflows", "public-build.yml")
        try:
            with io.open(p, encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            self.problems.append("public-build.yml: %s" % e)
            return None
        m = re.search(r"^\s*options:\s*\[([^\]]*RT-BE[^\]]*)\]", text, re.M)
        if not m:
            self.problems.append("public-build.yml: model options list not found")
            return None
        items = [x.strip() for x in m.group(1).split(",")]
        return [x for x in items if x and x != "all"]

    def usable(self):
        return not (self.treever is None or self.patchcount is None
                    or self.models is None)


# --------------------------------------------------------------------------
# claims
# --------------------------------------------------------------------------

MARKER_RE = re.compile(r"<!--@([a-z]+)-->")
STAMP_RE = re.compile(
    r"current as of\s+\*{0,2}(v[0-9]+\.[0-9]+\.[0-9]+[a-z]?)\*{0,2}\s*"
    r"[^0-9]{0,6}([0-9]{4}-[0-9]{2}-[0-9]{2})")

VERSION_TAIL = re.compile(r"(v[0-9]+\.[0-9]+\.[0-9]+[a-z]?)(\*{0,2}|`?)\s*$")
DATE_TAIL = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(\*{0,2}|`?)\s*$")
NUM_TAIL = re.compile(r"(?:^|[\s`*(])(`?)([0-9]{1,4}|[a-z]+)(`?)(\*{0,2})\s*$")


def _fmt_like(sample, value):
    """Render `value` the way `sample` was written: word for word, digits for
    digits, zero-padded if the sample was (patch numbers read `0550`)."""
    if sample.isdigit():
        if len(sample) > len(str(value)) and sample.startswith("0"):
            return str(value).zfill(len(sample))
        return str(value)
    low = sample.lower()
    if low in WORD_NUMS:
        word = NUM_WORDS.get(value)
        if word:
            return word[0].upper() + word[1:] if sample[0].isupper() else word
    return str(value)


class Claim(object):
    def __init__(self, path, lineno, kind, found, expected, col):
        self.path = path
        self.lineno = lineno
        self.kind = kind
        self.found = found
        self.expected = expected
        self.col = col

    @property
    def ok(self):
        if self.found is None:
            return False
        if self.kind in ("modelcount", "fleetjobs", "patchcount"):
            f = self.found.lower()
            n = int(f) if f.isdigit() else WORD_NUMS.get(f)
            return n is not None and n == self.expected
        return self.found == self.expected


def _in_code_span(line, pos):
    """True if `pos` sits inside a markdown inline-code span.

    A doc that explains the marker syntax necessarily contains markers - see
    COMMANDS.md. Those are written as `<!--@pubver-->` in backticks, so anything
    inside a code span is documentation about a claim, never a claim."""
    return line.count("`", 0, pos) % 2 == 1


def scan_line(line, facts, context=""):
    """Yield (kind, found_literal, expected, start, end) for each marker.

    `context` is the marked line plus the lines just before it: a model list is
    prose that wraps, or a table with a row per model, so membership is checked
    over that block rather than one line."""
    out = []
    for m in MARKER_RE.finditer(line):
        kind = m.group(1)
        head = line[:m.start()].rstrip()
        if kind == "stamp" or _in_code_span(line, m.start()):
            continue
        if kind == "treever":
            expected, tail = facts.treever, VERSION_TAIL.search(head)
        elif kind == "pubver":
            expected, tail = facts.pubver, VERSION_TAIL.search(head)
        elif kind == "pubdate":
            expected, tail = facts.pubdate, DATE_TAIL.search(head)
        elif kind == "patchcount":
            expected, tail = facts.patchcount, NUM_TAIL.search(head)
        elif kind == "modelcount":
            expected, tail = facts.modelcount, NUM_TAIL.search(head)
        elif kind == "fleetjobs":
            expected, tail = facts.fleetjobs, NUM_TAIL.search(head)
        elif kind == "models":
            # A list, not a scalar: verified by membership, never rewritten.
            hay = context or line
            missing = [x for x in (facts.models or []) if x not in hay]
            out.append(("models", None if missing else "ok",
                        "ok" if not missing else "missing: " + ",".join(missing),
                        None, None))
            continue
        else:
            out.append((kind, None, "UNKNOWN MARKER", None, None))
            continue
        if expected is None or tail is None:
            out.append((kind, None, expected, None, None))
            continue
        grp = 1 if kind in ("treever", "pubver", "pubdate") else 2
        out.append((kind, tail.group(grp), expected,
                    tail.start(grp), tail.end(grp)))
    return out


def doc_files(root, extra):
    out = []
    d = os.path.join(root, "docs")
    if os.path.isdir(d):
        out += [os.path.join("docs", f) for f in sorted(os.listdir(d))
                if f.endswith(".md")]
    for e in extra:
        if os.path.exists(os.path.join(root, e)):
            out.append(e)
    return out


EXTRA_DOCS = ["README.md", "CONTRIBUTING.md", "SECURITY.md",
              "build-scripts/README.md"]


def process(root, mode, facts):
    bad, fixed, stamps, unmarked, unwritable = [], [], [], [], []
    for rel in doc_files(root, EXTRA_DOCS):
        path = os.path.join(root, rel)
        # newline="" both ways: this repo holds a mix of LF and CRLF files, and a
        # checker that silently renormalises one produces a 3000-line diff nobody
        # can review - the exact noise that hides a real change.
        with io.open(path, encoding="utf-8", newline="") as f:
            lines = f.read().splitlines(True)

        changed, marks = False, 0
        stamp_ver, stamp_date, stamp_line = None, None, None

        for i, line in enumerate(lines):
            if "<!--@stamp-->" in line:
                s = STAMP_RE.search(line)
                stamp_line = i
                if s:
                    stamp_ver, stamp_date = s.group(1), s.group(2)
            # a fleet list is usually a table, so the window spans one.
            ctx = "".join(lines[max(0, i - 11):i + 1])
            for kind, found, expected, a, b in scan_line(line, facts, ctx):
                marks += 1
                c = Claim(rel, i + 1, kind, found, expected, a)
                if kind == "models":
                    if found != "ok":
                        bad.append(c)
                    continue
                if c.ok:
                    continue
                if a is None:
                    bad.append(c)          # unreadable / underivable: report
                    continue
                if mode == "fix":
                    new = (expected if kind in ("treever", "pubver", "pubdate")
                           else _fmt_like(found, expected))
                    lines[i] = line[:a] + new + line[b:]
                    line = lines[i]
                    fixed.append(c)
                    changed = True
                else:
                    bad.append(c)

        if marks == 0:
            unmarked.append(rel)
        if stamp_line is None:
            stamps.append((rel, None, None))
        elif stamp_ver != facts.treever:
            stamps.append((rel, stamp_ver, stamp_date))

        if changed and mode == "fix":
            today = datetime.date.today().isoformat()
            if stamp_line is not None:
                lines[stamp_line] = STAMP_RE.sub(
                    "current as of **%s** · %s" % (facts.treever, today),
                    lines[stamp_line])
            try:
                with io.open(path, "w", encoding="utf-8", newline="") as f:
                    f.write("".join(lines))
            except (IOError, OSError) as e:
                # The lean repo sits on a Windows mount and anything that has
                # been through `sed -i` from WSL comes back with the ReadOnly
                # attribute set (the same trap that stops cut_rung pinning
                # EXPECTED_VERSION). Name the file and the remedy rather than
                # dying with a traceback halfway through a sweep.
                sys.stderr.write(
                    "reaper_docs: cannot write %s (%s)\n"
                    "  if this is a Windows mount, clear the read-only attribute:\n"
                    "  powershell Set-ItemProperty -Path <file> -Name IsReadOnly -Value $false\n"
                    % (rel, e))
                unwritable.append(rel)
                continue

    return bad, fixed, stamps, unmarked, unwritable


def main():
    ap = argparse.ArgumentParser(
        description="Check (or fix) the documentation against the fleet's own facts.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true",
                   help="fail on any marked claim that disagrees (the gate)")
    g.add_argument("--fix", action="store_true",
                   help="rewrite disagreeing claims and bump those files' stamps")
    g.add_argument("--report", action="store_true",
                   help="list docs trailing the current rung; never fails")
    ap.add_argument("--root", default=None, help="repo root (default: this script's parent)")
    ap.add_argument("--json", default=None, help="also write the report to this file")
    a = ap.parse_args()

    root = a.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mode = "fix" if a.fix else ("report" if a.report else "check")

    facts = Facts(root)
    if not facts.usable():
        sys.stderr.write("reaper_docs: cannot derive the fleet facts:\n")
        for p in facts.problems:
            sys.stderr.write("  %s\n" % p)
        sys.stderr.write("  (not a doc failure - the caller should warn, not abort)\n")
        return 3

    print("reaper_docs: tree %s | published %s (%s) | %s patches | %d models | %d fleet jobs"
          % (facts.treever, facts.pubver, facts.pubdate, facts.patchcount,
             facts.modelcount, facts.fleetjobs))

    bad, fixed, stamps, unmarked, unwritable = process(root, mode, facts)

    for c in fixed:
        print("  [fixed] %s:%d  %s -> %s" % (c.path, c.lineno, c.found, c.expected))

    if mode == "report":
        if stamps:
            print("\ndocs whose stamp predates %s (worklist, not a failure):" % facts.treever)
            for rel, ver, _ in stamps:
                print("  %-34s %s" % (rel, ver or "no stamp"))
        if unmarked:
            print("\ndocs with no claim markers yet:")
            for rel in unmarked:
                print("  %s" % rel)
        if a.json:
            with io.open(a.json, "w", encoding="utf-8") as f:
                json.dump({"version": facts.treever,
                           "generated": datetime.date.today().isoformat(),
                           "trailing": [{"doc": r, "stamp": v} for r, v, _ in stamps],
                           "unmarked": unmarked}, f, indent=2)
            print("\nwrote %s" % a.json)
        return 0

    # A file we could not write is a failure, and must never be reported as
    # "all agree" - the claims in it are still wrong, we just could not say so.
    if unwritable:
        print("\n%d file(s) could not be written: %s"
              % (len(unwritable), ", ".join(unwritable)))
        return 1

    if bad:
        print("\n%d claim(s) disagree with the repo:" % len(bad))
        for c in bad:
            print("  %s:%d  @%s  found %r, expected %r"
                  % (c.path, c.lineno, c.kind, c.found, c.expected))
        print("\nFix them, or run:  build-scripts/reaper_docs.py --fix")
        return 1

    if fixed:
        print("\nreaper_docs: %d claim(s) rewritten, all agree now" % len(fixed))
    else:
        print("reaper_docs: all marked claims agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
