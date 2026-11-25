"""真实 AI API 验证脚本（v1.2.1）。

用途：使用用户提供的真实 OpenAI 兼容 API，完成：
1. 登录超级用户，保存 AI 配置并调用连通性测试接口，确认真实 LLM 连通；
2. 登录演示团队管理员，调用 AI 推荐接口，确认由真实 LLM 链路返回候选；
3. 发布一个开启「AI 自动分配」的任务，确认执行人被自动指派（assignmentSource=ai）；
4. 自动取消测试任务并恢复原始 AI 配置（不污染演示数据）。

用法（PowerShell）：
    $env:REAL_API_BASE_URL='https://api.deepseek.com'
    $env:REAL_API_MODEL='deepseek-chat'
    $env:REAL_API_KEY='sk-...'
    # 可选：$env:REAL_API_CHAT_PATH='/v1/chat/completions'
    # 可选：$env:BASE_API_URL='http://127.0.0.1:8765'
    .\.venv\Scripts\python.exe ..\scripts\verifyRealAiApi.py

或直接传参：
    python scripts/verifyRealAiApi.py --base-url https://... --api-key sk-... --model deepseek-chat

退出码：0=全部通过；1=存在失败。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_API_URL = "http://127.0.0.1:8765"
DEFAULT_SUPER_ADMIN = ("superAdmin", "SuperAdmin@123")
DEFAULT_TEAM_ADMIN = ("demoAdmin", "Demo@123456")


def parseArguments() -> argparse.Namespace:
    """解析命令行参数（优先命令行，其次环境变量）。"""
    parser = argparse.ArgumentParser(description="Verify a real OpenAI-compatible LLM API against the running backend")
    parser.add_argument("--base-api", default=os.environ.get("BASE_API_URL", DEFAULT_BASE_API_URL))
    parser.add_argument("--base-url", default=os.environ.get("REAL_API_BASE_URL", ""))
    parser.add_argument("--api-key", default=os.environ.get("REAL_API_KEY", ""))
    parser.add_argument("--model", default=os.environ.get("REAL_API_MODEL", ""))
    parser.add_argument("--chat-path", default=os.environ.get("REAL_API_CHAT_PATH", "/v1/chat/completions"))
    parser.add_argument("--dispatch-mode", default=os.environ.get("REAL_API_DISPATCH_MODE", "LLM_ONLY"))
    parser.add_argument("--team-name", default=os.environ.get("REAL_API_TEAM_NAME", "Minimal R&D Team"))
    return parser.parse_args()


def raiseForStatus(statusCode: int, body: str) -> None:
    """把非 2xx 响应转换为带响应内容的异常，便于定位。"""
    if statusCode < 200 or statusCode >= 300:
        raise RuntimeError("HTTP " + str(statusCode) + ": " + body[:800])


def requestJson(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeoutSeconds: int = 120,
) -> dict[str, Any]:
    """发送 JSON 请求并解析 JSON 响应。"""
    requestHeaders = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        requestHeaders.update(headers)
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method=method, headers=requestHeaders)
    try:
        with urllib.request.urlopen(request, timeout=timeoutSeconds) as response:
            raw = response.read()
            raiseForStatus(response.status, raw.decode("utf-8", errors="replace"))
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as error:
        errorBody = error.read().decode("utf-8", errors="replace")
        raise RuntimeError("HTTP " + str(error.code) + " for " + method + " " + url + ": " + errorBody[:800]) from error


def login(baseApi: str, username: str, password: str) -> str:
    """登录并返回 access token。"""
    responseData = requestJson(
        "POST",
        baseApi + "/api/v1/auth/login",
        {"username": username, "password": password},
    )
    token = responseData.get("token") or responseData.get("accessToken")
    if not token:
        raise RuntimeError("Login response did not contain a token: " + json.dumps(responseData)[:400])
    return str(token)


def authHeaders(token: str) -> dict[str, str]:
    """构造 Bearer 认证头。"""
    return {"Authorization": "Bearer " + token}


def main() -> int:
    """执行真实 API 验证主流程。"""
    arguments = parseArguments()
    missingFields = [
        fieldName
        for fieldName, fieldValue in (
            ("Base URL", arguments.base_url),
            ("API Key", arguments.api_key),
            ("Model", arguments.model),
        )
        if not str(fieldValue).strip()
    ]
    if missingFields:
        print("[FAIL] Missing required API settings: " + ", ".join(missingFields))
        print("Provide via args or env REAL_API_BASE_URL / REAL_API_KEY / REAL_API_MODEL.")
        return 1

    baseApi = arguments.base_api.rstrip("/")
    passedChecks: list[str] = []
    failedChecks: list[str] = []
    cleanupTaskId: int | None = None
    originalConfig: dict[str, Any] | None = None

    def check(name: str, condition: bool, detail: str = "") -> None:
        """记录单项检查结果。"""
        if condition:
            passedChecks.append(name)
            print("[PASS] " + name + (("  " + detail) if detail else ""))
        else:
            failedChecks.append(name)
            print("[FAIL] " + name + (("  " + detail) if detail else ""))

    print("==================================================")
    print("Real AI API verification")
    print("Base API : " + baseApi)
    print("LLM URL  : " + arguments.base_url)
    print("Model    : " + arguments.model)
    print("Dispatch : " + arguments.dispatch_mode)
    print("==================================================")

    superAdminToken = login(baseApi, *DEFAULT_SUPER_ADMIN)
    teamAdminToken = login(baseApi, *DEFAULT_TEAM_ADMIN)
    superAdminHeaders = authHeaders(superAdminToken)
    teamAdminHeaders = authHeaders(teamAdminToken)

    try:
        # 1. 读取并保存原始配置，写入真实 API 配置
        originalConfig = requestJson("GET", baseApi + "/api/v1/settings/ai-config", headers=superAdminHeaders)
        updatePayload = {
            "llmBaseUrl": arguments.base_url.rstrip("/"),
            "llmChatPath": arguments.chat_path,
            "llmModel": arguments.model,
            "llmApiKey": arguments.api_key,
            "llmTimeoutSeconds": 60,
            "dispatchMode": arguments.dispatch_mode,
        }
        updatedConfig = requestJson(
            "PUT",
            baseApi + "/api/v1/settings/ai-config",
            updatePayload,
            superAdminHeaders,
        )
        check("AI configuration saved", updatedConfig.get("llmModel") == arguments.model and updatedConfig.get("hasApiKey") is True)

        # 2. 连通性测试（真实调用 LLM）
        testResult = requestJson(
            "POST",
            baseApi + "/api/v1/settings/ai-config/test",
            {"llmBaseUrl": arguments.base_url.rstrip("/"), "llmChatPath": arguments.chat_path, "llmModel": arguments.model, "llmApiKey": arguments.api_key, "llmTimeoutSeconds": 60},
            superAdminHeaders,
        )
        llmResult = testResult.get("llm", {})
        check("Local rule engine available", bool(testResult.get("local", {}).get("available")))
        check(
            "Real LLM connectivity test succeeded",
            bool(llmResult.get("configured")) and bool(llmResult.get("success")),
            "latencyMs=" + str(llmResult.get("latencyMs")) + ", message=" + str(llmResult.get("message"))[:200],
        )
        if llmResult.get("responsePreview"):
            print("LLM response preview: " + str(llmResult.get("responsePreview"))[:200])

        # 3. AI 状态确认真实配置生效
        aiStatus = requestJson("GET", baseApi + "/api/v1/ai/status", headers=superAdminHeaders)
        check(
            "AI status reflects LLM configuration",
            bool(aiStatus.get("llmConfigured")) and aiStatus.get("dispatchMode") == arguments.dispatch_mode,
            "dispatchMode=" + str(aiStatus.get("dispatchMode")) + ", llmModel=" + str(aiStatus.get("llmModel")),
        )

        # 4. 找到演示团队
        teamsData = requestJson("GET", baseApi + "/api/v1/teams?page=1&pageSize=50", headers=teamAdminHeaders)
        # /teams 可能返回数组或分页对象，两种结构都兼容
        if isinstance(teamsData, list):
            teams = teamsData
        elif isinstance(teamsData, dict):
            teams = teamsData.get("items", [])
        else:
            teams = []
        targetTeam = next((team for team in teams if team.get("name") == arguments.team_name), None)
        if targetTeam is None and teams:
            targetTeam = teams[0]
        check("Demo team found", targetTeam is not None, str(targetTeam.get("name")) if targetTeam else "")
        if targetTeam is None:
            raise RuntimeError("No team available for AI recommendation test")

        # 5. 真实 LLM 推荐候选
        recommendPayload = {
            "title": "Implement task board statistics API",
            "description": "Implement backend statistics and filtering APIs for the task board.",
            "priority": "medium",
            "requiredSkillNames": ["Backend Development", "FastAPI"],
            "maxCandidates": 5,
        }
        recommendResult = requestJson(
            "POST",
            baseApi + "/api/v1/teams/" + str(targetTeam["id"]) + "/ai/recommend-assignees",
            recommendPayload,
            teamAdminHeaders,
        )
        candidates = recommendResult.get("candidates", [])
        check("AI recommendation returns candidates", len(candidates) > 0, "count=" + str(len(candidates)))
        check(
            "Recommendation used the real LLM route",
            recommendResult.get("route") == "llm",
            "route=" + str(recommendResult.get("route")) + ", reason=" + str(recommendResult.get("reason"))[:200],
        )
        if candidates:
            print("Top candidate: " + str(candidates[0].get("nickname")) + " score=" + str(candidates[0].get("score")) + " reasons=" + str(candidates[0].get("reasons"))[:200])

        # 6. 发布开启 AI 自动分配的任务
        createTaskPayload = {
            "title": "Real API auto-assignment verification task",
            "description": "Created by verifyRealAiApi.py to verify real LLM auto-assignment; will be cancelled afterwards.",
            "priority": "medium",
            "assignmentMode": "specific",
            "acceptanceMode": "mandatory",
            "autoAssign": True,
            "requiredSkillNames": ["Backend Development", "FastAPI"],
        }
        createdTask = requestJson(
            "POST",
            baseApi + "/api/v1/teams/" + str(targetTeam["id"]) + "/tasks",
            createTaskPayload,
            teamAdminHeaders,
        )
        cleanupTaskId = int(createdTask.get("id") or 0) or None
        assignments = createdTask.get("assignments", [])
        check("Auto-assigned task has an assignee", len(assignments) == 1, "assignee=" + str(assignments[0].get("nickname")) if assignments else "none")
        check(
            "Assignee source is AI",
            bool(assignments) and assignments[0].get("assignmentSource") == "ai",
            "autoAssigned=" + str(createdTask.get("autoAssigned")),
        )

        # 7. 任务详情再次确认
        if cleanupTaskId:
            taskDetail = requestJson("GET", baseApi + "/api/v1/tasks/" + str(cleanupTaskId), headers=teamAdminHeaders)
            detailAssignments = taskDetail.get("assignments", [])
            check(
                "Task detail shows AI assignment persisted",
                len(detailAssignments) == 1 and detailAssignments[0].get("assignmentSource") == "ai",
            )
    finally:
        # 清理测试任务 + 恢复原 AI 配置（即使中途失败也执行）
        try:
            if cleanupTaskId:
                requestJson("POST", baseApi + "/api/v1/tasks/" + str(cleanupTaskId) + "/cancel", headers=teamAdminHeaders)
                print("[CLEANUP] Test task " + str(cleanupTaskId) + " cancelled")
        except Exception as cleanupError:  # noqa: BLE001
            print("[WARN] Failed to cancel test task: " + str(cleanupError)[:300])
        try:
            if originalConfig is not None:
                restorePayload = {
                    "llmBaseUrl": originalConfig.get("llmBaseUrl", ""),
                    "llmChatPath": originalConfig.get("llmChatPath", "/v1/chat/completions"),
                    "llmModel": originalConfig.get("llmModel", ""),
                    "clearApiKey": not bool(originalConfig.get("hasApiKey")),
                    "llmTimeoutSeconds": originalConfig.get("llmTimeoutSeconds", 20),
                    "llmMaxCandidates": originalConfig.get("llmMaxCandidates", 20),
                    "dispatchMode": originalConfig.get("dispatchMode", "LOCAL_FIRST"),
                    "matchThreshold": originalConfig.get("matchThreshold", 50),
                    "workloadPenalty": originalConfig.get("workloadPenalty", 5),
                }
                requestJson("PUT", baseApi + "/api/v1/settings/ai-config", restorePayload, superAdminHeaders)
                print("[CLEANUP] Original AI configuration restored")
        except Exception as cleanupError:  # noqa: BLE001
            print("[WARN] Failed to restore AI configuration: " + str(cleanupError)[:300])

    print("")
    print("================ Real API verification summary ================")
    print("Passed: " + str(len(passedChecks)) + " / " + str(len(passedChecks) + len(failedChecks)))
    if failedChecks:
        print("Failed checks: " + "; ".join(failedChecks))
        return 1
    print("All real API checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
