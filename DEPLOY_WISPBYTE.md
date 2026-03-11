# ThinkTank Monitor 部署到 Wispbyte 指南

## 📋 概述

本文档详细介绍了如何将 ThinkTank Monitor 项目从 GitHub 部署到 Wispbyte 平台。Wispbyte 是一个提供免费 24/7 托管的平台，主要面向 Discord bot 和游戏服务器托管，但也支持通用 Python 应用。

## 🔧 项目准备

### 1. 代码调整已完成

我已经为 Wispbyte 部署调整了代码：

1. **WSGI 入口点**：创建了 `wsgi.py` 文件，支持环境变量 `PORT` 和 `HOST`
2. **启动脚本**：创建了 `start.sh`（Linux）和 `start.bat`（Windows）启动脚本
3. **环境变量支持**：修改了 `app.py` 以从环境变量读取配置
4. **网络连接优化**：修复了代理配置问题，添加了重试机制和连接池优化

### 2. 文件结构

```
ThinkTank_Monitor/
├── app.py                 # Flask 主应用（已适配环境变量）
├── wsgi.py               # WSGI 入口点（生产环境使用）
├── start.sh              # Linux 启动脚本
├── start.bat             # Windows 启动脚本
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量示例
├── templates/            # HTML 模板
├── static/              # 静态文件
├── *.py                 # 其他核心模块
└── DEPLOY_WISPBYTE.md   # 本部署指南
```

## 🚀 部署到 Wispbyte

### 方法一：通过 GitHub 部署（推荐）

Wispbyte 可能支持直接从 GitHub 仓库部署：

1. **登录 Wispbyte 控制台**
   - 访问 [wispbyte.com](https://wispbyte.com)
   - 注册/登录账户

2. **创建新项目**
   - 选择 "Generic Hosting" 或 "Python App"
   - 选择 "Deploy from GitHub" 选项

3. **连接 GitHub 仓库**
   - 授权 Wispbyte 访问你的 GitHub 账户
   - 选择仓库：`你的用户名/ThinkTank_Monitor`
   - 选择分支：`main` 或 `master`

4. **配置部署设置**
   - **启动命令**：`python wsgi.py` 或 `bash start.sh`
   - **Python 版本**：选择 Python 3.9+（推荐 Python 3.10）
   - **端口**：通常自动检测，如未设置使用 `5000`
   - **环境变量**：添加以下变量（根据实际情况调整）：

     ```bash
     # 邮件配置（必需）
     EMAIL_PROVIDER=smtp
     SMTP_SERVER=smtp.office365.com
     SMTP_PORT=587
     SENDER_EMAIL=your_email@outlook.com
     SENDER_PASSWORD=your_smtp_password
     RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com
     
     # 应用配置（可选）
     HOST=0.0.0.0
     PORT=5000
     CHECK_INTERVAL_HOURS=2
     MONITOR_ENABLED=1
     ```

5. **开始部署**
   - 点击 "Deploy" 或 "Start" 按钮
   - 等待构建和部署完成

### 方法二：手动上传项目

如果 Wispbyte 支持手动上传：

1. **准备部署包**
   ```bash
   # 克隆或下载项目
   git clone https://github.com/你的用户名/ThinkTank_Monitor.git
   cd ThinkTank_Monitor
   
   # 确保所有文件已提交
   git add .
   git commit -m "准备部署到 Wispbyte"
   git push
   ```

2. **创建部署包（可选）**
   ```bash
   # 创建 ZIP 文件（排除不需要的文件）
   zip -r deploy.zip . -x "*.git*" "*.pyc" "__pycache__/*" "venv/*" ".env"
   ```

3. **上传到 Wispbyte**
   - 在 Wispbyte 控制台选择 "Upload Project"
   - 上传 ZIP 文件或通过 Git 链接
   - 配置启动命令和环境变量

4. **启动应用**
   - 确认配置后启动应用
   - 检查日志确认应用正常运行

## ⚙️ 环境变量配置

### 必需的环境变量

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `EMAIL_PROVIDER` | 邮件提供商 | `smtp` |
| `SMTP_SERVER` | SMTP 服务器地址 | `smtp.office365.com` |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SENDER_EMAIL` | 发件人邮箱 | `your_email@outlook.com` |
| `SENDER_PASSWORD` | SMTP 授权码 | `your_password` |
| `RECIPIENT_EMAILS` | 收件人邮箱列表 | `email1@example.com,email2@example.com` |

### 可选的环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HOST` | 监听主机 | `0.0.0.0` |
| `PORT` | 监听端口 | `5000` |
| `CHECK_INTERVAL_HOURS` | 检查间隔（小时） | `2` |
| `MONITOR_ENABLED` | 监控启用状态 | `1` |

## 🔍 部署验证

### 1. 检查应用状态

部署完成后，检查：

1. **应用日志**：查看启动日志，确认无错误
2. **Web 界面**：访问 `https://你的应用.wispbyte.com` 或分配的 URL
3. **API 状态**：访问 `https://你的应用.wispbyte.com/api/status`

### 2. 测试监控功能

1. **手动运行检查**：
   - 在 Web 界面点击 "运行单次检查"
   - 或调用 API：`POST /api/run_once`

2. **检查数据库**：
   - 应用会自动创建 `reports.db` 数据库文件
   - 确认可以正常存储和检索报告

3. **测试邮件发送**：
   - 在 Web 界面设置页面发送测试邮件
   - 确认收件箱收到测试邮件

### 3. 验证网络连接

由于 PythonAnywhere 存在网络限制，Wispbyte 应该能正常访问外部网站。测试：

```bash
# 使用诊断工具
python diagnose_network.py
```

## 🛠️ 故障排除

### 常见问题

#### 1. 应用启动失败
- **错误**：`ModuleNotFoundError`
- **解决**：确保 `requirements.txt` 正确，依赖已安装
- **操作**：检查部署日志，手动安装缺失包

#### 2. 端口冲突
- **错误**：`Address already in use`
- **解决**：检查 `PORT` 环境变量，使用平台分配的端口
- **操作**：在 Wispbyte 设置中调整端口配置

#### 3. 数据库写入失败
- **错误**：`read-only file system` 或权限错误
- **解决**：Wispbyte 可能有文件系统限制
- **操作**：确认数据库文件可写入，或使用内存数据库

#### 4. 邮件发送失败
- **错误**：SMTP 连接失败
- **解决**：Wispbyte 可能限制出站 SMTP 连接
- **操作**：
  - 检查 SMTP 服务器配置是否正确
  - 确认端口 587 或 465 是否被 Wispbyte 防火墙允许
  - 尝试使用不同的 SMTP 服务器（如 smtp.163.com 或 smtp.qq.com）

#### 5. 网络连接失败
- **错误**：`Connection refused` 或 `Network unreachable`
- **解决**：Wispbyte 可能也有网络限制
- **操作**：
  - 使用我们添加的重试机制
  - 检查目标网站是否屏蔽 Wispbyte IP
  - 考虑使用代理（如果平台允许）

### 日志检查

- **应用日志**：在 Wispbyte 控制台查看
- **错误跟踪**：检查 Flask 错误日志
- **监控日志**：查看 `monitor.log` 文件（如果启用）

## 🔄 更新部署

### 通过 GitHub 自动更新

如果配置了 GitHub 集成：

1. **推送代码到仓库**
   ```bash
   git add .
   git commit -m "更新功能"
   git push origin main
   ```

2. **触发重新部署**
   - Wispbyte 可能自动检测并重新部署
   - 或手动在控制台触发重新部署

### 手动更新

1. **重新上传项目**
   - 上传新的 ZIP 文件
   - 或重新连接 GitHub 仓库并部署

2. **重启应用**
   - 在控制台重启应用实例
   - 应用会自动加载最新代码

## 📞 获取帮助

### Wispbyte 支持
- **官方网站**：[wispbyte.com](https://wispbyte.com)
- **Discord 社区**：[wispbyte.com/discord](https://wispbyte.com/discord)
- **文档**：查看平台帮助文档

### 项目支持
- **GitHub Issues**：报告代码问题
- **邮件配置帮助**：参考 `.env.example` 文件
- **网络诊断**：使用 `diagnose_network.py` 工具

## 🎯 最佳实践

1. **使用环境变量**：不要将敏感信息硬编码在代码中
2. **定期备份**：定期备份 `reports.db` 数据库文件
3. **监控日志**：定期检查应用日志，及时发现和解决问题
4. **测试部署**：在更新前在测试环境验证更改
5. **使用版本控制**：所有代码更改通过 Git 管理

## ✅ 成功部署标志

- [ ] Web 界面可正常访问
- [ ] API 接口返回正确状态
- [ ] 监控任务可正常启动和停止
- [ ] 网站抓取功能正常工作
- [ ] 邮件发送功能正常
- [ ] 数据库可正常读写
- [ ] 定时任务按计划执行

---

**祝您部署顺利！如果遇到问题，请参考故障排除部分或联系支持。**