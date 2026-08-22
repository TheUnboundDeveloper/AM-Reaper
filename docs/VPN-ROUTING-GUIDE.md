# Reaper Policy Routing — user guide

This is the reference behind the **?** button on the **Policy Routing** page (VPN menu, next to VPN
Director).

If you only read one thing: **Policy Routing decides *which traffic* uses *which path* — a VPN
tunnel, the plain internet connection, or nowhere at all — by a rule you write.** It is the piece
Merlin's VPN Director was missing. VPN Director can only pick traffic by a source or destination
**address**; Policy Routing adds the ability to pick traffic by a named **Firewall object** (a whole
list of sites or domains under one name), or by a **device**, and send it to an OpenVPN client, out
the WAN, or to a block.

It is **off by default**, and turning it on changes nothing until you add a rule.

**Contents**

[How it works](#how-it-works) · [The page](#the-page) · [What a rule matches](#what-a-rule-matches) ·
[Where a rule sends traffic](#where-a-rule-sends-traffic) · [Order and precedence](#order-and-precedence) ·
[Fail-closed](#fail-closed) · [Examples](#examples) · [Worth knowing](#worth-knowing)

---

## How it works

A Policy Routing rule has two halves: **what to match**, and **where to send it**. When traffic
matches, the router marks it and steers it through the routing table for the target you chose — a VPN
client's table, the normal WAN table, or a dead end.

It is built entirely from mechanisms already in the firmware — a firewall mark plus a routing-policy
rule — so it adds no new moving parts and reuses the routing tables your OpenVPN clients already set
up. Nothing here dials a tunnel or changes a VPN's own settings; it only decides what rides through
one that is already connected.

**Policy Routing and VPN Director are meant to sit side by side.** Use VPN Director for the broad
posture ("send everything through the tunnel", or "send this subnet through the tunnel"), and use
Policy Routing for the exceptions that need an object or a device — because a Policy Routing rule
**wins** over a VPN Director rule for the same traffic. That is what lets you say "tunnel everything,
*except* send this one streaming service straight out the WAN."

---

## The page

**The master switch** turns the whole engine on or off. With it off, no marks and no routing rules
are placed, whatever is in the table.

**The rule table** lists your rules in order, with the match on the left and the target on the right,
each with its own enable checkbox so you can park a rule without deleting it.

**The add-rule form** builds one rule: pick the selector type, fill in its value, choose the target,
and add it. Every row also has **Modify**: it loads the rule back into the form, the Add button
becomes Save, and saving replaces the rule in place. **Apply and confirm** puts the whole list into
effect at once and starts the same auto-revert countdown the Firewall Rules tab uses (the timer is
set on the Firewall page): press **Keep** to make it permanent, or let it expire / press **Revert**
and the previous rules come back on their own — the router owns that deadline, so closing the tab
does not cancel it. Keep is the only thing that writes flash. A source rule may name **a list of
addresses** (IPv4/IPv6, one per line or comma-separated, up to 64).

**The Domain lists card** is where you build and maintain the lists the rules point at — see
[Domain lists](#domain-lists) below. You no longer have to go to the Firewall page for this.

---

## What a rule matches

Each rule matches traffic one of three ways:

- **Domain list / object (destination)** — a named list of domains built on this page, or any
  Firewall address object or group, chosen from the dropdown. The rule matches traffic whose
  **destination** is in that list. This is the powerful one: name a set of streaming sites, or a
  country, and route everything headed *to* it in one rule. Domain lists fill in as the router
  resolves the names (see below).
- **Device by IP / CIDR (source)** — a single address or a range on your LAN. The rule matches
  traffic **from** it.
- **Device by MAC (source)** — a device's hardware address. The rule matches traffic **from** that
  device, wherever it picked up its IP.

### "VPN Director already routes by source IP — what do the device rules add?"

A fair question; VPN Director's source rule and a device rule here do steer the same packets. The
device rules exist for what they add on top:

- **Fail-closed.** If the tunnel drops, a device routed here is **blocked** until it comes back. VPN
  Director's rule would quietly fall through to the WAN unless you also enabled its kill switch.
- **Block as a target.** "This device goes nowhere" without a firewall rule.
- **MAC keying.** A MAC rule follows the device across DHCP changes; an IP rule does not.
- **Precedence.** A rule here **overrides** a VPN Director rule for the same device, so you can carve
  one device out of a broad "route this subnet" policy.

If none of those matter to you, VPN Director alone is fine — use whichever you find clearer.

---

## Domain lists

A domain list is a Firewall object of type *Domain name*: a name plus the domains it covers. The
card on this page lets you **add, modify and delete** them without leaving Policy Routing; the
Firewall page sees the same lists, so nothing is duplicated.

- **Entering domains.** The box takes one domain per line, or a comma- or space-separated paste from
  a text file. Blank lines and duplicates are dropped, everything is lower-cased, and each name is
  checked before it is saved. A list can hold as many domains as fit in about 1,900 characters — if a
  service needs more, split it into two lists and two rules.
- **How a list becomes addresses.** Two mechanisms feed it: every DNS answer the router's own
  resolver gives for a listed name lands in the list immediately, and a timer re-resolves every name
  **every 10 minutes** as a floor (for clients that use their own DNS, names already cached, and
  the cold start after a reboot). Addresses expire an hour after they were last seen, so a CDN that
  rotates its pool prunes itself.
- **Across reboots.** After every timer pass the lists are **saved to the router's flash** and
  restored the moment they are re-created at boot, so a rule is not blind until the first lookup.
- **CDNs change.** When a service starts reaching out to a domain you did not list, the traffic is
  not matched. That is the one piece no timer can fix for you — come back and **Modify** the list.
  (Keeping lists here, next to the rules that use them, is the point of this card.)
- **The Firewall engine does not need to be on.** The lists are built whenever Policy Routing is
  enabled, engine or no engine. If the Firewall engine *is* on and you edit a list here, the routing
  side uses the new list on Apply; the Firewall's own rules pick it up on the Firewall page's Apply,
  as its commit-and-confirm flow requires.

---

## Where a rule sends traffic

Every rule has one target:

- **A VPN client (OpenVPN 1–5)** — matched traffic goes through that OpenVPN client's tunnel, using
  the routing table the client already created. The tunnel does not have to be the default route;
  this steers only the traffic you named through it.
- **WAN** — matched traffic is forced out the normal internet connection, **bypassing** a full-tunnel
  VPN. This is how you carve an exception out of "route everything through the tunnel".
- **Block** — matched traffic is dropped. Useful as a hard "this device / this destination goes
  nowhere" that does not depend on the firewall rule order.

- **WireGuard 1–5** — supported since v2.6.7. The router's hardware accelerator does not honour a
  routing rule whose exit is a WireGuard tunnel, so Reaper does what VPN Director does and tells the
  accelerator to leave the affected flows alone: a **source** rule excludes just those addresses; a
  **destination-list or MAC** rule has to exclude the whole LAN, which costs hardware acceleration for
  LAN traffic while such a rule exists. The rule's chip says which applies, and the log says so on
  every apply. A WireGuard rule whose client is switched off is fail-closed: it blocks the selected
  traffic until that client comes up.

**IPv6 is covered** (v2.6.7): a destination list matches its IPv6 addresses, a MAC rule follows the
device on both families, and a source rule may name an IPv6 prefix. If the chosen tunnel carries no
IPv6, the selected IPv6 traffic is blocked rather than leaked around the tunnel.

---

## Order and precedence

Rules read **top to bottom, first match wins** — put specific rules above broad ones. A device that
should mostly use a tunnel but reach one site directly needs the "reach this site directly" rule
*above* the "send this device to the tunnel" rule.

Between features, **a Policy Routing rule takes precedence over a VPN Director rule** covering the
same traffic. So you do not have to unpick VPN Director to make an exception — you add the exception
here and it wins.

---

## Fail-closed

A rule that targets a VPN client **fails closed**: if that tunnel is **down**, the matched traffic is
**blocked, not sent out the WAN.** This is deliberate and it is the safety property that matters most
in a routing feature. The whole point of sending a device or a site through a VPN is usually that it
must *not* touch the internet directly — so if the tunnel drops, leaking that traffic to the WAN
would be the one failure you were trying to prevent. Instead it stops until the tunnel is back.

If you actually want "use the tunnel when it's up, otherwise go direct," that is a **WAN** rule, not a
VPN-client rule — state it explicitly rather than relying on a failure.

---

## Examples

**Send a set of streaming sites through a VPN, leave everything else direct.**
On **Firewall → Objects**, make a domain object `streaming` listing the services' domains. Here: add
a rule, selector **Object** = `streaming`, target **OpenVPN 1**. Only traffic to those domains uses
the tunnel; the rest of the house is untouched.

**Tunnel the whole house, but send one service straight out the WAN.**
Set VPN Director (or a broad rule) to route everything through the tunnel. Then here: selector
**Object** = `work-app` (a domain object for the service that dislikes the VPN's exit address),
target **WAN**. Because Policy Routing wins over VPN Director, that one service goes direct and
everything else stays tunnelled.

**Force one device down a VPN, and nowhere else if it drops.**
Selector **Source MAC** = the device's address, target **OpenVPN 2**. If OVPN 2 is connected the
device uses it; if OVPN 2 goes down the device has no internet (fail-closed) rather than quietly
falling back to your real address.

**Send a device — or a destination — nowhere at all.**
Selector **Source IP** (or **Object**), target **Block**. A hard stop that does not depend on where
it sits in the firewall's own rule order.

---

## Worth knowing

- **It is off until you turn it on, and adding a rule is what makes it do anything.** The master
  switch alone places nothing.
- **Objects are shared with the Firewall.** Domain lists are edited here or on **Firewall →
  Objects** — they are the same objects. Address, MAC and country objects are still created on the
  Firewall page and simply show up in the dropdown. A list that has not resolved yet, or an emptied
  group, produces no rule rather than a rule that matches everything — the same fail-to-nothing
  behaviour the firewall uses.
- **Apply and confirm.** Rules go live at once and revert on their own unless you press Keep within
  the timer — the same protection the Firewall Rules tab has. It is still worth adding rules from a
  device that is **not** itself being routed by the rule you are testing.
- **WireGuard costs acceleration** for the flows it must bypass — see the target list above. Prefer a
  source rule (one address excluded) over a destination-list rule (whole LAN excluded) when you can.
- **Rules live on the router's internal flash** (`/jffs`), not in the stock settings backup: use
  *Reaper settings backup* on the Storage page.
- **To check what actually loaded**, the rules appear as routing-policy entries and a marking chain on
  the router; if something is not behaving, the system log names any rule that was skipped and why.
