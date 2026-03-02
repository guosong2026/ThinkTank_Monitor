@echo off
REM ThinkTank Monitor启动脚本（Windows）
REM 适用于本地测试和Windows服务器部署

echo === ThinkTank Monitor启动脚本 ===
echo 当前目录: %cd%
echo Python版本: 
python --version 2>nul || echo 未找到Python

REM 检查Python环境
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到Python环境
    pause
    exit /b 1
)

REM 检查依赖
echo 检查依赖安装...
if exist requirements.txt (
    echo 安装依赖包...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
) else (
    echo 警告: 未找到requirements.txt文件
)

REM 检查环境变量
echo 环境变量检查:
if defined PORT (
    echo   PORT=%PORT%
) else (
    echo   PORT=未设置，使用默认值5000
)
if defined HOST (
    echo   HOST=%HOST%
) else (
    echo   HOST=未设置，使用默认值127.0.0.1
)

REM 检查数据库文件
if not exist reports.db (
    echo 提示: 未找到数据库文件，将在首次运行时自动创建
)

REM 启动应用
echo 启动ThinkTank Monitor Web界面...
echo ==================================

REM 设置环境变量
set FLASK_APP=app.py
set FLASK_ENV=production

REM 启动Flask应用
REM Windows环境下通常不使用gunicorn，直接使用Flask开发服务器
echo 使用Flask开发服务器启动...
python wsgi.py

pause