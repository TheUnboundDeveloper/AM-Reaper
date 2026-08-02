# License texts

Full text of every license the Reaper firmware invokes, satisfying the "the
license must travel with the work" obligation (GPL v2 §1, GPL v3 §4, LGPL, OFL).

The **primary** license of the project — and of the GPL-covered majority of the
firmware — is **GPL v2**, whose text is the repository-root [`../LICENSE`](../LICENSE).
The texts below cover the additional licenses of components the image bundles.

| License | Text | Governs (examples) |
|---|---|---|
| **GPL-2.0-only** | [`../LICENSE`](../LICENSE) (repo root) | Asuswrt-Merlin base, the Reaper modifications ([`../LICENSE.reaper`](../LICENSE.reaper)), busybox, dnsmasq, iptables, and the bulk of the userspace |
| **GPL-3.0-or-later** | [`GPL-3.0.txt`](GPL-3.0.txt) | Samba 4.15.13a (SMB3 file server), GNU wget, GNU nano |
| **LGPL-2.1-or-later** | [`LGPL-2.1.txt`](LGPL-2.1.txt) | glib, avahi, libdaemon, and other shared libraries |
| **OFL-1.1** | [`OFL-1.1.txt`](OFL-1.1.txt) | the Inter and Rajdhani web fonts added by the Reaper UI |
| MIT | [`MIT-qrcode.txt`](MIT-qrcode.txt), [`MIT-jsTree.txt`](MIT-jsTree.txt) | jquery.qrcode, jsTree |
| BSD / ISC (OpenSSH) | [`OpenSSH.txt`](OpenSSH.txt) | openssh `sftp-server` |
| Net-SNMP (BSD-style) | [`Net-SNMP.txt`](Net-SNMP.txt) | net-snmp |

Every bundled package additionally retains its own license file in the
**reconstructed** source tree (pinned upstream + [`../patches/`](../patches/));
see [`../docs/SOURCE-AVAILABILITY.md`](../docs/SOURCE-AVAILABILITY.md).

The proprietary Broadcom / ASUS / Trend Micro / Tuxera components are **not**
open-source and are **not** redistributed by this repository — see
[`../docs/README.proprietary`](../docs/README.proprietary) and
[`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md).
