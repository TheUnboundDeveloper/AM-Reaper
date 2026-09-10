#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every shell variable a workflow step dereferences must be bound in that step.

WHY THIS EXISTS. On 2026-09-10 the v3.1.2 beta publish failed for all six models
with:

    .../runner_temp/xxxx.sh: line 66: CHANNEL: unbound variable

The twelve firmware builds were green and both images had downloaded and passed
their checksums. What failed was the channel-consistency guard added the same
day: the "Collect and verify this model's firmware assets" step bound V, B, FTOK
and M from the resolve step's outputs but never bound CHANNEL, then used it four
times. Under `set -euo pipefail` the first dereference aborts the step.

test_channel_naming.py did not catch it, and could not have: it EXTRACTS the
channel logic and exercises it with variables it binds itself, so it proves the
rules are right while saying nothing about whether the workflow actually binds
them. That is the same lesson the Warden suite taught - a check that has never
been observed to fail is not evidence - applied one level down: a check that has
never been observed to RUN in situ is not evidence either.

WHAT IT DOES. For every `run:` block in the workflows, collect the names it
dereferences ($FOO, ${FOO}, "${FOO}") and the names it binds (FOO=..., for FOO
in, read FOO, the step's own env:, and the workflow/job level env:). Anything
dereferenced but not bound, and not supplied by the runner, is reported.

Deliberately conservative: a default (${FOO:-x}), a test (${FOO:+x}) and
${#FOO[@]} are all safe under `set -u` and are not flagged, so this only fires
on the shape that actually breaks a run.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")

# Supplied by the runner or the shell itself - never bound by our scripts.
RUNNER = {
    "GITHUB_ENV", "GITHUB_OUTPUT", "GITHUB_PATH", "GITHUB_STEP_SUMMARY",
    "GITHUB_WORKSPACE", "GITHUB_REPOSITORY", "GITHUB_REPOSITORY_OWNER",
    "GITHUB_RUN_ID", "GITHUB_RUN_NUMBER", "GITHUB_SHA", "GITHUB_REF",
    "GITHUB_REF_NAME", "GITHUB_ACTOR", "GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH",
    "GITHUB_SERVER_URL", "GITHUB_API_URL", "GITHUB_TOKEN", "GITHUB_ACTION",
    "RUNNER_TEMP", "RUNNER_OS", "RUNNER_ARCH", "RUNNER_TOOL_CACHE", "RUNNER_DEBUG",
    "HOME", "PATH", "PWD", "USER", "SHELL", "TMPDIR", "HOSTNAME", "LANG",
    "IFS", "PS1", "PS2", "BASH_SOURCE", "FUNCNAME", "LINENO", "RANDOM", "SECONDS",
    "PIPESTATUS", "BASH_REMATCH", "OPTARG", "OPTIND", "REPLY", "HOSTTYPE",
}

# ${FOO:-x} ${FOO:+x} ${FOO:=x} ${FOO#x} ${FOO%x} ${#FOO} ${FOO[@]} are all
# safe under set -u, or are not plain dereferences. Only these two shapes break.
DEREF = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)')
SAFE_BRACED = re.compile(r'\$\{[A-Za-z_][A-Za-z0-9_]*[:#%/^,\[-]')
# An assignment can follow anything that ends a word - including a `case` arm's
# closing paren, which is where four of this file's first false positives came
# from (`*_BETA_*) got=pre ;;`).
ASSIGN = re.compile(r'(?:^|[\s;&|(){}])'
                    r'(?:export\s+|local\s+|declare\s+(?:-\w+\s+)?|readonly\s+)?'
                    r'([A-Za-z_][A-Za-z0-9_]*)=', re.M)
FOR_IN = re.compile(r'\bfor\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\b')
# `read` binds EVERY name it is given, not just the first: the provenance replay
# does `while IFS=$'\t' read -r version count expected`, and a first cut of this
# test captured only `version` and then called `$count` unbound.
READ_LINE = re.compile(r'\bread\s+((?:-\w+\s+)*)([A-Za-z_][A-Za-z0-9_ \t]*)')


# A step can hand a name to LATER steps through $GITHUB_ENV; it is then an
# ordinary environment variable and `set -u` is satisfied. Collected file-wide,
# because the exporting step always precedes the consuming one.
GH_ENV = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=[^\n]*>>\s*"?\$\{?GITHUB_ENV')


def read_names(s):
    names = set()
    for _flags, tail in READ_LINE.findall(s):
        names.update(t for t in tail.split() if re.fullmatch(r'[A-Za-z_]\w*', t))
    return names


def strip_comments(s):
    """Blank whole-line `#` comments, keeping line count and offsets.

    Must run BEFORE the quote pass. These workflows are heavily commented in
    English prose, and an apostrophe in a comment ("this model's assets") opens
    a single-quote region that then swallows every assignment until the next
    apostrophe - which is how a first cut of this test reported $TAG, $d and
    $sums as unbound when all three are plainly assigned.
    """
    out = []
    for ln in s.split("\n"):
        out.append(" " * len(ln) if re.match(r'^\s*#', ln) else ln)
    return "\n".join(out)


def strip_single_quoted(s):
    """Blank out '...' regions: the shell does not expand $ inside them.

    Without this an embedded awk/sed/perl program reads as shell - `awk -v v="$B"
    '{ print $v }'` looked like a dereference of an unbound $v when awk owns
    that name entirely.

    It MUST track double quotes as well. Inside "..." an apostrophe is an
    ordinary character, and these workflows are full of them:

        echo "::error::channel mismatch: tag '$V' publishes on the $CHANNEL ..."

    A scanner that treats every apostrophe as a quote opens a region at `'$V'`,
    drifts out of step with the real quoting, and blanks the very dereferences
    it is supposed to see. That is not hypothetical - it is why the negative
    test below failed on this file's first draft: `$CHANNEL` was erased and the
    checker reported a clean release.yml with the bug reintroduced.
    """
    out, i, n = [], 0, len(s)
    dq = False                              # inside "..."
    while i < n:
        c = s[i]
        if dq:
            if c == "\\" and i + 1 < n:     # \" and \\ inside double quotes
                out.append(c); out.append(s[i + 1]); i += 2; continue
            if c == '"':
                dq = False
            out.append(c); i += 1
            continue
        if c == '"':
            dq = True
            out.append(c); i += 1
            continue
        if c == "'":
            j = s.find("'", i + 1)
            if j == -1:                     # unterminated: blank the remainder
                out.append(" " * (n - i))
                break
            # keep newlines so line numbers stay honest across multi-line
            # programs (an awk body spans lines)
            out.append("".join("\n" if ch == "\n" else " " for ch in s[i:j + 1]))
            i = j + 1
            continue
        out.append(c); i += 1
    return "".join(out)


def steps_of(text):
    """Yield (line_no, step_name, run_body, env_names) per `run:` block.

    A hand-rolled scan rather than a YAML parse: the workflows are full of
    ${{ }} expressions that a strict YAML loader is happy with but that would
    need re-quoting, and all this needs is the block text and its indent.
    """
    lines = text.splitlines()
    # env: names anywhere above a step still cover it (workflow- and job-level),
    # so collect them all rather than tracking scope - this test is about
    # UNBOUND names, and over-collecting can only make it quieter, never noisier.
    env_names = set(re.findall(r'^\s{2,}([A-Za-z_][A-Za-z0-9_]*):\s', text, re.M))
    i = 0
    while i < len(lines):
        m = re.match(r'^(\s*)- name:\s*(.+?)\s*$', lines[i])
        name, name_ln = (m.group(2), i + 1) if m else (None, None)
        if m:
            base = len(m.group(1))
            j = i + 1
            while j < len(lines):
                r = re.match(r'^(\s*)run:\s*\|?', lines[j])
                nxt = re.match(r'^(\s*)- ', lines[j])
                if nxt and len(nxt.group(1)) <= base:
                    break
                if r and len(r.group(1)) > base:
                    ind = None
                    body, k = [], j + 1
                    while k < len(lines):
                        ln = lines[k]
                        if ln.strip():
                            cur = len(ln) - len(ln.lstrip())
                            if ind is None:
                                ind = cur
                            if cur < ind:
                                break
                        body.append(ln)
                        k += 1
                    yield (name_ln, name, "\n".join(body), env_names)
                    j = k
                    continue
                j += 1
            i = j
        else:
            i += 1


def check(path):
    text = open(path, encoding="utf-8").read()
    exported = set(GH_ENV.findall(text))
    problems = []
    for ln, name, body, env_names in steps_of(text):
        if "set -u" not in body and "set -euo" not in body:
            continue                      # unbound is not fatal without set -u
        # ${{ }} is substituted by Actions before bash ever sees the script, so
        # it is neither a binding nor a dereference. Blank it first, then the
        # single-quoted regions, keeping length so offsets stay honest.
        s = re.sub(r'\$\{\{.*?\}\}', lambda m: " " * (m.end() - m.start()), body, flags=re.S)
        s = strip_single_quoted(strip_comments(s))
        bound = set(ASSIGN.findall(s)) | set(FOR_IN.findall(s))
        bound |= read_names(s)
        bound |= env_names | exported | RUNNER
        for m in DEREF.finditer(s):
            if SAFE_BRACED.match(s[m.start():]):
                continue
            var = m.group(1) or m.group(2)
            if var not in bound:
                line = s[:m.start()].count("\n") + 1
                problems.append((ln, name, var, line))
    return problems


def negative_test():
    """Put the 2026-09-10 bug back and confirm this test sees it.

    A checker that has only ever been run against a passing tree proves nothing;
    this reintroduces the exact defect - deleting the CHANNEL binding from the
    assets step - and requires that it is reported.
    """
    import tempfile
    src = os.path.join(WORKFLOWS, "release.yml")
    text = open(src, encoding="utf-8").read()
    binding = '          CHANNEL="${{ steps.ver.outputs.channel }}"\n'
    if binding not in text:
        print("SKIP negative test: the CHANNEL binding is not where it was expected")
        return 1
    tmp = os.path.join(tempfile.mkdtemp(), "release.yml")
    open(tmp, "w", encoding="utf-8").write(text.replace(binding, "", 1))
    hits = [p for p in check(tmp) if p[2] == "CHANNEL"]
    if hits:
        print(f"OK   negative test: removing the CHANNEL binding is caught "
              f"({len(hits)} site(s) reported)")
        return 0
    print("FAIL negative test: the CHANNEL binding was removed and NOT reported "
          "- this checker would not have caught the v3.1.2 publish failure")
    return 1


def main():
    fails = negative_test()
    for fn in sorted(os.listdir(WORKFLOWS)):
        if not fn.endswith((".yml", ".yaml")):
            continue
        problems = check(os.path.join(WORKFLOWS, fn))
        seen = set()
        for ln, name, var, off in problems:
            key = (fn, name, var)
            if key in seen:
                continue
            seen.add(key)
            fails += 1
            print(f"FAIL {fn}: step '{name}' (line {ln}) dereferences ${var} "
                  f"without binding it (offset +{off}) - `set -u` aborts there")
        if not problems:
            print(f"OK   {fn}: every step under set -u binds what it dereferences")
    print()
    print(f"{fails} problem(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
