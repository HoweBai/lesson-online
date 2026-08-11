# Online Learning Platform - 功能完善规格说明书

**版本**: v1.0  
**日期**: 2026-08-11  
**状态**: 待审核  
**作者**: Agnes (Sapiens AI)

---

## 1. 项目概述

### 1.1 当前状态
- **技术栈**: FastAPI + React + TypeScript + SQLite
- **部署方式**: Docker Compose (nginx + backend)
- **服务器**: tlcw.yobeeo.com
- **用户数**: 7 (测试用户)
- **教程数**: 0

### 1.2 已完成功能
| 模块 | 功能 | 状态 |
|------|------|------|
| 认证 | 注册/登录/登出、JWT Token | ✅ |
| 教程 | 创建向导(4步)、大纲生成、章节生成 | ✅ |
| 用户档案 | 学习偏好、进度追踪、知识推断 | ✅ |
| Claude配置 | API Key加密存储 | ✅ |
| 导出 | Markdown/JSON/大纲导出 | ✅ |
| 备份 | 数据库备份/恢复 | ✅ |
| 监控 | 系统监控、告警服务 | ✅ |
| WebSocket | 实时聊天功能 | ✅ |
| 目录 | 公开教程浏览、点赞、举报 | ✅ |

### 1.3 已发现问题
1. React Router 缺少 BrowserRouter 包装（已通过 localStorage 补丁解决）
2. 前端使用 `alert()` 进行错误提示（用户体验差）
3. 教程详情页路由已存在但功能需完善
4. 缺少后台管理面板（前端无 admin 路由）
5. 搜索和排序功能需优化
6. 缺少暗色模式
7. 缺少学习统计图表（ProfilePage 有基础但需增强）
8. 缺少收藏/书签功能
9. 缺少评论功能
10. 缺少 API 限流

---

## 2. 完善方向与优先级

### 2.1 P0 - 核心体验优化（1-2周）

#### 2.1.1 错误提示系统
**现状**: 1处 `alert()` 调用  
**目标**: 统一的 Toast 通知系统

**技术方案**:
- 使用 `react-hot-toast` 库
- 创建 Toast 上下文 Provider
- 替换所有 alert() 调用

**API 变更**: 无

**数据库变更**: 无

**文件变更**:
```
frontend/src/components/ToastProvider.tsx (新建)
frontend/src/hooks/useToast.ts (新建)
frontend/src/main.tsx (修改 - 添加 Provider)
frontend/src/pages/TutorialListPage.tsx (修改)
frontend/src/pages/TutorialDisplayPage.tsx (修改)
frontend/src/components/CourseWizard.tsx (修改)
```

---

#### 2.1.2 教程详情页完善
**现状**: TutorialDisplayPage 路由已存在（/tutorial/:id），但功能需完善  
**目标**: 完整的章节浏览、进度追踪、导出功能

**功能清单**:
1. 章节导航侧边栏
2. 进度条显示
3. 章节生成状态
4. 导出按钮（Markdown/JSON）
5. 收藏按钮
6. 分享按钮

**API 调用**:
```typescript
// 已有 API
GET  /api/v1/tutorials/{id}           // 获取教程详情
GET  /api/v1/tutorials/{id}/chapters/{n}/status  // 章节状态
POST /api/v1/tutorials/{id}/generate-next  // 生成下一章
GET  /api/v1/tutorials/{id}/export/markdown  // 导出 Markdown
GET  /api/v1/tutorials/{id}/export/json  // 导出 JSON
```

**数据库变更**: 无

**文件变更**:
```
frontend/src/pages/TutorialDisplayPage.tsx (重写)
frontend/src/components/ChapterNav.tsx (新建)
frontend/src/components/ExportMenu.tsx (新建)
```

---

#### 2.1.3 搜索与排序优化
**现状**: 搜索存在但功能简单，排序未实现  
**目标**: 全文搜索 + 多维度排序

**功能清单**:
1. 搜索框优化（防抖、实时搜索）
2. 排序选项：最新、最热、最多章节
3. 分类筛选（按标签）
4. 搜索结果高亮

**API 变更**:
```typescript
// 现有 API 已支持
GET /api/v1/catalog?search=keyword&sort=views&order=desc&page=1&limit=20
```

**数据库变更**: 无

**文件变更**:
```
frontend/src/pages/TutorialListPage.tsx (修改)
frontend/src/components/SearchBar.tsx (新建)
```

---

### 2.2 P1 - 社交与学习功能（2-3周）

#### 2.2.1 收藏/书签功能
**目标**: 用户可收藏教程，在个人中心查看

**数据库变更**:
```sql
CREATE TABLE user_bookmarks (
    id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    tutorial_id VARCHAR(36) NOT NULL,
    created_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(tutorial_id) REFERENCES tutorials(id),
    UNIQUE(user_id, tutorial_id)
);
```

**API 变更**:
```typescript
POST /api/v1/tutorials/{id}/bookmark      // 收藏
DELETE /api/v1/tutorials/{id}/bookmark    // 取消收藏
GET /api/v1/users/profile/bookmarks      // 我的收藏
```

**文件变更**:
```
src/backend/src/api/catalog.py (修改)
src/backend/src/models/bookmark.py (新建)
frontend/src/api/client.ts (修改)
frontend/src/pages/TutorialDisplayPage.tsx (修改)
frontend/src/pages/ProfilePage.tsx (修改)
```

---

#### 2.2.2 学习统计图表
**目标**: 可视化学习进度、时长、成就

**功能清单**:
1. 学习时长统计（周/月）
2. 章节完成进度图
3. 学习趋势折线图
4. 成就徽章展示

**技术方案**:
- 使用 `recharts` 库
- 创建统计图表组件

**数据库变更**: 无（利用现有 task_logs 和 chapters 表）

**文件变更**:
```
frontend/src/components/LearningChart.tsx (新建)
frontend/src/pages/ProfilePage.tsx (修改)
frontend/src/api/client.ts (修改)
```

---

#### 2.2.3 评论功能
**目标**: 用户可在教程下发表评论

**数据库变更**:
```sql
CREATE TABLE tutorial_comments (
    id VARCHAR(36) NOT NULL,
    tutorial_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    content TEXT NOT NULL,
    parent_id VARCHAR(36),  -- 支持回复
    like_count INTEGER DEFAULT 0,
    created_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(tutorial_id) REFERENCES tutorials(id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(parent_id) REFERENCES tutorial_comments(id)
);
```

**API 变更**:
```typescript
GET /api/v1/tutorials/{id}/comments      // 获取评论
POST /api/v1/tutorials/{id}/comments    // 发表评论
POST /api/v1/comments/{id}/like         // 点赞评论
DELETE /api/v1/comments/{id}            // 删除评论
```

**文件变更**:
```
src/backend/src/api/comments.py (新建)
src/backend/src/models/comment.py (新建)
frontend/src/components/CommentSection.tsx (新建)
frontend/src/pages/TutorialDisplayPage.tsx (修改)
```

---

#### 2.2.4 教程分享功能
**目标**: 生成分享链接，支持社交媒体分享

**功能清单**:
1. 生成短链接
2. 分享预览卡片（标题、封面、描述）
3. 社交媒体按钮（微信、微博、Twitter）

**技术方案**:
- 使用短链接服务或自定义短链算法
- Open Graph 标签自动生成

**数据库变更**:
```sql
ALTER TABLE tutorials ADD COLUMN share_code VARCHAR(20) UNIQUE;
```

**文件变更**:
```
src/backend/src/api/tutorials.py (修改)
frontend/src/components/ShareModal.tsx (新建)
frontend/src/pages/TutorialDisplayPage.tsx (修改)
```

---

### 2.3 P2 - 后台管理功能（2-3周）

#### 2.3.1 管理员登录
**目标**: 管理员专用登录入口

**技术方案**:
- 添加 `is_admin` 字段到 users 表
- 创建管理员认证中间件
- 独立的管理员登录页面

**数据库变更**:
```sql
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
```

**API 变更**:
```typescript
POST /api/v1/admin/login    // 管理员登录
GET /api/v1/admin/me        // 获取管理员信息
```

**文件变更**:
```
src/backend/src/api/admin.py (新建或修改)
frontend/src/pages/AdminLoginPage.tsx (新建)
frontend/src/components/AdminGuard.tsx (新建)
```

---

#### 2.3.2 用户管理
**目标**: 管理用户账号、查看用户详情

**功能清单**:
1. 用户列表（分页、搜索）
2. 用户详情（教程、进度、配置）
3. 用户状态切换（启用/禁用）
4. 用户删除（级联处理）

**API 变更**:
```typescript
GET /api/v1/admin/users           // 用户列表
GET /api/v1/admin/users/{id}      // 用户详情
PUT /api/v1/admin/users/{id}/status  // 更新状态
DELETE /api/v1/admin/users/{id}   // 删除用户
```

**文件变更**:
```
src/backend/src/api/admin.py (修改)
frontend/src/pages/AdminUsersPage.tsx (新建)
frontend/src/components/UserTable.tsx (新建)
```

---

#### 2.3.3 教程审核
**目标**: 审核公开教程，管理内容质量

**功能清单**:
1. 待审核教程列表
2. 教程详情查看
3. 通过/拒绝审核
4. 审核意见填写

**API 变更**:
```typescript
GET /api/v1/admin/catalog/pending    // 待审核列表
PUT /api/v1/admin/catalog/{id}/review  // 审核操作
```

**文件变更**:
```
src/backend/src/api/admin.py (修改)
frontend/src/pages/AdminCatalogPage.tsx (新建)
frontend/src/components/CatalogReview.tsx (新建)
```

---

#### 2.3.4 数据统计面板
**目标**: 查看平台运营数据

**功能清单**:
1. 用户增长趋势图
2. 教程创建统计
3. 活跃度分析
4. 系统资源监控

**API 变更**:
```typescript
GET /api/v1/admin/stats/overview    // 概览统计
GET /api/v1/admin/stats/users       // 用户统计
GET /api/v1/admin/stats/tutorials   // 教程统计
```

**文件变更**:
```
src/backend/src/api/admin.py (修改)
frontend/src/pages/AdminDashboardPage.tsx (新建)
frontend/src/components/StatsCharts.tsx (新建)
```

---

### 2.4 P3 - 体验增强（1-2周）

#### 2.4.1 暗色模式
**目标**: 支持明暗主题切换

**技术方案**:
- 使用 `next-themes` 或自定义 Theme Context
- Tailwind CSS dark mode 配置
- 本地存储主题偏好

**文件变更**:
```
frontend/src/context/ThemeContext.tsx (新建)
frontend/src/main.tsx (修改)
tailwind.config.js (修改)
所有页面组件 (添加 dark: 类)
```

---

#### 2.4.2 响应式优化
**目标**: 优化移动端体验

**功能清单**:
1. 移动端导航菜单
2. 触摸友好的交互
3. 自适应布局
4. 离线提示

**文件变更**:
```
frontend/src/components/MobileNav.tsx (新建)
frontend/src/pages/TutorialListPage.tsx (修改)
frontend/src/pages/TutorialDisplayPage.tsx (修改)
```

---

#### 2.4.3 性能优化
**目标**: 提升加载速度和响应性能

**功能清单**:
1. 虚拟列表（长列表优化）
2. 图片懒加载
3. 代码分割
4. 请求缓存

**技术方案**:
- `react-virtual` 用于长列表
- `react-lazyload` 用于图片
- React.lazy + Suspense 用于代码分割
- SWR 或 React Query 用于请求缓存

**文件变更**:
```
frontend/src/pages/TutorialListPage.tsx (修改)
frontend/src/api/client.ts (修改 - 添加缓存)
```

---

#### 2.4.4 PWA 支持
**目标**: 支持离线访问和安装

**功能清单**:
1. Service Worker
2. Web App Manifest
3. 离线页面
4. 安装提示

**文件变更**:
```
frontend/public/manifest.json (新建)
frontend/src/service-worker.ts (新建)
frontend/index.html (修改)
```

---

## 3. 技术实现方案

### 3.1 前端架构

```
frontend/src/
├── api/
│   └── client.ts              # API 客户端（已存在，需扩展）
├── components/
│   ├── ToastProvider.tsx      # 通知系统
│   ├── ThemeProvider.tsx      # 主题切换
│   ├── SearchBar.tsx          # 搜索组件
│   ├── ChapterNav.tsx         # 章节导航
│   ├── ExportMenu.tsx         # 导出菜单
│   ├── CommentSection.tsx     # 评论区域
│   ├── ShareModal.tsx         # 分享弹窗
│   ├── LearningChart.tsx      # 学习图表
│   ├── UserTable.tsx          # 用户列表
│   ├── StatsCharts.tsx        # 统计图表
│   └── AdminGuard.tsx         # 管理员守卫
├── pages/
│   ├── AdminLoginPage.tsx     # 管理员登录
│   ├── AdminDashboardPage.tsx # 管理面板
│   ├── AdminUsersPage.tsx     # 用户管理
│   ├── AdminCatalogPage.tsx   # 教程审核
│   └── TutorialDisplayPage.tsx # 教程详情（重写）
├── context/
│   └── ThemeContext.tsx       # 主题上下文
├── hooks/
│   └── useToast.ts            # Toast Hook
│   └── useBookmark.ts         # 收藏 Hook
│   └── useComments.ts         # 评论 Hook
└── types/
    └── index.ts               # 类型定义
```

### 3.2 后端架构

```
src/backend/src/
├── api/
│   ├── admin.py               # 管理员 API
│   ├── comments.py            # 评论 API
│   ├── catalog.py             # 目录 API（修改）
│   ├── tutorials.py           # 教程 API（修改）
│   └── profile.py             # 用户档案 API（修改）
├── models/
│   ├── bookmark.py            # 收藏模型
│   ├── comment.py             # 评论模型
│   └── admin.py               # 管理员模型
└── services/
    └── admin_service.py       # 管理员服务
```

### 3.3 数据库变更

```sql
-- 1. 用户表添加管理员字段
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;

-- 2. 收藏表
CREATE TABLE user_bookmarks (
    id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    tutorial_id VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE,
    UNIQUE(user_id, tutorial_id)
);

-- 3. 评论表
CREATE TABLE tutorial_comments (
    id VARCHAR(36) NOT NULL,
    tutorial_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    content TEXT NOT NULL,
    parent_id VARCHAR(36),
    like_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY(tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(parent_id) REFERENCES tutorial_comments(id) ON DELETE CASCADE
);

-- 4. 教程表添加分享码
ALTER TABLE tutorials ADD COLUMN share_code VARCHAR(20) UNIQUE;
```

---

## 4. API 设计详情

### 4.1 收藏 API

```typescript
// 收藏教程
POST /api/v1/tutorials/{id}/bookmark
Response: { success: true, message: "Tutorial bookmarked" }

// 取消收藏
DELETE /api/v1/tutorials/{id}/bookmark
Response: { success: true }

// 获取我的收藏
GET /api/v1/users/profile/bookmarks?page=1&limit=20
Response: {
  data: [...],
  total: 10,
  page: 1,
  pages: 1
}
```

### 4.2 评论 API

```typescript
// 获取评论
GET /api/v1/tutorials/{id}/comments?parent_id=null&page=1&limit=20
Response: {
  data: [
    {
      id: "...",
      user: { id, username, avatar },
      content: "...",
      likes: 5,
      replies: [...],
      created_at: "..."
    }
  ],
  total: 10
}

// 发表评论
POST /api/v1/tutorials/{id}/comments
Body: { content: "...", parent_id: null }
Response: { id, ... }

// 点赞评论
POST /api/v1/comments/{id}/like
Response: { like_count: 6 }

// 删除评论
DELETE /api/v1/comments/{id}
Response: { success: true }
```

### 4.3 管理员 API

```typescript
// 管理员登录
POST /api/v1/admin/login
Body: { email: "...", password: "..." }
Response: { token, user: { id, username, email, is_admin } }

// 获取管理员信息
GET /api/v1/admin/me
Response: { id, username, email, created_at }

// 用户列表
GET /api/v1/admin/users?page=1&limit=20&search=keyword
Response: { data: [...], total: 100, page: 1, pages: 5 }

// 用户详情
GET /api/v1/admin/users/{id}
Response: { id, username, email, created_at, tutorial_count, is_active }

// 更新用户状态
PUT /api/v1/admin/users/{id}/status
Body: { is_active: true/false }
Response: { success: true }

// 删除用户
DELETE /api/v1/admin/users/{id}
Response: { success: true }

// 待审核教程
GET /api/v1/admin/catalog/pending?page=1&limit=20
Response: { data: [...], total: 5 }

// 审核教程
PUT /api/v1/admin/catalog/{id}/review
Body: { status: "approved"|"rejected", comment: "..." }
Response: { success: true }

// 统计数据
GET /api/v1/admin/stats/overview
Response: {
  total_users: 100,
  active_users: 50,
  total_tutorials: 500,
  public_tutorials: 300,
  today_registrations: 5,
  today_tutorials: 10
}

GET /api/v1/admin/stats/users?period=30d
Response: {
  chart_data: [
    { date: "2026-08-01", count: 10 },
    ...
  ]
}
```

---

## 5. 实施计划

### 5.1 第一阶段：核心体验优化（1-2周）

**Week 1**:
- [ ] 实现 Toast 通知系统
- [ ] 替换所有 alert() 调用
- [ ] 完善 TutorialDisplayPage
- [ ] 优化搜索和排序功能

**Week 2**:
- [ ] 实现收藏功能（前端 + 后端 + 数据库）
- [ ] 实现学习统计图表
- [ ] 实现评论功能
- [ ] 实现分享功能

### 5.2 第二阶段：后台管理功能（2-3周）

**Week 3-4**:
- [ ] 实现管理员登录
- [ ] 实现用户管理页面
- [ ] 实现教程审核页面
- [ ] 实现数据统计面板

### 5.3 第三阶段：体验增强（1-2周）

**Week 5-6**:
- [ ] 实现暗色模式
- [ ] 优化响应式布局
- [ ] 性能优化（虚拟列表、懒加载）
- [ ] PWA 支持

---

## 6. 风险与注意事项

### 6.1 技术风险
1. **React Router 兼容性问题**: 当前缺少 BrowserRouter，需确保补丁稳定
2. **SQLite 并发限制**: 高并发时可能遇到问题，建议监控
3. **WebSocket 连接稳定性**: 需实现重连机制

### 6.2 安全风险
1. **管理员权限**: 需实现严格的权限验证
2. **评论审核**: 需实现敏感词过滤
3. **API 限流**: 需实现请求频率限制

### 6.3 数据风险
1. **数据库迁移**: 添加新表前需备份
2. **级联删除**: 需测试删除用户/教程的级联效果
3. **数据一致性**: 需确保外键约束正确

---

## 7. 测试计划

### 7.1 单元测试
- [ ] API 端点测试
- [ ] 服务层逻辑测试
- [ ] 数据库模型测试

### 7.2 集成测试
- [ ] 前后端联调测试
- [ ] WebSocket 连接测试
- [ ] 文件导出测试

### 7.3 用户验收测试
- [ ] 收藏功能流程测试
- [ ] 评论功能流程测试
- [ ] 管理后台功能测试

---

## 8. 附录

### 8.1 依赖清单

**前端新增依赖**:
```json
{
  "react-hot-toast": "^2.4.0",
  "recharts": "^2.10.0",
  "react-virtual": "^3.0.0",
  "react-lazyload": "^3.2.0"
}
```

**后端新增依赖**:
```
# 无新增依赖，使用现有 redis 包
```

### 8.2 环境变量

```bash
# 新增环境变量
SECRET_KEY=your-production-secret-key
ADMIN_EMAIL=admin@tlcw.com
ADMIN_PASSWORD=your-admin-password
```

### 8.3 数据库迁移脚本

```python
# src/backend/src/database/migrations/001_add_features.py
import sqlite3

def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 添加管理员字段
    cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")

    # 2. 创建收藏表
    cursor.execute("""
        CREATE TABLE user_bookmarks (
            id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            tutorial_id VARCHAR(36) NOT NULL,
            created_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(tutorial_id) REFERENCES tutorials(id),
            UNIQUE(user_id, tutorial_id)
        )
    """)

    # 3. 创建评论表
    cursor.execute("""
        CREATE TABLE tutorial_comments (
            id VARCHAR(36) NOT NULL,
            tutorial_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            content TEXT NOT NULL,
            parent_id VARCHAR(36),
            like_count INTEGER DEFAULT 0,
            created_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(tutorial_id) REFERENCES tutorials(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(parent_id) REFERENCES tutorial_comments(id)
        )
    """)

    # 4. 添加分享码字段
    cursor.execute("ALTER TABLE tutorials ADD COLUMN share_code VARCHAR(20) UNIQUE")

    conn.commit()
    conn.close()
```

---

**文档结束**
