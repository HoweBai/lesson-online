#!/usr/bin/env python3
"""SSH diagnostics script - runs on server and outputs to /tmp/diag.log"""
import paramiko
import sys
import traceback

LOG_FILE = '/tmp/diag_ssh.log'

def run(cmd, desc):
    """Run command and write to log"""
    lines = [f"\n{'='*60}", f"=== {desc} ===", f"$ {cmd}"]
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        lines.append(f"STDOUT:\n{out}")
        if err:
            lines.append(f"STDERR:\n{err}")
    except Exception as e:
        lines.append(f"ERROR: {e}")
    log.write('\n'.join(lines) + '\n')
    log.flush()
    print(f"  {desc}: done")

client = None
log = None

try:
    log = open(LOG_FILE, 'w')
    print(f"Connecting to 119.27.173.222...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)
    print("Connected!")

    run('docker ps -a', 'Current containers')
    run('docker images', 'Docker images')
    run('docker compose -f /opt/ollp/docker-compose.production.yml config --quiet 2>&1; echo EXIT=$?', 'Config validation')
    run('docker compose -f /opt/ollp/docker-compose.production.yml ps 2>&1', 'Compose ps')
    run('docker compose -f /opt/ollp/docker-compose.production.yml logs --tail=20 2>&1', 'Compose logs')
    run('ls -la /opt/ollp/src/backend/ /opt/ollp/src/frontend/', 'Source dirs')
    run('cat /opt/ollp/.env', '.env file')
    run('df -h /var/lib/docker', 'Disk space')
    run('free -m', 'Memory')
    run('ps aux | grep docker', 'Docker processes')
    run('docker events --since 10m --format "{{.Time}} {{.Status}}" 2>&1', 'Docker events')

    print("Running build test...")
    run('cd /opt/ollp && docker compose -f docker-compose.production.yml build --no-cache db 2>&1; echo BUILD_EXIT=$?', 'Build db service only')

    run('docker ps -a', 'Containers after build')
    run('docker compose -f /opt/ollp/docker-compose.production.yml ps', 'Compose ps after build')

    print("\nAll diagnostics complete! Check /tmp/diag_ssh.log on server")
    log.write("\n=== ALL DONE ===\n")

except Exception as e:
    print(f"FATAL: {e}")
    traceback.print_exc()
    if log:
        log.write(f"\nFATAL ERROR: {e}\n")
        traceback.print_exc(file=log)
finally:
    if log:
        log.close()
    if client:
        client.close()
