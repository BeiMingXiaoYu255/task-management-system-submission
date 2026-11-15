"""身份认证接口控制器：注册、登录、当前用户、注销与修改密码。

控制器只做参数接收与响应组装，全部业务逻辑在 AuthService 中实现。
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import (
    bearerScheme,
    getClientIp,
    getCurrentUser,
)
from TaskManagementBackend.core.exceptions import unauthorized
from TaskManagementBackend.core.security import decodeAccessToken
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.authSchema import (
    AuthResponse,
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)
from TaskManagementBackend.schemas.commonSchema import MessageResponse
from TaskManagementBackend.services.authService import AuthService

# 路由前缀由主应用统一追加 /api/v1
router = APIRouter(tags=["Authentication"], prefix="/auth")


def extractAccessToken(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearerScheme),
) -> str:
    """从 Authorization 请求头提取当前访问 token（注销/改密时加入黑名单）。"""
    if credentials is None or not credentials.credentials:
        raise unauthorized()
    return credentials.credentials


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register standard user",
)
def registerAccount(payload: RegisterRequest, db: Session = Depends(getDb)) -> dict:
    """注册普通用户：校验账号信息并自动登录，返回 token 与当前用户。"""
    _, token, currentUser = AuthService(db).registerUser(
        username=payload.username,
        password=payload.password,
        nickname=payload.nickname,
        email=payload.email,
    )
    return {"token": token, "user": currentUser}


@router.post("/login", response_model=AuthResponse, summary="User login")
def loginAccount(
    payload: LoginRequest, request: Request, db: Session = Depends(getDb)
) -> dict:
    """登录：校验账号密码与限流后签发 token。"""
    _, token, currentUser = AuthService(db).loginUser(
        payload.username, payload.password, getClientIp(request)
    )
    return {"token": token, "user": currentUser}


@router.get("/me", response_model=CurrentUserResponse, summary="Current user information")
def getCurrentUserInformation(
    currentUser: User = Depends(getCurrentUser), db: Session = Depends(getDb)
) -> dict:
    """返回当前用户完整资料与在各团队中的身份列表。"""
    return AuthService(db).getCurrentUserInfo(currentUser)


@router.post("/logout", response_model=MessageResponse, summary="Log out")
def logoutAccount(
    currentUser: User = Depends(getCurrentUser),
    accessToken: str = Depends(extractAccessToken),
    db: Session = Depends(getDb),
) -> dict:
    """退出登录：把当前 token 加入 Redis 黑名单，旧 token 立即失效。"""
    AuthService(db).logoutByToken(accessToken)
    return {"message": "Logged out successfully"}


@router.put("/password", response_model=MessageResponse, summary="Change password")
def changeAccountPassword(
    payload: ChangePasswordRequest,
    currentUser: User = Depends(getCurrentUser),
    accessToken: str = Depends(extractAccessToken),
    db: Session = Depends(getDb),
) -> dict:
    """修改密码：校验旧密码后更新哈希，当前 token 立即失效。"""
    tokenPayload = decodeAccessToken(accessToken)
    AuthService(db).changePassword(
        currentUser, payload.oldPassword, payload.newPassword, tokenPayload
    )
    return {"message": "Password changed successfully. Please sign in again."}
