#!/bin/bash

# 系统状态检查脚本

echo "🔍 检查足底压力可视化系统状态..."
echo "=================================="

# 检查后端服务
echo "📡 后端服务状态:"
if curl -s http://localhost:3080/health > /dev/null; then
    echo "✅ 后端服务运行正常 (端口 3080)"
    BACKEND_STATUS=$(curl -s http://localhost:3080/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    echo "   状态: $BACKEND_STATUS"
else
    echo "❌ 后端服务未运行"
fi

echo ""

# 检查前端服务
echo "🎨 前端服务状态:"
if curl -s -I http://localhost:3060 > /dev/null 2>&1; then
    echo "✅ 前端服务运行正常 (端口 3060)"
else
    echo "❌ 前端服务未运行"
fi

echo ""

# 检查进程
echo "🔧 运行进程:"
BACKEND_PID=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $2}')
FRONTEND_PID=$(ps aux | grep "next.*dev" | grep -v grep | awk '{print $2}')

if [ ! -z "$BACKEND_PID" ]; then
    echo "✅ 后端进程运行中 (PID: $BACKEND_PID)"
else
    echo "❌ 后端进程未找到"
fi

if [ ! -z "$FRONTEND_PID" ]; then
    echo "✅ 前端进程运行中 (PID: $FRONTEND_PID)"
else
    echo "❌ 前端进程未找到"
fi

echo ""

# 检查API接口
echo "🔌 API接口测试:"
if curl -s http://localhost:3080/api/sensor-layout > /dev/null; then
    echo "✅ 传感器布局接口正常"
else
    echo "❌ 传感器布局接口异常"
fi

if curl -s http://localhost:3080/api/data-options > /dev/null; then
    echo "✅ 数据选项接口正常"
else
    echo "❌ 数据选项接口异常"
fi

echo ""
echo "=================================="
echo "🌐 访问地址:"
echo "   前端: http://localhost:3060"
echo "   后端: http://localhost:3080"
echo "   API文档: http://localhost:3080/docs"
