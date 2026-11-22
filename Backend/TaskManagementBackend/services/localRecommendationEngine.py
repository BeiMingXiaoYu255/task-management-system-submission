"""本地规则推荐引擎（v1.1，等价移植 Java LocalRecommendationEngine）。

打分公式：得分 = round(技能命中率 × 100) − 活跃待办数 × 负载惩罚。
    1. 技能命中率 = 命中的所需技能数 / 所需技能总数；无技能要求时视为 1.0；
    2. 与所需技能零交集的候选人直接排除；
    3. 得分低于有效配置 matchThreshold 的候选人视为无匹配；
    4. 同分排序：活跃待办少者优先，再按用户 ID 升序，保证稳定可复现。

本模块保持纯计算（不读取配置、不访问数据库）：候选人快照由 aiAssignmentService
按团队权限规则解析后传入，可通过阈值与负载惩罚让单元测试注入配置。
"""

import math
from dataclasses import dataclass, field

# 链路名称常量：与接口响应 route 字段取值一致
LOCAL_ROUTE_NAME = "local"
LLM_ROUTE_NAME = "llm"


@dataclass
class CandidateProfile:
    """候选人快照：团队权限解析后的成员资料、技能标签（小写）与当前负载。"""

    userId: int
    username: str
    nickname: str
    levelName: str
    levelOrder: int
    skillNames: list[str] = field(default_factory=list)
    activeTasks: int = 0


@dataclass
class CandidateItem:
    """候选人打分明细：与 aiModuleContract.md 6.2 响应字段一一对应。"""

    userId: int
    username: str
    nickname: str
    levelName: str
    levelOrder: int
    score: int
    matchRatio: float
    matchedSkills: list[str] = field(default_factory=list)
    activeTasks: int = 0
    reasons: list[str] = field(default_factory=list)
    route: str = LOCAL_ROUTE_NAME


@dataclass
class RecommendationResult:
    """单条推荐链路的返回结果：candidates 已按得分降序排列。"""

    route: str | None
    reason: str
    candidates: list[CandidateItem] = field(default_factory=list)

    @property
    def topCandidate(self) -> CandidateItem | None:
        """首选候选人（列表首位）；无候选人时返回 None。"""
        return self.candidates[0] if self.candidates else None

    @classmethod
    def empty(cls, route: str | None, reason: str) -> "RecommendationResult":
        """构造空结果：链路失败或无匹配时使用，reason 携带中文原因。"""
        return cls(route=route, reason=reason, candidates=[])


def normalizeSkillNames(skillNames: list[str] | None) -> list[str]:
    """技能标签规范化：去除首尾空白、转小写、去重并保持首次出现顺序。"""
    normalizedSkillNames: list[str] = []
    seenSkillNames: set[str] = set()
    for skillName in skillNames or []:
        if skillName is None:
            continue
        normalizedName = str(skillName).strip().lower()
        if normalizedName and normalizedName not in seenSkillNames:
            seenSkillNames.add(normalizedName)
            normalizedSkillNames.append(normalizedName)
    return normalizedSkillNames


def deriveRequiredSkillNames(
    candidateProfiles: list[CandidateProfile], title: str | None, description: str | None
) -> list[str]:
    """未提供所需技能时，从任务标题/描述中匹配候选成员已有技能标签（大小写不敏感、去重）。"""
    taskText = f"{title or ''} {description or ''}".lower()
    if not taskText.strip():
        return []
    matchedSkillNames: set[str] = set()
    for candidateProfile in candidateProfiles:
        for skillName in candidateProfile.skillNames:
            if skillName and skillName in taskText:
                matchedSkillNames.add(skillName)
    return sorted(matchedSkillNames)


def buildCandidateReasons(
    requiredSkillNames: list[str],
    matchedSkillNames: list[str],
    activeTasks: int,
    workloadPenalty: int,
) -> list[str]:
    """生成中文推荐理由：技能命中情况与当前活跃待办负载。"""
    if requiredSkillNames:
        reasons = [
            "Matched skills: "
            + ", ".join(matchedSkillNames)
            + f" ({len(matchedSkillNames)}/{len(requiredSkillNames)})"
        ]
    else:
        reasons = ["No required skills specified; ranked by current active workload"]
    if activeTasks == 0:
        reasons.append("No active to-dos; low workload")
    else:
        reasons.append(f"{activeTasks} active to-dos; workload penalty {activeTasks * workloadPenalty} points")
    return reasons


def scoreCandidate(
    candidateProfile: CandidateProfile,
    requiredSkillNames: list[str],
    matchThreshold: int,
    workloadPenalty: int,
) -> CandidateItem | None:
    """给单个候选人打分；与所需技能零交集或低于阈值时返回 None（即排除）。"""
    matchedSkillNames = [
        skillName for skillName in requiredSkillNames if skillName in candidateProfile.skillNames
    ]
    if requiredSkillNames and not matchedSkillNames:
        return None
    matchRatio = 1.0 if not requiredSkillNames else len(matchedSkillNames) / len(requiredSkillNames)
    # 使用 floor(x + 0.5) 与 Java Math.round 保持一致（Python round 为银行家舍入）
    score = int(math.floor(matchRatio * 100 + 0.5)) - candidateProfile.activeTasks * workloadPenalty
    if score < matchThreshold:
        return None
    return CandidateItem(
        userId=candidateProfile.userId,
        username=candidateProfile.username,
        nickname=candidateProfile.nickname,
        levelName=candidateProfile.levelName,
        levelOrder=candidateProfile.levelOrder,
        score=score,
        matchRatio=matchRatio,
        matchedSkills=matchedSkillNames,
        activeTasks=candidateProfile.activeTasks,
        reasons=buildCandidateReasons(
            requiredSkillNames, matchedSkillNames, candidateProfile.activeTasks, workloadPenalty
        ),
        route=LOCAL_ROUTE_NAME,
    )


def recommendLocally(
    candidateProfiles: list[CandidateProfile],
    requiredSkillNames: list[str] | None,
    matchThreshold: int,
    workloadPenalty: int,
) -> RecommendationResult:
    """本地链路推荐：逐人打分过滤，再按得分降序 → 负载升序 → 用户 ID 升序排序。"""
    normalizedRequiredSkillNames = normalizeSkillNames(requiredSkillNames)
    scoredCandidates: list[CandidateItem] = []
    for candidateProfile in candidateProfiles:
        candidateItem = scoreCandidate(
            candidateProfile, normalizedRequiredSkillNames, int(matchThreshold), int(workloadPenalty)
        )
        if candidateItem is not None:
            scoredCandidates.append(candidateItem)
    scoredCandidates.sort(key=lambda item: (-item.score, item.activeTasks, item.userId))
    reason = "Scored by skill match ratio and workload" if scoredCandidates else "No members reached the match threshold"
    return RecommendationResult(route=LOCAL_ROUTE_NAME, reason=reason, candidates=scoredCandidates)
