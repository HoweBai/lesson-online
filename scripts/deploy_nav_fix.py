#!/usr/bin/env python3
"""Deploy frontend changes."""
import paramiko
import time

SSH_PASSWORD = "tlcw_CENTOS@#2023"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password=SSH_PASSWORD, timeout=15)

print("Pulling latest code...")
c.exec_command('cd /root/lesson-online && git pull origin main', timeout=30)

print("Copying source...")
c.exec_command('cp -r /root/lesson-online/src/frontend/src /opt/ollp/src/frontend/', timeout=30)

print("Building Docker image (this takes ~2-3 min)...")
stdin, stdout, stderr = c.exec_command(
    'cd /opt/ollp && docker build --no-cache -t ollp-frontend -f src/frontend/Dockerfile.production src/frontend/ 2>&1 | tail -20',
    timeout=300
)
out = stdout.read().decode()
print(out[-500:] if out else "(building)")

print("\nRestarting frontend...")
c.exec_command('docker compose -f /opt/ollp/docker-compose.production.yml restart frontend', timeout=30)
time.sleep(20)

stdin, stdout, stderr = c.exec_command('docker ps --format "{{.Names}} {{.Status}}" | grep frontend', timeout=15)
print("Status:", stdout.read().decode())

c.close()
print("\nDone!")
