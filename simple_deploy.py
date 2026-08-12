#!/usr/bin/env python3
"""
Online Learning Platform - 云端快速部署脚本（简化版）
直接上传必要配置文件并启动服务
"""

import paramiko
import os
import sys
import time
from pathlib import Path

# 服务器配置
SERVER_HOST = "tlcw.yobeeo.com"
SERVER_USER = "root"
SERVER_PASSWORD = "tlcw_CENTOS@#2023"
REMOTE_PATH = "/opt/online-learning-platform"

def ssh_exec(ssh, command, timeout=60):
    """执行SSH命令"""
    print(f"$ {command}")
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    status = stdout.channel.recv_exit_status()
    if output:
        print(output[:500])
    if error and status != 0:
        print(f"ERROR: {error[:200]}")
    return status, output, error

def sftp_upload(sftp, local_path, remote_path):
    """上传单个文件"""
    try:
        sftp.put(str(local_path), remote_path)
        print(f"Uploaded: {local_path.name}")
        return True
    except Exception as e:
        print(f"Failed to upload {local_path.name}: {e}")
        return False

def main():
    print("="*60)
    print("  Online Learning Platform - 云端部署")
    print("="*60)
    print()

    # 连接到服务器
    print(f"Connecting to {SERVER_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print("Connected successfully!")
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

    sftp = ssh.open_sftp()

    try:
        # 1. 创建目录
        print("\n[1/5] Creating directories...")
        ssh_exec(ssh, f"mkdir -p {REMOTE_PATH}/src/backend {REMOTE_PATH}/src/frontend")
        ssh_exec(ssh, f"mkdir -p {REMOTE_PATH}/logs {REMOTE_PATH}/config/nginx/ssl")

        # 2. 生成并上传.env文件
        print("\n[2/5] Generating .env file...")
        import secrets
        secret_key = secrets.token_hex(32)
        crypto_key = secrets.token_hex(32)
        postgres_password = secrets.token_urlsafe(32)

        env_content = f"""# Production Environment
SECRET_KEY={secret_key}
CRYPTO_KEY_HEX={crypto_key}
POSTGRES_PASSWORD={postgres_password}
POSTGRES_USER=platform_user
POSTGRES_DB=online_learning
DATABASE_URL=postgresql://{{POSTGRES_USER}}:{{POSTGRES_PASSWORD}}@db:5432/{{POSTGRES_DB}}
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
"""
        env_path = Path(".env.production")
        env_path.write_text(env_content)
        sftp_upload(sftp, env_path, f"{REMOTE_PATH}/.env")

        # 3. 上传Docker Compose配置
        print("\n[3/5] Uploading docker-compose configuration...")
        compose_path = Path("docker-compose.prod.yml")
        if compose_path.exists():
            sftp_upload(sftp, compose_path, f"{REMOTE_PATH}/docker-compose.yml")
        else:
            print("Creating docker-compose.yml with Dockerfiles...")
            # 创建包含Dockerfile引用的docker-compose.yml
            template = """version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    env_file: ./.env
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend-build:/app/build
"""
            # 使用cat命令创建文件
            ssh.exec_command(f"cat > {REMOTE_PATH}/docker-compose.yml << 'EOF'\n{template}\nEOF")
            print("Docker Compose配置已创建在服务器上")

        # 上传Dockerfile
        print("Uploading Dockerfiles...")
        for dockerfile in ["Dockerfile.backend", "Dockerfile.frontend"]:
            df_path = Path(dockerfile)
            if df_path.exists():
                sftp_upload(sftp, df_path, f"{REMOTE_PATH}/{dockerfile}")

        # 4. 上传源代码
        print("\n[4/5] Uploading source code...")
        backend_src = Path("src/backend/src")
        frontend_src = Path("src/frontend/src")

        if backend_src.exists():
            for py_file in backend_src.rglob("*.py"):
                remote_file = f"{REMOTE_PATH}/{py_file}"
                sftp_upload(sftp, py_file, remote_file)

        if frontend_src.exists():
            for tsx_file in frontend_src.rglob("*.tsx"):
                remote_file = f"{REMOTE_PATH}/{tsx_file}"
                sftp_upload(sftp, tsx_file, remote_file)

        # 5. 构建并启动
        print("\n[5/5] Building and starting services...")
        # 尝试docker compose v2，如果失败则尝试v1
        status, output, error = ssh_exec(ssh, f"cd {REMOTE_PATH} && docker compose up -d --build")
        if status != 0:
            print("Docker Compose v2 failed, trying v1...")
            ssh_exec(ssh, f"cd {REMOTE_PATH} && docker-compose up -d --build")

        print("\n部署完成！")
        print("="*60)
        print(f"\n访问地址:")
        print(f"  API:    http://{SERVER_HOST}:8000")
        print(f"  前端:   http://{SERVER_HOST}:3000")
        print(f"\n管理命令:")
        print(f"  ssh {SERVER_USER}@{SERVER_HOST}")
        print(f"  cd {REMOTE_PATH}")
        print(f"  docker-compose logs -f")
        print(f"  docker-compose restart")

        return True

    finally:
        sftp.close()
        ssh.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
