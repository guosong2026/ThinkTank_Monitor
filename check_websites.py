#!/usr/bin/env python3
"""
智库网站连接检查脚本
检查所有配置的智库网站是否可访问
"""

import sys
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from website_configs import get_all_websites

def check_website(config):
    """检查单个网站"""
    result = {
        'name': config.name,
        'url': config.url,
        'status': 'unknown',
        'status_code': None,
        'error': None,
        'reports_found': 0
    }

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        session = requests.Session()
        retry = Retry(total=2, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        response = session.get(config.url, headers=headers, timeout=30, verify=False)

        result['status_code'] = response.status_code

        if response.status_code == 200:
            result['status'] = 'success'

            try:
                reports = config.get_reports(response.text, config.url)
                result['reports_found'] = len(reports)
            except Exception as e:
                result['error'] = f'解析错误: {str(e)[:50]}'

        elif response.status_code == 403:
            result['status'] = 'blocked'
            result['error'] = '403 访问被拒绝'
        elif response.status_code == 404:
            result['status'] = 'not_found'
            result['error'] = '404 页面不存在'
        else:
            result['status'] = 'error'
            result['error'] = f'HTTP {response.status_code}'

    except requests.exceptions.Timeout:
        result['status'] = 'timeout'
        result['error'] = '连接超时'
    except requests.exceptions.ConnectionError as e:
        result['status'] = 'connection_error'
        result['error'] = f'连接失败: {str(e)[:50]}'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)[:50]

    return result

def main():
    print("=" * 70)
    print("智库网站连接检查")
    print("=" * 70)

    websites = get_all_websites()

    results = []
    success_count = 0
    error_count = 0

    for i, config in enumerate(websites, 1):
        print(f"\n[{i}/{len(websites)}] 检查: {config.name}...", end=" ", flush=True)

        result = check_website(config)
        results.append(result)

        if result['status'] == 'success':
            print(f"✓ 成功 (HTTP {result['status_code']}, 发现 {result['reports_found']} 个报告)")
            success_count += 1
        elif result['status'] == 'blocked':
            print(f"⚠ 403 访问被拒绝")
            error_count += 1
        else:
            print(f"✗ {result['status']} - {result['error']}")
            error_count += 1

        time.sleep(1)

    print("\n" + "=" * 70)
    print("检查结果汇总")
    print("=" * 70)

    print(f"\n总计: {len(websites)} 个网站")
    print(f"✓ 可访问: {success_count} 个")
    print(f"✗ 不可访问: {error_count} 个")

    print("\n详细结果:")
    print("-" * 70)

    for result in results:
        status_icon = "✓" if result['status'] == 'success' else "✗"
        print(f"{status_icon} {result['name']}: {result['status']}", end="")
        if result['status'] == 'success':
            print(f" (发现 {result['reports_found']} 个报告)")
        else:
            print(f" - {result['error']}")

    print("\n" + "=" * 70)

    if error_count > 0:
        print("\n⚠️  存在无法访问的网站，可能需要:")
        print("  1. 检查网站URL是否正确")
        print("  2. 检查是否需要登录或VPN")
        print("  3. 调整请求头或代理设置")
        print("  4. 部分网站可能需要特殊处理(如OECD、WRI等)")

if __name__ == "__main__":
    main()
