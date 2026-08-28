#!/usr/bin/env python3
"""Check build progress and restart frontend if done."""
import paramiko
import time
import sys

SSH_PASSWORD = "tlcw_CENTOS@#2023"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password=SSH_PASSWORD, timeout=15)

try:
    # Check build log
    stdin, stdout, stderr = c.exec_command('tail -10 /tmp/frontend_build.log 2>/dev/null; echo ===LINES===; wc -l /tmp/frontend_build.log 2>/dev/null; echo ===DONE===; grep -c "BUILD_DONE" /tmp/frontend_build.log 2>/dev/null || echo 0', timeout=30)
    print(stdout.read().decode())

    # Check if build is done
    stdin, stdout, stderr = c.exec_command('grep -c "BUILD_DONE" /tmp/frontend_build.log 2>/dev/null || echo 0', timeout=15)
    done = stdout.read().decode().strip()

    if int(done) > 0:
        print("\nBuild complete! Restarting frontend...")
        stdin, stdout, stderr = c.exec_command('docker compose -f /opt/ollp/docker-compose.production.yml restart frontend', timeout=30)
        print(stdout.read().decode())
        time.sleep(15)
        stdin, stdout, stderr = c.exec_command('docker ps --format "{{.Names}} {{.Status}}" | grep frontend', timeout=15)
        print("Frontend status:", stdout.read().decode())
    else:
        print(f"\nBuild not done yet ({done} DONE markers). Waiting...")

except Exception as e:
    print(f"Error: {e}")
finally:
    c.close()
