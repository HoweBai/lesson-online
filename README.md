# LearnHub — AI 驱动的个人化教程学习平台

一个生产级在线学习平台，核心功能是通过 **Claude API** 为用户生成循序渐进、个性化的计算机科学知识教程。支持游客浏览公开教程，注册用户可通过收集个人信息并使用 AI 生成完整课程大纲和逐章详细讲解（含数学公式推导、代码示例和练习题）。

**版本**: v1.2.0  
**最后更新**: 2026-08-18  
**在线演示**: https://tlcw.yobeeo.com/

---

## 技术栈

| 层 | 技术 |
|---|---|
| **后端** | FastAPI + SQLAlchemy (async) + PostgreSQL + Redis |
| **前端** | React 18 + TypeScript + Tailwind CSS + React Router v6 |
| **AI 集成** | Claude API / OpenAI API (通过统一 LLM Adapter) |
| **实时通信** | WebSocket (Claude Code 聊天室) |
| **认证** | JWT + OAuth2 (Google / GitHub) |
| **部署** | Docker Compose + Nginx |
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

### 系统功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 数据库备份/恢复 | ✅ | SQL dump 备份与还原 |
| 系统监控 | ✅ | 健康检查、指标收集、资源监控 |
| 告警服务 | ✅ | 异常检测与通知 |
| 审计日志 | ✅ | 用户操作记录 |
| API Key 加密存储 | ✅ | AES-GCM 加密 Claude API Key |
| Celery 异步任务队列 | ✅ | 大纲/章节生成、文件导出异步化 |
| MinIO 对象存储 | ✅ | 导出文件上传对象存储，预签名下载链接 |

---

## 快速开始

### 云服务器一键部署（推荐新手）

```bash
# 1. 安装依赖
pip install -r scripts/requirements.txt

# 2. 一键部署（SSH 私钥方式，推荐）
python scripts/deploy.py --host <服务器IP> --user root --domain <你的域名> --key ~/.ssh/id_rsa

# 或使用密码方式
python scripts/deploy.py --host <服务器IP> --user root --domain <你的域名> --password 'SSH密码'

# 跳过 SSL 证书申请（使用已有证书）
python scripts/deploy.py --host <服务器IP> --user root --domain <你的域名> --key ~/.ssh/id_rsa --no-certbot
```

脚本自动完成：
- 检查/安装 Docker 和 Docker Compose（中国大陆自动配置镜像加速）
- 验证域名 DNS 解析
- 生成安全随机密钥（SECRET_KEY, POSTGRES_PASSWORD 等）
- 下载并上传项目代码到服务器
- 保留现有 `.env` 文件（避免覆盖密钥）
- 配置 Nginx 反向代理
- 申请 Let's Encrypt SSL 证书
- 构建并启动所有 Docker 容器

部署完成后访问：
- 主站: `https://你的域名/`
- API 文档: `https://你的域名/docs`
- 健康检查: `https://你的域名/health`
- 初始管理员: `admin@ollp.local` / `ollp_admin_2024`

### 卸载

```bash
# 完全卸载（删除所有数据）
python scripts/deploy.py --host <服务器IP> --user root --uninstall

# 保留数据库和对象存储数据卸载
python scripts/deploy.py --host <服务器IP> --user root --uninstall --keep-data

# 或使用独立脚本
python scripts/uninstall.py --host <服务器IP> --user root --key ~/.ssh/id_rsa
```

---

## 环境配置

项目根目录下的 `.env.example` 包含所有必需的环境变量模板。部署脚本会自动生成随机密钥，无需手动配置。

| 变量 | 必填 | 说明 |
|------|------|------|
| `SECRET_KEY` | ✅ | JWT 签名密钥 (`openssl rand -hex 32`) |
| `CRYPTO_KEY_HEX` | ✅ | AES-GCM 加密密钥（64 位十六进制） |
| `POSTGRES_PASSWORD` | ✅ | PostgreSQL 数据库密码 |
| `MINIO_ACCESS_KEY` | ❌ | MinIO 对象存储访问密钥 |
| `MINIO_SECRET_KEY` | ❌ | MinIO 对象存储密钥 |
| `GOOGLE_CLIENT_ID` | ❌ | Google OAuth 客户端 ID |
| `GOOGLE_CLIENT_SECRET` | ❌ | Google OAuth 客户端密钥 |
| `GITHUB_CLIENT_ID` | ❌ | GitHub OAuth 客户端 ID |
| `GITHUB_CLIENT_SECRET` | ❌ | GitHub OAuth 客户端密钥 |

> **注意**: 首次使用时请执行 `cp .env.example .env` 并修改必要配置。

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 部署后 `502 Bad Gateway` | `.env` 文件丢失 | 重新运行 `deploy.py` 或手动创建 `.env` |
| 登录失败 `invalid credentials` | 数据库密码不匹配 | 检查 `.env` 中 `POSTGRES_PASSWORD` |
| 生成教程失败 | Claude API Key 未配置 | 在「Claude 配置」页面填入有效 API Key |
| Docker 拉取镜像超时 | 中国大陆网络限制 | 脚本已自动配置腾讯云镜像加速 |
| 无法删除用户 | 外键约束冲突 | 已修复，用户可正常删除 |

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

## 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

---

*Built with ❤️ by Agnes (Sapiens AI)*
