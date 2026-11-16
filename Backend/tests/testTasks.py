"""任务模块接口测试：发布、列表、详情、修改、取消与我的任务中心。

测试数据通过数据库直接构造（用户、团队、级别、成员关系与 token），
不依赖账号/团队模块接口，保证任务模块可独立验证；每个用例由 conftest 自动清库。
"""

import pytest

from tests.helpers import buildAuthHeaders
from TaskManagementBackend.core.database import SessionLocal
from TaskManagementBackend.core.security import createAccessToken, hashPassword
from TaskManagementBackend.models import Team, TeamLevel, TeamMember, User
from TaskManagementBackend.models.enums import JoinMethod, TeamRole, TeamStatus


def createTestUser(username: str, nickname: str) -> dict:
    """直接写入测试用户并签发访问 token，返回 {id, headers} 字典。"""
    databaseSession = SessionLocal()
    try:
        user = User(username=username, passwordHash=hashPassword("Password123"), nickname=nickname)
        databaseSession.add(user)
        databaseSession.commit()
        databaseSession.refresh(user)
        token = createAccessToken(user.id, user.username, user.globalRole.value)["token"]
        return {"id": user.id, "headers": buildAuthHeaders(token)}
    finally:
        databaseSession.close()


def createActiveTeam(adminUserId: int, name: str) -> dict:
    """创建已认证团队与默认三个级别，返回 {id, name, levels}；创建者写入成员关系。"""
    databaseSession = SessionLocal()
    try:
        team = Team(
            name=name,
            description="Task module automated test team",
            joinMethod=JoinMethod.INVITE_ONLY,
            status=TeamStatus.ACTIVE,
            createdBy=adminUserId,
        )
        databaseSession.add(team)
        databaseSession.flush()
        levelIds: dict[int, int] = {}
        for levelOrder, levelName, canCreateTask in ((3, "Senior Member", True), (2, "Intermediate Member", True), (1, "Junior Member", False)):
            level = TeamLevel(
                teamId=team.id, name=levelName, levelOrder=levelOrder, canCreateTask=canCreateTask
            )
            databaseSession.add(level)
            databaseSession.flush()
            levelIds[levelOrder] = level.id
        databaseSession.add(
            TeamMember(teamId=team.id, userId=adminUserId, role=TeamRole.ADMIN, levelId=levelIds[3])
        )
        databaseSession.commit()
        return {"id": team.id, "name": team.name, "levels": levelIds}
    finally:
        databaseSession.close()


def addTeamMember(teamId: int, userId: int, levelId: int, role: TeamRole = TeamRole.MEMBER) -> None:
    """直接写入团队成员关系。"""
    databaseSession = SessionLocal()
    try:
        databaseSession.add(TeamMember(teamId=teamId, userId=userId, role=role, levelId=levelId))
        databaseSession.commit()
    finally:
        databaseSession.close()


@pytest.fixture()
def workspace(client) -> dict:
    """任务测试工作区：管理员、中级发布者、两名初级执行人与外部用户。"""
    owner = createTestUser("ownerTask01", "Team Admin")
    publisher = createTestUser("publisherTask01", "Intermediate Publisher")
    junior = createTestUser("juniorTask01", "Junior Assignee")
    juniorTwo = createTestUser("juniorTask02", "Second Junior Assignee")
    outsider = createTestUser("outsiderTask01", "Outsider")
    team = createActiveTeam(owner["id"], "Task Test Team")
    addTeamMember(team["id"], publisher["id"], team["levels"][2])
    addTeamMember(team["id"], junior["id"], team["levels"][1])
    addTeamMember(team["id"], juniorTwo["id"], team["levels"][1])
    return {
        "owner": owner,
        "publisher": publisher,
        "junior": junior,
        "juniorTwo": juniorTwo,
        "outsider": outsider,
        "team": team,
    }


def buildCreatePayload(**overrides) -> dict:
    """构造发布任务请求体，允许用例覆盖任意字段。"""
    payload = {
        "title": "Implement task module endpoints",
        "description": "Backend Development task module",
        "priority": "medium",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUserIds": [],
    }
    payload.update(overrides)
    return payload


def createTask(client, headers, teamId: int, **overrides) -> dict:
    """调用发布任务接口并断言成功，返回任务详情字典。"""
    response = client.post(
        f"/api/v1/teams/{teamId}/tasks", json=buildCreatePayload(**overrides), headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def testCreateMandatoryTaskAutoInProgress(client, workspace):
    """必须接受任务：分配记录直接进行中，任务聚合状态为 inProgress。"""
    task = createTask(
        client, workspace["owner"]["headers"], workspace["team"]["id"],
        targetUserIds=[workspace["junior"]["id"]],
    )
    assert task["status"] == "inProgress"
    assert task["teamName"] == workspace["team"]["name"]
    assert task["createdByName"] == "Team Admin"
    assert len(task["assignments"]) == 1
    assert task["assignments"][0]["status"] == "inProgress"
    assert task["assignments"][0]["acceptedAt"] is not None
    assert task["myAssignment"] is None and task["canReview"] is True and task["canEdit"] is True


def testCreateOptionalTaskWaitsForAcceptance(client, workspace):
    """可选任务：分配记录待接受，任务聚合状态为 published。"""
    task = createTask(
        client, workspace["owner"]["headers"], workspace["team"]["id"],
        acceptanceMode="optional", targetUserIds=[workspace["junior"]["id"]],
    )
    assert task["status"] == "published"
    assert task["assignments"][0]["status"] == "pendingAcceptance"
    assert task["assignments"][0]["acceptedAt"] is None


def testCreateLevelRangeTaskAssignsRangeMembers(client, workspace):
    """级别范围模式：为范围内全部成员创建分配记录。"""
    task = createTask(
        client, workspace["owner"]["headers"], workspace["team"]["id"],
        assignmentMode="levelRange", targetLevelMin=1, targetLevelMax=2,
        targetUserIds=None,
    )
    assignedUserIds = {assignment["userId"] for assignment in task["assignments"]}
    assert assignedUserIds == {workspace["publisher"]["id"], workspace["junior"]["id"], workspace["juniorTwo"]["id"]}
    assert task["targetLevelMin"] == 1 and task["targetLevelMax"] == 2


def testCreateTaskPermissionRejected(client, workspace):
    """发布权限：低级别成员不能发布任务，普通成员不能给高级别成员布置任务。"""
    teamId = workspace["team"]["id"]
    lowerLevelResponse = client.post(
        f"/api/v1/teams/{teamId}/tasks",
        json=buildCreatePayload(targetUserIds=[workspace["juniorTwo"]["id"]]),
        headers=workspace["junior"]["headers"],
    )
    assert lowerLevelResponse.status_code == 403
    higherTargetResponse = client.post(
        f"/api/v1/teams/{teamId}/tasks",
        json=buildCreatePayload(targetUserIds=[workspace["owner"]["id"]]),
        headers=workspace["publisher"]["headers"],
    )
    assert higherTargetResponse.status_code == 403


def testCreateTaskValidationErrors(client, workspace):
    """参数校验：标题过短、截止时间已过、指定成员为空、级别范围缺失均返回 400。"""
    teamId = workspace["team"]["id"]
    headers = workspace["owner"]["headers"]
    invalidPayloads = [
        buildCreatePayload(title="x", targetUserIds=[workspace["junior"]["id"]]),
        buildCreatePayload(dueAt="2020-01-01T00:00:00", targetUserIds=[workspace["junior"]["id"]]),
        buildCreatePayload(targetUserIds=[]),
        buildCreatePayload(assignmentMode="levelRange", targetUserIds=None),
    ]
    for payload in invalidPayloads:
        response = client.post(f"/api/v1/teams/{teamId}/tasks", json=payload, headers=headers)
        assert response.status_code == 400, response.text


def testTeamTaskListFiltersAndPagination(client, workspace):
    """团队任务列表：关键词/优先级筛选、优先级排序与分页结构符合契约。"""
    teamId = workspace["team"]["id"]
    headers = workspace["owner"]["headers"]
    firstTask = createTask(client, headers, teamId, title="Frontend page optimization", priority="high", targetUserIds=[workspace["junior"]["id"]])
    secondTask = createTask(client, headers, teamId, title="Backend API integration", priority="low", targetUserIds=[workspace["juniorTwo"]["id"]])
    keywordResponse = client.get(f"/api/v1/teams/{teamId}/tasks", params={"keyword": "Frontend"}, headers=headers)
    assert keywordResponse.status_code == 200
    assert keywordResponse.json()["total"] == 1
    assert keywordResponse.json()["items"][0]["id"] == firstTask["id"]
    priorityResponse = client.get(
        f"/api/v1/teams/{teamId}/tasks", params={"sortBy": "priority", "sortOrder": "desc"}, headers=headers
    )
    priorities = [item["priority"] for item in priorityResponse.json()["items"]]
    assert priorities == ["high", "low"]
    pageResponse = client.get(
        f"/api/v1/teams/{teamId}/tasks", params={"page": 1, "pageSize": 1}, headers=headers
    )
    assert pageResponse.json()["total"] == 2 and len(pageResponse.json()["items"]) == 1
    assert secondTask["id"] != firstTask["id"]


def testTaskDetailPermissionAndFields(client, workspace):
    """任务详情：同团队成员可看（含 myAssignment/canReview），非成员返回 403。"""
    task = createTask(
        client, workspace["owner"]["headers"], workspace["team"]["id"],
        targetUserIds=[workspace["junior"]["id"], workspace["juniorTwo"]["id"]],
    )
    juniorResponse = client.get(f"/api/v1/tasks/{task['id']}", headers=workspace["junior"]["headers"])
    assert juniorResponse.status_code == 200
    juniorDetail = juniorResponse.json()
    assert juniorDetail["myAssignment"]["userId"] == workspace["junior"]["id"]
    assert juniorDetail["canReview"] is False and juniorDetail["canEdit"] is False
    assert len(juniorDetail["assignments"]) == 2 and juniorDetail["reviewCount"] == 0
    outsiderResponse = client.get(f"/api/v1/tasks/{task['id']}", headers=workspace["outsider"]["headers"])
    assert outsiderResponse.status_code == 403


def testUpdateTaskAndPermission(client, workspace):
    """修改任务：发布者可改字段，非发布者普通成员返回 403。"""
    teamId = workspace["team"]["id"]
    task = createTask(client, workspace["owner"]["headers"], teamId, targetUserIds=[workspace["junior"]["id"]])
    updateResponse = client.put(
        f"/api/v1/teams/{teamId}/tasks/{task['id']}",
        json={"title": "Updated task title", "priority": "urgent", "description": "Updated description"},
        headers=workspace["owner"]["headers"],
    )
    assert updateResponse.status_code == 200, updateResponse.text
    updatedTask = updateResponse.json()
    assert updatedTask["title"] == "Updated task title"
    assert updatedTask["priority"] == "urgent"
    forbiddenResponse = client.put(
        f"/api/v1/teams/{teamId}/tasks/{task['id']}",
        json={"title": "Unauthorized title change"},
        headers=workspace["junior"]["headers"],
    )
    assert forbiddenResponse.status_code == 403


def testCancelTaskTransitions(client, workspace):
    """取消任务：发布者可取消未归档任务；重复取消与普通成员取消分别返回 400/403。"""
    teamId = workspace["team"]["id"]
    task = createTask(client, workspace["owner"]["headers"], teamId, targetUserIds=[workspace["junior"]["id"]])
    cancelResponse = client.post(f"/api/v1/tasks/{task['id']}/cancel", headers=workspace["owner"]["headers"])
    assert cancelResponse.status_code == 200
    assert cancelResponse.json()["status"] == "cancelled"
    repeatedResponse = client.post(f"/api/v1/tasks/{task['id']}/cancel", headers=workspace["owner"]["headers"])
    assert repeatedResponse.status_code == 400
    otherTask = createTask(client, workspace["owner"]["headers"], teamId, targetUserIds=[workspace["junior"]["id"]])
    forbiddenResponse = client.post(
        f"/api/v1/tasks/{otherTask['id']}/cancel", headers=workspace["junior"]["headers"]
    )
    assert forbiddenResponse.status_code == 403


def testMyTaskCenterRoleFilters(client, workspace):
    """我的任务中心：role=created 返回我发布的，role=assigned 返回我参与的。"""
    teamId = workspace["team"]["id"]
    task = createTask(client, workspace["owner"]["headers"], teamId, targetUserIds=[workspace["junior"]["id"]])
    createdResponse = client.get("/api/v1/tasks", params={"role": "created"}, headers=workspace["owner"]["headers"])
    assert createdResponse.status_code == 200
    assert [item["id"] for item in createdResponse.json()["items"]] == [task["id"]]
    assignedResponse = client.get("/api/v1/tasks", params={"role": "assigned"}, headers=workspace["junior"]["headers"])
    assert [item["id"] for item in assignedResponse.json()["items"]] == [task["id"]]
    ownerAssignedResponse = client.get("/api/v1/tasks", params={"role": "assigned"}, headers=workspace["owner"]["headers"])
    assert ownerAssignedResponse.json()["total"] == 0
