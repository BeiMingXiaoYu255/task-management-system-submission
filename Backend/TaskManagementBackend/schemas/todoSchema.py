"""待办模块 Pydantic 数据模型：待办列表查询、待办项与统计响应结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from TaskManagementBackend.models.enums import AssignmentStatus, TaskPriority


class TodoListQuery(BaseModel):
    """我的待办列表查询参数：status 不传时表示全部未归档待办。"""

    status: AssignmentStatus | None = None
    priority: TaskPriority | None = None
    teamId: int | None = None
    keyword: str | None = Field(default=None, max_length=100)
    sortBy: Literal["priority", "dueAt", "createdAt"] = "createdAt"
    sortOrder: Literal["asc", "desc"] = "desc"
    includeArchived: bool = False
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=100)


class TodoItemResponse(BaseModel):
    """待办列表项响应结构。"""

    assignmentId: int
    taskId: int
    teamId: int
    teamName: str
    title: str
    description: str | None = None
    priority: TaskPriority
    taskStatus: str
    assignmentStatus: str
    dueAt: datetime | None = None
    createdByName: str
    acceptedAt: datetime | None = None
    createdAt: datetime
    overdue: bool


class TodoStatsResponse(BaseModel):
    """待办统计响应结构。"""

    total: int
    pendingAcceptance: int
    inProgress: int
    pendingReview: int
    archived: int
    overdue: int
