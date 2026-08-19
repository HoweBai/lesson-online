#!/usr/bin/env python3
"""Build backend image with verbose output"""
import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

print("Starting backend build with output to file...")
stdin, stdout, stderr = c.exec_command(
    'cd /opt/ollp && docker compose -f docker-compose.production.yml build backend --progress=plain 2>&1 | tee /tmp/backend_build.log; echo "BUILD_EXIT=$?" >> /tmp/backend_build.log'
)
# Detach - will run in background
time.sleep(5)
print("Build started, checking progress...")

for i in range(60):
    time.sleep(10)
    stdin, stdout, stderr = c.exec_command('tail -20 /tmp/backend_build.log 2>&1')
    log = stdout.read().decode()
    if 'BUILD_EXIT=' in log or 'error' in log.lower() or 'failed' in log.lower():
        print("Build completed or failed!")
        print(log)
        break
    if i % 10 == 0:
        print(f"Progress check {i+1}/60...")
        print(log[-500:])
else:
    print("Timeout - checking final status")
    stdin, stdout, stderr = c.exec_command('tail -30 /tmp/backend_build.log 2>&1')
    print(stdout.read().decode())

c.close()
print("Done!")
