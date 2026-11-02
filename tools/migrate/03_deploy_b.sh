#!/bin/bash
# 迁移第 3 步：部署 B 槽，并让副本用它自己的 UUID 启动。以 root 运行。
# 用法: 03_deploy_b.sh <release 的 boot.img> <release 的 super.img>（必须和当前系统同版本）
#
# 为什么不用 btrfstune 把副本改回旧 UUID：新旧两个文件系统同时存在时，btrfstune 拒绝设成
# 重复的 fsid（"fsid ... is not unique"，-f 也绕不过）。所以保留副本自己的 UUID，
# 改引用它的地方。内核参数只记录在 BLS 条目里（ostree 的 origin 文件里没有 kargs），
# 以后系统更新会沿用。
set -euo pipefail
BOOT=$1; SUPERIMG=$2
OLD=$(cat /root/old-uuid.txt)
NEW=$(blkid -s UUID -o value /dev/disk/by-partlabel/armada_root)
[ -n "$OLD" ] && [ -n "$NEW" ] && [ "$OLD" != "$NEW" ] || { echo "!! UUID 异常: OLD=$OLD NEW=$NEW"; exit 1; }

dd if="$BOOT" of=/dev/disk/by-partlabel/boot_b bs=1M conv=fsync status=none
cmp "$BOOT" /dev/disk/by-partlabel/boot_b && echo "boot_b 写入校验 OK"
dd if="$SUPERIMG" of=/dev/disk/by-partlabel/armada_esp bs=1M conv=fsync status=none
cmp "$SUPERIMG" /dev/disk/by-partlabel/armada_esp && echo "armada_esp 写入校验 OK"

mkdir -p /mnt/aroot
mount /dev/disk/by-partlabel/armada_root /mnt/aroot
sed -i "s|root=UUID=$OLD|root=UUID=$NEW|g" /mnt/aroot/root/boot/loader/entries/*.conf
if grep -q "$OLD" /mnt/aroot/root/boot/loader/entries/*.conf; then echo "!! BLS 里仍有旧 UUID"; exit 1; fi
umount /mnt/aroot

# FAT 是 512 字节扇区，UFS 逻辑块是 4096，内核拒绝直接挂：要经过 512 字节扇区的 loop 设备
lo=$(losetup -f --show --sector-size 512 /dev/disk/by-partlabel/armada_esp)
mkdir -p /mnt/esp
mount -t vfat "$lo" /mnt/esp
sed -i "s|root=UUID=$OLD|root=UUID=$NEW|g" /mnt/esp/boot/grub/grub.cfg
echo "== armada_esp grub.cfg 的 root 引用:"
grep -oP 'root=UUID=[0-9a-f-]+' /mnt/esp/boot/grub/grub.cfg | sort | uniq -c
umount /mnt/esp
losetup -d "$lo"
sync
