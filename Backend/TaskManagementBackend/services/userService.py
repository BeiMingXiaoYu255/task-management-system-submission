"""用户资料与技能标签业务服务。

职责：
    1. 本人资料读取/修改、技能覆盖式保存、技能标签新建与字典查询；
    2. 查看他人资料：按团队级别关系做权限校验，隐私字段（邮箱/手机号）仅本人与全局管理员可见。
"""

import re

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import conflict, notFound, validationError
from TaskManagementBackend.core.permissions import (
    canViewPrivateProfile,
    requireCanViewUserProfile,
    requireSharesTeam,
)
from TaskManagementBackend.models import User
from TaskManagementBackend.repositories.userRepository import UserRepository
from TaskManagementBackend.schemas.userSchema import (
    CreateSkillTagRequest,
    SaveSkillsRequest,
    UpdateProfileRequest,
)
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.serializationService import buildUserDetail
from TaskManagementBackend.utils.validatorUtils import validateEmail, validateNickname

# 手机号允许数字、加号、短横线与括号，长度 6-30
PHONE_PATTERN = re.compile(r"^[0-9+\-\s()]{6,30}$")


class UserService(BaseService):
    """用户资料业务服务：个人资料、技能标签与他人资料查看。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化用户仓储。"""
        super().__init__(db)
        self.userRepository = UserRepository(db)

    def getMyProfile(self, currentUser: User) -> dict:
        """读取本人完整资料。"""
        return buildUserDetail(currentUser)

    def updateMyProfile(self, currentUser: User, payload: UpdateProfileRequest) -> dict:
        """修改本人资料：仅更新请求体中显式提交的字段。"""
        providedFields = payload.model_fields_set
        if "nickname" in providedFields:
            currentUser.nickname = validateNickname(payload.nickname or "")
        if "email" in providedFields:
            normalizedEmail = validateEmail(payload.email)
            if normalizedEmail is not None:
                existingUser = self.userRepository.getByEmail(normalizedEmail)
                if existingUser is not None and existingUser.id != currentUser.id:
                    raise conflict("Email already in use")
            currentUser.email = normalizedEmail
        if "phone" in providedFields:
            currentUser.phone = validatePhone(payload.phone)
        if "bio" in providedFields:
            currentUser.bio = (payload.bio or "").strip() or None
        self.commit()
        return buildUserDetail(currentUser)

    def saveMySkills(self, currentUser: User, payload: SaveSkillsRequest) -> dict:
        """覆盖式保存本人技能：先校验标签存在与熟练度，再整体替换旧关联。"""
        skillTagIds = [entry.skillTagId for entry in payload.skills]
        if len(skillTagIds) != len(set(skillTagIds)):
            raise validationError("The same skill tag cannot be saved more than once")
        existingTags = self.userRepository.listSkillTagsByIds(skillTagIds)
        if len(existingTags) != len(skillTagIds):
            raise validationError("One or more skill tags are invalid")
        skillEntries = [(entry.skillTagId, entry.proficiency) for entry in payload.skills]
        self.userRepository.replaceUserSkills(currentUser, skillEntries)
        self.commit()
        self.db.expire(currentUser, ["skills"])
        return buildUserDetail(currentUser)

    def createSkillTag(self, payload: CreateSkillTagRequest) -> dict:
        """新建技能标签；同名标签已存在时直接返回已有标签（幂等）。"""
        normalizedName = (payload.name or "").strip()
        if not 1 <= len(normalizedName) <= 50:
            raise validationError("Skill tag name must be 1-50 characters")
        category = (payload.category or "").strip() or None
        skillTag = self.userRepository.getSkillTagByName(normalizedName)
        if skillTag is None:
            skillTag = self.userRepository.createSkillTag(normalizedName, category)
            self.commit()
        return {
            "id": skillTag.id,
            "name": skillTag.name,
            "category": skillTag.category,
            "proficiency": 3,
        }

    def listSkillTags(self, keyword: str | None = None) -> list[dict]:
        """查询全部技能标签字典，可按名称关键字过滤。"""
        return [
            {"id": skillTag.id, "name": skillTag.name, "category": skillTag.category}
            for skillTag in self.userRepository.listSkillTags(keyword)
        ]

    def getUserProfile(self, viewer: User, targetUserId: int) -> dict:
        """查看他人完整资料：权限校验通过后返回，隐私字段按规则隐藏。"""
        targetUser = self.userRepository.getById(targetUserId)
        if targetUser is None:
            raise notFound("User not found")
        requireCanViewUserProfile(self.db, viewer, targetUser)
        profile = buildUserDetail(targetUser)
        if not canViewPrivateProfile(viewer, targetUser.id):
            profile["email"] = None
            profile["phone"] = None
        return profile

    def getUserPublicProfile(self, viewer: User, targetUserId: int) -> dict:
        """查看同团队公开资料：始终隐藏邮箱与手机号。"""
        targetUser = self.userRepository.getById(targetUserId)
        if targetUser is None:
            raise notFound("User not found")
        requireSharesTeam(self.db, viewer, targetUserId)
        profile = buildUserDetail(targetUser)
        profile["email"] = None
        profile["phone"] = None
        return profile


def validatePhone(phone: str | None) -> str | None:
    """校验手机号：允许数字、加号、短横线与括号，空值表示清空。"""
    normalizedPhone = (phone or "").strip()
    if not normalizedPhone:
        return None
    if not PHONE_PATTERN.match(normalizedPhone):
        raise validationError("Phone number format is invalid")
    return normalizedPhone
