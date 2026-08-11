"""Tests for ContentSecurityService."""

import pytest
from unittest.mock import patch, MagicMock
from src.services.content_security import ContentSecurityService


@pytest.fixture
def service():
    return ContentSecurityService()


@pytest.fixture(autouse=True)
def mock_audit_log():
    with patch('src.services.content_security.AuditLog.create') as mock_create:
        yield mock_create


@pytest.fixture(autouse=True)
def mock_get_session():
    with patch('src.services.content_security.get_session') as mock_session:
        mock_session.return_value = MagicMock()
        yield mock_session


def test_clean_content(service, mock_audit_log):
    content = "这是一段正常的教学内容，介绍Python基础语法。"
    result = service.scan_content(content, "user-123")
    assert result["needs_review"] == False
    assert result["contains_profanity"] == False
    assert result["contains_dangerous_content"] == False
    assert result["has_sensitive_info"] == False
    assert result["reasons"] == []


def test_content_with_dangerous_pattern(service, mock_audit_log):
    content = "本节介绍如何绕过防火墙进行网络注入攻击"
    result = service.scan_content(content, "user-123")
    assert result["needs_review"] == True
    assert result["contains_dangerous_content"] == True
    assert "包含危险内容模式" in result["reasons"][0]


def test_content_with_phone_number(service, mock_audit_log):
    content = "如有疑问请联系13800138000咨询"
    result = service.scan_content(content, "user-123")
    assert result["needs_review"] == True
    assert result["has_sensitive_info"] == True
    assert any("手机号" in r for r in result["reasons"])


def test_content_with_id_card(service, mock_audit_log):
    content = "您的身份证号是110101199001011234"
    result = service.scan_content(content, "user-123")
    assert result["needs_review"] == True
    assert result["has_sensitive_info"] == True
    assert any("身份证" in r for r in result["reasons"])


def test_is_content_safe(service, mock_audit_log):
    safe = service.is_content_safe("正常教学内容", "user-123")
    assert safe == True

    unsafe = service.is_content_safe("绕过安全机制", "user-123")
    assert unsafe == False


def test_scan_creates_audit_log(service, mock_audit_log):
    content = "正常教学内容"
    service.scan_content(content, "user-123")
    mock_audit_log.assert_called_once()
    call_kwargs = mock_audit_log.call_args
    assert call_kwargs.kwargs["action_type"] == "content_scanned"
    assert call_kwargs.kwargs["user_id"] == "user-123"
    assert call_kwargs.kwargs["details"]["content_length"] == len(content)


def test_dangerous_patterns_multiple(service, mock_audit_log):
    test_cases = [
        ("eval(代码执行)", "contains_dangerous_content"),
        ("破解密码教程", "contains_dangerous_content"),
        ("泄露密钥信息", "contains_dangerous_content"),
    ]
    for content, field in test_cases:
        result = service.scan_content(content, "user-123")
        assert result[field] == True, f"Expected {field}=True for content: {content}"
