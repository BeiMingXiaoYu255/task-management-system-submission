"""管理后台模块接口测试。

覆盖：管理员鉴权、用户分页/过滤、全局角色设置（仅 superAdmin）、启用禁用、
团队分页与认证审核、数据库表清单与数据浏览（脱敏）、单条 DML 执行与安全限制、
审计日志与概览统计。
"""

from sqlalchemy.engine import make_url

from tests.helpers import buildAuthHeaders

from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.models.enums import GlobalRole


def getUserId(account: dict) -> int:
    """从注册响应中取用户主键。"""
    return account["user"]["user"]["id"]


def createPendingTeam(client, adminToken: str, name: str) -> dict:
    """创建一个待认证团队并返回团队详情。"""
    response = client.post(
        "/api/v1/teams",
        json={"name": name, "description": "Admin Review Test Team", "joinMethod": "free"},
        headers=buildAuthHeaders(adminToken),
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestAdminAuthorization:
    """管理后台鉴权与全局角色设置。"""

    def test_nonAdminIsForbidden(self, client, registerUser):
        """普通用户访问管理后台全部返回 403。"""
        account = registerUser()
        headers = buildAuthHeaders(account["token"])
        assert client.get("/api/v1/admin/users", headers=headers).status_code == 403
        assert client.get("/api/v1/admin/overview", headers=headers).status_code == 403
        assert client.get("/api/v1/admin/database/tables", headers=headers).status_code == 403

    def test_setGlobalRoleRequiresSuperAdmin(self, client, registerUser, superAdminHeaders, setUserGlobalRole):
        """superAdmin 可设置全局管理员；全局管理员不能再设置角色，也不能改 superAdmin。"""
        target = registerUser()
        targetHeaders = buildAuthHeaders(target["token"])
        setRoleResponse = client.put(
            f"/api/v1/admin/users/{getUserId(target)}/global-role",
            json={"globalRole": "globalAdmin"},
            headers=superAdminHeaders,
        )
        assert setRoleResponse.status_code == 200
        assert setRoleResponse.json()["globalRole"] == "globalAdmin"
        assert client.get("/api/v1/admin/users", headers=targetHeaders).status_code == 200
        anotherUser = registerUser()
        forbiddenSet = client.put(
            f"/api/v1/admin/users/{getUserId(anotherUser)}/global-role",
            json={"globalRole": "user"},
            headers=targetHeaders,
        )
        assert forbiddenSet.status_code == 403
        superAdminUserList = client.get(
            "/api/v1/admin/users?globalRole=superAdmin", headers=superAdminHeaders
        )
        superAdminId = superAdminUserList.json()["items"][0]["id"]
        protectSuperAdmin = client.put(
            f"/api/v1/admin/users/{superAdminId}/global-role",
            json={"globalRole": "user"},
            headers=superAdminHeaders,
        )
        assert protectSuperAdmin.status_code == 403
        invalidRole = client.put(
            f"/api/v1/admin/users/{getUserId(anotherUser)}/global-role",
            json={"globalRole": "superAdmin"},
            headers=superAdminHeaders,
        )
        assert invalidRole.status_code == 400

    def test_userListFiltersAndStatus(self, client, registerUser, superAdminHeaders, setUserGlobalRole):
        """用户分页支持关键字/角色/状态过滤；禁用后无法登录，启用后恢复。"""
        enabledUser = registerUser(nickname="Enabled User")
        disabledUser = registerUser(nickname="Disabled User")
        setUserGlobalRole(getUserId(disabledUser), GlobalRole.GLOBAL_ADMIN)
        filtered = client.get(
            f"/api/v1/admin/users?keyword={enabledUser['user']['user']['username']}",
            headers=superAdminHeaders,
        )
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 1
        assert filtered.json()["items"][0]["teamCount"] == 0
        adminRoleList = client.get(
            "/api/v1/admin/users?globalRole=globalAdmin", headers=superAdminHeaders
        )
        assert adminRoleList.json()["total"] == 1
        disableResponse = client.put(
            f"/api/v1/admin/users/{getUserId(enabledUser)}/status",
            json={"isActive": False},
            headers=superAdminHeaders,
        )
        assert disableResponse.status_code == 200
        assert disableResponse.json()["isActive"] is False
        disabledLogin = client.post(
            "/api/v1/auth/login",
            json={
                "username": enabledUser["user"]["user"]["username"],
                "password": "Password123",
            },
        )
        assert disabledLogin.status_code == 403
        assert disabledLogin.json()["code"] == "ACCOUNT_DISABLED"
        inactiveList = client.get(
            "/api/v1/admin/users?isActive=false", headers=superAdminHeaders
        )
        assert any(
            item["id"] == getUserId(enabledUser) for item in inactiveList.json()["items"]
        )
        enableResponse = client.put(
            f"/api/v1/admin/users/{getUserId(enabledUser)}/status",
            json={"isActive": True},
            headers=superAdminHeaders,
        )
        assert enableResponse.json()["isActive"] is True
        adminSelfDisable = client.put(
            f"/api/v1/admin/users/{getUserId(disabledUser)}/status",
            json={"isActive": False},
            headers=buildAuthHeaders(disabledUser["token"]),
        )
        assert adminSelfDisable.status_code == 400


class TestAdminTeamsAndOverview:
    """团队分页、认证审核与概览统计。"""

    def test_teamCertificationFlow(self, client, registerUser, superAdminHeaders):
        """团队认证通过置 active、驳回置 rejected，团队列表可按状态过滤。"""
        creator = registerUser()
        pendingTeam = createPendingTeam(client, creator["token"], "Certification Test Team")
        pendingList = client.get("/api/v1/admin/teams?status=pending", headers=superAdminHeaders)
        assert pendingList.status_code == 200
        assert any(item["id"] == pendingTeam["id"] for item in pendingList.json()["items"])
        item = next(
            item for item in pendingList.json()["items"] if item["id"] == pendingTeam["id"]
        )
        assert item["memberCount"] == 1
        assert item["creatorName"] == creator["user"]["user"]["nickname"]
        approveResponse = client.put(
            f"/api/v1/admin/teams/{pendingTeam['id']}/certification",
            json={"approved": True},
            headers=superAdminHeaders,
        )
        assert approveResponse.status_code == 200
        assert approveResponse.json()["status"] == "active"
        rejectedTeamCreator = registerUser()
        rejectedTeam = createPendingTeam(client, rejectedTeamCreator["token"], "Rejection Test Team")
        rejectResponse = client.put(
            f"/api/v1/admin/teams/{rejectedTeam['id']}/certification",
            json={"approved": False},
            headers=superAdminHeaders,
        )
        assert rejectResponse.json()["status"] == "rejected"
        rejectedDetail = client.get(
            f"/api/v1/teams/{rejectedTeam['id']}",
            headers=buildAuthHeaders(rejectedTeamCreator["token"]),
        )
        assert rejectedDetail.status_code == 403

    def test_overviewCounts(self, client, registerUser, superAdminHeaders):
        """概览返回用户/团队/任务统计与当前数据库名。"""
        registerUser()
        pendingTeam = createPendingTeam(client, registerUser()["token"], "Overview Pending Team")
        overview = client.get("/api/v1/admin/overview", headers=superAdminHeaders)
        assert overview.status_code == 200
        body = overview.json()
        assert set(body) == {
            "userCount",
            "activeUserCount",
            "teamCount",
            "pendingTeamCount",
            "taskCount",
            "databaseName",
        }
        assert body["userCount"] >= 3
        assert body["activeUserCount"] >= 3
        assert body["teamCount"] >= 1
        assert body["pendingTeamCount"] >= 1
        assert body["taskCount"] == 0
        expectedDatabaseName = make_url(settings.databaseUrl).database or ""
        assert body["databaseName"] == expectedDatabaseName
        assert pendingTeam["status"] == "pending"


class TestAdminDatabase:
    """数据库表清单、数据浏览脱敏、单条 DML 执行限制与审计日志。"""

    def test_tableListAndRowsMasked(self, client, registerUser, superAdminHeaders):
        """表清单含行数，数据浏览对密码/邮箱脱敏，非法表名 404。"""
        account = registerUser()
        client.put(
            "/api/v1/users/me",
            json={"email": "hidden@example.com"},
            headers=buildAuthHeaders(account["token"]),
        )
        tables = client.get("/api/v1/admin/database/tables", headers=superAdminHeaders)
        assert tables.status_code == 200
        tableNames = [item["tableName"] for item in tables.json()]
        assert "users" in tableNames
        assert "audit_logs" in tableNames
        usersTable = next(item for item in tables.json() if item["tableName"] == "users")
        assert usersTable["rowCount"] >= 2
        rowsResponse = client.get(
            "/api/v1/admin/database/tables/users/rows?page=1&pageSize=100",
            headers=superAdminHeaders,
        )
        assert rowsResponse.status_code == 200
        body = rowsResponse.json()
        assert "password_hash" in body["columns"]
        assert body["total"] >= 2
        assert all(row["password_hash"] == "******" for row in body["rows"])
        assert any(row["email"] == "h***@example.com" for row in body["rows"])
        missingTable = client.get(
            "/api/v1/admin/database/tables/not_exist_table/rows", headers=superAdminHeaders
        )
        assert missingTable.status_code == 404

    def test_executeSqlSafetyAndAudit(self, client, registerUser, superAdminHeaders):
        """SELECT 返回行；写语句返回受影响行数；DDL/多语句/未确认均被拒绝；操作写审计日志。"""
        account = registerUser(nickname="Audit Target")
        selectResponse = client.post(
            "/api/v1/admin/database/execute",
            json={"sql": "SELECT id, username FROM users", "confirm": True},
            headers=superAdminHeaders,
        )
        assert selectResponse.status_code == 200
        selectBody = selectResponse.json()
        assert selectBody["executed"] is True
        assert selectBody["statementType"] == "SELECT"
        assert len(selectBody["rows"]) == selectBody["affectedRows"]
        assert "id" in selectBody["rows"][0]
        updateResponse = client.post(
            "/api/v1/admin/database/execute",
            json={
                "sql": f"UPDATE users SET bio = 'updated-by-admin' WHERE id = {getUserId(account)}",
                "confirm": True,
            },
            headers=superAdminHeaders,
        )
        assert updateResponse.status_code == 200
        assert updateResponse.json()["statementType"] == "UPDATE"
        assert updateResponse.json()["affectedRows"] == 1
        invalidRequests = [
            {"sql": "DROP TABLE users", "confirm": True},
            {"sql": "SELECT 1; SELECT 2", "confirm": True},
            {"sql": "TRUNCATE TABLE users", "confirm": True},
            {"sql": "SELECT id FROM users", "confirm": False},
        ]
        for invalidPayload in invalidRequests:
            response = client.post(
                "/api/v1/admin/database/execute",
                json=invalidPayload,
                headers=superAdminHeaders,
            )
            assert response.status_code == 400, invalidPayload
        auditLogs = client.get(
            "/api/v1/admin/audit-logs?page=1&pageSize=20", headers=superAdminHeaders
        )
        assert auditLogs.status_code == 200
        actions = [item["action"] for item in auditLogs.json()["items"]]
        assert "admin.database.execute" in actions
        executedLog = next(
            item
            for item in auditLogs.json()["items"]
            if item["action"] == "admin.database.execute"
        )
        assert "SELECT" in executedLog["detail"] or "UPDATE" in executedLog["detail"]
        assert executedLog["operatorName"]