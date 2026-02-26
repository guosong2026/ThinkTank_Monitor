#!/usr/bin/env python3
"""诊断SMTP连接问题"""

import sys
import socket
import smtplib
import ssl
import time

print("=== SMTP连接问题诊断 ===\n")

# 测试配置
configs = [
    {
        "name": "Outlook (默认)",
        "server": "smtp.office365.com",
        "port": 587,
        "ssl": False,
        "tls": True
    },
    {
        "name": "Outlook (SSL)",
        "server": "smtp.office365.com",
        "port": 465,
        "ssl": True,
        "tls": False
    },
    {
        "name": "Gmail",
        "server": "smtp.gmail.com",
        "port": 587,
        "ssl": False,
        "tls": True
    },
    {
        "name": "QQ邮箱",
        "server": "smtp.qq.com",
        "port": 465,
        "ssl": True,
        "tls": False
    }
]

# 账户信息（请谨慎使用）
EMAIL = "guosong2023@outlook.com"
PASSWORD = "qqnkssrooiioumub"

def test_network(server, port, timeout=5):
    """测试网络连接"""
    try:
        sock = socket.create_connection((server, port), timeout=timeout)
        sock.close()
        return True, None
    except Exception as e:
        return False, str(e)

def test_smtp(config, email, password):
    """测试SMTP连接"""
    server_name = config["name"]
    server = config["server"]
    port = config["port"]
    use_ssl = config["ssl"]
    use_tls = config["tls"]
    
    print(f"\n{'='*60}")
    print(f"测试配置: {server_name}")
    print(f"服务器: {server}:{port}")
    print(f"SSL: {use_ssl}, TLS: {use_tls}")
    print(f"{'='*60}")
    
    # 1. 测试网络连接
    print("1. 测试网络连接...")
    success, error = test_network(server, port)
    if not success:
        print(f"   ✗ 网络连接失败: {error}")
        return False
    
    print("   ✓ 网络连接成功")
    
    # 2. 测试SMTP连接
    print("2. 测试SMTP协议...")
    try:
        if use_ssl:
            # SSL连接
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, timeout=10, context=context) as smtp:
                smtp.ehlo()
                print("   ✓ SSL连接成功")
                
                # 3. 测试认证
                print("3. 测试邮箱认证...")
                smtp.login(email, password)
                print("   ✓ 邮箱认证成功")
                return True
                
        else:
            # 普通连接 + TLS
            with smtplib.SMTP(server, port, timeout=10) as smtp:
                smtp.ehlo()
                
                if use_tls:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                    print("   ✓ TLS连接成功")
                
                # 3. 测试认证
                print("3. 测试邮箱认证...")
                smtp.login(email, password)
                print("   ✓ 邮箱认证成功")
                return True
                
    except smtplib.SMTPAuthenticationError as e:
        print(f"   ✗ 认证失败: {e}")
        print(f"     错误代码: {e.smtp_code if hasattr(e, 'smtp_code') else '未知'}")
        print(f"     错误消息: {e.smtp_error if hasattr(e, 'smtp_error') else str(e)}")
        return False
        
    except smtplib.SMTPServerDisconnected as e:
        print(f"   ✗ 服务器断开连接: {e}")
        return False
        
    except socket.timeout as e:
        print(f"   ✗ 连接超时: {e}")
        return False
        
    except ConnectionRefusedError as e:
        print(f"   ✗ 连接被拒绝: {e}")
        return False
        
    except Exception as e:
        print(f"   ✗ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主诊断函数"""
    print(f"测试邮箱: {EMAIL}")
    print(f"密码长度: {len(PASSWORD)} 字符")
    
    print("\n注意: 请确保:")
    print("  1. 邮箱已启用SMTP服务")
    print("  2. 使用的是SMTP授权码，不是登录密码")
    print("  3. 如果需要，已开启两步验证并生成应用专用密码")
    print("  4. 网络可以访问SMTP服务器")
    
    all_failed = True
    
    for config in configs:
        if test_smtp(config, EMAIL, PASSWORD):
            all_failed = False
            print(f"\n✓ 找到可用的配置: {config['name']}")
            print(f"  请在email_sender.py中修改以下配置:")
            print(f"  SMTP_SERVER = \"{config['server']}\"")
            print(f"  SMTP_PORT = {config['port']}")
            
            if config['ssl']:
                print(f"  注意: 使用SMTP_SSL连接 (端口 {config['port']})")
            break
        else:
            print(f"  ✗ 配置 {config['name']} 失败")
    
    if all_failed:
        print(f"\n{'='*60}")
        print("所有配置测试失败！")
        print("\n可能原因:")
        print("  1. 邮箱或密码错误")
        print("  2. 未开启SMTP服务")
        print("  3. Outlook需要两步验证和应用密码")
        print("  4. 网络防火墙阻止SMTP连接")
        print("  5. 账户被锁定或需要验证")
        print("\n解决方案:")
        print("  1. 登录Outlook网页版 (https://outlook.live.com)")
        print("  2. 点击右上角头像 → 查看账户")
        print("  3. 选择 安全 → 两步验证 (启用)")
        print("  4. 返回安全页面 → 应用密码")
        print("  5. 生成新的16位应用密码")
        print("  6. 使用新密码更新email_sender.py")
        print(f"{'='*60}")
        
        # 测试其他可能性
        print("\n额外测试: 测试SMTP服务器响应...")
        for config in configs:
            server = config["server"]
            port = config["port"]
            try:
                sock = socket.create_connection((server, port), timeout=5)
                sock.send(b"EHLO test\r\n")
                response = sock.recv(1024)
                print(f"{server}:{port} 响应: {response[:100]}...")
                sock.close()
            except Exception as e:
                print(f"{server}:{port} 无响应: {e}")

if __name__ == "__main__":
    main()