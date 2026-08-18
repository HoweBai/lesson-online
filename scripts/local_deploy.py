#!/usr/bin/env python3
"""
本地一键部署脚本 - Online Learning Platform
在服务器上直接运行，无需 SSH 跳转

用法:
  python local_deploy.py --domain <你的域名>
  python local_deploy.py --domain <你的域名> --no-certbot

示例:
  python local_deploy.py --domain tlcw.yobeeo.com
  python local_deploy.py --domain example.com --no-certbot
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

# 配置
PROJECT_DIR = Path(__file__).parent.parent
REMOTE_BASE_DIR = "/opt/ollp"
DOCKER_COMPOSE_FILE = "docker-compose.production.yml"
VERSION = "1.2.0"


def log(msg: str, prefix: str = ">>>", color: str = ""):
    """打印日志消息"""
    print(f"{color}{prefix} {msg}")


def run_cmd(cmd: str, desc: str = "", timeout: int = 300) -> tuple[str, str, int]:
    """执行命令"""
    log(f"\n>>> {desc}")
    log(f"    {cmd[:120]}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_DIR)
        )
        output = result.stdout.strip()
        error = result.stderr.strip()

        if output:
            for line in output.splitlines()[:25]:
                log(f"    {line}")
        if error and output:
            for line in error.splitlines()[:5]:
                log(f"    ERR: {line}", color="\033[31m")

        return output, error, result.returncode
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


def check_docker() -> bool:
    """检查 Docker 是否已安装"""
    _, err, _ = run_cmd("docker --version", "检查 Docker 版本")
    return err == ""


def install_docker(os_type: str):
    """安装 Docker"""
    if os_type in ("ubuntu", "debian"):
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
        cmds = [
            "yum install -y yum-utils",
            'yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo',
            "yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
            "systemctl start docker",
            "systemctl enable docker",
            "usermod -aG docker root",
        ]

    for cmd in cmds:
        run_cmd(cmd, f"安装 Docker: {cmd[:50]}...")


def configure_docker_mirror():
    """配置 Docker 镜像加速"""
    log("\n>>> 配置 Docker 镜像加速")

    _, output, _ = run_cmd("cat /etc/docker/daemon.json 2>/dev/null || echo '{}'", "检查 Docker 配置")

    try:
        config = json.loads(output.strip()) if output.strip() != '{}' else {}
    except json.JSONDecodeError:
        config = {}

    mirrors = ["https://mirror.ccs.tencentyun.com"]
    existing = config.get("registry-mirrors", [])
    for mirror in mirrors:
        if mirror not in existing:
            existing.append(mirror)
    config["registry-mirrors"] = existing

    docker_conf = json.dumps(config, indent=2)
    run_cmd(f"echo '{docker_conf}' > /etc/docker/daemon.json", "写入 Docker 镜像配置")
    run_cmd("systemctl daemon-reload && systemctl restart docker", "重启 Docker 服务")

    _, result, _ = run_cmd("docker info | grep -A 5 'Registry Mirrors'", "验证镜像配置")
    log(f"  Docker 镜像加速已配置:\n{result}")


def setup_nginx(domain: str):
    """配置 Nginx"""
    run_cmd(f"mkdir -p {REMOTE_BASE_DIR}/nginx/ssl", "创建 nginx 目录")

    # 复制 nginx 配置
    nginx_conf = generate_nginx_config(domain)
    run_cmd(f"cat > {REMOTE_BASE_DIR}/nginx/nginx.production.conf << 'NGINX_EOF'\n{nginx_conf}\nNGINX_EOF", "写入 nginx 配置")


def generate_nginx_config(domain: str) -> str:
    """生成 nginx 配置"""
    return f"""worker_processes auto;
events {{ worker_connections 1024; }}
http {{
    include mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    gzip on;

    resolver 127.0.0.11 valid=30s ipv6=off;

    server {{
        listen 80;
        server_name {domain};
        return 301 https://$host$request_uri;
    }}

    server {{
        listen 443 ssl http2;
        server_name {domain};

        ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

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

        location /health {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}
        location /docs {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}
        location /redoc {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}
        location /monitor {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}
        location /admin {{ proxy_pass http://ollp-backend:8000; proxy_set_header Host $host; }}

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

        location ~ /\\. {{ deny all; }}
    }}
}}
"""


def setup_certbot(domain: str):
    """配置 Let's Encrypt SSL 证书"""
    run_cmd("ufw allow 80/tcp 2>/dev/null || iptables -I INPUT -p tcp --dport 80 -j ACCEPT || true", "开放 HTTP 端口")
    run_cmd("ufw allow 443/tcp 2>/dev/null || iptables -I INPUT -p tcp --dport 443 -j ACCEPT || true", "开放 HTTPS 端口")
    run_cmd("apt-get install -y certbot python3-certbot-nginx", "安装 Certbot")

    temp_conf = f"""server {{
    listen 80;
    server_name {domain};
    root /var/www/html;
    location / {{ return 200 'OK'; }}
    location /.well-known/acme-challenge/ {{ root /var/www/html; }}
}}"""

    run_cmd(f"mkdir -p /var/www/html && cat > /etc/nginx/sites-enabled/default << 'EOF'\n{temp_conf}\nEOF", "创建临时 nginx 配置")
    run_cmd("nginx -t && systemctl reload nginx", "测试并重载 nginx")
    run_cmd(f"certbot --nginx -d {domain} --non-interactive --agree-tos -m admin@{domain} --redirect", "申请 SSL 证书")
    run_cmd("rm -f /etc/nginx/sites-enabled/default && rm -f /etc/nginx/sites-available/default", "清理临时配置")


def setup_local():
    """本地部署流程"""
    log(f"\n{'='*60}")
    log(f"Online Learning Platform 本地部署")
    log(f"版本: {VERSION}")
    log(f"{'='*60}\n")

    # 1. 检查 Docker
    log("\n>>> 1. 检查 Docker")
    docker_ok = check_docker()
    if not docker_ok:
        log("[!] Docker 未安装，开始安装...")
        run_cmd("cat /etc/os-release | grep -E 'ID|VERSION' | head -3", "检测系统类型")
        os_result, _ = run_cmd("cat /etc/os-release | grep '^ID=' | cut -d= -f2", "获取 OS ID")
        install_docker(os_result.strip().lower())
        log("[OK] Docker 安装完成")
    configure_docker_mirror()

    # 2. 检查域名 DNS
    log(f"\n>>> 2. 检查域名 DNS")
    try:
        ip = socket.gethostbyname(args.domain)
        log(f"  域名解析: {args.domain} -> {ip}")
    except socket.gaierror as e:
        log(f"  [警告] DNS 解析失败: {e}", color="\033[33m")
        log(f"  请确保域名已正确指向服务器 IP")

    # 3. 生成密钥
    log(f"\n>>> 3. 生成安全密钥")
    secrets = generate_secrets()
    log(f"  SECRET_KEY: {secrets['SECRET_KEY'][:16]}...")
    log(f"  POSTGRES_PASSWORD: {secrets['POSTGRES_PASSWORD'][:16]}...")

    # 4. 创建配置目录
    run_cmd(f"mkdir -p {REMOTE_BASE_DIR}", "创建项目目录")
    run_cmd("systemctl enable docker 2>/dev/null || true", "启用 Docker 服务")

    # 5. 创建 .env 文件
    run_cmd(f"cat > {REMOTE_BASE_DIR}/.env << 'ENV_EOF'\n"
            f"SECRET_KEY={secrets['SECRET_KEY']}\n"
            f"CRYPTO_KEY_HEX={secrets['CRYPTO_KEY_HEX']}\n"
            f"POSTGRES_PASSWORD={secrets['POSTGRES_PASSWORD']}\n"
            f"MINIO_ACCESS_KEY={secrets['MINIO_ACCESS_KEY']}\n"
            f"MINIO_SECRET_KEY={secrets['MINIO_SECRET_KEY']}\n"
            f"DOMAIN={args.domain}\n"
            f"ALLOWED_HOSTS=*\n"
            f"LOG_LEVEL=info\n"
            f"ENV_EOF", "创建 .env 文件")
    log("  .env 文件已创建")

    # 6. 复制 docker-compose 文件
    run_cmd(f"cp {PROJECT_DIR}/docker-compose.production.yml {REMOTE_BASE_DIR}/", "复制 docker-compose 文件")
    run_cmd(f"cp -r {PROJECT_DIR}/nginx {REMOTE_BASE_DIR}/", "复制 nginx 配置")

    # 7. 设置 Nginx
    setup_nginx(args.domain)

    if not args.no_certbot:
        setup_certbot(args.domain)
    else:
        log("  跳过 SSL 证书申请 (--no-certbot)")

    # 8. 部署 Docker 容器
    log("\n>>> 8. 部署 Docker 容器")
    run_cmd(f"cd {REMOTE_BASE_DIR} && docker compose -f {DOCKER_COMPOSE_FILE} down --remove-orphans", "停止旧容器")
    run_cmd(f"cd {REMOTE_BASE_DIR} && docker compose -f {DOCKER_COMPOSE_FILE} up -d --build", "构建并启动容器", timeout=600)

    # 9. 等待服务就绪
    log("\n>>> 9. 等待服务就绪")
    if wait_for_services():
        # 10. 运行数据库迁移
        log("\n>>> 10. 应用数据库外键约束")
        fk_sql = (
            "ALTER TABLE tutorials DROP CONSTRAINT IF EXISTS tutorials_owner_id_fkey; "
            "ALTER TABLE tutorials ADD CONSTRAINT tutorials_owner_id_fkey "
            "FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE; "
            "ALTER TABLE public_catalog DROP CONSTRAINT IF EXISTS public_catalog_published_by_fkey; "
            "ALTER TABLE public_catalog ADD CONSTRAINT public_catalog_published_by_fkey "
            "FOREIGN KEY (published_by) REFERENCES users(id) ON DELETE CASCADE; "
            "ALTER TABLE public_catalog DROP CONSTRAINT IF EXISTS public_catalog_approved_by_fkey; "
            "ALTER TABLE public_catalog ADD CONSTRAINT public_catalog_approved_by_fkey "
            "FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL; "
            "ALTER TABLE task_logs DROP CONSTRAINT IF EXISTS task_logs_user_id_fkey; "
            "ALTER TABLE task_logs ADD CONSTRAINT task_logs_user_id_fkey "
            "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;"
        )
        run_cmd(f"docker exec ollp-db psql -U ollp_user -d ollp_db -c '{fk_sql}'", "修复外键约束")

        log(f"\n{'='*60}")
        log(f"部署完成!")
        log(f"{'='*60}")
        log(f"  主站:   https://{args.domain}/")
        log(f"  API:    https://{args.domain}/docs")
        log(f"  健康:   https://{args.domain}/health")
        log(f"  管理员: admin@ollp.local / ollp_admin_2024")
        log(f"{'='*60}\n")
    else:
        log("[!] 部分服务可能未就绪，请检查日志", color="\033[33m")
        run_cmd(f"docker compose -f {REMOTE_BASE_DIR}/{DOCKER_COMPOSE_FILE} logs --tail=20", "查看服务日志")


def wait_for_services(timeout: int = 120) -> bool:
    """等待服务就绪"""
    log("\n>>> 等待服务就绪")
    end_time = time.time() + timeout
    while time.time() < end_time:
        status, _, _ = run_cmd(
            f"docker compose -f {REMOTE_BASE_DIR}/{DOCKER_COMPOSE_FILE} ps --format json"
        )
        if "healthy" in status or "running" in status.lower():
            log("  服务已启动")
            return True
        time.sleep(5)
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Online Learning Platform - 本地一键部署脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 本地部署
  python local_deploy.py --domain example.com

  # 跳过 SSL 证书
  python local_deploy.py --domain example.com --no-certbot
        """
    )

    parser.add_argument("--domain", required=True, help="服务器绑定的域名")
    parser.add_argument("--no-certbot", action="store_true", help="跳过 SSL 证书申请")

    global args
    args = parser.parse_args()
    main_local()


def main_local():
    try:
        setup_local()
    except KeyboardInterrupt:
        log("\n操作已取消", color="\033[33m")
        sys.exit(1)
    except Exception as e:
        log(f"\n部署失败: {e}", color="\033[31m")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
