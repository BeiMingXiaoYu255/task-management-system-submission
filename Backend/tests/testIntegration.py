"""跨模块接口集成测试（Lead 维护）。

目标：用真实 HTTP 调用串联「团队认证 → 成员加入 → 任务发布 → 接受/提交 → 审核归档」等完整链路，
验证前后端契约（docs/development/apiContract.md）与前端类型文件保持一致。
说明：测试使用 conftest.py 提供的独立测试库与内置超级用户。
"""

from tests.helpers import buildAuthHeaders


def createTeamForAdmin(client, adminToken: str, joinMethod: str = "inviteOnly") -> dict:
    """创建团队并返回响应数据（创建后仍为 pending，需要认证或激活夹具处理）。"""
    response = client.post(
        "/api/v1/teams",
        json={"name": "Integration Test Team", "description": "For cross-module integration testing", "joinMethod": joinMethod},
        headers=buildAuthHeaders(adminToken),
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def certifyTeam(client, superAdminHeaders: dict, teamId: int) -> None:
    """超级用户在管理后台通过团队认证。"""
    response = client.put(
        "/api/v1/admin/teams/" + str(teamId) + "/certification",
        json={"approved": True},
        headers=superAdminHeaders,
    )
    assert response.status_code == 200, response.text


def addTeamMember(client, teamFactory, memberFactory, adminToken: str, levelOrder: int = 1):
    """创建团队并添加一个普通成员，返回 (团队, 成员账号)。"""
    teamData = teamFactory(adminToken)
    memberAccount = memberFactory(teamData["id"], levelOrder=levelOrder)
    return teamData, memberAccount


class TestCompleteTaskLifecycle:
    """任务闭环：发布 → 提交 → 驳回 → 重新提交 → 审核通过归档。"""

    def test_mandatory_task_lifecycle(self, client, teamFactory, memberFactory):
        """必须接受任务从发布到归档的完整状态流转。"""
        adminAccount = client.post(
            "/api/v1/auth/register",
            json={"username": "integrationAdmin", "password": "Password123", "nickname": "Integration Admin"},
        ).json()
        adminToken = adminAccount["token"]
        teamData, memberAccount = addTeamMember(client, teamFactory, memberFactory, adminToken)
        teamId = teamData["id"]
        memberHeaders = buildAuthHeaders(memberAccount["token"])
        adminHeaders = buildAuthHeaders(adminToken)

        # 发布必须接受任务（指定成员）
        createResponse = client.post(
            "/api/v1/teams/" + str(teamId) + "/tasks",
            json={
                "title": "Integration test: complete task lifecycle",
                "description": "Verify task state machine",
                "priority": "high",
                "assignmentMode": "specific",
                "acceptanceMode": "mandatory",
                "targetUserIds": [memberAccount["user"]["user"]["id"]],
            },
            headers=adminHeaders,
        )
        assert createResponse.status_code in (200, 201), createResponse.text
        taskData = createResponse.json()
        taskId = taskData["id"]
        assert taskData["status"] == "inProgress"
        assert taskData["assignments"][0]["status"] == "inProgress"

        # 待办列表可见
        todoResponse = client.get("/api/v1/todos", headers=memberHeaders)
        assert todoResponse.status_code == 200, todoResponse.text
        todoItems = todoResponse.json()["items"]
        assert any(item["taskId"] == taskId for item in todoItems)

        # 执行人提交完成 → 待审核
        submitResponse = client.post("/api/v1/tasks/" + str(taskId) + "/submit", headers=memberHeaders)
        assert submitResponse.status_code == 200, submitResponse.text
        assert submitResponse.json()["status"] == "pendingReview"

        # 发布者驳回 → 重新进行中并记录意见
        rejectResponse = client.post(
            "/api/v1/tasks/" + str(taskId) + "/review",
            json={
                "assignmentUserId": memberAccount["user"]["user"]["id"],
                "approved": False,
                "comment": "Please add test instructions",
            },
            headers=adminHeaders,
        )
        assert rejectResponse.status_code == 200, rejectResponse.text
        rejectedTask = rejectResponse.json()
        assert rejectedTask["status"] == "inProgress"
        memberAssignment = next(
            assignment
            for assignment in rejectedTask["assignments"]
            if assignment["userId"] == memberAccount["user"]["user"]["id"]
        )
        assert memberAssignment["status"] == "inProgress"
        assert memberAssignment["reviewComment"] == "Please add test instructions"

        # 再次提交并审核通过 → 归档
        client.post("/api/v1/tasks/" + str(taskId) + "/submit", headers=memberHeaders)
        approveResponse = client.post(
            "/api/v1/tasks/" + str(taskId) + "/review",
            json={
                "assignmentUserId": memberAccount["user"]["user"]["id"],
                "approved": True,
                "comment": "Approved",
            },
            headers=adminHeaders,
        )
        assert approveResponse.status_code == 200, approveResponse.text
        assert approveResponse.json()["status"] == "archived"
        assert len(approveResponse.json()["reviews"]) >= 2

    def test_optional_task_accept_and_decline(self, client, teamFactory, memberFactory):
        """选择性任务：接受后进入进行中；另一任务拒绝后从待办移除。"""
        adminAccount = client.post(
            "/api/v1/auth/register",
            json={"username": "optionalAdmin", "password": "Password123", "nickname": "Optional Task Admin"},
        ).json()
        adminToken = adminAccount["token"]
        teamData, memberAccount = addTeamMember(client, teamFactory, memberFactory, adminToken)
        teamId = teamData["id"]
        memberHeaders = buildAuthHeaders(memberAccount["token"])
        adminHeaders = buildAuthHeaders(adminToken)

        def createOptionalTask(title: str) -> int:
            """创建选择性接受任务并返回任务 ID。"""
            response = client.post(
                "/api/v1/teams/" + str(teamId) + "/tasks",
                json={
                    "title": title,
                    "priority": "medium",
                    "assignmentMode": "specific",
                    "acceptanceMode": "optional",
                    "targetUserIds": [memberAccount["user"]["user"]["id"]],
                },
                headers=adminHeaders,
            )
            assert response.status_code in (200, 201), response.text
            return response.json()["id"]

        acceptTaskId = createOptionalTask("Accepted Task")
        declineTaskId = createOptionalTask("Declined Task")

        acceptResponse = client.post(
            "/api/v1/tasks/" + str(acceptTaskId) + "/acceptance", headers=memberHeaders
        )
        assert acceptResponse.status_code == 200, acceptResponse.text
        assert acceptResponse.json()["assignments"][0]["status"] == "inProgress"

        declineResponse = client.post(
            "/api/v1/tasks/" + str(declineTaskId) + "/decline", headers=memberHeaders
        )
        assert declineResponse.status_code == 200, declineResponse.text
        assert declineResponse.json()["status"] == "cancelled"

        todoItems = client.get("/api/v1/todos", headers=memberHeaders).json()["items"]
        todoTaskIds = {item["taskId"] for item in todoItems}
        assert acceptTaskId in todoTaskIds
        assert declineTaskId not in todoTaskIds


class TestTeamPermissions:
    """团队权限与数据隔离测试。"""

    def test_outsider_cannot_access_team(self, client, teamFactory, memberFactory):
        """非团队成员访问团队、任务、审核接口均返回 403。"""
        adminAccount = client.post(
            "/api/v1/auth/register",
            json={"username": "isolationOwner", "password": "Password123", "nickname": "Team Admin"},
        ).json()
        teamData, _ = addTeamMember(client, teamFactory, memberFactory, adminAccount["token"])
        outsiderAccount = client.post(
            "/api/v1/auth/register",
            json={"username": "isolationOutsider", "password": "Password123", "nickname": "Outsider"},
        ).json()
        outsiderHeaders = buildAuthHeaders(outsiderAccount["token"])
        teamId = teamData["id"]
        assert client.get("/api/v1/teams/" + str(teamId), headers=outsiderHeaders).status_code == 403
        assert (
            client.get("/api/v1/teams/" + str(teamId) + "/tasks", headers=outsiderHeaders).status_code
            == 403
        )
        assert (
            client.post("/api/v1/teams/" + str(teamId) + "/invite-code", json={}, headers=outsiderHeaders).status_code
            == 403
        )

    def test_normal_user_cannot_access_admin(self, client, registerUser):
        """普通用户访问管理后台接口返回 403。"""
        account = registerUser()
        headers = buildAuthHeaders(account["token"])
        assert client.get("/api/v1/admin/users", headers=headers).status_code == 403
        assert client.get("/api/v1/admin/overview", headers=headers).status_code == 403

    def test_pending_team_cannot_create_task(self, client, registerUser):
        """未认证团队不能发布任务。"""
        account = registerUser()
        headers = buildAuthHeaders(account["token"])
        pendingResponse = client.post(
            "/api/v1/teams",
            json={"name": "Pending Certification Team", "joinMethod": "inviteOnly"},
            headers=headers,
        )
        assert pendingResponse.status_code in (200, 201), pendingResponse.text
        teamId = pendingResponse.json()["id"]
        taskResponse = client.post(
            "/api/v1/teams/" + str(teamId) + "/tasks",
            json={
                "title": "Uncertified team task",
                "priority": "low",
                "assignmentMode": "specific",
                "acceptanceMode": "mandatory",
                "targetUserIds": [account["user"]["user"]["id"]],
            },
            headers=headers,
        )
        assert taskResponse.status_code == 403, taskResponse.text


class TestJoinAndCertification:
    """加入团队与团队认证流程测试。"""

    def test_invite_code_join(self, client, teamFactory):
        """管理员生成邀请码后，新用户通过邀请码加入团队。"""
        adminAccount = client.post(
            "/api/v1/auth/register",
            json={"username": "inviteAdmin", "password": "Password123", "nickname": "Invite Admin"},
        ).json()
        teamData = createTeamForAdmin(client, adminAccount["token"])
        teamId = teamData["id"]
        activateResponse = client.get("/api/v1/teams/" + str(teamId), headers=buildAuthHeaders(adminAccount["token"]))
        assert activateResponse.status_code == 200
        # 通过超级用户认证团队
        superLogin = client.post(
            "/api/v1/auth/login",
            json={"username": "superAdmin", "password": "SuperAdmin@123"},
        )
        superHeaders = buildAuthHeaders(superLogin.json()["token"])
        certifyTeam(client, superHeaders, teamId)
        inviteResponse = client.post(
            "/api/v1/teams/" + str(teamId) + "/invite-code",
            json={"expiresInHours": 24, "maxUses": 5},
            headers=buildAuthHeaders(adminAccount["token"]),
        )
        assert inviteResponse.status_code == 200, inviteResponse.text
        inviteCode = inviteResponse.json()["inviteCode"]
        assert inviteCode
        newUser = client.post(
            "/api/v1/auth/register",
            json={"username": "invitedUser", "password": "Password123", "nickname": "Invited User"},
        ).json()
        joinResponse = client.post(
            "/api/v1/teams/join",
            json={"inviteCode": inviteCode},
            headers=buildAuthHeaders(newUser["token"]),
        )
        assert joinResponse.status_code == 200, joinResponse.text
        assert joinResponse.json()["status"] == "joined"
        members = client.get(
            "/api/v1/teams/" + str(teamId) + "/members",
            headers=buildAuthHeaders(adminAccount["token"]),
        ).json()
        assert any(member["userId"] == newUser["user"]["user"]["id"] for member in members)

    def test_approval_join_and_handle(self, client, teamFactory):
        """申请式加入：用户提交申请，管理员审批通过。"""
        adminAccount = client.post(
            "/api/v1/auth/register",
            json={"username": "approvalAdmin", "password": "Password123", "nickname": "Approval Admin"},
        ).json()
        teamData = createTeamForAdmin(client, adminAccount["token"], joinMethod="approval")
        teamId = teamData["id"]
        superLogin = client.post(
            "/api/v1/auth/login",
            json={"username": "superAdmin", "password": "SuperAdmin@123"},
        )
        superHeaders = buildAuthHeaders(superLogin.json()["token"])
        certifyTeam(client, superHeaders, teamId)
        applicant = client.post(
            "/api/v1/auth/register",
            json={"username": "applicantUser", "password": "Password123", "nickname": "Applicant"},
        ).json()
        joinResponse = client.post(
            "/api/v1/teams/join",
            json={"teamId": teamId, "message": "I would like to join the team"},
            headers=buildAuthHeaders(applicant["token"]),
        )
        assert joinResponse.status_code == 200, joinResponse.text
        assert joinResponse.json()["status"] == "pending"
        requestList = client.get(
            "/api/v1/teams/" + str(teamId) + "/join-requests",
            headers=buildAuthHeaders(adminAccount["token"]),
        ).json()
        pendingRequest = next(item for item in requestList if item["userId"] == applicant["user"]["user"]["id"])
        approveResponse = client.put(
            "/api/v1/teams/" + str(teamId) + "/join-requests/" + str(pendingRequest["id"]),
            json={"action": "approve"},
            headers=buildAuthHeaders(adminAccount["token"]),
        )
        assert approveResponse.status_code == 200, approveResponse.text


class TestSettingsAndAdmin:
    """设置、AI 推荐与管理后台直管测试。"""

    def test_settings_and_password_change(self, client, registerUser):
        """设置读写、修改密码后旧 token 失效。"""
        account = registerUser()
        headers = buildAuthHeaders(account["token"])
        settingsResponse = client.get("/api/v1/settings", headers=headers)
        assert settingsResponse.status_code == 200, settingsResponse.text
        updateResponse = client.put(
            "/api/v1/settings",
            json={"theme": "dark", "fontSize": "large", "fontFamily": "serif"},
            headers=headers,
        )
        assert updateResponse.status_code == 200, updateResponse.text
        assert updateResponse.json()["theme"] == "dark"
        changeResponse = client.put(
            "/api/v1/settings/password",
            json={"oldPassword": "Password123", "newPassword": "NewPassword456"},
            headers=headers,
        )
        assert changeResponse.status_code == 200, changeResponse.text
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
        loginResponse = client.post(
            "/api/v1/auth/login",
            json={"username": account["user"]["user"]["username"], "password": "NewPassword456"},
        )
        assert loginResponse.status_code == 200, loginResponse.text

    def test_admin_global_role_and_database_operation(self, client, registerUser, superAdminHeaders):
        """超级用户设置全局管理员；管理员可浏览数据库但禁止 DDL。"""
        account = registerUser()
        targetHeaders = buildAuthHeaders(account["token"])
        assert client.get("/api/v1/admin/overview", headers=targetHeaders).status_code == 403
        promoteResponse = client.put(
            "/api/v1/admin/users/" + str(account["user"]["user"]["id"]) + "/global-role",
            json={"globalRole": "globalAdmin"},
            headers=superAdminHeaders,
        )
        assert promoteResponse.status_code == 200, promoteResponse.text
        assert client.get("/api/v1/admin/overview", headers=targetHeaders).status_code == 200
        tablesResponse = client.get("/api/v1/admin/database/tables", headers=targetHeaders)
        assert tablesResponse.status_code == 200, tablesResponse.text
        tableNames = {table["tableName"] for table in tablesResponse.json()}
        assert "users" in tableNames
        forbiddenSql = client.post(
            "/api/v1/admin/database/execute",
            json={"sql": "DROP TABLE users", "confirm": True},
            headers=targetHeaders,
        )
        assert forbiddenSql.status_code in (400, 403), forbiddenSql.text
        selectSql = client.post(
            "/api/v1/admin/database/execute",
            json={"sql": "SELECT id, username FROM users LIMIT 5", "confirm": True},
            headers=targetHeaders,
        )
        assert selectSql.status_code == 200, selectSql.text
        assert isinstance(selectSql.json()["rows"], list)

    def test_ai_recommendation(self, client, teamFactory, memberFactory):
        """AI 推荐接口返回候选成员与中文理由。"""
        adminAccount = client.post(
            "/api/v1/auth/register",
            json={"username": "aiAdmin", "password": "Password123", "nickname": "AI Admin"},
        ).json()
        adminToken = adminAccount["token"]
        teamData, memberAccount = addTeamMember(client, teamFactory, memberFactory, adminToken)
        teamId = teamData["id"]
        recommendationResponse = client.post(
            "/api/v1/teams/" + str(teamId) + "/ai/recommend-assignees",
            json={
                "title": "Backend API performance optimization",
                "description": "Optimize FastAPI endpoint response time",
                "priority": "high",
            },
            headers=buildAuthHeaders(adminToken),
        )
        assert recommendationResponse.status_code == 200, recommendationResponse.text
        recommendationData = recommendationResponse.json()
        assert "candidates" in recommendationData
        assert isinstance(recommendationData["candidates"], list)
        assert all(
            "score" in item and "reasons" in item for item in recommendationData["candidates"]
        )

    def test_system_health_and_network(self, client, registerUser):
        """健康检查与局域网信息接口。"""
        healthResponse = client.get("/api/v1/health")
        assert healthResponse.status_code == 200
        assert healthResponse.json()["status"] == "ok"
        headers = buildAuthHeaders(registerUser()["token"])
        networkResponse = client.get("/api/v1/system/network", headers=headers)
        assert networkResponse.status_code == 200, networkResponse.text
        assert isinstance(networkResponse.json()["lanUrls"], list)