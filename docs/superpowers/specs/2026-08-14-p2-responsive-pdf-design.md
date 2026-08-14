# P2 功能设计 — WeasyPrint 部署修复 + 管理后台响应式优化

**设计日期**: 2026-08-14  
**基于版本**: v1.1.0  
**优先级**: P2  
**范围**: Dockerfile 依赖补全 + 3 个管理页面移动端适配

---

## 背景

根据 `docs/function-completeness-audit.md`，P2 级别存在两个问题：

1. **PDF 依赖 WeasyPrint 外部库** — `Dockerfile.backend` 缺少 pango、cairo 等系统级 C 库，部署时 PDF 导出失败
2. **管理后台移动端适配不足** — AdminDashboardPage / AdminUsersPage / AdminCatalogPage 在移动端体验差

---

## 设计方案

### 1. 后端部署修复 — WeasyPrint 系统依赖

**问题**: `Dockerfile.backend` 的 apt-get install 缺少 WeasyPrint 所需的图形渲染库。

**修改文件**: `Dockerfile.backend`

**改动**: 在现有依赖列表中添加以下系统包：

```dockerfile
libcairo2 \
libpango-1.0-0 \
libgdk-pixbuf2.0-0 \
libffi-dev \
shared-mime-info
```

这些依赖已在 `Dockerfile.worker` 中验证可用，直接同步即可。

**影响范围**: 仅构建层，无运行时变更。

---

### 2. 管理后台响应式优化

#### 2.1 AdminDashboardPage

**当前问题**:
- 统计卡片 `lg:grid-cols-6`，小屏（md）只有 `grid-cols-3`，6 张卡挤在一起
- 图表固定高度 250px，在手机屏上比例失调
- 图表可能溢出容器

**修复方案**:
| 改前 | 改后 |
|------|------|
| `grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6` | `grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6` |
| `<ResponsiveContainer height={250}>` | `<ResponsiveContainer height={200}>` |
| — | 图表容器添加 `overflow-x-auto` |

#### 2.2 AdminUsersPage

**当前问题**:
- 纯表格布局，移动端横向滚动，操作按钮挤压变形

**修复方案**: 双视图模式
- 桌面端（`md` 及以上）：保持原表格布局
- 移动端（`< md`）：显示卡片列表

**卡片布局设计**:
```
┌─────────────────────────────────────┐
│ [👤 Yobeeo]    yobeeo@example.com   │
│                    [Admin 标签]      │
├─────────────────────────────────────┤
│ Joined: 2026-01-15     [🔓] [🗑️]   │
└─────────────────────────────────────┘
```
- 头像左对齐 + 用户名/邮箱
- 角色标签右对齐
- 底部分割线 + 加入日期 + 图标操作按钮

#### 2.3 AdminCatalogPage

**当前问题**:
- 卡片布局尚可，但描述文字、统计信息在小屏可读性差
- 按钮间距不足

**修复方案**:
- 移动端：描述文字 `line-clamp-1` 截断
- 统计信息缩短（去掉 `...` 后缀，缩小字体）
- 按钮 padding 在移动端缩减

---

## 实施文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `Dockerfile.backend` | 修改 | 添加 5 个系统依赖包 |
| `src/frontend/src/pages/AdminDashboardPage.tsx` | 修改 | 统计卡片栅格 + 图表高度 |
| `src/frontend/src/pages/AdminUsersPage.tsx` | 修改 | 表格→卡片双视图 |
| `src/frontend/src/pages/AdminCatalogPage.tsx` | 修改 | 紧凑间距 + 截断优化 |

---

## 验收标准

1. `docker compose build backend` 不报错，PDF 导出端点可正常访问
2. 浏览器窗口宽度 < 768px 时，AdminUsersPage 显示卡片而非表格
3. 浏览器窗口宽度 < 768px 时，AdminDashboardPage 统计卡片 2 列排列，图表不溢出
4. AdminCatalogPage 移动端标题和描述可读，操作按钮可点击

---

## 不涉及的内容

- ~~PWA 离线支持~~ — P3 级别，单独实现
- ~~前端导出按钮适配异步导出~~ — 用户未要求，保持向后兼容
- ~~Nginx 配置变更~~ — 不涉及
