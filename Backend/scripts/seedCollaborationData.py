"""v1.1 演示数据：子团队、团队协作、协作任务、通知与 AI 自动分配示例。

由 seedDemoData.py 在基础演示数据之后调用；幂等执行（按名称/标题判断已存在）。
"""

from datetime import datetime, timedelta

from sqlalchemy import select

from TaskManagementBackend.models import (
    Notification,
    SubTeam,
    SubTeamMember,
    Task,
    TaskAssignment,
    Team,
    TeamCollaboration,
    TeamLevel,
    TeamMember,
    User,
)
from TaskManagementBackend.models.enums import (
    AcceptanceMode,
    AssignmentMode,
    AssignmentSource,
    AssignmentStatus,
    CollaborationPhase,
    CollaborationStatus,
    JoinMethod,
    NotificationType,
    TaskPriority,
    TaskStatus,
    TeamRole,
    TeamStatus,
)


def _getUser(databaseSession, username: str) -> User | None:
    """按用户名查询演示用户。"""
    return databaseSession.execute(
        select(User).where(User.username == username)
    ).scalars().first()


def _getOrCreateTeam(
    databaseSession, name: str, description: str, creator: User, joinMethod: JoinMethod
) -> Team:
    """按名称幂等创建演示团队，并补齐 3 个默认级别。"""
    team = databaseSession.execute(select(Team).where(Team.name == name)).scalars().first()
    if team is not None:
        return team
    team = Team(
        name=name,
        description=description,
        joinMethod=joinMethod,
        status=TeamStatus.ACTIVE,
        createdBy=creator.id,
    )
    databaseSession.add(team)
    databaseSession.flush()
    for levelName, levelOrder, canCreateTask in [("Senior Member", 3, True), ("Intermediate Member", 2, True), ("Junior Member", 1, False)]:
        databaseSession.add(
            TeamLevel(teamId=team.id, name=levelName, levelOrder=levelOrder, canCreateTask=canCreateTask)
        )
    databaseSession.flush()
    return team


def _ensureTeamMember(databaseSession, team: Team, user: User, role: TeamRole, levelOrder: int) -> TeamMember:
    """幂等创建团队成员关系。"""
    membership = databaseSession.execute(
        select(TeamMember).where(TeamMember.teamId == team.id, TeamMember.userId == user.id)
    ).scalars().first()
    if membership is not None:
        return membership
    level = databaseSession.execute(
        select(TeamLevel).where(TeamLevel.teamId == team.id, TeamLevel.levelOrder == levelOrder)
    ).scalar_one()
    membership = TeamMember(teamId=team.id, userId=user.id, role=role, levelId=level.id)
    databaseSession.add(membership)
    databaseSession.flush()
    return membership


def _ensureSubTeam(
    databaseSession, parentTeam: Team, name: str, description: str, leader: User, members: list[User]
) -> SubTeam:
    """幂等创建子团队并维护成员（成员必须属于父团队）。"""
    subTeam = databaseSession.execute(
        select(SubTeam).where(SubTeam.parentTeamId == parentTeam.id, SubTeam.name == name)
    ).scalars().first()
    if subTeam is None:
        subTeam = SubTeam(
            parentTeamId=parentTeam.id,
            name=name,
            description=description,
            leaderUserId=leader.id,
            createdBy=leader.id,
        )
        databaseSession.add(subTeam)
        databaseSession.flush()
    else:
        subTeam.leaderUserId = leader.id
    existingMemberIds = {
        row for row in databaseSession.execute(
            select(SubTeamMember.userId).where(SubTeamMember.subTeamId == subTeam.id)
        ).scalars().all()
    }
    for member in members:
        if member.id not in existingMemberIds:
            databaseSession.add(SubTeamMember(subTeamId=subTeam.id, userId=member.id))
    databaseSession.flush()
    return subTeam


def _ensureCollaboration(
    databaseSession,
    initiatorTeam: Team,
    initiatorSubTeam: SubTeam | None,
    targetTeam: Team,
    targetSubTeam: SubTeam | None,
    initiatorLiaison: User,
    targetLiaison: User | None,
    status: CollaborationStatus,
    message: str,
    createdBy: User,
) -> TeamCollaboration:
    """幂等创建协作关系（按双方单位组合匹配）。"""
    collaboration = databaseSession.execute(
        select(TeamCollaboration).where(
            TeamCollaboration.initiatorTeamId == initiatorTeam.id,
            TeamCollaboration.targetTeamId == targetTeam.id,
            TeamCollaboration.initiatorSubTeamId
            == (initiatorSubTeam.id if initiatorSubTeam is not None else None),
            TeamCollaboration.targetSubTeamId == (targetSubTeam.id if targetSubTeam is not None else None),
        )
    ).scalars().first()
    if collaboration is not None:
        return collaboration
    collaboration = TeamCollaboration(
        initiatorTeamId=initiatorTeam.id,
        initiatorSubTeamId=initiatorSubTeam.id if initiatorSubTeam is not None else None,
        targetTeamId=targetTeam.id,
        targetSubTeamId=targetSubTeam.id if targetSubTeam is not None else None,
        initiatorLiaisonUserId=initiatorLiaison.id,
        targetLiaisonUserId=targetLiaison.id if targetLiaison is not None else None,
        status=status,
        message=message,
        createdBy=createdBy.id,
    )
    databaseSession.add(collaboration)
    databaseSession.flush()
    return collaboration


def _ensureCollaborationTask(
    databaseSession,
    collaboration: TeamCollaboration,
    title: str,
    description: str,
    priority: TaskPriority,
    phase: str,
    createdBy: User,
    dueDays: int,
    assignee: User | None = None,
    assignmentStatus: AssignmentStatus | None = None,
) -> Task:
    """幂等创建协作任务（teamId=接收方团队，sourceTeamId=发起方团队）。"""
    task = databaseSession.execute(select(Task).where(Task.title == title)).scalars().first()
    if task is not None:
        return task
    task = Task(
        teamId=collaboration.targetTeamId,
        title=title,
        description=description,
        priority=priority,
        status=TaskStatus.PUBLISHED,
        assignmentMode=AssignmentMode.SPECIFIC,
        acceptanceMode=AcceptanceMode.MANDATORY,
        dueAt=datetime.now() + timedelta(days=dueDays),
        createdBy=createdBy.id,
        sourceTeamId=collaboration.initiatorTeamId,
        sourceSubTeamId=collaboration.initiatorSubTeamId,
        targetTeamId=collaboration.targetTeamId,
        targetSubTeamId=collaboration.targetSubTeamId,
        collaborationId=collaboration.id,
        collaborationPhase=phase,
        collaborationComment="The receiver liaison accepted the task" if phase != CollaborationPhase.PENDING_CONFIRMATION.value else None,
    )
    databaseSession.add(task)
    databaseSession.flush()
    if assignee is not None and phase != CollaborationPhase.PENDING_CONFIRMATION.value:
        databaseSession.add(
            TaskAssignment(
                taskId=task.id,
                userId=assignee.id,
                status=assignmentStatus or AssignmentStatus.IN_PROGRESS,
                acceptedAt=datetime.now(),
                assignmentSource=AssignmentSource.COLLABORATION.value,
                reviewStage="target"
                if (assignmentStatus == AssignmentStatus.PENDING_REVIEW)
                else None,
            )
        )
        task.status = (
            TaskStatus.PENDING_REVIEW
            if assignmentStatus == AssignmentStatus.PENDING_REVIEW
            else TaskStatus.IN_PROGRESS
        )
        databaseSession.flush()
    return task


def _ensureNotification(
    databaseSession, userId: int, notificationType: NotificationType, title: str, content: str
) -> None:
    """幂等创建演示通知（按标题+接收人判断）。"""
    existing = databaseSession.execute(
        select(Notification).where(Notification.userId == userId, Notification.title == title)
    ).scalars().first()
    if existing is not None:
        return
    databaseSession.add(
        Notification(
            userId=userId,
            type=notificationType.value,
            title=title,
            content=content,
            readFlag=False,
        )
    )


def seedCollaborationDemoData(databaseSession) -> None:
    """写入 v1.1 协作/子团队/通知/AI 演示数据（幂等）。"""
    adminUser = _getUser(databaseSession, "demoAdmin")
    developerUser = _getUser(databaseSession, "developerA")
    designerUser = _getUser(databaseSession, "designerB")
    testerUser = _getUser(databaseSession, "testerC")
    productManager = _getUser(databaseSession, "productManager")
    if None in (adminUser, developerUser, designerUser, testerUser):
        return
    if productManager is None:
        return
    demoTeam = databaseSession.execute(
        select(Team).where(Team.name == "Minimal R&D Team")
    ).scalars().first()
    if demoTeam is None:
        return

    productTeam = _getOrCreateTeam(
        databaseSession, "Product Design Team", "A partner team for product planning, interaction and visual design", productManager, JoinMethod.APPROVAL
    )
    _ensureTeamMember(databaseSession, productTeam, productManager, TeamRole.ADMIN, 3)
    _ensureTeamMember(databaseSession, productTeam, designerUser, TeamRole.MEMBER, 2)

    frontendSubTeam = _ensureSubTeam(
        databaseSession, demoTeam, "Frontend Team", "Builds frontend pages and interactions", developerUser, [developerUser, designerUser]
    )
    testSubTeam = _ensureSubTeam(
        databaseSession, demoTeam, "QA Team", "Owns quality assurance and automated testing", testerUser, [testerUser]
    )
    visualSubTeam = _ensureSubTeam(
        databaseSession, productTeam, "Visual Design Team", "Owns visual design and design guidelines", designerUser, [designerUser]
    )

    mainCollaboration = _ensureCollaboration(
        databaseSession,
        demoTeam,
        None,
        productTeam,
        None,
        adminUser,
        designerUser,
        CollaborationStatus.ACTIVE,
        "Jointly deliver the task board redesign and visual guidelines",
        adminUser,
    )
    subTeamCollaboration = _ensureCollaboration(
        databaseSession,
        demoTeam,
        frontendSubTeam,
        demoTeam,
        testSubTeam,
        developerUser,
        testerUser,
        CollaborationStatus.ACTIVE,
        "QA Team runs regression after frontend-backend integration",
        developerUser,
    )
    pendingCollaboration = _ensureCollaboration(
        databaseSession,
        productTeam,
        visualSubTeam,
        demoTeam,
        None,
        designerUser,
        None,
        CollaborationStatus.PENDING,
        "Would like to join the task board interface review",
        designerUser,
    )

    _ensureCollaborationTask(
        databaseSession,
        mainCollaboration,
        "Design the new task board visual mockup",
        "Create visual mockups and design notes for the new task board in the existing minimal black-and-white style.",
        TaskPriority.HIGH,
        CollaborationPhase.PENDING_CONFIRMATION.value,
        adminUser,
        dueDays=5,
    )
    _ensureCollaborationTask(
        databaseSession,
        mainCollaboration,
        "Create the cross-team collaboration flow diagram",
        "Document the full cross-team task flow from dispatch and acceptance to execution and two-stage review.",
        TaskPriority.MEDIUM,
        CollaborationPhase.EXECUTING.value,
        adminUser,
        dueDays=3,
        assignee=designerUser,
        assignmentStatus=AssignmentStatus.IN_PROGRESS,
    )
    _ensureCollaborationTask(
        databaseSession,
        subTeamCollaboration,
        "Regression test for frontend integration defects",
        "Run regression tests for the task board redesign and produce a defect list.",
        TaskPriority.HIGH,
        CollaborationPhase.TARGET_REVIEW.value,
        developerUser,
        dueDays=1,
        assignee=testerUser,
        assignmentStatus=AssignmentStatus.PENDING_REVIEW,
    )

    # AI 自动分配示例任务（普通团队内）
    autoTask = databaseSession.execute(
        select(Task).where(Task.title == "Implement task board data API")
    ).scalars().first()
    if autoTask is None:
        autoTask = Task(
            teamId=demoTeam.id,
            title="Implement task board data API",
            description="Implement task board statistics and filter APIs, auto-assigned by skills.",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.IN_PROGRESS,
            assignmentMode=AssignmentMode.SPECIFIC,
            acceptanceMode=AcceptanceMode.MANDATORY,
            dueAt=datetime.now() + timedelta(days=4),
            createdBy=adminUser.id,
            autoAssigned=True,
            requiredSkillNames="python,Database Design",
        )
        databaseSession.add(autoTask)
        databaseSession.flush()
        databaseSession.add(
            TaskAssignment(
                taskId=autoTask.id,
                userId=developerUser.id,
                status=AssignmentStatus.IN_PROGRESS,
                acceptedAt=datetime.now(),
                assignmentSource=AssignmentSource.AI.value,
            )
        )

    _ensureNotification(
        databaseSession, adminUser.id, NotificationType.COLLABORATION_CONFIRMED,
        "Collaboration is now active", "Your collaboration request with Product Design Team was approved. The liaison is Designer Lin.",
    )
    _ensureNotification(
        databaseSession, adminUser.id, NotificationType.COLLABORATION_APPLIED,
        "New collaboration request", "Product Design Team - Visual Design Team requested collaboration with Minimal R&D Team. Please confirm.",
    )
    _ensureNotification(
        databaseSession, designerUser.id, NotificationType.COLLABORATION_TASK_RECEIVED,
        "Collaboration task awaiting acceptance", "Minimal R&D Team assigned the collaboration task \"Design the new task board visual mockup\". Please accept it.",
    )
    _ensureNotification(
        databaseSession, testerUser.id, NotificationType.COLLABORATION_TASK_TARGET_REVIEW,
        "Collaboration task awaiting receiver review", "The collaboration task \"Regression test for frontend integration defects\" was submitted. Please review as the receiver.",
    )
    _ensureNotification(
        databaseSession, developerUser.id, NotificationType.TASK_AUTO_ASSIGNED,
        "New task auto-assigned", "The task \"Implement task board data API\" was auto-assigned to you by AI. Please handle it.",
    )
    databaseSession.flush()
