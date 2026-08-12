#!/usr/bin/env python3
"""Create admin user in database"""
import paramiko
import sys

SSH_HOST = 'tlcw.yobeeo.com'
SSH_USER = 'root'
SSH_PASSWORD = 'tlcw_CENTOS@#2023'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=15)

print("=== Creating Admin User ===")

admin_email = "admin@tlcw.com"
admin_password = "Admin@123456"

# Write a Python script to a temp file on server and execute it
script_content = f'''
import sqlite3
import uuid
from datetime import datetime
import bcrypt

db_path = '/opt/ollp/ollp.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if users table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if not cursor.fetchone():
    print('Users table does not exist')
    conn.close()
    sys.exit(1)

# Check if admin already exists
cursor.execute("SELECT id FROM users WHERE email = ?", ('{admin_email}',))
if cursor.fetchone():
    print('Admin user already exists')
    conn.close()
    sys.exit(0)

# Hash password
hashed_password = bcrypt.hashpw('{admin_password}'.encode(), bcrypt.gensalt()).decode()

# Insert admin user
user_id = str(uuid.uuid4())
now = datetime.utcnow().isoformat()
cursor.execute("INSERT INTO users (id, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
    (user_id, 'admin', '{admin_email}', hashed_password, now))

# Insert admin profile
cursor.execute("INSERT INTO user_profiles (id, user_id, programming_level, learning_goal, preferred_style, created_at) VALUES (?, ?, 1, ?, ?, ?)",
    (str(uuid.uuid4()), user_id, 'general', 'text', now))

conn.commit()
print(f'Admin user created: {admin_email} / {admin_password}')
conn.close()
'''

# Write script to server
stdin, stdout, stderr = ssh.exec_command('cat > /tmp/create_admin.py << \'PYEOF\'\n' + script_content + '\nPYEOF')
print("Script uploaded")

# Execute script
_, stdout, stderr = ssh.exec_command('python3 /tmp/create_admin.py')
print("Result:", stdout.read().decode())
print("Error:", stderr.read().decode())

# Verify creation
_, stdout, stderr = ssh.exec_command(f'''python3 -c "
import sqlite3
conn = sqlite3.connect('/opt/ollp/ollp.db')
cursor = conn.execute('SELECT id, username, email FROM users WHERE email = \"{admin_email}\"')
user = cursor.fetchone()
print('Admin user:', user)
conn.close()
"''')
print("Verification:", stdout.read().decode())

ssh.close()
print("\nDone!")
print(f"\nAdmin credentials:")
print(f"  Email: {admin_email}")
print(f"  Password: {admin_password}")
