#!/usr/bin/env python3
"""Test frontend and backend after deployment"""
import paramiko
import time
import json

SSH_HOST = 'tlcw.yobeeo.com'
SSH_USER = 'root'
SSH_PASSWORD = 'tlcw_CENTOS@#2023'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=15)

print("=== Frontend Deployment Test ===\n")

# Test 1: Frontend accessibility
print("1. Testing frontend accessibility...")
_, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost/')
status = stdout.read().decode().strip()
print(f"   Homepage: HTTP {status}")

_, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost/login')
status = stdout.read().decode().strip()
print(f"   Login page: HTTP {status}")

_, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost/static/js/main.6dbf5205.js')
status = stdout.read().decode().strip()
print(f"   JS bundle: HTTP {status}")

_, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost/static/css/main.231e7bba.css')
status = stdout.read().decode().strip()
print(f"   CSS bundle: HTTP {status}")

# Test 2: Backend health
print("\n2. Testing backend health...")
_, stdout, stderr = ssh.exec_command('curl -s http://localhost/health')
health = stdout.read().decode().strip()
print(f"   Health: {health[:200]}")

# Test 3: Registration
print("\n3. Testing registration...")
test_payload = json.dumps({"username": "testuser", "email": "test@example.com", "password": "testpass123"})
ssh.exec_command(f'curl -s -X POST http://localhost/api/v1/auth/register -H "Content-Type: application/json" -d \'{test_payload}\'')
_, stdout, stderr = ssh.exec_command('curl -s -X POST http://localhost/api/v1/auth/register -H "Content-Type: application/json" -d \'{test_payload}\'')
register = stdout.read().decode().strip()
print(f"   Register: {register[:300]}")

time.sleep(1)

# Test 4: Login
print("\n4. Testing login...")
login_payload = json.dumps({"email": "test@example.com", "password": "testpass123"})
_, stdout, stderr = ssh.exec_command(f'curl -s -X POST http://localhost/api/v1/auth/login -H "Content-Type: application/json" -d \'{login_payload}\'')
login = stdout.read().decode().strip()
print(f"   Login: {login[:300]}")

# Test 5: Container status
print("\n5. Container status...")
_, stdout, stderr = ssh.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
print(stdout.read().decode())

# Test 6: Frontend file details
print("6. Frontend files...")
_, stdout, stderr = ssh.exec_command('ls -lh /opt/ollp/frontend/static/js/main.6dbf5205.js /opt/ollp/frontend/static/css/main.231e7bba.css')
print(stdout.read().decode())

ssh.close()
print("\n=== Test Complete ===")
