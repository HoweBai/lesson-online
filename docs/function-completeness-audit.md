# LearnHub 功能完成度核实报告

**分析日期**: 2026-08-14  
**基于版本**: v1.1.0  
**源码分析范围**: `src/backend/`, `src/frontend/`

---

## 核实结论摘要

README 中标注的"已完成功能"大体准确，核心业务模块均可正常工作。但路线图中标注的"进行中"项目存在**基础设施就绪、应用层未接入**的问题，需要区分实际完成度和配置完成度。

---

## 🔴 高优先级（已实现但需优化）

### 1. 教程导出 — PDF 依赖 WeasyPrint 外部库

**位置**: [export_service.py](src/backend/src/services/export_service.py)

- ✅ API 端点 `/tutorials/{id}/export/pdf` 完整实现
- ✅ WeasyPrint 已加入 `requirements.txt` (`weasyprint>=61.0`)
- ⚠️ WeasyPrint 依赖系统级 C 库（pango, cairo），部署时可能缺少
- ⚠️ PDF 渲染为简单 HTML→PDF，不支持 KaTeX 公式复杂排版

**建议**: 在部署文档中明确系统依赖；后续可考虑接入专业 PDF 生成库（如 headless Chrome）。

---

### 2. WebSocket 聊天 — 匿名会话安全性不足

**位置**: [websocket.py](src/backend/src/api/websocket.py)

- ✅ 连接认证、消息持久化、AI 响应完整实现
- ✅ SQLite 持久化聊天历史
- ⚠️ 认证通过查询参数传递 JWT（`?token=xxx`），URL 中暴露 token 有安全风险
- ⚠️ 无房间权限控制——知道 URL 即可加入他人的聊天会话

**建议**: 改用 HTTP Upgrade 头传递认证；添加 session 级权限验证。

---

### 3. 硬编码密钥默认值

**位置**: [websocket.py:305](src/backend/src/api/websocket.py#L305), [main.py](src/backend/src/api/main.py)

```python
# websocket.py:305
master_key_hex = os.getenv("CRYPTO_KEY_HEX", "0" * 64)
```

- ⚠️ 默认全零密钥在开发环境可工作，但生产环境若忘记配置环境变量则使用弱密钥
- 应改为启动时强制校验，缺失则报错退出

**建议**: 在 `startup_event` 中校验所有必填密钥，缺失则拒绝启动。

---

## 🟡 中优先级（框架就绪，未集成到流程）

### 4. Celery 异步任务 — 未接入 API

**位置**: [tasks/generation_tasks.py](src/backend/tasks/generation_tasks.py), [celery_worker.py](src/backend/src/celery_worker.py)

- ✅ Celery worker 和任务文件已创建
- ✅ broker/backend 配置为 Redis
- ❌ `src/api/tutorials.py:148` 注释明确写着 `"Generate a course outline synchronously for MVP."`
- ❌ API 端点完全同步调用 LLM，无任何异步逻辑
- ❌ 长时间生成的任务无法中断或追踪进度（仅通过 TaskLog 轮询）

**实际状态**: 基础设施层就绪，应用层未接入。

**建议实施**:
1. 将 `generate_outline` / `generate_next` 端点改为 `celery_app.send_task()`
2. 前端轮询 `/api/v1/tutorials/outlines/{task_id}` 获取进度
3. 添加任务取消端点

---

### 5. MinIO 对象存储 — 仅配置，未使用

**位置**: [docker-compose.yml:164](docker-compose.yml#L164), 部署脚本

- ✅ `docker-compose.yml` 中有 MinIO 服务定义
- ✅ 环境变量 `MINIO_ENDPOINT`、`MINIO_ACCESS_KEY`、`MINIO_SECRET_KEY` 已配置
- ❌ `src/` 目录中无任何 Python 代码导入或使用 MinIO SDK
- ❌ 导出文件仍直接返回字节流，未上传对象存储
- ❌ 分享链接为本地短码跳转，不通过 CDN 提供

**实际状态**: Docker 编排层就绪，应用层未接入。

**建议实施**:
1. 安装 `boto3` 或 `minio` Python SDK
2. 导出时将 Markdown/PDF 上传至 MinIO bucket
3. 分享链接改为指向 MinIO 预签名 URL

---

## 🟢 低优先级（部分完成或规划中）

### 6. 移动端响应式 — 基础有，管理端弱

**位置**: 前端各页面

| 页面 | 响应式状态 | 说明 |
|------|-----------|------|
| TutorialListPage.tsx | 🟢 良好 | `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 自适应 |
| TutorialDisplayPage.tsx | 🟡 一般 | 侧边栏在移动端无折叠逻辑 |
| AdminDashboardPage.tsx | 🔴 弱 | 统计卡片 `grid-cols-2 md:grid-cols-3 lg:grid-cols-6`，但图表在小屏溢出 |
| AdminUsersPage.tsx | 🟡 一般 | 表格在移动端横向滚动，无行式卡片布局 |

**建议**: 为管理后台添加移动端专用布局（卡片替代表格）。

---

### 7. PWA 离线支持 — 零实现

**当前状态**: 
- `public/` 目录仅含 `index.html`
- 无 `manifest.json`
- 无 Service Worker
- `package.json` 无 PWA 依赖

这是纯粹的规划阶段功能，与 Celery/MinIO 的"框架就绪"不同，PWA 完全没有代码基础。

---

## 📋 问题汇总（按影响排序）

| 优先级 | 问题 | 位置 | 风险等级 |
|--------|------|------|----------|
| P0 | 硬编码密钥默认值 | websocket.py:305, main.py | 中 |
| P0 | WebSocket 匿名会话无权限控制 | websocket.py | 中 |
| P1 | Celery 未接入，大纲生成同步阻塞 | tutorials.py | 低（功能可用） |
| P1 | MinIO 未接入，导出文件不入库 | 无代码引用 | 低 |
| P2 | PDF 依赖 WeasyPrint 外部库 | requirements.txt | 部署风险 |
| P2 | 管理后台移动端适配不足 | Admin*.tsx | 体验 |
| P3 | PWA 离线支持为零 | 无代码 | 长期规划 |

---

## 对比 README 路线图

| README 标注 | 实际状态 | 偏差 |
|------------|----------|------|
| Celery 异步任务队列 🔄 进行中 | 框架就绪，API 未接入 | 夸大完成度 |
| MinIO 对象存储集成 🔄 进行中 | 仅 Docker 配置，无代码引用 | 夸大完成度 |
| 移动端响应式完善 ⏳ 计划中 | 基础响应式有，管理端弱 | 略低于预期 |
| PWA 离线支持 ⏳ 计划中 | 零实现 | 准确 |

---

*本报告基于对 `src/backend/` 和 `src/frontend/` 源码的直接核实，未参考功能差距分析文档。*
