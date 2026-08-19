#!/usr/bin/env python3
"""Build worker and start all containers"""
import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

def run(cmd, desc, timeout=300):
    print(f"\n=== {desc} ===")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    rc = stdin.channel.recv_exit_status()
    lines = out.strip().split('\n')
    for line in lines[-8:] if lines else []:
        print(f"  {line}")
    if err:
        for line in err.strip().split('\n')[-3:]:
            print(f"  ERR: {line}")
    print(f"  EXIT: {rc}")
    return rc

# Build worker (reuses backend image)
run('cd /opt/ollp && docker build -t ollp-worker -f src/backend/Dockerfile src/backend/ 2>&1 | tail -20',
    'Build worker image', timeout=120)

# Start all containers
print("\n=== Starting all containers ===")
stdin, stdout, stderr = c.exec_command(
    'cd /opt/ollp && docker compose -f docker-compose.production.yml up -d 2>&1'
)
out = stdout.read().decode()
err = stderr.read().decode()
print(out[-1500:])
if err:
    print("ERR:", err[-500:])

time.sleep(30)

# Check status
print("\n=== Container status ===")
run('docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"', 'Containers')
run('docker compose -f /opt/ollp/docker-compose.production.yml ps', 'Compose ps')

c.close()
print("\n=== Done! ===")
