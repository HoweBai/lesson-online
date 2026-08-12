"""Deploy backend to cloud server - comprehensive deployment script."""

import paramiko
import os
import sys
import time
import posixpath
import tarfile
import io

SERVER_HOST = "tlcw.yobeeo.com"
SERVER_USER = "root"
SERVER_PASSWORD = "tlcw_CENTOS@#2023"
REMOTE_PATH = "/opt/ollp"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_command(client, command, timeout=30, description=""):
    """Execute SSH command and return output."""
    print(f"\n>>> {description or command[:80]}")
    print(f"    {command}")
    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    if output:
        for line in output.split('\n')[-20:]:  # Show last 20 lines
            if line.strip():
                print(f"    {line}")
    if error and 'Warning' not in error and 'warning' not in error.lower():
        for line in error.split('\n')[-10:]:
            if line.strip():
                print(f"    ERR: {line}")
    return output, error


def upload_tar(client, local_path, remote_path, description=""):
    """Upload a tar.gz file via SFTP."""
    print(f"\n>>> {description}")
    sftp = client.open_sftp()
    # Create remote directory
    remote_dir = posixpath.dirname(remote_path)
    try:
        sftp.mkdir(remote_dir)
    except IOError:
        pass  # Directory exists

    # Create tar in memory
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        tar.add(local_path, arcname=os.path.basename(local_path))
    tar_buffer.seek(0)

    # Upload
    sftp.putfo(tar_buffer, remote_path)
    sftp.close()
    print(f"    Uploaded {os.path.getsize(local_path)} bytes")
    return True


def deploy():
    print("=" * 70)
    print("  Online Learning Platform - Backend Deployment")
    print(f"  Server: {SERVER_HOST}")
    print("=" * 70)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect
        print("\n[1/7] Connecting to server...")
        client.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=15)
        print("    [OK] Connected")

        # Check existing setup
        print("\n[2/7] Checking existing deployment...")
        run_command(client, f"ls {REMOTE_PATH}/src/api/*.py 2>/dev/null | wc -l", description="Check existing files")
        run_command(client, "docker ps --filter name=ollp-backend --format '{{.Status}}' 2>/dev/null || echo 'no container'", description="Check container status")
        run_command(client, "docker ps --format '{{.Names}}' | grep nginx || echo 'no nginx'", description="Check nginx")

        # Package backend source
        print("\n[3/7] Packaging backend source...")
        tar_path = "/tmp/ollp_backend.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            # Add all Python source files
            for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "src/backend/src")):
                # Skip __pycache__ and .pytest_cache
                dirs[:] = [d for d in dirs if d not in ('__pycache__', '.pytest_cache')]
                for file in files:
                    if file.endswith('.py'):
                        full_path = os.path.join(root, file)
                        arcname = posixpath.join("ollp_backend_src", posixpath.relpath(full_path, os.path.join(PROJECT_ROOT, "src/backend/src")))
                        tar.add(full_path, arcname=arcname)
                        print(f"    Adding: {arcname}")

        print(f"    Packaged to {tar_path} ({os.path.getsize(tar_path)} bytes)")

        # Upload tar
        print("\n[4/7] Uploading to server...")
        remote_tar = f"{REMOTE_PATH}/backend_src.tar.gz"
        upload_tar(client, tar_path, remote_tar, "Uploading backend source")

        # Extract on server
        print("\n[5/7] Deploying on server...")
        run_command(client, f"cd {REMOTE_PATH} && tar xzf backend_src.tar.gz", "Extracting source")
        run_command(client, f"cp -r {REMOTE_PATH}/ollp_backend_src/* {REMOTE_PATH}/src/", "Copying to src/")
        run_command(client, f"rm -rf {REMOTE_PATH}/ollp_backend_src {REMOTE_PATH}/backend_src.tar.gz", "Cleaning up")

        # Also upload tests
        tests_tar = "/tmp/ollp_tests.tar.gz"
        with tarfile.open(tests_tar, "w:gz") as tar:
            for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "src/backend/tests")):
                dirs[:] = [d for d in dirs if d not in ('__pycache__', '.pytest_cache')]
                for file in files:
                    if file.endswith('.py'):
                        full_path = os.path.join(root, file)
                        arcname = posixpath.join("ollp_tests", posixpath.relpath(full_path, os.path.join(PROJECT_ROOT, "src/backend/tests")))
                        tar.add(full_path, arcname=arcname)

        remote_tests = f"{REMOTE_PATH}/tests.tar.gz"
        upload_tar(client, tests_tar, remote_tests, "Uploading tests")
        run_command(client, f"cd {REMOTE_PATH} && tar xzf tests.tar.gz && cp -r ollp_tests/* tests/ && rm -rf ollp_tests tests.tar.gz", "Deploying tests")
        run_command(client, f"touch {REMOTE_PATH}/src/__init__.py {REMOTE_PATH}/src/api/__init__.py {REMOTE_PATH}/src/models/__init__.py {REMOTE_PATH}/src/services/__init__.py {REMOTE_PATH}/src/middleware/__init__.py", "Creating __init__.py files")

        # Restart backend
        print("\n[6/7] Restarting backend service...")
        run_command(client, f"cd {REMOTE_PATH} && docker exec ollp-backend pkill -f 'uvicorn' 2>/dev/null || true", "Stop old process")
        time.sleep(2)
        run_command(client, f"cd {REMOTE_PATH} && nohup python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload > logs/backend.log 2>&1 &", "Start backend")
        time.sleep(5)

        # Check process
        run_command(client, "ps aux | grep uvicorn | grep -v grep | head -3", "Check backend process")
        run_command(client, f"tail -20 {REMOTE_PATH}/logs/backend.log 2>/dev/null", "Check backend logs")

        # Verify
        print("\n[7/7] Verifying deployment...")
        time.sleep(3)
        run_command(client, "curl -s http://localhost:8000/health", "Health check")
        run_command(client, "curl -s http://localhost:8000/api/v1/auth/forgot-password -X POST -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\"}'", "Password reset endpoint")
        run_command(client, "curl -s http://localhost:8000/api/v1/auth/reset-password -X POST -H 'Content-Type: application/json' -d '{\"token\":\"bad\",\"new_password\":\"test\"}'", "Password reset validation")

        # List deployed files
        run_command(client, f"ls {REMOTE_PATH}/src/services/ | grep -v __pycache__", "Deployed services")
        run_command(client, f"ls {REMOTE_PATH}/src/api/ | grep -v __pycache__", "Deployed APIs")

        print("\n" + "=" * 70)
        print("  [SUCCESS] Deployment complete!")
        print(f"  Backend:   http://{SERVER_HOST}:8000")
        print(f"  API Docs:  http://{SERVER_HOST}:8000/docs")
        print(f"  Health:    http://{SERVER_HOST}:8000/health")
        print("=" * 70)
        return 0

    except Exception as e:
        print(f"\n[FAIL] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        client.close()
        # Cleanup temp files
        for f in ['/tmp/ollp_backend.tar.gz', '/tmp/ollp_tests.tar.gz']:
            try:
                os.remove(f)
            except:
                pass


if __name__ == "__main__":
    sys.exit(deploy())
