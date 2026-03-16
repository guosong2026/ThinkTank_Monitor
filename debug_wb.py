#!/usr/bin/env python3
"""检查World Bank页面结构"""

import requests
import urllib3
urllib3.disable_warnings()

url = "https://documents.worldbank.org/en/publication/documents-reports"
headers = {'User-Agent': 'Mozilla/5.0'}

r = requests.get(url, headers=headers, timeout=30, verify=False)
print(f"Status: {r.status_code}")
print(f"Content length: {len(r.text)}")

# 分析页面
from bs4 import BeautifulSoup
soup = BeautifulSoup(r.text, 'lxml')

# 查找所有链接
all_links = soup.find_all('a', href=True)
print(f"Total links: {len(all_links)}")

# 查找包含document/report的链接
doc_links = [l for l in all_links if '/document/' in l.get('href', '').lower() or '/report/' in l.get('href', '').lower()]
print(f"Document/Report links: {len(doc_links)}")

print("\nFirst 10 document/report links:")
for link in doc_links[:10]:
    href = link.get('href', '')
    text = link.get_text(strip=True)[:50]
    print(f"  {text}: {href[:80]}")
