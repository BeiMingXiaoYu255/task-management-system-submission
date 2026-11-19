"""子团队数据访问层：子团队、子团队成员关系与成员统计查询。

只封装 SQLAlchemy 查询，不包含权限与业务状态机判断（由 subTeamService 负责）。
"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import joinedload

from TaskManagementBackend.models import SubTeam, SubTeamMember
from TaskManagementBackend.repositories.baseRepository import BaseRepository


class SubTeamRepository(BaseRepository[SubTeam]):
    """子团队仓储：按父团队隔离的查询、成员维护与计数。"""

    model = SubTeam

    def getByIdAndTeam(self, teamId: int, subTeamId: int) -> SubTeam | None:
        """按主键与父团队查询子团队，避免跨团队越权访问。"""
        statement = select(SubTeam).where(
            SubTeam.id == subTeamId, SubTeam.parentTeamId == teamId
        )
        return self.db.execute(statement).scalars().first()

    def findByName(self, teamId: int, name: str) -> SubTeam | None:
        """按父团队与名称查询子团队，用于同团队内名称唯一校验。"""
        statement = select(SubTeam).where(SubTeam.parentTeamId == teamId, SubTeam.name == name)
        return self.db.execute(statement).scalars().first()

    def listByTeam(self, teamId: int) -> list[SubTeam]:
        """查询父团队下全部子团队，按创建先后排序。"""
        statement = select(SubTeam).where(SubTeam.parentTeamId == teamId).order_by(SubTeam.id.asc())
        return list(self.db.execute(statement).scalars())

    def listByTeamIds(self, teamIds: list[int]) -> list[SubTeam]:
        """批量查询多个父团队下的子团队（协作目录使用）。"""
        if not teamIds:
            return []
        statement = (
            select(SubTeam)
            .where(SubTeam.parentTeamId.in_(teamIds))
            .order_by(SubTeam.parentTeamId.asc(), SubTeam.id.asc())
        )
        return list(self.db.execute(statement).scalars())

    def countMembersBySubTeamIds(self, subTeamIds: list[int]) -> dict[int, int]:
        """批量统计子团队成员数，返回 {子团队主键: 成员数}。"""
        if not subTeamIds:
            return {}
        statement = (
            select(SubTeamMember.subTeamId, func.count(SubTeamMember.id))
            .where(SubTeamMember.subTeamId.in_(subTeamIds))
            .group_by(SubTeamMember.subTeamId)
        )
        return {int(subTeamId): int(count) for subTeamId, count in self.db.execute(statement).all()}

    def countMembers(self, subTeamId: int) -> int:
        """统计单个子团队成员数。"""
        statement = select(func.count(SubTeamMember.id)).where(
            SubTeamMember.subTeamId == subTeamId
        )
        return int(self.db.execute(statement).scalar_one())

    def listMembers(self, subTeamId: int) -> list[SubTeamMember]:
        """查询子团队全部成员关系（预加载用户），按加入时间升序。"""
        statement = (
            select(SubTeamMember)
            .options(joinedload(SubTeamMember.user))
            .where(SubTeamMember.subTeamId == subTeamId)
            .order_by(SubTeamMember.joinedAt.asc(), SubTeamMember.id.asc())
        )
        return list(self.db.execute(statement).scalars().unique())

    def listMemberUserIds(self, subTeamId: int) -> list[int]:
        """查询子团队全部成员用户主键。"""
        statement = select(SubTeamMember.userId).where(SubTeamMember.subTeamId == subTeamId)
        return [int(userId) for userId in self.db.execute(statement).scalars().all()]

    def getMember(self, subTeamId: int, userId: int) -> SubTeamMember | None:
        """查询指定用户在子团队中的成员关系。"""
        statement = select(SubTeamMember).where(
            SubTeamMember.subTeamId == subTeamId, SubTeamMember.userId == userId
        )
        return self.db.execute(statement).scalars().first()

    def addMember(self, subTeamId: int, userId: int) -> SubTeamMember:
        """新增子团队成员关系并 flush 取得主键。"""
        member = SubTeamMember(subTeamId=subTeamId, userId=userId)
        self.db.add(member)
        self.db.flush()
        return member

    def replaceMembers(self, subTeamId: int, userIds: list[int]) -> None:
        """覆盖式替换子团队成员：先删除旧成员关系，再批量插入新成员。"""
        self.db.execute(delete(SubTeamMember).where(SubTeamMember.subTeamId == subTeamId))
        for userId in userIds:
            self.db.add(SubTeamMember(subTeamId=subTeamId, userId=userId))
        self.db.flush()

    def deleteAllMembers(self, subTeamId: int) -> None:
        """删除子团队全部成员关系（覆盖式设置成员前的清空操作）。"""
        self.db.execute(delete(SubTeamMember).where(SubTeamMember.subTeamId == subTeamId))
        self.db.flush()

    def countByTeam(self, teamId: int) -> int:
        """统计父团队下子团队数量（团队详情展示用）。"""
        statement = select(func.count(SubTeam.id)).where(SubTeam.parentTeamId == teamId)
        return int(self.db.execute(statement).scalar_one())
