# Online Learning Platform - 云端部署指南
**服务器**: tlcw.yobeeo.com  
**部署时间**: 2026-07-30  
**状态**: 代码已上传，需要手动完成部署

---

## 📋 已完成的工作

### ✅ 代码已上传到服务器
- **路径**: `/opt/online-learning-platform/`
- **包含文件**:
  - 后端源代码: `src/backend/src/` (40+ Python文件)
  - 前端源代码: `src/frontend/src/` (20+ TypeScript文件)
  - 配置文件: `.env.production`, `docker-compose.yml`
  - Dockerfile: `Dockerfile.backend`, `Dockerfile.frontend`

### ✅ 环境配置已生成
- 数据库密码: 自动生成
- API密钥: 已加密
- Redis/Celery配置: 已设置

---

## 🚀 手动部署步骤

### 步骤1: SSH连接到服务器
```bash
ssh root@tlcw.yobeeo.com
# 密码: tlcw_CENTOS@#2023
```

### 步骤2: 进入项目目录
```bash
cd /opt/online-learning-platform
ls -la
```

### 步骤3: 检查Docker环境
```bash
# 检查Docker版本
docker --version

# 检查Docker Compose版本 (v2命令)
docker compose version

# 或者旧版命令
docker-compose --version
```

### 步骤4: 安装依赖（如果缺少）
```bash
# 更新包管理器
yum update -y  # 或 apt-get update

# 安装Docker（如果未安装）
yum install -y docker
systemctl start docker
systemctl enable docker

# 安装Docker Compose插件
yum install -y docker-compose-plugin
# 或
apt-get install -y docker-compose-plugin
```

### 步骤5: 构建并启动服务
```bash
# 方法1: 使用Docker Compose v2
docker compose up -d --build

# 方法2: 使用Docker Compose v1
docker-compose up -d --build

# 如果构建失败，可以分步构建
docker compose build backend
docker compose build frontend
docker compose up -d
```

### 步骤6: 检查服务状态
```bash
# 查看运行中的容器
docker ps

# 查看所有容器（包括已停止的）
docker ps -a

# 查看日志
docker compose logs -f

# 查看特定服务的日志
docker compose logs -f backend
docker compose logs -f frontend
```

### 步骤7: 访问应用
```bash
# 在浏览器中访问
http://tlcw.yobeeo.com:3000      # 前端应用
http://tlcw.yobeeo.com:8000/docs  # API文档
http://tlcw.yobeeo.com:8000/health # 健康检查
```

---

## 🔧 故障排查

### 问题1: Docker构建失败
```bash
# 检查Docker构建日志
docker compose build --progress=plain

# 清理Docker缓存后重试
docker system prune -a
docker compose build --no-cache
```

### 问题2: 端口被占用
```bash
# 检查端口占用
netstat -tlnp | grep 8000
netstat -tlnp | grep 3000

# 停止占用端口的进程
kill -9 <PID>

# 或者修改docker-compose.yml中的端口映射
# 例如: "8080:8000" 映射到8080端口
```

### 问题3: 数据库连接失败
```bash
# 检查数据库容器是否运行
docker ps | grep db

# 查看数据库日志
docker compose logs db

# 重启数据库容器
docker compose restart db
```

### 问题4: 前端构建失败
```bash
# 检查Node版本
node --version

# 进入前端目录手动构建
cd src/frontend
npm install
npm run build

# 如果失败，检查package.json中的依赖
cat package.json
```

---

## 📊 服务管理命令

```bash
# 进入项目目录
cd /opt/online-learning-platform

# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重启所有服务
docker compose restart

# 查看实时日志
docker compose logs -f

# 查看后端日志
docker compose logs -f backend

# 查看前端日志
docker compose logs -f frontend

# 进入后端容器
docker exec -it ollp-backend bash

# 进入前端容器
docker exec -it ollp-frontend sh

# 查看容器资源使用
docker stats

# 清理未使用的资源
docker system prune -a
```

---

## 🔐 安全建议

1. **修改默认密码**:
   ```bash
   # 编辑.env文件
   vi .env
   # 修改POSTGRES_PASSWORD和其他敏感信息
   ```

2. **配置防火墙**:
   ```bash
   # 只开放必要端口
   firewall-cmd --add-port=80/tcp --permanent
   firewall-cmd --add-port=443/tcp --permanent
   firewall-cmd --reload
   ```

3. **配置SSL证书**:
   ```bash
   # 使用Let's Encrypt
   yum install -y certbot python3-certbot-nginx
   certbot --nginx -d tlcw.yobeeo.com
   ```

4. **定期备份**:
   ```bash
   # 备份数据库
   docker exec ollp-db pg_dump -U platform_user online_learning > backup.sql
   
   # 备份文件
   tar -czvf backup-$(date +%Y%m%d).tar.gz uploads/ logs/
   ```

---

## 📝 下一步工作

完成基础部署后，建议进行以下工作：

1. **配置生产环境优化**
   - 调整Docker资源限制
   - 配置日志轮转
   - 设置监控告警

2. **完善功能**
   - 配置Celery worker持久化
   - 添加Redis集群支持
   - 配置对象存储（MinIO）

3. **安全加固**
   - 配置HTTPS
   - 设置访问控制
   - 启用审计日志

4. **性能优化**
   - 配置CDN
   - 启用Gzip压缩
   - 优化数据库查询

---

## 📞 联系支持

如需帮助，请提供：
- 服务器访问信息
- Docker版本信息
- 错误日志内容
- 网络环境说明

---

**部署成功标志**:
- [ ] `docker ps` 显示所有容器运行中
- [ ] `http://tlcw.yobeeo.com:8000/health` 返回健康状态
- [ ] `http://tlcw.yobeeo.com:3000` 可以访问前端页面
- [ ] 可以正常注册/登录用户
