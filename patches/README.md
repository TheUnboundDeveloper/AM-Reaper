# patches/

The `reaper` hardening for the RT-BE96U, as `git format-patch` files generated on top of Asuswrt-Merlin **`3006.102.8-beta2`**. Apply them to a stock upstream checkout to reproduce the hardened source.

## Apply

```bash
git clone https://github.com/RMerl/asuswrt-merlin.ng.git
cd asuswrt-merlin.ng
git checkout 3006.102.8-beta2

# preferred — preserves authorship + commit messages:
git am /path/to/ASUS-Merlin-Reaper/patches/*.patch

# or plain patch:
#   for p in /path/to/ASUS-Merlin-Reaper/patches/*.patch; do patch -p1 < "$p"; done
```

They touch only the shared open-source userspace (`release/src/router/{httpd, rc, shared, libovpn, snooper, urlfilterd, lltdc, wsdd2, infosvr, libcodb, …}`), so they apply cleanly to a stock tree. Build per [`../docs/DEV-SETUP.md`](../docs/DEV-SETUP.md).

## What each patch is

The filenames carry the summary; the full per-finding mapping (which CVE-class each fixes, with severities) is in [`../docs/REAPER-FIXES.md`](../docs/REAPER-FIXES.md). Roughly:

- `0001`–`0021` — **Round 1** hardening (IPsec/rc command-injection, httpd pre-auth overflow, snmpd/nvparse/usb/shared memory-safety, format strings, temp-file races, perms).
- `0022` — build branding (`BUILDREV=-reaper`).
- `0024`–`0025` — **Round 2** hardening (libovpn injection class; snooper/urlfilterd/lltdc/wsdd2 memory safety; infosvr/libcodb/rstats/lanauth defense-in-depth).

## Notes

- **`0023` is intentionally absent.** That commit only added project documentation to the tree — the docs ship in this repo's [`docs/`](../docs/) instead, so it isn't included as a source patch. `git am patches/*.patch` applies the rest in order regardless of the gap.
- **The "BE96U-only" strip is not a patch here.** Making the tree single-model (removing the other BE sibling models' artifacts) was a large mechanical deletion (~5,650 files). It is **optional** — `make rt-be96u` builds fine from the full upstream tree — so it's omitted to keep this set small and focused on the security changes.
