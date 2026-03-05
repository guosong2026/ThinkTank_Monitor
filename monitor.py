"""
网站监控主程序
定时抓取网站报告并存储到数据库
"""

import logging
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from db import DatabaseManager
from scraper import WebsiteScraper
from email_sender import EmailSender
from website_configs import WebsiteConfig, get_all_websites

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # 控制台输出
        logging.FileHandler('monitor.log', encoding='utf-8')  # 文件输出
    ]
)
logger = logging.getLogger(__name__)


class WebsiteMonitor:
    """网站监控器类"""
    
    def __init__(self, target_url: str, db_path: str = "reports.db", 
                 check_interval_hours: int = 2,
                 enable_email: bool = True,
                 smtp_server: str = None, smtp_port: int = None,
                 sender_email: str = None, sender_password: str = None,
                 recipient_emails: List[str] = None):
        """
        初始化网站监控器
        
        Args:
            target_url: 目标网站URL
            db_path: 数据库文件路径
            check_interval_hours: 检查间隔（小时）
            enable_email: 是否启用邮件通知
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender_email: 发件人邮箱
            sender_password: 发件人密码/授权码
            recipient_emails: 收件人邮箱列表
        """
        self.target_url = target_url
        self.db_path = db_path
        self.check_interval_seconds = check_interval_hours * 3600
        self.enable_email = enable_email
        
        # 来源网站（从URL提取域名）
        self.source_website = self._extract_domain(target_url)
        
        # 初始化邮件发送器（如果启用）
        self.email_sender = None
        if self.enable_email:
            try:
                self.email_sender = EmailSender(
                    smtp_server=smtp_server,
                    smtp_port=smtp_port,
                    sender_email=sender_email,
                    sender_password=sender_password,
                    recipient_emails=recipient_emails
                )
                logger.info("邮件发送器初始化成功")
            except Exception as e:
                logger.error(f"邮件发送器初始化失败: {e}")
                logger.warning("邮件通知功能将禁用")
                self.enable_email = False
        
        logger.info(f"初始化网站监控器")
        logger.info(f"目标URL: {target_url}")
        logger.info(f"数据库: {db_path}")
        logger.info(f"检查间隔: {check_interval_hours}小时")
        logger.info(f"邮件通知: {'启用' if self.enable_email else '禁用'}")
    
    def _extract_domain(self, url: str) -> str:
        """
        从URL中提取域名
        
        Args:
            url: 完整URL
            
        Returns:
            str: 域名
        """
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        return domain if domain else "unknown"
    
    def _extract_date_from_title(self, title: str):
        """
        从标题中提取发布日期
        
        Args:
            title: 报告标题
            
        Returns:
            str: 提取到的日期字符串（YYYY-MM-DD格式），如果提取失败则返回None
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
                    dt = datetime.strptime(date_str, date_format)
                    return dt.strftime('%Y-%m-%d')
                except (ValueError, AttributeError) as e:
                    logger.debug(f"日期解析失败: {date_str}, 格式: {date_format}, 错误: {e}")
                    continue
        
        return None
    
    def run_once(self, send_email: bool = True) -> int:
        """
        执行单次监控检查
        
        Args:
            send_email: 是否发送邮件通知（默认True）
            
        Returns:
            int: 发现的新报告数量
        """
        new_reports_count = 0
        
        try:
            logger.info("开始单次监控检查")
            
            # 创建抓取器和数据库管理器
            with WebsiteScraper(self.target_url) as scraper, \
                 DatabaseManager(self.db_path) as db:
                
                # 抓取报告
                reports = scraper.scrape_reports()
                
                if not reports:
                    logger.warning("未抓取到任何报告")
                    return 0
                
                logger.info(f"抓取到 {len(reports)} 个报告，正在保存到数据库...")
                
                # 保存每个报告到数据库并发送邮件通知
                for report in reports:
                    title = report['title']
                    url = report['url']
                    
                    # 尝试插入数据库
                    # 尝试从标题中提取发布日期
                    publish_date = self._extract_date_from_title(title)
                    report_id = db.insert_report(
                        title=title,
                        url=url,
                        source_website=self.source_website,
                        publish_date=publish_date
                    )
                    
                    if report_id:
                        new_reports_count += 1
                        # 记录发现的新报告
                        logger.debug(f"发现新报告：{title} - {url}")
                        
                        # 发送邮件通知（如果启用且允许发送邮件）
                        if send_email and self.enable_email and self.email_sender:
                            try:
                                email_success = self.email_sender.send_report_notification(
                                    title=title,
                                    url=url,
                                    source_website=self.source_website
                                )
                                
                                if email_success:
                                    # 标记报告为已发送
                                    db.mark_report_as_sent(report_id)
                                    logger.info(f"邮件通知发送成功: {title}")
                                else:
                                    logger.warning(f"邮件通知发送失败: {title}")
                            except Exception as e:
                                logger.error(f"发送邮件通知时出错: {e}")
                
                logger.info(f"检查完成，发现 {new_reports_count} 个新报告")
                
        except Exception as e:
            logger.error(f"监控检查失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return new_reports_count
    
    def run_continuous(self, max_runs: int = None):
        """
        连续运行监控检查
        
        Args:
            max_runs: 最大运行次数（None表示无限运行）
        """
        run_count = 0
        
        logger.info("开始连续监控模式")
        print(f"网站监控已启动，目标: {self.target_url}")
        print(f"检查间隔: {self.check_interval_seconds/3600}小时")
        print("按 Ctrl+C 停止监控")
        print("-" * 50)
        
        try:
            while True:
                # 检查是否达到最大运行次数
                if max_runs is not None and run_count >= max_runs:
                    logger.info(f"已达到最大运行次数 {max_runs}，停止监控")
                    break
                
                run_count += 1
                logger.info(f"开始第 {run_count} 次监控检查")
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 第 {run_count} 次检查...")
                
                # 执行单次检查
                new_reports = self.run_once(send_email=True)
                
                if new_reports > 0:
                    logger.info(f"本次检查发现 {new_reports} 个新报告")
                else:
                    logger.debug("本次检查未发现新报告")
                
                # 如果不是最后一次运行，则等待
                if max_runs is None or run_count < max_runs:
                    next_check_time = datetime.now() + timedelta(seconds=self.check_interval_seconds)
                    logger.debug(f"下次检查时间: {next_check_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug(f"等待 {self.check_interval_seconds/3600:.1f} 小时...")
                    
                    # 等待间隔时间，但允许被中断
                    self._wait_with_interrupt(self.check_interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("监控被用户中断")
            print("\n监控已停止")
        except Exception as e:
            logger.error(f"监控运行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            print(f"监控异常停止: {e}")
    
    def _wait_with_interrupt(self, seconds: int):
        """
        等待指定秒数，但允许被键盘中断
        
        Args:
            seconds: 等待秒数
        """
        try:
            # 分段等待，每10秒检查一次，以便更快响应中断
            interval = 10
            remaining = seconds
            
            while remaining > 0:
                sleep_time = min(interval, remaining)
                time.sleep(sleep_time)
                remaining -= sleep_time
                
                # 每30秒打印一次剩余时间
                if remaining > 0 and remaining % 30 == 0:
                    mins_remaining = remaining // 60
                    secs_remaining = remaining % 60
                    logger.debug(f"等待中，剩余时间: {mins_remaining}分{secs_remaining}秒")
        
        except KeyboardInterrupt:
            logger.info("等待被用户中断")
            raise
    
    def show_statistics(self):
        """显示监控统计信息"""
        try:
            with DatabaseManager(self.db_path) as db:
                reports = db.get_all_reports()
                unsent_reports = db.get_unsent_reports()
                
                print("\n" + "=" * 50)
                print("监控统计信息")
                print("=" * 50)
                print(f"数据库文件: {self.db_path}")
                print(f"目标网站: {self.target_url}")
                print(f"来源网站: {self.source_website}")
                print(f"邮件通知: {'启用' if self.enable_email else '禁用'}")
                print("-" * 50)
                print(f"总报告数量: {len(reports)}")
                print(f"已发送报告: {len(reports) - len(unsent_reports)}")
                print(f"未发送报告: {len(unsent_reports)}")
                
                if reports:
                    print("\n最近5个报告:")
                    for i, report in enumerate(reports[:5], 1):
                        sent_status = "✓" if report.get('sent_status') else "✗"
                        print(f"{i}. [{sent_status}] {report['title']}")
                        print(f"   链接: {report['url']}")
                        print(f"   发现时间: {report['discovered_time']}")
                        print()
                else:
                    print("\n数据库中暂无报告")
                
                print("=" * 50)
        
        except Exception as e:
            logger.error(f"显示统计信息失败: {e}")
    
    def send_unsent_reports(self) -> int:
        """
        发送数据库中未发送的报告
        
        Returns:
            int: 成功发送的报告数量
        """
        if not self.enable_email or not self.email_sender:
            logger.error("邮件通知功能未启用，无法发送未发送的报告")
            return 0
        
        try:
            with DatabaseManager(self.db_path) as db:
                # 获取未发送的报告
                unsent_reports = db.get_unsent_reports()
                
                if not unsent_reports:
                    logger.info("没有未发送的报告")
                    return 0
                
                logger.info(f"找到 {len(unsent_reports)} 个未发送的报告，开始发送邮件通知...")
                
                success_count = 0
                
                # 发送邮件通知
                for report in unsent_reports:
                    title = report['title']
                    url = report['url']
                    source_website = report.get('source_website', self.source_website)
                    report_id = report['id']
                    
                    try:
                        email_success = self.email_sender.send_report_notification(
                            title=title,
                            url=url,
                            source_website=source_website
                        )
                        
                        if email_success:
                            # 标记报告为已发送
                            db.mark_report_as_sent(report_id)
                            success_count += 1
                            logger.info(f"邮件通知发送成功: {title}")
                        else:
                            logger.warning(f"邮件通知发送失败: {title}")
                    except Exception as e:
                        logger.error(f"发送邮件通知时出错: {e}")
                
                logger.info(f"未发送报告处理完成: 成功 {success_count}/{len(unsent_reports)}")
                return success_count
                
        except Exception as e:
            logger.error(f"发送未发送报告时出错: {e}")
            return 0


class MultiWebsiteMonitor:
    """多网站监控器类"""
    
    def __init__(self, website_configs: List[WebsiteConfig], db_path: str = "reports.db",
                 check_interval_hours: int = 2,
                 enable_email: bool = True,
                 smtp_server: str = None, smtp_port: int = None,
                 sender_email: str = None, sender_password: str = None,
                 recipient_emails: List[str] = None):
        """
        初始化多网站监控器
        
        Args:
            website_configs: 网站配置列表
            db_path: 数据库文件路径
            check_interval_hours: 检查间隔（小时）
            enable_email: 是否启用邮件通知
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender_email: 发件人邮箱
            sender_password: 发件人密码/授权码
            recipient_emails: 收件人邮箱列表
        """
        self.website_configs = website_configs
        self.db_path = db_path
        self.check_interval_seconds = check_interval_hours * 3600
        self.enable_email = enable_email
        
        # 创建HTTP会话，重用连接提高性能
        import requests
        self.session = requests.Session()
        # 不信任环境变量中的代理配置，避免代理连接失败
        self.session.trust_env = False
        # 设置默认请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 初始化邮件发送器（如果启用）
        self.email_sender = None
        if self.enable_email:
            try:
                self.email_sender = EmailSender(
                    smtp_server=smtp_server,
                    smtp_port=smtp_port,
                    sender_email=sender_email,
                    sender_password=sender_password,
                    recipient_emails=recipient_emails
                )
                logger.info("邮件发送器初始化成功")
            except Exception as e:
                logger.error(f"邮件发送器初始化失败: {e}")
                logger.warning("邮件通知功能将禁用")
                self.enable_email = False
        
        logger.info(f"初始化多网站监控器")
        logger.info(f"监控网站数量: {len(website_configs)}")
        logger.info(f"数据库: {db_path}")
        logger.info(f"检查间隔: {check_interval_hours}小时")
        logger.info(f"邮件通知: {'启用' if self.enable_email else '禁用'}")
        
        # 打印监控的网站
        for config in website_configs:
            logger.info(f"  - {config.name}: {config.url}")
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """
        获取网页内容
        
        Args:
            url: 要获取的URL
            
        Returns:
            str: HTML内容，失败时返回None
        """
        import time
        from requests.exceptions import RequestException, ConnectionError, Timeout
        
        # 针对特定网站添加额外请求头
        additional_headers = {}
        if 'worldwildlife.org' in url:
            additional_headers['Referer'] = 'https://www.worldwildlife.org/'
            additional_headers['Origin'] = 'https://www.worldwildlife.org'
        
        max_retries = 2
        base_delay = 1  # 初始延迟秒数
        
        for retry_count in range(max_retries):
            try:
                if retry_count > 0:
                    logger.info(f"第 {retry_count + 1} 次重试获取页面: {url}")
                    # 指数退避延迟
                    delay = base_delay * (2 ** (retry_count - 1))
                    time.sleep(delay)
                else:
                    logger.debug(f"正在获取页面: {url}")
                
                # 使用共享的session，添加特定网站的额外请求头
                # 分别设置连接超时和读取超时：连接超时15秒，读取超时45秒
                response = self.session.get(url, timeout=(10, 20), 
                                       proxies={'http': None, 'https': None, 'ftp': None},
                                       verify=False,  # 关闭SSL验证，避免证书问题
                                       headers=additional_headers if additional_headers else None)
                response.raise_for_status()
                return response.text
                
            except (ConnectionError, Timeout) as e:
                # 连接错误或超时，进行重试
                if retry_count < max_retries - 1:
                    logger.warning(f"连接失败 ({e})，{base_delay * (2 ** retry_count)}秒后重试...")
                    continue
                else:
                    logger.error(f"连接失败，已达最大重试次数 {max_retries}: {url}: {e}")
                    return None
            except RequestException as e:
                # 其他请求异常（如HTTP错误），不重试
                logger.error(f"获取页面失败 {url}: {e}")
                return None
        
        return None
    
    def _extract_date_from_title(self, title: str):
        """
        从标题中提取发布日期
        
        Args:
            title: 报告标题
            
        Returns:
            str: 提取到的日期字符串（YYYY-MM-DD格式），如果提取失败则返回None
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
                    dt = datetime.strptime(date_str, date_format)
                    return dt.strftime('%Y-%m-%d')
                except (ValueError, AttributeError) as e:
                    logger.debug(f"日期解析失败: {date_str}, 格式: {date_format}, 错误: {e}")
                    continue
        
        return None
    
    def run_once(self, send_email: bool = True) -> Dict[str, int]:
        """
        执行单次监控检查（所有网站）
        
        Args:
            send_email: 是否发送邮件通知（默认True）
            
        Returns:
            Dict[str, int]: 每个网站发现的新报告数量
        """
        results = {}
        total_new_reports = 0
        
        for config in self.website_configs:
            logger.debug(f"检查网站: {config.name} ({config.url})")
            new_reports = self._check_single_website(config, send_email)
            results[config.name] = new_reports
            total_new_reports += new_reports
        
        logger.info(f"所有网站检查完成，共发现 {total_new_reports} 个新报告")
        return results
    
    def _check_single_website(self, config: WebsiteConfig, send_email: bool = True) -> int:
        """
        检查单个网站
        
        Args:
            config: 网站配置
            send_email: 是否发送邮件通知（默认True）
            
        Returns:
            int: 发现的新报告数量
        """
        new_reports_count = 0
        
        try:
            # 获取页面内容
            html_content = self._fetch_page(config.url)
            if not html_content:
                logger.warning(f"无法获取页面内容: {config.name}")
                return 0
            
            # 解析报告
            reports = config.get_reports(html_content, config.url)
            if not reports:
                logger.info(f"未找到报告: {config.name}")
                return 0
            
            logger.info(f"解析到 {len(reports)} 个报告: {config.name}")
            
            # 连接到数据库
            from db import DatabaseManager
            with DatabaseManager(self.db_path) as db:
                # 处理每个报告
                for report in reports:
                    title = report['title']
                    url = report['url']
                    source = report.get('source', config.name)
                    
                    # 插入数据库
                    # 尝试从标题中提取发布日期
                    publish_date = self._extract_date_from_title(title)
                    report_id = db.insert_report(
                        title=title,
                        url=url,
                        source_website=source,
                        publish_date=publish_date
                    )
                    
                    if report_id:
                        new_reports_count += 1
                        # 记录发现的新报告
                        logger.debug(f"发现新报告 [{config.name}]：{title} - {url}")
                        
                        # 发送邮件通知（如果启用且允许发送邮件）
                        if send_email and self.enable_email and self.email_sender:
                            try:
                                email_success = self.email_sender.send_report_notification(
                                    title=title,
                                    url=url,
                                    source_website=source
                                )
                                
                                if email_success:
                                    # 标记报告为已发送
                                    db.mark_report_as_sent(report_id)
                                    logger.info(f"邮件通知发送成功: {title}")
                                else:
                                    logger.warning(f"邮件通知发送失败: {title}")
                            except Exception as e:
                                logger.error(f"发送邮件通知时出错: {e}")
        
        except Exception as e:
            logger.error(f"检查网站 {config.name} 时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return new_reports_count
    
    def run_continuous(self, max_runs: int = None):
        """
        连续运行监控检查
        
        Args:
            max_runs: 最大运行次数（None表示无限运行）
        """
        run_count = 0
        
        logger.info("开始连续监控模式（多网站）")
        print(f"多网站监控已启动，监控 {len(self.website_configs)} 个网站")
        print(f"检查间隔: {self.check_interval_seconds/3600}小时")
        print("按 Ctrl+C 停止监控")
        print("-" * 50)
        
        try:
            while True:
                if max_runs is not None and run_count >= max_runs:
                    logger.info(f"已达到最大运行次数 {max_runs}，停止监控")
                    break
                
                run_count += 1
                logger.info(f"开始第 {run_count} 次监控检查（所有网站）")
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 第 {run_count} 次检查...")
                
                # 执行单次检查
                results = self.run_once(send_email=True)
                
                # 打印结果摘要
                total_new = sum(results.values())
                if total_new > 0:
                    print(f"本次检查发现 {total_new} 个新报告:")
                    for site_name, count in results.items():
                        if count > 0:
                            logger.debug(f"  {site_name}: {count} 个")
                else:
                    logger.debug("本次检查未发现新报告")
                
                # 如果不是最后一次运行，则等待
                if max_runs is None or run_count < max_runs:
                    next_check_time = datetime.now() + timedelta(seconds=self.check_interval_seconds)
                    logger.debug(f"下次检查时间: {next_check_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug(f"等待 {self.check_interval_seconds/3600:.1f} 小时...")
                    
                    # 等待间隔时间
                    self._wait_with_interrupt(self.check_interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("监控被用户中断")
            print("\n监控已停止")
        except Exception as e:
            logger.error(f"监控运行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            print(f"监控异常停止: {e}")
    
    def _wait_with_interrupt(self, seconds: int):
        """
        等待指定秒数，但允许被键盘中断
        
        Args:
            seconds: 等待秒数
        """
        try:
            interval = 10
            remaining = seconds
            
            while remaining > 0:
                sleep_time = min(interval, remaining)
                time.sleep(sleep_time)
                remaining -= sleep_time
                
                if remaining > 0 and remaining % 30 == 0:
                    mins_remaining = remaining // 60
                    secs_remaining = remaining % 60
                    logger.debug(f"等待中，剩余时间: {mins_remaining}分{secs_remaining}秒")
        
        except KeyboardInterrupt:
            logger.info("等待被用户中断")
            raise
    
    def show_statistics(self):
        """显示监控统计信息"""
        try:
            from db import DatabaseManager
            with DatabaseManager(self.db_path) as db:
                reports = db.get_all_reports()
                unsent_reports = db.get_unsent_reports()
                
                print("\n" + "=" * 50)
                print("多网站监控统计信息")
                print("=" * 50)
                print(f"数据库文件: {self.db_path}")
                print(f"监控网站数量: {len(self.website_configs)}")
                print(f"邮件通知: {'启用' if self.enable_email else '禁用'}")
                print("-" * 50)
                print(f"总报告数量: {len(reports)}")
                print(f"已发送报告: {len(reports) - len(unsent_reports)}")
                print(f"未发送报告: {len(unsent_reports)}")
                
                # 按网站统计
                site_stats = {}
                for report in reports:
                    site = report.get('source_website', '未知')
                    site_stats[site] = site_stats.get(site, 0) + 1
                
                if site_stats:
                    print("\n按网站统计:")
                    for site, count in sorted(site_stats.items()):
                        print(f"  {site}: {count} 个报告")
                
                if reports:
                    print("\n最近5个报告:")
                    for i, report in enumerate(reports[:5], 1):
                        sent_status = "✓" if report.get('sent_status') else "✗"
                        site = report.get('source_website', '未知')
                        print(f"{i}. [{sent_status}] [{site}] {report['title']}")
                        print(f"   链接: {report['url']}")
                        print(f"   发现时间: {report['discovered_time']}")
                        print()
                else:
                    print("\n数据库中暂无报告")
                
                print("=" * 50)
        
        except Exception as e:
            logger.error(f"显示统计信息失败: {e}")
    
    def send_unsent_reports(self) -> int:
        """
        发送数据库中未发送的报告
        
        Returns:
            int: 成功发送的报告数量
        """
        if not self.enable_email or not self.email_sender:
            logger.error("邮件通知功能未启用，无法发送未发送的报告")
            return 0
        
        try:
            from db import DatabaseManager
            with DatabaseManager(self.db_path) as db:
                unsent_reports = db.get_unsent_reports()
                
                if not unsent_reports:
                    logger.info("没有未发送的报告")
                    return 0
                
                logger.info(f"找到 {len(unsent_reports)} 个未发送的报告，开始发送邮件通知...")
                
                success_count = 0
                
                for report in unsent_reports:
                    title = report['title']
                    url = report['url']
                    source_website = report.get('source_website', '未知')
                    report_id = report['id']
                    
                    try:
                        email_success = self.email_sender.send_report_notification(
                            title=title,
                            url=url,
                            source_website=source_website
                        )
                        
                        if email_success:
                            db.mark_report_as_sent(report_id)
                            success_count += 1
                            logger.info(f"邮件通知发送成功: {title}")
                        else:
                            logger.warning(f"邮件通知发送失败: {title}")
                    except Exception as e:
                        logger.error(f"发送邮件通知时出错: {e}")
                
                logger.info(f"未发送报告处理完成: 成功 {success_count}/{len(unsent_reports)}")
                return success_count
                
        except Exception as e:
            logger.error(f"发送未发送报告时出错: {e}")
            return 0


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='网站报告监控工具')
    parser.add_argument('--url', default='https://concito.dk/en/analyser',
                       help='要监控的网站URL (默认: https://concito.dk/en/analyser)')
    parser.add_argument('--db', default='reports.db',
                       help='SQLite数据库文件路径 (默认: reports.db)')
    parser.add_argument('--interval', type=int, default=2,
                       help='检查间隔（小时） (默认: 2)')
    parser.add_argument('--runs', type=int, default=None,
                       help='最大运行次数（默认: 无限运行）')
    parser.add_argument('--once', action='store_true',
                       help='仅运行一次检查')
    parser.add_argument('--stats', action='store_true',
                       help='显示统计信息并退出')
    parser.add_argument('--test', action='store_true',
                       help='测试模式：运行一次检查并显示结果')
    
    # 邮件通知相关参数
    parser.add_argument('--no-email', action='store_true',
                       help='禁用邮件通知功能')
    parser.add_argument('--smtp-server',
                       help='SMTP服务器地址 (默认: smtp.office365.com)')
    parser.add_argument('--smtp-port', type=int,
                       help='SMTP端口 (默认: 587)')
    parser.add_argument('--sender-email',
                       help='发件人邮箱地址')
    parser.add_argument('--sender-password',
                       help='发件人SMTP授权码')
    parser.add_argument('--recipient-emails', nargs='+',
                       help='收件人邮箱地址列表 (多个用空格分隔)')
    parser.add_argument('--send-unsent', action='store_true',
                       help='发送数据库中未发送的历史报告')
    parser.add_argument('--multi', action='store_true',
                       help='启用多网站监控模式（默认监控CONCITO、WWF、EEB）')
    
    args = parser.parse_args()
    
    # 创建监控器
    if args.multi:
        # 多网站监控模式
        from website_configs import get_all_websites
        website_configs = get_all_websites()
        monitor = MultiWebsiteMonitor(
            website_configs=website_configs,
            db_path=args.db,
            check_interval_hours=args.interval,
            enable_email=not args.no_email,
            smtp_server=args.smtp_server,
            smtp_port=args.smtp_port,
            sender_email=args.sender_email,
            sender_password=args.sender_password,
            recipient_emails=args.recipient_emails
        )
    else:
        # 单网站监控模式（向后兼容）
        monitor = WebsiteMonitor(
            target_url=args.url,
            db_path=args.db,
            check_interval_hours=args.interval,
            enable_email=not args.no_email,
            smtp_server=args.smtp_server,
            smtp_port=args.smtp_port,
            sender_email=args.sender_email,
            sender_password=args.sender_password,
            recipient_emails=args.recipient_emails
        )
    
    try:
        # 处理发送未发送报告请求
        if args.send_unsent:
            print("发送未发送的历史报告...")
            success_count = monitor.send_unsent_reports()
            print(f"\n未发送报告处理完成: 成功发送 {success_count} 个报告")
            sys.exit(0)
        
        if args.stats:
            # 显示统计信息
            monitor.show_statistics()
        
        elif args.test:
            # 测试模式
            print("测试模式：运行单次检查")
            new_reports = monitor.run_once()
            print(f"\n测试完成，发现 {new_reports} 个新报告")
            
            if new_reports > 0:
                print("\n数据库统计:")
                monitor.show_statistics()
        
        elif args.once:
            # 单次运行模式
            print("单次运行模式")
            new_reports = monitor.run_once()
            print(f"\n运行完成，发现 {new_reports} 个新报告")
        
        else:
            # 连续运行模式
            monitor.run_continuous(max_runs=args.runs)
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()