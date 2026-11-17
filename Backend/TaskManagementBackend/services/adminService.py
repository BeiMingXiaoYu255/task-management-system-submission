"""管理后台业务服务：用户/团队管理、团队认证审核、概览统计与审计日志查询。"""

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.core.exceptions import forbidden, notFound, validationError
from TaskManagementBackend.models import Team, User
from TaskManagementBackend.models.enums import GlobalRole, TeamStatus
from TaskManagementBackend.repositories.adminRepository import AdminRepository
from TaskManagementBackend.services.auditService import AuditService
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.utils.paginationUtils import normalizePagination


def buildAdminUserItem(user: User, teamCount: int) -> dict:
    """把用户实体转换为管理后台用户列表项。"""
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "globalRole": user.globalRole,
        "isActive": bool(user.isActive),
        "teamCount": teamCount,
        "createdAt": user.createdAt,
    }


def buildAdminTeamItem(team: Team, memberCount: int, taskCount: int) -> dict:
    """把团队实体转换为管理后台团队列表项。"""
    creator = team.creator
    return {
        "id": team.id,
        "name": team.name,
        "status": team.status,
        "joinMethod": team.joinMethod,
        "createdBy": team.createdBy,
        "creatorName": creator.nickname if creator is not None else "Deleted User",
        "memberCount": memberCount,
        "taskCount": taskCount,
        "createdAt": team.createdAt,
    }


class AdminService(BaseService):
    """管理后台服务：用户与团队管理、认证审核、概览与审计日志。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化管理后台仓储与审计服务。"""
        super().__init__(db)
        self.adminRepository = AdminRepository(db)
        self.auditService = AuditService(db)

    def listUsers(
        self,
        keyword: str | None,
        globalRole: GlobalRole | None,
        isActive: bool | None,
        page: int,
        pageSize: int,
    ) -> dict:
        """后台用户分页列表：支持关键字、全局角色与启用状态过滤。"""
        normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
        users, total = self.adminRepository.listUsersPage(
            keyword, globalRole, isActive, normalizedPage, normalizedPageSize
        )
        teamCounts = self.adminRepository.countMembershipsByUserIds(
            [user.id for user in users]
        )
        return {
            "items": [
                buildAdminUserItem(user, teamCounts.get(user.id, 0)) for user in users
            ],
            "total": total,
            "page": normalizedPage,
            "pageSize": normalizedPageSize,
        }

    def setGlobalRole(
        self,
        operator: User,
        userId: int,
        globalRoleValue: str,
        clientIp: str,
    ) -> dict:
        """设置/取消全局管理员：仅超级用户可操作，且不能修改超级用户角色。"""
        if operator.globalRole != GlobalRole.SUPER_ADMIN:
            raise forbidden("Only the Super Admin can set global admins")
        targetUser = self.db.get(User, userId)
        if targetUser is None:
            raise notFound("User not found")
        if targetUser.globalRole == GlobalRole.SUPER_ADMIN:
            raise forbidden("The Super Admin global role cannot be changed")
        newGlobalRole = (
            GlobalRole.GLOBAL_ADMIN if globalRoleValue == "globalAdmin" else GlobalRole.USER
        )
        targetUser.globalRole = newGlobalRole
        self.auditService.recordAuditLog(
            operator.id,
            "admin.user.setGlobalRole",
            {"userId": userId, "globalRole": newGlobalRole.value},
            clientIp,
        )
        self.commit()
        teamCount = self.adminRepository.countMembershipsByUserIds([userId]).get(userId, 0)
        return buildAdminUserItem(targetUser, teamCount)

    def setUserStatus(
        self, operator: User, userId: int, isActive: bool, clientIp: str
    ) -> dict:
        """启用/禁用用户：不能禁用超级用户，也不能修改自己的账号状态。"""
        targetUser = self.db.get(User, userId)
        if targetUser is None:
            raise notFound("User not found")
        if targetUser.globalRole == GlobalRole.SUPER_ADMIN:
            raise forbidden("The Super Admin account status cannot be changed")
        if targetUser.id == operator.id:
            raise validationError("You cannot change your own account status")
        targetUser.isActive = isActive
        self.auditService.recordAuditLog(
            operator.id,
            "admin.user.setStatus",
            {"userId": userId, "isActive": isActive},
            clientIp,
        )
        self.commit()
        teamCount = self.adminRepository.countMembershipsByUserIds([userId]).get(userId, 0)
        return buildAdminUserItem(targetUser, teamCount)

    def listTeams(
        self,
        keyword: str | None,
        status: TeamStatus | None,
        page: int,
        pageSize: int,
    ) -> dict:
        """后台团队分页列表：支持关键字与认证状态过滤。"""
        normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
        teams, total = self.adminRepository.listTeamsPage(
            keyword, status, normalizedPage, normalizedPageSize
        )
        teamIds = [team.id for team in teams]
        memberCounts = self.adminRepository.countMembersByTeamIds(teamIds)
        taskCounts = self.adminRepository.countTasksByTeamIds(teamIds)
        return {
            "items": [
                buildAdminTeamItem(
                    team, memberCounts.get(team.id, 0), taskCounts.get(team.id, 0)
                )
                for team in teams
            ],
            "total": total,
            "page": normalizedPage,
            "pageSize": normalizedPageSize,
        }

    def certifyTeam(
        self, operator: User, teamId: int, approved: bool, clientIp: str
    ) -> dict:
        """团队认证审核：通过置为 active，驳回置为 rejected。"""
        team = self.db.get(Team, teamId)
        if team is None:
            raise notFound("Team not found")
        team.status = TeamStatus.ACTIVE if approved else TeamStatus.REJECTED
        self.auditService.recordAuditLog(
            operator.id,
            "admin.team.certification",
            {"teamId": teamId, "approved": approved},
            clientIp,
        )
        self.commit()
        memberCount = self.adminRepository.countMembersByTeamIds([teamId]).get(teamId, 0)
        taskCount = self.adminRepository.countTasksByTeamIds([teamId]).get(teamId, 0)
        return buildAdminTeamItem(team, memberCount, taskCount)

    def getOverview(self) -> dict:
        """管理后台概览统计：用户、团队、任务数量与数据库库名。"""
        databaseName = make_url(settings.databaseUrl).database or ""
        return {
            "userCount": self.adminRepository.countUsers(),
            "activeUserCount": self.adminRepository.countActiveUsers(),
            "teamCount": self.adminRepository.countTeams(),
            "pendingTeamCount": self.adminRepository.countPendingTeams(),
            "taskCount": self.adminRepository.countTasks(),
            "databaseName": databaseName,
        }

    def listAuditLogs(self, page: int, pageSize: int) -> dict:
        """审计日志分页列表。"""
        return self.auditService.listAuditLogs(page, pageSize)
