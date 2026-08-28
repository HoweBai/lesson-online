import paramiko
SSH_PASSWORD = "tlcw_CENTOS@#2023"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password=SSH_PASSWORD, timeout=15)
s,t,e=c.exec_command('tail -15 /tmp/deploy3.log 2>/dev/null; echo ===; grep -c BUILD_DONE /tmp/deploy3.log 2>/dev/null || echo 0; echo ===; docker ps --format "{{.Names}} {{.Status}}" | grep frontend')
print(s.read().decode())
c.close()
