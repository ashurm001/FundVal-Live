import requests

# 测试后端 API
code = "110020"
url = f"http://localhost:21345/api/fund/{code}/latest-nav"

try:
    response = requests.get(url, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
