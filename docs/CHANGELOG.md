# RT-BE Series "Reaper" — Changelog

High-level history of the Reaper build. One entry per version, big changes only —
the exhaustive security detail is in [`REAPER-FIXES.md`](REAPER-FIXES.md) and the
per-release summary in [`RELEASE-NOTES.md`](RELEASE-NOTES.md).

All versions are the `3006.102.8_Reaper_v<X>` firmware line, built on the
Asuswrt-Merlin 3006.102.8 base for the ASUS RT-BE Series (BCM4916 platform).
The RT-BEXXU is the primary, hardware-validated model; the **RT-BE86U**,
**RT-BE88U**, **GT-BE98**, and **GT-BE98 Pro** are built from per-model branches
of the same tree. See `RELEASE-NOTES.md` for each release's validation status.

Throughout this document, you will see references to AI and MCP functionality. Reaper is 
distributed in two distinct build variants. The MCP-enabled build includes a custom Model 
Context Protocol implementation that allows authorized AI agents on the local LAN to connect 
to the router, perform basic diagnostics, and provide the user with recommendations for 
improving performance or remediating identified issues. Any firmware image with noMCP in 
its name is compiled without MCP or AI functionality. This is not a disabled feature or 
a runtime setting; the relevant components are excluded from the build entirely.

AiMesh has been retained because no suitable open-source replacement is currently known. 
Replacing AiMesh would also require a compatible replacement implementation on every mesh 
node, not only on the primary router.

---

## v2.4.6 — Consoles can use UPnP again, mesh nodes stop looping, and an About page that can prove what it claims
*In the source tree, **not yet built or published**. Cut from RT-BE96U; the four sibling models are ported and take this rung from the patch series. Images come from the clean-room CI build.*

- **Fixed: a games console could fail to start networking whenever UPnP was switched on.** Reported repeatedly against Call of Duty, and it survived every restart-UPnP-and-clear-the-leases suggestion — because the console was never getting as far as asking for a port. Two separate causes, both fixed. **First, the router advertised a service it does not have.** It answered discovery requests for the old dial-up-era "PPP connection" service, which it has never implemented, so a console that asked for that one first was told "yes, over here", followed the pointer, found nothing it recognised, and gave up before requesting a single port forward. A dead end during introductions, not a refusal — which is exactly why it looked so unlike a port-forwarding problem. **Second, the router went back to introducing itself as the older, more widely understood kind of gateway.** A newer description had been adopted to gain two conveniences, chiefly "this port is taken, give me any free one"; but that same description is misread by real consoles, and the fix for *that* had already been to describe ourselves the old way to everyone — which is what withdraws the two conveniences in the first place. So the build was paying the whole price and keeping the whole risk. The two are now consistent: the router says one thing about itself everywhere. **IPv6 pinholes are unaffected** and still switch the router to the newer description when you turn them on, because they can only exist there. The separate "advertise the newer gateway description" setting is gone — with this change there is nothing for it to select, and a setting that cannot take effect is worse than no setting at all.
- **Fixed: flashing a mesh node left its web page blank, with the address bar cycling and no way to reach the login screen.** An AiMesh node deliberately restricts its own web interface to a short list of pages — that part is ASUS's design and is correct, since a node is configured from the main router. Reaper's theming redirects each page to its own interface, and the node's interface is not on that list, so the node bounced the redirect straight back to the page it came from, which redirected again. Neither side was wrong on its own; together they had no exit, and because the redirect runs before the page draws, the result was a blank window rather than anything that looked like an error. The node's own firmware-update page was caught in the same loop, so a node in that state could not be recovered through its own interface either. Reaper's theming now stands aside entirely on a node, which is what a node is meant to show. **This is not the first-boot loop fixed in v2.2.0** — different cause, and this one only ever affected mesh nodes.
- **New: three settings that previously existed only as hidden values now have proper controls,** on the Tools → Other Settings page. The **workaround for a Broadcom defect that can leave settings unable to save until the router is restarted** — now **on by default**, where before it had to be switched on by hand and almost nobody knew it existed. The **theme switch**, for anyone who wants the stock interface back without reflashing. And the **schedule for Warden's threat-feed refresh**.
- **Fixed: that Warden refresh schedule could be saved and would never actually take effect** — the page was restarting three services, none of which were Warden or the scheduler, so the setting looked accepted and quietly did nothing until the next reboot.
- **Fixed: saving anything on that page logged you out.** It restarted the web server every time, including for a save that changed only a connection timeout. Now only the settings that need a restart ask for one.
- **Removed: a "Disable Asusnat tunnel" switch that could not do anything.** The daemon it offered to disable is not compiled into this firmware and no such program exists anywhere in the image, so the control was an offer to turn off something that was never on. The neighbouring "Redirect webui access" option was checked at the same time and **deliberately kept** — it is a working, router-local convenience, not telemetry.
- **Fixed: the QoS diagnostics and system-information graphs moved in visible steps instead of flowing,** the same defect the Traffic Analyzer graphs shed in v2.4.5 and for the same reason: each point was placed by its position in the list rather than by when it arrived, so every reading shoved the whole trace sideways in one jump. The temperature graph was the worst in the build, moving by about a twentieth of its width every three seconds. Both now place readings by time and redraw continuously, so a late reading glides instead of stuttering, and the drops graph no longer rescales vertically the instant a peak scrolls off the edge.
- **Changed: the firmware flashing screen no longer shows internal polling detail, and no longer offers a Close button while the router is being written.** The progress overlay had been displaying the literal name of an internal function and a poll counter — debug output that reached the screen by accident. More importantly, the Close button was appearing on a timer *during the flash itself*, where dismissing it cannot stop anything and simply hands you a normal-looking page over a router that is rewriting its own storage. It still appears immediately if anything actually goes wrong, and still appears during download and upload.
- **Improved: the diagnostic report now covers the firewall and the dataplane accelerator, and it checks its own redaction before you send it.** A connectivity report could not be answered from a bundle at all, because the collector captured neither, so the commands that separate "Warden blocked it" from "the accelerator wedged" from "the problem is upstream" could only be run by hand, live, during the outage. It now captures Warden's counters and list sizes, the accelerator's status, bounded connectivity probes, and the watchdog's state. Separately, **e-mail addresses were not being redacted** — the redaction only looked at settings whose *name* implied sensitivity, so an address appearing in a log line or an addon's output went through untouched. That is fixed, and the finished report is now re-scanned for anything that still looks like a public address, a hardware address or an e-mail, and marked either clean or "review before sharing". Counts only — printing what it found would put the leak into the file being audited.
- **New: an About page, reached from a small scythe mark at the bottom of the menu.** It carries the credits this project owes — RMerlin, whose Asuswrt-Merlin every line of Reaper is patched on top of, and the testers and bug reporters who have shaped more releases than they probably realise — along with the project links, the licence position, and a way to contribute for anyone who wants to. It opens from the same place on every page and is not a menu entry, so it costs nothing to anyone who is not looking for it.
- **The page states its own provenance, and the build fills it in.** Above everything else it shows the number of patches applied, the exact upstream commit they were applied to, and the date the image was built — followed by the three commands that rebuild that image from scratch. Most router firmware asks to be trusted; this one can be checked, and the page hands you what you need to check it. **Those figures are written by the build itself**, not typed into the page, so they describe the image you are actually running rather than whatever was true when somebody last edited the file.

---

## v2.4.5 — Smooth live graphs, an update notice that stops pushing the dashboard off screen, and your addons in the dashboard menu
*Six field reports and one thing found while fixing them. Cut from RT-BE96U; the four sibling models are ported and take this rung from the patch series. Images come from the clean-room CI build.*

- **Fixed: the Traffic Analyzer's live graphs moved in visible steps rather than flowing.** The cause was not the update rate, which is why turning it up would never have helped. Each point was placed by its *position in the list* rather than by *when it arrived*, so every new reading shoved the whole trace sideways by exactly one slot — a jump of just under 1% of the graph width, once per poll and never in between. Even polling as fast as the router can answer, the graph would still only exist at ten positions a second. The graphs are now drawn on the display's own refresh, with each reading placed by the time it arrived, so how often the data comes in and how often the picture is drawn are no longer the same thing — and an update arriving slightly late becomes a smooth glide instead of a stutter. The vertical scale was a second, independent source of jumpiness: it was recalculated from scratch every poll, so the instant a peak scrolled off the left edge, every point on screen moved. It now steps between sensible round values and waits before shrinking. Returning from a history window no longer draws a long ramp across the gap that never happened.
- **Fixed: on some screens the dashboard ran off the right edge and cut off the Logout button — and on smaller windows the "new firmware" notice vanished entirely.** Both came from the same place: the row of small status pills across the top of the dashboard cannot wrap, so its full width set a floor for the whole page. Adding the firmware-update badge to that row pushed the page wider than the window on screens in a particular band — a 1920 monitor at 110% scaling lands squarely in it. Below that band the outcome was worse and much harder to notice: the dashboard's own rule for dropping pills on narrow windows counted the update badge as a pill, so **the notice that a new version was available quietly disappeared on any window narrower than about 1700 pixels**. The page can now shrink properly, so the pill row clips as it was always meant to, and the firmware notice has moved out of it into a full-width banner at the top of the dashboard — where it wraps instead of pushing, and is visible at every window size.
- **New: installed addons now appear in the dashboard's menu.** If you run amtm, Diversion, scMerlin or similar, their entries showed up on every page except the one you land on. Every other page is drawn inside the app frame, which builds its menu from the same file addons add themselves to; the dashboard is the one page with its own menu, and that menu was fixed at build time. It now reads the same file the rest of the interface does. Because that file belongs to third-party software, everything it offers is treated as untrusted: only plain links to pages on the router itself are accepted, anything else is dropped rather than cleaned up, and nothing from the file is ever executed. If it cannot be read or makes no sense, the menu stays exactly as it ships.
- **Fixed: Warden's outbound blocks could not be told apart from inbound ones in the system log.** Both directions ended at the same place, so every entry carried the same label and there was no way to answer "is it blocking what my devices are *reaching*?" from the log. Outbound blocks now have their own label, their own counter, and are reported separately rather than folded into the inbound total.
- **Fixed: Warden's breakdown of what it blocked was crammed into a card too narrow to hold it.** The figures that let you reconcile the big "blocked hits" total — countries, threat feeds, manual blocks — were tucked under that number in a box about 150 pixels wide, where they wrapped across three lines and broke mid-way through a separator. They now sit on one line directly above the country table they explain, styled as readings rather than prose so they are not mistaken for the paragraph above them. **Those four labels were also still in English in all 24 non-English languages** — unnoticed as small grey text, obvious once given a line of their own. They are now translated.
- **Fixed: a speed test could give up partway through, and the more tests you ran without reloading the page, the sooner it happened.** The page tolerates a number of error lines from the speed-test program before it declares a run failed. That tolerance was only ever reset when a run *finished* — never when one *started* — so every test in a session inherited whatever the earlier ones had used up, and after enough tests a run began with none left and gave up on the first error line it saw. Reloading the page cleared it, which is what made it look random rather than progressive. **This is a narrower fix than it sounds, and it is worth being plain about the limits:** it does not change *why* the speed-test program reports errors, and it is not what fixed the page freezing mid-test — that was the earlier change from synchronous to asynchronous polling. **Deliberately not fixed here:** that same tolerance is consumed once per *poll*, not once per error. The page re-reads the program's output every 200 ms and re-examines the same entry, so a single error sitting at the end of a stalled output burns the allowance at five per second and exhausts a nominal fifty in about ten seconds. That is the more likely explanation for a test that dies mid-run on the *first* attempt in a session, and it is a real change to how the run is bounded rather than a counter reset, so it is not being slipped into a release that is already cut.
- **Fixed: a handful of buttons and menu options were stuck in English regardless of your language setting.** The Drop/Accept/Both options on the firewall's logging selectors, the QoS diagnostics page title, and two buttons in the top bar were written as plain text rather than as translatable entries.

---

## v2.4.4 — hot fix: IPv6 traffic is now counted per device in the Traffic Analyzer
*A field report on an RT-BE88U: the WAN line showed 978 Mb/s while the device actually pulling that download showed 521 kb/s. The totals were right; the device list was not.*

**The Traffic Analyzer counted IPv4 only, per device.** The collector reads the kernel's connection-tracking table to work out which device each byte belongs to, and it skipped every IPv6 connection outright. Those bytes still reached the WAN figure and the per-network figures — which is why the totals always looked correct — but they were credited to no device at all. On a router handing out IPv6, that is most of a modern client's traffic: an iPhone downloading from a service that prefers IPv6 could show a few hundred kb/s against a saturated internet connection. The reporter's own reading of it was exactly right — the total was correct, the device listing was not.

**Why IPv6 needed new work rather than a one-line change.** For IPv4 the router finds the device by looking the connection's local address up in its ARP table. IPv6 has no equivalent file, and because IPv6 is not translated the way IPv4 is, either end of a connection may be the local device — a subnet test cannot tell them apart. The collector now asks the kernel directly for its IPv6 neighbour table and checks both ends against it, keeping only neighbours that sit behind one of the router's own bridges: a neighbour reached over the internet connection is your ISP's router, not a device of yours, and giving it a row would be wrong. Devices are matched on their **hardware address**, the same key the IPv4 side uses, so a device using both IPv4 and IPv6 appears as **one row** rather than two. The router's own IPv6 traffic goes to the "Router" row. Per-network figures pick IPv6 up as well, so the per-bridge numbers now reconcile with the WAN line too.

A device with no IPv4 traffic at all will show a blank address until the network map names it — the row counts correctly regardless, because it is keyed on the hardware address.

**Two related corrections in the same release:**

- **The "By QoS class" chart now says "Upload only".** The hardware QoS engine shapes the upload direction only, so that chart can never show a streaming device's download — a genuine and reasonable source of confusion, since several devices streaming video will barely register. The caveat existed but was buried at the end of a FAQ answer; it is now a badge on the chart itself, with the reason on hover.
- **The Analyzer's FAQ answer about where the numbers come from was wrong on two counts.** It still described the accelerator-table source that v2.3.3 replaced with connection tracking, and it told users IPv6 was "not yet split per-device" — now the opposite of what the router does. Rewritten. The non-English translations of the old text were discarded rather than left saying the reverse of the truth, so that answer reads in English in the other 24 languages until it is retranslated.

*Built on RT-BE96U, both variants. The four sibling models are ported and are for CI.*

---

## v2.4.3 — the v2.4.2 work, audited before it went anywhere
*This release carries everything in the v2.4.2 section below, which published no images, plus the remediation of a security audit run against it. Nothing here is a fix to code any user has ever installed.*

Before publishing the v2.4.2 rung, everything it added was audited: the shell scripts the router generates and runs as root, the new lines spliced into the DNS service's configuration, the JSON the web interface parses, the new pages, and the traffic daemon's output. That audit found six defects, all of them in code v2.4.2 introduced, and all six are fixed here. It also came back clean on the things that would have mattered most — no way found to inject a command into the generated scripts or a directive into the DNS configuration, no cross-site scripting in the new pages, no new listening service, and the cross-site request protections correct on every control that changes settings.

Three of the six could have been felt by someone running v2.4.2:

- **The web interface could be crashed by a malformed mesh-client file.** The code that decides whether a device is wired reads a file the mesh service writes, and checked the shape of that file at two of its three levels. A file that was valid but the wrong shape at the top would have crashed the web server — which runs with full privileges — rather than being rejected. Reaching it requires the ability to write into the router's temporary directory first, which nothing on a default system grants; it is a latent flaw rather than a live one, and it is now checked at both the entry point and the caller.
- **A website-name block rule with many names could have stopped DNS and DHCP for the whole network.** The new feature that turns a list of website names into a live block list writes a line into the DNS service's configuration, and the code reading that line back used a smaller buffer than the code writing it. A long enough list would have been cut in half — leaving either a rule that silently never matched, or a broken directive that makes the DNS service refuse to start, which on this router takes DHCP with it. Both ends are fixed: the writer now measures the line and says in the log if it had to leave names out, and the reader refuses a partial line outright rather than passing on half of one.
- **Warden's new block breakdown could read as zero with two browser tabs open.** The statistics are gathered by a script the web interface runs every thirty seconds, and it used one fixed working file, so two tabs — or two people signed in — overwrote each other's work and banked zeros. That is exactly the "the numbers don't add up" confusion the breakdown was added to solve. Each run now uses its own working file.

The other three are smaller: a limit on the number of block objects was applied in one place and not the matching one, so past that limit the router asked the DNS service to fill lists it had never created; the DNS configuration fragment was the one file the firewall engine wrote without setting its permissions, so it landed readable and writable by anyone; and two networks sharing one bridge (the guest IoT network sits on the main bridge) made the traffic graph label the main network with the guest network's name.

Two further hardening changes were taken at the same time. The most interesting one is not a leak but a silent-failure mode: the router-self filter exempts your DNS servers automatically, and it read those addresses straight out of the resolver file. An address written there with a prefix — `0.0.0.0/0` — is *accepted* by the firewall as "allow everything", at the top of the chain, which would have quietly turned the entire self-filter off while every status indicator continued to report it as on. Those values are now checked before use.

**Deliberately not fixed here:** the router's temporary directory is writable by every account with no restriction on deleting other accounts' files, which is what makes the first defect above reachable at all. That is stock ASUS/Merlin behaviour, it affects every part of the system including the closed-source components, and changing it is not something to do in a release whose purpose is to fix six specific things. It is recorded, with two candidate approaches, and gets its own release and its own round of hardware testing.

---

## v2.4.2 — Warden's outbound direction actually blocks, the firewall pages explain themselves, and two field reports about numbers that did not add up
*Built on RT-BE96U (MCP), 20/20 on the staged-image gate, and **run on hardware**. Everything below is additionally verified by construction (generated scripts parsed, emitters compiled against stubs, ipset commands run against a real ipset, page helpers executed in a browser engine). The four sibling models are ported but not yet built.*

- **Fixed: Warden's "outbound" and "both" directions were blocking nothing.** If you had told Warden to stop devices *reaching* flagged addresses, it did not — while inbound blocking of the very same addresses worked perfectly, which is what made this so hard to believe. The whitelist was checked before the outbound rules, and every outgoing connection has one of your own devices as its source, so **any whitelist entry covering that device skipped the outbound checks entirely** — including the "whitelist your own network" entry that this feature's own lockout guidance tells you to keep. The destination checks now run first, in a chain of their own. Two things fall out of that: a whitelisted **remote** address is still exempt in both directions, but a whitelisted **local** device no longer gets a free pass to a flagged destination — that pass was the bug — and the destination side gained the loopback/LAN/own-address exemptions it never had, which were the other half of the 2026-07-29 lockout waiting to happen on the way out.
- **New: Warden can filter what the router itself sends (off by default).** A compromised router is exactly the case where a threat feed earns its keep, and until now Warden only ever inspected traffic passing *through* the box, never traffic it originated. The new switch is deliberately opt-in and carries its caveats on the page rather than in a manual, because the trade is real: **it cannot lock you out** — the web interface and SSH stay reachable from your network, so you can always switch it back off — but it *can* stop the router reaching things it needs, and a broad country block makes that easy to do by accident. Your DNS resolvers and time servers are exempted automatically, since a blocked resolver or a stopped clock would present as a whole-network outage rather than a router-only one. Be clear-eyed about the ceiling, too: malware with full control of the router can remove these rules, so this is a speed bump and — mainly — a **detection signal**. Blocks here are always written to the system log, whether or not general Warden logging is on, and the health watchdog reports them so a router that has quietly lost its own internet access says so instead of being discovered weeks later.
- **Fixed: Warden showed a large "total blocked" beside a country table that was empty or nowhere near it.** Not a counting error — a missing explanation. The total counts *every* block: manual bans, threat feeds and countries. The country table only ever counted the country rules. And because the feed rules are checked before the country rules — both simply drop the packet, so this only decides which counter moves — the big feeds absorb most of the hits and the country counters barely move. That is why it looked broken **sometimes**: it depends entirely on how much your feeds and your chosen countries overlap. The total now shows its own breakdown — countries, threat feeds, manual blocks — so the numbers add up. Anything a store written before this change cannot account for is shown as "unclassified" rather than being quietly folded into one of the named figures.
- **New: every tab of the firewall page explains itself.** Eleven tabs of object models, zones, egress defaults and forwards is a lot to meet cold. Each tab now opens with a plain description of what it is for, how it is best used, and a worked example — a real rule you could type in, not a placeholder — and carries a **?** button linking to the matching section of a new [firewall guide](FIREWALL-GUIDE.md). The guide covers the things only the code knew: that rate-limited rules are *skipped* rather than silently unlimited when the kernel module is missing, that MAC-address objects only work as a source, that port forwards bypass your zone policy by design, and that the URL and Keyword filters cannot see encrypted sites — with what to use instead.
- **Website-name (FQDN) objects now fill themselves from the router's own DNS.** The previous release deferred this on the grounds that this router's DNS service is compiled without the necessary support. **That was wrong** — it has had it all along; the check that said otherwise had been run against a stock binary from a different model, of a different processor architecture. No rebuild of anything was needed. The router now hands matching answers straight into the object as it resolves them, so a name behind a large rotating content network is tracked as it rotates instead of lagging a ten-minute timer. **The timer stays**, because this only sees lookups the router itself answers: a device using its own DNS server, or encrypted DNS, is invisible to it — as is any network where another machine on the LAN does the resolving. Entries now expire after an hour so a rotating pool cannot grow the list without bound.
- **Fixed: the Traffic Analyzer's per-network view named bridges, which nobody configures.** It showed `br54`, `br55`, `br56` — internal names that do not match the VLAN numbers you actually set up, and on the reporting router differed from them by two. Each network is now labelled with its name and VLAN alongside the bridge, so `br54` reads as `Guests (VLAN 52, br54)`. Renaming a network in the GUI relabels the chart with no loss of history. *(The bridge remains the stored identity behind the scenes — relabelling that would have orphaned every saved history series.)*
- **Fixed: Wi-Fi devices connected through an AiMesh node were listed as Wired.** The router classifies a device by which of its own radios saw it, or failing that by the port its traffic arrives on — and for a device on a mesh node, the answer to both is the cable or backhaul link to that node. It now consults the mesh's own client list, so a device on a node is reported as Wi-Fi, on the band it is really using. *(A wireless backhaul had the same fault wearing a disguise: the device was labelled Wi-Fi, but on the backhaul's band rather than its own.)* Deliberately narrow: it only corrects devices the router's own radios did not see, so a directly-connected client's first-hand information is never overridden, and a device that has since moved onto a cable is reported as wired.

## v2.4.1 — A firewall of Reaper's own, UPnP that consoles can talk to again, and mesh nodes you can update from one page
*This release folds in the v2.3.8, v2.3.9 and v2.4.0 source rungs. None of those published images — the firewall work spanned all three, and shipping a half-built rules engine was not worth doing.*

- **Fixed: UPnP stopped consoles connecting to games — a PS5 could not reach Call of Duty at all, with IPv6 pinholes on or off.** Two separate faults were doing this, and both are fixed here.
  - **The router was describing itself in a dialect many clients do not speak.** When a console asks the router "what are you and what can you do", the answer can be written to either the 2001 revision of the standard (IGD:1) or the newer one (IGD:2). v2.3.5 moved every build to IGD:2 — and while *discovery* stays backward-compatible, the description fetched immediately afterwards does not. A PS5 reading an IGD:2 description recognised none of the services in it, never got a control address, and so could not create a port mapping at all. This is well-known enough that the code already force-downgrades the description for Microsoft clients for exactly this reason; the console simply is not covered by that exception. The description is now IGD:1 again for everyone. **Nothing is lost in practice:** the router still *implements* the newer actions, it just no longer advertises the two extras (ask-for-any-free-port, and list-all-mappings) that broke the clients. If you want IGD:2 back, `nvram set upnp_igd2_desc=1`. *Upstream engineers, consulted while this was being traced, independently reached the same conclusion: stick with V1 unless you need IPv6 pinholes.*
  - **And turning on IPv6 pinholes now switches the newer description back on by itself.** The first fix, on its own, introduced a second silent no-op: the IGD:1 description omits the IPv6 firewall service entirely, so switching pinholes on gave you a daemon that supported them and a description that hid them. Enabling pinholes is an explicit request for a service that only exists in IGD:2, so it now implies that description. Pinholes off — the default — still gives you IGD:1 and the console fix.
  - **The router now records which description each device was served, and what that device called itself.** UPnP never logged this, which is why the report above took a build to diagnose rather than a log line. One line per discovery now names the version, the client, and its User-Agent — so the next report of this shape is answerable from the log alone, and a future release can downgrade one misbehaving device instead of everyone.
- **Fixed: an upstream defect that sent *all* traffic through the UPnP redirect table.** A patch carried in the 3006.102.8 base adds an unqualified rule that tests every packet crossing the router against every active UPnP mapping — outbound traffic included. The effect is that a mapping on some port rewrites a *LAN device's own outgoing connection* to a remote server on that same port. The field symptom is a console that cannot reach a game server at all while UPnP is on. Reverted. *(This is a different bug from the description problem above; the upstream engineers who reported it were explicit that the two are unrelated. ASUS has resolved it internally and Merlin is reverting it for 102.8_4.)*
- **New: a native firewall, built into Reaper rather than bolted onto the stock pages.** This is the large piece of work in this release, and it is **off by default** — nothing changes until you switch it on.
  - **You write rules about *things*, not addresses.** Define a device, a network, a service or a country once as a named object, then use that name everywhere. Groups combine them. A country object reuses the list Warden already downloads, so the two features share one copy of the data instead of disagreeing.
  - **Rules cover inbound, forwarded and outbound traffic**, on IPv4 and IPv6, and can carry a schedule, a rate limit and their own logging. The engine adds policy **on top of** the stock firewall rather than replacing it, so Gatekeeper, Warden, SDN and the base rules all keep working underneath.
  - **You cannot lock yourself out.** Every apply starts a countdown: if you do not confirm from the browser, the router puts the previous ruleset back by itself. The rollback is armed *before* the new rules go on, is driven by a scheduled task rather than the web server, and runs from a pre-written script — so it still fires if the thing you just broke is the web interface. As a last resort it removes Reaper's own rules and leaves the stock firewall in charge. A protective set of rules is always applied first, including the IPv6 neighbour-discovery traffic a network stops working without — a rule that killed it would otherwise pass the countdown unnoticed, because your IPv4 session would stay up the whole time.
  - **Per-device internet defaults.** Zone rules can say "this network may not reach that one", but every LAN device shares one interface, so they cannot say "this laptop gets no internet unless a rule allows it". That is now its own list — and it is anchored to the internet-facing side only, so a device denied the internet can still reach your printer and NAS. Cutting a device off the internet and cutting it off the network are very different requests.
  - **Port forwards that can be restricted by source and by schedule**, including "only from this country". Each forward installs its translation *and* the matching permission together, since a forward that translates a packet and then drops it is the failure this whole design exists to avoid.
  - **A compile preview** shows you the exact ruleset a change would produce, generated by the same code that would apply it — not an approximation of it.
  - **Backup and restore** for the whole configuration as text. Restoring replays the same save path an interactive edit uses, so an imported file faces exactly the same validation, and it lands in the draft — the countdown still gates it going live.
- **The firewall Status page answers "what is switched on", instead of printing the raw rule tables.** It used to render every netfilter chain in full — on a live router that is 40-odd chains and several hundred rows of counters, re-fetched every ten seconds, and unreadable without prior `iptables` knowledge. It now reports posture in five groups: core switches, the rules engine, Gatekeeper and Warden, content filters, and — the one most people actually want — **exposure**: what of yours is reachable from the internet right now, including NAT, forwards, triggering, DMZ, UPnP with its advertised version, the remote-admin port and SSH from the WAN. That was all technically present in the chain dump before, and functionally unreachable. The page no longer runs `iptables` at all, so the auto-refresh is cheap. Raw chains are still there over SSH for anyone who wants them.
- **The firewall's master switch now tells you what it is doing — and reports what is actually true, not what was asked for.** Turning the engine on or off used to give no feedback whatsoever, so a working switch and a dead one looked identical. It now shows a live "Working…" while the change is in flight and states the outcome when the router confirms it. That confirmation is **measured**, not assumed: the engine sets a marker as its final act, and only when its rules really went on — so the case where the network is not ready yet at boot reports as inactive instead of quietly claiming success. If it has not settled in about fifteen seconds, it says so and stays on screen rather than disappearing. Believing a firewall is live when it is not is worse than knowing something went wrong.
- **Fixed, from the same page: the backup box was blinding white on a dark page, and empty with no explanation.** The styling rule beside it only ever matched single-line inputs, so the box fell through to the browser default. It now matches the fields next to it, and both the note above it and the box itself tell you to press Export first.
- **You can see your mesh nodes and update them from the main router.** Two things were wrong. The page filtered itself out of its own node list using a field the router does not actually send — so **the router listed itself as one of its own mesh nodes**. And when the list came back empty, a failed request and a genuinely empty node table produced the same generic message, though they mean completely different things. Both fixed, and there is now an Update button that hands the firmware to every connected node the same way the stock AiMesh upgrade does. *(Not fixed: the existing per-node "open" button builds its address without the capability check stock performs, so for a node that does not advertise local access it can produce the wrong address. Confirming that needs a live multi-node mesh.)*
- **The setup wizard no longer drops you onto an unthemed stock page.** One step after the Reaper-styled credential screen, the Wi-Fi step appeared in full stock ASUS styling. That page could not be brought inside the Reaper shell — doing so re-triggers the first-boot check from within and recreates the v1.6.6b setup loop — so it had been excluded entirely, which also excluded the stylesheet. It now gets the stylesheet without the redirect: themed, still top-level, loop still fixed.
- **The dashboard gets the two controls the old Network Map had.** An internet on/off switch on the Internet card — persistent across a reboot, not a session-only disconnect, and it asks before turning the internet *off* — and, on the Storage card, a disk selector that appears once two or more USB disks are attached, replacing the old "+N more disk attached" line. *(This also fixed a pre-existing fault in the Internet card's own refresh: a single failed request stopped it updating for the rest of the session — and a WAN restart is exactly what causes one.)*
- **New: export your device list.** The Devices page can now save every device's name, MAC and IP as CSV, JSON or HTML. It exports the **whole** inventory rather than whatever the filter currently shows, and the names are the ones you gave them, so the file matches what is on screen. Note that this file is deliberately unsanitised — unlike the diagnostic bundle, which strips personal data on purpose — so it is not something to attach to a bug report or post in a forum.
- **The Security Posture panel on the dashboard is now clickable.** Every row told you the state of a setting and left you to work out which page changes it. All fourteen now take you there, and the two firewall rows land on the tab that owns the setting rather than the page's front door.
- **Fixed: during a firmware flash, the page behind the header showed through it.** With the black curtain up, the version chips and labels appeared superimposed over the Reaper logo. The header was not moving and was not being covered — it was being *dimmed with transparency*, and transparency does not just fade something, it makes it see-through, so content sliding underneath showed straight through it. It is now dimmed in a way that leaves it solid. The shell also holds still during a flash and brings the curtain's own message into view, rather than leaving you parked halfway down a page that has stopped responding.

**Known and not fixed in this release:** the Professional Wi-Fi page still takes around 15 seconds on its first load after an upgrade — the mechanism is now understood, but the fix differs completely depending on whether the cost is the page or the wireless driver settling after a reboot, and that needs one measurement on real hardware rather than a guess. Two firewall items are also deliberately deferred: a rule tracer, and using DNS to keep website-name objects up to date — the latter because this router's DNS service is compiled without that capability, and rebuilding the most critical service on the box deserves its own release and its own hardware validation. Website-name objects keep refreshing on a ten-minute timer meanwhile. *(**Correction, 2026-08-14:** the DNS reason given here was wrong — the service has had that capability all along, and the check that concluded otherwise had been run against a stock binary from a different model and processor architecture. No rebuild was required and the feature is implemented in the unreleased rung above. The rule tracer remains deferred.)*

## v2.3.7 — The Wi-Fi pages stop misleading you, mesh nodes show their firmware, and Professional opens quickly
- **The Professional Wi-Fi page opens much faster.** It was asking the router for its wireless settings **one at a time — 116 separate questions** — and none of the page could be drawn until the last answer came back. On a three-radio router, 29 of those questions were about a fourth radio that does not exist. It now asks once, and only about the radios the router actually has, so the page adapts by itself to any model. Nothing you can see has changed; the page simply stops making the router work for it. *(If the page still feels slow after this, the cause is elsewhere and worth reporting — this removed a large amount of work, but it has not yet been timed on hardware.)*
- **Auto Scan now assigns the channel it told you was best.** On 5 GHz it used to rank individual narrow channels and then quietly apply the *wider block containing* the winner instead — so it could report channel 44 as best and set 36, which read as the tool ignoring its own results. It now measures at the width the radio will actually run, so the entry it ranks and the channel it sets are the same thing.
- **Auto Scan covers each radio's full range and locks in the winner.** The channels to sweep are taken from what each radio itself reports rather than a fixed list, so a router with two 5 GHz radios (or two 6 GHz radios) sweeps each one across only the channels that radio supports, and regions outside the US work without a code change. When a sweep finishes it now applies its winner instead of putting the old channel back and waiting for you to press a button. **Two things worth knowing:** radar-detection (DFS) channels are deliberately not swept, because each one requires a 60-second listening period with the radio off the air — up to ten minutes on some — which would turn a scan into a long outage; and applying a channel takes that radio off automatic channel selection until you set its control channel back to Auto. Both are now stated on the page.
- **You can see your mesh nodes' firmware from the main router, and update them from there.** The firmware page lists every AiMesh node paired with this router — name, address, the firmware version it reports, and whether it is online — and gives each online node an Update button that opens that node's own firmware page, where you pick an image and the node flashes itself. The image is never relayed through the main router. Update one node at a time and let it come back before starting the next.
- **When adding a mesh node finds nothing, the router now records why.** "Search for node" could come back empty with no explanation anywhere. There are two points where a discovered node is discarded for having incomplete information, and neither said anything. Both now write a line to the system log naming the node and exactly what was missing, so the next failed search explains itself instead of needing to be reproduced while someone watches. This changes no behaviour — it only makes an existing silence audible.
- **Smart Connect wording.** The note explaining the "- -" columns claimed 6 GHz is left out of Smart Connect by default "on this model". That is only true on some models and configurations, and the page is shown on all of them — and it was redundant anyway, since which radios take part is visible directly above it. Removed; the rest of the note stands.

## v2.3.6 — A workaround for a Broadcom bug that can permanently freeze saving settings
- **Fixed (worked around): a router can reach a state where saving a setting never completes, while everything else keeps working.** The symptom is unhelpfully quiet — the router stays up, SSH and the web interface still respond, traffic still flows — but one process is stuck forever, a CPU core is being consumed doing nothing, logs quietly fill, and whatever setting was being written is never actually saved. It gets more likely the longer a router has been up.
  - **The cause is in a closed Broadcom library** (`libnvram.so`), found by catching it live and then confirming it instruction-by-instruction in the shipped binary. Every process that touches settings opens a small kernel channel identified by a number, and this library uses **the process's own ID as that number**. It also keeps a record of *"which process am I"* — and the defect is that the number being used and that identity record are **the same piece of memory**. Whenever the two disagree, the library decides the process must have changed and starts over **without closing the channel it already opened**. There are two different ways to make them disagree, and both happen on ordinary routers.
  - **One channel is abandoned on every startup, on every router — no coincidence required.** Most background services read a setting *before* moving themselves into the background, and moving into the background gives the running copy a different process ID while it inherits the channel opened under the old one. The identity record and the real ID now genuinely differ, so the library starts over, opens a second channel under the new ID, and abandons the first. That abandoned number stays occupied while belonging to no running process. Confirmed on a live RT-BE96U: **six abandoned numbers, and four services each holding two channels, twenty-one minutes after a clean boot** — with nothing malfunctioning and nothing yet stuck.
  - **Those abandoned numbers are what eventually freezes something.** Process IDs are handed out in sequence and wrap around — every 32,768 processes on this hardware — so sooner or later a new process is handed a number one of those abandoned channels is sitting on. Now the conflict is real: the library cannot use its own ID and tries the next nine along, and *this* time each attempt overwrites the identity record. One such collision is survivable by itself — it finds a free number, and the mess disappears when that process exits. The damage comes when the affected process **stays running and goes on saving settings**: its record of its own identity is now permanently wrong, so every later call starts over and abandons another channel, until all ten are gone. After that it retries a failing send **forever**, with no pause, holding a lock that blocks every further settings operation *within that process* — roughly sixteen system calls per attempt, as fast as the processor allows. That process is finished; the rest of the router carries on, which is a large part of why this is so hard to notice.
  - **Why it keeps recurring, and why it is still hard to catch.** The abandoned numbers are produced by healthy services during a normal startup, not by anything already broken, so every router carries a handful from the moment it finishes booting — and the ID counter sweeps past every one of them on each wrap, which on a live RT-BE96U took between one and two hours. But a sweep on its own is harmless: measured on that hardware, tens of thousands of short-lived processes passed over all six abandoned numbers without producing a single freeze. What it takes is one of the *long-running* services to restart onto one of those numbers and then carry on saving settings. That is uncommon, unpredictable, and grows likelier the longer a router runs — which is exactly the shape of a complaint that has followed this platform for years without ever being pinned down.
  - **The workaround, and what it does not do.** The freeze depends entirely on an attempt failing with "address in use". Reaper now ships a small piece of its own code that sits beside the Broadcom library (it does **not** modify it) and, *only* after such a failure, asks the kernel to pick a free number instead. Everything else is passed through untouched. **This prevents the freeze, not the abandonment:** the startup case above never fails with "address in use" — the new ID is free — so those channels are still abandoned exactly as before, whether this is switched on or off. What changes is the outcome when something later lands on one: a rescued conflict and a line in the log, instead of a process stuck for good. Only Broadcom can fix the underlying leak.
  - **It is switched off by default.** The mechanism it uses applies to every program on the router, and while the defect itself has now been observed on real hardware, this workaround has not yet run there — so it ships inert and changes nothing until you deliberately enable it with `nvram set wlcsm_bindfix=1`, then commit and reboot. Setting it back to `0` removes it on the next boot (`/etc` is rebuilt from scratch each time, so nothing lingers). When it is on, every rescue writes a line to the system log naming the process and number involved, so you can see whether the problem exists on your router at all. Read that log on the **System Log** page, or as the file `/tmp/syslog.log` over SSH — **not** with `logread`, which returns nothing on this platform because the log is written to a file rather than to the in-memory buffer `logread` reads.
  - *Also worth recording, for anyone chasing this elsewhere: the Broadcom code prints its failures to standard error rather than the system log — even though it already links the routine that would log properly. On a router that means these failures normally reach nowhere at all, which is a large part of why the problem has gone unexplained for so long.*

## v2.3.5 — Counters that survive a reboot, UPnP that keeps working, and a first-boot setup you cannot walk past
- **Fixed: Warden's blocked-hit counts reset on every reboot and firmware upgrade, and the per-country list never accumulated at all.** Three separate faults were stacked here. The running counts were only ever saved to flash by a script that runs *after* the firewall rules are torn down — but on a reboot, a shutdown, or a Save & Apply, the teardown happens first, so by the time anything went looking the counters were already gone. The per-country table was worse: it had no saved copy whatsoever and was read straight from the live firewall rules, which are deleted and rebuilt every time anything touches the firewall. That is exactly why the downloaded blocklists survived a reboot while the numbers next to them did not. And nothing saved on a timer, so an unclean shutdown lost everything since the router last armed. Warden now banks both the total and the per-country counts to internal flash, zeroing what it saves so it can run from every path that would otherwise lose them — including a 15-minute checkpoint — and it writes to flash only when something actually changed, so an idle router costs no wear.
- **New: you can choose how long Warden's statistics are kept.** A *Reset interval* setting on the Warden page offers Never (the default, unchanged behaviour), 24 Hours, 7 Days, 1 Month or 3 Months, and a *Save block statistics* switch turns persistence off entirely if you would rather the numbers only cover the current session. The Blocked-hits tile now says what period it is counting, and the Long-Term Storage page shows the Warden row's real start date and size instead of a dash — which is what the "no date next to it" report was looking at.
- **Fixed: UPnP port mappings stopped working after a while, and nothing said so.** Anything that rebuilds the firewall — reconnecting the WAN, a DDNS update, toggling a VPN, saving any firewall or port-forwarding setting — wipes every active UPnP, NAT-PMP and PCP mapping. The router was supposed to put them back, but the signal it sent only told the service "your public IP changed"; it re-added nothing. The service still had the mappings in memory, so it kept telling programs "that port is already forwarded" — the program stopped asking, the router's own page still listed it, and no traffic was forwarded. Every layer reported success. Consoles losing their NAT type hours after boot, game hosting failing, downloads with no incoming connections, cameras losing remote access: all one bug. The service is now genuinely restarted, which reloads every mapping with its remaining lease time.
- **UPnP now presents itself as an IGD:2 gateway by default.** Before, the newer standard was only enabled if you also turned on IPv6 pinholes — a setting most people sensibly leave off — so IPv4 clients silently fell back to the 2001 revision and lost the ability to say "I want this port, but give me any free one if it's taken". That is the difference between two consoles (or two of the same game) both working and one of them failing. The two things are now separated: the newer standard is always on, and the IPv6 pinhole switch does only what its name says. The label was corrected to match.
- **Closed a way for a device on your network to hijack the router's own inbound connections.** A LAN device could ask UPnP for the port your VPN server listens on and be given it, silently taking inbound VPN connections away from the router. The "secure mode" setting does not help, because pointing the port at yourself *is* the attack. The router now refuses UPnP requests for its own OpenVPN, WireGuard, IPSec, SSH and web-admin ports (a new *Protect router service ports* switch, on by default), and the default range no longer hands out privileged ports below 1024 — the code already promised that, but the check could never run.
- **Fixed: the DHCP Leases page showed a dash instead of the device name, for devices the Devices page names perfectly well.** The column was being filled from the router's live network-map, which only lists devices it currently knows about — so anything that had aged out of it, or was never catalogued, came up blank even though you had given it a name. The name now comes from the same place the Devices page reads, so the two agree. A device name or a self-reported hostname containing a quote also used to break the whole table and leave the page blank; both are now escaped properly, which additionally closes a way for a device on your network to run script in your browser by choosing a crafted hostname.
- **The Smart Connect Rules page explains its "- -" columns instead of looking broken.** A band shows dashes when it is simply not part of the Smart Connect group — its settings still exist and come straight back when you add it. The page now says so, on the cell and above the table, and mentions that 6 GHz is left out by default on this model. *(Investigating a report of this also confirmed no fault in the page's band mapping: the reporting router had 2.4 GHz deliberately excluded, and every value on screen matched its saved configuration.)* A genuine markup bug behind those cells — a table cell that was opened and never closed, so the following cells nested inside it — is fixed at the same time.
- **First-boot setup can no longer be skipped, and it now actually asks for the Wi-Fi password.** Two problems. The Wi-Fi step was never reached: after you set the administrator username and password, the router sent you to the dashboard, and the dashboard is one of the pages that does not run the check that would have asked for a Wi-Fi password — so a router could finish setup with new admin credentials and the factory Wi-Fi password still in place. And the whole wizard could be bypassed by typing the address of almost any settings page directly, because the enforcement lived only in a script that fewer than half the pages load. Setup is now enforced by the web server itself, so every page is covered, and the wizard owns both steps in one place: it will not release you to the rest of the interface until the administrator credentials *and* the Wi-Fi password have been changed. This follows the no-default-credentials guidance that consumer router security baselines are converging on.
- Safety, because a setup gate that misfires would be worse than the bug: it only ever triggers on a router that is genuinely unconfigured, so upgrading an existing router never sees it; it does not apply to repeater or media-bridge modes, which legitimately have no wireless settings of their own; AiMesh node onboarding is unaffected; and a single setting, `reaper_fbdone=1`, releases the interface over SSH if anyone ever does get stuck.

## v2.3.4 — Traffic Manager and Traffic Analyzer fit the screen again
- **Fixed: the QoS and Traffic Analyzer pages rendered oversized and ran off the right edge of the screen, with no scrollbar to reach the rest.** Both pages carry a "FAQ" panel that slides in from the right, and while closed it is parked just off the edge of the page. A change in v2.3.3 — the one that made "please wait" overlays centre on your screen instead of inside the framed page — swept that parked panel into the same rule, which changed how it is positioned. As a side effect its off-screen parking started counting as *real page width*: the page reported itself about 460 pixels wider than it was, the shell stretched the frame to match, and every panel on the page stretched with it. The last column then sat outside the window. Only these two pages were affected, because they are the only two with that panel. The panel is now excluded from that rule and behaves exactly as before.
- **And the reason there was no scrollbar: the content area could not scroll.** The container holding the page is a grid cell, and a grid cell will not shrink below its contents unless told to — so instead of scrolling, it grew, pushing the page past the edge of the window. It is now allowed to shrink, which means any future case like this pans on a scrollbar rather than hiding content. The failure mode becomes visible instead of invisible.
- Nothing else changed in this release. v2.3.3 was built and flashed before this was found, so the fix ships as its own version rather than altering what v2.3.3 means — two different images should never share a version string.

## v2.3.3 — The browser stops talking to ASUS entirely, the post-flash freeze finally explained, QoS ships a validated profile, and traffic accounting that can see offloaded flows
- **The de-cloud is finished: no page in the web interface contacts ASUS any more.** Earlier releases closed the device/app **icon** callbacks (v2.2.0, v2.2.5); this one closes the wider **data** surface that was still live — the FAQ index, the DNS-provider list, the SDN scenario list, the model-name table, the AiMesh node-icon table, the timezone table, the ISP list, the IPTV profile list, the Open NAT game database, the VPN partner server lists, and 27 hardcoded game-artwork URLs. Each now uses the copy already bundled in the firmware, so opening a settings page no longer tells ASUS which pages you visit, which devices you own, or when your router is in use. The worst of them was on the Open NAT page: it fetched a game database from ASUS and, **if that request failed, retried every five seconds forever** — a router with no route to ASUS would keep trying for as long as the page stayed open. Verified against the actual staged filesystem rather than the source tree, which matters: several call sites the source appears to contain are already inert, and one that looked dead was live.
- **The per-game artwork on the Open NAT page is gone rather than re-hosted.** Those images were publisher-owned game art (Call of Duty, Destiny, Diablo, FIFA, League of Legends, Overwatch, Minecraft, Fortnite and the rest) that ASUS served from its own CDN. Dropping the remote fetch is one thing; copying that art into a redistributed firmware image is not something this project can do, so the per-game look is retired. In practice nothing was lost visually — once the CDN URLs were removed, all 104 per-game style rules pointed at the same bundled placeholder anyway. Those 414 lines are deleted and the placeholder now comes from the two base classes, so a game card still renders.
- **The AdGuard DNS page stopped fetching its banner from ASUS.** It loaded a promotional image from the ASUS CDN and used the copy already bundled in the firmware *only as an error fallback* — so simply opening that page announced the visit before falling back. It now uses the bundled image directly. (Caught by checking the built filesystem rather than the source tree: an earlier pass had wrongly concluded this page didn't ship, because the build copies overlay *contents* into the web root and the overlay directory never appears in the image.)
- **Fixed: opening the AiMesh page could throw a script error and leave the client list half-built.** When one of the page's data requests didn't come back (the router closes idle connections after five seconds, so this happens on a busy box), the client-list builder tried to read a field off an empty reply and aborted partway through — leaving the device list incompletely populated and stopping the page's refresh cycle. The same guard the neighbouring code path already used is now applied, so a failed request simply skips that refresh and the next one recovers.
- **The AiMesh node panel is tidier.** The ASUS product image (and its hidden "change model icon" control, which was the only consumer of one of the removed ASUS callbacks) is gone, and the node's name and MAC address moved from the lower-left of the banner to the upper right.
- **Hardware QoS no longer stands up the download-side redirect it can't use.** With either hardware QoS engine selected, the firewall still installed an ingress redirect that hands every incoming packet to a software queue — but only the *software* QoS engine ever attaches a queue to it, so under hardware QoS it did nothing except route traffic through an extra hop. It was switched on by a setting that ships non-zero by default, so it applied on essentially every hardware-QoS router. Now gated to the engine that actually uses it. *(This also corrects the earlier diagnosis of this bug, which named the wrong setting and the wrong location; clearing the download-bandwidth field, the previously reported workaround, was never what disabled it.)*
- **Closed an injection path in the Data Export settings.** The analytics export builds a configuration file for the download tool it uses; the destination URL and API token were written into that file inside quotes, and neither was checked when saved. A quote inside either value closed the string early and let the rest be read as **additional tool directives** — including one that writes a downloaded file to any path on the router, as root. The values are now rejected at save time if they contain a quote, backslash, or control character, and the generated script refuses to run if one reaches it another way. *(An audit item asked whether these settings could be injected into a shell command — they can't; the generated script is a fixed template and every setting is read into a quoted variable. The exposure was one layer over.)*
- **The AI Advisor's lab build no longer returns your Wi-Fi password.** Its output passes through a filter that redacts secrets, but the filter only recognised `key: value` shapes — and ASUS stores Wi-Fi credentials as a `>`-separated record, so a passphrase read straight from the settings store went out unredacted. The filter now understands that record format too. Affects only the lab/diagnostic build, which is not part of either shipped image.
- **Internal cleanup.** Roughly 390 lines of unreachable code removed — a disabled VPN-advertising block, an icon helper left as an empty stub by an earlier fix along with the call that guarded it, three upstream commented-out blocks that still carried ASUS URLs, and a file no shipping page had included in years. Each removal was checked for reachability *and* for anything still referring to it before being cut. The health watchdog's start-up log line also stopped naming a fixed path for its diagnostic dumps, which is wrong whenever they've been relocated to USB or JFFS — it sent a live investigation to the wrong directory.
- **The browser really does freeze after a firmware upgrade — and now we know why.** v2.3.2 gave the flashing overlay an escape hatch, on the theory that the page only *looked* frozen because a dead veil had no dismiss path. That was a genuine defect, but it was not this one: the tab was actually locking up. Every poll round scheduled **two** successors instead of one, because a failed request fires both a state-change event and an error event and each was wired to the same handler. While the router is rebooting, every request fails — so the chain doubled each round, and within a couple of minutes the page was running thousands of overlapping timers and the browser stopped responding to anything. That is why End Task and relaunch was the only way out. Every completion path is now one-shot: whichever event arrives first wins and the rest are ignored, so a round can schedule exactly one successor. *(This supersedes the v2.3.2 note's account of the same field report — the escape hatch treated a symptom.)*
- **"Please wait", countdowns and progress bars now appear in the middle of your screen.** Reaper pages render inside the shell, and an overlay pinned to the *page* is pinned to the frame's viewport, not the window's — so on a tall page or a scrolled one, the waiting message could sit well below the fold or off to one side, exactly when you most need to see it. Overlays now anchor to the shell's visible slice, so they land where you're looking regardless of how far the inner page has scrolled.
- **Closed a stored cross-site-scripting hole reachable from any device on the LAN.** The client-picker dropdown — used by the QoS, firewall, port-forward and parental-control pages — built its entries by pasting the device name into an HTML attribute that is itself JavaScript. Two parsers read that text in sequence, so HTML-encoding it (which the code did) was the wrong escape: the browser decoded the entities *before* the JavaScript ran, and an apostrophe in the decoded text ended the string and let what followed execute with the administrator's session. A device name is not trustworthy input — it comes from whatever hostname a machine announces over DHCP, so any device on the network, without logging in, could plant one and wait for an admin to open a page. Names are now escaped for both layers, and long names are shortened without breaking the encoding. The last remaining ASUS URL in a shipped script went at the same time.
- **Hardware QoS ships a working classful profile instead of a placeholder.** The defaults now carry rates, per-class scheduling, class names and starter rules that were set up and measured on a live router rather than left as an even five-way split: **Web/VoIP** and **Gaming** run as strict priority (latency first), while **Streaming**, **Downloads** and **Default** share the remaining capacity by weight, so a large download can use the whole link when nothing else wants it but can never starve a video call. Because that reordering moved Gaming and Streaming between queues, the codepoint map that feeds them was reordered to match — the queue index is what both actually key on, and the two lists have to move together. Starter rules for conferencing, SIP, game consoles, Steam, BitTorrent and web traffic ship enabled. *(v2.3.2 corrected an inversion in the same map; this is a re-alignment to the new class order, not a repeat of that fix.)*
- **QoS preset rules no longer sort traffic by how much it has transferred.** Several shipped rules matched on bytes-transferred, which sounds like a way to catch bulk transfers but classifies by *duration* rather than *kind*: a long video call or a long game session eventually crosses the same threshold a file download does, and gets demoted into the bulk queue for exactly as long as it keeps going. Rules now classify on what the traffic is, not how long it has been running.
- **The Traffic Analyzer was blind to the fastest transfers on the network.** It read its byte counts from the hardware accelerator's flow table, which lists only flows the accelerator has taken over — and those are disproportionately the big, steady ones. The result was backwards from what you'd expect: a device pulling a large fast download was the *most* likely to be missing from the list, and the bridge total under-reported. Counts now come from the kernel's connection table, which the accelerator folds its own statistics back into, so both offloaded and CPU-handled traffic are counted once and only once. Per-bridge attribution is derived from each interface's real subnet rather than assumed — previously only the main LAN's subnet was tested, so **every guest / SDN client was dropped from the totals entirely**. The router's own LAN address also stops appearing as if it were a client: it now goes to the same hidden "Router" bucket the Traffic Analyzer already used, which closes the last "IP in the MAC slot" row left after the v2.3.0 one-row-per-device work.
- **The Network Map page is retired and the dashboard takes its place in the navigation.** It was stock ASUS scaffolding that Reaper had progressively hollowed out, and the pieces people actually used — device list, connection status, per-device detail — now live on the dashboard and the Devices page. The dashboard button moves out of the header into the navigation slot the Network Map occupied, so the header stops carrying a control that duplicates a menu entry.
- **Translations extended.** The Firmware Upgrade page's strings — English-only in all 25 packs when the page shipped in v2.3.1 — plus the Data Export and USB/storage strings are now translated across all 24 non-English languages. On the AiMesh page, a node's model name is centred over its MAC address instead of sitting off to one side.
- **The de-cloud is now enforced by the build, not just done once.** Removing the callbacks is only as durable as the next edit that adds one back, so the packaging gate now **fails the build** if any ASUS-CDN reference reaches the *staged* web root in a request-shaped position — `fetch`/XHR/`ajax`/`getJSON`/`new Image`/`.src=`/`script|img src=`/`link href=`. It checks the filesystem that actually ships rather than the source tree, which is the only way to get a true answer here: several call sites the source appears to contain are already inert, one that looked dead was live, and the per-model UI overlays (ROG/TUF/GS/UI4) hold ~133 more references that no Reaper model ever builds. Ordinary `href` links to ASUS support pages are deliberately *not* gated — user-initiated navigation is not a silent callback.
- **Project housekeeping, both of which reach users indirectly.** The publish pipeline now refreshes the on-router update manifest itself: a release could previously be published while `updates/manifest_3006.txt` still advertised the previous version, so routers kept reporting "up to date" — which is exactly what happened to v2.3.2. And the firmware images are no longer committed into the source repository; they were only ever there for file-tree visibility, nothing consumed them (the router reads the manifest, and the release workflow attaches assets built in the clean room), and they accounted for ~830 MB of the ~835 MB repository. Published releases and their downloads are unaffected.
- Built on the **RT-BE96U** first (both variants); sibling fan-out and on-device validation to follow. The changes in the second half of this list were cut as a source rung on 2026-08-11 and are **not yet built** — they carry no on-device validation.

## v2.3.2 — QoS finally classifies the way its labels say, a firmware-flash screen you can always escape, and a small security sweep
- **The firmware page's flashing overlay can no longer trap you.** (Field report 2026-08-10: mid-flash, the page appeared completely frozen — no click did anything — and the only way out was killing the browser.) The full-screen "please wait" veil had no dismiss path, so if its status polling ever died the page was inert by construction. It now shows a **Close button (and accepts Esc)** immediately on any terminal state and, on any long-running one, after 25 seconds; a live **elapsed-time / phase heartbeat** renders inside the overlay so a stalled operation looks visibly different from a working one; and an unexpected page error reveals the escape instead of stranding the overlay silently. Dismissing only clears the overlay — it cannot stop a flash already running on the router, which is why it isn't offered in the first seconds. Also fixed: the manual-upload flow could declare a good image "rejected" after ~2 minutes while the router was in fact still verifying it; the window is now ~5 minutes.
- **Hardware QoS (classful mode) classification corrected end-to-end.** A review of the classful engine found the defaults working against their own labels, all fixed: **unmatched traffic now lands in the class actually named "Default"** (an off-by-one sent it — games included — into "Downloads", the same queue as bulk file transfers); the **DSCP-to-class map was inverted** (gaming codepoints went to the Streaming queue and vice versa — a game that marked its traffic correctly could never reach the queue named for it); **committed minimum rates are now budgeted** (the shipped template committed exactly 100% of the port, leaving unclassified and LAN traffic no guarantee and the scheduler no slack — anything over 85% is now scaled down proportionally, preserving your ratios); and **QoS with empty bandwidth fields now behaves as QoS-off** instead of silently reclassifying everything with no shaper at all (all of the cost, none of the benefit). The downstream **DSCP→WMM stamp is now opt-in**: defaulting it on promoted ordinary web browsing to the Voice class on the air, where it preempts genuinely latency-sensitive traffic. Robustness alongside: queue configuration is no longer destructively rewritten on every WAN event when nothing changed, apply errors are logged instead of discarded, and saved schedules/rates are grammar-checked on save. *(These were found while investigating a high-idle-latency field report and do **not** explain it — that investigation remains open.)*
- **Four small confirmed items cleared from the consolidated backlog.** The QoS diagnostic read the port shaper that only the classful engine uses, so a healthy classless box always looked uncapped (this false reading sent an earlier investigation down a blind alley) — it now names the running engine and reads the shaper that engine actually uses. A VPN-provider setup path quoted two profile values into a root shell command such that a single apostrophe escaped the quoting (admin-authenticated, but a real injection) — the values are now accepted only against a strict grammar. The password check compared hashes in a way that took measurably longer the more of the hash matched (not practically exploitable — the attacker can't choose the hash and logins are rate-limited — but a password check should leak nothing); it is now constant-time. And the rwatch health watchdog now writes at most one incident dump to flash per 30 minutes under a flapping condition (every failure is still logged; only the repeated flash writes are suppressed).
- **This is the first version built and released through the public clean-room CI pipeline** (GitHub Actions builds every model from the published patch series and publishes the release assets directly — see `docs/CI-PUBLIC-BUILD.md`). Source rung cut 2026-08-10; on-device validation to come.

## v2.3.1 — A native Firmware page: working update check, one-click verified install, manual upload
- **New native page: Administration → Firmware Upgrade is now a Reaper page (`Reaper_Firmware.asp`).** It shows the installed model, variant (Standard / AI Advisor), and Reaper version; checks the Reaper release channel on demand; shows the release notes inline; and — new capability the stock page never offered — **downloads and installs a published update in one click**, with a live download bar, then verifies and flashes and returns you to the sign-in page when the router is back. A **manual upload** section (with a real upload progress bar) replaces the stock file-upload flow, and the **scheduled daily check** opt-in lives on the same page. The stock page remains on disk as a fallback.
- **Fixed: the update check finally works from the GUI — it was silently asking ASUS instead.** On builds with AiMesh config-sync compiled in (all Reaper models), the stock page's "Check" button routed through the closed cfg_mnt helper to **ASUS's own firmware servers**, so the Reaper release-channel check added in v2.1.6 never actually ran when you clicked Check — and since the dashboard "new firmware" badge is driven by that check's result, the badge never fired either. Both the new native page and the stock fallback page now drive the Reaper manifest check directly. Also fixed: the release-note fetcher wrote its result where no page read it (and failed outright when invoked without arguments); notes now appear both on the new page and in the stock viewer.
- **One-click install is verified end-to-end before anything is flashed.** The published manifest now carries each image's **SHA-256 and size**; the on-router installer accepts download URLs only from the Reaper GitHub release channel, re-checks that the image is for **this exact model** (a GT-BE98 can never fetch a GT-BE98 Pro image) and **this exact variant** (a noMCP router refuses an MCP image and vice versa), requires the checksum to match after download, runs the platform's own firmware image check, and only then flashes using the same sequence as a manual upload. If any step fails, the download is discarded and nothing is written. Older manifests without checksums downgrade the page to notify-only — it will tell you about the update but won't offer the one-click install.
- Nothing about the update system phones home by default: the scheduled check remains **opt-in** (off after a factory reset), the manual Check is user-initiated, and both only ever contact the Reaper release channel on GitHub — never ASUS.
- New firmware-page strings are currently English in all 25 language packs (translation pass planned).

## v2.3.0 — Animated header, a standalone health-probe switch, a real "Store only" mode, and one row per device
- **The sign-in, set-password, and logout screens now show an animated model header.** It plays once when the page finishes loading and freezes on the finished "RT-BE96U REAPER" wordmark; the static logo is unchanged everywhere else (dashboard / shell header). It is delivered as an **animated PNG (APNG)** through the existing image path, so it needs no change to how the login page is served. (An earlier attempt using an `.mp4` never displayed: the login page is shown *before* you authenticate, and a logged-out browser is only served a fixed set of image types — video isn't one of them, but an animated PNG is, so it simply works. The dead `.mp4` handler was reverted, leaving the pre-authentication surface exactly as it was.)
- **New: a standalone "Health probe" switch on Administration → Data Export.** The per-device connection-health probe (round-trip latency, jitter, loss, TCP connection count/state) can now be turned on or off **independently of export**, so you can collect and watch the metrics — and use **Preview payload** — without configuring any external destination. The probe used to come on only as a side effect of enabling export, which is why Preview showed empty braces `{}` when export was off; Preview now shows a clear message ("enable the probe", or "collecting — no samples yet") instead.
- **New: a real "Store only" retain/send mode.** The Long-Term Storage export control now has **four** modes — **Off** / **Store only** / **Store + Export** / **Export only** — and the misleading "Off" label is fixed. "Store only" keeps the connection-health history on the router with no external push; "Off" now genuinely retains and sends nothing (it previously kept a local copy whenever a durable location was set, which is exactly what made the old "Off — history kept locally" label wrong). Stored history lands in the RAM / JFFS / USB location already selected at the top of that page.
- **Fixed: a device could appear twice** in the health metrics, the analytics export, and the Traffic Analyzer — once by its MAC and once with its **IP address in the MAC field**. When a traffic flow's source MAC couldn't be resolved at that moment (an offline device whose ARP entry had aged out), the collector created a second, IP-keyed entry for a device it already tracked by MAC. It now reuses the real MAC-keyed entry for that IP, and a lightweight once-a-second sweep folds away any phantom created before the MAC was known (or restored from a pre-fix history database), so **each device shows exactly once**. Existing duplicates clear on the next reboot.
- **Warden's total-blocked count truly persists now.** A boot-time cleanup was wiping Warden's persistent baseline on every start (it had survived the earlier v2.2.1 persistence fix), so the total could still reset. That cleanup is now gated so the baseline is only removed when Warden itself is turned off.
- **The apply / reboot overlay also locks the header and side navigation while a framed page finishes loading.** Building on the full-screen overlay from v2.2.5, the shell now disables the top header and side rail during a framed page's own load spinner, so you can't navigate away at a critical moment.
- **The firmware update-check log messages now say "Reaper", not "Merlin".** Two informational log lines still carried the upstream name; rebranded (behavior unchanged).
- **The Traffic Analyzer's "By network" view no longer shows a "Router" row.** That bucket was the router's own self-traffic (NTP, update checks, the latency probe), not a real network; it's hidden from the per-network breakdown (still collected internally).
- **The Roaming Assistant help text is simplified to just "0 = off"** on the all-bands WiFi Professional page (owner request).
- **Pre-distribution review hardening.** A four-agent audit of the v2.3.0 changes (daemon, httpd/CGI + pre-auth surface, UI, cross-component coherence) found **no shipping blockers**; the follow-ups it surfaced were folded in: the standalone Health-probe toggle now **refuses to turn off while an export mode is armed** — doing so would freeze the pushed feed while the exporter kept sending the last snapshot, so the probe stays required until you set the retain/send mode to Off (turning the probe *on* is always allowed); the Long-Term Storage export note now states that any non-off mode enables the probe; and a dead leftover `.mp4` handler was removed from the httpd source (it was in an unlinked table — cosmetic slop from the mp4→APNG work). Two rtrafd data-quality caveats were reviewed and kept as documented tradeoffs (a device-name mis-attribution only under DHCP-lease reuse of an offline device's IP; a negligible byte undercount when a duplicate row is folded away).
- Built + shipped on **all five models** (RT-BE96U + RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro), **both variants each** (with and without the AI Advisor) — each model built as itself with its own banner + animated header, verified by the port guards (correct BUILD_NAME/base/SAMBA4, one per-model APNG with no cross-model clobber, dictionaries in lockstep).

## v2.2.7 — Internal cleanup: one shared device-name resolver, one byte formatter, consistent theme colors
- **One shared device-name resolver instead of three.** The Connections, Traffic Analyzer, and QoS pages each carried their own copy of the "look up a device's friendly name" logic, keyed three different ways, which is why a renamed or offline device could show its name on one page but a bare IP/MAC on another. There is now a single resolver (`reaper_util.js`) that indexes devices by **both** MAC and IP and merges your saved names with the live client list — so **offline devices now keep their names on the Connections and QoS pages too** (the Traffic Analyzer already did this since v2.2.5). No visible change beyond that consistency. (The stock Network Map and DHCP pages keep their own built-in name field.)
- **One byte-size formatter.** The Traffic and Connections pages had slightly drifted copies of the "format bytes as KB/MB/GB" helper; they now share one **decimal (1000-based, KB/MB/GB)** formatter. The only visible effect is that the Connections page now shows one or two decimals on large byte totals (e.g. `5 GB` → `5.00 GB`), matching the Traffic Analyzer. Bandwidth-limit **caps** on the QoS page are a bitrate, not a byte count, and keep their own formatting.
- **Consistent accent colors across the Reaper pages.** A few theme colors had drifted between pages (the same role defined with two slightly different values). These are unified: the amber accent, the "danger" red on the first-boot screen, and a font-name quoting inconsistency (which rendered identically). Purely cosmetic consistency; no layout changes.
- **Not a bug (closed):** a long-standing review note about a "spurious leading `<`" when saving a device name or DHCP reservation was verified to be a **non-issue** — that leading `<` is the correct, required format for those lists, and every parser depends on it. No change made.
- Built on the **RT-BE96U** first (both variants) for on-device validation; the fan-out to the other four models follows after the name-display and theme checks pass on hardware.

## v2.2.6 — The Internet Speed Test no longer freezes the browser during a run
- **Fixed the speed-test page locking up (“page unresponsive”) partway through a test.** The Internet Speed Test (Adaptive QoS → Internet Speed) reads its live results from the router while the test runs. It was doing that with a **blocking** request repeated every fifth of a second for the whole test. During the download/upload phases the speed-test engine pushes the router’s CPU to the limit, so each of those blocking requests took longer and longer to answer — and because they blocked the browser’s single UI thread, the page eventually froze, showing the browser’s “page unresponsive” prompt. The test itself kept running in the background and finished normally, which is why refreshing the page a moment later showed the completed numbers. The result polling is now **non-blocking** (each poll is chained from the previous one’s reply, with a guard so requests can never pile up), so the page stays responsive and updates smoothly from start to finish. The 120-second overall timeout and the existing one-shot silent retry are unchanged.
- Built + shipped on **all five models** (RT-BE96U + RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro), **both variants each** (with and without the AI Advisor), 2026-08-07 — each model built as itself (own banner, base, and BUILD_NAME verified by the port guards; dictionaries confirmed in lockstep). On-device validation is still to come.

## v2.2.5 — Privacy and polish: masked Wi-Fi keys, fewer ASUS callbacks, full-screen loading, named offline devices, more translations
- **The Wi-Fi password is no longer shown in the clear on the post-apply reconnect card.** When you edit a Wi-Fi network from a browser that is itself on Wi-Fi, the router shows a reconnect hint listing each band's SSID; it used to print the **network key in plaintext** alongside it. The key is now masked (dots); the SSID reconnect hint is kept.
- **Three more ASUS-cloud icon callbacks removed (de-cloud).** Building on v2.2.0, the admin browser no longer fetches device/model or per-app icons from `nw-dlcdnet.asus.com` on the dashboard client detail, the AiMesh node/model icon helper, or the QoS bandwidth monitor. Each now uses the bundled local icon, so simply viewing those pages no longer tells ASUS which devices and apps you have.
- **The loading / progress / rebooting overlay now covers the whole screen.** It previously left the top header and side navigation clickable while an apply or reboot was in progress (you could start another action mid-reboot). The overlay now sits above all interface chrome and blocks interaction until the operation finishes.
- **Offline devices keep their names in the Traffic Analyzer history.** In the 24-hour / week / month views, a device that is currently offline used to fall back to a bare IP or MAC address, because names were only resolved from the live client list. History now also resolves names from your saved device list, so a device you've named still reads by name even while it's off.
- **More of the interface is translated.** The AI Advisor intro line was completed across all 24 non-English languages (it had been truncated), the Warden feed-deduplication note was translated (it had shipped in English everywhere), and the Connections page "Quick Look" view labels (Device, Scope, State, Internal, External, Quick Look, Advanced, Pause) were tokenized and localized across all 25 dictionaries.
- Built + shipped on **all five models** (RT-BE96U + RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro), **both variants each** (with and without the AI Advisor), 2026-08-07 — each model built as itself (own banner, base, and BUILD_NAME verified; noMCP images confirmed free of the Advisor). On-device validation is still to come.
- **Known limitation (GT-BE98, not fixable in Reaper).** On the GT-BE98, creating a Guest Network Pro network with AP isolation *while a manual WAN VLAN is in use* can stop the 2.5 Gbps-1 LAN port from passing normal (untagged) main-LAN traffic — the port effectively requires an 802.1Q VLAN tag afterward. This was investigated on-metal in depth: the guest network is a tagged VLAN trunk applied to the LAN ports and handled by the hardware switch/accelerator, and this firmware exposes **no interface to read or correct that hardware VLAN programming from software**, so it cannot be fixed in the Reaper firmware (it is a closed Broadcom/ASUS component, and almost certainly affects stock ASUS firmware the same way). **Workarounds:** don't extend the Guest Pro network to the 2.5 Gbps-1 port (bind it to other ports/bands), use a different LAN port for that device, or tag the device with the guest VLAN — or avoid combining a manual WAN VLAN with Guest Pro on that port.

## v2.2.4 — The connection-health probe is now light enough to leave running
- The optional per-device connection-health probe added in v2.2.2 (still **off by default**) could, once enabled on a busy 100+ device network, cause brief stutters in the live Traffic Analyzer graph and a momentary dip during an internet speed test. The cause was too much work landing on a single one-tenth-of-a-second collector tick: it parsed the entire connection-tracking table at once, pinged every device in one burst, and appended history to flash inline. v2.2.4 spreads all of it across many ticks — a bounded slice of the connection table per tick, at most 16 pings per tick, and history staged in RAM then written to flash only on the existing hourly save — and it **skips a probe cycle entirely while the internet link is saturated**, so it never competes with a speed test. The default probe interval is relaxed from 30 to 60 seconds. Net result: no single collector tick carries a spike, so the probe is safe to leave enabled.
- Built and compile-verified on the RT-BE96U (MCP variant). The noMCP variant, the fan-out to the other four models, and on-device validation are still to come.

## v2.2.3 — Live Traffic Analyzer graph smoothed on large networks
- Fixed an occasional micro-stutter in the live Traffic Analyzer that appeared after v2.2.2 raised the per-device capacity from 64 to 192 devices. For every network connection on the busy five-second update, the collector was doing a linear walk of the device table to find the owning device; tripling the device cap tripled that cost and pushed the update over its time budget on 100+ device networks. It is now a constant-time lookup. This was independent of the health probe — it occurred with the probe off — so it is fixed for everyone, not just those using the new feature. Built, shipped, and confirmed smooth on the RT-BE96U (MCP variant).

## v2.2.2 — Connection-health metrics and export to an analytics engine (Splunk, Datadog, Prometheus, and more)
- **New: per-device connection-health metrics.** The traffic collector can now measure, per device, the round-trip latency, jitter and packet loss (via a lightweight in-router ping that probes all your devices in one batch, never one process per device), the number of active TCP connections and how many are established, alongside the throughput and online/offline state it already tracked. It is **off by default** and turns on when you enable export or pick the metrics on the new page. The per-device capacity was raised from 64 to 192 to cover large networks.
- **New: send that data to an analytics engine (Administration → Data Export).** A new page configures streaming the health metrics to Splunk (HEC), Datadog, Dynatrace, Elastic/Kibana, a generic HTTP/JSON collector, OpenTelemetry, or a TLS syslog target — all **push** — or exposing a **Prometheus** scrape endpoint (OpenMetrics) that Prometheus pulls. Pick an engine, enter the endpoint and token, choose which metrics to send and how often; there is a **Test connection** button and a **Preview payload** button that shows exactly what will leave the router before you turn it on.
- **Retain, send, or both.** The Long-Term Storage page gains a **Data export** control with three modes: **Off** (history kept locally only, the default), **Store + Export** (keep a local copy *and* stream it out), and **Export only** (stream out without keeping a local copy, to save space). This pairs with the storage-location choice (RAM / JFFS / USB) already on that page.
- **Security posture (this is a de-clouded, hardened build).** Export is off by default and only ever talks to the endpoint you configure. TLS certificate verification is **on by default** (checked against the system CA bundle); turning it off for a self-signed collector shows a warning. The API token is stored so it never appears in the process list or any log line, and is shown masked in the interface. An optional switch hashes device MAC addresses before they leave the router. The Prometheus scrape endpoint requires a bearer token you generate; without it, it serves nothing.
- **Not included by deliberate choice:** wireless signal/PHY metrics (can be added later), and TCP retransmit counts — the latter cannot be measured reliably once traffic is hardware-accelerated, and a wrong number is worse than none.
- **Also in this build: the USB Health Scanner now actually scans ext4 disks and reports a real result.** v2.2.1 kept the scan result on screen, which exposed that on an ext4 stick the scan had never really run — the stock disk monitor skipped every ext4 partition, the `fsck.ext4` tool wasn't linked in, and the page fell back to dumping a raw internal XML blob. The on-demand scan path now runs `e2fsck` on ext4 and the page shows a proper pass/fail verdict plus the real check log (never raw XML), and won't report "done" instantly off a previous run's stale status. (The mount-time auto-check keeps its skip, as before.)
- Built and compile-verified on the RT-BE96U (MCP variant). The second variant, the fan-out to the other four models, and on-device validation are still to come.

## v2.2.1 — Warden's block count survives reboots, "collecting since" fills in for every dataset, the USB health-scan result stays on screen, and a dead Security-Update panel is gone
- **Warden's "total blocked" count now survives a reboot and a firmware flash.** v2.1.6 stopped the count resetting on every routine firewall restart, but it still started over at zero after a reboot or a re-flash — the running baseline was kept in temporary storage that clears on boot. It now lives alongside Warden's block-list cache in persistent storage, so the total carries across reboots and firmware updates. Turning Warden off still resets it to zero (as does a factory reset). Writes are kept minimal — the stored total is only updated when the count has actually grown.
- **The Long-Term Storage "Collecting since" column shows a date for every enabled dataset, not just Devices.** Each dataset now stamps its own start date the first time it writes to durable storage, and the page shows it per row. (Datasets stored in RAM stay blank — RAM history is volatile by design; a row only shows a date once it's collecting to JFFS or USB.)
- **The USB Health Scanner result stays on screen.** After a scan finished, the disk panel refreshed itself and wiped the just-shown scan output almost instantly (it flashed for a fraction of a second). The result is now preserved across that refresh and remains visible until you run another scan or format the disk.
- **The stock "Security Update" panel is removed from the firmware page.** It was ASUS-cloud TrendMicro signature-update machinery that does nothing on the de-clouded build. Reaper's own update check is unchanged and already correct: the "Scheduled check" toggle and the "Check" button both drive the Reaper GitHub release check, never an ASUS/Merlin endpoint.
- Built + shipped on all five models (RT-BE96U + RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro), both variants each, all passing the 19-check verify gate (two new patch markers prove the Warden-persistence and Security-Update-removal fixes are inside every image), 2026-08-06.

## v2.2.0 — First-boot loop fixed for good, Gatekeeper internet-only works with a LAN DNS, USB tools find their home, and a de-cloud console cleanup
- **A quieter, cleaner console — three de-cloud leftovers removed.** The stock ASUS
  privacy-policy check no longer runs at all (it logged "Error fetching ASUS privacy policy"
  on every page — the policy is pre-signed and its endpoints are part of the removed cloud
  surface); the dashboard client list no longer makes *any* requests to the ASUS icon CDN
  (neither the per-device product-icon fetch, which leaked the presence and model of ASUS
  devices on your LAN, nor the icon-catalog refresh — the bundled icons are used, as for
  every other vendor); and three client-popup tooltip fields gained full HTML encoding
  including apostrophes (defense-in-depth from the August audit; the values involved come
  from the vendor database, not from attacker-controlled input).
- **The first-boot setup no longer ends in an endlessly reloading login window.** (Field
  reports on v2.1.6; the flaw was present in every build with the first-boot wizard and was
  still in v2.1.9.) On a factory-fresh or factory-reset box, the web server decided its
  landing page once at startup — while the password was still the default — and never
  reconsidered. After you set your custom credentials, the address `/` therefore kept
  serving the (already-completed) credential wizard, which correctly noticed it was done
  and went back to `/` — an infinite reload loop that made the interface unusable and drove
  users to reflash stock firmware. The landing decision is now made fresh on every request,
  and the wizard's exit goes straight to the dashboard, which is immune to the loop by
  construction. Existing affected boxes can escape the loop today by simply power-cycling
  the router and logging in with the new credentials — no reflash needed. Upgrading to this
  release also recovers a looping box on its own.
- **Gatekeeper "Internet only" now works on networks with a LAN-hosted DNS server.** (Owner
  field report 2026-08-06: a work laptop set to internet-only had no usable internet while
  every other device was fine.) Root cause: internet-only seals the device off from the whole
  LAN — including, on AdGuard/Pi-hole-style networks, the very DNS server the router's DHCP
  told it to use; with no resolver, "internet only" was internet in name only. The firewall
  rules now carve out exactly port-53 (and ARP) from restricted devices to the DHCP-advertised
  DNS server, and only when that server actually lives on the LAN — router-provided or public
  DNS setups already worked and are untouched, so the change is a structural no-op there.
  Everything else on the LAN stays sealed; blocked and quarantined devices are unaffected.
  One prerequisite worth knowing: the DNS server device itself must be an approved (full)
  device in Gatekeeper. Also fixed while in there: the teardown command buffer was 44 bytes
  too small, silently skipping the final chain cleanup and accelerator flush on every
  disable — found by compile-checking the rule generator, now sized with headroom. A build
  gate marker (`gk_same_net`) proves the fix is compiled into every shipped image.
- **The 2.4 GHz Preamble control now follows "Disable 802.11b."** Preamble is an 802.11b-era
  concept, so on the all-bands WiFi Professional page the Disable-802.11b control is now the
  master: setting it to *disable* forces the Preamble selector to its "Disable 802.11b" state
  and locks it (dimmed, not editable) — the same consistent pair the stock page always wrote —
  and switching back to *allow* unlocks it and restores your previous preamble choice (a queued
  preamble change is parked while locked, not lost). A box whose stored settings already held
  the disabled state with a leftover preamble value no longer shows a phantom pending change
  when the page opens. (Owner request 2026-08-05.)
- **USB disk tools get their own tab under USB Application.** The disk panel (drive info and
  usage, health scan, format, safely remove, and the badge marking which partition holds the
  long-term store) moved from the Long-Term Storage page to a new **USB Disks** tab — the first
  tab of the USB Application menu, next to the other USB services where it belongs. It had only
  landed on the storage page in v2.1.7 as the interim home when the Network-Map side menu was
  retired. The Long-Term Storage page (System Log) keeps just the store selection. Same proven
  backends; no translation changes needed. (Owner request 2026-08-05.)
- Built + shipped on all five models (RT-BE96U + RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro),
  both variants each, all passing the 19-check verify gate — including new patch markers
  proving the first-boot and Gatekeeper fixes are inside every image — 2026-08-06.

## v2.1.9 — Device names unified (renames finally stick everywhere), flash-proof Traffic history, a USB disk panel, the siblings' PPPoE-1500 catch-up, a WAN-MTU rollback, and a code-audit hardening pass

> Version note: this rung went through two unpublished pre-release iterations
> before it settled. It was first cut as **v2.1.7**; an owner field report caught
> the WAN-MTU regression below, so it was respun as **v2.1.8** with the rollback.
> A full code audit of the Reaper sources then produced the hardening fixes in
> the last bullet, respun once more as **v2.1.9**. Neither v2.1.7 nor v2.1.8 was
> published — v2.1.9 is the release and carries everything below.

- **The WAN-MTU field no longer accepts 1508 (rollback of a v2.1.3/v2.1.5 over-reach).** The visible WAN MTU box only appears on automatic-IP / static-IP connections, where 1508 is not a valid MTU on a standard Ethernet WAN — yet the earlier PPPoE fixes had raised its limit to 1508, and it would accept and apply that value (field-reported on a DHCP line). The field is back to 1280–1500. Nothing is lost for PPPoE users: the PPPoE MTU/MRU fields still accept 1500, and the firmware raises the physical interface to 1508 **automatically and only for PPPoE** — a code sweep confirmed the PPPoE bring-up is the single place in the firmware that ever adds those 8 bytes, and every other connection type applies exactly the MTU you typed.
- **One master device-name list, everywhere.** Every page that shows a device — the Client List, the Network (Guest Network Pro) client views, the Devices page, Gatekeeper, Traffic's Top Talkers/Top Devices, Connections, the Wireless Log, and now the DHCP-leases log — resolves names from the same master store, with the same priority: your custom name first, the device's self-reported hostname only as a fallback. Renaming a device anywhere propagates to every other view on its next refresh.
- **The "my device names keep reverting" family of bugs is fixed — three root causes.** (1) On every boot the firmware pads the name records to a newer, longer format, but several maintenance paths — most notably *removing an offline client* — only understood the short format and silently **discarded every padded record when rewriting the list**: delete one offline device, lose all your custom names. These paths now understand both formats and pass through untouched records byte-identical. (2) A rename made on the **Devices page appended a duplicate record instead of replacing the old one** — pages that read the list front-to-back (Devices itself, Gatekeeper) kept showing the *old* name while others showed the new one, which is exactly the "rename doesn't propagate, then reverts" field report. It now replaces the record properly, keeps the device's group/icon data, and existing duplicates from the old bug self-heal on the first reboot. (3) The **stock rename popup saved the entire list from a snapshot taken at page load**, silently rolling back any rename made elsewhere (another tab, the Devices page, the app) since the page opened; it now re-reads the live list at save time.
- **Gatekeeper shows your names.** The Gatekeeper device lists used to prefer the hostname the device reports about itself over the name you assigned — the inverse of every other page. Your custom name now wins there too.
- **The DHCP-leases log gains a "Device Name" column.** The System Log → DHCP leases table showed only the raw hostname from the lease (whatever the device calls itself); it now also shows the unified device name beside it, so the leases view finally matches the rest of the UI while keeping the raw lease data visible.
- **Traffic Analyzer history now survives firmware flashes too.** v2.1.5 made history survive reboots; a firmware *flash* could still lose it — the flash process detaches storage mid-flight and the collector could write to a phantom mount point. The collector now verifies the store is genuinely mounted before writing, parks itself when the store vanishes, and re-attaches when it returns.
- **A USB disk panel on the Long-Term Storage tab.** Disk info, a health scan, format, and eject — the functions that previously lived only in the stock network-map side menu — are now on the Reaper storage page where the USB store is actually selected.
- **Sibling models: PPPoE MTU 1500 now accepted in the GUI.** The v2.1.5 GUI fix had only reached the RT-BE96U image: the WAN page variant these models actually ship lives under a build path the sibling port deliberately skipped, so BE86U/BE88U/GT-BE98/GT-BE98 Pro images through v2.1.6 still enforced the old 1492 cap (the backend accepted 1500 all along). The page is synced on all four siblings and the port process now syncs every shared page regardless of where it lives, so this class of gap can't recur. All five models also carry identical, fully in-step translation dictionaries as of this release.
- **The build gate now proves patches are inside every image.** Two new automatic checks run on every model and variant before an image can ship: a shared-code parity check against the primary branch (model-specific overlays respected — nothing is blind-copied between models), and a patch-marker check that greps the staged filesystem for each field-critical fix (and for forbidden leftovers like the old 1492 cap or the 1508 allowance). The gap class that shipped v2.1.5/v2.1.6 sibling images without the MTU fix is now structurally impossible to ship silently. (These checks promptly proved themselves: they caught that the GT-BE98 legitimately uses a different WAN page variant than the other four models — documented, not a defect — and they enforce the WAN-MTU rollback above.)
- **A full code audit of the Reaper sources, with the findings fixed.** Four parallel reviews (security, correctness, performance, code quality) plus a deterministic cross-model parity check. **No critical or high-severity defect was found**, and parity was perfect — every shared fix is present on every model, every model-specific difference is legitimate. The confirmed items were fixed and fanned out to all five models: three self-themed pages no longer get the stock page's CSS injected into them; the QoS-diagnostics page now carries the same anti-forgery token as the rest of the UI before running its diagnostic subprocess; the QoS page stops its background polling while its tab is hidden; DHCP reservations and pool edits now store the exact address that was validated (not a lenient variant); an uninitialised read in the boot-time client-list normaliser is fixed; deleting a client can no longer drop an over-long neighbouring record; plus small consistency/cleanup items. Two cosmetic/latent items and three cross-page refactors were deliberately deferred. Full detail in `CODE-AUDIT-2026-08-05.md`, which is **not published in this repo** — it lives in the private working tree.
- Built + shipped on all five models (RT-BE96U + RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro), both variants each, all passing the 19-check verify gate, 2026-08-05.

## v2.1.6 — Firmware-update notifications, the dashboard shows your real IPv6, and Warden/watchdog field fixes
- **The router can now tell you when a Reaper update exists (opt-in, notify-only).** Every Reaper release shares the same Merlin base number (3006.102.8), so the stock update check — which compares only that number — could never see a Reaper update. The check now reads a Reaper-published manifest on GitHub instead: it knows your model *and* your variant (Standard vs AI Advisor, so it never offers the wrong image), compares real Reaper versions, and on a match shows a crimson "New firmware available" badge on the dashboard plus the release note on the firmware page. It is **off by default** (`firmware_check_enable` stays 0, in keeping with the de-cloud posture — the only endpoint it ever talks to is the Reaper GitHub tree, and only when you enable it or press Check). It never downloads or flashes anything by itself.
- **The dashboard shows your real WAN IPv6 address instead of a `fe80::` link-local.** On the most common IPv6 setups (native / DHCPv6 with prefix delegation) the ISP delegates a prefix and the router's global address lands on the LAN bridge — the WAN interface itself carries only a link-local `fe80::` address. The dashboard's Internet card fell back to displaying the gateway/link-local in that case; it now falls back to the LAN-bridge global — the same source the stock IPv6 status page uses — and never presents a `fe80::` address as the WAN address (the gateway keeps its own line, where `fe80::` is normal and correct).
- **Warden's "total blocked" counter no longer resets behind your back.** The counter was read from a live firewall rule that gets rebuilt on every routine firewall restart (any WAN event, VPN change, etc.), so the UI total kept snapping back to zero. The count about to be flushed is now banked into a running baseline first; the total accumulates across firewall restarts and resets only when you deliberately reconfigure/disable Warden or reboot. The feed checkboxes also gained a note explaining that overlapping feeds are merged and de-duplicated into one block set — enabling several feeds never double-blocks or bloats matching.
- **"B/G Protection" is removed from the all-bands Professional page.** The control never worked: the Broadcom driver bring-up force-resets it to Auto on every wireless restart whenever the 2.4 GHz mode is Auto (the default, and effectively the only sane choice on Wi-Fi 7) — a stock firmware behavior, not something Reaper broke. Rather than ship a knob that silently ignores you, the row is gone.
- **No more phantom "wan-gw FAILURE" from the health watchdog.** If your ISP's first hop filters ping (many ONTs and PPPoE gateways do), the `rwatch` watchdog flagged a WAN-gateway failure on every probe while the connection was actually fine. A failed ping is now corroborated against the router's own WAN state: if the WAN is up, it logs a one-time informational note instead; a real outage still alarms.
- **Two menu labels render correctly again (Russian, Turkish).** The Russian "Administration" menu entry showed a literal `&shy;` on stock pages (the stock menu renderer emits labels as plain text, so HTML entities appear raw); it and a Turkish label with the same latent issue now use plain characters.
- Built + shipped on all five models (RT-BE96U + RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro), both variants each, 2026-08-05.

## v2.1.5 — Field-report fixes: PPPoE 1500 works from the GUI, first-boot page self-recovers, Traffic Analyzer history survives reboots
- **The 1500-byte PPPoE MTU (RFC 4638) can now actually be set from the GUI.** The v2.1.3 change raised the limits on a WAN page variant that does not ship on these models — the page the firmware actually installs still enforced the old 1492 cap and even silently knocked a hand-entered 1500 back down to 1492 on apply. The shipped page now accepts PPPoE MTU/MRU up to 1500 (WAN MTU up to 1508) and only steps in when you have deliberately lowered the WAN MTU below 1500. This explains the field pattern exactly: boxes flashed over from stock/Merlin kept their saved 1500 (applied at the service level, where it always worked), while factory-reset boxes had to re-enter it through the GUI and were blocked.
- **The first-boot credential page can no longer reject everything you type.** Field reports described a factory-reset box whose initial setup "would not accept anything" for the new username and password. Root cause: if that page is ever shown when the admin password is *already* set — a stale or back-navigated copy of the page, or an earlier submit whose success confirmation never reached the browser — every further attempt was doomed to the same generic error, with no way out short of restoring stock firmware. The page is now self-recovering: it leaves on load if the credential step is already done, and if a submit is rejected it re-checks the router's live state — when the password did in fact apply, it simply continues to the Wi-Fi step instead of looping the error.
- **Traffic Analyzer history now genuinely survives reboots on both storage options.** With storage on **USB**, history was lost on *every* reboot: the collector looked for its database once at startup — before the USB stick had mounted — silently fell back to RAM, and an hour later overwrote the previously saved history with an empty file. It now waits for the store to appear (retrying for up to 15 minutes), restores the saved history when it does, and will never overwrite a database it did not first load (an at-risk file is preserved as `rtraf.db.prev`). With storage on **JFFS**, the boot-time restore always worked, but saves were hourly — an unclean reboot (power pull, watchdog) could drop up to an hour of recent history, which read as "not persistent." USB now saves every 15 minutes (no flash-wear concern there); JFFS stays hourly to protect the router's NAND.

Built + shipped on all five models, both variants each, all passing the 17-check verify gate — the first release produced by the new parallel per-model build fleet.

## v2.1.4 — Factory-reset lockout fixed, WireGuard peer-row polish, OpenVPN version label corrected
- **Factory reset no longer strands you at the credential step.** On a factory-fresh box, logging in with the default admin/admin could land you on the stock ASUS "Change the router login password" page, which then collided with Reaper's own first-boot credential page — the second attempt failed with "Could not apply credentials" and left you unable to continue (recoverable only by restoring the stock firmware). Reaper now routes a default-password box straight to its single themed first-boot page, so the credential change happens once and applies cleanly. Reported on the GT-BE98; the fix is shared code and applies to every model.
- **WireGuard peer list — the edit control is reachable and centered.** On the VPN client peer list, the three-dots edit toggle was cramped against the delete/export buttons and could clip off the right edge of the view; it is now centered in its circle with room to spare, and the action buttons no longer run off-screen. (This also brings the siblings up to the earlier WireGuard peer-list icon fixes, which had not reached them.)
- **OpenVPN now reports its real version (2.7.5).** The 2.7.5 update shipped in v2.1.2, but the version string the router displayed stayed "2.7.4": a stale generated build file left the label frozen at the old value even though the running binary was already 2.7.5. The label is now regenerated correctly and reads 2.7.5 — a display correction only, the code behavior was unchanged.
- Built + shipped on all five models (RT-BE96U + RT-BE86U / RT-BE88U / GT-BE98 / GT-BE98 Pro), both variants each, 2026-08-04.

## v2.1.3 — Connections "Quick Look", baby-jumbo PPPoE, a stored-XSS fix, and UI polish
- **A stored cross-site-scripting hole in the stock client list is closed.** A device whose name or DHCP-hostname contained an apostrophe rendered broken on the stock Network Map client list — and the same flaw was a reachable stored XSS: the stock renderer placed the name in a single-quoted HTML attribute and encoded `& < > "` but not `'`, so a crafted name could break out of the attribute on a page the authenticated admin views. The name is now additionally apostrophe-encoded at the single point it is prepared, fixing both the display garble and the injection at once. Reaper's own Devices page was already safe.
- **Connections page — a "Quick Look" default view.** The Connections page now opens on a simple at-a-glance list — device name, local IP, remote IP:port, an internal-vs-external badge, protocol and TCP state — resolving device names from the client list rather than showing bare IP addresses. The existing live flow explorer is retained as "Advanced" (now with a Pause option, and the device name + connection state in its detail panel); a single slider switches modes and your choice is remembered.
- **Baby-jumbo PPPoE MTU (RFC 4638).** The WAN GUI now allows a 1500-byte PPPoE MTU/MRU (with the parent interface raised to 1508) for full-fibre lines that support it, instead of the usual 1492. It is opt-in — the nvram defaults are unchanged, so existing PPPoE users are unaffected.
- **Three UI touch-ups.** The all-bands Wireless Professional page no longer prints the raw nvram variable name beneath each setting; the AI Advisor's intro sentence is no longer truncated ("…read this router's **status and configuration.**"); and the dashboard radio tiles show the SSID in its real mixed case instead of all-caps.
- Built + shipped, both variants, 2026-08-03.

## v2.1.2 — Asuswrt-Merlin 3006.102.8 carry-forward
- **The fixes from the final Merlin 3006.102.8 release are folded in.** Reaper's base is pinned to the 3006.102.8 beta; this release carries forward the fixes Merlin landed between that beta and the final 3006.102.8 / 3006.102.8_2 production releases. There are no Reaper feature changes in this rung — it is purely an upstream carry-forward.
- **OpenVPN updated to 2.7.5.** This is the 2.7 line, which removes some long-deprecated server options. If you run an OpenVPN *server* with an older configuration, confirm it still connects after updating.
- **Security and package updates.** Dropbear (SSH) updated to 2026.94, a strongswan build fix (a missing executable), and a miniupnpd update; the default UPnP SSDP advertisement interval is now 900 s.
- **IPv6 address handling corrected.** The router now reports the correct IPv6 prefix length for the LAN address and clamps a delegated prefix to /64 where appropriate (mostly affects non-SDN / non-multilan setups; largely inert on this model). A custom DDNS update now also sets the IPv6 record on success.
- **Web-UI fixes carried over.** The client list now redraws incrementally instead of rebuilding the whole table, DHCP-reservation export works on iOS devices, the Traffic Analyzer no longer depends on the (removed) DPI engine to be available, and an obsolete USB-modem tweak was dropped.
- Carried as upstream commits with their original authorship preserved. Not carried: changes that don't apply to this model (a UI4-only popup, an OpenSSL bump for a different SoC, a sibling build-profile fix, and minor stock-page chart cosmetics).
- Built, both variants, 2026-08-03.

## v2.1.1 — Localized error messages, defense-in-depth hardening, and three UI fixes
- **The last hardcoded English is gone.** About three dozen error messages on the Devices and AI Advisor pages (e.g. "invalid MAC address", "the reservation store is full", "incorrect code") were shown in English regardless of your language; they now resolve through the translation dictionary in all 25 languages, with the English text kept as a safe fallback.
- **Two AI Advisor internals made structurally safe.** The Advisor daemon's secret-redaction — which strips passwords and keys from anything it returns — is now applied at the single point where every tool's output leaves the daemon, instead of tool-by-tool, so any future tool is covered automatically. And when a tool's output is too large to fit and gets truncated, the daemon now always returns valid JSON with a truncation marker rather than a cut-off response.
- **Extra escaping on three pages.** The Connections, QoS Diagnostics and QoS pages now pass system-supplied strings (port names, flow addresses, class names) through the same escape helper the other pages use — defense-in-depth; there was no reachable issue.
- **The Warden threat/geo block-lists load much faster.** Large feeds were added one address at a time — one process per entry — on every refresh; they now load in a single batched operation, with the old per-entry path kept as an automatic fallback if a malformed entry appears.
- **Three pages fit the window properly.** The Connections, QoS Diagnostics and all-bands Professional pages sat shifted to the right and could run off the edge of the frame; they now fill and left-align like every other Reaper page. The Connections page also gained a clearer **"QoS Class"** column header (was just "Q") and larger page and flow-detail titles.
- **Channel Lock now warns first.** On the Wireless Quality page, locking a channel restarts that radio (about a 20-second client drop on the band) exactly as unlocking does; Lock now shows the same Continue / Cancel confirmation that Unlock already had.
- Built + shipped, both variants, 2026-08-02.

## v2.1.0 — Pre-release code review, a hardening pass, and three more fully-translated pages
- **A full pre-release code review of every Reaper-authored component — no critical or high-severity issue found.** Six independent reviewers swept the web-server handlers, the background daemons, and the pages across six dimensions (security, memory/handle leaks, dead code, bloat, correctness, and privacy). The code came back clean of any reachable exploit or leak; the review's confirmed items are fixed in this release and the remainder is recorded in the backlog.
- **Hardening fixes applied.** Several admin-page JSON fields (a QoS-diagnostics value, the Advisor's saved client address, a couple of device band labels) are now escaped consistently, so an unusual stored value can never malform a status response. The live Connections feed's read of the flow accelerator is now single-flighted, so two open tabs can't pile concurrent reads onto that kernel surface. The Wireless status endpoint now carries the same anti-forgery token as the rest of the interface (it launches a short-lived helper per radio, which a background page should not be able to trigger). The Gatekeeper enable-time device snapshot now takes the same lock its sibling writer uses, and some dead code was removed. One developer device address left in a source comment was scrubbed.
- **The accelerator health probe is now opt-in.** The watchdog's check of the hardware forwarding pool — which reads a kernel accelerator file every few minutes — is now off by default and enabled with a single setting. The everyday probes (gateway reachability, loopback DNS, and the Warden self-lockout canary) stay on by default.
- **Three more pages fully localized.** The Connections, QoS Diagnostics, and all-bands Professional pages still carried hardcoded English; 132 strings across them are now translated into all 25 languages, and fourteen previously English-seeded interface labels were given real translations. No behavior change — localization only.
- Validation build (both variants) 2026-08-02.

## v2.0.8 — QoS Diagnostics dropdown fix + wording and localization touch-ups
- **The QoS Diagnostics port selector stays open now.** The port dropdown was being rebuilt on every refresh tick, which snapped it shut before you could pick a port; it is now rebuilt only when the port list actually changes (and never while you have it open), with the current selection kept in place.
- **"Wireless Diagnostics" is now "Wireless Quality," and a Devices label is corrected.** The Wireless tab was renamed to Wireless Quality across all 25 languages, and a Devices-page label that read "Network legible" is corrected to "Network Ledger" (each language had faithfully translated the typo's apparent meaning).
- Built + shipped, both variants, 2026-08-02.

## v2.0.7 — QoS Diagnostics reliability
- **The QoS Diagnostics page now reads the hardware traffic manager reliably.** It previously reached the accelerator through a shell alias that existed only by way of an untracked helper a rebuild could silently drop, so on some builds the page came up empty; it now calls the accelerator shell directly using the session id the router writes at boot. The page's live rate and drop figures are also now aware of the hardware's 32-bit byte counters wrapping (observed about every 15 seconds at ~2 Gbps), which had caused periodic zero-rate ticks; a counter reset is discarded rather than shown as a spike.
- Built + shipped, both variants, 2026-08-02.

## v2.0.6 — Connections: a live flow explorer with hardware-acceleration insight
- **The Connections page is now a live flow explorer.** It replaces the old list (source / destination / port / state only) with a per-flow view drawn from the router's Runner flow accelerator. For every active connection it shows source and destination, protocol, whether the flow is forwarded in hardware (the Runner) or by the CPU — with a real per-flow hardware-vs-CPU percentage split — plus the egress queue, DSCP, live throughput, total bytes, and true connection age. Summary cards show how many flows are hardware-accelerated and the overall hardware-vs-CPU forwarding split; filters narrow to accelerated or CPU-path flows, and a detail panel expands any flow.
- Live polling (500 ms – 4 s) runs only while the page is open. Connection age is tracked continuously by the resident traffic collector, so it stays accurate even for flows that started before you opened the page.
- The stock connection page is retained unchanged as a fallback.
- Built + shipped, both variants, 2026-08-01.

## v2.0.5 — Hardware QoS Diagnostics
- **New "QoS Diagnostics" page** under Traffic Manager (right of the QoS tab) — a live view of the router's hardware traffic manager (the Runner/XRDP egress scheduler). Per queue it shows live occupancy, drop rate, an estimated delay, the scheduling discipline (strict-priority / weighted round-robin) and weight, the AQM algorithm and the shaper rate, plus per-queue occupancy and drops graphs and a selected-queue detail card. It reads the accelerator directly (the on-box bdmf shell) — including occupancy, which the vendor CLI can't report — and adapts to your QoS mode: a single shaped queue under Hardware PI2, or the full weighted scheduler under HW Classful. A port selector exposes the per-port (WAN upload / LAN download) schedulers.
- Fast polling (250–500 ms) runs only while the page is open; the background collector stays at its normal cadence. Estimated delay is derived (backlog ÷ shaper rate); drops are the combined tail+AQM counter.
- Built + shipped, both variants, 2026-08-01.

## v2.0.4 — Safer out of the box: Wi-Fi Protected Setup off by default
- **WPS is now off by default.** On a fresh install or factory reset, Wi-Fi Protected Setup (the push-button / PIN pairing feature) no longer starts enabled. WPS — especially its PIN method — is a long-standing proximity attack surface, and Reaper's goal is that only physical access should be able to compromise the router; you add devices with the Wi-Fi password or a QR code instead. It remains a one-click toggle in the GUI for anyone who wants it.
- **UPnP master switch off by default.** The global UPnP flag now matches the per-WAN setting (which was already off), so automatic port-opening stays fully closed out of the box — belt-and-suspenders, with no change for anyone who wasn't already using UPnP.
- A full factory-default audit confirmed everything else unneeded is already off or not built: remote web admin, SSH, Telnet, WAN ping, FTP, media server (DLNA), DDNS, guest network, SNMP, custom-script execution, remote logging and IPv6 all default off, and TrendMicro DPI / AiProtection, LLTD, AiCloud/WebDAV, IFTTT and Alexa are compiled out entirely. USB-drive auto-sharing and the roaming assistant were deliberately kept at their defaults.
- Built + shipped, both variants, 2026-08-01.

## v2.0.3 — One Wi-Fi "Professional" page that fits every router
- **The all-bands Professional page now builds itself from your router's actual radios.** It previously assumed exactly three bands (2.4 / 5 / 6 GHz), so on a four-radio router like the GT-BE98 the fourth radio simply didn't appear. The page now reads the real radio list from the router and generates one column per radio, labeled by its frequency band — and a router with two same-band radios is labeled clearly (e.g. "5 GHz-1" / "5 GHz-2"). Per-band settings and their options follow each radio's band, so every control lands on the right radios automatically.
- **Tidier, easier-to-read layout.** The setting fields were far larger than the values they held; they're now compact with values centered, the table centered in the window, and the dropdown lists centered too — easier to track across bands and leaving room for four-radio models.
- Built + shipped, both variants, 2026-08-01.

## v2.0.2 — File sharing signs in properly, cleaner share names, faster updates
- **SMB file sharing now signs you in from a clean boot.** After the file server itself was fixed in v2.0.1, account-mode shares still refused *every* login: the password database came up empty on each boot, so Windows quietly fell back to a guest session and returned a cryptic "Encryption is not supported for guest access" error. The cause was that the boot-time step which registers each share account was calling the Samba password tool by a path that doesn't exist on this build (the tool moved location between Samba versions), so no account was ever written. It now calls the correct path, and your username and password work on the first try after any reboot.
- **A login prompt instead of a cryptic error.** When a computer connects without stored credentials, an account-mode share now asks for a username and password like any normal network drive, instead of silently dropping to a guest session and failing.
- **Cleaner share names.** A share is now named for its folder (e.g. `reaper`) instead of the old `folder (at DISK)` form — the spaces and parentheses in that name broke command-line access. The disambiguating "(at DISK)" suffix is kept automatically only when two disks hold a folder of the same name. (A per-router toggle still lets you choose the old form.)
- **~11 seconds off every firmware update.** A shutdown step that briefly power-cycles the LAN ports (to nudge clients into renewing their address) was already skipped on a normal reboot, but not on a firmware update — so every flash sat idle for ~11 seconds. It's now skipped on updates too.
- **Channel-quality alert threshold is tunable.** The passive channel monitor's "degraded" trigger — previously fixed at 20% undecodable airtime — can now be adjusted live via the `rchq_degraded` setting, with no rebuild and no restart needed.
- Built 2026-08-01, both variants.

## v2.0.1 — De-clouded, the file server starts again, quieter logs
- **The ASUS cloud connector is removed.** The ASUS AWS-IoT client — which carried off-network ("remote") ASUS-app access, ASUS-account binding, and ASUS-cloud push — was still compiled in and respawned at boot even after the earlier phone-home cleanup (a build config-generator quietly re-added it). It and the paired account-binding surface are now excluded from the build entirely. AiMesh and local-network app access are unaffected; only ASUS-cloud remote features are lost.
- **File sharing starts again (Samba 4).** v2.0.0's move to Samba 4 shipped a file server that never actually started — the daemon exited on every boot because its private libraries weren't on the loader search path and two runtime directories were missing, so Windows reported "can't find the path." The packaging is fixed and `smbd`/`nmbd` now start on boot. The Samba protocol dropdown was also relabeled to match Samba 4 (SMB2 only / SMB2 + SMB3 / SMB3 encrypted), and the obsolete SMB1 option removed.
- **A benign kernel debug flood is silenced.** A stock Broadcom flow-accelerator debug line (`blog_get_dstentry_by_id: match fails`) could flood the system log in bursts on this build, because its logger can't filter by severity. The harmless message is now gated off at the source. *(Flip the source define to re-enable it for debugging.)*
- Built + shipped, both variants, 2026-08-01.

## v2.0.0 — Security-hardening milestone: two full code audits, fixes applied
- **What 2.0.0 is.** This release marks a comprehensive security review of the whole firmware. Two end-to-end audits were run — one over all Reaper-authored code, and a second over the inherited ASUS/Merlin open-source code that Reaper ships — and the issues they surfaced were fixed. No critical or high-severity flaw was left open. The firmware base is unchanged (still Asuswrt-Merlin 3006.102.8); this release is about correctness and safety, not new features.
- **The web interface no longer trusts device-supplied names.** A device on your network can set its own hostname, and several admin pages displayed those names (and Wi-Fi/VPN/USB/mesh names) without neutralizing them first — so a malicious name could, in principle, run script in your browser when you opened the client list or a related page. Every one of those display points now encodes the text so it is shown, never executed — covering the dashboard and network-map client lists, the client picker used across many pages, the OpenVPN/WireGuard status pages, the AiMesh topology view, and the USB storage pages.
- **A malicious USB stick can no longer run commands as root.** The auto-mount path built a system command from a disk's volume label but allowed characters a label should never contain; a specially crafted label could have executed arbitrary commands when the stick was inserted. Labels are now restricted to safe characters.
- **Hardened the internal config database and the VPN pages against injection and overflow.** Values stored in the on-device statistics database are now escaped correctly; the VPN-profile page's fixed-size buffers are bounded to their real size; and the OpenVPN config-upload endpoint accepts only its own settings instead of any value.
- **Stronger request protection and safer defaults.** The Diagnostics and Warden "live status" tools now require the same anti-forgery token the rest of the interface uses, so another web page can't trigger them in the background. Outbound TLS made through the internal helper now verifies the server certificate against the shipped trust store and refuses rather than connect blindly. Threat-blocking now flushes the hardware flow cache so a newly blocked address is dropped immediately instead of after existing connections age out. JSON responses are served and encoded correctly.
- **Known limitations, stated plainly.** The bundled Samba is on an end-of-life branch (no reachable exploit found; a maintained-branch plan is tracked). The AiMesh config-sync and network-discovery services ship as closed vendor binaries and could not be source-audited. A full finding-by-finding status list is in the audit reports.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-31.

## v1.9.9b–c — Set every Wi-Fi band on one page, apply once
- **The Professional wireless page now shows all three radios at once.** Where the stock page let you configure one band at a time — each change forcing its own Wi-Fi restart — the Professional tab is now a single page laying 2.4, 5, and 6 GHz side by side. Set anything across all three bands and press **Apply all** once: only the settings you actually changed are written, and every radio restarts together a single time instead of once per band. Settings that don't apply to a given band are shown but disabled, so the full shape of each radio stays visible. *(The classic per-band page is retained unchanged — Region and the wireless scheduler still live there. New on-page text is English for now, with translations to follow.)*
- **SSID visibility and client isolation were kept off this page.** On this hardware the main network is served through a software-defined-network profile, so the radio-level "Hide SSID" and "AP isolation" switches only ever affected an internal interface — never the network you actually join, so toggling Hide SSID here didn't hide the SSID. Those controls stay on the General Wireless and Network pages, where they act on the real SSID.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-31.

## v1.9.9a — Wireless Diagnostics: clearer Unlock, and scanning the band you're on
- **Unlocking a channel now warns first.** Locking or unlocking a channel restarts that radio, dropping every client on it for about 20 seconds — which can look like the router has frozen. The **Unlock** button now asks for confirmation and explains the brief drop before proceeding. (Per-frequency restart isn't possible on this platform, so the radio restart is unavoidable.)
- **Auto Scan no longer stops after a single channel when you scan your own band.** Every channel the scan tests briefly restarts the radio; if your browser was on the band being scanned, that restart dropped your connection and the scan gave up after the first channel. The scan now tolerates those short reconnection gaps and works through the whole band. It is still cleanest to run a scan from a wired client or a different band.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-31.

## v1.9.9 — Wireless Diagnostics: Auto Scan & Capture made reliable
- **A stalled job no longer blocks the tools for minutes.** If a previous scan or capture ended abnormally — for example, interrupted by a Wi-Fi restart — a leftover marker could make every new Auto Scan and Targeted Capture report "busy" and leave their Start buttons disabled for up to ten minutes. The page now checks whether the earlier job is genuinely still running and clears a stale marker automatically, and a capture that can't start now shows the reason instead of silently doing nothing.
- **"Apply Best Channel" names the band you scanned.** The confirmation now shows the actual band and channel being pinned instead of always reading "6 GHz." The channel was already applied to the correct radio; the wording just made it look as though only 6 GHz was ever targeted.
- **Quad-band clarity.** On models with two 5 GHz radios, the band selectors now tell them apart instead of listing two identical "5 GHz" entries.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-31.

## v1.9.8 — Add-on menu fix, Warden persistence disclosure, change auditing, full localization pass
- **Third-party add-on menu links open correctly.** When an add-on such as scMerlin adds a "Help & Support" entry that points to an external site, the settings shell now opens it in a new browser tab instead of silently redirecting the frame to the Network Map. The same-origin iframe protection is unchanged — only genuine off-site menu links are affected.
- **Warden tells you when protection won't survive a reboot.** If Reaper Warden is enabled but `/jffs` is disabled or read-only, its threat/geo feed cache can't be saved: enforcement still runs from RAM, but there's no cross-reboot or no-internet-boot protection. The Warden page now shows a clear banner when this is the case, so the gap is visible instead of silent. (Disclosure only — by design the cache stays on internal flash, which must restore before the firewall arms.)
- **Change auditing.** Turning a Reaper feature on or off, or changing its settings, now writes a structured entry to the System Log — covering Gatekeeper (device-access changes, enable/disable, config), the Wireless channel monitor, and the Devices/Storage actions. These flow to remote syslog and the optional syslog storage dataset, giving an at-a-glance record of what changed and when.
- **Full 24-language localization pass.** The Devices, Long-Term Storage, and Warden pages — plus a handful of dashboard and QoS strings — were English-only in every language. All 219 remaining strings are now translated into the 24 supported languages; English remains selectable. (Machine-assisted; native review is still pending before public release.)
- Built + shipped on the RT-BEXXU, both variants, 2026-07-30.

## v1.9.7 — Traffic Analyzer accuracy (per-network + the router's own traffic) + dashboard client-list
- **The By-Network panel now reconciles with the live WAN chart.** With the flow accelerator on, the Traffic Analyzer only credited bytes to a network or a device when it could pair the upload and download halves of a connection — so **traffic the router itself generates** (the built-in speed test, DNS, firmware checks, the latency probe) was counted on the WAN line but dropped from every per-device and per-network view, and the By-Network total (br0) never matched the WAN chart. The collector now attributes each flow straight from its own LAN-side interface, and locally-terminated router traffic appears under a new **"Router"** row — so By-Network + Router + clients add up to the WAN line, and a client's download always lands on its network even when the return path isn't paired. Per-device client accounting is unchanged. *(This is the IPv4 path; the separate per-client IPv6 limitation is unchanged and only affects IPv6-enabled lines.)*
- **Dashboard "Clients" card.** The **View List** button now takes you to the full **Devices** page instead of a small in-place popup, and the client list grows to fill the lower part of its card instead of leaving an empty gap.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-30.

## v1.9.6 — Dashboard readability, Warden country picker, status at a glance
- **Security Posture now covers Gatekeeper and Warden.** The dashboard's Security Posture card gained rows for **Gatekeeper** (device access control) and **Reaper Warden** (threat/geo firewall), each showing enabled/off at a glance alongside the existing posture checks.
- **Warden country blocking is now a searchable checklist.** Choosing which countries to block moved from a fiddly multi-select list box to a **searchable checkbox grid** — type to filter, tick the countries you want, save. Any country codes the firmware doesn't recognize are still preserved on save.
- **USB storage shows up right after a boot.** The dashboard's USB tiles render once when the page loads, but USB drives don't mount until ~40–50 s into boot — so a freshly rebooted router showed no USB until you reloaded. The dashboard now re-polls USB status for the first ~90 s after load, so the drives and the storage ring fill in on their own.
- **Client list is easier to read.** The per-client detail text on the dashboard was small and grey; it's now larger and brighter with more card contrast.
- **System Info "Features" row reflects the real build.** The feature list now advertises Reaper's own packages — Gatekeeper, Warden, the Devices manager, unified storage, and the health watchdog — alongside the ones already listed.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.5 — First-boot: default credentials can no longer slip through
- **A factory-fresh router always forces you to set an admin username and password.** After the Reaper dashboard became the post-login landing page, a factory box could reach the interface on the default `admin`/`admin` without being sent through the forced credential-change step — the dashboard carried neither of the two enforcement paths the stock and Reaper first-boot flows rely on. Both the server-side post-login redirect and an early dashboard guard now send a default-credentials box to the first-boot setup page before anything else renders. The check only fires while the credentials are still default, so a configured or upgraded router never sees it.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.4 — Devices page: Wi-Fi clients no longer mislabeled "Wired"
- **Wired vs wireless is now decided by the bridge, not a guess.** The Devices page had been calling a client "Wired" whenever it wasn't in the Wi-Fi association list — but that list intermittently omits Wi-Fi 7 / 6 GHz / MLO stations, so real Wi-Fi clients were shown as Wired. The page now reads the LAN bridge's forwarding table to see which port (and which radio's band) a device was actually learned on, so wired and wireless — and the band — are classified correctly. It never downgrades a confirmed Wi-Fi client on a stale entry.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.3 — Devices page: Wi-Fi 7 multi-link devices shown as one
- **An MLO client is now a single device, not several.** With Wi-Fi 7 Multi-Link Operation, the driver reports each of a device's per-band links as its own address-randomized, lease-less entry, so a single laptop or phone could appear as several "Private address / No lease" rows. The Devices page now uses the driver's link-to-device mapping to fold those links into one device row showing its combined bands (e.g. "MLO · 5+6 GHz"). No effect when MLO is off.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.2 — Devices page: MLO awareness + an offline-device display fix
- **Multi-Link (Wi-Fi 7) links are labeled, not flagged as problems.** Before the full row-merge (v1.9.3), MLO clients' extra per-link addresses surfaced as alarming "Private address / No lease" rows. The page now detects when MLO is active and labels those links "MLO · <band>" with an explanatory tooltip, and stops counting them as unnamed / randomized / needs-attention.
- **Offline devices show a clean connection cell.** A never-seen or offline device printed a literal dash artifact in the Connection column (an escaping slip); it now renders correctly.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.1 — Device Identity Manager (Rung B): choose where long-term history lives
- **A Storage tab to pick where opt-in history is kept.** A new **Storage** page (under System Log) lets you select a durable location — **RAM**, **JFFS**, or a **USB** dot-directory — for the opt-in history datasets (devices, traffic, health-watch, channel-quality, syslog mirror), with per-dataset toggles and a health line. No new data store and no new background service are introduced; it simply directs the existing writers. The Traffic Analyzer's own storage selector becomes a read-only pointer to this one page, so there is a single place that controls where data is written.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.9.0 — Device Identity Manager (Rung A): one place for every device
- **A new "Devices" page that unifies what ASUS scatters.** ASUS keeps a device's identity across several separate places — its custom name, its DHCP reservation, its Gatekeeper access state, and its live presence (DHCP leases + address table + Wi-Fi association). The new **Devices** page (its own left-nav section, between USB Application and System Info) correlates all of them **per MAC** into one rounded view: inline rename, a pool-aware reservation ("Pin") dialog that warns when your DHCP pool is tight, a Gatekeeper state per row, an attention card for orphaned / duplicate reservations and pool exhaustion, filter chips and search, and a 24-hour traffic figure per device with a deep link to the Traffic page. Every change is a careful read-modify-write that preserves the other fields of each record — no sixth store is created — and presence is always computed from leases + address table + Wi-Fi, so it works even with Gatekeeper off. *(New page text is English-seeded across all 25 languages; translations to follow.)*
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.8.9 — WireGuard peer list: usable buttons, unclipped dialog
- **The peer-row buttons are visible again.** On **VPN Server › WireGuard**, the per-peer edit / QR / trash controls rendered as solid red rectangles — a Reaper button-recolor rule had overwritten the sprite-based icons. They are back to white glyphs on a crimson tile.
- **The peer-edit dialog no longer runs off-screen.** Expanding "More Settings for Site to Site Usage" grew the popup past its frame with no way to scroll to the rest; the dialog now refits when a section expands or collapses. *(That section's title, previously hard-coded English, is now translated.)* *(Metal-validated on hardware; the VPN pages can't be exercised in the mock.)*
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.8.8 — Warden: LAN-lockout fixes, persistence that actually works, and a new health watchdog
- **A Warden feed update can no longer lock your LAN off the internet.** A field incident traced to the scheduled threat-feed refresh: one feed (FireHOL level-1) includes private/bogon ranges (192.168/16, 127/8, …), which Warden ingested and then dropped, cutting all new LAN traffic until a power cycle. The updater now filters reserved/private ranges (IPv4 and IPv6) from every list it ingests, and the firewall chain order is rebuilt so the structural anti-lockout rules (loopback, DHCP, established connections, your allow-list, the LAN return path) always come **before** any feed or geo drop.
- **Warden's blocklist now survives a reboot.** The cache-save step had been calling `ipset save` in a way that silently wrote an empty file, so restoring on boot never actually worked; saves are now per-set and only non-empty caches are kept — so protection persists across reboots as intended. Entry validation was also tightened (bad country codes / CIDRs are rejected and logged instead of silently mangled).
- **New: `rwatch` health watchdog (on by default).** A lightweight probe runs every 5 minutes — a first-hop WAN ping (no external hosts), a loopback DNS check, a Warden "canary" that verifies your own LAN IP never matches a block set (re-applying the rules and logging a CRITICAL event if it ever does), and a check for the silent accelerator-wedge signature the stock firmware has no watchdog for. State transitions are written to the system log, and the first failure dumps bounded diagnostics to JFFS for later inspection.
- **Hardware QoS re-apply is now idempotent** — it skips a live-queue rewrite when the configuration hasn't changed, avoiding needless disruption.
- Built + shipped on the RT-BEXXU, both variants, 2026-07-29.

## v1.8.7 — Reaper Warden: IPv6 dual-stack + per-country block stats
- **Warden now protects IPv6 as well as IPv4.** The threat/geo firewall gained a parallel IPv6 stack — v6 threat-feed and country sets, v6 firewall chains, v6 CIDR validation, Spamhaus DROPv6 and per-country IPv6 ranges, and v6 anti-lockout for link-local / ULA / your delegated prefix. Manual block/allow entries are routed to the right family automatically.
- **New: Top blocked countries.** Each blocked country now has its own firewall rule and packet counter, so the Warden page shows a live **Blocked-hits** tile and a **Top blocked countries** card (refreshed every 30 s) — you can see which countries are actually hitting your router. The page wording was tightened, with an explicit "not a sole defense" caveat you can dismiss.
- **Full translation.** The complete Warden string set is now translated across all 24 non-English languages (was English-seeded).
- Built + shipped on the RT-BEXXU, both variants, 2026-07-28.

## v1.8.6 — Independent review of the audit remediation: clean, plus five hardening tightenings
- **Two independent adversarial code reviews — one of the v1.8.4/v1.8.5 audit fixes, one a fresh sweep of the Reaper-authored subsystems — found no live bugs, no security holes, and no performance regressions.** That is the sign-off on the whole audit-remediation arc below: the fixes landed cleanly. Each review verified every candidate against the source before reporting it, and the five low-risk, defense-in-depth items that survived are all closed here: a portability guard on the captive-portal cleanup path (so it compiles identically on every model), a belt-and-suspenders guard against a double-free on an out-of-memory error path in the traffic-history reader, a character-set gate on the LAN interface name used in the Gatekeeper teardown script (matching the guard its apply-path twin already carried), hard MAC-address validation before a device address reaches the Gatekeeper page's action buttons, and numeric emission of two Advisor status fields so a blank value can never malform the response. None was exploitable in normal use.

## v1.8.5 — Audit remediation: the low-severity batch
- **The remaining low-severity findings from the audit — 18 in all — are fixed.** These are the small robustness and hygiene items across the Reaper daemons and pages: an SNMPv3 config now refuses to emit a user with an empty passphrase (which the monitoring stack would silently reject anyway); the ping helper on the connection-diagnostics path now rejects anything but a valid host/IP before it runs; several file handles and buffers that could leak only on rare error paths are cleaned up; the captive-portal service frees all of its working memory on every exit path; the channel-quality monitor now logs its first event even in the first 15 minutes after boot; and a set of dead variables and duplicated render code in the dashboard and Traffic pages was removed. Three findings were deliberately left as-is with the reasons recorded (a duplicate default with no runtime effect, a kernel-accounting write that turned out to be load-bearing, and a no-behavior-change refactor).

## v1.8.4 — Audit remediation: the latent-issue batch
- **Twelve latent issues found by the audit are fixed** — real defects that the normal configuration doesn't trigger, closed defensively. Among them: the captive-portal config generator no longer treats a Wi-Fi network name as a text-format template; the threat/geo firewall (Warden) now keeps any stored country codes it doesn't recognize instead of dropping them when you save; the dashboard's by-band and history views guard against a malformed data response instead of blanking the page; the WAN firewall's SNMP allowance is narrowed to the single port the service actually uses; and the Advisor daemon's command runner, session-expiry check, and log redaction were tightened. None was reachable in normal use; each is now closed.

## v1.8.3 — Dashboard render fix + audit batches (Warden, redirects, i18n, build integrity)
- **Dashboard render fix.** A regression introduced with v1.8.2's new IPv6 logic (a scoping mistake) could leave the dashboard partly unrendered; the logic is moved to the correct scope and the dashboard renders fully again. The **IPv6 status icon** now also lights when the router has a working IPv6 gateway, not only a global address.
- **Warden anti-lockout + fail-safe corrections.** The threat/geo firewall's LAN anti-lockout rule was computing the wrong subnet, and its country-block updater could wipe its cached blocklist if a feed fetch failed mid-refresh. Both fixed — the updater now builds into a temporary set and only swaps it in on success (matching the threat-feed path), so a transient outage can't leave you unprotected, and the anti-lockout scope is corrected.
- **Login-redirect hardening.** Several standalone "no internet / redirecting" pages could be bounced to the admin login by the Reaper theme injector during a WAN outage — the exact moment those pages exist for. They are now excluded from injection.
- **Translation + build integrity.** A download-cap help string that gave inverted guidance in German and French was corrected; the new Warden page strings were seeded across all 24 non-English languages; and the Samba build stamp is now keyed to the patch contents, so an incremental rebuild can never ship a stale (unpatched) file server.

## v1.8.2 — Security batch: three high-impact fixes (start of the audit-remediation arc)
- **A large adversarial audit of the whole codebase drove this release and the four that follow.** An automated multi-agent audit swept every non-closed-source component — the Reaper-authored code, the shared ASUS/Merlin userspace, and the bundled third-party packages — and produced **73 verified findings**, each checked against the actual source, build config, and makefiles before it was called a defect. This release closes the three highest-impact: an IPsec configuration path where a profile name could reach a root shell, a port-forwarding field that could splice an extra rule into the firewall, and a file-read error path that freed the wrong pointer and could crash the web server. None was remotely exploitable in normal use, but each is the class of latent flaw the audit existed to find. A new IPv6 status indicator was also added to the dashboard this release (its scoping bug is fixed in v1.8.3). *(Every finding, verified, is catalogued in [`REAPER-FIXES.md`](REAPER-FIXES.md).)*

## v1.8.1 — Gatekeeper anti-lockout hardening + boot/teardown logging
- **Gatekeeper re-grandfathers your devices every time you enable it.** The grandfather-in step previously ran once; now every enable re-reads the router's full device knowledge (address table, DHCP leases, named-client list), so a device that happened to be asleep the first time can't be stranded on a later toggle.
- **More of the boot and shutdown sequence now leaves a log trail.** The LAN bring-up/teardown boundaries and Warden feed-fetch failures now write to the system log, so the several-minute boot-stabilization window and any feed problem are diagnosable from the log instead of invisible.

## v1.8.0a — Reaper Warden threat/geo firewall, a security-hardening pass, and Samba CVE backport
- **File sharing: Samba updated to 4.15.13a (backported security fix).** The SMB3 file server is
  built from Samba **4.15.13** — the last release that matches this router's compiler toolchain, and
  therefore no longer receiving upstream security updates. Rather than leave it untouched, this build
  **backports the upstream fix for CVE-2025-9640** (an uninitialized-memory disclosure in the
  `streams_xattr` module that could leak stray router memory into a file's alternate data stream) and
  marks the result **4.15.13a** (`smbd` reports `4.15.13-Reaper-a`). An audit of every Samba security
  advisory published since 4.15.13 confirmed the *rest* do not apply to this build — they're either in
  the Active-Directory/LDAP/Kerberos code that Reaper does not compile in, were introduced in a later
  Samba than 4.15.13, or depend on file-sharing options this build never enables. This one was
  backported as defense-in-depth. *(Applies to the **RT-BEXXU**, which is the model on Samba 4.)*
- **New: Reaper Warden — block malicious and by-country IP ranges at the router.** A new
  **Warden** page adds an optional, **default-OFF** firewall layer built on the kernel's `ipset`
  engine. It can automatically pull well-known **threat feeds** (known malware/botnet/attacker IP
  lists — FireHOL, Feodo, Spamhaus DROP, DShield) and refresh them on a schedule, block or allow
  **whole countries** by CIDR, and take your own **manual block / allow lists**. It has a strict
  **anti-lockout design** — your LAN, established connections, and an explicit allow-list are always
  let through *before* any drop rule — so turning it on can't strand you out of the router. Feeds
  are fetched over the router's own HTTPS and cached to JFFS so protection survives a reboot, and the
  rules **re-arm automatically** after any firewall restart or a cold boot. Optional drop-logging is
  available for auditing. *(Off until you enable it; costs nothing when unused.)*
- **Security-hardening pass (verified audit fixes).** A methodical firmware audit found and closed a
  set of latent issues in the Reaper-owned and adjacent code — all fixed and re-verified in this
  build: a format-string flaw in the network-tools handler; shell-injection hardening on the VPN
  Fusion (NordVPN/HMA) region fields, the WireGuard route path, and the Wi-Fi client-scan path; an
  out-of-bounds path check in the web server; an open-redirect guard on a login-redirect page; and
  input-sanitizing of the values spliced into the generated Gatekeeper firewall script. None were
  remotely exploitable in normal use, but each is now closed. *(Full technical detail in
  `REAPER-FIXES.md`.)*
- **Under the hood: cleaner theming and a lighter Traffic page.** The Reaper-native pages
  (Gatekeeper, Diagnostics, Wireless, Warden) no longer load the stock-page theme stylesheet that
  slightly fought their own layout, so they render cleaner. The **Traffic** page also stopped making
  a redundant second data request every refresh cycle — same information, half the polling.

## v1.7.9 — VPN page buttons restored, speed test made reliable, 2.4 GHz name fix completed
- **VPN client page: the buttons work again.** On the VPN client list ("VPN Fusion"-style page),
  the per-client controls rendered as solid **red blocks** and could not be used. Cause: a Reaper
  theme rule that recolors device icons in the Network Map "View List" was applied **site-wide**,
  and on the VPN page it painted the icon shapes into unreadable red squares. The rule is now
  scoped to the one place it was designed for, so the VPN page (and any other page using device
  icons) renders its controls normally — with the Reaper look unchanged where it belongs.
- **Internet speed test: no more first-try failures.** The built-in speed test could fail on the
  first run and then work on the second — reported across models. The test tool fetches its
  configuration from the internet exactly **once, with no retry**, so a just-booted or long-idle
  router could miss on a cold DNS lookup or a not-yet-synced clock and give up. The page now
  **retries once, silently,** before reporting an error — a real internet outage still reports
  immediately. In practice the "failed for no reason" case disappears.
- **2.4 GHz dashboard name: the remaining case.** v1.7.8 fixed the 2.4 GHz tile showing an
  internal ID when MLO reordered the network entries; field testing found one more path — when
  **2.4 GHz is excluded from MLO**, the band was dropped from the network's membership mask
  entirely, so the tile again fell back to the internal hex ID even though 2.4 GHz still
  broadcasts your network name. The dashboard now uses the network's real name for any band the
  mask misses (when a single main network exists), closing the loop.
- *Also this cycle (no firmware change):* a firmware-wide audit re-verified that the **ASUS
  cloud/remote-app tunnel is severed on every Reaper model** — reports of the ASUS app "still
  working" are local-network access only, which is expected and harmless. The teardown audit
  found no dangling references, broken shims, or dead-code hazards in the Reaper-owned surface.

## v1.7.8 — Encrypted SMB3 file sharing, SNMPv3-only, and SFTP as the secure default
- **Encrypted SMB3 file sharing (new "SMBv3" option).** The router's file-sharing service moves
  from the old Samba 3.6 (SMB2 at best) up to **Samba 4**, which speaks modern **SMB3 / SMB3.1.1**.
  A new **"SMBv3 (encrypted)"** choice on the Samba page turns on SMB3-only sharing with the
  transfer **encrypted end to end** (AES-GCM/CCM), so files copied to and from a USB drive on the
  router are no longer sent in the clear on your LAN. Current Windows, macOS, and Linux clients
  connect faster and more reliably over SMB3. *(Ships on the **RT-BEXXU** first; the other models
  stay on the older Samba for now.)*
- **SNMP is now SNMPv3-only — no more cleartext monitoring.** If you use SNMP to monitor the
  router, the insecure legacy versions (**SNMPv1 / SNMPv2c**, which send a plaintext "community
  string" password over the network) are **removed** — from both the service and the settings page.
  SNMP now requires authenticated, encrypted **SNMPv3** (default **SHA + AES**). This closes a
  common router-hygiene weakness that internet scanners actively look for.
- **SFTP is the recommended way to move files (FTP is now the deliberate legacy choice).** The
  **FTP** page gains a **"File transfer method"** selector with **SFTP pre-selected**. SFTP runs
  over the router's existing SSH service — your transfers and login are encrypted — whereas plain
  FTP is unencrypted. Picking FTP is now an explicit "I want the old, unencrypted way" decision;
  the page links you to the SSH settings (it never silently enables SSH for you). An `sftp-server`
  is bundled in the image so SFTP works out of the box once SSH is on.
- **USB dashboard: hubs no longer show "empty."** On the Reaper dashboard, plugging a **USB hub**
  into a port used to leave that port's tile reading "empty." Ports are now grouped by their
  physical slot, so a hub shows as connected and a port with several drives shows the **device
  count**.
- **2.4 GHz dashboard tile shows the right name again (with MLO on).** Turning on **MLO** could
  reorder the Wi-Fi entries so the dashboard's 2.4 GHz tile displayed a raw internal ID instead of
  the network name. The dashboard now reads all the radio entries, so each band's tile shows its
  correct SSID regardless of MLO.
- *Under the hood:* the bundled **net-snmp** was modernized (5.7.2 -> 5.9.4) for current CVE
  hygiene; SNMPv3 already worked, this is maintenance.

## v1.7.7a — GT-BE98: Wireless Log shows all four bands again (model-specific hotfix)
- **The Wireless Log page now lists every radio on the GT-BE98.** On the quad-band **GT-BE98**,
  **System Log &rsaquo; Wireless Log** was falling into the generic three-band layout, so the
  **second 5 GHz band was missing** and the **2.4 GHz radio and its connected clients were dropped**
  from the page. The GT-BE98 is now handled like its quad-band sibling (GT-AXE16000, which shares the
  same band order), so all four sections — 5 GHz, 5 GHz-2, 6 GHz, and 2.4 GHz — and their client lists
  appear correctly. *(This is a **GT-BE98-only** hotfix; the RT-BEXXU, RT-BE86U, RT-BE88U, and
  GT-BE98 Pro were not affected. The same fix is folded into the shared code for the next release of
  every model, where it is a harmless no-op on the non-quad-band units.)*

## v1.7.7 — VPN pages: no theme flash, plus a Network-Map lighting-control fix
- **No more stock-color flash on the VPN pages.** Opening **VPN &rsaquo; VPN Client** (PPTP/L2TP)
  or **VPN Server** could show the original blue ASUS styling for a split second before the Reaper
  theme took over. The nested settings panel now stays hidden over a dark background until it is
  fully themed, then fades in — so only the Reaper look is ever visible.
- **AURA/RGB lighting: no stray scrollbar.** On models with AURA/RGB lighting, the effect-scheme
  selector on the **Network Map** router panel showed an unnecessary horizontal scrollbar. That list
  already pages with its own left/right arrows, so the scrollbar has been removed. *(Affects the
  RGB-capable models; the RT-BEXXU has no AURA hardware.)*

## v1.7.6 — VPN theming: no stuck colors, no endless loading, single scrollbar
- **VPN Client/Server pages theme correctly and settle down.** On **VPN &rsaquo; VPN Client**
  (PPTP/L2TP) and **VPN Server**, the server-list cards could stay stuck in the original ASUS
  blue/teal, and the page never went idle — a constant churn of background activity that some users
  saw as the page "always loading." Two routines were fighting over the panel's size and fell into a
  loop; the build now lets the page size itself and simply keeps the Reaper theme on top, so the
  pages render in the Reaper colors and go quiet once loaded.
- **One scrollbar on the Internet Speed test.** Under **Traffic Manager &rsaquo; Internet Speed**
  (Adaptive QoS), the page could show a second, inner scrollbar. The speed-test panel now grows to
  fit its content, so the page uses a single page scrollbar.

## v1.7.5 — Security: close the last `openssl passwd` command-injection path (ASUS PSIRT case 1006563)
- **Removed a root command-injection path in password verification.** An internal helper that
  falls back to the `openssl passwd` command-line tool (used only when the C library's own
  password hasher is unavailable) built that command as a shell string with the *supplied
  password* embedded in it — so a password containing shell metacharacters could have run
  arbitrary commands as root. This was a second, independent copy of a flaw already fixed
  elsewhere in v1.0 (finding **C6**); this copy lived in the `libpasswd` helper reached from the
  HTTP and WebDAV/SMB basic-authentication paths, with the attacker-supplied password as the
  injected value. The helper now runs `openssl` directly with the password as a literal
  argument — never through a shell — so no metacharacter can be interpreted. No change for
  normal logins.
- Found and closed while preparing the coordinated-disclosure proof-of-concept material
  requested by **ASUS PSIRT (case 1006563)**; the C6 fix was point-fixed in v1.0 and is now
  class-fixed across every `openssl passwd` sink. See [`REAPER-FIXES.md`](REAPER-FIXES.md).

## v1.7.4 — DHCP client picker + Wireless page theme-flash (on-metal fixes)
- **Static-DHCP client picker back on the button.** On **LAN &rsaquo; DHCP Server**, the
  "select a client" dropdown for the Manually Assigned IP table is again anchored to its
  input and now opens **upward** with its own scroll — instead of floating detached in the
  middle of the page (a side effect of the earlier clip fix). Opening upward also keeps the
  full list on screen without the framed page having to grow.
- **Wireless page no longer flashes stock colors.** The heavier settings pages (Wireless,
  DHCP) could still show the old ASUS styling for a split second when opened, because the
  framed content was revealed a touch too early. The frame now stays dark until it is fully
  themed, so the flash is gone there too.

## v1.7.3 — Gatekeeper reliability: no lockout, dependable cold-boot arming
- **No more admin lockout.** With Gatekeeper on, a device that was asleep or idle when you
  enabled the feature — potentially including the computer you administer from — could be held
  at the gate with no route back to the page that turns Gatekeeper off, and enabling it could
  quarantine much of the household at once. Turn-on now grandfathers every device the router
  already knows (its address table, its DHCP leases, and its named-client list), not only the
  ones talking at that instant, and the firewall now always leaves the HTTPS admin page
  reachable, so the owner can never be fenced out of the control that disables the feature.
- **Dependable arming after a cold boot.** After a full power-cycle, Gatekeeper could come up
  reading "on" without actually enforcing, because it tried to build its rules before the
  network was ready. It now resolves the network details when the rules are applied and
  re-applies them the moment the bridge is up, so enforcement is in place on its own.
- **Clear on/off state.** The Gatekeeper page now shows an "Arming" state while enforcement is
  coming up, and escalates to a visible "Not enforcing — check the System Log" warning if it
  ever fails to arm — so the feature is never silently off while appearing on.

## v1.7.2 — AiMesh node onboarding fix + UI polish + full menu translation
- **AiMesh node onboarding restored.** A factory-fresh router running Reaper could not be
  **found** when another router searched for a new AiMesh node — the search would run and
  return nothing. Cause: the v1.2.7 first-boot cleanup set the "already configured" flags on
  by default, which (as a side effect deep in the closed Wi-Fi stack) stopped the onboarding
  radio beacon a fresh node uses to announce itself, and left WPS onboarding enrollment
  disabled. The factory defaults are back to stock, and the first-boot setup wizard stays
  retired the intended way — at the web-server layer — so nothing about the login/first-run
  experience changes. A mesh already built under stock/Merlin firmware and then flashed to
  Reaper was never affected; this only concerns onboarding a **new** Reaper node. (After
  updating, a router intended as a node must be factory-reset on this firmware to become
  discoverable.)
- **Static-DHCP client picker no longer clips.** On **LAN &rsaquo; DHCP Server**, the
  "select a client" dropdown on the Manually Assigned IP table was cut off at the bottom of
  the page (adding a few rows to the table was a partial workaround). It now floats centered
  with its own scroll, so the full client list is always reachable.
- **No more stock-style flash.** Some settings pages briefly showed the old ASUS blue for a
  split second before the Reaper theme took over. Pages now paint dark from the first frame,
  and the framed content stays hidden until it is themed, so the flash is gone.
- **Full menu + page translation pass.** A sweep for untranslated interface text found that
  the **Gatekeeper** page and the **Wireless** diagnostics page still carried English in the
  24 non-English languages, and fourteen menu/tab labels (AI Advisor, System Info, VPN Status,
  VPN Director, DNS Director, Site Survey, Traffic Limiter, NFS Exports, Temperature,
  Notification, Tweaks, and others) were hard-coded English. All are now translated across the
  full language set (machine-assisted; native review still recommended before public release).
  Product and protocol names (Gatekeeper, AiMesh, VPN, IPv6, SNMP, MAC, Wi-Fi&hellip;) stay in
  their standard form, matching the stock UI's own convention. *Known limit:* the Gatekeeper
  "awaiting approval" waiting-room page is generated by the web server itself, outside the
  translation system, and remains English.
- All four changes are in shared code, so every model (RT-BEXXU / RT-BE86U / RT-BE88U /
  GT-BE98 / GT-BE98 Pro) carries them; RT-BEXXU is the primary, hardware-validated build.

## v1.7.1 — Security remediation batch + Network Map panel fix
- **Post-release security review — every finding fixed.** A full security audit of the v1.7.0
  release (centered on the new Gatekeeper subsystem) found no critical or high-severity issues;
  all ten findings — two medium, five low, three informational — are fixed in this rung:
  - **Wireless Diagnostics CSRF guard.** The Wireless page's control endpoint now requires the
    router's request token on every state-changing action (channel scans, captures, the
    channel-quality monitor toggle), the same guard the other Reaper endpoints already carried —
    a page you were tricked into visiting can no longer bounce a radio.
  - **Gatekeeper device-list race closed.** A decision saved at the same moment a guest pass
    expires can no longer be silently lost — both writers now re-read the device list under a
    lock before updating it.
  - **Gatekeeper MAC validation (defense-in-depth).** Every stored device entry is validated as
    a real MAC address before it reaches the firewall apply script, so a corrupted or hand-seeded
    hostile value is dropped, never executed.
  - **Robustness and hardening:** the Gatekeeper daemon ages out stale devices so its table can't
    fill over long uptimes; the first-boot wizard now submits the new password by POST (not in
    the URL) and actually checks the result — a failed credential save shows an error instead of
    redirecting as if it worked; reduced Gatekeeper self-heal fork churn; duplicate new-device
    log entries suppressed across daemon restarts; Traffic Analyzer per-queue QoS counter reads
    batched.
- **Network Map client panel fixed.** The client-status panel could overflow sideways into a
  horizontal scrollbar; the panel and its content box are now sized to fit, and the map's
  content area was widened to use the space properly.
- RT-BEXXU flashed on hardware 2026-07-21 (core UI and Network Map verified). All 5 models built + shipped, both variants each
  (RT-BEXXU / GT-BE98 / GT-BE98 Pro / RT-BE86U on 2026-07-21, RT-BE88U on 2026-07-22).

## v1.7.0 — Gatekeeper: device access control + field-test fixes
- **Gatekeeper — you decide who gets on your network.** A new opt-in, **default-deny device
  access control** with its own page and menu entry. When you enable it, everything already on
  the network is grandfathered in; from then on each newly seen device is **held at the gate** —
  no internet, no reaching other LAN devices — until you choose: **Block**, **Full access**,
  **Internet only**, or a **timed Guest pass**. A held device that opens a web page sees a themed
  "awaiting approval" notice instead of a dead connection, and every new arrival is recorded in
  the system log. Enforcement lives at the firewall/bridge layer and **self-heals** — if a stock
  service flushes the rules, they are re-applied within seconds. Off by default. The page states
  the honest limitation: a MAC address *identifies* a device, it doesn't *authenticate* it — a
  determined user behind your Wi-Fi password can spoof one.
- **Factory-reset first-run fixes** (found in GT-BE98 field testing, applied to all models):
  a factory-fresh box could bounce forever between the dashboard and the first-run wizard (the
  wizard's Wi-Fi step was being rewritten into the app shell, which re-fired the gate — no
  settings reachable at all); and credentials entered in the first-boot wizard could fail to
  actually apply, locking the new login out after a factory reset. Both fixed.
- **UI fixes (series-wide).** The dashboard client panel's "VIEW LIST" control — previously an
  inert placeholder — now opens a client-list modal grouped by band (6 / 5 / 2.4 GHz / Wired)
  with name, IP, IPv6 and MAC; the WAN page's assigned-DNS list no longer clips its lower rows
  off-screen; the Network Map no longer stacks a double scrollbar.
- **Diagnostics v1.0.1** — fixes from the diagnostic report's first on-hardware run: MAC
  addresses written *without* colons are now pseudonymized like every other form (a redaction
  gap); over-eager masking of short brand words fixed; hardware-acceleration and QoS sections no
  longer come back empty on tools the shell lacks; per-station detail now covers guest and
  secondary interfaces; and the page layout was tightened around the download button.
- Consolidates the internal v1.6.8 build. All 5 models, both variants, built + shipped
  2026-07-21.

## v1.6.7 — Reaper Diagnostics
- **One-click sanitized diagnostic report.** New **Administration &rsaquo; Diagnostics** tab with a
  single Download button. It collects everything a network engineer would gather by hand — model
  and firmware identity, per-radio channel/width/signal health and client counts, wired port link
  states, hardware-acceleration and QoS engine readings, DHCP lease and service overview, and
  recent kernel/system log excerpts — in one pass, then pushes the **entire report through a
  redaction engine** before a single byte is written out.
- **Privacy by architecture, not by checklist.** Passwords, Wi-Fi keys and tokens are *never
  collected* (the report only notes SET/EMPTY); every MAC address becomes a consistent pseudonym
  (`MAC-3`), Wi-Fi names, usernames and hostnames become tokens, and all public IPv4/IPv6
  addresses are masked. Pseudonyms stay consistent within one report — a device can be followed
  across sections without revealing which device it is — and every report opens with a ledger
  counting exactly what was withheld. Because the whole document passes through the engine, even
  log lines nothing anticipated cannot leak identifiers.
- **Plain text, downloaded, never transmitted.** The report saves through the browser as a
  readable text file for review before sharing; the router sends nothing anywhere on its own.
  A busy overlay guards the 20–30 second collection. Available in all 25 interface languages,
  and the same collector is callable from SSH as `reaper_diag`.
- Both images built + shipped 2026-07-20.

## v1.6.6a — GT-BE98 System Info fix (GT-BE98 only)
- **Quad-band radio mapping on System Info.** Field testing on the GT-BE98 showed the System Info
  page mishandling this model's unusual radio order (both 5 GHz radios first, 6 GHz third, 2.4 GHz
  *last*): wireless client counts appeared under the wrong band headings with the 6 GHz row empty,
  the Temperatures panel rendered blank, and the fourth radio was missing from the Wireless Driver
  Version list. The page's per-model mapping had entries for the GT-BE98 Pro but never for the
  non-Pro — it now handles both, restoring correct client counts per band, all four radio
  temperatures with live charts, and the full driver-version list.
- GT-BE98 images only; built + shipped 2026-07-20.

## v1.6.6 — First-boot language selector, QoS Cake jitter tuning
- **Language selector on the first-boot wizard.** The initial setup card (administrator
  username/password and Wi-Fi) now carries a language selector at the top, so the interface
  language can be chosen *before* credentials are set. The selection carries through into the rest
  of the UI. Previously the wizard was English-only until setup was finished and the language could
  be changed from the main interface.
- **Cake QoS — ACK filtering on upload.** In Cake mode the upload shaper now filters redundant TCP
  ACKs. On an asymmetric line the upstream carries the ACK flood for every download; thinning those
  ACKs frees upstream capacity and cuts the upload-direction jitter that asymmetry creates. Applied
  to the upload direction only (the constrained one).
- **Cake QoS — tighter latency target.** Cake's AQM now targets a realistic broadband base RTT
  (50 ms) instead of its 100 ms internet default, trimming the standing queue and jitter. The value
  is adjustable via the `qos_cake_rtt` setting for per-line tuning without a rebuild.
- Both images built + shipped 2026-07-19.

## v1.6.5 — QoS download tuning
- **Download cap made foolproof.** The Hardware-Classful ingress policer now applies **10%
  headroom automatically** — you enter your measured download speed and the router caps at 90% of
  it. Previously the field expected you to do that math yourself, and entering your full line rate
  (a natural mistake) collapsed download throughput. The help text now says to enter your measured
  speed; no manual 90% math.
- **Cake mode consistency.** The Cake QoS mode applies the same 10% headroom to both upload and
  download, so both QoS engines read the bandwidth fields the same way — as your measured speeds.
- Both images built + shipped 2026-07-19.

## v1.6.4 — VPN theme fix, tablet layout, i18n sweep, audit hardening
- **VPN pages themed correctly.** The VPN Client and VPN Server pages had kept the stock ASUS
  blue accents. The cause was a cache-busting query string on the theme stylesheet request that
  the router's web server rejected, so the Reaper theme never loaded inside those nested frames.
  The query is removed and a dedicated palette pass recolors the remaining stock blues (buttons,
  checkboxes, input focus rings, dropdowns) to the Reaper crimson/jade/amber set, including
  retheming a stock cyan notice box on the VPN Server page.
- **Tablet / iPad layout.** On narrower tablet viewports some fixed-width pages could render past
  the screen edge with no way to pan to the cut-off content. The framed content area now pans
  horizontally when a page is wider than the column, and the header condenses so it always fits.
  (Phone-size screens remain out of scope by design.)
- **Network (SDN) page cut-off fixed.** Expanding a profile's General settings while Advanced
  settings were collapsed could push content past the frame with no way to scroll to it. The
  frame now grows to fit its content in that case.
- **Language coverage.** A full pass over every Reaper page confirmed all user-facing text follows
  the selected language. The first-boot setup wizard — which postdated the earlier translation
  work — was fully tokenized and translated across all 25 languages (machine-assisted; native
  review still recommended before public release).
- **`rchqd` monitor — syslog trail.** The passive channel-quality monitor now records
  degraded/recovered transitions to the system log (edge-triggered and rate-limited per radio),
  so interference events leave a timestamped trail even when the Wireless page is not open. It
  remains strictly read-only — it never changes a channel.
- **Audit hardening.** A pre-build security and quality review of the release drove a set of
  robustness fixes: the monitor's logging no longer depends on its JSON status file being
  writable (so a full RAM disk cannot silence it), a partial status write can no longer overwrite
  the last good one, radio state is cleanly closed out on a wireless restart, the log rate-limit
  now uses a monotonic clock (immune to time-sync steps), and its per-tick diagnostic overhead is
  roughly halved. On the web side, per-frame observers are now released on navigation and the
  tablet width logic was made convergent. No exploitable issues were found.
- Both images built + shipped 2026-07-19.

## v1.6.3 — Channel-quality syslog trail
- **`rchqd` degraded-event logging.** The opt-in passive channel-quality monitor gained a system
  log trail: when a radio's current channel deteriorates past the advisory threshold it writes one
  warning to the system log (with the channel and the measured interference), and a matching notice
  when it recovers. Logging is **edge-triggered** (only on the transition, not every sample) and
  **rate-limited per radio** so a channel hovering near the threshold cannot flood the log. This
  gives a timestamped record of interference events — useful for correlating intermittent Wi-Fi
  problems — without anyone needing to have the Wireless page open. The monitor stays opt-in and
  strictly read-only. Both images built + shipped 2026-07-19.

## v1.6.2 — Auto Scan across all bands
- **Band selector.** Auto Scan now runs on any radio, one band at a time via a selector, with a
  **separate report per band** and **Pin-best pinning the winner to that radio** — so you build up
  the best 6 GHz / 5 GHz / 2.4 GHz channels independently.
- **5 GHz + 2.4 GHz coverage.** 6 GHz is unchanged (the distinct 320 MHz blocks). **5 GHz** sweeps
  the nine non-DFS 20 MHz channels (UNII-1 36–48 + UNII-3 149–165) — **DFS 52–144 is skipped** so a
  scan stays quick — and Pin-best pins the **80 MHz block** around the winner. **2.4 GHz** sweeps
  1 / 6 / 11.
- **Band-aware report + plot.** The spectrum plot uses a per-band frequency axis and moves labels
  outside the bar for the narrow 20 MHz channels; the report names the band in its title.
- **Measurement hardening.** The first `chanim` sample after each channel change is discarded and a
  short settle added, fixing the occasional bogus post-restart noise-floor reading.
- Both images built + shipped 2026-07-18.

## v1.6.1 — Channel-Quality Auto Scan + passive monitor
- **Auto Scan (6 GHz).** A one-click sweep on the Wireless Diagnostics page that measures every
  6 GHz 320 MHz channel and ranks them by cleanliness, so a user can move to a clean channel
  without reading `chanim` output. It pins each candidate through the same supported
  channel-lock path (a live `wl chanspec` set does not stick on a running AP), samples the radio
  on it, then **restores the original channel**; the operator clicks **Pin best** to commit the
  winner (with a best-vs-current comparison shown first). It is the only path on the page that
  changes a channel — deliberately disruptive, warned before it runs. The candidate set is the
  distinct physical 320 blocks (one PSC representative each) across the whole band, validated
  against real hardware output.
- **Sweep is unattended-safe.** Closing the tab or navigating away stops the sweep immediately
  (unload beacon) and, as a crash backstop, a stale browser heartbeat aborts it — either way the
  radio is returned to its original channel. A progress bar with an ETA shows how far along it is,
  and the admin session is kept alive during the scan (the normal idle timeout resumes when it
  ends).
- **Downloadable report.** The results can be printed or saved as a **landscape PDF**, or
  downloaded as a self-contained **HTML** document — a ranked table (channel, frequency span,
  occupancy, free airtime, glitches, noise floor, score) plus a left-to-right **spectrum plot**
  that places each 320 block by frequency and colors it by occupancy, so the clean and dirty parts
  of the band are visible at a glance.
- **Clear-results button** on the on-demand capture panel (resets the view without a page reload).
- **Passive channel-quality monitor (`rchqd`) — opt-in, read-only.** A new background daemon
  (off by default) that watches only the *current* operating channel — the same non-disruptive
  on-channel read the capture panel uses — and raises a soft "degrading — consider Auto Scan"
  advisory when it deteriorates. It never changes a channel or restarts wireless; the remedy is
  always the user running Auto Scan. Modeled on `rtrafd`.
- **i18n.** All new strings tokenized across the 25 language dicts.
- Both images built + shipped 2026-07-18.

## v1.6.0 — hardening pass + full 24-language UI
- **Traffic collector (`rtrafd`) efficiency.** The live-view writer took the nvram lock three
  times on every 100 ms tick for values that only change on a settings apply (~30 lookups/s for
  the router's whole uptime); those are now cached and refreshed once a second (**30/s → 3/s**).
  The WAN byte counters are read by holding the sysfs files open and using `pread` instead of
  reopening them every tick; each top-talker's MAC is resolved once when its row is built rather
  than re-scanned on every write; and the Traffic Analyzer Live view rebuilds its per-device /
  per-network / top-talker tables at ~1 Hz (their data only changes every 5 s) while the rolling
  charts still draw every poll. All bounded — no behavior change.
- **Robustness.** All 83 of `rtrafd`'s ring allocations are NULL-checked at startup (was 4); the
  Advisor daemon (`rmcpd`) no longer leaks a pipe descriptor and a zombie child if a command's
  output handle fails to open after the fork.
- **Input-validation hardening (defense-in-depth).** The Advisor arm handler strips CR/LF and
  validates the client pin as a dotted-quad before writing it into its newline-delimited session
  file; the boot-time firewall sweep validates `lan_ifname` before splicing it into an `iptables`
  command.
- **AI Advisor — "Save settings" now confirmed.** It was posting to the apply CGI without the CSRF
  token and reporting success unconditionally; it now sends the token and checks the response, so a
  rejected save is reported instead of silently claimed. The **Refresh** button was also moved in
  next to the title.
- **Login / Logout favicon.** Both screens show the Reaper emblem in the browser tab (were the
  stock ASUS icon).
- **Full UI translation — 24 languages.** Every Reaper-authored page string is now translated into
  all 24 non-English languages the firmware ships (was English-in-every-dict fallback). A
  completeness sweep also caught the last hardcoded strings — the rail clock's weekday/month names,
  the AI Advisor "Copy snippet" button, the traffic-quota line, the Wi-Fi encryption labels, the
  dashboard tab title — and tokenized them. Where a translated label runs longer than its space it
  now truncates with an ellipsis and reveals the full text on hover, instead of stretching the
  layout. *Machine-assisted translation; English stays selectable.*
- **Cleanup.** Removed a never-fired QoS mode-link branch; stranded the disabled EULA-policy check
  as a no-op stub; corrected a stale watchdog comment about the acsd cooldown.
- Both images, built + shipped 2026-07-17.
- **RT-BE88U brought directly to v1.6.0** (2026-07-18): the full v1.5.2 → v1.6.0 line
  cherry-picked onto the RT-BE88U branch (its first build since the v1.5.0e port), both
  image variants. The RT-BE86U / GT-BE98 / GT-BE98 Pro branches remain at v1.5.9.

---

## v1.5.9 — Traffic Analyzer resilience + shell scrollbar
- **Traffic Analyzer can no longer freeze.** The live view could stick at its last paint while
  the browser kept polling (one stalled response wedged the poll loop's in-flight guard forever).
  The fetch path is rebuilt on a single always-fires completion point with a request timeout and
  a watchdog that aborts any hung request, so the loop always self-heals. When polls stop
  answering, the page now keeps its last data and flips the status pill to an amber
  **"No response"** marker instead of silently rendering zeros; the history windows
  (5 min / 24 h / 14 d / By month) also auto-refresh every 30 s instead of going stale.
- **Master page scrollbar themed everywhere.** The far-right top-window scrollbar was
  black-track/crimson-thumb on the dashboard but stock gray on every shell-framed page; the
  app shell (the top window for all framed pages) now carries the same red scrollbar rules.
- UI only, both images, built and shipped 2026-07-17.
- **Wireless page — quad-band radio ceiling.** The v1.5.8 Wireless diagnostics backend
  enumerated at most three radios (a value carried over from the tri-band RT-BEXXU), so on a
  four-radio model it hid the 4th radio and refused a channel capture on it. The ceiling is
  raised to four; it is self-configuring — a radio with no interface is skipped — so the
  RT-BEXXU still shows exactly its three. No visible change on the RT-BEXXU.

### v1.5.9 — sibling models RT-BE86U, GT-BE98, and GT-BE98 Pro
- **Both GT-BE98 variants and the RT-BE86U brought up to v1.5.9** (all of the above, plus
  the whole v1.5.2 → v1.5.9 line they had been missing: boot-efficiency, QoS v5 download
  side, the first-boot credentials wizard, the AI Advisor wireless-stations tool, the
  audit-fix rung, and the Wireless diagnostics page). All built in both variants — the
  cherry-pick applied with zero conflicts on each branch.
- **GT-BE98 (non-Pro) field-report fix.** A tester's GT-BE98 showed only three of four
  radios (no 6 GHz), an empty Wi-Fi client list, and roughly half the expected wired
  throughput. Root cause: the earlier GT-BE98 port linked four **GT-BE98 Pro** closed
  binaries as a stopgap — including the model-specific radio/board bring-up object — and the
  Pro's radio layout differs from the non-Pro's. All four are now the **official ASUS GT-BE98**
  binaries (from ASUS's GT-BE98 GPL source drop), with the build-compat shim reworked
  accordingly.
- Sibling-model images: flash only with a recovery path ready.

## v1.5.8 — Wireless diagnostics page
- **New "Wireless" diagnostics page** (`Reaper_Wireless.asp`): a live radio-state snapshot for
  every band, a one-click **channel Lock/Unlock** that pins the currently-running channel through
  the stock apply flow (so automatic channel selection can never drift it), a decoded view of the
  channel **exclusion list** and regulatory/board branch actually in effect, and an **on-demand
  channel-quality capture** — a bounded 1 Hz channel-utilization sample written to CSV in RAM
  (never always-on, never syslog). This productizes the manual capture loop that located a
  real-world 320 MHz interferer on the 6 GHz band on 2026-07-16.
- **Factory-default fix:** two duplicate defaults for the 6 GHz PSC-channel setting (`psc6g`)
  disagreed, so a factory reset landed on the unintended value; aligned to the intended default.
- Flashed to the physical RT-BEXXU 2026-07-16.

## v1.5.7 — Audit fix rung
- Fixes from a 34-agent adversarial sweep of all Reaper-authored code (21 raw findings —
  12 upheld and fixed, 9 refuted and recorded so they are not re-found):
  - **Smart Connect:** the band bitmask is now indexed by slot, not by band count, so the
    toggle stays correct when a radio is disabled.
  - **System Log:** Broadcom wireless-driver errors are no longer filtered out of the log.
  - **Traffic Analyzer collector:** radio queries moved out of the hot sampling path, and
    rate reporting corrected.
  - **AI Advisor:** every tool command now carries a hard time bound, and session cleanup is
    armed before it can first be needed.
  - Smaller fixes: firewall mangle flush when leaving HW QoS, port-forward names with spaces,
    AiMesh config-sync client count, Advisor page CSS.

## v1.5.6 — AI Advisor: wireless-stations read tool
- **New curated read tool `get_wireless_stations`** (AI Advisor image only): per-station
  signal/PHY/rate detail plus channel-utilization for every wireless interface, gathered by one
  fixed, no-caller-input pipeline — so the Advisor can reason about Wi-Fi health without shell
  access. Metal-validated on the RT-BEXXU.

## v1.5.5 — First-boot security wizard + dashboard/UX fixes
- **Mandatory first-boot / factory-reset credentials wizard.** A fully Reaper-authored, themed
  setup page (`Reaper_FirstBoot.asp`) now forces the admin **username + password** on a
  factory-fresh box (default `admin/admin` is disabled once setup completes, and "admin" is
  rejected as a password), then forces the wireless page until a **WiFi PSK** is set, before any
  other UI is reachable. Replaces the stock forced password-change gate (which lives in a closed
  blob and only changed the password). Upgrade-safe: the gate derives from live state, so a
  configured or upgraded box never sees it. This is the concrete mitigation for deferred finding
  **H15 (default admin creds)** and the primary credential-hygiene item from advisory
  **AA26-194A** (see `BACKLOG.md`). *Known limitation: the WiFi step releases on "configured",
  so an explicitly-open network can skip the PSK.*
- **Internet status now updates itself during boot.** The dashboard Internet card **and** the
  shell-header WAN pill poll the WAN state on their own and flip to Connected without a manual
  refresh — fast (~4 s) while disconnected, slow (~30 s) once up.
- **Waiting overlay for Reaper pages.** A reusable themed "applying" modal (modeled on the reboot
  overlay) now covers apply/arm actions on the Reaper-native pages that lacked one.
- **AI Advisor IP pin persists.** The client-IP pin is prefilled from the router and survives
  visits, reboots, and a later Save Settings (it was previously wiped to empty).

## v1.5.4 — QoS v5.1: download-policer metal tuning
- **Burst/rate fixes for the new download-side policer** from on-hardware tuning
  (2026-07-15). Small correctness rung on top of v1.5.3; no new features.

## v1.5.3 — QoS v5 download side + Traffic Analyzer Live (100 ms) + device identity
- **QoS v5: the download side.** A WAN-ingress RX policer (driven by the download bandwidth
  setting) plus a downstream DSCP→WMM class lift, so download traffic is now policed and
  classified like upload — previously the classful engine shaped upload only.
- **Traffic Analyzer "Live" tightened to 100 ms.** The collector tick and the page's Live
  option move together (200 ms → 100 ms) as a matched pair, with an in-flight request guard
  so a slow response skips ticks instead of stacking against the single-threaded web server.
- **Device identity rows.** Top Talkers and Top Devices now show the device **name** with an
  "IP · MAC" subline (names from the same source as the dashboard's client list), instead of
  raw addresses.

## v1.5.2 — Boot efficiency, round 1
- First fixes from the boot-behavior recon: the web UI no longer restarts when a USB drive
  mounts during bring-up, and watchdog wait paths were unblocked — trimming avoidable UI
  drops in the several-minute boot-stabilization window. (The wider boot-efficiency
  investigation remains open in `BACKLOG.md`.)

## v1.5.1 — GT-BE98 blob re-base (sibling models)
- The GT-BE98 ports' closed-source blobs were **re-based from the second-hand community
  import onto the official ASUS GPL drop** (102_39274), and the GT-BE98 quad-band gap was
  closed (`HAS_6G` — the 6 GHz radio was never enabled in the v1.5.0e port, the prime suspect
  in the GT-BE98 field report tracked in `BACKLOG.md`). Sibling-model build rung;
  no functional change to the RT-BEXXU image.

## v1.5.0e — Factory-reset recovery fix + first sibling-model builds
- **Fixed the factory-reset redirect loop.** On a factory-clean box the first-run gate pages and
  Reaper's serve-time bounce redirected each other forever, so the UI never loaded and the router
  appeared bricked (recoverable only via the ASUS rescue tool). Setup/QIS pages are now excluded
  from the bounce. *Reported by tester PorscheT — credit him in the public release notes.*
- **First builds for sibling BCM4916 models.** GT-BE98 Pro, GT-BE98, and RT-BE86U (plus RT-BEXXU)
  each built in both variants — closing the "wider BE-series support" investigation.
  Sibling models: flash only with a recovery path ready. (A GT-BE98 field report is tracked in
  `BACKLOG.md`.)
- **Reproducible branch builds.** The `BEXXU-only` branch now builds cleanly from a fresh
  checkout (it previously depended on uncommitted working-tree deletions).

## v1.5.0d — De-ASUS rebrand (UI only)
- **New wordmark banner.** The `REAPER1` wordmark banner replaces the previous logo everywhere it
  appeared: the dashboard and app-shell headers, the login/logout card, and the stock-page banner.
- **AiMesh backdrop.** The AiMesh node card now uses the `RLogo` artwork; the old ASUS logo asset is
  removed from the build entirely.
- **Live rail clock.** The "ASUS · Merlin · Reaper" wordmark at the top of the left rail is replaced
  by a themed, live, 24-hour **router-time clock** (date + seconds), on both the dashboard and the
  app shell. No functional/firmware change.

## v1.5.0c — Compliance: license headers + font license (no functional change)
- **SPDX license headers** (`GPL-2.0-only` + copyright) added to every Reaper-authored source
  file (the Traffic Analyzer and AI Advisor daemons, the theme-injection filter, the Reaper
  pages, CSS, and Makefiles) — provenance hygiene, no behavior change.
- **Font license shipped in the image.** The SIL Open Font License 1.1 text is now installed as
  `www/fonts/OFL.txt` so the license for the bundled Inter/Rajdhani web fonts travels with the
  firmware, as OFL 1.1 requires. Part of the 2026-07-13 release-compliance pass.

## v1.5.0b — Traffic Analyzer "Live (200ms)" mode + diag-aware AI Advisor
- **New "Live (200ms)" refresh mode** on the Traffic Analyzer. The collector's base tick moves
  from 1 s to 200 ms (work-time-paced so heavy samples never stretch the interval), giving the
  live WAN view true 5 Hz updates; the 1 s / 10 s / 30 s options remain and 1 s stays the default.
- **AI Advisor `initialize` instructions are now diagnostics-aware.** When a session has network
  diagnostics enabled, the Advisor is told the probes are active and to run them itself, instead
  of the previous static "read-only" wording that made it defer network probes back to the user.

## v1.5.0a — Network Diagnostics: AI network probes (+ security hardening)
- **AI Advisor network-diagnostics tier (AI Advisor image only).** When you explicitly allow it,
  the read-only Advisor can run bounded, read-only network probes — `ping`, `traceroute`,
  `DNS lookup`, `netstat` — so your own AI assistant can tell whether a problem sits at the
  **router, the client device, the ISP, or the wider internet**. It still cannot change a single
  setting.
  - **Off by default, per session.** An "Allow network diagnostics" checkbox on the arming
    card must be ticked *each time you arm*; the consent lives only in that session and never
    persists.
  - **Scoped + audited.** Every probe is fixed-argument (no shell), one-at-a-time, time-bounded,
    output-capped, and written to the system log. Targets are validated and resolved first, and
    loopback / link-local / ULA / private addresses that are **not** on this router's own LAN are
    refused — for IPv4 **and** IPv6 — so the Advisor cannot be turned into an internal-network scanner.
- **Security hardening.** The AI Advisor control endpoint now requires the router's request token
  on any state-changing action (CSRF protection); diagnostic input-validation, interface-name
  checks, and traffic-analyzer output escaping were tightened.
- **No bundled packet capture.** An earlier internal build carried a `tcpdump`-based "Packet
  Capture" page; it is **not** included — it pulled a large legacy dependency for a niche need.
  If you want packet capture, install `tcpdump` via Entware on a USB stick.
- **Metal-validated** on the RT-BEXXU: the AI Advisor and its diagnostics tier verified on hardware.

## v1.4.9a — UI polish: navigation, in-rail language selector, AiMesh, System Info
- **Slimmer left navigation.** The side nav is back to just wide enough for the menu items and
  the "ASUS · Merlin · Reaper" wordmark on one line.
- **Language selector moved into the rail.** It now sits above the "General" heading as a compact
  "Language:" dropdown instead of in the topbar.
- **AiMesh card.** The router backdrop image now extends down behind the room selector so the
  dropdown sits on the image, up to the divider — closing the dark gap.
- **System Info "Features" row** now advertises Reaper's own packages (AI Advisor, Traffic
  Analyzer, HW QoS classful) alongside the stock
  capability list, so it reflects the true per-build feature set. UI/presentation only; both images.

## v1.4.9 — USB second factor made binding + AI Advisor lock-state UI fix
- **The USB key is now binding.** "Remove USB key" (unenroll) now requires the enrolled
  stick to be physically inserted — someone with only the admin login and the arming code can
  no longer strip the third factor, including via the deprovision-then-unenroll path. If the
  key is lost, a **factory reset / nvram clear** is the only way to clear it. This makes the
  USB factor tamper-resistant: removal is now at least as strong as arming.
- **The AI Advisor page reflects the lock immediately.** While a session is armed the page now
  re-polls the router every few seconds, so pulling the USB key (or a session timeout/disarm)
  flips the card to "locked" within seconds instead of counting down a session the router has
  already torn down. (The router-side teardown — firewall rule removed, session file deleted —
  already fired on key removal; this closes the front-end feedback gap.)
- Security/UI only, in the **AI Advisor image** (the standard/noMCP image has no Advisor, so it
  is unaffected).

## v1.4.8a — Bandwidth Limiter on the QoS page + language-selector fixes
- **Bandwidth Limiter moved onto the Reaper QoS page.** Choosing the Bandwidth Limiter mode
  now shows a per-device cap editor (pick a device or enter a MAC, set download/upload in
  Mb/s, enable/disable and remove rows — up to 32 devices) directly on the page instead of
  linking out to the stock editor. The old `QoS_EZQoS.asp` page is removed from the menu and
  any direct or framed hit redirects to the Reaper QoS page.
- **Language selector fixes (from v1.4.8 on-hardware testing):**
  - You can now switch **back to English**, and the dropdown shows the **active** language as
    selected. (ASUS's language list deliberately omits the current language, so it wasn't
    selectable; the current language is now included.)
  - The selector is more visible in the topbar — a globe icon, a crimson-tinted border, and
    brighter text.
- **"Traffic Analyzer" no longer scrolls the side nav sideways.** Five languages shipped that
  menu label as "English + native", which overflowed the rail; it now shows the native
  translation only, and nav labels ellipsize so no language can force a horizontal scrollbar.
- **Removed the red editor link** from the Bandwidth Limiter option (now that the editor lives
  on the page). Localization/UI only. Both images.

## v1.4.8 — Language packs + UI fixes
- **Language packs (i18n).** The five Reaper-native pages (dashboard, Traffic Manager,
  Traffic Analyzer, AI Advisor, and the app shell) were 100% hardcoded English and ignored
  the router's language setting. They are now fully tokenized (`<#...#>` dict entries) like
  every stock ASUS page, so they follow `preferred_lang`. Where a string already had an
  ASUS translation (menus, buttons, modes, common labels — ~70% of the chrome) the existing
  key is reused, so those localize **immediately in all 25 languages**. Reaper-specific
  strings (the QoS/Traffic/Advisor help prose) get new keys carrying English in every
  language for now — a translation drop-in point with no code change needed. 350 new dict
  keys added across all 25 language files, kept in lockstep.
- **Language selector in the Reaper topbar.** Reaper's chrome hid the stock language menu
  and offered no replacement, so the language could not be changed from the UI at all. A
  compact language dropdown now sits in the shell and dashboard topbars (populated with the
  router's compiled languages, localized names), applying the choice the same way the stock
  UI does.
- **Download Master advert removed** from the USB Application page — the advertised
  "PC-free download manager" install tile no longer appears.
- **Network Map USB icon** sizing corrected — the v1.4.7 change reframed the glyph because
  the icon is a sprite sheet; the slice is now scaled to its box so a plugged drive shows
  the clean centered glyph.
- **AiMesh backdrop** stretched to fill the card band so there is no dark gap below the ASUS
  logo and the room selector sits correctly.
- UI/localization only; no change to any underlying feature. Both images.

## v1.4.7 — UI polish + idle auto-logout
- **Idle auto-logout (15 min).** An unattended admin session now logs itself out after
  15 minutes of no activity (mouse/keyboard/touch), in the shell and inside the framed
  page alike. Closes the "walked away from the router page" exposure.
- **Traffic Analyzer** reading line now names the **selected timeframe** (Live / 24 hours /
  14 days / 1 year / By month) instead of always saying "Live".
- **Every page lands at the top** — switching pages in the app shell no longer leaves you
  scrolled down with the tab strip hidden.
- **Network Map USB tile:** the plugged-USB icon is centered in its ring, the disk-quota
  bar is removed, and a long disk name no longer clips.
- **AiMesh:** the backdrop behind the router/node name is now the ASUS logo instead of the
  stock room photo.
- Device/client icons already carry the red-on-black theme across the client-list pages
  (confirmed on hardware). UI/navigation only; no underlying feature change. Both images.

## v1.4.6 — Navigation cleanup: hide superseded and duplicate pages
- **Superseded stock pages are now hidden and redirected.** The stock Traffic Monitor
  and Statistic pages (replaced by the Reaper Traffic Analyzer) and the legacy QoS rule
  editors (replaced by the Reaper QoS page) are removed from the menu; visiting one by
  direct URL now bounces to its Reaper-native replacement instead of showing the dead
  stock page.
- **"Open NAT" removed from navigation.** It is just port forwarding, already covered by
  the Port Forwarding page — removed from the menu and the dashboard rail. The
  port-forwarding feature itself is unchanged and still reachable.
- **QoS page tidy-up.** Removed the "Related Pages" block at the bottom of the QoS panel;
  the one control it still pointed to (the per-device Bandwidth Limiter editor) now
  appears as a link inside the Bandwidth Limiter mode where it belongs.
- Navigation/UI only; no change to any underlying feature. Applies to both images.

## v1.4.5 — Exploit-mitigation build hardening (Reaper daemons)
- Compiles the two Reaper background daemons — the Traffic Analyzer collector
  (`rtrafd`, in both images) and the AI Advisor server (`rmcpd`, AI Advisor image
  only) — with modern exploit mitigations the stock BCM build omits: stack canaries
  (`-fstack-protector-strong`), buffer-overflow checks (`-D_FORTIFY_SOURCE=2`),
  format-string diagnostics (`-Wformat -Wformat-security`), position-independent
  executables (**PIE**), and **full RELRO** (`-Wl,-z,relro,-z,now`). The stock base
  ships neither stack canaries nor full RELRO, so this is a genuine hardening uplift
  for Reaper's own long-running processes.
- Build-only change (two Makefiles); no source or behaviour change. Verified on the
  built binaries: both are now position-independent with read-only relocations and
  stack-protection. Kept as its own release so the mitigation can be validated on
  hardware in isolation.
- Both images (Standard + AI Advisor) receive the `rtrafd` hardening; the AI Advisor
  image additionally hardens `rmcpd`.

## v1.4.4 — Security-review remediation, round 2 (defense-in-depth)
- Clears the remaining LOW / defense-in-depth items from the v1.4.2 code review
  (the HIGH/MEDIUM findings were fixed in v1.4.3). None was a live vulnerability;
  these tighten untrusted-input handling, cleanup, and CSRF posture.
- **Both images (Standard + AI Advisor):**
  - **Traffic Analyzer:** the persistent history database is now written safely on an
    untrusted USB mount — the file is created without following symlinks, is no longer
    world-readable, and the store directory is rejected if it isn't a real directory
    (blocking a planted symlink from redirecting history writes).
  - **Dashboard:** the live CPU/temperature/port tiles no longer evaluate the stock
    status responses as code — they parse them strictly as data, so an unexpected
    response can never execute.
- **AI Advisor image only:**
  - Clearing the arming code or removing the USB second factor now requires the current
    arming code, closing a cross-site-request path that a stale admin session could
    otherwise have ridden to weaken the advisor's setup. (Arming already required the
    code; this extends that to the two remaining state-changing actions.)
  - If the advisor ever exits uncleanly, its LAN firewall rule and session file are now
    swept away on the next boot instead of lingering.
- The Standard (no-AI-Advisor) image receives the Traffic Analyzer and Dashboard fixes
  and a matching version bump; the AI Advisor fixes are absent because that code isn't
  in it.

## v1.4.3 — Security-review remediation
- Fixes from a full multi-agent code review of the newest subsystems (AI Advisor,
  Traffic Analyzer, Hardware QoS, and the web UI). No router-compromise or
  secret-leak path was found; these harden availability and untrusted-input handling.
- **Both images (Standard + AI Advisor):**
  - **Traffic Analyzer:** a crafted history database (on a USB/JFFS store) could cause
    an out-of-bounds write — the on-disk header is now validated and its strings
    treated as untrusted. Per-client attribution no longer rescans the ARP table for
    every connection each second (a LAN device could otherwise spike router CPU); the
    optional latency-probe target is validated more strictly.
  - **Hardware QoS:** both ends of a QoS IP-range rule are now validated, closing a
    path where a malformed rule address could inject an extra firewall rule.
- **AI Advisor image only:**
  - A slow or stalled connection can no longer wedge the advisor and delay its
    self-lockdown — it now enforces a connection timeout, so session-expiry and
    USB-key-removal always take effect promptly.
  - Repeated bad-token attempts can no longer be used by an unauthenticated LAN device
    to shut down your active advisor session.
  - Constant-time token comparison and broader log-redaction as extra hardening.
- The Standard (no-AI-Advisor) image receives the Traffic Analyzer and QoS fixes and a
  matching version bump; the AI Advisor fixes are absent because that code isn't in it.

## v1.4.2 — AI Advisor: TLS via the router's own certificate
- The AI Advisor now serves **HTTPS using the router's own web (httpd) certificate**
  when one is loaded (the same `/etc/cert.pem` the router's web UI uses — **not** a
  separate cert), and falls back to plain HTTP when the router has no certificate.
  The arming page hands you the matching `https://` or `http://` connection URL
  automatically. (If the router's certificate is self-signed, your AI client may need
  to trust it.)
- **Friendly network names:** the advisor's wireless view now reports your real SSIDs
  (from the SDN profiles) instead of the internal onboarding IDs — still security
  *mode* only, never the Wi-Fi password.
- The **Standard (no-AI-Advisor) image was rebuilt to keep the version numbers in
  step** — it contains no AI Advisor code and is otherwise unchanged from v1.4.1.

## v1.4.1 — AI Advisor: optional USB second factor + clean two-build split
- **Mode B (optional USB key)** added to the AI Advisor: an opt-in physical second
  factor *on top of* the arming code. The router writes a generated key to your USB
  stick and stores only its fingerprint; when enrolled, arming also requires the
  stick, and removing it locks the advisor within ~1 second.
- **Two-build split finalized.** A single build flag (`RTCONFIG_REAPER_MCP`) produces
  either a build **with** the AI Advisor or one that **never compiled it in at all**
  (no daemon, no page, no menu, no settings — verified zero-trace), for users who
  want the MCP feature entirely absent.

## v1.4.0 — AI Advisor (optional, read-only LAN MCP server)
- New **optional** subsystem: a read-only [Model Context Protocol](https://modelcontextprotocol.io)
  server (`rmcpd`) that lets your **own** AI client (with your **own** API key) read
  the router's configuration and traffic to **audit and explain** it. It cannot
  change any setting - **yet**.
- Fenced hard to fit the project's threat model: **off by default**, never started at
  boot, **LAN-only**, read-only, secrets redacted, and gated behind a hashed **arming
  code** (a second factor beyond the admin password). Self-terminates on a session
  timeout. No API key is ever stored on the router; nothing is sent to any cloud by
  the router itself.

## v1.3.0 – v1.3.3 — Traffic Analyzer
- New native **Traffic Analyzer** subsystem (`rtrafd` collector + a Reaper-themed
  page): per-device, per-network, and per-QoS-class bandwidth with sub-daily history,
  live top-talkers, an optional monthly-quota warning, and an opt-in WAN latency
  probe. History storage is a required user choice (RAM / JFFS / USB).
- Accuracy reworked to read the Broadcom flow-accelerator's own flow table so
  per-device numbers are correct **with hardware acceleration on** (v1.3.1); endpoint
  and live-view fixes (v1.3.2); and a 1-second dual-cadence live view with a rolling
  chart and a refresh-rate selector (v1.3.3).

## v1.2.8 – v1.2.9 — Hardware QoS v3 and v4
- **QoS v3** (v1.2.8): aggregate rate cap, per-class guaranteed minimums, DSCP trust,
  and live per-class counters, on a native Traffic Manager page.
- **QoS v4** (v1.2.9): per-class weighted round-robin (WRR) weights and an
  experimental L4S (low-latency) flag.

## v1.2.7 — Remove the first-boot cloud-consent surface
- Removed the first-boot **QIS setup wizard's EULA / privacy-consent** screens and the
  Advanced privacy page (kept the AiMesh add-node wizard), and hardened an SNMP token
  path. Continues the de-cloud direction below.

## v1.2.1 – v1.2.6 — UI polish, stability, and code-scan hardening
- Post-login now lands directly on the Reaper dashboard (v1.2.1); a series of GUI
  theming sweeps and metal-tested fixes across VPN, USB, Network Analysis, and the QoS
  classful rule editor (v1.2.2 – v1.2.4); and a Reaper-authored-code security scan +
  performance pass (v1.2.5).

## v1.2 — De-cloud: attack-surface removal (consolidates the v1.1 betas)
- Removed AI-branded, cloud-coupled, and superfluous features to shrink the attack
  surface, consistent with the project's "local-only, no cloud, no fake-AI" direction:
  **Alexa / Google Assistant**, the **Trend Micro DPI engine** (AiProtection / DPI-based
  Adaptive QoS / web history), **AiCloud / WebDAV**, the **AiDisk** cloud-share wizard,
  and the **AAE / AiHome cloud tunnel** — each dropped along with its hooks, with the
  closed blobs left unmodified. Restored the local Speedtest.
- (These shipped incrementally as the `v1.1-beta1…beta5` images and were consolidated
  and released as **v1.2**, dropping the beta label.)

## v1.0 — Initial hardened release
- **Security hardening** of the open-source userspace: four audit rounds plus latent
  buffer hardening and an avahi mDNS CVE backport — the command-injection and
  buffer-overflow classes cleared across the ASUS/Merlin-authored userspace
  (per-finding detail in `REAPER-FIXES.md`).
- **Hardware QoS** — two engines ASUS never shipped: `qos_type=10` (hardware
  rate-shaping + PI2 AQM in the Broadcom Runner **with the flow accelerator left on**)
  and `qos_type=11` **Classful** (per-class priority queues), both validated on metal.
- **Reaper UI** — full matte-black + crimson rebrand and redesign: a live dashboard and
  an app-shell that loads stock settings pages unmodified, applied at serve time from a
  single httpd filter with a runtime kill-switch (`nvram set reaper_inject=0`).
- **Scheduled firmware-availability check** — fixed the dead stock setting and set it
  **default off** (no outbound update traffic unless you opt in; notification only,
  never auto-upgrade).
- Single-model tree: RT-BEXXU only; all sibling BE models stripped.
