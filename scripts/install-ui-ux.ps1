#!/usr/bin/env pwsh
<#
UI/UX Pro Max 安装脚本
用于安装 uipro-cli 和设置 UI/UX 环境
#>

Write-Host "=== UI/UX Pro Max 安装脚本 ===" -ForegroundColor Cyan

# 检查 Node.js
Write-Host "检查 Node.js 安装..." -ForegroundColor Yellow
$nodePath = Get-Command node -ErrorAction SilentlyContinue
$npmPath = Get-Command npm -ErrorAction SilentlyContinue

if (-not $nodePath) {
    Write-Host "错误: Node.js 未找到！" -ForegroundColor Red
    Write-Host "请确保 Node.js 已安装并添加到系统 PATH 环境变量中。" -ForegroundColor Yellow
    Write-Host "下载地址: https://nodejs.org/" -ForegroundColor Blue
    exit 1
}

if (-not $npmPath) {
    Write-Host "错误: npm 未找到！" -ForegroundColor Red
    Write-Host "Node.js 安装可能不完整，请重新安装 Node.js。" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Node.js 版本: $(node --version)" -ForegroundColor Green
Write-Host "✓ npm 版本: $(npm --version)" -ForegroundColor Green

# 安装 uipro-cli
Write-Host "`n安装 uipro-cli (全局)..." -ForegroundColor Yellow
try {
    npm install -g uipro-cli
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ uipro-cli 安装成功" -ForegroundColor Green
        
        # 验证安装
        $uiproPath = Get-Command uipro -ErrorAction SilentlyContinue
        if ($uiproPath) {
            Write-Host "✓ uipro 命令可用: $($uiproPath.Source)" -ForegroundColor Green
            Write-Host "  版本信息: $(uipro --version 2>&1)" -ForegroundColor Gray
        } else {
            Write-Host "⚠ uipro 命令未在 PATH 中找到，可能需要重新打开终端" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✗ uipro-cli 安装失败 (退出代码: $LASTEXITCODE)" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ uipro-cli 安装过程中出现错误: $_" -ForegroundColor Red
}

# 检查项目 TRAE 绑定
Write-Host "`n检查 TRAE 项目绑定..." -ForegroundColor Yellow
$traeConfig = ".trae/config.json"
if (Test-Path $traeConfig) {
    Write-Host "✓ TRAE 配置文件存在" -ForegroundColor Green
    $config = Get-Content $traeConfig -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($config) {
        Write-Host "  项目: $($config.project.name)" -ForegroundColor Gray
        Write-Host "  绑定状态: $($config.trae.bound)" -ForegroundColor Gray
        Write-Host "  集成技能: $($config.trae.integrated_skills -join ', ')" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ TRAE 配置文件不存在，运行项目初始化脚本" -ForegroundColor Yellow
}

# 创建 UI/UX 配置文件
Write-Host "`n设置 UI/UX 配置..." -ForegroundColor Yellow
$uiConfig = @{
    project_root = $PWD.Path
    setup_date = Get-Date -Format "yyyy-MM-dd"
    node_version = node --version
    npm_version = npm --version
    uipro_installed = $true
}

$uiConfigPath = ".trae/ui-ux-config.json"
$uiConfig | ConvertTo-Json | Set-Content $uiConfigPath
Write-Host "✓ UI/UX 配置文件已创建: $uiConfigPath" -ForegroundColor Green

Write-Host "`n=== 安装完成 ===" -ForegroundColor Cyan
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "1. 重新打开终端使 uipro 命令生效" -ForegroundColor White
Write-Host "2. 运行 'uipro --help' 查看可用命令" -ForegroundColor White
Write-Host "3. 调用 UI-UX-Pro-Max-Skill 开始美化系统 UI" -ForegroundColor White
Write-Host "`n脚本完成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray