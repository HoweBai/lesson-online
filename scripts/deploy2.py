import paramiko
SSH_PASSWORD = "tlcw_CENTOS@#2023"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('119.27.173.222', username='root', password=SSH_PASSWORD, timeout=15)

def run(cmd):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out.strip(), err.strip()

# Check git status
print("=== Git status ===")
out, _ = run('cd /root/lesson-online && git status --short')
print(out or "clean")

print("=== Git log ===")
out, _ = run('cd /root/lesson-online && git log --oneline -3')
print(out)

print("=== Remote log ===")
out, _ = run('cd /root/lesson-online && git log --oneline origin/main -3')
print(out)

# Force reset to origin/main
print("=== Force reset ===")
out, err = run('cd /root/lesson-online && git reset --hard origin/main')
print(f"reset: {out}, err: {err}")

print("=== After reset ===")
out, _ = run('cd /root/lesson-online && git log --oneline -3')
print(out)

# Verify
print("=== Verify dark classes ===")
out, _ = run('grep -c "dark:text-gray-200" /root/lesson-online/src/frontend/src/App.tsx')
print(f"dark:text-gray-200: {out}")
out, _ = run('grep -c "dark:bg-gray-900" /root/lesson-online/src/frontend/src/index.css')
print(f"dark:bg-gray-900: {out}")

# Copy source
print("=== Copy source ===")
out, err = run('cp -r /root/lesson-online/src/frontend/src /opt/ollp/src/frontend/')
print(f"copy: {out or 'ok'}")

c.close()
print("Done!")
