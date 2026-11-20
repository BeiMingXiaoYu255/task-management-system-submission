"""子团队业务服务：子团队 CRUD、成员维护、权限校验与子团队任务视图。

权限规则（服务层强制）：
    1. 父团队管理员可创建/删除子团队、任免子负责人、维护成员；
    2. 子负责人可修改名称/简介/成员（不能更换负责人）；
    3. 子团队列表与详情对父团队全体成员可见；
    4. 子团队任务仅子团队成员与父团队管理者可见。
"""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import conflict, forbidden, notFound, validationError
from TaskManagementBackend.core.permissions import (
    getMembershipOrNone,
    requireTeamAdmin,
    requireTeamMember,
)
from TaskManagementBackend.models import SubTeam, Task, TeamMember, User
from TaskManagementBackend.models.enums import TeamRole
from TaskManagementBackend.repositories.subTeamRepository import SubTeamRepository
from TaskManagementBackend.repositories.teamRepository import TeamRepository
from TaskManagementBackend.schemas.subTeamSchema import (
    CreateSubTeamRequest,
    SetSubTeamMembersRequest,
    UpdateSubTeamRequest,
)
from TaskManagementBackend.schemas.taskSchema import TaskListQuery
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.collaborationPermissionService import (
    CollaborationViewerContext,
)
from TaskManagementBackend.services.taskService import TaskService

MIN_SUB_TEAM_NAME_LENGTH = 1
MAX_SUB_TEAM_NAME_LENGTH = 100


class SubTeamService(BaseService):
    """子团队业务服务：编排权限校验、成员维护与响应序列化。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化子团队与团队仓储。"""
        super().__init__(db)
        self.subTeamRepository = SubTeamRepository(db)
        self.teamRepository = TeamRepository(db)

    def _loadSubTeamOrRaise(self, teamId: int, subTeamId: int) -> SubTeam:
        """按父团队加载子团队，不存在时抛 404。"""
        subTeam = self.subTeamRepository.getByIdAndTeam(teamId, subTeamId)
        if subTeam is None:
            raise notFound("Sub-team not found")
        return subTeam

    def _validateTeamMemberUserIds(self, teamId: int, userIds: list[int]) -> list[int]:
        """校验用户主键均为父团队成员并去重，返回校验后的用户主键列表。"""
        uniqueUserIds = list(dict.fromkeys(int(userId) for userId in userIds))
        if not uniqueUserIds:
            return []
        existingUserIds = {
            int(userId)
            for userId in self.db.execute(
                select(TeamMember.userId).where(
                    TeamMember.teamId == teamId, TeamMember.userId.in_(uniqueUserIds)
                )
            ).scalars().all()
        }
        missingUserIds = [userId for userId in uniqueUserIds if userId not in existingUserIds]
        if missingUserIds:
            raise validationError("Sub-team members must be parent team members: " + ",".join(map(str, missingUserIds)))
        return uniqueUserIds

    def _resolveMyRole(
        self, membership: TeamMember, subTeam: SubTeam, viewerContext: CollaborationViewerContext
    ) -> str | None:
        """解析当前用户相对子团队的角色：admin / leader / member / None。"""
        if membership.role == TeamRole.ADMIN:
            return "admin"
        if subTeam.leaderUserId == membership.userId:
            return "leader"
        if viewerContext.isSubTeamMember(subTeam.id):
            return "member"
        return None

    def _buildSubTeamItem(
        self, subTeam: SubTeam, memberCount: int, myRole: str | None
    ) -> dict:
        """把子团队 ORM 对象序列化为 SubTeamItem 字典。"""
        return {
            "id": subTeam.id,
            "parentTeamId": subTeam.parentTeamId,
            "name": subTeam.name,
            "description": subTeam.description,
            "leaderUserId": subTeam.leaderUserId,
            "leaderNickname": subTeam.leaderNickname,
            "memberCount": memberCount,
            "createdAt": subTeam.createdAt,
            "myRole": myRole,
        }

    def _buildSubTeamDetail(self, currentUser: User, teamId: int, subTeam: SubTeam) -> dict:
        """构建子团队详情：列表项字段 + 成员列表（含父团队级别信息）。"""
        membership = getMembershipOrNone(self.db, teamId, currentUser.id)
        viewerContext = CollaborationViewerContext.load(self.db, currentUser)
        myRole = (
            self._resolveMyRole(membership, subTeam, viewerContext) if membership is not None else None
        )
        teamMembers = self.teamRepository.listMembers(teamId)
        membershipByUserId = {member.userId: member for member in teamMembers}
        subTeamMembers = self.subTeamRepository.listMembers(subTeam.id)
        members = []
        for subTeamMember in subTeamMembers:
            parentMembership = membershipByUserId.get(subTeamMember.userId)
            user = subTeamMember.user
            level = parentMembership.level if parentMembership is not None else None
            members.append(
                {
                    "userId": subTeamMember.userId,
                    "username": user.username if user is not None else "deleted",
                    "nickname": user.nickname if user is not None else "Deleted User",
                    "avatar": user.avatar if user is not None else None,
                    "levelName": level.name if level is not None else "",
                    "levelOrder": level.levelOrder if level is not None else 0,
                    "isLeader": subTeam.leaderUserId == subTeamMember.userId,
                }
            )
        detail = self._buildSubTeamItem(
            subTeam, self.subTeamRepository.countMembers(subTeam.id), myRole
        )
        detail["members"] = members
        return detail

    def listSubTeams(self, currentUser: User, teamId: int) -> list[dict]:
        """子团队列表：父团队全体成员可查看，含成员数与当前用户角色。"""
        requireTeamMember(self.db, teamId, currentUser)
        viewerContext = CollaborationViewerContext.load(self.db, currentUser)
        subTeams = self.subTeamRepository.listByTeam(teamId)
        memberCounts = self.subTeamRepository.countMembersBySubTeamIds(
            [subTeam.id for subTeam in subTeams]
        )
        membership = getMembershipOrNone(self.db, teamId, currentUser.id)
        items = []
        for subTeam in subTeams:
            myRole = (
                self._resolveMyRole(membership, subTeam, viewerContext)
                if membership is not None
                else None
            )
            items.append(
                self._buildSubTeamItem(subTeam, memberCounts.get(subTeam.id, 0), myRole)
            )
        return items

    def getSubTeamDetail(self, currentUser: User, teamId: int, subTeamId: int) -> dict:
        """子团队详情：父团队全体成员可查看，含成员列表。"""
        requireTeamMember(self.db, teamId, currentUser)
        subTeam = self._loadSubTeamOrRaise(teamId, subTeamId)
        return self._buildSubTeamDetail(currentUser, teamId, subTeam)

    def createSubTeam(self, currentUser: User, teamId: int, request: CreateSubTeamRequest) -> dict:
        """创建子团队：仅父团队管理员，子负责人与初始成员必须属于父团队。"""
        _team, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamAdmin(membership)
        name = (request.name or "").strip()
        if not MIN_SUB_TEAM_NAME_LENGTH <= len(name) <= MAX_SUB_TEAM_NAME_LENGTH:
            raise validationError("Sub-team name must be 1-100 characters")
        if self.subTeamRepository.findByName(teamId, name) is not None:
            raise conflict("A sub-team with this name already exists in the team")
        leaderUserId = request.leaderUserId
        if leaderUserId is not None and getMembershipOrNone(self.db, teamId, leaderUserId) is None:
            raise validationError("The sub-team lead must be a parent team member")
        memberUserIds = self._validateTeamMemberUserIds(teamId, request.memberUserIds or [])
        if leaderUserId is not None and leaderUserId not in memberUserIds:
            # 子负责人自动成为成员，保证负责人可查看子团队任务并以子团队名义操作
            memberUserIds.insert(0, leaderUserId)
        subTeam = SubTeam(
            parentTeamId=teamId,
            name=name,
            description=request.description,
            leaderUserId=leaderUserId,
            createdBy=currentUser.id,
        )
        self.subTeamRepository.add(subTeam)
        for memberUserId in memberUserIds:
            self.subTeamRepository.addMember(subTeam.id, memberUserId)
        self.commit()
        return self.getSubTeamDetail(currentUser, teamId, subTeam.id)

    def updateSubTeam(
        self, currentUser: User, teamId: int, subTeamId: int, request: UpdateSubTeamRequest
    ) -> dict:
        """修改子团队：管理员可改任意字段，子负责人仅可改名称/简介（成员走成员接口）。"""
        _team, membership = requireTeamMember(self.db, teamId, currentUser)
        subTeam = self._loadSubTeamOrRaise(teamId, subTeamId)
        isTeamAdmin = membership.role == TeamRole.ADMIN
        isLeader = subTeam.leaderUserId == currentUser.id
        if not isTeamAdmin and not isLeader:
            raise forbidden("Only a team admin or the sub-team lead can update the sub-team")
        updates = request.model_dump(exclude_unset=True)
        if "leaderUserId" in updates:
            if not isTeamAdmin:
                raise forbidden("Only a team admin can change the sub-team lead")
            newLeaderUserId = updates["leaderUserId"]
            subTeam.leaderUserId = newLeaderUserId
            if newLeaderUserId is not None:
                if getMembershipOrNone(self.db, teamId, newLeaderUserId) is None:
                    raise validationError("The sub-team lead must be a parent team member")
                if self.subTeamRepository.getMember(subTeam.id, newLeaderUserId) is None:
                    self.subTeamRepository.addMember(subTeam.id, newLeaderUserId)
        if updates.get("name") is not None:
            name = str(updates["name"]).strip()
            if not MIN_SUB_TEAM_NAME_LENGTH <= len(name) <= MAX_SUB_TEAM_NAME_LENGTH:
                raise validationError("Sub-team name must be 1-100 characters")
            duplicated = self.subTeamRepository.findByName(teamId, name)
            if duplicated is not None and duplicated.id != subTeam.id:
                raise conflict("A sub-team with this name already exists in the team")
            subTeam.name = name
        if "description" in updates:
            subTeam.description = updates["description"]
        self.commit()
        return self._buildSubTeamDetail(currentUser, teamId, subTeam)

    def deleteSubTeam(self, currentUser: User, teamId: int, subTeamId: int) -> dict:
        """删除子团队：仅父团队管理员；其任务 subTeamId 置空，成员关系级联删除。"""
        _team, membership = requireTeamMember(self.db, teamId, currentUser)
        requireTeamAdmin(membership)
        subTeam = self._loadSubTeamOrRaise(teamId, subTeamId)
        self.db.execute(
            update(Task).where(Task.subTeamId == subTeam.id).values(subTeamId=None)
        )
        self.subTeamRepository.delete(subTeam)
        self.commit()
        return {"message": "Sub-team deleted"}

    def setSubTeamMembers(
        self, currentUser: User, teamId: int, subTeamId: int, request: SetSubTeamMembersRequest
    ) -> dict:
        """覆盖式设置子团队成员：成员必须是父团队成员，子负责人自动保留为成员。"""
        _team, membership = requireTeamMember(self.db, teamId, currentUser)
        subTeam = self._loadSubTeamOrRaise(teamId, subTeamId)
        if membership.role != TeamRole.ADMIN and subTeam.leaderUserId != currentUser.id:
            raise forbidden("Only a team admin or the sub-team lead can manage sub-team members")
        memberUserIds = self._validateTeamMemberUserIds(teamId, request.userIds)
        if subTeam.leaderUserId is not None and subTeam.leaderUserId not in memberUserIds:
            memberUserIds.insert(0, subTeam.leaderUserId)
        self.subTeamRepository.replaceMembers(subTeam.id, memberUserIds)
        self.commit()
        return self._buildSubTeamDetail(currentUser, teamId, subTeam)

    def listSubTeamTasks(
        self, currentUser: User, teamId: int, subTeamId: int, query: TaskListQuery
    ) -> dict:
        """子团队任务分页：子团队成员或父团队管理者可查看（复用团队任务列表逻辑）。"""
        _team, membership = requireTeamMember(self.db, teamId, currentUser)
        subTeam = self._loadSubTeamOrRaise(teamId, subTeamId)
        isManager = membership.role in (TeamRole.ADMIN, TeamRole.SUB_ADMIN)
        if not isManager and self.subTeamRepository.getMember(subTeam.id, currentUser.id) is None:
            raise forbidden("Only sub-team members can view sub-team tasks")
        scopedQuery = query.model_copy(update={"subTeamId": subTeam.id})
        return TaskService(self.db).listTeamTasks(currentUser, teamId, scopedQuery)
