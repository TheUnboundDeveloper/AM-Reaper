# Reaper Quick Start: first setup after a factory reset

> **Doc status:** current as of **v3.7.5** · 2026-11-09 <!--@stamp-->

**Applies to:** every supported model, Reaper v3.4.2 and later, after a first flash or a factory reset.

Setup takes about five minutes. There is no wizard: you sign in, fill in one box with four fields, and the router restarts once. The full reference is the owner's guide, [`REAPER-GUIDE.md`](REAPER-GUIDE.md).

## What a reset router looks like

| | Factory value |
|---|---|
| Router address | `http://192.168.50.1` |
| Sign-in | name `admin`, password `admin` (both lower case) |
| Wi-Fi | an **open** network (no password) named `ASUS_xx`, where `xx` is specific to your router |
| Internet port | the port labelled **WAN** |

The `admin` / `admin` sign-in is only the starting point. Reaper shows a warning on every page until you replace it, and the steps below replace it.

## Steps

1. **Connect to the router.** Plug a computer into one of the LAN ports (best), or join the open `ASUS_xx` Wi-Fi.
2. **Plug the internet cable into the port labelled WAN.** You can also do this after setup.
3. **Open `http://192.168.50.1`** in a browser and sign in with `admin` / `admin`.
4. **Click "Set up this router".** It is the button in the banner that says *This router is not secured*.
5. **Fill in the four fields:**

   | Field | Rule |
   |---|---|
   | **Network Name (SSID)** | 1 to 32 characters. One name is used on every band. |
   | **Wi-Fi password** | 8 to 63 characters. This is what people type to join the Wi-Fi. |
   | **Router Login Name** | Lower-case letters, digits, `-` and `_`. At least 2 characters, starting with a letter or digit. Not `root`, `guest` or `anonymous`. |
   | **Router login password** | 10 to 32 characters with at least one letter, one number and one special character. It must differ from the login name. Keep it different from the Wi-Fi password. |

6. **Click "Apply & Reboot".** The router restarts once. This takes about three minutes, and the page counts down.
7. **Reconnect and sign in again.** The open `ASUS_xx` network is gone. Join the network name you chose, with your new Wi-Fi password, then open `http://192.168.50.1` and sign in with your new login name and password.

When the banner no longer appears, the router is set up.

## Internet

- **Most cable and fiber connections** work as soon as the cable is in the WAN port. Nothing to set.
- **PPPoE or a static address:** go to **WAN → Internet Connection**.
- **The cable is in a different port:** choose that port on **WAN → WAN Ports**, or move the cable to the port labelled WAN.

## If something does not work

| What you see | What to do |
|---|---|
| `admin` / `admin` is refused | It only works on a router that has just been reset, and both words are lower case. If the login was changed and is lost, factory reset the router again. |
| The page at `192.168.50.1` does not open | Your device is not on the router's network. Use a cable to a LAN port, or join the `ASUS_xx` Wi-Fi, and check that no other network on your device uses `192.168.50.x`. |
| The browser warns about the certificate | You opened `https://192.168.50.1:8443`. The router's certificate is self-signed until you install your own. Accept the warning, or use `http://192.168.50.1` for this first setup. |
| The login password is refused in the box | It needs 10 or more characters with a letter, a number and a special character, and it cannot equal the login name. |
| The login name changes to lower case as you type | Login names are lower case only. |
| After the restart the page does not come back | Your device is still looking for the old `ASUS_xx` network. Join your new network name. |
| The banner says *One step left to secure this router* | Only one of the two (login, Wi-Fi) was changed. Click the button in the banner to change the other. |

## Good to know

- **Do the setup straight away.** Until step 6, the Wi-Fi is open and the login is the factory one, so anyone in range can join and sign in.
- **The time zone** is set from your browser during setup. Check it on **Administration → System** if the clock looks wrong.
- **The warning banner cannot be closed.** It disappears by itself once both the login and the Wi-Fi have left their factory values.
- **A factory reset brings all of this back:** `admin` / `admin`, the open `ASUS_xx` network and `192.168.50.1`.

## Next steps

- **Save a backup** once the router works the way you want: **Administration → Restore/Save/Upload Setting**, the *Backup & Restore* page, then **Download full backup** (guide section 2.5).
- **Check for a firmware update:** **Administration → Firmware Upgrade** (guide section 2.11).
- **Add protection:** Warden, Dreadwatch, Wallguard and Gatekeeper are off at factory. The guide describes each one (sections 4.2 and 4.3).
- **Optional: watch name lookups.** On **Administration → DNS Failover**, switch on *LAN name resolution check* and click **Apply**. Once a minute the router checks that devices on your network can look up names. The status reads **Active** when they can, **Fault** when they cannot (the Internet status turns amber) and **Inactive** while the switch is off. It is off at factory, and each check sends one test lookup to the internet (guide section 4.14a).
- **Optional: encrypt DNS on both sides.** On **LAN → DNS**, switch on DNS-over-TLS to an upstream server so lookups leave the router encrypted. On **Bastion → Encrypted DNS**, the two switches at the top let your devices encrypt their lookups to the router as well (it needs a trusted certificate, for example Let's Encrypt for your DDNS name). The card *Is every lookup encrypted?* shows both sides and says in red which one is not working (guide section 4.3.4).
- **Every factory value** is listed in guide section 8.
