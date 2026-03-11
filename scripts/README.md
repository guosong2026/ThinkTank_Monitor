# UI/UX Pro Max 安装脚本

此目录包含 UI/UX Pro Max 技能的安装和验证脚本。

## 文件说明

- `install-ui-ux.ps1` - 主安装脚本，安装 uipro-cli 并配置环境
- `verify-installation.ps1` - 验证脚本，检查所有组件是否正确安装

## 安装步骤

### 1. 前提条件
- 已安装 Node.js（版本 14 或更高）
- Node.js 已添加到系统 PATH 环境变量
- PowerShell 5.0 或更高版本

### 2. 运行安装脚本
以管理员身份打开 PowerShell，导航到项目根目录，然后运行：
```powershell
.\scripts\install-ui-ux.ps1
```

### 3. 验证安装
安装完成后，运行验证脚本检查安装状态：
```powershell
.\scripts\verify-installation.ps1
```

## 故障排除

### Node.js 未找到
```
错误: Node.js 未找到！
```
解决方案：
1. 确认 Node.js 已安装
2. 将 Node.js 安装目录（如 `C:\Program Files\nodejs`）添加到系统 PATH
3. 重新打开终端窗口

### PowerShell 执行策略限制
```
无法加载文件，因为在此系统上禁止运行脚本
```
解决方案：
以管理员身份运行 PowerShell，然后执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### uipro-cli 安装失败
可能的原因：
1. 网络连接问题
2. npm 注册表访问问题
3. 权限不足（尝试以管理员身份运行）

## 使用技能

安装完成后，可以在 TRAE IDE 中调用 `ui-ux-pro-max` 技能来美化系统 UI。

技能将提供以下功能：
- 优化监控页面布局
- 改进报告列表显示
- 添加可视化图表
- 增强用户体验

## 注意事项

1. 安装脚本需要互联网连接以下载 npm 包
2. 某些操作可能需要管理员权限
3. 安装完成后建议重启 TRAE IDE 以确保技能完全加载