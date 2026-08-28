import paramiko
import time
SSH_PASSWORD = "tlcw_CENTOS@#2023"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password=SSH_PASSWORD, timeout=15)

def run(cmd):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

# Build with background logging
print("=== Building Docker image (2-3 min)... ===")
run('cd /opt/ollp && docker build --no-cache -t ollp-frontend -f src/frontend/Dockerfile.production src/frontend/ > /tmp/deploy3.log 2>&1; echo BUILD_DONE >> /tmp/deploy3.log')

print("Build started. Waiting for completion...")
time.sleep(120)

# Check progress
out, _ = run('tail -8 /tmp/deploy3.log')
print(out)

out, _ = run('grep -c BUILD_DONE /tmp/deploy3.log')
if int(out.strip()) > 0:
    print("=== Build complete! Restarting ===")
    run('docker compose -f /opt/ollp/docker-compose.production.yml restart frontend')
    time.sleep(20)
    out, _ = run('docker ps --format "{{.Names}} {{.Status}}" | grep frontend')
    print("Frontend:", out)
else:
    print("Build still running, check later")

c.close()
print("Done!")
