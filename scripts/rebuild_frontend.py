import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

print("Building frontend...")
stdin, stdout, stderr = c.exec_command('cd /opt/ollp && docker build -t ollp-frontend -f src/frontend/Dockerfile.production src/frontend/ 2>&1')
out = stdout.read().decode()
err = stderr.read().decode()
print(out[-1000:])
if err:
    print("ERR:", err[-300:])

print("Restarting frontend...")
stdin, stdout, stderr = c.exec_command('docker compose -f /opt/ollp/docker-compose.production.yml restart frontend 2>&1')
print(stdout.read().decode()[-300:])

import time
time.sleep(15)

print("Testing login...")
stdin, stdout, stderr = c.exec_command("curl -sk -X POST https://localhost/api/v1/admin/login -H 'Content-Type: application/json' -d '{\"email\":\"admin@ollp.local\",\"password\":\"ollp_admin_2024\"}'")
print("Login:", stdout.read().decode()[:200])

stdin, stdout, stderr = c.exec_command('docker ps -a --format "table {{.Names}}\t{{.Status}}"')
print("\nContainers:", stdout.read().decode())

c.close()
print("Done!")
