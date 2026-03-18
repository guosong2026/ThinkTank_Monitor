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
            reports = self.parser_func(html_content, base_url)
        else:
            reports = self._default_parser(html_content, base_url)
        
        # 对所有报告应用过滤和清理
        filtered_reports = []
        for report in reports:
            cleaned_title = self._clean_title(report['title'])
            if not cleaned_title:
                continue
                
            if self._is_report_link(report['url'], cleaned_title):
                filtered_reports.append({
                    'title': cleaned_title,
                    'url': report['url'],
                    'source': self.name
                })
        
        # 去重
        unique_reports = []
        seen_urls = set()
        for report in filtered_reports:
            if report['url'] not in seen_urls:
                seen_urls.add(report['url'])
                unique_reports.append(report)
        
        return unique_reports
    
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
        if not title:
            return ""
            
        title = ' '.join(title.split())
        
        # 定义常见非标题文本模式（如果标题匹配这些模式，则返回空字符串）
        non_title_patterns = [
            r'^\s*read\s+more(\s+»)?\s*$',  # "read more" 或 "read more »"
            r'^\s*read\s*$',                # "read"
            r'^\s*more\s*$',                # "more"
            r'^\s*next\s+page\s*$',         # "next page"
            r'^\s*previous\s+page\s*$',     # "previous page"
            r'^\s*page\s+\d+\s*$',          # "page 1", "page 2", 等等
            r'^\s*privacy\s+notice\s*$',    # "privacy notice"
            r'^\s*privacy\s+policy\s*$',    # "privacy policy"
            r'^\s*terms\s+of\s+use\s*$',    # "terms of use"
            r'^\s*our\s+research\s+culture\s*$',  # "our research culture"
            r'^\s*click\s+here\s*$',        # "click here"
            r'^\s*learn\s+more\s*$',        # "learn more"
            r'^\s*continue\s+reading\s*$',  # "continue reading"
            r'^\s*download\s*$',            # "download"
            r'^\s*print\s*$',               # "print"
            r'^\s*share\s*$',               # "share"
            r'^\s*email\s*$',               # "email"
            r'^\s*comment\s*$',             # "comment"
            r'^\s*follow\s+us\s*$',         # "follow us"
            r'^\s*follow\s*$',              # "follow"
            r'^\s*sign\s+up\s*$',           # "sign up"
            r'^\s*sign\s+in\s*$',           # "sign in"
            r'^\s*log\s+in\s*$',            # "log in"
            r'^\s*register\s*$',            # "register"
            r'^\s*authors\s*$',             # "authors"
            r'^\s*authorship\s*$',          # "authorship"
        ]
        
        import re
        title_lower = title.lower()
        for pattern in non_title_patterns:
            if re.match(pattern, title_lower):
                return ""  # 返回空字符串，表示这不是有效标题
        
        # 移除常见前缀（不区分大小写，并处理分隔符）
        prefixes = ['Read more', 'Read', 'Download', 'PDF', '»', '›', 'Continue reading', 'Learn more']
        for prefix in prefixes:
            # 不区分大小写检查
            if title.lower().startswith(prefix.lower()):
                # 移除前缀
                title = title[len(prefix):].strip()
                # 如果移除后以常见分隔符开头，也移除它们
                separators = [':', '-', '–', '—', '»', '›', '...', '.']
                while title and any(title.startswith(sep) for sep in separators):
                    title = title[1:].strip()
        
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
        """判断链接是否是报告链接"""
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
    
    # 清理标题
    for report in reports:
        title = report['title']
        
        # 移除日期模式（如 "February 26, 2026"）
        import re
        date_patterns = [
            r'January \d{1,2}, 20\d{2}',
            r'February \d{1,2}, 20\d{2}',
            r'March \d{1,2}, 20\d{2}',
            r'April \d{1,2}, 20\d{2}',
            r'May \d{1,2}, 20\d{2}',
            r'June \d{1,2}, 20\d{2}',
            r'July \d{1,2}, 20\d{2}',
            r'August \d{1,2}, 20\d{2}',
            r'September \d{1,2}, 20\d{2}',
            r'October \d{1,2}, 20\d{2}',
            r'November \d{1,2}, 20\d{2}',
            r'December \d{1,2}, 20\d{2}'
        ]
        
        for pattern in date_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
        
        # 移除常见类型标识
        type_indicators = [
            'Media Release',
            'Article', 
            'Publication',
            'Report',
            'Blog',
            'Analysis',
            'Press Release'
        ]
        
        for indicator in type_indicators:
            title = title.replace(indicator, '').strip()
        
        # 移除多余空白
        title = ' '.join(title.split())
        
        # 如果标题以标点或小写字母开头，可能是截断的，尝试修复
        if title and len(title) > 0:
            # 移除开头的标点
            while title and title[0] in '.,;:!?':
                title = title[1:].strip()
            
            # 如果标题仍然有意义，更新
            if len(title) > 10:
                report['title'] = title
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports

def oecd_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    OECD 报告页面解析器
    页面URL已筛选为特定政策领域（pa17）和语言（en）
    注意：该网站可能返回403错误，需要特殊处理
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 导入WebsiteConfig以使用其清理和过滤方法
    from website_configs import WebsiteConfig
    config = WebsiteConfig('OECD', base_url)
    
    # OECD特定选择器（基于常见模式）
    selectors = [
        'article a',
        '.card a',
        '.publication a',
        '.report a',
        '.item a',
        'h3 a',
        'h2 a',
        '.title a',
        '.result-item a',
        '.document a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                
                if href and title:
                    full_url = urljoin(base_url, href)
                    # 清理标题
                    cleaned_title = config._clean_title(title)
                    if not cleaned_title:
                        continue
                    # 检查是否是报告链接
                    if '/publications/' in full_url.lower() or '/report/' in full_url.lower():
                        if config._is_report_link(full_url, cleaned_title):
                            reports.append({
                                'title': cleaned_title,
                                'url': full_url,
                                'source': 'OECD'
                            })
    
    # 如果没找到，尝试通用方法：查找所有包含'/publications/'的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            title = link.text.strip()
            if href and title:
                if '/publications/' in href.lower():
                    full_url = urljoin(base_url, href)
                    cleaned_title = config._clean_title(title)
                    if cleaned_title and config._is_report_link(full_url, cleaned_title):
                        reports.append({
                            'title': cleaned_title,
                            'url': full_url,
                            'source': 'OECD'
                        })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports

def wri_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    WRI (World Resources Institute) 洞察页面解析器
    页面URL已筛选为insights-50类型
    注意：该网站可能返回403错误，需要特殊处理
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 导入WebsiteConfig以使用其清理和过滤方法
    from website_configs import WebsiteConfig
    config = WebsiteConfig('WRI', base_url)
    
    # WRI特定选择器（基于常见模式）
    selectors = [
        'article a',
        '.card a',
        '.insight a',
        '.resource a',
        '.item a',
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
                    # 清理标题
                    cleaned_title = config._clean_title(title)
                    if not cleaned_title:
                        continue
                    # 检查是否是洞察力链接
                    if '/insights/' in full_url.lower() or '/insight/' in full_url.lower():
                        if config._is_report_link(full_url, cleaned_title):
                            reports.append({
                                'title': cleaned_title,
                                'url': full_url,
                                'source': 'WRI'
                            })
    
    # 如果没找到，尝试通用方法：查找所有包含'insight'的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            title = link.text.strip()
            if href and title:
                if '/insights/' in href.lower() or '/insight/' in href.lower():
                    full_url = urljoin(base_url, href)
                    cleaned_title = config._clean_title(title)
                    if cleaned_title and config._is_report_link(full_url, cleaned_title):
                        reports.append({
                            'title': cleaned_title,
                            'url': full_url,
                            'source': 'WRI'
                        })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports

def unhabitat_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    UN-Habitat 研究出版物页面解析器
    页面使用.publication-list.container元素
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 导入WebsiteConfig以使用其清理和过滤方法
    from website_configs import WebsiteConfig
    
    # 创建临时WebsiteConfig实例
    config = WebsiteConfig('UN-Habitat', base_url)
    
    # 方法1：查找出版物列表容器
    publication_containers = soup.select('.publication-list.container')
    
    for container in publication_containers:
        # 查找容器中的所有链接
        links = container.find_all('a', href=True)
        for link in links:
            title = link.text.strip()
            href = link.get('href', '')
            
            # 清理标题
            cleaned_title = config._clean_title(title)
            if not cleaned_title:
                continue
                
            # 跳过"Read more"链接
            if cleaned_title.lower() in ['read more', 'read now', 'learn more']:
                continue
                
            full_url = urljoin(base_url, href)
            
            # 检查是否是报告链接
            if config._is_report_link(full_url, cleaned_title):
                reports.append({
                    'title': cleaned_title,
                    'url': full_url,
                    'source': 'UN-Habitat'
                })
    
    # 方法2：如果方法1没找到，尝试查找包含'/knowledge/'的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            title = link.text.strip()
            
            # 清理标题
            cleaned_title = config._clean_title(title)
            if not cleaned_title:
                continue
                
            # 检查是否是知识库链接
            if '/knowledge/' in href and len(cleaned_title) > 20:
                full_url = urljoin(base_url, href)
                if config._is_report_link(full_url, cleaned_title):
                    reports.append({
                        'title': cleaned_title,
                        'url': full_url,
                        'source': 'UN-Habitat'
                    })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports

def sei_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    SEI (Stockholm Environment Institute) 出版物页面解析器
    注意：该网站可能返回403错误，需要特殊处理
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # SEI特定选择器（基于常见模式）
    selectors = [
        '.publication-item a',
        '.publication a',
        'article a',
        '.resource-item a',
        '.card a',
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
                    # 检查是否是出版物链接
                    if '/publications/' in full_url.lower() or '/publication/' in full_url.lower():
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'SEI'
                        })
            break
    
    # 如果上述选择器都没找到，查找包含特定路径的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            # 过滤可能的出版物链接
            if ('/publications/' in href.lower() or 
                '/publication/' in href.lower() or
                '/report/' in href.lower() or
                '/research/' in href.lower()) and len(title) > 10:
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'SEI'
                })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def ecotrust_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Ecotrust 出版物与报告页面解析器
    页面使用article元素，链接包含/publications/路径
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Ecotrust特定选择器（基于分析）
    selectors = [
        'article a',
        '.publication a',
        'article.publication a',
        '.publication-item a',
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
                    # 检查是否是出版物链接
                    if '/publications/' in full_url.lower():
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'Ecotrust'
                        })
            break
    
    # 如果上述选择器都没找到，查找包含/publications/的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            if '/publications/' in href.lower() and len(title) > 10:
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'Ecotrust'
                })
    
    # 清理标题：移除日期和其他冗余信息
    for report in reports:
        title = report['title']
        
        # 移除日期模式（如 "2025"）
        import re
        date_patterns = [
            r'\b20\d{2}\b',
            r'\b\d{4}\b'
        ]
        
        for pattern in date_patterns:
            title = re.sub(pattern, '', title).strip()
        
        # 移除多余空白
        title = ' '.join(title.split())
        
        if len(title) > 10:
            report['title'] = title
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def nature_conservancy_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Nature Conservancy 报告页面解析器
    页面包含大量PDF链接，需要特殊处理
    """
    from bs4 import BeautifulSoup
    import re
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 辅助函数：从PDF链接提取更好的标题
    def extract_title_from_pdf_link(link):
        """从PDF链接及其周围元素提取有意义的标题"""
        href = link.get('href', '')
        link_text = link.text.strip()
        
        # 首先尝试从链接文本中清理出标题
        title = link_text
        
        # 移除常见的PDF指示文本
        patterns_to_remove = [
            r'\s*\(PDF\)',
            r'\s*Download\s*',
            r'\s*Full page and report to download\s*',
            r'\s*Download the report\s*',
            r'\s*Download the paper\s*',
            r'\s*More information\s*',
            r'\s*Read more\s*',
            r'\s*View PDF\s*'
        ]
        
        for pattern in patterns_to_remove:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        title = ' '.join(title.split())
        
        # 如果清理后标题仍然很短或无意义，尝试从父元素或兄弟元素获取
        if len(title) < 15 or title.lower() in ['more information', 'download', 'pdf']:
            # 向上查找可能的标题容器
            parent = link.parent
            for _ in range(3):  # 向上查找3层
                if parent is None:
                    break
                
                # 查找父元素中的标题元素
                title_elements = parent.find_all(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
                for elem in title_elements:
                    elem_text = elem.get_text(strip=True)
                    if len(elem_text) > 20 and len(elem_text) < 200:
                        title = elem_text
                        break
                
                if len(title) > 20:
                    break
                    
                # 查找父元素中的段落文本
                paragraphs = parent.find_all('p')
                for p in paragraphs:
                    p_text = p.get_text(strip=True)
                    if len(p_text) > 30 and len(p_text) < 300:
                        # 检查是否包含报告相关关键词
                        if any(keyword in p_text.lower() for keyword in ['report', 'study', 'research', 'analysis', 'publication']):
                            title = p_text[:100] + '...' if len(p_text) > 100 else p_text
                            break
                
                if len(title) > 20:
                    break
                    
                parent = parent.parent
        
        # 如果仍然没有找到好标题，使用链接文本（已清理）
        if len(title) < 10:
            title = link_text
        
        # 最终清理
        title = ' '.join(title.split())
        return title
    
    # 查找所有PDF链接
    pdf_links = soup.find_all('a', href=lambda href: href and href.lower().endswith('.pdf'))
    
    for link in pdf_links:
        href = link['href']
        
        # 跳过明显不是报告的链接
        link_text = link.text.strip().lower()
        exclude_keywords = ['cookie', 'privacy', 'terms', 'donate', 'subscribe', 'logo', 'icon']
        if any(keyword in link_text for keyword in exclude_keywords):
            continue
        
        # 提取更好的标题
        title = extract_title_from_pdf_link(link)
        
        # 如果标题仍然太短或无意义，跳过
        if len(title) < 15:
            continue
        
        full_url = urljoin(base_url, href)
        
        # 检查URL是否包含报告相关路径
        url_lower = full_url.lower()
        if any(path in url_lower for path in ['/documents/', '/dam/', '/reports/', '/publications/']):
            reports.append({
                'title': title,
                'url': full_url,
                'source': 'Nature Conservancy'
            })
    
    # 如果没有找到PDF链接，尝试查找包含"report"或"download"的链接
    if not reports:
        report_selectors = [
            'a[href*="/documents/"]',
            'a[href*="/dam/"]',
            'a[href*="/reports/"]',
            'a[href*="/publications/"]'
        ]
        
        for selector in report_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                title = link.text.strip()
                
                if not href or len(title) < 10:
                    continue
                
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'Nature Conservancy'
                })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def iisd_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    IISD (International Institute for Sustainable Development) 出版物页面解析器
    页面使用article元素，链接包含/publications/路径
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # IISD特定选择器（基于分析）
    selectors = [
        '.publication a',
        '.report a',
        'article.publication a',
        'article.report a',
        '.report-item a',
        'article a',
        '.publication-item a',
        '.resource-item a',
        '.card a',
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
                    # 检查是否是出版物链接
                    if '/publications/' in full_url.lower():
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'IISD'
                        })
            break
    
    # 如果上述选择器都没找到，查找包含特定路径的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            # 过滤可能的出版物链接
            if ('/publications/' in href.lower() or 
                '/report/' in href.lower() or
                '/article/' in href.lower() or
                '/blog/' in href.lower() or
                '/newsletter/' in href.lower()) and len(title) > 10:
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'IISD'
                })
    
    # 清理标题：移除日期和其他冗余信息
    for report in reports:
        title = report['title']
        
        # 移除日期模式（如 "February 2026"）
        import re
        date_patterns = [
            r'January \d{4}',
            r'February \d{4}',
            r'March \d{4}',
            r'April \d{4}',
            r'May \d{4}',
            r'June \d{4}',
            r'July \d{4}',
            r'August \d{4}',
            r'September \d{4}',
            r'October \d{4}',
            r'November \d{4}',
            r'December \d{4}'
        ]
        
        for pattern in date_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
        
        # 移除多余空白
        title = ' '.join(title.split())
        
        if len(title) > 10:
            report['title'] = title
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def ecologic_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Ecologic Institute 出版物页面解析器
    页面使用article元素
    """
    from bs4 import BeautifulSoup
    import re
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 辅助函数：判断链接是否是导航链接
    def is_navigation_link(url: str, title: str) -> bool:
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
                return True
        
        # 检查是否是常见文件类型
        if url_lower.endswith(('.jpg', '.png', '.gif', '.css', '.js', '.svg')):
            return True
        
        return False
    
    # 辅助函数：从元素及其附近提取发布日期
    def extract_date_from_element(element) -> str:
        """从元素及其父元素中提取发布日期"""
        if not element:
            return None
        
        # 首先在元素内部查找日期元素
        date_selectors = [
            'time',
            '.date',
            '.published',
            '.publication-date',
            '.post-date',
            '.entry-date',
            'span.date',
            'span.published'
        ]
        
        for selector in date_selectors:
            date_elem = element.find(selector)
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                if date_text:
                    # 尝试解析日期文本
                    date = parse_date_text(date_text)
                    if date:
                        return date
        
        # 如果没找到，向上查找父元素中的日期
        parent = element.parent
        for _ in range(3):  # 向上查找3层
            if parent is None:
                break
            for selector in date_selectors:
                date_elem = parent.find(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    if date_text:
                        date = parse_date_text(date_text)
                        if date:
                            return date
            parent = parent.parent
        
        # 最后，在元素的文本中查找日期模式
        element_text = element.get_text()
        date_patterns = [
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, element_text, re.IGNORECASE)
            if match:
                date_text = match.group(0)
                date = parse_date_text(date_text)
                if date:
                    return date
        
        return None
    
    # 辅助函数：解析日期文本为YYYY-MM-DD格式
    def parse_date_text(date_text: str) -> str:
        """解析日期文本，返回YYYY-MM-DD格式字符串"""
        from datetime import datetime
        import re
        
        if not date_text:
            return None
        
        # 移除多余空白
        date_text = ' '.join(date_text.split())
        
        # 尝试常见日期格式
        date_formats = [
            '%B %d, %Y',    # January 27, 2025
            '%b %d, %Y',    # Jan 27, 2025
            '%Y-%m-%d',     # 2025-01-27
            '%m/%d/%Y',     # 01/27/2025
            '%d/%m/%Y',     # 27/01/2025
            '%B %Y',        # January 2025
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_text, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # 尝试匹配年份模式
        year_match = re.search(r'\b(20\d{2})\b', date_text)
        if year_match:
            year = year_match.group(1)
            # 如果没有月份和日期，使用年份-01-01作为近似值
            return f"{year}-01-01"
        
        return None
    
    # Ecologic特定选择器（基于分析）
    selectors = [
        'article a',
        '.publication a',
        '.report a',
        '.research a',
        '.publication-item a',
        '.resource-item a',
        '.card a',
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
                
                if href and title and len(title) > 15:
                    full_url = urljoin(base_url, href)
                    # 排除导航链接
                    if not is_navigation_link(full_url, title):
                        # 尝试提取发布日期
                        publish_date = extract_date_from_element(link)
                        
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'Ecologic Institute',
                            'publish_date': publish_date
                        })
            break
    
    # 如果上述选择器都没找到，查找所有可能链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            if href and title and len(title) > 15:
                full_url = urljoin(base_url, href)
                if not is_navigation_link(full_url, title):
                    # 尝试提取发布日期
                    publish_date = extract_date_from_element(link)
                    
                    reports.append({
                        'title': title,
                        'url': full_url,
                        'source': 'Ecologic Institute',
                        'publish_date': publish_date
                    })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def columbia_energy_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Columbia Energy Policy 工作报告页面解析器
    注意：该网站可能返回403错误，需要特殊处理
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Columbia Energy特定选择器（基于常见模式）
    selectors = [
        '.publication-item a',
        '.publication a',
        '.report a',
        '.research a',
        'article a',
        '.resource-item a',
        '.card a',
        '.work-item a',
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
                    # 检查是否是工作报告链接
                    if ('/our-work/' in full_url.lower() or 
                        '/publications/' in full_url.lower() or
                        '/report/' in full_url.lower() or
                        '/research/' in full_url.lower()):
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'Columbia Energy Policy'
                        })
            break
    
    # 如果上述选择器都没找到，查找包含特定路径的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            # 过滤可能的工作报告链接
            if ('/our-work/' in href.lower() or 
                '/publications/' in href.lower() or
                '/report/' in href.lower() or
                '/research/' in href.lower() or
                '/article/' in href.lower()) and len(title) > 10:
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'Columbia Energy Policy'
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
    
    # 导入WebsiteConfig以使用其清理和过滤方法
    from website_configs import WebsiteConfig
    
    # 创建临时WebsiteConfig实例
    config = WebsiteConfig('Green Alliance', base_url)
    
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
                    # 清理标题
                    cleaned_title = config._clean_title(title)
                    if not cleaned_title:
                        continue
                    
                    full_url = urljoin(base_url, href)
                    
                    # 检查是否是报告链接
                    if config._is_report_link(full_url, cleaned_title):
                        reports.append({
                            'title': cleaned_title,
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
            
            # 清理标题
            cleaned_title = config._clean_title(title)
            if not cleaned_title:
                continue
            
            # 过滤可能的出版物或文章链接
            if (('/publication/' in href or 
                 '/resource/' in href or 
                 '/article/' in href or 
                 '/news/' in href or
                 '/blog/' in href or
                 '/report/' in href) and len(cleaned_title) > 10):
                full_url = urljoin(base_url, href)
                
                # 检查是否是报告链接
                if config._is_report_link(full_url, cleaned_title):
                    reports.append({
                        'title': cleaned_title,
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
    import re
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 导入WebsiteConfig以使用其清理和过滤方法
    from website_configs import WebsiteConfig
    
    # 创建临时WebsiteConfig实例
    config = WebsiteConfig('Pembina Institute', base_url)
    
    # 方法1：直接查找卡片中的文章链接（针对新网站结构优化）
    cards = soup.select('.card')
    
    for card in cards:
        # 在卡片中查找所有链接
        links = card.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            if not href:
                continue
            
            # 检查是否是文章链接
            href_lower = href.lower()
            is_article_link = any(pattern in href_lower for pattern in 
                                 ['/media-release/', '/blog/', '/pub/', 
                                  '/publication/', '/report/', '/article/',
                                  '/op-ed/'])  # 添加op-ed模式
            
            if not is_article_link:
                continue
            
            # 提取并清理标题
            title = link.text.strip()
            title = ' '.join(title.split())
            
            # 使用WebsiteConfig的清理方法
            cleaned_title = config._clean_title(title)
            if not cleaned_title:
                continue
            
            # 如果标题太短或为空，可能是图标链接，跳过
            if not cleaned_title or len(cleaned_title) < 10:
                continue
            
            # 检查标题是否包含日期模式（进一步确认是文章链接）
            # 文章标题通常包含日期，如 "February 27, 2026"
            date_patterns = [
                r'January \d{1,2}, 20\d{2}',
                r'February \d{1,2}, 20\d{2}',
                r'March \d{1,2}, 20\d{2}',
                r'April \d{1,2}, 20\d{2}',
                r'May \d{1,2}, 20\d{2}',
                r'June \d{1,2}, 20\d{2}',
                r'July \d{1,2}, 20\d{2}',
                r'August \d{1,2}, 20\d{2}',
                r'September \d{1,2}, 20\d{2}',
                r'October \d{1,2}, 20\d{2}',
                r'November \d{1,2}, 20\d{2}',
                r'December \d{1,2}, 20\d{2}'
            ]
            
            has_date = any(re.search(pattern, title, re.IGNORECASE) for pattern in date_patterns)
            
            # 也检查是否包含文章类型（Media Release, Article, Op-ed等）
            type_indicators = ['Media Release', 'Article', 'Op-ed', 'Publication', 'Report', 'Blog']
            has_type = any(indicator in title for indicator in type_indicators)
            
            # 如果标题包含日期或类型，或者长度足够，则认为是文章
            if has_date or has_type or len(cleaned_title) > 20:
                full_url = urljoin(base_url, href)
                
                # 检查是否是报告链接
                if config._is_report_link(full_url, cleaned_title):
                    reports.append({
                        'title': cleaned_title,
                        'url': full_url,
                        'source': 'Pembina Institute'
                    })
                # 找到一个有效链接后，跳出内层循环，处理下一个卡片
                break
    
    # 方法2：如果方法1没找到，回退到原始选择器逻辑
    if not reports:
        # Pembina特定选择器（针对新网站结构优化）
        # 优先使用更具体的选择器
        selectors = [
            'h3.text-2xl.mb-2 a',           # 文章标题链接
            '.card h3 a',                   # 卡片中的标题
            '.card a',                      # 卡片中的任何链接
            'article a',
            '.publication a',
            '.report a',
            '.resource a',
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
                    href = link.get('href', '')
                    if not href:
                        continue
                        
                    # 提取并清理标题
                    title = link.text.strip()
                    title = ' '.join(title.split())
                    
                    # 检查是否是文章链接
                    href_lower = href.lower()
                    is_article_link = any(pattern in href_lower for pattern in 
                                         ['/media-release/', '/blog/', '/pub/', 
                                          '/publication/', '/report/', '/article/',
                                          '/op-ed/'])
                    
                    # 如果链接看起来是文章且标题有一定长度
                    if is_article_link and title and len(title) > 10:
                        full_url = urljoin(base_url, href)
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'Pembina Institute'
                        })
    
    # 方法3：如果上述方法都没找到，查找包含特定路径的链接
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
                 '/blog/' in href or
                 '/media-release/' in href or
                 '/op-ed/' in href) and len(title) > 10):
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


def ieep_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    IEEP 出版物页面解析器
    页面使用article元素，链接包含/publications/路径
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # IEEP特定选择器（基于分析）
    selectors = [
        'article a',
        '.publication a',
        'article.publication a',
        '.publication-item a',
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
                    # 检查是否是出版物链接
                    if '/publications/' in full_url.lower():
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'IEEP'
                        })
            break
    
    # 如果上述选择器都没找到，查找包含/publications/的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            if '/publications/' in href.lower() and len(title) > 10:
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'IEEP'
                })
    
    # 清理标题：移除日期和其他冗余信息
    for report in reports:
        title = report['title']
        
        # 移除日期模式（如 "2 March 2026"）
        import re
        date_patterns = [
            r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
            r'\b20\d{2}\b',
            r'\b\d{4}\b'
        ]
        
        for pattern in date_patterns:
            title = re.sub(pattern, '', title).strip()
        
        # 移除多余空白
        title = ' '.join(title.split())
        
        if len(title) > 10:
            report['title'] = title
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def iucn_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    IUCN 新闻稿页面解析器
    页面可能有分页和列表容器
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # IUCN特定选择器（基于分析）
    selectors = [
        '.list a',
        '.grid a',
        '.row a',
        '.items a',
        '.results a',
        '.entries a',
        'article a',
        '.news-item a',
        '.press-release a',
        '.card a',
        '.item a',
        'h3 a',
        'h2 a',
        '.title a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                
                if href and title:
                    full_url = urljoin(base_url, href)
                    # 检查是否是新闻稿或出版物链接
                    if any(pattern in full_url.lower() for pattern in 
                          ['/press-release/', '/press/', '/news/', '/library/', '/publication/']):
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'IUCN'
                        })
            break
    
    # 如果上述选择器都没找到，查找所有链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            # 过滤可能的新闻稿链接
            if (('/press-release/' in href.lower() or 
                 '/press/' in href.lower() or 
                 '/news/' in href.lower() or
                 '/library/' in href.lower()) and 
                len(title) > 10):
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'IUCN'
                })
    
    # 清理标题
    for report in reports:
        title = report['title']
        title = ' '.join(title.split())
        if len(title) > 10:
            report['title'] = title
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def stockholm_resilience_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Stockholm Resilience Centre 出版物页面解析器
    页面包含research-stories和research-news
    """
    from bs4 import BeautifulSoup

    if not html_content:
        return []

    reports = []
    soup = BeautifulSoup(html_content, 'lxml')

    # 排除非内容链接的关键词
    exclude_keywords = [
        'home', 'about', 'contact', 'privacy', 'terms', 'login',
        'signup', 'subscribe', 'twitter', 'facebook', 'linkedin',
        'instagram', 'youtube', 'rss', 'feed', 'search', 'donate',
        'careers', 'press', 'media', 'newsletter', 'cookie',
        'meet-our-team', 'annual-reports', 'research-projects',
        'our-research-culture', 'principles-for-research-ethics',
        'resilience-dictionary', 'planetary-boundaries'
    ]

    # Stockholm Resilience特定选择器 - 针对research stories/news
    selectors = [
        '.content a',
        'main a',
        '.main-content a',
        'article a',
        '.publication a',
        '.item a',
        '.post a',
        '.news-item a',
        'h3 a',
        'h2 a',
        '.title a'
    ]

    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')

                if not href or not title:
                    continue

                # 清理标题 - 移除多余空白
                title = ' '.join(title.split())

                # 排除标题太短或包含排除关键词的链接
                if len(title) < 15:
                    continue

                # 排除非内容页面
                href_lower = href.lower()
                if any(kw in href_lower for kw in exclude_keywords):
                    continue

                # 检查是否是研究故事/新闻/出版物链接
                # 包含 /research-stories/ 或 /research-news/ 或 /publications/
                if any(pattern in href_lower for pattern in
                      ['/research-stories/', '/research-news/', '/publications/']):
                    # 排除页面类型链接
                    skip_patterns = ['type=', '?page', '#', 'meet-our-team']
                    if any(p in href_lower for p in skip_patterns):
                        continue

                    # 进一步清理标题
                    # 移除 "Research story|2026-02-27" 这种前缀
                    import re
                    title = re.sub(r'^(Research story|General news|Research story)\s*\|\s*\d{4}-\d{2}-\d{2}\s*', '', title)

                    # 移除 "Read more" 等
                    read_more_patterns = ['read more', 'read more »', 'learn more', 'click here']
                    for pattern in read_more_patterns:
                        title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()

                    # 清理标题中的出版物类型、日期和作者信息
                    # 格式: "Title Journal / article | 2026 Author..." -> "Title"
                    title = re.sub(r'\s*/\s*\w+\s*\|.*$', '', title)
                    title = re.sub(r'\s*\|\s*\d{4}.*$', '', title)
                    title = re.sub(r'\s+(Journal|Science|Nature|Paper|Research|Report|Book|Chapter)$', '', title, flags=re.IGNORECASE)
                    title = title.strip()

                    if len(title) >= 15:
                        full_url = urljoin(base_url, href)
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'Stockholm Resilience'
                        })
            break

    # 如果上述选择器都没找到，查找包含特定路径的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            title = link.text.strip()

            if not href or not title:
                continue

            title = ' '.join(title.split())
            href_lower = href.lower()

            # 排除非内容链接
            if any(kw in href_lower for kw in exclude_keywords):
                continue

            # 过滤可能的研究故事/新闻链接
            if (any(pattern in href_lower for pattern in
                   ['/research-stories/', '/research-news/', '/publications/']) and
                len(title) >= 15):
                # 清理标题
                import re
                title = re.sub(r'^(Research story|General news)\s*\|\s*\d{4}-\d{2}-\d{2}\s*', '', title)

                # 清理标题中的出版物类型、日期和作者信息
                title = re.sub(r'\s*/\s*\w+\s*\|.*$', '', title)
                title = re.sub(r'\s*\|\s*\d{4}.*$', '', title)
                title = re.sub(r'\s+(Journal|Science|Nature|Paper|Research|Report|Book|Chapter)$', '', title, flags=re.IGNORECASE)
                title = title.strip()

                if len(title) >= 15:
                    full_url = urljoin(base_url, href)
                    reports.append({
                        'title': title,
                        'url': full_url,
                        'source': 'Stockholm Resilience'
                    })

    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)

    # 限制只返回最新的报告（最多10个），避免抓取过多历史报告
    MAX_REPORTS_PER_SITE = 10
    if len(unique_reports) > MAX_REPORTS_PER_SITE:
        logger.info(f"Stockholm Resilience: 限制返回报告数量为 {MAX_REPORTS_PER_SITE} 个（共 {len(unique_reports)} 个）")
        unique_reports = unique_reports[:MAX_REPORTS_PER_SITE]

    return unique_reports


def biodiversity_council_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Biodiversity Council Australia 资源页面解析器
    页面按类别过滤（Report类别）
    """
    from bs4 import BeautifulSoup
    import re

    if not html_content:
        return []

    reports = []
    soup = BeautifulSoup(html_content, 'lxml')

    # 辅助函数：从父元素或兄弟元素提取标题
    def extract_title_from_link(link):
        """从链接或其周围元素提取正确的标题"""
        link_text = link.get_text(strip=True)

        # 如果标题已经有意义，直接返回
        if link_text and len(link_text) > 15:
            # 排除 "Read More", "Learn More" 等
            if link_text.lower() not in ['read more', 'read more »', 'learn more', 'learn more »', 'click here']:
                return link_text

        # 尝试从父元素获取标题
        parent = link.parent
        if parent:
            # 查找父元素中的标题标签
            title_tags = parent.find_all(['h1', 'h2', 'h3', 'h4', 'strong', 'b', 'span'])
            for tag in title_tags:
                tag_text = tag.get_text(strip=True)
                if tag_text and len(tag_text) > 15:
                    return tag_text

            # 查找前面的兄弟元素作为标题
            prev_sibling = link.previous_sibling
            while prev_sibling:
                if hasattr(prev_sibling, 'get_text'):
                    text = prev_sibling.get_text(strip=True)
                    if text and len(text) > 15:
                        return text
                prev_sibling = prev_sibling.previous_sibling

        return link_text

    # Biodiversity Council特定选择器
    selectors = [
        'article a',
        '.resource a',
        '.card a',
        '.item a',
        '.report a',
        '.category-report a',
        'h3 a',
        'h2 a',
        '.title a',
        'a[href*="/resources/"]'
    ]

    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                href = link.get('href', '')

                if not href:
                    continue

                # 提取标题
                title = extract_title_from_link(link)

                if not title:
                    continue

                # 清理标题
                title = ' '.join(title.split())

                # 跳过无效标题
                if len(title) < 15:
                    continue

                # 排除导航链接
                exclude_patterns = ['privacy', 'terms', 'contact', 'about', 'home', 'cookie']
                if any(p in title.lower() for p in exclude_patterns):
                    continue

                full_url = urljoin(base_url, href)

                # 检查是否是资源或报告链接
                if any(pattern in full_url.lower() for pattern in
                      ['/resources/', '/report/', '/publication/']):
                    reports.append({
                        'title': title,
                        'url': full_url,
                        'source': 'Biodiversity Council'
                    })
            break

    # 如果上述选择器都没找到，查找所有链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            title = extract_title_from_link(link)

            if not href or not title:
                continue

            title = ' '.join(title.split())

            if len(title) < 15:
                continue

            # 排除导航链接
            if any(p in title.lower() for p in ['privacy', 'terms', 'contact', 'about', 'home', 'cookie', 'read more', 'learn more']):
                continue

            # 过滤可能的报告或资源链接
            if (('/resources/' in href.lower() or
                 '/report/' in href.lower() or
                 '/publication/' in href.lower())):
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'Biodiversity Council'
                })

    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)

    # 限制只返回最新的报告（最多10个），避免抓取过多历史报告
    MAX_REPORTS_PER_SITE = 10
    if len(unique_reports) > MAX_REPORTS_PER_SITE:
        logger.info(f"Biodiversity Council: 限制返回报告数量为 {MAX_REPORTS_PER_SITE} 个（共 {len(unique_reports)} 个）")
        unique_reports = unique_reports[:MAX_REPORTS_PER_SITE]

    return unique_reports


def lincoln_institute_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Lincoln Institute 政策聚焦报告页面解析器
    页面有.publication-item元素
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Lincoln Institute特定选择器（基于分析）
    selectors = [
        '.publication-item a',
        '.publication a',
        'article.publication a',
        'article a',
        '.card a',
        '.item a',
        '.policy-focus a',
        '.brief a',
        'h3 a',
        'h2 a',
        '.title a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                
                if href and title:
                    full_url = urljoin(base_url, href)
                    # 检查是否是出版物链接
                    if any(pattern in full_url.lower() for pattern in 
                          ['/publications/', '/policy-focus/', '/brief/', '/report/']):
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'Lincoln Institute'
                        })
            break
    
    # 如果上述选择器都没找到，查找包含特定路径的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            title = link.text.strip()
            
            # 过滤可能的出版物链接
            if (('/publications/' in href.lower() or 
                 '/policy-focus/' in href.lower() or 
                 '/brief/' in href.lower() or
                 '/report/' in href.lower()) and 
                len(title) > 10):
                full_url = urljoin(base_url, href)
                reports.append({
                    'title': title,
                    'url': full_url,
                    'source': 'Lincoln Institute'
                })
    
    # 清理标题
    for report in reports:
        title = report['title']
        title = ' '.join(title.split())
        if len(title) > 10:
            report['title'] = title
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports


def nature_cities_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    Nature Cities 评论与分析页面解析器
    页面包含文章卡片，可能需要处理动态加载内容
    """
    from bs4 import BeautifulSoup
    
    if not html_content:
        return []
    
    reports = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 导入WebsiteConfig以使用其清理和过滤方法
    from website_configs import WebsiteConfig
    config = WebsiteConfig('Nature Cities', base_url)
    
    # Nature Cities特定选择器（基于常见模式）
    # Nature网站通常使用.c-card、article等类
    selectors = [
        'article a',
        '.c-card a',
        '.c-card__link',
        '.c-card__title a',
        '.c-article-item a',
        'h3 a',
        'h2 a',
        'h1 a',
        '.c-article-title a',
        '.article-item a',
        '.post-item a'
    ]
    
    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')
                
                if href and title:
                    full_url = urljoin(base_url, href)
                    # 清理标题
                    cleaned_title = config._clean_title(title)
                    if not cleaned_title:
                        continue
                    # 检查是否是文章链接
                    if '/natcities/articles/' in full_url.lower() or '/articles/' in full_url.lower():
                        if config._is_report_link(full_url, cleaned_title):
                            reports.append({
                                'title': cleaned_title,
                                'url': full_url,
                                'source': 'Nature Cities'
                            })
    
    # 如果没找到，尝试通用方法：查找所有包含'article'的链接
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            title = link.text.strip()
            if href and title:
                if '/natcities/articles/' in href.lower() or '/articles/' in href.lower():
                    full_url = urljoin(base_url, href)
                    cleaned_title = config._clean_title(title)
                    if cleaned_title and config._is_report_link(full_url, cleaned_title):
                        reports.append({
                            'title': cleaned_title,
                            'url': full_url,
                            'source': 'Nature Cities'
                        })
    
    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)
    
    return unique_reports

def world_bank_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    World Bank Documents & Reports 页面解析器
    适配新URL: documents.worldbank.org
    """
    from bs4 import BeautifulSoup

    if not html_content:
        return []

    reports = []
    soup = BeautifulSoup(html_content, 'lxml')

    # 导入WebsiteConfig以使用其清理和过滤方法
    from website_configs import WebsiteConfig
    config = WebsiteConfig('World Bank', base_url)

    # World Bank Documents 页面选择器
    selectors = [
        '.card a',
        '.document a',
        '.publication a',
        '.result a',
        'article a',
        '.item a',
        'h3 a',
        'h2 a',
        '.title a',
        '.doc-title a'
    ]

    for selector in selectors:
        links = soup.select(selector)
        if links:
            for link in links:
                title = link.text.strip()
                href = link.get('href', '')

                if not href or not title:
                    continue

                # 清理标题
                title = ' '.join(title.split())

                if len(title) < 15:
                    continue

                full_url = urljoin(base_url, href)

                # 检查是否是文档链接
                if '/document/' in full_url.lower() or '/report/' in full_url.lower():
                    if config._is_report_link(full_url, title):
                        reports.append({
                            'title': title,
                            'url': full_url,
                            'source': 'World Bank'
                        })
            break

    # 如果没找到，尝试通用方法
    if not reports:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            title = link.text.strip()

            if not href or not title:
                continue

            title = ' '.join(title.split())

            if len(title) < 15:
                continue

            # 检查是否是文档链接
            if '/document/' in href.lower() or '/report/' in href.lower():
                full_url = urljoin(base_url, href)
                if config._is_report_link(full_url, title):
                    reports.append({
                        'title': title,
                        'url': full_url,
                        'source': 'World Bank'
                    })

    # 去重
    unique_reports = []
    seen_urls = set()
    for report in reports:
        if report['url'] not in seen_urls:
            seen_urls.add(report['url'])
            unique_reports.append(report)

    return unique_reports


def sciencedirect_rss_parser(rss_content: str, base_url: str) -> List[Dict[str, str]]:
    """
    ScienceDirect RSS 解析器
    用于解析期刊RSS订阅，获取最新文章
    """
    import re
    import xml.etree.ElementTree as ET

    if not rss_content:
        return []

    reports = []

    try:
        root = ET.fromstring(rss_content)
        channel = root.find('channel')
        if channel is None:
            return []

        items = channel.findall('item')

        for item in items:
            title_elem = item.find('title')
            link_elem = item.find('link')
            desc_elem = item.find('description')

            if title_elem is None or link_elem is None:
                continue

            title = title_elem.text or ''
            if not title:
                continue

            title = ' '.join(title.split())

            link = link_elem.text or ''

            publish_date = None
            if desc_elem is not None and desc_elem.text:
                desc = desc_elem.text
                date_match = re.search(r'Publication date: ([^<]+)', desc)
                if date_match:
                    publish_date = date_match.group(1).strip()

            if link:
                reports.append({
                    'title': title,
                    'url': link,
                    'source': 'Land Use Policy',
                    'publish_date': publish_date
                })

    except ET.ParseError as e:
        logging.warning(f"RSS解析错误: {e}")
    except Exception as e:
        logging.warning(f"处理RSS内容时出错: {e}")

    return reports


# ============================================================================
# 测试函数
# ============================================================================



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
    WebsiteConfig(
        name="Ecotrust",
        url="https://ecotrust.org/stories-news/publications-reports/",
        parser_func=ecotrust_parser
    ),
    WebsiteConfig(
        name="Nature Conservancy",
        url="https://www.nature.org/en-us/what-we-do/our-insights/reports/",
        parser_func=nature_conservancy_parser
    ),
    WebsiteConfig(
        name="IISD",
        url="https://www.iisd.org/publications",
        parser_func=iisd_parser
    ),
    WebsiteConfig(
        name="Ecologic Institute",
        url="https://www.ecologic.eu/publications",
        parser_func=ecologic_parser
    ),
    WebsiteConfig(
        name="IEEP",
        url="https://ieep.eu/publications/",
        parser_func=ieep_parser
    ),
    WebsiteConfig(
        name="IUCN",
        url="https://iucn.org/press-releases",
        parser_func=iucn_parser
    ),
    WebsiteConfig(
        name="Stockholm Resilience",
        url="https://www.stockholmresilience.org/publications.html",
        parser_func=stockholm_resilience_parser
    ),
    WebsiteConfig(
        name="Biodiversity Council",
        url="https://biodiversitycouncil.org.au/resources?category=Report",
        parser_func=biodiversity_council_parser
    ),
    WebsiteConfig(
        name="Lincoln Institute",
        url="https://www.lincolninst.edu/publications/policy-focus-reports-policy-briefs/",
        parser_func=lincoln_institute_parser
    ),
    WebsiteConfig(
        name="UN-Habitat",
        url="https://unhabitat.org/knowledge/research-and-publications",
        parser_func=unhabitat_parser
    ),
    WebsiteConfig(
        name="Nature Cities",
        url="https://www.nature.com/natcities/reviews-and-analysis",
        parser_func=nature_cities_parser
    ),
    # Land Use Policy - ScienceDirect期刊RSS
    WebsiteConfig(
        name="Land Use Policy",
        url="https://rss.sciencedirect.com/publication/science/02648377",
        parser_func=sciencedirect_rss_parser
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