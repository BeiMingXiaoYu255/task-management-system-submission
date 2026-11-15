"""团队、团队级别、团队成员、入团申请 ORM 模型。"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from TaskManagementBackend.models.baseModel import Base, TimestampMixin, createEnumColumn
from TaskManagementBackend.models.enums import (
    JoinMethod,
    JoinRequestStatus,
    TeamRole,
    TeamStatus,
)


class Team(Base, TimestampMixin):
    """团队实体：团队信息、加入方式、邀请码与认证状态。"""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Team primary key")
    name = Column(String(100), nullable=False, comment="Team name")
    description = Column(Text, nullable=True, comment="Team description")
    joinMethod = Column(
        "join_method",
        createEnumColumn(JoinMethod, "join_method"),
        nullable=False,
        default=JoinMethod.INVITE_ONLY,
        comment="Join method",
    )
    inviteCode = Column("invite_code", String(32), unique=True, nullable=True, comment="Invite code")
    inviteExpiresAt = Column("invite_expires_at", DateTime, nullable=True, comment="Invite code expiration time")
    inviteMaxUses = Column("invite_max_uses", Integer, nullable=False, default=0, comment="Maximum uses; 0 means unlimited")
    inviteUsedCount = Column("invite_used_count", Integer, nullable=False, default=0, comment="Used count")
    status = Column(
        "status",
        createEnumColumn(TeamStatus, "team_status"),
        nullable=False,
        default=TeamStatus.PENDING,
        comment="Certification status",
    )
    createdBy = Column("created_by", Integer, ForeignKey("users.id"), nullable=False, comment="Creator")
    createdAt = Column("created_at", DateTime, nullable=False, default=datetime.now, comment="Creation time")
    updatedAt = Column(
        "updated_at", DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="Update time"
    )

    creator = relationship("User", foreign_keys=[createdBy])
    levels = relationship(
        "TeamLevel", back_populates="team", cascade="all, delete-orphan", order_by="TeamLevel.levelOrder.desc()"
    )
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    joinRequests = relationship("TeamJoinRequest", back_populates="team", cascade="all, delete-orphan")
    tasks = relationship(
        "Task", back_populates="team", cascade="all, delete-orphan", foreign_keys="Task.teamId"
    )
    subTeams = relationship("SubTeam", back_populates="parentTeam", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """调试输出：团队主键与名称。"""
        return f"<Team id={self.id} name={self.name} status={self.status}>"


class TeamLevel(Base, TimestampMixin):
    """团队自定义级别：levelOrder 越大级别越高，级别名称与发布权限由管理员定义。"""

    __tablename__ = "team_levels"
    __table_args__ = (UniqueConstraint("team_id", "level_order", name="uk_team_level_order"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Level primary key")
    teamId = Column("team_id", Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="Team")
    name = Column(String(50), nullable=False, comment="Level name")
    levelOrder = Column("level_order", Integer, nullable=False, comment="Level value; higher means higher rank")
    canCreateTask = Column("can_create_task", Boolean, nullable=False, default=True, comment="Can publish tasks")

    team = relationship("Team", back_populates="levels")
    members = relationship("TeamMember", back_populates="level")

    def __repr__(self) -> str:
        """调试输出：级别主键与名称。"""
        return f"<TeamLevel id={self.id} name={self.name} order={self.levelOrder}>"


class TeamMember(Base):
    """团队成员关系：用户在某团队中的角色与级别（一个用户可加入多个团队）。"""

    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uk_team_user"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    teamId = Column("team_id", Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="Team")
    userId = Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="User")
    role = Column(
        "role", createEnumColumn(TeamRole, "team_role"), nullable=False, default=TeamRole.MEMBER, comment="Team role"
    )
    levelId = Column("level_id", Integer, ForeignKey("team_levels.id"), nullable=False, comment="Member level")
    joinedAt = Column("joined_at", DateTime, nullable=False, default=datetime.now, comment="Joined at")

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="memberships")
    level = relationship("TeamLevel", back_populates="members")

    def __repr__(self) -> str:
        """调试输出：团队/用户/角色。"""
        return f"<TeamMember team={self.teamId} user={self.userId} role={self.role}>"


class TeamJoinRequest(Base):
    """入团申请：approval 方式加入团队时生成，由管理员/子管理员审批。"""

    __tablename__ = "team_join_requests"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    teamId = Column("team_id", Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="Team")
    userId = Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="Applicant")
    message = Column(String(255), nullable=True, comment="Request message")
    status = Column(
        "status",
        createEnumColumn(JoinRequestStatus, "join_request_status"),
        nullable=False,
        default=JoinRequestStatus.PENDING,
        comment="Request status",
    )
    handledBy = Column("handled_by", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Handler")
    createdAt = Column("created_at", DateTime, nullable=False, default=datetime.now, comment="Request time")
    handledAt = Column("handled_at", DateTime, nullable=True, comment="Handled time")

    team = relationship("Team", back_populates="joinRequests")
    user = relationship("User", foreign_keys=[userId])
    handler = relationship("User", foreign_keys=[handledBy])

    def __repr__(self) -> str:
        """调试输出：申请主键与状态。"""
        return f"<TeamJoinRequest id={self.id} team={self.teamId} status={self.status}>"
