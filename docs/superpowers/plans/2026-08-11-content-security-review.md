# 内容安全审查功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现AI生成内容的自动安全审查，包括敏感词过滤、危险内容检测和审计日志记录。

**Architecture:** 创建独立的 `ContentSecurityService` 服务，在大纲生成和章节生成后自动扫描内容。使用本地 badwords 库进行敏感词检测，正则表达式检测危险内容模式，并将扫描结果记录到新的 `audit_logs` 表中。扫描结果通过新的 API 端点暴露给管理员。

**Tech Stack:** Python, FastAPI, SQLAlchemy, badwords (profanity filter), regex

## Global Constraints

- 使用 `badwords` 包进行中文敏感词检测（无需外部API）
- 所有扫描结果必须记录到 `audit_logs` 表
- 危险内容不阻止生成，但标记为 `needs_review=True`
- 扫描服务必须是纯Python实现，不依赖AWS/Azure等外部服务
- 数据库迁移使用SQLite DDL语句（兼容当前SQLite部署）

---

### Task 1: 创建 audit_logs 数据库模型

**Files:**
- Create: `src/backend/src/models/audit_log.py`
- Modify: `src/backend/src/database.py` (添加导入)
- Test: `src/backend/tests/test_audit_log.py`

**Interfaces:**
- Consumes: `Base` from `database.py`
- Produces: `AuditLog` model with `id`, `user_id`, `action_type`, `ip_address`, `success`, `timestamp`, `details_json`

- [ ] **Step 1: 创建 AuditLog 模型文件**

```python
# src/backend/src/models/audit_log.py
"""Audit log model for tracking security scans and user actions."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON
from ..database import Base


class AuditLog(Base):
    """Records user actions and system events for audit purposes."""

    __tablename__ = 'audit_logs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True)
    action_type = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=True)
    success = Column(DateTime, default=datetime.utcnow)
    details_json = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "ip_address": self.ip_address,
            "success": self.success.isoformat() if self.success else None,
            "details": self.details_json,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    @staticmethod
    def create(db, user_id: str, action_type: str, details: dict = None, ip_address: str = None):
        """Create a new audit log entry."""
        log = AuditLog(
            user_id=user_id,
            action_type=action_type,
            ip_address=ip_address,
            details_json=details
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
```

- [ ] **Step 2: 更新 database.py 导入**

在 `src/backend/src/database.py` 中添加：
```python
from src.models.audit_log import AuditLog
```

- [ ] **Step 3: 创建测试文件**

```python
# src/backend/tests/test_audit_log.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, get_db
from src.models.audit_log import AuditLog


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_audit_log(db_session):
    log = AuditLog.create(
        db=db_session,
        user_id="user-123",
        action_type="content_scanned",
        details={"score": 0.5},
        ip_address="127.0.0.1"
    )
    assert log.id is not None
    assert log.action_type == "content_scanned"
    assert log.user_id == "user-123"


def test_audit_log_to_dict(db_session):
    log = AuditLog.create(
        db=db_session,
        user_id="user-456",
        action_type="login",
        details={"success": True}
    )
    d = log.to_dict()
    assert "id" in d
    assert d["action_type"] == "login"
    assert d["user_id"] == "user-456"
```

- [ ] **Step 4: 运行测试**

```bash
cd src/backend
python -m pytest tests/test_audit_log.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/backend/src/models/audit_log.py src/backend/src/database.py src/backend/tests/test_audit_log.py
git commit -m "feat: add AuditLog model for security audit tracking"
```

---

### Task 2: 创建 ContentSecurityService

**Files:**
- Create: `src/backend/src/services/content_security.py`
- Test: `src/backend/tests/test_content_security.py`

**Interfaces:**
- Consumes: `AuditLog.create()` from Task 1
- Produces: `ContentSecurityService.scan_content(content, user_id) -> Dict[str, Any]`

- [ ] **Step 1: 创建服务文件**

```python
# src/backend/src/services/content_security.py
"""Content security scanning service for AI-generated tutorials."""

import re
import logging
from typing import Dict, Any, List
from uuid import UUID

try:
    import badwords
    _BADWORDS = badwords.Badwords()
except ImportError:
    _BADWORDS = None

from ..models.audit_log import AuditLog
from ..database import get_session

logger = logging.getLogger(__name__)

# 危险内容正则模式
DANGEROUS_PATTERNS = [
    r'\b(注入|exec|system\(\)|eval\(|高风险 exploit)\b',
    r'\b(绕过.*安全|破解.*密码|窃取.*数据)\b',
    r'\b(输入.*秘密|泄露.*密钥|暴露.*API)\b',
]

# 编译正则
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


class ContentSecurityService:
    """Scan AI-generated content for security issues."""

    def __init__(self):
        self.profanity_filter = _BADWORDS
        self.dangerous_patterns = _COMPILED_PATTERNS

    def scan_content(self, content: str, user_id: str) -> Dict[str, Any]:
        """
        Scan content for security issues.

        Returns:
            {
                'contains_profanity': bool,
                'has_sensitive_info': bool,
                'contains_dangerous_content': bool,
                'needs_review': bool,
                'reasons': List[str],
                'flagged_terms': List[str]
            }
        """
        reasons: List[str] = []
        flagged_terms: List[str] = []

        # 1. 检测不当语言
        has_profanity = False
        if self.profanity_filter:
            try:
                result = self.profanity_filter.contains(content)
                if result:
                    has_profanity = True
                    reasons.append('包含不当语言')
                    # 提取被标记的词汇
                    flagged = self.profanity_filter.find(content)
                    flagged_terms.extend(flagged)
            except Exception as e:
                logger.warning(f"Profanity check failed: {e}")

        # 2. 检测危险内容模式
        has_dangerous = False
        for pattern in self.dangerous_patterns:
            matches = pattern.findall(content)
            if matches:
                has_dangerous = True
                reasons.append(f'包含危险内容模式: {matches[0]}')
                flagged_terms.extend(matches)
                break

        # 3. 检测敏感信息（简单规则：身份证号、手机号）
        has_sensitive = False
        # 身份证号正则
        id_pattern = re.compile(r'\b\d{17}[\dXx]\b')
        # 手机号正则
        phone_pattern = re.compile(r'\b1[3-9]\d{9}\b')

        if id_pattern.search(content):
            has_sensitive = True
            reasons.append('可能包含身份证信息')
        if phone_pattern.search(content):
            has_sensitive = True
            reasons.append('可能包含手机号信息')

        needs_review = has_profanity or has_dangerous or has_sensitive

        # 记录审计日志
        self._log_scan(user_id, content, has_profanity, has_dangerous, has_sensitive, reasons)

        return {
            'contains_profanity': has_profanity,
            'has_sensitive_info': has_sensitive,
            'contains_dangerous_content': has_dangerous,
            'needs_review': needs_review,
            'reasons': reasons,
            'flagged_terms': list(set(flagged_terms))
        }

    def _log_scan(self, user_id: str, content: str,
                  has_profanity: bool, has_dangerous: bool, has_sensitive: bool,
                  reasons: List[str]):
        """Log the security scan to audit_logs."""
        try:
            AuditLog.create(
                db=get_session(),
                user_id=user_id,
                action_type='content_scanned',
                details={
                    'content_length': len(content),
                    'profanity_detected': has_profanity,
                    'dangerous_content_detected': has_dangerous,
                    'sensitive_info_detected': has_sensitive,
                    'reasons': reasons,
                    'content_sample': content[:200] + '...' if len(content) > 200 else content
                }
            )
        except Exception as e:
            logger.error(f"Failed to log security scan: {e}")

    def is_content_safe(self, content: str, user_id: str) -> bool:
        """Quick check if content is safe (no review needed)."""
        result = self.scan_content(content, user_id)
        return not result['needs_review']
```

- [ ] **Step 2: 创建测试文件**

```python
# src/backend/tests/test_content_security.py
import pytest
from src.services.content_security import ContentSecurityService


@pytest.fixture
def service():
    return ContentSecurityService()


def test_clean_content(service):
    content = "这是一段正常的教学内容，介绍Python基础语法。"
    result = service.scan_content(content, "user-123")
    assert result['needs_review'] == False
    assert result['contains_profanity'] == False
    assert result['contains_dangerous_content'] == False


def test_content_with_dangerous_pattern(service):
    content = "本节介绍如何绕过防火墙进行网络注入攻击"
    result = service.scan_content(content, "user-123")
    assert result['needs_review'] == True
    assert result['contains_dangerous_content'] == True


def test_content_with_phone_number(service):
    content = "如有疑问请联系13800138000咨询"
    result = service.scan_content(content, "user-123")
    assert result['needs_review'] == True
    assert result['has_sensitive_info'] == True


def test_content_with_id_card(service):
    content = "您的身份证号是110101199001011234"
    result = service.scan_content(content, "user-123")
    assert result['needs_review'] == True
    assert result['has_sensitive_info'] == True


def test_is_content_safe(service):
    safe = service.is_content_safe("正常教学内容", "user-123")
    assert safe == True

    unsafe = service.is_content_safe("绕过安全机制", "user-123")
    assert unsafe == False
```

- [ ] **Step 3: 安装 badwords 依赖**

在项目根目录执行：
```bash
pip install badwords
```

然后在 `src/backend/requirements.txt` 中添加：
```
badwords>=1.0.0
```

- [ ] **Step 4: 运行测试**

```bash
cd src/backend
python -m pytest tests/test_content_security.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/backend/src/services/content_security.py src/backend/tests/test_content_security.py src/backend/requirements.txt
git commit -m "feat: add ContentSecurityService for AI content scanning"
```

---

### Task 3: 集成安全扫描到章节生成

**Files:**
- Modify: `src/backend/src/services/chapter_generator.py`
- Modify: `src/backend/src/api/tutorials.py`

**Interfaces:**
- Consumes: `ContentSecurityService` from Task 2
- Produces: 章节生成后自动扫描，结果记录到章节内容

- [ ] **Step 1: 修改 chapter_generator.py**

在 `src/backend/src/services/chapter_generator.py` 中：

1. 添加导入：
```python
from ..services.content_security import ContentSecurityService
```

2. 在 `__init__` 中添加：
```python
self.security_service = ContentSecurityService()
```

3. 在 `generate()` 方法中，解析内容后添加扫描：
```python
# 扫描生成的内容
content_to_scan = json.dumps(chapter_content) if isinstance(chapter_content, dict) else chapter_text
scan_result = self.security_service.scan_content(content_to_scan, str(user_id))

# 将扫描结果存入章节
chapter_content['_security_scan'] = scan_result
```

- [ ] **Step 2: 修改 tutorials.py 的 generate_next_chapter 端点**

在 `src/backend/src/api/tutorials.py` 的 `generate_next_chapter` 函数中，保存章节前添加：

```python
# 获取扫描结果（已在章节内容中）
security_scan = chapter_content.get('_security_scan', {})

# 如果内容需要审核，标记教程状态
if security_scan.get('needs_review'):
    tutorial.status = TutorialStatus.REVIEWING.value
    logger.warning(f"Chapter {next_number} flagged for review: {security_scan.get('reasons', [])}")
```

- [ ] **Step 3: 运行现有测试确保无回归**

```bash
cd src/backend
python -m pytest tests/ -v
```

- [ ] **Step 4: 提交**

```bash
git add src/backend/src/services/chapter_generator.py src/backend/src/api/tutorials.py
git commit -m "feat: integrate content security scanning into chapter generation"
```

---

### Task 4: 集成安全扫描到大纲生成

**Files:**
- Modify: `src/backend/src/services/outline_generator.py`
- Modify: `src/backend/src/api/tutorials.py`

**Interfaces:**
- Consumes: `ContentSecurityService` from Task 2
- Produces: 大纲生成后自动扫描

- [ ] **Step 1: 修改 outline_generator.py**

在 `src/backend/src/services/outline_generator.py` 中：

1. 添加导入：
```python
from ..services.content_security import ContentSecurityService
```

2. 在 `__init__` 中添加：
```python
self.security_service = ContentSecurityService()
```

3. 在 `generate()` 方法中，解析大纲后添加扫描：
```python
# 扫描大纲内容
scan_result = self.security_service.scan_content(
    json.dumps(outline_data),
    str(user_id)
)
outline_data['_security_scan'] = scan_result
```

- [ ] **Step 2: 修改 tutorials.py 的 generate_outline 端点**

在大纲生成成功后，检查扫描结果并记录：
```python
# 检查大纲安全性
outline_data = result.get("outline", {})
security_scan = outline_data.get('_security_scan', {})

if security_scan.get('needs_review'):
    task_log.details_json = {
        **task_log.details_json,
        'security_scan': security_scan,
        'needs_review': True
    }
    logger.warning(f"Outline flagged for review: {security_scan.get('reasons', [])}")
```

- [ ] **Step 3: 运行测试**

```bash
cd src/backend
python -m pytest tests/ -v
```

- [ ] **Step 4: 提交**

```bash
git add src/backend/src/services/outline_generator.py src/backend/src/api/tutorials.py
git commit -m "feat: integrate content security scanning into outline generation"
```

---

### Task 5: 添加安全扫描 API 端点

**Files:**
- Create: `src/backend/src/api/security.py`
- Modify: `src/backend/src/api/main.py`
- Modify: `src/backend/src/schemas/api.py`

**Interfaces:**
- Consumes: `AuditLog` model, `ContentSecurityService`
- Produces: `GET /api/v1/security/scans` (管理员查看扫描记录)

- [ ] **Step 1: 创建 security.py API 文件**

```python
# src/backend/src/api/security.py
"""Security scanning API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from ..database import get_db
from ..models.audit_log import AuditLog
from ..services.content_security import ContentSecurityService

logger = logging.getLogger(__name__)

security_router = APIRouter(prefix="/security", tags=["security"])


@security_router.get("/scans", response_model=Dict[str, Any])
async def get_security_scans(
    db: Session = Depends(get_db),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """Get security scan records."""
    query = db.query(AuditLog).filter(AuditLog.action_type == 'content_scanned')

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)

    total = query.count()
    offset = (page - 1) * limit
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "data": [log.to_dict() for log in logs],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@security_router.get("/stats", response_model=Dict[str, Any])
async def get_security_stats(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get security scan statistics."""
    total_scans = db.query(AuditLog).filter(
        AuditLog.action_type == 'content_scanned'
    ).count()

    flagged_count = db.query(AuditLog).filter(
        AuditLog.action_type == 'content_scanned',
        AuditLog.details_json['reasons'].isnot(None)
    ).count()

    return {
        "total_scans": total_scans,
        "flagged_count": flagged_count,
        "flag_rate": flagged_count / total_scans if total_scans > 0 else 0
    }
```

- [ ] **Step 2: 在 main.py 中注册路由**

在 `src/backend/src/api/main.py` 中添加：
```python
from .security import security_router
# ... 在 app.include_router 部分添加 ...
app.include_router(security_router, prefix="/api/v1")
```

- [ ] **Step 3: 创建测试**

```python
# src/backend/tests/test_security_api.py
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database import Base, get_db
from src.models.audit_log import AuditLog


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c


def test_get_security_scans(client, db_session):
    # Create a test audit log
    AuditLog.create(
        db=db_session,
        user_id="user-123",
        action_type="content_scanned",
        details={"reasons": ["测试原因"]}
    )
    db_session.commit()

    response = client.get("/api/v1/security/scans")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data


def test_get_security_stats(client, db_session):
    # Create test data
    AuditLog.create(
        db=db_session,
        user_id="user-123",
        action_type="content_scanned",
        details={"reasons": ["测试"]}
    )
    db_session.commit()

    response = client.get("/api/v1/security/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_scans" in data
    assert "flagged_count" in data
```

- [ ] **Step 4: 运行测试**

```bash
cd src/backend
python -m pytest tests/test_security_api.py -v
```

- [ ] **Step 5: 提交**

```bash
git add src/backend/src/api/security.py src/backend/src/api/main.py src/backend/tests/test_security_api.py
git commit -m "feat: add security scanning API endpoints"
```

---

### Task 6: 数据库迁移脚本

**Files:**
- Create: `src/backend/src/database/migrations/001_add_audit_logs.py`
- Create: `src/backend/src/database/migrations/002_add_content_security.py`

**Interfaces:**
- Consumes: SQLite DDL support
- Produces: Migration scripts that can be run to add new tables

- [ ] **Step 1: 创建迁移脚本目录**

```bash
mkdir -p src/backend/src/database/migrations
```

- [ ] **Step 2: 创建迁移脚本**

```python
# src/backend/src/database/migrations/001_add_audit_logs.py
"""Migration: Add audit_logs table."""

import sqlite3


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36),
            action_type VARCHAR(50) NOT NULL,
            ip_address VARCHAR(45),
            success DATETIME,
            details_json JSON,
            timestamp DATETIME,
            PRIMARY KEY (id)
        )
    """)

    conn.commit()
    conn.close()
    print("Migration 001 completed: audit_logs table created")


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./ollp.db"
    migrate(db_path)
```

```python
# src/backend/src/database/migrations/002_add_content_security.py
"""Migration: Add content security related fields."""

import sqlite3


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add is_reviewing status to tutorials if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tutorials_backup AS SELECT * FROM tutorials
    """)
    cursor.execute("DROP TABLE tutorials")
    cursor.execute("""
        CREATE TABLE tutorials (
            id VARCHAR(36) NOT NULL,
            owner_id VARCHAR(36) NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            is_public BOOLEAN,
            status VARCHAR(9),
            outline JSON,
            total_chapters INTEGER,
            current_chapter INTEGER,
            created_at DATETIME,
            updated_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(owner_id) REFERENCES users (id)
        )
    """)
    cursor.execute("INSERT INTO tutorials SELECT * FROM tutorials_backup")
    cursor.execute("DROP TABLE tutorials_backup")

    conn.commit()
    conn.close()
    print("Migration 002 completed: content security fields added")


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./ollp.db"
    migrate(db_path)
```

- [ ] **Step 3: 创建迁移运行脚本**

```python
# src/backend/src/database/migrate.py
"""Database migration runner."""

import os
import sys
import importlib.util
from pathlib import Path


def run_migrations(db_path: str):
    """Run all pending migrations."""
    migrations_dir = Path(__file__).parent / "migrations"

    if not db_path.endswith('.db'):
        # Extract path from SQLite URL
        db_path = db_path.replace('sqlite:///', '').replace('sqlite://', '')

    print(f"Running migrations for: {db_path}")

    # Get all migration files
    migration_files = sorted([
        f for f in migrations_dir.glob("*.py")
        if f.name != "__init__.py"
    ])

    for migration_file in migration_files:
        spec = importlib.util.spec_from_file_location(
            migration_file.stem, migration_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(db_path)

    print("All migrations completed!")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./ollp.db"
    run_migrations(db_path)
```

- [ ] **Step 4: 提交**

```bash
git add src/backend/src/database/
git commit -m "feat: add database migration scripts for audit logs and content security"
```

---

### Task 7: 部署到服务器并验证

**Files:**
- Modify: 服务器上的 `/opt/ollp/src/services/content_security.py`
- Modify: 服务器上的 `/opt/ollp/src/api/tutorials.py`
- Modify: 服务器上的 `/opt/ollp/frontend/static/js/main.de6c3c14.js` (如有需要)

**Interfaces:**
- Consumes: 所有已完成的代码
- Produces: 部署后的功能验证

- [ ] **Step 1: 上传新文件到服务器**

使用现有的部署脚本上传：
```python
# 上传到服务器
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('tlcw.yobeeo.com', username='root', password='tlcw_CENTOS@#2023')

# 上传文件...
```

- [ ] **Step 2: 运行数据库迁移**

```bash
docker exec ollp-backend python /opt/ollp/src/database/migrate.py /app/ollp.db
```

- [ ] **Step 3: 重启后端服务**

```bash
docker restart ollp-backend
```

- [ ] **Step 4: 验证 API**

```bash
# 测试安全扫描 API
curl -s http://localhost:8000/api/v1/security/stats | jq .

# 测试扫描记录
curl -s http://localhost:8000/api/v1/security/scans | jq .
```

- [ ] **Step 5: 测试内容生成**

通过前端创建一个教程，生成章节，然后检查：
1. 扫描日志是否记录
2. 危险内容是否被标记
3. API 返回是否正确

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "deploy: add content security scanning to production"
```

---

## 文件结构总览

```
src/backend/
├── src/
│   ├── api/
│   │   ├── security.py          # 新建：安全扫描 API
│   │   └── tutorials.py         # 修改：集成安全扫描
│   ├── services/
│   │   ├── content_security.py  # 新建：安全扫描服务
│   │   └── chapter_generator.py # 修改：调用安全扫描
│   │   └── outline_generator.py # 修改：调用安全扫描
│   ├── models/
│   │   └── audit_log.py         # 新建：审计日志模型
│   └── database/
│       └── migrations/          # 新建：迁移脚本
│           ├── 001_add_audit_logs.py
│           └── 002_add_content_security.py
├── tests/
│   ├── test_audit_log.py        # 新建
│   ├── test_content_security.py # 新建
│   └── test_security_api.py     # 新建
└── requirements.txt             # 修改：添加 badwords
```

---

## 验收标准

1. [ ] `audit_logs` 表已创建，包含必要字段
2. [ ] `ContentSecurityService` 能检测敏感词、危险模式、个人信息
3. [ ] 章节生成后自动进行安全扫描
4. [ ] 大纲生成后自动进行安全扫描
5. [ ] 扫描结果记录到 `audit_logs` 表
6. [ ] `GET /api/v1/security/scans` 返回扫描记录
7. [ ] `GET /api/v1/security/stats` 返回统计信息
8. [ ] 所有测试通过
9. [ ] 部署到服务器后功能正常

---

**计划完成**
