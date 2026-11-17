"""系统状态接口控制器：健康检查、局域网访问信息、系统信息。"""

import socket

from fastapi import APIRouter, Depends
from sqlalchemy import text

from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.core.database import engine
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.core.redisClient import cacheClient
from TaskManagementBackend.models import User

router = APIRouter(tags=["System"])


def collectLanIpAddresses() -> list[str]:
    """收集本机可用于局域网访问的 IPv4 地址。

    实现原理：
        1. 通过 UDP connect 探测默认出口网卡地址（不会真正发包）；
        2. 再枚举主机名解析出的全部 IPv4 地址作为补充；
        3. 过滤回环地址后去重排序。
    """
    addresses: set[str] = set()
    try:
        probeSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probeSocket.settimeout(0.5)
        probeSocket.connect(("8.8.8.8", 80))
        addresses.add(probeSocket.getsockname()[0])
        probeSocket.close()
    except OSError:
        pass
    try:
        for addressInfo in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addresses.add(addressInfo[4][0])
    except OSError:
        pass
    return sorted(address for address in addresses if not address.startswith("127."))


def checkDatabaseConnection() -> str:
    """检查数据库连通性，返回 connected / disconnected。"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "disconnected"


@router.get("/health", summary="Health check (public)")
def getHealthStatus() -> dict:
    """返回服务、数据库与缓存状态，用于桌面启动探活。"""
    databaseStatus = checkDatabaseConnection()
    return {
        "status": "ok" if databaseStatus == "connected" else "degraded",
        "version": settings.appVersion,
        "database": databaseStatus,
        "redis": cacheClient.mode,
        "redisConnected": cacheClient.ping(),
    }


@router.get("/system/network", summary="LAN access addresses")
def getNetworkInformation(currentUser: User = Depends(getCurrentUser)) -> dict:
    """返回本机可用的局域网访问地址列表，供客户端复制分享。"""
    port = settings.port
    lanUrls = [f"http://{address}:{port}" for address in collectLanIpAddresses()]
    return {
        "lanUrls": lanUrls,
        "port": port,
        "version": settings.appVersion,
        "hostname": socket.gethostname(),
    }


@router.get("/system/info", summary="System information")
def getSystemInformation(currentUser: User = Depends(getCurrentUser)) -> dict:
    """返回应用名称、版本、数据库类型与缓存模式。"""
    databaseUrl = settings.databaseUrl
    databaseType = "mysql" if databaseUrl.startswith("mysql") else "sqlite"
    return {
        "appName": settings.appName,
        "version": settings.appVersion,
        "databaseType": databaseType,
        "redisMode": cacheClient.mode,
    }
