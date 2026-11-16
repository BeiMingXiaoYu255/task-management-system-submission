"""桌面安装版运行时：路径解析与本地配置管理。

设计说明：
    1. 桌面安装版由 Tauri 外壳通过环境变量传入资源目录、前端目录与数据目录，源码模式则回退到仓库目录；
    2. 本地配置（数据库账号密码、JWT 密钥、实际端口）首次启动生成后写入
       %APPDATA%/TaskManagementSystem/runtimeConfig.json，后续启动复用，保证数据目录与账号稳定；
    3. 所有路径使用 pathlib.Path，避免 Windows 下的反斜杠转义与空格问题；
    4. 本模块在导入时不得依赖 TaskManagementBackend.config.settings（配置尚未注入环境变量）。
"""

import json
import logging
import os
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

# 应用本地数据目录名：Windows 下为 %APPDATA%\TaskManagementSystem
APPLICATION_DIRECTORY_NAME = "TaskManagementSystem"
# 本地运行时配置文件名称
RUNTIME_CONFIGURATION_FILE_NAME = "runtimeConfig.json"
# 配置结构版本：后续格式升级时用于兼容旧配置
RUNTIME_CONFIGURATION_SCHEMA_VERSION = 1
# 默认数据库名称与账号（密码随机生成）
DEFAULT_DATABASE_NAME = "task_management"
DEFAULT_DATABASE_USER = "taskadmin"
# 默认端口
DEFAULT_HTTP_PORT = 8765
DEFAULT_MYSQL_PORT = 3307
DEFAULT_REDIS_PORT = 6380

_logger = logging.getLogger("taskManagement.desktop.runtimePaths")

# Windows 扩展长度路径前缀：Tauri 的 resource_dir() 等 API 在 Windows 会返回带该前缀的路径，
# 直接传给 MariaDB/PyInstaller 子进程会出现“系统找不到指定的路径”，必须先统一去掉。
WINDOWS_EXTENDED_PATH_PREFIX = "\\\\?\\"
# Windows 扩展长度 UNC 路径前缀：\\?\UNC\server\share → \\server\share
WINDOWS_EXTENDED_UNC_PATH_PREFIX = "\\\\?\\UNC\\"


def normalizeFilePath(filePath: Path | str) -> Path:
    r"""把 Windows 扩展长度路径前缀（\\?\）去掉，返回普通绝对路径。

    设计说明：
        Tauri 在 Windows 上对资源目录调用 canonicalize 后会得到 \\?\C:\... 形式，
        该前缀会沿环境变量传入 Python 并拼接进 MariaDB 初始化的 --datadir 参数，
        导致 mariadb-install-db.exe 报“系统找不到指定的路径”。本函数在所有路径入口统一转换，
        同时兼容 UNC 路径（\\?\UNC\server\share → \\server\share），非 Windows 路径原样返回。
    """
    rawPathText = str(filePath)
    if rawPathText.startswith(WINDOWS_EXTENDED_UNC_PATH_PREFIX):
        return Path("\\\\" + rawPathText[len(WINDOWS_EXTENDED_UNC_PATH_PREFIX):])
    if rawPathText.startswith(WINDOWS_EXTENDED_PATH_PREFIX):
        return Path(rawPathText[len(WINDOWS_EXTENDED_PATH_PREFIX):])
    return Path(rawPathText)


def isFrozenApplication() -> bool:
    """判断当前是否运行在 PyInstaller 打包后的可执行文件内。"""
    return bool(getattr(sys, "frozen", False))


def getFrozenBundleDirectory() -> Path:
    """返回 PyInstaller onedir 打包后的后端目录（runServer 可执行文件所在目录）。

    说明：PyInstaller 6 的 onedir 模式把依赖放在 _internal 子目录，
    资源目录 staging 结构为 <resources>/backend/_internal/...，因此上两级即为 <resources>。
    """
    bundledInternalDirectory = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return bundledInternalDirectory.parent.parent


def resolveProjectRootDirectory() -> Path:
    """源码模式：返回仓库根目录（Backend 目录的上一级）。"""
    return Path(__file__).resolve().parents[3]


@dataclass
class DesktopPaths:
    """桌面安装版运行所需的全部路径。"""

    runtimeDirectory: Path
    frontendDirectory: Path
    applicationDataDirectory: Path
    logDirectory: Path
    mariadbDataDirectory: Path
    redisDataDirectory: Path
    runtimeConfigurationFilePath: Path


def selectFirstExistingDirectory(candidateDirectories: list[Path]) -> Path:
    """按顺序返回第一个存在的目录；都不存在时返回首个候选（便于错误提示定位）。"""
    for candidateDirectory in candidateDirectories:
        if candidateDirectory.is_dir():
            return candidateDirectory
    return candidateDirectories[0]


def resolveDesktopPaths() -> DesktopPaths:
    """解析运行时路径：优先环境变量（Tauri 外壳注入），其次按源码/打包模式推断。

    打包模式下的候选顺序：
        1. Tauri 安装包资源目录 <resources>/runtime 与 <resources>/frontend；
        2. PyInstaller 包内自带的 _internal/Frontend/dist（便于后端独立运行调试）。
    """
    projectRootDirectory = resolveProjectRootDirectory()
    if isFrozenApplication():
        bundledResourceDirectory = getFrozenBundleDirectory()
        bundledInternalDirectory = Path(getattr(sys, "_MEIPASS", bundledResourceDirectory))
        defaultRuntimeDirectory = selectFirstExistingDirectory(
            [bundledResourceDirectory / "runtime", bundledResourceDirectory / "Runtime"]
        )
        defaultFrontendDirectory = selectFirstExistingDirectory(
            [
                bundledResourceDirectory / "frontend",
                bundledInternalDirectory / "Frontend" / "dist",
            ]
        )
    else:
        defaultRuntimeDirectory = projectRootDirectory / "Runtime"
        defaultFrontendDirectory = projectRootDirectory / "Frontend" / "dist"
    runtimeDirectory = Path(
        os.environ.get("TASK_MANAGEMENT_RUNTIME_DIR") or defaultRuntimeDirectory
    )
    frontendDirectory = Path(
        os.environ.get("TASK_MANAGEMENT_FRONTEND_DIR") or defaultFrontendDirectory
    )
    applicationDataDirectory = resolveApplicationDataDirectory()
    runtimeDirectory = normalizeFilePath(runtimeDirectory)
    frontendDirectory = normalizeFilePath(frontendDirectory)
    applicationDataDirectory = normalizeFilePath(applicationDataDirectory)
    desktopPaths = DesktopPaths(
        runtimeDirectory=runtimeDirectory,
        frontendDirectory=frontendDirectory,
        applicationDataDirectory=applicationDataDirectory,
        logDirectory=normalizeFilePath(applicationDataDirectory / "logs"),
        mariadbDataDirectory=normalizeFilePath(applicationDataDirectory / "mariadb-data"),
        redisDataDirectory=normalizeFilePath(applicationDataDirectory / "redis-data"),
        runtimeConfigurationFilePath=normalizeFilePath(
            applicationDataDirectory / RUNTIME_CONFIGURATION_FILE_NAME
        ),
    )
    ensureDirectories(desktopPaths)
    return desktopPaths


def resolveApplicationDataDirectory() -> Path:
    """解析应用数据目录：环境变量 > Windows APPDATA > 用户主目录。"""
    configuredDirectory = os.environ.get("TASK_MANAGEMENT_DATA_DIR")
    if configuredDirectory:
        return normalizeFilePath(configuredDirectory)
    appDataDirectory = os.environ.get("APPDATA")
    if appDataDirectory:
        return normalizeFilePath(Path(appDataDirectory) / APPLICATION_DIRECTORY_NAME)
    if sys.platform == "darwin":
        return normalizeFilePath(
            Path.home() / "Library" / "Application Support" / APPLICATION_DIRECTORY_NAME
        )
    return normalizeFilePath(Path.home() / ".local" / "share" / APPLICATION_DIRECTORY_NAME)


def ensureDirectories(desktopPaths: DesktopPaths) -> None:
    """创建数据目录、日志目录与子目录（幂等）。"""
    for directoryPath in (
        desktopPaths.applicationDataDirectory,
        desktopPaths.logDirectory,
        desktopPaths.mariadbDataDirectory,
        desktopPaths.redisDataDirectory,
    ):
        directoryPath.mkdir(parents=True, exist_ok=True)


def resolveHttpPort() -> int:
    """读取 Tauri 外壳传入的后端 HTTP 端口，缺省 8765。"""
    rawPort = os.environ.get("TASK_MANAGEMENT_HTTP_PORT", "")
    if rawPort.isdigit():
        port = int(rawPort)
        if 1 <= port <= 65535:
            return port
    return DEFAULT_HTTP_PORT


@dataclass
class RuntimeConfiguration:
    """本地运行时配置：首次启动随机生成，之后复用。"""

    schemaVersion: int
    databaseName: str
    databaseUser: str
    databasePassword: str
    rootPassword: str
    mysqlPort: int
    redisPort: int
    jwtSecret: str
    initializedAt: str

    def buildDatabaseUrl(self) -> str:
        """按当前配置生成 SQLAlchemy 数据库连接串（密码做 URL 编码）。"""
        encodedPassword = quote_plus(self.databasePassword)
        return (
            f"mysql+pymysql://{self.databaseUser}:{encodedPassword}"
            f"@127.0.0.1:{self.mysqlPort}/{self.databaseName}?charset=utf8mb4"
        )

    def buildRedisUrl(self) -> str:
        """按当前配置生成 Redis 连接串。"""
        return f"redis://127.0.0.1:{self.redisPort}/0"


def createDefaultRuntimeConfiguration() -> RuntimeConfiguration:
    """生成默认运行时配置：数据库密码、root 密码与 JWT 密钥均为随机值。"""
    return RuntimeConfiguration(
        schemaVersion=RUNTIME_CONFIGURATION_SCHEMA_VERSION,
        databaseName=DEFAULT_DATABASE_NAME,
        databaseUser=DEFAULT_DATABASE_USER,
        databasePassword=secrets.token_urlsafe(24),
        rootPassword=secrets.token_urlsafe(24),
        mysqlPort=DEFAULT_MYSQL_PORT,
        redisPort=DEFAULT_REDIS_PORT,
        jwtSecret=secrets.token_urlsafe(48),
        initializedAt=datetime.now().isoformat(timespec="seconds"),
    )


def readRuntimeConfiguration(configurationFilePath: Path) -> RuntimeConfiguration | None:
    """读取本地运行时配置；文件不存在或格式不合法时返回 None（触发重新生成）。"""
    if not configurationFilePath.is_file():
        return None
    try:
        rawConfiguration = json.loads(configurationFilePath.read_text(encoding="utf-8"))
        return RuntimeConfiguration(
            schemaVersion=int(rawConfiguration.get("schemaVersion", 1)),
            databaseName=str(rawConfiguration["databaseName"]),
            databaseUser=str(rawConfiguration["databaseUser"]),
            databasePassword=str(rawConfiguration["databasePassword"]),
            rootPassword=str(rawConfiguration["rootPassword"]),
            mysqlPort=int(rawConfiguration["mysqlPort"]),
            redisPort=int(rawConfiguration["redisPort"]),
            jwtSecret=str(rawConfiguration["jwtSecret"]),
            initializedAt=str(rawConfiguration.get("initializedAt", "")),
        )
    except (OSError, ValueError, KeyError, TypeError) as exception:
        _logger.warning("Failed to read the local runtime configuration; regenerating it: %s", exception)
        return None


def writeRuntimeConfiguration(
    configurationFilePath: Path, runtimeConfiguration: RuntimeConfiguration
) -> None:
    """把运行时配置以 UTF-8 缩进 JSON 写入磁盘（含版本号，便于后续兼容）。"""
    configurationFilePath.parent.mkdir(parents=True, exist_ok=True)
    configurationText = json.dumps(
        {
            "schemaVersion": runtimeConfiguration.schemaVersion,
            "databaseName": runtimeConfiguration.databaseName,
            "databaseUser": runtimeConfiguration.databaseUser,
            "databasePassword": runtimeConfiguration.databasePassword,
            "rootPassword": runtimeConfiguration.rootPassword,
            "mysqlPort": runtimeConfiguration.mysqlPort,
            "redisPort": runtimeConfiguration.redisPort,
            "jwtSecret": runtimeConfiguration.jwtSecret,
            "initializedAt": runtimeConfiguration.initializedAt,
            "savedAt": datetime.now().isoformat(timespec="seconds"),
        },
        ensure_ascii=False,
        indent=2,
    )
    configurationFilePath.write_text(configurationText, encoding="utf-8")


def loadOrCreateRuntimeConfiguration(configurationFilePath: Path) -> RuntimeConfiguration:
    """加载本地配置；不存在时生成随机配置并立即落盘。"""
    runtimeConfiguration = readRuntimeConfiguration(configurationFilePath)
    if runtimeConfiguration is None:
        runtimeConfiguration = createDefaultRuntimeConfiguration()
        writeRuntimeConfiguration(configurationFilePath, runtimeConfiguration)
        _logger.info("Generated a new local runtime configuration: %s", configurationFilePath)
    return runtimeConfiguration