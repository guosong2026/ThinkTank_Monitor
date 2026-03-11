#!/usr/bin/env pwsh
<#
UI/UX Pro Max 安装验证脚本
验证所有组件是否已正确安装和配置
#>

Write-Host "=== UI/UX Pro Max 安装验证 ===" -ForegroundColor Cyan
$allPassed = $true

# 1. 检查技能目录
Write-Host "`n1. 检查技能目录..." -ForegroundColor Yellow
$skillDir = ".trae/skills/ui-ux-pro-max"
$skillFile = "$skillDir/SKILL.md"
if (Test-Path $skillDir -PathType Container) {
    Write-Host "  ✓ 技能目录存在: $skillDir" -ForegroundColor Green
    if (Test-Path $skillFile) {
        Write-Host "  ✓ 技能文件存在: $skillFile" -ForegroundColor Green
    } else {
        Write-Host "  ✗ 技能文件不存在: $skillFile" -ForegroundColor Red
        $allPassed = $false
    }
} else {
    Write-Host "  ✗ 技能目录不存在: $skillDir" -ForegroundColor Red
    $allPassed = $false
}

# 2. 检查 TRAE 配置文件
Write-Host "`n2. 检查 TRAE 配置文件..." -ForegroundColor Yellow
$traeConfig = ".trae/config.json"
if (Test-Path $traeConfig) {
    Write-Host "  ✓ TRAE 配置文件存在: $traeConfig" -ForegroundColor Green
    try {
        $config = Get-Content $traeConfig -Raw | ConvertFrom-Json -ErrorAction Stop
        if ($config.trae.bound -eq $true) {
            Write-Host "  ✓ TRAE 绑定状态: 已绑定" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ TRAE 绑定状态: 未绑定" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⚠ TRAE 配置文件格式错误: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ TRAE 配置文件不存在: $traeConfig" -ForegroundColor Red
    $allPassed = $false
}

# 3. 检查安装脚本
Write-Host "`n3. 检查安装脚本..." -ForegroundColor Yellow
$installScript = "scripts/install-ui-ux.ps1"
if (Test-Path $installScript) {
    Write-Host "  ✓ 安装脚本存在: $installScript" -ForegroundColor Green
} else {
    Write-Host "  ✗ 安装脚本不存在: $installScript" -ForegroundColor Red
    $allPassed = $false
}

# 4. 检查 Node.js 环境
Write-Host "`n4. 检查 Node.js 环境..." -ForegroundColor Yellow
$nodePath = Get-Command node -ErrorAction SilentlyContinue
$npmPath = Get-Command npm -ErrorAction SilentlyContinue

if ($nodePath) {
    Write-Host "  ✓ Node.js 已安装: $(node --version 2>&1)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Node.js 未在 PATH 中找到" -ForegroundColor Yellow
    Write-Host "    注意: 需要 Node.js 来运行 uipro-cli" -ForegroundColor Gray
}

if ($npmPath) {
    Write-Host "  ✓ npm 已安装: $(npm --version 2>&1)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ npm 未在 PATH 中找到" -ForegroundColor Yellow
}

# 5. 检查 uipro-cli
Write-Host "`n5. 检查 uipro-cli..." -ForegroundColor Yellow
$uiproPath = Get-Command uipro -ErrorAction SilentlyContinue
if ($uiproPath) {
    Write-Host "  ✓ uipro-cli 已安装: $($uiproPath.Source)" -ForegroundColor Green
    Write-Host "    版本: $(uipro --version 2>&1)" -ForegroundColor Gray
} else {
    Write-Host "  ⚠ uipro-cli 未在 PATH 中找到" -ForegroundColor Yellow
    Write-Host "    运行安装脚本: .\scripts\install-ui-ux.ps1" -ForegroundColor Gray
}

# 总结
Write-Host "`n=== 验证结果 ===" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "✓ 所有核心组件已正确配置" -ForegroundColor Green
    Write-Host "  可以调用 UI-UX-Pro-Max-Skill 开始美化系统 UI" -ForegroundColor White
} else {
    Write-Host "⚠ 部分组件配置不完整" -ForegroundColor Yellow
    Write-Host "  请运行安装脚本: .\scripts\install-ui-ux.ps1" -ForegroundColor White
}

Write-Host "`n验证完成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray