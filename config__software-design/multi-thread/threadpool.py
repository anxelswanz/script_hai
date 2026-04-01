from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from urllib3.util import url

urls = [
    "https://www.baidu.com",
    "https://www.github.com",
    "https://www.google.com", # 国内可能无法访问，用来测试超时
    "https://www.python.org",
    "https://www.wikipedia.org"
]

def check_url(url):
    try:
        response = requests.get(url, timeout=5)
        return f"{url} status: {response.status_code}"
    except Exception:
        raise TimeoutError


def main():
    with ThreadPoolExecutor(max_workers=5) as executor:
        # key: future对象  value: url 字符串（对应的网址）。
        future_to_url = {executor.submit(check_url, url): url for url in urls}
        for future in as_completed(future_to_url):
            result = future.result()
            print(result)
    print("--- 检查任务结束 ---")

if __name__ == '__main__':
    main()