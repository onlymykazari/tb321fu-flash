# TB321FU 双系统：Android（A 槽）+ Armada（B 槽）

联想拯救者 Y700 三代 / Legion Tab Gen 3（TB321FU）的双系统知识库。2026-11-02 从 Armada 单系统迁移而来，原有数据全部保留，两个方向的一键切换都已实测。

内容：一、当前状态 → 二、切换 → **三、经验与踩坑记录（最重要）** → 四、日常注意 → 五、救援 → 六、从零重做 → 七、文件与工具 → 八、更新 Armada。

---

## 一、当前状态

| 位置 | 内容 |
|---|---|
| `userdata`（sda16，扇区 3613096–37167527，128 GiB） | 安卓数据，f2fs（首次开机由安卓格式化） |
| `armada_esp`（sda17，扇区 37167616–37233151，256 MiB） | Armada 的 GRUB FAT，由 `tb321fu-grub-sync` 维护 |
| `armada_root`（sda18，扇区 37233152–123365370，328.568 GiB） | Armada 的 btrfs，fsid **`61564dbd-2530-4afb-a751-444d437d867b`**；子卷 `root`（256）和嵌套的 Steam `steamapps`（257） |
| `super`（13 GiB） | ZUI 17.5.10.170 原厂动态分区；`system_a` 换成 Pixel tangorpro 15 GSI V6（1804 MiB） |
| `boot_a` | 9008 包顶层 boot.img = SukiSU Ultra GKI 重签名版（自带 root） |
| `init_boot_a` / `vendor_boot_a` / `dtbo_a` / `vbmeta_a` / `recovery_a` | 9008 包原样（已逐个核对哈希） |
| `boot_b` | Armada release v20261015.0544305 的 UEFI 加载器 |
| A 侧固件（LUN1 xbl_a 等，LUN4 *_a） | 9008 包原样 |
| B 侧固件（LUN2 xbl_b 等，LUN4 *_b） | 用 9008 写入的、和 A 侧相同的 31 个镜像（见第三节第 1 条） |
| 安卓侧 SukiSU 模块 | `reboot_to_armada`（已修版）、`vintf_vndk_fix` v1.1（开机 bind mount 框架 VINTF 清单，消除「系统内部出现问题」弹窗，见第三节第 14 条） |

磁盘 LUN0 总共 505304580096 字节，备份 GPT 在第 123365371 块。原来那块 userdata 的旧 fsid `751a1261-4d4a-45ec-8078-bc0089f6c743` 已随安卓清数据消失。

B 槽的 Armada 现在是 **20261028.903dbdb**（ghcr `build-20261028.903dbdb-40750905234-1`，2026-11-02 从 preview 4 用第八节的流程升上来的）。ostree 保留了 preview 4 作为回退部署，GRUB 菜单里是 "(previous)"，armada_esp 的槽 b 还放着它的内核。issue #4 的元数据已经补上，之后的更新走 Steam 即可。

关键哈希（sha256）：

| 文件 | 哈希 |
|---|---|
| 原厂 super 展开后整块（13 GiB） | `46e4ae1f71e9b15756accab2f91dcca305bb20f6c9bf624c51654bb75ef1f6c9` |
| boot.img（SukiSU GKI，包顶层） | `d06f5ab0837c1952414d7e73fce0880583d761294cabc64242d76a79cd406785` |
| vbmeta.img（包顶层） | `d4c8b06c96e1d6ac7d4c76fc6adac3fc7a962cbeeef04af4e6f4169c829947b1` |
| Armada release boot.img | `45f923bc3980a8ba6e12ce606c30b4b08c2de48047626648a3d1861c95d2a58f` |
| Armada release super.img | `321f877d68ced75a219d0595d247945f9d8b0c154068f88623e4a094190db1e6` |
| GSI（V6 erofs raw Signed） | `3d3c7690fbc8f216cee0bdb80fdfb8a8281eeb724dc9c8f2d51711babfaa0788` |
| vintf_vndk_fix.zip（v1.1，与仓库 `build.py` 产物逐字节一致） | `7a42358cd9a1b4ed97cf32e2db60db0b1d21fa0fd1df33c0270ccc0bb0b28da7` |
| 设备原始框架清单 manifest.xml.orig | `a2c9d8ec4c4f8c8122c3316c3f3234e0732cf4a4819b0edccdbb5e415fbac825` |

## 二、切换

- **安卓 → Armada**：SukiSU 管理器 → 模块 → “重启到 Armada” → ▶（也可以打开它的 WebUI）
- **Armada → 安卓**：桌面模式的桌面上点“重启到 Android”；命令行是 `sudo /var/lib/dualboot/reboot-to-android`
- **兜底**：在 fastboot 里执行 `fastboot set_active a`（安卓）或 `fastboot set_active b`（Armada）
- **进 fastboot**：关机后按住电源键 + 音量减；在 Armada 里可以用 `sudo systemctl reboot --reboot-argument=bootloader`；在安卓里用 `adb reboot bootloader`

---

## 三、经验与踩坑记录

每条按“现象 → 根因 → 怎么确认的 → 怎么解决 → 以后怎么做”写。

### 1. 这个 9008 包只写 A 侧固件，B 槽一切就掉 9008（最关键）

- **现象**：执行 `fastboot set_active b` 并重启后，设备直接掉进 9008（Qualcomm HS-USB QDLoader 9008）。
- **根因**：高通机型切槽时会同时切换 UFS 启动 LUN（A 侧 LUN1，B 侧 LUN2）。这个包的 `rawprogram2.xml` 里 `xbl_b`、`xbl_config_b` 等条目的 filename 为空，`rawprogram4.xml` 里所有 `*_b` 也都为空。所以 B 侧引导链从来没被写过，芯片读到空的 xbl_b 就进了 9008。
- **怎么确认的**：用 firehose 读取各分区第一个 4K：`xbl_a` 是 ELF，`xbl_b` 和 `abl_b` 全是 0，`boot_b` 与 release 的 boot.img 一致（这一项顺便证明分区定位是对的）。
- **怎么解决**：用 `tools/make_fill_b.py` 生成清单。规则是：每个 `_b` 分区用对应 `_a` 分区的镜像；跳过 `boot_b`；A 侧也没有镜像的跳过（qweslicstore）；包里缺文件的跳过（vm-bootsys.img）。这样一共 31 个分区（LUN2 4 个、LUN4 26 个、LUN0 1 个 vbmeta_system_b），通过 fh_loader 写入，不碰 GPT。写完把 31 个分区逐个回读，和源文件逐字节比对全部一致；`boot_b` 也整块回读，确认没被动过。
- **以后怎么做**：**只要再全量刷这个 9008 包，就必须在 `set_active b` 之前重新补一次 B 侧固件。** 套件教程默认 B 侧有固件，这个前提只对 OTA 过的机器成立。

### 2. B 槽的 UEFI 加载器会优先使用 super 开头的旧 GRUB FAT

- **现象**：补好 B 侧固件后切到 B 槽，起来的却是**旧系统**（内核参数是旧 UUID），而不是 armada_esp 指向的副本。
- **根因**：Armada 单系统把 GRUB FAT 写在了 super 开头。加载器会在所有 FAT 分区里找 GRUB，super 先被找到。套件作者没遇到这个问题，因为他是先装安卓，super 里没有 FAT。
- **怎么确认的**：`boot_b` 的 GPT 属性是 active、优先级 3、重试计数从 7 减到 6，说明确实是从 B 槽启动的；而 super 开头那块 FAT 的 grub.cfg 指向的是旧 UUID。
- **怎么解决**：迁移期间用 `tools/migrate/04_point_old_fat_to_copy.sh` 把旧 FAT 的 grub.cfg 也指向副本，并保留一个指向旧数据的备用项。最终把 super 恢复成原厂内容（开头 4 KiB 全为 0，没有 FAT 签名），之后 B 槽就稳定走 armada_esp 了。
- **以后怎么做**：super 里不能残留 FAT。

### 3. ABL 的 fastboot 刷大镜像不可靠

- **现象**：`fastboot -S 700M flash super super_stock.img` 的 16 段全部显示 OKAY，每段 Writing 只有几毫秒，但设备上 super 的哈希不对。
- **怎么确认的**：两边都按 256 MiB 分段算哈希。第 0~15 段（前 4 GiB）和第 41~51 段一致，**第 16~40 段（super 内 4 GiB 到 10.25 GiB）全部不一致**；抽查 system_ext_a、vendor_a、vendor_dlkm_a 的分区头也不对。证据保存在 `_work/super_pc_blocks.txt` 和 `_work/super_dev_blocks.txt`。
- **怎么解决**：进 Linux（Armada）后，把稀疏镜像从电脑经 SSH 流式传给 `tools/simg_write.py`，直接写入 `/dev/disk/by-partlabel/super`（13 GiB 用时 223 秒）。然后执行 `echo 3 > /proc/sys/vm/drop_caches` 清掉页缓存，再读整块算哈希，结果与期望值一致。
- **补充**：当初单系统安装时用 fastboot 刷的 16 GiB `userdata.simg` 是好的：迁移时 btrfs 读完了全部数据，没有报任何校验错误。出问题的只有 super，可能是 ABL 对这个分区有特殊处理。
- **以后怎么做**：大分区一律用 Linux 的 `dd`/`simg_write.py` 写，或在 fastbootd（用户态，可靠）里刷。**刷完必须校验哈希**。boot 这类小镜像用 ABL 刷没问题。

### 4. super 的分区表主备两份都在开头；原厂包里的 super 是“最小化”分块

- liblp 的布局是：开头 4 KiB 保留，几何信息 `gDla` 在 4096（主）和 8192（备），元数据头 `0PLA` 在 12288 起，主元数据和备份元数据**都在 super 开头**，末尾没有备份。所以 Armada 的 GRUB FAT 一旦写进 super 开头，fastbootd 就读不到分区表了，只能整块恢复原厂 super。
- 9008 包里的 `super_1.img`～`super_8.img` 是 super 里的非零片段，偏移记录在 `rawprogram_unsparse0.xml`，正好对应各逻辑分区（odm_a、product_a、system_a、system_dlkm_a、system_ext_a、vendor_a、vendor_dlkm_a）。片段之间的空隙在原厂镜像里是 0。
- `tools/super_compose.py` 把这些片段重组成稀疏镜像：空隙要写 FILL(0)，**不能用 DONT_CARE**，否则设备上残留的旧数据会保留下来；RAW chunk 的 total_sz 字段只有 32 位，所以每块限制在 64 MiB 以内。`tools/super_verify.py` 负责逐字节核对。
- 原厂分区组 `qti_dynamic_partitions_a` 上限 13 GiB，已用 10 GiB。GSI 刷入后 system_a 从 5064 MiB 缩成 1804 MiB。

### 5. 没法用 btrfstune 把副本改回旧 UUID，改成修改引用

- **现象**：`btrfstune -f -U <旧UUID>` 报 `fsid ... is not unique`。
- **根因**：新旧两个文件系统同时存在时，内核和 btrfs-progs 拒绝重复的 fsid，`-f` 只能绕过 received_uuid 那项检查，绕不过这一项。
- **怎么解决**：保留副本自己的 UUID，只改两处引用：副本里的 BLS 条目 `boot/loader/entries/ostree-1.conf`，以及 armada_esp 的 `/boot/grub/grub.cfg`（`tools/migrate/03_deploy_b.sh`）。ostree 的 `.origin` 文件里只有容器镜像引用，没有内核参数。以后系统更新会继承 BLS 里的内核参数，grub-sync 也从 BLS 生成配置，所以一直一致。
- **附带好处**：两个文件系统从来没有共用同一个 fsid，不存在“启动时挂错盘”的风险。

### 6. 这一版 Armada 的根是 composefs

- `/` 不是 btrfs，真实数据在只读挂载的 `/sysroot`（子卷 `root`）上，`/var` 是同一子卷的可写挂载。
- 所以预检、查 UUID 都要对 `/sysroot` 做。当时预检脚本用了 `/`，结果记下来的旧 UUID 是空的，后面是从 grub.cfg 和 btrfs 两处交叉核对取回来的。
- 缩容要经 `/var` 执行（`btrfs filesystem resize 124G /var`），快照也要建在 `/var` 下面。
- 嵌套子卷在 `/sysroot` 下的完整路径要带 ostree 前缀：`/sysroot/ostree/deploy/default/var/home/...`。`/var/home/...` 只是活动根里的路径，在 `/sysroot` 下面不存在。

### 7. btrfs 快照不包含嵌套子卷；receive 出来的子卷要加 -f 才能解除只读

- Steam 的 `steamapps` 是一个独立子卷（257），对 root 子卷做快照时不会把它带上，副本里只留下一个空目录。当时第一次 send/receive 后子卷列表里只有 root，是查看列表时发现的。解决办法是对它单独快照、send/receive，再放回原位（`tools/migrate/02_migrate_data.sh` 已经自动处理）。
- 新版 btrfs-progs 中，带 received_uuid 的子卷执行 `btrfs property set ... ro false` 会被拒绝，必须加 `-f`。
- 迁移结果：两次 scrub 共校验 35.70 GiB，零错误；Steam 库 19G 完整。

### 8. 旧系统关机时会重写 super 里那块 FAT 的 grub.cfg

- `tb321fu-grub-sync.service` 的 ExecStop 会在关机时按本系统的 BLS 重写 grub.cfg。所以在旧系统里改了 super FAT 的 grub.cfg 之后，必须让这一次关机跳过同步：在 `/run/systemd/system/` 下放一个临时覆盖，清空 ExecStop，重启后自动失效（已写进 `04_point_old_fat_to_copy.sh`）。
- 套件的 `dualboot-fix.sh` 要在**副本**里运行，它把 grub-sync 改到 armada_esp，把启动成功标记改为标 boot_b，配置写在 `/etc`，更新后保留。

### 9. 这个 GSI 的 bootctl 只认 HIDL HAL，套件的切换模块会失败

- **现象**：模块执行后报“切换失败：bootctl 返回错误”。这个脚本会先校验，所以失败时没有重启。
- **根因**：GSI 自带的 `/system/bin/bootctl` 只会找 HIDL v1.0 的启动控制 HAL（报 `Error getting bootctrl v1.0 module`）；ZUI 17.5 的 vendor 只注册了 AIDL 版 `android.hardware.boot.IBootControl/default`。
- **怎么解决**：直接用 `service call` 调用 AIDL HAL。事务码按接口声明顺序排列：1 getActiveBootSlot、2 getCurrentSlot、3 getNumberSlots、4 getSnapshotMergeStatus、5 getSuffix、6 isSlotBootable、7 isSlotMarkedSuccessful、8 markBootSuccessful、**9 setActiveBootSlot**、10 setSlotAsUnbootable、11 setSnapshotMergeStatus。其中 1/2/3/5/6/7 用只读调用逐个核对过（例如 getSuffix(0) 返回 `_a`），9 通过实际切换验证。
- 修改的文件是 `tb321fu-android-armada-dualboot/android/reboot_to_armada/switch.sh`：先试 bootctl，失败就改用 `service call ... 9 i32 1`，然后用 1 号调用复核下次启动槽是 1，复核不过就不重启。这个改动已经提交并推到 fork <https://github.com/onlymykazari/tb321fu-android-armada-dualboot>（commit `21dfc82`，本地 clone 的 origin 指向 fork，upstream 指向 CharlesGool）；上游还没有。
- 高通的 HAL 切槽时也会切换 UFS 启动 LUN，效果和 qbootctl 一样。

### 10. 刷 GSI：已签名、只刷 system；userdata 由安卓自己格式化

- 按 GSI 作者仓库（CharlesGool/TB321FU_PixelOS_15_Tangorpro）的说明：底包必须是 **ZUI 17.5.10.170**（蓝牙通话修复依赖这个版本的 vendor）；GSI 已签名，**不需要**关闭 vbmeta 校验，也**不需要**删除 product 等分区；只在 fastbootd 里刷 system，再 `-w`。
- fastbootd 报 `partition-type:userdata: raw`，所以 `fastboot -w` 只擦除，不会在电脑端格式化（会提示 “not automatically formatting”）。这是正常的：安卓首次开机会把 userdata 格式化成 f2fs，容量 128G。
- 这个 GSI 默认开着 adb，验证启动状态为 orange（已解锁，正常）。

### 11. SukiSU（KernelSU 系）的细节

- 内核里 KernelSU 的版本是 40740（`v4.1.2-d43e2505@builtin`）。管理器装的是 v4.1.3（40796），首页会提示“版本不一致”，但不影响 root 和模块。发布页上没有完全对应 40740 的管理器。
- `adb shell su` 默认不可用，要在管理器 → 超级用户 → Shell 里打开授权。用完记得关掉（2026-11-02 排查开机弹窗时又打开过一次）。
- 模块安装：管理器 → 模块 → “+” → 选择 zip → 重启后生效；root shell 里也可以 `ksud module install <zip>`。
- **这版 ksud（4.1.2）不会自己挂载模块的 `system/` 目录**：挂载交给“元模块（metamodule）”，没装元模块就静默跳过，管理器照样显示“已启用”，post-fs-data 日志里根本没有挂载这一步。带 `system/` 文件的模块要么装元模块，要么在 `post-fs-data.sh` 里自己 `mount -o bind`（第 14 条就是这么做的）。
- ROM 里没有 `logcat` 二进制，但 SukiSU 会把每次开机的 dmesg / logcat 存到 `/data/adb/ksu/log/`（`logcat.log`、`dmesg.log`，上一次的带 `.old`），ksud 各阶段的日志也在里面。
- 内核带 SuSFS（dmesg 有 `susfs:` 行），但没装 `ksu_susfs` 工具，默认不会对 system_server 卸载模块挂载。

### 12. 9008 / firehose 操作细节

- **进 9008**：关机后按住音量加，同时插入 USB 线（用长边接口）。
- 先用 `QSaharaServer.exe -p \\.\COMxx -s 13:prog_firehose_ddr.elf` 上传编程器，再用 `fh_loader.exe --port=\\.\COMxx --memoryname=ufs --zlpawarehost=1 ...` 操作。
- 如果 fh_loader 提示 “target is in SAHARA mode”，说明还没上传编程器。如果 QSaharaServer 读到 0 字节，但 fh_loader 能正常读写，说明编程器早就加载过了，直接用 fh_loader 即可。
- 退出 9008：`fh_loader ... --reset`，大约 10 秒后重启。只读检查用 `<read>` 标签的 XML，绝不会写入。
- 端口被 QPST/QFIL 占用时会报 “Error setting com port timeouts”。
- **Git Bash 会把 `\\.\COM24` 吞成 `\.\COM24`**，也会报同样的错。所以命令要写进 .bat 文件再执行（用 Python 生成，反斜杠用 `chr(92)`）。

### 13. 工具链与操作习惯

- 写 GPT 备份到磁盘末尾要用 `seek`（输出偏移），**不是 `skip`**。当时写错了一次，是写后的哈希校验拦下来的。所以**所有写入都要配校验**：cmp、sha256 或回读比对，读之前先清页缓存。
- 在 Git Bash 里 `adb push` / `adb pull` / `adb shell` 把 `/sdcard/...`、`/system/...` 这类设备路径作为独立参数时，会被转换成 `C:/Program Files/Git/...`，要加 `MSYS_NO_PATHCONV=1`；加了之后本地路径不能再写 `/tmp`，要写 `C:/...`（Windows 版 adb 不认 MSYS 路径）。多条 root 命令直接写成脚本 push 到 `/data/local/tmp` 再 `su -c 'sh ...'`，省得套引号。
- 通过 SSH 往 `sudo` 命令灌数据时，`sudo -S` 会和数据流抢 stdin。改用 `SUDO_ASKPASS=<回显密码的脚本> sudo -A`。
- Windows 的 ping 会把路由器回的“无法访问”也算作“已接收”，不能用来判断设备在不在线。要看 SSH 或 ARP 表。
- `adb devices` 有时会卡在启动 adb 服务，命令前要加 `timeout`。
- 在 Armada 里编译 qbootctl：`~/dualboot/armada/build-qbootctl.sh` 用 rootless podman 拉 Alpine 容器编译，需要联网。
- GitHub 账号开了“禁止命令行推送暴露私人邮箱”，提交邮箱要用 `30022022+onlymykazari@users.noreply.github.com`（2026-11-02 已写进全局 git 配置），否则推送报 GH007。

### 14. GSI 每次开机弹「安卓系统内部出现问题，请联系设备制造商」

- **现象**：开机后几秒弹出该对话框，每次必弹，点掉后一切正常。
- **根因**：AOSP `Build.isBuildConsistent()` 在 Treble 设备上只做 VINTF 兼容性校验（`VintfObject.verifyBuildAtBoot()`），不查 AVB，也走不到 system/vendor 指纹比对。ZUI 17.5 的 vendor 冻结在 Android 14（`ro.vndk.version=34`），它的设备兼容矩阵要求框架声明 `vendor-ndk 34`；而这个 GSI 的 `/system/etc/vintf/manifest.xml` 一个 `<vendor-ndk>` 都没有（Pixel 自家 Android 15 vendor 不需要 VNDK，移植时漏了）。GSI 其实带着 `com.android.vndk.v30`～`v34` 五个 APEX 且全部激活、linker 也在用，所以补上声明是如实修正，不是绕过校验。
- **怎么确认的**：`adb shell vintf legacy | tail -9`（免 root）只有一项不过：`Framework HAL Manifest <==> Device Compatibility Matrix? INCOMPATIBLE, Vndk version 34 is not supported. Supported versions in framework manifest are: []`。开机日志 `/data/adb/ksu/log/logcat.log` 里对应两行：`E Build: Vendor interface is incompatible, error=1`、`E ActivityTaskManager: Build fingerprint is not consistent, warning user`。
- **怎么解决**：模块 `vintf_vndk_fix` v1.1（源码在 `tb321fu-vintf-vndk-fix/`，已发布到 GitHub，见第七节）。清单 = 设备原始文件 + 5 个 `<vendor-ndk>` 块（30–34，diff 正好 15 行）；`post-fs-data.sh` 开机时把它 `mount -o bind` 到 `/system/etc/vintf/manifest.xml`，结果写在模块目录的 `last_run.log`。装完重启后 `vintf legacy` 四行全 GOOD，开机日志里那两行消失。
- **弯路**：第一版只放了 `system/etc/vintf/manifest.xml` 指望模块覆盖，管理器显示已启用，但 init / zygote / system_server 三个命名空间里都没有挂载——这版 ksud 不挂模块 `system/`（第 11 条）。改脚本前先以 root 现场 bind 了一次做预演，`chroot /proc/$(pidof system_server)/root /system/bin/vintf legacy` 也 GOOD，说明 init 命名空间里的挂载会传播到 system_server，测完即卸载。
- **以后怎么做**：换 GSI 版本前先卸载这个模块，新版本先跑 `vintf legacy` 看还缺不缺。从源码排除的无效偏方：刷 vbmeta `--disable-verification`、resetprop 对齐 system/vendor 指纹、清数据、藏 root。

---

## 四、日常注意

- **不要在 recovery 卡刷 ROM 或 OTA**：A/B 机型卡刷会写到另一个槽，`boot_b` 会被覆盖。万一被覆盖，用 `fastboot flash boot_b boot.img` 写回（Armada release 的 boot.img，preview 4 和 5 相同，sha256 `45f923bc…`；本地不再保留，从 `ASSETS.md` 第二节的链接下载并核对；小镜像，fastboot 可靠）。
- **Armada 的日常更新**：Steam 后台下载 → 提示时重启（或平时正常重启也会应用）。重启后在电脑上跑一条 `bash tools/armada-ota.sh <IP>` 体检（不需要密码，十几秒）；全是 OK 就完事。要手动触发更新用 `bash tools/armada-ota.sh <IP> upgrade`（会问 sudo 密码，然后升级 + 重启 + 体检一条龙）。原理和出问题时的手动流程见**第八节**。armada_esp 在 2026-11-02 更新后只剩 22 MB，体检脚本不查这项（要 root），偶尔按第八节第 1 步看一眼。双系统配置在 `/etc/systemd/system/*.d/50-dualboot.conf`，更新后保留（已实测）。
- 本机是 BOE 屏。如果是 CSOT 屏：`sudo SUPER=/dev/disk/by-partlabel/armada_esp tb321fu-panel csot`。
- Armada 的 SSH 已开启，默认密码 `armada` **要改**。电脑公钥 `~/.ssh/tb321fu` 已加入 Armada 的 `~/.ssh/authorized_keys`，不需要就删掉那一行。
- 查看槽位：Armada 里用 `sudo /var/lib/dualboot/qbootctl` 或 `sudo bash tools/slotattr.sh`。GPT 属性位：48–49 优先级，50 active，51–53 重试次数，54 已成功，55 不可启动。
- **换 GSI 版本前先卸载 `vintf_vndk_fix` 模块**：它整文件覆盖 `/system/etc/vintf/manifest.xml`，新版本的清单可能有新增条目。刷完先 `adb shell vintf legacy | tail -9` 看新版本还缺不缺，再决定装不装回去。

## 五、救援

- **Armada 起不来**：`fastboot set_active a` 先回安卓，Armada 的数据在 armada_root 上不受影响。GRUB FAT 坏了的话，优先按第八节第 6 步写回 `_work\backup\armada_esp.pre-ota.img`（grub.cfg 已经是本机 UUID）；或者在 Linux 里把 release 的 super.img（下载见 `ASSETS.md`）`dd` 到 armada_esp，再把 grub.cfg 里的 `root=UUID=` 改成 `61564dbd-2530-4afb-a751-444d437d867b`。
- **安卓起不来 / 想重刷 GSI**：
  ```bat
  REM 先解压工作区根目录的 Pixel-tangorpro-15_TB321FU_V6-faceunlock_erofs_raw_Signed.zip 得到 .img，核对 _work\android\*.img.sha256
  fastboot set_active a
  fastboot reboot fastboot
  fastboot flash system Pixel-tangorpro-15_TB321FU_V6-faceunlock_erofs_raw_Signed.img
  fastboot -w
  fastboot reboot
  ```
  `-w` 会清掉 `/data/adb`，之后要重装 SukiSU 管理器、`reboot_to_armada.zip` 和 `vintf_vndk_fix.zip`（都在 `_work\android\`）。
- **super 坏了**（fastbootd 读不到分区表等）：先进 Armada，然后在电脑上执行：
  ```sh
  # super_stock.img（11 GB）本地已清理：先解压 9008 包，用 tools/super_compose.py 重建到 _work/，再 super_verify.py 核对（命令见 ASSETS.md 第三节）
  cat _work/super_stock.img | ssh -i ~/.ssh/tb321fu armada@<IP> "SUDO_ASKPASS=/tmp/ap.sh sudo -A python3 /tmp/simg_write.py /dev/disk/by-partlabel/super"
  # 事先把 tools/simg_write.py 传到 /tmp，并建好 /tmp/ap.sh（内容: #!/bin/sh + echo <密码>，chmod 700）
  # 写完在设备上执行: sync; echo 3 > /proc/sys/vm/drop_caches; sha256sum /dev/disk/by-partlabel/super
  # 结果应为 46e4ae1f71e9b15756accab2f91dcca305bb20f6c9bf624c51654bb75ef1f6c9
  ```
  之后按上一条重刷 GSI。
- **boot_a 被覆盖**：`fastboot flash boot_a _work\android\boot.img`。
- **B 槽一切就掉 9008**：说明 B 侧固件又空了（多半是全量刷过 9008 包）。按第三节第 1 条补齐：在 `_work\qfil\tool` 里依次执行 QSaharaServer、`fh_loader --sendxml=fill_b_lun2.xml,fill_b_lun4.xml,fill_b_lun0.xml`、`--reset`。
- **需要线刷又想保住 Armada**：不要用原版 `rawprogram0.xml`，它会重建原厂 GPT，armada_esp 和 armada_root 都会消失。用 `_work\rawprogram0_nogpt.xml`，并且不要加载 `patch0.xml`（里面的补丁会把 userdata 改回原厂大小）。
- **恢复原来的单系统分区布局**：原始 GPT 是 `_work\gpt_primary.bin` / `_work\gpt_backup.bin`；当前布局是 `_work\new_primary.bin` / `_work\new_backup.bin`。写回方法同第六节 A 的第 2 步。

## 六、从零重做

### A. 已经是 Armada 单系统，要保数据（这次实际走通的流程，已修正）

1. **补 B 侧固件**（9008，见第三节第 1 条）。必须在第一次 `set_active b` 之前做。
2. **Armada 里，以 root 运行**：
   - `tools/migrate/00_preflight.sh`：只读检查，并把 GPT 备份到 /root；
   - 在电脑上：`python tb321fu-android-armada-dualboot/tools/gpt_split.py gpt_primary.bin gpt_backup.bin new_primary.bin new_backup.bin --android-gib 128`；
   - `01_shrink_and_gpt.sh new_primary.bin new_backup.bin`；
   - `02_migrate_data.sh`（先关掉 Steam）；
   - `03_deploy_b.sh boot.img super.img`（release 镜像，必须和当前系统同版本）；
   - `04_point_old_fat_to_copy.sh`。
3. `sudo systemctl reboot --reboot-argument=bootloader` 进 fastboot → `fastboot set_active b` → `fastboot reboot`。启动后确认 `/proc/cmdline` 里是副本的 UUID、`/sysroot` 来自 armada_root。然后运行套件的 `armada/dualboot-fix.sh`，输出里要有 `in sync`。可选：`build-qbootctl.sh` 加 `install-reboot-to-android.sh`。
4. **还在副本 Armada 里**：用 `simg_write.py` 把原厂 super 写回去并校验哈希（见第五节），再把包里的 boot.img 用 `dd` 写到 boot_a 并 cmp。重启一次，确认 B 槽改走 armada_esp 也能正常启动。
5. 进 fastboot → `fastboot set_active a` → `fastboot reboot fastboot` → `fastboot flash system <GSI>` → `fastboot -w` → `fastboot reboot`。**`-w` 是唯一不可逆的一步**，前面所有步骤都能用 GPT 备份退回。
6. 安卓：装 SukiSU 管理器，安装 `_work\android\reboot_to_armada.zip`（已修版）和 `_work\android\vintf_vndk_fix.zip`，实测两个方向的切换，并确认开机不再弹「系统内部出现问题」（`adb shell vintf legacy | tail -4` 全 GOOD）。

### B. 全量刷过 9008 包之后从头装（不保留 Armada 数据）

1. 全量 9008 刷包，然后在同一次 9008 会话里补 B 侧固件（第三节第 1 条）。
2. 安卓：fastbootd 刷 GSI → `-w` → 开机 → 装 SukiSU 管理器 → 给 root。
3. 按套件 README 第 2~4 步拆分 userdata（会清空安卓数据，所以放在设置安卓之前）。
4. fastboot 刷 `boot_b`、`armada_esp`（小镜像，可靠），以及 `armada_root`（16 GiB 的 userdata.simg）。Armada 首次开机后跑一次 `btrfs scrub start -B /sysroot` 检查 armada_root；有错误就改在 Linux 里重写。
5. `set_active b` → Armada 首次开机 → `dualboot-fix.sh` → qbootctl 快捷方式。安卓那边装修好的模块和 `vintf_vndk_fix.zip`。
   这种情况下 super 是原厂内容，没有 FAT，不会遇到第三节第 2 条的问题。也不需要改 UUID：armada_root 用的就是 release 镜像自带的 UUID，和 grub.cfg 一致。

## 七、文件与工具（D:\Projects\TB321FU-Flash）

仓库：<https://github.com/onlymykazari/tb321fu-flash>（公开；大文件不入库）。每个大文件在哪、哈希、本地留没留，见 **`ASSETS.md`**；本机专属的二进制备份（armada_esp、GPT、boot/vbmeta、模块 zip）在 <https://github.com/onlymykazari/tb321fu-assets>（release `20261102`，不要公开），9008 包和 GSI zip 存在自己的网盘。2026-11-02 整理：`super_stock.img`、两个 release 目录的镜像、解压出的 GSI `.img` 已从本地删除，需要时按 ASSETS.md 重建或下载，**用前核对哈希**。

| 路径 | 用途 |
|---|---|
| `tools/make_fill_b.py` | 从 rawprogram*.xml 生成补 B 侧固件的清单，和当时实际刷入的 31 条逐条对过，完全一致 |
| `tools/super_compose.py` / `super_verify.py` | 把原厂 super 片段重组为稀疏镜像 / 逐字节核对 |
| `tools/simg_write.py` | 在 Linux 里把稀疏镜像从 stdin 写入块设备（代替 ABL 的 fastboot） |
| `tools/slotattr.sh` | 读取 boot_a / boot_b 的 A/B 槽 GPT 属性 |
| `tools/migrate/00..04_*.sh` | 迁移脚本。按实际成功执行的命令整理，修正了当时的错误，但没有作为整体重新跑过 |
| `_work/super_stock.sha256` | 原厂 super 写入设备后整块的 sha256（`46e4ae1f…`）。11 GB 的 `super_stock.img` 本体已清理，需要时解压 9008 包后 `python tools/super_compose.py --images <包>/image --rawprogram <包>/image/rawprogram_unsparse0.xml -o _work/super_stock.img`，再 `super_verify.py` 核对 |
| `_work/qfil/tool/` | fh_loader、QSaharaServer、编程器、`fill_b_lun*.xml` 和所需镜像（本地保留，随时可用；二进制全部来自 9008 包，清单和 `step*.bat`、`read_*.xml` 已入库） |
| `_work/android/` | boot.img、vbmeta.img、SukiSU 管理器 APK（4.1.3）、`reboot_to_armada.zip`（已修版）、`vintf_vndk_fix.zip`（v1.1 成品，哈希见第一节）、GSI 的 `.img.sha256`。GSI 的 `.img` 已清理（解压根目录的 zip 即得）；设备原始框架清单在 `tb321fu-vintf-vndk-fix/original/manifest.xml` |
| `_work/release/SHA256SUMS` | Armada v20261015.0544305（preview 4）的哈希表。boot.img / super.img 本地已清理，从 <https://github.com/enij90/armada-tb321fu/releases/tag/v20261015.0544305> 下载 |
| `_work/release_v20261024/SHA256SUMS` | Armada v20261024.0146e89（preview 5）的哈希表：boot.img、super.img、userdata.simg.part1~7（9 个文件当时全部校验通过）。镜像本地已清理，从 <https://github.com/enij90/armada-tb321fu/releases/tag/v20261024.0146e89> 下载。boot.img 与 preview 4 相同；super.img 里 GRUB 二进制与 preview 4 相同。userdata 分片合并 `copy /b userdata.simg.part* userdata.simg`，合并后哈希 `6fe4c117…`。**只用于从零安装，不是更新手段** |
| `_work/backup/` | 更新前的 armada_esp 备份（第八节第 2 步生成） |
| `tools/ghcr_layers.py` | 更新前在电脑上跑：查 ghcr 上 `:latest` 的第一层是否和设备上的 preview 4 相同，决定 issue #4 的原地修复能否直接用（元数据修好后不再需要） |
| `tools/armada-ota.sh` | 日常更新工具：`<IP>` 体检（无需密码）、`<IP> reboot` 重启应用更新、`<IP> upgrade` 手动 `bootc upgrade` + 重启 + 体检。检查项对应第八节第 5 步里不需要 root 的部分 |
| `_work/gpt_*.bin`、`_work/new_*.bin` | 分区表备份（原始布局 / 当前布局） |
| `_work/rawprogram0_nogpt.xml` | 不碰 GPT 的 LUN0 刷写清单 |
| `_work/super_pc_blocks.txt`、`super_dev_blocks.txt` | ABL 刷写出错的分段哈希证据 |
| `tb321fu-android-armada-dualboot/` | 双系统套件（独立 git 仓库，不入本仓库）；`switch.sh` 的修复已提交到 fork `onlymykazari/tb321fu-android-armada-dualboot`（origin），upstream 是 CharlesGool，已提上游 PR #2 |
| `tb321fu-vintf-vndk-fix/` | 消除开机弹窗的 SukiSU 模块源码（第三节第 14 条），已发布到 <https://github.com/onlymykazari/tb321fu-vintf-vndk-fix>（Release v1.1 附成品 zip）。`python build.py` 打包，产物与实机验证版逐字节一致；`original/manifest.xml` 是设备原始清单，`diff` 它和 `system/etc/vintf/manifest.xml` 正好 15 行 |
| `armada-tb321fu/` | enij90 上游的本地 clone 已删（2026-11-02，无本地修改）。预防性 fork 在 <https://github.com/onlymykazari/armada-tb321fu>；要查源码 `git clone https://github.com/enij90/armada-tb321fu` 即可 |
| `AGENTS.md` | 给以后在这个目录里工作的 AI 看的要点摘要 |
| `ASSETS.md` | 资产清单：每个大文件的位置（私有备份 release / 公开直链 / 怎么重建）、大小、sha256、本地保留状态 |
| `README.md` / `README.zh-CN.md` | 仓库说明 |

## 八、更新 Armada（双系统下）

2026-11-02 按这个流程实际执行了一次：preview 4 → 20261028.903dbdb，一次成功，记录在本节末尾的"实际执行记录"。之后的常规更新直接走 Steam（后台下载 → 重启应用）；需要手动更新或再遇到元数据问题时按这里走。执行时按顺序走，每一步的预期结果都写在旁边；对不上就停。

### 背景

- 设备上的 Armada 是 **preview 4**（v20261015.0544305，ghcr 构建 tag `build-20261015.0544305-38757030059-1`）。preview 4 及更早的安装镜像缺少 ostree 容器元数据（`ostree/container/blob/…` 这些 ref），`bootc status` 报 `Missing base image ref ostree/container/blob/sha256_3A_53c6f11a…`，更新检查在到达仓库之前就失败了，所以 **Steam 的系统更新从来没有工作过**（作者仓库 issue #4，preview 5 的 release note 也明说了）。
- 真正的更新通道是容器镜像 **`ghcr.io/enij90/armada-tb321fu:latest`**（main 每次 push 构建一次；2026-11-02 查到 `latest` = `build-20261028.903dbdb`，manifest `sha256:6d8a5de5…`，内容见仓库 README 的 "Recent changes"：DP 音频、陀螺仪、蓝牙、USB-C、Waydroid）。GitHub release 页的 boot.img / super.img / userdata.simg **只用于全新安装**；`userdata.simg` 写到 armada_root 会清掉全部数据。
- 作者给的原地修复（issue #4）：先用 `ostree container image pull` 拉一次 `:latest`，把缺的 ref 记进仓库，再 `bootc switch :latest`。作者自己没在受影响的机器上测过。已经在电脑上查清它为什么能成立：bootc 只要求**已启动部署的第一层** blob ref 存在；`53c6f11a…` 正是 preview 4 的第一层，而当前 `:latest` 的第一层与之相同（前两层相同，128 层里共享 50 层）。只要作者在我们动手前没换底层镜像，这个修复就会成功。**动手前用 `python tools/ghcr_layers.py` 再查一次**；如果它报 DIFFERENT，把第 3 步第一条命令里的 `:latest` 换成 `:build-20261015.0544305-38757030059-1`（preview 4 自己的镜像，精确补齐），其余不变。

### 更新会动什么，不会动什么

| 部件 | OTA 是否触及 | 依据 |
|---|---|---|
| `armada_root`（btrfs） | 是 | 新增一个 ostree 部署（几 GB），旧部署保留作回退。`/var`、Steam 库、嵌套子卷不动；`/etc` 三方合并 |
| `armada_esp`（GRUB FAT） | 是，只有内核相关文件 | 关机时 `ostree-finalize-staged` → `tb321fu-boot-finalize` → `grub-sync`：把新内核 / initramfs / DTB 写进空闲槽（FAT 里是 `Image-a`/`Image-b` 双槽），重写 `grub.cfg`（新版默认 + 旧版 "(previous)"）。它先把 grub.cfg 指向保留槽再写另一槽，中断也能启动；同步失败会自动 `bootc rollback`。GRUB 二进制从不被更新 |
| `boot_b`（UEFI 加载器） | 否 | preview 4 → preview 5 的 boot.img 哈希相同（`45f923bc…`） |
| `abl_a` / `abl_b` | 否 | 新版带 `openabl-updater`，"始终开启"。但它只作为 `armada-bootimg-sync.service` 的 ExecStop 挂载，而这个 unit 在 TB321FU 上被 `20-tb321fu.conf` 的 `ConditionFirmware=!device-tree-compatible(lenovo,tb321fu)` 跳过，根本不会运行。就算被调用，原厂 ABL 的哈希不在它的目录里、设备也报不出 OpenABL 版本（ESRT / efivars），脚本会 exit 7 拒绝写入。更新前后比对 abl 哈希兜底 |
| 安卓侧 `boot_a` / `super` / `userdata` / `vbmeta` | 否 | |
| `/etc/systemd/system/*.d/50-dualboot.conf` | 保留 | `grub-sync`、`boot-finalize`、三个相关 service、`bootimg-args`、`tb321fu-panel` 从 v20261015 到 main **一行没改**，`SUPER=` 环境变量机制不变。`ostree-finalize-staged.service` 也有同样的覆盖，所以关机阶段的同步也指向 armada_esp |
| `armada-esp-rename`（会 `sgdisk --change-name`） | 不触发 | 只在磁盘上同时有 `ARMADA_BOOT`、`ARMADA_ROOT` 和一个 `ROCKNIX`/`ARMADA` 分区时才动，TB321FU 一个都没有。preview 4 里就有这个脚本 |
| 内核参数 | 继承 | ostree 新部署从当前部署的 BLS 复制 `root=UUID=61564dbd…`（第三节第 5 条）；第 5 步用 `/proc/cmdline` 验证 |

空间：FAT 256 MiB，一个槽约 111 MiB（preview 5 实测 Image 64 MB + initramfs 52 MB），双槽后约剩 20 MB。镜像约 6.8 GB 压缩层，armada_root 空间充足。

### 步骤

设备切到 Armada，桌面模式终端或 SSH（`<IP>` 问用户）。全程接电源，不要断电。

**0. 电脑上确认前提**

```sh
python tools/ghcr_layers.py        # 最后一行要是 OK
```

**1. 只读预检（Armada 里）**

```sh
cat /proc/cmdline                                   # root=UUID=61564dbd-… ostree=/ostree/boot.1/default/<hash>/0
sudo bootc status                                   # 预期报 Missing base image ref（就是 issue #4）
sudo ostree admin status                            # 一个部署 default <commit>.0，origin 指向 ghcr …:latest
systemctl cat tb321fu-grub-sync.service ostree-finalize-staged.service tb321fu-mark-boot-successful.service | grep -B1 -A3 50-dualboot
                                                    # 三个覆盖都在
systemctl show armada-bootimg-sync.service -p ConditionResult -p ActiveState   # ConditionResult=no
df -h /sysroot /var
sudo bash -c 'l=$(losetup -f --show -r /dev/disk/by-partlabel/armada_esp); mkdir -p /run/esp-ro; mount -o ro "$l" /run/esp-ro; ls -la /run/esp-ro; echo; cat /run/esp-ro/.slot-*.id; echo; df -h /run/esp-ro; echo; cat /run/esp-ro/boot/grub/grub.cfg; umount /run/esp-ro; losetup -d "$l"'
#   预期：Image-b / initrd-b.img / dtb-b.dtb / dtb-b-csot.dtb / .slot-b.id（安装镜像布局已迁移到 b 槽），没有 dtb/ 目录；
#   可用空间 ≥ 120 MiB；grub.cfg 第一行注释是 "Written by tb321fu-grub-sync"，里面 root=UUID=61564dbd…
sudo /var/lib/dualboot/qbootctl                     # boot_b: active + successful（或 sudo bash slotattr.sh）
sudo sha256sum /dev/disk/by-partlabel/abl_a /dev/disk/by-partlabel/abl_b | tee /var/tmp/abl.pre.sha256
```

**2. 备份（都很小，几秒钟）**

```sh
sudo dd if=/dev/disk/by-partlabel/armada_esp of=/var/tmp/armada_esp.pre-ota.img bs=1M status=none && sha256sum /var/tmp/armada_esp.pre-ota.img
sudo cp -a /boot/loader/entries /var/tmp/bls.pre-ota
# 电脑上也留一份（256 MiB）：
#   scp -i ~/.ssh/tb321fu armada@<IP>:/var/tmp/armada_esp.pre-ota.img _work/backup/
# 可选的最后一道保险：根子卷只读快照（COW，秒级；验证稳定一周后删掉，否则一直占着旧数据块）
sudo mkdir -p /run/top && sudo mount -o subvolid=5 /dev/disk/by-partlabel/armada_root /run/top \
  && sudo btrfs subvolume snapshot -r /run/top/root /run/top/root-pre-ota-$(date +%Y%m%d) && sudo umount /run/top
```

**3. 补元数据，升级到最新构建**

```sh
sudo unshare -m sh -c 'mount -o remount,rw /sysroot && ostree container image pull /sysroot/ostree/repo ostree-unverified-registry:ghcr.io/enij90/armada-tb321fu:latest'
sudo bootc status                                   # 现在应正常显示，不再报 Missing base image ref；booted.imageDigest 应是 preview 4 的 c2369862…
sudo bootc upgrade                                  # 不是 bootc switch，见下面
sudo bootc status                                   # staged.version = 新版本，imageDigest 和 ghcr_layers.py 打印的 latest manifest 一致
sudo ostree admin status                            # 两个部署：staged（新）+ booted（旧）
```

- 拉取约 6.8 GB，看网速；中途断了直接重跑，ostree 按层续传。拉取时日志里没有进度（没接 tty），用 `sudo ostree refs --repo=/sysroot/ostree/repo | grep -c ostree/container/blob/` 看已导入层数（满 128）。
- **用 `bootc upgrade`，不要照 issue #4 用 `bootc switch`**：origin 本来就是 `ostree-image-signed:docker://…:latest`，`bootc switch --enforce-container-sigpolicy …:latest` 会说 "Image specification is unchanged" 然后什么都不做；作者那条不带参数的 `bootc switch` 之所以"有效"，是因为它把签名策略从 containerPolicy 降成了 unverified，规格变了才触发部署——这会把 origin 永久降级成不校验签名。本机 `/etc/containers/policy.json` 对 `ghcr.io/enij90/armada-tb321fu` 有严格的 sigstore 策略（作者公钥 `/etc/pki/containers/armada-tb321fu.pub`），`bootc upgrade` 读 manifest 时会走这个校验。
- `bootc upgrade --check` 在手动拉取之后会说 "No changes"，它指的是"没有新层要拉"，不是"没有新版本"，不用管。
- stage 之后看新部署目录的 `/etc`（`/ostree/deploy/default/deploy/<新csum>.0/etc`）里**没有** `50-dualboot.conf` 是正常的：ostree 2026.4 把 `/etc` 三方合并推迟到关机 finalize 时做（machine-id 也是空的，整个目录和 `/usr/etc` 一样）。重启后再查。
- 想提前确认 staged 的内核参数：`sudo grep -a -o "root=UUID=[0-9a-f-]*" /run/ostree/staged-deployment`（`ostree=` 那项会在 finalize 时重算，显示旧值正常）。
- 万一 `bootc status` 在拉取后还是报 Missing base image ref，不经 bootc 的备用路径（没实测过）：
  ```sh
  R=/sysroot/ostree/repo
  REF=$(sudo ostree refs --repo=$R | grep '^ostree/container/image/' | grep latest)
  C=$(sudo ostree rev-parse --repo=$R "$REF")
  printf '[origin]\ncontainer-image-reference=ostree-image-signed:docker://ghcr.io/enij90/armada-tb321fu:latest\n' > /tmp/origin
  sudo ostree admin deploy --stage --os=default --origin-file=/tmp/origin "$C"    # 内核参数自动从当前部署继承
  ```

**4. 重启应用**

```sh
sudo systemctl reboot        # 或按 Steam 的提示重启。关机阶段跑 finalize + grub-sync，可能多等十几秒
```

Lenovo logo 后 3 秒的 GRUB 菜单应有：新版本（默认）、旧版本 "(previous)"、"(CSOT panel)"、Power off。GRUB 之后自动重启一两次是已知现象。

**5. 启动后验证**

```sh
cat /proc/cmdline                                   # root=UUID=61564dbd-… 且 ostree= 指向新部署的 hash
sudo bootc status                                   # Booted = latest；Rollback = 旧版本
journalctl -b -1 -o cat --no-pager | grep -E "tb321fu-grub-sync|boot-finalize"   # 上次关机：writing … to slot a / in sync（日志不持久就没有）
journalctl -b -u tb321fu-grub-sync -u tb321fu-mark-boot-successful -o cat --no-pager   # 本次启动 in sync；成功标记无报错
sudo sha256sum /dev/disk/by-partlabel/abl_a /dev/disk/by-partlabel/abl_b | diff - /var/tmp/abl.pre.sha256 && echo "ABL unchanged"
sudo /var/lib/dualboot/qbootctl                     # boot_b active + successful；boot_a 不变
systemctl status armada-bootimg-sync.service        # 仍是 condition failed / inactive
# 功能抽查：Wi-Fi、触摸、扬声器、睡眠唤醒、G9、Steam。Steam → 设置 → 系统：能正常检查更新
# 最后切回 Android 再切回 Armada 一次，确认两个方向的切换都正常
```

**6. 回滚**

- 临时：GRUB 里选 "(previous)"，旧槽文件和旧 BLS 条目都还在。
- 永久回旧版本：`sudo bootc rollback`，下次关机 grub-sync 会把默认项指回旧槽。bootc 不可用就 `sudo ostree admin undeploy 0`（删掉新部署；0 是当前默认的那个，先 `ostree admin status` 看清楚）。
- GRUB FAT 坏了：Armada 里 `sudo dd if=/var/tmp/armada_esp.pre-ota.img of=/dev/disk/by-partlabel/armada_esp bs=1M conv=fsync`，再校验哈希。进不了 Armada 就在 fastboot 里 `fastboot flash armada_esp _work\backup\armada_esp.pre-ota.img`（256 MiB 小镜像，ABL 的 fastboot 可靠）。这份镜像里是更新前的 grub.cfg + preview 4 的 b 槽，配合保留的旧部署能直接启动。
- 完全起不来：`fastboot set_active a` 回安卓，Armada 数据无损，再按上面恢复。
- 最后手段（根子卷快照）：挂 `subvolid=5`，`mv root root-broken && btrfs subvolume snapshot root-pre-ota-<日期> root`，GRUB 选 "(previous)" 启动，下次关机 grub-sync 会自动收敛。

### 注意

- 更新后 boot_b 已经标记 successful，ABL **不会**因为内核起不来而自动退回安卓（这是 dualboot-fix 的设计），失败时靠 GRUB "(previous)" 或 `fastboot set_active a`。
- 以后每次更新（Steam 后台下载 → 重启应用）都走同一条 grub-sync 路径。更新后在电脑上跑 `bash tools/armada-ota.sh <IP>`，它查的就是第 5 步里不需要 root 的那些项（版本、根 UUID、槽位、上次关机 grub-sync 有没有 in sync / 有没有回滚、boot_b 成功标记、ABL 更新器仍被跳过、failed unit）。
- FAT 只剩约 20 MB 余量。哪天内核 + initramfs 再涨 20 MB，双槽就放不下：grub-sync 失败并自动回滚，更新卡住但系统照常。那时把 FAT 里 "(previous)" 那个槽的 `Image-x`、`initrd-x.img`、`dtb-x*.dtb`、`.slot-x.id` 删掉腾地方，再重启一次。
- 不要把 release 的 `super.img` 当更新 dd 到 armada_esp：它的 grub.cfg 带的是 release 自己的根 UUID，在下次 grub-sync 重写之前第一次启动会找不到根。两个版本的 GRUB 二进制完全一样，没有换的必要。
- `tb321fu-panel` 仍要加 `SUPER=/dev/disk/by-partlabel/armada_esp`。

### 实际执行记录（2026-11-02）

全程 SSH 操作，sudo 用 `/tmp/ap.sh` + `sudo -A`（/tmp 是 tmpfs，重启后脚本自动消失，要用得重建）。

| 阶段 | 结果 |
|---|---|
| 预检 | 全部符合预期。`bootc status` 报的正是 `Missing base image ref …53c6f11a…`；FAT 是单槽 b 布局（`.slot-b.id` = `430c6dff…`），剩余 134 MB；abl_a = abl_b = `3387ffdf…`；两个槽都 successful + bootable，b 为 active |
| 备份 | `/var/tmp/armada_esp.pre-ota.img`（sha256 `4380333d…`，电脑上 `_work/backup/` 有同一份）、`/var/tmp/bls.pre-ota/`、`/var/tmp/abl.pre.sha256`；btrfs 快照 `root-pre-ota-20261102`（子卷 ID 258，**一周后删**：`mount -o subvolid=5 /dev/disk/by-partlabel/armada_root /run/top && btrfs subvolume delete /run/top/root-pre-ota-20261102`） |
| 拉取 | `ostree container image pull` 用 nohup 放后台，128 层 6.8 GB，Wi-Fi 约 9 MB/s，12:11 → 12:28 共 17 分钟；前两层（1.78 GB + 0.7 GB）占了一半时间。结束行 `Wrote: … => 83be757d…` |
| 修复生效 | 拉完后 `bootc status` 正常：booted = `…:latest` 20261015.0544305，imageDigest `c2369862…`（就是 preview 4 的构建）。仓库从 36G 涨到 38G |
| 升级 | `bootc switch --enforce-container-sigpolicy` → "Image specification is unchanged"（规格没变，不动作）；改用 `bootc upgrade`：Deploying 13 秒，"Queued for next boot: … Version: 20261028.903dbdb, Digest: sha256:6d8a5de5…"，128 层里换了 78 层（-2.0 GB / +2.1 GB） |
| 重启前核对 | staged 部署的 vmlinuz 64104960 + initramfs 52334141 = 111 MiB，放得进 134 MB；`grub-sync`、`boot-finalize` 两版哈希相同；`20-tb321fu.conf` 的 ConditionFirmware 还在；新镜像确实带了 `openabl-updater`（OpenABL 1.2）；`ostree-finalize-staged.service` 有效 ExecStop = `ostree admin finalize-staged` → `tb321fu/boot-finalize`，Environment 有 `SUPER=armada_esp` |
| 关机日志 | `grub.cfg: default Armada 20261015.0544305 (slot b)` → `writing Armada 20261028.903dbdb to slot a` → `grub.cfg: default Armada 20261028.903dbdb (slot a), previous slot b` → `in sync`；ostree-finalize-staged 和 tb321fu-grub-sync 都 res=success |
| 重启 | 12:43:03 发出，12:44:02 SSH 回来，一次成功，没有 GRUB 后重启 |
| 启动后 | `BOOT_IMAGE=/Image-a`，`root=UUID=61564dbd…`，`ostree=/ostree/boot.0/default/43593203…/0`；`PRETTY_NAME="Armada 20261028.903dbdb"`；`bootc status` booted = 20261028.903dbdb，rollback = 20261015.0544305；三个 `50-dualboot.conf` 都在新 `/etc` 里；`armada-bootimg-sync` ConditionResult=no；abl 哈希不变；槽位属性不变；`systemctl --failed` 为空 |
| ESP 之后 | 槽 a（新）`.slot-a.id` = `94764cb3…`，槽 b（旧）保留；grub.cfg 三项：20261028（默认）、20261015 (previous)、20261028 (CSOT panel)；剩余 **22 MB** |

没做的：功能抽查（Wi-Fi、触摸、声音、睡眠、G9、Steam 检查更新）和"切回 Android 再切回来"要用户在机器上确认。
