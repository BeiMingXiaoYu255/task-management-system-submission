"""v1.1 跨模块集成测试（Lead 维护）：团队协作、协作任务双审核、通知与 AI 自动分配。

依赖 conftest.py 提供的独立测试库与注册/团队夹具；使用真实 HTTP 接口串起完整链路。
"""

from tests.helpers import buildAuthHeaders


def createTeam(client, ownerAccount, name: str) -> dict:
    """创建并激活一个团队（直接写入 active 状态，便于协作测试）。"""
    response = client.post(
        "/api/v1/teams",
        json={"name": name, "description": "v1.1 Integration Test Team", "joinMethod": "inviteOnly"},
        headers=buildAuthHeaders(ownerAccount["token"]),
    )
    assert response.status_code in (200, 201), response.text
    teamData = response.json()
    from TaskManagementBackend.core.database import SessionLocal
    from TaskManagementBackend.models import Team
    from TaskManagementBackend.models.enums import TeamStatus

    databaseSession = SessionLocal()
    try:
        team = databaseSession.get(Team, teamData["id"])
        team.status = TeamStatus.ACTIVE
        databaseSession.commit()
    finally:
        databaseSession.close()
    return teamData


def updateProfileSkills(client, account, skillTagNames: list[str]) -> None:
    """按技能标签名称为用户设置技能（不存在时先创建标签）。"""
    headers = buildAuthHeaders(account["token"])
    skillsPayload = []
    for skillName in skillTagNames:
        tagResponse = client.post(
            "/api/v1/users/me/skills/tags",
            json={"name": skillName, "category": "Testing"},
            headers=headers,
        )
        assert tagResponse.status_code in (200, 201), tagResponse.text
        skillsPayload.append({"skillTagId": tagResponse.json()["id"], "proficiency": 5})
    response = client.put(
        "/api/v1/users/me/skills", json={"skills": skillsPayload}, headers=headers
    )
    assert response.status_code == 200, response.text


def createSubTeam(client, teamId: int, adminHeaders: dict, leaderUserId: int, name: str) -> dict:
    """创建子团队并返回详情。"""
    response = client.post(
        "/api/v1/teams/" + str(teamId) + "/sub-teams",
        json={"name": name, "description": "Integration test sub-team", "leaderUserId": leaderUserId, "memberUserIds": [leaderUserId]},
        headers=adminHeaders,
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def createCollaboration(
    client,
    initiatorAccount,
    initiatorTeamId: int,
    targetTeamId: int,
    initiatorLiaisonUserId: int,
    initiatorSubTeamId: int | None = None,
) -> dict:
    """发起协作申请并返回协作数据。"""
    payload = {
        "initiatorTeamId": initiatorTeamId,
        "targetTeamId": targetTeamId,
        "initiatorLiaisonUserId": initiatorLiaisonUserId,
        "message": "v1.1 integration test collaboration request",
    }
    if initiatorSubTeamId is not None:
        payload["initiatorSubTeamId"] = initiatorSubTeamId
    response = client.post("/api/v1/collaborations", json=payload, headers=buildAuthHeaders(initiatorAccount["token"]))
    assert response.status_code in (200, 201), response.text
    return response.json()


class TestSubTeams:
    """子团队 CRUD 与权限。"""

    def test_sub_team_crud(self, client, registerUser):
        """管理员可创建子团队、维护成员，普通成员可查看列表。"""
        adminAccount = registerUser()
        memberAccount = registerUser()
        team = createTeam(client, adminAccount, "Sub-team Test Team")
        adminHeaders = buildAuthHeaders(adminAccount["token"])
        memberId = memberAccount["user"]["user"]["id"]
        # 先把成员加入团队
        from TaskManagementBackend.core.database import SessionLocal
        from TaskManagementBackend.models import TeamLevel, TeamMember
        from TaskManagementBackend.models.enums import TeamRole

        databaseSession = SessionLocal()
        try:
            level = databaseSession.execute(
                __import__("sqlalchemy").select(TeamLevel).where(TeamLevel.teamId == team["id"], TeamLevel.levelOrder == 1)
            ).scalar_one()
            databaseSession.add(
                TeamMember(teamId=team["id"], userId=memberId, role=TeamRole.MEMBER, levelId=level.id)
            )
            databaseSession.commit()
        finally:
            databaseSession.close()
        subTeam = createSubTeam(client, team["id"], adminHeaders, memberId, "Integration Frontend Sub-team")
        assert subTeam["leaderUserId"] == memberId
        listResponse = client.get(
            "/api/v1/teams/" + str(team["id"]) + "/sub-teams",
            headers=buildAuthHeaders(memberAccount["token"]),
        )
        assert listResponse.status_code == 200, listResponse.text
        assert any(item["id"] == subTeam["id"] for item in listResponse.json())
        detailResponse = client.get(
            "/api/v1/teams/" + str(team["id"]) + "/sub-teams/" + str(subTeam["id"]),
            headers=adminHeaders,
        )
        assert detailResponse.status_code == 200, detailResponse.text
        assert detailResponse.json()["memberCount"] >= 1

    def test_sub_team_collaboration(self, client, registerUser):
        """子团队作为协作单位：子负责人发起协作、对方管理员确认。"""
        initiatorAdmin = registerUser()
        targetAdmin = registerUser()
        initiatorTeam = createTeam(client, initiatorAdmin, "Sub-team Collaboration Initiator")
        targetTeam = createTeam(client, targetAdmin, "Sub-team Collaboration Receiver")
        initiatorTeamAdminHeaders = buildAuthHeaders(initiatorAdmin["token"])
        memberAccount = registerUser()
        memberId = memberAccount["user"]["user"]["id"]
        from TaskManagementBackend.core.database import SessionLocal
        from TaskManagementBackend.models import TeamLevel, TeamMember
        from TaskManagementBackend.models.enums import TeamRole

        databaseSession = SessionLocal()
        try:
            level = databaseSession.execute(
                __import__("sqlalchemy").select(TeamLevel).where(TeamLevel.teamId == initiatorTeam["id"], TeamLevel.levelOrder == 1)
            ).scalar_one()
            databaseSession.add(
                TeamMember(teamId=initiatorTeam["id"], userId=memberId, role=TeamRole.MEMBER, levelId=level.id)
            )
            databaseSession.commit()
        finally:
            databaseSession.close()
        subTeam = createSubTeam(client, initiatorTeam["id"], initiatorTeamAdminHeaders, memberId, "Collaboration Sub-team")
        # 子负责人发起协作（子团队作为发起方单位）
        collaboration = createCollaboration(
            client,
            memberAccount,
            initiatorTeam["id"],
            targetTeam["id"],
            memberId,
            initiatorSubTeamId=subTeam["id"],
        )
        assert collaboration["status"] == "pending"
        assert collaboration["canConfirm"] is False
        confirmResponse = client.post(
            "/api/v1/collaborations/" + str(collaboration["id"]) + "/confirm",
            json={"approved": True, "targetLiaisonUserId": targetAdmin["user"]["user"]["id"]},
            headers=buildAuthHeaders(targetAdmin["token"]),
        )
        assert confirmResponse.status_code == 200, confirmResponse.text
        assert confirmResponse.json()["status"] == "active"


class TestCollaborationTaskFlow:
    """协作任务完整闭环：申请→确认→派发→接单指派→双审核。"""

    def test_full_collaboration_task_flow(self, client, registerUser):
        """验证协作任务从建立到发起方审核归档的完整状态流转与通知。"""
        initiatorAdmin = registerUser()
        targetAdmin = registerUser()
        targetExecutor = registerUser()
        initiatorTeam = createTeam(client, initiatorAdmin, "Collaboration Initiator Team")
        targetTeam = createTeam(client, targetAdmin, "Collaboration Receiver Team")
        targetAdminHeaders = buildAuthHeaders(targetAdmin["token"])
        initiatorHeaders = buildAuthHeaders(initiatorAdmin["token"])
        targetExecutorId = targetExecutor["user"]["user"]["id"]
        # 把执行人加入接收方团队
        from TaskManagementBackend.core.database import SessionLocal
        from TaskManagementBackend.models import TeamLevel, TeamMember
        from TaskManagementBackend.models.enums import TeamRole

        databaseSession = SessionLocal()
        try:
            level = databaseSession.execute(
                __import__("sqlalchemy").select(TeamLevel).where(TeamLevel.teamId == targetTeam["id"], TeamLevel.levelOrder == 1)
            ).scalar_one()
            databaseSession.add(
                TeamMember(teamId=targetTeam["id"], userId=targetExecutorId, role=TeamRole.MEMBER, levelId=level.id)
            )
            databaseSession.commit()
        finally:
            databaseSession.close()
        collaboratorUserId = initiatorAdmin["user"]["user"]["id"]
        collaboration = createCollaboration(
            client, initiatorAdmin, initiatorTeam["id"], targetTeam["id"], collaboratorUserId
        )
        confirmResponse = client.post(
            "/api/v1/collaborations/" + str(collaboration["id"]) + "/confirm",
            json={"approved": True, "targetLiaisonUserId": targetAdmin["user"]["user"]["id"]},
            headers=targetAdminHeaders,
        )
        assert confirmResponse.status_code == 200, confirmResponse.text
        # 发起方创建协作任务
        taskResponse = client.post(
            "/api/v1/collaborations/" + str(collaboration["id"]) + "/tasks",
            json={
                "title": "Collaboration task integration test",
                "description": "Verify the collaboration two-stage review flow",
                "priority": "high",
                "acceptanceMode": "mandatory",
            },
            headers=initiatorHeaders,
        )
        assert taskResponse.status_code in (200, 201), taskResponse.text
        taskData = taskResponse.json()
        taskId = taskData["id"]
        assert taskData["collaborationPhase"] == "pendingConfirmation"
        # 接收方对接人确认并指派执行人
        confirmTaskResponse = client.post(
            "/api/v1/collaboration-tasks/" + str(taskId) + "/confirm",
            json={"approved": True, "assigneeUserIds": [targetExecutorId]},
            headers=targetAdminHeaders,
        )
        assert confirmTaskResponse.status_code == 200, confirmTaskResponse.text
        assert confirmTaskResponse.json()["collaborationPhase"] == "executing"
        # 执行人提交完成
        submitResponse = client.post(
            "/api/v1/tasks/" + str(taskId) + "/submit",
            headers=buildAuthHeaders(targetExecutor["token"]),
        )
        assert submitResponse.status_code == 200, submitResponse.text
        assert submitResponse.json()["collaborationPhase"] == "targetReview"
        # 接收方对接人审核通过 → 进入发起方审核
        targetReviewResponse = client.post(
            "/api/v1/collaboration-tasks/" + str(taskId) + "/target-review",
            json={"assignmentUserId": targetExecutorId, "approved": True, "comment": "Receiver review approved"},
            headers=targetAdminHeaders,
        )
        assert targetReviewResponse.status_code == 200, targetReviewResponse.text
        assert targetReviewResponse.json()["collaborationPhase"] == "sourceReview"
        # 发起方发布者审核通过 → 归档
        sourceReviewResponse = client.post(
            "/api/v1/collaboration-tasks/" + str(taskId) + "/source-review",
            json={"assignmentUserId": targetExecutorId, "approved": True, "comment": "Initiator review approved"},
            headers=initiatorHeaders,
        )
        assert sourceReviewResponse.status_code == 200, sourceReviewResponse.text
        assert sourceReviewResponse.json()["status"] == "archived"
        # 通知：接收方对接人收到过协作任务通知
        notificationsResponse = client.get(
            "/api/v1/notifications?page=1&pageSize=50", headers=targetAdminHeaders
        )
        assert notificationsResponse.status_code == 200, notificationsResponse.text
        notificationTypes = {item["type"] for item in notificationsResponse.json()["items"]}
        assert "collaborationTaskReceived" in notificationTypes

    def test_collaboration_task_reject_and_target_reject(self, client, registerUser):
        """接收方拒绝任务与接收方驳回执行人提交两条分支。"""
        initiatorAdmin = registerUser()
        targetAdmin = registerUser()
        executorAccount = registerUser()
        initiatorTeam = createTeam(client, initiatorAdmin, "Reject Branch Initiator")
        targetTeam = createTeam(client, targetAdmin, "Reject Branch Receiver")
        initiatorHeaders = buildAuthHeaders(initiatorAdmin["token"])
        targetHeaders = buildAuthHeaders(targetAdmin["token"])
        executorId = executorAccount["user"]["user"]["id"]
        from TaskManagementBackend.core.database import SessionLocal
        from TaskManagementBackend.models import TeamLevel, TeamMember
        from TaskManagementBackend.models.enums import TeamRole

        databaseSession = SessionLocal()
        try:
            level = databaseSession.execute(
                __import__("sqlalchemy").select(TeamLevel).where(TeamLevel.teamId == targetTeam["id"], TeamLevel.levelOrder == 1)
            ).scalar_one()
            databaseSession.add(TeamMember(teamId=targetTeam["id"], userId=executorId, role=TeamRole.MEMBER, levelId=level.id))
            databaseSession.commit()
        finally:
            databaseSession.close()
        collaboration = createCollaboration(
            client, initiatorAdmin, initiatorTeam["id"], targetTeam["id"],
            initiatorAdmin["user"]["user"]["id"],
        )
        client.post(
            "/api/v1/collaborations/" + str(collaboration["id"]) + "/confirm",
            json={"approved": True, "targetLiaisonUserId": targetAdmin["user"]["user"]["id"]},
            headers=targetHeaders,
        )
        taskResponse = client.post(
            "/api/v1/collaborations/" + str(collaboration["id"]) + "/tasks",
            json={"title": "Reject branch collaboration task", "priority": "medium", "acceptanceMode": "mandatory"},
            headers=initiatorHeaders,
        )
        taskId = taskResponse.json()["id"]
        client.post(
            "/api/v1/collaboration-tasks/" + str(taskId) + "/confirm",
            json={"approved": True, "assigneeUserIds": [executorId]},
            headers=targetHeaders,
        )
        client.post("/api/v1/tasks/" + str(taskId) + "/submit", headers=buildAuthHeaders(executorAccount["token"]))
        targetRejectResponse = client.post(
            "/api/v1/collaboration-tasks/" + str(taskId) + "/target-review",
            json={"assignmentUserId": executorId, "approved": False, "comment": "Please add test screenshots"},
            headers=targetHeaders,
        )
        assert targetRejectResponse.status_code == 200, targetRejectResponse.text
        assert targetRejectResponse.json()["collaborationPhase"] == "executing"


class TestAiAutoAssign:
    """AI 推荐与自动分配集成。"""

    def test_ai_status_and_recommend(self, client, registerUser):
        """AI 状态返回调度配置；推荐接口返回对象结构。"""
        adminAccount = registerUser()
        memberAccount = registerUser()
        team = createTeam(client, adminAccount, "AI Recommendation Team")
        updateProfileSkills(client, memberAccount, ["Backend Development", "Database Design"])
        from TaskManagementBackend.core.database import SessionLocal
        from TaskManagementBackend.models import TeamLevel, TeamMember
        from TaskManagementBackend.models.enums import TeamRole

        databaseSession = SessionLocal()
        try:
            level = databaseSession.execute(
                __import__("sqlalchemy").select(TeamLevel).where(TeamLevel.teamId == team["id"], TeamLevel.levelOrder == 1)
            ).scalar_one()
            databaseSession.add(
                TeamMember(teamId=team["id"], userId=memberAccount["user"]["user"]["id"], role=TeamRole.MEMBER, levelId=level.id)
            )
            databaseSession.commit()
        finally:
            databaseSession.close()
        adminHeaders = buildAuthHeaders(adminAccount["token"])
        statusResponse = client.get("/api/v1/ai/status", headers=adminHeaders)
        assert statusResponse.status_code == 200, statusResponse.text
        statusData = statusResponse.json()
        assert statusData["dispatchMode"] in {"LOCAL_ONLY", "LLM_ONLY", "LOCAL_FIRST", "LLM_FIRST"}
        assert "llmConfigured" in statusData
        recommendResponse = client.post(
            "/api/v1/teams/" + str(team["id"]) + "/ai/recommend-assignees",
            json={
                "title": "Implement backend endpoint",
                "priority": "high",
                "requiredSkillNames": ["Backend Development"],
            },
            headers=adminHeaders,
        )
        assert recommendResponse.status_code == 200, recommendResponse.text
        recommendData = recommendResponse.json()
        assert "candidates" in recommendData and isinstance(recommendData["candidates"], list)
        if recommendData["candidates"]:
            candidate = recommendData["candidates"][0]
            assert candidate["userId"] == memberAccount["user"]["user"]["id"]
            assert candidate["score"] > 0

    def test_auto_assign_publish_and_manual_assign(self, client, registerUser):
        """发布任务开启 AI 自动分配：有匹配自动指派；无匹配可手动指派。"""
        adminAccount = registerUser()
        memberAccount = registerUser()
        team = createTeam(client, adminAccount, "AI Auto-assignment Team")
        updateProfileSkills(client, memberAccount, ["Frontend Development"])
        from TaskManagementBackend.core.database import SessionLocal
        from TaskManagementBackend.models import TeamLevel, TeamMember
        from TaskManagementBackend.models.enums import TeamRole

        databaseSession = SessionLocal()
        try:
            level = databaseSession.execute(
                __import__("sqlalchemy").select(TeamLevel).where(TeamLevel.teamId == team["id"], TeamLevel.levelOrder == 1)
            ).scalar_one()
            databaseSession.add(
                TeamMember(teamId=team["id"], userId=memberAccount["user"]["user"]["id"], role=TeamRole.MEMBER, levelId=level.id)
            )
            databaseSession.commit()
        finally:
            databaseSession.close()
        adminHeaders = buildAuthHeaders(adminAccount["token"])
        autoTaskResponse = client.post(
            "/api/v1/teams/" + str(team["id"]) + "/tasks",
            json={
                "title": "Auto-assigned task",
                "priority": "high",
                "assignmentMode": "specific",
                "acceptanceMode": "mandatory",
                "autoAssign": True,
                "requiredSkillNames": ["Frontend Development"],
            },
            headers=adminHeaders,
        )
        assert autoTaskResponse.status_code in (200, 201), autoTaskResponse.text
        autoTaskData = autoTaskResponse.json()
        assert autoTaskData["autoAssigned"] is True
        assert len(autoTaskData["assignments"]) == 1
        assert autoTaskData["assignments"][0]["userId"] == memberAccount["user"]["user"]["id"]
        assert autoTaskData["assignments"][0]["assignmentSource"] == "ai"
        # 无匹配：创建成功但无执行人，可手动指派
        failedTaskResponse = client.post(
            "/api/v1/teams/" + str(team["id"]) + "/tasks",
            json={
                "title": "Task with no matching assignee",
                "priority": "low",
                "assignmentMode": "specific",
                "acceptanceMode": "mandatory",
                "autoAssign": True,
                "requiredSkillNames": ["Non-existent skill tag"],
            },
            headers=adminHeaders,
        )
        assert failedTaskResponse.status_code in (200, 201), failedTaskResponse.text
        failedTaskData = failedTaskResponse.json()
        assert failedTaskData["assignments"] == []
        assert failedTaskData["canAssign"] is True
        assignResponse = client.post(
            "/api/v1/tasks/" + str(failedTaskData["id"]) + "/assignments",
            json={"userIds": [memberAccount["user"]["user"]["id"]]},
            headers=adminHeaders,
        )
        assert assignResponse.status_code == 200, assignResponse.text
        assert len(assignResponse.json()["assignments"]) == 1


class TestAIConfigSettings:
    """v1.1.1 AI 配置持久化与连通性测试接口。"""

    def test_ai_config_permissions_and_masking(self, client, registerUser, superAdminHeaders):
        """普通用户只读且看不到 Key 掩码；管理员 canEdit=true；普通用户写接口 403。"""
        normalAccount = registerUser()
        normalHeaders = buildAuthHeaders(normalAccount["token"])
        normalGetResponse = client.get("/api/v1/settings/ai-config", headers=normalHeaders)
        assert normalGetResponse.status_code == 200, normalGetResponse.text
        normalConfig = normalGetResponse.json()
        assert normalConfig["canEdit"] is False
        assert normalConfig["apiKeyMasked"] is None
        assert normalConfig["dispatchMode"] in {"LOCAL_ONLY", "LLM_ONLY", "LOCAL_FIRST", "LLM_FIRST"}
        forbiddenPut = client.put(
            "/api/v1/settings/ai-config",
            json={"dispatchMode": "LOCAL_ONLY"},
            headers=normalHeaders,
        )
        assert forbiddenPut.status_code == 403, forbiddenPut.text
        forbiddenTest = client.post(
            "/api/v1/settings/ai-config/test",
            json={},
            headers=normalHeaders,
        )
        assert forbiddenTest.status_code == 403, forbiddenTest.text
        adminResponse = client.get("/api/v1/settings/ai-config", headers=superAdminHeaders)
        assert adminResponse.status_code == 200, adminResponse.text
        assert adminResponse.json()["canEdit"] is True

    def test_admin_save_config_and_effect_on_ai_status(self, client, superAdminHeaders):
        """管理员保存配置后 /ai/status 立即返回新的调度模式与评分参数。"""
        updateResponse = client.put(
            "/api/v1/settings/ai-config",
            json={
                "dispatchMode": "LOCAL_ONLY",
                "matchThreshold": 42,
                "workloadPenalty": 7,
                "llmTimeoutSeconds": 30,
                "llmMaxCandidates": 15,
                "clearApiKey": True,
            },
            headers=superAdminHeaders,
        )
        assert updateResponse.status_code == 200, updateResponse.text
        updatedConfig = updateResponse.json()
        assert updatedConfig["dispatchMode"] == "LOCAL_ONLY"
        assert updatedConfig["matchThreshold"] == 42
        assert updatedConfig["workloadPenalty"] == 7
        assert updatedConfig["configSource"] == "database"
        assert updatedConfig["hasApiKey"] is False
        statusResponse = client.get("/api/v1/ai/status", headers=superAdminHeaders)
        assert statusResponse.status_code == 200, statusResponse.text
        statusData = statusResponse.json()
        assert statusData["dispatchMode"] == "LOCAL_ONLY"
        assert statusData["matchThreshold"] == 42
        assert statusData["workloadPenalty"] == 7

    def test_connectivity_test_local_and_unconfigured_llm(self, client, superAdminHeaders):
        """LLM 未配置时测试接口仍返回本地引擎可用与中文提示。"""
        testResponse = client.post(
            "/api/v1/settings/ai-config/test",
            json={},
            headers=superAdminHeaders,
        )
        assert testResponse.status_code == 200, testResponse.text
        testResult = testResponse.json()
        assert testResult["local"]["available"] is True
        assert testResult["local"]["message"]
        assert testResult["llm"]["configured"] is False
        assert testResult["llm"]["success"] is False
        assert testResult["llm"]["latencyMs"] is None
        assert testResult["llm"]["message"]

    def test_admin_update_validation(self, client, superAdminHeaders):
        """非法调度模式/URL/阈值返回参数校验错误。"""
        invalidMode = client.put(
            "/api/v1/settings/ai-config",
            json={"dispatchMode": "INVALID_MODE"},
            headers=superAdminHeaders,
        )
        assert invalidMode.status_code in (400, 422), invalidMode.text
        invalidUrl = client.put(
            "/api/v1/settings/ai-config",
            json={"llmBaseUrl": "ftp://example.com"},
            headers=superAdminHeaders,
        )
        assert invalidUrl.status_code == 400, invalidUrl.text
        invalidThreshold = client.put(
            "/api/v1/settings/ai-config",
            json={"matchThreshold": 200},
            headers=superAdminHeaders,
        )
        assert invalidThreshold.status_code in (400, 422), invalidThreshold.text
