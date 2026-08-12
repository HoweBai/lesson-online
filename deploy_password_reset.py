"""Deploy password reset feature to cloud server."""
import paramiko
import os
import sys
import posixpath
import time

SERVER_HOST = "tlcw.yobeeo.com"
SERVER_USER = "root"
SERVER_PASSWORD = "tlcw_CENTOS@#2023"
REMOTE_PATH = "/opt/ollp"
PROJECT_ROOT = "d:/project/lessons"

def run(client, cmd, desc=""):
    print(f"\n>>> {desc or cmd[:70]}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    if out:
        for line in out.split('\n')[-15:]:
            if line.strip(): print(f"    {line}")
    if err and not err.startswith('Warning'):
        for line in err.split('\n')[-5:]:
            if line.strip(): print(f"    ERR: {line}")
    return out, err

def upload_file(client, local_path, remote_path, desc=""):
    print(f"\n>>> {desc or os.path.basename(local_path)}")
    sftp = client.open_sftp()
    try:
        sftp.put(local_path, remote_path)
        size = os.path.getsize(local_path)
        print(f"    Uploaded {size} bytes -> {remote_path}")
    finally:
        sftp.close()

def deploy():
    print("=" * 60)
    print("  Deploy Password Reset Feature")
    print(f"  Server: {SERVER_HOST}")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("\n[1/6] Connecting...")
        client.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=15)
        print("    [OK]")

        # Upload new files
        print("\n[2/6] Uploading files...")

        # password_reset_service.py
        local = os.path.join(PROJECT_ROOT, "src/backend/src/services/password_reset_service.py")
        remote = f"{REMOTE_PATH}/src/services/password_reset_service.py"
        upload_file(client, local, remote, "password_reset_service.py")

        # password_reset.py
        local = os.path.join(PROJECT_ROOT, "src/backend/src/api/password_reset.py")
        remote = f"{REMOTE_PATH}/src/api/password_reset.py"
        upload_file(client, local, remote, "password_reset.py")

        # main.py (modified)
        local = os.path.join(PROJECT_ROOT, "src/backend/src/api/main.py")
        remote = f"{REMOTE_PATH}/src/api/main.py"
        upload_file(client, local, remote, "main.py")

        # test_password_reset.py
        local = os.path.join(PROJECT_ROOT, "src/backend/tests/test_password_reset.py")
        remote = f"{REMOTE_PATH}/tests/test_password_reset.py"
        upload_file(client, local, remote, "test_password_reset.py")

        # Verify files on server
        print("\n[3/6] Verifying files...")
        run(client, f"docker exec ollp-backend ls {REMOTE_PATH}/src/services/password_reset_service.py", "Verify service")
        run(client, f"docker exec ollp-backend ls {REMOTE_PATH}/src/api/password_reset.py", "Verify API")
        run(client, f"docker exec ollp-backend grep password_reset {REMOTE_PATH}/src/api/main.py", "Verify router")

        # Rebuild and restart
        print("\n[4/6] Rebuilding container...")
        run(client, f"cd {REMOTE_PATH} && docker build -t ollp-backend .", "Docker build")

        print("\n[5/6] Restarting container...")
        run(client, "docker stop ollp-backend", "Stop old")
        run(client, "docker rm ollp-backend", "Remove old")
        run(client, f"cd {REMOTE_PATH} && docker run -d --name ollp-backend -p 8000:8000 -e SECRET_KEY=test-key -e CRYPTO_KEY_HEX={'0'*64} ollp-backend", "Start new")
        time.sleep(5)
        run(client, "docker ps --filter name=ollp-backend --format '{{.Status}}'", "Container status")

        # Verify
        print("\n[6/6] Verifying endpoints...")
        time.sleep(3)
        run(client, "docker exec ollp-backend python -c \"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read().decode())\"", "Health check")
        run(client, "curl -s -X POST http://127.0.0.1:8000/api/v1/auth/forgot-password -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\"}'", "Forgot password")
        run(client, "curl -s -X POST http://127.0.0.1:8000/api/v1/auth/reset-password -H 'Content-Type: application/json' -d '{\"token\":\"bad\",\"new_password\":\"test\"}'", "Reset password validation")
        run(client, "docker logs ollp-backend --tail 20", "Recent logs")

        print("\n" + "=" * 60)
        print("  [SUCCESS] Deployment complete!")
        print(f"  Health:  http://{SERVER_HOST}/health")
        print(f"  API:     http://{SERVER_HOST}/docs")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        client.close()

if __name__ == "__main__":
    sys.exit(deploy())
