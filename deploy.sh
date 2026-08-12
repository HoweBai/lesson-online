#!/bin/bash
# Online Learning Platform - Docker 部署脚本
# 使用方法: ./deploy.sh [up|down|build|logs|restart]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi

    print_success "Docker 环境检查通过"
}

# 检查 .env 文件
check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在，正在从模板创建..."
        cp .env.example .env
        print_warning "请编辑 .env 文件，修改安全密钥和数据库密码"
    fi

    # 检查必要的环境变量
    if ! grep -q "^SECRET_KEY=" .env 2>/dev/null || [ "$(grep '^SECRET_KEY=' .env | cut -d'=' -f2)" = "your-secret-key-change-in-production" ]; then
        print_warning "请修改 .env 文件中的 SECRET_KEY"
    fi

    if ! grep -q "^POSTGRES_PASSWORD=" .env 2>/dev/null || [ "$(grep '^POSTGRES_PASSWORD=' .env | cut -d'=' -f2)" = "your-postgres-password-change-me" ]; then
        print_warning "请修改 .env 文件中的 POSTGRES_PASSWORD"
    fi
}

# 启动服务
start() {
    print_info "正在启动服务..."
    docker compose up -d --build

    print_info "等待服务启动..."
    sleep 10

    print_info "检查服务状态..."
    docker compose ps

    print_success "服务启动完成！"
    echo ""
    print_info "访问地址:"
    print_info "  主站:     http://localhost"
    print_info "  API文档:  http://localhost:8000/docs"
    print_info "  健康检查: http://localhost:8000/health"
    print_info "  MinIO:    http://localhost:9001"
}

# 停止服务
stop() {
    print_info "正在停止服务..."
    docker compose down
    print_success "服务已停止"
}

# 重启服务
restart() {
    print_info "正在重启服务..."
    docker compose restart
    print_success "服务已重启"
}

# 查看日志
logs() {
    if [ "$1" = "-f" ]; then
        docker compose logs -f "$2"
    else
        docker compose logs "$2"
    fi
}

# 构建镜像
build() {
    print_info "正在构建镜像..."
    docker compose build --no-cache
    print_success "镜像构建完成"
}

# 进入容器
exec_container() {
    local container=$1
    if [ -z "$container" ]; then
        print_error "请指定容器名称 (backend, frontend, db, redis, minio, worker)"
        exit 1
    fi
    docker compose exec "$container" bash
}

# 显示帮助
show_help() {
    echo "Online Learning Platform - Docker 部署脚本"
    echo ""
    echo "使用方法:"
    echo "  ./deploy.sh [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  up        - 启动所有服务 (默认)"
    echo "  down      - 停止所有服务"
    echo "  restart   - 重启所有服务"
    echo "  build     - 重新构建镜像"
    echo "  logs      - 查看日志 (可选: -f 跟随, 服务名)"
    echo "  exec      - 进入容器 (需要指定容器名)"
    echo "  help      - 显示此帮助"
    echo ""
    echo "示例:"
    echo "  ./deploy.sh up"
    echo "  ./deploy.sh logs -f backend"
    echo "  ./deploy.sh exec db"
}

# 主函数
main() {
    local command=${1:-up}

    case $command in
        up)
            check_docker
            check_env
            start
            ;;
        down)
            stop
            ;;
        restart)
            restart
            ;;
        build)
            build
            ;;
        logs)
            logs "${@:2}"
            ;;
        exec)
            exec_container "$2"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行
main "$@"
