"""身份认证接口数据模型：注册/登录/当前用户/修改密码。"""

from datetime import datetime

from pydantic import BaseModel, Field

from TaskManagementBackend.models.enums import TeamRole, TeamStatus
from TaskManagementBackend.schemas.userSchema import UserDetailResponse


class RegisterRequest(BaseModel):
    """注册请求体：用户名 3-30 位、密码 6-64 位、昵称 1-50 字。"""

    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6, max_length=64)
    nickname: str = Field(min_length=1, max_length=50)
    email: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    """登录请求体。"""

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=64)


class ChangePasswordRequest(BaseModel):
    """修改密码请求体（需提供旧密码）。"""

    oldPassword: str = Field(min_length=1, max_length=64)
    newPassword: str = Field(min_length=6, max_length=64)


class TeamMembershipResponse(BaseModel):
    """当前用户在某团队中的身份信息。"""

    teamId: int
    teamName: str
    teamStatus: TeamStatus
    role: TeamRole
    levelId: int
    levelName: str
    levelOrder: int
    canCreateTask: bool
    joinedAt: datetime


class CurrentUserResponse(BaseModel):
    """当前用户信息：用户资料 + 各团队身份。"""

    user: UserDetailResponse
    teams: list[TeamMembershipResponse]


class AuthResponse(BaseModel):
    """登录/注册响应：token + 当前用户。"""

    token: str
    user: CurrentUserResponse
