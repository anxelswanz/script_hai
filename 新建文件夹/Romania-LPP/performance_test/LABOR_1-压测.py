import math
import random
import threading
import time

import flask
import json

import requests
import datetime
from log_handler import logger

server = flask.Flask(__name__)


def letRobotGo(robotCode):
    url = host + "/ess-api/station/letRobotGo"

    data = {
        "robotCode": robotCode
    }
    # time.sleep(5)
    re = requests.post(url, data=json.dumps(data), headers=head)

    print(re.text)


def queryRobot():
    re = requests.get(f"{host}/ess-api/model/queryModelByType?modelType=robot")
    return json.loads(re.text)


def createOutBound(taskNum1,hasTaskContainer):
    url = host + "/tms/createWmsOutboundTask"
    containerCodes = queryContainer()
    data = {
        "taskGroupCode": "",
        "tasks": [

        ]
    }
    newTaskContainer = []
    for j in containerCodes:
        if j not in hasTaskContainer:
            newTaskContainer.append(j)
            if   len(newTaskContainer) == taskNum1:
                break
    chunk_size = 200
    newTaskArray = [newTaskContainer[i:i + chunk_size] for i in range(0, len(newTaskContainer), chunk_size)]
    for sublist in newTaskArray:
        for i in sublist:
            data["tasks"].append({
                "taskTemplateCode": "",
                "taskCode": "LABOR_1-" + str(int(time.time() * 1000)) + i,
                "taskPriority": 0,
                "deadline": 0,
                "taskDescribe": {
                    "containerCode": i,
                    "toStationCode": stations
                }
            })
        taskJson = json.dumps(data)
        # print(data)
        re = requests.post(url, data=taskJson, headers=head)
        print(re.text)
        data["tasks"].clear()





def queryContainer():
    url = host + "/wms/locationQuery"
    data = json.dumps({
        "locationTypeCodes": [
            "LT_SHELF_STORAGE_POC"
        ]
    })

    re = requests.post(url, data=data, headers=head)
    req = json.loads(re.text)

    containers = []
    for i in req["data"]["locations"]:
        # print(i)
        if i["loadContainerCode"] != "" and i["isLocked"] is False and i["isAbnormal"] is False:
            containers.append(i["loadContainerCode"])
    random.shuffle(containers)
    return containers


def queryLocation():
    url = host + "/wms/locationQuery"
    data = json.dumps({
        "locationTypeCodes": [
            "LT_LABOR"
        ]
    })

    re = requests.post(url, data=data, headers=head)
    req = json.loads(re.text)

    locations = []
    for i in req["data"]["locations"]:
        if i["locationCode"] == "LT_LABOR:POINT:157775:154498":
            locations.append(i["locationCode"])
    return locations


def queryTask():
    url = f'{host}/ess-api/model/queryModelByType?modelType=wms_task'
    re = requests.get(url).json()
    taskCount = 0
    hasTaskContainers = []
    for i in re["data"]["wmsTask"]:
        if i["state"] in ['PENDING', 'PROCESSING'] and i["code"].startswith("LABOR_1"):
            taskCount += 1
            hasTaskContainers.append(i["containerCode"])

    return taskCount, hasTaskContainers


def moveIn(locationCode, containerCode):
    url = host + "/container/moveIn"

    data = json.dumps({
        "containerMoveIns": [
            {
                "containerCode": containerCode,
                "positionCode": locationCode
            }
        ]
    })
    time.sleep(3)
    re = requests.post(url, data=data, headers=head)
    print(f"move in container {containerCode} to {locationCode} response: {re.text}")


def createInbound(containerCode):
    url = host + "/ess-api/tms/createWmsInboundTask"

    data = json.dumps({
        "taskGroupCode": "",
        "groupPriority": 0,
        "tasks": [
            {
                "taskCode": "In" + str(int(time.time() * 1000)),
                "taskTemplateCode": "TOTE_INBOUND",
                "taskDescribe": {
                    "containerCode": containerCode,
                }
            }
        ]
    })
    time.sleep(3)
    re = requests.post(url, data=data, headers=head)
    print(f"create container {containerCode} inbound task, response: {re.text}")


@server.route('/task/unloadContainerDone', methods=['get', 'post'])
def kivaAndKubotCallback():
    _json = flask.request.json
    # print(json.dumps(_json, indent=4, separators=(', ', ': '), ensure_ascii=False))
    eventCode = _json["eventCode"]
    containerCode = _json["containerCode"]
    stationCode = _json["stationCode"]
    if eventCode == "CALLBACK_OF_TASK_FINISHED" and stationCode in stations:
        threading.Thread(createInbound(containerCode))

    resu = {'code': 0, "msg": ""}
    return json.dumps(resu, ensure_ascii=False), {"Content-Type": "application/json"}


def createTask() -> object:
        # # 任务数量低于30时补发出库任务
        # processingTaskCount, hasTaskContainer = queryTask()
        # if processingTaskCount < tasksNumber:
        #     createTaskNum = tasksNumber - processingTaskCount
        # createOutBound(createTaskNum,hasTaskContainer)


    processingTaskCount, hasTaskContainer = queryTask()
    createOutBound(tasks, hasTaskContainer)
    # while True:
    #     # 任务数量低于30时补发出库任务
    #     processingTaskCount, hasTaskContainer = queryTask()
    #     if processingTaskCount < tasksNumber:
    #         createTaskNum = tasksNumber - processingTaskCount
    #         createOutBound(createTaskNum, hasTaskContainer)
    #         logger.info(
    #             f"[任务监控] 当前进行中任务数: {processingTaskCount}, 低于阈值: {tasksNumber}, 准备补发: {createTaskNum}个任务")
    #     time.sleep(50)

# 版本1
# def queryRobotJob():
#     atLaborRobot = {}
#     while True:
#         # 查询在工作位等待的机器人
#         robRes = queryRobot()
#         laborLocations = queryLocation()
#         for i in robRes["data"]["robot"]:
#             # 1. 将机器人字典转换为格式化的 JSON 字符串
#             robot_json_pretty = json.dumps(i, indent=4, ensure_ascii=False)
#
#             # 2. 打印到控制台（方便实时看）
#             # print(f"检测到机器人到岗，完整数据如下:\n{robot_json_pretty}")
#             if i["belongLocationCode"] in laborLocations and i["code"] not in atLaborRobot:
#                 print(f'let robot {i["code"]} at belongLocationCode {i["belongLocationCode"]}')
#                 atLaborRobot[i["code"]] = datetime.datetime.now()
#                 # print(f"机器人 {i} 在datetime.datetime.now()")
#                 # 记录到岗
#                 logger.info(
#                     f"[流程监控] 机器人 {i['code']} 在{datetime.datetime.now()}时间 已到达工位 LABOR_1，开始计时，预定放行时间: {waitingTime}秒后")
#         now = datetime.datetime.now()
#
#         for key, timestamp in atLaborRobot.items():
#             if (now - timestamp).total_seconds() > waitingTime:
#                 print(f'let robot {key} go {(now - timestamp).total_seconds()}')
#                 logger.info(f"[流程监控] 机器人 {key} 停留已满 {(now - timestamp).total_seconds()}秒，执行放行指令")
#                 letRobotGo(key)
#         atLaborRobot = {key: timestamp for key, timestamp in atLaborRobot.items() if
#                         (now - timestamp).total_seconds() <= waitingTime}
#         time.sleep(1)

# 版本2
def queryRobotJob():
    atLaborRobot = {}  # 结构将变为: { robotCode: [时间戳, 容器编码] }
    while True:
        robRes = queryRobot()
        laborLocations = queryLocation()
        for i in robRes["data"]["robot"]:
            if i["belongLocationCode"] in laborLocations and i["code"] not in atLaborRobot:
                # --- 修改点 1: 提取容器编码并存为列表 [时间, 容器] ---
                # 修改后 (增加提取逻辑)  raw_container 拿到的是 {'64': 'D000000870'}
                raw_container = i.get('trayLoadingContainerCode', {})
                # 如果字典不为空，取第一个 value；否则给个空字符串或 None
                container = list(raw_container.values())[0] if raw_container else ""
                atLaborRobot[i["code"]] = [datetime.datetime.now(), container]
                logger.info(f"[流程监控] 机器人 {i['code']} 已到岗，载货: {container}")

        now = datetime.datetime.now()
        # --- 修改点 2: 这里的 timestamp 变成了列表，所以取索引 [0] ---
        for key, val in list(atLaborRobot.items()):
            timestamp = val[0]
            container_code = val[1]
            print(f"拿到container_code: {container_code} ")
            if (now - timestamp).total_seconds() > waitingTime:
                logger.info(f"[流程监控] 机器人 {key} 停留满 {waitingTime}秒，执行放行")
                letRobotGo(key)
                create_wms_outbound_task(container_code)
        # --- 修改点 4: 同样，这里的 timestamp 取 val[0] ---
        atLaborRobot = {key: val for key, val in atLaborRobot.items() if
                        (now - val[0]).total_seconds() <= waitingTime}
        time.sleep(1)

def queryInConveyor():
    url = f'{host}/ess-api/wms/locationQuery'
    data = json.dumps({
        "locationTypeCodes": [
            "LT_CONVEYOR_OUTPUT"
        ]
    })
    re = requests.post(url, data=data, headers=head).json()
    inLocations = []
    for i in re["data"]["locations"]:
        if i["loadContainerCode"] == "":#and i["locationCode"] in ["LT_CONVEYOR_OUTPUT:POINT:12188:81712","LT_CONVEYOR_OUTPUT:POINT:12188:76368"]:
            inLocations.append(i["locationCode"])
    # print("query empty location")
    return inLocations


def containerAdd():
    url = host + "/container/add"

    container = f"container{str(int(time.time() * 1000))}"
    data = json.dumps({
        "containerAdds": [
            {
                "containerCode": container,
                "containerTypeCode": "CT_KUBOT_STANDARD"
            }
        ]
    })
    re = requests.post(url, data=data, headers=head)
    return container


def moveIn(locationCode, containerCode):
    url = host + "/container/moveIn"

    data = json.dumps({
        "containerMoveIns": [
            {
                "containerCode": containerCode,
                "positionCode": locationCode
            }
        ]
    })
    re = requests.post(url, data=data, headers=head)
    print(re.text)


def moveInContainer():
    while True:
        print("query empty location")
        loc = queryInConveyor()

        for i in loc:
            container = containerAdd()
            # if i["containerCode"] == "":
            moveIn(i, container)
            print(f"move in container {container} to {i}")
        time.sleep(inboundTime)
        now=int(time.time())
        #if now - now1 >= 7200:
           # break


def create_wms_outbound_task(container_code,
                            #  base_url=BASE_URL,  # 默认使用全局URL变量
                             group_priority=0, task_priority=0):
    url = host + "/tms/createWmsOutboundTask"
    # 生成带时间戳的任务编码（Re-开头+毫秒级时间戳）
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
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
                        "containerCode": container_code,
                        "toStationCode": "OUT-S-105"
                    }
                }
            ]
        })
        print(payload)
        # 请求头
        headers = {
            'Content-Type': 'application/json'
        }

        # 发送POST请求
        response = requests.post(
            url,
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


if __name__ == '__main__':
    now1=int(time.time())
    host = "http://10.201.160.213:9000"
    head = {"Content-Type": "application/json; charset=UTF-8", 'Connection': 'close'}

    #stations = "conveyor_30-262,conveyor_29-138,conveyor_28-306,conveyor_27-121,conveyor_26-211,conveyor_25-1,conveyor_21-19,conveyor_20-185,conveyor_19-86,conveyor_18-56,conveyor_17-111,conveyor_16-2,conveyor_15-317,conveyor_14-77,conveyor_13-160,conveyor_12-276,conveyor_11-218,conveyor_10-193,conveyor_9-252,conveyor_8-288"
    #stations = "OUT1S,OUT2S,OUT3S,OUT4S,OUT5S,OUT6S,OUT7S,OUT8S,OUT5W,OUT4W"
    #stations = "haiport-40,haiport-39,haiport-38,haiport-37,haiport-36,haiport-35,haiport-34,haiport-33,haiport-32,haiport-31,haiport-30,haiport-29,haiport-28,haiport-27,haiport-26,haiport-25,haiport-24,haiport-23,haiport-22,haiport-21,haiport-20,haiport-19,haiport-18,haiport-17"
    #stations = "LA-02,LA-03,LA-01"



    # 同时入库输送线做入库任务
    # 入库输送线多少秒movein一个箱子
    inboundTime = 3
    # 启动持续movein箱子到入库口进程
    #threading.Thread(target=lambda: moveInContainer()).start()




    # 任务发到哪些工作站，多个用逗号隔开
    stations = "LABOR_1"
    # 机器人在人工工作站等待时间（秒）
    waitingTime = 10
    # 启动持续让机器人离开的进程
    threading.Thread(target=lambda: queryRobotJob()).start()

    # 一次性下发的任务数量
    tasks = 1
    # 任务低于多少时需要补发 任务
    tasksNumber = 0
    createTask()