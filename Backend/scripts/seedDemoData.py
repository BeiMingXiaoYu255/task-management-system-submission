"""演示数据种子脚本。

用途：
    为本地开发/演示环境创建可直接体验的团队、成员、技能与任务数据。
    幂等执行：已存在的用户/团队/任务不会重复创建。
运行：
    cd Backend && .\.venv\Scripts\python.exe -m scripts.seedDemoData
    （或项目根目录 python scripts/seedDemoData.py）
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# 允许以脚本方式直接运行：把 Backend 加入模块搜索路径
BACKEND_ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT_DIRECTORY))

from sqlalchemy import select  # noqa: E402

from TaskManagementBackend.core.database import SessionLocal, initDatabase  # noqa: E402
from TaskManagementBackend.core.security import hashPassword  # noqa: E402
from TaskManagementBackend.models import (  # noqa: E402
    SkillTag,
    Task,
    TaskAssignment,
    TaskReview,
    Team,
    TeamLevel,
    TeamMember,
    User,
    UserSkill,
)
from TaskManagementBackend.models.enums import (  # noqa: E402
    AcceptanceMode,
    AssignmentMode,
    AssignmentStatus,
    GlobalRole,
    JoinMethod,
    ReviewResult,
    TaskPriority,
    TaskStatus,
    TeamRole,
    TeamStatus,
)
from TaskManagementBackend.services.initializationService import initializeSystemData  # noqa: E402
from scripts.seedCollaborationData import seedCollaborationDemoData  # noqa: E402

# 演示账号统一密码
DEMO_PASSWORD = "Demo@123456"
# 演示团队名称
DEMO_TEAM_NAME = "Minimal R&D Team"


def getOrCreateUser(
    databaseSession,
    username: str,
    nickname: str,
    bio: str,
    email: str,
) -> User:
    """按用户名幂等创建演示用户。"""
    existingUser = databaseSession.execute(
        select(User).where(User.username == username)
    ).scalars().first()
    if existingUser is not None:
        return existingUser
    user = User(
        username=username,
        passwordHash=hashPassword(DEMO_PASSWORD),
        nickname=nickname,
        email=email,
        bio=bio,
        globalRole=GlobalRole.USER,
        isActive=True,
    )
    databaseSession.add(user)
    databaseSession.flush()
    return user


def getOrCreateSkillTag(databaseSession, tagName: str, category: str) -> SkillTag:
    """按名称幂等创建技能标签。"""
    existingTag = databaseSession.execute(
        select(SkillTag).where(SkillTag.name == tagName)
    ).scalars().first()
    if existingTag is not None:
        return existingTag
    skillTag = SkillTag(name=tagName, category=category)
    databaseSession.add(skillTag)
    databaseSession.flush()
    return skillTag


def bindUserSkills(databaseSession, user: User, skillDefinitions: list[tuple[str, str, int]]) -> None:
    """为演示用户绑定技能标签（已存在的关联跳过）。"""
    existingTagNames = {
        userSkill.skillTag.name
        for userSkill in databaseSession.execute(
            select(UserSkill).where(UserSkill.userId == user.id)
        ).scalars().all()
    }
    for tagName, category, proficiency in skillDefinitions:
        if tagName in existingTagNames:
            continue
        skillTag = getOrCreateSkillTag(databaseSession, tagName, category)
        databaseSession.add(
            UserSkill(userId=user.id, skillTagId=skillTag.id, proficiency=proficiency)
        )


def getOrCreateDemoTeam(databaseSession, adminUser: User) -> Team:
    """幂等创建演示团队并保证默认级别、成员关系完整。"""
    existingTeam = databaseSession.execute(
        select(Team).where(Team.name == DEMO_TEAM_NAME)
    ).scalars().first()
    if existingTeam is not None:
        return existingTeam
    team = Team(
        name=DEMO_TEAM_NAME,
        description="A demo team for task workflow, to-do list and dashboard showcase",
        joinMethod=JoinMethod.APPROVAL,
        status=TeamStatus.ACTIVE,
        createdBy=adminUser.id,
    )
    databaseSession.add(team)
    databaseSession.flush()
    defaultLevels = [
        ("Senior Member", 3, True),
        ("Intermediate Member", 2, True),
        ("Junior Member", 1, False),
    ]
    for levelName, levelOrder, canCreateTask in defaultLevels:
        databaseSession.add(
            TeamLevel(teamId=team.id, name=levelName, levelOrder=levelOrder, canCreateTask=canCreateTask)
        )
    databaseSession.flush()
    return team


def ensureTeamMember(
    databaseSession,
    team: Team,
    user: User,
    role: TeamRole,
    levelOrder: int,
) -> TeamMember:
    """幂等创建团队成员关系。"""
    existingMembership = databaseSession.execute(
        select(TeamMember).where(
            TeamMember.teamId == team.id, TeamMember.userId == user.id
        )
    ).scalars().first()
    if existingMembership is not None:
        return existingMembership
    level = databaseSession.execute(
        select(TeamLevel).where(
            TeamLevel.teamId == team.id, TeamLevel.levelOrder == levelOrder
        )
    ).scalar_one()
    membership = TeamMember(
        teamId=team.id,
        userId=user.id,
        role=role,
        levelId=level.id,
        joinedAt=datetime.now() - timedelta(days=20),
    )
    databaseSession.add(membership)
    databaseSession.flush()
    return membership


def createDemoTask(
    databaseSession,
    team: Team,
    creator: User,
    title: str,
    description: str,
    priority: TaskPriority,
    assignmentMode: AssignmentMode,
    acceptanceMode: AcceptanceMode,
    assignments: list[tuple[User, AssignmentStatus, int]],
    dueDays: int,
    createdDaysAgo: int,
    targetLevelMin: int | None = None,
    targetLevelMax: int | None = None,
) -> Task | None:
    """幂等创建演示任务及其分配记录。

    参数说明：
        assignments：[(执行用户, 待办状态, 提交/归档距今天数)]；
        createdDaysAgo：任务创建时间距今天数，用于仪表盘趋势统计。
    """
    existingTask = databaseSession.execute(
        select(Task).where(Task.teamId == team.id, Task.title == title)
    ).scalars().first()
    if existingTask is not None:
        return existingTask
    createdAt = datetime.now() - timedelta(days=createdDaysAgo)
    task = Task(
        teamId=team.id,
        title=title,
        description=description,
        priority=priority,
        status=TaskStatus.PUBLISHED,
        assignmentMode=assignmentMode,
        acceptanceMode=acceptanceMode,
        targetLevelMin=targetLevelMin,
        targetLevelMax=targetLevelMax,
        dueAt=datetime.now() + timedelta(days=dueDays),
        createdBy=creator.id,
        createdAt=createdAt,
        updatedAt=createdAt,
    )
    databaseSession.add(task)
    databaseSession.flush()
    statusValues: list[AssignmentStatus] = []
    for assignee, assignmentStatus, reviewedDaysAgo in assignments:
        acceptedAt = createdAt + timedelta(hours=2)
        submittedAt = None
        reviewedAt = None
        reviewComment = None
        if assignmentStatus in (AssignmentStatus.PENDING_REVIEW, AssignmentStatus.ARCHIVED):
            submittedAt = datetime.now() - timedelta(days=reviewedDaysAgo, hours=-2)
        if assignmentStatus == AssignmentStatus.ARCHIVED:
            reviewedAt = datetime.now() - timedelta(days=reviewedDaysAgo)
            reviewComment = "Quality meets requirements. Review approved."
        assignment = TaskAssignment(
            taskId=task.id,
            userId=assignee.id,
            status=assignmentStatus,
            acceptedAt=None if assignmentStatus == AssignmentStatus.PENDING_ACCEPTANCE else acceptedAt,
            submittedAt=submittedAt,
            reviewedAt=reviewedAt,
            reviewedBy=creator.id if reviewedAt is not None else None,
            reviewComment=reviewComment,
        )
        databaseSession.add(assignment)
        databaseSession.flush()
        statusValues.append(assignmentStatus)
        if assignmentStatus == AssignmentStatus.ARCHIVED:
            databaseSession.add(
                TaskReview(
                    taskId=task.id,
                    assignmentId=assignment.id,
                    reviewerId=creator.id,
                    result=ReviewResult.APPROVED,
                    comment=reviewComment,
                    createdAt=reviewedAt,
                )
            )
    if all(statusValue == AssignmentStatus.ARCHIVED for statusValue in statusValues):
        task.status = TaskStatus.ARCHIVED
        task.archivedAt = datetime.now() - timedelta(days=2)
    elif any(statusValue == AssignmentStatus.PENDING_REVIEW for statusValue in statusValues):
        task.status = TaskStatus.PENDING_REVIEW
    elif any(statusValue == AssignmentStatus.IN_PROGRESS for statusValue in statusValues):
        task.status = TaskStatus.IN_PROGRESS
    else:
        task.status = TaskStatus.PUBLISHED
    databaseSession.flush()
    return task


def seedDemoData() -> None:
    """写入全部演示数据（幂等）。"""
    initDatabase()
    databaseSession = SessionLocal()
    try:
        initializeSystemData(databaseSession)
        adminUser = getOrCreateUser(
            databaseSession,
            "demoAdmin",
            "Demo Admin",
            "Coordinates team collaboration and task assignments, focused on engineering efficiency.",
            "demoAdmin@example.com",
        )
        developerUser = getOrCreateUser(
            databaseSession,
            "developerA",
            "Developer Zhou",
            "Backend developer focused on API design and database optimization.",
            "developerA@example.com",
        )
        designerUser = getOrCreateUser(
            databaseSession,
            "designerB",
            "Designer Lin",
            "Designs interfaces and interactions with a minimal style.",
            "designerB@example.com",
        )
        testerUser = getOrCreateUser(
            databaseSession,
            "testerC",
            "Tester Chen",
            "Responsible for automated testing and quality assurance.",
            "testerC@example.com",
        )
        bindUserSkills(databaseSession, adminUser, [("Project Management", "Management", 4), ("Requirements Analysis", "Product", 4)])
        bindUserSkills(databaseSession, developerUser, [("Backend Development", "Development", 5), ("Database Design", "Development", 4), ("FastAPI", "Development", 4)])
        bindUserSkills(databaseSession, designerUser, [("Interaction Design", "Design", 5), ("Visual Design", "Design", 4), ("Frontend Development", "Development", 3)])
        bindUserSkills(databaseSession, testerUser, [("Testing & Quality", "Testing", 5), ("Test Automation", "Testing", 4)])

        team = getOrCreateDemoTeam(databaseSession, adminUser)
        ensureTeamMember(databaseSession, team, adminUser, TeamRole.ADMIN, 3)
        ensureTeamMember(databaseSession, team, developerUser, TeamRole.SUB_ADMIN, 2)
        ensureTeamMember(databaseSession, team, designerUser, TeamRole.MEMBER, 1)
        ensureTeamMember(databaseSession, team, testerUser, TeamRole.MEMBER, 2)

        # v1.1：产品团队、子团队、协作关系、协作任务、通知与 AI 自动分配示例
        productManager = getOrCreateUser(
            databaseSession,
            "productManager",
            "Product Manager Su",
            "Plans products and requirements, and drives cross-team collaboration.",
            "productManager@example.com",
        )
        bindUserSkills(databaseSession, productManager, [("Product Design", "Product", 5), ("Requirements Analysis", "Product", 5), ("Project Management", "Management", 4)])
        seedCollaborationDemoData(databaseSession)

        createDemoTask(
            databaseSession, team, adminUser,
            "Improve login page interactions",
            "Improve login form validation and error messages, and add keyboard interactions.",
            TaskPriority.HIGH, AssignmentMode.LEVEL_RANGE, AcceptanceMode.MANDATORY,
            [(developerUser, AssignmentStatus.IN_PROGRESS, 0), (designerUser, AssignmentStatus.IN_PROGRESS, 0)],
            dueDays=3, createdDaysAgo=2, targetLevelMin=1, targetLevelMax=2,
        )
        createDemoTask(
            databaseSession, team, adminUser,
            "Write automated API tests for the task module",
            "Cover the full publish, accept, submit and review flow, and produce a pytest report.",
            TaskPriority.MEDIUM, AssignmentMode.SPECIFIC, AcceptanceMode.MANDATORY,
            [(testerUser, AssignmentStatus.IN_PROGRESS, 0)],
            dueDays=5, createdDaysAgo=3,
        )
        createDemoTask(
            databaseSession, team, adminUser,
            "Design a team weekly report template",
            "Deliver a one-page team weekly report template in a minimal black-and-white style.",
            TaskPriority.LOW, AssignmentMode.LEVEL_RANGE, AcceptanceMode.OPTIONAL,
            [(designerUser, AssignmentStatus.PENDING_ACCEPTANCE, 0)],
            dueDays=7, createdDaysAgo=1, targetLevelMin=1, targetLevelMax=2,
        )
        createDemoTask(
            databaseSession, team, developerUser,
            "Fix task list pagination bug",
            "Filters are lost after changing pages in the task list. Fix it and add tests.",
            TaskPriority.URGENT, AssignmentMode.SPECIFIC, AcceptanceMode.MANDATORY,
            [(developerUser, AssignmentStatus.PENDING_REVIEW, 1)],
            dueDays=-1, createdDaysAgo=4,
        )
        createDemoTask(
            databaseSession, team, adminUser,
            "Write project installation guide",
            "Write installation instructions for Windows, Linux and macOS.",
            TaskPriority.MEDIUM, AssignmentMode.SPECIFIC, AcceptanceMode.MANDATORY,
            [(testerUser, AssignmentStatus.ARCHIVED, 2)],
            dueDays=-2, createdDaysAgo=6,
        )
        createDemoTask(
            databaseSession, team, adminUser,
            "Research database backup strategy",
            "Research scheduled MySQL backup and restore options, and summarize the comparison.",
            TaskPriority.MEDIUM, AssignmentMode.LEVEL_RANGE, AcceptanceMode.OPTIONAL,
            [(developerUser, AssignmentStatus.PENDING_ACCEPTANCE, 0)],
            dueDays=10, createdDaysAgo=0, targetLevelMin=1, targetLevelMax=2,
        )
        # 给演示管理员本人安排任务，保证仪表盘有待办/待审核数据可展示
        createDemoTask(
            databaseSession, team, adminUser,
            "Plan next sprint",
            "Summarize this week's progress and outline next sprint plan and risks.",
            TaskPriority.HIGH, AssignmentMode.SPECIFIC, AcceptanceMode.MANDATORY,
            [(adminUser, AssignmentStatus.IN_PROGRESS, 0)],
            dueDays=2, createdDaysAgo=1,
        )
        createDemoTask(
            databaseSession, team, adminUser,
            "Review task board interaction design",
            "Review the task board interaction draft and provide feedback.",
            TaskPriority.MEDIUM, AssignmentMode.SPECIFIC, AcceptanceMode.MANDATORY,
            [(adminUser, AssignmentStatus.PENDING_REVIEW, 1)],
            dueDays=1, createdDaysAgo=2,
        )
        createDemoTask(
            databaseSession, team, developerUser,
            "Compile this week's code review notes",
            "Summarize code review issues and improvements from this week.",
            TaskPriority.LOW, AssignmentMode.SPECIFIC, AcceptanceMode.MANDATORY,
            [(adminUser, AssignmentStatus.ARCHIVED, 1)],
            dueDays=-1, createdDaysAgo=5,
        )
        databaseSession.commit()
        print("Demo data seeded successfully.")
        print("Demo accounts (password: " + DEMO_PASSWORD + "):")
        print("  demoAdmin  - Team Admin (task publishing, review and member management)")
        print("  developerA - Sub-admin / Intermediate Member")
        print("  designerB  - Junior Member")
        print("  testerC    - Intermediate Member")
    finally:
        databaseSession.close()


if __name__ == "__main__":
    seedDemoData()
