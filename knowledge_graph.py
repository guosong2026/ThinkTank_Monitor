"""
知识图谱模块
处理报告数据，提取关键词，构建知识图谱
"""

import json
import logging
import re
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta

from db import DatabaseManager

logger = logging.getLogger(__name__)

try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba模块未安装，将使用简单关键词提取方法")


TRANSLATION_DICT = {
    'climate': '气候',
    'change': '变化',
    'climate change': '气候变化',
    'carbon': '碳',
    'neutral': '中和',
    'carbon neutral': '碳中和',
    'sustainable': '可持续',
    'development': '发展',
    'sustainable development': '可持续发展',
    'biodiversity': '生物多样性',
    'energy': '能源',
    'transition': '转型',
    'energy transition': '能源转型',
    'green': '绿色',
    'economy': '经济',
    'green economy': '绿色经济',
    'environmental': '环境',
    'protection': '保护',
    'environmental protection': '环境保护',
    'ecosystem': '生态系统',
    'policy': '政策',
    'climate policy': '气候政策',
    'renewable': '可再生',
    'renewable energy': '可再生能源',
    'water': '水',
    'water resources': '水资源',
    'air': '空气',
    'pollution': '污染',
    'air pollution': '空气污染',
    'circular': '循环',
    'circular economy': '循环经济',
    'low carbon': '低碳',
    'low-carbon': '低碳',
    'adaptation': '适应',
    'climate adaptation': '气候适应',
    'nature': '自然',
    'conservation': '保护',
    'nature conservation': '自然保护',
    'marine': '海洋',
    'marine conservation': '海洋保护',
    'forest': '森林',
    'forest conservation': '森林保护',
    'clean': '清洁',
    'clean energy': '清洁能源',
    'action': '行动',
    'climate action': '气候行动',
    'report': '报告',
    'study': '研究',
    'research': '研究',
    'analysis': '分析',
    'survey': '调查',
    'data': '数据',
    'government': '政府',
    'federal': '联邦',
    'spending': '支出',
    'program': '项目',
    'programs': '项目',
    'nature-related': '自然相关',
    'extinction': '灭绝',
    'preventing': '预防',
    'cost': '成本',
    'australia': '澳大利亚',
    'australian': '澳大利亚',
    'environment': '环境',
    'law': '法律',
    'reform': '改革',
    'support': '支持',
    'community': '社区',
    'attitudes': '态度',
    'gender': '性别',
    'equality': '平等',
    'masculinities': '男性气质',
    'conservation': '保护',
    'science': '科学',
    'policy': '政策',
    'practice': '实践',
    'journal': '期刊',
    'article': '文章'
}


SYNONYM_DICT = {
    '气候变化': ['气候变迁', '气候转变'],
    '碳中和': ['碳中性', '净零排放'],
    '可持续发展': ['永续发展'],
    '生物多样性': ['物种多样性'],
    '能源转型': ['能源转变'],
    '绿色经济': ['环保经济'],
    '环境保护': ['环保', '环境保育'],
    '生态系统': ['生态系'],
    '气候政策': ['气候相关政策'],
    '可再生能源': ['再生能源'],
    '水资源': ['水源'],
    '空气污染': ['大气污染'],
    '循环经济': ['循环型经济'],
    '低碳发展': ['低碳经济'],
    '气候适应': ['适应气候变化'],
    '自然保护': ['自然保育'],
    '海洋保护': ['海洋保育'],
    '森林保护': ['森林保育'],
    '清洁能源': ['洁净能源'],
    '气候行动': ['气候相关行动'],
    '研究': ['调研', '探讨'],
    '分析': ['解析'],
    '调查': ['调研'],
    '保护': ['保育']
}


STOP_KEYWORDS = {
    '2024', '2025', '2026', '2027',
    '一月', '二月', '三月', '四月', '五月', '六月',
    '七月', '八月', '九月', '十月', '十一月', '十二月',
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
    'publication', '出版物',
    'report', 'reports', '报告',
    'article', 'articles', '文章',
    'journal', 'journals',
    'study', 'studies',
    'paper', 'papers',
    '本文聚焦', '本报告', '本篇', '本文', '该报告',
    '本报告由', '日发布', '阿尔伯'
}


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self, data_path: str = "./data/reports_last_10days.json"):
        """
        初始化知识图谱构建器
        
        Args:
            data_path: 报告数据文件路径
        """
        self.data_path = data_path
        self.reports = []
        self.keyword_freq = Counter()
        self.keyword_reports = defaultdict(list)
        self.report_keywords = {}
        self.cooccurrence = defaultdict(Counter)
        
    def translate_keyword(self, keyword: str) -> str:
        """
        翻译关键词为中文
        
        Args:
            keyword: 原始关键词
            
        Returns:
            翻译后的中文关键词
        """
        keyword_lower = keyword.lower().strip()
        
        if keyword_lower in TRANSLATION_DICT:
            return TRANSLATION_DICT[keyword_lower]
        
        for en, zh in TRANSLATION_DICT.items():
            if ' ' in en and en in keyword_lower:
                return zh
        
        if self._is_chinese(keyword):
            return keyword
        
        return keyword
    
    def _is_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)
    
    def normalize_keyword(self, keyword: str) -> str:
        """
        标准化关键词（翻译+同义词合并）
        
        Args:
            keyword: 原始关键词
            
        Returns:
            标准化后的关键词
        """
        translated = self.translate_keyword(keyword)
        
        for standard, synonyms in SYNONYM_DICT.items():
            if translated == standard or translated in synonyms:
                return standard
        
        return translated
    
    def is_valid_keyword(self, keyword: str) -> bool:
        """
        检查关键词是否有效（过滤停用词）
        
        Args:
            keyword: 关键词
            
        Returns:
            是否有效
        """
        keyword_stripped = keyword.strip()
        
        if keyword_stripped == '阿尔伯塔':
            return True
        
        keyword_lower = keyword_stripped.lower()
        
        if keyword_lower in STOP_KEYWORDS:
            return False
        
        if re.match(r'^\d{4}$', keyword_lower):
            return False
        
        if len(keyword_stripped) < 2:
            return False
        
        return True
    
    def load_reports_from_db(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        从数据库加载最近N天的报告数据
        
        Args:
            days: 天数，默认为30天
            
        Returns:
            报告列表
        """
        try:
            with DatabaseManager('reports.db') as db:
                all_reports = db.get_all_reports()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            self.reports = []
            
            for report in all_reports:
                try:
                    discovered_time_str = report['discovered_time']
                    if 'T' in discovered_time_str:
                        discovered_time = datetime.fromisoformat(discovered_time_str.replace('Z', '+00:00'))
                        if discovered_time.tzinfo is not None:
                            discovered_time = discovered_time.replace(tzinfo=None)
                    else:
                        discovered_time = datetime.strptime(discovered_time_str, '%Y-%m-%d %H:%M:%S')
                    
                    if discovered_time >= cutoff_date:
                        title = report.get('title', '')
                        ai_summary = report.get('ai_summary', '')
                        
                        if ai_summary and ai_summary != 'N/A':
                            content = ai_summary
                        else:
                            content = title
                        
                        self.reports.append({
                            'title': title,
                            'url': report.get('url', ''),
                            'content': content,
                            'date': discovered_time.strftime('%Y-%m-%d')
                        })
                except Exception as e:
                    logger.warning(f"解析报告时间失败: {e}")
                    continue
            
            logger.info(f"从数据库成功加载最近 {days} 天的 {len(self.reports)} 篇报告")
            return self.reports
            
        except Exception as e:
            logger.error(f"从数据库加载数据失败: {e}")
            return []
    
    def load_reports(self, use_db: bool = True, days: int = 30) -> List[Dict[str, Any]]:
        """
        加载报告数据（优先从数据库加载）
        
        Args:
            use_db: 是否优先从数据库加载
            days: 从数据库加载的天数
            
        Returns:
            报告列表
        """
        if use_db:
            reports = self.load_reports_from_db(days=days)
            if reports:
                return reports
        
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.reports = json.load(f)
            logger.info(f"成功从文件加载 {len(self.reports)} 篇报告")
            return self.reports
        except FileNotFoundError:
            logger.warning(f"数据文件未找到: {self.data_path}")
            return []
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return []
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        从文本中提取关键词（提取后再翻译）
        
        Args:
            text: 文本内容
            top_k: 返回关键词数量
            
        Returns:
            关键词列表（仅中文）
        """
        if not text or len(text.strip()) == 0:
            return []
        
        cleaned_text = self._clean_text(text)
        
        keywords = []
        
        if JIEBA_AVAILABLE:
            try:
                jieba_keywords = jieba.analyse.extract_tags(cleaned_text, topK=top_k * 2, withWeight=False)
                keywords.extend(jieba_keywords)
            except Exception as e:
                logger.warning(f"jieba提取关键词失败: {e}")
        
        simple_keywords = self._simple_extract_keywords(cleaned_text, top_k * 2)
        keywords.extend(simple_keywords)
        
        normalized_keywords = []
        seen = set()
        
        for kw in keywords:
            normalized = self.normalize_keyword(kw)
            
            if (self.is_valid_keyword(normalized) and 
                normalized not in seen and 
                self._is_chinese(normalized)):
                normalized_keywords.append(normalized)
                seen.add(normalized)
                if len(normalized_keywords) >= top_k:
                    break
        
        return normalized_keywords
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        text = re.sub(r'[^\w\s\u4e00-\u9fa5]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _simple_extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """简单关键词提取（备用方法）"""
        stop_words = {
            '的', '了', '和', '是', '就', '都', '而', '及', '与', '在', '对', '为',
            '有', '等', '这', '那', '也', '但', '或', '并', '个', '之', '以', '于',
            'the', 'and', 'of', 'to', 'in', 'for', 'is', 'are', 'on', 'with', 'that',
            'this', 'by', 'from', 'at', 'it', 'as', 'be', 'or', 'an', 'but', 'we', 'you',
            'a', 'an', 'can', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'need', 'dare', 'ought', 'used', 'have', 'has', 'had', 'do', 'does', 'did',
            'shall', 'will', 'may', 'might', 'must', 'can', 'could', 'would', 'should'
        }
        
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}|[a-zA-Z]{3,}', text.lower())
        word_freq = Counter(w for w in words if w not in stop_words)
        
        return [word for word, _ in word_freq.most_common(top_k)]
    
    def process_reports(self, top_k_keywords: int = 10, global_top_n: int = 100):
        """
        处理所有报告，提取关键词并统计
        
        Args:
            top_k_keywords: 每篇报告提取的关键词数量
            global_top_n: 全局保留的高频关键词数量
        """
        if not self.reports:
            self.load_reports()
        
        if not self.reports:
            logger.warning("没有报告数据可处理")
            return
        
        self.keyword_freq.clear()
        self.keyword_reports.clear()
        self.report_keywords.clear()
        self.cooccurrence.clear()
        
        for idx, report in enumerate(self.reports):
            report_id = idx
            title = report.get('title', '')
            content = report.get('content', '')
            
            full_text = f"{title} {content}"
            keywords = self.extract_keywords(full_text, top_k=top_k_keywords)
            
            self.report_keywords[report_id] = keywords
            
            for keyword in keywords:
                self.keyword_freq[keyword] += 1
                self.keyword_reports[keyword].append(report_id)
            
            for i, kw1 in enumerate(keywords):
                for kw2 in keywords[i+1:]:
                    self.cooccurrence[kw1][kw2] += 1
                    self.cooccurrence[kw2][kw1] += 1
        
        if global_top_n > 0:
            top_keywords = set([kw for kw, _ in self.keyword_freq.most_common(global_top_n)])
            
            self.keyword_freq = Counter({kw: cnt for kw, cnt in self.keyword_freq.items() if kw in top_keywords})
            self.keyword_reports = {kw: reports for kw, reports in self.keyword_reports.items() if kw in top_keywords}
            
            for report_id in list(self.report_keywords.keys()):
                self.report_keywords[report_id] = [kw for kw in self.report_keywords[report_id] if kw in top_keywords]
            
            new_cooccurrence = defaultdict(Counter)
            for kw1 in top_keywords:
                if kw1 in self.cooccurrence:
                    for kw2, cnt in self.cooccurrence[kw1].items():
                        if kw2 in top_keywords:
                            new_cooccurrence[kw1][kw2] = cnt
            self.cooccurrence = new_cooccurrence
        
        logger.info(f"处理完成，共 {len(self.keyword_freq)} 个关键词")
    
    def build_graph_data(self) -> Dict[str, Any]:
        """
        构建图谱数据
        
        Returns:
            包含节点和边的图谱数据
        """
        nodes = []
        edges = []
        
        max_freq = max(self.keyword_freq.values()) if self.keyword_freq else 1
        
        for keyword, freq in self.keyword_freq.items():
            size = 15 + (freq / max_freq) * 45
            nodes.append({
                'id': f'kw_{keyword}',
                'label': keyword,
                'type': 'keyword',
                'frequency': freq,
                'size': size,
                'color': self._get_color_by_frequency(freq, max_freq)
            })
        
        for idx, report in enumerate(self.reports):
            report_id = idx
            title = report.get('title', '')
            url = report.get('url', '')
            date = report.get('date', '')
            
            nodes.append({
                'id': f'report_{report_id}',
                'label': title[:30] + '...' if len(title) > 30 else title,
                'type': 'report',
                'title': title,
                'url': url,
                'date': date,
                'size': 10,
                'color': '#666666'
            })
            
            keywords = self.report_keywords.get(report_id, [])
            for keyword in keywords:
                edges.append({
                    'source': f'kw_{keyword}',
                    'target': f'report_{report_id}',
                    'type': 'contains',
                    'weight': 1
                })
        
        max_cooccur = 1
        for kw1, cooccurs in self.cooccurrence.items():
            if cooccurs:
                current_max = max(cooccurs.values())
                if current_max > max_cooccur:
                    max_cooccur = current_max
        
        added_pairs = set()
        high_cooccur_threshold = max_cooccur * 0.6  # 定义高频阈值为最大值的60%
        for kw1, cooccurs in self.cooccurrence.items():
            for kw2, cnt in cooccurs.items():
                pair = tuple(sorted([kw1, kw2]))
                if pair not in added_pairs:
                    added_pairs.add(pair)
                    width = 1 + (cnt / max_cooccur) * 4
                    is_high_cooccur = cnt >= high_cooccur_threshold
                    edges.append({
                        'source': f'kw_{kw1}',
                        'target': f'kw_{kw2}',
                        'type': 'cooccurrence',
                        'weight': cnt,
                        'width': width,
                        'is_high_cooccur': is_high_cooccur
                    })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'reports': self.reports,
            'keyword_reports': {kw: [self.reports[idx] for idx in idxs] for kw, idxs in self.keyword_reports.items()}
        }
    
    def _get_color_by_frequency(self, freq: int, max_freq: int) -> str:
        """根据频率生成颜色"""
        ratio = freq / max_freq if max_freq > 0 else 0
        
        if ratio >= 0.8:
            return '#e74c3c'
        elif ratio >= 0.6:
            return '#e67e22'
        elif ratio >= 0.4:
            return '#f39c12'
        elif ratio >= 0.2:
            return '#3498db'
        else:
            return '#2ecc71'


def create_sample_data(output_path: str = "./data/reports_last_10days.json", num_reports: int = 20):
    """
    创建示例数据用于测试
    
    Args:
        output_path: 输出文件路径
        num_reports: 报告数量
    """
    import os
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    topics = [
        "气候变化", "碳中和", "可持续发展", "生物多样性",
        "能源转型", "绿色经济", "环境保护", "生态系统",
        "气候政策", "可再生能源", "水资源", "空气污染",
        "循环经济", "低碳发展", "气候适应", "自然保护",
        "海洋保护", "森林保护", "清洁能源", "气候行动"
    ]
    
    organizations = [
        "世界自然基金会", "联合国环境规划署", "国际能源署",
        "自然资源保护协会", "世界资源研究所", "气候组织"
    ]
    
    reports = []
    base_date = datetime.now()
    
    for i in range(num_reports):
        topic1 = topics[i % len(topics)]
        topic2 = topics[(i + 3) % len(topics)]
        org = organizations[i % len(organizations)]
        date = (base_date - timedelta(days=i % 10)).strftime("%Y-%m-%d")
        
        title = f"{org}发布关于{topic1}与{topic2}的最新研究报告"
        content = f"""
        本报告由{org}于{date}发布，重点探讨了{topic1}和{topic2}的最新发展趋势。
        报告指出，{topic1}已成为全球关注的焦点，各国纷纷采取措施应对相关挑战。
        同时，{topic2}作为解决方案的重要组成部分，正在获得越来越多的关注和投资。
        报告还分析了{topic1}与{topic2}之间的相互关系，以及它们对可持续发展目标的贡献。
        专家建议，应加强国际合作，推动技术创新，以实现更加可持续的未来。
        """
        
        reports.append({
            'title': title,
            'url': f"https://example.org/report/{i+1}",
            'content': content,
            'date': date
        })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)
    
    logger.info(f"示例数据已创建: {output_path}")
    return reports


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_sample_data()
