#!/bin/bash
# 迁移第 0 步：只读预检 + 备份分区表。在原 Armada 单系统上以 root 运行。
# 本版 Armada 的根是 composefs，"/" 不是 btrfs：所有 btrfs 查询都要对 /sysroot 做
# （当时预检用了 "/"，导致记录的旧 UUID 是空的）。
set -u
DISK=/dev/$(lsblk -no PKNAME "$(readlink -f /dev/disk/by-partlabel/userdata)")
echo "== 磁盘 $DISK"
lsblk -o NAME,SIZE,PARTLABEL "$DISK"
echo "== /sysroot 来源: $(findmnt -no SOURCE /sysroot)"
echo "== btrfs 用量（Device allocated 必须 <= ~118 GiB 才能缩到 124G）"
btrfs filesystem usage /sysroot | head -8
echo "== 子卷（root 之外的都是嵌套子卷，迁移时要单独搬）"
btrfs subvolume list /sysroot
echo "== 旧 fsid（grub.cfg / BLS 的 root=UUID 应与之相同）"
btrfs filesystem show /sysroot | grep -oP 'uuid:\s*\K[0-9a-f-]+' | tee /root/old-uuid.txt
[ -s /root/old-uuid.txt ] || { echo "!! 没取到 UUID"; exit 1; }
N=$(blockdev --getsize64 "$DISK")
dd if="$DISK" of=/root/gpt_primary.bin bs=4096 count=6 status=none
dd if="$DISK" of=/root/gpt_backup.bin bs=4096 skip=$((N/4096-5)) count=5 status=none
echo "== GPT 已备份到 /root/gpt_primary.bin、/root/gpt_backup.bin（拷回电脑保存），磁盘 $N 字节"
echo "== 系统版本"; grep -E '^(NAME|VERSION)=' /etc/os-release
