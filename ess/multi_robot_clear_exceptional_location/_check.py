from tool.logger import logger
# import requests
#
# def check_robot_tasks(robot_code):
#     url = f"http://10.201.160.113:9000/ess-api/model/queryModelByCode?modelCode={robot_code}"
#     try:
#         logger.info(f"正在查询机器人状态，URL: {url}")
#         response = requests.get(url, timeout=10)
#         res_data = response.json()
#
#         robot_data = res_data.get("data", {}).get("robot", {})
#         unfinished_tasks = robot_data.get("unfinishedTransportTaskCode", {})
#         if unfinished_tasks:
#             logger.info(f"机器人 {robot_code} 当前有未完成任务: {list(unfinished_tasks.keys())}")
#             return True
#         else:
#             logger.info(f"机器人 {robot_code} 当前没有未完成任务。")
#             return False
#     except Exception as e:
#         logger.exception(f"调用接口发生异常: {str(e)}")
#         return False
#
#
# if __name__ == '__main__':

if __name__ == '__main__':
    logger.error("this is an error message")