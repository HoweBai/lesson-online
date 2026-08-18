#!/usr/bin/env python3
"""
卸载脚本 - 卸载 Online Learning Platform 所有服务

用法:
  python uninstall.py --host <服务器IP或域名> --user root [--key ~/.ssh/id_rsa] [--keep-data]
"""

import argparse
import getpass
import sys
import time

try:
    import paramiko
except ImportError:
    print("错误: 需要 paramiko 库。请运行: pip install paramiko")
    sys.exit(1)

REMOTE_BASE_DIR = "/opt/ollp"
DOCKER_COMPOSE_FILE = "docker-compose.production.yml"


def log(msg: str, prefix: str = ">>>", color: str = ""):
    print(f"{color}{prefix} {msg}")


def run_remote(ssh, cmd: str, desc: str = "", timeout: int = 60) -> tuple[str, str]:
    log(f"\n>>> {desc}")
    log(f"    {cmd[:120]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    output = stdout.read().decode("utf-8", errors="ignore").strip()
    error = stderr.read().decode("utf-8", errors="ignore").strip()
    if output:
        for line in output.splitlines()[:20]:
            log(f"    {line}")
    if error and output:
        for line in error.splitlines()[:5]:
            log(f"    ERR: {line}", color="\033[31m")
    return output, error


def get_ssh_client(host: str, user: str, password: str = None, key_file: str = None):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = {"hostname": host, "username": user, "timeout": 30}
    if key_file:
        kwargs["key_filename"] = key_file
    elif password:
        kwargs["password"] = password
    else:
        kwargs["look_for_keys"] = True
        kwargs["allow_agent"] = True
    client.connect(**kwargs)
    return client


def run_uninstall(ssh, keep_data: bool = False):
    log(f"\n{'='*60}")
    log(f"Online Learning Platform 卸载")
    log(f"{'='*60}\n")

    if not keep_data:
        answer = input("警告: 这将删除所有数据（数据库、对象存储、备份）！确认卸载? (yes/no): ")
        if answer.strip().lower() != 'yes':
            log("已取消")
            return
    else:
        log("  保留数据模式 (--keep-data)，仅停止并删除容器和镜像\n")

    # 1. 停止容器
    log("\n>>> 1. 停止 Docker 容器")
    run_remote(ssh, f"cd {REMOTE_BASE_DIR} && docker compose -f {DOCKER_COMPOSE_FILE} down 2>/dev/null || true",
               "停止容器")

    # 2. 删除容器
    log("\n>>> 2. 删除 Docker 容器")
    run_remote(ssh, f"cd {REMOTE_BASE_DIR} && docker compose -f {DOCKER_COMPOSE_FILE} rm -f 2>/dev/null || true",
               "删除容器")

    # 3. 删除卷和网络
    log("\n>>> 3. 删除 Docker 卷和网络")
    run_remote(ssh, "docker volume ls -q | grep -E 'ollp_' | xargs -r docker volume rm",
               "删除卷")
    run_remote(ssh, "docker network ls -q | grep -E 'ollp' | xargs -r docker network rm",
               "删除网络")

    # 4. 删除镜像
    log("\n>>> 4. 删除 Docker 镜像")
    run_remote(ssh, "docker images -q ollp-* 2>/dev/null | xargs -r docker rmi -f",
               "删除 ollp 镜像")

    # 5. 清理 Nginx
    log("\n>>> 5. 清理 Nginx 配置")
    run_remote(ssh, "rm -f /etc/nginx/nginx.conf", "移除 nginx 配置")
    run_remote(ssh, "systemctl stop nginx 2>/dev/null || true", "停止 nginx")
    run_remote(ssh, "apt-get remove -y nginx 2>/dev/null || yum remove -y nginx 2>/dev/null || true",
               "卸载 nginx")
    run_remote(ssh, "rm -rf /etc/nginx 2>/dev/null || true", "清理 nginx 目录")
    run_remote(ssh, "certbot delete --non-interactive 2>/dev/null || true", "删除 SSL 证书")
    run_remote(ssh, "rm -rf /etc/letsencrypt 2>/dev/null || true", "清理 letsencrypt 目录")
    run_remote(ssh, "ufw delete allow 80/tcp 2>/dev/null || iptables -D INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true",
               "关闭 HTTP 端口")
    run_remote(ssh, "ufw delete allow 443/tcp 2>/dev/null || iptables -D INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true",
               "关闭 HTTPS 端口")

    # 6. 删除项目目录
    log("\n>>> 6. 删除项目目录")
    if not keep_data:
        run_remote(ssh, f"rm -rf {REMOTE_BASE_DIR}", "删除项目目录")
        log(f"  已删除: {REMOTE_BASE_DIR}")
    else:
        run_remote(ssh,
                   f"rm -rf {REMOTE_BASE_DIR}/src {REMOTE_BASE_DIR}/{DOCKER_COMPOSE_FILE} {REMOTE_BASE_DIR}/.env {REMOTE_BASE_DIR}/nginx 2>/dev/null || true",
                   "清理项目文件（保留 data 目录）")
        log(f"  已清理项目文件，保留: {REMOTE_BASE_DIR}/data")

    # 7. 清理 Docker 残留
    log("\n>>> 7. 清理 Docker 残留")
    run_remote(ssh, "docker system prune -af 2>/dev/null || true",
               "清理无用 Docker 资源")

    # 8. 验证
    log("\n>>> 8. 验证卸载结果")
    _, containers = run_remote(ssh, "docker ps -a --format '{{.Names}}' 2>/dev/null",
                               "检查容器")
    _, images = run_remote(ssh, "docker images --format '{{.Repository}}' 2>/dev/null | grep -E 'ollp|python.*slim' || true",
                           "检查镜像")
    _, dir_status = run_remote(ssh, f"[ -d {REMOTE_BASE_DIR} ] && echo EXISTS || echo REMOVED",
                               "检查项目目录")

    log(f"\n{'='*60}")
    if dir_status.strip() == 'REMOVED':
        log("卸载完成!")
    elif keep_data:
        log("卸载完成！（保留了 data 目录）")
    else:
        log("[警告] 项目目录仍存在，请手动清理")
    log(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Online Learning Platform - 卸载脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python uninstall.py --host example.com --user root --uninstall
  python uninstall.py --host example.com --user root --key ~/.ssh/id_rsa --uninstall --keep-data
        """
    )
    parser.add_argument("--host", required=True, help="服务器 IP 或域名")
    parser.add_argument("--user", default="root", help="SSH 用户名")
    parser.add_argument("--password", help="SSH 密码")
    parser.add_argument("--key", help="SSH 私钥文件路径")
    parser.add_argument("--keep-data", action="store_true", help="保留数据目录")
    parser.add_argument("--uninstall", action="store_true", help="执行卸载（默认行为）")

    args = parser.parse_args()

    # 如果需要密码
    password = args.password
    if not password and not args.key:
        try:
            password = getpass.getpass("请输入 SSH 密码: ")
        except Exception:
            log("无法获取密码，请使用 --password 或 --key 参数", color="\033[33m")
            sys.exit(1)

    ssh = None
    try:
        ssh = get_ssh_client(args.host, args.user, password, args.key)
        log("[OK] SSH 连接成功")
        run_uninstall(ssh, args.keep_data)
    except KeyboardInterrupt:
        log("\n操作已取消", color="\033[33m")
        sys.exit(1)
    except Exception as e:
        log(f"\n卸载失败: {e}", color="\033[31m")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if ssh:
            ssh.close()


if __name__ == "__main__":
    main()
