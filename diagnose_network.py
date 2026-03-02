#!/usr/bin/env python3
"""
网络诊断工具
用于测试PythonAnywhere环境中的网络连接问题
"""

import socket
import requests
import time
import sys
from urllib.parse import urlparse

def test_socket_connection(hostname: str, port: int = 443, timeout: int = 10) -> bool:
    """测试基本的socket连接"""
    try:
        print(f"测试socket连接到 {hostname}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print(f"  ✓ Socket连接成功")
            return True
        else:
            print(f"  ✗ Socket连接失败 (错误代码: {result})")
            return False
    except Exception as e:
        print(f"  ✗ Socket连接异常: {e}")
        return False

def test_http_request(url: str, timeout: int = 30) -> bool:
    """测试HTTP/HTTPS请求"""
    try:
        print(f"测试HTTP请求到 {url}...")
        response = requests.get(url, timeout=timeout, verify=False, 
                               proxies={'http': None, 'https': None})
        print(f"  ✓ HTTP请求成功 (状态码: {response.status_code})")
        print(f"     内容长度: {len(response.text)} 字节")
        return True
    except requests.exceptions.Timeout:
        print(f"  ✗ HTTP请求超时 (超时: {timeout}秒)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"  ✗ HTTP连接错误: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"  ✗ HTTP请求异常: {e}")
        return False

def main():
    """主诊断函数"""
    print("=" * 60)
    print("PythonAnywhere 网络诊断工具")
    print("=" * 60)
    print(f"Python版本: {sys.version}")
    print(f"Requests版本: {requests.__version__}")
    print()
    
    # 要测试的网站列表
    test_urls = [
        "https://concito.dk/en/analyser",
        "https://www.worldwildlife.org/news/press-releases/",
        "https://eeb.org/en/library/",
        "https://green-alliance.org.uk",
        "https://www.pembina.org/all"
    ]
    
    print("阶段1: 基本socket连接测试")
    print("-" * 40)
    
    socket_results = {}
    for url in test_urls:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        success = test_socket_connection(hostname, port)
        socket_results[url] = success
        time.sleep(1)  # 避免过于频繁的连接
    
    print()
    print("阶段2: HTTP/HTTPS请求测试")
    print("-" * 40)
    
    http_results = {}
    for url in test_urls:
        success = test_http_request(url)
        http_results[url] = success
        time.sleep(2)  # 避免过于频繁的请求
    
    print()
    print("=" * 60)
    print("诊断结果总结")
    print("=" * 60)
    
    all_socket_ok = all(socket_results.values())
    all_http_ok = all(http_results.values())
    
    if all_socket_ok and all_http_ok:
        print("✓ 所有网络测试通过！")
        print("  监控程序应该可以正常工作。")
    else:
        print("✗ 发现网络连接问题：")
        
        for url in test_urls:
            socket_ok = socket_results[url]
            http_ok = http_results[url]
            
            if not socket_ok:
                print(f"  - {url}: Socket连接失败")
            elif not http_ok:
                print(f"  - {url}: HTTP请求失败 (但Socket连接成功)")
        
        print()
        print("可能的原因：")
        print("1. PythonAnywhere防火墙阻止了出站连接")
        print("2. 目标网站屏蔽了PythonAnywhere的IP地址")
        print("3. 网络临时故障")
        print()
        print("建议：")
        print("1. 等待一段时间后重试")
        print("2. 检查PythonAnywhere的服务状态")
        print("3. 联系PythonAnywhere支持")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()