# Online Learning Platform - Docker 部署指南

## 🚀 快速开始

### 1. 环境准备

确保已安装以下工具：
- Docker 20.10+
- Docker Compose v2.x+

### 2. 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，修改安全密钥
vim .env
```

**重要**: 务必修改以下配置：
- `SECRET_KEY` - JWT 密钥
- `CRYPTO_KEY_HEX` - 加密密钥
- `POSTGRES_PASSWORD` - 数据库密码
- `MINIO_SECRET_KEY` - MinIO 密钥

### 3. 启动服务

```bash
# 构建并启动所有服务
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 4. 访问应用

启动完成后，访问以下地址：

| 服务 | 地址 |
|------|------|
| 主站 | http://localhost |
| API 文档 | http://localhost/docs |
| 健康检查 | http://localhost/health |
| MinIO 控制台 | http://localhost:9001 |

## 📋 服务架构

```
┌─────────────────────────────────────────────────────────┐
│                      Nginx (Port 80)                     │
│  • 反向代理                                              │
│  • SSL 终止（可选）                                      │
│  • 静态文件服务                                          │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Backend     │ │   Frontend    │ │  Celery       │
│   (Port 8000) │ │   (Port 3000) │ │   Worker      │
│   FastAPI     │ │   React       │ │   Celery      │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    数据层服务                             │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL (5432)  │  Redis (6379)  │  MinIO (9000)   │
│  持久化存储          │  缓存/消息队列  │  对象存储        │
└─────────────────────────────────────────────────────────┘
```

## 🔧 常用命令

### 服务管理

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重启服务
docker compose restart

# 重启单个服务
docker compose restart backend

# 停止并删除容器（保留数据卷）
docker compose down

# 停止并删除所有（包括数据卷）
docker compose down -v
```

### 日志查看

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# 查看最近100行
docker compose logs --tail=100 -f
```

### 进入容器

```bash
# 进入后端容器
docker compose exec backend bash

# 进入数据库容器
docker compose exec db bash

# 执行数据库迁移
docker compose exec backend python src/initdb.py

# 进入 Redis CLI
docker compose exec redis redis-cli
```

### 构建与更新

```bash
# 重新构建所有镜像
docker compose build

# 重新构建并启动
docker compose up -d --build

# 构建时不使用缓存
docker compose build --no-cache

# 更新镜像
docker compose pull
docker compose up -d
```

### 数据库管理

```bash
# 备份数据库
docker compose exec db pg_dump -U ollp_user ollp_db > backup.sql

# 恢复数据库
cat backup.sql | docker compose exec -T db psql -U ollp_user ollp_db

# 查看数据库状态
docker compose exec db psql -U ollp_user ollp_db -c "\dt"
```

### MinIO 管理

```bash
# 创建桶
docker compose exec minio mc mb minio/tutorials

# 设置权限
docker compose exec minio mc policy set download minio/tutorials
```

## 🔐 安全配置

### 1. 修改默认密码

务必修改 `.env` 文件中的所有默认密码：
- `POSTGRES_PASSWORD`
- `MINIO_SECRET_KEY`
- `SECRET_KEY`
- `CRYPTO_KEY_HEX`

### 2. 配置 HTTPS（生产环境）

```bash
# 生成自签名证书（测试用）
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/server.key \
  -out nginx/ssl/server.crt \
  -subj "/CN=yourdomain.com"

# 修改 nginx.conf 添加 SSL 配置
```

### 3. 防火墙规则

```bash
# 只开放必要端口
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## 📊 监控与维护

### 查看资源使用

```bash
# 查看所有容器资源使用
docker compose stats

# 查看系统资源
docker system df
```

### 清理资源

```bash
# 清理未使用的资源
docker system prune -a

# 清理特定服务日志
docker compose logs --tail=0 backend > /dev/null
```

### 健康检查

```bash
# 检查所有服务健康状态
docker compose ps

# 手动测试健康检查
curl http://localhost/health
```

## 🐛 故障排查

### 问题1: 服务启动失败

```bash
# 查看详细日志
docker compose logs backend

# 检查端口占用
netstat -tlnp | grep :80

# 重启服务
docker compose restart
```

### 问题2: 数据库连接失败

```bash
# 检查数据库状态
docker compose ps db

# 查看数据库日志
docker compose logs db

# 检查连接字符串
docker compose exec backend env | grep DATABASE
```

### 问题3: 前端无法访问

```bash
# 检查前端构建日志
docker compose logs frontend

# 重新构建前端
docker compose build frontend
docker compose up -d frontend
```

### 问题4: Celery 任务不执行

```bash
# 检查 Worker 日志
docker compose logs -f worker

# 重启 Worker
docker compose restart worker

# 检查 Redis 连接
docker compose exec redis ping
```

## 🔄 数据备份与恢复

### 备份

```bash
# 备份数据库
docker compose exec db pg_dump -U ollp_user ollp_db > backups/db_$(date +%Y%m%d).sql

# 备份 MinIO 数据
docker compose run --rm minio mc mirror minio/tutorials ./backups/minio_$(date +%Y%m%d)/

# 备份配置文件
tar -czvf backups/config_$(date +%Y%m%d).tar.gz .env docker-compose.yml nginx/
```

### 恢复

```bash
# 恢复数据库
cat backups/db_20260802.sql | docker compose exec -T db psql -U ollp_user ollp_db

# 恢复 MinIO 数据
docker compose run --rm minio mc mirror ./backups/minio_20260802/ minio/tutorials
```

## 📝 环境变量参考

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SECRET_KEY` | JWT 密钥 | 必填 |
| `CRYPTO_KEY_HEX` | API 密钥加密密钥 | 必填 |
| `POSTGRES_PASSWORD` | 数据库密码 | ollp_password |
| `MINIO_ACCESS_KEY` | MinIO 访问密钥 | ollp_minio |
| `MINIO_SECRET_KEY` | MinIO 秘密密钥 | 必填 |
| `ALLOWED_HOSTS` | 允许的域名 | * |
| `CORS_ORIGINS` | CORS 允许来源 | http://localhost |
| `LOG_LEVEL` | 日志级别 | INFO |

## 🚀 生产部署建议

### 1. 使用 Compose Profile

```yaml
# docker-compose.prod.yml
services:
  backend:
    profiles: ["prod"]
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  celery-worker:
    profiles: ["prod"]
    deploy:
      replicas: 3
```

启动生产环境：
```bash
docker compose --profile prod up -d
```

### 2. 使用 Secrets

```bash
# 创建 secret 文件
echo "your-secret-key" > ./secrets/secret_key.txt

# 在 compose 中使用
# secrets:
#   - secret_key
```

### 3. 配置监控

```bash
# 添加 Prometheus 和 Grafana
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

## 📞 支持

如有问题，请检查：
1. 服务日志: `docker compose logs -f`
2. 容器状态: `docker compose ps`
3. 系统资源: `docker stats`

---

**版本**: 1.0.0  
**最后更新**: 2026-07-30
