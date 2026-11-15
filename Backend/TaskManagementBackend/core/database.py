"""数据库引擎、会话与初始化逻辑。

设计说明：
    1. 引擎在模块加载时创建，连接参数来自集中配置；
    2. getDb 作为 FastAPI 依赖提供请求级数据库会话，请求结束自动关闭；
    3. initDatabase 在应用启动时建表（本项目使用 create_all，无需迁移工具）。
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.core.migrationService import upgradeDatabaseSchema
from TaskManagementBackend.models import Base


def createDatabaseEngine(databaseUrl: str | None = None, echo: bool = False) -> Engine:
    """按数据库地址创建 SQLAlchemy 引擎。

    参数：
        databaseUrl：数据库连接串，缺省使用全局配置；
        echo：是否打印 SQL（调试用）。
    返回：
        SQLAlchemy Engine。
    """
    resolvedUrl = databaseUrl or settings.databaseUrl
    engineArguments: dict = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "echo": echo,
        "future": True,
    }
    if resolvedUrl.startswith("sqlite"):
        engineArguments["connect_args"] = {"check_same_thread": False}
    return create_engine(resolvedUrl, **engineArguments)


# 全局数据库引擎（应用进程内单例）
engine = createDatabaseEngine()

# 会话工厂：expire_on_commit=False 便于提交后继续读取 ORM 对象属性
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def getDb() -> Generator[Session, None, None]:
    """FastAPI 依赖：为每个请求创建独立数据库会话，并在请求结束后关闭。"""
    databaseSession = SessionLocal()
    try:
        yield databaseSession
    finally:
        databaseSession.close()


def initDatabase() -> None:
    """初始化数据库表结构：创建缺失的表并执行 v1.1 增量迁移。"""
    Base.metadata.create_all(bind=engine)
    upgradeDatabaseSchema(engine)
