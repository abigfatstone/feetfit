#!/bin/bash

# 后端服务启动脚本
echo "🔧 启动Python后端服务器..."

# 进入后端目录
cd "$(dirname "$0")/backend"

# 激活虚拟环境
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

# 安装依赖
echo "安装Python依赖..."
pip install -r requirements.txt

# 启动服务器
echo "启动FastAPI服务器 (端口 3080)..."
python main.py
