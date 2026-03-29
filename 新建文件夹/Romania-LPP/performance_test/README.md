
# 压测脚本

## 1. 监控

- 任务补发逻辑监控 createTask
- 机器人到岗与放行监控 queryRobotJob / letRobotGo


## 2. 流程
- 开启机器人离开线程 
  func createTask
  1. 
  func queryRobotJob
  1. ess-api/model/queryModelByType?modelType=robot 获取机器人
  2. /wms/locationQuery" 获取工作站点位
  3. 如果机器人停留时间 > 设定停留时间，调用：/ess-api/station/letRobotGo