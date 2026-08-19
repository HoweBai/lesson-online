import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

# 1. Check DB record
s,t,e=c.exec_command("docker exec ollp-db psql -U ollp_user -d ollp_db -t -c \"SELECT email, LEFT(password_hash,40), is_admin FROM users WHERE email='admin@ollp.local';\"")
print('DB:', t.read().decode().strip())

# 2. Write test script to server
import base64
script = b'''import sys
sys.path.insert(0, "/app")
from src.database import get_session
from src.models.user import User
from src.services.auth_service import AuthService
auth = AuthService()
db = get_session()
user = db.query(User).filter_by(email="admin@ollp.local").first()
print(f"User: {user is not None}")
if user:
    print(f"Email: {user.email}")
    print(f"Admin: {user.is_admin}")
    vh = auth.verify_password("ollp_admin_2024", user.password_hash)
    print(f"Password match: {vh}")
    token = auth.create_access_token(data={"sub": str(user.id)})
    print(f"Token OK: {len(token)} chars")
db.close()
'''
enc = base64.b64encode(script).decode()
s,t,e=c.exec_command(f'echo {enc} | base64 -d > /tmp/test_login.py')
print('Write:', t.read().decode().strip())

s,t,e=c.exec_command('docker cp /tmp/test_login.py ollp-backend:/tmp/test_login.py')
print('CP:', t.read().decode().strip(), e.read().decode().strip())

s,t,e=c.exec_command('docker exec ollp-backend python3 /tmp/test_login.py 2>&1')
print('Test:', t.read().decode()[-400:])
print('Err:', e.read().decode()[-200:])

# 3. Test API login
s,t,e=c.exec_command("curl -sk -X POST https://localhost/api/v1/admin/login -H 'Content-Type: application/json' -d '{\"email\":\"admin@ollp.local\",\"password\":\"ollp_admin_2024\"}'")
print('API:', t.read().decode()[:300])

c.close()
