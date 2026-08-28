import paramiko, time
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

print("Restarting frontend...")
c.exec_command('docker compose -f /opt/ollp/docker-compose.production.yml restart frontend', timeout=30)
time.sleep(20)

stdin, stdout, stderr = c.exec_command('docker ps --format "{{.Names}} {{.Status}}" | grep frontend', timeout=15)
print("Frontend:", stdout.read().decode())

c.close()
print("Done!")
