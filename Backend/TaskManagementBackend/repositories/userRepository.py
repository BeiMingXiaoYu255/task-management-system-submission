"""用户与技能标签数据访问层。

只封装用户账号、技能标签与用户技能关联的查询和写入，不包含权限判断等业务逻辑。
"""

from sqlalchemy import delete, select

from TaskManagementBackend.models import SkillTag, User, UserSkill
from TaskManagementBackend.repositories.baseRepository import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户仓储：账号查询、创建、资料字段更新与技能关联维护。"""

    model = User

    def getByUsername(self, username: str) -> User | None:
        """按登录名查询用户，不存在返回 None。"""
        return self.db.execute(select(User).where(User.username == username)).scalars().first()

    def getByEmail(self, email: str) -> User | None:
        """按邮箱查询用户，不存在返回 None。"""
        return self.db.execute(select(User).where(User.email == email)).scalars().first()

    def createUser(
        self,
        username: str,
        passwordHash: str,
        nickname: str,
        email: str | None = None,
        phone: str | None = None,
        bio: str | None = None,
    ) -> User:
        """创建用户记录并 flush 取得主键（事务由服务层提交）。"""
        user = User(
            username=username,
            passwordHash=passwordHash,
            nickname=nickname,
            email=email,
            phone=phone,
            bio=bio,
            isActive=True,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def listSkillTags(self, keyword: str | None = None) -> list[SkillTag]:
        """查询技能标签字典，可按名称关键字模糊过滤。"""
        statement = select(SkillTag).order_by(SkillTag.name.asc())
        if keyword and keyword.strip():
            statement = statement.where(SkillTag.name.like(f"%{keyword.strip()}%"))
        return list(self.db.execute(statement).scalars())

    def getSkillTagByName(self, name: str) -> SkillTag | None:
        """按标签名精确查询技能标签。"""
        return self.db.execute(select(SkillTag).where(SkillTag.name == name)).scalars().first()

    def createSkillTag(self, name: str, category: str | None = None) -> SkillTag:
        """创建技能标签并 flush 取得主键。"""
        skillTag = SkillTag(name=name, category=category)
        self.db.add(skillTag)
        self.db.flush()
        return skillTag

    def listSkillTagsByIds(self, skillTagIds: list[int]) -> list[SkillTag]:
        """按主键批量查询技能标签，用于保存技能前校验标签是否存在。"""
        if not skillTagIds:
            return []
        statement = select(SkillTag).where(SkillTag.id.in_(skillTagIds))
        return list(self.db.execute(statement).scalars())

    def replaceUserSkills(self, user: User, skillEntries: list[tuple[int, int]]) -> None:
        """覆盖式替换用户技能：先删除旧关联，再批量插入新关联。"""
        self.db.execute(delete(UserSkill).where(UserSkill.userId == user.id))
        for skillTagId, proficiency in skillEntries:
            self.db.add(
                UserSkill(userId=user.id, skillTagId=skillTagId, proficiency=proficiency)
            )
        self.db.flush()
