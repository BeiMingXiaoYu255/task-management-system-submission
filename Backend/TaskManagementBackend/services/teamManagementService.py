"""团队治理业务服务：团队级别 CRUD 与入团申请审批。

级别规则：levelOrder 在团队内唯一、数值越大级别越高；有成员引用的级别不可删除。
审批规则：管理员/子管理员可查看待处理申请并通过或拒绝，通过后申请人加入最低级别。
"""

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import conflict, notFound, validationError
from TaskManagementBackend.core.permissions import (
    requireTeamAdmin,
    requireTeamManager,
    requireTeamMember,
)
from TaskManagementBackend.models import Team, TeamJoinRequest, TeamLevel, User
from TaskManagementBackend.models.enums import JoinRequestStatus
from TaskManagementBackend.repositories.teamRepository import TeamRepository
from TaskManagementBackend.schemas.teamSchema import (
    HandleJoinRequestRequest,
    SaveLevelRequest,
)
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.teamMembershipService import createMemberAtLowestLevel
from TaskManagementBackend.services.teamService import buildTeamLevelDict
from TaskManagementBackend.utils.timeUtils import getCurrentTime


def buildJoinRequestItem(joinRequest: TeamJoinRequest) -> dict:
    """把入团申请实体转换为 JoinRequestItem 响应字典。"""
    applicant = joinRequest.user
    return {
        "id": joinRequest.id,
        "teamId": joinRequest.teamId,
        "userId": joinRequest.userId,
        "username": applicant.username if applicant is not None else "deleted",
        "nickname": applicant.nickname if applicant is not None else "Deleted User",
        "message": joinRequest.message,
        "status": joinRequest.status.value if hasattr(joinRequest.status, "value") else joinRequest.status,
        "createdAt": joinRequest.createdAt,
    }


class TeamManagementService(BaseService):
    """团队治理服务：级别管理与入团申请审批。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化团队仓储。"""
        super().__init__(db)
        self.teamRepository = TeamRepository(db)

    def listLevels(self, teamId: int, currentUser: User) -> list[dict]:
        """级别列表（成员可见），附带每个级别的成员数量。"""
        requireTeamMember(self.db, teamId, currentUser)
        return [
            buildTeamLevelDict(level, self.teamRepository.countMembersAtLevel(level.id))
            for level in self.teamRepository.listLevels(teamId)
        ]

    def createLevel(self, teamId: int, currentUser: User, payload: SaveLevelRequest) -> dict:
        """新建团队级别：仅管理员可操作，级别数值团队内唯一。"""
        _, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamAdmin(membership)
        levelName = (payload.name or "").strip()
        if not 1 <= len(levelName) <= 50:
            raise validationError("Level name must be 1-50 characters")
        if self.teamRepository.findLevelByOrder(teamId, payload.levelOrder) is not None:
            raise conflict("This level order already exists")
        level = TeamLevel(
            teamId=teamId,
            name=levelName,
            levelOrder=payload.levelOrder,
            canCreateTask=payload.canCreateTask,
        )
        self.db.add(level)
        self.db.flush()
        self.commit()
        return buildTeamLevelDict(level, 0)

    def updateLevel(
        self, teamId: int, levelId: int, currentUser: User, payload: SaveLevelRequest
    ) -> dict:
        """修改团队级别：仅管理员可操作，级别数值变更后仍需团队内唯一。"""
        _, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamAdmin(membership)
        level = self.teamRepository.getLevel(levelId)
        if level is None or level.teamId != teamId:
            raise notFound("Team level not found")
        levelName = (payload.name or "").strip()
        if not 1 <= len(levelName) <= 50:
            raise validationError("Level name must be 1-50 characters")
        conflictLevel = self.teamRepository.findLevelByOrder(teamId, payload.levelOrder)
        if conflictLevel is not None and conflictLevel.id != level.id:
            raise conflict("This level order already exists")
        level.name = levelName
        level.levelOrder = payload.levelOrder
        level.canCreateTask = payload.canCreateTask
        self.commit()
        return buildTeamLevelDict(
            level, self.teamRepository.countMembersAtLevel(level.id)
        )

    def deleteLevel(self, teamId: int, levelId: int, currentUser: User) -> dict:
        """删除团队级别：仅管理员可操作，级别下仍有成员或仅剩一个级别时禁止删除。"""
        _, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamAdmin(membership)
        level = self.teamRepository.getLevel(levelId)
        if level is None or level.teamId != teamId:
            raise notFound("Team level not found")
        if self.teamRepository.countMembersAtLevel(level.id) > 0:
            raise validationError("This level still has members and cannot be deleted")
        if self.teamRepository.countLevels(teamId) <= 1:
            raise validationError("A team must keep at least one level")
        self.db.delete(level)
        self.commit()
        return {"message": "Level deleted"}

    def listJoinRequests(self, teamId: int, currentUser: User) -> list[dict]:
        """待处理入团申请列表（管理员/子管理员可见）。"""
        _, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamManager(membership)
        return [
            buildJoinRequestItem(joinRequest)
            for joinRequest in self.teamRepository.listPendingJoinRequests(teamId)
        ]

    def handleJoinRequest(
        self,
        teamId: int,
        requestId: int,
        currentUser: User,
        payload: HandleJoinRequestRequest,
    ) -> dict:
        """审批入团申请：通过则加入最低级别，拒绝则仅更新申请状态。"""
        _, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamManager(membership)
        joinRequest = self.teamRepository.getJoinRequest(teamId, requestId)
        if joinRequest is None:
            raise notFound("Join request not found")
        if joinRequest.status != JoinRequestStatus.PENDING:
            raise conflict("This join request has already been processed")
        joinRequest.handledBy = currentUser.id
        joinRequest.handledAt = getCurrentTime()
        if payload.action == "approve":
            joinRequest.status = JoinRequestStatus.APPROVED
            if self.teamRepository.getMembership(teamId, joinRequest.userId) is None:
                team = self.teamRepository.getById(teamId)
                applicant = self.db.get(User, joinRequest.userId)
                if applicant is not None and team is not None:
                    createMemberAtLowestLevel(self.db, team, applicant)
            self.commit()
            return {"message": "Join request approved"}
        joinRequest.status = JoinRequestStatus.REJECTED
        self.commit()
        return {"message": "Join request rejected"}
