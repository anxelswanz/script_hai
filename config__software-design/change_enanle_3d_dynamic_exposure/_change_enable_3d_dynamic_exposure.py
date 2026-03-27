import csv
import time
import json
import paramiko
import concurrent.futures
import os
import tempfile

# =========================
# ✅ 配置区
# =========================
CSV_FILE_PATH = "robots.csv"  # 请确保你的 CSV 文件名正确
REMOTE_CONF_PATH = "/home/kubot/app/config__software-design.json"


# =========================
# ✅ 核心逻辑：修改 JSON
# =========================
def modify_json_content(file_content):
    """
    定位并修改 enable_3d_dynamic_exposure 为 false
    """
    try:
        data = json.loads(file_content)
        modified_flag = False

        if "profiles" in data:
            for profile in data["profiles"]:
                # 1. 寻找 device-settings 配置块
                if profile.get("config-field") == "device-settings":
                    p_data = profile.get("profile-data", {})

                    # 2. 定位 3d_camera_fork
                    camera_3d = p_data.get("3d_camera_fork", {})

                    # 3. 检查或创建 dynamic_exposure 层级
                    if "dynamic_exposure" not in camera_3d:
                        camera_3d["dynamic_exposure"] = {}

                    dyn_exp = camera_3d["dynamic_exposure"]

                    # 4. 修改目标值为 False
                    if dyn_exp.get("enable_3d_dynamic_exposure") is not False:
                        dyn_exp["enable_3d_dynamic_exposure"] = False
                        modified_flag = True

        return data, modified_flag
    except Exception as e:
        print(f"解析 JSON 失败: {e}")
        return None, False


# =========================
# ✅ 执行单台机器人操作
# =========================
def process_robot(robot_info):
    hostname = robot_info['hostname']
    ip = robot_info['ip']
    user = robot_info['username']
    pwd = robot_info['password']

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"🚀 [{hostname}] 正在连接 {ip}...")
        client.connect(ip, username=user, password=pwd, timeout=10)

        # 1. 停止服务
        client.exec_command("sudo /etc/kubot_application.sh stop")

        # 2. 备份原文件
        client.exec_command(f"sudo cp {REMOTE_CONF_PATH} {REMOTE_CONF_PATH}.bak")

        # 3. 读取内容 (通过 sudo cat 读取)
        stdin, stdout, stderr = client.exec_command(f"sudo cat {REMOTE_CONF_PATH}")
        content = stdout.read().decode()

        # 4. 修改内容
        new_json, is_changed = modify_json_content(content)

        if is_changed:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tf:
                json.dump(new_json, tf, indent=2)
                temp_path = tf.name

            # 上传并覆盖
            sftp = client.open_sftp()
            remote_tmp = f"/home/{user}/tmp_software_design.json"
            sftp.put(temp_path, remote_tmp)
            sftp.close()
            os.remove(temp_path)

            # 使用 sudo 移动到目标目录
            mv_cmd = f"echo '{pwd}' | sudo -S mv {remote_tmp} {REMOTE_CONF_PATH}"
            client.exec_command(mv_cmd)
            print(f"✅ [{hostname}] 参数修改成功并已保存")
        else:
            print(f"ℹ️ [{hostname}] 已经是目标状态，无需修改")

        # 5. 重启服务
        # client.exec_command("sudo /etc/kubot_application.sh start")
        # print(f"🔄 [{hostname}] 服务已重启")

    except Exception as e:
        print(f"❌ [{hostname}] 出错: {e}")
    finally:
        client.close()


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

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_robot, robots)

    print("\n✨ 所有设备任务执行完毕")


if __name__ == "__main__":
    main()