"""桌面安装版运行时管理器：由 runServer.py 在 --manage-runtime 模式下调用的总入口。

职责：
    1. 准备应用数据目录（%APPDATA%/TaskManagementSystem）与日志目录；
    2. 加载/生成本地运行时配置（随机数据库密码、root 密码与 JWT 密钥，仅首次生成）；
    3. 启动便携 MariaDB（首次自动初始化数据目录并创建业务库/账号）与便携 Redis（可选）；
    4. 把 databaseUrl/redisUrl/jwtSecret/frontendDistPath/port 注入环境变量，再交给 FastAPI 使用；
    5. 监控 Tauri 外壳通过标准输入管道发送的 EOF 以及父进程存活状态，退出时优雅关闭数据库与缓存。

调用时序（runServer.py 已实现）：解析 --manage-runtime 参数 → startManagedRuntime() → 导入
TaskManagementBackend.config.settings（此时环境变量已就绪）→ 启动 uvicorn。
"""

import atexit
import logging
import os
import sys
import threading
import time
from pathlib import Path

from TaskManagementBackend.desktop.databaseRuntime import MariaDbRuntime
from TaskManagementBackend.desktop.externalRuntimeSupport import (
    buildExternalDatabaseUrl,
    detectReachableRedisPort,
    detectSystemMysqlPort,
)
from TaskManagementBackend.desktop.processUtils import (
    findAvailablePort,
    isParentProcessAlive,
    isPortListening,
)
from TaskManagementBackend.desktop.redisRuntime import RedisRuntime
from TaskManagementBackend.desktop.runtimePaths import (
    DEFAULT_MYSQL_PORT,
    DEFAULT_REDIS_PORT,
    DesktopPaths,
    RuntimeConfiguration,
    loadOrCreateRuntimeConfiguration,
    resolveDesktopPaths,
    resolveHttpPort,
    writeRuntimeConfiguration,
)

_logger = logging.getLogger("taskManagement.desktop.runtimeManager")
# 父进程存活轮询间隔（秒）
PARENT_PROCESS_CHECK_INTERVAL_SECONDS = 2.0
# 全局托管实例与退出保护状态
_managedRuntimeInstance: "ManagedRuntime | None" = None
_shutdownLock = threading.Lock()
_isShuttingDown = False


class ManagedRuntime:
    """托管运行时：负责便携 MariaDB/Redis 的启动、环境变量注入与退出清理。"""

    def __init__(self, desktopPaths: DesktopPaths, runtimeConfiguration: RuntimeConfiguration) -> None:
        """保存路径与配置，并初始化两个运行时管理器。"""
        self.desktopPaths = desktopPaths
        self.runtimeConfiguration = runtimeConfiguration
        self.mariaDbRuntime: MariaDbRuntime | None = None
        self.redisRuntime: RedisRuntime | None = None
        self.startedMariaDb = False
        self.startedRedis = False
        self.isStopped = False
        self.externalDatabaseUrl: str | None = None

    def prepare(self) -> None:
        """准备并启动托管运行时，最后注入后端配置所需的全部环境变量。"""
        self._prepareMariaDb()
        self._prepareRedis()
        self._persistRuntimeConfiguration()
        self._injectEnvironmentVariables()

    def _prepareMariaDb(self) -> None:
        """启动便携 MariaDB：优先复用已运行实例，端口冲突时自动递增。"""
        bundledMariaDbDirectory = self.desktopPaths.runtimeDirectory / "mariadb"
        if not (bundledMariaDbDirectory / "bin").is_dir():
            self._prepareExternalDatabase(bundledMariaDbDirectory)
            return
        self.mariaDbRuntime = MariaDbRuntime(
            bundledMariaDbDirectory,
            self.desktopPaths.mariadbDataDirectory,
            self.desktopPaths.logDirectory,
            self.runtimeConfiguration,
        )
        if self.mariaDbRuntime.isApplicationDatabaseReachable():
            _logger.info("Detected a running bundled MariaDB (port %s); reusing it", self.runtimeConfiguration.mysqlPort)
            return
        if isPortListening(self.runtimeConfiguration.mysqlPort):
            # 端口被占用但无法用本地配置连接：说明是其他程序或其他实例，重新选择端口
            if self.mariaDbRuntime.isServerReachable():
                _logger.info("Reusing the MariaDB instance already running for this application (port %s)", self.runtimeConfiguration.mysqlPort)
                self.mariaDbRuntime.ensureApplicationDatabase()
                return
            originalPort = self.runtimeConfiguration.mysqlPort
            self.runtimeConfiguration.mysqlPort = findAvailablePort(originalPort + 1)
            _logger.info("MySQL port %s is in use; switching to %s", originalPort, self.runtimeConfiguration.mysqlPort)
        self.mariaDbRuntime.start()
        self.startedMariaDb = True

    def _prepareExternalDatabase(self, bundledMariaDbDirectory: Path) -> None:
        """非 Windows 安装包：使用系统已安装的 MariaDB/MySQL（约定账号 taskadmin/taskadmin123）。"""
        environmentDatabaseUrl = os.environ.get("TASK_MANAGEMENT_DATABASE_URL", "")
        if environmentDatabaseUrl:
            self.externalDatabaseUrl = environmentDatabaseUrl
            _logger.info("Using the external database specified by TASK_MANAGEMENT_DATABASE_URL")
            return
        systemMysqlPort = detectSystemMysqlPort(self.runtimeConfiguration.mysqlPort)
        if systemMysqlPort is None:
            _logger.warning(
                "Bundled MariaDB was not found (%s) and the system MySQL/MariaDB is not running. Install it as described in packaging/README.md",
                bundledMariaDbDirectory,
            )
            return
        self.runtimeConfiguration.mysqlPort = systemMysqlPort
        self.externalDatabaseUrl = buildExternalDatabaseUrl(systemMysqlPort)
        _logger.info("Using system MariaDB/MySQL: port %s (account: taskadmin)", systemMysqlPort)

    def _prepareRedis(self) -> None:
        """启动便携 Redis；不可用时仅告警（后端会自动降级内存缓存）。"""
        redisDirectory = self.desktopPaths.runtimeDirectory / "redis"
        self.redisRuntime = RedisRuntime(
            redisDirectory,
            self.desktopPaths.redisDataDirectory,
            self.desktopPaths.logDirectory,
            self.runtimeConfiguration.redisPort,
        )
        if self.redisRuntime.locateServerExecutable() is None:
            systemRedisPort = detectReachableRedisPort(self.runtimeConfiguration.redisPort)
            if systemRedisPort is not None:
                self.runtimeConfiguration.redisPort = systemRedisPort
                _logger.info("Using system Redis: port %s", systemRedisPort)
                return
            _logger.warning("Bundled Redis was not found and system Redis is unavailable; the backend will fall back to in-memory cache")
            return
        if self.redisRuntime.isRedisReachable():
            _logger.info("Detected a running Redis (port %s); reusing it", self.runtimeConfiguration.redisPort)
            return
        if isPortListening(self.runtimeConfiguration.redisPort):
            originalPort = self.runtimeConfiguration.redisPort
            self.runtimeConfiguration.redisPort = findAvailablePort(originalPort + 1)
            _logger.info("Redis port %s is in use; switching to %s", originalPort, self.runtimeConfiguration.redisPort)
        self.startedRedis = self.redisRuntime.startServer()
        if not self.startedRedis:
            _logger.warning("Redis failed to start; the backend will fall back to in-process in-memory cache")

    def _persistRuntimeConfiguration(self) -> None:
        """把实际使用的端口与配置写回本地配置文件，供下次启动复用。"""
        writeRuntimeConfiguration(
            self.desktopPaths.runtimeConfigurationFilePath, self.runtimeConfiguration
        )

    def _injectEnvironmentVariables(self) -> None:
        """注入后端配置环境变量（必须在导入 settings 之前执行）。"""
        os.environ["databaseUrl"] = (
            self.externalDatabaseUrl or self.runtimeConfiguration.buildDatabaseUrl()
        )
        os.environ["redisUrl"] = self.runtimeConfiguration.buildRedisUrl()
        os.environ["jwtSecret"] = self.runtimeConfiguration.jwtSecret
        os.environ["host"] = "0.0.0.0"
        os.environ["port"] = str(resolveHttpPort())
        if self.desktopPaths.frontendDirectory.is_dir():
            os.environ["frontendDistPath"] = str(self.desktopPaths.frontendDirectory)
        _logger.info(
            "Injected runtime configuration: databaseUrl=mysql+pymysql://%s:***@127.0.0.1:%s/%s, redisUrl=%s, "
            "frontendDistPath=%s, httpPort=%s, logDirectory=%s",
            self.runtimeConfiguration.databaseUser,
            self.runtimeConfiguration.mysqlPort,
            self.runtimeConfiguration.databaseName,
            self.runtimeConfiguration.buildRedisUrl(),
            os.environ.get("frontendDistPath", "(none)"),
            os.environ["port"],
            self.desktopPaths.logDirectory,
        )

    def stop(self) -> None:
        """关闭本进程启动的 Redis 与 MariaDB（复用其他实例时不动它们）。"""
        if self.isStopped:
            return
        self.isStopped = True
        if self.redisRuntime is not None and self.startedRedis:
            self.redisRuntime.stopServer()
        if self.mariaDbRuntime is not None and self.startedMariaDb:
            self.mariaDbRuntime.stop()
        _logger.info("Managed runtime has shut down")


def _configureRuntimeLogging(logDirectory: Path) -> None:
    """配置后端进程日志：文件（UTF-8）+ 标准错误，两处同时输出便于排障。"""
    logDirectory.mkdir(parents=True, exist_ok=True)
    logFormat = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)
    if not any(isinstance(handler, logging.FileHandler) for handler in rootLogger.handlers):
        fileHandler = logging.FileHandler(logDirectory / "backend.log", encoding="utf-8")
        fileHandler.setFormatter(logFormat)
        rootLogger.addHandler(fileHandler)
    if not any(isinstance(handler, logging.StreamHandler) for handler in rootLogger.handlers):
        streamHandler = logging.StreamHandler(sys.stderr)
        streamHandler.setFormatter(logFormat)
        rootLogger.addHandler(streamHandler)


def startManagedRuntime() -> None:
    """启动托管运行时（runServer.py --manage-runtime 时调用），并注册退出清理。"""
    global _managedRuntimeInstance
    desktopPaths = resolveDesktopPaths()
    _configureRuntimeLogging(desktopPaths.logDirectory)
    runtimeConfiguration = loadOrCreateRuntimeConfiguration(
        desktopPaths.runtimeConfigurationFilePath
    )
    _logger.info("Desktop runtime starting: data directory %s", desktopPaths.applicationDataDirectory)
    managedRuntime = ManagedRuntime(desktopPaths, runtimeConfiguration)
    managedRuntime.prepare()
    _managedRuntimeInstance = managedRuntime
    atexit.register(stopManagedRuntime)
    _startRuntimeExitMonitors()


def stopManagedRuntime() -> None:
    """关闭托管运行时（幂等，供退出监控与 atexit 调用）。"""
    global _managedRuntimeInstance
    managedRuntime = _managedRuntimeInstance
    _managedRuntimeInstance = None
    if managedRuntime is None:
        return
    managedRuntime.stop()


def _startRuntimeExitMonitors() -> None:
    """启动退出监控：标准输入 EOF（Tauri 外壳关闭管道）与父进程存活探测。

    仅在 Tauri 外壳通过 TASK_MANAGEMENT_PARENT_PID 声明父进程时启用：
    命令行手动运行（含单元测试、开发调试）时标准输入通常立即 EOF，
    若同样启用监控会导致后端启动后立刻退出。
    """
    parentProcessIdText = os.environ.get("TASK_MANAGEMENT_PARENT_PID", "")
    if not parentProcessIdText.isdigit():
        _logger.info("No desktop shell parent process ID detected; skipping exit monitoring (manual/command-line mode)")
        return
    inputStream = sys.stdin
    if inputStream is not None:
        monitorThread = threading.Thread(
            target=_monitorInputStreamEof,
            args=(inputStream,),
            name="runtimeInputEofMonitor",
            daemon=True,
        )
        monitorThread.start()
    parentMonitorThread = threading.Thread(
        target=_monitorParentProcess,
        args=(int(parentProcessIdText),),
        name="runtimeParentProcessMonitor",
        daemon=True,
    )
    parentMonitorThread.start()


def _monitorInputStreamEof(inputStream) -> None:
    """阻塞读取标准输入；桌面外壳退出导致管道关闭（EOF）时触发优雅停机。"""
    try:
        while True:
            inputLine = inputStream.readline()
            if not inputLine:
                break
    except (OSError, ValueError):
        pass
    _handleExitSignal("Standard input pipe closed (desktop shell exited)")


def _monitorParentProcess(parentProcessId: int) -> None:
    """定时探测父进程存活；父进程被强制结束（未走到 EOF）时兜底清理。"""
    while True:
        time.sleep(PARENT_PROCESS_CHECK_INTERVAL_SECONDS)
        if not isParentProcessAlive(parentProcessId):
            _handleExitSignal(f"Parent process {parentProcessId} has exited")
            return


def _handleExitSignal(reason: str) -> None:
    """统一退出处理：停止数据库与缓存后直接结束进程（uvicorn 主线程无法被跨线程中断）。"""
    global _isShuttingDown
    with _shutdownLock:
        if _isShuttingDown:
            return
        _isShuttingDown = True
    _logger.info("Received exit signal: %s; shutting down the managed runtime", reason)
    try:
        stopManagedRuntime()
    finally:
        logging.shutdown()
        os._exit(0)