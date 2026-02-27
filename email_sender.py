#!/usr/bin/env python3
"""
邮件发送模块
用于发送新报告的通知邮件

使用Outlook SMTP服务器，支持其他主流邮箱服务商

配置方式：
1. 通过环境变量（推荐）：
   - SMTP_SERVER: SMTP服务器地址（默认：smtp.office365.com）
   - SMTP_PORT: SMTP端口（默认：587）
   - SENDER_EMAIL: 发件人邮箱
   - SENDER_PASSWORD: 发件人SMTP授权码
   - RECIPIENT_EMAILS: 收件人邮箱，多个用逗号分隔

2. 修改类属性（不推荐）：
   直接修改EmailSender类中的SMTP_SERVER、SENDER_EMAIL等属性

注意：对于Outlook邮箱，需要在账户设置中启用SMTP并生成授权码
"""

import logging
import smtplib
import ssl
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)

# 自动加载 .env 文件中的环境变量（如果存在）
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 解析键值对
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 去除值两侧的引号
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    # 设置环境变量（如果尚未设置）
                    if key and key not in os.environ:
                        os.environ[key] = value
                        logger.debug(f"从 .env 文件加载环境变量: {key}")
    except Exception as e:
        logger.warning(f"加载 .env 文件失败: {e}")

class EmailSender:
    """邮件发送器类"""
    
    # SMTP配置 - 优先使用环境变量，没有则使用安全默认值
    # 邮件服务器配置
    SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.office365.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    
    # 发件人配置 - 必须通过环境变量设置
    SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
    SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
    
    # 收件人配置 - 可以配置多个收件人，用逗号分隔
    DEFAULT_RECIPIENT_EMAILS = os.environ.get("RECIPIENT_EMAILS", "")
    RECIPIENT_EMAILS = [email.strip() for email in DEFAULT_RECIPIENT_EMAILS.split(",") if email.strip()] if DEFAULT_RECIPIENT_EMAILS else []
    
    # 邮件主题前缀
    EMAIL_SUBJECT_PREFIX = "【新报告监控】"
    
    def __init__(self, smtp_server: str = None, smtp_port: int = None,
                 sender_email: str = None, sender_password: str = None,
                 recipient_emails: List[str] = None):
        """
        初始化邮件发送器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender_email: 发件人邮箱
            sender_password: 发件人密码/授权码
            recipient_emails: 收件人邮箱列表
        """
        self.smtp_server = smtp_server or self.SMTP_SERVER
        self.smtp_port = smtp_port or self.SMTP_PORT
        self.sender_email = sender_email or self.SENDER_EMAIL
        self.sender_password = sender_password or self.SENDER_PASSWORD
        self.recipient_emails = recipient_emails or self.RECIPIENT_EMAILS
        
        # 验证必要的配置
        self._validate_config()
        
        logger.info(f"邮件发送器初始化完成")
        logger.info(f"SMTP服务器: {self.smtp_server}:{self.smtp_port}")
        logger.info(f"发件人: {self.sender_email}")
        logger.info(f"收件人: {self.recipient_emails}")
    
    def send_report_notification(self, title: str, url: str, source_website: str) -> bool:
        """
        发送报告通知邮件
        
        Args:
            title: 报告标题
            url: 报告链接
            source_website: 来源网站
            
        Returns:
            bool: 发送是否成功
        """
        # 检查收件人配置
        if not self.recipient_emails:
            logger.error("无法发送邮件：收件人邮箱列表为空")
            logger.error("请通过环境变量 RECIPIENT_EMAILS 设置收件人邮箱")
            return False
        
        # 检查发件人配置
        if not self.sender_email or not self.sender_password:
            logger.error("无法发送邮件：发件人邮箱或SMTP授权码未设置")
            logger.error("请通过环境变量 SENDER_EMAIL 和 SENDER_PASSWORD 设置发件人信息")
            return False
        
        # 构建邮件内容
        subject = f"{self.EMAIL_SUBJECT_PREFIX}来自{source_website}的新发布"
        
        # 邮件正文格式
        body = f"""【新报告监控】来自{source_website}的新发布

标题：{title}
链接：{url}

发现时间：{self._get_current_time()}

---
此邮件由网站监控工具自动发送
"""
        
        try:
            # 创建邮件消息
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = ", ".join(self.recipient_emails)
            message["Subject"] = subject
            
            # 添加正文
            message.attach(MIMEText(body, "plain", "utf-8"))
            
            # 连接SMTP服务器并发送
            success = self._send_email(message)
            
            if success:
                logger.info(f"邮件发送成功: {title}")
                return True
            else:
                logger.error(f"邮件发送失败: {title}")
                return False
                
        except Exception as e:
            logger.error(f"构建或发送邮件失败: {e}")
            return False
    
    def send_batch_notifications(self, reports: List[Dict[str, str]]) -> int:
        """
        批量发送报告通知邮件
        
        Args:
            reports: 报告列表，每个报告包含'title', 'url', 'source_website'键
            
        Returns:
            int: 成功发送的邮件数量
        """
        # 检查邮件配置
        if not self.recipient_emails:
            logger.error("无法发送邮件：收件人邮箱列表为空")
            logger.error("请通过环境变量 RECIPIENT_EMAILS 设置收件人邮箱")
            return 0
        
        if not self.sender_email or not self.sender_password:
            logger.error("无法发送邮件：发件人邮箱或SMTP授权码未设置")
            logger.error("请通过环境变量 SENDER_EMAIL 和 SENDER_PASSWORD 设置发件人信息")
            return 0
        
        if not reports:
            logger.info("没有需要发送的报告")
            return 0
        
        success_count = 0
        
        # 如果是多个报告，可以合并为一封邮件
        if len(reports) > 1:
            success = self._send_combined_notification(reports)
            if success:
                success_count = len(reports)
        else:
            # 单个报告单独发送
            for report in reports:
                success = self.send_report_notification(
                    title=report['title'],
                    url=report['url'],
                    source_website=report.get('source_website', '未知来源')
                )
                if success:
                    success_count += 1
        
        logger.info(f"批量发送完成: 成功 {success_count}/{len(reports)}")
        return success_count
    
    def _send_combined_notification(self, reports: List[Dict[str, str]]) -> bool:
        """
        发送合并通知邮件（多个报告在一封邮件中）
        
        Args:
            reports: 报告列表
            
        Returns:
            bool: 发送是否成功
        """
        if not reports:
            return False
        
        # 使用第一个报告的来源网站
        source_website = reports[0].get('source_website', '未知来源')
        
        subject = f"{self.EMAIL_SUBJECT_PREFIX}来自{source_website}的{len(reports)}个新发布"
        
        # 构建合并邮件正文
        body_lines = [f"【新报告监控】来自{source_website}的{len(reports)}个新发布", "", "报告列表："]
        
        for i, report in enumerate(reports, 1):
            body_lines.append(f"{i}. {report['title']}")
            body_lines.append(f"   链接：{report['url']}")
            body_lines.append("")
        
        body_lines.append(f"发现时间：{self._get_current_time()}")
        body_lines.append("")
        body_lines.append("---")
        body_lines.append("此邮件由网站监控工具自动发送")
        
        body = "\n".join(body_lines)
        
        try:
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = ", ".join(self.recipient_emails)
            message["Subject"] = subject
            
            message.attach(MIMEText(body, "plain", "utf-8"))
            
            success = self._send_email(message)
            
            if success:
                logger.info(f"合并邮件发送成功: {len(reports)}个报告")
            else:
                logger.error(f"合并邮件发送失败: {len(reports)}个报告")
                
            return success
            
        except Exception as e:
            logger.error(f"构建或发送合并邮件失败: {e}")
            return False
    
    def _send_email(self, message: MIMEMultipart) -> bool:
        """
        实际发送邮件
        
        Args:
            message: 邮件消息对象
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 创建安全SSL/TLS上下文
            context = ssl.create_default_context()
            
            # 设置超时（秒）
            timeout_seconds = 30
            
            # 根据端口选择连接方式（与test_connection保持一致）
            if self.smtp_port == 465:
                # SSL端口（163邮箱等）
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=timeout_seconds, context=context) as server:
                    server.ehlo()  # 向服务器标识自己
                    # SSL连接不需要starttls
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(message)
            else:
                # 普通TLS端口（587等，Outlook/Gmail/QQ邮箱）
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout_seconds) as server:
                    server.ehlo()  # 向服务器标识自己
                    server.starttls(context=context)  # 启用TLS加密
                    server.ehlo()  # 再次向服务器标识自己（TLS模式）
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(message)
                
            logger.debug("邮件发送成功")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP认证失败: {e}")
            logger.error("请检查发件邮箱和SMTP授权码是否正确")
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP服务器断开连接: {e}")
            logger.error("可能原因: 服务器主动断开、TLS/SSL协商失败、端口错误")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP错误: {e}")
            return False
        except socket.timeout as e:
            error_msg = f"SMTP连接超时: {str(e)}。可能原因: 网络慢、防火墙阻止、服务器无响应。"
            logger.error(error_msg)
            return False
        except ConnectionRefusedError as e:
            error_msg = f"连接被拒绝: {str(e)}。可能原因: 端口错误、SMTP服务器未运行、防火墙阻止。"
            logger.error(error_msg)
            return False
        except socket.error as e:
            # 处理socket层面错误，包括"Network is unreachable"
            error_msg = f"网络连接错误: {str(e)}。可能原因: 网络不可达、DNS解析失败、防火墙阻止、PythonAnywhere端口限制。"
            logger.error(error_msg)
            return False
        except OSError as e:
            # 处理操作系统层面错误
            error_msg = f"操作系统错误: {str(e)}。可能原因: 网络配置问题、权限问题、资源限制。"
            logger.error(error_msg)
            return False
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return False
    
    def _validate_config(self):
        """
        验证邮件配置是否完整
        
        检查必要的环境变量是否设置，如果未设置则记录警告。
        注意：这里只记录警告，不抛出异常，因为配置可能在后续通过其他方式设置。
        """
        missing_configs = []
        
        # 检查发件人配置
        if not self.sender_email:
            missing_configs.append("SENDER_EMAIL")
            logger.warning("发件人邮箱未设置，请通过环境变量 SENDER_EMAIL 设置")
            
        if not self.sender_password:
            missing_configs.append("SENDER_PASSWORD")
            logger.warning("发件人SMTP授权码未设置，请通过环境变量 SENDER_PASSWORD 设置")
        
        # 检查收件人配置
        if not self.recipient_emails:
            missing_configs.append("RECIPIENT_EMAILS")
            logger.warning("收件人邮箱未设置，邮件将无法发送。请通过环境变量 RECIPIENT_EMAILS 设置")
        
        # 检查SMTP服务器配置
        if not self.smtp_server:
            missing_configs.append("SMTP_SERVER")
            logger.warning("SMTP服务器地址未设置，使用默认值: smtp.office365.com")
            self.smtp_server = "smtp.office365.com"
        
        if not self.smtp_port:
            missing_configs.append("SMTP_PORT")
            logger.warning("SMTP端口未设置，使用默认值: 587")
            self.smtp_port = 587
        
        if missing_configs:
            logger.warning(f"缺少以下配置项: {', '.join(missing_configs)}")
            logger.warning("可以通过以下方式设置:")
            logger.warning("1. 设置环境变量 (推荐):")
            logger.warning("   export SENDER_EMAIL='your_email@example.com'")
            logger.warning("   export SENDER_PASSWORD='your_smtp_password'")
            logger.warning("   export RECIPIENT_EMAILS='recipient1@example.com,recipient2@example.com'")
            logger.warning("2. 在创建EmailSender实例时传递参数")
            logger.warning("3. 创建.env文件并在其中设置环境变量")
        else:
            logger.debug("邮件配置验证通过")
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def test_connection(self) -> tuple[bool, str]:
        """
        测试SMTP连接
        
        Returns:
            tuple[bool, str]: (连接是否成功, 错误信息或空字符串)
        """
        # 检查必要的配置
        if not self.sender_email or not self.sender_password:
            error_msg = "无法测试SMTP连接：发件人邮箱或SMTP授权码未设置。请通过环境变量 SENDER_EMAIL 和 SENDER_PASSWORD 设置发件人信息。"
            logger.error(error_msg)
            return False, error_msg
        
        if not self.smtp_server:
            error_msg = "无法测试SMTP连接：SMTP服务器地址未设置。请通过环境变量 SMTP_SERVER 设置SMTP服务器地址。"
            logger.error(error_msg)
            return False, error_msg
        
        try:
            context = ssl.create_default_context()
            
            # 设置超时（秒）
            timeout_seconds = 30
            
            # 根据端口选择连接方式
            if self.smtp_port == 465:
                # SSL端口
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=timeout_seconds, context=context) as server:
                    server.ehlo()
                    # SSL连接不需要starttls
                    server.login(self.sender_email, self.sender_password)
            else:
                # 普通端口（587等）
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout_seconds) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.sender_email, self.sender_password)
                
            logger.info("SMTP连接测试成功")
            return True, ""
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP认证测试失败: {str(e)}。请检查邮箱 {self.sender_email} 和授权码是否正确。"
            logger.error(error_msg)
            return False, error_msg
        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"SMTP服务器断开连接: {str(e)}。可能原因: 服务器主动断开、TLS协商失败、端口错误。"
            logger.error(error_msg)
            return False, error_msg
        except socket.timeout as e:
            error_msg = f"SMTP连接超时: {str(e)}。可能原因: 网络慢、防火墙阻止、服务器无响应。"
            logger.error(error_msg)
            return False, error_msg
        except ConnectionRefusedError as e:
            error_msg = f"连接被拒绝: {str(e)}。可能原因: 端口错误、SMTP服务器未运行、防火墙阻止。"
            logger.error(error_msg)
            return False, error_msg
        except socket.error as e:
            # 处理socket层面错误，包括"Network is unreachable"
            error_msg = f"网络连接错误: {str(e)}。可能原因: 网络不可达、DNS解析失败、防火墙阻止、PythonAnywhere端口限制。"
            logger.error(error_msg)
            return False, error_msg
        except OSError as e:
            # 处理操作系统层面错误
            error_msg = f"操作系统错误: {str(e)}。可能原因: 网络配置问题、权限问题、资源限制。"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"SMTP连接测试失败: {str(e)}。请检查SMTP配置: {self.smtp_server}:{self.smtp_port}。"
            logger.error(error_msg)
            return False, error_msg


def get_smtp_config_instructions():
    """获取SMTP配置说明"""
    instructions = """
    ================================================
    SMTP配置说明（包含Outlook认证问题解决方案）
    ================================================
    
    重要提示：如果您遇到"basic authentication is disabled"错误，请参考下面的解决方案！
    
    1. Outlook邮箱配置（可能遇到认证问题）：
       - SMTP服务器: smtp.office365.com
       - 端口: 587
       - 加密方式: TLS
       - 常见问题: "535 5.7.139 Authentication unsuccessful, basic authentication is disabled"
    
    2. 163邮箱配置（推荐，认证简单）：
       - SMTP服务器: smtp.163.com
       - 端口: 465 (SSL) 或 994 (SSL)
       - 加密方式: SSL
    
    3. QQ邮箱配置（推荐，认证简单）：
       - SMTP服务器: smtp.qq.com
       - 端口: 465 (SSL) 或 587 (TLS)
       - 加密方式: SSL/TLS
    
    ================================================
    【Outlook认证问题解决方案】
    ================================================
    
    如果您遇到"basic authentication is disabled"错误，请按以下步骤解决：
    
    方案A：启用SMTP AUTH（推荐）
    ------------------------------------
    1. 登录Outlook网页版 (outlook.live.com)
    2. 点击右上角设置图标 → "查看所有Outlook设置"
    3. 选择"邮件" → "同步电子邮件"
    4. 点击"POP和IMAP"
    5. 确保以下选项已启用：
       - POP选项: 选择"是"
       - IMAP: 选择"是"
    6. 点击"保存"
    7. 可能需要启用"两步验证"并生成"应用密码"
    
    方案B：生成应用密码（如果已启用两步验证）
    ------------------------------------
    1. 登录Microsoft账户安全页面: https://account.microsoft.com/security
    2. 启用"两步验证"（如果未启用）
    3. 在"应用密码"部分，生成新的应用密码
    4. 在.env文件中使用这个应用密码，而不是邮箱登录密码
    
    方案C：更换为163/QQ邮箱（最简单）
    ------------------------------------
    1. 注册163或QQ邮箱（如果没有）
    2. 在邮箱设置中开启SMTP服务
    3. 获取SMTP授权码
    4. 修改.env文件中的配置：
        SMTP_SERVER=smtp.163.com   # 或 smtp.qq.com
        SMTP_PORT=465              # 163邮箱用465，QQ邮箱用465或587
        SENDER_EMAIL=您的163/QQ邮箱
        SENDER_PASSWORD=您的SMTP授权码
    
    ================================================
    如何获取SMTP授权码：
    ================================================
    
    A. Outlook邮箱：
       1. 参考上面的"方案A"和"方案B"
       2. 注意：Outlook可能已禁用基本认证，需要应用密码
    
    B. 163邮箱：
       1. 登录163邮箱
       2. 进入"设置" → "POP3/SMTP/IMAP"
       3. 开启"SMTP服务"
       4. 根据提示获取授权码（16位字母数字组合）
    
    C. QQ邮箱：
       1. 登录QQ邮箱
       2. 进入"设置" → "账户"
       3. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
       4. 开启"SMTP服务"
       5. 点击"生成授权码"，获取16位授权码
    
    ================================================
    配置步骤（推荐使用.env文件）：
    ================================================
    
    1. 编辑 .env 文件（如果不存在，复制 .env.example 为 .env）：
    
       推荐使用163邮箱配置示例：
         SMTP_SERVER=smtp.163.com
         SMTP_PORT=465
         SENDER_EMAIL=您的163邮箱@163.com
         SENDER_PASSWORD=您的163邮箱SMTP授权码
         RECIPIENT_EMAILS=收件人邮箱@example.com
    
       或使用QQ邮箱配置示例：
         SMTP_SERVER=smtp.qq.com
         SMTP_PORT=465
         SENDER_EMAIL=您的QQ邮箱@qq.com
         SENDER_PASSWORD=您的QQ邮箱SMTP授权码
         RECIPIENT_EMAILS=收件人邮箱@example.com
    
    2. 运行测试：
         python email_sender.py --test          # 测试SMTP连接
         python email_sender.py --send-test     # 发送测试邮件
    
    3. 启动Web界面：
         python app.py
         或运行 start_web.bat (Windows) / start_web.sh (Linux/macOS)
    
    ================================================
    重要提醒：
    ================================================
    1. 授权码 ≠ 邮箱登录密码！必须通过邮箱服务商获取
    2. 请勿将真实的 .env 文件提交到Git！.gitignore 已包含 .env
    3. 如果Outlook认证持续失败，建议更换为163/QQ邮箱
    4. 确保防火墙允许连接到SMTP端口（465或587）
    
    ================================================
    """
    return instructions


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='邮件发送测试工具')
    parser.add_argument('--test', action='store_true',
                       help='测试SMTP连接')
    parser.add_argument('--send-test', action='store_true',
                       help='发送测试邮件')
    parser.add_argument('--instructions', action='store_true',
                       help='显示SMTP配置说明')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    if args.instructions:
        print(get_smtp_config_instructions())
    
    elif args.test:
        print("测试SMTP连接...")
        sender = EmailSender()
        if sender.test_connection():
            print("SMTP连接测试成功！")
        else:
            print("SMTP连接测试失败，请检查配置。")
            print("\n配置说明：")
            print(get_smtp_config_instructions())
    
    elif args.send_test:
        print("发送测试邮件...")
        sender = EmailSender()
        
        # 发送测试邮件
        success = sender.send_report_notification(
            title="测试报告标题",
            url="https://example.com/test-report",
            source_website="concito.dk"
        )
        
        if success:
            print("测试邮件发送成功！")
        else:
            print("测试邮件发送失败，请检查配置。")
            print("\n配置说明：")
            print(get_smtp_config_instructions())
    
    else:
        print("请使用以下选项：")
        print("  --test         测试SMTP连接")
        print("  --send-test    发送测试邮件")
        print("  --instructions 显示SMTP配置说明")
        print("\n首次使用时，请先运行：")
        print("  python email_sender.py --instructions")
        print("  python email_sender.py --test")