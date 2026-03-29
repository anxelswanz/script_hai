import json
import time
import requests


host = "http://10.201.160.213:9000"
def createOutBound(taskNum1, hasTaskContainer):
    # 强制将请求数量锁定为 1
    target_num = 1
    url = host + "/tms/createWmsOutboundTask"
    containerCodes = queryContainer()

    data = {
        "taskGroupCode": "",
        "tasks": []
    }

    # 1. 寻找第一个可用的容器
    selected_container = None
    for j in containerCodes:
        if j not in hasTaskContainer:
            selected_container = j
            break  # 找到一个就立刻跳出循环

    if not selected_container:
        print("警告：没有找到可用的空闲容器，无法下发任务")
        return
    stations = "LABOR_1"

    # 2. 构造单任务数据
    data["tasks"].append({
        "taskTemplateCode": "",
        "taskCode": "LABOR_1-" + str(int(time.time() * 1000)) + selected_container,
        "taskPriority": 0,
        "deadline": 0,
        "taskDescribe": {
            "containerCode": selected_container,
            "toStationCode": stations
        }
    })

    # 3. 发送请求
    taskJson = json.dumps(data)
    re = requests.post(url, data=taskJson)
    print(f"下发单任务结果: {re.text}")

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

if __name__ == '__main__':
