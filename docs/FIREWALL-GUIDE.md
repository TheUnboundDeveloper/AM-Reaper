# Reaper Firewall — user guide

This is the reference behind the **?** button on every tab of the Firewall page. Each section below
matches one tab, in the order they appear in the interface.

If you only read one thing: the **Rules**, **Egress** and **Forwards** tabs are the Reaper engine and
they use **commit-confirm** — a change applies immediately but reverts on its own unless you press
Keep before the countdown ends. That is deliberate. It means a mistake that locks you out of the
router undoes itself, so you can experiment from a browser without a serial cable standing by.

The **General**, **Network Services**, **URL Filter** and **Keyword Filter** tabs are the long-standing
Asuswrt firewall controls, re-presented in one place. They apply straight away with no countdown.

**Contents**

[Status](#status) · [General](#general) · [Rules](#rules) · [Objects](#objects) · [Zones](#zones) ·
[Egress](#egress) · [Forwards](#forwards) · [Network Services](#network-services) ·
[URL Filter](#url-filter) · [Keyword Filter](#keyword-filter) · [Logging](#logging)

---

## Status

**What it is.** A read-only picture of what is actually filtering traffic right now: whether the base
firewall and the Reaper engine are up, how many rules, objects and zones are loaded, which content
filters are on, and what of the router is reachable from the internet.

**How to use it.** Treat it as the answer to "is what I think I configured actually live?" — the two
can differ while a restart is in flight, or if a ruleset failed to build. Check it after every Apply,
and again after a reboot. The exposure card is the one worth a slow read: anything listed there can
be reached from the WAN side.

**Example.** You add a port forward, apply it, and the Forwards table shows your rule — but Status
still reports the engine inactive. That means the generated ruleset did not run (most often the LAN
was not up yet at boot). The rule exists in your configuration and does nothing until it does.

---

## General

**What it is.** The base Asuswrt firewall: the master on/off switch, DoS protection, whether the
router answers pings from the internet, which packets get logged, an allow-list of addresses
permitted to reach the router's own services from the WAN, and the separate IPv6 firewall.

**How to use it.** Leave the master switch and DoS protection on. Leave "respond to ping from WAN"
off unless you have a specific reason — answering it confirms the address is live to anyone
scanning. Remember that the IPv6 firewall is genuinely separate: IPv6 traffic is not translated, so
every device on your LAN has a globally routable address and only this switch stands in front of it.

**Example.** To let only your office reach the router's web interface from outside, turn on the WAN
access allow-list and add a single entry — source `203.0.113.10`, port `8443`, TCP. Every other
source is refused, whatever the port forwards say.

---

## Rules

**What it is.** The Reaper rules engine. Each rule names a direction (into the router, through it, or
out of it), an action, an optional source and destination — as zones, objects or both — an optional
service, an optional schedule, an optional rate limit, and whether to log matches.

**How to use it.** Build the pieces first: define your Objects and Zones, then write rules that refer
to them by name. Rules read top to bottom and the first match wins, so put specific exceptions above
broad blocks. Press **Preview** before **Apply** — it shows the exact commands the rule set will run
without running any of them. After Apply, the countdown starts: press **Keep** only once you have
confirmed you can still reach the router.

Within forwarded traffic the order of precedence is: an explicit rule here, then a per-device Egress
default, then the broad Zone policy. So a specific allow beats a device block, which beats a
zone-wide deny.

**Example.** To stop a smart TV reaching the internet during the working day: direction `Forward`,
action `Drop`, source object `tv` (the TV's address), destination zone `wan`, schedule
`Mon,Tue,Wed,Thu,Fri|09:00|17:00`. Leave the service empty so it covers every protocol.

### Allowing only certain destinations, and blocking everything else

This is the most common thing people ask for, and it does not need a "not" or "invert" setting.
**Leaving a source or destination empty means "anything"**, so an allowlist is two rules in the right
order:

| # | direction | action | source | destination | meaning |
|---|---|---|---|---|---|
| 1 | Forward | Accept | `iot-devices` | `vendor-cloud` | the traffic you want to permit |
| 2 | Forward | Drop | `iot-devices` | *(leave empty)* | everything else from those devices |

First match wins, so rule 1 must sit above rule 2. Add more allow rules above the drop as you need
them. The same shape works for a single device, a group, or a whole zone.

Three ways to express "deny by default" exist, and they differ in scope rather than in strength —
pick the narrowest one that covers what you mean:

- **an ordered pair of rules**, as above — best when the exceptions are specific and you want them
  visible next to the block;
- **an Egress default** on the Egress tab — best for "this device gets nothing outbound unless
  listed", because it is anchored to the internet interface and so never cuts the device off from
  the printer or the NAS;
- **a Zone policy** on the Zones tab — best for a broad posture such as "guest may not reach lan".

Because an explicit rule beats an Egress default, which beats a Zone policy, you can set a strict
default at the bottom layer and open specific holes at the top without editing the default again.

**Worth knowing.**

- Rate limiting needs a kernel module that is not always present. If it is missing, rules that use a
  rate limit are skipped rather than silently applied without the limit, and a line saying so is
  written to the system log.
- **An empty source or destination means "anything". A named object that currently resolves to
  nothing is not the same thing** — that rule is left out entirely rather than becoming a rule that
  matches everything. A domain object that has not resolved yet, or an emptied group, therefore
  fails to a missing rule, never to an unintended block.

---

## Objects

**What it is.** Named things you can point rules at, so you write `printer` instead of an address you
have to remember. Three kinds live here: address objects (a host or subnet, an address range, a MAC
address, a domain name, or a country), address groups that bundle several objects under one name,
and service objects that name a protocol and a set of ports.

**How to use it.** Name objects after what they are, not where they are — `printer`, `kids-tablet`,
`nas` — so a rule still reads correctly after you renumber your network. Edit the object when a
device moves and every rule using it follows automatically. Use a group when the same set of devices
keeps appearing in rules.

**Example.** Create an address object `nas` of type host with value `192.168.50.20`, and a service
object `smb` with protocol TCP and ports `139,445`. A rule blocking `smb` to `nas` from your guest
zone then reads as plain English and needs no comment.

**Worth knowing.**

- **Domain-name objects** fill in as the router resolves the name, and entries expire after about an
  hour so a rotating content network does not accumulate stale addresses forever. They only see
  lookups the router's own resolver answers — a device using its own DNS server, or encrypted DNS,
  is invisible to them. A background refresh every ten minutes covers the common case.
- **A long list pastes in one go.** Domain and address lists take one entry per line or
  comma-separated, and the editor normalises the whitespace and line endings for you, so a
  forty-domain object goes in as a single paste rather than a few entries at a time. If something in
  the paste cannot be accepted the editor says so and keeps saying so — it never silently drops the
  remainder. These lists live on the router's internal flash (`/jffs`), not in nvram, which is what
  lifted the old size ceiling.
- **MAC objects** only work as a *source* on traffic into or through the router. A MAC address does
  not survive being routed, so it cannot be used as a destination or on outbound traffic.
- **Country objects** are owned by Warden, not by this engine — set them up on the Warden page.

---

## Zones

**What it is.** A zone is a name for a set of interfaces — `lan` for your bridge, `wan` for the
internet, `vpn` for tunnel interfaces. A zone policy then says what happens by default when traffic
moves from one zone to another.

**How to use it.** Zones let you write intent once instead of repeating interface names in every
rule. Start with the broad policy — for example guest to LAN denied — and then write specific Rules
for the exceptions you actually want. Interface names accept a trailing `+` as a wildcard, so `tun+`
covers every tunnel interface without listing them.

**Example.** Define a zone `guest` with interface `br1`, and a zone `lan` with `br0`. Add a zone
policy: source `guest`, destination `lan`, action `Drop`. Guests can now reach the internet but
nothing on your home network — and you have not written a single address anywhere.

**Worth knowing.** A zone policy is the weakest statement in the engine; both explicit Rules and
Egress defaults override it. That is what makes "deny everything, then allow what I need" workable.

---

## Egress

**What it is.** A per-device default for traffic leaving your network toward the internet. Pick an
address object, pick what should happen to its outbound traffic, and optionally limit it to a
schedule.

**How to use it.** This is the short path for "this device should not be on the internet" without
writing a full rule. It sits between explicit Rules and Zone policy in precedence, so you can set a
device to Drop here and still allow one specific thing through with a Rule above it.

Prefer `Reject` over `Drop` for devices someone is sitting at: reject sends a refusal and the
application fails immediately, while drop leaves it hanging until it times out. Use `Drop` for
devices nobody is watching, which reveals less.

**Example.** Object `kids-tablet`, action `Reject`, schedule `Sun,Mon,Tue,Wed,Thu 21:00-07:00`. The
tablet keeps working on the local network overnight — it can still reach the printer and a media
server — but it cannot reach the internet, and it says so instead of hanging.

---

## Forwards

**What it is.** Port forwarding: traffic arriving at the router from the internet on a chosen port is
sent to a device inside your network. You can restrict which outside addresses are allowed to use
the forward, and put it on a schedule. This tab also holds Export and Import for backing up the whole
firewall configuration as text.

**How to use it.** A port forward is a hole in the firewall by definition, so make it as small as it
can be. Restrict the source whenever you know who will connect. Use a non-obvious external port —
forwarding external `8443` to internal `443` will not stop a determined attacker but removes you from
the results of everyone scanning the standard port. Give the target device a fixed address first, or
the forward will eventually point at whatever picked up that address.

Export before you make a large change. The result is plain text you can paste back to restore.

**Example.** To reach a home server's web interface: protocol TCP, external port `8443`, internal
address `192.168.50.80`, internal port `443`, source restricted to an object holding your office
address. Everyone else scanning port 8443 finds nothing.

**Worth knowing.** Forwards bypass your Zone policy by design — that is what a forward is. If you
want traffic to reach the device but not the rest of the network, put the device in its own zone.

---

## Network Services

**What it is.** The long-standing Asuswrt service filter. It matches traffic leaving your LAN by
source address, destination address, port and protocol, and either blocks the listed traffic or
permits only the listed traffic, within a daily time window.

**How to use it.** Choose the mode deliberately. Block-list blocks what you list and allows the rest.
Allow-list allows only what you list and blocks everything else — which is far stricter, and will cut
off things you forgot, so add DNS and the rest of your essentials before you switch it on.

The time window applies to the whole list, not per entry. If you need per-device or per-rule
scheduling, use the Rules or Egress tabs instead.

**Example.** To stop devices using outside DNS servers and force them through the router: mode
Block-list, source blank (meaning every device), destination blank, destination port `53`, protocol
UDP. Add a second entry for TCP. The router's own resolver still works because that traffic never
leaves the LAN.

**Worth knowing.** This filter needs the router's clock to be correct for the time window to mean
anything. If time has not synchronised yet, the page says so.

---

## URL Filter

**What it is.** Blocks web requests whose address contains one of the keywords you list.

**How to use it.** Keep the entries short and distinctive — a fragment of the domain rather than a
full address, because the same site is reached by many different URLs. Test with one entry before
adding a long list.

Be realistic about the limits. This matches the request as it goes past, so it works on plain,
unencrypted requests and misses almost everything on the modern web, which is encrypted. Treat it as
a nudge for casual use, not a control. For blocking that holds, use a domain-name Object in a Rule,
or block at the DNS level.

**Example.** Entry `example-game.com`. Plain requests to that domain are refused; the same site over
HTTPS is not, which is why this tab is the weakest of the blocking options here.

---

## Keyword Filter

**What it is.** Blocks web pages whose content contains one of the words you list.

**How to use it.** The same realism applies, more so: the filter has to be able to read the page to
match a word in it, so encrypted sites pass untouched. It also matches inside ordinary text, so a
short or common word will block pages you did not intend — prefer distinctive phrases, and add them
one at a time.

**Example.** Entry `freegamedownload`. A plain page containing that string is blocked. A page that is
encrypted, or that spells it differently, is not.

---

## Logging

**What it is.** Chooses which firewall decisions get written to the system log — nothing, dropped
packets, accepted packets, or both — and shows the recent entries.

**How to use it.** Leave it off for normal running. A busy connection can log thousands of lines a
minute, which fills the log and pushes out everything else you might have wanted to read.

Turn on **Drop** while you are diagnosing a rule that is not doing what you expect, look at the
entries, then turn it back off. **Accept** and **Both** are for short, deliberate investigations only.

**Example.** A device cannot reach a service and you do not know which rule is stopping it. Set
logging to Drop, reproduce the failure, and read the entries — each logged line names the addresses
and ports, which tells you which of your rules matched.
