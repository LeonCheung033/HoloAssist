#!/bin/bash
# Docker Compose 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "启动HoloAssist服务容器..."
echo ""

# 检查.env.docker文件是否存在
if [ ! -f .env.docker ]; then
    echo "警告: .env.docker 文件不存在"
    echo "正在从 .env.docker.example 创建..."
    if [ -f .env.docker.example ]; then
        cp .env.docker.example .env.docker
        echo "已创建 .env.docker 文件，请编辑并设置密码"
        echo "然后重新运行此脚本"
        exit 1
    else
        echo "错误: .env.docker.example 文件不存在"
        exit 1
    fi
fi

# 加载环境变量
export $(grep -v '^#' .env.docker | xargs)

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 启动服务
docker-compose --env-file .env.docker up -d

echo ""
echo "等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "服务状态："
docker-compose ps

echo ""
echo "服务已启动！"
echo ""
echo "访问地址："
echo "  - MySQL: localhost:3306"
echo "  - Redis: localhost:6379"
echo "  - Neo4j Browser: http://localhost:7474"
echo "  - Neo4j Bolt: localhost:7687"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
