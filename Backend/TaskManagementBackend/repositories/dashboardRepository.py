"""仪表盘数据访问层：待办汇总、分布、近七日趋势与团队统计查询。"""

from datetime import datetime

from sqlalchemy import func, select

from TaskManagementBackend.models import Task, TaskAssignment, Team, TeamMember
from TaskManagementBackend.models.enums import AssignmentStatus, TaskStatus
from TaskManagementBackend.repositories.baseRepository import BaseRepository
from TaskManagementBackend.utils.timeUtils import getCurrentTime

# 未完成待办状态集合
ACTIVE_ASSIGNMENT_STATUSES = (
    AssignmentStatus.PENDING_ACCEPTANCE,
    AssignmentStatus.IN_PROGRESS,
    AssignmentStatus.PENDING_REVIEW,
)

# 未结束任务状态集合（用于团队开放任务数统计）
OPEN_TASK_STATUSES = (TaskStatus.PUBLISHED, TaskStatus.IN_PROGRESS, TaskStatus.PENDING_REVIEW)


class DashboardRepository(BaseRepository[Task]):
    """仪表盘仓储：聚合查询当前用户的待办与任务统计数据。"""

    model = Task

    def getAssignmentStatusCounts(self, userId: int, teamId: int | None = None) -> dict[str, int]:
        """按待办状态统计当前用户数量（不含已取消任务的待办）。"""
        statement = (
            select(TaskAssignment.status, func.count(TaskAssignment.id))
            .join(Task, TaskAssignment.taskId == Task.id)
            .where(TaskAssignment.userId == userId, Task.status != TaskStatus.CANCELLED)
        )
        if teamId is not None:
            statement = statement.where(Task.teamId == teamId)
        statement = statement.group_by(TaskAssignment.status)
        return {status.value: int(count) for status, count in self.db.execute(statement).all()}

    def countOverdueAssignments(self, userId: int, teamId: int | None = None) -> int:
        """统计当前用户已逾期且未归档的待办数量。"""
        statement = (
            select(func.count(TaskAssignment.id))
            .join(Task, TaskAssignment.taskId == Task.id)
            .where(
                TaskAssignment.userId == userId,
                Task.status != TaskStatus.CANCELLED,
                TaskAssignment.status != AssignmentStatus.ARCHIVED,
                Task.dueAt.is_not(None),
                Task.dueAt < getCurrentTime(),
            )
        )
        if teamId is not None:
            statement = statement.where(Task.teamId == teamId)
        return int(self.db.execute(statement).scalar_one())

    def getPriorityDistribution(self, userId: int, teamId: int | None = None) -> list[tuple[str, int]]:
        """按任务优先级统计当前用户未归档待办数量。"""
        statement = (
            select(Task.priority, func.count(TaskAssignment.id))
            .join(TaskAssignment, TaskAssignment.taskId == Task.id)
            .where(
                TaskAssignment.userId == userId,
                TaskAssignment.status != AssignmentStatus.ARCHIVED,
                Task.status != TaskStatus.CANCELLED,
            )
        )
        if teamId is not None:
            statement = statement.where(Task.teamId == teamId)
        statement = statement.group_by(Task.priority)
        return [(priority.value, int(count)) for priority, count in self.db.execute(statement).all()]

    def getStatusDistribution(self, userId: int, teamId: int | None = None) -> list[tuple[str, int]]:
        """按待办状态统计当前用户数量（含已归档，便于前端展示全貌）。"""
        statement = (
            select(TaskAssignment.status, func.count(TaskAssignment.id))
            .join(Task, TaskAssignment.taskId == Task.id)
            .where(TaskAssignment.userId == userId, Task.status != TaskStatus.CANCELLED)
        )
        if teamId is not None:
            statement = statement.where(Task.teamId == teamId)
        statement = statement.group_by(TaskAssignment.status)
        return [(status.value, int(count)) for status, count in self.db.execute(statement).all()]

    def countArchivedAssignments(
        self, userId: int, teamId: int | None = None, since: datetime | None = None
    ) -> int:
        """统计当前用户已归档待办数量；since 非空时只统计审核时间在该时间之后的记录。"""
        statement = (
            select(func.count(TaskAssignment.id))
            .join(Task, TaskAssignment.taskId == Task.id)
            .where(TaskAssignment.userId == userId, TaskAssignment.status == AssignmentStatus.ARCHIVED)
        )
        if teamId is not None:
            statement = statement.where(Task.teamId == teamId)
        if since is not None:
            statement = statement.where(TaskAssignment.reviewedAt >= since)
        return int(self.db.execute(statement).scalar_one())

    def getCreatedTaskTrend(
        self, userId: int, teamId: int | None, since: datetime
    ) -> dict[str, int]:
        """统计当前用户近七日每日创建的任务数量，返回 {'YYYY-MM-DD': 数量} 字典。"""
        statement = select(func.date(Task.createdAt), func.count(Task.id)).where(
            Task.createdBy == userId, Task.createdAt >= since
        )
        if teamId is not None:
            statement = statement.where(Task.teamId == teamId)
        statement = statement.group_by(func.date(Task.createdAt))
        return {str(day): int(count) for day, count in self.db.execute(statement).all()}

    def getCompletedAssignmentTrend(
        self, userId: int, teamId: int | None, since: datetime
    ) -> dict[str, int]:
        """统计当前用户近七日每日审核通过的待办数量，返回 {'YYYY-MM-DD': 数量} 字典。"""
        statement = (
            select(func.date(TaskAssignment.reviewedAt), func.count(TaskAssignment.id))
            .join(Task, TaskAssignment.taskId == Task.id)
            .where(
                TaskAssignment.userId == userId,
                TaskAssignment.status == AssignmentStatus.ARCHIVED,
                TaskAssignment.reviewedAt.is_not(None),
                TaskAssignment.reviewedAt >= since,
            )
        )
        if teamId is not None:
            statement = statement.where(Task.teamId == teamId)
        statement = statement.group_by(func.date(TaskAssignment.reviewedAt))
        return {str(day): int(count) for day, count in self.db.execute(statement).all()}

    def listUserTeams(self, userId: int, teamId: int | None = None) -> list[Team]:
        """查询用户加入的团队列表，可按单个团队过滤。"""
        statement = (
            select(Team)
            .join(TeamMember, TeamMember.teamId == Team.id)
            .where(TeamMember.userId == userId)
            .order_by(Team.id.asc())
        )
        if teamId is not None:
            statement = statement.where(Team.id == teamId)
        return list(self.db.execute(statement).scalars())

    def countMembersByTeams(self, teamIds: list[int]) -> dict[int, int]:
        """批量统计团队人数，返回 {teamId: 人数} 字典。"""
        if not teamIds:
            return {}
        statement = (
            select(TeamMember.teamId, func.count(TeamMember.id))
            .where(TeamMember.teamId.in_(teamIds))
            .group_by(TeamMember.teamId)
        )
        return {int(teamId): int(count) for teamId, count in self.db.execute(statement).all()}

    def countTasksByTeams(self, teamIds: list[int]) -> dict[int, tuple[int, int]]:
        """批量统计团队的开放任务数与已归档任务数，返回 {teamId: (open, archived)} 字典。"""
        if not teamIds:
            return {}
        statement = (
            select(Task.teamId, Task.status, func.count(Task.id))
            .where(Task.teamId.in_(teamIds), Task.status != TaskStatus.CANCELLED)
            .group_by(Task.teamId, Task.status)
        )
        statistics: dict[int, tuple[int, int]] = {}
        for teamId, status, count in self.db.execute(statement).all():
            openCount, archivedCount = statistics.get(int(teamId), (0, 0))
            if status == TaskStatus.ARCHIVED:
                archivedCount += int(count)
            elif status in OPEN_TASK_STATUSES:
                openCount += int(count)
            statistics[int(teamId)] = (openCount, archivedCount)
        return statistics
