@echo off
echo ========================================
echo ThinkTank Monitor Web界面启动脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

REM 检查依赖是否安装
echo 检查Python依赖...
python -c "import flask, requests, bs4, apscheduler" >nul 2>&1
if errorlevel 1 (
    echo 依赖未安装，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 依赖安装失败，请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo 依赖安装完成。
) else (
    echo 依赖检查通过。
)

echo.
echo 启动ThinkTank Monitor Web界面...
echo 访问地址: http://127.0.0.1:5000
echo 按 Ctrl+C 停止服务
echo.
echo ========================================

REM 启动Flask应用
python app.py

if errorlevel 1 (
    echo.
    echo 启动失败，请检查错误信息。
    pause
)