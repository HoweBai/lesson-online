import paramiko, time, os
SSH_PASSWORD = "tlcw_CENTOS@#2023"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password=SSH_PASSWORD, timeout=20)

def run(cmd):
    s,t,e = c.exec_command(cmd, timeout=60)
    out = s.read().decode()
    err = e.read().decode()
    return out.strip(), err.strip()

print("Step 1: Git pull latest...")
run('cd /root/lesson-online && git pull origin main')

print("Step 2: Copy build files to nginx...")
# Copy the entire build directory
run('cp -r /root/lesson-online/src/frontend/build/* /usr/share/nginx/html/')

print("Step 3: Verify new CSS...")
out, _ = run('ls -la /usr/share/nginx/html/static/css/')
print(out)

out, _ = run('grep -c "is(.dark" /usr/share/nginx/html/static/css/main.*.css')
print(f"Dark selectors on server: {out}")

print("Step 4: Check website...")
out, _ = run('curl -sk https://localhost/ | grep -o "main\.[a-f0-9]*\.css"')
print(f"CSS referenced: {out}")

c.close()
print("\nDeployment complete!")
