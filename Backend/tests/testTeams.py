"""团队模块接口测试（创建、列表、详情、修改、解散、转让、加入与退出）。

覆盖：创建团队默认级别与管理员、团队列表/详情/修改/解散/转让、free/approval/inviteOnly
加入规则与邀请码、退出团队与待认证团队限制。
"""

from datetime import datetime, timedelta

from tests.helpers import buildAuthHeaders

from TaskManagementBackend.core.database import SessionLocal
from TaskManagementBackend.models import Team


def getUserId(account: dict) -> int:
    """从注册响应中取用户主键。"""
    return account["user"]["user"]["id"]


def getLevelByOrder(teamDetail: dict, levelOrder: int) -> dict:
    """从团队详情中按级别数值取级别对象。"""
    return next(level for level in teamDetail["levels"] if level["levelOrder"] == levelOrder)


def getMemberByUserId(teamDetail: dict, userId: int) -> dict:
    """从团队详情中按用户主键取成员对象。"""
    return next(member for member in teamDetail["members"] if member["userId"] == userId)


class TestTeamLifecycle:
    """团队创建、列表、详情、修改、解散与转让。"""

    def test_createTeamDefaults(self, client, registerUser):
        """创建团队返回 pending 详情：自动 3 个默认级别、创建者为 admin 级别 3。"""
        admin = registerUser(nickname="Team Creator")
        headers = buildAuthHeaders(admin["token"])
        response = client.post(
            "/api/v1/teams",
            json={"name": "Research Team One", "description": "Core research and development", "joinMethod": "inviteOnly"},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        detail = response.json()
        assert detail["status"] == "pending"
        assert detail["createdBy"] == getUserId(admin)
        assert detail["memberCount"] == 1
        assert detail["currentUserRole"] == "admin"
        assert detail["currentUserLevelOrder"] == 3
        assert [level["levelOrder"] for level in detail["levels"]] == [3, 2, 1]
        assert [level["name"] for level in detail["levels"]] == ["Senior Member", "Intermediate Member", "Junior Member"]
        creatorMember = detail["members"][0]
        assert creatorMember["role"] == "admin"
        assert creatorMember["levelOrder"] == 3
        teamList = client.get("/api/v1/teams", headers=headers)
        assert teamList.status_code == 200
        assert isinstance(teamList.json(), list)
        assert teamList.json()[0]["id"] == detail["id"]
        assert "levels" not in teamList.json()[0]
        currentUser = client.get("/api/v1/auth/me", headers=headers)
        teamMemberships = currentUser.json()["teams"]
        assert teamMemberships[0]["teamId"] == detail["id"]
        assert teamMemberships[0]["teamStatus"] == "pending"
        assert teamMemberships[0]["role"] == "admin"

    def test_updateAndDeleteTeam(self, client, registerUser, teamFactory, memberFactory):
        """管理员可修改/解散团队，普通成员被拒绝；解散需 confirmName 完全一致。"""
        admin = registerUser()
        headers = buildAuthHeaders(admin["token"])
        team = teamFactory(admin["token"], name="Team To Rename")
        member = memberFactory(team["id"], levelOrder=1)
        memberHeaders = buildAuthHeaders(member["token"])
        updateResponse = client.put(
            f"/api/v1/teams/{team['id']}",
            json={"name": "Renamed Team", "description": "New description", "joinMethod": "approval"},
            headers=headers,
        )
        assert updateResponse.status_code == 200
        assert updateResponse.json()["name"] == "Renamed Team"
        assert updateResponse.json()["joinMethod"] == "approval"
        memberUpdate = client.put(
            f"/api/v1/teams/{team['id']}", json={"name": "Unauthorized Rename"}, headers=memberHeaders
        )
        assert memberUpdate.status_code == 403
        wrongDelete = client.request(
            "DELETE",
            f"/api/v1/teams/{team['id']}",
            json={"confirmName": "Wrong Team Name"},
            headers=headers,
        )
        assert wrongDelete.status_code == 400
        deleteResponse = client.request(
            "DELETE",
            f"/api/v1/teams/{team['id']}",
            json={"confirmName": "Renamed Team"},
            headers=headers,
        )
        assert deleteResponse.status_code == 200
        assert deleteResponse.json()["message"] == "Team dissolved"
        assert client.get(f"/api/v1/teams/{team['id']}", headers=headers).status_code == 404

    def test_transferAdmin(self, client, registerUser, teamFactory, memberFactory):
        """转让后新管理员拥有管理权限，原管理员降为普通成员。"""
        admin = registerUser()
        adminHeaders = buildAuthHeaders(admin["token"])
        team = teamFactory(admin["token"])
        member = memberFactory(team["id"], levelOrder=1)
        memberHeaders = buildAuthHeaders(member["token"])
        transferResponse = client.post(
            f"/api/v1/teams/{team['id']}/transfer",
            json={"newAdminUserId": getUserId(member)},
            headers=adminHeaders,
        )
        assert transferResponse.status_code == 200
        assert transferResponse.json()["currentUserRole"] == "member"
        newAdminView = client.get(f"/api/v1/teams/{team['id']}", headers=memberHeaders)
        assert newAdminView.json()["currentUserRole"] == "admin"
        oldAdminUpdate = client.put(
            f"/api/v1/teams/{team['id']}", json={"name": "Renamed by Former Admin"}, headers=adminHeaders
        )
        assert oldAdminUpdate.status_code == 403


class TestJoinAndLeave:
    """三种加入方式、邀请码、退出团队与待认证团队限制。"""

    def test_joinFreeTeamAndDuplicate(self, client, registerUser, teamFactory):
        """free 团队可直接加入，重复加入返回 409。"""
        admin = registerUser()
        team = teamFactory(admin["token"], joinMethod="free")
        joiner = registerUser()
        joinerHeaders = buildAuthHeaders(joiner["token"])
        joinResponse = client.post(
            "/api/v1/teams/join", json={"teamId": team["id"]}, headers=joinerHeaders
        )
        assert joinResponse.status_code == 200
        assert joinResponse.json()["status"] == "joined"
        duplicate = client.post(
            "/api/v1/teams/join", json={"teamId": team["id"]}, headers=joinerHeaders
        )
        assert duplicate.status_code == 409
        memberList = client.get(
            f"/api/v1/teams/{team['id']}/members", headers=joinerHeaders
        )
        assert len(memberList.json()) == 2
        memberView = client.get(f"/api/v1/teams/{team['id']}", headers=joinerHeaders)
        assert memberView.json()["inviteCode"] is None
        assert memberView.json()["inviteExpiresAt"] is None

    def test_joinApprovalFlow(self, client, registerUser, teamFactory):
        """approval 团队生成入团申请，管理员通过后成为成员，拒绝则不加入。"""
        admin = registerUser()
        adminHeaders = buildAuthHeaders(admin["token"])
        team = teamFactory(admin["token"], joinMethod="approval")
        applicant = registerUser()
        applicantHeaders = buildAuthHeaders(applicant["token"])
        joinResponse = client.post(
            "/api/v1/teams/join",
            json={"teamId": team["id"], "message": "I would like to join the team"},
            headers=applicantHeaders,
        )
        assert joinResponse.status_code == 200
        assert joinResponse.json()["status"] == "pending"
        assert joinResponse.json()["message"] == "Join request submitted. Please wait for admin review."
        duplicate = client.post(
            "/api/v1/teams/join", json={"teamId": team["id"]}, headers=applicantHeaders
        )
        assert duplicate.status_code == 409
        requestList = client.get(
            f"/api/v1/teams/{team['id']}/join-requests", headers=adminHeaders
        )
        assert requestList.status_code == 200
        assert len(requestList.json()) == 1
        joinRequest = requestList.json()[0]
        assert joinRequest["userId"] == getUserId(applicant)
        assert joinRequest["message"] == "I would like to join the team"
        approveResponse = client.put(
            f"/api/v1/teams/{team['id']}/join-requests/{joinRequest['id']}",
            json={"action": "approve"},
            headers=adminHeaders,
        )
        assert approveResponse.status_code == 200
        detail = client.get(f"/api/v1/teams/{team['id']}", headers=adminHeaders).json()
        assert getMemberByUserId(detail, getUserId(applicant)) is not None
        rejectedApplicant = registerUser()
        rejectedHeaders = buildAuthHeaders(rejectedApplicant["token"])
        client.post("/api/v1/teams/join", json={"teamId": team["id"]}, headers=rejectedHeaders)
        requestList = client.get(
            f"/api/v1/teams/{team['id']}/join-requests", headers=adminHeaders
        )
        rejectResponse = client.put(
            f"/api/v1/teams/{team['id']}/join-requests/{requestList.json()[0]['id']}",
            json={"action": "reject"},
            headers=adminHeaders,
        )
        assert rejectResponse.status_code == 200
        detail = client.get(f"/api/v1/teams/{team['id']}", headers=adminHeaders).json()
        assert all(
            member["userId"] != getUserId(rejectedApplicant) for member in detail["members"]
        )

    def test_inviteOnlyAndInviteCodeRules(self, client, registerUser, teamFactory):
        """inviteOnly 团队必须邀请码；邀请码校验无效、过期与使用次数上限。"""
        admin = registerUser()
        adminHeaders = buildAuthHeaders(admin["token"])
        team = teamFactory(admin["token"], joinMethod="inviteOnly")
        outsider = registerUser()
        outsiderHeaders = buildAuthHeaders(outsider["token"])
        forbiddenJoin = client.post(
            "/api/v1/teams/join", json={"teamId": team["id"]}, headers=outsiderHeaders
        )
        assert forbiddenJoin.status_code == 403
        invalidCode = client.post(
            "/api/v1/teams/join", json={"inviteCode": "NOTVALID99"}, headers=outsiderHeaders
        )
        assert invalidCode.status_code == 404
        inviteResponse = client.post(
            f"/api/v1/teams/{team['id']}/invite-code",
            json={"expiresInHours": 24, "maxUses": 1},
            headers=adminHeaders,
        )
        assert inviteResponse.status_code == 200
        inviteCode = inviteResponse.json()["inviteCode"]
        assert inviteCode
        joinByCode = client.post(
            "/api/v1/teams/join", json={"inviteCode": inviteCode}, headers=outsiderHeaders
        )
        assert joinByCode.status_code == 200
        assert joinByCode.json()["status"] == "joined"
        secondOutsider = registerUser()
        usedUpResponse = client.post(
            "/api/v1/teams/join",
            json={"inviteCode": inviteCode},
            headers=buildAuthHeaders(secondOutsider["token"]),
        )
        assert usedUpResponse.status_code == 400
        client.post(
            f"/api/v1/teams/{team['id']}/invite-code",
            json={"expiresInHours": 24},
            headers=adminHeaders,
        )
        expiredCode = client.get(f"/api/v1/teams/{team['id']}", headers=adminHeaders).json()[
            "inviteCode"
        ]
        databaseSession = SessionLocal()
        try:
            teamEntity = databaseSession.get(Team, team["id"])
            teamEntity.inviteExpiresAt = datetime.now() - timedelta(hours=1)
            databaseSession.commit()
        finally:
            databaseSession.close()
        expiredResponse = client.post(
            "/api/v1/teams/join",
            json={"inviteCode": expiredCode},
            headers=buildAuthHeaders(registerUser()["token"]),
        )
        assert expiredResponse.status_code == 400

    def test_pendingTeamCannotBeJoined(self, client, registerUser):
        """待认证团队不可被其他用户加入（返回 TEAM_PENDING）。"""
        admin = registerUser()
        createResponse = client.post(
            "/api/v1/teams",
            json={"name": "Pending Team", "joinMethod": "free"},
            headers=buildAuthHeaders(admin["token"]),
        )
        teamId = createResponse.json()["id"]
        outsider = registerUser()
        joinResponse = client.post(
            "/api/v1/teams/join",
            json={"teamId": teamId},
            headers=buildAuthHeaders(outsider["token"]),
        )
        assert joinResponse.status_code == 403
        assert joinResponse.json()["code"] == "TEAM_PENDING"

    def test_leaveTeam(self, client, registerUser, teamFactory):
        """普通成员可退出团队，团队管理员必须先转让。"""
        admin = registerUser()
        team = teamFactory(admin["token"], joinMethod="free")
        memberAccount = registerUser()
        memberHeaders = buildAuthHeaders(memberAccount["token"])
        client.post("/api/v1/teams/join", json={"teamId": team["id"]}, headers=memberHeaders)
        leaveResponse = client.post(
            f"/api/v1/teams/{team['id']}/leave", headers=memberHeaders
        )
        assert leaveResponse.status_code == 200
        assert leaveResponse.json()["message"] == "Left the team"
        assert client.get(f"/api/v1/teams/{team['id']}", headers=memberHeaders).status_code == 403
        adminLeave = client.post(
            f"/api/v1/teams/{team['id']}/leave", headers=buildAuthHeaders(admin["token"])
        )
        assert adminLeave.status_code == 400
