"""非 Windows 平台（Linux/macOS）外部运行时支持：使用系统安装的 MariaDB/MySQL 与 Redis。

设计说明：
    1. Linux/macOS 安装包不内置便携数据库，运行时管理器改为连接系统服务（mariadb-server / redis-server）；
    2. 系统数据库按仓库开发约定创建：库 task_management、账号 taskadmin / taskadmin123，
       安装文档 packaging/README.md 提供初始化脚本 packaging/setupSystemRuntime.sh；
    3. 端口探测覆盖约定端口与系统默认端口（MySQL 3306/3307、Redis 6379/6380），
       用户也可通过环境变量 TASK_MANAGEMENT_DATABASE_URL 覆盖数据库连接串。
"""

import logging
import socket

import redis

_logger = logging.getLogger("taskManagement.desktop.externalRuntimeSupport")

# 系统数据库约定账号与密码（由 packaging/setupSystemRuntime.sh 创建）
EXTERNAL_DATABASE_USER = "taskadmin"
EXTERNAL_DATABASE_PASSWORD = "taskadmin123"
# 默认端口候选：优先应用约定端口，其次系统默认端口
DEFAULT_MYSQL_PORT_CANDIDATES = (3307, 3306)
DEFAULT_REDIS_PORT_CANDIDATES = (6380, 6379)


def isPortReachable(port: int, host: str = "127.0.0.1", timeoutSeconds: float = 0.6) -> bool:
    """TCP 探测端口是否可连接。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probeSocket:
        probeSocket.settimeout(timeoutSeconds)
        return probeSocket.connect_ex((host, port)) == 0


def detectSystemMysqlPort(preferredPort: int) -> int | None:
    """按候选顺序探测系统 MySQL/MariaDB 端口，返回第一个可用端口。"""
    candidatePorts = [preferredPort]
    for fallbackPort in DEFAULT_MYSQL_PORT_CANDIDATES:
        if fallbackPort not in candidatePorts:
            candidatePorts.append(fallbackPort)
    for candidatePort in candidatePorts:
        if isPortReachable(candidatePort):
            _logger.info("Detected system MySQL/MariaDB port: %s", candidatePort)
            return candidatePort
    return None


def buildExternalDatabaseUrl(mysqlPort: int) -> str:
    """按开发约定账号构造系统数据库连接串。"""
    return (
        f"mysql+pymysql://{EXTERNAL_DATABASE_USER}:{EXTERNAL_DATABASE_PASSWORD}"
        f"@127.0.0.1:{mysqlPort}/task_management?charset=utf8mb4"
    )


def detectReachableRedisPort(preferredPort: int) -> int | None:
    """按候选顺序探测可用 Redis 端口（PING 成功才算可用）。"""
    candidatePorts = [preferredPort]
    for fallbackPort in DEFAULT_REDIS_PORT_CANDIDATES:
        if fallbackPort not in candidatePorts:
            candidatePorts.append(fallbackPort)
    for candidatePort in candidatePorts:
        try:
            redisClient = redis.Redis(
                host="127.0.0.1",
                port=candidatePort,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            redisClient.ping()
            redisClient.close()
            _logger.info("Detected system Redis port: %s", candidatePort)
            return candidatePort
        except Exception:
            continue
    return None
