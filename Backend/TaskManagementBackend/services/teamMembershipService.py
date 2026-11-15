"""团队成员业务服务：加入/退出团队、成员列表、踢人、子管理员设置、级别调整与候选成员。

加入规则：
    free      —— 直接加入团队最低级别；
    approval  —— 创建待处理入团申请，由管理员/子管理员审批；
    inviteOnly—— 必须提供有效邀请码（校验过期时间与最大使用次数）。
"""

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import (
    AppException,
    conflict,
    forbidden,
    notFound,
    validationError,
)
from TaskManagementBackend.core.permissions import (
    requireCanLeaveTeam,
    requireCanManageTargetMember,
    requireJoinableTeam,
    requireTeamAdmin,
    requireTeamManager,
    requireTeamMember,
)
from TaskManagementBackend.models import Team, TeamMember, User
from TaskManagementBackend.models.enums import JoinMethod, TeamRole
from TaskManagementBackend.repositories.teamRepository import TeamRepository
from TaskManagementBackend.schemas.teamSchema import (
    JoinTeamRequest,
    SetMemberLevelRequest,
    SetMemberRoleRequest,
)
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.serializationService import buildSkillItems
from TaskManagementBackend.services.teamService import buildTeamMemberItemDict
from TaskManagementBackend.utils.timeUtils import getCurrentTime


def createMemberAtLowestLevel(db: Session, team: Team, user: User) -> TeamMember:
    """把用户加入团队最低级别（仅 flush，事务由调用方提交）。"""
    teamRepository = TeamRepository(db)
    lowestLevel = teamRepository.getLowestLevel(team.id)
    if lowestLevel is None:
        raise AppException("DATABASE_ERROR", "Team level data is missing. Unable to join the team.", 500)
    return teamRepository.addMember(
        teamId=team.id, userId=user.id, role=TeamRole.MEMBER, levelId=lowestLevel.id
    )


def buildJoinTeamResult(statusValue: str, team: Team, message: str) -> dict:
    """构造加入团队结果响应。"""
    return {
        "status": statusValue,
        "teamId": team.id,
        "teamName": team.name,
        "message": message,
    }


def buildMemberCandidateItem(member: TeamMember) -> dict:
    """把成员关系转换为任务可选成员候选响应（含级别与技能）。"""
    memberUser = member.user
    memberLevel = member.level
    return {
        "userId": member.userId,
        "username": memberUser.username if memberUser is not None else "deleted",
        "nickname": memberUser.nickname if memberUser is not None else "Deleted User",
        "avatar": memberUser.avatar if memberUser is not None else None,
        "role": member.role.value,
        "levelId": member.levelId,
        "levelName": memberLevel.name if memberLevel is not None else "Unknown Level",
        "levelOrder": memberLevel.levelOrder if memberLevel is not None else 0,
        "skills": buildSkillItems(memberUser.skills) if memberUser is not None else [],
    }


class TeamMembershipService(BaseService):
    """成员业务服务：加入退出、成员管理、子管理员与级别调整。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化团队仓储。"""
        super().__init__(db)
        self.teamRepository = TeamRepository(db)

    def joinTeam(self, currentUser: User, payload: JoinTeamRequest) -> dict:
        """加入团队入口：优先按邀请码加入，否则按团队编号与加入方式处理。"""
        inviteCode = (payload.inviteCode or "").strip()
        if inviteCode:
            return self.joinByInviteCode(currentUser, inviteCode)
        if payload.teamId is None:
            raise validationError("Provide either a team ID or an invite code")
        return self.joinByTeamId(currentUser, payload.teamId, payload.message)

    def joinByInviteCode(self, currentUser: User, inviteCode: str) -> dict:
        """邀请码加入：校验邀请码有效性、团队认证状态、过期时间与使用次数。"""
        team = self.teamRepository.findTeamByInviteCode(inviteCode)
        if team is None:
            raise notFound("Invalid invite code")
        requireJoinableTeam(team)
        if team.inviteExpiresAt is not None and team.inviteExpiresAt < getCurrentTime():
            raise validationError("Invite code has expired. Please contact the team admin.")
        if team.inviteMaxUses and team.inviteUsedCount >= team.inviteMaxUses:
            raise validationError("Invite code has reached its usage limit")
        if self.teamRepository.getMembership(team.id, currentUser.id) is not None:
            raise conflict("You are already a member of this team")
        createMemberAtLowestLevel(self.db, team, currentUser)
        team.inviteUsedCount = (team.inviteUsedCount or 0) + 1
        self.commit()
        return buildJoinTeamResult("joined", team, "Joined the team with the invite code")

    def joinByTeamId(self, currentUser: User, teamId: int, message: str | None) -> dict:
        """按团队编号加入：按 free / approval / inviteOnly 三种方式分别处理。"""
        team = self.teamRepository.getById(teamId)
        if team is None:
            raise notFound("Team not found")
        requireJoinableTeam(team)
        if self.teamRepository.getMembership(team.id, currentUser.id) is not None:
            raise conflict("You are already a member of this team")
        if team.joinMethod == JoinMethod.FREE:
            createMemberAtLowestLevel(self.db, team, currentUser)
            self.commit()
            return buildJoinTeamResult("joined", team, "Joined the team successfully")
        if team.joinMethod == JoinMethod.APPROVAL:
            if self.teamRepository.findPendingJoinRequest(team.id, currentUser.id) is not None:
                raise conflict("You have already submitted a join request. Please wait for review.")
            self.teamRepository.createJoinRequest(
                team.id, currentUser.id, (message or "").strip() or None
            )
            self.commit()
            return buildJoinTeamResult("pending", team, "Join request submitted. Please wait for admin review.")
        raise forbidden("This team only allows joining with an invite code")

    def leaveTeam(self, teamId: int, currentUser: User) -> dict:
        """退出团队：团队管理员需先转让管理员，普通成员/子管理员可直接退出。"""
        _, membership = requireTeamMember(self.db, teamId, currentUser)
        requireCanLeaveTeam(membership)
        self.db.delete(membership)
        self.commit()
        return {"message": "Left the team"}

    def listMembers(self, teamId: int, currentUser: User) -> list[dict]:
        """查询团队成员列表（要求当前用户是团队成员）。"""
        requireTeamMember(self.db, teamId, currentUser)
        return [
            buildTeamMemberItemDict(member)
            for member in self.teamRepository.listMembers(teamId)
        ]

    def kickMember(self, teamId: int, targetUserId: int, currentUser: User) -> dict:
        """踢出成员：管理员可踢任何人，子管理员仅可踢级别更低的普通成员。"""
        _, operatorMembership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamManager(operatorMembership)
        targetMembership = self.teamRepository.getMembership(teamId, targetUserId)
        if targetMembership is None:
            raise notFound("This user is not a member of the team")
        requireCanManageTargetMember(operatorMembership, targetMembership)
        if targetMembership.role == TeamRole.ADMIN:
            raise forbidden("The team admin cannot be removed")
        self.db.delete(targetMembership)
        self.commit()
        return {"message": "Member removed"}

    def setMemberRole(
        self, teamId: int, targetUserId: int, currentUser: User, payload: SetMemberRoleRequest
    ) -> dict:
        """设置/撤销子管理员：仅团队管理员可操作，不能修改管理员本人角色。"""
        _, operatorMembership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamAdmin(operatorMembership)
        targetMembership = self.teamRepository.getMembership(teamId, targetUserId)
        if targetMembership is None:
            raise notFound("This user is not a member of the team")
        requireCanManageTargetMember(operatorMembership, targetMembership)
        if targetMembership.role == TeamRole.ADMIN:
            raise forbidden("The team admin role cannot be changed")
        targetMembership.role = (
            TeamRole.SUB_ADMIN if payload.role == "subAdmin" else TeamRole.MEMBER
        )
        self.commit()
        return {"message": "Member role updated"}

    def setMemberLevel(
        self, teamId: int, targetUserId: int, currentUser: User, payload: SetMemberLevelRequest
    ) -> dict:
        """调整成员级别：管理员不限，子管理员不能把成员调到与自己同级或更高。"""
        _, operatorMembership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamManager(operatorMembership)
        targetMembership = self.teamRepository.getMembership(teamId, targetUserId)
        if targetMembership is None:
            raise notFound("This user is not a member of the team")
        targetLevel = self.teamRepository.getLevel(payload.levelId)
        if targetLevel is None or targetLevel.teamId != teamId:
            raise validationError("The target level does not belong to this team")
        requireCanManageTargetMember(operatorMembership, targetMembership)
        operatorLevel = operatorMembership.level
        if (
            operatorMembership.role == TeamRole.SUB_ADMIN
            and operatorLevel is not None
            and targetLevel.levelOrder >= operatorLevel.levelOrder
        ):
            raise forbidden("Sub-admins cannot set a member to their own level or higher")
        targetMembership.levelId = targetLevel.id
        self.commit()
        return {"message": "Member level updated"}

    def listMemberCandidates(self, teamId: int, currentUser: User) -> list[dict]:
        """任务可选成员候选列表：管理员/子管理员或级别允许发布任务的成员可见。"""
        _, operatorMembership = requireTeamMember(self.db, teamId, currentUser)
        operatorLevel = operatorMembership.level
        canViewCandidates = operatorMembership.role in (TeamRole.ADMIN, TeamRole.SUB_ADMIN) or (
            operatorLevel is not None and bool(operatorLevel.canCreateTask)
        )
        if not canViewCandidates:
            raise forbidden("Only admins, sub-admins, or members allowed to publish tasks can view member candidates")
        return [
            buildMemberCandidateItem(member)
            for member in self.teamRepository.listMembers(teamId)
        ]