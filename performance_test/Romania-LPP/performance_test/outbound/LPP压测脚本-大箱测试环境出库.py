import math
import random
import threading
import time

import flask
import json

import requests
import datetime

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


def createOutBound(taskNum,hasTaskContainer):
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
            if len(newTaskContainer) == tasksNumber or len(newTaskContainer) == taskNum:
                break
    chunk_size = 200
    newTaskArray = [newTaskContainer[i:i + chunk_size] for i in range(0, len(newTaskContainer), chunk_size)]
    for sublist in newTaskArray:
        for i in sublist:
            data["tasks"].append({
                "taskTemplateCode": "",
                "taskCode": taskCode + str(int(time.time() * 1000)) + i,
                "taskPriority": 0,
                "deadline": 0,
                "taskDescribe": {
                    "containerCode": "D000000901",
                    "toStationCode": stations
                }
            })
        taskJson = json.dumps(data)
        print(data)
        re = requests.post(url, data=taskJson, headers=head)
        print(re.text)
        data["tasks"].clear()



#容器

def queryContainer():
    url = host + "/wms/locationQuery"
    data = json.dumps({
        # "locationTypeCodes": [
        #     "LT_SHELF_STORAGE",
        #     "LT_MINI_HAIFLEX_SHELF_STORAGE"
        # ]
        "locationTypeCodes": ["LT_SHELF_STORAGE_POC"],
        # "containerTypeCode":"CT_KUBOT_STANDARD_POC"#容器标签containerTypeCode": "CT_KUBOT_STANDARD_POC",
    })

    re = requests.post(url, data=data, headers=head)
    req = json.loads(re.text)

    containers = []
    for i in req["data"]["locations"]:
        # print(i)
        if i["loadContainerCode"] != ""  and i["isAbnormal"] is False:#and i["isLocked"] is False
            containers.append(i["loadContainerCode"])
    random.shuffle(containers)
    print("containers:", len(containers))
    return containers


def queryLocation():
    url = host + "/wms/locationQuery"
    data = json.dumps({
        "locationTypeCodes": [
            "LT_HAIPORT"
        ]
    })

    re = requests.post(url, data=data, headers=head)
    req = json.loads(re.text)

    locations = []
    for i in req["data"]["locations"]:
        locations.append(i["locationCode"])
    return locations


def queryTask():
    url = f'{host}/ess-api/model/queryModelByType?modelType=wms_task'
    re = requests.get(url).json()
    taskCount = 0
    hasTaskContainers = []
    for i in re["data"]["wmsTask"]:
        if i["state"] in ['PENDING', 'PROCESSING']:
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
    print(json.dumps(_json, indent=4, separators=(', ', ': '), ensure_ascii=False))
    eventCode = _json["eventCode"]
    containerCode = _json["containerCode"]
    stationCode = _json["stationCode"]
    if eventCode == "CALLBACK_OF_TASK_FINISHED" and stationCode in stations:
        threading.Thread(createInbound(containerCode))

    resu = {'code': 0, "msg": ""}
    return json.dumps(resu, ensure_ascii=False), {"Content-Type": "application/json"}


def createTask() -> object:
        # 任务数量低于30时补发出库任务
        processingTaskCount, hasTaskContainer = queryTask()
        #if processingTaskCount < tasksNumber:
            #createTaskNum = tasksNumber - processingTaskCount
        createOutBound(tasksNumber,hasTaskContainer)


def queryRobotJob():
    atLaborRobot = {}
    while True:
        # 查询在工作位等待的机器人
        robRes = queryRobot()
        laborLocations = queryLocation()
        for i in robRes["data"]["robot"]:
            if i["belongLocationCode"] in laborLocations and i["code"] not in atLaborRobot:
                print(f'let robot {i["code"]} at belongLocationCode {i["belongLocationCode"]}')
                atLaborRobot[i["code"]] = datetime.datetime.now()
        now = datetime.datetime.now()
        for key, timestamp in atLaborRobot.items():
            if (now - timestamp).total_seconds() > waitingTime:
                print(f'let robot {key} go')
                letRobotGo(key)

        atLaborRobot = {key: timestamp for key, timestamp in atLaborRobot.items() if
                        (now - timestamp).total_seconds() <= waitingTime}
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
        if now - now1 >= 7200:
            break



if __name__ == '__main__':
    now1=int(time.time())
    taskCode = "NEO_TEST2026-3-11"
    host = "http://10.201.160.113:9000"
    head = {"Content-Type": "application/json; charset=UTF-8", 'Connection': 'close'}
    # 任务发到哪些工作站，多个用逗号隔开
    # stations = "OUT1W,OUT2W,OUT3W,OUT4W,OUT5W,OUT1S,OUT2S,OUT3S,OUT4S,OUT5S"#OUT1W,OUT2W,
    stations = "OUT-S-101"  # 目标工作站
    # 机器人在人工工作站等待时间（秒）
    waitingTime = 9
    # 启动持续让机器人离开的进程
    #threading.Thread(target=lambda: queryRobotJob()).start()
    # 同时入库输送线做入库任务
    # 入库输送线多少秒movein一个箱子
    inboundTime = 9
    # 启动持续movein箱子到入库口进程
    #threading.Thread(target=lambda: moveInContainer()).start()
    # 一次性下发的任务数量
    tasksNumber = 1
    createTask()
