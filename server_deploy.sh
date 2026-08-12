#!/bin/bash
# Online Learning Platform - 服务器端部署脚本
# 直接在服务器上执行

set -e

echo "=========================================="
echo "  Online Learning Platform 部署脚本"
echo "=========================================="
echo ""

# 项目路径
PROJECT_PATH="/opt/online-learning-platform"
cd "$PROJECT_PATH"

echo "[1/6] 检查Python环境..."
python3 --version || echo "Python3未安装"

echo "[2/6] 安装Python依赖..."
cd src/backend
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt
echo "Python依赖安装完成"

echo "[3/6] 检查Node.js环境..."
cd ../..
cd src/frontend
node --version || echo "Node.js未安装"

echo "[4/6] 安装前端依赖..."
npm install --legacy-peer-deps 2>/dev/null || npm install
echo "前端依赖安装完成"

echo "[5/6] 启动后端服务..."
cd ../backend
nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload > /app/logs/backend.log 2>&1 &
echo "后端服务已启动 (PID: $!)"

echo "[6/6] 启动前端服务..."
cd ../../frontend
nohup npm start > /app/logs/frontend.log 2>&1 &
echo "前端服务已启动 (PID: $!)"

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  前端应用: http://tlcw.yobeeo.com:3000"
echo "  API文档:  http://tlcw.yobeeo.com:8000/docs"
echo "  健康检查: http://tlcw.yobeeo.com:8000/health"
echo ""
echo "管理命令:"
echo "  查看日志: tail -f /opt/online-learning-platform/logs/*.log"
echo "  停止服务: pkill -f 'uvicorn\|npm start'"
echo "  重启服务: ./deploy.sh"
echo ""
