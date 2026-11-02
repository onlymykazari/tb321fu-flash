# tb321fu-flash

Working notes, tools and recovery data for running **Android (slot A) + Armada (slot B)** on the Lenovo Legion Y700 Gen 3 / Legion Tab Gen 3 (**TB321FU**, Snapdragon 8 Gen 3 / SM8650) — migrated from an Armada-only install without losing data, with both switch directions and OSTree/bootc updates verified on the device.

The knowledge base is the runbook, **[双系统迁移-runbook.md](双系统迁移-runbook.md)** (Chinese): current partition layout and hashes, every pitfall hit and how each was diagnosed and fixed, day-to-day rules, rescue procedures, two from-scratch procedures, and how Armada OTA works on a dual-boot device. **Read section 3 before touching the device.** [AGENTS.md](AGENTS.md) is the short version of the hard rules.

## Layout

| Path | What |
|---|---|
| `tools/make_fill_b.py` | Generates the fh_loader lists that copy the A-side firmware into the empty `*_b` partitions. This 9008 package never writes slot B; without this step `set_active b` drops the device into 9008. |
| `tools/super_compose.py`, `super_verify.py` | Rebuild the stock `super` sparse image from the package's minimized `super_1..8.img` fragments, and verify it byte for byte. |
| `tools/simg_write.py` | Write an Android sparse image from stdin to a block device on Linux — the ABL fastboot silently corrupts `super` past 4 GiB. |
| `tools/slotattr.sh` | Read the A/B GPT attribute bits of `boot_a` / `boot_b`. |
| `tools/armada-ota.sh` | Post-update health check / manual `bootc upgrade` over SSH. |
| `tools/ghcr_layers.py` | Compare the first layers of the installed Armada build and `ghcr.io/…:latest`. |
| `tools/migrate/00..04_*.sh` | The migration scripts (shrink btrfs, rewrite GPT, send/receive data, deploy slot B, point the old GRUB at the copy). |
| `_work/` | Small, version-controlled artifacts: `rawprogram0_nogpt.xml` (flash LUN0 without touching the GPT), the generated `fill_b_lun*.xml`, read-only check XMLs and `.bat` wrappers for a 9008 session, GPT dumps before/after the migration, hash records. |
| `ASSETS.md` | Where every large binary is (private backup release, public release, or how to rebuild it) with sizes and SHA-256. |

The 9008 package, GSI, disk images and the device-specific ESP backup are **not** in git — see [ASSETS.md](ASSETS.md).

## Related repositories

- [enij90/armada-tb321fu](https://github.com/enij90/armada-tb321fu) — Armada for the TB321FU (upstream; updates come from `ghcr.io/enij90/armada-tb321fu:latest`). Preventive fork: [onlymykazari/armada-tb321fu](https://github.com/onlymykazari/armada-tb321fu).
- [CharlesGool/tb321fu-android-armada-dualboot](https://github.com/CharlesGool/tb321fu-android-armada-dualboot) — the dual-boot kit. My fork [onlymykazari/tb321fu-android-armada-dualboot](https://github.com/onlymykazari/tb321fu-android-armada-dualboot) carries the fix that lets the "reboot to Armada" module work on a GSI whose `bootctl` only speaks HIDL (it falls back to the AIDL boot control HAL) — upstream PR [#2](https://github.com/CharlesGool/tb321fu-android-armada-dualboot/pull/2).
- [onlymykazari/tb321fu-vintf-vndk-fix](https://github.com/onlymykazari/tb321fu-vintf-vndk-fix) — SukiSU module that removes the "There's an internal problem with your device" dialog on this GSI.
- [CharlesGool/TB321FU_PixelOS_15_Tangorpro](https://github.com/CharlesGool/TB321FU_PixelOS_15_Tangorpro) — the Pixel Tablet (tangorpro) Android 15 GSI used in slot A.

## Hard rules, in one breath

Never flash the stock `rawprogram0.xml` (it rebuilds the stock GPT and wipes `armada_esp` / `armada_root`); refill slot-B firmware before any `set_active b` after a full 9008 flash; never trust the ABL fastboot for `super` or `userdata`, write them from Linux and hash afterwards; keep GRUB's FAT out of `super`; don't sideload OTAs in recovery; update Armada only through `bootc upgrade`. Details and evidence for each are in the runbook.

## License

MIT, see [LICENSE](LICENSE) — same as the other TB321FU repositories. Everything was done on one device; use at your own risk.
