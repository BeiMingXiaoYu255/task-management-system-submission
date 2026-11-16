"""pytest 全局夹具与测试环境准备。

设计说明：
    1. 在导入任何应用模块之前设置 databaseUrl / redisUrl 环境变量，确保应用引擎指向测试库；
    2. 测试库默认 task_management_test，可用 TEST_DATABASE_NAME 环境变量隔离并行开发；
    3. 每个测试函数结束后清空全部业务表并重建内置数据，保证用例相互独立；
    4. 提供注册用户、创建团队、直接添加成员等数据工厂夹具。
"""

import os
import random
import string
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pymysql
import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url

# ===== 1. 路径与环境变量准备（必须先于应用模块导入） =====
BACKEND_ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT_DIRECTORY))

DEFAULT_DATABASE_URL = (
    "mysql+pymysql://taskadmin:taskadmin123@127.0.0.1:3307/task_management?charset=utf8mb4"
)
BASE_DATABASE_URL = os.environ.get("databaseUrl") or DEFAULT_DATABASE_URL
TEST_DATABASE_NAME = os.environ.get("TEST_DATABASE_NAME", "task_management_test")
TEST_REDIS_DATABASE = os.environ.get("TEST_REDIS_DB", "15")
BASE_REDIS_URL = os.environ.get("redisUrl") or "redis://127.0.0.1:6380/0"

parsedDatabaseUrl = make_url(BASE_DATABASE_URL)


def ensureTestDatabaseExists() -> None:
    """若测试数据库不存在则自动创建（需要账号具备建库权限）。"""
    connection = pymysql.connect(
        host=parsedDatabaseUrl.host or "127.0.0.1",
        port=parsedDatabaseUrl.port or 3306,
        user=parsedDatabaseUrl.username or "root",
        password=parsedDatabaseUrl.password or "",
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=5,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{TEST_DATABASE_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        connection.close()


ensureTestDatabaseExists()

# 注入测试数据库与独立 Redis 库（db 15 避免污染开发缓存）
os.environ["databaseUrl"] = parsedDatabaseUrl.set(
    database=TEST_DATABASE_NAME
).render_as_string(hide_password=False)
parsedRedisUrl = urlparse(BASE_REDIS_URL)
os.environ["redisUrl"] = urlunparse(parsedRedisUrl._replace(path=f"/{TEST_REDIS_DATABASE}"))
os.environ["bcryptRounds"] = "4"

# 提示：测试文件需要构造请求头时使用 from tests.helpers import buildAuthHeaders；
# 不要 from conftest import ...（conftest 不作为模块被测试文件导入）。

# ===== 2. 应用模块导入（此时环境变量已就绪） =====
from fastapi.testclient import TestClient  # noqa: E402

from TaskManagementBackend.config.settings import settings  # noqa: E402
from TaskManagementBackend.core.database import SessionLocal, engine, initDatabase  # noqa: E402
from TaskManagementBackend.core.redisClient import cacheClient  # noqa: E402
from TaskManagementBackend.main import createApp  # noqa: E402
from TaskManagementBackend.models import (  # noqa: E402
    Base,
    Team,
    TeamLevel,
    TeamMember,
    User,
)
from TaskManagementBackend.models.enums import GlobalRole, TeamRole, TeamStatus  # noqa: E402
from TaskManagementBackend.services.initializationService import initializeSystemData  # noqa: E402
from sqlalchemy import text  # noqa: E402


from tests.helpers import buildAuthHeaders  # noqa: E402  （测试文件也可直接引用该辅助函数）


def generateRandomSuffix(length: int = 8) -> str:
    """生成随机后缀，避免用户名/团队名唯一约束冲突。"""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def truncateAllBusinessTables() -> None:
    """清空全部业务表（保留表结构），并重置 Redis 测试库。"""
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    cacheClient.flushNamespace("")


def resetInitialSystemData() -> None:
    """重建内置超级用户与默认技能标签。"""
    databaseSession = SessionLocal()
    try:
        initializeSystemData(databaseSession)
    finally:
        databaseSession.close()


# ===== 3. 会话级夹具 =====
@pytest.fixture(scope="session")
def applicationClient():
    """整个测试会话共享的 TestClient；进入上下文触发应用启动事件。"""
    initDatabase()
    application = createApp()
    with TestClient(application) as testClient:
        yield testClient
    engine.dispose()


@pytest.fixture()
def client(applicationClient):
    """测试用例使用的 HTTP 客户端。"""
    return applicationClient


@pytest.fixture(autouse=True)
def cleanBusinessData(applicationClient):
    """每个用例结束后清理业务数据，保证测试相互独立。"""
    yield
    truncateAllBusinessTables()
    resetInitialSystemData()


# ===== 4. 数据工厂夹具 =====
@pytest.fixture()
def registerUser(client):
    """注册用户工厂：返回 { token, user } 字典。"""

    def factory(username: str | None = None, password: str = "Password123", nickname: str | None = None):
        payload = {
            "username": username or f"user{generateRandomSuffix()}",
            "password": password,
            "nickname": nickname or "测试用户",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201, f"注册失败: {response.status_code} {response.text}"
        return response.json()

    return factory


@pytest.fixture()
def superAdminHeaders(client):
    """内置超级用户的认证请求头。"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.superAdminUsername,
            "password": settings.superAdminPassword,
        },
    )
    assert response.status_code == 200, f"超级用户登录失败: {response.text}"
    return buildAuthHeaders(response.json()["token"])


@pytest.fixture()
def activateTeam():
    """把团队状态直接改为已认证（测试便捷夹具）。"""

    def activate(teamId: int) -> None:
        databaseSession = SessionLocal()
        try:
            team = databaseSession.get(Team, teamId)
            assert team is not None, "团队不存在"
            team.status = TeamStatus.ACTIVE
            databaseSession.commit()
        finally:
            databaseSession.close()

    return activate


@pytest.fixture()
def teamFactory(client, activateTeam):
    """创建团队工厂：默认创建后立即激活。"""

    def factory(adminToken: str, name: str | None = None, joinMethod: str = "inviteOnly"):
        payload = {
            "name": name or f"测试团队{generateRandomSuffix(6)}",
            "description": "自动化测试团队",
            "joinMethod": joinMethod,
        }
        response = client.post(
            "/api/v1/teams", json=payload, headers=buildAuthHeaders(adminToken)
        )
        assert response.status_code in (200, 201), f"创建团队失败: {response.text}"
        teamData = response.json()
        activateTeam(teamData["id"])
        return teamData

    return factory


@pytest.fixture()
def memberFactory(client, registerUser):
    """团队普通成员工厂：注册用户后直接写入团队成员关系（默认最低级别）。"""

    def factory(teamId: int, levelOrder: int = 1, nickname: str | None = None):
        account = registerUser(nickname=nickname)
        databaseSession = SessionLocal()
        try:
            level = databaseSession.execute(
                select(TeamLevel).where(
                    TeamLevel.teamId == teamId, TeamLevel.levelOrder == levelOrder
                )
            ).scalar_one()
            member = TeamMember(
                teamId=teamId,
                userId=account["user"]["user"]["id"],
                role=TeamRole.MEMBER,
                levelId=level.id,
            )
            databaseSession.add(member)
            databaseSession.commit()
        finally:
            databaseSession.close()
        account["levelOrder"] = levelOrder
        return account

    return factory


@pytest.fixture()
def setUserGlobalRole():
    """直接设置用户全局角色（用于管理后台测试）。"""

    def setRole(userId: int, globalRole: GlobalRole) -> None:
        databaseSession = SessionLocal()
        try:
            user = databaseSession.get(User, userId)
            assert user is not None, "用户不存在"
            user.globalRole = globalRole
            databaseSession.commit()
        finally:
            databaseSession.close()

    return setRole
