#!/bin/bash
# 迁移第 2 步：把运行中系统的 btrfs（子卷 root 及其嵌套子卷）完整复制到 armada_root。以 root 运行。
# 先关掉 Steam 等大 IO 程序。整个过程只读源盘，源数据不受影响。
# 要点：
#   * /sysroot 只读，快照放在 /var（同一子卷的可写挂载）；
#   * btrfs 快照不包含嵌套子卷（如 Steam 的 steamapps），副本里只会留下空目录，要逐个单独 send/receive；
#   * receive 出来的子卷带 received_uuid，新版 btrfs-progs 要加 -f 才能解除只读。
# 不支持路径里带空格的子卷，也不处理“嵌套子卷里再嵌套”的情况（遇到会报错退出）。
set -euo pipefail
DEV=/dev/disk/by-partlabel/armada_root
MNT=/mnt/aroot

mkfs.btrfs -f -L armada "$DEV"
mkdir -p "$MNT"
mount "$DEV" "$MNT"

btrfs subvolume snapshot -r /sysroot /var/.mig-snap
btrfs send /var/.mig-snap | btrfs receive "$MNT/"
btrfs property set -f "$MNT/.mig-snap" ro false
mv "$MNT/.mig-snap" "$MNT/root"
btrfs subvolume delete /var/.mig-snap

# 当时设备上 `btrfs subvolume list /sysroot` 的输出：root 自己显示为 "root"，
# 嵌套子卷显示为相对 /sysroot 的路径（ostree/deploy/default/var/home/...）
for P in $(btrfs subvolume list /sysroot | awk '$NF != "root" {print $NF}'); do
  echo "== 嵌套子卷 $P"
  btrfs subvolume show "/sysroot/$P" >/dev/null
  btrfs subvolume snapshot -r "/sysroot/$P" /var/.mig-sub
  btrfs send /var/.mig-sub | btrfs receive "$MNT/"
  btrfs property set -f "$MNT/.mig-sub" ro false
  rmdir "$MNT/root/$P"
  mv "$MNT/.mig-sub" "$MNT/root/$P"
  btrfs subvolume delete /var/.mig-sub
done

echo "== 副本子卷（应与源一致）"
btrfs subvolume list "$MNT"
touch "$MNT/root/.rwtest" && rm "$MNT/root/.rwtest" && echo "副本可写"
btrfs scrub start -B "$MNT"
umount "$MNT"
sync
echo "== 完成。副本 fsid: $(blkid -s UUID -o value "$DEV")"
