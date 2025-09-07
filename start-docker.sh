#!/bin/bash
# 足底压力可视化系统 - Docker启动脚本
# 创建时间: 2025-01-14

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否运行
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker未运行，请先启动Docker"
        exit 1
    fi
    log_success "Docker运行正常"
}

# 检查docker-compose是否可用
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        log_error "docker-compose未安装，请先安装docker-compose"
        exit 1
    fi
    log_success "docker-compose可用"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    mkdir -p logs/feetfit
    mkdir -p data/testData
    log_success "目录创建完成"
}

# 停止并清理现有容器
cleanup_containers() {
    log_info "停止并清理现有容器..."
    docker-compose down --remove-orphans
    log_success "容器清理完成"
}

# 构建并启动服务
start_services() {
    log_info "构建并启动服务..."
    docker-compose up --build -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    check_services_health
}

# 检查服务健康状态
check_services_health() {
    log_info "检查服务健康状态..."
    
    # 检查数据库
    if docker-compose exec -T db pg_isready -U holistic_user -d holistic_db > /dev/null 2>&1; then
        log_success "数据库服务正常"
    else
        log_warning "数据库服务未就绪，请稍后检查"
    fi
    
    # 检查后端API
    sleep 5
    if curl -f http://localhost:3080/health > /dev/null 2>&1; then
        log_success "后端API服务正常"
    else
        log_warning "后端API服务未就绪，请稍后检查"
    fi
    
    # 检查前端
    sleep 5
    if curl -f http://localhost:3060 > /dev/null 2>&1; then
        log_success "前端服务正常"
    else
        log_warning "前端服务未就绪，请稍后检查"
    fi
}

# 显示服务信息
show_service_info() {
    echo ""
    log_info "=== 足底压力可视化系统 - 服务信息 ==="
    echo ""
    echo "🗄️  数据库服务:"
    echo "   - 容器内端口: 5432"
    echo "   - 宿主机端口: 15432"
    echo "   - 连接命令: psql -h localhost -p 15432 -U holistic_user -d holistic_db"
    echo ""
    echo "🔧 后端API服务:"
    echo "   - 端口: 3080"
    echo "   - 健康检查: http://localhost:3080/health"
    echo "   - API文档: http://localhost:3080/docs"
    echo ""
    echo "🌐 前端Web服务:"
    echo "   - 端口: 3060"
    echo "   - 访问地址: http://localhost:3060"
    echo ""
    echo "📁 代码挂载:"
    echo "   - 项目根目录 -> 后端容器:/app"
    echo "   - pressure-viz-web -> 前端容器:/app"
    echo ""
    echo "📋 常用命令:"
    echo "   - 查看日志: docker-compose logs -f [service_name]"
    echo "   - 停止服务: docker-compose down"
    echo "   - 重启服务: docker-compose restart [service_name]"
    echo "   - 进入容器: docker-compose exec [service_name] bash"
    echo ""
}

# 显示帮助信息
show_help() {
    echo "足底压力可视化系统 - Docker启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  start     启动所有服务（默认）"
    echo "  stop      停止所有服务"
    echo "  restart   重启所有服务"
    echo "  logs      查看所有服务日志"
    echo "  status    查看服务状态"
    echo "  clean     清理所有容器和镜像"
    echo "  help      显示此帮助信息"
    echo ""
}

# 主函数
main() {
    case "${1:-start}" in
        start)
            log_info "启动足底压力可视化系统..."
            check_docker
            check_docker_compose
            create_directories
            cleanup_containers
            start_services
            show_service_info
            ;;
        stop)
            log_info "停止足底压力可视化系统..."
            docker-compose down
            log_success "系统已停止"
            ;;
        restart)
            log_info "重启足底压力可视化系统..."
            docker-compose restart
            log_success "系统已重启"
            ;;
        logs)
            docker-compose logs -f
            ;;
        status)
            docker-compose ps
            ;;
        clean)
            log_warning "这将删除所有容器、镜像和数据卷！"
            read -p "确认继续？(y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker-compose down -v --rmi all
                log_success "清理完成"
            else
                log_info "取消清理操作"
            fi
            ;;
        help)
            show_help
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
