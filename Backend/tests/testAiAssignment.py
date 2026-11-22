"""本地推荐引擎与调度模式单元测试（v1.1 AI 自动分配模块）。

覆盖 docs/development/aiModuleContract.md 第 2、5、8 节：
    本地引擎：命中率/负载惩罚/零交集排除/阈值过滤/稳定排序/空技能列表/技能推导；
    调度模式：四种模式的链路选择、主路失败/无候选回退、LLM 未配置中文原因与异常降级。
v1.1.1 起配置以 aiConfigService.AIConfig 对象注入，不再依赖全局 Settings。
"""

from TaskManagementBackend.services import aiAssignmentService
from TaskManagementBackend.services.aiAssignmentService import (
    dispatchRecommendation,
    getDispatchMode,
)
from TaskManagementBackend.services.aiConfigService import AIConfig
from TaskManagementBackend.services.llmRecommendationClient import (
    LlmRecommendationClient,
    LlmRouteException,
)
from TaskManagementBackend.services.localRecommendationEngine import (
    CandidateProfile,
    deriveRequiredSkillNames,
    normalizeSkillNames,
    recommendLocally,
)


def buildConfig(**overrides) -> AIConfig:
    """构造测试用有效 AI 配置（默认本地链路优先、阈值 50、负载惩罚 5）。"""
    configValues: dict = {
        "llmBaseUrl": "",
        "llmChatPath": "/v1/chat/completions",
        "llmModel": "",
        "llmApiKey": "",
        "llmTimeoutSeconds": 20,
        "llmMaxCandidates": 20,
        "dispatchMode": "LOCAL_FIRST",
        "matchThreshold": 50,
        "workloadPenalty": 5,
    }
    configValues.update(overrides)
    return AIConfig(**configValues)


def buildConfiguredConfig(**overrides) -> AIConfig:
    """构造 LLM 三项关键配置齐全的 AI 配置。"""
    configuredValues: dict = {
        "llmBaseUrl": "https://llm.example.com",
        "llmApiKey": "test-key",
        "llmModel": "test-model",
    }
    configuredValues.update(overrides)
    return buildConfig(**configuredValues)


def buildProfiles() -> list[CandidateProfile]:
    """构造候选人快照：alice 技能全命中，bob 命中一半且负载高，carol 技能不相关。"""
    return [
        CandidateProfile(
            userId=1, username="alice", nickname="Backend-Alice",
            levelName="Intermediate Member", levelOrder=2, skillNames=["java", "python"], activeTasks=0,
        ),
        CandidateProfile(
            userId=2, username="bob", nickname="Frontend-Bob",
            levelName="Junior Member", levelOrder=1, skillNames=["java"], activeTasks=4,
        ),
        CandidateProfile(
            userId=3, username="carol", nickname="QA-Carol",
            levelName="Junior Member", levelOrder=1, skillNames=["css"], activeTasks=0,
        ),
    ]


def patchLlmContent(monkeypatch, content: str) -> list[dict]:
    """替换 LLM 的 HTTP 调用为固定返回内容，并记录调用参数。"""
    llmCalls: list[dict] = []

    def fakePostForChatCompletion(self, systemPrompt: str, userPrompt: str) -> str:
        """记录提示词并返回预设内容（不发起真实网络请求）。"""
        llmCalls.append({"systemPrompt": systemPrompt, "userPrompt": userPrompt})
        return content

    monkeypatch.setattr(LlmRecommendationClient, "postForChatCompletion", fakePostForChatCompletion)
    return llmCalls


def patchLlmFailure(monkeypatch, error: Exception) -> None:
    """让 LLM 的 HTTP 调用抛出指定异常，用于验证调度层降级。"""

    def fakePostForChatCompletion(self, systemPrompt: str, userPrompt: str) -> str:
        """直接抛出预设异常。"""
        raise error

    monkeypatch.setattr(LlmRecommendationClient, "postForChatCompletion", fakePostForChatCompletion)


def patchLocalCalls(monkeypatch) -> list[list[CandidateProfile]]:
    """记录本地引擎调用（用于断言某模式下不会走到本地链路）。"""
    localCalls: list[list[CandidateProfile]] = []

    def fakeRecommendLocally(candidateProfiles, requiredSkillNames, matchThreshold, workloadPenalty):
        """记录入参并抛出断言异常（若被调用则说明调度模式错误）。"""
        localCalls.append(candidateProfiles)
        raise AssertionError("This dispatch mode must not call the local engine")

    monkeypatch.setattr(aiAssignmentService, "recommendLocally", fakeRecommendLocally)
    return localCalls


# ===== 1. 本地推荐引擎 =====
def testLocalScoringFullMatchAndFields():
    """本地打分：技能全命中且无负载时得 100 分，命中信息与理由随结果返回。"""
    result = recommendLocally(buildProfiles()[:1], ["java", "python"], 50, 5)
    topCandidate = result.topCandidate
    assert result.route == "local"
    assert result.reason == "Scored by skill match ratio and workload"
    assert topCandidate is not None
    assert topCandidate.userId == 1
    assert topCandidate.score == 100
    assert topCandidate.matchRatio == 1.0
    assert topCandidate.matchedSkills == ["java", "python"]
    assert topCandidate.activeTasks == 0
    assert topCandidate.route == "local"
    assert any("Matched skills" in reason for reason in topCandidate.reasons)
    assert any("active to-dos" in reason for reason in topCandidate.reasons)


def testLocalWorkloadPenaltyAndOrdering():
    """负载惩罚：每多一个活跃待办扣 5 分（配置值），得分低者排后。"""
    candidates = [
        CandidateProfile(1, "idle", "Idle Member", "Junior Member", 1, ["java"], 0),
        CandidateProfile(2, "busy", "Busy Member", "Junior Member", 1, ["java"], 4),
    ]
    result = recommendLocally(candidates, ["java"], 50, buildConfig().workloadPenalty)
    assert [item.userId for item in result.candidates] == [1, 2]
    assert result.candidates[0].score == 100
    assert result.candidates[1].score == 100 - 4 * buildConfig().workloadPenalty


def testLocalTieBreakByWorkloadThenUserId():
    """同分排序：活跃待办少者优先，再按用户 ID 升序，保证结果稳定可复现。"""
    candidates = [
        CandidateProfile(3, "c", "Member C", "Junior Member", 1, ["java"], 0),
        CandidateProfile(1, "a", "Member A", "Junior Member", 1, ["java"], 0),
        CandidateProfile(2, "b", "Member B", "Junior Member", 1, ["java"], 2),
    ]
    result = recommendLocally(candidates, ["java"], 50, 5)
    assert [item.userId for item in result.candidates] == [1, 3, 2]


def testLocalExcludesZeroSkillOverlap():
    """零交集排除：与所需技能完全对不上的候选人不进入候选列表。"""
    result = recommendLocally(buildProfiles(), ["python"], 50, 5)
    assert [item.userId for item in result.candidates] == [1]
    emptyResult = recommendLocally(buildProfiles()[2:], ["python"], 50, 5)
    assert emptyResult.candidates == []
    assert emptyResult.topCandidate is None
    assert emptyResult.reason == "No members reached the match threshold"


def testLocalFiltersBelowMatchThreshold():
    """阈值过滤：命中 1/2 项（50 分）再扣 1 个负载（5 分）得 45 分低于阈值 50，被排除。"""
    candidates = [CandidateProfile(1, "carol", "Member Carol", "Junior Member", 1, ["java"], 1)]
    result = recommendLocally(candidates, ["java", "python"], 50, 5)
    assert result.candidates == []


def testLocalWithoutRequiredSkillsReturnsAllByLoad():
    """空技能列表：所有候选人都参与排序，按活跃待办升序、再按用户 ID 升序。"""
    result = recommendLocally(buildProfiles(), [], 50, 5)
    assert [item.userId for item in result.candidates] == [1, 3, 2]
    assert all(item.matchRatio == 1.0 for item in result.candidates)
    assert all(item.matchedSkills == [] for item in result.candidates)
    assert result.candidates[0].score == 100


def testNormalizeSkillNames():
    """技能标签规范化：去空白、转小写、去重并保持首次出现顺序。"""
    assert normalizeSkillNames([" JAVA ", "java", "Python", "", None]) == ["java", "python"]
    assert normalizeSkillNames(None) == []


def testDeriveRequiredSkillNamesFromTaskText():
    """未提供所需技能时：从标题/描述中匹配候选成员已有技能标签（大小写不敏感、去重）。"""
    derivedSkills = deriveRequiredSkillNames(buildProfiles(), "Need Java backend development", "Familiar with python data processing")
    assert derivedSkills == ["java", "python"]
    assert deriveRequiredSkillNames(buildProfiles(), "Pure frontend page", None) == []


# ===== 2. 调度模式与回退 =====
def testGetDispatchModeFallsBackWhenConfiguredValueInvalid():
    """调度模式配置非法时回退默认 LOCAL_FIRST。"""
    assert getDispatchMode(buildConfig(dispatchMode="UNKNOWN_MODE")) == "LOCAL_FIRST"


def testLocalOnlyUsesLocalEngineOnly(monkeypatch):
    """LOCAL_ONLY：只走本地引擎，不调用 LLM。"""
    llmCalls = patchLlmContent(monkeypatch, '{"rankedUserIds":[1],"reason":"should not be called"}')
    config = buildConfig(dispatchMode="LOCAL_ONLY")
    result = dispatchRecommendation(buildProfiles(), ["java"], config)
    assert result.route == "local"
    assert [item.userId for item in result.candidates] == [1, 2]
    assert llmCalls == []


def testLlmOnlyUsesLlmClientOnly(monkeypatch):
    """LLM_ONLY：只走 LLM 链路，按排名解析候选人与展示分。"""
    patchLlmContent(monkeypatch, '{"rankedUserIds":[2,1],"reason":"bob has a lower workload"}')
    localCalls = patchLocalCalls(monkeypatch)
    config = buildConfiguredConfig(dispatchMode="LLM_ONLY")
    result = dispatchRecommendation(buildProfiles(), ["java"], config)
    assert result.route == "llm"
    assert [item.userId for item in result.candidates] == [2, 1]
    assert [item.score for item in result.candidates] == [100, 90]
    assert result.reason == "bob has a lower workload"
    assert localCalls == []


def testLocalFirstSkipsLlmWhenLocalHasCandidates(monkeypatch):
    """LOCAL_FIRST：本地有匹配时直接返回，不调用 LLM。"""
    llmCalls = patchLlmContent(monkeypatch, '{"rankedUserIds":[1],"reason":"should not be called"}')
    result = dispatchRecommendation(buildProfiles(), ["java"], buildConfig())
    assert result.route == "local"
    assert llmCalls == []


def testLocalFirstFallsBackToLlmWhenLocalEmpty(monkeypatch):
    """LOCAL_FIRST：本地无候选时回退 LLM，并允许推荐技能零交集候选人。"""
    patchLlmContent(monkeypatch, '{"rankedUserIds":[3],"reason":"semantically close: carol knows css"}')
    config = buildConfiguredConfig()
    assert recommendLocally(buildProfiles(), ["cobol"], 50, 5).candidates == []
    result = dispatchRecommendation(buildProfiles(), ["cobol"], config)
    assert result.route == "llm"
    assert [item.userId for item in result.candidates] == [3]
    assert result.candidates[0].matchedSkills == []
    assert result.candidates[0].matchRatio == 0.0


def testLocalFirstBothRoutesEmptyGivesChineseReason():
    """LOCAL_FIRST：本地无匹配且 LLM 未配置时，返回空候选与中文原因。"""
    result = dispatchRecommendation(buildProfiles(), ["cobol"], buildConfig())
    assert result.route == "llm"
    assert result.candidates == []
    assert "not configured" in result.reason


def testLlmFirstFallsBackToLocalWhenLlmThrows(monkeypatch):
    """LLM_FIRST：LLM 调用异常时自动回退本地引擎并成功产出候选。"""
    patchLlmFailure(monkeypatch, LlmRouteException("LLM request failed: connect timeout"))
    result = dispatchRecommendation(buildProfiles(), ["java"], buildConfiguredConfig(dispatchMode="LLM_FIRST"))
    assert result.route == "local"
    assert [item.userId for item in result.candidates] == [1, 2]


def testLlmFirstFallsBackToLocalWhenLlmReturnsNoCandidate(monkeypatch):
    """LLM_FIRST：LLM 未给出有效候选人时回退本地引擎。"""
    patchLlmContent(monkeypatch, '{"rankedUserIds":[],"reason":""}')
    result = dispatchRecommendation(buildProfiles(), ["java"], buildConfiguredConfig(dispatchMode="LLM_FIRST"))
    assert result.route == "local"
    assert result.candidates


def testLlmOnlyUnconfiguredReturnsEmptyWithReason():
    """LLM_ONLY：LLM 未配置时返回空候选，并给出中文原因供发布者手动指派。"""
    result = dispatchRecommendation(buildProfiles(), ["java"], buildConfig(dispatchMode="LLM_ONLY"))
    assert result.route == "llm"
    assert result.candidates == []
    assert "not configured" in result.reason
