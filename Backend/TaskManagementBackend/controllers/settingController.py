"""系统设置接口控制器：界面设置、修改密码与注销账号。

修改密码与注销账号成功后，当前请求 token 会写入黑名单，迫使客户端重新登录。
"""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import bearerScheme, getCurrentUser
from TaskManagementBackend.core.security import blacklistAccessToken, decodeAccessToken
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.commonSchema import MessageResponse
from TaskManagementBackend.schemas.settingSchema import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    UpdateSettingsRequest,
    UserSettingsResponse,
)
from TaskManagementBackend.services.authService import AuthService
from TaskManagementBackend.services.settingService import SettingService

# 设置路由统一前缀 /settings
router = APIRouter(tags=["Settings"], prefix="/settings")


def blacklistCurrentToken(credentials: HTTPAuthorizationCredentials | None) -> None:
    """把当前请求 token 加入黑名单，使修改密码/注销账号后旧 token 立即失效。"""
    if credentials is None or not credentials.credentials:
        return
    try:
        blacklistAccessToken(decodeAccessToken(credentials.credentials))
    except InvalidTokenError:
        return


@router.get("", response_model=UserSettingsResponse, summary="Get Settings")
def getSettings(
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """读取界面设置；记录不存在时返回默认值并自动创建。"""
    return SettingService(db).getSettings(currentUser)


@router.put("", response_model=UserSettingsResponse, summary="Update Settings")
def updateSettings(
    payload: UpdateSettingsRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """修改主题、字号与字体族设置。"""
    return SettingService(db).updateSettings(currentUser, payload)


@router.put("/password", response_model=MessageResponse, summary="Change Password")
def changePassword(
    payload: ChangePasswordRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearerScheme),
) -> dict:
    """修改密码（与 /auth/password 等价）：复用 AuthService，成功后当前 token 失效。"""
    tokenText = credentials.credentials if credentials is not None else ""
    tokenPayload = decodeAccessToken(tokenText) if tokenText else {}
    AuthService(db).changePassword(currentUser, payload.oldPassword, payload.newPassword, tokenPayload)
    return {"message": "Password changed successfully. Please sign in again."}


@router.delete("/account", response_model=MessageResponse, summary="Delete Account")
def deleteAccount(
    payload: DeleteAccountRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearerScheme),
) -> dict:
    """注销账号：密码二次确认后软删除并清理关联数据，当前 token 立即失效。"""
    result = SettingService(db).deleteAccount(currentUser, payload.password)
    blacklistCurrentToken(credentials)
    return result