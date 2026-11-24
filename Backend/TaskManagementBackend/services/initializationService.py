"""系统初始化数据：内置超级用户与默认技能标签。

应用启动时调用，保证系统首次运行即可登录；重复执行幂等，不覆盖已有数据。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.core.security import hashPassword
from TaskManagementBackend.models import SkillTag, User
from TaskManagementBackend.models.enums import GlobalRole

# 默认技能标签：覆盖常见的软件开发与设计领域
DEFAULT_SKILL_TAGS = [
    ("Frontend Development", "Development"),
    ("Backend Development", "Development"),
    ("Full-stack Development", "Development"),
    ("Mobile Development", "Development"),
    ("Database Design", "Development"),
    ("Testing & Quality", "Testing"),
    ("DevOps & Deployment", "Operations"),
    ("Product Design", "Product"),
    ("Interaction Design", "Design"),
    ("Visual Design", "Design"),
    ("Project Management", "Management"),
    ("Requirements Analysis", "Product"),
    ("Documentation", "General"),
    ("Data Analysis", "Data"),
    ("Artificial Intelligence", "Data"),
]


def ensureSuperAdmin(db: Session) -> User:
    """确保内置超级用户存在且全库唯一。

    实现原理：
        1. 查询是否已有超级用户；有则直接返回；
        2. 否则按配置创建超级用户并提交；
        3. 若配置的用户名已被普通账号占用，则将其升级为超级用户。
    """
    existingSuperAdmin = db.execute(
        select(User).where(User.globalRole == GlobalRole.SUPER_ADMIN)
    ).scalars().first()
    if existingSuperAdmin is not None:
        return existingSuperAdmin
    configuredUsername = settings.superAdminUsername
    user = db.execute(select(User).where(User.username == configuredUsername)).scalars().first()
    if user is None:
        user = User(
            username=configuredUsername,
            passwordHash=hashPassword(settings.superAdminPassword),
            nickname=settings.superAdminNickname,
            globalRole=GlobalRole.SUPER_ADMIN,
            isActive=True,
        )
        db.add(user)
    else:
        user.globalRole = GlobalRole.SUPER_ADMIN
        user.isActive = True
    db.commit()
    db.refresh(user)
    return user


def ensureDefaultSkillTags(db: Session) -> None:
    """确保默认技能标签存在（按名称幂等插入）。"""
    existingNames = set(db.execute(select(SkillTag.name)).scalars().all())
    created = False
    for tagName, category in DEFAULT_SKILL_TAGS:
        if tagName in existingNames:
            continue
        db.add(SkillTag(name=tagName, category=category))
        created = True
    if created:
        db.commit()


def initializeSystemData(db: Session) -> None:
    """初始化系统数据：超级用户与默认技能标签。"""
    ensureSuperAdmin(db)
    ensureDefaultSkillTags(db)
