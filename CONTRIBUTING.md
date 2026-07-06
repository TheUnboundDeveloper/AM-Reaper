# Contributing

Thanks for wanting to help harden the RT-BE96U.

1. **Set up the build environment** — read [`docs/DEV-SETUP.md`](docs/DEV-SETUP.md). It covers fetching the upstream source and toolchains, applying [`patches/`](patches/), the WSL/gcc-10.3 build recipe, and how to verify a change compiles and links.
2. **Understand what's already fixed** — [`docs/REAPER-FIXES.md`](docs/REAPER-FIXES.md) is the authoritative fix list. Check it (including the "deferred by decision" items) before re-reporting or re-fixing something.
3. **Security findings** — see [SECURITY.md](SECURITY.md). Please don't open public issues for exploitable bugs.
4. **Submitting changes** — open a PR that adds/modifies patch files in `patches/` (generated with `git format-patch` against upstream tag `3006.102.8-beta2`), with a note on how you build-verified it. Keep patches focused: one finding or one tightly-related class per patch.

Scope guardrails: RT-BE96U only, open-source userspace only (never the proprietary blobs), and no behavior changes beyond what the hardening requires.
