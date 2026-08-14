# 项目冗余文件清理清单

**分析日期**: 2026-08-14  
**基于**: 源码结构、git 历史、README 引用关系

---

## 🚨 严重问题 — 立即删除

### 1. 根目录散落的异常命名文件（git 追踪外的孤儿文件）

这些文件名是路径名直接拼接而成（如 `d:projectlessons...`），是 git worktree 或路径操作产生的残留，不是真正的源代码文件。

| 文件 | 原因 |
|------|------|
| `d:projectlessons.env.example` | 应为 `.env.example`，文件名错误 |
| `d:projectlessonsdocker-compose.yml` | 重复的 docker-compose，文件名错误 |
| `d:projectlessonsrequirements.txt` | 重复的 requirements.txt，文件名错误 |
| `d:projectlessonssrcbackendsrc__init__.py` | 空文件（0 字节），路径拼接残留 |
| `d:projectlessonssrcbackendsrcapi__init__.py` | 空文件（0 字节），路径拼接残留 |
| `d:projectlessonssrcbackendsrcdatabase.py` | 与 `src/backend/src/database.py` 重复 |
| `d:projectlessonssrcbackendsrcmodels__init__.py` | 空文件（0 字节），路径拼接残留 |
| `d:projectlessonssrcbackendsrcmodelsclaude_config.py` | 旧模型文件副本 |
| `d:projectlessonssrcbackendsrcmodelsknowledge_mapping.py` | 旧模型文件副本 |
| `d:projectlessonssrcbackendsrcmodelsprofile.py` | 旧模型文件副本 |
| `d:projectlessonssrcbackendsrcmodelsuser.py` | 旧模型文件副本 |
| `d:projectlessonssrcbackendsrcservices__init__.py` | 空文件（0 字节），路径拼接残留 |
| `d:projectlessonssrcbackendsrcservicesauth_service.py` | 旧服务文件副本 |

### 2. 重复的部署脚本（7 个仅有一个应保留）

README 仅引用 `deploy_compose.py`，其他均为迭代过程中的废弃版本。所有脚本均含硬编码服务器密码（`tlcw_CENTOS@#2023`）。

| 文件 | 保留？ | 原因 |
|------|--------|------|
| `deploy_compose.py` | ✅ 保留 | README 引用，当前推荐方式 |
| `deploy_full.py` | ❌ 删除 | 与 deploy_compose.py 功能重叠 |
| `deploy_p3.py` | ❌ 删除 | P3 专项部署，已随功能合并 |
| `deploy_backend_v2.py` | ❌ 删除 | v2 版本已废弃 |
| `deploy_cli.py` | ❌ 删除 | 包含 quick_deploy() 但已被取代 |
| `deploy_frontend.py` | ❌ 删除 | 仅部署前端，是完整流程的子集 |
| `deploy_password_reset.py` | ❌ 删除 | 单功能脚本，已被集成 |
| `deploy_to_server.py` | ❌ 删除 | 已被 deploy_compose.py 取代 |
| `cloud_deploy.py` | ❌ 删除 | 早期云端部署脚本 |

### 3. 一次性临时脚本

| 文件 | 原因 |
|------|------|
| `analyze_app.py` | 分析生产环境打包代码的调试脚本 |
| `app_full.py` | 从生产代码中提取 App 组件的调试脚本 |
| `create_admin.py` | 手动创建管理员，已有 `src/backend/src/init_admin.py` 替代 |
| `test_api.py` | 本地手动测试脚本（硬编码 localhost） |
| `test_deployment.py` | SSH 连接测试，含硬编码密码 |
| `test_ssh.py` | SSH 连通性测试，含硬编码密码 |
| `upload_frontend.py` | 手动上传前端构建产物，已被集成到主部署脚本 |
| `direct_deploy.py` | 直接部署脚本，与主脚本重复 |
| `quick_deploy.py` | 快速部署脚本，与主脚本重复 |
| `quick_deploy_v2.py` | 快速部署 v2，与主脚本重复 |
| `simple_deploy.py` | 简化部署脚本，与主脚本重复 |
| `deploy.sh` | Shell 部署脚本，与 Python 脚本重复 |
| `server_deploy.sh` | 服务器部署脚本，与 Python 脚本重复 |

### 4. 已过时的文档

| 文件 | 原因 |
|------|------|
| `PHASE1_COMPLETE.md` | 阶段性完成记录，已被后续阶段覆盖 |
| `PHASE2_COMPLETE.md` | 同上 |
| `PHASE3_COMPLETE.md` | 同上 |
| `PHASE4_COMPLETE.md` | 同上 |
| `DEPLOYMENT_COMPLETE.md` | 单次部署记录，信息已过时 |
| `FUNCTIONAL_GAP_ANALYSIS.md` | 旧版差距分析（2026-07-30），已被 v2 取代 |

---

## ⚠️ 中度冗余 — 建议清理

### 5. Celery 异步任务框架（未集成）

这些文件构建了完整的 Celery 框架，但 API 从未调用它们。保留会增加维护负担和混淆。

| 文件 | 说明 |
|------|------|
| `src/backend/src/celery_worker.py` | Celery worker 入口（56 行） |
| `src/backend/tasks/generation_tasks.py` | Celery 任务定义（242 行） |
| `Dockerfile.worker` | Celery Worker 的 Docker 镜像 |

> **注意**: `docker-compose.yml` 中仍引用了 `celery-worker` 服务（第 65-72 行），需同步清理。

### 6. 过时的 Nginx 配置

| 文件 | 原因 |
|------|------|
| `nginx.production.conf` | 旧版生产配置，缺少缓存优化（已被 `nginx_new.conf` 取代但未使用） |
| `nginx_new.conf` | 中间版本，当前 docker-compose.production.yml 使用的是 `nginx/nginx.conf` |

实际使用的配置是 `nginx/nginx.conf`（开发环境）和 `nginx.production.conf`（生产环境在 docker-compose.production.yml 中引用），`nginx_new.conf` 是两者之间的过渡产物。

---

## ✅ 保留的文件（确认有效）

### 核心文档
- `README.md` — 项目主文档
- `DOCKER_DEPLOYMENT.md` — Docker 部署指南
- `DEPLOYMENT_GUIDE.md` — 部署指南
- `FUNCTIONAL_GAP_ANALYSIS_v2.md` — 最新功能差距分析（2026-08-12）

### 核心配置文件
- `docker-compose.yml` — 开发环境编排
- `docker-compose.production.yml` — 生产环境编排
- `nginx/nginx.conf` — 开发环境 Nginx
- `.dockerignore`、`.gitignore`
- `Dockerfile.backend`、`Dockerfile.frontend`
- `requirements.txt`（根目录）、`src/backend/requirements.txt`

### 源代码
- `src/backend/src/` — 后端完整源码
- `src/frontend/src/` — 前端完整源码
- `src/backend/tests/` — 测试套件
- `docs/` — 设计文档

---

## 清理后的预期效果

| 类别 | 删除数量 | 节省行数（约） |
|------|----------|---------------|
| 异常命名孤儿文件 | 13 个 | ~200 行 |
| 重复部署脚本 | 8 个 | ~2,500 行 |
| 临时脚本 | 13 个 | ~1,200 行 |
| 过时文档 | 6 个 | ~3,000 行 |
| Celery 框架 | 3 个 | ~324 行 |
| 过渡配置文件 | 1 个 | ~40 行 |
| **合计** | **~44 个** | **~7,264 行** |

---

## 执行命令

```bash
# 1. 删除异常命名文件
rm -f d:projectlessons.env.example \
      d:projectlessonsdocker-compose.yml \
      d:projectlessonsrequirements.txt \
      d:projectlessonssrcbackendsrc__init__.py \
      d:projectlessonssrcbackendsrcapi__init__.py \
      d:projectlessonssrcbackendsrcdatabase.py \
      d:projectlessonssrcbackendsrcmodels__init__.py \
      d:projectlessonssrcbackendsrcmodelsclaude_config.py \
      d:projectlessonssrcbackendsrcmodelsknowledge_mapping.py \
      d:projectlessonssrcbackendsrcmodelsprofile.py \
      d:projectlessonssrcbackendsrcmodelsuser.py \
      d:projectlessonssrcbackendsrcservices__init__.py \
      d:projectlessonssrcbackendsrcservicesauth_service.py

# 2. 删除重复部署脚本
rm -f deploy_full.py deploy_p3.py deploy_backend_v2.py deploy_cli.py \
      deploy_frontend.py deploy_password_reset.py deploy_to_server.py cloud_deploy.py

# 3. 删除临时脚本
rm -f analyze_app.py app_full.py create_admin.py test_api.py \
      test_deployment.py test_ssh.py upload_frontend.py \
      direct_deploy.py quick_deploy.py quick_deploy_v2.py simple_deploy.py \
      deploy.sh server_deploy.sh

# 4. 删除过时文档
rm -f PHASE1_COMPLETE.md PHASE2_COMPLETE.md PHASE3_COMPLETE.md \
      PHASE4_COMPLETE.md DEPLOYMENT_COMPLETE.md FUNCTIONAL_GAP_ANALYSIS.md

# 5. 删除 Celery 框架（需同步修改 docker-compose.yml）
rm -f src/backend/src/celery_worker.py \
      src/backend/tasks/generation_tasks.py \
      Dockerfile.worker

# 6. 删除过渡 nginx 配置
rm -f nginx_new.conf
```
