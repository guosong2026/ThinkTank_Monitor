"""
网页抓取和解析模块
从目标网站提取报告标题和链接
"""

import logging
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

# 禁用SSL警告（在使用代理或自签名证书时）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class WebsiteScraper:
    """网站抓取器类"""
    
    def __init__(self, base_url: str, user_agent: Optional[str] = None, proxy: Optional[str] = None):
        """
        初始化网站抓取器
        
        Args:
            base_url: 目标网站基础URL
            user_agent: 用户代理字符串（可选）
            proxy: 代理服务器URL，例如 'http://proxy.example.com:8080'（可选）
        """
        self.base_url = base_url
        self.session = requests.Session()
        # 不自动使用环境变量中的代理配置，避免代理连接失败
        self.session.trust_env = False
        
        # 设置请求头
        headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session.headers.update(headers)
        
        # 设置代理
        self.proxy = proxy
        if not self.proxy:
            # 尝试从环境变量读取代理配置
            import os
            self.proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('https_proxy') or os.environ.get('http_proxy')
        
        if self.proxy:
            logger.info(f"使用代理: {self.proxy}")
        else:
            logger.info("未配置代理")
    
    def fetch_page(self, url: str) -> Optional[str]:
        """
        获取网页内容
        
        Args:
            url: 要获取的URL
            
        Returns:
            str: 网页HTML内容，失败时返回None
            
        Raises:
            requests.RequestException: 网络请求错误
        """
        import time
        from requests.exceptions import ConnectionError, Timeout
        
        max_retries = 3
        base_delay = 2  # 初始延迟秒数
        
        for retry_count in range(max_retries):
            try:
                if retry_count > 0:
                    logger.info(f"第 {retry_count + 1} 次重试获取页面: {url}")
                    # 指数退避延迟
                    delay = base_delay * (2 ** (retry_count - 1))
                    time.sleep(delay)
                else:
                    logger.info(f"正在获取页面: {url}")
                
                # 准备代理配置
                proxies = None
                if self.proxy:
                    proxies = {
                        'http': self.proxy,
                        'https': self.proxy
                    }
                
                # 分别设置连接超时和读取超时：连接超时15秒，读取超时45秒
                response = self.session.get(url, timeout=(15, 45), proxies=proxies, verify=False)
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    logger.warning(f"返回的内容类型不是HTML: {content_type}")
                
                return response.text
                
            except requests.exceptions.ProxyError as e:
                # 代理连接失败，尝试不使用代理
                logger.warning(f"代理连接失败 ({e})，尝试不使用代理...")
                try:
                    response = self.session.get(url, timeout=(15, 45), proxies={'http': None, 'https': None}, verify=False)
                    response.raise_for_status()
                    return response.text
                except requests.exceptions.RequestException as retry_e:
                    logger.error(f"不使用代理重试也失败: {retry_e}")
                    # 继续外层循环进行重试
                    if retry_count < max_retries - 1:
                        continue
                    else:
                        return None
            except (ConnectionError, Timeout) as e:
                # 连接错误或超时，进行重试
                if retry_count < max_retries - 1:
                    logger.warning(f"连接失败 ({e})，{base_delay * (2 ** retry_count)}秒后重试...")
                    continue
                else:
                    logger.error(f"连接失败，已达最大重试次数 {max_retries}: {url}: {e}")
                    return None
            except requests.exceptions.HTTPError as e:
                # HTTP错误（如404, 403），不重试
                logger.error(f"HTTP错误 {e.response.status_code}: {url}")
                return None
            except requests.exceptions.RequestException as e:
                # 其他请求异常，不重试
                logger.error(f"请求失败: {e}")
                return None
        
        return None
    
    def extract_reports(self, html_content: str) -> List[Dict[str, str]]:
        """
        从HTML内容中提取报告列表
        
        Args:
            html_content: HTML内容
            
        Returns:
            List[Dict[str, str]]: 报告字典列表，每个字典包含'title'和'url'键
        """
        if not html_content:
            return []
        
        reports = []
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 尝试多种选择器来查找报告链接
        # 这些选择器需要根据实际网站结构调整
        
        # 选择器1：查找所有文章链接
        article_selectors = [
            'article a',  # 文章内的链接
            '.publication a',  # 出版物类
            '.report a',  # 报告类
            '.analyser a',  # 分析类
            'h3 a',  # 标题链接
            'h2 a',  # 二级标题链接
            '.entry-title a',  # 文章标题链接
            '.post-title a',  # 帖子标题链接
        ]
        
        for selector in article_selectors:
            links = soup.select(selector)
            if links:
                logger.info(f"使用选择器 '{selector}' 找到 {len(links)} 个链接")
                for link in links:
                    title = self._clean_title(link.text.strip())
                    href = link.get('href', '')
                    
                    if href and title:
                        # 构建完整URL
                        full_url = urljoin(self.base_url, href)
                        
                        # 检查是否是报告链接（可根据需要调整条件）
                        if self._is_report_link(full_url, title):
                            reports.append({
                                'title': title,
                                'url': full_url
                            })
                break
        
        # 如果上述选择器都没找到，尝试查找所有可能包含报告的链接
        if not reports:
            logger.warning("未找到报告链接，尝试通用方法")
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                title = self._clean_title(link.text.strip())
                href = link['href']
                
                if href and title and len(title) > 10:  # 标题长度阈值
                    full_url = urljoin(self.base_url, href)
                    if self._is_report_link(full_url, title):
                        reports.append({
                            'title': title,
                            'url': full_url
                        })
        
        # 去重
        unique_reports = []
        seen_urls = set()
        for report in reports:
            if report['url'] not in seen_urls:
                seen_urls.add(report['url'])
                unique_reports.append(report)
        
        logger.info(f"共提取到 {len(unique_reports)} 个唯一报告")
        return unique_reports
    
    def _clean_title(self, title: str) -> str:
        """
        清理标题文本
        
        Args:
            title: 原始标题
            
        Returns:
            str: 清理后的标题
        """
        if not title:
            return ""
            
        # 移除多余空白字符
        title = ' '.join(title.split())
        
        # 定义常见非标题文本模式（如果标题匹配这些模式，则返回空字符串）
        non_title_patterns = [
            r'^\s*read\s+more(\s+»)?\s*$',  # "read more" 或 "read more »"
            r'^\s*read\s*$',                # "read"
            r'^\s*more\s*$',                # "more"
            r'^\s*next\s+page\s*$',         # "next page"
            r'^\s*previous\s+page\s*$',     # "previous page"
            r'^\s*page\s+\d+\s*$',          # "page 1", "page 2", 等等
            r'^\s*click\s+here\s*$',        # "click here"
            r'^\s*learn\s+more\s*$',        # "learn more"
            r'^\s*continue\s+reading\s*$',  # "continue reading"
            r'^\s*download\s*$',            # "download"
            r'^\s*print\s*$',               # "print"
            r'^\s*share\s*$',               # "share"
            r'^\s*email\s*$',               # "email"
            r'^\s*comment\s*$',             # "comment"
            r'^\s*follow\s+us\s*$',         # "follow us"
        ]
        
        import re
        title_lower = title.lower()
        for pattern in non_title_patterns:
            if re.match(pattern, title_lower):
                return ""  # 返回空字符串，表示这不是有效标题
        
        # 移除常见前缀
        prefixes = ['Read more', 'Read', 'Download', 'PDF', '»', '›', 'Continue reading', 'Learn more']
        for prefix in prefixes:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
        
        # 移除常见后缀
        suffixes = ['»', '›', '...', 'read more', 'read more »', 'learn more']
        for suffix in suffixes:
            if title.lower().endswith(suffix.lower()):
                # 移除后缀并清理
                title = title[:len(title)-len(suffix)].strip()
        
        # 如果清理后标题太短（少于10个字符），可能不是有效标题
        if len(title) < 10:
            # 检查是否包含明显的文章标题词汇
            article_indicators = ['report', 'study', 'research', 'analysis', 'article', 
                                'publication', 'press release', 'news', 'blog', 'paper',
                                'policy', 'brief', 'insight', 'perspective', 'commentary']
            has_indicator = any(indicator in title.lower() for indicator in article_indicators)
            if not has_indicator:
                return ""  # 太短且不包含文章指示词，可能不是有效标题
        
        return title
    
    def _is_report_link(self, url: str, title: str) -> bool:
        """
        判断链接是否是报告链接
        
        Args:
            url: 链接URL
            title: 链接标题
            
        Returns:
            bool: 是否是报告链接
        """
        # 排除常见非报告链接
        exclude_keywords = [
            'home', 'about', 'contact', 'privacy', 'terms', 'login',
            'signup', 'subscribe', 'twitter', 'facebook', 'linkedin',
            'instagram', 'youtube', 'rss', 'feed', 'search', 'donate',
            'careers', 'press', 'media', 'newsletter', 'cookie',
            'next page', 'previous page', 'page', 'next', 'previous',
            'privacy notice', 'privacy policy', 'terms of use',
            'our research culture', 'read more', 'read more »', 'read',
            'more', 'continue reading', 'learn more', 'click here',
            'download', 'share', 'print', 'email', 'comment',
            'authors', 'authorship', 'follow us', 'follow',
            'sign up', 'sign in', 'log in', 'register'
        ]
        
        url_lower = url.lower()
        title_lower = title.lower()
        
        # 检查是否包含排除关键词
        for keyword in exclude_keywords:
            if keyword in url_lower or keyword in title_lower:
                return False
        
        # 检查URL是否可能是报告链接（可根据需要调整）
        report_indicators = [
            '/analyser/', '/publication/', '/report/', '/study/', 
            '/research/', '/article/', '/blog/', '/analysis/',
            '.pdf'  # PDF文件
        ]
        
        for indicator in report_indicators:
            if indicator in url_lower:
                return True
        
        # 如果标题有一定长度且URL看起来不是导航链接
        if len(title) > 20 and not url_lower.endswith(('.jpg', '.png', '.gif', '.css', '.js')):
            return True
        
        return False
    
    def scrape_reports(self) -> List[Dict[str, str]]:
        """
        执行完整的抓取流程
        
        Returns:
            List[Dict[str, str]]: 提取的报告列表
        """
        logger.info(f"开始抓取网站: {self.base_url}")
        
        html_content = self.fetch_page(self.base_url)
        if not html_content:
            logger.error("无法获取网页内容")
            return []
        
        reports = self.extract_reports(html_content)
        
        if reports:
            logger.info(f"成功提取 {len(reports)} 个报告")
            for i, report in enumerate(reports[:5], 1):  # 只显示前5个
                logger.debug(f"报告 {i}: {report['title']} - {report['url']}")
        else:
            logger.warning("未提取到任何报告")
        
        return reports
    
    def close(self):
        """关闭会话"""
        self.session.close()
        logger.debug("HTTP会话已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


if __name__ == "__main__":
    # 测试抓取功能
    import sys
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        with WebsiteScraper("https://concito.dk/en/analyser") as scraper:
            reports = scraper.scrape_reports()
            
            if reports:
                print(f"成功抓取到 {len(reports)} 个报告:")
                for i, report in enumerate(reports, 1):
                    print(f"{i}. {report['title']}")
                    print(f"   链接: {report['url']}")
                    print()
            else:
                print("未抓取到任何报告")
                
    except Exception as e:
        print(f"抓取测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)