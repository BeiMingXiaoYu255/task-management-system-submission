"""身份认证业务服务：注册、登录限流、当前用户装配、注销与修改密码。

实现要点：
    1. 密码只以 bcrypt 哈希落库，任何日志与响应不出现明文与哈希；
    2. 登录失败按「用户名 + 客户端 IP」在 Redis 计数，5 分钟窗口内超限返回 429；
    3. 注销 / 修改密码时把当前 token 的 jti 写入黑名单，实现旧 token 立即失效。
"""

from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.core.exceptions import AppException, conflict, validationError
from TaskManagementBackend.core.redisClient import cacheClient
from TaskManagementBackend.core.security import (
    blacklistAccessToken,
    createAccessToken,
    decodeAccessToken,
    hashPassword,
    verifyPassword,
)
from TaskManagementBackend.models import Team, User
from TaskManagementBackend.repositories.userRepository import UserRepository
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.serializationService import (
    buildTeamMembership,
    buildUserDetail,
)
from TaskManagementBackend.utils.validatorUtils import (
    validateEmail,
    validateNickname,
    validatePassword,
    validateUsername,
)

# 登录失败计数键模板：同一用户名 + IP 在窗口期内累计失败次数
LOGIN_FAILURE_KEY_TEMPLATE = "login:fail:{username}:{ip}"


class AuthService(BaseService):
    """认证业务服务：账号注册登录、当前用户信息、注销与密码修改。"""

    def __init__(self, db) -> None:
        """注入数据库会话并初始化用户仓储。"""
        super().__init__(db)
        self.userRepository = UserRepository(db)

    def registerUser(
        self,
        username: str,
        password: str,
        nickname: str,
        email: str | None = None,
    ) -> tuple[User, str, dict]:
        """注册普通用户并自动登录，返回 (用户, token, CurrentUser 字典)。"""
        normalizedUsername = validateUsername(username)
        if self.userRepository.getByUsername(normalizedUsername) is not None:
            raise conflict("Username already exists")
        normalizedPassword = validatePassword(password)
        normalizedNickname = validateNickname(nickname)
        normalizedEmail = validateEmail(email)
        if normalizedEmail is not None and self.userRepository.getByEmail(normalizedEmail) is not None:
            raise conflict("Email already in use")
        user = self.userRepository.createUser(
            username=normalizedUsername,
            passwordHash=hashPassword(normalizedPassword),
            nickname=normalizedNickname,
            email=normalizedEmail,
        )
        self.commit()
        return user, self.issueToken(user), self.buildCurrentUser(user)

    def loginUser(self, username: str, password: str, clientIp: str) -> tuple[User, str, dict]:
        """登录校验：先检查失败限流，再验证账号密码与启用状态，成功清空失败计数。"""
        normalizedUsername = (username or "").strip()
        failureKey = LOGIN_FAILURE_KEY_TEMPLATE.format(username=normalizedUsername, ip=clientIp)
        self.ensureNotRateLimited(failureKey)
        user = self.userRepository.getByUsername(normalizedUsername)
        if user is None or not verifyPassword(password, user.passwordHash):
            cacheClient.increment(failureKey, settings.loginWindowSeconds)
            raise AppException("INVALID_CREDENTIALS", "Incorrect username or password", 401)
        if not user.isActive:
            raise AppException("ACCOUNT_DISABLED", "This account has been disabled. Please contact an administrator.", 403)
        cacheClient.delete(failureKey)
        return user, self.issueToken(user), self.buildCurrentUser(user)

    def ensureNotRateLimited(self, failureKey: str) -> None:
        """检查登录失败计数是否达到上限，达到则返回 429。"""
        currentCount = cacheClient.get(failureKey)
        if currentCount is not None and int(currentCount) >= settings.loginMaxAttempts:
            windowMinutes = max(1, settings.loginWindowSeconds // 60)
            raise AppException(
                "RATE_LIMITED",
                f"Too many failed login attempts. Please try again in {windowMinutes} minutes.",
                429,
            )

    def issueToken(self, user: User) -> str:
        """为用户签发 JWT 访问 token。"""
        tokenData = createAccessToken(
            user.id, user.username, user.globalRole.value
        )
        return str(tokenData["token"])

    def buildCurrentUser(self, user: User) -> dict:
        """构建 CurrentUser：用户完整资料 + 当前用户在各团队中的身份列表。"""
        teams: list[dict] = []
        for membership in sorted(user.memberships, key=lambda item: item.teamId):
            team = self.db.get(Team, membership.teamId)
            if team is None:
                continue
            teams.append(buildTeamMembership(team, membership))
        return {"user": buildUserDetail(user), "teams": teams}

    def getCurrentUserInfo(self, currentUser: User) -> dict:
        """返回当前登录用户信息（/auth/me 使用）。"""
        return self.buildCurrentUser(currentUser)

    def logoutByToken(self, token: str) -> None:
        """注销当前 token：解析出 jti 后写入黑名单，剩余有效期后自动过期。"""
        tokenPayload = decodeAccessToken(token)
        blacklistAccessToken(tokenPayload)

    def changePassword(
        self,
        currentUser: User,
        oldPassword: str,
        newPassword: str,
        tokenPayload: dict,
    ) -> None:
        """修改密码：校验旧密码、更新 bcrypt 哈希，并把当前 token 加入黑名单。

        被 settingController 的 /settings/password 复用，保证密码修改行为单一来源。
        """
        if not verifyPassword(oldPassword, currentUser.passwordHash):
            raise validationError("Current password is incorrect")
        normalizedNewPassword = validatePassword(newPassword)
        if verifyPassword(normalizedNewPassword, currentUser.passwordHash):
            raise validationError("New password must differ from the current password")
        currentUser.passwordHash = hashPassword(normalizedNewPassword)
        self.commit()
        blacklistAccessToken(tokenPayload)
