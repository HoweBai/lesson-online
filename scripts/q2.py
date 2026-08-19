import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)
stdin, stdout, stderr = c.exec_command('ls /opt/ollp/src/backend/ && ls /opt/ollp/src/frontend/')
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
