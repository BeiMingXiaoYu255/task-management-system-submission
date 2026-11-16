"""便携 Redis 运行时：配置文件启动、健康探测与优雅关闭。

设计说明：
    1. 打包版 Windows 使用随安装包分发的 redis-server.exe（tporadowski 构建）；
    2. Linux/macOS 无便携二进制时，运行时管理器改为使用系统中已运行的 Redis；
    3. Redis 仅用于登录限流、token 黑名单与缓存，不可用时后端会自动降级内存缓存，
       因此启动失败只记录警告、不阻断应用启动。
"""

import logging
import subprocess
import sys
import time
from pathlib import Path

import redis

from TaskManagementBackend.desktop.processUtils import (
    readLogTail,
    startDetachedProcess,
    stopProcessTree,
    waitForPortListening,
)

_logger = logging.getLogger("taskManagement.desktop.redisRuntime")

# 等待 Redis 端口监听的最长时间（秒）
REDIS_START_TIMEOUT_SECONDS = 30.0
# 关闭 Redis 的等待时间（秒）
REDIS_SHUTDOWN_TIMEOUT_SECONDS = 5.0


class RedisRuntime:
    """便携 Redis 运行时管理器。"""

    def __init__(self, redisDirectory: Path, dataDirectory: Path, logDirectory: Path, redisPort: int) -> None:
        """保存运行时目录与端口；实际启动由 startServer 完成。"""
        self.redisDirectory = redisDirectory
        self.dataDirectory = dataDirectory
        self.logDirectory = logDirectory
        self.redisPort = redisPort
        self.serverProcess: subprocess.Popen | None = None
        self.serverLogFilePath = logDirectory / "redis.log"
        self.configurationFilePath = dataDirectory / "redis.conf"

    def locateServerExecutable(self) -> Path | None:
        """查找便携 redis-server 可执行文件（不存在返回 None，表示使用系统 Redis）。"""
        executableName = "redis-server.exe" if sys.platform == "win32" else "redis-server"
        candidatePath = self.redisDirectory / executableName
        return candidatePath if candidatePath.is_file() else None

    def isRedisReachable(self) -> bool:
        """探测 Redis 是否可用（PING）。"""
        try:
            redisClient = redis.Redis(
                host="127.0.0.1",
                port=self.redisPort,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            redisClient.ping()
            redisClient.close()
            return True
        except Exception:
            return False

    def writeConfigurationFile(self) -> Path:
        """生成 Redis 配置文件（绑定回环地址、持久化关闭、日志写文件）。"""
        self.dataDirectory.mkdir(parents=True, exist_ok=True)
        configurationLines = [
            f"port {self.redisPort}",
            "bind 127.0.0.1",
            "protected-mode yes",
            f'dir "{self.dataDirectory.as_posix()}"',
            'save ""',
            "appendonly no",
            f'logfile "{self.serverLogFilePath.as_posix()}"',
            "databases 16",
            "daemonize no",
        ]
        self.configurationFilePath.write_text("\r\n".join(configurationLines) + "\r\n", encoding="utf-8")
        return self.configurationFilePath

    def startServer(self) -> bool:
        """启动便携 Redis 并等待 PING 成功；返回是否由本进程成功启动。"""
        if self.serverProcess is not None and self.serverProcess.poll() is None:
            return True
        serverExecutablePath = self.locateServerExecutable()
        if serverExecutablePath is None:
            return False
        self.dataDirectory.mkdir(parents=True, exist_ok=True)
        configurationFilePath = self.writeConfigurationFile()
        _logger.info("Starting bundled Redis: port %s", self.redisPort)
        self.serverProcess = startDetachedProcess(
            serverExecutablePath,
            [str(configurationFilePath)],
            workingDirectory=self.redisDirectory,
            logFilePath=self.serverLogFilePath,
        )
        if not waitForPortListening(
            self.redisPort, REDIS_START_TIMEOUT_SECONDS, process=self.serverProcess
        ):
            _logger.warning("Redis failed to start (port is not listening): %s", readLogTail(self.serverLogFilePath))
            self.serverProcess = None
            return False
        deadline = time.monotonic() + REDIS_START_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self.isRedisReachable():
                _logger.info("Redis is ready: 127.0.0.1:%s", self.redisPort)
                return True
            if self.serverProcess is not None and self.serverProcess.poll() is not None:
                break
            time.sleep(0.25)
        _logger.warning("Redis PING failed after startup: %s", readLogTail(self.serverLogFilePath))
        return False

    def stopServer(self) -> None:
        """优雅关闭便携 Redis（没有启动过则跳过）。"""
        if self.serverProcess is None or self.serverProcess.poll() is not None:
            self.serverProcess = None
            return
        shutdownStartedAt = time.monotonic()
        _logger.info("Shutting down Redis (process ID %s)", self.serverProcess.pid)
        try:
            if self.serverProcess is not None:
                # 直接结束进程即可：Redis 安装版仅用于缓存，非持久化配置（save ""），无需 SHUTDOWN 落盘
                self.serverProcess.terminate()
                _logger.info(
                    "Sent termination signal to Redis in %.1f seconds",
                    time.monotonic() - shutdownStartedAt,
                )
        except OSError as exception:
            _logger.warning("Failed to send termination signal to Redis: %s", exception)
        try:
            if self.serverProcess is not None:
                self.serverProcess.wait(timeout=REDIS_SHUTDOWN_TIMEOUT_SECONDS)
                _logger.info(
                    "Redis shut down in %.1f seconds", time.monotonic() - shutdownStartedAt
                )
        except subprocess.TimeoutExpired:
            _logger.warning("Redis did not exit within the timeout; force-killing the process")
        finally:
            stopProcessTree(self.serverProcess)
            self.serverProcess = None