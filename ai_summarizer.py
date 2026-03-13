"""
AI总结模块
调用火山方舟豆包大模型对报告进行总结
"""

import logging
import time
import json
import os
import re
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    if key and key not in os.environ:
                        os.environ[key] = value
    except Exception as e:
        logger.warning(f"加载 .env 文件失败: {e}")


class AISummarizer:
    """AI总结器类 - 使用火山方舟豆包大模型"""

    # 火山方舟API配置
    ARK_API_KEY = os.environ.get("ARK_API_KEY", "")
    ARK_BASE_URL = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    MODEL_ID = os.environ.get("ARK_MODEL_ID", "doubao-pro-1m-preview-20250515")

    # API限流配置
    REQUEST_DELAY = float(os.environ.get("AI_SUMMARY_DELAY", "2.0"))

    def __init__(self, api_key: str = None, model_id: str = None):
        """
        初始化AI总结器

        Args:
            api_key: 火山方舟API密钥
            model_id: 模型ID
        """
        self.api_key = api_key or self.ARK_API_KEY
        self.model_id = model_id or self.MODEL_ID

        if not self.api_key:
            logger.warning("火山方舟API密钥未设置，AI总结功能将禁用")

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key)

    def summarize_report(self, url: str, title: str) -> Optional[Dict[str, str]]:
        """
        对报告进行AI总结

        Args:
            url: 报告URL
            title: 报告原始标题

        Returns:
            Dict包含chinese_title, keywords, summary，或失败时返回None
        """
        if not self.is_configured():
            logger.warning("AI总结器未配置，跳过总结")
            return None

        # 限流：每次请求间隔
        time.sleep(self.REQUEST_DELAY)

        try:
            # 获取网页内容
            page_content = self._fetch_page_content(url)
            if not page_content:
                logger.warning(f"无法获取页面内容: {url}")
                return None

            # 构建提示词
            prompt = self._build_prompt(title, page_content)

            # 调用API
            result = self._call_ark_api(prompt)

            if result:
                # 解析结果
                parsed = self._parse_result(result)
                if parsed:
                    logger.info(f"AI总结成功: {title[:30]}...")
                    return parsed

            logger.warning(f"AI总结失败: {title[:30]}...")
            return None

        except Exception as e:
            logger.error(f"AI总结异常: {e}")
            return None

    def _fetch_page_content(self, url: str, max_length: int = 8000) -> Optional[str]:
        """
        获取网页内容（纯文本）

        Args:
            url: 报告URL
            max_length: 最大字符数

        Returns:
            网页纯文本内容
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                proxies={'http': None, 'https': None, 'ftp': None},
                verify=False
            )
            response.raise_for_status()

            # 提取纯文本（移除HTML标签）
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # 移除script和style标签
            for tag in soup(['script', 'style']):
                tag.decompose()

            # 获取文本
            text = soup.get_text(separator=' ', strip=True)

            # 清理多余空白
            text = re.sub(r'\s+', ' ', text)

            # 截取最大长度
            if len(text) > max_length:
                text = text[:max_length] + "..."

            return text

        except Exception as e:
            logger.error(f"获取页面内容失败: {e}")
            return None

    def _build_prompt(self, title: str, content: str) -> str:
        """
        构建提示词

        Args:
            title: 报告标题
            content: 页面内容

        Returns:
            提示词字符串
        """
        prompt = f"""请阅读以下报告内容，并按要求输出：

1. 将报告标题翻译成中文
2. 提取3个关键词
3. 生成200字以内的中文总结

输出格式（严格按此格式，不要有其他内容）：
翻译标题：[中文标题]
关键词：[关键词1], [关键词2], [关键词3]
总结：[200字以内的中文总结]

报告标题：{title}

报告内容：
{content}
"""
        return prompt

    def _call_ark_api(self, prompt: str, max_tokens: int = 400) -> Optional[str]:
        """
        调用火山方舟API

        Args:
            prompt: 提示词
            max_tokens: 最大输出token数

        Returns:
            API响应内容
        """
        try:
            url = f"{self.ARK_BASE_URL}/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": self.model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60,
                proxies={'http': None, 'https': None, 'ftp': None},
                verify=False
            )

            response.raise_for_status()

            result = response.json()

            # 解析响应
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0].get('message', {})
                content = message.get('content', '')
                return content

            logger.warning(f"API响应格式异常: {result}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"API响应JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"API调用异常: {e}")
            return None

    def _parse_result(self, result: str) -> Optional[Dict[str, str]]:
        """
        解析API返回结果

        Args:
            result: API返回内容

        Returns:
            包含chinese_title, keywords, summary的字典
        """
        try:
            lines = result.strip().split('\n')

            chinese_title = ""
            keywords = ""
            summary = ""

            for line in lines:
                line = line.strip()
                if line.startswith('翻译标题：') or line.startswith('翻译标题:'):
                    chinese_title = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif line.startswith('关键词：') or line.startswith('关键词:'):
                    keywords = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif line.startswith('总结：') or line.startswith('总结:'):
                    summary = line.split('：', 1)[-1].split(':', 1)[-1].strip()

            if chinese_title and keywords and summary:
                return {
                    "chinese_title": chinese_title,
                    "keywords": keywords,
                    "summary": summary
                }

            logger.warning(f"解析结果不完整: {result}")
            return None

        except Exception as e:
            logger.error(f"解析结果失败: {e}")
            return None


def get_ai_summarizer() -> AISummarizer:
    """获取AI总结器实例"""
    return AISummarizer()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    summarizer = AISummarizer()

    if not summarizer.is_configured():
        print("请在.env文件中配置 ARK_API_KEY")
        exit(1)

    test_url = "https://example.com/test-report"
    test_title = "Climate Change Report 2024"

    print("测试AI总结功能...")
    result = summarizer.summarize_report(test_url, test_title)

    if result:
        print(f"翻译标题: {result['chinese_title']}")
        print(f"关键词: {result['keywords']}")
        print(f"总结: {result['summary']}")
    else:
        print("AI总结失败")
