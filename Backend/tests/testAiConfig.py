"""AI 配置持久化与连通性测试（v1.1.1，aiModuleContract.md 第 9 节）。

覆盖：GET 有效配置与权限、PUT 部分更新/掩码/校验/审计、POST 连通性测试（草稿覆盖、
成功/失败中文信息、不泄露 Key）、数据库优先与环境兜底优先级、保存后 /ai/status 立即生效。
"""

import json
import urllib.error
import urllib.request

from sqlalchemy import select

from tests.helpers import buildAuthHeaders
from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.core.database import SessionLocal
from TaskManagementBackend.models import AuditLog, SystemSetting
from TaskManagementBackend.models.enums import GlobalRole

AI_CONFIG_AUDIT_ACTION = "admin.aiConfig.update"
AI_CONFIG_RESPONSE_FIELDS = {
    "llmBaseUrl", "llmChatPath", "llmModel", "llmTimeoutSeconds", "llmMaxCandidates",
    "dispatchMode", "matchThreshold", "workloadPenalty", "hasApiKey", "apiKeyMasked",
    "canEdit", "configSource", "updatedAt", "updatedByName",
}


class FakeHttpResponse:
    """模拟 urllib 响应对象：支持 with 上下文与 read()。"""

    def __init__(self, responseText: str) -> None:
        """保存响应原文。"""
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


def patchUrlopen(monkeypatch, responseText: str = "", error: Exception | None = None) -> list[dict]:
    """替换 urllib.request.urlopen：记录请求，返回固定响应或抛出指定异常。"""
    capturedRequests: list[dict] = []

    def fakeUrlopen(request, timeout=None):
        """记录请求并返回伪造响应/抛出异常。"""
        capturedRequests.append({"url": request.full_url, "timeout": timeout, "headers": dict(request.headers), "body": json.loads(request.data.decode("utf-8"))})
        if error is not None:
            raise error
        return FakeHttpResponse(responseText)

    monkeypatch.setattr(urllib.request, "urlopen", fakeUrlopen)
    return capturedRequests


def buildChatCompletionResponse(content: str) -> str:
    """构造 OpenAI 兼容 Chat Completions 响应 JSON 字符串。"""
    return json.dumps({"choices": [{"message": {"role": "assistant", "content": content}}]})


def listAiSystemSettings() -> dict[str, str]:
    """查询 AI 配置相关 system_settings，返回 {configKey: configValue}。"""
    databaseSession = SessionLocal()
    try:
        rows = databaseSession.execute(select(SystemSetting).where(SystemSetting.configKey.like("ai.%"))).scalars()
        return {row.configKey: (row.configValue or "") for row in rows}
    finally:
        databaseSession.close()


def getLatestAiConfigAudit() -> dict:
    """查询最近一条 AI 配置审计日志并解析 detail。"""
    databaseSession = SessionLocal()
    try:
        statement = select(AuditLog).where(AuditLog.action == AI_CONFIG_AUDIT_ACTION).order_by(AuditLog.id.desc())
        auditLog = databaseSession.execute(statement).scalars().first()
        assert auditLog is not None, "Saving AI configuration should write an audit log"
        return {"detail": json.loads(auditLog.detail or "{}"), "detailText": auditLog.detail or ""}
    finally:
        databaseSession.close()


def buildUserHeaders(account: dict) -> dict:
    """由注册返回的 token 构造请求头。"""
    return buildAuthHeaders(account["token"])


def getConfig(client, headers) -> dict:
    """调用 GET /settings/ai-config 并断言成功。"""
    response = client.get("/api/v1/settings/ai-config", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def saveConfig(client, headers, payload: dict) -> dict:
    """调用 PUT /settings/ai-config 并断言成功。"""
    response = client.put("/api/v1/settings/ai-config", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def buildFullConfigPayload() -> dict:
    """构造一份完整的 AI 配置保存请求。"""
    return {
        "llmBaseUrl": "https://api.deepseek.com/",
        "llmChatPath": "/v1/chat/completions",
        "llmModel": "deepseek-chat",
        "llmApiKey": "sk-secret-5678",
        "llmTimeoutSeconds": 30,
        "llmMaxCandidates": 15,
        "dispatchMode": "LLM_FIRST",
        "matchThreshold": 70,
        "workloadPenalty": 3,
    }


def testGetDefaultConfigForNormalUser(client, registerUser):
    """GET：普通用户读取环境默认值，canEdit=false 且不返回 Key 掩码。"""
    configData = getConfig(client, buildUserHeaders(registerUser()))
    assert set(configData.keys()) == AI_CONFIG_RESPONSE_FIELDS
    assert configData["llmBaseUrl"] == settings.llmBaseUrl
    assert configData["llmChatPath"] == settings.llmChatPath
    assert configData["dispatchMode"] == settings.assignmentDispatchMode
    assert configData["llmTimeoutSeconds"] == settings.llmTimeoutSeconds
    assert configData["llmMaxCandidates"] == settings.llmMaxCandidates
    assert configData["matchThreshold"] == settings.assignmentMatchThreshold
    assert configData["workloadPenalty"] == settings.assignmentWorkloadPenalty
    assert configData["hasApiKey"] is False and configData["apiKeyMasked"] is None
    assert configData["canEdit"] is False and configData["configSource"] == "environment"
    assert configData["updatedAt"] is None and configData["updatedByName"] is None


def testSaveConfigPersistsMasksAndAudits(client, superAdminHeaders, registerUser):
    """PUT：保存全部字段、URL 去尾斜杠、Key 落库但接口只回掩码，并写审计日志。"""
    response = client.put(
        "/api/v1/settings/ai-config", json=buildFullConfigPayload(), headers=superAdminHeaders
    )
    assert response.status_code == 200, response.text
    savedConfig = response.json()
    assert savedConfig["llmBaseUrl"] == "https://api.deepseek.com"
    assert savedConfig["llmModel"] == "deepseek-chat"
    assert savedConfig["dispatchMode"] == "LLM_FIRST"
    assert (savedConfig["matchThreshold"], savedConfig["workloadPenalty"]) == (70, 3)
    assert savedConfig["hasApiKey"] is True and savedConfig["apiKeyMasked"] == "****5678"
    assert savedConfig["canEdit"] is True and savedConfig["configSource"] == "database"
    assert savedConfig["updatedByName"] and savedConfig["updatedAt"] is not None
    assert "sk-secret-5678" not in json.dumps(savedConfig)
    databaseValues = listAiSystemSettings()
    assert databaseValues["ai.llmApiKey"] == "sk-secret-5678"
    assert databaseValues["ai.dispatchMode"] == "LLM_FIRST" and len(databaseValues) == 9
    auditLog = getLatestAiConfigAudit()
    assert "llmApiKey" in auditLog["detail"]["changedFields"]
    assert auditLog["detail"]["hasApiKey"] is True
    assert "sk-secret-5678" not in auditLog["detailText"]
    normalUserConfig = getConfig(client, buildUserHeaders(registerUser()))
    assert normalUserConfig["canEdit"] is False and normalUserConfig["apiKeyMasked"] is None
    assert normalUserConfig["hasApiKey"] is True and normalUserConfig["configSource"] == "database"


def testApiKeyKeepAndClear(client, superAdminHeaders):
    """PUT：apiKey 空字符串保持原值，clearApiKey=true 清空并使 LLM 视为未配置。"""
    saveConfig(client, superAdminHeaders, {"llmApiKey": "sk-first-9999"})
    assert getConfig(client, superAdminHeaders)["apiKeyMasked"] == "****9999"
    keptConfig = saveConfig(client, superAdminHeaders, {"llmApiKey": ""})
    assert keptConfig["hasApiKey"] is True and keptConfig["apiKeyMasked"] == "****9999"
    clearedConfig = saveConfig(client, superAdminHeaders, {"clearApiKey": True})
    assert clearedConfig["hasApiKey"] is False and clearedConfig["apiKeyMasked"] is None
    assert listAiSystemSettings()["ai.llmApiKey"] == ""
    aiStatus = client.get("/api/v1/ai/status", headers=superAdminHeaders).json()
    assert aiStatus["llmConfigured"] is False


def testUpdateValidation(client, superAdminHeaders):
    """PUT 参数校验：URL/路径/枚举/数值范围非法与空请求体均返回 400。"""
    invalidPayloads = [
        {"llmBaseUrl": "ftp://example.com"},
        {"llmBaseUrl": "not-a-url"},
        {"llmChatPath": "v1/chat/completions"},
        {"llmTimeoutSeconds": 0},
        {"llmTimeoutSeconds": 121},
        {"llmMaxCandidates": 101},
        {"matchThreshold": 101},
        {"workloadPenalty": -1},
        {"dispatchMode": "UNKNOWN_MODE"},
        {},
    ]
    for invalidPayload in invalidPayloads:
        response = client.put("/api/v1/settings/ai-config", json=invalidPayload, headers=superAdminHeaders)
        assert response.status_code == 400, f"{invalidPayload} -> {response.status_code} {response.text}"
    boundaryConfig = saveConfig(
        client, superAdminHeaders,
        {"matchThreshold": 0, "workloadPenalty": 100, "llmTimeoutSeconds": 1, "llmMaxCandidates": 100},
    )
    assert boundaryConfig["matchThreshold"] == 0 and boundaryConfig["workloadPenalty"] == 100


def testPermissions(client, registerUser, setUserGlobalRole):
    """权限：普通用户 PUT/测试 403、未登录 401；提升全局管理员后可保存。"""
    normalUserHeaders = buildUserHeaders(registerUser())
    assert client.put("/api/v1/settings/ai-config", json={"matchThreshold": 60}, headers=normalUserHeaders).status_code == 403
    assert client.post("/api/v1/settings/ai-config/test", json={}, headers=normalUserHeaders).status_code == 403
    assert client.get("/api/v1/settings/ai-config").status_code == 401
    adminAccount = registerUser()
    setUserGlobalRole(adminAccount["user"]["user"]["id"], GlobalRole.GLOBAL_ADMIN)
    adminHeaders = buildUserHeaders(adminAccount)
    savedConfig = saveConfig(client, adminHeaders, {"matchThreshold": 60})
    assert savedConfig["canEdit"] is True and savedConfig["matchThreshold"] == 60


def testConnectivityUnconfigured(client, superAdminHeaders):
    """POST test：LLM 未配置时返回中文原因（本地引擎始终可用），草稿缺 Key 也不算已配置。"""
    response = client.post("/api/v1/settings/ai-config/test", json={}, headers=superAdminHeaders)
    assert response.status_code == 200, response.text
    testResult = response.json()
    assert testResult["testedAt"] and testResult["local"]["available"] is True
    assert testResult["llm"]["configured"] is False and testResult["llm"]["success"] is False
    assert "not configured" in testResult["llm"]["message"] and testResult["llm"]["latencyMs"] is None
    draftResult = client.post(
        "/api/v1/settings/ai-config/test",
        json={"llmBaseUrl": "https://llm.example.com", "llmModel": "draft-model"},
        headers=superAdminHeaders,
    ).json()
    assert draftResult["llm"]["configured"] is False


def testConnectivitySuccessAndDraftOverride(client, superAdminHeaders, monkeypatch):
    """POST test：已保存 Key 生效；草稿覆盖请求地址/Key 但不写库。"""
    saveConfig(
        client, superAdminHeaders,
        {"llmBaseUrl": "https://llm.example.com", "llmModel": "test-model", "llmApiKey": "sk-saved-0001"},
    )
    capturedRequests = patchUrlopen(monkeypatch, buildChatCompletionResponse("pong"))
    testResult = client.post("/api/v1/settings/ai-config/test", json={}, headers=superAdminHeaders).json()
    assert testResult["llm"]["configured"] is True and testResult["llm"]["success"] is True
    assert testResult["llm"]["latencyMs"] is not None and testResult["llm"]["responsePreview"] == "pong"
    assert "connection OK" in testResult["llm"]["message"]
    savedRequest = capturedRequests[0]
    assert savedRequest["url"] == "https://llm.example.com/v1/chat/completions"
    assert savedRequest["headers"].get("Authorization") == "Bearer sk-saved-0001"
    assert savedRequest["body"]["model"] == "test-model" and savedRequest["body"]["max_tokens"] > 0
    assert savedRequest["body"]["messages"][0]["content"] == "ping"
    client.post(
        "/api/v1/settings/ai-config/test",
        json={
            "llmBaseUrl": "https://draft.example.com",
            "llmChatPath": "/chat/completions",
            "llmModel": "draft-model",
            "llmApiKey": "sk-draft-2222",
        },
        headers=superAdminHeaders,
    )
    draftRequest = capturedRequests[-1]
    assert draftRequest["url"] == "https://draft.example.com/chat/completions"
    assert draftRequest["headers"].get("Authorization") == "Bearer sk-draft-2222"
    assert listAiSystemSettings()["ai.llmApiKey"] == "sk-saved-0001"
    client.post("/api/v1/settings/ai-config/test", json={"dispatchMode": "LOCAL_ONLY"}, headers=superAdminHeaders)
    assert listAiSystemSettings().get("ai.dispatchMode") != "LOCAL_ONLY"


def testConnectivityFailureNoKeyLeak(client, superAdminHeaders, monkeypatch):
    """POST test：HTTP 错误/网络失败/非 JSON/空内容均返回中文失败信息且不泄露 Key。"""
    saveConfig(
        client, superAdminHeaders,
        {"llmBaseUrl": "https://llm.example.com", "llmModel": "test-model", "llmApiKey": "sk-error-3333"},
    )
    patchUrlopen(monkeypatch, error=urllib.error.HTTPError("https://llm.example.com", 500, "error", None, None))
    httpErrorResult = client.post("/api/v1/settings/ai-config/test", json={}, headers=superAdminHeaders).json()
    assert httpErrorResult["llm"]["success"] is False and "HTTP 500" in httpErrorResult["llm"]["message"]
    assert "sk-error-3333" not in json.dumps(httpErrorResult)
    patchUrlopen(monkeypatch, error=urllib.error.URLError("connection refused"))
    networkResult = client.post("/api/v1/settings/ai-config/test", json={}, headers=superAdminHeaders).json()
    assert networkResult["llm"]["success"] is False and "connectivity test failed" in networkResult["llm"]["message"]
    patchUrlopen(monkeypatch, "not-json")
    invalidResult = client.post("/api/v1/settings/ai-config/test", json={}, headers=superAdminHeaders).json()
    assert invalidResult["llm"]["success"] is False and "not a valid Chat Completions" in invalidResult["llm"]["message"]
    patchUrlopen(monkeypatch, buildChatCompletionResponse(""))
    emptyResult = client.post("/api/v1/settings/ai-config/test", json={}, headers=superAdminHeaders).json()
    assert emptyResult["llm"]["success"] is False and "empty" in emptyResult["llm"]["message"]


def testDatabasePriorityAndImmediateEffect(client, superAdminHeaders, monkeypatch):
    """有效配置：数据库值优先于环境变量；保存后 /ai/status 立即生效且无需重启。"""
    monkeypatch.setattr(settings, "assignmentDispatchMode", "LLM_ONLY")
    aiStatus = client.get("/api/v1/ai/status", headers=superAdminHeaders).json()
    assert aiStatus["dispatchMode"] == "LLM_ONLY"
    saveConfig(client, superAdminHeaders, {"dispatchMode": "LOCAL_ONLY", "matchThreshold": 80, "workloadPenalty": 2})
    aiStatus = client.get("/api/v1/ai/status", headers=superAdminHeaders).json()
    assert (aiStatus["dispatchMode"], aiStatus["matchThreshold"], aiStatus["workloadPenalty"]) == ("LOCAL_ONLY", 80, 2)
    assert getConfig(client, superAdminHeaders)["configSource"] == "database"
    monkeypatch.setattr(settings, "assignmentDispatchMode", "LLM_FIRST")
    assert client.get("/api/v1/ai/status", headers=superAdminHeaders).json()["dispatchMode"] == "LOCAL_ONLY"
    monkeypatch.setattr(settings, "llmModel", "env-model")
    assert getConfig(client, superAdminHeaders)["llmModel"] == "env-model"
    saveConfig(client, superAdminHeaders, {"llmModel": ""})
    assert getConfig(client, superAdminHeaders)["llmModel"] == ""
