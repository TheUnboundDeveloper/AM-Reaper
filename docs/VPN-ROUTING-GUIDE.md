# Reaper Policy Routing — user guide

> **Doc status:** current as of **v2.8.6** · 2026-08-28 <!--@stamp-->

> **This guide has moved.** Every section below now lives in
> **[`REAPER-GUIDE.md`](REAPER-GUIDE.md)**, the single Reaper manual, under
> **[4.4 Policy Routing](REAPER-GUIDE.md#44-policy-routing)**. It is the same material, kept current
> in one place instead of two.
>
> This file remains so that the **?** buttons on the Policy Routing page of already-installed
> routers keep working. Each heading below preserves its original link target and points at the new
> location. Nothing here is maintained — follow the link.

**Jump straight to the full section:** [REAPER-GUIDE.md § 4.4](REAPER-GUIDE.md#44-policy-routing)

Policy Routing in brief, so this page is not useless on its own: it decides **which traffic uses
which path** — an OpenVPN or WireGuard client, the plain WAN, or nowhere — by a rule you write. It
is the piece VPN Director was missing, because it can match a named **object or domain list** or a
**device**, not only an address. A Policy Routing rule **wins** over a VPN Director rule for the
same traffic. A rule targeting a VPN client is **fail-closed**: if the tunnel drops the traffic is
blocked, never leaked to the WAN. It is off by default, and turning it on changes nothing until you
add a rule.

---

## How it works

Moved → **[4.4.1 How it works](REAPER-GUIDE.md#441-how-it-works)**

## The page

Moved → **[4.4.2 The page](REAPER-GUIDE.md#442-the-page)**

## What a rule matches

Moved → **[4.4.3 What a rule matches](REAPER-GUIDE.md#443-what-a-rule-matches)**

## Domain lists

Moved → **[4.4.4 Domain lists](REAPER-GUIDE.md#444-domain-lists)**

## Where a rule sends traffic

Moved → **[4.4.5 Where a rule sends traffic](REAPER-GUIDE.md#445-where-a-rule-sends-traffic)**

## Order and precedence

Moved → **[4.4.6 Order and precedence](REAPER-GUIDE.md#446-order-and-precedence)**

## Fail-closed

Moved → **[4.4.7 Fail-closed](REAPER-GUIDE.md#447-fail-closed)**

## Examples

Moved → **[4.4.8 Examples](REAPER-GUIDE.md#448-examples)**

## Worth knowing

Moved → **[4.4.9 Limits and gotchas](REAPER-GUIDE.md#449-limits-and-gotchas)**

---

*Maintainers: do not add content here. This file exists only to keep the deep links in shipped
firmware resolving. When a firmware release ships whose **?** buttons point directly at
`REAPER-GUIDE.md`, and enough time has passed that older images are out of circulation, this file
can be deleted.*
