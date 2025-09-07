#!/bin/bash

# 前端服务启动脚本
echo "🎨 启动Next.js前端服务器 (端口 3060)..."

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

# 启动开发服务器
npm run dev
