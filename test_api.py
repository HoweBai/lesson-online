import requests
import time

base = 'http://localhost'

# Test registration
print('=== Registration Test ===')
r = requests.post(f'{base}/api/v1/auth/register', json={
    'username': 'testuser',
    'email': 'test@example.com',
    'password': 'testpass123'
})
print(f'Status: {r.status_code}')
print(f'Response: {r.text}')

time.sleep(1)

# Test login
print('\n=== Login Test ===')
r = requests.post(f'{base}/api/v1/auth/login', json={
    'email': 'test@example.com',
    'password': 'testpass123'
})
print(f'Status: {r.status_code}')
print(f'Response: {r.text}')

# Test health
print('\n=== Health Test ===')
r = requests.get(f'{base}/health')
print(f'Status: {r.status_code}')
print(f'Response: {r.text}')

# Test frontend
print('\n=== Frontend Test ===')
r = requests.get(f'{base}/')
print(f'Status: {r.status_code}')
print(f'Content length: {len(r.text)} bytes')
print(f'Has React root: {"root" in r.text}')
