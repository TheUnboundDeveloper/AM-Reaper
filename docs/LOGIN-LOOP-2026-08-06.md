# First-Boot Login Refresh-Loop — Investigation Report (2026-08-06)

**Status: ROOT-CAUSED at source. No fix applied yet (investigation only, per owner
instruction). NOT fixed in v2.1.7–v2.1.9 — the affected files are byte-identical to
v2.1.6, so v2.2.0 must carry the remediation below.**

## Field report (v2.1.6, factory-fresh install)

1. First connect → prompt for default login `admin`/`admin` → works.
2. Next window: set custom username + password → confirm → "service restarts."
3. "The login window pops up again. However, it's impossible to enter anything
   because the page keeps constantly refreshing/reloading in a loop." Internet
   itself works.
4. Only known recovery: restore stock ASUS firmware, then upgrade to Reaper via
   the Web UI.

## Root cause — a stale index-page cache in httpd

`httpd` computes the landing page **once, at process startup**:

- `httpd/httpd.c:2881` — `get_index_page(indexpage, sizeof(indexpage));` in main().
- `get_index_page()` (`shared/misc.c:6378`) returns **`Reaper_FirstBoot.asp`**
  while `is_passwd_default()` or `force_chgpass` is true (the v1.9.5 admin/admin
  dashboard-bypass fix), else `Main_ReaperDash.asp`.

On a factory-default box httpd starts while the password is still `admin` →
`indexpage` is cached as **`Reaper_FirstBoot.asp`** — and it is **never
recomputed**, because the credential flow deliberately avoids an httpd restart:
`chpass.cgi` is called with `restart_httpd=0`, and the follow-up apply
(`saveNvram;restart_chpass`) maps to `setup_passwd()` only (`rc/services.c:21207`).

After the user sets their credentials, the wizard navigates to `/`:

1. `/` → `file = indexpage` (`httpd.c:1608`) = **stale `Reaper_FirstBoot.asp`**.
2. `Reaper_FirstBoot.asp` renders and its v2.1.5 self-recovery guard
   (`Reaper_FirstBoot.asp:137-139`) reads the **live** state — `check_pw()` now 0,
   `force_chgpass` 0 — and correctly concludes the credential step is done →
   `location.replace("/")`.
3. `/` → stale `indexpage` → `Reaper_FirstBoot.asp` → guard → `/` → …

That is the reported loop: the FirstBoot credential card (which reads as "the
login window") reloading several times per second, uninteractable. If the
credential change also dropped the web session, the real login page appears once
— but logging in with the new password re-enters the loop, because `login_cgi`'s
post-login redirect uses the same stale `indexpage` global (`web.c:25376`), or the
stored `login_url`/`next_page`, which is also `Reaper_FirstBoot.asp`. Every path
converges on the loop; the GUI is unusable until httpd restarts.

## Why the history lines up

- **v2.1.2-era report** ("second credential window rejects everything — Could not
  apply credentials"): same stale `indexpage`. Pre-v2.1.5 the stale FirstBoot page
  simply re-showed the form, whose second `chpass` could never succeed.
- **v2.1.5** (`a11cc56879`) added the self-recovery leave-guard: correct in
  isolation, but against the stale cache it converted the dead-end into the
  **visible refresh loop** now reported on v2.1.6. The page was never the root
  cause — httpd's startup cache is.
- **v2.1.4** (`502d19c8a1`) unified the two credential surfaces; also correct, and
  also unable to fix a loop that lives in the cached index.
- **Stock-reflash-then-upgrade "fixes" it** because the upgraded box is already
  configured: httpd starts with a non-default password → `indexpage =
  Main_ReaperDash.asp` → the gate never fires.
- **A plain power-cycle should also recover** — *if* the `saveNvram` commit
  landed. If `chpass` invalidated the session token before the hidden
  `saveNvram;restart_chpass` POST completed, the new password lived in RAM only;
  a reboot reverts to `admin`/`admin` and the wizard re-runs into the same loop —
  which is exactly why field users concluded only a stock reflash helps.
  (Whether the token survives `do_chpass` is closed-blob behavior — metal-verify.)

## Immediate field guidance (v2.1.6 users, no reflash needed)

Power-cycle the router when the loop appears, then log in with the **new**
credentials; if the box answers only to `admin`/`admin` again, redo the credential
step and power-cycle once more. This escapes the loop because httpd recomputes its
landing page at startup.

## Remediation plan (target: v2.2.0)

1. **Primary — make the index decision live.** Recompute instead of trusting the
   startup cache at both consumers:
   - `httpd.c:1608` (bare-`/` mapping): call `get_index_page()` into a local
     buffer per request. Cost is one nvram read + `pw_dec` + two file-exist
     checks, only on bare-`/` requests — negligible.
   - `web.c:25376` (`login_cgi` post-login redirect): same live recompute.
   This kills the loop at the source and also fixes the pre-v2.1.5 dead-end class
   for good.
2. **Suspenders — FirstBoot leaves to an explicit stable target.** Change the
   leave-guard and `finishOk()` to `location.replace("/Main_ReaperDash.asp")`
   instead of `/`. The dashboard never consults `indexpage`, so even a future
   stale-cache regression cannot ping-pong. (If the session is dead this lands on
   the login page with the dashboard as the stored next-page — correct behavior.)
3. **Commit-robustness check (metal):** verify on hardware whether the session
   token survives `do_chpass` (blob). If it does not, the hidden
   `saveNvram;restart_chpass` apply dies unauthenticated and the new credential is
   RAM-only until reboot. If metal confirms that, consider having the wizard fire
   the apply and verify (probe) before reporting success, or find a commit path
   that rides the chpass request itself.
4. **Verify marker:** add a `verify_markers.txt` line for the live-recompute fix
   (grep the `rc`/`httpd` binary for a distinctive symbol/string) so no image can
   ship without it.
5. **Metal acceptance test (factory reset, next build):** full wizard → lands on
   dashboard (or login → dashboard) with **no loop**; `nvram get http_passwd`
   committed (survives reboot); upgrade-in-place from a looping v2.1.6 box
   recovers without factory reset (flash restarts httpd → cache recomputed).

## Scope

Shared code — all five models (RT-BE96U / BE86U / BE88U / GT-BE98 / GT-BE98 Pro),
both variants, every **factory-fresh or factory-reset** install of any build since
the first-boot gate landed (v1.5.5/v1.9.5 lineage). Configured/upgraded boxes are
untouched, which is why routine rung upgrades never showed it.
