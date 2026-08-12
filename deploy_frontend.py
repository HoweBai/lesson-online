#!/usr/bin/env python3
"""Deploy React frontend to tlcw.yobeeo.com with Node.js v18"""
import paramiko
import subprocess
import os
import sys
import json
import base64

SSH_HOST = 'tlcw.yobeeo.com'
SSH_USER = 'root'
SSH_PASSWORD = 'tlcw_CENTOS@#2023'

def run_ssh(ssh, command, description=""):
    """Run SSH command and return result"""
    print(f"\n>>> {description}")
    print(f"    Command: {command}")
    stdin, stdout, stderr = ssh.exec_command(command, timeout=120)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    if output:
        print(f"    Output: {output[:500]}")
    if error:
        print(f"    Error: {error[:500]}")
    return output, error

def install_nodejs_v18(ssh):
    """Install Node.js v18 on CentOS Stream 8"""
    print("\n=== Installing Node.js v18 ===")

    # Remove old Node.js if exists
    run_ssh(ssh, "yum remove -y nodejs 2>/dev/null || true", "Remove old Node.js")

    # Install NodeSource repository for Node.js 18
    run_ssh(ssh, "curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -", "Setup NodeSource repo")

    # Install Node.js
    run_ssh(ssh, "yum install -y nodejs", "Install Node.js v18")

    # Verify installation
    output, _ = run_ssh(ssh, "node --version && npm --version", "Verify Node.js")

    if "v18." in output:
        print("[OK] Node.js v18 installed successfully!")
        return True
    else:
        print(f"[WARN] Unexpected Node.js version: {output}")
        return False

def build_frontend():
    """Build React frontend locally"""
    print("\n=== Building React Frontend ===")
    frontend_dir = os.path.join(os.path.dirname(__file__), 'src', 'frontend')
    if not os.path.exists(frontend_dir):
        print(f"[ERROR] Frontend directory not found: {frontend_dir}")
        return False

    # Install dependencies
    print("Installing npm dependencies...")
    result = subprocess.run(
        ['npm', 'install'],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        timeout=180
    )
    if result.returncode != 0:
        print(f"npm install failed: {result.stderr[-500:]}")
        return False
    print("npm install completed")

    # Build
    print("Building frontend...")
    result = subprocess.run(
        ['npm', 'run', 'build'],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        timeout=300
    )
    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr[-1000:]}")
        return False

    build_dir = os.path.join(frontend_dir, 'build')
    if os.path.exists(build_dir):
        print(f"[OK] Frontend built successfully at {build_dir}")
        return True
    else:
        print("[ERROR] Build directory not found after build")
        return False

def deploy_frontend(ssh):
    """Upload built frontend to server"""
    print("\n=== Deploying Frontend ===")
    frontend_dir = os.path.join(os.path.dirname(__file__), 'src', 'frontend')
    build_dir = os.path.join(frontend_dir, 'build')

    if not os.path.exists(build_dir):
        print(f"[ERROR] Build directory not found: {build_dir}")
        return False

    # Create remote directory
    run_ssh(ssh, "mkdir -p /opt/ollp/frontend && chmod 755 /opt/ollp/frontend", "Create frontend directory")

    # Upload files
    print("Uploading frontend files...")
    sftp = ssh.open_sftp()
    uploaded = 0
    for root, dirs, files in os.walk(build_dir):
        for file in files:
            local_path = os.path.join(root, file)
            rel_path = os.path.relpath(local_path, build_dir)
            remote_path = f"/opt/ollp/frontend/{rel_path}"

            # Create remote directory
            remote_dir = os.path.dirname(remote_path)
            try:
                sftp.stat(remote_dir)
            except:
                sftp.mkdir(remote_dir)

            # Upload file
            sftp.put(local_path, remote_path)
            uploaded += 1

    sftp.close()
    print(f"[OK] Uploaded {uploaded} files to server")
    return True

def restart_nginx(ssh):
    """Restart nginx to pick up new frontend"""
    print("\n=== Restarting Nginx ===")
    run_ssh(ssh, "docker restart ollp-nginx 2>/dev/null || docker restart nginx || systemctl restart nginx", "Restart nginx")
    run_ssh(ssh, "sleep 2 && curl -s http://localhost/health", "Verify nginx")

def main():
    print("=" * 60)
    print("Frontend Build & Deploy Script")
    print("=" * 60)

    # Connect to server
    print("\n[INFO] Connecting to server...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=15)
    print("[OK] Connected to server")

    try:
        # Step 1: Install Node.js v18
        if not install_nodejs_v18(ssh):
            print("[ERROR] Failed to install Node.js v18")
            return 1

        # Step 2: Build frontend locally
        if not build_frontend():
            print("[ERROR] Failed to build frontend")
            return 1

        # Step 3: Deploy frontend
        if not deploy_frontend(ssh):
            print("[ERROR] Failed to deploy frontend")
            return 1

        # Step 4: Restart nginx
        restart_nginx(ssh)

        # Final verification
        print("\n=== Final Verification ===")
        run_ssh(ssh, "curl -s http://localhost/health", "Backend health")
        run_ssh(ssh, "curl -s http://localhost/ | head -5", "Frontend page")

        print("\n" + "=" * 60)
        print("[SUCCESS] Deployment completed successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        ssh.close()
        print("\n[INFO] Connection closed")

if __name__ == '__main__':
    sys.exit(main())
