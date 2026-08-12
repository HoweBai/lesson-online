#!/usr/bin/env python3
"""
Online Learning Platform - 服务器直接运行脚本（修复版）
"""

import paramiko
import time
import sys
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
    print("  Online Learning Platform - 直接部署（修复版）")
    print("="*60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD)
        print("连接成功!\n")

        # 1. 停止旧进程
        print("[1/6] 停止旧进程...")
        run_cmd(ssh, "pkill -f uvicorn 2>/dev/null || true")
        run_cmd(ssh, "pkill -f 'python.*uvicorn' 2>/dev/null || true")

        # 2. 创建启动脚本（设置正确的PYTHONPATH）
        print("\n[2/6] 创建启动脚本...")
        start_script = f"""#!/bin/bash
cd {REMOTE_PATH}
export PYTHONPATH="${{PYTHONPATH}}:{REMOTE_PATH}"
nohup python3 -m src.api.main > {REMOTE_PATH}/logs/backend.log 2>&1 &
echo "后端服务已启动，PID: $!"
sleep 3
tail -10 {REMOTE_PATH}/logs/backend.log
"""
        stdin, stdout, stderr = ssh.exec_command(f"cat > {REMOTE_PATH}/start_backend.sh")
        stdin.write(start_script)
        stdin.flush()
        stdin.close()
        run_cmd(ssh, f"chmod +x {REMOTE_PATH}/start_backend.sh")

        # 3. 启动后端
        print("\n[3/6] 启动后端服务...")
        run_cmd(ssh, f"bash {REMOTE_PATH}/start_backend.sh")
        time.sleep(5)

        # 4. 检查进程
        print("\n[4/6] 检查进程...")
        run_cmd(ssh, "ps aux | grep -E 'python|uvicorn' | grep -v grep")

        # 5. 检查日志
        print("\n[5/6] 检查日志...")
        run_cmd(ssh, f"tail -30 {REMOTE_PATH}/logs/backend.log")

        # 6. 健康检查
        print("\n[6/6] 健康检查...")
        time.sleep(3)
        run_cmd(ssh, "curl -s http://localhost:8000/health || echo '服务尚未响应'")

        print("\n" + "="*60)
        print("  部署完成!")
        print("="*60)
        print(f"\n访问地址:")
        print(f"  API: http://{SERVER_HOST}:8000")
        print(f"  文档: http://{SERVER_HOST}:8000/docs")
        print(f"  健康: http://{SERVER_HOST}:8000/health")
        print("\n管理命令:")
        print(f"  启动: cd {REMOTE_PATH} && bash start_backend.sh")
        print(f"  日志: tail -f {REMOTE_PATH}/logs/backend.log")
        print(f"  停止: pkill -f uvicorn")
        print("="*60)

    finally:
        ssh.close()

if __name__ == "__main__":
    main()
