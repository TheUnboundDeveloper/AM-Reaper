# Reaper Firewall — user guide

> **Doc status:** current as of **v2.8.6** · 2026-08-28 <!--@stamp-->

> **This guide has moved.** Every section below now lives in
> **[`REAPER-GUIDE.md`](REAPER-GUIDE.md)**, the single Reaper manual, under
> **[4.1 Firewall](REAPER-GUIDE.md#41-firewall)**. It is the same material, kept current in one
> place instead of two.
>
> This file remains so that the **?** buttons on firewall pages of already-installed routers keep
> working. Each heading below preserves its original link target and points at the new location.
> Nothing here is maintained — follow the link.

**Jump straight to the full firewall section:** [REAPER-GUIDE.md § 4.1](REAPER-GUIDE.md#41-firewall)

The firewall in brief, so this page is not useless on its own: **Rules**, **Egress** and
**Forwards** use commit-confirm — a change applies at once but reverts unless you press Keep before
the countdown ends, so a mistake that locks you out undoes itself. **General**, **Network
Services**, **URL Filter** and **Keyword Filter** are the stock Asuswrt controls and apply
immediately. Precedence within forwarded traffic is **explicit rule > Egress default > Zone
policy**.

---

## Status

Moved → **[4.1.1 Status](REAPER-GUIDE.md#411-status)**

## General

Moved → **[4.1.2 General](REAPER-GUIDE.md#412-general)**

## Rules

Moved → **[4.1.3 Rules](REAPER-GUIDE.md#413-rules)**

### Allowing only certain destinations, and blocking everything else

Moved → **[the allowlist recipe](REAPER-GUIDE.md#allowing-only-certain-destinations-and-blocking-everything-else)**

## Objects

Moved → **[4.1.4 Objects](REAPER-GUIDE.md#414-objects)**

## Zones

Moved → **[4.1.5 Zones](REAPER-GUIDE.md#415-zones)**

## Egress

Moved → **[4.1.6 Egress](REAPER-GUIDE.md#416-egress)**

## Forwards

Moved → **[4.1.7 Forwards](REAPER-GUIDE.md#417-forwards)**

## Network Services

Moved → **[4.1.8 Network Services](REAPER-GUIDE.md#418-network-services)**

## URL Filter

Moved → **[4.1.9 URL Filter](REAPER-GUIDE.md#419-url-filter)**

## Keyword Filter

Moved → **[4.1.10 Keyword Filter](REAPER-GUIDE.md#4110-keyword-filter)**

## Logging

Moved → **[4.1.11 Logging](REAPER-GUIDE.md#4111-logging)**

---

*Maintainers: do not add content here. This file exists only to keep the deep links in shipped
firmware resolving. When a firmware release ships whose **?** buttons point directly at
`REAPER-GUIDE.md`, and enough time has passed that older images are out of circulation, this file
can be deleted.*
