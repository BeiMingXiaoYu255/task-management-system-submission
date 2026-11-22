"""设置与 AI 辅助接口测试：界面设置、修改密码、注销账号、AI 状态与推荐。

注销账号用例覆盖 databaseContract.md 第 3 节第 9 条：
软删除、username 后缀释放、团队关系/待办清理、发布任务 createdBy 置空、
团队管理员需先转让、无其他成员的管理员团队随账号解散。
"""

from sqlalchemy import func, select

from tests.helpers import buildAuthHeaders
from tests.testTasks import (
    createActiveTeam,
    createTask,
    createTestUser,
    workspace,
)
from TaskManagementBackend.core.database import SessionLocal
from TaskManagementBackend.core.security import createAccessToken, verifyPassword
from TaskManagementBackend.models import (
    SkillTag,
    Task,
    Team,
    TeamMember,
    User,
    UserSkill,
)


def addSkillToUser(userId: int, skillTagName: str, category: str, proficiency: int) -> None:
    """为用户写入技能标签与熟练度（标签不存在时自动创建）。"""
    databaseSession = SessionLocal()
    try:
        skillTag = databaseSession.execute(
            select(SkillTag).where(SkillTag.name == skillTagName)
        ).scalar_one_or_none()
        if skillTag is None:
            skillTag = SkillTag(name=skillTagName, category=category)
            databaseSession.add(skillTag)
            databaseSession.flush()
        databaseSession.add(
            UserSkill(userId=userId, skillTagId=skillTag.id, proficiency=proficiency)
        )
        databaseSession.commit()
    finally:
        databaseSession.close()


def countRows(model, *conditions) -> int:
    """统计满足条件的记录数（用于断言数据库副作用）。"""
    databaseSession = SessionLocal()
    try:
        statement = select(func.count()).select_from(model).where(*conditions)
        return int(databaseSession.execute(statement).scalar_one())
    finally:
        databaseSession.close()


def testSettingsReadWrite(client):
    """界面设置：首次读取自动创建默认值，修改后回读一致，非法枚举返回 400。"""
    account = createTestUser("settingsUser01", "设置用户")
    firstResponse = client.get("/api/v1/settings", headers=account["headers"])
    assert firstResponse.status_code == 200, firstResponse.text
    assert firstResponse.json() == {"theme": "light", "fontSize": "medium", "fontFamily": "system"}
    updateResponse = client.put(
        "/api/v1/settings",
        json={"theme": "dark", "fontSize": "large", "fontFamily": "serif"},
        headers=account["headers"],
    )
    assert updateResponse.status_code == 200, updateResponse.text
    assert updateResponse.json() == {"theme": "dark", "fontSize": "large", "fontFamily": "serif"}
    readResponse = client.get("/api/v1/settings", headers=account["headers"])
    assert readResponse.json()["theme"] == "dark"
    invalidResponse = client.put(
        "/api/v1/settings",
        json={"theme": "blue", "fontSize": "medium", "fontFamily": "system"},
        headers=account["headers"],
    )
    assert invalidResponse.status_code == 400


def testChangePasswordInvalidatesOldToken(client):
    """修改密码：旧密码错误/新密码过弱返回 400，成功后旧 token 失效且新哈希生效。"""
    account = createTestUser("settingsUser02", "修改密码用户")
    wrongOldResponse = client.put(
        "/api/v1/settings/password",
        json={"oldPassword": "WrongPass1", "newPassword": "NewPassword123"},
        headers=account["headers"],
    )
    assert wrongOldResponse.status_code == 400
    weakNewResponse = client.put(
        "/api/v1/settings/password",
        json={"oldPassword": "Password123", "newPassword": "abcdefgh"},
        headers=account["headers"],
    )
    assert weakNewResponse.status_code == 400
    successResponse = client.put(
        "/api/v1/settings/password",
        json={"oldPassword": "Password123", "newPassword": "NewPassword123"},
        headers=account["headers"],
    )
    assert successResponse.status_code == 200, successResponse.text
    blockedResponse = client.get("/api/v1/settings", headers=account["headers"])
    assert blockedResponse.status_code == 401
    databaseSession = SessionLocal()
    try:
        user = databaseSession.get(User, account["id"])
        assert verifyPassword("NewPassword123", user.passwordHash) is True
    finally:
        databaseSession.close()
    newToken = createAccessToken(account["id"], "settingsUser02", "user")["token"]
    assert client.get("/api/v1/settings", headers=buildAuthHeaders(newToken)).status_code == 200


def testDeleteAccountWrongPassword(client):
    """注销账号：密码错误返回 400，账号保持启用。"""
    account = createTestUser("settingsUser03", "注销用户")
    response = client.request(
        "DELETE",
        "/api/v1/settings/account",
        json={"password": "WrongPass1"},
        headers=account["headers"],
    )
    assert response.status_code == 400
    databaseSession = SessionLocal()
    try:
        assert databaseSession.get(User, account["id"]).isActive is True
    finally:
        databaseSession.close()


def testDeleteAccountClearsRelationsAndTaskCreator(client, workspace):
    """注销普通成员：软删除、清理成员关系与待办、发布任务 createdBy 置空。"""
    publisher = workspace["publisher"]
    owner = workspace["owner"]
    junior = workspace["junior"]
    teamId = workspace["team"]["id"]
    createdTask = createTask(client, publisher["headers"], teamId, targetUserIds=[junior["id"]])
    assignedTask = createTask(client, owner["headers"], teamId, targetUserIds=[publisher["id"]])
    response = client.request(
        "DELETE",
        "/api/v1/settings/account",
        json={"password": "Password123"},
        headers=publisher["headers"],
    )
    assert response.status_code == 200, response.text
    assert client.get("/api/v1/settings", headers=publisher["headers"]).status_code == 401
    databaseSession = SessionLocal()
    try:
        deletedUser = databaseSession.get(User, publisher["id"])
        assert deletedUser.isActive is False
        assert deletedUser.username.endswith(f"_deleted_{publisher['id']}")
        assert databaseSession.get(Task, createdTask["id"]).createdBy is None
    finally:
        databaseSession.close()
    assert countRows(TeamMember, TeamMember.userId == publisher["id"]) == 0
    taskDetail = client.get(f"/api/v1/tasks/{createdTask['id']}", headers=owner["headers"]).json()
    assert taskDetail["createdBy"] is None
    assert taskDetail["createdByName"] == "Deleted User"
    assert taskDetail["canReview"] is True
    cancelledTask = client.get(f"/api/v1/tasks/{assignedTask['id']}", headers=owner["headers"]).json()
    assert cancelledTask["assignments"] == []
    assert cancelledTask["status"] == "cancelled"


def testDeleteAccountAdminMustTransfer(client, workspace):
    """注销团队管理员：团队仍有其他成员时返回 409，要求先转让。"""
    response = client.request(
        "DELETE",
        "/api/v1/settings/account",
        json={"password": "Password123"},
        headers=workspace["owner"]["headers"],
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"
    assert "Transfer" in response.json()["message"]


def testDeleteAccountSoloAdminDeletesTeam(client):
    """注销无其他成员的团队管理员：团队随账号一起解散。"""
    account = createTestUser("soloAdmin01", "独立管理员")
    team = createActiveTeam(account["id"], "独立团队")
    response = client.request(
        "DELETE",
        "/api/v1/settings/account",
        json={"password": "Password123"},
        headers=account["headers"],
    )
    assert response.status_code == 200, response.text
    databaseSession = SessionLocal()
    try:
        assert databaseSession.get(Team, team["id"]) is None
    finally:
        databaseSession.close()


def testAiStatus(client):
    """AI 状态（v1.1）：provider 为 hybrid，返回调度模式与本地/LLM 可用性字段。"""
    account = createTestUser("aiUser01", "AI User")
    response = client.get("/api/v1/ai/status", headers=account["headers"])
    assert response.status_code == 200
    statusData = response.json()
    assert statusData["provider"] == "hybrid"
    assert statusData["available"] is True
    assert statusData["dispatchMode"] in {"LOCAL_ONLY", "LLM_ONLY", "LOCAL_FIRST", "LLM_FIRST"}
    assert statusData["localAvailable"] is True
    assert isinstance(statusData["llmConfigured"], bool)
    assert isinstance(statusData["llmModel"], str)
    assert statusData["matchThreshold"] >= 0 and statusData["workloadPenalty"] >= 0
    assert statusData["description"]


def testRecommendAssignees(client, workspace):
    """AI 推荐（v1.1）：响应为 {route, reason, candidates}；技能匹配与权限拒绝正确。"""
    teamId = workspace["team"]["id"]
    addSkillToUser(workspace["junior"]["id"], "Backend Development", "Development", 5)
    recommendPayload = {
        "title": "Backend development API implementation",
        "description": "Backend development and API testing",
        "priority": "high",
        "requiredSkillNames": ["Backend Development"],
    }
    response = client.post(
        f"/api/v1/teams/{teamId}/ai/recommend-assignees",
        json=recommendPayload,
        headers=workspace["owner"]["headers"],
    )
    assert response.status_code == 200, response.text
    recommendData = response.json()
    assert set(recommendData.keys()) == {"route", "reason", "candidates"}
    assert recommendData["route"] == "local"
    assert recommendData["reason"]
    recommendations = recommendData["candidates"]
    assert [item["userId"] for item in recommendations] == [workspace["junior"]["id"]]
    assert recommendations[0]["matchedSkills"] == ["backend development"]
    assert recommendations[0]["route"] == "local"
    assert all(0 <= item["score"] <= 100 for item in recommendations)
    levelFilteredResponse = client.post(
        f"/api/v1/teams/{teamId}/ai/recommend-assignees",
        json={**recommendPayload, "targetLevelMin": 2, "targetLevelMax": 2},
        headers=workspace["owner"]["headers"],
    )
    assert levelFilteredResponse.status_code == 200, levelFilteredResponse.text
    # 级别 2 的发布者不具备「后端开发」技能，零交集被排除，因此范围内候选为空
    assert levelFilteredResponse.json()["candidates"] == []
    outsiderResponse = client.post(
        f"/api/v1/teams/{teamId}/ai/recommend-assignees",
        json=recommendPayload,
        headers=workspace["outsider"]["headers"],
    )
    assert outsiderResponse.status_code == 403
    lowerLevelResponse = client.post(
        f"/api/v1/teams/{teamId}/ai/recommend-assignees",
        json=recommendPayload,
        headers=workspace["junior"]["headers"],
    )
    assert lowerLevelResponse.status_code == 403