import math
import random
import threading
import time

import flask
import json

import requests
import datetime
from concurrent.futures import ThreadPoolExecutor
# from log_handler import logger

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


def createOutBound(taskNum=None,hasTaskContainer=None,cacheShelfContainerCode=None):
    url = host + "/tms/createWmsOutboundTask"
    if cacheShelfContainerCode is not None:
        containerCodes = [cacheShelfContainerCode]
    else:
        container_b = queryContainer()
        container_s = queryContainer_s()
        containerCodes = container_b + container_s
        random.shuffle(containerCodes)

    data = {
        "taskGroupCode": "",
        "tasks": [

        ]
    }
    newTaskContainer = []
    for j in containerCodes:
        if hasTaskContainer is not None:
            if j not in hasTaskContainer:
                newTaskContainer.append(j)
                if  len(newTaskContainer) == taskNum:
                    break
        elif hasTaskContainer is None:
            newTaskContainer.append(j)
    chunk_size = 200
    newTaskArray = [newTaskContainer[i:i + chunk_size] for i in range(0, len(newTaskContainer), chunk_size)]
    for sublist in newTaskArray:
        for i in sublist:
            data["tasks"].append({
                "taskTemplateCode": "",
                "taskCode": "LABOR_2-" + str(int(time.time() * 1000)) + i,
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
    return containers


def queryContainer_s():
    url = host + "/ess-api/monitor/location/query"
    containers = []
    location_heads = []

    for column in range(cShelfStart, cShelfEnd + 1):
        for row in range(rShelfStart, rShelfEnd + 1):
            c = "%03d" % column
            location_heads.append(f"HAI-{c}-{row}")

    def fetch_containers(location_head):
        data = json.dumps({"page": 1, "size": 50, "code": location_head, "isShelfStorage": True})
        re = requests.post(url, data=data, headers=head).json()
        return [i["containerCode"] for i in re["data"]["locations"] if i["containerCode"] != '' and not i["isLocked"]]

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_containers, location_heads)

    for result in results:
        containers.extend(result)

    return containers


# def queryContainer_s():
#     url = host + "/ess-api/monitor/location/query"
#     containers = []
#     for column in range(cShelfStart, cShelfEnd + 1):
#         for row in range(rShelfStart, rShelfEnd + 1):
#             c = "%03d" % column
#             locationHead = f"HAI-{c}-{row}"
#             data = json.dumps({"page":1,"size":50,"code":locationHead,"isShelfStorage":True})
#
#             re = requests.post(url, data=data, headers=head).json()
#             for i in re["data"]["locations"]:
#                 if i["containerCode"] != '' and i["isLocked"] is False:
#
#                     containers.append(i["containerCode"])
#
#     return containers


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
        if i["locationCode"] == "LT_LABOR:POINT:157775:152788":
            locations.append(i["locationCode"])
    return locations


def queryTask():
    url = f'{host}/ess-api/model/queryModelByType?modelType=wms_task'
    re = requests.get(url).json()
    taskCount = 0
    hasTaskContainers = []
    for i in re["data"]["wmsTask"]:
        if i["state"] in ['PENDING', 'PROCESSING'] and i["code"].startswith("LABOR_2"):
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
    eventCode = _json["eventCode"]
    containerCode = _json["containerCode"]
    locationCode = _json["locationCode"]
    stationCode = _json["stationCode"]
    if eventCode == "CALLBACK_OF_TOTE_UNLOADED_BY_ROBOT" and stationCode in cacheShelfStationCodes and "_coop_haiflex" in locationCode:
        locationCodeHead = locationCode[0:7]
        if locationCodeHead in cacheShelfHead:
            print(f"kivaAndKubotCallback被调用 时间: {datetime.datetime.now()}")
            print(json.dumps(_json, indent=4, separators=(', ', ': '), ensure_ascii=False))
            threading.Thread(createOutBound(cacheShelfContainerCode=containerCode)).start()
            print(f"容器 {containerCode} 被放置到缓存位 {locationCode} 直接给这个容器下发出库任务")

    resu = {'code': 0, "msg": ""}
    return json.dumps(resu, ensure_ascii=False), {"Content-Type": "application/json"}


def createTask() -> object:
        # # 任务数量低于30时补发出库任务
        # processingTaskCount, hasTaskContainer = queryTask()
        # #if processingTaskCount < tasksNumber:
        #     #createTaskNum = tasksNumber - processingTaskCount
        # createOutBound(tasksNumber,hasTaskContainer)
    processingTaskCount, hasTaskContainer = queryTask()
    createOutBound(tasks, hasTaskContainer)
    while True:
        # 任务数量低于30时补发出库任务
        try:
            processingTaskCount, hasTaskContainer = queryTask()
            if processingTaskCount < tasksNumber:
                createTaskNum = tasksNumber - processingTaskCount
                print(f"补充任务量： {createTaskNum}")
                createOutBound(createTaskNum, hasTaskContainer)
            time.sleep(13)
        except Exception as e:
            print(f"任务下发定时任务报错：{e} 正在重试")
            pass


def queryRobotJob():
    atLaborRobot = {}
    while True:
        try:
            # 查询在工作位等待的机器人
            robRes = queryRobot()
            laborLocations = queryLocation()
            for i in robRes["data"]["robot"]:
                if i["belongLocationCode"] in laborLocations and i["code"] not in atLaborRobot:
                    print(f"机器人 {i} 在datetime.datetime.now()")
                    # 记录到岗
                    print(
                        f"[流程监控] 机器人 {i['code']} 在{datetime.datetime.now()}时间 已到达工位 LABOR_1，开始计时，预定放行时间: {waitingTime}秒后")
                    atLaborRobot[i["code"]] = datetime.datetime.now()

            now = datetime.datetime.now()
            for key, timestamp in atLaborRobot.items():
                if (now - timestamp).total_seconds() > waitingTime:
                    print(f'let robot {key} go {(now - timestamp).total_seconds()}')
                    print(f"[流程监控] 机器人 {key} 停留已满 {(now - timestamp).total_seconds()}秒，执行放行指令")
                    letRobotGo(key)
            atLaborRobot = {key: timestamp for key, timestamp in atLaborRobot.items() if
                            (now - timestamp).total_seconds() <= waitingTime}
            time.sleep(1)
        except Exception as e:
            print(f"让机器人离开的定时任务报错： {e} 正在重试")
            pass




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


if __name__ == '__main__':
    now1=int(time.time())
    host = "http://10.201.160.103:9000"
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
    stations = "LABOR_2"
    # 机器人在人工工作站等待时间（秒）
    waitingTime = 17

    # 一次性下发的任务数量
    tasks = 20
    # 任务低于多少时需要补发 任务
    tasksNumber = 16

    # 小箱货架排
    cShelfStart = 59
    cShelfEnd = 62

    # 小箱货架列
    rShelfStart = 200
    rShelfEnd = 236

    # 缓存货架工作站编码
    cacheShelfStationCodes = ["LA_MINI_HAIFLEX_SHELF_STORAGE", "LA_MINI_HAIFLEX_SHELF_STORAGE_POC"]

    # 放箱后需要直接出库的缓存位
    cacheShelfHead = ["HAI-066", "HAI-062", "HAI-061"]

    # 启动持续让机器人离开的进程
    threading.Thread(target=lambda: queryRobotJob()).start()
    threading.Thread(target=lambda: createTask()).start()
    server.run(debug=True, port=1002, host='10.201.157.240')




