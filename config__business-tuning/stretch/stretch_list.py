import pandas as pd
import json
import paramiko
import csv
import concurrent.futures
from typing import List, Dict
import os

# =========================
# 配置区
# =========================
CSV_FILE_PATH = r"kubot.csv"  # 原始机器人列表文件
OUTPUT_EXCEL_PATH = "Kubot_Stretch_Report.xlsx"  # 导出的 Excel 文件名
# 配置文件路径
CONF_TUNING = "/home/kubot/app/config__business-tuning.json"
CONF_PERFORMANCE = "/home/kubot/app/config__environment-performance.json"


# =========================
# 读取机器人列表
# =========================
def read_ssh_csv(file_path: str) -> List[dict]:
    ssh_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 5:
                    ssh_list.append({
                        "hostname": row[0].strip(),
                        "ip": row[2].strip(),
                        "username": row[3].strip(),
                        "password": row[4].strip()
                    })
    except Exception as e:
        print(f"读取 CSV 出错: {e}")
    return ssh_list


# =========================
# JSON 解析逻辑
# =========================
def extract_tuning_value(json_content: str) -> str:
    """解析 tuning 文件获取 locationType 0 的 stretch_dif_tar 值"""
    try:
        data = json.loads(json_content)
        for profile in data.get("profiles", []):
            if profile.get("config-field") == "command":
                p_data = profile.get("profile-data", {})
                pos_params = p_data.get("ROBOT_COMMAND_POSITION_PARAMS", {})
                put_params = pos_params.get("EXTERNAL_BIN_OP_PUT", {})
                push_params = put_params.get("PUSH", {})
                stretch_list = push_params.get("stretch_dif_tar@", [])
                for item in stretch_list:
                    if item.get("locationType") == 1:
                        return item.get("@")
    except Exception:
        pass
    return "N/A"


def extract_performance_value(json_content: str) -> str:
    """解析 performance 文件获取 shallow_deep_box_gap 值"""
    try:
        data = json.loads(json_content)
        for profile in data.get("profiles", []):
            if profile.get("config-field") == "environment-settings":
                p_data = profile.get("profile-data", {})
                loc_data = p_data.get("location", {})
                support_list = loc_data.get("support_list", {})
                # 获取 STORAGE_SHELF_DEEP1 下的 gap 值
                deep_shelf = support_list.get("STORAGE_SHELF_DEEP1", {})
                return deep_shelf.get("shallow_deep_box_gap", "N/A")
    except Exception:
        pass
    return "N/A"


# =========================
# SSH 获取数据任务
# =========================
def fetch_data(cfg: dict) -> dict:
    hostname = cfg["hostname"]
    ip = cfg["ip"]

    result = {
        "Kubot_id": hostname,
        "locationType": 1,
        "PUSH-stretch_dif_tar": "读取失败",
        "shallow_deep_box_gap": "读取失败"
    }

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(ip, username=cfg["username"], password=cfg["password"], timeout=8)

        # 1. 读取 tuning 文件
        cmd_tuning = f"echo '{cfg['password']}' | sudo -S cat {CONF_TUNING}"
        _, stdout1, _ = client.exec_command(cmd_tuning)
        content_tuning = stdout1.read().decode().strip()
        if content_tuning:
            result["PUSH-stretch_dif_tar"] = extract_tuning_value(content_tuning)

        # 2. 读取 performance 文件
        cmd_perf = f"echo '{cfg['password']}' | sudo -S cat {CONF_PERFORMANCE}"
        _, stdout2, _ = client.exec_command(cmd_perf)
        content_perf = stdout2.read().decode().strip()
        if content_perf:
            result["shallow_deep_box_gap"] = extract_performance_value(content_perf)

        print(f"Success: {hostname} ({ip})")

    except Exception as e:
        print(f"Error: {hostname} : {str(e)}")
        error_msg = f"错误: {str(e)}"
        result["PUSH-stretch_dif_tar"] = error_msg
        result["shallow_deep_box_gap"] = error_msg
    finally:
        client.close()

    return result


# =========================
# 主程序
# =========================
def main():
    robots = read_ssh_csv(CSV_FILE_PATH)
    if not robots:
        print("未在 CSV 中找到设备信息")
        return

    print(f"开始采集 {len(robots)} 台机器人的参数...\n")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        future_to_robot = {executor.submit(fetch_data, r): r for r in robots}
        for future in concurrent.futures.as_completed(future_to_robot):
            results.append(future.result())

    new_df = pd.DataFrame(results)
    new_df = new_df.sort_values(by="Kubot_id")

    print(f"\n正在尝试追加数据到 Excel 文件...")

    try:
        if not os.path.exists(OUTPUT_EXCEL_PATH):
            new_df.to_excel(OUTPUT_EXCEL_PATH, index=False, engine='openpyxl')
            print(f"文件不存在，已创建新文件: {OUTPUT_EXCEL_PATH}")
        else:
            with pd.ExcelWriter(OUTPUT_EXCEL_PATH, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                try:
                    existing_df = pd.read_excel(OUTPUT_EXCEL_PATH, sheet_name='Sheet1')
                    start_row = len(existing_df) + 1
                except Exception:
                    start_row = 0

                new_df.to_excel(writer, index=False, header=False, startrow=start_row, sheet_name='Sheet1')

            print(f"数据已成功追加至: {OUTPUT_EXCEL_PATH}")

    except Exception as e:
        print(f"Excel 操作失败: {e}")


if __name__ == "__main__":
    main()