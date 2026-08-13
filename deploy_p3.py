"""
Server Deployment Script
Uploads latest code to tlcw.yobeeo.com and rebuilds services.
Reads SSH credentials from environment or .env file.
"""
import os
import sys
import paramiko
import time
import tarfile
import io
import subprocess
from pathlib import Path


# ── Credentials ──────────────────────────────────────────────────────────────
SSH_HOST = os.environ.get("SSH_HOST", "tlcw.yobeeo.com")
SSH_USER = os.environ.get("SSH_USER", "root")
SSH_PASSWORD = os.environ.get("SSH_PASSWORD")
PROJECT_PATH = "/opt/ollp"

# Load from .env if not in env
if not SSH_PASSWORD:
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("SSH_PASSWORD=") and not line.startswith("#"):
                SSH_PASSWORD = line.split("=", 1)[1].strip().strip('"').strip("'")


def log(msg, color=""):
    """Print a status line."""
    print(msg)


def run_cmd(ssh, cmd, timeout=120, description=""):
    """Run a command on the remote server."""
    if description:
        log(f"\n>>> {description}")
    log(f"    {cmd[:120]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    output = stdout.read().decode("utf-8", errors="ignore").strip()
    error = stderr.read().decode("utf-8", errors="ignore").strip()
    exit_code = stdout.channel.recv_exit_status()
    if output:
        for line in output.splitlines()[:20]:
            log(f"    {line}")
    if error and exit_code != 0:
        for line in error.splitlines()[:10]:
            log(f"    ERR: {line}", color="RED")
    return exit_code, output, error


def build_frontend():
    """Build React frontend locally."""
    log("\n=== Building Frontend ===")
    frontend_dir = Path(__file__).parent / "src" / "frontend"
    if not frontend_dir.exists():
        log("ERROR: Frontend dir not found", "RED")
        return False

    # Install deps
    log("Installing npm deps...")
    r = subprocess.run(
        ["npm", "install"], cwd=str(frontend_dir),
        capture_output=True, text=True, timeout=180
    )
    if r.returncode != 0:
        log(f"npm install failed:\n{r.stderr[-300:]}", "RED")
        return False
    log("npm install OK")

    # Build
    log("Building frontend...")
    r = subprocess.run(
        ["npm", "run", "build"], cwd=str(frontend_dir),
        capture_output=True, text=True, timeout=300
    )
    if r.returncode != 0:
        log(f"Build failed:\n{r.stderr[-500:]}", "RED")
        return False
    log("Frontend build OK")
    return True


def build_backend_docker_context():
    """Create a tarball of backend source for server build context."""
    log("\n=== Creating Backend Build Context ===")
    backend_src = Path(__file__).parent / "src" / "backend" / "src"
    build_ctx = Path(__file__).parent / "build-context-backend"

    if build_ctx.exists():
        import shutil
        shutil.rmtree(build_ctx)
    build_ctx.mkdir()

    # Copy source files
    for item in backend_src.rglob("*"):
        if item.is_file() and item.name != "__pycache__":
            rel = item.relative_to(backend_src)
            dest = build_ctx / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(item.read_bytes())

    # Copy requirements.txt
    req = Path(__file__).parent / "src" / "backend" / "requirements.txt"
    if req.exists():
        import shutil
        shutil.copy2(str(req), str(build_ctx / "requirements.txt"))

    # Copy tests
    tests_dir = Path(__file__).parent / "src" / "backend" / "tests"
    if tests_dir.exists():
        import shutil
        dest_tests = build_ctx / "tests"
        if dest_tests.exists():
            shutil.rmtree(dest_tests)
        shutil.copytree(str(tests_dir), str(dest_tests))

    # Create requirements.txt at root for Dockerfile
    req_content = req.read_text() if req.exists() else ""
    (build_ctx / "requirements.txt").write_text(req_content)

    log(f"Build context created at {build_ctx}")
    return True


def upload_file(sftp, local_path, remote_path):
    """Upload a single file via SFTP."""
    try:
        sftp.put(str(local_path), remote_path)
        log(f"  Uploaded: {local_path.name} -> {remote_path}")
        return True
    except Exception as e:
        log(f"  Upload failed {local_path.name}: {e}", "RED")
        return False


def upload_directory(sftp, local_dir, remote_dir, exclude=None):
    """Recursively upload a directory."""
    if exclude is None:
        exclude = {"__pycache__", "*.pyc", ".git", ".env", "node_modules", ".DS_Store"}

    local_path = Path(local_dir)
    for item in local_path.iterdir():
        if item.name in exclude or item.name.startswith("."):
            continue

        remote_item = f"{remote_dir}/{item.name}"

        if item.is_dir():
            try:
                sftp.mkdir(remote_item)
            except IOError:
                pass
            upload_directory(sftp, item, remote_item, exclude)
        elif item.is_file():
            upload_file(sftp, item, remote_item)


def deploy():
    """Main deployment flow."""
    log("=" * 60)
    log("  Server Deployment — tlcw.yobeeo.com")
    log("=" * 60)

    if not SSH_PASSWORD:
        log("ERROR: SSH_PASSWORD not set", "RED")
        log("Set SSH_PASSWORD env var or add to .env file")
        return False

    # ── 1. Connect ─────────────────────────────────────────────────────────
    log("\n[1/7] Connecting to server...")
    ssh = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=15)
        log("[OK] Connected")
    except Exception as e:
        log(f"SSH connect failed: {e}", "RED")
        return False

    try:
        # ── 2. Build frontend ──────────────────────────────────────────────
        if not build_frontend():
            log("Frontend build failed", "RED")
            return False

        # ── 3. Upload backend source ───────────────────────────────────────
        log("\n[3/7] Uploading backend source...")
        sftp = ssh.open_sftp()

        # Create remote directories
        run_cmd(ssh, f"mkdir -p {PROJECT_PATH}/src/backend/src", "Create backend dirs")
        run_cmd(ssh, f"mkdir -p {PROJECT_PATH}/src/backend/tests", "Create tests dir")
        run_cmd(ssh, f"mkdir -p {PROJECT_PATH}/frontend", "Create frontend dir")

        # Upload backend source
        upload_directory(sftp,
            Path(__file__).parent / "src" / "backend" / "src",
            f"{PROJECT_PATH}/src/backend/src")
        # Upload tests
        upload_directory(sftp,
            Path(__file__).parent / "src" / "backend" / "tests",
            f"{PROJECT_PATH}/src/backend/tests")
        # Upload requirements
        req = Path(__file__).parent / "src" / "backend" / "requirements.txt"
        if req.exists():
            upload_file(sftp, req, f"{PROJECT_PATH}/requirements.txt")

        sftp.close()
        log("[OK] Backend source uploaded")

        # ── 4. Upload frontend build ───────────────────────────────────────
        log("\n[4/7] Uploading frontend build...")
        sftp = ssh.open_sftp()
        upload_directory(sftp,
            Path(__file__).parent / "src" / "frontend" / "build",
            f"{PROJECT_PATH}/frontend/build")
        sftp.close()
        log("[OK] Frontend build uploaded")

        # ── 5. Update nginx config ─────────────────────────────────────────
        log("\n[5/7] Updating nginx config...")
        nginx_conf = Path(__file__).parent / "nginx" / "nginx.production.conf"
        if nginx_conf.exists():
            sftp = ssh.open_sftp()
            upload_file(sftp, nginx_conf, f"{PROJECT_PATH}/nginx_conf/nginx.conf")
            sftp.close()
            log("[OK] Nginx config updated")

        # ── 6. Rebuild backend image ───────────────────────────────────────
        log("\n[6/7] Rebuilding backend Docker image...")
        run_cmd(ssh, f"cd {PROJECT_PATH} && docker build -t ollp-backend:latest -f Dockerfile.backend .",
                "Build backend image", timeout=600)
        run_cmd(ssh, f"docker stop ollp-backend 2>/dev/null; docker rm ollp-backend 2>/dev/null; true",
                "Stop old container", timeout=30)
        run_cmd(ssh, f"cd {PROJECT_PATH} && docker run -d "
                f"--name ollp-backend "
                f"-p 8000:8000 "
                f"-e DATABASE_URL=sqlite:////opt/ollp/ollp.db "
                f"-e SECRET_KEY=test "
                f"-e CRYPTO_KEY_HEX=0000000000000000000000000000000000000000000000000000000000000000 "
                f"-e FRONTEND_URL=http://tlcw.yobeeo.com "
                f"-e LOG_LEVEL=info "
                f"-v /opt/ollp/logs:/app/logs "
                f"-v /opt/ollp/uploads:/app/uploads "
                f"-v {PROJECT_PATH}/src:/app/src "
                f"ollp-backend:latest",
                "Start new container", timeout=60)
        time.sleep(5)

        # ── 7. Verify ──────────────────────────────────────────────────────
        log("\n[7/7] Verifying deployment...")
        run_cmd(ssh, "curl -s http://localhost:8000/health", "Health check")
        run_cmd(ssh, "curl -s http://localhost/health", "Nginx health check")
        run_cmd(ssh, "curl -s http://localhost/ | head -c 200", "Frontend check")
        run_cmd(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "Container status")

        log("\n" + "=" * 60)
        log("  Deployment complete!")
        log("  Backend API:  http://tlcw.yobeeo.com:8000/health")
        log("  Frontend:     http://tlcw.yobeeo.com/")
        log("  API Docs:     http://tlcw.yobeeo.com:8000/docs")
        log("=" * 60)
        return True

    except Exception as e:
        log(f"Deployment failed: {e}", "RED")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh:
            ssh.close()
            log("[OK] SSH connection closed")


if __name__ == "__main__":
    ok = deploy()
    sys.exit(0 if ok else 1)
