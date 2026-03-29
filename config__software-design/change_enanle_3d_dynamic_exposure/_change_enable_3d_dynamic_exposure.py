import csv
import time
import json
import paramiko
import concurrent.futures
import os
import tempfile
import pandas as pd  # 新增：用于导出Excel

# =========================
# ✅ 配置区
# =========================
CSV_FILE_PATH = "robots.csv"
LOG_EXCEL_PATH = "modification_log.xlsx"  # 新增：日志导出路径
REMOTE_CONF_PATH = "/home/kubot/app/config__software-design.json"

# 新增：用于存储每台机器的执行结果
results_list = []


def modify_json_content(file_content):
    """
    针对 vision -> dynamic_exposure -> enable_3d_dynamic_exposure 的修改
    """
    try:
        data = json.loads(file_content)
        modified_flag = False

        if "profiles" not in data:
            return None, False

        for profile in data["profiles"]:
            # 1. 准确定位 module 块 (根据你提供的逻辑)
            if profile.get("config-field") == "module":
                p_data = profile.get("profile-data", {})

                # 2. 定位 vision 块
                vision = p_data.get("vision")
                if isinstance(vision, dict):
                    # 3. 定位 dynamic_exposure 块
                    dyn_exp = vision.get("dynamic_exposure")

                    if isinstance(dyn_exp, dict):
                        current_val = dyn_exp.get("enable_3d_dynamic_exposure")
                        # 4. 如果不是 False，则修改为 False
                        if current_val is not False:
                            dyn_exp["enable_3d_dynamic_exposure"] = False
                            modified_flag = True
        return data, modified_flag
    except Exception as e:
        return None, False


# =========================
# ✅ 执行单台机器人操作
# =========================
def process_robot(robot_info):
    hostname = robot_info['hostname']
    ip = robot_info['ip']
    user = robot_info['username']
    pwd = robot_info['password']

    # 默认状态
    status = "失败"
    remark = ""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"🚀 [{hostname}] 正在连接 {ip}...")
        client.connect(ip, username=user, password=pwd, timeout=5)

        # 2. 备份原文件
        client.exec_command(f"sudo cp {REMOTE_CONF_PATH} {REMOTE_CONF_PATH}.bak")
        # 3. 读取内容
        stdin, stdout, stderr = client.exec_command(f"sudo cat {REMOTE_CONF_PATH}")
        content = stdout.read().decode()

        # 4. 修改内容
        new_json, is_changed = modify_json_content(content)

        if is_changed:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tf:
                json.dump(new_json, tf, indent=2)
                temp_path = tf.name

            sftp = client.open_sftp()
            remote_tmp = f"/home/{user}/tmp_software_design.json"
            sftp.put(temp_path, remote_tmp)
            sftp.close()
            os.remove(temp_path)

            mv_cmd = f"echo '{pwd}' | sudo -S mv {remote_tmp} {REMOTE_CONF_PATH}"
            client.exec_command(mv_cmd)
            status = "成功"
            remark = "参数已从 True 修改为 False"
            print(f"✅ [{hostname}] 参数修改成功")
        else:
            status = "跳过"
            remark = "已经是 False 或未找到配置项"
            print(f"ℹ️ [{hostname}] 已经是目标状态，无需修改")

    except Exception as e:
        status = "连接失败/出错"
        remark = str(e)
        print(f"❌ [{hostname}] 出错: {e}")
    finally:
        client.close()
        # 将结果存入列表
        results_list.append({
            "机器人名称": hostname,
            "IP地址": ip,
            "执行结果": status,
            "备注/错误详情": remark,
            "时间": time.strftime("%Y-%m-%d %H:%M:%S")
        })


# =========================
# ✅ 读取 CSV 并启动并发
# =========================
def main():
    robots = []
    try:
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 5:
                    robots.append({
                        'hostname': row[0].strip(),
                        'ip': row[2].strip(),
                        'username': row[3].strip(),
                        'password': row[4].strip()
                    })
    except FileNotFoundError:
        print(f"❌ 找不到 CSV 文件: {CSV_FILE_PATH}")
        return

    print(f"📢 准备处理 {len(robots)} 台设备...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_robot, robots)

    # 新增：导出结果到 Excel
    print(f"\n📊 正在生成统计报表...")
    df = pd.DataFrame(results_list)
    # 按结果排序，方便查看失败的机器
    df = df.sort_values(by="执行结果", ascending=False)
    df.to_excel(LOG_EXCEL_PATH, index=False)

    print(f"✨ 所有任务执行完毕！报表已保存至: {LOG_EXCEL_PATH}")


if __name__ == "__main__":
    main()