#!/bin/bash
# 迁移第 4 步：让 B 槽启动副本。在原系统（还在用 super 开头的 GRUB FAT）上以 root 运行，然后重启。
#
# 原因：B 槽的 UEFI 加载器会优先找到 super 开头那块旧 GRUB FAT，而不是 armada_esp。
# 在 super 恢复成安卓原厂内容之前，B 槽实际上走的是旧 FAT。所以把旧 FAT 的 grub.cfg
# 也指向副本，同时保留一个指向旧数据的备用项（GRUB 菜单里用音量键选）。
# 另外，原系统关机时 tb321fu-grub-sync 会按它自己的 BLS 重写这个 grub.cfg，
# 所以要用 /run 下的临时覆盖让这一次关机跳过同步（重启后自动失效）。
set -euo pipefail
OLD=$(cat /root/old-uuid.txt)
NEW=$(blkid -s UUID -o value /dev/disk/by-partlabel/armada_root)
[ -n "$OLD" ] && [ -n "$NEW" ] && [ "$OLD" != "$NEW" ] || { echo "!! UUID 异常"; exit 1; }
[ -e /run/ostree/staged-deployment ] && { echo "!! 有待应用的系统更新，先处理掉再做"; exit 1; }

lo=$(losetup -f --show --sector-size 512 /dev/disk/by-partlabel/super)
mkdir -p /tmp/sfat
mount -t vfat "$lo" /tmp/sfat
cfg=/tmp/sfat/boot/grub/grub.cfg
cp "$cfg" /root/superfat-grub.cfg.bak
python3 - "$cfg" "$OLD" "$NEW" <<'PY'
import re, sys
path, old, new = sys.argv[1:4]
cfg = open(path).read()
first = re.findall(r'menuentry "[^"]*" \{.*?\n\}\n', cfg, flags=re.S)[0]
fallback = re.sub(r'menuentry "([^"]*)"', r'menuentry "\1 (OLD userdata, fallback)"', first, count=1)
out = cfg.replace(old, new).replace('menuentry "Power off"', fallback + '\nmenuentry "Power off"')
open(path, "w").write(out)
PY
grep -E '^menuentry' "$cfg"
umount /tmp/sfat
losetup -d "$lo"

mkdir -p /run/systemd/system/tb321fu-grub-sync.service.d /run/systemd/system/ostree-finalize-staged.service.d
printf '[Service]\nExecStart=\nExecStop=\nExecStart=/bin/true\n' > /run/systemd/system/tb321fu-grub-sync.service.d/99-skip-once.conf
printf '[Unit]\nConditionPathExists=/nonexistent-skip-once\n' > /run/systemd/system/ostree-finalize-staged.service.d/99-skip-once.conf
systemctl daemon-reload
sync
echo "== 完成。现在: fastboot set_active b（B 槽固件必须已补齐）→ 启动后确认 /proc/cmdline 里是 root=UUID=$NEW"
echo "== 然后在副本里运行套件的 armada/dualboot-fix.sh"
