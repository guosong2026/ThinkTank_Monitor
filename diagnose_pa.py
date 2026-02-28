#!/usr/bin/env python3
"""
诊断PythonAnywhere上的ThinkTank_Monitor问题
请在PythonAnywhere的Bash中运行此脚本
"""

import sys
import os
import sqlite3
import json
from datetime import datetime

def check_database():
    """检查数据库状态"""
    print("=" * 60)
    print("1. 检查数据库状态")
    print("=" * 60)
    
    db_path = 'reports.db'
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("   数据库路径:", os.path.abspath(db_path))
        return False
    
    print(f"✅ 数据库文件存在: {db_path}")
    print(f"   文件大小: {os.path.getsize(db_path) / 1024:.1f} KB")
    
    # 检查数据库连接
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ 数据库中没有表")
            return False
        
        print(f"✅ 数据库中有 {len(tables)} 个表:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # 检查reports表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reports'")
        if not cursor.fetchone():
            print("❌ 缺少reports表")
            return False
        
        print("✅ reports表存在")
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(reports)")
        columns = cursor.fetchall()
        print(f"✅ reports表有 {len(columns)} 列:")
        
        required_columns = ['id', 'title', 'url', 'source_website', 'discovered_time', 'sent_status']
        found_columns = [col[1] for col in columns]
        
        for col in columns:
            print(f"   - {col[1]}: {col[2]}")
        
        # 检查是否包含必需列
        missing_columns = [col for col in required_columns if col not in found_columns]
        if missing_columns:
            print(f"❌ 缺少必需列: {missing_columns}")
            return False
        
        # 检查数据
        cursor.execute("SELECT COUNT(*) FROM reports")
        count = cursor.fetchone()[0]
        
        print(f"✅ reports表中有 {count} 条记录")
        
        if count > 0:
            cursor.execute("SELECT id, title, source_website, discovered_time FROM reports ORDER BY discovered_time DESC LIMIT 5")
            rows = cursor.fetchall()
            
            print("   最近5条报告:")
            for row in rows:
                title = row[1] if row[1] else '无标题'
                source = row[2] if row[2] else '未知'
                time = row[3] if row[3] else '未知'
                print(f"   - ID: {row[0]}, 标题: {title[:40]}..., 来源: {source}, 时间: {time}")
        else:
            print("⚠️  数据库为空，没有报告数据")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ 数据库错误: {e}")
        return False

def check_web_config():
    """检查Web应用配置"""
    print("\n" + "=" * 60)
    print("2. 检查Web应用配置")
    print("=" * 60)
    
    # 检查Flask应用文件
    files_to_check = ['app.py', 'monitor_service.py', 'db.py', 'templates/reports.html']
    
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ {file} 存在")
        else:
            print(f"❌ {file} 不存在")
    
    # 检查Python环境
    print("\nPython环境:")
    print(f"  Python版本: {sys.version}")
    
    # 检查依赖
    try:
        import flask
        print(f"  Flask版本: {flask.__version__}")
    except ImportError:
        print("❌ Flask未安装")
    
    try:
        import bs4
        print(f"  BeautifulSoup4版本: {bs4.__version__}")
    except ImportError:
        print("❌ BeautifulSoup4未安装")
    
    try:
        import apscheduler
        print(f"  APScheduler版本: {apscheduler.__version__}")
    except ImportError:
        print("❌ APScheduler未安装")
    
    return True

def test_monitor_service():
    """测试监控服务"""
    print("\n" + "=" * 60)
    print("3. 测试监控服务")
    print("=" * 60)
    
    try:
        # 尝试导入监控服务
        sys.path.insert(0, '.')
        from monitor_service import get_monitor_service
        
        print("✅ 成功导入monitor_service")
        
        service = get_monitor_service()
        print("✅ 监控服务初始化成功")
        
        # 测试获取报告
        reports = service.get_recent_reports(limit=5)
        print(f"✅ get_recent_reports(5) 返回 {len(reports)} 条报告")
        
        if reports:
            print("   前2条报告:")
            for i, report in enumerate(reports[:2], 1):
                title = report.get('title', '无标题')[:40]
                source = report.get('source_website', '未知')
                print(f"   {i}. {title}... ({source})")
        
        # 测试获取推文
        tweets = service.get_recent_tweets(days=30, limit=5)
        print(f"✅ get_recent_tweets(30天, 5条) 返回 {len(tweets)} 条推文")
        
        if tweets:
            print("   前2条推文:")
            for i, tweet in enumerate(tweets[:2], 1):
                title = tweet.get('title', '无标题')[:40]
                source = tweet.get('source_website', '未知')
                print(f"   {i}. {title}... ({source})")
        
        return True
        
    except Exception as e:
        print(f"❌ 监控服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_web_routes():
    """测试Web路由"""
    print("\n" + "=" * 60)
    print("4. 测试Web路由")
    print("=" * 60)
    
    try:
        from app import app
        
        with app.test_client() as client:
            # 测试首页
            response = client.get('/')
            print(f"✅ GET / -> 状态码: {response.status_code}")
            
            # 测试报告页面
            response = client.get('/reports')
            print(f"✅ GET /reports -> 状态码: {response.status_code}")
            
            # 测试带参数的报告页面
            response = client.get('/reports?limit=10')
            print(f"✅ GET /reports?limit=10 -> 状态码: {response.status_code}")
            
            # 测试推文页面
            response = client.get('/tweets')
            print(f"✅ GET /tweets -> 状态码: {response.status_code}")
            
            # 测试API
            response = client.get('/api/reports?limit=3')
            if response.status_code == 200:
                data = response.get_json()
                print(f"✅ GET /api/reports -> 成功: {data.get('success')}, 数量: {data.get('count')}")
            else:
                print(f"❌ GET /api/reports -> 状态码: {response.status_code}")
            
            # 测试近期推文API
            response = client.get('/api/recent_tweets?limit=3')
            if response.status_code == 200:
                data = response.get_json()
                print(f"✅ GET /api/recent_tweets -> 成功: {data.get('success')}, 数量: {data.get('count')}")
            else:
                print(f"❌ GET /api/recent_tweets -> 状态码: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Web路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_monitor_once():
    """运行一次监控检查"""
    print("\n" + "=" * 60)
    print("5. 运行监控检查")
    print("=" * 60)
    
    try:
        from monitor_service import get_monitor_service
        import asyncio
        
        service = get_monitor_service()
        print("开始运行监控检查...")
        
        # 注意：在PythonAnywhere上可能需要同步运行
        results = service.run_once()
        
        print(f"✅ 监控检查完成")
        print(f"   结果: {results}")
        
        if results:
            total = sum(results.values())
            print(f"   发现 {total} 条新报告:")
            for site, count in results.items():
                print(f"     - {site}: {count}")
        else:
            print("⚠️  未发现新报告")
        
        return True
        
    except Exception as e:
        print(f"❌ 监控检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主诊断函数"""
    print("\n" + "=" * 60)
    print("ThinkTank Monitor - PythonAnywhere诊断工具")
    print("=" * 60)
    print(f"当前目录: {os.getcwd()}")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查数据库
    db_ok = check_database()
    
    # 检查Web配置
    config_ok = check_web_config()
    
    # 测试监控服务
    service_ok = test_monitor_service()
    
    # 测试Web路由
    routes_ok = test_web_routes()
    
    # 运行监控检查（如果需要）
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    print(f"✅ 数据库检查: {'通过' if db_ok else '失败'}")
    print(f"✅ Web配置检查: {'通过' if config_ok else '失败'}")
    print(f"✅ 监控服务测试: {'通过' if service_ok else '失败'}")
    print(f"✅ Web路由测试: {'通过' if routes_ok else '失败'}")
    
    print("\n" + "=" * 60)
    print("建议")
    print("=" * 60)
    
    if not db_ok:
        print("❌ 数据库问题:")
        print("   1. 确保数据库文件存在")
        print("   2. 检查数据库权限")
        print("   3. 运行监控检查填充数据")
    
    if service_ok and db_ok:
        # 询问是否运行监控检查
        print("\n💡 是否运行监控检查来填充数据？")
        print("   执行: python -c \"from monitor_service import get_monitor_service; print(get_monitor_service().run_once())\"")
    else:
        print("\n⚠️  请先修复上述问题")
    
    print("\n📋 常见解决方案:")
    print("   1. 确保PythonAnywhere上的代码是最新的:")
    print("      cd ~/ThinkTank_Monitor && git pull origin main")
    print("   2. 安装依赖:")
    print("      pip install -r requirements.txt --upgrade")
    print("   3. 运行监控检查:")
    print("      python -c \"from monitor_service import get_monitor_service; get_monitor_service().run_once()\"")
    print("   4. 重启Web应用:")
    print("      在PythonAnywhere Dashboard的'Web'标签页中点击'Reload'")
    print("   5. 查看日志:")
    print("      tail -f ~/ThinkTank_Monitor/monitor.log")
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()