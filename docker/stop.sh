#!/bin/bash
# Docker Compose 停止脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 如果.env.docker存在，加载环境变量
if [ -f .env.docker ]; then
    export $(grep -v '^#' .env.docker | xargs)
fi

echo "停止HoloAssist服务容器..."
if [ -f .env.docker ]; then
    docker-compose --env-file .env.docker down
else
    docker-compose down
fi

echo ""
echo "服务已停止"
