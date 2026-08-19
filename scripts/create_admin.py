import paramiko, base64

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password='tlcw_CENTOS@#2023', timeout=15)

# Base64 encode the admin creation script
script_bytes = b"""from src.database import get_session
from src.models.user import User
from src.services.auth_service import AuthService
auth = AuthService()
db = get_session()
a = db.query(User).filter_by(email="admin@ollp.local").first()
if a:
    a.password_hash = auth.hash_password("ollp_admin_2024")
    a.is_admin = True
    print("Updated admin")
else:
    a = User(username="admin", email="admin@ollp.local", is_admin=True)
    a.password_hash = auth.hash_password("ollp_admin_2024")
    db.add(a)
    print("Created admin")
db.commit()
db.close()
print("Done!")
"""

encoded = base64.b64encode(script_bytes).decode('ascii')

# Write to server
stdin, stdout, stderr = c.exec_command(f'echo {encoded} | base64 -d > /tmp/ca.py')
print("Write:", stdout.read().decode().strip(), stderr.read().decode().strip())

# Copy to container
stdin, stdout, stderr = c.exec_command('docker cp /tmp/ca.py ollp-backend:/tmp/ca.py')
print("CP:", stdout.read().decode().strip(), stderr.read().decode().strip())

# Run in container
stdin, stdout, stderr = c.exec_command('docker exec ollp-backend python3 /tmp/ca.py 2>&1')
print("Run:", stdout.read().decode()[-300:])
print("Err:", stderr.read().decode()[-200:])

# Verify
stdin, stdout, stderr = c.exec_command("docker exec ollp-db psql -U ollp_user -d ollp_db -t -c \"SELECT email, is_admin FROM users WHERE email='admin@ollp.local';\"")
print("Verify:", stdout.read().decode().strip())

c.close()
print("Done!")
