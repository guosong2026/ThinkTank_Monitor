#!/usr/bin/env python3
"""深入分析Stockholm Resilience网站结构"""

import requests
import sys
sys.path.insert(0, '.')

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from bs4 import BeautifulSoup

url = "https://www.stockholmresilience.org"
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30, verify=False)

soup = BeautifulSoup(response.text, 'lxml')

# 查找所有导航链接
nav = soup.find('nav')
if nav:
    print("导航菜单:")
    nav_links = nav.find_all('a', href=True)
    for link in nav_links[:20]:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        if text and 'publication' in href.lower() or 'research' in href.lower() or 'report' in href.lower():
            print(f"  {text}: {href}")

# 查找可能包含Publications的链接
print("\n包含关键词的链接:")
all_links = soup.find_all('a', href=True)
keywords = ['publication', 'research', 'report', 'paper', 'article']
for link in all_links:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    if any(kw in href.lower() for kw in keywords):
        print(f"  {text}: {href}")
