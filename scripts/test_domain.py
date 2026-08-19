import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

# Test via domain
s,t,e=c.exec_command('curl -sk https://tlcw.yobeeo.com/api/v1/admin/login -H "Content-Type: application/json" -d \'{"email":"admin@ollp.local","password":"ollp_admin_2024"}\'')
print('Via domain:', t.read().decode()[:300])

# Check nginx config
s,t,e=c.exec_command('grep -A5 "location /api" /opt/ollp/nginx/nginx.production.conf')
print('Nginx API:', t.read().decode())

# Check backend logs
s,t,e=c.exec_command('docker logs ollp-backend 2>&1 | grep -i "invalid\\|401\\|login" | tail -10')
print('Logs:', t.read().decode()[-500:])

c.close()
