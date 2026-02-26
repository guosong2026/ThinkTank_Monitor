# 网站报告监控工具

一个用于监控网站报告并自动存储到SQLite数据库的Python工具。

## 功能特点

- **定时监控**：每小时自动检查目标网站（可配置间隔）
- **智能抓取**：自动解析网页中的报告标题和链接
- **数据存储**：将发现的报告保存到SQLite数据库
- **重复检测**：自动跳过已存在的报告
- **实时通知**：在控制台显示新发现的报告
- **邮件推送**：发现新报告时自动发送邮件通知（支持SMTP协议）
- **详细日志**：记录所有操作到日志文件
- **多种模式**：支持单次运行、连续监控、测试模式

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用（连续监控模式）

```bash
python monitor.py
```

默认配置：
- 目标网站：`https://concito.dk/en/analyser`
- 数据库文件：`reports.db`
- 检查间隔：1小时

### 单次检查模式

```bash
python monitor.py --once
```

### 显示统计信息

```bash
python monitor.py --stats
```

### 测试模式

```bash
python monitor.py --test
```

### 自定义配置

```bash
# 自定义目标网站
python monitor.py --url https://example.com/reports

# 自定义数据库文件
python monitor.py --db custom.db

# 自定义检查间隔（2小时）
python monitor.py --interval 2

# 限制运行次数（运行3次后停止）
python monitor.py --runs 3

# 组合使用
python monitor.py --url https://example.com --db example.db --interval 2 --runs 5
```

## 邮件配置

### 1. 配置SMTP

首次使用邮件功能前，需要配置SMTP：

1. **通过环境变量配置（推荐）**：
   
   项目支持通过环境变量配置邮件参数，这样无需修改源代码，便于在不同环境使用不同邮箱。
   
   **设置环境变量**：
   
   ```bash
   # Windows (命令行)
   set SMTP_SERVER=smtp.office365.com
   set SMTP_PORT=587
   set SENDER_EMAIL=your_email@outlook.com
   set SENDER_PASSWORD=your_smtp_authorization_code
   set RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com
   
   # Linux/macOS (bash)
   export SMTP_SERVER=smtp.office365.com
   export SMTP_PORT=587
   export SENDER_EMAIL=your_email@outlook.com
   export SENDER_PASSWORD=your_smtp_authorization_code
   export RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com
   
   # Windows PowerShell
   $env:SMTP_SERVER="smtp.office365.com"
   $env:SMTP_PORT="587"
   $env:SENDER_EMAIL="your_email@outlook.com"
   $env:SENDER_PASSWORD="your_smtp_authorization_code"
   $env:RECIPIENT_EMAILS="recipient1@example.com,recipient2@example.com"
   ```
   
   或者创建 `.env` 文件（推荐）：
   
   在项目根目录创建 `.env` 文件，内容如下：
   
   ```bash
   SMTP_SERVER=smtp.office365.com
   SMTP_PORT=587
   SENDER_EMAIL=your_email@outlook.com
   SENDER_PASSWORD=your_smtp_authorization_code
   RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com
   ```
   
   注意：请将 `.env` 添加到 `.gitignore` 文件中，避免将敏感信息提交到版本控制系统。

2. **获取SMTP授权码**：
   - **Outlook邮箱**：登录Outlook → 设置 → 查看所有Outlook设置 → 邮件 → 同步电子邮件 → POP和IMAP → 开启相关服务
   - **163/QQ邮箱**：登录邮箱 → 设置 → 账户设置 → POP3/SMTP/IMAP服务 → 开启SMTP服务 → 获取授权码

3. **测试邮件功能**：
   ```bash
   # 显示SMTP配置说明
   python email_sender.py --instructions
   
   # 测试SMTP连接
   python email_sender.py --test
   
   # 发送测试邮件
   python email_sender.py --send-test
   ```

### 2. 命令行参数

邮件相关命令行参数：

```bash
# 禁用邮件通知
python monitor.py --no-email

# 自定义SMTP配置
python monitor.py --smtp-server smtp.office365.com --smtp-port 587 \
                  --sender-email your_email@outlook.com \
                  --sender-password your_smtp_password \
                  --recipient-emails recipient1@example.com recipient2@example.com

# 发送未发送的历史报告
python monitor.py --send-unsent

# 组合使用
python monitor.py --url https://concito.dk/en/analyser --interval 2 \
                  --sender-email your_email@outlook.com \
                  --sender-password your_smtp_password \
                  --recipient-emails guosong2023@outlook.com
```

### 3. 邮件内容格式

发现新报告时，邮件内容格式如下：

```
【新报告监控】来自concito.dk的新发布

标题：[报告标题]
链接：[报告链接]

发现时间：2024-01-01 12:00:00

---
此邮件由网站监控工具自动发送
```

## 数据库结构

表名：`reports`

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 自增主键 |
| title | TEXT NOT NULL | 报告标题 |
| url | TEXT NOT NULL UNIQUE | 报告链接 |
| source_website | TEXT NOT NULL | 来源网站域名 |
| publish_date | TEXT | 发布日期（可选） |
| discovered_time | TIMESTAMP NOT NULL | 发现时间 |
| sent_status | INTEGER DEFAULT 0 | 邮件发送状态（0=未发送，1=已发送） |

## 项目结构

```
ThinkTank_Monitor/
├── app.py              # Flask Web应用入口
├── monitor.py          # 命令行监控程序入口
├── monitor_service.py  # 监控服务模块（APScheduler集成）
├── website_configs.py  # 多网站配置和解析器
├── scraper.py          # 网页抓取模块
├── db.py               # 数据库操作模块
├── email_sender.py     # 邮件发送模块
├── requirements.txt    # 依赖包列表
├── README.md           # 使用说明
├── start_web.bat       # Windows启动脚本
├── start_web.sh        # Linux/macOS启动脚本
├── templates/          # Web界面HTML模板
│   ├── base.html       # 基础模板
│   ├── index.html      # 首页模板
│   ├── settings.html   # 设置页面模板
│   ├── reports.html    # 报告页面模板
│   └── error.html      # 错误页面模板
└── monitor.log         # 运行时生成的日志文件
```

## 模块说明

### 1. db.py - 数据库管理模块

提供数据库连接、表创建、数据插入和查询功能。

主要类：`DatabaseManager`
- 自动创建数据库表
- 支持重复检查
- 使用上下文管理器确保连接关闭

### 2. scraper.py - 网页抓取模块

提供网页内容获取和报告提取功能。

主要类：`WebsiteScraper`
- 支持自定义User-Agent
- 智能解析报告链接
- 自动过滤导航链接
- 支持多种CSS选择器

### 3. monitor.py - 主监控程序

整合抓取和数据库功能，提供定时监控。

主要类：`WebsiteMonitor`
- 支持单次和连续运行模式
- 可配置检查间隔
- 实时控制台输出
- 邮件通知功能集成
- 完善的错误处理

### 4. email_sender.py - 邮件发送模块

使用SMTP协议发送报告通知邮件。

主要类：`EmailSender`
- 支持Outlook、163、QQ等主流邮箱
- 可配置SMTP服务器和端口
- 支持批量发送和合并通知
- 完善的错误处理和日志记录
- 提供SMTP配置说明和测试功能

### 5. website_configs.py - 多网站配置模块

管理多个网站的监控配置和解析器函数。

主要功能：
- 定义`WebsiteConfig`类表示网站配置
- 提供默认的5个网站配置（CONCITO、WWF、EEB、Green Alliance、Pembina Institute）
- 每个网站有独立的解析器函数处理网站特定结构
- 支持添加、移除和修改网站配置
- 提供`get_all_websites()`函数获取所有配置

### 6. monitor_service.py - 监控服务模块

提供监控服务的核心逻辑和APScheduler任务调度。

主要类：`MonitorService`
- 使用APScheduler进行后台任务调度
- 支持自动启动（基于数据库设置）
- 动态调整检查间隔
- 线程安全的操作（使用锁）
- 提供状态查询、报告获取、设置更新等功能
- 单例模式确保全局唯一实例

主要功能：
- `start_monitoring()`: 启动定时监控任务
- `stop_monitoring()`: 停止监控任务
- `run_once()`: 运行单次检查
- `get_status()`: 获取监控状态和统计信息
- `get_recent_reports()`: 获取最近的报告
- `update_settings()`: 更新邮箱和检查间隔设置

### 7. app.py - Flask Web应用模块

提供Web管理界面的Flask应用。

主要功能：
- 提供RESTful API接口
- 渲染HTML模板页面
- 集成监控服务
- 错误处理和CORS支持

页面路由：
- `/`: 首页（监控状态仪表板）
- `/settings`: 邮箱设置页面
- `/reports`: 报告查看页面
- `/api/*`: 各种API端点

## 错误处理

程序包含完善的错误处理机制：
- 网络请求异常处理
- 数据库操作异常处理
- 解析错误处理
- 日志记录所有异常信息

## 日志系统

程序使用Python标准logging模块，日志同时输出到：
- 控制台：实时显示操作状态
- 文件（monitor.log）：持久化记录所有操作

日志级别：INFO（可修改代码调整为DEBUG查看更多细节）

## 注意事项

1. **网站结构变化**：如果目标网站结构发生变化，可能需要调整`scraper.py`中的解析逻辑
2. **网络连接**：确保运行环境可以访问目标网站
3. **资源占用**：长时间运行会占用少量磁盘空间（数据库和日志文件）
4. **中断恢复**：程序支持Ctrl+C中断，下次运行会继续从数据库已有记录开始

## 多网站监控

### 1. 默认监控的网站

工具默认监控以下五个网站：

1. **CONCITO** (https://concito.dk/en/analyser) - 绿色智库分析报告
2. **WWF** (https://www.worldwildlife.org/news/press-releases/) - 世界自然基金会新闻稿
3. **EEB** (https://eeb.org/en/library/) - 欧洲环境署图书馆（自动处理Cookie弹窗）
4. **Green Alliance** (https://green-alliance.org.uk/) - 英国绿色联盟智库报告
5. **Pembina Institute** (https://www.pembina.org/all) - 加拿大彭比纳研究所报告

### 2. 启用多网站监控

使用 `--multi` 参数启用多网站监控模式：

```bash
# 监控所有默认网站
python monitor.py --multi

# 监控所有默认网站，每2小时检查一次
python monitor.py --multi --interval 2

# 监控所有默认网站，禁用邮件通知
python monitor.py --multi --no-email

# 监控所有默认网站，自定义邮件配置
python monitor.py --multi --sender-email your_email@outlook.com --sender-password your_smtp_password
```

### 3. 自定义网站配置

您可以通过修改 `website_configs.py` 文件来自定义监控的网站：

1. **添加新网站**：
   ```python
   from website_configs import WebsiteConfig, add_website_config
   
   # 创建自定义解析器函数
   def my_custom_parser(html_content: str, base_url: str) -> List[Dict[str, str]]:
       # 解析逻辑...
       pass
   
   # 创建网站配置
   new_config = WebsiteConfig(
       name="MY_SITE",
       url="https://example.com/news",
       parser_func=my_custom_parser
   )
   
   # 添加到配置列表
   add_website_config(new_config)
   ```

2. **移除网站**：
   ```python
   from website_configs import remove_website_config
   
   # 移除WWF网站
   remove_website_config("WWF")
   ```

3. **修改现有解析器**：
   直接编辑 `website_configs.py` 中的解析器函数（`wwf_parser`, `eeb_parser`, `concito_parser`）。

### 4. 网站解析器开发指南

每个网站解析器函数应该：
- 接受 `html_content` (HTML字符串) 和 `base_url` (基础URL) 参数
- 返回报告字典列表，每个字典包含 `title`、`url` 和 `source` 键
- 处理网站特定的结构差异和Cookie弹窗
- 包含适当的错误处理和日志记录

### 5. 统计信息

多网站监控模式下，统计信息会按网站分组显示：

```bash
python monitor.py --multi --stats
```

输出示例：
```
==================================================
多网站监控统计信息
==================================================
数据库文件: reports.db
监控网站数量: 5
邮件通知: 启用
--------------------------------------------------
总报告数量: 35
已发送报告: 30
未发送报告: 5

按网站统计:
  CONCITO: 10 个报告
  WWF: 7 个报告
  EEB: 8 个报告
  Green Alliance: 6 个报告
  Pembina Institute: 4 个报告

最近5个报告:
1. [✓] [CONCITO] 报告标题1
   链接: https://...
   发现时间: 2024-01-01T12:00:00
...
```

### 6. 注意事项

1. **网站结构变化**：不同网站的结构差异很大，可能需要定制解析器
2. **JavaScript渲染**：某些网站可能需要JavaScript渲染（当前版本不支持）
3. **请求频率**：避免过于频繁的请求，尊重网站的robots.txt
4. **错误处理**：单个网站失败不会影响其他网站的监控

## Web界面管理

ThinkTank Monitor 提供了一个基于Flask的Web管理界面，方便用户通过浏览器监控和管理监控任务。

### 1. 界面功能

- **首页仪表板**：显示监控状态（运行/停止）、报告统计信息、最近活动
- **监控控制**：一键启动/停止监控任务，运行单次检查
- **邮箱设置**：配置接收邮件通知的邮箱地址和检查间隔
- **报告查看**：表格展示最近发现的报告，支持分页和搜索
- **实时状态更新**：页面自动刷新监控状态和统计信息

### 2. 技术架构

- **前端**：Bootstrap 5 + jQuery + Font Awesome
- **后端**：Flask + APScheduler
- **任务调度**：APScheduler提供可靠的后台任务调度
- **数据库**：SQLite存储报告和配置信息
- **API设计**：RESTful API支持前后端分离

### 3. 启动Web服务

#### 方法一：直接运行
```bash
python app.py
```

#### 方法二：使用启动脚本
- **Windows**: 双击 `start_web.bat` 或命令行运行 `start_web.bat`
- **Linux/macOS**: 运行 `chmod +x start_web.sh` 然后 `./start_web.sh`

#### 方法三：生产环境部署（建议）
```bash
# 使用Gunicorn（需要额外安装）
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 4. 访问地址

启动成功后，在浏览器中访问：http://127.0.0.1:5000

### 5. 界面截图

#### 首页（仪表板）
![首页截图](docs/images/dashboard.png)

#### 邮箱设置页
![设置截图](docs/images/settings.png)

#### 报告查看页
![报告截图](docs/images/reports.png)

### 6. API接口

Web界面提供了以下API接口：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/status` | GET | 获取监控状态和统计信息 |
| `/api/start` | POST | 启动监控任务 |
| `/api/stop` | POST | 停止监控任务 |
| `/api/run_once` | POST | 运行单次检查 |
| `/api/settings` | GET | 获取当前设置 |
| `/api/settings` | POST | 更新设置（邮箱、检查间隔） |
| `/api/reports` | GET | 获取报告数据 |
| `/api/send_unsent` | POST | 发送未发送的报告邮件 |

### 7. 配置说明

#### 7.1 邮箱配置
1. 访问Web界面 → 邮箱设置页
2. 输入接收邮件的邮箱地址（多个邮箱用逗号分隔）
3. 设置检查间隔（小时）
4. 点击"保存设置"

#### 7.2 监控配置
- **自动启动**：如果上次关闭时监控处于运行状态，重启Web服务后会自动启动监控
- **检查间隔**：可动态调整，调整后立即生效
- **多网站支持**：默认监控5个智库网站，可在`website_configs.py`中添加更多网站

#### 7.3 数据库配置
- 配置文件：`reports.db`（默认）
- 包含两个表：`reports`（报告数据）和`settings`（配置数据）
- 设置信息持久化存储，重启后保留

### 8. 注意事项

1. **首次使用**：需要先配置邮箱设置才能启用邮件通知
2. **SMTP配置**：邮件发送需要正确的SMTP配置，请确保`email_sender.py`中的配置正确
3. **后台任务**：监控任务在后台运行，不会阻塞Web界面
4. **服务重启**：重启Web服务会保持之前的监控状态
5. **安全性**：默认使用开发服务器，生产环境请使用生产级WSGI服务器

### 9. 故障排除

#### 9.1 Web服务无法启动
```bash
# 检查Python版本
python --version

# 检查依赖安装
pip install -r requirements.txt

# 检查端口占用
netstat -ano | findstr :5000  # Windows
lsof -i :5000                 # Linux/macOS
```

#### 9.2 监控任务不运行
1. 检查首页状态是否显示"运行中"
2. 检查邮箱设置是否已配置
3. 查看控制台日志输出
4. 检查数据库文件权限

#### 9.3 邮件发送失败
1. 检查`email_sender.py`中的SMTP配置
2. 运行测试：`python email_sender.py --test`
3. 检查收件人邮箱格式是否正确

## 扩展建议

1. **Web界面**：添加简单的Web界面查看报告
2. **日期解析**：从报告页面中提取发布日期
3. **内容下载**：自动下载报告PDF文件
4. **邮件模板自定义**：允许用户自定义邮件模板和样式
5. **多语言支持**：支持英文邮件通知和多语言界面
6. **JavaScript渲染支持**：使用Selenium或Playwright支持需要JavaScript的网站
7. **API接口**：提供REST API供其他系统调用
8. **智能去重**：使用自然语言处理识别相似报告
9. **优先级排序**：根据关键词或分类为报告设置优先级
10. **定时任务调度**：支持更灵活的定时任务配置

## 许可证

本项目仅供学习和研究使用。