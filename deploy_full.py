#!/usr/bin/env python3
"""
完整部署脚本 - tlcw.yobeeo.com (Docker Compose with PostgreSQL/Redis/MinIO)
用法: python deploy_full.py
"""
import os
import sys
import time
import paramiko
import subprocess
from pathlib import Path

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
        for line in out.splitlines()[:20]:
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
    log("  完整部署到 tlcw.yobeeo.com")
    log("  (PostgreSQL + Redis + MinIO + Backend + Nginx)")
    log("=" * 60)

    log("\n[1/8] 连接服务器...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASSWORD, timeout=15)
    log("[OK] 连接成功")

    try:
        if not build_frontend():
            log("前端构建失败", "RED")
            return 1

        sftp = ssh.open_sftp()

        # 2. 创建目录结构
        log("\n[2/8] 创建目录结构...")
        dirs = [
            f"{REMOTE_PATH}/src/backend/src",
            f"{REMOTE_PATH}/src/backend/tests",
            f"{REMOTE_PATH}/frontend/build",
            f"{REMOTE_PATH}/nginx_conf",
            f"{REMOTE_PATH}/db/init",
            f"{REMOTE_PATH}/logs",
            f"{REMOTE_PATH}/uploads",
        ]
        for d in dirs:
            run_ssh(ssh, f"mkdir -p {d}", f"创建目录: {d.split('/')[-1]}")
        log("[OK] 目录结构已创建")

        # 3. 上传后端源码
        log("\n[3/8] 上传后端代码...")
        upload_dir(sftp, PROJECT_ROOT / "src" / "backend" / "src", f"{REMOTE_PATH}/src/backend/src")
        upload_dir(sftp, PROJECT_ROOT / "src" / "backend" / "tests", f"{REMOTE_PATH}/src/backend/tests")
        upload_file(sftp, PROJECT_ROOT / "src" / "backend" / "requirements.txt", f"{REMOTE_PATH}/requirements.txt")
        log("[OK] 后端代码已上传")

        # 4. 上传前端构建
        log("\n[4/8] 上传前端...")
        run_ssh(ssh, f"rm -rf {REMOTE_PATH}/frontend/build/* && mkdir -p {REMOTE_PATH}/frontend/build", "清理旧构建")
        upload_dir(sftp, PROJECT_ROOT / "src" / "frontend" / "build", f"{REMOTE_PATH}/frontend/build")
        log("[OK] 前端已上传")

        # 5. 上传 nginx 配置
        log("\n[5/8] 上传 nginx 配置...")
        nginx_conf = PROJECT_ROOT / "nginx" / "nginx.production.conf"
        if nginx_conf.exists():
            upload_file(sftp, nginx_conf, f"{REMOTE_PATH}/nginx_conf/nginx.conf")
        # 也上传本地 nginx conf (HTTP only, no SSL)
        nginx_http = PROJECT_ROOT / "nginx" / "nginx.conf"
        if not nginx_http.exists():
            # Create HTTP-only nginx config
            nginx_http_content = """worker_processes auto;
events { worker_connections 1024; }
http {
    include mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    gzip on;
    upstream backend {
        server backend:8000;
    }
    server {
        listen 80;
        server_name _;
        root /opt/ollp/frontend;
        index index.html;
        client_max_body_size 50m;
        location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|otf)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
        location ~* \\.html$ {
            add_header Cache-Control "no-cache";
        }
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
        location /health { proxy_pass http://backend; }
        location /docs { proxy_pass http://backend; }
        location /redoc { proxy_pass http://backend; }
        location /monitor { proxy_pass http://backend; }
        location /admin { proxy_pass http://backend; }
        location / {
            try_files $uri $uri/ /index.html;
        }
    }
}
"""
            (PROJECT_ROOT / "nginx" / "nginx.conf").write_text(nginx_http_content)
            upload_file(sftp, nginx_http, f"{REMOTE_PATH}/nginx_conf/nginx.conf")
        log("[OK] nginx 配置已上传")

        # 6. 创建 docker-compose.yml
        log("\n[6/8] 创建 docker-compose 配置...")
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
        log("[OK] docker-compose.yml 已创建")

        # 7. 创建 .env 文件
        log("\n[7/8] 创建环境变量...")
        import secrets
        pg_password = secrets.token_urlsafe(24)
        secret_key = secrets.token_hex(32)
        crypto_key = secrets.token_hex(32)
        env_content = f"""SECRET_KEY={secret_key}
CRYPTO_KEY_HEX={crypto_key}
PG_PASSWORD={pg_password}
"""
        sftp.open(f"{REMOTE_PATH}/.env", "w").write(env_content.encode())
        log(f"[OK] .env 已创建 (PG_PASSWORD={pg_password[:8]}...)")

        sftp.close()

        # 停止旧的 ollp-backend 容器（不用 docker-compose，直接停）
        log("\n[8/8] 启动服务...")
        run_ssh(ssh, "docker stop ollp-backend ollp-nginx 2>/dev/null; docker rm ollp-backend ollp-nginx 2>/dev/null; true", "停止旧容器")

        # 构建并启动
        run_ssh(ssh, f"cd {REMOTE_PATH} && docker compose up -d --build 2>&1", "构建并启动所有服务", timeout=900)

        time.sleep(15)

        # 验证
        log("\n=== 验证部署 ===")
        run_ssh(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "容器状态")
        run_ssh(ssh, "curl -s http://localhost/health 2>/dev/null || curl -s http://localhost:8000/health", "健康检查")
        run_ssh(ssh, "curl -s http://localhost/ | head -c 100", "前端检查")

        # 检查后端日志
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
