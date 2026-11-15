"""应用配置：统一从环境变量 / Backend/.env 读取，供全后端使用。

配置字段使用小驼峰命名，环境变量名大小写不敏感（例如 databaseUrl 可写成 DATABASEURL 或 databaseUrl）。
桌面安装版由运行时管理器在启动前注入连接信息，因此配置在实例化时读取环境变量。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 后端根目录（Backend/），用于定位 .env 与前端构建产物
BACKEND_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
PROJECT_ROOT_DIRECTORY = BACKEND_ROOT_DIRECTORY.parent


class Settings(BaseSettings):
    """全局配置类：所有配置项集中管理，禁止在业务代码中直接读取环境变量。"""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT_DIRECTORY / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 应用基础信息 =====
    appName: str = "Task Management System"
    appVersion: str = "1.2.2"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8765

    # ===== 数据库与缓存 =====
    databaseUrl: str = "mysql+pymysql://taskadmin:taskadmin123@127.0.0.1:3307/task_management?charset=utf8mb4"
    redisUrl: str = "redis://127.0.0.1:6380/0"

    # ===== 身份认证 =====
    jwtSecret: str = "task-management-system-development-secret-key-2026"
    jwtAlgorithm: str = "HS256"
    jwtExpireDays: int = 7
    bcryptRounds: int = 12
    loginMaxAttempts: int = 10
    loginWindowSeconds: int = 300

    # ===== 内置超级用户（首次启动自动创建） =====
    superAdminUsername: str = "superAdmin"
    superAdminPassword: str = "SuperAdmin@123"
    superAdminNickname: str = "Super Admin"

    # ===== AI 自动分配（v1.1 移植自 Java AI 模块） =====
    # 调度模式：LOCAL_ONLY / LLM_ONLY / LOCAL_FIRST / LLM_FIRST
    assignmentDispatchMode: str = "LOCAL_FIRST"
    # 本地推荐最低分阈值
    assignmentMatchThreshold: int = 50
    # 每个活跃待办的负载惩罚分
    assignmentWorkloadPenalty: int = 5
    # LLM（OpenAI 兼容）配置：三项齐全才启用
    llmBaseUrl: str = ""
    llmChatPath: str = "/v1/chat/completions"
    llmApiKey: str = ""
    llmModel: str = ""
    llmTimeoutSeconds: int = 20
    llmMaxCandidates: int = 20

    # ===== 跨域与前端静态资源 =====
    corsOrigins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://tauri.localhost,tauri://localhost,https://tauri.localhost"
    )
    frontendDistPath: str = ""

    @property
    def corsOriginList(self) -> list[str]:
        """将逗号分隔的跨域白名单解析为列表。"""
        return [origin.strip() for origin in self.corsOrigins.split(",") if origin.strip()]

    @property
    def resolvedFrontendDistPath(self) -> str:
        """解析前端构建产物目录：优先配置，其次 Frontend/dist。"""
        if self.frontendDistPath:
            return self.frontendDistPath
        candidate = PROJECT_ROOT_DIRECTORY / "Frontend" / "dist"
        return str(candidate) if candidate.exists() else ""


settings = Settings()
