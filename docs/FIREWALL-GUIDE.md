# Reaper Firewall — user guide

> **Doc status:** current as of **v3.1.1** · 2026-09-06 <!--@stamp-->

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

Moved → **[4.1.9 Network Services](REAPER-GUIDE.md#419-network-services)**

## URL Filter

Moved → **[4.1.10 URL Filter](REAPER-GUIDE.md#4110-url-filter)**

## Keyword Filter

Moved → **[4.1.11 Keyword Filter](REAPER-GUIDE.md#4111-keyword-filter)**

## Logging

Moved → **[4.1.12 Logging](REAPER-GUIDE.md#4112-logging)**

---

*Maintainers: do not add content here. Since v3.1.1 the **?** buttons link `REAPER-GUIDE.md`
directly; this file exists only for the buttons of images before that, and can be deleted once
v2.8.8 and the v3.1.0 beta are out of circulation.*
