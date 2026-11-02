#!/usr/bin/env python3
"""
为 TB321FU 原厂 9008 包生成“补 B 槽固件”的 fh_loader 清单。

背景：这个 9008 包的 rawprogram 只给 _a 分区写镜像，_b 分区（xbl_b、abl_b、tz_b……）
全部留空。只要 `fastboot set_active b`，芯片就会从空的 xbl_b 启动失败，直接掉进 9008。
解决办法是把 A 侧的同款镜像写到对应的 _b 分区（OTA 本来也会这么做）。

规则：
  * 只处理 filename 为空的 *_b 条目，镜像取自同名 *_a 条目（sparse 属性也照抄）；
  * 默认跳过 boot_b（双系统里装的是 Armada 的 UEFI 加载器），可用 --skip 追加；
  * A 侧也没有���像的条目（如 qweslicstore）自动跳过；
  * 给了 --images 时检查文件是否存在、是否放得下，缺文件的条目跳过并警告（如 vm-bootsys.img）；
  * 不输出任何 GPT 条目，也不需要 patch*.xml。

用法：
    python make_fill_b.py --xml-dir <含 rawprogram*.xml 的目录> --images <解压出的镜像目录> --out <输出目录>

输出：fill_b_lun<N>.xml（每个 LUN 一个）和 fill_b_files.txt（需要的镜像文件清单）。
刷写（在镜像目录里，先用 QSaharaServer 上传编程器）：
    fh_loader.exe --port=\\\\.\\COMxx --memoryname=ufs --zlpawarehost=1 --search_path=. ^
        --sendxml=fill_b_lun2.xml,fill_b_lun4.xml,fill_b_lun0.xml --noprompt
"""
import argparse
import os
import re


def attr(tag, key):
    m = re.search(r'\b' + key + r'="([^"]*)"', tag)
    return m.group(1) if m else None


def set_attr(tag, key, value):
    return re.sub(r'\b' + key + r'="[^"]*"', f'{key}="{value}"', tag)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xml-dir", required=True, help="包含 rawprogram0..5.xml 的目录")
    ap.add_argument("--images", help="镜像目录（用于检查文件存在和大小）")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--skip", action="append", default=["boot_b"], help="额外跳过的 _b 分区（默认 boot_b）")
    a = ap.parse_args()

    xmls = sorted(f for f in os.listdir(a.xml_dir) if re.fullmatch(r"rawprogram\d+\.xml", f))
    if not xmls:
        raise SystemExit("找不到 rawprogram<N>.xml")
    tags = []
    for f in xmls:
        tags += re.findall(r"<program[^>]*/>", open(os.path.join(a.xml_dir, f), encoding="utf-8").read())
    a_side = {attr(t, "label"): t for t in tags if (attr(t, "label") or "").endswith("_a") and attr(t, "filename")}

    plan, files = {}, set()
    for t in tags:
        label = attr(t, "label") or ""
        if not label.endswith("_b") or attr(t, "filename") or label in a.skip:
            continue
        src = a_side.get(label[:-2] + "_a")
        if not src:
            continue
        fn = attr(src, "filename")
        cap = int(attr(t, "num_partition_sectors")) * int(attr(t, "SECTOR_SIZE_IN_BYTES"))
        if a.images:
            path = os.path.join(a.images, fn)
            if not os.path.exists(path):
                print(f"  跳过 {label}：镜像目录里没有 {fn}")
                continue
            if os.path.getsize(path) > cap:
                raise SystemExit(f"{label}: {fn} 有 {os.path.getsize(path)} 字节，分区只有 {cap} 字节")
        entry = set_attr(set_attr(t, "filename", fn), "sparse", attr(src, "sparse") or "false")
        lun = int(attr(t, "physical_partition_number"))
        plan.setdefault(lun, []).append(entry)
        files.add(fn)
        print(f"  LUN{lun} {label:18s} <- {fn}")

    os.makedirs(a.out, exist_ok=True)
    for lun, entries in sorted(plan.items()):
        body = "\n".join("  " + e for e in entries)
        with open(os.path.join(a.out, f"fill_b_lun{lun}.xml"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f'<?xml version="1.0" ?>\n<data>\n{body}\n</data>\n')
    with open(os.path.join(a.out, "fill_b_files.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(sorted(files)) + "\n")
    print(f"共 {sum(len(v) for v in plan.values())} 个分区，写出 " +
          ", ".join(f"fill_b_lun{lun}.xml" for lun in sorted(plan)) + " 和 fill_b_files.txt")


if __name__ == "__main__":
    main()
