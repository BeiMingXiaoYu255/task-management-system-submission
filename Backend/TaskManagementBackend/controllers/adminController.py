"""管理后台接口控制器：用户/团队管理、数据库直管、审计日志与概览。

全部接口要求全局管理员或超级用户身份；设置全局角色仅超级用户可用。
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import (
    getClientIp,
    requireGlobalAdmin,
    requireSuperAdmin,
)
from TaskManagementBackend.models import User
from TaskManagementBackend.models.enums import GlobalRole, TeamStatus
from TaskManagementBackend.schemas.adminSchema import (
    AdminOverviewResponse,
    AdminTeamItemResponse,
    AdminUserItemResponse,
    AuditLogItemResponse,
    CertifyTeamRequest,
    DatabaseRowsResponse,
    DatabaseTableInfoResponse,
    ExecuteSqlRequest,
    ExecuteSqlResultResponse,
    SetGlobalRoleRequest,
    SetUserStatusRequest,
)
from TaskManagementBackend.schemas.commonSchema import PageResult
from TaskManagementBackend.services.adminService import AdminService
from TaskManagementBackend.services.databaseAdminService import DatabaseAdminService

# 路由前缀由主应用统一追加 /api/v1
router = APIRouter(tags=["Admin Console"], prefix="/admin")


@router.get(
    "/users", response_model=PageResult[AdminUserItemResponse], summary="List users (admin)"
)
def listAdminUsers(
    keyword: str | None = Query(default=None, description="Username, nickname, or email keyword"),
    globalRole: GlobalRole | None = Query(default=None, description="Global role"),
    isActive: bool | None = Query(default=None, description="Whether active"),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    operator: User = Depends(requireGlobalAdmin),
    db: Session = Depends(getDb),
) -> dict:
    """后台用户分页列表，支持关键字、全局角色与启用状态过滤。"""
    return AdminService(db).listUsers(keyword, globalRole, isActive, page, pageSize)


@router.put(
    "/users/{userId}/global-role",
    response_model=AdminUserItemResponse,
    summary="Set or revoke global admin (Super Admin only)",
)
def setGlobalRole(
    userId: int,
    payload: SetGlobalRoleRequest,
    request: Request,
    operator: User = Depends(requireSuperAdmin),
    db: Session = Depends(getDb),
) -> dict:
    """设置或取消全局管理员，仅超级用户可操作。"""
    return AdminService(db).setGlobalRole(
        operator, userId, payload.globalRole, getClientIp(request)
    )


@router.put(
    "/users/{userId}/status", response_model=AdminUserItemResponse, summary="Activate or deactivate user"
)
def setUserStatus(
    userId: int,
    payload: SetUserStatusRequest,
    request: Request,
    operator: User = Depends(requireGlobalAdmin),
    db: Session = Depends(getDb),
) -> dict:
    """启用或禁用用户账号（不能操作超级用户与自己）。"""
    return AdminService(db).setUserStatus(
        operator, userId, payload.isActive, getClientIp(request)
    )


@router.get(
    "/teams", response_model=PageResult[AdminTeamItemResponse], summary="List teams (admin)"
)
def listAdminTeams(
    keyword: str | None = Query(default=None, description="Team name keyword"),
    status: TeamStatus | None = Query(default=None, description="Certification status"),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    operator: User = Depends(requireGlobalAdmin),
    db: Session = Depends(getDb),
) -> dict:
    """后台团队分页列表，支持关键字与认证状态过滤。"""
    return AdminService(db).listTeams(keyword, status, page, pageSize)


@router.put(
    "/teams/{teamId}/certification",
    response_model=AdminTeamItemResponse,
    summary="Review team certification",
)
def certifyTeam(
    teamId: int,
    payload: CertifyTeamRequest,
    request: Request,
    operator: User = Depends(requireGlobalAdmin),
    db: Session = Depends(getDb),
) -> dict:
    """团队认证审核：通过置为 active，驳回置为 rejected。"""
    return AdminService(db).certifyTeam(
        operator, teamId, payload.approved, getClientIp(request)
    )


@router.get(
    "/database/tables",
    response_model=list[DatabaseTableInfoResponse],
    summary="List database tables",
)
def listDatabaseTables(
    operator: User = Depends(requireGlobalAdmin), db: Session = Depends(getDb)
) -> list[dict]:
    """返回全部业务数据表及行数。"""
    return DatabaseAdminService(db).listTables()


@router.get(
    "/database/tables/{tableName}/rows",
    response_model=DatabaseRowsResponse,
    summary="Browse table rows (masked)",
)
def getDatabaseRows(
    tableName: str,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    operator: User = Depends(requireGlobalAdmin),
    db: Session = Depends(getDb),
) -> dict:
    """分页浏览指定数据表内容，敏感列脱敏。"""
    return DatabaseAdminService(db).getTableRows(tableName, page, pageSize)


@router.post(
    "/database/execute",
    response_model=ExecuteSqlResultResponse,
    summary="Execute single DML statement",
)
def executeDatabaseSql(
    payload: ExecuteSqlRequest,
    request: Request,
    operator: User = Depends(requireGlobalAdmin),
    db: Session = Depends(getDb),
) -> dict:
    """执行单条 SELECT/INSERT/UPDATE/DELETE，SELECT 返回行数据，全程写审计日志。"""
    return DatabaseAdminService(db).executeSql(
        operator, payload.sql, payload.confirm, getClientIp(request)
    )


@router.get(
    "/audit-logs", response_model=PageResult[AuditLogItemResponse], summary="List audit logs"
)
def listAuditLogs(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    operator: User = Depends(requireGlobalAdmin),
    db: Session = Depends(getDb),
) -> dict:
    """分页查询管理后台审计日志（按时间倒序）。"""
    return AdminService(db).listAuditLogs(page, pageSize)


@router.get("/overview", response_model=AdminOverviewResponse, summary="Admin console overview")
def getAdminOverview(
    operator: User = Depends(requireGlobalAdmin), db: Session = Depends(getDb)
) -> dict:
    """返回用户、团队、任务数量与数据库库名等概览数据。"""
    return AdminService(db).getOverview()