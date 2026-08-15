"""Deploy backend to cloud server using paramiko SSH."""

import paramiko
import os
import sys
import time
import posixpath

SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_USER = "root"
SERVER_PASSWORD = "tlcw_CENTOS@#2023"
REMOTE_PATH = "/opt/ollp"

def run_command(client, command, timeout=30):
    """Execute SSH command and return output."""
    print(f"  Executing: {command[:100]}...")
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    if output:
        print(f"  Output: {output[:200]}")
    if error and "Warning" not in error and "Error" not in error:
        print(f"  Error: {error[:200]}")
    return output, error

def upload_file(client, local_path, remote_path):
    """Upload a file to server."""
    sftp = client.open_sftp()
    print(f"  Uploading: {os.path.basename(local_path)} -> {remote_path}")
    sftp.put(local_path, remote_path)
    sftp.close()
    print(f"  Uploaded successfully")

def upload_dir(client, local_dir, remote_dir):
    """Upload a directory recursively."""
    sftp = client.open_sftp()
    # Create remote directory
    try:
        sftp.mkdir(remote_dir)
    except:
        pass

    for root, dirs, files in os.walk(local_dir):
        # Calculate relative path with forward slashes
        rel_path = os.path.relpath(root, local_dir).replace('\\', '/')
        remote_path = posixpath.join(remote_dir, rel_path) if rel_path != '.' else remote_dir

        # Create remote subdirectory
        try:
            sftp.mkdir(remote_path)
        except:
            pass

        # Upload files
        for file in files:
            if file.endswith('.pyc') or file.startswith('__'):
                continue  # Skip Python cache files
            local_file = os.path.join(root, file)
            remote_file = posixpath.join(remote_path, file)
            print(f"  Uploading: {local_file.replace(os.sep, '/')}")
            sftp.put(local_file, remote_file)

    sftp.close()
    print(f"  Directory upload complete")

def main():
    print("=" * 60)
    print("Online Learning Platform - Backend Deployment")
    print("=" * 60)

    # Backend source directory
    backend_src = os.path.join(os.path.dirname(__file__), 'src')

    # Connect to server
    print("\n[1/5] Connecting to server...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=10)
        print("[OK] Connected to server")
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        return 1

    try:
        # Step 1: Create remote directory structure
        print("\n[2/5] Creating directory structure...")
        run_command(client, f"mkdir -p {REMOTE_PATH}/app")
        run_command(client, f"mkdir -p {REMOTE_PATH}/src/api")
        run_command(client, f"mkdir -p {REMOTE_PATH}/src/models")
        run_command(client, f"mkdir -p {REMOTE_PATH}/src/services")
        run_command(client, f"mkdir -p {REMOTE_PATH}/src/schemas")
        run_command(client, f"mkdir -p {REMOTE_PATH}/logs")
        run_command(client, f"mkdir -p {REMOTE_PATH}/data")
        print("[OK] Directory structure created")

        # Step 2: Upload files
        print("\n[3/5] Uploading files...")

        # Upload Dockerfile
        dockerfile_path = os.path.join(os.path.dirname(__file__), 'Dockerfile')
        if os.path.exists(dockerfile_path):
            upload_file(client, dockerfile_path, f"{REMOTE_PATH}/Dockerfile")
        else:
            run_command(client, f"""cat > {REMOTE_PATH}/Dockerfile << 'DOCKERFILE'
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
COPY src /app/src
RUN mkdir -p /app/logs
EXPOSE 8000
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
DOCKERFILE""")
            print("[OK] Dockerfile created")

        # Upload requirements.txt
        req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
        if os.path.exists(req_path):
            upload_file(client, req_path, f"{REMOTE_PATH}/requirements.txt")

        # Upload app directory
        app_dir = os.path.join(backend_src, 'api')
        if os.path.exists(app_dir):
            upload_dir(client, app_dir, f"{REMOTE_PATH}/src/api")

        # Upload models
        models_dir = os.path.join(backend_src, 'models')
        if os.path.exists(models_dir):
            upload_dir(client, models_dir, f"{REMOTE_PATH}/src/models")

        # Upload services
        services_dir = os.path.join(backend_src, 'services')
        if os.path.exists(services_dir):
            upload_dir(client, services_dir, f"{REMOTE_PATH}/src/services")

        # Upload schemas
        schemas_dir = os.path.join(backend_src, 'schemas')
        if os.path.exists(schemas_dir):
            upload_dir(client, schemas_dir, f"{REMOTE_PATH}/src/schemas")

        # Upload database.py
        db_file = os.path.join(backend_src, 'database.py')
        if os.path.exists(db_file):
            upload_file(client, db_file, f"{REMOTE_PATH}/src/database.py")

        # Create __init__.py files
        run_command(client, f"touch {REMOTE_PATH}/src/__init__.py")
        run_command(client, f"touch {REMOTE_PATH}/src/api/__init__.py")
        run_command(client, f"touch {REMOTE_PATH}/src/models/__init__.py")
        run_command(client, f"touch {REMOTE_PATH}/src/services/__init__.py")
        run_command(client, f"touch {REMOTE_PATH}/src/schemas/__init__.py")

        print("[OK] Files uploaded successfully")

        # Step 3: Build Docker image
        print("\n[4/5] Building Docker image...")
        output, error = run_command(client, f"cd {REMOTE_PATH} && docker build -t ollp-backend .")
        if "Successfully built" in output or "Successfully tagged" in output:
            print("[OK] Docker image built")
        else:
            print(f"[WARN] Build output: {output[-500:]}")

        # Step 4: Deploy container
        print("\n[5/5] Deploying container...")
        run_command(client, "docker stop ollp-backend 2>/dev/null || true")
        run_command(client, "docker rm ollp-backend 2>/dev/null || true")
        run_command(client, f"cd {REMOTE_PATH} && docker run -d --name ollp-backend -p 8000:8000 -e SECRET_KEY=test-key -e CRYPTO_KEY_HEX={'0'*64} ollp-backend")
        time.sleep(5)

        # Verify deployment
        output, error = run_command(client, "docker ps --filter name=ollp-backend --format '{{.Status}}'")
        if "Up" in output:
            print("[OK] Container is running")
        else:
            print(f"[WARN] Container status: {output}")
            run_command(client, "docker logs ollp-backend --tail=20")

        # Test API
        print("\n[Testing API...]")
        output, error = run_command(client, "curl -s http://localhost:8000/health")
        if output:
            print(f"[OK] Health check: {output}")
        else:
            print("[WARN] Health check failed")

        print("\n" + "=" * 60)
        print("[SUCCESS] Deployment complete!")
        print(f"API URL: http://{SERVER_HOST}:8000")
        print(f"Docs:    http://{SERVER_HOST}:8000/docs")
        print(f"Health:  http://{SERVER_HOST}:8000/health")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"[FAIL] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
