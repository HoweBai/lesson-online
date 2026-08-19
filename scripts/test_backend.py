import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

print("=== Test: docker compose up redis ===")
stdin, stdout, stderr = c.exec_command(
    'cd /opt/ollp && docker compose -f docker-compose.production.yml up -d redis 2>&1'
)
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:", out[-1000:])
print("STDERR:", err[-500:])

time.sleep(5)
stdin, stdout, stderr = c.exec_command('docker ps -a --format "table {{.Names}}\t{{.Status}}"')
print("\n=== Containers ===")
print(stdout.read().decode())

print("\n=== Test: docker compose build backend ===")
stdin, stdout, stderr = c.exec_command(
    'cd /opt/ollp && docker compose -f docker-compose.production.yml build backend 2>&1'
)
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT last 2000:", out[-2000:])
print("STDERR:", err[-1000:])
print("EXIT:", out.split('\n')[-1] if out else 'N/A')

c.close()
