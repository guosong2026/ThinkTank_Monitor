#!/usr/bin/env python3
"""检查World Bank网站结构"""

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 尝试不同的URL
urls_to_try = [
    "https://openknowledge.worldbank.org/",
    "https://openknowledge.worldbank.org/handle/10986/active",
    "https://documents.worldbank.org/",
    "https://www.worldbank.org/en/research"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

for url in urls_to_try:
    print(f"\n尝试: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        print(f"  状态: {response.status_code}")
        print(f"  内容长度: {len(response.text)}")

        # 检查是否有重定向
        if response.url != url:
            print(f"  重定向到: {response.url}")
    except Exception as e:
        print(f"  错误: {e}")
