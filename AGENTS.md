# TB321FU 刷机工作区

联想拯救者 Y700 三代（TB321FU，SM8650）的 Android + Armada 双系统维护目录。
完整知识库在 `双系统迁移-runbook.md`：当前状态、踩坑记录、救援、从零重做。动手前先读它的第三节。

## 设备现状（2026-11-02）
- A 槽：Android，Pixel tangorpro 15 GSI V6，底包 ZUI 17.5.10.170（9008 包 `TB321FU_ZUI_17.5.10.170_OPEN_CRACKED`），boot_a 是 SukiSU Ultra GKI，userdata 128 GiB（f2fs）。
- B 槽：Armada **20261028.903dbdb**（ghcr 构建 `build-20261028.903dbdb-40750905234-1`，2026-11-02 从 preview 4 用 `bootc upgrade` 升上来的，回退部署是 preview 4），GRUB FAT 在 `armada_esp`（双槽：a=新 b=旧，剩 22 MB），根在 `armada_root`（btrfs，fsid `61564dbd-2530-4afb-a751-444d437d867b`；grub.cfg 和 BLS 都引用这个 UUID）。
- Steam 系统更新现在可用（issue #4 的元数据已补）。最新 release（preview 5，v20261024.0146e89）只用于从零安装，镜像本地不再保留（公开直链和哈希见 `ASSETS.md`）；更新走 `ghcr.io/enij90/armada-tb321fu:latest`。更新前的 armada_esp 备份在 `_work/backup/`、设备 `/var/tmp/` 和私有备份仓；btrfs 快照 `root-pre-ota-20261102` 一周后删。
- B 侧固件（xbl_b、abl_b 等 31 个分区）是用 9008 从 A 侧镜像补上的。super 是原厂内容，开头没有 FAT。

## 仓库与资产（2026-11-02 整理）
- 本目录就是公开仓 <https://github.com/onlymykazari/tb321fu-flash>。大文件不入库（`.gitignore` 按扩展名排除），位置全在 `ASSETS.md`。
- 二进制资产的私有备份：<https://github.com/onlymykazari/tb321fu-assets>，release `20261102`（armada_esp 备份、迁移前后 GPT、boot/vbmeta、两个模块 zip）。里面有联想固件和本机专属数据，**不要公开**。9008 包和 GSI zip 两个大文件不放 GitHub，用户存在自己的网盘上，哈希在 `ASSETS.md`。
- 本地已删、需要时重建或下载的：`_work/super_stock.img`（`tools/super_compose.py` 从 9008 包重建）、`_work/release*/` 的镜像（enij90 的 release）、`_work/android/` 里解压出的 GSI `.img`（解压根目录的 zip）。**用前核对哈希**，哈希都在 `ASSETS.md` 和保留的 `.sha256` / `SHA256SUMS` 里。
- 相邻的独立 git 仓库，被 `.gitignore` 排除：`tb321fu-android-armada-dualboot/`（origin = 自己的 fork，upstream = CharlesGool；修复已提 PR #2）、`tb321fu-vintf-vndk-fix/`（自己的）。enij90 上游 `armada-tb321fu` 的本地 clone 已删，预防性 fork 在 <https://github.com/onlymykazari/armada-tb321fu>，要看源码重新 clone。

## 硬性规则
1. **不要用原版 `rawprogram0.xml` 全量刷 9008**：会重建原厂 GPT，`armada_esp`/`armada_root` 都会消失。需要线刷时用 `_work/rawprogram0_nogpt.xml`，不加载 `patch0.xml`。
2. **全量刷过这个 9008 包后，`set_active b` 之前必须先补 B 侧固件**（`tools/make_fill_b.py` 生成的 `_work/qfil/tool/fill_b_lun*.xml`），否则切到 B 槽会直接掉进 9008。
3. **大分区（super、userdata/armada_root）不要依赖 ABL 的 fastboot**：实测 `fastboot flash super` 全部 OKAY，但 4 GiB 之后没写对。用 Linux 的 `dd`/`tools/simg_write.py` 或 fastbootd 写，**每次写完都要校验哈希**（读之前先 `drop_caches`）。
4. super 里不能残留 GRUB FAT，否则 B 槽加载器会优先用它，而不是 armada_esp。
5. 不要在 recovery 卡刷 ROM 或 OTA（会覆盖 boot_b）。
6. 这个 GSI 的 `bootctl` 连不上 vendor 的 AIDL 启动控制 HAL。安卓上切槽要用 `service call android.hardware.boot.IBootControl/default 9 i32 <slot>`（1 号事务是 getActiveBootSlot），模块的 `switch.sh` 已经这样改了（已提交到 fork `onlymykazari/tb321fu-android-armada-dualboot`）。
7. 刷 GSI 只在 fastbootd 里刷 system 再 `-w`，不要动 vbmeta（GSI 已签名）。
8. 任何会改变设备状态的操作，先确认证据支持；写入后必须验证。不可逆的操作（清 userdata、全量 9008）先和用户确认。
9. **更新 Armada 只走 OSTree/bootc**（runbook 第八节，2026-11-02 实测）：手动更新用 `bootc upgrade`，不要用 issue #4 的 `bootc switch`（会把签名策略降级）。先备份 `armada_esp`，更新后核对 `/proc/cmdline` 的 UUID、grub-sync 的 "in sync" 和 abl_a/abl_b 哈希。不要把 release 的 `userdata.simg` 写到 armada_root（清数据），也不要把 release 的 `super.img` dd 到 armada_esp（它的 grub.cfg 是 release 自己的根 UUID）。

## 访问方式
- Armada：`ssh -i ~/.ssh/tb321fu armada@<IP>`（IP 问用户）。sudo 密码要问用户，不要写进文件。需要往 sudo 命令灌 stdin 数据时，用 `SUDO_ASKPASS` 脚本加 `sudo -A`，脚本只放在 /tmp。
- Armada 进 fastboot：`sudo systemctl reboot --reboot-argument=bootloader`。
- Armada 更新体检 / 手动更新：`bash tools/armada-ota.sh <IP> [check|reboot|upgrade]`（check 不需要密码）。
- Android：GSI 默认开着 adb。root 要在 SukiSU 管理器 → Superuser → Shell 里临时授权，用完关掉。
- 9008：先 `QSaharaServer` 上传 `prog_firehose_ddr.elf`，再用 `fh_loader --memoryname=ufs --zlpawarehost=1`。只读检查用 `<read>` 标签的 XML，退出用 `--reset`。

## Windows / Git Bash 的坑
- `\\.\COM24` 会被吞掉反斜杠，fh_loader 和 QSaharaServer 的命令要写进 .bat 执行（用 Python 的 `chr(92)` 生成）。
- `adb push/shell` 涉及 `/sdcard` 这类路径时要加 `MSYS_NO_PATHCONV=1`。
- Python 在 Windows 上写的文本默认是 CRLF。给设备用的脚本和文件清单要用 `newline="\n"` 写，或者用 `tr -d '\r'` 处理。
- Windows 的 ping 会把“无法访问”算作已接收，判断设备在不在线要看 SSH 或 ARP。`adb devices` 可能卡住，命令前加 `timeout`。
