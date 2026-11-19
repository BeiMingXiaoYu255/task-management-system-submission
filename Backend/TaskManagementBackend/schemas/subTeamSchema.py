"""子团队模块 Pydantic 请求/响应模型。

字段命名与 Frontend/src/types/collaboration.ts 中的 SubTeamItem / SubTeamMemberItem /
SubTeamDetail / SaveSubTeamPayload 完全一致（camelCase）。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateSubTeamRequest(BaseModel):
    """创建子团队请求体：名称、简介、子负责人与初始成员（成员必须是父团队成员）。"""

    name: str = Field(min_length=1, max_length=100, description="Sub-team name")
    description: str | None = Field(default=None, max_length=2000, description="Sub-team description")
    leaderUserId: int | None = Field(default=None, gt=0, description="Sub-team lead user ID")
    memberUserIds: list[int] | None = Field(default=None, max_length=200, description="Initial member user IDs")


class UpdateSubTeamRequest(BaseModel):
    """修改子团队请求体：仅提交需要修改的字段，未提交字段保持不变。"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="Sub-team name")
    description: str | None = Field(default=None, max_length=2000, description="Sub-team description")
    leaderUserId: int | None = Field(default=None, gt=0, description="Sub-team lead user ID (team admin only)")


class SetSubTeamMembersRequest(BaseModel):
    """覆盖式设置子团队成员请求体。"""

    userIds: list[int] = Field(default_factory=list, max_length=200, description="Member user IDs")


class SubTeamMemberItemResponse(BaseModel):
    """子团队成员项响应：含父团队级别信息与是否子负责人标记。"""

    userId: int
    username: str
    nickname: str
    avatar: str | None = None
    levelName: str
    levelOrder: int
    isLeader: bool


class SubTeamItemResponse(BaseModel):
    """子团队列表项响应：含负责人昵称、成员数与当前用户角色。"""

    id: int
    parentTeamId: int
    name: str
    description: str | None = None
    leaderUserId: int | None = None
    leaderNickname: str | None = None
    memberCount: int
    createdAt: datetime
    myRole: Literal["admin", "leader", "member"] | None = None


class SubTeamDetailResponse(SubTeamItemResponse):
    """子团队详情响应：在列表项基础上追加成员列表。"""

    members: list[SubTeamMemberItemResponse]
