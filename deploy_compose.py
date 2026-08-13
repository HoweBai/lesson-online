#!/usr/bin/env python3
"""
完整部署脚本 - tlcw.yobeeo.com (Docker Compose: PostgreSQL + Redis + MinIO)
用法: python deploy_compose.py
"""
import os
import sys
import time
import paramiko
import subprocess
from pathlib import Path
import secrets
import json

SERVER = "tlcw.yobeeo.com"
USER = "root"
PASSWORD = os.environ.get("SSH_PASSWORD", "tlcw_CENTOS@#2023")
REMOTE_PATH = "/opt/ollp"
PROJECT_ROOT = Path(__file__).parent

def log(msg, color=""):
    print(msg)

def run_ssh(ssh, cmd, desc="", timeout=300):
    log(f"\n>>> {desc}")
    log(f"    {cmd[:120]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="ignore").strip()
    err = stderr.read().decode("utf-8", errors="ignore").strip()
    if out:
        for line in out.splitlines()[:25]:
            log(f"    {line}")
    if err and out:
        for line in err.splitlines()[:5]:
            log(f"    ERR: {line}")
    return out, err

def upload_file(sftp, local, remote):
    sftp.put(str(local), remote)
    log(f"  Uploaded: {local.name}")

def upload_dir(sftp, local_dir, remote_dir, exclude=None):
    if exclude is None:
        exclude = {"__pycache__", "*.pyc", ".git", "node_modules"}
    local = Path(local_dir)
    for item in local.iterdir():
        if item.name in exclude or item.name.startswith("."):
            continue
        remote_item = f"{remote_dir}/{item.name}"
        if item.is_dir():
            try:
                sftp.mkdir(remote_item)
            except IOError:
                pass
            upload_dir(sftp, item, remote_item, exclude)
        else:
            upload_file(sftp, item, remote_item)

def build_frontend():
    log("\n=== Building Frontend ===")
    frontend = PROJECT_ROOT / "src" / "frontend"
    build_dir = frontend / "build"
    if build_dir.exists() and (build_dir / "index.html").exists():
        log("Using existing frontend build")
        return True
    npm_path = None
    for p in ["npm.cmd", "npm", "D:/softwares/nodejs/npm.cmd"]:
        import shutil
        if shutil.which(p) or os.path.exists(p):
            npm_path = p
            break
    if not npm_path:
        log("ERROR: npm not found", "RED")
        return False
    log("Installing npm deps...")
    r = subprocess.run([npm_path, "install"], cwd=str(frontend), capture_output=True, timeout=180)
    if r.returncode != 0:
        log(f"npm install failed:\n{r.stderr[-300:]}", "RED")
        return False
    log("Building frontend...")
    r = subprocess.run([npm_path, "run", "build"], cwd=str(frontend), capture_output=True, timeout=300)
    if r.returncode != 0:
        log(f"Build failed:\n{r.stderr[-500:]}", "RED")
        return False
    log("Frontend build OK")
    return True

def main():
    log("=" * 60)
    log("  完整部署 (Docker Compose: PostgreSQL + Redis + MinIO)")
    log("=" * 60)

    log("\n[1/9] 连接服务器...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASSWORD, timeout=15)
    log("[OK]")

    try:
        if not build_frontend():
            log("前端构建失败", "RED")
            return 1

        sftp = ssh.open_sftp()

        # 2. 创建目录
        log("\n[2/9] 创建目录结构...")
        for d in ["src/backend/src", "src/backend/tests", "frontend/build",
                   "nginx_conf", "db/init", "logs", "uploads", "db/data", "redis/data"]:
            run_ssh(ssh, f"mkdir -p {REMOTE_PATH}/{d}", f"mkdir {d}")
        log("[OK]")

        # 3. 上传后端源码
        log("\n[3/9] 上传后端代码...")
        upload_dir(sftp, PROJECT_ROOT / "src" / "backend" / "src", f"{REMOTE_PATH}/src/backend/src")
        upload_dir(sftp, PROJECT_ROOT / "src" / "backend" / "tests", f"{REMOTE_PATH}/src/backend/tests")
        upload_file(sftp, PROJECT_ROOT / "src" / "backend" / "requirements.txt", f"{REMOTE_PATH}/requirements.txt")
        log("[OK]")

        # 4. 上传前端
        log("\n[4/9] 上传前端...")
        run_ssh(ssh, f"rm -rf {REMOTE_PATH}/frontend/build/* && mkdir -p {REMOTE_PATH}/frontend/build", "清理旧构建")
        upload_dir(sftp, PROJECT_ROOT / "src" / "frontend" / "build", f"{REMOTE_PATH}/frontend/build")
        log("[OK]")

        # 5. 上传 nginx 配置
        log("\n[5/9] 上传 nginx 配置...")
        nginx_conf = PROJECT_ROOT / "nginx" / "nginx.production.conf"
        if nginx_conf.exists():
            upload_file(sftp, nginx_conf, f"{REMOTE_PATH}/nginx_conf/nginx.conf")
        log("[OK]")

        # 6. 创建 docker-compose.yml
        log("\n[6/9] 创建 docker-compose 配置...")
        compose = """version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ollp-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./ollp.db:/app/ollp.db
      - ./logs:/app/logs
      - ./uploads:/app/uploads
      - ./src:/app/src:ro
    environment:
      - DATABASE_URL=postgresql://ollp_user:${PG_PASSWORD}@db:5432/ollp_db
      - SECRET_KEY=${SECRET_KEY}
      - CRYPTO_KEY_HEX=${CRYPTO_KEY_HEX}
      - REDIS_URL=redis://redis:6379/0
      - PYTHONPATH=/app
      - PYTHONDONTWRITEBYTECODE=1
      - FRONTEND_URL=http://tlcw.yobeeo.com
      - LOG_LEVEL=info
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - ollp-net

  db:
    image: postgres:16-alpine
    container_name: ollp-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=ollp_user
      - POSTGRES_PASSWORD=${PG_PASSWORD}
      - POSTGRES_DB=ollp_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d:ro
    networks:
      - ollp-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ollp_user -d ollp_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: ollp-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - ollp-net

  nginx:
    image: nginx:alpine
    container_name: ollp-nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx_conf/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend:/opt/ollp/frontend:ro
    depends_on:
      - backend
    networks:
      - ollp-net

volumes:
  postgres_data:
  redis_data:

networks:
  ollp-net:
    external: true
"""
        sftp.open(f"{REMOTE_PATH}/docker-compose.yml", "w").write(compose.encode())
        log("[OK]")

        # 7. 创建 .env
        log("\n[7/9] 创建环境变量...")
        pg_password = secrets.token_urlsafe(24)
        secret_key = secrets.token_hex(32)
        crypto_key = secrets.token_hex(32)
        env_content = f"""SECRET_KEY={secret_key}
CRYPTO_KEY_HEX={crypto_key}
PG_PASSWORD={pg_password}
"""
        sftp.open(f"{REMOTE_PATH}/.env", "w").write(env_content.encode())
        log(f"[OK] (PG_PASSWORD={pg_password[:10]}...)")

        # 8. 创建 Dockerfile（确保正确）
        log("\n[8/9] 确认 Dockerfile...")
        dockerfile = """FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY tests/ ./tests/
RUN mkdir -p /app/logs /app/uploads
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
"""
        sftp.open(f"{REMOTE_PATH}/Dockerfile", "w").write(dockerfile.encode())
        log("[OK] Dockerfile 已确认")

        sftp.close()

        # 停止旧容器
        log("\n[9/9] 启动服务...")
        run_ssh(ssh,
            "docker stop ollp-backend ollp-nginx ollp-db ollp-redis 2>/dev/null; "
            "docker rm ollp-backend ollp-nginx ollp-db ollp-redis 2>/dev/null; true",
            "停止旧容器")

        # 用 docker-compose 启动
        run_ssh(ssh,
            f"cd {REMOTE_PATH} && docker compose up -d --build 2>&1",
            "构建并启动所有服务", timeout=900)

        time.sleep(15)

        # 验证
        log("\n=== 验证 ===")
        run_ssh(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "容器状态")
        run_ssh(ssh, "curl -s http://localhost/health 2>/dev/null || curl -s http://localhost:8000/health", "健康检查")
        run_ssh(ssh, "curl -s http://localhost/ | head -c 100", "前端检查")

        # 后端日志
        _, out, _ = ssh.exec_command("docker logs ollp-backend --tail 15 2>&1")
        logs = out.read().decode().strip()
        if logs:
            log(f"\n后端日志:\n{logs}")

        log("\n" + "=" * 60)
        log("  部署完成!")
        log("  主站:   http://tlcw.yobeeo.com/")
        log("  API:    http://tlcw.yobeeo.com:8000/docs")
        log("  健康:   http://tlcw.yobeeo.com/health")
        log("=" * 60)
        return 0

    except Exception as e:
        log(f"\n部署失败: {e}", "RED")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        ssh.close()

if __name__ == "__main__":
    sys.exit(main())
