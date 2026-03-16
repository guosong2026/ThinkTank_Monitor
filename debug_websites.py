#!/usr/bin/env python3
"""
检查特定网站解析情况
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
sys.path.insert(0, '.')

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from website_configs import (
    stockholm_resilience_parser,
    biodiversity_council_parser,
    world_bank_parser
)

def check_website(name, url, parser_func):
    """检查单个网站"""
    print(f"\n{'='*70}")
    print(f"检查: {name}")
    print(f"URL: {url}")
    print('='*70)

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        session = requests.Session()
        retry = Retry(total=2, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        response = session.get(url, headers=headers, timeout=30, verify=False)

        print(f"HTTP状态: {response.status_code}")
        print(f"页面长度: {len(response.text)} 字符")

        if response.status_code == 200:
            reports = parser_func(response.text, url)
            print(f"\n发现报告: {len(reports)} 个")

            if reports:
                print("\n前5个报告:")
                for i, r in enumerate(reports[:5], 1):
                    print(f"  {i}. {r['title'][:60]}...")
                    print(f"     URL: {r['url'][:80]}")
            else:
                print("\n未找到报告，尝试分析页面结构...")

                # 分析页面结构
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'lxml')

                # 查找所有链接
                all_links = soup.find_all('a', href=True)
                print(f"\n页面中总链接数: {len(all_links)}")

                # 查找可能包含publication/report的链接
                pub_links = [l for l in all_links if 'publication' in l.get('href', '').lower() or 'report' in l.get('href', '').lower()]
                print(f"包含publication/report的链接数: {len(pub_links)}")

                if pub_links:
                    print("\n前10个可能相关的链接:")
                    for i, l in enumerate(pub_links[:10], 1):
                        print(f"  {i}. {l.get('href', '')[:80]}")
                        print(f"     文本: {l.get_text(strip=True)[:50]}")

        elif response.status_code == 403:
            print("⚠️ 403 访问被拒绝 - 网站拒绝爬虫访问")

        elif response.status_code == 404:
            print("⚠️ 404 页面不存在")

        else:
            print(f"⚠️ 其他错误: HTTP {response.status_code}")

    except Exception as e:
        print(f"错误: {e}")

# 检查三个网站
if __name__ == "__main__":
    print("检查特定网站解析情况")
    print("="*70)

    # Stockholm Resilience
    check_website(
        "Stockholm Resilience",
        "https://www.stockholmresilience.org/publications.html",
        stockholm_resilience_parser
    )

    # Biodiversity Council
    check_website(
        "Biodiversity Council",
        "https://biodiversitycouncil.org.au/resources?category=Report",
        biodiversity_council_parser
    )

    # World Bank
    check_website(
        "World Bank",
        "https://openknowledge.worldbank.org/search?query=&f.topic=Urban%20Development,%20equals&spc.page=1",
        world_bank_parser
    )
