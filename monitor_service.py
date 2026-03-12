"""
监控服务模块
提供可调用的监控服务，用于Web界面和后台任务调度
使用APScheduler进行任务调度
"""

import json
import time
import logging
import os
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from db import DatabaseManager
from monitor import MultiWebsiteMonitor
from website_configs import get_all_websites
from email_sender import EmailSender

logger = logging.getLogger(__name__)


class MonitorService:
    """监控服务类（使用APScheduler）"""
    
    def __init__(self, db_path: str = "reports.db"):
        """
        初始化监控服务
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.monitor = None
        self.scheduler = None
        self.is_running = False
        self.lock = threading.Lock()
        self.job_id = "monitor_job"
        
        logger.info(f"初始化监控服务，数据库: {db_path}")
        
        # 初始化调度器（但不启动）
        self.scheduler = BackgroundScheduler(
            daemon=True,
            job_defaults={
                'coalesce': True,  # 合并多次未执行的任务
                'max_instances': 1,  # 最多1个实例同时运行
                'misfire_grace_time': 30  # 任务错过执行的宽容时间（秒）
            }
        )
        
        # 根据数据库设置决定是否自动启动监控
        # 部署到PythonAnywhere时禁用自动启动，使用外部cron触发
        # self._auto_start_from_settings()
    
    def _auto_start_from_settings(self):
        """根据数据库设置自动启动监控"""
        try:
            settings = self._load_settings()
            if settings.get("monitor_enabled", False):
                logger.info("检测到监控已启用，正在自动启动...")
                # 延迟启动，避免在初始化阶段阻塞
                threading.Timer(2.0, self.start_monitoring).start()
        except Exception as e:
            logger.error(f"自动启动监控失败: {e}")
    
    def _load_settings(self) -> Dict[str, Any]:
        """
        从数据库加载设置
        
        Returns:
            Dict[str, Any]: 解析后的设置字典
        """
        with DatabaseManager(self.db_path) as db:
            settings = db.get_all_settings()
        
        # 解析设置值
        parsed_settings = {}
        
        # 监控启用状态
        monitor_enabled = settings.get("monitor_enabled", "0")
        parsed_settings["monitor_enabled"] = monitor_enabled == "1"
        
        # 收件人邮箱列表
        recipient_emails_json = settings.get("recipient_emails", "[]")
        try:
            parsed_settings["recipient_emails"] = json.loads(recipient_emails_json)
        except json.JSONDecodeError:
            logger.warning(f"无法解析收件人邮箱JSON: {recipient_emails_json}")
            parsed_settings["recipient_emails"] = []
        
        # 检查间隔
        check_interval_str = settings.get("check_interval_hours", "2")
        try:
            parsed_settings["check_interval_hours"] = float(check_interval_str)
        except ValueError:
            logger.warning(f"无效的检查间隔: {check_interval_str}，使用默认值2小时")
            parsed_settings["check_interval_hours"] = 2.0
        
        logger.debug(f"加载设置: {parsed_settings}")
        return parsed_settings
    
    def _create_monitor(self) -> Optional[MultiWebsiteMonitor]:
        """
        创建监控器实例
        
        Returns:
            Optional[MultiWebsiteMonitor]: 监控器实例，失败时返回None
        """
        try:
            settings = self._load_settings()
            
            # 从email_sender模块获取默认的发件人配置
            # 注意：这些配置应该来自环境变量或配置文件，而不是硬编码
            sender_email = EmailSender.SENDER_EMAIL
            sender_password = EmailSender.SENDER_PASSWORD
            smtp_server = EmailSender.SMTP_SERVER
            smtp_port = EmailSender.SMTP_PORT
            
            # 从设置获取收件人邮箱
            recipient_emails = settings.get("recipient_emails", [])
            
            # 如果收件人列表为空，禁用邮件通知
            enable_email = len(recipient_emails) > 0
            
            # 获取所有网站配置
            website_configs = get_all_websites()
            
            # 创建监控器
            monitor = MultiWebsiteMonitor(
                website_configs=website_configs,
                db_path=self.db_path,
                check_interval_hours=settings.get("check_interval_hours", 2),
                enable_email=enable_email,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                sender_email=sender_email,
                sender_password=sender_password,
                recipient_emails=recipient_emails
            )
            
            logger.info("监控器创建成功")
            return monitor
            
        except Exception as e:
            logger.error(f"创建监控器失败: {e}")
            return None
    
    def run_once(self, send_email: bool = True) -> Dict[str, int]:
        """
        运行单次监控检查
        
        Args:
            send_email: 是否发送邮件通知（默认True）
            
        Returns:
            Dict[str, int]: 每个网站发现的新报告数量
        """
        with self.lock:
            if self.monitor is None:
                self.monitor = self._create_monitor()
            
            if self.monitor is None:
                logger.error("无法创建监控器，检查失败")
                return {}
        
        start_time = datetime.now()
        start_timestamp = time.perf_counter()
        results = {}
        new_reports_count = 0
        status = 'success'
        error_message = None
        
        try:
            logger.info("开始单次监控检查")
            results = self.monitor.run_once(send_email=send_email, delay_between_sites=30)
            new_reports_count = sum(results.values())
            logger.info(f"单次监控检查完成: {results}")
            
        except Exception as e:
            logger.error(f"单次监控检查失败: {e}")
            status = 'error'
            error_message = str(e)
            results = {}
        
        end_timestamp = time.perf_counter()
        end_time = datetime.now()
        duration_seconds = end_timestamp - start_timestamp
        
        # 插入监控运行记录到数据库
        try:
            with DatabaseManager(self.db_path) as db:
                db.insert_monitor_run(
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration_seconds,
                    new_reports_count=new_reports_count,
                    results_json=json.dumps(results) if results else None,
                    status=status,
                    error_message=error_message
                )
                logger.debug(f"监控运行记录已保存，耗时: {duration_seconds:.2f}秒")
        except Exception as e:
            logger.error(f"保存监控运行记录失败: {e}")
        
        return results
    
    def _run_once_with_email(self) -> Dict[str, int]:
        """
        包装方法，用于调度任务，始终发送邮件
        """
        return self.run_once(send_email=True)
    
    def send_test_email(self) -> Dict[str, Any]:
        """
        发送测试邮件
        
        Returns:
            Dict[str, Any]: 发送结果信息
        """
        try:
            # 加载设置获取收件人邮箱
            settings = self._load_settings()
            recipient_emails = settings.get("recipient_emails", [])
            
            if not recipient_emails:
                return {
                    'success': False,
                    'error': '收件人邮箱列表为空，请先在设置中配置收件人邮箱。'
                }
            
            # 读取邮件发送配置 - 使用EmailSender类属性，它已处理.env文件加载
            # 记录当前配置状态以帮助调试
            provider = os.environ.get("EMAIL_PROVIDER", EmailSender.EMAIL_PROVIDER).lower()
            logger.info(f"调试信息: 邮件提供商={provider}")
            logger.info(f"调试信息: os.environ SMTP_SERVER={os.environ.get('SMTP_SERVER', '未设置')}")
            logger.info(f"调试信息: EmailSender.SMTP_SERVER={EmailSender.SMTP_SERVER}")
            logger.info(f"调试信息: EmailSender.SMTP_PORT={EmailSender.SMTP_PORT}")
            logger.info(f"调试信息: EmailSender.SENDER_EMAIL={EmailSender.SENDER_EMAIL}")
            
            # 优先使用环境变量，如果没有则使用EmailSender类属性
            smtp_server = os.environ.get("SMTP_SERVER", EmailSender.SMTP_SERVER)
            smtp_port_str = os.environ.get("SMTP_PORT", str(EmailSender.SMTP_PORT))
            sender_email = os.environ.get("SENDER_EMAIL", EmailSender.SENDER_EMAIL)
            sender_password = os.environ.get("SENDER_PASSWORD", EmailSender.SENDER_PASSWORD)
            
            # 如果密码为空，尝试从EmailSender.SENDER_PASSWORD获取
            if not sender_password and EmailSender.SENDER_PASSWORD:
                sender_password = EmailSender.SENDER_PASSWORD
            
            # 转换端口为整数
            try:
                smtp_port = int(smtp_port_str)
            except ValueError:
                logger.warning(f"SMTP端口格式无效: {smtp_port_str}，使用默认值{EmailSender.SMTP_PORT}")
                smtp_port = EmailSender.SMTP_PORT
            
            # 记录使用的配置（不包含密码）
            logger.info(f"使用邮件配置: 发件人={sender_email}")
            logger.info(f"  SMTP服务器={smtp_server}, 端口={smtp_port}")
            
            # 创建邮件发送器实例
            email_sender = EmailSender(
                provider=provider,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                sender_email=sender_email,
                sender_password=sender_password,
                recipient_emails=recipient_emails
            )
            
            # 测试邮件服务连接
            logger.info(f"测试{provider}邮件服务连接...")
            connection_success, connection_error = email_sender.test_connection()
            if not connection_success:
                logger.error(f"邮件服务连接测试失败: {connection_error}")
                return {
                    'success': False,
                    'error': f'邮件服务连接测试失败: {connection_error}'
                }
            
            # 发送测试邮件
            logger.info("发送测试邮件...")
            success = email_sender.send_report_notification(
                title="测试报告 - ThinkTank Monitor",
                url="https://github.com/your-repo/thinktank-monitor",
                source_website="ThinkTank Monitor"
            )
            
            if success:
                logger.info("测试邮件发送成功")
                return {
                    'success': True,
                    'message': f'测试邮件已发送到 {", ".join(recipient_emails)}，请检查收件箱。'
                }
            else:
                return {
                    'success': False,
                    'error': '测试邮件发送失败，请检查邮件配置和网络连接。'
                }
                
        except Exception as e:
            logger.error(f"发送测试邮件失败: {e}")
            return {
                'success': False,
                'error': f'发送测试邮件时发生错误: {str(e)}'
            }
    
    def get_smtp_config(self) -> Dict[str, Any]:
        """
        获取当前邮件配置（保持向后兼容）
        
        Returns:
            Dict[str, Any]: 邮件配置信息
        """
        try:
            # 从环境变量读取邮件配置
            provider = os.environ.get("EMAIL_PROVIDER", EmailSender.EMAIL_PROVIDER).lower()
            smtp_server = os.environ.get("SMTP_SERVER", EmailSender.SMTP_SERVER)
            smtp_port_str = os.environ.get("SMTP_PORT", str(EmailSender.SMTP_PORT))
            sender_email = os.environ.get("SENDER_EMAIL", EmailSender.SENDER_EMAIL)
            
            # 转换端口为整数
            try:
                smtp_port = int(smtp_port_str)
            except ValueError:
                smtp_port = EmailSender.SMTP_PORT
            
            # 返回配置信息
            config = {
                'success': True,
                'provider': provider,
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'sender_email': sender_email,
                'is_configured': bool(sender_email and sender_email != 'your_email@outlook.com')
            }
            
            return config
        except Exception as e:
            logger.error(f"获取邮件配置失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def start_monitoring(self) -> bool:
        """
        开始持续监控（使用APScheduler）
        
        Returns:
            bool: 是否成功启动
        """
        with self.lock:
            if self.is_running:
                logger.warning("监控已经在运行中")
                return False
            
            # 更新数据库设置，标记监控为启用
            with DatabaseManager(self.db_path) as db:
                db.set_setting("monitor_enabled", "1")
            
            # 创建监控器
            if self.monitor is None:
                self.monitor = self._create_monitor()
            
            if self.monitor is None:
                logger.error("无法创建监控器，启动失败")
                return False
            
            try:
                # 获取检查间隔
                settings = self._load_settings()
                check_interval_hours = settings.get("check_interval_hours", 2)
                check_interval_seconds = int(check_interval_hours * 3600)
                
                # 添加调度任务
                trigger = IntervalTrigger(seconds=check_interval_seconds)
                self.scheduler.add_job(
                    func=self._run_once_with_email,
                    trigger=trigger,
                    id=self.job_id,
                    name="网站监控任务",
                    replace_existing=True,
                    max_instances=1
                )
                
                # 启动调度器（如果尚未启动）
                if not self.scheduler.running:
                    self.scheduler.start()
                    logger.info("APScheduler已启动")
                
                self.is_running = True
                
                # 立即运行一次检查
                self.scheduler.add_job(
                    func=self._run_once_with_email,
                    trigger='date',
                    run_date=datetime.now(),
                    id=f"{self.job_id}_initial",
                    name="初始检查任务"
                )
                
                logger.info(f"监控已启动，检查间隔: {check_interval_hours}小时")
                return True
                
            except Exception as e:
                logger.error(f"启动监控失败: {e}")
                return False
    
    def stop_monitoring(self) -> bool:
        """
        停止持续监控
        
        Returns:
            bool: 是否成功停止
        """
        with self.lock:
            if not self.is_running:
                logger.warning("监控未在运行中")
                return False
            
            # 更新数据库设置，标记监控为禁用
            with DatabaseManager(self.db_path) as db:
                db.set_setting("monitor_enabled", "0")
            
            try:
                # 移除调度任务
                if self.scheduler.get_job(self.job_id):
                    self.scheduler.remove_job(self.job_id)
                    logger.info("监控任务已从调度器移除")
                
                self.is_running = False
                logger.info("监控已停止")
                return True
                
            except Exception as e:
                logger.error(f"停止监控失败: {e}")
                return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取监控状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        with self.lock:
            settings = self._load_settings()
            
            status = {
                "is_running": self.is_running,
                "monitor_enabled": settings.get("monitor_enabled", False),
                "check_interval_hours": settings.get("check_interval_hours", 2),
                "recipient_emails": settings.get("recipient_emails", []),
                "website_count": len(get_all_websites()) if hasattr(get_all_websites, '__call__') else 0,
            }
            
            # 获取调度器状态
            if self.scheduler:
                status["scheduler_running"] = self.scheduler.running
                if self.scheduler.get_job(self.job_id):
                    job = self.scheduler.get_job(self.job_id)
                    status["next_run_time"] = str(job.next_run_time) if job.next_run_time else None
                else:
                    status["next_run_time"] = None
            else:
                status["scheduler_running"] = False
                status["next_run_time"] = None
            
            # 获取报告统计
            try:
                with DatabaseManager(self.db_path) as db:
                    all_reports = db.get_all_reports()
                    unsent_reports = db.get_unsent_reports()
                    
                    status["total_reports"] = len(all_reports)
                    status["sent_reports"] = len(all_reports) - len(unsent_reports)
                    status["unsent_reports"] = len(unsent_reports)
            except Exception as e:
                logger.error(f"获取报告统计失败: {e}")
                status["total_reports"] = 0
                status["sent_reports"] = 0
                status["unsent_reports"] = 0
            
            return status
    
    def get_recent_reports(self, limit: int = 20, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        获取最近的报告
        
        Args:
            limit: 返回的报告数量限制
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            
        Returns:
            List[Dict[str, Any]]: 报告列表
        """
        try:
            with DatabaseManager(self.db_path) as db:
                all_reports = db.get_all_reports()
                
                # 按发布日期降序排序，如果发布日期为空则按发现时间排序
                def get_sort_key(report):
                    # 优先使用发布日期
                    publish_date = report.get('publish_date')
                    if publish_date and publish_date != 'None':
                        return publish_date
                    # 其次使用发现时间
                    discovered_time = report.get('discovered_time', '')
                    # 提取日期部分（处理多种格式）
                    if not discovered_time:
                        return ''
                    
                    # 处理ISO格式: 2026-02-28T15:01:17.198158
                    if 'T' in discovered_time:
                        return discovered_time.split('T')[0]
                    # 处理空格分隔格式: YYYY-MM-DD HH:MM:SS
                    elif ' ' in discovered_time:
                        return discovered_time.split(' ')[0]
                    # 其他格式直接返回
                    else:
                        return discovered_time
                
                sorted_reports = sorted(
                    all_reports,
                    key=get_sort_key,
                    reverse=True
                )
                
                # 日期筛选
                if start_date or end_date:
                    filtered_reports = []
                    for report in sorted_reports:
                        # 优先使用发布日期，其次使用发现时间
                        date_str = report.get('publish_date')
                        if not date_str or date_str == 'None':
                            discovered_time = report.get('discovered_time', '')
                            if not discovered_time:
                                continue
                            # 提取日期部分（处理多种格式，与get_sort_key一致）
                            if 'T' in discovered_time:
                                date_str = discovered_time.split('T')[0]
                            elif ' ' in discovered_time:
                                date_str = discovered_time.split(' ')[0]
                            else:
                                date_str = discovered_time
                        
                        # 日期比较
                        if start_date and date_str < start_date:
                            continue
                        if end_date and date_str > end_date:
                            continue
                            
                        filtered_reports.append(report)
                    
                    sorted_reports = filtered_reports
                
                return sorted_reports[:limit]
                
        except Exception as e:
            logger.error(f"获取最近报告失败: {e}")
            return []
    def get_recent_monitor_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的监控运行记录
        
        Args:
            limit: 返回记录数量限制
        
        Returns:
            List[Dict[str, Any]]: 监控运行记录列表
        """
        try:
            with DatabaseManager(self.db_path) as db:
                return db.get_recent_monitor_runs(limit=limit)
        except Exception as e:
            logger.error(f"获取监控运行记录失败: {e}")
            return []
    
    def _extract_date_from_title(self, title: str) -> Optional[datetime]:
        """
        从标题中提取发布日期
        
        Args:
            title: 报告标题
            
        Returns:
            Optional[datetime]: 提取到的日期，如果提取失败则返回None
        """
        import re
        from datetime import datetime
        
        if not title:
            return None
        
        # 常见日期模式
        date_patterns = [
            # 完整月份名称 + 日期 + 年份 (February 27, 2026)
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})', '%B %d, %Y'),
            # 缩写月份名称 + 日期 + 年份 (Feb 27, 2026)
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})', '%b %d, %Y'),
            # YYYY-MM-DD 格式
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
            # MM/DD/YYYY 格式
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),
            # DD/MM/YYYY 格式
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%d/%m/%Y'),
        ]
        
        for pattern, date_format in date_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                try:
                    # 提取匹配的日期字符串
                    date_str = match.group(0)
                    return datetime.strptime(date_str, date_format)
                except (ValueError, AttributeError) as e:
                    logger.debug(f"日期解析失败: {date_str}, 格式: {date_format}, 错误: {e}")
                    continue
        
        return None
    
    def _get_publish_date(self, report: Dict[str, Any]) -> Optional[datetime]:
        """
        获取报告的发布日期
        
        优先使用publish_date字段，如果为空则从标题中提取
        
        Args:
            report: 报告字典
            
        Returns:
            Optional[datetime]: 发布日期，如果无法获取则返回None
        """
        from datetime import datetime
        
        # 首先尝试使用publish_date字段
        publish_date_str = report.get('publish_date')
        if publish_date_str:
            try:
                # 尝试解析ISO格式日期
                return datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # 如果ISO格式解析失败，尝试其他常见格式
                date_formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%Y/%m/%d',
                    '%d/%m/%Y',
                ]
                
                for date_format in date_formats:
                    try:
                        return datetime.strptime(publish_date_str, date_format)
                    except ValueError:
                        continue
        
        # 如果publish_date字段为空或解析失败，尝试从标题中提取
        title = report.get('title', '')
        return self._extract_date_from_title(title)
    
    def get_recent_tweets(self, days: int = 30, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取最近发布的推文（报告）
        
        Args:
            days: 最近多少天内（默认30天）
            limit: 返回的最大数量限制（默认50）
            
        Returns:
            List[Dict[str, Any]]: 推文列表，包含额外字段publish_date_parsed
        """
        try:
            from datetime import datetime, timedelta
            
            with DatabaseManager(self.db_path) as db:
                all_reports = db.get_all_reports()
                
                # 计算截止日期
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # 处理每个报告，提取发布日期
                recent_tweets = []
                for report in all_reports:
                    # 获取发布日期（优先使用发布日期，其次使用发现时间）
                    publish_date = self._get_publish_date(report)
                    
                    # 如果没有发布日期，尝试使用发现时间
                    if not publish_date:
                        discovered_time_str = report.get('discovered_time')
                        if discovered_time_str:
                            try:
                                # 尝试解析ISO格式的发现时间
                                publish_date = datetime.fromisoformat(discovered_time_str.replace('Z', '+00:00'))
                            except (ValueError, AttributeError):
                                # 如果解析失败，跳过该报告
                                continue
                        else:
                            # 既没有发布日期也没有发现时间，跳过
                            continue
                    
                    # 检查是否在指定时间范围内
                    if publish_date >= cutoff_date:
                        # 添加解析后的日期字段
                        report_with_date = report.copy()
                        report_with_date['publish_date_parsed'] = publish_date
                        recent_tweets.append(report_with_date)
                
                # 按发布日期降序排序（最新的在前）
                recent_tweets.sort(key=lambda x: x['publish_date_parsed'], reverse=True)
                
                # 限制返回数量
                return recent_tweets[:limit]
                
        except Exception as e:
            logger.error(f"获取最近推文失败: {e}")
            return []

    def send_unsent_reports(self) -> Dict[str, Any]:
        """
        发送未发送的报告邮件
        
        Returns:
            Dict[str, Any]: 发送结果信息
        """
        try:
            # 确保监控器存在（用于获取邮件发送器）
            if self.monitor is None:
                self.monitor = self._create_monitor()
            
            if self.monitor is None:
                return {
                    'success': False,
                    'error': '无法创建监控器，邮件发送失败'
                }
            
            # 获取最近15分钟内未发送的报告，只发送本次监控中发现的新报告
            # 排除最近5分钟内发现的报告，避免与正在进行的邮件发送冲突
            from datetime import datetime, timedelta
            with DatabaseManager(self.db_path) as db:
                unsent_reports = db.get_unsent_reports(hours=0.25)  # 15分钟
                
            if not unsent_reports:
                return {
                    'success': True,
                    'message': '没有未发送的报告',
                    'sent_count': 0
                }
            
            # 过滤掉最近5分钟内发现的报告
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            filtered_reports = []
            for report in unsent_reports:
                try:
                    discovered_str = report.get('discovered_time')
                    if discovered_str:
                        if 'T' in discovered_str:
                            discovered_time = datetime.fromisoformat(discovered_str.replace('Z', '+00:00'))
                        else:
                            discovered_time = datetime.strptime(discovered_str, '%Y-%m-%d %H:%M:%S')
                        
                        # 如果报告发现时间在5分钟以前，才包含
                        if discovered_time < five_minutes_ago:
                            filtered_reports.append(report)
                        else:
                            logger.debug(f"跳过最近发现的报告（避免重复发送）: {report.get('title', 'Unknown')}")
                    else:
                        filtered_reports.append(report)
                except (ValueError, KeyError) as e:
                    logger.warning(f"解析报告发现时间失败 {report.get('id', 'unknown')}: {e}")
                    filtered_reports.append(report)  # 无法解析时间，包含以防万一
            
            if not filtered_reports:
                return {
                    'success': True,
                    'message': '过滤后没有未发送的报告（可能都是最近5分钟内发现的）',
                    'sent_count': 0
                }
            
            unsent_reports = filtered_reports
            
            sent_count = 0
            failed_count = 0
            
            # 使用监控器的邮件发送器
            email_sender = self.monitor.email_sender
            if not email_sender:
                return {
                    'success': False,
                    'error': '邮件发送器未初始化'
                }
            
            for report in unsent_reports:
                try:
                    success = email_sender.send_report_notification(
                        title=report['title'],
                        url=report['url'],
                        source_website=report['source_website']
                    )
                    
                    if success:
                        # 标记报告为已发送
                        with DatabaseManager(self.db_path) as db:
                            db.mark_report_as_sent(report['id'])
                        sent_count += 1
                        logger.info(f"未发送报告邮件发送成功: {report['title']}")
                    else:
                        failed_count += 1
                        logger.warning(f"未发送报告邮件发送失败: {report['title']}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"发送未发送报告时出错: {e}")
            
            message = f"已发送 {sent_count} 个未发送报告，失败 {failed_count} 个"
            return {
                'success': True,
                'message': message,
                'sent_count': sent_count,
                'failed_count': failed_count,
                'total_count': len(unsent_reports)
            }
            
        except Exception as e:
            logger.error(f"发送未发送报告失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def update_settings(self, recipient_emails: List[str] = None, 
                       check_interval_hours: float = None) -> bool:
        """
        更新设置
        
        Args:
            recipient_emails: 收件人邮箱列表
            check_interval_hours: 检查间隔（小时）
            
        Returns:
            bool: 是否成功更新
        """
        try:
            with DatabaseManager(self.db_path) as db:
                if recipient_emails is not None:
                    # 验证邮箱格式（简单验证）
                    valid_emails = []
                    for email in recipient_emails:
                        if '@' in email and '.' in email:
                            valid_emails.append(email.strip())
                        else:
                            logger.warning(f"跳过无效邮箱格式: {email}")
                    
                    # 保存为JSON
                    emails_json = json.dumps(valid_emails)
                    db.set_setting("recipient_emails", emails_json)
                    logger.info(f"更新收件人邮箱: {valid_emails}")
                
                if check_interval_hours is not None:
                    # 验证间隔
                    if check_interval_hours < 0.1:
                        check_interval_hours = 0.1
                    elif check_interval_hours > 24:
                        check_interval_hours = 24
                    
                    db.set_setting("check_interval_hours", str(check_interval_hours))
                    logger.info(f"更新检查间隔: {check_interval_hours}小时")
            
            # 如果监控正在运行，更新调度任务
            if self.is_running:
                self._reschedule_job()
            
            return True
            
        except Exception as e:
            logger.error(f"更新设置失败: {e}")
            return False
    
    def _reschedule_job(self):
        """重新调度任务（当检查间隔改变时）"""
        with self.lock:
            if not self.is_running or not self.scheduler:
                return
            
            try:
                # 获取当前检查间隔
                settings = self._load_settings()
                check_interval_hours = settings.get("check_interval_hours", 2)
                check_interval_seconds = int(check_interval_hours * 3600)
                
                # 移除旧任务
                if self.scheduler.get_job(self.job_id):
                    self.scheduler.remove_job(self.job_id)
                
                # 添加新任务
                trigger = IntervalTrigger(seconds=check_interval_seconds)
                self.scheduler.add_job(
                    func=self._run_once_with_email,
                    trigger=trigger,
                    id=self.job_id,
                    name="网站监控任务",
                    replace_existing=True,
                    max_instances=1
                )
                
                logger.info(f"监控任务已重新调度，新间隔: {check_interval_hours}小时")
                
            except Exception as e:
                logger.error(f"重新调度任务失败: {e}")
    
    def export_reports(self, format: str = 'csv', start_date: str = None, end_date: str = None) -> tuple[str, str]:
        """
        导出报告为指定格式
        
        Args:
            format: 导出格式，目前只支持'csv'
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            
        Returns:
            tuple[str, str]: (文件内容, 文件名)
        """
        try:
            # 获取报告数据（使用大限制或不限制，因为这是导出操作）
            reports = self.get_recent_reports(limit=10000, start_date=start_date, end_date=end_date)
            
            if format.lower() == 'csv':
                # 生成CSV内容
                csv_lines = []
                
                # CSV头部
                headers = ['标题', '链接', '来源', '发布日期', '发现时间', '邮件状态']
                csv_lines.append(','.join(headers))
                
                # 数据行
                for report in reports:
                    title = report.get('title', '')
                    url = report.get('url', '')
                    source = report.get('source_website', '')
                    publish_date = report.get('publish_date', '')
                    discovered_time = report.get('discovered_time', '')
                    sent_status = '已发送' if report.get('sent_status') else '未发送'
                    
                    # 处理CSV特殊字符：将双引号替换为两个双引号，并用双引号包裹字段
                    title_escaped = title.replace('"', '""')
                    url_escaped = url.replace('"', '""')
                    source_escaped = source.replace('"', '""')
                    
                    # 构建CSV行
                    row = [
                        f'"{title_escaped}"',
                        f'"{url_escaped}"',
                        f'"{source_escaped}"',
                        f'"{publish_date}"',
                        f'"{discovered_time}"',
                        f'"{sent_status}"'
                    ]
                    csv_lines.append(','.join(row))
                
                csv_content = '\n'.join(csv_lines)
                
                # 生成文件名
                date_range = ''
                if start_date and end_date:
                    date_range = f'_{start_date}_至_{end_date}'
                elif start_date:
                    date_range = f'_从_{start_date}'
                elif end_date:
                    date_range = f'_至_{end_date}'
                
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'thinktank_reports{date_range}_{timestamp}.csv'
                
                return csv_content, filename
                
            else:
                raise ValueError(f"不支持的导出格式: {format}")
                
        except Exception as e:
            logger.error(f"导出报告失败: {e}")
            raise
    
    def get_recent_stats(self, days: int = 10) -> Dict[str, Any]:
        """
        获取最近N天的报告统计数据
        
        Args:
            days: 统计天数，默认为10天
            
        Returns:
            Dict[str, Any]: 统计数据，包含每日总计和网站来源分布
        """
        try:
            with DatabaseManager(self.db_path) as db:
                return db.get_recent_stats(days=days)
        except Exception as e:
            logger.error(f"获取近期统计数据失败: {e}")
            return {
                "days": days,
                "start_date": "",
                "end_date": "",
                "daily_totals": [],
                "website_distribution": {},
                "all_websites": []
            }
    
    def shutdown(self):
        """关闭监控服务（清理资源）"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("APScheduler已关闭")
        except Exception as e:
            logger.error(f"关闭调度器失败: {e}")


# 全局监控服务实例
_monitor_service = None

def get_monitor_service(db_path: str = None) -> MonitorService:
    """
    获取全局监控服务实例（单例模式）
    
    Args:
        db_path: 数据库文件路径，如果为None则使用环境变量DATABASE_PATH或默认值
        
    Returns:
        MonitorService: 监控服务实例
    """
    global _monitor_service
    
    if _monitor_service is None:
        # 优先使用环境变量DATABASE_PATH，其次使用传入参数，最后使用默认值
        if db_path is None:
            db_path = os.environ.get('DATABASE_PATH', 'reports.db')
        _monitor_service = MonitorService(db_path)
    
    return _monitor_service


def shutdown_monitor_service():
    """关闭监控服务（在应用退出时调用）"""
    global _monitor_service
    if _monitor_service:
        _monitor_service.shutdown()
        _monitor_service = None


if __name__ == "__main__":
    # 测试监控服务
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    service = get_monitor_service()
    
    print("1. 获取监控状态:")
    status = service.get_status()
    print(f"   运行状态: {'运行中' if status['is_running'] else '停止'}")
    print(f"   监控启用: {'是' if status['monitor_enabled'] else '否'}")
    print(f"   检查间隔: {status['check_interval_hours']}小时")
    print(f"   收件人邮箱: {status['recipient_emails']}")
    print(f"   网站数量: {status['website_count']}")
    print(f"   报告统计: 总共 {status['total_reports']}, 已发送 {status['sent_reports']}, 未发送 {status['unsent_reports']}")
    print(f"   调度器状态: {'运行中' if status.get('scheduler_running') else '停止'}")
    print(f"   下次运行时间: {status.get('next_run_time', 'N/A')}")
    
    print("\n2. 运行单次检查:")
    results = service.run_once(delay_between_sites=30)
    if results:
        print(f"   检查结果: {results}")
    else:
        print("   检查失败或无新报告")
    
    print("\n3. 获取最近5个报告:")
    reports = service.get_recent_reports(limit=5)
    for i, report in enumerate(reports, 1):
        print(f"   {i}. {report.get('title', '无标题')}")
        print(f"      来源: {report.get('source_website', '未知')}")
        print(f"      发现时间: {report.get('discovered_time', '未知')}")
        print(f"      链接: {report.get('url', '无链接')[:50]}...")
    
    print("\n4. 测试启动和停止监控:")
    if status['is_running']:
        print("   监控正在运行，正在停止...")
        service.stop_monitoring()
    else:
        print("   监控未运行，正在启动...")
        service.start_monitoring()
    
    print("\n监控服务测试完成")
    
    # 关闭服务
    shutdown_monitor_service()