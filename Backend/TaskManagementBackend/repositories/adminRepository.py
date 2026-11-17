"""管理后台数据访问层。

封装后台用户/团队分页、统计、审计日志查询，以及数据库表浏览与单条 SQL 执行。
表名由服务层按 ORM 元数据白名单校验后再传入，仓储内部使用反引号包裹表名。
"""

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload

from TaskManagementBackend.models import AuditLog, Task, Team, TeamMember, User
from TaskManagementBackend.models.enums import GlobalRole, TeamStatus
from TaskManagementBackend.utils.paginationUtils import normalizePagination


class AdminRepository:
    """管理后台仓储：后台列表、统计计数、审计日志与数据库直管操作。"""

    def __init__(self, db: Session) -> None:
        """注入请求级数据库会话。"""
        self.db = db

    def listUsersPage(
        self,
        keyword: str | None,
        globalRole: GlobalRole | None,
        isActive: bool | None,
        page: int,
        pageSize: int,
    ) -> tuple[list[User], int]:
        """后台用户分页查询：支持关键字（用户名/昵称/邮箱）、全局角色、启用状态过滤。"""
        normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
        conditions = []
        if keyword and keyword.strip():
            likePattern = f"%{keyword.strip()}%"
            conditions.append(
                User.username.like(likePattern)
                | User.nickname.like(likePattern)
                | User.email.like(likePattern)
            )
        if globalRole is not None:
            conditions.append(User.globalRole == globalRole)
        if isActive is not None:
            conditions.append(User.isActive == isActive)
        countStatement = select(func.count()).select_from(User).where(*conditions)
        total = int(self.db.execute(countStatement).scalar_one())
        statement = (
            select(User)
            .where(*conditions)
            .order_by(User.id.asc())
            .offset((normalizedPage - 1) * normalizedPageSize)
            .limit(normalizedPageSize)
        )
        return list(self.db.execute(statement).scalars()), total

    def countMembershipsByUserIds(self, userIds: list[int]) -> dict[int, int]:
        """统计多个用户各自加入的团队数，返回 {用户主键: 团队数}。"""
        if not userIds:
            return {}
        statement = (
            select(TeamMember.userId, func.count())
            .where(TeamMember.userId.in_(userIds))
            .group_by(TeamMember.userId)
        )
        return {int(userId): int(count) for userId, count in self.db.execute(statement).all()}

    def listTeamsPage(
        self,
        keyword: str | None,
        status: TeamStatus | None,
        page: int,
        pageSize: int,
    ) -> tuple[list[Team], int]:
        """后台团队分页查询：支持团队名关键字与认证状态过滤，并预加载创建者。"""
        normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
        conditions = []
        if keyword and keyword.strip():
            conditions.append(Team.name.like(f"%{keyword.strip()}%"))
        if status is not None:
            conditions.append(Team.status == status)
        countStatement = select(func.count()).select_from(Team).where(*conditions)
        total = int(self.db.execute(countStatement).scalar_one())
        statement = (
            select(Team)
            .options(joinedload(Team.creator))
            .where(*conditions)
            .order_by(Team.id.asc())
            .offset((normalizedPage - 1) * normalizedPageSize)
            .limit(normalizedPageSize)
        )
        return list(self.db.execute(statement).scalars().unique()), total

    def countMembersByTeamIds(self, teamIds: list[int]) -> dict[int, int]:
        """统计多个团队的成员数量。"""
        if not teamIds:
            return {}
        statement = (
            select(TeamMember.teamId, func.count())
            .where(TeamMember.teamId.in_(teamIds))
            .group_by(TeamMember.teamId)
        )
        return {int(teamId): int(count) for teamId, count in self.db.execute(statement).all()}

    def countTasksByTeamIds(self, teamIds: list[int]) -> dict[int, int]:
        """统计多个团队的任务数量（含已取消与已归档任务）。"""
        if not teamIds:
            return {}
        statement = (
            select(Task.teamId, func.count())
            .where(Task.teamId.in_(teamIds))
            .group_by(Task.teamId)
        )
        return {int(teamId): int(count) for teamId, count in self.db.execute(statement).all()}

    def listAuditLogsPage(self, page: int, pageSize: int) -> tuple[list[AuditLog], int]:
        """审计日志分页查询，按操作时间倒序并预加载操作人。"""
        normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
        total = int(self.db.execute(select(func.count()).select_from(AuditLog)).scalar_one())
        statement = (
            select(AuditLog)
            .options(joinedload(AuditLog.operator))
            .order_by(AuditLog.id.desc())
            .offset((normalizedPage - 1) * normalizedPageSize)
            .limit(normalizedPageSize)
        )
        return list(self.db.execute(statement).scalars().unique()), total

    def countUsers(self) -> int:
        """统计用户总数。"""
        return int(self.db.execute(select(func.count()).select_from(User)).scalar_one())

    def countActiveUsers(self) -> int:
        """统计启用状态的用户数量。"""
        statement = select(func.count()).select_from(User).where(User.isActive.is_(True))
        return int(self.db.execute(statement).scalar_one())

    def countTeams(self) -> int:
        """统计团队总数。"""
        return int(self.db.execute(select(func.count()).select_from(Team)).scalar_one())

    def countPendingTeams(self) -> int:
        """统计待认证团队数量。"""
        statement = (
            select(func.count()).select_from(Team).where(Team.status == TeamStatus.PENDING)
        )
        return int(self.db.execute(statement).scalar_one())

    def countTasks(self) -> int:
        """统计任务总数。"""
        return int(self.db.execute(select(func.count()).select_from(Task)).scalar_one())

    def countTableRows(self, tableName: str) -> int:
        """统计指定数据表的行数（表名已由服务层白名单校验）。"""
        return int(self.db.execute(text(f"SELECT COUNT(*) FROM `{tableName}`")).scalar_one())

    def fetchTableRows(
        self, tableName: str, page: int, pageSize: int
    ) -> tuple[list[str], list[dict], int, int, int]:
        """分页浏览数据表内容，返回 (列名, 行字典, 总数, 规范化页码, 规范化页大小)。"""
        normalizedPage, normalizedPageSize = normalizePagination(page, pageSize)
        total = self.countTableRows(tableName)
        result = self.db.execute(
            text(f"SELECT * FROM `{tableName}` LIMIT :limit OFFSET :offset"),
            {"limit": normalizedPageSize, "offset": (normalizedPage - 1) * normalizedPageSize},
        )
        columns = [str(column) for column in result.keys()]
        rows = [dict(zip(columns, tuple(row))) for row in result.fetchall()]
        return columns, rows, total, normalizedPage, normalizedPageSize

    def executeSelectStatement(self, sql: str) -> tuple[list[str], list[dict]]:
        """执行只读 SQL 并返回列名与行字典列表。"""
        result = self.db.execute(text(sql))
        columns = [str(column) for column in result.keys()]
        rows = [dict(zip(columns, tuple(row))) for row in result.fetchall()]
        return columns, rows

    def executeWriteStatement(self, sql: str) -> int:
        """执行写类 DML 语句并返回受影响行数（事务由服务层提交）。"""
        result = self.db.execute(text(sql))
        return int(result.rowcount or 0)
