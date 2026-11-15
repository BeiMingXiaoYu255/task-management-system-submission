"""待办数据访问层：我的待办分页、待办统计与执行人负载统计。

待办数据即 task_assignments 表，仓储包装待办查询所需的联表与排序逻辑。
"""

from sqlalchemy import case, func, select
from sqlalchemy.orm import joinedload

from TaskManagementBackend.models import Task, TaskAssignment
from TaskManagementBackend.models.enums import AssignmentStatus, TaskPriority, TaskStatus
from TaskManagementBackend.repositories.baseRepository import BaseRepository
from TaskManagementBackend.utils.paginationUtils import paginateStatement
from TaskManagementBackend.utils.timeUtils import getCurrentTime

# 优先级排序权重表达式：urgent > high > medium > low
PRIORITY_SORT_EXPRESSION = case(
    (Task.priority == TaskPriority.LOW, 1),
    (Task.priority == TaskPriority.MEDIUM, 2),
    (Task.priority == TaskPriority.HIGH, 3),
    (Task.priority == TaskPriority.URGENT, 4),
    else_=0,
)

# 视为“未完成”的待办状态集合，用于统计与逾期判断
ACTIVE_ASSIGNMENT_STATUSES = (
    AssignmentStatus.PENDING_ACCEPTANCE,
    AssignmentStatus.IN_PROGRESS,
    AssignmentStatus.PENDING_REVIEW,
)


class TodoRepository(BaseRepository[TaskAssignment]):
    """待办仓储：封装当前用户待办查询与统计。"""

    model = TaskAssignment

    def _applyFilters(self, statement, filters: dict):
        """为待办查询追加筛选条件：状态默认排除已归档。"""
        status = filters.get("status")
        if status is not None:
            statement = statement.where(TaskAssignment.status == status)
        elif not filters.get("includeArchived"):
            statement = statement.where(TaskAssignment.status != AssignmentStatus.ARCHIVED)
        if filters.get("priority") is not None:
            statement = statement.where(Task.priority == filters["priority"])
        if filters.get("teamId") is not None:
            statement = statement.where(Task.teamId == filters["teamId"])
        keyword = filters.get("keyword")
        if keyword:
            statement = statement.where(Task.title.like(f"%{keyword.strip()}%"))
        return statement

    def _applySort(self, statement, sortBy: str | None, sortOrder: str | None):
        """为待办查询追加排序：priority / dueAt / createdAt，默认创建时间倒序。"""
        if sortBy == "priority":
            orderColumn = PRIORITY_SORT_EXPRESSION
        elif sortBy == "dueAt":
            orderColumn = Task.dueAt
        else:
            orderColumn = TaskAssignment.createdAt
        orderExpression = orderColumn.desc() if (sortOrder or "desc") == "desc" else orderColumn.asc()
        return statement.order_by(orderExpression, TaskAssignment.id.desc())

    def listTodos(
        self, userId: int, filters: dict, page: int, pageSize: int
    ) -> tuple[list[TaskAssignment], int]:
        """我的待办分页查询，返回 (当页待办, 总数)；已取消任务的待办不展示。"""
        statement = (
            select(TaskAssignment)
            .join(Task, TaskAssignment.taskId == Task.id)
            .options(
                joinedload(TaskAssignment.task).joinedload(Task.team),
                joinedload(TaskAssignment.task).joinedload(Task.creator),
            )
            .where(TaskAssignment.userId == userId, Task.status != TaskStatus.CANCELLED)
        )
        statement = self._applySort(
            self._applyFilters(statement, filters), filters.get("sortBy"), filters.get("sortOrder")
        )
        return paginateStatement(self.db, statement, page, pageSize)

    def getStatusCounts(self, userId: int) -> dict[str, int]:
        """统计当前用户各待办状态数量（不含已取消任务的待办）。"""
        statement = (
            select(TaskAssignment.status, func.count(TaskAssignment.id))
            .join(Task, TaskAssignment.taskId == Task.id)
            .where(TaskAssignment.userId == userId, Task.status != TaskStatus.CANCELLED)
            .group_by(TaskAssignment.status)
        )
        return {status.value: int(count) for status, count in self.db.execute(statement).all()}

    def countOverdue(self, userId: int) -> int:
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
        return int(self.db.execute(statement).scalar_one())

    def countActiveAssignmentsByUsers(self, userIds: list[int]) -> dict[int, int]:
        """批量统计一组用户未完成的待办数量，供 AI 推荐计算负载。"""
        if not userIds:
            return {}
        statement = (
            select(TaskAssignment.userId, func.count(TaskAssignment.id))
            .join(Task, TaskAssignment.taskId == Task.id)
            .where(
                TaskAssignment.userId.in_(userIds),
                Task.status != TaskStatus.CANCELLED,
                TaskAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES),
            )
            .group_by(TaskAssignment.userId)
        )
        return {int(userId): int(count) for userId, count in self.db.execute(statement).all()}
