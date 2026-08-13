# P1 社交功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 P1 社交功能：教程分享（share_code）和 WebSocket 聊天历史持久化

**Architecture:** 纯前端 + 轻量后端修改。分享功能通过生成短码并添加 API 端点实现；WebSocket 聊天历史通过新增 SQLite 表实现持久化。

**Tech Stack:** FastAPI + SQLAlchemy + React + TypeScript + recharts + uuid

## Global Constraints

- 不引入新的 npm 包，复用现有 recharts、uuid、react-hot-toast
- 数据库变更使用 SQLAlchemy migration（sqlite 文件直接 ALTER TABLE）
- 所有 UI 使用 Tailwind CSS dark: 变体预留（暂不实现暗色模式）
- 错误提示统一使用 useToast()，禁用 alert()
- 后端所有端点需要 JWT 认证（admin 端点除外）
- 前端路由在 App.tsx 中保持单一入口
- share_code 格式：8位大写字母数字组合（35^8 种可能性）

---

## 任务总览

| # | 任务 | 文件变更 |
|---|------|----------|
| 1 | 教程分享 - 后端 share_code | models/tutorial.py, api/tutorials.py, database.py |
| 2 | 教程分享 - 前端 ShareModal | components/ShareModal.tsx, api/client.ts, pages/TutorialDisplayPage.tsx |
| 3 | WebSocket 聊天历史持久化 | models/chat_history.py, api/websocket.py |

---

### Task 1: 教程分享 - 后端 share_code

**Files:**
- Modify: `src/backend/src/models/tutorial.py` — 添加 share_code 字段
- Modify: `src/backend/src/api/tutorials.py` — 添加 get_by_share_code 端点
- Modify: `src/backend/src/database.py` — 启动时执行 ALTER TABLE
- Modify: `src/backend/src/api/main.py` — 注册新端点

**Interfaces:**
- Consumes: Tutorial model, JWT auth (get_current_user)
- Produces: `GET /api/v1/tutorials/share/{share_code}` — 返回教程基本信息

**前置知识:**
- Tutorial 模型已有 id, title, description, is_public, status 等字段
- share_code 为 VARCHAR(20) UNIQUE，自动生成（8位字母数字）
- 分享链接格式: `/tutorial/share/{share_code}`

- [ ] **Step 1: 在 Tutorial 模型中添加 share_code 字段**

修改 `src/backend/src/models/tutorial.py`:
```python
# 在 Column 定义区域添加
share_code = Column(String(20), unique=True, nullable=True)

# 在 to_dict 方法中添加
"share_code": self.share_code,
```

- [ ] **Step 2: 添加 share_code 生成方法和数据库迁移**

修改 `src/backend/src/models/tutorial.py`, 添加:
```python
import random
import string

@staticmethod
def generate_share_code() -> str:
    """Generate an 8-character alphanumeric share code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))
```

修改 `src/backend/src/database.py`, 在 `init_db()` 中添加:
```python
import sqlite3
import os

def migrate_db():
    """Run database migrations for new features."""
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add share_code to tutorials if not exists
        try:
            cursor.execute("ALTER TABLE tutorials ADD COLUMN share_code VARCHAR(20) UNIQUE")
            conn.commit()
            logger.info("Added share_code column to tutorials")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.close()
```

修改 `src/backend/src/api/main.py`, 在 startup_event 中添加:
```python
from ..database import migrate_db
# ...
async def startup_event():
    Base.metadata.create_all(bind=engine)
    migrate_db()  # 添加这一行
    logger.info("Database tables created/initialized successfully")
```

- [ ] **Step 3: 在 Tutorial 创建时自动生成 share_code**

修改 `src/backend/src/api/tutorials.py`, 在 `confirm_outline` 中添加:
```python
# 创建教程后
tutorial = Tutorial(
    owner_id=str(current_user.id),
    # ... 其他字段
)
tutorial.share_code = Tutorial.generate_share_code()  # 添加这行
db.add(tutorial)
```

- [ ] **Step 4: 添加按 share_code 获取教程的端点**

在 `src/backend/src/api/tutorials.py` 中添加:
```python
@tutorials_router.get("/share/{share_code}")
async def get_tutorial_by_share_code(
    share_code: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get tutorial by share code for public viewing."""
    tutorial = db.query(Tutorial).filter(
        Tutorial.share_code == share_code.upper()
    ).first()
    
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    
    if not tutorial.is_public:
        raise HTTPException(status_code=403, detail="Tutorial is not public")
    
    return {
        "success": True,
        "data": {
            "id": tutorial.id,
            "title": tutorial.title,
            "description": tutorial.description,
            "owner_id": tutorial.owner_id,
            "status": tutorial.status,
            "total_chapters": tutorial.total_chapters,
            "created_at": tutorial.created_at.isoformat() if tutorial.created_at else None,
        }
    }
```

- [ ] **Step 5: 运行测试并验证**

```bash
cd src/backend
python -c "
from src.models.tutorial import Tutorial
print(Tutorial.generate_share_code())
"
```

预期输出：8位大写字母数字组合，如 `A3F7K9M2`

- [ ] **Step 6: 提交**

```bash
git add src/backend/src/models/tutorial.py src/backend/src/database.py src/backend/src/api/main.py src/backend/src/api/tutorials.py
git commit -m "feat: add share_code to Tutorial model and create endpoint"
```

---

### Task 2: 教程分享 - 前端 ShareModal

**Files:**
- Create: `src/frontend/src/components/ShareModal.tsx`
- Modify: `src/frontend/src/api/client.ts` — 添加 getTutorialByShareCode 方法
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx` — 集成 ShareModal
- Modify: `src/frontend/src/App.tsx` — 添加分享路由

**Interfaces:**
- Consumes: `api.getCatalogTutorial(id)` (existing), tutorial data
- Produces: ShareModal component with social buttons, copy link, preview card

**前置知识:**
- 分享链接格式: `{origin}/tutorial/share/{share_code}`
- 使用 react-hot-toast 进行提示
- 使用现有的 toast hook: `const toast = useToast()`

- [ ] **Step 1: 添加 API 客户端方法**

修改 `src/frontend/src/api/client.ts`, 在 export 方法前添加:
```typescript
async getTutorialByShareCode(shareCode: string) {
  return this.request<any>(`GET`, `/api/v1/tutorials/share/${shareCode.toUpperCase()}`);
}
```

- [ ] **Step 2: 创建 ShareModal 组件**

创建 `src/frontend/src/components/ShareModal.tsx`:
```tsx
import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  tutorialId: string;
  tutorialTitle: string;
  tutorialDescription: string;
}

const ShareModal = ({ isOpen, onClose, tutorialId, tutorialTitle, tutorialDescription }: ShareModalProps) => {
  const toast = useToast();
  const [shareUrl, setShareUrl] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && tutorialId) {
      const baseUrl = window.location.origin;
      setShareUrl(`${baseUrl}/tutorial/${tutorialId}`);
    }
  }, [isOpen, tutorialId]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast.success('Link copied to clipboard!');
    } catch {
      toast.error('Failed to copy link');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-gray-900">Share Tutorial</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Preview Card */}
        <div className="bg-gradient-to-br from-primary-50 to-accent-50 rounded-xl p-4 mb-6">
          <h4 className="font-bold text-gray-900 mb-2">{tutorialTitle}</h4>
          <p className="text-sm text-gray-600 line-clamp-2">{tutorialDescription || 'AI-powered personalized learning tutorial'}</p>
        </div>

        {/* Share Link */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Share Link</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={shareUrl}
              readOnly
              className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600"
            />
            <button
              onClick={handleCopy}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
            >
              Copy
            </button>
          </div>
        </div>

        {/* Social Buttons */}
        <div className="flex justify-center gap-4">
          <button
            onClick={() => {
              window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(tutorialTitle)}&url=${encodeURIComponent(shareUrl)}`, '_blank');
            }}
            className="w-10 h-10 rounded-full bg-sky-500 text-white flex items-center justify-center hover:bg-sky-600 transition-colors"
            title="Share on Twitter"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
            </svg>
          </button>
          <button
            onClick={() => {
              const linkedInUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;
              window.open(linkedInUrl, '_blank');
            }}
            className="w-10 h-10 rounded-full bg-blue-700 text-white flex items-center justify-center hover:bg-blue-800 transition-colors"
            title="Share on LinkedIn"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
            </svg>
          </button>
          <button
            onClick={() => {
              const wechatUrl = `https://api.wechat.com/scan?url=${encodeURIComponent(shareUrl)}`;
              window.open(wechatUrl, '_blank');
            }}
            className="w-10 h-10 rounded-full bg-green-500 text-white flex items-center justify-center hover:bg-green-600 transition-colors"
            title="Share on WeChat"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 01.213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 00.167-.054l1.903-1.114a.864.864 0 01.717-.098 10.16 10.16 0 002.837.403c.276 0 .543-.027.811-.05a6.127 6.127 0 01-.253-1.735c0-3.672 3.381-6.654 7.56-6.654.22 0 .437.011.653.03C16.643 4.988 13.035 2.188 8.691 2.188zm-2.6 4.408c.56 0 1.016.454 1.016 1.016 0 .562-.456 1.016-1.016 1.016-.56 0-1.016-.454-1.016-1.016 0-.562.456-1.016 1.016-1.016zm5.22 0c.56 0 1.016.454 1.016 1.016 0 .562-.456 1.016-1.016 1.016-.56 0-1.016-.454-1.016-1.016 0-.562.456-1.016 1.016-1.016zm4.49 3.376c-3.74 0-6.774 2.722-6.774 6.08 0 3.357 3.034 6.08 6.774 6.08.947 0 1.86-.163 2.69-.46a.744.744 0 01.616.084l1.464.858a.272.272 0 00.139.045c.133 0 .241-.108.241-.241 0-.06-.023-.118-.038-.176l-.3-1.14a.486.486 0 01.175-.545C22.887 17.21 24 15.468 24 13.46c0-3.358-3.034-6.08-6.774-6.08h-.025zm-2.6 3.512c.46 0 .833.373.833.833s-.373.833-.833.833-.833-.373-.833-.833.373-.833.833-.833zm5.187 0c.46 0 .833.373.833.833s-.373.833-.833.833-.833-.373-.833-.833.373-.833.833-.833z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ShareModal;
```

- [ ] **Step 3: 修改 TutorialDisplayPage 集成 ShareModal**

在 `TutorialDisplayPage.tsx` 中添加:
```tsx
import ShareModal from '../components/ShareModal';

// 添加 state
const [showShareModal, setShowShareModal] = useState(false);
```

修改 handleShare 函数:
```tsx
const handleShare = () => {
  if (!id) return;
  setShowShareModal(true);
};
```

在 JSX 中添加 ShareModal 组件:
```tsx
<ShareModal
  isOpen={showShareModal}
  onClose={() => setShowShareModal(false)}
  tutorialId={id!}
  tutorialTitle={chapter?.title || ''}
  tutorialDescription={chapter?.description || ''}
/>
```

- [ ] **Step 4: 添加路由支持**

修改 `src/frontend/src/App.tsx`, 添加:
```tsx
import { Navigate } from 'react-router-dom';

// 在 Routes 中添加分享页面
<Route path="/tutorial/share/:shareCode" element={<ShareRedirect />} />

// 添加重定向组件
const ShareRedirect = () => {
  const { shareCode } = useParams<{ shareCode: string }>();
  const navigate = useNavigate();
  
  useEffect(() => {
    const redirect = async () => {
      const result = await api.getCatalogTutorial(shareCode);
      if (result.success && result.data?.id) {
        navigate(`/tutorial/${result.data.id}`);
      } else {
        navigate('/');
      }
    };
    redirect();
  }, [shareCode, navigate]);
  
  return <div className="min-h-screen flex items-center justify-center"><p>Redirecting...</p></div>;
};
```

需要添加 import:
```tsx
import { useEffect } from 'react';
```

- [ ] **Step 5: 运行构建验证**

```bash
cd src/frontend
npm run build
```

预期：构建成功，无 TypeScript 错误

- [ ] **Step 6: 提交**

```bash
git add src/frontend/src/components/ShareModal.tsx src/frontend/src/api/client.ts src/frontend/src/pages/TutorialDisplayPage.tsx src/frontend/src/App.tsx
git commit -m "feat: add ShareModal component and share functionality"
```

---

### Task 3: WebSocket 聊天历史持久化

**Files:**
- Create: `src/backend/src/models/chat_history.py`
- Modify: `src/backend/src/api/websocket.py` — 添加持久化逻辑
- Modify: `src/backend/src/database.py` — 注册新模型

**Interfaces:**
- Consumes: ChatHistory model, WebSocket connection
- Produces: Persistent chat history stored in SQLite

**前置知识:**
- 当前 WebSocket 历史存储在内存中（`chat_history` dict）
- 需要持久化到数据库表 `chat_histories`
- 重启后历史应保留

- [ ] **Step 1: 创建 ChatHistory 模型**

创建 `src/backend/src/models/chat_history.py`:
```python
"""Chat history model for persistent WebSocket messages."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship, Session
from ..database import Base


class ChatHistory(Base):
    __tablename__ = 'chat_histories'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tutorial_id = Column(String(36), nullable=False)
    channel_id = Column(String(36), nullable=False)
    sender = Column(String(20), nullable=False)  # 'user' or 'ai'
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default='message')  # message, typing, system
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def create(db: Session, tutorial_id: str, channel_id: str, sender: str, content: str, message_type: str = 'message') -> 'ChatHistory':
        """Create a chat history record."""
        record = ChatHistory(
            tutorial_id=tutorial_id,
            channel_id=channel_id,
            sender=sender,
            content=content,
            message_type=message_type
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_history(db: Session, tutorial_id: str, channel_id: str, limit: int = 50) -> list:
        """Get chat history for a tutorial channel."""
        return db.query(ChatHistory).filter(
            ChatHistory.tutorial_id == tutorial_id,
            ChatHistory.channel_id == channel_id
        ).order_by(ChatHistory.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_last_message(db: Session, tutorial_id: str, channel_id: str) -> 'ChatHistory | None':
        """Get the last message for a tutorial channel."""
        return db.query(ChatHistory).filter(
            ChatHistory.tutorial_id == tutorial_id,
            ChatHistory.channel_id == channel_id
        ).order_by(ChatHistory.created_at.desc()).first()
```

- [ ] **Step 2: 修改 database.py 注册新模型**

修改 `src/backend/src/database.py`:
```python
# 在 init_db 函数中添加
from src.models.chat_history import ChatHistory  # 添加这行
# 在 create_all 前确保模型已导入
```

- [ ] **Step 3: 修改 websocket.py 添加持久化**

修改 `src/backend/src/api/websocket.py`:

1. 导入 ChatHistory 模型:
```python
from ..models.chat_history import ChatHistory
```

2. 在收到 user_message 后添加持久化:
```python
# 在发送 acknowledgment 前
if user_id:
    db = SessionLocal()
    try:
        ChatHistory.create(
            db=db,
            tutorial_id=tutorial_id,
            channel_id=channel_id,
            sender='user',
            content=user_content
        )
    finally:
        db.close()
```

3. 在 AI 响应后添加持久化:
```python
# 在发送 ai_response 前
if user_id:
    db = SessionLocal()
    try:
        ChatHistory.create(
            db=db,
            tutorial_id=tutorial_id,
            channel_id=channel_id,
            sender='ai',
            content=response
        )
    finally:
        db.close()
```

4. 修改连接时加载历史:
```python
# 在发送历史前
db = SessionLocal()
try:
    stored_history = ChatHistory.get_history(db, tutorial_id, channel_id, 50)
    # 将存储的历史转换为与内存格式相同
    stored_messages = [
        {
            "id": str(h.id),
            "sender": h.sender,
            "content": h.content,
            "timestamp": h.created_at.isoformat() if h.created_at else datetime.utcnow().isoformat()
        }
        for h in reversed(stored_history)
    ]
    if stored_messages:
        await session.send({
            "type": "history",
            "messages": stored_messages,
            "timestamp": datetime.utcnow().isoformat()
        })
finally:
    db.close()
```

5. 修改数据库迁移:
```python
# 在 database.py 的 migrate_db 函数中添加
cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_histories (
        id VARCHAR(36) NOT NULL,
        tutorial_id VARCHAR(36) NOT NULL,
        channel_id VARCHAR(36) NOT NULL,
        sender VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        message_type VARCHAR(50) DEFAULT 'message',
        created_at DATETIME,
        PRIMARY KEY (id)
    )
""")
conn.commit()
```

- [ ] **Step 4: 运行测试**

```bash
cd src/backend
python -c "
from src.models.chat_history import ChatHistory
print('ChatHistory model imported successfully')
"
```

- [ ] **Step 5: 提交**

```bash
git add src/backend/src/models/chat_history.py src/backend/src/database.py src/backend/src/api/websocket.py
git commit -m "feat: add persistent chat history for WebSocket"
```

---

## 验证清单

- [ ] `GET /api/v1/tutorials/share/{code}` 返回正确的教程信息
- [ ] `/tutorial/share/ABC123` 路由重定向到 `/tutorial/{id}`
- [ ] ShareModal 组件正确显示并支持复制链接
- [ ] Twitter/LinkedIn/微信分享按钮正常工作
- [ ] WebSocket 连接后加载历史消息
- [ ] 发送消息后持久化到数据库
- [ ] 重启后端后历史消息仍然存在
- [ ] 前端构建成功，无 TypeScript 错误

## 风险与注意事项

1. **数据库迁移**: SQLite 的 ALTER TABLE 对已有数据的兼容性需要测试
2. **share_code 唯一性**: 使用 random 生成，需要处理碰撞情况
3. **WebSocket 消息顺序**: 持久化操作应在发送前完成，避免消息丢失
4. **性能**: chat_histories 表可能增长较快，需要定期清理旧数据
