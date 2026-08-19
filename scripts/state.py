#!/usr/bin/env python3
import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

# Kill stuck build
stdin, stdout, stderr = c.exec_command('pkill -f "docker-compose.*build" || true; docker compose -f /opt/ollp/docker-compose.production.yml down || true')
print("Kill:", stdout.read().decode()[:100])

# Check state
stdin, stdout, stderr = c.exec_command('ps aux | grep docker-compose | grep -v grep | wc -l')
print("Compose procs:", stdout.read().decode().strip())

stdin, stdout, stderr = c.exec_command('docker ps -a --format "table {{.Names}}\t{{.Status}}"')
print("Containers:", stdout.read().decode().strip())

stdin, stdout, stderr = c.exec_command('docker images | grep ollp')
print("Images:", stdout.read().decode().strip())

c.close()
print("Done!")
