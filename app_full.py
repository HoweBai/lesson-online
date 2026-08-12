import re

with open("/opt/ollp/frontend/static/js/main.de6c3c14.js") as f:
    content = f.read()

# Find the App component (pi) and the render call
idx = content.find("pi=")
render_idx = content.find('getElementById("root")')
if idx > 0 and render_idx > 0:
    app_code = content[idx:render_idx+100]
    print(app_code[:5000])
elif idx > 0:
    app_code = content[idx:idx+5000]
    print(app_code[:5000])
