"""团队模块接口数据模型：团队、级别、成员、入团申请与候选成员。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from TaskManagementBackend.models.enums import (
    JoinMethod,
    JoinRequestStatus,
    TeamRole,
    TeamStatus,
)
from TaskManagementBackend.schemas.commonSchema import SkillItem


class CreateTeamRequest(BaseModel):
    """创建团队请求体。"""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    joinMethod: JoinMethod = JoinMethod.INVITE_ONLY


class UpdateTeamRequest(BaseModel):
    """修改团队请求体：仅提交需要修改的字段。"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    joinMethod: JoinMethod | None = None


class DeleteTeamRequest(BaseModel):
    """解散团队请求体：confirmName 必须与团队名称一致。"""

    confirmName: str = Field(min_length=1, max_length=100)


class TransferTeamRequest(BaseModel):
    """转让团队管理员请求体。"""

    newAdminUserId: int = Field(gt=0)


class JoinTeamRequest(BaseModel):
    """加入团队请求体：teamId 与 inviteCode 至少提供一个。"""

    teamId: int | None = Field(default=None, gt=0)
    inviteCode: str | None = Field(default=None, max_length=32)
    message: str | None = Field(default=None, max_length=255)


class SetMemberRoleRequest(BaseModel):
    """设置/撤销子管理员请求体。"""

    role: Literal["subAdmin", "member"]


class SetMemberLevelRequest(BaseModel):
    """调整成员级别请求体。"""

    levelId: int = Field(gt=0)


class SaveLevelRequest(BaseModel):
    """新建/修改团队级别请求体。"""

    name: str = Field(min_length=1, max_length=50)
    levelOrder: int = Field(ge=1, le=999)
    canCreateTask: bool = True


class GenerateInviteCodeRequest(BaseModel):
    """生成邀请码请求体：expiresInHours 为 null 表示永不过期，maxUses=0 表示不限次数。"""

    expiresInHours: int | None = Field(default=24, ge=1, le=8760)
    maxUses: int | None = Field(default=0, ge=0, le=100000)


class HandleJoinRequestRequest(BaseModel):
    """审批入团申请请求体。"""

    action: Literal["approve", "reject"]


class TeamBriefResponse(BaseModel):
    """团队列表项响应。"""

    id: int
    name: str
    description: str | None = None
    status: TeamStatus
    joinMethod: JoinMethod
    createdBy: int | None = None
    memberCount: int
    createdAt: datetime


class TeamLevelResponse(BaseModel):
    """团队级别响应（含使用该级别的成员数）。"""

    id: int
    teamId: int
    name: str
    levelOrder: int
    canCreateTask: bool
    memberCount: int


class TeamMemberItemResponse(BaseModel):
    """团队成员列表项响应。"""

    id: int
    userId: int
    username: str
    nickname: str
    avatar: str | None = None
    role: TeamRole
    levelId: int
    levelName: str
    levelOrder: int
    joinedAt: datetime
    skills: list[SkillItem]


class TeamDetailResponse(TeamBriefResponse):
    """团队详情响应：团队信息 + 级别 + 成员 + 当前用户身份。"""

    inviteCode: str | None = None
    inviteExpiresAt: datetime | None = None
    levels: list[TeamLevelResponse]
    members: list[TeamMemberItemResponse]
    currentUserRole: TeamRole
    currentUserLevelOrder: int


class JoinTeamResultResponse(BaseModel):
    """加入团队结果响应。"""

    status: Literal["joined", "pending"]
    teamId: int
    teamName: str
    message: str


class JoinRequestItemResponse(BaseModel):
    """入团申请列表项响应。"""

    id: int
    teamId: int
    userId: int
    username: str
    nickname: str
    message: str | None = None
    status: JoinRequestStatus
    createdAt: datetime


class MemberCandidateItemResponse(BaseModel):
    """任务可选成员候选响应（含级别与技能）。"""

    userId: int
    username: str
    nickname: str
    avatar: str | None = None
    role: TeamRole
    levelId: int
    levelName: str
    levelOrder: int
    skills: list[SkillItem]
