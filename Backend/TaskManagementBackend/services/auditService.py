"""审计日志业务服务：后台操作留痕与审计日志分页查询。"""

import json

from sqlalchemy.orm import Session

from TaskManagementBackend.models import AuditLog
from TaskManagementBackend.repositories.adminRepository import AdminRepository
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.utils.paginationUtils import normalizePagination


class AuditService(BaseService):
    """审计服务：记录管理后台操作，分页查询审计日志。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化管理后台仓储。"""
        super().__init__(db)
        self.adminRepository = AdminRepository(db)

    def recordAuditLog(
        self,
        userId: int | None,
        action: str,
        detail: dict | None = None,
        ip: str | None = None,
    ) -> AuditLog:
        """写入一条审计日志（仅 flush，事务由调用方提交）。"""
        detailText = None
        if detail is not None:
            detailText = json.dumps(detail, ensure_ascii=False, default=str)
        auditLog = AuditLog(userId=userId, action=action, detail=detailText, ip=ip)
        self.db.add(auditLog)
        self.db.flush()
        return auditLog

    def listAuditLogs(self, page: int, pageSize: int) -> dict:
        """分页查询审计日志（按时间倒序）。"""
        normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
        auditLogs, total = self.adminRepository.listAuditLogsPage(
            normalizedPage, normalizedPageSize
        )
        return {
            "items": [buildAuditLogItem(auditLog) for auditLog in auditLogs],
            "total": total,
            "page": normalizedPage,
            "pageSize": normalizedPageSize,
        }


def buildAuditLogItem(auditLog: AuditLog) -> dict:
    """把审计日志实体转换为接口响应字典。"""
    return {
        "id": auditLog.id,
        "userId": auditLog.userId,
        "operatorName": auditLog.operatorName,
        "action": auditLog.action,
        "detail": auditLog.detail,
        "ip": auditLog.ip,
        "createdAt": auditLog.createdAt,
    }
