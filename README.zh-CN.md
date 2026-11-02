# tb321fu-flash

联想拯救者 Y700 三代 / Legion Tab Gen 3（**TB321FU**，骁龙 8 Gen 3 / SM8650）**Android（A 槽）+ Armada（B 槽）** 双系统的工作记录、工具和救援数据。从 Armada 单系统迁移而来，数据全部保留，两个方向的切换和 OSTree/bootc 更新都在机器上实测过。

知识库是 **[双系统迁移-runbook.md](双系统迁移-runbook.md)**：当前分区布局和哈希、每一个踩过的坑（现象 → 根因 → 怎么确认 → 怎么解决）、日常注意、救援、两套从零重做的流程、双系统下 Armada 更新的原理和实录。**动手前先读第三节。** [AGENTS.md](AGENTS.md) 是硬性规则的摘要。

## 目录

| 路径 | 内容 |
|---|---|
| `tools/make_fill_b.py` | 生成把 A 侧固件补到空的 `*_b` 分区的 fh_loader 清单。这个 9008 包从不写 B 槽，不补就 `set_active b` 会直接掉 9008。 |
| `tools/super_compose.py`、`super_verify.py` | 把包里“最小化”的 `super_1..8.img` 片段重组成原厂 super 稀疏镜像，并逐字节核对。 |
| `tools/simg_write.py` | 在 Linux 里把稀疏镜像从 stdin 写进块设备——ABL 的 fastboot 写 super 超过 4 GiB 后会悄悄写错。 |
| `tools/slotattr.sh` | 读 `boot_a` / `boot_b` 的 A/B GPT 属性位。 |
| `tools/armada-ota.sh` | 更新后体检 / SSH 手动 `bootc upgrade`。 |
| `tools/ghcr_layers.py` | 比较设备上的 Armada 构建和 `ghcr.io/…:latest` 的首层。 |
| `tools/migrate/00..04_*.sh` | 迁移脚本（缩 btrfs、改 GPT、send/receive 数据、部署 B 槽、把旧 GRUB 指向副本）。 |
| `_work/` | 入库的小文件：`rawprogram0_nogpt.xml`（不碰 GPT 的 LUN0 刷写清单）、生成的 `fill_b_lun*.xml`、9008 会话的只读检查 XML 和 .bat 包装、迁移前后的 GPT 备份、哈希记录。 |
| `ASSETS.md` | 每个大文件在哪（私有备份 release / 公开 release / 怎么重建），大小和 SHA-256。 |

9008 包、GSI、磁盘镜像和本机专属的 ESP 备份**不在 git 里**，见 [ASSETS.md](ASSETS.md)。

## 相关仓库

- [enij90/armada-tb321fu](https://github.com/enij90/armada-tb321fu) — TB321FU 的 Armada（上游；更新来自 `ghcr.io/enij90/armada-tb321fu:latest`）。预防性 fork：[onlymykazari/armada-tb321fu](https://github.com/onlymykazari/armada-tb321fu)。
- [CharlesGool/tb321fu-android-armada-dualboot](https://github.com/CharlesGool/tb321fu-android-armada-dualboot) — 双系统套件。我的 fork [onlymykazari/tb321fu-android-armada-dualboot](https://github.com/onlymykazari/tb321fu-android-armada-dualboot) 带着让“重启到 Armada”模块在只认 HIDL 的 GSI `bootctl` 上也能工作的修复（退回直接调用 AIDL 启动控制 HAL），已提上游 PR [#2](https://github.com/CharlesGool/tb321fu-android-armada-dualboot/pull/2)。
- [onlymykazari/tb321fu-vintf-vndk-fix](https://github.com/onlymykazari/tb321fu-vintf-vndk-fix) — 消除这个 GSI 开机“系统内部出现问题”弹窗的 SukiSU 模块。
- [CharlesGool/TB321FU_PixelOS_15_Tangorpro](https://github.com/CharlesGool/TB321FU_PixelOS_15_Tangorpro) — A 槽用的 Pixel Tablet（tangorpro）Android 15 GSI。

## 硬性规则一口气版

不要刷原版 `rawprogram0.xml`（重建原厂 GPT，`armada_esp` / `armada_root` 全没）；全量 9008 之后、任何 `set_active b` 之前先补 B 侧固件；super 和 userdata 不要信 ABL 的 fastboot，在 Linux 里写、写完算哈希；super 里不能留 GRUB 的 FAT；不要在 recovery 卡刷 OTA；Armada 只用 `bootc upgrade` 更新。每一条的证据都在 runbook 里。

## 许可

MIT，见 [LICENSE](LICENSE)，和另外两个 TB321FU 仓库一致。所有操作只在一台机器上做过，风险自负。
