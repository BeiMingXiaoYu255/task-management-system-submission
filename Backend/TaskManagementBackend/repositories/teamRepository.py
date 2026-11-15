"""团队、团队级别、团队成员与入团申请数据访问层。

只封装团队域的查询与写入，不包含权限判断与业务状态机。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from TaskManagementBackend.models import Team, TeamJoinRequest, TeamLevel, TeamMember, User
from TaskManagementBackend.models.enums import JoinRequestStatus
from TaskManagementBackend.repositories.baseRepository import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """团队仓储：团队、级别、成员与入团申请的统一数据访问入口。"""

    model = Team

    def getTeamWithDetails(self, teamId: int) -> Team | None:
        """按主键查询团队，并预加载级别与成员（含用户技能），用于构建团队详情。"""
        statement = (
            select(Team)
            .options(
                selectinload(Team.levels),
                selectinload(Team.members)
                .joinedload(TeamMember.user)
                .selectinload(User.skills),
                selectinload(Team.members).joinedload(TeamMember.level),
            )
            .where(Team.id == teamId)
        )
        return self.db.execute(statement).scalars().unique().first()

    def listTeamsForUser(self, userId: int) -> list[Team]:
        """查询用户加入的全部团队（含自己创建的待认证团队），按团队主键倒序。"""
        statement = (
            select(Team)
            .join(TeamMember, TeamMember.teamId == Team.id)
            .where(TeamMember.userId == userId)
            .order_by(Team.id.desc())
        )
        return list(self.db.execute(statement).scalars().unique())

    def countMembersByTeamIds(self, teamIds: list[int]) -> dict[int, int]:
        """统计多个团队的成员数量，返回 {团队主键: 成员数}。"""
        if not teamIds:
            return {}
        statement = (
            select(TeamMember.teamId, func.count())
            .where(TeamMember.teamId.in_(teamIds))
            .group_by(TeamMember.teamId)
        )
        return {int(teamId): int(count) for teamId, count in self.db.execute(statement).all()}

    def listMembers(self, teamId: int) -> list[TeamMember]:
        """查询团队成员（预加载用户技能与级别），按级别从高到低、加入时间先后排序。"""
        statement = (
            select(TeamMember)
            .options(
                joinedload(TeamMember.user).selectinload(User.skills),
                joinedload(TeamMember.level),
            )
            .where(TeamMember.teamId == teamId)
        )
        members = list(self.db.execute(statement).scalars().unique())
        members.sort(key=lambda member: (-(member.level.levelOrder if member.level else 0), member.id))
        return members

    def getMembership(self, teamId: int, userId: int) -> TeamMember | None:
        """查询指定用户在指定团队中的成员关系（预加载级别与用户）。"""
        statement = (
            select(TeamMember)
            .options(joinedload(TeamMember.level), joinedload(TeamMember.user))
            .where(TeamMember.teamId == teamId, TeamMember.userId == userId)
        )
        return self.db.execute(statement).scalars().first()

    def addMember(self, teamId: int, userId: int, role, levelId: int) -> TeamMember:
        """新增团队成员关系并 flush 取得主键。"""
        membership = TeamMember(teamId=teamId, userId=userId, role=role, levelId=levelId)
        self.db.add(membership)
        self.db.flush()
        return membership

    def listLevels(self, teamId: int) -> list[TeamLevel]:
        """查询团队级别列表，按级别数值从高到低排序。"""
        statement = (
            select(TeamLevel)
            .where(TeamLevel.teamId == teamId)
            .order_by(TeamLevel.levelOrder.desc())
        )
        return list(self.db.execute(statement).scalars())

    def getLevel(self, levelId: int) -> TeamLevel | None:
        """按主键查询团队级别。"""
        return self.db.get(TeamLevel, levelId)

    def findLevelByOrder(self, teamId: int, levelOrder: int) -> TeamLevel | None:
        """按团队与级别数值查询级别，用于唯一性校验。"""
        statement = select(TeamLevel).where(
            TeamLevel.teamId == teamId, TeamLevel.levelOrder == levelOrder
        )
        return self.db.execute(statement).scalars().first()

    def getLowestLevel(self, teamId: int) -> TeamLevel | None:
        """获取团队最低级别（levelOrder 最小），新成员默认加入该级别。"""
        statement = (
            select(TeamLevel)
            .where(TeamLevel.teamId == teamId)
            .order_by(TeamLevel.levelOrder.asc())
        )
        return self.db.execute(statement).scalars().first()

    def countMembersAtLevel(self, levelId: int) -> int:
        """统计使用某个级别的成员数量，用于删除级别前的占用校验。"""
        statement = (
            select(func.count()).select_from(TeamMember).where(TeamMember.levelId == levelId)
        )
        return int(self.db.execute(statement).scalar_one())

    def countLevels(self, teamId: int) -> int:
        """统计团队级别数量，用于保证至少保留一个级别。"""
        statement = select(func.count()).select_from(TeamLevel).where(TeamLevel.teamId == teamId)
        return int(self.db.execute(statement).scalar_one())

    def findTeamByInviteCode(self, inviteCode: str) -> Team | None:
        """按邀请码查询团队，用于邀请码加入流程。"""
        return self.db.execute(
            select(Team).where(Team.inviteCode == inviteCode)
        ).scalars().first()

    def listPendingJoinRequests(self, teamId: int) -> list[TeamJoinRequest]:
        """查询团队待处理入团申请（预加载申请人），按申请时间升序。"""
        statement = (
            select(TeamJoinRequest)
            .options(joinedload(TeamJoinRequest.user))
            .where(
                TeamJoinRequest.teamId == teamId,
                TeamJoinRequest.status == JoinRequestStatus.PENDING,
            )
            .order_by(TeamJoinRequest.createdAt.asc())
        )
        return list(self.db.execute(statement).scalars().unique())

    def getJoinRequest(self, teamId: int, requestId: int) -> TeamJoinRequest | None:
        """按团队与申请主键查询入团申请。"""
        statement = select(TeamJoinRequest).where(
            TeamJoinRequest.id == requestId, TeamJoinRequest.teamId == teamId
        )
        return self.db.execute(statement).scalars().first()

    def findPendingJoinRequest(self, teamId: int, userId: int) -> TeamJoinRequest | None:
        """查询用户对某团队的待处理入团申请，用于重复申请校验。"""
        statement = select(TeamJoinRequest).where(
            TeamJoinRequest.teamId == teamId,
            TeamJoinRequest.userId == userId,
            TeamJoinRequest.status == JoinRequestStatus.PENDING,
        )
        return self.db.execute(statement).scalars().first()

    def createJoinRequest(
        self, teamId: int, userId: int, message: str | None = None
    ) -> TeamJoinRequest:
        """创建待处理入团申请并 flush 取得主键。"""
        joinRequest = TeamJoinRequest(
            teamId=teamId,
            userId=userId,
            message=message,
            status=JoinRequestStatus.PENDING,
        )
        self.db.add(joinRequest)
        self.db.flush()
        return joinRequest
