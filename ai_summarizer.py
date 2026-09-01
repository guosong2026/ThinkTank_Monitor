"""
AI总结模块
调用火山方舟豆包大模型对报告进行总结
"""

import logging
import time
import json
import os
import re
from io import BytesIO
import requests
from typing import Optional, Dict, Any

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

    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    def __init__(self, api_key: str = None, endpoint: str = None,
                 base_url: str = None, request_delay: float = None):
        """
        初始化AI总结器

        Args:
            api_key: 火山方舟API密钥
            endpoint: 模型ID或推理接入点ID
            base_url: 火山方舟API基础URL
            request_delay: 两次总结请求之间的等待秒数
        """
        # 每次创建实例时读取环境变量，避免模块导入后修改配置不生效。
        self.api_key = api_key if api_key is not None else os.environ.get("ARK_API_KEY", "")
        self.endpoint = endpoint if endpoint is not None else os.environ.get("ARK_ENDPOINT", "")
        configured_base_url = base_url if base_url is not None else os.environ.get(
            "ARK_BASE_URL", self.DEFAULT_BASE_URL
        )
        self.base_url = configured_base_url.rstrip('/')
        delay_value = request_delay if request_delay is not None else os.environ.get("AI_SUMMARY_DELAY", "2.0")
        try:
            self.request_delay = max(0.0, float(delay_value))
        except (TypeError, ValueError):
            self.request_delay = 2.0

        self.last_error = ""
        self.session = requests.Session()
        # 服务器部署时不继承宿主机意外配置的代理，避免方舟请求被错误转发。
        self.session.trust_env = False

        if not self.api_key:
            logger.warning("火山方舟API密钥未设置，AI总结功能将禁用")

        if not self.endpoint:
            logger.warning("火山方舟模型ID/推理接入点未设置，AI总结功能将禁用")

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key and self.endpoint)

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
        if self.request_delay:
            time.sleep(self.request_delay)

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

            response = self.session.get(
                url,
                headers=headers,
                timeout=30,
                verify=True
            )
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/pdf' in content_type or url.lower().split('?', 1)[0].endswith('.pdf'):
                return self._extract_pdf_text(response.content, max_length)

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
            self.last_error = f"获取报告内容失败: {e}"
            logger.error(self.last_error)
            return None

    def _extract_pdf_text(self, content: bytes, max_length: int) -> Optional[str]:
        """从PDF中提取文本，使直接链接到PDF的智库报告也能被总结。"""
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            parts = []
            current_length = 0
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if not page_text:
                    continue
                remaining = max_length - current_length
                if remaining <= 0:
                    break
                parts.append(page_text[:remaining])
                current_length += len(parts[-1])

            text = re.sub(r'\s+', ' ', ' '.join(parts)).strip()
            if not text:
                self.last_error = "PDF中未提取到可总结的文本"
                logger.warning(self.last_error)
                return None
            return text + ("..." if current_length >= max_length else "")
        except Exception as e:
            self.last_error = f"PDF文本提取失败: {e}"
            logger.error(self.last_error)
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
2. 提取3个关键词，每个关键词不超过7个字
3. 生成200字以内的中文总结

只输出一个合法JSON对象，不要使用Markdown代码块或添加其他内容：
{{"chinese_title":"中文标题","keywords":["关键词1","关键词2","关键词3"],"summary":"200字以内的中文总结"}}

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
            # 使用推理接入点ID构建API URL
            self.last_error = ""
            url = f"{self.base_url}/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": self.endpoint,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }

            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                timeout=60,
                verify=True
            )

            if not response.ok:
                self.last_error = self._format_api_error(response)
                logger.error(self.last_error)
                return None

            result = response.json()

            # 解析响应
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0].get('message', {})
                content = message.get('content', '')
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    text_parts = [
                        item.get('text', '') for item in content
                        if isinstance(item, dict) and item.get('type') in ('text', 'output_text')
                    ]
                    return ''.join(text_parts)

            self.last_error = "火山方舟API响应中没有可用的文本内容"
            logger.warning(self.last_error)
            return None

        except requests.exceptions.RequestException as e:
            self.last_error = f"火山方舟API请求失败: {e}"
            logger.error(self.last_error)
            return None
        except json.JSONDecodeError as e:
            self.last_error = f"火山方舟API响应JSON解析失败: {e}"
            logger.error(self.last_error)
            return None
        except Exception as e:
            self.last_error = f"火山方舟API调用异常: {e}"
            logger.error(self.last_error)
            return None

    def _format_api_error(self, response: requests.Response) -> str:
        """提取方舟错误信息，但不记录请求头或API密钥。"""
        detail = ""
        try:
            body: Any = response.json()
            error = body.get('error', body) if isinstance(body, dict) else body
            if isinstance(error, dict):
                detail = error.get('message') or error.get('code') or json.dumps(error, ensure_ascii=False)
            else:
                detail = str(error)
        except (ValueError, json.JSONDecodeError):
            detail = response.text[:300].strip()
        suffix = f": {detail}" if detail else ""
        return f"火山方舟API返回HTTP {response.status_code}{suffix}"

    def test_connection(self) -> tuple[bool, str]:
        """用一个最小请求验证API密钥、模型和Base URL是否可用。"""
        if not self.is_configured():
            return False, "请先填写API Key和模型ID/推理接入点"

        result = self._call_ark_api("请只回复：连接成功", max_tokens=20)
        if result:
            return True, "火山方舟连接测试成功"
        return False, self.last_error or "火山方舟连接测试失败"

    def _parse_result(self, result: str) -> Optional[Dict[str, str]]:
        """
        解析API返回结果

        Args:
            result: API返回内容

        Returns:
            包含chinese_title, keywords, summary的字典
        """
        try:
            cleaned = result.strip()
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s*```$', '', cleaned)

            # 首选JSON，兼容模型在JSON前后偶尔附加少量文字的情况。
            json_match = re.search(r'\{.*\}', cleaned, flags=re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    chinese_title = str(data.get('chinese_title') or data.get('title') or '').strip()
                    raw_keywords = data.get('keywords', [])
                    if isinstance(raw_keywords, list):
                        keywords = '，'.join(str(item).strip() for item in raw_keywords if str(item).strip())
                    else:
                        keywords = str(raw_keywords).strip()
                    summary = str(data.get('summary') or '').strip()
                    if chinese_title and keywords and summary:
                        return {
                            "chinese_title": chinese_title,
                            "keywords": keywords,
                            "summary": summary[:200]
                        }
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            lines = cleaned.split('\n')

            chinese_title = ""
            keywords = ""
            summary = ""

            for line in lines:
                line = line.strip().strip('*')
                if line.startswith('标题：') or line.startswith('标题:') or line.startswith('翻译标题：') or line.startswith('翻译标题:'):
                    chinese_title = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif line.startswith('关键词：') or line.startswith('关键词:'):
                    keywords = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif line.startswith('总结：') or line.startswith('总结:'):
                    summary = line.split('：', 1)[-1].split(':', 1)[-1].strip()

            # 兼容总结换行输出：从“总结”标签后读取剩余全部文本。
            summary_match = re.search(r'(?:总结|摘要)\s*[：:]\s*(.+)$', cleaned, flags=re.DOTALL)
            if summary_match:
                summary = re.sub(r'\s+', ' ', summary_match.group(1)).strip().strip('*')

            if chinese_title and keywords and summary:
                return {
                    "chinese_title": chinese_title,
                    "keywords": keywords,
                    "summary": summary[:200]
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
