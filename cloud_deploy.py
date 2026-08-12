#!/usr/bin/env python3
"""
Online Learning Platform - 云端自动化部署脚本
使用Paramiko进行SSH连接和远程部署

作者: Agnes AI Assistant
日期: 2026-07-30
"""

import paramiko
import os
import sys
import json
import io
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import secrets
import hashlib
import base64


class PlatformDeployer:
    """Online Learning Platform 云端部署管理器"""

    # 服务器配置
    SERVER_CONFIG = {
        "hostname": "tlcw.yobeeo.com",
        "port": 22,
        "username": "root",
        "password": "tlcw_CENTOS@#2023",
        "project_path": "/opt/online-learning-platform"
    }

    def __init__(self):
        """初始化部署器"""
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.sftp_client: Optional[paramiko.SFTPClient] = None
        self.project_root = Path(__file__).parent.absolute()
        self.colors = {
            'GREEN': '\033[0;32m',
            'RED': '\033[0;31m',
            'YELLOW': '\033[1;33m',
            'BLUE': '\033[0;34m',
            'CYAN': '\033[0;36m',
            'WHITE': '\033[1;37m',
            'NC': '\033[0m'
        }

    def color_print(self, message: str, color: str = 'GREEN'):
        """带颜色的打印输出"""
        print(f"{self.colors[color]}{message}{self.colors['NC']}")

    def log(self, message: str, level: str = 'INFO'):
        """日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prefix = f"[{timestamp}] [{level}]"
        colors = {'INFO': 'CYAN', 'SUCCESS': 'GREEN', 'WARNING': 'YELLOW', 'ERROR': 'RED'}
        self.color_print(f"{prefix} {message}", colors.get(level, 'WHITE'))

    # ==================== SSH连接管理 ====================

    def connect_ssh(self) -> bool:
        """建立SSH连接到云服务器"""
        self.log("正在连接到云服务器...", 'INFO')

        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.ssh_client.connect(
                hostname=self.SERVER_CONFIG["hostname"],
                port=self.SERVER_CONFIG["port"],
                username=self.SERVER_CONFIG["username"],
                password=self.SERVER_CONFIG["password"],
                timeout=30,
                allow_agent=False,
                look_for_keys=False
            )

            self.sftp_client = self.ssh_client.open_sftp()
            self.log(f"成功连接到 {self.SERVER_CONFIG['hostname']}", 'SUCCESS')
            return True

        except paramiko.AuthenticationException:
            self.log("SSH认证失败：用户名或密码错误", 'ERROR')
            return False
        except paramiko.SSHException as e:
            self.log(f"SSH连接错误：{str(e)}", 'ERROR')
            return False
        except Exception as e:
            self.log(f"连接失败：{str(e)}", 'ERROR')
            return False

    def disconnect_ssh(self):
        """断开SSH连接"""
        try:
            if self.sftp_client:
                self.sftp_client.close()
            if self.ssh_client:
                self.ssh_client.close()
            self.log("SSH连接已断开")
        except Exception as e:
            self.log(f"断开连接时出错：{str(e)}", 'WARNING')

    def execute_command(self, command: str, timeout: int = 300) -> tuple:
        """在远程服务器上执行命令"""
        self.log(f"执行命令: {command[:100]}...", 'INFO')

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)

            # 读取输出
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            exit_status = stdout.channel.recv_exit_status()

            if output:
                self.log(f"输出: {output[:500]}", 'INFO')
            if error and exit_status != 0:
                self.log(f"错误: {error[:500]}", 'WARNING')

            return exit_status, output, error

        except Exception as e:
            self.log(f"命令执行失败：{str(e)}", 'ERROR')
            return 1, "", str(e)

    # ==================== 配置文件生成 ====================

    def generate_env_file(self) -> str:
        """生成生产环境配置文件"""
        self.log("生成生产环境配置文件...")

        # 生成安全密钥
        secret_key = secrets.token_hex(32)
        crypto_key_hex = secrets.token_hex(32)
        postgres_password = secrets.token_urlsafe(32)
        minio_root_password = secrets.token_urlsafe(24)

        env_content = f"""# ============================================================
# Online Learning Platform - 生产环境配置
# 生成时间: {datetime.now().isoformat()}
# 请勿将此文件提交到版本控制！
# ============================================================

# ==================== 应用密钥 ====================
SECRET_KEY={secret_key}
CRYPTO_KEY_HEX={crypto_key_hex}
DEBUG=false
APP_ENV=production

# ==================== 数据库配置 ====================
DATABASE_URL=postgresql://platform_user:{postgres_password}@db:5432/online_learning
POSTGRES_USER=platform_user
POSTGRES_PASSWORD={postgres_password}
POSTGRES_DB=online_learning

# ==================== 缓存与消息队列 ====================
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ==================== 对象存储 (MinIO) ====================
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY={minio_root_password}
MINIO_BUCKET=tutorials
MINIO_REGION=us-east-1

# ==================== 安全配置 ====================
ALLOWED_HOSTS=tlcw.yobeeo.com,www.tlcw.yobeeo.com
CORS_ORIGINS=https://tlcw.yobeeo.com
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SECURE_PROXY_SSL_HEADER=https

# ==================== Claude API 默认配置 ====================
DEFAULT_MODEL=claude-3-opus-20240925
API_TIMEOUT=300
MAX_RETRIES=3

# ==================== 日志配置 ====================
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log
"""

        # 保存到本地
        local_env_path = self.project_root / ".env.production"
        local_env_path.write_text(env_content)
        self.log(f"配置文件已保存到: {local_env_path}", 'SUCCESS')

        return env_content

    def generate_docker_compose(self) -> str:
        """生成生产级Docker Compose配置"""
        self.log("生成Docker Compose配置文件...")

        compose_content = """version: '3.8'

services:
  # ==================== 后端API服务 ====================
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ollp-backend
    restart: always
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - CRYPTO_KEY_HEX=${CRYPTO_KEY_HEX}
      - MINIO_ENDPOINT=${MINIO_ENDPOINT}
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - CORS_ORIGINS=${CORS_ORIGINS}
      - LOG_LEVEL=${LOG_LEVEL}
    volumes:
      - app_logs:/app/logs
      - tutorial_uploads:/app/uploads
      - ./config/nginx:/etc/nginx/conf.d:ro
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
      minio:
        condition: service_healthy
    networks:
      - platform-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ==================== 前端应用 ====================
  frontend:
    build:
      context: ./frontend
      dockerfile: ../Dockerfile.frontend
    container_name: ollp-frontend
    restart: always
    environment:
      - API_URL=${INTERNAL_API_URL}
      - NODE_ENV=production
    depends_on:
      - backend
    networks:
      - platform-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ==================== 数据库 (PostgreSQL) ====================
  db:
    image: postgres:15-alpine
    container_name: ollp-db
    restart: always
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d:ro
    networks:
      - platform-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # ==================== 缓存与消息队列 (Redis) ====================
  redis:
    image: redis:7-alpine
    container_name: ollp-redis
    restart: always
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --loglevel warning
    volumes:
      - redis_data:/data
    networks:
      - platform-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 512M

  # ==================== 对象存储 (MinIO) ====================
  minio:
    image: minio/minio:latest
    container_name: ollp-minio
    restart: always
    command: server /data --console-address ":9001" --address ":9000"
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
      - MINIO_PROMETHEUS_AUTH_TYPE=public
    volumes:
      - minio_data:/data
    networks:
      - platform-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1G

  # ==================== Celery Worker ====================
  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ollp-worker
    restart: always
    command: celery -A backend.src.tasks worker --loglevel=info --concurrency=4 --prefetch-multiplier=1 -E
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - CRYPTO_KEY_HEX=${CRYPTO_KEY_HEX}
      - MINIO_ENDPOINT=${MINIO_ENDPOINT}
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - LOG_LEVEL=${LOG_LEVEL}
    volumes:
      - app_logs:/app/logs
      - tutorial_uploads:/app/uploads
    depends_on:
      - db
      - redis
      - minio
    networks:
      - platform-net
    deploy:
      resources:
        limits:
          memory: 2G

  # ==================== Nginx反向代理 ====================
  nginx:
    image: nginx:alpine
    container_name: ollp-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./config/nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
      - ./logs/nginx/certbot:/etc/letsencrypt:ro
    depends_on:
      - backend
      - frontend
    networks:
      - platform-net
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 256M

  # ==================== Certbot (SSL证书) ====================
  certbot:
    image: certbot/certbot:latest
    container_name: ollp-certbot
    volumes:
      - ./logs/nginx/certbot:/etc/letsencrypt
      - ./logs/nginx/certbot-webroot:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew --webroot --webroot-path=/var/www/certbot; sleep 12h & wait $${!}; done;'"
    networks:
      - platform-net

# ==================== 数据卷 ====================
volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  minio_data:
    driver: local
  app_logs:
    driver: local
  tutorial_uploads:
    driver: local

# ==================== 网络 ====================
networks:
  platform-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
"""

        return compose_content

    def generate_dockerfiles(self) -> Dict[str, str]:
        """生成Dockerfile配置"""
        self.log("生成Dockerfile配置...")

        # 后端Dockerfile
        backend_dockerfile = """# ==================== 后端服务Dockerfile ====================
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
COPY backend/requirements.txt backend/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend/ ./backend/
COPY src/backend/ ./src/

# 创建日志和上传目录
RUN mkdir -p /app/logs /app/uploads

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
"""

        # 前端Dockerfile
        frontend_dockerfile = """# ==================== 前端服务Dockerfile ====================
FROM node:20-alpine

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apk add --no-cache python3 make g++

# 复制package文件
COPY frontend/package*.json ./

# 安装依赖
RUN npm ci --only=production && npm cache clean --force

# 复制应用代码
COPY frontend/ ./

# 构建前端
RUN npm run build

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# 启动命令
CMD ["node", "server.js"]
"""

        return {
            "Dockerfile.backend": backend_dockerfile,
            "Dockerfile.frontend": frontend_dockerfile
        }

    # ==================== 文件上传 ====================

    def upload_file(self, local_path: Path, remote_path: str):
        """上传单个文件到服务器"""
        try:
            self.sftp_client.put(str(local_path), remote_path)
            self.log(f"已上传: {local_path.name} -> {remote_path}", 'SUCCESS')
            return True
        except Exception as e:
            self.log(f"上传文件失败 {local_path.name}: {str(e)}", 'ERROR')
            return False

    def upload_directory(self, local_dir: Path, remote_dir: str, exclude: List[str] = None):
        """递归上传目录到服务器"""
        if exclude is None:
            exclude = ['.git', '__pycache__', '*.pyc', 'node_modules', '.env']

        self.log(f"上传目录: {local_dir} -> {remote_dir}")

        for item in local_dir.iterdir():
            if item.name in exclude or item.name.startswith('.'):
                continue

            remote_item = f"{remote_dir}/{item.name}"

            if item.is_dir():
                # 创建远程目录
                try:
                    self.sftp_client.mkdir(remote_item)
                except FileNotFoundError:
                    pass  # 目录已存在
                # 递归上传子目录
                self.upload_directory(item, remote_item, exclude)
            elif item.is_file():
                # 上传文件
                self.upload_file(item, remote_item)

    # ==================== 部署流程 ====================

    def prepare_server(self):
        """准备服务器环境"""
        self.log("=" * 60)
        self.log("开始准备服务器环境...", 'INFO')
        self.log("=" * 60)

        # 1. 创建项目目录
        self.execute_command(f"mkdir -p {self.SERVER_CONFIG['project_path']}")
        self.execute_command(f"mkdir -p {self.SERVER_CONFIG['project_path']}/logs")
        self.execute_command(f"mkdir -p {self.SERVER_CONFIG['project_path']}/config/nginx/ssl")
        self.execute_command(f"mkdir -p {self.SERVER_CONFIG['project_path']}/db/init")
        self.execute_command(f"mkdir -p {self.SERVER_CONFIG['project_path']}/frontend/build")

        # 2. 检查并安装Docker
        self.log("检查Docker安装...")
        exit_code, output, error = self.execute_command("docker --version")
        if exit_code != 0:
            self.log("安装Docker...", 'WARNING')
            self.install_docker()
        else:
            self.log(f"Docker已安装: {output.strip()}", 'SUCCESS')

        # 3. 检查并安装Docker Compose
        self.log("检查Docker Compose...")
        exit_code, output, error = self.execute_command("docker-compose --version")
        if exit_code != 0:
            self.log("安装Docker Compose...", 'WARNING')
            self.install_docker_compose()
        else:
            self.log(f"Docker Compose已安装: {output.strip()}", 'SUCCESS')

        self.log("服务器环境准备完成", 'SUCCESS')

    def install_docker(self):
        """在服务器上安装Docker"""
        commands = [
            "apt-get update",
            "apt-get install -y apt-transport-https ca-certificates curl software-properties-common",
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -",
            "add-apt-repository \"deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\"",
            "apt-get update",
            "apt-get install -y docker-ce docker-ce-cli containerd.io",
            "systemctl enable docker",
            "systemctl start docker",
            "usermod -aG docker root"
        ]

        for cmd in commands:
            self.execute_command(cmd)

    def install_docker_compose(self):
        """在服务器上安装Docker Compose"""
        # 方法1: 尝试使用apt-get安装（Debian/Ubuntu）
        self.log("尝试通过apt安装Docker Compose...")
        self.execute_command("apt-get update -qq")
        self.execute_command("apt-get install -y docker-compose-plugin")

        # 方法2: 如果失败，尝试手动下载（备用方案）
        exit_code, output, error = self.execute_command("docker compose version")
        if exit_code != 0:
            self.log("apt安装失败，尝试手动下载...")
            # 检测系统架构
            self.execute_command("uname -m")
            arch = "x86_64"  # 默认
            exit_code, output, _ = self.execute_command("uname -m")
            if "aarch" in output or "arm" in output:
                arch = "aarch64"

            # 下载docker-compose
            compose_url = f"https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-{arch}"
            self.execute_command(f"curl -L \"{compose_url}\" -o /tmp/docker-compose")
            self.execute_command("chmod +x /tmp/docker-compose")
            self.execute_command("mv /tmp/docker-compose /usr/local/bin/docker-compose")

    def upload_project(self):
        """上传项目文件到服务器"""
        self.log("=" * 60)
        self.log("上传项目文件...", 'INFO')
        self.log("=" * 60)

        project_path = self.SERVER_CONFIG['project_path']

        # 1. 上传配置文件
        env_content = self.generate_env_file()
        self.sftp_client.putfo(
            io.BytesIO(env_content.encode()),
            f"{project_path}/.env.production"
        )

        # 2. 上传Docker Compose配置
        compose_content = self.generate_docker_compose()
        self.sftp_client.putfo(
            io.BytesIO(compose_content.encode()),
            f"{project_path}/docker-compose.prod.yml"
        )

        # 3. 上传Dockerfiles
        dockerfiles = self.generate_dockerfiles()
        for filename, content in dockerfiles.items():
            self.sftp_client.putfo(
                io.BytesIO(content.encode()),
                f"{project_path}/{filename}"
            )

        # 4. 上传项目代码
        self.upload_directory(
            self.project_root / "src" / "backend",
            f"{project_path}/src/backend"
        )
        self.upload_directory(
            self.project_root / "src" / "frontend",
            f"{project_path}/src/frontend"
        )

        # 5. 上传requirements.txt
        if (self.project_root / "requirements.txt").exists():
            self.sftp_client.put(
                str(self.project_root / "requirements.txt"),
                f"{project_path}/requirements.txt"
            )

        # 6. 上传package.json
        if (self.project_root / "src" / "frontend" / "package.json").exists():
            self.sftp_client.put(
                str(self.project_root / "src" / "frontend" / "package.json"),
                f"{project_path}/src/frontend/package.json"
            )

        self.log("项目文件上传完成", 'SUCCESS')

    def build_and_deploy(self):
        """构建并部署服务"""
        self.log("=" * 60)
        self.log("开始构建和部署服务...", 'INFO')
        self.log("=" * 60)

        project_path = self.SERVER_CONFIG['project_path']

        # 1. 进入项目目录
        self.execute_command(f"cd {project_path} && pwd")

        # 2. 停止旧容器
        self.log("停止旧容器...", 'WARNING')
        self.execute_command(f"cd {project_path} && docker-compose -f docker-compose.prod.yml down --remove-orphans")

        # 3. 构建镜像
        self.log("构建Docker镜像（这可能需要几分钟）...", 'WARNING')
        self.execute_command(
            f"cd {project_path} && docker-compose -f docker-compose.prod.yml build --no-cache",
            timeout=1800  # 30分钟超时
        )

        # 4. 启动服务
        self.log("启动服务...", 'INFO')
        self.execute_command(
            f"cd {project_path} && docker-compose -f docker-compose.prod.yml up -d",
            timeout=300
        )

        # 5. 等待服务启动
        self.log("等待服务启动...", 'INFO')
        time.sleep(15)

        # 6. 检查服务状态
        self.log("检查服务状态...", 'INFO')
        self.execute_command(f"cd {project_path} && docker-compose -f docker-compose.prod.yml ps")

        self.log("部署完成！", 'SUCCESS')

    def verify_deployment(self):
        """验证部署结果"""
        self.log("=" * 60)
        self.log("验证部署结果...", 'INFO')
        self.log("=" * 60)

        # 检查容器状态
        exit_code, output, error = self.execute_command(
            "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'"
        )

        if exit_code == 0:
            self.log("运行中的容器:", 'SUCCESS')
            print(output)

        # 检查健康状态
        self.log("\n健康检查:", 'INFO')
        self.execute_command("curl -s http://localhost:8000/health || echo '后端API未响应'")

        # 显示访问地址
        print("\n" + "=" * 60)
        self.color_print("部署完成！访问地址:", 'GREEN')
        print("=" * 60)
        print(f"  🌐 主站:      https://tlcw.yobeeo.com")
        print(f"  📚 API文档:   http://tlcw.yobeeo.com:8000/docs")
        print(f"  🔍 健康检查:  http://tlcw.yobeeo.com:8000/health")
        print(f"  💾 MinIO:     http://tlcw.yobeeo.com:9001")
        print("=" * 60)

    # ==================== 主流程 ====================

    def deploy(self):
        """执行完整部署流程"""
        self.log("=" * 70)
        self.log("  Online Learning Platform - 云端自动化部署", 'CYAN')
        self.log("=" * 70)

        try:
            # 1. 连接服务器
            if not self.connect_ssh():
                return False

            # 2. 准备服务器环境
            self.prepare_server()

            # 3. 上传项目文件
            self.upload_project()

            # 4. 构建并部署
            self.build_and_deploy()

            # 5. 验证部署
            self.verify_deployment()

            self.log("=" * 70)
            self.log("  部署成功完成！", 'GREEN')
            self.log("=" * 70)
            return True

        except KeyboardInterrupt:
            self.log("\n部署被用户中断", 'WARNING')
            return False
        except Exception as e:
            self.log(f"\n部署失败: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.disconnect_ssh()


def main():
    """主入口函数"""
    deployer = PlatformDeployer()
    success = deployer.deploy()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
