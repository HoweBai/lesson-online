# P1 异步任务与对象存储 — Design Spec

**Date**: 2026-08-14  
**Scope**: Celery 异步任务队列 + MinIO 对象存储集成

---

## 概述

两个 P1 功能：
1. **Celery 异步任务** — 大纲生成、章节生成改为异步，支持进度轮询和任务取消
2. **MinIO 对象存储** — 导出文件上传对象存储，返回可访问链接

## 第一节：Celery 异步任务架构

### 架构图

```
FastAPI (backend) ──publish──▶ Redis (broker) ──consume──▶ Celery Worker
       │                                               │
       │◀── poll status ───────────────────────────────┤
       │                                               │
       │◀── result (TaskLog) ──────────────────────────┤
```

### 任务类型（3 种）

| 任务 | 原端点 | 新端点行为 |
|------|--------|-----------|
| `generate_outline` | `POST /generate-outline` | 提交后立即返回 task_id，后台执行 |
| `generate_chapter` | `POST /{id}/generate-next` | 提交后立即返回 task_id，后台执行 |
| `export_file` | `GET /{id}/export/pdf` | 新建异步端点，返回 task_id |

### 轮询接口（不变）

- `GET /outlines/{task_id}` — 大纲进度（已有）
- `GET /{tutorial_id}/chapters/{n}/status` — 章节进度（已有）
- `GET /tasks/{task_id}/export/{format}` — 导出进度（新建）

### 新增端点

- `DELETE /tasks/{task_id}` — 取消任务
- `GET /tasks/{task_id}/status` — 通用任务状态

### Worker 实现

- 每个任务中实时更新 `TaskLog.progress`（0→50→100）
- 任务循环中检查 `task_log.status == "cancelled"` 以支持取消
- 错误时标记 `status="failed"` 并记录 `error_message`

## 第二节：MinIO 对象存储

### 存储策略

| Bucket | 路径 | 用途 |
|--------|------|------|
| `exports` | `exports/{user_id}/{task_id}.{ext}` | 个人导出文件 |
| `public` | `public/{tutorial_id}/{task_id}.{ext}` | 公开教程导出 |

### 文件生命周期

- 上传后通过 MinIO 预签名 URL 提供下载
- 预签名 URL 有效期 30 天
- 前端收到 URL 后触发浏览器下载

### API 变化

导出端点返回格式从字节流改为：
```json
{
  "download_url": "https://cdn.example.com/exports/user/uuid.pdf",
  "presigned_url": "https://minio:9000/exports/user/uuid.pdf?X-Amz-...",
  "task_id": "xxx",
  "expires_in": 2592000
}
```

## 第三节：变更范围

| 文件 | 操作 |
|------|------|
| `requirements.txt` | 添加 celery, minio |
| `docker-compose.yml` | 添加 worker 服务 |
| `src/backend/celery_worker.py` | 新建 — Worker 入口 |
| `src/backend/tasks/__init__.py` | 新建 |
| `src/backend/tasks/outline_tasks.py` | 新建 — 大纲任务 |
| `src/backend/tasks/chapter_tasks.py` | 新建 — 章节任务 |
| `src/backend/tasks/export_tasks.py` | 新建 — 导出任务 |
| `src/backend/src/services/minio_service.py` | 新建 — MinIO 客户端 |
| `src/backend/src/api/tutorials.py` | 修改 — 改为异步提交 |
| `src/backend/src/api/export.py` | 修改 — 异步导出端点 |
| `src/backend/src/api/main.py` | 修改 — 添加 task cancel 路由 |

**数据库迁移：** 无需 — 复用已有 TaskLog 表。
**前端变更：** 导出按钮适配新 API 响应格式（可选，不在本次范围）。
