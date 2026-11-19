"""协作模块 Pydantic 请求/响应模型。

字段命名与 Frontend/src/types/collaboration.ts 完全一致（camelCase）：
CollaborationUnit、CollaborationItem、CollaborationDirectoryItem、CollaborationUnitCandidate、
CollaborationTaskItem、CollaborationTaskDetail 及各请求体。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from TaskManagementBackend.models.enums import (
    AcceptanceMode,
    TaskPriority,
    TeamRole,
)
from TaskManagementBackend.schemas.taskSchema import ReviewRecordResponse, TaskItemResponse


class CollaborationUnitResponse(BaseModel):
    """协作单位：TeamId + SubTeamId 唯一确定一个单位（subTeamId 为空表示团队本级）。"""

    teamId: int
    teamName: str
    subTeamId: int | None = None
    subTeamName: str | None = None
    unitName: str


class CollaborationItemResponse(BaseModel):
    """协作关系项响应：双方单位、对接人、状态与当前用户可执行动作。"""

    id: int
    initiatorUnit: CollaborationUnitResponse
    targetUnit: CollaborationUnitResponse
    initiatorLiaisonUserId: int | None = None
    initiatorLiaisonNickname: str | None = None
    targetLiaisonUserId: int | None = None
    targetLiaisonNickname: str | None = None
    status: Literal["pending", "active", "rejected", "ended"]
    message: str | None = None
    rejectComment: str | None = None
    createdByName: str
    createdAt: datetime
    updatedAt: datetime
    canConfirm: bool
    canEnd: bool
    canCreateTask: bool
    myUnitRole: Literal["initiator", "target", "both"] | None = None


class CollaborationDirectorySubTeamItemResponse(BaseModel):
    """协作目录中的子团队摘要。"""

    subTeamId: int
    name: str
    memberCount: int
    leaderNickname: str | None = None


class CollaborationDirectoryItemResponse(BaseModel):
    """可申请协作的团队目录项（仅已认证团队）。"""

    teamId: int
    teamName: str
    description: str | None = None
    memberCount: int
    subTeams: list[CollaborationDirectorySubTeamItemResponse]


class CreateCollaborationRequest(BaseModel):
    """发起协作申请请求体：发起方单位、接收方单位与发起方对接人。"""

    initiatorTeamId: int = Field(gt=0, description="Initiating team ID")
    initiatorSubTeamId: int | None = Field(default=None, gt=0, description="Initiating sub-team ID (omit for team level)")
    targetTeamId: int = Field(gt=0, description="Receiving team ID")
    targetSubTeamId: int | None = Field(default=None, gt=0, description="Receiving sub-team ID (omit for team level)")
    initiatorLiaisonUserId: int = Field(gt=0, description="Initiator liaison user ID (must be a member of the initiating unit)")
    message: str | None = Field(default=None, max_length=500, description="Request message")


class ConfirmCollaborationRequest(BaseModel):
    """确认/拒绝协作申请请求体：确认时必须指定接收方对接人。"""

    approved: bool = Field(description="Whether to approve the collaboration")
    targetLiaisonUserId: int | None = Field(default=None, gt=0, description="Receiver liaison user ID")
    comment: str | None = Field(default=None, max_length=500, description="Confirm or reject comment")


class EndCollaborationRequest(BaseModel):
    """结束协作请求体。"""

    comment: str | None = Field(default=None, max_length=500, description="Reason for ending")


class CollaborationListQuery(BaseModel):
    """协作关系列表查询参数。"""

    status: Literal["pending", "active", "rejected", "ended"] | None = None
    teamId: int | None = Field(default=None, gt=0, description="Filter by involved team")
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=100)


class CollaborationUnitCandidateResponse(BaseModel):
    """协作单位候选成员：用于选择对接人与指派执行人。"""

    userId: int
    username: str
    nickname: str
    avatar: str | None = None
    levelName: str
    levelOrder: int
    role: TeamRole


class CreateCollaborationTaskRequest(BaseModel):
    """创建协作任务请求体：任务基础字段（不含分配对象，由接收方对接人确认时指派）。"""

    title: str = Field(min_length=2, max_length=200, description="Task title")
    description: str | None = Field(default=None, max_length=5000, description="Task description")
    priority: TaskPriority = Field(description="Priority")
    dueAt: datetime | None = Field(default=None, description="Due date")
    acceptanceMode: AcceptanceMode = Field(description="Acceptance mode")


class ConfirmCollaborationTaskRequest(BaseModel):
    """接收方对接人确认/拒绝协作任务请求体：确认时必须指定 1-N 名执行人。"""

    approved: bool = Field(description="Whether to accept the task")
    assigneeUserIds: list[int] | None = Field(default=None, max_length=100, description="Assignee user IDs")
    comment: str | None = Field(default=None, max_length=2000, description="Accept or reject comment")


class ReviewCollaborationTaskRequest(BaseModel):
    """协作任务审核请求体（接收方/发起方共用）。"""

    assignmentUserId: int = Field(gt=0, description="User ID of the assignee being reviewed")
    approved: bool = Field(description="Whether to approve")
    comment: str | None = Field(default=None, max_length=2000, description="Review comment")


class CollaborationTaskItemResponse(TaskItemResponse):
    """协作任务列表项：在任务字段基础上追加双方单位与双审核权限标记。"""

    sourceUnit: CollaborationUnitResponse
    targetUnit: CollaborationUnitResponse
    canConfirmTask: bool
    canTargetReview: bool
    canSourceReview: bool


class CollaborationTaskDetailResponse(CollaborationTaskItemResponse):
    """协作任务详情：追加审核记录。"""

    reviews: list[ReviewRecordResponse]
