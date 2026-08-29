# 手动部署步骤（在服务器上执行）
# 1. SSH 到服务器
# ssh root@119.27.173.222

# 2. 拉取最新代码
cd /root/lesson-online && git pull origin main

# 3. 检查 postcss 配置是否存在
ls src/frontend/postcss.config.js

# 4. 重新构建前端（需要 ~3 分钟）
cd /opt/ollp && docker build --no-cache -t ollp-frontend -f src/frontend/Dockerfile.production src/frontend/

# 5. 重启前端容器
docker compose -f docker-compose.production.yml restart frontend

# 6. 验证
curl -sk https://localhost/ | grep "main.*\.css"
curl -sk https://tlcw.yobeeo.com/static/css/main.*.css | grep -c "is(.dark"
