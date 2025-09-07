#!/bin/bash

# FeetFit Docker服务停止脚本

set -e

echo "🛑 停止 FeetFit 跑步步态分析系统"
echo "=================================="

# 检查docker-compose是否存在
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose未安装"
    exit 1
fi

# 停止所有服务
echo "🛑 停止所有服务..."
docker-compose down

# 可选：清理数据卷（谨慎使用）
read -p "是否要清理所有数据卷？这将删除所有数据 (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️ 清理数据卷..."
    docker-compose down -v
    docker system prune -f
    echo "✅ 数据卷已清理"
else
    echo "📦 数据卷已保留"
fi

echo ""
echo "✅ FeetFit 系统已停止"
echo "🔄 重新启动: ./start.sh"
