#!/bin/bash
# 迁移第 1 步：把 btrfs 缩到 124G，写入 gpt_split.py 生成的新分区表。以 root 运行。
# 用法: 01_shrink_and_gpt.sh new_primary.bin new_backup.bin [124G]
# 新分区表在电脑上生成:
#   python tb321fu-android-armada-dualboot/tools/gpt_split.py gpt_primary.bin gpt_backup.bin new_primary.bin new_backup.bin --android-gib 128
set -euo pipefail
NP=$1; NB=$2; SIZE=${3:-124G}
DISK=/dev/$(lsblk -no PKNAME "$(readlink -f /dev/disk/by-partlabel/userdata)")
N=$(blockdev --getsize64 "$DISK")
sum() { sha256sum | cut -d' ' -f1; }

# /sysroot 是只读挂载，经 /var（同一子卷的可写挂载）缩容
btrfs filesystem resize "$SIZE" /var
btrfs filesystem show /sysroot | tail -2

dd if="$NP" of="$DISK" bs=4096 seek=0 count=6 conv=notrunc,fsync status=none
# 写到磁盘末尾要用 seek（输出偏移）；当时误写成 skip，是写后校验拦下来的
dd if="$NB" of="$DISK" bs=4096 seek=$((N/4096-5)) count=5 conv=notrunc,fsync status=none
[ "$(dd if="$DISK" bs=4096 count=6 status=none | sum)" = "$(sum < "$NP")" ] || { echo "!! 主 GPT 校验失败"; exit 1; }
[ "$(dd if="$DISK" bs=4096 skip=$((N/4096-5)) count=5 status=none | sum)" = "$(sum < "$NB")" ] || { echo "!! 备份 GPT 校验失败"; exit 1; }
echo "GPT 写入并校验通过"
partx -u "$DISK" || partprobe "$DISK"
lsblk -o NAME,SIZE,PARTLABEL "$DISK" | tail -4
