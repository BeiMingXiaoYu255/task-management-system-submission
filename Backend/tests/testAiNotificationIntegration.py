"""AI 自动分配与通知集成测试（v1.1 AI 自动分配模块）。

覆盖 docs/development/aiModuleContract.md 第 3、6、8 节：
    自动分配发布成功（assignment_source=ai、通知首选执行人与其余候选）、无匹配通知发布者、
    权限拒绝、级别范围收敛候选、推荐接口响应字段/权限/级别与人数过滤、通知接口分页与已读幂等。
"""

from sqlalchemy import select

from tests.testTasks import addTeamMember, createActiveTeam, createTestUser, workspace  # noqa: F401

from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.core.database import SessionLocal
from TaskManagementBackend.models import Notification, SkillTag, UserSkill
from TaskManagementBackend.models.enums import TeamRole


def addSkillToUser(userId: int, skillTagName: str, proficiency: int = 5) -> None:
    """为用户写入技能标签（标签不存在时自动创建）。"""
    databaseSession = SessionLocal()
    try:
        skillTag = databaseSession.execute(
            select(SkillTag).where(SkillTag.name == skillTagName)
        ).scalar_one_or_none()
        if skillTag is None:
            skillTag = SkillTag(name=skillTagName, category="test")
            databaseSession.add(skillTag)
            databaseSession.flush()
        databaseSession.add(UserSkill(userId=userId, skillTagId=skillTag.id, proficiency=proficiency))
        databaseSession.commit()
    finally:
        databaseSession.close()


def listUserNotifications(userId: int) -> list[dict]:
    """查询用户站内通知（新到旧），返回 type/title/content/readFlag 字典列表。"""
    databaseSession = SessionLocal()
    try:
        notifications = list(
            databaseSession.execute(
                select(Notification).where(Notification.userId == userId).order_by(Notification.id.desc())
            ).scalars()
        )
        return [
            {
                "id": item.id,
                "type": item.type,
                "title": item.title,
                "content": item.content or "",
                "readFlag": bool(item.readFlag),
            }
            for item in notifications
        ]
    finally:
        databaseSession.close()


def clearLlmConfig(monkeypatch) -> None:
    """清空 LLM 配置，确保测试环境回退本地引擎（不发起真实网络请求）。"""
    monkeypatch.setattr(settings, "llmBaseUrl", "")
    monkeypatch.setattr(settings, "llmApiKey", "")
    monkeypatch.setattr(settings, "llmModel", "")


def buildAutoAssignPayload(**overrides) -> dict:
    """构造 AI 自动分配发布任务请求体。"""
    payload = {
        "title": "AI auto-assignment task",
        "description": "Verify auto-assignment success and notifications",
        "priority": "high",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "autoAssign": True,
        "requiredSkillNames": ["python"],
    }
    payload.update(overrides)
    return payload


def postRecommend(client, teamId: int, headers: dict, **overrides) -> dict:
    """调用推荐接口并断言成功，返回响应字典。"""
    payload = {"title": "Backend API development", "priority": "high", "requiredSkillNames": ["python"]}
    payload.update(overrides)
    response = client.post(
        f"/api/v1/teams/{teamId}/ai/recommend-assignees", json=payload, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def testAutoAssignPublishSuccessNotifiesCandidates(client, workspace):
    """自动分配成功：首位候选成为执行人（来源 ai），其余候选收到匹配提醒。"""
    teamId = workspace["team"]["id"]
    addSkillToUser(workspace["publisher"]["id"], "python")
    addSkillToUser(workspace["junior"]["id"], "python")
    response = client.post(
        f"/api/v1/teams/{teamId}/tasks",
        json=buildAutoAssignPayload(title="Backend API development"),
        headers=workspace["owner"]["headers"],
    )
    assert response.status_code == 200, response.text
    taskData = response.json()
    assert taskData["autoAssigned"] is True
    assert taskData["requiredSkillNames"] == ["python"]
    assert taskData["status"] == "inProgress"
    assert len(taskData["assignments"]) == 1
    assert taskData["assignments"][0]["userId"] == workspace["publisher"]["id"]
    assert taskData["assignments"][0]["assignmentSource"] == "ai"
    publisherNotifications = listUserNotifications(workspace["publisher"]["id"])
    assert [item["type"] for item in publisherNotifications] == ["taskAutoAssigned"]
    assert "100" in publisherNotifications[0]["content"]
    juniorNotifications = listUserNotifications(workspace["junior"]["id"])
    assert [item["type"] for item in juniorNotifications] == ["taskMatchReminder"]
    assert listUserNotifications(workspace["juniorTwo"]["id"]) == []
    assert listUserNotifications(workspace["owner"]["id"]) == []


def testAutoAssignNoMatchNotifiesPublisher(client, workspace, monkeypatch):
    """自动分配无匹配：任务创建成功但无执行人，通知发布者手动指派。"""
    clearLlmConfig(monkeypatch)
    response = client.post(
        f"/api/v1/teams/{workspace['team']['id']}/tasks",
        json=buildAutoAssignPayload(title="No match task", requiredSkillNames=["non-existent-skill"]),
        headers=workspace["owner"]["headers"],
    )
    assert response.status_code == 200, response.text
    taskData = response.json()
    assert taskData["autoAssigned"] is False
    assert taskData["status"] == "published"
    assert taskData["assignments"] == []
    assert taskData["canAssign"] is True
    publisherNotifications = listUserNotifications(workspace["owner"]["id"])
    assert [item["type"] for item in publisherNotifications] == ["taskAssignFailed"]
    assert "not configured" in publisherNotifications[0]["content"]
    assert listUserNotifications(workspace["junior"]["id"]) == []


def testAutoAssignPermissionRejected(client, workspace):
    """级别不允许发布任务的成员开启 AI 自动分配时返回 403。"""
    response = client.post(
        f"/api/v1/teams/{workspace['team']['id']}/tasks",
        json=buildAutoAssignPayload(),
        headers=workspace["junior"]["headers"],
    )
    assert response.status_code == 403
    assert "does not allow publishing tasks" in response.json()["message"]


def testAutoAssignLevelRangeConvergesCandidates(client, workspace):
    """级别范围收敛候选：仅级别范围内且技能匹配的成员会被自动分配。"""
    addSkillToUser(workspace["publisher"]["id"], "python")
    addSkillToUser(workspace["junior"]["id"], "python")
    response = client.post(
        f"/api/v1/teams/{workspace['team']['id']}/tasks",
        json=buildAutoAssignPayload(targetLevelMin=1, targetLevelMax=1),
        headers=workspace["owner"]["headers"],
    )
    assert response.status_code == 200, response.text
    assignment = response.json()["assignments"][0]
    assert assignment["userId"] == workspace["junior"]["id"]


def testAutoAssignWithoutCandidatePoolNotifiesPublisher(client, monkeypatch):
    """候选池为空：任务无执行人，发布者收到分配失败通知。"""
    clearLlmConfig(monkeypatch)
    soloAdmin = createTestUser("soloAiAdmin", "Solo Admin")
    team = createActiveTeam(soloAdmin["id"], "AI Solo Team")
    response = client.post(
        f"/api/v1/teams/{team['id']}/tasks",
        json=buildAutoAssignPayload(),
        headers=soloAdmin["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["assignments"] == []
    notifications = listUserNotifications(soloAdmin["id"])
    assert [item["type"] for item in notifications] == ["taskAssignFailed"]
    assert "No candidates" in notifications[0]["content"]


def testRecommendEndpointFieldsAndPermissions(client, workspace, monkeypatch):
    """推荐接口：响应对象字段符合契约，级别/人数过滤与权限拒绝正确。"""
    clearLlmConfig(monkeypatch)
    teamId = workspace["team"]["id"]
    addSkillToUser(workspace["publisher"]["id"], "python")
    addSkillToUser(workspace["junior"]["id"], "python")
    recommendData = postRecommend(client, teamId, workspace["owner"]["headers"])
    assert set(recommendData.keys()) == {"route", "reason", "candidates"}
    assert recommendData["route"] == "local"
    assert recommendData["reason"] == "Scored by skill match ratio and workload"
    candidates = recommendData["candidates"]
    assert [item["userId"] for item in candidates] == [
        workspace["publisher"]["id"],
        workspace["junior"]["id"],
    ]
    firstCandidate = candidates[0]
    assert set(firstCandidate.keys()) == {
        "userId", "username", "nickname", "levelName", "levelOrder", "score",
        "matchRatio", "matchedSkills", "activeTasks", "reasons", "route",
    }
    assert firstCandidate["username"] == "publisherTask01"
    assert firstCandidate["levelName"] == "Intermediate Member" and firstCandidate["levelOrder"] == 2
    assert firstCandidate["score"] == 100 and firstCandidate["matchRatio"] == 1.0
    assert firstCandidate["matchedSkills"] == ["python"] and firstCandidate["activeTasks"] == 0
    assert firstCandidate["reasons"] and firstCandidate["route"] == "local"
    limitedData = postRecommend(client, teamId, workspace["owner"]["headers"], maxCandidates=1)
    assert len(limitedData["candidates"]) == 1
    rangedData = postRecommend(
        client, teamId, workspace["owner"]["headers"], targetLevelMin=1, targetLevelMax=1
    )
    assert [item["userId"] for item in rangedData["candidates"]] == [workspace["junior"]["id"]]
    onlyMinResponse = client.post(
        f"/api/v1/teams/{teamId}/ai/recommend-assignees",
        json={"title": "Backend API development", "priority": "high", "targetLevelMin": 1},
        headers=workspace["owner"]["headers"],
    )
    assert onlyMinResponse.status_code == 400
    invertedResponse = client.post(
        f"/api/v1/teams/{teamId}/ai/recommend-assignees",
        json={"title": "Backend API development", "priority": "high", "targetLevelMin": 2, "targetLevelMax": 1},
        headers=workspace["owner"]["headers"],
    )
    assert invertedResponse.status_code == 400
    outsiderResponse = client.post(
        f"/api/v1/teams/{teamId}/ai/recommend-assignees",
        json={"title": "Backend API development", "priority": "high"},
        headers=workspace["outsider"]["headers"],
    )
    assert outsiderResponse.status_code == 403
    lowerLevelResponse = client.post(
        f"/api/v1/teams/{teamId}/ai/recommend-assignees",
        json={"title": "Backend API development", "priority": "high"},
        headers=workspace["junior"]["headers"],
    )
    assert lowerLevelResponse.status_code == 403


def testRecommendDerivesSkillsAndFiltersCandidatePoolByRole(client, workspace, monkeypatch):
    """推荐：未传技能时从标题/描述推导；候选人按团队角色与级别权限规则过滤。"""
    clearLlmConfig(monkeypatch)
    teamId = workspace["team"]["id"]
    addSkillToUser(workspace["junior"]["id"], "Backend Development")
    derivedData = postRecommend(
        client, teamId, workspace["owner"]["headers"],
        title="Backend development API implementation", description="Backend development and integration", requiredSkillNames=None,
    )
    assert [item["userId"] for item in derivedData["candidates"]] == [workspace["junior"]["id"]]
    assert derivedData["candidates"][0]["matchedSkills"] == ["backend development"]
    subAdmin = createTestUser("subAdminAi01", "Sub-admin")
    addTeamMember(teamId, subAdmin["id"], workspace["team"]["levels"][3], role=TeamRole.SUB_ADMIN)
    subAdminData = postRecommend(client, teamId, subAdmin["headers"], requiredSkillNames=[])
    assert [item["userId"] for item in subAdminData["candidates"]] == [
        workspace["publisher"]["id"],
        workspace["junior"]["id"],
        workspace["juniorTwo"]["id"],
    ]
    memberData = postRecommend(client, teamId, workspace["publisher"]["headers"], requiredSkillNames=[])
    assert [item["userId"] for item in memberData["candidates"]] == [
        workspace["junior"]["id"],
        workspace["juniorTwo"]["id"],
    ]


def testNotificationApiPaginationUnreadAndReadIdempotent(client, workspace):
    """通知接口：分页/未读数/已读幂等，越权标记他人通知返回 404。"""
    addSkillToUser(workspace["junior"]["id"], "python")
    autoTaskResponse = client.post(
        f"/api/v1/teams/{workspace['team']['id']}/tasks",
        json=buildAutoAssignPayload(title="Notification API verification task"),
        headers=workspace["owner"]["headers"],
    )
    assert autoTaskResponse.status_code == 200, autoTaskResponse.text
    assert autoTaskResponse.json()["assignments"][0]["userId"] == workspace["junior"]["id"]
    juniorNotificationsResponse = client.get(
        "/api/v1/notifications", params={"unreadOnly": True}, headers=workspace["junior"]["headers"]
    )
    assert juniorNotificationsResponse.status_code == 200, juniorNotificationsResponse.text
    juniorNotifications = juniorNotificationsResponse.json()
    assert juniorNotifications["total"] == 1
    notificationItem = juniorNotifications["items"][0]
    assert notificationItem["type"] == "taskAutoAssigned" and notificationItem["readFlag"] is False
    unreadCountResponse = client.get("/api/v1/notifications/unread-count", headers=workspace["junior"]["headers"])
    assert unreadCountResponse.json() == {"count": 1}
    markReadUrl = f"/api/v1/notifications/{notificationItem['id']}/read"
    firstReadResponse = client.put(markReadUrl, headers=workspace["junior"]["headers"])
    assert firstReadResponse.status_code == 200 and firstReadResponse.json()["readFlag"] is True
    secondReadResponse = client.put(markReadUrl, headers=workspace["junior"]["headers"])
    assert secondReadResponse.status_code == 200 and secondReadResponse.json()["readFlag"] is True
    assert client.get("/api/v1/notifications/unread-count", headers=workspace["junior"]["headers"]).json() == {"count": 0}
    crossUserResponse = client.put(markReadUrl, headers=workspace["publisher"]["headers"])
    assert crossUserResponse.status_code == 404
    markAllResponse = client.put("/api/v1/notifications/read-all", headers=workspace["junior"]["headers"])
    assert markAllResponse.status_code == 200
