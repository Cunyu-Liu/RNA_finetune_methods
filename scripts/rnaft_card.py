#!/usr/bin/env python3
"""共享卡锁助手（2026-09-29）：跨队列统一原子卡锁，防多队列在同卡叠加导致 OOM 竞卡。
用法:
  rnaft_card.py pick <needGB>          -> 打印 "<gpu> <slot>"（拿锁成功）或空字符串
  rnaft_card.py release <gpu> <slot>   -> 释放
规则: slot0 需 free>=need；slot1 需 free>=1.8*need（为同卡第二任务保留余量）。
MIG 过滤: total<20GiB 跳过（torch 视图物理不可用，非策略 gate）。
"""
import os, sys

LOCKDIR = "/tmp/rnaft_shared_locks"


def main():
    os.makedirs(LOCKDIR, exist_ok=True)
    cmd = sys.argv[1]
    if cmd == "release":
        g, s = sys.argv[2], sys.argv[3]
        try:
            os.rmdir("%s/gpu_%s_slot_%s" % (LOCKDIR, g, s))
        except Exception:
            pass
        return
    import torch
    need = float(sys.argv[2])
    cands = []
    for i in range(torch.cuda.device_count()):
        try:
            free, total = torch.cuda.mem_get_info(i)
        except Exception:
            continue
        if total < 20 * 2 ** 30 or free < need * 1e9:
            continue
        cands.append((free, i))
    import time
    now = time.time()
    for free, i in sorted(cands, reverse=True):
        for s in (0, 1):
            lk = "%s/gpu_%d_slot_%d" % (LOCKDIR, i, s)
            try:
                os.mkdir(lk)
            except FileExistsError:
                # 僵尸锁自愈（0930 教训：进程被杀后锁残留 9 小时空占 GPU5 slot0）
                try:
                    age = now - os.path.getmtime(lk)
                except OSError:
                    continue
                if age > 3600:   # >1h 且目录为空 = 视为僵尸锁，回收
                    if not os.listdir(lk):
                        try:
                            os.rmdir(lk)
                        except OSError:
                            continue
                        continue  # rmdir 后本轮跳过，下轮 pick 会重新抢
                continue
            try:
                free2, total2 = torch.cuda.mem_get_info(i)
            except Exception:
                free2, total2 = 0, 0
            margin = need * (1.0 if s == 0 else 1.5) * 1e9
            if total2 >= 20 * 2 ** 30 and free2 >= margin:
                print("%d %d" % (i, s))
                return
            try:
                os.rmdir(lk)
            except Exception:
                pass
    print("")


main()