"""管理后台接口数据模型：用户/团队管理、数据库直管、审计日志与概览。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from TaskManagementBackend.models.enums import GlobalRole, JoinMethod, TeamStatus


class SetGlobalRoleRequest(BaseModel):
    """设置/取消全局管理员请求体（仅超级用户可用）。"""

    globalRole: Literal["globalAdmin", "user"]


class SetUserStatusRequest(BaseModel):
    """启用/禁用用户请求体。"""

    isActive: bool


class CertifyTeamRequest(BaseModel):
    """团队认证审核请求体。"""

    approved: bool


class ExecuteSqlRequest(BaseModel):
    """执行单条 DML 请求体：必须显式 confirm=true。"""

    sql: str = Field(min_length=1, max_length=10000)
    confirm: bool = False


class AdminUserItemResponse(BaseModel):
    """管理后台用户列表项。"""

    id: int
    username: str
    nickname: str
    email: str | None = None
    globalRole: GlobalRole
    isActive: bool
    teamCount: int
    createdAt: datetime


class AdminTeamItemResponse(BaseModel):
    """管理后台团队列表项。"""

    id: int
    name: str
    status: TeamStatus
    joinMethod: JoinMethod
    createdBy: int | None = None
    creatorName: str
    memberCount: int
    taskCount: int
    createdAt: datetime


class DatabaseTableInfoResponse(BaseModel):
    """数据库表清单项。"""

    tableName: str
    rowCount: int


class DatabaseRowsResponse(BaseModel):
    """数据表分页浏览结果（敏感列已脱敏）。"""

    tableName: str
    columns: list[str]
    rows: list[dict]
    total: int
    page: int
    pageSize: int


class ExecuteSqlResultResponse(BaseModel):
    """执行单条 SQL 的结果。"""

    executed: bool
    statementType: str
    affectedRows: int
    rows: list[dict]


class AuditLogItemResponse(BaseModel):
    """审计日志列表项。"""

    id: int
    userId: int | None = None
    operatorName: str
    action: str
    detail: str | None = None
    ip: str | None = None
    createdAt: datetime


class AdminOverviewResponse(BaseModel):
    """管理后台概览数据。"""

    userCount: int
    activeUserCount: int
    teamCount: int
    pendingTeamCount: int
    taskCount: int
    databaseName: str
