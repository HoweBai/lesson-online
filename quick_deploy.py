#!/usr/bin/env python3
"""
Online Learning Platform - 服务器直接运行脚本（无Docker）
"""

import paramiko
import time
import sys
import subprocess
from pathlib import Path

SERVER_HOST = "tlcw.yobeeo.com"
SERVER_USER = "root"
SERVER_PASSWORD = "tlcw_CENTOS@#2023"
REMOTE_PATH = "/opt/online-learning-platform"

def run_cmd(ssh, cmd):
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    status = stdout.channel.recv_exit_status()
    if out:
        print(out[:500])
    if err and status != 0:
        print(f"ERROR: {err[:300]}")
    return status, out, err

def main():
    print("="*60)
    print("  Online Learning Platform - 直接部署")
    print("="*60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD)
        print("连接成功!\n")

        # 1. 检查Python
        print("[1/5] 检查Python环境...")
        run_cmd(ssh, "python3 --version")

        # 2. 创建requirements.txt
        print("\n[2/5] 创建requirements.txt...")
        req_content = """fastapi
uvicorn
sqlalchemy
psycopg2-binary
redis
httpx
cryptography
bcrypt
python-multipart
pydantic
python-jose
slowapi
python-dotenv
werkzeug
"""
        stdin, stdout, stderr = ssh.exec_command(f"cat > {REMOTE_PATH}/src/backend/requirements.txt")
        stdin.write(req_content)
        stdin.flush()
        stdin.close()
        print("requirements.txt 已创建")

        # 3. 安装Python依赖
        print("\n[3/5] 安装Python依赖...")
        run_cmd(ssh, f"cd {REMOTE_PATH}/src/backend && pip3 install -r requirements.txt --break-system-packages")

        # 4. 创建启动脚本
        print("\n[4/5] 创建启动脚本...")
        start_script = f"""#!/bin/bash
cd {REMOTE_PATH}/src/backend
nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > {REMOTE_PATH}/logs/backend.log 2>&1 &
echo "后端服务已启动，PID: $!"
"""
        stdin, stdout, stderr = ssh.exec_command(f"cat > {REMOTE_PATH}/start_backend.sh")
        stdin.write(start_script)
        stdin.flush()
        stdin.close()
        run_cmd(ssh, f"chmod +x {REMOTE_PATH}/start_backend.sh")

        # 5. 启动后端
        print("\n[5/5] 启动后端服务...")
        run_cmd(ssh, f"bash {REMOTE_PATH}/start_backend.sh")
        time.sleep(5)

        # 验证
        print("\n验证服务状态...")
        run_cmd(ssh, "ps aux | grep uvicorn | grep -v grep")
        run_cmd(ssh, f"curl -s http://localhost:8000/health || echo '服务未响应'")

        print("\n" + "="*60)
        print("  部署完成!")
        print("="*60)
        print(f"\n访问地址:")
        print(f"  API: http://{SERVER_HOST}:8000")
        print(f"  文档: http://{SERVER_HOST}:8000/docs")
        print(f"\n管理命令:")
        print(f"  ssh root@{SERVER_HOST}")
        print(f"  cd {REMOTE_PATH}")
        print(f"  bash start_backend.sh  # 启动后端")
        print(f"  pkill -f uvicorn       # 停止后端")
        print("="*60)

    finally:
        ssh.close()

if __name__ == "__main__":
    main()
