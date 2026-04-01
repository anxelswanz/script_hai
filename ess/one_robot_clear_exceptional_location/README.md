

1. Read the abnormal storage location file 
def read_excel_to_tuples
- input file.excel
- return (location, container)
2. for these tuples, we do serial execution
   2.1 robot goes to the location take the container
   def createAction
     - input robot_id, location, container
   2.2 robot goes to place the container 
     def queryAvailableLocation
     def distance_calculation
     def query_current_robot
     def createAction 



api: Robot takes container
http://10.201.160.113:9003/ess-api/wms/createActionTask
body:
{
  "robotCode": "kubot-245",
  "tasks": [
    {
      "taskAction": "load",
      "taskCode": "load-1774802187194-0",
      "isFinallyPaused": true,
      "locationCode": "HAI-070-093-18_1"
    }
  ]
}

api: http://10.201.160.113:9003/ess-api/wms/createActionTask
{
  "robotCode": "kubot-13",
  "tasks": [
    {
      "taskAction": "unload",
      "taskCode": "unload-1774802449747-0",
      "isFinallyPaused": true,
      "containerCode": "C000475122",
      "locationCode": "HAI-062-053-20_1"
    }
  ]
}