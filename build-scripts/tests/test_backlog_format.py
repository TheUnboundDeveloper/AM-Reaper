#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/BACKLOG.md keeps its one-line-per-item form.

WHY THIS EXISTS. The backlog is an index: one physical line per item (priority, title, a short status, a
pointer to the notes or the review report), with every detail kept in the notes. It has drifted back to
multi-line entries, to sentences inside titles and to build histories inside status brackets several times,
and each time it was found by eye. This test is the gate.

WHAT IT CHECKS
  - LF line endings, and the "Doc status" stamp line is present;
  - every entry is ONE line: nothing but entries, blank lines, rules and the section's italic description
    stands under a section heading;
  - open sections: `- **[P1..P4] Title** [**[status]**] <arrow> notes: `file.md`` or `<arrow> report: `id` ...`;
  - the closed (working-as-designed) section: the same without a priority;
  - titles stay under 140 characters and status brackets under 60 (detail belongs in the notes);
  - no duplicate titles, no retired pointer kinds, no retired sections (Waiting, Work next, Blocked);
  - every Contents link lands on a section heading and every section is in Contents;
  - when a notes directory is available (REAPER_BACKLOG_NOTES, or a notes folder beside the repo), every
    named notes file exists; without one this check is skipped (the notes are not part of the repo);
  - when the other source line's repo is beside this one (REAPER_LEAN_PEER, or the sibling folder), the two
    BACKLOG.md files are identical apart from the stamp line.

Exit 0 pass, 1 fail, 77 skipped (no docs/BACKLOG.md).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DOCS = os.environ.get("REAPER_DOCS", os.path.join(REPO, "docs"))
PATH = os.path.join(DOCS, "BACKLOG.md")
if not os.path.isfile(PATH):
    print("SKIP: no docs/BACKLOG.md"); sys.exit(77)

ARROW = u"↳"
TITLE_MAX, STATUS_MAX = 140, 60
CLOSED = "closed as working-as-designed"
RETIRED = ("waiting", "work next", "blocked")

raw = open(PATH, "rb").read()
text = raw.decode("utf-8")
lines = text.split("\n")
fails, n_ok = [], 0

def a(s):
    return s.encode("ascii", "replace").decode("ascii")

def check(ok, msg):
    global n_ok
    if ok:
        n_ok += 1
    else:
        fails.append(msg)
        print("FAIL " + a(msg))

check(b"\r" not in raw, "the file has CR characters (it must be LF)")
check(any("<!--@stamp-->" in l and l.startswith("> **Doc status:**") for l in lines), "no Doc status stamp line")

OPEN = re.compile(u"^- \\*\\*\\[P([1-4])\\] (.+?)\\*\\* (?:\\*\\*\\[([^\\]]+)\\]\\*\\* )?" + ARROW + u" (.+)$")
WAD = re.compile(u"^- \\*\\*(.+?)\\*\\* (?:\\*\\*\\[([^\\]]+)\\]\\*\\* )?" + ARROW + u" (.+)$")
PTR = re.compile(r"^(notes|report): `[^`]+`")

def slug(h):
    return re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")

section, italic, entries, headings, contents = None, False, [], [], []
for no, line in enumerate(lines, 1):
    if line.startswith("## "):
        section, italic = line[3:].strip(), False
        headings.append(section)
        low = section.lower()
        check(not any(w in low for w in RETIRED), "line %d: retired section '%s'" % (no, section))
        continue
    if section is None:
        continue
    if section == "Contents":
        m = re.match(r"^- \[(.+?)\]\(#([^)]+)\)$", line)
        if m:
            contents.append((m.group(1), m.group(2)))
        else:
            check(line.strip() in ("", "---"), "line %d: not a Contents link: %s" % (no, line[:60]))
        continue
    if italic:
        italic = not line.rstrip().endswith("*")
        continue
    if line.strip() in ("", "---"):
        continue
    if line.startswith("*") and not line.startswith("**"):
        italic = not (len(line.rstrip()) > 1 and line.rstrip().endswith("*"))
        continue
    if not line.startswith("- "):
        check(False, "line %d: text outside an entry (an entry is ONE line; detail goes in the notes): %s" % (no, line[:70]))
        continue
    closed = CLOSED in section.lower()
    m = (WAD if closed else OPEN).match(line)
    if not m:
        why = "no priority / title / pointer in the expected form"
        if ARROW not in line:
            why = "no notes or report pointer"
        elif ARROW + " memory:" in line:
            why = "the memory pointer is retired - point at a notes file"
        check(False, "line %d: %s: %s" % (no, why, line[:80]))
        continue
    if closed:
        title, status, ptr = m.group(1), m.group(2), m.group(3)
    else:
        title, status, ptr = m.group(2), m.group(3), m.group(4)
    check(PTR.match(ptr) is not None, "line %d: pointer is not `notes:` or `report:` with a name in backticks: %s" % (no, ptr[:60]))
    check(len(title) <= TITLE_MAX, "line %d: title is %d characters (max %d): %s" % (no, len(title), TITLE_MAX, title[:60]))
    if status:
        check(len(status) <= STATUS_MAX, "line %d: status is %d characters (max %d): [%s]" % (no, len(status), STATUS_MAX, status[:50]))
    check(line == line.rstrip(), "line %d: trailing white space" % no)
    entries.append((no, section, title, status, ptr))

check(not italic, "a section description opened with * is never closed")
check(len(entries) > 0, "no entries found - the entry pattern no longer matches the file")

seen = {}
for no, sec, title, status, ptr in entries:
    key = title.strip().lower()
    check(key not in seen, "line %d: duplicate title (also line %s): %s" % (no, seen.get(key), title[:60]))
    seen.setdefault(key, no)

anchors = set(slug(h) for h in headings)
for label, anchor in contents:
    check(anchor in anchors, "Contents link #%s does not land on a section" % anchor)
linked = set(x[1] for x in contents)
for h in headings:
    if h != "Contents":
        check(slug(h) in linked, "section '%s' is missing from Contents" % h)

# notes files resolve (only where a notes directory exists; the notes are not part of the repo)
notes_dir = os.environ.get("REAPER_BACKLOG_NOTES", "")
if not notes_dir:
    cand = os.path.join(os.path.dirname(REPO), "asuswrt-merlin.ng", "docs", "backlog")
    notes_dir = cand if os.path.isdir(cand) else ""
n_notes = 0
if notes_dir and os.path.isdir(notes_dir):
    for no, sec, title, status, ptr in entries:
        for name in re.findall(r"`([^`]+\.md)`", ptr):
            n_notes += 1
            check(os.path.isfile(os.path.join(notes_dir, name)), "line %d: notes file not found: %s" % (no, name))
    print("notes directory: %d pointer(s) checked" % n_notes)
else:
    print("notes directory: not available - pointer targets not checked")

# the two source lines carry ONE backlog
peer = os.environ.get("REAPER_LEAN_PEER", "")
if not peer:
    base = os.path.basename(REPO)
    other = base[:-len("-102.8")] if base.endswith("-102.8") else base + "-102.8"
    cand = os.path.join(os.path.dirname(REPO), other)
    peer = cand if os.path.isdir(cand) else ""
pp = os.path.join(peer, "docs", "BACKLOG.md") if peer else ""
if pp and os.path.isfile(pp):
    def body(p):
        return [l for l in open(p, "rb").read().decode("utf-8").split("\n") if "<!--@stamp-->" not in l]
    check(body(PATH) == body(pp), "BACKLOG.md differs from the other source line's copy (edit one, copy it over the other)")
    print("peer copy: compared")
else:
    print("peer copy: not available - not compared")

tmax = max(len(e[2]) for e in entries) if entries else 0
smax = max(len(e[3] or "") for e in entries) if entries else 0
print("\n%d entries in %d sections; longest title %d, longest status %d; %d check(s) ok, %d failed"
      % (len(entries), len(headings) - 1, tmax, smax, n_ok, len(fails)))
sys.exit(1 if fails else 0)
