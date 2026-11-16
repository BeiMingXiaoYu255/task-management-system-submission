"""认证与用户资料模块接口测试。

覆盖：注册/登录/当前用户、登录失败限流、注销 token 黑名单、修改密码失效旧 token、
本人资料与技能标签、查看他人资料/公开资料的权限与隐私字段可见性。
"""

import secrets

from tests.helpers import buildAuthHeaders

from TaskManagementBackend.models.enums import GlobalRole


def generateUsername(prefix: str = "u") -> str:
    """生成随机用户名，避免用例之间唯一约束冲突。"""
    return f"{prefix}{secrets.token_hex(4)}"


def registerAccount(client, username: str | None = None, password: str = "Password123") -> dict:
    """注册一个账号并返回 AuthResponse 字典。"""
    payload = {
        "username": username or generateUsername(),
        "password": password,
        "nickname": "Test User",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


class TestAuthFlow:
    """注册、登录、当前用户、注销与修改密码。"""

    def test_registerLoginAndCurrentUser(self, client):
        """注册成功返回 token + CurrentUser，token 可用于 /auth/me，且可再次登录。"""
        username = generateUsername("alice")
        body = registerAccount(client, username=username)
        assert body["token"]
        assert body["user"]["user"]["username"] == username
        assert body["user"]["teams"] == []
        headers = buildAuthHeaders(body["token"])
        meResponse = client.get("/api/v1/auth/me", headers=headers)
        assert meResponse.status_code == 200
        assert meResponse.json()["user"]["id"] == body["user"]["user"]["id"]
        loginResponse = client.post(
            "/api/v1/auth/login", json={"username": username, "password": "Password123"}
        )
        assert loginResponse.status_code == 200
        assert loginResponse.json()["user"]["user"]["nickname"] == "Test User"

    def test_registerValidationFailures(self, client):
        """用户名/密码/邮箱重复与格式错误均应被拒绝。"""
        username = generateUsername("bob")
        registerAccount(client, username=username)
        duplicateResponse = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "Password123", "nickname": "Duplicate User"},
        )
        assert duplicateResponse.status_code == 409
        assert duplicateResponse.json()["code"] == "CONFLICT"
        assert duplicateResponse.json()["message"] == "Username already exists"
        invalidUsername = client.post(
            "/api/v1/auth/register",
            json={"username": "ab", "password": "Password123", "nickname": "Short Name"},
        )
        assert invalidUsername.status_code == 400
        weakPassword = client.post(
            "/api/v1/auth/register",
            json={"username": generateUsername("carol"), "password": "abc", "nickname": "Weak Password"},
        )
        assert weakPassword.status_code == 400
        emailUser = generateUsername("dave")
        registerAccount(client, username=emailUser)
        profileResponse = client.post(
            "/api/v1/auth/login", json={"username": emailUser, "password": "Password123"}
        )
        headers = buildAuthHeaders(profileResponse.json()["token"])
        client.put("/api/v1/users/me", json={"email": "shared@example.com"}, headers=headers)
        duplicateEmail = client.post(
            "/api/v1/auth/register",
            json={
                "username": generateUsername("erin"),
                "password": "Password123",
                "nickname": "Duplicate Email",
                "email": "shared@example.com",
            },
        )
        assert duplicateEmail.status_code == 409

    def test_loginFailureRateLimit(self, client):
        """同一 IP+用户名 5 分钟内失败 10 次后，第 11 次返回 429。"""
        username = generateUsername("rate")
        registerAccount(client, username=username)
        for _ in range(10):
            response = client.post(
                "/api/v1/auth/login", json={"username": username, "password": "WrongPass1"}
            )
            assert response.status_code == 401
        limitedResponse = client.post(
            "/api/v1/auth/login", json={"username": username, "password": "Password123"}
        )
        assert limitedResponse.status_code == 429
        assert limitedResponse.json()["code"] == "RATE_LIMITED"

    def test_logoutBlacklistsToken(self, client):
        """注销后原 token 立即失效，无法再访问受保护接口。"""
        account = registerAccount(client)
        headers = buildAuthHeaders(account["token"])
        logoutResponse = client.post("/api/v1/auth/logout", headers=headers)
        assert logoutResponse.status_code == 200
        assert logoutResponse.json()["message"] == "Logged out successfully"
        afterLogout = client.get("/api/v1/auth/me", headers=headers)
        assert afterLogout.status_code == 401
        assert afterLogout.json()["code"] in ("TOKEN_EXPIRED", "INVALID_CREDENTIALS")

    def test_changePasswordInvalidatesCurrentToken(self, client):
        """修改密码需旧密码；成功后旧 token 失效、新密码可登录、旧密码不可登录。"""
        username = generateUsername("pwd")
        account = registerAccount(client, username=username)
        headers = buildAuthHeaders(account["token"])
        wrongOld = client.put(
            "/api/v1/auth/password",
            json={"oldPassword": "WrongPass1", "newPassword": "NewPassword456"},
            headers=headers,
        )
        assert wrongOld.status_code == 400
        samePassword = client.put(
            "/api/v1/auth/password",
            json={"oldPassword": "Password123", "newPassword": "Password123"},
            headers=headers,
        )
        assert samePassword.status_code == 400
        success = client.put(
            "/api/v1/auth/password",
            json={"oldPassword": "Password123", "newPassword": "NewPassword456"},
            headers=headers,
        )
        assert success.status_code == 200
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
        newLogin = client.post(
            "/api/v1/auth/login", json={"username": username, "password": "NewPassword456"}
        )
        assert newLogin.status_code == 200
        oldLogin = client.post(
            "/api/v1/auth/login", json={"username": username, "password": "Password123"}
        )
        assert oldLogin.status_code == 401


class TestUserProfile:
    """个人资料、技能标签与他人资料权限。"""

    def test_myProfileUpdateAndSkills(self, client):
        """本人资料修改、技能覆盖式保存与技能标签新建/查询。"""
        account = registerAccount(client)
        headers = buildAuthHeaders(account["token"])
        profile = client.get("/api/v1/users/me", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["email"] is None
        updated = client.put(
            "/api/v1/users/me",
            json={
                "nickname": "New Nickname",
                "email": "profile@example.com",
                "phone": "13800138000",
                "bio": "Personal bio",
            },
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["nickname"] == "New Nickname"
        assert updated.json()["email"] == "profile@example.com"
        assert updated.json()["bio"] == "Personal bio"
        tagList = client.get("/api/v1/skill-tags", headers=headers)
        assert tagList.status_code == 200
        assert len(tagList.json()) > 0
        firstTagId = tagList.json()[0]["id"]
        saved = client.put(
            "/api/v1/users/me/skills",
            json={"skills": [{"skillTagId": firstTagId, "proficiency": 5}]},
            headers=headers,
        )
        assert saved.status_code == 200
        assert saved.json()["skills"][0]["id"] == firstTagId
        assert saved.json()["skills"][0]["proficiency"] == 5
        createdTag = client.post(
            "/api/v1/users/me/skills/tags",
            json={"name": "Automation Testing", "category": "Testing"},
            headers=headers,
        )
        assert createdTag.status_code == 200
        assert createdTag.json()["name"] == "Automation Testing"
        againTag = client.post(
            "/api/v1/users/me/skills/tags",
            json={"name": "Automation Testing", "category": "Testing"},
            headers=headers,
        )
        assert againTag.json()["id"] == createdTag.json()["id"]
        keywordList = client.get("/api/v1/skill-tags?keyword=Automation", headers=headers)
        assert any(item["id"] == createdTag.json()["id"] for item in keywordList.json())
        invalidSkill = client.put(
            "/api/v1/users/me/skills",
            json={"skills": [{"skillTagId": 999999, "proficiency": 3}]},
            headers=headers,
        )
        assert invalidSkill.status_code == 400

    def test_profileVisibilityRules(self, client, teamFactory, setUserGlobalRole):
        """他人资料权限：同团队管理者/更高级别可看，隐私字段仅本人与全局管理员可见。"""
        adminAccount = registerAccount(client)
        adminHeaders = buildAuthHeaders(adminAccount["token"])
        team = teamFactory(adminAccount["token"], joinMethod="free")
        memberAccount = registerAccount(client)
        memberHeaders = buildAuthHeaders(memberAccount["token"])
        joinResponse = client.post(
            "/api/v1/teams/join", json={"teamId": team["id"]}, headers=memberHeaders
        )
        assert joinResponse.status_code == 200
        memberId = memberAccount["user"]["user"]["id"]
        adminId = adminAccount["user"]["user"]["id"]
        client.put(
            "/api/v1/users/me",
            json={"email": "member@example.com", "phone": "13900139000", "bio": "Member bio"},
            headers=memberHeaders,
        )
        managerView = client.get(f"/api/v1/users/{memberId}/profile", headers=adminHeaders)
        assert managerView.status_code == 200
        assert managerView.json()["bio"] == "Member bio"
        assert managerView.json()["email"] is None
        assert managerView.json()["phone"] is None
        lowerView = client.get(f"/api/v1/users/{adminId}/profile", headers=memberHeaders)
        assert lowerView.status_code == 403
        selfView = client.get(f"/api/v1/users/{memberId}/profile", headers=memberHeaders)
        assert selfView.status_code == 200
        assert selfView.json()["email"] == "member@example.com"
        outsiderAccount = registerAccount(client)
        outsiderResponse = client.get(
            f"/api/v1/users/{memberId}/profile",
            headers=buildAuthHeaders(outsiderAccount["token"]),
        )
        assert outsiderResponse.status_code == 403
        setUserGlobalRole(adminId, GlobalRole.GLOBAL_ADMIN)
        globalView = client.get(f"/api/v1/users/{memberId}/profile", headers=adminHeaders)
        assert globalView.status_code == 200
        assert globalView.json()["email"] == "member@example.com"
        assert globalView.json()["phone"] == "13900139000"
        publicView = client.get(
            f"/api/v1/users/{adminId}/public-profile", headers=memberHeaders
        )
        assert publicView.status_code == 200
        assert publicView.json()["email"] is None
        outsiderPublic = client.get(
            f"/api/v1/users/{adminId}/public-profile",
            headers=buildAuthHeaders(outsiderAccount["token"]),
        )
        assert outsiderPublic.status_code == 403