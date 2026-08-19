import paramiko
import time
import sys

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

print("=== Step 1: docker compose up db only ===")
stdin, stdout, stderr = c.exec_command(
    'cd /opt/ollp && docker compose -f docker-compose.production.yml up -d db 2>&1'
)
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:", out[-2000:])
print("STDERR:", err[-1000:])

time.sleep(10)

print("\n=== Step 2: Check containers ===")
stdin, stdout, stderr = c.exec_command('docker ps -a')
print(stdout.read().decode())
print(stderr.read().decode())

print("\n=== Step 3: Check db logs ===")
stdin, stdout, stderr = c.exec_command('docker logs ollp-db 2>&1')
print(stdout.read().decode()[-1000:])
print(stderr.read().decode()[-500:])

c.close()
print("\nDone!")
