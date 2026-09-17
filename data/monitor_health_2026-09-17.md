# IISD 与 Land Use Policy 监控优化验收（2026-09-17）

检测环境：本地 Windows，使用 `MultiWebsiteMonitor` 常规请求路径及各来源解析器，
未写入报告数据库、未发送邮件。联网检测，包含两次真实火山方舟摘要调用。

## 问题

这两个来源能抓到条目，但长期无法生成 AI 摘要：

- IISD 出版物详情页对服务器请求返回 **HTTP 403 + Cloudflare "Just a moment..."**，正文、Key Messages 都取不到。
- Land Use Policy 的文章页同样返回 **HTTP 403**；ScienceDirect RSS 的 `description` 只有
  "Publication date / Source / Author(s)"，不含摘要。

原先的实现只在"新报告插入成功"时调用 AI，且摘要唯一依赖抓取详情页，于是这些条目永久没有摘要。

## 本次策略调整

| 来源 | 详情页可读性 | 内容来源与顺序 | 摘要标注 |
| --- | --- | --- | --- |
| IISD | 403（Cloudflare） | 详情页 → 列表页官方简介 → 题录 | `（依据官网列表页简介概括）` |
| Land Use Policy | 403（ScienceDirect） | 详情页 → Crossref 定位DOI → OpenAlex/Crossref/Semantic Scholar 公开摘要 → 题录 | `（依据公开摘要数据库内容概括）` / `（依据题录信息概括，未获取原文摘要）` |
| 其他 14 个来源 | 正常 | 行为不变：抓不到正文即不生成摘要 | 无标注 |

配套改动：

1. `iisd_parser` 改为解析列表页卡片（`article.c-list-item`），带回简介、`Report/Guide/Digital Story` 类型和 ISO 日期。
2. `sciencedirect_rss_parser` 带回 PII、期刊卷期、作者、出版月等题录信息。
3. `AISummarizer` 新增内容兜底链与来源标注，摘要正文 + 标注合计不超过 200 字。
4. `_is_report_link` 的导航过滤改为路径片段匹配（单词只对 ≤30 字标题生效），修复
   《Making Electric Vehicles Work for More People》这类正常报告被 `more` 误杀的问题。
5. 详情页 403 属于已知情况，不再以 `last_error` 形式残留在成功记录上。

## 联网验收

`python check_websites.py --json data/monitor_health_2026-09-17.json`：**16/16 通过**，
无连接失败、零报告或解析异常。

| 来源 | HTTP | 解析数量 |
| --- | --- | --- |
| CONCITO | 200 | 6 |
| EEB | 200 | 6 |
| Green Alliance | 200 | 2 |
| Pembina Institute | 200 | 5 |
| Ecotrust | 200 | 6 |
| Nature Conservancy | 200 | 6 |
| IISD | 200 | 6 |
| Ecologic Institute | 200 | 6 |
| IEEP | 200 | 6 |
| IUCN | 200 | 6 |
| Stockholm Resilience | 200 | 6 |
| Biodiversity Council | 200 | 4 |
| Lincoln Institute | 200 | 6 |
| UN-Habitat | 200 | 1 |
| Nature Cities | 200 | 6 |
| Land Use Policy | 200 | 6 |

IUCN（5→6）与 Lincoln Institute（5→6）的数量变化来自导航过滤修正，新增条目均为真实新闻稿/出版物。

### 内容与摘要实测

IISD 列表页简介长度 131–226 字符，例如
《Lithium Mining in Chile》："This case study describes Chile's environmental challenges and
associated social issues relating to lithium extraction from brine..."。

Land Use Policy 最新文章经 Crossref `alternative-id` 精确解析 PII→DOI
（`S0264837726004321` → `10.1016/j.landusepol.2026.108348`），OpenAlex 提供了 1449 字符的真实摘要。

两次真实模型调用结果：

- IISD《Mapping Indonesia's Nickel and Cobalt Value Chain》
  → 中文标题"印度尼西亚镍钴价值链研究"，关键词"镍钴价值链，印度尼西亚，风险应对"，
  摘要"该报告探讨印度尼西亚如何在环境、社会和治理、技术、地缘政治等风险下，从镍钴产业中获取更多价值（依据官网列表页简介概括）"。
- Land Use Policy《Improving landcover data governance in developing countries》
  → 摘要基于 OpenAlex 摘要生成，末尾标注"（依据公开摘要数据库内容概括）"。

## 限制

- 源站 403 依然存在，本次没有、也不会绕过站点的人机校验；系统是在"读不到详情页"的前提下改用其它**公开**信息。
- 列表页简介与题录概括只描述主题，不能替代原文结论，因此在摘要中显式标注来源，阅读时请以标注为准。
- Semantic Scholar 未申请密钥时限流严重（429），仅作为第三顺位来源；OpenAlex 才是 Land Use Policy 摘要的主要来源。
- 存量缺失摘要由 `summary_recovery.py` 每 6 小时补一批（每批最多 10 篇、同一篇至少间隔 6 小时），不会立即全部补齐，也不会触发邮件。
- 未验证部署服务器所在网络的结果；部署端更新代码并重启后，应再次运行
  `python check_websites.py --json data/monitor_health.json` 复测。

## 验证

- `python -m pytest tests -q`：36 passed（新增 `tests/test_source_content_fallbacks.py` 覆盖列表页简介、PII 题录、公开摘要、来源标注长度上限，以及"未知站点遇到验证页仍不生成摘要"的回归）。
- `python -m py_compile ai_summarizer.py website_configs.py monitor.py summary_recovery.py`：通过。
- `git diff --check`：通过。
