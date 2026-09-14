# 全部监控来源验收（2026-09-14）

检测环境：本地 Windows，使用 MultiWebsiteMonitor 常规请求路径及各来源解析器。
本地配置：monitor_enabled=1，check_interval_hours=6。未验证远程部署进程状态。

首轮：16 个来源均 HTTP 200，其中 9 个解析成功，7 个异常。

- EEB、Green Alliance、IISD、IEEP、IUCN：请求声明支持 Brotli，但基础依赖未提供解码器，压缩内容被当作文本解析。两个抓取入口统一仅请求 gzip/deflate。
- Biodiversity Council：超过 6 条资源时引用未定义的 logger，导致解析异常。补全模块日志定义。
- Land Use Policy：RSS 文章 URL 中的 dgcid=rss_sd_all 跟踪参数被导航过滤规则误拒绝。过滤改为检查域名与路径。
- EEB：额外排除指向当前目录页的链接，避免将 Publications 导航当作报告。
- 连接检查脚本改用常规监控路径，将零报告及解析异常计为失败，并提供 JSON 输出和非零退出码。

最终联网验收：16/16 通过，无连接失败、零报告或解析异常。完整 URL、HTTP 状态、时间与报告样例见同目录 monitor_health_2026-09-14.json。

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
| IUCN | 200 | 5 |
| Stockholm Resilience | 200 | 6 |
| Biodiversity Council | 200 | 4 |
| Lincoln Institute | 200 | 5 |
| UN-Habitat | 200 | 1 |
| Nature Cities | 200 | 6 |
| Land Use Policy | 200 | 6 |

验证：python -m pytest -q，19 passed；git diff --check 通过。
此次检查未写入业务报告数据库、未调用 AI、未发送邮件。数量是本次解析样例数（受现有最多 6 条规则限制），不是新增报告数；未逐篇下载所有正文。部署端更新代码并重启后，应再次运行 python check_websites.py --json data/monitor_health.json 以确认部署网络下的结果。
