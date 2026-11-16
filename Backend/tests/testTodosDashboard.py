"""待办与仪表盘接口测试：接受/拒绝/提交/审核状态机、待办列表统计、仪表盘汇总。

复用 testTasks.py 中的测试数据构造辅助函数与 workspace 夹具；
每个用例结束由 conftest 自动清库，状态机分支与权限拒绝均有覆盖。
"""

from datetime import datetime, timedelta

from tests.testTasks import createActiveTeam, createTask, workspace
from TaskManagementBackend.core.database import SessionLocal
from TaskManagementBackend.models import Task


def setTaskDueAt(taskId: int, dueAt: datetime) -> None:
    """直接修改任务截止时间，用于构造逾期待办场景。"""
    databaseSession = SessionLocal()
    try:
        task = databaseSession.get(Task, taskId)
        task.dueAt = dueAt
        databaseSession.commit()
    finally:
        databaseSession.close()


def submitTask(client, headers, taskId: int) -> dict:
    """调用提交完成接口并断言成功。"""
    response = client.post(f"/api/v1/tasks/{taskId}/submit", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def reviewTask(client, headers, taskId: int, assignmentUserId: int, approved: bool, comment=None) -> dict:
    """调用审核接口并返回响应对象（由用例自行断言状态码）。"""
    payload = {"assignmentUserId": assignmentUserId, "approved": approved}
    if comment is not None:
        payload["comment"] = comment
    return client.post(f"/api/v1/tasks/{taskId}/review", json=payload, headers=headers)


def testAcceptOptionalTask(client, workspace):
    """接受可选任务：待办进入进行中；重复接受返回 400。"""
    task = createTask(
        client, workspace["owner"]["headers"], workspace["team"]["id"],
        acceptanceMode="optional", targetUserIds=[workspace["junior"]["id"]],
    )
    juniorHeaders = workspace["junior"]["headers"]
    todoList = client.get("/api/v1/todos", headers=juniorHeaders).json()
    assert todoList["items"][0]["assignmentStatus"] == "pendingAcceptance"
    acceptResponse = client.post(f"/api/v1/tasks/{task['id']}/acceptance", headers=juniorHeaders)
    assert acceptResponse.status_code == 200, acceptResponse.text
    assert acceptResponse.json()["myAssignment"]["status"] == "inProgress"
    assert acceptResponse.json()["status"] == "inProgress"
    repeatedResponse = client.post(f"/api/v1/tasks/{task['id']}/acceptance", headers=juniorHeaders)
    assert repeatedResponse.status_code == 400
    assert client.get("/api/v1/todos/stats", headers=juniorHeaders).json()["inProgress"] == 1
    mandatoryTask = createTask(
        client, workspace["owner"]["headers"], workspace["team"]["id"],
        targetUserIds=[workspace["junior"]["id"]],
    )
    mandatoryResponse = client.post(f"/api/v1/tasks/{mandatoryTask['id']}/acceptance", headers=juniorHeaders)
    assert mandatoryResponse.status_code == 400


def testDeclineMandatoryAndOptionalTask(client, workspace):
    """拒绝规则：必须接受任务拒绝返回 400；可选任务单人拒绝后任务自动取消。"""
    teamId = workspace["team"]["id"]
    mandatoryTask = createTask(client, workspace["owner"]["headers"], teamId, targetUserIds=[workspace["junior"]["id"]])
    mandatoryResponse = client.post(f"/api/v1/tasks/{mandatoryTask['id']}/decline", headers=workspace["junior"]["headers"])
    assert mandatoryResponse.status_code == 400
    optionalTask = createTask(
        client, workspace["owner"]["headers"], teamId,
        acceptanceMode="optional", targetUserIds=[workspace["junior"]["id"]],
    )
    declineResponse = client.post(f"/api/v1/tasks/{optionalTask['id']}/decline", headers=workspace["junior"]["headers"])
    assert declineResponse.status_code == 200, declineResponse.text
    declinedTask = declineResponse.json()
    assert declinedTask["assignments"] == []
    assert declinedTask["status"] == "cancelled"


def testDeclineOptionalTaskKeepsOtherAssignees(client, workspace):
    """可选任务多人分配：一人拒绝后任务保留，其余待接受成员继续存在。"""
    task = createTask(
        client, workspace["owner"]["headers"], workspace["team"]["id"],
        acceptanceMode="optional",
        targetUserIds=[workspace["junior"]["id"], workspace["juniorTwo"]["id"]],
    )
    declineResponse = client.post(f"/api/v1/tasks/{task['id']}/decline", headers=workspace["junior"]["headers"])
    assert declineResponse.status_code == 200
    declinedTask = declineResponse.json()
    assert [item["userId"] for item in declinedTask["assignments"]] == [workspace["juniorTwo"]["id"]]
    assert declinedTask["status"] == "published"


def testSubmitAndReviewApproveFlow(client, workspace):
    """审核通过：待办归档，全部归档后任务归档并记录归档时间与审核记录。"""
    task = createTask(client, workspace["owner"]["headers"], workspace["team"]["id"], targetUserIds=[workspace["junior"]["id"]])
    submittedTask = submitTask(client, workspace["junior"]["headers"], task["id"])
    assert submittedTask["myAssignment"]["status"] == "pendingReview"
    assert submittedTask["status"] == "pendingReview"
    reviewResponse = reviewTask(client, workspace["owner"]["headers"], task["id"], workspace["junior"]["id"], True, "Good quality")
    assert reviewResponse.status_code == 200, reviewResponse.text
    archivedTask = reviewResponse.json()
    assert archivedTask["status"] == "archived"
    assert archivedTask["archivedAt"] is not None
    assert archivedTask["assignments"][0]["status"] == "archived"
    assert archivedTask["reviewCount"] == 1
    assert archivedTask["reviews"][0]["result"] == "approved"
    assert archivedTask["reviews"][0]["comment"] == "Good quality"
    assert archivedTask["reviews"][0]["reviewerName"] == "Team Admin"
    todoList = client.get("/api/v1/todos", headers=workspace["junior"]["headers"]).json()
    assert todoList["total"] == 0
    archivedList = client.get(
        "/api/v1/todos", params={"includeArchived": True}, headers=workspace["junior"]["headers"]
    ).json()
    assert archivedList["total"] == 1
    assert client.get("/api/v1/todos/stats", headers=workspace["junior"]["headers"]).json()["archived"] == 1
    teamId = workspace["team"]["id"]
    updateArchivedResponse = client.put(
        f"/api/v1/teams/{teamId}/tasks/{task['id']}",
        json={"title": "Update archived task title"},
        headers=workspace["owner"]["headers"],
    )
    assert updateArchivedResponse.status_code == 400
    cancelArchivedResponse = client.post(
        f"/api/v1/tasks/{task['id']}/cancel", headers=workspace["owner"]["headers"]
    )
    assert cancelArchivedResponse.status_code == 400
    archivedSummary = client.get("/api/v1/dashboard/summary", headers=workspace["junior"]["headers"]).json()
    assert archivedSummary["archivedTotal"] == 1 and archivedSummary["archivedThisWeek"] == 1
    assert archivedSummary["weeklyTrend"][-1]["completed"] == 1


def testReviewRejectFlow(client, workspace):
    """审核驳回：待办回到进行中并写入审核意见，可再次提交并审核通过。"""
    task = createTask(client, workspace["owner"]["headers"], workspace["team"]["id"], targetUserIds=[workspace["junior"]["id"]])
    submitTask(client, workspace["junior"]["headers"], task["id"])
    rejectResponse = reviewTask(client, workspace["owner"]["headers"], task["id"], workspace["junior"]["id"], False, "Please add test cases")
    assert rejectResponse.status_code == 200, rejectResponse.text
    rejectedTask = rejectResponse.json()
    assert rejectedTask["status"] == "inProgress"
    assert rejectedTask["assignments"][0]["status"] == "inProgress"
    assert rejectedTask["assignments"][0]["reviewComment"] == "Please add test cases"
    assert rejectedTask["reviews"][0]["result"] == "rejected"
    assert rejectedTask["reviewCount"] == 1
    submitTask(client, workspace["junior"]["headers"], task["id"])
    approveResponse = reviewTask(client, workspace["owner"]["headers"], task["id"], workspace["junior"]["id"], True)
    assert approveResponse.status_code == 200
    assert approveResponse.json()["status"] == "archived"
    assert approveResponse.json()["reviewCount"] == 2


def testReviewPermissionAndIllegalStates(client, workspace):
    """审核权限与非法状态：非发布者 403、未提交审核 400、执行人不存在 404、重复提交 400。"""
    teamId = workspace["team"]["id"]
    task = createTask(client, workspace["owner"]["headers"], teamId, targetUserIds=[workspace["junior"]["id"]])
    forbiddenResponse = reviewTask(client, workspace["junior"]["headers"], task["id"], workspace["junior"]["id"], True)
    assert forbiddenResponse.status_code == 403
    illegalStateResponse = reviewTask(client, workspace["owner"]["headers"], task["id"], workspace["junior"]["id"], True)
    assert illegalStateResponse.status_code == 400
    missingAssignment = reviewTask(client, workspace["owner"]["headers"], task["id"], workspace["juniorTwo"]["id"], True)
    assert missingAssignment.status_code == 404
    submitTask(client, workspace["junior"]["headers"], task["id"])
    repeatedSubmit = client.post(f"/api/v1/tasks/{task['id']}/submit", headers=workspace["junior"]["headers"])
    assert repeatedSubmit.status_code == 400
    nonExecutorSubmit = client.post(f"/api/v1/tasks/{task['id']}/submit", headers=workspace["juniorTwo"]["headers"])
    assert nonExecutorSubmit.status_code == 403


def testTodoListFiltersAndOverdue(client, workspace):
    """待办列表：关键词/优先级/状态筛选与优先级排序，逾期标记与统计正确。"""
    teamId = workspace["team"]["id"]
    juniorHeaders = workspace["junior"]["headers"]
    overdueTask = createTask(
        client, workspace["owner"]["headers"], teamId,
        title="Overdue task investigation", priority="urgent", targetUserIds=[workspace["junior"]["id"]],
    )
    setTaskDueAt(overdueTask["id"], datetime.now() - timedelta(hours=2))
    createTask(
        client, workspace["owner"]["headers"], teamId,
        title="Regular task documentation", priority="low", acceptanceMode="optional", targetUserIds=[workspace["junior"]["id"]],
    )
    todoList = client.get("/api/v1/todos", headers=juniorHeaders).json()
    assert todoList["total"] == 2
    overdueItem = next(item for item in todoList["items"] if item["taskId"] == overdueTask["id"])
    assert overdueItem["overdue"] is True
    assert overdueItem["priority"] == "urgent"
    keywordList = client.get("/api/v1/todos", params={"keyword": "documentation"}, headers=juniorHeaders).json()
    assert keywordList["total"] == 1
    statusList = client.get("/api/v1/todos", params={"status": "inProgress"}, headers=juniorHeaders).json()
    assert statusList["total"] == 1 and statusList["items"][0]["taskId"] == overdueTask["id"]
    stats = client.get("/api/v1/todos/stats", headers=juniorHeaders).json()
    assert stats["total"] == 2 and stats["inProgress"] == 1 and stats["pendingAcceptance"] == 1
    assert stats["overdue"] == 1


def testDashboardSummary(client, workspace):
    """仪表盘汇总：待办计数、优先级/状态分布、近七日趋势与团队统计结构完整。"""
    teamId = workspace["team"]["id"]
    createTask(client, workspace["owner"]["headers"], teamId, targetUserIds=[workspace["junior"]["id"]])
    createTask(
        client, workspace["owner"]["headers"], teamId,
        acceptanceMode="optional", priority="high", targetUserIds=[workspace["junior"]["id"]],
    )
    summaryResponse = client.get("/api/v1/dashboard/summary", headers=workspace["junior"]["headers"])
    assert summaryResponse.status_code == 200, summaryResponse.text
    summary = summaryResponse.json()
    assert summary["todoCount"] == 2
    assert summary["inProgressCount"] == 1 and summary["pendingAcceptanceCount"] == 1
    assert summary["pendingReviewCount"] == 0 and summary["overdueCount"] == 0
    assert isinstance(summary["byPriority"], list) and isinstance(summary["byStatus"], list)
    assert len(summary["weeklyTrend"]) == 7
    assert len(summary["teamStats"]) == 1
    teamStat = summary["teamStats"][0]
    assert teamStat["teamId"] == teamId and teamStat["memberCount"] == 4
    assert teamStat["openTaskCount"] == 2 and teamStat["archivedTaskCount"] == 0
    teamSummary = client.get(
        "/api/v1/dashboard/summary", params={"teamId": teamId}, headers=workspace["junior"]["headers"]
    )
    assert teamSummary.status_code == 200 and len(teamSummary.json()["teamStats"]) == 1
    outsiderTeam = createActiveTeam(workspace["outsider"]["id"], "Outsider Team")
    forbiddenResponse = client.get(
        "/api/v1/dashboard/summary",
        params={"teamId": outsiderTeam["id"]},
        headers=workspace["junior"]["headers"],
    )
    assert forbiddenResponse.status_code == 403
