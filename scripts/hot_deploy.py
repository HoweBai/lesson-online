import paramiko, time, os, sys
SSH_PASSWORD = "tlcw_CENTOS@#2023"

# Read local build
local_css = 'src/frontend/build/static/css/main.05685f41.css'
local_html = 'src/frontend/build/index.html'

if not os.path.exists(local_css):
    print(f"Local build not found: {local_css}")
    sys.exit(1)

print(f"Local CSS size: {os.path.getsize(local_css)} bytes")
print(f"Local dark selectors: {open(local_css).read().count('is(.dark')}")

# Try multiple SSH attempts
for attempt in range(5):
    print(f"\nAttempt {attempt+1}/5...")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        c.connect('119.27.173.222', username='root', password=SSH_PASSWORD, timeout=20)

        # Check container status
        s,t,e = c.exec_command('docker ps --format "{{.Names}} {{.Status}}" | grep frontend')
        time.sleep(2)
        status = s.read().decode().strip() if s else 'unknown'
        print(f"Frontend: {status}")

        if 'Up' in status and 'healthy' in status.lower():
            print("Container is healthy, trying to copy files...")

            # Copy CSS file directly to container
            with open(local_css, 'rb') as f:
                c.open_sftp().putfo(f, '/usr/share/nginx/html/static/css/main.05685f41.css')
            print("CSS copied!")

            # Copy index.html
            with open(local_html, 'rb') as f:
                c.open_sftp().putfo(f, '/usr/share/nginx/html/index.html')
            print("HTML copied!")

            # Restart nginx
            c.exec_command('docker exec ollp-nginx nginx -s reload', timeout=10)
            time.sleep(3)
            s,t,e = c.exec_command('curl -sk https://localhost/ | grep -o "main\.[a-f0-9]*\.css"')
            time.sleep(2)
            new_css = s.read().decode().strip() if s else 'unknown'
            print(f"New CSS: {new_css}")

        c.close()
        print("\nDeployment complete!")
        break
    except Exception as ex:
        print(f"Error: {ex}")
        try:
            c.close()
        except:
            pass
    time.sleep(15)
