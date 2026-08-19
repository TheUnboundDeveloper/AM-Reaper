# "Reaper" — Release Notes

| | |
|---|---|
| **Current rung** | **v2.5.0** — committed on `be96u-only` (HEAD `8be2150520`) and **cut into the lean repo** (patches 0463-0465, 465 total, replay-verified, provenance stamped); **built on RT-BE96U** (MCP variant, `sha256 31e02104…`) with every change confirmed present in the staged rootfs. **Not yet pushed or released**, and the four siblings have not taken it. Carries the new Warden feature, the block-count change, and a full three-phase security review (five defective fixes corrected, the QoS remap reverted pending a hardware test, and a batch of new hardening fixes). The newest *cut* rung remains **v2.4.9** — `3006.102.8_Reaper_v2.4.9`, cut from RT-BE96U: **462 patches** (replay-verified), provenance stamped, and **all four sibling models ported** — they were on v2.4.7, so this rung carries them across v2.4.8 as well. The four overlays were **regenerated** and passed the identity gate; that is expected here rather than a warning sign, because the rung carries v2.4.8's menu work, which touches per-model files. Built on RT-BE96U as a compile check. **No image published.** Published images come from the clean-room CI build. |
| **Newest published** | **v2.3.7**, on all five models, both variants — the newest image you can actually install, and what "current version" means in [`../README.md`](../README.md). |
| **Base** | Asuswrt-Merlin 3006.102.8 (upstream RMerl/asuswrt-merlin.ng) |
| **Models** | ASUS **RT-BEXXU** (primary) + **RT-BE86U**, **RT-BE88U**, **GT-BE98**, **GT-BE98 Pro** siblings — WiFi 7, Broadcom BCM4916 |
| **Images** | Two variants per model — **with** or **without** the AI Advisor (§2) |
| **Rungs without images** | v2.3.8, v2.3.9, v2.4.0 — the firewall spanned all three, and shipping a half-built rules engine was not worth doing — plus v2.4.2, v2.4.3, v2.4.4, v2.4.5, v2.4.6, v2.4.7, v2.4.8, v2.4.9 and v2.5.0. v2.4.1 through v2.4.4, and v2.4.8, are built on RT-BE96U, both variants; v2.4.9 is built on RT-BE96U as a compile check. |
| **Prior full-fleet releases** | **v2.3.4**, **v2.3.2**, **v2.3.1**, **v2.3.0** |

> A security-hardened, rebranded, de-clouded build of Asuswrt-Merlin for the
> RT-BEXXU. This document is the release summary; the exhaustive security detail
> is in [`REAPER-FIXES.md`](REAPER-FIXES.md), the per-version history in
> [`CHANGELOG.md`](CHANGELOG.md), and the maintainer merge guide in
> [`GPL-MERGE.md`](GPL-MERGE.md).

---

## What's new in v2.5.0 — cut into the lean repo, not yet pushed or published

*One new feature, one deliberate change to what an existing statistic means, and four fixes taken
off the backlog. Built on RT-BE96U so the changes could be exercised; the rung is not cut, so there
is no patch series and the four siblings have not taken it.*

### Warden: bring your own blocklists

Up to eight of your own IP or CIDR lists, each given a name and an HTTPS address. They are fetched
on the same schedule as the four built-in feeds and merged into the same block set, so a custom
entry enforces exactly like a built-in one and appears in the same counters — there is no separate
switch and no second set of rules to reason about.

**Private, loopback and reserved ranges are stripped from every list before it is loaded.** That is
the filter added after the July 2026 lockout, when a built-in feed turned out to ship bogon ranges
including the whole of 192.168/16; custom feeds sit behind the same guard, so a list cannot
blackhole your own network however badly chosen it is.

Lists are HTTPS-only, and the address is validated against a deliberately narrow set of characters
— narrower than the URL standard allows. A feed address is one of very few places where text you
type reaches something the router runs as root, so it is treated as a boundary rather than a form
field, and the same check runs again when the fetcher is generated rather than trusting what was
stored.

**That path was reviewed adversarially before release, and the review found four things worth
fixing.** A stored address was being read back into the page in a form a single apostrophe could
have broken out of. `curl` was following redirects from HTTPS to plain HTTP — so a list that
redirected could have been supplied by anyone positioned in the middle, and whatever came back would
have gone straight into a blocking set. There was no limit on how much a list could download, and
the router's scratch space is memory rather than disk, so one oversized list was a way to exhaust
it. And the eight-feed limit counted feeds *accepted* rather than entries *read*, so a malformed
setting was still walked from end to end. All four are fixed.

The checks were run rather than reasoned: the real code was driven with hostile settings and its
output inspected. An address carrying a quote, a command substitution, a backtick, or a plain-HTTP
address produces no fetch at all; one bad entry among good ones is dropped while its neighbours
still work; and twelve entries yield exactly eight.

### Country block counts are now real

Warden drops a packet if it matches a threat feed **or** a blocked country. Both jump to the same
place, so the order between them never decided whether anything was dropped — only which counter got
the credit. The feeds ran first, and the large open feeds overlap heavily with the countries people
block, so the feed rule absorbed nearly every hit: the country table sat near zero while the total
climbed. That is exactly the "block count with no matching country count" that was reported.

Countries are now evaluated first. The per-country numbers are real, and the feed number carries
only what no country rule already matched.

**Nothing about what gets blocked has changed** — but two numbers you may have been watching for
months have changed meaning. Expect country counts to climb much faster from here and the feed count
to flatten, with a visible kink in the history at this version. The breakdown strip from v2.4.5
shows both figures together, which is what makes that readable rather than alarming.

### The donate button goes through our own page

An image ships once and cannot be recalled, so a payment link baked into firmware is permanent:
changing provider, adding an option or retiring a dead link would otherwise need a release on every
installed router. The button now points at `unbounded-engineering.com/support/#give`, and the
redirect happens in the browser after the click — the router never fetches, parses or validates
anything.

The rejected alternative was having the router read the links from the update file. It worked, and
its validation held, but it turned a static page into one whose links a remote file controls. That
was not a trade worth making to swap a URL.

### A full code review, and what is being fixed because of it

Reaper's own code was reviewed end to end in three passes: what is wasteful or unreachable, whether
data actually arrives where it is supposed to, and — still to come — a dedicated security pass. The
first two passes are complete and produced 114 findings. This section tracks what has been fixed;
it will grow as the rest are worked.

**Be clear about the ceiling.** This review covers the code we can read and change. It does not
cover the closed wireless driver, the Broadcom dataplane, `cfg_server`, the end-of-life 4.19 kernel,
or the third-party packages (Samba, OpenVPN, dnsmasq, Tor) that carry their own advisories. "Only
someone with physical access could break in" is not a reachable claim on this hardware, and this
work does not make it one. What it does is narrower and real: reduce what *our* code contributes.

Fixed so far:

- **The scratch directory `/tmp` is now protected against one program interfering with another's
  files.** It holds live control state — generated firewall rules, block lists, the device table —
  and was world-writable without the usual safeguard. Not an attack on its own, since nearly
  everything on a router runs as the administrator; it matters as the second step of a chain. This
  one is inherited from the base firmware rather than introduced here.
- **A device the Gatekeeper had no rule for was displayed as having full access** — including
  devices that were actively being blocked — and the control could not be used to correct it,
  because it only reacts when the selection changes and the wrong value was already selected.
- **Every device was labelled wireless**, cabled ones included, because the flag could only ever
  hold one value. It is now derived from whether the device appears on any Wi-Fi radio. The same fix
  had to restore the hostname and band the device table was discarding on every restart.
- **Four responses were being written a byte at a time** — one network write, and one encrypted
  record under HTTPS, per character. On the 250 KB dropped-packet view that is a quarter of a
  million writes, and because the interface serves one request at a time it stalled the whole GUI.
- **Disabling the firewall engine left up to 256 address sets in memory** until reboot, while the
  comment beside the code claimed they had been cleaned up.

- **Blocking a device only worked on the main network.** The Gatekeeper discovered devices on every
  network - guest, IoT, anything separated off - and enforced on none of them but the primary LAN.
  Block was accepted, recorded and logged, and changed nothing, on exactly the networks people
  create because they distrust what is on them. Enforcement now follows discovery.
- **The firewall could not report a partial failure**, so a ruleset missing any number of block rules
  was recorded as applied - and became the saved configuration and the rollback target if kept.
- **Analytics kept posting a frozen snapshot** to your external service after collection was turned
  off, indefinitely, while reporting success.
- **Inbound connections were counted but attributed to nobody** - port forwards and UPnP mappings
  showed on the WAN graph with no device against them, and IPv6 disagreed with IPv4 on the page.
- **The live graph stuttered every five minutes** while all four history ranges were rewritten
  together. They now take turns.
- **An unconfirmed firewall change could survive the reboot meant to undo it** - the anti-lockout net
  had a hole, because any unrelated save elsewhere in the interface writes the whole settings store,
  pending rule included, while the countdown tracking it lived in memory a reboot clears. Boot now
  starts from the last ruleset you actually confirmed.
- **Warden's "Outbound only" never differed from "Both directions"** and has been removed. Nothing
  about what is filtered changes.
- **QoS priorities are still ranked the old (inverted) way — the fix was reverted.** The class you marked most
  important really is served last (confirmed on hardware), but the router's own queue tool refuses the in-place
  renumber the fix attempted, so the correction cannot be proven without the hardware. This release keeps the
  existing behaviour; the QoS follow-up is tracked in the Backlog.

**Correction resolved (2026-08-19).** The six flagged fixes have been worked. Five are now genuinely
corrected — Gatekeeper enforcement, the firewall's partial-failure reporting, analytics/Prometheus
staleness, inbound-flow attribution, and the unconfirmed-change-survives-reboot hole — and re-validated by
a full RT-BE96U build. The sixth, the QoS priority fix, was **reverted**: the router's own queue tool
confirms the priorities really are inverted, but it also rejects the in-place renumber the fix attempted,
and a correct fix cannot be validated without the hardware, so this release keeps the existing
(inverted-but-stable) behaviour and the QoS follow-up is tracked in the Backlog. The security pass (Phase
3) below has since run and been applied. This version is **committed locally** (patches 0463-0465) but **not yet pushed or published**; roughly 96
smaller code-quality findings from the earlier passes remain unworked.

### The security pass (Phase 3) — what it found and what is fixed

This is the pass the whole review was building toward: eight reviewers plus two specialists, each
given a different way into the router, and one more told to attack this session's own changes. Be
clear about the ceiling, unchanged from before: this covers the code we can read. It does not cover
the closed wireless driver, the Broadcom dataplane, the end-of-life kernel, or the third-party
packages, and "only physical access could break in" is not reachable on this hardware. The goal is
narrower — that our own code adds no way in.

Fixed and confirmed:

- **A saved firewall object could run a command as root.** An address-object's name was passed into
  the rule-builder unquoted, so a name carrying a semicolon and a command executed it with full
  privileges — and it persisted across reboots. Names are now restricted to safe characters at the
  point of use. Administrator-reachable, closed regardless.
- **Warden could run a planted script as root on a router where it was never enabled** — the script
  was executed on an existence check alone, from a directory a lesser process could create first. It
  now runs only when Warden is on and only from a genuinely root-owned, owner-only file.
- **A cluster of working files were world-writable** (the traffic collector, the analytics exporter
  and the health watchdog, including one holding your analytics token) — now owner-only. **Two heavy
  read-only pages could be triggered from another website**; they now require the anti-forgery token.
- **SNMP-over-WAN also exposed SNMP to guest and IoT networks** — now pinned to the WAN interface.
- **Two DHCP-reservation paths and the connection daemon could be fed router configuration or a crash
  through a device-supplied field** — all now validated.
- **UPnP could be used to hijack the router's own VPN or file-server ports** — when the router runs a PPTP VPN
  or an internet-facing FTP server, UPnP now refuses a device's request to map those external ports to itself.
- **Blocking an IP now cuts its live connection at once** — a manually banned host used to keep any already-open
  connection until it timed out; those are now severed when the ban is applied.
- **A flood of oversized requests could hang the whole web interface** — an unauthenticated request claiming a
  two-billion-byte body would pin the CPU; those reads are now capped (genuine large uploads are unaffected), and a
  companion off-by-one past a request-path buffer was fixed.
- **The advisor's arming second factor could be reset from an ordinary settings save** — its salt, hash, lockout
  counters and USB enrolment were in the general settings table; they are now written only by the arming screen.
- **The firmware update check trusted the published manifest blindly** — every field (URL, version, checksum, size)
  is now validated before it is stored or shown, and the firmware page renders them safely.
- **Ejecting a USB disk could be triggered from another website** — it now carries the anti-forgery token.
- **The first-boot password screen could be set by a cross-site request** while the password was still default — it
  now requires the anti-forgery token in exactly that window (post-setup changes are unchanged).
- **A firewall rule with an over-long field silently widened** — it is now dropped and logged instead.
- **SNMP now answers only on the main LAN address** (not on guest/IoT VLANs), plus smaller hardening — the analytics
  history log will not follow a symlink, the advisor reclaims a stale diagnostic lock on start-up, and the export
  screen caps its free-text fields.

Honestly stated: a systemic issue is deliberately held for the next pass — the router's scratch
directories are created without verifying they are owned by root, which on a box that runs almost everything
as root is the second half of several of the findings above. Two applied fixes carry a caveat: the QoS
priority correction was reverted (above) and needs a hardware session, and the first-boot password protection
should be checked on a real factory-reset flow before this is cut. A handful of smaller hardening items and
two architectural questions (the order the firewall layers run in, and how the device gate behaves across
separated networks) are open and tracked in the Backlog.



### A tagged WAN line can no longer undo the 1500-byte PPPoE fix

A field report on a GT-BE98 showed the symptom v2.4.9 was written to fix, on a line where the
provider requires VLAN tagging: the physical WAN port had been widened to 1508, but the tagged
interface sitting on top of it — the one the PPPoE session actually runs over — was still 1500, so
the session came up at 1492 and a full-size ping still failed. **v2.4.9 fixes that report.** Most
lines have no tagged interface at all and never showed this shape; on those, the port itself was the
thing that snapped back.

What the tagged case exposed is worth removing anyway. A tagged interface cannot be made wider than
the one underneath it — the kernel refuses rather than widening the one underneath for you. The
firmware widens both, in the right order, but it only *records* the width of the tagged one. The one
underneath held its width for the rest of the session purely because nothing else ever re-applied a
width to it. Nothing in the firmware lowers it today; the point is that the correctness of a tagged
PPPoE line rested on that continuing to be true, in two steps whose ordering was never written down
as mattering. A later change could have broken it silently, and only for people on tagged lines.

The width underneath is now re-established at the moment the recorded WAN width is applied, so the
two can no longer drift apart whatever order things happen in. It only ever widens, never narrows,
and only for the WAN interface — tagged interfaces elsewhere on the router are untouched. If the one
underneath ever cannot be widened, the log now says so and names it, rather than the connection
settling for 1492 without comment.

### Two smaller fixes

The dashboard's **Wi-Fi Encryption** row linked to the per-radio Wireless page, which on this build
cannot change the setting the row reports — the main network's security lives in the Network
profile. It now goes there, and falls back to the old destination on builds without that page.

Two **latent translation faults** on the firewall page, neither visible in English. The IPv6
protocol menu submitted its visible text as its value, so translating the labels would have sent a
translated word into the rule format and broken the feature in 24 languages; values and labels are
now separate. And the log table's column headings would have been cut short by any translation
containing an apostrophe — the same fault that broke several European packs in v1.8.6a.

---

## What's new in v2.4.9 — cut, ported to the fleet, not published

*One field report about a PPPoE connection refusing to run at a 1500-byte MTU — and two further
defects found underneath it while working out why.*

### A PPPoE connection set to 1500 now keeps the size you asked for

Reported as a full-size ping test failing: `ping -f -l 1472` is exactly a 1500-byte packet that may
not be split up on the way, so it is the standard way to ask "does 1500 actually work end to end?"

PPPoE spends 8 bytes of every frame on its own headers, so the ordinary ceiling is 1492. A
long-standing extension — RFC 4638, usually called *baby jumbo* — asks the provider to carry 8 bytes
more per frame so the connection can run a clean 1500. Reaper is the only build in this lineage that
offers the setting at all; upstream caps both boxes at 1492, so the only way to ask for it there is
by hand at the command line.

**The cause was not in the PPPoE code.** Running at 1500 works by widening the physical WAN port to
1508 first, and the firmware did that correctly — but it widened the port without *recording* the
new width. The recorded width is what gets re-applied every time anything touches that port
afterwards, and for PPPoE the router asks the provider for an address on that same port moments
later, which touches it. The port therefore snapped back to its old width before the PPPoE session
was negotiated at all; the negotiation found no room for the extra 8 bytes and settled for 1492
without a word, and did so again at every address renewal.

The width is now recorded when it is set, so it survives — and it is cleared again if the connection
changes type or the MTU drops back below the threshold, so a stale 1508 cannot leak into a
connection that should not have one.

**Whether 1500 is actually available still depends on the provider supporting the extension.** That
is not something firmware can change; what has changed is that you now get what you asked for
wherever it is supported, and are told plainly when it is not.

**This is not the LAN "Jumbo Frame" setting.** That is a separate feature, on a different page, and
it has no bearing on a whole-path test like the one above — the two are easy to conflate and were.

### The MTU and MRU boxes are treated as the pair they are

They are the outgoing and incoming halves of a single negotiation, and the extension is only
*requested* when **both** exceed 1492 — the router asks for the smaller of the two. Setting one to
1500 and leaving the other at its 1492 default was a silent no-op: nothing was requested, nothing
was refused, and the page gave no hint that the two boxes were related.

Raising either one now raises the other to match — as you type, when you save, and on both variants
of the WAN page. Values at or below 1492 are left exactly as entered, and the defaults are unchanged
at 1492, so this stays opt-in and is invisible to anyone not looking for it.

### The log says what the connection actually got

When a PPPoE link comes up it now records the MTU it settled on, and where more than 1492 was asked
for and not granted, it says so explicitly — that is the provider declining the extension rather
than the router discarding the setting. That fallback was previously silent, which is the whole
reason the original report was hard to place: nothing on the router distinguished "your setting was
thrown away" from "your provider does not offer this."

### A second internet connection never had its MTU applied

Found while tracing the above. A loop meant to check each configured connection in turn was asking
about the first one every time — a variable was read before it had been given a value, and the
compiler settled it to zero, so every lookup answered for connection one regardless of what was
asked. It has been present for as long as the code has and can only show on a dual-WAN setup.

---

## What's new in v2.4.8 — cut with v2.4.9, ported to the fleet, not published

*Two field reports, two owner requests, and one regression from v2.4.6. Built on RT-BE96U in both
variants so the changes could be seen working. It was not cut on its own: patches 0455–0460 went out
inside the v2.4.9 series, which is also how the four siblings took it.*

### Your addons are listed in the menu on every page, not just the dashboard

Reported plainly: on the dashboard, ntpMerlin, spdMerlin, scMerlin and the rest each get their own
menu entry; open any other page and all of them are gone, replaced by a single **Addons** link.

Both menus read the same file, but different code draws them. Addons register themselves as *tabs*
underneath one parent entry — the right shape for every other section of the menu, and the wrong
one here, because the side menu draws one entry per section. The dashboard is the one top-level
page that builds its own menu, and it had already been taught to open that section out, so the two
menus disagreed and the dashboard was the one that was right. The side menu now expands it too:
a heading, then one entry per addon, framed by the same handler as everything else.

That file is the one third-party addons write themselves into, so nothing in it is trusted. Names
are escaped rather than rendered as written; a target that is not a plain page on the router itself
opens in a new tab instead of being drawn inside the interface — a third-party "Help & Support"
entry is a real case. A router with no addons installed emits nothing at all, not even a bare
heading, so its menu is byte-for-byte what it shipped with.

### The About mark stays on screen when the menu gets long

It is pinned to the bottom of the *menu*, which is where it belongs and is not the same thing as the
bottom of the *window*. The menu deliberately has no scrollbar of its own — it grows with the
document and scrolls with the page, which is what keeps one scrollbar on the right instead of two —
so with several addons installed the menu runs past the bottom of the window and takes the mark
with it: still at the bottom, just not a bottom anyone can see without scrolling to the end of the
page. Listing addons individually, above, made the menu grow by a row per addon rather than a row
in total, which made this worse on exactly the routers most likely to hit it.

The mark now holds its place at the foot of the window while the menu slides beneath it, and
releases back into its natural position at the true end of the list — so it is never detached from
the list it belongs to. On a menu that fits the window it costs nothing and renders identically to
before.

### The temperature and QoS diagnostics graphs fill left to right again

Reported as "they load right to left". **The axis was never inverted** — newest on the right, oldest
on the left, correctly, in both. What was backwards was the direction the trace *grew* while the
history was still short.

This is a v2.4.6 regression, from the change that made these graphs flow instead of stepping.
Placing each reading by *when it arrived* anchors the window to "now" at the right-hand edge, so
the first reading of a run is drawn at the right edge and the trace extends leftward as history
accumulates. The index-based code it replaced began at the left and grew rightward, simply because
a half-full history had fewer entries. Same picture once the window is full; completely different
first minute — which is the whole of what someone watching a page load actually sees.

Both graphs now scale across only the history they actually hold until a full window has elapsed,
so the oldest reading sits at the left edge and the newest advances rightward, reaching the right
edge exactly as the window fills. From that point the behaviour is identical to v2.4.6. The
vertical scaling — its rounding to sensible values and its hold before shrinking — is deliberately
left running on real time, so the smoothness v2.4.5 and v2.4.6 bought is kept intact.

### The Reaper settings explain themselves behind a "?" now

On **Tools → Other Settings**, the three Reaper rows printed their entire explanation as text beside
the control, so a one-word dropdown sat next to a full sentence — while the stock rows on the same
page put their help behind a marker you click. The page disagreed with itself halfway down.

The setting's name now carries a small **?**; clicking it discloses the same text in a panel under
the control. The wording is unchanged — this only moves where it renders. It is reachable by
keyboard and announces its state to a screen reader. It deliberately does not use the stock help
popup: that indexes numbered arrays in a shared stock file, which makes every entry added there a
merge conflict waiting for the next upstream drop, and these strings already exist in Reaper's own
dictionaries.

### You can choose which hour the scheduled firmware check runs in

On the **Firmware** page, a time picker appears when **Scheduled Check** is switched on, and saves
with it — there is no second Apply button, and no state where a time is set but the check is off.

There was nothing to expose before this, so it had to be built. The check has always fired at an
hour and minute drawn at random once per boot, landing somewhere between 02:00 and 05:59 and moving
every time the router restarts, with nothing user-visible and no setting behind it. The new setting
pins the **hour**; leaving it on **Automatic** is exactly the old behaviour.

**The minute stays random either way, and that is deliberate rather than an omission.** The check
pulls a manifest we host, so a time users could name to the minute would let a fleet converge on
one — and the default would concentrate hardest of all. Pinning the hour is what the request is
actually about: check overnight, not in the middle of the working day. A junk or out-of-range value
falls back to automatic rather than failing closed, so a bad setting can never stop the check
running.

---

## What's new in v2.4.7 — cut, not yet built or published

*A small rung: two things v2.4.6 left half-finished. No behaviour changes at all — one label and
one log line.*

### The "settings will not save" switch now says what it is

On **Tools → Other Settings** it read *"nvram netlink workaround"*. That is accurate about the
symptom and useless for finding it: the switch has existed since the previous rung and has been
**on by default** since the day it was added, but nothing on the page identified it as the socket
bind shim, and nothing said which way it was set out of the box. It was asked for twice as a
missing feature — which is the clearest possible evidence that a setting you cannot recognise is,
in practice, a setting you do not have.

It now reads **"Socket bind shim (nvram netlink)"**, and the description states that it is on by
default. Nothing about the behaviour changed.

### Enabling IPv6 pinholes no longer switches off the UPnP diagnostic

The router records which version of its gateway description it gave each device that asked, and
what that device calls itself. That single line is the most useful evidence there is for working
out why a games console will not open its ports.

There are two UPnP programs, and the router runs one or the other depending on whether IPv6
pinholes are switched on. The logging had only ever been added to one of them — so turning on
pinholes moved you to the program without it. That was exactly the wrong way round: the pinhole
program is the one that describes itself in the newer way consoles misread, so it is both the
configuration most likely to need diagnosing and the one that could not be. Both now log
identically.

---

## What's new in v2.4.6 — cut, not yet built or published

*The rung is cut and the four siblings are ported. No image exists from it yet;
these notes are written while the reasoning is fresh.*

**Two field reports drive this rung**, and they are unrelated to each other except
that both had been resisting the obvious fixes for a while.

### A games console could not use UPnP

Reported repeatedly against Call of Duty — "Networking failed to start" — and it
survived every restart-UPnP-and-delete-the-leases suggestion, because **the console
was never getting as far as asking for a port.** Two separate causes, both fixed.

**The router advertised a service it does not have.** It answered discovery requests
for the old dial-up-era "PPP connection" service, which it has never implemented. A
console that asked for that one first was told "yes, over here", followed the
pointer, found nothing it recognised, and gave up — before requesting a single port
forward. A dead end during introductions, not a refusal, which is exactly why it
looked so unlike a port-forwarding problem and why clearing leases never helped.

**And the router now introduces itself as the older, more widely understood kind of
gateway again.** A newer description had been adopted to gain two conveniences,
chiefly *"this port is taken, give me any free one"*. But that newer description is
misread by real consoles, and the fix for that had already been to describe
ourselves the old way to every client — which is precisely what withdraws those two
conveniences. The build was paying the entire price and keeping the entire risk. The
router now says one consistent thing about itself, in discovery and in its own
description alike.

**IPv6 pinholes are unaffected.** They can only exist under the newer description, so
turning them on still switches the router to it — one coherent arrangement either
way, chosen by that single setting. The separate "advertise the newer description"
option has been removed: with this change there is nothing left for it to select, and
a setting that cannot take effect is worse than no setting.

**Being straight about what this does and does not prove:** both changes are
correct and both remove real dead ends, but neither has yet been confirmed against
the reporter's console. The router now logs which description it served and to
whom, which is the evidence needed to close the report properly.

### Flashing a mesh node left it showing a blank page

An AiMesh node deliberately restricts its own web interface to a short list of
pages. That is ASUS's design and it is right — a node is configured from the main
router. Reaper's theming redirects each page to its own interface, and the node's
interface is not on that list, so the node bounced the redirect back to where it came
from, which redirected again. Neither side was wrong alone; together they had no
exit. Because the redirect runs before the page draws, what you saw was a blank
window with a cycling address bar rather than anything resembling an error, and the
login page could never be reached. The node's own firmware-update page was caught the
same way, so a node in that state could not be recovered through its own interface.

Reaper's theming now stands aside completely on a node, which leaves the stock
AiMesh node page — what a node is meant to show.

**This is not the first-boot login loop fixed in v2.2.0.** Different cause entirely,
and this one only ever affected mesh nodes.

### Settings that only existed as hidden values now have controls

Three of them, on **Tools → Other Settings**. The **workaround for a Broadcom defect
that can leave settings unable to save until the router is restarted** is the
significant one, and it is now **on by default** — previously it had to be switched
on by hand, and almost nobody knew it was there. Alongside it, the **theme switch**
for anyone who wants the stock interface back without reflashing, and the
**schedule for Warden's threat-feed refresh**.

Two defects in that page were fixed at the same time: the Warden schedule could be
saved and would **never take effect** (the page restarted three services, none of
them Warden or the scheduler), and **every save restarted the web server** and
logged you out, including saves that changed only a connection timeout.

A **"Disable Asusnat tunnel" switch was removed** — the daemon it offered to disable
is not compiled into this firmware and no such program exists in the image, so it was
an offer to turn off something that was never on.

### Smoother graphs, a calmer flashing screen, and a diagnostic bundle that covers more

The **QoS diagnostics and system-information graphs** had the defect the Traffic
Analyzer shed in v2.4.5 — points placed by position in the list rather than by when
they arrived, so each reading shoved the whole trace sideways in one jump. The
temperature graph was the worst in the build. Both now place readings by time and
redraw continuously.

The **firmware flashing screen** no longer displays internal polling detail that had
reached the screen by accident, and no longer offers a Close button *while the router
is being written* — dismissing it cannot stop a flash, and it hands you a
normal-looking page over a router rewriting its own storage. It still appears at once
if something genuinely fails.

The **diagnostic report** now captures the firewall and the dataplane accelerator. A
connectivity report could not be answered from a bundle at all, because neither was
collected. It also **redacts e-mail addresses**, which it previously did not — the
redaction only examined settings whose name implied sensitivity, so an address in a
log line went through untouched — and the finished report is re-scanned and marked
either clean or "review before sharing".

### An About page that can prove what it claims

Reached from a small scythe mark at the **bottom of the menu**, on every page. Not
a menu entry — it costs nothing to anyone who is not looking for it.

It carries the credits this project owes: **RMerlin**, whose Asuswrt-Merlin every
line of Reaper is patched on top of, and the testers and bug reporters who have
shaped more releases than they probably realise. Alongside those, the project
links, the licence position, and a way to contribute for anyone who wants to.

**Above all of it, the page states its own provenance** — the number of patches
applied, the exact upstream commit they were applied to, the date the image was
built, and the three commands that rebuild that image from scratch. Most router
firmware asks to be trusted. This one can be checked, and the page hands you what
you need in order to check it.

Those figures are **written by the build**, not typed into the page. That is the
difference between a claim and a fact: they describe the image actually running,
not whatever was true when the file was last edited. A missing value renders as a
dash rather than a stale number.

---

## What's new in v2.4.5

**Six field reports, and one thing found while fixing them.** Nothing in this rung
changes how the router forwards, filters or shapes traffic — it is display, logging and
language work, plus one long-standing annoyance in the built-in speed test.

### The live graphs move smoothly now

The Traffic Analyzer's live graphs advanced in visible steps. **The update rate was not
the cause,** which is why turning it up would never have fixed it: each point was placed
by its *position in the list* rather than by *when it arrived*, so every new reading shoved
the whole trace sideways by one slot — a jump of just under 1% of the graph width, once per
update and never in between. Even polling as fast as the router can answer, the graph would
still only exist at ten positions a second.

Graphs are now drawn on the display's own refresh, with each reading placed by its arrival
time, so **how often data comes in and how often the picture is drawn are no longer the same
thing** — and a reading arriving slightly late becomes a smooth glide rather than a stutter.

The vertical scale was a second and independent source of jumpiness: recalculated from
scratch on every update, so the moment a peak scrolled off the left edge, *every* point on
screen moved. It now steps between round values and waits before shrinking. Coming back
from a history window no longer draws a long ramp across the gap that never happened.

### The dashboard stops pushing itself off the screen

On some screens the dashboard ran past the right edge and cut off the **Logout** button.
On smaller windows something worse and much quieter happened: **the "new firmware
available" notice disappeared entirely.**

One cause behind both. The row of small status pills across the top cannot wrap, so its
full width set a floor for the whole page; adding the firmware badge to that row pushed the
page wider than the window on screens in a particular band — a 1920 monitor at 110% display
scaling sits squarely in it. Below that band, the dashboard's own rule for dropping pills on
narrow windows counted the update badge as a pill, so on any window narrower than about
1700 pixels the update notice was simply hidden.

The page can now shrink as intended, so the pill row clips instead of pushing, and the
firmware notice has moved out of it into a **full-width banner at the top of the dashboard**
— visible at every window size.

### Your addons appear in the dashboard menu

If you run amtm, Diversion, scMerlin or similar, their menu entries appeared on every page
*except* the one you land on. Every other page is drawn inside the app frame, which builds
its menu from the same file addons add themselves to; the dashboard is the one page with a
menu of its own, and that menu was fixed at build time — it never had the mechanism.

It now reads the same file the rest of the interface does. That file belongs to third-party
software, so everything in it is treated as untrusted: only plain links to pages on the
router itself are accepted, anything else is **dropped rather than cleaned up**, and nothing
from the file is ever executed. If it cannot be read, or does not make sense, the menu stays
exactly as it ships.

### Warden: outbound blocks are now distinguishable, and the breakdown is readable

- **Outbound blocks could not be told apart from inbound ones in the system log.** Both
  directions ended at the same place, so every entry carried the same label — there was no
  way to answer *"is it blocking what my devices are reaching?"* from the log. Outbound now
  has its own label and its own counter, reported separately instead of folded into the
  inbound total.
- **The breakdown of what was blocked was crammed into a card too narrow to hold it.** The
  figures that let you reconcile the big "blocked hits" total — countries, threat feeds,
  manual blocks — sat under that number in a box about 150 pixels wide, wrapping across
  three lines and breaking mid-separator. They now sit on one line directly above the
  country table they explain, styled as readings rather than prose so they are not mistaken
  for the paragraph above them.
- **Those four labels were still in English in all 24 non-English languages.** Unnoticeable
  as small grey text; obvious once given a line of their own. Now translated.

### The speed test: one cause fixed, a second one named

The page tolerates a number of error lines from the speed-test program before it declares a
run failed. That tolerance was only ever reset when a run **finished** — never when one
**started** — so every test in a session inherited whatever the earlier ones had used up.
After enough tests a run began with none left and gave up on the first error line it saw.
Reloading the page cleared it, which is what made it look random rather than progressive.

**Be clear about what this does and does not fix.** It does not change *why* the speed-test
program reports errors, and it is not what fixed the page freezing mid-test — that was the
earlier change from synchronous to asynchronous result polling. It fixes exactly one thing:
later tests in a session failing sooner than earlier ones.

**Named but not fixed here — and it is probably the bigger one.** That same tolerance is
consumed once per *poll*, not once per *error*. The page re-reads the program's output every
200 ms and re-examines the same entry each time, so one error line sitting at the end of a
stalled output burns the allowance at **five per second** — a nominal fifty is gone in about
ten seconds. That fits a test dying mid-run on the *first* attempt of a session far better
than the counter leak does. Changing it alters how a run is bounded rather than resetting a
counter, so it is not being slipped into a rung that is already cut; it is recorded in
[`BACKLOG.md`](BACKLOG.md) with the fix shape and the reason the existing overall timeout
still bounds a genuinely stalled run.

### A few controls were stuck in English

The Drop/Accept/Both options on the firewall's logging selectors, the QoS diagnostics page
title, and two top-bar buttons were written as plain text rather than as translatable
entries, so they ignored the language setting. **Known and not fixed here:** the firewall
page's own vocabulary — 244 entries — has never had a translation pass, so that page reads
in English in the other 24 languages. Translating one option of a selector whose other
options are English would read worse than leaving the set consistent, so it is tracked as
one job rather than done piecemeal.

**Validation:** 439 patches, gapless, full-series replay verified against the pinned base.
The four siblings are ported. Per-item detail in [`CHANGELOG.md`](CHANGELOG.md).

---

## Hot fix — v2.4.4: IPv6 traffic is now counted per device in the Traffic Analyzer

**A field report on an RT-BE88U:** the WAN line showed **978 Mb/s** while the device
actually pulling that download showed **521 kb/s**. The totals were right; the device
list was not. The reporter's own reading was exactly correct.

**The Analyzer counted IPv4 only, per device.** The collector reads the kernel's
connection-tracking table to decide which device each byte belongs to, and it skipped
every IPv6 connection outright. Those bytes still reached the WAN figure and the
per-network figures — which is why the totals always looked right — but they were
credited to **no device at all**. On a router handing out IPv6 that is most of a modern
client's traffic, and it is worst for exactly the devices people notice: a phone pulling
from a service that prefers IPv6 barely registers against a saturated line.

### Why this needed real work rather than a one-line change

For IPv4 the router finds the device by looking the connection's local address up in its
ARP table. IPv6 has no equivalent file, and because IPv6 is not translated the way IPv4
is, **either end of a connection may be the local device** — a subnet test cannot tell
them apart. The collector now asks the kernel directly for its IPv6 neighbour table and
checks both ends against it, keeping only neighbours behind one of the router's own
bridges: a neighbour reached over the internet connection is your ISP's router, not a
device of yours, and giving it a row would be wrong.

Devices are matched on their **hardware address** — the same key the IPv4 side already
uses — so a device using both IPv4 and IPv6 appears as **one row**, not two. The router's
own IPv6 traffic goes to the "Router" row, and the per-network figures pick IPv6 up as
well, so the per-bridge numbers now reconcile with the WAN line too.

*Known edge:* a device with **no** IPv4 traffic at all shows a blank address until the
network map names it. The row still counts correctly — it is keyed on the hardware
address, not on either of the device's addresses.

### Two related corrections in the same release

- **The "By QoS class" chart now says "Upload only".** The hardware QoS engine shapes the
  upload direction only, so that chart can never show a streaming device's *download* —
  a fair source of confusion, since several devices streaming video barely register on
  it. The caveat existed but sat at the end of a FAQ answer; it is now a badge on the
  chart, with the reason on hover.
- **The FAQ answer about where the numbers come from was wrong twice over.** It still
  described the accelerator-table source that v2.3.3 replaced with connection tracking,
  *and* it told users IPv6 was "not yet split per-device" — now the opposite of what the
  router does. Rewritten. The non-English translations of the old text were discarded
  rather than left asserting the reverse of the truth, so that one answer reads in
  English in the other 24 languages until it is retranslated.

**Validation:** built on RT-BE96U, both variants (20 pass / 0 warn / 0 FAIL each), and
both images decomposed to confirm the payload from inside the filesystem rather than from
the build tree. The four siblings are ported and are for CI. Per-item detail in
[`CHANGELOG.md`](CHANGELOG.md).

---

## What's new in v2.4.3

**The v2.4.2 work, audited before it went anywhere.** This rung carries everything in
v2.4.2 — which published no images — plus the remediation of a security audit run
against it, so **nothing here is a fix to code any user has ever installed.**

The audit covered the shell scripts the router generates and runs as root, the lines
spliced into the DNS service's configuration, the JSON the web interface parses, the new
pages, and the traffic daemon's output. It came back **clean** on what would have mattered
most: no command injection into the generated scripts, no directive injection into the DNS
configuration, no cross-site scripting in the new pages, no new listening service, and
correct cross-site request protection on every control that changes a setting.

### Six defects found — all in code v2.4.2 introduced, all fixed

| | Defect | What it did |
|---|---|---|
| 1 | Malformed mesh-client file | Could **crash the web interface** — the wired/wireless check validated the file's shape at two of its three levels, and the web server runs with full privileges. Latent: it first requires the ability to write into the router's temporary directory. |
| 2 | Website-name block rule with many names | Could **stop DNS and DHCP for the whole network.** The code reading the generated DNS line used a smaller buffer than the code writing it, so a long list was cut in half — leaving either a rule that silently never matched, or a broken directive that makes the DNS service refuse to start. Both ends fixed: the writer logs any names it had to omit, the reader refuses a partial line outright. |
| 3 | Warden block breakdown | Could **read as zero with two browser tabs open** — the statistics script used one fixed working file and the web interface runs it every thirty seconds, so two sessions overwrote each other and banked zeros. Exactly the confusion the breakdown was added to solve. |
| 4 | Object limit applied in one place, not its match | Past that limit the router asked the DNS service to fill lists it had never created. |
| 5 | DNS configuration fragment | The one file the firewall engine wrote without setting permissions, so it landed **world-writable**. |
| 6 | Two networks sharing one bridge | The guest IoT network sits on the main bridge, which made the traffic graph label the main network with the **guest network's name**. |

### Hardening

- **The router-self filter could be silently disabled.** It exempts your DNS servers
  automatically and read those addresses straight from the resolver file — where an
  address written with a prefix (`0.0.0.0/0`) is *accepted* by the firewall as "allow
  everything" at the top of the chain, disabling the entire self-filter while every status
  indicator still reported it on. A silent-failure mode rather than a leak.

### Deliberately not fixed here

- **The router's temporary directory is writable by every account, with nothing stopping
  one account deleting another's files** — which is what makes defect 1 reachable at all.
  This is stock ASUS/Merlin behaviour affecting every part of the system, including the
  closed-source components. Recorded with two candidate approaches; it is owed its own
  release and its own hardware pass.

**Validation:** built on RT-BE96U, both variants. The four siblings are ported and are for CI.

Per-version detail is in [`CHANGELOG.md`](CHANGELOG.md); earlier releases are summarized in §3.

---

## 1. What Reaper is

Reaper narrows stock Asuswrt-Merlin to the ASUS RT-BE Series (primary model RT-BEXXU,
plus the RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro siblings), **hardens** the
open-source userspace against remote compromise, **removes** cloud-coupled and
AI-branded attack surface, **rebrands** the web UI, and adds a few genuinely-local
router features ASUS never shipped.

**Design goal / threat model:** harden the device so that **only physical access
can compromise it** — eliminate every remotely reachable code-execution, memory-
safety, and injection flaw in the auditable userspace, and cut the cloud/telemetry
surface that a de-cloud build shouldn't have. Closed-source WiFi drivers and
prebuilt ASUS/Broadcom/Trend Micro blobs are explicitly **out of scope** and
documented as residual risk (see §6).

---

## 2. Two build variants — with or without the AI Advisor

Starting with the v1.4 line, Reaper ships as **two images built from the same
source**, differing only by whether the optional AI Advisor (§3) is compiled in:

| Variant | Image | Contains the AI Advisor? |
|---|---|---|
| **Standard** | `RT-BEXXU_…_Reaper_v2.3.7_noMCP_nand_squashfs.pkgtb` | **No — never compiled in** |
| **+ AI Advisor** | `RT-BEXXU_…_Reaper_v2.3.7_nand_squashfs.pkgtb` | Yes (optional, off by default) |

The Standard image contains **zero** trace of the AI Advisor — no daemon, no page,
no menu entry, no settings, nothing hidden or merely disabled. Both are otherwise
identical. Pick whichever you prefer; the AI Advisor is opt-in even in the variant
that includes it.

> Naming note: the build artifacts are `…_Reaper_v<version>_nand_squashfs.pkgtb`
> (**with** the Advisor) and `…_Reaper_v<version>_noMCP_…` (**without**); the filenames
> above show the newest published version, **v2.3.7**. §8 lists the exact filenames and
> their hashes per release.

---

## 3. New since v1.0

### Since v2.3.4 — a firewall of Reaper's own, UPnP consoles can use again, Wi-Fi pages that stop misleading you (v2.3.5 – v2.4.3)

Headlines — per-version detail is in [`CHANGELOG.md`](CHANGELOG.md):

- **v2.4.3 — the v2.4.2 work, audited before it went anywhere.** Six defects found and fixed, all in code v2.4.2 introduced, so none of them is a fix to code any user had installed; see the "What's new in v2.4.3" section above.
- **v2.4.2 — Warden's outbound direction actually blocks, and the firewall pages explain themselves.**
  - **"Outbound" and "both" were blocking nothing.** The whitelist was checked before the outbound rules, and every outgoing connection has one of your own devices as its source — so any whitelist entry covering that device, including the "whitelist your own network" entry this feature's own lockout guidance tells you to keep, skipped the destination checks entirely. Inbound blocking of the same addresses worked perfectly. Destination checks now run first, in a chain of their own, with the loopback / LAN / own-address exemptions the outbound side never had.
  - **Warden can now filter what the router itself sends** (opt-in, off by default) — a compromised router is where a threat feed earns its keep. It cannot lock you out (the web interface and SSH stay reachable from your network), DNS resolvers and time servers are exempted automatically, and every block here is logged whether or not general Warden logging is on. The ceiling: malware with full control of the router can remove these rules, so this is a speed bump and mainly a **detection signal**.
  - **"Total blocked" beside an empty country table is explained rather than fixed.** The total counts every block — manual, feeds and countries — while the table only ever counted countries, and the feed rules are checked first, so the feeds absorb most hits. The total now shows its breakdown.
  - **Every tab of the firewall page explains itself** — what it is for, how it is best used, a worked example you could type in, and a **?** button into the new [firewall guide](FIREWALL-GUIDE.md).
  - **Website-name objects fill themselves from the router's own DNS.** v2.4.1 deferred this on the stated grounds that the DNS service lacks the capability; that was wrong — it has had it all along, and the check had been run against a stock binary from a different model and architecture. The ten-minute timer stays as the floor, since this only sees lookups the router itself answers.
  - Traffic Analyzer per-network rows now carry **name and VLAN** (`Guests (VLAN 52, br54)`) instead of the bare `br54` nobody configures, and **Wi-Fi devices connected through an AiMesh node are no longer listed as Wired** — the router consults the mesh's own client list, so they report the band they are really using.
- **v2.4.1 — a native firewall, UPnP that consoles can talk to again, and mesh nodes you can update from one page.** Folds in the v2.3.8, v2.3.9 and v2.4.0 source rungs — the firewall spanned all three.
  - **UPnP stopped consoles connecting to games** (a PS5 could not reach Call of Duty at all, pinholes on or off) — two faults. v2.3.5 moved every build to describing itself as an **IGD:2** gateway; *discovery* stays backward-compatible but the **description** the client fetches next does not, so a console recognised none of the services, never got a control address, and could not create a mapping. The code already force-downgrades that description for Microsoft clients for exactly this reason; the console simply is not covered by the exception. It is now IGD:1 for everyone (`upnp_igd2_desc=1` restores IGD:2), and because the IGD:1 description omits the IPv6 firewall service entirely, enabling pinholes now implies IGD:2. The router also logs which description each client was served **and what that client called itself** — the fact that was missing when this took a build to diagnose rather than a log line.
  - **An upstream defect carried in the 3006.102.8 base** added an unqualified rule testing every packet crossing the router — outbound included — against every active UPnP mapping, so a mapping on some port rewrote a LAN device's own outgoing connection to a remote server on that port. Reverted.
  - **The native firewall is real, and switched on by choice** (off by default). Rules are written about named objects — a device, a network, a service, a country reusing the list Warden already downloads — across inbound, forwarded and outbound traffic on IPv4 and IPv6, with schedules, rate limits and per-rule logging, **adding** policy on top of the stock firewall rather than replacing it.
  - **You cannot lock yourself out:** every apply starts a countdown and the router restores the previous ruleset by itself unless you confirm, driven by a scheduled task running a pre-written script rather than by the web server, so it still fires if what you just broke is the web interface. A protective set is always applied first, including the IPv6 neighbour-discovery traffic a network stops working without — a rule that killed it would otherwise pass the countdown unnoticed, because the operator's IPv4 session stays up throughout.
  - Per-device internet defaults, source- and schedule-restricted port forwards, a compile preview generated by the same code that would apply it, and text backup/restore round it out. The firewall **Status** page reports posture in five groups instead of 40-odd raw netfilter chains refetched every ten seconds — including the one most people need, **what of yours is reachable from the internet right now** — and the engine's on/off switch reports a **measured** signal (the engine marks itself active as its last act, only when its rules really went on) rather than echoing back the flag just written.
  - Also: **mesh nodes** appear correctly and can be updated from the main router — the page had been filtering itself out of its own node list using a field the router never sends, so **the router listed itself as one of its own nodes**; the setup wizard no longer drops you onto an unthemed stock Wi-Fi page; the dashboard regains the internet switch and USB disk selector the retired Network Map carried; **Devices** exports the client inventory as CSV, JSON or HTML; every dashboard **Security Posture** row links to the page that owns the setting; and during a flash the page behind the header no longer shows through it.
  - **Known and not fixed:** the Professional Wi-Fi page still takes ~15 s on its first load after an upgrade (the mechanism is understood; the fix depends on whether the cost is the page or the driver settling), and the firewall rule tracer is deferred.
- **v2.3.7 — the Wi-Fi pages stop misleading you, mesh nodes show their firmware, and Professional opens quickly.** Five changes, all in the web interface and the small server behind it; nothing touches how traffic is forwarded.
  - **Professional** was asking the router for its wireless settings one at a time — 116 separate questions, none of the page drawable until the last answer arrived — and on a three-radio router 29 of them asked about a fourth radio that does not exist. It now asks once, about the radios the router actually has, and adapts by itself to any model.
  - **Auto Scan now assigns the channel it told you was best.** On 5 GHz it ranked individual narrow channels and then quietly applied the wider block *containing* the winner — so it could report channel 44 as best and set 36. It now measures at the width the radio will really run, takes the channels to sweep from what each radio itself reports rather than a fixed list (so a two-5 GHz-radio router sweeps each correctly and other regions work without a code change), and applies its winner instead of restoring the old channel and waiting for a button. Two consequences, now stated on the page: radar-detection (DFS) channels are deliberately not swept, because each needs a 60-second listening period with the radio off the air — up to ten minutes on some; and applying a channel takes that radio off automatic channel selection until you set its control channel back to Auto.
  - **The firmware page lists your AiMesh nodes** with the firmware each reports and whether it is online, and gives each online node a button that opens that node's own firmware page, where you choose an image and the node flashes itself — the image is never relayed through the main router.
  - **A failed "Search for node" now records why.** Two points discard a discovered node for incomplete information and neither said anything, so the search came back empty with no explanation; both now log the node and exactly what was missing.
  - A **Smart Connect** note claimed 6 GHz is left out by default "on this model", which is true only on some models while the page is shown on all of them; removed.
  - **Built and published on all five models** (2026-08-13, three assets each) through the public clean-room CI pipeline.
- **v2.3.6 — a workaround for a Broadcom bug that can permanently freeze saving settings.** A router can reach a state where saving a setting simply never completes, and the symptom is quiet: the router stays up, SSH and the web interface still respond, traffic still flows — but one process is stuck forever, a CPU core is consumed doing nothing useful, and the setting is never written. It becomes more likely the longer a router has been running.
  - **The cause is in a closed Broadcom library** (`libnvram.so`), found by catching it live on hardware and confirming it instruction-by-instruction in the shipped binary: the library identifies its kernel channel by the process's own ID, and also keeps a record of *"which process am I"* — and those are **the same piece of memory**. Whenever the two disagree it decides the process must have changed and starts over **without closing the channel it already opened**.
  - **Two things make them disagree, and both happen on ordinary routers.** Most background services read a setting before moving themselves into the background, which gives the running copy a new process ID while it inherits the channel opened under the old one — measured on a live router: six abandoned numbers, and four services each holding two channels, twenty-one minutes after a clean boot. Then, because process IDs wrap every 32,768 processes, a new process is eventually handed one of those numbers. *That* is when it retries — and each retry overwrites its own identity record, so a long-running service that keeps saving settings burns all ten slots and then retries a failing operation forever, holding a lock that blocks every further settings operation within that process. The rest of the router carries on regardless, which is much of why this is hard to notice.
  - **Reaper now ships a small shim beside the library** — it does **not** modify it — that asks the kernel to pick a free number after such a failure. This **prevents the freeze, not the abandonment**: the startup case never fails with "address in use", so those channels are still abandoned exactly as before. Fixing the leak itself is Broadcom's to do.
  - **It ships switched off**, since the mechanism applies to every program on the router: `nvram set wlcsm_bindfix=1`, commit and reboot to enable; `0` removes it on the next boot. Each rescue writes a line to the system log naming the process and number, so you can tell whether your router is affected — read it on the **System Log** page or as `/tmp/syslog.log`, not via `logread`, which returns nothing on this platform.
- **v2.3.5 — counters that survive a reboot, UPnP that keeps working, and a first-boot setup you cannot walk past.** Five field reports, all of the same shape: a feature that reported success while doing nothing.
  - **Warden's blocked-hit counts** reset on every reboot and firmware upgrade, and the per-country list never accumulated at all — the totals were only saved by a script that runs *after* the firewall rules are torn down, and the per-country table had no saved copy whatsoever, being read straight from live rules that are deleted and rebuilt whenever anything touches the firewall. That is why the downloaded blocklists survived a reboot while the numbers beside them did not. Both are now banked to flash from every path that would lose them, including a 15-minute checkpoint, and you choose how long they are kept (Never / 24 Hours / 7 Days / 1 Month / 3 Months).
  - **UPnP port mappings** stopped working after a while and nothing said so: any firewall rebuild wipes every mapping, and the router's recovery signal only announced a public-IP change — it re-added nothing, while the service kept telling programs "that port is already forwarded". Consoles losing their NAT type hours after boot, game hosting failing, downloads with no incoming connections: one bug, fixed by genuinely restarting the service so every mapping is reloaded with its remaining lease. UPnP also began presenting itself as an **IGD:2** gateway by default *(reverted to IGD:1 in v2.4.1 — see above)*, and it now **refuses mappings on the router's own** OpenVPN, WireGuard, IPSec, SSH and web-admin ports, closing a path by which a LAN device could quietly take over inbound VPN connections.
  - **DHCP Leases** showed a dash instead of the device name for devices the Devices page names perfectly well — it read from the live network-map rather than from where names are actually stored — and a name or self-reported hostname containing a quote could blank the whole table. Both fixed, which additionally closes a way for a LAN device to run script in an admin's browser by choosing a crafted hostname.
  - **Smart Connect Rules** explains its "- -" columns instead of looking broken. *(Investigating that report also confirmed the page's band mapping is correct — the reporting router simply had 2.4 GHz deliberately excluded.)*
  - **First-boot setup can no longer be skipped, and now actually asks for the Wi-Fi password.** The wizard previously sent you to the dashboard after setting admin credentials, and the dashboard is one of the pages that does not run the Wi-Fi check — so a router could finish setup with new admin credentials and the factory Wi-Fi password still in place — while the wizard itself could be bypassed entirely by typing almost any settings-page address directly. Enforcement now lives in the web server, so every page is covered, and the wizard will not release you until both the administrator credentials and the Wi-Fi password have been changed.

### Since v2.3.1 — the de-cloud finished, the frozen-browser cause found, QoS defaults that match their labels, and traffic accounting that can see offloaded flows (v2.3.2 – v2.3.4)

Headlines — per-version detail is in [`CHANGELOG.md`](CHANGELOG.md):

- **v2.3.4 — the Traffic Manager and Traffic Analyzer pages fit the screen again.** A regression from v2.3.3's own overlay fix: the FAQ panel that slides in from the right is parked just off the edge of the page while closed, and the change that made "please wait" overlays centre on your screen swept that parked panel into the same rule. Its parking then counted as real page width — the page claimed ~460 pixels it did not have, the frame stretched to match, and every panel stretched with it, putting the last column outside the window with no scrollbar to reach it. Only those two pages carry that panel. Fixed, and the content area can now scroll, so a future case pans rather than hiding content.
- **v2.3.3 — no page in the web interface contacts ASUS any more, and two injection paths are closed.** Earlier releases closed the **icon** callbacks; this one closes the remaining **data** surface (FAQ index, DNS-provider list, SDN scenarios, model-name and node-icon tables, timezones, ISP list, IPTV profiles, the Open NAT game database, VPN partner lists, 27 game-artwork URLs), each replaced by the copy already bundled in the firmware — one of them had been retrying ASUS **every five seconds forever** on failure. It is now enforced by the build rather than done once: the packaging gate **fails** if any ASUS-CDN reference reaches the shipped web root in a request-shaped position. Also in this release: the **post-upgrade frozen browser** is explained and fixed (a failed request fires two events, both wired to the same handler, so the flash page's poll chain doubled every round until the tab locked up — v2.3.2's Close button treated the symptom); a **stored XSS** that any device on the LAN could plant through its DHCP hostname and that fired in an administrator's session; the **Data Export** URL/token could inject directives into the download tool's config and write a file anywhere as root; the AI Advisor's **lab** build could return the Wi-Fi passphrase; hardware QoS now ships a **measured classful profile** and stops classifying by **bytes transferred** (which demoted long calls and game sessions into the bulk queue for simply lasting); the **Traffic Analyzer** counts from the kernel's connection table instead of the accelerator's flow list, so fast downloads stop going missing and guest / SDN clients are no longer dropped; **"Please wait" overlays and countdowns centre on your screen** instead of inside the framed page; the **Network Map** is retired and the dashboard takes its navigation slot; the AiMesh node's model name is centred over its MAC; and the Firmware, Data Export and USB/storage strings are translated into all **24** non-English languages, leaving no untranslated Reaper strings.
- **v2.3.2 — QoS finally classifies the way its labels say, and a flash screen you can always escape.** The classful engine's shipped defaults worked against their own labels: unmatched traffic (games included) shared a queue with bulk file transfers, the **DSCP-to-class map was inverted** so a correctly-marked game could never reach the queue named for it, committed minimum rates consumed **100% of the port**, and QoS with empty bandwidth fields armed classification with no shaper at all. All corrected, with the DSCP→WMM stamp made **opt-in**. The firmware page's overlay gained **Close / Esc** and an elapsed-time heartbeat, and the manual upload no longer declares a good image rejected while the router is still verifying it. Four smaller items cleared: the QoS diagnostic read the wrong shaper for the running engine, a VPN-provider path let an apostrophe escape shell quoting, the password check was made constant-time, and the health watchdog rate-limits incident dumps to flash. **First release built and published through the public clean-room CI pipeline** — which also gained the missing step that had left routers reporting "up to date" after a release: the pipeline now refreshes the on-router update manifest itself.

### Since v2.3.0 — a native Firmware page with a working update check and one-click verified install (v2.3.1)

Headlines — per-version detail is in [`CHANGELOG.md`](CHANGELOG.md):

- **v2.3.1 — the Firmware page is now Reaper-native, and the update check finally works.** Administration → Firmware Upgrade is a new Reaper page: installed model / variant / version at a glance, an on-demand **Check** against the Reaper release channel, **inline release notes**, an opt-in **scheduled daily check** (off by default), a **manual upload** with a real progress bar — and a capability the stock page never offered: **one-click download + install** of a published update, with a live download bar and an end-to-end verification chain before anything is flashed (downloads accepted only from the Reaper GitHub release channel; the image must match **this exact model and variant** — a noMCP router refuses an MCP image; the manifest's **SHA-256 and size** must match; the platform's own image check must pass). Under the hood this release also fixes why the update system appeared dead: on AiMesh-config-sync builds (all Reaper models) the stock page's Check silently routed through a closed ASUS helper to **ASUS's servers**, so the Reaper release-channel check (v2.1.6) never ran from the GUI and the dashboard "new firmware" badge never fired; the release-note fetcher also wrote its result where no page read it. Both are fixed on the native page *and* on the stock page, which stays on disk as a fallback. Nothing phones home by default — the scheduled check is opt-in and the only endpoint ever contacted is the Reaper release channel on GitHub. (New firmware-page strings are English in all 25 language packs for now; translation pass planned.)

### Since v2.2.5 — the speed-test freeze fix, a front-end cleanup, and the v2.3.0 feature batch (v2.2.6 – v2.3.0)

Headlines — per-version detail is in [`CHANGELOG.md`](CHANGELOG.md):

- **v2.3.0 — animated header, a standalone health-probe switch, a real "Store only" mode, and one row per device.** The **sign-in / set-password / logout** screens gain an **animated model header** that plays once and freezes on the logo — an **animated PNG** served through the normal image path, so it needs no change to how the login page is served (an earlier `.mp4` attempt never displayed, because a logged-out browser is only served a fixed set of image types on the pre-authentication login page; the dead `.mp4` handler was reverted, leaving that surface unchanged). The per-device **health probe** (round-trip latency / jitter / loss + TCP state) gets a **standalone on/off switch** on Administration → Data Export, **independent of export**, so you can collect and **Preview** the metrics without configuring any external destination (Preview now shows a helpful message instead of empty `{}`). The Long-Term Storage export control now offers **four modes — Off / Store only / Store + Export / Export only** — with the misleading "Off" label fixed ("Off" now genuinely keeps and sends nothing; "Store only" keeps history locally with no external push). A device that could appear **twice** in the metrics / export / Traffic Analyzer — once by MAC, once with its **IP in the MAC field** — is folded to **one row per device** (an unresolved-MAC flow used to seed a phantom IP-keyed entry; it's now merged into the real device and a once-a-second sweep clears any that slipped through). Plus: **Warden's total-blocked count truly persists** across reboots (a boot-time baseline wipe that survived the v2.2.1 fix is closed), the **apply/reboot overlay locks the header + side nav** while a framed page loads, the **update-check log lines are de-Merlin'd**, the **Traffic Analyzer hides its own "Router" self-traffic row**, and the **Roaming Assistant help reads just "0 = off"**. A four-agent **pre-distribution review** found no shipping blockers; its follow-ups were folded in — the Health-probe toggle now **refuses to turn off while an export mode is armed** (which would otherwise freeze the pushed feed), the Storage export note flags that non-off modes enable the probe, and a dead leftover `.mp4` httpd handler was removed. **Built + shipped on all five models, both variants each.**
- **v2.2.7 — internal front-end cleanup (no new features).** One shared device-name resolver (offline devices keep their names on Connections + QoS too, not just the Traffic Analyzer), one decimal-SI byte formatter shared by Traffic + Connections, and unified accent colors across the Reaper pages. A long-standing "spurious leading `<`" review note was verified not-a-bug and closed.
- **v2.2.6 — the Internet Speed Test no longer freezes the browser mid-run.** The live result polling changed from a blocking request repeated five times a second to a non-blocking chained poll, so the page stays responsive through the CPU-heavy download/upload phases and updates smoothly to the finish.

### Since v2.1.9 — connection-health metrics + analytics export, a de-cloud + field-fix batch, and a privacy/polish pass (v2.2.0 – v2.2.5)

v2.2.0, v2.2.1, and **v2.2.5** shipped on **all five models** (both variants); the intermediate v2.2.2 – v2.2.4 rungs were RT-BE96U-only. Headlines — per-version detail is in [`CHANGELOG.md`](CHANGELOG.md):

- **v2.2.0 — first-boot loop fixed for good, Gatekeeper internet-only behind a LAN DNS, USB tools rehomed, de-cloud console cleanup.** The first-boot setup no longer ends in an endlessly reloading login window (the web server re-decides its landing page on every request instead of once at startup, and the wizard exits straight to the dashboard); a power-cycle recovers an already-affected box, no reflash. **Gatekeeper "internet-only"** now works when your DHCP-assigned DNS is a LAN server (AdGuard / Pi-hole) — DNS to that server still resolves while other LAN access and the router's own services stay blocked. The USB disk utilities moved to their own tab. Three de-cloud leftovers were removed: the stock ASUS privacy-policy check (it logged an error on every page), the dashboard client-list's ASUS icon-CDN fetches, and three tooltip fields gained HTML encoding.
- **v2.2.1 — Warden count survives reboots, per-dataset "collecting since", USB scan result stays on screen, dead Security-Update panel gone.** Warden's **total-blocked counter persists across a reboot and a reflash** (banked in persistent storage, not a rule the restart rebuilds). Every enabled Long-Term Storage dataset stamps and shows its own start date. The USB Health Scanner result no longer flashes and vanishes. And the stock cloud **"Security Update"** (Trend Micro signature) panel was removed from the firmware page — Reaper's own GitHub update check is unchanged.
- **v2.2.2 — per-device connection-health metrics + export to an analytics engine.** The traffic collector can now measure, **per device, round-trip latency / jitter / loss** (a batched in-router ping, never one process per device) plus **TCP connection count and state**, alongside the throughput / online state it already tracked. A new **Administration → Data Export** page streams that to **Splunk (HEC), Datadog, Dynatrace, Elastic/Kibana, a generic HTTP/JSON collector, OpenTelemetry, or a TLS syslog target** — or exposes a token-gated **Prometheus** scrape endpoint — with **Test-connection** and **Preview-payload** buttons; the Long-Term Storage page gains **Off / Store+Export / Export-only** modes. Everything is **off by default**, TLS-verify is **on by default**, the API token never appears in the process list or logs, and an optional switch hashes device MACs before they leave. The per-device capacity was raised 64 → 192. Also in this build: the **USB Health Scanner now actually scans ext4** disks and reports a real pass/fail verdict.
- **v2.2.3 — live Traffic Analyzer graph smoothed on large networks.** Fixed a micro-stutter that appeared after the 64 → 192 device-cap bump: the per-connection device lookup on the five-second update was a linear scan; it is now constant-time. Independent of the health probe, so everyone benefits.
- **v2.2.4 — the connection-health probe made light enough to leave running.** The opt-in probe (still **off by default**) could stutter the live graph and dip a speed test once enabled on a busy 100+ device network; the work is now spread across many collector ticks (a bounded slice of the connection table per tick, ≤16 pings per tick), history is staged in RAM and flushed on the hourly save, and a saturated WAN defers a cycle so the probe never competes with a speed test. Default probe interval relaxed 30 → 60 s.
- **v2.2.5 — privacy and polish.** The **Wi-Fi key is masked** on the post-apply reconnect card; **three more ASUS-cloud icon callbacks are removed** (bundled icons used, so viewing those pages no longer tells ASUS which devices/apps you have); the **loading / reboot overlay now covers the whole screen** (the nav and header are no longer clickable mid-apply); **offline devices keep their names** in the Traffic Analyzer 24h / week / month history; and more of the UI is translated (the AI Advisor intro completed and a Warden note translated across all 24 non-English languages, and the Connections "Quick Look" labels localized). A **five-agent pre-release review** of the v2.2.4 + v2.2.5 changes found **no critical / high / medium** defect; the one low — a single self-healing file descriptor held if the opt-in probe is disabled mid-scan — was fixed.

> **Known limitation (GT-BE98, not fixable in Reaper).** Creating a Guest Network Pro network with AP isolation *while a manual WAN VLAN is in use* can stop the 2.5 Gbps-1 LAN port from passing untagged main-LAN traffic (an 802.1Q tag becomes required). Investigated on-metal in depth — the hardware VLAN programming is a closed Broadcom/ASUS component with **no software interface to read or correct it**, so it cannot be fixed in the Reaper firmware (and almost certainly affects stock ASUS the same way). Workarounds: keep Guest Pro off that port, move the device to another LAN port, or tag it VID-52.

### Since v2.1.0 — localization, an upstream carry-forward, feature adds, and field fixes (v2.1.1 – v2.1.9)

The rungs after v2.1.0 are RT-BEXXU-first; since v2.1.4 the fleet ships every rung on all five models in parallel (RT-BEXXU carried v2.1.3 alone, then the siblings were brought straight to v2.1.4). Headlines — per-version detail is in [`CHANGELOG.md`](CHANGELOG.md):

- **v2.1.1 — localization, defense-in-depth, and UI polish.** The last hardcoded-English error messages on the Devices and AI Advisor pages now localize into all 25 languages. The AI Advisor daemon's secret-redaction is now applied structurally at its single output point (so any future tool is covered), and oversized tool output always returns valid JSON with a truncation marker. Three pages gained extra output escaping (defense-in-depth). The Warden threat/geo block-lists load in one batched operation instead of one process per address. Three pages (Connections, QoS Diagnostics, all-bands Professional) that sat shifted right now fit the frame, and Channel Lock gained the same confirmation Unlock already had.
- **v2.1.2 — Asuswrt-Merlin 3006.102.8 carry-forward.** The upstream fixes Merlin landed between the pinned beta base and the final production release are folded in: **OpenVPN 2.7.5** (the 2.7 line — deprecated server options removed; test any server config), **dropbear 2026.94**, a strongswan build fix, a miniupnpd update, IPv6 prefix-length corrections, and web-UI fixes (incremental client-list redraw, iOS DHCP export). Pure upstream carry-forward; carried commits keep their original authorship. The base stays pinned to 3006.102.8-beta2 — the carry-forward is by cherry-pick, not a base rebase, so the corresponding-source recipe is unchanged.
- **v2.1.3 — Connections "Quick Look", baby-jumbo PPPoE, a stored-XSS fix, and UI polish.** The Connections page now opens on a simple at-a-glance list (device name, local IP, remote IP:port, an internal-vs-external badge, protocol, TCP state), with the live flow explorer retained as "Advanced" (now with a Pause option); a single slider switches modes. The WAN GUI now permits a 1500-byte **RFC 4638 baby-jumbo PPPoE MTU** for full-fibre lines (opt-in; defaults unchanged). A reachable **stored XSS** in the *stock* client list — a device name containing an apostrophe could break out of a single-quoted HTML attribute on a page the admin views — is closed by additionally apostrophe-encoding the name. Plus three touch-ups: the Wireless Professional page no longer prints raw nvram variable names, the AI Advisor intro sentence is completed, and dashboard SSIDs show in real mixed case.
- **v2.1.4 — factory-reset lockout, WireGuard peer-row, OpenVPN label.** A factory-fresh box could get stranded when the stock ASUS "Change router login password" page collided with Reaper's own first-boot credential page (the second attempt failed "Could not apply credentials"); Reaper now routes a default-password box straight to its single first-boot page. The WireGuard client peer list's three-dots edit toggle is centered and no longer clipped. And **OpenVPN now reports 2.7.5** — the 2.7.5 binary had displayed "2.7.4" because a stale generated build file froze the version label; regenerating it corrected the display (behavior was already 2.7.5).
- **v2.1.5 — three field-report fixes.** The **1500-byte PPPoE MTU is settable from the GUI** (the v2.1.3 raise had landed on a WAN page variant that doesn't ship; the shipped page still capped at 1492 and silently clamped a hand-entered 1500). The **first-boot credential page is self-recovering** (a stale or back-navigated copy can no longer reject every input when the password already applied). And **Traffic Analyzer history genuinely survives reboots on both stores** — USB had lost all history every reboot (the collector looked for its database before the stick mounted, then overwrote it); it now waits for the store, restores, never overwrites an unloaded database, and saves every 15 minutes on USB (JFFS stays hourly for flash wear).
- **v2.1.6 — update notifications, real IPv6 on the dashboard, Warden/watchdog fixes.** The router can now **notify you when a Reaper update exists** — opt-in and notify-only: the stock check compares only the shared Merlin base number so it could never see a Reaper release; the new check reads a Reaper-published GitHub manifest, knows your model *and* variant, and lights a crimson dashboard badge (off by default; talks only to the Reaper GitHub tree; never downloads or flashes by itself). The **dashboard shows your real WAN IPv6** — on native/DHCPv6-PD lines the global lands on the LAN bridge and the card had fallen back to the `fe80::` gateway/link-local; it now uses the bridge global, the same source as the stock IPv6 status page. **Warden's total-blocked counter survives firewall restarts** (banked into a running baseline instead of a rule the restart rebuilds), the **health watchdog** no longer flags a phantom `wan-gw` failure behind an ICMP-filtering first hop, the non-functional **"B/G Protection"** control is removed (stock driver force-resets it to Auto), and two menu labels (RU/TR) no longer show raw HTML entities.
- **v2.1.9 — unified device naming, flash-proof Traffic Analyzer history, a USB disk panel, the siblings' PPPoE-1500 catch-up, a WAN-MTU rollback, and a code-audit hardening pass.** Device names now come from **one master list on every page** and renames stick: three defects are fixed (removing an offline client could wipe every custom name after a reboot; a Devices-page rename appended a duplicate record so first-match pages kept the old name; the stock rename popup could roll back names changed elsewhere from its stale snapshot) — existing duplicates self-heal on reboot. **Gatekeeper is name-first** now (self-reported hostname only as fallback) and the **DHCP-leases log gains a unified Device Name column**. **Traffic Analyzer history survives firmware flashes** (phantom-mount guard + late store re-attach), the **Long-Term Storage tab gains a USB disk panel** (info, health scan, format, eject), the **sibling models finally accept PPPoE MTU 1500 in the GUI** (the v2.1.5 fix had shipped only on the RT-BEXXU image due to a port-process gap, now closed permanently), and the **WAN-MTU field's 1508 allowance is rolled back to 1280–1500** (it only renders on automatic/static-IP WANs where 1508 is invalid; PPPoE keeps 1500 with the automatic PPPoE-only +8 on the physical interface). Finally, a **full code audit of the Reaper sources** (four parallel reviews + a deterministic cross-model parity check) found **no critical or high-severity defect** and its confirmed fixes were folded in: three self-themed pages no longer receive the stock CSS injection; the QoS-diagnostics page carries the shared anti-forgery token before its diagnostic subprocess; the QoS page pauses polling while hidden; DHCP reservations/pool edits store the canonicalised address; an uninitialised boot-normaliser read is fixed; and delete can no longer drop an over-long neighbouring record. First cut as v2.1.7, respun as v2.1.8 for the WAN-MTU rollback, then v2.1.9 for the audit fixes — neither v2.1.7 nor v2.1.8 was published.

### Since v2.0.0 — de-cloud completion, the Samba 4 file server, secure defaults, live diagnostics, and a pre-release hardening pass (v2.0.1 – v2.1.0)

The rungs from v2.0.1 to **v2.1.0** continued **RT-BEXXU only, both variants**. Headlines
— per-version detail is in [`CHANGELOG.md`](CHANGELOG.md):

- **De-cloud completion + the Samba 4 file server working (v2.0.1 – v2.0.2).** The ASUS **AWS-IoT**
  phone-home and **account-binding** surface — quietly re-added by a config generator after the earlier
  phone-home cleanup — is now removed from the build entirely. The **Samba 4** SMB3 file server, which
  shipped in v2.0.0 but never actually started (packaging bugs), now starts on boot and signs you in
  cleanly from a fresh boot, with tidier share names and a proper login prompt.
- **Router-generated Professional page + secure factory defaults (v2.0.3 – v2.0.4).** The all-bands
  Professional page now builds its columns from the router's real radio list (correct on quad-band
  models). Factory-reset defaults are hardened: **WPS is off** and the **UPnP master switch is off**
  out of the box (everything else unneeded was already off or compiled out).
- **Live hardware insight — QoS Diagnostics + a Connections flow explorer (v2.0.5 – v2.0.8).** A new
  **QoS Diagnostics** page shows the hardware traffic manager live (per-queue occupancy, drops,
  estimated delay, scheduler); the **Connections** page became a live per-flow explorer drawn from the
  Runner flow accelerator (hardware-vs-CPU split, DSCP, egress queue, live throughput, true connection
  age). Reliability and dropdown fixes followed, and the Wireless tab was renamed **Wireless Quality**.
- **Full localization of the newest pages.** The Connections, QoS Diagnostics, and all-bands
  Professional pages were tokenized and translated across all 25 languages (localization only).
- **Pre-release code-review hardening (v2.1.0).** A six-agent pre-release audit of every
  Reaper-authored component found **no critical or high-severity issue**; the confirmed items were
  fixed — consistent JSON escaping on several admin-page fields, a single-flighted read of the flow
  accelerator, an anti-forgery token on the Wireless status endpoint, a lock on the Gatekeeper
  enable-time snapshot, and the accelerator health probe made opt-in — and the remainder recorded in
  the backlog. No feature change.

### Since v1.8.0a — audit remediation, Warden hardening, a Devices manager, and a full security re-audit (v1.8.1 – v2.0.0)

The rungs from v1.8.1 to **v2.0.0** shipped **RT-BEXXU only, both variants** (the sibling
fan-out reached v1.8.6c then; v1.8.7 → v2.1.0 were later fanned out to all five models). Headlines — per-version
detail is in [`CHANGELOG.md`](CHANGELOG.md):

- **The audit-remediation arc (v1.8.2 – v1.8.6).** A multi-agent adversarial audit of every
  non-blob component produced **73 verified findings** (each checked against the actual source
  before it was called a defect); v1.8.2 closed the three highest-impact (an IPsec profile-name
  root path, a port-forward firewall-rule splice, a bad-pointer free in the web server), v1.8.3–v1.8.5
  worked the latent and low-severity batches, and v1.8.6 was the independent clean-review sign-off
  plus five defense-in-depth tightenings. All catalogued in [`REAPER-FIXES.md`](REAPER-FIXES.md).
- **Reaper Warden grows up (v1.8.7 – v1.8.8).** IPv6 dual-stack (v6 threat/geo sets, chains,
  anti-lockout) and a **Top blocked countries** stats card (v1.8.7); then a field LAN-lockout was
  root-caused and fixed — private/bogon ranges are now filtered out of every ingested feed, the
  anti-lockout chain order is rebuilt, and blocklist persistence across reboot actually works. v1.8.8
  also added **`rwatch`**, an on-by-default health watchdog (5-min WAN/DNS/Warden-canary/accelerator-wedge
  probe with JFFS incident dumps).
- **WireGuard peer-list fixes (v1.8.9).** The per-peer edit/QR/trash controls render correctly again
  and the peer-edit dialog no longer runs off-screen.
- **Device Identity Manager — the new Devices page (v1.9.0 – v1.9.4).** A new **Devices** page (its
  own left-nav section) correlates every device's identity **per MAC** — custom name, DHCP reservation,
  Gatekeeper state, and live presence — into one view with inline rename, a pool-aware reservation
  ("Pin") dialog, an attention card, filter/search, and a 24-hour per-device traffic figure. v1.9.1
  added a **Storage** tab to choose where opt-in long-term history lives (RAM / JFFS / USB), unifying
  the writers behind one control. v1.9.2–v1.9.4 fixed Wi-Fi 7 classification: MLO links are folded into
  one device row, and wired-vs-wireless is now read from the LAN bridge instead of guessed (so 6 GHz /
  MLO stations are no longer mislabeled "Wired").
- **First-boot credential enforcement (v1.9.5).** A factory-fresh box can no longer reach the dashboard
  on default `admin/admin` — both enforcement paths now send it through the forced credential-change step.
- **Dashboard / Warden / SysInfo polish (v1.9.6).** Security Posture now covers Gatekeeper and Warden,
  the Warden country picker became a searchable checklist, USB tiles re-poll after boot, and the
  System Info feature list reflects Reaper's own packages.
- **Traffic Analyzer accuracy (v1.9.7).** By-Network totals now reconcile with the live WAN chart, and
  the router's own locally-terminated traffic (speed test, DNS, firmware checks, latency probe) appears
  under a new **"Router"** row instead of vanishing from every per-device/per-network view.
- **Security-hardening milestone — two full code audits (v2.0.0).** A comprehensive security review of
  inherited ASUS/Merlin open source Reaper ships — with every surfaced issue fixed and no critical or
  high-severity flaw left open. The web UI no longer trusts device-supplied names (hostname / Wi-Fi /
  VPN / USB / mesh names are HTML-encoded at every display point — dashboard and network-map client
  lists, the shared client picker, OpenVPN/WireGuard status, AiMesh topology, USB storage); a malicious
  USB volume label can no longer inject a root command at auto-mount; the on-device stats database and
  the VPN-profile page are hardened against injection and buffer overflow; the Diagnostics and Warden
  live-status tools now require the interface's anti-forgery token; the internal TLS helper verifies the
  server certificate against the shipped trust store instead of connecting blindly; and threat-blocking
  flushes the hardware flow cache so a newly blocked address drops immediately. The base firmware is
  unchanged — this release is correctness and safety, not features. Known limitations are stated plainly
  (§6): the bundled Samba is on an EOL branch (no reachable exploit found; a maintained-branch plan is
  tracked), and the AiMesh config-sync / network-discovery services ship as closed vendor binaries that
  could not be source-audited. Full finding-by-finding status is in the audit reports.

### Reaper Warden, a security-hardening pass, and a Samba CVE backport (v1.8.0a)
- **Reaper Warden — optional threat-feed / geo / manual-IP firewall.** A new **Warden** page adds a
  **default-OFF** blocking layer built on the kernel's `ipset` engine: auto-pull known
  malware/botnet/attacker IP lists (FireHOL, Feodo, Spamhaus DROP, DShield) on a schedule, block or
  allow whole countries by CIDR, and take your own manual block/allow lists. It has a strict
  **anti-lockout** design (your LAN, established connections, and an explicit allow-list always pass
  before any drop), fetches feeds over the router's own HTTPS with a JFFS cache that survives reboot,
  and **re-arms automatically** after a firewall restart or cold boot. Optional drop-logging for
  auditing. Off until you enable it.
- **Verified security-hardening pass.** A methodical audit found and closed a set of latent issues in
  the Reaper-owned and adjacent code (format-string, shell-injection guards on VPN Fusion / WireGuard
  / Wi-Fi-scan paths, an out-of-bounds path check, an open-redirect guard, and input-sanitizing of the
  generated Gatekeeper firewall script). None were remotely exploitable in normal use; each is now
  closed. Full technical detail in [`REAPER-FIXES.md`](REAPER-FIXES.md).
- **Samba 4.15.13a — backported CVE-2025-9640.** The SMB3 server (Samba 4.15.13, pinned to this
  router's toolchain and no longer receiving upstream updates) gets the **upstream fix for
  CVE-2025-9640** (uninitialized-memory disclosure in `streams_xattr`) backported as defense-in-depth;
  `smbd` now reports `4.15.13-Reaper-a`. Every other Samba advisory since 4.15.13 was audited and
  confirmed not applicable to this file-server-only, AD-DC-free build.

### VPN-page theming + Network-Map polish (v1.7.6 – v1.7.7)
- **VPN Client/Server pages render cleanly.** On **VPN &rsaquo; VPN Client** (PPTP/L2TP) and **VPN
  Server**, the settings panel no longer flashes the original ASUS blue before the Reaper theme
  loads (v1.7.7), and an earlier fault where the cards could stay stuck in stock colors while the
  page churned in the background — which some users read as "always loading" — is fixed (v1.7.6).
  The Internet Speed test (Adaptive QoS) now uses a single page scrollbar.
- **AURA/RGB lighting control.** On the RGB-capable models, the effect-scheme selector on the
  Network Map router panel no longer shows a stray horizontal scrollbar (v1.7.7). *(The RT-BEXXU has
  no AURA hardware; this applies to the RGB-capable siblings.)*

### Gatekeeper — default-deny device access control (v1.7.0, hardened v1.7.3)
- **A new, fully-local device gate.** Gatekeeper lets you approve or block devices on your network:
  the devices the router already knows are grandfathered in when you enable it, anything new lands
  in a **"Pending approval"** list, and blocking is enforced in the firewall. It arms reliably after
  a cold power-cycle and always leaves the HTTPS admin page reachable, so it can never fence the
  administrator out of the control that turns it off. Off by default; entirely on-router, no cloud.

### Security remediation batch + PSIRT class-fix (v1.7.1, v1.7.5)
- **Another audit round (2026-07-21)** closed its findings in v1.7.1, and v1.7.5 class-fixed the last
  `openssl passwd` command-injection sink found while preparing the coordinated-disclosure material
  for **ASUS PSIRT (case 1006563)**. Exhaustive detail in [`REAPER-FIXES.md`](REAPER-FIXES.md).

### Hardening pass + full 24-language UI (v1.6.0)
- **The whole UI is now translated into all 24 non-English languages** it ships (previously the
  Reaper-authored pages fell back to English in every dictionary). Switch language from the
  left-rail selector and the QoS, Traffic Analyzer and AI Advisor pages — help prose included —
  follow, along with the dashboard and the rail clock's localized weekday/month names. Where a
  translated label runs longer than its space it truncates with an ellipsis and reveals the full
  text on hover, so the layout never stretches. *Machine-assisted translation; English stays
  selectable, and native review is recommended before relying on the non-English help text.*
- **Collector efficiency + robustness.** The traffic collector no longer re-reads settings from
  nvram on every 100 ms tick (cached, refreshed once a second), reads the WAN counters without
  reopening their files each tick, resolves each top-talker's MAC once, and throttles the Live
  tables to their real ~1 Hz data rate; every one of its allocations is now failure-checked, and
  the Advisor daemon closes a rare descriptor/child leak. No visible change — the page just costs
  less.
- **Defense-in-depth + fixes.** Input validation on the two spots that write a stored value into a
  session file / firewall command; an **AI Advisor "Save settings"** fix so a rejected save is
  reported instead of silently claimed (and its Refresh button moved next to the title); a
  **Reaper favicon** on the Login/Logout browser tab; and dead-code cleanups.

### Network Diagnostics — optional AI network probes (v1.5.0a)
- **No bundled packet capture.** An earlier internal build carried a `tcpdump`-based Packet
  Capture page; it is **not** shipped (a large legacy dependency for a niche need). Install
  `tcpdump` via Entware on a USB stick if you need capture.
- **AI Advisor diagnostics tier** (AI Advisor variant only): with **per-session, off-by-default**
  consent (a checkbox on the arming card, re-ticked each arm), the read-only Advisor may run
  bounded read-only probes — `ping` / `traceroute` / `DNS lookup` / `netstat` — to localize a
  problem to the **router, client, ISP, or WAN**. Each probe is fixed-argument (no shell),
  one-at-a-time, time-bounded, output-capped, audited to the system log, and target-scoped
  (private addresses that are not on this router's own LAN are refused, so it cannot be used to
  scan the internal network). It still cannot change any setting.

### AI Advisor — optional, read-only, LAN-only (v1.4.x)
An **optional** subsystem (present only in the AI Advisor variant &mdash; the image with no `noMCP` suffix &mdash; and **off by default**
there) that exposes the router as a read-only [Model Context Protocol](https://modelcontextprotocol.io)
server on the LAN. Your **own** AI client, using your **own** API key, connects and
can **read** the router's configuration and traffic to **audit and explain** it —
"is my firewall sane?", "why is my bufferbloat bad?", "what is this device doing?".
It is deliberately fenced to fit the threat model:

- **Read-only.** It exposes curated read tools only; there is no tool that can change
  a setting. The AI recommends; you apply.
- **Off by default and never boot-started.** Nothing listens until you explicitly
  arm it, and it never survives a reboot.
- **LAN-only.** Binds the router's LAN address; never reachable from the internet.
- **Second factor.** Arming needs the admin session **and** an out-of-band **arming
  code** (stored only as a salted hash — the code lives off the router). Optionally,
  a **USB physical key** (v1.4.2): when enrolled, arming also needs the stick, and
  pulling it locks the advisor within ~1 second.
- **Secrets never leave** and **no API key is stored on the router.** Wi-Fi
  passwords, admin credentials, and keys are redacted; the router itself sends
  nothing to any cloud. Network names are shown as your real SSIDs (from the SDN
  profiles), security mode only — never the PSK.
- **Encrypted with the router's own certificate (v1.4.2).** When the router has a web
  (httpd) certificate loaded, the advisor serves **HTTPS using that same certificate**
  — the one your router's web UI uses, **not** a separate cert — and the arming page
  hands you an `https://` URL. If the router has no certificate loaded, it serves plain
  HTTP. (A self-signed router certificate may need to be trusted by your AI client.)

The advisor self-terminates on a session timeout, on disable, or on repeated auth
failure.

### Traffic Analyzer (v1.3.x)
A native, Reaper-themed traffic monitor: **per-device, per-network, and
per-QoS-class** bandwidth with sub-daily history, a 1-second live view with live
top-talkers, an optional monthly-quota warning, and an opt-in WAN latency probe. You
choose where longer-than-a-day history lives (RAM / JFFS / USB). It reads the
Broadcom flow-accelerator's own flow table, so per-device numbers are correct **with
hardware acceleration on**.

### Hardware QoS v3 and v4 (v1.2.8 – v1.2.9)
Extends the Hardware QoS engines with an **aggregate rate cap, per-class guaranteed
minimums, DSCP trust, live per-class counters** (v3), and **per-class weighted
round-robin weights plus an experimental L4S low-latency flag** (v4) — all on a
native Traffic Manager page.

### De-cloud — attack-surface removal (v1.2)
Removed AI-branded and cloud-coupled features to shrink the attack surface, each
dropped with its hooks (closed blobs left unmodified): **Alexa / Google Assistant**,
the **Trend Micro DPI engine** (AiProtection / DPI-based Adaptive QoS / web history),
**AiCloud / WebDAV**, the **AiDisk** cloud-share wizard, the **AAE / AiHome cloud
tunnel**, and the first-boot **QIS EULA / privacy-consent** surface (v1.2.7). The
local Speedtest was restored.

---

## 4. Carried from v1.0

### Hardware QoS — two engines ASUS never shipped
`qos_type=10` runs hardware rate-shaping + PI2 AQM in the Broadcom Runner **with the
flow accelerator left on** (solving the stock accelerator-OR-software-QoS either/or);
`qos_type=11` **Classful** adds per-class priority queues. Both validated on live
hardware (at a 20 Mbit cap, upload loss 6.5% → 0% and loaded latency 71 ms → 30 ms,
all cores under 2%, acceleration still on). Upload-side; download-side aggregate AQM
is pointed at software CAKE, also compiled in. Two Classful properties to know:
classification is fixed when a connection starts (build rules on IP/MAC, port, or
protocol — not "transferred" ranges), and queues are capped individually with no
aggregate shaper (keep class ceilings summing to ~100% for a strict total limit).

### Reaper UI — full rebrand and redesign
Matte-black + crimson theme across the entire web UI: a live-wired landing
**dashboard** and an app-**shell** that loads stock settings pages unmodified in an
iframe (so all settings behavior is preserved). Applied at **serve time from a single
httpd filter**, with a runtime kill-switch: `nvram set reaper_inject=0; restart_httpd`
returns the pristine stock UI with no reflash.

### Scheduled firmware-availability check — fixed, opt-in, default off
The dead stock "scheduled check for new firmware" setting was fixed and set **default
off**: no scheduled check and no outbound update traffic unless you opt in;
notification only, never auto-upgrade.

### Retained Merlin/base capabilities
OpenVPN, WireGuard, IPsec/strongSwan, CAKE QoS, SNMP, IPv6, USB storage / Samba / FTP
/ media server, AiMesh, SDN/MLO, Smart Connect, VPN Director, DNS Director — all from
the 3006.102.8 base.

---

## 5. Security hardening (headline)

Four audit rounds plus a package-CVE backport, all landed in v1.0 and carried
forward. **The command-injection and buffer-overflow classes are cleared** across the
ASUS/Merlin-authored userspace; ~70+ issues fixed. Every fix is compiled into the
build and catalogued by ID in [`REAPER-FIXES.md`](REAPER-FIXES.md).

- **Rounds 1–3 — stock userspace audit** (httpd, rc, shared, libovpn, libcodb,
  libdisk, and the shipping daemons): 8 Critical, 12 High, 19 Medium, 5 Low plus
  internal IPsec-sink hardening.
- **Round 4 — self-review** of the Reaper-authored changes (UI + Hardware QoS) for
  regressions we introduced.
- **Package CVE backport — avahi 0.8 mDNS DoS** (`CVE-2023-38469/38470/38473`),
  ABI-preserving.
- **Latent buffer hardening** (T1–T4) and a **v1.0 pre-release multi-agent code
  audit** of the Reaper-authored C and web UI (no Critical/High found).
- **New-subsystem posture:** the QoS engines, Traffic Analyzer (`rtrafd`), and AI
  Advisor (`rmcpd`) were built to the same threat model — no new inbound listeners
  except the AI Advisor, which is the one deliberate, LAN-only, off-by-default,
  auth-gated exception (see §3).
- **v2.0.0 comprehensive re-audit.** Ahead of the 2.0.0 milestone, two fresh
  end-to-end audits were run — one over all Reaper-authored code and one over the
  inherited ASUS/Merlin open source Reaper ships — and every finding was fixed with
  no critical or high left open. Highlights: stored-XSS neutralization of
  device-supplied names across all admin display points, a USB volume-label root-
  command-injection fix at auto-mount, injection/overflow hardening of the on-device
  stats DB and the VPN-profile page, CSRF-token enforcement on the Diagnostics/Warden
  live tools, certificate verification on the internal TLS helper, and a
  flow-cache flush so threat blocks take effect immediately. Finding-by-finding status
  is in the audit reports.
- **v2.1.0 pre-release code review.** A six-agent audit of every Reaper-authored component ahead of
  the v2.1.0 build found **no critical or high**; confirmed items were fixed — JSON-escape parity on
  several admin-page fields, a single-flighted read of the flow accelerator, an anti-forgery token on
  the Wireless status endpoint, a lock on the Gatekeeper enable-time snapshot, and the accelerator
  health probe made opt-in — with the remainder tracked in [`BACKLOG.md`](BACKLOG.md).

Because most of the hardened userspace is shared with stock ASUS/Merlin firmware
across Broadcom-HND models, please practice **coordinated disclosure** for
base-firmware findings (see [`../SECURITY.md`](../SECURITY.md)).

---

## 6. Known issues & residual risk — READ BEFORE DEPLOYING

Hardening targets the **ASUS/Merlin-authored userspace**. The items below are **not
fixed** and are tracked in
[`REAPER-FIXES.md` → "Open security items"](REAPER-FIXES.md).

**Must be worked (active):**
- **EOL system libraries ship frozen with known unpatched CVEs** — OpenSSL 1.1.1w,
  lighttpd 1.4.39, expat 2.0.1, libgcrypt 1.5.1. OpenSSL is in the remote TLS path and
  is the highest-priority backport. (zlib and curl are current; avahi is patched;
  **Samba was moved to 4.15.13a** with the CVE-2025-9640 backport, and **net-snmp to
  5.9.4** — both current or CVE-backported, no longer on the frozen-EOL list.) To be
  addressed by ABI-preserving CVE backports or an ASUS-led version bump.

**Cannot fix in this tree (monitor ASUS):**
- The **auth / token / session core** and the web input filter live in closed-source
  blobs (`web_hook.o`, `priv_webapi.o`) that cannot be source-verified; the WiFi
  drivers are likewise closed. This is the dominant residual risk versus the
  physical-access-only goal. Mitigation: keep remote web admin disabled; every
  downstream sink is hardened regardless. Watch for ASUS firmware/blob updates.

**Resolved since v1.0:**
- **AiCloud / WebDAV** (which had high-severity findings in v1.0 and was disabled
  there) is now **removed** as part of the v1.2 de-cloud work — the stack is gone, not
  merely inert. Do not attempt to re-add it.

**Design decisions:** default admin credentials (mitigated by the forced first-boot
password change) and lower-priority latent hardening are listed in `REAPER-FIXES.md`.

---

## 7. Install & recovery

1. Log in to the router web UI → **Administration → Firmware Upgrade**.
2. Upload the **`…_nand_squashfs.pkgtb`** firmware image for your chosen variant (§2).
   **Do not** flash the `…_loader.pkgtb` (that is recovery-only).
3. First non-stock flash may need `nvram set DOWNGRADE_CHECK_PASS=1` over SSH first.
   A factory reset is recommended when coming from much older or another third-party
   firmware; do **not** reload a saved settings backup after a reset.
4. On first boot, complete setup and **set a strong, non-default admin password**
   (this is the mitigation for the default-creds item).
5. **Recovery:** if a flash fails, use **ASUS Firmware Restoration** in rescue mode
   with the matching `…_loader.pkgtb`.

You can return to stock anytime by flashing an official ASUS image.

---

## 8. Build & image verification

Built per model with the BCM4916 userspace toolchain (gcc-10.3, 32-bit ARM) via
`make <target>` (`rt-BEXXU` / `rt-be86u` / `rt-be88u` / `gt-be98` / `gt-be98_pro`), each
`MAKE_EXIT=0` with "Done! Image 96813GW has been built" and the noMCP staged filesystem
confirmed free of the AI Advisor.

**v2.3.7 flashable-image hashes (SHA-256)** — the **newest published release**, built and
shipped on all five models (both variants each) through the public clean-room CI pipeline,
2026-08-13. These are the values in the on-router update manifest
([`releases/latest.json`](../releases/latest.json)), which the Firmware page checks before it
flashes anything.

| Model | Variant | SHA-256 of `…_nand_squashfs.pkgtb` |
|---|---|---|
| RT-BE96U | + AI Advisor | `0e5a85e2842e86a7ca21a1c9c0c4e58cfbc6aa627cfd86107a6b8fffc7116ae7` |
| RT-BE96U | Standard (`noMCP`) | `a48952f4755a737853198e929386b1af5f90bdbaad070fbe9c1aeeb7ce5a9ad3` |
| RT-BE86U | + AI Advisor | `814d663db3bc42e48b92fc6aaae502afe462d222711884a2db42bbbb47898a9b` |
| RT-BE86U | Standard (`noMCP`) | `45a52022987a38e38a79e3d113ef2384a8bafcd570484322a76bdcf27cf77aa6` |
| RT-BE88U | + AI Advisor | `ec38a58fc720cfae8288e48ab559adfcee4cddc62236336af0c2c7c8845298df` |
| RT-BE88U | Standard (`noMCP`) | `299a390d3d4cd8e38477509a35ed091a2c8462c4948ebf85370b620bb016e78b` |
| GT-BE98 | + AI Advisor | `d0859e8820adf08b901bd5debe2403cc29f99558f9cba3b19abcee4199d78273` |
| GT-BE98 | Standard (`noMCP`) | `9a4e3b5ea8f017a521f178ffe3d5fcd0bef810b2c6ca02c007f02a2add86dd35` |
| GT-BE98 Pro | + AI Advisor | `7232067e325ce3d70037c14cd5f5bbf4f55f4e6df686049013450fb6d0dd53b1` |
| GT-BE98 Pro | Standard (`noMCP`) | `baf4bdffc0638f8ccdd8c5f8eadf88294f7c9fa24bc74259d0c4949eead4281d` |

Each model's `…_loader.pkgtb` recovery image is listed in its own
`SHA256SUMS-<MODEL>-Reaper_v2.3.7.txt` alongside the images under `releases/<Model>/`.

<details>
<summary><strong>Earlier releases — image hashes (v2.1.0 – v2.1.9, v1.7.7)</strong></summary>

**v2.1.9 flashable-image hashes (SHA-256)** — **built + shipped on all five models**
(both variants each, 19-check verify gate) by the parallel per-model fleet, 2026-08-05. The RT-BE96U
image hashes are shown below; each sibling has its own `SHA256SUMS-<MODEL>-Reaper_v2.1.9.txt`
alongside its images under `releases/<Model>/`. (v2.1.7 and v2.1.8 were both built but never
published — v2.1.7 was superseded pre-release by the WAN-MTU rollback → v2.1.8, and v2.1.8 by the
code-audit fixes → v2.1.9.)

| Image (`RT-BE96U_3006_102.8_Reaper_v2.1.9…`) | SHA-256 |
|---|---|
| `…_nand_squashfs.pkgtb` (+ AI Advisor) | `690db20470dc68f1b58074fa722f380315c45101299904004442edda97f05bed` |
| `…_nand_squashfs_loader.pkgtb` (+ AI Advisor, recovery) | `0d55cb928bacf51132735c6e56c84285322599aaad009e044b74f8b3f0c09fca` |
| `…_noMCP_nand_squashfs.pkgtb` (Standard) | `134eef123586fee0e9d716b9502c94175652f8580b56e03e147160360f9dbfdd` |
| `…_noMCP_nand_squashfs_loader.pkgtb` (Standard, recovery) | `76adf939d0580ca811dc54fd7c06521facbfdf3dc76d3b5b3ba34204d84e6bff` |

**v2.1.6 flashable-image hashes (SHA-256)** — **built + shipped on all five models**
(both variants each) by the parallel per-model fleet, 2026-08-05. The RT-BE96U image hashes are shown
below; each sibling has its own `SHA256SUMS-<MODEL>-Reaper_v2.1.6.txt` alongside its images under
`releases/<Model>/`.

| Image (`RT-BE96U_3006_102.8_Reaper_v2.1.6…`) | SHA-256 |
|---|---|
| `…_nand_squashfs.pkgtb` (+ AI Advisor) | `fd50d77121c70621741048f902ef51075cef127065f7abd0caaa5713a99e316d` |
| `…_nand_squashfs_loader.pkgtb` (+ AI Advisor, recovery) | `044fea003e48232146621bc82bc51fc0d05341f61f6cb66ffcecbfad1a0b1f6b` |
| `…_noMCP_nand_squashfs.pkgtb` (Standard) | `133cd2448bad23f163e0b2723dfd3c4f4222757cd7ca8ac65459117698e220f7` |
| `…_noMCP_nand_squashfs_loader.pkgtb` (Standard, recovery) | `69027c1be3f61ce0308736b2423420e74d67ea714ae11dbf37416ec428bb9c88` |

**v2.1.5 flashable-image hashes (SHA-256)** — **built + shipped on all five models** (both variants
each), the first release produced by the parallel per-model build fleet. Each sibling has its own
`SHA256SUMS-<MODEL>-Reaper_v2.1.5.txt` alongside its images under `releases/<Model>/`.

| Image (`RT-BE96U_3006_102.8_Reaper_v2.1.5…`) | SHA-256 |
|---|---|
| `…_nand_squashfs.pkgtb` (+ AI Advisor) | `53f9cf62f05bd1cb041e6f2a96e7d4c445b799f633ba5bb56b5f14118343388e` |
| `…_noMCP_nand_squashfs.pkgtb` (Standard) | `78d162bcd11fafbf4d2f41a679b424ef19aae1c7d6d9b0401556fb1e72ea31bf` |

**v2.1.4 flashable-image hashes (SHA-256)** — **built + shipped on all five models**
(both variants each). The RT-BE96U four-file set (both variants' `…_nand_squashfs.pkgtb` **and** their
`…_loader.pkgtb` recovery images) is shown below; each sibling has its own
`SHA256SUMS-<MODEL>-Reaper_v2.1.4.txt` on the `reaper-firmware/` ladder (RT-BE86U / RT-BE88U / GT-BE98 /
GT-BE98_PRO).

| Image (`RT-BE96U_3006_102.8_Reaper_v2.1.4…`) | SHA-256 |
|---|---|
| `…_nand_squashfs.pkgtb` (+ AI Advisor) | `910bba678e5d27a43196ea339b0b630a1b1d4c1a05163a17e673aefdfb3cb111` |
| `…_nand_squashfs_loader.pkgtb` (+ AI Advisor, recovery) | `e722a78b441b454bf785072c700962614a6582783732c86ca60e462b32194028` |
| `…_noMCP_nand_squashfs.pkgtb` (Standard) | `45cbcd42fd2bd25fed30ecdd00aefa87df7c634313282965227ebd578efd7f70` |
| `…_noMCP_nand_squashfs_loader.pkgtb` (Standard, recovery) | `68e591c6beb666b4e92c961dfbe48277fc69b103a2c54541ef73c4cb494642de` |

**v2.1.3 flashable-image hashes (SHA-256)** — **RT-BE96U only** (RT-BE96U-first rung; the siblings
went straight from v2.1.2 to the v2.1.4 fan-out). `SHA256SUMS-RT-BE96U-Reaper_v2.1.3.txt` on the ladder.

| Image (`RT-BE96U_3006_102.8_Reaper_v2.1.3…`) | SHA-256 |
|---|---|
| `…_nand_squashfs.pkgtb` (+ AI Advisor) | `9f8f16f39f2a7e2704dfb3962b2ae388d201a3776ef546eeabaef0e814b29cf5` |
| `…_nand_squashfs_loader.pkgtb` (+ AI Advisor, recovery) | `cd6ccc0d98337c99b493452c816cbe8db546966eaaadf75c70970bf5eb97f303` |
| `…_noMCP_nand_squashfs.pkgtb` (Standard) | `815b8a166114d4d52063102365af5c8581a4079086750867ee6523df17b3661a` |
| `…_noMCP_nand_squashfs_loader.pkgtb` (Standard, recovery) | `1432c0a20d0e61b7210ff7c364fa40c3ddd0c212e7524cbc0e59b842edb4d1ae` |

**v2.1.2 flashable-image hashes (SHA-256)** — **RT-BE96U** (the last rung shipped across the full
five-model fleet before the v2.1.4 fan-out). The four-file set (both variants'
`…_nand_squashfs.pkgtb` **and** their `…_loader.pkgtb` recovery images) is on the `reaper-firmware/`
ladder as `SHA256SUMS-RT-BE96U-Reaper_v2.1.2.txt`.

| Image (`RT-BE96U_3006_102.8_Reaper_v2.1.2…`) | SHA-256 |
|---|---|
| `…_nand_squashfs.pkgtb` (+ AI Advisor) | `eab8bdd393cf435ccfae8f71bb631511bd5594cda0d44b54f0d9bebcf0489419` |
| `…_nand_squashfs_loader.pkgtb` (+ AI Advisor, recovery) | `1d8a734ca297cc2b8aeed3325410630c6e63888959401c47f53423cdac386876` |
| `…_noMCP_nand_squashfs.pkgtb` (Standard) | `88398251688c78cae7d428ba515ce40bfef3594eaeb9f725b9abf94bb2ba1dc0` |
| `…_noMCP_nand_squashfs_loader.pkgtb` (Standard, recovery) | `71fd3c65409c80fff6ed82975182046d374475ed6b6a6526d593c0f86d187397` |

> Source provenance: this image was built from `release/src/router` tree
> `b2c357fa4a340d51a1cd6ef8777693781db92c56`, reproducible from patches `0001`–`0310`
> onto base `a7ebfa133a`. See [`BUILD-PROVENANCE.md`](BUILD-PROVENANCE.md).

**v2.1.0 flashable-image hashes (SHA-256)** — the **four siblings** (RT-BE86U / RT-BE88U / GT-BE98 /
GT-BE98 Pro) remain at v2.1.0, and RT-BE96U's v2.1.0 set is retained below for reference. Each model's
four-file set (both variants' `…_nand_squashfs.pkgtb` **and** their `…_loader.pkgtb` recovery images)
has its own `SHA256SUMS-<MODEL>-Reaper_v2.1.0.txt` on the `reaper-firmware/` ladder; the **RT-BE96U**
set is tabulated below. *(The primary model builds as the **RT-BE96U**; this document refers to it
generically as "RT-BEXXU" elsewhere.)*

| Image (`RT-BE96U_3006_102.8_Reaper_v2.1.0…`) | SHA-256 |
|---|---|
| `…_nand_squashfs.pkgtb` (+ AI Advisor) | `a87d38538b3e2f907a0023a7f663f042d5e3ef088752336f63e461d22f2ea736` |
| `…_nand_squashfs_loader.pkgtb` (+ AI Advisor, recovery) | `37314dfc73515f94e1f5dff8c7778d2d0ce2bbf611efea471016ec4e8f1322ba` |
| `…_noMCP_nand_squashfs.pkgtb` (Standard) | `6b7eee81ca382e38db52307e1cbd1b692c93980c6223572402ad172791d084ea` |
| `…_noMCP_nand_squashfs_loader.pkgtb` (Standard, recovery) | `399b841499807952f2d88789d3663e4cb05a221882f6e3f4ef10c501534d62b4` |

The **v1.7.7** table below remains the last full five-model, both-variant fan-out for reference.

**v1.7.7 flashable-image hashes (SHA-256)** — the `…_nand_squashfs.pkgtb` you flash. The full
20-file set (both variants + the `…_loader.pkgtb` recovery images) is in `SHA256SUMS-v1.7.7.txt`
on the `reaper-firmware/` ladder.

| Image (`3006_102.8_Reaper_v1.7.7…`) | SHA-256 |
|---|---|
| `RT-BEXXU_…_nand_squashfs.pkgtb` (+ AI Advisor) | `eb0391c9da30f82ca03a13ee6fdcc56f888f62fe68824430b65bb8314d61f76e` |
| `RT-BEXXU_…_noMCP_nand_squashfs.pkgtb` (Standard) | `1338b4e1ed1862b895a2f130dc202f842055d7a9881879a146e49b8630e78ef0` |
| `RT-BE86U_…_nand_squashfs.pkgtb` (+ AI Advisor) | `12b96e1b1535d9b1d3d9733dc418072a85dbfe3e9400842a112e04dc5b74a9ea` |
| `RT-BE86U_…_noMCP_nand_squashfs.pkgtb` (Standard) | `c6dc3094a1a4025c7b40839c9f50d45bad9ba3de52c502eb2b6105b70806da5b` |
| `RT-BE88U_…_nand_squashfs.pkgtb` (+ AI Advisor) | `a5bfeb1621b30da4ae26d8a0910c42dfbac7a0d67ebeb95329df93a2d7df25f0` |
| `RT-BE88U_…_noMCP_nand_squashfs.pkgtb` (Standard) | `3ad3d6bd5ce99d500c5c3908c03df40d564e5cb293734c96704efb51aa6db26f` |
| `GT-BE98_…_nand_squashfs.pkgtb` (+ AI Advisor) | `69823f8c7788051f907a7cca736edbdae7c626477c1fb414f856deba9879c2d0` |
| `GT-BE98_…_noMCP_nand_squashfs.pkgtb` (Standard) | `10a7bcfb811c2cd4fbbeb13d8a3d77f2479dd921a773b1d10c14855d041923b5` |
| `GT-BE98_PRO_…_nand_squashfs.pkgtb` (+ AI Advisor) | `c2ed0f388699bcc5643947a50c5ebd8db7f795f3a333cbdc61a3a70a23759cb8` |
| `GT-BE98_PRO_…_noMCP_nand_squashfs.pkgtb` (Standard) | `c7c216fe7070e704fa30e492d4f493d47b1f4af2efb853f11e91b38f49ab2189` |

> All five models built + shipped 2026-07-24 (both variants, staged-fs verified) on the
> `reaper-firmware/` ladder alongside `SHA256SUMS-v1.7.7.txt` (which also lists the ten
> `…_loader.pkgtb` recovery images).

</details>

### Validation status

| Line | Status |
|---|---|
| **through v1.3.3** | Validated on the physical RT-BEXXU: hardening rounds 1–4 + latent T1–T4, the avahi CVE backport, all Hardware QoS engines (v1 global, Classful, v3, v4) end-to-end, the Traffic Analyzer, the de-cloud removals, and the Reaper UI at all page depths. |
| **v1.4.x – v1.5.0a** | The **AI Advisor** — arming, LAN-only bind, token auth, secret redaction, USB third-factor, network-diagnostics tier — metal-validated on the RT-BEXXU. |
| **v1.5.x** | Newest fully metal-validated build in the line: **v1.5.6**. |
| **v2.0.0** | Upgrade-path first boot verified on the physical RT-BEXXU (clean boot + healthy diagnostics). |
| **v2.1.4 – v2.2.1** | Five-model, both-variant fan-out — all five built + shipped, each passing the staged-image verify gate (17 checks through v2.1.6, **19 from v2.1.7** once the shared-parity and patch-marker checks were added). GT-BE98 Pro was converted to Samba 4 during this line. |
| **v2.2.2 – v2.2.4** | RT-BE96U only. |
| **v2.2.5, v2.2.6, v2.3.0, v2.3.1** | Each built + shipped on all five models, both variants — every build as itself, per-model banner / base / BUILD_NAME verified by the 19-check staged-image gate, noMCP images confirmed Advisor-free. |
| **v2.3.2, v2.3.4, v2.3.7** | Shipped on all five models. **v2.3.7** is the newest published release. |
| **v2.4.1, v2.4.2** | Built on RT-BE96U, both variants, and run on hardware. |
| **v2.4.3** | Built on RT-BE96U, both variants (20 pass / 0 warn / 0 FAIL each). Siblings ported, for CI. |

---

## 9. Distribution & license

Reaper distributes its **GPL userspace modifications** (source + patches in this
repo) under **GPL v2** — see [`../LICENSE`](../LICENSE) and the Reaper-specific notice
[`../LICENSE.reaper`](../LICENSE.reaper). The image additionally bundles **GPL v3**
components (Samba 4, GNU wget / nano) and **LGPL v2.1** libraries; their full license
texts are in [`../LICENSES/`](../LICENSES/), and the complete corresponding source +
terms (incl. GPL v3 § 6 Installation Information) are in
[`SOURCE-AVAILABILITY.md`](SOURCE-AVAILABILITY.md). The proprietary Broadcom/ASUS/Trend
Micro binary blobs are **not redistributable**, are not published, and are licensed for
genuine ASUS hardware only (`README.proprietary`). Reaper is provided **as-is, with
no warranty**; run it understanding the residual risks in §6.
