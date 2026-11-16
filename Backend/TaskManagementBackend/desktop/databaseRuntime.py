"""便携 MariaDB 运行时：数据目录初始化、mysqld 启停、业务库与账号创建。

设计说明：首次运行初始化 %APPDATA% 下的独立数据目录；每次启动前重写 my.ini（basedir/
datadir/端口/日志路径）；以 root 创建业务库与随机密码账号；退出时 mariadb-admin shutdown。
"""

import logging
import re
import shutil
import subprocess
import time
from pathlib import Path

import pymysql

from TaskManagementBackend.desktop.processUtils import (
    readLogTail,
    runCommandCaptured,
    startDetachedProcess,
    stopProcessTree,
    waitForPortListening,
)
from TaskManagementBackend.desktop.runtimePaths import RuntimeConfiguration

_logger = logging.getLogger("taskManagement.desktop.databaseRuntime")

# 等待 mysqld 端口监听的最长时间（秒）：首次启动需初始化 InnoDB 日志文件，留足余量
MYSQL_START_TIMEOUT_SECONDS = 120.0
# 初始化数据目录超时（秒）
MYSQL_INITIALIZE_TIMEOUT_SECONDS = 240.0
# 关闭数据库时的等待时间（秒）
MYSQL_SHUTDOWN_TIMEOUT_SECONDS = 15.0
# 服务器程序候选文件名（MariaDB 11.4 为 mariadbd.exe，兼容 mysqld.exe）
MYSQL_SERVER_FILE_NAMES = ("mariadbd.exe", "mysqld.exe")
# 数据目录初始化工具候选文件名
MYSQL_INSTALL_TOOL_FILE_NAMES = ("mariadb-install-db.exe", "mysql_install_db.exe")
# 合法数据库标识符：只允许字母数字下划线，避免 SQL 注入
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


class MariaDbRuntime:
    """便携 MariaDB 运行时管理器。"""

    def __init__(
        self,
        mariaDbDirectory: Path,
        dataDirectory: Path,
        logDirectory: Path,
        runtimeConfiguration: RuntimeConfiguration,
    ) -> None:
        """保存运行时目录与配置；实际启动由 start 方法完成。"""
        self.mariaDbDirectory = mariaDbDirectory
        self.dataDirectory = dataDirectory
        self.logDirectory = logDirectory
        self.runtimeConfiguration = runtimeConfiguration
        self.serverProcess: subprocess.Popen | None = None
        self.serverLogFilePath = logDirectory / "mariadb.log"
        self.installLogFilePath = logDirectory / "mariadb-install.log"
        self.configurationFilePath = dataDirectory / "runtime-my.ini"

    @property
    def binaryDirectory(self) -> Path:
        """MariaDB 可执行文件目录。"""
        return self.mariaDbDirectory / "bin"

    @property
    def mysqlPort(self) -> int:
        """当前使用的 MySQL 端口。"""
        return self.runtimeConfiguration.mysqlPort

    def locateRequiredExecutable(self, candidateFileNames: tuple[str, ...]) -> Path:
        """在 bin 目录中查找第一个存在的可执行文件，找不到时抛出中文异常。"""
        for fileName in candidateFileNames:
            candidatePath = self.binaryDirectory / fileName
            if candidatePath.is_file():
                return candidatePath
        raise RuntimeError(
            f"Bundled MariaDB is missing executable files: {candidateFileNames} (directory: {self.binaryDirectory})"
        )

    def isDataDirectoryInitialized(self) -> bool:
        """判断数据目录是否已完成初始化（存在 mysql 系统库目录）。"""
        return (self.dataDirectory / "mysql").is_dir()

    def isDatabaseConnectable(self, databaseUser: str, databasePassword: str, databaseName: str) -> bool:
        """以指定账号探测数据库是否可用（短超时，失败返回 False）。"""
        try:
            connection = pymysql.connect(
                host="127.0.0.1",
                port=self.mysqlPort,
                user=databaseUser,
                password=databasePassword,
                database=databaseName,
                connect_timeout=2,
                read_timeout=3,
                write_timeout=3,
            )
            connection.close()
            return True
        except Exception:
            return False

    def isServerReachable(self) -> bool:
        """以 root 身份探测数据库是否已就绪（用于复用已有实例）。"""
        return self.isDatabaseConnectable(
            "root", self.runtimeConfiguration.rootPassword, "mysql"
        )

    def isApplicationDatabaseReachable(self) -> bool:
        """以业务账号探测业务库是否可用（用于判断是否可跳过启动流程）。"""
        return self.isDatabaseConnectable(
            self.runtimeConfiguration.databaseUser,
            self.runtimeConfiguration.databasePassword,
            self.runtimeConfiguration.databaseName,
        )

    def removeIncompleteDataDirectory(self) -> None:
        """清理半初始化数据目录（仅当缺少 mysql 系统库时；成功初始化的目录不会删除）。"""
        if not self.dataDirectory.exists() or self.isDataDirectoryInitialized():
            return
        _logger.warning("Detected an incomplete MariaDB data directory; cleaning it up and reinitializing: %s", self.dataDirectory)
        shutil.rmtree(self.dataDirectory, ignore_errors=True)

    def initializeDataDirectory(self) -> None:
        """首次运行：用 mariadb-install-db 初始化独立数据目录并设置 root 随机密码。

        关键点：mariadb-install-db.exe 会根据自身可执行文件位置推断 basedir（不支持 --basedir 参数），
        因此必须保证运行时目录结构完整（bin/server.dll、share/errmsg.sys 等），并把工作目录设为 MariaDB 根目录。
        """
        installToolPath = self.locateRequiredExecutable(MYSQL_INSTALL_TOOL_FILE_NAMES)
        self.removeIncompleteDataDirectory()
        self.dataDirectory.mkdir(parents=True, exist_ok=True)
        _logger.info("Initializing MariaDB data directory: %s", self.dataDirectory)
        completedProcess = runCommandCaptured(
            installToolPath,
            [
                f"--datadir={self.dataDirectory}",
                f"--password={self.runtimeConfiguration.rootPassword}",
                f"--port={self.mysqlPort}",
                "--silent",
            ],
            timeoutSeconds=MYSQL_INITIALIZE_TIMEOUT_SECONDS,
            logFilePath=self.installLogFilePath,
            workingDirectory=self.mariaDbDirectory,
        )
        if not self.isDataDirectoryInitialized():
            raise RuntimeError(
                "MariaDB data directory initialization failed (exit code: "
                f"{completedProcess.returncode}). Log: {readLogTail(self.installLogFilePath)}"
            )
        _logger.info("MariaDB data directory initialized")

    def writeServerConfigurationFile(self) -> Path:
        """重写 mysqld 配置文件（启动参数集中在此，避免命令行转义问题）。"""

        def normalizePath(path: Path) -> str:
            """把 Windows 路径转换为正斜杠形式，避免 ini 文件反斜杠转义问题。"""
            return path.resolve().as_posix() if path.is_absolute() else path.as_posix()

        configurationLines = [
            "[mysqld]",
            f'basedir="{normalizePath(self.mariaDbDirectory)}"',
            f'datadir="{normalizePath(self.dataDirectory)}"',
            f"port={self.mysqlPort}",
            "bind-address=127.0.0.1",
            "skip-name-resolve",
            f'lc-messages-dir="{normalizePath(self.mariaDbDirectory / "share")}"',
            "character-set-server=utf8mb4",
            "collation-server=utf8mb4_unicode_ci",
            "max_connections=128",
            f'pid-file="{normalizePath(self.dataDirectory / "mysqld.pid")}"',
            f'log-error="{normalizePath(self.serverLogFilePath)}"',
            "[client]",
            f"port={self.mysqlPort}",
        ]
        self.configurationFilePath.parent.mkdir(parents=True, exist_ok=True)
        self.configurationFilePath.write_text("\r\n".join(configurationLines) + "\r\n", encoding="utf-8")
        return self.configurationFilePath

    def startServer(self) -> subprocess.Popen:
        """启动 mysqld 并等待端口监听与 root 连接就绪。"""
        if self.serverProcess is not None and self.serverProcess.poll() is None:
            return self.serverProcess
        serverExecutablePath = self.locateRequiredExecutable(MYSQL_SERVER_FILE_NAMES)
        configurationFilePath = self.writeServerConfigurationFile()
        _logger.info("Starting MariaDB: port %s, configuration file %s", self.mysqlPort, configurationFilePath)
        self.serverProcess = startDetachedProcess(
            serverExecutablePath,
            [f"--defaults-file={configurationFilePath}"],
            workingDirectory=self.mariaDbDirectory,
            logFilePath=self.serverLogFilePath,
        )
        if not waitForPortListening(
            self.mysqlPort, MYSQL_START_TIMEOUT_SECONDS, process=self.serverProcess
        ):
            self.serverProcess = None
            raise RuntimeError(
                "MariaDB failed to start (port is not listening). Server log:\n"
                + readLogTail(self.serverLogFilePath)
            )
        if not self._waitForRootConnection():
            self.serverProcess = None
            raise RuntimeError(
                "MariaDB port is listening but root cannot connect. Server log:\n"
                + readLogTail(self.serverLogFilePath)
            )
        _logger.info("MariaDB is ready: 127.0.0.1:%s", self.mysqlPort)
        return self.serverProcess

    def _waitForRootConnection(self, timeoutSeconds: float = 60.0) -> bool:
        """等待 root 账号可连接（端口监听后仍可能处于初始化收尾阶段）。"""
        deadline = time.monotonic() + timeoutSeconds
        while time.monotonic() < deadline:
            if self.isServerReachable():
                return True
            if self.serverProcess is not None and self.serverProcess.poll() is not None:
                return False
            time.sleep(0.5)
        return False

    def ensureApplicationDatabase(self) -> None:
        """以 root 身份创建业务库、业务账号并授权（幂等，可重复执行）。"""
        databaseName = self.runtimeConfiguration.databaseName
        databaseUser = self.runtimeConfiguration.databaseUser
        databasePassword = self.runtimeConfiguration.databasePassword
        for identifier in (databaseName, databaseUser):
            if not SAFE_IDENTIFIER_PATTERN.match(identifier):
                raise RuntimeError(f"Invalid database identifier: {identifier}")
        clientExecutablePath = self.locateRequiredExecutable(("mariadb.exe", "mysql.exe"))
        statements = [
            f"CREATE DATABASE IF NOT EXISTS `{databaseName}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
            f"CREATE USER IF NOT EXISTS '{databaseUser}'@'127.0.0.1' "
            f"IDENTIFIED BY '{databasePassword}'",
            f"CREATE USER IF NOT EXISTS '{databaseUser}'@'localhost' "
            f"IDENTIFIED BY '{databasePassword}'",
            f"ALTER USER '{databaseUser}'@'127.0.0.1' IDENTIFIED BY '{databasePassword}'",
            f"ALTER USER '{databaseUser}'@'localhost' IDENTIFIED BY '{databasePassword}'",
            f"GRANT ALL PRIVILEGES ON `{databaseName}`.* TO '{databaseUser}'@'127.0.0.1'",
            f"GRANT ALL PRIVILEGES ON `{databaseName}`.* TO '{databaseUser}'@'localhost'",
            "FLUSH PRIVILEGES",
        ]
        completedProcess = runCommandCaptured(
            clientExecutablePath,
            [
                "--protocol=TCP",
                "-h127.0.0.1",
                f"-P{self.mysqlPort}",
                "-uroot",
                f"-p{self.runtimeConfiguration.rootPassword}",
                "--connect-timeout=15",
                "--skip-ssl",
                "-e",
                "; ".join(statements),
            ],
            timeoutSeconds=60,
            logFilePath=self.installLogFilePath,
        )
        if completedProcess.returncode != 0:
            raise RuntimeError(
                "Failed to create the application database and account:\n" + (completedProcess.stderr or "").strip()
            )
        _logger.info("Application database and account are ready: %s (port %s)", databaseName, self.mysqlPort)

    def start(self) -> None:
        """完整启动流程：初始化数据目录（首次）→ 启动服务 → 创建业务库与账号。"""
        if not self.isDataDirectoryInitialized():
            self.initializeDataDirectory()
        self.startServer()
        self.ensureApplicationDatabase()

    def stop(self) -> None:
        """优雅关闭数据库：优先 mariadb-admin shutdown，超时强制结束进程树。"""
        if self.serverProcess is None or self.serverProcess.poll() is not None:
            self.serverProcess = None
            return
        shutdownStartedAt = time.monotonic()
        _logger.info("Shutting down MariaDB (process ID %s)", self.serverProcess.pid)
        try:
            adminExecutablePath = self.locateRequiredExecutable(("mariadb-admin.exe", "mysqladmin.exe"))
            runCommandCaptured(
                adminExecutablePath,
                [
                    "--protocol=TCP",
                    "-h127.0.0.1",
                    f"-P{self.mysqlPort}",
                    "-uroot",
                    f"-p{self.runtimeConfiguration.rootPassword}",
                    "--connect-timeout=10",
                    "--skip-ssl",
                    "shutdown",
                ],
                timeoutSeconds=20,
                logFilePath=self.installLogFilePath,
            )
            self.serverProcess.wait(timeout=MYSQL_SHUTDOWN_TIMEOUT_SECONDS)
            _logger.info(
                "MariaDB shut down gracefully in %.1f seconds", time.monotonic() - shutdownStartedAt
            )
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired) as exception:
            _logger.warning("Graceful MariaDB shutdown failed; forcing termination: %s", exception)
        finally:
            stopProcessTree(self.serverProcess)
            self.serverProcess = None