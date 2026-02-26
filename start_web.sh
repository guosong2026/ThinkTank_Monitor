#!/bin/bash

echo "========================================"
echo "ThinkTank Monitor Web界面启动脚本"
echo "========================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

# 检查依赖是否安装
echo "检查Python依赖..."
python3 -c "import flask, requests, bs4, apscheduler" &> /dev/null
if [ $? -ne 0 ]; then
    echo "依赖未安装，正在安装..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "依赖安装失败，请手动运行: pip3 install -r requirements.txt"
        exit 1
    fi
    echo "依赖安装完成。"
else
    echo "依赖检查通过。"
fi

echo
echo "启动ThinkTank Monitor Web界面..."
echo "访问地址: http://127.0.0.1:5000"
echo "按 Ctrl+C 停止服务"
echo
echo "========================================"

# 启动Flask应用
python3 app.py

if [ $? -ne 0 ]; then
    echo
    echo "启动失败，请检查错误信息。"
    exit 1
fi