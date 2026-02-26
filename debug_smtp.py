#!/usr/bin/env python3
"""详细SMTP连接测试脚本"""

import sys
import traceback
import logging
from email_sender import EmailSender

# 设置详细日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("=== 详细SMTP连接测试 ===")

try:
    # 创建邮件发送器实例
    sender = EmailSender()
    
    print("\n=== 当前配置 ===")
    print(f"SMTP服务器: {sender.smtp_server}:{sender.smtp_port}")
    print(f"发件人邮箱: {sender.sender_email}")
    print(f"发件人密码长度: {len(sender.sender_password)} 字符")
    print(f"收件人邮箱: {sender.recipient_emails}")
    
    print("\n=== 测试SMTP连接 ===")
    
    # 直接测试SMTP连接
    import smtplib
    import ssl
    
    print(f"1. 连接到 {sender.smtp_server}:{sender.smtp_port}...")
    try:
        context = ssl.create_default_context()
        
        with smtplib.SMTP(sender.smtp_server, sender.smtp_port) as server:
            print(f"2. 连接成功，发送EHLO...")
            server.ehlo()
            
            print(f"3. 启用TLS加密...")
            server.starttls(context=context)
            
            print(f"4. 再次发送EHLO...")
            server.ehlo()
            
            print(f"5. 尝试登录邮箱 {sender.sender_email}...")
            server.login(sender.sender_email, sender.sender_password)
            
            print("✓ SMTP连接测试成功！")
            
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ SMTP认证失败: {e}")
        print(f"  错误代码: {e.smtp_code}")
        print(f"  错误消息: {e.smtp_error}")
        print("\n可能原因:")
        print("  1. 邮箱或密码错误")
        print("  2. 未开启SMTP服务")
        print("  3. 需要应用专用密码（如Gmail、Outlook）")
        print("  4. 授权码已过期")
        
    except smtplib.SMTPException as e:
        print(f"✗ SMTP错误: {e}")
        
    except ConnectionRefusedError as e:
        print(f"✗ 连接被拒绝: {e}")
        print("可能原因:")
        print("  1. SMTP服务器地址错误")
        print("  2. 端口错误")
        print("  3. 防火墙阻止连接")
        
    except Exception as e:
        print(f"✗ 其他错误: {e}")
        traceback.print_exc()
        
    print("\n=== 使用EmailSender.test_connection()方法测试 ===")
    success = sender.test_connection()
    print(f"test_connection()返回: {success}")
    
except Exception as e:
    print(f"✗ 初始化失败: {e}")
    traceback.print_exc()
    sys.exit(1)