#!/usr/bin/env python3
"""Complete frontend deployment with git update"""
import paramiko
import time
import sys

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

def run(cmd, desc=""):
    print(f"\n=== {desc} ===")
    print(f"$ {cmd[:100]}...")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        for line in out.strip().split('\n')[-5:]:
            print(f"  {line}")
    if err:
        for line in err.strip().split('\n')[-3:]:
            print(f"  ERR: {line}")
    return out, err

try:
    print("Step 1: Git pull latest code")
    run('cd /root/lesson-online && git pull origin main', "Pull code")

    print("\nStep 2: Copy updated source to /opt/ollp")
    run('cp -r /root/lesson-online/src/frontend/src /opt/ollp/src/frontend/', "Copy source")

    print("\nStep 3: Verify updated files")
    out, _ = run('grep "profile_stat_total_tutorials" /opt/ollp/src/frontend/src/i18n/locales/zh/tutorials.json', "Check tutorials")
    out, _ = run('grep -c "t(" /opt/ollp/src/frontend/src/pages/ProfilePage.tsx', "Count t() calls")
    out, _ = run('grep "approve_btn" /opt/ollp/src/frontend/src/pages/AdminCatalogPage.tsx | wc -l', "Count approve_btn")

    print("\nStep 4: Build frontend Docker image")
    out, err = run('cd /opt/ollp && docker build --no-cache -t ollp-frontend -f src/frontend/Dockerfile.production src/frontend/ 2>&1 | tail -10', "Build")

    print("\nStep 5: Restart frontend container")
    run('docker compose -f /opt/ollp/docker-compose.production.yml restart frontend', "Restart")

    print("\nStep 6: Wait and verify")
    time.sleep(20)
    run('docker ps -a --format "table {{.Names}}\t{{.Status}}"', "Container status")
    run('docker images | grep ollp-frontend', "Frontend image")

    print("\n✅ Deployment complete!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    c.close()
