"""
网站配置模块
定义要监控的网站及其解析规则
"""

from typing import List, Dict, Callable, Optional
from urllib.parse import urljoin


# ============================================================================
# 网站配置基类
# ============================================================================

class WebsiteConfig:
    """网站配置基类"""
    
    def __init__(self, name: str, url: str, parser_func: Callable = None):
        """
        初始化网站配置
        
        Args:
            name: 网站名称（用于标识）
            url: 监控的URL
            parser_func: 自定义解析函数（可选）
        """
        self.name = name
        self.url = url
        self.parser_func = parser_func
    
    def get_reports(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """
        从HTML内容中提取报告
        
        Args:
            html_content: HTML内容
            base_url: 基础URL（用于构建完整链接）
            
        Returns:
            List[Dict[str, str]]: 报告列表，每个报告包含'title'和'url'
        """
        if self.parser_func:
            return self.parser_func(html_content, base_url)
        else:
            return self._default_parser(html_content, base_url)
    
    def _default_parser(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """
        默认解析器（通用解析逻辑）
        
        Args:
            html_content: HTML内容
            base_url: 基础URL
            
        Returns:
            List[Dict[str, str]]: 报告列表
        """
        from bs4 import BeautifulSoup
        
        if not html_content:
            return []
        
        reports = []
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 通用选择器
        selectors = [
            'article a', '.news-item a', '.press-release a',
            '.publication a', '.report a', '.library-item a',
            'h3 a', 'h2 a', '.title a', '.entry-title a',
            '.post-title a', '.news-title a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            if links:
                for link in links:
                    title = self._clean_title(link.text.strip())
                    href = link.get('href', '')
                    
                    if href and title:
                        full_url = urljoin(base_url, href)
                        if self._is_report_link(full_url, title):
                            reports.append({
                                'title': title,
                                'url': full_url,
                                'source': self.name
                            })
                break
        
        # 如果没有找到，尝试通用方法
        if not reports:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                title = self._clean_title(link.text.strip())
                href = link['href']
                
                if href and title and len(title) > 10:
                    full_url = urljoin(base_url, href)
                    if self._is_report_link(full_url, title):
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': self.name
                        })
        
        # 去重
        unique_reports = []
        seen_urls = set()
        for report in reports:
            if report['url'] not in seen_urls:
                seen_urls.add(report['url'])
                unique_reports.append(report)
        
        return unique_reports
    
    def _clean_title(self, title: str) -> str:
        """清理标题文本"""
        title = ' '.join(title.split())
        
        # 移除常见前缀/后缀
        prefixes = ['Read more', 'Read', 'Download', 'PDF', '»', '›']
        for prefix in prefixes:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
        
        return title
    
    def _is_report_link(self, url: str, title: str) -> bool:
        """判断链接是否是报告链接"""
        exclude_keywords = [
            'home', 'about', 'contact', 'privacy', 'terms', 'login',
            'signup', 'subscribe', 'twitter', 'facebook', 'linkedin',
            'instagram', 'youtube', 'rss', 'feed', 'search', 'donate',
            'careers', 'press', 'media', 'newsletter', 'cookie'
        ]
        
        url_lower = url.lower()
        title_lower = title.lower()
        
        for keyword in exclude_keywords:
            if keyword in url_lower or keyword in title_lower:
                return False
        
        # 检查URL是否可能是报告链接
        report_indicators = [
            '/news/', '/press/', '/release/', '/publication/',
            '/report/', '/study/', '/research/', '/article/',
            '/blog/', '/analysis/', '/library/', '/analyser/',
            '.pdf'
        ]
        
        for indicator in report_indicators:
            if indicator in url_lower:
                return True
        
        # 如果标题有一定长度且URL看起来不是导航链接
        if len(title) > 20 and not url_lower.endswith(('.jpg', '.png', '.gif', '.css', '.js')):
            return True
        
        return False


# ============================================================================
# 特定网站解析器
# ============================================================================

def wwf_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    WWF新闻稿页面解析器
    
    Args:
        html_content: HTML内容
        base_url: 基础URL
        
    Returns:
        List[Dict[str, str]]: 报告列表
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # WWF特定选择器（需要根据实际页面结构调整）
    # 尝试多种可能的选择器
    selectors = [
        '.news-list article a',
        '.press-releases .item a',
        '.news-item .title a',
        '.news-article h3 a',
        '#main-content article a',
        '.view-content .views-row a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                
                if href and title:
                    full_url = urljoin(base_url, href)
                    reports.append({
                        'title': title,
                        'url': full_url,
                        'source': 'WWF'
                    })
            break
    
    # 如果上述选择器都没找到，使用通用方法
    if not reports:
        # 查找所有包含'news'或'press'的链接
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            if ('/news/' in href or '/press-release/' in href) and len(title) > 10:
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'WWF'
                })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def eeb_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    EEB图书馆页面解析器（处理Cookie弹窗）
    
    Args:
        html_content: HTML内容
        base_url: 基础URL
        
    Returns:
        List[Dict[str, str]]: 报告列表
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 尝试查找并关闭Cookie弹窗（如果存在）
    cookie_selectors = [
        '#cookie-notice', '.cookie-consent', '.eu-cookie-compliance',
        '#CybotCookiebotDialog', '.cookie-banner'
    ]
    
    for selector in cookie_selectors:
        cookie_div = soup.select_one(selector)
        if cookie_div:
            # 从DOM中移除Cookie弹窗，避免干扰
            cookie_div.decompose()
    
    # EEB特定选择器
    selectors = [
        '.library-item .title a',
        '.publication-item h3 a',
        '.views-row .field-title a',
        '.node--type-publication .node__title a',
        '.content .field-name-title a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                
                if href and title:
                    full_url = urljoin(base_url, href)
                    reports.append({
                        'title': title,
                        'url': full_url,
                        'source': 'EEB'
                    })
            break
    
    # 如果上述选择器都没找到，查找包含'library'或'publication'的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            if ('/library/' in href or '/publication/' in href) and len(title) > 10:
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'EEB'
                })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def concito_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    CONCITO分析页面解析器（原有逻辑）
    
    Args:
        html_content: HTML内容
        base_url: 基础URL
        
    Returns:
        List[Dict[str, str]]: 报告列表
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # CONCITO特定选择器
    selectors = [
        'article a',
        '.publication a',
        '.analyser a',
        '.report a',
        'h3 a',
        'h2 a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                
                if href and title:
                    full_url = urljoin(base_url, href)
                    reports.append({
                        'title': title,
                        'url': full_url,
                        'source': 'CONCITO'
                    })
            break
    
    # 通用回退
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            if ('/analyser/' in href or '/publication/' in href) and len(title) > 10:
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'CONCITO'
                })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def green_alliance_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Green Alliance网站解析器
    
    Args:
        html_content: HTML内容
        base_url: 基础URL
        
    Returns:
        List[Dict[str, str]]: 报告列表
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Green Alliance特定选择器
    selectors = [
        'article a',
        '.publication-item a',
        '.news-item a',
        '.post-item a',
        '.card a',
        '.resource-item a',
        'h3 a',
        'h2 a',
        '.title a',
        '.entry-title a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                
                if href and title:
                    full_url = urljoin(base_url, href)
                    reports.append({
                        'title': title,
                        'url': full_url,
                        'source': 'Green Alliance'
                    })
            break
    
    # 如果上述选择器都没找到，查找包含特定路径的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            # 过滤可能的出版物或文章链接
            if (('/publication/' in href or 
                 '/resource/' in href or 
                 '/article/' in href or 
                 '/news/' in href or
                 '/blog/' in href or
                 '/report/' in href) and len(title) > 10):
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'Green Alliance'
                })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def pembina_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Pembina Institute网站解析器
    
    Args:
        html_content: HTML内容
        base_url: 基础URL
        
    Returns:
        List[Dict[str, str]]: 报告列表
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Pembina特定选择器
    selectors = [
        'article a',
        '.publication a',
        '.report a',
        '.resource a',
        '.card a',
        '.item a',
        'h3 a',
        'h2 a',
        '.title a',
        '.field-name-title a',
        '.node-title a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                
                if href and title:
                    full_url = urljoin(base_url, href)
                    reports.append({
                        'title': title,
                        'url': full_url,
                        'source': 'Pembina Institute'
                    })
            break
    
    # 如果上述选择器都没找到，查找包含特定路径的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            # 过滤可能的出版物或文章链接
            if (('/pub/' in href or 
                 '/publication/' in href or 
                 '/report/' in href or 
                 '/resource/' in href or
                 '/article/' in href or
                 '/blog/' in href) and len(title) > 10):
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'Pembina Institute'
                })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


# ============================================================================
# 网站配置列表
# ============================================================================

# 默认监控的网站列表
DEFAULT_WEBSITES = [
    WebsiteConfig(
        name="CONCITO",
        url="https://concito.dk/en/analyser",
        parser_func=concito_parser
    ),
    WebsiteConfig(
        name="WWF",
        url="https://www.worldwildlife.org/news/press-releases/",
        parser_func=wwf_parser
    ),
    WebsiteConfig(
        name="EEB",
        url="https://eeb.org/en/library/",
        parser_func=eeb_parser
    ),
    WebsiteConfig(
        name="Green Alliance",
        url="https://green-alliance.org.uk",
        parser_func=green_alliance_parser
    ),
    WebsiteConfig(
        name="Pembina Institute",
        url="https://www.pembina.org/all",
        parser_func=pembina_parser
    ),
]

# 网站配置字典（按名称索引）
WEBSITE_CONFIGS = {config.name: config for config in DEFAULT_WEBSITES}


def get_website_config(name: str) -> Optional[WebsiteConfig]:
    """获取指定名称的网站配置"""
    return WEBSITE_CONFIGS.get(name)


def get_all_websites() -> List[WebsiteConfig]:
    """获取所有网站配置"""
    return DEFAULT_WEBSITES.copy()


def add_website_config(config: WebsiteConfig) -> None:
    """添加新的网站配置"""
    DEFAULT_WEBSITES.append(config)
    WEBSITE_CONFIGS[config.name] = config


def remove_website_config(name: str) -> bool:
    """移除网站配置"""
    if name in WEBSITE_CONFIGS:
        del WEBSITE_CONFIGS[name]
        for i, config in enumerate(DEFAULT_WEBSITES):
            if config.name == name:
                DEFAULT_WEBSITES.pop(i)
                return True
    return False


# ============================================================================
# 测试函数
# ============================================================================

def test_all_parsers():
    """测试所有解析器"""
    import requests
    
    print("测试网站解析器...")
    
    for config in DEFAULT_WEBSITES:
        print(f"\n{'='*60}")
        print(f"测试: {config.name} - {config.url}")
        
        try:
            # 获取页面内容
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(config.url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                reports = config.get_reports(response.text, config.url)
                print(f"状态: 成功 (HTTP {response.status_code})")
                print(f"找到报告: {len(reports)} 个")
                
                if reports:
                    print("前3个报告:")
                    for i, report in enumerate(reports[:3], 1):
                        print(f"  {i}. {report['title']}")
                        print(f"     链接: {report['url']}")
            else:
                print(f"状态: 失败 (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"状态: 错误 ({e})")


if __name__ == "__main__":
    test_all_parsers()