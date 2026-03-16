#!/usr/bin/env python3
"""
数据库清理脚本
删除无效报告记录（如'Read More'、'privacy notice'等）
"""

import sqlite3
import sys
import os

# 添加当前目录到路径，以便导入website_configs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from website_configs import WebsiteConfig

def cleanup_database(db_path='reports.db', dry_run=True):
    """
    清理数据库中的无效报告
    
    Args:
        db_path: 数据库文件路径
        dry_run: 是否为试运行（True=只显示不删除，False=实际删除）
    """
    # 创建一个临时的WebsiteConfig实例来使用过滤方法
    config = WebsiteConfig(name="Cleanup", url="")
    
    # 连接到数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有报告
    cursor.execute('SELECT id, title, url, source_website FROM reports ORDER BY discovered_time DESC')
    reports = cursor.fetchall()
    
    print(f"数据库中共有 {len(reports)} 个报告")
    print("=" * 80)
    
    invalid_reports = []
    valid_reports = []
    
    for report in reports:
        report_id = report['id']
        title = report['title']
        url = report['url']
        source = report['source_website']
        
        # 应用标题清理
        cleaned_title = config._clean_title(title)
        
        # 检查是否为有效报告链接
        is_valid = config._is_report_link(url, cleaned_title if cleaned_title else title)
        
        if not cleaned_title or not is_valid:
            invalid_reports.append({
                'id': report_id,
                'title': title,
                'url': url,
                'source': source,
                'reason': '无效标题' if not cleaned_title else '无效链接'
            })
        else:
            valid_reports.append(report_id)
    
    print(f"发现 {len(invalid_reports)} 个无效报告:")
    print("=" * 80)
    
    for i, invalid in enumerate(invalid_reports, 1):
        print(f"{i}. ID: {invalid['id']}, 来源: {invalid['source']}")
        print(f"   标题: {invalid['title']}")
        print(f"   链接: {invalid['url']}")
        print(f"   原因: {invalid['reason']}")
        print()
    
    if dry_run:
        print(f"试运行模式: 不会删除任何记录")
        print(f"要实际删除这些无效报告，请运行: python cleanup_database.py --apply")
    else:
        # 实际删除
        if invalid_reports:
            print("正在删除无效报告...")
            invalid_ids = [str(inv['id']) for inv in invalid_reports]
            placeholders = ','.join('?' * len(invalid_ids))
            
            cursor.execute(f'DELETE FROM reports WHERE id IN ({placeholders})', invalid_ids)
            conn.commit()
            
            print(f"已删除 {cursor.rowcount} 个无效报告")
        else:
            print("没有需要删除的无效报告")
    
    # 统计信息
    print("=" * 80)
    print("统计信息:")
    print(f"总报告数: {len(reports)}")
    print(f"有效报告: {len(valid_reports)}")
    print(f"无效报告: {len(invalid_reports)}")
    
    conn.close()
    
    return len(invalid_reports)

def cleanup_and_export(db_path='reports.db', export_path='cleaned_reports.db'):
    """
    清理数据库并导出为新的数据库文件（保留原始数据库）
    """
    import shutil
    
    print(f"备份原始数据库: {db_path} -> {db_path}.backup")
    shutil.copy2(db_path, f"{db_path}.backup")
    
    print(f"创建清理后的数据库: {export_path}")
    shutil.copy2(db_path, export_path)
    
    # 在清理后的数据库中删除无效记录
    cleanup_database(export_path, dry_run=False)
    
    print(f"清理完成！")
    print(f"- 原始数据库备份: {db_path}.backup")
    print(f"- 清理后的数据库: {export_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='清理数据库中的无效报告记录')
    parser.add_argument('--db', default='reports.db', help='数据库文件路径 (默认: reports.db)')
    parser.add_argument('--apply', action='store_true', help='实际应用删除操作（默认是试运行）')
    parser.add_argument('--export', metavar='FILE', help='导出清理后的数据库到指定文件')
    
    args = parser.parse_args()
    
    if args.export:
        cleanup_and_export(args.db, args.export)
    else:
        cleanup_database(args.db, dry_run=not args.apply)