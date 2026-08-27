# Reaper Firmware — Installation & Rollback Guide

> **Doc status:** current as of **v2.7.9** · 2026-08-26 <!--@stamp-->

**Applies to:** Reaper (Asuswrt‑Merlin 3006.102.8 fork), current release **v2.7.8** <!--@pubver--> (`3006.102.8_Reaper_v2.7.6`) — the newest **published** release, available for all five main models (and the RT-BE92U as an experimental prerelease) on [Releases](https://github.com/TheUnboundDeveloper/AM-Reaper/releases) — for the **ASUS RT‑BEXXU** (Broadcom BCM4916, WiFi 7). This guide is written for the RT‑BEXXU specifically; Reaper also ships for the sibling BCM4916 models **RT‑BE86U**, **RT‑BE88U**, **GT‑BE98**, and **GT‑BE98 Pro**, and the newer BCM6765 **RT‑BE92U** (experimental prereleases), and the **same flash and rollback procedure below applies to each — using that model's own image**.
**Status:** DRAFT — user‑facing. Items marked **⚠ VERIFY ON UNIT** are based on general ASUS/Merlin behaviour and should be bench‑confirmed on an actual RT‑BEXXU before this ships publicly.

> **Read first — flash only the image built for your exact model.** These instructions cover the RT‑BEXXU; if you have a sibling model (RT‑BE86U / RT‑BE88U / GT‑BE98 / GT‑BE98 Pro / RT‑BE92U) follow the same steps with that model's image. Flashing an image built for a different model/SoC can brick the router. Do **not** cross‑flash between models. Always keep a stock ASUS firmware file **for your exact model** on hand before you begin (your rollback/rescue image).

---

## 1. What you’re flashing

Reaper ships two build variants, each with a matching recovery loader:

| File | What it is |
|------|-----------|
| `RT-BEXXU_3006_102.8_<EXTENDNO>_nand_squashfs.pkgtb` | **The firmware you flash** (normal install). |
| `RT-BEXXU_..._noMCP_...pkgtb` | Same firmware **without** the AI Advisor / MCP server compiled in (choose this if you don’t want the MCP feature present at all). |
| `..._loader.pkgtb` | **Recovery loader only** — used in Rescue Mode, *not* a normal firmware. Don’t flash this from the Web UI as your firmware. |

- Output format is **`.pkgtb`** (BCM NAND), not `.trx`.
- Confirm the file’s SHA‑256 against the published checksum before flashing. A truncated/corrupt image is a common cause of a failed flash.
- Pick **one** variant (standard *or* noMCP). The MCP server in the standard build is **off until you explicitly arm it** — it is never started at boot — so the standard build is safe to run without ever enabling MCP.

> **v1.5.0a note:** the bundled **Packet Capture (tcpdump)** page has been **removed** — the firmware ships no packet-capture tool. Power users who want capture can install `tcpdump` on a USB stick via Entware (`opkg install tcpdump`). This keeps the image free of that dependency and its attack surface.

---

## 2. Pre‑flight checklist (do this every time)

1. **Back up your current config.** Web UI → *Administration → Restore/Save/Upload Setting* → **Save**. Store the `.cfg` off the router.
2. **Download a stock ASUS RT‑BEXXU firmware** from ASUS support and keep it with the Reaper image. This is your rollback and your rescue image. ⚠ VERIFY ON UNIT: confirm it’s the exact RT‑BEXXU file.
3. **Be on a recent stock firmware first.** If you’re far behind, update to a recent official ASUS RT‑BEXXU firmware *before* flashing Reaper. This avoids nvram/bootloader‑format mismatches. ⚠ VERIFY ON UNIT: whether the BEXXU enforces any minimum‑version / anti‑rollback gate.
4. **Use a wired connection** (Ethernet from PC to a LAN port). Never flash over Wi‑Fi.
5. **Uninterruptible power.** Do not lose power mid‑flash — a firmware flash is recoverable, an interrupted **bootloader** write generally is not.
6. **Note your access details** (admin password, LAN IP). Plan to factory‑reset after flashing (below), which clears them.

---

## 3. Install — normal path (Web UI)

1. Log into the router (default LAN IP is typically `192.168.1.1`; **⚠ VERIFY ON UNIT**).
2. Go to **Administration → Firmware Upgrade**.
3. **Manual firmware upload** → select `RT-BEXXU_..._nand_squashfs.pkgtb` (the standard or noMCP firmware, **not** the `_loader`).
4. Upload and let it flash. **Do not touch power.** The router writes the image and reboots on its own (this can take several minutes).
5. Wait for it to come back up (power LED solid). If the UI doesn’t load, give it another minute and hard‑refresh.

### Strongly recommended after a major version change: reset to defaults
A cross‑major upgrade can leave stale nvram. To avoid odd behaviour:

1. After the first successful boot, go to **Administration → Restore/Save/Upload Setting → Factory default** (or hold the physical **Reset** button per §5). Choose the option that **also formats JFFS** if offered. ⚠ VERIFY ON UNIT: exact wording/behaviour of the “initialize/format JFFS” option on the BEXXU.
2. Reconfigure from scratch (don’t restore the old `.cfg` across a major version if you can avoid it — re‑enter settings, or restore only if the versions are close).

### Verify the install
- **Administration → System / firmware version** shows the Reaper build.
- **System Info → Features** row reflects the Reaper package set (traffic analyzer, classful HW‑QoS, MCP if standard build, etc.).
- Internet + Wi‑Fi work.

---

## 4. Install — Rescue Mode (CFE / TFTP) path

Use this if the Web‑UI flash fails, or the router won’t boot normally. This is also the **un‑brick** path (§5).

1. Set your PC to a **static IP** on the router’s rescue subnet — commonly `192.168.1.10 / 255.255.255.0`, gateway `192.168.1.1`. ⚠ VERIFY ON UNIT.
2. Power the router **off**.
3. **Enter Rescue Mode:** hold the **Reset** button (some ASUS models use **WPS** — ⚠ VERIFY ON UNIT which one the BEXXU uses) while powering **on**, and keep holding until the **power LED blinks slowly** (indicating rescue/recovery mode). Release.
4. Push the firmware using the **ASUS Firmware Restoration utility** (Windows/macOS tool from ASUS support) pointed at `192.168.1.1`, **or** a manual `tftp` PUT of the `.pkgtb` to `192.168.1.1`. Use the recovery `_loader` image if the utility requires the loader; otherwise the standard firmware. ⚠ VERIFY ON UNIT which image the BEXXU’s recovery flow expects.
5. Wait for the write to complete and the router to reboot. Do not interrupt power.
6. Set your PC’s network back to DHCP and log in.

---

## 5. Rollback to stock ASUS firmware

Rolling back is the same operation as installing, using the **stock ASUS RT‑BEXXU** image instead of Reaper:

- **Easiest:** Web UI → **Administration → Firmware Upgrade** → upload the **stock ASUS `.pkgtb`** → reboot → then **factory‑reset / format JFFS** (§2) so no Reaper nvram remains.
- **If the UI is unavailable:** use **Rescue Mode** (§3) to push the stock image.
- After rolling back, do a **factory reset** and reconfigure. ⚠ VERIFY ON UNIT: whether the BEXXU enforces an anti‑rollback / minimum‑version gate that could block a downgrade to an older stock build (if so, roll back to a stock build at or above your current version).

There is **no cloud/account tie‑in** to undo — Reaper is de‑clouded, so rollback is purely a firmware re‑flash.

---

## 6. Recovery / un‑brick — and what actually bricks

**Physical Reset button (factory reset):** with the router on, hold **Reset** ~10 s until the power LED flashes, then release; it reboots to defaults. ⚠ VERIFY ON UNIT: exact hold time / LED behaviour on the BEXXU.

**If it won’t boot at all → Rescue Mode (§3).** On ASUS routers the **bootloader (CFE/U‑Boot) is a separate region that a normal firmware flash does not overwrite**, so a bad *firmware* flash almost always recovers via Rescue Mode + a known‑good image.

**Brick taxonomy — set expectations honestly:**
- **Bad firmware image / interrupted firmware write → recoverable** via Rescue Mode. This is the common, fixable case.
- **Corrupted bootloader (CFE) → hard brick**, generally requiring serial/JTAG. This is why you never interrupt power and never flash a wrong‑model image.
- **⚠ Do not assume automatic dual‑partition rollback.** ASUS consumer routers historically do not expose Netgear‑style automatic A/B failover; the reliable safety net is **Rescue Mode + your saved stock image**, not an assumed auto‑rollback. ⚠ VERIFY ON UNIT: whether the BEXXU keeps a usable second image.

**Golden rules:** keep a stock image staged · flash wired · never cut power mid‑flash · never cross‑flash another model.

---

## 7. This‑version security notes for installers

- **MCP / AI Advisor (standard build):** off by default and **never started at boot**. It only runs after you explicitly *arm* it (with an arming code, optionally a USB key), binds to the LAN only, and pins the client. If you don’t want it present at all, install the **noMCP** variant.
- **MCP diagnostics tier:** even after arming, the active network‑diagnostics tools (ping/traceroute/DNS/netstat) stay **off until you separately opt in per session**. Leave that opt‑in off unless you’re actively using it.
- **De‑clouded by design:** no AiCloud, no AiMesh cloud, no TrendMicro/bwdpi, no ASUS account, no phone‑home. This removes several known ASUS cloud vulnerability classes outright.
- **Keep WAN management off.** Do not enable remote/WAN administration or WAN SSH. The biggest real‑world ASUS threats target the internet‑facing management surface; keeping admin LAN‑only is your best protection.
- **Wi‑Fi chipset advisory (not fixable in firmware):** the BCM4916 WiFi‑7 radio shares a Broadcom software base with a known over‑the‑air 5 GHz denial‑of‑service issue (a malformed frame can drop the 5 GHz radio until reboot). This lives in the proprietary Broadcom blob, not Reaper’s code, and cannot be patched by this firmware — it is noted here for awareness.

---

*Questions marked ⚠ VERIFY ON UNIT are the ones to confirm on a physical RT‑BEXXU before publishing this guide: the rescue button (Reset vs WPS) and LED sequence, the exact recovery image the BEXXU’s restoration flow expects, whether a second/rollback image exists, and any minimum‑version/anti‑rollback enforcement on downgrade.*
