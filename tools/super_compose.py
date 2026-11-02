#!/usr/bin/env python3
"""
把 TB321FU 原厂 9008 包（OPEN_CRACKED）里被"最小化"拆分的 super_1.img ... super_8.img
按 rawprogram_unsparse0.xml 记录的偏移，重组为一个完整的 super 分区镜像：

    fastboot flash super super.img

包里的分块不是 sparse，而是 super 分区里的"非零原始片段"（零区域被裁掉，
contents.xml 标记 minimized=true），所以必须按 XML 的 start_sector 放回原位。

用法（在本目录有 image\\ 的情况下）：
    python super_compose.py --images image --rawprogram image\\rawprogram_unsparse0.xml -o super.img

默认输出 Android 稀疏镜像（0 区域写成 DONT_CARE，文件小、fastboot 传输快），
加 --raw 输出 13 GiB 裸镜像（给 lpunpack 之类工具用）。

自动校验：片段无重叠、总覆盖 == 分区大小、liblp 魔数
（分区 4096 处 geometry "RHTl"、8192 处 metadata "0PLA"）必须出现，否则拒绝输出。
"""
import argparse
import os
import re
import struct
import sys

SECTOR = 4096
RAW_CHUNK_MAX = 64 * 1024 * 1024
SPARSE_MAGIC = 0xED26FF3A
CHUNK_RAW, CHUNK_FILL, CHUNK_DONT_CARE, CHUNK_CRC32 = 0xCAC1, 0xCAC2, 0xCAC3, 0xCAC4


def parse_programs(xml_path):
    xml = open(xml_path, encoding="utf-8").read()
    progs = re.findall(r"<program[^>]*/>", xml)
    out = []
    super_start = None
    super_sectors = None
    for p in progs:
        def field(name, default=None):
            m = re.search(name + r'="([^"]*)"', p)
            return m.group(1) if m else default
        label = field("label", "")
        fn = field("filename")
        if label == "super" and fn == "super.img":
            super_start = int(field(r"start_sector").rstrip("."))
            super_sectors = int(field(r"num_partition_sectors").rstrip("."))
        if fn and re.fullmatch(r"super_\d+\.img", fn):
            out.append((fn, int(field(r"start_sector").rstrip(".")),
                        int(field(r"num_partition_sectors").rstrip("."))))
    return out, super_start, super_sectors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default="image", help="分块文件所在目录")
    ap.add_argument("--rawprogram", default=None,
                    help="rawprogram_unsparse0.xml 路径（分块偏移清单，默认在 <images> 或其上级目录找）")
    ap.add_argument("--rawprogram0", default=None,
                    help="rawprogram0.xml 路径（读取 label=super 的分区几何；默认与 --rawprogram 同目录）")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--raw", action="store_true", help="输出裸镜像而非稀疏镜像")
    a = ap.parse_args()

    rp = a.rawprogram
    if not rp:
        for cand in (os.path.join(a.images, "rawprogram_unsparse0.xml"),
                     os.path.join(os.path.dirname(os.path.abspath(a.images)), "rawprogram_unsparse0.xml")):
            if os.path.exists(cand):
                rp = cand
                break
    if not rp or not os.path.exists(rp):
        raise SystemExit("找不到 rawprogram_unsparse0.xml，请用 --rawprogram 指定")
    rp0 = a.rawprogram0 or os.path.join(os.path.dirname(rp), "rawprogram0.xml")
    if not os.path.exists(rp0):
        raise SystemExit(f"找不到 {rp0}（需要其中的 label=super 条目确定分区几何），请用 --rawprogram0 指定")

    pieces, _, _ = parse_programs(rp)
    _, super_start, super_sectors = parse_programs(rp0)
    if not pieces:
        raise SystemExit("rawprogram_unsparse0.xml 里没有 super_N.img 条目")
    if super_start is None:
        raise SystemExit("rawprogram0.xml 里没有 label=super 条目，无法确定分区内偏移")
    print(f"super 分区：起始扇区 {super_start}，共 {super_sectors} 扇区 "
          f"({super_sectors * SECTOR / 2**30:.2f} GiB)")
    print(f"片段 {len(pieces)} 个：")

    regions = []  # (rel_start_byte, rel_end_byte, path)
    covered = 0
    for fn, start, nsec in sorted(pieces, key=lambda x: x[1]):
        path = os.path.join(a.images, fn)
        size = os.path.getsize(path)
        expect = nsec * SECTOR
        if size != expect:
            raise SystemExit(f"{fn}: 文件大小 {size} != XML 记录 {expect} 扇区*{SECTOR}")
        rel = (start - super_start) * SECTOR
        if rel < 0:
            raise SystemExit(f"{fn}: start_sector 在 super 分区之前")
        regions.append((rel, rel + size, path))
        covered += size
        print(f"  {fn:14s} 分区内偏移 {rel:>13,} .. {rel + size:>13,}  ({size / 2**20:8.1f} MiB)")
    for (s1, e1, p1), (s2, e2, p2) in zip(regions, regions[1:]):
        if s2 < e1:
            raise SystemExit(f"片段重叠：{p1} 与 {p2}")
    total = super_sectors * SECTOR
    print(f"覆盖 {covered / 2**20:.1f} MiB / {total / 2**20:.1f} MiB（其余为出厂零区域，写为 FILL(0)）")

    # 校验 liblp 魔数（第一个片段覆盖分区 0 偏移）：
    # geometry 主/备份在 4096、8192（"gDla"），元数据头在 12288（"0PLA"）
    p0 = regions[0][2]
    if regions[0][0] != 0:
        raise SystemExit("第一个片段不从分区 0 偏移开始，无法校验 liblp 头")
    with open(p0, "rb") as f:
        head = f.read(16384)
    GEO, HDR = struct.pack("<I", 0x616C4467), struct.pack("<I", 0x414C5030)
    checks = [(4096, GEO, "geometry"), (8192, GEO, "geometry(backup)"), (12288, HDR, "metadata header")]
    ok = True
    for off, magic, name in checks:
        got = head[off:off + 4]
        good = got == magic
        ok &= good
        print(f"  {name:17s} @{off:5d}: {got.hex()} {'OK' if good else 'BAD'}")
    if head[:4096].count(0) != 4096:
        print("  注意：分区开头 4 KiB 不全为 0")
    if not ok:
        raise SystemExit("liblp 魔数不对——片段/清单不匹配，拒绝生成")

    if a.raw:
        with open(a.out, "wb") as out:
            pos = 0
            for s, e, path in regions:
                out.seek(s)
                with open(path, "rb") as f:
                    while True:
                        buf = f.read(1 << 24)
                        if not buf:
                            break
                        out.write(buf)
                pos = e
            out.truncate(total)
        print(f"已写出裸镜像 {a.out}（{total} 字节）")
    else:
        blocks = total // SECTOR
        nchunks = 0
        with open(a.out, "wb") as out:
            def hdr32(*v):
                out.write(struct.pack("<IHHHHIIII", SPARSE_MAGIC, 1, 0, 28, 12, SECTOR, v[0], v[1], 0))
            # 先占位写头，最后回填
            hdr32(0, 0)
            pos = 0

            def fill_zero(nbytes):
                # 原厂包把全零区域裁掉了：空隙必须写回 0（FILL），不能用 DONT_CARE 保留设备上的旧数据
                nonlocal nchunks
                while nbytes:
                    n = min(nbytes, RAW_CHUNK_MAX)
                    out.write(struct.pack("<HHIII", CHUNK_FILL, 0, n // SECTOR, 16, 0))
                    nchunks += 1
                    nbytes -= n

            for s, e, path in regions:
                if s > pos:
                    fill_zero(s - pos)
                # chunk 头的 total_sz 只有 32 位：大片段切成 64 MiB 的 RAW chunk
                with open(path, "rb") as f:
                    left = e - s
                    while left:
                        n = min(left, RAW_CHUNK_MAX)
                        out.write(struct.pack("<HHII", CHUNK_RAW, 0, n // SECTOR, 12 + n))
                        nchunks += 1
                        todo = n
                        while todo:
                            buf = f.read(min(todo, 1 << 24))
                            if not buf:
                                raise SystemExit(f"{path}: 读取提前结束")
                            out.write(buf)
                            todo -= len(buf)
                        left -= n
                pos = e
            if pos < total:
                fill_zero(total - pos)
            out.seek(0)
            hdr32(blocks, nchunks)
        print(f"已写出稀疏镜像 {a.out}（{blocks} 块，{nchunks} chunks）")

    print("完成。刷写：fastboot flash super " + a.out)


if __name__ == "__main__":
    main()
