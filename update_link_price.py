#!/usr/bin/env python3
"""更新LINK价格"""

import requests

API_BASE = "http://127.0.0.1:21345/api"

def update_link_price():
    """更新LINK价格"""
    print("更新LINK价格...")
    response = requests.post(f"{API_BASE}/crypto/update_prices?symbols=LINK")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")

if __name__ == "__main__":
    update_link_price()
