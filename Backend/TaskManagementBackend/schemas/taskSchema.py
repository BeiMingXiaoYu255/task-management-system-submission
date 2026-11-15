"""任务模块 Pydantic 数据模型：创建/修改/审核请求与任务响应结构。

命名约定：请求体与响应结构均直接使用 camelCase 字段名，与前端
Frontend/src/types/task.ts 一一对应，避免 alias 转换带来的歧义。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from TaskManagementBackend.models.enums import (
    AcceptanceMode,
    AssignmentMode,
    AssignmentStatus,
    ReviewResult,
    TaskPriority,
    TaskStatus,
)

class CreateTaskRequest(BaseModel):
    """发布任务请求体：specific 模式传 targetUserIds，levelRange 模式传级别范围。"""

    title: str = Field(min_length=2, max_length=200, description="Task title")
    description: str | None = Field(default=None, max_length=5000, description="Task description")
    priority: TaskPriority = Field(description="Priority")
    dueAt: datetime | None = Field(default=None, description="Due date")
    assignmentMode: AssignmentMode = Field(description="Assignment mode")
    acceptanceMode: AcceptanceMode = Field(description="Acceptance mode")
    targetUserIds: list[int] | None = Field(default=None, max_length=100, description="Assigned members")
    targetLevelMin: int | None = Field(default=None, description="Minimum level")
    targetLevelMax: int | None = Field(default=None, description="Maximum level")
    # ===== v1.1 子团队与 AI 自动分配扩展 =====
    subTeamId: int | None = Field(default=None, description="Sub-team of the task (optional)")
    autoAssign: bool = Field(default=False, description="Whether AI selects the assignee automatically")
    requiredSkillNames: list[str] | None = Field(
        default=None, max_length=30, description="Required skill tags for AI auto-assignment"
    )


class AssignTaskMembersRequest(BaseModel):
    """手动指派执行人请求体：用于 AI 自动分配无匹配或管理员改派。"""

    userIds: list[int] = Field(min_length=1, max_length=100, description="Assignee user IDs")


class UpdateTaskRequest(BaseModel):
    """修改任务请求体：仅传需要修改的字段，未传字段保持不变。"""

    title: str | None = Field(default=None, min_length=2, max_length=200, description="Task title")
    description: str | None = Field(default=None, max_length=5000, description="Task description")
    priority: TaskPriority | None = Field(default=None, description="Priority")
    dueAt: datetime | None = Field(default=None, description="Due date")
    acceptanceMode: AcceptanceMode | None = Field(default=None, description="Acceptance mode")


class ReviewTaskRequest(BaseModel):
    """审核任务请求体：approved=true 归档，false 驳回重做。"""

    assignmentUserId: int = Field(description="User ID of the assignee being reviewed")
    approved: bool = Field(description="Whether approved")
    comment: str | None = Field(default=None, max_length=2000, description="Review comment")


class TaskListQuery(BaseModel):
    """团队任务列表查询参数。"""

    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    keyword: str | None = Field(default=None, max_length=100)
    createdBy: int | None = None
    assigneeId: int | None = None
    subTeamId: int | None = None
    sortBy: Literal["createdAt", "dueAt", "priority"] = "createdAt"
    sortOrder: Literal["asc", "desc"] = "desc"
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=100)


class MyTaskListQuery(TaskListQuery):
    """我的任务中心查询参数：role 区分我发布的 / 我参与的。"""

    role: Literal["created", "assigned"] | None = None
    teamId: int | None = None


class TaskAssignmentResponse(BaseModel):
    """任务分配（待办）项响应结构。"""

    id: int
    userId: int
    username: str
    nickname: str
    avatar: str | None = None
    status: AssignmentStatus
    acceptedAt: datetime | None = None
    submittedAt: datetime | None = None
    reviewedAt: datetime | None = None
    reviewedBy: int | None = None
    reviewComment: str | None = None
    # ===== v1.1 双审核与分配来源 =====
    reviewStage: str | None = None
    targetReviewedAt: datetime | None = None
    targetReviewerId: int | None = None
    targetReviewComment: str | None = None
    assignmentSource: str = "manual"


class ReviewRecordResponse(BaseModel):
    """审核记录响应结构。"""

    id: int
    taskId: int
    assignmentId: int
    reviewerId: int
    reviewerName: str
    result: ReviewResult
    comment: str | None = None
    createdAt: datetime


class TaskItemResponse(BaseModel):
    """任务列表项响应结构。"""

    id: int
    teamId: int
    teamName: str
    title: str
    description: str | None = None
    priority: TaskPriority
    status: TaskStatus
    assignmentMode: AssignmentMode
    acceptanceMode: AcceptanceMode
    targetLevelMin: int | None = None
    targetLevelMax: int | None = None
    dueAt: datetime | None = None
    createdBy: int | None = None
    createdByName: str
    createdAt: datetime
    updatedAt: datetime
    archivedAt: datetime | None = None
    assignments: list[TaskAssignmentResponse]
    myAssignment: TaskAssignmentResponse | None = None
    canReview: bool
    canEdit: bool
    canAssign: bool = False
    reviewCount: int
    # ===== v1.1 子团队/协作/AI 扩展字段 =====
    subTeamId: int | None = None
    subTeamName: str | None = None
    sourceTeamId: int | None = None
    sourceTeamName: str | None = None
    sourceSubTeamId: int | None = None
    sourceSubTeamName: str | None = None
    targetTeamId: int | None = None
    targetTeamName: str | None = None
    targetSubTeamId: int | None = None
    targetSubTeamName: str | None = None
    collaborationId: int | None = None
    collaborationPhase: str | None = None
    collaborationComment: str | None = None
    autoAssigned: bool = False
    requiredSkillNames: list[str] = []


class TaskDetailResponse(TaskItemResponse):
    """任务详情响应结构：在列表项基础上追加审核记录。"""

    reviews: list[ReviewRecordResponse]
