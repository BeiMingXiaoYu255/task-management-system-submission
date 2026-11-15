"""v1.1 协作领域 ORM 模型：子团队、子团队成员、团队协作关系。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from TaskManagementBackend.models.baseModel import Base, TimestampMixin, createEnumColumn
from TaskManagementBackend.models.enums import CollaborationStatus


class SubTeam(Base, TimestampMixin):
    """子团队：父团队内一层分组，复用父团队级别，拥有独立子负责人与成员集合。"""

    __tablename__ = "sub_teams"
    __table_args__ = (UniqueConstraint("parent_team_id", "name", name="uk_parent_team_sub_team_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Sub-team primary key")
    parentTeamId = Column(
        "parent_team_id", Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="Parent team"
    )
    name = Column(String(100), nullable=False, comment="Sub-team name")
    description = Column(Text, nullable=True, comment="Sub-team description")
    leaderUserId = Column(
        "leader_user_id", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Sub-team Lead"
    )
    createdBy = Column(
        "created_by", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Creator"
    )

    parentTeam = relationship("Team", back_populates="subTeams", foreign_keys=[parentTeamId])
    leader = relationship("User", foreign_keys=[leaderUserId], lazy="joined")
    members = relationship(
        "SubTeamMember", back_populates="subTeam", cascade="all, delete-orphan"
    )

    @property
    def leaderNickname(self) -> str | None:
        """子负责人昵称；未设置负责人时返回 None。"""
        return self.leader.nickname if self.leader is not None else None

    def __repr__(self) -> str:
        """调试输出：子团队主键与名称。"""
        return f"<SubTeam id={self.id} name={self.name} parent={self.parentTeamId}>"


class SubTeamMember(Base):
    """子团队成员关系：成员必须同时是父团队成员（服务层校验）。"""

    __tablename__ = "sub_team_members"
    __table_args__ = (UniqueConstraint("sub_team_id", "user_id", name="uk_sub_team_user"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    subTeamId = Column(
        "sub_team_id", Integer, ForeignKey("sub_teams.id", ondelete="CASCADE"), nullable=False, comment="Sub-team"
    )
    userId = Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="Member")
    joinedAt = Column("joined_at", DateTime, nullable=False, default=datetime.now, comment="Joined at")

    subTeam = relationship("SubTeam", back_populates="members")
    user = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        """调试输出：子团队与用户。"""
        return f"<SubTeamMember subTeam={self.subTeamId} user={self.userId}>"


class TeamCollaboration(Base, TimestampMixin):
    """协作关系：协作单位可以是团队本级或其一层的子团队。

    状态机：pending（申请中）→ active（已生效）/ rejected（已拒绝）；active → ended（已结束）。
    """

    __tablename__ = "team_collaborations"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Collaboration primary key")
    initiatorTeamId = Column(
        "initiator_team_id", Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="Initiating team"
    )
    initiatorSubTeamId = Column(
        "initiator_sub_team_id",
        Integer,
        ForeignKey("sub_teams.id", ondelete="SET NULL"),
        nullable=True,
        comment="Initiating sub-team (empty = team level)",
    )
    targetTeamId = Column(
        "target_team_id", Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="Receiving team"
    )
    targetSubTeamId = Column(
        "target_sub_team_id",
        Integer,
        ForeignKey("sub_teams.id", ondelete="SET NULL"),
        nullable=True,
        comment="Receiving sub-team (empty = team level)",
    )
    initiatorLiaisonUserId = Column(
        "initiator_liaison_user_id",
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Initiator liaison",
    )
    targetLiaisonUserId = Column(
        "target_liaison_user_id",
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Receiver liaison",
    )
    status = Column(
        "status",
        createEnumColumn(CollaborationStatus, "collaboration_status"),
        nullable=False,
        default=CollaborationStatus.PENDING,
        comment="Collaboration status",
    )
    message = Column(String(500), nullable=True, comment="Request description")
    rejectComment = Column("reject_comment", String(500), nullable=True, comment="Rejection/end reason")
    createdBy = Column(
        "created_by", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Requester"
    )

    initiatorTeam = relationship("Team", foreign_keys=[initiatorTeamId])
    targetTeam = relationship("Team", foreign_keys=[targetTeamId])
    initiatorSubTeam = relationship("SubTeam", foreign_keys=[initiatorSubTeamId])
    targetSubTeam = relationship("SubTeam", foreign_keys=[targetSubTeamId])
    initiatorLiaison = relationship("User", foreign_keys=[initiatorLiaisonUserId], lazy="joined")
    targetLiaison = relationship("User", foreign_keys=[targetLiaisonUserId], lazy="joined")
    creator = relationship("User", foreign_keys=[createdBy])
    tasks = relationship("Task", back_populates="collaboration", foreign_keys="Task.collaborationId")

    def __repr__(self) -> str:
        """调试输出：协作主键与状态。"""
        return f"<TeamCollaboration id={self.id} status={self.status}>"
