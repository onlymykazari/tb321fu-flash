#!/bin/bash
# Armada OTA 体检 / 手动更新（在电脑的 Git Bash 里跑）。
#
# 用法:
#   bash tools/armada-ota.sh <IP>              # 体检（更新重启后跑这个，不需要 sudo）
#   bash tools/armada-ota.sh <IP> reboot       # 重启，应用已 staged 的更新，然后体检
#   bash tools/armada-ota.sh <IP> upgrade      # sudo bootc upgrade + 重启 + 体检
#
# reboot/upgrade 需要 sudo 密码（交互输入，不落盘）。检查项依据 runbook 第八节。
set -u

IP=${1:?usage: armada-ota.sh <IP> [check|reboot|upgrade]}
MODE=${2:-check}
KEY="$HOME/.ssh/tb321fu"
ROOT_UUID=61564dbd-2530-4afb-a751-444d437d867b
SSH() { ssh -o ConnectTimeout=8 -o BatchMode=yes -i "$KEY" "armada@$IP" "$@"; }

die() { echo "ERROR: $*" >&2; exit 1; }

ask_pw() { read -rsp "sudo 密码 (armada@$IP): " PW; echo; [ -n "$PW" ] || die "需要密码"; }
sudo_run() { printf '%s\n' "$PW" | SSH "sudo -S -p '' $*"; }

wait_ssh() {
    echo "== 等设备回来 =="
    for i in $(seq 1 30); do
        sleep 15
        if SSH 'echo ok' >/dev/null 2>&1; then echo "SSH 回来 ($(date +%T))"; return 0; fi
        echo "  $(date +%T) 还没起来 ($i)"
    done
    die "5 分钟没等到 SSH；看 runbook 第八节回滚"
}

do_check() {
    echo "== Armada OTA 体检 ($IP, $(date +%F' '%T)) =="
    SSH 'echo ok' >/dev/null 2>&1 || die "连不上 armada@$IP：设备睡眠了、在 Android 里，或 IP 变了（SSH 不通不代表更新有问题）"
    SSH 'bash -s' <<REMOTE
set -u
fail=0
say() { printf '  [%-4s] %s\n' "\$2" "\$1"; }
ok()  { say "\$1" OK; }
bad() { say "\$1" FAIL; fail=1; }

v=\$(grep -E '^BUILD_ID=' /etc/os-release | cut -d'"' -f2)
say "booted 版本: \$v" info

cmd=\$(cat /proc/cmdline)
case "\$cmd" in *root=UUID=$ROOT_UUID*) ok "cmdline 根 UUID";; *) bad "cmdline 根 UUID";; esac
slot=\${cmd#BOOT_IMAGE=}; slot=\${slot%% *}
case "\$slot" in /Image-[ab]) ok "GRUB 槽位 (\$slot)";; *) bad "GRUB 槽位 (\$slot)";; esac

# 上次关机：grub-sync 必须成功（失败会自动回滚，更新等于没应用）
p=\$(journalctl -b -1 -o cat --no-pager 2>/dev/null)
if echo "\$p" | grep -q "tb321fu-grub-sync: in sync"; then ok "上次关机 grub-sync in sync"
else bad "上次关机 grub-sync in sync"; fi
if echo "\$p" | grep -qE "GRUB sync failed|rolling back deployment"; then bad "上次关机无回滚"; else ok "上次关机无回滚"; fi

# 本次启动
c=\$(journalctl -b -o cat --no-pager 2>/dev/null | grep -c "tb321fu-grub-sync: in sync")
[ "\$c" -ge 1 ] && ok "本次启动 grub-sync in sync" || bad "本次启动 grub-sync in sync"
ms=\$(systemctl show tb321fu-mark-boot-successful.service -p Result -p ExecMainStatus)
case "\$ms" in *Result=success*ExecMainStatus=0*|*ExecMainStatus=0*Result=success*) ok "boot_b 成功标记";; *) bad "boot_b 成功标记 (\$ms)";; esac

# 槽位属性（bit50 active / bit54 successful）
flags=\$(lsblk -no PARTLABEL,PARTFLAGS "\$(readlink -f /dev/disk/by-partlabel/boot_b)" 2>/dev/null | awk '/boot_b/{print \$2}')
flags=\${flags#0x}
case "\$flags" in
    ""|*[!0-9a-fA-F]*) bad "boot_b active+successful (flags=\${flags:-none})";;
    *) if [ "\$(( 0x\$flags >> 50 & 1 ))" = 1 ] && [ "\$(( 0x\$flags >> 54 & 1 ))" = 1 ]; then ok "boot_b active+successful (0x\$flags)"
       else bad "boot_b active+successful (0x\$flags)"; fi;;
esac

# ABL 更新器必须仍被 ConditionFirmware 跳过
cr=\$(systemctl show armada-bootimg-sync.service -p ConditionResult)
case "\$cr" in *ConditionResult=no*) ok "ABL 更新器未激活";; *) bad "ABL 更新器未激活 (\$cr)";; esac

n=\$(systemctl --failed --no-legend 2>/dev/null | wc -l)
[ "\$n" = 0 ] && ok "无 failed unit" || { bad "\$n 个 failed unit:"; systemctl --failed --no-legend; }

a=\$(df -BG --output=avail /sysroot | tail -1 | tr -d 'G ')
say "armada_root 剩余 \${a}G" info

# 需要 sudo 的两项（abl 字节、FAT 剩余）不在这里查；命令见 runbook 第八节第 5 步
exit \$fail
REMOTE
    rc=$?
    [ "$rc" = 0 ] && echo "== 全部通过 ==" || { echo "== 有 FAIL，按 runbook 第八节处理 =="; }
    return $rc
}

case "$MODE" in
check)
    do_check
    ;;
reboot)
    ask_pw
    echo "== 重启应用已 staged 的更新 =="
    sudo_run systemctl reboot || die "重启命令失败"
    wait_ssh
    do_check
    ;;
upgrade)
    ask_pw
    echo "== bootc upgrade =="
    sudo_run bootc upgrade 2>&1 | tr '\r' '\n' | grep -v '^$' | tail -12
    [ "${PIPESTATUS[0]}" = 0 ] || die "bootc upgrade 失败（未重启，设备保持原样）"
    echo "== 重启 =="
    sudo_run systemctl reboot || die "重启命令失败"
    wait_ssh
    do_check
    ;;
*)
    die "未知模式 '$MODE'（check / reboot / upgrade）"
    ;;
esac
