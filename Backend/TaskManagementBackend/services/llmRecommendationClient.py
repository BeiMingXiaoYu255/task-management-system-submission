"""LLM 推荐链路（v1.1，等价移植 Java LlmRecommendationClient）。

定位：本地链路失效、或新任务在本地规则下没有任何成员达到匹配阈值时，
由大语言模型对候选人做语义排序兜底。按 OpenAI 兼容协议调用 Chat Completions：
    POST {llmBaseUrl}{llmChatPath}，Header Authorization: Bearer <key>；
    system prompt 要求模型只输出 JSON：{"rankedUserIds":[...],"reason":"..."}。

契约（aiModuleContract.md 第 4 节）：
    1. 未配置 / 网络错误 / 返回内容非法时抛 LlmRouteException，由调度层按模式回退；
    2. 允许解析带 markdown 代码块包裹的 JSON，忽略模型幻觉出的不存在用户 ID；
    3. 使用标准库 urllib.request，不新增依赖；日志脱敏，绝不输出 API Key。

v1.1.1 起：所有配置来自 aiConfigService.loadEffectiveAIConfig 解析出的 AIConfig
（数据库 system_settings 优先、环境变量兜底），不再直接读取 settings。
"""

import json
import logging
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from TaskManagementBackend.services.localRecommendationEngine import (
    LLM_ROUTE_NAME,
    CandidateItem,
    CandidateProfile,
    RecommendationResult,
    normalizeSkillNames,
)

if TYPE_CHECKING:  # 仅用于类型标注，运行时不导入以避免模块循环依赖
    from TaskManagementBackend.services.aiConfigService import AIConfig

logger = logging.getLogger("taskManagement")

# system prompt 与 Java 版保持一致：只输出 JSON 对象（提示词同样使用英文）
SYSTEM_PROMPT = (
    "You are the assignment assistant of the Task Management System. Based on the required skills "
    "of the task and the skill tags and current workload of candidate members, choose the most "
    "suitable members and rank them by suitability. You may recommend candidates whose skill tags "
    "do not fully match but are semantically close. Output exactly one JSON object and nothing else, "
    'format: {"rankedUserIds":[candidate IDs in descending suitability order],"reason":"reason within 50 words"}'
)
# 未配置时的原因文案（接口/调试统一复用）
UNCONFIGURED_REASON = "LLM API is not configured (llmBaseUrl, llmApiKey and llmModel are required)"
# 日志中 LLM 返回内容的最大展示长度
MAX_LOG_CONTENT_LENGTH = 120
# LLM 连通性测试：最小请求参数与响应预览长度
CONNECTIVITY_MAX_TOKENS = 16
RESPONSE_PREVIEW_LENGTH = 120


class LlmRouteException(Exception):
    """LLM 推荐链路不可用或调用失败：由调度层捕获并回退到备用链路。"""


def isLlmConfigured(config: "AIConfig") -> bool:
    """判断 LLM 三项关键配置（baseUrl/apiKey/model）是否齐全。"""
    return config.llmConfigured


def abbreviate(content: str | None) -> str:
    """截断过长内容用于日志，避免日志膨胀。"""
    text = content or ""
    return text if len(text) <= MAX_LOG_CONTENT_LENGTH else text[:MAX_LOG_CONTENT_LENGTH] + "..."


class LlmRecommendationClient:
    """LLM 推荐客户端：组装提示词、调用接口并把返回 JSON 解析成候选人排序。"""

    def __init__(self, config: "AIConfig") -> None:
        """注入有效 AI 配置（由 aiConfigService 从数据库/环境合并后传入）。"""
        self.config = config
        self.baseUrl = str(config.llmBaseUrl or "").strip().rstrip("/")
        self.apiKey = str(config.llmApiKey or "").strip()
        self.model = str(config.llmModel or "").strip()
        self.timeoutSeconds = max(int(config.llmTimeoutSeconds or 20), 1)
        self.maxCandidates = max(int(config.llmMaxCandidates or 20), 1)

    @property
    def configured(self) -> bool:
        """三项关键配置齐全才算可用。"""
        return self.config.llmConfigured

    @property
    def chatPath(self) -> str:
        """对话接口路径（有效配置已在读取时规范化为以 / 开头）。"""
        return self.config.llmChatPath

    def routeName(self) -> str:
        """链路名：local / llm，与响应 route 字段一致。"""
        return LLM_ROUTE_NAME

    def recommend(
        self, candidateProfiles: list[CandidateProfile], requiredSkillNames: list[str] | None
    ) -> RecommendationResult:
        """对候选成员做语义排序；未配置或调用失败抛 LlmRouteException 由调度层回退。"""
        if not self.configured:
            raise LlmRouteException(UNCONFIGURED_REASON)
        if not candidateProfiles:
            return RecommendationResult.empty(LLM_ROUTE_NAME, "No candidates available to send to the LLM")
        promptProfiles = candidateProfiles[: self.maxCandidates]
        requiredSkills = normalizeSkillNames(requiredSkillNames)
        userPrompt = self.buildUserPrompt(promptProfiles, requiredSkills)
        content = self.postForChatCompletion(SYSTEM_PROMPT, userPrompt)
        return self.parseRanked(content, promptProfiles, requiredSkills)

    def buildUserPrompt(
        self, candidateProfiles: list[CandidateProfile], requiredSkillNames: list[str]
    ) -> str:
        """组装 user prompt：任务所需技能 + 候选人清单（ID | 用户名 | 技能标签 | 当前活跃待办数）。"""
        requiredDescription = ", ".join(requiredSkillNames) if requiredSkillNames else "(no specific requirements)"
        promptLines = [f"Required skill tags: {requiredDescription}", "Candidates (ID | username | skill tags | active to-dos):"]
        for candidateProfile in candidateProfiles:
            skillDescription = ",".join(candidateProfile.skillNames) or "none"
            promptLines.append(
                f"{candidateProfile.userId} | {candidateProfile.username} | {skillDescription} | {candidateProfile.activeTasks}"
            )
        promptLines.append("Output JSON only.")
        return "\n".join(promptLines)

    def parseRanked(
        self,
        content: str,
        candidateProfiles: list[CandidateProfile],
        requiredSkillNames: list[str],
    ) -> RecommendationResult:
        """解析 rankedUserIds：忽略无效 ID，按排名生成 100/90/80... 的展示分。"""
        rankedContent = self.readJsonObject(content)
        rankedUserIds = rankedContent.get("rankedUserIds")
        if not isinstance(rankedUserIds, list) or not rankedUserIds:
            return RecommendationResult.empty(LLM_ROUTE_NAME, "LLM did not return a valid candidate ranking")
        reasonText = str(rankedContent.get("reason") or "").strip()
        profilesById = {profile.userId: profile for profile in candidateProfiles}
        candidates: list[CandidateItem] = []
        rank = 0
        for rawUserId in rankedUserIds:
            userId = self.toUserId(rawUserId)
            candidateProfile = profilesById.get(userId) if userId is not None else None
            if candidateProfile is None:
                continue  # 忽略 LLM 幻觉出的不存在用户 ID
            rank += 1
            candidates.append(self.buildLlmCandidate(candidateProfile, requiredSkillNames, rank))
            if rank >= self.maxCandidates:
                break
        if not candidates:
            return RecommendationResult.empty(LLM_ROUTE_NAME, "All candidate IDs returned by the LLM are invalid")
        return RecommendationResult(route=LLM_ROUTE_NAME, reason=reasonText or "LLM semantic ranking", candidates=candidates)

    def buildLlmCandidate(
        self, candidateProfile: CandidateProfile, requiredSkillNames: list[str], rank: int
    ) -> CandidateItem:
        """构造 LLM 链路候选人：分数为排名分（第一名 100，依次递减 10，最低 0）。"""
        matchedSkillNames = [name for name in requiredSkillNames if name in candidateProfile.skillNames]
        matchRatio = 1.0 if not requiredSkillNames else len(matchedSkillNames) / len(requiredSkillNames)
        reasons = [f"LLM semantic ranking #{rank}"]
        if matchedSkillNames:
            reasons.append("Matched skills: " + ", ".join(matchedSkillNames))
        if candidateProfile.activeTasks == 0:
            reasons.append("No active to-dos; low workload")
        else:
            reasons.append(f"{candidateProfile.activeTasks} active to-dos")
        return CandidateItem(
            userId=candidateProfile.userId,
            username=candidateProfile.username,
            nickname=candidateProfile.nickname,
            levelName=candidateProfile.levelName,
            levelOrder=candidateProfile.levelOrder,
            score=max(100 - (rank - 1) * 10, 0),
            matchRatio=matchRatio,
            matchedSkills=matchedSkillNames,
            activeTasks=candidateProfile.activeTasks,
            reasons=reasons,
            route=LLM_ROUTE_NAME,
        )

    def readJsonObject(self, content: str | None) -> dict:
        """提取模型返回内容中的 JSON 对象：兼容 markdown 代码块包裹的内容。"""
        text = (content or "").strip()
        if not text:
            raise LlmRouteException("LLM returned empty content")
        try:
            parsedContent = json.loads(text)
        except json.JSONDecodeError:
            parsedContent = self.extractJsonBlock(text)
        if not isinstance(parsedContent, dict):
            raise LlmRouteException("LLM content is not a valid JSON object: " + abbreviate(text))
        return parsedContent

    def extractJsonBlock(self, text: str) -> object:
        """截取首个 { 到末个 } 之间的内容再解析；仍失败则抛 LlmRouteException。"""
        startIndex = text.find("{")
        endIndex = text.rfind("}")
        if startIndex >= 0 and endIndex > startIndex:
            try:
                return json.loads(text[startIndex : endIndex + 1])
            except json.JSONDecodeError:
                pass
        raise LlmRouteException("LLM content is not valid JSON: " + abbreviate(text))

    @staticmethod
    def toUserId(rawUserId: object) -> int | None:
        """把模型返回的候选人 ID 转换为整数；非法值返回 None（随后被忽略）。"""
        if isinstance(rawUserId, bool):
            return None
        if isinstance(rawUserId, int):
            return rawUserId
        if isinstance(rawUserId, float) and rawUserId.is_integer():
            return int(rawUserId)
        if isinstance(rawUserId, str):
            strippedValue = rawUserId.strip()
            if strippedValue.lstrip("-").isdigit():
                return int(strippedValue)
        return None

    def postForChatCompletion(self, systemPrompt: str, userPrompt: str) -> str:
        """调用 OpenAI 兼容 Chat Completions 接口并返回 message.content；失败抛 LlmRouteException。"""
        requestBody = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [{"role": "system", "content": systemPrompt}, {"role": "user", "content": userPrompt}],
        }
        requestUrl = f"{self.baseUrl}{self.chatPath}"
        httpRequest = urllib.request.Request(
            requestUrl,
            data=json.dumps(requestBody, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.apiKey}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(httpRequest, timeout=self.timeoutSeconds) as response:
                responseText = response.read().decode("utf-8")
        except Exception as error:  # 网络/超时/协议异常统一降级为 LlmRouteException
            # 注意：异常信息只包含底层错误，不拼接 API Key，避免敏感信息进入日志
            raise LlmRouteException(f"LLM request failed: {error}") from error
        content = self.extractMessageContent(responseText)
        logger.debug("LLM response content: %s", abbreviate(content))
        return content

    def extractMessageContent(self, responseText: str) -> str:
        """从接口响应中提取 choices[0].message.content；结构异常或内容为空时抛错。"""
        try:
            responsePayload = json.loads(responseText)
        except json.JSONDecodeError as error:
            raise LlmRouteException("LLM response is not valid JSON") from error
        try:
            content = responsePayload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LlmRouteException("LLM response does not follow the OpenAI-compatible protocol") from error
        contentText = str(content or "").strip()
        if not contentText:
            raise LlmRouteException("LLM returned an empty message.content")
        return contentText

def buildConnectivityFailure(message: str, startedAt: float) -> dict:
    """构造 LLM 连通性测试失败结果（与成功响应字段保持一致）。"""
    return {"configured": True, "success": False, "message": message, "latencyMs": int((time.perf_counter() - startedAt) * 1000), "responsePreview": None}


def testLlmConnectivity(config: "AIConfig") -> dict:
    """向 LLM 发送最小 Chat Completions 请求并返回中文结论；不输出 API Key。"""
    if not config.llmConfigured:
        return {"configured": False, "success": False, "message": UNCONFIGURED_REASON, "latencyMs": None, "responsePreview": None}
    requestBody = {
        "model": config.llmModel,
        "temperature": 0,
        "max_tokens": CONNECTIVITY_MAX_TOKENS,
        "messages": [{"role": "user", "content": "ping"}],
    }
    httpRequest = urllib.request.Request(
        f"{config.llmBaseUrl}{config.llmChatPath}",
        data=json.dumps(requestBody).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.llmApiKey}"},
        method="POST",
    )
    startedAt = time.perf_counter()
    try:
        with urllib.request.urlopen(httpRequest, timeout=max(config.llmTimeoutSeconds, 1)) as response:
            statusCode = int(getattr(response, "status", 200))
            responseText = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return buildConnectivityFailure(f"LLM endpoint returned HTTP {error.code}; check the base URL, API key and model", startedAt)
    except Exception as error:  # 网络/超时异常统一转中文提示，不拼接 API Key
        return buildConnectivityFailure(f"LLM connectivity test failed: {error}", startedAt)
    latencyMs = int((time.perf_counter() - startedAt) * 1000)
    try:
        contentText = str(json.loads(responseText)["choices"][0]["message"]["content"] or "").strip()
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return {"configured": True, "success": False, "message": "LLM response is not a valid Chat Completions payload", "latencyMs": latencyMs, "responsePreview": None}
    if not contentText:
        return {"configured": True, "success": False, "message": "LLM returned empty content", "latencyMs": latencyMs, "responsePreview": None}
    return {"configured": True, "success": True, "message": f"LLM connection OK (HTTP {statusCode}, model {config.llmModel})", "latencyMs": latencyMs, "responsePreview": contentText[:RESPONSE_PREVIEW_LENGTH]}
