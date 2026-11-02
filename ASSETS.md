# 资产清单 / Asset inventory

Every large binary this workspace depends on, where it lives, and how to get it back. Git only tracks the small files; see the tables for the rest.

本仓库只跟踪小文件。下面列出工作区依赖的每一个大文件：在哪、哈希、本地还留不留。整理日期 **2026-11-02**。

**私有备份仓**（不要公开，里面有联想固件和本机专属的分区备份）：
<https://github.com/onlymykazari/tb321fu-assets/releases/tag/20261102>

9008 包和 GSI zip 两个大文件**不放 GitHub**，存在自己的网盘上（见第一节开头）。下载任何镜像后都要核对哈希再用。

## 一、没有公开直链（或直链不可靠）的资产

### 1a. 存在自己的网盘，不在 GitHub

| 文件 | 大小 | sha256 | 说明 | 本地 |
|---|---|---|---|---|
| `TB321FU_ZUI_17.5.10.170_OPEN_CRACKED.7z` | 6 742 323 109 B（6.28 GiB） | `b427c85e00e29bdda219ba68d1913676873df5f05873fc00a5938fb9b8038166` | ZUI 17.5.10.170 的 9008 线刷包。一切的源头：firehose 编程器、QPST 工具（`tool\`）、全部分区镜像（含 `super_1..8.img`、SukiSU Ultra GKI 重签名 `boot.img`、`vbmeta.img`）、rawprogram/patch XML。 | 保留（根目录） |
| `Pixel-tangorpro-15_TB321FU_V6-faceunlock_erofs_raw_Signed.zip` | 1 575 358 989 B（1.47 GiB） | `ec9bb353f220b13642c24d9cd1be65c464af01d47bda2fec450b7eda6603122c` | A 槽正在跑的 GSI。作者 [CharlesGool/TB321FU_PixelOS_15_Tangorpro](https://github.com/CharlesGool/TB321FU_PixelOS_15_Tangorpro/releases/tag/Pixel-tangorpro-15_TB321FU_V6-faceunlock_erofs_raw_Signed) 目前有公开直链（大小一致），但该仓库已经删过旧版本，所以自己也存一份。zip 里是 `.img`（1 892 077 568 B，sha256 `3d3c7690…`）和它的 `.sha256`。 | 保留（根目录）；解压出的 `.img` 已删 |

### 1b. 私有备份仓 release `20261102`

| 文件 | 大小 | sha256 | 说明 | 本地 |
|---|---|---|---|---|
| `armada_esp.pre-ota.img` | 268 435 456 B（256 MiB） | `4380333de213a1d508fe7f46bae13c2a053505c3e3c04d8222c6ce763c93bce6` | 2026-11-02 OTA 之前的 `armada_esp` 整块备份（preview 4、单槽 b 布局、grub.cfg 已是本机根 UUID）。**不可再生**。设备 `/var/tmp/` 也有一份。 | 保留 `_work/backup/` |
| `boot.img`（SukiSU GKI） | 100 663 296 B（96 MiB） | `d06f5ab0837c1952414d7e73fce0880583d761294cabc64242d76a79cd406785` | 现在 `boot_a` 里的内容，等于 7z 的 `image\boot.img`。救援 `boot_a` 用。 | 保留 `_work/android/` |
| `vbmeta.img` | 12 288 B | `d4c8b06c96e1d6ac7d4c76fc6adac3fc7a962cbeeef04af4e6f4169c829947b1` | 7z 的 `image\vbmeta.img`（`vbmeta_a`）。 | 保留 `_work/android/` |
| `gpt_primary.bin` / `gpt_backup.bin` | 24 576 / 20 480 B | `ed47b206…` / `2a3ada17…` | 迁移**前**本机 GPT（Armada 单系统布局）。**不可再生**。 | 保留 `_work/`，也在 git 里 |
| `new_primary.bin` / `new_backup.bin` | 24 576 / 20 480 B | `d72bfb48…` / `ce0711ec…` | 迁移**后**本机 GPT（现在的双系统布局）。 | 保留 `_work/`，也在 git 里 |
| `reboot_to_armada.zip` | 2 461 B | `676c864dd595d57c3784473fc61fe4c510075184c131041ad499d9ef04e836bb` | 设备上装的那个“重启到 Armada”模块，由修过的 `switch.sh` 打包（源码见 fork `onlymykazari/tb321fu-android-armada-dualboot` commit `21dfc82`，上游 PR [#2](https://github.com/CharlesGool/tb321fu-android-armada-dualboot/pull/2)）。 | 保留 `_work/android/` |
| `vintf_vndk_fix.zip` | 1 669 B | `7a42358cd9a1b4ed97cf32e2db60db0b1d21fa0fd1df33c0270ccc0bb0b28da7` | 设备上装的 v1.1 模块，和 `tb321fu-vintf-vndk-fix` 的 `build.py` 产物逐字节一致（该仓库 Release v1.1 也有）。 | 保留 `_work/android/` |
| `notice.txt` | 980 B | `9d8579aa…` | 9008 包自带说明（进 9008 的按键、回滚值 1775347200）。 | 保留 `_work/`，也在 git 里 |

完整哈希在 release 里的 `SHA256SUMS`。

## 二、有公开直链，本地已删除（只留 SHA256SUMS 校验下载）

| 文件 | 大小 | sha256 | 公开直链 |
|---|---|---|---|
| Armada preview 5 `boot.img` | 100 663 296 B | `45f923bc3980a8ba6e12ce606c30b4b08c2de48047626648a3d1861c95d2a58f` | <https://github.com/enij90/armada-tb321fu/releases/tag/v20261024.0146e89> |
| Armada preview 5 `super.img` | 268 435 456 B | `9a11ad9b935836bf8230e6866594871f893cf1e655aed11146a8519052cff5d3` | 同上 |
| Armada preview 5 `userdata.simg.part1..7` | 6 × 1 992 294 400 + 113 718 376 B（11.24 GiB） | 分片哈希见 `_work/release_v20261024/SHA256SUMS`；合并后 `6fe4c1176a5c0c647f3cb1fdd83b6ccb6e9084fe16714daa13b4046e5f36c5fe` | 同上。**只用于从零安装**，写到 armada_root 会清掉全部数据 |
| Armada preview 4 `boot.img` | 100 663 296 B | `45f923bc…`（和 preview 5 相同） | <https://github.com/enij90/armada-tb321fu/releases/tag/v20261015.0544305> |
| Armada preview 4 `super.img` | 268 435 456 B | `321f877d68ced75a219d0595d247945f9d8b0c154068f88623e4a094190db1e6` | 同上。GRUB 二进制和 preview 5 相同，只有 grub.cfg 不同 |
| SukiSU 管理器 4.1.3（40796） | 12 148 312 B | — | <https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.1.3>。设备上装的版本；本地 `_work/android/` 还留着一份 |
| SukiSU 管理器 4.1.2（40545） | 9 944 150 B | — | <https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.1.2>。没用上，本地已删 |

救援时 `boot_b` 用 preview 4/5 任一的 `boot.img`（相同）；GRUB FAT 坏了优先用第一节的 `armada_esp.pre-ota.img`（runbook 第八节第 6 步），其次才是 release 的 `super.img`（要改 grub.cfg 的 UUID）。

## 三、可以从上面的东西重建，本地已删除

| 文件 | 大小 | 怎么重建 | 校验 |
|---|---|---|---|
| `_work/super_stock.img` | 10 739 911 508 B（稀疏；展开 13 GiB） | 解压 7z 后 `python tools/super_compose.py --images <7z>/image --rawprogram <7z>/image/rawprogram_unsparse0.xml -o _work/super_stock.img`，再 `python tools/super_verify.py` | 写入设备后整块 sha256 应为 `46e4ae1f71e9b15756accab2f91dcca305bb20f6c9bf624c51654bb75ef1f6c9`（`_work/super_stock.sha256`） |
| `_work/android/Pixel-tangorpro-15_TB321FU_V6-faceunlock_erofs_raw_Signed.img` | 1 892 077 568 B | 解压根目录的同名 zip | `3d3c7690fbc8f216cee0bdb80fdfb8a8281eeb724dc9c8f2d51711babfaa0788`（`_work/android/*.img.sha256`） |
| `_work/android/manifest.xml.orig` | 1 773 B | 就是 `tb321fu-vintf-vndk-fix/original/manifest.xml` | `a2c9d8ec4c4f8c8122c3316c3f3234e0732cf4a4819b0edccdbb5e415fbac825` |
| `_work/README.md`、`contents.xml`、`provision_ufs40.xml` | 小 | 9008 包原文件，用不到；`notice.txt` 已包含 README 的内容 | — |

## 四、可以重建，但本地仍保留（救援随时要用）

| 目录 | 大小 | 内容 | 来源 |
|---|---|---|---|
| `_work/qfil/image/prog_firehose_ddr.elf` | 303 KB | firehose 编程器 | 7z `image\` |
| `_work/qfil/tool/` 里的 `.exe/.dll/.ocx` | 45 MB，37 个 | QSaharaServer、fh_loader 及依赖（QPST 子集） | 7z `tool\` |
| `_work/qfil/tool/` 里的 `.bin/.mbn/.elf/.melf/.img` | ~390 MB，31 个 | 补 B 侧固件的源镜像（`fill_b_files.txt`） | 7z `image\` |
| `_work/qfil/tool/fill_b_lun{0,2,4}.xml`、`fill_b_files.*`、`read_*.xml`、`step*.bat` | 小 | 补 B 侧的清单、只读检查、.bat 包装 | 自己生成（`tools/make_fill_b.py`）；**已在 git 里** |

## 五、在 git 里的小文件（本仓库）

`_work/rawprogram0.xml`（原版，仅供对照）、`_work/rawprogram0_nogpt.xml`（不碰 GPT 的版本，线刷用这个）、`_work/rawprogram_unsparse0.xml`、`_work/patch0.xml`（不要加载）、`_work/xml/`（make_fill_b 的输入）、四个 GPT `.bin`、`_work/super_stock.sha256`、`_work/super_*_blocks.txt`、`_work/android/*.sha256`、`_work/release*/SHA256SUMS`、`_work/notice.txt`，以及 `tools/` 全部。

## 六、相邻的独立仓库（被 .gitignore 排除，各自 clone）

| 目录 | 远端 | 状态 |
|---|---|---|
| `armada-tb321fu/` | 上游 <https://github.com/enij90/armada-tb321fu>；预防性 fork <https://github.com/onlymykazari/armada-tb321fu> | 本地 clone 已删（2026-11-02，当时无本地修改）；要看源码就重新 clone |
| `tb321fu-android-armada-dualboot/` | origin = <https://github.com/onlymykazari/tb321fu-android-armada-dualboot>（fork），upstream = CharlesGool | `switch.sh` AIDL HAL 修复已提交并推送（`21dfc82`），上游 PR [#2](https://github.com/CharlesGool/tb321fu-android-armada-dualboot/pull/2) |
| `tb321fu-vintf-vndk-fix/` | <https://github.com/onlymykazari/tb321fu-vintf-vndk-fix> | 干净，已发布 Release v1.1 |
