"""LLM 推荐链路客户端测试（v1.1 AI 自动分配模块）。

覆盖 docs/development/aiModuleContract.md 第 4、8 节：
    请求体与 Authorization 头构造、OpenAI 兼容响应解析、markdown 代码块 JSON 提取、
    无效 ID 忽略、非法返回/网络失败抛 LlmRouteException、未配置中文原因、API Key 脱敏。
v1.1.1 起配置以 aiConfigService.AIConfig 对象注入，不再依赖全局 Settings。
"""

import json
import logging
import urllib.error
import urllib.request

import pytest

from TaskManagementBackend.services.aiConfigService import AIConfig
from TaskManagementBackend.services.llmRecommendationClient import (
    LlmRecommendationClient,
    LlmRouteException,
    isLlmConfigured,
)
from TaskManagementBackend.services.localRecommendationEngine import CandidateProfile


class FakeHttpResponse:
    """模拟 urllib 响应对象：支持 with 上下文与 read()。"""

    def __init__(self, responseText: str) -> None:
        """保存响应原文，read() 时返回 UTF-8 字节。"""
        self.responseText = responseText

    def read(self) -> bytes:
        """返回响应体字节。"""
        return self.responseText.encode("utf-8")

    def __enter__(self) -> "FakeHttpResponse":
        """进入 with 上下文。"""
        return self

    def __exit__(self, exceptionType, exceptionValue, traceback) -> bool:
        """退出 with 上下文，不吞异常。"""
        return False


def buildConfig(**overrides) -> AIConfig:
    """构造测试用 AI 有效配置（默认 LLM 未配置）。"""
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
    """构造 LLM 三项配置齐全的 AI 配置。"""
    configuredValues: dict = {
        "llmBaseUrl": "https://llm.example.com",
        "llmApiKey": "test-key",
        "llmModel": "test-model",
        "llmTimeoutSeconds": 7,
    }
    configuredValues.update(overrides)
    return buildConfig(**configuredValues)


def buildProfiles() -> list[CandidateProfile]:
    """构造两名候选人：alice 命中 java/python，bob 只命中 java。"""
    return [
        CandidateProfile(2, "alice", "Backend-Alice", "Intermediate Member", 2, ["java", "python"], 1),
        CandidateProfile(3, "bob", "Frontend-Bob", "Junior Member", 1, ["java"], 0),
    ]


def buildChatCompletionResponse(content: str) -> str:
    """构造 OpenAI 兼容 Chat Completions 响应 JSON 字符串。"""
    return json.dumps({"choices": [{"message": {"role": "assistant", "content": content}}]})


def patchUrlopen(monkeypatch, responseText: str) -> list[dict]:
    """替换 urllib.request.urlopen：记录请求并返回固定响应。"""
    capturedRequests: list[dict] = []

    def fakeUrlopen(request, timeout=None):
        """记录请求 URL/请求体/请求头/超时并返回伪造响应。"""
        capturedRequests.append(
            {
                "url": request.full_url,
                "body": json.loads(request.data.decode("utf-8")),
                "headers": dict(request.headers),
                "timeout": timeout,
            }
        )
        return FakeHttpResponse(responseText)

    monkeypatch.setattr(urllib.request, "urlopen", fakeUrlopen)
    return capturedRequests


def patchUrlopenFailure(monkeypatch, error: Exception) -> list[str]:
    """替换 urlopen 使其抛出网络异常，返回调用记录列表。"""
    callRecords: list[str] = []

    def fakeUrlopen(request, timeout=None):
        """记录请求 URL 后抛出网络异常。"""
        callRecords.append(request.full_url)
        raise error

    monkeypatch.setattr(urllib.request, "urlopen", fakeUrlopen)
    return callRecords


def patchLlmContent(monkeypatch, content: str) -> None:
    """跳过 HTTP 层，直接给 postForChatCompletion 返回模型文本。"""

    def fakePostForChatCompletion(self, systemPrompt: str, userPrompt: str) -> str:
        """返回预设模型输出。"""
        return content

    monkeypatch.setattr(LlmRecommendationClient, "postForChatCompletion", fakePostForChatCompletion)


def testLlmConfiguredDetection():
    """未配置三项关键配置时视为不可用，配置齐全后可用。"""
    assert isLlmConfigured(buildConfig()) is False
    assert isLlmConfigured(buildConfiguredConfig()) is True
    assert isLlmConfigured(buildConfiguredConfig(llmApiKey="")) is False


def testRequestPayloadAndResponseParsing(monkeypatch):
    """请求：OpenAI 兼容请求体（model/temperature/messages）与 Bearer 认证头正确。"""
    capturedRequests = patchUrlopen(
        monkeypatch, buildChatCompletionResponse('{"rankedUserIds":[2,3],"reason":"alice matches the skills better"}')
    )
    result = LlmRecommendationClient(buildConfiguredConfig()).recommend(buildProfiles(), ["java", "python"])
    assert capturedRequests
    capturedRequest = capturedRequests[0]
    assert capturedRequest["url"] == "https://llm.example.com/v1/chat/completions"
    assert capturedRequest["headers"].get("Authorization") == "Bearer test-key"
    assert capturedRequest["body"]["model"] == "test-model"
    assert capturedRequest["body"]["temperature"] == 0.2
    assert [message["role"] for message in capturedRequest["body"]["messages"]] == ["system", "user"]
    assert "Required skill tags: java, python" in capturedRequest["body"]["messages"][1]["content"]
    assert "2 | alice | java,python | 1" in capturedRequest["body"]["messages"][1]["content"]
    assert capturedRequest["timeout"] == 7
    assert result.route == "llm"
    assert [item.userId for item in result.candidates] == [2, 3]
    assert [item.score for item in result.candidates] == [100, 90]
    assert result.candidates[0].matchRatio == 1.0
    assert result.reason == "alice matches the skills better"


def testParsesMarkdownFencedJson(monkeypatch):
    """模型返回 markdown 代码块包裹的内容时，仍能提取出 JSON 并解析。"""
    fence = chr(96) * 3
    fencedContent = fence + "json\n" + '{"rankedUserIds":[2],"reason":"alice matches all skills"}' + "\n" + fence
    patchLlmContent(monkeypatch, fencedContent)
    result = LlmRecommendationClient(buildConfiguredConfig()).recommend(buildProfiles(), ["java", "python"])
    assert result.topCandidate is not None
    assert result.topCandidate.userId == 2
    assert result.topCandidate.matchRatio == 1.0


def testIgnoresUnknownUserIds(monkeypatch):
    """模型幻觉出的不存在用户 ID 被忽略，有效候选人按排名给展示分。"""
    patchLlmContent(monkeypatch, '{"rankedUserIds":[3,99,2],"reason":"bob has a lower workload"}')
    result = LlmRecommendationClient(buildConfiguredConfig()).recommend(buildProfiles(), ["java", "python"])
    assert [item.userId for item in result.candidates] == [3, 2]
    assert [item.score for item in result.candidates] == [100, 90]
    assert result.candidates[0].matchedSkills == ["java"]
    assert result.candidates[0].matchRatio == 0.5
    assert result.candidates[0].activeTasks == 0
    assert result.candidates[0].route == "llm"


def testNonJsonContentRaisesException(monkeypatch):
    """模型返回非 JSON 文本时抛 LlmRouteException，供调度层回退。"""
    patchLlmContent(monkeypatch, "Sorry, I cannot complete this request.")
    with pytest.raises(LlmRouteException) as exceptionInfo:
        LlmRecommendationClient(buildConfiguredConfig()).recommend(buildProfiles(), ["java"])
    assert "not valid JSON" in str(exceptionInfo.value)


def testHttpFailureRaisesExceptionWithoutApiKey(monkeypatch):
    """网络失败抛 LlmRouteException，且异常信息不泄漏 API Key。"""
    patchUrlopenFailure(monkeypatch, urllib.error.URLError("connect timeout"))
    with pytest.raises(LlmRouteException) as exceptionInfo:
        LlmRecommendationClient(buildConfiguredConfig()).recommend(buildProfiles(), ["java"])
    assert "LLM request failed" in str(exceptionInfo.value)
    assert "test-key" not in str(exceptionInfo.value)


def testAllInvalidUserIdsReturnsEmptyResult(monkeypatch):
    """排序里全是无效 ID 时返回空结果（中文原因），不抛异常。"""
    patchLlmContent(monkeypatch, '{"rankedUserIds":[88,99],"reason":""}')
    result = LlmRecommendationClient(buildConfiguredConfig()).recommend(buildProfiles(), ["java"])
    assert result.route == "llm"
    assert result.candidates == []
    assert "invalid" in result.reason


def testUnconfiguredRaisesWithoutHttpCall(monkeypatch):
    """LLM 未配置时抛中文原因异常，且不发起任何 HTTP 请求。"""
    urlopenCalls = patchUrlopen(monkeypatch, buildChatCompletionResponse("{}"))
    with pytest.raises(LlmRouteException) as exceptionInfo:
        LlmRecommendationClient(buildConfig()).recommend(buildProfiles(), ["java"])
    assert "not configured" in str(exceptionInfo.value)
    assert urlopenCalls == []


def testNoCandidateProfilesReturnsEmpty(monkeypatch):
    """没有可提交给 LLM 的候选人时直接返回空结果，不发起 HTTP 请求。"""
    urlopenCalls = patchUrlopen(monkeypatch, buildChatCompletionResponse("{}"))
    result = LlmRecommendationClient(buildConfiguredConfig()).recommend([], ["java"])
    assert result.candidates == []
    assert "No candidates available" in result.reason
    assert urlopenCalls == []


def testMalformedResponseRaisesException(monkeypatch):
    """接口响应缺少 choices 或 content 为空时抛 LlmRouteException。"""
    patchUrlopen(monkeypatch, json.dumps({"error": "invalid_request"}))
    with pytest.raises(LlmRouteException) as structureInfo:
        LlmRecommendationClient(buildConfiguredConfig()).recommend(buildProfiles(), ["java"])
    assert "OpenAI-compatible protocol" in str(structureInfo.value)
    patchUrlopen(monkeypatch, buildChatCompletionResponse(""))
    with pytest.raises(LlmRouteException) as emptyInfo:
        LlmRecommendationClient(buildConfiguredConfig()).recommend(buildProfiles(), ["java"])
    assert "empty message.content" in str(emptyInfo.value)


def testMaxCandidatesLimit(monkeypatch):
    """最大候选人数配置生效：送入提示词与采纳的候选人都受上限限制。"""
    patchLlmContent(monkeypatch, '{"rankedUserIds":[3,2],"reason":"only accept one candidate"}')
    result = LlmRecommendationClient(buildConfiguredConfig(llmMaxCandidates=1)).recommend(
        buildProfiles(), ["java"]
    )
    # 上限为 1 时只把首位候选人（用户 2）送入提示词，排名中的用户 3 被忽略
    assert [item.userId for item in result.candidates] == [2]


def testLoggingDoesNotExposeApiKey(monkeypatch, caplog):
    """日志脱敏：调用成功的调试日志不包含 API Key。"""
    patchLlmContent(monkeypatch, '{"rankedUserIds":[2],"reason":"alice matched"}')
    with caplog.at_level(logging.DEBUG, logger="taskManagement"):
        LlmRecommendationClient(buildConfiguredConfig()).recommend(buildProfiles(), ["java"])
    assert "test-key" not in caplog.text
