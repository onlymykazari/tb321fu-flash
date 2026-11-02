#!/bin/bash
for p in boot_a boot_b; do
  dev=$(readlink -f /dev/disk/by-partlabel/$p)
  disk=/dev/$(lsblk -no PKNAME "$dev")
  n=$(cat /sys/class/block/$(basename "$dev")/partition)
  a=$(sgdisk -i "$n" "$disk" | grep -i "attribute flags" | awk '{print $3}')
  v=$((16#$a))
  echo "$p ($disk p$n) attr=$a active=$(( (v>>50)&1 )) prio=$(( (v>>48)&3 )) retry=$(( (v>>51)&7 )) successful=$(( (v>>54)&1 )) unbootable=$(( (v>>55)&1 ))"
done
