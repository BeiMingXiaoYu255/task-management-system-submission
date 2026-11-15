"""任务数据访问层：任务列表、详情、分配与审核记录的查询封装。

仓储层只负责 SQLAlchemy 查询、筛选、排序与分页，不包含权限与状态机判断。
"""

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from TaskManagementBackend.models import Task, TaskAssignment, TaskReview, TeamMember
from TaskManagementBackend.models.enums import TaskPriority
from TaskManagementBackend.repositories.baseRepository import BaseRepository
from TaskManagementBackend.utils.paginationUtils import paginateStatement

# 任务查询统一预加载：团队/执行人/审核人（多对一）用 joinedload，集合关系用 selectinload 避免行膨胀
TASK_EAGER_OPTIONS = (
    joinedload(Task.team),
    joinedload(Task.subTeam),
    joinedload(Task.sourceTeam),
    joinedload(Task.targetTeam),
    joinedload(Task.sourceSubTeam),
    joinedload(Task.targetSubTeam),
    joinedload(Task.collaboration),
    selectinload(Task.assignments).joinedload(TaskAssignment.user),
    selectinload(Task.assignments).joinedload(TaskAssignment.targetReviewer),
    selectinload(Task.reviews).joinedload(TaskReview.reviewer),
)

# 优先级排序权重表达式：urgent > high > medium > low
PRIORITY_SORT_EXPRESSION = case(
    (Task.priority == TaskPriority.LOW, 1),
    (Task.priority == TaskPriority.MEDIUM, 2),
    (Task.priority == TaskPriority.HIGH, 3),
    (Task.priority == TaskPriority.URGENT, 4),
    else_=0,
)


class TaskRepository(BaseRepository[Task]):
    """任务仓储：封装任务查询、分配记录查询与状态统计。"""

    model = Task

    def getTaskWithRelations(self, taskId: int) -> Task | None:
        """按主键查询任务，并预加载团队、分配（含执行人）与审核记录。"""
        statement = select(Task).options(*TASK_EAGER_OPTIONS).where(Task.id == taskId)
        return self.db.execute(statement).scalar_one_or_none()

    def listMemberships(self, userId: int, teamIds: list[int]) -> dict[int, TeamMember]:
        """批量查询用户在一组团队中的成员关系，返回 {teamId: 成员关系} 字典。"""
        if not teamIds:
            return {}
        rows = self.db.execute(
            select(TeamMember).where(TeamMember.userId == userId, TeamMember.teamId.in_(teamIds))
        ).scalars()
        return {membership.teamId: membership for membership in rows}

    def listTeamMembers(self, teamId: int) -> list[TeamMember]:
        """查询团队全部成员（预加载级别与用户），供 AI 推荐挑选候选成员。"""
        statement = (
            select(TeamMember)
            .options(joinedload(TeamMember.level), joinedload(TeamMember.user))
            .where(TeamMember.teamId == teamId)
            .order_by(TeamMember.levelId.desc())
        )
        return list(self.db.execute(statement).scalars())

    def getAssignment(self, taskId: int, userId: int) -> TaskAssignment | None:
        """查询某任务下指定执行人的分配记录。"""
        statement = select(TaskAssignment).where(
            TaskAssignment.taskId == taskId, TaskAssignment.userId == userId
        )
        return self.db.execute(statement).scalar_one_or_none()

    def countAssignmentStatuses(self, taskId: int) -> dict[str, int]:
        """统计任务下各分配状态数量，供服务层重算任务聚合状态。"""
        statement = (
            select(TaskAssignment.status, func.count(TaskAssignment.id))
            .where(TaskAssignment.taskId == taskId)
            .group_by(TaskAssignment.status)
        )
        return {status.value: int(count) for status, count in self.db.execute(statement).all()}

    def _applyFilters(self, statement, filters: dict):
        """为任务查询追加筛选条件；未提供的条件跳过。"""
        if filters.get("teamId") is not None:
            statement = statement.where(Task.teamId == filters["teamId"])
        if filters.get("status") is not None:
            statement = statement.where(Task.status == filters["status"])
        if filters.get("priority") is not None:
            statement = statement.where(Task.priority == filters["priority"])
        keyword = filters.get("keyword")
        if keyword:
            statement = statement.where(Task.title.like(f"%{keyword.strip()}%"))
        if filters.get("createdBy") is not None:
            statement = statement.where(Task.createdBy == filters["createdBy"])
        if filters.get("assigneeId") is not None:
            assigneeUserId = filters["assigneeId"]
            statement = statement.where(
                Task.id.in_(
                    select(TaskAssignment.taskId).where(TaskAssignment.userId == assigneeUserId)
                )
            )
        return statement

    def _applySort(self, statement, sortBy: str | None, sortOrder: str | None):
        """为任务查询追加排序：createdAt / dueAt / priority，默认创建时间倒序。"""
        if sortBy == "dueAt":
            orderColumn = Task.dueAt
        elif sortBy == "priority":
            orderColumn = PRIORITY_SORT_EXPRESSION
        else:
            orderColumn = Task.createdAt
        orderExpression = orderColumn.desc() if (sortOrder or "desc") == "desc" else orderColumn.asc()
        return statement.order_by(orderExpression, Task.id.desc())

    def listTeamTasks(
        self,
        teamId: int,
        filters: dict,
        page: int,
        pageSize: int,
        subTeamIds: list[int] | None = None,
        isManager: bool = False,
    ) -> tuple[list[Task], int]:
        """团队任务分页查询：包含团队本级任务与协作任务，并按子团队可见性过滤。"""
        visibleSubTeamIds = subTeamIds or []
        statement = (
            select(Task)
            .options(*TASK_EAGER_OPTIONS)
            .where(
                or_(
                    Task.teamId == teamId,
                    Task.sourceTeamId == teamId,
                    Task.targetTeamId == teamId,
                )
            )
        )
        if filters.get("subTeamId") is not None:
            statement = statement.where(Task.subTeamId == filters["subTeamId"])
        if not isManager:
            if visibleSubTeamIds:
                statement = statement.where(
                    or_(
                        Task.subTeamId.is_(None),
                        Task.subTeamId.in_(visibleSubTeamIds),
                        Task.teamId != teamId,
                    )
                )
            else:
                statement = statement.where(or_(Task.subTeamId.is_(None), Task.teamId != teamId))
        statement = self._applySort(
            self._applyFilters(statement, filters), filters.get("sortBy"), filters.get("sortOrder")
        )
        return paginateStatement(self.db, statement, page, pageSize)

    def listMyTasks(
        self, userId: int, role: str | None, filters: dict, page: int, pageSize: int
    ) -> tuple[list[Task], int]:
        """我的任务中心分页：role=created 我发布的 / assigned 我参与的 / 空为两者并集。"""
        assignedTaskIds = select(TaskAssignment.taskId).where(TaskAssignment.userId == userId)
        statement = select(Task).options(*TASK_EAGER_OPTIONS)
        if role == "created":
            statement = statement.where(Task.createdBy == userId)
        elif role == "assigned":
            statement = statement.where(Task.id.in_(assignedTaskIds))
        else:
            statement = statement.where(or_(Task.createdBy == userId, Task.id.in_(assignedTaskIds)))
        statement = self._applySort(
            self._applyFilters(statement, filters), filters.get("sortBy"), filters.get("sortOrder")
        )
        return paginateStatement(self.db, statement, page, pageSize)
