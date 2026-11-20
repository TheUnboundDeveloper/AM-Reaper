#!/usr/bin/env python3
"""Review 2026-11-03 - the HIGH and MEDIUM fixes the owner asked for.

  E-1  bcm_knvram NETLINK_WLCSM: only a sender with CAP_SYS_ADMIN may use the nvram family (not
       CAP_NET_ADMIN - dnsmasq keeps that as nobody); sender-controlled lengths are bounded by what
       arrived (REGISTER name copy, GETALL index, XFR string).
  E-2  /data (the kernel-nvram commit file) is 0700 and the file 0600 right after /data is mounted.
  C-1  /var/lock and /var/tmp/dhcp 0755, rc lock files 0600, /tmp/mnt 0755, avahi / nt_center /
       netool directories through reaper_secure_dir(), mount_r() refuses a mount point that is not
       a real directory.
  E-3  proc_create_cmd() is owner-write; rc drops group/other write under /proc/driver (bcm_enet is
       prebuilt, so only that reaches its consoles). The real reaper_proc_nowrite() is compiled and
       run on a scratch tree.
  E-4  rc makes the Broadcom driver nodes, kmsg, kmem and raw sd/sg nodes 0600 (after the static
       nodes exist and again before services start); asus_sd / asus_sg hotplug applets do it for
       new disks (the real reaper_devnode_private() is compiled and run with a chmod stub);
       blog_drv_ioctl() requires CAP_SYS_ADMIN.
  E-5  five 4.19 stable backports: CVE-2023-42752, CVE-2024-36904, CVE-2024-56631, CVE-2024-41012,
       CVE-2024-47685. (CVE-2024-26921 is deferred - its upstream fix is a 6.x rework; see the
       private review report.)
Source pins are checked against the tree; the two rc helpers are also compiled and run with the
host compiler when one is present. Kernel and BSP code cannot be compiled here.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] / REAPER_ROUTER_SRC).
"""
import os, re, shutil, stat, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "init.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
PLAT = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916"))
CC = shutil.which("gcc") or shutil.which("cc")

def rd(p):
    return open(p, encoding="latin-1").read() if os.path.isfile(p) else None
def nocomment(t):
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("//"))
def func(t, head):
    """the text of the C function whose definition line starts with head (to its closing brace)"""
    m = re.search(r"\n" + re.escape(head) + r".*?\n\}\n", t, re.S)
    return m.group(0) if m else ""

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

R = lambda rel: rd(os.path.join(SRC, rel)) or ""
init, rcc, usb, svc = R("rc/init.c"), R("rc/rc.c"), R("rc/usb.c"), R("rc/services.c")
files, netool = R("shared/files.c"), R("rc/netool.c")
initc = nocomment(init)

# ---- E-2
i_mount = initc.find('reaper_mount_data("mount -t ubifs ubi:data /data");')
i_data = initc.find('chmod("/data", 0700);')
i_knv = initc.find('system("insmod bcm_knvram")')
check("E-2: /data is chmod 0700 after it is mounted and before bcm_knvram loads",
      0 <= i_mount < i_data < i_knv, (i_mount, i_data, i_knv))
check("E-2: the commit file is chmod 0600", 'chmod("/data/.kernel_nvram.setting", 0600);' in initc)

# ---- C-1
for d in ("/var/lock", "/var/tmp/dhcp"):
    check("C-1: %s is made 0755 and chmod 0755" % d,
          'mkdir("%s", 0755);' % d in initc and 'chmod("%s", 0755);' % d in initc
          and 'mkdir("%s", 0777);' % d not in initc)
check("C-1: /tmp/mnt is 0755", "chmod(POOL_MOUNT_ROOT, 0755);" in initc and "chmod(POOL_MOUNT_ROOT, 0777);" not in initc)
fl = nocomment(func(files, "int _file_lock("))
check("C-1: rc lock files are created 0600", "open(path, O_CREAT | O_RDWR, 0600)" in fl and "0666" not in fl, fl[:200])
svcc = nocomment(svc)
for name in ("AVAHI_CONFIG_PATH", "AVAHI_SERVICES_PATH", "NOTIFY_CENTER_TEMP_DIR"):
    check("C-1: %s goes through reaper_secure_dir(.., 0755), not mkdir_if_none" % name,
          "reaper_secure_dir(%s, 0755);" % name in svcc and "mkdir_if_none(%s);" % name not in svcc)
check("C-1: netool's result directory goes through reaper_secure_dir",
      "reaper_secure_dir(NETOOL_RESULT_DIR, 0755);" in netool and "mkdir_if_none(NETOOL_RESULT_DIR);" not in nocomment(netool))
mr = nocomment(func(usb, "int mount_r("))
i_l, i_m = mr.find("lstat(mnt_dir, &mst)"), mr.find("mount(mnt_dev, mnt_dir")
check("C-1: mount_r() lstat()s the mount point before the first mount(2)", 0 <= i_l < i_m, (i_l, i_m))
check("C-1: ...and refuses a non-directory", "!S_ISDIR(mst.st_mode)" in mr and "return MOUNT_VAL_FAIL;" in mr)

# ---- E-3 / E-4 (rc side)
perms = func(init, "static void reaper_root_only_perms(void)")
check("E-4: reaper_root_only_perms() is in rc/init.c", bool(perms))
for n in ("fcache", "pktrunner", "bdmf_shell", "bcmvlan", "blog", "bpm", "mpm", "bp3", "spdsvc", "kmsg", "kmem"):
    check("E-4: /dev/%s is in the 0600 list" % n, '"%s"' % n in perms)
check("E-4: raw sd/sg nodes present at boot are made 0600", '"sd", 2' in perms and '"sg", 2' in perms and "chmod(path, 0600)" in perms)
check("E-3: /proc/driver loses group/other write", 'reaper_proc_nowrite("/proc/driver", 0);' in perms)
calls = [m.start() for m in re.finditer(r"\breaper_root_only_perms\(\);", initc)]
i_static = initc.find('eval("/etc/make_static_devnodes.sh");')
i_start = [m.start() for m in re.finditer(r"\n\s*start_services\(\);", initc)]
check("E-4: called right after the static device nodes are made", any(c > i_static for c in calls) and i_static >= 0, (calls, i_static))
check("E-4: called again just before start_services() (drivers loaded by then)",
      any(any(0 < s - c < 200 for s in i_start) for c in calls), (calls, i_start[:4]))
rcc_c = nocomment(rcc)
for app in ("asus_sd", "asus_sg"):
    check("E-4: the %s applet makes the new node private first" % app,
          re.search(r"reaper_devnode_private\(argv\[1\], argv\[2\]\);\s*return %s\(argv\[1\], argv\[2\]\);" % app, rcc_c) is not None)

# ---- E-1 / E-3 / E-4 / E-5 (BSP and kernel)
if not os.path.isdir(PLAT):
    print("SKIP (part): no platform tree at %s - BSP and kernel pins not checked" % PLAT)
else:
    P = lambda rel: rd(os.path.join(PLAT, rel)) or ""
    wl = P("bcmdrivers/opensource/char/bcm_knvram/impl1/src/wlcsm_netlink.c")
    rcv = nocomment(func(wl, "wlcsm_nl_rcv_skb("))
    i_cap, i_sw = rcv.find("netlink_capable(skb, CAP_SYS_ADMIN)"), rcv.find("switch(msg_hdr->type)")
    check("E-1: the nvram family requires CAP_SYS_ADMIN before any message is handled", 0 <= i_cap < i_sw, (i_cap, i_sw))
    check("E-1: CAP_NET_ADMIN is not the gate (dnsmasq keeps it as nobody)", "netlink_capable(skb, CAP_NET_ADMIN)" not in rcv)
    check("E-1: msg_hdr->len is bounded by what arrived", "if (msg_hdr->len > avail)" in rcv)
    check("E-1: the REGISTER name copy is bounded and terminated",
          "memcpy(process->name,reg->process,nlen);" in rcv and "process->name[nlen] = '\\0';" in rcv
          and "memcpy(process->name,reg->process,reg->len);" not in rcv)
    check("E-1: the GETALL page index is bounded", "index < 0 || index > INT_MAX / maxAllowedSize" in rcv)
    check("E-1: no unbounded strcpy into buffer", "strcpy(buffer, p);" not in rcv and "strlcpy(buffer, p, sizeof(buffer));" in rcv)
    pc = P("bcmdrivers/opensource/include/bcm963xx/proc_cmd.h")
    check("E-3: proc_create_cmd() is owner-write", "S_IRUGO | S_IWUSR" in pc and "S_IWUGO" not in nocomment(pc))
    # the definition, not the forward declaration near the top of blog.c (that one ends in ");")
    m = re.search(r"\nstatic long blog_drv_ioctl\(struct file \*filep, unsigned int command,\s*\n\s*unsigned long arg\)\n\{.*?\n\}",
                  P("kernel/bcmkernel/net/core/blog.c"), re.S)
    bl = m.group(0) if m else ""
    check("E-4: blog_drv_ioctl() definition found", bool(bl))
    i_c, i_l = bl.find("capable(CAP_SYS_ADMIN)"), bl.find("BLOG_LOCK_BH();")
    check("E-4: blog_drv_ioctl() requires CAP_SYS_ADMIN before it takes the lock", 0 <= i_c < i_l, (i_c, i_l))
    K = lambda rel: P("kernel/linux-4.19/" + rel)
    ig = func(K("net/ipv4/igmp.c"), "static struct sk_buff *igmpv3_newpack(")
    check("E-5 CVE-2023-42752: igmpv3_newpack() caps the size at IP_MAX_MTU", "size = min(mtu, IP_MAX_MTU);" in ig)
    tw = nocomment(func(K("net/ipv4/tcp_ipv4.c"), "int tcp_twsk_unique("))
    check("E-5 CVE-2024-36904: tcp_twsk_unique() takes the ref with refcount_inc_not_zero() and no sock_hold()",
          "refcount_inc_not_zero(&sktw->sk_refcnt)" in tw and "sock_hold(sktw)" not in tw)
    sg = nocomment(K("drivers/scsi/sg.c"))
    m = re.search(r"\nsg_release\(struct inode \*inode, struct file \*filp\)\n\{.*?\n\}\n", sg, re.S)
    rel = m.group(0) if m else ""
    i_u, i_k = rel.find("mutex_unlock(&sdp->open_rel_lock);"), rel.find("kref_put(&sfp->f_ref, sg_remove_sfp);")
    check("E-5 CVE-2024-56631: sg_release() drops the fd reference after the unlock", 0 <= i_u < i_k, (i_u, i_k))
    lk = nocomment(K("fs/locks.c"))
    check("E-5 CVE-2024-41012: the fcntl/close race removes the locks with locks_remove_posix()",
          lk.count("locks_remove_posix(filp, current->files);") == 2 and "WARN_ON_ONCE(error);" not in lk)
    rj = K("net/ipv6/netfilter/nf_reject_ipv6.c")
    check("E-5 CVE-2024-47685: the IPv6 RST header is zeroed", "tcph = skb_put_zero(nskb, sizeof(struct tcphdr));" in rj
          and "tcph = skb_put(nskb, sizeof(struct tcphdr));" not in rj)

# ---- the two rc helpers, compiled and run
if not CC:
    print("SKIP (part): no host C compiler - helpers not run")
else:
    tmp = tempfile.mkdtemp(prefix="rev1103_")
    try:
        dp = func(rcc, "static void reaper_devnode_private(const char *name, const char *action)")
        check("E-4: reaper_devnode_private() found in rc/rc.c", bool(dp))
        if dp:
            c = os.path.join(tmp, "dp.c"); x = os.path.join(tmp, "dp")
            open(c, "w").write("#include <stdio.h>\n#include <string.h>\n#include <sys/stat.h>\n"
                               "static int calls;\n#define chmod(p, m) (printf(\"%s %o\\n\", p, (unsigned)(m)), ++calls)\n" + dp +
                               "int main(void) {\n"
                               " reaper_devnode_private(\"sda\", \"add\"); reaper_devnode_private(\"sda1\", \"add\");\n"
                               " reaper_devnode_private(\"sg0\", \"add\"); reaper_devnode_private(\"sda1\", \"remove\");\n"
                               " reaper_devnode_private(\"../etc/shadow\", \"add\"); reaper_devnode_private(\"sda/x\", \"add\");\n"
                               " reaper_devnode_private(\"SDA\", \"add\"); reaper_devnode_private(\"\", \"add\");\n"
                               " reaper_devnode_private(NULL, \"add\"); reaper_devnode_private(\"sda\", NULL);\n"
                               " reaper_devnode_private(\"sdaaaaaaaaaaaaaaaaaaa\", \"add\"); return 0; }\n")
            r = subprocess.run([CC, "-std=gnu99", "-Wall", "-o", x, c], capture_output=True, text=True)
            check("E-4: reaper_devnode_private() compiles", r.returncode == 0, r.stderr)
            if r.returncode == 0:
                out = subprocess.run([x], capture_output=True, text=True).stdout.split("\n")
                out = [l for l in out if l]
                check("E-4: only add events for plain sd/sg names are chmod 0600",
                      out == ["/dev/sda 600", "/dev/sda1 600", "/dev/sg0 600"], out)
        pn = func(init, "static void reaper_proc_nowrite(const char *dir, int depth)")
        check("E-3: reaper_proc_nowrite() found in rc/init.c", bool(pn))
        if pn:
            c = os.path.join(tmp, "pn.c"); x = os.path.join(tmp, "pn")
            open(c, "w").write("#include <stdio.h>\n#include <string.h>\n#include <dirent.h>\n#include <sys/stat.h>\n#include <sys/types.h>\n" + pn +
                               "int main(int c, char **v) { reaper_proc_nowrite(v[1], 0); return 0; }\n")
            r = subprocess.run([CC, "-std=gnu99", "-Wall", "-o", x, c], capture_output=True, text=True)
            check("E-3: reaper_proc_nowrite() compiles", r.returncode == 0, r.stderr)
            if r.returncode == 0:
                root = os.path.join(tmp, "driver"); os.makedirs(os.path.join(root, "phy")); os.makedirs(os.path.join(root, "enet", "x"))
                spec = {"phy/cmd": 0o666, "enet/cmd": 0o666, "enet/stats": 0o664, "enet/x/deep": 0o622, "keep": 0o600, "ro": 0o444}
                for f, m in spec.items():
                    p = os.path.join(root, f); open(p, "w").close(); os.chmod(p, m)
                subprocess.run([x, root])
                got = {f: stat.S_IMODE(os.stat(os.path.join(root, f)).st_mode) for f in spec}
                want = {"phy/cmd": 0o644, "enet/cmd": 0o644, "enet/stats": 0o644, "enet/x/deep": 0o600, "keep": 0o600, "ro": 0o444}
                check("E-3: group/other write comes off every file at any depth, nothing else changes", got == want,
                      {k: oct(v) for k, v in got.items()})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
