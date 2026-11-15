"""团队管理接口控制器：团队、成员、级别、邀请码与入团申请。

控制器只做参数接收与响应组装，权限校验与业务逻辑在团队相关 Service 中实现。
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.commonSchema import MessageResponse
from TaskManagementBackend.schemas.teamSchema import (
    CreateTeamRequest,
    DeleteTeamRequest,
    GenerateInviteCodeRequest,
    HandleJoinRequestRequest,
    JoinRequestItemResponse,
    JoinTeamRequest,
    JoinTeamResultResponse,
    MemberCandidateItemResponse,
    SaveLevelRequest,
    SetMemberLevelRequest,
    SetMemberRoleRequest,
    TeamBriefResponse,
    TeamDetailResponse,
    TeamLevelResponse,
    TeamMemberItemResponse,
    TransferTeamRequest,
    UpdateTeamRequest,
)
from TaskManagementBackend.services.teamManagementService import TeamManagementService
from TaskManagementBackend.services.teamMembershipService import TeamMembershipService
from TaskManagementBackend.services.teamService import TeamService

# 路由前缀由主应用统一追加 /api/v1
router = APIRouter(tags=["Team Management"], prefix="/teams")


@router.post(
    "",
    response_model=TeamDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create team",
)
def createTeam(
    payload: CreateTeamRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """创建团队：创建者自动成为团队管理员，自动生成三个默认级别。"""
    return TeamService(db).createTeam(currentUser, payload)


@router.get("", response_model=list[TeamBriefResponse], summary="List my teams")
def listMyTeams(
    currentUser: User = Depends(getCurrentUser), db: Session = Depends(getDb)
) -> list[dict]:
    """返回当前用户加入的全部团队（含自己创建的待认证团队）。"""
    return TeamService(db).listMyTeams(currentUser)


@router.post("/join", response_model=JoinTeamResultResponse, summary="Join team")
def joinTeam(
    payload: JoinTeamRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """加入团队：自由加入/申请审核/邀请码三种方式。"""
    return TeamMembershipService(db).joinTeam(currentUser, payload)


@router.get("/{teamId}", response_model=TeamDetailResponse, summary="Team details")
def getTeamDetail(
    teamId: int, currentUser: User = Depends(getCurrentUser), db: Session = Depends(getDb)
) -> dict:
    """返回团队详情（级别、成员与当前用户身份），仅团队成员可见。"""
    return TeamService(db).getTeamDetail(teamId, currentUser)


@router.put("/{teamId}", response_model=TeamDetailResponse, summary="Update team")
def updateTeam(
    teamId: int,
    payload: UpdateTeamRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """修改团队名称、简介与加入方式（仅团队管理员）。"""
    return TeamService(db).updateTeam(teamId, currentUser, payload)


@router.delete("/{teamId}", response_model=MessageResponse, summary="Dissolve team")
def deleteTeam(
    teamId: int,
    payload: DeleteTeamRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """解散团队：需 confirmName 与团队名称完全一致（仅团队管理员）。"""
    return TeamService(db).deleteTeam(teamId, currentUser, payload.confirmName)


@router.post("/{teamId}/transfer", response_model=TeamDetailResponse, summary="Transfer team ownership")
def transferTeamAdmin(
    teamId: int,
    payload: TransferTeamRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """转让团队管理员：自己降为普通成员（仅团队管理员）。"""
    return TeamService(db).transferAdmin(teamId, currentUser, payload.newAdminUserId)


@router.post("/{teamId}/leave", response_model=MessageResponse, summary="Leave team")
def leaveTeam(
    teamId: int, currentUser: User = Depends(getCurrentUser), db: Session = Depends(getDb)
) -> dict:
    """退出团队：团队管理员需先转让管理员。"""
    return TeamMembershipService(db).leaveTeam(teamId, currentUser)


@router.get(
    "/{teamId}/members/candidates",
    response_model=list[MemberCandidateItemResponse],
    summary="List member candidates",
)
def listMemberCandidates(
    teamId: int, currentUser: User = Depends(getCurrentUser), db: Session = Depends(getDb)
) -> list[dict]:
    """返回任务可选成员候选（含级别与技能，管理员/子管理员可见）。"""
    return TeamMembershipService(db).listMemberCandidates(teamId, currentUser)


@router.get(
    "/{teamId}/members",
    response_model=list[TeamMemberItemResponse],
    summary="List team members",
)
def listTeamMembers(
    teamId: int, currentUser: User = Depends(getCurrentUser), db: Session = Depends(getDb)
) -> list[dict]:
    """返回团队成员列表（含级别与技能），仅团队成员可见。"""
    return TeamMembershipService(db).listMembers(teamId, currentUser)


@router.delete(
    "/{teamId}/members/{userId}", response_model=MessageResponse, summary="Remove member"
)
def kickTeamMember(
    teamId: int,
    userId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """踢出成员：管理员可踢任何人，子管理员仅可踢级别更低的普通成员。"""
    return TeamMembershipService(db).kickMember(teamId, userId, currentUser)


@router.put(
    "/{teamId}/members/{userId}/role", response_model=MessageResponse, summary="Set or revoke sub-admin"
)
def setMemberRole(
    teamId: int,
    userId: int,
    payload: SetMemberRoleRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """设置或撤销成员子管理员身份（仅团队管理员）。"""
    return TeamMembershipService(db).setMemberRole(teamId, userId, currentUser, payload)


@router.put(
    "/{teamId}/members/{userId}/level", response_model=MessageResponse, summary="Update member level"
)
def setMemberLevel(
    teamId: int,
    userId: int,
    payload: SetMemberLevelRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """调整成员级别（管理员/子管理员，子管理员受级别上限约束）。"""
    return TeamMembershipService(db).setMemberLevel(teamId, userId, currentUser, payload)


@router.get("/{teamId}/levels", response_model=list[TeamLevelResponse], summary="List team levels")
def listTeamLevels(
    teamId: int, currentUser: User = Depends(getCurrentUser), db: Session = Depends(getDb)
) -> list[dict]:
    """返回团队级别列表（含每个级别的成员数），团队成员可见。"""
    return TeamManagementService(db).listLevels(teamId, currentUser)


@router.post(
    "/{teamId}/levels",
    response_model=TeamLevelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create team level",
)
def createTeamLevel(
    teamId: int,
    payload: SaveLevelRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """新建团队级别（仅团队管理员，级别数值团队内唯一）。"""
    return TeamManagementService(db).createLevel(teamId, currentUser, payload)


@router.put(
    "/{teamId}/levels/{levelId}", response_model=TeamLevelResponse, summary="Update team level"
)
def updateTeamLevel(
    teamId: int,
    levelId: int,
    payload: SaveLevelRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """修改团队级别名称、数值与发布任务权限（仅团队管理员）。"""
    return TeamManagementService(db).updateLevel(teamId, levelId, currentUser, payload)


@router.delete(
    "/{teamId}/levels/{levelId}", response_model=MessageResponse, summary="Delete team level"
)
def deleteTeamLevel(
    teamId: int,
    levelId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """删除团队级别（仅团队管理员，级别下不能有成员）。"""
    return TeamManagementService(db).deleteLevel(teamId, levelId, currentUser)


@router.post(
    "/{teamId}/invite-code", response_model=TeamDetailResponse, summary="Generate invite code"
)
def generateInviteCode(
    teamId: int,
    payload: GenerateInviteCodeRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """生成团队邀请码，可设置有效期与最大使用次数（管理员/子管理员）。"""
    return TeamService(db).generateInviteCode(teamId, currentUser, payload)


@router.get(
    "/{teamId}/join-requests",
    response_model=list[JoinRequestItemResponse],
    summary="List pending join requests",
)
def listJoinRequests(
    teamId: int, currentUser: User = Depends(getCurrentUser), db: Session = Depends(getDb)
) -> list[dict]:
    """返回待处理入团申请（管理员/子管理员可见）。"""
    return TeamManagementService(db).listJoinRequests(teamId, currentUser)


@router.put(
    "/{teamId}/join-requests/{requestId}",
    response_model=MessageResponse,
    summary="Review join request",
)
def handleJoinRequest(
    teamId: int,
    requestId: int,
    payload: HandleJoinRequestRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """通过或拒绝入团申请（管理员/子管理员）。"""
    return TeamManagementService(db).handleJoinRequest(teamId, requestId, currentUser, payload)
