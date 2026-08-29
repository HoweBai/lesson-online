import paramiko, os, sys
SSH_PASSWORD = "tlcw_CENTOS@#2023"

# Check local build exists
css_file = 'src/frontend/build/static/css/main.05685f41.css'
html_file = 'src/frontend/build/index.html'
js_file = 'src/frontend/build/static/js/main.30595dd2.js'

if not os.path.exists(css_file):
    print(f"Local build not found: {css_file}")
    sys.exit(1)

print(f"Local build ready:")
print(f"  CSS: {os.path.getsize(css_file)} bytes")
print(f"  HTML: {os.path.getsize(html_file)} bytes")
dark_count = open(css_file).read().count('is(.dark')
print(f"  Dark selectors: {dark_count}")

# Connect via SFTP
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password=SSH_PASSWORD, timeout=20)
sftp = c.open_sftp()

try:
    print("\nUploading files via SFTP...")

    # Upload CSS
    sftp.put(css_file, '/usr/share/nginx/html/static/css/main.05685f41.css')
    print("  CSS uploaded")

    # Upload HTML
    sftp.put(html_file, '/usr/share/nginx/html/index.html')
    print("  HTML uploaded")

    # Upload JS if exists
    if os.path.exists(js_file):
        sftp.put(js_file, '/usr/share/nginx/html/static/js/main.30595dd2.js')
        print("  JS uploaded")

    # List uploaded files
    files = sftp.listdir('/usr/share/nginx/html/static/css/')
    print(f"\nUploaded CSS files: {files}")

    # Restart nginx to pick up changes
    print("\nReloading nginx...")
    stdin, stdout, stderr = c.exec_command('docker exec ollp-nginx nginx -s reload', timeout=10)
    import time; time.sleep(2)
    print(stdout.read().decode().strip() if stdout else "(reloaded)")

    # Verify
    print("\nVerifying deployment...")
    import requests
    r = requests.get('https://tlcw.yobeeo.com/', timeout=10, verify=False)
    import re
    m = re.search(r'href="(/static/css/main\.[a-f0-9]+\.css)"', r.text)
    if m:
        css_url = 'https://tlcw.yobeeo.com' + m.group(1)
        css = requests.get(css_url, timeout=10, verify=False)
        new_dark = css.text.count('is(.dark')
        print(f"New CSS: {m.group(1)}")
        print(f"Dark selectors: {new_dark}")
        if new_dark >= 70:
            print("\n✅ Deployment successful!")
        else:
            print("\n⚠️  CSS may need cache refresh")
    else:
        print("Could not verify CSS URL")

except Exception as ex:
    print(f"Error: {ex}")
    import traceback; traceback.print_exc()
finally:
    sftp.close()
    c.close()
