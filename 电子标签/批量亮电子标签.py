#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PTL Batch Light Control v4.0 (性能优化 + 耗时统计)
------------------------------------------------
功能：
- 批量控制指定区域 PTL 灯（Lxx#1~12 / Rxx#1~12）
- 支持多轮亮灯/灭灯测试
- 统计成功率 + 每轮耗时 + 单灯平均耗时
- 使用 requests.Session() 提升性能
------------------------------------------------
Author: Neo Xu
"""

import json
import time
import requests

# ======== 配置区 ========
URL = "http://10.201.160.113:9000/equipment/ptl/sendCommand"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

ZONE = "18"                # 区``1           `   ``  域号
COLOR = "BLUE"           # 灯颜色
RANGE = range(1, 24)       # 1~12号灯
DELAY = 0.1              # 单灯请求间隔 (默认 0.1 → 0.05 提升性能)
WAIT = 1                   # 每轮之间等待时间
LOOPS = 3               # 循环次数


# ======== 核心方法 ========
session = requests.Session()


def send_command(tag_code: str, color: str, mode: str) -> bool:
    """发送单个 PTL 命令，返回 True=成功 / False=失败"""
    payload = {
        "tagCode": tag_code,
        "color": color,
        "mode": mode,
        "display": "0",
        "displayText": "0"
    }

    try:
        resp = session.post(URL, headers=HEADERS, json=payload, timeout=2)
        return resp.status_code == 200
    except requests.RequestException as e:
        return False


def batch_light(zone: str, mode: str) -> tuple[int, int, float]:
    """批量亮/灭灯，返回 (成功数, 总数, 耗时秒)"""
    start = time.time()

    total = 0
    success = 0
    prefixes = [f"L{zone}", f"R{zone}"]

    for prefix in prefixes:
        for i in RANGE:
            tag = f"{prefix}#{i}"
            total += 1
            if send_command(tag, COLOR, mode):
                success += 1
            time.sleep(DELAY)

    elapsed = time.time() - start
    return success, total, elapsed


# ======== 主流程 ========
if __name__ == "__main__":
    print(f"=== 🚀 PTL Batch Control Start | Zone={ZONE}, Loops={LOOPS} ===\n")

    total_requests = 0
    total_success = 0
    total_time = 0

    for loop in range(1, LOOPS + 1):
        print(f"🔁 循环 {loop}/{LOOPS}")

        # --- 亮灯 ---
        s1, t1, dt1 = batch_light(ZONE, "LIGHT")
        total_requests += t1
        total_success += s1
        total_time += dt1

        print(f"  💡 亮灯: {s1}/{t1} 成功率 {(s1/t1)*100:.1f}% | 耗时 {dt1:.2f}s | 平均 {dt1/t1*1000:.1f}ms/灯")

        time.sleep(WAIT)

        # --- 灭灯 ---
        s2, t2, dt2 = batch_light(ZONE, "DARK")
        total_requests += t2
        total_success += s2
        total_time += dt2

        print(f"  💤 灭灯: {s2}/{t2} 成功率 {(s2/t2)*100:.1f}% | 耗时 {dt2:.2f}s | 平均 {dt2/t2*1000:.1f}ms/灯")

        print("-" * 60)
        time.sleep(WAIT)

    # ======== 总结 ========
    print("\n=== ✅ 测试结束 ===")
    print(f"总请求数: {total_requests}")
    print(f"总成功数: {total_success}")
    print(f"整体成功率: {total_success/total_requests*100:.2f}%")
    print(f"总耗时: {total_time:.2f}s")
    print(f"平均耗时: {total_time/total_requests*1000:.1f}ms/灯")
