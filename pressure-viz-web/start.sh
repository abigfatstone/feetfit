#!/bin/bash

# 足底压力可视化系统启动脚本
# 前端端口: 3060, 后端端口: 3080

echo "🚀 启动足底压力可视化系统..."

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装 Python3"
    exit 1
fi

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js"
    exit 1
fi

# 安装Python依赖
echo "📦 安装Python后端依赖..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

# 启动后端服务器
echo "🔧 启动Python后端服务器 (端口 3080)..."
python main.py &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "⏳ 等待后端服务器启动..."
sleep 5

# 检查后端是否启动成功
if curl -s http://localhost:3080/health > /dev/null; then
    echo "✅ 后端服务器启动成功 (PID: $BACKEND_PID)"
else
    echo "❌ 后端服务器启动失败，请检查数据库连接"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 启动前端开发服务器
echo "🎨 启动Next.js前端服务器 (端口 3060)..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "🎉 系统启动完成!"
echo "📱 前端地址: http://localhost:3060"
echo "🔌 后端API: http://localhost:3080"
echo "📊 API文档: http://localhost:3080/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap 'echo "🛑 正在停止服务..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' INT

# 保持脚本运行
wait
