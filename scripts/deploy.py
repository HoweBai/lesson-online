#!/usr/bin/env python3
"""
一键部署脚本 - Online Learning Platform

用法:
  python deploy.py --host <服务器IP或域名> --user root --domain <你的域名>

示例:
  python deploy.py --host 1.2.3.4 --user root --domain example.com
  python deploy.py --host example.com --user root --password 'your_ssh_password'
  python deploy.py --host example.com --user root --key ~/.ssh/id_rsa
"""

import argparse
import getpass
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path

# 尝试导入 paramiko，如果没有则提示安装
try:
    import paramiko
except ImportError:
    print("错误: 需要 paramiko 库。请运行: pip install paramiko")
    sys.exit(1)

# 配置
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
REMOTE_BASE_DIR = "/opt/ollp"
DOCKER_COMPOSE_FILE = "docker-compose.production.yml"
VERSION = "1.2.0"


def log(msg: str, prefix: str = ">>>", color: str = ""):
    """打印日志消息"""
    print(f"{color}{prefix} {msg}")


def run_local(cmd: list[str], desc: str = "") -> tuple[str, str, int]:
    """本地执行命令"""
    if desc:
        log(f"执行本地命令: {desc}")
    log(f"  命令: {' '.join(cmd[:80])}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.stdout.strip():
            for line in result.stdout.strip().splitlines()[:20]:
                log(f"  OUT: {line}")
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines()[:5]:
                log(f"  ERR: {line}")
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        log("命令超时", color="\033[31m")
        return "", "Timeout", 1
    except Exception as e:
        log(f"执行失败: {e}", color="\033[31m")
        return "", str(e), 1


def generate_secrets() -> dict[str, str]:
    """生成安全随机密钥"""
    return {
        "SECRET_KEY": secrets.token_hex(32),
        "CRYPTO_KEY_HEX": secrets.token_hex(32),
        "POSTGRES_PASSWORD": secrets.token_hex(24),
        "MINIO_ACCESS_KEY": secrets.token_hex(16),
        "MINIO_SECRET_KEY": secrets.token_hex(32),
    }


def get_ssh_client(host: str, user: str, password: str = None, key_file: str = None) -> paramiko.SSHClient:
    """创建 SSH 连接"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {
        "hostname": host,
        "username": user,
        "timeout": 30,
    }

    if key_file:
        connect_kwargs["key_filename"] = key_file
    elif password:
        connect_kwargs["password"] = password
    else:
        # 尝试使用系统代理的 SSH 配置
        connect_kwargs["look_for_keys"] = True
        connect_kwargs["allow_agent"] = True

    try:
        client.connect(**connect_kwargs)
        return client
    except Exception as e:
        log(f"SSH 连接失败: {e}", color="\033[31m")
        if password is None and key_file is None:
            log("提示: 请提供密码 (--password) 或私钥文件 (--key)", color="\033[33m")
        raise


def run_remote(ssh: paramiko.SSHClient, cmd: str, desc: str = "", timeout: int = 300) -> tuple[str, str]:
    """远程执行命令"""
    log(f"\n>>> {desc}")
    log(f"    {cmd[:120]}")

    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    output = stdout.read().decode("utf-8", errors="ignore").strip()
    error = stderr.read().decode("utf-8", errors="ignore").strip()

    if output:
        for line in output.splitlines()[:25]:
            log(f"    {line}")
    if error and output:
        for line in error.splitlines()[:5]:
            log(f"    ERR: {line}", color="\033[31m")

    return output, error


def check_docker(ssh: paramiko.SSHClient) -> bool:
    """检查 Docker 是否已安装"""
    _, err = run_remote(ssh, "docker --version", "检查 Docker 版本")
    return err == ""


def install_docker(ssh: paramiko.SSHClient, os_type: str):
    """安装 Docker"""
    if os_type == "ubuntu" or os_type == "debian":
        cmds = [
            "apt-get update",
            "apt-get install -y ca-certificates curl gnupg lsb-release",
            "install -m 0755 -d /etc/apt/keyrings",
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
            "chmod a+r /etc/apt/keyrings/docker.gpg",
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null',
            "apt-get update",
            "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
            "usermod -aG docker root",
        ]
    else:
        # CentOS/RHEL/Fedora
        cmds = [
            "yum install -y yum-utils",
            'yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo',
            "yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
            "systemctl start docker",
            "systemctl enable docker",
            "usermod -aG docker root",
        ]

    for cmd in cmds:
        run_remote(ssh, cmd, f"安装 Docker: {cmd[:50]}...")


def configure_docker_mirror(ssh: paramiko.SSHClient):
    """配置 Docker 镜像加速（中国大陆服务器必需）"""
    log("\n>>> 配置 Docker 镜像加速")

    # 检查是否已配置镜像
    _, output = run_remote(ssh, "cat /etc/docker/daemon.json 2>/dev/null || echo '{}'", "检查 Docker 配置")

    import json
    try:
        config = json.loads(output.strip()) if output.strip() != '{}' else {}
    except json.JSONDecodeError:
        config = {}

    # 腾讯云镜像源
    mirrors = ["https://mirror.ccs.tencentyun.com"]

    # 检查是否已配置
    existing = config.get("registry-mirrors", [])
    for mirror in mirrors:
        if mirror not in existing:
            existing.append(mirror)
    config["registry-mirrors"] = existing

    # 写入配置
    docker_conf = json.dumps(config, indent=2)
    run_remote(ssh, f"echo '{docker_conf}' > /etc/docker/daemon.json", "写入 Docker 镜像配置")
    run_remote(ssh, "systemctl daemon-reload && systemctl restart docker", "重启 Docker 服务")

    # 验证配置
    _, result = run_remote(ssh, "docker info | grep -A 5 'Registry Mirrors'", "验证镜像配置")
    log(f"  Docker 镜像加速已配置:\n{result}")


def setup_nginx(ssh: paramiko.SSHClient, domain: str):
    """配置 Nginx"""
    # 创建 nginx 配置目录
    run_remote(ssh, f"mkdir -p {REMOTE_BASE_DIR}/nginx/ssl", "创建 nginx 目录")

    # 复制 nginx 配置（使用域名）
    nginx_conf = generate_nginx_config(domain)
    run_remote(ssh, f"cat > {REMOTE_BASE_DIR}/nginx/nginx.production.conf << 'NGINX_EOF'\n{nginx_conf}\nNGINX_EOF", "写入 nginx 配置")


def generate_nginx_config(domain: str) -> str:
    """生成 nginx 配置"""
    return f"""# Production Nginx Configuration for Online Learning Platform
# Domain: {domain}

worker_processes auto;
events {{ worker_connections 1024; }}
http {{
    include mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    gzip on;

    # DNS resolver for Docker internal DNS
    resolver 127.0.0.11 valid=30s ipv6=off;

    # HTTP server - redirect to HTTPS
    server {{
        listen 80;
        server_name {domain};
        return 301 https://$host$request_uri;
    }}

    # HTTPS server
    server {{
        listen 443 ssl http2;
        server_name {domain};

        # SSL Certificate (Let's Encrypt)
        ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # API routes - proxy to backend
        location /api/ {{
            proxy_pass http://ollp-backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }}

        # WebSocket support
        location /ws/ {{
            proxy_pass http://ollp-backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 86400s;
            proxy_send_timeout 86400s;
        }}

        # Backend admin endpoints
        location /health {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}
        location /docs {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}
        location /redoc {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}
        location /monitor {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}
        location /admin {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}

        # Frontend - proxy to React build
        location / {{
            proxy_pass http://ollp-frontend:80;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }}

        # Deny access to hidden files
        location ~ /\\. {{ deny all; }}
    }}
}}
"""


def setup_certbot(ssh: paramiko.SSHClient, domain: str):
    """配置 Let's Encrypt SSL 证书"""
    # 先允许 HTTP 流量（在重定向之前）
    run_remote(ssh, "ufw allow 80/tcp 2>/dev/null || iptables -I INPUT -p tcp --dport 80 -j ACCEPT || true",
               "开放 HTTP 端口")
    run_remote(ssh, "ufw allow 443/tcp 2>/dev/null || iptables -I INPUT -p tcp --dport 443 -j ACCEPT || true",
               "开放 HTTPS 端口")

    # 安装 certbot
    run_remote(ssh, "apt-get install -y certbot python3-certbot-nginx", "安装 Certbot")

    # 创建临时 nginx 配置用于证书颁发
    temp_conf = f"""server {{
    listen 80;
    server_name {domain};
    root /var/www/html;
    location / {{ return 200 'OK'; }}
    location /.well-known/acme-challenge/ {{ root /var/www/html; }}
}}"""

    run_remote(ssh, f"mkdir -p /var/www/html && cat > /etc/nginx/sites-enabled/default << 'EOF'\n{temp_conf}\nEOF",
               "创建临时 nginx 配置")
    run_remote(ssh, "nginx -t && systemctl reload nginx", "测试并重载 nginx")

    # 获取证书
    run_remote(ssh, f"certbot --nginx -d {domain} --non-interactive --agree-tos -m admin@{domain} --redirect",
               "申请 SSL 证书 (Let's Encrypt)")

    # 恢复 nginx 配置（certbot 会修改站点配置）
    run_remote(ssh, f"rm -f /etc/nginx/sites-enabled/default && rm -f /etc/nginx/sites-available/default",
               "清理临时配置")


def upload_files(ssh: paramiko.SSHClient):
    """通过 Tarball 下载项目代码到服务器"""
    log("\n>>> 获取项目代码")

    # 备份旧数据并下载最新代码（使用 tarball 方式，无需 git）
    backup_dir = f"{REMOTE_BASE_DIR}_backup_{int(time.time())}"
    run_remote(ssh, f"mkdir -p {backup_dir} && [ -d {REMOTE_BASE_DIR} ] && mv {REMOTE_BASE_DIR}/* {backup_dir}/ 2>/dev/null || true",
               "备份旧数据")
    run_remote(ssh,
               f"rm -rf {REMOTE_BASE_DIR} && curl -L https://github.com/HoweBai/lesson-online/archive/refs/heads/main.tar.gz -o /tmp/lesson-online.tar.gz --max-time 120 && tar -xzf /tmp/lesson-online.tar.gz -C /opt && mv /opt/lesson-online-main {REMOTE_BASE_DIR} && rm /tmp/lesson-online.tar.gz",
               "下载项目代码 (tarball)")

    # 验证下载
    _, output = run_remote(ssh, f"ls {REMOTE_BASE_DIR}/src/frontend/", "验证代码结构")
    if "Dockerfile.production" not in output:
        log("  [警告] Dockerfile.production 未找到，尝试修复...", color="\033[33m")
        run_remote(ssh, f"cp {PROJECT_DIR}/src/frontend/Dockerfile.production {REMOTE_BASE_DIR}/src/frontend/ 2>/dev/null || true")
        run_remote(ssh, f"cp {PROJECT_DIR}/src/frontend/nginx.frontend.conf {REMOTE_BASE_DIR}/src/frontend/ 2>/dev/null || true")

    log(f"  项目代码已就绪: {REMOTE_BASE_DIR}")


def create_env_file(ssh: paramiko.SSHClient, secrets: dict[str, str], domain: str):
    """创建 .env 文件"""
    env_content = f"""# ==================== Security Keys ====================
SECRET_KEY={secrets['SECRET_KEY']}
CRYPTO_KEY_HEX={secrets['CRYPTO_KEY_HEX']}
POSTGRES_PASSWORD={secrets['POSTGRES_PASSWORD']}
MINIO_ACCESS_KEY={secrets['MINIO_ACCESS_KEY']}
MINIO_SECRET_KEY={secrets['MINIO_SECRET_KEY']}

# ==================== Network ====================
DOMAIN={domain}
ALLOWED_HOSTS=*

# ==================== Logging ====================
LOG_LEVEL=info
"""

    run_remote(ssh, f"cat > {REMOTE_BASE_DIR}/.env << 'ENV_EOF'\n{env_content}\nENV_EOF",
               "创建 .env 文件")
    log("  .env 文件已创建")


def deploy_docker(ssh: paramiko.SSHClient):
    """部署 Docker 容器"""
    log("\n>>> 部署 Docker 容器")

    # 停止旧容器
    run_remote(ssh, f"cd {REMOTE_BASE_DIR} && docker compose -f {DOCKER_COMPOSE_FILE} down --remove-orphans",
               "停止旧容器")

    # 构建并启动容器
    run_remote(ssh,
               f"cd {REMOTE_BASE_DIR} && docker compose -f {DOCKER_COMPOSE_FILE} up -d --build",
               "构建并启动容器", timeout=600)


def wait_for_services(ssh: paramiko.SSHClient, timeout: int = 120):
    """等待服务就绪"""
    log("\n>>> 等待服务就绪")

    end_time = time.time() + timeout
    while time.time() < end_time:
        status, _ = run_remote(ssh,
                               f"docker compose -f {REMOTE_BASE_DIR}/{DOCKER_COMPOSE_FILE} ps --format json",
                               "检查服务状态")
        if "healthy" in status or "running" in status.lower():
            log("  服务已启动")
            return True
        time.sleep(5)

    return False


def verify_deployment(ssh: paramiko.SSHClient, domain: str):
    """验证部署"""
    log("\n>>> 验证部署")

    # 检查容器状态
    status, _ = run_remote(ssh,
                           f"docker compose -f {REMOTE_BASE_DIR}/{DOCKER_COMPOSE_FILE} ps",
                           "容器状态")

    # 检查健康状态
    health, _ = run_remote(ssh,
                           f"curl -s http://localhost/health",
                           "健康检查")

    log(f"\n{'='*60}")
    log(f"部署完成!")
    log(f"{'='*60}")
    log(f"  主站:   https://{domain}/")
    log(f"  API:    https://{domain}/docs")
    log(f"  健康:   https://{domain}/health")
    log(f"  默认管理员: admin@ollp.local / ollp_admin_2024")
    log(f"{'='*60}")

    return health


def main():
    parser = argparse.ArgumentParser(
        description="Online Learning Platform - 一键部署脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用密码登录
  python deploy.py --host 1.2.3.4 --user root --domain example.com --password 'your_password'

  # 使用 SSH 私钥登录
  python deploy.py --host example.com --user root --domain example.com --key ~/.ssh/id_rsa

  # 交互模式（会提示输入密码）
  python deploy.py --host example.com --user root --domain example.com
        """
    )

    parser.add_argument("--host", required=True, help="服务器 IP 或域名")
    parser.add_argument("--user", default="root", help="SSH 用户名 (默认: root)")
    parser.add_argument("--domain", required=True, help="服务器绑定的域名")
    parser.add_argument("--password", help="SSH 密码（可选，建议使用 --key）")
    parser.add_argument("--key", help="SSH 私钥文件路径")
    parser.add_argument("--no-certbot", action="store_true", help="跳过 SSL 证书申请")

    args = parser.parse_args()

    # 如果没有提供密码且没有密钥文件，尝试交互式输入
    password = args.password
    if not password and not args.key:
        # 检查是否有 SSH agent 或已知密钥
        try:
            password = getpass.getpass("请输入 SSH 密码: ")
        except Exception:
            log("无法获取密码，请使用 --password 或 --key 参数", color="\033[33m")
            sys.exit(1)

    log(f"\n{'='*60}")
    log(f"Online Learning Platform 一键部署")
    log(f"版本: {VERSION}")
    log(f"目标服务器: {args.host}")
    log(f"域名: {args.domain}")
    log(f"{'='*60}\n")

    ssh = None
    try:
        # 1. 连接服务器
        ssh = get_ssh_client(args.host, args.user, password, args.key)
        log("[OK] SSH 连接成功")

        # 2. 检查 Docker
        docker_ok = check_docker(ssh)
        if not docker_ok:
            log("[!] Docker 未安装，开始安装...")
            run_remote(ssh, "cat /etc/os-release | grep -E 'ID|VERSION' | head -3", "检测系统类型")
            os_result, _ = run_remote(ssh, "cat /etc/os-release | grep '^ID=' | cut -d= -f2", "获取 OS ID")
            install_docker(ssh, os_result.strip().lower())
            log("[OK] Docker 安装完成")
        configure_docker_mirror(ssh)

        # 3. 检查域名 DNS
        log(f"\n>>> 检查域名 DNS")
        try:
            ip = socket.gethostbyname(args.domain)
            log(f"  域名解析: {args.domain} -> {ip}")
        except socket.gaierror as e:
            log(f"  [警告] DNS 解析失败: {e}", color="\033[33m")
            log(f"  请确保域名已正确指向服务器 IP: {args.host}")
            answer = input("继续部署? (y/N): ")
            if answer.lower() != 'y':
                sys.exit(0)

        # 4. 生成密钥
        log(f"\n>>> 生成安全密钥")
        secrets = generate_secrets()
        log(f"  SECRET_KEY: {secrets['SECRET_KEY'][:16]}...")
        log(f"  POSTGRES_PASSWORD: {secrets['POSTGRES_PASSWORD'][:16]}...")

        # 5. 创建配置目录
        run_remote(ssh, f"mkdir -p {REMOTE_BASE_DIR}", "创建项目目录")
        run_remote(ssh, "systemctl enable docker 2>/dev/null || true", "启用 Docker 服务")

        # 6. 上传文件
        upload_files(ssh)

        # 7. 创建 .env 文件
        create_env_file(ssh, secrets, args.domain)

        # 8. 设置 Nginx（不使用 certbot 自动配置，因为我们要用自定义配置）
        if not args.no_certbot:
            setup_nginx(ssh, args.domain)
            setup_certbot(ssh, args.domain)
        else:
            setup_nginx(ssh, args.domain)
            log("  跳过 SSL 证书申请 (--no-certbot)")
            log("  请手动配置 SSL 证书或使用自签名证书")

        # 9. 部署 Docker 容器
        deploy_docker(ssh)

        # 10. 等待服务就绪
        if wait_for_services(ssh):
            # 11. 验证部署
            verify_deployment(ssh, args.domain)

            # 12. 输出初始管理员信息
            log(f"\n{'='*60}")
            log(f"初始管理员账户:")
            log(f"  邮箱: admin@ollp.local")
            log(f"  密码: ollp_admin_2024")
            log(f"  (请登录后立即修改密码!)")
            log(f"{'='*60}\n")
        else:
            log("[!] 部分服务可能未就绪，请检查日志", color="\033[33m")
            run_remote(ssh, f"docker compose -f {REMOTE_BASE_DIR}/{DOCKER_COMPOSE_FILE} logs --tail=20",
                       "查看服务日志")

    except KeyboardInterrupt:
        log("\n操作已取消", color="\033[33m")
        sys.exit(1)
    except Exception as e:
        log(f"\n部署失败: {e}", color="\033[31m")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if ssh:
            ssh.close()


if __name__ == "__main__":
    main()
