#!/usr/bin/env python3
"""
Online Learning Platform - 云端部署辅助工具

提供快速部署、状态检查、日志查看等功能
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_prerequisites():
    """检查必要工具"""
    tools = {
        'python3': 'Python 3.8+',
        'pip3': 'pip',
        'docker': 'Docker 20.10+',
        'docker-compose': 'Docker Compose 2.x+'
    }

    print("\n检查部署 prerequisites...")
    print("-" * 40)

    missing = []
    for tool, desc in tools.items():
        try:
            result = subprocess.run([tool, '--version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✓ {tool}: {result.stdout.strip().split()[1] if len(result.stdout.split()) > 1 else 'installed'}")
            else:
                missing.append(tool)
                print(f"✗ {tool}: not found")
        except FileNotFoundError:
            missing.append(tool)
            print(f"✗ {tool}: not installed")

    if missing:
        print("\n请安装缺失的工具:")
        for tool in missing:
            if tool == 'python3':
                print("  apt-get install python3 python3-pip")
            elif tool == 'docker':
                print("  curl -fsSL https://get.docker.com | sh")
            elif tool == 'docker-compose':
                print("  apt-get install docker-compose-plugin")
        return False

    return True


def quick_deploy():
    """快速部署流程"""
    print("\n" + "=" * 60)
    print("  Online Learning Platform - 快速部署")
    print("=" * 60)

    # 检查依赖
    if not check_prerequisites():
        print("\n请先安装必要的工具")
        sys.exit(1)

    # 检查配置文件
    env_file = Path(".env.production")
    if not env_file.exists():
        print(f"\n错误: 找不到配置文件 {env_file}")
        print("请先运行: python3 cloud_deploy.py --generate-config")
        sys.exit(1)

    compose_file = Path("docker-compose.prod.yml")
    if not compose_file.exists():
        print(f"\n错误: 找不到配置文件 {compose_file}")
        print("请先运行: python3 cloud_deploy.py --generate-config")
        sys.exit(1)

    # 检查Docker
    try:
        subprocess.run(['docker', 'info'], check=True, capture_output=True)
        print("✓ Docker运行中")
    except subprocess.CalledProcessError:
        print("✗ Docker未运行，请先启动Docker服务")
        sys.exit(1)

    # 开始部署
    print("\n开始部署...")
    print("-" * 40)

    # 构建镜像
    print("1. 构建Docker镜像...")
    subprocess.run(['docker-compose', '-f', 'docker-compose.prod.yml', 'build'], check=True)

    # 启动服务
    print("2. 启动服务...")
    subprocess.run(['docker-compose', '-f', 'docker-compose.prod.yml', 'up', '-d'], check=True)

    # 等待
    print("3. 等待服务启动...")
    import time
    time.sleep(10)

    # 检查状态
    print("4. 检查服务状态...")
    result = subprocess.run(['docker-compose', '-f', 'docker-compose.prod.yml', 'ps'],
                          capture_output=True, text=True)
    print(result.stdout)

    print("\n" + "=" * 60)
    print("  部署完成！")
    print("=" * 60)
    print("\n访问地址:")
    print("  🌐 主站:     http://localhost")
    print("  📚 API文档:  http://localhost:8000/docs")
    print("  🔍 健康检查: http://localhost:8000/health")
    print("  💾 MinIO:    http://localhost:9001")
    print("=" * 60)


def check_status():
    """检查服务状态"""
    print("\n检查服务状态...")
    print("-" * 40)

    subprocess.run(['docker-compose', '-f', 'docker-compose.prod.yml', 'ps'], check=True)

    print("\n健康检查:")
    try:
        import urllib.request
        response = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
        print(f"✓ 后端API正常: {response.status}")
    except Exception as e:
        print(f"✗ 后端API异常: {e}")


def show_logs(follow=False, tail=100):
    """查看日志"""
    cmd = ['docker-compose', '-f', 'docker-compose.prod.yml', 'logs']
    if follow:
        cmd.append('-f')
    if tail:
        cmd.extend(['--tail', str(tail)])

    subprocess.run(cmd, check=True)


def stop_services():
    """停止所有服务"""
    print("停止所有服务...")
    subprocess.run(['docker-compose', '-f', 'docker-compose.prod.yml', 'down'], check=True)
    print("✓ 所有服务已停止")


def restart_services():
    """重启所有服务"""
    print("重启服务...")
    subprocess.run(['docker-compose', '-f', 'docker-compose.prod.yml', 'restart'], check=True)
    print("✓ 服务已重启")


def main():
    parser = argparse.ArgumentParser(
        description='Online Learning Platform - 云端部署工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 cloud_deploy.py deploy          # 完整部署
  python3 cloud_deploy.py status          # 检查状态
  python3 cloud_deploy.py logs            # 查看日志
  python3 cloud_deploy.py stop            # 停止服务
  python3 cloud_deploy.py restart         # 重启服务
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # deploy命令
    deploy_parser = subparsers.add_parser('deploy', help='执行完整部署')
    deploy_parser.add_argument('--no-cache', action='store_true', help='不使用缓存构建')

    # status命令
    subparsers.add_parser('status', help='检查服务状态')

    # logs命令
    logs_parser = subparsers.add_parser('logs', help='查看服务日志')
    logs_parser.add_argument('-f', '--follow', action='store_true', help='持续跟踪日志')
    logs_parser.add_argument('-n', '--tail', type=int, default=100, help='显示最后N行')

    # stop命令
    subparsers.add_parser('stop', help='停止所有服务')

    # restart命令
    subparsers.add_parser('restart', help='重启所有服务')

    args = parser.parse_args()

    if args.command == 'deploy':
        quick_deploy()
    elif args.command == 'status':
        check_status()
    elif args.command == 'logs':
        show_logs(follow=args.follow, tail=args.tail)
    elif args.command == 'stop':
        stop_services()
    elif args.command == 'restart':
        restart_services()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
