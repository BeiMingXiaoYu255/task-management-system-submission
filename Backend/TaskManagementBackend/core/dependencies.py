"""FastAPI 依赖注入：当前用户、管理员权限、客户端 IP。"""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.exceptions import AppException, forbidden, unauthorized
from TaskManagementBackend.core.security import decodeAccessToken, isTokenBlacklisted
from TaskManagementBackend.models import User
from TaskManagementBackend.models.enums import GlobalRole

# HTTP Bearer 认证方案：auto_error=False 以便自定义错误响应
bearerScheme = HTTPBearer(auto_error=False)


def getClientIp(request: Request) -> str:
    """获取客户端 IP：优先代理头 X-Forwarded-For，其次直连地址。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def getCurrentUser(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearerScheme),
    db: Session = Depends(getDb),
) -> User:
    """解析 Bearer token 并返回当前登录用户。

    校验顺序：token 存在性 → JWT 合法性与过期 → 黑名单 → 用户存在性与启用状态。
    """
    if credentials is None or not credentials.credentials:
        raise unauthorized()
    token = credentials.credentials
    try:
        tokenPayload = decodeAccessToken(token)
    except ExpiredSignatureError:
        raise AppException("TOKEN_EXPIRED", "Session expired. Please sign in again.", 401)
    except InvalidTokenError:
        raise AppException("INVALID_CREDENTIALS", "Invalid credentials. Please sign in again.", 401)
    if isTokenBlacklisted(tokenPayload):
        raise AppException("TOKEN_EXPIRED", "Session is no longer valid. Please sign in again.", 401)
    userId = int(tokenPayload.get("sub", 0))
    user = db.get(User, userId)
    if user is None:
        raise unauthorized("User not found")
    if not user.isActive:
        raise AppException("ACCOUNT_DISABLED", "This account has been disabled", 403)
    return user


def requireGlobalAdmin(currentUser: User = Depends(getCurrentUser)) -> User:
    """要求全局管理员或超级用户身份。"""
    if currentUser.globalRole not in (GlobalRole.SUPER_ADMIN, GlobalRole.GLOBAL_ADMIN):
        raise forbidden("Only global admins can access this feature")
    return currentUser


def requireSuperAdmin(currentUser: User = Depends(getCurrentUser)) -> User:
    """要求超级用户身份。"""
    if currentUser.globalRole != GlobalRole.SUPER_ADMIN:
        raise forbidden("Only super admins can perform this action")
    return currentUser
