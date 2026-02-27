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
    
    def run_once(self) -> Dict[str, int]:
        """
        运行单次监控检查
        
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
            results = self.monitor.run_once()
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
            
            # 读取SMTP配置 - 使用EmailSender类属性，它已处理.env文件加载
            # 记录当前配置状态以帮助调试
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
            
            # 记录使用的SMTP配置（不包含密码）
            logger.info(f"使用SMTP配置: 服务器={smtp_server}, 端口={smtp_port}, 发件人={sender_email}")
            
            # 创建邮件发送器实例
            email_sender = EmailSender(
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                sender_email=sender_email,
                sender_password=sender_password,
                recipient_emails=recipient_emails
            )
            
            # 测试SMTP连接
            logger.info("测试SMTP连接...")
            connection_success, connection_error = email_sender.test_connection()
            if not connection_success:
                logger.error(f"SMTP连接测试失败: {connection_error}")
                return {
                    'success': False,
                    'error': f'SMTP连接测试失败: {connection_error}'
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
                    'error': '测试邮件发送失败，请检查SMTP配置和网络连接。'
                }
                
        except Exception as e:
            logger.error(f"发送测试邮件失败: {e}")
            return {
                'success': False,
                'error': f'发送测试邮件时发生错误: {str(e)}'
            }
    
    def get_smtp_config(self) -> Dict[str, Any]:
        """
        获取当前SMTP配置
        
        Returns:
            Dict[str, Any]: SMTP配置信息
        """
        try:
            # 从环境变量读取SMTP配置
            smtp_server = os.environ.get("SMTP_SERVER", EmailSender.SMTP_SERVER)
            smtp_port_str = os.environ.get("SMTP_PORT", str(EmailSender.SMTP_PORT))
            sender_email = os.environ.get("SENDER_EMAIL", EmailSender.SENDER_EMAIL)
            
            # 转换端口为整数
            try:
                smtp_port = int(smtp_port_str)
            except ValueError:
                smtp_port = EmailSender.SMTP_PORT
            
            # 返回配置信息（不包含密码）
            return {
                'success': True,
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'sender_email': sender_email,
                'is_configured': bool(sender_email and sender_email != 'your_email@outlook.com')
            }
        except Exception as e:
            logger.error(f"获取SMTP配置失败: {e}")
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
                    func=self.run_once,
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
                    func=self.run_once,
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
    
    def get_recent_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近的报告
        
        Args:
            limit: 返回的报告数量限制
            
        Returns:
            List[Dict[str, Any]]: 报告列表
        """
        try:
            with DatabaseManager(self.db_path) as db:
                all_reports = db.get_all_reports()
                # 按发现时间降序排序
                sorted_reports = sorted(
                    all_reports,
                    key=lambda x: x.get('discovered_time', ''),
                    reverse=True
                )
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
                    func=self.run_once,
                    trigger=trigger,
                    id=self.job_id,
                    name="网站监控任务",
                    replace_existing=True,
                    max_instances=1
                )
                
                logger.info(f"监控任务已重新调度，新间隔: {check_interval_hours}小时")
                
            except Exception as e:
                logger.error(f"重新调度任务失败: {e}")
    
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
    results = service.run_once()
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