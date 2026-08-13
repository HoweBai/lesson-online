#!/usr/bin/env python3
"""
一键部署脚本 - tlcw.yobeeo.com
用法: python deploy_to_server.py
"""
import os
import sys
import time
import paramiko
import subprocess
from pathlib import Path

# 配置
SERVER = "tlcw.yobeeo.com"
USER = "root"
PASSWORD = os.environ.get("SSH_PASSWORD", "tlcw_CENTOS@#2023")
REMOTE_PATH = "/opt/ollp"
PROJECT_ROOT = Path(__file__).parent

def log(msg, color=""):
    print(msg)

def run_ssh(ssh, cmd, desc="", timeout=120):
    log(f"\n>>> {desc}")
    log(f"    {cmd[:100]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="ignore").strip()
    err = stderr.read().decode("utf-8", errors="ignore").strip()
    if out:
        for line in out.splitlines()[:15]:
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

    # Use existing build if available
    if build_dir.exists() and (build_dir / "index.html").exists():
        log("Using existing frontend build (skipping rebuild)")
        return True

    npm_path = None
    for p in ["npm.cmd", "npm", "D:/softwares/nodejs/npm.cmd"]:
        import shutil
        found = shutil.which(p) or os.path.exists(p)
        if found:
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
    log("npm install OK")

    log("Building frontend...")
    r = subprocess.run([npm_path, "run", "build"], cwd=str(frontend), capture_output=True, timeout=300)
    if r.returncode != 0:
        log(f"Build failed:\n{r.stderr[-500:]}", "RED")
        return False
    log("Frontend build OK")
    return True

def main():
    log("=" * 60)
    log("  部署到 tlcw.yobeeo.com")
    log("=" * 60)

    # 连接服务器
    log("\n[1/5] 连接服务器...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASSWORD, timeout=15)
    log("[OK] 连接成功")

    try:
        # 构建前端
        if not build_frontend():
            log("前端构建失败", "RED")
            return 1

        sftp = ssh.open_sftp()

        # 上传后端代码
        log("\n[2/5] 上传后端代码...")
        run_ssh(ssh, f"mkdir -p {REMOTE_PATH}/src/backend/src {REMOTE_PATH}/src/backend/tests", "创建目录")
        upload_dir(sftp, PROJECT_ROOT / "src" / "backend" / "src", f"{REMOTE_PATH}/src/backend/src")
        upload_dir(sftp, PROJECT_ROOT / "src" / "backend" / "tests", f"{REMOTE_PATH}/src/backend/tests")
        upload_file(sftp, PROJECT_ROOT / "src" / "backend" / "requirements.txt", f"{REMOTE_PATH}/requirements.txt")
        log("[OK] 后端代码已上传")

        # 上传前端构建
        log("\n[3/5] 上传前端...")
        run_ssh(ssh, f"rm -rf {REMOTE_PATH}/frontend/build && mkdir -p {REMOTE_PATH}/frontend/build", "清理旧构建")
        upload_dir(sftp, PROJECT_ROOT / "src" / "frontend" / "build", f"{REMOTE_PATH}/frontend/build")
        log("[OK] 前端已上传")

        # 更新 nginx 配置
        log("\n[4/5] 更新 nginx 配置...")
        nginx_conf = PROJECT_ROOT / "nginx" / "nginx.production.conf"
        if nginx_conf.exists():
            upload_file(sftp, nginx_conf, f"{REMOTE_PATH}/nginx_conf/nginx.conf")
            log("[OK] nginx 配置已更新")

        sftp.close()

        # 重启后端容器
        log("\n[5/5] 重建后端容器...")
        run_ssh(ssh, f"docker stop ollp-backend 2>/dev/null; docker rm ollp-backend 2>/dev/null || true", "停止旧容器")
        run_ssh(ssh, f"cd {REMOTE_PATH} && docker build -t ollp-backend:latest -f Dockerfile.backend .", "构建镜像", timeout=600)
        run_ssh(ssh, f"docker run -d --name ollp-backend -p 8000:8000 "
                   f"-e DATABASE_URL=sqlite:////opt/ollp/ollp.db "
                   f"-e SECRET_KEY=test "
                   f"-e CRYPTO_KEY_HEX=0000000000000000000000000000000000000000000000000000000000000000 "
                   f"-e FRONTEND_URL=http://tlcw.yobeeo.com "
                   f"-v {REMOTE_PATH}/src:/app/src "
                   f"ollp-backend:latest", "启动新容器", timeout=60)
        time.sleep(5)

        # 验证
        log("\n=== 验证部署 ===")
        run_ssh(ssh, "curl -s http://localhost:8000/health", "健康检查")
        run_ssh(ssh, "curl -s http://localhost/ | head -c 100", "前端检查")
        run_ssh(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}'", "容器状态")

        log("\n" + "=" * 60)
        log("  部署完成!")
        log("  后端: http://tlcw.yobeeo.com:8000/health")
        log("  前端: http://tlcw.yobeeo.com/")
        log("  API:  http://tlcw.yobeeo.com:8000/docs")
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
