"""
数据库操作模块
处理SQLite数据库的连接、表创建和数据插入
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器类"""
    
    def __init__(self, db_path: str = "reports.db"):
        """
        初始化数据库管理器
        
        Args:
            db_path: SQLite数据库文件路径，默认为'reports.db'
        """
        self.db_path = db_path
        self.connection = None
        
    def connect(self) -> sqlite3.Connection:
        """
        连接到SQLite数据库
        
        Returns:
            sqlite3.Connection: 数据库连接对象
            
        Raises:
            sqlite3.Error: 数据库连接错误
        """
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"成功连接到数据库: {self.db_path}")
            return self.connection
        except sqlite3.Error as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def create_tables(self) -> None:
        """
        创建报告表和设置表（如果不存在）
        
        Raises:
            sqlite3.Error: 表创建错误
        """
        create_reports_table_sql = """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            source_website TEXT NOT NULL,
            publish_date TEXT,
            discovered_time TIMESTAMP NOT NULL,
            sent_status INTEGER DEFAULT 0
        )
        """
        
        create_settings_table_sql = """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT,
            updated_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        create_monitor_runs_table_sql = """
        CREATE TABLE IF NOT EXISTS monitor_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            duration_seconds REAL,
            new_reports_count INTEGER DEFAULT 0,
            results_json TEXT,
            status TEXT DEFAULT 'success',
            error_message TEXT
        )
        """
        
        try:
            cursor = self.connection.cursor()
            
            # 创建报告表
            cursor.execute(create_reports_table_sql)
            logger.info("报告表创建成功或已存在")
            
            # 创建设置表
            cursor.execute(create_settings_table_sql)
            logger.info("设置表创建成功或已存在")
            
            # 创建监控运行表
            cursor.execute(create_monitor_runs_table_sql)
            logger.info("监控运行表创建成功或已存在")
            
            self.connection.commit()
            
            # 检查sent_status字段是否存在，如果不存在则添加
            self._add_sent_status_column_if_needed()
            
            # 初始化默认设置（如果不存在）
            self._initialize_default_settings()
            
        except sqlite3.Error as e:
            logger.error(f"创建表失败: {e}")
            raise
    
    def insert_report(self, title: str, url: str, source_website: str, 
                     publish_date: Optional[str] = None) -> Optional[int]:
        """
        插入新的报告记录
        
        Args:
            title: 报告标题
            url: 报告链接
            source_website: 来源网站
            publish_date: 发布日期（可选）
            
        Returns:
            Optional[int]: 插入成功的报告ID，重复或失败时返回None
        """
        insert_sql = """
        INSERT OR IGNORE INTO reports (title, url, source_website, publish_date, discovered_time, sent_status)
        VALUES (?, ?, ?, ?, ?, 0)
        """
        
        try:
            cursor = self.connection.cursor()
            
            # 插入新记录，使用INSERT OR IGNORE避免重复
            discovered_time = datetime.now().isoformat()
            cursor.execute(insert_sql, (title, url, source_website, publish_date, discovered_time))
            self.connection.commit()
            
            # 获取插入的ID，如果为0则表示重复或未插入
            report_id = cursor.lastrowid
            if report_id:
                logger.info(f"成功插入报告: {title}, ID: {report_id}")
            else:
                logger.debug(f"报告已存在，跳过: {title}")
            return report_id if report_id else None
            
        except sqlite3.Error as e:
            logger.error(f"插入报告失败: {e}")
            self.connection.rollback()
            return None
    
    def report_exists(self, url: str) -> bool:
        """
        检查报告是否已存在
        
        Args:
            url: 报告链接
            
        Returns:
            bool: 是否存在
        """
        check_sql = "SELECT 1 FROM reports WHERE url = ?"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(check_sql, (url,))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"检查报告存在性失败: {e}")
            return False
    
    def get_all_reports(self) -> List[dict]:
        """
        获取所有报告
        
        Returns:
            List[dict]: 报告列表
        """
        select_sql = "SELECT * FROM reports ORDER BY discovered_time DESC"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(select_sql)
            rows = cursor.fetchall()
            
            # 转换为字典列表
            reports = []
            for row in rows:
                reports.append(dict(row))
            
            return reports
            
        except sqlite3.Error as e:
            logger.error(f"获取报告列表失败: {e}")
            return []
    
    def _add_sent_status_column_if_needed(self) -> None:
        """
        检查并添加sent_status字段（如果不存在）
        
        用于向后兼容，确保现有表结构包含sent_status字段
        """
        try:
            cursor = self.connection.cursor()
            
            # 检查sent_status字段是否存在
            cursor.execute("PRAGMA table_info(reports)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'sent_status' not in column_names:
                logger.info("添加sent_status字段到reports表")
                cursor.execute("ALTER TABLE reports ADD COLUMN sent_status INTEGER DEFAULT 0")
                self.connection.commit()
                logger.info("sent_status字段添加成功")
                
        except sqlite3.Error as e:
            logger.warning(f"检查/添加sent_status字段失败: {e}")
    
    def mark_report_as_sent(self, report_id: int) -> bool:
        """
        标记报告为已发送
        
        Args:
            report_id: 报告ID
            
        Returns:
            bool: 标记是否成功
        """
        update_sql = "UPDATE reports SET sent_status = 1 WHERE id = ?"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(update_sql, (report_id,))
            self.connection.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"报告ID {report_id} 标记为已发送")
                return True
            else:
                logger.warning(f"未找到报告ID {report_id}")
                return False
                
        except sqlite3.Error as e:
            logger.error(f"标记报告为已发送失败: {e}")
            self.connection.rollback()
            return False
    
    def get_unsent_reports(self, hours: Optional[int] = None) -> List[dict]:
        """
        获取未发送的报告
        
        Args:
            hours: 可选，限制报告发现时间在最近N小时内，None表示无时间限制
            
        Returns:
            List[dict]: 未发送的报告列表
        """
        if hours is not None:
            # 获取所有未发送报告，时间过滤在Python层面进行
            select_sql = "SELECT * FROM reports WHERE sent_status = 0 ORDER BY discovered_time"
            params = ()
        else:
            select_sql = "SELECT * FROM reports WHERE sent_status = 0 ORDER BY discovered_time"
            params = ()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(select_sql, params)
            rows = cursor.fetchall()
            
            reports = []
            for row in rows:
                reports.append(dict(row))
            
            # 如果指定了小时数，进行Python层面的时间过滤（避免时区和格式问题）
            if hours is not None:
                from datetime import datetime, timedelta
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                
                filtered_reports = []
                for report in reports:
                    # 解析discovered_time（ISO格式）
                    try:
                        discovered_str = report['discovered_time']
                        if 'T' in discovered_str:
                            # ISO格式: YYYY-MM-DDTHH:MM:SS
                            discovered_time = datetime.fromisoformat(discovered_str.replace('Z', '+00:00'))
                        else:
                            # SQLite格式: YYYY-MM-DD HH:MM:SS
                            discovered_time = datetime.strptime(discovered_str, '%Y-%m-%d %H:%M:%S')
                        
                        # 转换为UTC时间进行比较（如果discovered_time是本地时间，需要调整）
                        # 假设discovered_time存储为UTC时间
                        if discovered_time >= cutoff_time:
                            filtered_reports.append(report)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"解析报告发现时间失败 {report.get('id', 'unknown')}: {e}")
                        # 无法解析时间，保留报告（安全起见）
                        filtered_reports.append(report)
                
                reports = filtered_reports
                time_filter = f"最近{hours}小时内"
            else:
                time_filter = "全部"
            
            logger.debug(f"获取到 {len(reports)} 个未发送的报告 ({time_filter})")
            return reports
            
        except sqlite3.Error as e:
            logger.error(f"获取未发送报告失败: {e}")
            return []
    
    def get_report_id_by_url(self, url: str) -> Optional[int]:
        """
        根据URL获取报告ID
        
        Args:
            url: 报告URL
            
        Returns:
            Optional[int]: 报告ID，如果不存在则返回None
        """
        select_sql = "SELECT id FROM reports WHERE url = ?"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(select_sql, (url,))
            row = cursor.fetchone()
            
            return row['id'] if row else None
            
        except sqlite3.Error as e:
            logger.error(f"根据URL获取报告ID失败: {e}")
            return None
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    def _initialize_default_settings(self) -> None:
        """
        初始化默认设置
        
        设置键:
        - monitor_enabled: 监控是否启用 (1/0)
        - recipient_emails: 收件人邮箱 (JSON列表)
        - check_interval_hours: 检查间隔 (小时)
        """
        default_settings = {
            "monitor_enabled": "0",  # 默认禁用
            "recipient_emails": "[]",  # 空列表
            "check_interval_hours": "2",  # 默认2小时
        }
        
        try:
            cursor = self.connection.cursor()
            
            for key, default_value in default_settings.items():
                # 检查设置是否已存在
                cursor.execute("SELECT 1 FROM settings WHERE key = ?", (key,))
                if not cursor.fetchone():
                    # 插入默认值
                    cursor.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?)",
                        (key, default_value)
                    )
                    logger.info(f"初始化默认设置: {key} = {default_value}")
            
            self.connection.commit()
            
        except sqlite3.Error as e:
            logger.error(f"初始化默认设置失败: {e}")
            self.connection.rollback()
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """
        获取设置值
        
        Args:
            key: 设置键
            default: 默认值（如果键不存在）
            
        Returns:
            Optional[str]: 设置值，不存在时返回默认值
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                return row['value']
            else:
                return default
                
        except sqlite3.Error as e:
            logger.error(f"获取设置失败: {e}")
            return default
    
    def set_setting(self, key: str, value: str) -> bool:
        """
        设置键值
        
        Args:
            key: 设置键
            value: 设置值
            
        Returns:
            bool: 是否成功
        """
        try:
            cursor = self.connection.cursor()
            
            # 使用UPSERT (SQLite 3.24.0+ 支持 INSERT OR REPLACE)
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_time) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, value)
            )
            
            self.connection.commit()
            logger.info(f"设置更新: {key} = {value}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"设置更新失败: {e}")
            self.connection.rollback()
            return False
    
    def get_all_settings(self) -> Dict[str, str]:
        """
        获取所有设置
        
        Returns:
            Dict[str, str]: 所有设置的键值对
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()
            
            settings = {}
            for row in rows:
                settings[row['key']] = row['value']
            
            return settings
            
        except sqlite3.Error as e:
            logger.error(f"获取所有设置失败: {e}")
            return {}
    def insert_monitor_run(self, start_time, end_time, duration_seconds, 
                          new_reports_count=0, results_json=None, 
                          status='success', error_message=None) -> Optional[int]:
        """
        插入监控运行记录
        
        Args:
            start_time: 开始时间 (datetime)
            end_time: 结束时间 (datetime)
            duration_seconds: 耗时秒数 (float)
            new_reports_count: 新报告数量 (int)
            results_json: 结果JSON字符串 (str, optional)
            status: 状态 ('success', 'error') (str)
            error_message: 错误信息 (str, optional)
        
        Returns:
            Optional[int]: 插入成功的运行ID，失败时返回None
        """
        insert_sql = """
        INSERT INTO monitor_runs 
        (start_time, end_time, duration_seconds, new_reports_count, 
         results_json, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_sql, (
                start_time.isoformat() if hasattr(start_time, 'isoformat') else start_time,
                end_time.isoformat() if hasattr(end_time, 'isoformat') else end_time,
                duration_seconds,
                new_reports_count,
                results_json,
                status,
                error_message
            ))
            self.connection.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"插入监控运行记录失败: {e}")
            return None
    
    def get_recent_monitor_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的监控运行记录
        
        Args:
            limit: 返回记录数量限制
        
        Returns:
            List[Dict[str, Any]]: 监控运行记录列表
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT id, start_time, end_time, duration_seconds, 
                       new_reports_count, results_json, status, error_message
                FROM monitor_runs 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            
            runs = []
            for row in rows:
                runs.append({
                    'id': row['id'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'duration_seconds': row['duration_seconds'],
                    'new_reports_count': row['new_reports_count'],
                    'results_json': row['results_json'],
                    'status': row['status'],
                    'error_message': row['error_message']
                })
            return runs
        except sqlite3.Error as e:
            logger.error(f"获取监控运行记录失败: {e}")
            return []
    
    def get_recent_stats(self, days: int = 10) -> Dict[str, Any]:
        """
        获取最近N天的报告统计数据
        
        Args:
            days: 统计天数，默认为10天
            
        Returns:
            Dict[str, Any]: 统计数据，包含每日总计和网站来源分布
        """
        try:
            cursor = self.connection.cursor()
            
            # 计算开始日期（当前日期往前推days-1天，包含今天）
            from datetime import datetime, timedelta
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days-1)
            
            # 查询最近days天的报告，按日期和网站分组
            # 使用substr提取日期部分（YYYY-MM-DD），处理两种格式：
            # 1. ISO格式: 2026-02-28T15:01:17.198158
            # 2. SQLite格式: 2026-02-28 15:01:17
            cursor.execute("""
                SELECT 
                    substr(discovered_time, 1, 10) as date,
                    source_website,
                    COUNT(*) as count
                FROM reports 
                WHERE substr(discovered_time, 1, 10) >= ?
                GROUP BY date, source_website
                ORDER BY date DESC, count DESC
            """, (str(start_date),))
            
            rows = cursor.fetchall()
            
            # 构建数据结构
            daily_totals = []
            website_distribution = {}
            
            # 生成所有日期的列表（从start_date到end_date）
            date_list = []
            current_date = start_date
            while current_date <= end_date:
                date_str = str(current_date)
                date_list.append(date_str)
                daily_totals.append({"date": date_str, "count": 0})
                website_distribution[date_str] = {}
                current_date += timedelta(days=1)
            
            # 填充数据
            for row in rows:
                date_str = row['date']
                website = row['source_website']
                count = row['count']
                
                # 更新每日总计
                for daily in daily_totals:
                    if daily['date'] == date_str:
                        daily['count'] += count
                        break
                
                # 更新网站分布
                if date_str in website_distribution:
                    website_distribution[date_str][website] = count
            
            # 获取所有出现的网站名称（用于图表标签）
            all_websites = set()
            for date_data in website_distribution.values():
                all_websites.update(date_data.keys())
            all_websites = sorted(list(all_websites))
            
            return {
                "days": days,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "daily_totals": daily_totals,  # 按日期倒序排列
                "website_distribution": website_distribution,
                "all_websites": all_websites
            }
            
        except sqlite3.Error as e:
            logger.error(f"获取近期统计数据失败: {e}")
            return {
                "days": days,
                "start_date": "",
                "end_date": "",
                "daily_totals": [],
                "website_distribution": {},
                "all_websites": []
            }
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        self.create_tables()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


if __name__ == "__main__":
    # 测试数据库功能
    import sys
    
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    try:
        with DatabaseManager("test.db") as db:
            print("数据库连接和表创建测试成功")
            
            # 测试插入
            report_id = db.insert_report(
                title="测试报告",
                url="https://example.com/test",
                source_website="concito.dk",
                publish_date="2024-01-01"
            )
            print(f"插入测试结果: {'成功, ID: ' + str(report_id) if report_id else '失败或重复'}")
            
            # 测试获取
            reports = db.get_all_reports()
            print(f"获取到 {len(reports)} 条报告")
            
            # 测试标记为已发送
            if report_id:
                success = db.mark_report_as_sent(report_id)
                print(f"标记为已发送: {'成功' if success else '失败'}")
            
            # 测试获取未发送报告
            unsent_reports = db.get_unsent_reports()
            print(f"未发送报告数量: {len(unsent_reports)}")
            
    except Exception as e:
        print(f"数据库测试失败: {e}")
        sys.exit(1)