import csv
import json
import paramiko
import tempfile
import os
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================
# ⚙️ 配置区
# =========================
CSV_FILE = "kiva.csv"
REMOTE_CONF_PATH = "/home/kubot/app/config__software-design.json"
MAX_THREADS = 10
LOG_FILENAME = "deploy_result_kubot.log"  # 日志文件名


# =========================
# 📝 日志配置
# =========================
def setup_logging():
    # 创建日志器
    logger = logging.getLogger("DeployLogger")
    logger.setLevel(logging.INFO)

    # 格式：2023-10-27 10:00:00 - INFO - 消息内容
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 1. 文件处理器 (写入文件)
    file_handler = logging.FileHandler(LOG_FILENAME, encoding='utf-8')
    file_handler.setFormatter(formatter)

    # 2. 控制台处理器 (终端打印)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


logger = setup_logging()


# =========================
# 🛠️ 核心修改函数
# =========================
def modify_safety_door_params(client, ip, sudo_password):
    remote_tmp_path = f"/home/kubot/safety_door_tmp_{ip}.json"

    # 1. 读取文件
    cmd_read = f"echo '{sudo_password}' | sudo -S cat {REMOTE_CONF_PATH}"
    stdin, stdout, stderr = client.exec_command(cmd_read)
    file_content = stdout.read().decode().strip()

    if not file_content:
        return False, "无法读取文件或文件不存在"

    # 2. 解析与逻辑修改
    try:
        content = json.loads(file_content)
        modified = False

        for profile in content.get("profiles", []):
            if profile.get("config-field") == "module":
                recv_signals = profile.get("profile-data", {}).get("safety", {}).get("signalmaps", {}).get("recv", {})
                if "config_has_safety_door" in recv_signals:
                    target = recv_signals["config_has_safety_door"]
                    if target.get("value") is not False:
                        target["value"] = False
                        modified = True
                        break

        if not modified:
            return True, "跳过（已经是 False）"

    except Exception as e:
        return False, f"JSON 解析失败: {e}"

    # 3. 写入并回传
    fd, local_path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(content, f, indent=4)

        sftp = client.open_sftp()
        sftp.put(local_path, remote_tmp_path)
        sftp.close()

        mv_cmd = f"echo '{sudo_password}' | sudo -S mv {remote_tmp_path} {REMOTE_CONF_PATH}"
        client.exec_command(mv_cmd)
        return True, "修改成功"
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


# =========================
# 🌐 线程任务封装
# =========================
def process_machine(row):
    hostname, _, ip, username, password = row
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    status = "FAILED"
    message = ""

    try:
        client.connect(ip, username=username, password=password, timeout=10)
        success, msg = modify_safety_door_params(client, ip, password)
        if success:
            status = "SUCCESS"
            message = msg
        else:
            status = "FAILED"
            message = msg
    except Exception as e:
        status = "FAILED"
        message = f"连接异常: {e}"
    finally:
        client.close()

    return hostname, ip, status, message


# =========================
# 🏁 主程序入口
# =========================
def main():
    if not os.path.exists(CSV_FILE):
        logger.error(f"文件 {CSV_FILE} 不存在")
        return

    machines = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and len(row) >= 5:
                machines.append(row)

    logger.info(f"🚀 开始批量处理 {len(machines)} 台机器...")

    success_list = []
    fail_list = []

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_machine = {executor.submit(process_machine, m): m for m in machines}

        for future in as_completed(future_to_machine):
            hostname, ip, status, msg = future.result()
            log_msg = f"{hostname} ({ip}): {msg}"

            if status == "SUCCESS":
                success_list.append(log_msg)
                logger.info(f"✅ [SUCCESS] {log_msg}")
            else:
                fail_list.append(log_msg)
                logger.error(f"❌ [FAILED] {log_msg}")

    # =========================
    # 📊 最终汇总写入
    # =========================
    summary = [
        "\n" + "=" * 50,
        "📊 任务汇总报告",
        f"总计: {len(machines)} | 成功: {len(success_list)} | 失败: {len(fail_list)}",
        "=" * 50
    ]

    for line in summary:
        logger.info(line)

    if fail_list:
       # logger.info("\n🔴 失败详细清单:")
        for item in fail_list:
            logger.info(f"  - {item}")

    logger.info(f"\n✨ 完整日志已保存至: {os.path.abspath(LOG_FILENAME)}")


if __name__ == "__main__":
    main()