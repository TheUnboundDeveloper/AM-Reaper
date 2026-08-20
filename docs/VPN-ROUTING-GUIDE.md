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
and add it. **Apply** writes the whole list to the router and puts it into effect immediately. There
is no countdown here (unlike the Firewall Rules tab) — see [Fail-closed](#fail-closed) for why the
risky direction is defended a different way, and [Worth knowing](#worth-knowing) for the honest limit
of that.

---

## What a rule matches

Each rule matches traffic one of three ways:

- **Object** — a **Firewall address or domain object**, chosen from the dropdown. The rule matches
  traffic whose **destination** is in that object. This is the powerful one: build an object on the
  **Firewall → Objects** tab that holds a list of domains or addresses (for example a group of
  streaming sites, or a country), name it, and route everything headed *to* that list in one rule.
  Domain objects fill in as the router resolves the names, exactly as they do in firewall rules.
- **Source IP** — a single address or a range on your LAN. The rule matches traffic **from** it.
- **Source MAC** — a device's hardware address. The rule matches traffic **from** that device,
  wherever it picked up its IP.

You build objects on the Firewall page, not here — this page only *refers* to them by name, so the
same object can drive both a firewall rule and a routing rule and stays in one place when a device or
a site's addresses change.

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

**WireGuard clients are not offered as a target yet.** The router's hardware accelerator forwards
WireGuard traffic in a way that bypasses the routing rule this feature relies on, so a WireGuard
target would silently not work — and silently-not-working is worse than absent. A rule that names a
WireGuard client is skipped and a line saying so is written to the system log, rather than pretending
to route it. OpenVPN, WAN and Block work today; WireGuard is deferred until the accelerator side is
handled properly.

This first version is **IPv4 only.**

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
- **Objects are shared with the Firewall.** Create and edit them on **Firewall → Objects**; this page
  only points at them. A domain object that has not resolved yet, or an emptied group, produces no
  rule rather than a rule that matches everything — the same fail-to-nothing behaviour the firewall
  uses.
- **No commit-confirm countdown here.** The Firewall's Rules tab reverts on its own unless you press
  Keep, because a bad firewall rule can lock you out of the router. Policy Routing does not carry that
  countdown in this version: the engine stays inert until enabled, and a malformed rule is dropped and
  logged rather than applied. It is still worth adding rules from a device that is **not** itself
  being routed by the rule you are testing, so a mistake cannot cut off the browser you are using.
- **WireGuard targets are not available yet** — see above; a WireGuard rule is skipped and logged,
  never silently ignored.
- **IPv4 only** in this version.
- **To check what actually loaded**, the rules appear as routing-policy entries and a marking chain on
  the router; if something is not behaving, the system log names any rule that was skipped and why.
