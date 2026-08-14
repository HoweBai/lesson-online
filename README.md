# LearnHub — AI 驱动的个人化教程学习平台

一个生产级在线学习平台，核心功能是通过 **Claude API** 为用户生成循序渐进、个性化的计算机科学知识教程。支持游客浏览公开教程，注册用户可通过收集个人信息并使用 AI 生成完整课程大纲和逐章详细讲解（含数学公式推导、代码示例和练习题）。

**版本**: v1.2.0  
**最后更新**: 2026-08-14  
**部署地址**: https://tlcw.yobeeo.com/

---

## 技术栈

| 层 | 技术 |
|---|---|
| **后端** | FastAPI + SQLAlchemy (async) + PostgreSQL + Redis |
| **前端** | React 18 + TypeScript + Tailwind CSS + React Router v6 |
| **AI 集成** | Claude API / OpenAI API (通过统一 LLM Adapter) |
| **实时通信** | WebSocket (Claude Code 聊天室) |
| **认证** | JWT + OAuth2 (Google / GitHub) |
| **部署** | Docker Compose (PostgreSQL + Redis + Nginx) |
| **测试** | pytest + FastAPI TestClient |

---

## 已完成功能

### 认证与授权

| 功能 | 状态 | 说明 |
|------|------|------|
| 邮箱密码注册/登录 | ✅ | JWT Token，密码 bcrypt 哈希 |
| 密码找回 | ✅ | 邮件令牌重置 |
| Google OAuth 登录 | ✅ | authlib 授权码流程 |
| GitHub OAuth 登录 | ✅ | authlib 授权码流程 |
| 管理员权限控制 | ✅ | `is_admin` 字段 + AdminGuard |
| 速率限制 | ✅ | slowapi + Redis 滑动窗口 |
| 敏感信息检测 | ✅ | PII 检测 + 不当语言过滤 |

### 教程系统

| 功能 | 状态 | 说明 |
|------|------|------|
| 教程创建向导 | ✅ | 4 步向导：个人信息 → Claude 配置 → 大纲 → 章节生成 |
| AI 大纲生成 | ✅ | 基于用户背景的个性化课程大纲 |
| 逐章生成 | ✅ | 每章完成后手动触发下一章节 |
| 前置知识检查 | ✅ | 基于用户知识图谱的智能依赖分析 |
| 教程 CRUD | ✅ | 创建/编辑/删除/发布/取消发布 |
| 教程导出 | ✅ | Markdown / JSON / PDF（WeasyPrint）异步导出，MinIO 对象存储上传 |
| 教程分享 | ✅ | 分享码短链接 + ShareModal 社交分享 |

### 用户系统

| 功能 | 状态 | 说明 |
|------|------|------|
| 用户档案 | ✅ | 学习目标、编程水平、数学背景、学习风格 |
| 知识图谱推断 | ✅ | 从用户档案推断知识点掌握程度 |
| 收藏/书签 | ✅ | 收藏教程，个人中心查看 |
| 学习统计图表 | ✅ | Recharts 可视化学习进度和时长 |
| 暗色模式 | ✅ | ThemeContext + Tailwind dark: 策略 |
| Toast 通知系统 | ✅ | react-hot-toast 统一提示 |

### 公共课程库

| 功能 | 状态 | 说明 |
|------|------|------|
| 公开教程列表 | ✅ | 分页、搜索、排序（最新/最热/最多章节） |
| 教程详情 | ✅ | 章节导航、进度追踪、导出按钮 |
| 点赞/举报 | ✅ | 社交互动功能 |
| 评论系统 | ✅ | 支持回复和点赞，嵌套评论结构 |

### 管理员后台

| 功能 | 状态 | 说明 |
|------|------|------|
| 管理员登录 | ✅ | 独立登录入口 `/admin/login` |
| 用户管理 | ✅ | 列表、搜索、详情、状态切换、删除 |
| 教程审核 | ✅ | 待审核列表、通过/拒绝、审核意见 |
| 数据统计 | ✅ | 用户增长、教程统计、活跃度分析 |
| 仪表盘 | ✅ | 概览统计 + 图表可视化 |

### 实时通信

| 功能 | 状态 | 说明 |
|------|------|------|
| WebSocket 聊天 | ✅ | 基于教程的实时 Claude Code 对话 |
| 消息历史 | ✅ | SQLite 持久化聊天记录 |
| 在线状态 | ✅ | 连接管理、断线重连 |

### 系统功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 数据库备份/恢复 | ✅ | SQL dump 备份与还原 |
| 系统监控 | ✅ | 健康检查、指标收集、资源监控 |
| 告警服务 | ✅ | 异常检测与通知 |
| 审计日志 | ✅ | 用户操作记录 |
| API Key 加密存储 | ✅ | AES-GCM 加密 Claude API Key |
| Celery 异步任务队列 | ✅ | 大纲/章节生成、文件导出异步化，独立 Worker 服务 |
| MinIO 对象存储 | ✅ | 导出文件上传对象存储，预签名下载链接 |
| PDF 依赖补全 | ✅ | Dockerfile.backend 集成 pango/cairo 等 WeasyPrint 系统库 |

---

## API 概览

### 认证 (`/api/v1/auth`)

```
POST   /api/v1/auth/register          注册
POST   /api/v1/auth/login             登录
POST   /api/v1/auth/logout            登出
GET    /api/v1/auth/me                当前用户
POST   /api/v1/auth/forgot-password   忘记密码
POST   /api/v1/auth/reset-password    重置密码
```

### OAuth (`/api/v1/oauth`)

```
GET    /api/v1/oauth/google/init      Google 授权初始化
GET    /api/v1/oauth/github/init      GitHub 授权初始化
GET    /api/v1/oauth/google/callback  Google 回调
GET    /api/v1/oauth/github/callback  GitHub 回调
GET    /api/v1/oauth/me               当前 OAuth 连接
DELETE /api/v1/oauth/{provider}       取消 OAuth 授权
```

### 教程 (`/api/v1/tutorials`)

```
GET    /api/v1/tutorials              我的教程列表
POST   /api/v1/tutorials              创建教程
GET    /api/v1/tutorials/{id}         教程详情
PUT    /api/v1/tutorials/{id}         更新教程
DELETE /api/v1/tutorials/{id}         删除教程
POST   /api/v1/tutorials/{id}/publish 发布教程
POST   /api/v1/tutorials/{id}/unpublish 取消发布
POST   /api/v1/tutorials/generate-outline 生成大纲
PUT    /api/v1/tutorials/outlines/{id}/confirm 确认大纲
POST   /api/v1/tutorials/{id}/generate-next 生成下一章
GET    /api/v1/tutorials/{id}/chapters/{n}/status 章节状态
GET    /api/v1/tutorials/{id}/export/markdown  Markdown 导出
GET    /api/v1/tutorials/{id}/export/json     JSON 导出
GET    /api/v1/tutorials/{id}/export/outline  大纲导出
GET    /api/v1/tutorials/{id}/export/pdf      PDF 导出
POST   /api/v1/tutorials/{id}/export/{format} 异步导出（Celery + MinIO）
GET    /api/v1/tutorials/{id}/export/{format}/{task_id} 查询导出进度
DELETE /api/v1/tutorials/tasks/{task_id}      取消异步任务
GET    /api/v1/tutorials/share/{code}         分享码跳转
```

### 公共课程库 (`/api/v1/catalog`)

```
GET    /api/v1/catalog                公开教程列表（搜索/排序/分页）
GET    /api/v1/catalog/popular        热门教程
GET    /api/v1/catalog/{id}           教程详情
POST   /api/v1/catalog/{id}/like      点赞
POST   /api/v1/catalog/{id}/report    举报
```

### 书签 (`/api/v1/bookmarks`)

```
GET    /api/v1/bookmarks/bookmarks    我的收藏
POST   /api/v1/bookmarks/{tutorial_id}/bookmark  收藏
DELETE /api/v1/bookmarks/{tutorial_id}/bookmark  取消收藏
```

### 评论 (`/api/v1/comments`)

```
GET    /api/v1/comments/{tutorial_id}        获取评论
POST   /api/v1/comments/{tutorial_id}        发表评论
POST   /api/v1/comments/{tutorial_id}/replies  回复评论
POST   /api/v1/comments/{id}/like            点赞评论
DELETE /api/v1/comments/{id}                 删除评论
```

### 用户档案 (`/api/v1/users/profile`)

```
GET    /api/v1/users/profile           获取档案
PUT    /api/v1/users/profile           更新档案
GET    /api/v1/users/profile/stats     学习统计
```

### 管理员 (`/api/v1/admin`)

```
POST   /api/v1/admin/login           管理员登录
GET    /api/v1/admin/me              管理员信息
GET    /api/v1/admin/users           用户列表
GET    /api/v1/admin/users/{id}      用户详情
PUT    /api/v1/admin/users/{id}/status  更新用户状态
DELETE /api/v1/admin/users/{id}      删除用户
GET    /api/v1/admin/catalog/pending 待审核教程
PUT    /api/v1/admin/catalog/{id}/review 审核教程
GET    /api/v1/admin/stats/overview  概览统计
GET    /api/v1/admin/stats/users     用户统计
GET    /api/v1/admin/stats/tutorials 教程统计
```

### 系统 (`/`)

```
GET    /health                       健康检查
WS     /ws/claude/{tutorial_id}/{channel_id}  WebSocket 聊天
GET    /monitor/health               监控健康
GET    /monitor/metrics              系统指标
POST   /backup/now                   立即备份
POST   /backup/upload                上传备份
```

---

## 项目结构

```
online-learning-platform/
├── src/
│   ├── backend/                    # FastAPI 后端
│   │   ├── src/
│   │   │   ├── api/                # API 路由层
│   │   │   │   ├── main.py         # 应用入口 + 路由注册
│   │   │   │   ├── auth.py         # 认证 API
│   │   │   │   ├── oauth.py        # OAuth 第三方登录
│   │   │   │   ├── tutorials.py    # 教程 CRUD + 生成
│   │   │   │   ├── catalog.py      # 公共课程库
│   │   │   │   ├── bookmarks.py    # 书签
│   │   │   │   ├── comments.py     # 评论
│   │   │   │   ├── profile.py      # 用户档案
│   │   │   │   ├── export.py       # 内容导出
│   │   │   │   ├── admin.py        # 管理 API
│   │   │   │   ├── websocket.py    # WebSocket 聊天
│   │   │   │   ├── backup.py       # 备份/恢复
│   │   │   │   ├── monitor.py      # 系统监控
│   │   │   │   └── alerts.py       # 告警
│   │   │   ├── models/             # SQLAlchemy 数据模型
│   │   │   │   ├── user.py         # 用户
│   │   │   │   ├── tutorial.py     # 教程
│   │   │   │   ├── chapter.py      # 章节
│   │   │   │   ├── bookmark.py     # 书签
│   │   │   │   ├── comment.py      # 评论
│   │   │   │   ├── profile.py      # 用户档案
│   │   │   │   ├── oauth_token.py  # OAuth 令牌
│   │   │   │   ├── chat_history.py # 聊天历史
│   │   │   │   ├── task_log.py     # 任务日志
│   │   │   │   ├── audit_log.py    # 审计日志
│   │   │   │   ├── public_catalog.py # 公开课程
│   │   │   │   ├── claude_config.py  # Claude 配置
│   │   │   │   └── knowledge_mapping.py # 知识映射
│   │   │   ├── services/           # 业务逻辑层
│   │   │   │   ├── auth_service.py
│   │   │   │   ├── oauth_service.py
│   │   │   │   ├── export_service.py
│   │   │   │   ├── admin_service.py
│   │   │   │   ├── content_security.py  # 安全扫描
│   │   │   │   ├── knowledge_inferencer.py # 知识推断
│   │   │   │   ├── prerequisite_checker.py # 前置检查
│   │   │   │   ├── outline_generator.py   # 大纲生成
│   │   │   │   ├── chapter_generator.py   # 章节生成
│   │   │   │   ├── llm_adapter.py         # LLM 适配器
│   │   │   │   ├── crypto_service.py      # 加密服务
│   │   │   │   ├── backup_service.py      # 备份服务
│   │   │   │   └── alert_service.py       # 告警服务
│   │   │   ├── middleware/
│   │   │   │   └── rate_limiter.py  # 速率限制
│   │   │   └── database/
│   │   │       ├── database.py      # 数据库连接 + 迁移
│   │   │       └── migrations/      # 数据库迁移脚本
│   │   ├── tests/                   # 测试套件 (179 passed)
│   │   │   ├── test_auth.py
│   │   │   ├── test_oauth.py
│   │   │   ├── test_bookmarks.py
│   │   │   ├── test_comments.py
│   │   │   ├── test_admin.py
│   │   │   ├── test_password_reset.py
│   │   │   └── ...
│   │   ├── celery_worker.py           # Celery Worker 入口
│   │   ├── tasks/                   # Celery 异步任务
│   │   │   ├── outline_tasks.py   # 大纲生成任务
│   │   │   ├── chapter_tasks.py   # 章节生成任务
│   │   │   └── export_tasks.py    # 文件导出任务
│   │   └── requirements.txt
│   │
│   └── frontend/                    # React + TypeScript 前端
│       ├── src/
│       │   ├── api/
│       │   │   └── client.ts        # API 客户端
│       │   ├── components/
│       │   │   ├── CodeBlock.tsx    # 代码高亮
│       │   │   ├── MathFormula.tsx  # 公式渲染 (KaTeX)
│       │   │   ├── TutorialCard.tsx # 教程卡片
│       │   │   ├── CommentSection.tsx  # 评论区域
│       │   │   ├── ShareModal.tsx   # 分享弹窗
│       │   │   ├── LearningChart.tsx # 学习图表
│       │   │   ├── GenerationProgress.tsx # 进度指示
│       │   │   ├── ClaudeChatSidebar.tsx # 聊天侧栏
│       │   │   ├── AdminGuard.tsx   # 管理员守卫
│       │   │   └── WizardSteps/     # 向导步骤组件
│       │   ├── contexts/
│       │   │   ├── ThemeContext.tsx # 主题切换
│       │   │   └── ToastContext.tsx # Toast 通知
│       │   ├── hooks/
│       │   │   ├── useToast.ts      # Toast hook
│       │   │   └── useWebSocket.ts  # WebSocket hook
│       │   └── pages/
│       │       ├── AuthPage.tsx     # 登录/注册（含 OAuth 按钮）
│       │       ├── AuthCallbackPage.tsx  # OAuth 回调
│       │       ├── TutorialListPage.tsx  # 教程列表
│       │       ├── TutorialDisplayPage.tsx # 教程详情
│       │       ├── ProfilePage.tsx  # 个人中心
│       │       ├── ClaudeConfigPage.tsx # Claude 配置
│       │       ├── AdminLoginPage.tsx  # 管理员登录
│       │       ├── AdminDashboardPage.tsx # 管理仪表盘
│       │       ├── AdminUsersPage.tsx    # 用户管理
│       │       └── AdminCatalogPage.tsx  # 教程审核
│       └── package.json
│
├── nginx/
│   └── nginx.production.conf        # 生产 Nginx 配置
│
├── deploy_compose.py                # Docker Compose 部署脚本
├── deploy_full.py                   # 完整部署脚本（含 MinIO）
├── docker-compose.yml               # 开发环境 Docker Compose
└── README.md                        # 本文档
```

---

## 快速开始

### 开发环境

```bash
# 1. 复制环境变量
cp .env.example .env
# 编辑 .env，填入数据库连接等信息

# 2. 启动基础设施（PostgreSQL + Redis）
docker-compose up -d

# 3. 初始化数据库
cd src/backend && python src/initdb.py

# 4. 启动后端
uvicorn src.api.main:app --reload --port 8000

# 5. 启动前端（另一终端）
cd src/frontend && npm install && npm start
```

访问 `http://localhost:3000`，API 文档在 `http://localhost:8000/docs`。

### 生产部署

```bash
# 一键部署到云服务器
python deploy_compose.py
```

部署脚本会自动：
- 构建前端静态资源
- 上传后端源码和前端构建产物
- 创建 Docker Compose 配置（PostgreSQL + Redis + Nginx）
- 生成安全随机密钥
- 启动所有服务

部署后访问 https://tlcw.yobeeo.com/

---

## 环境配置

| 变量 | 必填 | 说明 |
|------|------|------|
| `SECRET_KEY` | ✅ | JWT 签名密钥 (`openssl rand -hex 32`) |
| `CRYPTO_KEY_HEX` | ✅ | AES-GCM 加密密钥（64 位十六进制） |
| `DATABASE_URL` | ✅ | PostgreSQL 连接字符串 |
| `REDIS_URL` | ✅ | Redis 连接地址 |
| `FRONTEND_URL` | ✅ | 前端 URL（OAuth 回调用） |
| `GOOGLE_CLIENT_ID` | ❌ | Google OAuth 客户端 ID |
| `GOOGLE_CLIENT_SECRET` | ❌ | Google OAuth 客户端密钥 |
| `GITHUB_CLIENT_ID` | ❌ | GitHub OAuth 客户端 ID |
| `GITHUB_CLIENT_SECRET` | ❌ | GitHub OAuth 客户端密钥 |

---

## 安全特性

- **密码安全**: bcrypt 哈希，每用户独立 salt
- **API Key 加密**: AES-GCM 加密存储 Claude API Key
- **JWT 认证**: 无状态 Token，支持 OAuth 集成
- **速率限制**: slowapi + Redis 滑动窗口，防止 API 滥用
- **内容安全扫描**: PII 检测 + 不当语言过滤 + 危险模式检测
- **CORS 配置**: 生产环境限制来源
- **管理员守卫**: `AdminGuard` 组件 + `require_admin` 中间件
- **数据隔离**: 用户仅能访问自己的教程和配置

---

## 测试

```bash
# 运行全部测试
cd src/backend && python -m pytest tests/ -v

# 运行指定测试
python -m pytest tests/test_oauth.py -v
python -m pytest tests/test_pdf_export.py -v
python -m pytest tests/test_bookmarks.py -v
python -m pytest tests/test_comments.py -v
python -m pytest tests/test_admin.py -v

# 前端构建验证
cd src/frontend && npm run build
```

当前测试状态: **179 passed** (全部通过)

---

## 代码规模

| 层级 | 文件数 | 代码行数 |
|------|--------|---------|
| 后端 Python | 45 | ~6,500 |
| 后端测试 | 23 | ~3,200 |
| 前端 TypeScript | 30+ | ~5,200 |
| **总计** | **~100** | **~15,000** |

---

## 路线图

| 里程碑 | 状态 | 日期 |
|--------|------|------|
| MVP 核心功能 | ✅ 完成 | 2026-07 |
| P0 体验优化 (Toast, 教程详情, 搜索排序) | ✅ 完成 | 2026-08-11 |
| P1 社交功能 (书签, 评论, 分享) | ✅ 完成 | 2026-08-12 |
| P2 管理后台 (管理员, 用户管理, 审核, 暗色模式) | ✅ 完成 | 2026-08-12 |
| P3 OAuth + PDF 导出 | ✅ 完成 | 2026-08-13 |
| P0 安全修复 (启动校验, WS 认证, 房间权限) | ✅ 完成 | 2026-08-14 |
| P1 异步任务 + 对象存储 (Celery + MinIO) | ✅ 完成 | 2026-08-14 |
| P2 部署修复 + 响应式适配 (WeasyPrint deps, 移动端布局) | ✅ 完成 | 2026-08-14 |
| P3 PWA 离线支持 (manifest + Service Worker) | ✅ 完成 | 2026-08-14 |

---

## 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

---

*Built with ❤️ by Agnes (Sapiens AI)*
