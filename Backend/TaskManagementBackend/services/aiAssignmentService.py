"""AI 自动分配服务（v1.1，移植自 Java AI 模块）。

本文件是后端任务模块依赖的稳定接口层，taskService 只依赖以下两个函数：
    autoAssignTask(...)      -> 发布任务时的自动选人（返回是否成功与候选明细）；
    recommendCandidates(...) -> AI 推荐接口（返回 route/reason/candidates 结构）。

实现分三段：
    1. 候选池：按团队角色/级别权限规则解析候选人（aiModuleContract.md 第 3 节）；
    2. 技能推导：优先使用请求中的 requiredSkillNames，为空时从任务标题/描述匹配技能标签；
    3. 调度：按有效配置（数据库优先、环境兜底）的 dispatchMode 在本地引擎与 LLM
       链路间选择与自动回退，因此管理后台保存配置后下一次请求立即生效。
"""

import logging
from dataclasses import asdict, dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from TaskManagementBackend.core.exceptions import forbidden, validationError
from TaskManagementBackend.core.permissions import requireTeamActiveForTasks, requireTeamMember
from TaskManagementBackend.models import Team, TeamMember, User
from TaskManagementBackend.models.enums import TaskPriority, TeamRole
from TaskManagementBackend.repositories.todoRepository import TodoRepository
from TaskManagementBackend.services.aiConfigService import (
    AIConfig,
    loadEffectiveAIConfig,
    normalizeDispatchMode,
)
from TaskManagementBackend.services.llmRecommendationClient import LlmRecommendationClient
from TaskManagementBackend.services.localRecommendationEngine import (
    LLM_ROUTE_NAME,
    LOCAL_ROUTE_NAME,
    CandidateItem,
    CandidateProfile,
    RecommendationResult,
    deriveRequiredSkillNames,
    normalizeSkillNames,
    recommendLocally,
)

logger = logging.getLogger("taskManagement")

# 四种调度模式（与 aiModuleContract.md 第 5 节一致）
DISPATCH_MODE_LOCAL_ONLY = "LOCAL_ONLY"
DISPATCH_MODE_LLM_ONLY = "LLM_ONLY"
DISPATCH_MODE_LOCAL_FIRST = "LOCAL_FIRST"
DISPATCH_MODE_LLM_FIRST = "LLM_FIRST"
# 推荐接口默认最多返回的候选人数（aiModuleContract.md 第 3 节）
DEFAULT_MAX_CANDIDATES = 10


@dataclass
class AIAssignmentOutcome:
    """自动分配结果：成功时 assigneeUserId 为首选执行人，candidates 为全部合格候选。"""

    assigned: bool
    assigneeUserId: int | None
    route: str | None
    reason: str
    candidates: list[CandidateItem] = field(default_factory=list)


def getDispatchMode(config: AIConfig) -> str:
    """返回有效配置中的调度模式（非法值兜底 LOCAL_FIRST）。"""
    return normalizeDispatchMode(config.dispatchMode)


def validateLevelRange(targetLevelMin: int | None, targetLevelMax: int | None) -> None:
    """校验级别范围：必须同时提供，且最低级别不能高于最高级别。"""
    if (targetLevelMin is None) != (targetLevelMax is None):
        raise validationError("Level range requires both the minimum and maximum levels")
    if targetLevelMin is not None and targetLevelMax is not None and targetLevelMin > targetLevelMax:
        raise validationError("Minimum level cannot be higher than maximum level")


def resolveCandidateMembers(
    db: Session,
    currentUser: User,
    membership: TeamMember,
    targetLevelMin: int | None = None,
    targetLevelMax: int | None = None,
) -> list[TeamMember]:
    """按团队角色与级别权限规则解析可接收任务的候选成员（排除发布者本人）。

    规则（aiModuleContract.md 第 3 节）：
        管理员 → 团队全体其他成员；子管理员 → 排除管理员与本人；
        普通成员 → 级别允许发布任务时，仅级别低于自己的成员。
    同时支持 targetLevelMin/targetLevelMax 收敛候选人，并排除已停用账号。
    """
    validateLevelRange(targetLevelMin, targetLevelMax)
    if membership.role == TeamRole.MEMBER and (
        membership.level is None or not membership.level.canCreateTask
    ):
        raise forbidden("Your current level does not allow publishing tasks")
    operatorLevelOrder = membership.level.levelOrder if membership.level is not None else None
    statement = (
        select(TeamMember)
        .options(joinedload(TeamMember.level), joinedload(TeamMember.user))
        .where(TeamMember.teamId == membership.teamId, TeamMember.userId != currentUser.id)
        .order_by(TeamMember.levelId.desc(), TeamMember.userId.asc())
    )
    candidateMembers: list[TeamMember] = []
    for member in db.execute(statement).scalars().unique():
        if member.level is None or member.user is None or not member.user.isActive:
            continue
        if membership.role == TeamRole.SUB_ADMIN and member.role == TeamRole.ADMIN:
            continue
        if membership.role == TeamRole.MEMBER:
            if operatorLevelOrder is None or member.level.levelOrder >= operatorLevelOrder:
                continue
        if targetLevelMin is not None and not (
            targetLevelMin <= member.level.levelOrder <= targetLevelMax
        ):
            continue
        candidateMembers.append(member)
    return candidateMembers


def buildCandidateProfiles(db: Session, candidateMembers: list[TeamMember]) -> list[CandidateProfile]:
    """把团队成员关系转换为候选人快照：技能标签小写 + 当前活跃待办数（批量查询）。"""
    if not candidateMembers:
        return []
    activeTaskCounts = TodoRepository(db).countActiveAssignmentsByUsers(
        [member.userId for member in candidateMembers]
    )
    candidateProfiles: list[CandidateProfile] = []
    for member in candidateMembers:
        user = member.user
        skillNames = normalizeSkillNames(
            [
                userSkill.skillTag.name
                for userSkill in (user.skills if user is not None else [])
                if userSkill.skillTag is not None
            ]
        )
        candidateProfiles.append(
            CandidateProfile(
                userId=member.userId,
                username=user.username if user is not None else "deleted",
                nickname=user.nickname if user is not None else "Deleted User",
                levelName=member.level.name,
                levelOrder=member.level.levelOrder,
                skillNames=skillNames,
                activeTasks=activeTaskCounts.get(member.userId, 0),
            )
        )
    return candidateProfiles


def resolveRequiredSkillNames(
    candidateProfiles: list[CandidateProfile],
    requestedSkillNames: list[str] | None,
    title: str | None,
    description: str | None,
) -> list[str]:
    """确定任务所需技能：优先请求值；未提供时从标题/描述匹配候选成员技能标签。"""
    normalizedRequestedSkillNames = normalizeSkillNames(requestedSkillNames)
    if normalizedRequestedSkillNames:
        return normalizedRequestedSkillNames
    return deriveRequiredSkillNames(candidateProfiles, title, description)


def callRecommendationRoute(
    routeName: str,
    candidateProfiles: list[CandidateProfile],
    requiredSkillNames: list[str],
    config: AIConfig,
) -> RecommendationResult:
    """调用单条推荐链路：任何异常都转成空结果（带中文原因），保证调度层可统一回退。"""
    try:
        if routeName == LLM_ROUTE_NAME:
            return LlmRecommendationClient(config).recommend(candidateProfiles, requiredSkillNames)
        return recommendLocally(
            candidateProfiles,
            requiredSkillNames,
            config.matchThreshold,
            config.workloadPenalty,
        )
    except Exception as error:  # 链路故障不能阻塞任务发布，交由调度层降级
        logger.warning("Recommendation route %s failed: %s", routeName, error)
        routeDescription = "LLM recommendation route" if routeName == LLM_ROUTE_NAME else "Local recommendation route"
        return RecommendationResult.empty(routeName, f"{routeDescription} failed: {error}")


def dispatchRecommendation(
    candidateProfiles: list[CandidateProfile], requiredSkillNames: list[str], config: AIConfig
) -> RecommendationResult:
    """按调度模式选择链路；主路失败或无候选时自动回退备用链路（aiModuleContract.md 第 5 节）。"""
    dispatchMode = getDispatchMode(config)
    if dispatchMode == DISPATCH_MODE_LOCAL_ONLY:
        return callRecommendationRoute(LOCAL_ROUTE_NAME, candidateProfiles, requiredSkillNames, config)
    if dispatchMode == DISPATCH_MODE_LLM_ONLY:
        return callRecommendationRoute(LLM_ROUTE_NAME, candidateProfiles, requiredSkillNames, config)
    if dispatchMode == DISPATCH_MODE_LOCAL_FIRST:
        primaryResult = callRecommendationRoute(
            LOCAL_ROUTE_NAME, candidateProfiles, requiredSkillNames, config
        )
        if primaryResult.candidates:
            return primaryResult
        return callRecommendationRoute(LLM_ROUTE_NAME, candidateProfiles, requiredSkillNames, config)
    primaryResult = callRecommendationRoute(
        LLM_ROUTE_NAME, candidateProfiles, requiredSkillNames, config
    )
    if primaryResult.candidates:
        return primaryResult
    return callRecommendationRoute(LOCAL_ROUTE_NAME, candidateProfiles, requiredSkillNames, config)


def autoAssignTask(
    db: Session,
    currentUser: User,
    team: Team,
    membership: TeamMember,
    title: str,
    description: str | None,
    priority: TaskPriority,
    requiredSkillNames: list[str] | None,
    targetLevelMin: int | None,
    targetLevelMax: int | None,
) -> AIAssignmentOutcome:
    """发布任务时自动选择执行人：返回全部合格候选（按得分降序，首位即分配对象）。"""
    candidateMembers = resolveCandidateMembers(
        db, currentUser, membership, targetLevelMin, targetLevelMax
    )
    candidateProfiles = buildCandidateProfiles(db, candidateMembers)
    if not candidateProfiles:
        return AIAssignmentOutcome(
            assigned=False,
            assigneeUserId=None,
            route=None,
            reason="No candidates match the permission and level requirements in this team",
        )
    config = loadEffectiveAIConfig(db)
    requiredSkills = resolveRequiredSkillNames(
        candidateProfiles, requiredSkillNames, title, description
    )
    result = dispatchRecommendation(candidateProfiles, requiredSkills, config)
    topCandidate = result.topCandidate
    logger.debug(
        "Team %s task \"%s\" auto-assignment: mode=%s route=%s candidates=%d",
        team.id,
        title,
        getDispatchMode(config),
        result.route,
        len(result.candidates),
    )
    return AIAssignmentOutcome(
        assigned=topCandidate is not None,
        assigneeUserId=topCandidate.userId if topCandidate is not None else None,
        route=result.route,
        reason=result.reason,
        candidates=result.candidates,
    )


def recommendCandidates(
    db: Session,
    currentUser: User,
    teamId: int,
    title: str,
    description: str | None,
    priority: TaskPriority,
    targetLevelMin: int | None,
    targetLevelMax: int | None,
    requiredSkillNames: list[str] | None = None,
    maxCandidates: int | None = None,
) -> dict:
    """AI 推荐接口数据：{ route, reason, candidates }，默认最多返回 10 名候选。"""
    team, membership = requireTeamMember(db, teamId, currentUser)
    requireTeamActiveForTasks(team)
    candidateMembers = resolveCandidateMembers(
        db, currentUser, membership, targetLevelMin, targetLevelMax
    )
    candidateProfiles = buildCandidateProfiles(db, candidateMembers)
    if not candidateProfiles:
        return {
            "route": None,
            "reason": "No candidates match the permission and level requirements in this team",
            "candidates": [],
        }
    config = loadEffectiveAIConfig(db)
    requiredSkills = resolveRequiredSkillNames(
        candidateProfiles, requiredSkillNames, title, description
    )
    result = dispatchRecommendation(candidateProfiles, requiredSkills, config)
    candidateLimit = DEFAULT_MAX_CANDIDATES if maxCandidates is None else max(int(maxCandidates), 1)
    return {
        "route": result.route,
        "reason": result.reason,
        "candidates": [asdict(candidateItem) for candidateItem in result.candidates[:candidateLimit]],
    }
