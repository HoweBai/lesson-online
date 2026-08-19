#!/usr/bin/env python3
"""Step-by-step backend build to avoid SSH timeout"""
import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

def run(cmd, desc, timeout=300):
    print(f"\n=== {desc} ===")
    print(f"$ {cmd}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    rc = stdin.channel.recv_exit_status()
    if out:
        lines = out.strip().split('\n')
        for line in lines[-10:]:
            print(f"  {line}")
    if err:
        for line in err.strip().split('\n')[-5:]:
            print(f"  ERR: {line}")
    print(f"  EXIT: {rc}")
    return rc

# Step 1: Pull base image
run('docker pull python:3.11-slim', 'Pull base image', timeout=120)

# Step 2: Build step by step
run('cd /opt/ollp && docker build -t ollp-backend -f src/backend/Dockerfile src/backend/ 2>&1 | tail -50',
    'Build backend image', timeout=600)

# Step 3: Check result
run('docker images | grep ollp-backend', 'Check backend image')
run('docker ps -a --format "table {{.Names}}\t{{.Status}}"', 'Check containers')

c.close()
print("\n=== Done! ===")
