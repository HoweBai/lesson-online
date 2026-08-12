#!/usr/bin/env python3
"""Test SSH connection to server"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(
        hostname='tlcw.yobeeo.com',
        port=22,
        username='root',
        password='tlcw_CENTOS@#2023',
        timeout=10,
        allow_agent=False,
        look_for_keys=False
    )
    print("SSH connection successful!")

    # Test node version
    stdin, stdout, stderr = ssh.exec_command('node --version 2>&1')
    node_version = stdout.read().decode().strip()
    print(f"Node.js version: {node_version or 'not installed'}")

    # Check node path
    stdin, stdout, stderr = ssh.exec_command('which node 2>&1')
    node_path = stdout.read().decode().strip()
    print(f"Node path: {node_path or 'N/A'}")

    # Check OS
    stdin, stdout, stderr = ssh.exec_command('cat /etc/os-release | head -5')
    print(f"\nOS Info:\n{stdout.read().decode()}")

    # Check docker
    stdin, stdout, stderr = ssh.exec_command('docker --version 2>&1')
    print(f"Docker: {stdout.read().decode().strip()}")

    ssh.close()
    print("\nConnection closed successfully.")

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
