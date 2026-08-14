# P2 功能实施计划 — WeasyPrint 部署修复 + 管理后台响应式优化

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Dockerfile.backend 缺少 WeasyPrint 系统依赖的问题，并为 3 个管理页面添加移动端响应式适配。

**Architecture:** Dockerfile 只需补全 apt 包依赖；前端响应式通过 Tailwind CSS 断点控制双视图切换（AdminUsersPage）和布局微调（AdminDashboardPage、AdminCatalogPage）。

**Tech Stack:** Docker, React 18, TypeScript, Tailwind CSS, WeasyPrint

## Global Constraints

- Dockerfile.worker 已有 pango/cairo 依赖作为参考基准
- Tailwind CSS v3.3.3 已配置，使用标准断点：sm=640px, md=768px, lg=1024px
- 不新增任何 npm 依赖或 Python 依赖
- 保持现有深色模式支持
- 所有修改仅影响指定文件，不改动其他模块

---

### Task 1: Dockerfile.backend 补全 WeasyPrint 系统依赖

**Files:**
- Modify: `Dockerfile.backend`

**Interfaces:**
- Consumes: none
- Produces: 可构建 WeasyPrint PDF 的后端镜像

- [ ] **Step 1: 查看当前 Dockerfile.backend 的依赖列表**

```bash
grep -n "apt-get install" Dockerfile.backend -A5
```

- [ ] **Step 2: 编辑 Dockerfile.backend，在 gcc/libpq-dev/curl 之后添加 WeasyPrint 系统依赖**

将以下内容添加到 `apt-get install -y` 块的末尾（在 `curl \` 之后、`&& rm -rf` 之前）：

```dockerfile
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
```

完整修改后的 RUN 块应为：

```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 3: 验证 Dockerfile 语法**

```bash
docker build -f Dockerfile.backend --check . 2>&1 || echo "build check done"
```

- [ ] **Step 4: Commit**

```bash
git add Dockerfile.backend
git commit -m "fix: add WeasyPrint system deps to Dockerfile.backend"
```

---

### Task 2: AdminDashboardPage 响应式优化

**Files:**
- Modify: `src/frontend/src/pages/AdminDashboardPage.tsx`

**Interfaces:**
- Consumes: 现有 api 客户端 `api.adminGetStatsOverview()`, `api.adminGetUserStats()`, `api.adminGetTutorialStats()`
- Produces: 移动端友好的仪表盘布局

- [ ] **Step 1: 打开 AdminDashboardPage.tsx 找到统计卡片 grid**

定位第 77 行附近的 `<div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">`

- [ ] **Step 2: 修改统计卡片栅格断点**

将 `md:grid-cols-3` 改为 `sm:grid-cols-3`：

```tsx
// 改前
<div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">

// 改后
<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
```

- [ ] **Step 3: 修改图表高度**

找到两个 `<ResponsiveContainer` 的 `height={250}`，改为 `height={200}`。

```tsx
// 改前（有两个地方）
<ResponsiveContainer width="100%" height={250}>

// 改后
<ResponsiveContainer width="100%" height={200}>
```

- [ ] **Step 4: 为图表容器添加 overflow-x-auto**

给两个图表卡片 div 添加 `overflow-x-auto` 类：

```tsx
// User Growth 图表卡片
<div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-soft border border-gray-100 dark:border-gray-700 overflow-x-auto">

// Tutorial Stats 图表卡片（同样添加）
<div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-soft border border-gray-100 dark:border-gray-700 overflow-x-auto">
```

- [ ] **Step 5: 前端构建验证**

```bash
cd src/frontend && npm run build 2>&1 | tail -20
```

确认无 TypeScript 错误。

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/pages/AdminDashboardPage.tsx
git commit -m "feat: improve AdminDashboardPage responsive layout"
```

---

### Task 3: AdminUsersPage 移动端卡片布局

**Files:**
- Modify: `src/frontend/src/pages/AdminUsersPage.tsx`

**Interfaces:**
- Consumes: 现有 `User` 类型、`api.adminListUsers()`、`api.adminUpdateUserStatus()`、`api.adminDeleteUser()`
- Produces: 桌面端表格 + 移动端卡片的视图切换

- [ ] **Step 1: 分析现有 AdminUsersPage.tsx 结构**

关键区域：
- 第 100-153 行：`<table>` 元素包含所有用户数据
- 第 155-176 行：分页控件
- 第 61-76 行：页面头部

- [ ] **Step 2: 隐藏表格在移动端**

找到 `<table className="w-full">` ，添加响应式类：

```tsx
// 改前
<table className="w-full">

// 改后
<table className="w-full hidden md:table">
```

同时找到包裹表格的父 div `<div className="bg-white ... overflow-hidden">` ，也添加 `hidden md:block`：

```tsx
// 改前
<div className="bg-white dark:bg-gray-800 rounded-2xl shadow-soft border border-gray-100 dark:border-gray-700 overflow-hidden">

// 改后
<div className="bg-white dark:bg-gray-800 rounded-2xl shadow-soft border border-gray-100 dark:border-gray-700 overflow-hidden hidden md:block">
```

- [ ] **Step 3: 在表格之后添加移动端卡片视图**

在 `</table>` 和 `{/* Pagination */}` 之间插入以下卡片列表代码：

```tsx
{/* Mobile card view */}
<div className="md:hidden space-y-3">
  {users.map((user) => (
    <div key={user.id} className="bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-soft border border-gray-100 dark:border-gray-700">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white text-sm font-bold">
          {user.username[0].toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 dark:text-white truncate">{user.username}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400 truncate">{user.email}</div>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
          user.is_admin
            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
        }`}>
          {user.is_admin ? 'Admin' : 'User'}
        </span>
      </div>
      <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700">
        <span className="text-xs text-gray-400 dark:text-gray-500">
          Joined {new Date(user.created_at).toLocaleDateString()}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => handleToggleAdmin(user)}
            className="w-8 h-8 flex items-center justify-center rounded-lg bg-primary-50 text-primary-600 hover:bg-primary-100 dark:bg-primary-900/20 dark:text-primary-400 dark:hover:bg-primary-900/30 text-sm"
            title={user.is_admin ? 'Remove Admin' : 'Make Admin'}
          >
            {user.is_admin ? '🔓' : '🔒'}
          </button>
          <button
            onClick={() => handleDeleteUser(user)}
            className="w-8 h-8 flex items-center justify-center rounded-lg bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30 text-sm"
            title="Delete user"
          >
            🗑️
          </button>
        </div>
      </div>
    </div>
  ))}
</div>
```

- [ ] **Step 4: 移动端添加搜索框适配**

找到搜索 input 的父 div `<div className="bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-soft ... mb-6">` ，确保 padding 在小屏合理。当前已是 `p-4`（1rem），对小屏够用，无需修改。

- [ ] **Step 5: 前端构建验证**

```bash
cd src/frontend && npm run build 2>&1 | tail -20
```

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/pages/AdminUsersPage.tsx
git commit -m "feat: add mobile card layout to AdminUsersPage"
```

---

### Task 4: AdminCatalogPage 移动端紧凑优化

**Files:**
- Modify: `src/frontend/src/pages/AdminCatalogPage.tsx`

**Interfaces:**
- Consumes: 现有 `PendingTutorial` 接口、`api.adminListPendingTutorials()`、`api.adminReviewTutorial()`
- Produces: 移动端紧凑可读的卡片布局

- [ ] **Step 1: 定位需要优化的元素**

当前卡片布局（第 100-135 行）：
- 标题 + 描述 + 统计信息 + 操作按钮
- 统计信息使用 `text-xs` + `...` 截断 owner_id
- 按钮为完整文字 "Approve"/"Reject"

- [ ] **Step 2: 统计信息改为移动端紧凑格式**

找到第 107-116 行的统计信息 div，修改为响应式显示：

```tsx
// 改前
<div className="flex items-center gap-4 mt-3 text-xs text-gray-400 dark:text-gray-500">
  <span>👤 Owner: {tutorial.owner_id.slice(0, 8)}...</span>
  <span>📖 {tutorial.total_chapters || 0} chapters</span>
  <span>👁️ {tutorial.view_count || 0} views</span>
  <span>❤️ {tutorial.like_count || 0} likes</span>
  {tutorial.reported_count && tutorial.reported_count > 0 && (
    <span className="text-red-500">⚠️ {tutorial.reported_count} reports</span>
  )}
  <span>📅 {new Date(tutorial.created_at).toLocaleDateString()}</span>
</div>

// 改后
<div className="flex flex-wrap items-center gap-2 mt-3 text-xs text-gray-400 dark:text-gray-500">
  <span className="hidden sm:inline">👤 Owner: {tutorial.owner_id.slice(0, 8)}...</span>
  <span className="sm:hidden">👤 {tutorial.owner_id.slice(0, 6)}...</span>
  <span>📖 {tutorial.total_chapters || 0}ch</span>
  <span>👁️ {tutorial.view_count || 0}</span>
  <span>❤️ {tutorial.like_count || 0}</span>
  {tutorial.reported_count && tutorial.reported_count > 0 && (
    <span className="text-red-500">⚠️{tutorial.reported_count}</span>
  )}
  <span className="ml-auto">📅 {new Date(tutorial.created_at).toLocaleDateString()}</span>
</div>
```

- [ ] **Step 3: 操作按钮改为移动端紧凑形式**

找到第 118-133 行的按钮 div，改为响应式布局：

```tsx
// 改前
<div className="flex gap-2 ml-4">
  <button ... className="px-4 py-2 bg-green-500 ...">
    {reviewingId === tutorial.id ? '...' : '✓ Approve'}
  </button>
  <button ... className="px-4 py-2 bg-red-500 ...">
    {reviewingId === tutorial.id ? '...' : '✗ Reject'}
  </button>
</div>

// 改后
<div className="flex gap-2 ml-4 shrink-0">
  <button
    onClick={() => handleReview(tutorial.id, 'approve')}
    disabled={reviewingId === tutorial.id}
    className="hidden sm:flex px-4 py-2 bg-green-500 text-white rounded-xl hover:bg-green-600 text-sm font-medium disabled:opacity-50"
  >
    {reviewingId === tutorial.id ? '...' : '✓ Approve'}
  </button>
  <button
    onClick={() => handleReview(tutorial.id, 'approve')}
    disabled={reviewingId === tutorial.id}
    className="sm:hidden w-9 h-9 flex items-center justify-center rounded-lg bg-green-500 text-white text-sm disabled:opacity-50"
    title="Approve"
  >
    ✓
  </button>
  <button
    onClick={() => handleReview(tutorial.id, 'reject')}
    disabled={reviewingId === tutorial.id}
    className="hidden sm:flex px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600 text-sm font-medium disabled:opacity-50"
  >
    {reviewingId === tutorial.id ? '...' : '✗ Reject'}
  </button>
  <button
    onClick={() => handleReview(tutorial.id, 'reject')}
    disabled={reviewingId === tutorial.id}
    className="sm:hidden w-9 h-9 flex items-center justify-center rounded-lg bg-red-500 text-white text-sm disabled:opacity-50"
    title="Reject"
  >
    ✗
  </button>
</div>
```

- [ ] **Step 4: 卡片容器添加小屏 padding 缩减**

找到第 100 行的卡片 div `<div key={tutorial.id} className="bg-white ... p-6 ...">` ，添加响应式 padding：

```tsx
// 改前
<div key={tutorial.id} className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-soft border border-gray-100 dark:border-gray-700">

// 改后
<div key={tutorial.id} className="bg-white dark:bg-gray-800 rounded-2xl p-4 sm:p-6 shadow-soft border border-gray-100 dark:border-gray-700">
```

- [ ] **Step 5: 顶部标题行在小屏缩减字体**

找到第 103 行的标题 `<h3 className="text-lg ...">` ，添加响应式：

```tsx
// 改前
<h3 className="text-lg font-bold text-gray-900 dark:text-white">{tutorial.title}</h3>

// 改后
<h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white">{tutorial.title}</h3>
```

- [ ] **Step 6: 前端构建验证**

```bash
cd src/frontend && npm run build 2>&1 | tail -20
```

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/pages/AdminCatalogPage.tsx
git commit -m "feat: optimize AdminCatalogPage for mobile screens"
```

---

### Task 5: 全量构建与测试验证

**Files:**
- No code changes
- Verify: docker build, npm build

**Interfaces:**
- Consumes: all previous tasks
- Produces: 可部署的完整构建

- [ ] **Step 1: 构建后端镜像验证 WeasyPrint 依赖**

```bash
docker build -f Dockerfile.backend --progress=plain -t ollp-backend:test . 2>&1 | tail -30
```

确认构建成功，无 apt-get 错误。

- [ ] **Step 2: 构建前端验证 TypeScript 无错误**

```bash
cd src/frontend && npm run build 2>&1
```

确认 `Compiled successfully.` 且退出码为 0。

- [ ] **Step 3: 运行后端测试**

```bash
cd src/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

确认所有测试通过（允许已知的 3 个预存失败）。

- [ ] **Step 4: 最终 Commit（如有增量改动）**

```bash
git status --short
git add -A
git commit -m "feat: P2 responsive optimization + WeasyPrint deps"
```
