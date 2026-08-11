"""Content security scanning service for AI-generated tutorials."""

import re
import logging
from typing import Dict, Any, List

# Bundled Chinese profanity words (fallback since badwords package lacks Badwords class)
_DEFAULT_PROFANITY_WORDS = [
    '他妈的', '操你', '日你', '傻逼', 'fuck', 'shit', 'ass', 'damn',
    'nmld', 'nmsl', 'caonima', 'tmd', 'tm', 'sb', 'cnm',
]

from ..models.audit_log import AuditLog
from ..database import get_session

logger = logging.getLogger(__name__)

# 危险内容正则模式
DANGEROUS_PATTERNS = [
    r"(注入|exec|system\(\)|eval\(|高风险 exploit)",
    r"(绕过.*安全|破解.*密码|窃取.*数据)",
    r"(输入.*秘密|泄露.*密钥|暴露.*API)",
]

# 编译正则
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


class ContentSecurityService:
    """Scan AI-generated content for security issues."""

    def __init__(self):
        self.profanity_words = _DEFAULT_PROFANITY_WORDS
        self.dangerous_patterns = _COMPILED_PATTERNS

    def scan_content(self, content: str, user_id: str) -> Dict[str, Any]:
        reasons: List[str] = []
        flagged_terms: List[str] = []

        # 1. 检测不当语言
        has_profanity = False
        if self.profanity_filter:
            try:
                result = self.profanity_filter.contains(content)
                if result:
                    has_profanity = True
                    reasons.append("包含不当语言")
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
                reasons.append(f"包含危险内容模式: {matches[0]}")
                flagged_terms.extend(matches)
                break

        # 3. 检测敏感信息
        has_sensitive = False
        id_pattern = re.compile(r"\d{17}[\dXx]")
        phone_pattern = re.compile(r"1[3-9]\d{9}")

        if id_pattern.search(content):
            has_sensitive = True
            reasons.append("可能包含身份证信息")
        if phone_pattern.search(content):
            has_sensitive = True
            reasons.append("可能包含手机号信息")

        needs_review = has_profanity or has_dangerous or has_sensitive

        self._log_scan(user_id, content, has_profanity, has_dangerous, has_sensitive, reasons)

        return {
            "contains_profanity": has_profanity,
            "has_sensitive_info": has_sensitive,
            "contains_dangerous_content": has_dangerous,
            "needs_review": needs_review,
            "reasons": reasons,
            "flagged_terms": list(set(flagged_terms))
        }

    def _log_scan(self, user_id: str, content: str,
                  has_profanity: bool, has_dangerous: bool, has_sensitive: bool,
                  reasons: List[str]):
        try:
            AuditLog.create(
                db=get_session(),
                user_id=user_id,
                action_type="content_scanned",
                details={
                    "content_length": len(content),
                    "profanity_detected": has_profanity,
                    "dangerous_content_detected": has_dangerous,
                    "sensitive_info_detected": has_sensitive,
                    "reasons": reasons,
                    "content_sample": content[:200] + "..." if len(content) > 200 else content
                }
            )
        except Exception as e:
            logger.error(f"Failed to log security scan: {e}")

    def is_content_safe(self, content: str, user_id: str) -> bool:
        result = self.scan_content(content, user_id)
        return not result["needs_review"]
