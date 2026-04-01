import os.path

import requests
import json
import time
from datetime import datetime

# 接口URL提取为全局变量，方便统一修改
BASE_URL = "http://10.201.160.113:9000/tms/createWmsOutboundTask"
# 每次下发任务后的等待时间（单位：秒），可根据需求调整
WAIT_SECONDS = 0.1
# 多个容器编码
CONTAINER_CODES = [
    "C000551035",
]
def load_containers_from_file(file_path):
    if not os.path.exists(file_path):
        print(f"错误，找不到文件")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        containers = [item.strip() for item in content.replace(","," ").split() if item.strip()]
# -------------------------- 核心函数（保持稳定，适配多容器传入） --------------------------
def create_wms_outbound_task(container_code,
                             base_url=BASE_URL,  # 默认使用全局URL变量
                             group_priority=0, task_priority=0):
    """
    创建WMS出库任务的封装函数（适配多容器，单个容器仅执行1次）

    参数:
        container_code (str): 容器编码（必填）
        base_url (str): 请求接口地址（可选，默认使用全局BASE_URL）
        group_priority (int): 任务组优先级（可选，默认0）
        task_priority (int): 单个任务优先级（可选，默认0）

    返回:
        dict: 成功返回接口响应数据；失败返回包含"error"键的字典
    """
    # 生成带时间戳的任务编码（Re-开头+毫秒级时间戳）
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]  # 毫秒级时间戳
        task_code = f"Re-{timestamp}"
        task_group_code = task_code

        # 构造请求体（保留接口要求格式，toLocationCode为空值）
        payload = json.dumps({
            "taskGroupCode": task_group_code,
            "groupPriority": group_priority,
            "tasks": [
                {
                    "taskCode": task_code,
                    "taskPriority": task_priority,
                    "taskDescribe": {
                       # "fromLocationCode": location_code,
                        "containerCode": "D000000164",
                        "toStationCode": "OUT-S-101"
                    }
                }
            ]
        })

        # 请求头
        headers = {
            'Content-Type': 'application/json'
        }

        # 发送POST请求
        response = requests.post(
            base_url,
            headers=headers,
            data=payload,
            timeout=10  # 10秒超时
        )
        response.raise_for_status()  # 捕获HTTP状态码异常（4xx/5xx）

        # 解析响应并返回
        result = response.json()
        print(f"✅ 任务创建成功！任务编码：{task_code} | 容器编码：{container_code} | result {result}")
        return result

    except requests.exceptions.Timeout:
        error_msg = "错误：请求超时，请检查网络或目标服务是否可用"
        print(f"❌ 任务创建失败 | 容器编码：{container_code} | {error_msg}")
        return {"error": error_msg}
    except requests.exceptions.ConnectionError:
        error_msg = "错误：无法连接到目标服务器，请检查URL是否正确"
        print(f"❌ 任务创建失败 | 容器编码：{container_code} | {error_msg}")
        return {"error": error_msg}
    except requests.exceptions.HTTPError as e:
        error_msg = f"错误：HTTP请求失败，状态码：{response.status_code}，详情：{str(e)}"
        print(f"❌ 任务创建失败 | 容器编码：{container_code} | {error_msg}")
        return {"error": error_msg, "status_code": response.status_code}
    except Exception as e:
        error_msg = f"错误：任务创建失败，未知异常：{str(e)}"
        print(f"❌ 任务创建失败 | 容器编码：{container_code} | {error_msg}")
        return {"error": error_msg}


if __name__ == "__main__":
    task_total = len(CONTAINER_CODES)
    print(f"开始批量下发任务，共{task_total}个任务（每个容器仅下发1次），每次间隔{WAIT_SECONDS}秒...\n")

    # 循环遍历容器编码列表，逐个容器下发1次任务
    for idx, container_code in enumerate(CONTAINER_CODES, start=1):
        print(f"正在处理第{idx}个任务：")
        # 调用核心函数，为当前容器创建1次任务
        result = create_wms_outbound_task(container_code=container_code)

        # 不是最后一个任务时，添加等待时间
        if idx < task_total:
            print(f"等待{WAIT_SECONDS}秒后下发下一个容器任务...\n")
            time.sleep(WAIT_SECONDS)

    print("\n✅ 所有容器任务处理完成！")