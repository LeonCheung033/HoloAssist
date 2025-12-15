# Docker Compose 配置说明

## 服务说明

本docker-compose.yml配置了项目所需的三个服务：

1. **MySQL 8.0** - 主数据库
2. **Redis 8-alpine** - 缓存服务
3. **Neo4j 5-community** - 图数据库

## 使用方法

### 1. 配置环境变量

首先复制环境变量模板文件：

```bash
cd docker
cp .env.docker.example .env.docker
```

编辑 `.env.docker` 文件，设置你的密码：

```bash
# MySQL配置
MYSQL_ROOT_PASSWORD=your-secure-password
MYSQL_PASSWORD=your-secure-password

# Redis配置
REDIS_PASSWORD=your-secure-password

# Neo4j配置
NEO4J_PASSWORD=your-secure-password
```

**重要**: `.env.docker` 文件已被 `.gitignore` 忽略，不会被提交到仓库。

### 2. 启动所有服务

```bash
cd docker
./start.sh

# 或手动启动
docker-compose --env-file .env.docker up -d
```

### 查看服务状态

```bash
docker-compose --env-file .env.docker ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose --env-file .env.docker logs -f

# 查看特定服务日志
docker-compose --env-file .env.docker logs -f mysql
docker-compose --env-file .env.docker logs -f redis
docker-compose --env-file .env.docker logs -f neo4j
```

### 停止服务

```bash
./stop.sh

# 或手动停止
docker-compose --env-file .env.docker down
```

### 停止并删除数据卷（谨慎使用）

```bash
docker-compose --env-file .env.docker down -v
```

## 服务端口

- **MySQL**: `localhost:3306`
- **Redis**: `localhost:6379`
- **Neo4j HTTP**: `http://localhost:7474`
- **Neo4j Bolt**: `localhost:7687`

## 环境变量配置

确保项目根目录的 `.env` 文件中的配置与 `docker/.env.docker` 中的服务配置一致：

```env
# Database settings
DB_HOST=localhost  # 或使用 docker 服务名 mysql
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-mysql-password  # 与 docker/.env.docker 中的 MYSQL_PASSWORD 一致
DB_NAME=holoassist

# Neo4j settings
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-neo4j-password  # 与 docker/.env.docker 中的 NEO4J_PASSWORD 一致
NEO4J_DATABASE=neo4j

# Redis settings
REDIS_HOST=localhost  # 或使用 docker 服务名 redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password  # 与 docker/.env.docker 中的 REDIS_PASSWORD 一致
REDIS_CACHE_EXPIRE=3600
REDIS_CACHE_THRESHOLD=0.8
```

## 数据持久化

所有数据都保存在Docker volumes中：
- `mysql_data` - MySQL数据
- `redis_data` - Redis数据
- `neo4j_data` - Neo4j数据
- `neo4j_logs` - Neo4j日志
- `neo4j_import` - Neo4j导入目录
- `neo4j_plugins` - Neo4j插件目录

## 健康检查

所有服务都配置了健康检查，可以使用以下命令查看：

```bash
docker-compose ps
```

## 注意事项

1. 首次启动Neo4j可能需要一些时间来初始化
2. 确保端口3306、6379、7474、7687没有被其他服务占用
3. 如果需要在容器内连接其他服务，可以使用服务名（mysql、redis、neo4j）而不是localhost
