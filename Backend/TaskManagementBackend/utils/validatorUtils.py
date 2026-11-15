"""校验工具：用户名、密码、邮箱等基础格式校验（中文提示）。"""

import re

from TaskManagementBackend.core.exceptions import validationError

# 用户名：3-30 位字母、数字、下划线，必须以字母开头
USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,29}$")
# 邮箱：常见邮箱格式
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validateUsername(username: str) -> str:
    """校验并返回用户名；不合法抛出 400。"""
    normalized = (username or "").strip()
    if not USERNAME_PATTERN.match(normalized):
        raise validationError("Username must be 3-30 letters, digits, or underscores and start with a letter")
    return normalized


def validatePassword(password: str) -> str:
    """校验密码强度：6-64 位，至少包含字母和数字。"""
    normalized = password or ""
    if not 6 <= len(normalized) <= 64:
        raise validationError("Password must be 6-64 characters long")
    if not re.search(r"[A-Za-z]", normalized) or not re.search(r"\d", normalized):
        raise validationError("Password must contain both letters and digits")
    return normalized


def validateEmail(email: str | None) -> str | None:
    """校验邮箱（为空时允许），返回规范化小写邮箱。"""
    if email is None or not email.strip():
        return None
    normalized = email.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise validationError("Invalid email format")
    return normalized


def validateNickname(nickname: str) -> str:
    """校验昵称长度 1-50。"""
    normalized = (nickname or "").strip()
    if not 1 <= len(normalized) <= 50:
        raise validationError("Nickname must be 1-50 characters long")
    return normalized
