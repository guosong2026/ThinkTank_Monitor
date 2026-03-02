#!/bin/bash
# ThinkTank Monitor启动脚本（Linux/macOS）
# 适用于Wispbyte等云平台部署

set -e  # 遇到错误时退出

echo "=== ThinkTank Monitor启动脚本 ==="
echo "当前目录: $(pwd)"
echo "Python版本: $(python --version 2>/dev/null || echo '未找到Python')"
echo "Python3版本: $(python3 --version 2>/dev/null || echo '未找到Python3')"

# 检查Python环境
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "错误: 未找到Python环境"
    exit 1
fi

echo "使用Python命令: $PYTHON_CMD"

# 检查依赖
echo "检查依赖安装..."
if [ -f "requirements.txt" ]; then
    echo "安装依赖包..."
    $PYTHON_CMD -m pip install --upgrade pip
    $PYTHON_CMD -m pip install -r requirements.txt
else
    echo "警告: 未找到requirements.txt文件"
fi

# 检查环境变量
echo "环境变量检查:"
echo "  PORT=${PORT:-未设置，使用默认值5000}"
echo "  HOST=${HOST:-未设置，使用默认值127.0.0.1}"

# 检查数据库文件
if [ ! -f "reports.db" ]; then
    echo "提示: 未找到数据库文件，将在首次运行时自动创建"
fi

# 启动应用
echo "启动ThinkTank Monitor Web界面..."
echo "=================================="

# 使用gunicorn作为WSGI服务器（如果已安装）
if $PYTHON_CMD -c "import gunicorn" 2>/dev/null; then
    echo "检测到gunicorn，使用WSGI服务器启动..."
    PORT=${PORT:-5000}
    WORKERS=$(( $(nproc --all) * 2 + 1 ))
    WORKERS=$(( WORKERS > 4 ? 4 : WORKERS ))  # 限制最大worker数
    
    exec gunicorn \
        --bind 0.0.0.0:$PORT \
        --workers $WORKERS \
        --threads 2 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        wsgi:app
else
    echo "警告: 未安装gunicorn，使用Flask开发服务器启动（不适用于生产环境）"
    echo "建议安装gunicorn: pip install gunicorn"
    
    # 设置环境变量
    export FLASK_APP=app.py
    export FLASK_ENV=production
    
    # 启动Flask应用
    exec $PYTHON_CMD wsgi.py
fi