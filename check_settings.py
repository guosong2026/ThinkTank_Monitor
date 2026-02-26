#!/usr/bin/env python3
"""检查数据库设置"""

import json
import sqlite3
import os

DB_PATH = "reports.db"

def check_settings():
    """检查数据库设置"""
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        return
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查settings表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not cursor.fetchone():
            print("settings表不存在")
            return
        
        # 获取所有设置
        cursor.execute("SELECT key, value FROM settings")
        settings = cursor.fetchall()
        
        print("=== 数据库设置 ===")
        for key, value in settings:
            print(f"{key}: {value}")
            
            # 尝试解析JSON值
            if key == 'recipient_emails':
                try:
                    emails = json.loads(value)
                    print(f"  解析后的收件人邮箱: {emails}")
                    print(f"  邮箱数量: {len(emails)}")
                except json.JSONDecodeError as e:
                    print(f"  JSON解析错误: {e}")
                except Exception as e:
                    print(f"  解析错误: {e}")
    
    except Exception as e:
        print(f"检查数据库时出错: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_settings()