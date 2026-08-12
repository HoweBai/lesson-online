#!/usr/bin/env python3
"""
Online Learning Platform - 服务器端直接部署脚本
不使用Docker，直接在服务器上运行
"""

import paramiko
import time
import sys
from pathlib import Path

# 服务器配置
SERVER_HOST = "tlcw.yobeeo.com"
SERVER_USER = "root"
SERVER_PASSWORD = "tlcw_CENTOS@#2023"
REMOTE_PATH = "/opt/online-learning-platform"

def run_command(ssh, command, timeout=120):
    """执行命令"""
    print(f"\n$ {command}")
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    status = stdout.channel.recv_exit_status()

    if output:
        print(output[:1000])
    if error and status != 0:
        print(f"ERROR: {error[:500]}")

    return status, output, error

def main():
    print("="*70)
    print("  Online Learning Platform - 服务器端部署")
    print("="*70)
    print(f"\n服务器: {SERVER_HOST}")
    print(f"路径: {REMOTE_PATH}")
    print()

    # 连接服务器
    print("[1/6] 连接服务器...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print("连接成功!")
    except Exception as e:
        print(f"连接失败: {e}")
        return False

    try:
        # 2. 创建项目目录
        print("\n[2/6] 创建项目目录...")
        run_command(ssh, f"mkdir -p {REMOTE_PATH}/src/backend {REMOTE_PATH}/src/frontend")
        run_command(ssh, f"mkdir -p {REMOTE_PATH}/logs")

        # 3. 上传部署脚本
        print("\n[3/6] 上传部署脚本...")
        script_path = Path("server_deploy.sh")
        if script_path.exists():
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            stdin, stdout, stderr = ssh.exec_command(f"cat > {REMOTE_PATH}/server_deploy.sh")
            stdin.write(content)
            stdin.flush()
            stdin.close()
            run_command(ssh, f"chmod +x {REMOTE_PATH}/server_deploy.sh")
            print("部署脚本已上传")

        # 4. 执行部署
        print("\n[4/6] 执行部署...")
        print("这可能需要几分钟，请耐心等待...")
        status, output, error = run_command(ssh, f"cd {REMOTE_PATH} && bash server_deploy.sh", timeout=600)

        if status != 0:
            print("部署失败，请检查错误信息")
            return False

        # 5. 等待服务启动
        print("\n[5/6] 等待服务启动...")
        time.sleep(10)

        # 6. 验证服务
        print("\n[6/6] 验证服务状态...")
        run_command(ssh, "ps aux | grep -E 'uvicorn|npm' | grep -v grep")
        run_command(ssh, "netstat -tlnp | grep -E '8000|3000'")

        # 健康检查
        print("\n健康检查:")
        for port in [8000, 3000]:
            status, output, error = run_command(ssh, f"curl -s http://localhost:{port}/health || curl -s http://localhost:{port}")
            if "healthy" in output.lower() or "welcome" in output.lower() or "react" in output.lower():
                print(f"  端口 {port}: 正常")
            else:
                print(f"  端口 {port}: {output[:100] or '未响应'}")

        print("\n" + "="*70)
        print("  部署完成！")
        print("="*70)
        print(f"\n访问地址:")
        print(f"  前端应用: http://{SERVER_HOST}:3000")
        print(f"  API文档:  http://{SERVER_HOST}:8000/docs")
        print(f"  健康检查: http://{SERVER_HOST}:8000/health")
        print("\n管理命令:")
        print(f"  SSH登录: ssh {SERVER_USER}@{SERVER_HOST}")
        print(f"  查看日志: tail -f {REMOTE_PATH}/logs/*.log")
        print(f"  停止服务: pkill -f 'uvicorn|npm start'")
        print(f"  重启服务: cd {REMOTE_PATH} && bash server_deploy.sh")
        print("="*70)

        return True

    finally:
        ssh.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
