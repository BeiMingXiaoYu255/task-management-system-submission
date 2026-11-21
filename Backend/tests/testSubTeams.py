"""子团队模块接口测试：CRUD、权限、成员维护、任务归属与子团队任务视图。

测试数据通过数据库直接构造（用户/团队/级别/成员/token），不依赖账号与团队模块接口。
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
            description="Sub-team module test team",
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


def addTeamMember(teamId: int, userId: int, levelId: int, role: TeamRole = TeamRole.MEMBER) -> None:
    """直接写入团队成员关系。"""
    databaseSession = SessionLocal()
    try:
        databaseSession.add(TeamMember(teamId=teamId, userId=userId, role=role, levelId=levelId))
        databaseSession.commit()
    finally:
        databaseSession.close()


def createSubTeamDirect(teamId: int, name: str, leaderUserId: int, memberUserIds: list[int]) -> int:
    """直接写入子团队与成员关系，返回子团队主键。"""
    databaseSession = SessionLocal()
    try:
        subTeam = SubTeam(
            parentTeamId=teamId, name=name, description="Directly created sub-team", leaderUserId=leaderUserId
        )
        databaseSession.add(subTeam)
        databaseSession.flush()
        for userId in set(memberUserIds):
            databaseSession.add(SubTeamMember(subTeamId=subTeam.id, userId=userId))
        databaseSession.commit()
        return subTeam.id
    finally:
        databaseSession.close()


@pytest.fixture()
def workspace() -> dict:
    """子团队测试工作区：团队管理员、子负责人、普通成员与外部用户。"""
    owner = createTestUser("ownerSubTeam01", "Team Admin")
    leader = createTestUser("leaderSubTeam01", "Sub-team Lead")
    member = createTestUser("memberSubTeam01", "Member")
    outsider = createTestUser("outsiderSubTeam01", "Outsider")
    team = createActiveTeam(owner["id"], "Sub-team Test Team")
    addTeamMember(team["id"], leader["id"], team["levels"][2])
    addTeamMember(team["id"], member["id"], team["levels"][1])
    return {"owner": owner, "leader": leader, "member": member, "outsider": outsider, "team": team}


def testCreateSubTeamAndListAsMember(client, workspace):
    """创建子团队：管理员可创建，负责人自动入成员，成员列表含级别信息且角色正确。"""
    teamId = workspace["team"]["id"]
    response = client.post(
        f"/api/v1/teams/{teamId}/sub-teams",
        json={
            "name": "Frontend Team",
            "description": "Responsible for frontend pages",
            "leaderUserId": workspace["leader"]["id"],
            "memberUserIds": [workspace["member"]["id"]],
        },
        headers=workspace["owner"]["headers"],
    )
    assert response.status_code == 200, response.text
    subTeam = response.json()
    assert subTeam["parentTeamId"] == teamId
    assert subTeam["leaderNickname"] == "Sub-team Lead"
    assert subTeam["memberCount"] == 2
    assert subTeam["myRole"] == "admin"
    leaderMember = next(item for item in subTeam["members"] if item["userId"] == workspace["leader"]["id"])
    assert leaderMember["isLeader"] is True
    assert leaderMember["levelOrder"] == 2 and leaderMember["levelName"] == "Intermediate Member"
    memberList = client.get(
        f"/api/v1/teams/{teamId}/sub-teams", headers=workspace["member"]["headers"]
    )
    assert memberList.status_code == 200
    assert memberList.json()[0]["myRole"] == "member"
    bystander = createTestUser("bystanderSubTeam01", "Bystander")
    addTeamMember(teamId, bystander["id"], workspace["team"]["levels"][1])
    bystanderList = client.get(
        f"/api/v1/teams/{teamId}/sub-teams", headers=bystander["headers"]
    )
    assert bystanderList.status_code == 200 and bystanderList.json()[0]["myRole"] is None
    outsiderResponse = client.get(
        f"/api/v1/teams/{teamId}/sub-teams", headers=workspace["outsider"]["headers"]
    )
    assert outsiderResponse.status_code == 403


def testSubTeamCreatePermissionsAndValidation(client, workspace):
    """创建权限与校验：非管理员 403、负责人/成员非父团队成员 400、重名 409。"""
    teamId = workspace["team"]["id"]
    nonAdminResponse = client.post(
        f"/api/v1/teams/{teamId}/sub-teams",
        json={"name": "Unauthorized Team", "leaderUserId": workspace["leader"]["id"]},
        headers=workspace["member"]["headers"],
    )
    assert nonAdminResponse.status_code == 403
    invalidLeaderResponse = client.post(
        f"/api/v1/teams/{teamId}/sub-teams",
        json={"name": "Invalid Team", "leaderUserId": workspace["outsider"]["id"]},
        headers=workspace["owner"]["headers"],
    )
    assert invalidLeaderResponse.status_code == 400
    invalidMemberResponse = client.post(
        f"/api/v1/teams/{teamId}/sub-teams",
        json={"name": "Invalid Members Team", "memberUserIds": [workspace["outsider"]["id"]]},
        headers=workspace["owner"]["headers"],
    )
    assert invalidMemberResponse.status_code == 400
    createResponse = client.post(
        f"/api/v1/teams/{teamId}/sub-teams",
        json={"name": "Duplicate Team", "leaderUserId": workspace["leader"]["id"]},
        headers=workspace["owner"]["headers"],
    )
    assert createResponse.status_code == 200, createResponse.text
    duplicateResponse = client.post(
        f"/api/v1/teams/{teamId}/sub-teams",
        json={"name": "Duplicate Team", "leaderUserId": workspace["leader"]["id"]},
        headers=workspace["owner"]["headers"],
    )
    assert duplicateResponse.status_code == 409


def testSubTeamUpdatePermissions(client, workspace):
    """修改权限：子负责人可改名称/简介，不可换负责人；管理员可换负责人；普通成员 403。"""
    teamId = workspace["team"]["id"]
    subTeamId = createSubTeamDirect(
        teamId, "Team To Update", workspace["leader"]["id"], [workspace["leader"]["id"]]
    )
    memberUpdateResponse = client.put(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}",
        json={"description": "Unauthorized Update"},
        headers=workspace["member"]["headers"],
    )
    assert memberUpdateResponse.status_code == 403
    leaderResponse = client.put(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}",
        json={"name": "Updated Team", "description": "New description"},
        headers=workspace["leader"]["headers"],
    )
    assert leaderResponse.status_code == 200, leaderResponse.text
    assert leaderResponse.json()["name"] == "Updated Team"
    leaderChangeResponse = client.put(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}",
        json={"leaderUserId": workspace["member"]["id"]},
        headers=workspace["leader"]["headers"],
    )
    assert leaderChangeResponse.status_code == 403
    adminChangeResponse = client.put(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}",
        json={"leaderUserId": workspace["member"]["id"]},
        headers=workspace["owner"]["headers"],
    )
    assert adminChangeResponse.status_code == 200, adminChangeResponse.text
    assert adminChangeResponse.json()["leaderUserId"] == workspace["member"]["id"]


def testSetSubTeamMembersCoverMode(client, workspace):
    """覆盖式设置成员：负责人自动保留为成员，非父团队成员返回 400，普通成员返回 403。"""
    teamId = workspace["team"]["id"]
    subTeamId = createSubTeamDirect(
        teamId,
        "Member Management Team",
        workspace["leader"]["id"],
        [workspace["leader"]["id"], workspace["member"]["id"]],
    )
    response = client.put(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}/members",
        json={"userIds": [workspace["member"]["id"]]},
        headers=workspace["leader"]["headers"],
    )
    assert response.status_code == 200, response.text
    memberUserIds = {item["userId"] for item in response.json()["members"]}
    assert memberUserIds == {workspace["leader"]["id"], workspace["member"]["id"]}
    forbiddenResponse = client.put(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}/members",
        json={"userIds": [workspace["member"]["id"]]},
        headers=workspace["member"]["headers"],
    )
    assert forbiddenResponse.status_code == 403
    invalidResponse = client.put(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}/members",
        json={"userIds": [workspace["outsider"]["id"]]},
        headers=workspace["owner"]["headers"],
    )
    assert invalidResponse.status_code == 400


def testDeleteSubTeamClearsTaskSubTeamId(client, workspace):
    """删除子团队：普通成员 403，管理员删除后其任务 subTeamId 置空。"""
    teamId = workspace["team"]["id"]
    subTeamId = createSubTeamDirect(
        teamId, "Team To Delete", workspace["leader"]["id"], [workspace["leader"]["id"]]
    )
    taskResponse = client.post(
        f"/api/v1/teams/{teamId}/tasks",
        json={
            "title": "Sub-team Task",
            "priority": "medium",
            "assignmentMode": "specific",
            "acceptanceMode": "mandatory",
            "targetUserIds": [workspace["member"]["id"]],
            "subTeamId": subTeamId,
        },
        headers=workspace["owner"]["headers"],
    )
    assert taskResponse.status_code == 200, taskResponse.text
    taskId = taskResponse.json()["id"]
    assert taskResponse.json()["subTeamId"] == subTeamId
    forbiddenResponse = client.delete(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}",
        headers=workspace["member"]["headers"],
    )
    assert forbiddenResponse.status_code == 403
    deleteResponse = client.delete(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}",
        headers=workspace["owner"]["headers"],
    )
    assert deleteResponse.status_code == 200, deleteResponse.text
    detailResponse = client.get(f"/api/v1/tasks/{taskId}", headers=workspace["owner"]["headers"])
    assert detailResponse.status_code == 200
    assert detailResponse.json()["subTeamId"] is None


def testSubTeamTasksVisibility(client, workspace):
    """子团队任务分页：子团队成员与团队管理员可查看，其他团队成员 403。"""
    teamId = workspace["team"]["id"]
    subTeamId = createSubTeamDirect(
        teamId,
        "Task Visibility Team",
        workspace["leader"]["id"],
        [workspace["leader"]["id"]],
    )
    taskResponse = client.post(
        f"/api/v1/teams/{teamId}/tasks",
        json={
            "title": "Internal Sub-team Task",
            "priority": "high",
            "assignmentMode": "specific",
            "acceptanceMode": "mandatory",
            "targetUserIds": [workspace["member"]["id"]],
            "subTeamId": subTeamId,
        },
        headers=workspace["owner"]["headers"],
    )
    assert taskResponse.status_code == 200, taskResponse.text
    client.post(
        f"/api/v1/teams/{teamId}/tasks",
        json={
            "title": "Team-level Task",
            "priority": "low",
            "assignmentMode": "specific",
            "acceptanceMode": "mandatory",
            "targetUserIds": [workspace["member"]["id"]],
        },
        headers=workspace["owner"]["headers"],
    )
    leaderResponse = client.get(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}/tasks",
        headers=workspace["leader"]["headers"],
    )
    assert leaderResponse.status_code == 200, leaderResponse.text
    items = leaderResponse.json()["items"]
    assert len(items) == 1 and items[0]["subTeamId"] == subTeamId
    memberResponse = client.get(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}/tasks",
        headers=workspace["member"]["headers"],
    )
    assert memberResponse.status_code == 403
    adminResponse = client.get(
        f"/api/v1/teams/{teamId}/sub-teams/{subTeamId}/tasks",
        headers=workspace["owner"]["headers"],
    )
    assert adminResponse.status_code == 200 and adminResponse.json()["total"] == 1
