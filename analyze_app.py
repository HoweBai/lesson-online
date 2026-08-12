import re

with open('/opt/ollp/frontend/static/js/main.de6c3c14.js', 'r') as f:
    content = f.read()

print(f"Bundle size: {len(content)}")

# Find the App component
idx = content.find('pi=')
if idx < 0:
    print("App component not found")
    exit(1)

# Find the Routes section
routes_idx = content.find('(0,We.jsx)(Ee,{children:', idx)
if routes_idx < 0:
    print("Routes not found")
    exit(1)

print(f"Found Routes at {routes_idx}")
routes_ctx = content[routes_idx:routes_idx+2000]
print(routes_ctx[:1000])
