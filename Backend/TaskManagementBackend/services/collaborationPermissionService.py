"""协作领域权限服务：协作单位语义、可见范围解析、对接人与双审核权限判断。

协作单位（unit）= 团队本级（subTeamId 为空）或父团队内的一层子团队。
本模块集中实现单位成员/管理员解析与协作任务权限标记，供 subTeamService /
collaborationService / collaborationTaskService 复用，避免权限规则散落到接口层。
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import forbidden, validationError
from TaskManagementBackend.core.permissions import getMembershipOrNone
from TaskManagementBackend.models import SubTeam, SubTeamMember, Task, Team, TeamMember, User
from TaskManagementBackend.models.enums import (
    AssignmentStatus,
    CollaborationPhase,
    ReviewStage,
    TeamRole,
)
from TaskManagementBackend.repositories.teamRepository import TeamRepository


def enumValue(value) -> str:
    """把枚举或普通字符串统一转换为字符串值，便于与数据库字符串列比较。"""
    return value.value if hasattr(value, "value") else str(value)


def getSubTeamOrRaise(db: Session, teamId: int, subTeamId: int) -> SubTeam:
    """按主键与父团队查询子团队，不存在或不属于该团队时抛 400。"""
    subTeam = db.get(SubTeam, subTeamId)
    if subTeam is None or subTeam.parentTeamId != teamId:
        raise validationError("Sub-team not found or does not belong to this team")
    return subTeam


def isUserTeamAdmin(db: Session, teamId: int, userId: int) -> bool:
    """判断用户是否为指定团队的管理员。"""
    membership = getMembershipOrNone(db, teamId, userId)
    return membership is not None and membership.role == TeamRole.ADMIN


def isUserUnitMember(db: Session, teamId: int, subTeamId: int | None, userId: int) -> bool:
    """判断用户是否严格属于协作单位：团队本级=团队成员，子团队=子团队成员。"""
    if subTeamId is None:
        return getMembershipOrNone(db, teamId, userId) is not None
    statement = select(SubTeamMember.id).where(
        SubTeamMember.subTeamId == subTeamId, SubTeamMember.userId == userId
    )
    return db.execute(statement).first() is not None


def listUnitAdminUserIds(db: Session, teamId: int, subTeamId: int | None) -> list[int]:
    """解析协作单位管理员用户主键集合（去重排序）。

    团队本级：团队管理员；子团队：子负责人 + 父团队管理员。
    """
    statement = select(TeamMember.userId).where(
        TeamMember.teamId == teamId, TeamMember.role == TeamRole.ADMIN
    )
    adminUserIds = {int(userId) for userId in db.execute(statement).scalars().all()}
    if subTeamId is not None:
        subTeam = db.get(SubTeam, subTeamId)
        if subTeam is not None and subTeam.leaderUserId is not None:
            adminUserIds.add(int(subTeam.leaderUserId))
    return sorted(adminUserIds)


def listUnitMemberCandidates(
    db: Session, teamId: int, subTeamId: int | None
) -> list[dict]:
    """解析协作单位候选成员（含父团队级别信息与团队角色），按级别从高到低排序。"""
    teamMembers = TeamRepository(db).listMembers(teamId)
    memberUserIds: set[int] | None = None
    if subTeamId is not None:
        statement = select(SubTeamMember.userId).where(SubTeamMember.subTeamId == subTeamId)
        memberUserIds = {int(userId) for userId in db.execute(statement).scalars().all()}
    candidates: list[dict] = []
    for membership in teamMembers:
        if memberUserIds is not None and membership.userId not in memberUserIds:
            continue
        user = membership.user
        level = membership.level
        candidates.append(
            {
                "userId": membership.userId,
                "username": user.username if user is not None else "deleted",
                "nickname": user.nickname if user is not None else "Deleted User",
                "avatar": user.avatar if user is not None else None,
                "levelName": level.name if level is not None else "",
                "levelOrder": level.levelOrder if level is not None else 0,
                "role": membership.role,
            }
        )
    return candidates


def buildCollaborationUnit(team: Team | None, subTeam: SubTeam | None) -> dict:
    """构建协作单位响应字典：团队名 + 可选子团队名，unitName 为展示用全称。"""
    teamId = team.id if team is not None else (subTeam.parentTeamId if subTeam is not None else 0)
    teamName = team.name if team is not None else ""
    subTeamId = subTeam.id if subTeam is not None else None
    subTeamName = subTeam.name if subTeam is not None else None
    unitName = f"{teamName} - {subTeamName}" if subTeamName else teamName
    return {
        "teamId": teamId,
        "teamName": teamName,
        "subTeamId": subTeamId,
        "subTeamName": subTeamName,
        "unitName": unitName,
    }


@dataclass
class CollaborationViewerContext:
    """当前用户协作可见范围上下文：一次加载、多次判断，避免列表接口逐条查询。"""

    userId: int
    currentUser: User | None = None
    teamRoles: dict[int, TeamRole] = field(default_factory=dict)
    leaderSubTeamIds: set[int] = field(default_factory=set)
    memberSubTeamIds: set[int] = field(default_factory=set)

    @classmethod
    def load(cls, db: Session, currentUser: User) -> "CollaborationViewerContext":
        """加载当前用户的团队成员关系、子团队负责人身份与子团队成员关系。"""
        memberships = db.execute(
            select(TeamMember).where(TeamMember.userId == currentUser.id)
        ).scalars().all()
        leaderSubTeamIds = {
            int(subTeamId)
            for subTeamId in db.execute(
                select(SubTeam.id).where(SubTeam.leaderUserId == currentUser.id)
            ).scalars().all()
        }
        memberSubTeamIds = {
            int(subTeamId)
            for subTeamId in db.execute(
                select(SubTeamMember.subTeamId).where(SubTeamMember.userId == currentUser.id)
            ).scalars().all()
        }
        return cls(
            userId=currentUser.id,
            currentUser=currentUser,
            teamRoles={membership.teamId: membership.role for membership in memberships},
            leaderSubTeamIds=leaderSubTeamIds,
            memberSubTeamIds=memberSubTeamIds,
        )

    @property
    def requireCurrentUser(self) -> User:
        """当前登录用户对象：构建任务响应（我的待办/权限标记）时需要。"""
        if self.currentUser is None:
            raise validationError("Current user context is missing")
        return self.currentUser

    def isTeamMember(self, teamId: int | None) -> bool:
        """判断当前用户是否为团队成员。"""
        return teamId is not None and teamId in self.teamRoles

    def isTeamAdmin(self, teamId: int | None) -> bool:
        """判断当前用户是否为团队管理员。"""
        return teamId is not None and self.teamRoles.get(teamId) == TeamRole.ADMIN

    def isSubTeamMember(self, subTeamId: int | None) -> bool:
        """判断当前用户是否为子团队成员。"""
        return subTeamId is not None and subTeamId in self.memberSubTeamIds

    def isUnitMember(self, teamId: int, subTeamId: int | None) -> bool:
        """判断当前用户是否严格属于协作单位（团队本级=团队成员；子团队=子团队成员）。"""
        if subTeamId is None:
            return self.isTeamMember(teamId)
        return self.isSubTeamMember(subTeamId)

    def isUnitAdmin(self, teamId: int, subTeamId: int | None) -> bool:
        """判断当前用户是否为单位管理员（团队管理员；子负责人或父团队管理员）。"""
        if subTeamId is None:
            return self.isTeamAdmin(teamId)
        isSubTeamLeader = self.isSubTeamMember(subTeamId) and subTeamId in self.leaderSubTeamIds
        return isSubTeamLeader or self.isTeamAdmin(teamId)

    def canViewUnit(self, teamId: int, subTeamId: int | None) -> bool:
        """判断当前用户能否查看单位数据：单位成员，或子团队所属父团队的管理员。"""
        if self.isUnitMember(teamId, subTeamId):
            return True
        return subTeamId is not None and self.isTeamAdmin(teamId)

    def resolveMyUnitRole(
        self,
        initiatorTeamId: int,
        initiatorSubTeamId: int | None,
        targetTeamId: int,
        targetSubTeamId: int | None,
    ) -> str | None:
        """解析当前用户在协作关系中的单位角色：initiator / target / both / None。"""
        isInitiatorSide = self.canViewUnit(initiatorTeamId, initiatorSubTeamId)
        isTargetSide = self.canViewUnit(targetTeamId, targetSubTeamId)
        if isInitiatorSide and isTargetSide:
            return "both"
        if isInitiatorSide:
            return "initiator"
        if isTargetSide:
            return "target"
        return None


def buildCollaborationTaskFlags(task: Task, context: CollaborationViewerContext) -> dict:
    """构建协作任务的双审核权限标记（供列表/详情响应追加）。

    canConfirmTask：接收方对接人且任务处于待确认阶段；
    canTargetReview：接收方对接人且存在待接收方审核的执行人；
    canSourceReview：任务发布者（发布者注销时为发起单位管理员）且存在待发起方审核的执行人。
    """
    collaboration = task.collaboration
    targetTeamId = task.targetTeamId or task.teamId
    assignments = list(task.assignments)
    hasTargetPending = any(
        assignment.status == AssignmentStatus.PENDING_REVIEW
        and assignment.reviewStage == ReviewStage.TARGET.value
        for assignment in assignments
    )
    hasSourcePending = any(
        assignment.status == AssignmentStatus.PENDING_REVIEW
        and assignment.reviewStage == ReviewStage.SOURCE.value
        for assignment in assignments
    )
    isTargetLiaison = (
        collaboration is not None and collaboration.targetLiaisonUserId == context.userId
    )
    isTargetUnitMember = context.isUnitMember(targetTeamId, task.targetSubTeamId)
    isPublisher = task.createdBy is not None and task.createdBy == context.userId
    isSourceUnitAdmin = task.createdBy is None and context.isUnitAdmin(
        task.sourceTeamId or 0, task.sourceSubTeamId
    )
    return {
        "canConfirmTask": enumValue(task.collaborationPhase)
        == CollaborationPhase.PENDING_CONFIRMATION.value
        and isTargetLiaison
        and isTargetUnitMember,
        "canTargetReview": isTargetLiaison and isTargetUnitMember and hasTargetPending,
        "canSourceReview": (isPublisher or isSourceUnitAdmin) and hasSourcePending,
    }


def resolveSourceReviewerUserIds(db: Session, task: Task) -> list[int]:
    """解析发起方审核人：默认任务发布者；发布者注销后为发起单位全部管理员。"""
    if task.createdBy is not None:
        return [int(task.createdBy)]
    return listUnitAdminUserIds(db, task.sourceTeamId or task.teamId, task.sourceSubTeamId)


def requireCanSourceReview(
    task: Task, currentUser: User, context: CollaborationViewerContext
) -> None:
    """校验发起方审核权限：任务发布者；发布者注销时由发起单位管理员审核。"""
    if task.createdBy is not None:
        if task.createdBy != currentUser.id:
            raise forbidden("Only the task publisher can review this collaboration task")
        return
    if not context.isUnitAdmin(task.sourceTeamId or task.teamId, task.sourceSubTeamId):
        raise forbidden("Only an initiating unit admin can review this collaboration task")
