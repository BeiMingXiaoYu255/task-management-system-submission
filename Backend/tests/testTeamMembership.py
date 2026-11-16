"""团队成员与级别管理接口测试。

覆盖：踢人权限（管理员/子管理员）、子管理员设置、级别调整约束、候选成员可见性
与团队级别 CRUD（数值唯一、有成员引用不可删除）。
"""

from tests.helpers import buildAuthHeaders


def getUserId(account: dict) -> int:
    """从注册响应中取用户主键。"""
    return account["user"]["user"]["id"]


def getLevelByOrder(teamDetail: dict, levelOrder: int) -> dict:
    """从团队详情中按级别数值取级别对象。"""
    return next(level for level in teamDetail["levels"] if level["levelOrder"] == levelOrder)


class TestMemberManagement:
    """踢人权限、子管理员设置、级别调整与候选成员。"""

    def test_kickAndSubAdminPermissions(self, client, registerUser, teamFactory, memberFactory):
        """子管理员只能踢级别更低成员；管理员可踢普通成员；不能踢管理员与自己。"""
        admin = registerUser()
        adminHeaders = buildAuthHeaders(admin["token"])
        team = teamFactory(admin["token"])
        upperMember = memberFactory(team["id"], levelOrder=2)
        lowerMember = memberFactory(team["id"], levelOrder=1)
        upperHeaders = buildAuthHeaders(upperMember["token"])
        lowerHeaders = buildAuthHeaders(lowerMember["token"])
        plainKick = client.delete(
            f"/api/v1/teams/{team['id']}/members/{getUserId(lowerMember)}",
            headers=lowerHeaders,
        )
        assert plainKick.status_code == 403
        client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(upperMember)}/level",
            json={"levelId": getLevelByOrder(team, 2)["id"]},
            headers=adminHeaders,
        )
        setRole = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(upperMember)}/role",
            json={"role": "subAdmin"},
            headers=adminHeaders,
        )
        assert setRole.status_code == 200
        sameLevelKick = client.delete(
            f"/api/v1/teams/{team['id']}/members/{getUserId(admin)}",
            headers=upperHeaders,
        )
        assert sameLevelKick.status_code == 403
        subAdminKick = client.delete(
            f"/api/v1/teams/{team['id']}/members/{getUserId(lowerMember)}",
            headers=upperHeaders,
        )
        assert subAdminKick.status_code == 200
        assert subAdminKick.json()["message"] == "Member removed"
        selfKick = client.delete(
            f"/api/v1/teams/{team['id']}/members/{getUserId(admin)}", headers=adminHeaders
        )
        assert selfKick.status_code == 400

    def test_setMemberLevelRules(self, client, registerUser, teamFactory, memberFactory):
        """管理员可任意调整级别；子管理员不能把成员调整到与自己同级或更高。"""
        admin = registerUser()
        adminHeaders = buildAuthHeaders(admin["token"])
        team = teamFactory(admin["token"])
        managerAccount = memberFactory(team["id"], levelOrder=2)
        targetAccount = memberFactory(team["id"], levelOrder=1)
        managerHeaders = buildAuthHeaders(managerAccount["token"])
        targetHeaders = buildAuthHeaders(targetAccount["token"])
        plainSetLevel = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(targetAccount)}/level",
            json={"levelId": getLevelByOrder(team, 2)["id"]},
            headers=targetHeaders,
        )
        assert plainSetLevel.status_code == 403
        invalidLevel = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(targetAccount)}/level",
            json={"levelId": 999999},
            headers=adminHeaders,
        )
        assert invalidLevel.status_code == 400
        client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(managerAccount)}/role",
            json={"role": "subAdmin"},
            headers=adminHeaders,
        )
        tooHigh = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(targetAccount)}/level",
            json={"levelId": getLevelByOrder(team, 3)["id"]},
            headers=managerHeaders,
        )
        assert tooHigh.status_code == 403
        sameLevel = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(targetAccount)}/level",
            json={"levelId": getLevelByOrder(team, 2)["id"]},
            headers=managerHeaders,
        )
        assert sameLevel.status_code == 403
        validSet = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(targetAccount)}/level",
            json={"levelId": getLevelByOrder(team, 1)["id"]},
            headers=managerHeaders,
        )
        assert validSet.status_code == 200

    def test_roleChangeRequiresAdminAndCandidates(self, client, registerUser, teamFactory, memberFactory):
        """设置子管理员仅管理员可用；候选成员列表含级别与技能且仅管理者可见。"""
        admin = registerUser()
        adminHeaders = buildAuthHeaders(admin["token"])
        team = teamFactory(admin["token"])
        member = memberFactory(team["id"], levelOrder=1)
        memberHeaders = buildAuthHeaders(member["token"])
        plainSetRole = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(member)}/role",
            json={"role": "subAdmin"},
            headers=memberHeaders,
        )
        assert plainSetRole.status_code == 403
        invalidRole = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(member)}/role",
            json={"role": "admin"},
            headers=adminHeaders,
        )
        assert invalidRole.status_code == 400
        promoted = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(member)}/role",
            json={"role": "subAdmin"},
            headers=adminHeaders,
        )
        assert promoted.status_code == 200
        candidates = client.get(
            f"/api/v1/teams/{team['id']}/members/candidates", headers=memberHeaders
        )
        assert candidates.status_code == 200
        candidate = candidates.json()[0]
        assert {"userId", "levelName", "levelOrder", "skills", "role"} <= set(candidate)
        revoked = client.put(
            f"/api/v1/teams/{team['id']}/members/{getUserId(member)}/role",
            json={"role": "member"},
            headers=adminHeaders,
        )
        assert revoked.status_code == 200
        memberLevel = getLevelByOrder(team, 1)
        client.put(
            f"/api/v1/teams/{team['id']}/levels/{memberLevel['id']}",
            json={"name": memberLevel["name"], "levelOrder": 1, "canCreateTask": False},
            headers=adminHeaders,
        )
        levelRestrictedCandidates = client.get(
            f"/api/v1/teams/{team['id']}/members/candidates", headers=memberHeaders
        )
        assert levelRestrictedCandidates.status_code == 403
        client.put(
            f"/api/v1/teams/{team['id']}/levels/{memberLevel['id']}",
            json={"name": memberLevel["name"], "levelOrder": 1, "canCreateTask": True},
            headers=adminHeaders,
        )
        allowedCandidates = client.get(
            f"/api/v1/teams/{team['id']}/members/candidates", headers=memberHeaders
        )
        assert allowedCandidates.status_code == 200

    def test_levelCrudConstraints(self, client, registerUser, teamFactory, memberFactory):
        """级别 CRUD：数值唯一、有成员引用不可删、普通成员无管理权限。"""
        admin = registerUser()
        adminHeaders = buildAuthHeaders(admin["token"])
        team = teamFactory(admin["token"])
        member = memberFactory(team["id"], levelOrder=1)
        memberHeaders = buildAuthHeaders(member["token"])
        createLevel = client.post(
            f"/api/v1/teams/{team['id']}/levels",
            json={"name": "Expert", "levelOrder": 4, "canCreateTask": True},
            headers=adminHeaders,
        )
        assert createLevel.status_code == 201
        newLevelId = createLevel.json()["id"]
        assert createLevel.json()["memberCount"] == 0
        duplicateOrder = client.post(
            f"/api/v1/teams/{team['id']}/levels",
            json={"name": "Duplicate Level", "levelOrder": 4, "canCreateTask": False},
            headers=adminHeaders,
        )
        assert duplicateOrder.status_code == 409
        memberCreate = client.post(
            f"/api/v1/teams/{team['id']}/levels",
            json={"name": "Unauthorized Level", "levelOrder": 5, "canCreateTask": True},
            headers=memberHeaders,
        )
        assert memberCreate.status_code == 403
        updateLevel = client.put(
            f"/api/v1/teams/{team['id']}/levels/{newLevelId}",
            json={"name": "Senior Expert", "levelOrder": 5, "canCreateTask": False},
            headers=adminHeaders,
        )
        assert updateLevel.status_code == 200
        assert updateLevel.json()["levelOrder"] == 5
        usedLevel = getLevelByOrder(team, 1)
        deleteUsed = client.delete(
            f"/api/v1/teams/{team['id']}/levels/{usedLevel['id']}", headers=adminHeaders
        )
        assert deleteUsed.status_code == 400
        deleteFree = client.delete(
            f"/api/v1/teams/{team['id']}/levels/{newLevelId}", headers=adminHeaders
        )
        assert deleteFree.status_code == 200
        levelList = client.get(f"/api/v1/teams/{team['id']}/levels", headers=memberHeaders)
        assert levelList.status_code == 200
        assert len(levelList.json()) == 3
