"""协作任务模块接口测试：接收方确认指派、双审核闭环（含双审核驳回）、权限与状态校验。

测试数据通过数据库直接构造，协作关系与协作任务通过真实 HTTP 接口串起状态机。
"""

import pytest

from TaskManagementBackend.core.database import SessionLocal
from TaskManagementBackend.core.security import createAccessToken, hashPassword
from TaskManagementBackend.models import SubTeam, SubTeamMember, Team, TeamLevel, TeamMember, User
from TaskManagementBackend.models.enums import JoinMethod, TeamRole, TeamStatus
from tests.helpers import buildAuthHeaders


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
    """创建已认证团队与默认三个级别，返回 {id, levels}；创建者写入管理员成员关系。"""
    databaseSession = SessionLocal()
    try:
        team = Team(
            name=name,
            description="Collaboration task test team",
            joinMethod=JoinMethod.INVITE_ONLY,
            status=TeamStatus.ACTIVE,
            createdBy=adminUserId,
        )
        databaseSession.add(team)
        databaseSession.flush()
        levelIds: dict[int, int] = {}
        for levelOrder, levelName in ((3, "Senior Member"), (2, "Intermediate Member"), (1, "Junior Member")):
            level = TeamLevel(teamId=team.id, name=levelName, levelOrder=levelOrder, canCreateTask=True)
            databaseSession.add(level)
            databaseSession.flush()
            levelIds[levelOrder] = level.id
        databaseSession.add(
            TeamMember(teamId=team.id, userId=adminUserId, role=TeamRole.ADMIN, levelId=levelIds[3])
        )
        databaseSession.commit()
        return {"id": team.id, "levels": levelIds}
    finally:
        databaseSession.close()


def addTeamMember(teamId: int, userId: int, levelId: int) -> None:
    """直接写入团队普通成员关系。"""
    databaseSession = SessionLocal()
    try:
        databaseSession.add(
            TeamMember(teamId=teamId, userId=userId, role=TeamRole.MEMBER, levelId=levelId)
        )
        databaseSession.commit()
    finally:
        databaseSession.close()


def createSubTeamDirect(teamId: int, name: str, leaderUserId: int, memberUserIds: list[int]) -> int:
    """直接写入子团队与成员关系，返回子团队主键。"""
    databaseSession = SessionLocal()
    try:
        subTeam = SubTeam(parentTeamId=teamId, name=name, description="Test sub-team", leaderUserId=leaderUserId)
        databaseSession.add(subTeam)
        databaseSession.flush()
        for userId in set(memberUserIds):
            databaseSession.add(SubTeamMember(subTeamId=subTeam.id, userId=userId))
        databaseSession.commit()
        return subTeam.id
    finally:
        databaseSession.close()


@pytest.fixture()
def world() -> dict:
    """协作任务工作区：发起方管理员/对接人、接收方管理员/对接人、两名执行人与外部用户。"""
    sourceAdmin = createTestUser("taskSourceAdmin01", "Initiating Admin")
    sourceLiaison = createTestUser("taskSourceLiaison01", "Initiating Liaison")
    targetAdmin = createTestUser("taskTargetAdmin01", "Receiving Admin")
    targetLiaison = createTestUser("taskTargetLiaison01", "Receiving Liaison")
    executorOne = createTestUser("taskExecutor01", "Executor One")
    executorTwo = createTestUser("taskExecutor02", "Executor Two")
    outsider = createTestUser("taskOutsider01", "Outsider")
    sourceTeam = createActiveTeam(sourceAdmin["id"], "Collaboration Task Initiator Team")
    targetTeam = createActiveTeam(targetAdmin["id"], "Collaboration Task Receiver Team")
    addTeamMember(sourceTeam["id"], sourceLiaison["id"], sourceTeam["levels"][1])
    for account in (targetLiaison, executorOne, executorTwo):
        addTeamMember(targetTeam["id"], account["id"], targetTeam["levels"][1])
    return {
        "sourceAdmin": sourceAdmin,
        "sourceLiaison": sourceLiaison,
        "targetAdmin": targetAdmin,
        "targetLiaison": targetLiaison,
        "executorOne": executorOne,
        "executorTwo": executorTwo,
        "outsider": outsider,
        "sourceTeam": sourceTeam,
        "targetTeam": targetTeam,
    }


def setupCollaboration(client, world: dict, **overrides) -> dict:
    """创建并确认一条协作关系，返回协作数据。"""
    payload = {
        "initiatorTeamId": world["sourceTeam"]["id"],
        "targetTeamId": world["targetTeam"]["id"],
        "initiatorLiaisonUserId": world["sourceLiaison"]["id"],
        "message": "Collaboration task test request",
    }
    payload.update(overrides)
    createResponse = client.post(
        "/api/v1/collaborations", json=payload, headers=world["sourceAdmin"]["headers"]
    )
    assert createResponse.status_code == 200, createResponse.text
    collaborationId = createResponse.json()["id"]
    confirmResponse = client.post(
        f"/api/v1/collaborations/{collaborationId}/confirm",
        json={"approved": True, "targetLiaisonUserId": world["targetLiaison"]["id"]},
        headers=world["targetAdmin"]["headers"],
    )
    assert confirmResponse.status_code == 200, confirmResponse.text
    return confirmResponse.json()


def createTask(client, world: dict, collaborationId: int, headers: dict | None = None) -> dict:
    """发起方发布协作任务并返回任务详情。"""
    response = client.post(
        f"/api/v1/collaborations/{collaborationId}/tasks",
        json={
            "title": "Collaboration Task Loop Test",
            "description": "Verify two-stage review loop",
            "priority": "high",
            "acceptanceMode": "mandatory",
        },
        headers=headers or world["sourceAdmin"]["headers"],
    )
    assert response.status_code == 200, response.text
    return response.json()


def confirmTask(client, world: dict, taskId: int, assigneeUserIds: list[int], approved: bool = True, headers: dict | None = None, comment: str | None = None):
    """接收方对接人确认/拒绝协作任务，返回响应对象。"""
    payload: dict = {"approved": approved, "assigneeUserIds": assigneeUserIds}
    if comment is not None:
        payload["comment"] = comment
    return client.post(
        f"/api/v1/collaboration-tasks/{taskId}/confirm",
        json=payload,
        headers=headers or world["targetLiaison"]["headers"],
    )


def submitTask(client, headers: dict, taskId: int):
    """执行人提交完成。"""
    return client.post(f"/api/v1/tasks/{taskId}/submit", headers=headers)


def reviewTask(client, world: dict, taskId: int, executorId: int, approved: bool, stage: str = "target", headers: dict | None = None, comment: str | None = None):
    """调用接收方/发起方审核接口。"""
    defaultHeaders = (
        world["targetLiaison"]["headers"] if stage == "target" else world["sourceAdmin"]["headers"]
    )
    return client.post(
        f"/api/v1/collaboration-tasks/{taskId}/{stage}-review",
        json={"assignmentUserId": executorId, "approved": approved, "comment": comment},
        headers=headers or defaultHeaders,
    )


def testFullCollaborationTaskFlowAndNotifications(client, world):
    """完整闭环：创建→确认指派→提交→接收方审核→发起方审核归档，并校验通知与响应字段。"""
    collaboration = setupCollaboration(client, world)
    collaborationId = collaboration["id"]
    task = createTask(client, world, collaborationId)
    assert task["collaborationId"] == collaborationId
    assert task["collaborationPhase"] == "pendingConfirmation"
    assert task["status"] == "published" and task["assignments"] == []
    assert task["sourceUnit"]["teamName"] == "Collaboration Task Initiator Team"
    assert task["targetUnit"]["teamName"] == "Collaboration Task Receiver Team"
    assert task["canConfirmTask"] is False and task["canSourceReview"] is False
    detailAsTargetLiaison = client.get(
        f"/api/v1/collaboration-tasks/{task['id']}", headers=world["targetLiaison"]["headers"]
    )
    assert detailAsTargetLiaison.status_code == 200
    assert detailAsTargetLiaison.json()["canConfirmTask"] is True
    confirmed = confirmTask(client, world, task["id"], [world["executorOne"]["id"]])
    assert confirmed.status_code == 200, confirmed.text
    confirmedTask = confirmed.json()
    assert confirmedTask["collaborationPhase"] == "executing"
    assert confirmedTask["status"] == "inProgress"
    assignment = confirmedTask["assignments"][0]
    assert assignment["assignmentSource"] == "collaboration" and assignment["acceptedAt"] is not None
    executorNotifications = client.get(
        "/api/v1/notifications", headers=world["executorOne"]["headers"]
    ).json()["items"]
    assert "taskAssigned" in {item["type"] for item in executorNotifications}
    liaisonNotifications = client.get(
        "/api/v1/notifications", headers=world["sourceLiaison"]["headers"]
    ).json()["items"]
    assert "collaborationTaskConfirmed" in {item["type"] for item in liaisonNotifications}
    submitResponse = submitTask(client, world["executorOne"]["headers"], task["id"])
    assert submitResponse.status_code == 200, submitResponse.text
    assert submitResponse.json()["collaborationPhase"] == "targetReview"
    targetReviewResponse = reviewTask(
        client, world, task["id"], world["executorOne"]["id"], True, "target", comment="Receiver approved"
    )
    assert targetReviewResponse.status_code == 200, targetReviewResponse.text
    reviewedDetail = targetReviewResponse.json()
    assert reviewedDetail["collaborationPhase"] == "sourceReview"
    assert reviewedDetail["status"] == "pendingReview"
    assert len(reviewedDetail["reviews"]) == 1
    sourceDetail = client.get(
        f"/api/v1/collaboration-tasks/{task['id']}", headers=world["sourceAdmin"]["headers"]
    ).json()
    assert sourceDetail["canSourceReview"] is True
    sourceReviewResponse = reviewTask(
        client, world, task["id"], world["executorOne"]["id"], True, "source", comment="Initiator approved"
    )
    assert sourceReviewResponse.status_code == 200, sourceReviewResponse.text
    archivedTask = sourceReviewResponse.json()
    assert archivedTask["status"] == "archived" and archivedTask["collaborationPhase"] is None
    assert len(archivedTask["reviews"]) == 2
    executorNotifications = client.get(
        "/api/v1/notifications", headers=world["executorOne"]["headers"]
    ).json()["items"]
    assert "taskReviewResult" in {item["type"] for item in executorNotifications}
    archiveNotifications = client.get(
        "/api/v1/notifications", headers=world["sourceLiaison"]["headers"]
    ).json()["items"]
    assert "collaborationTaskArchived" in {item["type"] for item in archiveNotifications}
    taskListResponse = client.get(
        f"/api/v1/collaborations/{collaborationId}/tasks",
        headers=world["targetLiaison"]["headers"],
    )
    assert taskListResponse.status_code == 200 and taskListResponse.json()["total"] == 1
    outsiderResponse = client.get(
        f"/api/v1/collaboration-tasks/{task['id']}", headers=world["outsider"]["headers"]
    )
    assert outsiderResponse.status_code == 403


def testDoubleReviewRejectBranches(client, world):
    """双审核驳回分支：接收方驳回与发起方驳回均回到执行中，重新提交后可再次审核归档。"""
    collaboration = setupCollaboration(client, world)
    task = createTask(client, world, collaboration["id"])
    executorId = world["executorOne"]["id"]
    assert confirmTask(client, world, task["id"], [executorId]).status_code == 200
    stage = "target"
    submitTask(client, world["executorOne"]["headers"], task["id"])
    rejected = reviewTask(client, world, task["id"], executorId, False, "target", comment="Add test screenshots")
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["collaborationPhase"] == "executing"
    assert rejected.json()["assignments"][0]["reviewComment"] == "Add test screenshots"
    submitTask(client, world["executorOne"]["headers"], task["id"])
    assert reviewTask(client, world, task["id"], executorId, True, "target").status_code == 200
    sourceRejected = reviewTask(client, world, task["id"], executorId, False, "source", comment="Feature incomplete")
    assert sourceRejected.status_code == 200, sourceRejected.text
    assert sourceRejected.json()["collaborationPhase"] == "executing"
    assert sourceRejected.json()["status"] == "inProgress"
    submitTask(client, world["executorOne"]["headers"], task["id"])
    assert reviewTask(client, world, task["id"], executorId, True, "target").status_code == 200
    finalResponse = reviewTask(client, world, task["id"], executorId, True, "source")
    assert finalResponse.status_code == 200, finalResponse.text
    assert finalResponse.json()["status"] == "archived"
    # 审核记录：接收方驳回、接收方通过、发起方驳回、接收方通过、发起方通过，共 5 条
    assert len(finalResponse.json()["reviews"]) == 5


def testMultipleAssigneesPhaseTransitions(client, world):
    """多执行人：接收方逐个审核，全部进入发起方审核后任务仍待审核；全部归档后任务归档。"""
    collaboration = setupCollaboration(client, world)
    task = createTask(client, world, collaboration["id"])
    executorOneId = world["executorOne"]["id"]
    executorTwoId = world["executorTwo"]["id"]
    assert confirmTask(client, world, task["id"], [executorOneId, executorTwoId]).status_code == 200
    assert submitTask(client, world["executorOne"]["headers"], task["id"]).status_code == 200
    assert submitTask(client, world["executorTwo"]["headers"], task["id"]).status_code == 200
    firstTargetReviewed = reviewTask(client, world, task["id"], executorOneId, True, "target")
    assert firstTargetReviewed.json()["collaborationPhase"] == "targetReview"
    secondTargetReviewed = reviewTask(client, world, task["id"], executorTwoId, True, "target")
    assert secondTargetReviewed.json()["collaborationPhase"] == "sourceReview"
    firstSourceReviewed = reviewTask(client, world, task["id"], executorOneId, True, "source")
    assert firstSourceReviewed.json()["collaborationPhase"] == "sourceReview"
    finalResponse = reviewTask(client, world, task["id"], executorTwoId, True, "source")
    assert finalResponse.json()["status"] == "archived"
    assert finalResponse.json()["collaborationPhase"] is None


def testConfirmTaskPermissionsAndReject(client, world):
    """确认任务：创建/确认权限校验、执行人校验，拒绝后任务取消并通知发起方。"""
    collaboration = setupCollaboration(client, world)
    outsiderCreateResponse = client.post(
        f"/api/v1/collaborations/{collaboration['id']}/tasks",
        json={"title": "Unauthorized Task", "priority": "low", "acceptanceMode": "mandatory"},
        headers=world["outsider"]["headers"],
    )
    assert outsiderCreateResponse.status_code == 403
    targetLiaisonCreateResponse = client.post(
        f"/api/v1/collaborations/{collaboration['id']}/tasks",
        json={"title": "Unauthorized Task", "priority": "low", "acceptanceMode": "mandatory"},
        headers=world["targetLiaison"]["headers"],
    )
    assert targetLiaisonCreateResponse.status_code == 403
    task = createTask(client, world, collaboration["id"])
    nonLiaisonConfirmResponse = confirmTask(client, world, task["id"], [world["executorOne"]["id"]], headers=world["targetAdmin"]["headers"])
    assert nonLiaisonConfirmResponse.status_code == 403
    executorConfirmResponse = confirmTask(client, world, task["id"], [world["executorOne"]["id"]], headers=world["executorOne"]["headers"])
    assert executorConfirmResponse.status_code == 403
    emptyAssigneeResponse = confirmTask(client, world, task["id"], [])
    assert emptyAssigneeResponse.status_code == 400
    invalidAssigneeResponse = confirmTask(client, world, task["id"], [world["outsider"]["id"]])
    assert invalidAssigneeResponse.status_code == 400
    rejected = confirmTask(client, world, task["id"], [], approved=False, comment="No resources available")
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "cancelled"
    assert rejected.json()["collaborationPhase"] == "rejected"
    repeatedConfirmResponse = confirmTask(client, world, task["id"], [world["executorOne"]["id"]])
    assert repeatedConfirmResponse.status_code == 400
    liaisonNotifications = client.get(
        "/api/v1/notifications", headers=world["sourceLiaison"]["headers"]
    ).json()["items"]
    assert "collaborationTaskRejected" in {item["type"] for item in liaisonNotifications}
    initiatorLiaisonTask = createTask(client, world, collaboration["id"], headers=world["sourceLiaison"]["headers"])
    assert initiatorLiaisonTask["id"] != task["id"]


def testReviewStatusAndPermissionValidations(client, world):
    """审核状态与权限：未提交/错误阶段 400，非对接人/非发布者 403，跨阶段审核被拒绝。"""
    collaboration = setupCollaboration(client, world)
    task = createTask(client, world, collaboration["id"])
    executorId = world["executorOne"]["id"]
    earlyReviewResponse = reviewTask(client, world, task["id"], executorId, True, "target")
    assert earlyReviewResponse.status_code == 400
    invalidSubmitResponse = submitTask(client, world["targetLiaison"]["headers"], task["id"])
    assert invalidSubmitResponse.status_code == 403
    assert confirmTask(client, world, task["id"], [executorId]).status_code == 200
    submitTask(client, world["executorOne"]["headers"], task["id"])
    executorReviewResponse = reviewTask(client, world, task["id"], executorId, True, "target", headers=world["executorOne"]["headers"])
    assert executorReviewResponse.status_code == 403
    sourceReviewTooEarly = reviewTask(client, world, task["id"], executorId, True, "source")
    assert sourceReviewTooEarly.status_code == 400
    missingAssignmentResponse = reviewTask(client, world, task["id"], world["executorTwo"]["id"], True, "target")
    assert missingAssignmentResponse.status_code == 404
    assert reviewTask(client, world, task["id"], executorId, True, "target").status_code == 200
    targetLiaisonSourceReview = reviewTask(client, world, task["id"], executorId, True, "source", headers=world["targetLiaison"]["headers"])
    assert targetLiaisonSourceReview.status_code == 403
    liaisonSourceReview = reviewTask(client, world, task["id"], executorId, True, "source", headers=world["sourceLiaison"]["headers"])
    assert liaisonSourceReview.status_code == 403
    outsiderListResponse = client.get(
        f"/api/v1/collaborations/{collaboration['id']}/tasks", headers=world["outsider"]["headers"]
    )
    assert outsiderListResponse.status_code == 403
    assert reviewTask(client, world, task["id"], executorId, True, "source").status_code == 200


def testSubTeamUnitTaskAssignmentRules(client, world):
    """子团队作为协作单位：执行人必须属于接收子团队；父团队管理员可查看，非子团队成员 403。"""
    sourceSubTeamId = createSubTeamDirect(
        world["sourceTeam"]["id"], "Initiating Sub-team", world["sourceLiaison"]["id"], [world["sourceLiaison"]["id"]]
    )
    targetSubTeamId = createSubTeamDirect(
        world["targetTeam"]["id"],
        "Receiving Sub-team",
        world["targetLiaison"]["id"],
        [world["targetLiaison"]["id"], world["executorOne"]["id"]],
    )
    collaboration = setupCollaboration(
        client,
        world,
        initiatorSubTeamId=sourceSubTeamId,
        targetSubTeamId=targetSubTeamId,
    )
    task = createTask(client, world, collaboration["id"])
    nonMemberAssigneeResponse = confirmTask(client, world, task["id"], [world["executorTwo"]["id"]])
    assert nonMemberAssigneeResponse.status_code == 400
    confirmed = confirmTask(client, world, task["id"], [world["executorOne"]["id"]])
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["targetUnit"]["subTeamName"] == "Receiving Sub-team"
    parentAdminDetail = client.get(
        f"/api/v1/collaboration-tasks/{task['id']}", headers=world["sourceAdmin"]["headers"]
    )
    assert parentAdminDetail.status_code == 200
    plainSourceMember = createTestUser("taskPlainSource01", "Initiating Plain Member")
    addTeamMember(world["sourceTeam"]["id"], plainSourceMember["id"], world["sourceTeam"]["levels"][1])
    forbiddenDetail = client.get(
        f"/api/v1/collaboration-tasks/{task['id']}", headers=plainSourceMember["headers"]
    )
    assert forbiddenDetail.status_code == 403
