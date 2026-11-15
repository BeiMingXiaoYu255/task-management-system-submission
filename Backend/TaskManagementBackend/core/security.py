"""安全基础能力：bcrypt 密码哈希、JWT 签发与解析、token 黑名单。

设计说明：
    1. 密码使用 bcrypt 单向哈希，cost=12；
    2. JWT 使用 HS256，payload 含用户标识、角色、jti、过期时间；
    3. 注销 token 时把 jti 写入缓存黑名单，过期时间与 token 剩余有效期一致。
"""

import uuid
from datetime import datetime, timedelta

import bcrypt
import jwt

from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.core.redisClient import cacheClient

# token 黑名单在缓存中的键前缀
TOKEN_BLACKLIST_PREFIX = "token:blacklist:"


def hashPassword(plainPassword: str) -> str:
    """将明文密码转换为 bcrypt 哈希字符串。"""
    passwordBytes = plainPassword.encode("utf-8")
    hashedBytes = bcrypt.hashpw(passwordBytes, bcrypt.gensalt(rounds=settings.bcryptRounds))
    return hashedBytes.decode("utf-8")


def verifyPassword(plainPassword: str, passwordHash: str) -> bool:
    """校验明文密码与数据库中的哈希是否匹配。"""
    try:
        return bcrypt.checkpw(plainPassword.encode("utf-8"), passwordHash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def createAccessToken(userId: int, username: str, globalRole: str) -> dict:
    """签发访问 token。

    参数：
        userId：用户主键；
        username：登录名；
        globalRole：全局角色值。
    返回：
        { token, jti, expiresAt } 字典。
    """
    issuedAt = datetime.now()
    expiresAt = issuedAt + timedelta(days=settings.jwtExpireDays)
    tokenId = uuid.uuid4().hex
    payload = {
        "sub": str(userId),
        "username": username,
        "globalRole": globalRole,
        "jti": tokenId,
        "iat": int(issuedAt.timestamp()),
        "exp": int(expiresAt.timestamp()),
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwtSecret, algorithm=settings.jwtAlgorithm)
    return {"token": token, "jti": tokenId, "expiresAt": expiresAt}


def decodeAccessToken(token: str) -> dict:
    """解析并校验访问 token。

    异常：
        jwt.ExpiredSignatureError：token 已过期；
        jwt.InvalidTokenError：token 非法。
    """
    return jwt.decode(token, settings.jwtSecret, algorithms=[settings.jwtAlgorithm])


def blacklistAccessToken(tokenPayload: dict) -> None:
    """将 token 的 jti 写入黑名单，TTL 为剩余有效期。"""
    tokenId = tokenPayload.get("jti")
    expireTimestamp = int(tokenPayload.get("exp", 0))
    remainingSeconds = max(1, expireTimestamp - int(datetime.now().timestamp()))
    if tokenId:
        cacheClient.set(TOKEN_BLACKLIST_PREFIX + tokenId, "1", remainingSeconds)


def isTokenBlacklisted(tokenPayload: dict) -> bool:
    """判断 token 是否已被注销。"""
    tokenId = tokenPayload.get("jti", "")
    return cacheClient.exists(TOKEN_BLACKLIST_PREFIX + tokenId)
