import pandas as pd
import yaml
import json
import requests
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from Robot import Robot
import sys
import os

limit = 20
all_robots = []
print("===================================")
print("Mischievous Robot for Exception Location - v1.0")
print("===================================")
print("""   
    |Come and find me....|
        \\/
      .---.
     |o_o |
     |_^_|
    //   \\\\
   (|     |)
   / \\___/ \\
   \__|_|__/
""")
print("developed by ansel zhong @Hairobotics ^_^")
print("===================================")
print("kindly remind everyone that remember to take a rest when you are tired.")
# --- 1. 配置日志系统 ---
log_filename = f"robot_query_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'), # 保存到文件
       # logging.StreamHandler() # 同时输出到控制台
    ]
)

# 加载配置文件
def load_config(file_path="config.yaml"):
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

config = load_config()
api_cfg = config["api_config"]

def log_position_frequency():
    """统计频率并保存到单独的 output.txt 文件中"""
    global all_robots

    if not all_robots:
        logging.warning("No record. Can't do anything.")
        return

    # 1. 统计逻辑
    robot_models = {}

    for r in all_robots:
        name = r.get("roughPosition", "unknown")
        if name not in robot_models:
            robot_models[name] = Robot(name)
        time = r.get("createTime")
        readable_time = format_timestamp(time)
        robot_models[name].add_record(
            readable_time,
            r.get("containerCode"),
        )

    sorted_robots = sorted(
        robot_models.values(),
        key=lambda x:x.count,
        reverse=True
    )

    # 2. 写入到 output.txt (使用 'w' 模式每次覆盖，或 'a' 模式追加)
    try:
        with open("output.txt", "w", encoding="utf-8") as f:
            # 写入标题和时间戳，方便识别
            f.write(f"Execution time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            counter = 1
            for robot in sorted_robots:
                # print(f"#{counter} {robot.get_report()}")
                f.write(f"#{counter} {robot.get_report()}")
                counter += 1
        # 依然在原来的日志文件里记录一条通知
        logging.info("The result is now in: output.txt")
    except Exception as e:
        logging.error(f"Write output.txt failed: {e}")


def process_excel_pandas(file_path):
    if not os.path.exists(file_path):
        error_msg = f"Critical Error: The file '{file_path}' was not found."
        #print(f"\n{error_msg}")
        logging.error(error_msg)
        return

    try:
        df = pd.read_excel(file_path, usecols="D")
        column_name = df.columns[0]
        valid_data = df[column_name].dropna().tolist()
    except Exception as e:
        logging.error(f"Failed to read Excel: {e}")
        return

    total_count = len(valid_data)
    if total_count == 0:
        logging.warning("No valid data found.")
        return

    logging.info(f"Starting task: {total_count} containers.")

    # 定义旋转图标
    spinners = ['|', '/', '-', '\\']
    completed = 0

    # print("\nProcessing Tasks:")  # 打印一个起始提示

    with ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有任务
        future_to_container = {executor.submit(get_latest_robot_position, val): val for val in valid_data}

        # 每当一个任务完成时触发
        for future in as_completed(future_to_container):
            completed += 1
            # 计算当前旋转图标的索引
            idx = completed % len(spinners)
            char = spinners[idx]

            # 使用 \r 实现原地刷新
            # 显示格式： [ / ] 加载 (12/200) ...
            print(f"\r [{char}] 加载 ({completed}/{total_count}) ...".ljust(40), end="", flush=True)

    # print(f"\n\nProcessing complete. {total_count} tasks finished.")
    log_position_frequency()

def format_timestamp(ts):
    """将毫秒级时间戳转换为易读的字符串格式"""
    if not ts: return "未知时间"
    # 除以 1000 将毫秒转为秒
    dt = datetime.datetime.fromtimestamp(ts / 1000.0)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def get_latest_robot_position(container):
    # 获取配置中的 headers 并确保 User-Agent 存在
    headers = api_cfg.get("headers", {}).copy()
    if "User-Agent" not in headers:
        headers[
            "User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    try:
        payload = {
            "containerCode": container,
            "page": 1,
            "limit": api_cfg["limit"]
        }

        cookie = api_cfg["cookies"]
        # 简单处理 session_token 格式
        if isinstance(cookie, dict) and 'session_token' in cookie:
            cookie['session_token'] = cookie['session_token'].replace("session_token=", "", 1)

        # 发起请求
        response = requests.post(
            api_cfg["url"],
            headers=headers,
            cookies=cookie,
            json=payload,
            verify=False,
            timeout=10  # 建议增加超时设置，防止脚本卡死
        )

        # 检查 HTTP 状态码
        response.raise_for_status()
        res_data = response.json()

        if res_data.get("code") == 0:
            positions = res_data.get("data", {}).get("position", [])
            robot_positions = [p for p in positions if p.get("positionType") == "ROBOT"]

            if not robot_positions:
                logging.warning(f"Container {container}: No ROBOT data found.")
                return None

            robot_positions.sort(key=lambda x: x["createTime"], reverse=True)
            latest_robot = robot_positions[0]
            all_robots.append(latest_robot)

            # 记录成功日志
            logging.info(f"Successfully processed container: {container} -> RobotID: {latest_robot.get('robotCode')}")
            return latest_robot
        else:
            # 记录业务错误日志并退出
            err_msg = f"API Business Error for {container}: {res_data.get('msg')} (Code: {res_data.get('code')})"
            logging.error(err_msg)
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        # 捕获网络、超时、404/500 等异常
        logging.error(f"Network error processing container {container}: {str(e)}")
    except Exception as e:
        # 捕获其他未知异常（如 JSON 解析失败）
        logging.error(f"Unexpected error processing container {container}: {str(e)}")
    return None

if __name__ == "__main__":
    # get_latest_robot_position()
    process_excel_pandas("location.xlsx")
