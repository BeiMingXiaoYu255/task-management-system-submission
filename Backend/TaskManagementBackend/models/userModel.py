"""用户表 ORM 模型。"""

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from TaskManagementBackend.models.baseModel import Base, TimestampMixin, createEnumColumn
from TaskManagementBackend.models.enums import GlobalRole


class User(Base, TimestampMixin):
    """用户实体：账号、资料与全局角色。

    关系说明：
        memberships —— 用户加入的团队关系；
        skills      —— 用户技能标签关联；
        setting     —— 用户界面设置（一对一）；
        createdTasks—— 用户发布的任务。
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="User primary key")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="Username")
    passwordHash = Column("password_hash", String(100), nullable=False, comment="bcrypt password hash")
    nickname = Column(String(50), nullable=False, comment="Nickname")
    email = Column(String(100), unique=True, nullable=True, comment="Email")
    phone = Column(String(30), nullable=True, comment="Phone number (private field)")
    bio = Column(Text, nullable=True, comment="Bio")
    avatar = Column(String(255), nullable=True, comment="Avatar URL")
    globalRole = Column(
        "global_role",
        createEnumColumn(GlobalRole, "global_role"),
        nullable=False,
        default=GlobalRole.USER,
        comment="Global role",
    )
    isActive = Column("is_active", Boolean, nullable=False, default=True, comment="Active flag")

    memberships = relationship(
        "TeamMember", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    skills = relationship(
        "UserSkill", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    setting = relationship(
        "UserSetting", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    createdTasks = relationship(
        "Task", back_populates="creator", foreign_keys="Task.createdBy", passive_deletes=True
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        """调试输出：仅展示与定位相关的字段。"""
        return f"<User id={self.id} username={self.username} role={self.globalRole}>"
