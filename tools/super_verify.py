#!/usr/bin/env python3
"""校验 super_compose.py 生成的稀疏 super.img：结构正确 + RAW 数据与源片段逐字节一致。"""
import os
import re
import struct
import sys

SECTOR = 4096


def main():
    img, images_dir, unsparse_xml, rp0_xml = sys.argv[1:5]
    rp0 = open(rp0_xml, encoding="utf-8").read()
    sup = re.search(r'<program[^>]*filename="super.img"[^>]*label="super"[^>]*/>', rp0).group(0)
    super_start = int(re.search(r'start_sector="(\d+)"', sup).group(1))
    super_secs = int(re.search(r'num_partition_sectors="(\d+)"', sup).group(1))
    xml = open(unsparse_xml, encoding="utf-8").read()
    pieces = []
    for p in re.findall(r"<program[^>]*/>", xml):
        fn = re.search(r'filename="([^"]*)"', p).group(1)
        if re.fullmatch(r"super_\d+\.img", fn):
            st = int(re.search(r'start_sector="(\d+)"', p).group(1))
            pieces.append(((st - super_start) * SECTOR, os.path.join(images_dir, fn)))
    pieces.sort()

    def source_bytes(off, n):
        """从源片段取 [off, off+n)；不在任何片段内的部分视为 0。"""
        out = bytearray(n)
        for s, path in pieces:
            size = os.path.getsize(path)
            a, b = max(off, s), min(off + n, s + size)
            if a < b:
                with open(path, "rb") as f:
                    f.seek(a - s)
                    out[a - off:b - off] = f.read(b - a)
        return bytes(out)

    with open(img, "rb") as f:
        magic, major, minor, fhs, chs, blk_sz, total_blks, total_chunks, _ = struct.unpack("<IHHHHIIII", f.read(28))
        assert magic == 0xED26FF3A and major == 1 and fhs == 28 and chs == 12 and blk_sz == SECTOR, "文件头不对"
        assert total_blks == super_secs, f"total_blks {total_blks} != 分区扇区数 {super_secs}"
        f.seek(fhs)
        pos = 0
        raw_bytes = 0
        for i in range(total_chunks):
            ctype, _, csz, tsz = struct.unpack("<HHII", f.read(12))
            if ctype == 0xCAC1:
                n = csz * SECTOR
                assert tsz == 12 + n, f"chunk {i}: RAW 大小字段不一致"
                done = 0
                while done < n:
                    k = min(n - done, 1 << 24)
                    if f.read(k) != source_bytes(pos + done, k):
                        raise SystemExit(f"!! chunk {i} 偏移 {pos + done} 数据与源片段不一致")
                    done += k
                raw_bytes += n
            elif ctype == 0xCAC2:
                assert tsz == 16, f"chunk {i}: FILL 大小字段不对"
                val = struct.unpack("<I", f.read(4))[0]
                assert val == 0, f"chunk {i}: FILL 值不是 0"
                n = csz * SECTOR
                done = 0
                while done < n:
                    k = min(n - done, 1 << 24)
                    if source_bytes(pos + done, k).count(0) != k:
                        raise SystemExit(f"!! chunk {i}: FILL(0) 覆盖了源片段里的非零数据")
                    done += k
            elif ctype == 0xCAC3:
                raise SystemExit(f"chunk {i}: 出现 DONT_CARE（空隙应写 0）")
            else:
                raise SystemExit(f"chunk {i}: 意外类型 0x{ctype:04x}")
            pos += csz * SECTOR
        assert pos == super_secs * SECTOR, f"chunk 覆盖 {pos} != 分区大小"
        assert f.read(1) == b"", "文件尾部有多余数据"
    src_total = sum(os.path.getsize(p) for _, p in pieces)
    print(f"校验通过：{total_chunks} chunks，覆盖 {pos / 2**30:.2f} GiB，RAW 数据 {raw_bytes:,} 字节 == 源片段合计 {src_total:,} 字节："
          f"{'一致' if raw_bytes == src_total else '不一致!!'}")


if __name__ == "__main__":
    main()
