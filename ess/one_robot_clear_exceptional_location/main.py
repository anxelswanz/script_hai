import json
import random
import time
from time import sleep
from tool.logger import logger
import flask
from typing import List
import datetime
import requests
import logging
import os

# 配置日志：保存到当前文件夹下的 robot_task.log，使用追加模式 (filemode='a')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("robot_task.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()  # 同时在控制台打印
    ]
)
logger = logging.getLogger(__name__)

file_path = "location.xlsx"
host = "http://10.201.160.113:9000"
headers = {"Content-Type": "application/json; charset=UTF-8", 'Connection': 'close'}
robot_id = "kubot-121"

LOCATION_SELECTED = ""
ALL_LIST = []
server = flask.Flask(__name__)
IF_SKIP_CURRENT_TASK = False
CURRENT_UNFINISHED_TASK = ""


class Location:
    positionX: str
    positionY: str
    locationCode: str
    container: str
    def __str__(self):
        return f"Location(code='{self.locationCode}', x='{self.positionX}', y='{self.positionY}', container={container})"

    def __repr__(self):
        # 建议同时实现 __repr__，这样在打印 [列表] 时也能看到内容
        return self.__str__()


class Robot:
    positionX: str
    positionY: str
    robot_code: str

    def __str__(self):
        return f"Location(code='{self.locationCode}', x='{self.x}', y='{self.y}')"

    def __repr__(self):
        # 建议同时实现 __repr__，这样在打印 [列表] 时也能看到内容
        return self.__str__()


import pandas as pd
import re


def getAllList():
    return extract_coords_from_excel(file_path)

import pandas as pd
import re


def extract_coords_from_excel(file_path, sheet_name=0):
    # 1. 读取 Excel 文件
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name)
    df = df_raw.dropna(subset=[df_raw.columns[0], df_raw.columns[3]])
    results = []
    # 使用 range(len(df)) 通过行索引遍历，方便同时访问 A 列和 M 列
    for i in range(len(df)):
        # 获取 M 列数据 (索引 12)
        entry = df.iloc[i, 12]
        # 获取 第一列 (A 列) 数据 (索引 0)
        code_val = df.iloc[i, 0]
        container_val = df.iloc[i, 3]
        if pd.isna(entry):
            continue

        # 3. 使用正则提取 x 和 y 的值
        x_match = re.search(r'x:\s*(\d+)', str(entry))
        y_match = re.search(r'y:\s*(\d+)', str(entry))
        if x_match and y_match:
            location = Location()
            # 提取正则匹配的第一个分组并赋值
            location.positionX = x_match.group(1)
            location.positionY = y_match.group(1)
            location.container = container_val
            # 升级点：将第一列的值赋给 locationCode
            # 如果第一列可能是数字，建议根据需要转成 str(code_val)
            location.locationCode = code_val
            results.append(location)
            print(f"[DEBUG] x: {location.positionX}, y: {location.positionY}, container: {location.container}, locationCode: {location.locationCode}")
    return results


def cancel_wms_task(task_code):
    url = "http://10.201.160.113:9003/ess-api/wms/cancelWmsTask"
    print(f"cancel 获取到的task_code: {task_code}")
    # 构建负载数据
    payload = {
        "taskCode": task_code
    }

    try:
        # 发送 POST 请求，json 参数会自动设置 Content-Type 为 application/json
        response = requests.post(url, json=payload, timeout=10)

        # 打印响应结果以便调试
        print(f"cancel 状态码: {response.status_code}")
        print(f"cancel 响应内容: {response.text}")

        # 检查是否请求成功
        if response.status_code == 200:
            return response.json()
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求发生异常: {e}")
        return None

def check_suspend_task():
    """
    查询传输任务并校验机器人 ID
    :param host: 接口地址前缀 (例如 "http://127.0.0.1:8080")
    :param robot_id: 需要匹配的机器人编号
    :return: bool
    """
    url = host + "/ess-api/task/queryTransportTask"

    # 构造请求体
    payload = {
        "state": "SUSPEND",
        "columns": "code,state,taskType,parentTaskCode,groupCode,containerCode,intendedRobotCode,fromLocationCode,toLocationCode,priority",
        "page": 1,
        "limit": 20
    }

    try:
        # 发送 POST 请求
        response = requests.post(url, json=payload, timeout=10)
        print(f"查询挂起数据: {response.text}")
        # 检查 HTTP 状态码
        if response.status_code != 200:
            print(f"请求失败，状态码: {response.status_code}")
            return False

        data_json = response.json()

        # 解析响应数据
        # 路径: data -> transportTasks (列表)
        tasks = data_json.get("data", {}).get("transportTasks", [])

        if not tasks:
            return False

        # 遍历任务列表，检查是否有匹配的机器人 ID
        for task in tasks:
            if task.get("intendedRobotCode") == robot_id:
                print("find intendedRobotCode: ", robot_id)
                return True

        return False

    except requests.exceptions.RequestException as e:
        print(f"发生网络异常: {e}")
        return False


# 使用示例
# data = extract_coords_from_excel('你的文件.xlsx')
# print(data)

def queryContainer(limit):
    url = host + "/wms/locationQuery"
    data = json.dumps({
        "locationTypeCodes": ["LT_SHELF_STORAGE"]
    })
    locations = []
    re = requests.post(url, data=data, headers=headers)
    req = json.loads(re.text)
    all_locations = req.get("data", {}).get("locations",[])

    locations = []
    while True:
        for i in all_locations:
            if not i.get("locationCode").endswith("coop_kubot") \
                and i.get("loadContainerCode") == "" \
                and i.get("isLocked") is False \
                and i.get("isAbnormal") is False:
                location = Location()
                location.locationCode = i.get("locationCode")
                location.positionX = i.get("positionX")
                location.positionY = i.get("positionY")
                # print(location)
                locations.append(location)
            if len(locations) >= limit + 10:
                break
        break
    if len(locations) < 10:
        raise RuntimeError("Please pay attention to available storage locations")
    random.shuffle(locations)
    return locations

def get_robot_location():
    url = f"http://10.201.160.113:9000/ess-api/model/queryModelByCode?modelCode={robot_id}"
    try:
        logger.info(f"正在查询机器人状态，URL: {url}")
        response = requests.get(url, timeout=10)
        res_data = response.json()

        robot_data = res_data.get("data", {}).get("robot", {})
        position = robot_data.get("precisePosition", {})
        if position:
            robot = Robot()
            robot.robot_code = robot_id
            robot.positionX = position.get("x")
            robot.positionY = position.get("y")
            return robot
        else:
            logger.info(f"机器人 {robot_id} 获取信息失败")
            return None
    except Exception as e:
        logger.exception(f"调用接口发生异常: {str(e)}")
        return None


def distance_calculation(locations: List[Location]):
    if not locations:
        return None
    robot_location = get_robot_location()
    rx = float(robot_location.positionX)
    ry = float(robot_location.positionY)
    print(f"Get robot's location information -> rx: {rx} ry: {ry}")
    min_distance = float("inf")
    closest_location = None
    for location in locations:
        lx = float(location.positionX)
        ly = float(location.positionY)
        distance = abs(rx-lx)+abs(ry-ly)
        if distance < min_distance:
            min_distance = distance
            closest_location = location
    locations.remove(closest_location)
    return min_distance, closest_location

def createAction(robot_id, action, location, container=None):
    if container is None:
        container = ""
    url = host + "/ess-api/wms/createActionTask"
    timestamp = int(time.time() * 1000)
    generated_task_code = f"{action}-{timestamp}-0"

    data = json.dumps({
        "robotCode": robot_id,
        "tasks": [
            {
                "taskAction": action,
                "taskCode": generated_task_code,
                "isFinallyPaused": False,
                "containerCode": container,
                "locationCode": location
            }
        ]
    })

    try:
        re = requests.post(url, data=data, headers=headers)
        print(f"request successfully {re.text}")
        return re.json()
    except Exception as e:
        print(f"create task failure {e}")
        return None


import pandas as pd


def read_excel_to_tuples(file_path, sheet_name=0):
    """
    读取 Excel 的 A 列和 D 列，并转换为元组列表
    :param file_path: Excel 文件路径
    :param sheet_name: 工作表名称或索引，默认为第一个 sheet
    :return: List[tuple]
    """
    try:
        # 1. 读取 Excel，usecols 支持列名(如 'A, D') 或 索引(如 [0, 3])
        # 这里使用 'A, D' 更加直观
        df = pd.read_excel(file_path, sheet_name=sheet_name, usecols="A, D")

        # 2. 核心逻辑：dropna 会删除任何包含空值（NaN）的行
        # how='any' 表示 A 或 D 只要有一个为空就整行跳过
        df_clean = df.dropna(how='any')

        # 3. 将每一行转换为元组，并存入列表
        # itertuples(index=False) 会忽略行号，只保留数据
        result = [tuple(x) for x in df_clean.values]

        return result

    except Exception as e:
        print(f"读取文件出错: {e}")
        return []



current_container = ""
next = 0
all_location_container_data = []

@server.route('/task/unloadContainerDone', methods=['get', 'post'])
def kubotUnloadCallback():
    print("callback unload done!")
    #createAction(robot_id=robot_id, action="unload", container=container, location=location)
    pass

@server.route('/task/loadContainerDone', methods=['get', 'post'])
def kubotLoadCallback():
    print("callback load done!")
    #createAction(robot_id=robot_id, action="unload", container=container, location=location)
    pass

def current_robot_task(robot_code):
    url = f"http://10.201.160.113:9000/ess-api/model/queryModelByCode?modelCode={robot_code}"
    try:
        logger.info(f"正在查询机器人状态，URL: {url}")
        response = requests.get(url, timeout=10)
        res_data = response.json()
        robot_data = res_data.get("data", {}).get("robot", {})
        unfinished_tasks = robot_data.get("unfinishedTransportTaskCode", {})
        if unfinished_tasks:
            logger.info(f"机器人 {robot_code} 当前有未完成任务: {list(unfinished_tasks.keys())}")
            return list(unfinished_tasks.keys())[0]
        else:
            logger.info(f"机器人 {robot_code} 当前没有未完成任务。")
            return None
    except Exception as e:
        logger.exception(f"调用接口发生异常: {str(e)}")
        return None



def check_robot_tasks(robot_code):
    url = f"http://10.201.160.113:9000/ess-api/model/queryModelByCode?modelCode={robot_code}"
    try:
        logger.info(f"正在查询机器人状态，URL: {url}")
        response = requests.get(url, timeout=10)
        res_data = response.json()
        robot_data = res_data.get("data", {}).get("robot", {})
        unfinished_tasks = robot_data.get("unfinishedTransportTaskCode", {})
        if unfinished_tasks:
            logger.info(f"机器人 {robot_code} 当前有未完成任务: {list(unfinished_tasks.keys())}")
            return True
        else:
            logger.info(f"机器人 {robot_code} 当前没有未完成任务。")
            return False
    except Exception as e:
        logger.exception(f"调用接口发生异常: {str(e)}")
        return False

def start_polling(robot_code, task, interval_seconds=30, generated_task_code=None):
    print(f"开始轮询机器人状态，间隔: {interval_seconds}秒。若无任务将自动退出...")
    logger.info(f"开始轮询机器人状态，间隔: {interval_seconds}秒。若无任务将自动退出...")
    global IF_SKIP_CURRENT_TASK
    try:
        while True:
            # 检查是否挂起
            flag = check_suspend_task()
            if flag:
                cancel_wms_task(generated_task_code)
                # 取消完成后查询目前是否有任务，如果没有任务就可以停止
                # 如果这个任务被成功取消，那么就不进行放箱任务
                IF_SKIP_CURRENT_TASK = True
                print(f"应更改 IF_SKIP_CURRENT_TASK: {IF_SKIP_CURRENT_TASK}")
                break;
            status = check_robot_tasks(robot_code)
            if not status:
                print("检测到退出信号（无任务或异常），轮询结束。")
                logger.info("检测到退出信号（无任务或异常），轮询结束。")
                break
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        logger.info("用户手动停止了程序 (Ctrl+C)")

# 读取excel文件
# 寻找可用库位
# 查询机器人当前点位，使用算法查找最近一个库位
# 下发取箱任务
# 进行30s轮询，查询机器人是否完成当前取箱任务
# 任务完成，下发放箱任务
# 进行30s轮询，查询机器人是否完成放箱任务
# 一个循环结束


# 中途不能取消任务，因为取消任务以后轮询会查到任务为空会自动去做一个空的unload


if __name__ == '__main__':
    list_data = getAllList()
    LOCATION_SELECTED = len(list_data)

    # print(f"[DEBUG] before {len(list_data)}")
    while len(list_data) > 0:
        print("开始新一轮任务")
        # 充值参数
        IF_SKIP_CURRENT_TASK = False
        min_distance, closest_take_location = distance_calculation(list_data)
        container = closest_take_location.container
        locationCode = closest_take_location.locationCode
        print(f"[DEBUG] 还剩: {len(list_data)}")
        print(f"[INFO] find target container {container} & target location: {locationCode}")
        locations = queryContainer(LOCATION_SELECTED)
        # min_distance, closest_put_location = distance_calculation(locations)
        print(f"found the closest location: {closest_take_location.locationCode}...now go take the container {container}")
        createAction(robot_id=robot_id,action="load", location=locationCode)
        task_code = current_robot_task(robot_id)
        print(f"获取task_code: {task_code}" )
        start_polling(robot_id, "load", generated_task_code=task_code)
        sleep(5)
        print(f"start_polling IF_SKIP_CURRENT_TASK 状态: {IF_SKIP_CURRENT_TASK}")
        if not IF_SKIP_CURRENT_TASK:
            print(f"{container} is taken by robot {robot_id}, now let's place the container in {closest_take_location.locationCode}...")
            createAction(robot_id=robot_id, action="unload", location=closest_take_location.locationCode, container=container)
            print("task created now let's do the polling....")
            start_polling(robot_id, "unload", generated_task_code=task_code)
            sleep(1)
            now = datetime.now()
            formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"{formatted_time} 已清除异常库位 {closest_take_location.locationCode}")
            print(f"this task all done now let's do next one....")
        else:
            now = datetime.now()
            formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
            logger.error(f"{formatted_time} {closest_take_location.locationCode}机器人无法取，需要人工取出")

# if __name__ == '__main__':
#     # 1. 初始化数据
#     list_data = read_excel_to_tuples(file_path)
#     all_location_container_data = list_data
#
#     if not all_location_container_data:
#         print("Excel 数据为空，请检查文件！")
#     else:
#         LOCATION_SELECTED = len(all_location_container_data)
#         # 获取可用位置
#         #locations = queryContainer(LOCATION_SELECTED)
#
#         # 取第一条数据准备触发
#         (location, container) = all_location_container_data[next]
#         print(f"准备发送任务: Location={location}, Container={container}")
#
#         # 发送第一个任务
#         # 注意：这里发送后，机器人完成后会回调你定义的接口
#         createAction(robot_id, "load", container, location)
#
    # 2. 关键：启动 Flask 服务器，监听回调
    # host='0.0.0.0' 表示允许外部 IP 访问，port 是端口号
    # debug=False 建议在生产/测试脚本中关闭，防止重复加载导致 AssertionError
    #print("正在启动回调服务器...")
    #server.run(host='0.0.0.0', port=5234, debug=False)



# locations = queryContainer()
# print(locations)
# min_distance, closest_location = distance_calculation(locations)
# print(f"找到: {min_distance}", f"和: {closest_location}")


