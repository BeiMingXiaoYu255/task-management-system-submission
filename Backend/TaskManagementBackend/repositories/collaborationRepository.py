"""协作关系数据访问层：协作关系、协作目录与协作任务列表查询。

只封装 SQLAlchemy 查询，不包含权限与状态机判断（由 collaborationService /
collaborationTaskService 负责）；协作任务查询复用任务仓储的预加载与排序定义。
"""

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import joinedload, selectinload

from TaskManagementBackend.models import SubTeam, Task, TaskAssignment, Team, TeamCollaboration
from TaskManagementBackend.models.enums import CollaborationStatus, TeamStatus
from TaskManagementBackend.repositories.baseRepository import BaseRepository
from TaskManagementBackend.repositories.taskRepository import (
    PRIORITY_SORT_EXPRESSION,
    TASK_EAGER_OPTIONS,
)
from TaskManagementBackend.utils.paginationUtils import paginateStatement

# 协作关系查询统一预加载：双方团队/子团队、双方对接人与申请人
COLLABORATION_EAGER_OPTIONS = (
    joinedload(TeamCollaboration.initiatorTeam),
    joinedload(TeamCollaboration.targetTeam),
    joinedload(TeamCollaboration.initiatorSubTeam),
    joinedload(TeamCollaboration.targetSubTeam),
    joinedload(TeamCollaboration.creator),
)


class CollaborationRepository(BaseRepository[TeamCollaboration]):
    """协作关系仓储：协作关系查询、重复校验、可见范围分页与目录数据。"""

    model = TeamCollaboration

    def getWithDetails(self, collaborationId: int) -> TeamCollaboration | None:
        """按主键查询协作关系并预加载双方单位与对接人。"""
        statement = (
            select(TeamCollaboration)
            .options(*COLLABORATION_EAGER_OPTIONS)
            .where(TeamCollaboration.id == collaborationId)
        )
        return self.db.execute(statement).scalars().first()

    def findConflictingPair(
        self,
        initiatorTeamId: int,
        initiatorSubTeamId: int | None,
        targetTeamId: int,
        targetSubTeamId: int | None,
    ) -> TeamCollaboration | None:
        """查询同一对协作单位之间已存在的 pending/active 协作（双向检查）。"""
        activeStatuses = (CollaborationStatus.PENDING, CollaborationStatus.ACTIVE)
        forwardCondition = and_(
            TeamCollaboration.initiatorTeamId == initiatorTeamId,
            TeamCollaboration.initiatorSubTeamId.is_(None)
            if initiatorSubTeamId is None
            else TeamCollaboration.initiatorSubTeamId == initiatorSubTeamId,
            TeamCollaboration.targetTeamId == targetTeamId,
            TeamCollaboration.targetSubTeamId.is_(None)
            if targetSubTeamId is None
            else TeamCollaboration.targetSubTeamId == targetSubTeamId,
        )
        reverseCondition = and_(
            TeamCollaboration.initiatorTeamId == targetTeamId,
            TeamCollaboration.initiatorSubTeamId.is_(None)
            if targetSubTeamId is None
            else TeamCollaboration.initiatorSubTeamId == targetSubTeamId,
            TeamCollaboration.targetTeamId == initiatorTeamId,
            TeamCollaboration.targetSubTeamId.is_(None)
            if initiatorSubTeamId is None
            else TeamCollaboration.targetSubTeamId == initiatorSubTeamId,
        )
        statement = select(TeamCollaboration).where(
            or_(forwardCondition, reverseCondition),
            TeamCollaboration.status.in_(activeStatuses),
        )
        return self.db.execute(statement).scalars().first()

    def listRelated(
        self,
        userId: int,
        teamMemberIds: list[int],
        adminTeamIds: list[int],
        memberSubTeamIds: list[int],
        status: str | None,
        teamId: int | None,
        page: int,
        pageSize: int,
    ) -> tuple[list[TeamCollaboration], int]:
        """分页查询与当前用户相关的协作关系。

        可见范围由服务层预先解析为数据集合：
            teamMemberIds     当前用户加入的团队主键；
            adminTeamIds      当前用户担任管理员的团队主键；
            memberSubTeamIds  当前用户加入的子团队主键；
        团队本级单位对全体团队成员可见；子团队单位对子团队成员与父团队管理员可见；
        任一方对接人始终可见。
        """
        teamLevelVisible = or_(
            and_(
                TeamCollaboration.initiatorSubTeamId.is_(None),
                TeamCollaboration.initiatorTeamId.in_(teamMemberIds),
            ),
            and_(
                TeamCollaboration.targetSubTeamId.is_(None),
                TeamCollaboration.targetTeamId.in_(teamMemberIds),
            ),
        )
        subTeamVisible = or_(
            TeamCollaboration.initiatorSubTeamId.in_(memberSubTeamIds),
            TeamCollaboration.targetSubTeamId.in_(memberSubTeamIds),
        )
        adminVisible = or_(
            and_(
                TeamCollaboration.initiatorSubTeamId.is_not(None),
                TeamCollaboration.initiatorTeamId.in_(adminTeamIds),
            ),
            and_(
                TeamCollaboration.targetSubTeamId.is_not(None),
                TeamCollaboration.targetTeamId.in_(adminTeamIds),
            ),
        )
        liaisonVisible = or_(
            TeamCollaboration.initiatorLiaisonUserId == userId,
            TeamCollaboration.targetLiaisonUserId == userId,
        )
        statement = (
            select(TeamCollaboration)
            .options(*COLLABORATION_EAGER_OPTIONS)
            .where(or_(teamLevelVisible, subTeamVisible, adminVisible, liaisonVisible))
        )
        if status:
            statement = statement.where(TeamCollaboration.status == status)
        if teamId is not None:
            statement = statement.where(
                or_(
                    TeamCollaboration.initiatorTeamId == teamId,
                    TeamCollaboration.targetTeamId == teamId,
                )
            )
        statement = statement.order_by(
            TeamCollaboration.createdAt.desc(), TeamCollaboration.id.desc()
        )
        return paginateStatement(self.db, statement, page, pageSize)

    def listActiveTeamsWithSubTeams(self) -> list[Team]:
        """查询全部已认证团队并预加载子团队与子负责人（协作目录使用）。"""
        statement = (
            select(Team)
            .options(selectinload(Team.subTeams).joinedload(SubTeam.leader))
            .where(Team.status == TeamStatus.ACTIVE)
            .order_by(Team.id.desc())
        )
        return list(self.db.execute(statement).scalars().unique())

    def listCollaborationTasks(
        self, collaborationId: int, filters: dict, page: int, pageSize: int
    ) -> tuple[list[Task], int]:
        """分页查询某协作关系下的协作任务，支持状态/优先级/关键词/执行人筛选与排序。"""
        statement = (
            select(Task)
            .options(*TASK_EAGER_OPTIONS)
            .where(Task.collaborationId == collaborationId)
        )
        if filters.get("status") is not None:
            statement = statement.where(Task.status == filters["status"])
        if filters.get("priority") is not None:
            statement = statement.where(Task.priority == filters["priority"])
        if filters.get("keyword"):
            statement = statement.where(Task.title.like(f"%{str(filters['keyword']).strip()}%"))
        if filters.get("createdBy") is not None:
            statement = statement.where(Task.createdBy == filters["createdBy"])
        if filters.get("assigneeId") is not None:
            statement = statement.where(
                Task.id.in_(
                    select(TaskAssignment.taskId).where(
                        TaskAssignment.userId == filters["assigneeId"]
                    )
                )
            )
        if filters.get("sortBy") == "dueAt":
            orderColumn = Task.dueAt
        elif filters.get("sortBy") == "priority":
            orderColumn = PRIORITY_SORT_EXPRESSION
        else:
            orderColumn = Task.createdAt
        if (filters.get("sortOrder") or "desc") == "asc":
            statement = statement.order_by(orderColumn.asc(), Task.id.asc())
        else:
            statement = statement.order_by(orderColumn.desc(), Task.id.desc())
        return paginateStatement(self.db, statement, page, pageSize)
