#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PTL Blink Control v3.5
-----------------------------------
功能：
- 批量控制指定区域 PTL 灯闪烁
- 可设置循环次数与间隔时间
-----------------------------------
Author: Neo Xu
"""
from datetime import datetime
import json
import time
import requests

# ======== 配置区 ========
URL = "http://10.201.160.113:9000/equipment/ptl/sendCommand"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

ZONE = "21"           # 🔧 区域号，可改为 "04"、"06" 等
COLOR = "GREEN"      # 灯颜色，可选 RED / GREEN / BLUE / WHITE
RANGE = range(1, 13)  # 1~12号灯
DELAY = 1           # 每个请求间隔
WAIT = 5              # 每轮亮/灭后等待秒数
LOOPS = 1           # 循环次数（亮-灭为一轮）


# ======== 核心方法 ========
def send_command(tag_code: str, color: str, mode: str):
    """发送单个 PTL 命令"""
    payload = {
        "tagCode": tag_code,
        "color": color,
        "mode": mode,
        "display": "0",
        "displayText": "0"
    }

    try:
        # 获取当前时间
        now = datetime.now()
        # 格式化输出
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
        print()
        resp = requests.post(URL, headers=HEADERS, data=json.dumps(payload), timeout=5)
        # print(f"[{mode}] {tag_code:<8} → {resp.status_code} content: {resp.content} ")
        print(f"{formatted_time} {resp.text}")
    except requests.RequestException as e:
        print(f"[ERROR] {tag_code} -> {e}")


def batch_light(zone: str, mode: str):
    """批量亮/灭灯"""
    prefixes = [f"L{zone}",f"R{zone}"]
    for prefix in prefixes:
        for i in RANGE:
            tag = f"{prefix}#{i}"
            print(f"send tags: {prefix} #{i}")
            send_command(tag, COLOR, mode)
            time.sleep(DELAY)


def light_on(zone: str):
    print(f"💡 L{zone}/R{zone} → LIGHT")
    batch_light(zone, mode="LIGHT")


def light_off(zone: str):
    print(f"💤 L{zone}/R{zone} → DARK")
    batch_light(zone, mode="DARK")


# ======== 主流程 ========
if __name__ == "__main__":
    for n in range(1, LOOPS + 1):
        print(f"\n=== 🔁 循环 {n}/{LOOPS} ===")
        light_on(ZONE)
        #light_off(ZONE)

    print("\n✅ 完成所有循环")
