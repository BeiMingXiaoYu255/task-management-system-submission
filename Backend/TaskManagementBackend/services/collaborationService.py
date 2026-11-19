"""协作关系业务服务：协作目录、申请/确认/拒绝/结束、协作列表详情与单位候选成员。

状态机：pending（申请中）→ 接收方管理员确认 active / 拒绝 rejected；active → 任一单位管理员结束 ended。
同一对协作单位之间只允许存在一条 pending/active 记录（双向校验）；允许同一父团队下两个不同子团队协作。
序列化与通知定义构造由 collaborationSharedService 提供，双审核由 collaborationTaskReviewService 负责。
"""

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import conflict, forbidden, notFound, validationError
from TaskManagementBackend.core.permissions import getTeamOrRaise, requireActiveTeam, requireTeamMember
from TaskManagementBackend.models import TeamCollaboration, User
from TaskManagementBackend.models.enums import CollaborationStatus, NotificationType
from TaskManagementBackend.repositories.collaborationRepository import CollaborationRepository
from TaskManagementBackend.repositories.subTeamRepository import SubTeamRepository
from TaskManagementBackend.repositories.teamRepository import TeamRepository
from TaskManagementBackend.schemas.collaborationSchema import (
    CollaborationListQuery,
    ConfirmCollaborationRequest,
    CreateCollaborationRequest,
    EndCollaborationRequest,
)
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.collaborationPermissionService import (
    CollaborationViewerContext, buildCollaborationUnit, getSubTeamOrRaise,
    isUserUnitMember, listUnitAdminUserIds, listUnitMemberCandidates,
)
from TaskManagementBackend.services.collaborationSharedService import (
    buildCollaborationItem,
    buildInitiatorNotificationRecipients,
    buildNotificationDefinitions,
)
from TaskManagementBackend.services.notificationService import createNotifications


class CollaborationService(BaseService):
    """协作关系业务服务：编排单位权限、状态机推进、通知与响应序列化。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化协作、团队、子团队仓储。"""
        super().__init__(db)
        self.collaborationRepository = CollaborationRepository(db)
        self.teamRepository = TeamRepository(db)
        self.subTeamRepository = SubTeamRepository(db)

    def _loadCollaborationOrRaise(self, collaborationId: int) -> TeamCollaboration:
        """加载协作关系（预加载双方单位与对接人），不存在时抛 404。"""
        collaboration = self.collaborationRepository.getWithDetails(collaborationId)
        if collaboration is None:
            raise notFound("Collaboration not found")
        return collaboration

    def _requireViewPermission(
        self, collaboration: TeamCollaboration, viewerContext: CollaborationViewerContext
    ) -> None:
        """校验协作关系查看权限：双方单位成员（子团队含父团队管理员）或对接人。"""
        canView = viewerContext.canViewUnit(
            collaboration.initiatorTeamId, collaboration.initiatorSubTeamId
        ) or viewerContext.canViewUnit(collaboration.targetTeamId, collaboration.targetSubTeamId)
        if not canView:
            raise forbidden("You are not a member of this collaboration")

    def _reloadAndBuildItem(self, collaborationId: int, viewerContext: CollaborationViewerContext) -> dict:
        """提交事务后重新加载协作关系并序列化，避免关系集合残留旧状态。"""
        self.db.expire_all()
        collaboration = self._loadCollaborationOrRaise(collaborationId)
        return buildCollaborationItem(collaboration, viewerContext)

    def _unitName(self, collaboration: TeamCollaboration, isInitiator: bool) -> str:
        """取协作关系某一方单位的展示全称。"""
        if isInitiator:
            return buildCollaborationUnit(
                collaboration.initiatorTeam, collaboration.initiatorSubTeam
            )["unitName"]
        return buildCollaborationUnit(collaboration.targetTeam, collaboration.targetSubTeam)[
            "unitName"
        ]

    def getDirectory(self, currentUser: User) -> list[dict]:
        """可申请协作的团队/子团队目录：仅已认证团队，含成员数、子团队与负责人。"""
        teams = self.collaborationRepository.listActiveTeamsWithSubTeams()
        teamMemberCounts = self.teamRepository.countMembersByTeamIds([team.id for team in teams])
        subTeams = [subTeam for team in teams for subTeam in team.subTeams]
        subTeamMemberCounts = self.subTeamRepository.countMembersBySubTeamIds(
            [subTeam.id for subTeam in subTeams]
        )
        return [
            {
                "teamId": team.id,
                "teamName": team.name,
                "description": team.description,
                "memberCount": teamMemberCounts.get(team.id, 0),
                "subTeams": [
                    {
                        "subTeamId": subTeam.id,
                        "name": subTeam.name,
                        "memberCount": subTeamMemberCounts.get(subTeam.id, 0),
                        "leaderNickname": subTeam.leaderNickname,
                    }
                    for subTeam in team.subTeams
                ],
            }
            for team in teams
        ]

    def listUnitCandidates(self, currentUser: User, teamId: int, subTeamId: int | None) -> list[dict]:
        """协作单位候选成员：选择对接人与指派执行人时使用；要求当前用户是团队成员。"""
        requireTeamMember(self.db, teamId, currentUser)
        if subTeamId is not None:
            getSubTeamOrRaise(self.db, teamId, subTeamId)
        return listUnitMemberCandidates(self.db, teamId, subTeamId)

    def createCollaboration(self, currentUser: User, request: CreateCollaborationRequest) -> dict:
        """发起协作申请：发起单位管理员指定己方对接人，接收单位待确认。"""
        initiatorTeam = getTeamOrRaise(self.db, request.initiatorTeamId)
        targetTeam = getTeamOrRaise(self.db, request.targetTeamId)
        requireActiveTeam(initiatorTeam)
        requireActiveTeam(targetTeam)
        if request.initiatorSubTeamId is not None:
            getSubTeamOrRaise(self.db, request.initiatorTeamId, request.initiatorSubTeamId)
        if request.targetSubTeamId is not None:
            getSubTeamOrRaise(self.db, request.targetTeamId, request.targetSubTeamId)
        if (
            request.initiatorTeamId == request.targetTeamId
            and request.initiatorSubTeamId == request.targetSubTeamId
        ):
            raise validationError("A collaboration unit cannot collaborate with itself")
        viewerContext = CollaborationViewerContext.load(self.db, currentUser)
        if not viewerContext.isUnitAdmin(request.initiatorTeamId, request.initiatorSubTeamId):
            raise forbidden("Only an initiating unit admin can create a collaboration request")
        if not isUserUnitMember(
            self.db,
            request.initiatorTeamId,
            request.initiatorSubTeamId,
            request.initiatorLiaisonUserId,
        ):
            raise validationError("The initiator liaison must be a member of the initiating unit")
        if self.collaborationRepository.findConflictingPair(
            request.initiatorTeamId,
            request.initiatorSubTeamId,
            request.targetTeamId,
            request.targetSubTeamId,
        ) is not None:
            raise conflict("An open collaboration already exists between these units")
        collaboration = TeamCollaboration(
            initiatorTeamId=request.initiatorTeamId,
            initiatorSubTeamId=request.initiatorSubTeamId,
            targetTeamId=request.targetTeamId,
            targetSubTeamId=request.targetSubTeamId,
            initiatorLiaisonUserId=request.initiatorLiaisonUserId,
            targetLiaisonUserId=None,
            status=CollaborationStatus.PENDING,
            message=request.message,
            createdBy=currentUser.id,
        )
        self.collaborationRepository.add(collaboration)
        initiatorUnitName = buildCollaborationUnit(
            initiatorTeam, collaboration.initiatorSubTeam
        )["unitName"]
        targetUnitName = buildCollaborationUnit(targetTeam, collaboration.targetSubTeam)[
            "unitName"
        ]
        createNotifications(
            self.db,
            buildNotificationDefinitions(
                listUnitAdminUserIds(
                    self.db, request.targetTeamId, request.targetSubTeamId
                ),
                NotificationType.COLLABORATION_APPLIED,
                "Collaboration request received",
                f'"{initiatorUnitName}" requested collaboration with "{targetUnitName}". Confirm or reject the request.',
                collaborationId=collaboration.id,
            ),
        )
        self.commit()
        return self._reloadAndBuildItem(collaboration.id, viewerContext)

    def listCollaborations(self, currentUser: User, query: CollaborationListQuery) -> dict:
        """与我相关的协作关系分页列表（我所在单位、我管理的单位或我作为对接人）。"""
        if query.teamId is not None:
            requireTeamMember(self.db, query.teamId, currentUser)
        viewerContext = CollaborationViewerContext.load(self.db, currentUser)
        adminTeamIds = [
            teamId for teamId, role in viewerContext.teamRoles.items() if role.value == "admin"
        ]
        collaborations, total = self.collaborationRepository.listRelated(
            currentUser.id,
            list(viewerContext.teamRoles.keys()),
            adminTeamIds,
            list(viewerContext.memberSubTeamIds),
            query.status,
            query.teamId,
            query.page,
            query.pageSize,
        )
        return {
            "items": [
                buildCollaborationItem(collaboration, viewerContext)
                for collaboration in collaborations
            ],
            "total": total,
            "page": query.page,
            "pageSize": query.pageSize,
        }

    def getCollaborationDetail(self, currentUser: User, collaborationId: int) -> dict:
        """协作详情：参与单位成员可查看，含当前用户动作标记。"""
        collaboration = self._loadCollaborationOrRaise(collaborationId)
        viewerContext = CollaborationViewerContext.load(self.db, currentUser)
        self._requireViewPermission(collaboration, viewerContext)
        return buildCollaborationItem(collaboration, viewerContext)

    def confirmCollaboration(
        self, currentUser: User, collaborationId: int, request: ConfirmCollaborationRequest
    ) -> dict:
        """接收单位管理员确认（指定接收方对接人）或拒绝协作申请。"""
        collaboration = self._loadCollaborationOrRaise(collaborationId)
        if collaboration.status != CollaborationStatus.PENDING:
            raise validationError("Only a pending collaboration can be confirmed or rejected")
        viewerContext = CollaborationViewerContext.load(self.db, currentUser)
        if not viewerContext.isUnitAdmin(
            collaboration.targetTeamId, collaboration.targetSubTeamId
        ):
            raise forbidden("Only a receiving unit admin can confirm or reject the collaboration request")
        targetUnitName = self._unitName(collaboration, False)
        if request.approved:
            if request.targetLiaisonUserId is None:
                raise validationError("A receiver liaison is required to confirm the collaboration")
            if not isUserUnitMember(
                self.db,
                collaboration.targetTeamId,
                collaboration.targetSubTeamId,
                request.targetLiaisonUserId,
            ):
                raise validationError("The receiver liaison must be a member of the receiving unit")
            collaboration.status = CollaborationStatus.ACTIVE
            collaboration.targetLiaisonUserId = request.targetLiaisonUserId
            notificationType = NotificationType.COLLABORATION_CONFIRMED
            title = "Collaboration request approved"
            content = f'Your collaboration with "{targetUnitName}" is now active.'
        else:
            collaboration.status = CollaborationStatus.REJECTED
            collaboration.rejectComment = request.comment
            notificationType = NotificationType.COLLABORATION_REJECTED
            title = "Collaboration request rejected"
            content = f'"{targetUnitName}" rejected the collaboration request.'
        createNotifications(
            self.db,
            buildNotificationDefinitions(
                buildInitiatorNotificationRecipients(self.db, collaboration),
                notificationType,
                title,
                content,
                collaborationId=collaboration.id,
            ),
        )
        self.commit()
        return self._reloadAndBuildItem(collaborationId, viewerContext)

    def endCollaboration(
        self, currentUser: User, collaborationId: int, request: EndCollaborationRequest
    ) -> dict:
        """结束协作关系：任一单位管理员可结束已生效协作，已派发任务不受影响。"""
        collaboration = self._loadCollaborationOrRaise(collaborationId)
        if collaboration.status != CollaborationStatus.ACTIVE:
            raise validationError("Only an active collaboration can be ended")
        viewerContext = CollaborationViewerContext.load(self.db, currentUser)
        isInitiatorAdmin = viewerContext.isUnitAdmin(
            collaboration.initiatorTeamId, collaboration.initiatorSubTeamId
        )
        isTargetAdmin = viewerContext.isUnitAdmin(
            collaboration.targetTeamId, collaboration.targetSubTeamId
        )
        if not isInitiatorAdmin and not isTargetAdmin:
            raise forbidden("Only an admin of either unit can end the collaboration")
        collaboration.status = CollaborationStatus.ENDED
        collaboration.rejectComment = request.comment
        recipientUserIds = set(buildInitiatorNotificationRecipients(self.db, collaboration))
        recipientUserIds.update(
            listUnitAdminUserIds(self.db, collaboration.targetTeamId, collaboration.targetSubTeamId)
        )
        if collaboration.targetLiaisonUserId is not None:
            recipientUserIds.add(int(collaboration.targetLiaisonUserId))
        createNotifications(
            self.db,
            buildNotificationDefinitions(
                recipientUserIds,
                NotificationType.COLLABORATION_ENDED,
                "Collaboration ended",
                f'Collaboration between "{self._unitName(collaboration, True)}" and '
                f'"{self._unitName(collaboration, False)}" has ended.',
                collaborationId=collaboration.id,
            ),
        )
        self.commit()
        return self._reloadAndBuildItem(collaborationId, viewerContext)
