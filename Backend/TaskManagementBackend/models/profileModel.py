"""技能标签与用户技能关联 ORM 模型。"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import relationship

from datetime import datetime

from TaskManagementBackend.models.baseModel import Base


class SkillTag(Base):
    """技能标签字典：所有用户共享，登录用户可创建新标签。"""

    __tablename__ = "skill_tags"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Skill tag primary key")
    name = Column(String(50), unique=True, nullable=False, comment="Tag name")
    category = Column(String(50), nullable=True, comment="Tag category")
    createdAt = Column("created_at", DateTime, nullable=False, default=datetime.now, comment="Creation time")

    userSkills = relationship("UserSkill", back_populates="skillTag", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """调试输出：标签名。"""
        return f"<SkillTag id={self.id} name={self.name}>"


class UserSkill(Base):
    """用户技能：标签 + 熟练度（1-5），用于个人资料展示与 AI 推荐。"""

    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_tag_id", name="uk_user_skill"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    userId = Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="User")
    skillTagId = Column(
        "skill_tag_id", Integer, ForeignKey("skill_tags.id", ondelete="CASCADE"), nullable=False, comment="Tag"
    )
    proficiency = Column(SmallInteger, nullable=False, default=3, comment="Proficiency (1-5)")

    user = relationship("User", back_populates="skills")
    skillTag = relationship("SkillTag", back_populates="userSkills", lazy="joined")

    def __repr__(self) -> str:
        """调试输出：用户与标签。"""
        return f"<UserSkill user={self.userId} tag={self.skillTagId} proficiency={self.proficiency}>"
