#!/usr/bin/env python3
"""
分析新网站结构，为编写解析器做准备
"""

import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 要分析的网站列表
NEW_SITES = [
    {
        'name': 'IEEP',
        'url': 'https://ieep.eu/publications/'
    },
    {
        'name': 'IUCN',
        'url': 'https://iucn.org/press-releases'
    },
    {
        'name': 'Stockholm Resilience',
        'url': 'https://www.stockholmresilience.org/publications.html'
    },
    {
        'name': 'Biodiversity Council',
        'url': 'https://biodiversitycouncil.org.au/resources?category=Report'
    },
    {
        'name': 'Lincoln Institute',
        'url': 'https://www.lincolninst.edu/publications/policy-focus-reports-policy-briefs/'
    }
]

def analyze_site(name, url):
    """分析单个网站结构"""
    print(f"\n{'='*80}")
    print(f"分析网站: {name}")
    print(f"URL: {url}")
    print('='*80)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # 获取页面内容
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 分析页面结构
        print(f"状态: 成功 (HTTP {response.status_code})")
        print(f"页面标题: {soup.title.string if soup.title else '无标题'}")
        
        # 查找可能的报告容器
        common_selectors = [
            'article', '.publication', '.report', '.research', '.publication-item',
            '.post', '.blog-post', '.news-item', '.card', '.resource-item',
            '.library-item', '.analyser', '.study', '.insight'
        ]
        
        print("\n常见容器元素统计:")
        for selector in common_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"  {selector}: {len(elements)} 个元素")
                # 显示前3个元素的简短信息
                for i, elem in enumerate(elements[:3]):
                    text = elem.get_text(strip=True, separator=' ')[:100]
                    if text:
                        print(f"    元素 {i+1}: {text}")
        
        # 查找所有链接并分析模式
        print("\n链接分析:")
        all_links = soup.find_all('a', href=True)
        print(f"总链接数: {len(all_links)}")
        
        # 按常见路径分类链接
        link_categories = {}
        categories = [
            ('/publication/', '出版物'),
            ('/report/', '报告'),
            ('/research/', '研究'),
            ('/article/', '文章'),
            ('/blog/', '博客'),
            ('/news/', '新闻'),
            ('/analysis/', '分析'),
            ('/study/', '研究'),
            ('/insight/', '洞察'),
            ('/library/', '图书馆'),
            ('/resource/', '资源'),
            ('/publications/', '出版物'),
            ('.pdf', 'PDF文件')
        ]
        
        for href, category in categories:
            matching_links = [link for link in all_links if href in link['href'].lower()]
            if matching_links:
                link_categories[category] = len(matching_links)
        
        print("按类别统计的链接:")
        for category, count in link_categories.items():
            print(f"  {category}: {count} 个链接")
        
        # 显示示例链接
        print("\n示例链接 (前5个可能的报告链接):")
        example_count = 0
        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True)
            
            # 判断是否是可能的报告链接
            is_report = False
            for pattern, _ in categories:
                if pattern in href.lower():
                    is_report = True
                    break
            
            if is_report and text and len(text) > 10:
                full_url = urljoin(url, href)
                print(f"  标题: {text[:80]}{'...' if len(text) > 80 else ''}")
                print(f"  链接: {full_url}")
                print()
                example_count += 1
                
                if example_count >= 5:
                    break
        
        # 分析页面结构线索
        print("\n页面结构线索:")
        
        # 查找可能的列表容器
        list_containers = soup.select('.list, .grid, .row, .items, .results, .entries')
        print(f"列表/网格容器: {len(list_containers)} 个")
        
        # 查找分页元素
        pagination = soup.select('.pagination, .page-nav, .pager, .next, .prev, .page-numbers')
        if pagination:
            print("发现分页元素")
        
        # 查找搜索/过滤元素
        search_forms = soup.select('form[role="search"], form.search, input[type="search"]')
        if search_forms:
            print("发现搜索表单")
        
        # 推荐选择器
        print("\n推荐的选择器 (基于分析):")
        recommended_selectors = []
        
        # 基于容器分析
        for selector in common_selectors:
            elements = soup.select(selector)
            if elements and len(elements) >= 3:  # 至少有3个元素
                recommended_selectors.append(f"{selector} a")
        
        # 基于链接分析
        for category, count in link_categories.items():
            if count >= 3:
                # 根据类别推荐选择器
                if category == '出版物':
                    recommended_selectors.extend(['.publication a', '.publication-item a', 'article.publication a'])
                elif category == '报告':
                    recommended_selectors.extend(['.report a', '.report-item a', 'article.report a'])
        
        # 去重并显示
        unique_selectors = list(set(recommended_selectors))
        if unique_selectors:
            for selector in unique_selectors[:10]:  # 最多显示10个
                print(f"  {selector}")
        else:
            print("  无明确推荐选择器，可能需要进一步分析")
        
        # 保存HTML片段供进一步分析
        with open(f'{name.lower().replace(" ", "_")}_sample.html', 'w', encoding='utf-8') as f:
            # 保存前1000个字符的HTML
            f.write(str(soup)[:1000])
        
        return True
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("开始分析新网站结构...")
    
    successful = 0
    for site in NEW_SITES:
        try:
            if analyze_site(site['name'], site['url']):
                successful += 1
            time.sleep(2)  # 避免请求过快
        except KeyboardInterrupt:
            print("\n用户中断")
            break
        except Exception as e:
            print(f"分析 {site['name']} 时出错: {e}")
            continue
    
    print(f"\n{'='*80}")
    print(f"分析完成。成功分析 {successful}/{len(NEW_SITES)} 个网站。")

if __name__ == '__main__':
    main()