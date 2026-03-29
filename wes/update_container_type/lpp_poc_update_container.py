import requests
import json

# wes主服务器ip
#server_ip = '172.18.86.20'
server_ip = '10.201.160.112'
# 密码，从前端登录接口拷参数
password = '4b764a0c3319aa8d89173eade4c16c71129ccbe84b9b59c987ecaacc57f3a640'
# 修改前的容器类型
old_containerTypeCode = 'PT_5'
# 修改后的容器类型
new_containerTypeCode = 'PT_1'
# 一次查询多少条
limit_query = 2000
prefix = 'C'
headers = ''
port = '9102'
compartmentCode = 'F1A'
containerCode_query = 'C%'

# 记录一个更新成功的容器数组，最后打印
success_containers = []
fail_containers = []

def get_token():
    url = f"http://{server_ip}:9102/imhs-api/login"
    data = {"account": "hairou", "password": password }
    r = requests.post(url, json=data)
    response = json.loads(r.text)
    global token
    token = response["data"]["auth_token"]
    global headers
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "User-Agent": "Apache-HttpClient/4.5.6 (Java/1.8.0_152-release)",
        "Cookie": f"session_token={token}"
    }


def update_containers():
    
    url = f'http://{server_ip}:{port}/container/query'
    body = {
        "containerCode":containerCode_query,
        "containerTypeCode":old_containerTypeCode,
        "statuses":["FILL_STOCK"],
        "filterGroup":[],
        "page":1,
        "limit": limit_query
    }
    r = requests.post(url, json=body, headers=headers).json()
    containers = r.get('data', {}).get('containers', [])
    
    # 遍历containers
    for c in containers:
        container_code = c['container']['code']
        # 只更新C开头，且容器格口是容器编码+F1A的容器
        if container_code.startswith(prefix) and len(c['container']['compartmentCode']) == 1 and len(c['container']['combineCompartment']) == 1 and c['container']['compartmentCode'][0] == container_code + compartmentCode:
            print(f"更新容器 {container_code} 为 {new_containerTypeCode}")

            # 查询容器pb
            query_url = f'http://{server_ip}:{port}/imhs-api/model/queryModelByCode?modelType=CONTAINER&code=' + container_code
            req = requests.get(url=query_url, headers=headers)
            old_container_pb = req.json()["data"]

            # 构建更新请求
            update_url = f'http://{server_ip}:{port}/imhs-api/model/updateModelNotSafe'
            old_container_pb['container']['containerTypeCode'] = new_containerTypeCode
            # 发送更新请求
            req = requests.post(url=update_url, json=old_container_pb, headers=headers)
            print(req.json())
            if req.json().get('code') == 0:
                print(f"✅ 容器 {container_code} 更新成功")
                # 记录成功的容器
                success_containers.append(container_code)
            else:
                print(f"❌ 容器 {container_code} 更新失败: {req.json().get('msg', '未知错误')}")
                 # 记录失败的容器
                fail_containers.append(container_code)



def main():
    print("=" * 60)
    print("批量更新容器类型脚本")
    print("=" * 60)

    # 登录获取token
    print("\n登录获取token...")
    get_token()
    print("✅ 登录成功\n")

    # 更新容器
    update_containers()

    print("\n" + "=" * 60)
    print("🎉 所有容器更新完成！")
    print("=" * 60)
    print(f"成功更新 {len(success_containers)} 个容器")
    # 打印success_containers
    print("成功更新的容器:")
    for container_code in success_containers:
        print(container_code)
    print(f"失败更新 {len(fail_containers)} 个容器")
    print("=" * 60)


if __name__ == "__main__":
    main()