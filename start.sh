#!/bin/bash

# FeetFit Docker服务启动脚本

set -e

echo "🚀 启动 FeetFit 跑步步态分析系统"
echo "=================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 检查docker-compose是否存在
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose未安装"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p docker/postgres/init-scripts
mkdir -p docker/redis
mkdir -p docker/nginx
mkdir -p docker/prometheus
mkdir -p docker/grafana/dashboards
mkdir -p docker/grafana/datasources
mkdir -p logs
mkdir -p data

# 设置权限
chmod +x docker/postgres/start.sh

# 构建并启动服务
echo "🔨 构建Docker镜像..."
docker-compose build --no-cache

echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 显示服务访问信息
echo ""
echo "✅ FeetFit 系统启动完成！"
echo "=================================="
echo "🌐 服务访问地址:"
echo "   - 主应用: http://localhost:8000"
echo "   - API文档: http://localhost:8000/docs"
echo "   - 数据库管理: http://localhost:8080"
echo "   - 监控面板: http://localhost:3000"
echo "   - Prometheus: http://localhost:9090"
echo ""
echo "🔑 默认登录信息:"
echo "   - pgAdmin: admin@feetfit.com / admin123"
echo "   - Grafana: admin / admin123"
echo ""
echo "📝 查看日志: docker-compose logs -f [service_name]"
echo "🛑 停止服务: docker-compose down"
echo "🔄 重启服务: docker-compose restart"
