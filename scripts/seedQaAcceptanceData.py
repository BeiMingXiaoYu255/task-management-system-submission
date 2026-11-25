"""QA 验收测试数据种子脚本（通过已安装应用的公开 HTTP API 写入数据）。

用途：
    为 v1.2.1 桌面安装版的真人式全功能验收测试准备一套完整数据：
    多角色用户、认证/待认证团队、成员级别、入团申请、任务全状态、待办、
    子团队、协作关系与协作任务、通知、AI 配置与自动分配示例。

特性：
    1. 只使用标准库 urllib 走 HTTP API（不直连数据库，除管理员单条 DML 用于构造逾期数据）；
    2. 幂等：重复执行不会重复创建账号/团队/任务，已存在的账号/团队/任务会复用并补齐关系；
    3. --base-api 可配置，失败时打印明确的 HTTP 状态码、错误码与中文/英文错误信息。

运行：
    python scripts/seedQaAcceptanceData.py
    python scripts/seedQaAcceptanceData.py --base-api http://10.5.61.61:8765
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
QA_DOCS_DIRECTORY = PROJECT_ROOT_DIRECTORY / "docs" / "qa"
QA_STATE_DIRECTORY = PROJECT_ROOT_DIRECTORY / ".devdata" / "qa"
QA_PASSWORD = "Qa@123456"
QA_USERNAME_PREFIX = "qa"
DEFAULT_BASE_API = "http://127.0.0.1:8765"

# 用户清单：username / nickname / 用途说明 / 技能标签 [(标签名, 分类, 熟练度)]
QA_USER_SPECS = [
    {
        "username": "qaGlobalAdmin",
        "nickname": "QA Global Admin",
        "purpose": "全局管理员：管理后台概览、用户/团队认证、数据库只读浏览、AI 配置",
        "bio": "QA acceptance global administrator for admin console and system settings.",
        "skills": [("Project Management", "Management", 4), ("Requirements Analysis", "Product", 4)],
    },
    {
        "username": "qaTeamAdminA",
        "nickname": "QA Alpha Team Admin",
        "purpose": "QA Alpha Team 团队管理员：发布/修改/取消/审核任务、生成邀请码、管理成员级别",
        "bio": "Administrator of QA Alpha Team, responsible for task lifecycle and member management.",
        "skills": [("Backend Development", "Development", 5), ("Database Design", "Development", 4)],
    },
    {
        "username": "qaTeamAdminB",
        "nickname": "QA Beta Team Admin",
        "purpose": "QA Beta Team 团队管理员 + QA Gamma 待认证团队创建者：协作接收方管理员",
        "bio": "Administrator of QA Beta Team and creator of the pending QA Gamma Team.",
        "skills": [("Frontend Development", "Development", 5), ("Visual Design", "Design", 4)],
    },
    {
        "username": "qaSubAdminA",
        "nickname": "QA Alpha Sub-admin",
        "purpose": "QA Alpha Team 子管理员（自定义级别 QA Lead）：入团审核、邀请码、低级别成员管理",
        "bio": "Sub-admin of QA Alpha Team with the custom QA Lead level.",
        "skills": [("Testing & Quality", "Testing", 5), ("Test Automation", "Testing", 4)],
    },
    {
        "username": "qaMemberA1",
        "nickname": "QA Alpha Member One",
        "purpose": "QA Alpha Team 普通成员 / Frontend Squad 子负责人：待接受、进行中、已归档、AI 自动分配执行人",
        "bio": "Member of QA Alpha Team and lead of the Frontend Squad sub-team.",
        "skills": [("QA Automation", "Testing", 5), ("Backend Development", "Development", 4)],
    },
    {
        "username": "qaMemberA2",
        "nickname": "QA Alpha Member Two",
        "purpose": "QA Alpha Team 普通成员：逾期任务、待审核任务执行人；协作发起方对接人",
        "bio": "Member of QA Alpha Team and initiator liaison for cross-team collaboration.",
        "skills": [("Frontend Development", "Development", 4), ("Interaction Design", "Design", 3)],
    },
    {
        "username": "qaMemberB1",
        "nickname": "QA Beta Member One",
        "purpose": "QA Beta Team 普通成员（邀请码加入）：待办各状态、协作任务执行人",
        "bio": "Member of QA Beta Team who joined through an invite code.",
        "skills": [("Documentation", "General", 4), ("Testing & Quality", "Testing", 3)],
    },
    {
        "username": "qaMemberB2",
        "nickname": "QA Beta Member Two",
        "purpose": "QA Beta Team 普通成员：协作接收方对接人（接收方双审核）",
        "bio": "Member of QA Beta Team and receiver liaison for two-stage collaboration review.",
        "skills": [("Product Design", "Product", 4), ("Requirements Analysis", "Product", 3)],
    },
    {
        "username": "qaApplicantAlpha",
        "nickname": "QA Pending Applicant",
        "purpose": "非成员账号：对 QA Alpha Team 有一条待处理入团申请（用于入团审核测试）",
        "bio": "Applicant waiting for QA Alpha Team join request approval.",
        "skills": [("Data Analysis", "Data", 3)],
    },
    {
        "username": "qaDisabledUser",
        "nickname": "QA Disabled User",
        "purpose": "已禁用账号：登录返回 ACCOUNT_DISABLED（用于禁用账号与错误提示测试）",
        "bio": "Disabled account used to verify login rejection and admin user status.",
        "skills": [],
    },
]

# 团队清单：key / 名称 / 简介 / 加入方式 / 是否需要认证 / 创建者
QA_TEAM_SPECS = {
    "alpha": {
        "name": "QA Alpha Team",
        "description": "Certified team for QA acceptance: tasks, to-dos, sub-teams and collaboration initiator.",
        "joinMethod": "approval",
        "certify": True,
        "owner": "qaTeamAdminA",
    },
    "beta": {
        "name": "QA Beta Team",
        "description": "Certified team for QA acceptance: invite code join, collaboration receiver and review.",
        "joinMethod": "inviteOnly",
        "certify": True,
        "owner": "qaTeamAdminB",
    },
    "gamma": {
        "name": "QA Gamma Pending Team",
        "description": "Pending certification team for QA acceptance of the admin certification flow.",
        "joinMethod": "approval",
        "certify": False,
        "owner": "qaTeamAdminB",
    },
}

# Alpha 团队成员：username -> (role, levelOrder)
ALPHA_MEMBERS = [
    ("qaTeamAdminA", "admin", 3),
    ("qaSubAdminA", "subAdmin", 4),
    ("qaMemberA1", "member", 2),
    ("qaMemberA2", "member", 2),
]

# Beta 团队成员（邀请码加入）：username -> (role, levelOrder)
BETA_MEMBERS = [
    ("qaTeamAdminB", "admin", 3),
    ("qaMemberB1", "member", 1),
    ("qaMemberB2", "member", 1),
]

# 任务清单：team / title / 优先级 / 分配方式 / 接受方式 / 目标 / 期望状态 / 截止时间等
QA_TASK_SPECS = [
    {
        "team": "alpha",
        "title": "QA Alpha Optional Published Task",
        "description": "Optional task waiting for acceptance to verify pendingAcceptance to-dos.",
        "priority": "medium",
        "assignmentMode": "specific",
        "acceptanceMode": "optional",
        "targetUsers": ["qaMemberA1"],
        "dueInHours": 72,
        "desiredStatus": "published",
    },
    {
        "team": "alpha",
        "title": "QA Alpha In Progress Sub-team Task",
        "description": "Mandatory task inside the Frontend Squad sub-team to verify sub-team task visibility.",
        "priority": "high",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUsers": ["qaMemberA2"],
        "subTeam": "Frontend Squad",
        "dueInHours": 48,
        "desiredStatus": "inProgress",
    },
    {
        "team": "alpha",
        "title": "QA Alpha Overdue Task",
        "description": "Task whose due date is in the past, used to verify overdue to-dos and dashboard counters.",
        "priority": "urgent",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUsers": ["qaMemberA1"],
        "dueInHours": 24,
        "desiredStatus": "inProgress",
        "overdue": True,
    },
    {
        "team": "alpha",
        "title": "QA Alpha Pending Review Task",
        "description": "Task submitted by the assignee and waiting for publisher review.",
        "priority": "medium",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUsers": ["qaMemberA2"],
        "dueInHours": 48,
        "desiredStatus": "pendingReview",
        "submitBy": "qaMemberA2",
    },
    {
        "team": "alpha",
        "title": "QA Alpha Archived Task",
        "description": "Task fully reviewed and archived, contributing to archived counters and trends.",
        "priority": "low",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUsers": ["qaMemberA1"],
        "dueInHours": 48,
        "desiredStatus": "archived",
        "submitBy": "qaMemberA1",
        "reviewBy": "qaTeamAdminA",
        "enrichCreatedDaysAgo": 5,
        "enrichReviewedDaysAgo": 2,
    },
    {
        "team": "alpha",
        "title": "QA Alpha Cancelled Task",
        "description": "Task cancelled by the publisher to verify the cancelled status and terminal-state rules.",
        "priority": "high",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUsers": ["qaMemberA2"],
        "dueInHours": 72,
        "desiredStatus": "cancelled",
        "cancelBy": "qaTeamAdminA",
    },
    {
        "team": "alpha",
        "title": "QA Alpha Level Range Optional Task",
        "description": "Optional level-range task assigned to all Alpha members between level 1 and 2.",
        "priority": "high",
        "assignmentMode": "levelRange",
        "acceptanceMode": "optional",
        "targetLevelMin": 1,
        "targetLevelMax": 2,
        "dueInHours": 120,
        "desiredStatus": "published",
    },
    {
        "team": "alpha",
        "title": "QA Alpha AI Auto-assigned Task",
        "description": "Automated QA testing for backend services; AI should auto-assign the best matching member.",
        "priority": "high",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "autoAssign": True,
        "requiredSkillNames": ["QA Automation"],
        "targetLevelMin": 1,
        "targetLevelMax": 2,
        "dueInHours": 3,
        "desiredStatus": "inProgress",
        "aiAssigned": True,
    },
    {
        "team": "beta",
        "title": "QA Beta Optional Published Task",
        "description": "Optional task waiting for acceptance in QA Beta Team.",
        "priority": "medium",
        "assignmentMode": "specific",
        "acceptanceMode": "optional",
        "targetUsers": ["qaMemberB1"],
        "dueInHours": 96,
        "desiredStatus": "published",
    },
    {
        "team": "beta",
        "title": "QA Beta In Progress Task",
        "description": "Mandatory in-progress task owned by a Beta member.",
        "priority": "high",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUsers": ["qaMemberB2"],
        "dueInHours": 48,
        "desiredStatus": "inProgress",
    },
    {
        "team": "beta",
        "title": "QA Beta Pending Review Task",
        "description": "Task submitted by the assignee and waiting for Beta admin review.",
        "priority": "low",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUsers": ["qaMemberB1"],
        "dueInHours": 24,
        "desiredStatus": "pendingReview",
        "submitBy": "qaMemberB1",
    },
    {
        "team": "beta",
        "title": "QA Beta Archived Task",
        "description": "Task fully reviewed and archived in QA Beta Team.",
        "priority": "medium",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUsers": ["qaMemberB2"],
        "dueInHours": 48,
        "desiredStatus": "archived",
        "submitBy": "qaMemberB2",
        "reviewBy": "qaTeamAdminB",
        "enrichCreatedDaysAgo": 3,
        "enrichReviewedDaysAgo": 1,
    },
    {
        "team": "beta",
        "title": "QA Beta Cancelled Task",
        "description": "Cancelled task to verify terminal-state handling in QA Beta Team.",
        "priority": "urgent",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "targetUsers": ["qaMemberB1"],
        "dueInHours": 72,
        "desiredStatus": "cancelled",
        "cancelBy": "qaTeamAdminB",
    },
    {
        "team": "beta",
        "title": "QA Beta Level Range Task",
        "description": "Mandatory level-range task assigned to all Beta members at level 1 and 2.",
        "priority": "medium",
        "assignmentMode": "levelRange",
        "acceptanceMode": "mandatory",
        "targetLevelMin": 1,
        "targetLevelMax": 2,
        "dueInHours": 120,
        "desiredStatus": "inProgress",
    },
    {
        "team": "beta",
        "title": "QA Beta Manual Assign Task",
        "description": "AI auto-assignment fails on purpose, then the Beta admin assigns an assignee manually.",
        "priority": "low",
        "assignmentMode": "specific",
        "acceptanceMode": "mandatory",
        "autoAssign": True,
        "requiredSkillNames": ["Skill That Does Not Exist"],
        "dueInHours": 168,
        "desiredStatus": "inProgress",
        "manualAssign": "qaMemberB1",
    },
]

COLLABORATION_TASK_SPECS = [
    {
        "title": "QA Collaboration Pending Confirmation Task",
        "description": "Collaboration task waiting for the receiver to confirm and pick an assignee.",
        "priority": "high",
        "desiredPhase": "pendingConfirmation",
    },
    {
        "title": "QA Collaboration Executing Task",
        "description": "Collaboration task accepted and executing in the receiver team.",
        "priority": "medium",
        "desiredPhase": "executing",
    },
    {
        "title": "QA Collaboration Target Review Task",
        "description": "Collaboration task submitted by the assignee and waiting for receiver review.",
        "priority": "urgent",
        "desiredPhase": "targetReview",
    },
]


class ApiError(Exception):
    """HTTP API 业务错误：携带状态码、错误码与错误信息。"""

    def __init__(self, method: str, path: str, statusCode: int, code: str, message: str) -> None:
        self.method = method
        self.path = path
        self.statusCode = statusCode
        self.code = code
        self.message = message
        super().__init__(f"{method} {path} -> HTTP {statusCode} [{code}] {message}")


class ApiClient:
    """已安装应用的 HTTP API 客户端（标准库 urllib 实现，带 token 缓存）。"""

    def __init__(self, baseApi: str) -> None:
        """规范化 base API 地址并初始化 token 缓存。"""
        self.baseApi = baseApi.rstrip("/")
        self.tokens: dict[str, str] = {}

    def request(self, method: str, path: str, token: str | None = None, body: dict | None = None):
        """发送请求并解析 JSON；非 2xx 统一抛出 ApiError。"""
        url = self.baseApi + "/api/v1" + path
        requestData = None if body is None else json.dumps(body).encode("utf-8")
        httpRequest = urllib.request.Request(url, data=requestData, method=method)
        httpRequest.add_header("Content-Type", "application/json")
        if token:
            httpRequest.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(httpRequest, timeout=30) as response:
                responseText = response.read().decode("utf-8")
                return json.loads(responseText) if responseText else None
        except urllib.error.HTTPError as httpError:
            errorText = httpError.read().decode("utf-8", errors="replace")
            try:
                errorPayload = json.loads(errorText)
            except json.JSONDecodeError:
                errorPayload = {"code": "HTTP_ERROR", "message": errorText[:300]}
            raise ApiError(
                method, path, httpError.code, errorPayload.get("code", "HTTP_ERROR"), errorPayload.get("message", "")
            ) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as connectionError:
            reason = getattr(connectionError, "reason", connectionError)
            raise ApiError(
                method, path, 0, "NETWORK_ERROR", "cannot reach the application API: " + str(reason)
            ) from None

    def login(self, username: str, password: str) -> dict:
        """登录并缓存 token，返回登录响应。"""
        loginResult = self.request("POST", "/auth/login", body={"username": username, "password": password})
        self.tokens[username] = loginResult["token"]
        return loginResult

    def token(self, username: str, password: str = QA_PASSWORD) -> str:
        """获取用户 token：优先缓存，未登录时执行登录。"""
        if username not in self.tokens:
            self.login(username, password)
        return self.tokens[username]


def printSection(title: str) -> None:
    """打印阶段标题，便于长流程日志阅读。"""
    print("\n[seed] " + title)


def formatDateTime(moment: datetime) -> str:
    """格式化 API 使用的本地 ISO 时间字符串。"""
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def formatSqlDateTime(moment: datetime) -> str:
    """格式化管理员单条 DML 使用的 MySQL DATETIME 字符串。"""
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def queryPath(path: str, **queryArguments) -> str:
    """拼接带查询参数的路径（自动忽略 None 值）。"""
    filteredArguments = {key: value for key, value in queryArguments.items() if value is not None}
    if not filteredArguments:
        return path
    return path + "?" + urllib.parse.urlencode(filteredArguments)


# ===== 用户相关 =====


def find_user_by_username(client: ApiClient, superAdminToken: str, username: str) -> dict | None:
    """通过管理后台用户列表按用户名精确查找用户。"""
    pageResult = client.request(
        "GET", queryPath("/admin/users", keyword=username, page=1, pageSize=100), token=superAdminToken
    )
    for userItem in pageResult["items"]:
        if userItem["username"] == username:
            return userItem
    return None


def ensure_user(client: ApiClient, superAdminToken: str, userSpec: dict) -> dict:
    """幂等创建或复用用户，设置资料与技能，返回 {id, token, ...} 字典。"""
    username = userSpec["username"]
    existingUser = find_user_by_username(client, superAdminToken, username)
    if existingUser is None:
        registerResult = client.request(
            "POST",
            "/auth/register",
            body={
                "username": username,
                "password": QA_PASSWORD,
                "nickname": userSpec["nickname"],
                "email": username + "@qa.example.com",
            },
        )
        userId = registerResult["user"]["user"]["id"]
        userToken = registerResult["token"]
        client.tokens[username] = userToken
        print("  created user: " + username)
    else:
        userId = existingUser["id"]
        if existingUser["isActive"]:
            userToken = client.token(username)
        else:
            userToken = None
        print("  reused user: " + username)

    if userToken is not None:
        client.request(
            "PUT",
            "/users/me",
            token=userToken,
            body={
                "nickname": userSpec["nickname"],
                "email": username + "@qa.example.com",
                "bio": userSpec["bio"],
            },
        )
        ensure_user_skills(client, userToken, userSpec["skills"])
    return {"id": userId, "username": username, "token": userToken, "nickname": userSpec["nickname"]}


def list_skill_tags(client: ApiClient, token: str) -> dict[str, dict]:
    """读取全部技能标签，返回 {标签名: 标签} 字典。"""
    tags = client.request("GET", "/skill-tags", token=token)
    return {tag["name"]: tag for tag in tags}


def ensure_skill_tag(client: ApiClient, token: str, tagName: str, category: str) -> dict:
    """按名称幂等获取技能标签，不存在时创建。"""
    tags = list_skill_tags(client, token)
    if tagName in tags:
        return tags[tagName]
    createdTag = client.request(
        "POST", "/users/me/skills/tags", token=token, body={"name": tagName, "category": category}
    )
    print("  created skill tag: " + tagName)
    return createdTag


def ensure_user_skills(client: ApiClient, token: str, skillDefinitions: list[tuple[str, str, int]]) -> None:
    """覆盖式保存用户技能（技能标签不存在时自动创建）。"""
    skillsPayload = []
    for tagName, category, proficiency in skillDefinitions:
        skillTag = ensure_skill_tag(client, token, tagName, category)
        skillsPayload.append({"skillTagId": skillTag["id"], "proficiency": proficiency})
    client.request("PUT", "/users/me/skills", token=token, body={"skills": skillsPayload})


def ensure_global_admin(client: ApiClient, superAdminToken: str, targetUser: dict) -> None:
    """把用户提升为全局管理员（幂等）。"""
    client.request(
        "PUT",
        "/admin/users/" + str(targetUser["id"]) + "/global-role",
        token=superAdminToken,
        body={"globalRole": "globalAdmin"},
    )


def ensure_user_disabled(client: ApiClient, superAdminToken: str, targetUser: dict) -> None:
    """禁用用户账号（幂等）。"""
    client.request(
        "PUT",
        "/admin/users/" + str(targetUser["id"]) + "/status",
        token=superAdminToken,
        body={"isActive": False},
    )


# ===== 团队相关 =====


def find_team_by_name(client: ApiClient, superAdminToken: str, teamName: str) -> dict | None:
    """通过管理后台团队列表按名称精确查找团队。"""
    pageResult = client.request(
        "GET", queryPath("/admin/teams", keyword=teamName, page=1, pageSize=100), token=superAdminToken
    )
    for teamItem in pageResult["items"]:
        if teamItem["name"] == teamName:
            return teamItem
    return None


def get_team_detail(client: ApiClient, adminToken: str, teamId: int) -> dict:
    """读取团队详情（级别与成员）。"""
    return client.request("GET", "/teams/" + str(teamId), token=adminToken)


def certify_team(client: ApiClient, superAdminToken: str, teamId: int) -> None:
    """超级用户通过团队认证。"""
    client.request(
        "PUT",
        "/admin/teams/" + str(teamId) + "/certification",
        token=superAdminToken,
        body={"approved": True},
    )


def ensure_team(client: ApiClient, superAdminToken: str, teamSpec: dict, ownerToken: str) -> dict:
    """幂等创建或复用团队，并按需认证，返回团队详情。"""
    teamName = teamSpec["name"]
    existingTeam = find_team_by_name(client, superAdminToken, teamName)
    if existingTeam is None:
        createdTeam = client.request(
            "POST",
            "/teams",
            token=ownerToken,
            body={
                "name": teamName,
                "description": teamSpec["description"],
                "joinMethod": teamSpec["joinMethod"],
            },
        )
        teamId = createdTeam["id"]
        print("  created team: " + teamName + " (id=" + str(teamId) + ")")
    else:
        teamId = existingTeam["id"]
        print("  reused team: " + teamName + " (id=" + str(teamId) + ")")
    teamDetail = get_team_detail(client, ownerToken, teamId)
    if teamSpec["certify"] and teamDetail["status"] != "active":
        certify_team(client, superAdminToken, teamId)
        print("  certified team: " + teamName)
        teamDetail = get_team_detail(client, ownerToken, teamId)
    return teamDetail


def ensure_team_level(
    client: ApiClient, adminToken: str, teamId: int, levelName: str, levelOrder: int, canCreateTask: bool
) -> dict:
    """幂等创建或更新自定义成员级别，返回更新后的团队详情。"""
    teamDetail = get_team_detail(client, adminToken, teamId)
    existingLevel = next((level for level in teamDetail["levels"] if level["levelOrder"] == levelOrder), None)
    if existingLevel is None:
        client.request(
            "POST",
            "/teams/" + str(teamId) + "/levels",
            token=adminToken,
            body={"name": levelName, "levelOrder": levelOrder, "canCreateTask": canCreateTask},
        )
        print("  created custom level: " + levelName)
    elif existingLevel["name"] != levelName:
        client.request(
            "PUT",
            "/teams/" + str(teamId) + "/levels/" + str(existingLevel["id"]),
            token=adminToken,
            body={"name": levelName, "levelOrder": levelOrder, "canCreateTask": canCreateTask},
        )
        print("  updated custom level: " + levelName)
    return get_team_detail(client, adminToken, teamId)


def list_team_members(client: ApiClient, adminToken: str, teamId: int) -> list[dict]:
    """读取团队成员列表。"""
    return client.request("GET", "/teams/" + str(teamId) + "/members", token=adminToken)


def ensure_invite_code(client: ApiClient, adminToken: str, teamId: int) -> dict:
    """生成团队邀请码（每次新生成，供邀请加入测试使用）。"""
    return client.request(
        "POST",
        "/teams/" + str(teamId) + "/invite-code",
        token=adminToken,
        body={"expiresInHours": 168, "maxUses": 20},
    )


def ensure_team_membership(
    client: ApiClient,
    teamDetail: dict,
    adminToken: str,
    joinMethod: str,
    targetUser: dict,
) -> None:
    """幂等保证用户是团队成员：approval 走申请+审批，inviteOnly 走邀请码加入。"""
    teamId = teamDetail["id"]
    members = list_team_members(client, adminToken, teamId)
    if any(member["userId"] == targetUser["id"] for member in members):
        return
    targetToken = targetUser["token"]
    if targetToken is None:
        raise RuntimeError("目标用户已禁用，无法加入团队：" + targetUser["username"])
    if joinMethod == "approval":
        pendingRequests = client.request("GET", "/teams/" + str(teamId) + "/join-requests", token=adminToken)
        pendingRequest = next(
            (item for item in pendingRequests if item["userId"] == targetUser["id"]), None
        )
        if pendingRequest is None:
            client.request(
                "POST",
                "/teams/join",
                token=targetToken,
                body={"teamId": teamId, "message": "QA acceptance data: please approve this join request."},
            )
            pendingRequests = client.request(
                "GET", "/teams/" + str(teamId) + "/join-requests", token=adminToken
            )
            pendingRequest = next(
                (item for item in pendingRequests if item["userId"] == targetUser["id"]), None
            )
        if pendingRequest is not None:
            client.request(
                "PUT",
                "/teams/" + str(teamId) + "/join-requests/" + str(pendingRequest["id"]),
                token=adminToken,
                body={"action": "approve"},
            )
    elif joinMethod == "inviteOnly":
        inviteCodeData = ensure_invite_code(client, adminToken, teamId)
        client.request("POST", "/teams/join", token=targetToken, body={"inviteCode": inviteCodeData["inviteCode"]})
    elif joinMethod == "free":
        client.request("POST", "/teams/join", token=targetToken, body={"teamId": teamId})
    print("  joined member: " + targetUser["username"] + " -> " + teamDetail["name"])


def ensure_member_role_and_level(
    client: ApiClient,
    adminToken: str,
    teamDetail: dict,
    targetUser: dict,
    role: str,
    levelOrder: int,
) -> None:
    """幂等设置团队成员的角色与级别。"""
    teamId = teamDetail["id"]
    members = list_team_members(client, adminToken, teamId)
    member = next((item for item in members if item["userId"] == targetUser["id"]), None)
    if member is None:
        raise RuntimeError("成员不存在，无法设置角色/级别：" + targetUser["username"])
    if member["role"] != role:
        client.request(
            "PUT",
            "/teams/" + str(teamId) + "/members/" + str(targetUser["id"]) + "/role",
            token=adminToken,
            body={"role": role},
        )
        print("  set role: " + targetUser["username"] + " -> " + role)
    teamDetailAfter = get_team_detail(client, adminToken, teamId)
    level = next((item for item in teamDetailAfter["levels"] if item["levelOrder"] == levelOrder), None)
    if level is None:
        raise RuntimeError("目标级别不存在：" + str(levelOrder))
    if member["levelId"] != level["id"]:
        client.request(
            "PUT",
            "/teams/" + str(teamId) + "/members/" + str(targetUser["id"]) + "/level",
            token=adminToken,
            body={"levelId": level["id"]},
        )
        print("  set level: " + targetUser["username"] + " -> " + level["name"])


# ===== 子团队 / 任务 / 协作相关 =====


def list_sub_teams(client: ApiClient, token: str, teamId: int) -> list[dict]:
    """读取团队子团队列表。"""
    return client.request("GET", "/teams/" + str(teamId) + "/sub-teams", token=token)


def ensure_sub_team(
    client: ApiClient,
    adminToken: str,
    teamId: int,
    subTeamName: str,
    description: str,
    leaderUserId: int,
    memberUserIds: list[int],
) -> dict:
    """幂等创建或更新子团队（负责人 + 成员）。"""
    existingSubTeam = next(
        (item for item in list_sub_teams(client, adminToken, teamId) if item["name"] == subTeamName), None
    )
    if existingSubTeam is None:
        createdSubTeam = client.request(
            "POST",
            "/teams/" + str(teamId) + "/sub-teams",
            token=adminToken,
            body={
                "name": subTeamName,
                "description": description,
                "leaderUserId": leaderUserId,
                "memberUserIds": memberUserIds,
            },
        )
        print("  created sub-team: " + subTeamName)
        return createdSubTeam
    client.request(
        "PUT",
        "/teams/" + str(teamId) + "/sub-teams/" + str(existingSubTeam["id"]),
        token=adminToken,
        body={"leaderUserId": leaderUserId},
    )
    updatedSubTeam = client.request(
        "PUT",
        "/teams/" + str(teamId) + "/sub-teams/" + str(existingSubTeam["id"]) + "/members",
        token=adminToken,
        body={"userIds": memberUserIds},
    )
    print("  updated sub-team: " + subTeamName)
    return updatedSubTeam


def find_team_task(client: ApiClient, token: str, teamId: int, title: str) -> dict | None:
    """在团队任务列表中按标题精确查找任务（幂等复用）。"""
    pageResult = client.request(
        "GET",
        queryPath("/teams/" + str(teamId) + "/tasks", keyword=title, page=1, pageSize=100),
        token=token,
    )
    for taskItem in pageResult["items"]:
        if taskItem["title"] == title:
            return taskItem
    return None


def create_team_task(
    client: ApiClient,
    creatorToken: str,
    teamId: int,
    taskSpec: dict,
    userIdByUsername: dict[str, int],
    subTeamId: int | None,
) -> dict:
    """按任务规格调用发布任务接口。"""
    dueAt = formatDateTime(datetime.now() + timedelta(hours=taskSpec["dueInHours"]))
    requestBody: dict = {
        "title": taskSpec["title"],
        "description": taskSpec.get("description"),
        "priority": taskSpec["priority"],
        "dueAt": dueAt,
        "assignmentMode": taskSpec["assignmentMode"],
        "acceptanceMode": taskSpec["acceptanceMode"],
    }
    if taskSpec.get("targetUsers"):
        requestBody["targetUserIds"] = [
            userIdByUsername[username] for username in taskSpec["targetUsers"]
        ]
    if taskSpec.get("targetLevelMin") is not None:
        requestBody["targetLevelMin"] = taskSpec["targetLevelMin"]
        requestBody["targetLevelMax"] = taskSpec["targetLevelMax"]
    if subTeamId is not None:
        requestBody["subTeamId"] = subTeamId
    if taskSpec.get("autoAssign"):
        requestBody["autoAssign"] = True
        requestBody["requiredSkillNames"] = taskSpec["requiredSkillNames"]
    return client.request("POST", "/teams/" + str(teamId) + "/tasks", token=creatorToken, body=requestBody)


def submit_task(client: ApiClient, token: str, taskId: int) -> dict:
    """执行人提交完成。"""
    return client.request("POST", "/tasks/" + str(taskId) + "/submit", token=token)


def review_task(client: ApiClient, token: str, taskId: int, assignmentUserId: int) -> dict:
    """发布者审核通过（归档）。"""
    return client.request(
        "POST",
        "/tasks/" + str(taskId) + "/review",
        token=token,
        body={"assignmentUserId": assignmentUserId, "approved": True, "comment": "QA acceptance: review approved."},
    )


def cancel_task(client: ApiClient, token: str, taskId: int) -> dict:
    """发布者取消任务。"""
    return client.request("POST", "/tasks/" + str(taskId) + "/cancel", token=token)


def assign_task_members(client: ApiClient, token: str, taskId: int, userIds: list[int]) -> dict:
    """手动指派执行人。"""
    return client.request(
        "POST", "/tasks/" + str(taskId) + "/assignments", token=token, body={"userIds": userIds}
    )


def advance_task_to_status(
    client: ApiClient,
    task: dict,
    taskSpec: dict,
    tokensByUsername: dict[str, str],
    userIdByUsername: dict[str, int],
    creatorUsername: str,
) -> dict:
    """按期望状态推进任务（幂等：已达到期望状态时跳过）。"""
    desiredStatus = taskSpec["desiredStatus"]
    currentStatus = task["status"]
    if desiredStatus in ("published", "inProgress") or currentStatus == desiredStatus:
        return task
    if desiredStatus == "pendingReview":
        if currentStatus == "inProgress":
            task = submit_task(client, tokensByUsername[taskSpec["submitBy"]], task["id"])
        if task["status"] != "pendingReview":
            raise RuntimeError("任务未能进入待审核状态：" + task["title"])
        return task
    if desiredStatus == "archived":
        if task["status"] == "inProgress":
            task = submit_task(client, tokensByUsername[taskSpec["submitBy"]], task["id"])
        if task["status"] == "pendingReview":
            assignmentUserId = userIdByUsername[taskSpec["submitBy"]]
            task = review_task(client, tokensByUsername[taskSpec["reviewBy"]], task["id"], assignmentUserId)
        if task["status"] != "archived":
            raise RuntimeError("任务未能归档：" + task["title"])
        return task
    if desiredStatus == "cancelled":
        if task["status"] != "cancelled":
            task = cancel_task(client, tokensByUsername[taskSpec["cancelBy"]], task["id"])
        if task["status"] != "cancelled":
            raise RuntimeError("任务未能取消：" + task["title"])
        return task
    raise RuntimeError("不支持的任务期望状态：" + desiredStatus)


def ensure_team_task(
    client: ApiClient,
    teamDetail: dict,
    taskSpec: dict,
    tokensByUsername: dict[str, str],
    userIdByUsername: dict[str, int],
    usernameByUserId: dict[int, str],
    subTeamIdByName: dict[str, int],
) -> dict:
    """幂等创建任务并推进到期望状态；处理 AI 自动分配与手动指派任务。"""
    teamId = teamDetail["id"]
    ownerUsername = QA_TEAM_SPECS[taskSpec["team"]]["owner"]
    ownerToken = tokensByUsername[ownerUsername]
    task = find_team_task(client, ownerToken, teamId, taskSpec["title"])
    if task is None:
        subTeamId = subTeamIdByName.get(taskSpec.get("subTeam")) if taskSpec.get("subTeam") else None
        task = create_team_task(
            client, ownerToken, teamId, taskSpec, userIdByUsername, subTeamId
        )
        print("  created task: " + taskSpec["title"] + " (status=" + task["status"] + ")")
    else:
        print("  reused task: " + taskSpec["title"] + " (status=" + task["status"] + ")")

    if taskSpec.get("aiAssigned"):
        if not task.get("autoAssigned") or not task.get("assignments"):
            raise RuntimeError(
                "AI 自动分配未成功（请检查 AI 配置与技能标签）：" + taskSpec["title"] + " autoAssigned=" + str(task.get("autoAssigned"))
            )
        if task["assignments"][0]["assignmentSource"] != "ai":
            raise RuntimeError("AI 任务未使用 ai 分配来源：" + taskSpec["title"])

    if taskSpec.get("manualAssign"):
        if not task.get("assignments"):
            assigneeUserId = userIdByUsername[taskSpec["manualAssign"]]
            task = assign_task_members(client, ownerToken, task["id"], [assigneeUserId])
            print("  manual assigned task: " + taskSpec["title"] + " -> " + taskSpec["manualAssign"])

    task = advance_task_to_status(client, task, taskSpec, tokensByUsername, userIdByUsername, ownerUsername)

    if taskSpec.get("overdue"):
        ensure_task_overdue(client, tokensByUsername["__superAdmin__"], teamId, task["id"])

    if taskSpec.get("enrichCreatedDaysAgo") is not None:
        enrich_task_timeline(
            client,
            tokensByUsername["__superAdmin__"],
            task["id"],
            taskSpec["enrichCreatedDaysAgo"],
            taskSpec.get("enrichReviewedDaysAgo"),
            userIdByUsername.get(taskSpec.get("submitBy", "")),
        )
    return task


def ensure_task_overdue(client: ApiClient, superAdminToken: str, teamId: int, taskId: int) -> None:
    """通过管理员单条 DML 把任务截止时间改为两天前，构造已逾期数据（公开接口禁止创建过期任务）。"""
    dueAtText = formatSqlDateTime(datetime.now() - timedelta(days=2))
    sqlText = (
        "UPDATE tasks SET due_at = '" + dueAtText + "' WHERE id = " + str(taskId) + " AND team_id = " + str(teamId)
    )
    execute_admin_sql(client, superAdminToken, sqlText)


def enrich_task_timeline(
    client: ApiClient,
    superAdminToken: str,
    taskId: int,
    createdDaysAgo: int,
    reviewedDaysAgo: int | None,
    assigneeUserId: int | None,
) -> None:
    """通过管理员单条 DML 调整任务创建/审核时间，让仪表盘近七日趋势有跨天数据。"""
    createdAtText = formatSqlDateTime(datetime.now() - timedelta(days=createdDaysAgo))
    execute_admin_sql(
        client,
        superAdminToken,
        "UPDATE tasks SET created_at = '" + createdAtText + "' WHERE id = " + str(taskId),
    )
    if reviewedDaysAgo is not None and assigneeUserId is not None:
        reviewedAtText = formatSqlDateTime(datetime.now() - timedelta(days=reviewedDaysAgo))
        execute_admin_sql(
            client,
            superAdminToken,
            "UPDATE task_assignments SET reviewed_at = '"
            + reviewedAtText
            + "', submitted_at = '"
            + reviewedAtText
            + "' WHERE task_id = "
            + str(taskId)
            + " AND user_id = "
            + str(assigneeUserId),
        )


def execute_admin_sql(client: ApiClient, superAdminToken: str, sqlText: str) -> None:
    """调用管理后台数据库直管接口执行单条 DML（失败只告警，不阻断种子流程）。"""
    try:
        client.request(
            "POST", "/admin/database/execute", token=superAdminToken, body={"sql": sqlText, "confirm": True}
        )
    except ApiError as error:
        print("  WARN admin SQL skipped: " + str(error))

# ===== 协作相关 =====


def list_collaborations(client: ApiClient, token: str, status: str | None = None) -> list[dict]:
    """读取当前用户可见的协作列表（可按状态过滤）。"""
    pageResult = client.request(
        "GET", queryPath("/collaborations", status=status, page=1, pageSize=100), token=token
    )
    return pageResult["items"]


def find_unit_collaboration(
    client: ApiClient, tokens: list[str], initiatorTeamId: int, targetTeamId: int, initiatorSubTeamId: int | None
) -> dict | None:
    """在多个用户的协作列表中查找指定发起/接收单位的协作。"""
    seenIds: set[int] = set()
    for token in tokens:
        for collaborationItem in list_collaborations(client, token):
            collaborationId = collaborationItem["id"]
            if collaborationId in seenIds:
                continue
            seenIds.add(collaborationId)
            initiatorUnit = collaborationItem["initiatorUnit"]
            targetUnit = collaborationItem["targetUnit"]
            if initiatorUnit["teamId"] != initiatorTeamId or targetUnit["teamId"] != targetTeamId:
                continue
            if initiatorUnit["subTeamId"] != initiatorSubTeamId:
                continue
            if targetUnit["subTeamId"] is not None:
                continue
            return collaborationItem
    return None


def confirm_collaboration(
    client: ApiClient, targetAdminToken: str, collaborationId: int, targetLiaisonUserId: int
) -> dict:
    """接收方管理员确认协作并指定接收方对接人。"""
    return client.request(
        "POST",
        "/collaborations/" + str(collaborationId) + "/confirm",
        token=targetAdminToken,
        body={
            "approved": True,
            "targetLiaisonUserId": targetLiaisonUserId,
            "comment": "QA acceptance: collaboration confirmed.",
        },
    )


def ensure_active_collaboration(
    client: ApiClient,
    initiatorAdminToken: str,
    initiatorLiaisonToken: str,
    targetAdminToken: str,
    targetLiaisonUserId: int,
    initiatorTeamId: int,
    targetTeamId: int,
    initiatorLiaisonUserId: int,
) -> dict:
    """幂等建立两个认证团队之间的 active 协作关系。"""
    existingCollaboration = find_unit_collaboration(
        client, [initiatorAdminToken, targetAdminToken, initiatorLiaisonToken], initiatorTeamId, targetTeamId, None
    )
    if existingCollaboration is not None:
        if existingCollaboration["status"] == "active":
            print("  reused active collaboration: id=" + str(existingCollaboration["id"]))
            return existingCollaboration
        if existingCollaboration["status"] == "pending":
            confirmedCollaboration = confirm_collaboration(
                client, targetAdminToken, existingCollaboration["id"], targetLiaisonUserId
            )
            print("  confirmed pending collaboration: id=" + str(existingCollaboration["id"]))
            return confirmedCollaboration
    createdCollaboration = client.request(
        "POST",
        "/collaborations",
        token=initiatorAdminToken,
        body={
            "initiatorTeamId": initiatorTeamId,
            "targetTeamId": targetTeamId,
            "initiatorLiaisonUserId": initiatorLiaisonUserId,
            "message": "QA acceptance data: collaboration request from QA Alpha Team.",
        },
    )
    confirmedCollaboration = confirm_collaboration(
        client, targetAdminToken, createdCollaboration["id"], targetLiaisonUserId
    )
    print("  created active collaboration: id=" + str(confirmedCollaboration["id"]))
    return confirmedCollaboration


def ensure_pending_collaboration(
    client: ApiClient,
    initiatorToken: str,
    initiatorAdminToken: str,
    initiatorTeamId: int,
    initiatorSubTeamId: int,
    targetTeamId: int,
    initiatorLiaisonUserId: int,
) -> dict | None:
    """幂等建立一条待确认（pending）协作关系：子团队作为发起单位。"""
    existingCollaboration = find_unit_collaboration(
        client, [initiatorToken, initiatorAdminToken], initiatorTeamId, targetTeamId, initiatorSubTeamId
    )
    if existingCollaboration is not None:
        print(
            "  reused collaboration: id=" + str(existingCollaboration["id"])
            + " status=" + existingCollaboration["status"]
        )
        return existingCollaboration
    createdCollaboration = client.request(
        "POST",
        "/collaborations",
        token=initiatorToken,
        body={
            "initiatorTeamId": initiatorTeamId,
            "initiatorSubTeamId": initiatorSubTeamId,
            "targetTeamId": targetTeamId,
            "initiatorLiaisonUserId": initiatorLiaisonUserId,
            "message": "QA acceptance data: pending collaboration request from the Frontend Squad sub-team.",
        },
    )
    print("  created pending collaboration: id=" + str(createdCollaboration["id"]))
    return createdCollaboration


def list_collaboration_tasks(client: ApiClient, token: str, collaborationId: int) -> list[dict]:
    """读取协作关系下的协作任务列表。"""
    pageResult = client.request(
        "GET",
        queryPath("/collaborations/" + str(collaborationId) + "/tasks", page=1, pageSize=100),
        token=token,
    )
    return pageResult["items"]


def create_collaboration_task(
    client: ApiClient, token: str, collaborationId: int, taskSpec: dict
) -> dict:
    """发起方创建协作任务（默认进入 pendingConfirmation 阶段）。"""
    dueAt = formatDateTime(datetime.now() + timedelta(hours=72))
    return client.request(
        "POST",
        "/collaborations/" + str(collaborationId) + "/tasks",
        token=token,
        body={
            "title": taskSpec["title"],
            "description": taskSpec["description"],
            "priority": taskSpec["priority"],
            "dueAt": dueAt,
            "acceptanceMode": "mandatory",
        },
    )


def confirm_collaboration_task(
    client: ApiClient, token: str, taskId: int, assigneeUserId: int
) -> dict:
    """接收方确认接单并指派执行人。"""
    return client.request(
        "POST",
        "/collaboration-tasks/" + str(taskId) + "/confirm",
        token=token,
        body={"approved": True, "assigneeUserIds": [assigneeUserId], "comment": "QA acceptance: task accepted."},
    )


def call_with_token_fallback(
    client: ApiClient,
    requestFactory,
    primaryToken: str,
    fallbackToken: str,
):
    """先用主 token 调用，403 时改用备用 token（对接人与管理员权限差异兜底）。"""
    try:
        return requestFactory(primaryToken)
    except ApiError as apiError:
        if apiError.statusCode != 403:
            raise
        return requestFactory(fallbackToken)


def ensure_collaboration_task(
    client: ApiClient,
    collaboration: dict,
    taskSpec: dict,
    initiatorLiaisonToken: str,
    initiatorAdminToken: str,
    initiatorLiaisonUserId: int,
    targetLiaisonToken: str,
    targetAdminToken: str,
    assigneeUserId: int,
    assigneeToken: str,
    skippedItems: list[str],
) -> dict | None:
    """幂等创建协作任务并推进到期望阶段（pendingConfirmation/executing/targetReview）。"""
    collaborationId = collaboration["id"]
    existingTask = next(
        (
            item
            for item in list_collaboration_tasks(client, initiatorLiaisonToken, collaborationId)
            if item["title"] == taskSpec["title"]
        ),
        None,
    )
    if existingTask is None:
        existingTask = call_with_token_fallback(
            client,
            lambda token: create_collaboration_task(client, token, collaborationId, taskSpec),
            initiatorLiaisonToken,
            initiatorAdminToken,
        )
        print(
            "  created collaboration task: " + taskSpec["title"]
            + " phase=" + str(existingTask.get("collaborationPhase"))
        )
    else:
        print(
            "  reused collaboration task: " + taskSpec["title"]
            + " phase=" + str(existingTask.get("collaborationPhase"))
        )

    desiredPhase = taskSpec["desiredPhase"]
    if desiredPhase == "pendingConfirmation" or existingTask.get("collaborationPhase") == desiredPhase:
        return existingTask

    if existingTask.get("collaborationPhase") == "pendingConfirmation":
        confirmedTask = call_with_token_fallback(
            client,
            lambda token: confirm_collaboration_task(client, token, existingTask["id"], assigneeUserId),
            targetLiaisonToken,
            targetAdminToken,
        )
        existingTask = confirmedTask

    if desiredPhase == "executing":
        return existingTask

    if desiredPhase == "targetReview":
        if existingTask.get("collaborationPhase") == "executing":
            existingTask = submit_task(client, assigneeToken, existingTask["id"])
        if existingTask.get("collaborationPhase") != "targetReview":
            skippedItems.append(
                "协作任务未进入 targetReview 阶段：" + taskSpec["title"]
                + " phase=" + str(existingTask.get("collaborationPhase"))
            )
        return existingTask

    skippedItems.append("未知协作任务目标阶段：" + desiredPhase)
    return existingTask


# ===== 通知相关 =====


def list_notifications(client: ApiClient, token: str, pageSize: int = 50) -> dict:
    """读取当前用户通知列表。"""
    return client.request(
        "GET", queryPath("/notifications", page=1, pageSize=pageSize), token=token
    )


def mark_notifications_read(client: ApiClient, token: str, readCount: int = 1) -> int:
    """把用户最新若干条未读通知标记为已读，返回实际标记数量。"""
    notificationPage = list_notifications(client, token)
    unreadItems = [item for item in notificationPage["items"] if not item["readFlag"]]
    markedCount = 0
    for notificationItem in unreadItems[:readCount]:
        client.request("PUT", "/notifications/" + str(notificationItem["id"]) + "/read", token=token)
        markedCount += 1
    return markedCount


def ensure_some_read_notifications(client: ApiClient, token: str) -> int:
    """幂等保证用户至少有一条已读通知：仅当完全没有已读通知时标记 1 条。"""
    notificationPage = list_notifications(client, token)
    existingReadCount = sum(1 for item in notificationPage["items"] if item["readFlag"])
    if existingReadCount > 0:
        return 0
    return mark_notifications_read(client, token, 1)


def get_unread_notification_count(client: ApiClient, token: str) -> int:
    """读取未读通知数量。"""
    countResult = client.request("GET", "/notifications/unread-count", token=token)
    return int(countResult["count"])


# ===== 入团申请 =====


def ensure_pending_join_request(
    client: ApiClient, adminToken: str, teamDetail: dict, targetUser: dict, skippedItems: list[str]
) -> bool:
    """保证目标用户对该团队有一条待处理入团申请（不审批通过）。"""
    teamId = teamDetail["id"]
    members = list_team_members(client, adminToken, teamId)
    if any(member["userId"] == targetUser["id"] for member in members):
        skippedItems.append("入团申请账号意外已是团队成员，已跳过申请：" + targetUser["username"])
        return False
    pendingRequests = client.request("GET", "/teams/" + str(teamId) + "/join-requests", token=adminToken)
    existingRequest = next((item for item in pendingRequests if item["userId"] == targetUser["id"]), None)
    if existingRequest is not None:
        print("  reused pending join request: " + targetUser["username"])
        return True
    try:
        client.request(
            "POST",
            "/teams/join",
            token=targetUser["token"],
            body={"teamId": teamId, "message": "QA acceptance data: I would like to join QA Alpha Team."},
        )
        print("  created pending join request: " + targetUser["username"])
        return True
    except ApiError as apiError:
        skippedItems.append("入团申请创建失败：" + targetUser["username"] + " -> " + str(apiError))
        return False

# ===== 汇总与文档输出 =====


def collect_summary(
    client: ApiClient,
    superAdminToken: str,
    tokensByUsername: dict[str, str],
    userIdByUsername: dict[str, int],
    userSpecs: list[dict],
    activeCollaboration: dict | None,
    pendingCollaboration: dict | None,
    skippedItems: list[str],
    superAdminUsername: str,
    superAdminPassword: str,
) -> dict:
    """从 API 重新读取权威数据，汇总为文档与 JSON 输出所需的字典。"""
    adminUsersPage = client.request(
        "GET", queryPath("/admin/users", keyword=QA_USERNAME_PREFIX, page=1, pageSize=100), token=superAdminToken
    )
    adminUsers = {item["username"]: item for item in adminUsersPage["items"]}
    usernameByUserId = {item["id"]: item["username"] for item in adminUsersPage["items"]}

    teamDetails = {}
    for teamKey, teamSpec in QA_TEAM_SPECS.items():
        teamSummary = find_team_by_name(client, superAdminToken, teamSpec["name"])
        if teamSummary is None:
            continue
        ownerToken = tokensByUsername[teamSpec["owner"]]
        teamDetails[teamKey] = get_team_detail(client, ownerToken, teamSummary["id"])

    membershipCandidates: dict[int, list[tuple[dict, dict]]] = {}
    for teamDetail in teamDetails.values():
        for member in teamDetail["members"]:
            membershipCandidates.setdefault(member["userId"], []).append((teamDetail, member))
    teamNameByUserId: dict[int, tuple[str, str, str]] = {}
    for memberUserId, candidates in membershipCandidates.items():
        certifiedCandidates = [candidate for candidate in candidates if candidate[0]["status"] == "active"]
        chosenTeam, chosenMember = (certifiedCandidates or candidates)[0]
        teamNameByUserId[memberUserId] = (chosenTeam["name"], chosenMember["role"], chosenMember["levelName"])

    accounts = [
        {
            "username": superAdminUsername,
            "password": superAdminPassword,
            "globalRole": "superAdmin",
            "teamName": "",
            "teamRole": "",
            "levelName": "",
            "notes": "内置超级用户：可认证团队、设置全局管理员、管理后台数据库只读浏览",
        }
    ]
    for userSpec in userSpecs:
        adminUser = adminUsers.get(userSpec["username"])
        if adminUser is None:
            continue
        membership = teamNameByUserId.get(adminUser["id"])
        accounts.append(
            {
                "username": userSpec["username"],
                "password": QA_PASSWORD,
                "globalRole": adminUser["globalRole"],
                "teamName": membership[0] if membership else "",
                "teamRole": membership[1] if membership else "",
                "levelName": membership[2] if membership else "",
                "notes": userSpec["purpose"]
                + ("" if adminUser["isActive"] or "禁用" in userSpec["purpose"] else "（账号已禁用）"),
            }
        )

    teamEntries = [
        {
            "id": teamDetail["id"],
            "name": teamDetail["name"],
            "certified": teamDetail["status"] == "active",
            "status": teamDetail["status"],
            "joinMethod": teamDetail["joinMethod"],
            "memberCount": len(teamDetail["members"]),
        }
        for teamDetail in teamDetails.values()
    ]

    taskEntries = []
    expectedTaskTitles = [taskSpec["title"] for taskSpec in QA_TASK_SPECS]
    for teamKey, teamDetail in teamDetails.items():
        ownerToken = tokensByUsername[QA_TEAM_SPECS[teamKey]["owner"]]
        taskPage = client.request(
            "GET",
            queryPath("/teams/" + str(teamDetail["id"]) + "/tasks", page=1, pageSize=100),
            token=ownerToken,
        )
        for taskItem in taskPage["items"]:
            if taskItem["title"] not in expectedTaskTitles:
                continue
            assigneeUsernames = [
                usernameByUserId.get(assignment["userId"], "unknown") for assignment in taskItem["assignments"]
            ]
            taskEntries.append(
                {
                    "id": taskItem["id"],
                    "title": taskItem["title"],
                    "status": taskItem["status"],
                    "teamName": teamDetail["name"],
                    "priority": taskItem["priority"],
                    "assignmentMode": taskItem["assignmentMode"],
                    "acceptanceMode": taskItem["acceptanceMode"],
                    "assigneeUsername": assigneeUsernames[0] if assigneeUsernames else "",
                    "assigneeUsernames": assigneeUsernames,
                    "autoAssigned": taskItem["autoAssigned"],
                    "dueAt": taskItem["dueAt"],
                    "overdue": bool(
                        taskItem["dueAt"]
                        and taskItem["status"] not in ("archived", "cancelled")
                        and datetime.fromisoformat(taskItem["dueAt"]) < datetime.now()
                    ),
                }
            )

    collaborationEntries = []
    collaborationTaskEntries = []
    if activeCollaboration is not None:
        collaborationEntries.append(
            {
                "id": activeCollaboration["id"],
                "status": activeCollaboration["status"],
                "initiatorTeamName": activeCollaboration["initiatorUnit"]["unitName"],
                "targetTeamName": activeCollaboration["targetUnit"]["unitName"],
            }
        )
        for taskItem in list_collaboration_tasks(client, tokensByUsername["qaMemberA2"], activeCollaboration["id"]):
            collaborationTaskEntries.append(
                {
                    "id": taskItem["id"],
                    "title": taskItem["title"],
                    "status": taskItem["status"],
                    "collaborationPhase": taskItem.get("collaborationPhase"),
                    "teamName": taskItem["teamName"],
                }
            )
    if pendingCollaboration is not None:
        collaborationEntries.append(
            {
                "id": pendingCollaboration["id"],
                "status": pendingCollaboration["status"],
                "initiatorTeamName": pendingCollaboration["initiatorUnit"]["unitName"],
                "targetTeamName": pendingCollaboration["targetUnit"]["unitName"],
            }
        )

    subTeamEntries = []
    if "alpha" in teamDetails:
        alphaDetail = teamDetails["alpha"]
        for subTeamItem in list_sub_teams(client, tokensByUsername["qaTeamAdminA"], alphaDetail["id"]):
            subTeamEntries.append(
                {
                    "id": subTeamItem["id"],
                    "name": subTeamItem["name"],
                    "teamName": alphaDetail["name"],
                    "leaderUsername": usernameByUserId.get(subTeamItem["leaderUserId"] or 0, ""),
                    "memberCount": subTeamItem["memberCount"],
                }
            )

    pendingJoinRequestTeamIds = []
    pendingJoinRequestCounts = {}
    if "alpha" in teamDetails:
        joinRequests = client.request(
            "GET",
            "/teams/" + str(teamDetails["alpha"]["id"]) + "/join-requests",
            token=tokensByUsername["qaTeamAdminA"],
        )
        if joinRequests:
            pendingJoinRequestTeamIds.append(teamDetails["alpha"]["id"])
            pendingJoinRequestCounts[teamDetails["alpha"]["name"]] = len(joinRequests)

    todoStats = {}
    for username in ("qaMemberA1", "qaMemberA2", "qaMemberB1", "qaMemberB2"):
        if tokensByUsername.get(username):
            todoStats[username] = client.request("GET", "/todos/stats", token=tokensByUsername[username])

    unreadCounts = {}
    for username in ("qaMemberA1", "qaMemberA2", "qaMemberB1", "qaMemberB2", "qaTeamAdminA", "qaTeamAdminB"):
        if tokensByUsername.get(username):
            unreadCounts[username] = get_unread_notification_count(client, tokensByUsername[username])

    aiConfig = client.request("GET", "/settings/ai-config", token=superAdminToken)
    aiStatus = client.request("GET", "/ai/status", token=superAdminToken)
    health = client.request("GET", "/health")
    aiTask = next((taskItem for taskItem in taskEntries if taskItem["autoAssigned"]), None)
    manualAssignTask = next(
        (taskItem for taskItem in taskEntries if taskItem["title"] == "QA Beta Manual Assign Task"), None
    )

    return {
        "generatedAt": formatDateTime(datetime.now()),
        "baseApi": client.baseApi,
        "appVersion": health.get("version"),
        "accounts": accounts,
        "teams": teamEntries,
        "tasks": taskEntries,
        "collaborationTasks": collaborationTaskEntries,
        "collaborations": collaborationEntries,
        "subTeams": subTeamEntries,
        "pendingJoinRequestTeamIds": pendingJoinRequestTeamIds,
        "pendingJoinRequestCounts": pendingJoinRequestCounts,
        "todoStats": todoStats,
        "unreadNotificationCounts": unreadCounts,
        "aiConfig": {
            "dispatchMode": aiConfig["dispatchMode"],
            "matchThreshold": aiConfig["matchThreshold"],
            "workloadPenalty": aiConfig["workloadPenalty"],
            "llmConfigured": aiConfig["hasApiKey"],
        },
        "aiStatus": {
            "provider": aiStatus["provider"],
            "dispatchMode": aiStatus["dispatchMode"],
            "localAvailable": aiStatus["localAvailable"],
        },
        "aiTaskId": aiTask["id"] if aiTask else None,
        "aiTaskTitle": aiTask["title"] if aiTask else "",
        "manualAssignTaskId": manualAssignTask["id"] if manualAssignTask else None,
        "skippedItems": skippedItems,
    }


def build_accounts_markdown(summary: dict) -> str:
    """构建账号清单 Markdown（含表头、登录说明）。"""
    accountRows = []
    for account in summary["accounts"]:
        teamText = account["teamName"] or "-"
        roleText = (account["teamRole"] + " / " + account["levelName"]) if account["teamRole"] else "-"
        accountRows.append(
            "| " + account["username"] + " | " + account["password"] + " | " + account["globalRole"]
            + " | " + teamText + " | " + roleText + " | " + account["notes"] + " |"
        )
    return "\n".join(
        [
            "# QA Acceptance Test Accounts (v" + str(summary["appVersion"]) + ")",
            "",
            "> Generated at " + summary["generatedAt"] + "; base API: " + summary["baseApi"],
            "> All QA accounts share the password " + QA_PASSWORD + ".",
            "> LAN access: " + (summary.get("lanApi") or "(not configured)") + "",
            "",
            "| Username | Password | Global Role | Team | Team Role / Level | Purpose |",
            "| --- | --- | --- | --- | --- | --- |",
            "\n".join(accountRows),
            "",
            "## Login notes",
            "",
            "1. Open the application (desktop or browser) and sign in with any account above.",
            "2. superAdmin can open the Admin Console for team certification, global admin management and database browsing.",
            "3. qaGlobalAdmin is a global admin (Admin Console access, no super-admin-only actions).",
            "4. qaTeamAdminA / qaTeamAdminB own certified teams and can publish and review tasks.",
            "5. qaDisabledUser is disabled; signing in must return ACCOUNT_DISABLED.",
            "",
        ]
    )


def build_summary_markdown(summary: dict) -> str:
    """构建 QA 数据摘要 Markdown（团队/任务/待办/子团队/协作/通知/AI/跳过项）。"""
    taskRows = []
    for taskItem in summary["tasks"]:
        assignees = ", ".join(taskItem["assigneeUsernames"]) if taskItem["assigneeUsernames"] else "-"
        taskRows.append(
            "| " + taskItem["teamName"] + " | " + taskItem["title"] + " | " + taskItem["status"]
            + " | " + taskItem["priority"] + " | " + taskItem["assignmentMode"]
            + " | " + taskItem["acceptanceMode"] + " | " + assignees + " |"
        )
    collaborationTaskRows = [
        "| " + taskItem["title"] + " | " + str(taskItem["collaborationPhase"]) + " | " + str(taskItem["status"]) + " |"
        for taskItem in summary["collaborationTasks"]
    ]
    todoRows = []
    for username, stats in summary["todoStats"].items():
        todoRows.append(
            "| " + username + " | " + str(stats["total"]) + " | " + str(stats["pendingAcceptance"])
            + " | " + str(stats["inProgress"]) + " | " + str(stats["pendingReview"])
            + " | " + str(stats["archived"]) + " | " + str(stats["overdue"]) + " |"
        )
    unreadRows = [
        "| " + username + " | " + str(count) + " |"
        for username, count in summary["unreadNotificationCounts"].items()
    ]
    teamRows = [
        "| " + str(teamItem["id"]) + " | " + teamItem["name"] + " | "
        + ("Certified" if teamItem["certified"] else "Pending") + " | " + teamItem["joinMethod"]
        + " | " + str(teamItem["memberCount"]) + " |"
        for teamItem in summary["teams"]
    ]
    collaborationRows = [
        "| " + str(collaborationItem["id"]) + " | " + collaborationItem["status"] + " | "
        + collaborationItem["initiatorTeamName"] + " | " + collaborationItem["targetTeamName"] + " |"
        for collaborationItem in summary["collaborations"]
    ]
    subTeamRows = [
        "| " + str(subTeamItem["id"]) + " | " + subTeamItem["name"] + " | " + subTeamItem["teamName"]
        + " | " + subTeamItem["leaderUsername"] + " | " + str(subTeamItem["memberCount"]) + " |"
        for subTeamItem in summary["subTeams"]
    ]
    skippedText = "\n".join(["- " + item for item in summary["skippedItems"]]) if summary["skippedItems"] else "None."
    qaAccountCount = len([account for account in summary["accounts"] if account["username"].startswith("qa")])
    return "\n".join(
        [
            "# QA Acceptance Test Data Summary (v" + str(summary["appVersion"]) + ")",
            "",
            "> Generated at " + summary["generatedAt"] + "; base API: " + summary["baseApi"],
            "> Regenerate with: python scripts/seedQaAcceptanceData.py (idempotent).",
            "> LAN access: " + (summary.get("lanApi") or "(not configured)") + "",
            "",
            "## 1. Accounts and roles",
            "",
            "- QA accounts: " + str(qaAccountCount) + "; plus built-in superAdmin.",
            "- globalAdmin: qaGlobalAdmin; disabled user: qaDisabledUser; team admins: qaTeamAdminA (QA Alpha Team), qaTeamAdminB (QA Beta Team / QA Gamma Pending Team creator); sub-admin: qaSubAdminA.",
            "- See testAccounts.md and testAccounts.json for the full account list.",
            "",
            "## 2. Teams and member levels",
            "",
            "| Team ID | Team Name | Certification | Join Method | Members |",
            "| --- | --- | --- | --- | --- |",
            "\n".join(teamRows),
            "",
            "- QA Alpha Team has the custom level QA Lead (levelOrder=4, canCreateTask=true) used by qaSubAdminA.",
            "- QA Alpha Team uses approval join and keeps one pending join request; QA Beta Team uses invite-code join.",
            "",
            "## 3. Tasks (" + str(len(summary["tasks"])) + ")",
            "",
            "| Team | Title | Status | Priority | Assignment | Acceptance | Assignees |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "\n".join(taskRows),
            "",
            "- Statuses: published / inProgress / pendingReview / archived / cancelled.",
            "- Priorities: low / medium / high / urgent; specific member and level-range assignment; mandatory and optional acceptance.",
            "- The overdue task due date was moved into the past through the admin single-statement DML API.",
            "- AI auto-assigned task: " + str(summary["aiTaskId"]) + " (" + summary["aiTaskTitle"] + "), assignmentSource=ai.",
            "- Manual assignment task: " + str(summary["manualAssignTaskId"]) + " (AI match failure, then manual assignee).",
            "",
            "## 4. To-dos (/todos/stats per user)",
            "",
            "| User | total | pendingAcceptance | inProgress | pendingReview | archived | overdue |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "\n".join(todoRows),
            "",
            "## 5. Sub-teams",
            "",
            "| Sub-team ID | Name | Team | Leader | Members |",
            "| --- | --- | --- | --- | --- |",
            "\n".join(subTeamRows),
            "",
            "## 6. Collaborations and collaboration tasks",
            "",
            "| Collaboration ID | Status | Initiator Unit | Receiver Unit |",
            "| --- | --- | --- | --- |",
            "\n".join(collaborationRows),
            "",
            "| Collaboration Task | Phase | Status |",
            "| --- | --- | --- |",
            "\n".join(collaborationTaskRows),
            "",
            "## 7. Notifications",
            "",
            "- Triggered by collaboration request/confirmation, collaboration task confirm/submit, task review results, AI auto-assignment / match reminder / assignment failure and manual assignment.",
            "- qaMemberA2 and qaMemberB2 each have one notification marked as read; the rest stay unread.",
            "",
            "| User | Unread notifications |",
            "| --- | --- |",
            "\n".join(unreadRows),
            "",
            "## 8. AI configuration",
            "",
            "- dispatchMode=" + summary["aiConfig"]["dispatchMode"] + " (LOCAL_ONLY, local rule engine).",
            "- matchThreshold=" + str(summary["aiConfig"]["matchThreshold"]) + "; workloadPenalty=" + str(summary["aiConfig"]["workloadPenalty"]) + ".",
            "- LLM configured=" + str(summary["aiConfig"]["llmConfigured"]) + "; /ai/status provider=" + summary["aiStatus"]["provider"] + ".",
            "",
            "## 9. Skipped items / known limitations",
            "",
            skippedText,
            "",
            "## 10. Idempotency",
            "",
            "- The script looks up accounts by username, teams by name and tasks by title, so re-running it reuses existing data.",
            "- Re-running also repairs missing memberships, roles/levels, task states and collaborations.",
            "- If the application data is reset, re-run the script to rebuild the whole QA dataset.",
            "",
        ]
    )


def write_output_files(summary: dict) -> None:
    """写出账号清单、数据摘要（Markdown / JSON）与 QA 数据索引 JSON。"""
    QA_DOCS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    QA_STATE_DIRECTORY.mkdir(parents=True, exist_ok=True)

    accountsJson = []
    for account in summary["accounts"]:
        accountsJson.append(
            {
                "username": account["username"],
                "password": account["password"],
                "globalRole": account["globalRole"],
                "teamName": account["teamName"],
                "teamRole": account["teamRole"],
                "levelName": account["levelName"],
                "notes": account["notes"],
            }
        )
    (QA_DOCS_DIRECTORY / "testAccounts.json").write_text(
        json.dumps(accountsJson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (QA_DOCS_DIRECTORY / "testAccounts.md").write_text(build_accounts_markdown(summary), encoding="utf-8")
    (QA_DOCS_DIRECTORY / "testDataSummary.md").write_text(build_summary_markdown(summary), encoding="utf-8")

    qaData = {
        "generatedAt": summary["generatedAt"],
        "baseApi": summary["baseApi"],
        "appVersion": summary["appVersion"],
        "teams": [
            {"id": teamItem["id"], "name": teamItem["name"], "certified": teamItem["certified"]}
            for teamItem in summary["teams"]
        ],
        "categories": {
            "statuses": ["published", "inProgress", "pendingReview", "archived", "cancelled"],
            "priorities": ["low", "medium", "high", "urgent"],
            "acceptanceModes": ["mandatory", "optional"],
            "assignmentModes": ["specific", "levelRange"],
        },
        "tasks": summary["tasks"],
        "collaborations": summary["collaborations"],
        "collaborationTasks": summary["collaborationTasks"],
        "subTeams": summary["subTeams"],
        "pendingJoinRequestTeamIds": summary["pendingJoinRequestTeamIds"],
        "aiTaskId": summary["aiTaskId"],
        "aiTaskTitle": summary["aiTaskTitle"],
        "manualAssignTaskId": summary["manualAssignTaskId"],
        "users": [
            {
                "username": account["username"],
                "globalRole": account["globalRole"],
                "teamName": account["teamName"],
                "teamRole": account["teamRole"],
                "levelName": account["levelName"],
            }
            for account in summary["accounts"]
        ],
        "skippedItems": summary["skippedItems"],
    }
    (QA_STATE_DIRECTORY / "qaData.json").write_text(
        json.dumps(qaData, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def print_account_table(summary: dict) -> None:
    """在控制台打印账号清单原文，供团队复制使用。"""
    print("\n[seed] QA accounts (password: " + QA_PASSWORD + "):")
    for account in summary["accounts"]:
        teamText = account["teamName"] or "-"
        roleText = (account["teamRole"] + "/" + account["levelName"]) if account["teamRole"] else "-"
        print(
            "  " + account["username"].ljust(20) + " " + account["password"].ljust(12)
            + " " + account["globalRole"].ljust(11) + " " + teamText.ljust(24) + " " + roleText
        )


def main() -> int:
    """脚本主流程：按阶段幂等写入 QA 验收数据并输出文档。"""
    argumentParser = argparse.ArgumentParser(description="Seed QA acceptance data for the installed application.")
    argumentParser.add_argument("--base-api", default=DEFAULT_BASE_API, help="Application base URL")
    argumentParser.add_argument("--lan-api", default="", help="Optional LAN base URL shown in generated docs")
    argumentParser.add_argument("--super-admin-username", default="superAdmin")
    argumentParser.add_argument("--super-admin-password", default="SuperAdmin@123")
    scriptArguments = argumentParser.parse_args()

    client = ApiClient(scriptArguments.base_api)
    skippedItems: list[str] = []
    try:
        printSection("1/10 Health check and super admin login")
        health = client.request("GET", "/health")
        print(
            "  app version=" + str(health.get("version")) + " database=" + str(health.get("database"))
            + " redis=" + str(health.get("redis"))
        )
        superLogin = client.login(scriptArguments.super_admin_username, scriptArguments.super_admin_password)
        superAdminUserId = superLogin["user"]["user"]["id"]
        tokensByUsername: dict[str, str] = {"__superAdmin__": client.tokens[scriptArguments.super_admin_username]}
        userIdByUsername: dict[str, int] = {"__superAdmin__": superAdminUserId}
        print("  super admin login OK (id=" + str(superAdminUserId) + ")")

        printSection("2/10 Configure AI local-only dispatch")
        aiConfig = client.request(
            "PUT",
            "/settings/ai-config",
            token=tokensByUsername["__superAdmin__"],
            body={"dispatchMode": "LOCAL_ONLY", "matchThreshold": 20, "workloadPenalty": 2, "clearApiKey": False},
        )
        print(
            "  ai-config dispatchMode=" + aiConfig["dispatchMode"]
            + " matchThreshold=" + str(aiConfig["matchThreshold"])
        )
        aiStatus = client.request("GET", "/ai/status", token=tokensByUsername["__superAdmin__"])
        print("  ai-status provider=" + aiStatus["provider"] + " localAvailable=" + str(aiStatus["localAvailable"]))

        printSection("3/10 Ensure QA users, profile and skills")
        usersByUsername: dict[str, dict] = {}
        for userSpec in QA_USER_SPECS:
            userRecord = ensure_user(client, tokensByUsername["__superAdmin__"], userSpec)
            usersByUsername[userSpec["username"]] = userRecord
            tokensByUsername[userSpec["username"]] = userRecord["token"]
            userIdByUsername[userSpec["username"]] = userRecord["id"]
        ensure_global_admin(client, tokensByUsername["__superAdmin__"], usersByUsername["qaGlobalAdmin"])
        print("  promoted to globalAdmin: qaGlobalAdmin")
        try:
            ensure_user_disabled(client, tokensByUsername["__superAdmin__"], usersByUsername["qaDisabledUser"])
            print("  disabled user: qaDisabledUser")
        except ApiError as apiError:
            skippedItems.append("禁用账号失败（可继续其余验收）：" + str(apiError))

        printSection("4/10 Ensure certified and pending teams")
        alphaDetail = ensure_team(
            client, tokensByUsername["__superAdmin__"], QA_TEAM_SPECS["alpha"], tokensByUsername["qaTeamAdminA"]
        )
        alphaDetail = ensure_team_level(
            client, tokensByUsername["qaTeamAdminA"], alphaDetail["id"], "QA Lead", 4, True
        )
        betaDetail = ensure_team(
            client, tokensByUsername["__superAdmin__"], QA_TEAM_SPECS["beta"], tokensByUsername["qaTeamAdminB"]
        )
        gammaDetail = ensure_team(
            client, tokensByUsername["__superAdmin__"], QA_TEAM_SPECS["gamma"], tokensByUsername["qaTeamAdminB"]
        )
        if gammaDetail["status"] == "active":
            skippedItems.append("待认证团队 QA Gamma Pending Team 已处于 active 状态，公开 API 无法回退为 pending。")
        teamDetailsById = {"alpha": alphaDetail, "beta": betaDetail, "gamma": gammaDetail}

        printSection("5/10 Ensure team memberships, roles and levels")
        for username, role, levelOrder in ALPHA_MEMBERS:
            if username != "qaTeamAdminA":
                ensure_team_membership(
                    client,
                    alphaDetail,
                    tokensByUsername["qaTeamAdminA"],
                    "approval",
                    usersByUsername[username],
                )
        for username, role, levelOrder in ALPHA_MEMBERS:
            if role != "admin":
                ensure_member_role_and_level(
                    client,
                    tokensByUsername["qaTeamAdminA"],
                    alphaDetail,
                    usersByUsername[username],
                    role,
                    levelOrder,
                )
        for username, role, levelOrder in BETA_MEMBERS:
            if username != "qaTeamAdminB":
                ensure_team_membership(
                    client,
                    betaDetail,
                    tokensByUsername["qaTeamAdminB"],
                    "inviteOnly",
                    usersByUsername[username],
                )
        for username, role, levelOrder in BETA_MEMBERS:
            if role != "admin":
                ensure_member_role_and_level(
                    client,
                    tokensByUsername["qaTeamAdminB"],
                    betaDetail,
                    usersByUsername[username],
                    role,
                    levelOrder,
                )
        ensure_pending_join_request(
            client,
            tokensByUsername["qaTeamAdminA"],
            alphaDetail,
            usersByUsername["qaApplicantAlpha"],
            skippedItems,
        )

        printSection("6/10 Ensure sub-teams and sub-team leads")
        subTeams = [
            ensure_sub_team(
                client,
                tokensByUsername["qaTeamAdminA"],
                alphaDetail["id"],
                "Frontend Squad",
                "QA acceptance sub-team focused on frontend tasks and pending collaboration requests.",
                userIdByUsername["qaMemberA1"],
                [userIdByUsername["qaMemberA1"], userIdByUsername["qaMemberA2"]],
            ),
            ensure_sub_team(
                client,
                tokensByUsername["qaTeamAdminA"],
                alphaDetail["id"],
                "Backend Squad",
                "QA acceptance sub-team led by the Alpha sub-admin.",
                userIdByUsername["qaSubAdminA"],
                [userIdByUsername["qaSubAdminA"]],
            ),
        ]
        subTeamIdByName = {subTeam["name"]: subTeam["id"] for subTeam in subTeams}

        printSection("7/10 Ensure tasks across all statuses in both certified teams")
        for taskSpec in QA_TASK_SPECS:
            teamDetail = teamDetailsById[taskSpec["team"]]
            ensure_team_task(
                client,
                teamDetail,
                taskSpec,
                tokensByUsername,
                userIdByUsername,
                {},
                subTeamIdByName,
            )

        printSection("8/10 Ensure collaborations, pending request and collaboration tasks")
        activeCollaboration = ensure_active_collaboration(
            client,
            tokensByUsername["qaTeamAdminA"],
            tokensByUsername["qaMemberA2"],
            tokensByUsername["qaTeamAdminB"],
            userIdByUsername["qaMemberB2"],
            alphaDetail["id"],
            betaDetail["id"],
            userIdByUsername["qaMemberA2"],
        )
        pendingCollaboration = None
        try:
            pendingCollaboration = ensure_pending_collaboration(
                client,
                tokensByUsername["qaMemberA1"],
                tokensByUsername["qaTeamAdminA"],
                alphaDetail["id"],
                subTeamIdByName["Frontend Squad"],
                betaDetail["id"],
                userIdByUsername["qaMemberA1"],
            )
        except ApiError as apiError:
            skippedItems.append("pending 协作创建失败（可继续其余验收）：" + str(apiError))
        if activeCollaboration is not None:
            for collaborationTaskSpec in COLLABORATION_TASK_SPECS:
                ensure_collaboration_task(
                    client,
                    activeCollaboration,
                    collaborationTaskSpec,
                    tokensByUsername["qaMemberA2"],
                    tokensByUsername["qaTeamAdminA"],
                    userIdByUsername["qaMemberA2"],
                    tokensByUsername["qaMemberB2"],
                    tokensByUsername["qaTeamAdminB"],
                    userIdByUsername["qaMemberB1"],
                    tokensByUsername["qaMemberB1"],
                    skippedItems,
                )

        printSection("9/10 Trigger and mark notifications")
        readCountA2 = ensure_some_read_notifications(client, tokensByUsername["qaMemberA2"])
        readCountB2 = ensure_some_read_notifications(client, tokensByUsername["qaMemberB2"])
        print("  marked read notifications: qaMemberA2=" + str(readCountA2) + ", qaMemberB2=" + str(readCountB2))

        printSection("10/10 Collect summary and write QA documents")
        summary = collect_summary(
            client,
            tokensByUsername["__superAdmin__"],
            tokensByUsername,
            userIdByUsername,
            QA_USER_SPECS,
            activeCollaboration,
            pendingCollaboration,
            skippedItems,
            scriptArguments.super_admin_username,
            scriptArguments.super_admin_password,
        )
        summary["lanApi"] = scriptArguments.lan_api
        write_output_files(summary)
        print_account_table(summary)
        print("\n[seed] DONE in " + summary["generatedAt"])
        print("  docs: docs/qa/testAccounts.md, docs/qa/testAccounts.json, docs/qa/testDataSummary.md")
        print("  data index: .devdata/qa/qaData.json")
        print(
            "  tasks=" + str(len(summary["tasks"])) + " collaborationTasks="
            + str(len(summary["collaborationTasks"])) + " teams=" + str(len(summary["teams"]))
            + " subTeams=" + str(len(summary["subTeams"]))
        )
        if summary["skippedItems"]:
            print("  skipped items:")
            for skippedItem in summary["skippedItems"]:
                print("    - " + skippedItem)
        return 0
    except ApiError as apiError:
        print("\n[seed] FAILED: " + str(apiError))
        print("  hint: check that the application is running and the account has permission for this API.")
        return 1
    except RuntimeError as runtimeError:
        print("\n[seed] FAILED: " + str(runtimeError))
        return 1


if __name__ == "__main__":
    sys.exit(main())
