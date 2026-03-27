import csv
import time
import json
import paramiko
import concurrent.futures
import os
import tempfile
from typing import Dict, Optional

# =========================
# ✅ 配置区
# =========================
CSV_FILE_PATH = r"LPP_50.csv"  # 你的 CSV 文件路径
# 👇 修改目标文件路径为 config__business-tuning.json
REMOTE_CONF_PATH = "/home/kubot/app/config__business-tuning.json"

# 打开机器人放箱提前上报 和 调整顶升相对库位高度差 = -0.15
# =========================
# ✅ 读取 CSV
# =========================
def read_ssh_csv(file_path: str) -> Dict[str, dict]:
    ssh_info = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 5:
                    hostname = row[0].strip()
                    ip = row[2].strip()
                    username = row[3].strip()
                    password = row[4].strip()

                    if hostname and ip and username and password:
                        ssh_info[hostname] = {
                            "hostname": hostname,
                            "ip_address": ip,
                            "port": 22,
                            "username": username,
                            "password": password
                        }
    except Exception as e:
        print(f"❌ 读取CSV出错: {e}")
    return ssh_info


# =========================
# ✅ 停止节点
# =========================
def stop_node(client):
    stdin, stdout, stderr = client.exec_command(
        "sudo /etc/kubot_application.sh stop"
    )
    return stdout.read().decode(), stderr.read().decode()


# =========================
# ✅ 修改 Business Tuning 参数
# 1. report_complete_in_advance@ (Type 10 -> True)
# 2. lift_report_dis@ (Type 10 -> -0.15)
# =========================
def modify_business_tuning_params(ip, client, username, sudo_password=None):
    # 临时文件路径
    remote_tmp_path = f"/home/{username}/config_tmp_upload.json"

    print(f"   ↳ 正在读取远程配置 (sudo模式)...")

    # 1️⃣ 【读取】
    cmd_read = f"echo '{sudo_password}' | sudo -S -p '' cat {REMOTE_CONF_PATH}" if sudo_password else f"sudo cat {REMOTE_CONF_PATH}"

    stdin, stdout, stderr = client.exec_command(cmd_read)
    file_content = stdout.read().decode().strip()
    err_content = stderr.read().decode().strip()

    if not file_content:
        print(f"   ⚠️ sudo 读取为空，尝试普通读取...")
        try:
            sftp = client.open_sftp()
            with sftp.file(REMOTE_CONF_PATH, 'r') as f:
                file_content = f.read().decode().strip()
            sftp.close()
        except Exception as e:
            raise Exception(f"无法读取远程文件，报错: {err_content} | {e}")

    # 2️⃣ 【解析与修改】
    try:
        content = json.loads(file_content)
    except json.JSONDecodeError:
        raise Exception(f"远程文件不是合法的 JSON，无法解析。")

    # 🌟 修改逻辑
    modified_flag = False
    try:
        if "profiles" in content and isinstance(content["profiles"], list):
            for profile in content["profiles"]:
                # 找到 config-field 为 "command" 的配置块
                if profile.get("config-field") == "command":
                    p_data = profile.get("profile-data", {})

                    # --- 修改 1: 提前上报 (report_complete_in_advance) ---
                    try:
                        put_toggles = p_data.get("ROBOT_COMMAND_FEATURE_TOGGLES", {}) \
                            .get("EXTERNAL_BIN_OP_PUT", {}) \
                            .get("DOWN", {})

                        target_list_1 = put_toggles.get("report_complete_in_advance@", [])

                        for item in target_list_1:
                            if item.get("locationType") == 10:
                                if item.get("@") is not True:
                                    print(f"   ℹ️ [修改1] 提前上报 Type 10: {item.get('@')} -> True")
                                    item["@"] = True
                                    modified_flag = True
                    except Exception as e:
                        print(f"   ⚠️ 查找 report_complete_in_advance 路径失败: {e}")

                    # --- 修改 2: 提升上报距离 (lift_report_dis) ---
                    try:
                        put_params = p_data.get("ROBOT_COMMAND_POSITION_PARAMS", {}) \
                            .get("EXTERNAL_BIN_OP_PUT", {}) \
                            .get("DOWN", {})

                        target_list_2 = put_params.get("lift_report_dis@", [])

                        for item in target_list_2:
                            if item.get("locationType") == 10:
                                # 不管原来是多少，强制改成 -0.15
                                if item.get("@") != -0.15:
                                    print(f"   ℹ️ [修改2] 提升上报距离 Type 10: {item.get('@')} -> -0.15")
                                    item["@"] = -0.15
                                    modified_flag = True
                    except Exception as e:
                        print(f"   ⚠️ 查找 lift_report_dis 路径失败: {e}")

                    # 只要进了 command profile 就没必要继续遍历其他 profile 了 (通常只有一个 command)
                    break

        if not modified_flag:
            print("   ⚠️ 未做任何修改 (可能值已经是目标值，或者 JSON 路径不匹配)")

    except Exception as e:
        raise Exception(f"JSON 结构遍历/修改失败: {e}")

    # 3️⃣ 【保存到本地临时文件】
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".json", encoding='utf-8') as tmp_f:
        json.dump(content, tmp_f, indent=4)
        local_tmp_path = tmp_f.name

    try:
        # 4️⃣ 【上传】
        print(f"   ↳ 正在上传修改后的文件...")
        sftp = client.open_sftp()
        sftp.put(local_tmp_path, remote_tmp_path)
        sftp.close()

        # 5️⃣ 【覆盖】
        print("   ↳ 正在写入最终位置 (sudo mv)...")
        mv_cmd = f"sudo mv {remote_tmp_path} {REMOTE_CONF_PATH}"
        if sudo_password:
            mv_cmd = f"echo '{sudo_password}' | sudo -S -p '' mv {remote_tmp_path} {REMOTE_CONF_PATH}"

        stdin, stdout, stderr = client.exec_command(mv_cmd)
        exit_status = stdout.channel.recv_exit_status()

        if exit_status == 0:
            print(f"   ✅ {ip} 参数修改成功！")
        else:
            raise Exception(f"sudo mv 失败: {stderr.read().decode()}")

    finally:
        # 清理本地文件
        if os.path.exists(local_tmp_path):
            try:
                os.remove(local_tmp_path)
            except:
                pass


# =========================
# ✅ 单台机器人操作流程
# =========================
def operate_robot(ssh_cfg):
    ip = ssh_cfg["ip_address"]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"\n🔗 开始连接 {ip} ...")

        client.connect(
            hostname=ssh_cfg["ip_address"],
            username=ssh_cfg["username"],
            password=ssh_cfg["password"],
            port=ssh_cfg["port"],
            timeout=10
        )

        print(f"✅ {ip} 连接成功")

        # 1️⃣ 停止节点
        stdout, stderr = stop_node(client)
        print(f"{ip} 停止节点完成")

        # 2️⃣ 修改参数 (Business Tuning)
        modify_business_tuning_params(ip, client, username=ssh_cfg['username'], sudo_password=ssh_cfg['password'])

        time.sleep(1)

        # 3️⃣ 重启服务
        stdin, stdout, stderr = client.exec_command(
            "sudo /etc/kubot_application.sh start"
        )
        exit_status = stdin.channel.recv_exit_status()
        print(f"{ip} ✅ 服务已重启，状态码: {exit_status}")

    except Exception as e:
        print(f"❌ {ip} 发生错误: {e}")

    finally:
        client.close()
        print(f"{ip} ✅ 连接已关闭")


# =========================
# ✅ 主入口
# =========================
def main():
    ssh_info = read_ssh_csv(CSV_FILE_PATH)

    if not ssh_info:
        print("❌ CSV 中没有读取到任何设备，程序终止")
        return

    ssh_cfgs = list(ssh_info.values())
    print("\n✅ 设备列表:")
    for cfg in ssh_cfgs:
        print(f" - {cfg['hostname']} @ {cfg['ip_address']}")

    # 并发执行
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(operate_robot, cfg) for cfg in ssh_cfgs]
        concurrent.futures.wait(futures)

    print("\n✅ ✅ ✅ 所有设备操作完成")


if __name__ == "__main__":
    main()