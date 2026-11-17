"""设置数据访问层：用户界面设置与注销账号相关的数据清理操作。

设置仓储同时承担注销账号时的关联数据清理 SQL，业务规则（如团队管理员
必须先转让）由服务层判断。
"""

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import joinedload

from TaskManagementBackend.models import Task, TaskAssignment, TeamJoinRequest, TeamMember, UserSetting
from TaskManagementBackend.repositories.baseRepository import BaseRepository


class SettingRepository(BaseRepository[UserSetting]):
    """用户设置仓储：界面设置读写与注销账号的数据清理。"""

    model = UserSetting

    def getByUserId(self, userId: int) -> UserSetting | None:
        """按用户主键查询界面设置，不存在返回 None。"""
        statement = select(UserSetting).where(UserSetting.userId == userId)
        return self.db.execute(statement).scalar_one_or_none()

    def createDefault(self, userId: int) -> UserSetting:
        """为用户创建默认界面设置记录（light / medium / system）。"""
        setting = UserSetting(userId=userId)
        self.db.add(setting)
        self.db.flush()
        return setting

    def listMemberships(self, userId: int) -> list[TeamMember]:
        """查询用户全部团队关系（含团队预加载），供注销账号时校验管理员身份。"""
        statement = (
            select(TeamMember)
            .options(joinedload(TeamMember.team))
            .where(TeamMember.userId == userId)
        )
        return list(self.db.execute(statement).scalars())

    def countTeamMembers(self, teamId: int) -> int:
        """统计团队当前成员数量。"""
        statement = select(func.count(TeamMember.id)).where(TeamMember.teamId == teamId)
        return int(self.db.execute(statement).scalar_one())

    def deleteTeam(self, team) -> None:
        """删除团队（数据库外键级联删除级别、成员、任务等关联数据）。"""
        self.db.delete(team)
        self.db.flush()

    def listAssignedTaskIds(self, userId: int) -> list[int]:
        """查询用户作为执行人的全部任务主键（删除待办前记录，便于重算任务状态）。"""
        statement = select(TaskAssignment.taskId).where(TaskAssignment.userId == userId).distinct()
        return [int(taskId) for taskId in self.db.execute(statement).scalars().all()]

    def deleteAssignmentsByUser(self, userId: int) -> None:
        """删除用户的全部待办（任务分配记录）。"""
        self.db.execute(delete(TaskAssignment).where(TaskAssignment.userId == userId))
        self.db.flush()

    def clearTaskCreator(self, userId: int) -> None:
        """把用户发布的任务 created_by 置空（任务保留，发布者状态交由团队管理员审核）。"""
        self.db.execute(update(Task).where(Task.createdBy == userId).values(createdBy=None))
        self.db.flush()

    def deleteJoinRequestsByUser(self, userId: int) -> None:
        """删除用户发起的全部入团申请。"""
        self.db.execute(delete(TeamJoinRequest).where(TeamJoinRequest.userId == userId))
        self.db.flush()

    def deleteMembershipsByUser(self, userId: int) -> None:
        """删除用户的全部团队成员关系。"""
        self.db.execute(delete(TeamMember).where(TeamMember.userId == userId))
        self.db.flush()
