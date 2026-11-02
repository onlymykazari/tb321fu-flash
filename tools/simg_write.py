#!/usr/bin/env python3
"""从 stdin 读取 Android sparse 镜像，按块写入目标块设备（等价于 simg2img + dd）。"""
import os
import struct
import sys

dev = sys.argv[1]
inp = sys.stdin.buffer


def read_exact(n):
    out = bytearray()
    while len(out) < n:
        b = inp.read(n - len(out))
        if not b:
            raise SystemExit("输入流提前结束")
        out += b
    return bytes(out)


def write_all(fd, data):
    mv = memoryview(data)
    while mv:
        mv = mv[os.write(fd, mv):]


magic, major, minor, fhs, chs, blk, total_blks, total_chunks, _ = struct.unpack("<IHHHHIIII", read_exact(28))
if magic != 0xED26FF3A:
    raise SystemExit("不是 sparse 镜像")
read_exact(fhs - 28)
fd = os.open(dev, os.O_WRONLY)
size = os.lseek(fd, 0, os.SEEK_END)
if total_blks * blk != size:
    raise SystemExit(f"镜像大小 {total_blks * blk} 与分区大小 {size} 不一致，拒绝写入")
os.lseek(fd, 0, os.SEEK_SET)
STEP = 16 << 20
pos = 0
for i in range(total_chunks):
    ct, _, csz, tsz = struct.unpack("<HHII", read_exact(chs)[:12])
    n = csz * blk
    if ct == 0xCAC1:
        left = n
        while left:
            b = read_exact(min(left, STEP))
            write_all(fd, b)
            left -= len(b)
    elif ct == 0xCAC2:
        pat = read_exact(4) * (STEP // 4)
        left = n
        while left:
            k = min(left, STEP)
            write_all(fd, pat[:k])
            left -= k
    elif ct == 0xCAC3:
        os.lseek(fd, n, os.SEEK_CUR)
    elif ct == 0xCAC4:
        read_exact(4)
    else:
        raise SystemExit(f"未知 chunk 类型 0x{ct:04x}")
    pos += n
    if i % 20 == 0 or i == total_chunks - 1:
        print(f"chunk {i + 1}/{total_chunks}  {pos / 2**30:.2f} GiB", flush=True)
os.fsync(fd)
os.close(fd)
print(f"WRITE_DONE {pos}", flush=True)
