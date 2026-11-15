"""权限校验工具集合。

所有团队与任务相关的权限判断集中在此模块，服务层调用这些函数；
控制器层禁止散落权限 if 判断，避免规则漂移。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from TaskManagementBackend.core.exceptions import (
    AppException,
    conflict,
    forbidden,
    notFound,
    validationError,
)
from TaskManagementBackend.models import Team, TeamLevel, TeamMember, User
from TaskManagementBackend.models.enums import AssignmentMode, GlobalRole, TeamRole, TeamStatus


def getTeamOrRaise(db: Session, teamId: int) -> Team:
    """按主键获取团队，不存在时抛出 404。"""
    team = db.get(Team, teamId)
    if team is None:
        raise notFound("Team not found")
    return team


def getMembershipOrNone(db: Session, teamId: int, userId: int) -> TeamMember | None:
    """查询用户在某团队中的成员关系，不存在返回 None。"""
    statement = select(TeamMember).where(
        TeamMember.teamId == teamId, TeamMember.userId == userId
    )
    return db.execute(statement).scalar_one_or_none()


def requireTeamMember(db: Session, teamId: int, currentUser: User) -> tuple[Team, TeamMember]:
    """要求当前用户是团队成员。

    返回：
        (团队, 成员关系) 元组。
    异常：
        团队不存在 → 404；非成员 → 403；团队被驳回 → 403。
    """
    team = getTeamOrRaise(db, teamId)
    membership = getMembershipOrNone(db, teamId, currentUser.id)
    if membership is None:
        raise forbidden("You are not a member of this team")
    if team.status == TeamStatus.REJECTED:
        raise forbidden("This team is not certified and is unavailable")
    return team, membership


def requireActiveTeam(team: Team) -> None:
    """要求团队已通过认证，才能进行任务等业务操作。"""
    if team.status != TeamStatus.ACTIVE:
        raise forbidden("The team is pending certification. Complete certification to perform this action.")


def isTeamAdmin(membership: TeamMember) -> bool:
    """判断成员是否为团队管理员。"""
    return membership.role == TeamRole.ADMIN


def isTeamManager(membership: TeamMember) -> bool:
    """判断成员是否为管理员或子管理员（统称管理者）。"""
    return membership.role in (TeamRole.ADMIN, TeamRole.SUB_ADMIN)


def requireTeamAdmin(membership: TeamMember) -> None:
    """要求成员是团队管理员。"""
    if not isTeamAdmin(membership):
        raise forbidden("Only team admins can perform this action")


def requireTeamManager(membership: TeamMember) -> None:
    """要求成员是管理员或子管理员。"""
    if not isTeamManager(membership):
        raise forbidden("Only team admins or sub-admins can perform this action")


def requireCanManageLevel(membership: TeamMember) -> None:
    """级别管理（新建/修改/删除级别）仅限团队管理员。"""
    requireTeamAdmin(membership)


def requireCanManageTargetMember(operator: TeamMember, target: TeamMember) -> None:
    """校验操作者是否有权管理目标成员（改级别/踢出）。

    规则：
        1. 管理员可以管理除自己以外的任何成员；
        2. 子管理员只能管理角色为普通成员且级别低于自己的成员；
        3. 普通成员无管理权限。
    """
    if operator.userId == target.userId:
        raise validationError("You cannot perform this action on yourself")
    if operator.role == TeamRole.ADMIN:
        return
    if operator.role != TeamRole.SUB_ADMIN:
        raise forbidden("Only admins or sub-admins can manage members")
    if target.role != TeamRole.MEMBER:
        raise forbidden("Sub-admins cannot manage other admins")
    if target.level is None or operator.level is None:
        raise forbidden("Level information is missing. Cannot perform this action.")
    if target.level.levelOrder >= operator.level.levelOrder:
        raise forbidden("You can only manage members with a lower level")


def resolveTargetMembers(
    db: Session,
    teamId: int,
    targetUserIds: list[int] | None,
    targetLevelMin: int | None,
    targetLevelMax: int | None,
) -> list[TeamMember]:
    """解析任务的目标成员列表（按指定成员或级别范围）。

    返回：
        带有 level/user 预加载的成员关系列表。
    异常：
        目标为空、成员不存在、级别范围非法 → 400。
    """
    baseStatement = (
        select(TeamMember)
        .options(joinedload(TeamMember.level), joinedload(TeamMember.user))
        .where(TeamMember.teamId == teamId)
    )
    if targetUserIds:
        uniqueUserIds = list(dict.fromkeys(targetUserIds))
        members = list(db.execute(baseStatement.where(TeamMember.userId.in_(uniqueUserIds))).scalars())
        if len(members) != len(uniqueUserIds):
            raise validationError("Some task recipients are not members of this team")
        return members
    if targetLevelMin is None or targetLevelMax is None:
        raise validationError("Level range mode requires both minimum and maximum levels")
    if targetLevelMin > targetLevelMax:
        raise validationError("Minimum level cannot be higher than maximum level")
    requestedLevels = db.execute(
        select(TeamLevel).where(TeamLevel.teamId == teamId)
    ).scalars().all()
    validOrders = {level.levelOrder for level in requestedLevels}
    if targetLevelMin not in validOrders or targetLevelMax not in validOrders:
        raise validationError("Level range must use levels defined by the team")
    members = list(
        db.execute(
            baseStatement.join(TeamLevel, TeamMember.levelId == TeamLevel.id).where(
                TeamLevel.levelOrder >= targetLevelMin,
                TeamLevel.levelOrder <= targetLevelMax,
            )
        ).scalars()
    )
    if not members:
        raise validationError("No members found in the specified level range")
    return members


def requireCanCreateTask(
    operator: TeamMember,
    targetMembers: list[TeamMember],
) -> None:
    """校验发布任务的权限。

    规则：
        1. 管理员/子管理员可以给任何成员（子管理员不可给管理员）布置任务；
        2. 普通成员必须所在级别允许发布任务，且每个目标成员级别都低于自己；
        3. 不能给比自己级别高的成员布置任务；普通成员不能跨级。
    """
    if operator.role == TeamRole.ADMIN:
        return
    if operator.role == TeamRole.SUB_ADMIN:
        for target in targetMembers:
            if target.role == TeamRole.ADMIN:
                raise forbidden("Sub-admins cannot assign tasks to team admins")
        return
    if operator.level is None or not operator.level.canCreateTask:
        raise forbidden("Your current level does not allow publishing tasks")
    for target in targetMembers:
        if target.level is None or target.level.levelOrder >= operator.level.levelOrder:
            raise forbidden("You can only assign tasks to members with a lower level")


def requireCanReviewTask(task, currentUser: User, membership: TeamMember) -> None:
    """校验审核权限：默认由任务发布者审核；发布者注销后由团队管理员审核。"""
    if task.createdBy is None:
        requireTeamAdmin(membership)
        return
    if task.createdBy != currentUser.id:
        raise forbidden("Only the task publisher can review this task")


def requireCanEditTask(task, currentUser: User, membership: TeamMember) -> None:
    """校验编辑/取消任务权限：发布者或团队管理员。"""
    if task.createdBy == currentUser.id:
        return
    requireTeamAdmin(membership)


def requireTeamActiveForTasks(team: Team) -> None:
    """要求团队已认证，任务相关操作的前置条件。"""
    if team.status != TeamStatus.ACTIVE:
        raise forbidden("Team certification must be approved before task operations")


def isGlobalAdmin(user: User) -> bool:
    """判断用户是否具备全局管理权限：超级用户或全局管理员。"""
    return user.globalRole in (GlobalRole.SUPER_ADMIN, GlobalRole.GLOBAL_ADMIN)


def canViewPrivateProfile(viewer: User, targetUserId: int) -> bool:
    """判断查看者能否看到目标的隐私字段（邮箱/手机号）：本人或全局管理员。"""
    return viewer.id == targetUserId or isGlobalAdmin(viewer)


def findSharedTeamMemberships(
    db: Session, viewerUserId: int, targetUserId: int
) -> list[tuple[TeamMember, TeamMember]]:
    """查询两个用户共同加入的团队，返回 [(查看者成员关系, 目标成员关系)]。

    实现原理：分别加载双方带级别的成员关系，再按团队主键求交集。
    """
    viewerStatement = (
        select(TeamMember)
        .options(joinedload(TeamMember.level))
        .where(TeamMember.userId == viewerUserId)
    )
    targetStatement = (
        select(TeamMember)
        .options(joinedload(TeamMember.level))
        .where(TeamMember.userId == targetUserId)
    )
    viewerMemberships = {
        membership.teamId: membership
        for membership in db.execute(viewerStatement).scalars().unique()
    }
    sharedMemberships: list[tuple[TeamMember, TeamMember]] = []
    for targetMembership in db.execute(targetStatement).scalars().unique():
        viewerMembership = viewerMemberships.get(targetMembership.teamId)
        if viewerMembership is not None:
            sharedMemberships.append((viewerMembership, targetMembership))
    return sharedMemberships


def requireCanViewUserProfile(db: Session, viewer: User, targetUser: User) -> None:
    """校验查看他人完整资料的权限。

    规则：本人、全局管理员可查看；同团队时，团队管理员/子管理员或级别更高者可查看。
    """
    if canViewPrivateProfile(viewer, targetUser.id):
        return
    sharedMemberships = findSharedTeamMemberships(db, viewer.id, targetUser.id)
    if not sharedMemberships:
        raise forbidden("You are not allowed to view this user's profile")
    for viewerMembership, targetMembership in sharedMemberships:
        if viewerMembership.role in (TeamRole.ADMIN, TeamRole.SUB_ADMIN):
            return
        if (
            viewerMembership.level is not None
            and targetMembership.level is not None
            and viewerMembership.level.levelOrder > targetMembership.level.levelOrder
        ):
            return
    raise forbidden("You are not allowed to view this user's profile")


def requireSharesTeam(db: Session, viewer: User, targetUserId: int) -> None:
    """校验查看公开资料的权限：本人、全局管理员或与目标用户同团队。"""
    if canViewPrivateProfile(viewer, targetUserId):
        return
    if not findSharedTeamMemberships(db, viewer.id, targetUserId):
        raise forbidden("Only team members can view this user's public profile")


def requireJoinableTeam(team: Team) -> None:
    """校验团队当前允许新成员加入：仅已认证团队可加入。"""
    if team.status == TeamStatus.PENDING:
        raise AppException("TEAM_PENDING", "The team is pending certification and cannot be joined yet", 403)
    if team.status == TeamStatus.REJECTED:
        raise forbidden("This team is not certified and cannot be joined")


def requireCanLeaveTeam(membership: TeamMember) -> None:
    """校验退出团队：团队管理员必须先转让管理员后才能退出。"""
    if membership.role == TeamRole.ADMIN:
        raise validationError("Team admins cannot leave the team. Transfer the admin role first.")

