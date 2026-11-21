"""协作关系模块接口测试：协作目录、申请/确认/拒绝/结束、列表详情、单位候选成员与通知。

测试数据通过数据库直接构造，协作关系通过真实 HTTP 接口串起状态机。
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
            description="Collaboration module test team",
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
    """协作测试工作区：发起方/接收方管理员与成员、外部用户与两个已认证团队。"""
    sourceAdmin = createTestUser("sourceAdmin01", "Initiating Admin")
    sourceMember = createTestUser("sourceMember01", "Initiating Member")
    targetAdmin = createTestUser("targetAdmin01", "Receiving Admin")
    targetMember = createTestUser("targetMember01", "Receiving Member")
    outsider = createTestUser("outsiderCollab01", "Outsider")
    sourceTeam = createActiveTeam(sourceAdmin["id"], "Initiating Team")
    targetTeam = createActiveTeam(targetAdmin["id"], "Receiving Team")
    addTeamMember(sourceTeam["id"], sourceMember["id"], sourceTeam["levels"][1])
    addTeamMember(targetTeam["id"], targetMember["id"], targetTeam["levels"][1])
    return {
        "sourceAdmin": sourceAdmin,
        "sourceMember": sourceMember,
        "targetAdmin": targetAdmin,
        "targetMember": targetMember,
        "outsider": outsider,
        "sourceTeam": sourceTeam,
        "targetTeam": targetTeam,
    }


def createCollaboration(client, world: dict, **overrides) -> dict:
    """调用发起协作接口并断言成功，返回协作数据。"""
    payload = {
        "initiatorTeamId": world["sourceTeam"]["id"],
        "targetTeamId": world["targetTeam"]["id"],
        "initiatorLiaisonUserId": world["sourceMember"]["id"],
        "message": "Let us work on a joint project",
    }
    payload.update(overrides)
    response = client.post(
        "/api/v1/collaborations", json=payload, headers=world["sourceAdmin"]["headers"]
    )
    assert response.status_code == 200, response.text
    return response.json()


def confirmCollaboration(client, world: dict, collaborationId: int, approved: bool = True, **overrides) -> dict:
    """调用确认协作接口并断言成功，返回协作数据。"""
    payload = {"approved": approved, "targetLiaisonUserId": world["targetMember"]["id"]}
    payload.update(overrides)
    response = client.post(
        f"/api/v1/collaborations/{collaborationId}/confirm",
        json=payload,
        headers=world["targetAdmin"]["headers"],
    )
    assert response.status_code == 200, response.text
    return response.json()


def testCreateCollaborationAndDuplicateCheck(client, world):
    """发起协作：pending 状态与单位/对接人字段正确，重复或反向申请 409，非法参数 400/403。"""
    collaboration = createCollaboration(client, world)
    assert collaboration["status"] == "pending"
    assert collaboration["initiatorUnit"]["teamId"] == world["sourceTeam"]["id"]
    assert collaboration["initiatorUnit"]["subTeamId"] is None
    assert collaboration["initiatorUnit"]["unitName"] == "Initiating Team"
    assert collaboration["initiatorLiaisonNickname"] == "Initiating Member"
    assert collaboration["targetLiaisonUserId"] is None
    assert collaboration["createdByName"] == "Initiating Admin"
    assert collaboration["canConfirm"] is False and collaboration["canEnd"] is False
    assert collaboration["myUnitRole"] == "initiator"
    duplicateResponse = client.post(
        "/api/v1/collaborations",
        json={
            "initiatorTeamId": world["sourceTeam"]["id"],
            "targetTeamId": world["targetTeam"]["id"],
            "initiatorLiaisonUserId": world["sourceMember"]["id"],
        },
        headers=world["sourceAdmin"]["headers"],
    )
    assert duplicateResponse.status_code == 409
    reverseResponse = client.post(
        "/api/v1/collaborations",
        json={
            "initiatorTeamId": world["targetTeam"]["id"],
            "targetTeamId": world["sourceTeam"]["id"],
            "initiatorLiaisonUserId": world["targetMember"]["id"],
        },
        headers=world["targetAdmin"]["headers"],
    )
    assert reverseResponse.status_code == 409
    selfResponse = client.post(
        "/api/v1/collaborations",
        json={
            "initiatorTeamId": world["sourceTeam"]["id"],
            "targetTeamId": world["sourceTeam"]["id"],
            "initiatorLiaisonUserId": world["sourceMember"]["id"],
        },
        headers=world["sourceAdmin"]["headers"],
    )
    assert selfResponse.status_code == 400
    invalidLiaisonResponse = client.post(
        "/api/v1/collaborations",
        json={
            "initiatorTeamId": world["sourceTeam"]["id"],
            "targetTeamId": world["targetTeam"]["id"],
            "initiatorLiaisonUserId": world["outsider"]["id"],
        },
        headers=world["sourceAdmin"]["headers"],
    )
    assert invalidLiaisonResponse.status_code == 400
    forbiddenResponse = client.post(
        "/api/v1/collaborations",
        json={
            "initiatorTeamId": world["sourceTeam"]["id"],
            "targetTeamId": world["targetTeam"]["id"],
            "initiatorLiaisonUserId": world["sourceMember"]["id"],
        },
        headers=world["sourceMember"]["headers"],
    )
    assert forbiddenResponse.status_code == 403
    notificationResponse = client.get(
        "/api/v1/notifications", headers=world["targetAdmin"]["headers"]
    )
    notificationTypes = {item["type"] for item in notificationResponse.json()["items"]}
    assert "collaborationApplied" in notificationTypes


def testConfirmCollaborationPermissionsAndNotifications(client, world):
    """确认协作：仅接收单位管理员可确认（403），确认必须指定接收单位成员（400），成功后双方可见。"""
    collaboration = createCollaboration(client, world)
    collaborationId = collaboration["id"]
    initiatorConfirmResponse = client.post(
        f"/api/v1/collaborations/{collaborationId}/confirm",
        json={"approved": True, "targetLiaisonUserId": world["targetMember"]["id"]},
        headers=world["sourceAdmin"]["headers"],
    )
    assert initiatorConfirmResponse.status_code == 403
    outsiderConfirmResponse = client.post(
        f"/api/v1/collaborations/{collaborationId}/confirm",
        json={"approved": True, "targetLiaisonUserId": world["targetMember"]["id"]},
        headers=world["outsider"]["headers"],
    )
    assert outsiderConfirmResponse.status_code == 403
    invalidLiaisonResponse = client.post(
        f"/api/v1/collaborations/{collaborationId}/confirm",
        json={"approved": True, "targetLiaisonUserId": world["sourceMember"]["id"]},
        headers=world["targetAdmin"]["headers"],
    )
    assert invalidLiaisonResponse.status_code == 400
    missingLiaisonResponse = client.post(
        f"/api/v1/collaborations/{collaborationId}/confirm",
        json={"approved": True},
        headers=world["targetAdmin"]["headers"],
    )
    assert missingLiaisonResponse.status_code == 400
    confirmed = confirmCollaboration(client, world, collaborationId)
    assert confirmed["status"] == "active"
    assert confirmed["targetLiaisonUserId"] == world["targetMember"]["id"]
    assert confirmed["targetLiaisonNickname"] == "Receiving Member"
    repeatedResponse = client.post(
        f"/api/v1/collaborations/{collaborationId}/confirm",
        json={"approved": True, "targetLiaisonUserId": world["targetMember"]["id"]},
        headers=world["targetAdmin"]["headers"],
    )
    assert repeatedResponse.status_code == 400
    notificationResponse = client.get(
        "/api/v1/notifications", headers=world["sourceMember"]["headers"]
    )
    notificationTypes = {item["type"] for item in notificationResponse.json()["items"]}
    assert "collaborationConfirmed" in notificationTypes


def testRejectCollaborationAndEndFlow(client, world):
    """拒绝协作：rejected 且记录原因；拒绝后可重新申请，生效后可结束协作（ended）。"""
    collaboration = createCollaboration(client, world)
    collaborationId = collaboration["id"]
    rejected = confirmCollaboration(client, world, collaborationId, approved=False, comment="Not needed for now")
    assert rejected["status"] == "rejected" and rejected["rejectComment"] == "Not needed for now"
    endRejectedResponse = client.post(
        f"/api/v1/collaborations/{collaborationId}/end",
        json={"comment": "Invalid end"},
        headers=world["sourceAdmin"]["headers"],
    )
    assert endRejectedResponse.status_code == 400
    notificationResponse = client.get(
        "/api/v1/notifications", headers=world["sourceMember"]["headers"]
    )
    notificationTypes = {item["type"] for item in notificationResponse.json()["items"]}
    assert "collaborationRejected" in notificationTypes
    secondCollaboration = createCollaboration(client, world, message="Second request")
    confirmed = confirmCollaboration(client, world, secondCollaboration["id"])
    assert confirmed["status"] == "active"
    memberEndResponse = client.post(
        f"/api/v1/collaborations/{secondCollaboration['id']}/end",
        json={"comment": "Not allowed"},
        headers=world["targetMember"]["headers"],
    )
    assert memberEndResponse.status_code == 403
    ended = client.post(
        f"/api/v1/collaborations/{secondCollaboration['id']}/end",
        json={"comment": "Project finished"},
        headers=world["sourceAdmin"]["headers"],
    )
    assert ended.status_code == 200, ended.text
    assert ended.json()["status"] == "ended" and ended.json()["rejectComment"] == "Project finished"
    repeatedEndResponse = client.post(
        f"/api/v1/collaborations/{secondCollaboration['id']}/end",
        json={"comment": "Duplicate end"},
        headers=world["sourceAdmin"]["headers"],
    )
    assert repeatedEndResponse.status_code == 400


def testDirectoryAndUnitCandidates(client, world):
    """协作目录含已认证团队与子团队；单位候选成员区分团队本级与子团队，非成员 403。"""
    sourceTeamId = world["sourceTeam"]["id"]
    subTeamId = createSubTeamDirect(
        sourceTeamId, "Candidate Members Team", world["sourceMember"]["id"], [world["sourceMember"]["id"]]
    )
    directoryResponse = client.get(
        "/api/v1/collaboration/directory", headers=world["outsider"]["headers"]
    )
    assert directoryResponse.status_code == 200
    directoryTeam = next(
        item for item in directoryResponse.json() if item["teamId"] == sourceTeamId
    )
    assert directoryTeam["memberCount"] == 2
    assert directoryTeam["subTeams"][0]["subTeamId"] == subTeamId
    assert directoryTeam["subTeams"][0]["leaderNickname"] == "Initiating Member"
    teamCandidates = client.get(
        "/api/v1/collaborations/units/members",
        params={"teamId": sourceTeamId},
        headers=world["sourceMember"]["headers"],
    )
    assert teamCandidates.status_code == 200
    candidateUserIds = {item["userId"] for item in teamCandidates.json()}
    assert candidateUserIds == {world["sourceAdmin"]["id"], world["sourceMember"]["id"]}
    candidate = teamCandidates.json()[0]
    assert {"userId", "username", "nickname", "avatar", "levelName", "levelOrder", "role"} <= set(candidate)
    subTeamCandidates = client.get(
        "/api/v1/collaborations/units/members",
        params={"teamId": sourceTeamId, "subTeamId": subTeamId},
        headers=world["sourceMember"]["headers"],
    )
    assert [item["userId"] for item in subTeamCandidates.json()] == [world["sourceMember"]["id"]]
    invalidSubTeamResponse = client.get(
        "/api/v1/collaborations/units/members",
        params={"teamId": sourceTeamId, "subTeamId": 99999},
        headers=world["sourceMember"]["headers"],
    )
    assert invalidSubTeamResponse.status_code == 400
    outsiderResponse = client.get(
        "/api/v1/collaborations/units/members",
        params={"teamId": sourceTeamId},
        headers=world["outsider"]["headers"],
    )
    assert outsiderResponse.status_code == 403


def testCollaborationListDetailPermissionsAndSubTeamUnits(client, world):
    """列表按可见范围过滤；详情字段与动作标记正确；同一父团队两个子团队可互相协作。"""
    collaboration = createCollaboration(client, world)
    collaborationId = collaboration["id"]
    sourceListResponse = client.get(
        "/api/v1/collaborations", headers=world["sourceMember"]["headers"]
    )
    assert sourceListResponse.status_code == 200 and sourceListResponse.json()["total"] == 1
    pendingListResponse = client.get(
        "/api/v1/collaborations",
        params={"status": "pending", "teamId": world["sourceTeam"]["id"]},
        headers=world["sourceMember"]["headers"],
    )
    assert pendingListResponse.status_code == 200 and pendingListResponse.json()["total"] == 1
    activeListResponse = client.get(
        "/api/v1/collaborations", params={"status": "active"}, headers=world["sourceMember"]["headers"]
    )
    assert activeListResponse.json()["total"] == 0
    outsiderTeamFilterResponse = client.get(
        "/api/v1/collaborations",
        params={"teamId": world["sourceTeam"]["id"]},
        headers=world["outsider"]["headers"],
    )
    assert outsiderTeamFilterResponse.status_code == 403
    outsiderListResponse = client.get(
        "/api/v1/collaborations", headers=world["outsider"]["headers"]
    )
    assert outsiderListResponse.json()["total"] == 0
    detailResponse = client.get(
        f"/api/v1/collaborations/{collaborationId}", headers=world["targetAdmin"]["headers"]
    )
    assert detailResponse.status_code == 200
    detail = detailResponse.json()
    assert detail["canConfirm"] is True and detail["myUnitRole"] == "target"
    outsiderDetailResponse = client.get(
        f"/api/v1/collaborations/{collaborationId}", headers=world["outsider"]["headers"]
    )
    assert outsiderDetailResponse.status_code == 403
    subTeamOne = createSubTeamDirect(
        world["sourceTeam"]["id"], "Frontend Team", world["sourceMember"]["id"], [world["sourceMember"]["id"]]
    )
    subTeamTwo = createSubTeamDirect(
        world["targetTeam"]["id"], "QA Team", world["targetMember"]["id"], [world["targetMember"]["id"]]
    )
    subTeamCollaboration = createCollaboration(
        client,
        world,
        initiatorSubTeamId=subTeamOne,
        targetSubTeamId=subTeamTwo,
        initiatorLiaisonUserId=world["sourceMember"]["id"],
    )
    assert subTeamCollaboration["status"] == "pending"
    assert subTeamCollaboration["initiatorUnit"]["subTeamName"] == "Frontend Team"
    assert subTeamCollaboration["initiatorUnit"]["unitName"] == "Initiating Team - Frontend Team"
    targetAdminDetail = client.get(
        f"/api/v1/collaborations/{subTeamCollaboration['id']}",
        headers=world["targetAdmin"]["headers"],
    )
    assert targetAdminDetail.status_code == 200
    assert targetAdminDetail.json()["canConfirm"] is True
    selfCollaborationResponse = client.post(
        "/api/v1/collaborations",
        json={
            "initiatorTeamId": world["sourceTeam"]["id"],
            "initiatorSubTeamId": subTeamOne,
            "targetTeamId": world["sourceTeam"]["id"],
            "targetSubTeamId": subTeamOne,
            "initiatorLiaisonUserId": world["sourceMember"]["id"],
        },
        headers=world["sourceAdmin"]["headers"],
    )
    assert selfCollaborationResponse.status_code == 400
    # 同一父团队下的两个子团队允许互相协作（演示数据已依赖该能力）
    thirdSubTeam = createSubTeamDirect(
        world["targetTeam"]["id"], "Acceptance Team", world["targetMember"]["id"], [world["targetMember"]["id"]]
    )
    sameParentResponse = client.post(
        "/api/v1/collaborations",
        json={
            "initiatorTeamId": world["targetTeam"]["id"],
            "initiatorSubTeamId": subTeamTwo,
            "targetTeamId": world["targetTeam"]["id"],
            "targetSubTeamId": thirdSubTeam,
            "initiatorLiaisonUserId": world["targetMember"]["id"],
        },
        headers=world["targetAdmin"]["headers"],
    )
    assert sameParentResponse.status_code == 200, sameParentResponse.text
    assert sameParentResponse.json()["initiatorUnit"]["teamId"] == sameParentResponse.json()["targetUnit"]["teamId"]
