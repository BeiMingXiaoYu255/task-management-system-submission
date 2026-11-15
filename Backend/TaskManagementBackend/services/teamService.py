"""团队核心业务服务：创建/列表/详情/修改/解散/转让与邀请码生成。

同时提供团队域公共序列化函数，供成员服务与团队管理服务复用，保证
TeamBrief / TeamLevel / TeamMemberItem / TeamDetail 结构与前端类型完全一致。
"""

import secrets
import string
from datetime import timedelta

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import AppException, validationError
from TaskManagementBackend.core.permissions import (
    requireTeamAdmin,
    requireTeamManager,
    requireTeamMember,
)
from TaskManagementBackend.models import Team, TeamLevel, TeamMember, User
from TaskManagementBackend.models.enums import JoinMethod, TeamRole, TeamStatus
from TaskManagementBackend.repositories.teamRepository import TeamRepository
from TaskManagementBackend.schemas.teamSchema import (
    CreateTeamRequest,
    GenerateInviteCodeRequest,
    UpdateTeamRequest,
)
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.serializationService import buildSkillItems, buildTeamBrief
from TaskManagementBackend.utils.timeUtils import getCurrentTime

# 创建团队时自动生成的默认级别：(级别名称, 级别数值)，数值越大级别越高
DEFAULT_TEAM_LEVELS = (("Senior Member", 3), ("Intermediate Member", 2), ("Junior Member", 1))

# 邀请码字符集与长度
INVITE_CODE_CHARACTERS = string.ascii_uppercase + string.digits
INVITE_CODE_LENGTH = 10


def buildTeamLevelDict(level: TeamLevel, memberCount: int) -> dict:
    """把团队级别实体转换为 TeamLevel 响应字典。"""
    return {
        "id": level.id,
        "teamId": level.teamId,
        "name": level.name,
        "levelOrder": level.levelOrder,
        "canCreateTask": bool(level.canCreateTask),
        "memberCount": memberCount,
    }


def buildTeamMemberItemDict(member: TeamMember) -> dict:
    """把成员关系（含用户与技能）转换为 TeamMemberItem 响应字典。"""
    memberUser = member.user
    memberLevel = member.level
    return {
        "id": member.id,
        "userId": member.userId,
        "username": memberUser.username if memberUser is not None else "deleted",
        "nickname": memberUser.nickname if memberUser is not None else "Deleted User",
        "avatar": memberUser.avatar if memberUser is not None else None,
        "role": member.role.value,
        "levelId": member.levelId,
        "levelName": memberLevel.name if memberLevel is not None else "Unknown Level",
        "levelOrder": memberLevel.levelOrder if memberLevel is not None else 0,
        "joinedAt": member.joinedAt,
        "skills": buildSkillItems(memberUser.skills) if memberUser is not None else [],
    }


def buildTeamDetailDict(
    team: Team,
    currentMembership: TeamMember,
    levels: list[TeamLevel],
    members: list[TeamMember],
) -> dict:
    """组装 TeamDetail 响应：团队信息 + 级别（含成员数）+ 成员 + 当前用户身份。"""
    levelMemberCounts: dict[int, int] = {}
    for member in members:
        levelMemberCounts[member.levelId] = levelMemberCounts.get(member.levelId, 0) + 1
    detail = buildTeamBrief(team, len(members))
    currentLevel = currentMembership.level
    canViewInviteCode = currentMembership.role in (TeamRole.ADMIN, TeamRole.SUB_ADMIN)
    detail.update(
        {
            "inviteCode": team.inviteCode if canViewInviteCode else None,
            "inviteExpiresAt": team.inviteExpiresAt if canViewInviteCode else None,
            "levels": [
                buildTeamLevelDict(level, levelMemberCounts.get(level.id, 0))
                for level in levels
            ],
            "members": [buildTeamMemberItemDict(member) for member in members],
            "currentUserRole": currentMembership.role.value,
            "currentUserLevelOrder": currentLevel.levelOrder if currentLevel is not None else 0,
        }
    )
    return detail


class TeamService(BaseService):
    """团队业务服务：团队生命周期与邀请码管理。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化团队仓储。"""
        super().__init__(db)
        self.teamRepository = TeamRepository(db)

    def createTeam(self, currentUser: User, payload: CreateTeamRequest) -> dict:
        """创建团队：创建者自动成为团队管理员并持有最高级别，团队默认 pending。"""
        teamName = (payload.name or "").strip()
        if not 1 <= len(teamName) <= 100:
            raise validationError("Team name must be 1-100 characters")
        description = (payload.description or "").strip() or None
        team = Team(
            name=teamName,
            description=description,
            joinMethod=JoinMethod(payload.joinMethod.value),
            status=TeamStatus.PENDING,
            createdBy=currentUser.id,
            inviteMaxUses=0,
            inviteUsedCount=0,
        )
        self.db.add(team)
        self.db.flush()
        topLevel: TeamLevel | None = None
        for levelName, levelOrder in DEFAULT_TEAM_LEVELS:
            level = TeamLevel(
                teamId=team.id, name=levelName, levelOrder=levelOrder, canCreateTask=True
            )
            self.db.add(level)
            self.db.flush()
            if levelOrder == 3:
                topLevel = level
        self.teamRepository.addMember(
            teamId=team.id,
            userId=currentUser.id,
            role=TeamRole.ADMIN,
            levelId=topLevel.id if topLevel is not None else 0,
        )
        self.commit()
        return self.getTeamDetail(team.id, currentUser)

    def listMyTeams(self, currentUser: User) -> list[dict]:
        """查询当前用户加入的全部团队（含自己创建的待认证团队），返回 TeamBrief 数组。"""
        teams = self.teamRepository.listTeamsForUser(currentUser.id)
        memberCounts = self.teamRepository.countMembersByTeamIds([team.id for team in teams])
        return [buildTeamBrief(team, memberCounts.get(team.id, 0)) for team in teams]

    def getTeamDetail(self, teamId: int, currentUser: User) -> dict:
        """查询团队详情：要求当前用户是该团队成员。"""
        team, membership = requireTeamMember(self.db, teamId, currentUser)
        levels = self.teamRepository.listLevels(teamId)
        members = self.teamRepository.listMembers(teamId)
        return buildTeamDetailDict(team, membership, levels, members)

    def updateTeam(self, teamId: int, currentUser: User, payload: UpdateTeamRequest) -> dict:
        """修改团队信息：仅团队管理员可操作，支持部分字段更新。"""
        _, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamAdmin(membership)
        team = self.teamRepository.getById(teamId)
        providedFields = payload.model_fields_set
        if "name" in providedFields:
            teamName = (payload.name or "").strip()
            if not 1 <= len(teamName) <= 100:
                raise validationError("Team name must be 1-100 characters")
            team.name = teamName
        if "description" in providedFields:
            team.description = (payload.description or "").strip() or None
        if "joinMethod" in providedFields and payload.joinMethod is not None:
            team.joinMethod = JoinMethod(payload.joinMethod.value)
        self.commit()
        return self.getTeamDetail(teamId, currentUser)

    def deleteTeam(self, teamId: int, currentUser: User, confirmName: str) -> dict:
        """解散团队：管理员输入团队名称二次确认后删除全部团队数据。"""
        team, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamAdmin(membership)
        if (confirmName or "").strip() != team.name:
            raise validationError("Confirmation name does not match the team name. The team cannot be dissolved.")
        self.db.delete(team)
        self.commit()
        return {"message": "Team dissolved"}

    def transferAdmin(self, teamId: int, currentUser: User, newAdminUserId: int) -> dict:
        """转让团队管理员：目标必须是团队成员，自己降为普通成员。"""
        _, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamAdmin(membership)
        if newAdminUserId == currentUser.id:
            raise validationError("Cannot transfer team ownership to yourself")
        targetMembership = self.teamRepository.getMembership(teamId, newAdminUserId)
        if targetMembership is None:
            raise validationError("Target user is not a team member")
        membership.role = TeamRole.MEMBER
        targetMembership.role = TeamRole.ADMIN
        self.commit()
        return self.getTeamDetail(teamId, currentUser)

    def generateInviteCode(
        self, teamId: int, currentUser: User, payload: GenerateInviteCodeRequest
    ) -> dict:
        """生成邀请码：管理员/子管理员可操作，可设置有效期与最大使用次数。"""
        _, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamManager(membership)
        team = self.teamRepository.getById(teamId)
        expiresInHours = payload.expiresInHours
        team.inviteCode = self.buildUniqueInviteCode()
        team.inviteExpiresAt = (
            getCurrentTime() + timedelta(hours=expiresInHours)
            if expiresInHours is not None
            else None
        )
        team.inviteMaxUses = max(0, payload.maxUses or 0)
        team.inviteUsedCount = 0
        self.commit()
        return self.getTeamDetail(teamId, currentUser)

    def buildUniqueInviteCode(self) -> str:
        """生成全库唯一的邀请码（大写字母 + 数字，长度 10）。"""
        for _ in range(10):
            candidateCode = "".join(
                secrets.choice(INVITE_CODE_CHARACTERS) for _ in range(INVITE_CODE_LENGTH)
            )
            if self.teamRepository.findTeamByInviteCode(candidateCode) is None:
                return candidateCode
        raise AppException("INTERNAL_ERROR", "Failed to generate invite code. Please try again later.", 500)