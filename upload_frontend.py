#!/usr/bin/env python3
"""Upload built frontend to server"""
import paramiko
import os
import sys

SSH_HOST = 'tlcw.yobeeo.com'
SSH_USER = 'root'
SSH_PASSWORD = 'tlcw_CENTOS@#2023'

def upload_frontend(ssh):
    """Upload built frontend to server"""
    print("=== Deploying Frontend ===")
    frontend_dir = os.path.join(os.path.dirname(__file__), 'src', 'frontend')
    build_dir = os.path.join(frontend_dir, 'build')

    if not os.path.exists(build_dir):
        print(f"[ERROR] Build directory not found: {build_dir}")
        return False

    # Create remote directory
    stdin, stdout, stderr = ssh.exec_command("mkdir -p /opt/ollp/frontend && chmod 755 /opt/ollp/frontend")
    print(stdout.read().decode().strip() or "Created /opt/ollp/frontend")

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
    stdin, stdout, stderr = ssh.exec_command("docker restart ollp-nginx 2>/dev/null || docker restart nginx || systemctl restart nginx")
    print(stdout.read().decode().strip())
    stdin, stdout, stderr = ssh.exec_command("sleep 2 && curl -s http://localhost/health")
    print(f"Health check: {stdout.read().decode().strip()}")

def verify_deploy(ssh):
    """Verify deployment"""
    print("\n=== Verification ===")
    stdin, stdout, stderr = ssh.exec_command("ls -la /opt/ollp/frontend/ | head -10")
    print("Remote files:", stdout.read().decode().strip()[:500])

    stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost/ | head -5")
    print("\nFrontend page:", stdout.read().decode().strip()[:300])

    stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost/health")
    print("\nBackend health:", stdout.read().decode().strip())

def main():
    print("=" * 60)
    print("Frontend Deploy Script")
    print("=" * 60)

    print("\n[INFO] Connecting to server...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=15)
    print("[OK] Connected to server")

    try:
        if not upload_frontend(ssh):
            print("[ERROR] Failed to upload frontend")
            return 1

        restart_nginx(ssh)
        verify_deploy(ssh)

        print("\n" + "=" * 60)
        print("[SUCCESS] Deployment completed!")
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
